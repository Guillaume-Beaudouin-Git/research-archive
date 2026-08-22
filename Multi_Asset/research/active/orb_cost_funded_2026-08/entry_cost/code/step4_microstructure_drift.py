"""Volet A / étape 4 — dérive de microstructure : le tick en bps a-t-il changé de poids ?

Le tick NQ est FIXE (0.25 pt) alors que l'indice a été multiplié par ~13 sur l'échantillon.
Le coût d'entrée dû à la granularité s'exprime donc en bps décroissants. On vérifie
séparément que l'excursion intra-minute au-delà du niveau (le vrai risque de traversée)
n'a PAS suivi la même trajectoire.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "out"


def main() -> None:
    d = pd.read_parquet(OUT / "step2_trades_enriched.parquet")
    d = d.assign(
        exc_bps=d["excursion_beyond_pts"] / d["level"] * 1e4,
        tick_bps=0.25 / d["level"] * 1e4,
        range_bps=d["bar_range_pts"] / d["level"] * 1e4,
        risk_bps=d["risk_pts"] / d["level"] * 1e4,
    )
    t = d.groupby(d.index.year).agg(
        N=("level", "size"),
        level_med=("level", "median"),
        tick_bps=("tick_bps", "median"),
        exc_bps_med=("exc_bps", "median"),
        exc_bps_mean=("exc_bps", "mean"),
        range_bps_med=("range_bps", "median"),
        risk_bps_med=("risk_bps", "median"),
        cost_R_1tick=("cost_R_b1_plus1tick", "mean"),
        cost_R_c25=("cost_R_c25_trav", "mean"),
    )
    t.index.name = "annee"
    t.to_csv(OUT / "microstructure_by_year.csv")
    print(t.round(4).to_string())


if __name__ == "__main__":
    main()
