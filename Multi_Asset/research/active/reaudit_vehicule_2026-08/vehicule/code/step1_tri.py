"""ÉTAPE 1 — le tri MÉCANIQUE vs COÛT/VÉHICULE/PUISSANCE/GÉOMÉTRIE.

P2-R1 : seules les familles dont le kill d'origine est COÛT, VÉHICULE, PUISSANCE ou
GÉOMÉTRIE sont rouvrables. Un kill MÉCANIQUE reste fermé, sans exception — y compris
lorsqu'il est accompagné d'un kill de coût (le mécanisme mort n'est pas ressuscité par
un dénominateur plus petit).

Source : `edge_inventory_2026-07/INVENTORY.csv` (118 entrées, lecture seule, N0 —
aucune mesure n'y a été produite, c'est une fouille de rapports existants).
"""
from __future__ import annotations

import pandas as pd

from common import INVENTORY, OUT

df = pd.read_csv(INVENTORY)
kc = df["kill_class"].fillna("")

df["has_MECANIQUE"] = kc.str.contains("MECANIQUE")
df["has_COUT"] = kc.str.contains("COUT")
df["has_VEHICULE"] = kc.str.contains("VEHICULE")
df["has_PUISSANCE"] = kc.str.contains("PUISSANCE")
df["has_GEOMETRIE"] = kc.str.contains("GEOMETRIE")
df["has_DONNEES"] = kc.str.contains("DONNEES")


def statut(r) -> str:
    if r.has_MECANIQUE:
        return "FERME-P2R1 (mecanique)"
    if r.has_COUT:
        return "ROUVRABLE-COUT"
    if r.has_VEHICULE:
        return "ROUVRABLE-VEHICULE"
    if r.has_GEOMETRIE:
        return "ROUVRABLE-GEOMETRIE"
    if r.has_PUISSANCE:
        return "ROUVRABLE-PUISSANCE"
    if r.has_DONNEES:
        return "BLOQUE-DONNEES"
    return "AUTRE"


df["statut_P2R1"] = df.apply(statut, axis=1)

tri = (df.groupby("statut_P2R1")
         .agg(n=("id", "size"), ids=("id", lambda s: " ".join(sorted(s))))
         .sort_values("n", ascending=False))
tri.to_csv(OUT / "tri_kill_nature.csv")

cols = ["id", "name", "family", "instruments", "N", "sharpe", "t_stat",
        "cost_assumed", "origin_verdict", "kill_reason", "kill_class",
        "reopenable", "futures_vehicle_fits_13k", "statut_P2R1", "source"]
df[cols].to_csv(OUT / "inventaire_annote.csv", index=False)

print("=== TRI P2-R1 sur", len(df), "entrées de l'inventaire ===")
print(tri.to_string())
print()
n_mech = int(df.has_MECANIQUE.sum())
n_cost = int(df.has_COUT.sum())
print(f"contient COUT              : {n_cost}")
print(f"  dont AUSSI MECANIQUE     : {int((df.has_COUT & df.has_MECANIQUE).sum())}  -> FERMÉ (P2-R1)")
print(f"  COÛT sans mécanique      : {int((df.has_COUT & ~df.has_MECANIQUE).sum())}  -> rouvrable")
print(f"MECANIQUE (toutes formes)  : {n_mech}  ({100*n_mech/len(df):.0f} % des entrées)")
print()
print("=== Les familles tuées SUR LE COÛT et rouvrables ===")
sub = df[df.statut_P2R1 == "ROUVRABLE-COUT"]
for _, r in sub.iterrows():
    print(f"  {r['id']:5s} {r['name'][:62]:62s} | {r['kill_class']}")
