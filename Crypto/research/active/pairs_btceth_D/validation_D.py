"""
validation_D.py — Validate Strategy D (BTC/ETH pairs cointégration + Kalman).

Source: Park (IJSRA 2026), claimed Sharpe 2.23 on Jan 2022 - Oct 2024.

Apply the 4 stat-arb killers from data/ftmo_research/statarb_deepdive_ftmo.md:
  1. Cointegration OOS — does the relation hold OUTSIDE the Park window?
  2. Half-life OU — intraday-tradeable or multi-day (funding applies)?
  3. Funding two legs — the 2x structural drag, the most probable killer.
  4. Two-sided in spread / beta drift — is the "reversion" real or harvested drift?

Plus: DSR Bailey-LdP on the claimed 2.23, delay-1 test (the artifact arbiter).

Data:
  - BTC/ETH M1 spot Binance, 2018-01 to 2026-06.
  - BTC/ETH funding rates (Hyperliquid proxy for Bybit perp), 2023-05 to 2026-05.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from statsmodels.tsa.stattools import adfuller
from scipy.stats import norm

DATA_ROOT = Path("<HOME>/Desktop/Algo_claude")
BTC_SPOT = DATA_ROOT / "data/panels/m5_indices/binance/BTCUSD_M1.csv"
ETH_SPOT = DATA_ROOT / "data/panels/m5_indices/binance/ETHUSD_M1.csv"
BTC_FUND = DATA_ROOT / "data/funding_carry/BTC_funding.csv"
ETH_FUND = DATA_ROOT / "data/funding_carry/ETH_funding.csv"
OUT = DATA_ROOT / "Crypto/research/active/pairs_btceth_D"

PARK_LO = "2022-01-01"
PARK_HI = "2024-10-31"
PRE_LO  = "2018-01-01"
PRE_HI  = "2021-12-31"
POST_LO = "2024-11-01"
POST_HI = "2026-06-01"


def load_1h_aligned() -> pd.DataFrame:
    """Load BTC+ETH M1, resample 1H, return aligned closes."""
    cache = OUT / "_btceth_1h.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    print("  First time: loading + resampling M1 → 1H...")
    btc = pd.read_csv(BTC_SPOT, parse_dates=["timestamp_utc"])
    btc = btc.set_index("timestamp_utc").sort_index()
    btc_1h = btc["close"].resample("1h").last().rename("BTC")
    eth = pd.read_csv(ETH_SPOT, parse_dates=["timestamp_utc"])
    eth = eth.set_index("timestamp_utc").sort_index()
    eth_1h = eth["close"].resample("1h").last().rename("ETH")
    df = pd.concat([btc_1h, eth_1h], axis=1).dropna()
    df.to_parquet(cache)
    print(f"  Cached {len(df):,} 1h bars to {cache}")
    return df


def load_funding() -> pd.DataFrame:
    """Load BTC + ETH funding rates per hour (assumed Bybit ~ HL proxy)."""
    btc = pd.read_csv(BTC_FUND, parse_dates=["timestamp"])
    eth = pd.read_csv(ETH_FUND, parse_dates=["timestamp"])
    btc = btc.set_index("timestamp")["funding_rate_1h"].rename("BTC_fund_1h")
    eth = eth.set_index("timestamp")["funding_rate_1h"].rename("ETH_fund_1h")
    df = pd.concat([btc, eth], axis=1).dropna()
    # Strip timezone for consistency with M1 spot data (naive UTC)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


def ou_half_life(spread: pd.Series) -> tuple[float, float]:
    """Return (half-life in BARS, mean-reversion strength beta)."""
    s = spread.dropna()
    lag = s.shift(1)
    d = (s - lag).dropna()
    lag = lag.loc[d.index]
    if len(d) < 100:
        return np.nan, np.nan
    beta = np.polyfit(lag.values, d.values, 1)[0]
    phi = 1 + beta
    if not (0 < phi < 1):
        return np.nan, beta
    return float(-np.log(2) / np.log(phi)), float(beta)


def eg_test(logA: pd.Series, logB: pd.Series) -> dict:
    """Engle-Granger: OLS hedge ratio + ADF on residual."""
    X = np.vstack([np.ones(len(logB)), logB.values]).T
    coef, *_ = np.linalg.lstsq(X, logA.values, rcond=None)
    resid = logA.values - X @ coef
    adf_stat, p_val, *_ = adfuller(resid, maxlag=24, autolag=None)
    return {"alpha": coef[0], "beta": coef[1], "residuals": resid,
            "adf_stat": adf_stat, "p_value": p_val}


def kalman_dynamic_beta(logA: np.ndarray, logB: np.ndarray,
                        delta: float = 1e-4, R: float = 1e-3):
    """
    Kalman filter for dynamic hedge ratio beta_t (and alpha_t):
      State: theta_t = [alpha_t, beta_t]'
      Observation: logA_t = alpha_t + beta_t * logB_t + noise

    delta = process noise variance (controls how quickly beta drifts)
    R = observation noise variance
    """
    n = len(logA)
    Q = (delta / (1 - delta)) * np.eye(2)
    # State init
    theta = np.zeros(2)
    P = 1.0 * np.eye(2)
    alphas = np.zeros(n)
    betas = np.zeros(n)
    spreads = np.zeros(n)
    for t in range(n):
        # Predict
        P_pred = P + Q
        # Observation matrix at t
        H = np.array([1.0, logB[t]])
        # Innovation
        y_hat = H @ theta
        v = logA[t] - y_hat
        # Innovation covariance
        S = H @ P_pred @ H + R
        # Kalman gain
        K = (P_pred @ H) / S
        # Update
        theta = theta + K * v
        P = P_pred - np.outer(K, H @ P_pred)
        alphas[t] = theta[0]
        betas[t] = theta[1]
        spreads[t] = v  # residual = current spread
    return alphas, betas, spreads


def split_window(df: pd.DataFrame, lo: str, hi: str) -> pd.DataFrame:
    return df.loc[lo:hi].copy()


def run_eg_on_window(df_1h: pd.DataFrame, lo: str, hi: str, label: str) -> dict:
    """Engle-Granger on a specific window."""
    sub = split_window(df_1h, lo, hi)
    if len(sub) < 1000:
        return {"label": label, "n": len(sub), "p_value": np.nan, "beta": np.nan, "hl_h": np.nan}
    logA = np.log(sub["BTC"])
    logB = np.log(sub["ETH"])
    res = eg_test(logA, logB)
    hl, _ = ou_half_life(pd.Series(res["residuals"]))
    return {"label": label, "n": len(sub), "lo": lo, "hi": hi,
            "alpha": res["alpha"], "beta": res["beta"],
            "adf_stat": res["adf_stat"], "p_value": res["p_value"],
            "hl_hours": hl}


def kalman_backtest(sub: pd.DataFrame, z_entry: float = 2.0, z_exit: float = 0.5,
                     funding_df: pd.DataFrame = None, cost_bps_per_leg: float = 1.0,
                     delay_bars: int = 0,
                     z_window: int = 60) -> dict:
    """
    Z-score MR strategy on Kalman spread.
    - Enter short spread (= short BTC / long beta×ETH) when z > +z_entry
    - Enter long spread when z < -z_entry
    - Exit when |z| < z_exit
    - cost_bps_per_leg per side per turn (4 cost events per round trip: enter A enter B exit A exit B)
    - funding applied per hour on both legs
    - delay_bars = 0 (same bar fill) or 1 (next-bar)
    """
    logA = np.log(sub["BTC"].values)
    logB = np.log(sub["ETH"].values)
    alphas, betas, spreads = kalman_dynamic_beta(logA, logB)
    # Rolling z-score of the residual
    spread_s = pd.Series(spreads, index=sub.index)
    mu = spread_s.rolling(z_window).mean()
    sd = spread_s.rolling(z_window).std()
    z = ((spread_s - mu) / sd).fillna(0.0)

    # Generate signals: +1 = long spread (= long BTC, short β·ETH)
    #                  -1 = short spread (= short BTC, long β·ETH)
    pos = np.zeros(len(z))
    for i in range(1, len(z)):
        prev = pos[i - 1]
        zv = z.iloc[i]
        if prev == 0:
            if zv > z_entry:
                pos[i] = -1
            elif zv < -z_entry:
                pos[i] = +1
        else:
            if abs(zv) < z_exit:
                pos[i] = 0
            else:
                pos[i] = prev
    # Apply delay: signal at time t is implemented at time t + delay_bars
    if delay_bars > 0:
        pos = np.concatenate([np.zeros(delay_bars), pos[:-delay_bars]])

    # Returns: log returns
    rA = np.diff(logA, prepend=logA[0])
    rB = np.diff(logB, prepend=logB[0])
    # Position in spread: +1 means long BTC, short β·ETH
    # PnL_t = pos_t * (rA_t - beta_{t-1} * rB_t)
    # (use beta_{t-1} because position is held BEFORE realizing rt)
    beta_lag = np.concatenate([[betas[0]], betas[:-1]])
    spread_ret_gross = pos * (rA - beta_lag * rB)

    # Cost (4 legs per round trip at change in position)
    cost = np.zeros(len(pos))
    for i in range(1, len(pos)):
        if pos[i] != pos[i-1]:
            # Position changed = 2 trades (enter new or exit + enter), cost = 2 legs each * bps
            # Approximation: 2 cost events × cost_bps_per_leg per side × 2 sides = 4 × cost_bps_per_leg
            # In log units: cost in fraction = cost_bps_per_leg/10000 * 4 (2 entries + 2 exits if full swap)
            n_legs = 4 if (pos[i-1] != 0 and pos[i] != 0 and pos[i] != pos[i-1]) else 2
            cost[i] = n_legs * cost_bps_per_leg / 10000.0

    # Funding: assume hourly funding on both legs of the perp pair
    # Position in perp leg = pos * 1 unit BTC + pos * (-beta) units ETH (gross long-short)
    # Funding paid = pos * sign(leg) * funding_rate_1h
    # For long BTC + short ETH (pos = +1):
    #   pay funding rate on the LONG side, receive on the SHORT side (if pos)
    # Conventional perp: long pays positive funding, short receives.
    # Net funding = -pos * (BTC_fund - beta * ETH_fund)  [paid by long, received by short]
    funding_cost = np.zeros(len(pos))
    if funding_df is not None and len(funding_df):
        # Align funding to sub.index (forward fill from 8h granularity)
        f_btc = funding_df["BTC_fund_1h"].reindex(sub.index, method="ffill").fillna(0).values
        f_eth = funding_df["ETH_fund_1h"].reindex(sub.index, method="ffill").fillna(0).values
        # For long BTC / short β·ETH (pos=+1): pay BTC funding, receive β·ETH funding
        funding_cost = pos * (f_btc - beta_lag * f_eth)
        # Note: funding rates are typically reported as RATE (positive = long pays).
        # If pos > 0 (long BTC), we PAY f_btc; if pos > 0 we SHORT β·ETH, so we RECEIVE β·ETH funding.
        # Net cost = pos × f_btc - pos × β × f_eth (signs match).

    spread_ret_net = spread_ret_gross - cost - funding_cost

    # Equity curve
    eq_gross = np.exp(np.cumsum(spread_ret_gross))
    eq_net = np.exp(np.cumsum(spread_ret_net))

    # Sharpe (annualized, hourly bars → sqrt(24*365))
    annfac = np.sqrt(24 * 365)
    sr_gross = (spread_ret_gross.mean() / spread_ret_gross.std() * annfac) if spread_ret_gross.std() > 0 else 0
    sr_net = (spread_ret_net.mean() / spread_ret_net.std() * annfac) if spread_ret_net.std() > 0 else 0
    # Long-only / short-only split
    long_mask = pos > 0
    short_mask = pos < 0
    sr_long = sr_short = np.nan
    if long_mask.sum() > 20 and spread_ret_net[long_mask].std() > 0:
        sr_long = spread_ret_net[long_mask].mean() / spread_ret_net[long_mask].std() * annfac
    if short_mask.sum() > 20 and spread_ret_net[short_mask].std() > 0:
        sr_short = spread_ret_net[short_mask].mean() / spread_ret_net[short_mask].std() * annfac

    # Total return + max DD
    total_gross = eq_gross[-1] - 1
    total_net = eq_net[-1] - 1
    eq_net_s = pd.Series(eq_net)
    max_dd = (eq_net_s / eq_net_s.cummax() - 1).min()

    return {
        "n_bars": len(sub),
        "n_entries": int(((pos != 0) & (np.concatenate([[0], pos[:-1]]) == 0)).sum()),
        "frac_in_pos": float((pos != 0).mean()),
        "sr_gross_ann": sr_gross,
        "sr_net_ann": sr_net,
        "sr_long_ann": sr_long,
        "sr_short_ann": sr_short,
        "total_ret_gross": total_gross,
        "total_ret_net": total_net,
        "max_dd_net": max_dd,
        "cost_total_pct": cost.sum() * 100,
        "funding_total_pct": funding_cost.sum() * 100,
        "mean_beta": float(betas.mean()),
        "std_beta": float(betas.std()),
        "delay_bars": delay_bars,
    }


def deflated_sharpe(sr_obs: float, t_obs_days: int, n_trials: int,
                    skew: float = 0.0, kurt: float = 0.0) -> dict:
    if t_obs_days <= 2 or n_trials < 1:
        return {"sr0": np.nan, "sr_def": np.nan, "p_real": np.nan}
    gamma = 0.5772
    e = np.e
    EmaxN = ((1 - gamma) * norm.ppf(1 - 1/n_trials)
             + gamma * norm.ppf(1 - 1/(n_trials * e)))
    sr_daily = sr_obs / np.sqrt(252)
    var = (1 - skew * sr_daily + (kurt - 1) / 4 * sr_daily**2) / (t_obs_days - 1)
    if var <= 0:
        return {"sr0": np.nan, "sr_def": np.nan, "p_real": np.nan}
    sr0_daily = np.sqrt(var) * EmaxN
    sr0_ann = sr0_daily * np.sqrt(252)
    denom = np.sqrt(var) * np.sqrt(252)
    z = (sr_obs - sr0_ann) / denom if denom > 0 else np.nan
    p_real = float(norm.cdf(z)) if not np.isnan(z) else np.nan
    return {"sr0": sr0_ann, "sr_def": sr_obs - sr0_ann, "z": z, "p_real": p_real}


if __name__ == "__main__":
    print("=" * 90)
    print("VALIDATION D — BTC/ETH pairs Kalman, 4 killers + DSR + delay-1")
    print("=" * 90)
    df_1h = load_1h_aligned()
    print(f"\n1H aligned: {len(df_1h):,} bars, range {df_1h.index.min()} → {df_1h.index.max()}")
    funding = load_funding()
    print(f"Funding: {len(funding):,} hourly bars, range {funding.index.min()} → {funding.index.max()}")

    # ---- KILLER 1: cointegration OOS ----
    print("\n" + "=" * 90)
    print("KILLER 1 — Cointegration OOS")
    print("=" * 90)
    windows = [
        ("FULL 2018-2026", "2018-01-01", "2026-06-01"),
        ("PRE-Park 2018-2021", PRE_LO, PRE_HI),
        ("PARK Jan2022-Oct2024", PARK_LO, PARK_HI),
        ("POST-Park Nov2024-Jun2026", POST_LO, POST_HI),
    ]
    eg_rows = []
    for label, lo, hi in windows:
        res = run_eg_on_window(df_1h, lo, hi, label)
        eg_rows.append(res)
        print(f"  {label:>26}: n={res['n']}, beta={res['beta']:.4f}, "
              f"ADF p={res['p_value']:.4f}, HL={res['hl_hours']:.1f}h")
    pd.DataFrame(eg_rows).to_csv(OUT / "killer1_coint_oos.csv", index=False)

    # ---- KILLER 2: Half-life ----
    print("\n" + "=" * 90)
    print("KILLER 2 — Half-life OU (does spread revert intraday or multi-day?)")
    print("=" * 90)
    for r in eg_rows:
        hl_d = r["hl_hours"] / 24
        verdict = "intraday" if r["hl_hours"] <= 24 else "multi-day (funding applies)"
        print(f"  {r['label']:>26}: HL = {r['hl_hours']:.1f}h = {hl_d:.1f}d → {verdict}")

    # ---- KILLERS 3-4 + DSR + delay-1 via Kalman backtest ----
    print("\n" + "=" * 90)
    print("KILLERS 3-4 + delay-1: Kalman backtest with funding + 2-leg cost")
    print("=" * 90)
    # Run backtests on Park window with various cost/funding configs
    sub_park = split_window(df_1h, PARK_LO, PARK_HI)
    print(f"\nPark window: n={len(sub_park)} 1H bars")
    # Sub-window where funding is available (May 2023 - Oct 2024)
    sub_park_with_fund = split_window(df_1h, "2023-05-15", PARK_HI)
    print(f"Park sub-window with funding (May 2023+): n={len(sub_park_with_fund)} 1H bars")

    bt_rows = []
    for label, sub, fund_df, cost_bps in [
        ("Park GROSS no-cost no-fund delay=0", sub_park, None, 0.0),
        ("Park GROSS no-cost no-fund delay=1", sub_park, None, 0.0),
        ("Park 1bp 1leg cost only delay=0", sub_park, None, 1.0),
        ("Park 1bp + funding May2023+ delay=0", sub_park_with_fund, funding, 1.0),
        ("Park 1bp + funding May2023+ delay=1", sub_park_with_fund, funding, 1.0),
        ("Park 2bp + funding May2023+ delay=0", sub_park_with_fund, funding, 2.0),
        ("POST 1bp + funding delay=0", split_window(df_1h, POST_LO, POST_HI), funding, 1.0),
        ("POST 1bp + funding delay=1", split_window(df_1h, POST_LO, POST_HI), funding, 1.0),
    ]:
        delay = 1 if "delay=1" in label else 0
        r = kalman_backtest(sub, z_entry=2.0, z_exit=0.5,
                              funding_df=fund_df, cost_bps_per_leg=cost_bps,
                              delay_bars=delay)
        r["label"] = label
        bt_rows.append(r)
        print(f"\n  {label}:")
        print(f"    n_bars={r['n_bars']}, n_entries={r['n_entries']}, frac_pos={r['frac_in_pos']:.2f}")
        print(f"    SR gross={r['sr_gross_ann']:+.2f}, SR net={r['sr_net_ann']:+.2f}")
        print(f"    Long-leg SR={r['sr_long_ann']:+.2f}, Short-leg SR={r['sr_short_ann']:+.2f}")
        print(f"    Total ret gross={r['total_ret_gross']*100:+.1f}%, net={r['total_ret_net']*100:+.1f}%")
        print(f"    Max DD net={r['max_dd_net']*100:+.1f}%")
        print(f"    Cost total: {r['cost_total_pct']:.2f}%, Funding total: {r['funding_total_pct']:+.2f}%")
        print(f"    Beta mean={r['mean_beta']:.3f}, std={r['std_beta']:.3f}")

    bt_df = pd.DataFrame(bt_rows)
    bt_df.to_csv(OUT / "killers34_backtest.csv", index=False)

    # ---- DSR on the claimed 2.23 ----
    print("\n" + "=" * 90)
    print("DSR on claimed Sharpe 2.23")
    print("=" * 90)
    # Park window = ~2.5 years × 24h × 365 = 21,900 hourly bars ≈ 875 trading days
    t_obs_days = 875
    for n_trials in [1, 5, 20, 50, 100]:
        d = deflated_sharpe(2.23, t_obs_days, n_trials, skew=0.0, kurt=3.0)
        print(f"  n_trials={n_trials:>3d}: SR0_thr={d['sr0']:.2f}, SR_def={d['sr_def']:+.2f}, p_real={d['p_real']:.3f}")

    # Save
    print(f"\nSaved: killer1_coint_oos.csv, killers34_backtest.csv")
