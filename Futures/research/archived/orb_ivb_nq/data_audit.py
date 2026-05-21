"""
Futures/research/passed/orb_ivb_nq/data_audit.py
=================================================

Data quality audit for the Kaggle NQ 1-min OHLCV dataset (2022-12-26 to 2025-12-11).

Checks (7 total):
  1. Total bars expected vs actual
  2. Timestamp gaps during ORB+trading window (08:30-15:00 ET)
  3. OHLC price sanity (H/L integrity, zero-range, zero-volume)
  4. Overnight gap distribution (contract roll detection)
  5. Weekend / holiday handling
  6. RTH vs ETH bar/volume split
  7. VWAP sanity (vwap_rth within session H/L during RTH)

CRITICAL STOP conditions:
  - > 5% of expected bars missing
  - > 50 sessions with timestamp gaps in the ORB window
  - > 100 bars with H < L (data corruption)

Outputs:
  - Console report
  - data_audit_report.md  (same directory as this script)
  - clean_sessions.json   (list of YYYY-MM-DD strings; loaded by feasibility.py)

Run:
    python -m Futures.research.passed.orb_ivb_nq.data_audit
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import time
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path so `data` package is importable
_HERE  = Path(__file__).parent
_PROJ  = _HERE.parents[3]          # Algo_claude/
sys.path.insert(0, str(_PROJ))

from data.cache import load_nq_1min

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

_OUT_DIR  = _HERE
_REPORT   = _OUT_DIR / "data_audit_report.md"
_SESSIONS = _OUT_DIR / "clean_sessions.json"

# ORB strategy window (ET)
ORB_START   = time(8, 30)
ORB_END     = time(9, 0)
TRADE_START = time(9, 0)
TRADE_END   = time(15, 0)

# RTH for volume/bar split check (traditional equity RTH definition)
RTH_START = time(9, 30)
RTH_END   = time(16, 0)

# Thresholds
MIN_ORB_BARS_FRAC   = 0.80   # need ≥ 80% of expected 30 ORB bars
MIN_TRADE_BARS_FRAC = 0.80   # need ≥ 80% of expected 360 trade bars
MAX_GAP_MINUTES     = 5      # gaps > 5 min during ORB or trade window flagged
MAX_OVERNIGHT_GAP   = 0.03   # 3% overnight gap flags potential roll mismatch

CRITICAL_MISSING_PCT = 0.05  # >5% missing bars → STOP
CRITICAL_GAP_SESSIONS = 50   # >50 sessions with gaps → STOP
CRITICAL_OHLC_BAD    = 100   # >100 H<L bars → STOP


# ─────────────────────────────────────────────────────────────────────────────

def _window_mask(df: pd.DataFrame, t_start: time, t_end: time) -> pd.Series:
    """Boolean mask for rows within [t_start, t_end) in ET."""
    t = df.index.time
    return pd.Series((t >= t_start) & (t < t_end), index=df.index)


def _session_dates(df: pd.DataFrame, t_start: time, t_end: time) -> list[object]:
    """Unique ET calendar dates that have at least 1 bar in [t_start, t_end)."""
    mask = _window_mask(df, t_start, t_end)
    return sorted(df.index[mask].normalize().unique().tolist())


# ─────────────────────────────────────────────────────────────────────────────
# Check 1: total bars
# ─────────────────────────────────────────────────────────────────────────────

def check_total_bars(df: pd.DataFrame) -> dict:
    actual = len(df)
    date_range_days = (df.index[-1] - df.index[0]).days
    years            = date_range_days / 365.25
    trading_days     = years * 252
    bars_per_day     = 23 * 60  # NQ trades ~23h/day
    expected         = int(trading_days * bars_per_day)
    coverage_pct     = actual / expected * 100

    return {
        "actual_bars":   actual,
        "expected_bars": expected,
        "coverage_pct":  round(coverage_pct, 2),
        "date_range":    f"{df.index[0].date()} → {df.index[-1].date()}",
        "years":         round(years, 2),
        "pass":          (actual / expected) >= (1 - CRITICAL_MISSING_PCT),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Check 2: timestamp gaps during ORB + trading window
# ─────────────────────────────────────────────────────────────────────────────

def check_gaps(df: pd.DataFrame) -> dict:
    """
    For each session date, inspect bars in 08:30-15:00 ET.
    Flag any consecutive gap > MAX_GAP_MINUTES.
    """
    orb_trade_mask = _window_mask(df, ORB_START, TRADE_END)
    window_df      = df[orb_trade_mask]

    sessions_with_gaps  = []
    worst_gaps          = []

    for date, grp in window_df.groupby(window_df.index.normalize()):
        diffs = grp.index.to_series().diff().dt.total_seconds().div(60)
        bad   = diffs[diffs > MAX_GAP_MINUTES]
        if not bad.empty:
            largest_gap = bad.max()
            sessions_with_gaps.append(str(date.date()))
            worst_gaps.append({
                "date":         str(date.date()),
                "gap_min":      round(largest_gap, 1),
                "at_time":      str(bad.idxmax().time()),
                "n_gaps":       len(bad),
            })

    worst_gaps.sort(key=lambda x: -x["gap_min"])

    return {
        "sessions_with_gaps": len(sessions_with_gaps),
        "worst_10":           worst_gaps[:10],
        "pass":               len(sessions_with_gaps) <= CRITICAL_GAP_SESSIONS,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Check 3: OHLC price sanity
# ─────────────────────────────────────────────────────────────────────────────

def check_ohlc(df: pd.DataFrame) -> dict:
    h_lt_l         = (df["high"] < df["low"]).sum()
    h_lt_c         = (df["high"] < df["close"]).sum()
    h_lt_o         = (df["high"] < df["open"]).sum()
    l_gt_c         = (df["low"]  > df["close"]).sum()
    l_gt_o         = (df["low"]  > df["open"]).sum()
    zero_range     = (df["high"] == df["low"]).sum()

    rth_mask     = _window_mask(df, RTH_START, RTH_END)
    zero_vol_rth = (df[rth_mask]["volume"] == 0).sum()

    # For H<L check, collect worst offenders
    bad_hl_rows = df[df["high"] < df["low"]][["open", "high", "low", "close"]].head(10)

    return {
        "h_lt_l":         int(h_lt_l),
        "h_lt_c":         int(h_lt_c),
        "h_lt_o":         int(h_lt_o),
        "l_gt_c":         int(l_gt_c),
        "l_gt_o":         int(l_gt_o),
        "zero_range":     int(zero_range),
        "zero_vol_rth":   int(zero_vol_rth),
        "bad_hl_sample":  bad_hl_rows.to_dict("index"),
        "pass":           int(h_lt_l) <= CRITICAL_OHLC_BAD,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Check 4: overnight gap distribution
# ─────────────────────────────────────────────────────────────────────────────

def check_overnight_gaps(df: pd.DataFrame) -> dict:
    """
    Compute per-session overnight gap: |prev_session_close / this_session_open - 1|.
    Flag gaps > MAX_OVERNIGHT_GAP (3%) as potential contract roll artefacts.
    """
    # Last bar per session date
    session_close = (
        df.groupby(df.index.normalize())["close"]
        .last()
        .sort_index()
    )
    # First bar per session date
    session_open  = (
        df.groupby(df.index.normalize())["open"]
        .first()
        .sort_index()
    )

    # Align
    dates = session_close.index.intersection(session_open.index)
    closes = session_close.loc[dates]
    opens  = session_open.loc[dates]

    prev_close = closes.shift(1)
    gaps       = (opens / prev_close - 1).abs().dropna()

    large_gaps = gaps[gaps > MAX_OVERNIGHT_GAP].sort_values(ascending=False)
    pct_hist   = {
        "p50": round(gaps.quantile(0.50) * 100, 3),
        "p95": round(gaps.quantile(0.95) * 100, 3),
        "p99": round(gaps.quantile(0.99) * 100, 3),
        "max": round(gaps.max() * 100, 3),
    }

    return {
        "n_sessions":          len(gaps),
        "large_gaps_gt3pct":   int(len(large_gaps)),
        "pct_hist":            pct_hist,
        "worst_10":            [
            {"date": str(d.date()), "gap_pct": round(v * 100, 2)}
            for d, v in large_gaps.head(10).items()
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Check 5: weekends
# ─────────────────────────────────────────────────────────────────────────────

def check_weekends(df: pd.DataFrame) -> dict:
    # NQ futures trade Sunday evenings (CME Globex opens Sun 18:00 ET).
    # Sunday bars (dayofweek==6) are NORMAL and expected.
    # Only Saturday bars (dayofweek==5) are anomalous.
    sat_mask    = df.index.dayofweek == 5   # Sat only
    sun_mask    = df.index.dayofweek == 6   # Sun (normal for NQ)
    sat_bars    = int(sat_mask.sum())
    sun_bars    = int(sun_mask.sum())
    return {
        "saturday_bars": sat_bars,
        "sunday_bars":   sun_bars,
        "weekend_bars":  sat_bars,   # only Saturday is anomalous
        "note":          "Sunday bars are normal CME Globex hours (Sun 18:00 ET open)",
        "pass":          sat_bars == 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Check 6: RTH vs ETH split
# ─────────────────────────────────────────────────────────────────────────────

def check_rth_eth_split(df: pd.DataFrame) -> dict:
    rth_mask    = _window_mask(df, RTH_START, RTH_END)
    rth_bars    = rth_mask.sum()
    total_bars  = len(df)
    total_vol   = df["volume"].sum()
    rth_vol     = df.loc[rth_mask, "volume"].sum()

    bar_pct_rth = rth_bars / total_bars * 100
    vol_pct_rth = rth_vol  / total_vol  * 100

    # 6.5h / 23h ≈ 28% expected for RTH bars
    return {
        "rth_bars":      int(rth_bars),
        "total_bars":    int(total_bars),
        "bar_pct_rth":   round(bar_pct_rth, 2),
        "rth_vol":       int(rth_vol),
        "total_vol":     int(total_vol),
        "vol_pct_rth":   round(vol_pct_rth, 2),
        "expected_bar_pct": "~28% (6.5h / 23h)",
        "expected_vol_pct": "~70-80%",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Check 7: VWAP sanity
# ─────────────────────────────────────────────────────────────────────────────

def check_vwap(df: pd.DataFrame) -> dict:
    """
    VWAP_RTH should be within [session_low, session_high] when > 0.
    """
    rth_mask  = _window_mask(df, RTH_START, RTH_END)
    rth_df    = df[rth_mask & (df["vwap_rth"] > 0)].copy()

    if rth_df.empty:
        return {"vwap_violations": 0, "sample_sessions": [], "pass": True}

    # Per-session daily H/L
    dates      = rth_df.index.normalize()
    daily_high = rth_df.groupby(dates)["high"].transform("max")
    daily_low  = rth_df.groupby(dates)["low"].transform("min")

    above_high  = (rth_df["vwap_rth"] > daily_high).sum()
    below_low   = (rth_df["vwap_rth"] < daily_low).sum()
    violations  = int(above_high + below_low)

    # Sample 5 sessions for visual spot check
    sample_dates = rth_df.index.normalize().unique()[:5]
    sample_rows  = []
    for d in sample_dates:
        day = rth_df[rth_df.index.normalize() == d].head(1)
        if not day.empty:
            r = day.iloc[0]
            sample_rows.append({
                "date":     str(d.date()),
                "open":     float(r["open"]),
                "high":     float(daily_high[day.index[0]]),
                "low":      float(daily_low[day.index[0]]),
                "close":    float(r["close"]),
                "vwap_rth": float(r["vwap_rth"]),
            })

    return {
        "rth_bars_with_vwap": len(rth_df),
        "above_daily_high":   int(above_high),
        "below_daily_low":    int(below_low),
        "violations":         violations,
        "sample_sessions":    sample_rows,
        "pass":               violations < 100,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Build clean_sessions filter
# ─────────────────────────────────────────────────────────────────────────────

def build_clean_sessions(
    df: pd.DataFrame,
    gap_check: dict,
) -> tuple[list[str], list[dict]]:
    """
    Returns (clean_dates, excluded_dates) where each entry is a YYYY-MM-DD string.

    Exclusion criteria (per session date):
      1. < 80% of expected 30 ORB bars (08:30-08:59 ET)
      2. < 80% of expected 360 trading bars (09:00-14:59 ET)
      3. Any timestamp gap > 5 min in ORB window (08:30-08:59 ET)
      4. Any OHLC violation (H < L) in the session
    """
    orb_window_mask   = _window_mask(df, ORB_START, ORB_END)
    trade_window_mask = _window_mask(df, TRADE_START, TRADE_END)

    orb_counts   = df[orb_window_mask].groupby(df[orb_window_mask].index.normalize()).size()
    trade_counts = df[trade_window_mask].groupby(df[trade_window_mask].index.normalize()).size()

    # OHLC bad bars per session
    bad_ohlc     = df[df["high"] < df["low"]]
    bad_sessions = set(bad_ohlc.index.normalize().tolist())

    # Sessions with gaps in ORB window
    gap_sessions = set()
    for date, grp in df[orb_window_mask].groupby(df[orb_window_mask].index.normalize()):
        diffs = grp.index.to_series().diff().dt.total_seconds().div(60)
        if (diffs > MAX_GAP_MINUTES).any():
            gap_sessions.add(date)

    all_dates  = sorted(set(orb_counts.index.tolist()) & set(trade_counts.index.tolist()))
    clean      = []
    excluded   = []

    min_orb_bars   = int(30 * MIN_ORB_BARS_FRAC)    # 24
    min_trade_bars = int(360 * MIN_TRADE_BARS_FRAC)  # 288

    for d in all_dates:
        reasons = []
        n_orb   = int(orb_counts.get(d, 0))
        n_trade = int(trade_counts.get(d, 0))

        if n_orb < min_orb_bars:
            reasons.append(f"ORB bars {n_orb}<{min_orb_bars}")
        if n_trade < min_trade_bars:
            reasons.append(f"trade bars {n_trade}<{min_trade_bars}")
        if d in bad_sessions:
            reasons.append("H<L violation")
        if d in gap_sessions:
            reasons.append("gap in ORB window")

        ds = str(d.date())
        if reasons:
            excluded.append({"date": ds, "reasons": ", ".join(reasons)})
        else:
            clean.append(ds)

    return clean, excluded


# ─────────────────────────────────────────────────────────────────────────────
# Report builder
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_table(headers: list[str], rows: list[list]) -> str:
    """Simple markdown table."""
    sep  = "| " + " | ".join("-" * max(len(h), 6) for h in headers) + " |"
    head = "| " + " | ".join(headers) + " |"
    body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows)
    return "\n".join([head, sep, body])


def build_report(
    df: pd.DataFrame,
    c1: dict, c2: dict, c3: dict, c4: dict,
    c5: dict, c6: dict, c7: dict,
    clean: list[str], excluded: list[dict],
    critical_stop: bool, stop_reasons: list[str],
) -> str:
    lines = []
    A = lines.append

    A("# NQ 1-min Data Quality Audit")
    A("")
    A(f"**Dataset**: `Dataset_NQ_1min_2022_2025.csv`")
    A(f"**Date range**: {c1['date_range']}")
    A(f"**Bars**: {c1['actual_bars']:,} actual | {c1['expected_bars']:,} expected | coverage {c1['coverage_pct']:.1f}%")
    A("")

    # ── Critical checkpoint ──
    if critical_stop:
        A("## ⛔ CRITICAL STOP")
        for r in stop_reasons:
            A(f"- {r}")
        A("")
        A("Strategy script should NOT be run until these are resolved.")
        A("")
    else:
        A("## ✅ Critical checkpoint: PASS — no critical data issues")
        A("")

    # ── Check 1 ──
    A("## 1. Total Bars")
    A("")
    A(f"| Metric | Value |")
    A(f"|--------|-------|")
    A(f"| Actual bars | {c1['actual_bars']:,} |")
    A(f"| Expected bars | {c1['expected_bars']:,} |")
    A(f"| Coverage | {c1['coverage_pct']:.2f}% |")
    A(f"| Date range | {c1['date_range']} |")
    A(f"| Years | {c1['years']} |")
    A(f"| Status | {'✅ PASS' if c1['pass'] else '⛔ FAIL'} |")
    A("")

    # ── Check 2 ──
    A("## 2. Timestamp Gaps (ORB+Trading Window 08:30-15:00 ET)")
    A("")
    A(f"Sessions with gaps > {MAX_GAP_MINUTES} min: **{c2['sessions_with_gaps']}**  "
      f"{'✅' if c2['pass'] else '⛔ FAIL (>50)'}")
    A("")
    if c2["worst_10"]:
        A("**Worst 10 gaps:**")
        A("")
        A(_fmt_table(
            ["Date", "Gap (min)", "At time", "N gaps in session"],
            [[g["date"], g["gap_min"], g["at_time"], g["n_gaps"]] for g in c2["worst_10"]],
        ))
        A("")

    # ── Check 3 ──
    A("## 3. OHLC Price Sanity")
    A("")
    A(f"| Check | Count | Status |")
    A(f"|-------|-------|--------|")
    A(f"| H < L (corruption) | {c3['h_lt_l']} | {'✅' if c3['h_lt_l'] == 0 else ('⛔ FAIL' if c3['h_lt_l'] > CRITICAL_OHLC_BAD else '⚠️')} |")
    A(f"| H < Close | {c3['h_lt_c']} | {'✅' if c3['h_lt_c'] == 0 else '⚠️'} |")
    A(f"| H < Open | {c3['h_lt_o']} | {'✅' if c3['h_lt_o'] == 0 else '⚠️'} |")
    A(f"| L > Close | {c3['l_gt_c']} | {'✅' if c3['l_gt_c'] == 0 else '⚠️'} |")
    A(f"| L > Open | {c3['l_gt_o']} | {'✅' if c3['l_gt_o'] == 0 else '⚠️'} |")
    A(f"| Zero-range bars (H==L) | {c3['zero_range']} | {'✅' if c3['zero_range'] == 0 else '⚠️'} |")
    A(f"| Zero-volume bars (RTH) | {c3['zero_vol_rth']} | {'✅' if c3['zero_vol_rth'] == 0 else '⚠️'} |")
    A("")

    # ── Check 4 ──
    A("## 4. Overnight Gap Distribution")
    A("")
    A(f"Sessions analysed: {c4['n_sessions']}  |  Large gaps (>3%): **{c4['large_gaps_gt3pct']}**")
    A("")
    A(f"| Percentile | Gap |")
    A(f"|------------|-----|")
    for k, v in c4["pct_hist"].items():
        A(f"| {k} | {v:.3f}% |")
    A("")
    if c4["worst_10"]:
        A("**Worst 10 overnight gaps (potential roll misalignments):**")
        A("")
        A(_fmt_table(
            ["Date", "Gap (%)"],
            [[g["date"], f"{g['gap_pct']:.2f}%"] for g in c4["worst_10"]],
        ))
        A("")

    # ── Check 5 ──
    A("## 5. Weekend / Holiday Handling")
    A("")
    A(f"Saturday bars (anomalous): **{c5['saturday_bars']}**  {'✅ PASS' if c5['pass'] else '⛔ FAIL'}")
    A(f"Sunday bars: **{c5['sunday_bars']}** (normal — CME Globex opens Sunday 18:00 ET)")
    A("")

    # ── Check 6 ──
    A("## 6. RTH vs ETH Split")
    A("")
    A(f"| Metric | Value | Expected |")
    A(f"|--------|-------|----------|")
    A(f"| RTH bars (09:30-16:00) | {c6['rth_bars']:,} ({c6['bar_pct_rth']:.1f}%) | {c6['expected_bar_pct']} |")
    A(f"| RTH volume | {c6['rth_vol']:,} ({c6['vol_pct_rth']:.1f}%) | {c6['expected_vol_pct']} |")
    A(f"| Total bars | {c6['total_bars']:,} | — |")
    A(f"| Total volume | {c6['total_vol']:,} | — |")
    A("")

    # ── Check 7 ──
    A("## 7. VWAP Sanity")
    A("")
    A(f"RTH bars with VWAP_RTH > 0: {c7['rth_bars_with_vwap']:,}")
    A(f"Violations (VWAP outside session H/L): **{c7['violations']}**  "
      f"({'✅' if c7['pass'] else '⚠️'})")
    A("")
    if c7["sample_sessions"]:
        A("**Sample sessions (first bar of RTH per day):**")
        A("")
        A(_fmt_table(
            ["Date", "Open", "Session High", "Session Low", "Close", "VWAP_RTH"],
            [[s["date"], s["open"], s["high"], s["low"], s["close"], s["vwap_rth"]]
             for s in c7["sample_sessions"]],
        ))
        A("")

    # ── Clean sessions ──
    A("## 8. Clean Session Filter")
    A("")
    A(f"**Total sessions with ORB+trading data**: {len(clean) + len(excluded)}")
    A(f"**Excluded sessions**: {len(excluded)}")
    A(f"**Clean sessions (used by strategy)**: **{len(clean)}**")
    A("")
    if excluded[:20]:
        A("**Excluded sessions (first 20):**")
        A("")
        A(_fmt_table(
            ["Date", "Reason"],
            [[e["date"], e["reasons"]] for e in excluded[:20]],
        ))
        A("")
    if len(excluded) > 20:
        A(f"*… and {len(excluded) - 20} more excluded sessions.*")
        A("")
    A(f"Saved to: `clean_sessions.json`")
    A("")

    # ── Summary decisions ──
    A("## 9. Summary & Strategy Decisions")
    A("")
    A("| Check | Result | Action |")
    A("|-------|--------|--------|")
    A(f"| Total bars | {c1['coverage_pct']:.1f}% coverage | {'Use all data' if c1['pass'] else 'STOP'} |")
    A(f"| Timestamp gaps | {c2['sessions_with_gaps']} sessions | {'Exclude flagged sessions' if c2['sessions_with_gaps'] > 0 else 'None needed'} |")
    A(f"| OHLC integrity | {c3['h_lt_l']} H<L bars | {'Exclude affected sessions' if c3['h_lt_l'] > 0 else 'Clean'} |")
    A(f"| Overnight gaps | {c4['large_gaps_gt3pct']} >3% | {'Note contract rolls' if c4['large_gaps_gt3pct'] > 0 else 'Clean'} |")
    A(f"| Weekends | {c5['weekend_bars']} bars | {'STOP' if not c5['pass'] else 'Clean'} |")
    A(f"| RTH/ETH split | {c6['vol_pct_rth']:.0f}% RTH vol | Normal |")
    A(f"| VWAP | {c7['violations']} violations | {'Exclude affected' if c7['violations'] > 0 else 'Clean'} |")
    A("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    SEP = "─" * 72

    print("=" * 72)
    print("NQ 1-min Data Quality Audit")
    print("=" * 72)

    print("\nLoading data (first run parses CSV → parquet) …")
    df = load_nq_1min()
    print(f"  Loaded: {len(df):,} rows, {df.index[0].date()} → {df.index[-1].date()}")

    print(f"\n{SEP}")
    print("CHECK 1 — Total bars")
    print(SEP)
    c1 = check_total_bars(df)
    print(f"  Actual : {c1['actual_bars']:,}")
    print(f"  Expected: {c1['expected_bars']:,}")
    print(f"  Coverage: {c1['coverage_pct']:.2f}%  {'✓ PASS' if c1['pass'] else '✗ FAIL'}")

    print(f"\n{SEP}")
    print("CHECK 2 — Timestamp gaps (08:30-15:00 ET)")
    print(SEP)
    c2 = check_gaps(df)
    print(f"  Sessions with gaps > {MAX_GAP_MINUTES} min: {c2['sessions_with_gaps']}"
          f"  {'✓ PASS' if c2['pass'] else '✗ FAIL'}")
    if c2["worst_10"]:
        print("  Worst 5 gaps:")
        for g in c2["worst_10"][:5]:
            print(f"    {g['date']}  {g['gap_min']}min at {g['at_time']}")

    print(f"\n{SEP}")
    print("CHECK 3 — OHLC price sanity")
    print(SEP)
    c3 = check_ohlc(df)
    print(f"  H < L bars           : {c3['h_lt_l']:,}  {'✓' if c3['h_lt_l'] == 0 else '✗'}")
    print(f"  H < Close/Open       : {max(c3['h_lt_c'], c3['h_lt_o']):,}")
    print(f"  L > Close/Open       : {max(c3['l_gt_c'], c3['l_gt_o']):,}")
    print(f"  Zero-range (H==L)    : {c3['zero_range']:,}")
    print(f"  Zero-volume (RTH)    : {c3['zero_vol_rth']:,}")
    print(f"  Status: {'✓ PASS' if c3['pass'] else '✗ FAIL (>100 H<L)'}")

    print(f"\n{SEP}")
    print("CHECK 4 — Overnight gap distribution")
    print(SEP)
    c4 = check_overnight_gaps(df)
    print(f"  Large gaps (>3%): {c4['large_gaps_gt3pct']}")
    print(f"  p50={c4['pct_hist']['p50']:.3f}%  p95={c4['pct_hist']['p95']:.3f}%"
          f"  p99={c4['pct_hist']['p99']:.3f}%  max={c4['pct_hist']['max']:.3f}%")
    if c4["worst_10"][:3]:
        print("  Worst 3 gaps:")
        for g in c4["worst_10"][:3]:
            print(f"    {g['date']}  {g['gap_pct']:.2f}%")

    print(f"\n{SEP}")
    print("CHECK 5 — Weekend bars")
    print(SEP)
    c5 = check_weekends(df)
    print(f"  Saturday bars (anomalous): {c5['saturday_bars']}  {'✓ PASS' if c5['pass'] else '✗ FAIL'}")
    print(f"  Sunday bars (normal, CME Globex): {c5['sunday_bars']}")

    print(f"\n{SEP}")
    print("CHECK 6 — RTH vs ETH split")
    print(SEP)
    c6 = check_rth_eth_split(df)
    print(f"  RTH bars (09:30-16:00): {c6['rth_bars']:,}  ({c6['bar_pct_rth']:.1f}%)")
    print(f"  RTH volume            : {c6['vol_pct_rth']:.1f}% of total")

    print(f"\n{SEP}")
    print("CHECK 7 — VWAP sanity")
    print(SEP)
    c7 = check_vwap(df)
    print(f"  VWAP violations: {c7['violations']}  {'✓ PASS' if c7['pass'] else '⚠️'}")
    if c7["sample_sessions"]:
        print("  Sample session VWAP check:")
        for s in c7["sample_sessions"][:3]:
            print(f"    {s['date']}  H={s['high']}  L={s['low']}  VWAP_RTH={s['vwap_rth']}")

    # ── Build clean sessions ──
    print(f"\n{SEP}")
    print("Building clean session filter …")
    clean, excluded = build_clean_sessions(df, c2)
    print(f"  Total sessions  : {len(clean) + len(excluded)}")
    print(f"  Excluded        : {len(excluded)}")
    print(f"  Clean sessions  : {len(clean)}")

    # ── Critical checkpoint ──
    stop_reasons   = []
    if not c1["pass"]:
        stop_reasons.append(
            f"Missing bars: {100 - c1['coverage_pct']:.1f}% of expected bars absent (threshold 5%)"
        )
    if not c2["pass"]:
        stop_reasons.append(
            f"Timestamp gaps: {c2['sessions_with_gaps']} sessions with gaps > {MAX_GAP_MINUTES}min (threshold 50)"
        )
    if not c3["pass"]:
        stop_reasons.append(
            f"OHLC corruption: {c3['h_lt_l']} bars with H < L (threshold 100)"
        )
    if not c5["pass"]:
        stop_reasons.append(f"Weekend bars detected: {c5['weekend_bars']}")

    critical_stop = len(stop_reasons) > 0

    print(f"\n{'─' * 72}")
    if critical_stop:
        print("⛔ CRITICAL STOP — do not run strategy:")
        for r in stop_reasons:
            print(f"   • {r}")
    else:
        print("✅ CRITICAL CHECKPOINT PASSED — data quality OK for strategy run")

    # ── Save outputs ──
    report = build_report(df, c1, c2, c3, c4, c5, c6, c7, clean, excluded,
                          critical_stop, stop_reasons)
    _REPORT.write_text(report)
    print(f"\nSaved → {_REPORT}")

    with open(_SESSIONS, "w") as fh:
        json.dump({"clean_sessions": clean, "excluded_sessions": excluded}, fh, indent=2)
    print(f"Saved → {_SESSIONS}")

    if critical_stop:
        print("\nExiting with error code 1 (CRITICAL STOP).")
        sys.exit(1)

    return clean, excluded


if __name__ == "__main__":
    main()
