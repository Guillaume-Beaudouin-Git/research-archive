"""Step 4 — long-sample HELD/FORFEITED decomposition (ZN 2000-2026, n=311) with a
block bootstrap, robustness of the session cut, then the material constraints:
lot granularity, costs, and a first-passage propfirm simulation.

Session identification (step2, empirical, not assumed):
  yfinance ZN=F daily OPEN  == CME Globex session open 18:00 ET of the PRIOR
                               calendar day (71.6% exact tick match, median 0 ticks)
  yfinance ZN=F daily CLOSE == the 15:00 ET settlement mark (median 1 tick)

So for CME trading day D:
  HELD      = log C(D) - log O(D)     -> 18:00 ET (D-1) .. 15:00 ET (D)
  FORFEITED = log O(D+1) - log C(D)   -> 15:00 ET (D) .. 18:00 ET (D)
That FORFEITED window is strictly WIDER than what any futures propfirm actually
imposes (Apex 4.0 flat 16:59 ET, Topstep flat 16:10 ET, both re-entering 18:00 ET),
so the held leg measured here is a LOWER bound on what a daily-flat account keeps.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / "data"
BPS = 1e4
RNG = np.random.default_rng(20260725)


def load(tk: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA / f"daily_{tk}.parquet")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df.sort_index()


def dend(idx: pd.DatetimeIndex) -> np.ndarray:
    return pd.Series(0, index=idx).groupby(idx.to_period("M")).cumcount(ascending=False).values + 1


def tstat(x) -> float:
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def block_boot(x, block=3, n_boot=40000, seed=11):
    """Circular block bootstrap. Returns (p_null_two_sided, ci_lo, ci_hi)."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    n = len(x)
    nb = int(np.ceil(n / block))
    st = rng.integers(0, n, size=(n_boot, nb))
    idx = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(n_boot, -1)[:, :n] % n
    means = x[idx].mean(axis=1)
    p = float((np.abs(means - x.mean()) >= abs(x.mean())).mean())
    return p, float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def legs(tk: str, k: int = 3) -> pd.DataFrame:
    """Per-event sums of HELD and FORFEITED legs, plus per-day matrices."""
    df = load(tk)
    lc, lo = np.log(df["Close"]), np.log(df["Open"])
    held = lc - lo                 # session leg on day D
    forf = (lo - lc.shift(1))      # gap AFTER day D-1, i.e. credited to day D
    de = dend(df.index)
    m = de <= k
    per = df.index.to_period("M")
    t = pd.DataFrame(dict(held=held, forf=forf, cc=lc.diff(), per=per, px=df["Close"]))[m]
    g = t.groupby("per").agg(held=("held", "sum"), forf=("forf", "sum"),
                             cc=("cc", "sum"), px=("px", "mean"), n=("held", "count"))
    return g[(g.n == k) & g.notna().all(axis=1)]


def show(g: pd.DataFrame, tag: str) -> None:
    rows = []
    for col, lab in (("cc", "TOTAL close->close"), ("held", "HELD 18:00->15:00 ET"),
                     ("forf", "FORFEITED 15:00->18:00 ET")):
        x = g[col].values
        p, lo_, hi = block_boot(x)
        rows.append(dict(leg=lab, n=len(x), mean_bps=x.mean() * BPS, t=tstat(x),
                         hit=(x > 0).mean(), p_block=p,
                         ci95_lo_bps=lo_ * BPS, ci95_hi_bps=hi * BPS))
    out = pd.DataFrame(rows)
    print(f"\n--- {tag}  ({g.index[0]} -> {g.index[-1]}) ---")
    print(out.to_string(index=False, float_format=lambda v: f"{v:9.3f}"))
    print(f"    HELD share of total = {g['held'].mean() / g['cc'].mean():.1%}")


if __name__ == "__main__":
    print("#" * 78)
    print("# 4a — long-sample decomposition, CME rate futures, block bootstrap")
    print("#" * 78)
    G = {}
    for tk, lab in (("ZNF", "ZN 10y"), ("ZBF", "ZB 30y"), ("ZFF", "ZF 5y")):
        G[tk] = legs(tk)
        show(G[tk], lab)

    print("\n" + "#" * 78)
    print("# 4b — robustness of the cut: does the HELD share depend on window length,")
    print("#      sub-period, or the instrument?")
    print("#" * 78)
    rows = []
    for k in (1, 2, 3, 4, 5):
        g = legs("ZNF", k)
        rows.append(dict(window_days=k, n=len(g), total_bps=g.cc.mean() * BPS,
                         held_bps=g.held.mean() * BPS, held_t=tstat(g.held.values),
                         forf_bps=g.forf.mean() * BPS, forf_t=tstat(g.forf.values),
                         held_share=g.held.mean() / g.cc.mean()))
    print("\n  window length (last-k trading days), ZN:")
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda v: f"{v:8.2f}"))

    rows = []
    g = G["ZNF"]
    yr = np.array([p.year for p in g.index])
    for a, b, lab in ((2000, 2007, "2000-07"), (2008, 2014, "2008-14"),
                      (2015, 2021, "2015-21"), (2022, 2026, "2022-26")):
        s = g[(yr >= a) & (yr <= b)]
        rows.append(dict(period=lab, n=len(s), total_bps=s.cc.mean() * BPS,
                         held_bps=s.held.mean() * BPS, held_t=tstat(s.held.values),
                         forf_bps=s.forf.mean() * BPS,
                         held_share=s.held.mean() / s.cc.mean()))
    print("\n  sub-periods, ZN:")
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda v: f"{v:8.2f}"))

    print("\n  placebo: same HELD/FORFEITED split on NON-month-end days (ZN)")
    df = load("ZNF")
    lc, lo = np.log(df["Close"]), np.log(df["Open"])
    de = dend(df.index)
    base = pd.DataFrame(dict(held=(lc - lo), forf=(lo - lc.shift(1)))).iloc[1:]
    nm = (de <= 3)[1:]
    for lab, mask in (("month-end days", nm), ("all other days", ~nm)):
        s = base[mask]
        print(f"    {lab:16s} n={len(s):5d} held={s.held.mean()*BPS:+6.2f}bps "
              f"(t={tstat(s.held.values):+5.2f})  forf={s.forf.mean()*BPS:+6.2f}bps "
              f"(t={tstat(s.forf.values):+5.2f})")

    # -------------------------------------------------------------------------
    print("\n" + "#" * 78)
    print("# 4c — MATERIAL CONSTRAINTS: lot granularity and costs")
    print("#" * 78)
    g = G["ZNF"]
    notional = g["px"].mean() / 100 * 100_000
    print(f"\n  ZN average settle over the sample: {g['px'].mean():.2f} "
          f"-> notional/contract ~= ${notional:,.0f}")
    specs = {
        # name: (dollar P&L per 1 bp of PRICE return per contract, margin, tick $)
        "ZN  10y note ($100k face)": (notional * 1e-4, 1800, 15.625),
        "ZF   5y note ($100k face)": (load("ZFF")["Close"].tail(250).mean() / 100 * 100_000 * 1e-4, 1100, 7.8125),
        "ZB  30y bond ($100k face)": (load("ZBF")["Close"].tail(250).mean() / 100 * 100_000 * 1e-4, 3800, 31.25),
        "10Y micro yield ($10/bp y)": (10.0 / 6.4, 320, 1.0),   # DV01-converted, ZN CTD dur ~6.4
    }
    ev = {"ZN  10y note ($100k face)": G["ZNF"], "ZF   5y note ($100k face)": G["ZFF"],
          "ZB  30y bond ($100k face)": G["ZBF"], "10Y micro yield ($10/bp y)": G["ZNF"]}
    rows = []
    for k, (dpb, marg, tick) in specs.items():
        x = ev[k]["cc"].values * BPS
        h = ev[k]["held"].values * BPS
        rows.append(dict(instrument=k, mean_evt_usd=x.mean() * dpb, sd_evt_usd=x.std(ddof=1) * dpb,
                         held_evt_usd=h.mean() * dpb, init_margin=marg, tick_usd=tick,
                         worst_evt_usd=x.min() * dpb))
    print()
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda v: f"{v:10.1f}"))

    print("\n  Costs per contract (propfirm futures, all-in RT):")
    print("    commission+fees RT: ZN ~$3.10 (Rithmic/Tradovate propfirm tier)")
    print("    slippage: ZN top-of-book is 1 tick ($15.625) and thousands deep;")
    print("              assume 0.5 tick each way at 18:00 ET / 15:00 ET = $15.6 RT")
    print("    => ~$19 RT per contract per ROUND TRIP")
    rt_cost = 19.0
    for nrt, lab in ((1, "continuous hold (MFFU: overnight allowed)"),
                     (3, "daily-flat (Apex 4.0 / Topstep: 3 re-entries)")):
        for k, (dpb, _, _) in specs.items():
            gross = (G["ZNF"]["cc"].values.mean() * BPS if nrt == 1
                     else G["ZNF"]["held"].values.mean() * BPS) * dpb
            if "micro" not in k:
                continue
        gross_zn = ((g["cc"].mean() if nrt == 1 else g["held"].mean()) * BPS) * specs["ZN  10y note ($100k face)"][0]
        gross_mi = ((g["cc"].mean() if nrt == 1 else g["held"].mean()) * BPS) * specs["10Y micro yield ($10/bp y)"][0]
        print(f"    {lab:44s} cost=${nrt*rt_cost:5.0f}/ctr  "
              f"ZN net=${gross_zn - nrt*rt_cost:7.1f}  micro10Y net=${gross_mi - nrt*rt_cost*0.35:6.1f}"
              f"  (micro RT ~$6.6)")
