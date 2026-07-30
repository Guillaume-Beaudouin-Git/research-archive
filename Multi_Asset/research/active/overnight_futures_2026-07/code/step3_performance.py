"""Step 3 — performance, costs and sizing for the sleeves that reached this step.

Spec (frozen at step 1): LONG from the Globex reopen (18:00 ET) for 8 hours (exit
02:00 ET), gap EXCLUDED (entry is the first print at/after the reopen, so the halt
gap is never claimed), causal vol-target as in the source study, integer contracts.

Costs are the measured futures round-trip from step 0, applied to notional.
Annualisation is sqrt(obs/yr) measured empirically (L47).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from common import (ACCOUNT_USD, CONTRACTS, NOTIONAL, OUT, REPO, SLEEVES, cagr, hac_t,
                    max_dd, obs_per_year, sharpe, us_dst, vol_target)
from step1c_gap_decomposition import REOPEN_ET, WINDOW_HOURS, load_m1, price_at  # noqa

sys.path.insert(0, str(REPO / "yt_strategy_replications"))
from engine import stats as S  # noqa: E402

SLEEVE_LIST = ["GOLD", "SILVER", "WTI"]      # SOYBEAN has no CFD window (step 2b)
COST_BPS = {"GOLD": 0.66, "SILVER": 1.15, "WTI": 3.67}
COST_STRESS = {"GOLD": 0.91, "SILVER": 2.01, "WTI": 5.03}
MICRO = {"GOLD": "MGC", "SILVER": "SIL", "WTI": "MCL"}
H = np.int64(3_600_000_000_000)


def tradable_series(name: str) -> pd.Series:
    """Entry = first print at/after the reopen; exit = last print before window end.
    No pre-halt print required (that requirement dropped Sunday-evening sessions)."""
    sp = SLEEVES[name]
    df = load_m1(sp["cfd"], sp["sample_start"])
    ts = pd.DatetimeIndex(df["ts"])
    et = ts - pd.to_timedelta(np.where(us_dst(ts), 4, 5), unit="h")
    keys = et.asi8
    vals = df["close"].to_numpy()
    ro, hours = REOPEN_ET[name], WINDOW_HOURS[name]
    sess = pd.DatetimeIndex(np.unique(pd.DatetimeIndex(et).normalize()))
    base = (sess + pd.Timedelta(hours=ro)).asi8
    p0 = price_at(vals, keys, base, "first", 20)
    p1 = price_at(vals, keys, base + hours * H, "last", 30)
    s = pd.Series(np.log(p1 / p0), index=sess).dropna()
    s = s[np.isfinite(s.to_numpy())]
    lo, hi = s.quantile([0.005, 0.995])
    return s.clip(lo, hi)


rows, series = [], {}
for name in SLEEVE_LIST:
    win = tradable_series(name)
    series[name] = win
    pos = vol_target(win)
    ppy = obs_per_year(win)
    for label, cost in (("gross", 0.0), ("net_base", COST_BPS[name]),
                        ("net_stress", COST_STRESS[name]), ("net_cfd_1.5bp", 1.5)):
        net = (pos * win - pos.abs() * cost * 1e-4).dropna()
        net = net[net.index >= win.index[20]]
        mu, t = hac_t(net)
        d = S.deflated_sharpe_ratio(net.to_numpy(), n_trials=95, periods_per_year=ppy)
        r = dict(sleeve=name, cost_case=label, cost_bps=cost, N=len(net),
                 obs_per_yr=round(ppy, 1),
                 mean_bps=round(1e4 * net.mean(), 3),
                 SR=round(sharpe(net), 3), t_hac=round(t, 2),
                 DSR=round(float(d["dsr"]), 3),
                 vol_ann_pct=round(100 * net.std(ddof=1) * np.sqrt(ppy), 2),
                 CAGR_pct=round(100 * cagr(net), 2),
                 maxDD_pct=round(100 * max_dd(net), 1),
                 skew=round(float(pd.Series(net).skew()), 2))
        wf = S.fold_metrics(net.to_numpy(), n_folds=5, periods_per_year=ppy)
        r["WF"] = wf["wf_score"]
        r["fold_SR"] = wf["fold_sharpes"]
        rows.append(r)

perf = pd.DataFrame(rows)
pd.set_option("display.width", 300, "display.max_columns", 40)
print("=== per-sleeve, vol-targeted, per unit of NOTIONAL ===")
print(perf.to_string(index=False))
perf.to_csv(OUT / "step3_performance.csv", index=False)

# ---------------------------------------------------------------- alpha vs beta
print("\n=== beta check: sleeve ~ vol-matched buy&hold of the same underlying (L38) ===")
import statsmodels.api as sm  # noqa: E402
brows = []
for name in SLEEVE_LIST:
    sp = SLEEVES[name]
    h1 = pd.read_parquet(REPO / "yt_strategy_replications" / "data_cache" / "gold"
                         / f'{sp["cfd"]}_1h.parquet')
    daily = h1["close"].resample("1D").last().dropna()
    bh = np.log(daily / daily.shift(1)).dropna()
    net = (vol_target(series[name]) * series[name]).dropna()
    common = net.index.intersection(bh.index)
    y, x = net.reindex(common).to_numpy(), bh.reindex(common).to_numpy()
    m = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    brows.append(dict(sleeve=name, N=len(common), beta=round(float(m.params[1]), 4),
                      R2=round(float(m.rsquared), 4),
                      alpha_bps=round(1e4 * float(m.params[0]), 2),
                      alpha_t=round(float(m.tvalues[0]), 2)))
beta = pd.DataFrame(brows)
print(beta.to_string(index=False))
beta.to_csv(OUT / "step3_beta.csv", index=False)

# ------------------------------------------------------------- sizing on EUR13k
print("\n=== sizing on a $15,000 account (EUR 13,000) ===")
srows = []
for name in SLEEVE_LIST:
    win = series[name]
    pos = vol_target(win)
    net = (pos * win - pos.abs() * COST_BPS[name] * 1e-4).dropna()
    ppy = obs_per_year(net)
    mu_ann = float(net.mean()) * ppy
    sd_ann = float(net.std(ddof=1)) * np.sqrt(ppy)
    kelly = mu_ann / sd_ann ** 2                      # leverage in units of notional
    notional = NOTIONAL[MICRO[name]]
    marg = CONTRACTS[MICRO[name]]["margin"]
    for frac, tag in ((1.0, "full_Kelly"), (0.5, "half_Kelly"), (0.25, "quarter_Kelly")):
        lev = kelly * frac
        n_exact = lev * ACCOUNT_USD / notional
        n_int = int(np.floor(n_exact))
        srows.append(dict(sleeve=name, sizing=tag, kelly_leverage=round(kelly, 1),
                          target_leverage=round(lev, 2),
                          contracts_exact=round(n_exact, 2), contracts_int=n_int,
                          margin_used=round(n_int * marg),
                          margin_pct=round(100 * n_int * marg / ACCOUNT_USD, 1),
                          feasible=bool(n_int >= 1 and n_int * marg <= 0.5 * ACCOUNT_USD)))
    # what 1 contract actually is
    lev1 = notional / ACCOUNT_USD
    srows.append(dict(sleeve=name, sizing="1_contract(min)", kelly_leverage=round(kelly, 1),
                      target_leverage=round(lev1, 2), contracts_exact=1.0, contracts_int=1,
                      margin_used=round(marg), margin_pct=round(100 * marg / ACCOUNT_USD, 1),
                      feasible=bool(marg <= 0.5 * ACCOUNT_USD)))
    srows[-1]["kelly_fraction_of_1lot"] = round(lev1 / kelly, 3)
    # realised path at 1 contract
    acct = net * lev1
    srows[-1]["acct_vol_pct"] = round(100 * acct.std(ddof=1) * np.sqrt(ppy), 1)
    srows[-1]["acct_CAGR_pct"] = round(100 * cagr(acct), 1)
    srows[-1]["acct_maxDD_pct"] = round(100 * max_dd(acct), 1)

size = pd.DataFrame(srows)
print(size.to_string(index=False))
size.to_csv(OUT / "step3_sizing.csv", index=False)

pd.DataFrame(series).to_csv(OUT / "step3_sleeve_series.csv")
