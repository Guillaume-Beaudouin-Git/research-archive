"""
run_backtest.py — Strategy D: Weekend Return Anomaly (BTC perpetual)

Signal  : day-of-week indicator only (no free parameters)
Trade   : Short BTC perp at Friday 16:00 UTC close → exit at Monday 00:00 UTC open
Duration: 56 hours (7 × 8h bars)
Income  : short price P&L + funding income (shorts collect positive funding)
Cost    : 0.34% round-trip per trade
Sharpe  : weekly frequency (×√52)

Usage:
    python -m strategies.weekend_anomaly.run_backtest
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

PRICES_PATH  = REPO_ROOT / "data" / "funding_carry" / "prices" / "BTC_8h.csv"
FUNDING_PATH = REPO_ROOT / "data" / "funding_carry" / "BTC_funding.csv"
DOCS_DIR     = REPO_ROOT / "docs"
DOCS_DIR.mkdir(exist_ok=True)

NOTIONAL     = 10_000.0   # $ notional per trade
COST_RT      = 0.0034     # 0.34% round-trip
SHARPE_SCALE = np.sqrt(52)  # weekly Sharpe

# GO criteria
SHARPE_THRESHOLD = 1.0
MAX_DD_THRESHOLD = 0.30    # fraction of notional


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data() -> tuple[pd.DataFrame, pd.Series]:
    """Return (px_8h DataFrame, btc_funding_hourly Series)."""
    px = pd.read_csv(PRICES_PATH, parse_dates=["timestamp"])
    px["timestamp"] = pd.to_datetime(px["timestamp"], utc=True)
    px = px.set_index("timestamp").sort_index()

    fr = pd.read_csv(FUNDING_PATH, parse_dates=["timestamp"])
    fr["timestamp"] = pd.to_datetime(fr["timestamp"], utc=True)
    fr = fr.set_index("timestamp")["funding_rate_1h"].sort_index()

    return px, fr


# ---------------------------------------------------------------------------
# Trade identification
# ---------------------------------------------------------------------------

def find_trades(px: pd.DataFrame) -> list[dict]:
    """
    Find all Friday 16:00 UTC entry bars.
    Entry  = open of the NEXT bar after Friday 16:00 (= Sat 00:00 open).
    Exit   = open of Monday 00:00 bar (Friday 16:00 + 56h).
    Position: SHORT (−1).
    """
    trades = []
    idx = px.index

    for i, ts in enumerate(idx):
        # Friday = weekday 4, hour = 16
        if ts.weekday() != 4 or ts.hour != 16:
            continue

        entry_ts = ts + pd.Timedelta(hours=8)   # Sat 00:00 (open of next bar)
        exit_ts  = ts + pd.Timedelta(hours=56)  # Mon 00:00

        if entry_ts not in idx or exit_ts not in idx:
            continue

        trades.append({
            "signal_ts": ts,
            "entry_ts":  entry_ts,
            "exit_ts":   exit_ts,
        })

    return trades


# ---------------------------------------------------------------------------
# P&L computation
# ---------------------------------------------------------------------------

def compute_trade_pnl(
    trade: dict,
    px: pd.DataFrame,
    fr: pd.Series,
) -> dict:
    """Compute P&L for a single weekend short trade."""
    entry_ts = trade["entry_ts"]
    exit_ts  = trade["exit_ts"]

    entry_price = px.loc[entry_ts, "open"]
    exit_price  = px.loc[exit_ts,  "open"]

    # Price P&L: short position → profit if price falls
    price_ret   = (exit_price - entry_price) / entry_price   # raw return
    price_pnl   = -price_ret * NOTIONAL                       # short

    # Funding income: short collects positive funding
    # Funding timestamps in the data are 8h epochs (00:00, 08:00, 16:00)
    # Each row = avg 1h rate for the 8h period starting at that timestamp
    # Funding accumulated during hold = sum(funding_rate_1h × 8h × −position)
    # For a short position (−1): income = +rate × 8 × notional per period
    mask = (fr.index >= entry_ts) & (fr.index < exit_ts)
    funding_rates = fr.loc[mask]
    funding_pnl   = funding_rates.sum() * 8 * NOTIONAL  # 8h per period, short collects

    # Costs: 0.34% round-trip on notional
    fees = COST_RT * NOTIONAL

    net_pnl = price_pnl + funding_pnl - fees

    return {
        "entry_ts":    entry_ts,
        "exit_ts":     exit_ts,
        "entry_price": entry_price,
        "exit_price":  exit_price,
        "price_ret":   price_ret,
        "price_pnl":   price_pnl,
        "funding_pnl": funding_pnl,
        "fees":        fees,
        "net_pnl":     net_pnl,
    }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def max_drawdown(cum_pnl: pd.Series) -> float:
    """Maximum drawdown in $ from cumulative P&L series."""
    peak = cum_pnl.cummax()
    dd   = (peak - cum_pnl).max()
    return float(dd)


def compute_metrics(results: pd.DataFrame) -> dict:
    net = results["net_pnl"]
    cum = net.cumsum()

    sharpe = float(net.mean() / net.std() * SHARPE_SCALE) if net.std() > 0 else 0.0
    mdd    = max_drawdown(cum)

    return {
        "n_trades":      len(net),
        "total_net_pnl": float(net.sum()),
        "total_price":   float(results["price_pnl"].sum()),
        "total_funding": float(results["funding_pnl"].sum()),
        "total_fees":    float(results["fees"].sum()),
        "win_rate":      float((net > 0).mean()),
        "sharpe":        sharpe,
        "max_dd":        mdd,
        "max_dd_pct":    mdd / NOTIONAL,
    }


def year_by_year(results: pd.DataFrame) -> pd.DataFrame:
    results = results.copy()
    results["year"] = results["entry_ts"].dt.year

    rows = []
    for yr, grp in results.groupby("year"):
        net = grp["net_pnl"]
        cum = net.cumsum()
        sh  = float(net.mean() / net.std() * SHARPE_SCALE) if net.std() > 0 else 0.0
        mdd = max_drawdown(cum)
        rows.append({
            "year":         yr,
            "n_trades":     len(grp),
            "total_net":    round(net.sum(), 0),
            "price_pnl":    round(grp["price_pnl"].sum(), 0),
            "funding_pnl":  round(grp["funding_pnl"].sum(), 0),
            "fees":         round(grp["fees"].sum(), 0),
            "win_rate":     f"{(net > 0).mean():.0%}",
            "sharpe":       round(sh, 2),
            "max_dd":       round(mdd, 0),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

REPORT_TEMPLATE = """\
# Strategy D: Weekend Return Anomaly (BTC Perpetual)

**Generated:** 2026-05-05 UTC
**Universe:** BTC-USDT perpetual (Hyperliquid)
**Signal:** Day-of-week indicator — no free parameters
**Trade:** Short BTC perpetual Friday 16:00 UTC → Monday 00:00 UTC (56h hold)
**Income:** Short price P&L + funding income (shorts collect positive funding)
**Cost:** 0.34% round-trip per trade
**Notional:** $10,000 per trade
**Sharpe scale:** weekly (×√52)

---

## Verdict: {verdict}

---

## Overall Metrics

| Metric | Value |
|--------|-------|
| Trades | {n_trades} |
| Total Net P&L | ${total_net_pnl:+,.0f} |
| Total Price P&L | ${total_price:+,.0f} |
| Total Funding Income | ${total_funding:+,.0f} |
| Total Fees | −${total_fees:,.0f} |
| Win Rate | {win_rate:.0%} |
| **Sharpe (weekly)** | **{sharpe:.3f}** |
| Max Drawdown ($) | ${max_dd:,.0f} |
| Max Drawdown (% of notional) | {max_dd_pct:.1%} |

---

## GO Criteria

| Criterion | Required | Result | Pass? |
|-----------|----------|--------|-------|
| Sharpe (weekly) | ≥ 1.0 | {sharpe:.3f} | {sharpe_pass} |
| Max Drawdown | ≤ 30% of notional | {max_dd_pct:.1%} | {dd_pass} |

---

## Year-by-Year Breakdown

{yby_table}

---

## Decomposition

| Component | Amount | % of gross |
|-----------|--------|------------|
| Price P&L | ${total_price:+,.0f} | {price_frac:.1%} |
| Funding Income | ${total_funding:+,.0f} | {funding_frac:.1%} |
| Fees | −${total_fees:,.0f} | — |
| **Net P&L** | **${total_net_pnl:+,.0f}** | — |

---

## Methodology Notes

### Signal Construction
- Entry trigger: Friday 16:00 UTC bar (weekday=4, hour=16)
- Entry price: open of next bar (Saturday 00:00 UTC)
- Exit price: open of Monday 00:00 UTC bar (56h after signal)
- Position: SHORT (−1 × notional)
- No look-ahead bias: signal uses only day-of-week (no price data in signal)

### Funding Income
- BTC 8h funding rates from Hyperliquid (each row = avg 1h rate × 8h window)
- Short position collects: +funding_rate × 8h × notional per 8h period
- Weekend window: 7 funding periods (Sat 00:00, Sat 08:00, Sat 16:00, Sun 00:00, Sun 08:00, Sun 16:00, Sun 24:00/Mon 00:00 [excluded, exit point])
- Summed: total_funding_rate × 8 × notional

### Cost Model
- 0.035% taker fee × 2 sides + 0.05% slippage × 2 sides = 0.34% round-trip
- Applied per trade on full notional

### Mechanism (Weekend Effect)
- Documented in crypto literature (extension of Lou, Polk & Skouras 2019):
  BTC tends to underperform Friday close → Monday open vs weekday periods
- Proposed drivers: lower institutional participation on weekends, retail deleveraging,
  options gamma unwind Friday close, reduced liquidity amplifying directional moves
- No parameters: signal is purely calendar-based, requiring no calibration window

---

## Notes

- Data from Hyperliquid (first available: {first_date})
- Full history used: no walk-forward needed (no parameters to select)
- Correlation to TSMOM (Strategy A, 28d signal): expected low (weekly vs monthly signal)
"""


def build_report(metrics: dict, yby: pd.DataFrame, first_date: str) -> str:
    verdict    = "✅ GO" if (metrics["sharpe"] >= SHARPE_THRESHOLD and
                             metrics["max_dd_pct"] <= MAX_DD_THRESHOLD) else "❌ NO-GO"
    sharpe_p   = "✅" if metrics["sharpe"] >= SHARPE_THRESHOLD else "❌"
    dd_p       = "✅" if metrics["max_dd_pct"] <= MAX_DD_THRESHOLD else "❌"

    gross      = abs(metrics["total_price"]) + abs(metrics["total_funding"])
    price_frac = metrics["total_price"] / gross if gross > 0 else 0
    fund_frac  = metrics["total_funding"] / gross if gross > 0 else 0

    yby_str = yby.to_string(index=False)

    return REPORT_TEMPLATE.format(
        verdict=verdict,
        n_trades=metrics["n_trades"],
        total_net_pnl=metrics["total_net_pnl"],
        total_price=metrics["total_price"],
        total_funding=metrics["total_funding"],
        total_fees=metrics["total_fees"],
        win_rate=metrics["win_rate"],
        sharpe=metrics["sharpe"],
        max_dd=metrics["max_dd"],
        max_dd_pct=metrics["max_dd_pct"],
        sharpe_pass=sharpe_p,
        dd_pass=dd_p,
        yby_table=yby_str,
        price_frac=price_frac,
        funding_frac=fund_frac,
        first_date=first_date,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading data...")
    px, fr = load_data()
    print(f"  BTC prices: {len(px):,} bars  ({px.index[0].date()} → {px.index[-1].date()})")
    print(f"  BTC funding: {len(fr):,} rows  ({fr.index[0].date()} → {fr.index[-1].date()})")

    print("\nFinding weekend trades...")
    trades = find_trades(px)
    print(f"  Found {len(trades)} Friday→Monday trades")

    print("\nComputing P&L...")
    records = [compute_trade_pnl(t, px, fr) for t in trades]
    results = pd.DataFrame(records)

    metrics = compute_metrics(results)
    yby     = year_by_year(results)

    print("\n" + "="*55)
    print(f"  Trades:      {metrics['n_trades']}")
    print(f"  Net P&L:     ${metrics['total_net_pnl']:+,.0f}")
    print(f"  Price P&L:   ${metrics['total_price']:+,.0f}")
    print(f"  Funding:     ${metrics['total_funding']:+,.0f}")
    print(f"  Fees:        -${metrics['total_fees']:,.0f}")
    print(f"  Win rate:    {metrics['win_rate']:.0%}")
    print(f"  Sharpe:      {metrics['sharpe']:.3f}  (weekly ×√52)")
    print(f"  Max DD:      ${metrics['max_dd']:,.0f}  ({metrics['max_dd_pct']:.1%} of notional)")
    print("="*55)

    go     = metrics["sharpe"] >= SHARPE_THRESHOLD and metrics["max_dd_pct"] <= MAX_DD_THRESHOLD
    verdict = "GO" if go else "NO-GO"
    print(f"\n  VERDICT: {verdict}")

    print("\nYear-by-year:")
    print(yby.to_string(index=False))

    first_date = str(px.index[0].date())
    report = build_report(metrics, yby, first_date)
    out_path = DOCS_DIR / "strategy_D_weekend_anomaly.md"
    out_path.write_text(report)
    print(f"\nReport written: {out_path}")

    return metrics, verdict


if __name__ == "__main__":
    main()
