"""Data layer for session_I: Binance Vision bulk, Binance REST, DefiLlama emissions.

All fetches cache to CACHE; fail-loud (no synthetic fallback). UTC native.
"""
from __future__ import annotations

import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
VISION = "https://data.binance.vision"
FAPI = "https://fapi.binance.com"
LLAMA_DS = "https://defillama-datasets.llama.fi"

KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore",
]


def _get(url: str, params: dict | None = None, retries: int = 4, timeout: int = 30) -> requests.Response:
    last: Exception | None = None
    for k in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                raise FileNotFoundError(url)
            last = RuntimeError(f"HTTP {r.status_code} {url}")
        except FileNotFoundError:
            raise
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"fetch failed after {retries} tries: {url}") from last


def s3_list_prefixes(prefix: str) -> list[str]:
    """List sub-prefixes (directories) under a Vision S3 prefix, paginated."""
    out: list[str] = []
    marker = ""
    while True:
        url = f"{S3}?delimiter=/&prefix={prefix}" + (f"&marker={marker}" if marker else "")
        txt = _get(url).text
        page = [seg.split("</Prefix>")[0] for seg in txt.split("<Prefix>")[2:]]
        out += page
        if "<IsTruncated>true</IsTruncated>" not in txt:
            return out
        marker = page[-1]


def s3_list_keys(prefix: str) -> list[str]:
    txt = _get(f"{S3}?delimiter=/&prefix={prefix}").text
    return [seg.split("</Key>")[0] for seg in txt.split("<Key>")[1:]]


def all_um_symbols() -> list[str]:
    """Every UM perp symbol ever archived (includes delisted)."""
    f = CACHE / "um_symbols.json"
    if f.exists():
        return json.loads(f.read_text())
    syms = [p.rstrip("/").split("/")[-1] for p in s3_list_prefixes("data/futures/um/monthly/klines/")]
    syms = [s for s in syms if s.endswith("USDT")]
    f.write_text(json.dumps(syms))
    return syms


def listing_month(symbol: str) -> str | None:
    """First archived monthly 1d kline month 'YYYY-MM' (proxy for listing date)."""
    d = CACHE / "listing_months.json"
    store: dict[str, str | None] = json.loads(d.read_text()) if d.exists() else {}
    if symbol in store:
        return store[symbol]
    keys = s3_list_keys(f"data/futures/um/monthly/klines/{symbol}/1d/")
    months = sorted(k.split(f"{symbol}-1d-")[-1][:7] for k in keys if k.endswith(".zip"))
    store[symbol] = months[0] if months else None
    d.write_text(json.dumps(store))
    return store[symbol]


def _read_kline_zip(content: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        raw = z.read(z.namelist()[0])
    df = pd.read_csv(io.BytesIO(raw), header=None)
    if isinstance(df.iloc[0, 0], str) and not df.iloc[0, 0].lstrip("-").isdigit():
        df = df.iloc[1:].reset_index(drop=True)  # newer zips carry a header row
    df.columns = KLINE_COLS[: df.shape[1]]
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # 2025+ files use microsecond epochs
    unit_us = df["open_time"].iloc[0] > 1e14
    df["ts"] = pd.to_datetime(df["open_time"], unit=("us" if unit_us else "ms"), utc=True)
    return df.set_index("ts").sort_index()


def monthly_klines(symbol: str, interval: str, month: str) -> pd.DataFrame | None:
    """One Vision monthly kline zip -> DataFrame, cached as parquet. None if 404."""
    pq = CACHE / f"k_{symbol}_{interval}_{month}.parquet"
    if pq.exists():
        return pd.read_parquet(pq)
    url = f"{VISION}/data/futures/um/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"
    try:
        df = _read_kline_zip(_get(url).content)
    except FileNotFoundError:
        return None
    df.to_parquet(pq)
    return df


def funding_history(symbol: str) -> pd.DataFrame:
    """Full settled funding history for one symbol (Vision monthlies), cached."""
    pq = CACHE / f"f_{symbol}.parquet"
    if pq.exists():
        return pd.read_parquet(pq)
    keys = [k for k in s3_list_keys(f"data/futures/um/monthly/fundingRate/{symbol}/") if k.endswith(".zip")]
    if not keys:
        raise FileNotFoundError(f"no funding archive for {symbol}")
    frames = []
    for k in keys:
        with zipfile.ZipFile(io.BytesIO(_get(f"{VISION}/{k}").content)) as z:
            raw = z.read(z.namelist()[0])
        df = pd.read_csv(io.BytesIO(raw))
        df.columns = [c.strip().lower() for c in df.columns]
        tcol = next(c for c in df.columns if "time" in c)
        rcol = next(c for c in df.columns if "rate" in c)
        unit_us = float(df[tcol].iloc[0]) > 1e14
        out = pd.DataFrame({
            "ts": pd.to_datetime(pd.to_numeric(df[tcol]), unit=("us" if unit_us else "ms"), utc=True),
            "rate": pd.to_numeric(df[rcol]),
        })
        frames.append(out)
    all_f = pd.concat(frames).sort_values("ts").drop_duplicates("ts").set_index("ts")
    all_f.to_parquet(pq)
    return all_f


def rest_daily_klines(symbol: str, start_ms: int = 0) -> pd.DataFrame:
    """Full daily klines via fapi REST (works for delisted symbols too), cached."""
    pq = CACHE / f"d_{symbol}.parquet"
    if pq.exists():
        return pd.read_parquet(pq)
    rows: list[list] = []
    cur = start_ms
    while True:
        r = _get(f"{FAPI}/fapi/v1/klines",
                 params={"symbol": symbol, "interval": "1d", "startTime": cur, "limit": 1500})
        chunk = r.json()
        if not chunk:
            break
        rows += chunk
        if len(chunk) < 1500:
            break
        cur = chunk[-1][0] + 1
        time.sleep(0.15)
    if not rows:
        raise FileNotFoundError(f"no REST daily klines for {symbol}")
    df = pd.DataFrame(rows, columns=KLINE_COLS)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("ts").sort_index()
    df.to_parquet(pq)
    return df


def llama_protocol_list() -> list[str]:
    f = CACHE / "emissions_protocols.json"
    if f.exists():
        return json.loads(f.read_text())
    lst = _get(f"{LLAMA_DS}/emissionsProtocolsList").json()
    f.write_text(json.dumps(lst))
    return lst


def llama_emissions(protocol: str) -> dict | None:
    f = CACHE / f"em_{protocol}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            return None
    try:
        d = _get(f"{LLAMA_DS}/emissions/{protocol}").json()
    except (FileNotFoundError, RuntimeError, json.JSONDecodeError):
        f.write_text("null")
        return None
    f.write_text(json.dumps(d))
    return d


def fetch_all_emissions(protocols: list[str], workers: int = 8) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(llama_emissions, p): p for p in protocols}
        for fut in as_completed(futs):
            d = fut.result()
            if d:
                out[futs[fut]] = d
    return out


def coingecko_ticker_map() -> dict[str, str]:
    """gecko_id -> upper ticker."""
    f = CACHE / "cg_list.json"
    if f.exists():
        lst = json.loads(f.read_text())
    else:
        lst = _get("https://api.coingecko.com/api/v3/coins/list", timeout=60).json()
        f.write_text(json.dumps(lst))
    return {c["id"]: c["symbol"].upper() for c in lst}
