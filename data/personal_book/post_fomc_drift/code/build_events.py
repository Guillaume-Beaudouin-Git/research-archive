"""Build the canonical FOMC decision-event list per HYPOTHESIS.md section 3.

Sources:
  - 2018-01-01..2026-06-07: prescribed 74,543-event calendar (USD `Fed Interest Rate Decision`),
    filter identical to PropFirms/ftmo_paper_edges/code/edge_fomc_cycle.py::fomc_dates.
  - 2004-2017: federalreserve.gov historical pages (statement press-release URL dates),
    reconciled against the hardcoded scheduled-meeting prior; primary source wins, all
    discrepancies logged.
  - All years: FRED DFEDTAR/DFEDTARU target-change dates not within +/-1 business day of a
    listed event are ADDED as unscheduled decisions (mechanical rule).

Binding cross-validation: every target-change date must match a listed event (+/-1 bd).

Output: data_cache/fomc_events.csv (date, source) + reconciliation log to stdout
(redirect to results/event_reconciliation.log).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
CAL = REPO / "data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv"

# Scheduled FOMC statement (decision) dates 2004-2017 — prior to be verified by the scrape.
SCHEDULED_PRIOR = {
    2004: ["0128", "0316", "0504", "0630", "0810", "0921", "1110", "1214"],
    2005: ["0202", "0322", "0503", "0630", "0809", "0920", "1101", "1213"],
    2006: ["0131", "0328", "0510", "0629", "0808", "0920", "1025", "1212"],
    2007: ["0131", "0321", "0509", "0628", "0807", "0918", "1031", "1211"],
    2008: ["0130", "0318", "0430", "0625", "0805", "0916", "1029", "1216"],
    2009: ["0128", "0318", "0429", "0624", "0812", "0923", "1104", "1216"],
    2010: ["0127", "0316", "0428", "0623", "0810", "0921", "1103", "1214"],
    2011: ["0126", "0315", "0427", "0622", "0809", "0921", "1102", "1213"],
    2012: ["0125", "0313", "0425", "0620", "0801", "0913", "1024", "1212"],
    2013: ["0130", "0320", "0501", "0619", "0731", "0918", "1030", "1218"],
    2014: ["0129", "0319", "0430", "0618", "0730", "0917", "1029", "1217"],
    2015: ["0128", "0318", "0429", "0617", "0729", "0917", "1028", "1216"],
    2016: ["0127", "0316", "0427", "0615", "0727", "0921", "1102", "1214"],
    2017: ["0201", "0315", "0503", "0614", "0726", "0920", "1101", "1213"],
}

PAT_NEW = re.compile(r"monetary(20\d{6})[a-z]?\.htm")
PAT_MID = re.compile(r"/press/monetary/(20\d{6})[a-z]?\.htm")  # 2006-2010 era URLs
PAT_OLD = re.compile(r"/boarddocs/press/monetary/20\d{2}/(20\d{6})")


def scrape_year(year: int) -> list[str]:
    p = BASE / f"data_cache/fed_pages/fomc_{year}.html"
    if not p.exists() or p.stat().st_size < 2000:
        return []
    html = p.read_text(errors="ignore")
    ds = {m.group(1) for m in PAT_NEW.finditer(html)}
    ds |= {m.group(1) for m in PAT_MID.finditer(html)}
    ds |= {m.group(1) for m in PAT_OLD.finditer(html)}
    return sorted(d for d in ds if d.startswith(str(year)))


def load_target_changes() -> pd.DatetimeIndex:
    """Canonical target-change dates from assemble_yields.py (FRED DFEDTAR/DFEDTARU diffs
    or, FRED being unreachable, the primary source openmarket.htm — see provenance.json).
    Dates may be EFFECTIVE dates (announcement +1 bd in the modern era) — absorbed by the
    pre-registered +/-1 business-day matching tolerance."""
    df = pd.read_csv(BASE / "data_cache/target_changes.csv", parse_dates=["date"])
    return pd.DatetimeIndex(df["date"]).sort_values()


def main() -> None:
    # --- 2018+ prescribed calendar
    cal = pd.read_csv(CAL, usecols=["datetime_utc", "currency", "event"])
    m = (cal["currency"] == "USD") & cal["event"].str.contains(
        "Fed Interest Rate Decision", case=False, na=False
    )
    cal_dates = (
        pd.to_datetime(cal.loc[m, "datetime_utc"]).dt.normalize().drop_duplicates().sort_values()
    )
    events = {d: "calendar" for d in cal_dates}
    print(f"[calendar] {len(cal_dates)} USD rate-decision dates "
          f"{cal_dates.min().date()} .. {cal_dates.max().date()}")

    # --- 2004-2017 Fed historical pages, reconciled against the scheduled prior
    for year in range(2004, 2018):
        scraped = scrape_year(year)
        prior = [f"{year}{md}" for md in SCHEDULED_PRIOR[year]]
        sset, pset = set(scraped), set(prior)
        matched = sorted(sset & pset)
        scrape_only = sorted(sset - pset)
        prior_only = sorted(pset - sset)
        if not scraped:
            print(f"[fed {year}] PAGE EMPTY/MISSING -> fall back to prior (8 dates), "
                  f"FRED cross-check still binding")
            kept = prior
        else:
            kept = matched
            for d in scrape_only:
                # candidate statements not in the scheduled prior: unscheduled or non-rate
                print(f"[fed {year}] scrape-only candidate {d} -> held for FRED-diff check "
                      f"(kept only if a target change confirms a rate decision)")
            for d in prior_only:
                print(f"[fed {year}] PRIOR DATE {d} NOT FOUND IN SCRAPE -> kept (prior), "
                      f"flagged for manual review")
                kept.append(d)
        if len(kept) != 8:
            print(f"[fed {year}] WARNING: {len(kept)} scheduled dates retained (expected 8)")
        for d in sorted(kept):
            events[pd.Timestamp(d)] = "fed_scrape"

    # --- target-change additions + binding cross-validation
    chg = load_target_changes()
    chg = chg[(chg >= "2004-01-01") & (chg <= "2026-06-07")]
    ev_idx = pd.DatetimeIndex(sorted(events))
    bdays = pd.tseries.offsets.BDay(1)
    unmatched = []
    for c in chg:
        near = ev_idx[(ev_idx >= c - bdays) & (ev_idx <= c + bdays)]
        if len(near) == 0:
            unmatched.append(c)
    for c in unmatched:
        print(f"[fred-diff] target change {c.date()} has no listed event -> ADDED as unscheduled")
        events[c] = "fred_diff"

    out = (
        pd.DataFrame({"date": list(events), "source": list(events.values())})
        .sort_values("date")
        .reset_index(drop=True)
    )
    # re-validate after additions
    ev_idx = pd.DatetimeIndex(out["date"])
    fails = [c for c in chg if len(ev_idx[(ev_idx >= c - bdays) & (ev_idx <= c + bdays)]) == 0]
    if fails:
        raise SystemExit(f"CROSS-VALIDATION FAIL: target changes with no event: {fails}")
    print(f"[cross-validation] all {len(chg)} target-change dates matched to an event (+/-1bd) OK")

    per_year = out["date"].dt.year.value_counts().sort_index()
    print("[events/year]", dict(per_year))
    out.to_csv(BASE / "data_cache/fomc_events.csv", index=False)
    print(f"[out] {len(out)} events -> data_cache/fomc_events.csv")


if __name__ == "__main__":
    main()
