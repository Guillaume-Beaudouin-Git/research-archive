"""X* calibration (pre-registered, outcome-blind): pick the band X that cuts J1
turnover ~50% on the BASELINE-recorded (j1_prev, j1_tgt_raw) pairs at segment 4,
replayed per attempt with own-state hysteresis. Also computes the iso-leverage
factors FACT_A / FACT_C from baseline day records (frozen v2.1 formula).

Writes band_X.json + factors.json. Run AFTER `run_arms.py baseline`, BEFORE any variant.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
GRID = [0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30]

df = pd.read_parquet(HERE / "records" / "baseline_days.parquet")
df = df.sort_values(["cohort", "attempt", "phase", "date"])


def replay_turnover(X):
    tot = 0.0
    for _, g in df.groupby(["cohort", "attempt", "phase"], sort=False):
        cur = 0.0
        for raw in g["j1_tgt_raw"].to_numpy():
            if not np.isfinite(raw):
                continue
            if (X > 0.0 and cur != 0.0 and raw != 0.0 and cur * raw > 0
                    and abs(raw - cur) <= X * abs(raw)):
                continue                     # hold, no trade
            tot += abs(raw - cur)
            cur = raw
    return tot


t0 = replay_turnover(0.0)
rows = []
for X in GRID:
    tx = replay_turnover(X)
    rows.append(dict(X=X, turnover=tx, ratio=tx / t0))
    print(f"X={X:5.3f}  ratio={tx/t0:.3f}", flush=True)
tab = pd.DataFrame(rows)
x_star = float(tab.iloc[(tab.ratio - 0.5).abs().argmin()].X)
print(f"X* = {x_star} (target ratio 0.50, achieved {tab.set_index('X').ratio[x_star]:.3f})")
(HERE / "band_X.json").write_text(json.dumps(
    dict(X_star=x_star, target_ratio=0.5, grid=rows,
         note="offline replay on baseline s4 (prev,raw-target) pairs; "
              "eq-path feedback and intraday flattens ignored (pre-registered)"),
    indent=2, default=float))

# --- iso-leverage factors (frozen v2.1 formula, on v2.2 baseline day records)
book = df[["gold", "jpy", "on_us", "on_ger"]].sum(axis=1) + df["orb"] + df["micro"] + df["fix"]
FACT_A = float(book.std() / (book - 0.5 * df["jpy"]).std())
FACT_C = float(book.std() / (book - df["jpy"]).std())
print(f"FACT_A={FACT_A:.4f}  FACT_C={FACT_C:.4f}")
(HERE / "factors.json").write_text(json.dumps(
    dict(FACT_A=FACT_A, FACT_C=FACT_C,
         formula="std(book)/std(book - removed_component), v2.2 baseline day records",
         FACT_B="measured post B_raw: std(book_base)/std(book_B_raw); "
                "|FACT_B-1|<=0.01 => B_iso == B_raw (pre-registered)"),
    indent=2))
