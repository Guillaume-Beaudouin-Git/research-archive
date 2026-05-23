"""Test: fetch one full trading day with the new requests-based fetcher."""
import struct, lzma, time, requests
import pandas as pd
from datetime import datetime, timezone, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
BASE_URL = "https://datafeed.dukascopy.com/datafeed/{pair}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
TICK_STRUCT = struct.Struct(">IIIff")

pair = "EURUSD"
# 2024-01-02 (Tuesday, fully liquid)
test_hours = [datetime(2024, 1, 2, h, tzinfo=timezone.utc) for h in range(0, 24)]

session = requests.Session()
session.headers.update(HEADERS)

results = []
for h in test_hours:
    url = BASE_URL.format(pair=pair, year=h.year, month=h.month-1, day=h.day, hour=h.hour)
    r = session.get(url, timeout=15)
    status = r.status_code
    n_ticks = 0
    if status == 200 and r.content:
        raw = lzma.decompress(r.content)
        n_ticks = len(raw) // 20
    results.append((h.hour, status, n_ticks))
    print(f"  {h.hour:02d}:00 UTC → HTTP {status}, {n_ticks:5d} ticks")
    time.sleep(0.1)

non_empty = [(h, n) for h, s, n in results if n > 0]
print(f"\nHours with data: {len(non_empty)}/24")
print(f"Total ticks: {sum(n for _, n in non_empty):,}")
print(f"Fill rate: {len(non_empty)/24*100:.1f}%")
