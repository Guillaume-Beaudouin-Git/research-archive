"""Q3 — robustness of the -3.5% basket drawdown + the 45% common factor.

(a) Decompose the report's -3.5%: gross+winsor+inverse-vol+common-window vs realistic (net 2bp,
    equal-weight, full-range, RAW intraday low). MC stationary-block-bootstrap the realistic maxDD.
(b) Effective bets N_eff = (Σλ)²/Σλ² (PCA). Diversification ratio. Common-factor adverse stress:
    on the worst common-down days, does the basket fall like ~1 sleeve or √N smaller?
Reuses overnight_series + basket_series.
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import overnight_series as OS
import basket_series as BS
OUT = HERE.parent / "results"
ANN = 252.0
SLEEVES = ("GOLD", "SILVER", "WTI")
SLEEVES4 = ("GOLD", "SILVER", "WTI", "SOYBEAN")


def mdd(r):
    eq = np.cumprod(1 + np.asarray(r)); return float((eq / np.maximum.accumulate(eq) - 1).min())


def main():
    res = {}

    # ---------- (a) decompose the -3.5% ----------
    print("=== (a) basket maxDD: report -3.5% vs realistic ===")
    # report-style: gross, winsorised, inverse-vol, common window (all 4)
    per_w = {nm: OS.build(nm, 0.0, winsorise=True) for nm in SLEEVES4}
    g = pd.DataFrame({nm: (per_w[nm]["pos"] * per_w[nm]["win_w"]) for nm in SLEEVES4}).dropna()
    wv = 1.0 / g.std()
    rep_basket = (g * wv).sum(axis=1) / wv.sum()
    res["report_style_gross_winsor_invvol_commonwin"] = dict(
        n=len(g), sharpe=round(float(rep_basket.mean()/rep_basket.std()*np.sqrt(ANN)), 2),
        maxDD=round(mdd(rep_basket.to_numpy())*100, 1))
    print(f"  report-style (gross/winsor/inv-vol/common {len(g)}d): maxDD {mdd(rep_basket.to_numpy())*100:.1f}%  (claim -3.5)")

    # realistic: net 2bp, equal-weight, full range, B3 and B4
    real = {}
    for tag, sl in [("B3", SLEEVES), ("B4", SLEEVES4)]:
        d = BS.build(sl, 2.0, winsorise=True)
        r = d["basket_net"].to_numpy()
        real[tag] = dict(n=len(d), sharpe=round(float(r.mean()/r.std()*np.sqrt(ANN)), 2),
                         maxDD_close=round(mdd(r)*100, 1),
                         worst_intraday_low=round(float(d["basket_low"].min()*100), 2))
        print(f"  realistic {tag} (net2bp/eq-wt/full {len(d)}d): maxDD(close) {real[tag]['maxDD_close']}%  "
              f"worst intraday-low {real[tag]['worst_intraday_low']}%")
    res["realistic"] = real

    # MC stationary-block-bootstrap of realistic B3 maxDD
    d3 = BS.build(SLEEVES, 2.0, winsorise=True); r3 = d3["basket_net"].to_numpy()
    n = len(r3); rng = np.random.default_rng(11); B = 2000; p = 0.1; md = np.empty(B)
    for b in range(B):
        idx = np.empty(n, int); i = rng.integers(0, n)
        for k in range(n):
            idx[k] = i; i = rng.integers(0, n) if rng.random() < p else (i + 1) % n
        md[b] = mdd(r3[idx])
    res["mc_maxDD_B3"] = dict(median=round(float(np.median(md)*100), 1),
                              p5_worst=round(float(np.percentile(md, 5)*100), 1),
                              p1_worst=round(float(np.percentile(md, 1)*100), 1))
    print(f"  MC maxDD B3 (raw net): median {np.median(md)*100:.1f}%  5th-worst {np.percentile(md,5)*100:.1f}%  "
          f"1st-worst {np.percentile(md,1)*100:.1f}%")

    # ---------- (b) effective bets + common-factor stress ----------
    print("\n=== (b) effective bets + common-factor stress ===")
    gross4 = g  # winsorised gross, common window
    corr = gross4.corr()
    lam = np.sort(np.linalg.eigvalsh(corr.to_numpy()))[::-1]
    n_eff = float(lam.sum()**2 / (lam**2).sum())
    res["pca"] = dict(pc1_pct=round(float(lam[0]/lam.sum()*100), 0),
                      eigs_pct=[round(float(e/lam.sum()*100), 0) for e in lam],
                      effective_bets=round(n_eff, 2), n_sleeves=len(SLEEVES4),
                      avg_pairwise_corr=round(float(corr.where(~np.eye(4,dtype=bool)).stack().mean()), 2),
                      gold_silver=round(float(corr.loc["GOLD","SILVER"]), 2))
    print(f"  PC1 {res['pca']['pc1_pct']:.0f}%  eigs {res['pca']['eigs_pct']}  N_eff {n_eff:.2f}/4  "
          f"avg corr {res['pca']['avg_pairwise_corr']}  GOLD-SILVER {res['pca']['gold_silver']}")

    # diversification ratio (vol): Σ w σ / σ_basket  (gross winsor)
    sig = gross4.std(); dr = float((wv*sig).sum()/wv.sum() / rep_basket.std())
    res["diversification_ratio_vol"] = round(dr, 2)
    # common-factor adverse: days where ALL 4 sleeves < 0 ("common down")
    alldown = (gross4 < 0).all(axis=1)
    bn = (gross4 * wv).sum(axis=1)/wv.sum()
    res["common_down"] = dict(frac_days=round(float(alldown.mean()), 3),
                              basket_mean_on_commondown_bp=round(float(bn[alldown].mean()*1e4), 1),
                              basket_worst_day_bp=round(float(bn.min()*1e4), 1),
                              mean_sleeve_worst_day_bp=round(float(np.mean([gross4[c].min() for c in gross4])*1e4), 1))
    print(f"  vol diversification ratio {dr:.2f}x | common-down days {alldown.mean()*100:.1f}% "
          f"(basket {bn[alldown].mean()*1e4:.1f}bp)")
    print(f"  basket worst day {bn.min()*1e4:.0f}bp vs mean-sleeve-worst-day {np.mean([gross4[c].min() for c in gross4])*1e4:.0f}bp "
          f"(if √N-diversified, basket worst << sleeve worst)")

    (OUT / "q3_basket.json").write_text(json.dumps(res, indent=2, default=str))
    print("\nwritten q3_basket.json")


if __name__ == "__main__":
    main()
