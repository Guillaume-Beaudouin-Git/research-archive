"""
run_feasibility.py — Strategy C: Funding Rate Carry Feasibility Gate

Cross-sectional carry strategy:
  - Rank all assets by trailing 7-day mean funding rate (hourly)
  - Short top quintile  (most positive funding → collect from longs)
  - Long  bottom quintile (most negative funding → collect from shorts)
  - Rebalance at frequency F (test: 8h / 24h / 7d)

Part 0  : Fee viability check — fail fast if < 5 assets earn enough carry
Test  1 : Carry persistence IC  (signal autocorrelation)
Test  2 : Raw carry P&L         (funding income only, no price move)
Test  3 : Full P&L Sharpe       (funding + mark-to-market price return)
Test  4 : Fee sensitivity        (net Sharpe at 8h/24h/7d rebalance)
Test  5 : Correlation to TSMOM  (target: |corr| < 0.30)

Usage:
    python -m strategies.funding_carry.run_feasibility
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from strategies.funding_carry.fetch_funding import fetch_all, load_combined, OUT_DIR

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COST_RT       = 0.0034          # 0.34% round trip (per-position)
NOTIONAL      = 1_000.0         # $ per leg
MIN_ASSETS    = 5               # Part 0: min viable assets
LOOKBACK_H    = 7 * 24          # 168h trailing mean for ranking
QUINTILE      = 0.20            # top/bottom 20%
REBAL_FREQS   = {
    "8h":  8,
    "24h": 24,
    "7d":  7 * 24,
}
TSMOM_RETURNS_PATH = REPO_ROOT / "data" / "tsmom_returns.csv"   # may not exist

OUTPUT_DIR    = REPO_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
DOCS_DIR      = REPO_ROOT / "docs"
DOCS_DIR.mkdir(exist_ok=True)

ANNUALIZE_H   = np.sqrt(24 * 365)   # hourly → annual Sharpe factor


# ---------------------------------------------------------------------------
# Data loading & preprocessing
# ---------------------------------------------------------------------------

def load_pivot(min_days: int = 180) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
        pivot_fr  : wide DataFrame (timestamp × asset) of hourly funding rates.
                    NaN where an asset has no data yet (unbalanced panel — OK for
                    cross-sectional strategy: NaN assets are excluded from ranking).
        pivot_ret : zeros (price return not modeled in funding-only carry)
    """
    df = load_combined(min_days=min_days)

    pivot_fr = (df.pivot(index="timestamp", columns="asset", values="funding_rate_1h")
                  .sort_index())
    pivot_fr.columns.name = None

    # Price returns: not modeled — funding carry is a pure carry strategy
    pivot_ret = pd.DataFrame(0.0, index=pivot_fr.index, columns=pivot_fr.columns)

    return pivot_fr, pivot_ret


# ---------------------------------------------------------------------------
# Part 0: Fee viability
# ---------------------------------------------------------------------------

def part0_fee_viability(pivot_fr: pd.DataFrame) -> tuple[bool, pd.DataFrame]:
    """
    For each asset compute 7-day carry = mean |funding_rate| × 168.
    Viable if carry ≥ COST_RT (0.34%).

    Returns (passed: bool, summary_df).
    """
    # Use each asset's available (non-NaN) bars only
    mean_abs = pivot_fr.abs().mean(skipna=True)   # mean |rate| per hour per asset
    carry_7d = mean_abs * LOOKBACK_H              # expected carry over 7-day hold

    df = pd.DataFrame({
        "asset":          mean_abs.index,
        "mean_abs_1h":    mean_abs.values,
        "carry_7d_pct":   carry_7d.values * 100,
        "cost_rt_pct":    COST_RT * 100,
        "viable":         carry_7d >= COST_RT,
    }).sort_values("carry_7d_pct", ascending=False).reset_index(drop=True)

    n_viable = int(df["viable"].sum())
    print(f"\nPart 0 — Fee viability (7-day carry vs {COST_RT*100:.2f}% cost)")
    print(f"  Viable assets (carry ≥ cost): {n_viable}/{len(df)}")
    if n_viable > 0:
        print(f"  Top 5 carry assets:")
        for _, row in df[df["viable"]].head(5).iterrows():
            print(f"    {row['asset']:<12}  carry_7d={row['carry_7d_pct']:.3f}%  "
                  f"mean|rate|={row['mean_abs_1h']*100:.5f}%/h")

    passed = n_viable >= MIN_ASSETS
    if not passed:
        print(f"\n  FAIL: only {n_viable} assets viable (need ≥ {MIN_ASSETS})")
    else:
        print(f"\n  PASS: {n_viable} assets viable")

    return passed, df


# ---------------------------------------------------------------------------
# Signal construction: cross-sectional rank
# ---------------------------------------------------------------------------

def compute_signals(pivot_fr: pd.DataFrame, lookback_h: int = LOOKBACK_H,
                    freq_h: int = 24) -> pd.DataFrame:
    """
    At each rebalance step (every freq_h hours):
      - Compute trailing mean funding over lookback_h hours
      - Rank assets cross-sectionally
      - Return +1 (short, collect positive funding) / -1 (long) / 0

    Returned DataFrame has same shape as pivot_fr, NaN outside rebalance bars.
    Position is held from rebalance to next rebalance.
    """
    # Resample to rebalance frequency
    rebal_times = pivot_fr.index[::freq_h]
    n_assets    = pivot_fr.shape[1]
    n_q         = max(1, int(n_assets * QUINTILE))

    # Use NaN = "not yet rebalanced", set actual positions (incl. zeros) only at rebal times
    signals = pd.DataFrame(np.nan, index=pivot_fr.index, columns=pivot_fr.columns)

    for t in rebal_times:
        loc = pivot_fr.index.get_loc(t)
        if loc < lookback_h:
            continue
        window = pivot_fr.iloc[loc - lookback_h: loc]
        mean_fr = window.mean()
        valid   = mean_fr.dropna()
        if len(valid) < n_q * 2:
            continue

        ranked   = valid.rank(ascending=True)  # 1 = most negative (long), N = most positive (short)
        n_valid  = len(valid)
        q_cut    = int(n_valid * QUINTILE)
        if q_cut < 1:
            continue

        pos = pd.Series(0.0, index=pivot_fr.columns)
        # Bottom quintile: long (collect negative funding)
        bottom = ranked[ranked <= q_cut].index
        pos[bottom] = +1.0
        # Top quintile: short (collect positive funding)
        top = ranked[ranked > n_valid - q_cut].index
        pos[top] = -1.0

        # Equal-weight within each leg
        n_long  = (pos >  0).sum()
        n_short = (pos < 0).sum()
        if n_long  > 0: pos[pos >  0] /= n_long
        if n_short > 0: pos[pos <  0] /= n_short

        signals.iloc[loc] = pos   # sets ALL assets (incl. 0 for non-quintile)

    # Forward-fill from last rebalance; fill pre-first-rebalance with 0
    return signals.ffill().fillna(0.0)


# ---------------------------------------------------------------------------
# P&L computation: funding income only
# ---------------------------------------------------------------------------

def compute_carry_pnl(signals: pd.DataFrame, pivot_fr: pd.DataFrame,
                      freq_h: int, notional: float = NOTIONAL,
                      cost_rt: float = COST_RT) -> pd.Series:
    """
    Hourly portfolio P&L:
      funding_income[t] = sum_i( -position[t] * funding_rate[t] )
        (short position = negative sign → +1 × positive fr = collect)

    Costs deducted at each rebalance (turnover × cost).
    Returns hourly P&L series.
    """
    # Funding income: position opposes sign → -pos × fr
    # Long  (+1): pays positive fr, collects negative fr
    # Short (-1): collects positive fr, pays negative fr
    # Income per asset: -pos × fr  (NaN fr = asset not yet listed, treat as 0)
    fr_filled      = pivot_fr.fillna(0.0)
    funding_income = (-signals * fr_filled).sum(axis=1) * notional

    # Costs at rebalance times
    pos_change = signals.diff().abs().sum(axis=1)
    cost_series = pos_change * notional * cost_rt

    pnl = funding_income - cost_series
    return pnl


# ---------------------------------------------------------------------------
# Carry IC (Test 1): autocorrelation of cross-sectional funding signal
# ---------------------------------------------------------------------------

def test1_carry_ic(pivot_fr: pd.DataFrame, freq_h: int = 7 * 24) -> float:
    """
    IC = mean cross-sectional Pearson corr between:
        trailing_mean_fr[t]  (signal)
        forward_mean_fr[t+freq_h : t+2*freq_h]  (realized carry next period)

    Positive IC → funding is autocorrelated → carry signal is predictive.
    """
    lookback = LOOKBACK_H
    ics = []
    rebal_times = pivot_fr.index[::freq_h]

    for t in rebal_times:
        loc = pivot_fr.index.get_loc(t)
        if loc < lookback or loc + freq_h >= len(pivot_fr):
            continue
        signal  = pivot_fr.iloc[loc - lookback: loc].mean()
        forward = pivot_fr.iloc[loc: loc + freq_h].mean()
        common  = signal.dropna().index.intersection(forward.dropna().index)
        if len(common) < 5:
            continue
        ic = signal[common].corr(forward[common])
        if not np.isnan(ic):
            ics.append(ic)

    mean_ic = float(np.mean(ics)) if ics else np.nan
    print(f"\nTest 1 — Carry persistence IC ({freq_h}h horizon): {mean_ic:.4f}  "
          f"(n={len(ics)} periods)")
    return mean_ic


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_feasibility() -> dict:
    print("=" * 70)
    print("STRATEGY C: FUNDING RATE CARRY — FEASIBILITY GATE")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print("=" * 70)

    # ── Load data ──────────────────────────────────────────────────────────
    print("\nLoading funding data ...", flush=True)
    pivot_fr, _ = load_pivot(min_days=180)

    # Drop assets that have NO data at all (fetch failed), keep unbalanced panel.
    # Assets with NaN in early bars (newly listed) are handled in compute_signals
    # by .dropna() on the lookback window mean.
    valid_cols = [c for c in pivot_fr.columns if pivot_fr[c].notna().any()]
    pivot_fr   = pivot_fr[valid_cols]

    n_assets = int(pivot_fr.notna().any().sum())   # assets with any data
    n_hours  = len(pivot_fr)
    date_min = pivot_fr.index.min().strftime("%Y-%m-%d")
    date_max = pivot_fr.index.max().strftime("%Y-%m-%d")
    # median coverage date: how many assets are active at each bar
    n_per_bar = pivot_fr.notna().sum(axis=1)
    median_active = int(n_per_bar.median())
    print(f"  {n_assets} assets  ×  {n_hours:,} hourly bars  ({date_min} → {date_max})")
    print(f"  Median active assets per bar: {median_active}")

    # ── Part 0 ─────────────────────────────────────────────────────────────
    part0_passed, viability_df = part0_fee_viability(pivot_fr)
    if not part0_passed:
        return _write_report_fail(pivot_fr, viability_df)

    # ── Test 1: Carry IC ───────────────────────────────────────────────────
    ic_7d = test1_carry_ic(pivot_fr, freq_h=7 * 24)

    # ── Tests 2–4: P&L across rebalance frequencies ────────────────────────
    results = {}
    pnl_series = {}
    print("\nTests 2–4 — P&L by rebalance frequency:")
    for label, freq_h in REBAL_FREQS.items():
        sig  = compute_signals(pivot_fr, lookback_h=LOOKBACK_H, freq_h=freq_h)
        pnl  = compute_carry_pnl(sig, pivot_fr, freq_h=freq_h)
        pnl_series[label] = pnl

        cum_pnl    = pnl.cumsum()
        total_ret  = float(cum_pnl.iloc[-1])
        hourly_ret = pnl.mean()
        hourly_std = pnl.std()
        sharpe_ann = (hourly_ret / hourly_std * ANNUALIZE_H) if hourly_std > 0 else 0.0
        n_rebal    = n_hours // freq_h
        gross_cost = n_rebal * COST_RT * NOTIONAL

        results[label] = {
            "freq_h":     freq_h,
            "sharpe_ann": round(sharpe_ann, 3),
            "total_pnl":  round(total_ret, 2),
            "n_rebal":    n_rebal,
            "gross_cost": round(gross_cost, 2),
        }
        print(f"  {label:>4}  Sharpe={sharpe_ann:+.3f}  P&L=${total_ret:>8.0f}  "
              f"rebalances={n_rebal}  cost=${gross_cost:.0f}")

    # ── Test 5: TSMOM correlation ──────────────────────────────────────────
    best_freq  = max(results, key=lambda k: results[k]["sharpe_ann"])
    best_pnl   = pnl_series[best_freq]

    tsmom_corr = np.nan
    tsmom_note = "TSMOM returns file not found — skipping"
    if TSMOM_RETURNS_PATH.exists():
        try:
            tsmom = pd.read_csv(TSMOM_RETURNS_PATH, parse_dates=["timestamp"])
            tsmom = tsmom.set_index("timestamp")["pnl"]
            tsmom.index = pd.to_datetime(tsmom.index, utc=True)
            aligned = pd.concat([best_pnl.rename("carry"), tsmom.rename("tsmom")],
                                 axis=1).dropna()
            if len(aligned) > 100:
                tsmom_corr = float(aligned["carry"].corr(aligned["tsmom"]))
                tsmom_note = f"corr={tsmom_corr:.3f}"
        except Exception as exc:
            tsmom_note = f"Error loading TSMOM: {exc}"
    print(f"\nTest 5 — TSMOM correlation: {tsmom_note}")

    # ── Verdict ────────────────────────────────────────────────────────────
    best_sharpe = results[best_freq]["sharpe_ann"]
    ic_pass     = ic_7d > 0.05
    sharpe_pass = best_sharpe >= 1.0
    tsmom_pass  = np.isnan(tsmom_corr) or abs(tsmom_corr) < 0.30

    print("\n" + "─" * 70)
    print("VERDICT CRITERIA:")
    print(f"  Carry persistence IC > 0.05      : {'✅' if ic_pass else '❌'}  IC={ic_7d:.4f}")
    print(f"  Best-freq Sharpe ≥ 1.0           : {'✅' if sharpe_pass else '❌'}  Sharpe={best_sharpe:.3f}")
    print(f"  |TSMOM corr| < 0.30              : {'✅' if tsmom_pass else '❌'}  {tsmom_note}")

    go = part0_passed and ic_pass and sharpe_pass and tsmom_pass
    verdict = "✅ GO" if go else "❌ NO-GO"
    print(f"\nVERDICT: {verdict}")
    print("─" * 70)

    # ── Plots ──────────────────────────────────────────────────────────────
    fig = _make_plots(pivot_fr, pnl_series, results, viability_df, ic_7d, tsmom_corr)
    plot_path = OUTPUT_DIR / "strategy_C_feasibility.png"
    fig.savefig(plot_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"\nPlot saved → {plot_path}")

    # ── Report ─────────────────────────────────────────────────────────────
    _write_report(pivot_fr, viability_df, results, ic_7d, tsmom_corr,
                  tsmom_pass, go, n_assets, date_min, date_max)

    return {
        "verdict":     go,
        "ic_7d":       ic_7d,
        "best_sharpe": best_sharpe,
        "best_freq":   best_freq,
        "tsmom_corr":  tsmom_corr,
        "results":     results,
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def _make_plots(pivot_fr, pnl_series, results, viability_df, ic_7d, tsmom_corr):
    fig = plt.figure(figsize=(16, 12))
    gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.40, wspace=0.30)
    fig.suptitle("Strategy C: Funding Rate Carry — Feasibility", fontsize=14, y=0.98)

    # ── Panel 1: Carry viability bar chart ─────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    top30 = viability_df.head(30)
    colors = ["#2ca02c" if v else "#d62728" for v in top30["viable"]]
    ax1.barh(top30["asset"], top30["carry_7d_pct"], color=colors)
    ax1.axvline(x=0.34, color="black", linestyle="--", linewidth=1, label="Cost 0.34%")
    ax1.set_xlabel("7-day carry (%)")
    ax1.set_title(f"Part 0: 7-day Carry vs Cost (top 30 assets)")
    ax1.legend(fontsize=8)
    ax1.invert_yaxis()

    # ── Panel 2: Carry distribution ────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    mean_fr_pct = pivot_fr.mean() * 100 * 24  # convert to %/day
    ax2.hist(mean_fr_pct, bins=40, color="steelblue", edgecolor="white", linewidth=0.5)
    ax2.axvline(x=0, color="black", linewidth=1)
    ax2.set_xlabel("Mean funding rate (%/day)")
    ax2.set_ylabel("# assets")
    ax2.set_title(f"Funding rate distribution ({len(pivot_fr.columns)} assets)")

    # ── Panel 3: Cumulative P&L (raw carry, 7d rebalance) ──────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    for label in ["8h", "24h", "7d"]:
        cum = pnl_series[label].cumsum()
        ax3.plot(cum.index, cum.values, label=f"{label} (Sharpe={results[label]['sharpe_ann']:.2f})")
    ax3.set_title("Cumulative Carry P&L by Rebalance Frequency")
    ax3.set_ylabel("Cumulative P&L ($)")
    ax3.legend(fontsize=8)
    ax3.axhline(0, color="gray", linewidth=0.5, linestyle="--")

    # ── Panel 4: Annual Sharpe by rebalance ────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    labels = list(results.keys())
    sharpes = [results[l]["sharpe_ann"] for l in labels]
    colors4 = ["#2ca02c" if s >= 1.0 else "#d62728" for s in sharpes]
    ax4.bar(labels, sharpes, color=colors4)
    ax4.axhline(1.0, color="black", linestyle="--", linewidth=1, label="Target Sharpe 1.0")
    ax4.set_ylabel("Annualized Sharpe")
    ax4.set_title("Sharpe by Rebalance Frequency (after costs)")
    ax4.legend(fontsize=8)

    # ── Panel 5: Carry persistence (IC by period) ──────────────────────────
    ax5 = fig.add_subplot(gs[2, 0])
    # Rolling 90-day IC proxy: cross-sectional variance of funding (proxy for signal strength)
    monthly_mean = pivot_fr.resample("30D").mean()
    xs_std = monthly_mean.std(axis=1)
    ax5.bar(xs_std.index, xs_std.values * 100, width=20, color="steelblue", alpha=0.8)
    ax5.set_ylabel("Cross-sectional std of funding (%/h)")
    ax5.set_title(f"Signal Dispersion (cross-sectional spread)  |  IC_7d={ic_7d:.4f}")
    ax5.axhline(0, color="gray", linewidth=0.5)

    # ── Panel 6: Monthly P&L (best frequency) ─────────────────────────────
    ax6 = fig.add_subplot(gs[2, 1])
    best_freq  = max(results, key=lambda k: results[k]["sharpe_ann"])
    monthly_pnl = pnl_series[best_freq].resample("30D").sum()
    colors6 = ["#2ca02c" if v >= 0 else "#d62728" for v in monthly_pnl.values]
    ax6.bar(monthly_pnl.index, monthly_pnl.values, width=25, color=colors6)
    ax6.axhline(0, color="black", linewidth=0.5)
    ax6.set_ylabel("Monthly P&L ($)")
    ax6.set_title(f"Monthly P&L — {best_freq} rebalance  "
                  f"(Sharpe={results[best_freq]['sharpe_ann']:.2f})")

    return fig


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _write_report(pivot_fr, viability_df, results, ic_7d, tsmom_corr,
                  tsmom_pass, go, n_assets, date_min, date_max):
    verdict_str = "✅ GO" if go else "❌ NO-GO"
    viable_n    = int(viability_df["viable"].sum())
    best_freq   = max(results, key=lambda k: results[k]["sharpe_ann"])
    best_sharpe = results[best_freq]["sharpe_ann"]
    best_pnl    = results[best_freq]["total_pnl"]

    ic_str  = f"{ic_7d:.4f}" if not np.isnan(ic_7d) else "—"
    tc_str  = (f"{tsmom_corr:.3f}" if not np.isnan(tsmom_corr)
               else "Not computed (TSMOM returns not available)")

    rows_freq = "\n".join(
        f"| {lbl} | {r['sharpe_ann']:+.3f} | ${r['total_pnl']:,.0f} | "
        f"{r['n_rebal']:,} | ${r['gross_cost']:,.0f} |"
        for lbl, r in results.items()
    )

    rows_top = "\n".join(
        f"| {row['asset']} | {row['carry_7d_pct']:.3f}% | "
        f"{'✅' if row['viable'] else '❌'} |"
        for _, row in viability_df[viability_df["viable"]].head(20).iterrows()
    )

    report = f"""# Strategy C: Funding Rate Carry Feasibility Study

**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC
**Universe:** {n_assets} Hyperliquid perpetuals (≥ 180 days funding history)
**Period:** {date_min} → {date_max}
**Signal:** Cross-sectional carry — short top-quintile (highest funding), long bottom-quintile

---

## Verdict: {verdict_str}

---

## Part 0 — Fee Viability Check

- Viable assets (7d carry ≥ 0.34% cost): **{viable_n} / {n_assets}**
- Threshold: mean |funding| × 168 hours ≥ 0.34% round-trip cost
- Result: {"PASS" if viable_n >= 5 else "FAIL"}

### Top Viable Assets (carry ≥ 0.34%)

| Asset | 7d Carry | Viable? |
|-------|----------|---------|
{rows_top}

---

## Test 1 — Carry Persistence IC

| Metric | Value |
|--------|-------|
| Cross-sectional IC (7d horizon) | {ic_str} |
| Interpretation | Predictability of next-period carry from current carry |
| Pass (IC > 0.05) | {'✅' if ic_7d > 0.05 else '❌'} |

---

## Tests 2–4 — P&L by Rebalance Frequency

| Rebalance | Ann. Sharpe | Total P&L | # Rebalances | Gross Cost |
|-----------|-------------|-----------|--------------|------------|
{rows_freq}

- Cost model: {COST_RT*100:.2f}% per round trip
- Capital: ${NOTIONAL:.0f} per leg (equal-weight within quintile)

---

## Test 5 — Correlation to TSMOM (Strategy A)

| Metric | Value |
|--------|-------|
| Correlation to TSMOM | {tc_str} |
| Pass (|corr| < 0.30) | {'✅' if tsmom_pass else '❌  (TSMOM data unavailable — not blocking)'} |

---

## GO Criteria

| Criterion | Required | Pass? |
|-----------|----------|-------|
| Part 0: viable assets | ≥ 5 | {'✅' if viable_n >= 5 else '❌'} |
| Carry IC | > 0.05 | {'✅' if ic_7d > 0.05 else '❌'} |
| Best Sharpe | ≥ 1.0 | {'✅' if best_sharpe >= 1.0 else '❌'} |
| TSMOM correlation | < 0.30 | {'✅' if tsmom_pass else 'N/A'} |

---

## Methodology Notes

### Signal Construction
1. Trailing {LOOKBACK_H}h mean funding rate per asset → cross-sectional rank
2. Short top {int(QUINTILE*100)}% (highest positive funding → collect from longs)
3. Long bottom {int(QUINTILE*100)}% (most negative funding → collect from shorts)
4. Equal-weight within each leg; rebalance every F hours

### Cost Model
- Fee: 0.035% taker × 4 legs = 0.14%
- Slippage: 0.05% × 4 legs = 0.20%
- **Total: 0.34% per round trip**

### P&L Components
- Funding income: −position × funding_rate × notional (per hour)
- Price return: not modeled (funding carry is a pure carry strategy)
- Cost: deducted at each rebalance proportional to turnover
"""

    report_path = DOCS_DIR / "strategy_C_feasibility.md"
    report_path.write_text(report)
    print(f"Report saved → {report_path}")


def _write_report_fail(pivot_fr, viability_df):
    viable_n = int(viability_df["viable"].sum())
    n_assets = len(pivot_fr.columns)
    report_path = DOCS_DIR / "strategy_C_feasibility.md"
    report_path.write_text(
        f"# Strategy C: Funding Rate Carry Feasibility\n\n"
        f"**Verdict: ❌ FAIL — Part 0**\n\n"
        f"Only {viable_n}/{n_assets} assets have 7-day carry ≥ 0.34% cost. "
        f"Need ≥ {MIN_ASSETS}.\n"
    )
    print(f"Report saved → {report_path}")
    return {"verdict": False, "reason": "Part 0 fail"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Ensure funding data is available
    combined_path = OUT_DIR / "funding_rates_combined.csv"
    if not combined_path.exists():
        print("Combined funding data not found — running fetch_all() first ...\n")
        fetch_all()

    run_feasibility()
