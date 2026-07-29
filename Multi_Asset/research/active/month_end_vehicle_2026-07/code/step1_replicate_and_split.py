"""Step 1 — reproduce the B1 window convention, then split the effect into
RTH (open->close) vs OVERNIGHT (prev close->open) on cash-session instruments.

B1 spec (frozen, data/personal_book/sleeves/b1_month_end_bond_rally.md):
  LONG the Treasury complex over the last 3 trading days of the calendar month.
  Entry = close of day dend4, exit = close of day dend1.
  Reported on TLT 2002-2026: +37.5 bps/trade, t = +4.65, hit 63%.

We do NOT re-test the edge. We reproduce it only to prove that the window
convention used for the decomposition is the same one, so that the split is a
decomposition of THE edge and not of some neighbouring window.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / "data"
RES = BASE / "results"
RES.mkdir(exist_ok=True)

BPS = 1e4


def load(tk: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA / f"daily_{tk}.parquet")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df.sort_index()


def dend(idx: pd.DatetimeIndex) -> np.ndarray:
    """1 = last trading day of the calendar month, 2 = one before, ..."""
    per = idx.to_period("M")
    return pd.Series(0, index=idx).groupby(per).cumcount(ascending=False).values + 1


def tstat(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def describe(x: np.ndarray, label: str) -> dict:
    x = np.asarray(x, float)
    return dict(leg=label, n=len(x), mean_bps=x.mean() * BPS, t=tstat(x),
                hit=float((x > 0).mean()), sd_bps=x.std(ddof=1) * BPS)


def build_events(df: pd.DataFrame, use_adjusted: bool) -> pd.DataFrame:
    """One row per month-end event, with the 3 event days' log returns split."""
    px_c = df["Adj Close"] if use_adjusted else df["Close"]
    # Open must be put on the same adjustment scale as close.
    ratio = (df["Adj Close"] / df["Close"]) if use_adjusted else 1.0
    px_o = df["Open"] * ratio

    lc, lo = np.log(px_c), np.log(px_o)
    r_cc = lc.diff()                 # close(d-1) -> close(d)
    r_rth = lc - lo                  # open(d)    -> close(d)
    r_on = lo - lc.shift(1)          # close(d-1) -> open(d)

    de = dend(df.index)
    m = de <= 3
    ym = df.index.to_period("M")
    out = pd.DataFrame(dict(cc=r_cc.values, rth=r_rth.values, on=r_on.values),
                       index=df.index)[m]
    ev = out.groupby(ym[m]).sum()
    cnt = out.groupby(ym[m]).size()
    ev = ev[cnt == 3]                # keep only complete 3-day windows
    return ev.dropna()


def report(tk: str, use_adjusted: bool, y0: int | None = None, y1: int | None = None,
           tag: str = "") -> pd.DataFrame:
    df = load(tk)
    ev = build_events(df, use_adjusted)
    if y0 is not None:
        ev = ev[(ev.index.year >= y0) & (ev.index.year <= y1)]
    rows = [describe(ev["cc"].values, "TOTAL close->close (3d)"),
            describe(ev["rth"].values, "  RTH  open->close"),
            describe(ev["on"].values, "  ON   prevclose->open")]
    out = pd.DataFrame(rows)
    adj = "adjusted" if use_adjusted else "raw"
    print(f"\n=== {tk} [{adj}] {tag} {ev.index[0]} -> {ev.index[-1]} ===")
    print(out.to_string(index=False, float_format=lambda v: f"{v:8.2f}"))
    share = out.loc[1, "mean_bps"] / out.loc[0, "mean_bps"]
    print(f"  RTH share of total = {share:5.1%} | ON share = {1 - share:5.1%}")
    return ev


if __name__ == "__main__":
    print("#" * 78)
    print("# STEP 1a — convention check: reproduce the frozen B1 number on TLT")
    print("#" * 78)
    for adj in (True, False):
        report("TLT", adj)

    print("\n" + "#" * 78)
    print("# STEP 1b — dividend contamination check (TLT ex-div dates vs window)")
    print("#" * 78)
    tlt = load("TLT")
    div = tlt[tlt["Dividends"] > 0]
    de_all = pd.Series(dend(tlt.index), index=tlt.index)
    de_div = de_all.loc[div.index]
    print(f"  n ex-div days = {len(div)}")
    print(f"  ex-div days falling inside the last-3-day window (dend<=3): "
          f"{int((de_div <= 3).sum())}")
    print(f"  distribution of dend for ex-div days (top 8):\n"
          f"{de_div.value_counts().head(8).to_string()}")

    print("\n" + "#" * 78)
    print("# STEP 1c — the split, all instruments")
    print("#" * 78)
    for tk in ("TLT", "IEF"):
        report(tk, True)
    for tk in ("ZNF", "ZBF", "ZFF"):
        report(tk, False)

    print("\n" + "#" * 78)
    print("# STEP 1d — regime split on TLT (adjusted)")
    print("#" * 78)
    for y0, y1, tag in ((2002, 2021, "bull-bond"), (2022, 2026, "bear-bond")):
        report("TLT", True, y0, y1, tag)
