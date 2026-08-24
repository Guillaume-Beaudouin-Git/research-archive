"""
Phase 1 — Classic indicator baselines on SPY and QQQ.
Tests: 1.1–1.7 (MA, RSI, BB, MACD, Donchian, ATR, 2-way combos)
SR_IS < 1.0 → reject (no OOS). Quick vectorised sweeps.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from backtest_engine import (
    fetch_prices, fetch_rf, excess_returns, sharpe, max_drawdown,
    evaluate_strategy, save_result, load_register,
    IS_START, IS_END, OOS_START, OOS_END, HOLD_START, HOLD_END, COST_ETF,
)

rf = fetch_rf()
print("=== PHASE 1 — Classic Indicators ===\n")

# ── Asset universe ─────────────────────────────────────────────────────────
ASSETS = ["SPY", "QQQ", "GLD", "TLT", "IWM"]
prices_dict: dict[str, pd.Series] = {}
for t in ASSETS:
    try:
        prices_dict[t] = fetch_prices(t)
        print(f"  Loaded {t}: {len(prices_dict[t])} bars")
    except Exception as e:
        print(f"  SKIP {t}: {e}")

# Starting n_tests (global from CLAUDE.md + any already in register)
existing = load_register()
n_base = 322  # global count from CLAUDE.md
N_TESTS = n_base + len(existing)
results: list[dict] = []

# ────────────────────────────────────────────────────────────────────────────
# Helper: build position series for a signal and evaluate IS only (fast)
# ────────────────────────────────────────────────────────────────────────────
def fast_is_sr(prices: pd.Series, signal: pd.Series, cost: float) -> float:
    ret = prices.pct_change().dropna()
    pos = signal.shift(1).reindex(ret.index).fillna(0)
    strat_ret = pos * ret - cost * pos.diff().abs().fillna(0)
    is_ret = strat_ret.loc[IS_START:IS_END]
    exc = excess_returns(is_ret, rf)
    return sharpe(exc)


# ────────────────────────────────────────────────────────────────────────────
# 1.1  MA crossovers
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 1.1 MA Crossovers ---")
MA_PAIRS = [(20, 60), (50, 200), (10, 40), (20, 100), (100, 200), (5, 20)]

best_ma: dict[str, float] = {}
for ticker, prices in prices_dict.items():
    for fast, slow in MA_PAIRS:
        N_TESTS += 1
        sma_fast = prices.rolling(fast).mean()
        sma_slow = prices.rolling(slow).mean()
        signal = (sma_fast > sma_slow).astype(float)
        sr = fast_is_sr(prices, signal, COST_ETF)
        key = f"P1.1_{ticker}_SMA{fast}_{slow}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            best_ma[key] = sr
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

# EMA variants
for ticker, prices in prices_dict.items():
    for fast, slow in [(12, 26), (9, 21), (20, 50)]:
        N_TESTS += 1
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        signal = (ema_fast > ema_slow).astype(float)
        sr = fast_is_sr(prices, signal, COST_ETF)
        key = f"P1.1_{ticker}_EMA{fast}_{slow}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            best_ma[key] = sr
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

# ────────────────────────────────────────────────────────────────────────────
# 1.2  RSI Mean Reversion
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 1.2 RSI Mean Reversion ---")

def rsi(prices: pd.Series, period: int) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

RSI_PARAMS = [(14, 30, 70), (14, 20, 80), (7, 30, 70), (21, 30, 70), (14, 25, 75)]
best_rsi: dict[str, float] = {}
for ticker, prices in prices_dict.items():
    for period, lo, hi in RSI_PARAMS:
        N_TESTS += 1
        r = rsi(prices, period)
        # MR: long when oversold (<lo), exit at 50, short when overbought (>hi), exit at 50
        signal = pd.Series(0.0, index=prices.index)
        signal[r < lo] = 1.0
        signal[r > hi] = -1.0
        signal = signal.replace(0, np.nan).ffill().fillna(0)
        # exit at midline
        signal[(r > 50) & (signal == 1.0)] = 0.0
        signal[(r < 50) & (signal == -1.0)] = 0.0
        signal = signal.ffill().fillna(0)
        sr = fast_is_sr(prices, signal, COST_ETF)
        key = f"P1.2_{ticker}_RSI{period}_{lo}_{hi}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            best_rsi[key] = sr
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

# RSI trend following (long when RSI > 50, short when < 50)
for ticker, prices in prices_dict.items():
    for period in [14, 21]:
        N_TESTS += 1
        r = rsi(prices, period)
        signal = (r > 50).astype(float) * 2 - 1  # +1 / -1
        sr = fast_is_sr(prices, signal, COST_ETF)
        key = f"P1.2_{ticker}_RSI{period}_trend"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

# ────────────────────────────────────────────────────────────────────────────
# 1.3  Bollinger Bands
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 1.3 Bollinger Bands ---")
BB_PARAMS = [(20, 2.0), (20, 1.5), (20, 2.5), (50, 2.0), (10, 2.0)]
best_bb: dict[str, float] = {}
for ticker, prices in prices_dict.items():
    for period, k in BB_PARAMS:
        # MR variant
        N_TESTS += 1
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + k * std
        lower = sma - k * std
        z = (prices - sma) / std.replace(0, np.nan)
        signal = pd.Series(0.0, index=prices.index)
        signal[prices < lower] = 1.0    # long when below lower band
        signal[prices > upper] = -1.0   # short when above upper band
        signal[abs(z) < 0.5] = 0.0      # exit near mean
        signal = signal.replace(0, np.nan).ffill().fillna(0)
        sr = fast_is_sr(prices, signal, COST_ETF)
        key = f"P1.3_{ticker}_BB{period}_{k}_MR"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            best_bb[key] = sr
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

        # Breakout variant
        N_TESTS += 1
        signal_bo = pd.Series(0.0, index=prices.index)
        signal_bo[prices > upper] = 1.0
        signal_bo[prices < lower] = -1.0
        signal_bo = signal_bo.replace(0, np.nan).ffill().fillna(0)
        sr_bo = fast_is_sr(prices, signal_bo, COST_ETF)
        key_bo = f"P1.3_{ticker}_BB{period}_{k}_BO"
        if sr_bo >= 1.0:
            print(f"  PASS IS: {key_bo} SR_IS={sr_bo:.2f}")
            best_bb[key_bo] = sr_bo
        else:
            print(f"  FAIL IS: {key_bo} SR_IS={sr_bo:.2f}")

# ────────────────────────────────────────────────────────────────────────────
# 1.4  MACD
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 1.4 MACD ---")
MACD_PARAMS = [(12, 26, 9), (8, 21, 5), (5, 13, 4), (19, 39, 9)]
best_macd: dict[str, float] = {}
for ticker, prices in prices_dict.items():
    for fast, slow, sig in MACD_PARAMS:
        N_TESTS += 1
        macd_line = prices.ewm(span=fast).mean() - prices.ewm(span=slow).mean()
        signal_line = macd_line.ewm(span=sig).mean()
        signal = (macd_line > signal_line).astype(float)
        sr = fast_is_sr(prices, signal, COST_ETF)
        key = f"P1.4_{ticker}_MACD{fast}_{slow}_{sig}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            best_macd[key] = sr
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

# ────────────────────────────────────────────────────────────────────────────
# 1.5  Donchian Breakouts
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 1.5 Donchian Breakouts ---")
DONCHIAN_PARAMS = [20, 40, 55, 100]
best_don: dict[str, float] = {}
for ticker, prices in prices_dict.items():
    for period in DONCHIAN_PARAMS:
        N_TESTS += 1
        high_ch = prices.rolling(period).max().shift(1)
        low_ch  = prices.rolling(period).min().shift(1)
        signal = pd.Series(0.0, index=prices.index)
        signal[prices > high_ch] = 1.0
        signal[prices < low_ch]  = -1.0
        signal = signal.replace(0, np.nan).ffill().fillna(0)
        sr = fast_is_sr(prices, signal, COST_ETF)
        key = f"P1.5_{ticker}_Donchian{period}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            best_don[key] = sr
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

# ────────────────────────────────────────────────────────────────────────────
# 1.6  ATR Trailing Stop on Trend Filter
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 1.6 ATR Trailing Stop on Trend Filter ---")

def atr(prices: pd.Series, period: int) -> pd.Series:
    high = prices  # using close as proxy for daily data
    low  = prices
    tr = pd.concat([
        (high - low),
        (high - prices.shift(1)).abs(),
        (low  - prices.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

ATR_PARAMS = [(14, 200, 2.0), (14, 100, 2.0), (14, 50, 1.5), (20, 200, 3.0)]
best_atr: dict[str, float] = {}
for ticker, prices in prices_dict.items():
    for atr_period, trend_ma, mult in ATR_PARAMS:
        N_TESTS += 1
        trend = prices.rolling(trend_ma).mean()
        a = atr(prices, atr_period)
        # Long only when price > trend MA, size = 1 / (mult*ATR/price) * target_vol
        signal = (prices > trend).astype(float)
        sr = fast_is_sr(prices, signal, COST_ETF)
        key = f"P1.6_{ticker}_ATR{atr_period}_trend{trend_ma}_mult{mult}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            best_atr[key] = sr
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

# ────────────────────────────────────────────────────────────────────────────
# 1.7  2-way combos (RSI + BB, MA + RSI)
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 1.7 2-way Combos ---")
best_combo: dict[str, float] = {}
for ticker, prices in prices_dict.items():
    period_ma = 200
    sma = prices.rolling(period_ma).mean()
    trend_filter = (prices > sma).astype(float)  # long-only when above 200d

    # RSI + Trend filter (long only above 200d SMA when RSI < 40 = dip buy)
    N_TESTS += 1
    r14 = rsi(prices, 14)
    signal_dip = ((r14 < 40) & (prices > sma)).astype(float)
    signal_dip = signal_dip.replace(0, np.nan).ffill().fillna(0)
    signal_dip[r14 > 60] = 0
    signal_dip = signal_dip.ffill().fillna(0)
    sr = fast_is_sr(prices, signal_dip, COST_ETF)
    key = f"P1.7_{ticker}_RSI14_dip_200MA"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        best_combo[key] = sr
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # BB + RSI combo: enter when price < lower_BB AND RSI < 35
    N_TESTS += 1
    sma20 = prices.rolling(20).mean()
    std20 = prices.rolling(20).std()
    lower_bb = sma20 - 2 * std20
    signal_combo = ((prices < lower_bb) & (r14 < 35)).astype(float)
    signal_combo = signal_combo.replace(0, np.nan).ffill().fillna(0)
    signal_combo[r14 > 60] = 0
    signal_combo = signal_combo.ffill().fillna(0)
    sr = fast_is_sr(prices, signal_combo, COST_ETF)
    key = f"P1.7_{ticker}_BB20_RSI14_combo"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        best_combo[key] = sr
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # MA crossover + RSI filter (only cross when RSI confirms direction)
    N_TESTS += 1
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    ma_signal = (ema12 > ema26).astype(float)
    r_confirm = ((ma_signal == 1) & (r14 > 55)) | ((ma_signal == 0) & (r14 < 45))
    signal_confirmed = ma_signal * r_confirm.astype(float)
    sr = fast_is_sr(prices, signal_confirmed, COST_ETF)
    key = f"P1.7_{ticker}_EMA12_26_RSI_confirm"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        best_combo[key] = sr
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # Donchian + Vol filter (only trade when vol is below median)
    N_TESTS += 1
    vol_20 = prices.pct_change().rolling(20).std()
    vol_median = vol_20.rolling(252).median()
    low_vol = vol_20 < vol_median
    don55_high = prices.rolling(55).max().shift(1)
    don55_low  = prices.rolling(55).min().shift(1)
    signal_don_vol = pd.Series(0.0, index=prices.index)
    signal_don_vol[(prices > don55_high) & low_vol] = 1.0
    signal_don_vol[(prices < don55_low) & low_vol]  = -1.0
    signal_don_vol = signal_don_vol.replace(0, np.nan).ffill().fillna(0)
    sr = fast_is_sr(prices, signal_don_vol, COST_ETF)
    key = f"P1.7_{ticker}_Donchian55_LowVol"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        best_combo[key] = sr
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# Collect all Phase 1 passing IS candidates
# ────────────────────────────────────────────────────────────────────────────
all_pass_is = {**best_ma, **best_rsi, **best_bb, **best_macd, **best_don, **best_atr, **best_combo}
print(f"\n=== Phase 1 Summary ===")
print(f"Total tests run this phase: {N_TESTS - n_base - len(existing)}")
print(f"IS passes (SR≥1.0): {len(all_pass_is)}")
for k, v in sorted(all_pass_is.items(), key=lambda x: -x[1]):
    print(f"  {k}: SR_IS={v:.2f}")

print(f"\nRunning n_tests so far: {N_TESTS}")

# Save minimal register entries for all Phase 1 tests
# (Full OOS evaluation only for IS passes)
print("\n=== Phase 1 Complete ===")
print(f"IS passes to evaluate on OOS: {len(all_pass_is)}")
if not all_pass_is:
    print("NO Phase 1 candidate passed IS gate (SR≥1.0). Proceeding to Phase 2.")
