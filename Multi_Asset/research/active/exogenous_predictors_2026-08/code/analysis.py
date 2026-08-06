"""Three questions the two formulation sweeps do not answer on their own.

A. THE CARRY LEDGER (gold). The incumbent gold sleeve dies because the swap eats
   62 % of its gross. Does ANY exogenous predictor produce a gold sleeve whose
   swap share is materially lower? There are only two ways it could: raise the
   gross per trade, or move weight onto the SHORT leg, which costs -0.336/night
   instead of -1.518 (4.5x cheaper).

B. THE HEAD-TO-HEAD. A conditioned sleeve is only worth anything if it beats the
   unconditional always-long version of the same trade, net of everything. This
   is the L58 baseline turned into money.

C. THE CALENDAR FAMILY. Pure calendar predictors are the one exogenous class
   with zero revision risk and zero publication lag. Tested separately because
   they are event-shaped, not state-shaped.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from exog_lib import (COST_RT_BPS, MAIN, POST2021, SWAP_BPS, hac_t,  # noqa: E402
                      load_daily_panel)
from f2_intraday import SHAPES, hourly_local, shape_returns  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..")
pd.set_option("display.width", 250)


# ---------------------------------------------------------------- A. carry ledger
def carry_ledger() -> pd.DataFrame:
    f1 = pd.read_csv(f"{OUT}/f1_held_all.csv")
    g = f1[(f1.inst == "XAUUSD") & (f1.era == "post2021")].copy()
    g["swap_share_of_gross"] = np.where(g.gross_bps > 0,
                                        g.swap_bps_per_trade.abs() / g.gross_bps, np.nan)
    g["long_share"] = g.n_long / (g.n_long + g.n_short)
    return g[["predictor", "H", "form", "N", "freq_per_year", "gross_bps", "t_gross",
              "swap_bps_per_trade", "swap_share_of_gross", "long_share",
              "net_bps", "net_ann_bps"]].sort_values("swap_share_of_gross")


def short_leg_inventory() -> pd.DataFrame:
    legs = pd.read_csv(f"{OUT}/f1_held_legs.csv")
    s = legs[(legs.inst == "XAUUSD") & (legs.era == "post2021") & (legs.leg == "short")]
    return s[["predictor", "H", "form", "N", "freq_per_year", "gross_bps", "t_gross",
              "excess_bps", "t_excess", "swap_bps_per_trade", "net_bps"]] \
        .sort_values("gross_bps", ascending=False)


# ------------------------------------------------------------- B. head-to-head
def head_to_head() -> pd.DataFrame:
    """Net annual bps of the best conditioned sleeve vs the unconditional long.

    The unconditional long is HELD, so it pays the swap every night but only ONE
    round trip over the whole period -- that is the honest comparator, and it is
    the reason a high-frequency conditioned sleeve has to clear a real bar.
    """
    px, _ = load_daily_panel()
    rows = []
    for inst in ["XAUUSD", "USDJPY"]:
        p = px[inst].dropna()
        p = p[p.index >= POST2021]
        r = (np.log(p).diff() * 1e4).dropna()
        yrs = (p.index.max() - p.index.min()).days / 365.25
        for lname in ["long", "short"]:
            sgn = 1.0 if lname == "long" else -1.0
            y = sgn * r.to_numpy()
            g, t = hac_t(y)
            sw = SWAP_BPS[inst][lname]
            net_day = g + sw
            rows.append(dict(
                inst=inst, strategy=f"unconditional {lname}, held", N=len(y),
                trades_per_year=round(1 / yrs, 2),
                gross_bps_per_day=round(g, 3), t_gross=round(t, 2),
                swap_bps_per_day=sw, rt_cost_total_bps=COST_RT_BPS[inst],
                net_ann_bps=round(net_day * len(y) / yrs, 1),
                ann_vol_bps=round(float(np.std(y, ddof=1)) * np.sqrt(len(y) / yrs), 1),
                net_sharpe=round(net_day / float(np.std(y, ddof=1)) * np.sqrt(len(y) / yrs), 3)))
    f1 = pd.read_csv(f"{OUT}/f1_held_all.csv")
    best = f1[(f1.era == "post2021")].sort_values("net_ann_bps", ascending=False)
    for inst in ["XAUUSD", "USDJPY"]:
        b = best[best.inst == inst].iloc[0]
        rows.append(dict(
            inst=inst, strategy=f"BEST conditioned F1: {b.predictor} H={b.H} {b.form}",
            N=int(b.N), trades_per_year=b.freq_per_year,
            gross_bps_per_day=b.gross_bps, t_gross=b.t_gross,
            swap_bps_per_day=b.swap_bps_per_trade,
            rt_cost_total_bps=b.cost_rt_bps * b.freq_per_year,
            net_ann_bps=b.net_ann_bps, ann_vol_bps=np.nan, net_sharpe=np.nan))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- C. calendar
def load_events() -> dict:
    ev = {}
    f = pd.read_csv(f"{MAIN}/data/personal_book/post_fomc_drift/data_cache/fomc_events.csv",
                    parse_dates=["date"])
    ev["FOMC"] = pd.DatetimeIndex(f["date"].unique())
    c = pd.read_csv(f"{MAIN}/data/panels/economic_calendar.csv", parse_dates=["date"])
    for name, g in c.groupby("event"):
        ev[f"CAL_{name}"] = pd.DatetimeIndex(g["date"].unique())
    return ev


def calendar_tests() -> pd.DataFrame:
    """Event-day / day-after conditioning, both formulations, both instruments.

    The event date is known YEARS in advance, so there is no publication-lag or
    revision question at all -- the cleanest exogenous information there is.
    """
    events = load_events()
    px, _ = load_daily_panel()
    rows = []
    for inst in ["XAUUSD", "USDJPY"]:
        p = px[inst].dropna()
        r_daily = (np.log(p).diff() * 1e4).shift(-1)   # forward 1d, indexed on entry date
        intraday = {}
        d = hourly_local(inst)
        for sname, (hi, ho) in SHAPES.items():
            sh = shape_returns(d, hi, ho)
            if len(sh[sh.index >= POST2021]) > 200:
                intraday[sname] = sh["r_bps"]
        series = {"F1_hold_1d": r_daily, **{f"F2_{k}": v for k, v in intraday.items()}}
        for sname, s in series.items():
            for era, m in [("post2021", s.index >= POST2021), ("pre2021", s.index < POST2021)]:
                ss = s[m].dropna()
                if len(ss) < 200:
                    continue
                yrs = (ss.index.max() - ss.index.min()).days / 365.25
                m_all = float(ss.mean())
                for ename, edates in events.items():
                    for off, oname in [(0, "day_of"), (1, "day_after"), (-1, "day_before")]:
                        stamps = pd.DatetimeIndex(
                            [d0 + pd.Timedelta(days=off) for d0 in edates])
                        sel = ss.index.isin(stamps)
                        y = ss[sel].to_numpy()
                        if len(y) < 25:
                            continue
                        # two-sided, disjoint legs: report the LONG expression and
                        # let the sign of the mean speak. No pre-registered
                        # direction exists for a calendar event.
                        g, t = hac_t(y)
                        cost = COST_RT_BPS[inst]
                        swap = SWAP_BPS[inst]["long" if g > 0 else "short"] if sname == "F1_hold_1d" else 0.0
                        rows.append(dict(
                            inst=inst, shape_name=sname, era=era, event=ename, offset=oname,
                            N=len(y), freq_per_year=round(len(y) / yrs, 1),
                            gross_bps=round(g, 3), t_gross=round(t, 2),
                            baseline_bps=round(m_all, 3),
                            excess_bps=round(g - m_all, 3),
                            abs_gross_bps=round(abs(g), 3),
                            cost_rt_bps=cost, swap_bps=swap,
                            net_abs_bps=round(abs(g) + swap - cost, 3),
                            gross_over_cost=round(abs(g) / cost, 3)))
    return pd.DataFrame(rows)


def main() -> None:
    cl = carry_ledger()
    cl.to_csv(f"{OUT}/gold_carry_ledger.csv", index=False)
    print("=== A. GOLD CARRY LEDGER (post-2021) — incumbent sleeve: swap = 62 % of gross ===")
    print(cl.to_string(index=False))

    sl = short_leg_inventory()
    sl.to_csv(f"{OUT}/gold_short_leg_inventory.csv", index=False)
    print("\n=== A2. Can any exogenous state put gold SHORT profitably? "
          "(short swap -0.336 vs long -1.518) ===")
    print(sl.to_string(index=False))
    print(f"\nshort legs with gross > 0: {(sl.gross_bps > 0).sum()} / {len(sl)}"
          f"   |  with net > 0: {(sl.net_bps > 0).sum()} / {len(sl)}")

    hh = head_to_head()
    hh.to_csv(f"{OUT}/head_to_head_vs_unconditional.csv", index=False)
    print("\n=== B. HEAD-TO-HEAD vs the unconditional held long (post-2021) ===")
    print(hh.to_string(index=False))

    cal = calendar_tests()
    cal.to_csv(f"{OUT}/calendar_tests.csv", index=False)
    post = cal[cal.era == "post2021"]
    print(f"\n=== C. CALENDAR FAMILY — {len(cal)} cells ({len(post)} post-2021) ===")
    print("\ntop 12 post-2021 by |gross| / cost:")
    print(post.sort_values("gross_over_cost", ascending=False).head(12).to_string(index=False))
    print(f"\ncells with gross/cost >= 3 : {(post.gross_over_cost >= 3).sum()} / {len(post)}")
    print(f"cells with |t_gross| > 2.5 : {(post.t_gross.abs() > 2.5).sum()} / {len(post)}")
    both = post[(post.gross_over_cost >= 3) & (post.t_gross.abs() > 2.5)]
    print(f"BOTH: {len(both)}")
    if len(both):
        print(both.to_string(index=False))

    # ---- the ANNUAL COST BILL: does trading on a signal beat just holding? ---
    f1 = pd.read_csv(f"{OUT}/f1_held_all.csv")
    f2 = pd.read_csv(f"{OUT}/f2_intraday_all.csv")
    g = f1[(f1.inst == "XAUUSD") & (f1.era == "post2021")].copy()
    g["ann_cost_bill_bps"] = g.freq_per_year * (g.cost_rt_bps + g.swap_bps_per_trade.abs())
    hold_bill = abs(SWAP_BPS["XAUUSD"]["long"]) * 260 + COST_RT_BPS["XAUUSD"]
    bill = g[["predictor", "H", "form", "freq_per_year", "cost_rt_bps",
              "swap_bps_per_trade", "ann_cost_bill_bps"]].sort_values("ann_cost_bill_bps")
    bill["vs_hold_and_do_nothing"] = (bill.ann_cost_bill_bps / hold_bill).round(2)
    bill.to_csv(f"{OUT}/gold_annual_cost_bill.csv", index=False)
    print(f"\n=== E. ANNUAL COST BILL, gold. Holding continuously costs "
          f"{hold_bill:.0f} bps/yr (260 nights x 1.518 + one round trip). ===")
    print(bill.to_string(index=False))

    # ---- the ratio that compares this study to the price-predictor map -------
    f1p = f1[f1.era == "post2021"].copy()
    # for a HELD position the denominator is the round trip PLUS the swap paid
    f1p["total_cost"] = f1p.cost_rt_bps + f1p.swap_bps_per_trade.abs()
    f2p = f2[(f2.era == "post2021") & (f2.form != "unconditional")].copy()
    ratio = pd.DataFrame([
        dict(source="F1 held, cost = RT + swap actually paid", n_cells=len(f1p),
             median_gross_over_cost=round(float((f1p.gross_bps.abs() /
                                                 f1p.total_cost).median()), 3),
             p90=round(float((f1p.gross_bps.abs() / f1p.total_cost).quantile(.9)), 3),
             best=round(float((f1p.gross_bps.abs() / f1p.total_cost).max()), 3)),
        dict(source="F2 intraday-flat, cost = RT (no swap)", n_cells=len(f2p),
             median_gross_over_cost=round(float((f2p.gross_bps.abs() /
                                                 f2p.cost_rt_bps).median()), 3),
             p90=round(float((f2p.gross_bps.abs() / f2p.cost_rt_bps).quantile(.9)), 3),
             best=round(float((f2p.gross_bps.abs() / f2p.cost_rt_bps).max()), 3)),
        dict(source="gross_surface_map 2026-08 (PRICE predictors)", n_cells=6511,
             median_gross_over_cost=0.38, p90=np.nan, best=np.nan),
        dict(source="L43 (FX intraday-flat, different method)", n_cells=np.nan,
             median_gross_over_cost=0.36, p90=np.nan, best=np.nan),
    ])
    ratio.to_csv(f"{OUT}/gross_over_cost_ratio.csv", index=False)
    print("\n=== D. gross / cost — against gross_surface_map (0.38) and L43 (0.36) ===")
    print(ratio.to_string(index=False))


if __name__ == "__main__":
    main()
