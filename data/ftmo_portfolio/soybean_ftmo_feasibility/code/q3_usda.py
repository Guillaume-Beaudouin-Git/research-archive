"""Q3 — USDA/WASDE tail decomposition (soybean-specific; absent from gold).

(a) VALIDATE the calendar: realised window range elevated on tagged report/day-after mornings.
(b) Decompose the left tail by bucket {report_day R, day_after R+1, other}; ATTRIBUTE the worst
    days (dates + nearest scheduled report, calendar-free distance check).
(c) Edge WITH vs WITHOUT skip (Sharpe/mean/maxDD/worst/skew/OOS) -> does skip rescue daily -5%?
Reuses soy_series + usda_calendar. Costs at the report base 2bp.
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as sst

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import soy_series as SS
import usda_calendar as UC

OUT = HERE.parent / "results"
ANN = 252.0
SPREAD = 2.0


def sharpe(x):
    x = np.asarray(x); return float(x.mean() / x.std() * np.sqrt(ANN)) if len(x) > 1 and x.std() > 0 else np.nan


def mdd(r):
    eq = np.cumprod(1 + np.asarray(r)); return float((eq / np.maximum.accumulate(eq) - 1).min())


def main():
    d = SS.build(SPREAD)
    idx = d.index
    net = d["net_simple"]
    raw = d["raw_log"]                                  # window log return (direction+magnitude)
    rng = raw.abs()                                     # |window move| proxy for realised range

    # bucket tags
    is_R = pd.Series(UC.is_report_day(idx), index=idx)
    is_after = pd.Series(UC.is_report_day(idx - pd.Timedelta(days=1)), index=idx)  # D-1 is report
    bucket = np.where(is_R, "report_R", np.where(is_after, "day_after", "other"))
    bucket = pd.Series(bucket, index=idx)

    res = {"spread_bp": SPREAD, "n": len(d)}

    # ---------- (a) calendar validation: elevated range on tagged days ----------
    val = {b: dict(n=int((bucket == b).sum()),
                   mean_abs_move_bp=round(float(rng[bucket == b].mean() * 1e4), 1),
                   median_abs_move_bp=round(float(rng[bucket == b].median() * 1e4), 1))
           for b in ["report_R", "day_after", "other"]}
    elev = val["day_after"]["mean_abs_move_bp"] / val["other"]["mean_abs_move_bp"]
    res["calendar_validation"] = dict(by_bucket=val, day_after_vs_other_elevation=round(elev, 2),
                                      verdict=("elevated" if elev > 1.15 else "NOT elevated"))
    print("=== (a) calendar validation (|window move|, bp) ===")
    for b, v in val.items():
        print(f"  {b:>10}: n={v['n']:4d}  mean |move| {v['mean_abs_move_bp']:6.1f}bp  median {v['median_abs_move_bp']:6.1f}bp")
    print(f"  day_after/other elevation = {elev:.2f}x -> {res['calendar_validation']['verdict']}")

    # ---------- (b) worst-day attribution ----------
    report_dates = np.array(sorted(UC.REPORT_DATES))
    def nearest_report(ts):
        dd = np.array([(ts.date() - r).days for r in report_dates])
        j = np.argmin(np.abs(dd)); return int(dd[j]), report_dates[j]   # +offset = days AFTER report

    worst = net.nsmallest(15)
    wlist = []
    for ts, v in worst.items():
        off, rd = nearest_report(ts)
        wlist.append(dict(date=str(ts.date()), net_pct=round(v * 100, 2), bucket=bucket[ts],
                          days_from_report=off, nearest_report=str(rd),
                          near=bool(abs(off) <= 2)))
    res["worst_15_days"] = wlist
    print("\n=== (b) worst 15 days (net @2bp) — attribution ===")
    print(f"{'date':>12}{'net%':>8}{'bucket':>12}{'dFromRpt':>9}{'nearRpt':>12}")
    for w in wlist:
        print(f"{w['date']:>12}{w['net_pct']:>8.2f}{w['bucket']:>12}{w['days_from_report']:>9}{w['nearest_report']:>12}")
    near = sum(w["near"] for w in wlist)
    res["worst15_near_report_frac"] = round(near / len(wlist), 2)
    print(f"  worst-15 within +-2d of a scheduled report: {near}/15 ({near/15*100:.0f}%)")

    # ---------- tail metrics by bucket ----------
    tail = {}
    for b in ["report_R", "day_after", "other", "all"]:
        x = net if b == "all" else net[bucket == b]
        tail[b] = dict(n=int(len(x)), mean_bp=round(float(x.mean() * 1e4), 2),
                       worst_pct=round(float(x.min() * 100), 2),
                       p1_pct=round(float(np.percentile(x, 1) * 100), 2),
                       skew=round(float(sst.skew(x)), 2),
                       n_lt_m3pct=int((x < -0.03).sum()))
    res["tail_by_bucket"] = tail
    print("\n=== tail by bucket ===")
    for b, v in tail.items():
        print(f"  {b:>10}: n={v['n']:4d} mean {v['mean_bp']:+6.2f}bp worst {v['worst_pct']:6.2f}% "
              f"p1 {v['p1_pct']:6.2f}% skew {v['skew']:+5.2f} #<-3% {v['n_lt_m3pct']}")

    # ---------- (c) edge WITH vs WITHOUT skip ----------
    skip_mask = (bucket != "other")          # skip report_R OR day_after
    print(f"\n=== (c) edge with/without USDA skip (skip removes {int(skip_mask.sum())} days) ===")
    cmp = {}
    for tag, series in [("all_days", net), ("skip_usda", net[~skip_mask])]:
        r = series.to_numpy()
        oos = series[series.index >= series.index[int(0.6 * len(series))]].to_numpy()
        cmp[tag] = dict(n=len(r), sharpe=round(sharpe(r), 3), oos_sharpe=round(sharpe(oos), 3),
                        mean_bp=round(float(r.mean() * 1e4), 2), maxdd_pct=round(mdd(r) * 100, 1),
                        worst_pct=round(float(r.min() * 100), 2), skew=round(float(sst.skew(r)), 2))
        print(f"  {tag:>10}: n={cmp[tag]['n']} Sharpe {cmp[tag]['sharpe']:.2f} OOS {cmp[tag]['oos_sharpe']:.2f} "
              f"mean {cmp[tag]['mean_bp']:+.2f}bp maxDD {cmp[tag]['maxdd_pct']}% worst {cmp[tag]['worst_pct']}% skew {cmp[tag]['skew']}")
    res["edge_with_without_skip"] = cmp

    # does skip rescue the daily -5% at the Q2 best K=4?
    Kbest = 4.0
    worst_all = net.min() * Kbest * 100
    worst_skip = net[~skip_mask].min() * Kbest * 100
    res["skip_rescues_daily5"] = dict(K=Kbest, worst_day_scaled_all=round(worst_all, 1),
                                      worst_day_scaled_skip=round(worst_skip, 1),
                                      sharpe_ratio_post_skip=round(cmp["skip_usda"]["sharpe"] / cmp["all_days"]["sharpe"], 3))
    print(f"\n  at K={Kbest}: worst day scaled all {worst_all:.1f}% vs skip {worst_skip:.1f}%  "
          f"(daily barrier -5%); Sharpe ratio post/pre skip = {res['skip_rescues_daily5']['sharpe_ratio_post_skip']}")

    (OUT / "q3_usda.json").write_text(json.dumps(res, indent=2, default=str))
    print("\nwritten q3_usda.json")


if __name__ == "__main__":
    main()
