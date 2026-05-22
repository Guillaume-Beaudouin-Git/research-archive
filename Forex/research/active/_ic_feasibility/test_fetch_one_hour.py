"""Quick smoke test: fetch one hour of EURUSD from Dukascopy and decode it."""
import struct, lzma, requests, datetime, sys
from pathlib import Path

PAIR = "EURUSD"
# 2024-01-02 08:00 UTC — first Tuesday after NY/London new-year holiday, liquid
YEAR, MONTH_0IDX, DAY, HOUR = 2024, 0, 2, 8  # month 0-indexed → January

URL = f"https://datafeed.dukascopy.com/datafeed/{PAIR}/{YEAR}/{MONTH_0IDX:02d}/{DAY:02d}/{HOUR:02d}h_ticks.bi5"
print(f"URL: {URL}")

resp = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
print(f"Status: {resp.status_code}, bytes: {len(resp.content)}")
if resp.status_code != 200 or not resp.content:
    print("FAIL: bad response")
    sys.exit(1)

raw = lzma.decompress(resp.content)
TICK_STRUCT = struct.Struct(">IIIff")
TICK_SIZE = 20
n = len(raw) // TICK_SIZE
print(f"Ticks: {n}")
if n == 0:
    print("FAIL: 0 ticks")
    sys.exit(1)

point = 1e-5  # EURUSD 5-decimal
records = [TICK_STRUCT.unpack_from(raw, i * TICK_SIZE) for i in range(min(n, 5))]
hour_dt = datetime.datetime(YEAR, 1, 2, HOUR, tzinfo=datetime.timezone.utc)
for ms, ask, bid, avol, bvol in records:
    ts = hour_dt + datetime.timedelta(milliseconds=int(ms))
    print(f"  {ts.isoformat()}  ask={ask * point:.5f}  bid={bid * point:.5f}  av={avol:.1f}  bv={bvol:.1f}")

print("\nOK: Dukascopy decode validated")
