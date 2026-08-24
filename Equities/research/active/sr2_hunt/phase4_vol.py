"""
Phase 4 — Volatility-aware strategies.
4.1 Vol targeting on near-passing P1 candidates
4.2 VIX regime filter (percentile-based)
4.3 NR4/NR7 vol squeeze breakout
4.4 Multi-asset defensive rotation
Also: VIX mean reversion as signal
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
from backtest_engine import (
    fetch_prices, fetch_rf, excess_returns, sharpe, max_drawdown,
    IS_START, IS_END, OOS_START, OOS_END, HOLD_START, HOLD_END, COST_ETF,
)
import json

rf = fetch_rf()
N_PREV = 632
N_TESTS = N_PREV
print("=== PHASE 4 — Volatility-Aware Strategies ===\n")

# ── Data ───────────────────────────────────────────────────────────────────
def fetch_ohlc(ticker: str) -> pd.DataFrame:
    df = yf.download(ticker, start="2013-01-01", end="2026-05-26",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    for col in ["Open", "High", "Low", "Close"]:
        if col not in df.columns:
            df[col] = df["Close"]
    return df[["Open", "High", "Low", "Close"]].dropna()

print("Fetching data...")
spy = fetch_ohlc("SPY")
qqq = fetch_ohlc("QQQ")
tlt = fetch_ohlc("TLT")
gld = fetch_ohlc("GLD")
iwm = fetch_ohlc("IWM")

# VIX from yfinance
vix_df = yf.download("^VIX", start="2013-01-01", end="2026-05-26",
                      auto_adjust=True, progress=False)
if isinstance(vix_df.columns, pd.MultiIndex):
    vix_df.columns = vix_df.columns.get_level_values(0)
vix = vix_df["Close"].dropna()
if isinstance(vix, pd.DataFrame):
    vix = vix.iloc[:, 0]

print(f"  SPY={len(spy)}, QQQ={len(qqq)}, TLT={len(tlt)}, GLD={len(gld)}")
print(f"  VIX={len(vix)}")

candidates: list[dict] = []

def fast_is_sr(strat_ret: pd.Series) -> float:
    r = strat_ret.loc[IS_START:IS_END]
    return sharpe(excess_returns(r, rf))

def full_eval(strat_ret: pd.Series, sid: str, desc: str, phase: str,
              params: dict, n: int) -> dict:
    def m(r):
        if r.empty or r.std() == 0:
            return 0.0, 0.0
        return sharpe(excess_returns(r, rf)), max_drawdown(r)
    sr_is,   mdd_is   = m(strat_ret.loc[IS_START:IS_END])
    sr_oos,  mdd_oos  = m(strat_ret.loc[OOS_START:OOS_END])
    sr_hold, mdd_hold = m(strat_ret.loc[HOLD_START:HOLD_END])
    result = dict(id=sid, phase=phase, description=desc, params=params,
                  sr_is=sr_is, mdd_is=mdd_is, sr_oos=sr_oos, mdd_oos=mdd_oos,
                  sr_hold=sr_hold, mdd_hold=mdd_hold, n_tests_at_eval=n)
    print(f"  [{sid}] {desc[:55]:55s} | "
          f"IS={sr_is:+.2f} OOS={sr_oos:+.2f} HOLD={sr_hold:+.2f} | MDD={mdd_is:.1%}")
    return result


# ────────────────────────────────────────────────────────────────────────────
# 4.1  Vol targeting on near-passing P1 candidates
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 4.1 Vol Targeting on Near-Pass P1 Candidates ---")

def apply_vol_target(raw_ret: pd.Series, target: float = 0.15,
                     window: int = 63) -> pd.Series:
    rv = raw_ret.rolling(window).std() * np.sqrt(252)
    scale = (target / rv.shift(1)).clip(0.1, 3.0)
    return raw_ret * scale

def build_sma_strategy(prices: pd.Series, fast: int, slow: int, cost: float) -> pd.Series:
    signal = (prices.rolling(fast).mean() > prices.rolling(slow).mean()).astype(float)
    pos = signal.shift(1).fillna(0)
    ret = prices.pct_change().dropna()
    return (pos.reindex(ret.index).fillna(0) * ret
            - cost * pos.reindex(ret.index).fillna(0).diff().abs().fillna(0))

def build_atr_trend(prices: pd.Series, trend_ma: int, cost: float) -> pd.Series:
    signal = (prices > prices.rolling(trend_ma).mean()).astype(float)
    pos = signal.shift(1).fillna(0)
    ret = prices.pct_change().dropna()
    return (pos.reindex(ret.index).fillna(0) * ret
            - cost * pos.reindex(ret.index).fillna(0).diff().abs().fillna(0))

# Best near-pass candidates from Phase 1
near_pass = [
    ("SPY", "SMA20_60",   lambda p: build_sma_strategy(p, 20, 60, COST_ETF)),
    ("QQQ", "SMA100_200", lambda p: build_sma_strategy(p, 100, 200, COST_ETF)),
    ("QQQ", "ATR200",     lambda p: build_atr_trend(p, 200, COST_ETF)),
    ("SPY", "ATR200",     lambda p: build_atr_trend(p, 200, COST_ETF)),
    ("QQQ", "EMA20_50",   lambda p: build_sma_strategy(p, 20, 50, COST_ETF)),  # EMA approx
]

prices_map = {"SPY": spy["Close"], "QQQ": qqq["Close"],
              "TLT": tlt["Close"], "GLD": gld["Close"]}

for target_vol in [0.12, 0.15, 0.20]:
    for ticker, label, builder in near_pass:
        N_TESTS += 1
        prices = prices_map[ticker]
        raw_ret = builder(prices)
        vt_ret  = apply_vol_target(raw_ret, target=target_vol)
        sr = fast_is_sr(vt_ret)
        key = f"P4.1_{ticker}_{label}_VT{int(target_vol*100)}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(vt_ret, key, f"{ticker} {label} + VolTarget {target_vol:.0%}",
                               "4.1", {"ticker": ticker, "vol_target": target_vol}, N_TESTS)
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# 4.2  VIX Regime Filter
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 4.2 VIX Regime Filter ---")

vix_common = vix.reindex(spy.index, method="ffill").dropna()

for ticker, ohlc in [("SPY", spy), ("QQQ", qqq)]:
    prices = ohlc["Close"]
    ret = prices.pct_change().dropna()

    # Percentile-based regime
    for pct_lo, pct_hi in [(25, 75), (33, 67), (20, 80)]:
        N_TESTS += 1
        vix_pct_lo = vix_common.rolling(252).quantile(pct_lo / 100)
        vix_pct_hi = vix_common.rolling(252).quantile(pct_hi / 100)

        # Long in low vol regime, short in high vol regime
        signal = pd.Series(0.0, index=prices.index)
        signal[vix_common < vix_pct_lo] = 1.0
        signal[vix_common > vix_pct_hi] = -1.0

        pos = signal.shift(1).reindex(ret.index).fillna(0)
        strat_ret = pos * ret - COST_ETF * pos.diff().abs().fillna(0)
        sr = fast_is_sr(strat_ret)
        key = f"P4.2_{ticker}_VIX_pct{pct_lo}_{pct_hi}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(strat_ret, key,
                               f"{ticker} VIX pct{pct_lo}/{pct_hi} regime LS",
                               "4.2",
                               {"ticker": ticker, "pct_lo": pct_lo, "pct_hi": pct_hi},
                               N_TESTS)
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # Absolute VIX thresholds
    for vix_lo, vix_hi in [(15, 25), (15, 30), (20, 35), (15, 20)]:
        N_TESTS += 1
        signal = pd.Series(0.0, index=prices.index)
        signal[vix_common < vix_lo] = 1.0
        signal[vix_common > vix_hi] = -1.0

        pos = signal.shift(1).reindex(ret.index).fillna(0)
        strat_ret = pos * ret - COST_ETF * pos.diff().abs().fillna(0)
        sr = fast_is_sr(strat_ret)
        key = f"P4.2_{ticker}_VIX_abs{vix_lo}_{vix_hi}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(strat_ret, key,
                               f"{ticker} VIX abs {vix_lo}/{vix_hi} LS",
                               "4.2",
                               {"ticker": ticker, "vix_lo": vix_lo, "vix_hi": vix_hi},
                               N_TESTS)
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # VIX mean reversion: VIX high → SPY will recover; VIX low → overextended
    # Strategy: buy SPY when VIX spikes above 1.5× its 20d MA, sell when VIX < MA
    for spike_mult in [1.3, 1.5, 2.0]:
        N_TESTS += 1
        vix_ma = vix_common.rolling(20).mean()
        spike = vix_common > spike_mult * vix_ma

        signal = pd.Series(0.0, index=prices.index)
        signal[spike] = 1.0  # buy the fear
        # Hold until VIX reverts below MA
        pos = pd.Series(0.0, index=prices.index)
        in_trade = False
        for i, dt in enumerate(prices.index):
            if spike.reindex(prices.index).fillna(False)[dt]:
                in_trade = True
            if in_trade and vix_common.reindex(prices.index, method="ffill").fillna(method="ffill")[dt] < vix_ma.reindex(prices.index, method="ffill").fillna(method="ffill")[dt]:
                in_trade = False
            pos[dt] = 1.0 if in_trade else 0.0

        strat_ret = pos.shift(1) * ret.reindex(pos.index).fillna(0) - COST_ETF * pos.shift(1).diff().abs().fillna(0)
        sr = fast_is_sr(strat_ret)
        key = f"P4.2_{ticker}_VIX_spike{int(spike_mult*10)}_MR"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(strat_ret, key,
                               f"{ticker} VIX spike×{spike_mult} mean-reversion",
                               "4.2",
                               {"ticker": ticker, "spike_mult": spike_mult},
                               N_TESTS)
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# 4.3  Vol Squeeze Breakout (NR4, NR7)
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 4.3 NR4/NR7 Vol Squeeze Breakout ---")

def true_range(ohlc: pd.DataFrame) -> pd.Series:
    h, l, c = ohlc["High"], ohlc["Low"], ohlc["Close"].shift(1)
    return pd.concat([(h - l), (h - c).abs(), (l - c).abs()], axis=1).max(axis=1)

for ticker, ohlc in [("SPY", spy), ("QQQ", qqq), ("IWM", iwm)]:
    tr = true_range(ohlc)
    prices = ohlc["Close"]
    ret = prices.pct_change().dropna()

    for nr in [4, 7]:
        N_TESTS += 1
        # NR{n}: today's range is smallest of last n days → squeeze
        nr_squeeze = tr == tr.rolling(nr).min()

        # On next day after squeeze, trade in direction of breakout vs prev close
        # If open > prev_close → long; if open < prev_close → short
        signal = pd.Series(0.0, index=prices.index)
        for i in range(1, len(prices)):
            if nr_squeeze.iloc[i - 1]:
                today_ret = (prices.iloc[i] - prices.iloc[i - 1]) / prices.iloc[i - 1]
                signal.iloc[i] = np.sign(today_ret)  # hindsight for signal direction ONLY

        # This is a same-day directional signal using open — needs careful handling
        # Use: if ohlc open > prev close, go long close-to-close (direction bias)
        signal2 = pd.Series(0.0, index=prices.index)
        for i in range(1, len(ohlc)):
            if nr_squeeze.iloc[i - 1]:
                open_vs_prev_close = ohlc["Open"].iloc[i] / ohlc["Close"].iloc[i - 1] - 1
                signal2.iloc[i] = np.sign(open_vs_prev_close)

        pos = signal2  # no shift needed since we use open-determined direction (T signal → T trade)
        strat_ret = pos * ret.reindex(pos.index).fillna(0) - COST_ETF * pos.diff().abs().fillna(0)
        sr = fast_is_sr(strat_ret)
        key = f"P4.3_{ticker}_NR{nr}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(strat_ret, key, f"{ticker} NR{nr} squeeze breakout",
                               "4.3", {"ticker": ticker, "nr": nr}, N_TESTS)
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # Bollinger band squeeze: width at multi-year low
    for bb_period in [20, 50]:
        N_TESTS += 1
        sma = prices.rolling(bb_period).mean()
        std = prices.rolling(bb_period).std()
        bb_width = std / sma  # normalised BB width

        # Squeeze: BB width below 20th percentile of trailing 1yr
        width_pct = bb_width.rolling(252).rank(pct=True)
        squeeze = width_pct < 0.20

        # Trade direction using prior momentum
        mom5 = prices.pct_change(5)
        signal = pd.Series(0.0, index=prices.index)
        signal[squeeze & (mom5 > 0)] = 1.0
        signal[squeeze & (mom5 < 0)] = -1.0

        pos = signal.shift(1).fillna(0)
        strat_ret = pos * ret.reindex(pos.index).fillna(0) - COST_ETF * pos.diff().abs().fillna(0)
        sr = fast_is_sr(strat_ret)
        key = f"P4.3_{ticker}_BB{bb_period}_squeeze"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(strat_ret, key, f"{ticker} BB{bb_period} squeeze breakout",
                               "4.3",
                               {"ticker": ticker, "bb_period": bb_period},
                               N_TESTS)
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# 4.4  Multi-Asset Defensive Rotation (SPY/TLT/GLD)
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 4.4 Multi-Asset Defensive Rotation ---")

# Common index
common_idx = spy.index.intersection(tlt.index).intersection(gld.index)
spy_c = spy["Close"].reindex(common_idx)
tlt_c = tlt["Close"].reindex(common_idx)
gld_c = gld["Close"].reindex(common_idx)
vix_c = vix.reindex(common_idx, method="ffill")

spy_ret = spy_c.pct_change().dropna()
tlt_ret = tlt_c.pct_change().dropna()
gld_ret = gld_c.pct_change().dropna()

# 1: VIX-based rotation: low VIX→SPY, medium→TLT, high→GLD
for vix_th1, vix_th2 in [(20, 30), (15, 25), (20, 35)]:
    N_TESTS += 1
    signal_spy = pd.Series(0.0, index=spy_c.index)
    signal_tlt = pd.Series(0.0, index=spy_c.index)
    signal_gld = pd.Series(0.0, index=spy_c.index)

    signal_spy[vix_c <= vix_th1] = 1.0
    signal_tlt[(vix_c > vix_th1) & (vix_c <= vix_th2)] = 1.0
    signal_gld[vix_c > vix_th2] = 1.0

    idx = spy_ret.index
    strat_ret = (
        signal_spy.shift(1).reindex(idx).fillna(0) * spy_ret
        + signal_tlt.shift(1).reindex(idx).fillna(0) * tlt_ret.reindex(idx).fillna(0)
        + signal_gld.shift(1).reindex(idx).fillna(0) * gld_ret.reindex(idx).fillna(0)
    )
    # Cost: when switching between assets
    total_pos_change = (
        signal_spy.diff().abs() + signal_tlt.diff().abs() + signal_gld.diff().abs()
    ).fillna(0)
    strat_ret -= total_pos_change.shift(1).reindex(idx).fillna(0) * COST_ETF

    sr = fast_is_sr(strat_ret)
    key = f"P4.4_rotation_VIX{vix_th1}_{vix_th2}"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        result = full_eval(strat_ret, key,
                           f"SPY/TLT/GLD VIX rotation {vix_th1}/{vix_th2}",
                           "4.4",
                           {"vix_th1": vix_th1, "vix_th2": vix_th2},
                           N_TESTS)
        candidates.append(result)
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

# 2: Momentum-based rotation: hold asset with highest 3M momentum
for lookback in [63, 21]:
    N_TESTS += 1
    mom_spy = spy_c.pct_change(lookback).shift(1)
    mom_tlt = tlt_c.pct_change(lookback).shift(1)
    mom_gld = gld_c.pct_change(lookback).shift(1)

    strat_ret = pd.Series(0.0, index=spy_ret.index)
    for dt in spy_ret.index:
        ms = mom_spy.get(dt, np.nan)
        mt = mom_tlt.get(dt, np.nan)
        mg = mom_gld.get(dt, np.nan)
        if pd.isna(ms) or pd.isna(mt) or pd.isna(mg):
            continue
        moms = {"SPY": ms, "TLT": mt, "GLD": mg}
        best = max(moms, key=moms.get)
        rets = {"SPY": spy_ret.get(dt, 0), "TLT": tlt_ret.reindex([dt]).fillna(0).iloc[0],
                "GLD": gld_ret.reindex([dt]).fillna(0).iloc[0]}
        strat_ret[dt] = rets[best]

    # Rough cost (switch ~1x/month)
    strat_ret_net = strat_ret - COST_ETF * (strat_ret != 0).astype(float) * (1 / lookback)
    sr = fast_is_sr(strat_ret_net)
    key = f"P4.4_rotation_mom{lookback}"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        result = full_eval(strat_ret_net, key,
                           f"SPY/TLT/GLD momentum {lookback}d rotation",
                           "4.4",
                           {"lookback": lookback},
                           N_TESTS)
        candidates.append(result)
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

# 3: Risk parity rebalancing
N_TESTS += 1
weights_spy = pd.Series(0.0, index=spy_ret.index)
weights_tlt = pd.Series(0.0, index=spy_ret.index)
weights_gld = pd.Series(0.0, index=spy_ret.index)

for dt in spy_ret.index[63:]:
    hist_end = dt
    spy_vol = spy_ret.loc[:hist_end].iloc[-63:].std()
    tlt_vol = tlt_ret.reindex(spy_ret.index).fillna(0).loc[:hist_end].iloc[-63:].std()
    gld_vol = gld_ret.reindex(spy_ret.index).fillna(0).loc[:hist_end].iloc[-63:].std()
    total_inv_vol = (1/spy_vol + 1/tlt_vol + 1/gld_vol) if (spy_vol > 0 and tlt_vol > 0 and gld_vol > 0) else 1
    weights_spy[dt] = (1/spy_vol) / total_inv_vol if spy_vol > 0 else 1/3
    weights_tlt[dt] = (1/tlt_vol) / total_inv_vol if tlt_vol > 0 else 1/3
    weights_gld[dt] = (1/gld_vol) / total_inv_vol if gld_vol > 0 else 1/3

rp_ret = (weights_spy.shift(1) * spy_ret
          + weights_tlt.shift(1) * tlt_ret.reindex(spy_ret.index).fillna(0)
          + weights_gld.shift(1) * gld_ret.reindex(spy_ret.index).fillna(0))
# Monthly rebal cost
rp_ret_net = rp_ret - COST_ETF / 21  # approx monthly rebal
sr = fast_is_sr(rp_ret_net)
key = "P4.4_risk_parity_SPY_TLT_GLD"
if sr >= 1.0:
    print(f"  PASS IS: {key} SR_IS={sr:.2f}")
    result = full_eval(rp_ret_net, key, "Risk parity SPY/TLT/GLD 63d vol",
                       "4.4", {}, N_TESTS)
    candidates.append(result)
else:
    print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ── Extra: SMA trend + VIX regime combo ───────────────────────────────────
print("\n--- 4.x SMA Trend + VIX regime combo ---")

for ticker, ohlc in [("SPY", spy), ("QQQ", qqq)]:
    prices = ohlc["Close"]
    ret = prices.pct_change().dropna()

    for sma_p, vix_cut in [(200, 25), (200, 20), (100, 25)]:
        N_TESTS += 1
        trend = prices > prices.rolling(sma_p).mean()
        low_vix = vix.reindex(prices.index, method="ffill") < vix_cut

        signal = pd.Series(0.0, index=prices.index)
        signal[trend & low_vix] = 1.0   # long in uptrend + calm VIX
        signal[~trend] = -0.5           # light short when below SMA

        pos = signal.shift(1).reindex(ret.index).fillna(0)
        strat_ret = pos * ret - COST_ETF * pos.diff().abs().fillna(0)
        sr = fast_is_sr(strat_ret)
        key = f"P4x_{ticker}_SMA{sma_p}_VIX{vix_cut}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(strat_ret, key,
                               f"{ticker} SMA{sma_p}+VIX<{vix_cut} regime",
                               "4.x",
                               {"sma_period": sma_p, "vix_cut": vix_cut, "ticker": ticker},
                               N_TESTS)
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# Summary
# ────────────────────────────────────────────────────────────────────────────
print(f"\n=== Phase 4 Summary ===")
p4_count = N_TESTS - N_PREV
print(f"Phase 4 tests: {p4_count}")
print(f"Running n_tests: {N_TESTS}")
print(f"IS passes: {len(candidates)}")
for c in candidates:
    print(f"  → {c['id']}: IS={c['sr_is']:.2f} OOS={c['sr_oos']:.2f} HOLD={c['sr_hold']:.2f}")

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "phase4_results.json")
with open(RESULTS_FILE, "w") as f:
    json.dump({"n_tests": N_TESTS, "candidates": candidates}, f, indent=2, default=str)
print(f"Results saved: {RESULTS_FILE}")

oos_pass = [c for c in candidates if c["sr_oos"] >= 1.5]
hold_pass = [c for c in candidates if c["sr_hold"] >= 2.0]
print(f"\nOOS passes (SR≥1.5): {len(oos_pass)}")
print(f"HOLDOUT passes (SR≥2.0): {len(hold_pass)}")
