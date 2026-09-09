# Checkup funded <ACCOUNT_ID> — le drawdown de départ est-il anormal ?

**2026-09-09.** Compte funded livré le 2026-08-17, **15 jours ouvrés** écoulés. Δn_tests = 0
(simulation sur série existante, aucune hypothèse nouvelle testée).

## État du compte

| | |
|---|---|
| équité / solde | **9 859,80** / 9 878,44 |
| depuis le départ | **−1,40 %** (équité) / −1,22 % (solde) |
| depuis le pic (10 018,33 le 08-25) | **−1,58 %** |
| plancher statique 9 000 | marge **+859,80** (8,6 % du capital) |
| plancher journalier 9 405,53 | marge **+454,27** |
| ligne breaker 9 555,53 | marge +304,27 |
| position ouverte | US100 long 0,12 lot, notionnel 3 539 $, flottant −18,64 |
| retraits | aucun (`wd_due_usd` 0, 1 j ouvré depuis le dernier cycle) |

## Réponse directe : ~9 % — c'est un mauvais tirage ordinaire, pas une anomalie

Cohortes glissantes : un compte **neuf à 10 000** démarre chaque jour de bourse, book
**réellement déployé** (or et J1 à poids nul, overnight US100+GER40 `on_w` 0,35 lundi/mardi,
ORB funded 0,25 % tapé), config live-fidèle `CFG_FUNDED_V28` (breaker daily v2.4, marge Swing,
`leg_lev_cap`). 3 280 cohortes 2013→2026.

| fenêtre | n | **P(J15 ≤ −1,40 %)** | IC95 block-boot | P(maxDD ≤ −1,58 %) | IC95 |
|---|---|---|---|---|---|
| 2013-2026 | 3 280 | **9,0 %** | [6,2 – 12,2] | 23,1 % | [18,7 – 28,0] |
| 2020+ | 1 655 | 6,1 % | — | 20,2 % | — |
| 2021-09+ | 1 223 | **7,3 %** | [4,2 – 10,9] | 19,5 % | [13,0 – 26,2] |
| 2024+ | 616 | 7,3 % | — | 17,2 % | — |

Distribution des 15 premiers jours (2021-09+) : médiane **+0,43 %**, p10 −1,16 %, p5 −1,60 %,
écart-type 1,37 %. On est au **9ᵉ centile** — le creux le plus banal qu'on puisse appeler un creux.
**P(finir les 15 premiers jours dans le rouge) = 36 %.** Pire départ des 3 280 cohortes : −3,23 %.

**Zéro bust en 15 jours sur 3 280 cohortes**, et zéro sur 1 059 cohortes à 6 mois.

### Le chiffre est une borne BASSE

Toute la dispersion vient de l'ORB : sans lui, P(J15 ≤ −1,40 %) tombe à **2,3 %** [1,2–3,6]. Or le
ledger ORB funded est **idéalisé sur ses deux jambes** (entrée et stop remplis au prix exact, L59
jamais appliquée). Un ORB dégradé garde sa variance et perd de la moyenne ⇒ la vraie distribution
est décalée vers le bas ⇒ **P(≥ 9 %)**. Le 2,3 % est une attribution de variance, pas une borne.

## Un mauvais départ ne prédit rien

1 059 cohortes à 120 jours ouvrés (~6 mois), conditionnées sur l'état au jour 15 :

| groupe | n | médiane J60 | médiane J120 | P(J120 > 0) | bust |
|---|---|---|---|---|---|
| **départ ≤ −1,40 % (notre cas)** | 104 | −1,20 % | −0,53 % | 47,1 % | 0 % |
| départ meilleur | 955 | +0,93 % | +1,63 % | 77,2 % | 0 % |

**Corrélation rendement J15 → rendement J15→J120 : −0,011.** Aucune persistance : l'écart entre les
deux lignes est l'arithmétique du retard reporté, pas un régime. Les comptes mal partis récupèrent
+0,87 pt sur les 105 séances suivantes.

## La volatilité live est SOUS le modèle

16 séances réelles : écart-type quotidien **27,53 $**, pire jour **−84,24 $** (2026-09-01).
Le modèle implique 35,5 $/j. Le compte ne bouge pas plus violemment que prévu — il a simplement
tiré le mauvais côté. Le pire jour vaut **17 % de la barrière journalière**.

## ⚠ Ce que le checkup a trouvé, et qui compte plus que le drawdown

**Le 2026-09-07 (Labor Day US), une position ORB de 0,60 lot a raté son stop horaire et a été
portée toute la nuit — notionnel 17 745 $ short, soit 1,80 × l'équité.**

Chaîne établie : `swaps_billed.csv` facture bien `2026-09-07,US100.cash,0.60,-17744.85` (une
position intraday ne paie pas de swap) ; le journal EA du 09-07 montre
`OrderSend US100.cash ret=10018 Market closed` à **20:00:00** et **20:05:00** serveur — la séance
US100 a fermé tôt pour le férié, et l'EA n'a plus pu agir.

Trois conséquences, aucune cosmétique :
1. **Le sleeve ORB est conçu intraday** (stop horaire 22:00 Paris, risque 25 $). Il a passé une nuit
   à 1,8 × l'équité. Un gap de 2,8 % sur US100 consommait la barrière journalière entière.
   Le breaker M5 ne couvre pas un gap de réouverture — c'est exactement la queue que le sim ne voit
   pas (`funded_5ans_2026-09`, § limite structurelle).
2. **Le rebalance du 09-07 22:05 n'a jamais eu lieu** (aucun fill) : la jambe overnight US100 du
   lundi a été sautée, book partiel.
3. **La sortie de cette position n'est dans aucun ledger** — ni `fills.csv`, ni le journal EA du
   09-08. Elle a donc été fermée côté broker (stop). Le trou tombe précisément là où L59 dit que
   l'ORB est déjà idéalisé : **le ledger ORB ne voit pas ses propres sorties au stop.**

**Le calendrier des fériés d'échange n'est pas dans la chaîne de décision de l'EA.** C'est un défaut
de véhicule, pas de signal, et il est réparable sans toucher au binaire (garde côté brain :
pas d'entrée ORB sur séance écourtée).

## Autres points ouverts (non bloquants)

- `spec_bounds_breach = 1` : dérive des swaps, XAUUSD long **−93,00 vs ancre −65,68 (+42 %)**.
  Déjà au TODO, fenêtre samedi. Poids or nul aujourd'hui, mais **le swap de l'or est DANS le signal**
  de la sleeve gold — à ré-ancrer avant toute réactivation.
- `last_error` périmé et `targets_status: OK` avec `targets_age_h` 16,3 : champs « dernière valeur
  connue » lus comme « valeur courante » (`_audit/alertes_faux_positifs_2026-09-07.md`).

## Lecture opérationnelle

Le drawdown n'est pas le sujet : **9 %, sans persistance, sans bust, avec une vol live sous le
modèle.** Le sujet est le trou de véhicule du 09-07 — un jour férié a fait tenir une position
intraday à 1,8 × l'équité pendant une nuit, et sa sortie n'est tracée nulle part.

**Sources** : `cohortes_H15.csv`, `cohortes_noORB_H15.csv`, `conditionnel_H120.csv` (ce dossier).
