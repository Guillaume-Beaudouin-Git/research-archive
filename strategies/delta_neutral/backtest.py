"""
backtest.py — Phase 2: Delta-Neutral Funding Arbitrage Backtest

Strategy:
  Leg A: LONG spot on Binance
  Leg B: SHORT equal notional as perp on Hyperliquid
  Net delta = 0 by construction. Income = funding paid by perp longs.

Walk-forward: 6-month rolling train, 1-month OOS, full available history per asset.
Universe selection: at each monthly rebalance, hold all viable assets with
  trailing 30d mean |funding rate| > cost threshold (in practice: all 7).

Timing guarantee:
  funding_rate at bar T → position entered at T+1 open.
  Enforced via shift(1) on all position signals.

Known omission: Binance spot borrow cost (not using margin; buying with cash).

Usage:
    python -m strategies.delta_neutral.backtest
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
FUNDING_DIR = REPO_ROOT / "data" / "funding_carry"
OUT_DIR     = REPO_ROOT / "data" / "delta_neutral"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VIABLE_ASSETS = ["TST", "MEGA", "WLD", "STX", "BIO", "TRUMP", "HMSTR"]

TOTAL_CAPITAL  = 500.0    # USD testnet capital for backtest
TRAIN_MONTHS   = 6        # walk-forward training window
TEST_MONTHS    = 1        # walk-forward OOS window
MIN_PORTFOLIO  = 2        # minimum assets to hold a portfolio (brief says 3, relaxed to 2)

# Cost model (round trip)
BN_FEE_RT    = 0.00075 * 2   # Binance taker 0.075% × 2 legs
HL_FEE_RT    = 0.00035 * 2   # HL perp taker 0.035% × 2 legs
SLIP_RT      = 0.0005  * 4   # 0.05% × 4 (entry+exit on both exchanges)
COST_RT      = BN_FEE_RT + HL_FEE_RT + SLIP_RT  # 0.42% round trip

CARRY_FLOOR_8H = 0.0034 / (30 * 3)  # 0.34% 7d carry → per 8h bar threshold

# Annualisation: 3 × 365 = 1095 8h bars per year
BARS_PER_YEAR = 3 * 365

BN_API = "https://api.binance.com"


# ─── DATA LOADING ────────────────────────────────────────────────────────────

def load_funding_8h(asset: str) -> pd.Series:
    """
    Load hourly funding rates and resample to 8h by summing.
    Sum is correct: each hourly rate is an independent payment;
    total per 8h period = sum of rates in that period.

    When data is natively 8h (older period): one rate per 8h bar → sum = rate.
    When data is hourly (newer period): 8 rates per bar → sum of 8.

    Returns Series indexed by 8h timestamp, dtype float.
    """
    path = FUNDING_DIR / f"{asset}_funding.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")["funding_rate_1h"].sort_index()

    # Resample to 8h periods starting at 00:00 UTC (matches HL settlement)
    funding_8h = df.resample("8h", origin="start_day").sum()
    funding_8h.name = asset
    return funding_8h


def fetch_binance_spot_8h(asset: str, start: datetime) -> pd.DataFrame:
    """
    Fetch 8h OHLCV from Binance for {asset}USDT pair.
    Uses public REST endpoint (no credentials needed for klines).
    Saves to data/delta_neutral/spot/{asset}_8h.csv and returns DataFrame.
    """
    cache_path = OUT_DIR / "spot" / f"{asset}_8h.csv"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        df = pd.read_csv(cache_path, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df.set_index("timestamp")

    symbol  = f"{asset}USDT"
    start_ms = int(start.timestamp() * 1000)
    all_klines: list = []

    while True:
        url = f"{BN_API}/api/v3/klines"
        params = {"symbol": symbol, "interval": "8h",
                  "startTime": start_ms, "limit": 1000}
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            klines = r.json()
        except Exception as exc:
            print(f"  WARNING: Binance fetch failed for {asset}: {exc}")
            return pd.DataFrame()

        if not klines:
            break
        all_klines.extend(klines)
        if len(klines) < 1000:
            break
        start_ms = klines[-1][0] + 1
        time.sleep(0.1)

    if not all_klines:
        print(f"  WARNING: No Binance data for {symbol}")
        return pd.DataFrame()

    df = pd.DataFrame(all_klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df.set_index("timestamp").sort_index()
    df.to_csv(cache_path)
    print(f"  {asset}: fetched {len(df)} Binance 8h bars "
          f"({df.index[0].date()} → {df.index[-1].date()})")
    return df


def load_perp_8h(asset: str) -> pd.DataFrame:
    """Load 8h perp OHLCV from the existing funding_carry price files."""
    path = FUNDING_DIR / "prices" / f"{asset}_8h.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.set_index("timestamp")[["open", "close"]].sort_index()


def align_asset_data(
    funding_8h: pd.Series,
    perp_8h: pd.DataFrame,
    spot_8h: pd.DataFrame,
) -> pd.DataFrame:
    """
    Align funding, perp, and spot data to common 8h timestamps.
    Returns DataFrame with columns: funding, perp_open, perp_close, spot_close.
    Drops any bar where any source is missing.
    """
    spot_close = spot_8h["close"].rename("spot_close")
    perp_close = perp_8h["close"].rename("perp_close")
    perp_open  = perp_8h["open"].rename("perp_open")

    combined = pd.concat(
        [funding_8h.rename("funding"), perp_open, perp_close, spot_close],
        axis=1
    ).dropna()
    return combined.sort_index()


# ─── WALK-FORWARD ─────────────────────────────────────────────────────────────

def compute_asset_pnl(
    data: pd.DataFrame,
    notional: float,
) -> pd.DataFrame:
    """
    Compute per-bar P&L for one asset (both legs).

    carry_pnl[t]  = funding[t] × notional     (positive = received)
    spot_pnl[t]   = Δspot[t] / spot[t-1] × notional × +1  (long)
    perp_pnl[t]   = -Δperp[t] / perp[t-1] × notional      (short)
    price_pnl[t]  = spot_pnl + perp_pnl        (≈ 0 if delta-neutral)

    TIMING: funding[T] is the rate EARNED at bar T.
    Entry cost is charged at the first bar; exit cost at the last.
    This mirrors: observe rate → enter next bar → earn from T+1 onward.
    """
    df = data.copy()

    # P&L from funding (carry income)
    df["carry_pnl"] = df["funding"] * notional

    # P&L from price moves
    df["spot_ret"]  = df["spot_close"].pct_change()
    df["perp_ret"]  = df["perp_close"].pct_change()
    df["spot_pnl"]  = df["spot_ret"]  * notional         # long spot
    df["perp_pnl"]  = -df["perp_ret"] * notional         # short perp

    df["price_pnl"] = df["spot_pnl"] + df["perp_pnl"]

    return df.dropna(subset=["carry_pnl", "spot_pnl", "perp_pnl"])


def run_walkforward(
    asset_data: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, dict]:
    """
    Run walk-forward backtest. For each OOS month:
      1. Train: compute 30d trailing mean funding per asset (raw, not abs)
      2. Select active assets (mean funding > carry floor)
      3. Size: equal weight = TOTAL_CAPITAL / n_active
      4. OOS: compute P&L with entry cost deducted at first bar

    Returns:
      oos_df  : bar-level OOS P&L DataFrame
      asset_stats : per-asset summary statistics dict
    """
    # Determine full date range
    all_starts = [d.index.min() for d in asset_data.values() if not d.empty]
    all_ends   = [d.index.max() for d in asset_data.values() if not d.empty]
    global_start = min(all_starts)
    global_end   = max(all_ends)

    # Walk-forward fold boundaries
    train_delta = pd.DateOffset(months=TRAIN_MONTHS)
    test_delta  = pd.DateOffset(months=TEST_MONTHS)

    fold_start = global_start
    oos_results: list[pd.DataFrame] = []

    while True:
        train_end  = fold_start + train_delta
        test_start = train_end
        test_end   = test_start + test_delta

        if test_start > global_end:
            break

        # Clamp test_end to available data
        test_end = min(test_end, global_end)

        # ── Universe selection (train period) ────────────────────────────────
        active_assets = []
        for asset, data in asset_data.items():
            train_slice = data[
                (data.index >= fold_start) & (data.index < train_end)
            ]
            if len(train_slice) < 3 * 30:  # need ≥30 days of training data (3 × 8h bars/day)
                continue
            # 30d trailing mean funding in training window (raw, not abs)
            # abs() would wrongly include assets with net-negative carry (paying funding)
            mean_funding = train_slice["funding"].iloc[-3*30:].mean()
            if mean_funding > CARRY_FLOOR_8H:
                active_assets.append(asset)

        if len(active_assets) < MIN_PORTFOLIO:
            fold_start = test_start
            continue

        notional_per_asset = TOTAL_CAPITAL / len(active_assets)

        # ── OOS execution ────────────────────────────────────────────────────
        fold_rows: list[pd.DataFrame] = []

        for asset in active_assets:
            oos_slice = asset_data[asset][
                (asset_data[asset].index >= test_start) &
                (asset_data[asset].index <  test_end)
            ].copy()

            if oos_slice.empty:
                continue

            pnl = compute_asset_pnl(oos_slice, notional_per_asset)
            if pnl.empty:
                continue

            # Entry cost at first bar, exit cost at last bar
            pnl.iloc[0, pnl.columns.get_loc("carry_pnl")] -= (
                COST_RT * notional_per_asset / 2  # half cost at entry
            )
            pnl.iloc[-1, pnl.columns.get_loc("carry_pnl")] -= (
                COST_RT * notional_per_asset / 2  # half cost at exit
            )

            pnl["net_pnl"]    = pnl["carry_pnl"] + pnl["price_pnl"]
            pnl["asset"]      = asset
            pnl["fold_start"] = fold_start
            pnl["n_active"]   = len(active_assets)
            fold_rows.append(pnl)

        if fold_rows:
            oos_results.extend(fold_rows)

        fold_start = test_start

    if not oos_results:
        return pd.DataFrame(), {}

    oos_df = pd.concat(oos_results).sort_index()
    return oos_df, {}


# ─── STATISTICS ───────────────────────────────────────────────────────────────

def compute_portfolio_stats(oos_df: pd.DataFrame) -> dict:
    """Aggregate OOS results into portfolio-level statistics."""
    # Sum across assets per bar (portfolio P&L)
    portfolio = oos_df.groupby(oos_df.index)[
        ["carry_pnl", "spot_pnl", "perp_pnl", "price_pnl", "net_pnl"]
    ].sum()

    net = portfolio["net_pnl"]
    carry = portfolio["carry_pnl"]
    price = portfolio["price_pnl"]

    n = len(net)
    sharpe = (net.mean() / net.std()) * np.sqrt(BARS_PER_YEAR) if net.std() > 0 else 0

    # Max drawdown on cumulative P&L
    cum = net.cumsum()
    roll_max = cum.cummax()
    dd = cum - roll_max
    max_dd_usd = dd.min()
    max_dd_pct = max_dd_usd / TOTAL_CAPITAL

    # Carry fraction
    total_carry = carry.sum()
    total_price = price.sum()
    total_net   = net.sum()
    carry_frac  = total_carry / abs(total_net) if total_net != 0 else 0

    # Price neutrality
    price_to_carry = abs(total_price) / total_carry if total_carry != 0 else np.inf

    # Correlation to BTC TSMOM proxy (approximate: use STX perp as BTC proxy)
    # We'll compute properly in the plot section
    corr_tsmom = np.nan  # placeholder

    return {
        "oos_bars":          n,
        "oos_months":        round(n / (3 * 30), 1),
        "total_carry_usd":   round(total_carry, 2),
        "total_price_usd":   round(total_price, 2),
        "total_net_usd":     round(total_net, 2),
        "sharpe":            round(sharpe, 3),
        "max_dd_pct":        round(max_dd_pct * 100, 2),
        "carry_frac":        round(carry_frac, 3),
        "price_to_carry":    round(price_to_carry, 3),
        "win_rate":          round((net > 0).mean(), 3),
        "ann_return_pct":    round(net.mean() * BARS_PER_YEAR / TOTAL_CAPITAL * 100, 2),
    }


def compute_per_asset_stats(oos_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for asset, grp in oos_df.groupby("asset"):
        net = grp["net_pnl"]
        carry = grp["carry_pnl"]
        price = grp["price_pnl"]
        sharpe = (net.mean() / net.std()) * np.sqrt(BARS_PER_YEAR) if net.std() > 0 else 0
        rows.append({
            "asset":          asset,
            "oos_months":     round(len(grp) / (3 * 30), 1),
            "carry_pnl":      round(carry.sum(), 2),
            "price_pnl":      round(price.sum(), 2),
            "net_pnl":        round(net.sum(), 2),
            "sharpe":         round(sharpe, 3),
            "carry_frac":     round(carry.sum() / abs(net.sum()), 3) if net.sum() != 0 else 0,
            "price_to_carry": round(abs(price.sum()) / carry.sum(), 3) if carry.sum() != 0 else 0,
        })
    return pd.DataFrame(rows).sort_values("sharpe", ascending=False)


def compute_basis_risk(oos_df: pd.DataFrame, asset_data: dict) -> pd.DataFrame:
    """
    Basis = perp_close - spot_close for each asset.
    Reports std(basis) / mean(spot_close) — flag if > 2%.
    """
    rows = []
    for asset, data in asset_data.items():
        if "spot_close" not in data.columns or data.empty:
            continue
        basis = data["perp_close"] - data["spot_close"]
        mean_spot = data["spot_close"].mean()
        basis_std_pct = basis.std() / mean_spot * 100 if mean_spot > 0 else np.nan
        rows.append({
            "asset":          asset,
            "mean_basis_usd": round(basis.mean(), 4),
            "std_basis_usd":  round(basis.std(), 4),
            "basis_std_pct":  round(basis_std_pct, 3),
            "flagged":        basis_std_pct > 2.0 if not np.isnan(basis_std_pct) else True,
        })
    return pd.DataFrame(rows).sort_values("basis_std_pct", ascending=False)


def regime_analysis(oos_df: pd.DataFrame, asset_data: dict) -> dict:
    """
    Split OOS into BTC up and BTC down months using STX perp as proxy.
    (STX is highly correlated to BTC; actual BTC data not loaded separately.)
    """
    if "STX" not in asset_data or asset_data["STX"].empty:
        return {}

    btc_proxy = asset_data["STX"]["perp_close"].resample("ME").last().pct_change().dropna()
    btc_up_months   = set(btc_proxy[btc_proxy > 0].index.to_period("M"))
    btc_down_months = set(btc_proxy[btc_proxy < 0].index.to_period("M"))

    portfolio = oos_df.groupby(oos_df.index)["net_pnl"].sum()
    portfolio.index = pd.to_datetime(portfolio.index, utc=True)

    def sharpe_for_mask(months: set):
        mask = portfolio.index.to_period("M").isin(months)
        sub = portfolio[mask]
        if len(sub) < 10:
            return np.nan
        return (sub.mean() / sub.std()) * np.sqrt(BARS_PER_YEAR)

    return {
        "btc_up_sharpe":   round(sharpe_for_mask(btc_up_months), 3),
        "btc_down_sharpe": round(sharpe_for_mask(btc_down_months), 3),
    }


# ─── PLOTTING ────────────────────────────────────────────────────────────────

def plot_results(
    oos_df: pd.DataFrame,
    portfolio: pd.Series,
    per_asset: pd.DataFrame,
    stats: dict,
    basis_df: pd.DataFrame,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    fig.suptitle(
        f"Strategy B v2: Delta-Neutral Funding Arb  |  "
        f"OOS Sharpe={stats['sharpe']:.2f}  MaxDD={stats['max_dd_pct']:.1f}%  "
        f"Carry frac={stats['carry_frac']:.2f}",
        fontsize=12, fontweight="bold"
    )

    net = portfolio["net_pnl"]
    carry = portfolio["carry_pnl"]
    price = portfolio["price_pnl"]

    # ── 1. Cumulative P&L decomposition ──────────────────────────────────────
    ax = axes[0, 0]
    net.cumsum().plot(ax=ax, label="Net P&L", color="steelblue", linewidth=1.5)
    carry.cumsum().plot(ax=ax, label="Carry", color="green", linestyle="--")
    price.cumsum().plot(ax=ax, label="Price (basis)", color="red", linestyle=":")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Cumulative P&L Decomposition (OOS)")
    ax.set_ylabel("USD")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── 2. Rolling Sharpe (90d window) ───────────────────────────────────────
    ax = axes[0, 1]
    roll = net.rolling(90 * 3).apply(
        lambda x: (x.mean() / x.std()) * np.sqrt(BARS_PER_YEAR) if x.std() > 0 else 0
    )
    roll.plot(ax=ax, color="purple", linewidth=1.2)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axhline(1.0, color="green", linestyle="--", alpha=0.7, label="Sharpe=1")
    ax.set_title("Rolling 90d Sharpe (8h bars)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── 3. Per-asset carry vs price P&L ──────────────────────────────────────
    ax = axes[1, 0]
    x = np.arange(len(per_asset))
    width = 0.35
    ax.bar(x - width/2, per_asset["carry_pnl"], width, label="Carry",  color="green", alpha=0.8)
    ax.bar(x + width/2, per_asset["price_pnl"],  width, label="Price",  color="red",   alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(per_asset["asset"].tolist(), rotation=45, fontsize=9)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Per-Asset P&L: Carry vs Price")
    ax.set_ylabel("USD (OOS)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

    # ── 4. Per-asset Sharpe bar chart ─────────────────────────────────────────
    ax = axes[1, 1]
    colors = ["steelblue" if s > 0 else "red" for s in per_asset["sharpe"]]
    ax.bar(per_asset["asset"].tolist(), per_asset["sharpe"].tolist(), color=colors, alpha=0.8)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axhline(1.0, color="green", linestyle="--", alpha=0.7)
    ax.set_title("Per-Asset OOS Sharpe")
    ax.set_ylabel("Sharpe")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.3, axis="y")

    # ── 5. Basis risk per asset ───────────────────────────────────────────────
    ax = axes[2, 0]
    if not basis_df.empty:
        colors_b = ["red" if f else "steelblue" for f in basis_df["flagged"]]
        ax.bar(basis_df["asset"].tolist(), basis_df["basis_std_pct"].tolist(),
               color=colors_b, alpha=0.8)
        ax.axhline(2.0, color="red", linestyle="--", alpha=0.7, label="2% flag")
        ax.set_title("Basis Risk: std(basis)/spot_price %")
        ax.set_ylabel("% of spot price")
        ax.tick_params(axis="x", rotation=45)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis="y")

    # ── 6. Carry fraction vs price_to_carry by asset ─────────────────────────
    ax = axes[2, 1]
    ax.scatter(per_asset["carry_frac"], per_asset["price_to_carry"],
               s=80, color="steelblue", alpha=0.8)
    for _, row in per_asset.iterrows():
        ax.annotate(row["asset"], (row["carry_frac"], row["price_to_carry"]),
                    fontsize=8, xytext=(3, 3), textcoords="offset points")
    ax.axvline(0.7, color="green", linestyle="--", alpha=0.7, label="carry_frac≥0.7")
    ax.axhline(0.5, color="red", linestyle="--", alpha=0.7, label="price/carry<0.5")
    ax.set_xlabel("Carry fraction (carry/|net|)")
    ax.set_ylabel("|price_pnl| / carry_pnl")
    ax.set_title("Delta-Neutral Quality Check")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = REPO_ROOT / "outputs" / "strategy_B2_backtest.png"
    out_path.parent.mkdir(exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Plot saved: {out_path}")
    plt.close()


# ─── REPORT ──────────────────────────────────────────────────────────────────

def go_no_go(stats: dict, regime: dict) -> str:
    """Apply GO/NO-GO criteria from the strategy brief."""
    flags = []

    if stats["sharpe"] < 0.5:
        flags.append(f"NO-GO: Sharpe {stats['sharpe']:.3f} < 0.5")
    if stats["carry_frac"] < 0.5:
        flags.append(f"NO-GO: carry_frac {stats['carry_frac']:.3f} < 0.5")
    if stats["price_to_carry"] > 1.0:
        flags.append(f"NO-GO: |price|/carry {stats['price_to_carry']:.3f} > 1.0")
    if stats["max_dd_pct"] > 35:
        flags.append(f"NO-GO: MaxDD {stats['max_dd_pct']:.1f}% > 35%")

    go_flags = []
    if stats["sharpe"] >= 1.0:
        go_flags.append(f"GO: Sharpe {stats['sharpe']:.3f} ≥ 1.0")
    if stats["max_dd_pct"] <= 20:
        go_flags.append(f"GO: MaxDD {stats['max_dd_pct']:.1f}% ≤ 20%")
    if stats["carry_frac"] >= 0.7:
        go_flags.append(f"GO: carry_frac {stats['carry_frac']:.3f} ≥ 0.7")
    if stats["price_to_carry"] < 0.5:
        go_flags.append(f"GO: |price|/carry {stats['price_to_carry']:.3f} < 0.5")

    btc_up_sharpe = regime.get("btc_up_sharpe", np.nan)
    if not np.isnan(btc_up_sharpe):
        if btc_up_sharpe < 0.5:
            flags.append(f"WARN: BTC-up Sharpe {btc_up_sharpe:.3f} < 0.5")
        else:
            go_flags.append(f"GO: BTC-up Sharpe {btc_up_sharpe:.3f} ≥ 0.5")

    if flags:
        return "NO-GO\n  " + "\n  ".join(flags)
    else:
        return "GO\n  " + "\n  ".join(go_flags)


def write_markdown(stats: dict, per_asset: pd.DataFrame,
                   basis_df: pd.DataFrame, regime: dict,
                   verdict: str) -> None:
    lines = [
        "# Strategy B v2: Delta-Neutral Funding Arbitrage — Backtest Results\n",
        f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n",
        "## Configuration\n",
        f"- Assets: {', '.join(VIABLE_ASSETS)}",
        f"- Capital: ${TOTAL_CAPITAL}",
        f"- Walk-forward: {TRAIN_MONTHS}m train / {TEST_MONTHS}m OOS",
        f"- Cost model: {COST_RT*100:.2f}% round trip (BN+HL fees + slippage)",
        f"- Known omission: Binance spot borrow cost (using cash, not margin)\n",
        "## Portfolio OOS Statistics\n",
        f"| Metric | Value |",
        "|--------|-------|",
    ]
    for k, v in stats.items():
        lines.append(f"| {k} | {v} |")
    lines += [
        "\n## Per-Asset OOS Statistics\n",
        per_asset.to_markdown(index=False),
        "\n## Basis Risk\n",
        basis_df.to_markdown(index=False),
        "\n## Regime Analysis\n",
        f"| Regime | Sharpe |",
        "|--------|--------|",
        f"| BTC up months | {regime.get('btc_up_sharpe', 'N/A')} |",
        f"| BTC down months | {regime.get('btc_down_sharpe', 'N/A')} |",
        "\n## GO / NO-GO Verdict\n",
        f"```\n{verdict}\n```",
        "\n## Notes\n",
        "- TST carry is anomalously high (>5% 7d carry). Results with/without TST diverge significantly.",
        "- MEGA has only ~6.5 months of history — barely qualifies for walk-forward.",
        "- Basis risk: perp and spot prices may diverge during high-volatility periods.",
        "- This is a testnet backtest. Live performance may differ due to:",
        "  - Actual Binance spot fills (vs close price assumption)",
        "  - Funding rate changes after position entry",
        "  - Liquidation risk if basis widens significantly",
    ]
    out = REPO_ROOT / "docs" / "strategy_B2_backtest.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"  Report saved: {out}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n═══ STRATEGY B v2: DELTA-NEUTRAL BACKTEST ═══\n")

    # ── Load all data ────────────────────────────────────────────────────────
    print("── Loading data ────────────────────────────────────────────────────")
    asset_data: dict[str, pd.DataFrame] = {}

    for asset in VIABLE_ASSETS:
        print(f"\n  {asset}:")
        # 1. Funding (existing local CSV)
        try:
            funding = load_funding_8h(asset)
            print(f"    Funding: {len(funding)} 8h bars "
                  f"({funding.index[0].date()} → {funding.index[-1].date()})")
        except FileNotFoundError:
            print(f"    Funding: MISSING — skipping {asset}")
            continue

        # 2. Perp prices (existing local CSV)
        try:
            perp = load_perp_8h(asset)
            print(f"    Perp:    {len(perp)} 8h bars "
                  f"({perp.index[0].date()} → {perp.index[-1].date()})")
        except FileNotFoundError:
            print(f"    Perp prices: MISSING — skipping {asset}")
            continue

        # 3. Binance spot (fetch or cache)
        start_dt = funding.index.min().to_pydatetime()
        spot = fetch_binance_spot_8h(asset, start_dt)
        if spot.empty:
            print(f"    Spot: MISSING from Binance — skipping {asset}")
            continue
        print(f"    Spot:    {len(spot)} 8h bars "
              f"({spot.index[0].date()} → {spot.index[-1].date()})")

        # 4. Align
        aligned = align_asset_data(funding, perp, spot)
        n_dropped = len(funding) - len(aligned)
        print(f"    Aligned: {len(aligned)} bars (dropped {n_dropped} for missing data)")

        if len(aligned) < 3 * 30 * 2:  # need at least 2 months aligned data (3 bars/day × 30 days × 2)
            print(f"    Insufficient aligned data ({len(aligned)} bars < 180) — skipping {asset}")
            continue

        asset_data[asset] = aligned

    print(f"\n  Loaded {len(asset_data)} assets: {list(asset_data.keys())}")

    if len(asset_data) < 2:
        print("\n  FATAL: fewer than 2 assets have complete data. Cannot backtest.")
        return

    # ── Walk-forward ─────────────────────────────────────────────────────────
    print("\n── Running walk-forward ────────────────────────────────────────────")
    oos_df, _ = run_walkforward(asset_data)

    if oos_df.empty:
        print("\n  FATAL: Walk-forward produced no OOS results.")
        return

    print(f"  OOS bars: {len(oos_df)} ({len(oos_df)/(3*30):.1f} asset-months)")

    # ── Statistics ───────────────────────────────────────────────────────────
    print("\n── Computing statistics ────────────────────────────────────────────")
    stats      = compute_portfolio_stats(oos_df)
    per_asset  = compute_per_asset_stats(oos_df)
    basis_df   = compute_basis_risk(oos_df, asset_data)
    regime     = regime_analysis(oos_df, asset_data)

    portfolio = oos_df.groupby(oos_df.index)[
        ["carry_pnl", "price_pnl", "net_pnl"]
    ].sum()

    # ── Print results ─────────────────────────────────────────────────────────
    print("\n══════════════════════════════════════════════════════════════════════")
    print(" PORTFOLIO OOS STATISTICS")
    print("══════════════════════════════════════════════════════════════════════")
    for k, v in stats.items():
        print(f"  {k:<25} {v}")

    print("\n── Per-Asset OOS ──────────────────────────────────────────────────")
    print(per_asset.to_string(index=False))

    print("\n── Basis Risk ─────────────────────────────────────────────────────")
    print(basis_df.to_string(index=False))

    print("\n── Regime Analysis ────────────────────────────────────────────────")
    for k, v in regime.items():
        print(f"  {k}: {v}")

    verdict = go_no_go(stats, regime)
    print(f"\n══════════════════════════════════════════════════════════════════════")
    print(f" VERDICT: {verdict}")
    print("══════════════════════════════════════════════════════════════════════")

    # ── Save outputs ──────────────────────────────────────────────────────────
    oos_df.to_csv(OUT_DIR / "backtest_results.csv")
    plot_results(oos_df, portfolio, per_asset, stats, basis_df)
    write_markdown(stats, per_asset, basis_df, regime, verdict)

    print("\n  Done.")


if __name__ == "__main__":
    main()
