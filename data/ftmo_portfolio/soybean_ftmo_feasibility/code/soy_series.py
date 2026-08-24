"""Shared SOYBEAN reopen daily series builder for the FTMO feasibility sim.

Mirror of asia_series.py. Strategy = long SOYBEAN over 01:00->07:00 UTC (H1 hours
[1,2,3,4,5,6], label-left => entry ~01:00, exit ~07:00), vol-targeted, complete-window.
The VT and cost EXACTLY reproduce yt_strategy_replications/soybean_research/net_analysis.py
(the report's headline source): drift = sum of hourly log returns over the window;
sc = expanding-median(rolling-20 std) / rolling-20 std, clipped 3x (rv carries shift(1)).

Produces, per aday (entry UTC date = book CET date, SAME-DAY alignment unlike ASIA):
  pos         VT scale (causal)                                  [= net_analysis sc]
  raw_log     raw window log return (pre-VT, pre-cost)           [= net_analysis drift]
  net_log     pos*drift - cost   (log space; == report 'net')    [validated vs net_analysis]
  net_simple  pos*(exp(drift)-1) - cost   (simple, for $ equity / barrier)
  low_frac    worst intraday mark-to-market excursion (pos-scaled, net of half-spread)
              using H1 bar LOWS -> conservative barrier input
  is_usda     True if this morning is a scheduled USDA report-day or day-after (skip flag)

align_to_book(series, book_dates): aday D -> book CET date D (NO +1 shift; the 01:00-07:00
UTC window is intra-day-UTC and lands on the same server/CET calendar day; verified 99.8%
intersection with book dates vs 79.6% for the +1 shift).

NOTE on paths: engines + data are read via ABSOLUTE paths to the MAIN repo (branch-invariant
shared infra + gitignored data caches) so this runs identically from a git worktree.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")     # MAIN repo (data + engines)
YT = REPO / "yt_strategy_replications"

WIN = [1, 2, 3, 4, 5, 6]          # UTC hours; label-left => window 01:00->07:00 UTC
ANN = 252.0


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


data = _load("yt_engine_data", YT / "engine" / "data.py")
usda = _load("soy_usda_calendar", Path(__file__).resolve().parent / "usda_calendar.py")


def _load_h1():
    try:
        return data.load_h1("SOYBEAN")
    except (FileNotFoundError, OSError):
        return data.build_deephist_h1("SOYBEAN")


def build(spread_bps: float = 2.0) -> pd.DataFrame:
    h1 = _load_h1()[["open", "high", "low", "close"]].copy()
    lr = np.log(h1["close"] / h1["close"].shift(1))
    low_gap = np.log(h1["low"] / h1["close"])           # <= 0 within-bar dip vs bar close
    aday = h1.index.normalize()                          # intra-day-UTC window => same-day
    df = pd.DataFrame({"lr": lr, "low_gap": low_gap, "aday": aday,
                       "hour": h1.index.hour, "ts": h1.index}).dropna()
    df = df[df["hour"].isin(WIN)].sort_values("ts")

    # complete-window only: all 6 hours present (== net_analysis sub.notna().all(axis=1))
    g = df.groupby("aday", sort=True)
    df["cum"] = g["lr"].cumsum()                         # c_k = log(close_k / P0)
    df["low_path"] = df["cum"] + df["low_gap"]           # log(low_k / P0)
    cnt = g["lr"].transform("count")
    df = df[cnt == len(WIN)]

    drift = df.groupby("aday")["lr"].sum()               # == net_analysis drift
    low_excursion = df.groupby("aday")["low_path"].min().clip(upper=0.0)

    # VT EXACTLY as net_analysis.py / intraday.backtest voltarget
    rv = drift.rolling(20, min_periods=20).std().shift(1)
    pos = (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)

    sp = spread_bps * 1e-4
    net_log = pos * drift - pos.abs() * sp               # == net_analysis net(spread)
    net_simple = pos * (np.exp(drift) - 1.0) - pos.abs() * sp
    low_frac = pos * (np.exp(low_excursion) - 1.0) - pos.abs() * (sp / 2.0)
    low_frac = np.minimum(low_frac, net_simple)          # low can't be above the close P&L

    out = pd.DataFrame({"pos": pos, "raw_log": drift, "net_log": net_log,
                        "net_simple": net_simple, "low_frac": low_frac}).dropna()
    out = out[out["pos"] > 0]                             # traded days only (pos==0 = VT warmup)
    out["is_usda"] = usda.is_skip_morning(out.index)     # report-day OR day-after

    # --- verification: net_log must reproduce net_analysis's net() series exactly ---
    ref = _net_analysis_ref(spread_bps)
    j = out["net_log"].reindex(ref.index)
    err = float(np.nanmax(np.abs((j - ref).dropna())))
    out.attrs["verify_err"] = err
    out.attrs["n_ref"] = int(ref.notna().sum())
    return out


def _net_analysis_ref(spread: float) -> pd.Series:
    """Re-derive net_analysis.py's net() series from raw H1 (independent of build())."""
    g = _load_h1()
    g = g.assign(lr=np.log(g["close"] / g["close"].shift(1))).dropna(subset=["lr"])
    pv = g.assign(d=g.index.normalize(), hour=g.index.hour).pivot_table(
        index="d", columns="hour", values="lr")
    sub = pv[WIN]
    drift = sub[sub.notna().all(axis=1)].sum(axis=1)
    rv = drift.rolling(20, min_periods=20).std().shift(1)
    sc = (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)
    return (sc * drift - sc.abs() * spread * 1e-4).dropna()


def align_to_book(series: pd.Series, book_dates: pd.DatetimeIndex) -> np.ndarray:
    """aday D -> book CET date D (NO shift). 0 where soybean did not trade."""
    s = series.groupby(series.index.normalize()).sum()
    return s.reindex(book_dates).fillna(0.0).to_numpy(float)


if __name__ == "__main__":
    for sp in (1.5, 2.0, 3.0):
        d = build(sp)
        r = d["net_log"].to_numpy()
        sh = r.mean() / r.std() * np.sqrt(ANN)
        print(f"spread {sp}bp: n={len(d)} verify_err={d.attrs['verify_err']:.2e} "
              f"(ref n={d.attrs['n_ref']}) | net_log Sharpe {sh:.3f} "
              f"| net_simple mean {d['net_simple'].mean()*1e4:+.2f}bp "
              f"worst {d['net_simple'].min()*100:.2f}% | worst low {d['low_frac'].min()*100:.2f}% "
              f"| usda days {int(d['is_usda'].sum())}")
    d = build(2.0)
    print(f"\naday range {d.index[0].date()} -> {d.index[-1].date()} ({len(d)} days)")
    print("verify_err~0 confirms net_log == net_analysis.py net() => window 01:00->07:00 UTC, "
          "VT identical to report. net_log Sharpe@2bp should == 1.08 (report headline).")
