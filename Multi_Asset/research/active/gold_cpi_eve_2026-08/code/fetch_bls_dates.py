"""Recover the REAL BLS release calendars from the archived news releases.

The date of every BLS news release is encoded in the filename of the document
BLS itself published: `news.release/archives/<rel>_MMDDYYYY.htm`. That is the
primary, authentic source — not a rule, not a scrape of a broker calendar.

bls.gov answers 403 to a browser-like User-Agent and 200 to a descriptive one
carrying a contact address, which is what BLS's robots policy asks for.

Writes to the SESSION CACHE, never to the repo:
    $CPI_CACHE/bls_{cpi,ppi,empsit}_dates.csv
    $CPI_CACHE/blsrel/<MMDDYYYY>.htm          (release documents, for §B/§D2)
"""
from __future__ import annotations

import datetime
import os
import re
import subprocess
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpi_lib import CACHE  # noqa: E402

UA = "research-bot/1.0 (guillaumebeaudouinooo@gmail.com)"
KINDS = {"cpi": "cpi", "ppi": "ppi", "empsit": "empsit"}


def _get(url: str) -> str:
    r = subprocess.run(["curl", "-sS", "-A", UA, url], capture_output=True)
    return r.stdout.decode("utf-8", "ignore")


def main(start_year: int = 2007) -> None:
    os.makedirs(f"{CACHE}/blsrel", exist_ok=True)
    for kind, slug in KINDS.items():
        index = _get(f"https://www.bls.gov/bls/news-release/{slug}.htm")
        stamps = sorted(set(re.findall(rf"{slug}_(\d{{8}})\.", index)))
        stamps = [s for s in stamps if int(s[4:]) >= start_year]
        dates = sorted(datetime.date(int(s[4:]), int(s[:2]), int(s[2:4])) for s in stamps)
        pd.DataFrame({"date": pd.to_datetime(dates)}).to_csv(
            f"{CACHE}/bls_{kind}_dates.csv", index=False)
        print(f"{kind}: {len(dates)} releases {dates[0]} .. {dates[-1]}")
        if kind != "cpi":
            continue
        # CPI documents are also needed for the field-level concordance check
        # and for the published y/y series used by the regime test.
        hrefs = dict(re.findall(r'href="([^"]*cpi_(\d{8})\.(?:htm|txt))"', index)[::1]
                     ) if False else {}
        for m in re.finditer(r'href="([^"]*cpi_(\d{8})\.(?:htm|txt))"', index):
            u, s = m.group(1), m.group(2)
            if int(s[4:]) < start_year:
                continue
            dst = f"{CACHE}/blsrel/{s}.htm"
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                continue
            body = _get(f"https://www.bls.gov{u}")
            if not body.strip():          # a few .htm are empty; the PDF is served
                body = _get(f"https://www.bls.gov{u.replace('.htm', '.pdf')}")
            open(dst, "w", encoding="utf-8").write(body)
            time.sleep(0.3)


if __name__ == "__main__":
    main()
