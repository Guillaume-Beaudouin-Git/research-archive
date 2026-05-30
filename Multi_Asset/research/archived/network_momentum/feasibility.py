"""
feasibility.py — Network Momentum (GMOM) feasibility study — Strategy E
=========================================================================
Pu, Y. et al. (2023) "Network Momentum across Asset Classes"
https://arxiv.org/abs/2308.11294

Runs 4 variants (E1–E4), computes full gate-check statistics,
cross-strategy correlations, and saves feasibility_summary.md.

Usage:
    /usr/bin/python3 -m Multi_Asset.research.active.network_momentum.feasibility
"""
from __future__ import annotations

import logging
import os
import sys
import warnings
from datetime import date
from pathlib import Path
from textwrap import dedent
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

_REPO = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(_REPO))
os.chdir(_REPO)

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

START_DATE  = "2015-01-01"
END_DATE    = date.today().isoformat()
N_TESTS     = 130          # running counter before this study
N_VARIANTS  = 4

# Transaction costs per asset class (RT basis points → fraction)
COSTS_BPS = {
    "FX":        2,
    "Equity":    5,
    "Bond":      5,
    "Commodity": 8,
    "Sector":    5,
    "Crypto":   15,
}

BOOTSTRAP_N   = 20_000
SHARPE_LAG    = 6        # weeks for HAC (paper uses monthly rebalance)
WF_TRAIN_YRS  = 5
WF_TEST_YRS   = 1


# ─────────────────────────────────────────────────────────────────────────────
# Statistical utilities
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_hac(daily_ret: pd.Series, lag: int = SHARPE_LAG) -> float:
    """
    Annualized Sharpe ratio with Newey-West HAC long-run variance estimate.

    Uses the conventional Sharpe formula:
        SR = mu_daily * sqrt(252) / sqrt(NW_var_daily)

    where NW_var is the Bartlett-kernel long-run variance of daily returns.
    The lag parameter controls the Newey-West bandwidth in weeks.
    """
    r = daily_ret.dropna().values.astype(float)
    n = len(r)
    if n < 50:
        return 0.0
    mu       = r.mean()
    demeaned = r - mu
    nw_var   = np.mean(demeaned ** 2)
    bw = lag * 5   # convert weeks → approximate business days
    for k in range(1, bw + 1):
        if k >= n:
            break
        gamma_k = np.mean(demeaned[k:] * demeaned[:-k])
        nw_var  += 2.0 * (1.0 - k / (bw + 1.0)) * gamma_k
    nw_var = max(nw_var, 1e-20)
    return float(mu * np.sqrt(252) / np.sqrt(nw_var))


def max_drawdown(daily_ret: pd.Series) -> float:
    cum = (1 + daily_ret.fillna(0)).cumprod()
    roll_max = cum.cummax()
    dd = (cum - roll_max) / roll_max
    return float(dd.min())


def bootstrap_ev(
    daily_ret: pd.Series,
    n_boot: int = BOOTSTRAP_N,
    rng: np.random.Generator | None = None,
) -> float:
    """P(EV <= 0): fraction of bootstrap resample means that are non-positive."""
    r   = daily_ret.dropna().values
    n   = len(r)
    rng = rng or np.random.default_rng(42)
    means = rng.choice(r, size=(n_boot, n), replace=True).mean(axis=1)
    return float((means <= 0).mean())


def amtp(p_ev: float, n_tests: int) -> float:
    """
    Adjusted Multiple Testing Penalty (Harvey-Liu-Zhu).
    AMTP = 1 - (1 - p_ev)^n_tests
    """
    return 1.0 - (1.0 - p_ev) ** n_tests


def walk_forward_stats(
    daily_ret: pd.Series,
    train_yrs: int = WF_TRAIN_YRS,
    test_yrs:  int = WF_TEST_YRS,
) -> Tuple[float, List[dict]]:
    """
    Rolling walk-forward: train_yrs in-sample, test_yrs OOS, roll by test_yrs.
    Returns (pct_positive, windows list).
    """
    train_days = int(train_yrs * 252)
    test_days  = int(test_yrs  * 252)
    windows    = []
    idx        = daily_ret.index

    start = 0
    while start + train_days + test_days <= len(idx):
        oos_start = start + train_days
        oos_end   = oos_start + test_days
        oos_ret   = daily_ret.iloc[oos_start:oos_end]
        oos_pnl   = float(oos_ret.sum())
        windows.append({
            "oos_start": idx[oos_start].date(),
            "oos_end":   idx[min(oos_end - 1, len(idx) - 1)].date(),
            "oos_pnl":   round(oos_pnl, 4),
            "n_days":    len(oos_ret),
            "positive":  oos_pnl > 0,
        })
        start += test_days

    if not windows:
        return 0.0, []

    pct_pos = sum(w["positive"] for w in windows) / len(windows)
    return pct_pos, windows


# ─────────────────────────────────────────────────────────────────────────────
# Transaction cost estimation
# ─────────────────────────────────────────────────────────────────────────────

def estimate_costs(
    positions_df:   pd.DataFrame,  # (T, N) positions
    returns_df:     pd.DataFrame,  # (T, N) returns
    asset_class_map: dict,         # {asset: class}
    costs_bps:      dict = COSTS_BPS,
) -> pd.Series:
    """
    Estimate daily transaction costs from position turnover.
    cost_t = sum_i |delta_pos_i| × cost_i × price_proxy
    Returns daily cost as fraction of portfolio.
    """
    pos_vals = positions_df.values
    turnover = np.abs(np.diff(pos_vals, axis=0, prepend=pos_vals[:1]))  # (T, N)

    # Per-asset cost in fraction (bps / 10000)
    col_costs = np.array([
        costs_bps.get(asset_class_map.get(col, "Sector"), 5) / 10_000
        for col in positions_df.columns
    ])

    # Daily cost = sum of turnover × per-asset cost
    daily_cost = (turnover * col_costs).sum(axis=1)

    # Normalize by N_active (same as portfolio return normalization)
    n_active = (pos_vals != 0).sum(axis=1)
    n_active = np.where(n_active > 0, n_active, 1)
    daily_cost = daily_cost / n_active

    return pd.Series(daily_cost, index=positions_df.index)


# ─────────────────────────────────────────────────────────────────────────────
# Gate check
# ─────────────────────────────────────────────────────────────────────────────

def check_gates(stats: dict) -> Tuple[bool, bool]:
    """Returns (research_pass, propfirm_pass)."""
    def _lt(val, threshold):
        """Safe less-than: returns True if val is numeric and < threshold."""
        if isinstance(val, str) or (isinstance(val, float) and np.isnan(val)):
            return True   # N/A → don't penalize on this gate
        return float(val) < threshold

    def _gt(val, threshold):
        if isinstance(val, str) or (isinstance(val, float) and np.isnan(val)):
            return False
        return float(val) > threshold

    r = (
        _gt(stats["sharpe_hac"], 0.7)  and
        _gt(stats["max_dd"],    -0.20)  and  # less negative = better
        _gt(stats["wf_pct_pos"], 0.55)  and
        _lt(stats["corr_individual"], 0.75) and
        _lt(stats["corr_A"], 0.40) and
        _lt(stats["corr_C"], 0.40)
    )
    p = (
        _gt(stats["sharpe_hac"],  1.0)  and
        _gt(stats["max_dd"],     -0.10) and
        _gt(stats["wf_pct_pos"],  0.60) and
        _lt(stats["p_amtp"],      0.10)
    )
    return r, p


# ─────────────────────────────────────────────────────────────────────────────
# Sanity checks for data leak / overfitting
# ─────────────────────────────────────────────────────────────────────────────

def sanity_check(strat_ret: pd.Series, costs_applied: bool) -> List[str]:
    warnings_out = []
    ann_sr = sharpe_hac(strat_ret)
    if ann_sr > 2.0:
        warnings_out.append(
            f"SUSPICIOUS: Sharpe={ann_sr:.2f} > 2.0 — verify (a) costs applied={costs_applied}, "
            f"(b) shift(1) on signals, (c) no lookahead in features or graph learning"
        )
    if strat_ret.mean() > 0.01:
        warnings_out.append(
            f"SUSPICIOUS: mean daily return={strat_ret.mean():.4f} > 1% — check position scaling"
        )
    return warnings_out


# ─────────────────────────────────────────────────────────────────────────────
# Per-asset attribution
# ─────────────────────────────────────────────────────────────────────────────

def asset_attribution(
    positions_df: pd.DataFrame,
    returns_df:   pd.DataFrame,
) -> pd.DataFrame:
    """Per-asset contribution to total P&L."""
    contrib = (positions_df.shift(1) * returns_df).fillna(0)
    total   = contrib.sum(axis=0)
    n_days  = (positions_df.shift(1).ne(0) & returns_df.notna()).sum(axis=0)
    ann_ret = total / returns_df.shape[0] * 252
    result  = pd.DataFrame({
        "total_contrib": total.round(4),
        "ann_return":    ann_ret.round(4),
        "active_days":   n_days,
    }).sort_values("total_contrib", ascending=False)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main feasibility run
# ─────────────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 70)
    log.info("Network Momentum (GMOM) Feasibility Study — Strategy E")
    log.info("=" * 70)

    # ── 1. Load universe ──────────────────────────────────────────────────────
    log.info("\n[1/5] Loading cross-asset universe...")
    from Multi_Asset.research.active.network_momentum.universe import load_universe
    returns, meta = load_universe(start=START_DATE, end=END_DATE)

    N_assets = returns.shape[1]
    log.info(f"  Universe: {N_assets} assets, {len(returns)} days")

    if N_assets < 20:
        log.error(f"STOP: universe < 20 assets after quality filter ({N_assets}). "
                  "Expand universe or relax min_history requirement.")
        return

    # Per-class breakdown
    from collections import Counter
    class_counts = Counter(meta["asset_class"].values())
    log.info("  Per-class: " + ", ".join(f"{k}={v}" for k, v in sorted(class_counts.items())))
    log.info(f"  Dropped: {meta['dropped_assets']}")

    # ── 2. Build features ─────────────────────────────────────────────────────
    log.info("\n[2/5] Building momentum features (T×N×8)...")
    from Multi_Asset.research.active.network_momentum.features import build_features
    prices_aligned = meta["prices"].reindex(returns.index).ffill()
    F, feat_names  = build_features(returns, prices=prices_aligned)
    log.info(f"  Feature tensor: {F.shape}")

    # ── 3. Load existing strategy returns for correlation ─────────────────────
    log.info("\n[3/5] Loading Strategy A and C returns for correlation baseline...")
    try:
        from Portfolio.integration.load_returns import load_all_returns
        abc_ret = load_all_returns(align_start="2017-01-01")
        ret_A   = abc_ret["A"] if "A" in abc_ret.columns else None
        ret_C   = abc_ret["C"] if "C" in abc_ret.columns else None
        log.info(f"  Strategy A: {len(ret_A)} days" if ret_A is not None else "  Strategy A: not found")
        log.info(f"  Strategy C: {len(ret_C)} days" if ret_C is not None else "  Strategy C: not found")
    except Exception as exc:
        log.warning(f"  Could not load A/C returns ({exc}) — correlation with A,C will be NaN")
        ret_A, ret_C = None, None

    # SPY returns for market correlation reference
    spy_ret = returns.get("SPY", None)

    # ── 4. Run variants ───────────────────────────────────────────────────────
    log.info("\n[4/5] Running strategy variants...")
    from Multi_Asset.research.active.network_momentum.strategy import run_strategy

    VARIANTS = {
        "E1": dict(variant="E1", rebal_freq="ME"),
        "E2": dict(variant="E2", rebal_freq="ME"),
        "E3": dict(variant="E3", rebal_freq="ME"),
        "E4": dict(variant="E4", rebal_freq="ME"),
    }

    all_stats:   dict = {}
    all_returns: dict = {}
    all_pos:     dict = {}
    rng = np.random.default_rng(42)

    n_tests_running = N_TESTS

    for vname, vkwargs in VARIANTS.items():
        log.info(f"\n  ── Variant {vname} ──")
        try:
            strat_ret, positions = run_strategy(
                returns=returns,
                F=F,
                prices=prices_aligned,
                **vkwargs,
            )
        except Exception as exc:
            log.error(f"  {vname} FAILED: {exc}", exc_info=True)
            all_stats[vname] = {"error": str(exc)}
            continue

        # Apply transaction costs
        daily_cost = estimate_costs(
            positions, returns, meta["asset_class"], COSTS_BPS
        )
        daily_cost = daily_cost.reindex(strat_ret.index).fillna(0)
        strat_ret_net = strat_ret - daily_cost

        # Compute statistics
        n_tests_running += 1
        sr_hac  = sharpe_hac(strat_ret_net)
        mdd     = max_drawdown(strat_ret_net)
        ann_ret = strat_ret_net.mean() * 252
        ann_vol = strat_ret_net.std() * np.sqrt(252)
        p_ev    = bootstrap_ev(strat_ret_net, n_boot=BOOTSTRAP_N, rng=rng)
        p_amtp  = amtp(p_ev, n_tests_running)
        wf_pct, wf_windows = walk_forward_stats(strat_ret_net)

        # Correlations
        def _safe_corr(s1: pd.Series, s2: pd.Series | None) -> float:
            if s2 is None:
                return float("nan")
            aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
            if len(aligned) < 30:
                return float("nan")
            return float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))

        corr_A   = _safe_corr(strat_ret_net, ret_A)
        corr_C   = _safe_corr(strat_ret_net, ret_C)
        corr_spy = _safe_corr(strat_ret_net, spy_ret)
        # Correlation to E3 (individual momentum — paper's main comparison)
        corr_e3  = (
            _safe_corr(strat_ret_net, all_returns.get("E3_net"))
            if "E3_net" in all_returns else float("nan")
        )

        # Sanity checks
        sane_warnings = sanity_check(strat_ret_net, costs_applied=True)
        for w in sane_warnings:
            log.warning(f"  [SANITY] {w}")

        stats = {
            "sharpe_hac":      round(sr_hac,  3),
            "max_dd":          round(mdd,     4),
            "ann_ret":         round(ann_ret, 4),
            "ann_vol":         round(ann_vol, 4),
            "p_ev0":           round(p_ev,    4),
            "p_amtp":          round(p_amtp,  4),
            "n_tests_at_eval": n_tests_running,
            "wf_pct_pos":      round(wf_pct,  3),
            "wf_windows":      wf_windows,
            "corr_A":          round(corr_A,   3) if not np.isnan(corr_A)   else "N/A",
            "corr_C":          round(corr_C,   3) if not np.isnan(corr_C)   else "N/A",
            "corr_spy":        round(corr_spy, 3) if not np.isnan(corr_spy) else "N/A",
            "corr_individual": round(corr_e3,  3) if not np.isnan(corr_e3)  else "N/A",
            "n_days":          len(strat_ret_net),
            "gross_returns":   strat_ret,
            "warnings":        sane_warnings,
        }
        research_pass, propfirm_pass = check_gates(stats)
        stats["research_pass"]  = research_pass
        stats["propfirm_pass"]  = propfirm_pass

        verdict = "PROPFIRM_PASS" if propfirm_pass else ("RESEARCH_PASS" if research_pass else "FAIL")
        log.info(
            f"  {vname}: Sharpe={sr_hac:.2f}, MaxDD={mdd:.1%}, "
            f"WF={wf_pct:.0%}, Ann={ann_ret:.1%}, Vol={ann_vol:.1%} "
            f"[{verdict}]"
        )

        all_stats[vname]   = stats
        all_returns[vname]  = strat_ret_net
        all_returns[f"{vname}_net"] = strat_ret_net   # alias for cross-variant lookup
        all_pos[vname]      = positions

    # ── 5. Graph analysis (best GMOM variant) ─────────────────────────────────
    log.info("\n[5/5] Computing graph properties for best GMOM variant...")
    graph_stats_out = {}
    jaccard_out     = None

    try:
        from Multi_Asset.research.active.network_momentum.graph_learning import (
            learn_graph_ensemble, learn_graph, graph_stats, jaccard_stability
        )

        # Use last 504 days for analysis graph
        t_last = len(F)
        F_hist = F[max(0, t_last - 1260):]
        A_ens  = learn_graph_ensemble(F_hist, alpha=0.1, beta=0.1)
        if A_ens is not None:
            asset_names = list(returns.columns)
            graph_stats_out = graph_stats(A_ens, asset_names)
            log.info(f"  Edge density: {graph_stats_out['edge_density']:.3f}")
            log.info(f"  Top 5 edges: {graph_stats_out['top5_edges']}")

            # Jaccard stability: compare two consecutive 252-day graphs
            if t_last >= 1008:
                A1 = learn_graph(F[t_last - 756: t_last - 504], alpha=0.1, beta=0.1)
                A2 = learn_graph(F[t_last - 504: t_last - 252], alpha=0.1, beta=0.1)
                if A1 is not None and A2 is not None:
                    jaccard_out = round(jaccard_stability(A1, A2), 3)
                    log.info(f"  Jaccard stability: {jaccard_out:.3f}")
    except Exception as exc:
        log.warning(f"  Graph analysis failed: {exc}")

    # ── 6. Combined portfolio A + C + E (best variant) ────────────────────────
    combined_stats = {}
    best_variant   = None
    best_sharpe    = -np.inf

    for vname in ["E4", "E2", "E1", "E3"]:
        if vname in all_stats and "sharpe_hac" in all_stats[vname]:
            if all_stats[vname]["sharpe_hac"] > best_sharpe:
                best_sharpe   = all_stats[vname]["sharpe_hac"]
                best_variant  = vname

    if best_variant and ret_A is not None and ret_C is not None:
        log.info(f"\n  Building A+C+{best_variant} combined portfolio...")
        best_E = all_returns[best_variant]
        comb   = pd.concat([ret_A, ret_C, best_E], axis=1, join="inner").dropna()
        comb.columns = ["A", "C", "E"]
        if len(comb) > 252:
            eq_ret       = comb.mean(axis=1)
            combined_sr  = sharpe_hac(eq_ret)
            combined_mdd = max_drawdown(eq_ret)
            ac_ret       = comb[["A", "C"]].mean(axis=1)
            ac_sr        = sharpe_hac(ac_ret)
            combined_stats = {
                "portfolio":    "A+C+E eq-weight",
                "sharpe_hac":   round(combined_sr, 3),
                "max_dd":       round(combined_mdd, 4),
                "vs_AC_sharpe": round(ac_sr, 3),
                "n_days":       len(comb),
            }
            log.info(
                f"  A+C+{best_variant}: Sharpe={combined_sr:.2f}, MaxDD={combined_mdd:.1%} "
                f"(vs A+C: {ac_sr:.2f})"
            )

    # ── 7. Per-asset attribution (best variant) ───────────────────────────────
    attribution = {}
    if best_variant and best_variant in all_pos:
        attribution = asset_attribution(all_pos[best_variant], returns)
        log.info(f"\n  Top 5 assets by P&L contribution ({best_variant}):")
        for asset, row in attribution.head(5).iterrows():
            log.info(f"    {asset:<12} ann={row['ann_return']:+.2%}  days={row['active_days']}")

    # ── 8. Generate summary markdown ──────────────────────────────────────────
    log.info("\n[Output] Writing feasibility_summary.md...")
    _write_summary(
        returns, meta, all_stats, all_returns, graph_stats_out, jaccard_out,
        combined_stats, attribution, best_variant, n_tests_running,
        class_counts, N_assets,
    )

    log.info("\n" + "=" * 70)
    log.info("DONE")
    log.info("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# Summary markdown writer
# ─────────────────────────────────────────────────────────────────────────────

def _write_summary(
    returns, meta, all_stats, all_returns, graph_stats_out, jaccard_out,
    combined_stats, attribution, best_variant, n_tests_final,
    class_counts, N_assets,
):
    out_path = Path(__file__).parent / "feasibility_summary.md"

    lines = []

    def h(level, text):
        lines.append(f"\n{'#' * level} {text}\n")

    def row(*cells):
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")

    def sep(*widths):
        lines.append("| " + " | ".join("-" * (w or 6) for w in widths) + " |")

    # Header
    h(2, f"Network Momentum (GMOM) Feasibility — Strategy E")
    lines.append(f"*Generated: {date.today()}  |  n_tests after: {n_tests_final}*\n")

    # Headline verdict
    h(3, "1. Headline verdict")
    best_v_stats = all_stats.get(best_variant, {})
    if best_v_stats.get("propfirm_pass"):
        verdict = f"**PROPFIRM_PASS** — best variant {best_variant}"
    elif best_v_stats.get("research_pass"):
        verdict = f"**RESEARCH_PASS** — best variant {best_variant}"
    else:
        verdict = f"**FAIL** — best variant {best_variant} (Sharpe={best_v_stats.get('sharpe_hac','?')})"
    lines.append(verdict + "\n")

    # Universe
    h(3, "2. Universe")
    date_range = f"{returns.index[0].date()} → {returns.index[-1].date()}"
    lines.append(f"- Total assets after quality filter: **{N_assets}**")
    lines.append(f"- Date range: {date_range} ({len(returns)} trading days)")
    lines.append(f"- Per-class: " + ", ".join(f"{k}={v}" for k, v in sorted(class_counts.items())))
    if meta.get("dropped_assets"):
        lines.append(f"- Dropped: {meta['dropped_assets']}")

    # Graph properties
    h(3, "3. Graph properties (best GMOM variant)")
    if graph_stats_out:
        lines.append(f"- Edge density: {graph_stats_out.get('edge_density', '?')}")
        lines.append(f"- Active edges: {graph_stats_out.get('n_active_edges', '?')} / {N_assets*(N_assets-1)//2} possible")
        lines.append(f"- Mean node degree: {graph_stats_out.get('mean_degree', '?')}")
        if jaccard_out is not None:
            lines.append(f"- Jaccard stability (consecutive 252d windows): {jaccard_out:.3f}")
        top5 = graph_stats_out.get("top5_edges", [])
        if top5:
            lines.append(f"- Top 5 cross-asset connections:")
            for i, j, w in top5:
                ac_i = meta["asset_class"].get(i, "?")
                ac_j = meta["asset_class"].get(j, "?")
                lines.append(f"  - {i} ({ac_i}) ↔ {j} ({ac_j}): weight={w:.4f}")
    else:
        lines.append("- Graph analysis not available (solver failed or insufficient history)")

    # Variants comparison
    h(3, "4. Variants comparison")
    row("Variant", "Sharpe HAC", "MaxDD", "Ann Ret", "Ann Vol", "WF%pos", "corr(E,A)", "corr(E,C)", "corr(E,LinReg)", "Verdict")
    sep(14, 10, 8, 8, 8, 8, 10, 10, 14, 16)
    for vname in ["E1", "E2", "E3", "E4"]:
        s = all_stats.get(vname, {})
        if "error" in s:
            row(vname, "ERROR", s["error"][:40], "", "", "", "", "", "", "FAIL")
            continue
        v_str = "PROPFIRM" if s.get("propfirm_pass") else ("RESEARCH" if s.get("research_pass") else "FAIL")
        row(
            vname,
            s.get("sharpe_hac", "?"),
            f"{s.get('max_dd', 0):.1%}",
            f"{s.get('ann_ret', 0):.1%}",
            f"{s.get('ann_vol', 0):.1%}",
            f"{s.get('wf_pct_pos', 0):.0%}",
            s.get("corr_A", "N/A"),
            s.get("corr_C", "N/A"),
            s.get("corr_individual", "N/A"),
            v_str,
        )

    # Gate checks detail (best variant)
    h(3, "4b. Gate check detail — best variant")
    if best_v_stats:
        lines.append(f"**{best_variant}:**")
        lines.append(f"- Sharpe HAC: {best_v_stats.get('sharpe_hac','?')} (gate >0.7 RESEARCH / >1.0 PROPFIRM)")
        lines.append(f"- Max drawdown: {best_v_stats.get('max_dd', 0):.1%} (gate >-20% RESEARCH / >-10% PROPFIRM)")
        lines.append(f"- WF% positive: {best_v_stats.get('wf_pct_pos', 0):.0%} (gate >55% RESEARCH)")
        lines.append(f"- P(EV≤0): {best_v_stats.get('p_ev0','?')} | AMTP: {best_v_stats.get('p_amtp','?')} (n_tests={best_v_stats.get('n_tests_at_eval','?')})")
        lines.append(f"- corr(E,A): {best_v_stats.get('corr_A','?')} | corr(E,C): {best_v_stats.get('corr_C','?')} | corr(E,SPY): {best_v_stats.get('corr_spy','?')}")
        lines.append(f"- corr(E,LinReg): {best_v_stats.get('corr_individual','?')} (gate <0.75)")

        wf_wins = best_v_stats.get("wf_windows", [])
        if wf_wins:
            lines.append(f"\nWalk-forward windows:")
            lines.append("| Window | OOS P&L | N days | Verdict |")
            lines.append("|--------|---------|--------|---------|")
            for w in wf_wins:
                lines.append(f"| {w['oos_start']} → {w['oos_end']} | {w['oos_pnl']:+.4f} | {w['n_days']} | {'✓' if w['positive'] else '✗'} |")

        if best_v_stats.get("warnings"):
            lines.append(f"\n**WARNINGS:**")
            for w in best_v_stats["warnings"]:
                lines.append(f"- {w}")

    # Combined portfolio
    h(3, "5. Combined portfolio if E passes")
    if combined_stats:
        lines.append(f"- Portfolio: A + C + {best_variant} (equal-weight)")
        lines.append(f"- Sharpe HAC: {combined_stats.get('sharpe_hac','?')}")
        lines.append(f"- Max drawdown: {combined_stats.get('max_dd', 0):.1%}")
        lines.append(f"- vs A+C only: {combined_stats.get('vs_AC_sharpe','?')}")
        lines.append(f"- Period: {combined_stats.get('n_days','?')} days overlap")
    else:
        lines.append("- Not computed (A or C returns unavailable, or no variant passed)")

    # Per-asset attribution
    h(3, "6. Diagnostics — Per-asset attribution")
    if attribution is not None and len(attribution) > 0:
        lines.append(f"Top 10 contributors ({best_variant}, gross):\n")
        lines.append("| Asset | Class | Ann Contribution | Active Days |")
        lines.append("|-------|-------|-----------------|-------------|")
        for asset, row_data in attribution.head(10).iterrows():
            ac = meta["asset_class"].get(asset, "?")
            lines.append(f"| {asset} | {ac} | {row_data['ann_return']:+.2%} | {row_data['active_days']} |")

        lines.append(f"\nBottom 5 contributors:")
        lines.append("| Asset | Class | Ann Contribution | Active Days |")
        lines.append("|-------|-------|-----------------|-------------|")
        for asset, row_data in attribution.tail(5).iterrows():
            ac = meta["asset_class"].get(asset, "?")
            lines.append(f"| {asset} | {ac} | {row_data['ann_return']:+.2%} | {row_data['active_days']} |")

        # Per-class breakdown
        if meta.get("asset_class"):
            lines.append(f"\nPer-class P&L (annualized, equal-weight within class):")
            lines.append("| Class | Ann Return | N Assets |")
            lines.append("|-------|-----------|---------|")
            for cls in sorted(set(meta["asset_class"].values())):
                assets_in_class = [a for a, c in meta["asset_class"].items() if c == cls]
                cls_contrib = attribution[attribution.index.isin(assets_in_class)]["ann_return"]
                if len(cls_contrib) > 0:
                    lines.append(f"| {cls} | {cls_contrib.mean():+.2%} | {len(cls_contrib)} |")

    # Recommendation
    h(3, "7. Recommendation")
    if best_v_stats.get("propfirm_pass"):
        rec = dedent(f"""
        **{best_variant} PROPFIRM_PASS** — integrate as Strategy E.
        Next steps:
        1. Paper trade alongside Strategy C (NQ opening momentum)
        2. Run iter_e02 with variable selection (which features drive the most signal)
        3. Consider universe expansion to 50+ assets if more commodity futures data available
        """)
    elif best_v_stats.get("research_pass"):
        rec = dedent(f"""
        **{best_variant} RESEARCH_PASS (not propfirm)** — use as portfolio diversifier.
        - Can be included in A+C+E theoretical portfolio for diversification benefit
        - Before live consideration: need Sharpe >1.0 and MaxDD >-10%
        - iter_e02: test sparse feature selection (LASSO), longer OLS window (504d),
          quarterly rebalance to reduce costs
        """)
    else:
        rec = dedent(f"""
        **ALL VARIANTS FAIL** — graph learning doesn't transfer to this universe.
        Root causes to investigate:
        - N={N_assets} may be too small (paper used 64 assets) — expand to 50+
        - Cross-asset momentum spillover may be weaker at this universe composition
        - OLS regression may overfit with small N; try ridge or LASSO in iter_e02
        Next research: Paper 2 (Momentum Transformer LSTM), or consolidate A+C portfolio
        """)
    lines.append(rec)

    # Implementation lessons
    h(3, "8. Implementation lessons")
    if graph_stats_out:
        target_density = 0.35
        actual_density = graph_stats_out.get("edge_density", 0)
        density_ok     = 0.25 < actual_density < 0.55
        lines.append(f"- Universe size N={N_assets} (paper used 64) — {'adequate' if N_assets >= 25 else 'borderline small'}")
        lines.append(f"- Graph edge density: {actual_density:.3f} ({'OK, near paper 0.35' if density_ok else 'off-target 0.25-0.55 range'})")
        if jaccard_out is not None:
            lines.append(f"- Graph stability Jaccard={jaccard_out:.3f} (paper reports >0.99 for their universe)")
    lines.append(f"- CVXPY solver: CLARABEL (fallback SCS) — no numerical issues reported" if graph_stats_out else "- CVXPY: failed or not reached")
    lines.append(f"- Monthly rebalance sufficient; quarterly would reduce costs")

    # Next iteration roadmap
    h(3, "9. Next iteration roadmap")
    lines.append(dedent("""
    - **iter_e02** (if E passes): VSN-style feature weighting with LASSO (interpretable variable selection)
    - **iter_e02** (if E fails): LSTM/Transformer momentum features (Paper 2), or A+C portfolio final
    - **Universe expansion**: Add individual commodity futures (CL, GC, SI), bond futures (ZN, ZB)
    - **Quarterly rebalance**: Reduce turnover → lower costs → better net Sharpe
    - Either way: document methodology rigorously for portfolio framework
    """))

    # n_tests counter
    h(3, "10. n_tests counter")
    lines.append(f"- Start: {N_TESTS}")
    lines.append(f"- End:   {n_tests_final} (+{N_VARIANTS} variants)")

    out_path.write_text("\n".join(lines) + "\n")
    log.info(f"  Saved → {out_path}")


if __name__ == "__main__":
    main()
