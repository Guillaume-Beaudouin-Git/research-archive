"""
breakout_phase3_dsr.py — DSR/AMTP on the total breakout search space.

Total n_trials = phase 1 (10 variants) + phase 2 (4 exits × n_survivors) +
                  (possible) cost variants × filter variants on survivors.

For each survivor's best config, compute:
  - Bailey-Lopez de Prado DSR with n_trials = total
  - SR0 threshold for various n_trials scenarios

Also: block-bootstrap p-value of mean R total.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import norm


def daily_pnl_from_trades(df_trades: pd.DataFrame, r_col: str,
                           risk_per_trade: float = 0.005) -> pd.Series:
    """Convert per-trade R to daily PnL series."""
    pnl = df_trades[r_col] * risk_per_trade
    return pnl.fillna(0.0)


def deflated_sharpe(sr_obs: float, t_obs_days: int, n_trials: int,
                    skew: float, kurt: float) -> dict:
    if t_obs_days <= 2 or n_trials < 1:
        return {"sr0": float("nan"), "sr_def": float("nan"),
                "z": float("nan"), "dsr": float("nan")}
    gamma = 0.5772
    e = np.e
    EmaxN = ((1 - gamma) * norm.ppf(1 - 1/n_trials)
             + gamma * norm.ppf(1 - 1/(n_trials * e)))
    sr_daily = sr_obs / np.sqrt(252)
    var_sr_daily = (1 - skew * sr_daily + (kurt - 1) / 4 * sr_daily ** 2) / (t_obs_days - 1)
    if var_sr_daily <= 0:
        return {"sr0": float("nan"), "sr_def": float("nan"),
                "z": float("nan"), "dsr": float("nan")}
    sr0_daily = np.sqrt(var_sr_daily) * EmaxN
    sr0_ann = sr0_daily * np.sqrt(252)
    denom = np.sqrt(var_sr_daily) * np.sqrt(252)
    z = (sr_obs - sr0_ann) / denom if denom > 0 else float("nan")
    dsr = float(norm.cdf(z)) if not np.isnan(z) else float("nan")
    return {"sr0": sr0_ann, "sr_def": sr_obs - sr0_ann, "z": z, "dsr": dsr}


def block_bootstrap_pvalue(values: np.ndarray, dates: np.ndarray,
                            n_boot: int = 1000, block_len_days: int = 20,
                            seed: int = 42) -> tuple[float, float]:
    """Block-bootstrap p-value of mean > 0."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"v": values, "d": dates}).sort_values("d")
    days_u = sorted(df["d"].unique())
    means = []
    for _ in range(n_boot):
        n_blocks = (len(days_u) + block_len_days - 1) // block_len_days
        sampled_days = []
        for _b in range(n_blocks):
            start_idx = rng.integers(0, len(days_u) - block_len_days + 1)
            sampled_days.extend(days_u[start_idx:start_idx + block_len_days])
        sampled_days = sampled_days[:len(days_u)]
        sub = df[df["d"].isin(sampled_days)]
        if len(sub):
            means.append(sub["v"].mean())
    arr = np.array(means)
    p_value_one_sided = float((arr <= 0).mean())
    return float(arr.mean()), p_value_one_sided


if __name__ == "__main__":
    print("=" * 90)
    print("PHASE 3 — DSR on total breakout search space")
    print("=" * 90)
    df_phase1 = pd.read_csv("breakout_phase1_full.csv")
    n_phase1 = len(df_phase1)
    print(f"\nPhase 1 variants: {n_phase1}")

    no_survivors_file = Path("breakout_phase2_no_survivors.txt")
    if no_survivors_file.exists():
        print("\n⚠ No survivors from Phase 1/2 — DSR moot.")
        print("Conclusion: with TWO-SIDED requirement (L25), no breakout variant survives.")
        exit(0)

    # Load phase 2 if exists
    if Path("breakout_phase2_full.csv").exists():
        df_phase2 = pd.read_csv("breakout_phase2_full.csv")
        n_phase2 = len(df_phase2)
    else:
        df_phase2 = pd.DataFrame()
        n_phase2 = 0
    n_total_trials = n_phase1 + n_phase2
    print(f"Phase 2 variants: {n_phase2}")
    print(f"Total n_trials: {n_total_trials}")
    print()

    # For each survivor (= variant × exit combo from phase 2), compute DSR
    if not df_phase2.empty:
        # Sort by mean_R_total descending, get top 5
        candidates = df_phase2.sort_values("mean_R_total", ascending=False).head(10)
        print("=" * 90)
        print(f"DSR on top candidates from Phase 2")
        print("=" * 90)
        rows = []
        for _, row in candidates.iterrows():
            v = row["variant"]
            et = row["exit_type"]
            mean_R = row["mean_R_total"]
            n_trades = int(row["n_total"])
            # Load trades to compute Sharpe + skew + kurt
            df_t = pd.read_parquet(f"breakout_phase2_trades_{v}.parquet")
            r_col = f"r_net_{et}"
            r = df_t[r_col].dropna().values
            # Convert to daily by aggregating per date (max 1 trade per day)
            pnl = pd.Series(r, index=df_t.index[df_t[r_col].notna()])
            # Annualised Sharpe (per-trade × sqrt(trades/yr))
            # Approximation: trades/yr ≈ n_trades / 16 years
            trades_per_yr = n_trades / 16
            mean_per_trade = pnl.mean()
            std_per_trade = pnl.std()
            sharpe_ann = (mean_per_trade / std_per_trade) * np.sqrt(trades_per_yr) if std_per_trade > 0 else 0
            skew = pnl.skew()
            kurt = pnl.kurt()
            # DSR with full n_trials
            d = deflated_sharpe(sharpe_ann, n_trades, n_total_trials, skew, kurt)
            # block bootstrap p
            boot_mean, p_val = block_bootstrap_pvalue(r, df_t.index[df_t[r_col].notna()].values)
            rows.append({
                "variant": v, "exit": et,
                "n_trades": n_trades, "mean_R": mean_R,
                "sharpe_ann_approx": sharpe_ann,
                "skew": skew, "kurt": kurt,
                "sr0_threshold": d["sr0"], "sr_deflated": d["sr_def"],
                "dsr_p_real": d["dsr"],
                "boot_mean": boot_mean,
                "p_one_sided": p_val,
            })
        df_dsr = pd.DataFrame(rows)
        df_dsr.to_csv("breakout_phase3_dsr.csv", index=False)
        print(df_dsr.round(4).to_string(index=False))
        print()
        survivors_dsr = df_dsr[df_dsr["sr_deflated"] > 0]
        print(f"\nVariants surviving DSR (sr_deflated > 0): {len(survivors_dsr)}/{len(df_dsr)}")
        if len(survivors_dsr):
            print(survivors_dsr[["variant", "exit", "mean_R", "sharpe_ann_approx",
                                  "sr_deflated", "dsr_p_real", "p_one_sided"]].round(3).to_string(index=False))
