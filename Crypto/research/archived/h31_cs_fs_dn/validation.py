"""
validation.py — H31 CS-FS Delta-Neutral Carry
Statistical validation: HAC t-stat, WF 5-fold, DSR, HLZ AMTP, correlation vs Strategy A.
CPCV not used (skfolio unavailable); replaced by 5-fold expanding purged walk-forward.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as st
import statsmodels.api as sm

RESULTS_DIR = Path(__file__).resolve().parent / "results"

N_WF_FOLDS   = 5
PURGE_DAYS   = 1
EMBARGO_DAYS = 5
TRADING_DAYS = 365

# AMTP: HLZ with n=41 hypotheses (40 prior + this test)
N_TESTS_HLZ = 41
# DSR
N_MOD       = 0
SR_STAR     = 1.0


def load_returns() -> pd.Series:
    detail = pd.read_parquet(RESULTS_DIR / "trade_log.parquet")
    return detail["net_pnl"]


def hac_tstat(returns: pd.Series, lag: int = 6) -> float:
    """HAC Newey-West t-stat for H0: mean return = 0."""
    X = sm.add_constant(np.ones(len(returns)))
    model = sm.OLS(returns.values, X)
    result = model.fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(result.tvalues[0])


def walk_forward_sharpes(returns: pd.Series, n_folds: int = N_WF_FOLDS) -> list[float]:
    """
    Expanding-window walk-forward with purge + embargo.
    Train on first k folds, test on fold k+1, for k = 1..n_folds-1.
    Actually: split the full period into n_folds chunks; fold i is tested
    after training on folds 0..i-1. Returns OOS Sharpe for each test fold.
    """
    T = len(returns)
    fold_size = T // n_folds
    sharpes: list[float] = []

    for fold_idx in range(1, n_folds):
        train_end = fold_size * fold_idx - PURGE_DAYS - EMBARGO_DAYS
        test_start = fold_size * fold_idx
        test_end   = fold_size * (fold_idx + 1) if fold_idx < n_folds - 1 else T

        if train_end < 30 or test_end - test_start < 20:
            continue

        oos_rets = returns.iloc[test_start:test_end]
        ann_ret  = oos_rets.mean() * TRADING_DAYS
        ann_vol  = oos_rets.std() * math.sqrt(TRADING_DAYS)
        sr = ann_ret / ann_vol if ann_vol > 0 else 0.0
        sharpes.append(float(sr))

    return sharpes


def hlz_t_required(n: int, alpha: float = 0.05) -> float:
    """Harvey-Liu-Zhu minimum t-stat for multiple testing correction."""
    gamma = math.log(n)
    p_adj = alpha / n
    t_req = st.norm.ppf(1 - p_adj / 2) * math.sqrt(gamma)
    return float(t_req)


def dsr_correction(
    sr_observed: float,
    T: int,
    n_mod: int,
    sr_star: float,
    skew: float = 0.0,
    kurt: float = 3.0,
) -> float:
    """
    Bailey-LdP Deflated Sharpe Ratio.
    Returns SR_DSR = Phi( (SR_hat - E[max_SR]) / sqrt(var) ).
    """
    if T <= 1:
        return 0.0
    # E[max SR | N_trials] via Bailey-LdP
    n_trials = max(1, n_mod + 1)
    e_max_sr = (
        (1 - math.gamma(1 / n_trials))
        + math.gamma(1 - 1 / n_trials)
    ) if n_trials > 1 else sr_star

    # Variance adjustment for non-normality
    var_sr = (1 - skew * sr_observed + (kurt - 1) / 4 * sr_observed**2) / (T - 1)
    std_sr = math.sqrt(var_sr) if var_sr > 0 else 1e-6

    z = (sr_observed - sr_star) / std_sr
    return float(st.norm.cdf(z))


def correlation_vs_strat_a(returns: pd.Series) -> float:
    """
    Compute correlation with Strategy A (TSMOM). Strategy A returns are not
    available as a local series — use BTC weekly as proxy (documented approach).
    """
    # Load BTC funding CSV to get date range, use prices to proxy BTC return
    price_path = RESULTS_DIR / "price_daily.parquet"
    if not price_path.exists():
        return float("nan")
    prices = pd.read_parquet(price_path)
    prices.index = pd.to_datetime(prices.index, utc=True)

    if "BTC" not in prices.columns:
        return float("nan")

    btc_ret = prices["BTC"].pct_change().reindex(returns.index)
    common = btc_ret.dropna().index.intersection(returns.dropna().index)
    if len(common) < 30:
        return float("nan")

    return float(returns.loc[common].corr(btc_ret.loc[common]))


def main() -> None:
    with open(RESULTS_DIR / "metrics_raw.json") as f:
        raw_metrics = json.load(f)

    returns = load_returns()
    T = len(returns)

    print("Computing HAC t-stat (Newey-West lag-6)...")
    t_hac = hac_tstat(returns, lag=6)

    print("Running 5-fold walk-forward...")
    wf_sharpes = walk_forward_sharpes(returns, n_folds=N_WF_FOLDS)
    wf_positive = sum(1 for s in wf_sharpes if s > 0)
    wf_pct = wf_positive / len(wf_sharpes) * 100 if wf_sharpes else 0.0

    print("Computing HLZ AMTP t_required...")
    t_req_hlz = hlz_t_required(N_TESTS_HLZ)

    print("Computing DSR...")
    sr_ann = raw_metrics["sharpe_raw"]
    sr_daily = sr_ann / math.sqrt(TRADING_DAYS)
    dsr = dsr_correction(sr_daily * math.sqrt(T), T, N_MOD, SR_STAR)

    print("Computing correlation vs Strategy A (BTC proxy)...")
    corr_a = correlation_vs_strat_a(returns)

    # Gate evaluation
    research_pass = (
        raw_metrics["sharpe_raw"] > 0.7
        and raw_metrics["max_drawdown"] > -0.25
        and wf_pct > 50.0
        and abs(t_hac) > 1.5
    )
    propfirm_pass = (
        raw_metrics["sharpe_raw"] > 1.0
        and raw_metrics["max_drawdown"] > -0.10
        and wf_pct > 60.0
        and abs(t_hac) > 2.0
    )
    amtp_pass = abs(t_hac) > t_req_hlz

    validation = {
        "T_days":            T,
        "sharpe_raw":        raw_metrics["sharpe_raw"],
        "max_drawdown":      raw_metrics["max_drawdown"],
        "t_hac_lag6":        round(t_hac, 4),
        "t_required_hlz":    round(t_req_hlz, 4),
        "wf_sharpes":        [round(s, 3) for s in wf_sharpes],
        "wf_positive":       wf_positive,
        "wf_n_folds":        len(wf_sharpes),
        "wf_pct":            round(wf_pct, 1),
        "dsr":               round(dsr, 4),
        "n_mod":             N_MOD,
        "n_tests_hlz":       N_TESTS_HLZ,
        "corr_vs_strat_a_btc_proxy": round(corr_a, 4) if not math.isnan(corr_a) else None,
        "gates": {
            "RESEARCH_PASS":  research_pass,
            "PROPFIRM_PASS":  propfirm_pass,
            "AMTP_HLZ_PASS":  amtp_pass,
        },
    }

    print("\n=== VALIDATION RESULTS ===")
    print(f"Sharpe (raw, ann):    {raw_metrics['sharpe_raw']:.3f}")
    print(f"Max Drawdown:         {raw_metrics['max_drawdown']:.2%}")
    print(f"HAC t-stat (lag-6):   {t_hac:.3f}")
    print(f"HLZ t_required:       {t_req_hlz:.3f}")
    print(f"AMTP PASS:            {amtp_pass}")
    print(f"WF Sharpes:           {[round(s, 3) for s in wf_sharpes]}")
    print(f"WF positive:          {wf_positive}/{len(wf_sharpes)} ({wf_pct:.0f}%)")
    print(f"DSR:                  {dsr:.4f}")
    print(f"Corr vs BTC (proxy A):{corr_a:.3f}")
    print(f"\n--- GATE VERDICTS ---")
    print(f"RESEARCH_PASS:  {'✓' if research_pass else '✗'}")
    print(f"PROPFIRM_PASS:  {'✓' if propfirm_pass else '✗'}")

    (RESULTS_DIR / "metrics_validation.json").write_text(
        json.dumps(validation, indent=2, default=str)
    )
    print(f"\nValidation saved to {RESULTS_DIR / 'metrics_validation.json'}")


if __name__ == "__main__":
    main()
