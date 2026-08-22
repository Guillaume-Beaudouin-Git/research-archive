"""Double 7 book-fit gate — decorrelation vs Strategy A (TSMOM v3 weekly crypto).

Pre-registered in REGISTER.md (frozen before this test statistic was computed).
Frozen Double 7 variant = combo_voltarget12_ts10_full (eq_imp_combo_final.csv).
Strategy A = compute_tsmom_returns(BTC/ETH/SOL), inlined verbatim from
Portfolio/validation/strategies/tsmom_signal.py.

Run from repo root:  python3 data/double7_connors/bookfit/analysis.py
(network needed once for yfinance; cached afterwards).
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[3]
D7DIR = ROOT / "data" / "double7_connors"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(D7DIR))

import data as d7data          # noqa: E402  (load_etf_closes)
import improvements as imp     # noqa: E402  (sig_double7, frac_voltarget, portfolio, sleeve_run)
import metrics as d7m          # noqa: E402

RNG_SEED = 42
COMBO_CSV = D7DIR / "eq_imp_combo_final.csv"
A_CACHE = HERE / "strategy_a_prices.parquet"
DTB3_PARQUET = ROOT / "data" / "raw" / "fred_DTB3_37358bdf84.parquet"

# ───────────────────────── Strategy A (INLINED verbatim) ─────────────────────
# Source: Portfolio/validation/strategies/tsmom_signal.py::compute_tsmom_returns
_LOOKBACK, _VOL_LB, _VOL_TGT, _COST_RT, _CRYPTO_DAYS = 28, 20, 0.18, 0.0017, 365


def compute_tsmom_returns(prices, lookback=_LOOKBACK, vol_lb=_VOL_LB, vol_tgt=_VOL_TGT,
                          cost_rt=_COST_RT, crypto_days=_CRYPTO_DAYS):
    net_per_asset = {}
    for col in prices.columns:
        px = prices[col].dropna()
        if len(px) < lookback + vol_lb + 2:
            continue
        lr = np.log(px / px.shift(1)).clip(-1.0, 1.0).dropna()
        arith = np.exp(lr) - 1.0
        lr_lag = lr.shift(1)
        cumret = lr_lag.rolling(lookback).sum()
        vol_sig = lr_lag.rolling(lookback).std()
        raw_sig = (cumret / (vol_sig * np.sqrt(lookback))).fillna(0.0)
        signal = np.tanh(raw_sig).clip(lower=0.0)
        vol_ann = lr_lag.rolling(vol_lb).std() * np.sqrt(crypto_days)
        vol_scalar = (vol_tgt / vol_ann).clip(0.1, 2.0)
        position = (signal * vol_scalar).where(lr.index.dayofweek == 0).ffill()
        gross = position.shift(1) * arith
        turnover = (position - position.shift(1)).abs().fillna(0.0)
        net_per_asset[col] = (gross - turnover * cost_rt).dropna()
    if not net_per_asset:
        return pd.Series(dtype=float)
    port = pd.DataFrame(net_per_asset)
    valid = port.notna().sum(axis=1) >= 2
    return port[valid].mean(axis=1).dropna()


def fetch_strategy_a_prices():
    if A_CACHE.exists():
        df = pd.read_parquet(A_CACHE)
        if df.index.max() >= pd.Timestamp("2026-05-01"):
            print(f"  A prices from cache ({df.index.min().date()}→{df.index.max().date()})")
            return df
    import yfinance as yf
    print("  Fetching BTC/ETH/SOL from yfinance …")
    out = {}
    for t in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        raw = yf.download(t, start="2020-01-01", end="2026-05-28", interval="1d",
                          auto_adjust=True, progress=False)
        px = raw["Close"][t] if isinstance(raw.columns, pd.MultiIndex) else raw["Close"]
        if t == "SOL-USD":
            px = px[px.index >= pd.Timestamp("2020-04-10")]
        out[t] = px.dropna()
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.to_parquet(A_CACHE)
    print(f"  A prices cached ({df.index.min().date()}→{df.index.max().date()}, {len(df)} rows)")
    return df


# ───────────────────────── Risk-free (DTB3) ─────────────────────────────────
def load_rf_decimal():
    d = pd.read_parquet(DTB3_PARQUET)
    s = d.iloc[:, 0].copy()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return (s / 100.0).sort_index()          # percent → annual decimal


# ───────────────────────── Cash-aware Double 7 sleeve ────────────────────────
def sleeve_run_cash(close, entry, exit_, frac, slip, sleeve0, dates, rf_ann, time_stop=None):
    """imp.sleeve_run + calendar-day DTB3 interest accrued on IDLE cash only."""
    n = len(close)
    eq = np.empty(n)
    cash, shares, entry_px, entry_bar = sleeve0, 0.0, np.nan, -1
    for i in range(n):
        if i > 0:
            dd = (dates[i] - dates[i - 1]).days
            r = rf_ann[i]
            if dd > 0 and np.isfinite(r):
                cash *= (1.0 + r) ** (dd / 365.0)
        px = close[i]
        if shares > 0.0:
            timed_out = time_stop is not None and (i - entry_bar) >= time_stop
            if exit_[i] or timed_out:
                cash += shares * px * (1 - slip)
                shares = 0.0
        elif entry[i]:
            f = 1.0 if frac is None else frac[i]
            if f > 0:
                entry_px = px * (1 + slip)
                notional = cash * min(f, 1.0)
                shares = notional / entry_px
                cash -= notional
                entry_bar = i
        eq[i] = cash + shares * px
    return eq


def portfolio_cash(closes, signal_fn, rf_level, frac_fn=None, slip_bps=5.0,
                   start="2005-09-01", end="2026-05-27", capital=100_000.0, time_stop=None):
    slip = slip_bps * 1e-4
    syms = list(closes.columns)
    sleeve0 = capital / len(syms)
    eqs = []
    for sym in syms:
        c = closes[sym].dropna()
        ent, exi = signal_fn(c)
        m = (c.index >= start) & (c.index <= end)
        cm = c[m]
        frac = frac_fn(c)[m].values if frac_fn is not None else None
        rf_ann = rf_level.reindex(cm.index).ffill().bfill().values
        eq = sleeve_run_cash(cm.values, ent[m].values, exi[m].values, frac, slip,
                             sleeve0, list(cm.index), rf_ann, time_stop)
        eqs.append(pd.Series(eq, index=cm.index))
    return pd.concat(eqs, axis=1).ffill().bfill().sum(axis=1)


# ───────────────────────── stats helpers ────────────────────────────────────
def to_weekly(daily_ret, rule):
    return (1 + daily_ret).resample(rule).prod() - 1


def block_bootstrap_corr(x, y, block, n_boot=10_000, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    x = np.asarray(x); y = np.asarray(y); n = len(x)
    nb = int(np.ceil(n / block))
    out = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n, nb)
        idx = np.concatenate([(s + np.arange(block)) % n for s in starts])[:n]
        xs, ys = x[idx], y[idx]
        if xs.std() == 0 or ys.std() == 0:
            out[b] = np.nan
        else:
            out[b] = np.corrcoef(xs, ys)[0, 1]
    return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5)), float(np.nanmean(out))


def sharpe_excess(daily_eq, rf_level):
    r = daily_eq.pct_change().dropna()
    rf_d = (1 + rf_level.reindex(r.index).ffill().bfill()) ** (1 / 365.0) - 1
    # rf per calendar gap
    dts = r.index.to_series().diff().dt.days.fillna(1).values
    rf_step = (1 + rf_level.reindex(r.index).ffill().bfill().values) ** (dts / 365.0) - 1
    ex = r.values - rf_step
    return np.sqrt(252) * ex.mean() / ex.std(ddof=1)


def main():
    from scipy.stats import spearmanr, hypergeom

    print("=" * 70)
    print("DOUBLE 7 BOOK-FIT GATE vs STRATEGY A")
    print("=" * 70)
    res = {}
    rf = load_rf_decimal()

    # ── 1. Double 7 frozen combo: regenerate + cross-check vs canonical CSV ──
    print("\n[1] Double 7 combo (voltarget12 + timestop10) — regenerate & verify")
    etf = d7data.load_etf_closes()
    combo = imp.portfolio(etf, imp.sig_double7(), imp.frac_voltarget(0.12), time_stop=10)
    eq_engine = combo["equity"]
    eq_csv = pd.read_csv(COMBO_CSV, index_col=0, parse_dates=True).iloc[:, 0]
    j = eq_engine.index.intersection(eq_csv.index)
    max_rel = float((eq_engine[j] - eq_csv[j]).abs().div(eq_csv[j]).max())
    print(f"    engine vs eq_imp_combo_final.csv: max rel |Δ| = {max_rel:.2e}  "
          f"({'MATCH' if max_rel < 1e-4 else 'MISMATCH!!'})")
    print(f"    combo: CAGR={combo['cagr']:+.2%}  Sharpe={combo['sharpe']:.2f}  "
          f"MaxDD={combo['max_drawdown']:.1%}  n_trades={combo['n_trades']}")
    res["combo_verify_max_rel_diff"] = max_rel
    res["combo_reported"] = {k: combo[k] for k in
                             ["cagr", "sharpe", "sortino", "max_drawdown", "calmar",
                              "n_trades", "win_rate", "worst_trade"]}

    # ── 2. Cash-adjustment (idle cash @ DTB3) ──
    print("\n[2] Cash-adjustment: idle cash credited at DTB3 (calendar accrual)")
    eq_nocash = portfolio_cash(etf, imp.sig_double7(), rf * 0.0, imp.frac_voltarget(0.12), time_stop=10)
    eq_cash = portfolio_cash(etf, imp.sig_double7(), rf, imp.frac_voltarget(0.12), time_stop=10)
    reimpl_diff = float((eq_nocash - eq_engine.reindex(eq_nocash.index)).abs().max())
    print(f"    reimpl(rf=0) vs engine: max |Δ$| = {reimpl_diff:.2e}  "
          f"({'MATCH' if reimpl_diff < 1e-3 else 'MISMATCH!!'})")
    cagr_nocash, cagr_cash = d7m.cagr(eq_nocash), d7m.cagr(eq_cash)
    shp_nocash = d7m.sharpe(eq_nocash.pct_change().dropna())
    shp_cash_rf0 = d7m.sharpe(eq_cash.pct_change().dropna())
    shp_cash_excess = sharpe_excess(eq_cash, rf)
    print(f"    CAGR   rf=0 (report basis): {cagr_nocash:+.2%}   "
          f"cash@DTB3: {cagr_cash:+.2%}   (+{(cagr_cash-cagr_nocash)*100:.2f} pts)")
    print(f"    Sharpe rf=0 no-cash: {shp_nocash:.3f}   cash@DTB3 (rf=0 acct): {shp_cash_rf0:.3f}   "
          f"cash@DTB3 EXCESS: {shp_cash_excess:.3f}")
    res["cash_adjust"] = dict(cagr_rf0=cagr_nocash, cagr_cash=cagr_cash,
                              cagr_uplift_pts=(cagr_cash - cagr_nocash) * 100,
                              sharpe_rf0=shp_nocash, sharpe_cash_rf0=shp_cash_rf0,
                              sharpe_cash_excess=shp_cash_excess, reimpl_diff=reimpl_diff)

    # daily D7 returns (raw) for correlation
    d7_daily = eq_engine.pct_change().dropna()
    d7_daily.name = "D7"

    # ── 3. Strategy A daily returns ──
    print("\n[3] Strategy A (TSMOM v3 BTC/ETH/SOL) daily returns")
    prices = fetch_strategy_a_prices()
    a_daily = compute_tsmom_returns(prices)
    a_daily.name = "A"
    sr_a = a_daily.mean() / a_daily.std() * np.sqrt(252)
    print(f"    A: {len(a_daily)} daily obs [{a_daily.index.min().date()}→{a_daily.index.max().date()}]  "
          f"naive ann-SR={sr_a:.2f}")

    # ── 4. Weekly excess returns, common window ──
    print("\n[4] Align to weekly excess returns")
    # calendar-daily rf fractional → weekly compounded rf
    cal = pd.date_range(rf.index.min(), max(a_daily.index.max(), d7_daily.index.max()), freq="D")
    rf_cal = rf.reindex(cal).ffill()
    rf_cal_daily = (1 + rf_cal) ** (1 / 365.0) - 1

    def weekly_excess(daily, rule):
        wk_raw = to_weekly(daily, rule)
        wk_rf = to_weekly(rf_cal_daily, rule).reindex(wk_raw.index)
        return wk_raw - wk_rf, wk_raw

    results_by_anchor = {}
    for rule, label in [("W-SUN", "primary_W-SUN"), ("W-FRI", "robust_W-FRI")]:
        a_we, a_wr = weekly_excess(a_daily, rule)
        d_we, d_wr = weekly_excess(d7_daily, rule)
        common = a_we.index.intersection(d_we.index)
        aw, dw = a_we.reindex(common).dropna(), d_we.reindex(common)
        common = aw.index.intersection(dw.dropna().index)
        aw, dw = a_we.reindex(common), d_we.reindex(common)
        awr, dwr = a_wr.reindex(common), d_wr.reindex(common)
        pear = float(np.corrcoef(aw, dw)[0, 1])
        spear = float(spearmanr(aw, dw).correlation)
        pear_raw = float(np.corrcoef(awr, dwr)[0, 1])
        results_by_anchor[label] = dict(n_weeks=int(len(common)), pearson=pear,
                                        spearman=spear, pearson_raw=pear_raw,
                                        start=str(common.min().date()), end=str(common.max().date()))
        print(f"    [{label}] N_weeks={len(common)} [{common.min().date()}→{common.max().date()}]  "
              f"Pearson(exc)={pear:+.3f}  Spearman={spear:+.3f}  Pearson(raw)={pear_raw:+.3f}")
        if label == "primary_W-SUN":
            aw_p, dw_p = aw, dw

    res["weekly"] = results_by_anchor

    # ── 5. Daily correlation (robustness, common trading days) ──
    cd = a_daily.index.intersection(d7_daily.index)
    ad, dd_ = a_daily.reindex(cd), d7_daily.reindex(cd)
    pear_d = float(np.corrcoef(ad, dd_)[0, 1])
    spear_d = float(spearmanr(ad, dd_).correlation)
    print(f"\n[5] Daily (common trading days, N={len(cd)})  "
          f"Pearson={pear_d:+.3f}  Spearman={spear_d:+.3f}")
    res["daily"] = dict(n=int(len(cd)), pearson=pear_d, spearman=spear_d)

    # ── 6. Rolling 52w Pearson (primary anchor) ──
    roll = aw_p.rolling(52).corr(dw_p).dropna()
    if len(roll):
        print(f"[6] Rolling 52w Pearson (W-SUN): min={roll.min():+.3f}  "
              f"max={roll.max():+.3f}  mean={roll.mean():+.3f}  last={roll.iloc[-1]:+.3f}")
        res["rolling52w"] = dict(min=float(roll.min()), max=float(roll.max()),
                                 mean=float(roll.mean()), last=float(roll.iloc[-1]))

    # ── 7. Tail-coincidence (weekly excess, primary) ──
    print("[7] Tail-coincidence (bottom-decile weeks, W-SUN excess)")
    N = len(aw_p)
    qa, qd = np.quantile(aw_p, 0.10), np.quantile(dw_p, 0.10)
    botA = aw_p <= qa
    botD = dw_p <= qd
    k = int((botA & botD).sum())
    nA, nD = int(botA.sum()), int(botD.sum())
    exp = nA * nD / N
    p_tail = float(hypergeom.sf(k - 1, N, nD, nA))   # P(X>=k)
    d7_in_aworst = float(dw_p[botA].mean())
    a_in_d7worst = float(aw_p[botD].mean())
    union = botA | botD
    rho_tail = float(np.corrcoef(aw_p[union], dw_p[union])[0, 1]) if union.sum() > 2 else np.nan
    print(f"    bottom-decile: A_weeks={nA} D7_weeks={nD}  overlap k={k} (expected {exp:.1f})  "
          f"hypergeom P(X≥k)={p_tail:.3f}")
    print(f"    mean D7 wk-ret during A's worst decile = {d7_in_aworst:+.3%}  "
          f"(overall D7 wk mean {dw_p.mean():+.3%})")
    print(f"    mean A  wk-ret during D7's worst decile = {a_in_d7worst:+.3%}  "
          f"(overall A wk mean {aw_p.mean():+.3%})")
    print(f"    Pearson on union of bottom-decile weeks = {rho_tail:+.3f}")
    res["tail"] = dict(n_weeks=N, decile_A=nA, decile_D7=nD, overlap=k, overlap_expected=exp,
                       hypergeom_p_ge=p_tail, d7_mean_in_A_worst=d7_in_aworst,
                       a_mean_in_d7_worst=a_in_d7worst, d7_overall_mean=float(dw_p.mean()),
                       a_overall_mean=float(aw_p.mean()), pearson_union_tail=rho_tail)

    # ── 8. Block-bootstrap CIs ──
    print("[8] Block-bootstrap 95% CI on Pearson rho")
    lo_w, hi_w, mu_w = block_bootstrap_corr(aw_p.values, dw_p.values, block=8)
    lo_d, hi_d, mu_d = block_bootstrap_corr(ad.values, dd_.values, block=20)
    print(f"    weekly (W-SUN excess, L=8w): mean={mu_w:+.3f}  CI95=[{lo_w:+.3f}, {hi_w:+.3f}]")
    print(f"    daily  (raw, L=20d):         mean={mu_d:+.3f}  CI95=[{lo_d:+.3f}, {hi_d:+.3f}]")
    res["bootstrap"] = dict(weekly=dict(block=8, mean=mu_w, ci=[lo_w, hi_w]),
                            daily=dict(block=20, mean=mu_d, ci=[lo_d, hi_d]))

    # ── 9. VERDICT ──
    prim = results_by_anchor["primary_W-SUN"]
    pear, spear = abs(prim["pearson"]), abs(prim["spearman"])
    gate_corr = (pear < 0.30) and (spear < 0.30)
    tail_ok = (p_tail > 0.05) and (d7_in_aworst > 0 or d7_in_aworst > dw_p.mean() * 1.5 is False)
    # tail crash flag: D7 strongly negative AND co-crash significant
    tail_crash = (p_tail < 0.05) and (d7_in_aworst < 0)
    go = gate_corr and not tail_crash
    border = go and (hi_w >= 0.30)
    verdict = ("GO (borderline — bootstrap CI pierces 0.30)" if border
               else "GO" if go else "NO-GO")
    print("\n" + "=" * 70)
    print(f"VERDICT: {verdict}")
    print(f"  |Pearson|={pear:.3f} <0.30:{pear<0.30}  |Spearman|={spear:.3f} <0.30:{spear<0.30}")
    print(f"  tail co-crash significant & negative: {tail_crash}  (hypergeom p={p_tail:.3f})")
    print("=" * 70)
    res["verdict"] = dict(text=verdict, go=bool(go), gate_corr=bool(gate_corr),
                          tail_crash=bool(tail_crash), borderline=bool(border))

    # save
    (HERE / "results.json").write_text(json.dumps(res, indent=2, default=float))
    aligned = pd.DataFrame({"A_excess_wk": aw_p, "D7_excess_wk": dw_p})
    aligned.to_csv(HERE / "aligned_weekly_WSUN.csv")
    print(f"\nsaved → {HERE/'results.json'} , {HERE/'aligned_weekly_WSUN.csv'}")


if __name__ == "__main__":
    main()
