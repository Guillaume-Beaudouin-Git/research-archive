"""
fetch_finra.py — fetch FINRA consolidated daily short-volume (CNMSshvol) for a universe.
B1 IC gate: QQQ short-volume = ZERO-survivorship NDX index proxy; NDX mega-cap aggregate = today's
constituents (SURVIVORSHIP-OPTIMISTIC upper bound, flagged). Free FINRA CDN, 2009+. Write only here.
"""
from __future__ import annotations
import urllib.request, urllib.error, io, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd

OUT = Path(__file__).parent
ETFS = ["QQQ", "QQQM", "TQQQ", "SQQQ", "PSQ", "QLD", "QID"]               # NDX index proxies (QQQ = zero-survivorship)
NDX = ["AAPL","MSFT","NVDA","AMZN","GOOGL","GOOG","META","TSLA","AVGO","COST","NFLX","ADBE","AMD",
       "PEP","CSCO","TMUS","INTC","CMCSA","TXN","QCOM","AMAT","INTU","HON","AMGN","ISRG","BKNG","MU",
       "ADI","LRCX","REGN","VRTX","PANW","KLAC","SNPS","CDNS","MRVL","ORLY","CRWD","ABNB","FTNT",
       "ADP","MELI","CTAS","PYPL","MDLZ","PDD","MAR","CEG","ROP","NXPI"]   # ~current NDX mega-caps (survivorship-flagged)
UNIV = set(ETFS + NDX)
BASE = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt"
HDR = {"User-Agent": "Mozilla/5.0 (research; feasibility-gate)"}


def fetch_one(d: pd.Timestamp):
    url = BASE.format(d.strftime("%Y%m%d"))
    try:
        req = urllib.request.Request(url, headers=HDR)
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode("utf-8", "ignore")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, Exception):
        return []                                   # 404 = non-trading day / not published
    if "|" not in raw or "Symbol" not in raw[:50]:
        return []
    out = []
    for line in raw.splitlines()[1:]:
        p = line.split("|")
        if len(p) < 5 or p[1] not in UNIV:
            continue
        try:
            out.append((d.normalize(), p[1], int(p[2]), int(p[4])))   # date, sym, short, total
        except ValueError:
            continue
    return out


def main():
    days = pd.bdate_range("2018-01-01", "2026-05-29")
    print(f"fetching {len(days)} weekdays of FINRA CNMSshvol (universe {len(UNIV)} symbols) ...", flush=True)
    rows, done, t0 = [], 0, time.time()
    with ThreadPoolExecutor(max_workers=12) as ex:
        for res in ex.map(fetch_one, days):
            rows.extend(res); done += 1
            if done % 250 == 0:
                print(f"  {done}/{len(days)} days | {len(rows)} rows | {time.time()-t0:.0f}s", flush=True)
    df = pd.DataFrame(rows, columns=["date", "symbol", "short_vol", "total_vol"])
    df = df.drop_duplicates(["date", "symbol"]).sort_values(["date", "symbol"]).reset_index(drop=True)
    df.to_parquet(OUT / "finra_shortvol_universe.parquet", index=False)
    ndays = df["date"].nunique()
    cov = df.groupby("symbol")["date"].nunique()
    print(f"\nDONE: {len(df)} rows | {ndays} trading days | {df.date.min().date()}..{df.date.max().date()}", flush=True)
    print(f"QQQ days covered: {cov.get('QQQ', 0)} | median symbol coverage: {int(cov.median())}", flush=True)
    print("per-year QQQ rows:", df[df.symbol == 'QQQ'].assign(y=df[df.symbol=='QQQ'].date.dt.year).groupby('y').size().to_dict(), flush=True)


if __name__ == "__main__":
    main()
