"""
conditional_analysis.py — Part A: Deep Descriptive Analytics
==============================================================
Load iter_05_A400+B012 trade log (A$400 + B1.2% gap filter, 567 trades).
Add 13 contextual variables. Print 7 conditional P&L tables.
No signal changes — observation only.

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.conditional_analysis
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[5]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import NQBacktestEngine
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, signals_from_features,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

STRATEGY_GAP  = 0.012
STRATEGY_STOP = 400.0
VIX_LOW       = 15.0
VIX_HIGH      = 20.0


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_vix() -> pd.Series:
    """Load VIX daily close. Return series indexed by tz-naive date, shifted by 1 day (prev close)."""
    raw_dir = Path(__file__).parents[5] / "data" / "raw"
    vix_files = list(raw_dir.glob("yf_^VIX_1d_*.parquet"))
    if not vix_files:
        log.error("No VIX parquet found in %s", raw_dir)
        return pd.Series(dtype=float)
    vix = pd.read_parquet(vix_files[0])
    s = vix["close"].copy()
    s.index = pd.to_datetime(s.index).normalize()
    # Shift by 1 → each row = previous day's VIX close (no lookahead)
    s = s.shift(1)
    return s


def build_context(trade_log: pd.DataFrame,
                  feats: pd.DataFrame,
                  rth: pd.DataFrame,
                  vix: pd.Series) -> pd.DataFrame:
    """
    Enrich trade_log with 13 contextual variables.

    Variables added:
      1.  dow            — day of week (Monday…Friday)
      2.  rng            — opening range in points (09:30–09:45)
      3.  rng_pct        — percentile rank of rng in [0,100]
      4.  rng_quartile   — Q1/Q2/Q3/Q4 label
      5.  gap_pct        — overnight gap %
      6.  gap_direction  — +1 (gap up) / -1 (gap down) / 0 (near-flat |gap|<0.3%)
      7.  gap_aligned    — True if gap_direction == trade direction
      8.  vix_prev       — VIX close previous day
      9.  vix_regime     — Low (<15) / Medium (15–20) / High (>20)
      10. prior_day_dir  — direction of previous RTH day (+1 up / -1 down)
      11. trend_5d_dir   — sign of 5-day rolling NQ return (+1 up / -1 down)
      12. trend_aligned  — True if trend_5d_dir == trade direction
      13. month          — calendar month 1–12
    """
    tl = trade_log.copy()
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()

    # Build feats lookup keyed by date
    feats_vwap = feats[feats["vwap_ok"]].copy()
    feats_vwap["date"] = pd.to_datetime(feats_vwap["date"]).dt.normalize()
    feats_map = feats_vwap.set_index("date")

    # Daily RTH close series for trend/prior_day features
    rth_daily_close = (
        rth[(rth.index.time >= pd.Timestamp("09:30").time()) &
            (rth.index.time <= pd.Timestamp("15:59").time())]
        ["close"].resample("B").last().dropna()
    )
    rth_daily_close.index = rth_daily_close.index.normalize()

    # 5-day rolling log return (shift 1 = use data up to t-1 only)
    log_ret_5d = np.log(rth_daily_close / rth_daily_close.shift(5))
    log_ret_5d = log_ret_5d.shift(1)  # use data through yesterday

    # Prior day direction
    prior_dir = (rth_daily_close.diff().shift(1) > 0).map({True: 1, False: -1})

    rows = []
    for _, tr in tl.iterrows():
        date    = tr["date"]
        feat    = feats_map.loc[date] if date in feats_map.index else None

        rng     = float(feat["rng"])   if feat is not None else np.nan
        gap_pct = float(feat["gap_pct"]) if feat is not None and pd.notna(feat["gap_pct"]) else np.nan

        gap_dir = (1 if gap_pct > 0.003 else (-1 if gap_pct < -0.003 else 0)) if np.isfinite(gap_pct) else 0
        gap_aligned = bool(gap_dir == tr["direction"]) if gap_dir != 0 else None

        date_naive = date.tz_localize(None) if hasattr(date, "tz_localize") and date.tzinfo is not None else date
        vix_val = float(vix.get(date_naive, np.nan)) if len(vix) > 0 else np.nan
        if not np.isfinite(vix_val):
            vix_regime = "Unknown"
        elif vix_val < VIX_LOW:
            vix_regime = "Low"
        elif vix_val <= VIX_HIGH:
            vix_regime = "Medium"
        else:
            vix_regime = "High"

        trend_5d = float(log_ret_5d.get(date, np.nan))
        trend_dir = (1 if trend_5d > 0 else -1) if np.isfinite(trend_5d) else 0
        trend_aligned = bool(trend_dir == tr["direction"]) if trend_dir != 0 else None

        pday_dir = int(prior_dir.get(date, 0))

        rows.append({
            "dow":           date.day_name(),
            "rng":           rng,
            "gap_pct":       gap_pct,
            "gap_direction": gap_dir,
            "gap_aligned":   gap_aligned,
            "vix_prev":      vix_val,
            "vix_regime":    vix_regime,
            "prior_day_dir": pday_dir,
            "trend_5d":      trend_5d,
            "trend_dir":     trend_dir,
            "trend_aligned": trend_aligned,
            "month":         date.month,
        })

    ctx = pd.DataFrame(rows, index=tl.index)
    tl = pd.concat([tl, ctx], axis=1)

    # Range quartile
    valid_rng = tl["rng"].dropna()
    q25, q50, q75 = valid_rng.quantile([0.25, 0.5, 0.75]).values
    def _rq(r):
        if not np.isfinite(r): return "Q?"
        if r <= q25: return "Q1 (small)"
        if r <= q50: return "Q2"
        if r <= q75: return "Q3"
        return "Q4 (large)"
    tl["rng_quartile"] = tl["rng"].apply(_rq)
    tl["rng_pct"] = tl["rng"].rank(pct=True) * 100

    return tl


# ─────────────────────────────────────────────────────────────────────────────
# Table printers
# ─────────────────────────────────────────────────────────────────────────────

def _stats(group: pd.DataFrame) -> dict:
    pnl = group["pnl_usd"]
    n   = len(pnl)
    return {
        "N":         n,
        "WinRate%":  round((pnl > 0).mean() * 100, 1),
        "AvgP&L":    round(pnl.mean(), 1),
        "TotalP&L":  round(pnl.sum(), 0),
        "AvgWin":    round(pnl[pnl > 0].mean(), 1) if (pnl > 0).any() else 0,
        "AvgLoss":   round(pnl[pnl <= 0].mean(), 1) if (pnl <= 0).any() else 0,
    }


def print_table(title: str, tl: pd.DataFrame, groupby: str,
                order: list = None) -> None:
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print(f"  {'Group':<18} {'N':>5} {'Win%':>7} {'AvgP&L':>9} {'TotalP&L':>11} "
          f"{'AvgWin':>9} {'AvgLoss':>9}")
    print(f"  {'-'*70}")

    grps = tl.groupby(groupby)
    keys = order if order else sorted(grps.groups.keys())

    for k in keys:
        if k not in grps.groups:
            continue
        g  = grps.get_group(k)
        st = _stats(g)
        print(f"  {str(k):<18} {st['N']:>5} {st['WinRate%']:>6.1f}% "
              f"{st['AvgP&L']:>9.1f} {st['TotalP&L']:>11.0f} "
              f"{st['AvgWin']:>9.1f} {st['AvgLoss']:>9.1f}")

    total = _stats(tl)
    print(f"  {'-'*70}")
    print(f"  {'ALL':<18} {total['N']:>5} {total['WinRate%']:>6.1f}% "
          f"{total['AvgP&L']:>9.1f} {total['TotalP&L']:>11.0f} "
          f"{total['AvgWin']:>9.1f} {total['AvgLoss']:>9.1f}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> pd.DataFrame:
    print("=" * 80)
    print("PART A — CONDITIONAL ANALYSIS  |  iter_05_A$400 + B1.2% (baseline)")
    print("=" * 80)

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)
    sigs   = signals_from_features(feats, gap_thresh=STRATEGY_GAP,
                                    dollar_stop=STRATEGY_STOP)
    tl_raw, met = engine.run(sigs)

    print(f"\nBaseline: {len(tl_raw)} trades  |  "
          f"Sharpe={met.get('sharpe_daily_hac',0):.4f}  |  "
          f"MaxDD={met.get('max_dd_pct',0)*100:.1f}%  |  "
          f"WR={met.get('win_rate',0)*100:.1f}%  |  "
          f"PF={met.get('profit_factor',0):.4f}")

    # Load VIX
    vix = load_vix()
    print(f"VIX data: {len(vix)} days  "
          f"[{vix.first_valid_index().date() if len(vix)>0 else 'N/A'} → "
          f"{vix.last_valid_index().date() if len(vix)>0 else 'N/A'}]")

    # Build context
    tl = build_context(tl_raw, feats, engine.rth, vix)
    print(f"Context built: {len(tl)} trades, {tl.columns.tolist()}")

    # ── TABLE 1: Day of Week ──────────────────────────────────────────────
    print_table("TABLE 1 — P&L by Day of Week", tl, "dow",
                order=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])

    # ── TABLE 2: VIX Regime ──────────────────────────────────────────────
    print_table("TABLE 2 — P&L by VIX Regime (prev-day close)",
                tl, "vix_regime",
                order=["Low", "Medium", "High", "Unknown"])
    # Print VIX summary
    vix_in_sample = tl["vix_prev"].dropna()
    print(f"\n  VIX sample: mean={vix_in_sample.mean():.1f}  "
          f"median={vix_in_sample.median():.1f}  "
          f"min={vix_in_sample.min():.1f}  max={vix_in_sample.max():.1f}")

    # ── TABLE 3: Opening Range Quartile ──────────────────────────────────
    print_table("TABLE 3 — P&L by Opening Range Quartile (09:30-09:45 pts)",
                tl, "rng_quartile",
                order=["Q1 (small)", "Q2", "Q3", "Q4 (large)"])
    q25, q50, q75 = (tl["rng"].quantile([0.25, 0.5, 0.75]).values)
    print(f"\n  Range quartile boundaries: Q1≤{q25:.1f}  Q2≤{q50:.1f}  Q3≤{q75:.1f}  Q4>{q75:.1f} pts")

    # ── TABLE 4: Trend 5d Alignment ──────────────────────────────────────
    tl["trend_label"] = tl["trend_aligned"].map(
        {True: "Aligned", False: "Counter", None: "Unknown"}
    ).fillna("Unknown")
    print_table("TABLE 4 — P&L by 5-Day Trend Alignment (trade dir == NQ 5d trend)",
                tl, "trend_label",
                order=["Aligned", "Counter", "Unknown"])
    print(f"\n  5d trend: mean={tl['trend_5d'].dropna().mean()*100:.2f}%  "
          f"std={tl['trend_5d'].dropna().std()*100:.2f}%")

    # ── TABLE 5: Trade Direction ──────────────────────────────────────────
    tl["dir_label"] = tl["direction"].map({1: "Long", -1: "Short"})
    print_table("TABLE 5 — P&L by Trade Direction (Long / Short)",
                tl, "dir_label",
                order=["Long", "Short"])

    # ── TABLE 6: Exit Reason ──────────────────────────────────────────────
    print_table("TABLE 6 — P&L by Exit Reason",
                tl, "exit_reason",
                order=["tp", "sl", "time"])
    # Exit reason stats
    for er, g in tl.groupby("exit_reason"):
        pct = len(g) / len(tl) * 100
        print(f"  {er:<8} {len(g):>4} trades ({pct:.1f}%)  avg_bars={g['bars_held'].mean():.1f}")

    # ── TABLE 7: Monthly Seasonality ──────────────────────────────────────
    tl["month_name"] = pd.to_datetime(tl["date"]).dt.strftime("%b")
    month_order = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
    print_table("TABLE 7 — P&L by Calendar Month (seasonality)",
                tl, "month_name",
                order=month_order)

    # ── SUMMARY OBSERVATIONS ──────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  SUMMARY OBSERVATIONS")
    print("=" * 80)

    # Best/worst DOW
    dow_avg = tl.groupby("dow")["pnl_usd"].mean()
    best_dow  = dow_avg.idxmax()
    worst_dow = dow_avg.idxmin()
    print(f"\n  DOW: Best={best_dow} (avg ${dow_avg[best_dow]:.1f})  "
          f"Worst={worst_dow} (avg ${dow_avg[worst_dow]:.1f})")

    # VIX regime performance
    vix_avg = tl.groupby("vix_regime")["pnl_usd"].mean()
    print(f"  VIX: {dict(vix_avg.round(1).items())}")

    # Trend alignment effect
    ta = tl.groupby("trend_label")["pnl_usd"].agg(["mean","count"])
    print(f"  Trend alignment:\n{ta.to_string()}")

    # Range effect: does larger OR → better performance?
    rq_avg = tl.groupby("rng_quartile")["pnl_usd"].mean()
    print(f"\n  Range quartile avg P&L: {dict(rq_avg.round(1).items())}")

    # Long vs short asymmetry
    dir_avg = tl.groupby("dir_label")["pnl_usd"].mean()
    print(f"  Direction: {dict(dir_avg.round(1).items())}")

    print(f"\n  n_trades={len(tl)}  [Observation complete — no signal changes made]")
    print("=" * 80)

    return tl


if __name__ == "__main__":
    tl = main()
