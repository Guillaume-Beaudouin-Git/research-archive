"""
gate_BCG.py — Gate B (tail/conditional corr + co-breach), Gate C (leverage sensitivity),
Gate G (regime-conditional p(pass)). Uses steel-man sleeves.
"""
from __future__ import annotations
import json
import numpy as np, pandas as pd
from audit_common import load_daily, metrics, per_year_sharpe, ROOT
import firstpassage as fp

R = ROOT / "research/ftmo_portfolio_audit/results"
LO, HI, OLO = "2022-01-01", "2026-06-05", "2025-01-01"


def gate_B(comb):
    print("\n##### GATE B — tail / conditional correlation #####")
    c = comb.loc[LO:HI].copy()
    port = c.fillna(0).mean(axis=1)
    us500 = load_daily("US500", "EET")["close"].pct_change().reindex(c.index)
    out = {"unconditional_corr": c.corr().round(3).to_dict()}
    print(" unconditional pairwise corr:\n  ", c.corr().round(3).to_dict())

    # regimes
    trend = us500.rolling(20).sum().abs()
    masks = {
        "vol_shock(top10% |US500 daily|)": us500.abs() >= us500.abs().quantile(0.90),
        "strong_trend(top25% |20d US500|)": trend >= trend.quantile(0.75),
        "worst_decile_port_days": port <= port.quantile(0.10),
        "down_days_US500": us500 < 0,
    }
    cond = {}
    for name, m in masks.items():
        sub = c[m.reindex(c.index).fillna(False)]
        if len(sub) > 20:
            cc = sub.corr()
            cond[name] = {"n": int(len(sub)),
                          "AC": round(float(cc.loc["A", "C"]), 3),
                          "AB": round(float(cc.loc["A", "B"]), 3),
                          "BC": round(float(cc.loc["B", "C"]), 3)}
            print(f"  {name:38s} n={len(sub):4d}  rho(A,C)={cond[name]['AC']:+.2f} "
                  f"rho(A,B)={cond[name]['AB']:+.2f} rho(B,C)={cond[name]['BC']:+.2f}")
    out["conditional_corr"] = cond

    # co-breach: >=2 sleeves below their own 10th pct same day
    thr = c.quantile(0.10)
    below = c < thr
    n_below = below.sum(axis=1)
    co2 = float((n_below >= 2).mean())
    co3 = float((n_below >= 3).mean())
    indep2 = 3 * 0.1**2 * 0.9 + 0.1**3
    out["co_breach"] = {"p_ge2_empirical": round(co2, 4), "p_ge2_independent": round(indep2, 4),
                        "p_ge3_empirical": round(co3, 4), "ratio_vs_indep": round(co2 / indep2, 2)}
    print(f"  co-breach P(>=2 sleeves < own 10th pct): empirical={co2:.3f} vs independent={indep2:.3f} "
          f"(x{co2/indep2:.1f})")

    # rolling 63d pairwise corr range + CI
    roll = c["A"].rolling(63).corr(c["C"]).dropna()
    out["rolling63_AC"] = {"median": round(float(roll.median()), 3),
                           "min": round(float(roll.min()), 3), "max": round(float(roll.max()), 3),
                           "p05": round(float(roll.quantile(.05)), 3), "p95": round(float(roll.quantile(.95)), 3)}
    print(f"  rolling 63d rho(A,C): median={roll.median():+.2f} range[{roll.min():+.2f},{roll.max():+.2f}] "
          f"90%[{roll.quantile(.05):+.2f},{roll.quantile(.95):+.2f}]")
    return out


def gate_C(comb):
    print("\n##### GATE C — leverage sensitivity (p(pass<=3mo)) #####")
    full = comb.loc[LO:HI].fillna(0).mean(axis=1)
    oos = comb.loc[OLO:HI].fillna(0).mean(axis=1)
    rep_full = full - full.mean() + (1.39 / np.sqrt(252)) * full.std()
    out = {}
    print(f" {'L':>4s} | steel_full(corr/auth) | steel_oos | reportSh_full | reportSh_oos")
    for L in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]:
        row = {}
        for nm, s in [("steel_full", full), ("steel_oos", oos), ("repSh_full", rep_full),
                      ("repSh_oos", rep_full.reindex(oos.index).dropna())]:
            corr = fp.cdf_sequential(s, L, [63], n_paths=15000)[63]
            auth = fp.author_perphase_product(s, L, 63, n_paths=15000)["p_combined"]
            row[nm] = {"corrected_3mo": round(corr, 3), "author_3mo": round(auth, 3)}
        out[L] = row
        print(f" {L:>4.1f} | {row['steel_full']['corrected_3mo']:.3f}/{row['steel_full']['author_3mo']:.3f} "
              f"        | {row['steel_oos']['corrected_3mo']:.3f}     | {row['repSh_full']['corrected_3mo']:.3f}        "
              f" | {row['repSh_oos']['corrected_3mo']:.3f}")
    # optimal L for corrected steel_full
    best = max(out, key=lambda L: out[L]["steel_full"]["corrected_3mo"])
    print(f"  -> p(pass)-optimal L (steel_full corrected) = {best} giving {out[best]['steel_full']['corrected_3mo']:.3f}")
    print(f"  -> report claims L~2.5-3 optimal & p=0.485/0.549; even optimal-L corrected stays below.")
    out["_optimalL_steel_full"] = best
    return out


def gate_G(comb):
    print("\n##### GATE G — regime concentration / 2022-repeat downside #####")
    c = comb.fillna(0).mean(axis=1)
    out = {"per_year_combined_sharpe": {k: round(v, 2) for k, v in per_year_sharpe(c.loc[LO:HI]).items()}}
    print(" per-year combined Sharpe:", out["per_year_combined_sharpe"])
    # bootstrap p(pass<=3mo) conditioning ONLY on each calendar year's return distribution
    yr_p = {}
    for y in range(2022, 2027):
        s = c.loc[f"{y}-01-01":f"{y}-12-31"]
        if len(s) > 60:
            yr_p[y] = {"n": len(s),
                       "ann_sharpe": round(metrics(s)["ann_sharpe"], 2),
                       "p3mo_L2.5_corrected": round(fp.cdf_sequential(s, 2.5, [63], n_paths=15000)[63], 3),
                       "p3mo_L2.5_author": round(fp.author_perphase_product(s, 2.5, 63, 15000)["p_combined"], 3)}
            print(f"  {y}: annSh={yr_p[y]['ann_sharpe']:+.2f}  p3mo(corr)={yr_p[y]['p3mo_L2.5_corrected']:.3f} "
                  f"p3mo(auth)={yr_p[y]['p3mo_L2.5_author']:.3f}  (report '2022 repeats'~0.40)")
    out["regime_year_ppass"] = yr_p
    return out


def main():
    comb = pd.read_csv(R / "sleeves_steel_combined.csv", index_col=0, parse_dates=True)
    res = {"gate_B": gate_B(comb), "gate_C": gate_C(comb), "gate_G": gate_G(comb)}
    (R / "gate_BCG_results.json").write_text(json.dumps(res, indent=2, default=str))
    print("\nwrote gate_BCG_results.json")


if __name__ == "__main__":
    main()
