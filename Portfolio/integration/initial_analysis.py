"""
initial_analysis.py — Portfolio Integration Phase 1
=====================================================
Loads A/B/C returns, computes combined portfolio diagnostics, identifies
integration blockers, saves initial_summary.md.

Run:
    /usr/bin/python3 -m Portfolio.integration.initial_analysis
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Portfolio.integration.load_returns import load_all_returns, CAPITAL_A, CAPITAL_B, CAPITAL_C
from Portfolio.risk.correlation import (
    rolling_correlation_matrix, rolling_correlation_history,
    correlation_alert, diversification_ratio,
)
from Portfolio.risk.sizing import (
    equal_risk_contribution, inverse_vol_weighting,
    risk_contribution_breakdown, scale_to_target_vol,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

STRATEGY_META = {
    "A": {"name": "TSMOM v3", "source": "backtest (live 17d proxy)",
          "capital": CAPITAL_A, "asset_class": "crypto"},
    "B": {"name": "Delta-neutral carry", "source": "backtest (live 4d proxy)",
          "capital": CAPITAL_B, "asset_class": "crypto-carry"},
    "C": {"name": "NQ opening momentum", "source": "backtest (iter_05 A$400+B1.2%)",
          "capital": CAPITAL_C, "asset_class": "futures"},
}

TARGET_VOL = 0.10   # 10% annualised portfolio vol target


# ─────────────────────────────────────────────────────────────────────────────
# Analytics helpers
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_hac(ret: pd.Series) -> float:
    """HAC Sharpe if n >= 48, else plain."""
    r = ret.dropna()
    n = len(r)
    if n < 2:
        return float("nan")
    if n >= 48:
        try:
            exog = sm.add_constant(np.ones(n))
            res  = sm.OLS(r.values, exog).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
            lrv  = float(res.cov_params()[1, 1]) * n
            lrv  = max(lrv, 1e-12)
            return float(r.mean() / np.sqrt(lrv) * np.sqrt(252))
        except Exception:
            pass
    return float(r.mean() / r.std() * np.sqrt(252))


def maxdd(ret: pd.Series) -> float:
    cum = (1 + ret).cumprod()
    running_max = cum.cummax()
    dd = (cum - running_max) / running_max
    return float(dd.min())


def per_strategy_stats(returns_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in returns_df.columns:
        r = returns_df[col].dropna()
        r_nz = r[r != 0]   # exclude fill-value zeros for vol/Sharpe
        ann_ret  = float(r_nz.mean() * 252)
        ann_vol  = float(r_nz.std()  * np.sqrt(252))
        sh_hac   = sharpe_hac(r_nz)
        mdd      = maxdd(r_nz.cumsum() / r_nz.cumsum().abs().max())  # DD on cum PnL
        # Simpler: just use cumulative sum for drawdown on fractional returns
        cum = r_nz.cumsum()
        peak = cum.cummax()
        dd_series = (cum - peak)
        mdd_val  = float(dd_series.min())

        meta = STRATEGY_META.get(col, {})
        rows.append({
            "strategy":   col,
            "name":       meta.get("name", col),
            "source":     meta.get("source", "?"),
            "start":      str(r_nz.index[0].date()),
            "end":        str(r_nz.index[-1].date()),
            "n_obs":      len(r_nz),
            "ann_ret":    ann_ret,
            "ann_vol":    ann_vol,
            "sharpe_hac": sh_hac,
            "max_dd":     mdd_val,
        })
    return pd.DataFrame(rows).set_index("strategy")


def portfolio_stats(port_ret: pd.Series, label: str) -> dict:
    r = port_ret.dropna()
    ann_ret = float(r.mean() * 252)
    ann_vol = float(r.std() * np.sqrt(252))
    sh      = sharpe_hac(r)
    mdd_val = maxdd(r)
    dr      = float("nan")   # computed separately
    return {
        "label":    label,
        "ann_ret":  ann_ret,
        "ann_vol":  ann_vol,
        "sharpe":   sh,
        "max_dd":   mdd_val,
    }


def compute_portfolio_return(returns_df: pd.DataFrame,
                              weights: dict) -> pd.Series:
    strats = list(weights.keys())
    port = sum(returns_df[s] * weights[s]
               for s in strats if s in returns_df.columns)
    return port


# ─────────────────────────────────────────────────────────────────────────────
# Integration blockers check
# ─────────────────────────────────────────────────────────────────────────────

def check_integration_blockers(returns_df: pd.DataFrame) -> list:
    blockers = []

    # A) Date alignment
    starts = {c: returns_df[c][returns_df[c] != 0].index.min() for c in returns_df.columns}
    ends   = {c: returns_df[c][returns_df[c] != 0].index.max() for c in returns_df.columns}
    min_start = max(starts.values())
    max_end   = min(ends.values())
    overlap_days = len(returns_df[(returns_df.index >= min_start) & (returns_df.index <= max_end)])
    if overlap_days < 60:
        blockers.append({
            "issue": "A",
            "severity": "HIGH",
            "description": f"Overlap of all 3 strategies only {overlap_days} days "
                          f"({min_start.date()} → {max_end.date()}). "
                          f"ERC covariance estimate unreliable with < 60 days.",
            "resolution": "Use full individual history for each strategy; apply ERC "
                         "only on overlapping period or use inverse-vol as fallback."
        })
    else:
        blockers.append({
            "issue": "A",
            "severity": "OK",
            "description": f"Date overlap: {overlap_days} days ({min_start.date()} → {max_end.date()}). Sufficient.",
            "resolution": "None."
        })

    # B) Frequency
    blockers.append({
        "issue": "B",
        "severity": "OK",
        "description": "All strategies: daily frequency. "
                       "B aggregated from 8h → daily (summation, not averaging).",
        "resolution": "None."
    })

    # C) Currency
    blockers.append({
        "issue": "C",
        "severity": "LOW",
        "description": "A in USDC (Propr), B in USDC (Binance/HL), C in USD (NQ). "
                       "USDC ≈ USD (peg). No conversion needed.",
        "resolution": "Treat as identical. Monitor depeg risk."
    })

    # D) Capital base
    capitals = {c: STRATEGY_META[c]["capital"] for c in ["A", "B", "C"]}
    blockers.append({
        "issue": "D",
        "severity": "LOW",
        "description": f"Capital bases differ: A=${capitals['A']:,.0f}, "
                       f"B=${capitals['B']:,.0f} (backtest notional, not real), "
                       f"C=${capitals['C']:,.0f}. "
                       f"All returns already normalised to fractional (÷ capital). "
                       f"B backtest uses $500 — if live account is $1000, "
                       f"scale B returns by 2×.",
        "resolution": "Document capital scaling factor per strategy at deployment."
    })

    # E) Live vs backtest
    live_days = {"A": 17, "B": 4, "C": 0}
    blockers.append({
        "issue": "E",
        "severity": "MEDIUM",
        "description": "All 3 strategies use backtest data as proxy. "
                       f"Live history: A={live_days['A']}d, B={live_days['B']}d, C=0d. "
                       f"Backtest P&L for A/B will be higher than live "
                       f"(no slippage on crypto, model assumes ideal execution). "
                       f"Correlations estimated on backtest may differ in live trading.",
        "resolution": "Re-run Phase 1 analysis after 60 live trading days per strategy. "
                     "Until then, treat correlation estimates as approximate."
    })

    # F) Missing data / zeros
    for c in returns_df.columns:
        zero_pct = (returns_df[c] == 0).mean()
        if zero_pct > 0.50:
            blockers.append({
                "issue": "F",
                "severity": "LOW",
                "description": f"Strategy {c}: {zero_pct*100:.0f}% zero returns "
                               f"(expected for infrequent-trading strategies). "
                               f"Using non-zero-only slice for Sharpe/vol computation.",
                "resolution": "OK for backtest. Monitor live fill rate."
            })

    return blockers


# ─────────────────────────────────────────────────────────────────────────────
# Correlation rolling history
# ─────────────────────────────────────────────────────────────────────────────

def rolling_corr_summary(returns_df: pd.DataFrame, window: int = 60) -> dict:
    pairs = [("A", "B"), ("A", "C"), ("B", "C")]
    summary = {}
    for p in pairs:
        try:
            hist = rolling_correlation_history(returns_df, p, window=window)
            summary[p] = {
                "mean": float(hist.mean()),
                "max":  float(hist.max()),
                "min":  float(hist.min()),
                "pct_above_05": float((hist.abs() > 0.5).mean()),
            }
        except Exception as e:
            log.warning(f"Rolling corr {p} failed: {e}")
            summary[p] = {}
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=== Portfolio Integration Phase 1 ===")

    # ── Load returns ──────────────────────────────────────────────────────────
    returns_df = load_all_returns(align_start="2023-01-01")
    log.info(f"Combined returns loaded: {returns_df.shape}")

    # Use only non-zero observations for per-strategy stats
    # (C has many 0s from non-trading days)
    stats_df = per_strategy_stats(returns_df)

    # ── Individual strategy stats ─────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("STEP 1 — INDIVIDUAL STRATEGY STATISTICS")
    print("=" * 100)
    print(f"\n  {'Strategy':<6} {'Name':<22} {'Source':<30} {'Period':<22} "
          f"{'N':>5} {'AnnRet':>8} {'AnnVol':>8} {'Sharpe':>8} {'MaxDD':>8}")
    print("  " + "-" * 95)
    for s, row in stats_df.iterrows():
        period = f"{row['start']} → {row['end']}"
        print(f"  {s:<6} {row['name']:<22} {row['source']:<30} {period:<22} "
              f"{int(row['n_obs']):>5} {row['ann_ret']*100:>+7.1f}% "
              f"{row['ann_vol']*100:>7.1f}% {row['sharpe_hac']:>8.3f} "
              f"{row['max_dd']*100:>+7.1f}%")

    # ── Correlation matrix ────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("STEP 2 — CORRELATION MATRIX")
    print("=" * 100)

    # Use non-zero days only for correlation
    ret_nz = returns_df.copy()
    for c in ret_nz.columns:
        ret_nz.loc[ret_nz[c] == 0, c] = np.nan

    corr_full = ret_nz.corr()
    print("\n  Full-sample pairwise Pearson correlation (non-zero days):")
    print(corr_full.round(4).to_string(col_space=10))

    corr_recent = rolling_correlation_matrix(ret_nz.dropna(how="all"), window=60)
    print(f"\n  Rolling 60-day correlation (most recent window):")
    print(corr_recent.round(4).to_string(col_space=10))

    alerts = correlation_alert(corr_full, threshold=0.5)
    if alerts:
        print(f"\n  ⚠ Correlation alerts (|corr| > 0.5):")
        for a in alerts:
            print(f"    {a['pair']}: {a['correlation']:+.3f}  [{a['severity']}]")
    else:
        print(f"\n  No correlation alerts (all pairs |corr| < 0.5). ✓")

    # Rolling correlation history
    roll_summary = rolling_corr_summary(ret_nz.dropna(how="all"), window=60)
    print(f"\n  Rolling 60-day correlation summary:")
    print(f"  {'Pair':<8} {'Mean':>8} {'Max':>8} {'Min':>8} {'%>0.5':>8}")
    print("  " + "-" * 42)
    for (p1, p2), s in roll_summary.items():
        if s:
            print(f"  {p1+'-'+p2:<8} {s['mean']:>+8.3f} {s['max']:>+8.3f} "
                  f"{s['min']:>+8.3f} {s['pct_above_05']*100:>7.1f}%")

    # ── Diversification ratio ─────────────────────────────────────────────────
    ret_overlap = ret_nz.dropna(how="any")
    dr_ew = diversification_ratio(ret_nz.dropna(how="all"),
                                   weights={"A": 1/3, "B": 1/3, "C": 1/3})
    print(f"\n  Diversification ratio (equal-weighted): {dr_ew:.3f}")
    dr_label = ("Excellent (>2.0)" if dr_ew > 2.0 else
                "Strong (1.5-2.0)" if dr_ew > 1.5 else
                "Moderate (1.0-1.5)" if dr_ew > 1.0 else
                "Weak (<1.0, strategies too correlated)")
    print(f"  Assessment: {dr_label}")

    # ── Portfolio construction ────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("STEP 3 — PORTFOLIO CONSTRUCTION COMPARISON")
    print("=" * 100)

    # Equal-weighted
    w_ew = {"A": 1/3, "B": 1/3, "C": 1/3}
    port_ew = compute_portfolio_return(returns_df, w_ew)
    s_ew = portfolio_stats(port_ew[port_ew != 0], "Equal-weighted (33/33/33)")

    # For ERC/inverse-vol: use overlap period where all 3 have data
    # (most-recent 63d window falls after B/C data ends → covariance degenerate)
    overlap_start = max(
        ret_nz["A"].dropna().index.min(),
        ret_nz["B"].dropna().index.min(),
        ret_nz["C"].dropna().index.min(),
    )
    overlap_end = min(
        ret_nz["A"].dropna().index.max(),
        ret_nz["B"].dropna().index.max(),
        ret_nz["C"].dropna().index.max(),
    )
    # Use full returns (including zeros = "flat") for covariance estimation.
    # ret_nz has zeros→NaN; dropna(how="any") would keep only co-active days (~49).
    # Correct approach: use returns_df (zeros preserved) over the overlap period.
    ret_overlap = returns_df[(returns_df.index >= overlap_start) & (returns_df.index <= overlap_end)]
    log.info(f"Overlap for ERC estimation: {len(ret_overlap)} days "
             f"({overlap_start.date()} → {overlap_end.date()})")

    # Inverse-vol
    w_iv = inverse_vol_weighting(ret_overlap, target_vol=TARGET_VOL, window=len(ret_overlap))
    port_iv = compute_portfolio_return(returns_df, w_iv)
    s_iv = portfolio_stats(port_iv[port_iv != 0], "Inverse-vol")

    # ERC
    try:
        w_erc = equal_risk_contribution(ret_overlap, target_vol=TARGET_VOL,
                                         window=len(ret_overlap))
        port_erc = compute_portfolio_return(returns_df, w_erc)
        s_erc = portfolio_stats(port_erc[port_erc != 0], "ERC")
    except Exception as e:
        log.warning(f"ERC failed: {e}")
        w_erc = w_ew.copy()
        port_erc = port_ew.copy()
        s_erc = {"label": "ERC (fallback=EW)", "ann_ret": s_ew["ann_ret"],
                 "ann_vol": s_ew["ann_vol"], "sharpe": s_ew["sharpe"],
                 "max_dd": s_ew["max_dd"]}

    # ERC scaled to 10% vol target
    scale_factor = TARGET_VOL / max(s_erc["ann_vol"], 1e-6)
    w_erc_scaled = {s: w * scale_factor for s, w in w_erc.items()}
    port_erc_scaled = compute_portfolio_return(returns_df, w_erc_scaled)
    s_erc_scaled = portfolio_stats(port_erc_scaled[port_erc_scaled != 0],
                                    f"ERC 10%vol (×{scale_factor:.2f})")

    # Diversification ratios
    dr_erc = diversification_ratio(ret_nz.dropna(how="all"), weights=w_erc)
    dr_iv  = diversification_ratio(ret_nz.dropna(how="all"), weights=w_iv)

    portfolios = [
        (s_ew,  w_ew,  np.nan),
        (s_iv,  w_iv,  dr_iv),
        (s_erc, w_erc, dr_erc),
        (s_erc_scaled, w_erc_scaled, dr_erc),
    ]

    print(f"\n  {'Portfolio':<28} {'Weights (A/B/C)':>20} {'AnnRet':>8} {'AnnVol':>8} "
          f"{'Sharpe':>8} {'MaxDD':>8} {'DR':>6}")
    print("  " + "-" * 92)
    for ps, w, dr in portfolios:
        wstr = f"{w.get('A',0)*100:.0f}/{w.get('B',0)*100:.0f}/{w.get('C',0)*100:.0f}%"
        dr_s = f"{dr:.2f}" if np.isfinite(dr) else "—"
        print(f"  {ps['label']:<28} {wstr:>20} {ps['ann_ret']*100:>+7.1f}% "
              f"{ps['ann_vol']*100:>7.1f}% {ps['sharpe']:>8.3f} "
              f"{ps['max_dd']*100:>+7.1f}% {dr_s:>6}")

    # Risk contribution breakdown for ERC
    print(f"\n  ERC risk contribution breakdown:")
    rcb = risk_contribution_breakdown(w_erc, ret_nz.dropna(how="all"))
    if not rcb.empty:
        print(f"  {'Strategy':<10} {'Weight':>8} {'Vol ann':>9} {'Marg RC':>9} {'Pct RC':>8}")
        print("  " + "-" * 46)
        for s, row in rcb.iterrows():
            print(f"  {s:<10} {row['weight']*100:>7.1f}% {row['vol_ann']*100:>8.1f}% "
                  f"{row['marginal_rc']*100:>8.2f}% {row['pct_rc']*100:>7.1f}%")

    # ── Integration blockers ──────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("STEP 4 — INTEGRATION BLOCKERS")
    print("=" * 100)
    blockers = check_integration_blockers(returns_df)
    for b in blockers:
        sev_icon = "✓" if b["severity"] == "OK" else ("⚠" if b["severity"] in ("LOW", "MEDIUM") else "✗")
        print(f"\n  [{sev_icon} {b['severity']}] Issue {b['issue']}: {b['description']}")
        if b["severity"] != "OK":
            print(f"    Resolution: {b['resolution']}")

    # ── Recommendations ───────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("STEP 5 — RECOMMENDATIONS")
    print("=" * 100)

    best_sh  = max(s_ew["sharpe"], s_iv["sharpe"], s_erc["sharpe"])
    best_mdd = min(s_ew["max_dd"], s_iv["max_dd"], s_erc["max_dd"])

    print(f"""
  Most likely portfolio Sharpe (ERC, all backtest): {s_erc['sharpe']:.3f}
  MaxDD under ERC: {s_erc['max_dd']*100:.1f}%

  Critical issues before going live with ERC:
    1. Strategy B capital base: live account size ≠ backtest $500.
       Scale B returns to match actual deployed notional before sizing.
    2. Strategy A: live execution has crypto slippage (0.085% per leg assumed in backtest).
       At $5K account, slippage is immaterial. OK to proceed.
    3. All 3 strategies use backtest. Plan to re-run correlation/ERC after 60 live days.

  Deploy C paper trading immediately:
    → YES. NQ Strategy C is backtest-only. Paper trade at 0.25 contracts NOW.
    → Record daily equity. After 30 trades, update Phase 1 analysis with live C data.
    → Manual process: track entry/exit/P&L in a spreadsheet or simple log file.

  Next session priorities:
    Phase 2: live monitoring infrastructure
      - Daily cronjob that reads A live log (tsmom_trades.csv on VPS)
      - Reads B live state (state.json on VPS)
      - Reads C paper trade log (local file)
      - Computes daily portfolio P&L, correlation matrix, rebalance signal
    Phase 3: parametric stress tests
      - Correlation spike scenarios (+0.7 pairwise)
      - Volatility regime shift (×2 vols)
      - Strategy-specific shock (B carry collapses if funding turns negative)
""")

    # ── Save summary ──────────────────────────────────────────────────────────
    summary_path = Path(__file__).parent / "initial_summary.md"
    _write_summary(
        summary_path, stats_df, corr_full, corr_recent, w_ew, w_iv, w_erc,
        s_ew, s_iv, s_erc, s_erc_scaled, dr_ew, dr_iv, dr_erc,
        roll_summary, alerts, blockers, scale_factor,
    )
    log.info(f"Summary saved → {summary_path}")

    print(f"\n  Summary written to: {summary_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Markdown summary writer
# ─────────────────────────────────────────────────────────────────────────────

def _write_summary(path, stats_df, corr_full, corr_recent, w_ew, w_iv, w_erc,
                   s_ew, s_iv, s_erc, s_erc_scaled, dr_ew, dr_iv, dr_erc,
                   roll_summary, alerts, blockers, scale_factor):
    lines = [
        "# Portfolio Integration — Phase 1 Summary",
        "",
        f"*Generated: 2026-05-21*",
        "",
        "## 1. Headline",
        "",
        f"| Metric | Equal-weighted | ERC | ERC 10% vol |",
        f"|--------|---------------|-----|-------------|",
        f"| Portfolio Sharpe (HAC) | {s_ew['sharpe']:.3f} | {s_erc['sharpe']:.3f} | {s_erc_scaled['sharpe']:.3f} |",
        f"| MaxDD | {s_ew['max_dd']*100:+.1f}% | {s_erc['max_dd']*100:+.1f}% | {s_erc_scaled['max_dd']*100:+.1f}% |",
        f"| Diversification Ratio | {dr_ew:.2f} | {dr_erc:.2f} | {dr_erc:.2f} |",
        "",
        "## 2. Per-Strategy Stats",
        "",
        "| Strategy | Source | Period | N obs | Ann Ret | Ann Vol | Sharpe HAC | MaxDD |",
        "|----------|--------|--------|-------|---------|---------|------------|-------|",
    ]
    for s, row in stats_df.iterrows():
        lines.append(
            f"| {s} ({row['name']}) | {row['source']} | {row['start']} → {row['end']} "
            f"| {int(row['n_obs'])} | {row['ann_ret']*100:+.1f}% | {row['ann_vol']*100:.1f}% "
            f"| {row['sharpe_hac']:.3f} | {row['max_dd']*100:+.1f}% |"
        )

    lines += [
        "",
        "## 3. Correlation Matrix (Full Sample)",
        "",
        "```",
        corr_full.round(4).to_string(),
        "```",
        "",
        "### Rolling 60-day (most recent window)",
        "",
        "```",
        corr_recent.round(4).to_string(),
        "```",
        "",
        "### Correlation alerts",
        "",
    ]
    if alerts:
        for a in alerts:
            lines.append(f"- {a['pair']}: corr={a['correlation']:+.3f} [{a['severity']}]")
    else:
        lines.append("- None. All pairs |corr| < 0.5.")

    lines += [
        "",
        "## 4. Portfolio Construction Comparison",
        "",
        "| Portfolio | Weights A/B/C | Ann Ret | Ann Vol | Sharpe HAC | MaxDD | DR |",
        "|-----------|--------------|---------|---------|------------|-------|-----|",
    ]
    for ps, w, dr in [(s_ew, w_ew, dr_ew), (s_iv, w_iv, dr_iv),
                       (s_erc, w_erc, dr_erc), (s_erc_scaled, {}, dr_erc)]:
        wstr = f"{w.get('A',0)*100:.0f}/{w.get('B',0)*100:.0f}/{w.get('C',0)*100:.0f}%" \
               if w else f"×{scale_factor:.2f} ERC"
        dr_s = f"{dr:.2f}" if np.isfinite(dr) else "—"
        lines.append(
            f"| {ps['label']} | {wstr} | {ps['ann_ret']*100:+.1f}% | "
            f"{ps['ann_vol']*100:.1f}% | {ps['sharpe']:.3f} | "
            f"{ps['max_dd']*100:+.1f}% | {dr_s} |"
        )

    lines += [
        "",
        "## 5. Rolling Correlation Alerts",
        "",
        "| Pair | Mean corr | Max corr | % windows >0.5 |",
        "|------|-----------|----------|----------------|",
    ]
    for (p1, p2), s in roll_summary.items():
        if s:
            lines.append(
                f"| {p1}-{p2} | {s['mean']:+.3f} | {s['max']:+.3f} | "
                f"{s['pct_above_05']*100:.0f}% |"
            )

    lines += ["", "## 6. Integration Blockers", ""]
    for b in blockers:
        if b["severity"] != "OK":
            lines.append(f"- **[{b['severity']}] Issue {b['issue']}**: {b['description']}")
            lines.append(f"  - Resolution: {b['resolution']}")

    lines += [
        "",
        "## 7. Recommendations",
        "",
        "- **Deploy C paper trading immediately** — no blocking issue. Manual log sufficient.",
        "- **Re-run Phase 1 after 60 live days** per strategy with real returns.",
        "- **Strategy B capital scaling**: verify live notional matches backtest $500 assumption.",
        "- **ERC live deployment**: suitable as-is for paper sizing. "
          "Do not commit real capital until 60 live days of each strategy.",
        "",
        "## 8. Next Phases",
        "",
        "- **Phase 2** (next session): daily monitoring cronjob — reads A/B VPS logs + C paper log, "
          "computes daily portfolio P&L, correlation alert, rebalance trigger.",
        "- **Phase 3**: paper trade C alongside live A+B, validate 3-strategy portfolio in real time.",
        "- **Phase 4**: parametric stress tests — correlation spike, vol regime shift, "
          "B carry collapse scenarios.",
    ]

    path.write_text("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Portfolio integration Phase 1 failed")
        sys.exit(1)
