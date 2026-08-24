"""Volet 0 probe: pin tz offset (canonical sim_m5 MT5 vs deep_history true-UTC),
bar-label convention, spread-unit calibration. Read-only; no engine mutation."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
CACHE = MAIN / "data/ftmo_portfolio/cache"
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]

# ---- canonical panel -------------------------------------------------------
sim = pd.read_parquet(CACHE / "sim_m5_repaired.parquet")
print("=== sim_m5_repaired ===")
print("cols:", list(sim.columns))
print("index dtype:", sim.index.dtype, "| tz:", sim.index.tz)
print("range:", sim.index.min(), "->", sim.index.max(), "| n=", len(sim))
# bars-per-day + typical minutes
mins = sim.index.hour * 60 + sim.index.minute
print("min-of-day range:", mins.min(), "->", mins.max(),
      "| unique step(min):", int(np.median(np.diff(np.unique(mins)))))


def load_deep(sym, tag):
    df = pd.read_csv(DATA / f"{sym}_{tag}.csv", header=None,
                     names=["ts", "open", "high", "low", "close", "tv", "spread", "rv"])
    df["ts"] = pd.to_datetime(df["ts"], format="%Y.%m.%d %H:%M:%S")
    return df.set_index("ts")


def offset_scan(tag, day):
    simday = sim.loc[day, "USDJPY"].dropna()
    deep = load_deep("USDJPY", tag)["close"]
    best = None
    for off_min in range(-4 * 60, 4 * 60 + 1, 15):
        shifted = deep.copy()
        shifted.index = shifted.index + pd.Timedelta(minutes=off_min)
        m5 = shifted.resample("5min", label="left", closed="left").last().dropna()
        j = simday.index.intersection(m5.index)
        if len(j) < 100:
            continue
        d = np.abs(simday.reindex(j).values - m5.reindex(j).values)
        mad = np.nanmedian(d)
        if best is None or mad < best[1]:
            best = (off_min, mad, len(j))
    return best


for tag, day in [("20240214", "2024-02-14"), ("20240814", "2024-08-14")]:
    b = offset_scan(tag, day)
    print(f"\n[{day}] best USDJPY offset = {b[0]:+d} min (UTC+{b[0]/60:+.2f}h) "
          f"median|Δ|={b[1]:.5f} yen, matched {b[2]} bars")

# ---- bar-label convention check (winter day, best offset) -------------------
print("\n=== bar-label convention (2024-02-14) ===")
simday = sim.loc["2024-02-14", "USDJPY"].dropna()
deep = load_deep("USDJPY", "20240214")["close"]
b = offset_scan("20240214", "2024-02-14")[0]
deep.index = deep.index + pd.Timedelta(minutes=b)
for label, closed in [("left", "left"), ("right", "right")]:
    m5 = deep.resample("5min", label=label, closed=closed).last().dropna()
    j = simday.index.intersection(m5.index)
    if len(j) > 50:
        mad = np.nanmedian(np.abs(simday.reindex(j).values - m5.reindex(j).values))
        print(f"  label={label} closed={closed}: matched {len(j)} median|Δ|={mad:.6f}")

# ---- spread-unit calibration ------------------------------------------------
print("\n=== spread units (deep_history 'spread' col, day-median) vs known typical ===")
for sym in LEGS:
    for tag, day in [("20240214", "winter"), ("20240814", "summer")]:
        d = load_deep(sym, tag)
        sp_med = d["spread"].median()
        px = d["close"].median()
        print(f"  {sym:7s} {day}: spread_med={sp_med:.0f} raw | close~{px:.2f} "
              f"| if pts=1e-5: {sp_med*1e-5:.5f} | if 1pt=digit: see MEASURED_SPECS")
