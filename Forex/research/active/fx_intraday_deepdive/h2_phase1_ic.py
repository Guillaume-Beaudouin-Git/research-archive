"""
h2_phase1_ic.py — H2 IC feasibility gate: post-USD-news intraday continuation (cheap close).

Frozen spec (PRE_REGISTRATION.md ADDENDUM): USD HIGH events 2018-2026, deduped unique release minutes.
impulse = log(px(r+15)) - log(px(r)); cont = log(px(r+60)) - log(px(r+15)). x = impulse/σ60(lagged).
Entry r+30 (delay+1), exit r+60. Two-sided. Gate: pooled HAC|t|>2.5, sign=continuation (>0), L34 cost.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as ss

import fx_intraday_lib as L
import funnel_lib as F

RES = Path(__file__).parent / "results"
CAL = Path("<HOME>/Desktop/Algo_claude/data/deep_history_utc/calendar/economic_calendar_2018_2026.csv")
PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]


def usd_high_release_times() -> pd.DatetimeIndex:
    df = pd.read_csv(CAL)
    df["dt"] = pd.to_datetime(df["datetime_utc"])
    m = (df["currency"] == "USD") & (df["impact"].astype(str).str.upper() == "HIGH")
    rel = df.loc[m, "dt"].dt.floor("15min")
    return pd.DatetimeIndex(sorted(rel.unique()))


def nw_t(s, maxlags=6):
    s = pd.Series(s).dropna().to_numpy()
    if len(s) < 30 or s.std() < 1e-18:
        return 0.0
    return float(sm.OLS(s, np.ones(len(s))).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags}).tvalues[0])


def event_table(sym: str, rel: pd.DatetimeIndex) -> pd.DataFrame:
    b = L.load_bars(sym).set_index("ts").sort_index()
    o = b["open"]; sp = b["spread_med"]
    def px(k):  # open at r + k minutes
        return o.reindex(rel + pd.Timedelta(minutes=k)).to_numpy()
    def spread(k):
        return sp.reindex(rel + pd.Timedelta(minutes=k)).to_numpy()
    t = pd.DataFrame(index=rel)
    t["px_r"] = px(0); t["px_15"] = px(15); t["px_30"] = px(30); t["px_60"] = px(60)
    t["sp_30"] = spread(30); t["sp_60"] = spread(60)
    t["impulse"] = np.log(t["px_15"]) - np.log(t["px_r"])
    t["cont"] = np.log(t["px_60"]) - np.log(t["px_15"])
    t["trade_ret"] = np.log(t["px_60"]) - np.log(t["px_30"])     # delay+1 entry at r+30
    t = t.dropna(subset=["impulse", "cont", "trade_ret"])
    t["x"] = t["impulse"] / t["impulse"].shift(1).rolling(60, min_periods=20).std(ddof=0)
    return t.dropna(subset=["x"])


def per_pair(rel):
    rows, daily = {}, {}
    for s in PAIRS:
        t = event_table(s, rel)
        x, y = t["x"].to_numpy(), t["cont"].to_numpy()
        res = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
        pos = np.sign(t["x"]); gross = pos * t["trade_ret"]
        cost = 0.5 * F.rt_cost_fraction(s, t["sp_30"].to_numpy(), t["px_30"].to_numpy(), stress=1.0) \
             + 0.5 * F.rt_cost_fraction(s, t["sp_60"].to_numpy(), t["px_60"].to_numpy(), stress=1.0)
        cost = cost + 1.0e-4                                      # +1 tick news slippage (RT, fraction)
        net = gross - cost
        yrs = (t.index[-1] - t.index[0]).days / 365.25
        rows[s] = dict(n=int(len(t)), per_yr=round(len(t) / yrs, 1),
                       corr_imp_cont=round(float(np.corrcoef(t["impulse"], t["cont"])[0, 1]), 4),
                       hac_t=round(float(res.tvalues[1]), 3),
                       spearman=round(float(ss.spearmanr(x, y).statistic), 4),
                       gross_bps=round(float(gross.mean()) * 1e4, 3),
                       cost_bps=round(float(cost.mean()) * 1e4, 3),
                       gross_sharpe=round(F.ann_sharpe(gross), 3), net_sharpe=round(F.ann_sharpe(net), 3),
                       gross_t=round(nw_t(gross), 3))
        daily[s] = (pos * t["trade_ret"]).rename(s)
    port = pd.concat(daily.values(), axis=1, sort=True).mean(axis=1)
    return rows, dict(port_gross_sharpe=round(F.ann_sharpe(port), 3), port_gross_hac_t=round(nw_t(port), 3),
                      port_n=int(port.dropna().shape[0]))


def direction_split(rel):
    up, dn = [], []
    for s in PAIRS:
        t = event_table(s, rel); g = np.sign(t["x"]) * t["trade_ret"]
        up.append(g[t["impulse"] > 0]); dn.append(g[t["impulse"] < 0])
    U = pd.concat(up); D = pd.concat(dn)
    return dict(cont_up_bps=round(float(U.mean()) * 1e4, 3), cont_up_t=round(nw_t(U), 3), n_up=int(len(U)),
                cont_dn_bps=round(float(D.mean()) * 1e4, 3), cont_dn_t=round(nw_t(D), 3), n_dn=int(len(D)))


def main():
    rel = usd_high_release_times()
    rows, pool = per_pair(rel)
    ds = direction_split(rel)
    gpt = np.mean([v["gross_bps"] for v in rows.values()])
    cpt = np.mean([v["cost_bps"] for v in rows.values()])
    out = dict(n_release_minutes=int(len(rel)), per_pair=rows, pooled=pool, direction_split=ds,
               L34_preflight=dict(gross_bps=round(float(gpt), 3), cost_bps=round(float(cpt), 3),
                                  ratio=round(float(gpt / cpt), 3), bar=1.5, pass_=bool(gpt / cpt >= 1.5)))
    sign_cont = np.mean([v["corr_imp_cont"] for v in rows.values()]) > 0
    out["GATE"] = dict(port_hac_t=pool["port_gross_hac_t"], sign_continuation=bool(sign_cont),
                       F1_pass=bool(abs(pool["port_gross_hac_t"]) > 2.5),
                       GATE_PASS=bool(abs(pool["port_gross_hac_t"]) > 2.5 and sign_cont
                                      and out["L34_preflight"]["pass_"]))
    (RES / "h2_phase1_ic.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
