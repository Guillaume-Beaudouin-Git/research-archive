"""
run_kill_test.py — Two-sided TSMOM BTC/ETH on FTMO crypto CFD: kill-or-confirm.

Hypothesis H1
-------------
Take Strategy A's signal verbatim (strategies.tsmom_v2_propfirm.signal.compute_signal,
lookback=28, tanh of t-stat) and REMOVE the .clip(lower=0) so the short leg fires on
negative momentum. Weekly Monday rebalance. BTC + ETH only (per user: SOL spread too
wide on FTMO CFD).

Cost model
----------
- Spread RT: BTC empirical (FTMO MT5 panel data/panels/m5_indices/BTCUSD_M1.csv, median
  9 USD/BTC over 2018-11→2026-05 = 2.32 bps). ETH: no MT5 panel with spread in repo →
  conservative 2× BTC spread (public reviews: ETH spread typically 1.5-2x BTC on FTMO).
- Commission: 0.065% RT verbatim from ftmo.com blog (PropFirms/ftmo/rules.md, 2026 quote).
- Markup: feed-raw (=1.0) AND retail-vs-feed (=2.0) reported side-by-side.
- Swap: user-asserted prohibitive (overnight crypto FTMO not hold-able). This script
  runs the swap=0 COUNTERFACTUAL — even if swap were 0, does the two-sided edge exist?
  If no, the verdict is reinforced: the strategy dies on signal AND on swap.

Output
------
Split-by-direction table (L25): LONG / SHORT legs separately, plus long-survivor check
against A long-only.

Hard rules respected
--------------------
- Signal at T-1, trade at T: enforced by .shift(1) inside compute_signal (cf. signal.py:62).
- Excess returns: NOT applied for per-trade drift — this is a per-trade arithmetic drift
  test, not an annualized excess-return Sharpe vs cash. Per-trade is the right unit when
  the question is "does any cost-feasibility ceiling exist".
- HAC lag-6: applied for t-stat on weekly returns.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from strategies.tsmom_v2_propfirm.signal import compute_signal, apply_weekly_rebalance  # noqa: E402


# -- cost constants (bps RT, per rebalance) ------------------------------------
SPREAD_RT_BPS = {"BTC": 2.32, "ETH": 4.64}          # ETH = 2× BTC (no MT5 panel)
COMMISSION_RT_BPS = 6.50                            # FTMO blog: 0.0325%/side × 2
MARKUPS = (1.0, 2.0)                                # feed-raw and retail-vs-feed (L23b)


# -- data ----------------------------------------------------------------------
def load_prices() -> pd.DataFrame:
    btc = pd.read_csv(REPO / "data/ftmo_universe/daily_panels/crypto/btc_full.csv",
                      parse_dates=["Date"]).rename(columns={"BTC-USD": "BTC"}).set_index("Date")
    crypto = pd.read_csv(REPO / "data/ftmo_universe/daily_panels/crypto/crypto_panel.csv",
                         parse_dates=["Date"]).set_index("Date")
    eth = crypto[["ETHUSD"]].rename(columns={"ETHUSD": "ETH"})
    px = btc.join(eth, how="inner").dropna()
    return px


# -- signal (two-sided variant of A) ------------------------------------------
def compute_signal_twosided(prices: pd.DataFrame, lookback: int = 28) -> pd.DataFrame:
    """Same as compute_signal but signal NOT clipped at 0 (allow short leg)."""
    log_ret = np.log(prices / prices.shift(1))
    cum_ret = log_ret.rolling(lookback).sum().shift(1)
    vol = log_ret.rolling(lookback).std().shift(1) * np.sqrt(lookback)
    t_stat = cum_ret / (vol + 1e-8)
    signal = np.tanh(t_stat)
    signal[cum_ret.isna()] = np.nan
    return signal


# -- per-trade table -----------------------------------------------------------
def per_trade_legs(prices: pd.DataFrame, signal_weekly: pd.DataFrame,
                   cost_rt_bps: dict[str, float]) -> pd.DataFrame:
    """
    Aggregate weekly trades by direction (LONG / SHORT) per asset.

    A "trade" is one week of holding a position. The Monday signal s_t determines
    the direction and notional size in [-1, +1]. Gross weekly return = s_t × sum
    of daily log returns Monday→next-Monday. Cost = |s_t| × cost_rt_bps (paid once
    per rebalance; under continuous rebalance with similar |s|, this is the natural
    per-trade unit consistent with weekly cycling notional).

    Returns DataFrame with rows = (asset, leg) and columns:
      N | gross_bps | cost_bps | net_bps | t_HAC6 | L11_ratio (gross / 3×cost)
    """
    log_ret = np.log(prices / prices.shift(1))
    rows: list[dict] = []
    weekly = signal_weekly.copy()
    for asset in prices.columns:
        s = weekly[asset]
        is_mon = pd.Series(s.index.dayofweek == 0, index=s.index)
        mon_signals = s[is_mon].dropna()

        for leg_name, leg_mask in [("LONG", mon_signals > 0), ("SHORT", mon_signals < 0)]:
            mondays = mon_signals.index[leg_mask]
            if len(mondays) == 0:
                rows.append({"asset": asset, "leg": leg_name, "N": 0,
                             "gross_bps": np.nan, "cost_bps": np.nan,
                             "net_bps": np.nan, "t_HAC6": np.nan, "L11_ratio": np.nan})
                continue

            # gross return for each weekly trade
            trades = []
            for mon in mondays:
                s_mon = mon_signals.loc[mon]
                next_idx = mon_signals.index.get_loc(mon) + 1
                if next_idx >= len(mon_signals.index):
                    continue
                next_mon = mon_signals.index[next_idx]
                week_ret = log_ret[asset].loc[mon:next_mon].iloc[1:].sum()
                gross = s_mon * week_ret
                cost = abs(s_mon) * cost_rt_bps[asset] * 1e-4
                net = gross - cost
                trades.append({"mon": mon, "s": s_mon, "gross": gross,
                               "cost": cost, "net": net})
            if not trades:
                continue
            tdf = pd.DataFrame(trades).set_index("mon")

            # HAC lag-6 t-stat on net per-trade drift (intercept-only OLS)
            y = tdf["net"].values
            X = add_constant(np.ones_like(y))[:, [0]]
            res = OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
            t_hac = float(res.tvalues[0])

            mean_gross_bps = tdf["gross"].mean() * 1e4
            mean_cost_bps = tdf["cost"].mean() * 1e4
            mean_net_bps = tdf["net"].mean() * 1e4
            ratio = mean_gross_bps / (3 * mean_cost_bps) if mean_cost_bps > 0 else np.nan

            rows.append({"asset": asset, "leg": leg_name, "N": int(len(tdf)),
                         "gross_bps": round(mean_gross_bps, 2),
                         "cost_bps":  round(mean_cost_bps, 2),
                         "net_bps":   round(mean_net_bps, 2),
                         "t_HAC6":    round(t_hac, 2),
                         "L11_ratio": round(ratio, 2) if not np.isnan(ratio) else np.nan})
    return pd.DataFrame(rows)


# -- A long-only reproduction (for survivor check) ----------------------------
def long_only_legs(prices: pd.DataFrame, cost_rt_bps: dict[str, float]) -> pd.DataFrame:
    """Reproduce Strategy A (signal clipped at 0) — long-leg only by construction."""
    daily = compute_signal(prices, lookback=28)
    weekly = apply_weekly_rebalance(daily, rebalance_weekday=0)
    return per_trade_legs(prices, weekly, cost_rt_bps)


# -- delay-1 sensitivity (L26) ------------------------------------------------
def delay_sensitivity(prices: pd.DataFrame, cost_rt_bps: dict[str, float]) -> pd.DataFrame:
    """
    Compare signal computed with .shift(1) (canonical: trade at T uses signal
    from T-1 close) vs .shift(0) (look-ahead artifact: signal uses T close).

    Weekly cycle is low-frequency, so we expect minimal change; a large change
    flags a fill-timing artifact.
    """
    out = []
    for delay, label in [(1, "delay-1 (canonical)"), (0, "delay-0 (look-ahead)")]:
        log_ret = np.log(prices / prices.shift(1))
        cum_ret = log_ret.rolling(28).sum().shift(delay)
        vol = log_ret.rolling(28).std().shift(delay) * np.sqrt(28)
        t_stat = cum_ret / (vol + 1e-8)
        signal = np.tanh(t_stat)
        signal[cum_ret.isna()] = np.nan
        weekly = apply_weekly_rebalance(signal, rebalance_weekday=0)
        tbl = per_trade_legs(prices, weekly, cost_rt_bps)
        tbl.insert(0, "scenario", label)
        out.append(tbl)
    return pd.concat(out, ignore_index=True)


# -- DSR on aggregate net Sharpe ----------------------------------------------
def aggregate_sharpe_and_dsr(prices: pd.DataFrame, signal_weekly: pd.DataFrame,
                             cost_rt_bps: dict[str, float], n_trials: int) -> dict:
    """
    Pool weekly net returns across BTC + ETH (equal-weight pooling) and report
    annualised Sharpe + Bailey-LdP DSR at n_trials.
    """
    from scipy.stats import norm

    log_ret = np.log(prices / prices.shift(1))
    weekly_index = signal_weekly.index[signal_weekly.index.dayofweek == 0]
    all_net = []
    for mon in weekly_index:
        for asset in prices.columns:
            s_mon = signal_weekly[asset].loc[mon] if mon in signal_weekly.index else np.nan
            if np.isnan(s_mon) or s_mon == 0:
                continue
            next_mons = weekly_index[weekly_index > mon]
            if len(next_mons) == 0:
                continue
            next_mon = next_mons[0]
            week_ret = log_ret[asset].loc[mon:next_mon].iloc[1:].sum()
            gross = s_mon * week_ret
            cost = abs(s_mon) * cost_rt_bps[asset] * 1e-4
            all_net.append(gross - cost)
    arr = np.array(all_net)
    if len(arr) < 10:
        return {"sharpe_weekly": np.nan, "sharpe_ann": np.nan, "dsr": np.nan}

    sr_w = arr.mean() / arr.std(ddof=1)
    # 52 weekly trades/year × 2 assets pooled = 104 trades/yr; annualise by √104
    sr_ann = sr_w * np.sqrt(104)
    # DSR (Bailey-LdP): correction for selection from n_trials independent strategies
    # SR_0 = sqrt(2 * ln(N)); inverse-normal of E_max(SR_trial)
    skew = pd.Series(arr).skew()
    kurt = pd.Series(arr).kurt()
    T = len(arr)
    if T <= 1:
        return {"sharpe_weekly": sr_w, "sharpe_ann": sr_ann, "dsr": np.nan}
    emax_z = (1 - np.euler_gamma) * norm.ppf(1 - 1/n_trials) + np.euler_gamma * norm.ppf(1 - 1/(n_trials*np.e))
    sr0_w = emax_z * np.sqrt(1/T)
    denom = np.sqrt(1 - skew * sr_w + (kurt - 1) / 4 * sr_w**2)
    dsr_prob = norm.cdf((sr_w - sr0_w) / denom * np.sqrt(T - 1))
    return {"sharpe_weekly": round(sr_w, 3), "sharpe_ann": round(sr_ann, 2),
            "dsr_prob": round(dsr_prob, 3), "n_trials_assumed": n_trials,
            "T_weeks": T, "skew": round(skew, 2), "kurt": round(kurt, 2)}


# -- main ---------------------------------------------------------------------
def main() -> int:
    prices = load_prices()
    print("=" * 90)
    print("FTMO crypto-CFD two-sided TSMOM — kill-or-confirm (H1)")
    print("=" * 90)
    print(f"\nData: {prices.index.min().date()} → {prices.index.max().date()} | "
          f"N={len(prices)} days | assets={list(prices.columns)}\n")

    # signals
    sig_2s = compute_signal_twosided(prices)
    sig_2s_weekly = apply_weekly_rebalance(sig_2s)

    print("─" * 90)
    print("Per-trade table by direction (BTC/ETH, two-sided H1) — swap=0 COUNTERFACTUAL")
    print("─" * 90)

    for markup in MARKUPS:
        costs = {a: (SPREAD_RT_BPS[a] * markup + COMMISSION_RT_BPS) for a in SPREAD_RT_BPS}
        cost_label = f"markup={markup} → BTC cost={costs['BTC']:.1f} bps, ETH cost={costs['ETH']:.1f} bps"
        print(f"\n[{cost_label}]")
        tbl = per_trade_legs(prices, sig_2s_weekly, costs)
        print(tbl.to_string(index=False))

    # Long-survivor check: H1 long-leg vs A long-only
    print("\n" + "─" * 90)
    print("Long-survivor check (b): H1 long-leg vs A long-only (markup=1, swap=0)")
    print("─" * 90)
    costs1 = {a: (SPREAD_RT_BPS[a] * 1.0 + COMMISSION_RT_BPS) for a in SPREAD_RT_BPS}
    h1_tbl = per_trade_legs(prices, sig_2s_weekly, costs1)
    a_tbl = long_only_legs(prices, costs1)
    a_long_rows = a_tbl[a_tbl["leg"] == "LONG"]
    h1_long_rows = h1_tbl[h1_tbl["leg"] == "LONG"]
    cmp = a_long_rows.merge(h1_long_rows, on=["asset", "leg"], suffixes=("_A_LO", "_H1_LongLeg"))
    print(cmp.to_string(index=False))

    # Delay-1 sensitivity (L26)
    print("\n" + "─" * 90)
    print("Delay sensitivity (L26): delay-1 (canonical) vs delay-0 (look-ahead)")
    print("─" * 90)
    delay_tbl = delay_sensitivity(prices, costs1)
    print(delay_tbl.to_string(index=False))

    # DSR on aggregate net
    print("\n" + "─" * 90)
    print("DSR on aggregate net Sharpe (H1, pooled BTC+ETH, markup=1, swap=0)")
    print("─" * 90)
    dsr = aggregate_sharpe_and_dsr(prices, sig_2s_weekly, costs1, n_trials=3)
    print(dsr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
