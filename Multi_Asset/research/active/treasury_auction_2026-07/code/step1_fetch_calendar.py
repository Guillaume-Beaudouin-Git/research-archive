"""Fetch the US Treasury coupon-auction calendar from the public TreasuryDirect API.

Free, public source. No paid data. Writes ../data/auctions.parquet.

The `/securities/auctioned` endpoint is hard-capped at 250 rows and ignores `pagenum`,
so we use `/securities/search` with an explicit auctionDate range, year by year.

Validation performed here (PREREGISTRATION 4.1):
  (a) annual coverage per maturity,
  (b) announcementDate < auctionDate < issueDate,
  (c) auctionDate falls on a business day,
  (d) day-of-month distribution per maturity vs the institutional structure.
"""
from __future__ import annotations

import json
import pathlib
import subprocess

import numpy as np
import pandas as pd

OUT = pathlib.Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(parents=True, exist_ok=True)

SEARCH = "https://www.treasurydirect.gov/TA_WS/securities/search"
KEEP = [
    "cusip", "securityType", "securityTerm", "auctionDate", "announcementDate",
    "issueDate", "maturityDate", "offeringAmount", "bidToCoverRatio",
    "totalAccepted", "primaryDealerAccepted", "reopening",
]
# standard on-the-run coupon tenors
STANDARD = np.array([2, 3, 5, 7, 10, 20, 30])


def fetch_year(sec_type: str, year: int) -> list[dict]:
    url = (f"{SEARCH}?format=json&type={sec_type}&dateFieldName=auctionDate"
           f"&startDate={year}-01-01&endDate={year}-12-31")
    raw = subprocess.run(["curl", "-s", "-m", "120", url],
                         capture_output=True, text=True, check=True).stdout
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def parse_term_years(s: str) -> float:
    """'9-Year 10-Month' -> 9.833 ; '30-Year' -> 30.0."""
    y = m = 0.0
    import re
    if (g := re.search(r"(\d+)-Year", s)):
        y = float(g.group(1))
    if (g := re.search(r"(\d+)-Month", s)):
        m = float(g.group(1))
    return y + m / 12.0


def main() -> None:
    rows: list[dict] = []
    for st in ["Note", "Bond"]:
        for yr in range(2000, 2027):
            got = fetch_year(st, yr)
            rows.extend(got)
        print(f"{st:5s} cumulative rows = {len(rows)}")

    df = pd.DataFrame(rows)
    df = df[[c for c in KEEP if c in df.columns]].drop_duplicates(subset=["cusip", "auctionDate"])

    for c in ["auctionDate", "announcementDate", "issueDate", "maturityDate"]:
        df[c] = pd.to_datetime(df[c], errors="coerce").dt.tz_localize(None).dt.normalize()
    for c in ["offeringAmount", "bidToCoverRatio", "totalAccepted"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Nominal coupon securities only (TIPS / FRN excluded: different mechanism,
    # different dealer hedging instrument).
    df = df[df["securityType"].isin(["Note", "Bond"])]

    # Original tenor: a reopening of the 10y trades as '9-Year 10-Month'.
    # Snap the remaining life to the nearest STANDARD tenor *from above*.
    df["term_raw"] = df["securityTerm"].map(parse_term_years)
    df = df.dropna(subset=["term_raw", "auctionDate"])
    df["term"] = [int(STANDARD[np.argmin(np.abs(STANDARD - t))]) for t in df["term_raw"]]
    # a 9y10m security is a 10y reopen, never a "10y new issue"
    df["is_reopen"] = (np.abs(df["term_raw"] - df["term"]) > 1e-6)
    if "reopening" in df:
        df["is_reopen"] = df["is_reopen"] | df["reopening"].astype(str).str.lower().eq("yes")

    df = (df[df.auctionDate >= "2000-01-01"]
          .sort_values("auctionDate").reset_index(drop=True))

    # ---- validations -------------------------------------------------------
    print("\n=== (a) annual coverage per tenor ===")
    piv = df.pivot_table(index=df.auctionDate.dt.year, columns="term",
                         values="cusip", aggfunc="count").fillna(0).astype(int)
    print(piv.to_string())

    print("\n=== (b) date ordering ===")
    print(f"announcement >= auction : {(df.announcementDate >= df.auctionDate).sum()} / {len(df)}")
    print(f"issue < auction         : {(df.issueDate < df.auctionDate).sum()} / {len(df)}")
    lead = (df.auctionDate - df.announcementDate).dt.days
    print(f"announce lead (days)    : median {lead.median()}  p05 {lead.quantile(.05)}  min {lead.min()}")

    print("\n=== (c) weekday of auctionDate ===")
    print(df.auctionDate.dt.day_name().value_counts().to_string())

    print("\n=== (d) day-of-month per tenor ===")
    for t, s in df.groupby("term")["auctionDate"]:
        print(f"  {t:2d}y : median dom {s.dt.day.median():5.1f}  "
              f"p10 {s.dt.day.quantile(.10):5.1f}  p90 {s.dt.day.quantile(.90):5.1f}  n={len(s)}")

    df.to_parquet(OUT / "auctions.parquet")
    print(f"\nwritten rows={len(df)}  {df.auctionDate.min().date()} -> {df.auctionDate.max().date()}")


if __name__ == "__main__":
    main()
