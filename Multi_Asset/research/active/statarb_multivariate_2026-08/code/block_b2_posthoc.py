"""BLOC B2 — contrôle POST-HOC, hors pré-enregistrement, en direction GÉNÉREUSE.

Motif : dans le bloc B, la meilleure cellule (GER40->US30, h=60) porte un IC de 0.086
avec t_HAC 4.70 sur 40 422 trades — un signal RÉEL — mais ne rend que 0.643 bps contre
1.47 bps de coût. Sous normalité bivariée une stratégie de SIGNE devrait rendre
0.798*rho*sigma_h = 2.42 bps ; elle en rend 0.64. L'IC est donc porté par les GRANDS
mouvements du meneur, et prendre le signe de chaque mouvement jette le conditionnement.

Le coût étant FIXE par trade et le gross croissant avec l'amplitude du meneur, c'est la
seule manière naturelle de franchir un gate de coût. Si le kill du bloc B ne survit pas
à ce contrôle, il est prématuré.

48 cellules post-hoc (4 sens x 3 horizons x 4 quantiles). Elles ne sont PAS
pré-enregistrées : tout PASS devrait passer Šidák(48) puis DSR, et serait au mieux un
candidat à pré-enregistrer pour un test OOS ultérieur.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

M1DIR = sys.argv[1] if len(sys.argv) > 1 else "m1"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else "."

DIRECTED = [("GER40", "US30"), ("US30", "GER40"),
            ("XAGUSD", "XAUUSD"), ("XAUUSD", "XAGUSD")]
HORIZONS = [30, 60, 120]
QUANTILES = [0.50, 0.80, 0.90, 0.95]
COST = {"US500": 1.82, "US100": 1.80, "US30": 1.47, "GER40": 1.73,
        "XAUUSD": 1.84, "XAGUSD": 3.00}
GATE = 1.5


def hac_t(x, lags=6):
    if len(x) < 30 or np.allclose(x, 0):
        return np.nan
    return float(sm.OLS(x, np.ones(len(x))).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags}).tvalues[0])


def series(lead_s, foll_s, h, m1):
    L, F = m1[lead_s], m1[foll_s]
    idx = L.index.intersection(F.index)
    lc = np.log(L["close"].reindex(idx).to_numpy())
    fc = np.log(F["close"].reindex(idx).to_numpy())
    zr = L["zr"].reindex(idx).to_numpy()
    tmin = idx.asi8 // 60_000_000_000
    n = len(idx)
    i = np.arange(h, n - h - 1, h)
    ok = (tmin[i] - tmin[i - h] == h) & (tmin[i + h + 1] - tmin[i + 1] == h)
    sig = lc[i] - lc[i - h]
    ok &= (sig != 0) & (~zr[i])
    i, sig = i[ok], sig[ok]
    fwd = fc[i + h + 1] - fc[i + 1]
    return sig, fwd


def main():
    m1 = {}
    for a, b in DIRECTED:
        for s in (a, b):
            if s not in m1:
                m1[s] = pd.read_parquet(os.path.join(M1DIR, f"{s}.parquet"))

    rows = []
    for lead_s, foll_s in DIRECTED:
        for h in HORIZONS:
            sig, fwd = series(lead_s, foll_s, h, m1)
            if len(sig) < 500:
                continue
            a = np.abs(sig)
            for q in QUANTILES:
                thr = np.quantile(a, q)
                m = a >= thr
                if m.sum() < 300:
                    continue
                pnl = np.sign(sig[m]) * fwd[m] * 1e4
                c = COST[foll_s]
                rows.append(dict(
                    lead=lead_s, follow=foll_s, h=h, q=q, n=int(m.sum()),
                    ic=float(np.corrcoef(sig[m], fwd[m])[0, 1]),
                    gross_bps=float(pnl.mean()), t_hac=hac_t(pnl),
                    cost_rt=c, R=float(pnl.mean()) / c))
                r = rows[-1]
                print(f"{lead_s:>7}->{foll_s:<7} h={h:>3} q={q:.2f} n={r['n']:>6} "
                      f"IC={r['ic']:+.4f} gross={r['gross_bps']:+7.3f}bps "
                      f"t={r['t_hac']:+6.2f} R={r['R']:+.3f}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTDIR, "block_b2_posthoc.csv"), index=False)
    print("\n" + "=" * 74)
    print(f"BLOC B2 post-hoc — {len(df)} cellules")
    print(f"max R = {df['R'].max():+.4f}   (gate {GATE})   "
          f"cellules R>={GATE} : {(df['R'] >= GATE).sum()}")
    print("\nTop 8 par R :")
    print(df.nlargest(8, "R")[["lead", "follow", "h", "q", "n", "ic",
                               "gross_bps", "t_hac", "cost_rt", "R"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("\ngross moyen par quantile de |mouvement du meneur| :")
    print(df.groupby("q").agg(mean_gross=("gross_bps", "mean"),
                              max_R=("R", "max")).to_string())


if __name__ == "__main__":
    main()
