"""Step 3 — where inside the CME trading day does the month-end drift accrue?

The premise "futures propfirms force you flat overnight, so a 3-day effect dies"
comes from an equities mental model. On CME, the *trading day* for ZN runs
18:00 ET (D-1) -> 17:00 ET (D) with a one-hour settlement break. Firms that ban
"overnight" (Apex 4.0 flat 16:59 ET, Topstep flat 16:10 ET) therefore only force
you to skip the tail of the session plus the closed break -- NOT the Asian and
European hours.

So the right decomposition is: HELD leg (re-entry R -> exit C, inside one CME day)
vs FORFEITED leg (C -> R, the firm-imposed flat window). We sweep C and R.

Also: the hour-by-hour accrual shape, which is what makes the verdict falsifiable
rather than an artefact of one cut.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / "data"
BPS = 1e4


def load_h1(name: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA / f"h1_{name}.parquet")
    idx = pd.to_datetime(df.index, utc=True).tz_convert("America/New_York")
    df = df.set_axis(idx).sort_index()
    return df[~df.index.duplicated(keep="first")]


def cme_day(idx: pd.DatetimeIndex) -> pd.Series:
    """CME trading day: 18:00 ET (D-1) .. 17:00 ET (D) -> label D."""
    return pd.Series((idx + pd.Timedelta(hours=7)).normalize().tz_localize(None), index=idx)


def event_days(days: pd.DatetimeIndex, k: int = 3) -> pd.DatetimeIndex:
    """Last k trading days of each calendar month, plus the anchor day dend(k+1)."""
    s = pd.Series(0, index=days)
    de = s.groupby(days.to_period("M")).cumcount(ascending=False) + 1
    return de


def mark_series(h1: pd.DataFrame) -> pd.DataFrame:
    """Long frame: one row per (cme_day, hour_et) with the bar's CLOSE price.

    A bar stamped 14:00 ET closes at 15:00 ET, so we label the mark by its END
    time -- 'price at 15:00 ET'.
    """
    out = pd.DataFrame({
        "day": cme_day(h1.index).values,
        "mark_et": (h1.index + pd.Timedelta(hours=1)).hour,
        "px": h1["Close"].values,
    }, index=h1.index)
    return out


def price_at(marks: pd.DataFrame, hour: int) -> pd.Series:
    """Price at `hour` ET within each CME trading day (hour is the mark END time)."""
    sub = marks[marks["mark_et"] == hour]
    s = sub.groupby("day")["px"].last()
    return s


def tstat(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def block_bootstrap_t(x: np.ndarray, block: int = 3, n_boot: int = 20000,
                      seed: int = 7) -> tuple[float, float]:
    """Politis-Romano stationary-ish circular block bootstrap on the event series.

    Returns (p_two_sided for mean<=0, 95% CI lower) under the null of no drift,
    built by recentring. Events are monthly and ordered in time; block=3 covers
    residual month-to-month clustering. iid resampling is forbidden here (L: block
    bootstrap mandatory when trade clusters exist).
    """
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    n = len(x)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_boot, nb))
    offs = np.arange(block)
    idx = (starts[:, :, None] + offs[None, None, :]).reshape(n_boot, -1)[:, :n] % n
    samp = x[idx]
    means = samp.mean(axis=1)
    # null: recentre
    p = float((np.abs(means - x.mean()) >= abs(x.mean())).mean())
    lo = float(np.percentile(means, 2.5))
    return p, lo


if __name__ == "__main__":
    h1 = load_h1("ZNF")
    marks = mark_series(h1)
    days = pd.DatetimeIndex(sorted(marks["day"].unique()))
    # keep weekdays with a real session
    cnt = marks.groupby("day").size()
    days = pd.DatetimeIndex(cnt[cnt >= 12].index)
    de = event_days(days)

    print("=" * 78)
    print(f"ZN hourly, CME-day aligned: {days[0].date()} -> {days[-1].date()}  n_days={len(days)}")
    n_ev = int(((de <= 3).groupby(days.to_period('M')).sum() == 3).sum())
    print(f"complete 3-day month-end windows: {n_ev}")

    # ---- hour-by-hour accrual on event days vs non-event days -----------------
    print("\n" + "=" * 78)
    print("HOURLY ACCRUAL (mean log-return by ET hour-ending, bps)")
    print("  event = the 3 last trading days of the month; base = all other days")
    print("=" * 78)
    hours = list(range(19, 24)) + list(range(0, 18))  # 19:00 ET .. 17:00 ET
    px = {h: price_at(marks, h) for h in range(0, 24)}
    ev_mask = (de <= 3).reindex(days).fillna(False)

    seq = [(19, None)] + [(h, None) for h in hours[1:]]
    rows = []
    prev_h = 18  # session open mark 18:00->19:00 handled below
    prev_px = price_at(marks, 19).shift(0)  # placeholder
    # build a per-day ordered price vector at marks 19..23, then 0..17
    order = hours
    P = pd.DataFrame({h: px[h] for h in order}).reindex(days)
    open_px = h1.between_time("18:00", "18:00")["Open"]
    open_px = pd.Series(open_px.values, index=cme_day(open_px.index).values)
    open_px = open_px[~open_px.index.duplicated(keep="first")].reindex(days)
    cols = ["OPEN18"] + [f"{h:02d}" for h in order]
    M = pd.concat([open_px.rename("OPEN18"), P.rename(columns=lambda h: f"{h:02d}")], axis=1)[cols]
    R = np.log(M).diff(axis=1).iloc[:, 1:]

    tab = pd.DataFrame({
        "event_bps": R[ev_mask.values].mean() * BPS,
        "event_t": R[ev_mask.values].apply(lambda c: tstat(c.dropna().values)),
        "base_bps": R[~ev_mask.values].mean() * BPS,
        "n_ev": R[ev_mask.values].notna().sum(),
    })
    tab["cum_event_bps"] = tab["event_bps"].cumsum()
    tab.index = [f"{c} ET" for c in tab.index]
    print(tab.to_string(float_format=lambda v: f"{v:8.2f}"))

    # ---- HELD vs FORFEITED for a grid of firm flat-windows --------------------
    # M holds the ordered per-CME-day price marks: OPEN18 (session open 18:00 ET,
    # which happens on calendar day D-1) then hourly marks 19:00..17:00 ET.
    print("\n" + "=" * 78)
    print("HELD vs FORFEITED, by firm flat-window  (ZN hourly, CME-day aligned)")
    print("  window = last 3 trading days of the month; total = held(3 sessions)")
    print("           + forfeited(3 flat-gaps, after dend4/dend3/dend2)")
    print("=" * 78)
    scen = [
        ("MFFU / continuous (no flat rule)",  17,  "CONT"),
        ("Apex 4.0   flat 17:00 -> back 18:00", 17, "OPEN18"),
        ("Topstep    flat 16:00 -> back 18:00", 16, "OPEN18"),
        ("conservative flat 15:00 -> back 18:00", 15, "OPEN18"),
        ("RTH-ish    flat 16:00 -> back 08:00", 16, "08"),
        ("RTH-only   flat 16:00 -> back 10:00", 16, "10"),
        ("US-cash    flat 16:00 -> back 09:00", 16, "09"),
    ]
    dser = pd.Series(de.values, index=days)
    ev3 = (dser <= 3)
    per = pd.Series(days.to_period("M"), index=days)
    res = []
    for lab, C, Rk in scen:
        pC = np.log(M[f"{C:02d}"])
        if Rk == "CONT":
            held = pC.diff()
            forf = pd.Series(0.0, index=days)
        else:
            pR = np.log(M[Rk])
            held = pC - pR                     # re-entry(D) -> exit(D)
            forf = pR.shift(-1) - pC           # exit(D) -> re-entry(D+1)
        forf_in = forf.shift(1)                # gap AFTER day D-1, credited to day D
        df = pd.DataFrame({"held": held, "forf": forf_in, "per": per})[ev3.values]
        g = df.groupby("per").agg(held=("held", "sum"), forf=("forf", "sum"),
                                  nh=("held", "count"), nf=("forf", "count"))
        g = g[(g.nh == 3) & (g.nf == 3)]
        hv, fv = g["held"].values, g["forf"].values
        tot = hv + fv
        res.append(dict(scenario=lab, n=len(hv),
                        held_bps=hv.mean() * BPS, held_t=tstat(hv),
                        forf_bps=fv.mean() * BPS, forf_t=tstat(fv) if fv.std() > 0 else np.nan,
                        total_bps=tot.mean() * BPS,
                        held_share=hv.mean() / tot.mean()))
    out = pd.DataFrame(res)
    print(out.to_string(index=False, float_format=lambda v: f"{v:8.2f}"))

    print("\n  block-bootstrap (block=3 events, 20k draws) on the HELD leg:")
    for lab, C, Rk in scen:
        pC = np.log(M[f"{C:02d}"])
        if Rk == "CONT":
            held = pC.diff()
        else:
            held = pC - np.log(M[Rk])
        df = pd.DataFrame({"held": held, "per": per})[ev3.values]
        g = df.groupby("per").agg(h=("held", "sum"), n=("held", "count"))
        hv = g.loc[g.n == 3, "h"].values
        pb, lo = block_bootstrap_t(hv)
        print(f"    {lab:40s} mean={hv.mean()*BPS:+7.2f}bps  p_block={pb:.4f}  "
              f"boot 2.5%={lo*BPS:+7.2f}bps")
