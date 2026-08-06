"""FORMULATION 1 — exogenous predictor at T-1 -> position HELD for H days.

This formulation pays the overnight swap, which is exactly what kills the gold
sleeve (62 % of its gross). The swap is ASYMMETRIC and is charged per leg with
the leg's own rate, so a predictor that produces short-gold days is 4.5x cheaper
to carry than one that produces long-gold days. That asymmetry is the whole
point of testing the two legs disjointly (L25).

Everything is gated at the GROSS first (cost_rt = 0, swap = 0). Costs enter as a
reading threshold in the output columns.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, os.path.dirname(__file__))
from exog_lib import (COST_RT_BPS, MECHANISM_SIGN, POST2021, SWAP_BPS,  # noqa: E402
                      build_exog_panel, hac_t, load_daily_panel)

OUT = os.path.join(os.path.dirname(__file__), "..")
INSTRUMENTS = ["XAUUSD", "USDJPY"]
HORIZONS = [1, 5, 20]
FORMS = ["median", "quintile"]          # two-sided 50/50  vs  conditioned tails
RANK_WIN = 504                          # 2y trailing rank, look-ahead free


def trailing_rank(s: pd.Series, win: int = RANK_WIN) -> pd.Series:
    """Percentile of the current value inside its own trailing window (inclusive)."""
    return s.rolling(win, min_periods=int(win * 0.5)).apply(
        lambda a: (a[:-1] < a[-1]).mean(), raw=True)


def sides_from_rank(rk: pd.Series, mech: int, form: str) -> pd.Series:
    if form == "median":
        return np.sign(rk - 0.5) * mech
    lo, hi = 0.2, 0.8
    s = pd.Series(0.0, index=rk.index)
    s[rk >= hi] = mech
    s[rk <= lo] = -mech
    s[rk.isna()] = np.nan
    return s


def fwd_return_bps(px: pd.Series, H: int) -> pd.Series:
    """log forward return over H trading days, in bps, aligned on the ENTRY date."""
    return (np.log(px.shift(-H) / px) * 1e4)


def dual_r2(x: pd.Series, r: pd.Series) -> tuple[float, float]:
    """L54: R^2 of the state on the MEAN and on the VARIANCE proxy, side by side."""
    m = x.notna() & r.notna()
    if m.sum() < 60:
        return (np.nan, np.nan)
    xs = ((x[m] - x[m].mean()) / x[m].std()).to_numpy()
    X = sm.add_constant(xs)
    r2_mean = sm.OLS(r[m].to_numpy(), X).fit().rsquared
    r2_var = sm.OLS(np.abs(r[m].to_numpy()), X).fit().rsquared
    return float(r2_mean), float(r2_var)


def main() -> None:
    px, rets = load_daily_panel()
    exog = build_exog_panel(shift_days=1)

    rows = []
    legs = []
    for inst in INSTRUMENTS:
        p = px[inst].dropna()
        p = p[p.index >= "2007-01-01"]
        for H in HORIZONS:
            fr = fwd_return_bps(p, H)
            for pred, mech in MECHANISM_SIGN[inst].items():
                x = exog[pred].reindex(p.index).ffill(limit=5)
                rk = trailing_rank(x)
                for form in FORMS:
                    side = sides_from_rank(rk, mech, form)
                    for era, mask in [
                        ("post2021", p.index >= POST2021),
                        ("pre2021", p.index < POST2021),
                    ]:
                        sub = pd.DataFrame({"side": side, "fr": fr}).loc[mask].dropna()
                        # non-overlapping sampling of the ENTRY dates
                        sub = sub.iloc[::H]
                        act = sub[sub["side"] != 0]
                        if len(act) < 40:
                            continue
                        y = (act["side"] * act["fr"]).to_numpy()
                        # L58 baseline matched to the side mix this state produces
                        m_all = float(sub["fr"].mean())
                        base = float(act["side"].mean()) * m_all
                        gross, t_gross = hac_t(y)
                        exc, t_exc = hac_t(y - base)
                        yrs = (sub.index.max() - sub.index.min()).days / 365.25
                        n_long = int((act["side"] > 0).sum())
                        n_short = int((act["side"] < 0).sum())
                        swap_bill = (
                            n_long * H * SWAP_BPS[inst]["long"]
                            + n_short * H * SWAP_BPS[inst]["short"]
                        ) / len(act)
                        net = gross + swap_bill - COST_RT_BPS[inst]
                        r2m, r2v = dual_r2(
                            x.reindex(sub.index), (sub["fr"]).reindex(sub.index))
                        rows.append(dict(
                            inst=inst, predictor=pred, H=H, form=form, era=era,
                            N=len(act), n_long=n_long, n_short=n_short,
                            freq_per_year=round(len(act) / yrs, 1),
                            gross_bps=round(gross, 3), t_gross=round(t_gross, 2),
                            baseline_bps=round(base, 3),
                            excess_bps=round(exc, 3), t_excess=round(t_exc, 2),
                            swap_bps_per_trade=round(swap_bill, 3),
                            cost_rt_bps=COST_RT_BPS[inst],
                            net_bps=round(net, 3),
                            net_ann_bps=round(net * len(act) / yrs, 1),
                            R2_mean=round(r2m, 5), R2_var=round(r2v, 5),
                            swap_share_of_gross=(round(abs(swap_bill) / gross, 3)
                                                 if gross > 0 else np.nan),
                        ))
                        # ---- disjoint legs (L25) -------------------------------
                        for lname, sel in [("long", act["side"] > 0),
                                           ("short", act["side"] < 0)]:
                            a = act[sel]
                            if len(a) < 40:
                                continue
                            yl = (a["side"] * a["fr"]).to_numpy()
                            gl, tl = hac_t(yl)
                            bl = float(np.sign(a["side"].mean())) * m_all
                            el, tel = hac_t(yl - bl)
                            sw = H * SWAP_BPS[inst][lname]
                            legs.append(dict(
                                inst=inst, predictor=pred, H=H, form=form, era=era,
                                leg=lname, N=len(a),
                                freq_per_year=round(len(a) / yrs, 1),
                                gross_bps=round(gl, 3), t_gross=round(tl, 2),
                                baseline_bps=round(bl, 3),
                                excess_bps=round(el, 3), t_excess=round(tel, 2),
                                swap_bps_per_trade=round(sw, 3),
                                net_bps=round(gl + sw - COST_RT_BPS[inst], 3),
                            ))

    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/f1_held_all.csv", index=False)
    lg = pd.DataFrame(legs)
    lg.to_csv(f"{OUT}/f1_held_legs.csv", index=False)

    post = df[df.era == "post2021"]
    print(f"F1: {len(df)} rows ({len(post)} post-2021 cells), {len(lg)} leg rows")
    print("\n--- post-2021, ranked by t_excess ---")
    cols = ["inst", "predictor", "H", "form", "N", "freq_per_year", "gross_bps",
            "t_gross", "baseline_bps", "excess_bps", "t_excess",
            "swap_bps_per_trade", "net_bps", "R2_mean", "R2_var"]
    print(post.sort_values("t_excess", ascending=False)[cols].head(15).to_string(index=False))
    print("\n--- post-2021, worst (short-side mechanism check) ---")
    print(post.sort_values("t_excess")[cols].head(8).to_string(index=False))
    print("\n--- gate: net_bps > 0 AND |t_excess| > 2.5 (post-2021) ---")
    g = post[(post.net_bps > 0) & (post.t_excess.abs() > 2.5)]
    print(g[cols].to_string(index=False) if len(g) else "EMPTY")
    print("\n--- L54 dual R2, post-2021 summary ---")
    print(post.groupby("inst")[["R2_mean", "R2_var"]].median().to_string())


if __name__ == "__main__":
    main()
