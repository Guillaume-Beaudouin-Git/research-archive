# Candidat — Dérive de réouverture sur l'or (MGC / GC), fenêtre Globex 18:00 ET

> **Statut** : le **mieux mesuré de tout le dépôt hors month-end**. Sur FTMO :
> **UNDERPOWERED, famille OUVERTE**. Sur futures : **PASS conditionnel** au coût 0.66 bps.
> **Sources canoniques** : `Multi_Asset/research/active/overnight_futures_2026-07/`,
> `overnight_sleeve_reopen_2026-08/RESULTS.md`,
> `close_continuation_gold_subwindows_2026-08/RESULTS.md` (§ TEST B).

## Mécanisme

Rémunération d'inventaire au retour de la liquidité, dans la **première heure après la réouverture
Globex (18:00 ET)**. ⚠ **Le mécanisme des rapports archivés est FALSIFIÉ** : ce n'est **pas** « la
demande physique asiatique » — l'effet est ancré à **l'horloge CME**, 1 à 2 h **AVANT** Tokyo (L56).
La fenêtre héritée « 23:00-07:00 UTC » était juste en hiver et **une heure en retard tout l'été**.

## Métriques mesurées

| Métrique | Valeur |
|---|---:|
| t_HAC (E002, full) | **4.82** — le plus élevé du dépôt hors month-end |
| DSR / walk-forward | 0.99 / **5 folds sur 5** |
| β vs or vol-targeté | **0.014** (R² 0.002) |
| **Sharpe à 0.66 bps (futures)** | **1.31** sur 2020-26 · **1.39** full-sample |
| Sharpe à 1.5 bps (CFD) | **0.99**, DSR 0.495 → **sous le gate** |
| Gross post-2021 | **3.79 bps**, t_HAC 2.74 |
| **Survie au retard d'entrée** (post-2021) | **+5 min : 99 %** · **+10 min : 93 %** (4.04 bps, t 2.85) · +15 min : 91 % |
| Stabilité (entrée +10 min) | **18 années positives sur 20**, dont **6/6 depuis 2021** |
| Le véhicule cote-t-il la fenêtre ? | **oui, 99.78 %** des séances |

## Les deux hypothèses qui pouvaient le tuer sont RÉFUTÉES

1. **L'effet n'est pas dans les premières minutes** (1.4 % du total post-2021) — donc il n'est pas un
   artefact du premier print.
2. **Il survit au retard d'entrée**, à l'inverse exact de GER40 (qui ne gardait que 16 % à 5 min
   parce que 60 % de son effet était dans l'enchère de clôture Xetra).

Et le mécanisme de la Fed de New York qui a **tué le drift overnight ES/NQ/YM depuis 2021** (la
dispersion du volume signé de clôture passée de 6.5 % à 2.9 %) **ne se réplique PAS sur l'or**
(dispersion +8 %). Ce n'est pas la même chose qui meurt.

## Deux gains concrets du retard d'entrée

- Entrer **10-15 min plus tard coûte 7-9 % du gross** mais **sort du pire moment de fourchette de la
  journée** (premier print après une coupure de 76 min). Si le spread à `t0+15` est seulement
  modérément meilleur, **la variante retardée domine en net**. Choix disponible à coût de recherche nul.
- La position **ne traverse aucun rollover ⇒ aucune nuit de swap**, et le retard **éloigne** du
  tampon. Le swap or FTMO étant asymétrique, **une seule nuit facturée par erreur coûterait 47 % du
  gross**. ⚠ À vérifier sur compte réel : l'heure du tampon n'est pas mesurable en données de prix.

## ⚠ Points de vigilance, sérieux

- **La part de gap non tradable a DOUBLÉ post-2021 : 36.1 % (t 3.50)**, la coupure s'étant allongée
  à 76 minutes. Règle de mort fixée à 40 % — non déclenchée, **mais la tendance est mauvaise**.
  Corollaire : **tout chiffre H1 de ce dossier surestime le tradable d'environ un tiers.**
- **Granularité de lot (L57)** : à petit capital c'est **1 lot ou rien** ⇒ vol-targeting inopérant,
  **−0.35 de Sharpe**, skew **+0.99 → −0.49**, et une queue de **−18.4 % sur une seule séance**.
  Déployable à lot fixe : SR 1.39 full-sample, **0.77 sur 2020-26**. 1 MGC ≈ 0.12 Kelly.
- **AUCUN panier.** or↔argent 0.76 ; en equal-risk le couple donne **SR 1.096 contre 1.279 pour l'or
  seul** — ajouter l'argent **détruit** le Sharpe. L'argent est par ailleurs condamné par son
  **58.3 % de gap** non tradable, et le WTI par son coût (34.6 % de gap).
- **Le coût fixe domine sur MGC** (L57) : $1.70 sur ~$40 k de notionnel = 0.66 bps — c'est
  précisément l'hypothèse qui donne SR 1.31. Sur un contrat plus petit, l'edge se referme.

## Ce qu'il faut faire AVANT de le déployer

1. **Mesurer le spread réel à la réouverture** — c'est la seule inconnue qui reste, et elle décide
   entre SR 1.31 et un candidat mort. Non mesurable depuis nos données de prix.
2. Trancher **lot fixe vs vol-targeting** en fonction du capital, en rapportant **skew et queue
   single-session** (L57).
3. Re-vérifier la **part de gap** à la date du déploiement — elle se dégrade.
