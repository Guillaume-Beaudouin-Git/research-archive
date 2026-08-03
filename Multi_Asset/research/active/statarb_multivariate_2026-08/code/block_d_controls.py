"""BLOC D — batterie de contrôles sur les SEULS candidats qui franchissent le gate.

Candidats issus du post-hoc B2 : GER40->US30 (h=60) et XAGUSD->XAUUSD (h=120),
conditionnés sur |mouvement du meneur| >= quantile q.

Contrôles, dans l'ordre où ils peuvent tuer :
  D1  LATENCE      — delay d in {1,2,5,10,15} min sur l'ENTRÉE (sortie décalée d'autant,
                     h constant). Si l'edge meurt à d=5, il est de tier HFT, pas retail.
  D2  WALK-FORWARD — 5 folds contigus (hard rule >= 5 folds). Un edge porté par un seul
                     fold (2020) n'est pas un edge.
  D3  TWO-SIDED    — L25, jambes DISJOINTES : gross et t sur la jambe LONGUE et la jambe
                     COURTE séparément.
  D4  PLACEBO      — décalage circulaire du signal, 1000 tirages. Préserve
                     l'autocorrélation des DEUX séries. p = P(gross_placebo >= observé).
  D5  L38          — R² du P&L quotidien de la sleeve contre un buy-and-hold vol-targeté
                     du SUIVEUR. R² > 30 % => pas une sleeve neuve, c'est du beta timé.
  D6  DSR          — dsr.py racine, n_trials = 132 (84 pré-enregistrées + 48 post-hoc).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

# dsr.py vit à la racine du repo — résolue relativement à ce fichier, jamais en dur
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5)))

M1DIR = sys.argv[1] if len(sys.argv) > 1 else "m1"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else "."

CAND = [("GER40", "US30", 60, 0.95, 1.47),
        ("GER40", "US30", 60, 0.80, 1.47),
        ("XAGUSD", "XAUUSD", 120, 0.95, 1.84),
        ("XAGUSD", "XAUUSD", 120, 0.90, 1.84)]
N_TRIALS = 132
RNG = np.random.default_rng(20260803)


def hac_t(x, lags=6):
    if len(x) < 30 or np.allclose(x, 0):
        return np.nan
    return float(sm.OLS(x, np.ones(len(x))).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags}).tvalues[0])


def build(lead_s, foll_s, h, delay, m1):
    """Signal / forward return / timestamp, entry delayed `delay` bars (L59)."""
    L, F = m1[lead_s], m1[foll_s]
    idx = L.index.intersection(F.index)
    lc = np.log(L["close"].reindex(idx).to_numpy())
    fc = np.log(F["close"].reindex(idx).to_numpy())
    zr = L["zr"].reindex(idx).to_numpy()
    tmin = idx.asi8 // 60_000_000_000
    n = len(idx)
    i = np.arange(h, n - h - delay - 1, h)
    ok = ((tmin[i] - tmin[i - h] == h) &
          (tmin[i + h + delay] - tmin[i + delay] == h))
    sig = lc[i] - lc[i - h]
    ok &= (sig != 0) & (~zr[i])
    i, sig = i[ok], sig[ok]
    fwd = fc[i + h + delay] - fc[i + delay]
    return sig, fwd, idx[i]


def main():
    m1 = {}
    for a, b, *_ in CAND:
        for s in (a, b):
            if s not in m1:
                m1[s] = pd.read_parquet(os.path.join(M1DIR, f"{s}.parquet"))

    all_rows = []
    for lead_s, foll_s, h, q, cost in CAND:
        tag = f"{lead_s}->{foll_s} h={h} q={q}"
        print("\n" + "=" * 74)
        print(f"CANDIDAT {tag}   coût {cost} bps")
        print("=" * 74)

        # ---- D1 latence -------------------------------------------------
        print("D1 LATENCE (delay sur l'entrée, h constant)")
        base = None
        for d in (1, 2, 5, 10, 15):
            sig, fwd, ts = build(lead_s, foll_s, h, d, m1)
            thr = np.quantile(np.abs(sig), q)
            m = np.abs(sig) >= thr
            pnl = np.sign(sig[m]) * fwd[m] * 1e4
            print(f"   d={d:>2}min  n={m.sum():>5}  gross={pnl.mean():+7.3f}bps  "
                  f"t={hac_t(pnl):+5.2f}  R={pnl.mean()/cost:+.3f}")
            if d == 1:
                base = (sig[m], fwd[m], ts[m], pnl)
        sig_m, fwd_m, ts_m, pnl = base

        # ---- D2 walk-forward -------------------------------------------
        print("D2 WALK-FORWARD (5 folds contigus)")
        folds = np.array_split(np.arange(len(pnl)), 5)
        f_pos = 0
        for k, fk in enumerate(folds):
            p = pnl[fk]
            pos = p.mean() > cost
            f_pos += pos
            print(f"   fold{k+1} {str(ts_m[fk[0]])[:10]}..{str(ts_m[fk[-1]])[:10]} "
                  f"n={len(p):>5} gross={p.mean():+7.3f} t={hac_t(p):+5.2f} "
                  f"R={p.mean()/cost:+.2f} {'PASS' if pos else 'fail'}")
        print(f"   folds nets positifs : {f_pos}/5")

        # ---- D3 two-sided ----------------------------------------------
        up, dn = sig_m > 0, sig_m < 0
        print(f"D3 TWO-SIDED (L25)   long n={up.sum()} gross={pnl[up].mean():+7.3f} "
              f"t={hac_t(pnl[up]):+5.2f} | short n={dn.sum()} "
              f"gross={pnl[dn].mean():+7.3f} t={hac_t(pnl[dn]):+5.2f}")

        # ---- D4 placebo à autocorrélation appariée ----------------------
        obs = pnl.mean()
        sgn = np.sign(sig_m)
        draws = np.empty(1000)
        for j in range(1000):
            k = RNG.integers(1, len(sgn))
            draws[j] = (np.roll(sgn, k) * fwd_m * 1e4).mean()
        p_pl = float((draws >= obs).mean())
        print(f"D4 PLACEBO (décalage circulaire, 1000 tirages)  "
              f"observé={obs:+.3f}  placebo médian={np.median(draws):+.3f}  "
              f"p95={np.quantile(draws,0.95):+.3f}  p={p_pl:.4f}")

        # ---- D5 L38 orthogonalité --------------------------------------
        dser = pd.Series(pnl, index=ts_m).groupby(pd.Series(ts_m).dt.normalize().values).sum()
        fpx = m1[foll_s]["close"]
        fpx = fpx[fpx.index.hour < 20]
        fd = fpx.groupby(fpx.index.normalize()).last()
        bh = np.log(fd).diff() * 1e4
        j = dser.index.intersection(bh.index)
        x = sm.add_constant(bh.reindex(j).fillna(0).to_numpy())
        fit = sm.OLS(dser.reindex(j).to_numpy(), x).fit(
            cov_type="HAC", cov_kwds={"maxlags": 6})
        r2 = float(fit.rsquared)
        print(f"D5 L38  beta={fit.params[1]:+.4f}  alpha_HAC t={fit.tvalues[0]:+.2f}  "
              f"R²={r2*100:.1f}%  {'ECHEC (>30%)' if r2 > 0.30 else 'ok'}")

        # ---- D6 DSR -----------------------------------------------------
        try:
            from dsr import deflated_sharpe_ratio, sampling_noise_floor_sr
            dv = dser.reindex(j).fillna(0).to_numpy() / 1e4
            sd = sampling_noise_floor_sr(periods_per_year=252, n_obs=len(dv))
            # rf=0 : la sleeve est intraday-flat (aucun financement overnight),
            # le P&L est déjà un excès sur cash par construction.
            out = deflated_sharpe_ratio(dv, n_trials=N_TRIALS, periods_per_year=252,
                                        rf=0.0, std_sr_trials=sd)
            dsr_v = out["dsr"] if isinstance(out, dict) else float(out)
            sr_d = dv.mean() / dv.std(ddof=1) * np.sqrt(252)
            print(f"D6 DSR  SR_quotidien(gross)={sr_d:+.3f}  sigma_SR_trials={sd:.3f}  "
                  f"DSR={dsr_v:.4f}  {'PASS' if dsr_v >= 0.95 else 'ECHEC'}")
        except Exception as e:
            print(f"D6 DSR  indisponible: {type(e).__name__}: {e}")
            dsr_v = np.nan

        all_rows.append(dict(lead=lead_s, follow=foll_s, h=h, q=q, n=len(pnl),
                             gross_bps=obs, R=obs / cost, t_hac=hac_t(pnl),
                             folds_pass=int(f_pos), p_placebo=p_pl, l38_r2=r2,
                             dsr=dsr_v))

    pd.DataFrame(all_rows).to_csv(os.path.join(OUTDIR, "block_d_controls.csv"),
                                  index=False)


if __name__ == "__main__":
    main()
