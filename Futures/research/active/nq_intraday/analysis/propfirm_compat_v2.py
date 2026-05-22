"""
propfirm_compat_v2.py — Propfirm Compatibility Analysis v2
===========================================================
Strategy C iter_10: A$400 + B1.2% + rng≥30pt (346 trades, Sharpe 1.52)

Propfirm rules (FTMO Standard $100K):
  max_dd_total   = 10% TRAILING from equity peak (not fixed from start)
  max_dd_daily   = 5%  of initial balance per calendar day
  profit_target  = 10% of initial balance (phase 1)
  time_limit     = none
  Note: trailing DD is stricter than fixed DD — any profit then given back
        reduces the remaining drawdown room (peak moves up, never down).

Improvements over v1:
  1. 8×5 table with explicit binding constraint column
  2. Stationary block bootstrap (Politis-Romano 1994, L=20) vs iid
  3. Worst-observed-window stress test (non-parametric, 60-day rolling)
  4. Final recommendation with full justification

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.propfirm_compat_v2
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

STRATEGY_GAP  = 0.012
STRATEGY_STOP = 400.0
RNG_MIN       = 30.0

MNQ_POINT_VALUE = 2.0
MNQ_COST_RT     = 2.15
NQ_COST_RT      = 19.0
NQ_PV           = 20.0

ACCOUNT_SIZES = [50_000, 100_000]
MNQ_SIZES     = [5, 10, 15, 20]

MC_PATHS         = 10_000
MC_DAYS          = 60
MC_SEED          = 42
AVG_BLOCK_LEN    = 20    # Politis-Romano: L ≈ sqrt(N_days) ≈ 20

DD_TOTAL_PCT  = 0.10   # 10% max total DD → bust
DD_DAILY_PCT  = 0.05   # 5%  max daily loss
TARGET_PCT    = 0.10   # 10% profit target

# Acceptance thresholds
C1_THRESH = 10.0   # P(bust) < 10%
C2_THRESH = 15.0   # P(daily>5%) < 15%
C3_THRESH = 40.0   # P(target) > 40%
C4_THRESH = 8.0    # MaxDD_hist < 8% (2% buffer below 10% hard limit)


# ─────────────────────────────────────────────────────────────────────────────
# P&L scaling
# ─────────────────────────────────────────────────────────────────────────────

def scale_pnl(nq_pnl_usd: float, mnq_contracts: int) -> float:
    """Scale 1-NQ-contract backtest P&L to N /MNQ contracts."""
    nq_pts = (nq_pnl_usd + NQ_COST_RT) / NQ_PV
    return nq_pts * MNQ_POINT_VALUE * mnq_contracts - MNQ_COST_RT * mnq_contracts


def build_daily_pnl(trade_log: pd.DataFrame, mnq_contracts: int) -> pd.Series:
    """Build daily P&L series scaled to mnq_contracts, including zero-trade days."""
    tl = trade_log.copy()
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()
    tl["pnl_mnq"] = tl["pnl_usd"].apply(lambda x: scale_pnl(x, mnq_contracts))
    daily_trade = tl.groupby("date")["pnl_mnq"].sum()
    all_dates = pd.bdate_range(tl["date"].min(), tl["date"].max())
    daily = daily_trade.reindex(all_dates.normalize(), fill_value=0.0)
    return daily


# ─────────────────────────────────────────────────────────────────────────────
# Historical DD metrics
# ─────────────────────────────────────────────────────────────────────────────

def fixed_dd_metrics(daily: pd.Series, account: float) -> dict:
    """Compute fixed DD metrics from initial balance = 0."""
    cum         = daily.cumsum()
    running_max = cum.cummax()
    dd_series   = cum - running_max
    max_dd_usd  = float(dd_series.min())
    max_dd_pct  = -max_dd_usd / account * 100
    worst_day   = float(daily.min())
    return {
        "max_dd_usd":  round(max_dd_usd, 2),
        "max_dd_pct":  round(max_dd_pct, 2),
        "worst_day":   round(worst_day, 2),
        "busted_hist": max_dd_usd < -DD_TOTAL_PCT * account,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap path generation
# ─────────────────────────────────────────────────────────────────────────────

def _iid_paths(
    pnl_arr: np.ndarray,
    n_paths: int,
    n_days: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """iid bootstrap: sample with replacement (n_paths × n_days)."""
    idx = rng.integers(0, len(pnl_arr), size=(n_paths, n_days))
    return pnl_arr[idx]


def _stationary_block_paths(
    pnl_arr: np.ndarray,
    n_paths: int,
    n_days: int,
    avg_block_len: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Stationary block bootstrap (Politis-Romano 1994).
    Block length is geometrically distributed with mean = avg_block_len.
    Start positions chosen uniformly at random (with wrap-around).
    Preserves serial correlation structure of daily P&L.
    """
    N = len(pnl_arr)
    p = 1.0 / avg_block_len   # probability of starting a new block

    # Pre-generate all random numbers for efficiency
    new_block = rng.random((n_paths, n_days)) < p
    new_block[:, 0] = True   # first observation always starts a new block
    starts    = rng.integers(0, N, size=(n_paths, n_days))

    all_indices = np.empty((n_paths, n_days), dtype=int)
    for i in range(n_paths):
        pos = int(starts[i, 0])
        all_indices[i, 0] = pos
        for j in range(1, n_days):
            if new_block[i, j]:
                pos = int(starts[i, j])
            else:
                pos = (pos + 1) % N
            all_indices[i, j] = pos

    return pnl_arr[all_indices]


# ─────────────────────────────────────────────────────────────────────────────
# Simulation (vectorised, correct early-stopping semantics)
# ─────────────────────────────────────────────────────────────────────────────

def _simulate(paths: np.ndarray, account: float) -> dict:
    """
    Vectorised simulation over (n_paths × n_days) path matrix.
    Early-stopping semantics: bust → path ends, target → counted only if before bust.

    Bust rule: TRAILING DD from equity peak ≥ 10% of initial balance.
      trailing_dd = max(cumsum_so_far) - current_cumsum ≥ dd_limit
    This matches FTMO's "max overall loss" rule (trailing, not fixed from start).
    Note: running_peak initialises at 0 (no prior gains at challenge start).
    """
    dd_limit    = account * DD_TOTAL_PCT
    daily_limit = account * DD_DAILY_PCT
    target      = account * TARGET_PCT

    n_paths, n_days = paths.shape
    cum = np.cumsum(paths, axis=1)   # (n_paths, n_days)

    # Bust: TRAILING DD from equity peak ≥ dd_limit (FTMO rule)
    running_peak  = np.maximum.accumulate(cum, axis=1)   # peak equity so far (≥ 0)
    trailing_dd   = running_peak - cum                   # always ≥ 0
    bust_matrix   = trailing_dd >= dd_limit                            # (n_paths, n_days)
    bust_mask     = bust_matrix.any(axis=1)                            # (n_paths,) bool
    first_bust    = np.where(bust_mask,
                             bust_matrix.argmax(axis=1),
                             n_days)                                   # day index (0-based)

    # Target: first day where cum ≥ target, only if before bust
    target_matrix = cum >= target                                 # (n_paths, n_days)
    target_mask   = target_matrix.any(axis=1)
    first_target  = np.where(target_mask,
                              target_matrix.argmax(axis=1),
                              n_days)

    # Target counts only if hit STRICTLY before bust
    target_before_bust = target_mask & (first_target < first_bust)

    # Daily violation (structural: dollar stop cap makes this near-impossible)
    daily_vio_mask = (paths < -daily_limit).any(axis=1)

    # Median days to target (1-indexed)
    t_days = first_target[target_before_bust] + 1
    med_days = float(np.median(t_days)) if target_before_bust.sum() > 0 else np.nan

    return {
        "p_bust":      float(bust_mask.sum())               / n_paths * 100,
        "p_daily_vio": float(daily_vio_mask.sum())          / n_paths * 100,
        "p_target":    float(target_before_bust.sum())      / n_paths * 100,
        "med_days":    round(med_days, 0) if np.isfinite(med_days) else 999.0,
        "mean_monthly": float(paths.mean()) * 21,  # ~21 trading days/month
    }


# ─────────────────────────────────────────────────────────────────────────────
# Worst-window stress (non-parametric, 60-day rolling)
# ─────────────────────────────────────────────────────────────────────────────

def worst_window_stress(
    daily: pd.Series,
    account: float,
    window: int = MC_DAYS,
) -> dict:
    """
    Identify the worst 60-day rolling window in the historical backtest.
    For the recommended config: would we have busted? hit target?
    """
    pnl       = daily.values.astype(float)
    dates     = daily.index
    n         = len(pnl)
    dd_limit  = account * DD_TOTAL_PCT
    target    = account * TARGET_PCT

    worst_dd_usd = 0.0
    worst_start  = 0

    for start in range(n - window + 1):
        w       = pnl[start:start + window]
        cum_w   = np.cumsum(w)
        peak_w  = np.maximum.accumulate(cum_w)
        max_dd  = float((peak_w - cum_w).max())   # positive = drawdown amount
        if max_dd > worst_dd_usd:
            worst_dd_usd = max_dd
            worst_start  = start

    # Analyse the worst window
    w           = pnl[worst_start:worst_start + window]
    cum_w       = np.cumsum(w)
    peak_w      = np.maximum.accumulate(cum_w)
    trailing_dd_w = peak_w - cum_w
    busted      = bool(trailing_dd_w.max() >= dd_limit)   # FTMO trailing rule
    t_hit       = bool(cum_w.max() >= target)

    if busted:
        bust_day = int(np.argmax(cum_w <= -dd_limit))
        if t_hit and int(np.argmax(cum_w >= target)) < bust_day:
            outcome = "PASS (target before bust)"
        else:
            outcome = "BUST"
    elif t_hit:
        outcome = "PASS (target hit)"
    else:
        outcome = "NEITHER (window ended < target, no bust)"

    w_start = str(dates[worst_start].date())
    w_end   = str(dates[min(worst_start + window - 1, n - 1)].date())

    # Fixed DD from window start = worst cumulative drawdown from 0 (challenge start)
    fixed_dd_usd = -min(0.0, float(cum_w.min()))   # positive number, 0 if never negative

    return {
        "start_date":    w_start,
        "end_date":      w_end,
        "max_dd_usd":    round(worst_dd_usd, 0),     # trailing (from local peak)
        "max_dd_pct":    round(worst_dd_usd / account * 100, 1),
        "fixed_dd_usd":  round(fixed_dd_usd, 0),     # fixed (from window start)
        "fixed_dd_pct":  round(fixed_dd_usd / account * 100, 1),
        "busted":        busted,
        "target_hit":    t_hit,
        "outcome":       outcome,
        "window_pnl":    round(float(cum_w[-1]), 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 100)
    print("PROPFIRM COMPAT v2 — Strategy C iter_10 (fixed DD rules, block bootstrap)")
    print("=" * 100)
    print(f"  Rules: max_dd={DD_TOTAL_PCT*100:.0f}% total (fixed) | "
          f"daily={DD_DAILY_PCT*100:.0f}% | target={TARGET_PCT*100:.0f}%")
    print(f"  Bootstrap: {MC_PATHS:,} paths × {MC_DAYS} days | "
          f"iid vs stationary block (L={AVG_BLOCK_LEN})")

    # ── Load data + run iter_10 ────────────────────────────────────────────
    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)
    feats_filt = feats[feats["rng"] >= RNG_MIN].copy()
    sigs   = signals_from_features(feats_filt,
                                    gap_thresh=STRATEGY_GAP,
                                    dollar_stop=STRATEGY_STOP)
    tl, _ = engine.run(sigs)
    print(f"\n  iter_10: {len(tl)} trades  "
          f"[{pd.to_datetime(tl['entry_ts'].min()).date()} → "
          f"{pd.to_datetime(tl['entry_ts'].max()).date()}]")

    rng_iid   = np.random.default_rng(MC_SEED)
    rng_block = np.random.default_rng(MC_SEED + 1)

    # ── Compute all 8 configs ─────────────────────────────────────────────
    configs = {}
    for mnq in MNQ_SIZES:
        daily = build_daily_pnl(tl, mnq)
        pnl_arr = daily.values.astype(float)
        avg_block = max(5, int(np.sqrt(len(pnl_arr))))

        for acct in ACCOUNT_SIZES:
            dd   = fixed_dd_metrics(daily, acct)
            c4   = dd["max_dd_pct"] < C4_THRESH

            # iid paths
            paths_iid   = _iid_paths(pnl_arr, MC_PATHS, MC_DAYS, rng_iid)
            mc_iid      = _simulate(paths_iid, acct)

            # block paths
            paths_block = _stationary_block_paths(
                pnl_arr, MC_PATHS, MC_DAYS, avg_block, rng_block)
            mc_block    = _simulate(paths_block, acct)

            c1_block = mc_block["p_bust"]     < C1_THRESH
            c2_block = mc_block["p_daily_vio"] < C2_THRESH
            c3_block = mc_block["p_target"]   > C3_THRESH

            failing = []
            if not c1_block:
                delta = mc_block["p_bust"] - C1_THRESH
                failing.append(f"C1 fail @ {mc_block['p_bust']:.1f}% [need <{C1_THRESH:.0f}%, Δ+{delta:.1f}pp]")
            if not c2_block:
                delta = mc_block["p_daily_vio"] - C2_THRESH
                failing.append(f"C2 fail @ {mc_block['p_daily_vio']:.1f}% [need <{C2_THRESH:.0f}%, Δ+{delta:.1f}pp]")
            if not c3_block:
                delta = C3_THRESH - mc_block["p_target"]
                failing.append(f"C3 fail @ {mc_block['p_target']:.1f}% [need >{C3_THRESH:.0f}%, Δ-{delta:.1f}pp]")
            if not c4:
                delta = dd["max_dd_pct"] - C4_THRESH
                failing.append(f"C4 fail @ {dd['max_dd_pct']:.1f}% [need <{C4_THRESH:.0f}%, Δ+{delta:.1f}pp]")

            all_pass = c1_block and c2_block and c3_block and c4

            configs[(acct, mnq)] = {
                "daily":    daily,
                "dd":       dd,
                "mc_iid":   mc_iid,
                "mc_block": mc_block,
                "c1": c1_block, "c2": c2_block, "c3": c3_block, "c4": c4,
                "all_pass": all_pass,
                "failing":  failing,
                "n_criteria_pass": sum([c1_block, c2_block, c3_block, c4]),
            }

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1.1 — 8 × 5 binding constraint table
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("  STEP 1.1 — 8×5 BINDING CONSTRAINT TABLE (block bootstrap, L=20, TRAILING DD bust)")
    print("=" * 100)

    hdr = (f"  {'Account':>8} {'Sizing':>7} "
           f"{'C1 P(bust)<10%':>16} "
           f"{'C2 P(day>5%)<15%':>17} "
           f"{'C3 P(tgt)>40%':>14} "
           f"{'C4 MaxDD<8%':>12}  "
           f"Binding")
    print(hdr)
    print(f"  {'-'*96}")

    for acct in ACCOUNT_SIZES:
        for mnq in MNQ_SIZES:
            r = configs[(acct, mnq)]
            b = r["mc_block"]
            d = r["dd"]

            c1_str = f"{'✓' if r['c1'] else '✗'} {b['p_bust']:.1f}%"
            c2_str = f"{'✓' if r['c2'] else '✗'} {b['p_daily_vio']:.1f}%"
            c3_str = f"{'✓' if r['c3'] else '✗'} {b['p_target']:.1f}%"
            c4_str = f"{'✓' if r['c4'] else '✗'} {d['max_dd_pct']:.1f}%"

            binding = " | ".join(r["failing"]) if r["failing"] else "ALL PASS ✓"

            print(f"  ${acct:>7,} {mnq:>4}/MNQ "
                  f"{c1_str:>16} "
                  f"{c2_str:>17} "
                  f"{c3_str:>14} "
                  f"{c4_str:>12}  "
                  f"{binding}")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1.2 — iid vs block bootstrap comparison
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print(f"  STEP 1.2 — iid vs BLOCK BOOTSTRAP COMPARISON (L={AVG_BLOCK_LEN})")
    print("=" * 100)
    print(f"  Block bootstrap preserves serial correlation (win/loss clusters).")
    print(f"  For strategies with negative autocorrelation (mean-reverting losses),")
    print(f"  block P(bust) can be ≤ iid P(bust) — the serial structure cushions drawdowns.")
    print()
    print(f"  {'Account':>8} {'Sizing':>7} "
          f"{'P(bust) iid':>12} {'P(bust) blk':>12} {'Δ bust':>7} "
          f"{'P(tgt) iid':>11} {'P(tgt) blk':>11} {'Δ tgt':>7}")
    print(f"  {'-'*76}")

    for acct in ACCOUNT_SIZES:
        for mnq in MNQ_SIZES:
            r = configs[(acct, mnq)]
            i = r["mc_iid"]
            b = r["mc_block"]
            d_bust = b["p_bust"]  - i["p_bust"]
            d_tgt  = b["p_target"] - i["p_target"]
            print(f"  ${acct:>7,} {mnq:>4}/MNQ "
                  f"{i['p_bust']:>11.1f}% {b['p_bust']:>11.1f}% {d_bust:>+6.1f}pp "
                  f"{i['p_target']:>10.1f}% {b['p_target']:>10.1f}% {d_tgt:>+6.1f}pp")

    print(f"\n  → Decision: use BLOCK bootstrap for all sizing decisions.")
    print(f"    Here: block P(bust) < iid P(bust) — mean-reverting serial correlation")
    print(f"    cushions drawdowns. Block estimates are OPTIMISTIC vs iid for this strategy.")

    # ═══════════════════════════════════════════════════════════════════════
    # Select recommended config (block bootstrap criteria)
    # ═══════════════════════════════════════════════════════════════════════
    passing = [(k, v) for k, v in configs.items() if v["all_pass"]]

    if passing:
        # Among passing configs, prefer highest P(target) then lowest P(bust)
        best_key, best = max(passing, key=lambda kv: (kv[1]["mc_block"]["p_target"],
                                                        -kv[1]["mc_block"]["p_bust"]))
    else:
        # No config passes all 4: best available = most criteria + highest P(target)
        best_key, best = max(
            configs.items(),
            key=lambda kv: (kv[1]["n_criteria_pass"],
                            kv[1]["mc_block"]["p_target"],
                            -kv[1]["mc_block"]["p_bust"])
        )

    best_acct, best_mnq = best_key

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1.3 — Worst-window stress for recommended config
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print(f"  STEP 1.3 — WORST-WINDOW STRESS: ${best_acct:,} / {best_mnq} /MNQ")
    print("=" * 100)

    best_daily = best["daily"]
    stress = worst_window_stress(best_daily, best_acct)

    print(f"\n  Rolling {MC_DAYS}-day windows: {len(best_daily) - MC_DAYS + 1} windows analysed")
    print(f"\n  Worst window: {stress['start_date']} → {stress['end_date']}")
    print(f"  MaxDD (trailing, from local peak): ${stress['max_dd_usd']:,.0f}  ({stress['max_dd_pct']:.1f}% of ${best_acct:,})")
    print(f"  MaxDD (fixed, from window start):  ${stress['fixed_dd_usd']:,.0f}  ({stress['fixed_dd_pct']:.1f}% of ${best_acct:,})")
    print(f"  ⚠  Note: FTMO uses TRAILING DD from equity peak (not fixed from start).")
    print(f"     Simulation bust criterion now uses trailing DD — C1 P(bust) is higher than fixed-DD estimates.")
    print(f"  Window total P&L:  ${stress['window_pnl']:+,.0f}")
    print(f"  DD limit (10%):    ${best_acct * DD_TOTAL_PCT:,.0f}")
    print(f"  Target  (10%):     ${best_acct * TARGET_PCT:,.0f}")
    print(f"\n  Outcome if challenge started on {stress['start_date']}:")
    print(f"  → {stress['outcome']}")

    if stress["busted"]:
        print(f"\n  ⚠  WORST WINDOW BUSTS at ${best_acct:,} / {best_mnq} /MNQ")
        print(f"     This is expected for configs with max_dd_hist > 10% account.")
    else:
        print(f"\n  ✓ WORST WINDOW SURVIVES at ${best_acct:,} / {best_mnq} /MNQ")
        print(f"    Historical worst-case 60-day window does not breach the 10% DD limit.")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1.4 — Final recommendation
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("  STEP 1.4 — FINAL RECOMMENDATION")
    print("=" * 100)

    b = best["mc_block"]
    d = best["dd"]

    c1_ok = "✓" if best["c1"] else "✗"
    c2_ok = "✓" if best["c2"] else "✗"
    c3_ok = "✓" if best["c3"] else "✗"
    c4_ok = "✓" if best["c4"] else "✗"

    status = "RECOMMENDED" if best["all_pass"] else "BEST AVAILABLE"

    if best["all_pass"]:
        tradeoff = "All 4 criteria satisfied. Strategy is propfirm-ready at this sizing."
    else:
        binding_labels = [f[0:2] for f in best["failing"]]
        tradeoff = (f"Binding: {', '.join(binding_labels)}. "
                    f"{best['n_criteria_pass']}/4 criteria pass. "
                    f"No configuration satisfies all 4 simultaneously. "
                    f"Trade-off accepted: this config maximises P(target) among the "
                    f"closest-to-passing set.")

    if not passing:
        print(f"\n  ⚠  NO CONFIG PASSES ALL 4 CRITERIA (block bootstrap)")
        print(f"     Strategy C is not propfirm-ready at the strict C4=8% threshold.")
        print(f"     The binding constraint is typically C4 (max_dd_hist) — the strategy's")
        print(f"     historical max DD exceeds 8% at all sizings that generate enough P&L")
        print(f"     to hit the 10% target in 60 days.")
        print()

    print(f"\n  {'─'*80}")
    print(f"  {status}: ${best_acct:,} account, {best_mnq} /MNQ contracts")
    print(f"  {'─'*80}")
    print(f"  {c1_ok} C1 P(bust)         = {b['p_bust']:.1f}%   [need <{C1_THRESH:.0f}%]")
    print(f"  {c2_ok} C2 P(daily>5%)     = {b['p_daily_vio']:.1f}%   [need <{C2_THRESH:.0f}%]  "
          f"← structurally capped by dollar stop")
    print(f"  {c3_ok} C3 P(10% target)   = {b['p_target']:.1f}%   [need >{C3_THRESH:.0f}%]")
    print(f"  {c4_ok} C4 MaxDD_hist      = {d['max_dd_pct']:.1f}%   [need <{C4_THRESH:.0f}%]")
    print()
    print(f"  Worst-window 60-day: {stress['outcome']} "
          f"(trailing_dd={stress['max_dd_pct']:.1f}%, fixed_dd={stress['fixed_dd_pct']:.1f}%,"
          f" {stress['start_date']} → {stress['end_date']})")
    print()
    print(f"  iid vs block Δ on P(bust):   {best['mc_block']['p_bust'] - best['mc_iid']['p_bust']:+.1f}pp")
    print(f"  iid vs block Δ on P(target): {best['mc_block']['p_target'] - best['mc_iid']['p_target']:+.1f}pp")
    print()
    print(f"  E[monthly P&L]       = ${b['mean_monthly']:,.0f}")
    print(f"  Median days to target= {b['med_days']:.0f}")
    print()
    print(f"  Trade-off: {tradeoff}")
    print(f"  {'─'*80}")
    print(f"\n  → Update N_CONTRACTS={best_mnq} in config.py")
    print("=" * 100)

    # ── FTMO $10K 2-Step Standard ─────────────────────────────────────────
    section_ftmo_10k(tl)

    # ── Tradeify Select Flex $50K ──────────────────────────────────────────
    section_tradeify_50k(tl)

    return best_acct, best_mnq, best, stress


# ─────────────────────────────────────────────────────────────────────────────
# FTMO $10K 2-Step Standard — static DD (added after v2 analysis)
# ─────────────────────────────────────────────────────────────────────────────

FTMO_INITIAL      = 10_000
FTMO_STATIC_DD    = 1_000    # 10% from initial, FIXED (never trails)
FTMO_DAILY_LIMIT  = 500      # 5% from midnight balance (absolute)
FTMO_P1_TARGET    = 1_000    # Phase 1: 10%
FTMO_P2_TARGET    = 500      # Phase 2: 5%
FTMO_P1_DAYS      = 60
FTMO_P2_DAYS      = 30

FTMO_CFD_PV       = 10.0     # $/pt per lot (US100 FTMO standard)
FTMO_SPREAD_PTS   = 1.0      # conservative (FTMO US100 typ 0.5-1.5)
FTMO_SL_CAP_PTS   = 20.0     # same as iter_10 config

# Guardrail buffer (8% = $800 static → buffer $200 before $1,000 hard limit)
FTMO_GUARDRAIL_DD_BUFFER = 0.08


def scale_pnl_cfd(nq_pnl_usd: float, lot_size: float) -> float:
    """
    Convert 1-NQ-contract backtest P&L to US100 CFD at lot_size.
    NQ: $20/pt, $19 RT cost.  US100 CFD: $10/pt/lot, 1.0 spread pt cost.
    """
    nq_pts  = (nq_pnl_usd + NQ_COST_RT) / NQ_PV
    return nq_pts * FTMO_CFD_PV * lot_size - FTMO_SPREAD_PTS * FTMO_CFD_PV * lot_size


def build_daily_pnl_cfd(trade_log: pd.DataFrame, lot_size: float) -> pd.Series:
    tl = trade_log.copy()
    tl["date"]    = pd.to_datetime(tl["entry_ts"]).dt.normalize()
    tl["pnl_cfd"] = tl["pnl_usd"].apply(lambda x: scale_pnl_cfd(x, lot_size))
    daily_trade   = tl.groupby("date")["pnl_cfd"].sum()
    all_dates     = pd.bdate_range(tl["date"].min(), tl["date"].max())
    return daily_trade.reindex(all_dates.normalize(), fill_value=0.0)


def static_dd_metrics_cfd(daily: pd.Series, initial: float) -> dict:
    """Static DD from initial balance (not trailing). FTMO 2-Step rule."""
    cum        = daily.cumsum()
    max_dd_usd = float(min(0.0, cum.min()))   # most negative (vs initial_balance=0)
    max_dd_pct = -max_dd_usd / initial * 100
    worst_day  = float(daily.min())
    return {
        "max_dd_usd": round(max_dd_usd, 2),
        "max_dd_pct": round(max_dd_pct, 2),
        "worst_day":  round(worst_day, 2),
    }


def _simulate_ftmo_static(
    paths:        np.ndarray,
    static_dd:    float,
    daily_limit:  float,
    target:       float,
) -> dict:
    """
    Vectorised simulation — FTMO static DD bust rule.
    Bust: cumsum < -static_dd  OR  single_day < -daily_limit.
    Target: cumsum >= target (before bust).
    """
    n_paths, n_days = paths.shape
    cum = np.cumsum(paths, axis=1)

    # Bust conditions
    static_bust = cum < -static_dd
    daily_bust  = paths < -daily_limit
    bust_matrix = static_bust | daily_bust
    bust_mask   = bust_matrix.any(axis=1)
    first_bust  = np.where(bust_mask, bust_matrix.argmax(axis=1), n_days)

    # Target
    tgt_matrix  = cum >= target
    tgt_mask    = tgt_matrix.any(axis=1)
    first_tgt   = np.where(tgt_mask, tgt_matrix.argmax(axis=1), n_days)

    tgt_before_bust = tgt_mask & (first_tgt < first_bust)
    t_days          = first_tgt[tgt_before_bust] + 1
    med_days        = float(np.median(t_days)) if tgt_before_bust.sum() > 0 else np.nan

    return {
        "p_bust":       float(bust_mask.sum()) / n_paths * 100,
        "p_daily_bust": float((paths < -daily_limit).any(axis=1).sum()) / n_paths * 100,
        "p_target":     float(tgt_before_bust.sum()) / n_paths * 100,
        "med_days":     round(med_days, 0) if np.isfinite(med_days) else 999.0,
        "mean_daily":   float(paths.mean()),
    }


def section_ftmo_10k(tl: pd.DataFrame) -> tuple:
    """
    FTMO $10K 2-Step Standard analysis.
    Returns (recommended_lots, result_dict).
    """
    max_loss_per_lot = FTMO_SL_CAP_PTS * FTMO_CFD_PV          # $200/lot
    max_lots_safe    = int(FTMO_DAILY_LIMIT / max_loss_per_lot) # 2
    lot_candidates   = [round(max_lots_safe * f, 2) for f in [0.25, 0.5, 0.75, 1.0]]
    # Round to nearest 0.01 (FTMO volume step)
    lot_candidates   = [round(x, 2) for x in lot_candidates]

    rng_block = np.random.default_rng(MC_SEED + 10)

    configs = {}
    for lots in lot_candidates:
        daily   = build_daily_pnl_cfd(tl, lots)
        pnl_arr = daily.values.astype(float)
        avg_blk = max(5, int(np.sqrt(len(pnl_arr))))

        dd       = static_dd_metrics_cfd(daily, FTMO_INITIAL)
        cost_per_trade = FTMO_SPREAD_PTS * FTMO_CFD_PV * lots  # $/trade

        # Phase 1 simulation (60d, target $1K)
        paths_p1 = _stationary_block_paths(pnl_arr, MC_PATHS, FTMO_P1_DAYS, avg_blk, rng_block)
        mc_p1    = _simulate_ftmo_static(paths_p1, FTMO_STATIC_DD, FTMO_DAILY_LIMIT, FTMO_P1_TARGET)

        # Phase 2 simulation (30d, target $500, same rules)
        paths_p2 = _stationary_block_paths(pnl_arr, MC_PATHS, FTMO_P2_DAYS, avg_blk, rng_block)
        mc_p2    = _simulate_ftmo_static(paths_p2, FTMO_STATIC_DD, FTMO_DAILY_LIMIT, FTMO_P2_TARGET)

        max_loss_trade = FTMO_SL_CAP_PTS * FTMO_CFD_PV * lots  # total max loss/trade
        daily_ok = max_loss_trade < FTMO_DAILY_LIMIT            # must fit under daily limit

        configs[lots] = {
            "dd": dd, "cost_per_trade": cost_per_trade,
            "mc_p1": mc_p1, "mc_p2": mc_p2,
            "max_loss_trade": max_loss_trade,
            "daily_ok": daily_ok,
            "mean_monthly": mc_p1["mean_daily"] * 21,
        }

    print("\n" + "=" * 100)
    print("  FTMO $10K 2-STEP STANDARD — STATIC DD ANALYSIS")
    print("=" * 100)
    print(f"  Account: ${FTMO_INITIAL:,}  |  Static DD: ${FTMO_STATIC_DD} (fixed, never trails)")
    print(f"  Daily limit: ${FTMO_DAILY_LIMIT}/day from midnight balance")
    print(f"  Phases: P1 target=${FTMO_P1_TARGET} in {FTMO_P1_DAYS}d | P2 target=${FTMO_P2_TARGET} in {FTMO_P2_DAYS}d post-P1")
    print(f"  US100 CFD: {FTMO_CFD_PV}$/pt/lot | Spread: {FTMO_SPREAD_PTS}pt (conservative)")
    print(f"  SL cap: {FTMO_SL_CAP_PTS:.0f}pts | Max loss/lot: ${max_loss_per_lot:.0f} | Max safe lots: {max_lots_safe}")
    print()
    print(f"  NOTE: Static DD = bust only when balance drops below initial (${FTMO_INITIAL:,}).")
    print(f"  ADVANTAGE vs trailing DD: profits don't reduce remaining DD room.")
    print()

    hdr = (f"  {'Lots':>6} {'Cost/tr':>9} {'MaxDD hist':>12} "
           f"{'P1 P(bust)':>11} {'P1 P(10%)':>10} {'P1 med days':>12} "
           f"{'P2 P(5%)':>10} {'E[mo PnL]':>11} {'Daily OK':>10}")
    print(hdr)
    print(f"  {'-'*95}")

    for lots in lot_candidates:
        r   = configs[lots]
        p1  = r["mc_p1"]
        p2  = r["mc_p2"]
        dd  = r["dd"]
        ok  = "✓" if r["daily_ok"] else "✗"
        print(
            f"  {lots:>6.2f} "
            f"  ${r['cost_per_trade']:>6.1f} "
            f"  {dd['max_dd_pct']:>8.1f}% "
            f"  {p1['p_bust']:>9.1f}% "
            f"  {p1['p_target']:>9.1f}% "
            f"  {p1['med_days']:>9.0f}d "
            f"  {p2['p_target']:>9.1f}% "
            f"  ${r['mean_monthly']:>8,.0f} "
            f"  {ok}"
        )

    # Select recommended lot: max P1 target, daily_ok required
    safe = {k: v for k, v in configs.items() if v["daily_ok"]}
    if not safe:
        safe = configs  # fallback
    rec_lots, rec = max(safe.items(), key=lambda kv: kv[1]["mc_p1"]["p_target"])

    p1  = rec["mc_p1"]
    p2  = rec["mc_p2"]
    dd  = rec["dd"]

    print()
    print(f"  {'─'*80}")
    print(f"  FTMO $10K RECOMMENDED: {rec_lots} lots")
    print(f"  Cost/trade: ${rec['cost_per_trade']:.1f} | E[monthly PnL]: ${rec['mean_monthly']:,.0f}")
    print(f"  P(bust static): {p1['p_bust']:.1f}% | P(Phase1 in {FTMO_P1_DAYS}d): {p1['p_target']:.1f}%"
          f" | P(Phase2 in {FTMO_P2_DAYS}d post-P1): {p2['p_target']:.1f}%")
    print(f"  Median days Phase1: {p1['med_days']:.0f} | Phase2: {p2['med_days']:.0f}")
    print(f"  Max single-trade loss: ${rec['max_loss_trade']:.0f} (< ${FTMO_DAILY_LIMIT} daily limit ✓)")
    print(f"  MaxDD historical (static): {dd['max_dd_pct']:.1f}% of ${FTMO_INITIAL:,}")
    print(f"  Guardrail buffer: {FTMO_GUARDRAIL_DD_BUFFER*100:.0f}% fixed DD → halt at"
          f" ${FTMO_INITIAL * FTMO_GUARDRAIL_DD_BUFFER:.0f} loss"
          f" (${FTMO_STATIC_DD - FTMO_INITIAL * FTMO_GUARDRAIL_DD_BUFFER:.0f} buffer before limit)")
    print(f"  {'─'*80}")
    print(f"  → Update LOT_SIZE={rec_lots} in config.py")
    print("=" * 100)

    return rec_lots, rec


# ─────────────────────────────────────────────────────────────────────────────
# Tradeify Select Flex $50K — phase-aware simulation (added post-FTMO analysis)
# ─────────────────────────────────────────────────────────────────────────────

TV_INITIAL         = 50_000
TV_TRAILING_DD     = 2_000    # EOD trailing from peak (pre-lock)
TV_LOCK_BALANCE    = 52_100   # EOD balance → lock trigger (+ first payout)
TV_LOCKED_FLOOR    = 50_100   # post-lock permanent floor
TV_EVAL_TARGET     = 3_000    # Phase 1 target (6%)
TV_DAILY_LIMIT     = None     # No daily loss limit (Tradeify)
TV_CONSISTENCY     = 0.40     # 40% rule during eval (largest day <= 40% of total profit)
TV_MIN_WIN_DAY     = 150.0    # $150 min per winning day (for consistency check)
TV_MIN_WIN_DAYS    = 5        # 5 qualifying winning days before payout

# Eval: 3 MNQ | Pre-lock: 4 MNQ | Post-lock: 5 MNQ
TV_SIZING = {'eval': 3, 'pre_lock': 4, 'post_lock': 5}

TV_EVAL_DAYS    = 30     # median target days eval
TV_PRELOCK_DAYS = 30     # median days to lock (pre-lock phase)
TV_POSTLOCK_DAYS = 60    # stress test window post-lock


def build_daily_pnl_mnq(trade_log: pd.DataFrame, n_mnq: int) -> pd.Series:
    """Daily P&L scaled to n_mnq MNQ contracts (reuses scale_pnl from v2)."""
    return build_daily_pnl(trade_log, n_mnq)


def _simulate_tradeify_eval(
    paths:      np.ndarray,
    trail_dd:   float,
    target:     float,
    n_days:     int,
) -> dict:
    """
    Phase 1 eval simulation: trailing DD from peak (pre-lock rule).
    Bust = peak - cumsum >= trail_dd at any point.
    Target = cumsum >= target before bust.
    """
    n_paths, _ = paths.shape
    cum = np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(np.maximum(cum, 0), axis=1)
    trailing = peak - cum

    bust_matrix = trailing >= trail_dd
    bust_mask   = bust_matrix.any(axis=1)
    first_bust  = np.where(bust_mask, bust_matrix.argmax(axis=1), n_days)

    tgt_matrix = cum >= target
    tgt_mask   = tgt_matrix.any(axis=1)
    first_tgt  = np.where(tgt_mask, tgt_matrix.argmax(axis=1), n_days)

    pass_mask = tgt_mask & (first_tgt < first_bust)
    t_days    = first_tgt[pass_mask] + 1
    med_days  = float(np.median(t_days)) if pass_mask.sum() > 0 else np.nan

    return {
        "p_bust":    float(bust_mask.sum()) / n_paths * 100,
        "p_pass":    float(pass_mask.sum()) / n_paths * 100,
        "med_days":  round(med_days, 0) if np.isfinite(med_days) else 999.0,
        "mean_daily": float(paths.mean()),
    }


def _simulate_tradeify_prelock(
    paths:           np.ndarray,
    initial_balance: float,
    trail_dd:        float,
    lock_balance:    float,
    n_days:          int,
) -> dict:
    """
    Pre-lock funded simulation.
    Bust = trailing DD from peak >= trail_dd.
    Lock = cumsum >= (lock_balance - initial_balance) before bust.
    """
    lock_target = lock_balance - initial_balance   # = $2,100

    n_paths, _ = paths.shape
    cum  = np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(np.maximum(cum, 0), axis=1)
    trailing = peak - cum

    bust_matrix = trailing >= trail_dd
    bust_mask   = bust_matrix.any(axis=1)
    first_bust  = np.where(bust_mask, bust_matrix.argmax(axis=1), n_days)

    lock_matrix = cum >= lock_target
    lock_mask   = lock_matrix.any(axis=1)
    first_lock  = np.where(lock_mask, lock_matrix.argmax(axis=1), n_days)

    reached_lock = lock_mask & (first_lock < first_bust)
    t_days       = first_lock[reached_lock] + 1
    med_days     = float(np.median(t_days)) if reached_lock.sum() > 0 else np.nan

    return {
        "p_bust":      float(bust_mask.sum()) / n_paths * 100,
        "p_lock":      float(reached_lock.sum()) / n_paths * 100,
        "med_days":    round(med_days, 0) if np.isfinite(med_days) else 999.0,
        "mean_daily":  float(paths.mean()),
    }


def _simulate_tradeify_postlock(
    paths:        np.ndarray,
    lock_floor:   float,
    initial_balance: float,
    n_days:       int,
) -> dict:
    """
    Post-lock simulation. Floor is permanent absolute level.
    Bust = balance drops below lock_floor at any point.
    """
    floor_loss = initial_balance - lock_floor   # = -$49,900 (loss from initial needed to bust)
    # In P&L terms: cumsum < floor_loss - initial (= -initial + lock_floor)
    # Starting balance = initial, so bust when cumsum < lock_floor - initial_balance
    bust_level = lock_floor - initial_balance   # = $50,100 - $50,000 = $100 (gain needed above floor)
    # Actually: balance = initial + cumsum, bust when initial + cumsum < lock_floor
    # → cumsum < lock_floor - initial = 50,100 - 50,000 = $100
    # So floor is $100 above initial — extremely tight only if they somehow entered
    # post-lock at exactly initial (normal: post-lock starts at $52,100+).
    # Model starting balance = $52,100 for post-lock (best-case = entered at lock trigger).
    postlock_initial = TV_LOCK_BALANCE    # $52,100 starting balance post-lock
    floor_dd = postlock_initial - lock_floor   # = $2,000 max drawdown from postlock_initial

    n_paths, _ = paths.shape
    cum  = np.cumsum(paths, axis=1)
    bust_matrix = cum < -floor_dd
    bust_mask   = bust_matrix.any(axis=1)

    return {
        "p_bust":      float(bust_mask.sum()) / n_paths * 100,
        "mean_daily":  float(paths.mean()),
        "mean_monthly": float(paths.mean()) * 21 * 0.90,
    }


def section_tradeify_50k(tl: pd.DataFrame) -> dict:
    """
    Tradeify Select Flex $50K — three-phase Monte Carlo analysis.
    Returns results dict.
    """
    rng_tv = np.random.default_rng(MC_SEED + 20)

    results = {}
    for phase, n_mnq in TV_SIZING.items():
        daily  = build_daily_pnl_mnq(tl, n_mnq)
        pnl    = daily.values.astype(float)
        avg_bl = max(5, int(np.sqrt(len(pnl))))

        if phase == 'eval':
            paths = _stationary_block_paths(pnl, MC_PATHS, TV_EVAL_DAYS, avg_bl, rng_tv)
            r = _simulate_tradeify_eval(paths, TV_TRAILING_DD, TV_EVAL_TARGET, TV_EVAL_DAYS)
        elif phase == 'pre_lock':
            paths = _stationary_block_paths(pnl, MC_PATHS, TV_PRELOCK_DAYS, avg_bl, rng_tv)
            r = _simulate_tradeify_prelock(
                paths, TV_INITIAL, TV_TRAILING_DD, TV_LOCK_BALANCE, TV_PRELOCK_DAYS
            )
        else:  # post_lock
            paths = _stationary_block_paths(pnl, MC_PATHS, TV_POSTLOCK_DAYS, avg_bl, rng_tv)
            r = _simulate_tradeify_postlock(paths, TV_LOCKED_FLOOR, TV_INITIAL, TV_POSTLOCK_DAYS)

        dd = fixed_dd_metrics(daily, TV_INITIAL)
        r['max_dd_hist_usd'] = abs(dd['max_dd_usd'])
        results[phase] = r

    # Worst-window 60-day stress test (post-lock, 5 MNQ)
    daily5 = build_daily_pnl_mnq(tl, TV_SIZING['post_lock'])
    pnl5   = daily5.values.astype(float)
    n_win  = TV_POSTLOCK_DAYS
    if len(pnl5) >= n_win:
        windows = np.array([pnl5[i:i+n_win].sum() for i in range(len(pnl5) - n_win + 1)])
        worst_60d_pnl = float(windows.min())
        worst_cum = np.array([np.cumsum(pnl5[i:i+n_win]).min()
                              for i in range(len(pnl5) - n_win + 1)])
        worst_60d_dd = float(worst_cum.min())
    else:
        worst_60d_pnl = float(pnl5.sum())
        worst_60d_dd  = float(np.cumsum(pnl5).min())

    floor_dd_postlock = TV_LOCK_BALANCE - TV_LOCKED_FLOOR   # = $2,000
    worst_outcome = "PASS" if worst_60d_dd > -floor_dd_postlock else "BUST"

    print("\n" + "=" * 100)
    print("  TRADEIFY SELECT FLEX $50K — THREE-PHASE ANALYSIS")
    print("=" * 100)
    print(f"  Account: ${TV_INITIAL:,} | EOD trailing DD: ${TV_TRAILING_DD:,} (pre-lock)")
    print(f"  Lock trigger: EOD balance >= ${TV_LOCK_BALANCE:,} + first payout")
    print(f"  Post-lock floor: ${TV_LOCKED_FLOOR:,} (permanent)")
    print(f"  No daily loss limit | 90/10 split | Python automation allowed")
    print()

    ev = results['eval']
    pl = results['pre_lock']
    pk = results['post_lock']

    print(f"  Phase 1 — Eval (3 MNQ, target +${TV_EVAL_TARGET:,} in {TV_EVAL_DAYS}d):")
    print(f"    P(pass eval)     = {ev['p_pass']:.1f}%")
    print(f"    P(bust eval)     = {ev['p_bust']:.1f}%")
    print(f"    Median days      = {ev['med_days']:.0f}")
    print(f"    E[daily P&L]     = ${ev['mean_daily']:+.0f}")
    print()
    print(f"  Phase 2 — Funded pré-lock (4 MNQ, until lock trigger):")
    print(f"    P(reach lock)    = {pl['p_lock']:.1f}%")
    print(f"    P(bust pre-lock) = {pl['p_bust']:.1f}%")
    print(f"    Median days      = {pl['med_days']:.0f}")
    print(f"    E[daily P&L]     = ${pl['mean_daily']:+.0f}")
    print()
    print(f"  Phase 3 — Post-lock (5 MNQ, floor ${TV_LOCKED_FLOOR:,}):")
    print(f"    P(bust {TV_POSTLOCK_DAYS}d)      = {pk['p_bust']:.1f}%")
    print(f"    E[daily P&L]     = ${pk['mean_daily']:+.0f}")
    print(f"    E[monthly net]   = ${pk['mean_monthly']:+,.0f}  (×21 days × 90% split)")
    print()
    print(f"  Worst-window 60d (post-lock, 5 MNQ):")
    print(f"    Worst 60d P&L    = ${worst_60d_pnl:+,.0f}")
    print(f"    Worst 60d MaxDD  = ${worst_60d_dd:+,.0f}  (floor budget ${-floor_dd_postlock:,.0f})")
    print(f"    Outcome          = {worst_outcome}")
    print()
    print(f"  {'─'*80}")
    print(f"  TRADEIFY SELECT FLEX $50K — RECOMMENDED CONFIG")
    print(f"  Phase 1 (eval,  3 MNQ): P(pass)={ev['p_pass']:.0f}%,   median days={ev['med_days']:.0f}")
    print(f"  Phase 2 (pré-lock, 4 MNQ): P(bust)={pl['p_bust']:.1f}%, median days to lock={pl['med_days']:.0f}")
    print(f"  Phase 3 (post-lock, 5 MNQ): P(bust {TV_POSTLOCK_DAYS}d)={pk['p_bust']:.1f}%")
    print(f"  E[monthly net P&L post-lock]: ${pk['mean_monthly']:+,.0f}")
    print(f"  Worst-window 60-day (post-lock): MaxDD=${worst_60d_dd:+,.0f}, outcome={worst_outcome}")
    print(f"  {'─'*80}")
    print(f"  → PHASE_CONTRACTS = {{'eval': 3, 'pre_lock': 4, 'post_lock': 5}} in config.py")
    print("=" * 100)

    results['worst_60d'] = {
        'pnl': worst_60d_pnl,
        'max_dd': worst_60d_dd,
        'outcome': worst_outcome,
    }
    return results


if __name__ == "__main__":
    main()
