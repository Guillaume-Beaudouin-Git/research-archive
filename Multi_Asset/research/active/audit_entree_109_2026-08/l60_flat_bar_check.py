"""L60 honesty check on the corpus's OWN daily OHLC store: fraction of degenerate
(high==low) daily bars per instrument, before trusting range-dependent ambiguity
counts. A flat bar (range=0) can never register a dual-breakout ambiguity (both
levels can't be touched with zero range) -- so flat bars bias the MEASURED
ambiguity rate DOWN, not up; but a print-settlement-contaminated series is still
unusable for this corpus's OWN trades (its reported expR/Sharpe already bakes in
whatever quality the series has -- flagged here for transparency, not re-litigated)."""
import os
import numpy as np, pandas as pd

DAILY_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/archived/oxfordstrat_109_audit/ohlc"
rows = []
for f in sorted(os.listdir(DAILY_DIR)):
    if not f.endswith(".parquet"):
        continue
    t = f[:-8]
    df = pd.read_parquet(os.path.join(DAILY_DIR, f))
    flat = (df["high"] == df["low"])
    rows.append(dict(instr=t, n_bars=len(df), flat_frac=float(flat.mean()),
                      flat_and_close_frac=float(((df["high"]==df["low"]) & (df["low"]==df["close"])).mean())))
out = pd.DataFrame(rows).sort_values("flat_frac", ascending=False)
out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "l60_flat_bar_check.csv"), index=False)
print(out.to_string())
