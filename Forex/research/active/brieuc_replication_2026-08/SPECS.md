# SPECS — spec Python non ambiguë par stratégie

Convention commune à toutes les stratégies :
- Données M1 vraie UTC, `data/deep_history_utc/<INSTR>_M1.csv` (colonnes
  `timestamp_utc,open,high,low,close,tick_volume,spread,real_volume`), lues **read-only** par chemin
  absolu depuis le worktree.
- Timeframes dérivés (H1/H4/D1) par resample OHLC standard sur M1, label=left, closed=left, en UTC.
- "Signal à T-1, trade à T" (version CORRIGÉE) : le signal est calculé sur la DERNIÈRE BARRE FERMÉE
  au moment T-1 ; l'ordre (marché, stop ou limite) est envoyé/actif à partir de l'ouverture de la
  barre T de la timeframe d'EXÉCUTION (M1 dans tous les cas, puisque l'exécution réelle MT5 est
  tick-based — on utilise M1 comme approximation de l'exécution continue).
- Remplissage des ordres stop/limite : premier bar M1, à partir de T, dont le range `[low,high]`
  touche le prix déclencheur. Prix de fill = `min/max(prix déclencheur, open de la barre si l'open a
  déjà franchi le niveau)` — jamais mieux que ce que l'open offre (L59, gap-through).
- Sortie SL/TP : scan M1 avancé depuis le bar de fill ; si SL et TP sont tous deux dans le range de
  la même barre M1, on prend le PIRE des deux (hypothèse conservatrice, pas d'ordre intra-barre
  connu) — flag `ambiguous_bar` compté et rapporté (fraction par strat/instrument, cf. L59 leçon
  sœur "10× moins sur données réelles que sur placebo" — même contrôle appliqué ici : on rapporte le
  taux, on ne le suppose pas nul).
- Version NAÏVE : reproduit l'écart de timing identifié dans PREREGISTRATION.md (repaint / bar de
  formation) — implémentée en évaluant le signal sur la valeur de l'indicateur À L'INSTANT M1 courant
  (barre en formation de la TF native) plutôt qu'à la dernière clôture. Le remplissage/sortie utilise
  les mêmes règles L59 que la version corrigée (le bug naïf documenté est un bug de SIGNAL, pas un
  bug de remplissage — on ne double-compte pas deux bugs différents dans la même divergence).

---

## 1. LondonBreakout

**Paramètres** : SL=20, TP=40 ("pips", table PREREGISTRATION §point-size), lot par risk 1%.

**Fenêtre Londres** :
- Corrigé : 08:00–16:30 Europe/London (heure LOCALE Londres, DST géré par zoneinfo), convertie en
  UTC bar-par-bar (08:00 Londres = 08:00 UTC en hiver GMT, 07:00 UTC en été BST).
- Naïf : 09:00–18:00 UTC fixe toute l'année (reproduit `structLondonOpen.hour=9` interprété comme
  heure serveur EET/EEST **assumée = UTC+2/+3 fixe non ajustée**, i.e. la fenêtre néglige le DST —
  approximée ici par une fenêtre UTC fixe non ajustée, ce qui est le mode de défaillance décrit : la
  fenêtre dérive d'une heure l'été par rapport à l'intention "ouverture Londres").

**Signal** (calculé une fois par jour ouvré, à l'instant d'ouverture de fenêtre) :
`asian_high = max(high) sur les 10 barres H1 précédentes`, `asian_low = min(low)` sur les mêmes 10
barres H1 (corrigé : 10 dernières H1 CLOSES avant l'ouverture Londres ; naïf : identique — ce n'est
pas la partie buguée de cet EA, seule l'heure de fenêtre l'est).

**Ordres** : BuyStop à `asian_high` (SL=`asian_high-SL`, TP=`asian_high+TP`) ET SellStop à
`asian_low` (SL=`asian_low+SL`, TP=`asian_low-TP`), posés simultanément à l'ouverture de fenêtre,
expirent (annulés s'ils n'ont pas fillé) à la clôture de fenêtre. Si l'un fille, l'autre reste actif
(le code source ne les annule pas mutuellement — reproduit tel quel, two-sided peut donner 0, 1 ou 2
trades le même jour).

**Leg** : chaque fill (long et short) est logué séparément → reporting L25 two-sided.

---

## 2. DailyBreakout

**Paramètres** : lot par risk 1%, pas de TP fixe (0 = laisser courir), trailing 1:1 breakeven+.

**Signal** : à chaque nouveau jour D1 (`iBars` change), `prevHigh/prevLow` = high/low du D1 clôturé
la veille. Corrigé : disponible à l'ouverture UTC du jour D1 courant (00:00 UTC, D1 non session-
ajusté — le code source ne fait aucun ajustement de session, reproduit tel quel dans les deux
versions). Naïf ≡ corrigé pour le signal (pas de bug de repaint identifié ici, cf. PREREGISTRATION
§7) — la seule divergence naïf/corrigé pour cette stratégie est le remplissage de sortie (L59, ci-
dessous), pas le signal.

**Garde** : ordres posés seulement si `open_du_jour < prevHigh AND open_du_jour > prevLow` (sinon
gap-through, pas d'ordre — reproduit à l'identique).

**Ordres** : BuyStop à `prevHigh` (SL=`prevLow`, pas de TP) + SellStop à `prevLow` (SL=`prevHigh`,
pas de TP), `ORDER_TIME_DAY` = expirent à la clôture du jour D1 s'ils n'ont pas fillé.

**Trailing (position ouverte)** : à chaque M1 après fill, si `close` en profit de `d` par rapport à
l'entrée, `nouveau_SL = SL_initial + d` (long) / `SL_initial - d` (short), appliqué seulement si plus
favorable que le SL courant (ne recule jamais). Sortie quand le prix M1 touche le SL courant (scan
M1 bar-par-bar, pas de saut).

**L59 appliqué ici explicitement** : à chaque bar où le trailing aurait dû exécuter un stop-loss,
le prix de remplissage réel est `pire(niveau_stop_théorique, open_de_la_barre)`. Le % de barres où
`open` a déjà franchi le niveau (stop rempli pire que le théorique) est rapporté par instrument.

---

## 3. BollingerBands

**Paramètres** : BB(20,2σ) H4 close, MA200 H4 SMA close, SL=200/TP=200 "pips" (table point-size),
`RISK_IN_PCT` → ici forcé à 1% (convention commune, cf. PREREGISTRATION §sizing) au lieu de la valeur
source 0.5% (le code source a `RISK_IN_PCT=0.5` mais la formule `riskInCurrency = balance*0.5/100`
= 0.5% déjà — non modifié en pourcentage, seulement rendu comparable via le sizing commun 1% à toutes
les stratégies ; noté ici pour transparence, sans impact sur le Sharpe en R-multiples).

**Signal** (une fois par barre H4 fermée) :
- `close[1] (H4 fermée T-1) > bbUpper AND price < MA200` (corrigé : bbUpper/MA200 de la MÊME barre
  T-1 ; naïf : bbUpper/MA200 de la barre EN FORMATION au moment T-1, i.e. calculée avec un high/low
  encore incomplet — approximé par la valeur de l'indicateur à l'instant M1 correspondant, avant la
  clôture de la barre H4) ⇒ **SELL** (fade, sens de tendance baissière).
- `close[1] < bbLower AND price > MA200` ⇒ **BUY** (fade, sens de tendance haussière).
- Une seule position à la fois (`isTradeOpen`, remis à zéro quand la position ferme — reproduit).

**Exécution** : ordre marché à l'ouverture de la barre H4 T (corrigé) / dès que la condition devient
vraie intra-barre en formation (naïf, approximé par exécution au premier M1 où la condition tient).
SL/TP fixes en prix (pas de trailing).

---

## 4. FVG

**Paramètres** : SL=5, TP=40 "pips" (table point-size FX/métal ; non testé sur indices, cf. scope),
timeframe M1.

**Signal** (calculé à chaque minute M1) : sur 3 bougies consécutives `[i, i-1, i-2]` (indices MQL5
natifs 0,1,2 = naïf ; décalés 1,2,3 = corrigé) :
- `low[i] > high[i-2]` ⇒ FVG haussier, `middle = low[i-1] + (high[i-1]-low[i-1])/2`.
- `high[i] < low[i-2]` ⇒ FVG baissier, `middle = low[i-1] + (high[i-1]-low[i-1])/2`.
Naïf : `i=0` = bougie M1 EN FORMATION (le "gap" n'est pas encore confirmé, peut se refermer avant la
clôture). Corrigé : `i=1` = dernière bougie M1 FERMÉE au moment du calcul (donc le triplet complet
est [T-1,T-2,T-3], toutes fermées, disponible pour ordre à T).

**Ordre** : BuyLimit (haussier) / SellLimit (baissier) à `middle`, SL=`middle∓SL`, TP=`middle±TP`,
expire à la fin du jour UTC s'il n'a pas fillé (`ORDER_TIME_DAY`). Une fois fillé, la position n'a
pas d'expiration (portée jusqu'à SL/TP). `isFvgActivated` bloque les nouveaux ordres tant qu'un
ordre/position FVG est actif — reproduit (une position FVG à la fois).

---

## 5. MAcroisement

**Paramètres** : SL=20/TP=40 "pips" (table point-size), timeframe de base = **H1** (résolution de
`PERIOD_CURRENT`, cf. PREREGISTRATION), EMA21/EMA55 close.

**Signal** :
- `ema21[T] < ema55[T] AND ema21[T-1] > ema55[T-1]` ⇒ **BUY** (reproduit tel quel — c'est un
  croisement BAISSIER qui déclenche un achat dans le code source, cf. bug #8 PREREGISTRATION).
- `ema21[T] > ema55[T] AND ema21[T-1] < ema55[T-1]` ⇒ **SELL** (croisement HAUSSIER déclenche une
  vente).
- Naïf : `[T,T-1]` = `[barre H1 en formation à l'instant M1 courant, dernière H1 fermée]` — le
  signal peut apparaître et disparaître plusieurs fois avant la clôture H1 réelle (papillotement).
  Corrigé : `[T,T-1]` = deux dernières barres H1 FERMÉES, signal figé une fois par heure, trade à
  l'ouverture de l'heure suivante.
- Une position à la fois (`tradeEnCours`), remise à zéro quand flat.
- **Variant diagnostic (non-canonique, étiqueté à part, ne consomme pas de budget de recherche
  séparé)** : sens inversé (BUY sur croisement haussier, SELL sur croisement baissier) = ce qu'un
  praticien attendrait d'un "croisement EMA". Rapporté côte à côte dans resultats.csv avec
  `variant=sens_inverse`, exclu du n_tests principal (miroir de signe du même signal, pas une
  nouvelle hypothèse indépendante).

---

## Addendum d'implémentation — comment le bug "barre en formation" est simulé sans données tick

MT5 réévalue les indicateurs à CHAQUE tick sur la barre en formation ; nos données sont M1 (pas
tick), donc "reproduire le repaint" exige une approximation explicite, choisie et documentée AVANT
tout calcul de performance (pas ajustée après coup) :

- **BollingerBands / MAcroisement (naïf)** : la valeur "en formation" d'une MA/EMA/bande à l'instant
  M1 `t` à l'intérieur d'une période H4/H1 encore ouverte est calculée analytiquement en substituant
  le close M1 courant au close (encore inconnu) de la période : `forming_mean(t) = (S_{n-1} +
  close_M1(t]) / n` (idem somme des carrés pour l'écart-type, idem SMA200). C'est exactement ce que
  fait un indicateur MT5 continu — il n'y a pas d'approximation de perdue ici, seulement la limite de
  résolution (M1 au lieu du tick) sur QUAND, à l'intérieur de la minute, la condition a pu être vraie
  la première fois.
- **FVG (naïf)** : la bougie M1 "en formation" (index 0 du code source) est approximée par son
  OPEN SEUL (`low=high=open` du tick le plus précoce possible de cette minute) — c'est la version LA
  PLUS PRÉMATURÉE possible du bug (borne haute du repaint, pas une estimation moyenne). Documenté
  explicitement : ce choix majore probablement l'écart naïf/corrigé plutôt que de le sous-estimer,
  ce qui va dans le sens conservateur pour la conclusion "le naïf était optimiste".
- Dans les deux cas, l'ordre déclenché par le signal naïf est actif au moment exact où la condition
  intra-minute devient vraie (pas de délai artificiel ajouté) — c'est la version CORRIGÉE qui retarde
  l'ordre à l'ouverture de la barre suivante (T-1→T), pas la version naïve, qui reproduit fidèlement
  l'absence de ce délai dans le code source.

## n_tests (recompté après amendement du 2026-08-28, univers 6→11 instruments)

- Combinaisons principales : {LondonBreakout, BollingerBands, MAcroisement} × 11 instruments ×
  2 versions (naïf/corrigé) = 3 × 11 × 2 = **66**
- DailyBreakout : naïf ≡ corrigé pour le signal (spec §2, seul le remplissage de sortie diverge,
  mesuré en statistique descriptive L59 pas en 2e hypothèse) : 11 instruments × 1 version = **11**
- FVG : restreint à 4 instruments (EURUSD/GBPUSD/USDJPY/XAUUSD, non étendu — §PREREGISTRATION
  Instruments) × 2 versions = **8**
- **n_tests_principal = 66 + 11 + 8 = 85**
- Le variant diagnostic "MAcroisement sens_inverse" est ABANDONNÉ (2026-08-28) — c'était une
  reproduction d'une lecture erronée de l'indexation `CopyBuffer`, pas une hypothèse indépendante
  (voir journal de bugs #8 corrigé). Aucun test additionnel consommé pour ce point.
- **Δn_tests ce sprint = 85**, n_tests_global rapporté = 1904 (baseline brief) + 85 = **1989**.
