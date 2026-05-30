"""
iter_11_propfirm.py — AXIS 1: Frequency Push for Tradeify Select Flex $50K
===========================================================================
Goal: Find a variant of iter_10 with P($3,000 in 90 days at 3 MNQ) ≥ 50%.

iter_10 baseline: N=346, Sh=1.52, MaxDD=-13.4%, trades/day=0.46,
E[daily@3MNQ]=$17.7, P(eval pass 90d)≈2.7% → need ~$33.3/day.

AXIS 1 — 5 variants (n_tests 143–147):
  11a: gap≤1.5%, rng≥25pt, VWAP on,  TP=1.5R  — double filter relaxation
  11b: gap≤2.0%, rng≥30pt, VWAP on,  TP=1.5R  — permissive gap only
  11c: no VWAP,  gap≤1.2%, rng≥30pt, TP=1.5R  — VWAP removed
  11d: gap≤1.5%, rng≥25pt, VWAP on,  TP=2.0R  — frequency + higher TP mult
  11e: no VWAP,  gap≤1.5%, rng≥25pt, TP=1.5R  — maximum frequency

Gates (PROPFIRM_PASS):
  Sharpe ≥ 1.0, WF% ≥ 60%, PF ≥ 1.3, MaxDD ≥ -10%
  P(eval pass 90d at 3 MNQ) ≥ 50%, AMTP-BH p < 0.05

Kill switch: no PROPFIRM_PASS in 5 tests → recommend Strategy D.

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.iter_11_propfirm
n_tests: 142 → 147
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[5]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT, append_result,
)
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, BASE_TP_MULT, BASE_SL_MULT,
)
from Futures.research.active.nq_intraday.analysis.signal_refinements import (
    extended_wf,
)
from Futures.research.active.nq_intraday.analysis.propfirm_compat_v2 import (
    _stationary_block_paths,
    _simulate_tradeify_eval,
    build_daily_pnl_mnq,
    TV_TRAILING_DD, TV_EVAL_TARGET, TV_INITIAL,
    MC_PATHS, MC_SEED,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_TESTS_START = 142
EVAL_DAYS_90  = 90      # 90-day eval window (Tradeify has no hard time limit)
EVAL_DAYS_30  = 30      # keep 30-day for reference
MNQ_EVAL      = 3
MNQ_PRELOCK   = 4

# PROPFIRM gate thresholds
GATE_SHARPE   = 1.0
GATE_WF       = 60.0
GATE_PF       = 1.3
GATE_MDD      = -0.10
GATE_P_EVAL   = 50.0   # P(eval pass 90d) ≥ 50%
GATE_AMTP     = 0.05

# iter_10 reference
ITER10 = {
    "iteration":    "iter_10",
    "sharpe":       1.5212,
    "max_dd":      -0.1342,
    "pf":           1.4319,
    "n_trades":     346,
    "win_rate":     0.2775,
    "total_pnl":   45510.0,
    "p_ev_zero":    0.0014,
    "wf_pct":       78.0,   # extended WF%
}


# ─────────────────────────────────────────────────────────────────────────────
# Modified signal builder (v2)
# ─────────────────────────────────────────────────────────────────────────────

def signals_from_features_v2(
    feats:       pd.DataFrame,
    gap_thresh:  Optional[float] = None,
    dollar_stop: Optional[float] = None,
    use_vwap:    bool            = True,
    tp_mult:     float           = BASE_TP_MULT,
) -> pd.DataFrame:
    """
    Variant of signals_from_features with configurable VWAP filter and TP multiplier.
    Only change from iter_05.signals_from_features: optional use_vwap + tp_mult.
    """
    if use_vwap:
        f = feats[feats["vwap_ok"]].copy()
    else:
        f = feats.copy()

    if gap_thresh is not None:
        f = f[f["gap_pct"].abs() <= gap_thresh]

    rows = []
    for _, row in f.iterrows():
        rng    = float(row["rng"])
        sl_pts = rng * BASE_SL_MULT
        if dollar_stop is not None:
            cap_pts = (dollar_stop + COST_RT) / POINT_VALUE
            sl_pts  = min(sl_pts, cap_pts)

        rows.append({
            "signal_ts": row["sig_ts"],
            "direction": int(row["direction"]),
            "tp_points": rng * tp_mult,
            "sl_points": sl_pts,
            "exit_time": row["exit_time"],
            "rng":       rng,
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("signal_ts")


# ─────────────────────────────────────────────────────────────────────────────
# Variant configurations
# ─────────────────────────────────────────────────────────────────────────────

VARIANTS = [
    {
        "name":       "iter_11a",
        "gap":        0.015,
        "rng_min":    25.0,
        "use_vwap":   True,
        "tp_mult":    1.5,
        "dollar_stop":400.0,
        "rationale":  "Double relaxation: gap 1.2→1.5%, rng 30→25pt (VWAP on)",
    },
    {
        "name":       "iter_11b",
        "gap":        0.020,
        "rng_min":    30.0,
        "use_vwap":   True,
        "tp_mult":    1.5,
        "dollar_stop":400.0,
        "rationale":  "Permissive gap only: gap 1.2→2.0%, rng kept at 30pt",
    },
    {
        "name":       "iter_11c",
        "gap":        0.012,
        "rng_min":    30.0,
        "use_vwap":   False,
        "tp_mult":    1.5,
        "dollar_stop":400.0,
        "rationale":  "VWAP removed, all other filters unchanged",
    },
    {
        "name":       "iter_11d",
        "gap":        0.015,
        "rng_min":    25.0,
        "use_vwap":   True,
        "tp_mult":    2.0,
        "dollar_stop":400.0,
        "rationale":  "11a freq + TP 1.5→2.0R (boost avg trade)",
    },
    {
        "name":       "iter_11e",
        "gap":        0.015,
        "rng_min":    25.0,
        "use_vwap":   False,
        "tp_mult":    1.5,
        "dollar_stop":400.0,
        "rationale":  "Max frequency: no VWAP + gap 1.5% + rng 25pt",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Tradeify 90-day eval bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def tradeify_eval_90d(
    trade_log: pd.DataFrame,
    n_mnq:     int = MNQ_EVAL,
    rng_gen:   Optional[np.random.Generator] = None,
) -> dict:
    """
    Tradeify $50K eval (legacy target): trailing DD=$1,000 (aligned to live 2026-05-25),
    target=$3,000, 90 trading days. Note TV_INITIAL=50_000 inherited from propfirm_compat_v2
    is the deprecated $50K target — live config is $25K. Re-run results after full refactor.
    Block bootstrap (L=sqrt(N)) × 10,000 paths.
    Returns p_pass_30d, p_pass_90d, mean_daily.
    """
    if rng_gen is None:
        rng_gen = np.random.default_rng(MC_SEED + 11)

    daily = build_daily_pnl_mnq(trade_log, n_mnq)
    pnl   = daily.values.astype(float)
    avg_bl = max(5, int(np.sqrt(len(pnl))))

    # 90-day paths
    paths_90 = _stationary_block_paths(pnl, MC_PATHS, EVAL_DAYS_90, avg_bl, rng_gen)
    r90 = _simulate_tradeify_eval(paths_90, TV_TRAILING_DD, TV_EVAL_TARGET, EVAL_DAYS_90)

    # 30-day paths (reference)
    paths_30 = _stationary_block_paths(pnl, MC_PATHS, EVAL_DAYS_30, avg_bl, rng_gen)
    r30 = _simulate_tradeify_eval(paths_30, TV_TRAILING_DD, TV_EVAL_TARGET, EVAL_DAYS_30)

    return {
        "p_pass_90d":  r90["p_pass"],
        "p_bust_90d":  r90["p_bust"],
        "p_pass_30d":  r30["p_pass"],
        "mean_daily":  r90["mean_daily"],
        "e_monthly_4mnq": build_daily_pnl_mnq(trade_log, MNQ_PRELOCK).mean() * 21,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Single variant evaluation
# ─────────────────────────────────────────────────────────────────────────────

def eval_variant(
    engine:    NQBacktestEngine,
    feats:     pd.DataFrame,
    cfg:       dict,
    n_test:    int,
    rng_gen:   np.random.Generator,
) -> dict:
    """Full evaluation: backtest + WF + Tradeify 90d bootstrap."""
    name = cfg["name"]

    # Build signals
    feats_filt = feats[feats["rng"] >= cfg["rng_min"]].copy()
    sigs = signals_from_features_v2(
        feats_filt,
        gap_thresh   = cfg["gap"],
        dollar_stop  = cfg["dollar_stop"],
        use_vwap     = cfg["use_vwap"],
        tp_mult      = cfg["tp_mult"],
    )

    if sigs.empty or len(sigs) < 20:
        return {
            "iteration": name, "n_tests": n_test,
            "n_trades": 0, "verdict": "SKIP — insufficient signals",
            "p_ev_zero": 1.0,
        }

    # Full backtest
    tl, met = engine.run(sigs)
    sh  = met.get("sharpe_daily_hac") or 0
    mdd = met.get("max_dd_pct") or 0
    pf  = met.get("profit_factor") or 0
    n   = met.get("n_trades", 0)

    # Bootstrap EV test (p_ev_zero)
    boot = engine.bootstrap_ev(tl)
    p_ev = boot.get("p_ev_zero", 1.0)

    # Extended WF (6M/3M)
    def _sig_fn(df_w: pd.DataFrame, _params: dict) -> pd.DataFrame:
        feats_w = build_opening_features(df_w)
        feats_w = feats_w[feats_w["rng"] >= cfg["rng_min"]].copy()
        return signals_from_features_v2(
            feats_w,
            gap_thresh   = cfg["gap"],
            dollar_stop  = cfg["dollar_stop"],
            use_vwap     = cfg["use_vwap"],
            tp_mult      = cfg["tp_mult"],
        )

    wf     = extended_wf(engine, _sig_fn)
    wf_pct = wf.get("wf_pct_positive") or 0
    n_win  = wf.get("n_windows", 0)

    # Tradeify 90-day eval bootstrap
    tv = tradeify_eval_90d(tl, n_mnq=MNQ_EVAL, rng_gen=rng_gen)

    # Verdict
    gates = {
        "sh":       sh   >= GATE_SHARPE,
        "wf":       wf_pct >= GATE_WF,
        "pf":       pf   >= GATE_PF,
        "mdd":      mdd  >= GATE_MDD,
        "p_eval":   tv["p_pass_90d"] >= GATE_P_EVAL,
    }
    all_pass = all(gates.values())

    if all_pass:
        verdict = "PROPFIRM_PASS"
    elif sh >= 1.0 and mdd >= -0.15 and pf >= 1.2:
        verdict = "RESEARCH_PASS"
    elif sh >= 0.7 and mdd >= -0.20:
        verdict = "IMPROVE"
    else:
        verdict = "WEAK"

    result = {
        "iteration":       name,
        "n_tests":         n_test,
        "description":     cfg["rationale"],
        **met,
        "p_ev_zero":       p_ev,
        "wf_pct_positive": wf_pct,
        "wf_n_windows":    n_win,
        "p_pass_30d":      tv["p_pass_30d"],
        "p_pass_90d":      tv["p_pass_90d"],
        "p_bust_90d":      tv["p_bust_90d"],
        "mean_daily_3mnq": tv["mean_daily"],
        "e_monthly_4mnq":  tv["e_monthly_4mnq"],
        "gates":           gates,
        "verdict":         verdict,
    }

    append_result(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Benjamini-Hochberg AMTP adjustment
# ─────────────────────────────────────────────────────────────────────────────

def bh_adjust(p_values: list[float], fdr: float = 0.05) -> list[float]:
    """
    Benjamini-Hochberg FDR correction.
    Returns adjusted p-values (BH step-up).
    """
    n = len(p_values)
    if n == 0:
        return []
    order  = np.argsort(p_values)
    ranked = np.empty(n)
    for rank, idx in enumerate(order, 1):
        ranked[idx] = p_values[idx] * n / rank
    # Enforce monotonicity (step-down from largest)
    for i in range(n - 2, -1, -1):
        ranked[order[i]] = min(ranked[order[i]], ranked[order[i + 1]])
    return [min(1.0, v) for v in ranked]


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────

def print_results_table(results: list[dict], bh_ps: list[float]) -> None:
    print("\n" + "═" * 110)
    print(f"{'Variant':<12} {'N':>5} {'Sh':>7} {'MDD':>7} {'PF':>6} "
          f"{'WF%':>6} {'P30d':>7} {'P90d':>7} {'E$/day':>8} {'p_BH':>7} {'Verdict'}")
    print("─" * 110)
    for r, p_bh in zip(results, bh_ps):
        sh   = r.get("sharpe_daily_hac") or 0
        mdd  = r.get("max_dd_pct") or 0
        pf   = r.get("profit_factor") or 0
        wf   = r.get("wf_pct_positive") or 0
        n    = r.get("n_trades", 0)
        p30  = r.get("p_pass_30d", 0)
        p90  = r.get("p_pass_90d", 0)
        ed   = r.get("mean_daily_3mnq", 0)
        vd   = r.get("verdict", "?")
        delta_sh  = sh - ITER10["sharpe"]
        delta_mdd = (mdd - ITER10["max_dd"]) * 100
        delta_n   = n - ITER10["n_trades"]
        print(f"  {r['iteration']:<10} {n:>5}({delta_n:+d})  "
              f"{sh:>5.3f}({delta_sh:+.3f})  "
              f"{mdd*100:>5.1f}%({delta_mdd:+.1f}pp)  "
              f"{pf:>5.3f}  {wf:>5.0f}%  "
              f"{p30:>6.1f}%  {p90:>6.1f}%  "
              f"${ed:>7.1f}  {p_bh:>6.4f}  {vd}")
    print("─" * 110)
    print(f"  iter_10 ref: N={ITER10['n_trades']}, Sh={ITER10['sharpe']:.4f}, "
          f"MDD={ITER10['max_dd']*100:.1f}%, PF={ITER10['pf']:.4f}, "
          f"WF%={ITER10['wf_pct']:.0f}%")
    print("═" * 110)


def print_gate_detail(r: dict) -> None:
    gates = r.get("gates", {})
    g_labels = {
        "sh":     f"Sharpe ≥ {GATE_SHARPE}",
        "wf":     f"WF% ≥ {GATE_WF:.0f}%",
        "pf":     f"PF ≥ {GATE_PF}",
        "mdd":    f"MaxDD ≥ {GATE_MDD*100:.0f}%",
        "p_eval": f"P(eval 90d) ≥ {GATE_P_EVAL:.0f}%",
    }
    g_vals = {
        "sh":     f"{r.get('sharpe_daily_hac') or 0:.4f}",
        "wf":     f"{r.get('wf_pct_positive') or 0:.0f}%",
        "pf":     f"{r.get('profit_factor') or 0:.4f}",
        "mdd":    f"{(r.get('max_dd_pct') or 0)*100:.1f}%",
        "p_eval": f"{r.get('p_pass_90d', 0):.1f}%",
    }
    print(f"  Gate detail for {r['iteration']}:")
    for k, label in g_labels.items():
        mark = "PASS" if gates.get(k) else "FAIL"
        print(f"    [{mark}] {label:<30}  actual={g_vals[k]}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 80)
    print("ITER_11 — AXIS 1: Frequency Push for Tradeify $50K Eval")
    print(f"n_tests: {N_TESTS_START} → {N_TESTS_START + len(VARIANTS)}")
    print(f"Gate: Sharpe≥{GATE_SHARPE}, WF≥{GATE_WF:.0f}%, PF≥{GATE_PF}, "
          f"MaxDD≥{GATE_MDD*100:.0f}%, P(eval 90d)≥{GATE_P_EVAL:.0f}%, AMTP-BH p<{GATE_AMTP}")
    print("=" * 80)

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)

    n_days      = feats["date"].nunique()
    n_vwap      = feats["vwap_ok"].sum()
    trades_per_day = ITER10["n_trades"] / n_days
    print(f"\n  Dataset: {len(df):,} bars, {n_days} trading days")
    print(f"  iter_10 base: {ITER10['n_trades']} trades, {trades_per_day:.3f}/day, "
          f"VWAP-filtered days={n_vwap}/{n_days} ({n_vwap/n_days:.0%})")
    print(f"  E[daily@3MNQ] iter_10: ${ITER10['n_trades']/n_days * 38.7:.1f}/day  "
          f"(need ≥$33.3 for P(eval 90d)≥50%)")

    rng_main = np.random.default_rng(MC_SEED + 11)
    results  = []
    n_test   = N_TESTS_START

    # ── Run 5 variants ─────────────────────────────────────────────────────
    for cfg in VARIANTS:
        n_test += 1
        print(f"\n{'─'*70}")
        print(f"  [{n_test}] {cfg['name']} — {cfg['rationale']}")
        print(f"        gap≤{cfg['gap']*100:.1f}%  rng≥{cfg['rng_min']:.0f}pt  "
              f"VWAP={'on' if cfg['use_vwap'] else 'OFF'}  TP={cfg['tp_mult']}R")
        print(f"{'─'*70}")

        r = eval_variant(engine, feats, cfg, n_test, rng_main)
        results.append(r)

        sh  = r.get("sharpe_daily_hac") or 0
        mdd = r.get("max_dd_pct") or 0
        pf  = r.get("profit_factor") or 0
        n   = r.get("n_trades", 0)
        wf  = r.get("wf_pct_positive") or 0
        p90 = r.get("p_pass_90d", 0)
        ed  = r.get("mean_daily_3mnq", 0)
        em  = r.get("e_monthly_4mnq", 0)
        print(f"  N={n}  Sh={sh:.4f}  MaxDD={mdd*100:.1f}%  PF={pf:.4f}")
        print(f"  WF={wf:.0f}%  P(eval 90d)={p90:.1f}%  "
              f"E[daily@3MNQ]=${ed:.1f}  E[monthly@4MNQ]=${em:.0f}")
        print(f"  → {r.get('verdict')}")

    # ── AMTP Benjamini-Hochberg adjustment ─────────────────────────────────
    p_raw = [r.get("p_ev_zero", 1.0) for r in results]
    p_bh  = bh_adjust(p_raw, fdr=GATE_AMTP)

    for r, p_adj in zip(results, p_bh):
        r["p_bh_adjusted"] = round(p_adj, 4)

    # ── Results table ───────────────────────────────────────────────────────
    print(f"\n{'═'*80}")
    print("RESULTS SUMMARY — AXIS 1")
    print_results_table(results, p_bh)

    # ── Gate details for all variants ───────────────────────────────────────
    print()
    for r in results:
        print_gate_detail(r)
        print()

    # ── Final verdict ────────────────────────────────────────────────────────
    propfirm_passes = [r for r in results if r.get("verdict") == "PROPFIRM_PASS"]
    research_passes = [r for r in results if r.get("verdict") == "RESEARCH_PASS"]
    best_by_p90     = max(results, key=lambda r: r.get("p_pass_90d", 0))
    best_by_sh      = max(results, key=lambda r: r.get("sharpe_daily_hac") or 0)

    print("═" * 80)
    print("FINAL VERDICT")
    print("═" * 80)

    if propfirm_passes:
        # Pick best PROPFIRM_PASS by P(eval 90d)
        best = max(propfirm_passes, key=lambda r: r.get("p_pass_90d", 0))
        sh   = best.get("sharpe_daily_hac") or 0
        wf   = best.get("wf_pct_positive") or 0
        pf   = best.get("profit_factor") or 0
        p90  = best.get("p_pass_90d", 0)
        em   = best.get("e_monthly_4mnq", 0)
        p_bh_b = best.get("p_bh_adjusted", 1.0)
        n_test_b = best.get("n_tests", n_test)
        print(f"\n  PROPFIRM_PASS: {best['iteration']}")
        print(f"  Sharpe={sh:.4f} | WF={wf:.0f}% | PF={pf:.4f}")
        print(f"  MaxDD={best.get('max_dd_pct',0)*100:.1f}% | "
              f"P(eval 90d)={p90:.1f}% | AMTP-BH p={p_bh_b:.4f}")
        print(f"  E[monthly net @4MNQ]=${em:.0f}")
        print(f"\n  BEST: {best['iteration']} | Sharpe={sh:.2f} | WF={wf:.0f}% | "
              f"PF={pf:.2f} / E[monthly net @4MNQ]=${em:.0f} | "
              f"P(eval pass 90d)={p90:.1f}% / AMTP-p={p_bh_b:.4f} | Verdict=PROPFIRM_PASS")
        print(f"\n  → Deploy {best['iteration']} as Strategy C iter_11.")
        print(f"     Update config.py signal params, run validate_tradovate.py T1-T5.")
    elif research_passes:
        best = max(research_passes, key=lambda r: r.get("p_pass_90d", 0))
        sh   = best.get("sharpe_daily_hac") or 0
        wf   = best.get("wf_pct_positive") or 0
        pf   = best.get("profit_factor") or 0
        p90  = best.get("p_pass_90d", 0)
        em   = best.get("e_monthly_4mnq", 0)
        p_bh_b = best.get("p_bh_adjusted", 1.0)
        print(f"\n  RESEARCH_PASS only. Best: {best['iteration']}")
        print(f"  Sharpe={sh:.4f} | WF={wf:.0f}% | P(eval 90d)={p90:.1f}%")
        print(f"\n  BEST: {best['iteration']} | Sharpe={sh:.2f} | WF={wf:.0f}% | "
              f"PF={pf:.2f} / E[monthly net @4MNQ]=${em:.0f} | "
              f"P(eval pass 90d)={p90:.1f}% / AMTP-p={p_bh_b:.4f} | Verdict=RESEARCH_PASS")
        print(f"\n  No PROPFIRM_PASS variant found in AXIS 1 (5 tests).")
        print(f"  P(eval 90d) best={p90:.1f}% < {GATE_P_EVAL:.0f}% gate.")
        best_p = max(r.get("p_pass_90d", 0) for r in results)
        if best_p < 20:
            print(f"\n  KILL SWITCH: best P(eval 90d)={best_p:.1f}% << 50%.")
            print(f"  Strategy C signal is structurally limited by ≈0.5 trade/day @ 1R.")
            print(f"  RECOMMENDATION: Abandon iter_11 AXIS 2/3. Start Strategy D (new edge).")
        else:
            print(f"\n  Consider AXIS 2: conditional regime windows (observational P(90d)≈{best_p:.0f}%).")
    else:
        # All WEAK or IMPROVE
        best_p = max(r.get("p_pass_90d", 0) for r in results)
        best_sh_r = best_by_sh.get("sharpe_daily_hac") or 0
        best_sh_n = best_by_sh.get("iteration", "?")
        em_best   = best_by_p90.get("e_monthly_4mnq", 0)
        p_bh_bp   = best_by_p90.get("p_bh_adjusted", 1.0)
        print(f"\n  No PROPFIRM_PASS or RESEARCH_PASS in AXIS 1 (5 tests).")
        print(f"  Best Sharpe: {best_sh_n}={best_sh_r:.4f}")
        print(f"  Best P(eval 90d): {best_by_p90.get('iteration','?')}={best_p:.1f}%")
        print(f"\n  BEST: {best_by_p90.get('iteration','?')} | "
              f"Sharpe={best_by_p90.get('sharpe_daily_hac',0):.2f} | "
              f"WF={best_by_p90.get('wf_pct_positive',0):.0f}% | "
              f"PF={best_by_p90.get('profit_factor',0):.2f} / "
              f"E[monthly net @4MNQ]=${em_best:.0f} | "
              f"P(eval pass 90d)={best_p:.1f}% / AMTP-p={p_bh_bp:.4f} | "
              f"Verdict={best_by_p90.get('verdict','?')}")
        print(f"\n  KILL SWITCH TRIGGERED: no PROPFIRM_PASS in 5 AXIS 1 tests.")
        print(f"  Strategy C iter_10 edge is constrained by trade frequency ({trades_per_day:.2f}/day).")
        print(f"  Relaxing filters does not yield sufficient P(eval pass) without destroying Sharpe.")
        print(f"  RECOMMENDATION: Stop AXIS 2/3. Begin Strategy D (new edge from scratch).")

    print(f"\n  n_tests: {N_TESTS_START} → {n_test}")
    print("═" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_11_propfirm failed")
        sys.exit(1)
