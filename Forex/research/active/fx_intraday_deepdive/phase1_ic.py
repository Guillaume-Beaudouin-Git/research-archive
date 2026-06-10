"""
phase1_ic.py — H1 IC feasibility gate (cheap close BEFORE any full backtest).

Frozen spec (PRE_REGISTRATION.md §2): asian_start=23:00, open=07:00, exit=12:00 UTC, delay+1 entry.
Signal x_d = -asian_ret_d / sigma_lagged(60d). IC target = fwd_ret (07:00 -> 12:00).

Gate (ALL required): pooled PRIMARY HAC |t| > 2.5, sign = reversal (corr(asian_ret,fwd) < 0),
N >= 50/yr, deflated for Phase-0 variants. Reports the literal pooled-OLS HAC-t AND the
cross-pair-correlation-robust daily-portfolio HAC-t (honest), per-pair decomposition (F2 contrast),
directional split (F3), and the L34 gross-vs-cost pre-flight (F5).
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

import fx_intraday_lib as L
import funnel_lib as F

RES = Path(__file__).parent / "results"; RES.mkdir(exist_ok=True)
PPY = 252


def nw_t(series: pd.Series, maxlags: int = 6) -> float:
    """Newey-West t-stat of the mean of a daily series (H0: mean=0)."""
    s = series.dropna().to_numpy()
    if len(s) < 30 or s.std() < 1e-18:
        return 0.0
    res = sm.OLS(s, np.ones(len(s))).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    return float(res.tvalues[0])


def build_signal(sym, asian_start_hh=23, open_hh=7, exit_hh=12, delay_bars=1):
    t = L.session_table(sym, asian_start_hh=asian_start_hh, open_hh=open_hh,
                        exit_hh=exit_hh, delay_bars=delay_bars)
    sig = (-t["asian_ret"]) / t["asian_ret"].shift(1).rolling(60, min_periods=20).std(ddof=0)
    t = t.assign(x=sig).dropna(subset=["x", "fwd_ret"])
    return t


def per_pair(syms, **kw):
    rows = {}
    for s in syms:
        t = build_signal(s, **kw)
        h = L.hac_t(t["x"].to_numpy(), t["fwd_ret"].to_numpy(), maxlags=6)
        # sign-signal gross daily return (this pair), and per-trade gross/cost
        pos = np.sign(t["x"])
        gross = pos * t["fwd_ret"]
        cost = 0.5 * F.rt_cost_fraction(s, t["sp_entry"].to_numpy(), t["open_px"].to_numpy()) \
             + 0.5 * F.rt_cost_fraction(s, t["sp_exit"].to_numpy(), t["exit_px"].to_numpy())
        net = gross - cost
        yrs = (t.index[-1] - t.index[0]).days / 365.25
        rows[s] = dict(
            n=h["n"], per_yr=round(h["n"] / max(yrs, 1e-9), 1),
            corr_asian_fwd=round(float(np.corrcoef(t["asian_ret"], t["fwd_ret"])[0, 1]), 4),
            hac_t=round(h["t"], 3), pearson=round(h["pearson"], 4), spearman=round(h["spearman"], 4),
            gross_sharpe=round(F.ann_sharpe(gross), 3), net_sharpe=round(F.ann_sharpe(net), 3),
            gross_bps_per_trade=round(float(gross.mean()) * 1e4, 3),
            cost_bps_per_trade=round(float(cost.mean()) * 1e4, 3),
            cost_p95_bps=round(float(np.percentile(cost, 95)) * 1e4, 3),
            gross_t=round(nw_t(gross), 3),
        )
    return rows


def pooled(syms, **kw):
    """Stacked pooled OLS (literal pre-reg, SE-inflated: ignores cross-pair corr) +
    daily equal-weight sign-portfolio HAC-t (honest, cross-pair-corr-robust)."""
    xs, ys, daily = [], [], {}
    for s in syms:
        t = build_signal(s, **kw)
        xs.append(t["x"].to_numpy()); ys.append(t["fwd_ret"].to_numpy())
        daily[s] = (np.sign(t["x"]) * t["fwd_ret"]).rename(s)
    X = np.concatenate(xs); Y = np.concatenate(ys)
    res = sm.OLS(Y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    port = pd.concat(daily.values(), axis=1).mean(axis=1)        # equal-weight gross sign-portfolio
    return dict(
        stacked_slope=round(float(res.params[1]), 5), stacked_hac_t=round(float(res.tvalues[1]), 3),
        stacked_n=int(len(X)),
        port_gross_sharpe=round(F.ann_sharpe(port), 3), port_gross_hac_t=round(nw_t(port), 3),
        port_n_days=int(port.dropna().shape[0]),
    )


def direction_split(syms, **kw):
    """F3: gross of fade-up leg (asian_ret>0 -> short) vs fade-down leg, pooled."""
    up, dn = [], []
    for s in syms:
        t = build_signal(s, **kw)
        g = np.sign(t["x"]) * t["fwd_ret"]
        up.append(g[t["asian_ret"] > 0]); dn.append(g[t["asian_ret"] < 0])
    U = pd.concat(up); D = pd.concat(dn)
    return dict(fade_up_bps=round(float(U.mean()) * 1e4, 3), fade_up_t=round(nw_t(U), 3), n_up=int(len(U)),
                fade_dn_bps=round(float(D.mean()) * 1e4, 3), fade_dn_t=round(nw_t(D), 3), n_dn=int(len(D)))


def main():
    out = {"spec": dict(asian_start_hh=23, open_hh=7, exit_hh=12, delay_bars=1,
                        signal="x=-asian_ret/sigma60_lagged", target="fwd_ret 07:00->12:00 UTC")}
    out["primary_per_pair"] = per_pair(L.PRIMARY)
    out["contrast_per_pair"] = per_pair(L.CONTRAST)
    out["primary_pooled"] = pooled(L.PRIMARY)
    out["contrast_pooled"] = pooled(L.CONTRAST)
    out["primary_direction_split"] = direction_split(L.PRIMARY)
    # L34 pre-flight (F5): pooled primary gross-per-trade vs p95 cost
    gpt = np.mean([v["gross_bps_per_trade"] for v in out["primary_per_pair"].values()])
    cp95 = np.mean([v["cost_p95_bps"] for v in out["primary_per_pair"].values()])
    out["L34_preflight"] = dict(gross_bps=round(float(gpt), 3), cost_p95_bps=round(float(cp95), 3),
                                ratio=round(float(gpt / cp95), 3), bar=1.5, pass_=bool(gpt / cp95 >= 1.5))
    # gate verdict
    pp = out["primary_pooled"]; cp = out["contrast_pooled"]
    gate = dict(
        pooled_hac_t=pp["stacked_hac_t"], port_hac_t=pp["port_gross_hac_t"],
        sign_reversal=bool(np.mean([v["corr_asian_fwd"] for v in out["primary_per_pair"].values()]) < 0),
        F1_pass=bool(abs(pp["port_gross_hac_t"]) > 2.5),                 # honest gate on the portfolio t
        F2_primary_gt_contrast=bool(abs(pp["port_gross_hac_t"]) > abs(cp["port_gross_hac_t"])),
    )
    gate["GATE_PASS"] = bool(gate["F1_pass"] and gate["sign_reversal"] and gate["F2_primary_gt_contrast"]
                             and out["L34_preflight"]["pass_"])
    out["GATE"] = gate
    (RES / "phase1_ic.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
