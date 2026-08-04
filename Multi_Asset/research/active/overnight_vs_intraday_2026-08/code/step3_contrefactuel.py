"""Etape 3 — le contrefactuel : TENU vs ESQUIVE vs 24H comme TROIS STRATEGIES
comparables (memes dates, memes couts), plus difference appariee, bootstrap par
blocs, DSR et walk-forward.

Trois series, jours d'entree lundi+mardi, cout inclus :
  TENU     = ce que fait la sleeve deployee     (1 RT + 1 nuit de swap)
  ESQUIVE  = la seance cash qu'elle evite       (1 RT, 0 nuit de swap)
  24H      = ne jamais sortir                   (1 RT + 1 nuit de swap)

NOTE COUT — le brief suppose que tenir 24h "ajoute une nuit de swap". Ce n'est PAS
le cas et c'est verifiable : le rollover FTMO est a 00:00 serveur (23:00 CET) ;
22:05(D) -> 15:30(E) et 22:05(D) -> 22:05(E) franchissent le MEME et UNIQUE
rollover. Tenir 24h ne paie pas un centime de swap de plus. En chaine
(lundi 22:05 -> mercredi 15:30 d'un trait) il paie meme UN SEUL aller-retour au
lieu de deux : le 1 RT/evenement facture ici SUR-estime son cout de ~50%.
"""
from __future__ import annotations
import sys, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "code"))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude_tugofwar")
from common import hac_t, block_bootstrap_mean, sharpe_ann, ERA_CUT  # noqa
from dsr import deflated_sharpe_ratio, sampling_noise_floor_sr      # noqa

OUT = os.path.join(HERE, "results")
SEGS = ["tenu", "esquive", "h24"]
N_TRIALS = 12   # essais consommes par ce diagnostic : 3 segments x 2 instr x 2 eres


def load():
    d = pd.read_csv(os.path.join(OUT, "step1_segments.csv"), parse_dates=["D", "E"])
    d["era"] = np.where(d["D"] < ERA_CUT, "pre-2021", "post-2021")
    for s in SEGS:
        d[f"{s}_net"] = d[s] + d[f"swap_bps_{s}"] - d["rt_bps"]
    return d[d["dow_D"].isin([0, 1])].copy()


def series_frame(d: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par jour d'entree ; colonnes = les 3 series nettes, par instrument
    et combinees au poids reel du spec (0.6 par jambe)."""
    piv = {}
    for s in SEGS:
        w = d.pivot_table(index="D", columns="sym", values=f"{s}_net")
        w.columns = [f"{c}_{s}" for c in w.columns]
        piv[s] = w
    f = pd.concat(piv.values(), axis=1)
    for s in SEGS:
        # combinaison au poids du spec : weight_per_leg 0.6 sur chaque jambe
        f[f"BOOK_{s}"] = 0.6 * f[f"US100_{s}"] + 0.6 * f[f"GER40_{s}"]
    return f


def stat_block(x: pd.Series, obs_per_year: float, label: dict) -> dict:
    v = x.dropna().values
    m, t, n = hac_t(v)
    lo90, hi90, lo95, hi95 = block_bootstrap_mean(v, block=10)
    sr = sharpe_ann(v / 1e4, obs_per_year)
    try:
        floor = sampling_noise_floor_sr(len(v), periods_per_year=int(round(obs_per_year)))
        dd = deflated_sharpe_ratio(v / 1e4, n_trials=N_TRIALS,
                                   periods_per_year=int(round(obs_per_year)),
                                   std_sr_trials=floor, rf=0.0)
        dsr = float(dd["dsr"]) if isinstance(dd, dict) else float(dd)
    except Exception as e:                                     # pragma: no cover
        dsr = np.nan
        print("   [dsr]", e)
    return {**label, "mean_bps": m, "t_hac6": t, "N": n, "sharpe_ann": sr,
            "dsr": dsr, "boot_lo90": lo90, "boot_hi90": hi90,
            "boot_lo95": lo95, "boot_hi95": hi95}


def main():
    d = load()
    f = series_frame(d)
    f.to_csv(os.path.join(OUT, "step3_series.csv"))
    years = (f.index.max() - f.index.min()).days / 365.25
    opy = len(f) / years
    print(f"{len(f)} jours d'entree sur {years:.1f} ans -> {opy:.0f} evenements/an "
          f"(annualisation en sqrt({opy:.0f}), L47)")

    rows = []
    for leg in ("US100", "GER40", "BOOK"):
        for era in ("pre-2021", "post-2021", "TOTAL"):
            sub = f if era == "TOTAL" else f[(f.index < ERA_CUT) if era == "pre-2021"
                                             else (f.index >= ERA_CUT)]
            for s in SEGS:
                rows.append(stat_block(sub[f"{leg}_{s}"], opy,
                                       {"leg": leg, "era": era, "strategy": s}))
    tab = pd.DataFrame(rows)
    tab.to_csv(os.path.join(OUT, "step3_three_series.csv"), index=False)

    print("\n" + "=" * 108)
    print("TROIS SERIES COMPARABLES — net de couts, jours lundi+mardi, bps/evenement")
    print("=" * 108)
    for leg in ("US100", "GER40", "BOOK"):
        print(f"\n### {leg}")
        p = tab[tab.leg == leg].set_index(["strategy", "era"])[
            ["mean_bps", "t_hac6", "N", "sharpe_ann", "dsr", "boot_lo90", "boot_hi90"]]
        print(p.round(3).to_string())

    # ---- difference appariee 24H - TENU (= la seance esquivee, meme jours) ------
    print("\n" + "=" * 108)
    print("DIFFERENCE APPARIEE : 24H - TENU  (ce que la sortie en journee coute/rapporte)")
    print("=" * 108)
    rows = []
    for leg in ("US100", "GER40", "BOOK"):
        for era in ("pre-2021", "post-2021", "TOTAL"):
            sub = f if era == "TOTAL" else f[(f.index < ERA_CUT) if era == "pre-2021"
                                             else (f.index >= ERA_CUT)]
            diff = (sub[f"{leg}_h24"] - sub[f"{leg}_tenu"]).dropna()
            m, t, n = hac_t(diff.values)
            lo, hi, _, _ = block_bootstrap_mean(diff.values, block=10)
            rows.append({"leg": leg, "era": era, "mean_bps": m, "t_hac6": t, "N": n,
                         "boot_lo90": lo, "boot_hi90": hi})
    dt = pd.DataFrame(rows)
    dt.to_csv(os.path.join(OUT, "step3_paired_diff.csv"), index=False)
    print(dt.round(3).to_string(index=False))

    # ---- walk-forward expanding, 6 folds ---------------------------------------
    print("\n" + "=" * 108)
    print("WALK-FORWARD — 6 folds chronologiques egaux (le DSR ne voit pas la "
          "concentration de regime)")
    print("=" * 108)
    rows = []
    k = 6
    edges = np.array_split(np.arange(len(f)), k)
    for i, sl in enumerate(edges):
        sub = f.iloc[sl]
        for leg in ("US100", "GER40", "BOOK"):
            for s in SEGS:
                v = sub[f"{leg}_{s}"].dropna().values
                m, t, n = hac_t(v)
                rows.append({"fold": i + 1,
                             "from": str(sub.index.min().date()),
                             "to": str(sub.index.max().date()),
                             "leg": leg, "strategy": s, "mean_bps": m,
                             "t_hac6": t, "N": n,
                             "sharpe_ann": sharpe_ann(v / 1e4, opy)})
    wf = pd.DataFrame(rows)
    wf.to_csv(os.path.join(OUT, "step3_walkforward.csv"), index=False)
    for leg in ("US100", "GER40", "BOOK"):
        p = wf[wf.leg == leg].pivot_table(index=["fold", "from", "to"],
                                          columns="strategy", values="mean_bps")
        pos = (wf[wf.leg == leg].pivot_table(index="fold", columns="strategy",
                                             values="mean_bps") > 0).mean()
        print(f"\n### {leg} — moyenne bps par fold")
        print(p.round(2).to_string())
        print("  folds positifs :", {c: f"{v:.0%}" for c, v in pos.items()})

    # ---- correlation entre jambes (le book est-il vraiment diversifie ?) -------
    c = f[["US100_tenu", "GER40_tenu", "US100_esquive", "GER40_esquive"]].corr()
    c.to_csv(os.path.join(OUT, "step3_corr.csv"))
    print("\n--- correlation des jambes (net) ---")
    print(c.round(3).to_string())


if __name__ == "__main__":
    main()
