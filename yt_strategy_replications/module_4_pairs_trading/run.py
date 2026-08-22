"""
Module 4 runner — pairs trading (BRK-B vs MSFT) replication + rigorous OOS test.

Reproduces the video's correlation/cointegration/z-score workflow, exposes its
look-ahead (in-sample pair selection + same-sample trading), then runs the honest
version: causal rolling hedge ratio, out-of-sample z, dollar-neutral P&L with
costs, walk-forward, and cointegration-stability diagnostics.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from engine import stats as S  # noqa: E402
from statsmodels.tsa.stattools import coint as sm_coint  # noqa: E402
import pairs as P  # noqa: E402

RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
ANN = 252.0
COST_BPS_LEG = 5.0


def perf(net: pd.Series, label: str) -> dict:
    v = net.to_numpy(float)
    eq = (1 + net.fillna(0)).cumprod()
    _, t = S.hac_tstat(v)
    mdd, _ = S.max_drawdown(eq.to_numpy(float))
    folds = S.fold_metrics(v, 5, ANN)
    return dict(label=label, n_days=int(len(v)), sharpe=float(S.sharpe_ratio(v, ANN)),
                hac_t=float(t), ann_ret=float(v.mean() * ANN),
                ann_vol=float(v.std(ddof=1) * np.sqrt(ANN)),
                total_return=float(eq.iloc[-1] - 1), maxdd=float(mdd),
                wf=float(folds["wf_score"]))


def n_roundtrips(pos: pd.Series) -> int:
    entries = (pos != 0) & (pos.shift(1).fillna(0) == 0)
    return int(entries.sum())


def main():
    prices = pd.read_parquet(HERE.parent / "data_cache" / "equities" / "universe_close.parquet")
    p1, p2 = prices["BRK-B"], prices["MSFT"]

    # --- universe diagnostics ---
    corr = P.daily_corr(prices)
    c = corr.abs().copy()
    np.fill_diagonal(c.values, np.nan)
    top = c.unstack().dropna().sort_values(ascending=False)
    top_pair = top.index[0]
    # full-sample cointegration count across all pairs (echoes "0/19 qualify")
    cols = list(prices.columns)
    n_pairs = 0
    n_coint = 0
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            d = prices[[cols[i], cols[j]]].dropna()
            if len(d) < 250:
                continue
            n_pairs += 1
            try:
                if sm_coint(d.iloc[:, 0], d.iloc[:, 1])[1] < 0.05:
                    n_coint += 1
            except Exception:
                pass

    beta_full, adf_p, coint_p = P.engle_granger(p1, p2)
    pp = P.per_period_coint(p1, p2)

    diag = {
        "pair": "BRK-B / MSFT",
        "full_return_corr": float(corr.loc["BRK-B", "MSFT"]),
        "empirical_top_pair": f"{top_pair[0]}/{top_pair[1]}",
        "empirical_top_corr": float(top.iloc[0]),
        "EG_hedge_beta_full": beta_full,
        "EG_resid_ADF_p_full": adf_p,
        "coint_p_full": coint_p,
        "per_year_coint_p_median": float(pp["coint_p"].median()),
        "per_year_frac_coint_5pct": float((pp["coint_p"] < 0.05).mean()),
        "universe_pairs_tested": n_pairs,
        "universe_pairs_cointegrated_5pct": n_coint,
    }
    print("=== diagnostics ===")
    print(json.dumps(diag, indent=2))
    pp.to_csv(RESULTS / "module4_per_year_coint.csv", index=False)

    # --- backtests ---
    runs = []

    # (a) rigorous OOS: rolling hedge ratio, z60, entry 2 / exit 0.5
    beta_roll = P.rolling_hedge_ratio(p1, p2, win=252)
    z_rig = P.spread_zscore(p1, p2, beta_roll, z_win=60)
    bt_rig = P.backtest_spread(p1, p2, z_rig, beta_roll, entry=2.0, exit_band=0.5,
                               cost_bps_leg=COST_BPS_LEG)
    m = perf(bt_rig["net"], "rigorous_OOS_rollbeta")
    m["roundtrips"] = n_roundtrips(bt_rig["pos"])
    m["sharpe_gross"] = float(S.sharpe_ratio(bt_rig["gross"].to_numpy(float), ANN))
    runs.append(m)

    # (b) strict train/test: beta from first 40%, trade last 60% only
    split = prices.index[int(0.4 * len(prices))]
    beta_tr, _, _ = P.engle_granger(p1.loc[:split], p2.loc[:split])
    beta_fixed = pd.Series(beta_tr, index=prices.index)
    z_fixed = P.spread_zscore(p1, p2, beta_fixed, z_win=60)
    bt_oos = P.backtest_spread(p1.loc[split:], p2.loc[split:], z_fixed.loc[split:],
                               beta_fixed.loc[split:], entry=2.0, exit_band=0.5,
                               cost_bps_leg=COST_BPS_LEG)
    m = perf(bt_oos["net"], "strict_train_test_OOS")
    m["roundtrips"] = n_roundtrips(bt_oos["pos"])
    m["sharpe_gross"] = float(S.sharpe_ratio(bt_oos["gross"].to_numpy(float), ANN))
    runs.append(m)

    # (c) video method: ratio MA5/MA20 z, bands +/-1, beta=1
    z_vid = P.video_ratio_zscore(p1, p2, fast=5, slow=20)
    beta_one = pd.Series(1.0, index=prices.index)
    bt_vid = P.backtest_spread(p1, p2, z_vid, beta_one, entry=1.0, exit_band=0.5,
                               cost_bps_leg=COST_BPS_LEG)
    m = perf(bt_vid["net"], "video_ratio_MA5_20")
    m["roundtrips"] = n_roundtrips(bt_vid["pos"])
    m["sharpe_gross"] = float(S.sharpe_ratio(bt_vid["gross"].to_numpy(float), ANN))
    runs.append(m)

    res = pd.DataFrame(runs)[["label", "n_days", "roundtrips", "sharpe_gross", "sharpe",
                              "hac_t", "ann_ret", "ann_vol", "total_return", "maxdd", "wf"]]
    res.to_csv(RESULTS / "module4_backtests.csv", index=False)
    json.dump(diag, open(RESULTS / "module4_diagnostics.json", "w"), indent=2)
    print("\n=== backtests (net of 5 bps/leg) ===")
    print(res.to_string(index=False))

    # --- figures ---
    # corr heatmap
    fig, ax = plt.subplots(figsize=(8, 6.5))
    im = ax.imshow(corr.values, cmap="RdYlGn", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr))); ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(corr))); ax.set_yticklabels(corr.columns, fontsize=8)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=6)
    ax.set_title("Module 4 — daily-return correlation (2011–2026)")
    fig.colorbar(im, ax=ax)
    fig.tight_layout(); fig.savefig(RESULTS / "fig_A_corr_heatmap.png", dpi=120); plt.close(fig)

    # spread z + positions
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True, height_ratios=[2, 1])
    a1.plot(z_rig.index, z_rig.values, lw=0.8, color="navy")
    for lev, ls in [(2, "--"), (-2, "--"), (0, "-")]:
        a1.axhline(lev, color="gray", ls=ls, lw=0.8)
    a1.set_ylabel("z-score (rolling-β log-spread)")
    a1.set_title("Module 4 — BRK-B/MSFT spread z-score and OOS positions")
    a2.plot(bt_rig.index, bt_rig["pos"], lw=0.8, color="darkgreen")
    a2.set_ylabel("position"); a2.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(RESULTS / "fig_B_spread_z.png", dpi=120); plt.close(fig)

    # equity curves
    fig, ax = plt.subplots(figsize=(11, 5))
    for bt, lab, col in [(bt_rig, "Rigorous OOS (rolling β)", "seagreen"),
                         (bt_oos, "Strict train/test OOS", "navy"),
                         (bt_vid, "Video method (ratio MA5/20)", "indianred")]:
        eq = (1 + bt["net"].fillna(0)).cumprod()
        ax.plot(eq.index, eq.values, lw=1.3, label=lab, color=col)
    ax.axhline(1, color="gray", lw=0.8)
    ax.set_title("Module 4 — pairs-trading equity, net 5 bps/leg (BRK-B/MSFT)")
    ax.set_ylabel("Equity (×, start = 1)"); ax.legend(); ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(RESULTS / "fig_C_equity.png", dpi=120); plt.close(fig)
    print("\nfigures:", [p.name for p in sorted(RESULTS.glob('fig_*.png'))])


if __name__ == "__main__":
    main()
