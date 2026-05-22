"""
Run Phase 1.5 IC analysis (Tasks 3, 4, 5, 6) once data is available.
Usage: python3 run_all.py
Prerequisites: fetch_data.py must have completed successfully.
"""

from __future__ import annotations
import subprocess
import sys
from pathlib import Path

RAW_DIR = Path(__file__).parents[4] / "data" / "raw"
SCRIPT_DIR = Path(__file__).parent
PYTHON = sys.executable

REQUIRED_FILES = [
    RAW_DIR / "dukascopy_EURUSD_2020_2024.parquet",
    RAW_DIR / "dukascopy_GBPUSD_2020_2024.parquet",
]

def check_data() -> bool:
    missing = [p for p in REQUIRED_FILES if not p.exists()]
    if missing:
        print(f"MISSING data files:")
        for p in missing:
            print(f"  {p.name}")
        print("Run fetch_data.py first.")
        return False
    for p in REQUIRED_FILES:
        import pandas as pd
        n = len(pd.read_parquet(p))
        print(f"  {p.name}: {n:,} bars")
    return True


def run(script: str) -> bool:
    print(f"\n{'='*60}")
    print(f"Running {script}...")
    result = subprocess.run([PYTHON, str(SCRIPT_DIR / script)], capture_output=False)
    ok = result.returncode == 0
    print(f"{'OK' if ok else 'FAILED'}: {script} (exit code {result.returncode})")
    return ok


def main():
    print("Phase 1.5 IC Analysis — run_all.py")
    print(f"Python: {PYTHON}")
    if not check_data():
        sys.exit(1)

    steps = [
        ("ic_angle_a.py", "Task 3+4: London ORB IC + EUR/GBP correlation"),
        ("ic_angle_b.py", "Task 5: News-Fade IC"),
        ("synthesize.py",  "Task 6: Synthesis + decision"),
    ]
    all_ok = True
    for script, desc in steps:
        print(f"\n>>> {desc}")
        ok = run(script)
        all_ok = all_ok and ok
        if not ok:
            print(f"STOP: {script} failed. Check output above.")
            sys.exit(1)

    if all_ok:
        print("\n" + "="*60)
        print("Phase 1.5 COMPLETE. Check _ic_feasibility.md for synthesis.")


if __name__ == "__main__":
    main()
