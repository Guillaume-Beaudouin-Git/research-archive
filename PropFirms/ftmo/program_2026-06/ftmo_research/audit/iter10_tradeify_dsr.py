"""
iter10_tradeify_dsr.py — Tradeify $25K p(pass) simulation + DSR for iter_10.

Tradeify simulation method:
  1. Load actual iter_10 trade log from Databento 2010-2026.
  2. Aggregate to daily P&L (in NQ $20/pt scale), include zero-trade days.
  3. Convert to MNQ scale at 2 contracts (per config.py): nq_pnl → mnq_pnl.
  4. Block bootstrap the daily series (block_size=20) → 20,000 MC paths
     of 360-day length (180 eval + 180 funded).
  5. Feed paths into simulate_n_runs from trailing_dd_simulator.py.
  6. Compute p(eval_pass), p(bust), expected funded PnL.

Three scenarios:
  A. Full Databento 2010-2026 sample (the honest, extended estimate)
  B. Databento 2022-2026 only (matches the original Kaggle window, but
     on Databento data)
  C. Reference: existing make_iter10_trade_generator with reported iter_10 stats
     (Sharpe 1.52, win_rate 27.75%, etc.) — to validate this is what was assumed.

DSR computation:
  - iter_10 family consumed 10+ iterations (iter_1a→iter_10) + 5+ sub-variants
    + various filter parameters tested (gap thresholds, stop sizes, vol_ratio,
    range_min). Honest n_trials estimate ≥ 15-25.
  - Apply Bailey-LdP DSR to the daily Sharpe of iter_10 on Databento
    full sample AND on 2022-2026.

Outputs:
  - iter10_tradeify.csv (p(pass), p(bust) per scenario)
  - iter10_dsr.csv
  - iter10_tradeify_dsr_output.txt
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import numpy as np
import pandas as pd
from scipy import stats as scstats

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2]))

from Portfolio.risk.trailing_dd_simulator import (
    simulate_n_runs, PropfirmConfig, make_iter10_trade_generator,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Tradeify Select Flex $25K canonical config — already the default in PropfirmConfig
CFG = PropfirmConfig(
    capital=25_000.0,
    profit_target=1_500.0,
    trailing_dd_eval=1_000.0,
    trailing_dd_funded=1_000.0,
    lock_trigger_excess=100.0,
    locked_floor_offset=100.0,
    consistency_cap_pct=0.40,
    max_eval_days=180,
    funded_days=180,
    payout_threshold_days=5,
    win_day_min_pnl=100.0,
    max_payout=1_250.0,
    payout_pct_of_profit=0.50,
)

# Sizing: 2 MNQ (per Futures/live/strategy_c_live/config.py)
N_MNQ = 2

# NQ/MNQ contract specs
NQ_COST_USD = 19.0
NQ_POINT_USD = 20.0
MNQ_POINT_USD = 2.0
MNQ_COST_USD = 2.15


def nq_to_mnq_pnl(nq_pnl: float, n_mnq: int = N_MNQ) -> float:
    """Convert NQ-scale per-trade $ PnL to MNQ-scale at n_mnq contracts.

    PnL_NQ = nq_pts × $20 − $19 (cost)
    PnL_MNQ(n contracts) = nq_pts × $2 × n − $2.15 × n
    Inverting: nq_pts = (PnL_NQ + $19) / $20
    """
    nq_pts = (nq_pnl + NQ_COST_USD) / NQ_POINT_USD
    return nq_pts * MNQ_POINT_USD * n_mnq - MNQ_COST_USD * n_mnq


def build_daily_mnq_pnl(trade_log: pd.DataFrame, n_mnq: int = N_MNQ) -> pd.Series:
    """Aggregate per-trade NQ $ PnL to daily MNQ $ PnL series.

    Includes zero-trade days. Index = business days in trade log range.
    """
    tl = trade_log.copy()
    tl["mnq_pnl"] = tl["pnl_usd"].apply(lambda x: nq_to_mnq_pnl(x, n_mnq))
    tl["entry_date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize().dt.tz_localize(None)
    daily = tl.groupby("entry_date")["mnq_pnl"].sum()
    all_dates = pd.bdate_range(daily.index.min(), daily.index.max())
    return daily.reindex(all_dates, fill_value=0.0)


def block_bootstrap_generator(daily_pnl: np.ndarray, n_days_required: int,
                                block_size: int = 20, seed: int | None = None):
    """Block bootstrap generator for simulate_n_runs."""
    rng = np.random.default_rng(seed)
    n = len(daily_pnl)
    if n < block_size * 2:
        raise ValueError(f"Daily series too short ({n}) for block_size {block_size}")
    n_blocks = (n_days_required // block_size) + 1

    def generate():
        starts = rng.integers(0, n, size=n_blocks)
        offsets = np.arange(block_size)
        idx = ((starts[:, None] + offsets[None, :]) % n).ravel()
        return daily_pnl[idx[:n_days_required]].astype(np.float64)
    return generate


# ---------------------------------------------------------------------------
# Bailey-LdP DSR
# ---------------------------------------------------------------------------

def dsr(sr_per_period: float, n_obs: int, n_trials: int,
         skew_r: float = 0.0, kurt_r: float = 3.0) -> dict:
    """Deflated Sharpe (Bailey-LdP 2014).

    SR_normalized = SR_obs × sqrt(T-1) / sqrt(1 - skew×SR + (kurt-1)/4 × SR²)
    E[max] of N i.i.d. N(0,1) ≈ (1-γ)Φ⁻¹(1-1/N) + γΦ⁻¹(1-1/(N·e))
    DSR = Φ(SR_normalized - E[max])
    """
    if n_trials < 2:
        emax = 0.0
    else:
        gamma = 0.5772156649
        emax = (1 - gamma) * scstats.norm.ppf(1 - 1.0 / n_trials) + \
                gamma * scstats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    denom = np.sqrt(max(1e-12, 1 - skew_r * sr_per_period + ((kurt_r - 1) / 4) * sr_per_period**2))
    sr_n = sr_per_period * np.sqrt(n_obs - 1) / denom
    z = sr_n - emax
    return {"sr_per_period": float(sr_per_period),
             "sr_normalized": round(float(sr_n), 3),
             "n_obs": int(n_obs),
             "n_trials": int(n_trials),
             "emax": round(float(emax), 4),
             "z": round(float(z), 3),
             "dsr_p": round(float(scstats.norm.cdf(z)), 4)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log.info("Loading iter_10 full trade log (Databento 2010-2026)...")
    tl = pd.read_parquet(ROOT / "iter10_trades_full.parquet")
    log.info(f"  {len(tl)} trades, {tl['entry_ts'].min()} -> {tl['entry_ts'].max()}")

    # Daily PnL series in MNQ scale
    daily_full = build_daily_mnq_pnl(tl, n_mnq=N_MNQ)
    log.info(f"  Daily PnL (MNQ x{N_MNQ}): {len(daily_full)} days, "
              f"mean=${daily_full.mean():.2f}, std=${daily_full.std():.2f}, "
              f"sum=${daily_full.sum():,.0f}")

    # Restrict to 2022-2026 for scenario B
    daily_2022 = daily_full[daily_full.index >= "2022-01-01"]
    log.info(f"  2022-2026 only: {len(daily_2022)} days, "
              f"mean=${daily_2022.mean():.2f}, std=${daily_2022.std():.2f}")

    print("\n" + "=" * 100)
    print("TRADEIFY SELECT FLEX $25K — p(pass) simulation")
    print("=" * 100)
    print(f"  Config: capital=$25K, eval DD=$1K trailing, profit target=$1.5K, "
           f"consistency cap 40%, min trading days=3")
    print(f"  Sizing: {N_MNQ} MNQ contracts (per config.py PHASE_CONTRACTS)")
    print(f"  Bootstrap block size: 20 days, 20,000 MC paths each scenario")
    print()

    # === Scenario A — Full sample 2010-2026 ===
    log.info("Scenario A: Full sample 2010-2026 block bootstrap...")
    gen_A = block_bootstrap_generator(daily_full.values,
                                       n_days_required=CFG.max_eval_days + CFG.funded_days,
                                       block_size=20, seed=42)
    sim_A = simulate_n_runs(20000, gen_A, config=CFG, payout_regime="no_payout")
    print(f"  [A] Full sample 2010-2026 (n_trades={len(tl)}, mean_R_daily=${daily_full.mean():.2f}):")
    print(f"      p(eval_pass): {sim_A.p_eval_pass*100:.2f}%")
    print(f"      p(bust):      {sim_A.p_bust*100:.2f}%")
    print(f"      p(timeout):   {sim_A.p_timeout*100:.2f}%")
    print(f"      E[days to target | passed]: {sim_A.e_days_to_target:.1f}")
    print(f"      E[funded PnL 180d | passed]: ${sim_A.e_funded_pnl_180d:.2f}")
    print()

    # === Scenario B — 2022-2026 only ===
    log.info("Scenario B: 2022-2026 only block bootstrap (matches Kaggle period)...")
    if len(daily_2022) >= 60:
        gen_B = block_bootstrap_generator(daily_2022.values,
                                           n_days_required=CFG.max_eval_days + CFG.funded_days,
                                           block_size=20, seed=42)
        sim_B = simulate_n_runs(20000, gen_B, config=CFG, payout_regime="no_payout")
        print(f"  [B] 2022-2026 sample only (n_trades=512 cherry-pick window):")
        print(f"      p(eval_pass): {sim_B.p_eval_pass*100:.2f}%")
        print(f"      p(bust):      {sim_B.p_bust*100:.2f}%")
        print(f"      p(timeout):   {sim_B.p_timeout*100:.2f}%")
        print(f"      E[days to target | passed]: {sim_B.e_days_to_target:.1f}")
        print(f"      E[funded PnL 180d | passed]: ${sim_B.e_funded_pnl_180d:.2f}")
        print()
    else:
        sim_B = None
        print(f"  [B] SKIPPED — insufficient 2022-2026 days ({len(daily_2022)})")
        print()

    # === Scenario C — Reference: existing make_iter10_trade_generator ===
    log.info("Scenario C: Reference using reported iter_10 stats...")
    gen_C = make_iter10_trade_generator(
        n_days=CFG.max_eval_days + CFG.funded_days, n_mnq=N_MNQ, seed=42)
    sim_C = simulate_n_runs(20000, gen_C, config=CFG, payout_regime="no_payout")
    print(f"  [C] Reference (reported iter_10 stats: win_rate=27.75%, "
           f"avg_winner=$1572, avg_loser=-$421, trade_freq=45.8%):")
    print(f"      p(eval_pass): {sim_C.p_eval_pass*100:.2f}%")
    print(f"      p(bust):      {sim_C.p_bust*100:.2f}%")
    print(f"      p(timeout):   {sim_C.p_timeout*100:.2f}%")
    print(f"      E[days to target | passed]: {sim_C.e_days_to_target:.1f}")
    print(f"      E[funded PnL 180d | passed]: ${sim_C.e_funded_pnl_180d:.2f}")
    print()

    # === Stress: cost x 1.5 and x 3 ===
    print("=" * 100)
    print("STRESS — cost × {1.5, 3} via raw cost adjustment in trade log")
    print("=" * 100)
    # Apply extra cost: each trade incurs (cm-1)×$19 NQ extra ; in MNQ at 2 contracts:
    # Extra cost MNQ = (cm-1) × $2.15 × 2 = (cm-1) × $4.30 per trade.
    for cm in [1.5, 3.0]:
        extra_nq = (cm - 1.0) * NQ_COST_USD
        # Adjust daily PnL: count trades per day, subtract extra
        # easier: per trade subtract extra mnq cost
        extra_mnq_per_trade = extra_nq / NQ_POINT_USD * MNQ_POINT_USD * N_MNQ
        # so per trade subtract extra_mnq_per_trade.  Sum per day:
        n_per_day = pd.to_datetime(tl["entry_ts"]).dt.normalize().dt.tz_localize(None).value_counts()
        n_per_day = n_per_day.reindex(daily_full.index, fill_value=0)
        daily_stress = daily_full - n_per_day * extra_mnq_per_trade
        gen_stress = block_bootstrap_generator(
            daily_stress.values, CFG.max_eval_days + CFG.funded_days,
            block_size=20, seed=42)
        sim_s = simulate_n_runs(10000, gen_stress, config=CFG, payout_regime="no_payout")
        print(f"  cost × {cm}: extra ${extra_nq:.2f}/trade NQ = ${extra_mnq_per_trade:.4f}/trade MNQ. "
               f"p(pass)={sim_s.p_eval_pass*100:.2f}%, p(bust)={sim_s.p_bust*100:.2f}%, "
               f"E[funded]={sim_s.e_funded_pnl_180d:.2f}")
    print()

    # === DSR ===
    print("=" * 100)
    print("DSR — Bailey-Lopez de Prado deflated Sharpe")
    print("=" * 100)
    print(f"  iter_10 family mining depth (honest):")
    print(f"    - iter_1 family (3 variants 1a-1c)        ~3 trials")
    print(f"    - iter_2 family (a, b, c, d variants)     ~4 trials")
    print(f"    - iter_3-5 (gap, ETH, dollar stops, ...)  ~6 trials")
    print(f"    - iter_7-9 (VWAP, vol_ratio, 8a/b/c)      ~8 trials")
    print(f"    - iter_10 + variants 11a-11e              ~5 trials")
    print(f"    = total ≥ 26 honest trials")
    print()

    # Compute SR per period (per trade) for both samples
    # For DSR on daily, use daily Sharpe; for per-trade use trade Sharpe
    for label, tl_subset, period_label in [
        ("Full sample 2010-2026", tl, "per-trade"),
        ("2022-2026 only", tl[tl["entry_ts"] >= pd.Timestamp("2022-01-01", tz="US/Eastern")], "per-trade"),
    ]:
        pnls = tl_subset["pnl_usd"].values
        n = len(pnls)
        if n < 30:
            continue
        m = float(np.mean(pnls))
        s = float(np.std(pnls, ddof=1))
        sr = m / s if s > 0 else 0
        sk = float(scstats.skew(pnls))
        ku = float(scstats.kurtosis(pnls, fisher=False))  # non-excess
        print(f"  [{label}] {period_label}: n={n}, mean=${m:.2f}, std=${s:.2f}, "
               f"SR={sr:.4f}, skew={sk:.2f}, kurt={ku:.2f}")
        for nt in [10, 26, 50]:
            d = dsr(sr, n, nt, skew_r=sk, kurt_r=ku)
            print(f"    n_trials={nt:>2}: SR_norm={d['sr_normalized']:>6.3f}, "
                   f"emax={d['emax']:>5.3f}, z={d['z']:>+6.3f}, DSR_p={d['dsr_p']:>6.4f}")
        print()
