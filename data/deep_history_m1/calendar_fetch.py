"""
calendar_fetch.py
=================
P3 economic calendar 2018->present for all major currencies.

Source: TradingView economic-calendar API
  https://economic-calendar.tradingview.com/events  (needs Origin/Referer headers; no API key)
  Returns REAL events: title, country, currency, importance(-1/0/1), date(ISO UTC),
  actual/forecast/previous, indicator/source.

WHY NOT Forex Factory: FF historical pages are Cloudflare-protected (verified 403
"Just a moment"); the faireconomy JSON feed only serves the current week. No calendar
API key is present in the environment. TradingView's public calendar endpoint is the
only no-key source that serves the full historical range — fragile / gray-area ToS
(FLAGGED). Never fabricates: failed windows are reported as gaps, not invented.

The API caps at 2000 results/request -> we chunk biweekly (well under cap) with a
recursive split safety guard. Output schema (spec): datetime_utc,currency,impact,event.
A companion *_full.csv keeps actual/forecast/previous/importance/indicator/source.

Output: data/deep_history_utc/calendar/{economic_calendar_2018_2026.csv,
        economic_calendar_2018_2026_full.csv, calendar_gap_report.md, _stats.json}
"""
from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parent.parent / "deep_history_utc" / "calendar"
OUT.mkdir(parents=True, exist_ok=True)
URL = "https://economic-calendar.tradingview.com/events"
COUNTRIES = "US,EU,GB,JP,AU,CA,CH,NZ,DE,CN"   # FX majors + DE (DAX) + CN (risk)
HEADERS = {"Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/",
           "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
START = datetime(2018, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 6, 8, tzinfo=timezone.utc)         # today + 1
IMP = {1: "HIGH", 0: "MED", -1: "LOW"}
CAP = 2000


def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def fetch(frm: datetime, to: datetime, sess: requests.Session, depth: int = 0) -> list | None:
    """Fetch one window; recursively split if the 2000-cap is hit. None = hard failure (gap)."""
    params = {"from": _iso(frm), "to": _iso(to), "countries": COUNTRIES}
    for a in range(5):
        try:
            r = sess.get(URL, params=params, headers=HEADERS, timeout=45)
            if r.status_code == 200:
                res = r.json().get("result", [])
                if len(res) >= CAP and depth < 8 and (to - frm) > timedelta(days=1):
                    mid = frm + (to - frm) / 2
                    a1 = fetch(frm, mid, sess, depth + 1)
                    a2 = fetch(mid, to, sess, depth + 1)
                    if a1 is None or a2 is None:
                        return None
                    return a1 + a2
                return res
            time.sleep(1.0 * (2 ** a))
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (2 ** a))
    return None


def main() -> None:
    sess = requests.Session()
    rows: list[dict] = []
    failed: list[tuple[str, str]] = []
    cur = START
    n_win = 0
    while cur < END:
        nxt = min(cur + timedelta(days=14), END)
        res = fetch(cur, nxt, sess)
        n_win += 1
        if res is None:
            failed.append((cur.date().isoformat(), nxt.date().isoformat()))
        else:
            rows.extend(res)
        if n_win % 20 == 0:
            print(f"  {n_win} windows, {len(rows)} events, {len(failed)} failed "
                  f"(up to {nxt.date()})", flush=True)
        cur = nxt

    # dedup by stable event id
    seen, uniq = set(), []
    for e in rows:
        k = e.get("id") or (e.get("date"), e.get("currency"), e.get("title"))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(e)

    def to_utc(s: str) -> str:
        return s.replace("T", " ").replace(".000Z", "").replace("Z", "") if s else ""

    full = pd.DataFrame([{
        "datetime_utc": to_utc(e.get("date", "")), "currency": e.get("currency"),
        "impact": IMP.get(e.get("importance"), "LOW"), "event": e.get("title"),
        "country": e.get("country"), "indicator": e.get("indicator"),
        "importance_raw": e.get("importance"), "actual": e.get("actual"),
        "forecast": e.get("forecast"), "previous": e.get("previous"),
        "source": e.get("source"), "id": e.get("id"),
    } for e in uniq])
    full = full[full["datetime_utc"] != ""].sort_values(["datetime_utc", "currency"]).reset_index(drop=True)
    spec = full[["datetime_utc", "currency", "impact", "event"]]
    spec.to_csv(OUT / "economic_calendar_2018_2026.csv", index=False)
    full.to_csv(OUT / "economic_calendar_2018_2026_full.csv", index=False)

    # ---- coverage stats for the gap report ----
    full["year"] = full["datetime_utc"].str[:4]
    by_year = full.groupby("year").size().to_dict()
    by_ccy = full["currency"].value_counts().to_dict()
    by_imp = full["impact"].value_counts().to_dict()
    yc = full.groupby(["year", "currency"]).size().unstack(fill_value=0)
    stats = dict(rows=len(full), windows=n_win, failed_windows=failed,
                 date_min=full["datetime_utc"].min(), date_max=full["datetime_utc"].max(),
                 by_year=by_year, by_currency=by_ccy, by_impact=by_imp)
    json.dump(stats, open(OUT / "_stats.json", "w"), indent=2, default=str)

    lines = ["# P3 Economic Calendar — coverage & gap report", "",
             f"**Generated:** assembled from the TradingView economic-calendar API "
             f"(`economic-calendar.tradingview.com/events`).", "",
             "## Source & honest caveats",
             "- **Source:** TradingView public economic-calendar endpoint (no API key; requires "
             "`Origin`/`Referer` headers). Returns REAL events with `importance`, `currency`, ISO-UTC `date`.",
             "- **Gray-area ToS — FLAGGED:** this is an undocumented public endpoint scraped "
             "programmatically; use is fragile and may breach TradingView ToS. Not an officially "
             "licensed feed.",
             "- **Forex Factory was NOT usable:** FF historical calendar pages are Cloudflare-protected "
             "(verified HTTP 403 \"Just a moment…\"); the faireconomy JSON feed only serves the current "
             "week. No calendar API key is present in the environment.",
             "- **No fabrication:** failed request windows are listed below as gaps; no row was invented "
             "or placeholder-filled.",
             "- **impact mapping:** TradingView `importance` 1→HIGH, 0→MED, -1→LOW (LOW includes bank "
             "holidays, `indicator=Holidays`).",
             "- **NOT merged** into `data/panels/economic_calendar.csv` or "
             "`Forex/data/news_events_2020_2025.csv` (per instruction).", "",
             "## Files",
             "- `economic_calendar_2018_2026.csv` — spec schema `datetime_utc,currency,impact,event`.",
             "- `economic_calendar_2018_2026_full.csv` — + `country,indicator,importance_raw,actual,"
             "forecast,previous,source,id`.", "",
             "## Coverage",
             f"- **Rows:** {len(full):,}  ·  **range:** {stats['date_min']} → {stats['date_max']} (UTC)",
             f"- **Currencies:** {COUNTRIES} (CN→CNY, DE→EUR).",
             f"- **By impact:** {by_imp}", "",
             "### Events per year", "", "| year | " + " | ".join(yc.columns) + " | total |",
             "|" + "---|" * (len(yc.columns) + 2)]
    for y, r in yc.iterrows():
        lines.append(f"| {y} | " + " | ".join(str(int(v)) for v in r.values) + f" | {int(r.sum())} |")
    lines += ["", "## Gaps / what could NOT be fetched",
              f"- **Failed request windows:** {len(failed)}"
              + ("" if not failed else " — " + ", ".join(f"{a}→{b}" for a, b in failed[:40]))
              + ("" if len(failed) <= 40 else f" … (+{len(failed)-40} more)"),
              "- **2026 partial:** ends at data/run date (forward of today not yet announced).",
              "- **Pre-2018:** not requested (out of P3 scope).",
              "- **Impact granularity:** TradingView importance tiers differ from FF's exact "
              "high/medium/low taxonomy; treat as approximately aligned.",
              "- **For a licensed/audited feed:** add a TradingEconomics/Finnhub/FMP API key to env, "
              "or run a browser-based FF scraper that can pass the Cloudflare JS challenge."]
    (OUT / "calendar_gap_report.md").write_text("\n".join(lines))
    print(f"\nDONE: {len(full):,} events {stats['date_min']}→{stats['date_max']}; "
          f"{len(failed)} failed windows. -> {OUT}")


if __name__ == "__main__":
    main()
