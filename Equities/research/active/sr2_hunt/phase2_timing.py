"""
Phase 2 — Timing & Calendar strategies on daily data.
Tests:
2.2 Day-of-week effects
2.3 Overnight gap / close drift
2.4 Intraday momentum vs overnight reversal
2.6 Calendar: Turn-of-month, FOMC pre-announcement, OpEx week

Note: ORB (2.1) requires 1-min data → handled in phase2_orb.py
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
    evaluate_strategy, save_result, load_register, hac_tstat,
    IS_START, IS_END, OOS_START, OOS_END, HOLD_START, HOLD_END, COST_ETF,
)
import json

rf = fetch_rf()

# Load n_tests from Phase 1 result
N_PHASE1 = 210
N_BASE = 322
N_TESTS = N_BASE + N_PHASE1  # = 532

print("=== PHASE 2 — Timing & Calendar Effects ===\n")

# ── Download data with OHLC for gap analysis ───────────────────────────────
def fetch_ohlc(ticker: str) -> pd.DataFrame:
    df = yf.download(ticker, start="2014-01-01", end="2026-05-26",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()

print("Fetching OHLC data...")
spy_ohlc = fetch_ohlc("SPY")
qqq_ohlc = fetch_ohlc("QQQ")
iwm_ohlc = fetch_ohlc("IWM")
print(f"  SPY: {len(spy_ohlc)} bars | QQQ: {len(qqq_ohlc)} bars | IWM: {len(iwm_ohlc)} bars")

ASSETS = {"SPY": spy_ohlc, "QQQ": qqq_ohlc, "IWM": iwm_ohlc}


def fast_is_sr_ohlc(ohlc: pd.DataFrame, signal: pd.Series, cost: float) -> float:
    ret = ohlc["Close"].pct_change().dropna()
    pos = signal.shift(1).reindex(ret.index).fillna(0)
    strat_ret = pos * ret - cost * pos.diff().abs().fillna(0)
    is_ret = strat_ret.loc[IS_START:IS_END]
    exc = excess_returns(is_ret, rf)
    return sharpe(exc)


def full_eval(ohlc: pd.DataFrame, signal: pd.Series, cost: float,
              strategy_id: str, desc: str, phase: str, params: dict,
              n_total: int) -> dict:
    prices = ohlc["Close"]
    ret = prices.pct_change().dropna()
    pos = signal.shift(1).reindex(ret.index).fillna(0)
    strat_ret = pos * ret - cost * pos.diff().abs().fillna(0)

    def m(r):
        if r.empty or r.std() == 0:
            return 0.0, 0.0
        exc = excess_returns(r, rf)
        return sharpe(exc), max_drawdown(r)

    sr_is,   mdd_is   = m(strat_ret.loc[IS_START:IS_END])
    sr_oos,  mdd_oos  = m(strat_ret.loc[OOS_START:OOS_END])
    sr_hold, mdd_hold = m(strat_ret.loc[HOLD_START:HOLD_END])

    result = {
        "id": strategy_id,
        "phase": phase,
        "description": desc,
        "params": params,
        "sr_is": sr_is, "mdd_is": mdd_is,
        "sr_oos": sr_oos, "mdd_oos": mdd_oos,
        "sr_hold": sr_hold, "mdd_hold": mdd_hold,
        "n_tests_at_eval": n_total,
    }

    print(
        f"  [{strategy_id}] {desc[:50]:50s} | "
        f"IS={sr_is:+.2f} OOS={sr_oos:+.2f} HOLD={sr_hold:+.2f} | MDD_IS={mdd_is:.1%}"
    )
    return result


candidates_oos: list[dict] = []


# ────────────────────────────────────────────────────────────────────────────
# 2.2  Day-of-week effects
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 2.2 Day-of-Week Effects ---")

for ticker, ohlc in ASSETS.items():
    prices = ohlc["Close"]
    ret = prices.pct_change()
    dow = prices.index.dayofweek  # 0=Mon, 4=Fri

    for day, day_name in [(0, "Mon"), (1, "Tue"), (2, "Wed"), (3, "Thu"), (4, "Fri")]:
        N_TESTS += 1
        # Long only on this day of week
        signal = pd.Series((dow == day).astype(float), index=prices.index)
        sr = fast_is_sr_ohlc(ohlc, signal, COST_ETF)
        key = f"P2.2_{ticker}_long_{day_name}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(ohlc, signal, COST_ETF, key, f"Long {ticker} on {day_name}",
                               "2.2", {"ticker": ticker, "day": day_name}, N_TESTS)
            candidates_oos.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # Short Friday, Long Monday (weekend effect)
    N_TESTS += 1
    signal_wknd = pd.Series(0.0, index=prices.index)
    signal_wknd[prices.index[dow == 0]] = 1.0   # Long Monday
    signal_wknd[prices.index[dow == 4]] = -1.0  # Short Friday
    sr = fast_is_sr_ohlc(ohlc, signal_wknd, COST_ETF)
    key = f"P2.2_{ticker}_longMon_shortFri"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        result = full_eval(ohlc, signal_wknd, COST_ETF, key,
                           f"{ticker} L Mon S Fri", "2.2",
                           {"ticker": ticker}, N_TESTS)
        candidates_oos.append(result)
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# 2.3  Overnight Gap & Close-to-Close patterns
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 2.3 Overnight Gap & Drift ---")

for ticker, ohlc in ASSETS.items():
    prices = ohlc["Close"]

    # Overnight return = Open/prev_Close - 1
    overnight_ret = ohlc["Open"] / ohlc["Close"].shift(1) - 1
    intraday_ret  = ohlc["Close"] / ohlc["Open"] - 1

    # Gap reversal: if gap up, short; if gap down, long (hold intraday)
    for gap_thresh in [0.003, 0.005, 0.008]:
        N_TESTS += 1
        signal = pd.Series(0.0, index=prices.index)
        signal[overnight_ret < -gap_thresh] = 1.0   # gap down → long
        signal[overnight_ret >  gap_thresh] = -1.0  # gap up → short
        sr = fast_is_sr_ohlc(ohlc, signal, COST_ETF)
        key = f"P2.3_{ticker}_gapRev_{int(gap_thresh*1000)}bp"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(ohlc, signal, COST_ETF, key,
                               f"{ticker} gap reversal {gap_thresh:.1%}", "2.3",
                               {"gap_thresh": gap_thresh, "ticker": ticker}, N_TESTS)
            candidates_oos.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # Gap continuation: if gap up, long; if gap down, short
    for gap_thresh in [0.003, 0.005]:
        N_TESTS += 1
        signal = pd.Series(0.0, index=prices.index)
        signal[overnight_ret >  gap_thresh] = 1.0
        signal[overnight_ret < -gap_thresh] = -1.0
        sr = fast_is_sr_ohlc(ohlc, signal, COST_ETF)
        key = f"P2.3_{ticker}_gapCont_{int(gap_thresh*1000)}bp"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # Overnight momentum: use prev overnight return to predict today's close return
    for lookback in [1, 3, 5]:
        N_TESTS += 1
        overnight_ma = overnight_ret.rolling(lookback).mean()
        signal = np.sign(overnight_ma)
        sr = fast_is_sr_ohlc(ohlc, signal, COST_ETF)
        key = f"P2.3_{ticker}_overnightMom_{lookback}d"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# 2.4  Intraday vs Overnight decomposition
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 2.4 Intraday vs Overnight Decomp ---")

for ticker, ohlc in ASSETS.items():
    prices = ohlc["Close"]
    overnight_ret = ohlc["Open"] / ohlc["Close"].shift(1) - 1
    intraday_ret  = ohlc["Close"] / ohlc["Open"] - 1

    # Overnight continuation: if last N days overnight positive, next will be too
    for lookback in [5, 10, 20]:
        N_TESTS += 1
        cumulated_overnight = overnight_ret.rolling(lookback).mean()
        signal = pd.Series(np.sign(cumulated_overnight), index=prices.index)
        sr = fast_is_sr_ohlc(ohlc, signal, COST_ETF)
        key = f"P2.4_{ticker}_overnightMom{lookback}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(ohlc, signal, COST_ETF, key,
                               f"{ticker} overnight momentum {lookback}d", "2.4",
                               {"lookback": lookback, "ticker": ticker}, N_TESTS)
            candidates_oos.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # Intraday reversal: if strong intraday gain, short overnight (next open)
    for lookback in [3, 5]:
        N_TESTS += 1
        intraday_ma = intraday_ret.rolling(lookback).mean()
        signal = pd.Series(-np.sign(intraday_ma), index=prices.index)  # fade intraday move overnight
        sr = fast_is_sr_ohlc(ohlc, signal, COST_ETF)
        key = f"P2.4_{ticker}_intradayFade{lookback}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# 2.6  Calendar Effects
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 2.6 Calendar Effects ---")

# Turn-of-Month (TOM): last 2 + first 3 trading days of each month
for ticker, ohlc in ASSETS.items():
    prices = ohlc["Close"]
    idx = prices.index

    # Compute TOM mask
    def is_tom(idx: pd.DatetimeIndex) -> pd.Series:
        mask = pd.Series(False, index=idx)
        for year in idx.year.unique():
            for month in range(1, 13):
                month_days = idx[(idx.year == year) & (idx.month == month)]
                if len(month_days) == 0:
                    continue
                # Last 2 trading days
                last_2 = month_days[-2:]
                # First 3 trading days
                first_3 = month_days[:3]
                tom_days = last_2.union(first_3)
                mask[tom_days] = True
        return mask

    tom_mask = is_tom(idx)

    N_TESTS += 1
    signal_tom = tom_mask.astype(float)
    sr = fast_is_sr_ohlc(ohlc, signal_tom, COST_ETF)
    key = f"P2.6_{ticker}_TOM"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        result = full_eval(ohlc, signal_tom, COST_ETF, key,
                           f"{ticker} Turn-of-Month", "2.6",
                           {"window": "last2+first3", "ticker": ticker}, N_TESTS)
        candidates_oos.append(result)
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # TOM variants: last 3 + first 4
    N_TESTS += 1
    def is_tom_wide(idx: pd.DatetimeIndex) -> pd.Series:
        mask = pd.Series(False, index=idx)
        for year in idx.year.unique():
            for month in range(1, 13):
                month_days = idx[(idx.year == year) & (idx.month == month)]
                if len(month_days) == 0:
                    continue
                tom_days = month_days[-3:].union(month_days[:4])
                mask[tom_days] = True
        return mask

    tom_wide = is_tom_wide(idx)
    signal_tom_wide = tom_wide.astype(float)
    sr = fast_is_sr_ohlc(ohlc, signal_tom_wide, COST_ETF)
    key = f"P2.6_{ticker}_TOM_wide"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        result = full_eval(ohlc, signal_tom_wide, COST_ETF, key,
                           f"{ticker} Turn-of-Month wide", "2.6",
                           {"window": "last3+first4", "ticker": ticker}, N_TESTS)
        candidates_oos.append(result)
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # TOM vs non-TOM L/S
    N_TESTS += 1
    signal_tom_ls = tom_mask.astype(float) * 2 - 1  # +1 TOM, -1 non-TOM
    sr = fast_is_sr_ohlc(ohlc, signal_tom_ls, COST_ETF)
    key = f"P2.6_{ticker}_TOM_LS"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        result = full_eval(ohlc, signal_tom_ls, COST_ETF, key,
                           f"{ticker} TOM long, non-TOM short", "2.6",
                           {"ticker": ticker}, N_TESTS)
        candidates_oos.append(result)
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ── FOMC pre-announcement drift ────────────────────────────────────────────
print("\n--- 2.6 FOMC Pre-announcement Drift ---")
# Known FOMC dates from Fed calendar (approximate — day before press release)
# Strategy: buy SPY 1 trading day before FOMC, sell on FOMC day at close
# Data source: hardcoded FOMC announcement dates 2015-2024

FOMC_DATES = [
    # 2015
    "2015-01-28", "2015-03-18", "2015-04-29", "2015-06-17",
    "2015-07-29", "2015-09-17", "2015-10-28", "2015-12-16",
    # 2016
    "2016-01-27", "2016-03-16", "2016-04-27", "2016-06-15",
    "2016-07-27", "2016-09-21", "2016-11-02", "2016-12-14",
    # 2017
    "2017-02-01", "2017-03-15", "2017-05-03", "2017-06-14",
    "2017-07-26", "2017-09-20", "2017-11-01", "2017-12-13",
    # 2018
    "2018-01-31", "2018-03-21", "2018-05-02", "2018-06-13",
    "2018-08-01", "2018-09-26", "2018-11-08", "2018-12-19",
    # 2019
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19",
    "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    # 2020
    "2020-01-29", "2020-03-03", "2020-03-15", "2020-04-29",
    "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05",
    "2020-12-16",
    # 2021
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16",
    "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    # 2022
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15",
    "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    # 2023
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    # 2024
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    # 2025
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
]

fomc_dates = pd.to_datetime(FOMC_DATES)
spy_idx = spy_ohlc.index

# Strategy: long from T-1 close to T close (hold 1 day)
# Actually we hold from T-1 (buy at close T-1) to T (sell at close T)
# In daily backtest: signal=1 on T-1 date (so shift(1) means position on T)

for ticker, ohlc in {"SPY": spy_ohlc, "QQQ": qqq_ohlc}.items():
    prices = ohlc["Close"]
    idx = prices.index

    # FOMC day signal: 1 on the day BEFORE fomc (T-1)
    N_TESTS += 1
    signal_fomc = pd.Series(0.0, index=idx)
    for fd in fomc_dates:
        # Find T-1 (prev trading day before FOMC)
        fomc_loc = idx.searchsorted(fd)
        if fomc_loc > 0 and fomc_loc < len(idx):
            t_minus_1 = idx[fomc_loc - 1]
            signal_fomc[t_minus_1] = 1.0

    sr = fast_is_sr_ohlc(ohlc, signal_fomc, COST_ETF)
    key = f"P2.6_{ticker}_FOMC_preDrift"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        result = full_eval(ohlc, signal_fomc, COST_ETF, key,
                           f"{ticker} FOMC pre-announcement drift", "2.6",
                           {"hold": "T-1_to_T", "ticker": ticker}, N_TESTS)
        candidates_oos.append(result)
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # Hold 2 days before FOMC (T-2 to T)
    N_TESTS += 1
    signal_fomc2 = pd.Series(0.0, index=idx)
    for fd in fomc_dates:
        fomc_loc = idx.searchsorted(fd)
        for offset in [1, 2]:
            t_m = fomc_loc - offset
            if 0 <= t_m < len(idx):
                signal_fomc2[idx[t_m]] = 1.0

    sr2 = fast_is_sr_ohlc(ohlc, signal_fomc2, COST_ETF)
    key2 = f"P2.6_{ticker}_FOMC_2d_pre"
    if sr2 >= 1.0:
        print(f"  PASS IS: {key2} SR_IS={sr2:.2f}")
        result = full_eval(ohlc, signal_fomc2, COST_ETF, key2,
                           f"{ticker} FOMC 2d pre-drift", "2.6",
                           {"hold": "T-2_to_T", "ticker": ticker}, N_TESTS)
        candidates_oos.append(result)
    else:
        print(f"  FAIL IS: {key2} SR_IS={sr2:.2f}")


# ── OpEx week (3rd Friday of each month = monthly options expiry) ──────────
print("\n--- 2.6 Options Expiration Week ---")

def is_opex_week(idx: pd.DatetimeIndex) -> pd.Series:
    """True during the week containing the 3rd Friday of each month."""
    mask = pd.Series(False, index=idx)
    for year in idx.year.unique():
        for month in range(1, 13):
            # Find 3rd Friday
            cal_days = pd.date_range(f"{year}-{month:02d}-01",
                                     f"{year}-{month:02d}-28", freq="D")
            fridays = cal_days[cal_days.dayofweek == 4]
            if len(fridays) < 3:
                continue
            opex_friday = fridays[2]
            opex_week_start = opex_friday - pd.Timedelta(days=4)
            week_days = idx[(idx >= opex_week_start) & (idx <= opex_friday)]
            mask[week_days] = True
    return mask

for ticker, ohlc in ASSETS.items():
    prices = ohlc["Close"]
    opex_mask = is_opex_week(prices.index)

    N_TESTS += 1
    signal_opex = opex_mask.astype(float)
    sr = fast_is_sr_ohlc(ohlc, signal_opex, COST_ETF)
    key = f"P2.6_{ticker}_OpExWeek"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        result = full_eval(ohlc, signal_opex, COST_ETF, key,
                           f"{ticker} OpEx week long", "2.6",
                           {"ticker": ticker}, N_TESTS)
        candidates_oos.append(result)
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    N_TESTS += 1
    signal_opex_short = (1 - opex_mask.astype(float))  # short during opex, long other
    sr_short = fast_is_sr_ohlc(ohlc, signal_opex_short, COST_ETF)
    key_short = f"P2.6_{ticker}_non_OpEx_long"
    if sr_short >= 1.0:
        print(f"  PASS IS: {key_short} SR_IS={sr_short:.2f}")
        result = full_eval(ohlc, signal_opex_short, COST_ETF, key_short,
                           f"{ticker} non-OpEx long", "2.6",
                           {"ticker": ticker}, N_TESTS)
        candidates_oos.append(result)
    else:
        print(f"  FAIL IS: {key_short} SR_IS={sr_short:.2f}")


# ── Year-end / December effect ─────────────────────────────────────────────
print("\n--- 2.6 Year-End Effect ---")
for ticker, ohlc in ASSETS.items():
    prices = ohlc["Close"]
    idx = prices.index

    # Long in last 10 trading days of year + first 5 of new year (Santa Rally)
    N_TESTS += 1
    def is_santa(idx):
        mask = pd.Series(False, index=idx)
        for year in idx.year.unique():
            year_end = idx[idx.year == year]
            if len(year_end) < 10:
                continue
            last_10 = year_end[-10:]
            year_start = idx[idx.year == year]
            first_5 = year_start[:5]
            mask[last_10.union(first_5)] = True
        return mask

    signal_santa = is_santa(idx).astype(float)
    sr = fast_is_sr_ohlc(ohlc, signal_santa, COST_ETF)
    key = f"P2.6_{ticker}_SantaRally"
    if sr >= 1.0:
        print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        result = full_eval(ohlc, signal_santa, COST_ETF, key,
                           f"{ticker} Santa Rally last10+first5", "2.6",
                           {"ticker": ticker}, N_TESTS)
        candidates_oos.append(result)
    else:
        print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # January effect (small caps outperform in January) — IWM vs SPY LS
    if ticker == "IWM":
        N_TESTS += 1
        jan_mask = pd.Series((idx.month == 1).astype(float), index=idx)
        signal_jan = jan_mask
        sr = fast_is_sr_ohlc(ohlc, signal_jan, COST_ETF)
        key = f"P2.6_{ticker}_January"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(ohlc, signal_jan, COST_ETF, key,
                               "IWM long in January (small-cap effect)", "2.6",
                               {"ticker": ticker}, N_TESTS)
            candidates_oos.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ── Combined calendar strategy ─────────────────────────────────────────────
print("\n--- 2.6 Combined Calendar (TOM + FOMC + Santa) ---")
ticker = "SPY"
ohlc = spy_ohlc
prices = ohlc["Close"]
idx = prices.index

tom_mask = pd.Series(False, index=idx)
for year in idx.year.unique():
    for month in range(1, 13):
        month_days = idx[(idx.year == year) & (idx.month == month)]
        if len(month_days) == 0:
            continue
        tom_days = month_days[-2:].union(month_days[:3])
        tom_mask[tom_days] = True

fomc_signal_full = pd.Series(0.0, index=idx)
for fd in fomc_dates:
    fomc_loc = idx.searchsorted(fd)
    if fomc_loc > 0 and fomc_loc < len(idx):
        fomc_signal_full[idx[fomc_loc - 1]] = 1.0

santa_mask = is_santa(idx)

# Union: long on any of the three calendar events
N_TESTS += 1
combined = (tom_mask | (fomc_signal_full > 0) | santa_mask).astype(float)
sr_combined = fast_is_sr_ohlc(ohlc, combined, COST_ETF)
key_comb = "P2.6_SPY_TOM_FOMC_Santa_combined"
if sr_combined >= 1.0:
    print(f"  PASS IS: {key_comb} SR_IS={sr_combined:.2f}")
    result = full_eval(ohlc, combined, COST_ETF, key_comb,
                       "SPY combined TOM+FOMC+Santa", "2.6",
                       {"combo": "TOM+FOMC+Santa"}, N_TESTS)
    candidates_oos.append(result)
else:
    print(f"  FAIL IS: {key_comb} SR_IS={sr_combined:.2f}")

# ────────────────────────────────────────────────────────────────────────────
# Summary
# ────────────────────────────────────────────────────────────────────────────
print(f"\n=== Phase 2 Summary ===")
p2_count = N_TESTS - (N_BASE + N_PHASE1)
print(f"Phase 2 tests: {p2_count}")
print(f"Running n_tests: {N_TESTS}")
print(f"IS passes going to OOS: {len(candidates_oos)}")
for c in candidates_oos:
    print(f"  → {c['id']}: IS={c['sr_is']:.2f} OOS={c['sr_oos']:.2f} HOLD={c['sr_hold']:.2f}")

# Save all results
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "phase2_results.json")
with open(RESULTS_FILE, "w") as f:
    json.dump({"n_tests": N_TESTS, "candidates": candidates_oos}, f, indent=2, default=str)
print(f"\nResults saved to {RESULTS_FILE}")

# Report OOS passes
oos_pass = [c for c in candidates_oos if c["sr_oos"] >= 1.5]
hold_pass = [c for c in candidates_oos if c["sr_hold"] >= 2.0]
print(f"\nOOS passes (SR≥1.5): {len(oos_pass)}")
for c in oos_pass:
    print(f"  {c['id']}: OOS={c['sr_oos']:.2f} HOLD={c['sr_hold']:.2f}")
print(f"HOLDOUT passes (SR≥2.0): {len(hold_pass)}")
for c in hold_pass:
    print(f"  {c['id']}: HOLD={c['sr_hold']:.2f}")
