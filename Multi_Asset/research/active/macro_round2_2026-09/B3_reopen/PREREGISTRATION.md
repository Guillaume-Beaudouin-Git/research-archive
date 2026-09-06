# PRÉ-ENREGISTREMENT — B3 ré-ouverture : décomposition du choc FOMC

> **GELÉ avant tout contact avec les données de sortie.** À la rédaction, j'ai vu les premières
> lignes du fichier de chocs (pour en établir le schéma et les unités) et **aucun rendement d'actif**.
> Toute modification du signal, du seuil, des horizons ou du modèle de coût après le premier contact
> avec les rendements invalide l'étude.
> Date : 2026-09-06. Autorité : `FICHE_KILL_B3.md`, commit `667f71fa`.

## 1. Ce que cette étude teste, et ce qu'elle ne teste pas

L'étude `data/personal_book/post_fomc_drift/` (2026-06-10) a tué le drift post-FOMC sur les taux :
brut poolé **+6,8 / +4,5 / −0,8 bps** par événement, t_HAC +0,46 / +0,24 / −0,08, avec une
**inversion de signe après 2022**.

Elle mesurait la surprise par `d2y_bps`, la variation du CMT 2 ans sur **la journée entière**, et
son propre pré-enregistrement acte la limite : *« We do NOT have Fed Funds futures; d(2y) is the
pre-registered proxy, accepted as noisier (attenuation biases toward NO-GO). »*

**Hypothèse de cette ré-ouverture.** Ce proxy n'est pas seulement bruité : il **mélange deux chocs
aux dynamiques opposées** (Jarociński & Karadi, AEJ:Macro 2020) — un choc de politique monétaire et
un choc d'information de banque centrale. Un brut poolé nul peut alors être une **annulation**, pas
une absence. L'inversion post-2022 est le symptôme attendu d'un changement de composition du mélange.

**Ce qui n'est PAS testé** : aucun nouvel instrument, aucun nouvel horizon, aucune autre banque
centrale, aucune nouvelle règle d'entrée ou de sortie. **Un seul axe change : la mesure de surprise.**

## 2. Données

- **Chocs** : `shocks_fed_jk_t.csv`, dépôt `marekjarocinski/jkshocks_update_fed_202401`
  (mise à jour officielle des séries de Jarociński-Karadi). 309 événements, 1990-02-08 → 2024-01-31.
  Colonnes retenues : `start` (horodatage de l'annonce), `MP_pm`, `CBI_pm`.
- **Décomposition « poor man's »** : la surprise de taux `pc1` est attribuée **entièrement** à `MP_pm`
  si taux et S&P 500 bougent en sens **opposé** (choc de politique), **entièrement** à `CBI_pm` s'ils
  bougent dans le **même** sens (choc d'information). L'autre composante vaut exactement zéro. Chaque
  événement appartient donc à une seule des deux familles — la partition est exhaustive et disjointe.
- **Unités** : points de pourcentage. `MP_pm = -0.0517` vaut **−5,17 bps**. Le seuil de 5 bps du gel
  d'origine se transpose donc **directement** en `0.05`, sans re-calibrage.
- **Rendements, calendrier, coût, règles d'entrée/sortie** : **repris à l'identique** du moteur gelé
  `data/personal_book/post_fomc_drift/code/engine.py` — IEF en excès du DTB3, entrée à la clôture de
  T+1, sortie à `min(entrée + H, entrée de l'événement suivant)`, coût 1,0 bp RT par événement.

## 3. Signal — paramètres gelés

- **Seuil** : `|composante| ≥ 0,05` (5 bps), identique au gel d'origine.
- **Côté** : `composante ≥ +0,05` → **SHORT duration** (side = −1) ; `≤ −0,05` → **LONG duration**
  (side = +1). **La même convention est appliquée aux DEUX composantes.** On ne postule pas que
  l'information doit prédire dans l'autre sens : on laisse le signe du résultat le dire.
- **Horizons** : H ∈ {5, 10, 20} jours ouvrés — les trois du gel d'origine, pas de nouvel horizon.

## 4. Comptage des essais

**2 essais** : une hypothèse par composante (MP, CBI). Les 3 horizons sont ceux déjà gelés et ne
comptent pas comme des essais nouveaux (convention du gel d'origine, qui comptait 4 essais pour
3 horizons + 1 seuil). Compteur du programme macro : **0 → 2**. Le global reste figé.

La version par restriction de signe (`MP_median`, `CBI_median`) sera rapportée comme **diagnostic de
robustesse**, **explicitement PAS comme un test d'hypothèse séparé** — elle ne peut ni sauver ni
condamner le verdict.

## 5. Critères, écrits avant de voir le résultat

**KILL MÉCANIQUE DÉFINITIF** — si les **deux** composantes sont individuellement indistinguables de
zéro en **brut** (|t_HAC| < 2,0 aux trois horizons, moyennes brutes sous ±3 bps/événement), alors la
famille se ferme pour de bon. Plus aucune ré-ouverture sans un mécanisme entièrement nouveau. La
mesure de surprise était le dernier axe plausible.

**VALIDATION PARTIELLE** — deux composantes non nulles **et de signe opposé** (au moins une à
|t_HAC| ≥ 2,5). Condition supplémentaire **obligatoire** : **stabilité du signe de chaque composante
à travers les trois sous-périodes** (avant 2015 / 2015-2021 / 2022+). C'est cette stabilité qui
distingue une décomposition réelle d'un sur-ajustement à deux paramètres. Sans elle, le résultat est
classé NON CONCLUANT, pas PASS.

**Ce qui ne serait PAS une validation** : une seule composante significative sans que l'autre soit de
signe opposé — ce serait un simple sous-échantillonnage du signal d'origine, pas une décomposition,
et le verdict NO-GO tiendrait.

**Contrainte d'échantillon connue d'avance** : les chocs s'arrêtent au 2024-01-31, le ledger va
jusqu'au 2026-04-29. La fenêtre commune est **2004-01 → 2024-01**. Le sous-échantillon « 2022+ »
sera donc court (~16 réunions) et son test sera rapporté avec son MDE à 80 % de puissance ; aucune
conclusion ne sera tirée d'un sous-échantillon sous-puissant.
