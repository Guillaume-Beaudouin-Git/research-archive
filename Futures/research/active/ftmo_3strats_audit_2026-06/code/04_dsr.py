"""
Deflated Sharpe Ratio (Bailey & López de Prado, 2014).

SR* = E[max_{k=1..N} SR_k]
    = (1 - γ) * Phi^{-1}(1 - 1/N) + γ * Phi^{-1}(1 - 1/(N * e))
DSR = Phi((SR_hat - SR*) / sigma_SR)
sigma_SR = sqrt((1 - skew*SR_hat + (kurt-1)/4 * SR_hat**2) / (T-1))

Computed on the per-trade R series (S1 daily R-multiples here, T_obs=number of obs).

We evaluate two key claimed SRs:
  - The report's SR = 0.73 on 2021-2026 (T_obs ≈ 1361 sessions ; skew = +2.88, kurt unknown, assume excess kurt = 15)
  - My S1 full-sample SR = 0.14 on 2010-2026 (T_obs ≈ 4089)
  - My S1 SR = 0.70 on 2021-2026 fenêtre.

n_trials: report mentions 105 candidates + "second engineered wave" (~3). Range tested: 50, 105, 120, 200.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path("<HOME>/Desktop/Algo_claude")
RES = ROOT / "Futures/research/active/ftmo_3strats_audit_2026-06/results"

EULER_GAMMA = 0.5772156649015329


def expected_max_sr(n_trials: int) -> float:
    """E[max_{k=1..N} SR_k] = (1 - γ) Φ^-1(1 - 1/N) + γ Φ^-1(1 - 1/(N e))."""
    if n_trials < 2:
        return 0.0
    a = norm.ppf(1.0 - 1.0 / n_trials)
    b = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    return (1 - EULER_GAMMA) * a + EULER_GAMMA * b


def dsr_test(sr_hat_annual: float, t_obs: int, skew: float, kurt_excess: float,
             n_trials: int, periodicity: int = 252) -> dict:
    """
    Bailey-LdP (2014) DSR.

    sigma_SR (Mertens) = sqrt((1 - skew*SR + (kurt_excess)/4 * SR^2) / (T-1))
    sr_star (Z-quantile, dimensionless) = (1-γ) Z_{1-1/N} + γ Z_{1-1/(N e)}
    DSR = Phi( SR_hat/sigma_SR - sr_star )
    """
    sr_hat_daily = sr_hat_annual / math.sqrt(periodicity)
    sr_star_z = expected_max_sr(n_trials)  # dimensionless quantile
    sigma_sr = math.sqrt(
        (1.0 - skew * sr_hat_daily + kurt_excess / 4.0 * sr_hat_daily ** 2)
        / max(t_obs - 1, 1)
    )
    sr_hat_tstat = sr_hat_daily / sigma_sr if sigma_sr > 0 else float("nan")
    z = sr_hat_tstat - sr_star_z
    dsr = norm.cdf(z)
    return {
        "sr_hat_annual": sr_hat_annual,
        "sr_hat_daily": sr_hat_daily,
        "sigma_sr_daily": sigma_sr,
        "sr_hat_tstat": sr_hat_tstat,
        "sr_star_z_quantile": sr_star_z,
        "z": z,
        "dsr": dsr,
        "passes_05": bool(dsr > 0.95),
    }


def main() -> None:
    # ---- Pull empirical skew/kurt from MY S1 daily R series ----
    s1 = pd.read_parquet(RES / "s1_trades.parquet")["pnl_R"]
    s1_clean = s1.dropna()
    full_skew = float(s1_clean.skew())
    full_kurt_excess = float(s1_clean.kurt())  # pandas returns excess kurtosis
    full_T = int(len(s1_clean))

    sub2021 = s1.loc["2021-01-01":"2026-05-31"]
    sub_skew = float(sub2021.skew())
    sub_kurt_excess = float(sub2021.kurt())
    sub_T = int(len(sub2021))

    print(f"Full window: T={full_T}, skew={full_skew:.2f}, kurt_excess={full_kurt_excess:.2f}", flush=True)
    print(f"Sub 2021-2026: T={sub_T}, skew={sub_skew:.2f}, kurt_excess={sub_kurt_excess:.2f}", flush=True)

    cases = {}

    # SR cases:
    sr_cases = [
        ("report_0.73_window_2021_2026", 0.73, sub_T, sub_skew, sub_kurt_excess),
        ("my_0.70_window_2021_2026", 0.70, sub_T, sub_skew, sub_kurt_excess),
        ("my_0.14_full_2010_2026", 0.14, full_T, full_skew, full_kurt_excess),
    ]
    n_trials_range = [50, 105, 120, 200, 500]

    for label, sr_h, T, sk, kx in sr_cases:
        cases[label] = {
            "T_obs": T,
            "skew": sk,
            "kurt_excess": kx,
            "by_n_trials": {},
        }
        for nt in n_trials_range:
            cases[label]["by_n_trials"][nt] = dsr_test(sr_h, T, sk, kx, nt)

    # ---- Pretty print ----
    for label, payload in cases.items():
        print(f"\n=== {label} (T={payload['T_obs']}, skew={payload['skew']:.2f}, kurt_ex={payload['kurt_excess']:.2f}) ===", flush=True)
        for nt, dd in payload["by_n_trials"].items():
            tag = "PASS" if dd["passes_05"] else "FAIL"
            print(
                f"  N_trials={nt:3d}: t_SR={dd['sr_hat_tstat']:.2f}  "
                f"SR*_z={dd['sr_star_z_quantile']:.2f}  "
                f"z={dd['z']:+.2f}  DSR={dd['dsr']:.3f}  [{tag} 95%]",
                flush=True,
            )

    (RES / "s1_dsr.json").write_text(json.dumps(cases, indent=2))
    print(f"\n[save] {RES / 's1_dsr.json'}", flush=True)


if __name__ == "__main__":
    main()
