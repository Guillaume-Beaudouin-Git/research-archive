"""
step2_robustness.py — Robustness tests (T3 drop-top-N, T4 DSR, T5 slippage, T6 delay).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats
from orb_core import build_3sleeve_matrix, block_capped_pnl, SLEEVE_NAMES
from ftmo_engine import simulate


def drop_top_n(M: pd.DataFrame, n_drop: int) -> pd.DataFrame:
    """Remove the n_drop trades with largest R-multiples (across all sleeves)."""
    M = M.copy()
    # Flatten all R values and find top n by absolute value of positive R
    vals = []
    for col in M.columns:
        for d, v in M[col].dropna().items():
            vals.append((d, col, v))
    vals.sort(key=lambda x: -x[2])  # largest first
    for d, col, v in vals[:n_drop]:
        M.loc[d, col] = np.nan
    return M


def daily_sharpe_ann(M: pd.DataFrame) -> float:
    pnl = block_capped_pnl(M).fillna(0.0)
    s = pnl.std(ddof=1)
    return float(pnl.mean() / s * np.sqrt(252)) if s > 0 else float("nan")


def mean_R(M: pd.DataFrame) -> float:
    vals = M.values.flatten()
    vals = vals[~np.isnan(vals)]
    return float(vals.mean()) if len(vals) else float("nan")


def step_T3_drop_top_n(M_full: pd.DataFrame, M_2026: pd.DataFrame, n_paths: int = 10000):
    print("=" * 80)
    print("T3 — Drop-top-N tail dependence")
    print("=" * 80)
    print(f"{'Drop N':>6} | {'Full 2022-25 meanR':>18} | {'Sharpe':>7} | {'Pass% iid':>10} || "
          f"{'2026 meanR':>11} | {'Sharpe':>7} | {'Pass% iid':>10}")
    print("-" * 100)
    for n in [0, 1, 3, 5, 10]:
        Mf_d = drop_top_n(M_full, n)
        M26_d = drop_top_n(M_2026, n)
        mr_f = mean_R(Mf_d)
        sh_f = daily_sharpe_ann(Mf_d)
        p_f = simulate(Mf_d, mode="iid_bootstrap", n_paths=n_paths)["pass_rate"]
        mr_26 = mean_R(M26_d)
        sh_26 = daily_sharpe_ann(M26_d)
        p_26 = simulate(M26_d, mode="iid_bootstrap", n_paths=n_paths)["pass_rate"]
        print(f"{n:6d} | {mr_f:+18.4f} | {sh_f:7.3f} | {p_f*100:8.1f}% || "
              f"{mr_26:+11.4f} | {sh_26:7.3f} | {p_26*100:8.1f}%")
    print()


def deflated_sharpe(sr_obs: float, t_obs_days: int, n_trials: int,
                    skew: float, kurt: float, sr_independent_trials_max: float | None = None) -> dict:
    """
    Bailey-Lopez de Prado (2014) DSR.
    sr_obs is the observed daily Sharpe (annualised).
    n_trials = number of strategies tried (multiple testing).
    skew, kurt = skew and excess-kurtosis of returns.
    """
    # SR0 = expected max SR of n_trials iid normal Sharpes ~ Z_(1-1/(n_trials*sqrt(2*pi)))
    # Simpler: SR0 = sqrt(Var(SR)) * E[max of N standard normals]
    from scipy.stats import norm
    # E[max of N independent standard normals] = approx Phi^{-1}(1 - 1/N) for large N
    # More precise: (1-gamma)*Phi^{-1}(1-1/N) + gamma*Phi^{-1}(1-1/(N*e))
    gamma = 0.5772
    e = np.e
    EmaxN = ((1 - gamma) * norm.ppf(1 - 1/n_trials)
             + gamma * norm.ppf(1 - 1/(n_trials * e)))
    # Convert annualised SR back to daily-frequency for the variance scaling
    sr_daily = sr_obs / np.sqrt(252)
    var_sr_daily = (1 - skew * sr_daily + (kurt - 1) / 4 * sr_daily ** 2) / (t_obs_days - 1)
    sr0_daily = np.sqrt(max(var_sr_daily, 0)) * EmaxN
    sr0_ann = sr0_daily * np.sqrt(252)
    # DSR = Phi((SR_obs - SR0) / std(SR))
    denom = np.sqrt(var_sr_daily) * np.sqrt(252)
    z = (sr_obs - sr0_ann) / denom if denom > 0 else float("nan")
    dsr = float(norm.cdf(z)) if not np.isnan(z) else float("nan")
    sr_deflated = sr_obs - sr0_ann  # what's left after deflation
    return {
        "sr_obs": sr_obs,
        "sr0_threshold": sr0_ann,
        "sr_deflated": sr_deflated,
        "z": z,
        "dsr_prob_real": dsr,
        "EmaxN": EmaxN,
        "n_trials": n_trials,
    }


def step_T4_dsr(M_full: pd.DataFrame, M_2026: pd.DataFrame):
    print("=" * 80)
    print("T4 — Deflated Sharpe (Bailey-Lopez de Prado)")
    print("=" * 80)
    for lab, M in [("Full 2022-2025", M_full), ("2026 only", M_2026)]:
        pnl = block_capped_pnl(M).fillna(0.0)
        sr_obs = pnl.mean() / pnl.std(ddof=1) * np.sqrt(252)
        sk = pnl.skew()
        ku = pnl.kurt()  # pandas returns excess kurtosis
        print(f"\n{lab} — daily Sharpe ann = {sr_obs:.3f}, skew={sk:.2f}, "
              f"excess kurt={ku:.2f}, T={len(pnl)} days")
        print(f"  {'n_trials':>9} | {'SR0 threshold':>13} | {'SR deflated':>11} | "
              f"{'DSR P(real)':>11} | Verdict")
        for n_trials in [1, 5, 18, 50, 100]:
            d = deflated_sharpe(sr_obs, len(pnl), n_trials, sk, ku)
            verdict = "FAIL <1.0" if d["sr_deflated"] < 1.0 else "pass >1.0"
            print(f"  {n_trials:>9d} | {d['sr0_threshold']:>13.3f} | "
                  f"{d['sr_deflated']:>11.3f} | {d['dsr_prob_real']:>10.3f} | {verdict}")
    print()


def step_T5_slippage(M_full: pd.DataFrame):
    print("=" * 80)
    print("T5 — Slippage breakeven sweep (full 2022-2025, iid bootstrap)")
    print("=" * 80)
    print(f"{'slip_R':>7} | {'meanR':>8} | {'Sharpe':>7} | {'Pass%':>6} | {'Bust(tot)%':>10}")
    print("-" * 60)
    last_pass = None
    last_busts = None
    for slip in np.arange(0.0, 0.31, 0.025):
        M = build_3sleeve_matrix(lo="2022", hi="2025", slip_R=slip)
        mr = mean_R(M)
        sh = daily_sharpe_ann(M)
        out = simulate(M, mode="iid_bootstrap", n_paths=10000)
        p = out["pass_rate"]
        ft = out["fail_total"]
        print(f"{slip:7.3f} | {mr:+8.4f} | {sh:7.3f} | {p*100:5.1f}% | {ft*100:9.1f}%")
        if last_pass is not None and last_pass > last_busts and p <= ft:
            print(f"  -> pass = bust crossover at ~slip_R={slip-0.0125:.3f}")
        last_pass, last_busts = p, ft
    print()
    print("Note: slip_R is the breakout-level slippage as a fraction of 1R "
          "(applied symmetrically: entry adverse + stop fills past level).")


def step_T6_delay(periods: list):
    print("=" * 80)
    print("T6 — Delay test on the 3 RETAINED sleeves (NOT just rejected sleeves)")
    print("=" * 80)
    print(f"{'Period':>15} | {'Delay':>5} | {'meanR':>8} | {'Sharpe':>7} | {'Pass% iid':>10}")
    print("-" * 70)
    for lab, lo, hi in periods:
        for delay in [0, 1, 2]:
            M = build_3sleeve_matrix(lo=lo, hi=hi, delay_bars=delay)
            mr = mean_R(M)
            sh = daily_sharpe_ann(M)
            p = simulate(M, mode="iid_bootstrap", n_paths=10000)["pass_rate"]
            print(f"{lab:>15} | {delay:5d} | {mr:+8.4f} | {sh:7.3f} | {p*100:8.1f}%")
        print("-" * 70)


if __name__ == "__main__":
    print("Loading data...")
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    M_2026 = build_3sleeve_matrix(lo="2026", hi="2026")
    M_all = build_3sleeve_matrix(lo="2021", hi="2026")
    print(f"  Full 2022-2025: {len(M_full)} days; 2026: {len(M_2026)} days")
    print()

    step_T3_drop_top_n(M_full, M_2026)
    step_T4_dsr(M_full, M_2026)
    step_T5_slippage(M_full)
    step_T6_delay([("Full 2022-25", "2022", "2025"),
                   ("2023 chop", "2023", "2023"),
                   ("2024-25 OOS", "2024", "2025"),
                   ("2026 cherry", "2026", "2026")])
