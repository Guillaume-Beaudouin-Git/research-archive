"""
Phase 3 — Cross-Sectional strategies on US Sector ETFs and Crypto.
3.1 CS Momentum 12-1, 6-1, 3-1 on sector ETFs
3.2 CS Short-term reversal 1W, 1M
3.3 Pairs cointegration (skipped — already tested in history: 0/19 qualify)
3.4 PCA residual stat-arb on sectors
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
N_PREV = 613  # running count after Phase 1+2
N_TESTS = N_PREV
print("=== PHASE 3 — Cross-Sectional Strategies ===\n")

# ── Sector ETF universe (all existed since ~1998, minimal survivorship) ────
SECTORS = ["XLK", "XLF", "XLE", "XLY", "XLP", "XLI", "XLB", "XLV", "XLU",
           "XLRE"]  # XLRE from 2015
SECTORS_LEGACY = ["XLK", "XLF", "XLE", "XLY", "XLP", "XLI", "XLB", "XLV", "XLU"]

print("Fetching sector ETF data...")
sector_data: dict[str, pd.Series] = {}
for t in SECTORS:
    try:
        df = yf.download(t, start="2013-01-01", end="2026-05-26",
                         auto_adjust=True, progress=False)
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        sector_data[t] = close.dropna()
        print(f"  {t}: {len(sector_data[t])} bars")
    except Exception as e:
        print(f"  SKIP {t}: {e}")

# Build price matrix (common date index)
price_df = pd.DataFrame(sector_data).dropna(how="any")
price_df = price_df[price_df.index >= "2015-01-01"]  # XLRE start
ret_df = price_df.pct_change().dropna()
print(f"\nPrice matrix: {price_df.shape}, {price_df.index[0].date()} → {price_df.index[-1].date()}")

candidates_oos: list[dict] = []


def fast_is_sr_port(strat_ret: pd.Series) -> float:
    is_r = strat_ret.loc[IS_START:IS_END]
    exc = excess_returns(is_r, rf)
    return sharpe(exc)


def full_eval_port(strat_ret: pd.Series, strategy_id: str, desc: str,
                   phase: str, params: dict, n_total: int) -> dict:
    def m(r):
        if r.empty or r.std() == 0:
            return 0.0, 0.0
        exc = excess_returns(r, rf)
        return sharpe(exc), max_drawdown(r)

    sr_is,   mdd_is   = m(strat_ret.loc[IS_START:IS_END])
    sr_oos,  mdd_oos  = m(strat_ret.loc[OOS_START:OOS_END])
    sr_hold, mdd_hold = m(strat_ret.loc[HOLD_START:HOLD_END])

    result = {
        "id": strategy_id, "phase": phase, "description": desc,
        "params": params,
        "sr_is": sr_is, "mdd_is": mdd_is,
        "sr_oos": sr_oos, "mdd_oos": mdd_oos,
        "sr_hold": sr_hold, "mdd_hold": mdd_hold,
        "n_tests_at_eval": n_total,
    }
    print(
        f"  [{strategy_id}] {desc[:55]:55s} | "
        f"IS={sr_is:+.2f} OOS={sr_oos:+.2f} HOLD={sr_hold:+.2f} | MDD_IS={mdd_is:.1%}"
    )
    return result


# ────────────────────────────────────────────────────────────────────────────
# 3.1  CS Momentum: rank sectors, long top-k, short bottom-k
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 3.1 CS Momentum ---")

def cs_momentum_portfolio(ret_df: pd.DataFrame, lookback: int, skip: int,
                           top_k: int, cost_per_trade: float) -> pd.Series:
    """
    Monthly rebalanced cross-sectional momentum.
    Signal: total return over [lookback+skip, skip] months ago (skip=1 standard).
    Long top_k, short bottom_k each with equal weight.
    """
    # Monthly returns for signal
    monthly_prices = ret_df.resample("ME").last()
    # Signal: cumulative return over lookback months, skipping last 'skip' months
    # Use daily prices for returns, signal monthly
    prices_m = price_df.resample("ME").last()

    positions_list = []
    # Rebalance at each month end
    for i in range(lookback + skip, len(prices_m)):
        ref_date = prices_m.index[i]
        past_date = prices_m.index[i - lookback - skip]
        skip_date = prices_m.index[i - skip]

        # Momentum signal: return from past_date to skip_date
        mom_signal = prices_m.loc[skip_date] / prices_m.loc[past_date] - 1

        # Rank and construct long/short portfolio
        ranked = mom_signal.rank(ascending=False)
        n = len(ranked)
        longs  = ranked <= top_k
        shorts = ranked >= (n - top_k + 1)

        pos = pd.Series(0.0, index=mom_signal.index)
        pos[longs]  = 1.0 / top_k
        pos[shorts] = -1.0 / top_k
        pos.name = ref_date
        positions_list.append(pos)

    if not positions_list:
        return pd.Series(dtype=float)

    positions = pd.DataFrame(positions_list)

    # Apply to daily returns (positions held for 1 month after signal)
    daily_rets = ret_df.copy()
    port_ret = pd.Series(0.0, index=daily_rets.index)

    for i, ref_date in enumerate(positions.index):
        if i + 1 < len(positions.index):
            next_date = positions.index[i + 1]
        else:
            next_date = daily_rets.index[-1]

        # Find daily rows in holding period
        hold_mask = (daily_rets.index > ref_date) & (daily_rets.index <= next_date)
        daily_rows = daily_rets.loc[hold_mask]

        pos_row = positions.iloc[i]
        for dt, row in daily_rows.iterrows():
            port_ret[dt] = (pos_row * row).sum()

    # Cost: apply turnover cost at each monthly rebal
    port_ret_with_cost = port_ret.copy()
    for i, ref_date in enumerate(positions.index):
        if i > 0:
            prev_pos = positions.iloc[i - 1]
            curr_pos = positions.iloc[i]
            turnover = (curr_pos - prev_pos).abs().sum() / 2
            # Find next trading day after ref_date
            next_days = daily_rets.index[daily_rets.index > ref_date]
            if len(next_days) > 0:
                cost_day = next_days[0]
                port_ret_with_cost[cost_day] -= turnover * cost_per_trade

    return port_ret_with_cost


# Momentum parameters: (lookback_months, skip_months, top_k)
MOM_PARAMS = [
    (12, 1, 3),  # standard 12-1, top/bottom 3
    (12, 1, 2),
    (6,  1, 3),
    (6,  1, 2),
    (3,  1, 3),
    (12, 1, 4),
    (6,  0, 3),  # no skip (more aggressive)
]

for lookback, skip, top_k in MOM_PARAMS:
    N_TESTS += 1
    try:
        strat_ret = cs_momentum_portfolio(ret_df, lookback, skip, top_k, COST_ETF)
        sr = fast_is_sr_port(strat_ret)
        key = f"P3.1_CSMom{lookback}_{skip}_top{top_k}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval_port(strat_ret, key,
                                    f"CS Momentum {lookback}-{skip} top{top_k} sectors",
                                    "3.1", {"lookback": lookback, "skip": skip, "top_k": top_k},
                                    N_TESTS)
            candidates_oos.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")
    except Exception as e:
        print(f"  ERROR {key}: {e}")


# ────────────────────────────────────────────────────────────────────────────
# 3.1b  CS Momentum with Vol Targeting
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 3.1b CS Momentum + Vol Targeting ---")

def cs_mom_vol_targeted(ret_df: pd.DataFrame, lookback: int, skip: int,
                         top_k: int, cost: float, target_vol: float = 0.15) -> pd.Series:
    """CS momentum with daily vol targeting overlay."""
    raw = cs_momentum_portfolio(ret_df, lookback, skip, top_k, cost)
    if raw.empty:
        return raw
    # 63-day rolling vol estimate
    roll_vol = raw.rolling(63).std() * np.sqrt(252)
    scale = (target_vol / roll_vol).clip(0.1, 3.0)
    return (raw * scale.shift(1)).fillna(0)


for lookback, skip, top_k in [(12, 1, 3), (6, 1, 3), (12, 1, 2)]:
    N_TESTS += 1
    try:
        strat_ret = cs_mom_vol_targeted(ret_df, lookback, skip, top_k, COST_ETF)
        sr = fast_is_sr_port(strat_ret)
        key = f"P3.1b_CSMom{lookback}_{skip}_top{top_k}_VT"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval_port(strat_ret, key,
                                    f"CS Momentum {lookback}-{skip} top{top_k} + VolTarget",
                                    "3.1b",
                                    {"lookback": lookback, "skip": skip, "top_k": top_k, "vol_target": 0.15},
                                    N_TESTS)
            candidates_oos.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")
    except Exception as e:
        print(f"  ERROR {key}: {e}")


# ────────────────────────────────────────────────────────────────────────────
# 3.2  CS Short-Term Reversal
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 3.2 CS Short-Term Reversal ---")

def cs_reversal_portfolio(ret_df: pd.DataFrame, lookback_days: int,
                           top_k: int, cost: float, rebal_freq: str = "W") -> pd.Series:
    """Weekly rebalanced CS reversal — long recent losers, short recent winners."""
    prices_r = price_df.resample(rebal_freq).last()

    positions_list = []
    for i in range(lookback_days // 5 + 1, len(prices_r)):
        ref_date = prices_r.index[i]
        past_idx = max(0, i - lookback_days // 5)
        past_date = prices_r.index[past_idx]

        signal = prices_r.loc[ref_date] / prices_r.loc[past_date] - 1
        ranked = signal.rank(ascending=False)  # high return = high rank
        n = len(ranked)
        # Reversal: long bottom (losers), short top (winners)
        pos = pd.Series(0.0, index=signal.index)
        pos[ranked > (n - top_k)]  = 1.0 / top_k   # long losers
        pos[ranked <= top_k]       = -1.0 / top_k   # short winners
        pos.name = ref_date
        positions_list.append(pos)

    if not positions_list:
        return pd.Series(dtype=float)

    positions = pd.DataFrame(positions_list)
    daily_rets = ret_df.copy()
    port_ret = pd.Series(0.0, index=daily_rets.index)

    for i, ref_date in enumerate(positions.index):
        if i + 1 < len(positions.index):
            next_date = positions.index[i + 1]
        else:
            next_date = daily_rets.index[-1]
        hold_mask = (daily_rets.index > ref_date) & (daily_rets.index <= next_date)
        daily_rows = daily_rets.loc[hold_mask]
        pos_row = positions.iloc[i]
        for dt, row in daily_rows.iterrows():
            port_ret[dt] = (pos_row * row).sum()

    # Cost
    for i, ref_date in enumerate(positions.index[1:], 1):
        prev_pos = positions.iloc[i - 1]
        curr_pos = positions.iloc[i]
        turnover = (curr_pos - prev_pos).abs().sum() / 2
        next_days = daily_rets.index[daily_rets.index > ref_date]
        if len(next_days) > 0:
            port_ret[next_days[0]] -= turnover * cost

    return port_ret


REV_PARAMS = [(5, 3), (10, 3), (21, 3), (5, 2), (10, 2)]
for lookback_d, top_k in REV_PARAMS:
    N_TESTS += 1
    try:
        strat_ret = cs_reversal_portfolio(ret_df, lookback_d, top_k, COST_ETF)
        sr = fast_is_sr_port(strat_ret)
        key = f"P3.2_CSRev{lookback_d}d_top{top_k}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval_port(strat_ret, key,
                                    f"CS Reversal {lookback_d}d top{top_k}",
                                    "3.2", {"lookback_d": lookback_d, "top_k": top_k}, N_TESTS)
            candidates_oos.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")
    except Exception as e:
        print(f"  ERROR {key}: {e}")


# ────────────────────────────────────────────────────────────────────────────
# 3.4  PCA Residual Stat-Arb on sectors
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 3.4 PCA Residual Stat-Arb ---")
from sklearn.decomposition import PCA

def pca_residual_statarb(ret_df: pd.DataFrame, n_components: int,
                          z_entry: float, z_exit: float, cost: float,
                          lookback: int = 252) -> pd.Series:
    """
    Rolling PCA: regress each sector on top n_components.
    Trade residual z-score: long when z < -z_entry, short when z > z_entry, exit at |z| < z_exit.
    Equal-weight across all active positions.
    """
    daily_rets = ret_df.copy()
    positions = pd.DataFrame(0.0, index=daily_rets.index, columns=daily_rets.columns)

    for i in range(lookback, len(daily_rets)):
        window = daily_rets.iloc[i - lookback:i].values
        # PCA on the window
        pca = PCA(n_components=min(n_components, window.shape[1] - 1))
        factors = pca.fit_transform(window)  # (T, n_comp)
        loadings = pca.components_  # (n_comp, N_assets)
        residuals = window - factors @ loadings  # (T, N_assets)

        # Z-score of most recent residual relative to window
        res_mean = residuals.mean(axis=0)
        res_std  = residuals.std(axis=0)
        z = (residuals[-1] - res_mean) / (res_std + 1e-8)

        # Entry/exit signals
        today = daily_rets.index[i]
        prev_pos = positions.iloc[i - 1]
        new_pos = prev_pos.copy()

        # Entry: when z > z_entry or z < -z_entry (not already in position)
        new_pos[(z < -z_entry) & (prev_pos == 0)] = 1.0
        new_pos[(z > z_entry) & (prev_pos == 0)]  = -1.0

        # Exit: when |z| < z_exit
        new_pos[((abs(z) < z_exit)) & (prev_pos != 0)] = 0.0

        positions.iloc[i] = new_pos

    # Normalise position to unit weight
    pos_sum = positions.abs().sum(axis=1).replace(0, np.nan)
    positions_norm = positions.div(pos_sum, axis=0).fillna(0)

    # Strategy returns
    port_ret = (positions_norm.shift(1) * daily_rets).sum(axis=1)

    # Cost: on position changes
    turnover = positions_norm.diff().abs().sum(axis=1)
    port_ret -= turnover * cost

    return port_ret


PCA_PARAMS = [(3, 1.5, 0.5), (2, 1.5, 0.5), (3, 2.0, 0.5), (1, 1.5, 0.5)]
for n_comp, z_in, z_out in PCA_PARAMS:
    N_TESTS += 1
    try:
        strat_ret = pca_residual_statarb(ret_df, n_comp, z_in, z_out, COST_ETF)
        sr = fast_is_sr_port(strat_ret)
        key = f"P3.4_PCA{n_comp}_z{int(z_in*10)}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval_port(strat_ret, key,
                                    f"PCA{n_comp} residual stat-arb z{z_in}/{z_out}",
                                    "3.4",
                                    {"n_components": n_comp, "z_entry": z_in, "z_exit": z_out},
                                    N_TESTS)
            candidates_oos.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")
    except Exception as e:
        print(f"  ERROR {key}: {e}")


# ────────────────────────────────────────────────────────────────────────────
# Summary
# ────────────────────────────────────────────────────────────────────────────
print(f"\n=== Phase 3 Summary ===")
p3_count = N_TESTS - N_PREV
print(f"Phase 3 tests: {p3_count}")
print(f"Running n_tests: {N_TESTS}")
print(f"IS passes: {len(candidates_oos)}")
for c in candidates_oos:
    print(f"  → {c['id']}: IS={c['sr_is']:.2f} OOS={c['sr_oos']:.2f} HOLD={c['sr_hold']:.2f}")

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "phase3_results.json")
with open(RESULTS_FILE, "w") as f:
    json.dump({"n_tests": N_TESTS, "candidates": candidates_oos}, f, indent=2, default=str)
print(f"Results saved: {RESULTS_FILE}")
