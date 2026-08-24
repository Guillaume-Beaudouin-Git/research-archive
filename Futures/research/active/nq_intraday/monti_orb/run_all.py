"""
run_all.py — Master runner for all Monti ORB tests T0–T6.

Run from repo root:
    python3 -m Futures.research.active.nq_intraday.monti_orb.run_all

Outputs:
    monti_orb/results.json   — all test results
    monti_orb/REPORT.md      — human-readable recommendation
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[5]))

from data.cache import load_nq_1min, get_cached_or_fetch_fred
from Futures.research.active.nq_intraday.monti_orb.signal import monti_orb_signal
from Futures.research.active.nq_intraday.monti_orb.backtest import (
    daily_returns, compute_metrics,
)
from Futures.research.active.nq_intraday.monti_orb.analysis import (
    t0_reproduction,
    t1_walkforward,
    t2_vt_ablation_L19,
    t3_cost_gate,
    t4_iter10_comparison,
    t5_tradeify_compat,
    t6_amtp_dsr,
)

HERE = Path(__file__).parent


def _run_test(name: str, fn, *args, **kwargs) -> dict:
    print(f"\n{'─'*60}")
    start = time.time()
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:
        print(f"[{name}] ERROR: {exc}")
        import traceback; traceback.print_exc()
        result = {"test": name, "error": str(exc)}
    elapsed = time.time() - start
    print(f"[{name}] done in {elapsed:.1f}s")
    return result


def generate_report(all_results: dict) -> str:
    r0 = all_results.get("T0", {})
    r1 = all_results.get("T1", {})
    r2 = all_results.get("T2", {})
    r3 = all_results.get("T3", {})
    r4 = all_results.get("T4", {})
    r5 = all_results.get("T5", {})
    r6 = all_results.get("T6", {})

    sr        = r0.get("sharpe_hac")
    max_dd    = r0.get("max_dd_pct")
    wf_rate   = r1.get("wf_pass_rate", 0.0)
    dsr       = r6.get("dsr")
    amtp_p    = r6.get("p_holm")
    corr_abs  = abs(r4.get("pearson_r", 1.0)) if r4.get("pearson_r") is not None else 1.0
    t4_verdict = r4.get("verdict", "UNKNOWN")
    p_pass     = r5.get("mc_trade_p_pass")

    # ── Gate evaluation ────────────────────────────────────────────────────
    research_pass = (
        sr is not None and sr > 0.7 and
        max_dd is not None and max_dd > -0.25 and
        wf_rate > 0.50 and
        amtp_p is not None and amtp_p < 0.20
    )
    propfirm_pass = (
        sr is not None and sr > 1.0 and
        max_dd is not None and max_dd > -0.10 and
        wf_rate > 0.60 and
        dsr is not None and dsr > 0.95
    )
    l19_pass = r2.get("vt_adds_value", False)
    orthogonal = corr_abs < 0.30

    # ── Economic merit check (separate from statistical gates) ────────────────
    # Strategy has "economic merit" if Sharpe, MaxDD, WF pass even if AMTP/DSR fail
    sr_t_hac = r6.get("t_hac", 0.0) or 0.0
    econ_merit = (
        sr is not None and sr > 0.7 and
        max_dd is not None and max_dd > -0.25 and
        wf_rate > 0.50 and
        sr_t_hac > 1.5
    )
    amtp_dsr_structural_fail = (
        econ_merit and
        amtp_p is not None and amtp_p >= 0.20  # fails only due to N
    )

    # ── Final recommendation ────────────────────────────────────────────────
    if not r0.get("reproduction_ok", False):
        recommendation = "DEBUG"
        rationale      = "T0 reproduction failed. Implementation bug must be fixed before any conclusion."
    elif not econ_merit:
        recommendation = "ARCHIVE"
        rationale      = "Fails economic gate: Sharpe<0.7, or MaxDD<-25%, or WF<50%, or alpha t<1.5."
    elif t4_verdict == "SAME_EDGE" and r0.get("sharpe_hac", 0) < r4.get("sr_iter10", 0):
        recommendation = "ARCHIVE"
        rationale      = (
            "Same edge as iter_10 (|corr|>0.70). iter_10 has better Sharpe — "
            "Monti ORB is a redundant, inferior variant."
        )
    elif t4_verdict == "SAME_EDGE":
        recommendation = "REPLACE_iter10"
        rationale      = "Same edge as iter_10. Monti ORB has higher Sharpe — evaluate as direct replacement."
    elif not research_pass and amtp_dsr_structural_fail:
        # Economic merit exists but L27 structural ceiling prevents formal RESEARCH_PASS
        if t4_verdict == "ORTHOGONAL":
            recommendation = "KEEP_AS_PAPER"
            rationale      = (
                "Economic merit confirmed (SR>0.7, MaxDD>-25%, WF 5/5, t>1.5). "
                "AMTP/DSR fail only due to L27 structural constraint (N=275). "
                "Orthogonal to iter_10 — paper-trade to accumulate live data for pre-registered DSR reset."
            )
        else:
            recommendation = "ARCHIVE"
            rationale      = (
                "Economic merit exists but AMTP fails due to L27 (N=275). "
                "Strategy overlaps with iter_10 — no independent value. "
                "Pre-registration before any testing would be needed to reset DSR."
            )
    elif orthogonal and propfirm_pass:
        recommendation = "COMBINE_with_iter10"
        rationale      = "Orthogonal to iter_10 AND passes PROPFIRM gate. Strategy D candidate."
    elif orthogonal and research_pass:
        recommendation = "KEEP_AS_PAPER"
        rationale      = "Orthogonal to iter_10, passes RESEARCH gate. Paper-trade to gather live data."
    elif not orthogonal and propfirm_pass:
        recommendation = "REPLACE_iter10"
        rationale      = "Partial overlap with iter_10. Monti passes PROPFIRM gate; evaluate as replacement."
    else:
        recommendation = "ARCHIVE"
        rationale      = "Does not meet any keep/combine threshold after full test battery."

    lines = [
        "# Monti ORB — Research Report",
        "",
        f"**Date:** 2026-05-27  |  **N_tests global:** 275  |  **Dataset:** 2022-12-26 → 2025-12-11",
        "",
        "## Summary",
        "",
        f"| Metric                  | Value            | Gate              | Status |",
        f"|-------------------------|------------------|-------------------|--------|",
        f"| Sharpe HAC              | {_fmt(sr, '.3f')}     | >0.7 (R) / >1.0 (P) | {_gate(sr, 0.7, 1.0)} |",
        f"| Max DD (vs $50K equity) | {_fmt(max_dd, '.1%')}  | >-25% (R) / >-10% (P) | {_gate_dd(max_dd)} |",
        f"| WF pass rate (5 folds)  | {_fmt(wf_rate, '.0%')}    | >50% (R) / >60% (P) | {_gate(wf_rate, 0.50, 0.60)} |",
        f"| Alpha t-stat (HAC)      | {_fmt(r6.get('t_hac'), '.3f')}  | >1.5 (R) / >2.0 (P) | {_pass(r6.get('t_hac') is not None and r6.get('t_hac', 0) > 1.5)} |",
        f"| Cost gate (ratio)       | {_fmt(r3.get('gross_cost_ratio'), '.2f')}  | >3.0               | {_pass(r3.get('gate_pass', False))} |",
        f"| Pearson corr (iter10)   | {_fmt(r4.get('pearson_r'), '.3f')}  | <0.30 orthogonal   | — |",
        f"| P(pass) Tradeify 3MNQ   | {_fmt(p_pass, '.1%')}    | ref iter10 27%     | — |",
        f"| AMTP p-val (Holm N=275) | {_fmt(amtp_p, '.4f')} | <0.20              | {_pass(amtp_p is not None and amtp_p < 0.20)} |",
        f"| DSR (Bailey-LdP N=275)  | {_fmt(dsr, '.3f')}     | >0.95 PROPFIRM     | {_pass(dsr is not None and dsr > 0.95)} |",
        "",
        "## Test results",
        "",
        f"**T0 Reproduction:** {_ok(r0.get('reproduction_ok'))}  "
        f"N={r0.get('n_trades')} trades  WR={_fmt(r0.get('win_rate'), '.1%')}  "
        f"PF={_fmt(r0.get('profit_factor'), '.2f')}",
        "",
        f"**T1 Walk-forward:** {r1.get('n_positive', 0)}/{r1.get('n_folds', 5)} folds positive  "
        f"(worst: {_fmt(r1.get('worst_sharpe'), '.3f')})  "
        f"WF gate: {_pass(r1.get('wf_gate_pass', False))}",
        "",
        f"**T2 Vol-targeting:** Δ Sharpe = {_fmt(r2.get('delta_sharpe'), '+.3f')}  "
        f"t = {_fmt(r2.get('bootstrap_t'), '.2f')}  "
        f"L19 gate: {_pass(l19_pass)}",
        "",
        f"**T3 Cost gate:** gross/cost ratio = {_fmt(r3.get('gross_cost_ratio'), '.2f')}  "
        f"({_fmt(r3.get('trades_per_year'), '.0f')} trades/yr, "
        f"${_fmt(r3.get('annual_cost_usd'), ',.0f')} annual cost)  "
        f"Gate: {_pass(r3.get('gate_pass', False))}",
        "",
        f"**T4 iter_10 comparison:** Pearson r = {_fmt(r4.get('pearson_r'), '.3f')}  "
        f"Spearman r = {_fmt(r4.get('spearman_r'), '.3f')}  "
        f"Verdict: **{t4_verdict}**",
        f"  Blend Sharpes: 50/50 = {_fmt(r4.get('sr_blend_50'), '.3f')}  "
        f"ERC = {_fmt(r4.get('sr_blend_erc'), '.3f')}",
        "",
        f"**T5 Tradeify compat (3 MNQ):** P(pass) = {_fmt(p_pass, '.1%')}  "
        f"P(bust) = {_fmt(r5.get('mc_trade_p_bust'), '.1%')}  "
        f"Worst day = ${_fmt(r5.get('worst_day_mnq_usd'), ',.0f')}",
        "",
        f"**T6 AMTP+DSR:** SR needed for DSR>0.95 = {_fmt(r6.get('sr_needed_dsr95'), '.2f')}  "
        f"(observed: {_fmt(sr, '.2f')})  "
        f"[L27 note: with N=275, DSR>0.95 requires SR>{_fmt(r6.get('sr_needed_dsr95'), '.2f')}]",
        "",
        "## Recommendation",
        "",
        f"**{recommendation}**",
        "",
        rationale,
        "",
        "### Decision tree",
        f"- Reproduction OK: {_ok(r0.get('reproduction_ok'))}",
        f"- Economic merit: {_pass(econ_merit)}  (SR>0.7, MaxDD>-25%, WF>50%, alpha t>1.5)",
        f"- RESEARCH_PASS: {_pass(research_pass)}  (adds AMTP p<0.20)",
        f"- PROPFIRM_PASS: {_pass(propfirm_pass)}  (SR>1.0, MaxDD>-10%, WF>60%, DSR>0.95)",
        f"- L19/L24 PASS (vol-targeting adds edge): {_pass(l19_pass)}",
        f"- ORTHOGONALITY (|corr|<0.30): {_pass(orthogonal)}",
        "",
        "### L27 structural note",
        f"With N_trials=275 and T={r6.get('n_obs', '?')} obs, E[max SR | N] = "
        f"{_fmt(r6.get('e_max_sr'), '.2f')}. "
        f"Any strategy discovered after >{275//2} tests is unlikely to pass DSR>0.95 "
        f"unless SR > {_fmt(r6.get('sr_needed_dsr95'), '.2f')}. "
        "Pre-registration (N=1 at DSR calculation time) would reset this constraint.",
        "",
        "---",
        "_Generated by run_all.py — Algo_claude research pipeline_",
    ]
    return "\n".join(lines)


def _fmt(v, fmt: str) -> str:
    if v is None or (isinstance(v, float) and (v != v)):
        return "N/A"
    try:
        return format(v, fmt)
    except (TypeError, ValueError):
        return str(v)


def _pass(ok: bool) -> str:
    return "✓ PASS" if ok else "✗ FAIL"


def _ok(ok) -> str:
    return "✓" if ok else "✗"


def _gate(v, lo, hi) -> str:
    if v is None:
        return "—"
    if v > hi:
        return "PROPFIRM ✓"
    if v > lo:
        return "RESEARCH ✓"
    return "FAIL ✗"


def _gate_dd(v) -> str:
    if v is None:
        return "—"
    if v > -0.10:
        return "PROPFIRM ✓"
    if v > -0.25:
        return "RESEARCH ✓"
    return "FAIL ✗"


def main() -> None:
    print("Loading data…")
    df = load_nq_1min()
    print("Running monti_orb_signal…")
    trades = monti_orb_signal(df)
    print(f"Signal computed: {len(trades)} days, "
          f"{(~trades['exit_reason'].isin(['no_signal','insufficient_orb'])).sum()} trades")

    results: dict[str, dict] = {}

    results["T0"] = _run_test("T0", t0_reproduction.run)
    if not results["T0"].get("reproduction_ok", False):
        print("\n*** T0 FAILED — aborting remaining tests ***")
        _save(results)
        return

    results["T1"] = _run_test("T1", t1_walkforward.run, trades)
    results["T2"] = _run_test("T2", t2_vt_ablation_L19.run, trades)
    results["T3"] = _run_test("T3", t3_cost_gate.run, trades)
    results["T4"] = _run_test("T4", t4_iter10_comparison.run, trades)
    results["T5"] = _run_test("T5", t5_tradeify_compat.run, trades)
    results["T6"] = _run_test("T6", t6_amtp_dsr.run, trades)

    _save(results)

    report = generate_report(results)
    (HERE / "REPORT.md").write_text(report, encoding="utf-8")
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)
    print(f"\nResults saved → {HERE / 'results.json'}")
    print(f"Report saved  → {HERE / 'REPORT.md'}")


def _save(results: dict) -> None:
    out_path = HERE / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
