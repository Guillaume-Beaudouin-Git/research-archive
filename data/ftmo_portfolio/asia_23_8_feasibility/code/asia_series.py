"""Shared ASIA_23_8 daily series builder for the FTMO feasibility sim.

Produces, per aday (entry UTC date):
  pos        VT scale (causal, native ~1.05x avg)            [= strategy_overnight]
  net_log    log window return net of round-trip spread       [= backtest()['net']]
  net_simple pos*(exp(onr)-1) - cost  (simple, for equity)
  low_frac   worst intraday mark-to-market excursion (simple, pos-scaled,
             net of half-spread) using H1 bar LOWS -> conservative barrier input
  raw_log    raw window log return (pre-VT, pre-cost) for the regime overlay

Also exposes align_to_book(series, book_dates): maps aday D -> book CET date D+1
(the window closes 07:00 UTC = 09:00 CET the next calendar day, exactly when the
book's first segment opens). No look-ahead: the position is fixed from data up to
the 23:00 UTC entry, strictly before the book day's 09:00 open.

Verifies the resample-label semantics Q4 depends on: net_log must equal the
strategy's own backtest net (sum-of-lr telescoping = log(price@07:00/price@23:00)).
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

# Load yt modules by explicit path under UNIQUE names: the cleanroom and
# yt_strategy_replications both ship a package called `engine`, which collide in
# sys.modules when this runs alongside engine_v22. data.py / strategy_overnight.py
# only need numpy/pandas at import time, so a path-based load is safe.
YT = Path("<HOME>/Desktop/Algo_claude/yt_strategy_replications")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


data = _load("yt_engine_data", YT / "engine" / "data.py")
SO = _load("yt_strategy_overnight", YT / "gold_research" / "strategy_overnight.py")

WINDOW_HOURS = [(SO.PARAMS["window_start_utc"] + i) % 24
                for i in range(SO.PARAMS["window_hours"])]   # [23,0,1,2,3,4,5,6]


def _load_h1():
    try:
        return data.load_h1("XAUUSD")
    except (FileNotFoundError, OSError):
        return data.build_deephist_h1("XAUUSD")


def build(spread_bps: float = 1.5) -> pd.DataFrame:
    h1 = _load_h1()[["open", "high", "low", "close"]].copy()
    lr = np.log(h1["close"] / h1["close"].shift(1))
    low_gap = np.log(h1["low"] / h1["close"])          # <= 0 within-bar dip vs bar close
    aday = (h1.index - pd.Timedelta(hours=SO.PARAMS["window_start_utc"])).normalize()
    df = pd.DataFrame({"lr": lr, "low_gap": low_gap, "aday": aday,
                       "hour": h1.index.hour, "ts": h1.index}).dropna()
    df = df[df["hour"].isin(WINDOW_HOURS)].sort_values("ts")

    # cumulative log return from window base (close@22:00 = denominator of first lr)
    g = df.groupby("aday", sort=True)
    df["cum"] = g["lr"].cumsum()                        # c_k = log(close_k / P0)
    df["low_path"] = df["cum"] + df["low_gap"]          # log(low_k / P0)
    cnt = g["lr"].transform("count")
    df = df[cnt == SO.PARAMS["window_hours"]]           # complete windows only

    onr = df.groupby("aday")["lr"].sum()                # = SO.overnight_returns
    low_excursion = df.groupby("aday")["low_path"].min().clip(upper=0.0)  # <=0, simple-ish in log
    pos = SO.vol_target_scale(onr)
    sp = spread_bps * 1e-4
    net_log = pos * onr - pos.abs() * sp                # == backtest()['net']
    net_simple = pos * (np.exp(onr) - 1.0) - pos.abs() * sp
    low_frac = pos * (np.exp(low_excursion) - 1.0) - pos.abs() * (sp / 2.0)
    low_frac = np.minimum(low_frac, net_simple)         # low can't be above the close P&L

    out = pd.DataFrame({"pos": pos, "raw_log": onr, "net_log": net_log,
                        "net_simple": net_simple, "low_frac": low_frac}).dropna()

    # --- verification: net_log must match the strategy's own backtest (label semantics) ---
    bt = SO.backtest(h1, spread_bps=spread_bps, swap_bps=0.0)["net"]
    j = out["net_log"].reindex(bt.index)
    err = float(np.nanmax(np.abs((j - bt).dropna())))
    assert err < 1e-9, f"net_log mismatch vs backtest: {err}"
    out.attrs["verify_err"] = err
    return out


def align_to_book(series: pd.Series, book_dates: pd.DatetimeIndex) -> np.ndarray:
    """aday D -> book CET date D+1 (window closes 09:00 CET next day). Returns array
    aligned to book_dates, 0 where ASIA did not trade."""
    shifted = series.copy()
    shifted.index = shifted.index + pd.Timedelta(days=1)
    # collapse to date, then reindex onto the book's trading dates
    shifted = shifted.groupby(shifted.index.normalize()).sum()
    return shifted.reindex(book_dates).fillna(0.0).to_numpy(float)


if __name__ == "__main__":
    for sp in (1.0, 1.5, 2.0):
        d = build(sp)
        print(f"spread {sp}bp: n={len(d)}  verify_err={d.attrs['verify_err']:.2e}  "
              f"net mean {d['net_simple'].mean()*1e4:+.2f}bp  "
              f"low mean {d['low_frac'].mean()*1e4:+.1f}bp  "
              f"worst low {d['low_frac'].min()*100:.2f}%  worst net {d['net_simple'].min()*100:.2f}%")
    # label-semantics sanity: the window must be 23:00->07:00 UTC (entry 23:00).
    d = build(1.5)
    print(f"\naday range {d.index[0].date()} -> {d.index[-1].date()}  ({len(d)} days)")
    print("verify_err≈0 confirms sum-of-lr telescopes to log(px@07:00/px@23:00) "
          "=> window is 23:00->07:00 UTC, entry 23:00 (label-left resample). "
          "intraday low uses H1 bar lows (conservative).")
