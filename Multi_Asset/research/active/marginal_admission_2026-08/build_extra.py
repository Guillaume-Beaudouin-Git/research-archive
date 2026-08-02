"""Convert trade-level and event-level ledgers into daily calendar series.

Two shortlist edges of the inventory saved a ledger but no daily return stream, so
the marginal test cannot reach them as-is:

* **E012 / E013 Gap Pattern (A and B)** — ``gap_pattern_rehab_2026-07`` stores
  per-trade ``netR`` with entry and exit dates. Killed on an *invalidated* DSR and
  on "no longer beats a matched buy-and-hold", i.e. a challenge lens applied to a
  sleeve candidate. It is the only two-sided non-beta survivor of the 109 audit.
* **E020 Treasury auction cycle** — ``treasury_auction_2026-07`` stores 251 events
  with ``post_bps``. Skipped at gate-0 for years because bonds are not FTMO-tradable.

Attribution convention, stated because it matters for a barrier problem: a trade's
P&L is booked on its **exit** date. That is causal (nothing is known before the exit)
but it makes the daily stream lumpier than the true equity path, which *understates*
the number of days the sleeve is active and *overstates* single-day magnitude. For a
daily-stop barrier this is the conservative direction on frequency and the
anti-conservative direction on tail, so both Delta p(pass) figures below carry that
caveat explicitly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def trades_to_daily(f: Path, col: str = "netR") -> pd.Series:
    t = pd.read_parquet(f)
    ex = pd.DatetimeIndex(pd.to_datetime(t["exit"])).normalize()
    s = pd.Series(t[col].to_numpy(), index=ex).groupby(level=0).sum()
    idx = pd.bdate_range(s.index.min(), s.index.max())
    return s.reindex(idx).fillna(0.0)


def auction_to_daily() -> pd.Series:
    e = pd.read_parquet(MAIN / "Multi_Asset/research/active/treasury_auction_2026-07/data/events_10y_ZN.parquet")
    d = pd.DatetimeIndex(pd.to_datetime(e["auction_date"])).normalize()
    s = pd.Series(e["post_bps"].to_numpy() * 1e-4, index=d).groupby(level=0).sum()
    idx = pd.bdate_range(s.index.min(), s.index.max())
    return s.reindex(idx).fillna(0.0)


if __name__ == "__main__":
    CACHE.mkdir(exist_ok=True)
    gp = MAIN / "Multi_Asset/research/active/gap_pattern_rehab_2026-07"
    out = {
        "gapA_S035_point": trades_to_daily(gp / "s035_trades_point.parquet"),
        "gapB_S036_point": trades_to_daily(gp / "s036_trades_point.parquet"),
        "gapA_S035_best": trades_to_daily(gp / "s035_trades_best.parquet"),
        "auction_ZN_post": auction_to_daily(),
    }
    df = pd.DataFrame(out)
    df.to_parquet(CACHE / "extra_sleeves.parquet")
    for k, v in out.items():
        v = v.dropna()
        print(f"{k:18s} n={len(v)} active={(v != 0).mean():.3f} "
              f"SR={v.mean() / v.std() * np.sqrt(252):+.3f} "
              f"{v.index.min().date()}->{v.index.max().date()}")
