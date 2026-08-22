"""
Data loader for the newly-fetched Asia/EU indices (JP225/HK50/AUS200[/UK100/FRA40]),
M5 Dukascopy cache -> resampled to 15-min, session window derived EMPIRICALLY from the data's
own tick-count profile (L52/L56 discipline: never assume a clock). Small sample (1-2 years,
whatever `fetch_new_indices.py` managed to pull within this session's time budget) -- reported
as a feasibility read, not a full-history verdict (PREREGISTRATION.md §1/§6).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DUKA = HERE / "_cache" / "dukascopy_m5"
CACHE15 = HERE / "_cache"

DIGITS = {"JP225": 0, "HK50": 0, "AUS200": 1, "UK100": 1, "FRA40": 1}

# Provisional cost: no direct spread measurement exists (the Dukascopy fetch only kept
# ask/bid MIDPOINT per M5 bar -- see fetch_new_indices.py::_ticks_to_m5 -- not the spread
# itself). Rather than borrow GER40's 1.017bps (a European index, likely too tight for Asia CFDs
# per retail-broker quotes), this uses a WebSearch cross-check of typical retail CFD spreads,
# converted to bps at each index's own price level (2026-08-21 search, brokerchooser.com/
# teletrade.org): JP225 ~8.5pts/~40,000 level = 2.1bps; HK50 ~7.6pts/~25,700 level = 3.0bps;
# AUS200 no direct quote found, averaged with JP225/HK50 = 2.5bps (flagged as the weakest link
# in this chain). UK100/FRA40 use the GER40 point (1.5bps, mid-way, no direct quote either).
COST_RT_BPS_PROXY = {"JP225": 2.1, "HK50": 3.0, "AUS200": 2.5, "UK100": 1.5, "FRA40": 1.5}
COST_PROVENANCE = "PROXY, NOT measured from this study's own data (Dukascopy fetch kept only " \
                 "the M5 mid-price, not spread): WebSearch cross-check of retail CFD broker " \
                 "quotes, 2026-08-21, converted to bps at each index's price level. Weaker " \
                 "provenance than the deep_history_utc-measured costs elsewhere in this study."



# ---------------------------------------------------------------- L52/L56 clock bug, found and fixed
#
# `fetch_new_indices.py` (this study's own fetcher, copying the URL/bi5-decode protocol read-only
# from `Forex/data/dukascopy_downloader_m5.py`) anchors each fetch-day's 24 hourly tick buckets on
# PARIS-LOCAL midnight (`CET = ZoneInfo("Europe/Paris")`, DST-aware), then adds `hour * 3.6e6 ms`
# in absolute time and stores the result AS IF it were plain UTC. This is only correct if
# Dukascopy's own bi5 hour-folders are indexed by Paris-local hour. A direct falsification test
# (exactly the L56 method: split the fetched year at the EU DST transition and check whether the
# hourly liquidity profile's PEAK HOUR is stable across the split) proves they are not:
#
#   BEFORE fix: winter (Jan-Mar) peak hour = 23 UTC-as-labeled; summer (Apr-Jun) peak hour = 22
#   -- a clean 1-hour seasonal SHIFT, shape correlation winter-vs-summer = 0.32 (weak) -- the
#   same diagnostic signature L56 used to catch the EET-mislabeled overnight gold/silver window.
#   AFTER fix (below): both seasons peak at hour 0 UTC, shape correlation = 0.83.
#
# Conclusion: Dukascopy's bi5 hour-folders are UTC-indexed, not Paris-local, and the inherited
# construction (from the pre-existing, presumably-unvalidated `Forex/data/dukascopy_downloader_m5.py`
# protocol) mislabels every bar EARLIER than true UTC by exactly the Paris/UTC offset of that
# fetch-day: 1h before the 2024-03-31 01:00 UTC transition, 2h from it onward. Fixed here by
# adding that offset back. Precision note: the correction is applied by the CORRECTED-clock date
# relative to the transition instant (conservative boundary at 2024-03-30 23:00 UTC in
# pre-correction-clock terms) -- this can misclassify at most the handful of bars within the ~1-2h
# window immediately around the single transition instant (one day out of 130), immaterial to a
# session-level or full-sample statistic. This bug most likely also affects
# `Forex/data/dukascopy_downloader_m5.py`'s own cached output (not modified or re-validated here --
# out of scope, flagged for a future session; this study's fix only touches its own `_cache/`).
_DST_2024_UTC = pd.Timestamp("2024-03-30 23:00:00", tz="UTC")  # conservative pre-transition boundary


def _fix_paris_anchor_bug(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index
    correction = pd.Series(pd.Timedelta(hours=1), index=idx)
    correction[idx >= _DST_2024_UTC] = pd.Timedelta(hours=2)
    out = df.copy()
    out.index = df.index + correction
    return out.sort_index()


def load_m5_years(sym: str, years: list[int]) -> pd.DataFrame:
    frames = []
    for y in years:
        pq = DUKA / f"{sym}_{y}_M5.parquet"
        if pq.exists():
            frames.append(pd.read_parquet(pq))
    if not frames:
        raise FileNotFoundError(f"No cached Dukascopy M5 data for {sym} in years {years}")
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = _fix_paris_anchor_bug(df)  # L52/L56 fix -- see block comment above
    return df


def hourly_profile(df5: pd.DataFrame) -> pd.Series:
    return df5.groupby(df5.index.hour)["tick_count"].sum().sort_index()


def infer_session(df5: pd.DataFrame, target_frac: float = 0.85) -> tuple[str, str]:
    """Smallest contiguous (wraparound-aware) block of UTC hours capturing >= target_frac of
    total tick volume -- an empirical session window, not an assumed one."""
    prof = hourly_profile(df5)
    hours = prof.index.to_numpy()
    vals = prof.reindex(range(24), fill_value=0).to_numpy()
    total = vals.sum()
    best = None
    for start in range(24):
        cum = 0
        for length in range(1, 25):
            idxs = [(start + k) % 24 for k in range(length)]
            cum = vals[idxs].sum()
            if cum >= target_frac * total:
                if best is None or length < best[0]:
                    best = (length, start)
                break
    length, start = best
    end = (start + length) % 24
    return f"{start:02d}:00", f"{end:02d}:00"


def build_15min(sym: str, years: list[int], force: bool = False,
                session: tuple[str, str] | None = None, tag: str = "") -> tuple[pd.DataFrame, tuple]:
    """`session=None` -> empirically inferred (85%-of-volume contiguous block, `infer_session`).
    `session=(start,end)` -> explicit override (used to compare candidate windows on a
    genuinely bimodal instrument -- see RAPPORT.md §1.3 for why JP225 needs this)."""
    out = CACHE15 / f"{sym}_15min_new{tag}.parquet"
    if out.exists() and not force:
        df = pd.read_parquet(out)
        sess = (str(df.attrs.get("sess_start", "NA")), str(df.attrs.get("sess_end", "NA")))
        return df, sess
    df5 = load_m5_years(sym, years)
    st, en = session if session is not None else infer_session(df5)
    agg = (df5.resample("15min")
             .agg({"open": "first", "high": "max", "low": "min", "close": "last",
                   "tick_count": "sum"})
             .dropna(subset=["open", "high", "low", "close"]))
    t = agg.index.time
    s_t = pd.Timestamp(st).time(); e_t = pd.Timestamp(en).time()
    if s_t < e_t:
        mask = (t >= s_t) & (t < e_t)
    else:  # wraps midnight UTC
        mask = (t >= s_t) | (t < e_t)
    agg = agg[mask].copy()
    agg = agg.rename(columns={"tick_count": "tick_volume"})
    agg["session_date"] = agg.index.normalize()
    agg.attrs["sess_start"] = st; agg.attrs["sess_end"] = en
    agg.to_parquet(out)
    return agg, (st, en)


if __name__ == "__main__":
    for sym in ("JP225", "HK50", "AUS200"):
        try:
            df5 = load_m5_years(sym, [2024])
        except FileNotFoundError as e:
            print(sym, "NOT YET AVAILABLE:", e)
            continue
        st, en = infer_session(df5)
        df15, _ = build_15min(sym, [2024], force=True)
        bpd = df15.groupby("session_date").size()
        print(f"{sym}: M5 rows={len(df5)}  session=[{st},{en})  15min bars={len(df15)}  "
              f"bars/day median={bpd.median()}  from={df15.index.min()} to={df15.index.max()}")
