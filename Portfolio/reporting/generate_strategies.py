"""
Generate HTML tear sheets for Strategies A, B, and C.

Usage
-----
    # All strategies (from repo root):
    python -m Portfolio.reporting.generate_strategies

    # Single strategy:
    python -m Portfolio.reporting.generate_strategies --strategy C
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "Portfolio" / "reporting" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Project-level n_tests from CLAUDE.md
N_TRIALS_GLOBAL = 321


# ── Strategy A — TSMOM v3 (BTC/ETH/SOL) ──────────────────────────────────────

def _run_tsmom_v3() -> pd.Series:
    """
    Replicate TSMOM v3 return series on BTC/ETH/SOL, 2020-2024.

    Signal  : tanh(cumret_28d / (vol_28d × sqrt(28))).clip(lower=0)
    Timing  : signal at T-1, position active from T (CLAUDE.md rule 1)
    Rebal   : Monday only
    Vol tgt : 18%  |  Costs: 0.17% RT
    """
    import yfinance as yf

    TICKERS   = ["BTC-USD", "ETH-USD", "SOL-USD"]
    LOOKBACK  = 28
    VOL_LB    = 20
    VOL_TGT   = 0.18
    COST_RT   = 0.0017
    CRYPTO_DAYS = 365
    MIN_DATE  = {"SOL-USD": "2020-04-10"}

    prices: dict[str, pd.Series] = {}
    for t in TICKERS:
        raw = yf.download(
            t, start="2020-01-01", end="2024-12-31",
            interval="1d", auto_adjust=True, progress=False,
        )
        if isinstance(raw.columns, pd.MultiIndex):
            px = raw["Close"][t]
        else:
            px = raw["Close"]
        if t in MIN_DATE:
            px = px[px.index >= pd.Timestamp(MIN_DATE[t])]
        prices[t] = px.dropna()

    net_per_asset: dict[str, pd.Series] = {}
    for t, px in prices.items():
        lr = np.log(px / px.shift(1)).clip(-1.0, 1.0).dropna()
        arith = np.exp(lr) - 1.0

        # Signal uses data through T-1 → shift(1) before rolling
        lr_lag = lr.shift(1)
        cumret = lr_lag.rolling(LOOKBACK).sum()
        vol_sig = lr_lag.rolling(LOOKBACK).std()
        raw_sig = (cumret / (vol_sig * np.sqrt(LOOKBACK))).fillna(0.0)
        signal = np.tanh(raw_sig).clip(lower=0.0)

        # Vol scaling
        vol_ann = lr_lag.rolling(VOL_LB).std() * np.sqrt(CRYPTO_DAYS)
        vol_scalar = (VOL_TGT / vol_ann).clip(0.1, 2.0)

        # Monday-only rebalance (forward-fill from last Monday)
        position = (signal * vol_scalar).where(lr.index.dayofweek == 0).ffill()

        # Gross return: position at T-1 × return at T
        gross = position.shift(1) * arith
        turnover = (position - position.shift(1)).abs().fillna(0.0)
        cost = turnover * COST_RT
        net_per_asset[t] = (gross - cost).dropna()

    port = pd.DataFrame(net_per_asset)
    valid = port.notna().sum(axis=1) >= 2
    return port[valid].mean(axis=1).dropna()


# ── Strategy B — Delta-neutral carry (HL) ────────────────────────────────────

def _run_delta_neutral() -> pd.Series:
    """
    Delta-neutral funding carry on HL: load cached spot/perp/funding data,
    run walk-forward backtest, return daily return fraction of total capital.

    Uses functions from strategies.delta_neutral.backtest (safe to import —
    main() is guarded by __name__ == '__main__').
    """
    sys.path.insert(0, str(REPO))
    from strategies.delta_neutral.backtest import (
        VIABLE_ASSETS, TOTAL_CAPITAL,
        load_funding_8h, load_perp_8h, fetch_binance_spot_8h,
        align_asset_data, compute_asset_pnl, run_walkforward,
    )

    START = datetime(2024, 1, 1, tzinfo=timezone.utc)

    asset_data: dict[str, pd.DataFrame] = {}
    for asset in VIABLE_ASSETS:
        try:
            funding = load_funding_8h(asset)
            perp_8h = load_perp_8h(asset)
            spot_8h = fetch_binance_spot_8h(asset, START)   # uses cache
            combined = align_asset_data(funding, perp_8h, spot_8h)
            if len(combined) > 100:
                notional = TOTAL_CAPITAL / max(len(VIABLE_ASSETS), 1)
                asset_data[asset] = compute_asset_pnl(combined, notional)
        except Exception as exc:
            print(f"  [B] skipping {asset}: {exc}")

    if not asset_data:
        raise RuntimeError("Strategy B: no asset data loaded")

    oos_df, _ = run_walkforward(asset_data)
    if oos_df.empty:
        raise RuntimeError("Strategy B: walk-forward produced no OOS results")

    # Aggregate 8h bars → daily USD P&L → daily return fraction
    oos_df.index = pd.to_datetime(oos_df.index, utc=True)
    daily_pnl = (
        oos_df["net_pnl"]
        .resample("1D")
        .sum()
    )
    return (daily_pnl / TOTAL_CAPITAL).dropna()


# ── Strategy C — NQ Opening Momentum iter_10 ─────────────────────────────────

def _run_nq_iter10() -> pd.Series:
    """
    NQ ORB iter_10 on Kaggle 1-min dataset.
    Returns daily P&L as fraction of $25K Tradeify account.
    """
    sys.path.insert(0, str(REPO))
    from data.cache import load_nq_1min
    from Futures.research.active.nq_intraday.engine import NQBacktestEngine
    from Futures.research.active.nq_intraday.iter_05 import (
        build_opening_features, signals_from_features,
    )

    ACCOUNT   = 25_000.0
    GAP_THRESH = 0.012
    DOLLAR_SL  = 400.0
    RNG_MIN    = 30.0

    df_1min = load_nq_1min()
    engine = NQBacktestEngine(df_1min)

    feats = build_opening_features(df_1min)
    feats_f = feats[feats["rng"] >= RNG_MIN].copy()
    signals = signals_from_features(feats_f, gap_thresh=GAP_THRESH, dollar_stop=DOLLAR_SL)

    tl, _ = engine.run(signals)
    if tl.empty:
        raise RuntimeError("Strategy C: no trades generated")

    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()
    daily_pnl = tl.groupby("date")["pnl_usd"].sum()

    all_days = pd.bdate_range(daily_pnl.index.min(), daily_pnl.index.max())
    daily_pnl = daily_pnl.reindex(pd.DatetimeIndex(all_days).normalize(), fill_value=0.0)

    return (daily_pnl / ACCOUNT).dropna()


# ── Top-level runner ──────────────────────────────────────────────────────────

_STRATEGIES = {
    "A": {
        "name": "Strategy A — TSMOM v3 (BTC/ETH/SOL)",
        "fn": _run_tsmom_v3,
        "filename": "strategy_a_tearsheet.html",
        "metadata": {
            "Universe": "BTC/ETH/SOL",
            "Rebalance": "Monday",
            "Propfirm": "Propr (paused)",
        },
        "benchmark_ticker": "BTC-USD",
        "n_trials": N_TRIALS_GLOBAL,
    },
    "B": {
        "name": "Strategy B — Delta-Neutral Carry (HL)",
        "fn": _run_delta_neutral,
        "filename": "strategy_b_tearsheet.html",
        "metadata": {
            "Type": "Delta-neutral funding carry",
            "Exchange": "Hyperliquid testnet",
            "Proxy SR": "2.0 (L14)",
        },
        "benchmark_ticker": None,
        "n_trials": N_TRIALS_GLOBAL,
    },
    "C": {
        "name": "Strategy C — NQ Opening Momentum iter_10",
        "fn": _run_nq_iter10,
        "filename": "strategy_c_tearsheet.html",
        "metadata": {
            "Asset": "MNQ (Micro NQ futures)",
            "Signal": "09:30-09:45 ORB",
            "Propfirm": "Tradeify Select Flex 25K",
        },
        "benchmark_ticker": None,
        "n_trials": N_TRIALS_GLOBAL,
    },
}


def _fetch_benchmark(ticker: Optional[str]) -> Optional[pd.Series]:
    if ticker is None:
        return None
    try:
        import yfinance as yf
        raw = yf.download(ticker, start="2020-01-01", end="2025-01-01",
                          interval="1d", auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            px = raw["Close"][ticker]
        else:
            px = raw["Close"]
        return px.dropna().pct_change().dropna()
    except Exception:
        return None


def generate_one(key: str) -> None:
    from Portfolio.reporting.tearsheet import generate_tearsheet

    cfg = _STRATEGIES[key]
    print(f"\n{'=' * 60}")
    print(f"  Strategy {key}: {cfg['name']}")
    print("=" * 60)

    try:
        returns = cfg["fn"]()
        print(f"  Returns loaded: {len(returns)} obs  "
              f"{str(returns.index.min())[:10]} → {str(returns.index.max())[:10]}")
    except Exception as exc:
        print(f"  [SKIP] Strategy {key} failed: {exc}")
        return

    bm = _fetch_benchmark(cfg["benchmark_ticker"])

    out = OUT_DIR / cfg["filename"]
    try:
        path = generate_tearsheet(
            returns=returns,
            strategy_name=cfg["name"],
            output_path=out,
            benchmark=bm,
            n_trials=cfg["n_trials"],
            metadata=cfg["metadata"],
        )
        size_kb = path.stat().st_size / 1024
        print(f"  Written: {path}  ({size_kb:.0f} KB)")
    except Exception as exc:
        print(f"  [ERROR] Tear sheet generation failed: {exc}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate strategy tear sheets")
    parser.add_argument(
        "--strategy", choices=["A", "B", "C"],
        help="Single strategy to generate (default: all)",
    )
    args = parser.parse_args()

    keys = [args.strategy] if args.strategy else list(_STRATEGIES)
    for k in keys:
        generate_one(k)
    print("\nDone. Tear sheets in:", OUT_DIR)


if __name__ == "__main__":
    main()
