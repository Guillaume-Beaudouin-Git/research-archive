"""The only cell in the whole study that clears both gates: XAUUSD, day BEFORE CPI.

post-2021: gross +38.07 bps, t_HAC 3.86, N=65, 12 trades/yr, gross/cost 20.7.

L58 is explicit that this is exactly the shape of result that a biased placebo
manufactures: US CPI is released on a narrow band of calendar days (roughly the
10th-13th), so "the day before CPI" is also "a particular day-of-month". The
control that costs nothing is to check the baseline against the UNCONDITIONAL
expectation, and to build a placebo matched on DAY-OF-MONTH rather than on
nothing at all.

Also run: pre-2021 out-of-sample, power, AMTP over the 76 calendar cells, the
disjoint-leg reading, walk-forward, block bootstrap and DSR.
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from exog_lib import (COST_RT_BPS, MAIN, POST2021, SWAP_BPS,  # noqa: E402
                      block_bootstrap_p, hac_t, load_daily_panel, walk_forward)
from dsr import deflated_sharpe_ratio  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..")
N_CAL_TESTS = 76      # post-2021 calendar cells swept in analysis.py

pd.set_option("display.width", 250)


def main() -> None:
    warnings.simplefilter("ignore")
    px, _ = load_daily_panel()
    p = px["XAUUSD"].dropna()
    r = (np.log(p).diff() * 1e4).shift(-1).dropna()      # forward 1d on entry date

    cal = pd.read_csv(f"{MAIN}/data/panels/economic_calendar.csv", parse_dates=["date"])
    cpi = pd.DatetimeIndex(cal.loc[cal.event == "CPI", "date"].unique())
    entry = pd.DatetimeIndex([d - pd.Timedelta(days=1) for d in cpi])

    rows = []
    for era, m in [("post2021", r.index >= POST2021), ("pre2021", r.index < POST2021)]:
        rr = r[m]
        if len(rr) < 200:
            continue
        yrs = (rr.index.max() - rr.index.min()).days / 365.25
        sel = rr.index.isin(entry)
        y = rr[sel].to_numpy()
        if len(y) < 20:
            continue
        g, t = hac_t(y)
        m_all = float(rr.mean())
        sd = float(np.std(rr, ddof=1))
        mde = 2.5 * sd / np.sqrt(len(y))

        # ---- day-of-month distribution of the entry days ----------------------
        doms = pd.Series(rr.index[sel]).dt.day
        dom_lo, dom_hi = int(doms.min()), int(doms.max())

        # ---- P-DOM: placebo matched on DAY-OF-MONTH (L58) ---------------------
        # Pool = every day whose day-of-month falls in the same band, EXCLUDING
        # the real entry days. If the band itself carries the return, the real
        # cell is a day-of-month effect wearing a CPI badge.
        band = rr.index.day.isin(range(dom_lo, dom_hi + 1)) & ~sel
        pool = rr[band].to_numpy()
        g_pool, t_pool = hac_t(pool)
        # matched draws of the same size from that pool
        rng = np.random.default_rng(3)
        draws = np.array([rng.choice(pool, size=len(y), replace=False).mean()
                          for _ in range(5000)])
        p_dom = float((draws >= g).mean())

        # ---- P-UNC: L58's zero-cost control -----------------------------------
        # the placebo pool's mean must equal the unconditional expectation;
        # if it does not, the placebo is biased, not the signal.
        bias = g_pool - m_all

        # ---- AMTP over the calendar sweep -------------------------------------
        p_raw = 2 * (1 - stats.norm.cdf(abs(t)))
        p_sidak = 1 - (1 - p_raw) ** N_CAL_TESTS

        net = y + SWAP_BPS["XAUUSD"]["long"] - COST_RT_BPS["XAUUSD"]
        wf = walk_forward(rr.index[sel], net, n_folds=5) if len(net) >= 100 else {"folds_pos": "IMPOSSIBLE (N<100)", "fold_means": []}
        pb = block_bootstrap_p(y - m_all, block=3)
        ppy = len(y) / yrs
        try:
            d = deflated_sharpe_ratio(net, n_trials=N_CAL_TESTS, periods_per_year=ppy,
                                      rf=0.0, std_sr_trials=0.5)
            dsr, shp = round(d["dsr"], 4), round(d["sharpe"], 3)
        except Exception:
            dsr, shp = np.nan, np.nan

        rows.append(dict(
            era=era, N=len(y), freq_per_year=round(len(y) / yrs, 1),
            dom_band=f"{dom_lo}-{dom_hi}",
            gross_bps=round(g, 3), t_HAC=round(t, 2),
            uncond_mean_bps=round(m_all, 3),
            excess_vs_uncond=round(g - m_all, 3),
            MDE_bps_at_t2p5=round(mde, 2),
            powered=("YES" if abs(g - m_all) > mde else "UNDERPOWERED"),
            dom_pool_mean_bps=round(g_pool, 3), dom_pool_t=round(t_pool, 2),
            dom_pool_bias_vs_uncond=round(bias, 3),
            p_placebo_dom=round(p_dom, 4),
            p_raw=round(p_raw, 5), p_sidak_76=round(p_sidak, 4),
            p_block_bootstrap=pb,
            net_bps=round(float(net.mean()), 3),
            net_ann_bps=round(float(net.mean()) * len(y) / yrs, 1),
            wf_folds_pos=wf["folds_pos"], wf_fold_means=str(wf["fold_means"]),
            sharpe_net=shp, DSR=dsr))

    res = pd.DataFrame(rows)
    res.to_csv(f"{OUT}/cpi_candidate.csv", index=False)
    print("=== XAUUSD, day BEFORE US CPI — full battery ===")
    print(res.T.to_string())

    # ---- two-sided reading: is there anything on the short side? -------------
    print("\n=== the same cell, split by realised sign of the CPI-eve move ===")
    rr = r[r.index >= POST2021]
    sel = rr.index.isin(entry)
    y = rr[sel]
    print(f"N={len(y)}  positive days={int((y > 0).sum())}  win rate={(y > 0).mean():.3f}")
    print(f"mean winner={y[y > 0].mean():.1f} bps   mean loser={y[y < 0].mean():.1f} bps")
    print(f"median={y.median():.2f} bps   (mean {y.mean():.2f})")
    top3 = y.abs().nlargest(3)
    print(f"3 largest |moves| carry {y.loc[top3.index].sum() / y.sum() * 100:.0f} % of the total P&L:")
    print(y.loc[top3.index].to_string())
    trimmed, t_tr = hac_t(y.drop(top3.index).to_numpy())
    print(f"after removing them: mean {trimmed:.2f} bps, t {t_tr:.2f}")

    # ---- year by year: the only fold structure 65 trades can support --------
    yr = y.groupby(y.index.year).agg(["mean", "count", lambda a: (a > 0).mean()])
    yr.columns = ["mean_bps", "n", "win_rate"]
    yr.to_csv(f"{OUT}/cpi_by_year.csv")
    print("\n=== year by year (5 folds of 13 trades is not a walk-forward; this is the honest view) ===")
    print(yr.round(2).to_string())
    print(f"years with positive mean: {(yr.mean_bps > 0).sum()} / {len(yr)}")

    # ---- day-of-month profile, the L58 diagnostic ---------------------------
    prof = rr.groupby(rr.index.day).agg(["mean", "count"])
    prof.columns = ["mean_bps", "n"]
    prof.to_csv(f"{OUT}/xauusd_day_of_month_profile.csv")
    print("\n=== XAUUSD day-of-month return profile, post-2021 (L58 diagnostic) ===")
    print(prof.round(2).to_string())


if __name__ == "__main__":
    main()
