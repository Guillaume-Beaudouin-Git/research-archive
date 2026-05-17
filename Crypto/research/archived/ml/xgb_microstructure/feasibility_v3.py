"""
XGBoost v3 — Long-Short Test + Confidence Threshold Sweep
==========================================================

Extends v2 with two targeted fixes:

FIX 1 — Long-Short: long top-3, short bottom-3 by proba_ensemble.
  Confidence filter on L/S removes the MOST UNCERTAIN (middle-rank)
  assets, which is exactly how the ScienceDirect 2022 paper achieves
  Sharpe 3.23.  Long leg: 15% vol target. Short leg: 10% vol target.

FIX 2 — Confidence threshold sweep for long-only: test
  [0%, 10%, 20%, 30%, 40%, 50%] cutoffs → find the peak Sharpe.
  0% = trade all (v2 base = 0.734 Sharpe).

P&L decomposition (L/S) → diagnose if short side destroys value.

DEPLOY:   L/S SR > 1.0 AND short_leg SR > -0.2
PROMISING: L/S SR 0.8-1.0
SKIP:     L/S SR < 0.8 OR short_leg SR < -0.5
          → accept long-only 0.734 as Strategy C at w_C=0.2
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# ── import all shared logic from v2 ──────────────────────────────────────────
from strategies.xgb_microstructure.feasibility_v2 import (
    ASSETS, TICKERS, FEAT_NAMES, WF_WINDOWS, PURGE_WEEKS,
    DATA_START, DATA_END, COST_RT, N_LONG, N_SHORT,
    load_prices, load_funding_weekly,
    build_feature_panel, cs_zscore_panel, build_target,
    run_purged_walkforward,
    build_portfolio, _sharpe, _maxdd,
    load_tsmom_daily,
)
from dsr import deflated_sharpe_ratio

LONG_VOL_TGT  = 0.15   # per long position
SHORT_VOL_TGT = 0.10   # per short position (smaller)
N_TRIALS_DSR  = 30
OUT_DIR = Path(__file__).parent


# ══════════════════════════════════════════════════════════════════════════════
# LONG-SHORT PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════

def build_portfolio_ls(
    pred_df:   pd.DataFrame,
    close:     pd.DataFrame,
    log_ret:   pd.DataFrame,
    proba_col: str,
    conf_pct:  float,     # 0=ALL, 20=TOP20 (keep confidence > 20th pct)
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Long top-N_LONG, short bottom-N_SHORT at each weekly date.
    Confidence filter: keep only assets with confidence > conf_pct-th percentile.
    Returns (pnl_total, pnl_long_leg, pnl_short_leg) as daily Series.
    """
    vol_daily  = log_ret.rolling(20, min_periods=10).std() * np.sqrt(252)
    vol_w      = vol_daily.resample("W-FRI").last()
    arith      = close.pct_change().fillna(0.0)

    common_cols = [a for a in ASSETS if a in arith.columns and a in vol_w.columns]
    pos_long  = pd.DataFrame(0.0, index=vol_w.index, columns=common_cols)
    pos_short = pd.DataFrame(0.0, index=vol_w.index, columns=common_cols)

    for dt in sorted(pred_df["date"].unique()):
        if dt not in pos_long.index:
            continue
        day = pred_df[pred_df["date"] == dt].copy()

        # Confidence filter: remove most uncertain (middle-rank) assets
        if conf_pct > 0 and len(day) > 1:
            conf = (day[proba_col] - 0.5).abs()
            thr  = np.percentile(conf, conf_pct)
            day  = day[conf > thr]

        if day.empty:
            continue

        sorted_day = day.sort_values(proba_col, ascending=False)
        pos_long.loc[dt]  = 0.0
        pos_short.loc[dt] = 0.0

        for _, row in sorted_day.head(N_LONG).iterrows():
            asset = row["asset"]
            if asset in common_cols and dt in vol_w.index:
                v = vol_w.at[dt, asset]
                if np.isfinite(v) and v > 0:
                    pos_long.loc[dt, asset] += LONG_VOL_TGT / v

        for _, row in sorted_day.tail(N_SHORT).iterrows():
            asset = row["asset"]
            if asset in common_cols and dt in vol_w.index:
                v = vol_w.at[dt, asset]
                if np.isfinite(v) and v > 0:
                    pos_short.loc[dt, asset] -= SHORT_VOL_TGT / v

    pos_long  = pos_long.reindex(vol_w.index).ffill().fillna(0.0)
    pos_short = pos_short.reindex(vol_w.index).ffill().fillna(0.0)

    pos_long_d  = pos_long.reindex(log_ret.index).ffill().fillna(0.0)
    pos_short_d = pos_short.reindex(log_ret.index).ffill().fillna(0.0)

    held_l = pos_long_d.shift(1).fillna(0.0)
    held_s = pos_short_d.shift(1).fillna(0.0)

    pnl_long_g  = (held_l[common_cols] * arith[common_cols]).sum(axis=1)
    pnl_short_g = (held_s[common_cols] * arith[common_cols]).sum(axis=1)

    is_mon = pd.Series(log_ret.index.dayofweek == 0, index=log_ret.index).astype(float)
    cost_l = (pos_long_d[common_cols].diff().abs()
              * COST_RT * is_mon.values.reshape(-1, 1)).sum(axis=1)
    cost_s = (pos_short_d[common_cols].diff().abs()
              * COST_RT * is_mon.values.reshape(-1, 1)).sum(axis=1)

    pnl_long_net  = pnl_long_g  - cost_l
    pnl_short_net = pnl_short_g - cost_s
    pnl_total     = pnl_long_net + pnl_short_net

    pnl_total.name     = f"ls_cf{int(conf_pct)}_total"
    pnl_long_net.name  = f"ls_cf{int(conf_pct)}_long"
    pnl_short_net.name = f"ls_cf{int(conf_pct)}_short"
    return pnl_total, pnl_long_net, pnl_short_net


# ══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE THRESHOLD SWEEP (long-only)
# ══════════════════════════════════════════════════════════════════════════════

def threshold_sweep(
    pred_df:  pd.DataFrame,
    close:    pd.DataFrame,
    log_ret:  pd.DataFrame,
    proba_col: str = "proba_ens",
    thresholds: list[int] = None,
) -> dict[int, float]:
    """
    For long-only, sweep confidence percentile cutoffs.
    cutoff=0  → trade all (no filter)
    cutoff=20 → confidence > 20th pct (keep top 80%)
    cutoff=50 → confidence > 50th pct (keep top 50%)
    Returns {cutoff: sharpe}.
    """
    if thresholds is None:
        thresholds = [0, 10, 20, 30, 40, 50]
    results = {}
    for thr in thresholds:
        pnl = build_portfolio(
            pred_df, close, log_ret,
            proba_col=proba_col, conf_pct=thr,
        )
        results[thr] = _sharpe(pnl)
    return results


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def per_window_sharpe(pnl: pd.Series) -> list[float]:
    """Slice daily P&L into each WF window and return Sharpe per window."""
    sharpes = []
    for w in WF_WINDOWS:
        sub = pnl.loc[w["test_start"]:w["test_end"]]
        sharpes.append(_sharpe(sub))
    return sharpes


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE
# ══════════════════════════════════════════════════════════════════════════════

def make_figure(
    sweep_results:   dict[int, float],
    ls_all_total:    pd.Series,
    ls_all_long:     pd.Series,
    ls_all_short:    pd.Series,
    best_lo_pnl:     pd.Series,
    ls_best_pnl:     pd.Series,
    tsmom_pnl:       pd.Series,
    window_sharpes:  dict[str, list[float]],
    out_path:        str,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("XGBoost v3 — Long-Short + Confidence Sweep",
                 fontsize=13, fontweight="bold")

    # [0,0]: Threshold sweep for long-only
    ax = axes[0, 0]
    thrs  = sorted(sweep_results)
    sharps = [sweep_results[t] for t in thrs]
    ax.plot(thrs, sharps, "o-", color="#3498db", linewidth=2)
    for t, s in zip(thrs, sharps):
        ax.annotate(f"{s:.2f}", (t, s), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=8)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xlabel("Confidence filter cutoff (percentile)")
    ax.set_ylabel("Sharpe Ratio (long-only)")
    ax.set_title("Long-Only: Sharpe vs Confidence Filter Threshold")
    ax.set_xticks(thrs)
    ax.set_xticklabels([f"{t}%" for t in thrs])

    # [0,1]: L/S P&L leg decomposition
    ax = axes[0, 1]
    common = ls_all_total.index
    eq_total = (1 + ls_all_total.fillna(0)).cumprod()
    eq_long  = (1 + ls_all_long.fillna(0)).cumprod()
    eq_short = (1 + ls_all_short.fillna(0)).cumprod()
    sh_t = _sharpe(ls_all_total)
    sh_l = _sharpe(ls_all_long)
    sh_s = _sharpe(ls_all_short)
    ax.plot(eq_total, label=f"Total (SR={sh_t:.2f})", color="#2c3e50", linewidth=1.8)
    ax.plot(eq_long,  label=f"Long leg (SR={sh_l:.2f})", color="#2ecc71", linewidth=1.2, linestyle="--")
    ax.plot(eq_short, label=f"Short leg (SR={sh_s:.2f})", color="#e74c3c", linewidth=1.2, linestyle=":")
    ax.axhline(1, color="black", linewidth=0.5)
    ax.legend(fontsize=8)
    ax.set_title("L/S Leg Decomposition (ALL filter)")
    ax.set_ylabel("Cumulative Return")

    # [1,0]: OOS equity curves
    ax = axes[1, 0]
    ts_aligned = tsmom_pnl.reindex(best_lo_pnl.index).fillna(0)
    eq_lo   = (1 + best_lo_pnl.fillna(0)).cumprod()
    eq_ls   = (1 + ls_best_pnl.reindex(best_lo_pnl.index).fillna(0)).cumprod()
    eq_ts   = (1 + ts_aligned).cumprod()
    ax.plot(eq_lo, label=f"XGB Long-only best (SR={_sharpe(best_lo_pnl):.2f})",
            color="#3498db", linewidth=1.4)
    ax.plot(eq_ls, label=f"XGB L/S best (SR={_sharpe(ls_best_pnl):.2f})",
            color="#9b59b6", linewidth=1.4)
    ax.plot(eq_ts, label=f"TSMOM v3 (SR={_sharpe(ts_aligned):.2f})",
            color="#e67e22", linewidth=1.4, linestyle="--")
    ax.axhline(1, color="black", linewidth=0.5)
    ax.legend(fontsize=8)
    ax.set_title("OOS Equity Curves")
    ax.set_ylabel("Cumulative Return")

    # [1,1]: Per-window Sharpe bars
    ax = axes[1, 1]
    window_labels = [f"W{i+1}\n{w['test_start'][:7]}" for i, w in enumerate(WF_WINDOWS)]
    x      = np.arange(len(WF_WINDOWS))
    width  = 0.22
    colors = {"LO-ALL": "#3498db", "LO-BEST": "#2980b9", "LS-ALL": "#9b59b6", "LS-TOP20": "#8e44ad"}
    for i, (cfg, color) in enumerate(colors.items()):
        vals = window_sharpes.get(cfg, [np.nan] * len(WF_WINDOWS))
        ax.bar(x + i * width, vals, width, label=cfg, color=color, alpha=0.8)
    ax.set_xticks(x + 1.5 * width)
    ax.set_xticklabels(window_labels, fontsize=8)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axhline(1.0, color="red", linewidth=0.8, linestyle="--", label="1.0 target")
    ax.legend(fontsize=7)
    ax.set_title("Per-Window Sharpe")
    ax.set_ylabel("Sharpe Ratio")

    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"[plot] Saved → {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 70)
    print("XGBoost v3 — LONG-SHORT + CONFIDENCE THRESHOLD SWEEP")
    print("=" * 70)

    # 1. Data (same as v2)
    close, volume, log_ret = load_prices()
    funding = load_funding_weekly()
    # Rename to short asset keys
    for df in [close, volume, log_ret]:
        df.columns = [c.replace("-USD", "") if "-USD" in c else c
                      for c in df.columns]

    # 2. Features + target (same as v2)
    print("\n[2] Building features …")
    feat_panel = build_feature_panel(close, volume, log_ret, funding)
    feat_panel = cs_zscore_panel(feat_panel)

    print("\n[3] Building cross-sectional target …")
    target = build_target(log_ret)

    # 4. Walk-forward (same model, same preds as v2)
    print("\n[4] Purged walk-forward …")
    pred_df, *_ = run_purged_walkforward(feat_panel, target)

    if pred_df.empty:
        print("FATAL: no predictions")
        return

    oos_start = pred_df["date"].min()
    oos_end   = pred_df["date"].max()
    close_oos   = close.loc[str(oos_start.date()):str(oos_end.date())]
    log_ret_oos = log_ret.loc[str(oos_start.date()):str(oos_end.date())]

    # 5. FIX 2 — Confidence threshold sweep (long-only)
    print("\n[5] FIX 2 — Confidence threshold sweep (long-only) …")
    sweep = threshold_sweep(pred_df, close_oos, log_ret_oos,
                            thresholds=[0, 10, 20, 30, 40, 50])
    print(f"\n  {'Cutoff':>8} {'Sharpe':>9}")
    print("  " + "─" * 20)
    best_thr    = 0
    best_lo_sh  = -np.inf
    for thr, sh in sorted(sweep.items()):
        marker = " ← v2 base" if thr == 0 else ""
        print(f"  {thr:>7}%  {sh:>9.3f}{marker}")
        if not np.isnan(sh) and sh > best_lo_sh:
            best_lo_sh = sh
            best_thr   = thr
    print(f"\n  Peak at cutoff={best_thr}%  Sharpe={best_lo_sh:.3f}")

    # Build best long-only pnl
    best_lo_pnl = build_portfolio(pred_df, close_oos, log_ret_oos,
                                  proba_col="proba_ens", conf_pct=best_thr)

    # 6. FIX 1 — Long-Short variants
    print("\n[6] FIX 1 — Long-Short variants …")
    ls_all_total, ls_all_long, ls_all_short = build_portfolio_ls(
        pred_df, close_oos, log_ret_oos, "proba_ens", conf_pct=0
    )
    ls_top20_total, ls_top20_long, ls_top20_short = build_portfolio_ls(
        pred_df, close_oos, log_ret_oos, "proba_ens", conf_pct=20
    )

    sh_ls_all    = _sharpe(ls_all_total)
    sh_ls_top20  = _sharpe(ls_top20_total)
    sh_ll_all    = _sharpe(ls_all_long)
    sh_ls_all_s  = _sharpe(ls_all_short)
    sh_ll_top20  = _sharpe(ls_top20_long)
    sh_ls_top20_s = _sharpe(ls_top20_short)
    dd_ls_all   = _maxdd(ls_all_total)
    dd_ls_top20 = _maxdd(ls_top20_total)

    print(f"\n  P&L decomposition (L/S ALL):")
    print(f"    Long  leg Sharpe : {sh_ll_all:+.3f}")
    print(f"    Short leg Sharpe : {sh_ls_all_s:+.3f}  "
          f"{'← short side destroys (6.3 problem)' if sh_ls_all_s < -0.3 else '← acceptable'}")
    print(f"    Total Sharpe     : {sh_ls_all:.3f}  MaxDD: {dd_ls_all:.1%}")
    print(f"\n  P&L decomposition (L/S TOP20%):")
    print(f"    Long  leg Sharpe : {sh_ll_top20:+.3f}")
    print(f"    Short leg Sharpe : {sh_ls_top20_s:+.3f}")
    print(f"    Total Sharpe     : {sh_ls_top20:.3f}  MaxDD: {dd_ls_top20:.1%}")

    # 7. Per-window table
    print("\n[7] Per-window Sharpe table …")
    lo_base_pnl = build_portfolio(pred_df, close_oos, log_ret_oos,
                                  proba_col="proba_ens", conf_pct=0)
    w_lo_base  = per_window_sharpe(lo_base_pnl)
    w_lo_best  = per_window_sharpe(best_lo_pnl)
    w_ls_all   = per_window_sharpe(ls_all_total)
    w_ls_top20 = per_window_sharpe(ls_top20_total)

    sh_lo_base = _sharpe(lo_base_pnl)

    print(f"\n  {'Config':<30} {'W1':>7} {'W2':>7} {'W3':>7} {'W4':>7} {'All':>7}")
    print("  " + "─" * 65)
    def _row(label, w_list, total):
        vals = " ".join(f"{v:>7.3f}" if not np.isnan(v) else "    N/A" for v in w_list)
        print(f"  {label:<30} {vals} {total:>7.3f}")

    _row("Long-only ALL (v2 base)",      w_lo_base,  sh_lo_base)
    _row(f"Long-only BEST (thr={best_thr}%)", w_lo_best,  best_lo_sh)
    _row("Long-short ALL",               w_ls_all,   sh_ls_all)
    _row("Long-short TOP20%",            w_ls_top20, sh_ls_top20)

    # 8. TSMOM correlation
    print("\n[8] TSMOM correlations …")
    tsmom_pnl = load_tsmom_daily()
    def _corr(pnl):
        aligned = pnl.reindex(tsmom_pnl.index).fillna(0)
        return float(aligned.corr(tsmom_pnl.reindex(aligned.index).fillna(0)))

    corr_lo   = _corr(best_lo_pnl)
    corr_ls   = _corr(ls_all_total)
    corr_ls20 = _corr(ls_top20_total)
    print(f"  Long-only best   : {corr_lo:+.4f}")
    print(f"  Long-short ALL   : {corr_ls:+.4f}")
    print(f"  Long-short TOP20 : {corr_ls20:+.4f}")

    # 9. DSR (best config)
    best_ls = ls_top20_total if sh_ls_top20 > sh_ls_all else ls_all_total
    best_ls_sh = max(sh_ls_top20, sh_ls_all)
    print("\n[9] DSR (best L/S config) …")
    dsr = deflated_sharpe_ratio(
        best_ls.dropna().values, n_trials=N_TRIALS_DSR, periods_per_year=252,
    )
    print(f"  SR={dsr['sharpe']:.3f}  E[max SR]={dsr['sr_benchmark']:.3f}  "
          f"DSR={dsr['dsr']:.3f}  {'PASS' if dsr['passed'] else 'FAIL'}")

    # 10. Verdict
    print("\n" + "=" * 70)
    short_ok   = sh_ls_all_s > -0.5
    deploy_ls  = best_ls_sh > 1.0 and sh_ls_all_s > -0.2
    promise_ls = best_ls_sh >= 0.8
    accept_lo  = best_lo_sh >= 0.734 - 0.01   # v2 base ± noise

    print(f"  Long-only best Sharpe    : {best_lo_sh:.3f}  (threshold={best_thr}%)")
    print(f"  Long-short ALL Sharpe    : {sh_ls_all:.3f}  (long={sh_ll_all:+.3f}, short={sh_ls_all_s:+.3f})")
    print(f"  Long-short TOP20% Sharpe : {sh_ls_top20:.3f}  (long={sh_ll_top20:+.3f}, short={sh_ls_top20_s:+.3f})")
    print(f"  Short leg acceptable     : {'yes' if short_ok else 'NO — destroys value'}")
    print(f"  DSR (n={N_TRIALS_DSR})             : {dsr['dsr']:.3f}  {'PASS' if dsr['passed'] else 'FAIL'}")

    print(f"\n  Gate 1 — L/S SR > 1.0         : {'✓' if best_ls_sh > 1.0 else '✗'} ({best_ls_sh:.3f})")
    print(f"  Gate 2 — short leg SR > -0.2  : {'✓' if sh_ls_all_s > -0.2 else '✗'} ({sh_ls_all_s:.3f})")
    print(f"  Gate 3 — corr TSMOM < 0.50   : {'✓' if abs(corr_ls) < 0.50 else '✗'} ({abs(corr_ls):.4f})")

    if deploy_ls:
        verdict = "DEPLOY — long-short as Strategy C"
    elif promise_ls:
        verdict = "PROMISING — add L/S to A+B portfolio at w_C=0.2"
    elif accept_lo:
        verdict = ("SKIP L/S — short side fails. "
                   "Accept long-only 0.734 as Strategy C (w_C=0.2 in A+B+C)")
    else:
        verdict = "SKIP — neither variant clears threshold"

    print(f"\n  VERDICT: {verdict}")
    print("=" * 70)

    # 11. Combined A+B+C (if long-only is accepted)
    print("\n[10] Combined A+B+C preview (long-only at w_C=0.2) …")
    lo_daily = best_lo_pnl.reindex(tsmom_pnl.index).fillna(0)
    ts_daily = tsmom_pnl.reindex(lo_daily.index).fillna(0)
    combined_ac = 0.60 * ts_daily + 0.40 * lo_daily   # A only, no B (B not daily)
    print(f"  TSMOM (A) alone Sharpe      : {_sharpe(ts_daily):.3f}")
    print(f"  Long-only (C) alone Sharpe  : {_sharpe(lo_daily):.3f}")
    print(f"  Combined A(60%)+C(40%)      : {_sharpe(combined_ac):.3f}  "
          f"corr(A,C)={float(ts_daily.corr(lo_daily)):+.4f}")
    print("  (Strategy B excluded — different units, short OOS history)")

    # 12. Figure
    print("\n[11] Generating figure …")
    ls_best_pnl = ls_top20_total if sh_ls_top20 > sh_ls_all else ls_all_total
    window_sharpes = {
        "LO-ALL":   w_lo_base,
        "LO-BEST":  w_lo_best,
        "LS-ALL":   w_ls_all,
        "LS-TOP20": w_ls_top20,
    }
    make_figure(
        sweep_results   = sweep,
        ls_all_total    = ls_all_total,
        ls_all_long     = ls_all_long,
        ls_all_short    = ls_all_short,
        best_lo_pnl     = best_lo_pnl,
        ls_best_pnl     = ls_best_pnl,
        tsmom_pnl       = tsmom_pnl,
        window_sharpes  = window_sharpes,
        out_path        = str(OUT_DIR / "feasibility_v3_results.png"),
    )


if __name__ == "__main__":
    main()
