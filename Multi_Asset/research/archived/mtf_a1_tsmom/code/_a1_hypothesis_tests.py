"""A1 — Hypothesis tests H1-H5, reading the engine outputs.

Outputs printed AND saved to outputs/mtf/a1_h_tests.json + monthly aux parquets.
"""
from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "mtf"

# Load helpers from the engine
spec = importlib.util.spec_from_file_location("a1", str(ROOT / "code/mtf/a1_tsmom_multihorizon.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


def sharpe_ann_monthly(s: pd.Series) -> float:
    x = s.dropna()
    if x.std() == 0 or len(x) < 2:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(12))


def hac_ols(y: pd.Series, X_df: pd.DataFrame, lag: int = 6):
    df = pd.concat([y.rename("y"), X_df], axis=1).dropna()
    X = sm.add_constant(df.drop(columns="y"))
    mod = sm.OLS(df["y"], X).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    out = {
        "alpha":    float(mod.params["const"]),
        "alpha_t":  float(mod.tvalues["const"]),
        "alpha_p":  float(mod.pvalues["const"]),
        "n":        int(df.shape[0]),
        "betas":    {k: float(v) for k, v in mod.params.items() if k != "const"},
        "betas_t":  {k: float(v) for k, v in mod.tvalues.items() if k != "const"},
        "r2":       float(mod.rsquared),
    }
    return out


def psr_mertens(monthly_returns: pd.Series, sr_target_ann: float = 0.5) -> dict:
    """PSR with Mertens (2002) variance accounting for skew/kurtosis.

    Returns Prob(true SR > sr_target_ann) under monthly observations.
    """
    x = monthly_returns.dropna().values
    n = len(x)
    if n < 12 or x.std(ddof=1) == 0:
        return {"psr": float("nan"), "sr_obs_ann": float("nan"),
                "skew": float("nan"), "ex_kurt": float("nan"), "n": n}
    mu_m = float(x.mean())
    sd_m = float(x.std(ddof=1))
    sr_obs_m = mu_m / sd_m
    sr_obs_ann = sr_obs_m * np.sqrt(12)
    z = (x - mu_m) / sd_m
    skew = float(np.mean(z**3))
    ex_kurt = float(np.mean(z**4) - 3.0)
    sr_target_m = sr_target_ann / np.sqrt(12)
    var_sr_m = (1 - skew * sr_obs_m + ex_kurt / 4.0 * sr_obs_m**2) / (n - 1)
    if var_sr_m <= 0:
        return {"psr": float("nan"), "sr_obs_ann": sr_obs_ann,
                "skew": skew, "ex_kurt": ex_kurt, "n": n}
    se_sr_m = np.sqrt(var_sr_m)
    z_stat = (sr_obs_m - sr_target_m) / se_sr_m
    return {
        "psr": float(norm.cdf(z_stat)),
        "sr_obs_ann": sr_obs_ann,
        "skew": skew,
        "ex_kurt": ex_kurt,
        "n": n,
        "sr_target_ann": sr_target_ann,
    }


# ----------------- panel & daily-level pieces ---------------------
def panel_daily_for_H1():
    """Reload data to compute the H1 panel test on daily returns vs lagged-sign mom."""
    panel, meta = mod.load_panel()
    rets = mod.daily_returns(panel)
    sigma = mod.vol_ex_ante_daily(rets)
    S = mod.signal_tsmom_daily(panel)
    # Use a single-horizon trailing 12m sign signal at MONTHLY frequency
    # to match Huang-Li-Wang-Zhou style panel test (monthly returns, lagged monthly signal).
    monthly_ret_panel = (1 + rets.fillna(0)).resample("ME").prod() - 1
    # Recover signal at month-end of prior month
    S_eom = S.resample("BME").last()
    # Align index to month-end (ME) timing
    S_eom_eom = S_eom.copy()
    S_eom_eom.index = S_eom_eom.index + pd.offsets.MonthEnd(0)
    # Lag: signal at end of month t-1 applies to month t
    S_lagged = S_eom_eom.shift(1)
    # Stack to long format
    rets_long = monthly_ret_panel.stack().rename("r").reset_index()
    rets_long.columns = ["date", "asset", "r"]
    S_long = S_lagged.stack().rename("s").reset_index()
    S_long.columns = ["date", "asset", "s"]
    df = rets_long.merge(S_long, on=["date", "asset"]).dropna()
    return df


# ----------------- H1: panel + stationary block-bootstrap -----------------
def h1_panel_test(df_panel: pd.DataFrame, n_boot: int = 5000, block_size_months: int = 12,
                  seed: int = 123):
    """OLS panel: r = a + b * sign(mom_lag) + err
    Stationary block-bootstrap (Politis-Romano) on the time dimension.
    Returns t_empirical vs distribution under H0 (random sign per asset).
    """
    rng = np.random.default_rng(seed)
    y = df_panel["r"].values
    x = df_panel["s"].values
    # OLS coefficient & HAC t-stat
    X = sm.add_constant(x)
    res_real = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    coef_emp = float(res_real.params[1])
    t_emp = float(res_real.tvalues[1])

    # Stationary block-bootstrap for null: randomly resample TIME index in blocks,
    # but PRESERVE the sign series structure (i.e., shuffle r_t while keeping s_t).
    # Strategy: aggregate by (date) → monthly panel returns shape (T, N).
    pivot_r = df_panel.pivot(index="date", columns="asset", values="r").sort_index()
    pivot_s = df_panel.pivot(index="date", columns="asset", values="s").sort_index()
    common_dates = pivot_r.dropna(how="all").index.intersection(pivot_s.dropna(how="all").index)
    R = pivot_r.loc[common_dates].fillna(0).values  # (T, N)
    S = pivot_s.loc[common_dates].fillna(0).values  # (T, N)
    T, N = R.shape
    # Stationary block bootstrap of TIME indices
    # Expected block length = block_size_months ⇒ p_geo = 1/L
    p_geo = 1.0 / block_size_months
    coefs_null = np.empty(n_boot)
    for b in range(n_boot):
        # Build a permuted time index by stationary block-bootstrap:
        # break R rows into random blocks aligned with S row PERMUTATION.
        # Implementation: shuffle the TIME index of R only; keep S as-is.
        # This breaks the temporal alignment between signal and returns → null.
        idx_perm = np.empty(T, dtype=int)
        i = 0
        while i < T:
            start = int(rng.integers(0, T))
            L = int(rng.geometric(p_geo))
            for j in range(L):
                idx_perm[i] = (start + j) % T
                i += 1
                if i >= T:
                    break
        R_perm = R[idx_perm, :]
        # OLS on permuted panel
        y_null = R_perm.flatten()
        x_null = S.flatten()
        if np.all(x_null == 0):
            coefs_null[b] = 0.0
            continue
        X_null = np.column_stack([np.ones_like(x_null), x_null])
        # Use closed-form OLS for speed; no need for HAC under H0 panel
        try:
            beta = np.linalg.lstsq(X_null, y_null, rcond=None)[0]
            coefs_null[b] = float(beta[1])
        except Exception:
            coefs_null[b] = 0.0

    p95 = float(np.percentile(coefs_null, 95))
    p99 = float(np.percentile(coefs_null, 99))
    p_value_emp = float(np.mean(coefs_null >= coef_emp))
    return {
        "coef_empirical": coef_emp,
        "t_HAC6_empirical": t_emp,
        "n_obs_panel": int(len(y)),
        "n_dates": T,
        "n_assets": N,
        "block_size_months": block_size_months,
        "n_boot": n_boot,
        "null_p95": p95,
        "null_p99": p99,
        "p_value_one_sided": p_value_emp,
        "pass": bool(coef_emp > p95),
    }


# ----------------- H2: alpha vs BH -------------------
def h2_alpha_vs_bh(m_tsmom: pd.Series, m_bh: pd.Series):
    return hac_ols(m_tsmom, m_bh.rename("BH").to_frame(), lag=6)


# ----------------- H3: PSR(0.5) -----------------------
def h3_psr(m_tsmom: pd.Series):
    return psr_mertens(m_tsmom, sr_target_ann=0.5)


# ----------------- H4: leg split (long-month vs short-month) -----
def h4_leg_split(m_tsmom: pd.Series, S_proxy: pd.Series):
    """Split months by sign of portfolio-aggregate signal (long vs short tilt)."""
    df = pd.concat([m_tsmom.rename("r"), S_proxy.rename("s")], axis=1).dropna()
    long = df[df["s"] > 0]["r"]
    short = df[df["s"] < 0]["r"]
    neutral = df[df["s"] == 0]["r"]
    res = {
        "long":  {"n": int(long.shape[0]),  "mean_monthly": float(long.mean()),
                  "sharpe_ann": sharpe_ann_monthly(long)},
        "short": {"n": int(short.shape[0]), "mean_monthly": float(short.mean()),
                  "sharpe_ann": sharpe_ann_monthly(short)},
        "neutral": {"n": int(neutral.shape[0]), "mean_monthly": float(neutral.mean()),
                    "sharpe_ann": sharpe_ann_monthly(neutral)},
    }
    res["pass_both_positive"] = bool(res["long"]["mean_monthly"] > 0
                                     and res["short"]["mean_monthly"] > 0)
    return res


# ----------------- H5: post-2010 -----------------------------------
def h5_post_2010(m_tsmom: pd.Series):
    sub = m_tsmom[m_tsmom.index >= "2010-01-01"]
    sr = sharpe_ann_monthly(sub)
    return {
        "n_months": int(sub.shape[0]),
        "sharpe_ann": sr,
        "pass": bool(sr > 0.30),
    }


# ----------------- Hidden-factor regression -------------------------
def hidden_factor(m_tsmom: pd.Series, m_bh: pd.Series, panel_close):
    es_ret = panel_close["ES=F"].pct_change()
    es_m = (1 + es_ret.fillna(0)).resample("ME").prod() - 1
    X = pd.concat([es_m.rename("ES"), m_bh.rename("BH")], axis=1)
    return hac_ols(m_tsmom, X, lag=6)


# ----------------- Segment stability --------------------------------
def segment_stability(m_tsmom: pd.Series, n_seg: int = 6):
    """Split timeline into n_seg consecutive segments; report Sharpe per segment."""
    n = m_tsmom.shape[0]
    if n < n_seg:
        return {}
    boundaries = np.linspace(0, n, n_seg + 1).astype(int)
    segs = {}
    for i in range(n_seg):
        a, b = boundaries[i], boundaries[i + 1]
        sub = m_tsmom.iloc[a:b]
        segs[f"seg_{i+1}"] = {
            "start": str(sub.index.min().date()),
            "end":   str(sub.index.max().date()),
            "n_months": int(sub.shape[0]),
            "sharpe_ann": sharpe_ann_monthly(sub),
            "maxdd":     mod.maxdd(sub),
        }
    return segs


# ----------------- RandomSign test ---------------------------------
def rs_percentile(m_tsmom: pd.Series, rs_sharpes_path: Path):
    rs = pd.read_parquet(rs_sharpes_path)["rs_sharpe_ann"].values
    sr_tsmom = sharpe_ann_monthly(m_tsmom)
    pct = float((rs <= sr_tsmom).mean() * 100.0)
    return {
        "tsmom_sharpe_ann": sr_tsmom,
        "rs_mean": float(rs.mean()),
        "rs_p05": float(np.percentile(rs, 5)),
        "rs_p50": float(np.percentile(rs, 50)),
        "rs_p95": float(np.percentile(rs, 95)),
        "tsmom_percentile_in_rs": pct,
    }


# ----------------- Build aggregate signal series for H4 -----------
def build_portfolio_signal_series():
    panel, _ = mod.load_panel()
    rets = mod.daily_returns(panel)
    sigma = mod.vol_ex_ante_daily(rets)
    S_daily = mod.signal_tsmom_daily(panel)
    pos_eom = mod.build_monthly_positions(panel, rets, sigma, S_daily)
    pos_eom = pos_eom.shift(1)  # apply during next month
    # Aggregate portfolio-level signal = sign(sum of pos × sigma_ind / sigma_inv) = ...
    # Simpler: average of S_eom across assets weighted by inverse sigma — proxy for the
    # net directional tilt of the portfolio.
    S_eom = S_daily.resample("BME").last()
    sigma_eom = sigma.resample("BME").last()
    w_inv = (1.0 / sigma_eom).where(sigma_eom > 0)
    w_inv = w_inv.div(w_inv.sum(axis=1), axis=0)  # normalized inverse-vol weights
    portfolio_signal = (S_eom * w_inv).sum(axis=1).shift(1)
    # Convert index to ME
    portfolio_signal.index = portfolio_signal.index + pd.offsets.MonthEnd(0)
    return portfolio_signal


# ----------------- main --------------------------------------------
def main():
    rets_df = pd.read_parquet(OUT / "a1_returns.parquet")
    m_tsmom = rets_df["TSMOM_net_monthly"]
    m_bh = rets_df["BH_net_monthly"]

    print("=== A1 H1-H5 tests ===")
    # H2
    print("\nH2 — TSMOM ~ alpha + beta·BH (HAC lag-6):")
    h2 = h2_alpha_vs_bh(m_tsmom, m_bh)
    print(json.dumps(h2, indent=2))
    h2_pass = (h2["alpha"] > 0) and (h2["alpha_t"] > 1.5)
    print(f"H2 PASS: {h2_pass}")

    # H3 PSR
    print("\nH3 — PSR(SR*=0.5) on net monthly:")
    h3 = h3_psr(m_tsmom)
    print(json.dumps(h3, indent=2))
    h3_pass = (not np.isnan(h3["psr"])) and (h3["psr"] > 0.95)
    print(f"H3 PASS: {h3_pass}")

    # H4 leg split
    print("\nH4 — leg split by portfolio-signal direction:")
    port_sig = build_portfolio_signal_series()
    h4 = h4_leg_split(m_tsmom, port_sig)
    print(json.dumps(h4, indent=2))

    # H5 post-2010
    print("\nH5 — post-2010 Sharpe:")
    h5 = h5_post_2010(m_tsmom)
    print(json.dumps(h5, indent=2))

    # Hidden-factor
    panel, _ = mod.load_panel()
    print("\nHidden-factor (TSMOM ~ alpha + ES + BH):")
    hf = hidden_factor(m_tsmom, m_bh, panel)
    print(json.dumps(hf, indent=2))

    # Segment stability
    print("\nSegment stability (6 segments):")
    seg = segment_stability(m_tsmom, n_seg=6)
    for k, v in seg.items():
        print(f"  {k} [{v['start']} → {v['end']}, n={v['n_months']}]: SR={v['sharpe_ann']:.3f}  MaxDD={v['maxdd']:.3f}")

    # RandomSign
    print("\nRS percentile:")
    rs = rs_percentile(m_tsmom, OUT / "a1_rs_sharpes.parquet")
    print(json.dumps(rs, indent=2))

    # H1 (panel + block-bootstrap)
    print("\nH1 — panel OLS + stationary block-bootstrap (5000 reps)…")
    df_panel = panel_daily_for_H1()
    h1 = h1_panel_test(df_panel, n_boot=5000, block_size_months=12, seed=123)
    print(json.dumps(h1, indent=2))
    h1_pass = h1["pass"]

    # Verdict
    print("\n========== VERDICT ==========")
    print(f"H1 (panel signal exists): {'PASS' if h1_pass else 'FAIL'}")
    print(f"H2 (alpha vs BH, t>1.5):  {'PASS' if h2_pass else 'FAIL'}")
    print(f"H3 (PSR(0.5)>0.95):       {'PASS' if h3_pass else 'FAIL'}")
    print(f"H4 (both legs positive):  {'PASS' if h4['pass_both_positive'] else 'FAIL'}")
    print(f"H5 (post-2010 SR>0.3):    {'PASS' if h5['pass'] else 'FAIL'}")
    defendable = h1_pass and h2_pass and h3_pass
    print(f"=> A1 DÉFENDABLE: {'OUI' if defendable else 'NON'}")

    # Save all
    all_out = {
        "H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5,
        "hidden_factor": hf,
        "segment_stability": seg,
        "rs_percentile": rs,
        "verdict": {
            "H1_pass": h1_pass,
            "H2_pass": h2_pass,
            "H3_pass": h3_pass,
            "H4_pass": h4["pass_both_positive"],
            "H5_pass": h5["pass"],
            "A1_defendable": defendable,
        },
    }
    with open(OUT / "a1_h_tests.json", "w") as f:
        json.dump(all_out, f, indent=2, default=str)
    print(f"\nSaved {OUT/'a1_h_tests.json'}")


if __name__ == "__main__":
    main()
