"""FORMULATION 2 — exogenous state at T-1 conditions an INTRADAY-FLAT trade at T.

Zero swap by construction, so the carry that kills the gold sleeve is removed.
The question is whether the conditioning lifts gross per trade above the cost
gate FASTER than it destroys frequency.

Frequency is reported on EVERY row. A cell is only interesting if
    freq x (gross - cost)   beats the same quantity for the UNCONDITIONAL shape.
Gross alone is meaningless here (a quintile divides frequency by ~2.5-5).

Clock: exchange local time with its DST (L56). Hourly bars are true UTC
(gross_surface_map cache, read-only) and converted to America/New_York.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from exog_lib import (COST_RT_BPS, GROSSMAP, MECHANISM_SIGN, POST2021,  # noqa: E402
                      build_exog_panel, hac_t)

OUT = os.path.join(os.path.dirname(__file__), "..")
INSTRUMENTS = ["XAUUSD", "USDJPY"]
TZ = "America/New_York"

# Pre-registered intraday-flat shapes, declared BEFORE measurement.
# (entry local hour, exit local hour). Entry price = close of the bar labelled
# (h-1), i.e. the price observable AT h:00 -> no same-bar look-ahead (L26/L59).
SHAPES = {
    "A_reopen_18_19": (18, 19),   # first hour after the Globex reopen (L56 gold finding)
    "B_us_session_09_16": (9, 16),
    "C_afternoon_15_17": (15, 17),  # the only window where gross_surface_map found structure
}
RANK_WIN = 504


def hourly_local(inst: str) -> pd.DataFrame:
    d = pd.read_parquet(f"{GROSSMAP}/{inst}_H1.parquet")
    d.index = d.index.tz_localize("UTC").tz_convert(TZ)
    return d


def shape_returns(d: pd.DataFrame, h_in: int, h_out: int) -> pd.DataFrame:
    """Per-day entry/exit prices for one intraday-flat shape, in bps.

    Entry at h_in:00 = close of bar (h_in - 1). Exit at h_out:00 = close of bar
    (h_out - 1). Both are prices that existed BEFORE the clock struck, so the
    trade is fillable at the stamp (L59 entry side; exit is a time exit, not a
    stop, so there is no stop-gap re-pricing to do here).
    """
    c = d["close"]
    hh = c.index.hour
    day = c.index.normalize()
    ent = c[hh == (h_in - 1) % 24]
    ext = c[hh == (h_out - 1) % 24]
    ent = pd.Series(ent.to_numpy(), index=ent.index.normalize())
    ext = pd.Series(ext.to_numpy(), index=ext.index.normalize())
    ent = ent[~ent.index.duplicated(keep="last")]
    ext = ext[~ext.index.duplicated(keep="last")]
    out = pd.DataFrame({"entry": ent, "exit": ext}).dropna()
    out["r_bps"] = np.log(out["exit"] / out["entry"]) * 1e4
    out.index = out.index.tz_localize(None)
    # spread actually quoted at the traded hour (gross_surface_map section 6)
    sp = d["spread_med"][hh == (h_in - 1) % 24]
    sp = pd.Series(sp.to_numpy(), index=sp.index.normalize())
    sp = sp[~sp.index.duplicated(keep="last")]
    sp.index = sp.index.tz_localize(None)
    out["spread_med"] = sp.reindex(out.index)
    return out


def trailing_rank(s: pd.Series, win: int = RANK_WIN) -> pd.Series:
    return s.rolling(win, min_periods=int(win * 0.5)).apply(
        lambda a: (a[:-1] < a[-1]).mean(), raw=True)


def main() -> None:
    exog = build_exog_panel(shift_days=1)
    rows = []
    diag = []
    for inst in INSTRUMENTS:
        d = hourly_local(inst)
        cost = COST_RT_BPS[inst]
        # --- per-hour diagnostics: halt coverage + rollover spread blow-out ---
        dp = d[d.index >= POST2021.tz_localize("UTC").tz_convert(TZ)]
        bars_h = dp.groupby(dp.index.hour).size()
        sp_h = dp.groupby(dp.index.hour)["spread_med"].median()
        sp_ref = float(sp_h.median())
        n_ref = float(bars_h.median())
        for h in range(24):
            diag.append(dict(inst=inst, local_hour=h, n_bars=int(bars_h.get(h, 0)),
                             bar_coverage=round(bars_h.get(h, 0) / n_ref, 3),
                             spread_med_pts=float(sp_h.get(h, np.nan)),
                             spread_ratio_vs_day=round(float(sp_h.get(h, np.nan)) / sp_ref, 2)))
        for sname, (hi, ho) in SHAPES.items():
            sh = shape_returns(d, hi, ho)
            he = (hi - 1) % 24
            sp_ratio = round(float(sp_h.get(he, np.nan)) / sp_ref, 2)
            cover = round(bars_h.get(he, 0) / n_ref, 3)
            for era, m in [("post2021", sh.index >= POST2021),
                           ("pre2021", sh.index < POST2021)]:
                s = sh[m]
                if len(s) < 200:
                    continue
                yrs = (s.index.max() - s.index.min()).days / 365.25
                r = s["r_bps"]
                # ---- the UNCONDITIONAL benchmark for this shape ---------------
                for lname, sgn in [("uncond_long", 1.0), ("uncond_short", -1.0)]:
                    y = (sgn * r).to_numpy()
                    g, t = hac_t(y)
                    rows.append(dict(
                        inst=inst, shape_name=sname, era=era, predictor="NONE",
                        form="unconditional", side_rule=lname,
                        N=len(y), freq_per_year=round(len(y) / yrs, 1),
                        gross_bps=round(g, 3), t_gross=round(t, 2),
                        baseline_bps=round(g, 3), excess_bps=0.0, t_excess=np.nan,
                        cost_rt_bps=cost, net_bps=round(g - cost, 3),
                        net_ann_bps=round((g - cost) * len(y) / yrs, 1),
                        spread_at_hour=round(float(s["spread_med"].median()), 3),
                        spread_ratio_vs_day=sp_ratio, entry_bar_coverage=cover))
                m_all = float(r.mean())
                # ---- conditioned on the exogenous state ----------------------
                for pred, mech in MECHANISM_SIGN[inst].items():
                    x = exog[pred].reindex(sh.index).ffill(limit=5)
                    rk = trailing_rank(x)[m]
                    for form in ["median", "quintile"]:
                        if form == "median":
                            side = np.sign(rk - 0.5) * mech
                        else:
                            side = pd.Series(0.0, index=rk.index)
                            side[rk >= 0.8] = mech
                            side[rk <= 0.2] = -mech
                            side[rk.isna()] = np.nan
                        sub = pd.DataFrame({"side": side, "r": r}).dropna()
                        act = sub[sub["side"] != 0]
                        if len(act) < 60:
                            continue
                        y = (act["side"] * act["r"]).to_numpy()
                        g, t = hac_t(y)
                        base = float(act["side"].mean()) * m_all
                        e, te = hac_t(y - base)
                        rows.append(dict(
                            inst=inst, shape_name=sname, era=era, predictor=pred,
                            form=form, side_rule="mechanism",
                            N=len(y), freq_per_year=round(len(y) / yrs, 1),
                            gross_bps=round(g, 3), t_gross=round(t, 2),
                            baseline_bps=round(base, 3),
                            excess_bps=round(e, 3), t_excess=round(te, 2),
                            cost_rt_bps=cost, net_bps=round(g - cost, 3),
                            net_ann_bps=round((g - cost) * len(y) / yrs, 1),
                            spread_at_hour=round(float(s["spread_med"].median()), 3),
                        spread_ratio_vs_day=sp_ratio, entry_bar_coverage=cover))

    pd.DataFrame(diag).to_csv(f"{OUT}/f2_hour_diagnostics.csv", index=False)
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/f2_intraday_all.csv", index=False)
    post = df[df.era == "post2021"]
    pd.set_option("display.width", 250)
    print(f"F2: {len(df)} rows, {len(post)} post-2021")
    c = ["inst", "shape_name", "predictor", "form", "N", "freq_per_year", "gross_bps",
         "t_gross", "baseline_bps", "excess_bps", "t_excess", "net_bps",
         "net_ann_bps", "spread_ratio_vs_day", "entry_bar_coverage"]
    print("\n--- UNCONDITIONAL shapes, post-2021 (the benchmark every cell must beat) ---")
    print(post[post.form == "unconditional"][c].to_string(index=False))
    print("\n--- conditioned, top 12 by t_excess (post-2021) ---")
    cond = post[post.form != "unconditional"]
    print(cond.sort_values("t_excess", ascending=False)[c].head(12).to_string(index=False))
    print("\n--- gate: gross > 3 x cost AND |t_excess| > 2.5 ---")
    g = cond[(cond.gross_bps > 3 * cond.cost_rt_bps) & (cond.t_excess.abs() > 2.5)]
    print(g[c].to_string(index=False) if len(g) else "EMPTY")
    print("\n--- best net_ann_bps, conditioned vs unconditional, per (inst, shape) ---")
    agg = post.groupby(["inst", "shape_name", post.form == "unconditional"])["net_ann_bps"].max()
    print(agg.to_string())


if __name__ == "__main__":
    main()
