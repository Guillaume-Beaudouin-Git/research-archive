# Pré-enregistrement — Réplication Algorithm_Brieuc (2026-08-28)

Écrit AVANT tout calcul de performance. Grille, instruments, coûts, règles de kill figés ici ;
tout écart en cours de route sera noté dans RAPPORT.md avec sa justification, pas silencieusement
réabsorbé dans ce fichier.

## Amendement 2026-08-28 (après le pilote EURUSD 2022-2024, avant le run complet)

Deux changements matériels décidés en cours de route, notés ici plutôt que réécrits en silence
dans le corps du document :

1. **Univers étendu de 6 à 11 instruments** — le pilote (EURUSD seul, 2 ans) ne permettait aucune
   conclusion cross-instrument, or ces cinq EA sont des motifs génériques dont le test décisif est
   la **cohérence cross-instrument**, pas la performance sur un seul actif. Ajout de 4 FX majors
   (AUDUSD, USDCHF, USDCAD, NZDUSD) et d'un 3e indice (US100). Univers final et fenêtres
   d'analyse : voir le tableau §Instruments ci-dessous (mis à jour, contrôle L60 refait sur les 5
   nouveaux instruments — USDCAD et NZDUSD reculés à 2011-01-01, >10% de barres à fourchette nulle
   avant cette date).
2. **MAcroisement — correction d'indexation, PAS un changement de spec.** Le bug #8 du journal ci-
   dessous ("inversion de sens") reposait sur une lecture erronée de `CopyBuffer` en supposant la
   convention "index 0 = barre courante" ; le tableau récepteur du code source n'étant PAS déclaré
   `ArraySetAsSeries`, MQL5 le remplit en ordre chronologique direct, ce qui inverse la lecture des
   deux indices. Relu correctement, le code implémente un croisement EMA standard (golden cross ⇒
   achat), pas une stratégie contrarian. Le variant diagnostic "sens_inverse" initialement prévu
   est retiré (il aurait reproduit la lecture fausse) ; le spec de référence §5 est corrigé en
   conséquence — voir le journal de bugs mis à jour.
3. **Exécution en checkpoints** — `resultats.csv` est maintenant réécrit après CHAQUE instrument
   traité (DSR recalculé sur la famille des instruments déjà complétés), pas seulement à la toute
   fin, pour qu'un run interrompu laisse un livrable partiel exploitable.

## Question

Cinq EA MQL5 tiers (formation gratuite MetaQuotes, dossier `Algorithm_Brieuc/`, identiques au repo
public `brieuctrader/Dedale`) tiennent-ils encore une fois reproduits fidèlement en Python et testés
au harnais du dépôt (excess returns non applicable ici — instruments FX/indices sans rendement de
cash à soustraire au niveau trade ; HAC lag-6, WF ≥5 folds, AMTP/DSR, block-bootstrap, coûts réels) ?
Trois EA sont exclus d'office (martingale/grid/garde-fou) sans dépense de calcul.

## Candidats testés (5)

1. **LondonBreakout** — range H1 asiatique (10 barres) → buy stop/sell stop symétriques à l'ouverture
   de Londres, SL 20 / TP 40 "pips", expiration à la clôture de Londres. Two-sided par construction
   (les deux ordres sont posés ensemble).
2. **DailyBreakout** — high/low D1 de la veille → buy stop/sell stop symétriques, SL au côté opposé
   du range, pas de TP fixe (0), trailing stop 1:1 dès mise en profit. Two-sided par construction.
3. **BollingerBands** — clôture H4 hors bande (20, 2σ) + filtre MA200 H4 ⇒ FADE dans le sens de la
   tendance longue (close > upper ET prix < MA200 ⇒ vente ; close < lower ET prix > MA200 ⇒ achat).
   Risk-based sizing (`RISK_IN_PCT`). Two-sided par construction (les deux branches existent), mais
   chaque branche est conditionnée par le régime MA200 → à auditer séparément long vs short.
4. **FVG** — Fair Value Gap ICT sur M1 (`low[0]>high[2]` haussier / `high[0]<low[2]` baissier), ordre
   limite au milieu du gap, SL 5 / TP 40 "pips", expiration à la fin du jour (le fill peut arriver
   n'importe quand avant expiration ; une fois rempli, pas d'expiration sur la position).
5. **MAcroisement** — croisement EMA21/EMA55, SL 20 / TP 40 "pips", une position à la fois.

## Exclus d'office (0 calcul)

- **Abruti.mq5** — `lot_size = last_volume * LOT_MULTIPLIER` après une perte : martingale pure,
  EV structurellement nulle avant ruine (déjà gravé, `personal_book_research_2026-07`).
- **GridBotRSI.mq5** — `lotMultiplier = 2` sur une grille RSI : martingale déguisée en grille,
  même vice que ci-dessus.
- **PropFirmProtector.mq5** — pas une stratégie : un garde-fou de risque (freeze au DD daily/max).
  Rien à backtester.

## DédaleFormation.mq5 — machine à optimiser, non testée

806 lignes, pivots W1 + TDI sur 5 timeframes, **15 booléens de signal tous `false` par défaut**
(`TDI_TIMEFRAME{0-4}_CROSS/TREND/ANGLE`) ⇒ 2¹⁵ = 32 768 configurations activables. Toute exécution
qui choisit une configuration "qui marche" est du data-mining post-hoc (territoire L20/DSR). Ce
document ne teste **aucune** configuration : documenté comme classe d'objet (machine à optimiser),
pas comme résultat. Si une session future veut le tester, la règle du brief s'applique : UNE seule
config, choisie et écrite AVANT de toucher la donnée, justifiée par le transcript — pas ici.

## Instruments (11, univers étendu au 2026-08-28 — voir Amendement)

| Instrument | Classe | Fenêtre d'analyse | Raison |
|---|---|---|---|
| EURUSD | FX 5 décimales | 2008-01-01 → 2026-06-01 | benchmark FX standard, formation calibrée dessus |
| GBPUSD | FX 5 décimales | 2008-01-01 → 2026-06-01 | 2e FX majeure, session Londres native |
| AUDUSD | FX 5 décimales | 2008-01-01 → 2026-06-01 | breadth cross-instrument |
| USDCHF | FX 5 décimales | 2008-01-01 → 2026-06-01 | breadth cross-instrument |
| USDCAD | FX 5 décimales | **2011-01-01** → 2026-06-01 | breadth ; L60 >10% fourchette nulle avant 2011 |
| NZDUSD | FX 5 décimales | **2011-01-01** → 2026-06-01 | breadth ; L60 >10% fourchette nulle avant 2011 |
| USDJPY | FX 3 décimales | 2008-01-01 → 2026-06-01 | teste la convention pip 3-décimales |
| XAUUSD | Métal 2 décimales | 2008-01-01 → 2026-06-01 | teste un point-size hors FX/indices |
| US30 | Indice CFD | 2015-01-01 → 2026-06-01 | teste le bug `_Point*10` sur indice (post rampe) |
| US100 | Indice CFD | 2015-01-01 → 2026-06-01 | 2e test indice, tech-heavy |
| GER40 | Indice CFD, session EU | 2015-01-01 → 2026-06-01 | indice session Londres, 3e test indice |

2008/2011/2015 : marge de sécurité après la rampe de densité de chaque source (contrôle L60 par
année, fait avant usage — voir sous-section ci-dessous). LondonBreakout, DailyBreakout,
BollingerBands et MAcroisement tournent sur les 11. **FVG reste restreint à
EURUSD/GBPUSD/USDJPY/XAUUSD** (scope pré-enregistré initial, non étendu aux 5 nouveaux instruments
au 2026-08-28) : la famille est déjà morte par fréquence de coût sur le pilote (Sharpe net
Eightcap −1.7 à −3.6 pour ~2 000-2 700 trades/an) — l'étendre à tout l'univers n'aurait rien changé
au verdict et aurait consommé l'essentiel du budget de calcul du sprint. Décision de scope
explicite, pas un oubli.

### Contrôle L60 (fraction de barres à fourchette nulle, fait avant usage)

Mesuré par année sur les 11 instruments (high==low) : max observé GER40 2013 11.8%, USDCAD 18.1%
(2008) et NZDUSD 16.0% (2008) — ces deux reculés à 2011-01-01 (sous 5% dès 2011). Tous les autres
<9%, la plupart <2%. Aucun instrument exclu ; fenêtres d'analyse choisies pour rester après les pires
années de rampe (voir tableau ci-dessus).

## Point-size / "pip" — résolution explicite de l'ambiguïté `_Point*10`

Le code MQL5 utilise `_Point` (résolu automatiquement par MT5 au symbole réel) donc en exécution
MT5 réelle, un pair JPY 3-décimales n'est PAS cassé par la formule `param*_Point*10` : `_Point`
s'adapte déjà (0.001 pour JPY donne pip=0.01, cohérent). Le bug réel et mesurable est **spécifique
aux indices** : `_Point*10` suppose implicitement une cotation "pip-like" à 4-5 décimales de
fraction ; sur un indice coté à 1-2 décimales, la même formule produit une distance de risque sans
rapport avec la volatilité de l'instrument. C'est CE bug qui est répliqué à l'identique naïf vs
corrigé ; l'ambiguïté JPY est résolue une fois pour toutes par une table de point-size explicite
(même table utilisée dans les deux versions FX) plutôt que rejouée comme une deuxième bascule.

| Instrument | `_Point` (JT réel) | "pip" = 10×`_Point` (formule EA) | Utilisé pour |
|---|---|---|---|
| EURUSD, GBPUSD | 0.00001 | 0.0001 | naïf = corrigé (FX standard) |
| USDJPY | 0.001 | 0.01 | naïf = corrigé (FX standard) |
| XAUUSD | 0.01 | 0.1 | naïf = corrigé (métal, cotation 2 déc.) |
| US30, US100, GER40 — **NAÏF** | 0.01 (hypothèse FX-like, celle qu'un dev qui n'a testé que sur EURUSD coderait implicitement) | 0.1 point indice | reproduction fidèle du bug |
| US30, US100, GER40 — **CORRIGÉ** | — | 1 point indice natif (pas de ×10, le paramètre numérique est réinterprété en points indice bruts) | version de référence |

Conséquence attendue et déclarée AVANT calcul : sur indices, le stop **naïf** sera de l'ordre de
2-20 points sur un instrument dont l'ATR quotidien se compte en centaines de points ⇒ stop-out
quasi immédiat / bruit de spread. C'est la mesure même de l'écart naïf/corrigé demandée par le
brief, pas un artefact à corriger après coup.

## Bugs identifiés et résolution appliquée (journal complet dans SPECS.md)

1. **MAcroisement** — `CopyBuffer(h,0,0,2,arr)` : index 0 = barre en formation, réévaluée à chaque
   tick ⇒ signal papillotant / repaint. **Naïf** : évalué à CHAQUE minute M1 sur la valeur EMA de la
   barre en formation à cet instant (approximé ici par ré-évaluation de la croix EMA sur M1 avec la
   dernière valeur close-to-close disponible à chaque minute, cf. SPECS.md). **Corrigé** : signal
   figé à la clôture de la barre de base (H1, cf. ci-dessous), lu à T-1, exécuté à l'ouverture de T.
   `tradeEnCours` remis à zéro sur `PositionsTotal()==0` (tout le compte) — sans portée hors de cet
   EA seul dans un backtest mono-stratégie, donc sans effet ici (noté, pas un bug actif en solo).
   **Timeframe de base non spécifié dans le code** (`PERIOD_CURRENT`) : résolu à **H1**, déclaré
   avant calcul, car H1 est le choix par défaut du chart MT5 dans le transcript de formation.
2. **BollingerBands** — `iClose(_Symbol,tf,1)` (clôture de la dernière barre FERMÉE) comparé à
   `bbUpper[0]`/`ma[0]` (bande/MA de la barre EN FORMATION, `CopyBuffer` start_pos=0). Désalignement
   d'un bar. **Naïf** : reproduit tel quel (close[1] vs bande[0]). **Corrigé** : close[1] vs
   bande[1] (les deux à la même barre fermée), signal lu à la clôture de bar T-1, exécuté à
   l'ouverture de bar T.
3. **LondonBreakout** — `structLondonOpen.hour = 9` est en heure SERVEUR (EET/EEST), pas UTC ⇒ la
   fenêtre dérive d'une heure selon le DST (L56). **Naïf** : fenêtre fixe 09:00–18:00 UTC toute
   l'année (erreur d'une heure l'été si le serveur est EET/EEST). **Corrigé** : fenêtre ancrée à
   l'heure LONDRES réelle (08:00 Europe/London été comme hiver, ouverture LSE effective en UTC via
   zoneinfo), qui est l'intention manifeste du nom de la stratégie.
4. **FVG** — signal calculé sur `open/high/low/close[0..2]` où index 0 = barre M1 EN FORMATION ⇒
   le "gap" testé n'est pas encore clos, repaint. **Naïf** : reproduit tel quel (bougies 0,1,2).
   **Corrigé** : décalé d'un bar (bougies 1,2,3 — toutes fermées), signal disponible à la clôture de
   la bougie M1 T-1, ordre limite posé à l'ouverture de T.
5. **Partout** — SL/TP fixes en pips, aucune normalisation par la volatilité. Non "corrigé" (ce
   n'est pas un bug de code mais un choix de conception de la formation) ; mesuré indirectement en
   comparant le comportement cross-instrument à SL/TP identiques.
6. **DailyBreakout** — `ask < lastCandleHigh && bid > lastCandleLow` : les ordres stop ne sont posés
   que si le prix courant est encore À L'INTÉRIEUR du range de la veille (garde anti-gap-through).
   Reproduit à l'identique naïf et corrigé (c'est une garde d'exécution valide, pas un bug).
7. **DailyBreakout — sortie (L59)** : `trade.PositionModify` place le SL au prix stop exact
   théorique (breakeven + 1:1 trail). **Toute version (naïve et corrigée) re-price la sortie sur le
   PATH M1 réel** : le fill au stop est le PIRE de {niveau stop théorique, open de la barre M1 qui
   franchit ce niveau} — jamais supposé rempli au prix exact. Part des barres où l'ouverture est déjà
   au-delà du stop rapportée par strat/instrument.
8. **MAcroisement — CORRIGÉ 2026-08-28 (l'entrée initiale de ce journal était une erreur de
   lecture d'indexation, pas un bug du code source — voir §Amendement en tête de fichier)** :
   `CopyBuffer(ema21Handle,0,0,2,ema21)` est appelé sur un tableau déclaré SANS
   `ArraySetAsSeries(...,true)` ⇒ MQL5 le remplit en ordre CHRONOLOGIQUE (`arr[0]`=barre CLOSE la
   plus ancienne des deux, `arr[1]`=barre EN FORMATION la plus récente) — pas dans la convention
   "index 0 = présent" que la lecture initiale supposait à tort. Relue correctement, la condition
   source EST un croisement haussier (golden cross) déclenchant BUY / croisement baissier (death
   cross) déclenchant SELL — la logique standard, pas une inversion. Le seul bug réel reste le
   REPAINT (`[1]` = barre en formation, signal papillotant avant la clôture réelle) — déjà couvert
   par §1. Le variant "sens_inverse" prévu initialement est abandonné (il aurait reproduit la
   lecture erronée, pas une hypothèse indépendante) ; le spec de référence utilise directement la
   logique golden-cross/death-cross (`code/strategies.py::ma_croisement`, corrigé).

## Coûts (3 barèmes, tous rapportés, appliqués par trade via le levier réel)

`cost_R = (cost_bps / 1e4) × leverage`, `leverage = entry_price / |entry_price − stop_price|`
(jamais un levier médian fixe — barrière explicite du brief). Appliqué une fois par trade (aller-retour).

| Barème | bps RT | Teste |
|---|---|---|
| Gross | 0.00 | le signal existe-t-il ? |
| Eightcap Raw | 0.75 | véhicule bon marché (mesuré cette semaine) |
| FTMO retail | 2.48 | véhicule cher |

## Sizing & mesure de performance

Risque fixe par trade = 1% de l'équité courante (choix méthodologique déclaré, pas dans le code
source — nécessaire pour comparer des EA qui mélangent lot fixe et risk-based sizing sans données de
tick value/contrat réelles). Retour par trade en R-multiples : `R_gross = pnl_price / stop_distance`
(cap à -1R si le stop est le pire remplissage, cf. L59), `R_net = R_gross − cost_R`. Série d'équité :
compounding à 1%×R par trade. Sharpe annualisé en **√(trades/an)** (L47), jamais √252.

## Walk-forward (5 folds, jamais un split unique)

Fenêtre d'analyse par instrument découpée en 5 tranches calendaires contiguës égales (expanding
non pertinent ici — pas de paramètre fitté, SL/TP/périodes sont ceux du cours, aucun entraînement).
Le WF mesure donc la **stabilité temporelle** d'un edge non fitté, pas un train/test classique :
`WF% = fraction des 5 folds à Sharpe net > 0` (barème Eightcap 0.75bp, cohérent avec la convention
RESEARCH_PASS/PROPFIRM_PASS du repo).

## Découpe de régime

Blocs de 4 ans calendaires pour tout survivant du WF (règle du brief), rapportés séparément.

## DSR, placebo, bootstrap

- **n_tests** : chaque (stratégie × instrument × naïf/corrigé) est une hypothèse distincte.
  Univers étendu à 11 instruments (2026-08-28) ⇒ n_tests_principal = 85 (calcul exact dans
  SPECS.md §n_tests, après amendement). Le variant "sens inversé" MAcroisement est abandonné
  (correction d'indexation, pas une hypothèse — voir Amendement en tête de fichier).
- **n_tests_global** avant ce sprint ≈ 1904 (valeur donnée par le brief, chantier Multi_Asset
  post-321). Δn_tests = 85 ⇒ n_tests_global = **1989**, seuil Šidák recalculé et rapporté.
- **DSR** : `dsr.py` du dépôt (racine), `std_sr_trials` = dispersion empirique des Sharpes de la
  famille testée (pas de défaut 1.0), plancher `sampling_noise_floor_sr`.
- **Placebo apparié** : même construction de trade (mêmes timestamps d'entrée, même stop_distance,
  même coût), signe long/short tiré aléatoirement 50/50 (1000 tirages) — détruit l'info directionnelle
  en préservant fréquence/volatilité/clustering. Comparaison Sharpe réel vs distribution placebo.
- **Block-bootstrap** : bloc de 20 trades consécutifs (jamais iid), 2000 ré-échantillons, sur la
  série de R_net, IC95% du Sharpe et de la moyenne R.
- **HAC lag-6** : t-stat Newey-West sur la série de R_net (agrégée mensuellement quand la fréquence
  de trade le permet, sinon directement sur les trades avec Newey-West lag-6 en unités-trade).

## Règles de kill (déclarées avant tout run)

Une combinaison (stratégie × instrument × version) est déclarée **MORTE** et non creusée davantage si
UNE des conditions suit, dans cet ordre :
1. Sharpe **gross** ≤ 0 sur la fenêtre complète → mort mécaniquement, aucun barème de coût ne sauve.
2. Gross positif mais WF% < 50% (moins de la moitié des folds nets positifs au barème Eightcap).
3. Gross et WF passent mais le placebo apparié à signe aléatoire domine (médiane placebo ≥ Sharpe réel).
4. Survit 1-3 : régime 4 ans + DSR + bootstrap rapportés, jugement final sur la conjonction, pas sur
   un seul chiffre.
Aucune stratégie n'est retestée avec des paramètres modifiés dans ce sprint (règle "max 3
modifications" hors-sujet ici : on reproduit, on ne re-fit pas).

## Livrables

`PREREGISTRATION.md` (ce fichier), `SPECS.md` (spec Python non ambiguë par stratégie + journal des
bugs), `resultats.csv` (une ligne par stratégie×instrument×version×barème de coût), `RAPPORT.md`.
