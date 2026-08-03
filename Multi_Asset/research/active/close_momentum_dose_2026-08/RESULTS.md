# RÉSULTATS — Dose-réponse du close momentum (mécanisme LETF)

**Verdict : REJECTED. La famille est fermée sur le MÉCANISME.**
Pré-enregistrement : `PREREGISTRATION.md`, committé `212af030` **avant** tout chargement de donnée.
Compteur local **N1 = 5 essais** (une courbe dose-réponse par instrument), **50 cellules**
rapportées (5 instruments × 2 découpages × 5 bins), dont **5 non citables** (`n < 15`, bin ≥500 bps).
Aucune modification de spécification après ouverture de la donnée (budget de mods : 0, consommé 0).

---

## 1. LA TABLE — dose-réponse en GROSS (`cost_rt = 0`), quintiles de |R_day|

`gross` = bps par trade, `side = sign(R_day)`, entrée 15:31 (delay+1), sortie à la clôture cash.
IC = bootstrap **par blocs** (Politis-Romano, bloc moyen 5, 2 000 tirages). `plac_p95` = p95 du
**placebo à autocorrélation appariée** (décalage circulaire de `side`, 400 tirages, même bin).

| Instr | bin | n | \|R_day\| | **gross** | t_HAC | IC95 | µ/σ | **plac p95** | bat placebo ? |
|---|---|--:|--:|--:|--:|---|--:|--:|:--:|
| **US500** | Q1 | 626 | 6.3 | 0.31 | 0.54 | [-0.86, 1.49] | 0.02 | 0.76 | non |
| | Q2 | 626 | 19.6 | **-1.37** | -1.71 | [-2.91, 0.18] | -0.07 | 1.37 | non |
| | Q3 | 626 | 36.6 | 1.65 | 2.07 | [0.05, 3.24] | 0.08 | 1.36 | oui |
| | Q4 | 626 | 63.1 | **-0.45** | -0.43 | [-2.55, 1.56] | -0.02 | 1.15 | non |
| | **Q5** | 626 | 135.5 | **2.57** | 1.31 | **[-1.08, 6.31]** | 0.05 | **3.18** | **non** |
| **US100** | Q1 | 645 | 8.3 | -0.39 | -0.49 | [-1.94, 1.18] | -0.02 | 1.83 | non |
| | Q2 | 645 | 26.8 | 0.18 | 0.25 | [-1.23, 1.60] | 0.01 | 1.53 | non |
| | Q3 | 645 | 50.3 | 1.08 | 1.19 | [-0.69, 3.00] | 0.05 | 1.65 | non |
| | Q4 | 645 | 85.4 | 1.31 | 1.15 | [-0.90, 3.56] | 0.05 | 1.50 | non |
| | **Q5** | 645 | 176.2 | **0.66** | 0.31 | **[-3.56, 4.49]** | 0.01 | **3.34** | **non** |
| **US30** | Q1 | 592 | 5.7 | -0.34 | -0.51 | [-1.69, 0.94] | -0.02 | 1.11 | non |
| | Q2 | 592 | 19.1 | **-1.23** | -1.77 | [-2.59, 0.17] | -0.07 | 1.17 | non |
| | Q3 | 592 | 36.0 | 0.88 | 1.20 | [-0.48, 2.32] | 0.05 | 1.14 | non |
| | Q4 | 592 | 60.8 | 0.43 | 0.43 | [-1.63, 2.28] | 0.02 | 1.67 | non |
| | **Q5** | 592 | 130.9 | **3.54** | 2.02 | [0.18, 6.97] | 0.10 | 2.77 | oui (de peu) |
| **GER40** | Q1 | 641 | 7.4 | 0.74 | 1.16 | [-0.58, 2.10] | 0.04 | 1.16 | non |
| | Q2 | 640 | 24.6 | 1.75 | 2.50 | [0.38, 3.09] | 0.10 | 1.46 | oui |
| | Q3 | 640 | 44.7 | **0.71** | 1.02 | [-0.58, 2.10] | 0.04 | 1.28 | non |
| | Q4 | 640 | 75.0 | 2.68 | 2.84 | [0.90, 4.48] | 0.12 | 1.62 | oui |
| | **Q5** | 641 | 158.8 | **2.03** | 1.71 | **[-0.28, 4.44]** | 0.07 | **1.99** | limite |
| **XAUUSD** ⚠ | Q1 | 960 | 5.6 | -0.43 | -1.43 | [-1.02, 0.16] | -0.04 | 0.50 | non |
| **contrôle −** | Q2 | 959 | 17.6 | 0.09 | 0.26 | [-0.56, 0.77] | 0.01 | 0.61 | non |
| | Q3 | 959 | 32.7 | -0.42 | -1.26 | [-1.14, 0.23] | -0.04 | 0.62 | non |
| | Q4 | 959 | 55.6 | 0.71 | 1.55 | [-0.19, 1.61] | 0.05 | 0.70 | oui |
| | **Q5** | 959 | 127.6 | **2.55** | **3.50** | **[1.15, 4.06]** | **0.11** | 1.21 | **oui** |

### Découpage absolu ex-ante (aligné sur le papier, sans look-ahead)

| Instr | <50 | 50-100 | 100-200 | 200-500 | ≥500 |
|---|--:|--:|--:|--:|--:|
| US500 | 0.15 | 0.56 | 2.37 | 1.26 *(n=72)* | — *(n=1)* |
| US100 | -0.09 | 0.92 | -0.34 | 7.33 *(n=171, t 1.68, **< plac 8.77**)* | — *(n=3)* |
| US30 | -0.11 | 0.25 | 2.00 | 22.89 *(n=51, t 2.20, plac 16.80)* | — *(n=3)* |
| GER40 | 1.22 | 1.77 | 1.64 | 5.89 *(n=117, t 1.93, **< plac 6.89**)* | — *(n=1)* |
| **XAUUSD** | -0.20 | 1.24 | **2.74** *(t 3.62)* | 3.81 | — *(n=2)* |

Les bins ≥500 bps contiennent 1 à 3 jours : **non citables**, listés pour l'exhaustivité seulement.

---

## 2. Les trois critères pré-enregistrés — **0 / 3**

### (1) MONOTONIE — **ÉCHOUE sur 4 instruments sur 5**

En quintiles, la courbe **change de signe au milieu** partout où le mécanisme est censé être le
plus fort : US500 `+0.31 / −1.37 / +1.65 / −0.45 / +2.57`, US30 `−0.34 / −1.23 / +0.88 / +0.43 /
+3.54`, US100 monte jusqu'à Q4 puis **retombe en Q5** (1.31 → 0.66), GER40 oscille
`0.74 / 1.75 / 0.71 / 2.68 / 2.03`. Ce ne sont pas des gradients, ce sont des dents de scie.

Le test formel — pente de dose, `gross_i = α + β·|R_day|_i`, HAC(6), β rescalé par +100 bps de dose :

| | **β sur la MOYENNE** | t | R² | **β sur \|gross\| (variance)** | t | R² |
|---|--:|--:|--:|--:|--:|--:|
| US500 | 1.73 | **0.88** | 0.0011 | 14.14 | **4.40** | 0.110 |
| US100 | 2.08 | **1.71** | 0.0020 | 10.43 | **5.72** | 0.079 |
| US30 | 5.12 | 2.97 | 0.0135 | 10.94 | **7.60** | 0.101 |
| GER40 | 0.64 | **0.59** | 0.0003 | 7.09 | **9.15** | 0.075 |
| XAUUSD | 2.71 | 2.75 | 0.0097 | 7.21 | **9.57** | 0.111 |

Sur les deux instruments porteurs du mécanisme (US500, US100) et sur GER40, **la pente de dose sur
la moyenne n'est pas distinguable de zéro** (t 0.88 / 1.71 / 0.59 ; R² 0.03 % à 0.2 %).

### (2) SEUIL 5.4 bps sur le bin haut — **ÉCHOUE sur 5 instruments sur 5**

Q5 : US500 **2.57**, US100 **0.66**, US30 **3.54**, GER40 **2.03**, XAUUSD **2.55**. Aucun
n'atteint 5.4. Trois des cinq IC95 contiennent zéro. Et **le placebo à autocorrélation appariée
mange le résultat** : US500 2.57 < 3.18, US100 0.66 < 3.34, GER40 2.03 ≈ 1.99. Le contrôle exigé
par le mandat était le bon : contre zéro, US500-Q5 aurait eu l'air d'un demi-signal ; contre son
propre placebo persistant, il est **en dessous**.

En bins absolus, les seules cellules > 5.4 bps sont `200-500` — et là **US100 (7.33) et GER40
(5.89) passent SOUS leur placebo apparié** (8.77 et 6.89). Ne survit que US30 `200-500` à 22.89
bps sur **n = 51 jours**, IC [4.74, 42.36] : une cellule, aucun gradient qui y mène, une largeur
d'IC de 38 bps. C'est la définition du pic isolé que le pré-enregistrement écarte d'avance.

### (3) CONTRASTE DE MÉCANISME (L44) — **ÉCHOUE, et c'est le résultat qui tranche**

Attendu : **US500/US100 ≫ GER40 ≫ XAUUSD**. Observé en Q5 :

```
US30 3.54  >  US500 2.57  ≈  XAUUSD 2.55  >  GER40 2.03  >  US100 0.66
             t 1.31          t 3.50                          t 0.31
```

**L'ordre attendu est détruit, et le contrôle négatif est le meilleur élève.** XAUUSD est le seul
instrument dont la courbe absolue est **proprement monotone** (`−0.20 → 1.24 → 2.74 → 3.81`), le
seul dont le Q5 a un **t_HAC > 3** et un IC95 excluant zéro `[1.15, 4.06]`, et le seul à battre
franchement son placebo. Il a aussi la **pente de dose sur la moyenne la plus significative après
US30** (t 2.75) — devant US500 (0.88), US100 (1.71) et GER40 (0.59).

Il n'existe pas d'écosystème d'ETF à levier sur l'or comparable à celui des indices US, et
XAUUSD n'a **pas de clôture cash** : la fenêtre 15:31→16:00 ET y est une fenêtre de marché
continu. Qu'elle produise le résultat le plus net des cinq **falsifie l'attribution au flux MOC des
LETF**. Ce qui est mesuré est un **effet de continuation de fin de journée générique sur les jours
à forte amplitude**, présent sur un actif sans MOC, absent en gradient sur les indices qui
concentrent 100 % du flux LETF.

---

## 3. Le vrai contenu de la courbe : de la VARIANCE, pas de la moyenne (L54)

| σ du rendement de fenêtre (bps) | Q1 | Q2 | Q3 | Q4 | Q5 | **Q5/Q1** |
|---|--:|--:|--:|--:|--:|--:|
| US500 | 19.0 | 19.7 | 19.9 | 24.0 | 49.0 | **2.57×** |
| US100 | 22.6 | 19.4 | 23.9 | 28.2 | 52.5 | **2.32×** |
| US30 | 17.5 | 16.8 | 18.0 | 23.3 | 37.1 | **2.12×** |
| GER40 | 16.6 | 18.3 | 17.9 | 23.1 | 29.0 | **1.75×** |
| XAUUSD | 10.3 | 10.0 | 11.1 | 14.3 | 22.7 | **2.21×** |

L'amplitude du jour prédit la dispersion de la dernière demi-heure avec une force écrasante
(t 4.4 à 9.6, R² 7.5-11.1 %) et la moyenne avec une force nulle (t 0.6 à 3.0, R² 0.03-1.4 %).
**Le rapport des R² est de 50× à 250×.** C'est la signature exacte que L54 décrit : le régime
prédit la variance, pas la moyenne dans le même sens.

Conséquence directe : **µ/σ par trade ne dépasse jamais 0.12**, et ne présente aucun gradient
lisible (US500 : 0.02 / −0.07 / 0.08 / −0.02 / 0.05). Le gross qui « monte » avec la dose monte
parce que **σ monte de 2.1× à 2.6×** — c'est un effet d'échelle, pas d'edge. Un edge réel se
verrait sur µ/σ ; il n'y est pas.

---

## 4. Contrôles

- **Horloge (L56) — PASS, et le test valait son prix.** Corrélation du profil horaire hiver-vs-été,
  profils normalisés, 24 cellules : **exchange 0.988 (US500) / 0.991 (US100) / 0.985 (US30) /
  0.971 (GER40) / 0.963 (XAUUSD)** contre **UTC 0.766 / 0.785 / 0.739 / 0.703 / 0.591**. L'horloge
  d'échange avec DST est la bonne ; une spécification en UTC aurait décalé la fenêtre d'une heure
  sur tout l'été. Source `data/deep_history_utc/` (vrai UTC vérifié) ; `data/panels/m5_indices/`
  n'a **jamais** été ouvert.
- **L60 — barres à fourchette nulle : RAS dans la fenêtre.** Part de barres `high == low` **dans la
  fenêtre de trade**, par instrument et par an : **≤ 0.8 % partout après 2014**, 0.000 sur
  2020-2026 pour les cinq. Le pic historique est US500 2014 à 8.0 %. ⚠ **L'alerte US30
  79.7/100/74.9 % concerne la colonne `spread`, pas `high==low`** : elle ne contamine pas cette
  mesure, qui n'utilise à aucun moment la colonne `spread`.
- **L59 — delay+1 sur l'entrée ET la sortie.** Entrée à la clôture de la barre **suivant** le
  signal (15:31), jamais la barre du signal. Géométrie de sortie **constante** (sortie temporelle,
  aucun stop, aucun bracket) — le piège « l'edge était dans la sortie » ne s'applique pas ici par
  construction. **Variante sortie une barre plus tôt** : le gross Q5 tombe de **2.57 → 1.47**
  (US500, −43 %), **3.54 → 2.44** (US30, −31 %), **2.03 → 1.52** (GER40), **2.55 → 2.16** (XAUUSD).
  Un tiers à moitié du (déjà minuscule) effet vit dans **la dernière minute**, soit le print le
  moins exécutable de la séance.
- **L25 — jambes disjointes.** Rapportées séparément, jamais par `−side_long`. En Q5 aucune paire
  de jambes n'est significative des deux côtés : US500 up 1.80 (t 0.77) / down 3.34 (t 1.05) ;
  US30 up 1.86 (t 0.74) / down 5.36 (t 2.16) ; GER40 up 2.98 (t 1.83) / down 1.14 (t 0.64) ;
  XAUUSD up 3.82 (t 4.76) / down 1.23 (t 1.05) — **asymétrique**, la jambe qui porte XAUUSD est
  la jambe haussière seule.
- **L58 — baseline inconditionnelle appariée au bin.** `E[r_fenêtre]` non signé, calculé **dans
  chaque bin**, jamais sur la fenêtre pleine. Il est loin d'être nul et **change de signe selon le
  bin** (US500 Q4 −0.99, Q5 −0.75 ; US30 Q5 −1.61 ; XAUUSD Q5 +1.34) : une baseline globale
  aurait crédité ou débité les cellules hautes de plus d'un bps. Le piège annoncé était réel.
- **Bootstrap par blocs** partout (Politis-Romano, bloc moyen 5), **jamais iid**.
- **DSR non calculé** : aucun PASS n'émerge du gate gross, la déflation n'a rien à déflater.
  `framework.py:131` / `ftmo_lab.py:232` n'ont pas été utilisés (cassés, σ_SR_trials absent).

## 5. Le coût, pour mémoire — le gate gross ayant déjà tranché

Non appliqué comme critère (le gate est en gross), donné pour dimensionner. Coûts **mesurés**
(COST_AUDIT) sur le meilleur bin de chaque instrument, ~50 trades/an en Q5 :

| | gross Q5 | coût RT | **net** | µ/σ net | **Sharpe ann. net** |
|---|--:|--:|--:|--:|--:|
| US500 | 2.57 | 1.82 | **0.75** | 0.015 | **0.11** |
| US100 | 0.66 | 1.80 | **−1.14** | — | **négatif** |
| US30 | 3.54 | 1.47 | **2.07** | 0.056 | **0.39** |
| GER40 | 2.03 | 1.73 | **0.30** | 0.010 | **0.07** |
| XAUUSD | 2.55 | 1.84 | **0.71** | 0.031 | **0.22** |

Le meilleur cas — US30, **le seul des cinq dont le Q5 batte son placebo**, sur une courbe non
monotone — plafonne à **Sharpe 0.39**, sous RESEARCH_PASS (0.7) et très loin de PROPFIRM_PASS
(1.0). Et ce chiffre est **optimiste** : il retient le meilleur instrument après en avoir regardé
cinq, sans déflation.

---

## 6. Verdict

**REJECTED — kill MÉCANIQUE, pas kill de coût ni de puissance.**

Ce n'est pas « l'edge existe mais le coût le mange » et ce n'est pas UNDERPOWERED. C'est :
la dose ne prédit pas la moyenne (**t 0.88 / 1.71 / 0.59** sur US500 / US100 / GER40, R² < 0.2 %),
la courbe n'est pas monotone, le bin haut est **2 à 8× sous le seuil de 5.4 bps**, il passe **sous
son propre placebo apparié** sur les deux instruments-clés, et **le contrôle négatif produit le
résultat le plus propre des cinq**.

Au regard de la politique de ré-ouverture : le kill est de nature **mécanique** ⇒ la famille
**RESTE FERMÉE**. Elle n'est pas rouvrable par un meilleur véhicule, un meilleur tarif, ni un
échantillon plus long — recalibrer une statistique ne ressuscite pas une pente de 0.03 % de R².

**L'essai SG-2 est réhabilité dans sa conclusion, pas dans sa méthode.** Il avait raison (gross
≈ 0) pour de mauvaises raisons (mauvais prédicteur, effet supposé dilué par le pooling). La bonne
raison est établie ici : **il n'y a pas d'effet concentré à diluer**. Le pooling n'était pas le
problème.

## 7. Ce que ce test ne prouve PAS

- **Il ne réfute pas Baltussen-Da-Lammers-Martens.** Les auteurs mesurent le flux LETF sur les
  **volumes MOC** et travaillent sur des données d'enchère de clôture. Ce test mesure ce qu'un
  compte retail peut **capturer en prix** dans les 29 dernières minutes d'un CFD. L'effet peut être
  réel dans le carnet MOC et non capturable en prix hors enchère : **ce sont deux affirmations
  différentes**, et seule la seconde est testée ici.
- **Il ne teste pas l'enchère de clôture elle-même** (participation MOC/LOC), à laquelle ce desk
  n'a de toute façon pas accès via CFD ou futures.
- **Il ne teste pas d'autres fenêtres** — 5, 10, 60 minutes — ni d'autres seuils de dose que ceux
  gelés au §3.3 du pré-enregistrement. Les explorer maintenant serait du data-mining sur une
  courbe déjà vue, et déflaterait le DSR de tous les candidats suivants.
- **Il ne dit rien de l'amplitude comme prédicteur de VARIANCE**, qui est le seul résultat
  robuste ici (t 4.4-9.6, R² 7-11 %). Cette relation est solide mais bien connue, et **L54
  interdit d'en faire une sleeve** : prédire la dispersion sans prédire la moyenne ne rémunère rien.
- **US30 `200-500` bps (22.89 bps, n=51) n'est pas déclaré nul, il est déclaré non citable** :
  cellule isolée sans gradient, IC de 38 bps de large, sur le seul des quatre indices dont la
  série démarre en 2013-11. La ré-explorer exigerait un angle neuf écrit d'avance — et elle n'en
  offre aucun, puisque le mécanisme invoqué vient d'être falsifié par son propre contrôle négatif.

---

### Provenance

Données : `data/deep_history_utc/{US500,US100,US30,GER40,XAUUSD}_M1.csv`, importées du répertoire
principal par chemin absolu, **lecture seule**, aucun blob copié dans le repo.
Couverture : US500 3 130 j (2012-01→2026-06), US100 3 225 j (2013-01→), US30 2 960 j (2013-11→),
GER40 3 202 j (2013-10→), XAUUSD 4 796 j (2007-01→). Interpréteur **`/usr/bin/python3`**
(pandas 2.2.3) — l'alias zsh masquant un binaire sans pandas a été contourné explicitement.
