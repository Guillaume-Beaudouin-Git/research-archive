"""Local trial ledger for honest DSR (PREREG section 8). NOT the FTMO register.
Every distinct signal/system config that produces a Sharpe is appended with
dsr_count=True; cost-stress / execution variants of the same signal use
dsr_count=False so they don't inflate the multiple-testing penalty."""
from __future__ import annotations
import csv
from pathlib import Path
import pandas as pd

TRIALS = Path(__file__).resolve().parent / "trials_log.csv"
FIELDS = ["trial_id", "phase", "name", "sharpe", "cagr", "maxdd", "n_trades", "dsr_count", "notes"]


def log_trial(phase, name, sharpe, cagr=None, maxdd=None, n_trades=None, dsr_count=True, notes=""):
    rows = []
    if TRIALS.exists():
        rows = pd.read_csv(TRIALS).to_dict("records")
    tid = len(rows) + 1
    row = dict(trial_id=tid, phase=phase, name=name,
               sharpe=round(float(sharpe), 4) if sharpe is not None else "",
               cagr=round(float(cagr), 4) if cagr is not None else "",
               maxdd=round(float(maxdd), 4) if maxdd is not None else "",
               n_trades=n_trades if n_trades is not None else "",
               dsr_count=bool(dsr_count), notes=notes)
    write_header = not TRIALS.exists()
    with open(TRIALS, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        w.writerow(row)
    return tid


def reset():
    if TRIALS.exists():
        TRIALS.unlink()
