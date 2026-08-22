# Angle neuf — book intraday diversifié (√N)

Hypothèse testée : combiner plusieurs sleeves ORB **décorrélés** (instruments × sessions) remonte
le Sharpe quotidien du book, ce qui devrait lever la contrainte qui bloque (Sharpe trop bas pour
franchir +10 % en 2 mois). 7 sleeves construits : US100, US500, GER40 (session cash) + or et EURUSD
en sessions **London** et **NY** séparées.

## Ce que dit la donnée
**1. La décorrélation est excellente** (`figB1`) : corrélations quotidiennes ≈ 0 partout, sauf la
paire US100/US500 (0,66). GER40, or et FX sont indépendants des indices US **et entre eux** — même
or-London vs or-NY (−0,04). Le √N est donc *mécaniquement disponible*.

**2. Mais seuls 4 sleeves ont un edge positif après coûts** : US100 (Sharpe 1,16), US500 (0,67),
GER40 (0,58), or-NY (0,30). Les sleeves FX sont **négatifs** (tués par les coûts) et or-London aussi.
Pire : l'edge d'or-NY est un **artefact 2021** (+0,29 cette année-là, ≈ 0 sur 2022+).

**3. La diversification dilue le Sharpe au lieu de le monter** (`figB2`). Le book equal-risk
(Sharpe **1,03**) est *en dessous* du meilleur sleeve seul, US100 (**1,16**). Raison quant
classique : agréger des actifs de Sharpe inégaux à risque égal tire la moyenne vers le bas. Le
poids optimal (tangence) ∝ Σ⁻¹μ concentre sur le meilleur :

> **Book optimal (tangence) = 74 % US100 + 26 % GER40**, 0 % US500 (redondant), 0 % or (EV nulle).
> Sharpe **1,28** — soit seulement **+10 %** vs US100 seul. Plafond théorique non-corrélé = 1,46.

## Effet sur p(pass) FTMO (single attempt, MC, régime 2022+)
| Véhicule | p(<2 mois) | bust | p(éventuel, floor-taper, 0 % bust) |
|---|---:|---:|---:|
| US100 seul | 38 % | 56 % | 71 % (2 ans) |
| **Book tangence (US100+GER40)** | **43 %** | 51 % | **80 %** (2 ans) |
| Book equal-risk (4 sleeves) | 40 % | 59 % | 67 % |

## Verdict de l'angle
- La diversification **ne fait PAS franchir 50 % en <2 mois** (43 % au mieux). La contrainte de
  temps + l'absence d'alpha par-trade restent contraignantes ; c'est cohérent avec le first-passage.
- Son **vrai apport** est ailleurs : en sizing floor-taper (sans limite de temps), le book
  US100+GER40 atteint **~80 % de réussite éventuelle à 0 % de bust** (vs 71 % pour US100 seul), et
  GER40 — décorrélé des US — le rend **plus robuste au régime**. C'est un meilleur véhicule de
  *grind*, pas un raccourci vers les 2 mois.
- La leçon : « ajouter des sleeves » n'aide que si l'ajout a un Sharpe comparable. Ici le seul ajout
  utile est **GER40** (décorrélé ET +EV). Or/FX sont du bruit décorrélé sans rendement.

## Reco mise à jour
- **Si <2 mois est dur** : book tangence (US100+GER40) sizé pour la vitesse, **2-3 essais**
  (1−(1−0,43)² = 67 %, 3 = 81 %).
- **Si le temps peut se relâcher** (FTMO sans limite) : book US100+GER40 en **floor-taper**
  → ~80 % éventuel, 0 % bust. C'est l'option à variance minimale.

Fichiers : `figs/figB1_corr.png`, `figB2_sharpe.png`, `figB3_book_ppass.png`,
`code/multi_book.py`, `book_mc.py`, `book_finalize.py`.
