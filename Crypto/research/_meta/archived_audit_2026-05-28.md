# Audit Crypto Archived — Inventaire Complet
*Date audit : 2026-05-28 | Branche : claude/crypto-audit-2026-05-28*
*Scope : Crypto/research/archived/ + Crypto/data/ | LECTURE SEULE — aucun backtest lancé*

---

## CONVENTIONS

- **NON DOCUMENTÉ** : information introuvable dans les fichiers (pas de POSTMORTEM, pas de résultats JSON)
- **INFÉRÉ** : cause déduite du code ou du contexte (sans source primaire explicite)
- **Documentation complète** : POSTMORTEM + HYPOTHESIS/DECISION présents
- **Code seul** : uniquement le script de feasibility, pas de résultats sauvegardés

---

## PARTIE 1 — INVENTAIRE DATA

### 1.1 Données de prix crypto

| Fichier / Répertoire | Contenu | Taille approx | Couverture temporelle |
|---|---|---|---|
| `Crypto/research/archived/carry/cs_carry/data/prices_daily.csv` | 12 assets daily close (ADA/ARB/AVAX/BCH/BTC/DOGE/DOT/ETH/LINK/LTC/OP/SOL) | NON DOCUMENTÉ | 2024-01-01 → 2026-05-10 |
| `Crypto/data/pairs_trading/binance/` | 1h OHLCV CSVs Binance perp (AAVE/ADA/ATOM/AVAX/BNB/BTC/DOGE + autres) | ~1.6 MB par fichier | NON DOCUMENTÉ (INFÉRÉ 2021-2026) |
| `Crypto/data/delta_neutral/spot/` | 8h prix spot (BIO/HMSTR/MEGA/STX/TRUMP/TST/WLD) | NON DOCUMENTÉ | NON DOCUMENTÉ |
| `Crypto/data/vrp/cache/BTC_daily_close.parquet` | BTC-USD close journalier | ~31 KB | NON DOCUMENTÉ |
| `Crypto/data/vrp/cache/BTC_dvol_1d.parquet` | BTC Deribit Volatility Index (DVOL) journalier | ~30 KB | NON DOCUMENTÉ |

### 1.2 Funding rates (Hyperliquid)

| Fichier | Contenu | Nb symboles | Couverture temporelle |
|---|---|---|---|
| `Crypto/data/funding_carry/BTC_funding.csv` | Funding 8h, fréquence horaire | — | 2023-05-12 → 2026-05-04 |
| `Crypto/data/funding_carry/ETH_funding.csv` | Funding 8h, fréquence horaire | — | 2023-05-12 → 2026-05-04 |
| `Crypto/data/funding_carry/` (total) | Ensemble des symboles HL | **190 symboles** | 2023-05-12 → 2026-05-04 |

### 1.3 Données de missions spécifiques (archivées dans les sous-dossiers)

| Fichier | Mission | Contenu | Couverture |
|---|---|---|---|
| `archived/other/wav_h3/data/wiki/{TOKEN}.parquet` | WAV H3 | Wikipedia daily pageviews, 21 tokens | 2018 → 2026-05-21 |
| `archived/other/fgvd_h1/data/fg_raw.parquet` | FGVD H1 | Fear & Greed Index daily | 2018-02-01 → 2026-05-23 |
| `archived/other/fgvd_h1/data/btc_price_raw.parquet` | FGVD H1 | BTC-USD daily close (Yahoo) | 2017-01-01 → 2026-05-23 |
| `archived/other/fgvd_h1/data/merged.parquet` | FGVD H1 | F&G + BTC aligned | 2018-02-02 → 2026-05-23 (3028 obs) |
| `archived/etf_regime_overlay/data/etf_flows_raw.parquet` | ETF Regime | BTC ETF net flows daily (BitBO) | 2024-01-12 → 2026-05-22 (484 jours) |
| `archived/etf_regime_overlay/data/stablecoin_supply_raw.parquet` | ETF Regime | Stablecoin supply daily (DeFiLlama) | 2023-01-01 → 2026-05-23 (1239 jours) |
| `archived/etf_regime_overlay/data/prices_cache.parquet` | ETF Regime | 14 assets daily close | 2024-01-11 → 2026-05-22 |
| `archived/other/eth_mvrv_netflow/data/` | ETH MVRV+Netflow | CoinMetrics MVRV + exchange netflow ETH | 2016-2026 (~3795 obs) |
| `archived/options/vrp_deribit/data/cache/` | VRP Deribit | BTC daily close + DVOL | NON DOCUMENTÉ (INFÉRÉ 2021-2026) |
| `archived/carry/cs_carry/data/prices_daily.csv` | CS Carry | 12 assets daily | 2024-01-01 → 2026-05-10 |

### 1.4 Données non-crypto présentes dans Crypto/data/

| Fichier | Nature | Note |
|---|---|---|
| `Crypto/data/raw/EURUSD_*.parquet` | FX M5 Dukascopy | ~8 MB, 2020-2024. Données FX, pas crypto — probablement copie depuis Forex/ |
| `Crypto/data/raw/GBPUSD_*.parquet` | FX M5 Dukascopy | ~41 MB, 2020-2024. Idem |
| `Crypto/data/raw/FRED_*.parquet` | Taux sans risque DTB3 | Daily RF — infrastructure commune |

---

## PARTIE 2 — INVENTAIRE DES TESTS ARCHIVÉS

*Classement : (A) Documentation complète, (B) Résultats partiels disponibles, (C) Code seul*

---

### ═══ BLOC CARRY ═══

---

#### TEST-C01 : Perp-Spot Basis Trading
- **Répertoire** : `carry/basis_trading/`
- **Documentation** : Code seul (docstring)
- **Signal** : `basis_z = z-score(perp_close/spot_close − 1, 30d)` → short perp si z > +1.5σ, long perp si z < −1.5σ. Numéro signal : **36**.
- **Univers** : BTC, ETH, SOL
- **Fréquence** : Daily, max hold 10 jours
- **Coût RT** : 0.17%
- **Période** : 2021 → 2026
- **Stop-loss** : 7%
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : coût drag ou signal non significatif
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-C02 : CS Carry (90 paramètres)
- **Répertoire** : `carry/cs_carry/`
- **Documentation** : Code seul + résultats CSV (`feasibility_full_results.csv`)
- **Signal** : 6 variantes de signal (z-score / rank / normalized, trailing funding) × 5 fréquences de rebalancement × 3 niveaux de levier = **90 combinaisons**
- **Univers** : 12 assets (ADA/ARB/AVAX/BCH/BTC/DOGE/DOT/ETH/LINK/LTC/OP/SOL)
- **Fréquence** : journalier, 3j, hebdomadaire, bimensuel, mensuel (testées)
- **Coût RT** : NON DOCUMENTÉ
- **Période** : 2024-01-01 → 2026-05-10
- **Résultats (meilleur IS)** : Sharpe = 0.314 (zscore | Weekly | 3×), MaxDD = −73.5%, Beta = 1.41
- **Verdict** : Sharpe sous le gate RESEARCH_PASS (>0.7), **β-dominé** (beta=1.41, corrélation portefeuille ≥0.80)
- **Raison d'archivage** : INFÉRÉ : β-dominance (L11) — long-only CS crypto systématiquement beta-dominé
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-C03 : Funding Carry Cross-Sectionnel
- **Répertoire** : `carry/funding_carry/`
- **Documentation** : Code seul (docstring)
- **Signal** : Rank par trailing 7d mean funding rate → short top-20%, long bottom-20%
- **Univers** : HL perps (N NON DOCUMENTÉ)
- **Fréquence** : 8h, 24h, 7d (testées)
- **Coût RT** : 0.34% (RT taker × 2)
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : coût drag 0.34% RT trop élevé pour la magnitude du carry signal
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-C04 : Funding Momentum
- **Répertoire** : `carry/funding_momentum/`
- **Documentation** : Code seul (docstring)
- **Signal** : `funding_trend[T] = mean_7d[T-1] − mean_14d[T-8]`, z-scoré 60d rolling. Long BTC quand z > +0.5. Numéro signal : **29**.
- **Univers** : BTC (TS, non CS)
- **Fréquence** : Hebdomadaire
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : IC insuffisant ou proxy momentum
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-C05 : Funding Rate Reversal
- **Répertoire** : `carry/funding_reversal/`
- **Documentation** : Code seul (docstring)
- **Signal** : z-score funding 60d rolling → short si z > +2.5σ, long si z < −2.0σ. Numéro signal : **35**.
- **Univers** : BTC, ETH, SOL (Binance)
- **Fréquence** : Daily
- **Coût RT** : 0.17%
- **Période** : 2023-05 → 2026-04
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : événements trop rares (z>+2.5σ ≈ 1.2% des jours) ou signal momentum plutôt que reversal
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-C06 : Signal Stack (TSMOM × Funding Carry)
- **Répertoire** : `carry/signal_stack/`
- **Documentation** : Code seul (docstring)
- **Signal** : 3 méthodes de combinaison TSMOM + Funding Carry : M1=Intersection, M2=Multiplicatif, M3=Scaler
- **Univers** : NON DOCUMENTÉ (INFÉRÉ crypto perps)
- **Fréquence** : Hebdomadaire (21 × 8h bars)
- **WF** : 12m train / 1m test
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : β-dominance (L11) — long-only TSMOM empêche la diversification vraie
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-C07 : USDT Quote Volume (Proxy de Flow)
- **Répertoire** : `carry/usdt_flows/`
- **Documentation** : Code seul (docstring)
- **Signal** : Volume USDT des paires Binance z-scoré vs baseline 30j. Long BTC+ETH quand z > 0. Référence : Chi/Chu/Hao 2025.
- **Univers** : 5 paires Binance (BTC, ETH + 3 autres), long BTC+ETH
- **Fréquence** : Hebdomadaire
- **Période** : 2022 → 2026
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : IC insuffisant ou proxy TSMOM
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

### ═══ BLOC MEAN REVERSION ═══

---

#### TEST-MR01 : CS Stat-Arb (HL 174 assets)
- **Répertoire** : `mean_reversion/cs_stat_arb/`
- **Documentation** : Code seul (docstring)
- **Signal** : `equal_weight(carry_z + momentum_z)` → long top-5 CS
- **Univers** : 174 assets HL
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : β-dominance ou t_HAC insuffisant
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MR02 : MR ATR-Bounded
- **Répertoire** : `mean_reversion/mean_reversion_atr/`
- **Documentation** : Code seul (docstring)
- **Signal** : Signe opposé aux features MLP (ATR-bounded), ciblé propfirm
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MR03 : Pairs Trading (18 assets HL)
- **Répertoire** : `mean_reversion/pairs_trading/`
- **Documentation** : Code seul (docstring)
- **Signal** : Funnel 4-étapes : corrélation → cointégration → IC → exécution
- **Univers** : 18 assets HL
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ. INFÉRÉ depuis CLAUDE.md : 0/19 paires qualifiées (test de cointégration)
- **Raison d'archivage** : INFÉRÉ : aucune paire cointégrée dans l'univers HL (tech premium drift 2024-2026)
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MR04 : Short-Term Reversal Smallcap (STR)
- **Répertoire** : `mean_reversion/str_smallcap/`
- **Documentation** : Code seul (docstring)
- **Signal** : STR cross-sectionnel sur CoinGecko top-50-250. Référence : Zaremba 2021.
- **Univers** : CoinGecko top-50 à top-250 (médian-cap)
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : 0.34% (documenté — noté "survivorship bias documenté")
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : survivorship bias, β-dominance, ou coût drag 0.34%
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MR05 : BTC-Neutral Residual MR (fichier loose)
- **Répertoire** : `mean_reversion/residual_mr_feasibility.py` (fichier racine, pas de sous-dossier)
- **Documentation** : Code seul (docstring)
- **Signal** : `−1 × z-score(residual log return après beta hedge BTC)`
- **Univers** : NON DOCUMENTÉ (alts vs BTC)
- **Fréquence** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ (image `residual_mr_equity.png` présente)
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : test préliminaire non concluant
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ pré-2026-05-23 (structure loose = test ancien)

---

#### TEST-MR06 : Vol-Regime MR (fichier loose)
- **Répertoire** : `mean_reversion/vol_regime_mr_feasibility.py` (fichier racine)
- **Documentation** : Code seul (docstring)
- **Signal** : `−1 × z-score(prix 5j)`, filtré sur jours de faible volatilité
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ (images `vol_regime_equity_curve.png`, `vol_regime_ic.png` présentes)
- **Raison d'archivage** : NON DOCUMENTÉ
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ pré-2026-05-23

---

### ═══ BLOC ML ═══

---

#### TEST-ML01 : XGBoost Meta-Labeling TSMOM
- **Répertoire** : `ml/meta_tsmom/`
- **Documentation** : Code seul (docstring)
- **Signal** : XGBoost meta-labeling sur TSMOM v2. Labels = trades profitables TSMOM. Référence : Lopez de Prado 2018.
- **Univers** : 10 assets, 2021-2024 train, 2024-07 → 2026-05 test
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : overfitting sur le train set ou IC OOS insuffisant
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-ML02 : MLP TSMOM (12 features économiques)
- **Répertoire** : `ml/mlp_tsmom/`
- **Documentation** : Code seul (docstring)
- **Signal** : MLP feed-forward sur 12 features économiques (momentum, vol, funding, macro), prédit returns 7j
- **Univers** : 12 assets, 4 fenêtres WF
- **Fréquence** : Journalier (rebalance NON DOCUMENTÉ)
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : overfitting ML ou IC OOS non significatif
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-ML03 : XGBoost Microstructure (v1/v2/v3)
- **Répertoire** : `ml/xgb_microstructure/`
- **Documentation** : Code seul (docstring, 3 versions de fichier)
- **Signal** : XGBoost CS labels sur features microstructure. Purged WF. 3 versions documentées :
  - v1 : classification binaire (direction)
  - v2 : AUC = **0.6454**, Sharpe IS = **0.734** (INFÉRÉ gate RESEARCH_PASS borderline)
  - v3 : extension L/S à partir de v2
- **Univers** : 10 assets
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats (v2)** : AUC = 0.6454, Sharpe = 0.734 (IS seulement, OOS NON DOCUMENTÉ)
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : OOS dégradation (AUC IS ≠ AUC OOS) ou β-dominance sur v3
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

### ═══ BLOC MOMENTUM ═══

---

#### TEST-MO01 : Adaptive Trend (softmax TSMOM)
- **Répertoire** : `momentum/adaptive_trend/`
- **Documentation** : Code seul (docstring)
- **Signal** : Poids softmax sur lookbacks [14/28/56/112]j → signal agrégé. Numéro signal : **31**.
- **Univers** : NON DOCUMENTÉ (INFÉRÉ crypto perps multi-assets)
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : β-dominance (L11) — TSMOM long-only = beta proxy
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MO02 : BTC Dominance (market neutral)
- **Répertoire** : `momentum/btc_dominance/`
- **Documentation** : Code seul (docstring)
- **Signal** : Return relatif 14j de BTC vs basket d'alts → market neutral
- **Univers** : BTC vs basket alts
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : corrélation BTC/alts trop haute pour neutralisation efficace
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MO03 : Cross Breakout CS (Robot Wealth)
- **Répertoire** : `momentum/cross_breakout/`
- **Documentation** : Code seul (docstring)
- **Signal** : Breakout CS (Robot Wealth), market neutral. Anti-corrélé au carry signal. Numéro signal : **32**.
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : Sharpe insuffisant post-coûts ou β-dominance résiduelle
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MO04 : CS Reversal (3 pires performers 4w)
- **Répertoire** : `momentum/cs_reversal/`
- **Documentation** : Code seul (docstring)
- **Signal** : Long 3 pires performers 4 semaines CS
- **Univers** : 10 assets, 2021 → 2026
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : momentum plutôt que reversal en crypto (L11 implication)
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MO05 : Donchian Breakout
- **Répertoire** : `momentum/donchian_breakout/`
- **Documentation** : Code seul (docstring)
- **Signal** : Long/short sur nouveau high/low N-jours (Donchian channel)
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : Journalier
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : long-only β-dominance ou Sharpe < 0.7
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MO06 : Intraday TSMOM (4h bars)
- **Répertoire** : `momentum/intraday_tsmom/`
- **Documentation** : Code seul (docstring)
- **Signal** : `sign(close[t] − close[t−lookback])`, vol-scalé, sur données 4h
- **Univers** : NON DOCUMENTÉ (INFÉRÉ multi-assets)
- **Fréquence** : 4h
- **Coût RT** : 0.09% (inférieur au standard 0.17% — INFÉRÉ maker ou hypothèse optimiste)
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : β-dominance ou coût drag
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MO07 : LSTM HL (4h bars)
- **Répertoire** : `momentum/lstm_hl/`
- **Documentation** : Code seul (docstring)
- **Signal** : LSTM sur données 4h HL, 13 features. Référence : Parente & Rizzuti 2026.
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : 4h
- **Coût RT** : NON DOCUMENTÉ (calculé : 117 trades/an → 19.95%/an de coût drag à 0.17%)
- **Résultats** : AUC = 0.6454 (IS seulement). Coût drag : **19.95%/an** → non viable
- **Raison d'archivage** : INFÉRÉ : fréquence trop élevée (117 trades/an × 0.17% RT = coût astronomique)
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MO08 : Monthly TSMOM (40 assets)
- **Répertoire** : `momentum/monthly_tsmom/`
- **Documentation** : Code seul (docstring)
- **Signal** : Average [1m/3m/6m] TSMOM, long-only top-10 CS. Numéro signal : **33**.
- **Univers** : 40 assets
- **Fréquence** : Mensuelle
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : β-dominance (L11) — TSMOM long-only = beta proxy
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MO09 : Temporal Patterns (calendar 4h)
- **Répertoire** : `momentum/temporal_patterns/`
- **Documentation** : Code seul (docstring)
- **Signal** : Effets calendaires sur barres 4h : heure / jour semaine / semaine / mois. Gate : t_HAC > 2.5.
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : 4h
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : t_HAC < 2.5 sur tous les patterns testés
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-MO10 : TSMOM Préliminaire BTC/ETH/SOL (fichier loose)
- **Répertoire** : `momentum/tsmom_feasibility.py` (fichier racine)
- **Documentation** : Code seul (docstring)
- **Signal** : TSMOM Moskowitz/Ooi/Pedersen 2012, quick signal test sans coûts ni classes
- **Univers** : BTC, ETH, SOL
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : 0% (test préliminaire brut — explicitement noté sans coûts)
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : test préliminaire avant module `momentum/adaptive_trend/`
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ pré-2026-05-23 (test préliminaire)

---

#### TEST-MO11 : STR 30-min (fichier loose)
- **Répertoire** : `momentum/str_feasibility.py` (fichier racine)
- **Documentation** : Code seul (docstring : "Cross-Sectional Short-Term Reversal — 30-min Feasibility Check")
- **Signal** : STR CS à fréquence 30 minutes
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : 30 minutes
- **Coût RT** : NON DOCUMENTÉ (INFÉRÉ trop élevé pour 30min)
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : coût drag fatal à 30min (0.17% RT >> alpha 30-min)
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ pré-2026-05-23

---

### ═══ BLOC PATTERNS ═══

---

#### TEST-P01 : Crash Recovery (−8% en 3j)
- **Répertoire** : `patterns/crash_recovery/`
- **Documentation** : Code seul (docstring)
- **Signal** : Retour −8% en 3 jours → achat. Numéro signal : **34**.
- **Univers** : BTC, ETH, SOL, BNB, AVAX (Binance)
- **Fréquence** : Daily, hold 5j
- **Coût RT** : 0.17%
- **Période** : 2018 → 2026
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : fréquence trop faible, momentum > mean-reversion post-crash en crypto
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-P02 : Seasonality Mensuelle BTC/ETH
- **Répertoire** : `patterns/crypto_seasonality/`
- **Documentation** : Code seul (docstring)
- **Signal** : Mois forts : Oct/Nov/Dec/Jan/Apr — Mois faibles : May-Sep. Long/short selon mois.
- **Univers** : BTC, ETH
- **Fréquence** : Mensuelle
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : HAC deflation ou données insuffisantes pour t_HAC > 2.5 sur N~5 cycles
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-P03 : ORB Crypto (Zarattini 2024)
- **Répertoire** : `patterns/orb_crypto/`
- **Documentation** : Code seul (docstring)
- **Signal** : Opening Range Breakout (Zarattini 2024 adapté). RVOL ≥ 1.5× lors de 00:00-01:00 UTC → entrée direction breakout. Hold 4-8h.
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : 4-8h
- **Coût RT** : 0.17%
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : fréquence faible (~15-25 événements/an) ou coût drag
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-P04 : Asian Range Breakout (ORB v2)
- **Répertoire** : `patterns/orb_crypto_v2/`
- **Documentation** : Code seul (docstring)
- **Signal** : Asian Session Range Breakout adapté de NQ ORB (Strategy C). Numéro signal : **30**.
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : NON DOCUMENTÉ (INFÉRÉ daily, session asiatique)
- **Coût RT** : 0.17%
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : mécanisme NQ ORB ne se transfère pas aux crypto perps (fréquence de signal + coûts)
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-P05 : Volatility Breakout (BB Squeeze)
- **Répertoire** : `patterns/volatility_breakout/`
- **Documentation** : Code seul (docstring)
- **Signal** : Breakout quand `BB_width < percentile` (squeeze). Fréquence : ~15-25 événements/an.
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : fréquence trop faible (15-25/an → power insuffisant)
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-P06 : Weekend Anomaly (short BTC)
- **Répertoire** : `patterns/weekend_anomaly/`
- **Documentation** : Code seul (docstring)
- **Signal** : Short BTC vendredi 16:00 → lundi 00:00 UTC (56h hold)
- **Univers** : BTC (uniquement)
- **Fréquence** : Hebdomadaire
- **Coût RT** : 0.34% (aller-retour)
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : anomalie documentée pré-2021 mais absente en données récentes
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

### ═══ BLOC REGIME ═══

---

#### TEST-R01 : Combined Portfolio TSMOM L/S
- **Répertoire** : `regime/combined_portfolio/`
- **Documentation** : Code seul (docstring)
- **Signal** : TSMOM long (10 assets) + short (SOL/LINK/BCH/OP). Portfolio combiné.
- **Univers** : ~14 assets (10 long + 4 short)
- **Fréquence** : NON DOCUMENTÉ
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : Sharpe OOS = **0.76**, max daily DD = **−11.9%** (INFÉRÉ IS, pas WF complet)
- **Raison d'archivage** : INFÉRÉ : Sharpe OOS = 0.76 borderline RESEARCH_PASS, maxDD −11.9% journalier excessif pour propfirm
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-R02 : HMM 3-états (bull/range/bear)
- **Répertoire** : `regime/regime_hmm/`
- **Documentation** : Code seul (docstring)
- **Signal** : HMM 3 états (bull/range/bear) sur BTC daily returns 2019→2026. Utilisé comme filtre de régime.
- **Univers** : BTC (TS uniquement)
- **Fréquence** : Journalier
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : régime HMM ne prédit pas la direction — filtre non-prédictif
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-R03 : HMM Meta-Routing 4 états
- **Répertoire** : `regime/regime_meta/`
- **Documentation** : Code seul (docstring)
- **Signal** : 4 états HMM : BULL→long, BEAR→short, RANGE→flat, CRASH→cash. 2020-2022 train, 2023-2026 OOS.
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : Journalier
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : HMM OOS dégradation ou Sharpe < 0.7 OOS
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

### ═══ BLOC SENTIMENT ═══

---

#### TEST-S01 : MVRV Z-Score Scaler (TSMOM)
- **Répertoire** : `sentiment/mvrv/`
- **Documentation** : Code seul (docstring)
- **Signal** : MVRV Z-score comme scaler multiplicatif de Strategy A TSMOM (Glassnode ou proxy)
- **Univers** : NON DOCUMENTÉ (INFÉRÉ BTC/ETH/SOL)
- **Fréquence** : NON DOCUMENTÉ (INFÉRÉ hebdomadaire, aligné Strategy A)
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : INFÉRÉ : corr(MVRV, TSMOM-28d) = +0.73 documenté dans eth_mvrv_netflow/POSTMORTEM.md → MVRV est un proxy TSMOM, non-orthogonal
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-S02 : Fear & Greed Contrarian (fichier loose)
- **Répertoire** : `sentiment/fg_contrarian_feasibility.py` (fichier racine)
- **Documentation** : Code seul (docstring : "extreme fear → long, extreme greed → short, 5-day hold")
- **Signal** : F&G < seuil peur → long BTC, F&G > seuil avidité → short BTC. Hold 5j.
- **Univers** : BTC (TS)
- **Fréquence** : Daily, hold 5j
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : INFÉRÉ depuis L17 (FGVD POSTMORTEM) : F&G est proxy momentum, pas contrarian. Également documenté dans FGVD H1.
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ pré-2026-05-23 (test préliminaire avant FGVD H1)

---

### ═══ BLOC OTHER — TESTS PLEINEMENT DOCUMENTÉS ═══

---

#### TEST-O01 : PMR Basis Mean-Reversion ★ Documentation complète
- **Répertoire** : `other/pmr_basis/`
- **Documentation** : POSTMORTEM.md + résultats JSON (`results.json`)
- **Signal** : `basis_z = z-score(perp_close/spot_close − 1, 90d)`. Fade l'extrême : short perp si z ≥ +1.5σ, long perp si z ≤ −1.5σ. Exit quand z revient à 0 ou 7 jours.
- **Univers** : 29 coins Binance perp
- **Fréquence** : Daily (événement-driven sur z > |1.5|)
- **Coût RT** : 0.17% (taker)
- **Période** : Juin 2023 → Mai 2026
- **Résultats** :
  - IC pré-flight 3j : −0.0643, t_HAC = −**2.86** (PASS ✓)
  - Backtest Sharpe : **−0.55**
  - MaxDD : **−65%**
  - WF : **0%** (aucun fold positif)
  - Événements : **912/an** → coût drag **178%/an**
  - Gross P&L estimé : +16-20%/an vs coûts 97-178%/an → net catastrophique
- **Raison d'archivage** : Signal statistiquement réel (IC significatif) mais **turnover excessif** — 912 événements/an × 0.17% RT = 178%/an de coût drag. Le gate L12 (ceiling events) n'était pas encore formalisé à ce stade.
- **Leçon générée** : L12 (event-count ceiling gate)
- **n_tests consommés** : **142 → 148** (+6)
- **Date archivé** : 2026-05-23

---

#### TEST-O02 : OAGF — Open Auction Gap Fade ★ Documentation complète
- **Répertoire** : `other/oagf/`
- **Documentation** : POSTMORTEM.md + HYPOTHESIS_V2.md + résultats JSON
- **Signal** : `gap_ret = (open_t − close_{t-1}) / close_{t-1}` aux settlements 8h (00:00/08:00/16:00 UTC). Fade le gap : limit order opposé à la direction, exit 1h plus tard.
- **Seuil** : |gap_ret| > 0.30%
- **Univers** : 29 coins Binance perp 1h (proxy HL — HL candleSnapshot sans historique avant ~Oct 2025)
- **Fréquence** : 1h (3 événements/j possibles, déclenché par seuil)
- **Coût RT** : 0.17% (limit order hypothèse maker — toutefois risque de fill)
- **Période** : Janvier 2024 → Mai 2026 (28 mois)
- **Résultats** :

  | Horizon | IC_pooled | t_HAC | N événements | Gate |
  |---------|-----------|-------|--------------|------|
  | 1h | −0.195 | −1.17 | 304 | **FAIL** |
  | 2h | −0.087 | −1.02 | 304 | **FAIL** |
  | 4h | −0.084 | −0.61 | 304 | **FAIL** |

  Direction correcte (IC négatif = gap up → retour négatif). Magnitude IC = −0.19 (très élevée). t_HAC insuffisant car **304 événements en 28 mois = 128/an à travers 29 coins = 4.4 événements/coin/an**.
- **Raison d'archivage** : Signal réel, **puissance statistique insuffisante**. Besoin de ~10 ans de données à 0.30% seuil OU réduction du seuil à 0.10% (→ 5× plus d'événements, 800/an) pour atteindre t_HAC = −2.5 en 28 mois.
- **Leçon générée** : L12 (event-count ceiling gate, formalisée)
- **n_tests consommés** : **148 → 151** (+3)
- **Date archivé** : 2026-05-23

---

#### TEST-O03 : ETH MVRV + Exchange Netflow ★ Documentation complète
- **Répertoire** : `other/eth_mvrv_netflow/`
- **Documentation** : POSTMORTEM.md
- **Signal (MVRV)** : `mvrv_z = (CapMVRVCur − MA_365d) / std_365d`. Hypothèse : MVRV élevé → overvalued → retour négatif. Source : CoinMetrics Community API.
- **Signal (Netflow)** : `net_z = ((FlowOutExUSD − FlowInExUSD) − MA_90d) / std_90d`. Hypothèse : sorties élevées → accumulation → retour positif.
- **Signal combiné** : `comp = net_z − 0.5 × mvrv_z`
- **Univers** : ETH (TS)
- **Fréquence** : Hebdomadaire (test IC), journalier (données)
- **Période** : 2016 → 2026 (~3795 obs daily, ~488 weekly)
- **Résultats** :

  | Signal | IC fwd_14d | t_HAC | IC fwd_30d | t_HAC | Gate |
  |--------|-----------|-------|-----------|-------|------|
  | MVRV_z | +0.107 | +1.75 | +0.113 | +1.41 | FAIL (momentum, pas MR) |
  | Netflow_z | −0.015 | −0.36 | +0.003 | +0.11 | FAIL (IC≈0 sous HAC) |

  - corr(MVRV, TSMOM-28d) = **+0.734** (gate orthogonalité FAIL — MVRV est proxy TSMOM)
  - Netflow : t naive = 2.58 (N=3398) → t_HAC = **0.11** (N_eff≈73) — L12b autocorrélation
- **Raison d'archivage** : MVRV = proxy momentum (corrélation TSMOM 0.73), pas signal contrarian. Netflow : HAC deflation totale (L12b) — régimes de flux persistants (6-18 mois) → N_eff << N_nominal.
- **Leçons générées** : L12b (HAC deflation autocorrélation persistante)
- **n_tests consommés** : **151 → 153** (+2)
- **Date archivé** : 2026-05-23

---

#### TEST-O04 : FGVD H1 — Fear & Greed Velocity Divergence ★ Documentation complète
- **Répertoire** : `other/fgvd_h1/`
- **Documentation** : POSTMORTEM.md + HYPOTHESIS.md + _bootstrap_notes.md
- **Signal** : `FGVD = F&G_velocity_7d − price_velocity_7d` (divergence). Hypothèse contrarian : quand sentiment monte plus vite que prix → retour négatif.
- **Univers** : BTC (TS)
- **Fréquence** : Journalier, forward 7j
- **Période** : 2018-02-02 → 2026-05-23 (3028 obs)
- **Résultats** :

  | Test | IC | t_HAC | Gate |
  |------|-----|-------|------|
  | IC_A (−price MR) | −0.0083 | −0.256 | FAIL |
  | IC_B (F&G velocity seul) | **+0.0085** | +0.274 | FAIL (mauvaise direction) |
  | IC_C (combiné) | +0.0054 | +0.202 | FAIL |

  - corr(FGVD, TSMOM-28d) = −0.247 (orthogonalité ✓)
  - Événements/an (signal < −1.5σ) : 16.9 (gate ≥ 20 → FAIL)
  - Décomposition D1 déclenche : **STOP**
- **Raison d'archivage** : IC_B positif (momentum, pas contrarian). F&G velocity = indicateur avancé dans la même direction (Albrecht 2025 : IC +0.085 à 4-32j). Mécanisme Da et al. 2011 (inversement equity) ne se transfère pas : F&G reflète les holders existants, pas les nouveaux acheteurs.
- **Leçon générée** : L17 (F&G velocity = proxy momentum, branche sentiment existants FERMÉE)
- **n_tests consommés** : **157 → 158** (+1)
- **Date archivé** : 2026-05-23

---

#### TEST-O05 : WAV H3 — Wikipedia Attention Velocity ★ Documentation complète
- **Répertoire** : `other/wav_h3/`
- **Documentation** : POSTMORTEM.md + HYPOTHESIS_WAV.md + _bootstrap_notes.md
- **Signal** : `attention_z = z-score(pageviews_7d_rolling)`, normalisé, vs prix. Hypothèse contrarian : pic d'attention Wikipedia → acheteurs non-informés → retour négatif à 7j.
- **Univers** : 21 tokens avec article Wikipedia valide (depuis 38 candidats, 17 exclus : article inexistant ou données insuffisantes)
- **Fréquence** : Journalier CS (cross-sectionnel), forward 7j
- **Période** : 2018-01-01 → 2026-05-21 (3063 dates, 21 tokens)
- **Résultats** :

  | Test | IC | t_HAC | Gate | Verdict |
  |------|-----|-------|------|---------|
  | IC_A (−price MR) | +0.01283 | +1.407 | — | momentum direction |
  | IC_B (WAV seul) | **+0.00158** | +0.156 | D4 FAIL | **mauvaise direction + ≈0** |
  | IC_C (combiné) | +0.02143 | +2.172 | — | momentum amplifié |
  | Lagging corr (wiki_z vs price_prior_7d) | +0.102 | — | ≤ 0.30 → PASS | Gate 1 PASS |
  | corr(attention_z, TSMOM-28d) | −0.022 | — | < 0.5 → PASS | orthogonal ✓ |

  - D4 pré-enregistré : "si IC_B > 0 → proxy momentum → STOP". **D4 déclenche.**
- **Raison d'archivage** : IC_B ≈ 0 (statistiquement nul) avec légère tilt positive (momentum). Wikipedia pour crypto altcoins = curiosité informationnelle post-spike, pas vecteur d'achat de nouveaux investisseurs. Da et al. 2011 (SVI equity) ≠ Wikipedia crypto (médium de découverte différent : Twitter/Reddit pour crypto).
- **Leçon générée** : L18 (Wikipedia attention = IC≈0, proxy momentum. Branche attention nouveaux acheteurs FERMÉE.)
- **n_tests consommés** : **158 → 159** (+1)
- **Date archivé** : 2026-05-23

---

#### TEST-O06 : HL Native Signals (3 signaux HL-spécifiques)
- **Répertoire** : `other/hl_native/`
- **Documentation** : Code seul (docstring)
- **Signaux** :
  1. OI/Price Divergence (open interest diverge du prix → anticipation retournement)
  2. Post-Liquidation MR (spike liquidations → mean reversion 1h)
  3. Funding Extreme Reversal (z > +3σ → short)
- **Univers** : Hyperliquid perps
- **Fréquence** : 1h
- **Coût RT** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : IC t_HAC < 2.5 ou fréquence d'événements insuffisante
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-O07 : Market Neutral (3 stratégies)
- **Répertoire** : `other/market_neutral/`
- **Documentation** : Code seul (docstring)
- **Stratégies** :
  1. CS Funding Carry (delta-neutral par le CS)
  2. BTC/ETH Stat-Arb
  3. Overnight Gap MR
- **Protocole** : 5 étapes d'évaluation
- **Univers** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ depuis CLAUDE.md : BTC/ETH stat-arb ES/NQ Engle-Granger p=0.28 (tech premium drift), autres signaux IC insuffisants
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-O08 : New Strategies (TSMOM Short + Weekly Seasonality)
- **Répertoire** : `other/new_strategies/`
- **Documentation** : Code seul (docstring)
- **Stratégies** :
  1. TSMOM Short-Only : signal TSMOM < 0 → short SOL/LINK/BCH/OP
  2. Weekly Return Seasonality : Keloharju 2016 adapté à crypto
- **Univers** : SOL/LINK/BCH/OP (short-only) + NON DOCUMENTÉ (seasonality)
- **Fréquence** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : short-only crypto = beta court inverse risqué, seasonality IC < seuil
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-O09 : Portfolio TSMOM + MR-ATR
- **Répertoire** : `other/portfolio_tsmom_mr/`
- **Documentation** : Code seul (docstring)
- **Signal** : Portfolio combiné TSMOM v2 + MR-ATR (corrélation = **−0.30**)
- **Objectif** : Améliorer le Propr daily loss metric via décorrélation interne
- **Univers** : NON DOCUMENTÉ
- **Fréquence** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : corrélation −0.30 insuffisante pour diversification propfirm, ou MR-ATR seul Sharpe < gate
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

#### TEST-O10 : Strategy C Search (4 tests macro + 4h)
- **Répertoire** : `other/strategy_c_search/`
- **Documentation** : Code seul (docstring)
- **Tests** :
  - A : Macro overlay NQ (VIX/DXY/SPY/GLD comme filtre sur Strategy C)
  - B : 4h body score (momentum court terme intraday)
  - C : Macro lag correction (décalage signal macro → signal NQ)
  - D : Google Trends "bitcoin" comme signal proxy de flow retail
- **Univers** : NQ (propfirm Strategy C context)
- **Fréquence** : NON DOCUMENTÉ
- **Résultats** : NON DOCUMENTÉ
- **Raison d'archivage** : NON DOCUMENTÉ. INFÉRÉ : IC t_HAC < 2.5 sur tous les 4 tests, ou correlation avec Strategy C insuffisante pour décorrélation utile
- **n_tests consommés** : NON DOCUMENTÉ
- **Date archivé** : INFÉRÉ 2026-05-23

---

### ═══ MISSIONS AUTONOMES — ETF FLOWS + OPTIONS ═══

---

#### TEST-M01 : ETF Flows + Stablecoin Regime Overlay ★ Documentation complète
- **Répertoire** : `etf_regime_overlay/`
- **Documentation** : POSTMORTEM.md + HYPOTHESIS.md + _bootstrap_notes.md
- **Signal** :
  ```
  flow_z(t) = (flow_7d(t) − μ_{30d}) / σ_{30d}
  stable_z(t) = (Δstable_7d(t) − μ_{30d}) / σ_{30d}
  regime_score(t) = 0.5 × flow_z(t) + 0.5 × stable_z(t)
  signal_A_filtered(t) = signal_A(t) × [regime_score(t-1) > +0.5σ]
  ```
- **Base** : Strategy A (TSMOM v3, 14 assets BTC/ETH/SOL+alts)
- **Sources** : BitBO.io (BTC ETF net flows, remplacé Farside après bloc 403) + DeFiLlama (stablecoin supply)
- **Univers** : 14 assets crypto (Strategy A universe)
- **Fréquence** : Journalière, fenêtre 7j pour régime
- **Période** : ETF flows : 2024-01-12 → 2026-05-22 (post-approbation SEC ETF Bitcoin spot)
- **Résultats** :

  | Métrique | Valeur | Gate |
  |----------|--------|------|
  | Δ E[ret \| actif] − E[ret \| inactif] | **+0.022%/jour** | ≥ 0.10%/j → FAIL |
  | t_HAC (lag=6) | −0.17 | — |
  | Temps en marché (τ=+0.5σ) | 31.4% | ~31% Gaussien ✓ |

  Amélioration alpha réelle mais **sous-seuil** : 0.022%/j × 250j × 31.4% ≈ +1.7%/an → trop faible pour justifier gate WF (amélioration Sharpe < 0.10×).
- **Raison d'archivage** : Overlay sur stratégie haute-Sharpe (SR>1.0) apporte lift marginal insuffisant. Fenêtre post-ETF trop courte (~2.3 ans, peu de cycles régime). TSMOM 28j s'auto-filtre — données macro ajoutent peu.
- **Note data** : Farside.co.uk : HTTP 403 (Cloudflare). BitBO.io utilisé en remplacement (équivalent, BTC-dénominé).
- **Leçon générée** : L15 (régime overlay sur SR>1.0 : lift sub-threshold)
- **n_tests consommés** : **156 → 157** (+1)
- **Date archivé** : 2026-05-23

---

#### TEST-M02 : VRP Deribit BTC ★ Documentation complète
- **Répertoire** : `options/vrp_deribit/`
- **Documentation** : DECISION.md + HYPOTHESIS_VRP.md + résultats JSON (phases 2 et 3)
- **Signal** : `VRP_signal[t] = DVOL[t]^2 − RV30[t]^2`
  - DVOL = Deribit BTC Volatility Index (variance implicite 30j)
  - RV30 = realized variance rolling 30j (daily log returns)
  - Position : short straddle mensuel quand VRP > 0 (DVOL > RV historique)
  - Timing : entrée début de mois, expiration fin de mois (184 cycles, 2021-2026)
- **Univers** : BTC uniquement (options Deribit)
- **Fréquence** : Mensuelle (stratégie options, 1 cycle/mois)
- **Coût RT** : 0.03% × 4 legs (Deribit) + 0.5%+0.6% bid-ask spread
- **Résultats** :

  | Phase | Métrique | Valeur | Gate |
  |-------|----------|--------|------|
  | Phase 2 (IC daily overlapping) | IC | +0.126 | t=2.351 (BORDERLINE) |
  | Phase 2 (IC non-overlapping) | IC | −0.016 | — |
  | Phase 3 WF | Gross P&L/cycle | +0.122% | +4.44%/an |
  | Phase 3 WF | Coût option fees | −0.120% | −4.36%/an |
  | Phase 3 WF | Coût bid-ask | −0.121% | −4.38%/an |
  | Phase 3 WF | **Net P&L/an** | **−4.46%/an** | > 5%/an → **FAIL** |
  | Phase 3 WF | Sharpe HAC | **−2.68** | > 0.5 → **FAIL** |
  | Phase 3 WF | Folds positifs | **0/13** | — |

  Ratio coûts/gross = **200%**. Prime VRP structurellement positive (DVOL > RV 80% du temps) mais non accessible retail net de coûts Deribit.
- **Raison d'archivage** : **Erreur d'unité VRP** : magnitude académique en unités de variance, pas en % notionnel. À la conversion B-S : gross 4.4%/an vs coûts retail 8.89%/an → net −4.46%/an. Accessible uniquement à coût institutionnel < 1bp.
- **Leçon générée** : L13 (VRP unit error : variance ≠ % notionnel)
- **n_tests consommés** : **153 → 156** (+3 : Phase 1=0, Phase 2=+1, Phase 3=+2)
- **Date archivé** : 2026-05-23

---

## PARTIE 3 — SYNTHÈSE STATISTIQUE

### 3.1 Comptage global

| Catégorie | N tests | Avec POSTMORTEM/DECISION | Avec résultats quantitatifs | Code seul |
|---|---|---|---|---|
| Carry | 7 | 0 | 1 (cs_carry CSV) | 6 |
| Mean Reversion | 6 | 0 | 0 | 6 |
| ML | 3 | 0 | 1 (xgb_microstructure AUC partiel) | 2 |
| Momentum | 11 | 0 | 0 | 11 |
| Patterns | 6 | 0 | 0 | 6 |
| Régime | 3 | 0 | 1 (combined_portfolio OOS Sharpe) | 2 |
| Sentiment | 2 | 0 | 0 | 2 |
| Other (code seul) | 5 | 0 | 0 | 5 |
| Other (doc complète) | 5 | 5 | 5 | 0 |
| ETF Regime Overlay | 1 | 1 | 1 | 0 |
| Options VRP | 1 | 1 | 1 | 0 |
| **TOTAL** | **50** | **7** | **10** | **40** |

### 3.2 Tests avec résultats quantitatifs identifiés

| Test | Métrique clé | Valeur | Verdict |
|---|---|---|---|
| TEST-O01 PMR Basis | Sharpe | −0.55 | FAIL |
| TEST-O01 PMR Basis | MaxDD | −65% | FAIL |
| TEST-O01 PMR Basis | WF | 0% | FAIL |
| TEST-O01 PMR Basis | IC_3d (t_HAC) | −0.064 (−2.86) | PASS (signal réel) |
| TEST-O02 OAGF | IC_1h (t_HAC) | −0.195 (−1.17) | FAIL |
| TEST-O03 ETH MVRV | IC_MVRV_14d (t_HAC) | +0.107 (+1.75) | FAIL |
| TEST-O03 ETH MVRV | IC_Netflow_30d (t_HAC) | +0.003 (+0.11) | FAIL |
| TEST-O04 FGVD | IC_B (t_HAC) | +0.0085 (+0.274) | FAIL (direction) |
| TEST-O05 WAV H3 | IC_B (t_HAC) | +0.00158 (+0.156) | FAIL (direction+amplitude) |
| TEST-M01 ETF Regime | Δ ret/j | +0.022% | FAIL (seuil 0.10%/j) |
| TEST-M02 VRP Deribit | Net P&L/an | −4.46% | FAIL |
| TEST-M02 VRP Deribit | Sharpe HAC | −2.68 | FAIL |
| TEST-C02 CS Carry | Sharpe IS meilleur | 0.314 | FAIL (gate 0.7) |
| TEST-C02 CS Carry | Beta IS | 1.41 | β-dominé (L11) |
| TEST-R01 Combined | Sharpe OOS | 0.76 | BORDERLINE |
| TEST-R01 Combined | MaxDD journalier | −11.9% | Excès propfirm |
| TEST-ML03 XGBoost | AUC (IS) | 0.6454 | OOS non documenté |

### 3.3 n_tests consommés (partiellement documentés)

| Plage | Tests | n_tests cumulatif |
|---|---|---|
| Avant PMR Basis | Toutes phases early (carry/momentum/ML etc.) | 1 → ~141 |
| TEST-O01 PMR Basis | 6 tests | 142 → 148 |
| TEST-O02 OAGF | 3 tests | 148 → 151 |
| TEST-O03 ETH MVRV+Netflow | 2 tests | 151 → 153 |
| TEST-M02 VRP Deribit | 3 tests | 153 → 156 |
| TEST-M01 ETF Regime Overlay | 1 test | 156 → 157 |
| TEST-O04 FGVD H1 | 1 test | 157 → 158 |
| TEST-O05 WAV H3 | 1 test | 158 → **159** |

**n_tests crypto total : 159** (confirmé CLAUDE.md)
**n_tests non documentés (1 → ~141) : ~141 tests répartis sur ~43 modules de code**

### 3.4 Raisons d'archivage — distribution

| Raison | Tests concernés | Leçon |
|---|---|---|
| β-dominance (long-only CS) | TEST-C01, C02, C03, C04, MO01, MO02, MO08, et al. | L11 |
| Coût drag (fréquence × 0.17%) | TEST-O01, MO07, C03, et al. | L12 |
| Événements trop rares (power stat) | TEST-O02, P02, P03, P05, et al. | L12 |
| HAC deflation autocorrélation | TEST-O03 (Netflow) | L12b |
| VRP unit error | TEST-M02 | L13 |
| Lift sub-threshold (overlay SR>1) | TEST-M01 | L15 |
| Signal proxy momentum (mauvaise dir) | TEST-O04, O05, S01, S02 | L17, L18 |
| ML overfitting / OOS dégradation | TEST-ML01, ML02, ML03 (inféré) | — |
| IC OOS insuffisant | TEST-MR05, R02, R03 (inféré) | — |
| NON DOCUMENTÉ | ~20 tests | — |

---

## PARTIE 4 — INVENTAIRE DOCUMENTATION

### 4.1 Fichiers POSTMORTEM présents

| Fichier | Mission | Complet |
|---|---|---|
| `archived/other/pmr_basis/POSTMORTEM.md` | PMR Basis | ✓ |
| `archived/other/oagf/POSTMORTEM.md` | OAGF | ✓ |
| `archived/other/eth_mvrv_netflow/POSTMORTEM.md` | ETH MVRV+Netflow | ✓ |
| `archived/other/fgvd_h1/POSTMORTEM.md` | FGVD H1 | ✓ |
| `archived/other/wav_h3/POSTMORTEM.md` | WAV H3 | ✓ |
| `archived/etf_regime_overlay/POSTMORTEM.md` | ETF Regime Overlay | ✓ |
| `archived/options/vrp_deribit/DECISION.md` | VRP Deribit | ✓ (format DECISION, non POSTMORTEM) |

### 4.2 Fichiers HYPOTHESIS/Pre-registration présents

| Fichier | Mission |
|---|---|
| `archived/other/oagf/HYPOTHESIS_V2.md` | OAGF (v2 — une révision enregistrée) |
| `archived/other/fgvd_h1/HYPOTHESIS.md` | FGVD H1 |
| `archived/other/wav_h3/HYPOTHESIS_WAV.md` | WAV H3 |
| `archived/etf_regime_overlay/HYPOTHESIS.md` | ETF Regime Overlay |
| `archived/options/vrp_deribit/HYPOTHESIS_VRP.md` | VRP Deribit |

### 4.3 Fichiers de résultats structurés

| Fichier | Contenu |
|---|---|
| `archived/carry/cs_carry/feasibility_full_results.csv` | 90 combinaisons de paramètres, best Sharpe=0.314 |
| `archived/other/oagf/preflight_oagf_results.json` | IC gates Phase 1 OAGF |
| `archived/other/pmr_basis/results.json` | Résultats PMR complets |
| `archived/options/vrp_deribit/phase2_ic_results.json` | IC Phase 2 VRP |
| `archived/options/vrp_deribit/phase3_results.json` | WF Phase 3 VRP |
| `archived/other/fgvd_h1/data/phase2_results.json` | IC décomposition FGVD |
| `archived/other/wav_h3/data/phase2_results.json` | IC décomposition WAV |
| `archived/etf_regime_overlay/data/phase2_results.json` | Gate 2 ETF Regime |

### 4.4 Tests sans aucune documentation de résultats

Tous les tests **code seul** (~43 modules) n'ont ni POSTMORTEM, ni JSON de résultats, ni CSV de backtest. Les seules informations disponibles sont les docstrings Python (signal, univers, coût RT, période).

### 4.5 Framework code partagé (non-tests)

Les fichiers suivants dans `archived/other/` sont du code d'infrastructure ML partagée, **pas des tests individuels** :

```
backtest.py, config.py, features.py, labeler.py, live_trader.py, main.py,
model.py, oos_eval.py, packages.py, sanity_check.py, train_and_save.py,
trainer.py, walk_forward.py, test_delta_neutral_live.py, test_live_dryrun.py,
test_tsmom_live.py
```

Ces fichiers suggèrent une phase de tentative de déploiement live ML (delta-neutral + TSMOM) aujourd'hui archivée.

---

## PARTIE 5 — NOTES TECHNIQUES

### 5.1 Problèmes méthodologiques identifiés dans les tests pre-L8

Les tests les plus anciens (modules carry/momentum/patterns sans docstring de résultats) **précèdent probablement la formalisation des règles L1-L10** :

| Anomalie possible | Modules concernés | Risque |
|---|---|---|
| Pas de HAC Newey-West (t naïf) | Tests pré-2026-01 (inféré) | Inflation de significativité |
| Retours bruts (pas excess returns) | Tests anciens sans mention DTB3 | Biais alpha apparent |
| WF single split ou absent | Modules standalone `*_feasibility.py` | Overfitting IS |
| Coût 0% ou optimiste (0.09%) | MO06 intraday_tsmom | Biais net performance |
| Survivorship bias documenté | TEST-MR04 str_smallcap | Déclaré explicitement ✓ |

### 5.2 Note sur le coût 0.09% (TEST-MO06)

`momentum/intraday_tsmom/` utilise un coût RT de **0.09%** — inférieur au standard 0.17% de toutes les autres crypto tests. Cela suggère soit une hypothèse maker rebate (Hyperliquid : maker = 0.01%, taker = 0.05%, donc 0.06-0.10% RT envisageable pour limit orders), soit une erreur de modélisation. Le résultat (NON DOCUMENTÉ) doit être interprété avec cette hypothèse en tête.

### 5.3 HL API constraint relevée

`other/oagf/POSTMORTEM.md` documente explicitement : **HL candleSnapshot API ne fournit pas de données avant ~octobre 2025** (~7 mois de données). Tous les tests utilisant Binance comme proxy pour des signaux HL-natifs (OAGF, pairs_trading) ont cette limitation structurelle.

### 5.4 Farside.co.uk — data source fragile

`etf_regime_overlay/POSTMORTEM.md` confirme : **Farside.co.uk retourne HTTP 403** (Cloudflare IP block, validé 2026-05-23). BitBO.io (`bitbo.io/treasuries/etf-flows/`) est le remplacement valide (données en BTC-dénominé, z-score = invariant).

### 5.5 CoinMetrics Community API — limitation

`eth_mvrv_netflow/POSTMORTEM.md` utilise CoinMetrics Community (gratuit). Les métriques disponibles : CapMVRVCur, FlowOutExUSD, FlowInExUSD pour ETH/BTC. Les métriques Glassnode (stablecoin mint/burn) restent payantes (~$500/mois) et **non testées**.

### 5.6 Structure des directories loose (pré-module)

Les fichiers `*_feasibility.py` à la racine des dossiers `momentum/`, `mean_reversion/`, `sentiment/` suggèrent une **phase précoce de recherche** avant la structuration en modules (sous-dossiers). Ces tests correspondent aux n_tests 1-~50 (non tracés individuellement).

### 5.7 Comparaison v1/v2 xgb_microstructure

Le dossier `momentum/comparison/` contient `v1_v2_longshort_comparison.py` et `v1_v2_comparison.png` — comparaison visuelle des deux versions XGBoost. Ce dossier est **de support**, pas un test indépendant.

### 5.8 Données FX dans Crypto/data/raw/

La présence de parquets Dukascopy EURUSD/GBPUSD dans `Crypto/data/raw/` est **anormale**. Ces données appartiennent à `Forex/research/`. INFÉRÉ : copie ou symlink accidentel — ne pas confondre avec données crypto lors de futurs audits.

---

*Audit généré le 2026-05-28 sur branche `claude/crypto-audit-2026-05-28`*
*AUDIT SEULEMENT — aucun backtest lancé, aucun fichier de stratégie modifié*
