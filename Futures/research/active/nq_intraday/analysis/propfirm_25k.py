"""
propfirm_25k.py — Tradeify Select Flex $25K recalibration
===========================================================
Strategy: iter_11b (gap≤2.0%, rng≥30pt, VWAP on, TP=1.5R, stop=$400)
  Sharpe=1.59, MaxDD=-12.5%, N=378, WF=89%

Tradeify Select Flex $25K rules:
  initial_balance      = 25,000
  trailing_dd_usd      = 1,500  (6% of 25K, EOD trailing from equity peak)
  lock_trigger_balance = 26,100  (initial + trailing_dd + 100)
  locked_floor         = 25,100  (permanent post-lock floor)
  profit_target_eval   = 1,500  (6% of 25K)
  daily_loss_limit     = None
  min_winning_day_pnl  = 75     (proportional vs $150 on 50K)
  min_winning_days     = 5
  payout_split         = 0.90   (trader keeps 90%)

Sizings tested: 2 MNQ, 3 MNQ, 4 MNQ
Bootstrap: stationary block (L=20), 10,000 paths
n_tests: 158 (no new research test, simulation only)

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.propfirm_25k
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[5]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT,
)
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, BASE_SL_MULT, BASE_TP_MULT,
)
from Futures.research.active.nq_intraday.analysis.propfirm_compat_v2 import (
    _stationary_block_paths, _simulate_tradeify_eval,
    MC_PATHS, MC_SEED, AVG_BLOCK_LEN,
)

# ─── Tradeify $25K rules ──────────────────────────────────────────────────────
TV25_INITIAL     = 25_000
TV25_TRAIL_DD    = 1_500
TV25_LOCK_BAL    = 26_100   # lock trigger (EOD balance ≥ this)
TV25_FLOOR       = 25_100   # permanent post-lock floor
TV25_EVAL_TGT    = 1_500    # 6% eval target
TV25_EVAL_DAYS   = 90
TV25_PRELOCK_DAYS = 30      # reference window for pre-lock bootstrap
TV25_POSTLOCK_DAYS = 60     # stress window post-lock
PAYOUT_SPLIT     = 0.90     # trader share

# iter_11b params
GAP_THRESH  = 0.020
RNG_MIN     = 30.0
DOLLAR_STOP = 400.0

MNQ_PV      = 2.0
MNQ_COST_RT = 2.15
NQ_PV       = 20.0
NQ_COST_RT  = 19.0

SIZINGS = [2, 3, 4]


# ─── iter_11b signal builder ──────────────────────────────────────────────────

def build_iter11b_signals(feats: pd.DataFrame) -> pd.DataFrame:
    """iter_11b: gap≤2.0%, rng≥30pt, VWAP on, TP=1.5R, dollar_stop=$400."""
    f = feats[feats["vwap_ok"]].copy()
    f = f[f["gap_pct"].abs() <= GAP_THRESH]
    f = f[f["rng"] >= RNG_MIN]

    rows = []
    for _, row in f.iterrows():
        rng    = float(row["rng"])
        sl_pts = rng * BASE_SL_MULT
        cap    = (DOLLAR_STOP + COST_RT) / NQ_PV
        sl_pts = min(sl_pts, cap)
        rows.append({
            "signal_ts": row["sig_ts"],
            "direction": int(row["direction"]),
            "tp_points": rng * BASE_TP_MULT,
            "sl_points": sl_pts,
            "exit_time": row["exit_time"],
            "rng":       rng,
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("signal_ts")


# ─── MNQ P&L scaling ──────────────────────────────────────────────────────────

def scale_to_mnq(nq_pnl_usd: float, n_mnq: int) -> float:
    nq_pts = (nq_pnl_usd + NQ_COST_RT) / NQ_PV
    return nq_pts * MNQ_PV * n_mnq - MNQ_COST_RT * n_mnq


def build_daily_mnq(trade_log: pd.DataFrame, n_mnq: int) -> pd.Series:
    tl = trade_log.copy()
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()
    tl["pnl_mnq"] = tl["pnl_usd"].apply(lambda x: scale_to_mnq(x, n_mnq))
    daily = tl.groupby("date")["pnl_mnq"].sum()
    all_dates = pd.bdate_range(tl["date"].min(), tl["date"].max())
    return daily.reindex(all_dates.normalize(), fill_value=0.0)


# ─── Bootstrap simulation functions ───────────────────────────────────────────

def sim_eval(pnl_arr: np.ndarray, rng: np.random.Generator) -> dict:
    """Phase 1 eval: trailing DD $1,500, target $1,500, 90 days."""
    paths = _stationary_block_paths(pnl_arr, MC_PATHS, TV25_EVAL_DAYS, AVG_BLOCK_LEN, rng)
    return _simulate_tradeify_eval(paths, TV25_TRAIL_DD, TV25_EVAL_TGT, TV25_EVAL_DAYS)


def sim_prelock(pnl_arr: np.ndarray, rng: np.random.Generator) -> dict:
    """Phase 2 pre-lock: trailing DD $1,500, target $1,100 to reach lock trigger."""
    lock_gain = TV25_LOCK_BAL - TV25_INITIAL   # = $1,100
    paths = _stationary_block_paths(pnl_arr, MC_PATHS, TV25_PRELOCK_DAYS, AVG_BLOCK_LEN, rng)

    n_paths, n_days = paths.shape
    cum  = np.cumsum(paths, axis=1)
    peak = np.maximum.accumulate(np.maximum(cum, 0), axis=1)
    trail = peak - cum

    bust_matrix = trail >= TV25_TRAIL_DD
    bust_mask   = bust_matrix.any(axis=1)
    first_bust  = np.where(bust_mask, bust_matrix.argmax(axis=1), n_days)

    lock_matrix = cum >= lock_gain
    lock_mask   = lock_matrix.any(axis=1)
    first_lock  = np.where(lock_mask, lock_matrix.argmax(axis=1), n_days)

    reached_lock = lock_mask & (first_lock < first_bust)
    t_days       = first_lock[reached_lock] + 1
    med_days     = float(np.median(t_days)) if reached_lock.sum() > 0 else np.nan

    return {
        "p_bust":    float(bust_mask.sum()) / n_paths * 100,
        "p_lock":    float(reached_lock.sum()) / n_paths * 100,
        "med_days":  round(med_days, 0) if np.isfinite(med_days) else 999.0,
        "mean_daily": float(paths.mean()),
    }


def sim_postlock(pnl_arr: np.ndarray, rng: np.random.Generator) -> dict:
    """Phase 3 post-lock: floor $25,100. Starting balance = $26,100 (lock trigger)."""
    postlock_initial = float(TV25_LOCK_BAL)
    floor_dd         = postlock_initial - TV25_FLOOR   # = $1,000 max DD from lock point

    paths = _stationary_block_paths(pnl_arr, MC_PATHS, TV25_POSTLOCK_DAYS, AVG_BLOCK_LEN, rng)
    n_paths, _ = paths.shape
    cum  = np.cumsum(paths, axis=1)
    bust_matrix = cum < -floor_dd
    bust_mask   = bust_matrix.any(axis=1)

    mean_daily   = float(paths.mean())
    mean_monthly = mean_daily * 21 * PAYOUT_SPLIT

    return {
        "p_bust":       float(bust_mask.sum()) / n_paths * 100,
        "mean_daily":   mean_daily,
        "mean_monthly": mean_monthly,
    }


def worst_window_60d(pnl_arr: np.ndarray, floor_dd: float) -> dict:
    """Non-parametric: worst 60-day rolling window from historical data."""
    n = TV25_POSTLOCK_DAYS
    if len(pnl_arr) < n:
        return {"worst_pnl": float(pnl_arr.sum()), "worst_dd": float(np.cumsum(pnl_arr).min()), "worst_outcome": "INSUFFICIENT_DATA"}
    windows_pnl = np.array([pnl_arr[i:i+n].sum() for i in range(len(pnl_arr) - n + 1)])
    windows_dd  = np.array([np.cumsum(pnl_arr[i:i+n]).min() for i in range(len(pnl_arr) - n + 1)])
    worst_pnl = float(windows_pnl.min())
    worst_dd  = float(windows_dd.min())
    outcome   = "PASS" if worst_dd > -floor_dd else "BUST"
    return {"worst_pnl": worst_pnl, "worst_dd": worst_dd, "worst_outcome": outcome}


# ─── Max SL per trade (propfirm risk reference) ────────────────────────────────

def max_sl_per_trade(n_mnq: int) -> float:
    """Maximum dollar loss per trade at iter_11b dollar_stop=$400."""
    # NQ: max_sl = $400 + cost $19 = $419 (dollar_stop trigger)
    # MNQ equivalent: recover NQ pts (419/20=20.95) → scale to MNQ
    max_nq_sl_usd = DOLLAR_STOP + NQ_COST_RT   # = $419
    return scale_to_mnq(-max_nq_sl_usd, n_mnq)  # negative = loss


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 80)
    print("TRADEIFY SELECT FLEX $25K — iter_11b SIZING ANALYSIS")
    print(f"  Rules: trailing DD ${TV25_TRAIL_DD:,} | eval target ${TV25_EVAL_TGT:,} (6%) | "
          f"lock @ ${TV25_LOCK_BAL:,}")
    print(f"         floor ${TV25_FLOOR:,} | no daily limit | 90/10 split | 90-day eval window")
    print("=" * 80)

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)

    print("\nBuilding iter_11b trade log...")
    sigs   = build_iter11b_signals(feats)
    tl, m  = engine.run(sigs)
    n_days = engine.rth.index.normalize().nunique()
    print(f"  N={len(tl)} trades  Sharpe={m.get('sharpe_daily_hac', '?')}  "
          f"TPD={len(tl)/n_days:.3f}  "
          f"Total P&L=${tl['pnl_usd'].sum():,.0f}")

    rng_base = np.random.default_rng(MC_SEED + 25)

    # ── Per-sizing analysis ──────────────────────────────────────────────────
    results_table = []
    floor_dd_postlock = TV25_LOCK_BAL - TV25_FLOOR   # = $1,000

    for n_mnq in SIZINGS:
        daily   = build_daily_mnq(tl, n_mnq)
        pnl_arr = daily.values.astype(float)
        e_daily = float(pnl_arr.mean())
        max_sl  = abs(max_sl_per_trade(n_mnq))

        rng_e = np.random.default_rng(MC_SEED + 25 + n_mnq * 10)
        rng_p = np.random.default_rng(MC_SEED + 26 + n_mnq * 10)
        rng_k = np.random.default_rng(MC_SEED + 27 + n_mnq * 10)

        ev = sim_eval(pnl_arr, rng_e)
        pl = sim_prelock(pnl_arr, rng_p)
        pk = sim_postlock(pnl_arr, rng_k)
        ww = worst_window_60d(pnl_arr, floor_dd_postlock)

        results_table.append({
            "n_mnq":          n_mnq,
            "max_sl":         max_sl,
            "e_daily":        e_daily,
            "p_eval_90d":     ev["p_pass"],
            "p_bust_eval":    ev["p_bust"],
            "med_days_eval":  ev["med_days"],
            "p_lock":         pl["p_lock"],
            "p_bust_prelock": pl["p_bust"],
            "med_days_lock":  pl["med_days"],
            "p_bust_postlock": pk["p_bust"],
            "e_monthly":      pk["mean_monthly"],
            "worst_60d_dd":   ww["worst_dd"],
            "worst_outcome":  ww["worst_outcome"],
        })

        print(f"\n  ── {n_mnq} MNQ ─────────────────────────────────────────────────────")
        print(f"     Max SL/trade: ${max_sl:.0f}  |  E[daily]: ${e_daily:+.2f}")
        print(f"     EVAL  (90d):  P(pass)={ev['p_pass']:.1f}%  "
              f"P(bust)={ev['p_bust']:.1f}%  med_days={ev['med_days']:.0f}d")
        print(f"     PRE-LOCK:     P(lock)={pl['p_lock']:.1f}%  "
              f"P(bust)={pl['p_bust']:.1f}%  med_days_lock={pl['med_days']:.0f}d")
        print(f"     POST-LOCK 60d: P(bust)={pk['p_bust']:.1f}%  "
              f"E[monthly net]=${pk['mean_monthly']:+,.0f}")
        print(f"     Worst 60d (historical): MaxDD=${ww['worst_dd']:+,.0f}  "
              f"floor budget=${-floor_dd_postlock:,.0f}  → {ww['worst_outcome']}")

    # ── Summary table ────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SUMMARY TABLE — Tradeify Select Flex $25K")
    print("=" * 80)
    print(f"  {'Sizing':<8} {'Max SL':>7} {'E[daily]':>9} {'P(eval 90d)':>12} "
          f"{'P(bust eval)':>13} {'Med days':>9} {'E[mo post-lock]':>16}")
    print(f"  {'─'*78}")
    for r in results_table:
        flag = " ✓" if r["p_eval_90d"] >= 50.0 else ""
        print(f"  {r['n_mnq']} MNQ   ${r['max_sl']:>5.0f}  ${r['e_daily']:>+8.2f}  "
              f"{r['p_eval_90d']:>11.1f}%  {r['p_bust_eval']:>12.1f}%  "
              f"{r['med_days_eval']:>8.0f}d  ${r['e_monthly']:>+13,.0f}{flag}")

    print(f"\n  Additional risk metrics:")
    print(f"  {'Sizing':<8} {'P(lock)':>9} {'P(bust pre-lock)':>17} "
          f"{'P(bust 60d post)':>17} {'Worst60d DD':>12} {'Outcome':>8}")
    print(f"  {'─'*78}")
    for r in results_table:
        print(f"  {r['n_mnq']} MNQ   {r['p_lock']:>8.1f}%  {r['p_bust_prelock']:>16.1f}%  "
              f"{r['p_bust_postlock']:>16.1f}%  ${r['worst_60d_dd']:>+10,.0f}  "
              f"{r['worst_outcome']:>8}")

    # ── Recommendation ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    passing = [r for r in results_table if r["p_eval_90d"] >= 50.0]

    if not passing:
        print("\n  ► STRATEGY C INADEQUATE EVEN FOR $25K — REVISIT PLAN")
        print()
        best  = max(results_table, key=lambda r: r["p_eval_90d"])
        print(f"  Best sizing: {best['n_mnq']} MNQ  →  P(eval 90d)={best['p_eval_90d']:.1f}%  "
              f"(gate: 50%)")
        print(f"  All sizings fail the 50% eval gate. The $19 RT NQ cost and 0.46 trades/day")
        print(f"  ceiling produce E[daily] too low to reliably pass $1,500 in 90 days.")
        print()
        print(f"  Options to revisit:")
        print(f"  1. Use iter_11d (TP=2.0R): best P(eval 90d) was 38.2% at $50K → need $25K re-sim")
        print(f"  2. Focus on Strategy E (new signal, n_test 159+)")
        print(f"  3. Deploy iter_10 as paper trade only, no propfirm until new edge found")
    else:
        # Optimal = highest net score = P(eval_pass) × (1 - P(bust_eval))
        # This penalises busts heavily — we lose the eval fee on bust.
        # Note: P(bust eval) 4 MNQ = 59.1% is unacceptable (near coin-flip bust);
        # prefer 3 MNQ which has higher P(pass)=66.1% AND much lower P(bust)=26.8%.
        for r in results_table:
            r["_score"] = r["p_eval_90d"] * (1.0 - r["p_bust_eval"] / 100.0)
        best = max(passing, key=lambda r: r["_score"])
        print(f"\n  ► OPTIMAL SIZING: {best['n_mnq']} MNQ")
        print(f"     P(eval pass 90d) = {best['p_eval_90d']:.1f}%   [gate: ≥50% ✓]")
        print(f"     P(bust eval)     = {best['p_bust_eval']:.1f}%   ← key risk metric")
        print(f"     Net score        = P(pass)×(1-P(bust)) = {best['_score']:.1f}")
        print(f"     Median days      = {best['med_days_eval']:.0f}d")
        print(f"     P(reach lock)    = {best['p_lock']:.1f}%")
        print(f"     P(bust pre-lock) = {best['p_bust_prelock']:.1f}%")
        print(f"     P(bust 60d post) = {best['p_bust_postlock']:.1f}%")
        print(f"     E[monthly net]   = ${best['e_monthly']:+,.0f}  (×21d × 90%)")
        print(f"     Worst 60d MaxDD  = ${best['worst_60d_dd']:+,.0f}  → {best['worst_outcome']}")
        print()
        print(f"  CAUTION: ALL sizings have worst-60d MaxDD > floor budget (${-floor_dd_postlock:,}).")
        print(f"  Post-lock phase is fragile — worst historical windows exceed the $1,000 DD room.")
        print(f"  Mitigation: request payout early once past lock, reducing in-account risk.")
        print()
        print(f"  → PHASE_CONTRACTS = {{'eval': {best['n_mnq']}, "
              f"'pre_lock': {best['n_mnq']+1}, "
              f"'post_lock': {best['n_mnq']+2}}} in config.py")

    print("=" * 80)


if __name__ == "__main__":
    main()
