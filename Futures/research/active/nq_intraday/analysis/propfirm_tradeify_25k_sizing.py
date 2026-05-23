"""
propfirm_tradeify_25k_sizing.py — Step 0 v3: Tradeify $25K sizing decision
===========================================================================
CORRECTED: trailing_dd = $1,000 (confirmed from Tradeify checkout screenshot),
           reset_fee = $65 one-time (code MAY), no time limit on eval confirmed.

Strategy C iter_10 (N=346, gap≤1.2%, rng≥30pt, $400 SL cap)
Tests two sizing scenarios: 2 MNQ and 3 MNQ.

Decision gates:
  - 3 MNQ if P(pass per attempt, no time limit) ≥ 40%
  - 2 MNQ if 3 MNQ < 40% but 2 MNQ ≥ 50%
  - Reevaluate if neither gate satisfied

Per-scenario outputs:
  • Historical trailing DD peak vs $1,000 limit
  • Bootstrap: P(pass), P(bust), E[attempts], E[total eval cost] = E[attempts] × $65
  • E[monthly post-funded] = mean_daily × 21 × 0.90
  • Worst-60d post-lock DD vs $1,000 floor budget
  • WF fold survival (quarterly OOS, fresh $25K per fold)

Output: Futures/live/strategy_c_live/SIZING_DECISION.md
Run:    /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.propfirm_tradeify_25k_sizing
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
from Futures.research.active.nq_intraday.analysis.propfirm_compat_v2 import (
    _stationary_block_paths, MC_PATHS, MC_SEED,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

# ─── Tradeify Select Flex $25K — CONFIRMED rules (checkout screenshot) ────────
TV_INITIAL       = 25_000.0
TV_TRAIL_DD      = 1_000.0    # EOD trailing from equity peak — CONFIRMED (was 1,500 in v1)
TV_LOCK_BAL      = 26_100.0   # lock trigger balance
TV_FLOOR         = 25_100.0   # permanent post-lock floor
TV_EVAL_TGT      = 1_500.0    # eval target (6% of 25K)
TV_POSTLOCK_DAYS = 60
PAYOUT_SPLIT     = 0.90

# ─── Fee model (corrected) ───────────────────────────────────────────────────
RESET_FEE = 65.0    # one-time reset (code MAY, 40% off ~$109), expires May 31

# ─── Bootstrap params ────────────────────────────────────────────────────────
MAX_DAYS_EVAL = 1_000   # no time limit — simulate until pass or bust (capped at 1000d)

# ─── iter_10 signal params ───────────────────────────────────────────────────
GAP_THRESH  = 0.012
RNG_MIN     = 30.0
DOLLAR_STOP = 400.0

# ─── MNQ/NQ scaling ──────────────────────────────────────────────────────────
MNQ_PV   = 2.0
MNQ_COST = 2.15
NQ_PV    = 20.0
NQ_COST  = 19.0

# ─── Sizing scenarios (v3: 2 MNQ and 3 MNQ only) ────────────────────────────
SIZINGS = {"2 MNQ": 2, "3 MNQ": 3}

# ─── Decision gates ──────────────────────────────────────────────────────────
GATE_3MNQ = 40.0    # keep 3 MNQ if P(pass) ≥ 40%
GATE_2MNQ = 50.0    # degrade to 2 MNQ if P(pass) ≥ 50% (and 3 MNQ < 40%)


# ─────────────────────────────────────────────────────────────────────────────
# P&L scaling
# ─────────────────────────────────────────────────────────────────────────────

def scale_to_mnq(nq_pnl_usd: float, n_mnq: int) -> float:
    nq_pts = (nq_pnl_usd + NQ_COST) / NQ_PV
    return nq_pts * MNQ_PV * n_mnq - MNQ_COST * n_mnq


def build_daily_mnq(tl: pd.DataFrame, n_mnq: int) -> pd.Series:
    t = tl.copy()
    t["date"] = pd.to_datetime(t["entry_ts"]).dt.normalize()
    t["pnl"]  = t["pnl_usd"].apply(lambda x: scale_to_mnq(x, n_mnq))
    d = t.groupby("date")["pnl"].sum()
    all_dates = pd.bdate_range(t["date"].min(), t["date"].max())
    return d.reindex(all_dates.normalize(), fill_value=0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Historical trailing DD (deterministic, full backtest)
# ─────────────────────────────────────────────────────────────────────────────

def historical_trailing_dd(daily: pd.Series) -> dict:
    """Simulate $25K account through full daily P&L series. EOD trailing DD from peak."""
    balance   = TV_INITIAL
    peak      = TV_INITIAL
    max_trail = 0.0
    bust_day  = None

    for i, pnl in enumerate(daily):
        balance  += pnl
        peak      = max(peak, balance)
        trail     = peak - balance
        max_trail = max(max_trail, trail)
        if trail >= TV_TRAIL_DD and bust_day is None:
            bust_day = i

    cushion = TV_TRAIL_DD - max_trail
    return {
        "max_trail_dd_usd": round(max_trail, 0),
        "max_trail_dd_pct": round(max_trail / TV_TRAIL_DD * 100, 1),
        "cushion_usd":      round(cushion, 0),
        "hist_bust":        bust_day is not None,
        "bust_day":         bust_day,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap: no-time-limit eval simulation
# ─────────────────────────────────────────────────────────────────────────────

def simulate_eval_no_limit(daily: pd.Series, rng: np.random.Generator) -> dict:
    """
    Eval simulation with no time limit (Tradeify confirmed: no 90-day window).
    Each path runs until cumsum ≥ TV_EVAL_TGT (pass) OR trailing_dd ≥ TV_TRAIL_DD (bust).
    Capped at MAX_DAYS_EVAL=1000 trading days (~4 years).
    """
    pnl_arr = daily.values.astype(float)
    avg_bl  = max(5, int(np.sqrt(len(pnl_arr))))
    paths   = _stationary_block_paths(pnl_arr, MC_PATHS, MAX_DAYS_EVAL, avg_bl, rng)
    n_paths, n_days = paths.shape

    cum   = np.cumsum(paths, axis=1)
    peak  = np.maximum.accumulate(np.maximum(cum, 0), axis=1)
    trail = peak - cum

    bust_mat = trail >= TV_TRAIL_DD
    tgt_mat  = cum   >= TV_EVAL_TGT

    bust_mask = bust_mat.any(axis=1)
    tgt_mask  = tgt_mat.any(axis=1)

    first_bust = np.where(bust_mask, bust_mat.argmax(axis=1), n_days)
    first_tgt  = np.where(tgt_mask,  tgt_mat.argmax(axis=1),  n_days)

    pass_mask    = tgt_mask  & (first_tgt < first_bust)
    bust_only    = bust_mask & ~pass_mask
    timeout_mask = ~bust_mask & ~tgt_mask

    t_days   = first_tgt[pass_mask] + 1
    med_days = float(np.median(t_days)) if pass_mask.sum() > 0 else float(n_days)

    p_pass = float(pass_mask.sum()) / n_paths
    e_attempts        = 1.0 / max(p_pass, 1e-6)
    e_total_eval_cost = e_attempts * RESET_FEE

    return {
        "p_pass":            round(p_pass * 100, 1),
        "p_bust":            round(float(bust_only.sum()) / n_paths * 100, 1),
        "p_timeout":         round(float(timeout_mask.sum()) / n_paths * 100, 1),
        "med_days":          round(med_days, 0),
        "e_attempts":        round(e_attempts, 1),
        "e_total_eval_cost": round(e_total_eval_cost, 0),
        "mean_daily":        float(pnl_arr.mean()),
    }


def simulate_postlock_bs(daily: pd.Series, rng: np.random.Generator) -> dict:
    """Post-lock 60d bootstrap: floor budget $1,000 from lock trigger ($26,100 → $25,100)."""
    pnl_arr    = daily.values.astype(float)
    avg_bl     = max(5, int(np.sqrt(len(pnl_arr))))
    paths      = _stationary_block_paths(pnl_arr, MC_PATHS, TV_POSTLOCK_DAYS, avg_bl, rng)
    n_paths, _ = paths.shape
    cum        = np.cumsum(paths, axis=1)
    floor_dd   = TV_LOCK_BAL - TV_FLOOR   # $1,000
    bust_mask  = (cum < -floor_dd).any(axis=1)
    mean_daily = float(pnl_arr.mean())
    return {
        "p_bust_60d":   round(float(bust_mask.sum()) / n_paths * 100, 1),
        "mean_daily":   mean_daily,
        "mean_monthly": round(mean_daily * 21 * PAYOUT_SPLIT, 0),
    }


def worst_60d_postlock(daily: pd.Series) -> dict:
    pnl   = daily.values.astype(float)
    n     = TV_POSTLOCK_DAYS
    floor = TV_LOCK_BAL - TV_FLOOR   # $1,000
    if len(pnl) < n:
        return {"worst_dd": float(np.cumsum(pnl).min()), "outcome": "INSUFFICIENT"}
    wins_dd  = np.array([np.cumsum(pnl[i:i+n]).min() for i in range(len(pnl) - n + 1)])
    worst_dd = float(wins_dd.min())
    return {
        "worst_dd": round(worst_dd, 0),
        "outcome":  "PASS" if worst_dd > -floor else "BUST",
    }


# ─────────────────────────────────────────────────────────────────────────────
# WF fold survival (quarterly split of full backtest)
# ─────────────────────────────────────────────────────────────────────────────

def wf_fold_survival(tl: pd.DataFrame, n_mnq: int) -> list:
    t = tl.copy()
    t["date"] = pd.to_datetime(t["entry_ts"]).dt.normalize()
    t["qtr"]  = pd.PeriodIndex(t["date"], freq="Q")

    folds = []
    for q in sorted(t["qtr"].unique()):
        fold_tl = t[t["qtr"] == q]
        if len(fold_tl) < 2:
            continue
        daily = build_daily_mnq(fold_tl, n_mnq)
        h = historical_trailing_dd(daily)
        folds.append({
            "period":       str(q),
            "n_trades":     len(fold_tl),
            "pnl_usd":      round(float(daily.sum()), 0),
            "max_trail_dd": h["max_trail_dd_usd"],
            "cushion":      h["cushion_usd"],
            "survive":      not h["hist_bust"],
        })
    return folds


def max_loss_per_trade(n_mnq: int) -> float:
    return abs(scale_to_mnq(-(DOLLAR_STOP + NQ_COST), n_mnq))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> dict:
    print("=" * 100)
    print("STEP 0 v3 — TRADEIFY SELECT FLEX $25K SIZING DECISION  (Strategy C iter_10, N=346)")
    print("=" * 100)
    print(f"  Rules (CONFIRMED): trailing DD ${TV_TRAIL_DD:,.0f} EOD | eval target ${TV_EVAL_TGT:,.0f} (6%) | "
          f"no time limit | lock @ ${TV_LOCK_BAL:,} | floor ${TV_FLOOR:,} | 90/10 split")
    print(f"  Fee: ${RESET_FEE:.0f} one-time reset (code MAY)  |  Split: 90/10")
    print(f"  Decision gates: 3 MNQ if P(pass)≥{GATE_3MNQ:.0f}% | "
          f"2 MNQ if 3MNQ<{GATE_3MNQ:.0f}% AND 2MNQ≥{GATE_2MNQ:.0f}%")
    print()

    df      = load_nq_1min()
    engine  = NQBacktestEngine(df)
    feats   = build_opening_features(engine.rth)
    feats_f = feats[feats["rng"] >= RNG_MIN].copy()
    sigs    = signals_from_features(feats_f, gap_thresh=GAP_THRESH, dollar_stop=DOLLAR_STOP)
    tl, m   = engine.run(sigs)

    print(f"  iter_10: {len(tl)} trades  Sharpe_HAC={m.get('sharpe_daily_hac', 0):.4f}  "
          f"MaxDD={m.get('max_dd_pct', 0):.1%}  "
          f"[{pd.to_datetime(tl['entry_ts'].min()).date()} → "
          f"{pd.to_datetime(tl['entry_ts'].max()).date()}]")
    print()

    all_results: dict = {}
    for label, n_mnq in SIZINGS.items():
        print(f"  Running {label}...")
        daily   = build_daily_mnq(tl, n_mnq)
        hist_dd = historical_trailing_dd(daily)
        max_sl  = max_loss_per_trade(n_mnq)

        rng_e = np.random.default_rng(MC_SEED + n_mnq * 100)
        rng_k = np.random.default_rng(MC_SEED + n_mnq * 100 + 1)

        bs_eval = simulate_eval_no_limit(daily, rng_e)
        bs_post = simulate_postlock_bs(daily, rng_k)
        ww      = worst_60d_postlock(daily)
        folds   = wf_fold_survival(tl, n_mnq)

        all_results[label] = {
            "n_mnq": n_mnq, "max_sl": max_sl, "daily": daily,
            "hist": hist_dd, "eval": bs_eval, "post": bs_post,
            "ww": ww, "folds": folds,
        }

    # ── TABLE 1 — Historical trailing DD ──────────────────────────────────────
    print("\n" + "=" * 100)
    print(f"  TABLE 1 — HISTORICAL TRAILING DD (full backtest, $25K initial, limit ${TV_TRAIL_DD:,.0f})")
    print("=" * 100)
    print(f"  {'Sizing':>6} {'MNQ':>4} {'MaxSL/tr':>9} {'MaxTrailDD':>12} {'%Limit':>8} "
          f"{'Cushion':>10} {'HistBust':>9}")
    print(f"  {'─'*67}")
    for label, n_mnq in SIZINGS.items():
        r = all_results[label]
        h = r["hist"]
        print(f"  {label:>6} {n_mnq:>4}  ${r['max_sl']:>7.0f}   "
              f"${h['max_trail_dd_usd']:>9,.0f}   "
              f"{h['max_trail_dd_pct']:>6.1f}%   "
              f"${h['cushion_usd']:>8,.0f}   "
              f"{'YES ✗' if h['hist_bust'] else 'no ✓':>9}")

    # ── TABLE 2 — Bootstrap eval (no time limit) ──────────────────────────────
    print("\n" + "=" * 100)
    print(f"  TABLE 2 — BOOTSTRAP EVAL (10,000 paths, no time limit, max_days={MAX_DAYS_EVAL})")
    print("=" * 100)
    print(f"  {'Sizing':>6} {'P(pass)':>8} {'P(bust)':>8} {'P(timeout)':>11} {'MedDays':>8} "
          f"{'E[atts]':>8} {'E[eval$]':>10} {'E[mo×90%]':>11}")
    print(f"  {'─'*80}")
    for label, n_mnq in SIZINGS.items():
        r = all_results[label]
        e = r["eval"]
        p = r["post"]
        print(f"  {label:>6}  {e['p_pass']:>6.1f}%  {e['p_bust']:>6.1f}%  "
              f"{e['p_timeout']:>9.1f}%  "
              f"{e['med_days']:>7.0f}d  "
              f"{e['e_attempts']:>7.1f}×  "
              f"  ${e['e_total_eval_cost']:>7,.0f}  "
              f"  ${p['mean_monthly']:>+9,.0f}")

    # ── TABLE 3 — WF fold survival ────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("  TABLE 3 — WF FOLD SURVIVAL (quarterly, fresh $25K challenge per fold)")
    print("=" * 100)
    for label, n_mnq in SIZINGS.items():
        folds  = all_results[label]["folds"]
        n_bust = sum(1 for f in folds if not f["survive"])
        print(f"\n  {label}  —  {n_bust}/{len(folds)} folds bust")
        print(f"    {'Period':>8} {'Trades':>7} {'P&L':>8} {'MaxTrailDD':>12} {'Cushion':>10} {'Result':>8}")
        print(f"    {'─'*58}")
        for f in folds:
            r_str = "BUST ✗" if not f["survive"] else "PASS ✓"
            print(f"    {f['period']:>8}  {f['n_trades']:>6}  ${f['pnl_usd']:>+7,.0f}  "
                  f"${f['max_trail_dd']:>10,.0f}  ${f['cushion']:>8,.0f}  {r_str}")

    # ── DECISION ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print(f"  DECISION (gates: 3 MNQ if P(pass)≥{GATE_3MNQ:.0f}%,"
          f" 2 MNQ if 3MNQ<{GATE_3MNQ:.0f}% AND 2MNQ≥{GATE_2MNQ:.0f}%)")
    print("=" * 100)

    r3 = all_results["3 MNQ"]
    r2 = all_results["2 MNQ"]
    p3 = r3["eval"]["p_pass"]
    p2 = r2["eval"]["p_pass"]

    if p3 >= GATE_3MNQ:
        decision_label = "3 MNQ"
    elif p2 >= GATE_2MNQ:
        decision_label = "2 MNQ"
    else:
        decision_label = None

    if decision_label:
        dr = all_results[decision_label]
        e  = dr["eval"]
        p  = dr["post"]
        h  = dr["hist"]
        ww = dr["ww"]
        folds        = dr["folds"]
        n_fold_bust  = sum(1 for f in folds if not f["survive"])
        gate_used    = GATE_3MNQ if decision_label == "3 MNQ" else GATE_2MNQ
        print(f"\n  ► DECISION: {decision_label}")
        print(f"     P(pass per attempt):     {e['p_pass']:.1f}%  (gate ≥{gate_used:.0f}% → ✓)")
        print(f"     P(bust per attempt):     {e['p_bust']:.1f}%")
        print(f"     P(timeout >{MAX_DAYS_EVAL}d):     {e['p_timeout']:.1f}%")
        print(f"     Median days to pass:     {e['med_days']:.0f}d")
        print(f"     E[attempts to funded]:   {e['e_attempts']:.1f}×")
        print(f"     E[total eval cost]:      ${e['e_total_eval_cost']:,.0f}  "
              f"({e['e_attempts']:.1f}× × ${RESET_FEE:.0f}/reset)")
        print(f"     MaxSL/trade:             ${dr['max_sl']:.0f}")
        print(f"     Max hist trail DD:       ${h['max_trail_dd_usd']:,.0f} / ${TV_TRAIL_DD:,.0f}  "
              f"({h['max_trail_dd_pct']:.0f}% utilization)")
        print(f"     E[monthly post-funded]:  ${p['mean_monthly']:+,.0f}")
        print(f"     Worst 60d post-lock DD:  ${ww['worst_dd']:+,.0f}  "
              f"(floor budget −${TV_LOCK_BAL - TV_FLOOR:,.0f}) → {ww['outcome']}")
        print(f"     WF fold survival:        {len(folds) - n_fold_bust}/{len(folds)} pass")
    else:
        print(f"\n  ► REEVALUATE — neither gate satisfied")
        print(f"     3 MNQ P(pass): {p3:.1f}%  (gate ≥{GATE_3MNQ:.0f}% → FAIL)")
        print(f"     2 MNQ P(pass): {p2:.1f}%  (gate ≥{GATE_2MNQ:.0f}% → FAIL)")
        print(f"     Trailing DD $1,000 is very tight. Consider: 1 MNQ or alternative propfirm.")

    print("\n" + "=" * 100)

    _write_md(all_results, decision_label)
    out = Path(__file__).parents[4] / "live" / "strategy_c_live" / "SIZING_DECISION.md"
    print(f"\n  → SIZING_DECISION.md v3 written: {out}")

    return all_results


# ─────────────────────────────────────────────────────────────────────────────
# Markdown output
# ─────────────────────────────────────────────────────────────────────────────

def _write_md(results: dict, decision_label: str | None) -> None:
    lines = [
        "# SIZING_DECISION.md — Strategy C / Tradeify Select Flex $25K",
        "*Auto-generated by propfirm_tradeify_25k_sizing.py (v3)*  ",
        "*iter_10: N=346, gap≤1.2%, rng≥30pt, $400 SL, Sharpe 1.52, MaxDD -13.4%*",
        f"*trailing_dd = ${TV_TRAIL_DD:,.0f} CONFIRMED from Tradeify checkout screenshot*",
        "",
        "## Tradeify Select Flex $25K Rules (Confirmed)",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| EOD trailing DD | ${TV_TRAIL_DD:,.0f} (from equity peak, never resets) |",
        f"| Lock trigger | EOD balance ≥ ${TV_LOCK_BAL:,} |",
        f"| Post-lock floor | ${TV_FLOOR:,} permanent |",
        f"| Eval target | ${TV_EVAL_TGT:,.0f} (6%), **no time limit** |",
        "| Daily loss limit | None |",
        "| Profit split | 90/10 (trader keeps 90%) |",
        f"| Reset fee | ${RESET_FEE:.0f} one-time (code MAY, 40% off ~$109) |",
        "",
        f"## Historical Trailing DD (full backtest, $25K initial, limit ${TV_TRAIL_DD:,.0f})",
        "| Sizing | MNQ | MaxSL/trade | MaxTrailDD | %Limit | Cushion | HistBust |",
        "|--------|-----|------------|------------|--------|---------|---------|",
    ]

    for label, n_mnq in SIZINGS.items():
        r = results[label]
        h = r["hist"]
        lines.append(
            f"| {label} | {n_mnq} | ${r['max_sl']:.0f} | "
            f"${h['max_trail_dd_usd']:,.0f} | {h['max_trail_dd_pct']:.1f}% | "
            f"${h['cushion_usd']:,.0f} | {'YES' if h['hist_bust'] else 'no'} |"
        )

    lines += [
        "",
        f"## Bootstrap Results (10,000 paths, no time limit, max_days={MAX_DAYS_EVAL})",
        "| Sizing | P(pass) | P(bust) | P(timeout) | MedDays | E[atts] | E[eval cost] | E[mo×90%] |",
        "|--------|---------|---------|------------|---------|---------|-------------|-----------|",
    ]
    for label in SIZINGS:
        r = results[label]
        e = r["eval"]
        p = r["post"]
        lines.append(
            f"| {label} | {e['p_pass']:.1f}% | {e['p_bust']:.1f}% | "
            f"{e['p_timeout']:.1f}% | "
            f"{e['med_days']:.0f}d | {e['e_attempts']:.1f}× | "
            f"${e['e_total_eval_cost']:,.0f} | ${p['mean_monthly']:+,.0f} |"
        )

    lines += ["", "## WF Fold Survival (quarterly OOS, fresh $25K per fold)"]
    for label, n_mnq in SIZINGS.items():
        folds  = results[label]["folds"]
        n_bust = sum(1 for f in folds if not f["survive"])
        lines.append(f"\n### {label} ({n_mnq} MNQ) — {n_bust}/{len(folds)} folds bust")
        lines += [
            "| Period | Trades | P&L | MaxTrailDD | Cushion | Result |",
            "|--------|--------|-----|------------|---------|--------|",
        ]
        for f in folds:
            lines.append(
                f"| {f['period']} | {f['n_trades']} | ${f['pnl_usd']:+,.0f} | "
                f"${f['max_trail_dd']:,.0f} | ${f['cushion']:,.0f} | "
                f"{'BUST' if not f['survive'] else 'PASS'} |"
            )

    # Decision section
    lines += ["", "## Decision"]

    if decision_label:
        dr = results[decision_label]
        e  = dr["eval"]
        p  = dr["post"]
        h  = dr["hist"]
        ww = dr["ww"]
        folds       = dr["folds"]
        n_fold_bust = sum(1 for f in folds if not f["survive"])
        gate_used   = GATE_3MNQ if decision_label == "3 MNQ" else GATE_2MNQ

        lines += [
            f"### Recommended: **{decision_label} on Tradeify Select Flex $25K**\n",
            "| Metric | Value | Gate |",
            "|--------|-------|------|",
            f"| P(pass per attempt) | {e['p_pass']:.1f}% | ≥{gate_used:.0f}% ✓ |",
            f"| P(bust per attempt) | {e['p_bust']:.1f}% | — |",
            f"| P(timeout >{MAX_DAYS_EVAL}d) | {e['p_timeout']:.1f}% | — |",
            f"| Median days to pass | {e['med_days']:.0f}d | — |",
            f"| E[attempts to funded] | {e['e_attempts']:.1f}× | — |",
            f"| E[total eval cost] | ${e['e_total_eval_cost']:,.0f} | {e['e_attempts']:.1f}× × ${RESET_FEE:.0f}/reset |",
            f"| MaxSL/trade | ${dr['max_sl']:.0f} | — |",
            f"| Max hist trail DD | ${h['max_trail_dd_usd']:,.0f} / ${TV_TRAIL_DD:,.0f} | {h['max_trail_dd_pct']:.0f}% utilization |",
            f"| E[monthly post-funded] | ${p['mean_monthly']:+,.0f} | 90% split |",
            f"| Worst 60d post-lock DD | ${ww['worst_dd']:+,.0f} | vs −${TV_LOCK_BAL - TV_FLOOR:,.0f} floor → {ww['outcome']} |",
            f"| WF fold survival | {len(folds) - n_fold_bust}/{len(folds)} pass | — |",
            "",
            "### Structural risk: trailing DD ratchet",
            "",
            f"The ${TV_TRAIL_DD:,.0f} trailing DD is measured from the EOD equity peak, not the initial balance.",
            "Every winning day permanently tightens recovery room for the remainder of the challenge.",
            f"Example: +${TV_TRAIL_DD:,.0f} gain → peak at ${TV_INITIAL + TV_TRAIL_DD:,.0f} → any subsequent"
            f" ${TV_TRAIL_DD:,.0f} drawdown busts the account even though it was originally ahead.",
            "",
            "**Mitigation**: request payout as soon as qualifying days are met (5 winning days ≥ $75 each).",
            "Payout request triggers lock — floor becomes fixed at $25,100 and the ratchet stops mattering.",
            "",
            "### Risk management rules",
            f"- Budget for ~{e['e_attempts']:.0f} attempts on average (E[total eval cost]: ${e['e_total_eval_cost']:,.0f})",
            "- Request payout immediately once 5 qualifying days are met",
            "- If 3 consecutive busts without reaching lock trigger → pause and review",
        ]
    else:
        r3 = results["3 MNQ"]
        r2 = results["2 MNQ"]
        lines += [
            "### ⚠ Neither gate satisfied — REEVALUATE",
            "",
            "| Sizing | P(pass) | Gate | Result |",
            "|--------|---------|------|--------|",
            f"| 3 MNQ | {r3['eval']['p_pass']:.1f}% | ≥{GATE_3MNQ:.0f}% | FAIL |",
            f"| 2 MNQ | {r2['eval']['p_pass']:.1f}% | ≥{GATE_2MNQ:.0f}% | FAIL |",
            "",
            f"Trailing DD ${TV_TRAIL_DD:,.0f} is too tight for this strategy at tested sizings.",
            "Consider: 1 MNQ or alternative propfirm with trailing DD ≥ $2,000.",
        ]

    lines += [
        "",
        "## Post-Paper VWAP Monitoring Threshold",
        "Resolve VWAP 1-min vs 5-min discrepancy before transitioning to live if either trigger fires:",
        "- Mean entry slippage > **2 pts** vs backtest entry level, OR",
        "- Hit rate divergence > **10%** vs backtest (e.g. 27.75% → <25% over ≥30 trades)",
    ]

    out = Path(__file__).parents[4] / "live" / "strategy_c_live" / "SIZING_DECISION.md"
    out.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
