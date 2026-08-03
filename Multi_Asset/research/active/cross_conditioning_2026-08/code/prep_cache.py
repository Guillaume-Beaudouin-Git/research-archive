"""Cache the RAW M1 series this study needs, with tick_volume (the liquidity state).

Private cache dir, owner-stamped.  No data blob ever enters git.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common_xcond import M1_COLS, cache_dir, load_m1_raw  # noqa: E402

SERIES = ("XAUUSD", "US100", "US500", "US30")

if __name__ == "__main__":
    C = cache_dir()
    for name in SERIES:
        df = load_m1_raw(name)
        assert list(df.columns) == M1_COLS, (name, list(df.columns))
        df.to_parquet(C / f"{name}_M1.parquet")
        nz = float((df["tick_volume"] > 0).mean())
        print(f"{name:7s} rows={len(df):>10,}  {df.index.min().date()}..{df.index.max().date()}"
              f"  tick_volume>0: {nz:.3%}")
