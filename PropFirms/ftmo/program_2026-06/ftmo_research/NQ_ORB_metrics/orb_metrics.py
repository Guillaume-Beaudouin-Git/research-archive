#!/usr/bin/env python3
"""
orb_metrics.py — NQ intraday Opening-Range Breakout (ORB): full metrics + FTMO 2-step.
=====================================================================================
Strategy (canonical V2+E7):
  * Session: RTH cash (09:30-16:00 ET). Data: Databento NQ 1-min, RTH, roll days skipped.
  * Opening range (OR) = first 30 minutes (high/low of first 30 1-min bars).
  * Filter V2: skip days where OR width < 10 bps of price (no-edge dust days).
  * Entry: first 1-min bar to break OR_high (LONG) or OR_low (SHORT) after the OR; fill at level.
  * Risk unit R = OR width. Initial stop = opposite OR side (= 1R).
  * Exit E7 (trail-to-breakeven): once +1R favorable is reached, move stop to entry;
    exit at breakeven if later touched, else at the RTH close. (Baseline = hold-to-close.)
  * Cost: 2 bps of price round-trip (spread+slippage), subtracted from each trade.

FTMO 2-step first-passage: risk `f` of equity per trade (1R loss = f of equity).
P1 +10% -> P2 +5%, 5% daily loss, $9,000 static floor, no time limit. Rolling daily starts.

NO LOOK-AHEAD: OR and breakout use only bars up to the decision; stop/target resolved
forward bar-by-bar on the same day; the R of day t is realized intraday and never feeds
the entry decision.

Run:  python3 orb_metrics.py --data <NQ_1min.parquet> --out ./out
"""
from __future__ import annotations
import argparse, json, os
from dataclasses import dataclass
import numpy as np, pandas as pd


@dataclass
class Config:
    data_path: str
    out_dir: str = "./out"
    tz: str = "US/Eastern"
    or_min: int = 30           # opening-range length in 1-min bars
    min_or_bps: float = 10.0   # V2 filter: skip days with OR width < this many bps of price
    cost_bps: float = 2.0      # round-trip cost in bps of price
    init_equity: float = 10_000.0
    p1_target: float = 1.10
    p2_target: float = 1.05
    daily_loss_limit: float = 0.05
    total_floor: float = 9_000.0
    risk_levels: tuple = (0.010, 0.015, 0.025)   # risk per trade (fraction of equity)
    start_step: int = 2                          # subsample rolling starts (speed)
    weeks: tuple = tuple(range(1, 11))
    months: tuple = (3, 6, 9, 12, 18, 24, 36, 48)


# --------------------------------------------------------------------------- #
# 1. Build per-day ORB R-multiples (baseline hold-to-close AND E7 trail-to-BE)
# --------------------------------------------------------------------------- #
def _day_R(H, L, C, O_first, cfg: Config):
    """Return (R_close, R_e7, direction) for one day's 1-min OHLC arrays, or None to skip."""
    nb = cfg.or_min
    if len(H) < nb + 3:
        return None
    or_hi, or_lo = H[:nb].max(), L[:nb].min()
    risk = or_hi - or_lo
    if risk <= 0:
        return None
    mid = 0.5 * (or_hi + or_lo)
    if (risk / mid) * 1e4 < cfg.min_or_bps:        # V2 dust filter
        return None
    Hp, Lp, Cp = H[nb:], L[nb:], C[nb:]
    up = np.where(Hp > or_hi)[0]
    dn = np.where(Lp < or_lo)[0]
    iu = up[0] if len(up) else 10**9
    idn = dn[0] if len(dn) else 10**9
    if iu == idn == 10**9:
        return None
    if iu <= idn:
        direction, entry, stop0 = 1, or_hi, or_lo
        bi = iu
    else:
        direction, entry, stop0 = -1, or_lo, or_hi
        bi = idn
    cost = cfg.cost_bps / 1e4 * entry
    fh, fl, fc = Hp[bi:], Lp[bi:], Cp[bi:]         # from breakout bar to close
    close_px = fc[-1]

    def to_R(exit_px):
        return (direction * (exit_px - entry) - cost) / risk

    # --- baseline: stop at opposite side, else close ---
    if direction == 1:
        hit = np.where(fl <= stop0)[0]
    else:
        hit = np.where(fh >= stop0)[0]
    R_close = to_R(stop0 if len(hit) else close_px)

    # --- E7: arm breakeven once +1R favorable, then stop = entry ---
    armed = False
    exit_px = close_px
    for j in range(len(fh)):
        if direction == 1:
            if (not armed) and fl[j] <= stop0:            # original stop first
                exit_px = stop0; break
            if armed and fl[j] <= entry:                   # breakeven stop
                exit_px = entry; break
            if (not armed) and fh[j] >= entry + risk:      # reached +1R -> arm BE
                armed = True
        else:
            if (not armed) and fh[j] >= stop0:
                exit_px = stop0; break
            if armed and fh[j] >= entry:
                exit_px = entry; break
            if (not armed) and fl[j] <= entry - risk:
                armed = True
    R_e7 = to_R(exit_px)
    return R_close, R_e7, direction


def build_orb(cfg: Config) -> pd.DataFrame:
    df = pd.read_parquet(cfg.data_path, columns=["high", "low", "close", "is_rth", "is_roll_day"])
    df = df[df["is_rth"] & ~df["is_roll_day"]]
    idx = df.index.tz_convert(cfg.tz)
    # integer day key + day-change boundaries (data is time-sorted) -> pure numpy slicing
    day_int = (idx.year * 10000 + idx.month * 100 + idx.day).to_numpy()
    H, L, C = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    chg = np.where(np.diff(day_int) != 0)[0] + 1
    starts = np.concatenate([[0], chg])
    ends = np.concatenate([chg, [len(day_int)]])
    day_ts = pd.to_datetime(idx.normalize().to_numpy())[starts]
    R_close = np.full(len(starts), np.nan)
    R_e7 = np.full(len(starts), np.nan)
    direction = np.zeros(len(starts))
    for k, (s, e) in enumerate(zip(starts, ends)):
        r = _day_R(H[s:e], L[s:e], C[s:e], H[s], cfg)
        if r is not None:
            R_close[k], R_e7[k], direction[k] = r
    return pd.DataFrame({"R_close": R_close, "R_e7": R_e7, "direction": direction},
                        index=pd.DatetimeIndex(day_ts))


# --------------------------------------------------------------------------- #
# 2. Per-trade & equity metrics
# --------------------------------------------------------------------------- #
def trade_stats(R: np.ndarray, direction: np.ndarray) -> dict:
    R = R[~np.isnan(R)]
    wins, losses = R[R > 0], R[R <= 0]
    m, s = R.mean(), R.std(ddof=1)
    skew = ((R - m) ** 3).mean() / s ** 3
    d = dict(n_trades=int(len(R)), mean_R=float(m), win_rate=float((R > 0).mean()),
             avg_win_R=float(wins.mean()) if len(wins) else 0.0,
             avg_loss_R=float(losses.mean()) if len(losses) else 0.0,
             skew=float(skew), sharpe_per_trade=float(m / s),
             sharpe_ann=float(m / s * np.sqrt(252)))   # ~1 trade/day
    return d


def split_direction(df: pd.DataFrame, col: str) -> dict:
    sub = df.dropna(subset=[col])
    out = {}
    for lab, dnum in [("long", 1), ("short", -1)]:
        r = sub[sub["direction"] == dnum][col].to_numpy()
        out[lab] = dict(n=int(len(r)), mean_R=float(r.mean()) if len(r) else float("nan"))
    return out


def equity_metrics(daily_R: np.ndarray, f: float) -> dict:
    r = np.nan_to_num(daily_R) * f
    eq = np.cumprod(1.0 + r)
    yrs = len(r) / 252.0
    cagr = eq[-1] ** (1 / yrs) - 1
    dd = eq / np.maximum.accumulate(eq) - 1.0
    mdd = dd.min()
    act = r[r != 0]
    sk = ((act - act.mean()) ** 3).mean() / act.std(ddof=1) ** 3
    return dict(risk=f, CAGR=float(cagr), maxDD=float(mdd), Calmar=float(cagr / abs(mdd)),
                Sharpe_ann=float(r.mean() / r.std(ddof=1) * np.sqrt(252)), skew=float(sk))


# --------------------------------------------------------------------------- #
# 3. FTMO 2-step first-passage (one trade/day, risk f per trade)
# --------------------------------------------------------------------------- #
def _phase(r, start, tgt_mult, cfg, f):
    eq, tgt, i, N = cfg.init_equity, cfg.init_equity * tgt_mult, start, len(r)
    while i < N:
        chg = f * r[i]
        if chg <= -cfg.daily_loss_limit:
            return i, "bust"
        eq *= (1.0 + chg)
        if eq < cfg.total_floor:
            return i, "bust"
        if eq >= tgt:
            return i, "pass"
        i += 1
    return N - 1, "run"


def _funded(r, start, cfg, f):
    e1, s1 = _phase(r, start, cfg.p1_target, cfg, f)
    if s1 != "pass":
        return dict(out=s1, dtot=e1 - start + 1, reached_p2=False)
    e2, s2 = _phase(r, e1 + 1, cfg.p2_target, cfg, f)
    out = "funded" if s2 == "pass" else ("bust" if s2 == "bust" else "run")
    return dict(out=out, dtot=(e1 - start + 1) + max(e2 - e1, 0), reached_p2=True)


def ftmo(daily_R: np.ndarray, cfg: Config, f: float) -> dict:
    r = np.nan_to_num(daily_R)
    N = len(r)
    starts = np.arange(0, N - 5, cfg.start_step)
    recs = [_funded(r, s, cfg, f) for s in starts]
    out = np.array([x["out"] for x in recs])
    dtot = np.array([x["dtot"] for x in recs])
    rp2 = np.array([x["reached_p2"] for x in recs])
    fwd = (N - 1) - starts
    funded, bust, run = out == "funded", out == "bust", out == "run"
    term = funded | bust

    def cinc(Hd):
        elig = term | (fwd >= Hd)
        return float((funded & (dtot <= Hd) & elig).sum() / max(elig.sum(), 1))

    ttf = dtot[funded]
    q = lambda p: float(np.percentile(ttf, p)) if len(ttf) else float("nan")
    return dict(risk=f, n_starts=int(len(out)),
                p_funded_total=float(funded.mean()),
                p_funded_terminal=float(funded.sum() / max(term.sum(), 1)),
                p_P1=float(rp2.mean()), p_P2_given_P1=float(funded.sum() / max(rp2.sum(), 1)),
                pct_bust=float(bust.mean()), pct_running=float(run.mean()),
                ttf_days=dict(p25=q(25), median=q(50), p75=q(75)),
                by_week={w: round(cinc(w * 5), 4) for w in cfg.weeks},
                by_month={m: round(cinc(m * 21), 4) for m in cfg.months})


# --------------------------------------------------------------------------- #
# 4. Regime by year
# --------------------------------------------------------------------------- #
def regime_by_year(df: pd.DataFrame, col: str, cfg: Config) -> pd.DataFrame:
    sub = df.dropna(subset=[col]).copy()
    sub["year"] = sub.index.year
    rows = []
    for y, g in sub.groupby("year"):
        r = g[col].to_numpy()
        s = r.std(ddof=1)
        # single-attempt P1 pass at 1.5% risk, starting Jan 1 that year (illustrative)
        rows.append(dict(year=int(y), n_trades=int(len(r)), mean_R=round(float(r.mean()), 4),
                         win_rate=round(float((r > 0).mean()), 3),
                         sharpe_ann=round(float(r.mean() / s * np.sqrt(252)), 2) if s > 0 else None,
                         best_R=round(float(r.max()), 2), worst_R=round(float(r.min()), 2)))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
def run(cfg: Config) -> dict:
    import time as _t
    os.makedirs(cfg.out_dir, exist_ok=True)
    _t0 = _t.time(); df = build_orb(cfg); print(f"[build_orb {_t.time()-_t0:.1f}s]", flush=True)
    Rc, Re = df["R_close"].to_numpy(), df["R_e7"].to_numpy()
    out = dict(
        period=f"{df.index[0].date()} .. {df.index[-1].date()}",
        n_trading_days=int(len(df)), n_trades=int(df["R_e7"].notna().sum()),
        cost_bps=cfg.cost_bps, or_min=cfg.or_min, min_or_bps=cfg.min_or_bps,
        trade_stats=dict(baseline=trade_stats(Rc, df["direction"].to_numpy()),
                         E7=trade_stats(Re, df["direction"].to_numpy())),
        split_direction_E7=split_direction(df, "R_e7"),
        equity={f"{int(f*1000)/10}%": equity_metrics(Re, f) for f in cfg.risk_levels},
        ftmo={},
    )
    for f in cfg.risk_levels:
        _t1 = _t.time()
        out["ftmo"][f"{int(f*1000)/10}%"] = ftmo(Re, cfg, f)
        print(f"[ftmo risk {f*100:.1f}% {_t.time()-_t1:.1f}s]", flush=True)
    regime_by_year(df, "R_e7", cfg).to_csv(os.path.join(cfg.out_dir, "regime_by_year.csv"), index=False)
    df.to_csv(os.path.join(cfg.out_dir, "orb_daily_R.csv"))
    with open(os.path.join(cfg.out_dir, "metrics_summary.json"), "w") as fjs:
        json.dump(out, fjs, indent=2)
    return out


def _print(o, cfg):
    print(f"\nNQ ORB (V2+E7) | {o['period']} | {o['n_trades']} trades / {o['n_trading_days']} days "
          f"| cost {o['cost_bps']}bps | OR {o['or_min']}min")
    for k in ("baseline", "E7"):
        t = o["trade_stats"][k]
        print(f"  {k:8s}: mean_R {t['mean_R']:+.4f}  win {t['win_rate']*100:.0f}%  "
              f"avgW {t['avg_win_R']:+.2f} avgL {t['avg_loss_R']:+.2f}  skew {t['skew']:+.2f}  "
              f"SR/trade {t['sharpe_per_trade']:+.3f}  SR_ann {t['sharpe_ann']:.2f}")
    sd = o["split_direction_E7"]
    print(f"  direction: long mean_R {sd['long']['mean_R']:+.4f} (n={sd['long']['n']})  "
          f"short {sd['short']['mean_R']:+.4f} (n={sd['short']['n']})")
    print("\nEquity (E7):")
    for k, e in o["equity"].items():
        print(f"  risk {k:5s}  CAGR {e['CAGR']*100:6.1f}%  maxDD {e['maxDD']*100:6.1f}%  "
              f"Calmar {e['Calmar']:.2f}  Sharpe {e['Sharpe_ann']:.2f}  skew {e['skew']:+.2f}")
    print("\nFTMO 2-step (E7):")
    for k, R in o["ftmo"].items():
        print(f"  risk {k:5s}  p(funded) {R['p_funded_total']*100:5.1f}%  bust {R['pct_bust']*100:4.1f}%  "
              f"run {R['pct_running']*100:4.1f}%  p(P1) {R['p_P1']*100:.0f}%  p(P2|P1) {R['p_P2_given_P1']*100:.0f}%  "
              f"median {R['ttf_days']['median']:.0f}d")
        wk = R["by_week"]
        print(f"        p(pass) wk: " + " ".join(f"{w}={wk[w]*100:.0f}%" for w in cfg.weeks)
              + f" | 12mo={R['by_month'][12]*100:.0f}% 24mo={R['by_month'][24]*100:.0f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="./out")
    ap.add_argument("--cost-bps", type=float, default=2.0)
    ap.add_argument("--or-min", type=int, default=30)
    a = ap.parse_args()
    cfg = Config(data_path=a.data, out_dir=a.out, cost_bps=a.cost_bps, or_min=a.or_min)
    _print(run(cfg), cfg)
