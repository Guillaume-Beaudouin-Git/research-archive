"""
h2_phase1_surface.py — bulletproof H2's null: is the absent post-news continuation a window/event artifact?
Grid: impulse_win {15,30} x hold_win {30,60,120} x event-set {all USD-HIGH, majors NFP/CPI/FOMC}.
Grid-aligned to the 15-min cache. Each cell counts toward N. (Sub-15min impulse not viable: entry at r+5
pays the seconds-long spread spike -> cost-dead by construction; reported as a boundary.)
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

import fx_intraday_lib as L
import funnel_lib as F

RES = Path(__file__).parent / "results"
CAL = Path("<HOME>/Desktop/Algo_claude/data/deep_history_utc/calendar/economic_calendar_2018_2026.csv")
PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]


def release_times(event_set="all") -> pd.DatetimeIndex:
    df = pd.read_csv(CAL); df["dt"] = pd.to_datetime(df["datetime_utc"])
    m = (df["currency"] == "USD") & (df["impact"].astype(str).str.upper() == "HIGH")
    if event_set == "majors":
        m = m & df["event"].str.contains("Non Farm|Inflation Rate|Fed Interest Rate|FOMC", case=False, na=False)
    return pd.DatetimeIndex(sorted(df.loc[m, "dt"].dt.floor("15min").unique()))


def nw_t(s, maxlags=6):
    s = pd.Series(s).dropna().to_numpy()
    if len(s) < 30 or s.std() < 1e-18:
        return 0.0
    return float(sm.OLS(s, np.ones(len(s))).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags}).tvalues[0])


def cell(rel, imp_win, hold_win):
    """pooled continuation HAC-t (impulse->cont) + net sign-portfolio across 3 pairs."""
    xs, ys, daily_net, gpt, cpt = [], [], {}, [], []
    for s in PAIRS:
        b = L.load_bars(s).set_index("ts").sort_index()
        o, sp = b["open"], b["spread_med"]
        px_r = o.reindex(rel).to_numpy()
        px_i = o.reindex(rel + pd.Timedelta(minutes=imp_win)).to_numpy()           # impulse end
        px_e = o.reindex(rel + pd.Timedelta(minutes=imp_win + 15)).to_numpy()      # entry (delay+1)
        px_x = o.reindex(rel + pd.Timedelta(minutes=imp_win + hold_win)).to_numpy()  # exit
        sp_e = sp.reindex(rel + pd.Timedelta(minutes=imp_win + 15)).to_numpy()
        sp_x = sp.reindex(rel + pd.Timedelta(minutes=imp_win + hold_win)).to_numpy()
        t = pd.DataFrame(dict(impulse=np.log(px_i) - np.log(px_r), cont=np.log(px_x) - np.log(px_i),
                              trade=np.log(px_x) - np.log(px_e), px_e=px_e, px_x=px_x, sp_e=sp_e, sp_x=sp_x),
                         index=rel).dropna(subset=["impulse", "cont", "trade"])
        xs.append(t["impulse"].to_numpy()); ys.append(t["cont"].to_numpy())
        pos = np.sign(t["impulse"]); gross = pos * t["trade"]
        cost = 0.5 * F.rt_cost_fraction(s, t["sp_e"].to_numpy(), t["px_e"].to_numpy()) \
             + 0.5 * F.rt_cost_fraction(s, t["sp_x"].to_numpy(), t["px_x"].to_numpy()) + 1.0e-4
        daily_net[s] = (gross - cost).rename(s); gpt.append(float(gross.mean()) * 1e4); cpt.append(float(cost.mean()) * 1e4)
    X, Y = np.concatenate(xs), np.concatenate(ys)
    res = sm.OLS(Y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    Nn = pd.concat(daily_net.values(), axis=1, sort=True).mean(axis=1)
    return dict(cont_t=round(float(res.tvalues[1]), 2), gross_bps=round(float(np.mean(gpt)), 3),
                cost_bps=round(float(np.mean(cpt)), 3), ratio=round(float(np.mean(gpt) / np.mean(cpt)), 3),
                net_sharpe=round(F.ann_sharpe(Nn), 3), n=int(len(X) // 3))


def main():
    out = {}
    print(f"{'set':8s} {'imp':>4s} {'hold':>5s} | {'cont_t':>7s} {'gross':>6s} {'cost':>6s} {'ratio':>6s} {'netSh':>7s}")
    best = None
    for es in ["all", "majors"]:
        rel = release_times(es)
        for iw in [15, 30]:
            for hw in [30, 60, 120]:
                c = cell(rel, iw, hw); out[f"{es}_i{iw}_h{hw}"] = c
                print(f"{es:8s} {iw:>4d} {hw:>5d} | {c['cont_t']:>7.2f} {c['gross_bps']:>6.2f} "
                      f"{c['cost_bps']:>6.2f} {c['ratio']:>6.3f} {c['net_sharpe']:>7.2f}")
                if best is None or abs(c["cont_t"]) > abs(best[1]["cont_t"]):
                    best = (f"{es}_i{iw}_h{hw}", c)
    print(f"\nBEST |cont_t| cell: {best[0]} -> t={best[1]['cont_t']} (gate 2.5), "
          f"ratio={best[1]['ratio']} (bar 1.5), net_sharpe={best[1]['net_sharpe']}")
    (RES / "h2_phase1_surface.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
