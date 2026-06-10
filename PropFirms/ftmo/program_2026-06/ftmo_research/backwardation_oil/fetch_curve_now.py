"""Fetch the CURRENT WTI F1/F2 quotes + front prices for markup calibration.

EIA's RCLC series was discontinued 2024-04-05, so the swap markup (measured on
2026 FTMO specs) must be calibrated against the 2026 curve. Saves a small JSON
snapshot to ./cache/curve_now.json. If this fails, the engine falls back to the
last EIA date (2024-04-05) and flags the 26-month calibration mismatch.

WTI front as of 2026-06: June contract (CLM26) expired ~2026-05-19, so
F1 = CLN26 (Jul delivery), F2 = CLQ26 (Aug delivery).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yfinance as yf

CACHE = Path(__file__).resolve().parent / "cache"


def last_close(ticker: str) -> tuple[str, float]:
    h = yf.Ticker(ticker).history(period="10d")
    if h.empty:
        raise RuntimeError(f"no data for {ticker}")
    return str(h.index[-1].date()), float(h["Close"].iloc[-1])


def main() -> None:
    CACHE.mkdir(exist_ok=True)
    out = {}
    for key, tic in {
        "wti_f1": "CLN26.NYM", "wti_f2": "CLQ26.NYM",
        "wti_front_cont": "CL=F", "brent_front_cont": "BZ=F",
    }.items():
        d, px = last_close(tic)
        out[key] = {"ticker": tic, "date": d, "close": px}
        print(f"{key:18s} {tic:10s} {d} {px:.2f}")
    b_now = (out["wti_f1"]["close"] / out["wti_f2"]["close"] - 1.0) * 12.0
    out["wti_basis_ann_now"] = b_now
    print(f"WTI B_ann(now) = {b_now:+.4f} ({b_now * 100:+.2f}%/yr)")
    (CACHE / "curve_now.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
