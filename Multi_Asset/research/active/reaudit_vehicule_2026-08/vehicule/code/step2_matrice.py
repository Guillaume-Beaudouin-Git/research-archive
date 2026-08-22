"""ÉTAPES 2 + 3 — matrice de véhicule (L53 D'ABORD) puis re-gate au coût futures (P2-R2).

L'ordre est imposé : le véhicule AVANT le backtest (L53, correctif du biais
« véhicule en dernier » qui a coûté deux rejets au month-end ZN).

Tous les `gross_bps` sont des chiffres DÉJÀ PUBLIÉS dans le dépôt, cités avec leur
source. Aucune nouvelle mesure ici — c'est de l'arithmétique de re-gate sur des
hypothèses déjà comptées au ledger.

cost_p95 (P2-R2) : à défaut d'une distribution de fourchette futures mesurée, on
utilise la convention de stress documentée du dépôt — **2 ticks** au lieu d'un —
comme majorant de queue. C'est la même convention que `overnight_futures_2026-07`.
"""
from __future__ import annotations

import pandas as pd

from common import OUT, contract_specs

SPECS = contract_specs().set_index("contract")

# --------------------------------------------------------------------------
# Les familles. `gross_bps` = brut par trade/événement tel que PUBLIÉ.
# `veh` = contrat futures candidat le plus granulaire qui existe réellement.
# --------------------------------------------------------------------------
FAM = [
    # ---- les deux PRÉCÉDENTS déjà résolus (lignes de calibration) ----
    dict(id="E001", nom="Month-end Treasury (dash-for-cash)", classe="ROUVRABLE-VEHICULE",
         veh="ZN", gross_bps=16.25, gross_src="month_end_vehicle: jambe TENUE +16.25 bps/évt, t 4.79",
         cout_cfd="aucun instrument obligataire FTMO (gate-0)", statut_amont="VÉHICULE — RÉSOLU"),
    dict(id="E002", nom="Or overnight (réouverture Globex 18:00 ET)", classe="ROUVRABLE-GEOMETRIE",
         veh="MGC", gross_bps=4.59, gross_src="overnight_futures step1c: fenêtre CAPTURABLE 4.59 bps, t 7.13",
         cout_cfd="1.5 bps CFD -> SR 0.99 / DSR 0.495 sur 2020-26", statut_amont="COÛT+GÉOM — RÉSOLU (PASS cond.)"),
    # ---- les 11 tuées SUR LE COÛT ----
    dict(id="E003", nom="Argent overnight (post-2014)", classe="ROUVRABLE-COUT",
         veh="SIL", gross_bps=1.99, gross_src="overnight_futures step2b: contrat RÉEL 1.99 bps (CFD 10.95, capture 0.18)",
         cout_cfd="break-even 5.3 bps RT", statut_amont="re-testé futures 07-30"),
    dict(id="E004", nom="WTI overnight", classe="ROUVRABLE-COUT",
         veh="MCL", gross_bps=3.20, gross_src="overnight_futures step1c: capturable 3.20 bps (contrat réel -0.34)",
         cout_cfd="break-even ~3.5 bps RT", statut_amont="re-testé futures 07-30"),
    dict(id="E005", nom="Soja — dérive de réouverture CBOT", classe="ROUVRABLE-COUT",
         veh="MZS", gross_bps=9.65, gross_src="overnight_futures §6: ZS=F vraie fenêtre +9.65 bps, t 2.84, N=463 (2 ans)",
         cout_cfd="<=2 bps RT requis ; le CFD ne cote JAMAIS la réouverture", statut_amont="UNDERPOWERED"),
    dict(id="E011", nom="Blé — saisonnalité de mai (winter-wheat)", classe="ROUVRABLE-COUT",
         veh="ZW", gross_bps=241.0, gross_src="session_E2: +241 bps/mai brut, t 1.69 (net-CFD +126, t 0.89)",
         cout_cfd="swap grain CFD ~-115 bps/mois", statut_amont="jamais re-testé sur futures"),
    dict(id="E014", nom="VRP S1 (VIX - RV) swing quotidien", classe="ROUVRABLE-COUT",
         veh="MNQ", gross_bps=14.2, gross_src="indices_swing: SR brut 0.467, vol ~10 %/an, turnover 33x/an -> 14.2 bps/rotation",
         cout_cfd="0.10 % RT ETF (QQQ)", statut_amont="déjà re-calculé au coût futures : SR 0.454"),
    dict(id="E018", nom="Flux de rééquilibrage lev-ETF (30 dernières min NQ)", classe="ROUVRABLE-COUT",
         veh="MNQ", gross_bps=1.73, gross_src="session_structural_dislocations: +1.73 bps au décile |move|>=Q90 (t plafonne ~1.3)",
         cout_cfd="~0.5 bps NQ supposé, coût intraday JAMAIS mesuré", statut_amont="différé au sort de l'ORB"),
    dict(id="M022", nom="Continuation de gap CPI/NFP (open+5min -> close)", classe="ROUVRABLE-COUT",
         veh="MNQ", gross_bps=9.40, gross_src="session_G: two-sided +9.7 gap-up / +9.1 gap-down, net +6.5 @3 bps, t 0.69",
         cout_cfd="3 bps RT", statut_amont="net t 0.69"),
    dict(id="R006", nom="PMR basis delta-neutral (perps crypto)", classe="ROUVRABLE-COUT",
         veh=None, gross_bps=None, gross_src="IC réelle mais 912 évts/an contre un plafond L12 de ~29",
         cout_cfd="0.17 % RT -> 178 %/an de drag", statut_amont="aucun véhicule futures"),
    dict(id="R012", nom="Réversion H1 d'ouverture de Londres", classe="ROUVRABLE-COUT",
         veh="M6E", gross_bps=0.50, gross_src="fx_intraday: gross ~0.5 bps, meilleur gross/coût 0.287 (L43/L44)",
         cout_cfd="2-5 bps CFD RT", statut_amont="déjà re-testé sur futures : gate non franchi"),
    dict(id="R015", nom="Réversion du fix WMR (segmentation Ranaldo)", classe="ROUVRABLE-COUT",
         veh="6E", gross_bps=2.07, gross_src="L34 : two-sided t 3.55, gross 2.07 bps/jour",
         cout_cfd="2.48 bps RT retail mesuré (besoin <1 bps/jambe)", statut_amont="tier institutionnel"),
    dict(id="R021", nom="Fade de l'ORB raté (D1) NQ", classe="ROUVRABLE-COUT",
         veh="MNQ", gross_bps=None, gross_src="SR -0.14, IC_t 1.55 < gate 2.5 — brut non isolé, edge absent post-coût",
         cout_cfd="$19 RT", statut_amont="brut non publié"),
    # ---- ajout hors-inventaire : le kill de coût le plus RÉCENT (2026-08-13) ----
    dict(id="ORB", nom="ORB funded US100 (kill R2 du 2026-08-13)", classe="ROUVRABLE-COUT",
         veh="MNQ", gross_bps=None, gross_src="orb_cost_funded : mean R +0.04916 à coût nul ; FRONTIÈRE R2 = 0.588 bps RT",
         cout_cfd="1.80 bps RT mesuré (2 méthodes indép.)", statut_amont="ORB_KILL par R2 ET R4 (WF 2/5)"),
    # ---- variantes de GRANULARITÉ (L57) : même famille, deux tailles de contrat ----
    dict(id="E005b", nom="Soja — MÊME famille sur le contrat PLEIN", classe="variante L57",
         veh="ZS", gross_bps=9.65, gross_src="idem E005",
         cout_cfd="—", statut_amont="variante de granularité"),
    dict(id="E011b", nom="Blé — MÊME famille sur le MICRO", classe="variante L57",
         veh="MZW", gross_bps=203.5, gross_src="re-mesuré ici sur ZW=F : +203.5 bps/mai, N=22",
         cout_cfd="—", statut_amont="variante de granularité"),
    dict(id="R015b", nom="Fix WMR — MÊME famille sur le MICRO", classe="variante L57",
         veh="M6E", gross_bps=2.07, gross_src="idem R015",
         cout_cfd="—", statut_amont="variante de granularité"),
]

# Le second kill — celui que le changement de véhicule NE touche PAS.
SECOND_KILL = {
    "E001": "aucun — VALIDÉ, déployé (SR 0.92 net, +17.6 %/an)",
    "E002": "aucun sur le signal ; L57 mord (lot fixe : skew +0.99 -> -0.49, queue -18.4 %/séance)",
    "E003": "MÉCANIQUE — capture 0.18 sur le contrat réel (t -3.91) + 59 % du brut est le GAP de pause, non tradable",
    "E004": "MÉCANIQUE — 35 % de gap ; contrat réel -0.34 bps sur le recouvrement",
    "E005": "PUISSANCE — N=463 sur 2 ans ; walk-forward >=5 plis IMPOSSIBLE (règle dure)",
    "E011": "PUISSANCE + SÉLECTION — mesuré ici : IC95 bootstrap [-100, +496] CONTIENT ZÉRO ; sous son placebo de sélection-de-mois (p 0.333, décembre bat mai)",
    "E014": "SIGNAL — SR au coût futures DÉJÀ calculé = 0.454 < 0.7 ; l'IC (0.05-0.075) est une propriété du signal",
    "E018": "PUISSANCE — t plafonne ~1.3 (sd de r_last30 = 31 bps noie un edge de 1.7 bps)",
    "M022": "PUISSANCE — t net 0.69 ; re-échelonné au coût MNQ le t reste ~0.96, N=146",
    "R006": "aucun véhicule futures — le plafond L12 est intrinsèque au tarif perp",
    "R012": "COÛT confirmé — déjà re-testé sur futures, gate non franchi (L43/L44)",
    "R015": "L57 + L23 — ne passe QUE sur le 6E plein (notionnel 10.5x le compte) ; le micro M6E échoue au coût",
    "R021": "brut jamais isolé ; SR -0.14, IC_t 1.55 < 2.5",
    "ORB": "R4 INTACT — walk-forward 2/5 plis (40 %) au coût mesuré ; le pli est insensible au véhicule",
    "E005b": "granularité : notionnel 4.32x le compte -> vol de compte ~41 %",
    "E011b": "granularité : coût x1.6 (73 % de frais FIXE) mais queue de séance divisée par 10",
    "R015b": "granularité : le micro est GRANULAIRE mais son coût (2.03 bps) retue la famille",
}

GATE = 1.5

rows = []
for f in FAM:
    veh = f["veh"]
    if veh is None:
        rows.append(dict(
            id=f["id"], famille=f["nom"], classe_kill_origine=f["classe"],
            future_correspondant="AUCUN", notionnel_usd=None, marge_lot_min_usd=None,
            marge_pct_compte_12k=None, notionnel_x_compte=None,
            verdict_L53="n/a — pas d'instrument futures",
            cout_cfd_origine=f["cout_cfd"], cout_futures_base_bps=None,
            cout_futures_p95_bps=None, part_frais_fixe_pct=None,
            gross_bps=f["gross_bps"], gross_source=f["gross_src"],
            ratio_gross_sur_coutp95_futures=None,
            verdict_P2R2="n/a", statut_amont=f["statut_amont"], verdict_P2=""))
        continue
    s = SPECS.loc[veh]
    base = float(s.rt_bps_base)
    p95 = float(s.rt_bps_stress_2tick)
    g = f["gross_bps"]
    ratio = None if g is None else round(g / p95, 3)
    # L53 : la marge du lot minimum tient-elle dans le capital perso ?
    if s.margin_pct_account <= 35:
        l53 = f"OUI ({s.margin_pct_account:.1f} % du compte) -> propfirm STRICTEMENT DOMINÉ"
    elif s.margin_pct_account <= 100:
        l53 = f"OUI mais {s.margin_pct_account:.1f} % du compte -> matériellement hors budget (M1)"
    else:
        l53 = f"NON ({s.margin_pct_account:.1f} %) -> capital insuffisant"
    if ratio is None:
        p2r2 = "NON CALCULABLE (brut non publié)"
    elif ratio >= GATE:
        p2r2 = f"PASS ({ratio:.2f} >= 1.5)"
    else:
        p2r2 = f"FAIL ({ratio:.2f} < 1.5)"
    rows.append(dict(
        id=f["id"], famille=f["nom"], classe_kill_origine=f["classe"],
        future_correspondant=f"{veh} — {s.desc}",
        notionnel_usd=float(s.notional_usd), marge_lot_min_usd=float(s.margin_usd),
        marge_pct_compte_12k=float(s.margin_pct_account),
        notionnel_x_compte=float(s.notional_x_account),
        verdict_L53=l53,
        cout_cfd_origine=f["cout_cfd"],
        cout_futures_base_bps=base, cout_futures_p95_bps=p95,
        part_frais_fixe_pct=float(s.fixed_share_pct),
        gross_bps=g, gross_source=f["gross_src"],
        ratio_gross_sur_coutp95_futures=ratio,
        verdict_P2R2=p2r2, statut_amont=f["statut_amont"], verdict_P2=""))

m = pd.DataFrame(rows)
# L'ORB ne publie pas un brut par trade mais une FRONTIÈRE de coût (0.588 bps RT pour
# t_HAC = 2.0). Le re-gate s'y fait par comparaison directe — voir step4_orb_frontiere.py.
# Coût MNQ au dérapage MESURÉ de L19 (4 ticks RT) = 0.617 bps.
i = m.index[m.id == "ORB"][0]
m.loc[i, "cout_futures_base_bps"] = 0.617
m.loc[i, "cout_futures_p95_bps"] = 0.783
m.loc[i, "verdict_P2R2"] = "FAIL (0.617 > frontière 0.588 au dérapage L19 mesuré ; 1/4 scénarios sous la frontière)"

m["second_kill_non_couvert_par_le_vehicule"] = m.id.map(SECOND_KILL)


def verdict_p2(r) -> str:
    if r.id in ("E001",):
        return "DÉPLOYÉ (précédent L53)"
    if r.id in ("E002",):
        return "PASS conditionnel (précédent, déjà instruit)"
    if r.classe_kill_origine == "variante L57":
        return "variante — voir la famille mère"
    if r.verdict_P2R2.startswith("FAIL"):
        return "REFERMÉ — P2-R2 (le coût futures ne suffit pas)"
    if r.verdict_P2R2.startswith("n/a"):
        return "REFERMÉ — aucun véhicule futures"
    if r.verdict_P2R2.startswith("NON CALCULABLE"):
        return "REFERMÉ — brut non publié, R2 non évaluable"
    return "R2 FRANCHI puis REFERMÉ sur un SECOND kill non-coût"


m["verdict_P2"] = m.apply(verdict_p2, axis=1)
m.to_csv(OUT / "matrice_vehicule.csv", index=False)

pd.set_option("display.width", 250)
print("=== MATRICE DE VÉHICULE — L53 D'ABORD (compte 12 000 EUR = $13 826) ===\n")
print(m[["id", "future_correspondant", "notionnel_usd", "marge_lot_min_usd",
         "marge_pct_compte_12k", "notionnel_x_compte"]].to_string(index=False))
print("\n=== RE-GATE AU COÛT FUTURES (P2-R2, gate 1.5) ===\n")
print(m[["id", "cout_cfd_origine", "cout_futures_base_bps", "cout_futures_p95_bps",
         "part_frais_fixe_pct", "gross_bps", "ratio_gross_sur_coutp95_futures",
         "verdict_P2R2"]].to_string(index=False))
