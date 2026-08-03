# Pairs trading / cointégration sur véhicule FTMO CFD — RÉSULTATS

**2026-08-03.** Branche `claude/pairs-cointegration`. Pré-enregistrement committé en `bf27c8b4`,
**avant** toute mesure. Interpréteur `/usr/bin/python3`.
Données : `data/deep_history_utc/` (M1 vrai UTC), resamplées M5, **19 séries vérifiées
bit-exact contre le M1 source** (max abs diff = 0 sur 6 séries recontrôlées après un incident
de cache, §9.1).

---

## 0. Verdict

**REJECTED — famille fermée sur ce véhicule.** Deux verdicts distincts, à ne pas confondre :

| | verdict | nature du kill | rouvrable ? |
|---|---|---|---|
| 17 paires sur 18 | **REJECTED** | **MÉCANIQUE** — gross ≈ 0 ou négatif, two-sided échoué à coût NUL | **NON** |
| AUDUSD/USDCAD | **REJECTED sur FTMO** | **COÛT** — gross réel (DSR 0.97 à 171 essais), tué par la facture CFD | **OUI, hors CFD** |

Le chiffre qui décide, et il décide avant tout signal :

> **0 paire sur 171 n'a une demi-vie de retour compatible avec une séance.**
> La plus courte de tout l'univers vaut **1 588 minutes** contre une porte K1 à **480**.

Aucune stratégie n'a été construite pour « voir » — c'est la condition d'abandon anticipé §8 du
pré-enregistrement, appliquée telle qu'écrite. Ce qui suit explique **pourquoi**, parce que la
nature du kill décide de la ré-ouverture et qu'elle n'est pas la même pour toutes les paires.

---

## 1. Ce que dit la littérature — et son déclin, qui est l'information de premier ordre

La famille est **en déclin documenté, continu, et depuis vingt ans**. Ce n'est pas une nuance :
c'est le fait dominant.

| source | ce qu'elle établit |
|---|---|
| Gatev-Goetzmann-Rouwenhorst (2006), 1962-2002 | le point de départ : ~**11 %/an** d'excès sur portefeuille auto-financé |
| Krauss (2017), revue de **76 études** | moyenne **10.8 %/an**, Sharpe **0.96** — mais **15.6 % avant 2000 → 6.4 % après 2010** |
| Do & Faff (2010, 2012), CRSP 1962-2009 | déclin causé par la **part croissante de paires qui ne convergent pas** ; et surtout : **après coûts variables dans le temps, la méthode par distance ne rapporte plus rien en moyenne** |
| Zhu (2024, Yale), 20 dernières années | réplication GGR : **6.2 %/an**, Sharpe 1.35 — mais **une déviation d'un écart-type du facteur momentum efface presque tout le rendement** |
| « Gold Standard Pairs Trading Rules: Are They Valid? » (2020) | le paramétrage canonique (formation 12 mois, trading 6 mois, entrée 2σ, top-N) **n'est pas optimal** et les résultats y sont sensibles |
| Avellaneda-Lee (2010) | approche résiduelle/OU ; **filtre explicite de vitesse de retour** (κ > 252/30, demi-vie ~30 **jours**), Sharpe 1.51 sur 2003-2007 |
| Villota (2025), « Is Pairs Trading a Thing of The Past? » | l'érosion s'est poursuivie ; les implémentations mécaniques simples ne délivrent plus |

Trois enseignements qui ont directement structuré ce dossier :

1. **Le déclin est causé par la non-convergence, pas par la compétition HFT.** Do & Faff
   l'attribuent à des paires qui cessent d'être des substituts. C'est exactement ce que nos
   mesures retrouvent (§3, §4) — et c'est un problème que ni un meilleur estimateur ni un
   meilleur véhicule ne réparent.
2. **La littérature qui « marche » vit à des horizons de SEMAINES.** Avellaneda-Lee filtrent sur
   une demi-vie de ~30 jours. GGR tiennent 6 mois. C'est structurellement incompatible avec un
   CFD à deux jambes qui paie ~1.5 bps/nuit (L28) : 30 jours de détention = **45 bps de portage**.
   La littérature rentable de cette famille est donc, pour nous, la littérature **inaccessible**.
3. **Presque toute cette littérature porte sur des ACTIONS**, où le mécanisme (substituts proches,
   même secteur, chocs communs se propageant à vitesses différentes) est fort et l'univers large
   (N ≥ 30 trivialement satisfait). Sur 19 macro-instruments CFD, ni le mécanisme ni la largeur ne
   transfèrent. Le peu de littérature FX/commodités est mince et rarement nette de coûts réalistes.

---

## 2. LE RÉSULTAT STRUCTURANT — la table des demi-vies

Méthode : par fenêtre de formation glissante de 30 jours, OLS `log A = a + β log B` sur les
prix log M5, puis OU sur le résidu. **Seules les transitions intra-session comptent** — une
transition dont l'écart de timestamp n'est pas exactement 5 min (nuit, week-end, jour férié) n'est
pas une observation de retour à la moyenne et est écartée. 152 fenêtres par paire, 2014-01 → 2026-06.

**Univers complet : 171 paires. Rapporté intégralement dans `outputs/stage_a_halflife_171.csv`,
sans top-k** (l'étage A est descriptif : il ne consomme aucun essai et aucune décision n'en sort).

### 2.1 La distribution entière, en une ligne

| | demi-vie médiane (min de temps de trading) |
|---|--:|
| minimum sur 171 paires (EURGBP/GER40) | **1 588** |
| médiane des 171 | **2 160** |
| maximum (EURUSD/EURGBP) | **2 745** |
| **porte K1 (une séance = 96 barres M5)** | **480** |
| **paires sous la porte** | **0 / 171** |

La plus rapide de tout l'univers est **3.3× trop lente**. La médiane est **4.5× trop lente**.
Il n'y a pas de cas limite à arbitrer : la distribution entière est du mauvais côté, et l'écart
n'est pas un écart de réglage.

En clair : 1 588 minutes ≈ **26 heures de temps de marché**, et il en faut **trois demi-vies**
pour qu'une déviation se referme pour l'essentiel — soit **~80 heures**, c'est-à-dire **3 à 4
nuits tenues** sur les deux jambes.

### 2.2 Les 18 paires pré-enregistrées (étage B)

| A | B | groupe | HL méd. (min) | Q25 | Q75 | σ résidu (bps) | β méd. | β IQR | ADF tient |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| EURUSD | USDCHF | G8 | 1 752 | 941 | 2 976 | 32.7 | −0.77 | 0.38 | 19.7 % |
| XAUUSD | XAGUSD | G2 | 1 806 | 1 151 | 3 240 | 65.2 | 0.45 | 0.32 | 16.4 % |
| USDCAD | AUDUSD | G7 | 1 874 | 1 166 | 3 100 | 37.7 | −0.50 | 0.34 | 11.8 % |
| US30 | GER40 | G4 | 1 893 | 1 305 | 3 033 | 70.2 | 0.64 | 0.54 | 13.8 % |
| US500 | US30 | G3 | 1 916 | 1 011 | 3 422 | 39.2 | 0.96 | 0.30 | 17.1 % |
| UKOIL | USOIL | G1 | 1 950 | 1 281 | 3 588 | 60.3 | 0.90 | 0.18 | 16.4 % |
| US500 | GER40 | G4 | 1 955 | 1 352 | 3 352 | 71.5 | 0.59 | 0.53 | 11.2 % |
| AUDUSD | NZDUSD | G7 | 1 961 | 1 218 | 3 362 | 44.1 | 0.77 | 0.39 | 15.8 % |
| US500 | US100 | G3 | 2 021 | 1 259 | 3 389 | 38.8 | 0.68 | 0.25 | 8.6 % |
| EURJPY | AUDJPY | G6 | 2 263 | 1 559 | 3 195 | 45.8 | 0.53 | 0.43 | 12.5 % |
| EURUSD | GBPUSD | G5 | 2 338 | 1 423 | 3 409 | 40.9 | 0.62 | 0.50 | 14.5 % |
| US100 | GER40 | G4 | 2 349 | 1 574 | 4 238 | 110.2 | 0.68 | 0.65 | 14.5 % |
| USDJPY | AUDJPY | G6 | 2 429 | 1 636 | 3 763 | 55.0 | 0.38 | 0.50 | 15.1 % |
| US100 | US30 | G3 | 2 450 | 1 450 | 4 538 | 95.6 | 1.10 | 0.65 | 14.5 % |
| EURUSD | EURJPY | G8 | 2 481 | 1 687 | 3 916 | 48.0 | 0.40 | 0.81 | 12.5 % |
| USDJPY | EURJPY | G6 | 2 484 | 1 678 | 3 883 | 48.1 | 0.60 | 0.81 | 11.8 % |
| GBPUSD | EURGBP | G5 | 2 600 | 1 682 | 3 571 | 54.2 | −0.70 | 0.87 | 9.9 % |
| EURUSD | EURGBP | G5 | 2 722 | 1 787 | 3 782 | 54.3 | 0.30 | 0.87 | 9.9 % |

Deux colonnes méritent autant d'attention que la demi-vie :

- **`ADF tient` : 8.6 % à 19.7 %** des fenêtres de formation rejettent la racine unitaire à 5 %.
  Sous l'hypothèse nulle « aucune cointégration », on attendrait **5 %**. On est à peine au-dessus
  du hasard. **Ces paires ne sont pas cointégrées à fréquence intraday** — y compris Brent/WTI
  (16.4 %) et or/argent (16.4 %), les deux « évidences » du domaine.
- **`β IQR` : 0.18 à 0.87.** Le hedge ratio d'EURUSD/EURGBP se promène sur une fourchette
  inter-quartile de 0.87 autour d'une médiane de 0.30 — il change de **plus que sa propre
  valeur** d'une fenêtre à l'autre. Il n'y a pas de relation stable à estimer, donc rien qu'un
  hedge ratio dynamique puisse rattraper : le dynamique suivrait du bruit.

### 2.3 Falsification microstructure — la demi-vie mesurée est OPTIMISTE

Le rebond bid-ask fabrique du faux retour à la moyenne rapide à haute fréquence. Test gratuit :
si la demi-vie en **unités de TEMPS** est stable d'une fréquence d'échantillonnage à l'autre, la
dynamique est réelle ; si elle **croît** avec l'intervalle, une part du retour vu en M5 est du bruit.

| | M5 | M15 | M30 | H1 |
|---|--:|--:|--:|--:|
| demi-vie médiane (min), 18 paires | 2 142 | 2 269 | 2 367 | **2 438** |

**Ratio H1/M5 = 1.14, croissance monotone.** La demi-vie M5 est biaisée **court** d'environ 14 % :
la vraie est plus proche de **2 440 minutes** (≈ 40 h de marché). Le verdict K1 est donc rendu sur
l'estimation la **plus favorable** à la famille, et il est quand même sans appel.

### 2.4 Y a-t-il une minorité de fenêtres rapides ? Non

Une médiane peut cacher une sous-population tradable. Fraction des fenêtres de formation dont la
demi-vie passe la porte des 480 min :

**de 0.39 % (USDJPY/EURJPY, USDJPY/AUDJPY) à 10.8 % (US500/US30), médiane 2.1 %.**

Or un ajustement OU sur une marche aléatoire rend parfois une demi-vie courte par pur hasard :
quelques pourcents sont exactement ce qu'on attend **sans aucun signal**. Il n'y a pas de régime
rapide à isoler, et donc pas de filtre de régime à construire.

---

## 3. Le gate au GROSS (K3) — l'effet existe-t-il seulement à coût nul ?

C'est la mesure qui sépare un kill de véhicule d'un kill mécanique, et la première chose à faire.
Conditionnellement à |z| ≥ 2 **hors échantillon** (paramètres de la seule fenêtre de formation,
K9), de combien le résidu revient-il ? **À coût strictement nul.** Signe orienté : positif = revient.

| horizon | moyenne poolée (bps) | baseline L58 appariée à l'état | paires t > 2.5 | paires t < −2.5 |
|---|--:|--:|--:|--:|
| 12 barres (1 h) | **+0.122** | +0.030 | 5/18 | 0/18 |
| 48 barres (4 h) | **+0.129** | −0.027 | 5/18 | 1/18 |
| 144 barres (12 h) | **+0.033** | −0.250 | 6/18 | 3/18 |
| 288 barres (24 h) | **+0.148** | −0.434 | 6/18 | 4/18 |

**Un dixième de point de base.** Contre un coût aller-retour à deux jambes de **~3-4 bps**. Le
rapport gross/coût est de l'ordre de **0.04**, pour une porte K2 à **1.5** : il manque un facteur
**~35**. Et ce n'est pas un problème de coût — à coût NUL, l'effet est déjà indiscernable de rien.

Quatre paires ont même un retour **significativement négatif** à 24 h, c'est-à-dire que la
déviation **s'aggrave** : XAUUSD/XAGUSD **−6.11 bps** (t −12.8), US100/GER40 **−5.44** (t −7.5).
Or/argent, la paire canonique du domaine, est un spread **momentum**, pas un spread de retour.

### 3.1 L25 two-sided à jambes disjointes — et la confirmation de L27

Les déviations hautes (z ≥ +2) et basses (z ≤ −2) forment **deux échantillons de trades
disjoints** ; aucune n'est l'opposé de l'autre. À 12 h :

- **5/18 paires seulement** ont les deux côtés positifs.
- **10/18 ont les deux côtés de SIGNE OPPOSÉ.**

Le motif est systématique sur les indices : quand le spread est haut il monte encore, quand il est
bas il remonte. US100/GER40 : côté haut **−7.68**, côté bas **+5.82**. US30/GER40 : **−1.20** /
**+5.00**. Ce n'est pas du retour à la moyenne — c'est un **drift relatif persistant** que la
re-centrage tous les 20 jours ne retire jamais.

C'est **exactement L27, mesuré** : *market-neutral par construction ≠ two-sided en spread*. Un
spread cointégré hérite du drift relatif de ses jambes, et ce drift est ce que le z-score capture.
Sur 2014-2026, US100 surperforme GER40 ; « fader » le spread haut, c'est shorter la surperformance.

---

## 4. Le seul survivant du gross, et comment il meurt

Trois paires passent L25 (deux côtés positifs, côté faible t ≥ 1.0) : UKOIL/USOIL,
AUDUSD/USDCAD, AUDUSD/NZDUSD. Elles ont été re-testées **correctement**.

**Pourquoi un re-test.** Les t du §3 sont calculés sur des fenêtres **chevauchantes** (horizon
144-288 barres, avancées d'une barre) avec un HAC lag-6. Les magnitudes en bps sont non biaisées,
**les t ne le sont pas** : la longueur d'autocorrélation effective vaut au moins l'horizon, donc
N_eff ≪ N et le lag-6 sous-estime largement la variance (**L12b**). Un t de 13 sur 228 000
observations chevauchantes ne mesure que le chevauchement. Re-test en **trades non chevauchants**
(une position à la fois), delay+1 à l'entrée **et** à la sortie (K7/L59), **bootstrap par blocs**
stationnaire au lieu d'un t-stat, coûts sur **deux jambes** + portage 1.5 bps/nuit.

| paire | trades | barres méd. | nuits méd. | coût (bps) | **GROSS** [IC95] | **NET** [IC95] | L38 R² |
|---|--:|--:|--:|--:|---|---|--:|
| UKOIL/USOIL | 1 243 | 289 | 1 | 6.89 | +5.17 **[−2.64, +16.04]** | −1.72 [−9.57, +9.17] | 0.078 |
| **AUDUSD/USDCAD** | 1 585 | 289 | 1 | 4.05 | **+5.12 [+2.79, +7.42]** | +1.07 **[−1.25, +3.36]** | **0.003** |
| AUDUSD/NZDUSD | 1 650 | 289 | 1 | 4.05 | +0.63 [−1.05, +2.29] | −3.42 [−5.11, −1.76] | 0.005 |

- **UKOIL/USOIL** : l'IC du gross **contient zéro**. → **UNDERPOWERED**, pas un rejet — mais rien
  à déployer, et le coût pétrole (6.89 bps sur deux jambes) est de toute façon le double du gross
  ponctuel.
- **AUDUSD/NZDUSD** : gross indiscernable de zéro, net **significativement négatif**. → REJECTED.
- **AUDUSD/USDCAD** : gross **+5.12 bps, IC [+2.79, +7.42], exclut zéro**. Les **deux** côtés
  disjoints excluent zéro (haut +6.18 [+3.02, +9.30], bas +4.04 [+0.17, +7.82]) : **L25 passé**.
  **L38 R² = 0.003** : orthogonal à la direction de ses jambes. Puis **net +1.07, IC [−1.25,
  +3.36] — contient zéro.** Le coût mange **79 %** du gross.

### 4.1 DSR — et ce qu'il désigne exactement

| série | Sharpe | DSR (n_trials = 18, famille pré-enregistrée) | DSR (n_trials = 171, borne conservatrice) |
|---|--:|--:|--:|
| **gross** | 1.290 | **0.9973** | **0.9723** |
| **net** | 0.380 | 0.3101 | 0.0874 |

Lecture, et c'est le résultat le plus utile du dossier : **l'effet AUDUSD/USDCAD survit à la
correction pour essais multiples au gross, même en déflatant sur les 171 paires balayées.**
Ce n'est pas un artefact de data-mining. **Il meurt sur la facture de coût du CFD, et sur rien
d'autre.**

### 4.2 Le piège de la pré-vol d'amplitude — un enseignement méthodologique

La porte K2 telle que pré-enregistrée calcule le gross attendu comme `z_entry × σ_résidu`. Pour
AUDUSD/USDCAD : 2 × 37.7 = **75.4 bps**. Le gross **réalisé** est **5.12 bps**.

**La pré-vol standard surestime le gross réalisable d'un facteur ~15**, parce qu'elle suppose un
retour COMPLET à la moyenne — ce qui n'est vrai que si le résidu est stationnaire. Il ne l'est pas
(ADF tient 11.8 % du temps sur cette paire). La déviation est grande **précisément parce que** la
relation est instable, pas parce qu'il y a une grande oscillation qui revient.

Signe confirmatoire, gratuit : la **durée médiane des trades est de 289 barres pour un plafond de
288** — c'est-à-dire que **quasiment aucun trade ne sort par convergence**. Ils sortent tous au
plafond de temps. La sortie « |z| ≤ 0.5 » ne se déclenche presque jamais.

⇒ **Candidat de leçon (NOMMÉ, non numéroté)** : *la pré-vol d'amplitude d'une paire doit être
calculée sur la convergence RÉALISÉE hors échantillon, jamais sur `z × σ` — l'écart est d'un ordre
de grandeur dès que le résidu n'est pas stationnaire, et il est toujours dans le sens optimiste.
Contrôle gratuit : la fraction de trades qui sortent par convergence plutôt que par plafond de temps.*

---

## 5. Classification de la nature du kill — ce qui décide de la ré-ouverture

Selon la politique de ré-ouverture (CLAUDE.md) :

| paires | constat | nature | statut |
|---|---|---|---|
| 15/18 | gross ≈ 0 (±0.1 bps) à coût NUL, ou two-sided de signes opposés | **MÉCANIQUE** | **RESTE FERMÉ** — recalibrer une statistique ne ressuscite pas un gross de 0.03 bps |
| UKOIL/USOIL, AUDUSD/NZDUSD | IC du gross contenant zéro | **PUISSANCE** | rouvrable en principe, mais sans angle nouveau identifié |
| AUDUSD/USDCAD | gross réel et déflaté (DSR 0.97), tué par 4.05 bps de coût CFD | **COÛT** | **ROUVRABLE hors CFD** |

**Le seul pointeur qui vaut la peine d'être écrit** : AUDUSD/USDCAD est tué par le coût, et le
registre dit qu'un kill sur le coût est rouvrable parce que le tarif futures (~0.4 bps RT) change
la porte d'un ordre de grandeur. Ordre de grandeur, à titre indicatif et **non testé** : 1 585
trades sur 12.4 ans ≈ **128 trades/an × 5.12 bps ≈ 6.6 %/an de gross** sur le notionnel de la
jambe A. Le véhicule naturel n'est **pas FTMO** — ce sont les futures 6A/6C (ou leurs micros) sur
le **compte IBKR personnel**, véhicule de première classe (L53), où il n'y a ni markup de
financement ni barrière.

**Ce n'est PAS un PASS et ne doit pas être cité comme tel.** C'est une piste qui exige son propre
pré-enregistrement, sur son propre véhicule, avec ses propres coûts mesurés — et un examen sérieux
du fait qu'à β ≈ −0.50 la position nette est « long AUD contre un panier moitié CAD moitié USD »,
c'est-à-dire potentiellement du **beta dollar/matières premières déguisé**, même si le R² de L38
mesuré ici (0.003) ne le détecte pas.

---

## 6. Contrôles exécutés

| contrôle | statut | résultat |
|---|---|---|
| **K3 gate au GROSS d'abord** (`cost_rt = 0`) | ✅ | fait AVANT tout calcul de coût ; c'est lui qui tue 15/18 |
| **L25 two-sided à jambes DISJOINTES** | ✅ | échantillons de trades séparés, jamais `-side_long` ; 10/18 de signes opposés |
| **L58 baseline inconditionnelle appariée à l'état** | ✅ | même forme de trade, mêmes fenêtres, sans la condition \|z\|≥2 ; rapportée à chaque horizon |
| **L38 β-orthogonalité** | ✅ | R² 0.003-0.078, tous < 30 % |
| **L59 delay+1 ENTRÉE et SORTIE** | ✅ | signal lu en clôture de t, entrée ET sortie à l'**ouverture** de t+1 |
| **L60 barres à fourchette nulle** | ✅ | 2 série-années sur 247 > 20 % (COPPER 2014 27.7 %, 2015 23.1 %) ; COPPER n'entre dans aucune paire de l'étage B ⇒ sans effet |
| **Look-ahead de cointégration** | ✅ | β, μ, σ, seuils de la **seule** fenêtre de formation ; formation et trading strictement disjoints |
| **Walk-forward ≥ 5 folds** | ✅ | 152 fenêtres formation→trading par paire (formation 20 j, trading 5 j) |
| **Bootstrap par blocs** (Politis-Romano) | ✅ | stationnaire, bloc moyen 10, 5 000 tirages ; aucun IC iid |
| **DSR** via `dsr.py` racine corrigé | ✅ | `std_sr_trials` = plancher de bruit d'échantillonnage (0.280), jamais le défaut cassé de 1.0 |
| **L12b déflation HAC / chevauchement** | ✅ | détecté et corrigé : les t du §3 sont invalidés par le chevauchement, re-test en trades non chevauchants |
| **Placebo à autocorrélation appariée** | **non atteint** | voir §7 |

### 6.1 Pourquoi aucun p(pass) n'est rapporté

Aucune configuration n'a produit de série nette positive à simuler : le seul candidat qui passe le
gross a un **net dont l'IC contient zéro**. Simuler une barrière sur une espérance nulle ne
mesurerait que la persistance, ce qui est précisément le piège que le placebo à décalage circulaire
existe pour attraper — une série strictement dé-moyennée atteint **92.9 %** de p(pass) à horizon
long. **Rapporter un p(pass) ici aurait été le mensonge le plus facile du dossier.**

Les deux corrections de prémisses reçues en cours de route sont intégrées et **ne changent pas le
verdict** : (i) le **plancher statique** lie à 49.7 % des morts, pas la barrière journalière — un
spread à 3-4 nuits de détention et à queue non bornée est un profil défavorable au plancher aussi ;
(ii) l'horizon de référence est **182 jours** et non 91, ce qui adoucit la pénalité de lenteur —
mais adoucir la pénalité d'une espérance nulle laisse une espérance nulle.

---

## 7. Ce que ce dossier NE prouve PAS

1. **Il ne prouve pas que le pairs trading ne marche pas.** Il montre qu'il ne marche pas **sur
   19 macro-instruments CFD, à horizon intraday, avec deux jambes à financer**. La littérature
   rentable est sur ACTIONS, à univers large (des centaines de titres), à horizon de semaines.
   Nous n'avons ni cet univers ni cet horizon, et la contrainte N ≥ 30 de la maison n'est même pas
   satisfaite par 19 instruments pour une famille cross-sectionnelle.
2. **Il ne teste pas les copules**, écartées explicitement au pré-enregistrement. Elles changent la
   forme de la **dépendance**, pas la **demi-vie** — et c'est la demi-vie qui lie ici. Une copule
   sur un résidu non stationnaire à demi-vie de 26 h reste non tradable intraday. L'affirmation
   qu'elles ne sauveraient rien est un **argument**, pas une mesure.
3. **Il ne teste pas Johansen** ni les paniers à ≥3 jambes. Aucun n'était pré-enregistré. Un panier
   paierait **encore plus** de jambes à financer, mais son résidu pourrait être plus stationnaire :
   c'est une question ouverte, non tranchée ici.
4. **Il ne teste pas les horizons de semaines à mois** sur ces mêmes instruments. C'est le régime
   où la littérature trouve quelque chose — et c'est le régime que L28/L36 ferment sur CFD par le
   portage, pas par l'absence de signal. Sur un véhicule futures, la question est **rouvrable**.
5. **Le β-orthogonalité de AUDUSD/USDCAD (R² 0.003) est mesuré sur les jours à trade uniquement**
   et sur des rendements de jambes quotidiens. Il est cohérent, pas définitif ; §5 dit pourquoi il
   faut quand même s'en méfier.
6. **Les coûts sont des ordres de grandeur, pas des constantes** (COST_AUDIT §6.4 : n = 32 fills,
   un compte, aux heures liquides). Un déplacement de ±1 bps ne change pas un verdict à facteur 35,
   mais il déplacerait la frontière d'AUDUSD/USDCAD, qui se joue à ~1 bps près.
7. **La demi-vie est estimée par OU discret sur résidu OLS.** Un estimateur plus fin (Kalman,
   maximum de vraisemblance exact, filtrage du bruit microstructure) donnerait des chiffres un peu
   différents — mais §2.3 montre que le biais joue **dans le sens de la famille**, et l'écart à
   franchir est de 3.3× à 4.5×.

---

## 8. Comptabilité

- **N1 local ouvert à 0**, clos à **75 cellules** : 72 cellules de gross (18 paires
  pré-enregistrées × 4 horizons) + 3 re-tests puissamment spécifiés. Aucune cellule de stratégie
  déployable n'a été construite (condition d'abandon §8 du pré-enregistrement, appliquée).
- **Étage A = 171 paires, N0 descriptif, 0 essai consommé** — mesure rapportée intégralement,
  aucune décision n'en découle directement, aucune paire promue sur son seul classement de demi-vie.
- **Budget de modifications : 3 disponibles, 0 consommée.** Aucune variante n'a été ré-essayée
  après un résultat.
- **Écart au pré-enregistrement, déclaré** : le tableau §4.2 du pré-enregistrement annonce
  « 24 paires » à l'étage B ; les 8 groupes énumérés en contiennent en réalité **18**
  (1+1+3+3+3+3+2+2). C'est une erreur d'arithmétique dans le pré-enregistrement, pas un
  rétrécissement après mesure : la **liste** des paires n'a pas bougé. Les 18 sont testées.
- **Ajout post-hoc déclaré** : les diagnostics D1/D2/D3 et le re-test A3 ne figurent pas au
  pré-enregistrement, qui prévoyait un arrêt sec sur échec de K1. Ils ont été ajoutés pour établir
  la **nature** du kill, que la politique de ré-ouverture exige et que K1 seul ne détermine pas.
  Ils consomment N1 comme ci-dessus et sont rapportés en entier, résultats favorables inclus.
- **Verdicts** : REJECTED 16/18 · UNDERPOWERED 2/18 (UKOIL/USOIL, et AUDUSD/USDCAD **au net**).

## 9. Reproduction

`code/stage_a_halflife.py` (relevé 171 paires + L60 + stabilité de fréquence) ·
`code/stage_a2_diagnostics.py` (D1/D2/D3, gross gate, L25, L58) ·
`code/stage_a3_powered.py` (trades non chevauchants, bootstrap par blocs, L38) ·
`code/stage_b_strategy.py` (moteur intraday-flat, **écrit mais non exercé** — K1 a échoué avant).
Sorties dans `outputs/` (tables de résultats, aucun blob de données).

### 9.1 Incident de cache, et pourquoi les chiffres tiennent

Un second processus écrivait dans le répertoire de cache scratchpad pendant la construction, avec
un schéma de colonnes différent pour un contenu identique. Détecté par une erreur de schéma, pas
supposé. Réponse : reconstruction dans un répertoire privé, puis **vérification de provenance de
chaque série reconstituée contre le M1 source** — 6 séries recontrôlées bar à bar (EURUSD, US500,
AUDJPY, EURGBP, EURJPY, US100, GER40, XAUUSD, UKOIL), **écart absolu maximum = 0**. Le contenu est
déterministe à partir de `data/deep_history_utc/` ; seuls les noms de colonnes divergeaient, et le
lecteur est devenu tolérant aux deux schémas plutôt que de reconstruire 10 minutes de parsing.
