"""
Phase 4b — NR4/NR7 audit complet.

PROBLÈME DÉTECTÉ dans phase4_vol.py :
  - signal2[i] = sign(Open[i] - Close[i-1])  # direction basée sur gap overnight
  - ret[i] = Close[i] / Close[i-1] - 1       # close-to-close (inclut le gap)
  - pos = signal2 (pas de shift)

=> Le gap overnight (Close[i-1]→Open[i]) entre dans le calcul de return.
   Si signal=+1 (gap up), le retour close-to-close commence déjà positivement grâce au gap.
   C'est du look-ahead : on "capte" le gap overnight dans le P&L.

VERSIONS CORRIGÉES :
  V1 — Correct strict : entrer à Open[i], sortir à Close[i]
       return = Close[i] / Open[i] - 1  (intraday seulement)
  V2 — Entrée close : signaler à close i-1, trade direction = signe de Close[i] vs Close[i-1]
       return = Close[i+1] / Close[i] - 1 (signal au T-1, trade au T)
  V3 — Breakout classique : placer BuyStop/SellStop au high/low du jour NR4+1
       (difficile à simuler sans 1-min, approx avec Open > prev_high → long)

TEST UNITAIRE LOOK-AHEAD :
  Tronquer à 2019-12-31, recalculer. Si les signaux 2015-2019 changent → look-ahead.
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
    fetch_rf, excess_returns, sharpe, max_drawdown,
    IS_START, IS_END, OOS_START, OOS_END, HOLD_START, HOLD_END, COST_ETF,
)
import json

rf = fetch_rf()
N_PREV = 691
N_TESTS = N_PREV
print("=== PHASE 4b — NR4/NR7 Audit & Corrected Backtest ===\n")

def fetch_ohlc(ticker: str) -> pd.DataFrame:
    df = yf.download(ticker, start="2013-01-01", end="2026-05-26",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[["Open", "High", "Low", "Close"]].dropna()

print("Fetching OHLC...")
spy = fetch_ohlc("SPY")
qqq = fetch_ohlc("QQQ")
iwm = fetch_ohlc("IWM")
assets = {"SPY": spy, "QQQ": qqq, "IWM": iwm}
print(f"  SPY={len(spy)}, QQQ={len(qqq)}, IWM={len(iwm)}")


def true_range(ohlc: pd.DataFrame) -> pd.Series:
    h, l, c = ohlc["High"], ohlc["Low"], ohlc["Close"].shift(1)
    return pd.concat([(h - l), (h - c).abs(), (l - c).abs()], axis=1).max(axis=1)


# ────────────────────────────────────────────────────────────────────────────
# LOOK-AHEAD TEST
# Verify: truncating to 2019-12-31, signals on 2015-2019 must be identical.
# ────────────────────────────────────────────────────────────────────────────
print("\n--- Look-ahead Verification ---")

def build_nr4_signal_original(ohlc: pd.DataFrame, nr: int) -> pd.Series:
    """Original (potentially biased) implementation."""
    tr = true_range(ohlc)
    nr_squeeze = tr == tr.rolling(nr).min()
    signal = pd.Series(0.0, index=ohlc.index)
    for i in range(1, len(ohlc)):
        if nr_squeeze.iloc[i - 1]:
            gap = ohlc["Open"].iloc[i] / ohlc["Close"].iloc[i - 1] - 1
            signal.iloc[i] = np.sign(gap)
    return signal

qqq_full = build_nr4_signal_original(qqq, 4)
qqq_trunc = build_nr4_signal_original(qqq[qqq.index <= "2019-12-31"], 4)

overlap = qqq_full.loc["2015-01-01":"2019-12-31"]
overlap_t = qqq_trunc.loc["2015-01-01":"2019-12-31"].reindex(overlap.index)
diff = (overlap != overlap_t).sum()
print(f"Signal differences after truncation to 2019: {diff} rows")
if diff == 0:
    print("  ✓ No look-ahead bias in signal generation (NR squeeze + gap open both observable)")
else:
    print(f"  ✗ {diff} differences — LOOK-AHEAD CONFIRMED")

# ── Diagnose the return calculation issue ─────────────────────────────────
print("\n--- Return Calculation Audit ---")
print("Original: uses Close[i]/Close[i-1] with signal from Open[i]")
print("  → P&L = (overnight gap component) + (intraday component)")
print("  → If signal=+1 (gap up), overnight gap is positive AND included in return")
print("  → This OVERSTATES returns — entering at Open means you DON'T capture the gap")
print("  → Correct: entry at Open, so return = Close[i] / Open[i] - 1")


# ────────────────────────────────────────────────────────────────────────────
# V1 — CORRECTED: Entry at Open[i], Exit at Close[i]
#      signal[i-1] = squeeze detected at close of i-1
#      direction: sign(Open[i] - Close[i-1])  (gap observable before entry)
#      return: Close[i] / Open[i] - 1  (open-to-close intraday only)
# ────────────────────────────────────────────────────────────────────────────
print("\n--- V1 Corrected NR (Entry Open, Exit Close, Return=Open→Close) ---")

def nr_v1_corrected(ohlc: pd.DataFrame, nr: int, cost: float) -> pd.Series:
    """
    Correct implementation:
    - Detect NR squeeze at close of day t (using close prices only, no future info)
    - At open of t+1: observe gap direction = sign(Open[t+1] - Close[t])
    - Enter at Open[t+1], exit at Close[t+1]
    - Return = Close[t+1] / Open[t+1] - 1 in direction of gap
    - Cost applied on each trade (2 per trade: open + close)
    """
    tr = true_range(ohlc)
    nr_squeeze = tr == tr.rolling(nr).min()  # detected at end of each day

    daily_rets = pd.Series(0.0, index=ohlc.index)
    trade_costs = pd.Series(0.0, index=ohlc.index)

    for i in range(1, len(ohlc)):
        if not nr_squeeze.iloc[i - 1]:
            continue  # no squeeze yesterday

        # Gap direction (observable at open, before entry)
        gap_direction = np.sign(ohlc["Open"].iloc[i] - ohlc["Close"].iloc[i - 1])
        if gap_direction == 0:
            continue

        # Intraday return only
        intraday_ret = ohlc["Close"].iloc[i] / ohlc["Open"].iloc[i] - 1
        daily_rets.iloc[i] = gap_direction * intraday_ret
        trade_costs.iloc[i] = cost  # round-trip cost per trade

    return daily_rets - trade_costs


candidates_v1: list[dict] = []
for ticker, ohlc in assets.items():
    for nr in [4, 7]:
        N_TESTS += 1
        strat_ret = nr_v1_corrected(ohlc, nr, COST_ETF)

        def m(r):
            if r.empty or r.std() == 0:
                return 0.0, 0.0
            return sharpe(excess_returns(r, rf)), max_drawdown(r)

        sr_is,   mdd_is   = m(strat_ret.loc[IS_START:IS_END])
        sr_oos,  mdd_oos  = m(strat_ret.loc[OOS_START:OOS_END])
        sr_hold, mdd_hold = m(strat_ret.loc[HOLD_START:HOLD_END])

        print(f"  [{ticker} NR{nr} V1] IS={sr_is:+.2f} OOS={sr_oos:+.2f} HOLD={sr_hold:+.2f} | MDD_IS={mdd_is:.1%}")

        if sr_is >= 1.0:
            candidates_v1.append({
                "id": f"P4b_V1_{ticker}_NR{nr}",
                "phase": "4b_v1",
                "description": f"{ticker} NR{nr} corrected (open→close return)",
                "params": {"ticker": ticker, "nr": nr, "version": "V1_open_to_close"},
                "sr_is": sr_is, "mdd_is": mdd_is,
                "sr_oos": sr_oos, "mdd_oos": mdd_oos,
                "sr_hold": sr_hold, "mdd_hold": mdd_hold,
                "n_tests_at_eval": N_TESTS,
            })


# ────────────────────────────────────────────────────────────────────────────
# V2 — Close-to-close, signal from PRIOR close momentum (T-1 signal, T trade)
#      No open data needed. Pure daily close prices.
#      squeeze at T-1 → signal direction = close momentum of last n days
#      trade at T → close[T] / close[T-1] - 1
# ────────────────────────────────────────────────────────────────────────────
print("\n--- V2: Close-to-Close (T-1 signal from prior momentum) ---")

def nr_v2_momentum_dir(ohlc: pd.DataFrame, nr: int,
                        mom_lookback: int, cost: float) -> pd.Series:
    """
    - Detect NR squeeze at close T-1
    - Direction = sign of last mom_lookback-day price momentum at T-1
    - Enter at close T-1, exit at close T (shift(1))
    - Return = close[T] / close[T-1] - 1
    """
    tr = true_range(ohlc)
    prices = ohlc["Close"]
    nr_squeeze = tr == tr.rolling(nr).min()
    mom = prices.pct_change(mom_lookback)

    signal = pd.Series(0.0, index=prices.index)
    signal[nr_squeeze] = np.sign(mom[nr_squeeze])

    pos = signal.shift(1).fillna(0)
    ret = prices.pct_change().dropna()
    strat_ret = pos.reindex(ret.index).fillna(0) * ret - cost * pos.reindex(ret.index).fillna(0).diff().abs().fillna(0)
    return strat_ret


for mom_lb in [1, 3, 5, 10]:
    for ticker, ohlc in assets.items():
        for nr in [4, 7]:
            N_TESTS += 1
            strat_ret = nr_v2_momentum_dir(ohlc, nr, mom_lb, COST_ETF)

            sr_is = sharpe(excess_returns(strat_ret.loc[IS_START:IS_END], rf))
            sr_oos = sharpe(excess_returns(strat_ret.loc[OOS_START:OOS_END], rf))
            sr_hold = sharpe(excess_returns(strat_ret.loc[HOLD_START:HOLD_END], rf))
            mdd_is = max_drawdown(strat_ret.loc[IS_START:IS_END])

            key = f"P4b_V2_{ticker}_NR{nr}_mom{mom_lb}"
            if sr_is >= 1.0:
                print(f"  PASS IS: {key} IS={sr_is:.2f} OOS={sr_oos:.2f} HOLD={sr_hold:.2f}")
                candidates_v1.append({
                    "id": key, "phase": "4b_v2",
                    "description": f"{ticker} NR{nr} C2C mom{mom_lb} signal",
                    "params": {"ticker": ticker, "nr": nr, "mom_lb": mom_lb},
                    "sr_is": sr_is, "mdd_is": mdd_is,
                    "sr_oos": sr_oos, "mdd_oos": mdd_oos,
                    "sr_hold": sr_hold, "mdd_hold": mdd_hold,
                    "n_tests_at_eval": N_TESTS,
                })
            else:
                print(f"  FAIL IS: {key} SR_IS={sr_is:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# V3 — No look-ahead: hold close-to-close in BOTH directions after NR squeeze
#      (pure "volatility will expand" play — no directional prediction)
# ────────────────────────────────────────────────────────────────────────────
print("\n--- V3: Long Straddle proxy — long vol (long only, long abs|ret|) ---")
# Can't easily simulate straddle on daily. Instead: just go long after NR squeeze
# and test if the return is systematically positive.

for ticker, ohlc in assets.items():
    prices = ohlc["Close"]
    ret = prices.pct_change().dropna()
    tr = true_range(ohlc)

    for nr in [4, 7]:
        N_TESTS += 1
        nr_squeeze = tr == tr.rolling(nr).min()
        signal = nr_squeeze.astype(float)  # long on day after NR
        pos = signal.shift(1).reindex(ret.index).fillna(0)
        strat_ret = pos * ret - COST_ETF * pos.diff().abs().fillna(0)

        sr_is = sharpe(excess_returns(strat_ret.loc[IS_START:IS_END], rf))
        key = f"P4b_V3_{ticker}_NR{nr}_longonly"
        if sr_is >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr_is:.2f}")
        else:
            print(f"  FAIL IS: {key} SR_IS={sr_is:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# V1 Focus: deep analysis on best V1 candidates
# ────────────────────────────────────────────────────────────────────────────
print("\n\n=== FOCUS: V1 Candidates Analysis ===")
v1_pass = [c for c in candidates_v1 if c["phase"] == "4b_v1" and c["sr_is"] >= 1.0]
v1_oos_pass = [c for c in candidates_v1 if c.get("sr_oos", 0) >= 1.5]
v1_hold_pass = [c for c in candidates_v1 if c.get("sr_hold", 0) >= 2.0]

print(f"\nV1 IS passes (SR≥1.0): {len(v1_pass)}")
for c in v1_pass:
    print(f"  {c['id']}: IS={c['sr_is']:.2f} OOS={c['sr_oos']:.2f} HOLD={c['sr_hold']:.2f} MDD={c['mdd_is']:.1%}")

print(f"\nV2 IS passes (SR≥1.0): {len([c for c in candidates_v1 if c['phase']=='4b_v2' and c['sr_is']>=1.0])}")

print(f"\nAll candidates OOS≥1.5: {len(v1_oos_pass)}")
for c in v1_oos_pass:
    print(f"  {c['id']}: IS={c['sr_is']:.2f} OOS={c['sr_oos']:.2f} HOLD={c['sr_hold']:.2f}")

print(f"\nAll candidates HOLDOUT≥2.0: {len(v1_hold_pass)}")
for c in v1_hold_pass:
    print(f"  *** FINAL CANDIDATE: {c['id']}: IS={c['sr_is']:.2f} OOS={c['sr_oos']:.2f} HOLD={c['sr_hold']:.2f} ***")

# Comparison: original vs corrected
print("\n\n=== Original vs Corrected NR4 Comparison ===")
print(f"{'Strategy':<30} {'Original IS':>12} {'Corrected IS':>14} {'Correction factor':>18}")
for ticker, ohlc in assets.items():
    tr = true_range(ohlc)
    nr_squeeze = (tr == tr.rolling(4).min())
    ret_cc = ohlc["Close"].pct_change().dropna()

    # Original (biased)
    sig_orig = pd.Series(0.0, index=ohlc.index)
    for i in range(1, len(ohlc)):
        if nr_squeeze.iloc[i - 1]:
            sig_orig.iloc[i] = np.sign(ohlc["Open"].iloc[i] / ohlc["Close"].iloc[i - 1] - 1)
    pos_orig = sig_orig  # no shift
    ret_orig = (pos_orig.reindex(ret_cc.index).fillna(0) * ret_cc
                - COST_ETF * pos_orig.reindex(ret_cc.index).fillna(0).diff().abs().fillna(0))
    sr_orig = sharpe(excess_returns(ret_orig.loc[IS_START:IS_END], rf))

    # Corrected
    ret_v1 = nr_v1_corrected(ohlc, 4, COST_ETF)
    sr_v1 = sharpe(excess_returns(ret_v1.loc[IS_START:IS_END], rf))

    print(f"  {ticker} NR4:                   {sr_orig:>12.2f} {sr_v1:>14.2f} {(sr_orig - sr_v1):>+18.2f}")

# ────────────────────────────────────────────────────────────────────────────
# Save results
# ────────────────────────────────────────────────────────────────────────────
print(f"\n=== Phase 4b Summary ===")
print(f"Additional tests: {N_TESTS - N_PREV}")
print(f"Running n_tests: {N_TESTS}")

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "phase4b_results.json")
with open(RESULTS_FILE, "w") as f:
    json.dump({
        "n_tests": N_TESTS,
        "candidates": candidates_v1,
        "look_ahead_flag": diff > 0,
        "look_ahead_differences": int(diff),
    }, f, indent=2, default=str)
print(f"Results saved: {RESULTS_FILE}")
