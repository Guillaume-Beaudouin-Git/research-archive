"""BLOC B — terme de structure de l'avance-retard, jugé au GROSS.

Grille pré-enregistrée : 7 paires non ordonnées x 2 sens (L25, jambes disjointes)
x 6 horizons {1,5,15,30,60,120} min = 84 cellules.

Statistique principale : R = gross_par_trade / coût, au coût CENTRE, avec K=1 jambe
(on ne trade que le SUIVEUR). K=1 est la variante la MOINS chère, donc la plus
favorable : si elle échoue, la variante neutre à 2 jambes échoue a fortiori.

Contrôles : gross d'abord (cost_rt=0 dans la stat brute), L59 delay+1 sur l'entrée ET
la sortie, L60 barres à fourchette nulle exclues du signal, trades NON CHEVAUCHANTS,
t-stat HAC lag-6.

Lecture seule sur le repo principal ; le panneau M1 est reconstruit par m1build.py.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

M1DIR = sys.argv[1] if len(sys.argv) > 1 else "m1"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else "."

PAIRS = [
    ("GER40", "US500"), ("GER40", "US100"), ("GER40", "US30"),
    ("XAUUSD", "XAGUSD"), ("UKOIL", "USOIL"),
    ("COPPER", "AUDUSD"), ("GER40", "EURUSD"),
]
HORIZONS = [1, 5, 15, 30, 60, 120]

# Coût RT par jambe, bps. Centre = COST_AUDIT.md §5/§6 lorsqu'il est mesuré ;
# sinon spread médian NON NUL mesuré sur le panneau + 2 x 0.5 bps de dérapage.
COST_CENTRE = {
    "US500": 1.82, "US100": 1.80, "US30": 1.47, "GER40": 1.73,
    "XAUUSD": 1.84, "XAGUSD": 3.00, "EURUSD": 1.50,
    "AUDUSD": 1.86, "COPPER": 3.00, "UKOIL": 3.00, "USOIL": 3.00,
}
GATE = 1.5  # L43


def load(sym: str) -> pd.DataFrame:
    return pd.read_parquet(os.path.join(M1DIR, f"{sym}.parquet"))


def hac_t(x: np.ndarray, lags: int = 6) -> float:
    if len(x) < 30 or np.allclose(x, 0):
        return np.nan
    res = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.tvalues[0])


def cell(lead: pd.DataFrame, foll: pd.DataFrame, h: int) -> dict:
    """One (lead -> follower, horizon) cell, judged gross."""
    idx = lead.index.intersection(foll.index)
    L = lead.reindex(idx)
    F = foll.reindex(idx)

    lc = np.log(L["close"].to_numpy())
    fc = np.log(F["close"].to_numpy())
    n = len(idx)
    if n < 20_000:
        return {}

    # Contiguity: a window [i-h, i] is only valid if the clock gap matches h minutes
    # exactly (no session break, no hole). Same for the forward window.
    tmin = idx.asi8 // 60_000_000_000

    # NON-OVERLAPPING by construction: signals are sampled on a fixed grid of step h,
    # never chosen greedily (a greedy scan would select on the data).
    i = np.arange(h, n - h - 1, h)
    ok = (tmin[i] - tmin[i - h] == h) & (tmin[i + h + 1] - tmin[i + 1] == h)
    # L60: the lead must actually have moved and not be a stale/zero-range print
    sig = lc[i] - lc[i - h]
    ok &= (sig != 0) & (~L["zr"].to_numpy()[i])
    i, sig = i[ok], sig[ok]
    if len(i) < 500:
        return {}

    # L59: entry at follower close t+1, exit at follower close t+1+h
    fwd = fc[i + h + 1] - fc[i + 1]
    sig_n, fwd_n = sig, fwd

    ic = float(np.corrcoef(sig_n, fwd_n)[0, 1])
    pnl = np.sign(sig_n) * fwd_n * 1e4          # bps per trade, GROSS
    gross = float(pnl.mean())
    return {
        "n_trades": int(len(pnl)),
        "ic": ic,
        "gross_bps": gross,
        "sd_bps": float(pnl.std(ddof=1)),
        "t_hac": hac_t(pnl),
        "sigma_h_bps": float(np.std(fwd_n) * 1e4),
    }


def main() -> None:
    cache = {}
    rows = []
    for a, b in PAIRS:
        for s in (a, b):
            if s not in cache:
                cache[s] = load(s)
        for lead_s, foll_s in ((a, b), (b, a)):
            for h in HORIZONS:
                r = cell(cache[lead_s], cache[foll_s], h)
                if not r:
                    rows.append({"lead": lead_s, "follow": foll_s, "h": h,
                                 "status": "INSUFFICIENT"})
                    continue
                c = COST_CENTRE[foll_s]
                r.update(lead=lead_s, follow=foll_s, h=h, status="ok",
                         cost_rt=c, R=r["gross_bps"] / c,
                         need_gross=GATE * c)
                rows.append(r)
                print(f"{lead_s:>7}->{foll_s:<7} h={h:>3}  n={r['n_trades']:>6}  "
                      f"IC={r['ic']:+.4f}  gross={r['gross_bps']:+7.3f}bps  "
                      f"t={r['t_hac']:+6.2f}  sig_h={r['sigma_h_bps']:6.1f}  "
                      f"R={r['R']:+.3f}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTDIR, "block_b_cells.csv"), index=False)

    ok = df[df["status"] == "ok"]
    print("\n" + "=" * 74)
    print(f"BLOC B — {len(ok)} cellules évaluées sur 84 pré-enregistrées")
    print("=" * 74)
    print(f"max R (gate L43 = {GATE})           : {ok['R'].max():+.4f}")
    print(f"max gross_bps                       : {ok['gross_bps'].max():+.4f}")
    print(f"max |IC|                            : {ok['ic'].abs().max():.4f}")
    print(f"cellules avec R >= {GATE}              : {(ok['R'] >= GATE).sum()}")
    print(f"cellules avec gross > 0             : {(ok['gross_bps'] > 0).sum()}/{len(ok)}")
    print("\nTop 8 par R :")
    print(ok.nlargest(8, "R")[["lead", "follow", "h", "n_trades", "ic",
                               "gross_bps", "t_hac", "cost_rt", "R"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("\nIC moyen |.| par horizon (décroissance de l'information) :")
    print(ok.groupby("h").agg(mean_abs_ic=("ic", lambda s: s.abs().mean()),
                              mean_gross=("gross_bps", "mean"),
                              max_R=("R", "max")).to_string())
    verdict = "PASS-CANDIDATE" if (ok["R"] >= GATE).any() else "REJECTED"
    print(f"\nRègle de mort B : max R < {GATE} => REJECTED.  VERDICT = {verdict}")


if __name__ == "__main__":
    main()
