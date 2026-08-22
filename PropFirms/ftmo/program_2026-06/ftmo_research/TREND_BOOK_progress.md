# Book Trend-Following — ledger de progression
### Construction incrémentale du book diversifié. Conforme `CHARTE_methodo_trendfollowing.md`.

> **Thèse : un seul actif TF = Sharpe ~0,5 → mur ~33 %. Le levier est la DIVERSIFICATION cross-asset (CTA).** Cible : 5 sleeves décorrélés → Sharpe ~1,3 → p(pass) ~48-52 %. Edges réels & cost-robustes (≠ ORB).

---

## Sleeves validés

| sleeve | spec | SR (full / commun) | skew | swap | gap-risk (pire jour) | statut |
|---|---|---:|---:|---|---:|---|
| **J1** USDJPY | TSMOM 12-1 carry-aligned | 0,58 / 0,49 | −0,29 | **+** (carry) | faible (−5,1 %) | ✅ réel, régime-stable, cost-robuste |
| **G1** Gold | TSMOM 12-1 | 0,69 / 0,54 | −0,16 | − (funding) | moyen (−11,4 %) | ✅ réel, 3 décennies + |

## Books mesurés
| book | période | Sharpe | skew | p(pass) 2-step |
|---|---|---:|---:|---:|
| J1+G1 | 2001-26 (full) | **0,72** | −0,36 | **~37 %** |
| J1+G1+B1 | 2015-26 (commun BTC) | 0,59 | −0,55 | ~35 % |

corr toutes paires ~0 (J-G −0,01, J-B +0,02, G-B +0,05) — décorrélation parfaite ✓.

## Projection RÉVISÉE (la charte corrige l'optimisme)
La projection initiale « 5 sleeves à 0,6 → Sharpe 1,34 → ~50 % » **ne tient pas** : (a) vrais sleeves ~0,3-0,6 (pas 0,6+), pire sur période récente ; (b) **oil échoué** ; (c) **crypto negative-skew + perce le DD**. **Le book réel plafonne ~Sharpe 0,6-0,72 / p(pass) 35-37 %** — au-dessus du mur single-asset 33 %, mais loin des 50 %.

## Adaptation propfirm (overlays sur J1+G1, full-sample)
| overlay | p(pass) | bust | verdict |
|---|---:|---:|---|
| baseline fixe 1,5 % | 36 % | 55 % | réf |
| **floor-taper c=0,15** | 33 % | **27 %** | ✅ KEEPER (coupe le bust de moitié) |
| floor-taper c=0,25 | 36 % | 39 % | équilibre pass/bust |
| + crash-filter | ~même | ~même | ❌ rejeté (skew inchangé) |

→ **Le floor-taper coupe le bust (55%→27%) mais ne monte pas le p(pass)** (sizing ≠ levier, L35). **Crash-filter inutile** (skew −0,36→−0,35 : le négatif vient du trend qui tient graduellement, pas de jours isolés). **Plafond p(pass) ~36% confirmé.** Seul levier restant non testé = **modifier le signal pour un skew positif** (exit plus rapide / trailing stop).

## Modif skew (trailing-stop) — ÉCHEC + faux positif attrapé
- Version naïve : book Sharpe 2,05 / skew + → **100 % look-ahead** (out[t] enregistré après réalisation de rr[t] et déclenchement du stop). Charte = alarme « trop beau ».
- **Corrigé (timing propre, test délai+1 stable)** : book Sharpe **0,72→0,32**. Le stop whipsaw sur des trends lents (rejeté pour ça). ⚠ **MAJ revue équipe : la prémisse "skew négatif structurel" était FALSE** — J1 skew mensuel **+0,70** (positif), worst-days 1/10 en crise. Le trailing-stop répondait donc à un problème inexistant ; il reste rejeté (whipsaw), mais pas pour le skew. → on reprend la recherche.

## Voie 2 — p(pass) par structure de firme (le DD journalier étrangle-t-il le book ?)
| structure | full | récent |
|---|---:|---:|
| FTMO 2-step (daily 5 %, static) | 36 % | 33 % |
| 1-step no-daily, total 10 % **STATIC** | **62 %** | 59 % |
| 1-step trailing 10 % (large) | 53 % | 50 % |
| 1-step trailing 6 % (futures prop réaliste) | 36 % | 35 % |
| 1-step trailing 5 % (Apex serré) | 31 % | 31 % |

**Verdict : le levier structure est énorme en théorie (62 %) mais s'évapore en pratique.** Les firmes futures réelles ont un **trailing serré 5-6 %** → ~35 %, comme FTMO (le trailing attrape les pullbacks comme le daily attrape les crash-days). Le 62 % exige un 1-step **static large no-daily = la firme classée "n'existe pas" (canonique #1)**. → **Aucune structure réelle ne sauve le book ; ~35 % partout. Path = multi-essais ou déploiement perso.**

## B1 (crypto) — validé-avec-caveat
SR 0,67 full / 0,34 récent, décorrélé, MAIS **skew −0,83** (TSMOM lent reste long dans les crashs) + **pire jour compte −9,1 % > DD 5 %** (gap non dompté par le vol-target laggé). Apport book +3 pp net (diversification > skew), mais n'corrige PAS le skew comme espéré. **Marginal.**

## Caveats (charte)
1. Projection suppose 3 sleeves de plus *aussi propres* — **oil/crypto = risque de gap** (self-critique) à vérifier, dilué en book mais réel.
2. **Skew book négatif (−0,36)** — besoin d'un sleeve à **skew positif** (crypto TF) pour corriger la barrière.
3. Mur Sharpe : même à 1,3, le 2-step plafonne ~50 %. Viser book déployable réel (perso/CV) + firme à meilleure structure, pas miracle FTMO.
4. Swap mesuré sur démo avant capital (J1 + / G1 −) ; données rates = proxy ^IRX (FRED injoignable sandbox), à durcir.

## Sleeves / directions REJETÉS (charte = on consigne les échecs)
- **O1 Oil carry+momentum** — **SR −0,37, 5/21 années +, négatif les 2 décennies.** Oil = mauvais TF single-commodity (contango 60 %, vol 41 %, mean-reversion, désastre avril 2020 prix négatif). **N'entre pas dans le book.**
- **XS Cross-sectional momentum (31 instr, market-neutral)** — **GROSS SR +0,17 (faible même sans coût), NET −0,49** (financing long-short CFD ~1,5bp/j sur brut tue l'edge, L28/L33). Univers hétérogène = pas de relative-strength propre. **Rejeté.**
- **CTA complet (31 marchés TS-momentum, la dernière cartouche)** — **GROSS SR +0,34, NET +0,23, skew +0,70 (positif !)** mais **PLUS FAIBLE que le book focalisé** (le large univers dilue USDJPY/or avec 29 marchés à trend faible ; cohérent avec l'industrie CTA réelle 2000-26 + trend-winter 2010s). **p(pass) 1 essai ~22 % < book 36 %.** Le skew positif ne compense pas le Sharpe faible. **Rejeté. La diversification large dilue, n'amplifie pas.**

## CONCLUSION DÉFINITIVE (5 familles confirmées)
Breakout (mort coût) · Trend single-asset (réel ~0,7, book 36 %) · CTA complet (dilué, 22 %) · Cross-sectional (fail) · Structure firme (ne sauve pas). **Aucune stratégie price-pattern retail ne passe FTMO confortablement en 1 essai. Plafond ~36 %, structurel.** Meilleur actif réel = **book J1+G1** (déployable perso/CV). FTMO single-attempt = non résolu structurellement.

## Next candidats (à trancher)
- **Crypto TSMOM (B1)** — ⭐ skew **positif** (corrige le book −0,36) + décorrélé + momentum le plus fort. **Disponible sur FTMO** (BTCUSD/ETHUSD…). Gap extrême mais dilué en book. Le plus complémentaire.
- **Nasdaq dual-momentum (N1)** — décorrélé-ish, MAIS swap long négatif lourd.

---
*Ledger book 2026-06-03. `outputs/book_JG.parquet`, `usdjpy_clean.parquet`, `gold_clean.parquet`. Backtest, 0 jour live.*
