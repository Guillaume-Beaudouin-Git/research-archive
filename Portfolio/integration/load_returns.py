"""
load_returns.py — Historical returns loader for each strategy
==============================================================
Returns daily fractional returns (not $) for each strategy,
normalised to a common capital base so they can be combined.

Strategy A — TSMOM v3 (crypto, C1 config: tanh t-stat 28d)
  Source: backtest proxy (live only 17 days as of 2026-05-21)
  Method: yfinance download + tsmom_v3 signal logic
  Capital: fractional return → scale to $5000 Propr account

Strategy B — Delta-neutral carry (HL perp short + Binance spot long)
  Source: backtest CSV (data/metadata/delta_neutral_backtest.csv)
           live only 4 days as of 2026-05-21
  Method: aggregate 8h net_pnl to daily, divide by TOTAL_CAPITAL=$500
  Returns: absolute daily $ P&L (not %, because notional is fixed)

Strategy C — NQ opening momentum (iter_05 A$400 + B1.2%)
  Source: backtest via NQBacktestEngine
  Method: run engine, extract daily P&L, scale to 0.25 contracts on $50K

All three are normalised to daily fractional returns (%) before combination.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

log = logging.getLogger(__name__)

# ── Capital bases ─────────────────────────────────────────────────────────────
CAPITAL_A = 5_000.0    # Propr testnet USDC account
CAPITAL_B = 500.0      # delta-neutral backtest notional (TOTAL_CAPITAL in backtest.py)
CAPITAL_C = 50_000.0   # NQ paper trading account
CONTRACTS_C = 0.25     # production sizing (Decision B)

# ─────────────────────────────────────────────────────────────────────────────
# Strategy A — TSMOM v3 (C1: tanh t-stat 28d, long-only)
# ─────────────────────────────────────────────────────────────────────────────

def load_returns_A(
    test_start: str = "2023-01-01",
    data_end:   str = "2026-05-20",
) -> pd.Series:
    """
    Compute TSMOM v3 C1 backtest daily fractional returns.

    Uses tsmom_v3.signal functions directly (same as production).
    Returns pd.Series indexed by date, values = daily fractional return
    (e.g. 0.002 = +0.2% day).

    Data source: yfinance (crypto universe, 2020-01-01 onwards).
    Live history: only 17 days as of 2026-05-21 → using backtest as proxy.
    """
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf

    from strategies.tsmom_v3.signal import (
        continuous_signal, build_positions,
    )

    UNIVERSE = [
        "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD", "DOGE-USD",
        "ADA-USD", "DOT-USD", "UNI-USD", "LTC-USD", "BCH-USD",
        "MATIC-USD", "OP-USD", "ARB-USD",
    ]
    VOL_TARGET   = 0.18
    COST_PER_LEG = 0.00085

    log.info("Strategy A: downloading crypto prices (yfinance)...")
    raw = yf.download(UNIVERSE, start="2020-01-01", end=data_end,
                      auto_adjust=True, progress=False)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    raw = raw.ffill()
    available = [c for c in UNIVERSE if c in raw.columns and raw[c].dropna().shape[0] > 100]
    raw = raw[available]
    log_ret = np.log(raw / raw.shift(1)).clip(-1.0, 1.0)

    log.info(f"  Universe: {len(available)} assets  "
             f"Range: {raw.index[0].date()} → {raw.index[-1].date()}")

    # C1 config: tanh t-stat 28d (production spec)
    sig = continuous_signal(log_ret, lookback=28)   # C1 config: 28d tanh t-stat
    pos = build_positions(sig, log_ret, VOL_TARGET)

    # P&L: mean(positions × arithmetic returns) − costs
    arith = raw.pct_change().fillna(0.0)
    held  = pos.shift(1).fillna(0.0)
    gross = (held * arith).mean(axis=1)
    is_mon = pd.Series(raw.index.dayofweek == 0, index=raw.index).astype(float)
    turn   = pos.diff().abs()
    costs  = (turn * COST_PER_LEG * is_mon.values.reshape(-1, 1)).mean(axis=1)
    pnl_frac = gross - costs

    # OOS period only
    pnl_oos = pnl_frac[pnl_frac.index >= test_start]
    pnl_oos.name = "A"

    log.info(f"  Strategy A: {len(pnl_oos)} daily obs  "
             f"[{pnl_oos.index[0].date()} → {pnl_oos.index[-1].date()}]  "
             f"Ann ret: {pnl_oos.mean()*252*100:.1f}%  "
             f"Sharpe (naive): {pnl_oos.mean()/pnl_oos.std()*252**0.5:.2f}")
    return pnl_oos


# ─────────────────────────────────────────────────────────────────────────────
# Strategy B — Delta-neutral carry
# ─────────────────────────────────────────────────────────────────────────────

def load_returns_B(
    data_path: str | None = None,
) -> pd.Series:
    """
    Load delta-neutral carry backtest returns from the pre-computed CSV.

    Source: data/metadata/delta_neutral_backtest.csv
    (copied from VPS /home/algo/projects/Algo_claude/data/delta_neutral/backtest_results.csv)

    The CSV has 8h-interval rows with columns:
      timestamp, funding, ..., net_pnl, asset, fold_start, n_active

    Aggregation:
      - Parse timestamp → date (UTC)
      - Sum net_pnl across assets per UTC date (portfolio = all active assets)
      - Divide by CAPITAL_B ($500) → fractional daily return

    Live history: only 4 days as of 2026-05-21 (TST + MEGA, $50 each)
      → cumulative_carry = 0.0 → using backtest as proxy.
    """
    if data_path is None:
        data_path = str(ROOT / "data" / "metadata" / "delta_neutral_backtest.csv")

    log.info(f"Strategy B: loading delta-neutral backtest from {data_path}...")
    df = pd.read_csv(data_path)
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["ts"].dt.normalize().dt.tz_localize(None)

    # Aggregate: sum net_pnl across all active assets per UTC day
    daily = df.groupby("date")["net_pnl"].sum()

    # Fractional return = daily $ / backtest capital
    pnl_frac = daily / CAPITAL_B
    pnl_frac.name = "B"
    pnl_frac = pnl_frac.sort_index()

    log.info(f"  Strategy B: {len(pnl_frac)} daily obs  "
             f"[{pnl_frac.index[0].date()} → {pnl_frac.index[-1].date()}]  "
             f"Ann ret: {pnl_frac.mean()*252*100:.1f}%  "
             f"Sharpe (naive): {pnl_frac.mean()/pnl_frac.std()*252**0.5:.2f}")
    return pnl_frac


# ─────────────────────────────────────────────────────────────────────────────
# Strategy C — NQ opening momentum (iter_05 A$400 + B1.2%)
# ─────────────────────────────────────────────────────────────────────────────

def load_returns_C() -> pd.Series:
    """
    Reconstruct daily P&L from NQ iter_05 backtest.

    Steps:
      1. Load NQ 1-min data via data.cache.load_nq_1min()
      2. Build opening features (iter_05.build_opening_features)
      3. Build signals (A$400 + B1.2%)
      4. Run NQBacktestEngine
      5. Aggregate to daily P&L, scale to 0.25 contracts
      6. Return fractional returns vs CAPITAL_C ($50K)

    Backtest period: 2022-12-26 → 2025-12-11 (3 years OOS).
    """
    from data.cache import load_nq_1min
    from Futures.research.active.nq_intraday.engine import NQBacktestEngine, POINT_VALUE, COST_RT
    from Futures.research.active.nq_intraday.iter_05 import (
        build_opening_features, signals_from_features,
    )

    log.info("Strategy C: loading NQ 1-min data...")
    df = load_nq_1min()
    engine = NQBacktestEngine(df)

    log.info("  Building features + iter_05 signals (A$400 + B1.2%)...")
    feats = build_opening_features(engine.rth)
    sigs  = signals_from_features(feats, gap_thresh=0.012, dollar_stop=400.0)

    log.info(f"  Signals: {len(sigs)}")
    trade_log, _ = engine.run(sigs)

    if trade_log.empty:
        log.warning("  No trades in NQ backtest!")
        return pd.Series(dtype=float, name="C")

    # Scale to 0.25 contracts
    trade_log["pnl_025c"] = trade_log["pnl_usd"] * CONTRACTS_C

    # Aggregate to daily
    trade_log["date"] = pd.to_datetime(trade_log["entry_ts"]).dt.normalize().dt.tz_localize(None)
    daily = trade_log.groupby("date")["pnl_025c"].sum()

    # Forward-fill through trading calendar gaps (weekends → 0 return)
    # Strategy only trades RTH days — fill missing days with 0
    full_idx = pd.date_range(daily.index.min(), daily.index.max(), freq="B")
    daily = daily.reindex(full_idx, fill_value=0.0)

    # Fractional return vs capital
    pnl_frac = daily / CAPITAL_C
    pnl_frac.name = "C"

    log.info(f"  Strategy C: {len(pnl_frac)} daily obs  "
             f"[{pnl_frac.index[0].date()} → {pnl_frac.index[-1].date()}]  "
             f"Ann ret: {pnl_frac.mean()*252*100:.1f}%  "
             f"Sharpe (naive): {pnl_frac.mean()/pnl_frac.std()*252**0.5:.2f}")
    return pnl_frac


# ─────────────────────────────────────────────────────────────────────────────
# Combined loader
# ─────────────────────────────────────────────────────────────────────────────

def load_all_returns(
    align_start: str = "2023-01-01",
) -> pd.DataFrame:
    """
    Load all 3 strategies, align to common date range, return combined DataFrame.

    Args:
        align_start: earliest date to include (default: TSMOM v3 OOS start)

    Returns:
        DataFrame with columns A, B, C; index = date; values = daily frac returns.
        Missing days filled with 0 (strategy not trading that day).
    """
    ret_A = load_returns_A()
    ret_B = load_returns_B()
    ret_C = load_returns_C()

    # Align: outer join, fill NaN with 0 (strategy flat/not deployed)
    combined = pd.concat([ret_A, ret_B, ret_C], axis=1, join="outer").fillna(0.0)
    combined = combined[combined.index >= align_start].sort_index()

    overlap_start = max(
        ret_A.index.min(), ret_B.index.min(), ret_C.index.min()
    )
    overlap_end = min(
        ret_A.index.max(), ret_B.index.max(), ret_C.index.max()
    )

    log.info(f"\nCombined returns: {len(combined)} days  "
             f"[{combined.index[0].date()} → {combined.index[-1].date()}]")
    log.info(f"  Overlap (all 3 strategies): "
             f"{overlap_start.date()} → {overlap_end.date()}")

    return combined
