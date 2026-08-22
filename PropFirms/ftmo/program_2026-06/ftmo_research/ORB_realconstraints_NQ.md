## ORB 30-min NQ — Le VRAI chiffre p(pass) (contraintes FTMO 2026 + placebo)

> **TL;DR — Le 98.6% K5 du Fil 1b n'était PAS un artefact de mauvaises
> hypothèses : les règles FTMO 2026 confirment NO time limit (changement
> juillet 2023), donc le simulateur était déjà correct. MAIS le placebo
> révèle la vraie cause du 100% : c'est mécaniquement DÛ à
> floor_taper × unlimited-time × mean_R ≥ 0. La preuve : un random Gaussien
> à zero-mean (sample chanceux 0.027) sous le même floor_taper donne 97.7%
> OOF. L'ORB lui-même apporte ~+21pp via son skew distributif, mais le gros
> du 100% n'est pas un "edge ORB" — c'est de la math no-bust + temps illimité.**
>
> **Chiffres déployables HONNÊTES (régime mid-vol aujourd'hui, FTMO 2026
> rules confirmées):**
>
> - **V2+E7 SEUL (Lever A, pas de floor)** : OOF 75% pooled / régime mid 46.3%.
>   Régime-conditionnel brutal: 0% en 2013-2015, 100% en 2019-2023.
> - **V2+E7 + floor_taper (K2)** : OOF held 90.4% / strict 77.1%.
>   Robuste, principalement par no-bust math.
> - **K5 (V2+E7 + floor + vol_high)** : OOF held 100% / strict 85.3%.
>   Sim "always passes eventually" sous FTMO unlimited time.
>
> **Interprétation honnête** : V2+E7 SEUL = 46% aujourd'hui = le vrai chiffre
> ORB déployable durable. Le 100% K5 = comment FTMO no-time-limit + ne-pas-bust
> deviennent algorithmiquement un "pass garanti". Pari différent : pari sur la
> persistence de la règle FTMO no-time-limit, pas sur un edge ORB.

---

## Check 0 — Règles FTMO 2026 confirmées (sources web)

| Règle | Valeur (2-Step Challenge) | Source |
|---|---|---|
| Profit target P1 (Challenge) | 10% | FTMO trading-objectives, blog 2026 |
| Profit target P2 (Verification) | 5% | FTMO trading-objectives |
| Daily Loss Limit | 5% | FTMO trading-objectives |
| Max Loss Limit | 10% | FTMO trading-objectives |
| Min trading days | 4 | FTMO trading-objectives |
| **Time limit / Trading Period** | **UNLIMITED** (since July 13, 2023) | FTMO blog "Trade without any time limit" |
| Consistency rule 2-Step | **NONE** (Best Day Rule = 1-Step only) | FTMO 2-step-challenge page |
| Fees | One-time, refunded on first reward (2-Step) | FTMO FAQ |
| Inactivity | Account contact after "a few weeks", freeze 7d-6mo available | FTMO FAQ |

**Conclusion Check 0 :** mon simulateur `nq_sim_v3` modélise exactement ces
règles. Le rapport Fil 1b qui mentionnait "FTMO eval ~30-60j cap" était une
ERREUR — cette règle a été supprimée en juillet 2023. **Donc le 100% OOF
de K5 n'est pas overstated par un time-cap manquant** — la simulation
correspond aux vraies règles.

---

## Check 1 — K5 + V2+E7 sous FTMO 2026 (in-sample / OOF / strict)

Reporting `standard` (exclut les censurés) ET `strict` (censured=FAIL = borne
conservative). Censored signifie attempt en cours au end-of-data ; sous
FTMO unlimited time il continuerait, mais on doit l'admettre comme "unknown".

| Config | in-sample standard | in-sample strict | **OOF held standard** | **OOF held strict** | OOF censored% |
|---|---:|---:|---:|---:|---:|
| K1 V2+E7 (Lever A seul) | 56.58% | 50.72% | **75.02%** | **65.01%** | 13.3% |
| K2 V2E7 + floor_taper | 68.77% | 60.89% | **90.43%** | **77.08%** | 14.8% |
| **K5 V2E7+floor+vol_high** | 97.40% | 86.28% | **100.00%** | **85.30%** | 14.7% |

**Lecture Check 1 :**
- Standard est optimiste (les censurés finiraient par passer sous FTMO unlimited).
- Strict est pessimiste (censurés = fails).
- **Réalité** entre les deux. Vraisemblablement plus proche de standard
  vu FTMO 2026 unlimited time. **Range honnête : K5 entre 85% (strict) et 100% (std).**

---

## Check 2 — Placebo : floor_taper expose-t-il que l'ORB ne contribute rien ?

### Test 2a : entrées ORB vs random simple vs long-bias

Sous IDENTIQUE floor_proximity_taper (taper_min=0.25) + vol_high sizing,
sur même fenêtre OOF 2014-2026 :

| Config | mean R/day | std R/day | floor OOF | no-floor OOF |
|---|---:|---:|---:|---:|
| **a) K5 ORB (réel)** | +0.022 | 1.08 | **100.00%** | **77.55%** |
| b) Random iid mean V2+E7 | +0.002 | 1.08 | 55.36% | 49.39% |
| c) Long-bias open→close (2bp) | -0.009 | 2.09 | 1.97% | 5.83% |
| d) Long-bias no cost | +0.025 | 2.09 | 21.45% | 15.22% |

**Premier verdict :** l'ORB bat clairement les placebos basiques (+45pp vs
random, +98pp vs long-bias). Mais le random a un sample mean très bas (0.002
vs K5 0.022). **Pas apples-to-apples.**

### Test 2b : placebos plus puissants (K5 distribution preserved)

| Config | mean R/day | std R/day | floor OOF | no-floor OOF |
|---|---:|---:|---:|---:|
| **1. K5 actual** | +0.022 | 1.08 | **100.00%** | 77.55% |
| **2. K5 shuffled** (même dist, ordre random) | +0.022 | 1.08 | **100.00%** | 53.92% |
| **3. Random matched Gaussian** (mean/std identiques) | +0.036 | 1.08 | **79.38%** | 54.46% |
| 4. Random 2× mean | +0.023 | 1.08 | 86.20% | 48.76% |
| 5. Random half mean | +0.005 | 1.08 | 62.01% | 34.17% |
| **6. Random ZERO mean** (sample lucky 0.027) | +0.027 | 1.07 | **97.71%** | 84.42% |

### Insights décisifs Check 2

1. **K5 shuffled = K5 actual sous floor (100% = 100%).**
   → La **séquence temporelle ne contribute RIEN** sous floor_taper.
     Seule la distribution importe.

2. **K5 shuffled no-floor = 53.9% (vs K5 actual no-floor = 77.55%).**
   → Sans floor, la **séquence temporelle MATTER** : le clustering des
     bons jours (régime 2017-2023) ajoute +24 pp vs même distribution
     déstructurée.

3. **Random matched Gaussian (sample mean 0.036 > K5's 0.022) → 79.4% floor OOF.**
   → Random Gaussien avec MEME mean/std ne reproduit pas le 100% K5.
     Gap = +21 pp dû à la **forme distributionnelle ORB** (skew, fat tails).

4. **Random ZERO mean (vrai mean 0, sample chanceux 0.027) → 97.71% floor OOF.**
   → Avec un mean ~0 et de la chance d'échantillonnage, **floor_taper +
     unlimited time = pass quasi-garanti**. C'est la math no-bust ×
     temps illimité.

5. **K5 distribution :** skew +1.78, kurt +11.29 (queue droite extrême).
   Random Gaussien : skew=0, kurt=3. La différence de forme explique le gap.

### Décomposition honnête du 100% K5

| Source | Contribution estimée |
|---|---:|
| Distribution Gaussienne de base avec mean ≈ 0 + floor_taper + unlimited time | ~80% |
| Skew/kurt ORB (queue droite, gros winners) | ~+15 pp |
| (Au-delà du floor) Time clustering du signal ORB | indirectement, absorbé par floor |
| **Total** | **~100%** |

**L'ORB contribute ~+15-21 pp via sa distribution, le reste est math de
no-bust × temps illimité.**

---

## Check 3 — V2+E7 SEUL régime decomposition (le chiffre durable)

V2+E7 = filter rng≥10bps + trail BE@1R. PAS de floor_taper, PAS de vol_high.
C'est l'ORB stratégie nue, sous FTMO 2026.

| Bloc | n_days | n_resolved | n_funded | **p_funded** | strict | censored% |
|---|---:|---:|---:|---:|---:|---:|
| 2010-2012 | 671 | 671 | 10 | **1.49%** | 1.49% | 0% |
| **2013-2015** | 783 | 783 | 0 | **0.00%** | 0.00% | 0% |
| 2016-2018 | 782 | 782 | 643 | 82.23% | 82.23% | 0% |
| 2019-2021 | 784 | 784 | 784 | **100.00%** | 100.00% | 0% |
| 2022-2023 | 520 | 520 | 520 | **100.00%** | 100.00% | 0% |
| 2024-2026 | 630 | 198 | 158 | 79.80% | 25.08% | 68.6% |

**Vol regime tercile (NOWCAST) :**

| Vol regime | n_starts | n_resolved | n_funded | **p_funded** | strict |
|---|---:|---:|---:|---:|---:|
| LOW vol | 1550 | 1414 | 886 | **62.66%** | 57.16% |
| **MID vol (aujourd'hui)** | 1312 | 1161 | 538 | **46.34%** | 41.01% |
| HIGH vol | 1308 | 1163 | 691 | **59.42%** | 52.83% |

### Verdict Check 3

V2+E7 **SEUL est brutalement régime-conditionnel** :
- **2013-2015 : 0% p_funded** sur 783 attempts (mean R négatif, pas d'edge)
- **2016+ : 82-100% p_funded**

Le résultat "100% en 2019-2023" est PORTÉ par le bêta NQ (régime favorable).
Le "0% en 2013-2015" montre que V2+E7 sans floor_taper PEUT mourir
complètement dans certains régimes.

**Aujourd'hui (mid vol) : V2+E7 SEUL = 46.3% (strict 41.0%).** C'est le
chiffre DURABLE de Lever A. Inférieur au 75% OOF held (qui inclut tous
les régimes 2014-2026 dont 2019-2023 à 100%).

---

## Verdict — le chiffre p(pass) déployable honnête

### Trois lectures possibles

| Lecture | Chiffre | Hypothèses |
|---|---:|---|
| **Pessimiste (Lever A seul, régime mid aujourd'hui)** | **46.3%** | Pas de floor_taper, régime mid persiste, pas de bêta favorable |
| **Modérée (V2+E7 + floor_taper K2)** | **77-90%** | Floor implémenté correctement, FTMO unlimited time tient, régime n'est pas catastrophique comme 2013-2015 |
| **Optimiste (K5 complet)** | **85-100%** | Tous les leviers actifs, distribution ORB stable, no-bust math + FTMO unlimited tient |

### Décomposition edge vs path-management

Le DSR per-trade fail (p=0.08, SR=0.014) confirmé : **l'ORB n'a quasi pas
d'edge per-trade**. Le rendement vient de :

1. **Bêta NQ favorable 2017-2026** : régime de hausse + ORB long-biased = mean R + 0.022 (de 2010-2026)
2. **Skew distributif ORB** : queue droite +1.78 → gros winners occasionnels
3. **Floor_taper math** : no-bust + unlimited time = pass eventuel garanti (si mean R ≥ 0)

Le placebo random à mean 0 + sample chanceux donne 97.7% sous floor → le
floor + unlimited time est le levier dominant.

### Risque structurel

Si une de ces 3 conditions casse :
1. **Régime bear durable type 2013-2015** : V2+E7 mean R devient négatif →
   floor_taper grind ÉTERNEL sans atteindre target → fail (ou très long
   à atteindre). K5 sur 2013-2015 = 98.6% en sim, mais sim avait 0
   censored — limite arbitraire des données. Sur 50 ans de bear, attente
   pourrait dépasser patience utilisateur.
2. **FTMO restaure time limit** : tout le mécanisme floor_taper s'effondre
   sous time-cap. K5 chuterait à ~50-70%.
3. **Implementation floor_taper ratée** : sizing fonctionnel uniquement
   si on peut effectivement scaler à 25%. FTMO minimum 0.01 lot ; OK
   en pratique.

### Décision de lancement

**Le 100% K5 est mathématiquement réel sous FTMO 2026 + nq_sim.** Mais
ce N'EST PAS un edge ORB — c'est une exploitation de la règle FTMO
no-time-limit via no-bust path management.

**Pour le lancement :**
1. **Estimation conservatrice honnête : ~75-90%** (V2+E7+floor sans
   vol_high amplification). C'est le chiffre que je RECOMMANDE pour planning.
2. Si FTMO maintient unlimited time pendant la durée du défi : ~95% est
   atteignable (K5 complet).
3. **Si FTMO restaure time-cap pendant le défi : ~46% (Lever A mid vol)**.

**Premier défi à $150-200** : recommandé. Test live des hypothèses ci-dessus.
Si pass → bien. Si fail → comprendre pourquoi (time cap, régime, mécanique).

---

## Distinction nette : ce que c'est et ce que ce n'est pas

### Ce que K5 EST
- Une stratégie de path-management qui exploite la règle FTMO
  unlimited-time avec un signal ORB modestement positif
- Mécaniquement valide sous FTMO 2026 rules confirmées
- Robuste à 13 années OOF (2014-2026) en simulateur

### Ce que K5 N'EST PAS
- Pas un "edge" trading per-trade (DSR per-trade fail, p=0.08)
- Pas un signal robuste à TOUS les régimes (V2+E7 seul = 0% en 2013-2015)
- Pas un "100% p(pass) live" garanti — c'est un 100% simulateur sous des
  hypothèses spécifiques (unlimited time, no consistency rule, floor
  implementable)
- Pas un argument pour deviner que la stratégie est "bonne" — c'est plutôt
  une exploitation intelligente de la règle FTMO 2026

### La métaphore juste
Imaginer une roulette biaisée à 51/49 noir/rouge. Sans limite de temps, en
augmentant les paris quand on monte et réduisant quand on baisse
(floor_taper), on finit TOUJOURS par gagner. Mais ce n'est pas un edge
roulette — c'est de la math + patience + règles permissives.

C'est exactement K5 : l'ORB est la roulette 51/49 (à peine), floor_taper
est la stratégie de paris, FTMO unlimited time est la règle permissive.
Le 100% est valide mais ce n'est pas un edge ORB — c'est l'exploitation
combinée.

---

## Fichiers produits

| Fichier | Rôle |
|---|---|
| `audit/realconstraints_check.py` | Check 1 + Check 2 (placebo basique) + Check 3 |
| `audit/placebo_matched.py` | Check 2 raffiné (shuffled K5 + matched Gaussian) |
| `audit/realconstraints_output.txt` | Output Check 1/2/3 |
| `audit/placebo_matched_output.txt` | Output placebo matched |
| `audit/realconstraints_check1.csv` | K5/K2/V2+E7 sous FTMO real |
| `audit/realconstraints_check2_placebo.csv` | Placebo basique |
| `audit/realconstraints_check3_regime.csv` | V2+E7 seul régime decomp |
| `audit/realconstraints_check3_vol.csv` | V2+E7 seul vol terciles |
| `audit/placebo_matched.csv` | Matched placebo final |
| **`ORB_realconstraints_NQ.md`** | **Ce livrable** |

---

## Sources Check 0 (FTMO rules web search)

- [FTMO Trading Objectives](https://ftmo.com/en/trading-objectives/)
- [FTMO 2-Step Challenge](https://ftmo.com/en/2-step-challenge/)
- [Trade without any time limit (FTMO blog)](https://ftmo.com/en/blog/trade-without-any-time-limit-and-take-as-long-as-you-want-to-pass/)
- [FTMO FAQ Step 1](https://ftmo.com/en/faq/step-1-ftmo-challenge/)
- [FTMO Rules 2026 (third-party)](https://tradetanto.com/learn/ftmo-rules-evaluation-process)

---

*ORB-realconstraints Fil 2 réalisé 2026-06-02 — Claude Code (Opus 4.7 1M ctx).
Verdict honnête : K5 100% OOF est mécaniquement réel sous FTMO 2026
unlimited time + floor_taper. Le placebo confirme : 80% du 100% vient de la
math no-bust + unlimited time, ~15-20 pp viennent de la distribution
skew/fat-tail de l'ORB. Lever A seul en mid-vol aujourd'hui = 46% (le
chiffre régime-conditionnel durable). L'ORB n'a pas d'edge per-trade
(DSR per-trade fail) — la stratégie est une exploitation intelligente
des règles FTMO 2026, pas un edge trading.*
