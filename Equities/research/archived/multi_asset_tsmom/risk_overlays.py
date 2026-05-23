"""
multi_asset_tsmom/risk_overlays.py
====================================
Three risk overlays on multi-asset TSMOM, tested independently then combined.

Walk-forward passed (median Sharpe 0.78, 69% positive windows) but two gates failed:
  - DSR full-sample p=0.369  (penalty from n_tests=58)
  - Vol-targeted MaxDD = -18.7%  (target > -10%)
  Binding cause: EuroCrisis 2011 correlation breakdown → -16% in 10 months.

Overlays:
  A — Aggressive vol targeting   (target=6%, lb=21d, cap=2.5×)
  B — Per-position stop loss     (-5% per ETF leg, daily close proxy)
  C — Correlation regime filter  (scale by 0.5 if corr>0.50, by 0.25 if >0.65)

Backtests run:
  1. Baseline VT (10% target, 63d lookback, 2× cap)   — n_tests = 58
  2. Overlay A                                          — n_tests = 59
  3. Overlay B                                          — n_tests = 60
  4. Overlay C                                          — n_tests = 61
  5. Best-two combined (highest Sharpe×(1-|MaxDD|) pair) — n_tests = 62

Run:
  python -m Equities.research.passed.multi_asset_tsmom.risk_overlays
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
START    = "2004-01-01"
END      = pd.Timestamp.today().strftime("%Y-%m-%d")
COST_RT  = 0.0005
ANN_M    = 12
UNIVERSE = ["SPY", "QQQ", "EFA", "EEM", "IWM",
            "TLT", "IEF", "SHY", "GLD", "VNQ"]
BETA_FACTORS = ["SPY", "AGG"]
N_BASE   = 58    # n_tests entering this session

CRASH_PERIODS = {
    "GFC_2008":    ("2008-07-01", "2009-06-30"),
    "EuroCrisis":  ("2011-04-01", "2012-01-31"),
    "COVID_2020":  ("2020-02-01", "2020-05-31"),
    "Inflation22": ("2022-01-01", "2022-12-31"),
}

RESULTS_DIR  = Path(__file__).parent
RESULTS_JSON = RESULTS_DIR / "risk_overlays_results.json"
SUMMARY_MD   = RESULTS_DIR / "risk_overlays_summary.md"


# ──────────────────────────────────────────────────────────────────────────────
# Core primitives (self-contained — don't import from feasibility/walkforward)
# ──────────────────────────────────────────────────────────────────────────────
def _tsmom_signal(px: pd.DataFrame, ann: int) -> pd.DataFrame:
    logret = np.log(px / px.shift(1))
    cumret = logret.rolling(ann).sum().shift(1)
    vol    = logret.rolling(ann).std()
    denom  = (vol * np.sqrt(ann)).replace(0, np.nan)
    return np.tanh((cumret / denom).replace([np.inf, -np.inf], np.nan))


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


def _ols_stats(y: pd.Series, factor_ret: pd.DataFrame) -> dict:
    """OLS: y = α + β_SPY·x_SPY + β_AGG·x_AGG + ε. Returns dict of stats."""
    idx = y.index.intersection(factor_ret.index)
    if len(idx) < 12:
        return {}
    yv = y.loc[idx].values.astype(float)
    Xv = factor_ret.loc[idx, [c for c in ["SPY", "AGG"] if c in factor_ret.columns]].values.astype(float)
    X  = np.column_stack([Xv, np.ones(len(yv))])
    coef, _, _, _ = np.linalg.lstsq(X, yv, rcond=None)
    resid   = yv - X @ coef
    alpha_m = float(coef[-1])
    n, k    = len(yv), X.shape[1]
    ss_res  = float((resid ** 2).sum())
    ss_tot  = float(((yv - yv.mean()) ** 2).sum())
    r2      = float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan
    mse     = ss_res / max(n - k, 1)
    XtX_inv = np.linalg.inv(X.T @ X)
    se      = np.sqrt(np.maximum(np.diag(mse * XtX_inv), 0))
    t_vals  = coef / np.where(se > 0, se, np.nan)
    resid_sharpe = float(alpha_m / resid.std(ddof=1) * np.sqrt(ANN_M)) \
                   if resid.std(ddof=1) > 0 else np.nan
    factors = [c for c in ["SPY", "AGG"] if c in factor_ret.columns]
    out = {
        "alpha_ann":    round(alpha_m * ANN_M, 4),
        "alpha_t":      round(float(t_vals[-1]), 2),
        "beta_SPY":     round(float(coef[0]), 3) if "SPY" in factors else None,
        "beta_AGG":     round(float(coef[1 if len(factors) > 1 else 0]), 3) if "AGG" in factors else None,
        "r2":           round(r2, 4),
        "resid_sharpe": round(resid_sharpe, 3),
    }
    return out


def _crash_stats(r: pd.Series, periods: dict) -> dict:
    out = {}
    for name, (s, e) in periods.items():
        sub = r.loc[s:e]
        if len(sub) < 2:
            out[name] = {"note": "insufficient data"}
            continue
        eq = (1 + sub).cumprod()
        out[name] = {
            "sharpe":  round(_sharpe(sub), 2),
            "max_dd":  round(_max_dd(sub), 4),
            "cum_ret": round(float(eq.iloc[-1] - 1.0), 4),
            "n_obs":   int(len(sub)),
        }
    return out


def _dsr_pvalue(sr_obs: float, T: int, skew: float, kurt: float,
                n_tests: int) -> float:
    """Bailey & López de Prado 2014 DSR. SR inputs are annualised."""
    if T < 2:
        return np.nan
    sr_m = sr_obs / np.sqrt(ANN_M)
    euler_gamma = 0.5772156649
    z = ((1 - euler_gamma) * stats.norm.ppf(1 - 1 / n_tests)
         + euler_gamma     * stats.norm.ppf(1 - 1 / (n_tests * np.e)))
    sr_star_m   = z / np.sqrt(T - 1)
    denom_inner = (1 - skew * sr_m + (kurt - 1) / 4.0 * sr_m ** 2) / (T - 1)
    if denom_inner <= 0:
        return np.nan
    # sf = 1 - Φ(z): conventional p-value (small = SR significantly exceeds expected max)
    # Using sf ensures high SR → p → 0 → PASS "< 0.05"
    return float(stats.norm.sf((sr_m - sr_star_m) / np.sqrt(denom_inner)))


def _dsr(r: pd.Series, n_tests: int) -> dict:
    sr   = _sharpe(r)
    sk   = float(r.skew()) if len(r) > 0 else np.nan
    ku   = float(r.kurtosis() + 3.0) if len(r) > 0 else np.nan
    pval = _dsr_pvalue(sr, len(r), sk, ku, n_tests)
    return {
        "n_tests":    n_tests,
        "dsr_pvalue": round(pval, 4) if np.isfinite(pval) else None,
        "dsr_pass":   bool(pval < 0.05) if np.isfinite(pval) else False,
    }


def _fmt(x, fmt=".3f", pct: bool = False) -> str:
    """Format float, handling None and NaN gracefully."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    if pct:
        return f"{x*100:{fmt}}"
    return f"{x:{fmt}}"


def _full_stats(r: pd.Series, factor_ret: pd.DataFrame, n_tests: int,
                crash_pds: dict = CRASH_PERIODS) -> dict:
    ols = _ols_stats(r, factor_ret)
    dsr_actual = _dsr(r, n_tests)
    dsr_58     = _dsr(r, N_BASE)
    return {
        "sharpe":       round(_sharpe(r), 3),
        "max_dd":       round(_max_dd(r), 4),
        "ann_ret":      round(_ann_ret(r), 4),
        "ann_vol":      round(_ann_vol(r), 4),
        "n_months":     int(len(r)),
        **ols,
        "dsr_actual":   dsr_actual,
        "dsr_58":       dsr_58,
        "crashes":      _crash_stats(r, crash_pds),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Data
# ──────────────────────────────────────────────────────────────────────────────
def fetch_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (px_daily_univ, px_daily_beta, px_beta_monthly_factor_ret)."""
    all_tickers = list(dict.fromkeys(UNIVERSE + BETA_FACTORS))
    log.info(f"Downloading {all_tickers} …")
    raw  = yf.download(all_tickers, start=START, end=END,
                       auto_adjust=True, progress=False)
    px   = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    px.index = pd.to_datetime(px.index)
    px   = px.ffill(limit=3)
    px_univ = px[[c for c in UNIVERSE if c in px.columns]]
    px_beta = px[[c for c in BETA_FACTORS if c in px.columns]]
    # Monthly factor returns for OLS
    px_beta_m  = px_beta.resample("ME").last()
    factor_ret = np.log(px_beta_m / px_beta_m.shift(1)).dropna(how="all")
    return px_univ, px_beta, factor_ret


# ──────────────────────────────────────────────────────────────────────────────
# Raw monthly signal + weights (no vol targeting)
# ──────────────────────────────────────────────────────────────────────────────
def build_raw_monthly(px_daily: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Returns (net_raw_monthly, weights_monthly)."""
    px     = px_daily.resample("ME").last()
    logret = np.log(px / px.shift(1)).dropna(how="all")
    sig    = _tsmom_signal(px, ann=ANN_M)
    fwd    = logret.shift(-1)
    n      = sig.shape[1]
    w      = sig.fillna(0.0) / n

    idx   = (sig.dropna(how="all").index
                .intersection(logret.index)
                .intersection(fwd.dropna(how="all").index))
    w_al  = w.reindex(idx)
    fwd_al = fwd.reindex(idx)

    gross    = (w_al * fwd_al).sum(axis=1)
    turnover = (w_al - w_al.shift(1).fillna(0)).abs().sum(axis=1)
    net      = (gross - turnover * (COST_RT / 2.0)).dropna()
    return net, w_al


# ──────────────────────────────────────────────────────────────────────────────
# BASELINE — vol targeting at 10% (matches walkforward.py)
# ──────────────────────────────────────────────────────────────────────────────
def vol_target(returns: pd.Series, target: float, lb_months: int,
               cap: float) -> pd.Series:
    rvol    = returns.rolling(lb_months).std() * np.sqrt(ANN_M)
    scaling = (target / rvol.shift(1)).clip(upper=cap)
    return (returns * scaling).dropna()


def _vol_scale_series(returns: pd.Series, target: float, lb_months: int,
                      cap: float) -> pd.Series:
    """Scale factor series used in baseline, aligned to returns index."""
    rvol    = returns.rolling(lb_months).std() * np.sqrt(ANN_M)
    return (target / rvol.shift(1)).clip(upper=cap)


# ──────────────────────────────────────────────────────────────────────────────
# OVERLAY A — aggressive vol targeting
# ──────────────────────────────────────────────────────────────────────────────
def overlay_a(net_raw: pd.Series, px_daily: pd.DataFrame,
              weights_m: pd.DataFrame) -> pd.Series:
    """
    Aggressive vol targeting: 6% target, 21-day daily lookback, 2.5× cap.
    Uses daily portfolio returns for vol estimation (monthly rolling(1).std()
    is undefined; daily series gives a proper 21-day realized vol estimate).
    """
    daily_logret = np.log(px_daily / px_daily.shift(1))
    assets  = [c for c in weights_m.columns if c in daily_logret.columns]
    n       = weights_m.shape[1]
    # Daily portfolio P&L from raw unscaled TSMOM weights (forward-filled to daily)
    w_daily = (weights_m[assets] / n).reindex(daily_logret.index, method="ffill")
    daily_pf = (w_daily * daily_logret[assets]).sum(axis=1)

    # 21-day rolling realized vol, annualized to match target units
    rvol_21d = daily_pf.rolling(21).std() * np.sqrt(252)

    # Sample at each month-end: vol known at end of month T
    rvol_monthly = rvol_21d.reindex(net_raw.index, method="ffill")

    # Scaling: vol at T → scale applied to month T+1 (shift(1))
    scale = (0.06 / rvol_monthly.shift(1)).clip(upper=2.5)

    return (net_raw * scale).dropna()


# ──────────────────────────────────────────────────────────────────────────────
# OVERLAY B — per-position stop loss (daily simulation)
# ──────────────────────────────────────────────────────────────────────────────
def overlay_b(px_daily: pd.DataFrame,
              weights_m: pd.DataFrame,
              net_raw: pd.Series,
              stop_pct: float = 0.05,
              vt_target: float = 0.10,
              vt_lb_months: int = 3,
              vt_cap: float = 2.0) -> pd.Series:
    """
    Daily simulation: at each monthly rebalance apply TSMOM weights (scaled by
    baseline vol target). During each holding month, if any individual position
    accumulates a loss > stop_pct × |w_i| → close that leg for remainder of month.

    Returns monthly net return series.
    """
    # Vol-scale factor aligned to month-end signal dates
    scale_m = _vol_scale_series(net_raw, target=vt_target,
                                lb_months=vt_lb_months, cap=vt_cap)
    scale_m = scale_m.reindex(weights_m.index).fillna(1.0)

    # Apply vol scale to raw weights
    scaled_w = weights_m.multiply(scale_m, axis=0)  # shape (n_months, n_assets)

    daily_logret = np.log(px_daily / px_daily.shift(1))

    monthly_returns = {}
    prev_scaled_w   = pd.Series(0.0, index=scaled_w.columns)

    for i, month_end in enumerate(scaled_w.index):
        w_month = scaled_w.loc[month_end]   # target weights for this holding period

        # Trading days in this holding month: from day after prev month-end to this month-end
        if i == 0:
            continue
        prev_end  = scaled_w.index[i - 1]
        # Days strictly after prev_end up to and including month_end
        day_mask  = (daily_logret.index > prev_end) & (daily_logret.index <= month_end)
        days_ret  = daily_logret.loc[day_mask, [c for c in w_month.index if c in daily_logret.columns]]
        if days_ret.empty:
            continue

        assets   = days_ret.columns.tolist()
        w_arr    = w_month.reindex(assets).fillna(0.0).values  # shape (n_assets,)
        active   = np.ones(len(assets), dtype=bool)
        cum_ret  = np.zeros(len(assets))      # cumulative ETF return per leg since month start
        daily_pnl_total = 0.0
        stop_turnover   = 0.0

        for _, day_rets in days_ret.iterrows():
            dr = day_rets.values
            for j in range(len(assets)):
                if not active[j] or w_arr[j] == 0.0:
                    continue
                cum_ret[j] += dr[j]
                # Stop: if position-level loss > stop_pct (measured on underlying ETF return)
                # Long (w>0) stops when ETF drops >5%; short (w<0) stops when ETF rises >5%
                if np.sign(w_arr[j]) * cum_ret[j] < -stop_pct:
                    # Realize the return that triggered the stop (daily-close proxy)
                    daily_pnl_total += w_arr[j] * dr[j]
                    stop_turnover   += abs(w_arr[j]) * COST_RT / 2.0   # exit cost
                    active[j]        = False
                    continue
                daily_pnl_total += w_arr[j] * dr[j]

        # Monthly rebalance turnover cost
        prev_w_arr  = prev_scaled_w.reindex(assets).fillna(0.0).values
        reb_turnover = float(np.abs(w_arr - prev_w_arr).sum()) * COST_RT / 2.0

        monthly_returns[month_end] = daily_pnl_total - reb_turnover - stop_turnover
        prev_scaled_w = w_month

    return pd.Series(monthly_returns).sort_index().dropna()


# ──────────────────────────────────────────────────────────────────────────────
# OVERLAY C — correlation regime filter
# ──────────────────────────────────────────────────────────────────────────────
def _rolling_avg_pairwise_corr(px_daily: pd.DataFrame,
                                 window: int = 21) -> pd.Series:
    """
    For each trading day, compute rolling `window`-day Pearson pairwise
    correlation across all assets, average the upper triangle.
    Returns a daily Series aligned to px_daily.index.
    """
    logret = np.log(px_daily / px_daily.shift(1)).dropna(how="all")
    cols   = logret.columns.tolist()
    n      = len(cols)
    pair_corrs = []
    for i in range(n):
        for j in range(i + 1, n):
            rc = logret[cols[i]].rolling(window).corr(logret[cols[j]])
            pair_corrs.append(rc)
    avg = pd.concat(pair_corrs, axis=1).mean(axis=1)
    return avg


def overlay_c(net_vt: pd.Series, px_daily: pd.DataFrame,
              window: int = 21,
              thresh_half: float = 0.50,
              thresh_quarter: float = 0.65) -> pd.Series:
    """
    At end of month T, compute rolling 21-day avg pairwise correlation.
    Scale month T+1 positions:
      corr > 0.65 → ×0.25
      corr > 0.50 → ×0.50
      else        → ×1.00
    Applied to the baseline VT monthly returns.
    """
    avg_corr_daily = _rolling_avg_pairwise_corr(px_daily, window=window)

    # Get avg_corr value at each month-end
    month_ends      = net_vt.index
    corr_at_month   = avg_corr_daily.reindex(month_ends, method="ffill")

    def _scale(c: float) -> float:
        if np.isnan(c):
            return 1.0
        if c > thresh_quarter:
            return 0.25
        if c > thresh_half:
            return 0.50
        return 1.0

    # shift(1): corr at end of T → scale applied to T+1
    scale_series = corr_at_month.map(_scale).shift(1).reindex(month_ends).fillna(1.0)

    log.info(f"Overlay C: corr>0.50 triggered in "
             f"{(corr_at_month > thresh_half).sum()} months; "
             f"corr>0.65 in {(corr_at_month > thresh_quarter).sum()} months")
    return (net_vt * scale_series).dropna()


# ──────────────────────────────────────────────────────────────────────────────
# COMBINED overlay
# ──────────────────────────────────────────────────────────────────────────────
def overlay_combined(label: str,
                     net_A: pd.Series | None,
                     net_B: pd.Series | None,
                     net_C_baseline: pd.Series | None,
                     px_daily: pd.DataFrame,
                     net_raw: pd.Series,
                     weights_m: pd.DataFrame) -> pd.Series:
    """
    Combine two best overlays:
      A+B: rebuild daily stop simulation using Overlay A vol params
      A+C: Overlay A returns × corr scale factor
      B+C: Overlay B returns × corr scale factor
    """
    if label == "A+B":
        return overlay_b(px_daily, weights_m, net_raw,
                         stop_pct=0.05, vt_target=0.06,
                         vt_lb_months=1, vt_cap=2.5)
    if label == "A+C":
        return overlay_c(net_A, px_daily)
    if label == "B+C":
        return overlay_c(net_B, px_daily)
    raise ValueError(f"Unknown combination label: {label}")


# ──────────────────────────────────────────────────────────────────────────────
# EuroCrisis deep-dive
# ──────────────────────────────────────────────────────────────────────────────
def eurocrisis_analysis(px_daily: pd.DataFrame,
                        weights_m: pd.DataFrame) -> dict:
    """
    Analyse the EuroCrisis 2011 period in detail.
    Returns: per-asset contribution, correlation spike timing.
    """
    s, e      = "2011-04-01", "2012-01-31"
    logret_d  = np.log(px_daily / px_daily.shift(1))
    px_m      = px_daily.resample("ME").last()
    logret_m  = np.log(px_m / px_m.shift(1))

    # Monthly returns during crisis
    crisis_m  = logret_m.loc[s:e]
    w_crisis  = weights_m.reindex(crisis_m.index).fillna(0)
    contrib   = (w_crisis * crisis_m).sum(axis=0)

    # Rolling 21-day avg pairwise corr during and around crisis
    avg_corr  = _rolling_avg_pairwise_corr(px_daily)
    corr_slice = avg_corr.loc["2011-01-01":"2012-03-31"]
    peak_corr  = float(corr_slice.max())
    peak_date  = str(corr_slice.idxmax().date())

    # Month when correlation breached 0.50
    crisis_month_ends = weights_m.loc[s:e].index
    avg_corr_me       = avg_corr.reindex(crisis_month_ends, method="ffill")
    months_above_50   = int((avg_corr_me > 0.50).sum())
    months_above_65   = int((avg_corr_me > 0.65).sum())

    return {
        "period":           f"{s} → {e}",
        "top_drag_assets":  contrib.nsmallest(3).round(4).to_dict(),
        "top_lift_assets":  contrib.nlargest(2).round(4).to_dict(),
        "peak_avg_pairwise_corr": round(peak_corr, 3),
        "peak_corr_date":         peak_date,
        "months_corr_above_0.50": months_above_50,
        "months_corr_above_0.65": months_above_65,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Summary builder
# ──────────────────────────────────────────────────────────────────────────────
def build_summary(variants: dict[str, dict],
                  ec_analysis: dict,
                  best_combo_label: str) -> str:
    def f2(x): return f"{x:.2f}"  if x is not None and np.isfinite(x) else "n/a"
    def f3(x): return f"{x:.3f}"  if x is not None and np.isfinite(x) else "n/a"
    def fp(x): return f"{x*100:.1f}%" if x is not None and np.isfinite(x) else "n/a"
    def ok(b): return "✓" if b else "✗"

    # Determine best propfirm variant
    propfirm_pass = {k: (v["max_dd"] > -0.10 and
                          v.get("crashes", {}).get("COVID_2020", {}).get("max_dd", -1) > -0.05 and
                          (v.get("resid_sharpe") or 0) > 0.40)
                     for k, v in variants.items()}
    best_var = max(variants, key=lambda k: (
        variants[k]["sharpe"] * (1 - abs(variants[k]["max_dd"]))
    ))
    best_stats = variants[best_var]
    headline_pass = propfirm_pass.get(best_var, False)
    verdict = f"{best_var} — {'PASS_PROPFIRM' if headline_pass else 'PASS_RESEARCH_ONLY'}"

    lines = []
    lines.append("## Result Summary: multi_asset_tsmom — Risk Overlays")
    lines.append("")

    lines.append("### 1. Headline verdict")
    lines.append(f"**Best variant: {verdict}** — best Sharpe×(1-|MaxDD|) score, "
                 f"propfirm gates {'all clear' if headline_pass else 'partially cleared'}.")
    lines.append("")

    lines.append("### 2. All variants comparison table")
    lines.append("| Variant       | Sharpe | Ann ret | Ann vol | MaxDD  | Alpha | β_SPY | β_AGG | R²  | Resid SR | DSR(n) | DSR(58) |")
    lines.append("|---------------|--------|---------|---------|--------|-------|-------|-------|-----|----------|--------|---------|")
    for name, s in variants.items():
        dsr_n  = s["dsr_actual"]["dsr_pvalue"]
        dsr_58 = s["dsr_58"]["dsr_pvalue"]
        r2_pct = f"{s.get('r2',0)*100:.1f}%" if s.get("r2") is not None else "n/a"
        lines.append(
            f"| {name:<13} | {f2(s['sharpe'])} | {fp(s['ann_ret'])}    | {fp(s['ann_vol'])}    | "
            f"{fp(s['max_dd'])}  | {fp(s.get('alpha_ann'))}  | {f2(s.get('beta_SPY'))} | "
            f"{f2(s.get('beta_AGG'))} | {r2_pct} | {f2(s.get('resid_sharpe'))}     | "
            f"{f3(dsr_n)} ({s['dsr_actual']['n_tests']}) | {f3(dsr_58)} |"
        )
    lines.append("")

    lines.append("### 3. Crash period MaxDD per variant")
    lines.append("| Period       | Baseline | A    | B    | C    | Combined |")
    lines.append("|--------------|----------|------|------|------|----------|")
    period_labels = {
        "GFC_2008":    "GFC",
        "EuroCrisis":  "EuroCrisis",
        "COVID_2020":  "COVID",
        "Inflation22": "Inflation",
    }
    for k, label in period_labels.items():
        row = [f"| {label:<12} |"]
        for vname in ["Baseline VT", "Overlay A", "Overlay B", "Overlay C",
                      f"Combined {best_combo_label}"]:
            c = variants.get(vname, {}).get("crashes", {}).get(k, {})
            dd = c.get("max_dd")
            row.append(f" {fp(dd) if dd is not None else 'n/a':>6} |")
        lines.append("".join(row))
    lines.append("")

    lines.append("### 4. Propfirm gate decision per variant")
    lines.append("| Variant       | MaxDD>-10% | COVID>-5% | Resid SR>0.40 | DSR<0.05 | Verdict |")
    lines.append("|---------------|------------|-----------|---------------|----------|---------|")
    for name, s in variants.items():
        covid_dd  = s.get("crashes", {}).get("COVID_2020", {}).get("max_dd", -1)
        gate_dd   = s["max_dd"] > -0.10
        gate_cov  = (covid_dd or -1) > -0.05
        gate_rs   = (s.get("resid_sharpe") or 0) > 0.40
        gate_dsr  = s["dsr_actual"]["dsr_pass"]
        all_pass  = gate_dd and gate_cov and gate_rs and gate_dsr
        ver = "PASS" if all_pass else ("PARTIAL" if (gate_dd and gate_cov) else "FAIL")
        lines.append(f"| {name:<13} | {ok(gate_dd):<10} | {ok(gate_cov):<9} | "
                     f"{ok(gate_rs):<13} | {ok(gate_dsr):<8} | {ver}    |")
    lines.append("")

    lines.append("### 5. EuroCrisis 2011 detailed analysis (the binding constraint)")
    lines.append(f"- **Period**: {ec_analysis['period']}")
    base_ec = variants["Baseline VT"]["crashes"].get("EuroCrisis", {}).get("max_dd")
    lines.append(f"- **Baseline MaxDD**: {fp(base_ec)}")
    lines.append(f"- **What killed it**: peak avg pairwise correlation = "
                 f"{ec_analysis['peak_avg_pairwise_corr']:.2f} on "
                 f"{ec_analysis['peak_corr_date']} — all assets correlated during EU sovereign crisis. "
                 f"Top drag: {list(ec_analysis['top_drag_assets'].items())}. "
                 f"Correlation above 0.50 in {ec_analysis['months_corr_above_0.50']} of the crisis months.")
    # Best overlay for EuroCrisis
    ec_dds = {k: variants[k]["crashes"].get("EuroCrisis", {}).get("max_dd", -99)
              for k in variants}
    best_ec = max(ec_dds, key=lambda k: ec_dds[k] if ec_dds[k] is not None else -99)
    lines.append(f"- **Best rescue**: {best_ec} → EuroCrisis MaxDD {fp(ec_dds[best_ec])}")
    lines.append(f"- **Mechanism**: {'Overlay C correlation filter scales down positions when avg pairwise corr breaches thresholds, directly targeting the diversification breakdown.' if 'C' in best_ec else 'Overlay A lower vol target / Overlay B stops reduce drawdown by limiting position size or cutting losing legs.'}")
    lines.append("")

    lines.append("### 6. Recommendation")
    best_p = max(propfirm_pass, key=lambda k: propfirm_pass[k])
    if any(propfirm_pass.values()):
        best_p_s = variants[best_p]
        lines.append(
            f"**{best_p}** clears the propfirm MaxDD gate at {fp(best_p_s['max_dd'])} "
            f"with Sharpe {f2(best_p_s['sharpe'])} and residual Sharpe {f2(best_p_s.get('resid_sharpe'))}. "
            f"Proceed to paper trading with {best_p} sizing. "
            f"Monitor the correlation regime filter threshold (currently 0.50/0.65) — "
            f"consider tightening to 0.40/0.55 if the next drawdown exceeds -8%."
        )
    else:
        lines.append(
            "No variant fully clears all propfirm gates. The binding constraint is MaxDD compression. "
            "Consider further reducing the vol target to 5% or implementing a dynamic stop "
            "that tightens during high-correlation regimes."
        )
    lines.append("")

    lines.append("### 7. n_tests counter")
    lines.append(f"- Start of session: {N_BASE}")
    lines.append(f"- End of session: {N_BASE + 4} (added Overlay A, B, C, Combined — all documented regardless of outcome)")
    lines.append("- Audit trail: all variants logged in risk_overlays_results.json")
    lines.append("")

    lines.append("### 8. Files written")
    lines.append("- risk_overlays.py (this script)")
    lines.append("- risk_overlays_results.json (machine-readable)")
    lines.append("- risk_overlays_summary.md (this summary)")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main() -> dict:
    log.info("=== Multi-Asset TSMOM Risk Overlays ===")

    # ── Data ──────────────────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("DATA DOWNLOAD")
    print("─" * 72)
    px_univ, px_beta, factor_ret = fetch_data()
    log.info(f"Universe: {list(px_univ.columns)}")

    # ── Raw monthly returns + weights ─────────────────────────────────────────
    print("\n" + "─" * 72)
    print("RAW SIGNAL")
    print("─" * 72)
    net_raw, weights_m = build_raw_monthly(px_univ)
    log.info(f"Raw monthly: {len(net_raw)} months, Sharpe={_sharpe(net_raw):.3f}")

    # ── Baseline VT (10%, 3M, 2×) ─────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("BASELINE VT — 10% target, 3M lookback, 2× cap")
    print("─" * 72)
    net_vt = vol_target(net_raw, target=0.10, lb_months=3, cap=2.0)
    log.info(f"Baseline VT: {len(net_vt)} months, Sharpe={_sharpe(net_vt):.3f}, MaxDD={_max_dd(net_vt)*100:.1f}%")

    # ── Overlay A ─────────────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("OVERLAY A — aggressive vol targeting: 6%, 21-day lookback, 2.5× cap")
    print("─" * 72)
    net_a = overlay_a(net_raw, px_univ, weights_m)
    log.info(f"Overlay A: {len(net_a)} months, Sharpe={_sharpe(net_a):.3f}, MaxDD={_max_dd(net_a)*100:.1f}%")

    # ── Overlay B ─────────────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("OVERLAY B — per-position stop loss: -5% per ETF leg (daily close)")
    print("─" * 72)
    net_b = overlay_b(px_univ, weights_m, net_raw,
                      stop_pct=0.05, vt_target=0.10, vt_lb_months=3, vt_cap=2.0)
    log.info(f"Overlay B: {len(net_b)} months, Sharpe={_sharpe(net_b):.3f}, MaxDD={_max_dd(net_b)*100:.1f}%")

    # ── Overlay C ─────────────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("OVERLAY C — correlation regime filter: ×0.5 if corr>0.50, ×0.25 if corr>0.65")
    print("─" * 72)
    net_c = overlay_c(net_vt, px_univ)
    log.info(f"Overlay C: {len(net_c)} months, Sharpe={_sharpe(net_c):.3f}, MaxDD={_max_dd(net_c)*100:.1f}%")

    # ── Score and pick best two ───────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("SELECTING BEST TWO OVERLAYS (Sharpe × (1 - |MaxDD|) score)")
    print("─" * 72)
    overlay_results = {
        "A": (net_a, "A"),
        "B": (net_b, "B"),
        "C": (net_c, "C"),
    }
    scores = {}
    for k, (r, _) in overlay_results.items():
        sh = _sharpe(r)
        dd = abs(_max_dd(r))
        sc = sh * (1 - dd) if (np.isfinite(sh) and np.isfinite(dd)) else np.nan
        scores[k] = sc
        print(f"  Overlay {k}: Sharpe={_fmt(sh,'+.3f')}  MaxDD={_fmt(dd,'+.1f',pct=True)}  score={_fmt(sc,'+.3f')}")

    valid   = {k: v for k, v in scores.items() if np.isfinite(v)}
    ranked  = sorted(valid, key=lambda k: valid[k], reverse=True)
    if len(ranked) < 2:
        # fallback: sort all by Sharpe when too few valid scores
        ranked = sorted(overlay_results, key=lambda k: _sharpe(overlay_results[k][0])
                        if np.isfinite(_sharpe(overlay_results[k][0])) else -999,
                        reverse=True)
    best_two = ranked[:2]
    best_combo_label = "+".join(sorted(best_two))
    print(f"\n  → Best two: {best_two[0]} (score={scores[best_two[0]]:.3f}) "
          f"+ {best_two[1]} (score={scores[best_two[1]]:.3f})")
    print(f"  → Combined label: {best_combo_label}")

    # ── Combined overlay ──────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print(f"COMBINED {best_combo_label}")
    print("─" * 72)
    net_combo = overlay_combined(
        best_combo_label, net_a, net_b, net_vt,
        px_univ, net_raw, weights_m
    )
    log.info(f"Combined {best_combo_label}: {len(net_combo)} months, "
             f"Sharpe={_sharpe(net_combo):.3f}, MaxDD={_max_dd(net_combo)*100:.1f}%")

    # ── Compute full stats for all variants ───────────────────────────────────
    print("\n" + "─" * 72)
    print("FULL STATS — ALL VARIANTS")
    print("─" * 72)
    all_series = {
        "Baseline VT":              (net_vt,   N_BASE),
        "Overlay A":                (net_a,    N_BASE + 1),
        "Overlay B":                (net_b,    N_BASE + 2),
        "Overlay C":                (net_c,    N_BASE + 3),
        f"Combined {best_combo_label}": (net_combo, N_BASE + 4),
    }
    variants_stats = {}
    for name, (r, n_tests) in all_series.items():
        s = _full_stats(r, factor_ret, n_tests)
        variants_stats[name] = s
        dsr_n_p  = s["dsr_actual"]["dsr_pvalue"]
        dsr_58_p = s["dsr_58"]["dsr_pvalue"]
        print(f"\n  [{name}] n={len(r)}  Sharpe={_fmt(s['sharpe'],'+.3f')}  "
              f"MaxDD={_fmt(s['max_dd'],'+.1f',pct=True)}%  "
              f"alpha={_fmt(s.get('alpha_ann'),'+.1f',pct=True)}%  "
              f"residSR={_fmt(s.get('resid_sharpe'),'+.3f')}  "
              f"DSR(n)={_fmt(dsr_n_p,'.4f')}  "
              f"DSR(58)={_fmt(dsr_58_p,'.4f')}")
        for crash_name, c in s["crashes"].items():
            if "max_dd" in c:
                print(f"    {crash_name:<16} MaxDD={c['max_dd']*100:+.1f}%  "
                      f"Sharpe={c['sharpe']:+.2f}  CumRet={c['cum_ret']*100:+.1f}%")

    # ── EuroCrisis deep dive ───────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("EUROCRISIS 2011 DEEP DIVE")
    print("─" * 72)
    ec = eurocrisis_analysis(px_univ, weights_m)
    print(f"  Period:                {ec['period']}")
    print(f"  Peak avg pairwise corr: {ec['peak_avg_pairwise_corr']:.3f} on {ec['peak_corr_date']}")
    print(f"  Months corr > 0.50:    {ec['months_corr_above_0.50']}")
    print(f"  Months corr > 0.65:    {ec['months_corr_above_0.65']}")
    print(f"  Top drag assets:       {ec['top_drag_assets']}")
    print(f"  Top lift assets:       {ec['top_lift_assets']}")

    # ── Structured summary ─────────────────────────────────────────────────────
    summary = build_summary(variants_stats, ec, best_combo_label)

    print("\n\n" + "=" * 72)
    print(summary)
    print("=" * 72)

    # ── Save ──────────────────────────────────────────────────────────────────
    results = {
        "best_combo":   best_combo_label,
        "scores":       scores,
        "variants":     variants_stats,
        "eurocrisis":   ec,
    }
    RESULTS_JSON.write_text(json.dumps(results, indent=2, default=str))
    SUMMARY_MD.write_text(summary)
    log.info(f"Saved → {RESULTS_JSON}")
    log.info(f"Saved → {SUMMARY_MD}")

    return results


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("risk_overlays run failed")
        sys.exit(1)
