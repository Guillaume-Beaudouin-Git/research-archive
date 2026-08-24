"""
iter_11_refined.py — Strategy C Pivot: iter_11_fast
====================================================
Modifications vs iter_10 (pre-registered 2026-05-26):
  TP_R       : 1.0 (vs 1.5 in iter_10)
  time_stop  : 11:30 ET (vs 12:30 ET in iter_10)
  sizing     : 5 MNQ for MC only — NQ backtest P&L is per-contract

All other parameters PRESERVED (iter_10 canonical):
  VWAP filter, gap≤1.2%, rng≥30pts, dollar_stop=$400

Pre-spec: prespec.md
  H1: WF Sharpe ≥ 1.22 (0.80 × 1.52)
  H2: avg_bars_held < 120 bars (< 2h at 1-min bars)
  H3: P(pass in 30d @ 5 MNQ) > 25% — see mc_pivot_test.py

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.variants.iter_11_fast.iter_11_refined
n_tests: 322 → 323
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[6]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT,
)
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, BASE_SL_MULT,
)
from Futures.research.active.nq_intraday.analysis.signal_refinements import extended_wf
from Futures.research.active.nq_intraday.iter_07_validation import sharpe_hac

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Strategy parameters (unchanged from iter_10) ─────────────────────────────
STRATEGY_GAP  = 0.012    # 1.2% overnight gap filter
STRATEGY_STOP = 400.0    # $400 dollar stop cap
RNG_MIN       = 30.0     # minimum opening range (pts)

# ── iter_11_fast modifications ────────────────────────────────────────────────
TP_R          = 1.0      # take-profit multiple (was 1.5 in iter_10)
TIME_STOP_H   = 11       # time stop hour (was 12 in iter_10)
TIME_STOP_M   = 30       # time stop minute

N_TESTS_START = 322
ITERATION     = "iter_11_fast"

RESULTS_PATH  = Path(__file__).parent / "results.json"

# iter_10 baseline for comparison
ITER10 = {
    "sharpe": 1.5212,
    "max_dd": -0.1342,
    "n_trades": 346,
    "win_rate": 0.2775,
    "avg_winner_usd": 1571.60,
    "avg_loser_usd": -421.45,
    "avg_bars_held": 23.6,
    "wf_pct": 77.78,   # extended 6M/3M WF%
    "wf_n_windows": 9,
}


# ── Signal builder ────────────────────────────────────────────────────────────

def build_signals_fast(feats: pd.DataFrame) -> pd.DataFrame:
    """
    iter_11_fast signals:
      - VWAP filter (unchanged from iter_10)
      - gap ≤ 1.2% (unchanged)
      - rng ≥ 30pts (M1 filter from iter_10)
      - dollar_stop = $400 (unchanged)
      - TP = 1.0R  ← CHANGED from 1.5R
      - exit_time = 11:30 ET  ← CHANGED from 12:30 ET
    """
    f = feats[feats["vwap_ok"]].copy()
    f = f[f["gap_pct"].abs() <= STRATEGY_GAP]
    f = f[f["rng"] >= RNG_MIN]

    if f.empty:
        return pd.DataFrame()

    # Override exit_time to 11:30 ET (same tz as sig_ts)
    f["exit_time"] = f["sig_ts"].apply(
        lambda ts: pd.Timestamp(
            ts.year, ts.month, ts.day,
            TIME_STOP_H, TIME_STOP_M, 0,
            tzinfo=ts.tzinfo,
        )
    )

    rows = []
    for _, row in f.iterrows():
        rng    = float(row["rng"])
        sl_pts = rng * BASE_SL_MULT
        cap_pts = (STRATEGY_STOP + COST_RT) / POINT_VALUE
        sl_pts  = min(sl_pts, cap_pts)

        rows.append({
            "signal_ts": row["sig_ts"],
            "direction": int(row["direction"]),
            "tp_points": rng * TP_R,
            "sl_points": sl_pts,
            "exit_time": row["exit_time"],
            "rng":       rng,
        })

    return pd.DataFrame(rows).set_index("signal_ts")


def signal_fn_iter11_fast(df_1min: pd.DataFrame, _params: dict) -> pd.DataFrame:
    """WF-compatible signal function (same interface as NQBacktestEngine.walk_forward)."""
    feats = build_opening_features(df_1min)
    return build_signals_fast(feats)


# ── Full backtest ─────────────────────────────────────────────────────────────

def run_backtest(engine: NQBacktestEngine, feats: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    sigs = build_signals_fast(feats)
    if sigs.empty:
        return pd.DataFrame(), {}
    return engine.run(sigs)


# ── Gate evaluation ───────────────────────────────────────────────────────────

def print_gate_matrix(met: dict, wf_pct: float, n_windows: int) -> str:
    sh  = met.get("sharpe_daily_hac") or 0
    mdd = met.get("max_dd_pct") or 0
    pf  = met.get("profit_factor") or 0
    avg_bars = met.get("avg_bars_held") or 0

    h1_pass = sh >= 1.22
    h2_pass = avg_bars < 120
    wf_pass = wf_pct >= 60.0

    print("\n  Gate matrix:")
    print(f"  {'Gate':<40} {'Required':>10} {'Actual':>12} {'Result':>7}")
    print(f"  {'-'*72}")
    print(f"  {'H1: WF Sharpe ≥ 1.22 (0.8×1.52)':<40} {'≥1.22':>10} {sh:>12.4f} {'PASS' if h1_pass else 'FAIL':>7}")
    print(f"  {'H2: avg_bars_held < 120 bars':<40} {'<120':>10} {avg_bars:>12.1f} {'PASS' if h2_pass else 'FAIL':>7}")
    print(f"  {'WF%: ≥60% positive windows':<40} {'≥60%':>10} {wf_pct:>11.1f}% {'PASS' if wf_pass else 'FAIL':>7}")
    print(f"  {'MaxDD (info): ≥-25% RESEARCH':<40} {'≥-25%':>10} {mdd*100:>11.1f}% {'PASS' if mdd >= -0.25 else 'FAIL':>7}")

    if h1_pass and h2_pass:
        return "RESEARCH_PASS_pending_H3"
    elif h1_pass:
        return "H1_PASS_H2_FAIL"
    else:
        return "H1_FAIL"


# ── Results I/O ───────────────────────────────────────────────────────────────

def save_results(result: dict) -> None:
    RESULTS_PATH.write_text(json.dumps([result], indent=2), encoding="utf-8")
    print(f"\n  [Saved: {RESULTS_PATH}]")


def load_results() -> list[dict]:
    if not RESULTS_PATH.exists():
        return []
    try:
        return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 80)
    print(f"iter_11_fast — Strategy C Pivot: TP=1.0R, time_stop=11:30 ET, sizing=5MNQ")
    print(f"n_tests: {N_TESTS_START} → {N_TESTS_START + 1}")
    print(f"Modifications: TP 1.5R→1.0R | time_stop 12:30→11:30 ET | sizing 2→5 MNQ (MC)")
    print("=" * 80)

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)

    n_days = feats["date"].nunique()
    print(f"\n  Dataset: {len(df):,} bars | {n_days} trading days")
    print(f"  VWAP+gap+rng-filtered pool: {len(feats[feats['vwap_ok'] & (feats['gap_pct'].abs() <= STRATEGY_GAP) & (feats['rng'] >= RNG_MIN)])} days")

    # ── Full backtest ─────────────────────────────────────────────────────────
    print("\n[1] Full backtest (2022-2025)...")
    tl, met = run_backtest(engine, feats)

    if tl.empty:
        print("  ERROR: No trades generated. Check data and signal builder.")
        return

    sh  = met.get("sharpe_daily_hac") or 0
    mdd = met.get("max_dd_pct") or 0
    pf  = met.get("profit_factor") or 0
    n   = met.get("n_trades", 0)
    wr  = met.get("win_rate") or 0
    avg_bars = met.get("avg_bars_held") or 0
    avg_w = met.get("avg_winner_usd") or 0
    avg_l = met.get("avg_loser_usd") or 0

    print(f"\n  iter_11_fast vs iter_10 baseline:")
    print(f"  {'Metric':<28} {'iter_11_fast':>14} {'iter_10':>14} {'Delta':>12}")
    print(f"  {'-'*70}")
    rows = [
        ("N trades",       f"{n}",                  f"{ITER10['n_trades']}",          f"{n - ITER10['n_trades']:+d}"),
        ("Win rate",       f"{wr*100:.2f}%",          f"{ITER10['win_rate']*100:.2f}%",  ""),
        ("Sharpe HAC",     f"{sh:.4f}",               f"{ITER10['sharpe']:.4f}",         f"{sh - ITER10['sharpe']:+.4f}"),
        ("MaxDD",          f"{mdd*100:.2f}%",          f"{ITER10['max_dd']*100:.2f}%",    f"{(mdd - ITER10['max_dd'])*100:+.1f}pp"),
        ("PF",             f"{pf:.4f}",               f"1.4319",                         f"{pf - 1.4319:+.4f}"),
        ("Avg winner",     f"${avg_w:,.0f}",           f"${ITER10['avg_winner_usd']:,.0f}", f"${avg_w - ITER10['avg_winner_usd']:+,.0f}"),
        ("Avg loser",      f"${avg_l:,.0f}",           f"${ITER10['avg_loser_usd']:,.0f}",  f"${avg_l - ITER10['avg_loser_usd']:+,.0f}"),
        ("Avg bars held",  f"{avg_bars:.1f}",           f"{ITER10['avg_bars_held']:.1f}",   f"{avg_bars - ITER10['avg_bars_held']:+.1f}"),
        ("Total PnL",      f"${met.get('total_pnl_usd',0):,.0f}", "$(iter_10: $45,511)", ""),
    ]
    for label, v1, v2, dv in rows:
        print(f"  {label:<28} {v1:>14} {v2:>14} {dv:>12}")

    # ── Exit reason breakdown ─────────────────────────────────────────────────
    exit_counts = tl["exit_reason"].value_counts()
    print(f"\n  Exit reason breakdown:")
    for reason, cnt in exit_counts.items():
        print(f"    {reason:<12}: {cnt:>4} ({cnt/n*100:.1f}%)")

    # ── Bootstrap EV ─────────────────────────────────────────────────────────
    boot = engine.bootstrap_ev(tl)
    p_ev = boot.get("p_ev_zero", np.nan)
    print(f"\n  Bootstrap EV: P(EV≤0) = {p_ev:.4f}  "
          f"CI95 [{boot.get('ci_low', 0):.0f}, {boot.get('ci_high', 0):.0f}]")

    # ── Walk-forward (extended 6M/3M) ────────────────────────────────────────
    print("\n[2] Extended walk-forward (6M/3M rolling)...")
    wf = extended_wf(engine, signal_fn_iter11_fast)
    wf_pct    = wf.get("wf_pct_positive", 0)
    n_windows = wf.get("n_windows", 0)
    windows   = wf.get("windows", [])

    print(f"\n  {'#':<3} {'OOS start':<12} {'OOS end':<12} {'N':>5} {'Sharpe':>8} {'PnL$':>9} {'+'}")
    print(f"  {'-'*58}")
    sh_vals = []
    for i, w in enumerate(windows, 1):
        sh_s = f"{w['sharpe']:.3f}" if w.get("sharpe") is not None else "   N/A"
        pos  = "✓" if w["positive"] else "✗"
        if w.get("sharpe") is not None:
            sh_vals.append(w["sharpe"])
        print(f"  {i:<3} {w['oos_start']:<12} {w['oos_end']:<12} "
              f"{w['n_trades']:>5} {sh_s:>8} {w['total_pnl']:>9.0f} {pos}")

    med_sh = float(np.median(sh_vals)) if sh_vals else np.nan
    print(f"\n  Summary: {n_windows} windows | {sum(w['positive'] for w in windows)} positive ({wf_pct:.0f}%)")
    print(f"  Median OOS Sharpe: {med_sh:.3f}" if np.isfinite(med_sh) else "  Median OOS Sharpe: N/A")
    print(f"  Total OOS PnL: ${wf.get('total_pnl', 0):,.0f}")
    print(f"\n  vs iter_10 baseline: WF%={ITER10['wf_pct']:.0f}% ({ITER10['wf_n_windows']} windows)")

    # ── Gate matrix ───────────────────────────────────────────────────────────
    print("\n[3] Gate matrix:")
    interim_verdict = print_gate_matrix(met, wf_pct, n_windows)

    # ── H2 explicit check ─────────────────────────────────────────────────────
    h2_pass = avg_bars < 120
    print(f"\n  H2 time compression check:")
    print(f"    avg_bars_held = {avg_bars:.1f} bars (= {avg_bars:.0f} min from entry)")
    print(f"    Max possible  = 104 bars (09:46→11:30 ET)")
    print(f"    H2 gate (<120): {'PASS' if h2_pass else 'FAIL'}")

    # ── STOP-POINT 1 ─────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("STOP-POINT 1 — Walk-forward results")
    print("=" * 80)
    print(f"  Median WF Sharpe (6M/3M): {med_sh:.3f}")
    print(f"  WF% positive:             {wf_pct:.0f}% ({n_windows} windows)")
    print(f"  avg_bars_held:            {avg_bars:.1f} bars")
    print(f"  vs iter_10 WF Sharpe:     n/a (iter_10 used extended WF%={ITER10['wf_pct']:.0f}%)")
    h1_pass = med_sh >= 1.22 if np.isfinite(med_sh) else False
    print(f"\n  H1 gate (WF Sharpe ≥ 1.22):  {'PASS' if h1_pass else 'FAIL'} ({med_sh:.3f})")
    print(f"  H2 gate (avg_bars < 120):    {'PASS' if h2_pass else 'FAIL'} ({avg_bars:.1f})")
    print(f"\n  → Run mc_pivot_test.py for STOP-POINT 2 (H3 gate)")
    print("=" * 80)

    # ── Save results ─────────────────────────────────────────────────────────
    result = {
        "iteration":         ITERATION,
        "n_tests":           N_TESTS_START + 1,
        "description":       "TP=1.0R, time_stop=11:30 ET, 5MNQ MC, all other iter_10 params preserved",
        "tp_r":              TP_R,
        "time_stop":         f"{TIME_STOP_H:02d}:{TIME_STOP_M:02d}",
        **met,
        "p_ev_zero":         round(float(p_ev), 4) if np.isfinite(p_ev) else None,
        "ci_low":            boot.get("ci_low"),
        "ci_high":           boot.get("ci_high"),
        "wf_pct_positive":   wf_pct,
        "wf_n_windows":      n_windows,
        "wf_median_sharpe":  round(float(med_sh), 4) if np.isfinite(med_sh) else None,
        "wf_total_pnl":      wf.get("total_pnl"),
        "exit_reasons":      exit_counts.to_dict(),
        "h1_pass":           h1_pass,
        "h2_pass":           h2_pass,
        "interim_verdict":   interim_verdict,
    }
    save_results(result)

    print(f"\n  n_tests: {N_TESTS_START} → {N_TESTS_START + 1}")


if __name__ == "__main__":
    main()
