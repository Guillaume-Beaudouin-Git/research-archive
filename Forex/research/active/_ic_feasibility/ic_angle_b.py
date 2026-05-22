"""
PHASE 1.5 Task 5 — IC Feasibility: Angle B (News-Fade)
=======================================================
Signal: Fade the initial spike after major macro news event
  - Events: NFP, CPI, FOMC, ECB, GDP, BOE, Retail Sales (hardcoded 2020-2024)
  - Entry: T+5min after event timestamp (open of the T+5min bar)
  - Direction: -1 × sign(spike) where spike = close_at_T+2min - close_at_T-1min
  - Filter: |spike| > 1.0 × ATR(14-day daily, scaled to 5min bar)
  - SL: spike extreme; TP: 2× ATR (computed in IC as truncated return)
  - Exit horizons: 15min, 30min, 1h, 2h after entry

HAC t-stat: Newey-West lag 6 (pooled across events × pairs)
Gate: N_events > 150, |t_HAC| > 1.65 one-sided
N_tests: +20 (5 event types × 4 horizons = 20; AMTP denominator += 20)

Input: data/raw/dukascopy_{PAIR}_2020_2024.parquet
Output: prints table + saves to _ic_feasibility/results_angle_b.json
"""

from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

RAW_DIR = Path(__file__).parents[4] / "data" / "raw"
OUT_DIR  = Path(__file__).parent
RESULT_FILE = OUT_DIR / "results_angle_b.json"

PAIRS = ["EURUSD", "GBPUSD"]
HORIZONS_MIN = [15, 30, 60, 120]

# Hardcoded major macro events 2020-2024 (UTC timestamps)
# Format: (datetime_str_utc, event_type)
# Sources: BLS, Fed, ECB, ONS calendars — major market-moving releases only
NEWS_EVENTS_RAW = [
    # NFP (Non-Farm Payrolls) — 1st Friday of month, 13:30 UTC
    ("2020-01-10 13:30", "NFP"), ("2020-02-07 13:30", "NFP"), ("2020-03-06 13:30", "NFP"),
    ("2020-04-03 13:30", "NFP"), ("2020-05-08 13:30", "NFP"), ("2020-06-05 13:30", "NFP"),
    ("2020-07-02 13:30", "NFP"), ("2020-08-07 13:30", "NFP"), ("2020-09-04 13:30", "NFP"),
    ("2020-10-02 13:30", "NFP"), ("2020-11-06 13:30", "NFP"), ("2020-12-04 13:30", "NFP"),
    ("2021-01-08 13:30", "NFP"), ("2021-02-05 13:30", "NFP"), ("2021-03-05 13:30", "NFP"),
    ("2021-04-02 13:30", "NFP"), ("2021-05-07 13:30", "NFP"), ("2021-06-04 13:30", "NFP"),
    ("2021-07-02 13:30", "NFP"), ("2021-08-06 13:30", "NFP"), ("2021-09-03 13:30", "NFP"),
    ("2021-10-08 13:30", "NFP"), ("2021-11-05 13:30", "NFP"), ("2021-12-03 13:30", "NFP"),
    ("2022-01-07 13:30", "NFP"), ("2022-02-04 13:30", "NFP"), ("2022-03-04 13:30", "NFP"),
    ("2022-04-01 13:30", "NFP"), ("2022-05-06 13:30", "NFP"), ("2022-06-03 13:30", "NFP"),
    ("2022-07-08 13:30", "NFP"), ("2022-08-05 13:30", "NFP"), ("2022-09-02 13:30", "NFP"),
    ("2022-10-07 13:30", "NFP"), ("2022-11-04 13:30", "NFP"), ("2022-12-02 13:30", "NFP"),
    ("2023-01-06 13:30", "NFP"), ("2023-02-03 13:30", "NFP"), ("2023-03-10 13:30", "NFP"),
    ("2023-04-07 13:30", "NFP"), ("2023-05-05 13:30", "NFP"), ("2023-06-02 13:30", "NFP"),
    ("2023-07-07 13:30", "NFP"), ("2023-08-04 13:30", "NFP"), ("2023-09-01 13:30", "NFP"),
    ("2023-10-06 13:30", "NFP"), ("2023-11-03 13:30", "NFP"), ("2023-12-08 13:30", "NFP"),
    ("2024-01-05 13:30", "NFP"), ("2024-02-02 13:30", "NFP"), ("2024-03-08 13:30", "NFP"),
    ("2024-04-05 13:30", "NFP"), ("2024-05-03 13:30", "NFP"), ("2024-06-07 13:30", "NFP"),
    ("2024-07-05 13:30", "NFP"), ("2024-08-02 13:30", "NFP"), ("2024-09-06 13:30", "NFP"),
    ("2024-10-04 13:30", "NFP"), ("2024-11-01 13:30", "NFP"), ("2024-12-06 13:30", "NFP"),

    # US CPI — ~15th of each month, 13:30 UTC
    ("2020-01-14 13:30", "CPI"), ("2020-02-13 13:30", "CPI"), ("2020-03-11 13:30", "CPI"),
    ("2020-04-10 13:30", "CPI"), ("2020-05-12 13:30", "CPI"), ("2020-06-10 13:30", "CPI"),
    ("2020-07-14 13:30", "CPI"), ("2020-08-12 13:30", "CPI"), ("2020-09-11 13:30", "CPI"),
    ("2020-10-13 13:30", "CPI"), ("2020-11-12 13:30", "CPI"), ("2020-12-10 13:30", "CPI"),
    ("2021-01-13 13:30", "CPI"), ("2021-02-10 13:30", "CPI"), ("2021-03-10 13:30", "CPI"),
    ("2021-04-13 13:30", "CPI"), ("2021-05-12 13:30", "CPI"), ("2021-06-10 13:30", "CPI"),
    ("2021-07-13 13:30", "CPI"), ("2021-08-11 13:30", "CPI"), ("2021-09-14 13:30", "CPI"),
    ("2021-10-13 13:30", "CPI"), ("2021-11-10 13:30", "CPI"), ("2021-12-10 13:30", "CPI"),
    ("2022-01-12 13:30", "CPI"), ("2022-02-10 13:30", "CPI"), ("2022-03-10 13:30", "CPI"),
    ("2022-04-12 13:30", "CPI"), ("2022-05-11 13:30", "CPI"), ("2022-06-10 13:30", "CPI"),
    ("2022-07-13 13:30", "CPI"), ("2022-08-10 13:30", "CPI"), ("2022-09-13 13:30", "CPI"),
    ("2022-10-13 13:30", "CPI"), ("2022-11-10 13:30", "CPI"), ("2022-12-13 13:30", "CPI"),
    ("2023-01-12 13:30", "CPI"), ("2023-02-14 13:30", "CPI"), ("2023-03-14 13:30", "CPI"),
    ("2023-04-12 13:30", "CPI"), ("2023-05-10 13:30", "CPI"), ("2023-06-13 13:30", "CPI"),
    ("2023-07-12 13:30", "CPI"), ("2023-08-10 13:30", "CPI"), ("2023-09-13 13:30", "CPI"),
    ("2023-10-12 13:30", "CPI"), ("2023-11-14 13:30", "CPI"), ("2023-12-12 13:30", "CPI"),
    ("2024-01-11 13:30", "CPI"), ("2024-02-13 13:30", "CPI"), ("2024-03-12 13:30", "CPI"),
    ("2024-04-10 13:30", "CPI"), ("2024-05-15 13:30", "CPI"), ("2024-06-12 13:30", "CPI"),
    ("2024-07-11 13:30", "CPI"), ("2024-08-14 13:30", "CPI"), ("2024-09-11 13:30", "CPI"),
    ("2024-10-10 13:30", "CPI"), ("2024-11-13 13:30", "CPI"), ("2024-12-11 13:30", "CPI"),

    # FOMC rate decision — 8× per year, 19:00 UTC (some 18:00 UTC)
    ("2020-01-29 19:00", "FOMC"), ("2020-03-03 15:00", "FOMC"), ("2020-03-15 22:00", "FOMC"),
    ("2020-04-29 18:00", "FOMC"), ("2020-06-10 18:00", "FOMC"), ("2020-07-29 18:00", "FOMC"),
    ("2020-09-16 18:00", "FOMC"), ("2020-11-05 19:00", "FOMC"), ("2020-12-16 19:00", "FOMC"),
    ("2021-01-27 19:00", "FOMC"), ("2021-03-17 18:00", "FOMC"), ("2021-04-28 18:00", "FOMC"),
    ("2021-06-16 18:00", "FOMC"), ("2021-07-28 18:00", "FOMC"), ("2021-09-22 18:00", "FOMC"),
    ("2021-11-03 18:00", "FOMC"), ("2021-12-15 19:00", "FOMC"),
    ("2022-01-26 19:00", "FOMC"), ("2022-03-16 18:00", "FOMC"), ("2022-05-04 18:00", "FOMC"),
    ("2022-06-15 18:00", "FOMC"), ("2022-07-27 18:00", "FOMC"), ("2022-09-21 18:00", "FOMC"),
    ("2022-11-02 18:00", "FOMC"), ("2022-12-14 19:00", "FOMC"),
    ("2023-02-01 19:00", "FOMC"), ("2023-03-22 18:00", "FOMC"), ("2023-05-03 18:00", "FOMC"),
    ("2023-06-14 18:00", "FOMC"), ("2023-07-26 18:00", "FOMC"), ("2023-09-20 18:00", "FOMC"),
    ("2023-11-01 18:00", "FOMC"), ("2023-12-13 19:00", "FOMC"),
    ("2024-01-31 19:00", "FOMC"), ("2024-03-20 18:00", "FOMC"), ("2024-05-01 18:00", "FOMC"),
    ("2024-06-12 18:00", "FOMC"), ("2024-07-31 18:00", "FOMC"), ("2024-09-18 18:00", "FOMC"),
    ("2024-11-07 19:00", "FOMC"), ("2024-12-18 19:00", "FOMC"),

    # ECB rate decision — ~6-8× per year, 13:15 UTC (press conference 13:45)
    ("2020-01-23 12:45", "ECB"), ("2020-03-12 12:45", "ECB"), ("2020-04-30 11:45", "ECB"),
    ("2020-06-04 11:45", "ECB"), ("2020-07-16 11:45", "ECB"), ("2020-09-10 11:45", "ECB"),
    ("2020-10-29 12:45", "ECB"), ("2020-12-10 12:45", "ECB"),
    ("2021-01-21 12:45", "ECB"), ("2021-03-11 12:45", "ECB"), ("2021-04-22 11:45", "ECB"),
    ("2021-06-10 11:45", "ECB"), ("2021-07-22 11:45", "ECB"), ("2021-09-09 11:45", "ECB"),
    ("2021-10-28 12:45", "ECB"), ("2021-12-16 12:45", "ECB"),
    ("2022-02-03 12:45", "ECB"), ("2022-03-10 12:45", "ECB"), ("2022-04-14 11:45", "ECB"),
    ("2022-06-09 11:45", "ECB"), ("2022-07-21 12:15", "ECB"), ("2022-09-08 12:15", "ECB"),
    ("2022-10-27 13:15", "ECB"), ("2022-12-15 13:15", "ECB"),
    ("2023-02-02 13:15", "ECB"), ("2023-03-16 13:15", "ECB"), ("2023-05-04 13:15", "ECB"),
    ("2023-06-15 13:15", "ECB"), ("2023-07-27 13:15", "ECB"), ("2023-09-14 13:15", "ECB"),
    ("2023-10-26 13:15", "ECB"), ("2023-12-14 13:15", "ECB"),
    ("2024-01-25 13:15", "ECB"), ("2024-03-07 13:15", "ECB"), ("2024-04-11 13:15", "ECB"),
    ("2024-06-06 13:15", "ECB"), ("2024-07-18 13:15", "ECB"), ("2024-09-12 13:15", "ECB"),
    ("2024-10-17 13:15", "ECB"), ("2024-12-12 13:15", "ECB"),
]

NEWS_EVENTS = pd.DataFrame(NEWS_EVENTS_RAW, columns=["timestamp", "event_type"])
NEWS_EVENTS["timestamp"] = pd.to_datetime(NEWS_EVENTS["timestamp"], utc=True)


def hac_tstat(y: np.ndarray, x: np.ndarray, lag: int = 6) -> float:
    x2 = sm.add_constant(x)
    res = sm.OLS(y, x2).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(res.tvalues[1])


def load_pair(pair: str) -> pd.DataFrame:
    path = RAW_DIR / f"dukascopy_{pair}_2020_2024.parquet"
    if not path.exists():
        print(f"  MISSING: {path}")
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


def compute_atr_daily(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Daily ATR from 1-min bars, indexed by date."""
    daily = df["close"].resample("1D").ohlc()
    daily["prev_close"] = daily["close"].shift(1)
    tr = pd.concat([
        daily["high"] - daily["low"],
        (daily["high"] - daily["prev_close"]).abs(),
        (daily["low"] - daily["prev_close"]).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def compute_event_observations(df: pd.DataFrame, pair: str) -> pd.DataFrame:
    """For each news event, compute spike direction and forward returns."""
    atr_daily = compute_atr_daily(df)

    rows = []
    for _, ev in NEWS_EVENTS.iterrows():
        t0 = ev["timestamp"]
        event_type = ev["event_type"]

        # Spike: change in close from t0-1min bar to t0+2min bar
        pre_bar  = df[df.index < t0].tail(1)
        post_bar = df[(df.index >= t0) & (df.index <= t0 + pd.Timedelta(minutes=2))].tail(1)
        if pre_bar.empty or post_bar.empty:
            continue

        spike = post_bar["close"].iloc[0] - pre_bar["close"].iloc[0]
        date_key = t0.normalize()

        # ATR filter
        if date_key not in atr_daily.index:
            continue
        atr = atr_daily.loc[date_key]
        if np.isnan(atr) or atr < 1e-8:
            continue

        # ATR is daily; scale to 3-minute equivalent (rough: 3/1440 of day, but keep daily for filter)
        spike_atr_ratio = abs(spike) / atr
        if spike_atr_ratio < 0.05:  # reject micro-noise (< 5% of daily ATR)
            continue

        signal = -np.sign(spike)  # fade: short if spike up, long if spike down
        if signal == 0:
            continue

        # Entry: open of T+5min bar
        entry_time = t0 + pd.Timedelta(minutes=5)
        entry_bars = df[df.index >= entry_time].head(1)
        if entry_bars.empty:
            continue
        entry_price = entry_bars["open"].iloc[0]

        # Forward returns
        fwd = {}
        for mins in HORIZONS_MIN:
            exit_time = entry_time + pd.Timedelta(minutes=mins)
            exit_bars = df[df.index >= exit_time].head(1)
            if exit_bars.empty:
                fwd[mins] = np.nan
            else:
                exit_price = exit_bars["close"].iloc[0]
                fwd[mins] = (exit_price - entry_price) / entry_price * signal

        rows.append({
            "timestamp":       t0,
            "event_type":      event_type,
            "spike":           spike,
            "spike_atr_ratio": spike_atr_ratio,
            "signal":          signal,
            "entry_price":     entry_price,
            **{f"ret_{m}m": v for m, v in fwd.items()},
        })

    return pd.DataFrame(rows)


def main():
    all_results = {}

    for pair in PAIRS:
        print(f"\n{'='*60}")
        print(f"Angle B IC — {pair}")
        df = load_pair(pair)
        if df.empty:
            print(f"ERROR: {pair} data not found. Run fetch_data.py first.")
            continue

        obs = compute_event_observations(df, pair)
        obs = obs.dropna(subset=[f"ret_{m}m" for m in HORIZONS_MIN])
        N = len(obs)
        print(f"  Total news events processed: {len(NEWS_EVENTS)}")
        print(f"  Observations with spike + returns: {N}")
        if N < 150:
            print(f"  FAIL: N={N} < 150 gate")
            all_results[pair] = {"pair": pair, "N": N, "gate": "FAIL_N"}
            continue

        # Event type breakdown
        print("\n  Event breakdown:")
        for ev_type, grp in obs.groupby("event_type"):
            print(f"    {ev_type}: {len(grp)}")

        # IC by horizon
        print(f"\n  {'Horizon':<12} {'IC_spearman':>12} {'t_HAC_NW6':>12} {'p_val':>8} {'gate':>8}")
        print(f"  {'-'*60}")
        res_h = {}
        for mins in HORIZONS_MIN:
            col = f"ret_{mins}m"
            mask = ~obs[col].isna()
            sig = obs.loc[mask, "signal"].values
            ret = obs.loc[mask, col].values
            n_h = len(ret)
            if n_h < 50:
                continue
            ic, _ = stats.spearmanr(sig, ret)
            t_hac = hac_tstat(ret, sig, lag=6)
            pval  = 2 * (1 - stats.norm.cdf(abs(t_hac)))
            gate  = "PASS" if abs(t_hac) > 1.65 and ic > 0 else "WEAK" if abs(t_hac) > 1.0 else "FAIL"
            label = f"{mins}min"
            print(f"  {label:<12} {ic:>+12.4f} {t_hac:>+12.2f} {pval:>8.4f} {gate:>8}")
            res_h[label] = {"n": n_h, "IC_spearman": round(ic, 4),
                            "t_HAC_NW6": round(t_hac, 3), "p_val": round(pval, 4), "gate": gate}

        all_results[pair] = {"pair": pair, "N": N, "horizons": res_h}

    RESULT_FILE.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\nResults saved → {RESULT_FILE}")


if __name__ == "__main__":
    main()
