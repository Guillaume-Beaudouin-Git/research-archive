"""
gate_DEF.py — Gate D (BTC cost stress -> p(pass)), Gate E (+1-bar exec lag -> p(pass)),
Gate F (DSR at N=100 and N=500).
"""
from __future__ import annotations
import json
import numpy as np, pandas as pd
from scipy.stats import norm
from audit_common import load_m1, metrics, ROOT
from sleeve_bc import build_bars, backtest
import firstpassage as fp

R = ROOT / "research/ftmo_portfolio_audit/results"
LO, HI, OLO = "2022-01-01", "2026-06-05", "2025-01-01"
EULER = 0.5772156649


def ppass(series, L=2.5, H=63):
    return {"corrected": round(fp.cdf_sequential(series, L, [H], n_paths=15000)[H], 3),
            "author": round(fp.author_perphase_product(series, L, H, 15000)["p_combined"], 3)}


def gate_D(comb):
    print("\n##### GATE D — Sleeve B (BTC) cost stress -> portfolio p(pass<=3mo) #####")
    A, B, C = comb["A"], comb["B"], comb["C"]
    out = {}
    scenarios = {
        "baseline(B as-is)": B,
        "B_net_zero": B * 0.0,
        "B_net_negative(ann -0.5)": (B - B.mean() - (0.5 / np.sqrt(252)) * B.std()),
    }
    for name, Bx in scenarios.items():
        port = pd.concat([A, Bx, C], axis=1).loc[LO:HI].fillna(0).mean(axis=1)
        m = metrics(port)
        pp = ppass(port, 2.5, 63)
        ppL3 = ppass(port, 3.0, 63)
        out[name] = {"combined_ann_sharpe": round(m["ann_sharpe"], 2),
                     "p3mo_L2.5": pp, "p3mo_L3.0": ppL3}
        print(f"  {name:28s} combAnnSh={m['ann_sharpe']:+.2f}  p3mo(L2.5 corr/auth)={pp['corrected']:.3f}/{pp['author']:.3f}"
              f"  (L3.0 {ppL3['corrected']:.3f}/{ppL3['author']:.3f})")
    print("  -> losing B leaves a pure mean-reversion book (Gate-B regime-hedge gone) AND lowers Sharpe/p(pass).")
    return out


def gate_E(comb):
    print("\n##### GATE E — +1-bar execution lag on B & C -> p(pass) #####")
    A = comb["A"]
    btc = load_m1("BTCUSD", "panel")
    us30 = load_m1("US30", "deep")
    out = {}
    for lag in [0, 1]:
        barsB = build_bars(btc, "60min", 0, 21, drop_weekend=False)
        B = backtest(barsB, "BTCUSD", "mom", window=16, z_entry=2.5, daily_stop=0.03,
                     markup=2.0, commission_rt=0.00065, exec_lag=lag)["net"]
        barsC = build_bars(us30, "60min", 13, 21, drop_weekend=True)
        C = backtest(barsC, "US30", "mr", window=24, z_entry=1.5, daily_stop=0.02,
                     markup=2.0, exec_lag=lag)["net"]
        mB, mC = metrics(B.loc[LO:HI]), metrics(C.loc[LO:HI])
        port = pd.concat([A, B, C], axis=1).loc[LO:HI].fillna(0).mean(axis=1)
        pp = ppass(port, 2.5, 63)
        out[f"lag{lag}"] = {"B_annSh": round(mB["ann_sharpe"], 2), "C_annSh": round(mC["ann_sharpe"], 2),
                            "combined_annSh": round(metrics(port)["ann_sharpe"], 2), "p3mo_L2.5": pp}
        print(f"  lag={lag}: B_annSh={mB['ann_sharpe']:+.2f} C_annSh={mC['ann_sharpe']:+.2f} "
              f"comb={metrics(port)['ann_sharpe']:+.2f}  p3mo(corr/auth)={pp['corrected']:.3f}/{pp['author']:.3f}")
    print("  (Sleeve A daily MR is timing-robust by construction — entry/exit at daily open.)")
    return out


def dsr(returns, n_trials, sr_dispersion=None):
    """Bailey-Lopez de Prado Deflated Sharpe Ratio. returns: daily. Annualized reporting."""
    r = np.asarray(returns.dropna())
    T = len(r)
    sr_d = r.mean() / r.std(ddof=1)
    from scipy.stats import skew, kurtosis
    g3 = skew(r, bias=False)
    g4 = kurtosis(r, fisher=False, bias=False)        # non-excess
    var_sr = (1 - g3 * sr_d + ((g4 - 1) / 4.0) * sr_d ** 2) / (T - 1)
    se_sr = np.sqrt(max(var_sr, 1e-12))
    disp = sr_dispersion if sr_dispersion is not None else se_sr
    emax = disp * ((1 - EULER) * norm.ppf(1 - 1.0 / n_trials) +
                   EULER * norm.ppf(1 - 1.0 / (n_trials * np.e)))
    dsr_p = norm.cdf((sr_d - emax) / se_sr)
    return {"ann_sharpe": round(sr_d * np.sqrt(252), 3), "T": T, "skew": round(g3, 2),
            "kurt_excess": round(g4 - 3, 2), "E_maxSR_ann": round(emax * np.sqrt(252), 3),
            "DSR_prob": round(float(dsr_p), 3)}


def gate_F(comb):
    print("\n##### GATE F — DSR trial-count honesty #####")
    port = comb.loc[LO:HI].fillna(0).mean(axis=1)
    rep = port - port.mean() + (1.39 / np.sqrt(252)) * port.std()   # report-claimed Sharpe series
    out = {}
    for label, s in [("steelman_combined(ann~0.95)", port), ("report_claimed(ann1.39)", rep)]:
        out[label] = {}
        for N in [20, 100, 500, 1000]:
            d = dsr(s, N)
            out[label][f"N={N}"] = d
            print(f"  {label:30s} N={N:>4d}: annSh={d['ann_sharpe']} E[maxSR]={d['E_maxSR_ann']} DSR={d['DSR_prob']}")
    print("  report claims DSR 0.86 at N=100. honest trial count >> 100 (12 families x 11 FX x freqs x sessions x L).")
    return out


def main():
    comb = pd.read_csv(R / "sleeves_steel_combined.csv", index_col=0, parse_dates=True)
    res = {"gate_D": gate_D(comb), "gate_E": gate_E(comb), "gate_F": gate_F(comb)}
    (R / "gate_DEF_results.json").write_text(json.dumps(res, indent=2, default=str))
    print("\nwrote gate_DEF_results.json")


if __name__ == "__main__":
    main()
