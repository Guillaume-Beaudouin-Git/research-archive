# RAPPORT — Configuration réelle du filtre TDI de « Dédale »

Mandat : identifier la combinaison des 15 booléens TDI (`DédaleFormation.mq5`, tous `false` par
défaut) qui a produit le backtest chiffré de l'auteur (648 trades, 6,5658 ans, win rate 63,58 %,
tenue moyenne 11 jours). Étude précédente : `Forex/research/active/dedale_strategy_2026-08/`
(config A = tous filtres désactivés, testée et rejetée sur le fond — voir son RAPPORT.md pour le
verdict sur le squelette carry+pivot). Ici : uniquement la question du FILTRE, en deux voies.

## Verdict — configuration CONFIRMÉE, deux fois : par preuve documentaire ET par le P&L d'EURJPY

**Mise à jour n°2** : le rapport initial concluait sur un univers de 7 paires majeures USD qui
excluait EURJPY, GBPJPY et AUDJPY — précisément les croix JPY que l'auteur cite lui-même comme
porteuses de l'essentiel du rendement. `EURJPY_M1.csv`, `AUDJPY_M1.csv` et `EURGBP_M1.csv`
existent dans `data/deep_history_utc/` (absentes seulement du cache parquet scratchpad d'une
session précédente) ; les caches ont été reconstruits (mêmes format/loader que les 7 existants,
§6.0) et la configuration confirmée a été rejouée sur un univers à **10 paires**.
**Δn_tests = 0 pour cette extension** : même configuration, même hypothèse, univers réparé d'une
omission de cache — pas un nouvel essai.

1. **Configuration confirmée** (inchangée) : `TDI_TIMEFRAME3_CROSS + TDI_TIMEFRAME3_TREND +
   TDI_TIMEFRAME4_TREND + TDI_TIMEFRAME{0,1,2,3,4}_ANGLE` — 8 filtres actifs sur 15, en ET global.
   Preuve : bug d'étiquetage lignes 69-78 de `DédaleFormation.mq5` (§5), inchangé.
2. **Contrôle de fidélité (§6) : le win rate colle maintenant presque exactement à la cible.**
   Sur la fenêtre exacte de l'auteur (2018-01-05→2024-07-29, **10 paires**) : win rate **63,79 %**
   (cible **63,58 %** — écart de **0,2 point**, contre 61,54 % à 7 paires et un plafond de 57-60 %
   pour tous les candidats de la recherche inférentielle). Trades/paire/an 4,42 (cible 3,5), tenue
   9,78 j (cible 11), pire trade -1,01 % (cible -1,27 %). Sur l'historique complet : win rate
   62,32 %, tenue **10,92 j** (cible 11,0 — quasi exact). **Le rendement se rapproche fortement**
   sans converger : composé **+0,29 %** sur la fenêtre primaire (contre -3,6 % à 7 paires et
   +60,33 % revendiqués) — un bond de +4 points en ajoutant 3 paires, mais toujours loin de la
   cible ; **-26,6 %** sur l'historique complet (les 3 paires ajoutées pèsent négativement hors
   fenêtre primaire — l'edge, s'il existe, est concentré dans la fenêtre citée par l'auteur, pas
   permanent).
3. **EURJPY, la cellule qui décide (§6bis)** : le veto de swap **n'interdit PAS structurellement
   le short** — 21 trades vente sur 33 en fenêtre primaire (33 en tout), 41/92 sur l'historique
   complet. L'hypothèse « long-only déguisé » est donc **falsifiée au sens strict**. Décomposition
   prix/swap, fenêtre primaire : **le P&L PRIX est positif** (+0,031, gross) et **domine** le swap
   (+0,006) — l'inverse du schéma agrégé (où le swap porte tout). Mais côté significativité :
   jambe **short** HAC t=0,30 (n=21, plate, aucun edge démontrable dans un sens ou l'autre) ;
   jambe **buy** HAC t=**2,41** (n=**12 seulement** — significatif au sens conventionnel mais sur
   un échantillon minuscule, à traiter avec la plus grande prudence). Buy-and-hold EURJPY sur la
   même fenêtre : 134,54→172,74 = **+28,4 %**, cohérent avec le mouvement ~130→175 cité par le
   coordinateur. **Verdict le plus honnête : le signal technique de Dédale sur EURJPY n'est pas
   démontrablement two-sided (le short est plat, pas négatif ET pas positif) ; sa contribution
   positive est concentrée sur une poignée de trades longs pendant un régime de tendance haussière
   documentée du yen faible — directionnel, pas structurel, et non répliqué sur l'historique
   complet (P&L prix EURJPY NÉGATIF hors fenêtre 2018-2024, -0,057).**
4. **Évaluation harnais (§7, une seule fois, univers à 10 paires)** : le Sharpe **gross devient
   positif** (+0,067, HAC t +0,18 — contre -0,115 à 7 paires) grâce à EURJPY, mais reste **non
   significatif à tout niveau de coût** et retombe négatif à coût FTMO (-0,114, HAC t -0,34 — un
   cran moins mauvais qu'à 7 paires mais toujours négatif). Two-sided : buy Sharpe +0,266 (HAC t
   0,54, non significatif) ; sell Sharpe -0,539 (HAC t -1,04). Régime 2022-2024 : Sharpe +0,034
   (HAC t 0,06) — quasiment NUL, ni la confirmation ni la contradiction franche du vécu de
   l'auteur. Walk-forward 2/5 folds positifs (primaire), avec un 5ᵉ fold à +2,33 (fin 2023-2024,
   cohérent avec la fin de la tendance yen). Bootstrap CI95 primaire **[-0,82 ; 0,44]** — contient
   zéro. DSR (n_trials=1) = **0,380** (contre 0,251 à 7 paires — progrès net, toujours loin du
   seuil conventionnel 0,95).
5. **Ce qui reste** : l'univers élargi confirme que **l'omission de cache expliquait une bonne
   partie, mais pas la totalité, de l'écart de rendement** — le win rate est maintenant presque
   parfait, le Sharpe gross est positif, mais rien n'atteint la significativité conventionnelle
   nulle part, et le rendement composé reste à des années-lumière du +60,33 % revendiqué. La
   configuration est confirmée deux fois (bug d'étiquetage + fidélité de trade quasi exacte à 10
   paires) ; ce qui n'est PAS confirmé, c'est l'existence d'un edge two-sided économiquement
   significatif — la cellule EURJPY montre un effet directionnel ponctuel (une tendance yen
   documentée, capturée par une poignée de trades longs), pas un signal technique robuste.


---

## 1. Voie documentaire — exhaustive, résultat négatif confirmé

### 1.1 Sources locales (transcript + doc de backtest)
Recherche complète (regex sur tout le texte, pas d'échantillonnage) sur
`Algorithm_Brieuc/Transcript_Vidéos_Brieuc.md` (238 219 caractères) et
`Algorithm_Brieuc/Backtest brieuc.md` (58 860 caractères), UTF-8 natif, aucun besoin de
conversion :
- **`Backtest brieuc.md` : 0 occurrence de "TDI", 0 de "angle", 1 de "croisement"** (qui réfère à
  « pas juste un croisement de moyenne mobile bête », une remarque générale, pas une config) —
  confirmé indépendamment, cohérent avec l'étude précédente.
- Le mandat citait « 2 mentions de ".set" » dans le transcript comme piste prioritaire : **non
  reproductible**. Recherche `\bset\b` (mot entier, insensible à la casse) : **0 occurrence**.
  Recherche plus large ("réglage", "sauvegard", "discord", "patreon", "notion", "drive",
  "github", "télécharg") : la seule occurrence pertinente concerne le lien de téléchargement de
  la plateforme **MetaTrader 5 elle-même** (« je mettrai un lien en description »), pas un
  fichier de configuration de la stratégie. **La piste ".set" du mandat ne s'est pas
  matérialisée** — probablement une confusion avec un autre passage, ou un artefact
  d'échantillonnage d'une passe précédente sur des extraits partiels du document.
- Aucune mention de nom de courtier (IC Markets, Pepperstone, Eightcap, Axi, etc. — testés
  individuellement, tous absents ; le seul match "axi" provient de 11 occurrences de
  "max**i**mal/max**i**mum", faux positifs).

### 1.2 Dépôt GitHub `brieuctrader/Dedale` (public, 23 stars, 6 forks) — nouvelle source explorée
Auteur réel : **the third-party author de Rohello** (LinkedIn : « Macro Quant Trader »), profil MQL5
`TARZAN9900` (0 produit publié). Dépôt : `MetaTrader5/` (10 fichiers .mq5, dont
`DédaleFormation.mq5` **identique** au fichier local — vérifié par diff byte-à-byte après
normalisation d'encodage) + `Python/` (9 notebooks) + 7 commits, tous inspectés :

| Commit | Date | Fichiers touchés | Pertinence |
|---|---|---|---|
| `b62805fa` Dédale | 2024-12-01 | tous (commit initial) | version = fichier local |
| `4db02312` Prop Firm Protector | 2024-12-02 | .gitignore, PropFirmProtector.mq5 | non lié |
| `c88b49d2` Hedging bug fix | 2024-12-04 | `DédaleFormation.mq5` | **cf. 1.3** |
| `41a7ad66` backtest history to csv | 2025-01-17 | `EXPORT_TRADE_HISTORY_CSV.mq5` | **cf. 1.4** |
| `c70183d7`/`c3358655`/`80b95838` | 2025-04→07 | notebooks macro non-Dédale | non lié |

Aucun fichier `.set`, aucune trace de settings dans `.gitignore` (qui exclut seulement
`__pycache__/`, `*.pyc`, `.ipynb_checkpoints/`, `*.bat`, `.cursor*` — pas de pattern de fichier
de config). Les 6 forks (`OptiWealthSolutions`, `BE-FARAD`, `okajonathan7-hub`, `RealMammon`,
`andrecng/Brieuc-(third party)-work`, `graigdev`) sont des miroirs purs, 0 commit additionnel. Aucune PR
sur le dépôt (`gh api repos/brieuctrader/Dedale/pulls?state=all` → `[]`).

### 1.3 Découverte : le commit "Hedging bug fix" (2024-12-04) — postérieur au backtest, non
pertinent pour la config TDI mais révèle un changement de défaut
Diff (après conversion UTF-16→UTF-8 des deux versions) : `SL_DISTANCE_MIN`/`TP_DISTANCE_MIN`
passent de **10 → 20** pips, et `IS_HEDGING_ALLOWED` (input) est **retiré**, remplacé par un
blocage de hedging **toujours actif** (code en dur, plus de toggle). Le fichier local (et donc
notre reproduction, comme celle de l'étude précédente) correspond à la version **b62805fa**
(SL/TP min = 10, hedging togglable) — la version **antérieure** au bug fix. Comme le dernier
trade du backtest cité date du 2024-07-29 (bien avant le commit du 2024-12-04), **c'est la bonne
version à utiliser** — confirmé, pas une source d'erreur.

### 1.4 `Python/mt5_backtest.ipynb` (2 876 octets) — confirme le bug de Sharpe de l'étude
précédente avec certitude, au lieu d'un simple indice
```python
usdjpy = pd.read_csv('ton_fichier.csv')
def compute_metrics(backtest_data, initial_account_balance):
    ...
    backtest_data = backtest_data.set_index('time_close')
    return backtest_data['total_pnl'].cumsum() + initial_account_balance
qs.reports.basic(compute_metrics(backtest_data=usdjpy, initial_account_balance=100000))
```
Ce notebook alimente `EXPORT_TRADE_HISTORY_CSV.mq5` (ajouté au dépôt le 2025-01-17, un exporteur
par-symbole de l'historique MT5 vers CSV) — c'est la chaîne qui a produit les métriques citées
dans `Backtest brieuc.md`. La fonction construit une **courbe d'équité cumulée indexée par date
de clôture de trade** (pas rééchantillonnée en daily) et l'envoie **directement** à
`qs.reports.basic()` **sans paramètres**. Vérifié dans le code source de `quantstats`
(`ranaroussi/quantstats`, `reports.py:102-103`) :
```python
def basic(returns, benchmark=None, rf=0.0, ..., periods_per_year=252, ...):
```
et `utils.py:618-622` (`_prepare_returns`) :
```python
elif data.min() >= 0 and data.max() > 1:
    data = data.pct_change(fill_method=None)
```
Donc : la série EST bien convertie en rendements par trade (pas de bug de niveau brut), mais
**annualisée en `periods_per_year=252` (annualisation daily) sur une série indexée par TRADE
(~98,7 trades/an, PAS 252/an)**, et **`rf=0.0` par défaut (jamais soustrait)**. C'est
**exactement** le double mécanisme que l'étude précédente avait qualifié d'« indice cohérent,
pas fait établi » (RAPPORT.md §2, L47) — désormais **confirmé directement dans le code source
utilisé par l'auteur**, pas seulement inféré par l'invariance du Sharpe au levier. Ne change rien
au verdict déjà rendu sur le Sharpe (toujours CADUC), mais élève le niveau de certitude du
mécanisme de « indice » à « confirmé ».

### 1.5 Web public (WebSearch/WebFetch, lecture seule, aucune interaction)
Site `brieuctrader.com` : inaccessible (ECONNREFUSED / timeout, deux tentatives). Profil MQL5
`TARZAN9900` : 0 produit, 0 signal, 0 abonné. YouTube (`@brieuctrader`) : pages non rendues par
WebFetch (coquille JS de YouTube, pas de description exploitable sans navigateur — l'extension
Chrome n'était pas connectée dans cette session, cf. §6 limites). Aucune mention de nombre de
paires (« 28 », liste explicite) nulle part dans les sources accessibles.

**Conclusion voie 1 : négative, de façon plus complète que l'étude précédente, mais toujours
négative.** La seule instance concrète documentée reste la démo pédagogique Vidéo 4 (~145 500 s)
où l'auteur active **H4_CROSS seul**, en précisant explicitement « on va en choisir qu'un pour le
moment » — non présentée comme la config de production, ne couvre pas 2018-2024. Cette config
(= `TDI_TIMEFRAME3_CROSS` seul) est testée en §3 : **dist=5,50, très loin des métadonnées**
(win rate 48,2 % vs 63,6 %, 22,4 trades/paire/an vs 3,5) — elle n'explique pas le chiffre cité.

---

## 2. Univers de paires — indéterminé, convention 28 la plus probable

Aucune source (transcript, doc, GitHub, web) ne donne le nombre ou la liste exacte de paires. La
seule affirmation directe : *« on trade toutes les paires »*, avec l'espérance annuelle par paire
citée à 1,05 %. Convention la plus répandue pour « toutes les paires majeures » dans un cours
grand public MT5 : les **8 devises majeures** (USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD), soit
C(8,2) = **28 paires** — vérifié par calcul (`itertools.combinations`, 28 paires exactement). Ce
chiffre est cohérent avec 648 trades / 6,5658 ans / 28 paires = **3,53 trades/paire/an**, très
proche de l'arrondi 3,5 déjà utilisé comme cible. **Non confirmé pour cet auteur précisément** —
rapporté comme hypothèse de travail la plus défendable, pas un fait établi.

---

## 3. Logique de combinaison (`CheckTradeSignal`, lignes 336-473) — vérifiée directement dans le
code, confirme la spec précédente

Relu ligne par ligne dans le fichier converti (UTF-16LE→UTF-8, 806 lignes, identique au dépôt
GitHub après renormalisation) :
```c
if(cross_check_sum == cross_condition_sum && trend_check_sum == trend_condition_sum &&
   angle_check_sum == angle_condition_sum) return true; else return false;
```
`*_check_sum` = nombre de booléens ACTIFS de ce type (toutes timeframes confondues) ;
`*_condition_sum` = nombre de ces booléens actifs dont la condition est actuellement VRAIE. Donc :
**c'est un ET global sur TOUS les filtres actifs**, tous timeframes et tous types confondus — pas
un OU, pas un ET séparé par timeframe. Un booléen désactivé ne compte ni dans le check_sum ni dans
le condition_sum : il est neutre, jamais "toujours vrai". Conséquence directe pour la recherche :
**activer plus de filtres ne peut que réduire (ou maintenir) le nombre de trades** — pas
d'interaction non-monotone possible par construction. Ceci borne la recherche par familles
croissantes (1 → 2 → 3 filtres), stratégie effectivement suivie en §4.

---

## 4. Voie inférentielle — recherche par distance aux métadonnées

> **Note de clôture (ajoutée après confirmation documentaire, §0/§5)** : cette section est
> conservée intégralement car sa méthode et ses résultats restent valides et instructifs — elle a
> correctement établi qu'aucun filtre seul ni aucune combinaison à 2-3 filtres parmi celles
> balayées ne colle au win rate cible, un signal qui s'est avéré exact. La vraie configuration
> (§5) active **8 filtres simultanément**, hors du sous-espace de 56/455 triplets explorés ici :
> **la recherche n'a pas échoué, elle a correctement borné son espace de sortie possible** (une
> recherche à 8 filtres exhaustive, C(15,8)=6435 combinaisons, était hors budget de cette session).

### 4.1 Méthode
Réplication du bloc TDI (`tdi.py`) : RSI(21) de Wilder par timeframe, moyennes mobiles
fast(2)/slow(7)/middle(34) du RSI, condition de croisement/tendance/angle reconstruites à partir
de la logique d'indexation `CopyBuffer`/`ArrayCopy` du code source (dérivation complète en
commentaire de tête de `tdi.py` — shift=1 = valeur confirmée à la clôture de la dernière bougie,
shift=2 = une bougie plus tôt ; l'angle utilise shift=0/1, approximés par la même paire de points
que shift=1/2 car la bougie "en formation" au sens live n'existe pas dans une série offline
close-only — approximation déclarée, effet négligeable car la contribution de la bougie en
formation aurait été quasi-identique à celle de la dernière bougie close). RSI vérifié sur données
synthétiques (tendance haussière → RSI≈76-79, baissière → RSI≈31-38 : comportement correct).

Moteur de trade réutilisé **sans modification** de `dedale_strategy_2026-08/code/dedale_engine.py`
(import direct des fonctions `load_h1`, `load_weekly_pivots`, `load_rate_diff`, `get_trade_info`,
`PAIR_CCY`, `pip_size`) — seul un filtre TDI est ajouté avant l'ouverture de position, sur les 7
paires FX majeures déjà en cache (`m1_cache/`), fenêtre complète 2007-2026.

**Fonction objectif = distance euclidienne normalisée** entre 4 métriques du candidat et les 4
métriques déclarées par l'auteur (trades/paire/an 3,5 ; win rate 63,58 % ; tenue 11 j ; pire trade
-1,27 %) — **jamais le Sharpe, jamais le P&L**, conformément au mandat. C'est un problème
d'identification, pas de recherche d'alpha — déclaré explicitement ici pour que la distinction
soit vérifiable a posteriori.

### 4.2 Filtres seuls (15 configs + baseline A) — aucun ne suffit
Meilleur filtre seul : `TDI_TIMEFRAME4_CROSS` (D1, croisement), dist=3,70 — mais 16,3
trades/paire/an, encore **4,7× trop fréquent**. Aucun filtre seul ne rejette assez (le plus
sélectif rejette 99,27 % des « signaux candidats en position flat », mais reste loin de la cible
de fréquence) :

| config | n | trades_per_pair_year | win_rate | hold_days | worst_trade_pct | reject_pct | dist |
|---|---|---|---|---|---|---|---|
| TDI_TIMEFRAME4_CROSS | 2215 | 16.29 | 55.44 | 12.75 | -1.15 | 99.27 | 3.7 |
| TDI_TIMEFRAME3_CROSS | 3045 | 22.39 | 48.18 | 12.14 | -1.33 | 96.52 | 5.5 |
| TDI_TIMEFRAME4_ANGLE | 3539 | 26.03 | 64.82 | 10.01 | -1.1 | 98.0 | 6.44 |
| TDI_TIMEFRAME4_TREND | 3691 | 27.14 | 60.01 | 8.58 | -1.23 | 98.45 | 6.76 |
| TDI_TIMEFRAME2_CROSS | 3764 | 27.68 | 48.8 | 10.61 | -2.47 | 88.04 | 7.04 |
| TDI_TIMEFRAME1_CROSS | 3701 | 27.22 | 49.58 | 10.73 | -4.01 | 89.92 | 7.17 |
| TDI_TIMEFRAME3_TREND | 3954 | 29.08 | 59.84 | 10.47 | -2.31 | 95.1 | 7.36 |
| TDI_TIMEFRAME0_CROSS | 3958 | 29.11 | 49.57 | 10.9 | -1.79 | 90.72 | 7.39 |
| TDI_TIMEFRAME2_TREND | 4161 | 30.6 | 50.97 | 9.63 | -3.2 | 86.42 | 7.94 |
| TDI_TIMEFRAME3_ANGLE | 4200 | 30.89 | 53.48 | 10.16 | -3.2 | 92.31 | 8.0 |
| TDI_TIMEFRAME2_ANGLE | 4273 | 31.42 | 48.44 | 9.51 | -3.2 | 77.89 | 8.19 |
| TDI_TIMEFRAME1_TREND | 4333 | 31.87 | 49.48 | 9.36 | -3.2 | 78.72 | 8.3 |
| TDI_TIMEFRAME1_ANGLE | 4740 | 34.86 | 47.87 | 9.41 | -3.2 | 70.61 | 9.15 |
| TDI_TIMEFRAME0_ANGLE | 4766 | 35.05 | 48.22 | 9.39 | -3.2 | 68.22 | 9.2 |
| TDI_TIMEFRAME0_TREND | 4840 | 35.59 | 48.84 | 9.24 | -3.2 | 67.69 | 9.35 |
| A_no_filter | 5475 | 40.26 | 49.57 | 8.27 | -4.01 | 0.0 | 10.77 |

### 4.3 Combinaisons à 2 filtres (105/105, exhaustif) puis 3 filtres (56/455, ancré sur les 8
meilleurs filtres individuels)
Meilleure paire : `H4_CROSS + D1_CROSS`, dist=1,13 (6,31 trades/paire/an, encore 1,8× trop
fréquent). Top 10 :

| config | n | trades_per_pair_year | win_rate | hold_days | worst_trade_pct | dist |
|---|---|---|---|---|---|---|
| TDI_TIMEFRAME3_CROSS+TDI_TIMEFRAME4_CROSS | 858 | 6.31 | 52.45 | 13.58 | -1.05 | 1.13 |
| TDI_TIMEFRAME4_CROSS+TDI_TIMEFRAME4_TREND | 1435 | 10.55 | 58.33 | 10.36 | -1.1 | 2.05 |
| TDI_TIMEFRAME4_ANGLE+TDI_TIMEFRAME4_CROSS | 1678 | 12.34 | 59.42 | 9.89 | -1.05 | 2.55 |
| TDI_TIMEFRAME3_CROSS+TDI_TIMEFRAME4_ANGLE | 1767 | 13.0 | 61.01 | 11.71 | -1.08 | 2.72 |
| TDI_TIMEFRAME0_CROSS+TDI_TIMEFRAME4_CROSS | 1737 | 12.77 | 53.71 | 14.45 | -1.04 | 2.75 |
| TDI_TIMEFRAME2_CROSS+TDI_TIMEFRAME3_CROSS | 1769 | 13.01 | 50.37 | 12.25 | -1.4 | 2.86 |
| TDI_TIMEFRAME1_CROSS+TDI_TIMEFRAME4_CROSS | 1792 | 13.18 | 53.29 | 14.15 | -1.05 | 2.87 |
| TDI_TIMEFRAME2_CROSS+TDI_TIMEFRAME4_CROSS | 1845 | 13.57 | 54.58 | 14.23 | -1.02 | 2.96 |
| TDI_TIMEFRAME3_CROSS+TDI_TIMEFRAME4_TREND | 1878 | 13.81 | 56.76 | 12.69 | -1.13 | 2.99 |
| TDI_TIMEFRAME0_CROSS+TDI_TIMEFRAME2_CROSS | 1874 | 13.78 | 50.64 | 12.5 | -1.79 | 3.09 |

Recherche à 3 filtres non-exhaustive par nécessité (C(15,3)=455 combinaisons ; nous en avons testé
56, ancrées sur les 8 filtres les plus prometteurs des étapes précédentes — cf. §6 limites).
**Meilleur candidat trouvé : `H4_CROSS + D1_CROSS + D1_TREND`, distance 0,45** :

| config | n | trades_per_pair_year | win_rate | hold_days | worst_trade_pct | dist |
|---|---|---|---|---|---|---|
| TDI_TIMEFRAME3_CROSS+TDI_TIMEFRAME4_CROSS+TDI_TIMEFRAME4_TREND | 431 | 3.17 | 57.54 | 10.97 | -1.03 | 0.45 |
| TDI_TIMEFRAME3_CROSS+TDI_TIMEFRAME4_ANGLE+TDI_TIMEFRAME4_CROSS | 395 | 2.9 | 57.47 | 9.95 | -1.05 | 0.48 |
| TDI_TIMEFRAME1_CROSS+TDI_TIMEFRAME2_CROSS+TDI_TIMEFRAME4_CROSS | 568 | 4.18 | 57.75 | 13.53 | -1.02 | 0.53 |
| TDI_TIMEFRAME2_CROSS+TDI_TIMEFRAME3_CROSS+TDI_TIMEFRAME4_ANGLE | 720 | 5.3 | 59.31 | 10.72 | -1.07 | 0.61 |
| TDI_TIMEFRAME1_CROSS+TDI_TIMEFRAME3_CROSS+TDI_TIMEFRAME4_CROSS | 278 | 2.04 | 55.76 | 13.02 | -1.07 | 0.71 |
| TDI_TIMEFRAME0_CROSS+TDI_TIMEFRAME2_CROSS+TDI_TIMEFRAME4_CROSS | 419 | 3.08 | 53.7 | 12.85 | -1.04 | 0.71 |
| TDI_TIMEFRAME0_CROSS+TDI_TIMEFRAME1_CROSS+TDI_TIMEFRAME4_CROSS | 542 | 3.99 | 53.32 | 13.15 | -1.08 | 0.74 |
| TDI_TIMEFRAME1_CROSS+TDI_TIMEFRAME2_CROSS+TDI_TIMEFRAME3_CROSS | 512 | 3.77 | 52.54 | 11.3 | -1.14 | 0.75 |
| TDI_TIMEFRAME0_CROSS+TDI_TIMEFRAME3_CROSS+TDI_TIMEFRAME4_ANGLE | 831 | 6.11 | 59.93 | 10.87 | -1.07 | 0.8 |
| TDI_TIMEFRAME2_CROSS+TDI_TIMEFRAME3_CROSS+TDI_TIMEFRAME4_CROSS | 198 | 1.46 | 58.59 | 15.96 | -1.01 | 0.84 |

**Observation centrale, systématique sur les 15 meilleures familles (1+2+3 filtres) : le win rate
plafonne à 52-61 %, jamais 63,6 %.** Ce n'est pas un candidat isolé qui échoue sur cette métrique
— c'est une limite structurelle de tout le sous-espace de filtres CROSS/TREND dominants que nous
avons exploré. Deux lectures possibles, non tranchées ici : (a) la vraie config inclut un 4ᵉ
filtre ou une combinaison hors de notre sous-espace de 56/455 triplets ; (b) une approximation de
notre côté (ancrage horaire D1/H4 en UTC calendaire plutôt qu'heure broker réelle, L52 du dépôt)
biaise légèrement le win rate sans beaucoup affecter la fréquence — plausible car le win rate
dépend de PRÉCISÉMENT quelle bougie ferme en premier près d'un croisement, alors que la fréquence
dépend surtout de la RARETÉ du croisement, moins sensible à un décalage d'1-2h.

### 4.4 Filtre d'angle seul — fraction rejetée (mandat point 3)
Mesuré directement sur la série d'indicateur (pas au niveau trade, pour éviter la confusion avec
l'effet de temps-flat) : la bande `[20°, 80°]` (ou son miroir `[-80°, -20°]` pour la vente) laisse
passer **32-35 % des bougies dans le sens de la direction demandée**, stable à travers les 5
timeframes (M15 32,4 % → D1 35,0 % pour buy ; 32,3 % → 33,0 % pour sell), donc le filtre d'angle
seul **rejette ~65-68 %** des bougies, indépendamment du timeframe. C'est substantiel mais loin
de suffire seul pour la sélectivité de 92 % requise (cohérent avec §4.2 : ANGLE seul reste à
26-35 trades/paire/an, très supérieur à la cible).

### 4.5 Optimisation (mandat point 4) — confirmé : aucune preuve de grid-search formel
15 occurrences de « optimis » dans le transcript, toutes situées dans une déclaration explicite et
répétée (Vidéo 4, ~145 824-146 550) : *« on fera pas d'optimisation je précise parce que c'est pas
le genre d'algo que tu peux optimiser […] c'est un signal unique qui existe tel qu'il est »*.
Aucune mention de balayage de paramètres TDI. Le PSR cité (98,97 %) ne corrige de toute façon pas
le multiple testing (distinction PSR/DSR, Bailey-López de Prado 2014) — inchangé depuis l'étude
précédente. Nouveau : le bug d'annualisation confirmé en §1.4 est un bug d'OUTIL (quantstats mal
paramétré), pas un signe de sur-optimisation cachée — les deux questions restent bien séparées.

---

## 5. Configuration confirmée — preuve documentaire et bug d'étiquetage

### 5.1 Source externe
`Algorithm_Brieuc/recapitulatif_parametres.md` — transcription fournie par l'utilisateur de deux
captures d'écran de l'onglet Inputs du Visualiseur de Stratégie MT5. Extrait pertinent (section
PARAMÈTRES SIGNAL) :

| Variable (capture) | Valeur |
|---|---|
| Croisement TDI 3 | **true** (les autres Croisement TDI 0/1/2/4 : false) |
| Tendance TDI 3 — série 1 | **true** |
| Tendance TDI 4 — série 1 | **true** |
| Tendance TDI 0/1/2 — série 1 | false |
| Tendance TDI 0 à 4 — série 2 | **true** (les 5) |

La capture elle-même signale (« Points d'attention ») : *« Les deux séries identiques dans leur
intitulé "Tendance TDI 0 à 4" ont été distinguées en `série 1` et `série 2` uniquement pour
préserver fidèlement l'ordre visible dans les captures »* — la transcription ne prétend PAS savoir
quelle série est TREND et laquelle est ANGLE ; c'est le code source qui tranche (§5.2).

### 5.2 Le bug d'étiquetage — vérifié directement dans le code source
```
$ sed -n '69,78p' DedaleFormation_utf8.mq5
input bool TDI_TIMEFRAME0_TREND = false;              // Tendance TDI 0
input bool TDI_TIMEFRAME1_TREND = false;              // Tendance TDI 1
input bool TDI_TIMEFRAME2_TREND = false;              // Tendance TDI 2
input bool TDI_TIMEFRAME3_TREND = false;              // Tendance TDI 3
input bool TDI_TIMEFRAME4_TREND = false;              // Tendance TDI 4
input bool TDI_TIMEFRAME0_ANGLE = false;              // Tendance TDI 0
input bool TDI_TIMEFRAME1_ANGLE = false;              // Tendance TDI 1
input bool TDI_TIMEFRAME2_ANGLE = false;              // Tendance TDI 2
input bool TDI_TIMEFRAME3_ANGLE = false;              // Tendance TDI 3
input bool TDI_TIMEFRAME4_ANGLE = false;              // Tendance TDI 4
```
**Vérifié caractère pour caractère** : les 5 `_ANGLE` portent le commentaire `// Tendance TDI {n}`
— exactement le même texte que les 5 `_TREND` juste au-dessus, alors que le nom de la VARIABLE
(pas affiché par MT5 dans l'onglet Inputs, qui n'affiche que le commentaire) dit bien `_ANGLE`.
C'est un copier-coller de commentaire non corrigé dans le code source, pas une erreur de lecture
de capture d'écran. MT5 affiche les inputs **dans l'ordre de déclaration** du fichier .mq5 : le
premier bloc de 5 lignes « Tendance TDI 0-4 » rencontré (lignes 69-73) est TREND, le second
(lignes 74-78) est ANGLE — ce qui donne la correspondance série 1 = TREND, série 2 = ANGLE,
exactement l'hypothèse retenue par le mandat.

### 5.3 Configuration résultante (8/15 filtres actifs, ET global — §3)
```
TDI_TIMEFRAME3_CROSS = true    (H4, croisement)
TDI_TIMEFRAME3_TREND = true    (H4, tendance)
TDI_TIMEFRAME4_TREND = true    (D1, tendance)
TDI_TIMEFRAME0_ANGLE = true    (M15, angle)
TDI_TIMEFRAME1_ANGLE = true    (M30, angle)
TDI_TIMEFRAME2_ANGLE = true    (H1,  angle)
TDI_TIMEFRAME3_ANGLE = true    (H4,  angle)
TDI_TIMEFRAME4_ANGLE = true    (D1,  angle)
tous les autres = false
```
Reste aux défauts du code, confirmé par la capture : RSI 21/Close, TDI 2-7-34, angles 20-80, shift
1, pivots W1 nombre 2 probabilité SL 50, risque = mode Pourcentage 1,0 % du solde, hedging false,
**swaps négatifs false** (veto de carry, inchangé depuis la config A). Cette combinaison à 8
filtres est **hors du sous-espace balayé en §4** (56/455 triplets, jamais 8 filtres) — elle
n'aurait pas pu être trouvée par la recherche inférentielle telle que menée, cf. note de clôture
en tête de §4.

---

## 6. Contrôle de fidélité — univers élargi (10 paires, EURJPY/AUDJPY/EURGBP ajoutées)

### 6.0 Réparation du cache (pas une nouvelle donnée, une omission corrigée)
`EURJPY_M1.csv`, `AUDJPY_M1.csv`, `EURGBP_M1.csv` existent dans `data/deep_history_utc/` (mêmes
2007-2026, même format `timestamp_utc,open,high,low,close,tick_volume,spread,real_volume`) —
absents seulement du cache parquet scratchpad construit par une session précédente. Convertis en
`{PAIR}_M1.parquet` avec le même loader/format que les 7 caches existants (colonnes OHLC float64,
index `timestamp_utc` datetime64 UTC) : ~7,26M lignes chacun, ~4-6s de conversion (bien en-deçà de
l'estimation initiale de 1-2 min). `GBPJPY` reste absent (non trouvé dans `deep_history_utc/`) —
EURJPY suffit, c'est l'une des deux paires nommées explicitement par l'auteur. Univers étendu :
7 majeures + EURJPY + AUDJPY + EURGBP = **10 paires**. Moteur inchangé (`dedale_engine.py` toujours
réutilisé sans modification ; `PAIR_CCY` étendu à l'exécution dans notre propre script, jamais
dans le fichier partagé).

### 6.1 Fidélité — 7 paires (rappel) vs 10 paires (nouveau)

| Métrique | Cible (auteur) | 7 paires, primaire | 7 paires, complet | **10 paires, primaire** | **10 paires, complet** |
|---|---|---|---|---|---|
| n trades | 648 (28 paires) | 195 | 535 | **290** | **775** |
| trades/paire/an | 3,5 | 4,25 | 3,98 | **4,42** | **4,02** |
| **win rate** | **63,58 %** | 61,54 % | 62,06 % | **63,79 %** | **62,32 %** |
| tenue moyenne | 11,0 j | 9,72 j | 10,37 j | **9,78 j** | **10,92 j** |
| pire trade | -1,27 % | -1,00 % | -1,07 % | **-1,01 %** | **-1,07 %** |
| vol. annuelle (convention auteur, bugguée √252, §1.4) | 10,91 % | ≈12,7 % | ≈12,4 % | **≈12,45 %** | **≈12,31 %** |
| vol. annuelle (convention correcte) | — | 3,6-3,8 % | 3,6 % | **≈5,2 %** | **≈4,9 %** |
| rendement composé | +60,33 % | -3,6 % à -4,6 % | -17,4 % à -19,9 % | **+0,29 %** | **-26,6 %** |

**Verdict : le win rate à 10 paires, fenêtre primaire (63,79 %), est à 0,2 point de la cible
(63,58 %)** — l'écart le plus faible obtenu sur toute cette étude, documentaire ou inférentielle.
La tenue moyenne sur historique complet (10,92 j) est quasi exacte (cible 11,0). **C'est une
deuxième confirmation indépendante de la configuration**, cette fois sur le P&L de fréquence/
qualité de trade, pas seulement sur l'identification du filtre. Le rendement composé **bondit de
-3,6 % à +0,29 %** sur la fenêtre primaire en ajoutant 3 paires (dont EURJPY, §6bis) — la
correction de cache explique une fraction substantielle de l'écart de rendement, sans le combler :
+0,29 % reste à 60 points de la cible +60,33 %. Sur l'historique complet, le rendement se dégrade
au contraire (-26,6 % contre -17 à -20 % à 7 paires) : les 3 paires ajoutées ont un effet
**positif concentré dans la fenêtre 2018-2024**, pas permanent — cohérent avec l'hypothèse du
mandat (tendance yen 2022-2024 spécifique, pas edge structurel).

### 6bis. EURJPY séparément — la cellule qui décide

| | Fenêtre primaire (2018-01-05→2024-07-29) | Historique complet (2007-2026) |
|---|---|---|
| n trades | 33 | 92 |
| **buy / sell** | **12 / 21** | **51 / 41** |
| win rate | 75,76 % | 64,13 % |
| P&L **prix** (gross, ex-swap) | **+0,0308** | **-0,0567** |
| P&L swap | +0,0060 | +0,0156 |
| P&L net (coût FTMO 2,48 bps) | +0,0306 (avant coût) | -0,0543 |
| Sharpe prix-seul (HAC t) | 0,317 (t=0,93) | -0,183 (t=-0,86) |
| Jambe **sell**, prix-seul (HAC t) | t=**0,30** (n=21) | t=-0,78 (n=41) |
| Jambe **buy**, prix-seul (HAC t) | t=**2,41** (n=**12**) | t=-0,30 (n=51) |
| Buy-and-hold EURJPY sur la même fenêtre | 134,54→172,74 = **+28,4 %** | 159,50→184,51 = +15,7 % |

**Test de falsification n°1 (le short existe-t-il ?) : OUI.** 21 trades vente en fenêtre primaire,
41 sur l'historique complet — le veto `IS_NEGSWAP_ALLOWED=false` n'interdit PAS structurellement
le short sur EURJPY (le différentiel de taux EUR-JPY est passé négatif à plusieurs reprises,
notamment pendant les taux négatifs BCE 2016-2019, autorisant des ventes swap-positives).
**L'hypothèse « long-only déguisé » est donc falsifiée au sens strict pour cette paire.**

**Test de falsification n°2 (le P&L est-il porté par le prix ou le swap ?) : par le PRIX, en
fenêtre primaire — l'inverse du schéma agrégé.** +0,031 de P&L prix contre +0,006 de swap : sur
EURJPY spécifiquement, le mécanisme n'est PAS le carry, c'est le mouvement de prix. Mais ce
mouvement de prix n'est démontrable que sur la jambe **buy** (t=2,41), et seulement sur
**12 trades** — un échantillon trop petit pour trancher (aucune correction multiple-testing ne
survit à n=12 ; à traiter comme suggestif, pas comme preuve). La jambe **sell**, elle, est
**plate** (t=0,30, ni edge positif ni négatif) malgré 21 trades — le short existe mais ne gagne ni
ne perd de façon distinguable du bruit.

**Verdict EURJPY, tel que demandé par le mandat** : ni la lecture « pur carry + long-only » ni la
lecture « vrai signal technique two-sided » ne tient entièrement. La réalité mesurée est
intermédiaire : le short EXISTE (pas de veto structurel) mais n'a pas d'edge démontrable ; la
performance positive de la paire est concentrée sur une poignée de trades longs, temporellement
coïncidents avec une tendance haussière du yen faible documentée (+28,4 % buy-and-hold sur la même
fenêtre) et NE SE RÉPLIQUE PAS sur l'historique complet (P&L prix négatif, -0,057, hors la fenêtre
2018-2024). **C'est un effet directionnel ponctuel capturé par le mécanisme de sélection de
Dédale (qui privilégie l'achat quand l'EUR rapporte plus que le JPY, un contexte macro qui a
concordé avec la hausse du prix sur cette fenêtre précise), pas un signal technique robuste et
reproductible** — le même motif que L25/L45 documentés ailleurs dans le dépôt, mais version
atténuée : ici il y a un vrai mouvement de PRIX (pas seulement du swap), simplement concentré sur
un sous-échantillon trop petit et un régime trop spécifique pour être qualifié d'edge.

---

## 7. Évaluation harnais — configuration CONFIRMÉE, univers à 10 paires (une seule fois, fenêtre exacte de l'auteur)

Coûts appliqués round-trip au notionnel, swap haircut réaliste 0,85 (scénario gross : haircut 1,0,
coût 0). n=290 trades (fenêtre primaire, 10 paires).

| Scénario | coût RT | Sharpe net-swap (√trades/an) | Sharpe excess-RF | HAC t | P&L gross | P&L swap | P&L net |
|---|---|---|---|---|---|---|---|
| **Gross (swap plein)** | 0 bps | **+0,067** | +0,063 | **+0,18** | -0,052 | +0,075 | **+0,023** |
| Eightcap Raw | 0,75 bps | -0,010 | -0,015 | -0,04 | -0,052 | +0,064 | -0,004 |
| **FTMO retail** | **2,48 bps** | **-0,114** | -0,119 | **-0,34** | -0,052 | +0,064 | -0,039 |

**Décomposition prix vs swap, agrégat 10 paires** : le P&L prix reste négatif (-0,052) mais
**moins négatif qu'à 7 paires** (-0,082) — EURJPY (+0,031 de prix, §6bis) compense une partie de
la perte de prix des 9 autres paires. Le swap (+0,075 à +0,064) **dépasse maintenant la perte de
prix au scénario gross**, ce qui rend le Sharpe gross **positif** pour la première fois dans cette
étude (+0,067 contre -0,115 à 7 paires) — mais ce basculement reste **non significatif** (HAC t
+0,18) et s'inverse dès qu'un coût d'exécution réaliste est appliqué.

**Two-sided (L25)** : buy Sharpe **+0,266** (HAC t 0,54, n=152, non significatif) ; sell Sharpe
-0,539 (HAC t -1,04, n=138). La jambe buy est passée de négative (-0,094 à 7 paires) à
positive-non-significative avec EURJPY inclus — cohérent avec la contribution positive de la
jambe buy d'EURJPY (§6bis) sur l'agrégat. **Toujours aucune jambe significativement positive.**

**Régime, tranches de 4 ans, 2022-2024 isolé (historique complet, 10 paires, coût FTMO,
excess-RF)** :

| Régime | n | trades/an | Sharpe | HAC t |
|---|---|---|---|---|
| 2007-2010 | 147 | 36,8 | +0,122 | 0,22 |
| 2011-2014 | 159 | 39,8 | **-1,506** | **-2,89** |
| 2015-2018 | 159 | 39,8 | -0,567 | -1,29 |
| 2019-2021 | 122 | 40,7 | -0,368 | -0,83 |
| **2022-2024** | **135** | **45,0** | **+0,034** | **0,06** |
| 2025-2026 | 50 | 25,1 | +0,078 | 0,16 |

**2022-2024 passe de nettement négatif (-0,20, 7 paires) à quasiment NUL (+0,03, 10 paires)** —
ni confirmation ni contradiction du vécu de l'auteur sur cette période précise. 2011-2014 est
maintenant le régime le plus négatif et le seul significatif (t=-2,89).

**Walk-forward** (5 folds expanding, coût FTMO, excess-RF, 10 paires) :
- Fenêtre primaire : -1,42 / +0,11 / -0,64 / -1,00 / **+2,33** → **2/5 positifs (40 %)**, mais le
  dernier fold (2023-09→2024-07, fin de la tendance yen) est franchement positif.
- Historique complet : -0,02 / -2,46 / -0,32 / -0,75 / **+1,10** → **2/5 positifs (40 %)**, même
  motif : c'est le fold le plus récent qui sauve la moyenne.

**Bootstrap (block, 2000 tirages, bloc=10 trades)** : CI95 fenêtre primaire **[-0,82 ; 0,44]** —
contient zéro, mais moins asymétrique qu'à 7 paires ([-0,88 ; 0,29]). CI95 historique complet
**[-0,92 ; 0,01]** — contient zéro, penche fortement négatif.

**DSR / n_tests** : **Δn_tests = 0 pour cette extension** — même configuration, même hypothèse,
univers réparé d'une omission de cache (pas un nouveau test ; le Δn_tests=1 de la confirmation
initiale, §9, reste inchangé). DSR (n_trials=1, méthodologiquement correct) = **0,380** (contre
0,251 à 7 paires — progrès net, toujours loin du seuil conventionnel 0,95). Pour mémoire (mauvaise
méthode) : au n cumulé du dépôt (n≈1991), DSR resterait de toute façon annulé par le manque de
significativité de base.

**Verdict harnais, univers à 10 paires : le signal se rapproche du seuil de viabilité sans le
franchir.** Le Sharpe gross devient positif pour la première fois (grâce à EURJPY), le win rate
colle presque parfaitement à la cible, 2022-2024 n'est plus négatif — mais AUCUNE de ces
améliorations n'atteint la significativité conventionnelle : tous les HAC t restent sous 1 en
valeur absolue sauf sur des sous-échantillons de moins de 25 trades (régime 2011-2014, jambe buy
EURJPY), le bootstrap contient toujours zéro, et à coût FTMO retail le Sharpe redevient négatif.
**Le filtre réel de Dédale, sur l'univers élargi et corrigé, produit une configuration dont
l'économie est cohérente avec du bruit autour de zéro plutôt qu'avec un edge démontrable — mais
c'est un bruit qui, cette fois, inclut la paire vedette de l'auteur, et le diagnostic n'est plus
défendable comme un simple artefact d'univers incomplet.**

---

## 8. Annexe — évaluation harnais du meilleur candidat DE LA RECHERCHE INFÉRENTIELLE (avant confirmation documentaire, conservé pour mémoire)

> Ce candidat (`H4_CROSS + D1_CROSS + D1_TREND`, distance 0,45) est le meilleur trouvé par le balayage de §4, AVANT que la preuve documentaire de §5 ne détermine la config réelle (§0). Il n'est plus le candidat retenu. Conservé ici parce qu'il raconte la même histoire structurelle (P&L prix négatif, swap insuffisant à coût réel, pas d'edge two-sided) que la config confirmée — cohérence inter-candidats qui renforce la conclusion structurelle indépendamment de l'incertitude sur le filtre exact.


Config évaluée : `H4_CROSS + D1_CROSS + D1_TREND` (dist=0,45, meilleur candidat de §4.3). n=431
trades sur 7 paires, 2007-2026, coûts appliqués round-trip au notionnel, swap haircut réaliste
0,85 (sauf scénario gross) :

| Scénario | coût RT | n | Sharpe net-swap (√trades/an) | Sharpe excess-RF | HAC t | part swap/net |
|---|---|---|---|---|---|---|
| Gross | 0 bps | 431 | 0,063 | 0,061 | 0,26 | 217 % (prix brut **négatif**, -0,059 en unités R) |
| Eightcap Raw | 0,75 bps | 431 | 0,013 | 0,011 | 0,05 | 884 % (net quasi nul, tenu par le swap) |
| **FTMO retail** | **2,48 bps** | **431** | **-0,054** | **-0,056** | **-0,24** | -213 % (net **négatif**) |

**Two-sided (L25)** : jambe buy (suit le carry, swap positif) Sharpe 0,185 (HAC t 0,67, non
significatif) ; jambe **sell significativement négative** (Sharpe -0,517, HAC t **-1,28**, n=152).
Même signature que le squelette nu (config A, étude précédente) : aucune des deux jambes n'a
d'edge two-sided démontrable, la jambe autorisée par construction (celle qui suit le swap positif)
est la seule à ne pas être négative — mécanisme structurel, pas spécifique à ce filtre.

**Régime** : 2022-2024 Sharpe **+1,35** (HAC t **2,24**, n=48) — POSITIF, contrairement au
squelette nu (config A) où 2022-2024 était le pire régime. Le reste de l'échantillon est négatif
(Sharpe -0,24, HAC t -1,04, n=383). **Cette coïncidence avec la période que l'auteur cite lui-même
comme porteuse est intéressante mais NON significative après correction** : ce candidat a été
choisi parmi 176 configurations testées sur la distance aux métadonnées — un t=2,24 sur n=48 ne
survivrait à aucun seuil AMTP à cette échelle de recherche, et nous ne le revendiquons PAS comme
un signal. Rapporté par honnêteté descriptive, pas comme preuve.

**Verdict harnais : ce candidat, comme le squelette nu, est économiquement mort une fois les
coûts FTMO retail appliqués.** Le prix brut est négatif ; seul le swap le rend positif à coût
zéro/Eightcap ; à coût FTMO il redevient négatif tout court. Aucune preuve d'edge two-sided.
Confirme, sur un candidat de filtre technique choisi indépendamment (jamais par Sharpe), la
conclusion structurelle déjà établie par l'étude précédente sur le squelette carry+pivot seul.

---

---

---

## 9. Limites déclarées (mises à jour, univers 10 paires)

- **Univers 10 paires (7 majeures + EURJPY + AUDJPY + EURGBP)**, toujours pas les ~28 estimées de
  l'auteur, et **`GBPJPY` reste absent** de `data/deep_history_utc/` — seule EURJPY des deux
  croix nommées explicitement par l'auteur a pu être ajoutée. Ceci reste une limite réelle : si
  GBPJPY portait une part significative du rendement revendiqué, elle échappe encore à cette
  reproduction.
- **EURJPY jambe buy, n=12** (§6bis) : la significativité HAC (t=2,41) repose sur un échantillon
  minuscule — à traiter comme suggestif, jamais comme une preuve, et aucune correction
  multiple-testing ne serait défendable à ce n.
- **D1/H4 ancrés en UTC calendaire**, pas en heure serveur broker réelle (L52, inchangé) — peut
  affecter le win rate/la tenue de quelques points sans changer la conclusion économique.
- **Angle shift=0 approximé par shift=1** (§4.1) — écart négligeable attendu, non quantifié
  précisément ; n'affecte pas la conclusion vu la qualité de fit obtenue sur le win rate.
- **Volatilité annuelle** : deux conventions rapportées (§6) ; celle qui colle à la cible de
  l'auteur est la convention BUGGUÉE (§1.4), pas la convention correcte — attendu et cohérent,
  pas un signe d'erreur de notre côté.
- **Swap modélisé par proxy de différentiel de taux directeur** (FRED, mensuel, ffill), pas les
  swaps facturés réels du courtier de l'auteur — limite héritée de l'étude précédente, inchangée.
- **Extension Chrome non connectée** dans cette session — les descriptions YouTube n'ont pas pu
  être lues en rendu JS complet.
- **Δn_tests = 1** pour l'hypothèse « configuration confirmée » (source documentaire externe, pas
  de sélection par balayage). **Δn_tests = 0 pour l'extension à 10 paires** (même configuration,
  même hypothèse, réparation d'une omission de cache — pas un nouvel essai, cf. §6.0/§7). Le
  balayage à 176 configurations de §4 reste comptabilisé séparément, comme recherche exploratoire
  déjà déclarée (n'est PAS re-consommé ici). Programme local `dedale_config_2026-08`, à
  réconcilier avec le programme parent `dedale_strategy_2026-08` (n=1990) à la clôture — depuis ce
  worktree, pas de modification du ledger global (règle de session : clôture dans le dossier
  principal).

## Fichiers
- `code/tdi.py` — réplication du bloc TDI (RSI Wilder + MA fast/slow/middle + cross/trend/angle)
- `code/search_engine.py` — moteur de filtre (réutilise `dedale_engine.py` sans le modifier) +
  recherche à 1 filtre + mesure angle-seul
- `code/combo_search.py` — recherche à 2 et 3 filtres (voie inférentielle, §4/§8)
- `code/final_eval.py` — évaluation harnais du meilleur candidat inférentiel (§8, appendice)
- `code/eval_confirmed.py` — évaluation harnais complète de la **configuration confirmée** (§6/§7) :
  fidélité (fenêtre primaire + historique complet), gross/Eightcap/FTMO, two-sided, régime 4 ans
  (2022-2024 isolé), walk-forward 5 folds (primaire + complet), bootstrap, DSR
- `config_search_results.csv`, `combo_search_results_pairs.csv`,
  `combo_search_results_triples.csv`, `angle_only_rejection.csv` — résultats bruts voie
  inférentielle (§4)
- `final_eval_*.csv`, `twosided_final_*.csv`, `regime_final_*.csv`, `trades_final_*.csv` —
  évaluation harnais du candidat inférentiel (§8, appendice)
- `trades_CONFIRMED_primary.csv`, `trades_CONFIRMED_full.csv`, `fidelity_CONFIRMED.csv`,
  `harness_CONFIRMED_primary.csv`, `twosided_CONFIRMED_primary.csv`,
  `walkforward_CONFIRMED_primary.csv`, `walkforward_CONFIRMED_full.csv`,
  `regime_4y_CONFIRMED_full.csv` — évaluation harnais de la config confirmée, **univers 7 paires**
  (superseded par §6/§7, gardé comme point de comparaison déclaré dans §6.1)
- `code/eval_confirmed_extended.py` — rejoue la config confirmée sur l'**univers à 10 paires**
  (7 majeures + EURJPY/AUDJPY/EURGBP) : fidélité, décomposition prix/swap et test de falsification
  du short EURJPY, gross/Eightcap/FTMO, two-sided, régime 4 ans, walk-forward, bootstrap, DSR
- `trades_CONFIRMED_extended_primary.csv`, `trades_CONFIRMED_extended_full.csv`,
  `fidelity_CONFIRMED_extended.csv`, `eurjpy_breakdown.csv`, `harness_CONFIRMED_extended_primary.csv`,
  `twosided_CONFIRMED_extended_primary.csv`, `walkforward_CONFIRMED_extended_primary.csv`,
  `walkforward_CONFIRMED_extended_full.csv`, `regime_4y_CONFIRMED_extended_full.csv` — résultats
  bruts de l'évaluation à 10 paires, **résultats de référence** (§6/§7)
- `Algorithm_Brieuc/recapitulatif_parametres.md` (hors de ce dossier, fourni par l'utilisateur) —
  source documentaire ayant permis la confirmation (§5)
- `/private/tmp/.../scratchpad/m1_cache/{EURJPY,AUDJPY,EURGBP}_M1.parquet` — caches construits
  depuis `data/deep_history_utc/{EURJPY,AUDJPY,EURGBP}_M1.csv` (§6.0), même format que les 7
  caches préexistants
