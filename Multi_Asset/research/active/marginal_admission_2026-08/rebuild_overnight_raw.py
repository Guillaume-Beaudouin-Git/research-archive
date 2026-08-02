"""Rebuild the overnight-drift sleeves WITHOUT the 0.5/99.5 winsorisation.

``overnight_futures_2026-07/code/step3_performance.py:47`` clips the window return
inside ``tradable_series`` — i.e. inside the *constructor*, so every consumer of
``results/step3_sleeve_series.csv`` inherits truncated tails. Harmless for a Sharpe,
disqualifying for a barrier problem: the FTMO daily stop is a barrier on the left
tail of one day, and clipping removes exactly the observations that hit it.

This module reuses that study's own spec (same reopen hour, same window length,
same causal vol target, same measured futures cost) with the clip removed, and
reports how much of the tail the clip was hiding.

Read-only against the main working directory; nothing here is a new backtest — it
is the same measurement with a censoring step deleted.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
OVN = MAIN / "Multi_Asset/research/active/overnight_futures_2026-07/code"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

sys.path.insert(0, str(OVN))
from common import SLEEVES, us_dst, vol_target  # noqa: E402
from step1c_gap_decomposition import REOPEN_ET, WINDOW_HOURS, load_m1, price_at  # noqa: E402

H = np.int64(3_600_000_000_000)
# measured futures round-trip, step 0 of the source study (bps of notional)
COST_BPS = {"GOLD": 0.66, "SILVER": 1.15, "WTI": 3.67, "SOYBEAN": 1.53}
SLEEVE_LIST = ["GOLD", "SILVER", "WTI", "SOYBEAN"]


def raw_window_return(name: str) -> pd.Series:
    """Identical to ``step3_performance.tradable_series`` minus the final clip."""
    sp = SLEEVES[name]
    df = load_m1(sp["cfd"], sp["sample_start"])
    ts = pd.DatetimeIndex(df["ts"])
    et = ts - pd.to_timedelta(np.where(us_dst(ts), 4, 5), unit="h")
    keys = et.asi8
    vals = df["close"].to_numpy()
    ro, hours = REOPEN_ET[name], WINDOW_HOURS[name]
    sess = pd.DatetimeIndex(np.unique(pd.DatetimeIndex(et).normalize()))
    base = (sess + pd.Timedelta(hours=ro)).asi8
    p0 = price_at(vals, keys, base, "first", 20)
    p1 = price_at(vals, keys, base + hours * H, "last", 30)
    s = pd.Series(np.log(p1 / p0), index=sess).dropna()
    return s[np.isfinite(s.to_numpy())]


def net_sleeve(win: pd.Series, cost_bps: float) -> pd.Series:
    """Causal vol target + measured cost, as in the source study."""
    pos = vol_target(win)
    net = (pos * win - pos.abs() * cost_bps * 1e-4).dropna()
    return net[net.index >= win.index[20]]


def tail_report(raw: pd.Series) -> dict:
    lo, hi = raw.quantile([0.005, 0.995])
    clipped = raw.clip(lo, hi)
    return {
        "n": int(len(raw)),
        "raw_min_bps": float(raw.min() * 1e4),
        "clip_min_bps": float(clipped.min() * 1e4),
        "raw_max_bps": float(raw.max() * 1e4),
        "clip_max_bps": float(clipped.max() * 1e4),
        "raw_kurt": float(raw.kurtosis()),
        "clip_kurt": float(clipped.kurtosis()),
        "n_obs_censored": int((raw < lo).sum() + (raw > hi).sum()),
    }


if __name__ == "__main__":
    CACHE.mkdir(exist_ok=True)
    out, rows = {}, []
    for name in SLEEVE_LIST:
        raw = raw_window_return(name)
        rows.append(dict(sleeve=name, **tail_report(raw)))
        out[name] = net_sleeve(raw, COST_BPS[name])
    panel = pd.DataFrame(out)
    panel.to_parquet(CACHE / "overnight_raw_sleeves.parquet")
    rep = pd.DataFrame(rows)
    rep.to_csv(HERE / "winsorisation_audit.csv", index=False)
    print(rep.to_string(index=False))
    print("\nsaved cache/overnight_raw_sleeves.parquet", panel.shape)
