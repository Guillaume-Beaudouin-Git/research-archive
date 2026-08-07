"""Extended-sample confirmatory test of the frozen CPI-eve gold trade.

Spec frozen in ../PREREGISTRATION.md. The ONLY change vs 2026-08-06 is the
sample: BLS CPI release dates 2007-2026 (234 events) instead of the repo's
2020-2026 calendar file (77, of which 7 are wrong).
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from cpi_lib import (COST_RT_BPS, COST_RT_TAIL_BPS, MAIN, N_TRIALS, OUT,  # noqa: E402
                     POST2021, SWAP_BPS, bls_dates, block_bootstrap_p,
                     expanding_walk_forward, eve_of, fomc_dates,
                     frozen_returns, hac_t, walk_forward)
from dsr import deflated_sharpe_ratio  # noqa: E402

pd.set_option("display.width", 250)
COST = COST_RT_BPS["XAUUSD"]
SWAP = SWAP_BPS["XAUUSD"]["long"]
COST_TOT = COST + abs(SWAP)                       # 3.358 bps, one night held
COST_TAIL = COST_RT_TAIL_BPS["XAUUSD"] + abs(SWAP)  # 5.398 bps


def battery(r: pd.Series, entry: pd.DatetimeIndex, label: str,
            n_trials: int = N_TRIALS, seed: int = 3) -> dict:
    """The frozen battery, verbatim in structure from cpi_candidate.py."""
    yrs = (r.index.max() - r.index.min()).days / 365.25
    sel = r.index.isin(entry)
    y = r[sel]
    if len(y) < 20:
        return {}
    g, t = hac_t(y.to_numpy())
    m_all = float(r.mean())
    sd = float(np.std(r, ddof=1))
    mde = 2.5 * sd / np.sqrt(len(y))

    doms = pd.Series(y.index).dt.day
    lo, hi = int(doms.min()), int(doms.max())
    band = r.index.day.isin(range(lo, hi + 1)) & ~sel
    pool = r[band].to_numpy()
    g_pool, t_pool = hac_t(pool)
    rng = np.random.default_rng(seed)
    draws = np.array([rng.choice(pool, size=len(y), replace=False).mean()
                      for _ in range(5000)])
    p_dom = float((draws >= g).mean())

    net = y.to_numpy() + SWAP - COST
    net_tail = y.to_numpy() + SWAP - COST_RT_TAIL_BPS["XAUUSD"]
    wf = walk_forward(y.index, net, n_folds=5)
    wfe = expanding_walk_forward(y.index, net, n_folds=5)
    pb = block_bootstrap_p(y.to_numpy() - m_all, block=3)
    p_raw = 2 * (1 - stats.norm.cdf(abs(t)))
    ppy = len(y) / yrs
    try:
        d = deflated_sharpe_ratio(net, n_trials=n_trials, periods_per_year=ppy,
                                  rf=0.0, std_sr_trials=0.5)
        dsr, shp = round(d["dsr"], 4), round(d["sharpe"], 3)
    except Exception as e:                      # pragma: no cover
        dsr, shp = np.nan, str(e)[:30]

    return dict(
        sample=label, N=len(y), span=f"{y.index.min().date()}..{y.index.max().date()}",
        freq_per_year=round(len(y) / yrs, 1),
        dom_band=f"{lo}-{hi}",
        gross_bps=round(g, 3), t_HAC=round(t, 2),
        uncond_mean_bps=round(m_all, 3), excess_vs_uncond=round(g - m_all, 3),
        MDE_bps_at_t2p5=round(mde, 2),
        powered="YES" if abs(g - m_all) > mde else "UNDERPOWERED",
        dom_pool_mean_bps=round(g_pool, 3), dom_pool_t=round(t_pool, 2),
        dom_pool_bias_vs_uncond=round(g_pool - m_all, 3),
        L58_pool_valid="OK" if abs(g_pool - m_all) <= abs(g - m_all) / 3 else "BIASED",
        p_placebo_dom=round(p_dom, 4),
        p_raw=round(p_raw, 6), p_sidak=round(1 - (1 - p_raw) ** n_trials, 5),
        p_block_bootstrap=pb,
        gross_over_cost=round(g / COST_TOT, 2),
        gross_over_cost_tail=round(g / COST_TAIL, 2),
        net_bps=round(float(net.mean()), 3),
        net_ann_bps=round(float(net.mean()) * len(y) / yrs, 1),
        net_bps_tailcost=round(float(net_tail.mean()), 3),
        win_rate=round(float((y > 0).mean()), 4),
        wf_folds_pos=wf["folds_pos"], wf_fold_means=str(wf["fold_means"]),
        wf_exp_folds_pos=wfe["folds_pos"], wf_exp_fold_means=str(wfe["fold_means"]),
        wf_exp_fold_starts=str(wfe["fold_starts"]), wf_exp_fold_n=str(wfe["fold_n"]),
        sharpe_net=shp, DSR=dsr)


def main() -> None:
    warnings.simplefilter("ignore")
    r = frozen_returns("XAUUSD")
    cpi = bls_dates("cpi")
    entry = eve_of(cpi)

    # ---------------- hygiene, declared in the prereg ------------------------
    idx = set(r.index)
    in_px = [d for d in entry if d in idx]
    lost = [str(d.date()) for d in entry if d not in idx]
    pos = {d: i for i, d in enumerate(r.index)}
    next_is_cpi, next_bad = 0, []
    for c in cpi:
        e = c - pd.Timedelta(days=1)
        if e not in pos:
            continue
        i = pos[e]
        if i + 1 < len(r.index):
            nb = r.index[i + 1]
            if nb == c:
                next_is_cpi += 1
            else:
                next_bad.append((str(e.date()), str(c.date()), str(nb.date())))
    hyg = pd.DataFrame(dict(
        metric=["cpi_dates_bls", "entry_dates_in_price_index", "entry_dropped_not_traded",
                "exit_bar_is_cpi_day", "exit_bar_is_not_cpi_day"],
        value=[len(cpi), len(in_px), len(lost), next_is_cpi, len(next_bad)]))
    hyg.to_csv(f"{OUT}/sample_hygiene.csv", index=False)
    print("=== SAMPLE HYGIENE ===")
    print(hyg.to_string(index=False))
    print("dropped entries (eve not a trading day):", lost)
    print("exit bar != CPI day:", next_bad)

    # ---------------- the three eras -----------------------------------------
    rows = []
    eras = [
        ("OOS_PURE_2007_2020", r.index < POST2021),
        ("DISCOVERY_2021_2026", r.index >= POST2021),
        ("FULL_2007_2026", np.ones(len(r), dtype=bool)),
    ]
    for name, m in eras:
        row = battery(r[m], entry, name)
        if row:
            rows.append(row)
    # replication check: yesterday's file, yesterday's era
    old = pd.read_csv(f"{MAIN}/data/panels/economic_calendar.csv", parse_dates=["date"])
    old_cpi = pd.DatetimeIndex(old.loc[old.event == "CPI", "date"].unique())
    row = battery(r[r.index >= POST2021], eve_of(old_cpi),
                  "REPLICATION_2026-08-06_old_calendar", n_trials=76)
    if row:
        rows.append(row)
    res = pd.DataFrame(rows)
    res.to_csv(f"{OUT}/eras.csv", index=False)
    print("\n=== THE THREE ERAS + the replication of 2026-08-06 ===")
    print(res.T.to_string())

    # ---------------- year by year -------------------------------------------
    sel = r.index.isin(entry)
    y = r[sel]
    yr = y.groupby(y.index.year).agg(["mean", "count", lambda a: float((a > 0).mean())])
    yr.columns = ["mean_bps", "n", "win_rate"]
    yr["net_bps"] = yr.mean_bps + SWAP - COST
    yr.round(3).to_csv(f"{OUT}/by_year.csv")
    print("\n=== YEAR BY YEAR, full extended sample ===")
    print(yr.round(2).to_string())
    print(f"positive years: {(yr.mean_bps > 0).sum()} / {len(yr)}")

    # ---------------- robustness: trim, median, distribution -----------------
    top3 = y.abs().nlargest(3)
    tg, tt = hac_t(y.drop(top3.index).to_numpy())
    print(f"\nfull sample: mean {y.mean():.2f}  median {y.median():.2f}  "
          f"win {float((y > 0).mean()):.3f}  winner {y[y > 0].mean():.1f}  loser {y[y < 0].mean():.1f}")
    print(f"3 largest |moves| = {y.loc[top3.index].sum() / y.sum() * 100:.0f}% of P&L; "
          f"trimmed mean {tg:.2f} bps t {tt:.2f}")

    # ---------------- neighbourhood control ----------------------------------
    nb_rows = []
    events = {"CPI": cpi, "PPI": bls_dates("ppi"), "NFP_empsit": bls_dates("empsit"),
              "FOMC": fomc_dates()}
    for ename, ev in events.items():
        for era_name, m in eras:
            row = battery(r[m], eve_of(ev), f"{ename}|{era_name}")
            if row:
                row["event"] = ename
                row["era"] = era_name
                nb_rows.append(row)
    nb = pd.DataFrame(nb_rows)
    keep = ["event", "era", "N", "freq_per_year", "gross_bps", "t_HAC",
            "uncond_mean_bps", "excess_vs_uncond", "p_placebo_dom",
            "gross_over_cost", "net_bps", "net_ann_bps", "wf_folds_pos", "DSR"]
    nb[keep].to_csv(f"{OUT}/neighbourhood.csv", index=False)
    print("\n=== NEIGHBOURHOOD CONTROL (same frozen spec, other release calendars) ===")
    print(nb[keep].to_string(index=False))

    # ---------------- L60: zero-range bars -----------------------------------
    m1 = pd.read_parquet(f"{os.environ.get('CPI_CACHE', '<SCRATCH>')}/xau_m1.parquet")
    z = (m1.high == m1.low)
    l60 = z.groupby(m1.index.year).agg(["mean", "size"])
    l60.columns = ["zero_range_share", "n_bars"]
    l60.round(4).to_csv(f"{OUT}/l60_zero_range.csv")
    print("\n=== L60: zero-range M1 bars on XAUUSD, per year ===")
    print(l60.round(4).to_string())


if __name__ == "__main__":
    main()
