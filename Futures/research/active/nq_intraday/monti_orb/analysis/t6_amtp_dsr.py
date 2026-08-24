"""
T6 — AMTP (Bonferroni-Holm) + DSR (Bailey-LdP 2014).

Prior test count: N_PRIOR = 274 (from CLAUDE.md global n_tests).
This strategy is test #275.

DSR formula (Bailey & Lopez de Prado 2014):
  E[max SR* | N] = (1 - γ_e) × Φ^{-1}(1 - 1/N) + γ_e × Φ^{-1}(1 - 1/(N×e))
  where γ_e = 0.5772… (Euler-Mascheroni constant)

  Variance correction (Mertens 2002):
  V[SR | T, γ3, γ4] = (1 - γ3×SR_daily + (γ4-1)/4 × SR_daily²) / (T-1)
  where γ3 = skewness, γ4 = excess kurtosis of daily returns

  t_obs    = SR_annual / sqrt(252) × sqrt(T)
  DSR      = Φ((t_obs - E[max SR*]) / sqrt(V))

PROPFIRM_PASS gate: DSR > 0.95
Note: L27 warns that DSR ≈ 0 for any SR < E[max SR* | N] after large N.
We report DSR accurately regardless.

AMTP: Bonferroni-Holm correction for p-values of the full test battery.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parents[6]))

from data.cache import load_nq_1min, get_cached_or_fetch_fred
from Futures.research.active.nq_intraday.monti_orb.signal import monti_orb_signal
from Futures.research.active.nq_intraday.monti_orb.backtest import (
    daily_returns, sharpe_hac,
)

N_PRIOR     = 274   # global n_tests before this strategy
N_TOTAL     = 275   # this strategy is test #275
EULER_GAMMA = 0.5772156649015328


def deflated_sharpe_ratio(
    sr_annual: float,
    n_obs: int,
    n_trials: int,
    skewness: float = 0.0,
    excess_kurt: float = 0.0,
) -> tuple[float, float, float]:
    """
    Bailey-LdP (2014) Deflated Sharpe Ratio.

    Parameters
    ----------
    sr_annual  : annualized observed Sharpe ratio
    n_obs      : number of daily observations (T)
    n_trials   : total strategies tested (N)
    skewness   : skewness of daily returns
    excess_kurt: excess kurtosis of daily returns

    Returns
    -------
    (dsr, e_max_sr_annual, t_obs)
    """
    if n_trials < 1 or n_obs < 10:
        return (np.nan, np.nan, np.nan)

    # Expected max standardized SR (Bailey-LdP eq. 8)
    e_max = (
        (1 - EULER_GAMMA) * stats.norm.ppf(1 - 1.0 / n_trials) +
        EULER_GAMMA * stats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    )

    # t-statistic of observed SR
    sr_daily = sr_annual / np.sqrt(252)
    t_obs    = sr_annual * np.sqrt(n_obs / 252)

    # Variance of SR estimate (Mertens 2002)
    var_sr = (
        1.0 - skewness * sr_daily + (excess_kurt / 4.0) * sr_daily ** 2
    ) / max(n_obs - 1, 1)

    dsr = float(stats.norm.cdf(
        (t_obs - e_max) / np.sqrt(max(var_sr * (n_obs - 1), 1e-12))
    ))

    # E[max SR] converted to annualized Sharpe scale: E[max t] / sqrt(n/252) × sqrt(252/n) × sqrt(252)
    # e_max is a t-like statistic: t = SR_annual × sqrt(T/252)
    # So E[max SR_annual] = e_max / sqrt(n_obs / 252) = e_max × sqrt(252 / n_obs)
    e_max_annual_disp = e_max * np.sqrt(252.0 / n_obs)

    return (dsr, float(e_max_annual_disp), float(t_obs))


def _t_stat_hac(daily_net: pd.Series, lag: int = 6) -> float:
    """HAC t-stat for mean daily P&L != 0."""
    import statsmodels.api as sm
    r = daily_net.dropna()
    n = len(r)
    if n < 10:
        return np.nan
    reg = sm.OLS(r.values, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(reg.tvalues[0])


def run(trades=None) -> dict:
    print("=" * 60)
    print("T6 — AMTP + DSR (Bailey-LdP 2014)")
    print("=" * 60)

    df = load_nq_1min()
    if trades is None:
        trades = monti_orb_signal(df)

    rf = get_cached_or_fetch_fred("DTB3", "2022-12-26", "2025-12-11")
    tl, dn = daily_returns(trades, sizing="fixed", n_contracts_fixed=1, rf_series=rf["dtb3"])

    if tl.empty:
        print("[T6] No trades")
        return {"test": "T6", "dsr": None, "amtp_pass": False}

    sr   = sharpe_hac(dn)
    t_hac = _t_stat_hac(dn)
    n_obs = int(dn.dropna().shape[0])

    # Distribution moments
    r = dn.dropna()
    skew   = float(r.skew())
    exkurt = float(r.kurtosis())  # pandas uses excess kurtosis

    # AMTP: HAC t-stat p-value, Bonferroni-Holm adjusted
    p_raw = float(2.0 * (1.0 - stats.norm.cdf(abs(t_hac))))
    p_holm = min(1.0, p_raw * N_TOTAL)  # Bonferroni-Holm step 1 (most significant)
    amtp_pass = p_holm < 0.05

    # DSR
    dsr, e_max_sr, t_obs = deflated_sharpe_ratio(
        sr_annual=sr if sr is not None else 0.0,
        n_obs=n_obs,
        n_trials=N_TOTAL,
        skewness=skew,
        excess_kurt=exkurt,
    )
    dsr_pass = dsr > 0.95

    print(f"\nN observations (trading days): {n_obs}")
    print(f"Annualized Sharpe (HAC):        {sr:.4f}")
    print(f"HAC t-statistic:                {t_hac:.4f}")
    print(f"Daily returns: skew={skew:.3f}  ex.kurt={exkurt:.3f}")

    print(f"\nAMTP (Bonferroni-Holm, N={N_TOTAL}):")
    print(f"  p_raw:        {p_raw:.6f}")
    print(f"  p_adjusted:   {p_holm:.6f}  (gate: < 0.05 → RESEARCH_PASS)")
    print(f"  AMTP gate:    {'PASS ✓' if amtp_pass else 'FAIL ✗'}")

    print(f"\nDSR (Bailey-LdP 2014, N_trials={N_TOTAL}):")
    print(f"  t_obs:              {t_obs:.4f}")
    print(f"  E[max SR* | N]:     {e_max_sr:.4f}  (annualized)")
    print(f"  DSR:                {dsr:.4f}  (gate: > 0.95 → PROPFIRM_PASS)")
    print(f"  DSR gate:           {'PASS ✓' if dsr_pass else 'FAIL ✗'}")

    # L27 warning
    # Required t for DSR > 0.95:
    std_correction = np.sqrt(
        (1 - skew * (sr/np.sqrt(252)) + (exkurt/4) * (sr/np.sqrt(252))**2)
        / max(n_obs - 1, 1) * (n_obs - 1)
    )
    e_max_t = (
        (1 - EULER_GAMMA) * stats.norm.ppf(1 - 1.0 / N_TOTAL) +
        EULER_GAMMA * stats.norm.ppf(1 - 1.0 / (N_TOTAL * np.e))
    )
    required_t = e_max_t + stats.norm.ppf(0.95) * max(std_correction, 1.0)
    required_sr_annual = required_t * np.sqrt(252.0 / n_obs)
    print(f"\n  [L27] SR_annual needed for DSR>0.95: {required_sr_annual:.2f}")
    if sr < required_sr_annual:
        print(f"  [L27] DSR structurally < 0.95 with SR={sr:.2f} and N={N_TOTAL}")

    result = {
        "test":            "T6",
        "n_obs":           n_obs,
        "n_trials":        N_TOTAL,
        "sr_annual":       round(float(sr), 4) if sr else None,
        "t_hac":           round(float(t_hac), 4),
        "skewness":        round(float(skew), 4),
        "excess_kurt":     round(float(exkurt), 4),
        "p_raw":           round(float(p_raw), 6),
        "p_holm":          round(float(p_holm), 6),
        "amtp_pass":       bool(amtp_pass),
        "dsr":             round(float(dsr), 4) if not np.isnan(dsr) else None,
        "e_max_sr":        round(float(e_max_sr), 4) if not np.isnan(e_max_sr) else None,
        "dsr_pass":        bool(dsr_pass),
        "sr_needed_dsr95": round(float(required_sr_annual), 3),
    }
    return result


if __name__ == "__main__":
    run()
