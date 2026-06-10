"""
h3_phase1_scan.py — H3 controlled day-of-week x session seasonal scan (decisive falsification).

100 cells = 10 FX x 5 weekdays x 2 sessions (London 07->16, NY 13->20 UTC, intraday-flat). Each cell:
gross mean session-return + NW(6) t. Plus a causal WF day-of-week sleeve (sign = expanding same-weekday
mean, lagged; equal-risk across pairs), net of real cost. Gate: best gross cell vs noise floor @N=240;
WF sleeve net Sharpe vs floor + DSR(P)>0.5 + L34. If none clears -> seasonal space burned.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm

import fx_intraday_lib as L
import funnel_lib as F
from dsr import deflated_sharpe_ratio

RES = Path(__file__).parent / "results"
N_CUM = 240                      # 140 + 100 scan cells
_G = 0.5772156649015329
SESSIONS = {"london": (7, 16), "ny": (13, 20)}


def e_max_iid(n):
    return (1 - _G) * norm.ppf(1 - 1.0 / n) + _G * norm.ppf(1 - 1.0 / (n * math.e)) if n > 1 else 0.0


def nw_t(s, maxlags=6):
    s = pd.Series(s).dropna().to_numpy()
    if len(s) < 30 or s.std() < 1e-18:
        return 0.0
    return float(sm.OLS(s, np.ones(len(s))).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags}).tvalues[0])


def session_returns(sym, open_hh, exit_hh):
    b = L.load_bars(sym)
    op = L._anchor(b, open_hh, 0); ex = L._anchor(b, exit_hh, 0)
    op = op[op.index.dayofweek < 5]
    t = pd.DataFrame(index=op.index)
    t["px_o"] = op["px"]; t["px_x"] = ex["px"].reindex(op.index)
    t["sp_o"] = op["sp"]; t["sp_x"] = ex["sp"].reindex(op.index)
    t["ret"] = np.log(t["px_x"]) - np.log(t["px_o"])
    t["dow"] = t.index.dayofweek
    t["cost"] = 0.5 * F.rt_cost_fraction(sym, t["sp_o"].to_numpy(), t["px_o"].to_numpy()) \
              + 0.5 * F.rt_cost_fraction(sym, t["sp_x"].to_numpy(), t["px_x"].to_numpy())
    return t.dropna(subset=["ret", "cost"])


def wf_seasonal(t):
    """Causal WF: position = sign(expanding mean of prior same-weekday session returns)."""
    pos = pd.Series(0.0, index=t.index)
    for w in range(5):
        m = t["dow"] == w
        em = t.loc[m, "ret"].expanding(min_periods=20).mean().shift(1)
        pos.loc[m] = np.sign(em).fillna(0.0)
    net = pos * t["ret"] - t["cost"] * pos.abs()
    return net, pos


def main():
    cells, sleeves = [], {}
    for sess, (oh, xh) in SESSIONS.items():
        pair_nets = {}
        for s in L.ALL_FX:
            t = session_returns(s, oh, xh)
            net, _ = wf_seasonal(t)
            pair_nets[s] = net.rename(s)
            for w in range(5):
                r = t.loc[t["dow"] == w, "ret"]
                c = t.loc[t["dow"] == w, "cost"]
                cells.append(dict(pair=s, sess=sess, dow=int(w), n=int(len(r)),
                                  gross_bps=round(float(r.mean()) * 1e4, 3),
                                  gross_t=round(nw_t(r), 2),
                                  net_bps=round(float((np.sign(r.mean()) * r - c).mean()) * 1e4, 3)))
        sleeves[sess] = F.combine_inv_vol(pair_nets)
    # combined WF sleeve (London + NY equal-risk)
    sleeve = F.combine_inv_vol({"london": sleeves["london"], "ny": sleeves["ny"]})
    cdf = pd.DataFrame(cells)
    T = int(sleeve.dropna().shape[0]); se0 = math.sqrt(252.0 / T); floor = se0 * e_max_iid(N_CUM)
    d = deflated_sharpe_ratio(sleeve.dropna().to_numpy(), n_trials=N_CUM, periods_per_year=252, rf=0.0)
    pf = F.p_funded(sleeve, sigma_d=0.01)
    # gross-cell noise: best |t| of 100 cells vs expected max
    best_gross = cdf.loc[cdf["gross_t"].abs().idxmax()]
    cell_floor_t = math.sqrt(252.0 / int(best_gross["n"])) * e_max_iid(100) / math.sqrt(252.0 / int(best_gross["n"]))
    out = dict(
        n_cells=len(cdf), N_cumulative=N_CUM,
        sleeve_net_sharpe=round(F.ann_sharpe(sleeve), 3), noise_floor_sharpe=round(floor, 3),
        sleeve_beats_floor=bool(F.ann_sharpe(sleeve) > floor),
        sleeve_DSR_P=round(d["dsr"], 4), sleeve_p_funded=round(pf["p_combined"], 4),
        best_gross_cell=dict(pair=best_gross["pair"], sess=best_gross["sess"], dow=int(best_gross["dow"]),
                             gross_t=float(best_gross["gross_t"]), gross_bps=float(best_gross["gross_bps"]),
                             net_bps=float(best_gross["net_bps"]), n=int(best_gross["n"])),
        n_cells_grosst_gt_2p5=int((cdf["gross_t"].abs() > 2.5).sum()),
        n_cells_grosst_gt_3=int((cdf["gross_t"].abs() > 3.0).sum()),
        expected_max_t_100cells=round(e_max_iid(100), 2),
        n_cells_net_positive=int((cdf["net_bps"] > 0).sum()),
        cells_grosst_gt_2p5=cdf[cdf["gross_t"].abs() > 2.5][["pair", "sess", "dow", "gross_t", "gross_bps", "net_bps"]].to_dict("records"),
    )
    (RES / "h3_phase1_scan.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "cells_grosst_gt_2p5"}, indent=2))
    print("\nCells with |gross_t|>2.5 (pre-deflation; expected ~%.0f by chance among 100 at |t|>2.5):"
          % (100 * 2 * (1 - norm.cdf(2.5))))
    for c in out["cells_grosst_gt_2p5"]:
        print(f"  {c['pair']:7s} {c['sess']:7s} dow={c['dow']} gross_t={c['gross_t']:+.2f} "
              f"gross={c['gross_bps']:+.2f}bps net={c['net_bps']:+.2f}bps")


if __name__ == "__main__":
    main()
