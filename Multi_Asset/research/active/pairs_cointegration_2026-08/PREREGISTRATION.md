# PRÉ-ENREGISTREMENT — Pairs trading / cointégration sur véhicule FTMO CFD

**Ouvert 2026-08-03. Écrit AVANT toute mesure.** Branche `claude/pairs-cointegration`.
Compteur **N1 local = 0** à l'ouverture (famille neuve — aucun essai de cette famille dans
`research_history.md` ni dans le registre L).

Interpréteur : `/usr/bin/python3` explicitement.
Données : `<HOME>/Desktop/Algo_claude/data/deep_history_utc/` (M1 vrai UTC),
lecture seule, resamplées M5 dans un cache scratchpad **jamais committé**.
`data/panels/m5_indices/` est **interdit** (EET étiqueté `timestamp_utc`).

---

## 1. L'objectif de décision, écrit en premier

Ce n'est pas « trouver un edge ». C'est **passer un FTMO 2-step (+10 % puis +5 %)**.
Ordre des métriques : **p(pass)** → **durée** → **EV par unité de temps**. Une variante à Sharpe
inférieur mais plus rapide gagne. Le Sharpe est du contexte, pas un critère.

Barrières : daily **−5 %** du solde d'ouverture appliqué à l'**équité intraday** ; floor
**STATIQUE −10 %** du capital initial. Fait mesuré sur ce livre : **80.2 % des morts sont des
franchissements de la barrière journalière** ⇒ c'est la **queue gauche intra-journalière** qui
décide, pas le Sharpe.

Conséquence de conception, écrite avant la donnée : une sleeve de paires n'a d'intérêt ici que si
elle est **rapide** (beaucoup de trades courts ⇒ le +10 % s'atteint en semaines, pas en trimestres)
et **à queue gauche courte** (pas de position ouverte pendant un décrochage de cointégration).
Ces deux exigences pointent la même variable : la **demi-vie de retour**.

---

## 2. La contrainte qui décide de la famille — posée avant de concevoir

Une paire CFD est **deux jambes TENUES**. Elle paie le markup de financement **deux fois** :
mesuré sur ce desk ≈ **1.5 bps/nuit** (L28). Un spread à demi-vie de plusieurs jours est **mort
avant d'être testé** : un retour en 10 jours coûte ~15 bps de portage pour un edge qui en vaut
quelques-uns.

⇒ **La seule branche vivable est intraday-flat : demi-vie DANS la séance, zéro nuit.**

La **demi-vie de retour est la variable de conception n°1**. Elle est mesurée AVANT tout signal,
et c'est elle qui décide de l'horizon — pas l'inverse. Une paire à demi-vie de 3 jours ne reçoit
pas de stratégie : elle reçoit un verdict.

**La table des demi-vies mesurées est le livrable structurant de ce dossier, PASS ou non.**

Rappel L27 : **market-neutral par construction ≠ two-sided en spread**. Un spread cointégré hérite
d'un drift relatif ; il doit passer K4 comme n'importe quelle autre sleeve.

---

## 3. Mécanisme économique — pourquoi ceci pourrait exister

Deux instruments partageant un facteur commun dominant (même sous-jacent à deux points de
livraison ; deux indices actions du même bloc ; deux croisées FX partageant une jambe) sont cotés
par des **flux d'ordres partiellement segmentés** : heures de marché différentes, participants
dominants différents, teneurs de marché différents. Un déséquilibre de flux transitoire dans une
jambe la déplace **relativement** à l'autre ; le pricing par facteur commun la rappelle.

La **fenêtre de vie** de cet écart est le temps qu'il faut à l'arbitragiste marginal pour le
refermer — en 2026, sur des instruments listés et liquides, ce temps est **court** (minutes à
heures), pas long. C'est précisément l'hypothèse qui rend la famille *a priori* compatible avec la
contrainte §2 — et c'est ce que la mesure doit trancher.

**Ce que le mécanisme ne dit PAS** : il ne prédit pas que l'amplitude de l'écart dépasse le coût.
Un écart qui se referme en 20 minutes mais qui vaut 0.5 bps est un vrai phénomène et une fausse
stratégie. K2 sépare les deux.

---

## 4. Univers — figé ici, non extensible après mesure

19 séries, coût RT mesuré acceptable (`Multi_Asset/research/active/cost_denominator_2026-07/COST_AUDIT.md`) :

| classe | instruments |
|---|---|
| FX (10) | EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, EURGBP, EURJPY, AUDJPY |
| indices (4) | US500, US100, US30, GER40 |
| métaux (3) | XAUUSD, XAGUSD, COPPER |
| énergie (2) | UKOIL, USOIL |

**Exclus définitivement** (coût RT mesuré, §4 du COST_AUDIT) : COCOA 1189 bps, NGAS 300, COTTON
282, SOYBEAN 153, SUGAR 144, COFFEE 142, + OJUICE/DIESEL (même classe, non mesurés).

### 4.1 Deux étages distincts, à ne pas confondre

**Étage A — relevé de demi-vies (DESCRIPTIF, N0, ne consomme AUCUN essai).**
Les **C(19,2) = 171** paires sont mesurées et **rapportées intégralement** (pas de top-k).
C'est une carte du terrain, pas un test d'hypothèse : aucune décision de trading n'en sort
directement.

**Étage B — tests de stratégie (consomme N1).**
Seules les paires qui (i) passent K1 **et** (ii) appartiennent à un **groupe économique
pré-enregistré ci-dessous** reçoivent une stratégie. Interdiction explicite de promouvoir une
paire au seul motif qu'elle sort bien du relevé de demi-vies — ce serait du HL-mining.

### 4.2 Groupes économiques pré-enregistrés (mécanisme nommé AVANT la donnée)

| # | groupe | paires | facteur commun revendiqué |
|---|---|---|---|
| G1 | Brent/WTI | UKOIL–USOIL | même brut, deux points de livraison |
| G2 | métaux précieux | XAUUSD–XAGUSD | même actif monétaire réel |
| G3 | indices US | US500–US100, US500–US30, US100–US30 | même marché actions US |
| G4 | US–Europe | US500–GER40, US100–GER40, US30–GER40 | beta actions global |
| G5 | triangulaires EUR/GBP | EURUSD–GBPUSD, EURUSD–EURGBP, GBPUSD–EURGBP | identité triangulaire |
| G6 | triangulaires JPY | USDJPY–EURJPY, USDJPY–AUDJPY, EURJPY–AUDJPY | jambe JPY partagée |
| G7 | dollar-bloc | AUDUSD–NZDUSD, AUDUSD–USDCAD | devises matières premières |
| G8 | EUR-jambe croisée | EURUSD–EURJPY, EURUSD–USDCHF | jambe EUR / substitut EUR |

**24 paires** à l'étage B. Aucun autre groupe ne sera ajouté après la première mesure.

---

## 5. Kill rules — chiffrées, engagées avant la donnée

**K1 — Porte de demi-vie (la porte de véhicule).**
Demi-vie OU du résidu M5, estimée sur fenêtres de formation glissantes, médiane inter-fenêtres.
- HL_med ≤ **24 barres M5 (2 h)** → INTRADAY-VIABLE, passe à K2.
- **24 < HL_med ≤ 96 barres (8 h)** → MARGINAL : ne passe que si K2 est franchi avec **marge ≥ 2×**.
- HL_med > **96 barres (8 h = une séance)** → **REJECTED-ON-VEHICLE**. Aucune stratégie construite.
  C'est le kill L28 : 3 demi-vies pour converger ⇒ ≥ 1 nuit tenue ⇒ ≥ 1.5 bps de portage sur deux
  jambes, contre un edge qui en vaut quelques-uns.

**K2 — Pré-vol amplitude / coût (forme L43).**
`gross_par_trade_bps = z_entry × σ_résidu_bps` (déviation capturée de z_entry vers 0)
`coût_par_trade_bps = coût_RT(A) + coût_RT(B)` — **deux jambes**, entrée ET sortie comprises.
Porte : **gross / coût ≥ 1.5**. En dessous → **REJECTED-ON-COST**.
Coûts employés : indices ~1.8 bps RT (queue 2.9 provisionnée), XAUUSD 1.84 (queue 3.88), FX selon
COST_AUDIT §2 — **et jamais la colonne `spread` seule** (US30 79.7/100/74.9 % de barres nulles en
2019/2020/2021 ; EURUSD 33 % de jours nuls).

**K3 — Gate au GROSS d'abord.** Tout est d'abord tourné à `cost_rt = 0`. Si l'effet n'existe pas à
coût nul (moyenne ≤ 0 ou t_HAC lag-6 ≤ 2.5), il n'existe pas → **REJECTED-MECHANICAL**, et aucun
réglage de coût n'est tenté.

**K4 — L25 two-sided à jambes DISJOINTES.** Les trades « spread long » et « spread short » forment
**deux échantillons disjoints de trades**, jamais l'un l'opposé de l'autre. Les deux moyennes
doivent être positives ; le côté faible doit avoir **t ≥ 1.0**. Échec → REJECTED (beta déguisé).

**K5 — L38 β-orthogonalité.** Régression du P&L quotidien de la paire sur (a) un buy-and-hold
vol-targeté de chaque jambe, (b) le porteur du livre live (or). **R² > 30 %** sur l'un des trois
⇒ pas une sleeve neuve.

**K6 — L58 baseline inconditionnelle appariée à l'état.** Comparaison à l'espérance
inconditionnelle de **la même forme de trade** (même heure d'entrée, même durée de détention,
mêmes instruments), tirée du **même pool d'état** — pas une moyenne pleine fenêtre : la baseline
dérive avec l'état, et un blackout ou un filtre peut pousser le pool dans un creux (leçon L58).
Contrôle à coût nul : la moyenne du pool placebo doit égaler l'espérance inconditionnelle.

**K7 — L59 delay+1 sur l'ENTRÉE **et** la SORTIE.** Entrée à la barre SUIVANT la barre de signal.
Sorties : toute sortie sur seuil est repricée au **pire** entre le niveau et l'ouverture de la
barre suivante (25 % des barres de stop ouvrent au-delà, mesuré). Les sorties temporelles sont
repricées à la clôture de la barre suivante.

**K8 — Placebo à autocorrélation appariée (décalage circulaire).** Mesuré sur ce desk : une série
de moyenne **strictement nulle** mais persistante sur 10 jours rend **Δp(pass) = +0.1495**. La
persistance seule achète de la probabilité de passage. Tout p(pass) rapporté sans ce contrôle ne
vaut rien. Porte : Δp(pass) réel > **p95 du placebo**.

**K9 — Anti-look-ahead de cointégration.** La fenêtre de **formation** ne touche JAMAIS la fenêtre
de **trading** (l'erreur classique de cette famille). Hedge ratio, paramètres OU et seuils sont
estimés sur la formation seule, appliqués hors échantillon. Walk-forward **≥ 5 folds** (règle dure).

**K10 — DSR** via `dsr.py` racine (corrigé), avec `estimate_std_sr_trials`.
⚠ `top10_test/framework.py:131` et `ftmo_lab.py:232` sont **CASSÉES** (σ_SR absent) — non utilisées.

**K11 — L60 barres à fourchette nulle**, par série et par année, sur le M1 source. Toute
série-année à **> 20 %** de barres `high==low` est exclue de l'analyse pour cette année.

**Bootstrap** : par blocs (Politis-Romano / stationnaire), **jamais iid**.

---

## 6. Ce qui sera comparé — méthode, pas catalogue

Quatre familles d'estimation, comparées sur les MÊMES fenêtres :

| id | sélection / hedge ratio | seuils |
|---|---|---|
| M1 | distance (Gatev) sur prix normalisés, ratio 1:1 en normalisé | z-score, seuils fixes |
| M2 | Engle-Granger, β OLS **statique** par fenêtre de formation | z-score, seuils fixes |
| M3 | β **dynamique** (Kalman / OLS glissant) | z-score, seuils fixes |
| M4 | OU ajusté sur le résidu (κ, μ, σ) | seuils **optimaux par temps de premier passage**, maximisant l'**EV par unité de temps** — critère identique à l'objectif §1, pas un réglage à la main |

Johansen n'est ajouté que si un groupe à ≥3 jambes atteint l'étage B (aucun n'est pré-enregistré
comme tel ⇒ hors périmètre par défaut).
Copules : **hors périmètre de ce dossier**, et le dire ainsi plutôt que de les bricoler — elles
changent la forme de la dépendance, pas la demi-vie, et c'est la demi-vie qui gouverne ici (§2).

**Stabilité de la relation** : le vrai tueur du pairs trading n'est pas le paramétrage mais la
**rupture de cointégration**. Elle est mesurée explicitement — fraction de fenêtres de formation
où la cointégration tient, et stabilité **inter-régime** de la vitesse de retour κ.

---

## 7. Comptabilité et vocabulaire

- **N1 local = 0** à l'ouverture. Étage A (171 paires) = **N0 descriptif, 0 essai consommé**.
- Un essai = une cellule (paire × méthode × configuration) atteignant K3.
- Le nombre exact de paires et de cellules est rapporté dans RESULTS.md.
- Verdicts à trois valeurs : **PASS** / **REJECTED** / **UNDERPOWERED**.
  Un **UNDERPOWERED ne consomme pas le budget** (IC contenant zéro sur échantillon court ≠ rejet).
- Budget de modifications : **3 maximum** (règle dure), 0 consommée à l'ouverture.

## 8. Conditions d'abandon anticipé (engagement)

Si l'étage A montre qu'**aucune** des 24 paires de l'étage B n'a de demi-vie ≤ 96 barres M5, le
dossier s'arrête là et rend un **négatif de véhicule** documenté. Aucune stratégie ne sera
construite pour « voir ». C'est le cas de sortie le plus probable *a priori*, et il est écrit ici
pour qu'il ne puisse pas être renégocié après coup.

## 9. Interdits opérationnels

- Aucun blob de données dans git.
- Aucun chemin live touché : `ftmo_live/`, `strategies/`, `Futures/live/`, `Portfolio/`,
  `.github/`, `*.mq5`. `Portfolio/admission/barrier.py` **s'importe**, ne se modifie pas.
- Aucune série issue de `overnight_futures_2026-07/code/step3_performance.py` (winsorisation
  0.5/99.5 **dans le constructeur** ⇒ queue tronquée d'un facteur 4). Tout est reconstruit du M1.
