"""What the free exogenous caches ACTUALLY contain. Run first, before anything is built."""
from __future__ import annotations

import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from exog_lib import MAIN, POST2021  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..")

rows = []


def add(fam, path, col, idx, requested_start=None):
    s = col.dropna()
    if len(s) == 0:
        rows.append(dict(family=fam, file=os.path.basename(path), series=col.name,
                         n_obs=0, first="EMPTY", last="EMPTY", verdict="EMPTY"))
        return
    post = s[s.index >= POST2021]
    # median gap in calendar days -> frequency
    gaps = pd.Series(s.index).diff().dt.days.dropna()
    med_gap = float(gaps.median()) if len(gaps) else float("nan")
    freq = ("daily" if med_gap <= 1.5 else "weekly" if med_gap <= 8
            else "monthly" if med_gap <= 35 else "irregular")
    trunc = ""
    if requested_start is not None and s.index.min() > pd.Timestamp(requested_start) + pd.Timedelta(days=40):
        trunc = f"TRUNCATED (requested {requested_start}, first obs {s.index.min().date()})"
    rows.append(dict(
        family=fam, file=os.path.basename(path), series=col.name,
        n_obs=len(s), first=str(s.index.min().date()), last=str(s.index.max().date()),
        median_gap_days=med_gap, freq=freq,
        n_post2021=len(post),
        n_pre2021=len(s) - len(post),
        verdict=trunc or ("ENDS PRE-2021 -> unusable" if s.index.max() < POST2021 else "usable"),
    ))


# --- FRED bundles -----------------------------------------------------------
specs = [
    ("fred_BAMLH0A0_DGS3MO_DTWEXBGS_d06fce80fc", "2007-01-01"),
    ("fred_DTB3_37358bdf84", "2000-01-01"),
    ("fred_DGS3MO_16fc089f19", "2003-01-01"),
    ("fred_T10Y2Y_4b4c751920", "2003-01-01"),
    ("fred_DTWEXBGS_ff6045edaa", "2006-01-01"),
    ("fred_VIXCLS_14ec2ab193", "2007-01-01"),
]
for name, start in specs:
    p = f"{MAIN}/data/raw/{name}.parquet"
    d = pd.read_parquet(p)
    for c in d.columns:
        add("FRED", p, d[c], d.index, start)

# --- HTTP scrapes -----------------------------------------------------------
for name in ["http_cboe_pcr_equity_a15f2987", "http_cboe_pcr_total_3d75419d",
             "http_naaim_exposure_xlsx_ffd686b1"]:
    p = f"{MAIN}/data/raw/{name}.parquet"
    d = pd.read_parquet(p)
    for c in d.columns:
        add("scrape", p, d[c], d.index)

# --- panels -----------------------------------------------------------------
p = f"{MAIN}/data/panels/fx_rates_3m.csv"
d = pd.read_csv(p, index_col=0, parse_dates=True)
for c in ["USD", "JPY", "EUR", "GBP"]:
    add("panel", p, d[c], d.index)

p = f"{MAIN}/data/panels/vix_term_structure.csv"
d = pd.read_csv(p, index_col=0, parse_dates=True)
for c in d.columns:
    add("panel", p, d[c], d.index)

# --- calendars (event lists, not series) ------------------------------------
cal_rows = []
p = f"{MAIN}/data/personal_book/post_fomc_drift/data_cache/fomc_events.csv"
d = pd.read_csv(p, parse_dates=["date"])
cal_rows.append(dict(file="fomc_events.csv", n=len(d), first=str(d["date"].min().date()),
                     last=str(d["date"].max().date()),
                     n_post2021=int((d["date"] >= POST2021).sum()),
                     detail="date + source only; NO time-of-day"))
p = f"{MAIN}/data/panels/economic_calendar.csv"
d = pd.read_csv(p, parse_dates=["date"])
for ev, g in d.groupby("event"):
    cal_rows.append(dict(file="economic_calendar.csv", n=len(g),
                         first=str(g["date"].min().date()), last=str(g["date"].max().date()),
                         n_post2021=int((g["date"] >= POST2021).sum()),
                         detail=f"event={ev}; has time_utc"))

inv = pd.DataFrame(rows)
inv.to_csv(f"{OUT}/cache_inventory.csv", index=False)
cal = pd.DataFrame(cal_rows)
cal.to_csv(f"{OUT}/cache_inventory_calendars.csv", index=False)

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
print(inv.to_string(index=False))
print()
print(cal.to_string(index=False))
