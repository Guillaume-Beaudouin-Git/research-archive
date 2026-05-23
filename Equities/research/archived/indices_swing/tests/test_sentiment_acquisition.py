"""
tests/test_sentiment_acquisition.py — Probe AAII and NAAIM automated acquisition.

Run: /usr/bin/python3 Equities/research/active/indices_swing/tests/test_sentiment_acquisition.py

KNOWN RESULTS (as of 2026-05-23):
  AAII:
    - URL https://www.aaii.com/files/surveys/sentiment.xls returns 200 but
      with Content-Type: text/html ("Pardon Our Interruption" bot-block).
    - User-Agent spoofing does NOT bypass it (JS challenge / Akamai).
    - Status: NOT automatable without Selenium. DEFERRED to Sprint 2 (manual download).
    - Manual file path: data/aaii_sentiment_manual.xls

  NAAIM:
    - Direct URL from old docs returns 404.
    - Scraping naaim.org HTML page finds dynamic xlsx URL:
      https://naaim.org/wp-content/uploads/YYYY/MM/USE_Data-since-Inception_YYYY-MM-DD.xlsx
    - Download succeeds. 1,039 rows, 2006-07-05 to 2026-05-20 (full history).
    - Publication day: Wednesday (96%); ready_date = pub + 1 BD = Thursday.
    - Status: AUTOMATED ✓
"""
from __future__ import annotations

import io
import re
import sys
import urllib.request as req
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[4]))

import pandas as pd


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def probe_aaii() -> dict:
    url = "https://www.aaii.com/files/surveys/sentiment.xls"
    try:
        r    = req.urlopen(req.Request(url, headers={"User-Agent": UA}), timeout=20)
        raw  = r.read()
        ct   = r.info().get("Content-Type", "N/A")
        is_html = "html" in ct.lower() or raw[:15].lower().startswith(b"<!doctype")
        if is_html:
            return {
                "source": "AAII",
                "status": "BLOCKED",
                "reason": f"URL returns HTML ({len(raw)} bytes) — Akamai/bot protection. Content-Type={ct}",
                "automatable": False,
                "decision": "DEFERRED — manual download required",
                "manual_path": "data/aaii_sentiment_manual.xls",
                "download_from": "https://www.aaii.com/sentimentsurvey/sent_results",
            }
        # Try to parse
        try:
            df = pd.read_excel(io.BytesIO(raw), engine="xlrd", header=None)
        except Exception:
            df = pd.read_excel(io.BytesIO(raw), engine="openpyxl", header=None)
        return {"source": "AAII", "status": "OK", "bytes": len(raw),
                "rows": len(df), "automatable": True}
    except Exception as e:
        return {"source": "AAII", "status": "FAIL", "error": str(e), "automatable": False}


def probe_naaim() -> dict:
    page_url = "https://www.naaim.org/programs/naaim-exposure-index/"
    try:
        r    = req.urlopen(req.Request(page_url, headers={"User-Agent": UA}), timeout=20)
        html = r.read().decode("utf-8", errors="replace")
        links = re.findall(r'href=["\']([^"\']*\.xlsx)["\']', html, re.IGNORECASE)
        links = [l if l.startswith("http") else "https://www.naaim.org" + l for l in links]
        ranked = sorted(
            links,
            key=lambda l: ("since-inception" in l.lower() or "exposure" in l.lower()),
            reverse=True,
        )
        if not ranked:
            return {"source": "NAAIM", "status": "SCRAPE_NO_LINKS", "automatable": False,
                    "reason": "No xlsx links found on page"}

        xlsx_url = ranked[0]
        r2  = req.urlopen(req.Request(xlsx_url, headers={"User-Agent": UA}), timeout=30)
        raw = r2.read()
        df  = pd.read_excel(io.BytesIO(raw))
        df.columns = [str(c).strip().lower() for c in df.columns]
        dc  = next((c for c in df.columns if "date" in c or "week" in c), df.columns[0])
        df["_d"] = pd.to_datetime(df[dc], errors="coerce")
        df = df.dropna(subset=["_d"])

        dow = pd.Series(df["_d"].dt.dayofweek.values).value_counts().sort_index()
        primary_dow = dow.idxmax()

        return {
            "source":       "NAAIM",
            "status":       "OK",
            "automatable":  True,
            "method":       "HTML scrape → xlsx download",
            "xlsx_url":     xlsx_url,
            "bytes":        len(raw),
            "rows":         len(df),
            "first":        df["_d"].min().date(),
            "last":         df["_d"].max().date(),
            "primary_pub_dow": primary_dow,  # 2=Wed
            "ready_date_dow":  (primary_dow + 1) % 7,  # 3=Thu
            "day_dist":     dow.to_dict(),
        }
    except Exception as e:
        return {"source": "NAAIM", "status": "FAIL", "error": str(e), "automatable": False}


if __name__ == "__main__":
    print("=== SENTIMENT ACQUISITION PROBE ===\n")

    aaii = probe_aaii()
    print("[AAII]")
    for k, v in aaii.items():
        print(f"  {k}: {v}")
    print()

    naaim = probe_naaim()
    print("[NAAIM]")
    for k, v in naaim.items():
        print(f"  {k}: {v}")
    print()

    print("=== DECISION ===")
    if aaii.get("automatable") and naaim.get("automatable"):
        print("Both AAII + NAAIM automated → S4 INCLUDED in Sprint 1 with full composite.")
    elif not aaii.get("automatable") and naaim.get("automatable"):
        print("AAII DEFERRED (bot-blocked), NAAIM automated.")
        print("S4 in Sprint 1: NAAIM + PCR10 composite (AAII deferred to Sprint 2).")
    elif not aaii.get("automatable") and not naaim.get("automatable"):
        print("Both blocked → S4 DEFERRED to Sprint 2.")
    else:
        print("NAAIM DEFERRED, AAII automated. S4 partial.")
