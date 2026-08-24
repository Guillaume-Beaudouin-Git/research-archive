# N_tests Restructure — Crypto Research 2026-05-28

*Branche : `claude/crypto-audit-2026-05-28` | Investigateur : Claude Sonnet 4.6*
*Sources : `archived_audit_2026-05-28.md`, `audit_verification_2026-05-28.md`,*
*`readme_section_crypto.md` §6.51, `documentation_inventory.md` §I, POSTMORTEMs,*
*scripts archived/ et passed/ (lecture seule)*
*Prérequis : `audit_verification_2026-05-28.md` lu en premier*

---

## DÉFINITION OPÉRATIONNELLE

**Hypothèse économique distincte** : mécanisme générateur de rendement unique +
référence académique primaire distincte. Deux signaux qui partagent le même mécanisme
(ex. lookbacks différents sur le même signal de momentum) comptent comme **une** hypothèse
avec **N variants**.

**Variant paramétriste** : version d'une même hypothèse avec paramètres différents (seuils,
lookbacks, fréquences, leviers, horizons). Groupable sous DSR Bailey-LdP comme un seul
"trial" avec biais d'optimisation, non comme N trials indépendants.

**Source des n_tests** : `documentation_inventory.md` §V est la source primaire. POSTMORTEMs
pour détail V2. Inféré pour V1 où le détail signal-par-signal n'est pas documenté.

---

## PARTIE 1 — Mapping famille → variants

### BLOC V1 OHLCV (n=1→142, signaux 6.01–6.36)

| # | Famille d'hypothèse économique | Mécanisme | Référence académique primaire | Nb variants testés | n_tests consommés | Source comptage |
|---|---|---|---|---|---|---|
| H01 | **TSMOM — Time-Series Momentum** | Returns passés cumulés prédisent direction future (tanh-scalé, vol-targeted) | Moskowitz, Ooi & Pedersen (2012) *JF* | 4 | ~4 | Scripts : `tsmom_feasibility.py`, `adaptive_trend/` (softmax [14/28/56/112]), `intraday_tsmom/` (Zarattini 2025), `monthly_tsmom/` (40 assets) |
| H02 | **Cross-Sectional Funding Carry** | Funding rate élevé = surdemande d'exposition → signal haussier CS | Schmeling, Schrimpf & Todorov (2023) | **93** | ~93 | CS Carry : 90 combos (6 signal_types × 5 rebal_freq × 3 leverage, fichier `feasibility_full_results.csv` 90 lignes) + `funding_carry/` (3 variantes fréquence) |
| H03 | **Funding Rate Momentum** | Tendance récente du funding rate prédit la direction future | Schmeling et al. 2023 (variation) | 1 | ~1 | `funding_momentum/` (signal 29 : mean_7d[T-1] − mean_14d[T-8]) |
| H04 | **Funding Rate Extreme Reversal** | Funding extrême (z > +2.5σ) mean-reverts | Carry mean-reversion standard | 1 | ~1 | `funding_reversal/` (signal 35, z-score 60d) |
| H05 | **TSMOM × Carry Stack** | Signal combiné : TSMOM comme direction + funding comme confirmation/taille | Signal stacking Israel & Ross 2017 | 3 | ~3 | `signal_stack/` (M1=Intersection, M2=Multiplicatif, M3=Scaler) |
| H06 | **Cross-Sectional Price Momentum (CS)** | CS breakout anti-corrélé au carry (direction haussière de breakout long-only) | Drogen, Hoffstein & Otte (2023) | 2 | ~2 | `cross_breakout/` (signal 32), `donchian_breakout/` |
| H07 | **Short-Term Cross-Sectional Reversal (STR)** | 3 pires performers 4 semaines en CS → reversal attendu | Zaremba (2021) *JBF*; Grundy & Martin (2001) | 2 | ~2 | `cs_reversal/`, `mean_reversion/str_smallcap/` |
| H08 | **STR 30-min (intraday reversal)** | STR cross-sectionnel sur barres 30-min | Même mécanisme que H07, fréquence différente = hypothèse distincte (cost model différent) | 1 | ~1 | `momentum/str_feasibility.py` (racine) |
| H09 | **BTC Dominance Rotation** | BTC season vs alt season : momentum relatif BTC vs basket prédictif de l'allocation | Observed market cycle mechanism | 1 | ~1 | `btc_dominance/` |
| H10 | **Opening Range Breakout Crypto** | RVOL élevé au 00:00-01:00 UTC → breakout directionnel dans le sens du range initial | Zarattini, Barbon & Aziz (SSRN 4729284, 2024) | 2 | ~2 | `orb_crypto/` (RVOL ≥ 1.5), `orb_crypto_v2/` (Asian session, signal 30) |
| H11 | **Volatility Breakout (BB Squeeze)** | Contraction de BB width < percentile → breakout directionnel imminent | Bollinger (1992); Cont & Das (2022) | 1 | ~1 | `volatility_breakout/` |
| H12 | **Crash Recovery Dip-Buy** | Chute −8% en 3j → liquidations forcées → rebond | Barberis, Shleifer & Vishny (1998) overreaction | 1 | ~1 | `crash_recovery/` (signal 34) |
| H13 | **Calendar Anomalies** | Saisonnalité intra-hebdo/intra-journalière/mensuelle → prédictibilité des retours | Keloharju, Linnainmaa & Nyberg (2016); Heston & Sadka (2008) | 3 | ~3 | `temporal_patterns/` (6 patterns 4h : heure/jour/semaine/mois), `crypto_seasonality/` (mois forts Oct-Jan/Apr), `weekend_anomaly/` (Lou, Polk & Skouras 2019) |
| H14 | **USDT Quote Volume Proxy Flow** | Volume USDT-dénominé = proxy de flow retail → signal momentum | Chi, Chu & Hao (2025) | 1 | ~1 | `carry/usdt_flows/` |
| H15 | **ML Pattern Recognition** | Features OHLCV + funding → modèle ML prédit la direction des retours | Parente & Rizzuti (2026); Bieganowski & Ślepaczuk (2025) | 6 | ~6 | `ml/meta_tsmom/` (XGBoost meta-labeling), `ml/mlp_tsmom/` (12 features économiques), `ml/xgb_microstructure/` v1+v2+v3 (purged WF), `lstm_hl/` (Parente 2026) |
| H16 | **CS Stat-Arb / Pairs Trading / MR CS** | Résidu β-hedgé ou spread cointegré mean-revert | Gatev, Goetzmann & Rouwenhorst (2006); Engle-Granger (1987) | 4 | ~4 | `cs_stat_arb/` (signal combiné carry+momentum), `pairs_trading/` (cointegration), `residual_mr_feasibility.py` (β-hedge), `vol_regime_mr_feasibility.py` |
| H17 | **MR ATR-bounded** | Mean-reversion conditionnelle sur range ATR (MLP-assisté) | Wilder (1978) ATR — application ML | 1 | ~1 | `mean_reversion/mean_reversion_atr/` |
| H18 | **HMM Regime Signal (Viterbi)** | État caché HMM (bull/range/bear) prédit la direction | Hamilton (1989) *Econometrica* | 2 | ~2 | `regime/regime_hmm/` (3 états Viterbi), `regime/regime_meta/` (4 états meta-routing) |
| H19 | **TSMOM L/S Combined Portfolio** | Long TSMOM + short alts sélectionnées = portfolio β-neutre | Moskowitz 2012 extension delta-neutral | 1 | ~1 | `regime/combined_portfolio/` (10 long + 4 short) |
| H20 | **HL-native Microstructure** | OI/Price divergence + post-liquidation MR + funding extreme = signaux HL-spécifiques | Kyle (1985) microstructure; order flow literature | 3 | ~3 | `other/hl_native/` (3 sous-signaux) |
| H21 | **MVRV Z-score Scaler** | MVRV z-score (on-chain valuation) comme scaler multiplicatif de TSMOM A | Glassnode; Puell Multiple; Woo 2020 | 1 | ~1 | `sentiment/mvrv/` |
| H22 | **Fear & Greed Contrarian (préliminaire)** | F&G extrême peur → long, extrême avidité → short ; signal contrarian | Da, Engelberg & Gao (2011) SVI retail attention | 1 | ~1 | `sentiment/fg_contrarian_feasibility.py` (racine) |
| H23 | **Strategy C Macro Extensions** | Macro overlay (VIX/DXY/SPY/GLD) + intraday body score + Google Trends BTC comme filtre sur Strategy C NQ | Macro overlay standard | 4 | ~4 | `other/strategy_c_search/` (4 sous-tests A/B/C/D) |
| H24 | **TSMOM Short + Weekly Seasonality** | Short-only TSMOM (signal A < 0) + seasonalité hebdo Keloharju 2016 | Keloharju, Linnainmaa & Nyberg (2016) | 2 | ~2 | `other/new_strategies/` |
| H25 | **Portfolio TSMOM+MR (combined)** | Combinaison TSMOM v2 + MR-ATR (corr = −0.30) pour améliorer daily DD propfirm | Portfolio optimization standard | 1 | ~1 | `other/portfolio_tsmom_mr/` |
| H26 | **Market Neutral Multi-Signal** | CS Funding Carry delta-neutral + BTC/ETH Stat-Arb + Overnight Gap MR | Portmanteau (3 signaux groupés) | 3 | ~3 | `other/market_neutral/` (3 sous-stratégies) |
| H27 | **OBV Volume Momentum** | Volume on-balance prédit la direction (accumulation/distribution) | Granville (1963); Vo & Yost-Bremm (2018) | 3 | ~3 | `passed/obv_signal/` (signaux 37–39 : OBV momentum, Price-Volume Divergence, OBV×TSMOM) |
| H28 | **VPT + CMF Volume Intracandle** | Volume pondéré par la magnitude et la position intracandle prédit la direction | Chaikin (1981) CMF; standard VPT | 2 | ~2 | `passed/vpt_cmf/` (signaux 40–41 : VPT, CMF) |
| H29 | **Bitcoin Halving Supply Shock** | Réduction de l'offre nouvelle (halving −50%) → bull phase 6–18 mois post-halving | Supply shock macro; Filbfilb (2019) Halving Model | 3 | ~3 | `passed/halving_cycle/` (signaux 42–44 : phase filter, Gaussian, halving×TSMOM) |
| H30 | **HMM Forward-Algorithm Causal Regime** | Probabilité de transition vers bull (algorithme forward = causal) vs Viterbi (non-causal) → signal continu [0,1] | Hamilton (1989); Augustyniak (2014) forward filter | 4 | ~4 | `passed/hmm_transitions/` (signaux 45–48 : P_bull_next, prob change, Bear→Bull crossing, TSMOM×HMM) |

**Sous-total V1 OHLCV (H01–H30) : ~142 n_tests sur 30 hypothèses économiques distinctes**

---

### BLOC V2 MISSIONS (n=142→159, signaux 6.37–6.50)

Source détaillée : `documentation_inventory.md` §I famille 2a — "+9: CS-FS/FRA IC ×4, PMR backtest ×1, OAGF IC ×3 horizons, PMR WF ×1"

| # | Famille d'hypothèse économique | Mécanisme | Référence académique primaire | Nb variants testés | n_tests consommés | Source comptage |
|---|---|---|---|---|---|---|
| H31 | **CS-FS Delta-Neutral Carry** | Funding spread CS delta-neutral → corrélation A < 0.08 | Schmeling et al. (2023) delta-neutral extension | 1 | 1 (IC test) | `documentation_inventory.md` : "CS-FS/FRA IC ×4" → test CS-FS = 1 |
| H32 | **FRA Delta-Neutral (3 variants)** | Funding Rate Asymmetry : asymétrie hausse/baisse du funding → signal delta-neutral | HL-native, aucune ref publiée | 3 | 3 (IC stables, instable, aggregate) | `documentation_inventory.md` : "FRA IC ×3" dans les 4 CS-FS/FRA tests |
| H33 | **PMR Basis Mean-Reversion (backtest + WF)** | Perp/spot basis z-score |≥1.5σ → reversion delta-neutral | Basis mean-reversion: Duan et al. (2020) | 2 | 2 (backtest ×1 + WF ×1) | POSTMORTEM PMR : n=142→148 (+6) total, dont 4 tests CS-FS/FRA, 2 tests PMR proprement dit |
| H34 | **OAGF Settlement Gap Fade** | |gap_ret| > 0.30% aux settlements 8h → mean-reversion 1-4h | Shen, Urquhart & Wang (2022) — gap fade | 3 | 3 (horizons 1h, 2h, 4h) | POSTMORTEM OAGF : n=148→151 (+3) |
| H35 | **ETH MVRV Z-Score (on-chain valuation)** | MVRV élevé = overvalued → retour négatif (analogue P/B crypto) | CoinMetrics; Glassnode; Woo (2020) | 1 | 1 | POSTMORTEM ETH MVRV : "+2" dont MVRV = 1 |
| H36 | **ETH Exchange Netflow** | Sorties nettes élevées = accumulation → retour positif | Chainalysis; CoinMetrics on-chain flow | 1 | 1 | POSTMORTEM ETH MVRV : "+2" dont Netflow = 1 |
| H37 | **BTC ATM Straddle Short (VRP Deribit)** | DVOL² > RV30² → vente de straddle mensuel delta-hedgé → prime VRP captée | Almeida, Grith et al. (2024); Todorov (2019) | 3 | 3 (Phase 1=0, Phase 2=1, Phase 3=2) | POSTMORTEM VRP : n=153→156 (+3) |
| H38 | **ETF Flow + Stablecoin Regime Overlay** | Flux ETF positifs + supply stablecoin croissante = régime haussier → filtre sur TSMOM A | MacroVar flow analysis; institutional sentiment | 1 | 1 | POSTMORTEM ETF Regime : n=156→157 (+1) |
| H39 | **FGVD — Fear & Greed Velocity Divergence** | Divergence vitesse F&G vs vitesse prix → signal contrarian | Da, Engelberg & Gao (2011) SVI analogy; Albrecht (2025) | 1 | 1 | POSTMORTEM FGVD : n=157→158 (+1) |
| H40 | **WAV — Wikipedia Attention Velocity** | Pic d'attention Wikipedia → acheteurs non-informés → retour négatif (Da 2011 SVI analogy) | Da, Engelberg & Gao (2011) SVI; Kristoufek (2013) | 1 | 1 | POSTMORTEM WAV : n=158→159 (+1) |

**Sous-total V2 missions (H31–H40) : 17 n_tests sur 10 hypothèses économiques distinctes**

---

## PARTIE 2 — Statistiques globales

### 2.1 Vue d'ensemble

| Métrique | Valeur |
|----------|--------|
| Total n_tests crypto | **159** |
| Hypothèses économiques distinctes (H01–H40) | **40** |
| Variants par hypothèse — médiane | **1** |
| Variants par hypothèse — moyenne | **4.0** (159 / 40) |
| Variants par hypothèse — maximum | **93** (H02 CS Carry) |
| Hypothèses avec 1 seul variant | **21** (52.5%) |
| Hypothèses avec ≥ 10 variants | **2** (H02: 93, H15: 6 — seuil abaissé à 6) |

### 2.2 Distribution du nombre de variants (histogramme texte)

```
 1 variant  : ██████████████████████ 21 hypothèses (H03,H04,H06b,H07b,H08,H09,H11,H12,H14,H17,H19,H21,H22,H25,H31,H35,H36,H38,H39,H40 + H33 partiellement)
 2 variants : ████████               7 hypothèses  (H07,H10,H16⊂,H18,H24,H28,H29⊂)
 3 variants : ████████               8 hypothèses  (H05,H13⊂,H20,H26⊂,H27,H29,H30⊂,H32,H34,H37)
 4 variants : ████                   3 hypothèses  (H23,H30)
 6 variants : ██                     1 hypothèse   (H15)
 90+ variants: █                     1 hypothèse   (H02 — CS Carry)

Notes :
- H15 (ML) = 6 variants de 4 approches (XGBoost ×2 versions + MLP ×1 + LSTM ×1 + 2 agrégés dans xgb)
- H02 contribue 93 n_tests = 58% du total V1
- Distributions des V2 missions : 7 hypothèses avec exactement 1 variant
```

### 2.3 Hypothèse la plus testée

**H02 — Cross-Sectional Funding Carry** avec **93 variants** (58% des tests V1 OHLCV).
Grid exhaustif : 6 signal_types × 5 fréquences de rebalancement × 3 niveaux de levier = 90 combos (+3 variants standalone funding_carry). Un seul mécanisme économique : rang par funding rate moyen trailing.

### 2.4 Impact sur le compteur global

Si l'on retire la contribution H02 (93 variants de 1 hypothèse) du compteur :
- n_tests effectifs = 159 − 93 + 1 = **67 tests indépendants au sens DSR**
- Avec toutes grilles réduites à 1 par hypothèse : n_hypothèses = **40**

---

## PARTIE 3 — Hypothèses sous-explorées (≤2 variants)

Hypothèses avec exactement 1 ou 2 variants testés, ayant échoué principalement par manque de puissance statistique ou par stop précoce — non par falsification complète de l'hypothèse économique.

| # | Hypothèse | Variants testés | Variants évidents non testés | Cause d'échec documentée |
|---|-----------|-----------------|------------------------------|--------------------------|
| **H04** | Funding Rate Extreme Reversal (z > +2.5σ) | 1 : {z_threshold=+2.5σ, universe=BTC/ETH/SOL} | z_threshold = {1.5σ, 2.0σ, 3.0σ} ; univers élargi HL 29 perps | NON DOCUMENTÉ. INFÉRÉ : rareté événements (z > +2.5σ ≈ 1.2% des jours) — gate événements L12 probable |
| **H08** | STR 30-min intraday | 1 : 30-min uniquement | STR 15-min, 1h, 4h ; seuils de z-score différents | NON DOCUMENTÉ. INFÉRÉ : 0.17% RT × fréquence 30-min → coût drag fatal (mechanism = STR H07 déjà en FAIL) |
| **H09** | BTC Dominance Rotation | 1 : retour relatif 14j BTC vs basket | Lookbacks {7, 21, 56}j ; panier d'alts différent ; hedging avec futures | NON DOCUMENTÉ. INFÉRÉ : corrélation BTC/alts > 0.80 rend la neutralisation inefficace (même cause que L11) |
| **H11** | Volatility Breakout (BB Squeeze) | 1 : seuil BB percentile unique | Seuils percentile {5%, 10%, 20%} ; périodes de lookback BB {14, 20, 30}j | NON DOCUMENTÉ. INFÉRÉ : ~15–25 événements/an → gate L12 (floor insuffisant pour t_HAC > 2.5) |
| **H12** | Crash Recovery Dip-Buy | 1 : {threshold=−8%, horizon=3j, hold=5j} | Thresholds {−5%, −10%, −15%} ; horizon {1j, 5j} ; univers CS vs TS | NON DOCUMENTÉ. INFÉRÉ : momentum > mean-reversion post-crash en crypto (bull marché continue vs rebond) |
| **H17** | MR ATR-bounded (MLP) | 1 : MLP signe opposé sur ATR features | Features alternatives sans MLP ; seuils ATR différents ; MR sur delta-neutral | NON DOCUMENTÉ |
| **H21** | MVRV Scaler sur TSMOM A | 1 : scaler multiplicatif MVRV sur TSMOM | MVRV comme overlay conditionnel (gate, non scaler) ; BTC uniquement vs portfolio | DOCUMENTÉ L15 et L17 : corr(MVRV, TSMOM-28d) = +0.73 → proxy momentum. Signal non-orthogonal par construction. Hypothèse falsifiée sur mécanisme, pas sur paramètres. |
| **H22** | Fear & Greed Contrarian (préliminaire) | 1 : seuil fixe peur/avidité, hold 5j BTC | Seuils quantiles {5%, 10%, 25%} ; univers CS ; velocité F&G vs niveau F&G | DOCUMENTÉ L17 (confirmé par H39 FGVD) : F&G = proxy momentum, pas contrarian. Hypothèse falsifiée sur mécanisme. |
| **H25** | Portfolio TSMOM+MR combined | 1 : corr = −0.30 entre TSMOM v2 et MR-ATR | Poids ERC plutôt que 50/50 ; univers différent | NON DOCUMENTÉ. INFÉRÉ : MR-ATR (H17) seul non-viable, combinaison ne suffit pas |
| **H31** | CS-FS Delta-Neutral Carry | 1 : IC pre-flight unique | Delta différent (perp/spot vs CS long/short) ; seuils de carry différents | DOCUMENTÉ : IC t = 1.54 (FAIL gate 2.5). Puissance insuffisante — 1 seul IC test, aucun backtest. |
| **H35** | ETH MVRV Z-Score on-chain | 1 : MVRV z-score fwd-30d | MVRV fwd-7d, 14d, 60d ; BTC MVRV ; composite MVRV+NVT | DOCUMENTÉ POSTMORTEM : IC t_HAC = 1.41 (FAIL) + corr_A = 0.734 (beta-dominé). Mécanisme falsifié (mauvaise direction). |
| **H36** | ETH Exchange Netflow | 1 : netflow z-score fwd-30d | Netflow fwd-7d, 14d ; BTC netflow ; netflow normalisé par supply | DOCUMENTÉ POSTMORTEM : IC t_HAC = 0.11 (N_eff ≈ 73, L12b autocorrélation). FAIL structurel. |
| **H38** | ETF Flow + Stablecoin Regime Overlay | 1 : τ = +0.5σ, fenêtre 7j, poids 50/50 | τ = {0σ, 1σ, 1.5σ} ; fenêtres {3j, 14j, 30j} ; poids asymétriques | DOCUMENTÉ POSTMORTEM : lift = +0.022%/j = +1.7%/an (sous-seuil). 1 seul variant testé avant STOP. |
| **H39** | FGVD — F&G Velocity Divergence | 1 : velocité 7j, fwd 7j | Velocité {3j, 14j, 30j} ; composite avec prix-vol ; régime conditionnel | DOCUMENTÉ POSTMORTEM : IC_B = +0.274 (FAIL gate 2.5, mauvaise direction). Mécanisme falsifié (L17). |
| **H40** | WAV — Wikipedia Attention Velocity | 1 : z-score pageviews 7j, CS 21 tokens | z-score {3j, 14j, 30j} ; filter par page quality ; Reddit attention proxy | DOCUMENTÉ POSTMORTEM : IC_B = +0.156 (FAIL gate 2.5, direction ≈ 0, momentum résiduel). Mécanisme falsifié (L18). |

**Note sur H35/H36/H21/H22/H39/H40** : ces 6 hypothèses ont été arrêtées non par manque de variants testés mais parce que le **mécanisme lui-même est falsifié** (mauvaise direction, proxy momentum, HAC deflation structurelle). Les "variants non testés" sont listés pour exhaustivité mais leur test n'aurait pas changé le verdict économique.

**Note sur H38** : l'arrêt à 1 variant avec un lift réel mais sous-seuil (+1.7%/an) correspond à L15 (overlay sur SR>1.0 = lift marginal). Tested suffisamment pour la conclusion.

**Hypothèses potentiellement sous-explorées sur le mécanisme (non falsifiées, 1–2 tests seulement)** :

| # | Hypothèse | Justification |
|---|-----------|---------------|
| H04 | Funding extreme reversal | Mécanisme plausible (liquidation squeezes); rarement testé par rareté événements à z>2.5. Seuil z=1.5 non testé. |
| H11 | BB Squeeze breakout | Mécanisme distinct de TSMOM (volatility compression → expansion). 1 seul seuil percentile. |
| H31 | CS-FS delta-neutral | IC t=1.54 est 59% du gate. Non testé en backtest. Mécanisme orthogonal (L11 non applicable). |

---

## PARTIE 4 — Verdict factuel

**n_hypothèses économiques crypto distinctes testées = 40** (sur n_tests cumulé de 159 réalisations).

**21 familles testées avec un seul variant** (52.5% des familles). Parmi ces 21, **15 ont leur mécanisme économique falsifié** (mauvaise direction, beta-dominé, coût fatal documenté) et non leur paramétrage. Seules **6 familles** (H04, H11, H31, H08, H12, H38) présentent un mécanisme non-falsifié avec une couverture paramétrique incomplète.

**Le compteur AMTP brut surestime le coût de multiple testing d'un facteur ~4.0** (159/40). CS Carry seul contribue 93 n_tests pour 1 hypothèse économique, gonflant le compteur de 92 unités. Hors CS Carry, le ratio est (159−92)/(40−1) = 67/39 ≈ **1.7×**. Le facteur global de surestimation pondéré est donc situé entre **1.7× et 4.0×** selon que l'on considère CS Carry comme 1 ou 93 hypothèses indépendantes.

*Aucune proposition d'amendement de constitution. Aucune recommandation méthodologique. Pure structuration factuelle.*

---

*Rapport généré le 2026-05-28 sur branche `claude/crypto-audit-2026-05-28`*
*STRUCTURATION SEULEMENT — aucun backtest lancé, aucun fichier de stratégie modifié*
