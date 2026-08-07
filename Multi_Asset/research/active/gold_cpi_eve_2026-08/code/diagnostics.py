"""Pre-registered secondary diagnostics (§6 of PREREGISTRATION.md).

None of these is decision-bearing. They exist to say WHY the primary test lands
where it lands.

  D1  intraday decomposition of the frozen window: drift before 08:30 ET vs
      reaction after (M1 true UTC, exchange clock with DST, L56).
  D2  the regime hypothesis named in the prereg, tested: does the event return
      load on the inflation level knowable at entry, or on implied vol?
  D3  frequency arithmetic + one FTMO barrier run as an UPPER BOUND on a
      rejected candidate.
"""
from __future__ import annotations

import os
import re
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from cpi_lib import (CACHE, COST_RT_BPS, MAIN, OUT, POST2021, SWAP_BPS,  # noqa: E402
                     bls_dates, frozen_returns, hac_t)
import statsmodels.api as sm  # noqa: E402

COST = COST_RT_BPS["XAUUSD"]
SWAP = SWAP_BPS["XAUUSD"]["long"]
BLSREL = f"{CACHE}/blsrel"


# --------------------------------------------------------------------- D1
def d1_intraday() -> pd.DataFrame:
    """Split the frozen close-to-close window at the 08:30 ET embargo."""
    m1 = pd.read_parquet(f"{CACHE}/xau_m1.parquet")
    m1 = m1[~m1.index.duplicated(keep="last")].sort_index()
    et = m1.index.tz_localize("UTC").tz_convert("America/New_York")
    # exchange clock with DST (L56); minute-of-day in ET, and the UTC calendar
    # date used only to bucket bars into sessions
    et_hm = et.hour * 60 + et.minute
    m1 = m1.assign(_et_hm=et_hm.to_numpy(),
                   _et_str=et.strftime("%Y-%m-%d %H:%M %Z"),
                   _d=m1.index.normalize(), _h=m1.index.hour)
    byday = {d: g for d, g in m1.groupby("_d", sort=True)}

    cpi = bls_dates("cpi")
    px_idx = set(frozen_returns("XAUUSD").index)
    rows = []
    RELEASE_MIN = 8 * 60 + 30       # 08:30 ET
    for c in cpi:
        e = c - pd.Timedelta(days=1)
        if e not in px_idx or e not in byday or c not in byday:
            continue
        w_eve = byday[e]
        w_eve = w_eve[w_eve._h < 22]          # before the settlement halt
        w_day = byday[c]
        pre = w_day[w_day._et_hm < RELEASE_MIN]   # STRICTLY before the embargo
        post = w_day[w_day._h < 22]
        if len(w_eve) == 0 or len(pre) == 0 or len(post) == 0:
            continue
        p_eve = float(w_eve.close.iloc[-1])
        p_pre = float(pre.close.iloc[-1])
        p_close = float(post.close.iloc[-1])
        rows.append(dict(
            cpi=c, eve=e, era="DISCOVERY" if c >= POST2021 else "OOS",
            pre_bps=1e4 * np.log(p_pre / p_eve),
            post_bps=1e4 * np.log(p_close / p_pre),
            total_bps=1e4 * np.log(p_close / p_eve),
            last_pre_bar_et=str(pre._et_str.iloc[-1])))
    d = pd.DataFrame(rows)
    out = []
    for era in ["OOS", "DISCOVERY", "ALL"]:
        s = d if era == "ALL" else d[d.era == era]
        r = {"era": era, "N": len(s)}
        for leg in ["pre_bps", "post_bps", "total_bps"]:
            g, t = hac_t(s[leg].to_numpy())
            r[f"{leg}_mean"] = round(g, 3)
            r[f"{leg}_t"] = round(t, 2)
        r["pre_share_of_total"] = round(s.pre_bps.sum() / s.total_bps.sum(), 3) if s.total_bps.sum() else np.nan
        out.append(r)
    res = pd.DataFrame(out)
    d.to_csv(f"{OUT}/intraday_events.csv", index=False)
    res.to_csv(f"{OUT}/d1_intraday_decomposition.csv", index=False)
    print("=== D1  drift BEFORE 08:30 ET  vs  reaction AFTER (M1 true UTC -> ET with DST) ===")
    print(res.to_string(index=False))
    print("sanity: last pre-release bar, sample:",
          d.last_pre_bar_et.head(2).tolist(), d.last_pre_bar_et.tail(2).tolist())
    return d


# --------------------------------------------------------------------- D2
def parse_yoy() -> pd.Series:
    """Headline CPI-U 12-month change, parsed from the BLS release documents."""
    pats = [
        r"all items index (?:rose|increased|declined|fell|was up|was unchanged)[^.]{0,60}?(\d+\.\d) percent (?:before seasonal adjustment|for the (?:last )?12 months|over the last 12 months)",
        r"(?:over the last 12 months|for the 12 months ending [A-Za-z]+),? the all items index (?:rose|increased|declined|fell)\s*(\d+\.\d) percent",
        r"was (\d+\.\d) percent higher than in [A-Z][a-z]+ \d{4}",
    ]
    rows = []
    for f in sorted(os.listdir(BLSREL)):
        key = f[:-4]
        d = pd.Timestamp(f"{key[4:]}-{key[:2]}-{key[2:4]}")
        t = open(f"{BLSREL}/{f}", encoding="utf-8", errors="ignore").read()
        t = re.sub(r"<[^>]+>", " ", t).replace("&nbsp;", " ")
        t = re.sub(r"\s+", " ", t)
        v = None
        for p in pats:
            m = re.search(p, t, re.I)
            if m:
                v = float(m.group(1))
                # sign: BLS words the direction separately
                seg = t[max(0, m.start() - 120):m.end()]
                if re.search(r"declin|fell|decreas", seg, re.I) and "12 month" in seg.lower():
                    v = -v
                break
        rows.append((d, v))
    s = pd.Series(dict(rows)).sort_index()
    return s.dropna()


def d2_regime(y: pd.Series) -> None:
    """Does the event return load on the inflation level KNOWABLE at entry?"""
    yoy = parse_yoy()
    vix = pd.read_parquet(f"{MAIN}/data/raw/fred_VIXCLS_14ec2ab193.parquet")
    vix = vix[~vix.index.duplicated(keep="last")].sort_index()["vixcls"]

    cpi = bls_dates("cpi")
    m = pd.DataFrame({"cpi": cpi})
    m["eve"] = m.cpi - pd.Timedelta(days=1)
    # the y/y knowable at the eve is the one printed at the PREVIOUS release
    yy = yoy.reindex(cpi)
    m["yoy_prev"] = yy.shift(1).to_numpy()
    m["vix_eve"] = vix.reindex(m.eve, method="ffill").to_numpy()
    m["ret"] = y.reindex(m.eve).to_numpy()
    m = m.dropna(subset=["ret"])
    m.to_csv(f"{OUT}/d2_regime_inputs.csv", index=False)

    print("\n=== D2  the regime hypothesis, tested (prereg §5 'REGIME') ===")
    print(f"headline CPI y/y parsed from {yoy.notna().sum()} / 234 BLS releases, "
          f"{yoy.index.min().date()}..{yoy.index.max().date()}")
    rows = []
    for name, cols in [("yoy_prev", ["yoy_prev"]), ("vix_eve", ["vix_eve"]),
                       ("both", ["yoy_prev", "vix_eve"])]:
        s = m.dropna(subset=cols + ["ret"])
        X = sm.add_constant(s[cols].astype(float))
        r = sm.OLS(s.ret.astype(float), X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
        rows.append(dict(spec=name, N=int(r.nobs), R2=round(r.rsquared, 4),
                         **{f"beta_{c}": round(r.params[c], 3) for c in cols},
                         **{f"t_{c}": round(r.tvalues[c], 2) for c in cols}))
    reg = pd.DataFrame(rows)
    reg.to_csv(f"{OUT}/d2_regime_regression.csv", index=False)
    print(reg.to_string(index=False))

    # non-parametric: split by inflation level knowable at entry
    s = m.dropna(subset=["yoy_prev"])
    q = pd.qcut(s.yoy_prev, 4, labels=["Q1_low", "Q2", "Q3", "Q4_high"])
    tab = []
    for k, gr in s.groupby(q, observed=True):
        g, t = hac_t(gr.ret.to_numpy())
        tab.append(dict(quartile=str(k), N=len(gr),
                        yoy_range=f"{gr.yoy_prev.min():.1f}..{gr.yoy_prev.max():.1f}",
                        gross_bps=round(g, 2), t_HAC=round(t, 2)))
    tt = pd.DataFrame(tab)
    tt.to_csv(f"{OUT}/d2_regime_quartiles.csv", index=False)
    print("\nquartiles of the inflation level KNOWABLE at entry (previous print):")
    print(tt.to_string(index=False))


# --------------------------------------------------------------------- D3
def d3_frequency(y: pd.Series) -> None:
    from Portfolio.admission.barrier import BarrierConfig, simulate_campaign
    print("\n=== D3  frequency arithmetic, and an UPPER BOUND on a rejected candidate ===")
    px = frozen_returns("XAUUSD")
    cfg = BarrierConfig(horizon_days=182)
    rows = []
    for label, sel in [("FULL_2007_2026", y.index == y.index),
                       ("DISCOVERY_2021_2026", y.index >= POST2021)]:
        yy = y[sel]
        net = (yy + SWAP - COST) / 1e4
        # daily book series: the sleeve is FLAT on every non-event day
        daily = pd.Series(0.0, index=px.index[px.index >= yy.index.min()])
        daily.loc[net.index] = net.to_numpy()
        duty = float((daily != 0).mean())
        ann = 1e4 * float(net.mean()) * len(yy) / ((yy.index.max() - yy.index.min()).days / 365.25)
        sd_ann = float(daily.std() * np.sqrt(252))
        for vm in (1.0, 14.0):
            res = simulate_campaign(daily, cfg=cfg, n_paths=3000, mean_block=10.0,
                                    seed=11, scale=vm)
            rows.append(dict(sample=label, vm=vm, duty_cycle=round(duty, 4),
                             trades_per_year=round(len(yy) / ((yy.index.max() - yy.index.min()).days / 365.25), 1),
                             net_ann_bps=round(ann, 1),
                             sharpe_solo=round(daily.mean() / daily.std() * np.sqrt(252), 3),
                             **res.as_dict()))
    d = pd.DataFrame(rows)
    d.to_csv(f"{OUT}/d3_barrier_upper_bound.csv", index=False)
    print(d.to_string(index=False))


def main() -> None:
    warnings.simplefilter("ignore")
    r = frozen_returns("XAUUSD")
    entry = pd.DatetimeIndex([d - pd.Timedelta(days=1) for d in bls_dates("cpi")])
    y = r[r.index.isin(entry)]
    d1_intraday()
    d2_regime(y)
    d3_frequency(y)


if __name__ == "__main__":
    main()
