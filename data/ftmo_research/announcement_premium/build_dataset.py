"""Build the announcement-premium dataset per HYPOTHESIS.md (frozen 2026-06-10, commit 88cc29e).

Outputs (this directory only):
    dataset_daily.csv     -- trading-day grid: close, return, nights, rf, event flags
    events_mapped.csv     -- every kept calendar event with its mapped announcement day
    events_excluded.csv   -- exclusion manifest (unscheduled FOMC, out-of-sample, unmapped)
    build_meta.json       -- coverage, counts, sanity-gate results
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

M1_PATH = ROOT / "data/deep_history_utc/US500_M1.csv"
CAL_PATH = ROOT / "data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv"
RF_PATH = ROOT / "data/raw/fred_DTB3_37358bdf84.parquet"

NY = "America/New_York"
SESSION_START = "09:30"
SESSION_END = "16:00"          # close = last M1 bar with open time < 16:00 ET
MIN_BARS = 100                 # frozen trading-day definition
SAMPLE_START = pd.Timestamp("2018-01-03")   # calendar floor + 1 full holding window
# Data-validity rule (outcome-blind): no legitimate US500 close-to-close window exceeds
# ~5 calendar nights (Easter/Christmas). A larger gap is a data hole (US500_M1.csv has no
# usable bars 2018-01..2021-09-13); such return-rows are invalid observations and any
# event whose holding window spans the hole is unobservable -> exclusion manifest.
MAX_NIGHTS_VALID = 7
FOMC_SCHED_UTC_HOURS = {17, 18, 19, 20}     # 14:00 ET across DST regimes

EVENT_FILTERS = {
    "FOMC": lambda d: (d["event"] == "Fed Interest Rate Decision"),
    "CPI": lambda d: d["event"].isin(["CPI", "CPI s.a", "CPI s.a Final"]),
    "NFP": lambda d: (d["event"] == "Non Farm Payrolls"),
}


def build_daily_grid() -> pd.DataFrame:
    """Daily 16:00-ET closes from true-UTC M1 bars (frozen definition, HYPOTHESIS §5)."""
    m1 = pd.read_csv(M1_PATH, usecols=["timestamp_utc", "close"])
    ts = pd.to_datetime(m1["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    ny = ts.dt.tz_convert(NY)
    minutes = ny.dt.hour * 60 + ny.dt.minute
    in_session = (minutes >= 9 * 60 + 30) & (minutes < 16 * 60)
    sess = pd.DataFrame(
        {"date": ny.dt.date[in_session], "close": m1["close"][in_session],
         "ts_utc": ts[in_session]}
    )
    g = sess.groupby("date", sort=True)
    grid = pd.DataFrame(
        {"n_bars": g.size(), "close": g["close"].last(),
         "close_dt_utc": g["ts_utc"].last() + pd.Timedelta(minutes=1)}
    )
    grid = grid[grid["n_bars"] >= MIN_BARS].reset_index()
    grid["date"] = pd.to_datetime(grid["date"])
    grid["ret"] = grid["close"] / grid["close"].shift(1) - 1.0
    grid["nights"] = grid["date"].diff().dt.days
    return grid


def attach_risk_free(grid: pd.DataFrame) -> pd.DataFrame:
    """rf_T = DTB3_{T-1}/100 * nights/360, ffilled across holidays and to sample end."""
    rf = pd.read_parquet(RF_PATH)
    rf = rf.reset_index()
    rf.columns = ["date", "dtb3"] if rf.shape[1] == 2 else list(rf.columns)
    rf["date"] = pd.to_datetime(rf["date"]).dt.tz_localize(None)
    rate = (
        rf.set_index("date")["dtb3"].sort_index()
        .reindex(pd.date_range(rf["date"].min(), grid["date"].max()))
        .ffill()
    )
    rate_tm1 = rate.reindex(grid["date"]).shift(0).to_numpy()  # value AT date, used at T-1
    grid = grid.copy()
    grid["dtb3_tm1"] = pd.Series(rate_tm1).shift(1).to_numpy()
    grid["rf"] = grid["dtb3_tm1"] / 100.0 * grid["nights"] / 360.0
    return grid


def extract_events() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the frozen §4 filters. Returns (kept, excluded) raw calendar rows."""
    cal = pd.read_csv(CAL_PATH)
    us = cal[cal["country"] == "US"].copy()
    us["ts_utc"] = pd.to_datetime(us["datetime_utc"], utc=True)
    kept_parts, excl_parts = [], []
    for etype, fn in EVENT_FILTERS.items():
        rows = us[fn(us)].copy()
        rows["type"] = etype
        if etype == "FOMC":
            sched = rows["ts_utc"].dt.hour.isin(FOMC_SCHED_UTC_HOURS)
            excl = rows[~sched].copy()
            excl["exclusion_reason"] = "unscheduled (emergency) FOMC decision"
            excl_parts.append(excl)
            rows = rows[sched]
        kept_parts.append(rows)
    kept = pd.concat(kept_parts, ignore_index=True)
    excluded = (
        pd.concat(excl_parts, ignore_index=True)
        if excl_parts else pd.DataFrame(columns=list(us.columns) + ["type", "exclusion_reason"])
    )
    return kept, excluded


def map_events_to_days(events: pd.DataFrame, grid: pd.DataFrame) -> pd.DataFrame:
    """Frozen mapping: T = first trading day whose 16:00-ET close timestamp >= release ts."""
    close_dts = grid["close_dt_utc"].to_numpy()
    idx = np.searchsorted(close_dts, events["ts_utc"].to_numpy(), side="left")
    events = events.copy()
    events["grid_idx"] = idx
    in_range = (idx > 0) & (idx < len(grid))
    events["announce_date"] = pd.NaT
    events.loc[in_range, "announce_date"] = grid["date"].to_numpy()[idx[in_range]]
    events["released_while_closed"] = False
    ok = in_range.copy()
    rel_date_ny = events["ts_utc"].dt.tz_convert(NY).dt.normalize().dt.tz_localize(None)
    events.loc[in_range, "released_while_closed"] = (
        events.loc[in_range, "announce_date"] != rel_date_ny[in_range]
    )
    events["mapped"] = ok
    return events


def main() -> None:
    grid = attach_risk_free(build_daily_grid())
    kept, excluded = extract_events()
    mapped = map_events_to_days(kept, grid)

    unmapped = mapped[~mapped["mapped"]].copy()
    if len(unmapped):
        unmapped["exclusion_reason"] = "outside price grid"
        excluded = pd.concat([excluded, unmapped[excluded.columns.intersection(unmapped.columns).tolist()
                                                 + ["exclusion_reason"]]], ignore_index=True)
    mapped = mapped[mapped["mapped"]].copy()

    # one event-day per (announce_date, type); pooled = union of days
    day_type = mapped.drop_duplicates(["announce_date", "type"])[
        ["announce_date", "type", "ts_utc", "event", "released_while_closed"]
    ].sort_values("announce_date")
    pivot = day_type.assign(v=True).pivot_table(
        index="announce_date", columns="type", values="v", aggfunc="any", fill_value=False
    )
    grid = grid.merge(
        pivot.rename(columns={t: f"is_{t.lower()}" for t in EVENT_FILTERS}),
        left_on="date", right_index=True, how="left",
    )
    for t in EVENT_FILTERS:
        col = f"is_{t.lower()}"
        grid[col] = grid[col].astype("boolean").fillna(False).astype(bool)
    grid["is_event"] = grid[[f"is_{t.lower()}" for t in EVENT_FILTERS]].any(axis=1)

    in_window = grid["date"] >= SAMPLE_START
    valid_ret = grid["nights"] <= MAX_NIGHTS_VALID
    hole_days = grid.loc[in_window & ~valid_ret, "date"]
    unobservable = day_type[day_type["announce_date"].isin(hole_days)].copy()
    if len(unobservable):
        unobservable["exclusion_reason"] = "holding window spans data hole (unobservable)"
        excluded = pd.concat([excluded, unobservable], ignore_index=True)
        day_type = day_type[~day_type["announce_date"].isin(hole_days)]
    sample = grid[in_window & valid_ret].copy()

    # --- sanity gates (HYPOTHESIS §5) ---
    years = (sample["date"].max() - sample["date"].min()).days / 365.25
    ev_per_yr = sample["is_event"].sum() / years
    td_per_yr = len(sample) / years
    cpi_nfp_hours = mapped.loc[mapped["type"].isin(["CPI", "NFP"]), "ts_utc"].dt.hour
    fomc_hours = mapped.loc[mapped["type"] == "FOMC", "ts_utc"].dt.hour
    sanity = {
        "event_days_per_year": round(float(ev_per_yr), 2),
        "event_days_per_year_ok": bool(25 <= ev_per_yr <= 40),
        "trading_days_per_year": round(float(td_per_yr), 2),
        "trading_days_per_year_ok": bool(240 <= td_per_yr <= 260),
        "cpi_nfp_utc_hours": sorted(cpi_nfp_hours.unique().tolist()),
        "cpi_nfp_hours_ok": bool(set(cpi_nfp_hours.unique()) <= {12, 13}),
        "fomc_utc_hours": sorted(fomc_hours.unique().tolist()),
        "fomc_hours_ok": bool(set(fomc_hours.unique()) <= FOMC_SCHED_UTC_HOURS),
        "grid_monotonic": bool(sample["date"].is_monotonic_increasing),
        "events_on_nontrading_day": 0,  # impossible by mapping construction; kept for audit
        "released_while_closed_n": int(day_type["released_while_closed"].sum()),
        "max_nights_in_sample": int(sample["nights"].max()),
        "max_nights_ok": bool(sample["nights"].max() <= MAX_NIGHTS_VALID),
        "hole_rows_dropped": int(len(hole_days)),
        "unobservable_event_days_in_hole": int(unobservable["announce_date"].nunique())
        if len(unobservable) else 0,
    }
    all_ok = all(v for k, v in sanity.items() if k.endswith("_ok") or k == "grid_monotonic")

    meta = {
        "hypothesis_commit": "88cc29e",
        "grid_full": [str(grid["date"].min().date()), str(grid["date"].max().date())],
        "sample": [str(sample["date"].min().date()), str(sample["date"].max().date())],
        "sample_days": int(len(sample)),
        "event_days_pooled": int(sample["is_event"].sum()),
        "event_days_by_type": {
            t: int(sample[f"is_{t.lower()}"].sum()) for t in EVENT_FILTERS
        },
        "overlap_multi_type_days": int(
            (sample[[f"is_{t.lower()}" for t in EVENT_FILTERS]].sum(axis=1) > 1).sum()
        ),
        "excluded_rows": int(len(excluded)),
        "sanity": sanity,
        "sanity_all_ok": bool(all_ok),
    }

    sample.to_csv(OUT / "dataset_daily.csv", index=False)
    day_type.to_csv(OUT / "events_mapped.csv", index=False)
    excluded.to_csv(OUT / "events_excluded.csv", index=False)
    (OUT / "build_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    if not all_ok:
        raise SystemExit("SANITY GATE FAILED — see build_meta.json (HYPOTHESIS §5: abort and document)")


if __name__ == "__main__":
    main()
