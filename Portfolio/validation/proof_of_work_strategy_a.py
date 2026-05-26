"""
CPCV Proof-of-Work — Strategy A (TSMOM v3, BTC/ETH/SOL).

Usage
-----
    python -m Portfolio.validation.proof_of_work_strategy_a

Steps
-----
1. Check for parquet cache at Portfolio/validation/data_cache/strategy_a_prices.parquet.
   If absent, fetch from yfinance and write cache.
2. Compute full TSMOM v3 returns (pure, no I/O) via tsmom_signal.compute_tsmom_returns().
3. Build backtest_fn via make_tsmom_backtest_fn() (slice test_idx on pre-computed returns).
4. Call generate_cpcv_report() with n_trials=159 (Strategy A crypto budget).
5. Print a comparison table: WF baseline 1.33 vs CPCV distribution.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_CACHE_DIR = Path(__file__).parent / "data_cache"
_CACHE_PATH = _CACHE_DIR / "strategy_a_prices.parquet"
_REPORT_PATH = Path(__file__).parent / "reports" / "strategy_a_cpcv.html"

_TICKERS = ["BTC-USD", "ETH-USD", "SOL-USD"]
_SOL_MIN_DATE = "2020-04-10"
_START = "2020-01-01"
_END = "2024-12-31"

WF_BASELINE_SHARPE = 1.33   # OOS Sharpe from 5-fold expanding WF (CLAUDE.md)
N_TRIALS = 159               # Crypto budget at time of Strategy A validation


def _fetch_prices() -> pd.DataFrame:
    """Fetch BTC/ETH/SOL from yfinance, cache to parquet."""
    import yfinance as yf

    if _CACHE_PATH.exists():
        print(f"  Loading prices from cache: {_CACHE_PATH}")
        return pd.read_parquet(_CACHE_PATH)

    print("  Fetching BTC/ETH/SOL from yfinance …")
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    prices: dict[str, pd.Series] = {}
    for t in _TICKERS:
        raw = yf.download(
            t, start=_START, end=_END,
            interval="1d", auto_adjust=True, progress=False,
        )
        if isinstance(raw.columns, pd.MultiIndex):
            px = raw["Close"][t]
        else:
            px = raw["Close"]
        if t == "SOL-USD":
            px = px[px.index >= pd.Timestamp(_SOL_MIN_DATE)]
        prices[t] = px.dropna()

    df = pd.DataFrame(prices)
    df.to_parquet(_CACHE_PATH)
    print(f"  Prices cached → {_CACHE_PATH} ({len(df)} rows)")
    return df


def main() -> None:
    from Portfolio.validation.pipeline import generate_cpcv_report
    from Portfolio.validation.strategies.tsmom_signal import (
        compute_tsmom_returns,
        make_tsmom_backtest_fn,
    )

    print("\n" + "=" * 60)
    print("CPCV Proof-of-Work — Strategy A (TSMOM v3)")
    print("=" * 60)

    # Step 1: prices
    prices = _fetch_prices()
    print(f"  Prices: {prices.shape[1]} assets, {len(prices)} bars "
          f"({str(prices.index.min())[:10]} → {str(prices.index.max())[:10]})")

    # Step 2: full returns
    print("  Computing TSMOM v3 portfolio returns …")
    returns = compute_tsmom_returns(prices)
    print(f"  Returns: {len(returns)} bars — "
          f"naive SR = {(returns.mean() / returns.std()) * (252 ** 0.5):.2f}")

    # Step 3: backtest_fn factory
    backtest_fn = make_tsmom_backtest_fn(returns)

    # Step 4: run CPCV once, reuse for both report and summary
    from Portfolio.validation.cpcv import run_cpcv as _run_cpcv

    result = _run_cpcv(
        returns=returns,
        backtest_fn=backtest_fn,
        target_n_paths=30,
    )
    report_path = generate_cpcv_report(
        returns=returns,
        strategy_name="Strategy A — TSMOM v3 (BTC/ETH/SOL)",
        backtest_fn=backtest_fn,
        n_trials=N_TRIALS,
        output_path=str(_REPORT_PATH),
        wf_baseline_sharpe=WF_BASELINE_SHARPE,
        _cpcv_result=result,
    )

    print("\n" + "=" * 60)
    print("CPCV PROOF-OF-WORK — STRATEGY A — RESULTS")
    print("=" * 60)
    print(f"  WF baseline Sharpe  : {WF_BASELINE_SHARPE:.2f}  (OOS, 5-fold expanding)")
    print(f"  CPCV n_paths        : {result['n_paths']}  "
          f"(k={result['n_folds']}, p={result['n_test_folds']})")
    print(f"  CPCV mean SR        : {result['mean']:.3f}")
    print(f"  CPCV median SR      : {result['median']:.3f}")
    print(f"  CPCV std SR         : {result['std']:.3f}")
    print(f"  CPCV CI [5%, 95%]   : [{result['ci_5_95'][0]:.2f}, {result['ci_5_95'][1]:.2f}]")

    delta = result["median"] - WF_BASELINE_SHARPE
    if delta >= -0.05:
        verdict = "CONSISTENT ✓ (CPCV confirms WF result)"
    elif delta >= -0.3:
        verdict = "MODERATE GAP — investigate"
    else:
        verdict = "LARGE GAP — overfitting risk"
    print(f"  CPCV median vs WF   : {delta:+.2f}  → {verdict}")
    print(f"\n  Report → {report_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
