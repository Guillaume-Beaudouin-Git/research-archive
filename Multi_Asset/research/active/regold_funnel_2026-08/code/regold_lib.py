"""Shared plumbing for the gold re-cost pass (regold_funnel_2026-08).

Re-runs the 16 XAUUSD-touching specs of the 142-strategy FTMO funnel
(PropFirms/ftmo/program_2026-06/top10_test/) with a MEASURED cost denominator
instead of the catalog one. Nothing else changes: same spec, same window,
same signal, same evaluation pipeline.

Two shims are required and are documented, not hidden:

1. `load_index_m1` in the original `data_loaders.py` reads
   `data/panels/m5_indices/{sym}_M1.csv`. Those CSVs were deleted in the
   2026-06-10 P2 cleanup. The identical series survives as
   `data/panels/m5_indices/{sym}_m1_panel.parquet`. Reproduction of the
   original catalog-cost numbers is asserted, not assumed (see run_recost.py).

2. `Forex/data/cache/dukascopy_m5` was also deleted, so XAGUSD is
   unavailable -> the XAUUSD-XAGUSD pair spec cannot be re-run at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
TOP10 = MAIN / "PropFirms/ftmo/program_2026-06/top10_test"
CACHE = MAIN / "data/ftmo_portfolio/cache"
PANELS = MAIN / "data/panels/m5_indices"

sys.path.insert(0, str(TOP10))

import data_loaders as _dl  # noqa: E402


# ---------------------------------------------------------------------------
# Shim 1: M1 CSV -> M1 parquet panel (same series, CSV deleted in P2 cleanup)
# ---------------------------------------------------------------------------

_ORIG_LOAD_M1 = _dl.load_index_m1


def _load_index_m1_parquet(symbol: str) -> pd.DataFrame:
    csv = PANELS / f"{symbol}_M1.csv"
    if csv.exists():
        return _ORIG_LOAD_M1(symbol)
    pq = PANELS / f"{symbol}_m1_panel.parquet"
    if not pq.exists():
        raise FileNotFoundError(str(pq))
    df = pd.read_parquet(pq)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    return df[["open", "high", "low", "close"]].sort_index()


_dl.load_index_m1 = _load_index_m1_parquet

import batch_strategies as bs  # noqa: E402
import framework as fw  # noqa: E402

bs.load_index_m1 = _load_index_m1_parquet


# ---------------------------------------------------------------------------
# Cost denominators
# ---------------------------------------------------------------------------

# Catalog values actually used by the funnel (framework.py:29).
CATALOG_RT = dict(fw.FTMO_COST_BPS_RT)
CATALOG_SWAP = dict(fw.FTMO_SWAP_BPS_PER_NIGHT)

# Measured components (see COST_AUDIT.md and measure_costs.py).
METAL_COMM_RT_BPS = 2 * 7.0e-6 * 1e4          # config.py METAL_COMMISSION_SIDE
SLIP_SIDE_MODEL = 0.50                         # research_panel.py provision
SLIP_SIDE_MEDIAN = 0.10                        # reconcile fills, realized median
SLIP_SIDE_P95 = 1.485                          # reconcile fills, US100 p95
SLIP_SIDE_MAX = 3.67                           # reconcile fills, US100 max


def measured_costs() -> dict:
    """Measured gold/silver RT cost and asymmetric swap, from the caches.

    Windows are chosen to match the funnel's own sample (M1 panel starts
    2020-01), NOT the full 2000+ history, so the denominator describes the
    period actually screened.
    """
    out = {}
    for sym in ("XAUUSD", "XAGUSD"):
        d = pd.read_parquet(CACHE / f"{sym}_daily_cet.parquet")
        sp = d["spread_med_bps"]
        out[sym] = {
            "spread_med_tail750": float(sp.tail(750).median()),
            "spread_med_2020": float(sp.loc["2020":].median()),
            "spread_p75_2020": float(d["spread_p75_bps"].loc["2020":].median()),
            "zero_frac_2020": float((sp.loc["2020":] == 0).mean()),
        }
    swL = pd.read_parquet(CACHE / "panel_swapL.parquet")
    swS = pd.read_parquet(CACHE / "panel_swapS.parquet")
    for sym in ("XAUUSD", "XAGUSD"):
        out[sym]["swap_long_med_2020"] = float(swL[sym].loc["2020":].median())
        out[sym]["swap_short_med_2020"] = float(swS[sym].loc["2020":].median())
        out[sym]["swap_long_mean_full"] = float(swL[sym].mean())
        out[sym]["swap_short_mean_full"] = float(swS[sym].mean())
    return out


class CostModel:
    """A named cost denominator applied to a trade ledger.

    rt_bps: round-trip transaction cost in bps of notional.
    swap_long/swap_short: bps per night held, by leg sign (negative = paid).
    """

    def __init__(self, name: str, rt_bps: float, swap_long: float,
                 swap_short: float, note: str = ""):
        self.name = name
        self.rt_bps = rt_bps
        self.swap_long = swap_long
        self.swap_short = swap_short
        self.note = note

    def apply(self, trades: pd.DataFrame) -> pd.DataFrame:
        """Re-price an existing ledger. gross_bps, side and n_nights are kept
        verbatim; only cost_bps / swap_bps / net_bps are recomputed."""
        t = trades.copy()
        t["cost_bps"] = self.rt_bps
        sw_per_night = np.where(t["side"] > 0, self.swap_long, self.swap_short)
        t["swap_bps"] = sw_per_night * t["n_nights"].astype(float)
        t["net_bps"] = t["gross_bps"] - t["cost_bps"] + t["swap_bps"]
        return t


# ---------------------------------------------------------------------------
# FTMO barrier simulator, corrected
# ---------------------------------------------------------------------------

def ftmo_mc_static(daily_pnl_pct: pd.Series, n_runs: int = 5000,
                   max_days_per_phase: int = 365, seed: int = 7,
                   block_len: int = 5, extra_cost_per_active_day: float = 0.0):
    """Two-phase FTMO MC with a STATIC -10% floor.

    framework.ftmo_montecarlo uses `max(1 - MLL, hwm_eod - MLL)`, i.e. a
    ratcheting floor. That mechanism exists only on the 1-step product
    (confirmed 2026-08-01); on the 2-step the max-loss floor is static at
    -10% of INITIAL capital. The ratchet makes the barrier strictly harder,
    so the original funnel understated p(pass) for every candidate.

    `extra_cost_per_active_day` subtracts a fixed cost (fraction of capital)
    from every day that traded, used to provision the slippage TAIL for the
    barrier without touching the expectation used elsewhere.

    Daily-loss-limit is evaluated on END-OF-DAY equity: with a daily ledger
    there is no intraday path. This is optimistic and is reported as such.
    """
    rng = np.random.default_rng(seed)
    pnl = daily_pnl_pct.dropna().values
    if len(pnl) < 30:
        return dict(p_pass_p1=np.nan, p_pass_p1_p2=np.nan, p_bust=np.nan,
                    med_days_p1=np.nan, med_days_total=np.nan, n_runs=0)
    active = pnl != 0.0
    if extra_cost_per_active_day:
        pnl = pnl - active * extra_cost_per_active_day

    n = len(pnl)
    n_blocks = max(1, max_days_per_phase // block_len + 1)
    DLL, MLL = fw.FTMO_DLL_PCT, fw.FTMO_MLL_PCT

    def _phase(target):
        starts = rng.integers(0, n, size=n_blocks)
        path = np.concatenate([pnl[s: s + block_len] for s in starts])[:max_days_per_phase]
        eq, dll_floor = 1.0, 1.0 - DLL
        mll_floor = 1.0 - MLL            # STATIC
        for day, pct in enumerate(path):
            eq_next = eq * (1.0 + pct)
            if eq_next < dll_floor:
                return None, "dll", day + 1
            if eq_next < mll_floor:
                return None, "mll", day + 1
            eq = eq_next
            dll_floor = eq - DLL
            if eq >= 1.0 + target:
                return day + 1, None, day + 1
        return None, "timeout", len(path)

    p1_ok = p12_ok = bust = 0
    d1, dtot = [], []
    for _ in range(n_runs):
        day1, why1, _ = _phase(fw.FTMO_P1_TARGET)
        if day1 is None:
            if why1 in ("dll", "mll"):
                bust += 1
            continue
        p1_ok += 1
        d1.append(day1)
        day2, why2, _ = _phase(fw.FTMO_P2_TARGET)
        if day2 is not None:
            p12_ok += 1
            dtot.append(day1 + day2)

    return dict(
        p_pass_p1=p1_ok / n_runs,
        p_pass_p1_p2=p12_ok / n_runs,
        p_bust=bust / n_runs,
        med_days_p1=float(np.median(d1)) if d1 else np.nan,
        med_days_total=float(np.median(dtot)) if dtot else np.nan,
        n_runs=n_runs,
    )
