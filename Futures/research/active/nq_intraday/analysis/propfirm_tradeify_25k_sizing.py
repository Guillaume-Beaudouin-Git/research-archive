"""
propfirm_tradeify_25k_sizing.py — Step 0: Tradeify $25K sizing decision
========================================================================
Strategy C iter_10 (N=346, gap≤1.2%, rng≥30pt, $400 SL cap)
Tests three sizing scenarios against exact Tradeify Select Flex $25K rules.

Scenarios  MNQ   Interpretation
  1×        10   NQ contract equivalent (backtest reference)
  0.5×       5   Half of 1×
  0.33×      3   Current PHASE_CONTRACTS (all phases)

Per-scenario outputs:
  • Historical trailing DD peak + ≥30% cushion check ($450 buffer gate)
  • Bootstrap: P(pass eval 90d), P(bust), median days, E[monthly net 90%]
  • WF fold survival (quarterly OOS periods, fresh $25K per fold)
  • EV net of $119/mo fees + 10% Tradeify split

Recommendation: optimal sizing satisfying (a) ≥30% cushion, (b) EV > 0.
Worth-it check: if optimal ≥70% reduction vs 1× → raise fixed-DD alternative.

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

# ─── Tradeify Select Flex $25K — exact rules ─────────────────────────────────
TV_INITIAL       = 25_000.0
TV_TRAIL_DD      = 1_500.0    # EOD trailing from equity peak
TV_LOCK_BAL      = 26_100.0   # lock trigger balance
TV_FLOOR         = 25_100.0   # permanent post-lock floor
TV_EVAL_TGT      = 1_500.0    # eval target (6% of 25K)
TV_EVAL_DAYS     = 90
TV_POSTLOCK_DAYS = 60
PAYOUT_SPLIT     = 0.90

# ─── Fee model ───────────────────────────────────────────────────────────────
MONTHLY_FEE = 119.0
ANNUAL_FEE  = MONTHLY_FEE * 12   # $1,428/yr

# ─── iter_10 signal params ───────────────────────────────────────────────────
GAP_THRESH  = 0.012
RNG_MIN     = 30.0
DOLLAR_STOP = 400.0

# ─── MNQ/NQ scaling ──────────────────────────────────────────────────────────
MNQ_PV     = 2.0
MNQ_COST   = 2.15
NQ_PV      = 20.0
NQ_COST    = 19.0

# ─── Sizing scenarios ────────────────────────────────────────────────────────
SIZINGS = {"1×": 10, "0.5×": 5, "0.33×": 3}

# ─── Decision thresholds ─────────────────────────────────────────────────────
CUSHION_MIN_PCT = 0.30                        # ≥30% of trail limit = $450
CUSHION_MIN_USD = TV_TRAIL_DD * CUSHION_MIN_PCT
REDUCTION_WARN  = 0.70                        # ≥70% reduction → worth-it review


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
    """Simulate $25K account through full daily P&L series. Track EOD trailing DD."""
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
        "cushion_pct":      round(cushion / TV_TRAIL_DD * 100, 1),
        "cushion_ok":       cushion >= CUSHION_MIN_USD,
        "hist_bust":        bust_day is not None,
        "bust_day":         bust_day,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap simulations
# ─────────────────────────────────────────────────────────────────────────────

def simulate_eval_bs(daily: pd.Series, rng: np.random.Generator) -> dict:
    """Phase 1 eval: trailing DD $1,500, target $1,500, 90 days."""
    pnl_arr  = daily.values.astype(float)
    avg_bl   = max(5, int(np.sqrt(len(pnl_arr))))
    paths    = _stationary_block_paths(pnl_arr, MC_PATHS, TV_EVAL_DAYS, avg_bl, rng)
    n_paths, n_days = paths.shape

    cum   = np.cumsum(paths, axis=1)
    peak  = np.maximum.accumulate(np.maximum(cum, 0), axis=1)
    trail = peak - cum

    bust_mat   = trail >= TV_TRAIL_DD
    bust_mask  = bust_mat.any(axis=1)
    first_bust = np.where(bust_mask, bust_mat.argmax(axis=1), n_days)

    tgt_mat  = cum >= TV_EVAL_TGT
    tgt_mask = tgt_mat.any(axis=1)
    first_tgt = np.where(tgt_mask, tgt_mat.argmax(axis=1), n_days)

    pass_mask = tgt_mask & (first_tgt < first_bust)
    t_days    = first_tgt[pass_mask] + 1
    med_days  = float(np.median(t_days)) if pass_mask.sum() > 0 else 999.0

    return {
        "p_pass":     round(float(pass_mask.sum()) / n_paths * 100, 1),
        "p_bust":     round(float(bust_mask.sum())  / n_paths * 100, 1),
        "med_days":   round(med_days, 0),
        "mean_daily": float(pnl_arr.mean()),
    }


def simulate_postlock_bs(daily: pd.Series, rng: np.random.Generator) -> dict:
    """Post-lock: floor budget = $26,100 - $25,100 = $1,000 from lock start."""
    pnl_arr    = daily.values.astype(float)
    avg_bl     = max(5, int(np.sqrt(len(pnl_arr))))
    paths      = _stationary_block_paths(pnl_arr, MC_PATHS, TV_POSTLOCK_DAYS, avg_bl, rng)
    n_paths, _ = paths.shape
    cum         = np.cumsum(paths, axis=1)
    floor_dd    = TV_LOCK_BAL - TV_FLOOR   # $1,000
    bust_mask   = (cum < -floor_dd).any(axis=1)
    mean_daily  = float(pnl_arr.mean())
    return {
        "p_bust":       round(float(bust_mask.sum()) / n_paths * 100, 1),
        "mean_daily":   mean_daily,
        "mean_monthly": round(mean_daily * 21 * PAYOUT_SPLIT, 0),
    }


def worst_60d_postlock(daily: pd.Series) -> dict:
    pnl    = daily.values.astype(float)
    n      = TV_POSTLOCK_DAYS
    floor  = TV_LOCK_BAL - TV_FLOOR   # $1,000
    if len(pnl) < n:
        return {"worst_pnl": float(pnl.sum()), "worst_dd": float(np.cumsum(pnl).min()), "outcome": "INSUFFICIENT"}
    wins_pnl = np.array([pnl[i:i+n].sum() for i in range(len(pnl) - n + 1)])
    wins_dd  = np.array([np.cumsum(pnl[i:i+n]).min() for i in range(len(pnl) - n + 1)])
    worst_pnl = float(wins_pnl.min())
    worst_dd  = float(wins_dd.min())
    return {
        "worst_pnl": round(worst_pnl, 0),
        "worst_dd":  round(worst_dd, 0),
        "outcome":   "PASS" if worst_dd > -floor else "BUST",
    }


# ─────────────────────────────────────────────────────────────────────────────
# WF fold survival (quarterly split of full backtest)
# ─────────────────────────────────────────────────────────────────────────────

def wf_fold_survival(tl: pd.DataFrame, n_mnq: int) -> list:
    """
    Split 346-trade backtest into quarterly OOS periods.
    Simulate a fresh $25K challenge through each quarter.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# EV analysis
# ─────────────────────────────────────────────────────────────────────────────

def ev_analysis(daily: pd.Series, p_pass: float) -> dict:
    """
    Net EV assuming: E[monthly gross] × 90% split − $119/mo fee.
    p_pass drives expected number of re-buys before first pass.
    """
    mean_daily     = float(daily.mean())
    e_monthly_gross = mean_daily * 21 * PAYOUT_SPLIT
    e_monthly_net   = e_monthly_gross - MONTHLY_FEE
    e_annual_net    = e_monthly_net * 12
    p_frac          = max(0.001, p_pass / 100.0)
    e_attempts      = 1.0 / p_frac
    return {
        "e_monthly_gross": round(e_monthly_gross, 0),
        "e_monthly_net":   round(e_monthly_net, 0),
        "e_annual_net":    round(e_annual_net, 0),
        "e_attempts":      round(e_attempts, 1),
    }


def max_loss_per_trade(n_mnq: int) -> float:
    max_nq = DOLLAR_STOP + NQ_COST
    return abs(scale_to_mnq(-max_nq, n_mnq))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> dict:
    print("=" * 100)
    print("STEP 0 — TRADEIFY SELECT FLEX $25K SIZING DECISION  (Strategy C iter_10, N=346)")
    print("=" * 100)
    print(f"  Rules: trailing DD ${TV_TRAIL_DD:,.0f} EOD | eval target ${TV_EVAL_TGT:,.0f} (6%) | "
          f"lock @ ${TV_LOCK_BAL:,} | floor ${TV_FLOOR:,} | 90/10 split")
    print(f"  Cushion gate: ≥{CUSHION_MIN_PCT*100:.0f}% buffer → max observed trail DD ≤ "
          f"${TV_TRAIL_DD - CUSHION_MIN_USD:,.0f}  (cushion ≥ ${CUSHION_MIN_USD:,.0f})")
    print(f"  Fee model: ${MONTHLY_FEE:.0f}/mo = ${ANNUAL_FEE:,.0f}/yr  |  Split: 90/10")
    print()

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)
    feats_f = feats[feats["rng"] >= RNG_MIN].copy()
    sigs   = signals_from_features(feats_f, gap_thresh=GAP_THRESH, dollar_stop=DOLLAR_STOP)
    tl, m  = engine.run(sigs)

    print(f"  iter_10: {len(tl)} trades  Sharpe_HAC={m.get('sharpe_daily_hac', 0):.4f}  "
          f"MaxDD={m.get('max_dd_pct', 0):.1%}  "
          f"[{pd.to_datetime(tl['entry_ts'].min()).date()} → "
          f"{pd.to_datetime(tl['entry_ts'].max()).date()}]")
    print()

    all_results: dict = {}
    for label, n_mnq in SIZINGS.items():
        daily   = build_daily_mnq(tl, n_mnq)
        hist_dd = historical_trailing_dd(daily)
        max_sl  = max_loss_per_trade(n_mnq)

        rng_e = np.random.default_rng(MC_SEED + n_mnq * 100)
        rng_k = np.random.default_rng(MC_SEED + n_mnq * 100 + 1)

        bs_eval = simulate_eval_bs(daily, rng_e)
        bs_post = simulate_postlock_bs(daily, rng_k)
        ww      = worst_60d_postlock(daily)
        ev      = ev_analysis(daily, bs_eval["p_pass"])
        folds   = wf_fold_survival(tl, n_mnq)

        all_results[label] = {
            "n_mnq": n_mnq, "max_sl": max_sl, "daily": daily,
            "hist": hist_dd, "eval": bs_eval, "post": bs_post,
            "ww": ww, "ev": ev, "folds": folds,
        }

    # ──────────────────────────────────────────────────────────────────────
    # TABLE 1 — Historical trailing DD
    # ──────────────────────────────────────────────────────────────────────
    print("=" * 100)
    print("  TABLE 1 — HISTORICAL TRAILING DD (full backtest, $25K initial)")
    print("=" * 100)
    print(f"  {'Sizing':>7} {'MNQ':>4} {'MaxSL/tr':>9} {'MaxTrailDD':>12} {'%Limit':>8} "
          f"{'Cushion':>10} {'≥$450':>7} {'HistBust':>9}")
    print(f"  {'─'*73}")
    for label, n_mnq in SIZINGS.items():
        r = all_results[label]
        h = r["hist"]
        print(f"  {label:>7} {n_mnq:>4}  ${r['max_sl']:>7.0f}   "
              f"${h['max_trail_dd_usd']:>9,.0f}   "
              f"{h['max_trail_dd_pct']:>6.1f}%   "
              f"${h['cushion_usd']:>8,.0f}   "
              f"{'✓' if h['cushion_ok'] else '✗':>5}   "
              f"{'YES ✗' if h['hist_bust'] else 'no ✓':>9}")

    # ──────────────────────────────────────────────────────────────────────
    # TABLE 2 — Bootstrap eval + EV
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("  TABLE 2 — BOOTSTRAP EVAL + EV (10,000 paths × 90 days, stationary block)")
    print("=" * 100)
    print(f"  {'Sizing':>7} {'P(pass90d)':>11} {'P(bust)':>8} {'MedDays':>8} "
          f"{'E[mo×90%]':>11} {'MonthlyNet':>11} {'AnnualNet':>11} {'Attempts':>9}")
    print(f"  {'─'*83}")
    for label, n_mnq in SIZINGS.items():
        r  = all_results[label]
        e  = r["eval"]
        pk = r["post"]
        ev = r["ev"]
        print(f"  {label:>7}  {e['p_pass']:>10.1f}%  {e['p_bust']:>6.1f}%  "
              f"{e['med_days']:>7.0f}d  "
              f"  ${pk['mean_monthly']:>+9,.0f}  "
              f"  ${ev['e_monthly_net']:>+9,.0f}  "
              f"  ${ev['e_annual_net']:>+9,.0f}  "
              f"{ev['e_attempts']:>8.1f}×")

    # ──────────────────────────────────────────────────────────────────────
    # TABLE 3 — WF fold survival
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("  TABLE 3 — WF FOLD SURVIVAL (quarterly, fresh $25K challenge per fold)")
    print("=" * 100)
    for label, n_mnq in SIZINGS.items():
        folds  = all_results[label]["folds"]
        n_bust = sum(1 for f in folds if not f["survive"])
        print(f"\n  {label} ({n_mnq} MNQ)  —  {n_bust}/{len(folds)} folds bust")
        print(f"    {'Period':>8} {'Trades':>7} {'P&L':>8} {'MaxTrailDD':>12} {'Cushion':>10} {'Result':>8}")
        print(f"    {'─'*58}")
        for f in folds:
            r_str = "BUST ✗" if not f["survive"] else "PASS ✓"
            print(f"    {f['period']:>8}  {f['n_trades']:>6}  ${f['pnl_usd']:>+7,.0f}  "
                  f"${f['max_trail_dd']:>10,.0f}  ${f['cushion']:>8,.0f}  {r_str}")

    # ──────────────────────────────────────────────────────────────────────
    # SECTION 4 — Recommendation
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("  RECOMMENDATION")
    print("=" * 100)

    ref_mnq       = SIZINGS["1×"]
    optimal_label = None
    optimal_mnq   = None

    for label, n_mnq in SIZINGS.items():
        r = all_results[label]
        if (r["hist"]["cushion_ok"]
                and r["ev"]["e_annual_net"] > 0
                and not r["hist"]["hist_bust"]):
            if optimal_label is None:
                optimal_label = label
                optimal_mnq   = n_mnq

    if optimal_label:
        reduction_pct = 1.0 - optimal_mnq / ref_mnq
        r  = all_results[optimal_label]
        h  = r["hist"]
        e  = r["eval"]
        ev = r["ev"]
        ww = r["ww"]
        folds = r["folds"]
        n_fold_bust = sum(1 for f in folds if not f["survive"])

        print(f"\n  ► OPTIMAL SIZING: {optimal_label} = {optimal_mnq} MNQ")
        print(f"     Cushion:           ${h['cushion_usd']:,.0f}  ({h['cushion_pct']:.0f}% of limit)  "
              f"[gate ≥{CUSHION_MIN_PCT*100:.0f}% → {'PASS ✓' if h['cushion_ok'] else 'FAIL ✗'}]")
        print(f"     P(pass eval 90d):  {e['p_pass']:.1f}%")
        print(f"     P(bust eval):      {e['p_bust']:.1f}%")
        print(f"     Median days:       {e['med_days']:.0f}d")
        print(f"     E[monthly ×90%]:   ${r['post']['mean_monthly']:+,.0f}")
        print(f"     Monthly net (−fee): ${ev['e_monthly_net']:+,.0f}")
        print(f"     Annual net EV:     ${ev['e_annual_net']:+,.0f}")
        print(f"     Worst 60d post-lock: ${ww['worst_dd']:+,.0f} → {ww['outcome']}")
        print(f"     WF folds: {len(folds) - n_fold_bust}/{len(folds)} survive")

        if reduction_pct >= REDUCTION_WARN:
            print()
            print(f"  ⚠  SIZING REDUCTION = {reduction_pct*100:.0f}% vs 1× (10 MNQ) — EXCEEDS {REDUCTION_WARN*100:.0f}% THRESHOLD")
            print(f"  ─────────────────────────────────────────────────────────────────────")
            print(f"  Tradeify trailing DD: optimal {optimal_mnq} MNQ → Annual EV ${ev['e_annual_net']:+,.0f}")
            print(f"  Issue: trailing DD ratchets up with gains. A $600 win = $600 less recovery room.")
            print()
            print(f"  Fixed-DD alternative (e.g. Topstep $50K): $2,500 fixed from initial, never trails.")
            r3 = all_results.get("0.33×", {})
            max_trail_3mnq = r3.get("hist", {}).get("max_trail_dd_usd", 0)
            print(f"  At 3 MNQ: worst historical trailing DD = ${max_trail_3mnq:,.0f}  "
                  f"(fits $2,500 fixed limit with ${2500 - max_trail_3mnq:,.0f} buffer)")
            print(f"  At 3 MNQ with $2,500 fixed DD: same sizing, ~$66 more cushion/mo, "
                  f"no ratchet risk.")
            print(f"  Topstep fee: ~$165/mo = $1,980/yr (vs ${ANNUAL_FEE:,.0f}/yr Tradeify)")
            print(f"  → Topstep annual EV at 3 MNQ: ~${ev['e_monthly_gross'] - 165:.0f}/mo net")
            print()
            print(f"  Verdict: run the fixed-DD comparison. Tradeify may be sub-optimal for")
            print(f"  a trailing-DD strategy at {optimal_mnq} MNQ given the ratchet risk.")
        else:
            print()
            print(f"     Sizing reduction vs 1×: {reduction_pct*100:.0f}% < {REDUCTION_WARN*100:.0f}% threshold → Tradeify worthwhile.")
    else:
        print(f"\n  ► NO TESTED SIZING SATISFIES ALL CRITERIA (cushion ≥30% AND EV > 0 AND no hist bust)")
        print()
        print(f"  {'Sizing':>7}  {'Cushion':>10}  {'CushOK':>8}  {'AnnualEV':>10}  {'HistBust':>9}")
        print(f"  {'─'*52}")
        for label, n_mnq in SIZINGS.items():
            r = all_results[label]
            print(f"  {label:>7}  ${r['hist']['cushion_usd']:>9,.0f}  "
                  f"{'✓' if r['hist']['cushion_ok'] else '✗':>8}  "
                  f"${r['ev']['e_annual_net']:>+9,.0f}  "
                  f"{'YES' if r['hist']['hist_bust'] else 'no':>9}")
        print()
        print(f"  Trailing DD (${TV_TRAIL_DD:,.0f}) is too constraining for Strategy C at tested sizings.")
        print(f"  Consider fixed-DD propfirm with $2,000–$2,500 fixed DD for more sizing room.")

    print("\n" + "=" * 100)

    _write_md(all_results)
    out = Path(__file__).parents[4] / "live" / "strategy_c_live" / "SIZING_DECISION.md"
    print(f"\n  → SIZING_DECISION.md written: {out}")

    return all_results


# ─────────────────────────────────────────────────────────────────────────────
# Markdown output
# ─────────────────────────────────────────────────────────────────────────────

def _write_md(results: dict) -> None:
    lines = [
        "# SIZING_DECISION.md — Strategy C / Tradeify Select Flex $25K",
        "*Auto-generated by propfirm_tradeify_25k_sizing.py*  ",
        "*iter_10: N=346, gap≤1.2%, rng≥30pt, $400 SL, Sharpe 1.52, MaxDD -13.4%*",
        "",
        "## Tradeify Select Flex $25K Rules",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| EOD trailing DD | ${TV_TRAIL_DD:,.0f} (from equity peak, never resets) |",
        f"| Lock trigger | EOD balance ≥ ${TV_LOCK_BAL:,} |",
        f"| Post-lock floor | ${TV_FLOOR:,} permanent |",
        f"| Eval target | ${TV_EVAL_TGT:,.0f} (6%), 90-day window |",
        f"| Daily loss limit | None |",
        f"| Profit split | 90/10 (trader keeps 90%) |",
        f"| Monthly fee | ${MONTHLY_FEE:.0f} = ${ANNUAL_FEE:,.0f}/yr |",
        "",
        "## Historical Trailing DD (full backtest, deterministic)",
        f"| Sizing | MNQ | MaxSL/trade | MaxTrailDD | %Limit | Cushion | ≥30%? | HistBust |",
        f"|--------|-----|------------|------------|--------|---------|-------|---------|",
    ]

    for label, n_mnq in SIZINGS.items():
        r = results[label]
        h = r["hist"]
        lines.append(
            f"| {label} | {n_mnq} | ${r['max_sl']:.0f} | "
            f"${h['max_trail_dd_usd']:,.0f} | {h['max_trail_dd_pct']:.1f}% | "
            f"${h['cushion_usd']:,.0f} | {'✓' if h['cushion_ok'] else '✗'} | "
            f"{'YES' if h['hist_bust'] else 'no'} |"
        )

    lines += [
        "",
        "## Bootstrap Results (10,000 paths × 90 days, stationary block)",
        "| Sizing | P(pass 90d) | P(bust) | Med days | E[mo×90%] | Monthly net | Annual net | Attempts |",
        "|--------|------------|---------|----------|-----------|-------------|-----------|---------|",
    ]
    for label, n_mnq in SIZINGS.items():
        r  = results[label]
        e  = r["eval"]
        pk = r["post"]
        ev = r["ev"]
        lines.append(
            f"| {label} | {e['p_pass']:.1f}% | {e['p_bust']:.1f}% | "
            f"{e['med_days']:.0f}d | ${pk['mean_monthly']:+,.0f} | "
            f"${ev['e_monthly_net']:+,.0f} | ${ev['e_annual_net']:+,.0f} | {ev['e_attempts']:.1f}× |"
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

    # Recommendation block
    ref_mnq       = SIZINGS["1×"]
    optimal_label = None
    optimal_mnq   = None
    for label, n_mnq in SIZINGS.items():
        r = results[label]
        if (r["hist"]["cushion_ok"]
                and r["ev"]["e_annual_net"] > 0
                and not r["hist"]["hist_bust"]):
            if optimal_label is None:
                optimal_label = label
                optimal_mnq   = n_mnq

    lines += ["", "## Decision"]

    if optimal_label:
        reduction_pct = 1.0 - optimal_mnq / ref_mnq
        r  = results[optimal_label]
        lines.append(f"**Optimal sizing: {optimal_label} = {optimal_mnq} MNQ**\n")
        lines.append(f"- Cushion: ${r['hist']['cushion_usd']:,.0f} ({r['hist']['cushion_pct']:.0f}% of limit) ✓")
        lines.append(f"- P(pass eval 90d): {r['eval']['p_pass']:.1f}%")
        lines.append(f"- P(bust eval): {r['eval']['p_bust']:.1f}%")
        lines.append(f"- E[monthly net]: ${r['ev']['e_monthly_net']:+,.0f}")
        lines.append(f"- Annual net EV: ${r['ev']['e_annual_net']:+,.0f}")
        lines.append(f"- Sizing reduction vs 1×: {reduction_pct*100:.0f}%")
        if reduction_pct >= REDUCTION_WARN:
            lines.append(f"\n⚠ **{reduction_pct*100:.0f}% reduction exceeds {REDUCTION_WARN*100:.0f}% threshold.**  ")
            lines.append("Trailing DD ratchets with gains. Consider fixed-DD propfirm (Topstep $50K, "
                         "$2,500 fixed) for same sizing with no ratchet risk and similar EV.")
    else:
        lines.append("**No sizing satisfies all criteria.** Trailing DD too constraining for this strategy.")
        lines.append("Recommendation: evaluate fixed-DD propfirm with $2,000–$2,500 fixed drawdown.")

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
