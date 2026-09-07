"""Shared helpers for the fx_events_2026-09 event-study.

Signal T-1 / trade T is not directly applicable to an event study (there is no
signal to lag — event timestamps are known ex ante by construction, that is the
whole point of a calendar effect). What DOES apply: all price observations used
to mark an "entry" at horizon h must be observable AT OR BEFORE T+h (asof, never
look-ahead within the horizon bucket).
"""
import numpy as np
import pandas as pd

CACHE_DIR = "<SCRATCH>"

# currency -> list of (pair, sign) where sign=+1 if currency is the BASE of the
# pair (pair return = currency return) and sign=-1 if currency is the QUOTE
# (currency strength = -1 * pair return).
CCY_PAIRS = {
    "USD": [("EURUSD", -1), ("GBPUSD", -1), ("USDJPY", +1), ("USDCAD", +1), ("USDCHF", +1), ("AUDUSD", -1), ("NZDUSD", -1)],
    "EUR": [("EURUSD", +1), ("EURJPY", +1), ("EURGBP", +1)],
    "GBP": [("GBPUSD", +1), ("EURGBP", -1), ("GBPJPY", +1)],
    "JPY": [("USDJPY", -1), ("EURJPY", -1), ("AUDJPY", -1), ("GBPJPY", -1)],
    "AUD": [("AUDUSD", +1), ("AUDJPY", +1)],
    "CAD": [("USDCAD", -1)],
    "CHF": [("USDCHF", -1)],
    "NZD": [("NZDUSD", +1)],
}

ALL_PAIRS = sorted({p for pairs in CCY_PAIRS.values() for p, _ in pairs})

_series_cache = {}


def load_pair(pair):
    if pair not in _series_cache:
        df = pd.read_parquet(f"{CACHE_DIR}/{pair}_M1.parquet", columns=["close"])
        idx_ns = df.index.values.astype("int64")
        close = df["close"].values.astype("float64")
        _series_cache[pair] = (idx_ns, close)
    return _series_cache[pair]


def asof_prices(idx_ns, close, target_ns):
    """Vectorized asof lookup: for each target_ns, return close at the last bar
    with timestamp <= target_ns. NaN if before series start or after end (with
    a 6h stale-tolerance cutoff to avoid weekend-gap artifacts)."""
    pos = np.searchsorted(idx_ns, target_ns, side="right") - 1
    out = np.full(target_ns.shape, np.nan)
    valid = pos >= 0
    out_valid = np.zeros(target_ns.shape, dtype=bool)
    pos_c = np.clip(pos, 0, len(idx_ns) - 1)
    stale_ns = target_ns - idx_ns[pos_c]
    ok = valid & (stale_ns <= 6 * 3600 * 1_000_000_000) & (stale_ns >= 0)
    out[ok] = close[pos_c[ok]]
    return out


def extract_event_matrix(pair, event_times_utc, offsets_min):
    """event_times_utc: pd.DatetimeIndex (UTC). offsets_min: array of minute
    offsets (can be negative). Returns (n_events, n_offsets) price matrix."""
    idx_ns, close = load_pair(pair)
    ev_ns = event_times_utc.values.astype("int64")
    offs_ns = (np.asarray(offsets_min, dtype="int64") * 60_000_000_000)
    target = ev_ns[:, None] + offs_ns[None, :]
    mat = asof_prices(idx_ns, close, target.reshape(-1))
    return mat.reshape(target.shape)


def hac_tstat(x, lag=6):
    """Newey-West HAC t-stat for the mean of x being 0, via OLS on a constant."""
    import statsmodels.api as sm
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return np.nan, np.nan, n
    X = np.ones((n, 1))
    model = sm.OLS(x, X).fit(cov_type="HAC", cov_kwds={"maxlags": min(lag, n - 2)})
    return float(model.params[0]), float(model.tvalues[0]), n


def block_bootstrap_mean(x, n_boot=3000, block=5, seed=0):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 5:
        return np.array([np.nan])
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    means = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, max(n - block, 1), size=n_blocks)
        sample = np.concatenate([x[s:s + block] for s in starts])[:n]
        means[b] = sample.mean()
    return means


POOL_START = pd.Timestamp("2018-01-01", tz="UTC")
POOL_END = pd.Timestamp("2026-06-04", tz="UTC")


def build_placebo_times(event_times_utc, ccy, all_family_event_times_utc=None,
                         n_placebo=5, blackout_days=2, proxy_dir=None, seed=0,
                         pool_start=POOL_START, pool_end=POOL_END):
    """For each real event time, pick n_placebo non-event trading days whose
    trailing 5-day realized-vol (of the currency proxy) is closest to the
    event day's, excluding any day within `blackout_days` of ANY event in the
    family (so the placebo pool cannot itself straddle an event; L58: this
    also prevents a blackout-induced seasonality bias since we only exclude
    real event days themselves, not a broad calendar window).

    Returns (placebo_times: DatetimeIndex, source_idx: np.ndarray) where
    source_idx[i] is the index into event_times_utc that placebo_times[i]
    was matched against.
    """
    import os
    if proxy_dir is None:
        proxy_dir = os.path.join(os.path.dirname(__file__), "cache")
    proxy = pd.read_csv(f"{proxy_dir}/proxy_{ccy}.csv", parse_dates=["timestamp_utc"])
    proxy = proxy.dropna(subset=["vol5"]).reset_index(drop=True)
    proxy_dates = proxy["timestamp_utc"].dt.normalize()
    proxy_vol = proxy["vol5"].values

    if all_family_event_times_utc is None:
        all_family_event_times_utc = event_times_utc
    blackout_dates = set()
    for t in pd.DatetimeIndex(all_family_event_times_utc).normalize():
        for d in range(-blackout_days, blackout_days + 1):
            blackout_dates.add(t + pd.Timedelta(days=d))

    pool_mask = ~proxy_dates.isin(blackout_dates)
    if pool_start is not None:
        pool_mask &= (proxy_dates >= pool_start) & (proxy_dates <= pool_end)
    pool_dates = proxy_dates[pool_mask].values
    pool_vol = proxy_vol[pool_mask.values]
    pool_ts = proxy["timestamp_utc"].values[pool_mask.values]

    rng = np.random.default_rng(seed)
    placebo_times = []
    source_idx = []
    for i, t in enumerate(event_times_utc):
        t_date = pd.Timestamp(t).normalize()
        idx_loc = np.searchsorted(proxy_dates.values, np.datetime64(t_date))
        target_vol = proxy_vol[idx_loc - 1] if 0 < idx_loc <= len(proxy_vol) else np.nan
        if np.isnan(target_vol):
            continue
        dist = np.abs(pool_vol - target_vol)
        order = np.argsort(dist)
        # avoid exact same date as the real event, take next n_placebo distinct days
        picked = 0
        for o in order:
            cand_date = pd.Timestamp(pool_dates[o])
            if cand_date == t_date:
                continue
            hh, mm, ss = t.hour, t.minute, t.second
            placebo_times.append(cand_date + pd.Timedelta(hours=hh, minutes=mm, seconds=ss))
            source_idx.append(i)
            picked += 1
            if picked >= n_placebo:
                break
    placebo_times = pd.DatetimeIndex(placebo_times).tz_localize("UTC") if len(placebo_times) and placebo_times[0].tzinfo is None else pd.DatetimeIndex(placebo_times)
    return placebo_times, np.array(source_idx)


# Fine near-event resolution (1-min steps out to 10min, then coarsening) so
# genuinely fast decays (seconds-minutes, per the rate-decision hypothesis) are
# NOT aliased against the same half-life as slower ones by an overly coarse grid.
BUCKET_EDGES_MIN = [-120, -60, -30, -15, -5, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8,
                     9, 10, 12, 15, 20, 25, 30, 45, 60, 90, 120, 180, 240, 360,
                     480, 720, 1080, 1440, 2160, 2880, 3600, 4320]


_activity_cumsum_cache = {}


def _cumsum_sq_logret(pair):
    if pair not in _activity_cumsum_cache:
        idx_ns, close = load_pair(pair)
        logp = np.log(close)
        logret = np.diff(logp, prepend=logp[0])
        logret[0] = 0.0
        sq = logret ** 2
        S = np.concatenate([[0.0], np.cumsum(sq)])  # S[i] = sum_{k<i} sq[k]
        _activity_cumsum_cache[pair] = (idx_ns, S)
    return _activity_cumsum_cache[pair]


def bucket_realized_activity(pair, event_times_utc, edges_min=BUCKET_EDGES_MIN):
    """Realized activity (sqrt sum of squared 1-min log returns, in bps) in
    each [edges[b], edges[b+1]) minute-offset bucket relative to each event.
    Vectorized via a cumulative-sum-of-squared-returns trick (no python loop
    over events/buckets)."""
    idx_ns, S = _cumsum_sq_logret(pair)
    ev_ns = pd.DatetimeIndex(event_times_utc).values.astype("int64")
    edges_ns = np.asarray(edges_min, dtype="int64") * 60_000_000_000
    targets = ev_ns[:, None] + edges_ns[None, :]
    pos = np.searchsorted(idx_ns, targets.reshape(-1), side="left").reshape(targets.shape)
    pos = np.clip(pos, 0, len(idx_ns))
    S_at_pos = S[pos]
    bucket_sums = np.clip(S_at_pos[:, 1:] - S_at_pos[:, :-1], 0, None)
    # mark buckets that fall entirely outside available data as NaN (stale guard:
    # if the bucket's right edge maps to the very first or very last bar, data is missing)
    right_pos = pos[:, 1:]
    left_pos = pos[:, :-1]
    missing = (right_pos == left_pos) & (right_pos == 0)
    out = np.sqrt(bucket_sums) * 10000.0
    out[missing] = np.nan
    return out


def mde(sigma, n, alpha=0.05, power=0.80):
    from scipy.stats import norm
    z_a = norm.ppf(1 - alpha / 2)
    z_b = norm.ppf(power)
    return (z_a + z_b) * sigma / np.sqrt(n)
