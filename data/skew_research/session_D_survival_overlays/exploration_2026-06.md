# Survival Overlays — session_D_survival_overlays — Exploration 2026-06
*Thèse testée : « le seul gain de session_A vient d'un OVERLAY DE RISQUE (DD-sizing), pas d'un filtre signal ».
On façonne le profil de SURVIE (skew, queue daily, p(bust) MC), PAS le Sharpe (L15). Chaque overlay comparé au
**TSMOM nu RESCALÉ AU MÊME LEVIER opérationnel** (L19). Anti-mining (L10, 1 spec canonique/overlay, pas de sweep).
Gate-0 : instruments FTMO-tradeables, daily. Périmètre : écrit UNIQUEMENT `session_D_survival_overlays/`. Rien figé/mergé.
Code : `code/overlays.py`, `code/pbust_mc.py`.*

## Baseline — TSMOM nu sur univers FTMO-tradeable SEUL (réf L19)
12M TSMOM, inverse-vol, equal-weight, 14 instruments FTMO (indices US500/US100/GER40/JP225/US30 ; or GLD, DBC, USO,
SLV ; FX FXE/FXB/FXY ; crypto BTC/ETH ; **PAS de bonds**), 2000-2026, rescalé 15 % ann.
**SR=0,88 · skew=+0,087 · maxDD=−34,2 % · worstDay=−5,27 %.** (Proche du 0,82 référencé ; le 0,82 incluait sans doute du non-FTMO.)
SR DSR-significatif (t≈4,8 sur 30 ans) même après haircut N_tests cumulé ~O(150) ; mais **les overlays sont jugés sur
skew/worstDay/p(bust) à vol égale, pas SR** (SR≈const par construction).

## Résultats overlays — à VOL ÉGALE 15 % (L19)
| Overlay | SR | skew | maxDD | worstDay |
|---|---:|---:|---:|---:|
| **baseline** | 0,88 | +0,087 | −34,2 % | −5,27 % |
| #1 DD-sizing (recursif, ddmax 10 %) | 0,57 | **+0,509** | **−24,9 %** | **−9,73 %** ⚠ |
| #2 vol-target SYM | 0,88 | +0,173 | −36,3 % | −7,86 % |
| #2 vol-target ASYM | 0,88 | +0,180 | −36,7 % | −8,24 % |
| #3 flat-overnight (idx) | 0,78 | +0,156 | −33,6 % | −5,57 % |
| #4 vol-of-vol throttle | 0,72 | −0,058 | −39,6 % | −6,80 % |
| #5 per-sleeve cap (±3z) | 0,87 | −0,006 | −33,7 % | **−4,68 %** |

## p(bust) MC — la métrique décisive (FTMO 2-step proxy : cum −10 % / day −5 % / cible +10 %, 60j, block=10, vol égale)
| Stratégie | skew | worstDay | p(bust)@15% | p(pass)@15% | ratio | p(bust)@30% | p(pass)@30% |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | +0,09 | −5,27 % | **8,3 %** | 27,9 % | **3,36** | 41,6 % | 49,0 % |
| #5 cap | −0,01 | −4,68 % | 8,3 % | 27,8 % | 3,35 | 41,6 % | 49,1 % |
| #1 DD-sizing | +0,51 | −9,73 % | **16,4 %** | 18,6 % | 1,13 | 31,2 % | 32,5 % |
| #1+#5 | +0,19 | −9,79 % | 16,3 % | 18,7 % | 1,15 | 31,9 % | 32,7 % |

## Verdict par candidat
- **#1 DD-sizing — REJETÉ (thèse renversée).** Le skew **s'améliore (+0,087→+0,51, et +1,35 OOS 2023+)** ET le maxDD multi-jour
  baisse (−25 % vs −34 %), MAIS à vol égale le rescaling (L19) fait tourner la stratégie **plus chaud en période calme**
  → **worstDay −9,73 %** (vs −5,27 %) → la **règle daily −5 %** mord → **p(bust) DOUBLE (8,3→16,4 %)** à levier modéré.
  À 30 % il baisse p(bust) (31 vs 42 %) mais **le ratio pass/bust empire partout** (1,13 vs 3,36) = **dé-levier déguisé**, pas un edge.
  Sensibilité : **s'effondre à ddmax=7 %** (skew −0,73, worstDay −28 %). → KILL.
- **#2 vol-target asymétrique — KILL.** asym (+0,180) ≈ sym (+0,173) : **l'asymétrie n'apporte rien** ; le skew+ de #1 ne vient
  PAS de l'asymétrie-vol mais de l'**état-drawdown** (path-dependence). Et même le vol-target (sym/asym) ne donne que +0,17 skew.
- **#3 flat-overnight — KILL.** Coût EV net (SR 0,88→0,78) **sans** réduction de queue (worstDay même légèrement pire −5,57 %).
  La queue daily de ce book diversifié **n'est PAS un gap overnight d'indice** (elle vient de l'intraday + commo/FX/crypto).
- **#4 vol-of-vol throttle — KILL.** Empire tout à vol égale (skew −0,058, maxDD −39,6 %) : la vov n'est pas un signal avancé
  net ; le rescaling amplifie les mauvais jours.
- **#5 per-sleeve cap — NEUTRE survie.** Améliore le worstDay cosmétiquement (−4,68 < seuil 5 %) et préserve le SR, MAIS
  **p(bust) inchangé** (8,3 %) : à 15 % les busts viennent surtout du **maxDD static multi-jour**, que le cap single-day ne
  touche pas. Ni nuisible ni utile → pas une brique.

## Conclusion session_D
**AUCUN overlay ne réduit p(bust) à levier égal sans coût.** La thèse « DD-sizing = overlay de survie » est **réfutée
quand on juge sur p(bust) (pas sur skew)** : le gain de skew est réel mais **orthogonal à la survie FTMO**, car la contrainte
liante à levier réaliste est la **règle daily single-day**, pas la distribution multi-jour. **Le bon levier de survie est le
LEVIER lui-même** (baisser le gross), pas un overlay path-dependent.

## Candidats-leçons (NOMMÉS)
> **LESSON-CANDIDATE: skew-is-not-p(bust)-for-FTMO** — à vol égale, un overlay peut **améliorer le skew multi-jour
> (+0,09→+0,51) tout en EMPIRANT la queue single-day** (worstDay −5,3→−9,7) et en **doublant p(bust)** (8→16 %). La
> contrainte FTMO liante à levier réaliste est la **règle daily −5 % (queue single-day)**, que le skew ne capture pas.
> Juger les overlays de survie sur **p(bust) + worstDay à vol égale**, JAMAIS sur le skew.

> **LESSON-CANDIDATE: dd-throttle-amplifies-single-day-tails-at-equal-vol** — dé-risquer en drawdown baisse la vol, donc
> la normalisation à vol égale (L19) fait tourner **plus chaud en période calme** → **queues single-day plus grasses**.
> La discipline L19 révèle exactement le coût caché que la vue naïve « le skew s'est amélioré » masque.

> **LESSON-CANDIDATE: survival-overlays-are-disguised-deleveraging** — le seul bénéfice p(bust) de DD-sizing (à fort
> levier) s'accompagne d'une perte proportionnelle de p(pass) (**ratio pass/bust 1,13 vs 3,36**) = c'est du **dé-levier**,
> pas un edge de survie. Pour baisser p(bust), baisser le **levier** directement (plus simple, sans coût de queue single-day).
