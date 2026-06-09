"""
run_all.py — execute the full program (Phases 0 -> 2) and rebuild the report.
Usage: python3 run_all.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [
    ("Phase 0  — theory validation",      "run_phase0_theory.py"),
    ("Phase 0b — CFD cost reconciliation", "run_phase0b_costs.py"),
    ("Phase 1  — feasibility",             "run_phase1_feasibility.py"),
    ("Phase 2  — validation & verdict",    "run_phase2_validation.py"),
    ("Addendum A — EURUSD edge forensics", "research_eurusd_edge.py"),
    ("Addendum B — Family-3 index pairs",  "run_family3_pairs.py"),
    ("Addendum C — Family-4 XAUUSD fade",  "run_family4_xau.py"),
    ("Addendum D — Family-5 overnight",    "run_overnight.py"),
    ("Addendum E — Family-6 BTC intraday", "run_crypto.py"),
    ("Report   — assemble PDF",            "make_report.py"),
]

if __name__ == "__main__":
    for label, script in STEPS:
        print(f"\n{'='*80}\n>>> {label}  ({script})\n{'='*80}")
        r = subprocess.run([sys.executable, str(HERE / script)], cwd=str(HERE))
        if r.returncode != 0:
            print(f"!! {script} exited {r.returncode}")
            sys.exit(r.returncode)
    print("\nAll phases complete. See FTMO_Alpha_Program_Phases0-2_Report.pdf")
