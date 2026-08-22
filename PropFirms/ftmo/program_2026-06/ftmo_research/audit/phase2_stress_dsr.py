"""
phase2_stress_dsr.py — Stress (3x cost) + DSR + annual breakdown for H1.

Honesty checks for the only candidate that survived regime + bootstrap CI:

  H1: dir==1 AND gap_pct>0 AND dist_to_pdh_R>0
      (long ORB break with positive gap and breaking above prior-day high).

Tests:
  1. STRESS — rebuild dataset with cost_mult=3 (= ~3 points RT NQ) and
     evaluate H1 + H4 on r_exec_nextopen.
  2. SLIPPAGE STRESS — add slip_R = 0.05 (5% of R adverse on both sides)
     on top of baseline cost.
  3. ANNUAL BREAKDOWN — H1 + baseline mean R, std, hit rate, Sharpe per
     calendar year.
  4. DSR (Bailey-LdP) — deflated Sharpe with honest n_trials reflecting the
     mining depth. n_trials ≈ 23 features × 3 subsets × 2 sides (univariate)
     + 4 hypotheses with ablations ≈ 150.
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from trade_features_nq import extract_trades_nq

TARGET = "r_exec_nextopen"


def filt_H1(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["breakout_dir"] == 1) &
              (df["gap_pct"] > 0) &
              (df["dist_to_pdh_R"] > 0)]


def filt_H4(df: pd.DataFrame) -> pd.DataFrame:
    long_m = (df["breakout_dir"] == 1) & (df["gap_concord"] == 1) & (df["dist_to_pdh_R"] > 0)
    short_m = (df["breakout_dir"] == -1) & (df["gap_concord"] == 1) & (df["dist_to_pdl_R"] > 0)
    return df[long_m | short_m]


def summary(name: str, sub: pd.DataFrame, target: str = TARGET) -> dict:
    from scipy import stats as scstats
    y = sub[target].dropna().values
    n = len(y)
    if n == 0:
        return {"set": name, "n": 0}
    mean_R = float(np.mean(y))
    std_R = float(np.std(y, ddof=1))
    sharpe = mean_R / std_R * np.sqrt(252) if std_R > 0 else np.nan
    skew = float(scstats.skew(y))
    hit_rate = float((y > 0).mean()) * 100
    return {"set": name, "n": n,
             "mean_R": round(mean_R, 4),
             "std_R": round(std_R, 4),
             "sharpe_ann": round(sharpe, 3),
             "skew": round(skew, 3),
             "hit_rate_pct": round(hit_rate, 2)}


# ---------------------------------------------------------------------------
# 1. STRESS — cost_mult sweep
# ---------------------------------------------------------------------------

def run_stress(cost_mults: list[float], slip_Rs: list[float]) -> pd.DataFrame:
    rows = []
    for cm in cost_mults:
        for sr in slip_Rs:
            print(f"  Building stress: cost_mult={cm}, slip_R={sr}...")
            df = extract_trades_nq(cost_mult=cm, slip_R=sr).dropna(subset=[TARGET])
            base = summary(f"BASE cost={cm} slip={sr}", df)
            h1 = summary(f"H1 cost={cm} slip={sr}", filt_H1(df))
            h4 = summary(f"H4 cost={cm} slip={sr}", filt_H4(df))
            for r in [base, h1, h4]:
                r["cost_mult"] = cm
                r["slip_R"] = sr
            rows.extend([base, h1, h4])
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. ANNUAL BREAKDOWN
# ---------------------------------------------------------------------------

def annual_breakdown(df: pd.DataFrame, target: str = TARGET) -> pd.DataFrame:
    """Per-year diagnostics for BASE and H1."""
    rows = []
    h1 = filt_H1(df)
    years = sorted(set(df.index.year))
    for y in years:
        b = df.loc[str(y)]
        f = h1.loc[str(y)] if str(y) in h1.index.year.astype(str).values else h1[h1.index.year == y]
        b_y = b[target].dropna().values
        f_y = f[target].dropna().values
        rows.append({
            "year": y,
            "n_base": len(b_y),
            "n_H1": len(f_y),
            "mean_R_base": round(float(np.mean(b_y)), 4) if len(b_y) else np.nan,
            "mean_R_H1": round(float(np.mean(f_y)), 4) if len(f_y) else np.nan,
            "sharpe_base": round(float(np.mean(b_y) / np.std(b_y, ddof=1) * np.sqrt(252)), 3) if len(b_y) > 5 and np.std(b_y, ddof=1) > 0 else np.nan,
            "sharpe_H1": round(float(np.mean(f_y) / np.std(f_y, ddof=1) * np.sqrt(252)), 3) if len(f_y) > 5 and np.std(f_y, ddof=1) > 0 else np.nan,
            "hit_base_pct": round(float((b_y > 0).mean()) * 100, 1) if len(b_y) else np.nan,
            "hit_H1_pct": round(float((f_y > 0).mean()) * 100, 1) if len(f_y) else np.nan,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. DSR — Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014)
# ---------------------------------------------------------------------------

def dsr_bailey_lopezdeprado(sr_obs: float, n_obs: int, n_trials: int,
                              skew_R: float = 0.0, kurt_R: float = 3.0) -> dict:
    """Deflated Sharpe Ratio (Bailey-Lopez de Prado 2014).

    Formula (eq. 5-6):
       SR_normalized = SR_obs * sqrt(T - 1) / sqrt(1 - skew*SR_obs + (kurt-1)/4 * SR_obs^2)
       E[max] of N i.i.d. N(0,1)  ≈  (1-γ)Φ⁻¹(1-1/N) + γΦ⁻¹(1-1/(N·e))
       DSR = Φ(SR_normalized - E[max])

    SR_obs and skew/kurt are in PER-PERIOD (per-trade) units.

    DSR ≈ probability the observed SR is non-spurious given N trials.
    """
    from scipy import stats as scstats
    if n_trials < 2:
        emax = 0.0
    else:
        gamma = 0.5772156649
        emax = (1 - gamma) * scstats.norm.ppf(1 - 1.0 / n_trials) + \
                gamma * scstats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    denom = np.sqrt(max(1e-12, 1 - skew_R * sr_obs + ((kurt_R - 1) / 4) * sr_obs**2))
    sr_normalized = sr_obs * np.sqrt(n_obs - 1) / denom
    z = sr_normalized - emax
    dsr_p = float(scstats.norm.cdf(z))
    return {"sr_obs_per_trade": float(sr_obs),
             "sr_normalized": round(float(sr_normalized), 3),
             "n_trials": int(n_trials),
             "emax_threshold": round(float(emax), 4),
             "z_vs_threshold": round(float(z), 3),
             "dsr_p": round(dsr_p, 4)}


def compute_dsr_for_filter(filt: pd.DataFrame, target: str = TARGET,
                            n_trials: int = 150) -> dict:
    """Compute DSR for a filter.  SR_obs and skew/kurt in PER-TRADE units."""
    from scipy import stats as scstats
    y = filt[target].dropna().values
    n = len(y)
    if n < 30:
        return {"insufficient_n": True}
    mean = float(np.mean(y))
    std = float(np.std(y, ddof=1))
    sr_pt = mean / std if std > 0 else 0
    skew = float(scstats.skew(y))
    kurt = float(scstats.kurtosis(y, fisher=False))  # not excess
    dsr = dsr_bailey_lopezdeprado(sr_pt, n, n_trials, skew_R=skew, kurt_R=kurt)
    dsr["n_obs"] = n
    dsr["mean_R"] = round(mean, 4)
    dsr["std_R"] = round(std, 4)
    dsr["skew_R"] = round(skew, 3)
    dsr["kurt_R"] = round(kurt, 3)
    dsr["sr_annual_per_trade"] = round(sr_pt * np.sqrt(252), 3)
    return dsr


if __name__ == "__main__":
    print("=" * 110)
    print("1. STRESS TEST — cost_mult ∈ {1, 1.5, 3}, slip_R ∈ {0, 0.05}")
    print("=" * 110)
    stress = run_stress([1.0, 1.5, 3.0], [0.0, 0.05])
    print(stress.to_string(index=False))
    stress.to_csv(ROOT / "phase2_stress.csv", index=False)
    print()

    print("=" * 110)
    print("2. ANNUAL BREAKDOWN — H1 vs Baseline (clean cost, no extra slip)")
    print("=" * 110)
    df_base = extract_trades_nq().dropna(subset=[TARGET])
    annual = annual_breakdown(df_base)
    print(annual.to_string(index=False))
    annual.to_csv(ROOT / "phase2_annual_breakdown_H1.csv", index=False)
    print()

    print("=" * 110)
    print("3. DSR — Bailey-Lopez de Prado deflated Sharpe")
    print("=" * 110)
    h1 = filt_H1(df_base)
    h4 = filt_H4(df_base)

    print("\n  Honest n_trials estimate:")
    print("    - 23 features × 3 subsets × 2 sides (above/below median) = 138 univariate tests")
    print("    - 4 pre-registered hypotheses × 3 (full + 2 ablations each) = 12 hypothesis tests")
    print("    Total ≈ 150.  Round to 150.")
    print()
    print("  H1: DSR with n_trials = 150")
    dsr_h1 = compute_dsr_for_filter(h1, n_trials=150)
    for k, v in dsr_h1.items():
        print(f"    {k:25s}: {v}")
    print()
    print("  H1: DSR with n_trials = 500 (conservative — count of all pairs explored)")
    dsr_h1_c = compute_dsr_for_filter(h1, n_trials=500)
    for k, v in dsr_h1_c.items():
        print(f"    {k:25s}: {v}")
    print()
    print("  H4: DSR with n_trials = 150")
    dsr_h4 = compute_dsr_for_filter(h4, n_trials=150)
    for k, v in dsr_h4.items():
        print(f"    {k:25s}: {v}")
    print()

    print("=" * 110)
    print("DSR INTERPRETATION")
    print("=" * 110)
    print("  DSR p-value > 0.95 = strong evidence the SR is non-spurious.")
    print("  DSR p-value > 0.50 = positive but inconclusive.")
    print("  DSR p-value < 0.50 = likely spurious given mining depth.")
