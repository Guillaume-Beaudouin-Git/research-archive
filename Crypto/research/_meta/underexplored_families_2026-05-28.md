# Familles Crypto Sous-Explorées — Fiches Factuelles — 2026-05-28

*Branche : `claude/crypto-audit-2026-05-28` | Investigateur : Claude Sonnet 4.6*
*Sources primaires : `archived_audit_2026-05-28.md`, `n_tests_restructure_2026-05-28.md`,
`audit_verification_2026-05-28.md`, POSTMORTEMs complets (PMR, OAGF, ETH MVRV+Netflow,
FGVD, WAV, ETF Regime, VRP Deribit), `documentation_inventory.md`, CLAUDE.md §Methodology*

---

## Méthode

21 familles d'hypothèses économiques identifiées comme sous-explorées (≤2 variants testés
chacune) dans `n_tests_restructure_2026-05-28.md`. Fiche standardisée pour chacune, à partir
des sources primaires uniquement. Informations non trouvables marquées **NON DOCUMENTÉ**.

Catégorisation factuelle par mode de clôture documenté :
- **Section A** : Mécanisme économique falsifié (6 familles) — H21, H22, H35, H36, H39, H40
- **Section B** : Signal statistiquement réel, coût fatal documenté (3 familles) — H33, H08, H03
- **Section C** : Puissance statistique insuffisante, mécanisme non-falsifié (6 familles) — H04, H09, H11, H12, H14, H06
- **Section D** : Partiellement testé, mécanisme intact (3 familles) — H31, H19, H38
- **Section E** : Résultats non documentés (3 familles) — H17, H25, H07

Coûts de référence : Binance perp taker = 0.17% RT (standard utilisé dans tous les backtests).
HL perp taker = 0.035% RT. HL maker rebate = −0.010% RT (earn).
Propfirm note globale : CLAUDE.md confirme "Propfirms do NOT accept crypto/delta-neutral." La
colonne Propr = NON pour toutes les 21 familles. Velotrade/HyroTrader non documentés dans
CLAUDE.md → À DÉTERMINER pour toutes.

---

## SECTION A — Mécanisme économique falsifié

*Ces 6 familles ont été arrêtées parce que le mécanisme lui-même est empiriquement falsifié
(mauvaise direction IC, proxy momentum, ou déflation HAC structurelle). Les variants listés
sont techniquement possibles mais ne changeraient pas le verdict économique.*

---

### Famille H21 — MVRV Z-Score Scaler (TSMOM A)

- **Mécanisme économique** : MVRV (Market Value / Realized Value) mesure la prime de la
  capitalisation boursière au-dessus du coût de la base installée. Valeur élevée → actif
  overvalued → signal baissier contrarian — appliqué comme scaler multiplicatif sur TSMOM A.
- **Référence académique principale** : Glassnode metric; Woo (2020) "Bitcoin On-chain
  Analytics"; Puell Multiple (dérivé analogique).
- **Variants déjà testés** :
  - Signal : MVRV_z comme scaler multiplicatif de Strategy A TSMOM | Univers : BTC/ETH/SOL |
    Fréquence : hebdomadaire (alignée Strategy A)
  - Cause d'échec documentée : **corr(MVRV, TSMOM-28d) = +0.734** — MVRV est un proxy
    momentum (monte avec le prix, indique continuation), non un signal contrarian. Scaler
    non-orthogonal par construction. Documenté L15 et L17 (POSTMORTEM ETH MVRV).
- **Variants alternatifs évidents NON testés** : AUCUN VARIANT MÉCANISTE ÉVIDENT — la
  corrélation MVRV/TSMOM est une propriété intrinsèque du mécanisme (MVRV monte avec les
  bull runs = idem TSMOM). Aucune transformation paramétrique n'élimine corr > 0.70.
- **Data requirements** : CoinMetrics Community (gratuit) — CapMVRVCur ETH/BTC disponible.
  Binance OHLCV Strategy A disponible. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily (hérite du profil DD de Strategy A en crypto)
  - Compatible Propr (3% daily) : NON (crypto exclu)
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (corr = 0.734 mesuré)
  - Justification : MVRV capte la même information directionnelle que TSMOM par construction.

---

### Famille H22 — Fear & Greed Contrarian (préliminaire)

- **Mécanisme économique** : Index Fear & Greed (0-100) capte l'état émotionnel du marché.
  Extrême peur → long (oversold), extrême avidité → short (overbought). Analogie Da et al.
  2011 SVI retail attention crypto.
- **Référence académique principale** : Da, Engelberg & Gao (2011) *RFS* "In Search of
  Attention" — analogie comportementale standard.
- **Variants déjà testés** :
  - Signal : F&G < seuil_peur → long BTC, F&G > seuil_avidité → short. Hold 5j |
    Univers : BTC TS | Fréquence : daily
  - Cause d'échec documentée : **L17** — F&G est un indicateur avancé dans la même
    direction que le prix (velocity IC = +0.085 à 4-32j, Albrecht 2025). F&G reflète les
    holders existants (signal de continuation), non les nouveaux acheteurs retail. Confirmé
    par H39 FGVD (même mécanisme, test plus rigoureux).
- **Variants alternatifs évidents NON testés** : AUCUN VARIANT MÉCANISTE ÉVIDENT — le
  mécanisme contrarian est structurellement faux pour cet indicateur en crypto. F&G velocity
  confirme direction momentum (L17). Seuils différents ne changeront pas la direction d'IC.
- **Data requirements** : F&G archivé `archived/other/fgvd_h1/data/fg_raw.parquet` (2018-2026).
  **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily (long-only BTC sur signal journalier)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (F&G = momentum indicator → corrèle avec direction A)
  - Justification : F&G monte en bull run → même signal directionnel que TSMOM.

---

### Famille H35 — ETH MVRV Z-Score (on-chain valuation)

- **Mécanisme économique** : MVRV z-score mesure l'écart de la capitalisation boursière ETH
  au-dessus de la valeur réalisée. Valeur élevée → signal de vente (analogue P/B en equity :
  overvalued → mean-reversion attendue à moyen terme).
- **Référence académique principale** : CoinMetrics; Glassnode; Woo (2020); analogie
  Fama-French P/B ratio.
- **Variants déjà testés** :
  - Signal : mvrv_z = (CapMVRVCur − MA_365d) / std_365d → IC fwd-30d ETH |
    Période : 2016-2026 (~488 weekly obs, ~3795 daily)
  - Résultats : IC fwd-30d = +0.113, t_HAC = **1.41** (FAIL gate 2.5). Direction
    **POSITIVE** (MVRV monte avec prix = momentum, non MR). corr_A = **0.734** → β-dominé.
  - Cause d'échec documentée : MVRV = proxy TSMOM pour ETH. IC positif = continuation de
    tendance, pas reversal. (POSTMORTEM ETH MVRV complet, n=151→153).
- **Variants alternatifs évidents NON testés** : Lookbacks {7d, 14d, 60d}, BTC MVRV,
  composite MVRV+NVT. La cause d'échec est la **direction** (MVRV = momentum), non le
  paramétrage. Variants techniques disponibles mais résultat économique inchangé.
- **Data requirements** : CoinMetrics Community API — CapMVRVCur ETH/BTC gratuit.
  Archivé `archived/other/eth_mvrv_netflow/data/`. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily (long-only sur signal mensuel)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (corr = 0.734 mesuré)
  - Justification : MVRV = proxy TSMOM par construction (monte en bull run).

---

### Famille H36 — ETH Exchange Netflow

- **Mécanisme économique** : Sorties nettes des exchanges → "accumulation" par les holders →
  signal haussier. Entrées nettes → distribution → signal baissier. Proxy du flow
  institutionnel d'accumulation/distribution.
- **Référence académique principale** : Chainalysis on-chain analytics; CoinMetrics;
  Shu & Urquhart (2022) crypto microstructure flow.
- **Variants déjà testés** :
  - Signal : net_z = ((FlowOutExUSD − FlowInExUSD) − MA_90d) / std_90d → IC fwd-30d ETH |
    Période : 2016-2026 (~3398 daily obs)
  - Résultats : IC naïf t = 2.58 (N=3398) → HAC(lag=4) t = **0.11**. N_eff ≈ 73.
  - Cause d'échec documentée : **L12b** — régimes persistants de flow (accumulation dure
    6-18 mois) → autocorrélation déflate t massivement (3398 → 73 effective). STRUCTUREL.
- **Variants alternatifs évidents NON testés** : Horizons fwd {7d, 14d}, BTC netflow, netflow
  normalisé par supply. L12b est structurel : la persistence des régimes de flow (demi-vie
  >> 30j) signifie que toute fenêtre ≥ quelques semaines sera déflatée par HAC. Seule une
  fenêtre très courte (1-3j) pourrait échapper mais le mécanisme d'accumulation est
  fondamentalement long-terme (demi-vie empirique 6-18 mois).
- **Data requirements** : CoinMetrics Community — FlowOutExUSD, FlowInExUSD ETH.
  Archivé `archived/other/eth_mvrv_netflow/data/`. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily (long-only sur signal mensuel)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (signal long-only ETH corrèle avec TSMOM)
  - Justification : long-only sur signal non-orthogonal (corr = 0.512 mesuré).

---

### Famille H39 — FGVD (Fear & Greed Velocity Divergence)

- **Mécanisme économique** : Divergence entre la vitesse du sentiment F&G et la vitesse du
  prix → signal contrarian. Si sentiment monte plus vite que prix → prix va retomber (la
  réalité "rattrapera" le sentiment).
- **Référence académique principale** : Da, Engelberg & Gao (2011) *RFS*; Albrecht (2025)
  "F&G velocity as momentum leading indicator."
- **Variants déjà testés** :
  - Signal : FGVD = F&G_velocity_7d − price_velocity_7d → IC fwd-7d BTC |
    3028 obs 2018-2026
  - Résultats : IC_B (F&G velocity seul) = +0.0085, t_HAC = +0.274 — direction **ERRONÉE**
    (positive = momentum, non contrarian). Gate pré-enregistrée D4 déclenche : "si IC_B > 0
    → mécanisme inversé → STOP."
  - Cause d'échec documentée : **L17** — F&G velocity = indicateur avancé momentum (Albrecht
    2025 : IC +0.085 à 4-32j). F&G monte avant le prix (holders anticipent = signal
    directionnel), non après. Mécanisme Da 2011 ne se transfère pas du SVI equity au crypto.
- **Variants alternatifs évidents NON testés** : Velocité {3j, 14j, 30j}, composite prix-vol,
  régime conditionnel. **Tous inutiles** : le mécanisme contrarian est faux pour F&G velocity
  (L17). La direction de l'IC sera positive quel que soit le paramétrage.
- **Data requirements** : Archivé `archived/other/fgvd_h1/data/merged.parquet` (2018-2026,
  3028 obs). **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : NON DOCUMENTÉ (backtest non atteint — stop au pre-flight IC)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (F&G velocity = momentum indicator)
  - Note : corr(FGVD, TSMOM-28d) = −0.247 mesuré (signal orthogonal), mais IC direction
    positive → allié momentum en pratique.

---

### Famille H40 — WAV (Wikipedia Attention Velocity)

- **Mécanisme économique** : Pic d'attention Wikipedia sur un actif crypto → afflux d'acheteurs
  non-informés → retour négatif à court terme (Da 2011 SVI : attention retail → demande
  spéculative → reversal post-attention).
- **Référence académique principale** : Da, Engelberg & Gao (2011) *RFS*; Kristoufek (2013)
  "Bitcoin meets Google Trends and Wikipedia."
- **Variants déjà testés** :
  - Signal : attention_z = z-score(pageviews_7d_rolling), CS 21 tokens → IC fwd-7d |
    3063 dates 2018-2026
  - Résultats : IC_B (WAV seul) = +0.00158, t_HAC = +0.156 — IC ≈ **0** (statistiquement
    nul), légère tilt positive (momentum résiduel). Gate D4 déclenche.
  - Cause d'échec documentée : **L18** — Wikipedia pour crypto = curiosité informationnelle
    (recherche APRÈS que le prix a monté = "qu'est-ce que c'est ?"), non vecteur d'achat de
    nouveaux investisseurs. Da 2011 SVI equity ≠ Wikipedia crypto (médium de découverte :
    Twitter/Reddit pour crypto). IC ≈ 0 statistiquement.
- **Variants alternatifs évidents NON testés** : z-score {3j, 14j}, filter par qualité de page
  Wikipedia, Reddit attention proxy. **Inutiles** : IC_B ≈ 0 (absence totale d'edge, pas
  d'inversion de direction), mécanisme d'attention Wikipedia→acheteurs falsifié pour crypto.
- **Data requirements** : Archivé `archived/other/wav_h3/data/wiki/{TOKEN}.parquet`
  (2018-2026, 21 tokens). **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : NON DOCUMENTÉ (backtest non atteint)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : NEUTRE (corr(attention_z, TSMOM-28d) = −0.022 mesuré)
  - Justification : IC ≈ 0 → signal sans information directionnelle.

---

## SECTION B — Signal statistiquement réel, coût fatal documenté

*Ces 3 familles ont un signal économiquement réel (IC ou mécanisme confirmé par IC pre-flight)
mais ont été arrêtées par une structure de coûts incompatible avec le modèle de coût utilisé.
Les variants non testés concernent l'exécution ou la fréquence d'événements.*

---

### Famille H33 — PMR Basis Mean-Reversion ★ Signal réel (IC t=2.86)

- **Mécanisme économique** : Le spread perp/spot (basis) tend à réverter vers sa moyenne
  historique. Un basis élevé (perp premium excessive) signale une prime de liquidité temporaire
  → capital d'arbitrage la comprime. Mécanisme : short perp + long spot (delta-neutral) quand
  basis z > +1.5σ, attendre retour à la moyenne.
- **Référence académique principale** : Duan et al. (2020) perpetual swaps basis; Shu &
  Urquhart (2022) crypto microstructure; Gatev, Goetzmann & Rouwenhorst (2006) pairs trading.
- **Variants déjà testés** :
  - Signal : `basis_z = z-score(perp/spot − 1, 90d)`. Entry |basis_z| ≥ 1.5σ → fade.
    Exit : z→0 ou 7j | 29 coins Binance | Juin 2023 – Mai 2026 | Coût : 0.17% RT (taker)
  - Résultats IC : t_HAC = **−2.86** (PASS ✓) à horizon 3j. Signal statistiquement réel.
  - Résultats backtest : Sharpe = **−0.55**, MaxDD = **−65%**, WF = **0/2 folds**
  - Cause d'échec documentée : **912 événements/an** (12.6% des coin-days à |z| ≥ 1.5σ) ×
    0.17% RT = **178%/an** de coût drag vs ~16-20%/an gross. L12 event-count ceiling.
- **Variants alternatifs évidents NON testés** :
  - **Exécution HL maker (limit orders)** : HL maker rebate = −0.010% RT (earn). Au maker :
    912 × 2 × (−0.010%) = −18.2%/an earned → net ≈ +34-38%/an (16-20% gross + 18% rebate).
    Dimension non testée car backtest utilisait 0.17% Binance taker comme proxy.
    Risque clé : fill rate incertain pour orders contra-tendance sur basis extrême (adverse
    selection). | Difficulté : **HIGH** (infrastructure HL native + fill-rate uncertain)
  - **Funding earn pendant hold** : en shortant un perp avec basis > 0, on REÇOIT le funding
    rate (shorts reçoivent quand funding est positif). À 0.5%/semaine funding moyen ×
    7j de hold = +0.5%/trade de revenus additionnels. Sur 912 events × 0.5%/trade ≈ +456%/an
    adicional. Non comptabilisé dans le backtest. | Difficulté : **MED** (modélisation du
    funding dans le P&L de la stratégie)
  - **Threshold z > 3.0σ** : réduction d'événements ~95% → ~45/an. Gross ≈ 0.8%/an.
    Cost @ HL taker : 45 × 0.07% = 3.1%/an → net négatif même au taker HL. N_events < gate
    L12 minimum. | Difficulté : **LOW**
  - **PMR comme EXIT signal** pour Strategy A/C (non standalone) : basis_z ≥ 2.0σ → fermer
    long directionnels. Réutilisation du signal dans un rôle non-standalone. | Difficulté : **MED**
- **Data requirements** : Binance perp 1h (proxy, disponible). HL native candleSnapshot
  disponible depuis ~Oct 2025 seulement (~7 mois d'historique à la date d'audit). **Partiel**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : MaxDD = −65% à 0.17% taker. Théoriquement ≤3% daily si maker +
    funding combinés et vol-targeted.
  - Compatible Propr (3% daily) : NON (crypto exclu)
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : NÉGATIVE (corr_A = 0.18 mesuré, delta-neutral élimine beta)
  - Justification : delta-neutral par construction (short perp + long spot) → beta ≈ 0.

---

### Famille H08 — STR 30-min Intraday Reversal

- **Mécanisme économique** : Mean-reversion cross-sectionnel à très court terme sur barres
  30-min. Les pires performers récents sur 30-min tendent à rebondir (overreaction intraday,
  liquidations forcées, bid-ask bounce).
- **Référence académique principale** : Zaremba (2021) *JBF* "Crypto CS momentum/reversal";
  Grundy & Martin (2001) *RFS* CS reversal equity; Liu et al. (2021) crypto microstructure.
- **Variants déjà testés** :
  - Signal : STR cross-sectionnel sur barres 30-min | Univers : **NON DOCUMENTÉ** |
    Fréquence : 30-min | Résultats : **NON DOCUMENTÉ** (code seul)
  - Cause d'échec : **NON DOCUMENTÉ** (inférée) : 0.17% RT sur fréquence 30-min = coût
    inacceptable. Move typique 30-min ≈ 0.3-0.5% → gross margin avant coût ≈ 0.10-0.20%
    → négatif net de 0.17% taker.
- **Variants alternatifs évidents NON testés** :
  - **STR 1h bars** : même mécanisme, coût × 2 amorti. Au HL taker (0.035%) et 1h STR,
    move typique ≈ 0.3-0.6% → net potentiellement > 0 si IC t > 2.5. | Difficulté : **LOW**
  - **STR 4h bars** : coût encore amorti, signal plus net (moins de noise). H10 ORB Crypto
    a testé des structures 4h → chevauchement partiel. | Difficulté : **LOW**
  - **Delta-neutral STR** : long loser + short winner → résout β-dominance mais double le
    coût → viabilité conditionnelle à HL maker. | Difficulté : **MED**
- **Data requirements** : HL candleSnapshot 30-min (disponible uniquement depuis ~Oct 2025,
  ~7 mois). Binance OHLCV 1h (disponible, proxy). **Partiel (historique court)**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily (long-only haute fréquence crypto)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : NÉGATIVE (reversal vs momentum = anti-corrélé en principe)
  - Note : si long-only domine (pas vraiment delta-neutral), résidu beta POSITIF.

---

### Famille H03 — Funding Rate Momentum

- **Mécanisme économique** : La tendance haussière récente du funding rate (coût de détention
  des longs en hausse) prédit la continuation de la demande pour l'exposition longue → signal
  momentum sur le carry. Analogue du momentum de rendement obligataire en taux.
- **Référence académique principale** : Schmeling, Schrimpf & Todorov (2023) BIS WP 1087
  "Crypto Carry" — variation sur le momentum des taux de portage.
- **Variants déjà testés** :
  - Signal : `funding_trend[T] = mean_7d[T-1] − mean_14d[T-8]`, z-scoré 60j rolling.
    Long BTC quand z > +0.5 | Univers : BTC uniquement (TS) | Fréquence : hebdomadaire |
    Signal 29 | Résultats : **NON DOCUMENTÉ** (code seul)
  - Cause d'échec : NON DOCUMENTÉ (inférée) : IC insuffisant ou proxy TSMOM (funding
    momentum et prix-momentum corrèlent dans les bull runs).
- **Variants alternatifs évidents NON testés** :
  - **Univers HL multi-asset CS** : ranking par funding momentum sur 29-185 perps HL (au
    lieu de BTC uniquement). Résout β-dominance si delta-neutral exécuté. | Difficulté : **LOW**
  - **Horizons {mean_3d − mean_7d, mean_14d − mean_28d}** : signal plus réactif ou plus lent.
    | Difficulté : **LOW**
  - **Delta-neutral** : long funding momentum fort, short funding momentum faible (CS L/S)
    → résout β-dominance + orthogonalise avec TSMOM. | Difficulté : **MED**
- **Data requirements** : HL funding 185 symbols 2023-2026 (`data/funding_carry/`).
  **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily (long-only BTC sur signal hebdo)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (funding momentum corrèle avec prix-momentum)
  - Justification : même régime bull/bear → TSMOM et funding momentum évoluent ensemble.

---

## SECTION C — Puissance statistique insuffisante, mécanisme non-falsifié

*Ces 6 familles ont échoué par manque d'événements, univers trop petit, ou arrêt au pre-flight.
Le mécanisme économique n'est pas falsifié — l'évidence est insuffisante dans les configurations
testées.*

---

### Famille H04 — Funding Rate Extreme Reversal

- **Mécanisme économique** : Funding rate extrêmement élevé (z > +2.5σ) = positions longues
  surconcentrées (crowded longs). Résolution brutale (forced unwind, short squeeze déclenché
  par margin calls) → retour rapide du funding vers la moyenne → signal SHORT.
- **Référence académique principale** : Carry mean-reversion standard; Lou, Polk & Skouras
  (2019) *RFS* "Crowding and Factor Returns"; Koijen et al. (2018) carry cross-asset.
- **Variants déjà testés** :
  - Signal : short si z_funding_60d > +2.5σ, long si z < −2.0σ | Univers : BTC/ETH/SOL
    (Binance) | Fréquence : daily | Signal 35 | Résultats : **NON DOCUMENTÉ** (code seul)
  - Cause d'échec : NON DOCUMENTÉ (inférée) : z > +2.5σ ≈ 1.2% des jours × 3 assets =
    **~13 events/an** — en-dessous du gate L12 ≥18/an. Puissance statistique insuffisante.
- **Variants alternatifs évidents NON testés** :
  - **Univers HL 29-185 perps au lieu de 3** : à z > +2.5σ, ~4.5/asset/an × 29 perps =
    130 events/an → puissance acceptable pour IC pre-flight. Données disponibles.
    | Difficulté : **LOW**
  - **Threshold z > +2.0σ** (moins extrême) : ~4.55% des jours × 29 perps × 365 =
    481 events/an → test IC avec bonne puissance. Cost gate sera contraignant. | Difficulté : **LOW**
  - **CS long/short** : long asset funding le plus négatif + short asset funding le plus
    positif (CS L/S) → delta-neutral, résout β-dominance L11. | Difficulté : **MED**
  - **HL taker cost model** : à 0.035% RT (vs 0.17% Binance), cost drag divisé 4.9× pour
    un test de viabilité économique. | Difficulté : **LOW** (paramètre)
- **Data requirements** : HL funding 185 symbols 2023-2026 (`data/funding_carry/`).
  **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : ≤3% daily probable (signal rare, positions de petite taille)
  - Compatible Propr (3% daily) : NON (crypto exclu)
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : NÉGATIVE (signal SHORT quand funding extrême = contre-tendance)
  - Justification : funding extrême = bull market avancé → TSMOM signal fort → H04 SHORT
    = opposition directe à Strategy A.

---

### Famille H09 — BTC Dominance Rotation

- **Mécanisme économique** : Le retour relatif de BTC vs panier d'alts prédit la "saison."
  BTC surperformance relative → momentum BTC ; alts surperformance → alt season. Signal
  market-neutral sur la rotation BTC/alts dans le cycle.
- **Référence académique principale** : NON DOCUMENTÉ (mécanisme observé empiriquement,
  aucun papier académique identifié dans les scripts archivés).
- **Variants déjà testés** :
  - Signal : retour relatif 14j BTC vs basket alts → positions market-neutral | Univers :
    BTC vs basket | Résultats : **NON DOCUMENTÉ** (code seul)
  - Cause d'échec : NON DOCUMENTÉ (inférée) : corrélation BTC/alts > 0.80 → neutralisation
    inefficace (L11 indirect). Fréquence de rotation ≈ 4-6 fois/an → power insuffisant.
- **Variants alternatifs évidents NON testés** :
  - **Lookbacks {7j, 21j, 56j}** avec univers élargi HL : adresse le lookback optimal.
    | Difficulté : **LOW**
  - **Beta-hedge explicite** (spread BTC − beta × alts) : mesure le spread résiduel plutôt
    que le retour absolu. Adresse : covariance résiduelle. | Difficulté : **MED**
  - **Conditioning sur régime de volatilité** : rotation plus marquée en régimes de faible
    vol crypto. | Difficulté : **MED**
- **Data requirements** : Binance OHLCV daily. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : ≤5% daily si market-neutral bien exécuté
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (BTC leg longue corrèle avec TSMOM A si beta résiduel)
  - Note : si véritablement market-neutral → NEUTRE.

---

### Famille H11 — Volatility Breakout (BB Squeeze)

- **Mécanisme économique** : Contraction de la volatilité (Bollinger Band width < percentile
  seuil) → énergie cinétique accumulée → breakout directionnel amplifié à la cassure du range.
  Mécanisme de volatility clustering → expansion.
- **Référence académique principale** : Bollinger (1992) "Bollinger on Bollinger Bands";
  Cont & Das (2022) volatility clustering in crypto.
- **Variants déjà testés** :
  - Signal : long/short si BB_width < percentile → breakout | Univers : NON DOCUMENTÉ |
    Fréquence : NON DOCUMENTÉ (inférée daily) | Résultats : **NON DOCUMENTÉ** (code seul)
  - Cause d'échec : NON DOCUMENTÉ (inférée) : ~15-25 événements/an → t_HAC < 2.5 avec N
    insuffisant. L12 event-count floor.
- **Variants alternatifs évidents NON testés** :
  - **Percentile plus bas** {5%, 10%, 20%} : augmente la fréquence → meilleure puissance
    statistique. Adresse : L12 floor. | Difficulté : **LOW**
  - **4h bars** (au lieu de daily) : fréquence × 6 → ~90-150 events/an → puissance viable.
    Coût drag = 100 × 0.17% = 17%/an → IC doit être fort. | Difficulté : **LOW**
  - **Multi-asset CS** (long breakout le plus net, short breakout le plus négatif) → résout
    β-dominance L11. | Difficulté : **MED**
  - **Confirmation RVOL** : RVOL ≥ 1.5 au squeeze → filtre les faux breakouts. | Difficulté : **LOW**
- **Data requirements** : Binance OHLCV daily/4h. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily (directional breakout crypto)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (breakout directionnel suit la tendance = corrèle TSMOM)
  - Justification : BB Squeeze breakout capture momentum court terme.

---

### Famille H12 — Crash Recovery Dip-Buy

- **Mécanisme économique** : Baisse brutale −8% en 3j → liquidations forcées → overshoot →
  rebond de retour à la moyenne. Mécanisme de liquidity crunch : bid reappears post-forced-sell.
- **Référence académique principale** : Barberis, Shleifer & Vishny (1998) *JFE* overreaction;
  Jegadeesh (1990) short-term equity reversal; DeBondt & Thaler (1985) overreaction.
- **Variants déjà testés** :
  - Signal : chute ≥ −8% en 3j → achat. Hold 5j | Univers : BTC/ETH/SOL/BNB/AVAX |
    Fréquence : daily (event-driven) | Signal 34 | Période : 2018-2026 |
    Résultats : **NON DOCUMENTÉ** (code seul)
  - Cause d'échec : NON DOCUMENTÉ (inférée) : en crypto, momentum > mean-reversion
    post-crash sur 2018-2026 (bear markets s'approfondissent, bull markets se poursuivent).
    Absence de "V-shape" fiable.
- **Variants alternatifs évidents NON testés** :
  - **Threshold {−5%, −10%, −15%}** : calibrage du "crash signal." | Difficulté : **LOW**
  - **Conditioning sur régime** : déclencher seulement si VIX_crypto > percentile 90
    (vraie liquidation) vs simple baisse dans bull market. | Difficulté : **MED**
  - **Hold {1j, 3j}** : si rebond est ultra-court terme. | Difficulté : **LOW**
- **Data requirements** : Binance OHLCV daily 2018-2026. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily (long crypto après crash = exposition maximale)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (achat dips crypto = exposition longue)
  - Note : timing contraire de TSMOM (qui serait short au crash) → résidu POSITIF via beta.

---

### Famille H14 — USDT Quote Volume Proxy Flow

- **Mécanisme économique** : Volume de trading dénominé en USDT mesure le flux de capital
  retail entrant. Pic de volume USDT = nouvelle demande non-informée → continuation de
  tendance à court terme (momentum retail flow).
- **Référence académique principale** : Chi, Chu & Hao (2025) SSRN "USDT quote volume as
  retail attention proxy"; Kumar & Lee (2006) retail investor sentiment.
- **Variants déjà testés** :
  - Signal : volume USDT z-scoré vs baseline 30j. Long BTC+ETH quand z > 0 |
    Univers : 5 paires Binance | Fréquence : hebdomadaire | Période : 2022-2026 |
    Résultats : **NON DOCUMENTÉ** (code seul)
  - Cause d'échec : NON DOCUMENTÉ (inférée) : IC insuffisant ou proxy TSMOM (volume et prix
    montent ensemble en bull run).
- **Variants alternatifs évidents NON testés** :
  - **CS ranking** par z-score volume sur 29-185 perps HL : résout β-dominance (L/S).
    | Difficulté : **MED**
  - **Volume/OI ratio** (normalisation par open interest) → mesure flux marginal réel.
    OI data disponible sur HL. | Difficulté : **MED**
  - **Horizon {3j, 1j}** (au lieu de hebdomadaire) : signal plus réactif. | Difficulté : **LOW**
- **Data requirements** : Binance OHLCV (volume inclus). HL OI data disponible. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily (long-only BTC+ETH)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (retail volume momentum → même direction que TSMOM)
  - Justification : volume et prix montent ensemble → proxy momentum.

---

### Famille H06 — CS Price Momentum (Donchian + Cross Breakout)

- **Mécanisme économique** : Breakout de prix sur nouveau high N-jours (Donchian channel) ou
  cassure d'un niveau CS (Robot Wealth methodology) → signal de continuation de tendance
  cross-sectionnel. Long assets en breakout, short assets en breakdown.
- **Référence académique principale** : Drogen, Hoffstein & Otte (2023) SSRN "CS momentum in
  crypto"; Donchian (1960) channel breakout.
- **Variants déjà testés** (2 variants) :
  - V1 : Cross Breakout CS (Robot Wealth, signal 32) | V2 : Donchian Breakout |
    Résultats des deux : **NON DOCUMENTÉ** (code seul)
  - Cause d'échec : NON DOCUMENTÉ (inférée) : β-dominance L11 — long-only CS crypto =
    beta proxy indépendamment du signal IC. CS Carry best IS Sharpe = 0.314 → <0.7 gate.
- **Variants alternatifs évidents NON testés** :
  - **Delta-neutral** (long top-20% breakout + short bottom-20%) : résout β-dominance L11.
    Principal blocage documenté. | Difficulté : **MED**
  - **Lookback Donchian {10j, 20j, 50j}** : horizon optimal. | Difficulté : **LOW**
  - **Confirmation RVOL** : ne déclencher que si volume confirme le breakout. | Difficulté : **LOW**
- **Data requirements** : Binance OHLCV daily. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily (directional CS crypto)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (CS momentum long-only → même beta exposure que TSMOM)
  - Justification documentée : L11 — corr_A ≥ 0.80 inévitable en long-only CS crypto.

---

## SECTION D — Partiellement testé, mécanisme intact

*Ces 3 familles ont été arrêtées avant d'atteindre un backtest complet, ou ont un résultat
borderline sans invalidation du mécanisme. Le mécanisme économique n'est pas falsifié et les
données nécessaires sont disponibles.*

---

### Famille H31 — CS-FS Delta-Neutral Carry ★ IC = 1.54 (59% du gate)

- **Mécanisme économique** : Classement cross-sectionnel par funding spread (CS-FS) : long
  les assets à funding le plus faible, short les assets à funding le plus élevé → portage
  différentiel capturé de façon delta-neutral. Structure économique analogue à Strategy B
  (delta-neutral HL carry sur paires sélectionnées).
- **Référence académique principale** : Schmeling, Schrimpf & Todorov (2023) BIS WP 1087
  "Crypto Carry" — extension delta-neutral; Koijen et al. (2018) carry cross-asset.
- **Variants déjà testés** :
  - Signal : ranking CS par funding spread → delta-neutral | **1 seul IC pre-flight** |
    Résultat IC : t_HAC = **1.54** (FAIL gate 2.5 — mais 59% du gate, non-conclusif)
  - Aucun backtest. Aucun WF. Arrêt au pre-flight par insuffisance de puissance d'IC.
    Mécanisme non-falsifié.
- **Variants alternatifs évidents NON testés** :
  - **Backtest sur 2023-2026** (étape non franchie) : HL funding 185 symbols disponible,
    IC t=1.54 non-conclusif (ni PASS ni falsifié). Le backtest constituerait le test naturel
    suivant. | Difficulté : **MED** (code CS-FS dans archived — structure PMR réutilisable)
  - **Lookback funding** {3j, 7j, 14j, 30j} : adresse l'horizon optimal du spread CS.
    | Difficulté : **LOW**
  - **Universe size {29, 50, 100, 185 perps}** : plus grand univers → meilleur CS L/S
    spread potentiel. Données HL disponibles. | Difficulté : **LOW**
  - **HL taker (0.035%) vs Binance (0.17%)** : coût drag réduit 4.9× → seuil de viabilité
    économique plus bas. | Difficulté : **LOW** (paramètre)
- **Data requirements** : HL funding 185 symbols 2023-2026 (`data/funding_carry/`).
  **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : ≤3% daily probable si delta-neutral proprement exécuté
  - Compatible Propr (3% daily) : NON (crypto exclu)
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : NEUTRE (delta-neutral → beta ≈ 0; CLAUDE.md cite corr_A ≈ 0.08
    pour CS-FS context; analogie corr_A = 0.18 pour PMR delta-neutral mesuré)
  - Justification : delta-neutral élimine la composante beta (L11). Orthogonalité confirmée
    pour la structure générale de carry delta-neutral.

---

### Famille H19 — TSMOM L/S Combined Portfolio

- **Mécanisme économique** : TSMOM long-only (10 assets) + short sélectionné (4 alts faibles)
  → portfolio quasi-market-neutral réduisant la β-dominance. Objectif : réduire le daily DD
  pour compatibilité propfirm crypto.
- **Référence académique principale** : Moskowitz, Ooi & Pedersen (2012) *JF* "Time-Series
  Momentum" — extension L/S; Markowitz (1952) diversification.
- **Variants déjà testés** (1 variant) :
  - Signal : TSMOM long 10 assets + short SOL/LINK/BCH/OP (4 fixes) |
    Résultats : Sharpe OOS = **0.76** (borderline RESEARCH_PASS ≥0.7),
    MaxDD journalier = **−11.9%** (excès vs propfirm 3% daily)
  - Cause d'échec : Sharpe borderline, MaxDD journalier incompatible avec propfirm crypto.
- **Variants alternatifs évidents NON testés** :
  - **Short leg dynamique** : short les N assets avec signal TSMOM le plus négatif (au lieu
    de 4 assets fixes). Adresse : sélection sous-optimale du short. | Difficulté : **MED**
  - **Vol-targeting à 10% annualisé** : réduit le sizing → MaxDD journalier ≈ 3%.
    Adresse : MaxDD propfirm. | Difficulté : **MED**
  - **N long/short asymétrique {5L/5S, 10L/10S}** au lieu de 10L/4S → neutralisation
    beta améliorée. | Difficulté : **LOW**
  - **Universe HL élargi** (N ≥ 30 pour CS L11 gate) : plus d'assets → IC CS plus stable.
    | Difficulté : **MED**
- **Data requirements** : Binance OHLCV + HL funding. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : ≤5% daily si vol-targeted (MaxDD journalier mesuré −11.9% à sizing actuel)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (les 10 longs corrèlent avec Strategy A)
  - Justification : le short leg partiel (4/10) n'élimine pas le beta résiduel dominant.

---

### Famille H38 — ETF Flow + Stablecoin Regime Overlay

- **Mécanisme économique** : Flux nets positifs des ETF Bitcoin + croissance de la supply
  stablecoin → signal institutionnel de demande entrant → régime favorable pour TSMOM.
  Overlay conditionnel : activer Strategy A uniquement en régime institutionnel haussier.
- **Référence académique principale** : MacroVar institutional flow analysis; Jiang, Li &
  Wang (2022) institutional sentiment analogue.
- **Variants déjà testés** :
  - Signal : `regime = 0.5 × flow_z + 0.5 × stable_z`, activer Strategy A si regime > +0.5σ |
    Fenêtre : 7j | τ = +0.5σ | Période : 2024-01-12 → 2026-05-22 (ETF post-approbation SEC)
  - Résultats : Δ alpha = +0.022%/j = **+1.7%/an** (lift réel mais sous-seuil). t_HAC = −0.17.
    Temps en marché 31.4%.
  - Cause d'échec documentée : **L15** — overlay sur SR>1.0 = lift marginal par construction.
    Fenêtre courte (~2.3 ans, peu de cycles complets). (POSTMORTEM complet archivé.)
- **Variants alternatifs évidents NON testés** :
  - **τ = {1.0σ, 1.5σ}** : temps en marché ~16-31% → lift concentré sur régimes les plus
    forts. | Difficulté : **LOW**
  - **Fenêtres {3j, 14j, 30j}** pour le z-score regime. | Difficulté : **LOW**
  - **Poids asymétriques** flow_z vs stable_z : si ETF flows plus prédictifs que stablecoin
    supply. | Difficulté : **LOW**
  - **Extension temporelle** 2026-2028 : avec 4-5 ans de post-ETF data, cycles représentés.
    Adresse : manque de puissance statistique. | Difficulté : N/A (temps)
- **Data requirements** : Archivé `archived/etf_regime_overlay/data/` (ETF flows BitBO
  2024-2026, stablecoin DeFiLlama 2023-2026). **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : idem Strategy A (~5% daily en burst crypto)
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (overlay structurel sur Strategy A)
  - Justification : H38 est un filtre sur A, corrélation structurelle totale avec A.

---

## SECTION E — Résultats non documentés

*Ces 3 familles n'ont que du code source disponible. La cause d'échec est inférée.*

---

### Famille H17 — MR ATR-bounded (MLP)

- **Mécanisme économique** : Mean-reversion conditionnée sur le range ATR. Quand le range
  ATR récent est élevé (volatilité excessive), les prix ont overshot → signal de retour.
  MLP utilisé pour apprendre la relation non-linéaire entre features ATR et futur retour.
- **Référence académique principale** : Wilder (1978) ATR; Jegadeesh (1990) short-term
  reversal; Lo, Mamaysky & Wang (2000) technical patterns via neural networks.
- **Variants déjà testés** :
  - Signal : signe opposé des features ATR via MLP | Univers : **NON DOCUMENTÉ** |
    Résultats : **NON DOCUMENTÉ** (code seul)
  - Cause d'échec : NON DOCUMENTÉ. Inférée : OOS dégradation ML ou IC t < 2.5 sur features
    ATR. Possible β-dominance si long-only.
- **Variants alternatifs évidents NON testés** :
  - **ATR pur sans MLP** : z-score(price / ATR) comme signal direct de MR → évite overfitting
    ML. | Difficulté : **LOW**
  - **Delta-neutral sur ATR** : long assets z_price/ATR le plus négatif + short les plus
    positifs. | Difficulté : **MED**
  - Note : sans résultats documentés sur le variant actuel, les variants ci-dessus adressent
    les causes probables inférées.
- **Data requirements** : Binance OHLCV daily. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : NON DOCUMENTÉ
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : NÉGATIVE si purement MR; POSITIVE si long-only domine
  - Justification : MR = anti-tendance → anti-TSMOM en principe.

---

### Famille H25 — Portfolio TSMOM + MR Combined

- **Mécanisme économique** : Combinaison de Strategy A (TSMOM v2, momentum) et MR-ATR (H17,
  mean-reversion). Corrélation mesurée −0.30 → diversification du portfolio pour réduire le
  daily DD et améliorer la compatibilité propfirm.
- **Référence académique principale** : Markowitz (1952) diversification; Roncalli (2013)
  risk parity / ERC.
- **Variants déjà testés** (1 variant) :
  - Signal : 50/50 TSMOM v2 + MR-ATR | Corrélation mesurée = **−0.30** |
    Résultats : **NON DOCUMENTÉ** (code seul)
  - Cause d'échec : NON DOCUMENTÉ (inférée) : corrélation −0.30 insuffisante pour réduire
    MaxDD journalier à 3% (TSMOM seul = −11.9% daily). MR-ATR seul non-viable.
- **Variants alternatifs évidents NON testés** :
  - **Poids ERC** (Equal Risk Contribution) au lieu de 50/50 → maximise la diversification
    effective. | Difficulté : **MED**
  - **MR via H33 PMR basis** au lieu de H17 : corr_A = 0.18 (plus orthogonal que −0.30).
    Mais PMR non-viable standalone (coût). | Difficulté : **HIGH**
  - Note : sans résultats documentés pour H17, les variants ci-dessus répondent aux causes
    probables.
- **Data requirements** : Binance OHLCV. **Disponible**.
- **Compatibilité propfirm crypto** :
  - Drawdown profile : NON DOCUMENTÉ
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE (TSMOM composante dominante dans 50/50)
  - Justification : même si MR-ATR est NÉGATIVE avec A, le 50/50 garde une corrélation
    résiduelle positive (pondération TSMOM domine).

---

### Famille H07 — Short-Term Cross-Sectional Reversal (STR)

- **Mécanisme économique** : Les 3-5 pires performers cross-sectionnels sur 4 semaines ont
  tendance à rebondir (overreaction, reversal CS). Analogue du momentum loser-reversal
  documenté en equity large-cap.
- **Référence académique principale** : Zaremba (2021) *JBF* "Crypto CS momentum and
  reversal"; Grundy & Martin (2001) *RFS* CS reversal; Jegadeesh (1990) short-term reversal.
- **Variants déjà testés** (2 variants) :
  - V1 (cs_reversal) : long 3 pires CS performers 4w | 10 assets 2021-2026 |
    Résultats : **NON DOCUMENTÉ**
  - V2 (str_smallcap) : STR CS sur CoinGecko top-50→top-250 (médian-cap) | Coût = 0.34% RT
    (documenté, survivorship bias déclaré) | Résultats : **NON DOCUMENTÉ**
  - Cause d'échec : NON DOCUMENTÉ pour les deux. Inférée : survivorship bias (V2),
    β-dominance long-only, coût drag 0.34% RT (V2).
- **Variants alternatifs évidents NON testés** :
  - **Delta-neutral** (long losers + short winners) : résout β-dominance L11. Principal
    amélioration probable. | Difficulté : **MED**
  - **Universe sans survivorship** (V2) : reconstruction historique propre nécessaire.
    | Difficulté : **HIGH** (données propriétaires)
  - **Lookback {1w, 2w, 8w}** au lieu de 4w : horizon de reversal optimal. | Difficulté : **LOW**
- **Data requirements** : Binance OHLCV (V1, disponible). CoinGecko historical V2 avec
  survivorship non résolu. **Partiel** (V2 data contrainte).
- **Compatibilité propfirm crypto** :
  - Drawdown profile : >5% daily si long-only
  - Compatible Propr (3% daily) : NON
  - Compatible Velotrade / HyroTrader : À DÉTERMINER
- **Décorrélation vs Strategy A** :
  - Corrélation attendue : POSITIVE résiduelle (en crypto, momentum domine → long loser
    peut continuer à baisser = beta résiduel positif avec TSMOM)
  - Note : si vraiment reversal (delta-neutral), corrélation attendue NÉGATIVE.

---

## SYNTHÈSE — Tableau récapitulatif des 21 familles

| Famille | Force mécanisme éco | Variants alternatifs évidents | Data requirements satisfaits | Compat. propfirm | Décorr. vs A |
|---------|--------------------|-----------------------------|------------------------------|-----------------|--------------|
| **H21** MVRV Scaler | LOW (mécanisme falsifié) | NON | OUI | NON | Positive |
| **H22** F&G Contrarian | LOW (mécanisme falsifié L17) | NON | OUI | NON | Positive |
| **H35** ETH MVRV | LOW (mécanisme falsifié) | NON | OUI | NON | Positive |
| **H36** ETH Netflow | LOW (L12b structurel) | NON | OUI | NON | Positive |
| **H39** FGVD | LOW (mécanisme falsifié L17) | NON | OUI | NON | Positive |
| **H40** WAV | LOW (mécanisme falsifié L18) | NON | OUI | NON | Neutre |
| **H33** PMR Basis MR | HIGH (IC t=2.86 PASS) | OUI (maker exec, funding earn) | PARTIEL (HL court) | NON | Négative |
| **H08** STR 30-min | LOW (coût fatal à 30-min) | OUI (1h/4h bars) | PARTIEL (HL court) | NON | Négative |
| **H03** Funding Momentum | MED (carry momentum) | OUI (univers HL, delta-neutral) | OUI | NON | Positive |
| **H04** Funding Extreme Rev. | HIGH (short squeeze mécanisme) | OUI (univers HL, z-thresholds) | OUI | NON | Négative |
| **H09** BTC Dominance | LOW (corr BTC/alts > 0.80) | OUI (lookbacks, beta-hedge) | OUI | NON | Positive |
| **H11** BB Squeeze | MED (volatility clustering) | OUI (percentile, 4h bars) | OUI | NON | Positive |
| **H12** Crash Recovery | LOW (momentum > MR en crypto) | OUI (seuils, conditioning) | OUI | NON | Positive |
| **H14** USDT Volume | MED (Chi 2025 backing) | OUI (CS ranking, OI norm.) | OUI | NON | Positive |
| **H06** CS Price Momentum | LOW (β-dominance L11) | OUI (delta-neutral execution) | OUI | NON | Positive |
| **H31** CS-FS Delta-Neutral | HIGH (IC t=1.54, 59% gate) | OUI (backtest, univers, lookback) | OUI | NON | Neutre |
| **H19** TSMOM L/S Combined | MED (portfolio theory sound) | OUI (short dynamique, vol-target) | OUI | NON | Positive |
| **H38** ETF Regime Overlay | MED (lift réel +1.7%/an) | OUI (τ, fenêtre, poids) | OUI | NON | Positive |
| **H17** MR ATR-bounded | LOW (résultats inconnus) | OUI (sans ML, delta-neutral) | OUI | NON | Négative |
| **H25** Portfolio TSMOM+MR | LOW (MR non-viable seul) | OUI (ERC, composante MR alt.) | OUI | NON | Positive |
| **H07** STR (2 variants) | MED (reversal equity documenté) | OUI (delta-neutral, lookbacks) | PARTIEL (surv. V2) | NON | Positive (résiduel) |

**Notes synthèse :**
- **Propfirm** : NON pour toutes (CLAUDE.md : "Propfirms do NOT accept crypto/delta-neutral").
  Velotrade/HyroTrader = À DÉTERMINER (non documenté dans CLAUDE.md) pour toutes les 21 familles.
- **Familles à mécanisme falsifié** (H21, H22, H35, H36, H39, H40) : 6/21. Variants NON
  pour ces 6 — le mécanisme économique lui-même est invalide, non le paramétrage.
- **Familles HIGH mécanisme non-falsifié** : H33 (IC PASS documenté) et H04 (mécanisme
  court squeeze académiquement solide), H31 (IC 59% gate). Ces 3 sont à forte base mécanistique
  et données disponibles.
- **Familles décorrélées (NEUTRE ou NÉGATIVE vs Strategy A)** : H33, H08, H04, H31, H17 = 5.
  Ces familles sont structurellement plus intéressantes pour un portfolio multi-stratégies
  que les 14 POSITIVES qui répliquent le même beta.

---

*Rapport généré le 2026-05-28 sur branche `claude/crypto-audit-2026-05-28`*
*INVESTIGATION SEULEMENT — aucun backtest lancé, aucun fichier de stratégie modifié,
aucune modification de CLAUDE.md*
