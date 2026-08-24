# AUDIT INDÉPENDANT — Gold dosing + or-trend vs ASIA (Part A / Part B)

**Auditeur :** session Claude Code fraîche (author≠auditor), yeux neufs, posture adversariale.
**Date :** 2026-06-20 · **Worktree isolé :** `Algo_claude_goldcompare` (lecture seule, aucun `git`, aucun fichier live touché).
**Cible :** `STUDY_GOLD_DOSING_COMPARE_2026-06-20.md` + `PREREGISTRATION_GOLD.md`.
**Env :** `/usr/bin/python3` (numpy 2.0.2, pandas 2.2.3). Tous les scripts re-exécutés.

---

## VERDICT GLOBAL : **CONFIRM-WITH-CAVEATS**

Les deux verdicts directionnels de l'étude tiennent et sont reproductibles **au chiffre près** :
- **Part A — dosing dilemma : CONFIRMÉ et ROBUSTE.** Aucune dose net-positive ; dilution dès la dose
  infinitésimale ; conclusion stable sur la fenêtre canonique ET sur la fenêtre élargie. Le mécanisme
  « book épinglé sur le floor » est non seulement vrai, il est **plus fort** que ce que l'étude écrit.
- **Part B — or-trend = meilleur conteneur : CONFIRMÉ.** Le swap est implémenté correctement, la
  comparaison est **vol-fair** (ASIA K=1 ≈ vol déployée d'or-trend), et la décorrélation ρ≈0.08 est réelle.

**Les caveats (d'où "with-caveats") :**
1. **La narration "complémentarité temporelle" de Part B (c) est partiellement SUR-VENDUE** — l'argument
   "ASIA +8.8% sur les jours or-trend OFF" est **mécanique** (ASIA gagne ~+3 bps/jour TOUS les jours, pas
   spécifiquement les jours OFF), et l'"anti-phase" repose presque entièrement sur **un seul épisode 2018-19**.
   La preuve solide de complémentarité est ρ=0.08, pas le temporel.
2. **Le `min_eq` cité comme preuve de mécanisme (item C) est sur-estimé par un artefact du "breaker"** —
   à corriger dans la formulation, mais le mécanisme directionnel survit (vérifié par une voie indépendante).
3. **Asymétrie structurelle breaker** : la jambe ASIA injectée est testée contre un hard-floor SANS breaker,
   alors que les jambes du book ONT un breaker. Tilt léger contre ASIA — mais le dilemme tient même à dose
   0.02× où breaker/stop sont inertes, donc ce n'est PAS un refute, juste un caveat de calibration.
4. **ρ OOS 2020-26 = 0.226** (vs all-days 0.084) sous-souligné : décorrélation plus faible en période récente.

Aucune de ces réserves ne renverse le go/no-go. **Le book a raison d'utiliser or-trend ; ASIA-gold reste fermé
sur FTMO à toute taille.** Le résultat le plus important est en item C (ci-dessous).

---

## Item A — Baselines : **PASS**

`validate_baselines.py` reproduit **exactement** :
```
challenge cohorts 462 | canonical funded cohorts 191
(i)  ASIA-OFF challenge pooled = 87.01%  -> PASS
(ii) book-only canonical funded: survive252 97.9%  fundedV $1442  (anchor)
(iii) asia_stop -2.5%: trig 0.1%  Sharpe 1.13  alpha_given_up 2.7%
(iv) or-trend reconstructed: n=6895 | long 25.8% | active 39.3% | Sharpe(active) 0.40
```
Anchor (97.9% / $1442) et ASIA-OFF (87.01%) tiennent. L'ablation est donc fondée sur une base saine.
Bonus vérifié : le stop −2.5 % est quasi-inerte (trig 0.1 %, Sharpe 1.13 vs 1.14 sans stop) → **le dilemme
n'est PAS dû à un stop qui détruirait ASIA** ; ASIA dilue à plein edge.

## Item B — Dose appliquée UNE fois (pas de double-K) : **PASS**

Vérifié au code ET numériquement :
- `apply_stop(K=d, X=0.025)` retourne `net = d × net_base`, clampé à `−2.5%` SI `low_K ≤ −2.5%`.
- Injection avec `asia_lev=1.0` → `a_net = INIT × 1.0 × asia_net[i]`. **Dose appliquée exactement une fois.**
- Le floor du stop (−2.5 % du compte) est **constant**, NON re-scalé par la dose (correct).

Preuve numérique (dose → mean net, linéaire, et trig) :
| dose | mean net (bps) | worst close | worst low | trig_frac |
|--:|--:|--:|--:|--:|
| 0.10 | +0.31 | −0.38% | −0.78% | **0.000%** |
| 0.25 | +0.77 | −0.94% | −1.94% | **0.000%** |
| 0.50 | +1.50 | −2.50% | −2.50% | 0.040% |
| 1.00 | +3.06 | −2.50% | −2.50% | 0.139% |

La moyenne scale **linéairement** (0.31→0.77→1.50→3.06) = dose appliquée une seule fois ✓. À 0.10× et 0.25× le
stop ne déclenche **jamais** (worst low > −2.5%) → la série est purement K-scalée, pas de dose². Le double-K de
l'asia-funded est bien corrigé.

Re-run `partA_dosing.py` (reproduit le tableau de l'étude au chiffre près) :
```
dose  book+ASIA surv  Δsurv  fundedV  Δextract  net-positive?
0.10      85.3%       -12.6    1274     -168        no
0.25      67.5%       -30.4    1020     -422        no
0.50      68.6%       -29.3    1470      +28        no
0.75      64.9%       -33.0    1736     +294        no
1.00      65.4%       -32.5    2124     +682        no
VERDICT Part A: DOSING DILEMMA (no net-positive dose)
```
**0 dose net-positive. La dose minimale (0.10×) dilue −12.6 ET extrait NÉGATIF (−168). Dilemme prouvé.** ✓

## Item C — Mécanisme "book épinglé sur le floor" : **PASS (mécanisme RÉEL, plus fort que dit), avec une CORRECTION de formulation**

C'est le cœur de l'étude, et le résultat le plus important de cet audit. **Le mécanisme est vrai et plus
décisif que ce que l'étude affirme**, MAIS deux précisions s'imposent.

**(C.1) Le book frôle le floor de manière EXTRÊME — confirmé directement.**
À dose 0.02× (≈0.06 % vol, +0.06 bps/jour, presque rien), la survie chute déjà 97.9 % → 91.6 % (−6.3 pt).
J'ai attribué chaque bust à sa jambe :
```
dose 0.02: busts=56/191  via ASIA-leg (no breaker)=52   via BOOK-leg=4
dose 0.10: busts=64/191  via ASIA-leg=47               via BOOK-leg=17
dose 0.25: busts=128/191 via ASIA-leg=125              via BOOK-leg=3
dose 1.00: busts=97/191  via ASIA-leg=95               via BOOK-leg=2
```
Et pour les 52 busts via-ASIA à dose 0.02× : **bal à l'ouverture = $9000–$9004** (0.7 à 3.6 $ au-dessus du
hard-floor $9000), slack médian **$1.01**, dip ASIA médian **$1.51**, et **52/52 ont slack < |dip ASIA|** —
ASIA est littéralement la dernière goutte sur des cohortes que le book a garées à quelques dollars du floor.
**Le mécanisme "n'importe quelle source de drawdown always-on bascule les cohortes marginales" est confirmé
de la façon la plus crue possible.** L'étude le sous-vend même.

**(C.2) CORRECTION : le `min_eq` cité comme indicateur de proximité-floor est un ARTEFACT du breaker.**
L'étude (et le triplet pré-enregistré) s'appuie sur `min-balance p5 / min_eq`. Or `min_eq` est **sur-estimé** :
il est calculé (asia_inject.py:249) sur la trajectoire d'équité AVANT le flatten du breaker. Exemple tracé
(cohorte i0=384, 2015-03-24, China-deval 2015-08-24) : `min_eq = $8909 = −10.91 %` pour une cohorte qui
**SURVIT 504 jours** (wd=0). Impossible sous un floor −10 % dur — sauf que bar 73 le breaker (`brk_line =
lim_eff + 0.3×BUDGET = $9150`) flatte la position AVANT le bar 74 où `eq.min()=8909` aurait eu lieu. Le
réalisé s'arrête à ~$9133 (−8.7 %). Donc **102 "survivants" affichent min_eq dans la dernière bande de 1 %
sous le floor, et beaucoup à exactement −10.00 %** : ce sont des points contrefactuels pré-breaker, pas le
réalisé. → **Ne pas citer min_eq/p5 comme preuve de proximité-floor.** La bonne preuve est (C.1) : `bal` à
l'ouverture ∈ [$9000, $9004]. Le mécanisme survit, sa quantification par min_eq est fausse.

**(C.3) Non-monotonie 0.10→−12.6 / 0.25→−30.4 / 0.50→−29.3 : PAS un bug.** Grille fine :
```
dose  0.02  0.05  0.10  0.15  0.20  0.25  0.30  0.40  0.50  0.75  1.00
surv  91.6  86.9  85.3  82.7  69.6  67.5  66.0  67.5  68.6  64.9  65.5  (%)
```
Décroissance monotone 0.02→0.30 puis **plateau bruité 64–69 %** (±2-3 cohortes = bruit de discrétisation
à N=191). La "saturation" est réelle (la dilution sature ~0.20×, pas 0.25× comme écrit — minime). Le wobble
0.25↔0.50 est du bruit de cohortes, pas une marche. La série d'ENTRÉE est parfaitement monotone (item B), donc
toute non-monotonie vient de l'interaction floor/cohortes — attendu, pas pathologique. **Le fundedV qui baisse
0.10→0.25 ($1274→$1020) puis remonte est cohérent** : moins de survivants (busts $0) domine, puis chaque
survivant extrait plus. Pas de bug.

## Item D — Standalone + reconstruction or-trend : **PASS (proxy honnête)**

`partB_compare.py` reproduit : or-trend Sharpe full/active **0.3/0.4**, ASIA **1.14**, ρ vérifiés.
La reconstruction `ortrend_net` = `w×rets − turn + swap` avec `w = WT["XAUUSD"]` (colonne 0 confirmée = XAUUSD,
colonne 1 = USDJPY/J1). C'est un **proxy signal-level**, pas le P&L exact moteur : le moteur applique
`tgt[0] = WT[i,0] × (vm·taper·glide·pace) × eq`, puis margin-cap + quantize. En FUNDED `vm=1.0` donc
notional ≈ reconstruction ; en CHALLENGE `vm=14` (la reconstruction ne le reflète pas — mais elle ne sert PAS
au swap challenge, qui utilise le vrai moteur). Donc **pas de contamination** : reconstruction = comparaison de
qualité de signal (légitime, et même préférable car isole le signal de la plomberie), swap (e) = vrai moteur.
Le label "WT[XAUUSD] net reconstruit" est honnête.

## Item E — Complémentarité temporelle : **CONCERN (sur-vendu, mais pas faux)**

Reproduit exactement (2018-19 : or-trend +5.4 % / ASIA −7.7 % ; OFF-days : ASIA +8.8 %). MAIS :

**(E.1) "ASIA comble le trou des jours or-trend OFF" est MÉCANIQUE, pas une complémentarité.**
ASIA mean = **+3.49 bps/jour sur les jours or-trend OFF** vs **+2.77 bps/jour sur les jours ON** — quasi
identique (les OFF sont à peine meilleurs). Le "+8.8 % annualisé" sur les OFF n'est QUE la conséquence d'ASIA
qui gagne ~+3 bps **tous les jours** ; ASIA ferait +8.8 % sur n'importe quel sous-ensemble. Ce n'est PAS de
l'anti-phase, c'est l'always-on — précisément la propriété que le book funded PUNIT (ironie). Présenter ça
comme preuve de complémentarité est une **surinterprétation**.

**(E.2) L'"anti-phase" repose sur UN seul épisode.** Année par année, 2018 (−13.7 % ASIA / +3.9 % or-trend)
et 2019 sont les SEULES 2 années consécutives où ASIA<0 et or-trend>0. En sens inverse, 2012/2021/2023 ont
or-trend<0 ET ASIA fortement>0. Donc "anti-phase" comme propriété générale est trop fort ; 2018-19 est un
épisode réel (le drift overnight gold est mort là), pas cherry-pické arbitrairement, mais c'est le SEUL.

**Verdict E :** la **décorrélation ρ=0.08 est la vraie preuve** (solide, robuste) et suffit à valider le seuil
pré-enregistré « ρ<0.50 ». L'habillage "anti-phase / complémentaires" est défendable sur ρ mais **sur-vendu**
par le temporel. Note : ρ OOS 2020-26 = **0.226** (sous-souligné) — toujours <0.50, mais moins décorrélé en
période récente. Conclusion "décorrélées" tient ; le titre "ρ 0.08" est le cadrage le plus favorable.

## Item F — Swap hypothétique (claim central) : **PASS (correct ET vol-fair)**

Reproduit exactement :
```
book[or-trend] std            challenge 87.01%  funded 97.9%
book[ASIA replaces or-trend]  challenge 80.95%  funded 72.3%
book[BOTH or-trend+ASIA]      challenge 87.45%  funded 65.4%
```
**Implémentation correcte :** `WT_noOR[:,0]=0.0` zéro UNIQUEMENT la jambe XAUUSD/or-trend, garde J1 (col 1).
ASIA injectée K=1. "Replace" = J1 + ASIA-gold ; "BOTH" = J1 + or-trend-gold + ASIA-gold. ✓

**FAIRNESS (le test décisif) :** la comparaison "remplacer or-trend par ASIA" pourrait être truquée si ASIA
K=1 était sur-dimensionnée. Mesuré :
```
or-trend (déployé, tous jours) : ann-vol 7.10%  mean +0.73 bps
ASIA K=1 (always-on)           : ann-vol 6.83%  mean +3.08 bps   -> ratio 0.96x (≈ matché)
or-trend (jours actifs seuls)  : ann-vol 11.03% mean +1.76 bps
```
**ASIA K=1 a la MÊME vol annuelle qu'or-trend déployée (ratio 0.96×) → le swap est vol-fair, ASIA n'est PAS
sur-sizée.** La SEULE différence est la distribution temporelle : or-trend concentre 7.1 % de vol sur 56.9 %
des jours (0 le reste), ASIA étale 6.8 % sur 99 % des jours. Donc la conclusion "le book récompense le faible
risque always-on, pas le Sharpe" est **vol-fair et soutenue** — ASIA perd PUREMENT sur l'axe always-on, à vol
totale égale. C'est un argument propre. (ASIA livre 4× le rendement à vol égale → Sharpe 1.14, mais le
drawdown always-on tue la survie : le dilemme est réel, pas un artefact de sizing.)

**Caveat de calibration (asymétrie breaker) :** la jambe ASIA (asia_inject.py:217-224) a un hard-bust
`bal+a_low < lim_eff` SANS breaker ; les jambes du book (244-255) ont un breaker (`brk` flatte à `lim_eff+
0.3·BUDGET` AVANT le floor). ASIA est donc tenue à une barrière plus stricte → tilt léger contre ASIA. C'est
défendable (un hold overnight ne se micro-gère pas intraday comme une jambe du book), et **le dilemme tient
même à dose 0.02×** où breaker/stop sont inertes et le dip ASIA ≈ $1-5 → la conclusion ne DÉPEND pas de cette
asymétrie. Donc caveat, pas refute.

## Item G — Discipline pré-reg + calibration verdict : **PASS-WITH-CAVEATS**

- **Seuils figés et honnêtement appliqués :** Part A (Δsurv≥−2.5pt ET Δextract>0) et Part B (ρ<0.50 ET
  anti-phase) sont dans la pré-reg (commit cité) et appliqués sans déplacement. ✓
- **Fenêtre canonique** (pas de convenance) : leçon panier correctement appliquée, et c'est le choix
  CONSERVATEUR (book-only 97.9 % plus haut → dilution apparente plus grande). **Robustesse vérifiée** : sur la
  fenêtre élargie (book-only 93.0 %), dilution −8.9 pt @0.10× / −25.6 pt @1.0× → **dilemme tient sur les deux
  fenêtres**. Conclusion non-dépendante de la fenêtre. ✓
- **"both gold CLOS sur FTMO"** = juste (funded BOTH 65.4 % << 97.9 %).
- **Caveat "récoltable sur book perso non-floor"** : **fair, pas hand-wavy** — deux séries décorrélées (ρ0.08)
  à Sharpe 0.4 et 1.14 améliorent mécaniquement le Sharpe portefeuille ; le floor statique −10 % est
  spécifiquement ce qui l'empêche sur FTMO. C'est une déduction correcte (à confirmer si jamais poursuivie,
  mais légitime comme note hors-périmètre). ✓
- **Sur-déclarations à corriger** (n'affectent pas le go/no-go) : (i) item C cite min_eq/p5 alors qu'il est
  faussé par le breaker — utiliser bal-à-l'ouverture ∈[$9000,$9004] ; (ii) "complémentarité temporelle /
  anti-phase" (E) sur-vend un effet mécanique + un seul épisode — la preuve est ρ ; (iii) "dilution sature
  0.25×" → en réalité ~0.20× (cosmétique).

---

## Tableau récapitulatif

| Item | Sujet | Verdict | Chiffres reproduits |
|---|---|:--:|---|
| A | Baselines (ASIA-OFF 87.01, anchor 97.9/$1442, stop) | **PASS** | exacts |
| B | Dose appliquée une fois (pas de double-K) | **PASS** | mean linéaire 0.31→3.06 bps, trig 0%@≤0.25× |
| C | Mécanisme floor-grazing | **PASS** (+ correction min_eq) | 52/52 busts @bal∈[$9000,$9004], slack med $1.01 |
| D | Standalone + reconstruction or-trend | **PASS** | Sh 0.3/0.4 vs 1.14 |
| E | Complémentarité temporelle | **CONCERN** | OFF-days +8.8% = mécanique ; anti-phase = 1 épisode |
| F | Swap hypothétique (claim central) | **PASS** | swap correct + vol-fair (ASIA 6.83% ≈ or-trend 7.10%) |
| G | Pré-reg + calibration verdict | **PASS-WITH-CAVEATS** | robuste 2 fenêtres ; 3 sur-déclarations cosmétiques |

## Le bug / la sur-déclaration la plus importante (nommée exactement)

**`min_eq` est sur-estimé par le breaker (asia_inject.py:249 calcule `eq.min()` sur la trajectoire PRÉ-flatten).**
Conséquence : le triplet pré-enregistré inclut « min-balance p5 » comme indicateur de proximité-floor, mais
des cohortes qui SURVIVENT affichent min_eq jusqu'à **−10.91 %** (sous le floor dur −10 %) — points
contrefactuels que le breaker a empêché de se réaliser. **L'item C de l'étude doit citer `bal` à l'ouverture
de la jambe ASIA (∈ [$9000, $9004], 52/52 busts à dose 0.02×) comme preuve de proximité-floor, PAS min_eq/p5.**
Le mécanisme directionnel est confirmé par cette voie indépendante ; seule sa quantification par min_eq est
fausse. Aucun impact sur le go/no-go (Part A et Part B restent : **both-gold CLOS sur FTMO, le book a raison**).

---
*Audit exécuté en lecture seule, worktree isolé, aucun `git`, aucun fichier live/Portfolio/strategies/v22/
deep_history_utc/cleanroom modifié. Tous les scripts (`validate_baselines.py`, `partA_dosing.py`,
`partB_compare.py`) ré-exécutés ; investigations supplémentaires : grille de dose fine, attribution des busts
par jambe, fairness vol, robustesse de fenêtre, trace cohorte i0=384.*
