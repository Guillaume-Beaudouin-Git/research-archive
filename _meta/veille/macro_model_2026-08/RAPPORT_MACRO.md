# Deep dive — modèle macro `macro_score_overview.ipynb` (Dedale, brieuctrader)

Δn_tests = **0** (lecture de travail existant + reconstructibilité ; aucune hypothèse testée sur nos
données). Suite de `_meta/veille/dedale_notebooks_2026-08/RAPPORT.md` (survol des 8 notebooks) —
ce rapport ne refait pas ce travail, il approfondit `macro_score_overview.ipynb` et répond aux 4
questions non résolues par le premier passage.

## Résumé — 4 lignes

1. **Spécification** : score de surprise macro (`surprise = actual − consensus`, brut, non z-scoré)
   agrégé par noyau de décroissance exponentielle `e^{-λΔt}` (λ/half-life **jamais chiffrée**,
   symbolique uniquement) en score par indicateur → catégorie (5) → devise → paire (différence
   base−quote plus un résidu ~0.3-0.4 pt non expliqué). Grinold IR = TC×IC×√BR, avec **TC=0.20
   reconstruit par ratio exact** (jamais affiché dans le notebook, jamais mentionné dans la vidéo).
2. **Moteur récupérable : NON** — absent des 7 commits, de la branche unique, des 6 forks (tous à
   l'identique du HEAD upstream ou plus anciens), des 0 gists, du seul autre repo de l'auteur. C'est
   très probablement le backend du produit payant **Hawkline Vision (79 €/mois)**.
3. **Verdict IJR chiffré** : à IC=0.103 (AUDNZD, cas MAX affiché, pas la médiane), σ_target=0.10
   (canonique maison), **le résultat dépend à 100% d'une fréquence de rebalancement non divulguée**
   — PASS jusqu'à ~338 trades/an à 0.75 bps (Eightcap Raw), PASS seulement jusqu'à ~31 trades/an à
   2.48 bps (FTMO) ; pris au pied de la lettre (breadth=1755 = fréquence de trade), **ÉCHEC net aux
   deux coûts** (ratio 1.32× et 0.40×, cible ≥3×).
4. **Verdict** : **NON reconstructible en l'état** — calendrier de consensus macro gratuit et
   profond est le vrai point dur, pas le calcul. Angle précis, données manquantes et Δn_tests
   ci-dessous (§6).

---

## 1. Spécification reconstruite du modèle macro

### 1.1 Données d'entrée — `fetch_macro_events()`

Signature reconstruite depuis l'usage (cellule 2) :
```
from models.data_pipeline import fetch_macro_events
macro_events = fetch_macro_events()          # DataFrame à colonnes MultiIndex (country, event)
macro_events['United States', 'Inflation Rate YoY']   # -> sous-DataFrame
```
Colonnes de la sous-table : `datetime, country, event, surprise, trend, actual, consensus,
previous, forecast`.

**Source confirmée hors-notebook** : description de la vidéo YouTube associée (§3) —
*« Site pour trouver des datas macro : tradingeconomics.com »*. Cohérent avec les noms de colonnes
(`consensus`/`forecast`/`previous`/`actual` est exactement le vocabulaire du calendrier économique
TradingEconomics, pas celui de ForexFactory ou Investing.com qui n'ont pas de champ `forecast`
distinct du `consensus`).

**Définition de la surprise reconstruite par arithmétique exacte sur les valeurs affichées** :
- `surprise = actual − consensus`, en **unités brutes de l'indicateur** (points de %, ou emplois
  bruts pour NFP — 256000−160000=96000 ✓), **PAS z-scoré, pas normalisé par la volatilité
  historique de la surprise de cet indicateur**. Vérifié sur 10/10 lignes visibles (CPI + NFP).
- `trend = actual − previous` (momentum vs. dernière publication), même logique, brut. Vérifié sur
  10/10 lignes (ex. NFP ligne 116 : 256000−212000=44000 = trend affiché).
- `forecast` est un champ **distinct** de `consensus` dans les données mais n'apparaît dans aucun
  calcul visible des cellules suivantes — rôle indéterminé (résidu du provider, non utilisé par le
  modèle affiché, ou utilisé dans `f(ΔZ)` qui est invisible).

### 1.2 Le noyau de décroissance exponentielle

Formule (cellule 3, texte intégral) :
```
S_i(t) = Σ_k  w_ik · ξ_ik · e^{−λ(t − t_ik)}          avec ξ_ik = f(ΔZ_ik)
```
- `i` = indicateur, `k` = k-ième événement de cet indicateur, `t_ik` = timestamp de l'événement.
- `ΔZ_ik` = surprise brute (§1.1). `ξ_ik = f(ΔZ_ik)` = **« choc informationnel filtré »** — la
  fonction `f` (normalisation/winsorisation/z-score plausible, jamais montrée) vit dans le module
  absent. C'est elle qui explique l'écart d'échelle entre une surprise CPI brute de 0.001 et un
  score agrégé affiché à −0.4248 (cellule 11) : il y a nécessairement une mise à l'échelle non
  triviale entre `ΔZ` et `ξ`.
- `w_ik` = poids par événement, **« fitté avec du ML (cf De Prado) »** — texte du notebook, aucune
  implémentation visible, aucun horizon de fit indiqué (walk-forward ? in-sample unique ?).
- `λ` (taux de décroissance, lié à la half-life `h`) — **AUCUNE valeur numérique n'apparaît nulle
  part dans le notebook** (7 cellules markdown consacrées à justifier qualitativement pourquoi une
  décroissance exponentielle plutôt qu'une moyenne simple ou un Hawkes, zéro calibration montrée).
  C'est le paramètre le plus important pour juger la feasibility (il fixe l'horizon effectif de la
  stratégie) et il reste **totalement indéterminé** depuis les sources publiques.
- Le notebook argumente explicitement (cellules 4-6) que ce n'est **pas un Hawkes** (pas de
  feedback/branching ratio) mais un **« Linear Impact Kernel »** — un système événement→impact→
  agrégation sans auto-excitation. Choix défendu correctement (une surprise NFP ne cause pas
  statistiquement une autre surprise NFP) — c'est la seule partie du raisonnement qui est
  argumentée avec un contre-exemple explicite plutôt que par assertion.

### 1.3 Agrégation — `aggregate_scores(full=False)`

Signature reconstruite :
```
from score_payload import aggregate_scores
indicators_df, currencies_df, pairs_df = aggregate_scores(full=False)
```
- `indicators_df` : indexable par clé `"Country/Indicator"` (ex. `'United States/Inflation Rate
  YoY'`) → **scalaire** = `S_i(t)` courant pour cet indicateur (« delta par rapport à 0, baseline
  du processus »). Confirme que `μ=0` est la baseline implicite mentionnée en cellule 3.
- `currencies_df` : indexé par **Devise** (8 devises : USD, EUR, CHF, GBP, JPY, CAD, AUD, NZD),
  colonnes = 5 **catégories** macro (`Confiance, Croissance, Inflation, Taux, Emploi`) + `Score`
  total. **`Score` ≠ somme des 5 catégories** (vérifié : USD somme catégories = −15.89 vs Score
  affiché −3.18) → il y a une pondération/normalisation supplémentaire entre catégories, non
  disclosed (poids inégal par catégorie, ou cap/winsorisation du total).
- `pairs_df` : indexé par **Paire** (28 paires croisées des 8 devises), même structure de colonnes.
  Test arithmétique : `pairs_df['EURUSD'].Score` (3.00) = `currencies_df.loc['EUR'].Score` (−0.18)
  − `currencies_df.loc['USD'].Score` (−3.18) = **3.00, exact**. Mais sur EURGBP/EURAUD/EURNZD le
  même calcul laisse un **résidu constant ≈ +0.35/+0.36** entre le score pair affiché et la
  différence devise−devise calculée à partir des colonnes arrondies à 2 décimales (ex. EURGBP :
  différence calculée −8.07 vs pair affiché −7.71). Deux explications possibles, indiscernables
  sans le code : (a) accumulation d'erreur d'arrondi sur les colonnes à 2dp affichées (les valeurs
  réelles ont plus de précision), (b) un terme spécifique-paire additionnel au-delà de la simple
  différence de scores devise. **Le mécanisme exact de construction de paire reste indéterminé.**

### 1.4 Décomposition de Grinold — `run_analysis(as_of=date)`

Signature reconstruite :
```
from models.statistical_analysis import run_analysis
df_stats, _ = run_analysis(as_of=datetime.now().date())
# df_stats columns (au moins) : pair, acc_high, IC, breadth, IR — plus d'autres colonnes non
# affichées (le notebook slice avec df_stats[['pair','acc_high','IC','breadth','IR']])
```
Seules 2 des 28 paires (probablement 2 des N évaluées par `run_analysis`) sont montrées — **le
max et le min affichés, choisis après coup** :

| Paire | acc_high | IC | breadth | IR |
|---|---|---|---|---|
| AUDNZD | 0.5527 | 0.10347 | 1755 | 0.86690 |
| EURGBP | 0.5036 | −0.03240 | 1676 | −0.26529 |

**Découverte forensique — TC reconstruit par ratio exact, jamais affiché dans le notebook** :
la formule affichée est `IR = TC × IC × √BR` mais aucune colonne `TC` n'apparaît en sortie. En
recalculant `IC × √breadth` :
- AUDNZD : 0.10347 × √1755 = 0.10347 × 41.893 = 4.3345 → IR affiché 0.86690 → **ratio = 5.0002**
- EURGBP : −0.03240 × √1676 = −0.03240 × 40.939 = −1.3264 → IR affiché −0.26529 → **ratio = 5.0002**

Le ratio est identique à 4 décimales sur les deux seules paires observables, ce qui implique un
**TC constant = 1/5 = 0.20**, appliqué uniformément à toutes les paires — alors que le texte du
notebook (cellule 14) définit TC comme *« capacité à implémenter fidèlement la position… après
slippage, VaR, etc. »*, donc censé varier avec la liquidité de chaque paire. En pratique **TC est
une constante fixe non estimée**, pas un TC réellement fitté par instrument. C'est précisément le
paramètre que leur propre cellule 14 identifie comme critique (*« si TC est nul, alpha théorique
mais inexploitable »*) — et c'est celui qui n'est ni calculé ni justifié.

Ni la période d'évaluation, ni l'horizon de rendement forward utilisé pour l'IC, ni un test
walk-forward/OOS ne sont visibles dans les sorties — `run_analysis(as_of=...)` suggère un design
point-in-time mais rien ne prouve que l'IC affiché est autre chose qu'un fit in-sample sur tout
l'historique disponible.

### 1.5 Ce qui reste indéterminé (résumé)

| Inconnue | Impact |
|---|---|
| λ / half-life numérique | fixe l'horizon effectif de la stratégie — sans elle, impossible de dériver la fréquence de rebalancement réelle |
| `f(ΔZ)` — fonction de normalisation de la surprise | explique l'écart d'échelle brut→score, invérifiable |
| `w_ik` — poids ML « à la De Prado » | méthode de fit, période de fit, walk-forward ou non — invérifiable |
| Construction exacte de `pairs_df.Score` | résidu ~0.35 pt non expliqué sur 3/3 paires EUR testées |
| Horizon de rendement forward pour l'IC | daily ? weekly ? — détermine directement le sens du breadth |
| Fréquence de rebalancement réelle (≠ breadth) | **variable la plus déterminante pour le verdict IJR (§4)** |
| Période d'évaluation / walk-forward | aucune preuve d'OOS, `as_of` suggère point-in-time sans le confirmer |

---

## 2. Le moteur est-il récupérable ? NON

Vérifié directement via `gh api` (2026-08-31) :

- **Commits** : 7 au total sur la branche unique `main`, dernier `80b95838` (« macro model »,
  2025-07-09) qui ne touche QUE `Python/macro_score_overview.ipynb` — aucun commit n'a jamais
  ajouté puis retiré `models/` ou `score_payload.py`.
- **Branches** : une seule (`main`). Aucune branche de travail oubliée.
- **6 forks** (`OptiWealthSolutions`, `BE-FARAD`, `okajonathan7-hub`, `RealMammon`,
  `andrecng/Brieuc-(third party)-work`, `graigdev`) : 5/6 sont au SHA exact du HEAD upstream (identiques,
  zéro divergence, zéro commit propre), le 6e (`graigdev`) est **antérieur** à l'ajout du notebook
  macro (dernier commit `c70183d7`, avant `macro model`). **Aucun fork ne contient le moteur.**
- **Gists** : `public_gists: 0` sur le compte `brieuctrader`.
- **Autres repos** : `public_repos: 1` (seulement `Dedale`).
- **Recherche de code GitHub globale** (`score_payload`, `aggregate_scores`, `fetch_macro_events`) :
  seuls matchs = le notebook lui-même. Aucun autre dépôt public dans l'index GitHub ne contient ces
  identifiants.

**Explication la plus probable de la fermeture du moteur** : la description YouTube (§3) et le
site associé pointent vers **Hawkline Vision** (`hawklinevision.com`), un terminal payant
**79 €/mois** (ou 790 €/an) dont l'un des modules annoncés est explicitement un
**« Macro Calendar : Upcoming economic events ranked against historical performance »**. Le moteur
`data_pipeline.py`/`score_payload.py`/`statistical_analysis.py` est très vraisemblablement le
backend de ce produit commercial — sa fermeture n'est pas un oubli, c'est structurel : ouvrir le
moteur ouvrirait le produit payant.

---

## 3. Sources publiques de l'auteur

Profil GitHub (`brieuctrader` = **the third-party author**, bio « Amor fati », localisation Bali, blog =
`youtube.com/@brieuctrader`) renvoie vers :
- **YouTube** — vidéo dédiée trouvée et confirmée : **« Comment créer un MODÈLE MACRO en TRADING ?»**
  (`youtube.com/watch?v=Y4wAaoGfp_8`), datée exactement du jour du commit `macro model`
  (2025-07-09). Chapitrage dans la description : `00:00 Explications` / `25:00 Résultats` — même
  structure que le notebook (théorie d'abord, puis les mêmes sorties chiffrées).
  - **Transcript non récupérable** (YouTube bloque désormais l'endpoint `timedtext` sans session
    signée valide — testé, 200 OK mais `content-length: 0`). Pas de `yt-dlp` disponible dans
    l'environnement. Renoncé après 2 tentatives pour rester dans le cadre lecture-seule sans
    inscription.
  - **La description de la vidéo EST récupérable (HTML statique) et contient l'information la plus
    utile de tout ce point** : *« Site pour trouver des datas macro : tradingeconomics.com »* —
    confirme directement la source de données du §1.1, et *« Plateforme Hawkline :
    hawklinevision.com »* — confirme le produit commercial du §2.
- **Discord** (`discord.gg/cT8DFFUcpB`) — lien redirigeant vers `discord.com/invite/...`, non
  approfondi (lecture d'un salon Discord nécessite une session authentifiée même pour la preview
  publique dans la plupart des cas ; hors mandat lecture-seule-sans-compte).
- **Instagram** (`instagram.com/brieuctrader`) — profil listé, non exploré en détail (peu probable
  d'y trouver une explication technique du modèle vs. une vidéo YouTube dédiée de 25+ minutes déjà
  identifiée).
- **Site `brieuctrader.com`** — inaccessible au moment du test (connexion réinitialisée) ; le lien
  YouTube et Hawkline suffisent à couvrir la question posée.
- **Transcripts locaux `Algorithm_Brieuc/Transcript_Vidéos_Brieuc.md`** — vérifié (`grep -i macro`
  = 0 résultat) : ce fichier local est la formation MQL5 de base (variables, fonctions, syntaxe),
  **ne couvre pas** le modèle macro. Les promesses « je ferai une vidéo là-dessus » qu'il contient
  concernent d'autres sujets (formations avancées) — aucune ne correspond au modèle macro, dont la
  vidéo existe déjà séparément et a été trouvée par recherche directe (ci-dessus).

**Conclusion §3** : aucune explication technique supplémentaire du moteur n'est publiquement
accessible au-delà du notebook et de la source de données confirmée (TradingEconomics). La vidéo
existe et correspond exactement au notebook (même chronologie, même structure), donc n'apporte
vraisemblablement rien de plus que ce qui est déjà dans les cellules markdown — hypothèse
raisonnable étant donné qu'un créateur de contenu ne divulguerait pas plus à l'oral que ce qu'il
laisse dans le notebook public qui accompagne la vidéo, sur un modèle qui alimente son produit payant.

---

## 4. Verdict IJR chiffré

Application du gate maison (`Forex/research/archived/strategy_f2_asian_breakout/data_setup.py:483-511`,
implémentation canonique de la formule citée dans `CLAUDE.md`) :
```
gross_alpha_annuel = 0.40 × IC × √N × σ_target      (σ_target canonique = 0.10)
annual_cost_drag    = cost_frac_RT × N
gate_ratio           = gross / drag                  (PASS si ≥ 3.0)
```
avec **IC = 0.103467** (AUDNZD, la MEILLEURE des 2 seules paires visibles — traité explicitement
comme **cas maximal d'échantillon**, pas une médiane, conformément à l'avertissement de la mission).

Le point bloquant : **`breadth` (1755) et la fréquence de rebalancement/trade (N pour le coût) ne
sont PAS la même quantité chez Grinold**, et le notebook Dedale ne dissocie jamais les deux — il
alimente le même nombre dans `√BR` (breadth informationnelle) sans jamais dire à quelle fréquence
la position est réellement tournée. Faute de cette donnée, le calcul est fait pour **une grille de
N plausibles**, du monthly-ish au « littéralement 1755 trades/an » :

| N (trades/an) | Interprétation | gross annuel | drag @0.75bps (Eightcap) | ratio | drag @2.48bps (FTMO) | ratio |
|---|---|---|---|---|---|---|
| 12 | rebal mensuel | 1.43% | 0.09% | **15.9× PASS** | 0.30% | **4.8× PASS** |
| 31 | crossover FTMO (calculé) | 2.30% | — | — | 0.77% | **3.0× PASS (limite)** |
| 52 | rebal hebdo | 2.98% | 0.39% | **7.7× PASS** | 1.29% | 2.3× **FAIL** |
| 252 | rebal quotidien (convention « daily ») | 6.57% | 1.89% | **3.5× PASS (limite)** | 6.25% | 1.1× **FAIL** |
| 338 | crossover Eightcap (calculé) | 7.61% | 2.54% | **3.0× PASS (limite)** | — | — |
| 1755 | breadth pris au pied de la lettre = N | 17.34% | 13.16% | 1.3× **FAIL** | 43.52% | 0.4× **FAIL** |

**Lecture** : le `gross_alpha` croît en `√N` alors que le coût annuel croît **linéairement** en `N`
— donc le ratio se dégrade structurellement à mesure que N augmente (même dynamique que celle déjà
documentée dans `data_setup.py` pour F2 : *« gate_ratio decreasing in N »*). Résultat :
- **Au tarif institutionnel-adjacent Eightcap Raw (0.75 bps)**, le modèle **passe** le gate jusqu'à
  une fréquence de rebalancement proche du quotidien (~338 trades/an) — cohérent avec un système où
  la position est mise à jour chaque jour ouvré selon le score courant.
- **Au tarif retail FTMO (2.48 bps)**, le modèle ne passe **que jusqu'à ~31 trades/an**, soit une
  cadence proche du **mensuel** — presque exactement la cadence de Strategy A (28 j).
- **Pris au pied de la lettre** (breadth=1755 traité comme fréquence de trade réelle, soit ~7
  trades/jour ouvré — physiquement peu plausible pour un score macro qui ne bouge qu'à la
  publication d'indicateurs mensuels/trimestriels), le modèle **échoue nettement aux deux coûts**.

**Le verdict n'est donc PAS binaire — il est conditionnel à une variable que Dedale ne divulgue
jamais.** Sur l'hypothèse la plus défendable (un score à décroissance lente, cellule 13 filtre
explicitement `|Δ| > τ` pour ne trader que les déséquilibres nets — ce qui suggère une fréquence
BIEN EN DESSOUS du quotidien, plausiblement mensuelle à l'échelle d'une seule paire), **le modèle
franchit le gate à IC=0.103 aux deux coûts**, mais ce IC est le meilleur de 2 (probablement de 28)
paires affichées — sous AMTP/Šidák sur ≥8 paires testées, l'IC corrigé tomberait significativement
sous 0.103, ce qui referme la fenêtre de passage à la cadence hebdo/quotidienne et repousse le
seuil de survie vers une cadence encore plus lente.

### Confrontation aux kills existants — démontrée, pas supposée

- **L43 (FX intraday retail cost-dead, ratio gross/cost_p95≥1.5 requis, meilleur observé 0.36)**
  — **ne s'applique PAS mécaniquement ici**. L43 est bornée à des edges **intraday/session** dont
  le gross par trade est de l'ordre du bp. Le modèle Dedale est explicitement **multi-session**
  (cellule 10 : *« le marché continue de digérer l'info pendant plusieurs sessions »*), donc son
  gross par position tenue est d'un ordre de grandeur différent — c'est exactement ce que confirme
  le calcul ci-dessus : à cadence mensuelle le ratio est 15.9×/4.8×, très au-dessus du 1.5× requis
  par L43 pour l'intraday. **Mécanisme d'échappement démontré : horizon de tenue, pas magie.**
- **L34 (flow-anchored FX = tier institutionnel seulement, le seul two-sided réel meurt au coût
  retail, besoin <1bp/jambe vs 2.48 mesuré)** — **ne s'applique pas non plus par construction** :
  L34 concerne un edge ancré sur du **flux d'ordre / microstructure HFT**, alors que le score
  Dedale est ancré sur des **surprises macro publiques calendaires**, mécanisme totalement
  différent (pas de course à la latence). En revanche, la **leçon générale de L34** — coût retail
  vs institutionnel change le verdict — **s'applique bel et bien** ici de façon numérique : c'est
  exactement le delta entre la colonne Eightcap (PASS jusqu'à ~338/an) et la colonne FTMO (PASS
  seulement jusqu'à ~31/an) dans le tableau ci-dessus.
- **Carry G10 mort post-GFC** — mécanisme non pertinent (différentiel de taux vs. surprise
  d'indicateur), aucun recouvrement.

**Conclusion §4** : le modèle macro échappe aux 3 kills existants **par un mécanisme démontré**
(horizon multi-session ≠ intraday pour L43 ; signal public calendaire ≠ flow HFT pour L34 ; carry
différentiel ≠ surprise macro), mais reste **structurellement contraint par le même facteur
générique que L34/L43** (coût retail vs. tier d'exécution), et le verdict PASS/FAIL dépend d'une
variable (la fréquence de rebalancement réelle) que ni le notebook ni la vidéo ne divulguent.

---

## 5. Reste du dépôt — ce que le rapport précédent a manqué

Le rapport précédent (`dedale_notebooks_2026-08/RAPPORT.md`) couvre bien les 8 notebooks `.ipynb`
mais **omet deux fichiers non-notebook** du dossier `Python/`/`MetaTrader5/` :

- **`Python/move_files.py`** (34 lignes) — utilitaire trivial : déplace tous les `.csv` d'un dossier
  source vers un dossier `backtest_data/` de destination, dédoublonnage par nom de fichier. Rien de
  méthodologique, `source_root`/`destination_root` laissés vides (`r""`) — code jamais paramétré
  pour un usage réel, probablement un script jetable de rangement local. Aucun intérêt à reprendre.
- **`MetaTrader5/EXPORT_TRADE_HISTORY_CSV.mq5`** (120 lignes, encodage UTF-16) — export propre de
  l'historique MT5 vers CSV. Technique correcte et directement réutilisable : **dédoublonnage par
  `position_id`** (pas par ticket de deal individuel — évite de compter deux fois une position
  scale-in/scale-out), **agrégation explicite des jambes IN/OUT** (volume, prix, SL/TP côté IN ;
  prix de clôture côté OUT), et **séparation profit / swap / commission** en 3 colonnes distinctes
  avant somme en `total_pnl` — exactement la discipline qu'on impose nous-mêmes (`swap` mesuré
  séparément, jamais mélangé au P&L prix, cf. L28/L36). Convertit aussi le P&L en pips via
  `tick_value`/`tick_size`/`points`, ce qui est la bonne manière de comparer des trades multi-
  instruments sur une échelle commune. **Réutilisable tel quel** comme gabarit d'export MT5 si on
  devait un jour opérer un compte MT5 hors EA (le nôtre exporte différemment, `ftmo_live/`).

Les 6 notebooks (`Ornstein-Uhlenbeck`, `alpha_decay`, `correlations`, `monte_carlo`,
`supp_res_gold_btc_backtest`, `mt5_backtest`, `info_vs_structural_edge`) ont déjà été correctement
évalués dans le rapport précédent — relecture de leurs sorties dépouillées ne fait apparaître aucun
élément supplémentaire notable (les défauts déjà identifiés — exécution même-barre du backtest or/
BTC, MLE OU non testée statistiquement, absence de coûts dans `monte_carlo` — sont exacts et
complets). Rien à ajouter sur ce périmètre.

---

## 6. Reconstruire ou pas — verdict final

**NON reconstructible à l'identique, et non prioritaire à reconstruire même partiellement dans
l'immédiat.** Raisons, par ordre de poids :

1. **Le point dur est la donnée, pas le calcul.** Le noyau exponentiel, l'agrégation par catégorie/
   devise/paire et la décomposition IC×TC×√BR sont tous des morceaux qu'on sait déjà coder (on a
   `fred_loader.py`, `fomc_events.csv`, un cadre IJR déjà implémenté dans
   `strategy_f2_asian_breakout/data_setup.py`). Ce qu'on n'a **pas** : un calendrier de **consensus**
   multi-pays profond et gratuit. `data/raw/fomc_events.csv` est US-only et FOMC-only (pas de
   consensus CPI/NFP/PMI pour 8 devises). `Forex/data/news_events_2020_2025.csv` couvre 2020-2025
   seulement (5 ans, alors que breadth=1755 sur AUDNZD suggère un historique bien plus long si
   c'est un total cumulé). `Forex/data/fred_loader.py` donne des **séries publiées**, pas des
   **surprises vs consensus au moment de la publication** (FRED ne fournit pas le consensus de
   marché ex-ante) — c'est structurellement la mauvaise donnée pour ce modèle précis.
   **Source gratuite qui fournirait le consensus** : **TradingEconomics** a un frontend gratuit
   avec calendrier historique (actual/forecast/previous, mais **le consensus temps-réel au moment T
   n'est PAS dans l'API gratuite** — le tier gratuit ne donne que les valeurs finales, pas
   l'historique de consensus pré-publication, qui est justement le produit payant de
   TradingEconomics/Bloomberg/Refinitiv). Alternative gratuite partielle : **Investing.com**
   (scraping, fragile, ToS restrictif) ou **FRED ALFRED** (real-time vintages — donne les révisions
   mais pas le consensus de marché). **Aucune source gratuite ne donne un historique multi-année de
   consensus pré-publication pour 8 devises** — c'est le vrai goulot d'étranglement, confirmé, pas
   supposé.
2. **Le verdict IJR est déjà favorable dans la meilleure branche (§4)** — donc l'obstacle n'est pas
   "l'edge n'existe probablement pas" (contrairement à L43/L34/carry), il est purement
   d'approvisionnement en données. C'est le profil de cas le plus rare et le plus intéressant
   qu'on ait rencontré cette session : **feasibility économique validée conditionnellement,
   feasibility de données non résolue**.
3. **Si reconstruction future** : angle précis = **score de surprise macro à horizon multi-session,
   testé UNIQUEMENT sur des devises où un historique de consensus gratuit et profond existe**
   (probablement limité aux surprises **US** — NFP/CPI/FOMC ont le meilleur historique gratuit via
   des sources secondaires réputées, ex. `nfpsurprise`-type datasets ou séries composites), avec
   **notre** pipeline (HAC lag-6, walk-forward ≥5 folds, coûts FTMO réels 2.48bps ET Eightcap Raw
   0.75bps en parallèle puisque le §4 montre que le tier de coût est la variable qui décide),
   **breadth et fréquence de rebalancement explicitement dissociées** (ne pas répéter la confusion
   de Dedale), et **AMTP dès qu'on teste plus d'une devise/paire** (le tableau §1.4 n'a montré que
   2 valeurs sur ce qui est probablement 28 — ne jamais publier un IC max sans distribution).
4. **Δn_tests que ça coûterait** : au minimum **1 test pré-enregistré** (une hypothèse macro-surprise
   multi-session, univers restreint aux devises à historique de consensus vérifiable) sous le cadre
   `_automation/feasibility/` existant — mais seulement APRÈS avoir résolu le point dur data (§6.1);
   tant que la source de consensus n'est pas trouvée, tester serait construire sur une donnée
   probablement incomplète ou biaisée (survivor-bias si on reconstruit un "consensus" a posteriori
   à partir de la valeur `previous` ou d'un simple lissage — piège classique qu'on doit éviter
   explicitement).

**Ce que je recommande concrètement** : ne pas ouvrir cette piste maintenant. La ranger comme
**candidat data-gated** (pas mécaniquement mort, pas prêt) : si un accès à un historique de
consensus macro gratuit et profond (>5 ans, multi-devises) est trouvé plus tard, ce dossier devient
directement actionnable avec le tableau §4 comme pré-registration de la structure de coût attendue.
