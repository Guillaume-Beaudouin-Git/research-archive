"""Piste B — range trading (low-directionality regimes). Executes frozen PREREGISTRATION.md.

Causal range detection (ADX<thr AND Bollinger band-width percentile<40, trailing only) -> fade
Bollinger extremes -> exit on reversion / 8-bar time-stop / breakout hard-stop. Intraday-flat (no swap).
CAUSAL-vs-ORACLE contrast isolates the look-ahead selection artefact. NET of active-fill cost, two-sided.
Signal at T-1, execute at T. Hourly bars.
"""
from __future__ import annotations
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import data as D, stats as st, ftmo_costs as C

OUT = os.path.dirname(os.path.abspath(__file__))
SYMS = ["US100", "US500", "US30", "GER40", "EURUSD", "GBPUSD", "XAUUSD"]
ANN_H = 24 * 252.0            # hourly annualization (approx; intraday-flat so ~fewer, but consistent)
TIME_STOP, BW_PCTILE_W = 8, 250


def wilder(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(alpha=1.0 / n, adjust=False).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    up = h.diff(); dn = -l.diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = wilder(tr, n)
    pdi = 100 * wilder(pd.Series(plus_dm, index=df.index), n) / atr
    mdi = 100 * wilder(pd.Series(minus_dm, index=df.index), n) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return wilder(dx.fillna(0), n)


def atr_frac(df, n=14):
    h, l, c = df["high"], df["low"], df["close"]; pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return (wilder(tr, n) / c)


def precompute(sym, df):
    """All expensive indicators computed ONCE per sym (adx, atr, per-band bands + rolling-quantile
    compression flag, oracle flag). Returns numpy arrays for the lean per-config loop."""
    c = df["close"]; ret = np.log(c).diff(); idx = c.index
    ax = adx(df).values
    aatr = atr_frac(df).values
    day = idx.normalize().values
    fut_vol = ret.shift(-1).rolling(TIME_STOP).std().shift(-(TIME_STOP - 1))
    oracle = (fut_vol < fut_vol.quantile(0.40)).fillna(False).values     # look-ahead control (once)
    bands = {}
    for band_sig in (2.0, 2.5):
        sma = c.rolling(20).mean(); sd = c.rolling(20).std()
        upper, lower = sma + band_sig * sd, sma - band_sig * sd
        bw = (upper - lower) / sma
        compressed = (bw < bw.rolling(BW_PCTILE_W).quantile(0.40)).values  # the slow one — once per band
        bands[band_sig] = dict(cu=upper.values, lo=lower.values, mid=sma.values, compressed=compressed)
    return dict(ret=ret, ax=ax, aatr=aatr, day=day, cl=c.values, oracle=oracle, bands=bands, idx=idx)


def backtest(sym, pc, adx_thr, band_sig, exit_mode, use_oracle=False, zero_cost=False, slip_mult=1.0, light=False):
    ret = pc["ret"]; idx = pc["idx"]; ax = pc["ax"]; aatr = pc["aatr"]; day = pc["day"]; cl = pc["cl"]
    B = pc["bands"][band_sig]; cu, lo, mid = B["cu"], B["lo"], B["mid"]
    if use_oracle:
        rflag = pc["oracle"]
    else:
        raw = (ax < adx_thr) & B["compressed"]                 # low ADX AND compressed band-width
        rflag = np.concatenate([[False], raw[:-1]])            # shift(1): known at T-1
    rt = 0.0 if zero_cost else C.rt_cost_bps(sym, slip_mult) / 1e4

    n = len(idx); pos = np.zeros(n)
    entL = rflag & (cl <= lo)                              # fade low  -> long   (vectorized)
    entS = rflag & (cl >= cu)                              # fade high -> short
    cand = np.where(entL | entS)[0]                        # only candidate entry bars
    exit_ptr = 0
    for e in cand:                                        # event-driven: skip flat bars entirely
        if e < exit_ptr or e == 0:
            continue
        d = 1 if entL[e] else -1
        ea = aatr[e]
        x = e + 1
        while x < n:
            if day[x] != day[x - 1]:                      # intraday-flat over rollover
                break
            hold = x - e
            if d < 0:
                broke = cl[x] > cu[x] + ea; revert = cl[x] <= mid[x]
            else:
                broke = cl[x] < lo[x] - ea; revert = cl[x] >= mid[x]
            if broke or (hold >= TIME_STOP if exit_mode == "time" else (revert or hold >= TIME_STOP)):
                break
            x += 1
        pos[e:x] = d
        exit_ptr = x
    posx = np.concatenate([[0.0], pos[:-1]])              # shift(1): execute next bar
    retv = ret.values
    grossv = posx * retv
    state_chg = np.abs(np.diff(np.concatenate([[0.0], posx])))
    tcv = state_chg * (rt / 2.0)
    netv = np.nan_to_num(grossv) - tcv
    if light:                                            # only Sharpe (for gross/oracle contrast)
        bk = netv[posx != 0]
        s = bk.mean() / bk.std() * np.sqrt(ANN_H) if len(bk) > 3 and bk.std() > 0 else 0.0
        return dict(net_sharpe=float(s))
    posx = pd.Series(posx, index=idx)
    net = pd.Series(netv, index=idx); gross = pd.Series(np.nan_to_num(grossv), index=idx)
    longm, shortm = net.where(posx > 0), net.where(posx < 0)
    n_tr = int((posx.diff().abs() > 0).sum() // 2)
    book = net[posx != 0].reindex(idx).fillna(0.0)
    stt = st.annualized_stats(book, ann=ANN_H)
    gross_book = gross[posx != 0]
    gpt = float(gross_book.sum() / max(n_tr, 1) * 1e4)             # gross bps per trade
    cpt = float(C.rt_cost_bps(sym, slip_mult))                    # cost bps per trade (1 leg RT)
    return dict(sym=sym, adx=adx_thr, band=band_sig, exit=exit_mode, oracle=use_oracle, zero_cost=zero_cost,
                n_trades=n_tr, net_sharpe=stt["sharpe"], hac_t=stt["hac_t"], maxdd=stt["maxdd"],
                long_bps=float(longm[posx > 0].mean() * 1e4) if (posx > 0).any() else 0.0,
                short_bps=float(shortm[posx < 0].mean() * 1e4) if (posx < 0).any() else 0.0,
                short_t=st.hac_tstat(shortm[posx < 0].dropna().values) if (posx < 0).sum() > 10 else 0.0,
                gross_per_trade_bps=gpt, cost_per_trade_bps=cpt, gross_cost_ratio=gpt / cpt if cpt else 0,
                two_sided=bool((longm[posx > 0].mean() if (posx > 0).any() else -1) >= 0
                               and (shortm[posx < 0].mean() if (posx < 0).any() else -1) >= 0),
                _sr=(book.mean() / book.std() if book.std() > 0 else 0.0))


def run_one_sym(s):
    pc = precompute(s, D.load(s, "H")); rows = []
    for adx_thr in [20, 25]:
        for band in [2.0, 2.5]:
            for exm in ["revert", "time"]:
                r = backtest(s, pc, adx_thr, band, exm)                                   # causal NET (full)
                g = backtest(s, pc, adx_thr, band, exm, zero_cost=True, light=True)         # causal GROSS
                o = backtest(s, pc, adx_thr, band, exm, use_oracle=True, zero_cost=True, light=True)  # oracle GROSS
                r["gross_sharpe_causal"] = g["net_sharpe"]; r["gross_sharpe_oracle"] = o["net_sharpe"]
                rows.append({k: v for k, v in r.items() if not k.startswith("_")})
    pd.DataFrame(rows).to_csv(f"{OUT}/grid_{s}.csv", index=False)
    print(f"{s} done ({len(rows)} cells)")


def main():
    import glob
    df = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{OUT}/grid_*.csv"))], ignore_index=True)
    best = None
    q = df[(df.two_sided) & (df.gross_cost_ratio >= 3)]
    if len(q):
        best = q.loc[q.net_sharpe.idxmax()].to_dict()
    df.to_csv(f"{OUT}/backtest_grid.csv", index=False)
    summary = dict(n_trials=len(df),
                   gross_two_sided_pos=int(((df.long_bps > 0) & (df.short_bps > 0) &
                                            (df.gross_sharpe_causal > 0)).sum()),
                   causal_gross_sharpe_median=float(df.gross_sharpe_causal.median()),
                   oracle_gross_sharpe_median=float(df.gross_sharpe_oracle.median()),
                   cells_gross_cost_ratio_ge3=int((df.gross_cost_ratio >= 3).sum()),
                   best_net_sharpe=float(df.net_sharpe.max()),
                   n_two_sided_and_costgate=int(((df.two_sided) & (df.gross_cost_ratio >= 3)).sum()),
                   best_qualifying=None if best is None else {k: best[k] for k in
                       ["sym", "adx", "band", "exit", "net_sharpe", "short_bps", "short_t",
                        "gross_cost_ratio", "n_trades", "maxdd"]})
    json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    print("\n=== CAUSAL vs ORACLE gross Sharpe (selection-artefact test) & cost gate ===")
    show = df.groupby("sym").agg(causal_gross=("gross_sharpe_causal", "median"),
                                 oracle_gross=("gross_sharpe_oracle", "median"),
                                 net_sharpe=("net_sharpe", "median"),
                                 gross_cost_ratio=("gross_cost_ratio", "median"),
                                 short_bps=("short_bps", "mean")).round(3)
    print(show.to_string())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "aggregate":
        for s in sys.argv[1].split(","):
            run_one_sym(s)
    else:
        main()
