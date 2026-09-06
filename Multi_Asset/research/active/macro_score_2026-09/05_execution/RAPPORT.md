# Porte de faisabilité — Système de scoring macro cross-asset

**Date** : 2026-09-06
**Auteur** : quant risk / portfolio construction (session Claude Code)
**Statut** : pré-backtest — AUCUNE donnée téléchargée, AUCUN code écrit
**Portée** : ce document définit les seuils de passage, PAS le résultat d'un test empirique

---

## 0. Note de provenance (à lire avant tout le reste)

Cette session n'a pas pu relire directement `CLAUDE.md` (racine dépôt) ni `_meta/lessons_registry.md`
en cours de rédaction : les deux tentatives (Read, `cat`, `python3 open()`, `git show`, avec et sans
sandbox) ont échoué avec `Operation not permitted` — un blocage de permissions macOS sur l'arborescence
`Desktop/Algo_claude` existante (le dossier que j'ai moi-même créé pour ce livrable, lui, est accessible).
Ce n'était pas intermittent malgré sept tentatives réparties sur cinq méthodes différentes.

Ce rapport s'appuie donc sur deux sources fiables déjà présentes dans le contexte de la session :
1. le texte **intégral** de `CLAUDE.md` (projet) injecté au démarrage de la conversation, qui contient
   les hard rules, les seuils RESEARCH_PASS/PROPFIRM_PASS, la formule IC→Sharpe (Israel-Jiang-Ross) et
   le texte **verbatim** des leçons L51 à L60 ;
2. le texte **verbatim** de L36, L38, L43, L49, L53, L54, L55, L58, L64, L67 fourni explicitement dans
   la consigne de mission.

Je n'ai pas eu accès au texte complet de L61-L63, L65-L66 — je ne les cite donc pas et ne fabrique
aucun contenu à leur sujet. **Recommandation opérationnelle** : avant tout lancement de backtest sur
ce projet, relire ce document contre le registre complet dans une session ayant l'accès fichier, et
vérifier qu'aucune leçon L61-L66 ne mord sur les axes traités ici (elle serait alors à intégrer).

---

## 1. La porte de faisabilité chiffrée

### 1.1 Le cadre

Le toolkit méthodologique du dépôt fixe :

> `expected_gross_alpha ≈ 0.40 × IC × √breadth × σ_cible` ; exiger `gross > 3 × coût`.

Cette formule est une variante appliquée de la loi fondamentale de la gestion active de Grinold :
`IR = TC × IC × √BR`, où `TC` (transfer coefficient) capture tout ce qui dégrade le signal pur entre
la prévision et le portefeuille réellement implémentable (contraintes de position, coûts, retards
d'exécution, corrélations entre paris). **L67 est la leçon qui mord ici directement** : `BR` compte
des **paris indépendants**, jamais des observations calendaires, et `TC` **se mesure**, il ne se
suppose pas. Le `0.40` du toolkit est une valeur de référence de la littérature (Clarke/de Silva/
Thorley, Israel-Jiang-Ross), **pas une mesure de CE projet** — avant tout backtest, il doit être traité
comme une hypothèse à falsifier, pas un fait acquis. Je fais donc le calcul sur une fourchette de TC
(0.25 / 0.30 / 0.40) plutôt que sur la seule valeur du toolkit.

Puisque `gross_alpha = SR_gross × σ_cible` (l'alpha brut est réalisé à la même vol que le budget de
risque alloué), la porte se réduit à :

```
SR_gross ≈ TC × IC × √BR
IC_requis(SR_cible) = SR_cible / (TC × √BR)
```

### 1.2 Sens (a) — IC plausible de la littérature ⟶ Sharpe espéré

Pour un score macro cross-asset (prévision de rendement à partir de surprises macro / momentum de
cycle / spread de croissance-inflation entre pays), la littérature quantamental documente typiquement
des IC **hors coûts, en échantillon** de l'ordre de **0.02 à 0.08** pour un signal cross-sectionnel
mensuel ; des valeurs au-delà de ~0.10 sont presque toujours des artefacts de fenêtre courte, de
look-ahead ou de sur-ajustement (cf. discipline DSR/AMTP du dépôt). Je retiens une fourchette
IC ∈ {0.02, 0.04, 0.08} (faible / centrale / agressive-haute).

`BR` (paris indépendants par an) est établi honnêtement en §2 : fourchette défendable **2 à 15/an**,
centrale ≈ **6**. σ_cible = 10 %/an (budget de vol typique d'un book macro cross-asset, cohérent avec
les contraintes de drawdown propfirm et inférieur au 18 % utilisé pour la crypto mono-classe de la
Stratégie A).

| TC | IC | BR | SR_gross | Commentaire |
|---|---|---|---|---|
| 0.30 | 0.04 | 6 | **0.029** | scénario central, réaliste |
| 0.30 | 0.04 | 15 | 0.047 | BR optimiste, IC centrale |
| 0.30 | 0.08 | 6 | 0.059 | IC agressive-haute, BR centrale |
| 0.40 | 0.08 | 15 | **0.124** | scénario le plus optimiste défendable |
| 0.40 | 0.08 | **240 (naïf, FAUX)** | **0.496** | 20 instruments × 12 mois comptés comme 240 paris indépendants |

La dernière ligne est intentionnelle : c'est la démonstration que **compter la breadth naïvement
fabrique un Sharpe brut qui a l'air presque investissable (0.50, proche du RESEARCH_PASS 0.7)**, alors
que la même hypothèse, honnêtement comptée (BR=15), donne 0.124 — un ordre de grandeur en dessous.
C'est exactement le sens de L67 : la breadth est l'endroit où un projet se ment le plus facilement à
lui-même, avant même d'avoir écrit une ligne de backtest.

**Conclusion (a)** : même dans le scénario le plus optimiste défendable (IC=0.08, TC=0.40, BR=15),
`SR_gross ≈ 0.12`, très en dessous du seuil RESEARCH_PASS (0.7) et a fortiori de PROPFIRM_PASS (1.0).
Le scénario central (IC=0.04, BR=6) donne 0.03 — un signal économiquement nul avant même le premier
bps de coût.

### 1.3 Sens (b) — Sharpe cible ⟶ IC requis

En inversant pour atteindre RESEARCH_PASS (SR=0.7) :

| BR | TC | IC_requis | Crédible ? |
|---|---|---|---|
| 6 (central) | 0.35 | **0.816** | Non — aucun signal macro documenté n'approche cette valeur |
| 15 (optimiste) | 0.40 | **0.452** | Non — 5 à 20× les IC macro académiques typiques |
| 240 (naïf, FAUX) | 0.40 | 0.113 | Limite haute de crédibilité, et seulement en trichant sur BR |

Le résultat est sans ambiguïté : sous **n'importe quelle** hypothèse de breadth honnêtement comptée,
l'IC requis pour franchir même le gate le plus bas (RESEARCH_PASS, pas PROPFIRM_PASS) est hors de
portée de tout signal macro documenté dans la littérature académique ou propriétaire connue. Même en
acceptant la breadth **fausse** (compter chaque instrument-mois comme un pari indépendant), l'IC
requis (0.113) reste au bord extrême de la crédibilité — et ce chiffre-là est précisément celui que le
toolkit du dépôt cite pour un **ETF daily à 0.10 % RT** (IC>0.08), un contexte de fréquence et de
breadth réelle sans rapport avec un score macro mensuel.

**Le gate IC→Sharpe est, à lui seul, la raison suffisante de douter du projet — avant tout calcul de
coût.** Le point (3) ci-dessous montre que le coût n'est presque plus pertinent : à SR_gross≈0.03-0.06,
l'alpha brut annualisé n'est que de 0.3 à 0.6 %/an à 10 % de vol cible — un montant que même le
véhicule le moins cher (futures IBKR, ~0.4 bps RT) suffit à absorber, mais qui est de toute façon trop
petit pour justifier l'exercice.

---

## 2. La comptabilité honnête de la breadth

### 2.1 Pourquoi le calendrier ment

La tentation naturelle : univers de N=20 instruments macro (FX G10, taux, indices, matières
premières), rebalancé 12 fois/an ⇒ « 240 paris indépendants ». **C'est la faute exacte que L67
proscrit.** Deux effondrements se combinent, un cross-sectionnel et un temporel.

### 2.2 Effondrement cross-sectionnel — la corrélation inter-pays et le facteur dollar commun

Formule de la taille effective sous corrélation équicorrélée (N actifs, corrélation moyenne ρ) :

```
N_eff = N / (1 + (N-1)·ρ)
```

Les cycles macro des économies développées sont fortement co-mouvants, en particulier depuis le cycle
QE/pandémie synchronisé post-2020 (corrélation moyenne des surprises de croissance/inflation entre
pays du G10 souvent ρ ≈ 0.4-0.6 sur la dernière décennie) :

| N (pays) | ρ | N_eff |
|---|---|---|
| 10 | 0.5 | **1.82** |
| 10 | 0.3 | 2.70 |
| 20 | 0.3 | 2.99 |
| 20 | 0.15 (optimiste, multi-classes) | 5.19 |

À cela s'ajoute le **facteur dollar commun** sur tout univers FX : une analyse en composantes
principales du G10 FX montre typiquement une PC1 (facteur USD) expliquant 40-60 % de la variance —
c'est-à-dire que la plupart des paires ne sont pas des paris indépendants mais des expressions
différentes d'un seul pari USD. C'est la signature exacte mesurée en L55 (le FX porte 53 % du
notionnel d'un book macro mixte pour une contribution P&L négative) : compter 9 paires USD comme 9
paris revient à compter le même pari neuf fois avec des poids de notionnel différents.

**Conclusion 2.2** : la breadth cross-sectionnelle honnête d'un univers macro de 10-20 instruments
n'est pas 10-20, elle est de l'ordre de **2 à 5** paris réellement indépendants.

### 2.3 Effondrement temporel — le noyau de décroissance lente

Un score macro s'appuie nécessairement sur des fenêtres de plusieurs mois (les cycles de
croissance/inflation ne se déplacent pas en jours). Pour un noyau de demi-vie `h` (mois), l'
autocorrélation mensuelle AR(1) implicite est `φ = 0.5^(1/h)`, et le nombre d'observations
indépendantes effectives par an (T=12 obs/an) :

```
N_eff_temps ≈ 12 × (1-φ)/(1+φ)
```

| Demi-vie du noyau | φ (mensuel) | Paris indépendants/an |
|---|---|---|
| 1 mois (rapide) | 0.500 | 4.00 |
| 3 mois | 0.794 | 1.38 |
| 6 mois (typique macro) | 0.891 | **0.69** |
| 12 mois | 0.944 | 0.35 |

C'est la même signature que **L12b** (ETH netflow, demi-vie>30j ⇒ N_eff≪N, HAC déflaté à 0.11) —
sauf qu'ici on ne peut même pas invoquer un noyau plus rapide pour s'en sortir : **la donnée macro
sous-jacente elle-même n'apporte de l'information réellement nouvelle qu'à la fréquence de
publication** (CPI/PMI mensuels, GDP trimestriel), et les publications consécutives sont elles-mêmes
autocorrélées (un PMI ne surprend pas indépendamment d'un mois à l'autre en général). Choisir un noyau
rapide ne fabrique pas de l'information — il fait juste du bruit de réaction plus fréquent sur la même
information lente, ce qui **gonfle artificiellement N_eff sans gonfler l'IC réel**. Le calcul honnête
retient un noyau réaliste de 3-6 mois ⇒ **0.7 à 1.4 pari temporel indépendant par an, par pari
cross-sectionnel**.

### 2.4 Breadth combinée

```
BR/an ≈ N_eff_cross-sectionnel × N_eff_temporel/an
```

| Scénario | N_eff cross | N_eff temps | BR/an |
|---|---|---|---|
| Pessimiste | 2 | 0.7 | **1.4** |
| Central | 3 | 1.4 | **4.2** |
| Optimiste (nécessite ρ faible ET noyau rapide simultanément — peu crédible) | 5 | 4.0 | 20 |

**Fourchette défendable retenue : 2 à 15 paris indépendants par an, valeur centrale ≈ 5-8.** Le
scénario « optimiste » à 20 exige de supposer SIMULTANÉMENT une faible corrélation inter-pays (contredit
par le cycle macro synchronisé documenté) ET un noyau de décision rapide (contredit par la cadence de
publication et l'autocorrélation des surprises macro elles-mêmes) — cumuler ces deux hypothèses
optimistes n'est pas défendable, seulement l'une ou l'autre isolément. C'est pourquoi §1 retient BR=6
au centre et BR=15 comme borne haute déjà généreuse, jamais BR=240.

---

## 3. La matrice de véhicule — AVANT le backtest (L53)

Rappel L53 : la matrice de véhicule se résout en 5 minutes de calcul et passe **avant** toute
simulation — si la marge du lot minimum tient dans le capital personnel, le propfirm n'apporte rien ;
et le véhicule détermine à lui seul quelles fréquences de rebalancement sont même envisageables.

| Véhicule | Coût RT mesuré | Coût de portage | Granularité min. | Capital requis | Fréquences viables |
|---|---|---|---|---|---|
| **CFD FTMO** | ~2.48 bps (mesuré, cf. L34) | Swaps **asymétriques**, ex. US100 long −3.31 bps/nuit (L30) ; agrégé sur un book multi-actifs ≈ 6.75 %/an (L36) | 0.01 lot | faible (compte challenge) | **intraday-flat ou événementiel seulement** — toute tenue multi-jours percute L36 de plein fouet |
| **CFD Eightcap** | ~0.75 bps EURUSD | Swap/rollover **non mesuré dans ce dépôt** — à vérifier avant toute hypothèse (esprit L52 : ne jamais faire confiance au nom d'un champ provider) ; pas d'accès futures CME | 0.01 lot | faible | FX uniquement ⇒ réduit directement la breadth de §2 à un seul facteur USD (aggrave 2.2) ; tenue courte à moyenne SI le swap se révèle mesuré favorable, jamais supposé |
| **Futures IBKR** | ~0.4 bps (gros contrats) | Aucun swap CFD ; portage = coût d'opportunité de marge uniquement | **1 lot entier** (pas de fractionnement) | ES ~$250k notionnel, ZN ~$110k, minis (MES/MNQ/MGC/M2K) ~$5-15k | **mensuel/trimestriel** — seule fréquence cohérente avec la cadence de publication macro (§2.3), et coût quasi nul à cette fréquence (cf. note toolkit dépôt : « monthly-rebal breadth~12 : cost gate essentially absent ») |

### 3.1 Le conflit qui tue le véhicule CFD pour un score macro tenu

Un score macro, par construction, réagit à des données publiées mensuellement/trimestriellement — la
fréquence naturelle de rebalancement est donc **mensuelle**, pas intraday. Or **L36 a déjà mesuré** que
le portage overnight agrégé (~6.75 %/an) annule intégralement une prime de trend multi-actifs de
~8 %/an tenue sur CFD. Un score macro tenu sur FTMO (ou probablement Eightcap, swap non vérifié) meurt
donc **exactement au même endroit**, avant même d'arriver à la question de l'IC. La seule façon de
faire survivre un signal macro sur véhicule CFD est de le transformer en signal **événementiel /
intraday-flat** (fenêtre courte autour d'une publication, zéro swap) — ce qui change radicalement la
nature du projet (voir §6).

### 3.2 Le conflit qui tue la breadth sur futures IBKR

Futures IBKR est le seul véhicule cohérent avec une tenue mensuelle sans portage prohibitif — mais la
hard rule **N ≥ 30 instruments pour les stratégies cross-sectionnelles** entre en collision frontale
avec la granularité 1-lot : à un capital personnel de l'ordre de 12-15 k€ (profil du dépôt), diversifier
sur 20-30 futures macro à 1 lot chacun est **arithmétiquement impossible** sauf à se limiter aux minis
(MES/MNQ/MGC/M2K/MYM — qui ne couvrent qu'une poignée de classes d'actifs, aucun FX EM, peu de matières
premières agricoles), ou à accepter une concentration à quelques lots (ce qui, par L57, dégrade le skew
et ouvre une queue de perte mono-séance — mesuré ailleurs dans ce dépôt à −18.4 % sur une seule
séance pour une sleeve forcée à 1 lot). **Sur futures IBKR, soit le projet respecte N≥30 et le capital
ne suffit pas, soit il respecte le capital et casse la hard rule N≥30** — ce doit être tranché
explicitement, pas découvert après coup.

**Verdict de véhicule (avant tout backtest)** : aucun des trois véhicules ne permet, à capital
personnel réaliste, un score macro cross-sectionnel **tenu mensuellement sur N≥30 instruments**. Le
CFD meurt au portage (L36), les futures meurent à la granularité/capital (L53+L57) face à la hard rule
N≥30. Cette conclusion est indépendante de la qualité du signal et devrait, seule, suffire à reformuler
le projet avant tout écriture de backtest (voir §6).

---

## 4. Le test de β-orthogonalité pré-enregistré (L38)

**À écrire et figer AVANT de voir le moindre rendement du score macro.**

### 4.1 Spécification du benchmark

Benchmark = un portefeuille long-only, vol-ciblé à 10 %/an, composé à parts de risque égales de :
`[future S&P front, future 10Y UST front, future Bloomberg Commodity front]`, rebalancé à la même
fréquence que le score macro. Ce choix capture le « risk-on/risk-off » générique qu'un score macro
long-biaisé reproduit presque toujours mécaniquement (un score qui surpondère les actifs risqués
quand la macro s'améliore achète le marché, point).

### 4.2 Régression

```
R_book(t) = α + β · R_benchmark_vol_target(t) + ε(t)
```
HAC Newey-West, lag conforme au noyau de décroissance retenu en §2.3 (pas lag-6 générique par défaut
si le noyau est plus lent — l'aligner sur la vraie mémoire du signal).

### 4.3 Critère de passage/échec — figé maintenant

- **β significatif (|t|>2.5) ET R² > 30 % ⇒ ÉCHEC.** Reclassification automatique : ce n'est pas une
  prime macro structurelle, c'est du market-timing sur beta (L38 verbatim : « R² > 30 % ⇒ pas
  orthogonal, c'est du timing sur beta »).
- **R² ≤ 30 % ⇒ passe cette étape**, mais reste soumis au placebo apparié (§4.4) avant toute conclusion.

### 4.4 Stabilité du β dans le temps — rupture ESTIMÉE, jamais imposée (L64)

Refaire la régression sur deux sous-périodes séparées par une rupture **estimée** (Bai-Perron ou
CUSUM sur la série de β roulant), jamais une date choisie a priori (ex. « 2020 », « avant/après COVID »
imposée sans test). Un β qui change de signe ou d'ampleur à travers la rupture estimée n'est pas une
preuve d'alpha stable — c'est une preuve de beta conditionnel au régime, une variante toujours pas
orthogonale du même problème.

### 4.5 Condition croisée avec L54

Si le projet évolue vers un usage « overlay de régime » plutôt que directionnel pur (voir §6), la
condition liante n'est PAS le MaxDD mais la condition L54 : le régime identifié par le score doit
prédire la **moyenne** dans le même sens que la **variance**. Test explicite à pré-enregistrer :
comparer le rendement moyen conditionnel aux régimes « haute vol selon le score » contre les régimes
« basse vol selon le score » — si le book gagne davantage précisément dans les régimes que le score
signale comme risqués, toute coupe de risque sur ce signal retranche les jours qui paient, exactement
la faillite déjà mesurée sur le book MONO déployé (L54).

---

## 5. Critères d'arrêt pré-enregistrés — chiffrés, non négociables après coup

1. **Kill IC/breadth (mécanique)** — l'IC mesuré (cross-sectionnel ou temporel selon le mécanisme du
   score) a un IC95 contenant zéro après N_eff ≥ 30 paris indépendants **comptés selon §2** (jamais en
   mois calendaires) ⇒ **ABANDON**, classé « mécanique » dans la politique de réouverture — ne jamais
   rouvrir sans angle explicitement nouveau.
2. **Kill β-orthogonalité (L38)** — R² du benchmark de §4 > 30 % sur l'échantillon complet ⇒
   reclassification en étude de beta-timing, pas d'alpha ; si en plus la condition L54 échoue (le
   régime ne prédit pas la moyenne dans le même sens que la variance) ⇒ **arrêt total**, aucune valeur
   d'overlay non plus.
3. **Kill coût/véhicule (L53/L36)** — le Sharpe brut honnête (§1) ne dépasse pas 3× le coût du véhicule
   **le moins cher réellement faisable à la fréquence requise** (§3) ⇒ **ABANDON** sur le coût, quelle
   que soit la qualité apparente de l'IC. Rouvrable seulement si un véhicule matériellement moins cher
   apparaît (catégorie « véhicule », rouvrable par la politique du dépôt).
4. **Kill placebo (L49/L58)** — tout résultat positif doit battre un placebo apparié (même structure
   d'autocorrélation, même calendrier), dont la baseline est elle-même validée contre l'espérance
   inconditionnelle avant d'être utilisée comme contrôle. Un placebo dont la baseline dévie de plus de
   ~20 % relatif de l'espérance inconditionnelle est un placebo biaisé — le re-concevoir avant de
   relancer le test principal, jamais conclure PASS sur un placebo compromis.
5. **Kill granularité/capital (L53/L57)** — si respecter N≥30 sur le véhicule retenu exige de se
   concentrer sur moins de 10 positions à lot unique effectif ⇒ soit **ABANDON** sur le véhicule, soit
   **rétrogradation explicite et documentée** vers un régime « conviction restreinte » à N plus petit —
   jamais poursuivre silencieusement comme si la hard rule N≥30 était respectée.
6. **Kill n_tests/AMTP** — si franchir la porte exige plus de 3 modifications de l'hypothèse (hard
   rule), ou si la taille de la grille explorée (méthode variantes exhaustives) pousse le seuil
   AMTP/DSR au-delà de ce qui est atteignable compte tenu de la breadth honnête de §2 ⇒ **ABANDON**,
   ne pas continuer à tourner la grille en espérant une cellule survivante.
7. **Règle d'arrêt en amont, avant même le point 1** : si à ce stade — avant tout backtest — aucune
   hypothèse unique et pré-enregistrable ne peut afficher un IC plausible **> 0.15-0.20**, seuil sous
   lequel le calcul de §1(b) montre que la porte ne peut être franchie sous AUCUNE hypothèse de breadth
   crédible, **ne pas lancer le backtest du tout**. C'est le critère qui s'applique dès maintenant à ce
   projet (voir verdict §6).

---

## 6. Verdict honnête

**Sous sa forme actuellement proposée — un score macro cross-sectionnel, tenu sur plusieurs
semaines/mois, sur un univers de type N≥30 — ce projet n'a pas de chance, et le raisonnement s'effondre
en trois endroits indépendants, chacun suffisant seul :**

1. **Le gate IC→Sharpe (§1)** : sous la breadth honnêtement comptée (§2, BR≈2-15, jamais 240),
   franchir même RESEARCH_PASS (0.7) exige un IC de 0.45 à 0.82 — hors de portée de tout signal macro
   documenté (0.02-0.08 typique). Le seul scénario où l'IC requis descend à une zone à peu près
   discutable (0.11) exige de compter la breadth de façon fausse (calendrier × instruments), exactement
   l'erreur que L67 proscrit.
2. **Le véhicule (§3)** : aucun des trois véhicules candidats ne supporte, à capital personnel
   réaliste, une tenue mensuelle sur N≥30 instruments. CFD meurt au portage agrégé (L36, déjà mesuré
   sur une classe d'actifs analogue) ; futures IBKR meurt à la granularité 1-lot face à la hard rule
   N≥30 (L53+L57). Ce verdict est indépendant du signal.
3. **Le risque de beta déguisé (§4)** : même si (1) et (2) étaient franchis, un score macro long-biaisé
   a une probabilité a priori élevée d'échouer le test R²>30 % (L38) — c'est la signature structurelle
   de toute stratégie qui « achète le risque quand la macro va bien ».

**Où le raisonnement meurt précisément** : à la comptabilité de la breadth (§2). C'est le nœud —
tout le reste (véhicule, orthogonalité, coût) est secondaire tant que l'IC requis reste à 5-10× l'IC
macro documenté dans la littérature.

**Forme qui pourrait survivre — et sur quel véhicule.** Ce dépôt a déjà, en recherche active, un
candidat vivant dans une famille structurellement différente : un signal **événementiel**, ancré à une
publication macro connue (XAUUSD veille de CPI, t=3.86, gross/coût 20.7, DSR 0.637, N=65 trades —
research active du dépôt). Cette famille survit précisément parce qu'elle échappe aux trois points de
rupture ci-dessus :
- **Breadth honnête et petite par construction** : le nombre de paris est le nombre de publications
  CPI par an (≈12), pas un univers de 20-30 instruments — pas d'illusion de N≥30, pas de tentation de
  gonfler la breadth.
- **Fenêtre courte, intraday ou quasi** : pas de portage tenu, donc L36 ne s'applique pas — véhicule
  CFD (FTMO) redevient viable puisque c'est précisément le régime « intraday-flat » qui l'épargne.
- **Signal événementiel non directionnel-macro-continu** : moins susceptible d'être du beta de marché
  déguisé qu'un score qui pondère en continu des actifs risqués selon le cycle macro.

**Recommandation** : ne pas construire un nouveau « score macro cross-asset » au sens où la mission le
pose. Recentrer l'ambition sur **l'extension de la famille événementielle déjà validée** (plus
d'événements macro type CPI/PMI/emploi, testés un par un, sur le véhicule le moins cher disponible pour
chaque instrument — futures IBKR quand accessible, sinon CFD en fenêtre courte), plutôt que sur un book
tenu. Un usage résiduel envisageable mais **non prioritaire et à faible probabilité de succès** :
overlay de sizing sur un book déjà validé (ex. Stratégie A ou le book bond-month-end), sous la
condition stricte et pré-enregistrée de L54 (§4.5) — à tester seulement après épuisement de la piste
événementielle, jamais comme point de départ.

---

## Résumé (≤15 lignes)

Porte IC→Sharpe (IR=TC×IC×√BR, L67) : sous breadth honnêtement comptée (§2 : corrélation inter-pays +
facteur USD + noyau lent macro ⇒ **2 à 15 paris indépendants/an**, pas 240), franchir RESEARCH_PASS
(0.7) exige un IC de **0.45 à 0.82** — hors de portée de tout signal macro documenté (0.02-0.08
typique). Même en comptant la breadth naïvement (faux), l'IC requis reste à 0.11, au bord extrême.
Véhicule (§3, L53) : aucun des trois (FTMO ~2.48bps+swap asymétrique, Eightcap ~0.75bps FX-only,
IBKR futures ~0.4bps mais 1-lot) ne permet une tenue mensuelle sur N≥30 instruments à capital
personnel — CFD meurt au portage agrégé (L36), futures meurt à la granularité (L57) contre la hard
rule N≥30. β-orthogonalité (L38) pré-spécifiée : R²>30 % sur benchmark risk-on/risk-off vol-ciblé ⇒
reclassification en beta-timing. Six critères d'arrêt chiffrés posés (§5), dont un qui s'applique
déjà : sans IC pré-enregistrable >0.15-0.20, ne pas backtester. **Verdict : NON pour un score macro
tenu cross-sectionnel — le raisonnement meurt à la breadth (§2), redondé par le véhicule (§3).**
Forme qui survivrait : signal **événementiel intraday-flat** ancré à une publication (famille déjà
vivante dans le dépôt, XAUUSD pré-CPI, t=3.86) — étendre celle-là, pas construire un nouveau book.
Note : `_meta/lessons_registry.md` et `CLAUDE.md` racine illisibles cette session (permission OS) —
rapport bâti sur le texte déjà en contexte + citations verbatim fournies dans la mission.
