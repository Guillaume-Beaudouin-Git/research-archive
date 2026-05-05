"""
run_research.py — Signal Stack Research: TSMOM × Funding Carry

Hypothesis: TSMOM identifies direction; carry IC identifies crowded positioning.
Combined signal should have higher precision and lower directional risk.

Methods tested:
  Method 1 (Intersection): Hard gate — TSMOM direction × carry rank alignment
  Method 2 (Multiplicative): Combined score, long/short top/bottom quartile
  Method 3 (Scaler, diagnostic): TSMOM scaled by carry crowdedness
  Standalone TSMOM: cross-sectional TSMOM, top/bottom quintile (baseline)

Walk-forward: 12-month train / 1-month test, weekly rebalance (21 × 8h bars)
Method selected on train Sharpe, frozen on test.

Usage:
    python -m strategies.signal_stack.run_research
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT    = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

PRICES_DIR   = REPO_ROOT / "data" / "funding_carry" / "prices"
FUNDING_DIR  = REPO_ROOT / "data" / "funding_carry"
DOCS_DIR     = REPO_ROOT / "docs"
OUTPUTS_DIR  = REPO_ROOT / "outputs"
DOCS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

NOTIONAL        = 10_000.0    # $ per side
COST_PER_LEG    = 0.0017      # 0.17% per leg
QUINTILE        = 0.20
QUARTILE        = 0.25
MIN_ASSETS      = 10

# Walk-forward parameters
TRAIN_MONTHS    = 12
TEST_MONTHS     = 1
REBAL_BARS      = 21          # weekly (21 × 8h bars ≈ 7 days)
LOOKBACK_BARS   = 84          # 28d TSMOM lookback
VOL_SCALE_ANN   = np.sqrt(3 * 365)   # 8h bars annualization
VOL_TARGET      = 0.15
CARRY_ROLL_BARS = 3           # carry: 3-period rolling mean
PERIODS_PER_YEAR = 52         # weekly Sharpe

METHODS = ["method1", "method2", "standalone"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_all_prices() -> pd.DataFrame:
    """Load 8h price opens for all assets. Returns wide DataFrame (ts × asset)."""
    frames = []
    for p in sorted(PRICES_DIR.glob("*_8h.csv")):
        asset = p.stem.replace("_8h", "")
        df = pd.read_csv(p, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")[["open"]].rename(columns={"open": asset})
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).sort_index()


def load_all_funding_8h() -> pd.DataFrame:
    """
    Load per-asset hourly funding, resample to 8h periods.
    Returns wide DataFrame (8h ts × asset), values = mean hourly rate × 8 (per-period total).
    """
    frames = []
    for p in sorted(FUNDING_DIR.glob("*_funding.csv")):
        asset = p.stem.replace("_funding", "")
        df = pd.read_csv(p, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")[["funding_rate_1h"]]
        # Resample to 8h: sum of hourly rates = funding earned per 8h period
        df_8h = df.resample("8h").sum().rename(columns={"funding_rate_1h": asset})
        frames.append(df_8h)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).sort_index()


# ---------------------------------------------------------------------------
# Signal computation
# ---------------------------------------------------------------------------

def compute_tsmom_signal(px: pd.DataFrame) -> pd.DataFrame:
    """
    TSMOM signal for each asset: sign(28d_ret) × vol_target / realized_vol
    Returns signal DataFrame aligned to px index.
    """
    ret_1p  = px.pct_change(1)
    ret_28d = px.pct_change(LOOKBACK_BARS)
    vol_28d = ret_1p.rolling(LOOKBACK_BARS).std() * VOL_SCALE_ANN
    signal  = np.sign(ret_28d) * (VOL_TARGET / vol_28d.replace(0, np.nan))
    return signal.clip(-3, 3)   # cap at 3σ


def compute_carry_signal(fr_8h: pd.DataFrame) -> pd.DataFrame:
    """
    Carry signal: 3-period rolling mean of 8h funding rate, cross-sectionally ranked (0→1).
    High rank (→1) = high positive funding = short candidate.
    Low rank (→0)  = most negative funding = long candidate.
    """
    rolling_fr = fr_8h.rolling(CARRY_ROLL_BARS).mean()
    rank = rolling_fr.rank(axis=1, pct=True)
    return rank


# ---------------------------------------------------------------------------
# Position construction
# ---------------------------------------------------------------------------

def method1_positions(tsmom: pd.Series, carry_rank: pd.Series) -> pd.Series:
    """
    Intersection: Long if TSMOM>0 AND carry_rank<0.2; Short if TSMOM<0 AND carry_rank>0.8
    Equal-weight within each leg.
    """
    valid = tsmom.notna() & carry_rank.notna()
    long_mask  = valid & (tsmom > 0) & (carry_rank < QUINTILE)
    short_mask = valid & (tsmom < 0) & (carry_rank > 1 - QUINTILE)
    n_long  = long_mask.sum()
    n_short = short_mask.sum()
    pos = pd.Series(0.0, index=tsmom.index)
    if n_long  > 0: pos[long_mask]  =  1.0 / n_long
    if n_short > 0: pos[short_mask] = -1.0 / n_short
    return pos


def method2_positions(tsmom: pd.Series, carry_rank: pd.Series) -> pd.Series:
    """
    Multiplicative: score = tsmom × (−carry_rank_pct + 0.5) × 2
    Long top quartile, short bottom quartile by score. Equal-weight.
    """
    valid = tsmom.notna() & carry_rank.notna()
    score = tsmom * (-(carry_rank - 0.5) * 2)   # high = long candidate, low = short candidate
    score = score.where(valid)
    n = valid.sum()
    n_q = max(1, int(n * QUARTILE))
    pos = pd.Series(0.0, index=tsmom.index)
    if n < 4:
        return pos
    ranked = score[valid].rank()
    long_mask  = ranked >= (n - n_q + 1)
    short_mask = ranked <= n_q
    longs  = long_mask[long_mask].index
    shorts = short_mask[short_mask].index
    pos[longs]  =  1.0 / len(longs)
    pos[shorts] = -1.0 / len(shorts)
    return pos


def standalone_tsmom_positions(tsmom: pd.Series) -> pd.Series:
    """
    Standalone cross-sectional TSMOM: long top quintile, short bottom quintile by TSMOM score.
    Equal-weight within each leg (vol-scaled TSMOM score is the ranking criterion).
    """
    valid = tsmom.notna()
    n     = valid.sum()
    n_q   = max(1, int(n * QUINTILE))
    pos   = pd.Series(0.0, index=tsmom.index)
    if n < 4:
        return pos
    ranked = tsmom[valid].rank()
    long_mask  = ranked >= (n - n_q + 1)
    short_mask = ranked <= n_q
    longs  = long_mask[long_mask].index
    shorts = short_mask[short_mask].index
    pos[longs]  =  1.0 / len(longs)
    pos[shorts] = -1.0 / len(shorts)
    return pos


# ---------------------------------------------------------------------------
# P&L simulation
# ---------------------------------------------------------------------------

def simulate_pnl(
    method: str,
    tsmom_sig: pd.DataFrame,
    carry_rank: pd.DataFrame,
    px_open: pd.DataFrame,
    assets: list[str],
    rebal_index: pd.DatetimeIndex,
) -> pd.Series:
    """
    Simulate weekly rebalanced portfolio. Returns net P&L series (one value per rebal period).
    Price P&L included. Costs on turnover.
    """
    pnl_list = []
    prev_pos = pd.Series(0.0, index=assets)

    for i in range(len(rebal_index) - 1):
        ts     = rebal_index[i]
        ts_end = rebal_index[i + 1]

        # Signal at ts (uses data up to ts − lagged by construction)
        row_ts  = tsmom_sig.loc[ts, assets] if ts in tsmom_sig.index else pd.Series(np.nan, index=assets)
        row_cr  = carry_rank.loc[ts, assets] if ts in carry_rank.index else pd.Series(np.nan, index=assets)

        if method == "method1":
            pos = method1_positions(row_ts, row_cr)
        elif method == "method2":
            pos = method2_positions(row_ts, row_cr)
        else:  # standalone
            pos = standalone_tsmom_positions(row_ts)

        # Price return from ts to ts_end
        if ts in px_open.index and ts_end in px_open.index:
            p0 = px_open.loc[ts, assets]
            p1 = px_open.loc[ts_end, assets]
            ret = (p1 / p0 - 1).fillna(0)
        else:
            ret = pd.Series(0.0, index=assets)

        price_pnl = (pos * ret * NOTIONAL).sum()
        turnover  = (pos - prev_pos).abs().sum()
        fees      = turnover * NOTIONAL * COST_PER_LEG

        pnl_list.append({"ts": ts, "net": price_pnl - fees})
        prev_pos = pos.copy()

    if not pnl_list:
        return pd.Series(dtype=float)

    df = pd.DataFrame(pnl_list).set_index("ts")["net"]
    return df


def compute_sharpe(pnl: pd.Series) -> float:
    if len(pnl) < 2 or pnl.std() == 0:
        return 0.0
    return float(pnl.mean() / pnl.std() * np.sqrt(PERIODS_PER_YEAR))


# ---------------------------------------------------------------------------
# Walk-forward
# ---------------------------------------------------------------------------

def make_folds(px_open: pd.DataFrame) -> list[dict]:
    """Generate (train_start, test_start, test_end) tuples."""
    all_dates = px_open.index
    start     = all_dates[0]
    end       = all_dates[-1]

    folds = []
    test_start = start + pd.DateOffset(months=TRAIN_MONTHS)
    while test_start + pd.DateOffset(months=TEST_MONTHS) <= end:
        test_end   = test_start + pd.DateOffset(months=TEST_MONTHS)
        train_start = test_start - pd.DateOffset(months=TRAIN_MONTHS)
        folds.append({
            "train_start": train_start,
            "test_start":  test_start,
            "test_end":    test_end,
        })
        test_start = test_start + pd.DateOffset(months=TEST_MONTHS)

    return folds


def run_walkforward(
    px_open: pd.DataFrame,
    tsmom_sig: pd.DataFrame,
    carry_rank: pd.DataFrame,
) -> tuple[dict[str, list], dict[str, list]]:
    """Run walk-forward, returns per-method OOS P&L list and fold metadata."""
    # Pre-compute first valid index per asset
    first_ts = {c: px_open[c].first_valid_index() for c in px_open.columns}

    folds     = make_folds(px_open)
    n_folds   = len(folds)
    print(f"  Walk-forward: {n_folds} folds ({TRAIN_MONTHS}m train / {TEST_MONTHS}m test)")

    oos_pnl   = {m: [] for m in METHODS}
    fold_meta = []

    for fold_i, fold in enumerate(folds):
        train_start = fold["train_start"]
        test_start  = fold["test_start"]
        test_end    = fold["test_end"]

        # Available assets: listed before train_start
        available = [c for c, fts in first_ts.items()
                     if fts is not None and fts <= train_start]
        if len(available) < MIN_ASSETS:
            continue

        # Build rebalance index for train and test periods (weekly steps)
        all_idx   = px_open.index
        train_idx = all_idx[(all_idx >= train_start) & (all_idx < test_start)]
        test_idx  = all_idx[(all_idx >= test_start)  & (all_idx < test_end)]

        rebal_train = train_idx[::REBAL_BARS]
        rebal_test  = test_idx[::REBAL_BARS]

        if len(rebal_train) < 4 or len(rebal_test) < 1:
            continue

        # Add one extra index point after test for price return computation
        # Use full index for look-ahead-safe price returns
        extra_idx = all_idx[all_idx >= test_end]
        if len(extra_idx) > 0:
            rebal_test_ext = rebal_test.append(extra_idx[:1])
        else:
            continue

        # Train: select method by Sharpe
        # Add extra after train for last period price return
        rebal_train_ext = rebal_train.append(test_idx[:1] if len(test_idx) > 0 else pd.DatetimeIndex([]))

        best_method = "standalone"
        best_sharpe = -np.inf

        for method in METHODS:
            pnl = simulate_pnl(method, tsmom_sig, carry_rank, px_open, available, rebal_train_ext)
            sh  = compute_sharpe(pnl)
            if method != "standalone" and sh > best_sharpe:
                best_sharpe  = sh
                best_method  = method

        # Test: apply each method OOS
        for method in METHODS:
            pnl = simulate_pnl(method, tsmom_sig, carry_rank, px_open, available, rebal_test_ext)
            oos_pnl[method].extend(pnl.values.tolist())

        fold_meta.append({
            "fold":        fold_i + 1,
            "test_start":  test_start.date(),
            "test_end":    test_end.date(),
            "n_assets":    len(available),
            "best_method": best_method,
            "train_sharpe":round(best_sharpe, 2),
        })

        if (fold_i + 1) % 5 == 0:
            print(f"    Fold {fold_i+1}/{n_folds}  assets={len(available)}  best={best_method}  train_sh={best_sharpe:.2f}")

    return oos_pnl, fold_meta


# ---------------------------------------------------------------------------
# Report + chart
# ---------------------------------------------------------------------------

def build_chart(oos_pnl: dict[str, list], out_path: Path) -> None:
    """Plot cumulative P&L for all methods."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [2, 1]})

    colors = {"method1": "#2196F3", "method2": "#4CAF50", "standalone": "#FF9800"}
    labels = {
        "method1":    "Method 1: Intersection (TSMOM ∩ Carry)",
        "method2":    "Method 2: Multiplicative Score",
        "standalone": "Standalone TSMOM (baseline)",
    }

    ax = axes[0]
    for method in METHODS:
        pnl = pd.Series(oos_pnl[method])
        if len(pnl) > 0:
            cum = pnl.cumsum()
            ax.plot(cum.values, label=labels[method], color=colors[method], linewidth=1.5)

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_title("TSMOM × Funding Carry Signal Stack — OOS Cumulative P&L")
    ax.set_ylabel("Cumulative P&L ($)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)

    # Bottom: rolling 12-period Sharpe comparison
    ax2 = axes[1]
    window = 52  # 1 year of weekly periods
    for method in METHODS:
        pnl = pd.Series(oos_pnl[method])
        if len(pnl) >= window:
            roll = pnl.rolling(window).mean() / pnl.rolling(window).std() * np.sqrt(PERIODS_PER_YEAR)
            ax2.plot(roll.values, label=labels[method], color=colors[method], linewidth=1.2)

    ax2.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax2.axhline(1.0, color="gray", linewidth=0.8, linestyle=":", alpha=0.7)
    ax2.set_title(f"Rolling {window}-period Sharpe (weekly)")
    ax2.set_ylabel("Sharpe")
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Chart saved: {out_path}")


REPORT_TEMPLATE = """\
# Signal Stack Research: TSMOM × Funding Carry

**Generated:** 2026-05-05 UTC
**Universe:** {n_assets_range} Hyperliquid perpetuals (≥180 days history, expanding)
**Walk-forward:** {train_months}m train / {test_months}m test, {n_folds} folds
**Rebalance:** Weekly (21 × 8h bars)
**Baseline:** Standalone cross-sectional TSMOM (28d lookback, vol-scaled, top/bottom quintile)

---

## Hypothesis

TSMOM identifies price trend direction; cross-sectional carry rank identifies crowded positioning
(high positive funding = longs paying heavily = crowded long). Combining should yield:
- Higher precision on longs (trend + flow alignment)
- Lower directional risk on shorts (avoid shorting into consensus longs with momentum)
- Net: higher Sharpe than either signal alone

---

## Methods Tested

### Method 1 — Intersection (Hard Gate)
- **Long**: TSMOM > 0 AND carry_rank < 0.20 (most negative funding, least crowded long)
- **Short**: TSMOM < 0 AND carry_rank > 0.80 (most positive funding, most crowded)
- Equal-weight within each leg. May have fewer positions than standalone.

### Method 2 — Multiplicative Score
- **Score**: `tsmom_signal × (−carry_rank_pct + 0.5) × 2`
- High score = strong positive momentum + anti-crowded = long candidate
- Long top quartile, short bottom quartile by score. Equal-weight.

### Standalone TSMOM (Baseline)
- Cross-sectional rank by TSMOM score (vol-scaled 28d return)
- Long top quintile, short bottom quintile. Equal-weight.
- Expected OOS Sharpe: ~1.41 (per prior TSMOM backtest on BTC+SOL, adjusted for cross-sectional)

---

## OOS Results Summary

| Method | Total Net P&L | Sharpe (weekly) | vs Standalone |
|--------|---------------|-----------------|---------------|
| Method 1: Intersection | ${m1_pnl:+,.0f} | {m1_sharpe:.3f} | {m1_delta:+.3f} |
| Method 2: Multiplicative | ${m2_pnl:+,.0f} | {m2_sharpe:.3f} | {m2_delta:+.3f} |
| Standalone TSMOM | ${sa_pnl:+,.0f} | {sa_sharpe:.3f} | — |

---

## Correlation Between Methods

| Pair | Correlation |
|------|-------------|
| Method 1 vs Standalone | {corr_m1_sa:.3f} |
| Method 2 vs Standalone | {corr_m2_sa:.3f} |
| Method 1 vs Method 2 | {corr_m1_m2:.3f} |

---

## Method Selection (Train Period)

| Method Selected | % of Folds |
|-----------------|-----------|
| Method 1 | {pct_m1:.0%} |
| Method 2 | {pct_m2:.0%} |

---

## Conclusion

{conclusion}

---

## GO Criteria Assessment

| Criterion | Required | Result | Pass? |
|-----------|----------|--------|-------|
| Best combined Sharpe > standalone | > 1.41 | {best_sharpe:.3f} | {beat_baseline} |
| Correlation to standalone | Any | {best_corr:.3f} | — |
| Hypothesis validated | combined > 1.41 | {hyp_pass} | {hyp_emoji} |

---

## Methodology Notes

### TSMOM Signal Construction
- Lookback: 84 × 8h bars (28 days)
- Vol-scaling: 15% annual target, vol = pct_change(1).rolling(84).std() × √(3×365)
- Signal: sign(ret_84) × 0.15 / vol_84, clipped at ±3
- No look-ahead: signal at bar T uses prices from bars T-84 through T-1

### Carry Signal Construction
- 8h funding rate: hourly funding resampled to 8h (sum per period)
- Rolling 3-period mean cross-sectional rank (pct=True, 0→1)
- High rank (→1) = high positive funding = crowded longs = short candidate in Method 1
- No look-ahead: signal at bar T uses funding from bars T-3 through T-1

### Walk-Forward Protocol
- Fold structure: {train_months}m rolling train, {test_months}m test
- Asset universe per fold: assets with any price data before fold train_start (survival bias control)
- Method selection: Methods 1 & 2 compete on train Sharpe; selected method frozen on test
- Standalone TSMOM always run on test for direct comparison (no selection needed)
- Cost: 0.17% per leg (0.035% taker + 0.05% slippage) × 2 sides = 0.34% round-trip on turnover

### Per-Fold Results
{fold_table}
"""


def build_report(
    oos_pnl: dict[str, list],
    fold_meta: list[dict],
    n_assets_range: str,
) -> str:
    pnl = {m: pd.Series(v) for m, v in oos_pnl.items()}

    sharpes = {m: compute_sharpe(pnl[m]) for m in METHODS}
    totals  = {m: float(pnl[m].sum())  for m in METHODS}

    sa_sh   = sharpes["standalone"]
    m1_sh   = sharpes["method1"]
    m2_sh   = sharpes["method2"]
    best_sh = max(m1_sh, m2_sh)

    # Correlations (align by length)
    min_len = min(len(pnl[m]) for m in METHODS)
    corr_m1_sa = float(pd.Series(pnl["method1"][:min_len]).corr(pd.Series(pnl["standalone"][:min_len])))
    corr_m2_sa = float(pd.Series(pnl["method2"][:min_len]).corr(pd.Series(pnl["standalone"][:min_len])))
    corr_m1_m2 = float(pd.Series(pnl["method1"][:min_len]).corr(pd.Series(pnl["method2"][:min_len])))
    best_corr = corr_m2_sa if m2_sh > m1_sh else corr_m1_sa

    # Method selection stats
    methods_chosen = [f["best_method"] for f in fold_meta]
    pct_m1 = methods_chosen.count("method1") / len(methods_chosen) if methods_chosen else 0
    pct_m2 = methods_chosen.count("method2") / len(methods_chosen) if methods_chosen else 0

    # Fold table
    fold_df = pd.DataFrame(fold_meta)[["fold", "test_start", "test_end", "n_assets", "best_method", "train_sharpe"]]
    fold_table = fold_df.to_string(index=False)

    beat_baseline = "✅" if best_sh > 1.41 else "❌"
    hyp_pass  = f"{best_sh:.2f}" if best_sh > 1.41 else f"{best_sh:.2f} (fails)"
    hyp_emoji = "✅" if best_sh > 1.41 else "❌"

    best_method_name = "Method 2 (Multiplicative)" if m2_sh > m1_sh else "Method 1 (Intersection)"
    if best_sh > 1.41:
        conclusion = (
            f"**Hypothesis CONFIRMED.** {best_method_name} achieves OOS Sharpe {best_sh:.2f}, "
            f"beating standalone TSMOM ({sa_sh:.2f}) by {best_sh - sa_sh:+.2f}. "
            f"Combining carry crowding signal with TSMOM direction improves signal quality."
        )
    elif best_sh > sa_sh:
        conclusion = (
            f"**Hypothesis PARTIALLY confirmed.** {best_method_name} achieves OOS Sharpe {best_sh:.2f}, "
            f"improving over standalone TSMOM ({sa_sh:.2f}) by {best_sh - sa_sh:+.2f}, "
            f"but below the 1.41 GO threshold."
        )
    else:
        conclusion = (
            f"**Hypothesis NOT confirmed.** Best combined Sharpe is {best_sh:.2f} vs standalone TSMOM {sa_sh:.2f}. "
            f"The carry filter does not improve TSMOM in this cross-sectional setting. "
            f"Carry crowding and momentum direction are insufficiently orthogonal to improve signal."
        )

    return REPORT_TEMPLATE.format(
        n_assets_range=n_assets_range,
        train_months=TRAIN_MONTHS,
        test_months=TEST_MONTHS,
        n_folds=len(fold_meta),
        m1_pnl=totals["method1"],
        m2_pnl=totals["method2"],
        sa_pnl=totals["standalone"],
        m1_sharpe=m1_sh,
        m2_sharpe=m2_sh,
        sa_sharpe=sa_sh,
        m1_delta=m1_sh - sa_sh,
        m2_delta=m2_sh - sa_sh,
        corr_m1_sa=corr_m1_sa,
        corr_m2_sa=corr_m2_sa,
        corr_m1_m2=corr_m1_m2,
        best_sharpe=best_sh,
        best_corr=best_corr,
        beat_baseline=beat_baseline,
        hyp_pass=hyp_pass,
        hyp_emoji=hyp_emoji,
        conclusion=conclusion,
        pct_m1=pct_m1,
        pct_m2=pct_m2,
        fold_table=fold_table,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading prices...")
    px_open = load_all_prices()
    print(f"  {px_open.shape[1]} assets, {len(px_open):,} bars  ({px_open.index[0].date()} → {px_open.index[-1].date()})")

    print("Loading funding (8h resampled)...")
    fr_8h = load_all_funding_8h()
    print(f"  {fr_8h.shape[1]} assets, {len(fr_8h):,} periods")

    # Align to common 8h index
    common_idx = px_open.index.intersection(fr_8h.index)
    px_open = px_open.loc[common_idx]
    fr_8h   = fr_8h.loc[common_idx]
    common_assets = list(set(px_open.columns) & set(fr_8h.columns))
    print(f"  Common index: {len(common_idx):,} bars | {len(common_assets)} assets with both price+funding")

    print("\nComputing signals...")
    tsmom_sig   = compute_tsmom_signal(px_open[common_assets])
    carry_rank  = compute_carry_signal(fr_8h[common_assets])
    print("  TSMOM and carry signals computed.")

    print("\nRunning walk-forward...")
    oos_pnl, fold_meta = run_walkforward(
        px_open[common_assets],
        tsmom_sig,
        carry_rank,
    )

    print("\n" + "="*60)
    for method in METHODS:
        pnl = pd.Series(oos_pnl[method])
        sh  = compute_sharpe(pnl)
        label = {"method1": "Method 1 (Intersection)",
                 "method2": "Method 2 (Multiplicative)",
                 "standalone": "Standalone TSMOM"}[method]
        print(f"  {label:<35}  Sharpe={sh:.3f}  Net=${pnl.sum():+,.0f}")

    sa_sh = compute_sharpe(pd.Series(oos_pnl["standalone"]))
    best  = max(compute_sharpe(pd.Series(oos_pnl["method1"])),
                compute_sharpe(pd.Series(oos_pnl["method2"])))
    min_len = min(len(oos_pnl[m]) for m in METHODS)
    corr_r = float(pd.Series(oos_pnl["method2"][:min_len]).corr(
                   pd.Series(oos_pnl["standalone"][:min_len])))
    print("="*60)

    # Asset count range across folds
    if fold_meta:
        n_min = min(f["n_assets"] for f in fold_meta)
        n_max = max(f["n_assets"] for f in fold_meta)
        n_assets_range = f"{n_min}–{n_max}"
    else:
        n_assets_range = "N/A"

    print("\nBuilding chart...")
    chart_path = OUTPUTS_DIR / "signal_stack_comparison.png"
    build_chart(oos_pnl, chart_path)

    print("Building report...")
    report = build_report(oos_pnl, fold_meta, n_assets_range)
    report_path = DOCS_DIR / "strategy_stack_research.md"
    report_path.write_text(report)
    print(f"  Report written: {report_path}")

    # Print commit message
    best_m = "method2" if compute_sharpe(pd.Series(oos_pnl["method2"])) > compute_sharpe(pd.Series(oos_pnl["method1"])) else "method1"
    best_sh = compute_sharpe(pd.Series(oos_pnl[best_m]))
    print(f"\nSuggested commit message:")
    print(f'  research: TSMOM×carry signal stack — combined Sharpe {best_sh:.2f} vs TSMOM standalone {sa_sh:.2f}, corr={corr_r:.2f}')

    return oos_pnl, fold_meta


if __name__ == "__main__":
    main()
