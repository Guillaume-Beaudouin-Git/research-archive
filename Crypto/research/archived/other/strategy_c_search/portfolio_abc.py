"""
A+B+C Portfolio Combination
============================
Strategy A: TSMOM v3 C1 (long-only, Sharpe 1.33)
Strategy B: Delta-neutral funding carry (Sharpe 10.22)
Strategy C: XGBoost ensemble cross-sectional long-only (Sharpe 0.734)

Tests weight combinations W1-W4 vs the A+B baseline (2.61 Sharpe).
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from strategies.tsmom_v3.backtest import (
    download_data as tsmom_download, compute_pnl as tsmom_compute_pnl,
    VOL_TARGET as TSMOM_VOL, TRADING_DAYS,
)
from strategies.tsmom_v3.signal import continuous_signal, build_positions
from strategies.delta_neutral.backtest import (
    VIABLE_ASSETS, TOTAL_CAPITAL,
    load_funding_8h, load_perp_8h, fetch_binance_spot_8h,
    align_asset_data, run_walkforward,
)
from strategies.xgb_microstructure.feasibility_v2 import (
    load_prices, load_funding_weekly,
    build_feature_panel, cs_zscore_panel,
    build_target, run_purged_walkforward, build_portfolio,
    ASSETS,
)

OOS_START = "2023-01-01"

WEIGHT_CONFIGS = [
    {"label": "A+B (baseline)", "w_a": 0.30, "w_b": 0.70, "w_c": 0.00},
    {"label": "A+B+C  W1",     "w_a": 0.30, "w_b": 0.50, "w_c": 0.20},
    {"label": "A+B+C  W2",     "w_a": 0.25, "w_b": 0.55, "w_c": 0.20},
    {"label": "A+B+C  W3",     "w_a": 0.30, "w_b": 0.40, "w_c": 0.30},
    {"label": "A+B+C  W4",     "w_a": 0.20, "w_b": 0.50, "w_c": 0.30},
]


def _sharpe(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 10 or r.std() == 0:
        return np.nan
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS))


def _maxdd(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 2:
        return np.nan
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def build_carry_returns() -> pd.Series:
    print("  [B] Building carry returns …")
    asset_data: dict = {}
    for asset in VIABLE_ASSETS:
        try:
            funding  = load_funding_8h(asset)
            perp     = load_perp_8h(asset)
            start    = funding.index.min().to_pydatetime()
            spot     = fetch_binance_spot_8h(asset, start)
            if spot.empty:
                continue
            aligned  = align_asset_data(funding, perp, spot)
            if len(aligned) >= 180:
                asset_data[asset] = aligned
        except Exception:
            continue

    if len(asset_data) < 2:
        return pd.Series(dtype=float, name="carry")

    oos_df, _ = run_walkforward(asset_data)
    if oos_df.empty:
        return pd.Series(dtype=float, name="carry")

    port_8h  = oos_df.groupby(oos_df.index)["net_pnl"].sum()
    daily    = port_8h.resample("D").sum()
    daily.index = daily.index.tz_localize(None)
    carry    = (daily / TOTAL_CAPITAL).rename("carry")
    print(f"    Carry OOS: {carry.first_valid_index().date()} → "
          f"{carry.last_valid_index().date()}  "
          f"({(carry != 0).sum()} active days)")
    return carry


def build_xgb_returns() -> pd.Series:
    print("  [C] Building XGBoost ensemble returns …")
    close, volume, log_ret = load_prices()
    funding = load_funding_weekly()
    for df in [close, volume, log_ret]:
        df.columns = [c.replace("-USD", "") if "-USD" in c else c
                      for c in df.columns]

    feat_panel = build_feature_panel(close, volume, log_ret, funding)
    feat_panel = cs_zscore_panel(feat_panel)
    target     = build_target(log_ret)
    pred_df, *_ = run_purged_walkforward(feat_panel, target)

    if pred_df.empty:
        return pd.Series(dtype=float, name="xgb")

    oos_s = pred_df["date"].min()
    oos_e = pred_df["date"].max()
    close_oos   = close.loc[str(oos_s.date()):str(oos_e.date())]
    log_ret_oos = log_ret.loc[str(oos_s.date()):str(oos_e.date())]

    pnl = build_portfolio(pred_df, close_oos, log_ret_oos,
                          proba_col="proba_ens", conf_pct=0)
    pnl = pnl.rename("xgb")
    print(f"    XGB OOS: {pnl.first_valid_index().date()} → "
          f"{pnl.last_valid_index().date()}  "
          f"Sharpe={_sharpe(pnl):.3f}  MaxDD={_maxdd(pnl):.1%}")
    return pnl


def main() -> None:
    print("=" * 65)
    print("A+B+C PORTFOLIO COMBINATION")
    print("=" * 65)

    # ── Strategy A ─────────────────────────────────────────────────
    print("\n  [A] Building TSMOM v3 C1 returns …")
    close_ts, log_ret_ts = tsmom_download()
    pos_c1 = build_positions(
        continuous_signal(log_ret_ts, 28), log_ret_ts, TSMOM_VOL
    )
    r_a = tsmom_compute_pnl(close_ts, pos_c1).rename("tsmom")
    print(f"    TSMOM: {r_a.first_valid_index().date()} → "
          f"{r_a.last_valid_index().date()}  Sharpe={_sharpe(r_a[OOS_START:]):.3f}")

    # ── Strategy B ─────────────────────────────────────────────────
    r_b = build_carry_returns()

    # ── Strategy C ─────────────────────────────────────────────────
    r_c = build_xgb_returns()

    if r_b.dropna().empty:
        print("\nFATAL: carry returns unavailable")
        return
    if r_c.dropna().empty:
        print("\nFATAL: XGB returns unavailable")
        return

    # ── Common period ──────────────────────────────────────────────
    b_start = r_b[r_b != 0].first_valid_index()
    b_end   = r_b[r_b != 0].last_valid_index()
    c_start = r_c.first_valid_index()
    c_end   = r_c.last_valid_index()
    a_start = pd.Timestamp(OOS_START)

    common_start = max(a_start, b_start, c_start)
    common_end   = min(b_end, c_end)

    print(f"\n  Common period: {common_start.date()} → {common_end.date()}")
    n_days = (common_end - common_start).days
    print(f"  Duration: {n_days} calendar days")
    if n_days < 90:
        print("  *** WARNING: < 90 days — statistically limited ***")
    elif n_days < 365:
        print("  NOTE: < 1 year — treat with caution (carry OOS still short)")

    # Align
    idx = pd.date_range(common_start, common_end, freq="D")
    a   = r_a.reindex(idx).fillna(0.0)
    b   = r_b.reindex(idx).fillna(0.0)
    c   = r_c.reindex(idx).fillna(0.0)

    corr_ab = float(a.corr(b))
    corr_ac = float(a.corr(c))
    corr_bc = float(b.corr(c))

    print(f"\n  Per-strategy Sharpe over common period:")
    print(f"    A (TSMOM)  : {_sharpe(a):.3f}")
    print(f"    B (carry)  : {_sharpe(b):.3f}")
    print(f"    C (XGB)    : {_sharpe(c):.3f}")
    print(f"\n  Correlations:")
    print(f"    corr(A,B)  : {corr_ab:+.4f}")
    print(f"    corr(A,C)  : {corr_ac:+.4f}")
    print(f"    corr(B,C)  : {corr_bc:+.4f}")

    # ── Weight sweep ───────────────────────────────────────────────
    print(f"\n  {'Portfolio':<22} {'w_A':>5} {'w_B':>5} {'w_C':>5} "
          f"{'Sharpe':>9} {'MaxDD':>8} {'vs baseline':>12}")
    print("  " + "─" * 68)

    baseline_sh = None
    for cfg in WEIGHT_CONFIGS:
        w_a, w_b, w_c = cfg["w_a"], cfg["w_b"], cfg["w_c"]
        r = w_a * a + w_b * b + w_c * c
        sh = _sharpe(r)
        dd = _maxdd(r)
        if baseline_sh is None:
            baseline_sh = sh
            delta = ""
        else:
            delta = f"{sh - baseline_sh:+.3f}"
        print(f"  {cfg['label']:<22} {w_a:>5.0%} {w_b:>5.0%} {w_c:>5.0%} "
              f"{sh:>9.3f} {dd:>8.1%} {delta:>12}")

    print(f"\n  Theoretical ceiling (corr=0): "
          f"√({_sharpe(a):.2f}²+{_sharpe(b):.2f}²+{_sharpe(c):.2f}²) = "
          f"{np.sqrt(_sharpe(a)**2 + _sharpe(b)**2 + _sharpe(c)**2):.3f}")

    # ── Summary verdict ────────────────────────────────────────────
    best_abc_sh = max(
        _sharpe(cfg["w_a"]*a + cfg["w_b"]*b + cfg["w_c"]*c)
        for cfg in WEIGHT_CONFIGS if cfg["w_c"] > 0
    )
    print(f"\n  Best A+B+C Sharpe : {best_abc_sh:.3f}")
    print(f"  A+B baseline      : {baseline_sh:.3f}")
    if best_abc_sh > baseline_sh:
        print(f"  A+B+C BEATS A+B by {best_abc_sh - baseline_sh:+.3f} ✓")
    else:
        print(f"  A+B+C does NOT beat A+B "
              f"({best_abc_sh - baseline_sh:+.3f}). C adds diversification but short history limits B Sharpe.")


if __name__ == "__main__":
    main()
