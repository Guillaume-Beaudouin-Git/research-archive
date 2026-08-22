# Rapport stratégie 1/109 — Toby Crabel : 2-Bar Narrow Range + Opening Range Breakout

**Projet :** filtrage systématique des 109 revues de stratégies d'oxfordstrat.com sur l'univers FTMO.
**But de ce rapport :** permettre à l'équipe de **reproduire**, **auditer** et **contredire** le test de la stratégie 1, indépendamment.
**Statut :** ❌ **DISCARD** sous pipeline **v2-gates** (4/4 gates constitutionnels FAIL, cf. §8). *Le verdict v1 « KEEP borderline » a été downgradé suite à l'audit `AUDIT_S001_crabel.md`.*
**Auteur :** pipeline Cowork / Claude · **Date :** 2026-06-04 · **Version moteur :** `ftmo_lab v2-gates` — **mesures de base inchangées vs v1** ; seul le verdict change via les gates.

---

## 0. Résumé exécutif

| Élément | Valeur |
|---|---|
| Stratégie | Crabel 2-Bar NR + ORB (long/short, 1 position à la fois) |
| Source | https://oxfordstrat.com/trading-strategies/toby-crabel-narrow-range-1/ (rating site : **C**) |
| Univers testé | 30 / 40 instruments FTMO (indices, FX, commodities, BTC/ETH) |
| Période | 2000–2026 (indices), 2018/2021–2026 (FX, BTC, XAU), 2005–2026 (commodities) |
| Coûts | spread réel (M1) + commission (specs FTMO) + slippage, plancher conservateur par classe (méd. **2,9 bps** round-turn) |
| Point de référence (Target=3R, Time=10j) | **expectancy +0,0068 R/trade · Profit Factor 1,05 · win 45,1 % · 3 841 trades** |
| Equity poolée (réf.) | Sharpe **0,22** · CAGR **+0,4 %** · MaxDD **−16,1 %** |
| Robustesse | **100 % des 42 cellules** de la grille de paramètres ont une expectancy nette positive |
| Meilleure cellule | Target=6R / Time=40j → **+0,0387 R**, PF 1,16 |
| Concentration de l'edge | indices + quelques commodities ; **FX et crypto faibles/négatifs** |
| **Gates constitutionnels** | **0/4 PASS** (délai+1 FAIL, two-sided FAIL, DSR FAIL, OOS FAIL — §8) |
| **VERDICT (v2-gates)** | ❌ **DISCARD** — edge positif après coûts mais 4/4 gates FAIL |

**Lecture :** la *mesure* brute est positive (+0,0068 R, PF 1,05, grille 100 % positive) et **reproductible à l'identique**. Mais sous les **gates constitutionnels** (§8), cet edge est un **mirage** : il **s'inverse en fill réaliste** (artefact d'exécution intrabar, Sharpe +0,22→−0,74), provient quasi **exclusivement des longs** sur des indices qui ont monté (**beta déguisé**, contrib 342 %), est **indistinguable du bruit** après correction de multiplicité (DSR z<0), et **meurt hors échantillon** (flip de signe en 2016+). Conclusion : la barre « tout edge positif après coûts » est **nécessaire mais pas suffisante**.

> ⚠️ Les hypothèses intrabar de la *mesure* (§5.4) sont conservatrices ; ce qui tue la stratégie n'est **pas** la mesure mais les **gates** (§8) : exécution réaliste, symétrie long/short, multiplicité, OOS.

---

## 1. Spécification originale (reproduite fidèlement)

D'après la fiche oxfordstrat (développeur : Toby Crabel, *Day Trading with Short Term Price Patterns and Opening Range Breakout*, 1990). Concept : **expansion de volatilité** après contraction.

- **Setup — 2-Bar Narrow Range (NR) :** la fourchette high–low sur 2 jours consécutifs est la **plus étroite** comparée à toute fenêtre de 2 jours dans les **20 derniers jours** (`Look_Back = 20`, `NR_Size = 2`).
- **Entrée — Opening Range Breakout (ORB) :** le jour suivant, ordres stop de part et d'autre de l'ouverture.
  - `Noise[i] = min(High[i] − Open[i], Open[i] − Low[i])`
  - `Average_Noise = SMA(Noise, Stretch_Length)`, `Stretch_Length = 10`
  - `Stretch = Average_Noise × Stretch_Multiple`, `Stretch_Multiple = 2`
  - Long : buy stop à `Open + Stretch`. Short : sell stop à `Open − Stretch`. Le **premier** stop touché ouvre la position ; l'autre devient le stop de protection. Si **les deux** sont touchés le même jour → **comptés comme une perte** (pas de reversal).
- **Sorties (testées par le site) :**
  - **Target Exit :** `$Target = Target_Index × risque initial` (le risque initial est défini par le stop ATR).
  - **Time Exit :** clôture du n-ième jour, `n = Time_Index`.
  - **Stop Loss :** `ATR(ATR_Length) × ATR_Stop`, `ATR_Length = 20`, `ATR_Stop = 6`.
- **Sizing / données du site :** capital $1 M, fixed-fractional 1 %, 42 futures US, 1980–2013, plateforme MATLAB.

**Écarts assumés par rapport au site (et pourquoi) :**

| Site | Ici | Raison |
|---|---|---|
| 42 futures US, 1980–2013 | 30 instruments FTMO multi-classes, 2000–2026 | univers cible de l'utilisateur (FTMO) ; pas d'accès aux futures US continus |
| Résultats en images (PF/Sharpe/…) | métriques recalculées | la fiche ne publie aucun chiffre exploitable |
| Fixed-fractional 1 % | risque normalisé 0,5 %/trade en R-multiples | comparabilité inter-instruments et agrégation poolée |
| Coûts $0 et $50/round-turn | modèle de coûts FTMO bps (cf. §4) | réalisme FTMO |

---

## 2. Univers et données

30/40 instruments disposent d'un **vrai OHLC journalier** (les seules entrées exploitables pour un pattern NR/ORB). Détail dans `ohlc/_coverage.csv`.

| Classe | Couverts | Source OHLC | Période | Manquants |
|---|---|---|---|---|
| Indices | 10/10 | `panels/ftmo_*.csv` (panels FTMO) | 2000–2026 | — |
| Forex | 9/10 | resample M1 → daily (`panels/m5_indices/*_M1.csv`) | 2018 ou 2021–2026 | GBPJPY |
| Commodities | 9/10 | yfinance futures (`raw/yf_*=F_1d*.parquet`) + XAU (M1) | 2005–2026 (XAU 2018+) | USOIL (cache CL=F tronqué à 250 j) |
| Crypto | 2/10 | BTC (M1), ETH (yfinance) | 2017/2018–2026 | LTC, XRP, XMR, NEO, ADA, DASH, DOT, DOGE (close-only) |

**Conventions et points de vigilance données :**

1. **Frontière de bougie journalière (marchés 24 h).** Pour FX/crypto/XAU reconstruits depuis le M1, la bougie « jour » est découpée sur la **date calendaire UTC (00:00)**. FTMO utilise généralement l'heure serveur (EET). Déplacer la coupure change l'`Open` utilisé par l'entrée ORB → **paramètre à auditer** (cf. §9, A3).
2. **Futures yfinance = contrats continus** (back-adjusted) : utilisables pour des stats de pattern, mais les niveaux de prix absolus ne sont pas ceux du CFD FTMO. L'effet sur une stratégie en R-multiples (différences de prix normalisées) est faible mais non nul.
3. **Historique FX court** (certaines paires 2021+ → ~900 jours) : nombre de trades modeste sur ces paires (cf. tableau §7.2).
4. **Filtrage qualité :** lignes avec NaN ou prix ≤ 0 supprimées (`_clean()`).

Régénération : `python code/build_ohlc_store.py` (idempotent — couverture vérifiée identique à la reconstruction).

---

## 3. Pré-traitement des signaux (sans look-ahead)

- `rng2[i] = max(High[i],High[i-1]) − min(Low[i],Low[i-1])` (fourchette 2 jours).
- `prev_min[i] = min(rng2[i-Look_Back … i-1])` via `rolling(20).min().shift(1)` → **n'inclut jamais la barre courante**.
- `setup[i] = (rng2[i] ≤ prev_min[i])`.
- `Stretch[i]` calculé avec l'information **jusqu'à la barre i incluse**.
- **Entrée à la barre i+1** : le moteur consomme `setup[i-1]` et `Stretch[i-1]` pour entrer à `Open[i]`. Aucune information future n'est utilisée pour décider/dimensionner une entrée. (Test d'audit dédié en §9, A1.)

---

## 4. Modèle de coûts FTMO

Coût facturé **par round-turn**, en **bps de notionnel**, déduit en R sur chaque trade :

```
cost_round_turn_bps = max( spread_bps + commission_rt_bps + slippage_bps , plancher_classe )
```

- **spread_bps** : pour FX/BTC/XAU, médiane de la colonne `spread` réelle des M1 (en points broker) convertie en bps :
  `spread_bps = median(spread_points) × 10^(−digits) / median(close) × 1e4`.
  Pour les instruments yfinance (pas de spread tick), `spread_bps = 0` et le **plancher de classe** s'applique.
- **commission_rt_bps** (specs FTMO, `ftmo_specs_full.csv`) : FX 0,5 ; indices 0 ; commodities 0,3 ; crypto 2,0.
- **slippage_bps = 2,0** (round-turn) — hypothèse conservatrice pour une entrée sur stop en données daily.
- **Planchers de classe (bps round-turn) :** FX 1,5 · indices 2,0 · commodities 4,0 · crypto 8,0.

**Conversion en R :** `cost_R = (cost_bps / 1e4) × Close_entrée / risque_initial`. Conséquence voulue : un stop serré (R petit) est **davantage pénalisé** par les coûts — réaliste.

Coûts effectifs sur l'univers : **min 2,0 · médiane 2,9 · max 8,0 bps** round-turn.

> Choix délibéré : on **ne flatte pas** la stratégie avec les spreads bruts ultra-serrés. Le plancher + slippage rendent le test « après coûts » honnête.

---

## 5. Moteur de backtest et hypothèses

Moteur event-driven `simulate_bracket()` pour la famille « entrée sur stop + sortie bracket » (couvre ORB, breakouts, gaps, NR…).

### 5.1 Normalisation du risque
Chaque trade risque une fraction fixe du capital (`RISK_FRAC = 0,5 %`) à la distance de stop initiale. Les PnL sont exprimés en **R-multiples** (multiples du risque initial), donc directement **agrégeables** entre instruments hétérogènes.

### 5.2 Logique d'entrée (barre i)
- `buy = Open[i] + Stretch[i-1]`, `sell = Open[i] − Stretch[i-1]`.
- `long_hit = High[i] ≥ buy` ; `short_hit = Low[i] ≤ sell`.
- Remplissage : long à `max(Open[i], buy)`, short à `min(Open[i], sell)` (gère le gap d'ouverture au-delà du stop).
- `risque_initial = ATR(20)[i] × 6`.

### 5.3 Logique de sortie (barres i → i+Time_Index)
- Long : stop si `Low ≤ stop` ; sinon target si `High ≥ target`.
- Short : symétrique.
- Time exit : clôture à `i + Time_Index` si ni stop ni target touchés.
- Fin de données : clôture sur la dernière barre disponible.

### 5.4 Hypothèses intrabar (⚠️ critiques pour l'audit — toutes conservatrices)
1. **Stop avant target** quand les deux sont dans la fourchette du même jour → **pénalise** la stratégie (worst-case intrabar).
2. **Double-touche à l'entrée** (`long_hit` et `short_hit` le même jour) → trade comptabilisé **perdant** de `−2 × Stretch / R` (conforme à la spec « assume the trade was a loser »).
3. **Pas de positions superposées** : une seule position à la fois ; la recherche de setup reprend après la sortie. Réduit le nombre de trades mais évite le double-comptage.
4. Remplissage au **niveau du stop** (pas de prix meilleur intra-bar), sauf gap d'ouverture.

### 5.5 Métriques (`trade_metrics`)
`trades, win%, expectancy (R/trade), profit factor, Sharpe annualisé (depuis les R par trade), CAGR, MaxDD` sur une equity composée en `RISK_FRAC × netR` à la date de sortie.

---

## 6. Paramètres

| Paramètre | Valeur(s) | Rôle |
|---|---|---|
| `LOOK_BACK` | 20 | fenêtre du pattern NR |
| `STRETCH_LEN` | 10 | SMA du Noise |
| `STRETCH_MULT` | 2,0 | multiplicateur du Stretch (ORB) |
| `ATR_LEN` | 20 | ATR du stop |
| `ATR_STOP` | 6,0 | multiple ATR = risque initial |
| `RISK_FRAC` | 0,005 | risque/trade (equity) |
| **Point de référence** | Target=3R, Time=10j | défauts proches du site |
| **Balayage** | Target ∈ {1,2,3,4,6,8,10} R × Time ∈ {1,3,5,10,20,40} j | sensibilité (42 cellules) |

---

## 7. Résultats

### 7.1 Point de référence (Target = 3R, Time = 10 j)
- **Trades : 3 841 · Win : 45,1 % · Expectancy : +0,0068 R/trade · Profit Factor : 1,050**
- Equity poolée : **Sharpe 0,22 · CAGR +0,4 % · MaxDD −16,1 %**
- **16/30 instruments** à expectancy nette positive.

### 7.2 Par instrument (extraits — table complète : `results/s001_per_instrument.csv`)

**Top 8 (expectancy nette, R/trade) :**

| Instrument | Classe | Trades | Win | exp R | PF |
|---|---|---|---|---|---|
| XPDUSD | commodities | 25 | 0,600 | 0,150 | 2,12 |
| AUS200 | indices | 235 | 0,460 | 0,080 | 1,87 |
| COCOA | commodities | 118 | 0,508 | 0,048 | 1,35 |
| USDCHF | forex | 31 | 0,516 | 0,033 | 1,24 |
| US500 | indices | 226 | 0,491 | 0,032 | 1,29 |
| US2000 | indices | 240 | 0,471 | 0,030 | 1,23 |
| EU50 | indices | 163 | 0,448 | 0,025 | 1,19 |
| US100 | indices | 214 | 0,491 | 0,020 | 1,16 |

**Bottom 5 :**

| Instrument | Classe | Trades | Win | exp R | PF |
|---|---|---|---|---|---|
| BTCUSD | crypto | 94 | 0,415 | −0,045 | 0,73 |
| XAUUSD | commodities | 71 | 0,380 | −0,054 | 0,68 |
| USDCAD | forex | 61 | 0,443 | −0,056 | 0,66 |
| EURGBP | forex | 25 | 0,440 | −0,060 | 0,57 |
| EURUSD | forex | 63 | 0,413 | −0,081 | 0,54 |

> Lecture : l'edge est porté par les **indices** (large échantillon) et quelques **commodities** ; les paires **FX** (petits échantillons, mean-reverting) et **BTC/XAU** sont défavorables — l'ORB de breakout y est contre-productif.

### 7.3 Sensibilité — expectancy nette poolée (R/trade)

| Target \ Time | 1j | 3j | 5j | 10j | 20j | 40j |
|---|---|---|---|---|---|---|
| 1R | 0,0123 | 0,0081 | 0,0056 | 0,0060 | 0,0028 | 0,0310 |
| 2R | 0,0122 | 0,0083 | 0,0066 | 0,0066 | 0,0033 | 0,0338 |
| 3R | 0,0122 | 0,0083 | 0,0067 | 0,0068 | 0,0055 | 0,0339 |
| 4R | 0,0122 | 0,0083 | 0,0067 | 0,0063 | 0,0061 | 0,0361 |
| 6R | 0,0122 | 0,0083 | 0,0067 | 0,0063 | 0,0070 | **0,0387** |
| 8R | 0,0122 | 0,0083 | 0,0067 | 0,0063 | 0,0069 | 0,0376 |
| 10R | 0,0122 | 0,0083 | 0,0067 | 0,0063 | 0,0069 | 0,0368 |

- **100 % des cellules positives** → robustesse aux paramètres (signal de non-overfit).
- **Meilleure cellule :** Target=6R, Time=40j → **+0,0387 R**, PF 1,16.
- Gradient net : la sortie **40 j** domine → l'edge vient de **laisser courir** (composante trend), pas de la prise de profit rapide.
- Heatmap : `results/s001_sensitivity.png`.

---

## 8. GATES CONSTITUTIONNELS (v2) — OBLIGATOIRE

Exécutés dans le test principal : `res = ftmo_lab.run_gates(make_run(3R,10j), sharpe_grid, split='2015-12-31')`.
Résultats bruts : `results/s001_gates.csv`. **KEEP impossible sans 4/4 PASS.**

| # | Gate (loi) | Résultat S001 | Verdict |
|---|---|---|---|
| 1 | **Délai+1 / fill réaliste (L26)** | optimiste Sharpe **+0,22** (expR +0,0068) → réaliste `next_open` Sharpe **−0,74** (expR −0,0223) ; win 45,1 %→41 % | ❌ **FAIL** — artefact de fill intrabar |
| 2 | **Two-sided (L25)** | long expR **+0,0528** (n=1689, Sh ≈+1,05) / short expR **−0,0096** (n=1588, Sh ≈−0,18) ; contrib longs **342 %** | ❌ **FAIL** — beta déguisé (long-dominé) |
| 3 | **DSR (N=42 cellules)** | SR sélectionné **1,247** < E[max bruit] **2,157** ; DSR_z **−37,5** (prob ≈ 0) | ❌ **FAIL** — grille = bruit (multiplicité) |
| 4 | **OOS (≤2015 / ≥2016, L31)** | train expR **+0,0206** (Sh +0,58, n=1822) → test expR **−0,0056** (Sh −0,21, n=2019) | ❌ **FAIL** — flip de signe / décayé |

**Gates FAIL : 4/4.**

### 8.1 Lecture
- **Gate 1 (le plus décisif).** L'edge n'existe que parce que l'entrée est supposée se faire *au niveau du stop* sur la barre de breakout. Le high qui touche le buy-stop est par construction au-dessus de ce stop ; le close (ou l'open suivant) n'a aucune raison de l'être. Avec un fill réaliste, **le signe s'inverse** → ce n'est pas un edge tradable, c'est un artefact d'exécution.
- **Gate 2.** 342 % du PnL net vient des longs ; les shorts perdent. Un breakout symétrique devrait fonctionner des deux côtés. Ici c'est un **filtre de long-trend sur des indices haussiers** (à re-tester contre un buy-and-hold timé, Sharpe ≈ 0,4-0,6 — les longs Crabel l'améliorent, donc *timing sur beta*, pas edge intrinsèque).
- **Gate 3.** Sous H₀ « 42 tirages de bruit », on attendrait un Sharpe max ≈ 2,16 ; on observe 1,25 (cellule sélectionnée). Le « 100 % positif » et le « best cell » sont **en-dessous du bruit attendu**. *(Écart vs audit : l'audit déflatait le Sharpe poolé 0,216 → z −122,9 ; on déflate ici le Sharpe sélectionné 1,247 → z −37,5. Même verdict : SR_obs < E[max] ⇒ FAIL. Caveat : essais corrélés ⇒ DSR conservateur, ne sauve pas le verdict.)*
- **Gate 4.** Edge entièrement porté par 2000-2015 ; **flip de signe** sur 2016-2026 (vol plus basse, continuation post-impulse, compression HFT de l'ORB). **Non déployable** sur le régime actuel.

### 8.2 Verdict final (règle stricte v2)
`KEEP` ⇔ edge_net>0 **ET** 4/4 gates. Ici : edge_net>0 mais **0/4 gates** → **❌ DISCARD**.
Tags : *artefact de fill intrabar · beta déguisé · grille = bruit · régime-dépendant/décayé.*

> **Downgrade explicite : v1 « KEEP borderline » → v2 « DISCARD ».** Le rapport reste valide comme **mesure** (chiffres reproductibles) ; c'est le **verdict** qui change, conformément à l'audit `AUDIT_S001_crabel.md`.

### 8.3 Pourquoi ce n'est pas récupérable simplement
Restreindre aux longs indices reviendrait à assumer un **long-only beta timing** (ce que Gate 2 dénonce) qui **meurt OOS** (Gate 4) — donc même la version « horizon long sur indices » échoue aux gates. La stratégie est **archivée DISCARD**.

---

## 9. Limites connues & checklist d'audit prioritaire

**Où des erreurs/biais pourraient se cacher — à vérifier en priorité :**

- **A1 — Look-ahead.** Confirmer que `setup`/`Stretch` n'utilisent que l'info ≤ barre de décision et que l'entrée est bien en i+1. *Test :* décaler artificiellement `Stretch` d'un jour et vérifier que la perf se dégrade de façon cohérente.
- **A2 — Hypothèse stop-avant-target.** Impact potentiellement important sur les jours à grande amplitude. *Test :* inverser l'hypothèse (target d'abord) → borne supérieure de l'edge. L'écart mesure la sensibilité intrabar.
- **A3 — Frontière de bougie (UTC vs EET).** Rebuild du store avec coupure 22:00/00:00 EET et re-run → mesurer l'écart sur l'edge FX/crypto.
- **A4 — Continuité des futures yfinance.** Vérifier l'absence de sauts d'ajustement parasites dans XAG/XPT/XPD/UKOIL/WHEAT/SOYBEAN/COFFEE/COCOA.
- **A5 — Petits échantillons.** USDCHF (31), XPDUSD (25), EURGBP (25) : expectancy peu significative. *Test :* intervalle de confiance / bootstrap sur l'expectancy.
- **A6 — Coûts.** Re-run avec ×1,5 et ×2 sur les coûts → l'edge survit-il ? (stress test obligatoire vu sa faiblesse).
- **A7 — Couverture.** 10 instruments absents (8 cryptos, GBPJPY, USOIL). Compléter via yfinance (`ADA-USD`, etc.) puis re-run pour confirmer la généralité.
- **A8 — Définition du NR (`≤` vs `<`).** On utilise `≤ prev_min` (inclusif). Tester `<` strict.
- **A9 — Sharpe poolé.** Calculé depuis les R par trade (jours sans trade = 0 implicites). Métrique conservatrice ; ne pas comparer 1:1 à un Sharpe daily classique.

**Limites structurelles :** approximation **daily d'une stratégie intraday** (l'ORB et les sorties target/stop sont par nature intra-journaliers) ; historique FX/crypto court ; un seul jeu d'hypothèses de coûts.

---

## 10. Reproduction

**Environnement de référence :** Python 3.10.12 (Linux) · numpy 2.2.6 · pandas 2.3.3 · matplotlib 3.10.8 · pyarrow 24.0.0.

```bash
pip install numpy pandas matplotlib pyarrow

# 1) (optionnel) régénérer le store OHLC depuis les sources brutes
export ALGO_DATA_DIR="/Users/<vous>/Desktop/Algo_claude/data"   # dossier des sources
export OHLC_OUT_DIR="$(pwd)/ohlc"
python code/build_ohlc_store.py          # -> ohlc/*.parquet + ohlc/_coverage.csv

# 2) lancer le test de la stratégie 1 (lit ohlc/ à côté de ftmo_lab.py)
cd code && python strat_s001_crabel_nr_orb.py
```

**Sorties attendues :** console (point de référence + grille + verdict), `s001_sensitivity.png`, `s001_per_instrument.csv`, `s001_sensitivity_expectancy.csv`.

**Arborescence du livrable :**
```
oxfordstrat_109/
├── REPORT_S001_crabel_nr_orb.md   (ce fichier)
├── code/
│   ├── ftmo_lab.py                (moteur + coûts + métriques)
│   ├── build_ohlc_store.py        (reconstruction des données)
│   └── strat_s001_crabel_nr_orb.py(signaux + run + sensibilité)
├── ohlc/                          (30 parquets + _coverage.csv)
└── results/                       (heatmap + CSV)
```

> Note d'exécution : lancé depuis `code/`, `ftmo_lab` résout automatiquement le store (`../ohlc`), ou via la variable `OHLC_DIR`. Les sorties (`.png`/`.csv`) sont écrites dans le répertoire courant. Résultat vérifié reproductible à l'identique depuis `code/`.

> **Listings en annexe :** versions lisibles, fonctionnellement identiques aux fichiers `code/*.py` livrés (commentaires/affichages allégés). La **source faisant foi** est `code/*.py` (pipeline **v2-gates**). En v2, `simulate_bracket` a gagné un paramètre `fill=` (`'stop'`|`'close'`|`'next_open'`) et un champ `dir` par trade ; les **4 gates** (`gate_delay1/twosided/dsr/oos` + `run_gates`) sont listés en fin d'Annexe A et détaillés dans `PIPELINE_v2_gates.md` §2.

---

## Annexe A — `code/ftmo_lab.py`

```python
"""
ftmo_lab.py — Reusable backtest engine + FTMO cost model + metrics.
Used to filter the 109 oxfordstrat strategies across the FTMO universe.
"""
from __future__ import annotations
import numpy as np, pandas as pd, glob, os

def _find_ohlc_dir():
    """Resolve the OHLC store: $OHLC_DIR, else first existing of ./ohlc,
    ../ohlc (when this file lives in code/), or cwd/ohlc."""
    if os.environ.get("OHLC_DIR"):
        return os.environ["OHLC_DIR"]
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "ohlc"),
                 os.path.join(here, "..", "ohlc"),
                 os.path.join(os.getcwd(), "ohlc")):
        if os.path.isdir(cand):
            return os.path.abspath(cand)
    return os.path.join(here, "ohlc")

OHLC_DIR = _find_ohlc_dir()

CLASS = {  # instrument -> asset class
 **{t:'indices' for t in "US500 US100 US30 US2000 GER40 UK100 EU50 AUS200 JP225 HK50".split()},
 **{t:'forex'   for t in "EURUSD GBPUSD USDJPY USDCHF USDCAD AUDUSD NZDUSD EURGBP AUDJPY GBPJPY".split()},
 **{t:'crypto'  for t in "BTCUSD ETHUSD LTCUSD XRPUSD XMRUSD NEOUSD ADAUSD DASHUSD DOTUSD DOGEUSD".split()},
 **{t:'commodities' for t in "XAUUSD XAGUSD XPTUSD XPDUSD USOIL UKOIL WHEAT SOYBEAN COFFEE COCOA".split()},
}

# Conservative round-turn cost FLOORS (bps of notional) per class, FTMO-style.
COST_FLOOR_BPS = {'forex':1.5, 'indices':2.0, 'commodities':4.0, 'crypto':8.0}
# Commission per ROUND TURN (bps of notional), from ftmo_specs.
COMMISSION_RT_BPS = {'forex':0.5, 'indices':0.0, 'commodities':0.3, 'crypto':2.0}
SLIPPAGE_BPS = 2.0       # conservative daily stop-entry slippage, round turn
RISK_FRAC    = 0.005     # 0.5% equity risked per trade (fixed-fractional)

# ---------------------------------------------------------------- data
def load_universe(instruments=None):
    out = {}
    for f in sorted(glob.glob(os.path.join(OHLC_DIR, "*.parquet"))):
        t = os.path.basename(f)[:-8]
        if instruments and t not in instruments:
            continue
        df = pd.read_parquet(f)
        df.index = pd.to_datetime(df.index)
        out[t] = df.sort_index()
    return out

def round_turn_cost_bps(instr, df):
    """Round-turn cost in bps: measured spread (if present) + commission + slippage,
    floored at a conservative per-class level."""
    cls = CLASS.get(instr, 'indices')
    spread_bps = 0.0
    if 'spread' in df.columns:
        digits = _infer_digits(instr)
        pt = 10.0 ** (-digits)
        spread_bps = float((df['spread'].median() * pt / df['close'].median()) * 1e4)
    base = spread_bps + COMMISSION_RT_BPS.get(cls, 1.0) + SLIPPAGE_BPS
    return max(base, COST_FLOOR_BPS.get(cls, 3.0))

def _infer_digits(instr):
    return {'USDJPY':3,'AUDJPY':3,'GBPJPY':3}.get(instr, 5) if CLASS.get(instr)=='forex' else 2

# ---------------------------------------------------------------- indicators
def atr(df, n=20):
    h,l,c = df['high'], df['low'], df['close']
    pc = c.shift(1)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()

# ---------------------------------------------------------------- bracket simulator
def simulate_bracket(df, setup, stretch, *, target_index, time_index,
                     atr_len=20, atr_stop=6.0, cost_bps=2.0, allow_short=True):
    """Event-driven sim for ORB / breakout-type strategies.
    `setup[i]` True  -> NR/pattern formed using info up to & incl. bar i.
    `stretch[i]`     -> ORB offset to use for entry on bar i+1.
    Returns a DataFrame of trades with net R-multiples (costs included)."""
    o,h,l,c = (df[x].values for x in ('open','high','low','close'))
    A = atr(df, atr_len).values
    su = setup.values.astype(bool); st = stretch.values
    n = len(df); idx = df.index
    trades = []
    i = 1
    while i < n - 1:
        if not (su[i-1] and np.isfinite(st[i-1]) and st[i-1] > 0 and np.isfinite(A[i])):
            i += 1; continue
        e = i                                    # entry bar (day after setup)
        buy, sell = o[e] + st[i-1], o[e] - st[i-1]
        long_hit  = h[e] >= buy
        short_hit = (l[e] <= sell) and allow_short
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps/1e4) * c[e] / risk0    # round-turn cost in R units

        if long_hit and short_hit:                # both sides -> assume loser (spec)
            trades.append(_trade(idx[e], idx[e], 'both', -2*st[i-1]/risk0 - cost_R, 0))
            i = e + 1; continue
        if not (long_hit or short_hit):
            i += 1; continue

        if long_hit:
            entry = max(o[e], buy); d = 1; stop = entry - risk0; tgt = entry + target_index*risk0
        else:
            entry = min(o[e], sell); d = -1; stop = entry + risk0; tgt = entry - target_index*risk0

        exit_p, exit_j, reason = None, None, None
        for j in range(e, min(e + time_index, n-1) + 1):
            if d == 1:
                if l[j] <= stop:  exit_p, reason = stop, 'stop'; exit_j=j; break
                if h[j] >= tgt:   exit_p, reason = tgt,  'target'; exit_j=j; break
            else:
                if h[j] >= stop:  exit_p, reason = stop, 'stop'; exit_j=j; break
                if l[j] <= tgt:   exit_p, reason = tgt,  'target'; exit_j=j; break
            if j == e + time_index:               # time exit at close
                exit_p, reason = c[j], 'time'; exit_j=j; break
        if exit_p is None:                          # ran out of data
            exit_p, reason, exit_j = c[min(e+time_index, n-1)], 'eod', min(e+time_index, n-1)

        grossR = d * (exit_p - entry) / risk0
        trades.append(_trade(idx[e], idx[exit_j], reason, grossR - cost_R, exit_j - e))
        i = exit_j + 1                              # no overlapping positions
    return pd.DataFrame(trades)

def _trade(t_in, t_out, reason, netR, hold):
    return {'entry':t_in, 'exit':t_out, 'reason':reason, 'netR':netR, 'hold':hold}

# ---------------------------------------------------------------- metrics
def trade_metrics(tr, risk_frac=RISK_FRAC):
    if tr is None or len(tr) == 0:
        return dict(trades=0, win=np.nan, expR=np.nan, pf=np.nan, sharpe=np.nan,
                    cagr=np.nan, maxdd=np.nan, netR_sum=np.nan)
    r = tr['netR'].values
    wins, losses = r[r > 0], r[r < 0]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else np.inf
    eq = (1 + risk_frac * pd.Series(r, index=pd.to_datetime(tr['exit']))).cumprod()
    eq = eq.groupby(eq.index).last()
    days = max((eq.index[-1] - eq.index[0]).days, 1)
    cagr = eq.iloc[-1] ** (365.0/days) - 1
    dd = (eq / eq.cummax() - 1).min()
    tpy = len(r) / (days/365.0)
    sh = (np.mean(r)/np.std(r) * np.sqrt(tpy)) if np.std(r) > 0 else np.nan
    return dict(trades=len(r), win=float((r>0).mean()), expR=float(np.mean(r)),
                pf=float(pf), sharpe=float(sh), cagr=float(cagr), maxdd=float(dd),
                netR_sum=float(r.sum()))

# ============ v2-gates additions (constitutional gates, mandatory) ============
# simulate_bracket(...) also gained `fill=` ('stop'|'close'|'next_open') and a
# per-trade `dir` field — full body in the authoritative code/ftmo_lab.py.
from statistics import NormalDist
_NORM = NormalDist()

def gate_delay1(run, fill_realistic='next_open'):                  # GATE 1 (L26)
    opt = trade_metrics(run(fill='stop')); rea = trade_metrics(run(fill=fill_realistic))
    survives = bool(np.isfinite(rea['expR']) and rea['expR'] > 0 and rea['sharpe'] > 0)
    return {'gate':'delay1 (L26)','pass':survives,'fill':fill_realistic,
            'opt_expR':opt['expR'],'opt_sharpe':opt['sharpe'],'opt_win':opt['win'],
            'real_expR':rea['expR'],'real_sharpe':rea['sharpe'],'real_win':rea['win'],
            'tag':None if survives else 'artefact de fill intrabar'}

def gate_twosided(trades, dom_thresh=0.70):                        # GATE 2 (L25)
    r = trades['netR'].values; d = trades['dir'].values
    lr, sr = r[d == 1], r[d == -1]; sl, ss = float(lr.sum()), float(sr.sum())
    exp_long  = float(lr.mean()) if len(lr) else np.nan
    exp_short = float(sr.mean()) if len(sr) else np.nan
    tot = float(r.sum()); pos = max(sl,0)+max(ss,0)
    dom_share = (max(max(sl,0),max(ss,0))/pos) if pos>0 else 1.0
    dominant = 'long' if sl>=ss else 'short'
    minor_exp = exp_short if dominant=='long' else exp_long
    disguised = bool(dom_share>dom_thresh and (not np.isfinite(minor_exp) or minor_exp<=0))
    return {'gate':'twosided (L25)','pass':not disguised,'n_long':int(len(lr)),'n_short':int(len(sr)),
            'exp_long':exp_long,'exp_short':exp_short,
            'contrib_long_pct':(sl/tot*100) if tot else np.nan,
            'dominant':dominant,'dom_share_pos_pct':dom_share*100,
            'tag':None if not disguised else f'beta déguisé ({dominant}-dominé) — re-tester vs buy&hold timé'}

def gate_dsr(grid_sharpes, sr_obs, pooled_netR):                   # GATE 3 (DSR)
    sr = np.asarray([s for s in np.ravel(grid_sharpes) if np.isfinite(s)], float)
    N = max(len(sr), 2); g = 0.5772156649
    root = np.sqrt(2.0*np.log(N)); e_max = root*(1.0 - g/root)     # E[max] of N std-normal trials
    r = np.asarray(pooled_netR, float); nobs = len(r)
    sd = r.std(ddof=1) if nobs>1 else 0.0
    skew = float(((r-r.mean())**3).mean()/sd**3) if sd>0 else 0.0
    kurt = float(((r-r.mean())**4).mean()/sd**4) if sd>0 else 3.0
    var = max(1.0 - skew*sr_obs + (kurt-1.0)/4.0*sr_obs**2, 1e-9)
    sigma_sr = np.sqrt(var/max(nobs-1,1)); z = (sr_obs - e_max)/sigma_sr if sigma_sr>0 else np.nan
    passed = bool(np.isfinite(z) and sr_obs > e_max)
    return {'gate':'dsr','pass':passed,'N_trials':int(len(sr)),'SR_obs':float(sr_obs),
            'E_max_SR':float(e_max),'DSR_z':float(z),'skew':skew,'kurt':kurt,
            'tag':None if passed else 'grille = bruit (multiple testing, DSR<0)'}

def gate_oos(trades, split='2015-12-31'):                          # GATE 4 (L31)
    sd = pd.Timestamp(split); ent = pd.to_datetime(trades['entry'])
    tr, te = trades[ent <= sd], trades[ent > sd]
    mtr, mte = trade_metrics(tr), trade_metrics(te)
    flip = (np.sign(mtr['expR']) != np.sign(mte['expR']))
    survives = bool(np.isfinite(mte['expR']) and mte['expR']>0 and not flip)
    return {'gate':'oos (L31)','pass':survives,'split':split,
            'n_train':mtr['trades'],'train_expR':mtr['expR'],'train_sharpe':mtr['sharpe'],
            'n_test':mte['trades'],'test_expR':mte['expR'],'test_sharpe':mte['sharpe'],
            'tag':None if survives else 'régime-dépendant / décayé (flip OOS)'}

def run_gates(run, grid_sharpes, split='2015-12-31', weak_sharpe=0.5):
    base_trades = run(fill='stop'); base = trade_metrics(base_trades)
    edge_pos = bool(np.isfinite(base['expR']) and base['expR']>0 and base['pf']>1.0)
    sr_obs = float(np.nanmax(grid_sharpes)) if np.isfinite(np.nanmax(grid_sharpes)) else base['sharpe']
    gates = [gate_delay1(run), gate_twosided(base_trades),
             gate_dsr(grid_sharpes, sr_obs, base_trades['netR'].values), gate_oos(base_trades, split)]
    all_pass = all(x['pass'] for x in gates)
    if not edge_pos: verdict, reason = 'DISCARD', "pas d'edge positif après coûts"
    elif all_pass: verdict, reason = ('KEEP' if base['sharpe']>=weak_sharpe else 'BORDERLINE'), 'edge + 4 gates OK'
    else: verdict, reason = 'DISCARD', ' | '.join(x['tag'] for x in gates if not x['pass'])
    return {'base':base,'edge_positive':edge_pos,'gates':gates,
            'n_fail':int(sum(not x['pass'] for x in gates)),'verdict':verdict,'reason':reason}
```

---

## Annexe B — `code/build_ohlc_store.py`

```python
"""
build_ohlc_store.py — Reconstruct the consolidated daily OHLC store.
Sources (relative to DATA_DIR):
  - Indices  : panels/ftmo_{open,high,low,close}.csv
  - FX/BTC/XAU : panels/m5_indices/{TICKER}_M1.csv  (resampled to daily)
  - Commodities/ETH : raw/yf_{YFTICKER}_1d*.parquet
Output: {OUT_DIR}/{INSTR}.parquet + _coverage.csv
Daily-bar cut on UTC calendar day (00:00) for 24h markets — explicit assumption.
"""
import os, re, glob, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

DATA_DIR = os.environ.get("ALGO_DATA_DIR", "<HOME>/Desktop/Algo_claude/data")
OUT_DIR  = os.environ.get("OHLC_OUT_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ohlc"))

M1_RESAMPLE = {
    "EURUSD": ("EURUSD", "forex"), "GBPUSD": ("GBPUSD", "forex"), "USDJPY": ("USDJPY", "forex"),
    "USDCHF": ("USDCHF", "forex"), "USDCAD": ("USDCAD", "forex"), "AUDUSD": ("AUDUSD", "forex"),
    "NZDUSD": ("NZDUSD", "forex"), "EURGBP": ("EURGBP", "forex"), "AUDJPY": ("AUDJPY", "forex"),
    "BTCUSD": ("BTCUSD", "crypto"), "XAUUSD": ("XAUUSD", "commodities"),
}
YF = {
    "XAGUSD": ("SI=F", "commodities"), "XPTUSD": ("PL=F", "commodities"),
    "XPDUSD": ("PA=F", "commodities"), "UKOIL": ("BZ=F", "commodities"),
    "WHEAT": ("ZW=F", "commodities"), "SOYBEAN": ("ZS=F", "commodities"),
    "COFFEE": ("KC=F", "commodities"), "COCOA": ("CC=F", "commodities"),
    "ETHUSD": ("ETH-USD", "crypto"),
}
# Skipped (no reliable local daily OHLC): USOIL (CL=F truncated), GBPJPY,
# and 8 close-only cryptos (LTC/XRP/XMR/NEO/ADA/DASH/DOT/DOGE).

def _clean(df):
    df = df[["open", "high", "low", "close"] + (["spread"] if "spread" in df else [])].copy()
    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df[(df[["open", "high", "low", "close"]] > 0).all(axis=1)]
    df.index = pd.to_datetime(df.index); df.index.name = "Date"
    return df.sort_index()

def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    rep = []; P = os.path.join(DATA_DIR, "panels")
    o = pd.read_csv(f"{P}/ftmo_open.csv",  index_col=0, parse_dates=True)
    h = pd.read_csv(f"{P}/ftmo_high.csv",  index_col=0, parse_dates=True)
    l = pd.read_csv(f"{P}/ftmo_low.csv",   index_col=0, parse_dates=True)
    c = pd.read_csv(f"{P}/ftmo_close.csv", index_col=0, parse_dates=True)
    for t in c.columns:
        df = _clean(pd.DataFrame({"open": o[t], "high": h[t], "low": l[t], "close": c[t]}))
        df.to_parquet(f"{OUT_DIR}/{t}.parquet")
        rep.append((t, "indices", "ftmo_panel", len(df), df.index.min().date(), df.index.max().date(), ""))
    for t, (fn, cls) in M1_RESAMPLE.items():
        d = pd.read_csv(f"{P}/m5_indices/{fn}_M1.csv",
                        usecols=["timestamp_utc", "open", "high", "low", "close", "spread"])
        d["dt"] = pd.to_datetime(d["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
        d = d.dropna(subset=["dt"]); d["date"] = d["dt"].dt.normalize()
        g = d.groupby("date").agg(open=("open", "first"), high=("high", "max"),
                                  low=("low", "min"), close=("close", "last"),
                                  spread=("spread", "median"))
        g = _clean(g); g.to_parquet(f"{OUT_DIR}/{t}.parquet")
        rep.append((t, cls, "M1_resample", len(g), g.index.min().date(), g.index.max().date(),
                    f"spread~{g['spread'].median():.0f}pt"))
    for t, (yt, cls) in YF.items():
        cands = sorted(glob.glob(f"{DATA_DIR}/raw/yf_{yt}_1d*.parquet"), key=os.path.getsize)
        if not cands:
            rep.append((t, cls, "MISSING", 0, "", "", "")); continue
        df = pd.read_parquet(cands[-1]); df.columns = [str(x).lower() for x in df.columns]
        df = _clean(df); df.to_parquet(f"{OUT_DIR}/{t}.parquet")
        rep.append((t, cls, f"yf:{yt}", len(df), df.index.min().date(), df.index.max().date(), ""))
    R = pd.DataFrame(rep, columns=["instr","class","source","days","start","end","note"])
    R = R.sort_values(["class","instr"]).reset_index(drop=True)
    R.to_csv(f"{OUT_DIR}/_coverage.csv", index=False)
    print(R.to_string(index=False)); print(f"\n{(R.days>0).sum()}/40 instruments with real OHLC -> {OUT_DIR}")
    return R

if __name__ == "__main__":
    build()
```

---

## Annexe C — `code/strat_s001_crabel_nr_orb.py`

```python
"""
Strategy 1/109 — Toby Crabel 2-Bar Narrow Range + Opening Range Breakout.
Source: https://oxfordstrat.com/trading-strategies/toby-crabel-narrow-range-1/  (rating C)
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

LOOK_BACK, STRETCH_LEN, STRETCH_MULT, ATR_LEN, ATR_STOP = 20, 10, 2.0, 20, 6.0

def crabel_signals(df, look_back=LOOK_BACK, stretch_len=STRETCH_LEN, stretch_mult=STRETCH_MULT):
    h, l, o = df['high'], df['low'], df['open']
    rng2 = (pd.concat([h, h.shift(1)], axis=1).max(axis=1)
            - pd.concat([l, l.shift(1)], axis=1).min(axis=1))
    prev_min = rng2.rolling(look_back).min().shift(1)
    setup = (rng2 <= prev_min) & rng2.notna() & prev_min.notna()
    noise = pd.concat([h - o, o - l], axis=1).min(axis=1).clip(lower=0)
    stretch = noise.rolling(stretch_len).mean() * stretch_mult
    return setup, stretch

def run(target_index, time_index, uni, costs):
    all_tr, per = [], {}
    for t, df in uni.items():
        setup, stretch = crabel_signals(df)
        tr = lab.simulate_bracket(df, setup, stretch, target_index=target_index,
                                  time_index=time_index, atr_len=ATR_LEN,
                                  atr_stop=ATR_STOP, cost_bps=costs[t])
        if len(tr):
            tr['instr'] = t; all_tr.append(tr); per[t] = lab.trade_metrics(tr)
    pool = pd.concat(all_tr, ignore_index=True) if all_tr else pd.DataFrame()
    return pool, per

def pooled_stats(pool):
    if len(pool) == 0:
        return dict(trades=0, expR=np.nan, pf=np.nan, win=np.nan)
    r = pool['netR'].values
    pf = r[r > 0].sum() / abs(r[r < 0].sum()) if (r < 0).any() else np.inf
    return dict(trades=len(r), expR=float(r.mean()), pf=float(pf), win=float((r > 0).mean()))

if __name__ == "__main__":
    uni = lab.load_universe()
    costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
    # representative point
    TI_REP, TM_REP = 3.0, 10
    pool, per = run(TI_REP, TM_REP, uni, costs)
    ps = pooled_stats(pool); pm = lab.trade_metrics(pool)
    perdf = pd.DataFrame(per).T
    perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf = perdf.sort_values('expR', ascending=False); perdf.to_csv("s001_per_instrument.csv")
    # sensitivity sweep
    TIs = [1, 2, 3, 4, 6, 8, 10]; TMs = [1, 3, 5, 10, 20, 40]
    grid = np.full((len(TIs), len(TMs)), np.nan); pf_grid = np.full_like(grid, np.nan)
    for a, ti in enumerate(TIs):
        for b, tm in enumerate(TMs):
            s = pooled_stats(run(ti, tm, uni, costs)[0]); grid[a, b] = s['expR']; pf_grid[a, b] = s['pf']
    pd.DataFrame(grid, index=[f"{x}R" for x in TIs], columns=[f"{x}d" for x in TMs]).to_csv("s001_sensitivity_expectancy.csv")
    edge = (ps['expR'] > 0) and (ps['pf'] > 1.0)
    print("VERDICT:", "EDGE — keep" if edge else "NO EDGE — discard")
    # heatmap
    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid))
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(TMs))); ax.set_xticklabels([f"{x}d" for x in TMs])
    ax.set_yticks(range(len(TIs))); ax.set_yticklabels([f"{x}R" for x in TIs])
    ax.set_xlabel("Time exit (days held)"); ax.set_ylabel("Target (x initial risk)")
    for a in range(len(TIs)):
        for b in range(len(TMs)):
            ax.text(b, a, f"{grid[a,b]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout()
    fig.savefig("s001_sensitivity.png", dpi=130)
```

---

*Fin du rapport — stratégie 1/109. Le moteur (`ftmo_lab.py`) et le store OHLC sont réutilisés tels quels pour les stratégies suivantes ; seul un fichier `strat_sNNN_*.py` est ajouté par stratégie.*
