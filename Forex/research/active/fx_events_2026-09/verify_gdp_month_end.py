"""Critical robustness check on the GDP-USD pre-drift candidate: ALL 33 events
fall on day-of-month 20-30 (median 28) -- i.e. GDP Advance releases are, by
construction of the US statistical calendar, always in the LAST WEEK of the
month. This repo has extensive prior evidence of a genuine month-end FX/bond
flow effect (L51-L55, month_end_vehicle_2026-07) that has NOTHING to do with
any specific data release. The generic build_placebo_times() placebo (vol-
matched, same hour, ANY non-blackout day) does NOT control for day-of-month,
so it could produce a spurious "GDP effect" that is really just "late month".

This script builds a day-of-month-matched placebo (pool restricted to trading
days with day-of-month in the same range as the real GDP events, still vol-
matched and blackout-excluded) and re-tests the -60/-120min pre-drift.
"""
import numpy as np
import pandas as pd
from lib import CCY_PAIRS, extract_event_matrix, hac_tstat, block_bootstrap_mean

ev = pd.read_csv("events/gdp_USD.csv", parse_dates=["datetime_utc"])
event_times = pd.DatetimeIndex(pd.to_datetime(ev["datetime_utc"], utc=True))
pairs = CCY_PAIRS["USD"]

proxy = pd.read_csv("cache/proxy_USD.csv", parse_dates=["timestamp_utc"]).dropna(subset=["vol5"]).reset_index(drop=True)
proxy_dates = proxy["timestamp_utc"].dt.normalize()
proxy_dom = proxy["timestamp_utc"].dt.day
proxy_vol = proxy["vol5"].values

POOL_START = pd.Timestamp("2018-01-01", tz="UTC")
POOL_END = pd.Timestamp("2026-06-04", tz="UTC")

blackout = set()
for t in pd.DatetimeIndex(event_times).normalize():
    for d in range(-2, 3):
        blackout.add(t + pd.Timedelta(days=d))

dom_ok = (proxy_dom >= 20) & (proxy_dom <= 30)
in_range = (proxy_dates >= POOL_START) & (proxy_dates <= POOL_END)
not_blackout = ~proxy_dates.isin(blackout)
pool_mask = (dom_ok & in_range & not_blackout).values

pool_dates = proxy["timestamp_utc"].values[pool_mask]
pool_vol = proxy_vol[pool_mask]
print(f"day-of-month-matched pool size: {pool_mask.sum()} trading days (day-of-month 20-30, excluding blackout)")

n_placebo = 8
placebo_times = []
src_idx = []
for i, t in enumerate(event_times):
    t_date = pd.Timestamp(t).normalize()
    idx_loc = np.searchsorted(proxy_dates.values.astype("datetime64[ns]"), np.datetime64(t_date.tz_localize(None)))
    target_vol = proxy_vol[idx_loc - 1] if 0 < idx_loc <= len(proxy_vol) else np.nan
    dist = np.abs(pool_vol - target_vol)
    order = np.argsort(dist)
    picked = 0
    for o in order:
        cand_date = pd.Timestamp(pool_dates[o])
        if cand_date.normalize() == t_date:
            continue
        placebo_times.append(cand_date.normalize() + pd.Timedelta(hours=t.hour, minutes=t.minute, seconds=t.second))
        src_idx.append(i)
        picked += 1
        if picked >= n_placebo:
            break
placebo_times = pd.DatetimeIndex(placebo_times)
print(f"placebo events built: {len(placebo_times)}")


def pre_drift(times, window_min):
    offsets = [window_min, 0]
    acc = np.zeros(len(times))
    for pair, sign in pairs:
        mat = extract_event_matrix(pair, times, offsets)
        d = (np.log(mat[:, 1]) - np.log(mat[:, 0])) * sign * 10000.0
        acc += d
    return acc / len(pairs)


print("\n=== Day-of-month-MATCHED placebo (controls for month-end) ===")
for w in [-30, -60, -120, -240, -1440]:
    real = pre_drift(event_times, w)
    placebo = pre_drift(placebo_times, w)
    mean_real, t_real, n_real = hac_tstat(real)
    mean_placebo, t_placebo, n_placebo_ = hac_tstat(placebo)
    diff = mean_real - mean_placebo
    rng = np.random.default_rng(42)
    boot_means = np.array([np.nanmean(rng.choice(placebo[~np.isnan(placebo)], size=n_real, replace=True)) for _ in range(3000)])
    pct = float((boot_means < mean_real).mean())
    print(f"w={w:>5d}min  real_mean={mean_real:7.2f}bps t={t_real:5.2f} (n={n_real})  |  "
          f"DoM-placebo_mean={mean_placebo:7.2f}bps t={t_placebo:5.2f}  |  diff={diff:7.2f}bps  pctl={pct:.3f}")

print("\n=== For reference: generic (non-DoM-matched) placebo mean at same windows ===")
import lib
generic_placebo, _ = lib.build_placebo_times(event_times, "USD", event_times, n_placebo=8)
for w in [-30, -60, -120, -240, -1440]:
    p = pre_drift(generic_placebo, w)
    print(f"w={w:>5d}min  generic_placebo_mean={np.nanmean(p):7.2f}bps")
