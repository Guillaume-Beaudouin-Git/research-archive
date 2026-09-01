# DÉCISION — calendrier overnight lundi+mardi : dette DSR tranchée

**2026-09-01.** Clôt une question ouverte depuis le 2026-06-03, signalée « à trancher avant
signature » dans 5+ documents sur deux mois et jamais formellement résolue.

## La dette

`PropFirms/ftmo/program_2026-06/ftmo_universe/OVERNIGHT_VERIFICATION_REPORT.md` (2026-06-03)
DÉCOUVRE la concentration midweek et l'admet lui-même comme post-hoc :

> « le chiffre robuste est **TOUTES nuits (+4,90, t=4,04)**, non cherry-pické. La concentration
> midweek est un *post-hoc* […] Traite +4,9 comme la borne dure, midweek comme l'amélioration. »

Le choix a été gravé dans `spec_v22.yaml` sept jours plus tard en portant un **échec DSR 0,29**
sur sa propre grille de sélection à 40 cellules. Aucune pré-registration ne précède la découverte.

## Ce qui tranche : la haie de swap, connue ex ante

Net mesuré (swap LONG `spec_v22.yaml::measured_specs` 2026-06-10 ; spread RT natif mesuré
2026-08-17 ; swap ×3 le vendredi), échantillon complet, nuits étiquetées par jour d'ENTRÉE,
heure d'échange avec DST (L56) :

| configuration | US100 bps/nuit | US100 total | GER40 bps/nuit | GER40 total |
|---|---:|---:|---:|---:|
| **lundi+mardi (déployé)** | **+5,11** | **+6 183** | **+4,49** | **+5 766** |
| tout sauf vendredi | +1,61 | +3 949 | +0,83 | +2 125 |
| toutes les nuits | +0,36 | +1 105 | **−0,17** | **−529** |
| mardi seul | +6,60 | +4 185 | +3,87 | +2 505 |
| lundi seul | +3,48 | +1 998 | **+5,12** | +3 261 |

Haie = swap + spread : US100 **3,17 bps**, GER40 **2,58 bps**. Mercredi (1,26 US100) et jeudi
(1,48) sont **très en dessous** — il leur faudrait tripler, ce n'est pas une erreur de mesure.

## Décision : la restriction est MAINTENUE

**Motif — ce n'est pas une sélection de signal, c'est une contrainte de coût.** Le DSR punit la
recherche parmi des alternatives POSITIVES ; ici les alternatives ne le sont pas (« toutes nuits »
= −0,17 sur GER40, +0,36 sur US100). Il n'existe pas de choix entre plusieurs bons candidats : une
seule configuration franchit la haie. La haie elle-même est **connue ex ante**, mesurée sur le
compte, indépendante des rendements.

Appuis convergents :
- **L64 (corollaire)** : le bon test est celui de l'objet DÉPLOYÉ. Lundi+mardi POOLÉS comme UNE
  hypothèse → **t=4,65 (US100)**, franchit le seuil cumulé 4,21 ; 4,18 (GER40). Chaque jour isolé
  plafonne à 2,29 — décomposer détruit la puissance sans rien apprendre.
- **Aucune rupture endogène** ne survit à la correction du balayage (p=0,43-0,61, `desk_overnight_2026-09`).
- Cross-confirmé **3 marchés** (NQ, GER40, US100), même jour.
- Couper lundi retire **~51 %** de la contribution nette et dégrade le Sharpe (0,73→0,54 US100).

## Ce qui est assumé, explicitement

1. **Risque résiduel** : mercredi/jeudi pourraient être réellement positifs et exclus sur du bruit.
   Écart à la haie trop grand (facteur ~2,5) pour que ce soit crédible, mais non nul.
2. Le récit « seul le mardi persiste depuis 2022 » est **RETIRÉ** : sur l'histoire complète nette,
   **GER40 lundi seul (+5,12) bat GER40 mardi seul (+3,87)**. Il venait d'un sous-échantillon
   choisi après coup (L64).
3. La décision porte sur le CALENDRIER, pas sur le POIDS. Si le risque doit baisser, réduire
   `ea_on_w`, pas retirer un jour (L54 : dé-levier plat ≥ conditionnement).

**Statut : CLOS.** Ne pas rouvrir sans angle nouveau relevant des catégories rouvrables
(véhicule / coût / puissance / géométrie) — un changement du régime de swap serait le cas type.
