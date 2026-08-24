"""Build M5 low/high/close panel from deep_history_utc M1, Paris-localized, left-labeled,
aligned to the canonical sim_m5 grid. bid/ask via spread. Cache + G-tz validation.

G-tz gate: Duka-derived M5 CLOSE must reproduce canonical sim_m5 close (same source).
"""
import time
from pathlib import Path
import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
DEEP = MAIN / "data/deep_history_utc"
CACHE = MAIN / "data/ftmo_portfolio/cache"
HERE = Path(__file__).resolve().parent
OUT = HERE / "data"
LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]
PT = {"XAUUSD": 0.01, "USDJPY": 0.001, "US100": 0.01, "GER40": 0.01}  # 10^-digits
t0 = time.time()


def log(m):
    print(f"{m}  [{time.time()-t0:.0f}s]", flush=True)


def build_leg(sym):
    """M1 (true UTC) -> M5 Paris-localized left-labeled: low/high/close/spread."""
    df = pd.read_csv(DEEP / f"{sym}_M1.csv",
                     usecols=["timestamp_utc", "high", "low", "close", "spread"],
                     dtype={"high": "float64", "low": "float64", "close": "float64",
                            "spread": "float32"})
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns="timestamp_utc")
    df.index = pd.DatetimeIndex(ts.values)
    df = df[df.index >= pd.Timestamp("2013-09-01")]         # engine starts 2013-10
    # true UTC -> Europe/Paris -> naive (matches sim_m5, probe: +1h/+2h DST, |Δ|=0)
    df.index = df.index.tz_localize("UTC").tz_convert("Europe/Paris").tz_localize(None)
    df = df.sort_index()
    m5 = df.resample("5min", label="left", closed="left").agg(
        high=("high", "max"), low=("low", "min"), close=("close", "last"),
        spread=("spread", "mean")).dropna(subset=["close"])
    hp = PT[sym]
    m5["lo_bid"] = m5["low"] - 0.5 * m5["spread"] * hp
    m5["hi_ask"] = m5["high"] + 0.5 * m5["spread"] * hp
    log(f"  {sym}: M1 {len(df):,} -> M5 {len(m5):,}")
    return m5[["close", "low", "high", "lo_bid", "hi_ask"]]


def main():
    OUT.mkdir(exist_ok=True)
    parts = {}
    for sym in LEGS:
        parts[sym] = build_leg(sym)
    panel = pd.concat(parts, axis=1)          # columns: (sym, field)
    panel.columns = [f"{s}_{f}" for s, f in panel.columns]
    panel.to_parquet(OUT / "lohi_m5_paris.parquet")
    log(f"panel saved {panel.shape} {panel.index.min()}..{panel.index.max()}")

    # ---- G-tz VALIDATION: Duka M5 close vs canonical sim_m5 close ----
    sim = pd.read_parquet(CACHE / "sim_m5_repaired.parquet")
    print("\n=== G-tz: Duka-M5-close vs canonical sim_m5 close (full overlap) ===")
    rows = []
    for sym in LEGS:
        d = panel[f"{sym}_close"]
        s = sim[sym]
        j = d.index.intersection(s.index)
        a, b = d.reindex(j).values, s.reindex(j).values
        ok = np.isfinite(a) & np.isfinite(b)
        diff = np.abs(a[ok] - b[ok])
        # relative in bps for comparability across instruments
        rel_bps = diff / np.abs(b[ok]) * 1e4
        rows.append(dict(leg=sym, n=int(ok.sum()),
                         med_abs=float(np.median(diff)),
                         p99_abs=float(np.percentile(diff, 99)),
                         med_bps=float(np.median(rel_bps)),
                         p99_bps=float(np.percentile(rel_bps, 99)),
                         frac_within_2bps=float((rel_bps <= 2).mean())))
    v = pd.DataFrame(rows)
    v.to_csv(OUT / "gtz_validation.csv", index=False)
    print(v.round(5).to_string(index=False))
    passed = (v.med_bps < 0.5).all()
    print(f"\nG-tz {'PASS' if passed else 'REVIEW'} "
          f"(median close diff < 0.5 bps all legs = same source)")


if __name__ == "__main__":
    main()
