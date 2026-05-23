"""
backtest/engine.py — Vol-targeted swing strategy backtest core.

Position model:
    signal_z[T] = clip(rolling_zscore(signal[T], 252d), -3, 3)
    pos[T]      = (±1) × signal_z[T] × (vol_target / vol_ann[T])   [± = flip_sign]
    pnl[T]      = pos[T-1] × (log_ret[T] - rf[T-1]/252)
    cost[T]     = |pos[T] - pos[T-1]| × cost_rt/2

Signal at T-1, position set at close T-1, P&L realized during day T.
All in close-to-close daily series. No look-ahead in positions.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252
VOL_WIN               = 63     # trailing vol estimation window (days)
ZSCORE_WIN            = 252    # rolling signal z-score window (days)
WF_FOLDS              = 5
MIN_IS_YRS            = 4.0    # minimum in-sample years before first OOS fold
MIN_OOS_DAYS          = 60     # minimum OOS days per fold


def run_signal_backtest(
    signal:        pd.Series,
    prices_close:  pd.Series,
    rf:            pd.Series,
    name:          str   = "",
    vol_target:    float = 0.10,   # 10% annualized portfolio vol target
    cost_rt:       float = 0.001,  # 0.10% round-trip (ETF conservative)
    zscore_win:    int   = ZSCORE_WIN,
    flip_sign:     bool  = False,  # True when IC < 0 (inverts signal direction)
    wf_folds:      int   = WF_FOLDS,
    min_is_yrs:    float = MIN_IS_YRS,
) -> dict[str, Any]:
    """
    Run a vol-targeted backtest for a single (signal, ticker) pair.

    Parameters
    ----------
    signal        : daily signal values, indexed by observation date T.
                    Values represent information available at close T.
    prices_close  : close prices for the target ticker.
    rf            : annual risk-free rate (decimal, e.g. 0.05 = 5% p.a.).
    vol_target    : annualized portfolio volatility target.
    cost_rt       : round-trip transaction cost fraction (e.g. 0.001 = 0.10%).
    flip_sign     : if True, multiply signal_z by -1 (use when IC < 0).
    wf_folds      : number of walk-forward OOS folds (expanding IS window).
    min_is_yrs    : minimum in-sample period (years) before first OOS fold.

    Returns
    -------
    dict with keys:
        pnl, equity, pos, signal_z, stats_full (dict), stats_wf (dict)
    """
    # ── Align all series to signal index ─────────────────────────────────────
    idx          = signal.dropna().index
    close_a      = prices_close.reindex(idx).ffill(limit=3)
    rf_a         = rf.reindex(idx).ffill(limit=5).fillna(0.0)

    log_ret      = np.log(close_a).diff()

    # Trailing annualized vol (no look-ahead)
    vol_ann      = (log_ret.rolling(VOL_WIN, min_periods=VOL_WIN // 2).std()
                   * np.sqrt(TRADING_DAYS_PER_YEAR))
    vol_ann      = vol_ann.replace(0, np.nan)

    # ── Signal z-score (trailing 252d, no look-ahead) ─────────────────────────
    sig_mu       = signal.rolling(zscore_win, min_periods=zscore_win // 2).mean()
    sig_std      = signal.rolling(zscore_win, min_periods=zscore_win // 2).std()
    signal_z     = ((signal - sig_mu) / sig_std.replace(0, np.nan)).clip(-3, 3)
    if flip_sign:
        signal_z = -signal_z

    # ── Positions (set at close T using signal[T]) ─────────────────────────────
    pos          = (signal_z / vol_ann * vol_target).fillna(0.0)

    # ── Daily excess return at T: log_ret[T] − rf[T-1]/252 ───────────────────
    rf_daily     = rf_a.shift(1) / TRADING_DAYS_PER_YEAR
    excess_ret   = log_ret - rf_daily

    # ── P&L: pos[T-1] × excess_ret[T]  (signal at T-1 → position at T-1 → P&L at T) ──
    pnl_gross    = pos.shift(1) * excess_ret

    # ── Transaction costs: one-way = cost_rt/2 per side ─────────────────────
    costs        = pos.diff().abs() * (cost_rt / 2)
    pnl_net      = (pnl_gross - costs).dropna()
    pnl_gross_c  = pnl_gross.reindex(pnl_net.index)

    equity       = pnl_net.cumsum()

    # Annual turnover = mean(|Δpos|) × 252
    turnover_ann = pos.diff().abs().mean() * TRADING_DAYS_PER_YEAR

    stats_full          = _compute_stats(pnl_net)
    stats_gross         = _compute_stats(pnl_gross_c)
    stats_wf            = _walk_forward(pnl_net, wf_folds, min_is_yrs)

    return {
        "name":         name,
        "pnl":          pnl_net,
        "pnl_gross":    pnl_gross_c,
        "equity":       equity,
        "pos":          pos,
        "signal_z":     signal_z,
        "turnover_ann": round(float(turnover_ann), 3),
        "stats_full":   stats_full,
        "stats_gross":  stats_gross,
        "stats_wf":     stats_wf,
    }


def run_combo_backtest(
    signals_z:    dict[str, pd.Series],
    prices_close: pd.Series,
    rf:           pd.Series,
    name:         str   = "combo",
    vol_target:   float = 0.10,
    cost_rt:      float = 0.001,
    wf_folds:     int   = WF_FOLDS,
    min_is_yrs:   float = MIN_IS_YRS,
) -> dict[str, Any]:
    """
    Average a dict of pre-normalized signal_z series into a combined signal.

    signals_z: dict of {label: signal_z_series} — already direction-corrected
               (flip must be applied before passing).
    Each series is already on the same z-score scale. Combined = simple average.
    """
    # Align on common index
    combined_df  = pd.DataFrame(signals_z).dropna(how="all")
    combined_z   = combined_df.mean(axis=1)   # equal-weight average z-score

    # Vol-target positions using the combined z-score
    idx          = combined_z.dropna().index
    close_a      = prices_close.reindex(idx).ffill(limit=3)
    rf_a         = rf.reindex(idx).ffill(limit=5).fillna(0.0)

    log_ret      = np.log(close_a).diff()
    vol_ann      = (log_ret.rolling(VOL_WIN, min_periods=VOL_WIN // 2).std()
                   * np.sqrt(TRADING_DAYS_PER_YEAR)).replace(0, np.nan)

    pos          = (combined_z / vol_ann * vol_target).fillna(0.0)
    rf_daily     = rf_a.shift(1) / TRADING_DAYS_PER_YEAR
    excess_ret   = log_ret - rf_daily
    pnl_gross    = pos.shift(1) * excess_ret
    costs        = pos.diff().abs() * (cost_rt / 2)
    pnl_net      = (pnl_gross - costs).dropna()
    equity       = pnl_net.cumsum()

    return {
        "name":       name,
        "pnl":        pnl_net,
        "equity":     equity,
        "pos":        pos,
        "signal_z":   combined_z,
        "stats_full": _compute_stats(pnl_net),
        "stats_wf":   _walk_forward(pnl_net, wf_folds, min_is_yrs),
    }


def run_portfolio_backtest(
    individual_pnls: dict[str, pd.Series],
    name:            str   = "portfolio",
    vol_target:      float = 0.10,
) -> dict[str, Any]:
    """
    Equal-risk-budget portfolio of individual strategy P&Ls.

    Scales each strategy so the ex-ante vol contribution equals vol_target / N.
    Then sums. The realized portfolio vol ≈ vol_target if strategies are uncorrelated.
    """
    n = len(individual_pnls)
    if n == 0:
        return {}
    budget = vol_target / n   # vol budget per strategy

    scaled_pnls = {}
    for label, pnl in individual_pnls.items():
        pnl_vol = pnl.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        if pnl_vol > 0:
            scale = budget / pnl_vol
        else:
            scale = 0.0
        scaled_pnls[label] = pnl * scale

    pnl_df  = pd.DataFrame(scaled_pnls).dropna(how="all").fillna(0.0)
    pnl_net = pnl_df.sum(axis=1)
    equity  = pnl_net.cumsum()

    return {
        "name":         name,
        "pnl":          pnl_net,
        "equity":       equity,
        "components":   list(individual_pnls.keys()),
        "stats_full":   _compute_stats(pnl_net),
        "stats_wf":     _walk_forward(pnl_net, WF_FOLDS, MIN_IS_YRS),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _compute_stats(pnl: pd.Series) -> dict[str, Any]:
    n = len(pnl)
    if n < 50:
        return {
            "sharpe": np.nan, "ann_ret": np.nan, "ann_vol": np.nan,
            "max_dd": np.nan, "calmar": np.nan, "n_days": n, "n_years": round(n / TRADING_DAYS_PER_YEAR, 1),
        }

    ann_ret  = pnl.mean() * TRADING_DAYS_PER_YEAR
    ann_vol  = pnl.std()  * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe   = ann_ret / ann_vol if ann_vol > 0 else np.nan

    cum      = pnl.cumsum()
    max_dd   = (cum - cum.cummax()).min()
    calmar   = ann_ret / abs(max_dd) if max_dd < 0 else np.nan

    return {
        "sharpe":  round(sharpe,  3),
        "ann_ret": round(ann_ret, 4),
        "ann_vol": round(ann_vol, 4),
        "max_dd":  round(max_dd,  4),
        "calmar":  round(calmar,  3) if not np.isnan(calmar) else np.nan,
        "n_days":  n,
        "n_years": round(n / TRADING_DAYS_PER_YEAR, 1),
    }


def _walk_forward(pnl: pd.Series, n_folds: int, min_is_yrs: float) -> dict[str, Any]:
    n      = len(pnl)
    min_is = int(min_is_yrs * TRADING_DAYS_PER_YEAR)

    if n < min_is + n_folds * MIN_OOS_DAYS:
        return {"wf_positive_frac": np.nan, "wf_sharpe_list": [], "n_folds": 0}

    total_oos = n - min_is
    fold_size = total_oos // n_folds

    fold_sharpes = []
    for i in range(n_folds):
        oos_s    = min_is + i * fold_size
        oos_e    = min_is + (i + 1) * fold_size if i < n_folds - 1 else n
        oos_pnl  = pnl.iloc[oos_s:oos_e]
        fold_sharpes.append(_compute_stats(oos_pnl)["sharpe"])

    valid    = [s for s in fold_sharpes if not np.isnan(s)]
    pos_frac = sum(s > 0 for s in valid) / len(valid) if valid else np.nan

    return {
        "wf_positive_frac": round(pos_frac, 3),
        "wf_sharpe_list":   [round(s, 3) if not np.isnan(s) else float("nan")
                             for s in fold_sharpes],
        "n_folds":          len(fold_sharpes),
    }


def verdict_gate(stats_full: dict, stats_wf: dict) -> tuple[str, list[str]]:
    """
    Apply two-tier gates from CLAUDE.md:
      RESEARCH_PASS: Sharpe>0.7, MaxDD>-0.25, WF>0.50
      PROPFIRM_PASS: Sharpe>1.0, MaxDD>-0.10, WF>0.60

    Returns (verdict_str, list_of_failed_gates).
    """
    sr     = stats_full.get("sharpe", float("nan"))
    dd     = stats_full.get("max_dd", float("nan"))
    wf     = stats_wf.get("wf_positive_frac", float("nan"))

    if any(np.isnan(v) for v in [sr, dd, wf]):
        return "INCONCLUSIVE", ["missing data"]

    def _check(label: str, sr_th: float, dd_th: float, wf_th: float) -> list[str]:
        fails = []
        if sr  < sr_th:  fails.append(f"Sharpe={sr:.2f}<{sr_th}")
        if dd  < dd_th:  fails.append(f"MaxDD={dd:.3f}<{dd_th}")
        if wf  < wf_th:  fails.append(f"WF={wf:.2f}<{wf_th}")
        return fails

    propfirm_fails  = _check("PROPFIRM",  1.0, -0.10, 0.60)
    research_fails  = _check("RESEARCH",  0.7, -0.25, 0.50)

    if not propfirm_fails:
        return "PROPFIRM_PASS", []
    elif not research_fails:
        return "RESEARCH_PASS", propfirm_fails
    else:
        return "FAIL", research_fails
