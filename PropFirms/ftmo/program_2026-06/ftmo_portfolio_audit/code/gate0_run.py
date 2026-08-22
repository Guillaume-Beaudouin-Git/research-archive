"""
gate0_run.py — Gate 0: MC reliability, CIs on every p(pass), monotonicity resolution,
and the headline verdict (is p(pass<=3mo) distinguishable from 0.50?).
"""
from __future__ import annotations
import json
import numpy as np, pandas as pd
from audit_common import metrics, ROOT
import firstpassage as fp

R = ROOT / "research/ftmo_portfolio_audit/results"
HZ = [63, 126, 189, 252, None]   # 3,6,9,12 mo, terminal


def load_combined(path):
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df.fillna(0.0).mean(axis=1)        # equal-weight, missing-day=flat


def rescale_to_sharpe(r, ann_sharpe):
    sd = r.std(ddof=1)
    return r - r.mean() + (ann_sharpe / np.sqrt(252)) * sd


def selfcheck():
    """Validate _phase vs logistic closed form on a Gaussian iid series (no author code)."""
    sd_daily = 0.013
    print("[selfcheck] Gaussian single-phase p(pass) vs logistic 1/(1+e^-2*Sd*n):")
    rng = np.random.default_rng(0)
    for Sann in [0.0, 0.8, 1.5]:
        Sd = Sann / np.sqrt(252)
        mu = Sd * sd_daily
        series = rng.normal(mu, sd_daily, 40000)
        # single phase, target +10% vs -10%, no min-days, long cap
        passed, _ = fp._phase(fp._draw(series, 60000, 1500, np.random.default_rng(1)), fp.P1, min_days=1)
        n = fp.P1 / sd_daily
        cf = 1.0 / (1.0 + np.exp(-2 * Sd * n))
        print(f"   Sann={Sann}: MC={passed.mean():.3f}  closed_form={cf:.3f}  (n={n:.1f})")


def run_series(label, r, lev):
    m = metrics(r)
    print(f"\n===== {label} | L={lev} | base daily_sharpe={m['daily_sharpe']:.3f} "
          f"ann={m['ann_sharpe']:.2f} kurt={m['excess_kurtosis']:.1f} sigma_d={m['sigma_daily']*100:.2f}% =====")
    out = {"base_metrics": {k: m[k] for k in ['daily_sharpe', 'ann_sharpe', 'excess_kurtosis', 'sigma_daily', 'n_days']},
           "lev": lev}

    # (B) author per-phase-product replication + honest multi-seed SD
    print(" author per-phase-product method (p1(<=H)*p2(<=H)), independent seeds:")
    print(f"   {'H(mo)':>6s} {'p_comb':>7s} {'delta_se':>9s} {'emp_SD':>7s} {'90% CI (multi-seed)':>22s}")
    auth = {}
    for H, mo in [(63, 3), (126, 6), (189, 9)]:
        ms = fp.author_multiseed(r, lev, H, n_paths=20000, n_seeds=20)
        one = fp.author_perphase_product(r, lev, H, n_paths=20000, seed=42)
        auth[mo] = {"point_seed42": one["p_combined"], "delta_se": one["delta_se"], **ms}
        print(f"   {mo:>6d} {one['p_combined']:>7.3f} {one['delta_se']:>9.4f} {ms['empirical_sd']:>7.4f} "
              f"  [{ms['ci90'][0]:.3f},{ms['ci90'][1]:.3f}]")
    out["author_method"] = auth

    # (A) corrected monotone CDF (sequential joint-budget) with CI
    print(" CORRECTED monotone CDF (sequential 2-phase, total-time budget):")
    ci = fp.cdf_sequential_ci(r, lev, HZ, n_paths=20000, n_seeds=10)
    print(f"   {'H':>9s} {'mean':>6s} {'SD':>6s} {'90% CI':>16s} {'delta_se':>9s}")
    for k in [63, 126, 189, 252, "terminal"]:
        c = ci[k]
        print(f"   {str(k):>9s} {c['mean']:>6.3f} {c['sd']:>6.3f}  [{c['ci90'][0]:.3f},{c['ci90'][1]:.3f}] {c['delta_se']:>9.4f}")
    out["corrected_cdf"] = {str(k): ci[k] for k in ci}

    # outer block-resample CI (short-sample estimation uncertainty) at 3mo
    outer = fp.outer_resample_ci(r, lev, 63, n_outer=40, n_paths=8000)
    out["outer_resample_3mo"] = outer
    print(f"   outer data-resample 3mo: mean={outer['mean']:.3f} sd={outer['sd']:.3f} "
          f"90%CI=[{outer['ci90'][0]:.3f},{outer['ci90'][1]:.3f}]")
    return out


def main():
    selfcheck()
    results = {}
    steel = load_combined(R / "sleeves_steel_combined.csv")
    full = steel.loc["2022-01-01":"2026-06-05"]
    oos = steel.loc["2025-01-01":"2026-06-05"]

    for lev in [2.5, 3.0]:
        results[f"steelman_full_L{lev}"] = run_series(f"STEEL-MAN combined FULL 2022-26", full, lev)
        results[f"steelman_oos_L{lev}"] = run_series(f"STEEL-MAN combined OOS 2025-26", oos, lev)

    # headline audit: rescale to the report's CLAIMED combined Sharpe 1.39 and test the 0.55 headline
    rep_full = rescale_to_sharpe(full, 1.39)
    rep_oos = rescale_to_sharpe(oos, 1.39)
    for lev in [2.5, 3.0]:
        results[f"reportSharpe_full_L{lev}"] = run_series("REPORT-Sharpe(1.39) FULL", rep_full, lev)
        results[f"reportSharpe_oos_L{lev}"] = run_series("REPORT-Sharpe(1.39) OOS", rep_oos, lev)

    (R / "gate0_results.json").write_text(json.dumps(results, indent=2, default=str))
    print("\nwrote gate0_results.json")


if __name__ == "__main__":
    main()
