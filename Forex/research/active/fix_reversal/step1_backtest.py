"""
step1_backtest.py — Fix-reversal + segmentation on EURUSD FTMO MT5, gross vs net.

Two patterns from the practitioner brief:

Pattern A — Fix-reversal (Krohn-Mueller-Whelan 2024)
----------------------------------------------------
Three fix windows:
  • Tokyo  : 00:55 (JPY no DST, year-round UTC)
  • ECB    : 14:15 CET/CEST (Europe/Berlin)
  • London : 16:00 GMT/BST  (Europe/London)

For each fix-day:
  pre_drift  = log(P[T0]) − log(P[T0−30])        # 30-min run-up
  post_ret   = log(P[T0+60]) − log(P[T0])        # 60-min post-fix
  trade_ret  = −sign(pre_drift) × post_ret       # fade the run-up
  entry      = T0, exit = T0+60                   # intraday, no swap

Pattern B — Intraday segmentation (Ranaldo / Breedon-Ranaldo)
-------------------------------------------------------------
  short_leg  : enter 03:00 ET, exit 11:00 ET, position = −1
  long_leg   : enter 11:00 ET, exit 16:00 ET, position = +1

Cost model (per Step 0)
-----------------------
RT cost in bps charged on entry+exit (one full RT per trade-leg). Fix-specific
spread-p95 + commission $5/lot + 0.5×ATR slippage. markup=1 (feed-raw) baseline,
markup=2 (retail-vs-feed, L23b) stress.

Hard rules
----------
- T-1 signal / T trade: pre_drift uses prices through T0; position taken at the
  bar immediately after. delay=0 here = enter at T0 (same as Krohn convention,
  the fix-open price is the entry mid). delay=1 reported in Step 2.
- HAC lag-6 t-stat. Bootstrap CI on Sharpe in Step 2 if survives.

Implementation
--------------
Vectorised: one `reindex(target_index, method='ffill')` per cohort, not a
Python loop over days.
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import statsmodels.api as sm

REPO = Path(__file__).resolve().parents[4]
PANEL = REPO / "data/panels/m5_indices/EURUSD_M1.csv"
OUTDIR = Path(__file__).resolve().parent

JST = ZoneInfo("Asia/Tokyo")
CET = ZoneInfo("Europe/Berlin")
LON = ZoneInfo("Europe/London")
NY  = ZoneInfo("America/New_York")

PRE_MIN, POST_MIN = 30, 60


# -- loaders ------------------------------------------------------------------
def load_panel() -> pd.DataFrame:
    df = pd.read_csv(PANEL,
                     usecols=["timestamp_utc", "open", "high", "low", "close"])
    df["ts"] = pd.to_datetime(df["timestamp_utc"],
                              format="%Y.%m.%d %H:%M:%S", errors="coerce")
    df = df.dropna(subset=["ts"]).set_index("ts").sort_index()
    df.index = df.index.tz_localize("UTC")
    return df[["close"]]


def load_costs() -> dict:
    with open(OUTDIR / "step0_costs.json") as f:
        return json.load(f)


def t_hac(arr: np.ndarray, lags: int = 6) -> float:
    arr = arr[~np.isnan(arr)]
    if len(arr) < lags + 2:
        return float("nan")
    res = sm.OLS(arr, np.ones((len(arr), 1))
                 ).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.tvalues[0])


def sharpe(arr: np.ndarray, periods_per_year: int) -> float:
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        return float("nan")
    sd = arr.std(ddof=1)
    if sd == 0:
        return float("nan")
    return float(arr.mean() / sd * np.sqrt(periods_per_year))


# -- vectorised price lookup --------------------------------------------------
def asof_prices(prices: pd.Series, target_index: pd.DatetimeIndex) -> pd.Series:
    """For each target ts return the latest close at or before ts. Uses asof()
    which is vectorised and O((m + n) log n)."""
    out = prices.reindex(prices.index.union(target_index)).ffill().loc[target_index]
    return out


def make_fix_targets(unique_dates: pd.DatetimeIndex, fix: str
                     ) -> pd.DatetimeIndex:
    """For each calendar date return the UTC ts of the fix-open T0."""
    tz_map = {"tokyo": (JST, 9, 55),
              "ecb":   (CET, 14, 15),
              "london": (LON, 16, 0)}
    tz, h, m = tz_map[fix]
    # Build local timestamps; convert to UTC. unique_dates are naive dates.
    local = pd.to_datetime(unique_dates.strftime("%Y-%m-%d") + f" {h:02d}:{m:02d}")
    local = local.tz_localize(tz, nonexistent="shift_forward",
                              ambiguous="NaT")
    return pd.DatetimeIndex(local).tz_convert("UTC")


def make_segmentation_targets(unique_dates: pd.DatetimeIndex
                              ) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex,
                                         pd.DatetimeIndex]:
    """Return (t03, t11, t16) UTC for each NY date."""
    def at(h: int) -> pd.DatetimeIndex:
        s = pd.to_datetime(unique_dates.strftime("%Y-%m-%d") + f" {h:02d}:00")
        return pd.DatetimeIndex(s.tz_localize(NY, nonexistent="shift_forward",
                                              ambiguous="NaT")).tz_convert("UTC")
    return at(3), at(11), at(16)


# -- fix-reversal pattern (vectorised) ----------------------------------------
def backtest_fix(prices: pd.Series, fix: str, cost_bps_rt: float,
                 delay_minutes: int = 0) -> pd.DataFrame:
    dates = pd.DatetimeIndex(sorted({ts.date() for ts in prices.index}))
    t0 = make_fix_targets(dates, fix)
    t_pre = t0 - pd.Timedelta(minutes=PRE_MIN)
    t_in = t0 + pd.Timedelta(minutes=delay_minutes)
    t_out = t0 + pd.Timedelta(minutes=POST_MIN)
    p_pre = asof_prices(prices, t_pre).values
    p_t0  = asof_prices(prices, t0).values
    p_in  = asof_prices(prices, t_in).values
    p_out = asof_prices(prices, t_out).values
    valid = ~(np.isnan(p_pre) | np.isnan(p_t0) | np.isnan(p_in) | np.isnan(p_out))
    p_pre, p_t0, p_in, p_out = p_pre[valid], p_t0[valid], p_in[valid], p_out[valid]
    dates_v = dates[valid]
    pre_drift = np.log(p_t0 / p_pre)
    direction = -np.sign(pre_drift)
    post_ret  = np.log(p_out / p_in)
    gross = direction * post_ret
    net = gross - cost_bps_rt * 1e-4
    # drop bars where pre_drift == 0 (no signal)
    nonzero = pre_drift != 0
    return pd.DataFrame({"date": dates_v[nonzero],
                         "pre_drift": pre_drift[nonzero],
                         "direction": direction[nonzero],
                         "gross": gross[nonzero],
                         "net": net[nonzero]})


def backtest_segmentation(prices: pd.Series, cost_bps_rt: float,
                          delay_minutes: int = 0) -> pd.DataFrame:
    dates = pd.DatetimeIndex(sorted({ts.date() for ts in prices.index}))
    t03, t11, t16 = make_segmentation_targets(dates)
    t03 = t03 + pd.Timedelta(minutes=delay_minutes)
    t11_e = t11 + pd.Timedelta(minutes=delay_minutes)  # entry for long leg
    p03 = asof_prices(prices, t03).values
    p11 = asof_prices(prices, t11).values
    p11e = asof_prices(prices, t11_e).values
    p16 = asof_prices(prices, t16).values
    valid = ~(np.isnan(p03) | np.isnan(p11) | np.isnan(p11e) | np.isnan(p16))
    p03, p11, p11e, p16 = p03[valid], p11[valid], p11e[valid], p16[valid]
    dates_v = dates[valid]
    short_gross = -np.log(p11 / p03)
    long_gross  = +np.log(p16 / p11e)
    short_net = short_gross - cost_bps_rt * 1e-4
    long_net  = long_gross  - cost_bps_rt * 1e-4
    return pd.DataFrame({"date": dates_v,
                         "short_gross": short_gross,
                         "short_net":   short_net,
                         "long_gross":  long_gross,
                         "long_net":    long_net,
                         "combined_gross": short_gross + long_gross,
                         "combined_net":   short_net  + long_net})


# -- reporting ----------------------------------------------------------------
def report_leg(name: str, trades: pd.DataFrame, gross_col: str,
               net_col: str, periods_per_year: int = 252) -> dict:
    g = trades[gross_col].values
    n = trades[net_col].values
    return {"label": name, "N": int(len(trades)),
            "gross_mean_bps": round(float(np.nanmean(g)) * 1e4, 2),
            "net_mean_bps":   round(float(np.nanmean(n)) * 1e4, 2),
            "gross_t_HAC6":   round(t_hac(g), 2),
            "net_t_HAC6":     round(t_hac(n), 2),
            "gross_sharpe":   round(sharpe(g, periods_per_year), 2),
            "net_sharpe":     round(sharpe(n, periods_per_year), 2),
            "win_rate":       round(float((g > 0).mean()), 3)}


def main() -> dict:
    prices = load_panel()["close"]
    costs = load_costs()
    print(f"[load] {len(prices):,} M1 bars | {prices.index.min().date()} → "
          f"{prices.index.max().date()}")

    cs = costs["cost_stack_RT_bps"]
    cost_london = cs["London_fix_p95"]["total_markup1"]
    cost_tokyo  = cs["Tokyo_fix_p95"]["total_markup1"]
    cost_ecb    = cs["ECB_fix_p95_winter"]["total_markup1"]
    cost_seg    = cs["London_fix_p95"]["total_markup1"]  # NY hours ≈ London tight
    cost_lon_m2 = cs["London_fix_p95"]["total_markup2"]
    cost_tok_m2 = cs["Tokyo_fix_p95"]["total_markup2"]
    cost_ecb_m2 = cs["ECB_fix_p95_winter"]["total_markup2"]
    cost_seg_m2 = cs["London_fix_p95"]["total_markup2"]

    print(f"Costs RT (markup=1): London {cost_london} | Tokyo {cost_tokyo} | "
          f"ECB {cost_ecb} | Seg {cost_seg} bps\n")

    out = {"meta": {"data": str(PANEL.relative_to(REPO)),
                    "first": str(prices.index.min()),
                    "last":  str(prices.index.max())}}

    # -------- Pattern A: fix-reversal --------
    print("─" * 100)
    print("Pattern A — Fix-reversal (delay=0)")
    print("─" * 100)
    print(f"{'fix':<8s} {'cost_bps':>9s} {'N':>5s} {'gross_bps':>10s} "
          f"{'net_bps':>9s} {'gross_t':>8s} {'net_t':>7s} {'gross_SR':>9s} "
          f"{'net_SR':>8s} {'WR':>6s}")
    pa = {}
    for fix, cost in [("london", cost_london), ("ecb", cost_ecb),
                      ("tokyo", cost_tokyo)]:
        trades = backtest_fix(prices, fix, cost, delay_minutes=0)
        rep = report_leg(fix, trades, "gross", "net")
        pa[fix] = rep
        print(f"{fix:<8s} {cost:>9.2f} {rep['N']:>5d} "
              f"{rep['gross_mean_bps']:>10.2f} {rep['net_mean_bps']:>9.2f} "
              f"{rep['gross_t_HAC6']:>8.2f} {rep['net_t_HAC6']:>7.2f} "
              f"{rep['gross_sharpe']:>9.2f} {rep['net_sharpe']:>8.2f} "
              f"{rep['win_rate']:>6.3f}")

    # Pooled (3 fixes)
    pg, pn = [], []
    for fix, cost in [("london", cost_london), ("ecb", cost_ecb),
                      ("tokyo", cost_tokyo)]:
        t = backtest_fix(prices, fix, cost, delay_minutes=0)
        pg.extend(t["gross"].tolist())
        pn.extend(t["net"].tolist())
    pg, pn = np.array(pg), np.array(pn)
    print(f"\n  POOLED (3 fixes): N={len(pg)} | "
          f"gross_mean={np.nanmean(pg)*1e4:.2f} bps t={t_hac(pg):.2f} "
          f"SR={sharpe(pg, 252):.2f}")
    print(f"                            "
          f"net_mean={np.nanmean(pn)*1e4:.2f} bps t={t_hac(pn):.2f} "
          f"SR={sharpe(pn, 252):.2f}")

    # markup=2 stress
    pg2, pn2 = [], []
    for fix, cost in [("london", cost_lon_m2), ("ecb", cost_ecb_m2),
                      ("tokyo", cost_tok_m2)]:
        t = backtest_fix(prices, fix, cost, delay_minutes=0)
        pg2.extend(t["gross"].tolist()); pn2.extend(t["net"].tolist())
    pn2 = np.array(pn2)
    print(f"  POOLED markup×2 stress:   "
          f"net_mean={np.nanmean(pn2)*1e4:.2f} bps t={t_hac(pn2):.2f} "
          f"SR={sharpe(pn2, 252):.2f}")

    out["pattern_A_fix_reversal"] = {
        "per_fix": pa,
        "pooled": {"N": int(len(pg)),
                   "gross_bps": float(np.nanmean(pg)*1e4),
                   "net_bps":   float(np.nanmean(pn)*1e4),
                   "gross_t":   float(t_hac(pg)),
                   "net_t":     float(t_hac(pn)),
                   "gross_SR":  float(sharpe(pg, 252)),
                   "net_SR":    float(sharpe(pn, 252))},
        "pooled_markup2": {"net_bps": float(np.nanmean(pn2)*1e4),
                           "net_t":   float(t_hac(pn2)),
                           "net_SR":  float(sharpe(pn2, 252))}}

    # -------- Pattern B: segmentation --------
    print("\n" + "─" * 100)
    print("Pattern B — Segmentation EURUSD (short 03-11 ET, long 11-16 ET, delay=0)")
    print("─" * 100)
    seg = backtest_segmentation(prices, cost_seg, delay_minutes=0)
    s = report_leg("short_0311ET", seg, "short_gross", "short_net", 252)
    l = report_leg("long_1116ET",  seg, "long_gross",  "long_net",  252)
    c = report_leg("combined",     seg, "combined_gross", "combined_net", 252)
    print(f"{'leg':<14s} {'N':>5s} {'gross_bps':>10s} {'net_bps':>9s} "
          f"{'gross_t':>8s} {'net_t':>7s} {'gross_SR':>9s} {'net_SR':>8s} {'WR':>6s}")
    for r in [s, l, c]:
        print(f"{r['label']:<14s} {r['N']:>5d} "
              f"{r['gross_mean_bps']:>10.2f} {r['net_mean_bps']:>9.2f} "
              f"{r['gross_t_HAC6']:>8.2f} {r['net_t_HAC6']:>7.2f} "
              f"{r['gross_sharpe']:>9.2f} {r['net_sharpe']:>8.2f} "
              f"{r['win_rate']:>6.3f}")
    out["pattern_B_segmentation"] = {"short": s, "long": l, "combined": c,
                                      "cost_used": cost_seg}
    # markup=2 stress
    seg2 = backtest_segmentation(prices, cost_seg_m2, delay_minutes=0)
    s2 = report_leg("short_m2", seg2, "short_gross", "short_net", 252)
    l2 = report_leg("long_m2",  seg2, "long_gross",  "long_net",  252)
    c2 = report_leg("comb_m2",  seg2, "combined_gross", "combined_net", 252)
    print(f"\n  markup×2 stress: short net={s2['net_mean_bps']:.2f} t={s2['net_t_HAC6']:.2f} "
          f"SR={s2['net_sharpe']:.2f}  |  long net={l2['net_mean_bps']:.2f} t={l2['net_t_HAC6']:.2f} "
          f"SR={l2['net_sharpe']:.2f}  |  combined net={c2['net_mean_bps']:.2f} "
          f"t={c2['net_t_HAC6']:.2f} SR={c2['net_sharpe']:.2f}")
    out["pattern_B_segmentation"]["markup2"] = {"short": s2, "long": l2, "combined": c2}

    with open(OUTDIR / "step1_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nsaved → {OUTDIR / 'step1_results.json'}")
    return out


if __name__ == "__main__":
    main()
