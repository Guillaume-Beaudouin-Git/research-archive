# Audit indépendant — reproduction Python de DédaleFormation.mq5

Rôle : casser la reproduction, pas la valider. Tout est re-dérivé depuis `Algorithm_Brieuc/DédaleFormation.mq5`
(806 lignes, converti UTF-16LE→UTF-8), pas depuis les rapports antérieurs. Code audité :
`Forex/research/active/{dedale_config_2026-08,dedale_strategy_2026-08}/code/`. Tests exécutés dans
`Forex/research/active/dedale_audit_2026-08/code/` (worktree `.worktrees/dedale-audit`, rien poussé/mergé).
Δn_tests = 0 — audit d'une reproduction existante, pas une nouvelle hypothèse de marché.

## Divergences trouvées, classées par effet mesuré sur le R:R

### 1. `IsTradeAllowed()` (ligne 751, filtre ligne 801) bloque STRUCTURELLEMENT 100% des ventes — l'EA réel est long-only

**MQL5 (ligne 801)** : `if(bid < sl + sl_distance_min || ask > tp - tp_distance_min) return false;`
appliqué **identiquement pour achat ET vente**, en dehors du bloc `if(!direction){...}else{...}` (lignes
772-793) qui ne gère que le veto de swap et le hedging.

Pour une vente valide, `sl` = `ResistancePivot` (au-dessus du prix) — c'est une conséquence directe de
`CalculateLotSize(sl - ask)` en ligne 627 : pour que la taille de lot soit positive, `sl > ask ≥ bid` est
obligatoire, sans même regarder `GetTradeInfo`. Donc `bid < sl + sl_distance_min` est **trivialement vrai**
(bid < sl < sl+min) pour toute vente légitime, et `ask > tp - tp_distance_min` l'est tout autant (tp =
support, tp < ask). **Les deux branches du OU sont toujours vraies** → `IsTradeAllowed(1)` retourne
toujours `false`. Aucune vente ne peut jamais être ouverte, quels que soient les autres paramètres
(TDI, swap, spread).

**Notre code** (`intrabar_engine.py:127-129`, `dedale_engine.py:162-168`) implémente un filtre de
distance **symétrique par direction** (`dsl = mid-sl if direction==0 else sl-mid`), qui autorise les
ventes normalement. C'est une divergence, pas un choix délibéré documenté.

**Vérification empirique** (script `code/run_tz_compare.py` + test ad hoc, 8 paires, 2018-01-05→2024-07-29,
config confirmée 8 filtres) : sur les 173 signaux de vente que notre moteur exécute actuellement, **173/173
seraient rejetés par le filtre littéral** ; sur les 242 signaux d'achat, **0/242** sont rejetés. Match parfait
avec la dérivation ci-dessus — pas une coïncidence statistique.

**Confirmation source primaire** — `Backtest brieuc.md`, l'auteur en train de commenter SA PROPRE
courbe d'équité : *« ça suit le prix de dollarienne quoi en gros **c'est que du long c'est que de l'achat
quasiment** »*. Il observe lui-même, sans connaître la cause code, que son backtest est (quasi-)exclusivement
long. Ça correspond exactement au bug ci-dessus.

**Effet mesuré** (retirer les 173 ventes de la reproduction actuelle, sans autre changement) :

| | n | WR | R:R | total (composé) |
|---|---:|---:|---:|---:|
| Baseline actuelle (achat+vente) | 415 | 64,10% | 0,632 | +19,41% |
| **Corrigé (achat seul)** | **242** | **64,88%** | **0,631** | — |
| Cible (12 paires) | 648 | 63,58% | 0,719 | +60,33% |

**Le R:R ne bouge quasiment pas (0,632→0,631)** — achats et ventes ont un R:R quasi identique dans notre
modèle actuel (achat 0,631 / vente 0,634 pris séparément), donc retirer les ventes ne referme PAS l'écart
de R:R. Mais l'effet sur la composition et le compte est sévère : n chute de 415 à 242 (−42%), et surtout
**EURUSD et EURGBP tombent à ZÉRO trade sur toute la fenêtre** dans le modèle corrigé (leurs 173 trades
actuels étaient à 100% des ventes). C'est cohérent avec le régime de taux ECB proche de zéro/négatif
2018-2022 : EUR-base en taux bas ⇒ `swap_long` défavorable sur EURUSD/EURGBP la majorité de la période,
et la vente (seule alternative) est de toute façon bloquée par le bug ci-dessus. **EURUSD et EURGBP sont
structurellement quasi-morts dans le vrai EA sur cette fenêtre.**

**Conséquence directe pour les 4 paires manquantes** (AUDCAD, EURAUD, EURCHF, GBPNZD) : EURAUD et EURCHF
partagent la même jambe EUR-base — elles sont probablement **aussi quasi-mortes** sous le vrai régime
long-only, donc peu susceptibles de combler l'écart de n. AUDCAD et GBPNZD n'ont pas cette jambe EUR et
sont les candidats les plus prometteurs pour retrouver du volume côté achat (AUD et GBP ont eu des
régimes de taux plus favorables au carry que l'EUR sur la période) — priorité si acquisition de données
envisagée, à l'inverse d'EURAUD/EURCHF.

**Correction recommandée** : dans `get_trade_info`/le moteur intra-barre, appliquer le veto direction-
symétrique actuel (garder la logique actuelle pour les ACHATS, qui est correcte), et **forcer le rejet de
toute vente** — pas une modification du filtre de distance en tant que tel (qui doit rester tel quel pour
matcher le bug), mais un simple `if direction == 1: continue` (ou équivalent) documentant explicitement
que c'est un bug de l'EA d'origine, reproduit fidèlement, pas une simplification de notre part.

### 2. La géométrie bid/ask (spread) est totalement absente de notre P&L — et sa réintroduction correcte AGGRAVE l'écart, elle ne le comble pas

**MQL5** : pour un achat, `sl_size = |S-bid|` (ligne 505), `tp_size = |R-ask|` (ligne 506) — le calcul de
la position (ligne 620, `CalculateLotSize(bid-sl)`) utilise BID, mais l'entrée réelle est à ASK
(`trade.Buy(...,ask,...)`, même ligne). MT5 clôture un long en vendant, donc SL/TP se déclenchent sur le
BID.

Dérivation algébrique (spread = sp, ask=mid+sp/2, bid=mid-sp/2) :
- Perte réelle si SL touché = `ask_entrée - sl = sl_size_nominal(bid-based) + spread` → **en unités de
  risque nominal (bid-sl), la perte réelle est `-(1 + spread/sl_size)`, PAS exactement -1R.**
- Gain réel si TP touché = `tp - ask_entrée = tp_size` exactement (déjà mesuré depuis ask, pas de
  contamination supplémentaire).

**Notre code** : `bid=ask=mid` partout dans `get_trade_info` (ligne `dedale_engine.py:161`,
`intrabar_engine.py:125` — les deux passent `mid, mid`), et la sortie se fait exactement au niveau
`sl`/`tp` sans coût. **Toutes nos pertes sont pinnées à exactement -1,000R** (vérifié : `avg_loss_R` mesuré
à 0,9992-1,0003 dans tous les runs de cet audit, jamais autre chose).

**Effet, si on l'ajoutait tel quel** : la perte réelle est TOUJOURS plus négative que -1R (jamais moins),
donc le R:R réaliste est **plus bas** que notre R:R actuel (0,632), pas plus haut. Or notre R:R actuel est
déjà EN DESSOUS de la cible (0,719). **Ajouter le spread au réalisme creuse l'écart, il ne le comble pas.**
Conclusion nécessaire : pour que le 0,719 de l'auteur (probablement déjà mesuré avec spread dans le
Strategy Tester MT5) soit atteignable, la sélection de combo pivot NOMINALE (sans spread, ce que notre
code calcule actuellement) devrait produire un R:R nominal **supérieur** à 0,719 — quelque chose comme
0,75-0,85 selon le ratio spread/sl_size typique — pas 0,632. **L'écart réel à combler est donc plus grand
que ce que les chiffres bruts suggèrent.**

Non testé empiriquement dans cet audit (nécessiterait un vrai spread Eightcap tick-par-tick, absent des
données) — mais la direction de l'effet est sans ambiguïté algébrique. À corriger malgré tout pour la
fidélité globale, en sachant que ça ne règle pas le problème principal.

### 3. Ancrage horaire H4/D1/hebdo — testé, réel, mais dans le mauvais sens pour le R:R

Fait vérifié directement sur `EURUSD_M1.parquet` : le gap hebdomadaire de marché est à **22:00 UTC en
hiver / 21:00 UTC en été**, et le switch de printemps/automne 2023 (19 mars encore 22:00, 26 mars déjà
21:02 ; 22 oct encore 21:00, 29 oct déjà 22:00) **suit le calendrier DST EU (dernier dimanche mars/octobre),
PAS le calendrier US** (2ème dimanche mars / 1er dimanche novembre). C'est exactement Lundi 00:00
EET(hiver)/EEST(été) — cohérent avec la note déjà actée du repo (« MT5 provenance : panels EET/EEST »).

M15/M30/H1 ne sont PAS affectés (2h et 3h de décalage sont des multiples entiers de 15/30/60 min — les
bornes de barre coïncident en UTC avec ou sans ancrage broker). **H4, D1 et la semaine pivot LE SONT**
(2h/3h ne divisent pas 4h ni 24h) — et ce sont exactement les timeframes de 5 des 8 filtres actifs
(`TDI_TIMEFRAME3_CROSS/TREND`, `TDI_TIMEFRAME4_TREND`, `TDI_TIMEFRAME3/4_ANGLE`, + pivot hebdo).

Correction implémentée et testée (`code/intrabar_engine_tzfix.py`, resample sur l'heure murale
`Europe/Bucharest` DST-aware au lieu de `resample("4h"/"1D")` naïf UTC, pivots hebdo `W-MON` broker-local
au lieu de `W-SUN` UTC) :

| | n | WR | R:R | total (composé) |
|---|---:|---:|---:|---:|
| Baseline (ancrage UTC naïf) | 415 | 64,10% | 0,632 | +19,41% |
| **TZFIX (ancrage broker EET/EEST DST-aware)** | **365** | **66,85%** | **0,595** | **+25,89%** |

Résultat : **plus proche de la vraie sémantique MT5 (c'est objectivement le bon ancrage), mais ça éloigne
le R:R de la cible** (0,595 vs 0,719, pire que 0,632) tout en réduisant n (365 vs 648 mis à l'échelle
~432 — pire aussi). Recommandation : **adopter quand même pour la fidélité générale** (c'est la bonne
sémantique MT5, vérifiée empiriquement sur les données, indépendamment de ce test) mais ce n'est
**pas** le mécanisme qui explique le déficit de R:R — à combiner avec la correction #1, pas à la place.

### 4. Sélection de combo pivot dans `GetTradeInfo` (ligne 488-565) — anomalie MQL5 détectée mais REJETÉE par le compte de trades

`if(MathMin(proba_difference) == proba_difference[index])` (ligne 559) est évalué **à l'intérieur** de la
boucle double qui remplit `proba_difference[]` élément par élément. `ArrayResize` initialise à zéro les
nouveaux éléments numériques en MQL5 (comportement documenté) ; `MathMin` opère sur la taille déclarée de
l'array, pas sur son état de remplissage logique. Donc pour PIVOT_NUMBER=2 (4 combos, index 0-3), à
chaque itération avec index<3, le array contient encore des zéros en fin de tableau — `MathMin` est
contaminé par ces zéros et ne peut, sauf coïncidence à `proba_difference==0` exactement, jamais égaler la
valeur qu'on vient de calculer. **Seul le dernier index (i=j=PIVOT_NUMBER-1=1, la paire S2/R2) a un test
"honnête"** (array totalement rempli à ce stade). Dans tous les autres cas, `sl`/`tp` restent à leur
valeur initiale déclarée (`double sl = 0, tp = 0;`, ligne 490) — ce qui, en aval, fait échouer
`IsTradeAllowed` de toute façon (`ask > 0 - tp_distance_min` est trivialement vrai) : le trade est
silencieusement annulé.

Testé (`code/mathmin_bug_engine.py`, réplique littérale : ne peut retourner QUE le combo S2/R2, et
seulement s'il est l'argmin réel des 4) :

| | n | WR | R:R |
|---|---:|---:|---:|
| Baseline (recherche "normale" du min parmi 4) | 415 | 64,10% | 0,632 |
| **MathMin littéral (S2/R2 seul, si argmin)** | **48** | **54,17%** | **0,941** |
| Cible | 648 | 63,58% | 0,719 |

**Le sens de l'effet CONFIRME le mécanisme** (ne garder que les combos larges/proches-de-symétriques
FAIT monter le R:R, 0,632→0,941, dans la bonne direction) — mais l'ampleur est **incompatible avec le
volume déclaré** : n s'effondre à 48 (12x en dessous du besoin), WR tombe sous la cible (54,17% vs 63,58%).
**Rejeté comme explication seule** — soit ce n'est pas exactement comme ça que MT5 exécute (je ne peux
pas compiler du MQL5 ici pour vérifier expérimentalement le comportement runtime réel d'`ArrayResize`+
`MathMin` sur ce cas précis — c'est une DÉDUCTION de la doc, pas une observation directe du binaire),
soit un autre mécanisme compense. **Test définitif recommandé côté utilisateur** : ajouter
`Print(sl, tp)` juste avant le `return` de `GetTradeInfo` dans MetaEditor et lancer le Strategy Tester
sur quelques mois — si `sl`/`tp` valent 0,0 dans une fraction substantielle des barres, le bug est réel et
il faut alors chercher pourquoi le volume réel (648) dépasse largement ce que la version buggée produit
ici (peut-être une différence de compte de paires, de fenêtre, ou de calibrage des filtres actifs que je
n'ai pas testée).

## Vérifié, CONFIRMÉ correct (pas de divergence)

- **`GetTradeInfo` — arithmétique combo S/R et échange d'indices i↔j direction-dépendant** (lignes 496-501
  vs 508-511 du MQL5) : reproduit fidèlement dans `dedale_engine.get_trade_info`, byte pour byte sur la
  logique (vérifié terme à terme, y compris l'asymétrie i↔j entre achat et vente). Pas de bug ici — hors
  le problème #4 ci-dessus qui est un niveau au-dessus (la boucle qui APPELLE cette arithmétique).
- **`IsTradeOpen` (ligne 710) / hedging** : une position par SYMBOLE tous sens confondus quand
  `IS_HEDGING_ALLOWED=false` (vérifié : le veto croisé dans `IsTradeAllowed` bloque bien la direction
  opposée même si elle est vérifiée dans le MÊME tick que l'ouverture). Confirme l'hypothèse de
  l'utilisateur — pas de position long+short simultanée possible sur une paire.
- **`OnTick`/`OnInit` (lignes 114-145)** : aucune garde de nouvelle barre, aucun filtre horaire/jour de
  semaine/news — `OnTick` appelle juste `UpdateBidAsk()` puis `ExecuteTrade()` à CHAQUE tick, sans
  condition. Ça valide le principe du moteur intra-barre M1 (évaluation continue), et confirme qu'aucun
  filtre caché n'existe dans `OnInit`/`InitializeIndicators` (juste la création des 5 handles RSI).
- **`IsTradeAllowed` — le veto de swap lui-même** (lignes 777, 789) : ne contient RIEN d'autre qu'annoncé
  — pas de filtre horaire, pas de jour de semaine, pas de news, pas d'exposition. Le filtre de spread
  (ligne 797, `SPREAD_MAX*10`) et le filtre de distance (ligne 801, voir #1) sont les deux SEULS autres
  vetos, en plus du hedging et du swap.
- **Pivots** (`SupportPivot`/`ResistancePivot`, lignes ~166-222) : formules classiques confirmées
  identiques à notre `load_weekly_pivots` (P, S1=2P-H, S2=P-(H-L), R1=2P-L, R2=P+(H-L)).
- **Le filtre de distance minimale existe bel et bien** (contrairement à ce que l'utilisateur croyait
  avoir vérifié — `SL_DISTANCE_MIN`/`TP_DISTANCE_MIN` par défaut à 10 pips chacun, lignes 96-97, 105-106)
  — mais il vit dans `IsTradeAllowed`, pas dans `ExecuteTrade`, et surtout **il n'est pas symétrique par
  direction comme on le pensait** (voir #1). L'erreur n'était pas "il n'existe pas", c'était "il ne fait
  pas ce qu'on croyait".
- **Cible de probabilité = 50 = "probabilité de SL"**, pas "probabilité de TP" : `sl_probability =
  tp_size/(tp_size+sl_size)` est, par la formule classique de gambler's ruin à barrières symétriques, la
  probabilité de toucher la barrière SL en premier (pas TP). Cohérence interne vérifiée avec le nom de
  variable MQL5 — pas un bug, juste une clarification de lecture.

## Ce qui reste ouvert (pas de conclusion ferme)

1. **Les 4 paires manquantes** — reciblé par la finding #1 : AUDCAD et GBPNZD sont maintenant les deux
   candidates prioritaires (pas de jambe EUR négative), EURAUD/EURCHF probablement peu utiles. Non testé
   (pas de données, hors mission principale confirmée par l'utilisateur).
2. **Provenance des données M1** — `data/deep_history_utc` n'est pas le flux Eightcap réel ; les
   High/Low hebdomadaires qui pilotent `GetTradeInfo` pourraient différer assez du flux Eightcap pour
   changer quel combo (S1/S2/R1/R2) gagne l'argmin sur une fraction non-triviale de barres. Pas
   quantifiable sans données Eightcap.
3. **Le bug MathMin (#4)** — mécaniquement dérivé et dans le bon sens, mais son ampleur littérale est
   invalidée par le compte de trades. Nécessite soit un test MetaEditor réel (voir #4), soit d'être
   recombiné avec la correction #1 (long-only) + les paires manquantes pour voir si le volume remonte à un
   niveau plausible — non fait ici par manque de temps/données.
4. **Rounding `NormalizeDouble(...,2)`** sur `sl_size`/`tp_size` (lignes 507-508 MQL5) avant le calcul de
   probabilité : non répliqué (nos calculs sont en flottant plein, pas arrondis à 2 décimales de pip).
   Effet mineur attendu (départage de quasi-égalités entre combos), non quantifié.

## Combiné #1 + #3 (fait, après rédaction du reste du rapport)

`code/run_tz_compare.py` + filtrage achat-seul appliqué à `intrabar_engine_tzfix.py`, mêmes 8 paires,
même fenêtre :

| | n | WR | R:R | total (composé) |
|---|---:|---:|---:|---:|
| TZFIX seul (achat+vente, non corrigé) | 365 | 66,85% | 0,595 | +25,89% |
| **TZFIX + long-only (#1+#3 combinés)** | **211** | **70,14%** | **0,610** | **+30,40%** |
| Cible (12 paires) | 648 | 63,58% | 0,719 | +60,33% |

Le R:R remonte un peu par rapport au TZFIX seul (0,595→0,610) mais reste net en dessous de la cible, et
le WR **dépasse maintenant la cible dans l'autre sens** (70,14% vs 63,58%) tandis que n s'effondre encore
plus (211, contre 242 en long-only-sur-baseline et 648 visé) — **EURGBP et EURUSD tombent à zéro trade
sous les DEUX corrections**, et EURJPY chute de 44 à 15. Ça confirme et durcit encore la lecture de la
finding #1 (les paires EUR-base sont structurellement mortes sous le vrai régime long-only), mais ça
montre aussi que corriger #1+#3 ensemble ne suffit toujours PAS à combler l'écart de R:R ni de volume —
il manque encore un mécanisme (le spread, #2, dans le sens qui aggrave encore l'écart nominal requis ; ou
les paires manquantes AUDCAD/GBPNZD, qui n'ont pas la jambe EUR-morte et sont donc les mieux placées pour
regonfler le volume sans diluer le WR/RR).

## Prochaine étape suggérée

Récupérer AUDCAD et GBPNZD via Dukascopy (pas EURAUD/EURCHF, probablement aussi mortes) pour tester si le
volume manquant se comble avec 2 paires ciblées plutôt que 4 à l'aveugle. Puis rouvrir la question du
bug MathMin (#4) une fois le volume à un niveau plus proche de la cible : c'est seulement à ce moment-là
que sa contribution possible à la remontée de R:R (0,610→0,719) redevient testable sans être immédiatement
rejetée par un compte de trades déjà trop bas.
