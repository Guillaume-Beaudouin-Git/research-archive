# RESULTS — deux tests indépendants

**2026-08-02.** Worktree `claude/close-continuation-gold-subwindows`, base `origin/main` @ `2f728b3e`.
Interpréteur **`/usr/bin/python3` explicite** (pandas 2.2.3 / numpy 2.0.2 / statsmodels 0.14.6
vérifiés au lancement — un alias zsh masque `python3` par un binaire sans pandas).
Données lues en **LECTURE SEULE** depuis `<HOME>/Desktop/Algo_claude/data/deep_history_utc/`
(caches gitignorés, absents du worktree). Aucun blob data dans git ; aucun chemin live touché.

**La pré-inscription des deux tests (`PREREGISTRATION.md`) a été écrite et COMMITÉE
(`1f4df6d6`) avant la première lecture de donnée de ce worktree.** Elle contient les
hypothèses, les specs figées et les règles de mort chiffrées. Les verdicts ci-dessous sont
lus dans cette grille, pas construits après coup.

**A et B sont indépendants** : compteurs séparés, verdicts séparés, aucun résultat de l'un
n'est utilisé comme argument dans l'autre.

| | Question | Verdict |
|---|---|---|
| **A** | La pression de clôture des indices US **continue**-t-elle, et est-ce un mécanisme ? | **Mécanisme CONFIRMÉ sur US100 — edge REJECTED (exécution).** Demi-vie ≈ **1 minute** ; il ne reste rien après 2 min de retard. |
| **B** | Où vit l'effet de réouverture de l'or, et que reste-t-il si l'on entre plus tard ? | **RENFORCÉ.** Contrairement à GER40, l'effet **survit** : entrée +10 min ⇒ **93 %** du gross conservé post-2021 (4.04 bps, t 2.85). Il n'est **pas** dans les premières minutes. |

---
---

# TEST A — la CONTINUATION de la pression de clôture sur indices US

## A.0 Ce qui est en jeu

`mr_timezone_repair_2026-08` cherchait un **fade** de la pression de clôture et a trouvé que le
fade **perd** significativement (US100 −3.29 bps t −2.77 ; US500 −1.49 t −2.88 ; US30 −2.18
t −2.36), sur les deux jambes et après retrait de l'inconditionnel. L'agent a refusé de
revendiquer ce signe : il l'avait **trouvé, pas pré-enregistré**. Correct.

Une re-confirmation sur le même échantillon ne vaudrait rien. La preuve est donc allée chercher
la puissance ailleurs, **selon un plan écrit d'avance** : un test de **mécanisme** (gradient,
sans aucun seuil donc sans degré de liberté), un **placebo d'ancre**, un **hors-échantillon
temporel**, et un test d'**exécutabilité**.

**1 059 cellules à seuil + 156 cellules de placebo + 12 régressions de gradient** mesurées
(§A.7). Toutes au **GROSS, `cost_rt = 0`**.

## A.1 Hygiène d'abord (K7, L60) — et elle disqualifie un instrument

Part de barres à fourchette nulle **à la barre d'entrée et à la barre de sortie**, par année :

| instrument | zr entrée (moy / max) | zr **sortie** (moy / max) | fourchette de la barre d'entrée | couverture d=0 |
|---|---|---|---|---|
| US100 | 0.00 % / 0.00 % | 0.00 % / 0.00 % | **7.66 bps** | 0.96 |
| US30 | 0.00 % / 0.00 % | 0.00 % / 0.00 % | 5.24 bps | 0.95 |
| **US500** | 0.09 % / 0.80 % | 2.46 % / **9.64 %** | 5.45 bps | 0.94 |
| GER40 | 0.06 % / 0.39 % | 0.03 % / 0.39 % | 5.59 bps | 1.00 |

**US500 déclenche K7** : la barre de sortie (16:11 ET) est figée sur **6.05 % des séances en
2018** et **9.64 % en 2019** — au-dessus du seuil pré-enregistré de 5 %. Ses cellules 2018-2019
sont donc adossées, une fois sur dix, à un prix qui n'en est pas un. **US500 est disqualifié
comme porteur de preuve** ; il reste rapporté pour cohérence.

Chiffre à retenir avant tout le reste : **la fourchette moyenne de la barre d'entrée post-clôture
sur US100 est de 7.66 bps**, soit **2.7× l'edge total de la fenêtre de 10 minutes**. Le bruit
intra-minute au point d'entrée est plus grand que tout ce qu'il y a à gagner.

## A.2 K1 — LE GRADIENT. Le mécanisme existe, et il est propre.

Pente OLS du rendement post-clôture sur `z`, **sans aucun seuil** (donc aucun degré de liberté
exploitable), HAC(6) :

| instrument | K=15 | K=30 | K=60 |
|---|---|---|---|
| US500 | +1.690 (**t 2.49**) | +1.230 (t 1.72) | +0.657 (t 1.18) |
| **US100** | **+2.083 (t 3.53)** | +1.690 (t 2.35) | +0.999 (t 1.64) |
| US30 | +1.442 (**t 2.44**) | +0.582 (t 0.94) | +0.046 (t 0.09) |
| GER40 | −0.519 (t −1.33) | **−1.361 (t −2.93)** | −0.386 (t −0.91) |

Version **pooled US** et *tradable* (position proportionnelle à `z`, écrêtée à 3 σ ; moyenne
équipondérée des trois instruments par jour, ce qui absorbe la corrélation transverse) :

| K | n jours | moyenne (bps) | t HAC | boot p |
|---|--:|--:|--:|--:|
| **15** | 1 990 | **+1.106** | **2.344** | **0.009** |
| 30 | 1 990 | +0.655 | 1.491 | 0.103 |
| 60 | 1 990 | +0.349 | 0.888 | 0.369 |

**K1 est franchie pour K = 15 et échouée pour K = 30 et K = 60.** Ce n'est pas un hasard de
sélection : la pente **décroît monotonement en K** sur les quatre instruments. C'est exactement
la signature attendue d'une vraie pression de clôture — plus la fenêtre de signal est courte,
plus elle capte de la **pression** et moins de l'**information**. Le mécanisme se comporte comme
un mécanisme.

**K2 — quintiles de z** (rendement post-clôture moyen, bps) :

| instrument (K=15) | Q1 | Q2 | Q3 | Q4 | Q5 | Q5−Q1 | transitions croissantes |
|---|--:|--:|--:|--:|--:|--:|--:|
| US500 | −1.735 | +0.112 | +0.783 | +0.948 | +1.090 | **+2.83** | **4/4** |
| **US100** | −2.276 | −0.422 | +0.587 | +0.989 | +1.237 | **+3.51** | **4/4** |
| US30 | −1.080 | +0.933 | +0.387 | +0.750 | +0.087 | +1.17 | 2/4 ✗ |
| GER40 | +0.959 | −0.790 | +0.042 | −0.096 | −0.743 | −1.70 | 1/4 (réversion) |

US500 et US100 sont **parfaitement monotones**. US30 **déclenche K2**.

## A.3 K4 — le placebo d'ancre. US100 est premier sur 12.

La même forme de trade ancrée toutes les 30 minutes dans la séance, θ = 1.0, les trois K
pré-enregistrés rapportés (aucun choisi après coup) :

| instrument | K | rang de l'ancre de clôture | m clôture | m moyen hors-clôture | p95 hors-clôture |
|---|--:|---|--:|--:|--:|
| **US100** | **15** | **1 / 12** | **+2.70 (t 2.43)** | +0.40 | +1.72 |
| US100 | 30 | 1 / 12 | +2.80 (t 2.45) | +0.52 | +1.47 |
| US100 | 60 | 1 / 12 | +1.54 (t 1.50) | +0.64 | +1.34 |
| US500 | 15 | 1 / 12 | +2.12 (t 2.33) | +0.34 | +1.03 |
| US500 | 30 | 2 / 12 | +1.55 (t 1.57) | +0.36 | +1.61 |
| US30 | 15 | 1 / 12 | +1.91 (t 2.08) | +0.68 | +1.33 |
| US30 | 30 | 10 / 12 | −0.23 (t −0.30) | +0.60 | +1.61 |
| GER40 | 30 | **16 / 16** (dernier) | −1.86 (t −2.89) | −0.11 | +0.73 |

Contrôle de « momentum générique » — PnL quotidien **poolé de toutes les ancres hors clôture** :

| instrument | K=15 | K=30 | K=60 |
|---|---|---|---|
| US500 | +0.152 (t 0.60) | +0.016 (t 0.07) | −0.020 (t −0.09) |
| US100 | +0.206 (t 0.73) | +0.164 (t 0.57) | −0.456 (t −1.54) |
| **US30** | **+0.708 (t 2.90)** ✗ | +0.359 (t 1.68) | −0.425 (t −1.85) |
| GER40 | −0.156 (t −1.16) | −0.211 (t −1.60) | −0.606 (t −4.67) |

⇒ Sur **US500 et US100 il n'y a AUCUN momentum intraday générique** (t 0.60 / 0.73) : l'ancre de
clôture est spécifique, et elle est **première sur douze**. Sur **US30** les ancres ordinaires
portent elles-mêmes un momentum significatif (t 2.90) — **K4 clause 2 déclenchée, US30 tombe**.

Noter le miroir GER40 : dernier sur seize, et le seul instrument où la clôture **inverse**. Le
signe n'est donc pas une propriété universelle des indices ; c'est une propriété du marché.

## A.4 K6 — hors-échantillon 2018-2021 / 2022-2026

θ = 1.0, entrée immédiate, sortie clôture+11 :

| instrument | K | 2018-2021 | 2022-2026 | verdict |
|---|--:|---|---|---|
| **US100** | **15** | +2.57 (t 1.43) | **+2.99 (t 2.10)** | **PASSE** (même signe, seconde moitié t ≥ 1.5) |
| US100 | 30 | +3.87 (t 1.78) | +2.40 (t 1.89) | passe |
| US500 | 15 | +3.57 (t 2.18) | +1.31 (t 1.22) | ✗ K6 |
| US30 | 15 | +4.24 (t 2.35) | +0.77 (t 0.81) | ✗ K6 |
| GER40 | 30 | −2.19 (t −2.66) | −1.38 (t −1.34) | (réversion, décroissante) |

**US100 est le seul instrument dont l'effet est aussi fort — plus fort — dans la seconde
moitié.** US500 et US30 décroissent d'environ 70 %.

**K5 (L58)** est franchie partout où elle est évaluable : US100 K=15 θ=1.0 → excès jambe longue
**+3.150 (p 0.029)**, excès jambe courte **+2.483 (p 0.112)** contre un inconditionnel de
**+0.023 bps (t 0.06)** — la baseline est nulle, donc L58 ne mord pas ici. US500 : +2.124
(p 0.070) / +2.137 (p 0.061) contre un inconditionnel de +0.239.

## A.5 K3 — L'EXÉCUTION. C'est ici que tout meurt.

Two-sided, θ = 1.0, entrée retardée de *d* minutes, sortie maintenue à clôture+11 :

| instrument | K | d=0 | d=1 | d=2 | d=3 | d=5 |
|---|--:|--:|--:|--:|--:|--:|
| **US100** | 15 | **2.83** (t 2.53) | 1.96 (t 1.88) | 0.59 (t 0.62) | 0.17 (t 0.19) | 0.85 (t 1.31) |
| US100 | 30 | 2.98 (t 2.57) | 1.33 (t 1.43) | 0.35 (t 0.39) | −0.04 | 0.68 (t 1.07) |
| US500 | 15 | 2.15 (t 2.33) | 1.33 (t 1.51) | 0.32 (t 0.46) | 0.46 | 0.69 (t 1.13) |
| US30 | 15 | 2.08 (t 2.24) | 1.03 (t 1.46) | 0.74 (t 1.10) | 0.69 | 0.48 (t 0.88) |

Part du gross conservée : **US100 69 % à 1 min, 21 % à 2 min, 6 % à 3 min.**
US500 62 % / 15 %. US30 50 % / 35 %.

**Le seuil pré-enregistré K3 est `≥ 2.7 bps ET t ≥ 1.5` à d = 5.** Aucun instrument n'y arrive.
**Aucun n'y arrive même à d = 1.** La demi-vie de la continuation est d'environ **une minute**.

**Économie, au coût mesuré de 1.8 bps RT (jamais la colonne `spread`) :**

| instrument (K=15, θ=1.0) | trades/an | gross bps | net bps | **net bps/an** |
|---|--:|--:|--:|--:|
| US100 · d=0 | 44.3 | 2.83 | +1.03 | **+45.6** |
| US100 · d=1 | 44.4 | 1.96 | +0.16 | **+7.2** |
| US100 · d=2 | 44.4 | 0.59 | −1.21 | −53.6 |
| US500 · d=0 | 43.9 | 2.15 | +0.35 | +15.3 |
| US30 · d=0 | 44.8 | 2.08 | +0.28 | +12.7 |

Le **plafond absolu** — fill parfait à l'ouverture de la première barre post-clôture, coût de
séance appliqué à une fenêtre qui n'est pas une séance — vaut **0.46 %/an de notionnel** sur
US100. Une minute de retard le ramène à **0.07 %/an**. Et le coût de 1.8 bps est presque
certainement **sous-estimé** ici : la fourchette moyenne de la barre d'entrée est de 7.66 bps
(§A.1), la fenêtre post-clôture est mince, et `COST_AUDIT §7` avertit précisément qu'une médiane
journalière n'est pas le dénominateur d'une famille qui trade à une heure fixe.

## A.6 Verdict A

| règle | US100 | US500 | US30 |
|---|---|---|---|
| K7 hygiène L60 | ✓ | ✗ (9.64 % en 2019) | ✓ |
| K1 gradient (K=15) | ✓ t 3.53 | ✓ t 2.49 | ✓ t 2.44 |
| K2 monotonicité | ✓ 4/4 | ✓ 4/4 | ✗ 2/4 |
| K4 placebo d'ancre | ✓ 1/12, pas de momentum générique | ✓ 1/12 | ✗ momentum générique t 2.90 |
| K5 L58 | ✓ | ✓ | ✓ |
| K6 hors-échantillon | ✓ t 2.10 en 2022-26 | ✗ | ✗ |
| **K3 exécutabilité** | **✗** | **✗** | **✗** |

> **VERDICT : le MÉCANISME est CONFIRMÉ sur US100 — l'EDGE est REJECTED.**

Le mécanisme n'est pas un artefact : la continuation est **graduée dans l'intensité** de la
pression (pente t 3.53, sans seuil), **monotone en quintiles** (4/4), **première sur 12 ancres**
alors que les ancres ordinaires ne portent aucun momentum (t 0.73), **stable hors échantillon**
(t 2.10 sur 2022-2026), et **d'ampleur décroissante en K** comme doit l'être une pression de
clôture. C'est un vrai fait de marché, et il valide *a posteriori* le signe que
`mr_timezone_repair` avait refusé de revendiquer.

Il n'est simplement **pas prenable**. Il vaut au mieux **0.46 %/an brut de tout frottement
réaliste**, sa demi-vie est d'**une minute**, et le bruit de la barre où il faudrait entrer
(7.66 bps) vaut **2.7×** l'effet entier.

**Nature du kill : EXÉCUTION** — donc, au registre de la politique de ré-ouverture, rouvrable
**seulement** sur véhicule. Mais la ré-ouverture n'a aucun intérêt : même un fill parfait à coût
nul plafonne à ~1.25 bps/jour de trade sur 44 trades/an. **Cette famille est close en pratique**,
et cette fois elle l'est **avec** sa pré-inscription, ce qui rend le résultat citable.

## A.7 Ce que le TEST A ne prouve PAS

1. **Il ne prouve pas que la continuation existe sur tous les indices US.** Elle est confirmée
   sur **US100 seul**. US30 échoue le mécanisme (K2 et K4), US500 est disqualifié à l'hygiène
   (K7) et échoue le hors-échantillon. Trois instruments ne font pas une classe d'actifs.
2. **Il ne lave pas le péché originel.** Le signe a été **découvert** sur 2018-2026 US ; ma
   pré-inscription est postérieure à cette découverte. Elle déplace la charge de la preuve
   (gradient sans seuil, placebo, hors-échantillon) mais elle **ne peut pas** rendre
   l'échantillon vierge. Le seul test vraiment propre serait un **nouvel** échantillon —
   d'autres marchés, ou l'avenir.
3. **Il ne mesure pas le vrai coût post-clôture.** Les 1.8 bps sont une médiane de séance.
   La fenêtre testée n'est pas une séance. Le net rapporté est donc **optimiste**, ce qui
   **renforce** le verdict négatif (L36/L43 : un kill obtenu malgré une hypothèse de coût
   favorable est robuste).
4. **Il ne teste pas les actions individuelles**, qui sont l'univers du mécanisme publié
   (Baltussen-Da-Soebhag, long-short en coupe transverse). L'a priori « au niveau indice
   l'idiosyncratique se compense » reste **confirmé, pas contredit**.
5. **Il ne rapporte aucun p(pass).** Avec 45 bps/an au plafond, une simulation de barrière
   n'apporterait rien. **Aucun Δp(pass) n'est revendiqué, donc le placebo à autocorrélation
   appariée n'est pas déclenché** (§Contrainte, plus bas).
6. **La tenue de 10 minutes est imposée par la donnée**, pas choisie : la couverture des barres
   post-clôture chute de 0.96 à +10 min à 0.56 à +15 min. On ne sait pas ce que ferait une
   tenue plus longue, et on ne peut pas le savoir sur ce véhicule.

---
---

# TEST B — sous-fenêtres de l'heure de réouverture de l'or

## B.0 Ce qui est en jeu

Le candidat **E002** est **UNDERPOWERED, famille ouverte** : p(pass) 0.593, IC90
**[0.321 ; 0.817]**, DSR post-2021 **0.284**, coût = **49 %** du signal. Sur GER40, la même
décomposition venait de tuer un candidat qui semblait bien plus solide (gross +3.52 bps t 3.68,
12/13 ans positifs, 1ᵉʳ sur 29 au placebo) parce que **60 % de l'effet vivait dans l'auction**
et qu'un retard de 5 minutes ne laissait que 0.56 bps.

**Séries reconstruites depuis le M1 BRUT.** La winsorisation 0.5/99.5 de
`overnight_futures_2026-07/code/step3_performance.py:47` est appliquée **dans le constructeur** ;
tous ses consommateurs ont des queues tronquées. Elle n'est utilisée nulle part ici, sauf pour
chiffrer ce qu'elle cachait (§B.6).

## B.1 D'abord, un défaut d'horloge dans le véhicule lui-même (L52)

Avant toute mesure de performance : **à quelle heure ce véhicule cote-t-il réellement après la
pause de règlement ?** Minutes écoulées entre 18:00 ET nominal et le **premier print**, par année :

| ère | médiane du 1ᵉʳ print | % à ≤ 1 min | % à ≥ 5 min | durée de la coupure | heure de pause cotée |
|---|--:|--:|--:|--:|--:|
| 2007-2012 | **0 min** | 84-100 % | ~0 % | 1-2 min | **100 %** (aucune pause) |
| 2013-2017 | **0 min** | 91-100 % | ~1 % | 60-61 min | 0 % |
| 2018-2020 | **5 min** | 6-8 % | **91-94 %** | 65 min | 0 % |
| 2021 | 0 min | 62 % | 38 % | 66 min | 0 % |
| **2022-2026** | **5 min** | **0 %** | **100 %** | **76 min** | 0 % |

**La réouverture Globex nominale de 18:00 ET n'est PAS le moment où ce véhicule recommence à
coter.** Dans l'ère moderne — qui **est** l'échantillon décisionnel de E002 — le premier prix
disponible est à **18:05 ET**, jamais avant, et la période sans cotation est passée de 60 à
**76 minutes** (elle commence désormais vers 16:49 ET).

Conséquence méthodologique décisive : **une échelle de retards ancrée sur l'horloge murale
compare des conventions d'entrée différentes selon l'époque.** Les retards d = 0…5 min seraient
**identiques** après 2022 (tous résolus sur le print de 18:05), et le test d'exécutabilité
mesurerait zéro. Toute la décomposition est donc ancrée sur **`t0` = premier print exécutable**,
la version horloge murale étant conservée pour traçabilité avec la pré-inscription (§B.4).

C'est une instance directe de **L52** (« ne jamais faire confiance au nom d'un champ… une
décomposition n'est pas définie sans dire de quel jour/quelle horloge on parle »), appliquée
cette fois non à un champ de provider mais à **l'heure de réouverture supposée d'un véhicule**.

## B.2 Hygiène (KB4, L60) et ancrage d'horloge (KB6)

**Barres à fourchette nulle dans les 5 premières minutes à partir de `t0`** : maximum **4.05 %**
(2014) sur toute l'histoire, **≤ 0.75 %** sur tout post-2021, **0.11 %** en 2024-2025. Les seuils
pré-enregistrés (10 % / 25 %) ne sont approchés nulle part. **KB4 non déclenchée.** Aucun
syndrome XPT/XPD (L60) : ce sont de vrais prix.

**KB6 — falsification d'horloge au niveau MINUTE.** Corrélation du profil minute hiver~été :

| ancrage | corr |
|---|--:|
| **horloge d'échange (ET, avec DST)** | **+0.519** |
| 23:00 UTC fixe | **−0.169** |

L'ancrage ET domine sans ambiguïté (et le contrôle horaire indépendant de `prep_cache.py` donne
**0.963 en ET contre 0.591 en UTC** sur XAUUSD). **KB6 non déclenchée.** Réserve honnête : 0.519
en valeur absolue est **modeste** — un profil minute est bruyant. Ce n'est pas un problème : le
résultat central de §B.3 est précisément qu'il **n'y a pas** de structure minute nette à
localiser.

## B.3 Question 1 — OÙ est l'effet ? Pas dans les premières minutes.

Profil **cumulé** depuis `t0`, brut, en bps :

| minute après `t0` | full (N≈4 211) | t | **post-2021 (N≈1 009)** | **t** |
|--:|--:|--:|--:|--:|
| 1 | +0.60 | 7.64 | +0.20 | 1.71 |
| 2 | +0.82 | 8.14 | +0.22 | 1.58 |
| 5 | +1.11 | 7.88 | **+0.06** | **0.30** |
| 10 | +1.40 | 8.24 | +0.32 | 1.35 |
| 15 | +1.70 | 9.01 | +0.41 | 1.40 |
| 30 | +1.80 | 8.40 | +0.79 | 2.42 |
| 60 | +1.96 | 5.42 | +0.99 | 2.12 |

**Part de la fenêtre de 8 h portée par la première heure :**

| échantillon | N | 1ʳᵉ heure | fenêtre 8 h | **part 1ʳᵉ h** | 5 premières min | **part 5 min** |
|---|--:|--:|--:|--:|--:|--:|
| full | 4 259 | 1.96 | 4.93 | **39.7 %** | 1.11 | 22.6 % |
| pré-2018 | 2 490 | 2.23 | 6.35 | 35.1 % | 1.63 | 25.7 % |
| **post-2021** | 1 010 | 0.99 | 4.35 | **22.7 %** | **+0.06** | **1.4 %** |

**Décomposition par segments, post-2021 :**

| segment | bps | t |
|---|--:|--:|
| `t0` → `t0`+5 min | **+0.06** | 0.30 |
| `t0`+5 → `t0`+15 min | +0.35 | 1.72 |
| `t0`+15 → `t0`+30 min | +0.39 | 1.69 |
| `t0`+30 → `t0`+60 min | +0.20 | 0.59 |
| **`t0`+60 min → fin de fenêtre (7 h)** | **+3.36** | **2.35** |
| **GAP (période sans cotation, NON tradable)** | **+2.46** | **3.50** |

⇒ **Réponse : l'effet est ÉTALÉ, pas concentré.** Dans l'échantillon décisionnel, **77 % du
rendement tradable est au-delà de la première heure**, et les cinq premières minutes valent
**+0.06 bps, t 0.30 — rigoureusement rien**.

**Cela nuance la lecture héritée de L56.** « Le drift or tient entièrement dans la première heure
après la réouverture » est vrai comme énoncé **relatif** sur l'échantillon complet (39.7 % de la
fenêtre dans 1 h sur 8, soit **3.2× la part uniforme**) — mais ce n'est **pas** « entièrement »,
et la concentration **tombe de moitié** dans l'échantillon décisionnel (22.7 %, soit 1.8×
l'uniforme). La localisation n'est donc pas ce qu'on croyait, et c'est **une bonne nouvelle pour
l'exécutabilité** : un effet étalé sur sept heures est infiniment plus prenable qu'un effet logé
dans cinq minutes d'auction.

## B.4 Question 2 — LE TEST DÉCISIF. L'effet survit au retard.

Entrée à `t0 + d`, sortie à la fin de fenêtre, **brut**, HAC(6) :

| d (min) | full | t | **post-2021** | **t** | pré-2018 | t |
|--:|--:|--:|--:|--:|--:|--:|
| 0 | 4.93 | 7.07 | **4.35** | **2.96** | 6.35 | 7.15 |
| 1 | 4.33 | 6.54 | 4.16 | 2.84 | 5.50 | 6.20 |
| 2 | 4.11 | 6.25 | 4.13 | 2.81 | 5.18 | 5.92 |
| 3 | 4.01 | 6.12 | 4.16 | 2.86 | 4.98 | 5.70 |
| **5** | **3.83** | **5.84** | **4.30** | **2.94** | 4.69 | 5.39 |
| **10** | **3.54** | **5.49** | **4.04** | **2.85** | 4.43 | 5.13 |
| 15 | 3.24 | 5.08 | **3.95** | **2.80** | 4.07 | 4.78 |
| 20 | 3.12 | 4.92 | 3.74 | 2.64 | 3.94 | 4.66 |
| 30 | 3.14 | 4.98 | 3.56 | 2.54 | 4.13 | 4.95 |

À durée constante (sortie décalée du même *d*, L59 sur la sortie aussi) : **inchangé**
(post-2021 : 4.30 à d=5, 3.99 à d=10, 4.01 à d=15). En horloge murale 18:00 ET :
**inchangé** (post-2021 : 4.45 à d=5, 4.34 à d=10). **Les trois conventions concordent.**

> **KB1 (mort si < 2.76 bps ou t < 1.5 à d=5, post-2021) : 4.30 bps, t 2.94 → PASSE.**
> **KB2 (idem à d=10) : 4.04 bps, t 2.85 → PASSE.**
> Part conservée post-2021 : **99 % à 5 min, 93 % à 10 min, 91 % à 15 min.**

**C'est l'inverse exact de GER40** (0.56 bps, t 1.00, 16 % conservés à 5 min). Sur le full
sample la décroissance existe (78 % à 5 min, 72 % à 10 min) mais elle est **entièrement portée
par l'ère pré-2018**, la seule où les premières minutes étaient cotées : 6.35 → 4.69 à d=5
(−26 %). **La prime des premières minutes a existé, et elle a disparu** — ce qui rend le candidat
moderne plus robuste, pas moins.

**Stabilité annuelle, entrée retardée de 10 minutes** : **18 années positives sur 20**, dont
**6/6 depuis 2021** (seules 2018 et 2019 sont négatives — l'ère creuse déjà connue).

## B.5 Question 3 — la part de GAP non tradable, et elle a DOUBLÉ

| échantillon | N | gap (bps) | t | fenêtre capturable | fenêtre gap inclus | **part du gap** |
|---|--:|--:|--:|--:|--:|--:|
| full | 4 259 | 1.02 | 1.68 | 4.93 | 5.95 | **17.2 %** |
| pré-2021 | 3 249 | 0.57 | 0.75 | 5.10 | 5.68 | 10.1 % |
| **post-2021** | **1 010** | **2.46** | **3.50** | **4.35** | **6.81** | **36.1 %** |
| hiver | 1 489 | 1.25 | 1.36 | 7.56 | 8.80 | 14.2 % |
| été | 2 770 | 0.90 | 1.18 | 3.51 | 4.41 | 20.4 % |
| réouverture du dimanche | 394 | 2.67 | 0.96 | 9.02 | 11.69 | 22.9 % |

Le **17.2 %** full-sample **reproduit indépendamment** le 17.5 % archivé en H1 — bon contrôle de
cohérence. Mais le chiffre décisionnel est **36.1 %**, avec un gap **significatif** (t 3.50) : la
période sans cotation s'est allongée à 76 minutes et le prix y bouge désormais nettement.

KB3 (mort si > 40 %) **n'est pas déclenchée**, mais de peu, et la tendance est mauvaise. Deux
conséquences fermes :
- **Tout chiffre H1 de ce dossier surestime le tradable d'environ un tiers post-2021.** Les
  mesures de ce rapport partent toutes de `t0` et sont **gap-free par construction**.
- L'argent reste condamné par cette voie : **58.3 % de gap** (full) / **57.8 %** (post-2021), et
  il ne survit pas au retard (d=5 : 1.30 bps, t 0.99). WTI : 34.6 % de gap (reproduit le 35.5 %
  archivé).

## B.6 Ce que la winsorisation héritée cachait — et le point de barrière

Sur le rendement de fenêtre, l'effet est cosmétique : moyenne 4.926 → 4.887 bps (**−0.8 %**).
**Sur la queue, il ne l'est pas** : pire séance **−515 → −162 bps**.

Et sur la quantité qui décide réellement — l'**excursion adverse intra-fenêtre**, celle qu'une
barrière journalière FTMO à −5 % sur l'**équity** intègre — la troncature est massive :

| échantillon | pire excursion **BRUTE** | winsorisée | kurtosis brut → winsorisé |
|---|--:|--:|---|
| full, d=0 | **−863.8 bps** | −222.0 bps | **77.2 → 9.9** |
| post-2021, d=0 | **−863.8 bps** | −227.4 bps | **105.7 → 8.8** |
| post-2021, d=15 | −654.6 bps | −249.2 bps | 58.2 → 11.2 |

Le **skew de séance brut post-2021 est de −0.87 à −1.07** (positif après winsorisation). Toute
lecture « ce sleeve a un skew positif » reste un artefact de clip, comme
`overnight_sleeve_reopen` l'avait déjà signalé — et c'est **pire** sur l'excursion que sur la
clôture.

**Le retard d'entrée n'achète PAS de soulagement de queue.** Excursion adverse moyenne :
**−33.9 bps à d=0 comme à d=30** (post-2021), p05 ≈ −97 bps, p01 ≈ −195 bps, plate en *d*. Part
des séances dont la seule excursion intra-fenêtre franchirait −5 % : **32.3 % à vm 14, 19.6 % à
vm 10, 4.4 % à vm 5, 0.5 % à vm 2** — et ces parts sont, elles aussi, **insensibles au retard**.

⇒ **Le retard préserve le numérateur et devrait réduire le coût ; il ne fait rien pour le
risque de barrière.** À dire explicitement à quiconque reprendra ce dossier : le gain est sur
l'espérance, pas sur la survie.

## B.7 Économie — et pourquoi le retard est un gain NET

Post-2021, gross gap-free, contre les deux bornes de la fourchette de coût non résolue :

| d | gross | **net @ 1.84** | SR net | **net @ 3.88** | SR net | coût en % du signal @1.84 |
|--:|--:|--:|--:|--:|--:|--:|
| 0 | 4.35 | **+2.51** | 0.70 | +0.47 | 0.13 | 42 % |
| 5 | 4.30 | **+2.46** | 0.69 | +0.42 | 0.12 | 43 % |
| 10 | 4.04 | **+2.20** | 0.62 | +0.16 | 0.05 | 46 % |
| 15 | 3.95 | **+2.11** | 0.60 | +0.07 | 0.02 | 47 % |
| 30 | 3.56 | +1.72 | 0.49 | −0.32 | −0.09 | 52 % |

**La fourchette de coût décide toujours** — exactement la conclusion de
`overnight_sleeve_reopen`, que ce test ne résout pas et ne prétend pas résoudre. Mais il change
la **structure** du problème :

Le motif de la fourchette [1.84 ; 3.88] est que 1.84 bps est un spread médian **toutes heures
confondues**, alors que la sleeve entrait **au premier print après une coupure de 76 minutes** —
le pire moment de la journée pour une fourchette. **Entrer 10 à 15 minutes plus tard coûte 7-9 %
du gross et sort de ce point précis.** Si le spread à `t0`+15 est seulement modérément meilleur
qu'à `t0`, la variante retardée **domine** la variante immédiate en net. C'est un choix
strictement disponible, à zéro coût de recherche.

**Deuxième gain, sur le portage.** La réouverture nominale tombe à **00:00 Prague toute
l'année** (23:00 UTC l'hiver, 22:00 UTC l'été — les deux horloges suivent leur propre DST ;
alignement mesuré à 93.2 % dans `overnight_sleeve_reopen`). Le premier print exécutable moderne
est à **00:05 Prague** et une entrée retardée de 10-15 min tombe à **00:15-00:20 Prague**, pour
une sortie vers 08:00-08:20 Prague. La position **ne traverse aucun rollover** ⇒ **aucune nuit de
swap**, et le retard **éloigne** l'entrée du tampon de rollover au lieu de l'en rapprocher. Le
swap or FTMO étant **asymétrique** (−2.065 bps long / −0.335 short, mesuré 2020+), une seule nuit
facturée par erreur coûterait **47 % du gross** : ce n'est pas un détail, et le retard sécurise
cette marge. ⚠ **À vérifier sur le compte réel** — l'heure exacte du tampon de swap FTMO n'est
pas mesurable depuis des données de prix.

## B.8 Verdict B

| contrôle | résultat |
|---|---|
| **KB1** — d = 5 min, post-2021 (mort si < 2.76 bps ou t < 1.5) | **4.30 bps, t 2.94 → PASSE** |
| **KB2** — d = 10 min (mort si < 2.76 bps) | **4.04 bps, t 2.85 → PASSE** |
| **KB3** — part de gap (mort si > 40 %) | 36.1 % post-2021 — **non déclenchée, mais en hausse** (17.2 % full) |
| **KB4** — L60 dans la zone d'entrée | ≤ 0.75 % post-2021 → **non déclenchée** |
| **KB5** — concentration | mean 4.35 → **4.16 au trim symétrique 5 %**, 4.58 winsorisé, WR 55.1 % → **non portée par la queue** (§ réserve) |
| **KB6** — ancrage d'horloge | ET 0.519 vs UTC −0.169 (et 0.963 vs 0.591 en horaire) → **non déclenchée** |
| **VERDICT** | **RENFORCÉ — reste UNDERPOWERED, famille OUVERTE** |

**Le candidat E002 ne s'effondre pas comme GER40 : il en sort meilleur qu'il n'y est entré.**
Les deux hypothèses qui pouvaient le tuer sont réfutées — l'effet **n'est pas** dans les
premières minutes (1.4 % du total post-2021), et il **survit** à un retard d'entrée qui, lui,
attaque directement la seule vraie inconnue du dossier (le spread à la réouverture).

Il reste **UNDERPOWERED**, et pour les mêmes raisons qu'avant : DSR post-2021 0.284, t net entre
1.4 et 1.9, coût = 42-47 % du signal, et une fourchette de coût **toujours non résolue**. Rien
ici ne franchit un seuil de PASS. **Le budget d'essais n'est pas consommé.**

**Sur KB5, réserve méthodologique explicite :** le test pré-enregistré « retirer les 5 %
meilleures séances » rend la moyenne négative (−1.60). Ce test est **inadapté à cette forme de
distribution** : une sleeve directionnelle à moyenne 4.3 bps et écart-type 46 bps, symétrique
et à 55 % de séances gagnantes, voit *toujours* sa moyenne s'effondrer si l'on ampute une seule
queue. L'analogue correct est un **trim symétrique** — 4.16 bps à 5 % de chaque côté, soit
**96 % de la moyenne brute** — et une winsorisation à 0.5/99.5 qui laisse **4.58**. La moyenne
n'est **pas** portée par une poignée de séances. (Le test de GER40 mordait légitimement parce
qu'il portait sur un sous-échantillon **sélectionné par un signal**, pas sur une sleeve
inconditionnelle.) Je rapporte le résultat pré-enregistré **et** sa correction ; la
pré-inscription faisait de KB5 un indicateur non éliminatoire seul, ce qui reste le cas.

## B.9 Ce que le TEST B ne prouve PAS

1. **Il ne résout PAS la question du coût, qui reste la seule qui décide.** À 1.84 bps la sleeve
   retardée vaut SR net ~0.60 ; à 3.88 bps elle vaut ~0.02. Ce test **déplace** la mesure
   manquante (« spread à `t0` ») vers une mesure plus facile et plus favorable (« spread à
   `t0`+15 »), il ne la remplace pas. **La recommandation n°1 de `overnight_sleeve_reopen`
   reste la recommandation n°1**, désormais applicable à un instant plus liquide.
2. **Il ne mesure aucun spread.** Aucune fourchette n'est mesurée ici : la colonne `spread` de
   `deep_history_utc` est inutilisable seule (sous-estime le RT FTMO réel d'environ 2.4×), et
   les prix M1 ne portent pas de bid/ask. L'argument « entrer plus tard réduit le coût » est un
   argument de **microstructure**, plausible et non mesuré. Il doit être vérifié sur le flux
   broker avant d'être compté.
3. **Il ne prouve pas que la sleeve retardée est meilleure en net.** Elle est meilleure **si**
   le spread décroît de plus de 7-9 % entre `t0` et `t0`+15. C'est vraisemblable ; ce n'est pas
   établi.
4. **Il n'améliore en rien le risque de barrière** (§B.6) : l'excursion adverse est plate en *d*.
   Or 80.2 % des morts de ce livre sont des franchissements de la barrière journalière. Le gain
   est sur l'espérance, **pas** sur la survie.
5. **Il ne rapporte aucun p(pass) ni Δp(pass)** — voir §Contrainte. Le verdict porte sur le
   **GROSS**, donc il est immunisé contre le piège de la persistance.
6. **Il n'explique pas la baisse du gap ni le déplacement de l'effet.** Que la prime des
   premières minutes ait disparu entre l'ère pré-2018 et l'ère moderne est **observé, pas
   expliqué** — et c'est partiellement confondu avec le fait que ces minutes ne sont plus
   cotées. Je ne peux pas distinguer « l'effet a migré » de « le véhicule ne le cote plus ».
7. **Il ne dit rien de l'admission au livre.** Corrélation au book FTMO déployé non mesurée
   (`Portfolio/admission/` non lancé — hors mandat, et de toute façon soumis à la contrainte
   de placebo ci-dessous).
8. **Sur l'échantillon** : 4 259 séances à fenêtre complète contre 4 901 dans l'étude source.
   L'écart vient de tolérances de lookup plus strictes (`p_end` ≤ 30 min, `t0` ≤ 60 min) et de
   l'exigence d'un `p_pre` pour le calcul du gap. Les niveaux ne sont donc **pas** directement
   comparables au chiffre archivé (post-2021 4.35 bps sur N=1 010 ici, 3.79 bps sur N=1 311
   là-bas) ; ce qui est comparable, et qui porte la conclusion, ce sont les **rapports internes
   au même échantillon** (part conservée par retard, part de gap, part de la première heure).

---
---

# Contrainte reçue en cours de travail — Δp(pass) et placebo à autocorrélation appariée

Consigne reçue le 2026-08-02 : un contrôle nul de moyenne strictement nulle mais à persistance
10 jours achète **Δp = +0.1495** ; `corr(autocorrélation, Δp) = +0.511` sur le panel ; 8 finalistes
sur 12 tombent sous leur propre placebo à **décalage circulaire**.

**Application ici : aucun des deux tests ne rapporte de p(pass) ni de Δp(pass), donc l'exigence
n'est déclenchée nulle part.**
- **A** conclut REJECTED sur l'exécution, avec un plafond de 45 bps/an : une simulation de
  barrière n'aurait rien à décider.
- **B** conclut sur le **GROSS**, gap exclu, ce qui est précisément le registre immunisé contre
  ce piège.

**Consigne enregistrée comme pré-condition pour la suite** : tout Δp(pass) futur sur la variante
or retardée devra être accompagné de sa distribution placebo à **décalage circulaire** (médiane
et max), et ne pourra être revendiqué qu'au-dessus d'elle.

**Les deux autres éléments transmis sont directement corroborés par ce travail :**
- **Winsorisation.** Reconstruction depuis le M1 brut faite intégralement. Sur l'or, la
  troncature est cosmétique pour la moyenne (−0.8 %) et **massive sur la queue de l'excursion** :
  pire excursion **−863.8 → −222.0 bps**, kurtosis **77.2 → 9.9** (105.7 → 8.8 post-2021), skew
  de séance brut **−0.87 à −1.07** contre positif après clip (§B.6). C'est exactement le canal
  par lequel un Δp(pass) est surestimé, et c'est cohérent avec le +2.8 pt / +50 % rapporté.
- **80.2 % des morts = barrière journalière.** Mesuré ici pour la variante retardée (§B.6) :
  l'excursion adverse intra-fenêtre est **plate en retard d'entrée** (−33.9 bps de moyenne à
  d=0 comme à d=30 ; 32.3 % des séances franchiraient −5 % à vm 14 sur la seule excursion). **Le
  retard d'entrée n'achète aucune protection de barrière.** À intégrer avant toute décision de
  sizing.

---

# Comptabilité des essais

Compteurs **N1 locaux et SÉPARÉS**, comme pré-enregistré. Aucun n'est fusionné au ledger global
(321, figé) : réconciliation à la clôture de programme.

**TEST A — N1_A**

| bloc | cellules |
|---|--:|
| Cellules à seuil (4 instr × 3 K × 3 θ × 5 retards × 2 conventions de sortie × 3 périodes, moins N<25/jambe) | **1 059** |
| Placebo d'ancre (4 instr × 3 K × 12-16 ancres) | **156** |
| Gradient (12 régressions) + quintiles (12) + poolé (3) | 27 |
| Décomposition minute (60) + économie (36) | 96 |
| **TOTAL A mesuré** | **1 338** |

Réserve de comptage honnête : ces 1 338 cellules ne sont **pas** 1 338 hypothèses indépendantes.
La grille est un **balayage de robustesse** autour d'une seule forme de trade pré-enregistrée ;
le test qui porte la décision (K3) est **un** test à seuil fixé d'avance. Un Šidák à 5 % sur
1 338 cellules exigerait p < 3.8 × 10⁻⁵, que rien n'approche — mais ce n'est pas ce comptage-là
qui tue le candidat : c'est K3, et K3 est binaire.

**TEST B — N1_B**

| bloc | cellules |
|---|--:|
| Échelle de retard (9 retards × 3 conventions × 3 échantillons) — **une seule famille** pré-enregistrée | **81** |
| Profil cumulé (11 minutes × 2 échantillons) | 22 |
| Décomposition de gap (7 échantillons) + segments (6) | 13 |
| Robustesse (8) + économie (36) + année par année (20) | 64 |
| Contrôles argent / WTI | 4 |
| Excursion intra-fenêtre (10) + barrière (10) | 20 |
| **TOTAL B mesuré** | **204** |

Diagnostics **N0**, non comptés (ils ne mesurent aucune performance) : L60 par série et par
année, part de spread nul, profils horaires L56, horloge de réouverture du véhicule (§B.1),
couverture des barres post-clôture, audit de winsorisation.

---

# Reproduire

```
SC=<scratchpad>/cache
/usr/bin/python3 code/prep_cache.py         $SC   # cache M1 brut + L60 + L56   (~12 min)
/usr/bin/python3 code/test_a_continuation.py $SC  # TEST A, 1 338 cellules      (~4 min)
/usr/bin/python3 code/test_b_subwindows.py   $SC  # TEST B, décomposition       (~5 min)
/usr/bin/python3 code/test_b_extra.py        $SC  # TEST B, robustesse + économie
/usr/bin/python3 code/test_b_excursion.py    $SC  # TEST B, excursion intra-fenêtre
```

Caches et tables de cellules écrits **hors du repo** (scratchpad) : **aucun blob data n'entre
dans git**. Sources M1 lues en **lecture seule** dans le répertoire principal. Aucun chemin live
touché (`ftmo_live/`, `strategies/`, `Futures/live/`, `Portfolio/`, `.github/`, `*.mq5`).

---

# Corrections appelées ailleurs dans le repo

1. **`overnight_futures_2026-07` et tous ses consommateurs** — la réouverture Globex nominale
   de 18:00 ET **n'est pas** l'heure de cotation du véhicule XAUUSD : médiane du premier print à
   **18:05 ET depuis 2018**, coupure de **76 minutes** depuis 2022 (contre 60 min en 2013-2017,
   et **aucune** coupure avant 2013). Toute décomposition ancrée sur l'horloge murale mélange
   trois conventions d'entrée. Instance de **L52** appliquée à une heure de réouverture.
2. **`step3_performance.py:47`** — la winsorisation en constructeur doit être retirée ou rendue
   optionnelle. Chiffrée ici sur l'excursion de l'or : pire excursion −863.8 → −222.0 bps,
   kurtosis 77.2 → 9.9. Elle est anodine pour un Sharpe et **disqualifiante** pour toute
   simulation de barrière.
3. **Lecture de L56 à nuancer** — « le drift or tient *entièrement* dans la première heure » est
   un énoncé **relatif** valable sur l'échantillon complet (3.2× la part uniforme), **pas** un
   énoncé absolu : la première heure vaut 39.7 % de la fenêtre tradable full-sample et **22.7 %
   post-2021**. La leçon d'ancrage d'horloge (le cœur de L56) est **confirmée** deux fois ici
   (0.963 vs 0.591 en horaire, +0.519 vs −0.169 en minute).
4. **Part de gap or à réviser pour l'ère moderne** — 17.5 % archivé en H1 est **reproduit**
   full-sample (17.2 %) mais vaut **36.1 %, t 3.50** post-2021. Tout chiffre H1 du dossier or
   surestime le tradable d'environ un tiers sur l'échantillon décisionnel.
5. **Candidats de leçon (NON numérotés — pas de minting en session)** :
   - `un-effet-de-clôture-peut-avoir-une-demi-vie-d-UNE-minute-et-un-mécanisme-parfaitement-valide` :
     la batterie mécanisme (gradient sans seuil + monotonicité + placebo d'ancre + hors-échantillon)
     peut être franchie intégralement par un effet qui ne survit pas à **une** minute de retard.
     Le test de mécanisme et le test d'exécutabilité mesurent des choses **orthogonales** ;
     franchir le premier ne dit rien du second. Corollaire opératoire : comparer l'edge à la
     **fourchette de la barre d'entrée** (ici 7.66 bps contre 2.83 bps d'edge) avant toute autre
     statistique — c'est gratuit et c'est décisif.
   - `l-heure-de-réouverture-d-un-véhicule-se-mesure-elle-ne-se-suppose-pas` : ancrer une échelle
     de retards sur une horloge nominale peut rendre le test **structurellement incapable** de
     mesurer ce qu'il prétend (retards 0-5 min identiques post-2022). Ancrer sur le **premier
     print exécutable**. Extension de L52 du champ de provider à l'heure de séance.
   - `retarder-une-entrée-achète-de-l-espérance-jamais-de-la-survie` : sur l'or, un retard de
     10-15 min conserve 91-93 % du gross et devrait réduire le spread, mais laisse l'excursion
     adverse intra-fenêtre **rigoureusement inchangée** (−33.9 bps à d=0 comme à d=30). Pour un
     livre dont 80 % des morts sont des franchissements de barrière journalière, les deux gains
     ne sont pas substituables.
