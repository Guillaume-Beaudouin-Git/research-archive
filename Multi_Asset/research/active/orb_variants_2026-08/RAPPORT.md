# Balayage exhaustif ORB (NQ) — la spec déployée est-elle un point d'un voisinage mort ou vivant ?

Compte FTMO funded `<ACCOUNT_ID>`, sleeve `FU_ORB_RISK` (~57 % de la valeur simulée du livre).
Grille pré-enregistrée avant calcul : `PREREGISTRATION.md`. Code : `code/`. Résultat brut :
`grille_resultats.csv` (42 lignes dont 6 doublons de l'ancrage listés une fois par axe pour
lisibilité → **37 variantes uniques**, conforme au pré-enregistrement).

## Verdict en une phrase

**La spec déployée n'est pas un point médian d'un nuage plat — elle est près du HAUT d'un nuage
où 33 des 34 cellules non-artefactuelles sont indiscernables du bruit, et la seule cellule qui
dépasse le seuil de significativité corrigé est une NÉGATIVE dont l'effet s'est éteint dans le
dernier fold walk-forward.** Aucune variante testée ne bat la spec déployée de façon robuste au
régime, aux deux jambes et au placebo.

## 1. Ce qui a été balayé, et comment lire le tableau

37 variantes uniques (6 axes, conception OFAT depuis l'ancrage `RTH, 30min, touch, marge 0,
confirmation immédiate, sortie close RTH, aucun filtre` — la spec déployée). Chaque variante :
gross et net, jambe longue et courte séparées (L25), 4 tranches de régime de 4 ans, HAC lag-6,
block bootstrap (2000 tirages), placebo de signe (200 tirages, décrit ci-dessous).

**Coût** : 0.962 bps RT converti PAR TRADE via `entry × 0.962e-4 / |entry-stop|` — jamais un
levier fixe (contrainte #2 respectée, colonne `cost_R` dans le ledger reconstruit).

**Fidélité de la reconstruction** : rebâtie depuis `NQ_1min_databento_2010-2026.parquet` (pas
depuis le ledger figé, comme demandé). Cross-check : le premier jour (2010-06-07) donne un OR
RTH 30 min identique au tick au ledger figé (1844.25/1826.25). N total diffère légèrement (4105
jours RTH reconstruits ici contre N=4013 dans le ledger figé) — écart mineur attendu d'une
reconstruction indépendante, pas un signe d'erreur (la spec, les niveaux d'entrée et l'ordre de
grandeur du Sharpe/t sont cohérents : reconstruction ancrage t=1.16, Sharpe net 0.28,
long_t=1.13 / short_t=0.55 — même signature de piège bêta que le t=1.57/0.54 rapporté sur le
ledger figé).

## 2. Fondations vérifiées avant tout calcul (L52, L60)

- **Fuseau (L52)** : la colonne `is_rth` du parquet canonique tombe exactement à 13:30 UTC l'été
  (2694 jours) et 14:30 UTC l'hiver (1411 jours) = 9:30 ET — DST géré correctement à la source,
  vérifié au tick, pas supposé.
- **Fourchette nulle (L60)** : 0.09 % des barres RTH ont `high==low` — négligeable, ce n'est PAS
  un print de règlement type XPT/XPD, c'est un futur CME liquide.
- **Reprise Globex** : détectée directement dans la donnée (première barre à 18:00:00 ET après la
  pause), 3244 événements de reprise sur 4105 jours (861 jours sans reprise identifiée — gaps de
  données ou jours fériés US, exclus proprement, `or_globex` = NaN, 1 seul jour orphelin sur
  `or_globex[30]`).

## 3. La distribution des t — c'est elle qui parle, pas le max

34 variantes non-Globex, uniques (le Globex est traité à part, §5, artefact) :

| Statistique | Valeur |
|---|---|
| médiane `t_net` | **0.54** |
| `t_net` moyen | 0.35 |
| Q10 / Q90 de \|t\| | 0.06 / 1.83 |
| Q95 / Q99 de \|t\| | 2.57 / 3.85 |
| min / max | -4.29 (`retest`) / +2.97 (`cal_Fri_only`) |
| signe positif / négatif | 24 / 10 |

**24 des 34 variantes sont positives** — cohérent avec un léger biais long-NQ diffus dans
n'importe quel cornée de cet espace (le NQ a fait +1555 % sur la période), pas avec une
concentration d'edge. Aucune des 34 ne dépasse individuellement le seuil Šidák sprint (Δn=37,
`|t|>3.20`), **sauf `retest` (négatif)**.

**Position de la spec déployée dans cette distribution** : `t_net = 1.16`, **79ᵉ percentile de
|t|** parmi les 34 — donc PAS au milieu, plutôt en HAUT du nuage. Seules 4 des 34 variantes la
dépassent en valeur brute (`cal_excl_day_before_holiday` 1.18, quasi-identique ; `cal_excl_FOMC`
1.61 ; `cal_excl_FOMC_pm1` 1.93 ; `cal_Fri_only` 2.97) — et aucune ne clarifie le seuil Šidák
sprint. La spec déployée est donc **le meilleur point structurel non-calendaire, non-artefactuel
du voisinage balayé** — pas un choix arbitraire dans une mer plate, un des sommets d'une colline
qui reste, dans son ensemble, sous le seuil de signification.

## 4. Comparateur au max sous H0 (placebo de signe, pas N(0,1) théorique)

Le placebo conserve la **magnitude** \|r\| de chaque trade réel et retire son **signe** (attribué
par la cassure réelle) à pile-ou-face — 200 tirages par variante. Sous H0 « la cassure ne prédit
rien, seule l'exposition passive au NQ compte », la moyenne réelle doit ressembler à cette
distribution. Cible directement le piège bêta (faiblesse #2) : un biais long structurel apparaît
dans la moyenne réelle mais disparaît sous randomisation du signe.

Pooling des tirages placebo des 39 lignes non-Globex (36 uniques après dédoublonnage de l'ancre) :
2000 répétitions de `max(|t_placebo|)` sur l'ensemble de la grille (comparateur EMPIRIQUE, pas
`N(0,1)` théorique — les variantes OFAT sont corrélées entre elles par construction, un maximum
d'ordre théorique sous indépendance sous-estimerait le bruit) :

| Percentile de max(\|t\_placebo\|) | Valeur |
|---|---|
| p50 | 2.37 |
| p90 | 3.13 |
| p95 | 3.35 |
| p99 | 4.45 |

**Le max réel observé (hors artefact Globex) = 4.29 (`retest`), au 98.8ᵉ percentile** de cette
distribution — proche du sommet du bruit attendu sur 39 tirages corrélés, **mais sous le p99
(4.45)**. Autrement dit : même la cellule la plus extrême de toute la grille ne se détache pas
nettement du maximum qu'on obtiendrait par pur hasard en balayant 39 variantes corrélées. C'est
un résultat cohérent avec « voisinage globalement mort, une cellule à la marge du bruit
extrême » — ni un rejet net, ni une preuve solide.

## 5. Artefact Globex — mesuré, pas une découverte de signal

Les 3 variantes `Globex_15/30/60` affichent des t astronomiques (27-29) et des R moyens de
3.3-4.9 — **ce n'est PAS un edge, c'est un artefact de normalisation**. Mesuré :

- OR médian RTH 30 min = **32.75 pts** ; OR médian Globex 30 min = **8.75 pts** (÷3.7)
- **36 % des jours Globex** ont un OR < 5 pts, **9 % < 2 pts** (contre 0 % sur RTH, min 1.5 pt)
- Le stop = distance OR (côté opposé), donc `R_unit` devient quasi nul certains jours (min observé
  0.5 pt) → un mouvement de prix normal pendant le reste de la session (des dizaines de points)
  se traduit en R de 50 à 106 — un seul trade peut valoir "106R"

C'est un **piège de dénominateur** : la fenêtre Globex 18:00-18:xx ET a un volume trop faible
pour produire un OR utilisable comme distance de stop. Le t énorme est présent de façon quasi
identique dans les 4 tranches de régime (t≈12-18 partout) — signature typique d'un artefact
MÉCANIQUE et structurel (présent à toute époque), pas d'un signal économique concentré. **Exclu
de la classification VIVANT malgré le passage mécanique des 4 conditions du kill-rule** — décision
prise sur inspection des grandeurs, documentée ici plutôt que silencieusement corrigée dans la
règle (le pré-enregistrement n'avait pas anticipé cette dégénérescence). Piste de leçon nommée à
faire graver : **"OR-mesuré-en-liquidité-fine comme distance de stop dégénère le ratio R"**
(candidate, pas de numéro attribué en session).

## 6. La seule variante qui clarifie le seuil — et pourquoi elle ne sauve ni ne condamne rien

**`retest`** (axe 3, confirmation) : attendre un repli-retest du niveau avant d'entrer.
`t_net=-4.29` (< -3.20, clarifie le Šidák sprint ET le seuil cumulé ~4.19), jambe longue
`t=-3.22`, jambe courte `t=-2.83` (même signe, L25 respecté), 3/4 tranches de régime négatives
(2010-13 t=-2.91, 2014-17 t=-3.75, 2018-21 t=-2.06, 2022-26 t=+0.04 quasi-nul), bootstrap IC95
[-0.105, -0.038] exclut zéro, bat le placebo de signe deux-côtés.

**Walk-forward 5 folds expanding — le signal DÉCROÎT jusqu'à disparaître** :

| Fold | Période | t |
|---|---|---|
| 1 | 2010-06→2013-09 | -3.06 |
| 2 | 2013-09→2016-11 | -3.61 |
| 3 | 2016-11→2020-01 | -1.73 |
| 4 | 2020-01→2023-03 | -1.14 |
| 5 | 2023-03→2026-05 | **+0.04** |

Le seul point de la grille qui dépasse le seuil de significativité rapporte donc une chose utile
pour la spec déployée : **attendre un retest après cassure a été une mauvaise idée sur la majorité
de l'historique — l'entrée immédiate (choix de la spec déployée) était le bon coin sur cet axe**
— mais l'effet (négatif) s'est éteint depuis 2020, donc ce n'est ni un axe d'amélioration
disponible, ni une preuve stable qu'on puisse citer prospectivement. C'est un résultat NÉGATIF qui
confirme un choix déjà pris, pas une piste d'amélioration.

## 7. Le presque-cas positif — `cal_Fri_only`, et pourquoi il ne compte pas comme neuf

`t_net=2.97` (sous le seuil 3.20 de justesse), jambes longue/courte toutes deux `t≈2.11` (même
signe), 4/4 tranches de régime positives, bootstrap IC95 [0.044, 0.232] exclut zéro. Walk-forward :

| Fold | Période | t |
|---|---|---|
| 1 | 2010-06→2013-08 | 0.19 |
| 2 | 2013-08→2016-10 | 0.76 |
| 3 | 2016-11→2019-12 | 1.25 |
| 4 | 2020-01→2023-03 | 2.11 |
| 5 | 2023-03→2026-05 | **2.52** |

Motif MONOTONE croissant — mais **c'est exactement le motif de la spec déployée elle-même**
(tranches de régime ancrage : -0.31, -0.85, +0.44, **+3.09**) : l'edge NQ ORB, tous jours
confondus, est déjà concentré 2022-26 (faiblesse #1 de la mission). `cal_Fri_only` ne fait que
répéter cette même concentration temporelle sur un sous-ensemble d'un jour sur cinq — ce n'est pas
un second mécanisme indépendant, c'est la même faiblesse structurelle vue à travers un filtre
calendaire. Le placebo calendaire apparié en compte (tirer 807 jours au hasard, 1000 tirages,
style L49) place Friday au **99.9ᵉ percentile** — mais ce chiffre teste seulement "ces 807 jours
précis battent-ils un sous-ensemble aléatoire de même taille", pas "avons-nous testé 5 jours de la
semaine et gardé le meilleur" — c'est précisément ce que corrige le seuil Šidák sur les 37
variantes, et Friday ne le franchit pas. **Verdict : loterie du jour-de-semaine sur fond de
concentration de régime déjà connue, pas une découverte.**

## 8. Classification complète (colonne `kill_rule_verdict` du CSV)

| Verdict | N | Variantes |
|---|---|---|
| VIVANT | 3 | Globex_15/30/60 — **exclues manuellement, artefact §5** |
| VIVANT_NEGATIF | 1 | `retest` — négatif, décayé à zéro (§6) |
| mort | 33 | tout le reste, y compris l'ancrage lui-même |

Aucune variante n'obtient un verdict `VIVANT` positif légitime.

## 9. n_tests et correction multiple

- Δn_tests **ce sprint = 37** (configurations neuves, règle du ledger : « if swapping it could
  have been the winner, it counts »).
- Cumul déclaré en entrée de sprint : **1867** (MR intraday ~1454 + grille momentum 341 + reliquat,
  cf. mémoire de session) → **cumul après ce sprint = 1904**.
- Seuil Šidák sprint (Δn=37, familywise 5 %) : `α_var=1-(1-0.05)^(1/37)≈0.00139` → **\|t\|≈3.20**.
- Seuil Šidák cumulé (n=1904) : `α_var≈2.69e-5` → **\|t\|≈4.19**. Un seul point de la grille
  (`retest`, \|t\|=4.29) le franchit — et il ne survit pas au walk-forward (§6). **Aucune variante
  n'est citable comme un edge NQ ORB neuf au niveau du programme entier.**

## 10. Gamma / flux d'options — donnée absente, pas de proxy fabriqué

Recherché explicitement dans le dépôt (`gamma`, `0dte`, `gex`, `OI`) : **rien d'exploitable**. Seul
`Crypto/research/active/vrp_short_gamma` (options crypto, sans rapport avec NQ) et une fiche
`alpha_hunt/promising/` non traitée sur les straddles 0DTE SPY. **Aucun proxy n'a été inventé.**
Piste données payantes à consigner si l'axe doit être rouvert un jour : CBOE DataShop (gamma
exposure dealer, historique NDX/ES options), OptionMetrics IvyDB (OI/greeks historiques),
SqueezeMetrics GEX (propriétaire, NDX/SPX). Aucun n'est dans le dépôt ni disponible gratuitement.

## 11. Sizing — non couvert, L61

Le sizing dépendant du chemin (pyramide, échelonné) n'a **pas** été testé dans cette grille : L61
(2026-08-21) a mesuré qu'une entrée échelonnée fabrique du t positif (18/18 cellules >2.5) sur du
**bruit pur**, non détecté par HAC — cela exige un placebo de construction identique, un travail
distinct d'une case de grille de plus. Non fait ici, documenté comme lacune plutôt que fabriqué.

## 12. Variantes explicitement NON couvertes (reprises de PREREGISTRATION §9)

- Croisement factoriel complet des 6 axes (2 268 cellules théoriques) — seulement OFAT depuis
  l'ancrage a été balayé ici.
- Sortie sur clôture de session Globex (au lieu du close RTH) quand l'OR est mesuré en Globex.
- Sizing dépendant du chemin (pyramide/échelonné) — nécessite placebo dédié (L61).
- Gamma/flux d'options/OI/0DTE — donnée absente du dépôt (§10).
- VXN (vol implicite spécifique Nasdaq) — absent du dépôt ; VIX (S&P) utilisé en proxy imparfait.
- Repli-retest à profondeur variable (seul le retest « au niveau exact » a été testé).
- Trailing stop à des multiples d'ATR autres que 1×.
- Sizing conditionnel au régime / vol-targeting dynamique intra-sleeve.
- FOMC intraday (heure exacte 14:00 ET) — seul le jour calendaire est filtré, pas une fenêtre
  horaire de blackout intraday.
- Interaction Globex-OR × exits/confirmations (l'artefact §5 rend ces croisements sans intérêt
  tant que la mesure de l'OR overnight n'est pas réparée — pas re-testé après diagnostic).

## 13. Conclusion

Sur les 37 variantes naïves couvrant 6 axes (fenêtre OR, durcissement de cassure, confirmation,
filtres de largeur/vol, sortie, calendrier), **aucune ne bat la spec déployée de façon robuste au
régime, aux deux jambes ET au placebo**. La spec déployée (`RTH, 30 min, touch, marge 0,
confirmation immédiate, sortie close RTH, aucun filtre`) se situe au **79ᵉ percentile** d'une
distribution de t globalement plate (médiane 0.54, 33/34 cellules non-artefactuelles
indiscernables du bruit) — c'est-à-dire près du sommet, pas au milieu, d'un nuage mort. Le seul
point qui franchit le seuil de significativité corrigé est **négatif et décayé à zéro** depuis
2020 ; le presque-cas positif (Friday) n'est qu'une redite de la concentration de régime 2022-26
déjà connue (faiblesse #1), pas un mécanisme distinct. **Verdict : voisinage mort. La spec
déployée est un choix défendable — le meilleur point structurel disponible dans ce voisinage —
mais rien dans ce balayage ne dissout, ni n'aggrave, les trois faiblesses connues (concentration
de régime, piège bêta possible sur la jambe courte, puissance structurelle insuffisante).** La
décision de maintien en octobre doit reposer sur ces trois faiblesses préexistantes, pas sur une
opportunité manquée de reparamétrage — il n'y en a pas dans ce voisinage.
