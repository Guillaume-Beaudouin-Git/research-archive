"""Trial I-3 universe selection (rule frozen in preregistration) + 1h/funding fetch.

Rule: BTC/ETH/SOL + top-10 other UM perps by median daily quote-volume over
2024-01->2026-05 among symbols with >=2y history (first daily bar <= 2024-06-10).
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

import lib_data as ld

CORE = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


START_MS, END_MS = 1704067200000, 1748736000000  # 2024-01-01 .. 2026-06-01

FAILED: list[str] = []

# Delisted-from-REST symbols, Vision-verified 2024+ median quote volume far below
# the top-10 cutoff (BDXN $3.7M, BTCST $0.0M, SXP $5.9M vs cutoff ~$206M).
RESOLVED_INELIGIBLE = {"BDXNUSDT", "BTCSTUSDT", "SXPUSDT"}


def rank_volume(sym: str) -> tuple[str, float, str] | None:
    """Median daily quote volume 2024-01->2026-05; None = ineligible; FAILED list = fetch error."""
    if sym in RESOLVED_INELIGIBLE:
        return None
    try:
        rows: list[list] = []
        cur = START_MS
        while True:
            r = ld._get(f"{ld.FAPI}/fapi/v1/klines",
                        params={"symbol": sym, "interval": "1d", "startTime": cur,
                                "endTime": END_MS, "limit": 1500})
            chunk = r.json()
            if not chunk:
                break
            rows += chunk
            if len(chunk) < 500 or chunk[-1][0] >= END_MS - 86_400_000:
                break
            cur = chunk[-1][0] + 1
            time.sleep(0.1)
        if not rows or len(rows) < 200:
            return None
        first = pd.Timestamp(rows[0][0], unit="ms", tz="UTC")
        if first > pd.Timestamp("2024-06-10", tz="UTC"):
            return None
        qv = pd.Series([float(x[7]) for x in rows])
        return sym, float(qv.median()), str(first.date())
    except FileNotFoundError:
        return None
    except Exception as e:  # noqa: BLE001
        FAILED.append(sym)
        print(f"RANK FAIL {sym}: {e}")
        return None
    finally:
        time.sleep(0.1)


def vision_fallback_rank(sym: str) -> tuple[str, float, str] | None:
    """Eligibility from Vision monthly 1d archives when REST cannot serve (delisted)."""
    months = pd.period_range("2024-01", "2026-05", freq="M").strftime("%Y-%m")
    qvs: list[float] = []
    first: pd.Timestamp | None = None
    for m in months:
        df = ld.monthly_klines(sym, "1d", m)
        if df is not None and len(df):
            qvs += df["quote_volume"].tolist()
            first = first or df.index[0]
    if not qvs or len(qvs) < 200 or first is None or first > pd.Timestamp("2024-06-10", tz="UTC"):
        return None
    import numpy as np
    return sym, float(np.median(qvs)), str(first.date())


def main() -> None:
    syms = [s for s in ld.all_um_symbols() if s not in CORE]
    print(f"ranking {len(syms)} symbols by 2024+ median quote volume…")
    ranked: list[tuple[str, float, str]] = []
    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(rank_volume, s) for s in syms]
        for f in as_completed(futs):
            res = f.result()
            if res:
                ranked.append(res)
    for sym in list(FAILED):
        FAILED.remove(sym)
        res = rank_volume(sym)
        if res:
            ranked.append(res)
    for sym in list(FAILED):
        res = vision_fallback_rank(sym)
        print(f"vision fallback {sym}: {res}")
        if res:
            ranked.append(res)
        FAILED.remove(sym)
    if FAILED:
        raise RuntimeError(f"FAIL-LOUD: unrankable symbols after retry+fallback: {FAILED}")
    ranked.sort(key=lambda x: -x[1])
    top10 = ranked[:10]
    universe = CORE + [s for s, _, _ in top10]
    json.dump({"universe": universe,
               "top10_detail": [{"symbol": s, "med_qv_usd": v, "first_bar": d} for s, v, d in top10]},
              open(ld.CACHE / "i3_universe.json", "w"), indent=1)
    print("UNIVERSE:", universe)

    months = pd.period_range("2019-12", "2026-05", freq="M").strftime("%Y-%m").tolist()

    def fetch_symbol(sym: str) -> str:
        ld.funding_history(sym)
        got = 0
        for m in months:
            df = ld.monthly_klines(sym, "1h", m)
            got += df is not None
        return f"{sym}: {got} months 1h + funding ok"

    with ThreadPoolExecutor(6) as ex:
        for f in as_completed([ex.submit(fetch_symbol, s) for s in universe]):
            print(f.result())


if __name__ == "__main__":
    main()
