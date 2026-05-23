"""
multi_asset_tsmom/methodology_audit.py
=======================================
Methodology audit: re-evaluate MH+B under 5 corrected infrastructure fixes.

Fixes applied (simultaneous, all-or-nothing):
  Fix 1 — Daily vol targeting (63-day daily P&L rolling vol × sqrt(252))
  Fix 2 — Excess returns over risk-free rate (FRED DTB3)
  Fix 3 — Newey-West HAC standard errors (statsmodels, maxlags=6)
  Fix 4 — TSMOM diagnostics (directional accuracy, quintile, convexity test)
  Fix 5 — Rename DSR → approx_multi_test_penalty with documentation

Original MH+B reference metrics (from multi_horizon.py):
  Sharpe 0.478, MaxDD -14.5%, EuroCrisis MaxDD -7.1%, resid_sharpe 0.516

DO NOT COMMIT — user reviews corrected metrics before deployment decision.

Run:
  python -m Equities.research.passed.multi_asset_tsmom.methodology_audit
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
START        = "2004-01-01"
END          = pd.Timestamp.today().strftime("%Y-%m-%d")
COST_RT      = 0.0005
ANN_M        = 12
ANN_D        = 252
UNIVERSE     = ["SPY", "QQQ", "EFA", "EEM", "IWM",
                "TLT", "IEF", "SHY", "GLD", "VNQ"]
BETA_FACTORS = ["SPY", "AGG"]
N_TESTS      = 64    # cumulative (53 crypto + 4 FX + 1 feasibility + 4 overlays + 2 multi-horizon)

CRASH_PERIODS = {
    "GFC_2008":    ("2008-07-01", "2009-06-30"),
    "EuroCrisis":  ("2011-04-01", "2012-01-31"),
    "COVID_2020":  ("2020-02-01", "2020-05-31"),
    "Inflation22": ("2022-01-01", "2022-12-31"),
}

RESULTS_DIR  = Path(__file__).parent
SUMMARY_MD   = RESULTS_DIR / "methodology_audit_summary.md"

# Original MH+B reference (pre-audit)
ORIGINAL_MHB = {
    "sharpe":        0.478,
    "ann_ret":       0.049,
    "ann_vol":       0.102,
    "max_dd":       -0.145,
    "alpha_ann":     0.042,
    "alpha_t":       1.47,
    "resid_sharpe":  0.516,
    "eurocrisis_dd": -0.071,
    "covid_dd":      None,
    "dsr_pvalue":    0.7900,
}


# ──────────────────────────────────────────────────────────────────────────────
# Fix 2 — RF data from FRED DTB3
# ──────────────────────────────────────────────────────────────────────────────
def fetch_rf_daily(start: str, end: str) -> pd.Series:
    """
    Download 3-month T-bill rate (DTB3) from FRED via pandas_datareader.
    Convert annualised % → daily RF: rf_daily = (1 + DTB3/100)^(1/252) - 1
    Falls back to zero if FRED is unavailable.
    """
    try:
        import pandas_datareader.data as web
        raw = web.DataReader("DTB3", "fred", start, end)
        raw = raw["DTB3"].ffill().dropna()
        rf_daily = (1 + raw / 100) ** (1 / ANN_D) - 1
        rf_daily.index = pd.to_datetime(rf_daily.index)
        log.info(f"FRED DTB3: {len(rf_daily)} obs, mean={rf_daily.mean()*ANN_D*100:.2f}% p.a.")
        return rf_daily
    except Exception as exc:
        log.warning(f"FRED DTB3 fetch failed ({exc}). Using rf=0.")
        return pd.Series(dtype=float)


# ──────────────────────────────────────────────────────────────────────────────
# Data
# ──────────────────────────────────────────────────────────────────────────────
def fetch_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    """Returns (px_daily_univ, px_daily_beta, factor_ret_monthly_excess, rf_daily)."""
    all_tickers = list(dict.fromkeys(UNIVERSE + BETA_FACTORS))
    log.info(f"Downloading {all_tickers} …")
    raw = yf.download(all_tickers, start=START, end=END,
                      auto_adjust=True, progress=False)
    px  = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    px.index = pd.to_datetime(px.index)
    px  = px.ffill(limit=3)

    px_univ = px[[c for c in UNIVERSE if c in px.columns]]
    px_beta = px[[c for c in BETA_FACTORS if c in px.columns]]

    # Fix 2: excess returns for OLS factors
    rf_daily = fetch_rf_daily(START, END)
    rf_monthly = _rf_daily_to_monthly(rf_daily, px_beta.resample("ME").last().index)

    px_beta_m  = px_beta.resample("ME").last()
    factor_log = np.log(px_beta_m / px_beta_m.shift(1))
    factor_exc = factor_log.subtract(rf_monthly, axis=0).dropna(how="all")

    return px_univ, px_beta, factor_exc, rf_daily


def _rf_daily_to_monthly(rf_daily: pd.Series,
                          month_ends: pd.DatetimeIndex) -> pd.Series:
    """Compound daily RF rates to monthly RF, aligned to month-end index."""
    if rf_daily.empty:
        return pd.Series(0.0, index=month_ends)
    # For each month-end, sum daily rf in that calendar month (approx compounding)
    rf_m = {}
    for me in month_ends:
        ms = me - pd.offsets.MonthBegin(1)
        chunk = rf_daily.loc[ms:me]
        rf_m[me] = float((1 + chunk).prod() - 1) if len(chunk) > 0 else 0.0
    return pd.Series(rf_m)


# ──────────────────────────────────────────────────────────────────────────────
# Signal construction (multi-horizon, self-contained)
# ──────────────────────────────────────────────────────────────────────────────
def _tsmom_signal_k(px: pd.DataFrame, k: int, vol_window: int = 12) -> pd.DataFrame:
    logret = np.log(px / px.shift(1))
    cumret = logret.rolling(k).sum().shift(1)
    vol    = logret.rolling(vol_window).std()
    denom  = (vol * np.sqrt(k)).replace(0, np.nan)
    return np.tanh((cumret / denom).replace([np.inf, -np.inf], np.nan))


def _combined_signal(px: pd.DataFrame) -> pd.DataFrame:
    s1  = _tsmom_signal_k(px, 1)
    s3  = _tsmom_signal_k(px, 3)
    s12 = _tsmom_signal_k(px, 12)
    stacked = pd.concat([s1, s3, s12], axis=0, keys=["1m", "3m", "12m"]).groupby(level=1)
    return stacked.mean()


# ──────────────────────────────────────────────────────────────────────────────
# Monthly backtest (excess returns)
# ──────────────────────────────────────────────────────────────────────────────
def build_mh_monthly_excess(px_daily: pd.DataFrame,
                             rf_daily: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    """Multi-horizon TSMOM monthly net EXCESS returns + weights."""
    px_m   = px_daily.resample("ME").last()
    logret = np.log(px_m / px_m.shift(1)).dropna(how="all")

    # Fix 2: subtract monthly RF from each asset's log return
    rf_m = _rf_daily_to_monthly(rf_daily, logret.index)
    excess_ret = logret.subtract(rf_m, axis=0)

    sig = _combined_signal(px_m)
    fwd = excess_ret.shift(-1)
    n   = sig.shape[1]
    w   = sig.fillna(0.0) / n

    idx    = (sig.dropna(how="all").index
                 .intersection(logret.index)
                 .intersection(fwd.dropna(how="all").index))
    w_al   = w.reindex(idx)
    fwd_al = fwd.reindex(idx)

    gross    = (w_al * fwd_al).sum(axis=1)
    turnover = (w_al - w_al.shift(1).fillna(0)).abs().sum(axis=1)
    net      = (gross - turnover * (COST_RT / 2.0)).dropna()
    return net, w_al


# ──────────────────────────────────────────────────────────────────────────────
# Fix 1 — Daily vol targeting
# ──────────────────────────────────────────────────────────────────────────────
def vol_target_daily(px_daily: pd.DataFrame,
                     weights_m: pd.DataFrame,
                     net_raw: pd.Series,
                     rf_daily: pd.Series,
                     target: float = 0.10,
                     lb_days: int = 63,
                     cap: float = 2.0) -> pd.Series:
    """
    Fix 1: Daily vol targeting.
    Steps:
      1. Compute daily portfolio P&L from monthly weights (forward-filled) × daily excess returns
      2. Rolling lb_days-day std × sqrt(252) → daily realized vol
      3. Sample at each month-end → monthly vol estimate
      4. Scale = target / vol.shift(1) clipped at cap
      5. Apply to net_raw monthly returns
    """
    daily_logret = np.log(px_daily / px_daily.shift(1))
    assets = [c for c in weights_m.columns if c in daily_logret.columns]

    # Fix 2 inside vol estimation: subtract daily RF
    if not rf_daily.empty:
        rf_aligned = rf_daily.reindex(daily_logret.index).fillna(0.0)
        daily_exc = daily_logret[assets].subtract(rf_aligned, axis=0)
    else:
        daily_exc = daily_logret[assets]

    n = weights_m.shape[1]
    w_daily  = (weights_m[assets] / n).reindex(daily_exc.index, method="ffill")
    daily_pf = (w_daily * daily_exc).sum(axis=1)

    # 63-day rolling realized vol
    rvol_daily = daily_pf.rolling(lb_days).std() * np.sqrt(ANN_D)

    # Sample at month-ends
    rvol_monthly = rvol_daily.reindex(net_raw.index, method="ffill")

    # Scale applied one period ahead (shift(1) = vol estimated at T → applied to T+1)
    scale = (target / rvol_monthly.shift(1)).clip(upper=cap)
    return (net_raw * scale).dropna()


# ──────────────────────────────────────────────────────────────────────────────
# Overlay B with daily vol targeting (Fix 1 inside stop simulation)
# ──────────────────────────────────────────────────────────────────────────────
def overlay_b_daily_vt(px_daily: pd.DataFrame,
                        weights_m: pd.DataFrame,
                        net_raw: pd.Series,
                        rf_daily: pd.Series,
                        stop_pct: float = 0.05,
                        vt_target: float = 0.10,
                        vt_lb_days: int = 63,
                        vt_cap: float = 2.0) -> pd.Series:
    """
    Overlay B with Fix 1 (daily vol targeting) and Fix 2 (excess returns).
    Vol scale computed from daily P&L series, sampled at month-ends.
    """
    daily_logret = np.log(px_daily / px_daily.shift(1))
    assets = [c for c in weights_m.columns if c in daily_logret.columns]

    if not rf_daily.empty:
        rf_aligned = rf_daily.reindex(daily_logret.index).fillna(0.0)
        daily_exc = daily_logret[assets].subtract(rf_aligned, axis=0)
    else:
        daily_exc = daily_logret[assets]

    n = weights_m.shape[1]
    w_daily  = (weights_m[assets] / n).reindex(daily_exc.index, method="ffill")
    daily_pf = (w_daily * daily_exc).sum(axis=1)
    rvol_d   = daily_pf.rolling(vt_lb_days).std() * np.sqrt(ANN_D)
    rvol_me  = rvol_d.reindex(weights_m.index, method="ffill")
    scale_m  = (vt_target / rvol_me.shift(1)).clip(upper=vt_cap).fillna(1.0)

    scaled_w = weights_m.multiply(scale_m, axis=0)

    monthly_returns = {}
    prev_scaled_w   = pd.Series(0.0, index=scaled_w.columns)

    for i, month_end in enumerate(scaled_w.index):
        if i == 0:
            continue
        prev_end = scaled_w.index[i - 1]
        w_month  = scaled_w.loc[month_end]
        day_mask = (daily_exc.index > prev_end) & (daily_exc.index <= month_end)
        days_ret = daily_exc.loc[day_mask, [c for c in w_month.index if c in daily_exc.columns]]
        if days_ret.empty:
            continue

        assets_m = days_ret.columns.tolist()
        w_arr    = w_month.reindex(assets_m).fillna(0.0).values
        active   = np.ones(len(assets_m), dtype=bool)
        cum_ret  = np.zeros(len(assets_m))
        daily_pnl_total = 0.0
        stop_turnover   = 0.0

        for _, day_rets in days_ret.iterrows():
            dr = day_rets.values
            for j in range(len(assets_m)):
                if not active[j] or w_arr[j] == 0.0:
                    continue
                cum_ret[j] += dr[j]
                if np.sign(w_arr[j]) * cum_ret[j] < -stop_pct:
                    daily_pnl_total += w_arr[j] * dr[j]
                    stop_turnover   += abs(w_arr[j]) * COST_RT / 2.0
                    active[j]        = False
                    continue
                daily_pnl_total += w_arr[j] * dr[j]

        prev_w_arr   = prev_scaled_w.reindex(assets_m).fillna(0.0).values
        reb_turnover = float(np.abs(w_arr - prev_w_arr).sum()) * COST_RT / 2.0
        monthly_returns[month_end] = daily_pnl_total - reb_turnover - stop_turnover
        prev_scaled_w = w_month

    return pd.Series(monthly_returns).sort_index().dropna()


# ──────────────────────────────────────────────────────────────────────────────
# Statistics helpers
# ──────────────────────────────────────────────────────────────────────────────
def _sharpe(r: pd.Series, ann: int = ANN_M) -> float:
    s = r.std(ddof=1)
    return float(r.mean() / s * np.sqrt(ann)) if s > 0 else np.nan


def _max_dd(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def _ann_ret(r: pd.Series, ann: int = ANN_M) -> float:
    return float(r.mean() * ann)


def _ann_vol(r: pd.Series, ann: int = ANN_M) -> float:
    return float(r.std(ddof=1) * np.sqrt(ann))


def _crash_stats(r: pd.Series) -> dict:
    out = {}
    for name, (s, e) in CRASH_PERIODS.items():
        sub = r.loc[s:e]
        if len(sub) < 2:
            out[name] = {"note": "insufficient data"}
            continue
        eq = (1 + sub).cumprod()
        out[name] = {
            "sharpe":  round(_sharpe(sub), 2),
            "max_dd":  round(_max_dd(sub), 4),
            "cum_ret": round(float(eq.iloc[-1] - 1.0), 4),
        }
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Fix 3 — Newey-West HAC OLS
# ──────────────────────────────────────────────────────────────────────────────
def _ols_hac(y: pd.Series, factor_ret: pd.DataFrame, maxlags: int = 6) -> dict:
    """
    Fix 3: OLS with Newey-West HAC standard errors (statsmodels).
    Regress excess strategy returns on SPY and AGG excess factor returns.
    Returns alpha_ann, alpha_t (HAC), beta_SPY, beta_AGG, r2, resid_sharpe.
    """
    idx = y.index.intersection(factor_ret.index)
    if len(idx) < 12:
        return {}
    yv   = y.loc[idx].values.astype(float)
    fcols = [c for c in ["SPY", "AGG"] if c in factor_ret.columns]
    Xv   = factor_ret.loc[idx, fcols].values.astype(float)
    X    = sm.add_constant(Xv, prepend=False)   # intercept last column

    try:
        res = sm.OLS(yv, X).fit(cov_type='HAC',
                                 cov_kwds={'maxlags': maxlags, 'use_correction': True})
    except Exception as exc:
        log.warning(f"HAC OLS failed ({exc}), falling back to OLS.")
        res = sm.OLS(yv, X).fit()

    alpha_m  = float(res.params[-1])
    alpha_t  = float(res.tvalues[-1])
    resid    = res.resid
    resid_s  = float(alpha_m / resid.std(ddof=1) * np.sqrt(ANN_M)) \
               if resid.std(ddof=1) > 0 else np.nan

    out = {
        "alpha_ann":    round(alpha_m * ANN_M, 4),
        "alpha_t_hac":  round(alpha_t, 2),
        "r2":           round(float(res.rsquared), 4),
        "resid_sharpe": round(resid_s, 3),
    }
    for i, f in enumerate(fcols):
        out[f"beta_{f}"] = round(float(res.params[i]), 3)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Fix 4 — TSMOM diagnostics
# ──────────────────────────────────────────────────────────────────────────────
def _directional_accuracy(signal_w: pd.DataFrame,
                           fwd_returns: pd.DataFrame) -> float:
    """
    Fraction of (asset, month) pairs where sign(weight) == sign(forward return).
    Gate: >= 53%.
    """
    pairs = []
    idx = signal_w.index.intersection(fwd_returns.index)
    for col in signal_w.columns:
        if col not in fwd_returns.columns:
            continue
        w = signal_w[col].loc[idx]
        f = fwd_returns[col].loc[idx]
        mask = (w != 0) & f.notna()
        correct = (np.sign(w[mask]) == np.sign(f[mask])).sum()
        total   = mask.sum()
        if total > 0:
            pairs.append((int(correct), int(total)))
    if not pairs:
        return np.nan
    total_correct = sum(c for c, _ in pairs)
    total_obs     = sum(t for _, t in pairs)
    return total_correct / total_obs if total_obs > 0 else np.nan


def _quintile_analysis(signal_w: pd.DataFrame,
                        fwd_returns: pd.DataFrame) -> dict:
    """
    Stack all (signal, forward_return) pairs → sort by signal into 5 quintiles
    → compute mean forward return per quintile.
    Monotone increasing = expected TSMOM payoff.
    """
    idx = signal_w.index.intersection(fwd_returns.index)
    records = []
    for col in signal_w.columns:
        if col not in fwd_returns.columns:
            continue
        w = signal_w[col].loc[idx]
        f = fwd_returns[col].loc[idx]
        mask = w.notna() & f.notna()
        records.extend(zip(w[mask].values, f[mask].values))

    if len(records) < 50:
        return {"note": "insufficient obs"}

    df = pd.DataFrame(records, columns=["signal", "fwd_ret"])
    df["quintile"] = pd.qcut(df["signal"], 5, labels=False, duplicates="drop")
    q_means = df.groupby("quintile")["fwd_ret"].mean()

    # Monotonicity: count adjacent pairs where Q[k+1] > Q[k]
    vals = q_means.values
    mono_pairs = sum(1 for a, b in zip(vals, vals[1:]) if b > a)
    q1_q5_spread = float(vals[-1] - vals[0]) if len(vals) == 5 else np.nan

    return {
        "quintile_means":  {int(k): round(float(v), 5) for k, v in q_means.items()},
        "monotone_pairs":  int(mono_pairs),
        "max_mono_pairs":  int(len(vals) - 1),
        "q1_q5_spread":    round(q1_q5_spread, 5),
        "monotone_frac":   round(mono_pairs / max(len(vals) - 1, 1), 2),
    }


def _convexity_test(strategy_ret: pd.Series, px_daily: pd.DataFrame,
                    maxlags: int = 6) -> dict:
    """
    Fix 4c: Convexity test — regress monthly strategy returns on |SPY_monthly_return|.
    Positive coefficient = trend-following payoff profile (profits in large moves).
    Uses HAC SE.
    """
    px_m   = px_daily.resample("ME").last()
    spy_ret = np.log(px_m["SPY"] / px_m["SPY"].shift(1)).dropna() if "SPY" in px_m else None
    if spy_ret is None:
        return {"note": "SPY not available"}

    idx = strategy_ret.index.intersection(spy_ret.index)
    if len(idx) < 12:
        return {"note": "insufficient obs"}

    y = strategy_ret.loc[idx].values.astype(float)
    x = spy_ret.loc[idx].abs().values.astype(float)
    X = sm.add_constant(x, prepend=False)

    try:
        res = sm.OLS(y, X).fit(cov_type='HAC',
                                cov_kwds={'maxlags': maxlags, 'use_correction': True})
        coef  = float(res.params[0])
        t_val = float(res.tvalues[0])
    except Exception as exc:
        log.warning(f"Convexity HAC failed ({exc}).")
        return {"note": str(exc)}

    return {
        "convexity_coef":  round(coef, 4),
        "convexity_t_hac": round(t_val, 2),
        "convexity_pass":  bool(coef > 0 and t_val > 1.64),  # one-sided 5%
    }


# ──────────────────────────────────────────────────────────────────────────────
# Fix 5 — approx_multi_test_penalty (renamed from DSR)
# ──────────────────────────────────────────────────────────────────────────────
def _approx_multi_test_penalty(r: pd.Series, n_tests: int) -> dict:
    """
    Approximate multiple-testing penalty following Bailey & López de Prado (2014).

    NOTE: This is a simplified approximation, not the full Deflated Sharpe Ratio
    (DSR). The BLP formula uses an expected maximum SR benchmark (SR*) derived
    from n_tests independent trials. It does NOT account for: (a) auto-correlation
    in the strategy returns used to estimate SR, (b) correlation across the n_tests
    strategies themselves (treated as independent here), or (c) selection bias in
    which strategies are even presented for testing.

    Interpretation: p-value < 0.05 means the observed SR is statistically
    distinguishable from the maximum SR expected by chance across n_tests tests.
    With n_tests=64, the benchmark SR* is ~0.147 (monthly units); strategies
    with annualised SR < ~0.9 will typically fail this gate.

    Gate: p < 0.05 (observed SR significantly exceeds expected data-mining max).
    """
    T  = len(r)
    sr = _sharpe(r)
    if T < 2 or not np.isfinite(sr):
        return {"n_tests": n_tests, "amtp_pvalue": None, "amtp_pass": False}

    sk = float(r.skew())
    ku = float(r.kurtosis() + 3.0)
    sr_m = sr / np.sqrt(ANN_M)

    euler_gamma = 0.5772156649
    z = ((1 - euler_gamma) * stats.norm.ppf(1 - 1 / n_tests)
         + euler_gamma     * stats.norm.ppf(1 - 1 / (n_tests * np.e)))
    sr_star_m   = z / np.sqrt(T - 1)
    denom_inner = (1 - sk * sr_m + (ku - 1) / 4.0 * sr_m ** 2) / (T - 1)

    if denom_inner <= 0:
        return {"n_tests": n_tests, "amtp_pvalue": None, "amtp_pass": False}

    pval = float(stats.norm.sf((sr_m - sr_star_m) / np.sqrt(denom_inner)))
    return {
        "n_tests":    n_tests,
        "amtp_pvalue": round(pval, 4),
        "amtp_pass":   bool(pval < 0.05),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Full stats (all fixes)
# ──────────────────────────────────────────────────────────────────────────────
def full_stats_corrected(r: pd.Series,
                          factor_ret: pd.DataFrame,
                          px_daily: pd.DataFrame,
                          signal_w: pd.DataFrame,
                          fwd_returns: pd.DataFrame,
                          n_tests: int) -> dict:
    ols    = _ols_hac(r, factor_ret)
    amtp   = _approx_multi_test_penalty(r, n_tests)
    crash  = _crash_stats(r)

    # Fix 4
    dir_acc = _directional_accuracy(signal_w, fwd_returns)
    quint   = _quintile_analysis(signal_w, fwd_returns)
    convex  = _convexity_test(r, px_daily)

    return {
        "sharpe":       round(_sharpe(r), 3),
        "max_dd":       round(_max_dd(r), 4),
        "ann_ret":      round(_ann_ret(r), 4),
        "ann_vol":      round(_ann_vol(r), 4),
        "n_months":     int(len(r)),
        **ols,
        "amtp":         amtp,
        "crashes":      crash,
        "directional_accuracy": round(dir_acc, 4) if np.isfinite(dir_acc) else None,
        "quintile":     quint,
        "convexity":    convex,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Summary builder
# ──────────────────────────────────────────────────────────────────────────────
def _fmt(x, fmt=".3f", pct=False) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return f"{x*100:{fmt}}%" if pct else f"{x:{fmt}}"


def _ok(b: bool) -> str:
    return "✓" if b else "✗"


def build_summary(orig: dict, corr: dict, s: dict) -> str:
    lines = []
    lines.append("## Methodology Audit: MH+B — Original vs Corrected (All 5 Fixes)")
    lines.append("")
    lines.append("**Fixes applied simultaneously:**")
    lines.append("- Fix 1: Daily vol targeting (63-day daily P&L rolling vol × √252)")
    lines.append("- Fix 2: Excess returns over RF (FRED DTB3 3-month T-bill)")
    lines.append("- Fix 3: Newey-West HAC SE (statsmodels, maxlags=6)")
    lines.append("- Fix 4: TSMOM diagnostics (directional accuracy, quintile, convexity)")
    lines.append("- Fix 5: DSR renamed → `approx_multi_test_penalty` (simplified BLP approximation)")
    lines.append("")

    lines.append("### 1. Headline metrics comparison")
    lines.append("")
    lines.append("| Metric            | Original MH+B | Corrected MH+B | Change    |")
    lines.append("|-------------------|---------------|----------------|-----------|")

    def delta(a, b, pct=False):
        if a is None or b is None:
            return "n/a"
        d = b - a
        return f"{d*100:+.1f}pp" if pct else f"{d:+.3f}"

    corr_sh  = corr.get("sharpe")
    corr_ret = corr.get("ann_ret")
    corr_vol = corr.get("ann_vol")
    corr_dd  = corr.get("max_dd")
    corr_alp = corr.get("alpha_ann")
    corr_t   = corr.get("alpha_t_hac")
    corr_rs  = corr.get("resid_sharpe")
    corr_ec  = corr.get("crashes", {}).get("EuroCrisis", {}).get("max_dd")
    corr_cov = corr.get("crashes", {}).get("COVID_2020", {}).get("max_dd")
    corr_p   = corr.get("amtp", {}).get("amtp_pvalue")

    rows = [
        ("Sharpe",         orig["sharpe"],        corr_sh,  False),
        ("Ann ret",        orig["ann_ret"],        corr_ret, True),
        ("Ann vol",        orig["ann_vol"],        corr_vol, True),
        ("MaxDD",          orig["max_dd"],         corr_dd,  True),
        ("Alpha (ann)",    orig["alpha_ann"],       corr_alp, True),
        ("Alpha t-stat",   orig["alpha_t"],         corr_t,   False),
        ("Resid Sharpe",   orig["resid_sharpe"],   corr_rs,  False),
        ("EuroCrisis MaxDD", orig["eurocrisis_dd"], corr_ec, True),
        ("COVID MaxDD",    orig.get("covid_dd"),   corr_cov, True),
        ("AMTP p-value",   orig["dsr_pvalue"],     corr_p,   False),
    ]
    for label, o, c, is_pct in rows:
        o_s = _fmt(o, ".3f", pct=is_pct) if o is not None else "n/a"
        c_s = _fmt(c, ".3f", pct=is_pct) if c is not None else "n/a"
        d_s = delta(o, c, pct=is_pct)
        lines.append(f"| {label:<17} | {o_s:<13} | {c_s:<14} | {d_s:<9} |")
    lines.append("")

    lines.append("### 2. Fix 4 — TSMOM Diagnostics")
    da = s.get("directional_accuracy")
    lines.append(f"- **Directional accuracy**: {_fmt(da, '.1f', pct=True)}  "
                 f"(gate ≥53%: {_ok(da >= 0.53 if da else False)})")
    lines.append("")

    q = s.get("quintile", {})
    if "quintile_means" in q:
        lines.append("- **Quintile analysis** (Q1=lowest signal → Q5=highest):")
        for k, v in q["quintile_means"].items():
            lines.append(f"  - Q{k+1}: {v*100:+.3f}% avg fwd return")
        lines.append(f"  - Monotone adjacent pairs: {q['monotone_pairs']}/{q['max_mono_pairs']} "
                     f"({q['monotone_frac']*100:.0f}%)")
        lines.append(f"  - Q5-Q1 spread: {_fmt(q['q1_q5_spread'], '.3f', pct=True)}")
    lines.append("")

    cx = s.get("convexity", {})
    if "convexity_coef" in cx:
        lines.append(f"- **Convexity test** (coef on |SPY_ret|): "
                     f"β={cx['convexity_coef']:.4f}  t(HAC)={cx['convexity_t_hac']:.2f}  "
                     f"Pass (β>0, t>1.64): {_ok(cx['convexity_pass'])}")
    lines.append("")

    lines.append("### 3. Fix 5 — approx_multi_test_penalty documentation")
    amtp = s.get("amtp", {})
    lines.append(f"- n_tests: {amtp.get('n_tests', N_TESTS)}")
    lines.append(f"- AMTP p-value: {_fmt(amtp.get('amtp_pvalue'), '.4f')}  "
                 f"({'PASS < 0.05' if amtp.get('amtp_pass') else 'FAIL ≥ 0.05'})")
    lines.append("- **Limitation**: BLP approximation assumes independent tests and "
                 "i.i.d. strategy returns. Serial correlation in TSMOM returns and "
                 "correlation across the 64 tested variants means this p-value "
                 "understates true significance. Treat as conservative lower bound.")
    lines.append("")

    lines.append("### 4. Crash period breakdown (corrected MH+B)")
    lines.append("| Period       | Sharpe | MaxDD  | CumRet |")
    lines.append("|--------------|--------|--------|--------|")
    for pname in ["GFC_2008", "EuroCrisis", "COVID_2020", "Inflation22"]:
        c = s.get("crashes", {}).get(pname, {})
        if "max_dd" in c:
            lines.append(f"| {pname:<12} | {_fmt(c['sharpe'],'+.2f'):>6} | "
                         f"{_fmt(c['max_dd'],'.1f',pct=True):>6} | "
                         f"{_fmt(c['cum_ret'],'.1f',pct=True):>6} |")
    lines.append("")

    lines.append("### 5. Propfirm gate status (corrected metrics)")
    gates = {
        "MaxDD > -10%":           corr_dd is not None and corr_dd > -0.10,
        "COVID MaxDD > -5%":      corr_cov is not None and corr_cov > -0.05,
        "Resid Sharpe > 0.40":    corr_rs is not None and corr_rs > 0.40,
        "Dir accuracy ≥ 53%":     da is not None and da >= 0.53,
        "Convexity β > 0 (t>1.64)": cx.get("convexity_pass", False),
        "AMTP p < 0.05 (n=64)":   amtp.get("amtp_pass", False),
    }
    for g, passed in gates.items():
        lines.append(f"- {_ok(passed)} {g}")
    lines.append("")

    n_pass = sum(gates.values())
    propfirm_core = gates["MaxDD > -10%"] and gates["COVID MaxDD > -5%"] and gates["Resid Sharpe > 0.40"]
    if propfirm_core:
        verdict = "**PASS_PROPFIRM** — corrected MH+B clears all core drawdown and alpha gates."
    elif corr_dd is not None and corr_dd > -0.15:
        verdict = f"**PASS_RESEARCH_ONLY** — MaxDD {_fmt(corr_dd,'.1f',pct=True)} still outside propfirm -10% gate."
    else:
        verdict = f"**FAIL** — corrected metrics degrade below research threshold."

    lines.append("### 6. Verdict")
    lines.append(verdict)
    lines.append(f"Gates passed: {n_pass}/{len(gates)}")
    lines.append("")
    lines.append("### 7. n_tests counter: 64 (no new tests in this audit)")
    lines.append("### 8. Files written")
    lines.append("- methodology_audit.py (this script)")
    lines.append("- methodology_audit_summary.md (this summary)")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main() -> dict:
    log.info("=== Methodology Audit — MH+B with 5 corrected fixes ===")

    print("\n" + "─" * 72)
    print("FIX 2 — Fetching FRED DTB3 risk-free rate")
    print("─" * 72)
    px_univ, px_beta, factor_exc, rf_daily = fetch_data()
    log.info(f"Universe: {list(px_univ.columns)}")

    print("\n" + "─" * 72)
    print("SIGNAL — Combined 1M+3M+12M excess returns")
    print("─" * 72)
    net_raw, weights_m = build_mh_monthly_excess(px_univ, rf_daily)
    log.info(f"Raw excess returns: {len(net_raw)} months, "
             f"Sharpe={_sharpe(net_raw):.3f}, MaxDD={_max_dd(net_raw)*100:.1f}%")

    # Forward returns for diagnostics (excess, unshifted)
    px_m     = px_univ.resample("ME").last()
    logret_m = np.log(px_m / px_m.shift(1))
    rf_m     = _rf_daily_to_monthly(rf_daily, logret_m.index)
    exc_m    = logret_m.subtract(rf_m, axis=0)
    fwd_ret  = exc_m.shift(-1).loc[weights_m.index]   # aligned forward returns

    print("\n" + "─" * 72)
    print("FIX 1 — Daily vol targeting (63d rolling daily P&L vol)")
    print("─" * 72)
    net_vt_daily = vol_target_daily(px_univ, weights_m, net_raw, rf_daily,
                                     target=0.10, lb_days=63, cap=2.0)
    log.info(f"Daily-VT: {len(net_vt_daily)} months, "
             f"Sharpe={_sharpe(net_vt_daily):.3f}, MaxDD={_max_dd(net_vt_daily)*100:.1f}%")

    print("\n" + "─" * 72)
    print("MH+B — Multi-horizon + Overlay B (daily VT + excess returns)")
    print("─" * 72)
    net_b = overlay_b_daily_vt(px_univ, weights_m, net_raw, rf_daily,
                                stop_pct=0.05, vt_target=0.10,
                                vt_lb_days=63, vt_cap=2.0)
    log.info(f"MH+B corrected: {len(net_b)} months, "
             f"Sharpe={_sharpe(net_b):.3f}, MaxDD={_max_dd(net_b)*100:.1f}%")

    print("\n" + "─" * 72)
    print("FIX 3 — HAC OLS  |  FIX 4 — TSMOM diagnostics  |  FIX 5 — AMTP")
    print("─" * 72)
    stats_b = full_stats_corrected(net_b, factor_exc, px_univ,
                                    weights_m, fwd_ret, N_TESTS)

    # Print corrected stats
    print(f"\n  [MH+B CORRECTED]")
    print(f"    Sharpe={stats_b['sharpe']:+.3f}  MaxDD={stats_b['max_dd']*100:+.1f}%  "
          f"AnnRet={stats_b['ann_ret']*100:+.1f}%  AnnVol={stats_b['ann_vol']*100:+.1f}%")
    print(f"    alpha={stats_b.get('alpha_ann',0)*100:+.2f}% "
          f"(t_HAC={stats_b.get('alpha_t_hac',0):+.2f})  "
          f"beta_SPY={stats_b.get('beta_SPY',0):+.3f}  R²={stats_b.get('r2',0)*100:.1f}%  "
          f"residSR={stats_b.get('resid_sharpe',0):+.3f}")

    amtp = stats_b["amtp"]
    p = amtp["amtp_pvalue"]
    print(f"    AMTP(n={amtp['n_tests']}): p={p:.4f}  "
          f"{'✓ PASS' if amtp['amtp_pass'] else '✗ FAIL'}")

    da = stats_b.get("directional_accuracy")
    print(f"    Directional accuracy: {da*100:.1f}%  "
          f"{'✓ ≥53%' if da >= 0.53 else '✗ <53%'}")

    cx = stats_b.get("convexity", {})
    if "convexity_coef" in cx:
        print(f"    Convexity: β={cx['convexity_coef']:.4f}  t={cx['convexity_t_hac']:.2f}  "
              f"{'✓' if cx['convexity_pass'] else '✗'}")

    for crash_name, c in stats_b["crashes"].items():
        if "max_dd" in c:
            print(f"    {crash_name:<16} MaxDD={c['max_dd']*100:+.1f}%  "
                  f"Sharpe={c['sharpe']:+.2f}  CumRet={c['cum_ret']*100:+.1f}%")

    # Build and print summary
    summary = build_summary(ORIGINAL_MHB, stats_b, stats_b)
    print("\n\n" + "=" * 72)
    print(summary)
    print("=" * 72)

    SUMMARY_MD.write_text(summary)
    log.info(f"Saved → {SUMMARY_MD}")

    return {"corrected_mhb": stats_b}


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("methodology_audit run failed")
        sys.exit(1)
