"""Question B — puissance et deflation.

1. N necessaire pour t=2.0 sur le gross (0 cout, mean 0.0492, sigma 1.2008 -- valeurs
   ledger complet, reference RESULTS.md/audit_ledger) et sur le NET mesure (0.962 bps).
2. Puissance REELLE sur le seul sous-echantillon 2022-2026 (n ~1115), a la fois pour
   ALL et pour SHORT seul (l'objet de la question A).
3. MDE (effet minimum detectable) a 80% de puissance, n=4013 (plein echantillon) et
   n=1115 (2022-2026).
4. DSR (Bailey-Lopez de Prado, via dsr.py du repo, deja corrige du bug rf/std_sr_trials
   2026-08) a DEUX echelles : (a) n_trials = cumul registre (~1994) (b) n_trials =
   modifications propres a l'ORB (37, grille orb_variants_2026-08, Globex exclu comme
   artefact mecanique documente).
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, "<HOME>/Desktop/Algo_claude/.worktrees/desk-orb")
from dsr import deflated_sharpe_ratio, estimate_std_sr_trials, sampling_noise_floor_sr

from common import load_ledger, net_R, cost_R, hac_t, SPREAD_NATIVE_BPS

OUT = __file__.replace("code/b_power_dsr.py", "out")


def n_required_for_t(t_target: float, mean: float, sigma: float) -> float:
    return (t_target * sigma / mean) ** 2


def power_at_n(n: int, mean: float, sigma: float, alpha: float = 0.05) -> float:
    """Power of a one-sample two-sided t-test at given n, true mean/sigma (normal approx)."""
    se = sigma / np.sqrt(n)
    ncp = mean / se
    tcrit = stats.norm.ppf(1 - alpha / 2)
    # two-sided power via normal approx (n large enough here that t~normal)
    power = 1 - stats.norm.cdf(tcrit - ncp) + stats.norm.cdf(-tcrit - ncp)
    return power


def mde_at_n(n: int, sigma: float, power: float = 0.80, alpha: float = 0.05) -> float:
    se = sigma / np.sqrt(n)
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    return (z_alpha + z_power) * se


def main():
    df = load_ledger()
    r_gross = df["r_gross"]
    r_net = net_R(df, SPREAD_NATIVE_BPS)

    print("=== B1: N necessaire pour t=2.0 ===")
    mean_g, sigma_g = r_gross.mean(), r_gross.std(ddof=1)
    n_g = n_required_for_t(2.0, mean_g, sigma_g)
    print(f"GROSS (0 cout): mean={mean_g:.4f} sigma={sigma_g:.4f} -> N pour t=2.0 (naif) = {n_g:.0f}")

    mean_n, sigma_n = r_net.mean(), r_net.std(ddof=1)
    n_n = n_required_for_t(2.0, mean_n, sigma_n)
    print(f"NET (0.962 bps mesure): mean={mean_n:.4f} sigma={sigma_n:.4f} -> N pour t=2.0 (naif) = {n_n:.0f}")
    print(f"N disponible plein echantillon = {len(r_net)} ; N disponible 2022-2026 (tranche) ~1115")

    # ---------------------------------------------------------------
    # B2: puissance reelle sur 2022-2026, ALL et SHORT
    # ---------------------------------------------------------------
    tranche = df.loc["2022-01-01":"2026-12-31"]
    r_net_tr = net_R(tranche, SPREAD_NATIVE_BPS)
    short_tr = r_net_tr[tranche["direction"] == -1]
    n_tr_all = len(r_net_tr)
    n_tr_short = len(short_tr)

    print(f"\n=== B2: 2022-2026 tranche, n_all={n_tr_all}, n_short={n_tr_short} ===")
    # Effect size hypothesis = the full-sample NET effect (prior, not the tranche's own
    # point estimate -- using the tranche's own mean as "true effect" would be circular).
    power_all_fullprior = power_at_n(n_tr_all, mean_n, sigma_n)
    print(f"power(ALL, n={n_tr_all}) using FULL-SAMPLE net effect as prior "
          f"(mean={mean_n:.4f}, sigma={sigma_n:.4f}) = {power_all_fullprior:.3f}")

    # Using the tranche's OWN observed short-leg effect as the effect size (i.e., "if this
    # is real, how likely were we to detect it with only this many trades") -- ex-post power,
    # reported as a diagnostic, not a validation.
    m_s, se_s, t_s, n_s = hac_t(short_tr)
    sigma_s = short_tr.std(ddof=1)
    power_short_selfprior = power_at_n(n_tr_short, m_s, sigma_s)
    print(f"SHORT leg 2022-2026: n={n_s} mean={m_s:.4f} t_hac6={t_s:.3f} sigma={sigma_s:.4f}")
    print(f"  ex-post power at its OWN point estimate as if true = {power_short_selfprior:.3f} "
          f"(circular, diagnostic only -- an ex-post 'power' computed off the point estimate "
          f"that produced the claim is not independent evidence)")

    # ---------------------------------------------------------------
    # B3: MDE at n=4013 (full) and n=1115 (tranche), 80% power
    # ---------------------------------------------------------------
    mde_full = mde_at_n(len(r_net), sigma_n, power=0.80)
    mde_tranche = mde_at_n(n_tr_all, sigma_n, power=0.80)
    print(f"\n=== B3: MDE a 80% puissance, alpha=0.05 two-sided ===")
    print(f"n={len(r_net)} (plein echantillon): MDE = {mde_full:.4f} R/trade")
    print(f"n={n_tr_all} (2022-2026): MDE = {mde_tranche:.4f} R/trade")
    print(f"pour reference, l'effet mesure 2022-2026 (ALL, net) est ~ {r_net_tr.mean():.4f}")

    pd.DataFrame([{
        "n_full": len(r_net), "mean_full_net": mean_n, "sigma_full_net": sigma_n,
        "n_req_t2_gross": n_g, "n_req_t2_net": n_n,
        "n_2022_2026_all": n_tr_all, "n_2022_2026_short": n_tr_short,
        "power_all_2022_2026_fullprior": power_all_fullprior,
        "short_2022_2026_mean": m_s, "short_2022_2026_t_hac6": t_s,
        "power_short_selfprior_circular": power_short_selfprior,
        "mde_80pct_full": mde_full, "mde_80pct_2022_2026": mde_tranche,
    }]).to_csv(f"{OUT}/b_power_summary.csv", index=False)

    # ---------------------------------------------------------------
    # B4: DSR at two n_trials scales
    # ---------------------------------------------------------------
    print("\n=== B4: DSR ===")
    SPAN_YEARS = (df.index.max() - df.index.min()).days / 365.25
    TRADES_PER_YEAR_FULL = len(df) / SPAN_YEARS
    print(f"span={SPAN_YEARS:.2f} yrs, trades/year full-sample = {TRADES_PER_YEAR_FULL:.1f}")

    # local ORB trial family: orb_variants_2026-08 grid, Globex excluded (documented
    # mechanical artifact, not a legitimate strategy trial).
    grid = pd.read_csv(
        "<HOME>/Desktop/Algo_claude/Multi_Asset/research/active/"
        "orb_variants_2026-08/grille_resultats.csv"
    )
    grid = grid[~grid["variant"].str.startswith("Globex")]
    grid = grid.drop_duplicates(subset=["net_sharpe", "net_n"])
    print(f"orb_variants grid, unique non-Globex trials = {len(grid)}")
    grid["trades_per_year"] = grid["net_n"] / SPAN_YEARS
    grid["sharpe_annual"] = grid["net_sharpe"] * np.sqrt(grid["trades_per_year"])
    trial_sharpes = grid["sharpe_annual"].values

    n_obs_deployed = len(r_net)  # the deployed spec's own N (r_net, full ledger)
    std_sr_local = estimate_std_sr_trials(
        trial_sharpes, periods_per_year=int(round(TRADES_PER_YEAR_FULL)), n_obs=n_obs_deployed
    )
    print(f"std_sr_trials (orb-local family, {len(trial_sharpes)} trials) = {std_sr_local:.4f} "
          f"(annualised Sharpe units; floor = "
          f"{sampling_noise_floor_sr(n_obs_deployed, int(round(TRADES_PER_YEAR_FULL))):.4f})")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dsr_local = deflated_sharpe_ratio(
            r_net.values, n_trials=len(trial_sharpes),
            periods_per_year=int(round(TRADES_PER_YEAR_FULL)),
            rf=0.0, std_sr_trials=std_sr_local,
        )
    print(f"DSR (n_trials={len(trial_sharpes)}, ORB-local): sharpe={dsr_local['sharpe']:.3f} "
          f"benchmark={dsr_local['sr_benchmark']:.3f} DSR={dsr_local['dsr']:.4f} "
          f"passed(>=0.95)={dsr_local['passed']}")

    N_CUMUL = 1994 + 5  # registre (regime_diagnostic_2026-09) + Delta ce sprint (A2,A3,A1,A1b,D-beta-retest)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dsr_cumul = deflated_sharpe_ratio(
            r_net.values, n_trials=N_CUMUL,
            periods_per_year=int(round(TRADES_PER_YEAR_FULL)),
            rf=0.0, std_sr_trials=std_sr_local,  # same dispersion estimate; n_trials scaled up
        )
    print(f"DSR (n_trials={N_CUMUL}, cumul registre): sharpe={dsr_cumul['sharpe']:.3f} "
          f"benchmark={dsr_cumul['sr_benchmark']:.3f} DSR={dsr_cumul['dsr']:.4f} "
          f"passed(>=0.95)={dsr_cumul['passed']}")

    pd.DataFrame([
        {"scale": "orb_local_37trials", "n_trials": len(trial_sharpes),
         "std_sr_trials": std_sr_local, **{k: v for k, v in dsr_local.items()}},
        {"scale": "registry_cumulative", "n_trials": N_CUMUL,
         "std_sr_trials": std_sr_local, **{k: v for k, v in dsr_cumul.items()}},
    ]).to_csv(f"{OUT}/b4_dsr.csv", index=False)


if __name__ == "__main__":
    main()
