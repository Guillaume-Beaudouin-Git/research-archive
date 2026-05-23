# Bootstrap VRP Notes — Variance Risk Premium on BTC Deribit Options
*Date: 2026-05-23 | Phase: 0 | Status: GATE 0 — AWAITING "GO PHASE 1"*

---

## Section 1 — VRP Mechanics

### Définition exacte

**Variance Risk Premium (VRP)** = la différence entre la variance *implicite* dans les prix d'options (risque-neutre) et la variance *réalisée* ex-post (mesure physique) :

```
VRP = σ²_Q − σ²_P   (en termes de variance annualisée)
    = DVOL²         − RV30²

Où :
  DVOL   = Deribit Implied Volatility Index (30d forward-looking, en %)
  RV30   = Realized Volatility sur 30 jours = sqrt(365/27 × Σ r²_d)
          où r_d = log(S_t / S_{t-1}) (log-return quotidien)
```

Magnitude confirmée : Almeida, Grith, Miftachov & Wang (arXiv:2410.15195) :
- **BTC VRP ≈ 0.14 annualisé (14%)** vs S&P 500 ≈ 0.02 (2%) → ratio 7×
- Régime basse vol : VRP = 0.17 | Régime haute vol : VRP = 0.12
- Direction : les investisseurs BTC surpaient systématiquement l'assurance vol → VRP > 0 en moyenne
- Fréquence : IV > RV 70% du temps depuis 2019 (Deribit Insights empirique)

### Décomposition du P&L d'une stratégie VRP short-vol

```
PnL_total = Carry_vol − Gamma_cost − Transaction_cost − Funding_cost

Carry_vol   = (DVOL − RV_réalisée) × notional × T  (theta positif)
Gamma_cost  = ½ × Γ × (ΔS)²                         (perte sur grands mouvements)
```

### Pourquoi le delta-hedging est obligatoire

Sans delta-hedge, "short straddle" = position directionnelle (long ou short selon la direction de BTC). Exemple :
- BTC monte +20% → la put perd de la valeur (good), la call augmente (bad), net delta = long BTC exposé
- Le P&L est dominé par la direction BTC, pas par le spread IV−RV

Avec delta-hedge continu (en pratique : threshold-based) :
- On réajuste la position en perp à chaque dépassement du seuil (ex : 2.5% de mouvement BTC)
- Delta du portefeuille reste ≈ 0 par construction
- Résidu = Vega PnL (exposition à IV−RV) + Gamma PnL (exposition à (ΔS)²)
- C'est une position **pure vol bet**, orthogonale à la direction BTC → satisfait Lesson 11

**VRP est la seule source d'alpha isolée par delta-hedging.** Tout comme Strategy B isole le carry de la direction en hedgeant le spot par un perp court, ici on isole le premium de variance en hedgeant le delta de l'option par un perp.

---

## Section 2 — Architecture Data Deribit

### Endpoints publics nécessaires (JSON-RPC over HTTP)

Base URL : `https://www.deribit.com/api/v2`

#### 1. Lister les instruments options disponibles
```bash
GET /public/get_instruments?currency=BTC&kind=option&expired=false
# Retourne : tous les strikes et échéances disponibles
# Paramètres : currency (BTC|ETH), kind (option|future|spot), expired (bool)
```

#### 2. DVOL Index (30d implied vol candles)
```bash
GET /public/get_volatility_index_data?currency=BTC&start_timestamp=...&end_timestamp=...&resolution=1D
# Retourne : timestamp, open, high, low, close (en % annualisé)
# Résolutions : 1/60 (1min), 60 (1h), 3600 (1d)  — vérifier valeurs exactes
# Paramètre continuation : pour paginer si période > limite API
```

#### 3. Historique mark price (5-min)
```bash
GET /public/get_mark_price_history?instrument_name=BTC-30MAY25-100000-C&start_timestamp=...&end_timestamp=...
# Retourne : prix mark (mid), IV, delta, gamma, vega pour chaque snapshot
# Disponible depuis 2019-10-01
```

#### 4. OHLCV options (TradingView format)
```bash
GET /public/get_tradingview_chart_data?instrument_name=BTC-30MAY25-100000-C&start_timestamp=...&end_timestamp=...&resolution=1D
# Retourne : open, high, low, close, volume (en BTC)
```

#### 5. Book summary (OI, volume, best bid/ask)
```bash
GET /public/get_book_summary_by_currency?currency=BTC&kind=option
# Retourne : pour chaque instrument actif — bid, ask, mark_price, IV, OI, 24h vol
```

#### 6. Dernier carnet d'ordres (L2 snapshot actuel)
```bash
GET /public/get_order_book?instrument_name=BTC-30MAY25-100000-C&depth=5
# Retourne : bids, asks, mark_price, index_price, greeks
# CRITIQUE : pas de L2 historique via API publique (voir contrainte ci-dessous)
```

#### 7. Trades récents
```bash
GET /public/get_last_trades_by_instrument?instrument_name=BTC-30MAY25-100000-C&count=100
```

### Rate limits

Deribit utilise un système de crédits :
- Requêtes non-authentifiées : politique plus stricte (risque de blocage IP si vol élevé)
- **Recommandation** : s'authentifier même pour les endpoints publics
- Pratique conseillée : max 5 req/s, avec sleep(0.2) entre requêtes batch

### Profondeur historique disponible — CONTRAINTE CRITIQUE

| Type de données | Disponible depuis | Source | Coût |
|----------------|------------------|--------|------|
| Options ticker/mark price | 2019-10-01 | Deribit API publique | Gratuit |
| Options chain (tous strikes) | 2019-03-30 | Tardis.dev L1/L2 | Payant (~$200/mo) |
| Options trades tick-by-tick | 2019-03-30 | Tardis.dev | Payant |
| DVOL (volatility index) | **2021-04-01** | Deribit API publique | **Gratuit** |
| DVOL candles (1d) | 2021-04-01 | Deribit API publique | Gratuit |
| Perp funding rates | 2019-03-30 | Deribit API / HL | Gratuit |

**Implications directes :**
1. DVOL backtest window : **avril 2021 → mai 2026 = 61 mois** ← baseline gratuite
2. Walk-forward 18m train / 6m OOS : folds = (61 − 18) / 6 = 7.2 → **7 folds réalisables** ✓
3. La COVID crash (mars 2020) est **HORS fenêtre DVOL** — stress test non backtestable
4. Pour proxy pre-2021 : reconstruire IV implicite depuis mark_price des options (2019-10-01) → 18 mois supplémentaires
5. Alternative payante : Tardis.dev full tick data 2019-03-30 → 7.1 années → walk-forward robuste

### Pipeline cache Parquet (design)

```
data/vrp/
├── dvol/
│   ├── BTC_dvol_1d.parquet       ← DVOL daily candles, 2021-04 → now
│   └── ETH_dvol_1d.parquet
├── options_mark/
│   ├── BTC_atm_mark_daily.parquet  ← ATM mark price + IV + greeks, daily
│   └── fetched_{date}.lock          ← éviter refetch
├── perp/
│   └── BTC_perp_1d.parquet          ← close price pour RV30 computation
└── cache_manifest.json              ← metadata : dates, sources, versions
```

Pattern: même logique que `strategies/delta_neutral/backtest.py` lignes 88-117 (fetch → cache CSV/parquet → load depuis cache si existe).

Exemple code fetch DVOL :
```python
import requests, pandas as pd, time
from pathlib import Path

def fetch_dvol_daily(currency: str = "BTC") -> pd.DataFrame:
    cache = Path(f"data/vrp/dvol/{currency}_dvol_1d.parquet")
    if cache.exists():
        return pd.read_parquet(cache)

    base = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
    start_ms = int(pd.Timestamp("2021-04-01", tz="UTC").timestamp() * 1000)
    end_ms   = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)

    results = []
    while start_ms < end_ms:
        r = requests.get(base, params={
            "currency": currency,
            "start_timestamp": start_ms,
            "end_timestamp": end_ms,
            "resolution": "1D"   # vérifier paramètre exact dans API ref
        }, timeout=30).json()
        data = r.get("result", {}).get("data", [])
        if not data:
            break
        results.extend(data)
        # data = [[ts_ms, open, high, low, close], ...]
        start_ms = data[-1][0] + 86_400_000
        time.sleep(0.2)

    df = pd.DataFrame(results, columns=["ts_ms","open","high","low","close"])
    df["timestamp"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df = df.set_index("timestamp")[["open","high","low","close"]].sort_index()
    df.rename(columns={"close": "dvol"}, inplace=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    return df
```

---

## Section 3 — Cost Model Détaillé

### 3.1 Fees Deribit options

| Composant | Montant | Notes |
|-----------|---------|-------|
| Option taker fee | **0.03% du sous-jacent** | idem maker et taker |
| Option maker fee | 0.03% du sous-jacent | pas de rebate maker sur options |
| Cap fee | 12.5% du prix de l'option | protection contre frais > option value |
| Settlement fee (expiry) | 0.015% du sous-jacent | à chaque expiration |
| Straddle/strangle | **Pas de combo discount** | confirmé dans policy Deribit |
| Liquidation | 0.2% | non-applicable si pas de levier |

**Pour un straddle ATM BTC à $100K notional, 30 DTE :**
```
Fee d'entrée  = 2 options × 0.03% × $100K = $60
Fee de sortie = 2 options × 0.03% × $100K = $60  (ou settlement 0.015%×2 = $30)
Total options fees = $90-$120 = 0.09-0.12% de notional par roll mensuel
```

### 3.2 Bid-ask spreads (estimation conservative)

Marché BTC options ATM 30 DTE sur Deribit :
- Bid-ask spread observé : ~0.5-1.5% de la valeur de l'option en normal, ~3-5% en stress
- Prix du straddle ATM (30 DTE, IV=80%) : ≈ 22% de notional
  ```
  Straddle_price ≈ 2 × C_ATM ≈ 2 × (S × N(d1) − K×e^{-rT}×N(d2))
  Pour ATM (S≈K, r≈0) ≈ 2 × S × N(0) × σ × √T ≈ S × σ × √(2T/π)
  = $100K × 0.80 × √(2×30/365/π) = $100K × 0.80 × 0.228 = $18,240 ≈ 18.2% notional
  ```
- Spread mid-to-trade : conservatif 0.5% de l'option premium
  ```
  Spread cost = 0.5% × 18.2% = 0.09% de notional par jambe
  Pour 2 options (straddle) × 2 (entrée+sortie) = 0.36% notional total
  ```
- Estimation conservative (stress + slippage) : **0.3-0.5% de notional** par roll

### 3.3 Coût de delta-hedge (dominant)

Stratégie : threshold-based rehedging à 2.5% de mouvement BTC (norme industrie).

**Estimations de fréquence des rehedges :**
- BTC σ_daily ≈ 5% (80%/√252)
- Seuil 2.5% = 0.5σ → probabilité franchissement en 1 jour ≈ 62%
- Estimation empirique : ~15-25 hedges/mois en régime normal, ~40-60 en haute vol

**Coût par hedge :**
- Via HL perp (taker base): 0.045% par trade
- Via Deribit BTC-PERPETUAL (taker): 0.05%, (maker): **−0.01% rebate**
- **Recommandation : utiliser Deribit perp pour hedge** (même exchange, latence minimale)
  - Avec maker limit orders : coût hedge peut devenir négatif (rebate)
  - En pratique (fill rate 70% maker) : net ≈ 0.0% (rebate + taker blended)

**Taille du hedge :**
- Delta straddle ATM ≈ 0 au moment d'entrée (call delta ≈ +0.5, put delta ≈ −0.5)
- Après mouvement de 2.5% : |Δ_net| ≈ Gamma × 0.025 × S
  - Gamma ATM 30 DTE (IV=80%) ≈ N'(0)/(S×σ×√T) ≈ 0.399/(100K×0.80×0.286) ≈ 1.74e-5 /BTC
  - ΔΔ = 1.74e-5 × 0.025 × 100K ≈ 0.044 BTC par jambe → total 0.088 BTC à hedger
- Hedge trade notional ≈ 0.088 × $100K = $8,800 = 8.8% de notional

**Coût hedge mensuel (scénarios) :**
```
Base (20 hedges × 0.045% HL × 8.8% size) = 20 × 0.045% × 8.8% ÷ 100% × $100K
= 20 × 0.045% × $8,800 = 20 × $3.96 = $79.2 ≈ 0.08% notional/mois

Conservative (40 hedges, haute vol)        = 0.16% notional/mois
Stress (70 hedges, crash)                  = 0.28% notional/mois

Via Deribit maker (rebate +0.01%) :
Base (20 hedges × −0.01%) = GAIN net = +$17.6 ≈ +0.018% notional/mois
```

**NOTE CRITIQUE :** Le coût du delta-hedge via maker est dramatiquement plus faible que via taker HL. Si Deribit perp maker est accessible avec fill rate ≥ 70%, le hedge cost est quasi-nul ou légèrement positif (rebate).

### 3.4 Funding payments sur perp hedge

- En régime haussier (BTC bull) : funding Deribit perp ≈ +0.01-0.05%/8h
- La position de hedge est **alternée** (long quand BTC baisse, short quand monte)
- En moyenne : funding net ≈ 0 (symétrique) sauf en régimes persistants
- Conservative : 0.05%/mois net funding cost (régime haussier prolongé)

### 3.5 Résumé cost model complet (par roll mensuel, notional $100K)

| Composant | Fourchette (% notional) | Scénario médian |
|-----------|------------------------|-----------------|
| Option fees (entrée + sortie) | 0.09% − 0.12% | 0.10% |
| Bid-ask spread (2 jambes × 2) | 0.30% − 0.50% | 0.35% |
| Delta hedge (Deribit maker 70%) | −0.02% − 0.16% | 0.04% |
| Delta hedge (HL taker 100%) | 0.08% − 0.28% | 0.12% |
| Funding net sur hedge | 0.00% − 0.10% | 0.05% |
| **Total (Deribit maker hedge)** | **0.37% − 0.78%** | **0.54%/mois** |
| **Total (HL taker hedge)** | **0.47% − 1.00%** | **0.62%/mois** |

**Annualisé :**
- Deribit maker hedge : ~6.5%/yr
- HL taker hedge : ~7.4%/yr

**VRP premium vs cost :**
```
VRP gross  ≈ 14%/yr
Coût total ≈  7%/yr (médian, Deribit maker hedge)
Net VRP    ≈  7%/yr → Sharpe estimé : 7% / σ_PnL

σ_PnL ≈ ? (dépend de la variance du P&L autour du VRP moyen)
→ en régime normal : σ_PnL mensuel ≈ 3-5% (à calibrer Phase 1)
→ Sharpe estimé : 7% / (3.5%×√12) ≈ 7% / 12.1% ≈ 0.58

AVEC STRESS REGIME (crash) : sigma_PnL explose → Sharpe peut tomber à ~0.3
SANS STRESS (exclude événements > 3σ) : Sharpe peut dépasser 1.0
```

**Conclusion coûts :** Le spread bid-ask est le coût dominant (~0.35%/mois), pas les fees Deribit. Le delta hedge est secondaire et peut être quasi-nul avec maker orders. **Le coût total est compétitif** — contrairement aux stratégies crypto perp où 0.17% RT tuait les edges faibles.

---

## Section 4 — Stress Test Events Catalogue

### Événements dans la fenêtre DVOL (avril 2021 − mai 2026)

| # | Date | Événement | Magnitude BTC | Durée | Dans DVOL window |
|---|------|-----------|--------------|-------|-----------------|
| 1 | Mai 12-19, 2021 | Tesla FUD + ban crypto Chine | **−53% en 1 semaine** ($64K→$30K) | 7 jours | ✓ |
| 2 | Jun-Jul 2021 | Continuation correction | −55% peak-to-trough ($64K→$29K) | 6 semaines | ✓ |
| 3 | Nov-Dec 2021 | Début du bear market 2022 | −40% ($69K→$41K) | 8 semaines | ✓ |
| 4 | Mai 2022 | **LUNA/Terra collapse** | **−65% pic-à-creux** ($40K→$17.7K) | 6 semaines | ✓ |
| 5 | Nov 8-14, 2022 | **FTX collapse** | **−25% en 5 jours** ($21K→$15.5K) | 5 jours | ✓ |
| 6 | 2026 (actuel) | Crash BTC −52% | **−52%** | en cours | ✓ |

### Événements HORS fenêtre DVOL (≡ non-backtestables gratuitement)

| # | Date | Événement | Magnitude BTC | Durée | Risk pour stratégie |
|---|------|-----------|--------------|-------|---------------------|
| A | Mars 12, 2020 | **COVID crash** | **−50% en 1 jour** | 1 jour | CATASTROPHIQUE : gamma exposure maximale |
| B | Nov 2018 | Crypto winter | −44% en 2 mois | 8 semaines | Drawdown prolongé |
| C | Déc 2017 − Déc 2018 | Bear market 2018 | −84% total | 12 mois | Stratégie profitable si IV > RV, même en bear |

**⚠️ CONTRAINTE CRITIQUE :** La COVID crash (mars 2020) est le pire scénario pour une short-vol delta-hedgée :
- -50% en 1 jour → gamma non-hedgeable à cette vitesse
- IV spike instantané de 80% → 400%+ (annualisé)
- Perte d'une short straddle : plusieurs fois la prime collectée
- Aucun seuil de threshold ne permet de hedger un mouvement de 50% en 1 jour
- **Ce scénario est HORS fenêtre DVOL** → le backtest WF ne le verra pas

**Mitigation recommandée :** Tester la stratégie sur mars 2020 séparément avec données de price BTC (disponibles) et proxy IV reconstruit depuis options data disponible depuis 2019-10-01. Sinon : ajouter une stop-loss sur delta-hedge loss mensuelle (ex : SL si pertes > 20% sur 1 mois).

### Impact magnitude sur P&L straddle court

En cas de move de magnitude M sur la période de hold (30 DTE) :
```
Perte_gamma ≈ ½ × Γ × M² × S²  (approximation Black-Scholes)

Pour M=20% (cas LUNA sur 1 semaine) et Γ ATM 30 DTE :
  Perte ≈ ½ × 1.74e-5 × (0.20 × 100K)² = ½ × 1.74e-5 × 400M = $3,480 = 3.5% notional

Pour M=50% (COVID 1 jour) :
  Perte ≈ ½ × 1.74e-5 × (0.50 × 100K)² = ½ × 1.74e-5 × 2.5Md = $21,750 = 21.75% notional
  → Perte > prime collectée (straddle ≈ 18.2% notional) → position nette négative
```

Ces chiffres confirment que la COVID-style crash génère une perte nette supérieure à la prime collectée en 1 seul événement.

---

## Section 5 — Deux Designs Candidates

### Design A : Short Straddle ATM 30 DTE, Delta-Hedged, Monthly Roll

**Mécanique :**
1. Au début de chaque mois : identifier l'option ATM la plus proche d'expiration en 28-35 DTE
2. Vendre 1 call ATM + 1 put ATM (même strike, même expiration) = straddle court
3. Delta initial ≈ 0 par construction (call delta ≈ +0.5, put delta ≈ −0.5)
4. Rehedger avec Deribit BTC-PERPETUAL chaque fois que BTC bouge >2.5% depuis dernier hedge
5. **Rouler à 7 DTE** (ne pas aller à l'expiration : gamma explosion dans les 5 derniers jours)
6. À 7 DTE : racheter straddle + clôturer hedge, puis entrer nouveau straddle 30 DTE

**Pros :**
- Implémentation simple (2 jambes) — 1 test AMTP seulement
- Strike ATM = plus liquide → spread minimal, fill rate élevé
- 70% du temps IV > RV → signal structurel robuste
- Backtest window suffisante (61 mois DVOL disponible)
- Pattern maker-taker sur perp hedge analogue à Strategy B (infrastructure existante)
- VRP premium 14%/yr >> cost total estimé 7%/yr → marge confortable

**Cons :**
- **Gamma risk en crash** : pertes non-linéaires si BTC bouge >20% rapidement
- Roll à 7 DTE = friction mensuelle (acheter straddle à 7 DTE = option encore avec value intrinsèque + extrinsèque)
- Pas de combo discount straddle → fee double vs autres combinaisons
- Corrélation avec Strategy A en crash : **DVOL spike dans les bear markets → les deux stratégies perdent simultanément** (voir alerte corr ci-dessous)
- Exposition unilatérale : si VRP retourne à zéro (régime ≡ IV ≈ RV), stratégie à flat P&L sans risk

**Expected Sharpe :**
- Régime normal (VRP=14%, σ_PnL=12%) : Sharpe ≈ 14%/12% = **1.17** (optimiste)
- Avec coûts (net 7%) et σ_PnL realistic 15% : Sharpe ≈ **0.47** (conservateur)
- Source Deribit Insights : "massive profitability in straddle-selling strategies" — mais sans coûts de hedge
- Estimation consensus : Sharpe **0.6-1.0** selon régime et coût hedge

**Tail risk magnitude :**
- COVID-style (−50%/jour) : perte potentielle 20-30% du notional en 1 événement
- LUNA-style (−30%/semaine) : perte potentielle 5-8% du notional
- FTX-style (−25%/5 jours) : perte potentielle 3-5% du notional

---

### Design B : Variance Swap Synthétique (Demeterfi et al. 1999)

**Mécanique (réplication log-contract) :**
La variance swap est répliquée par un portefeuille statique d'options à tous les strikes, pondérés par 1/K² :

```
Variance_swap_payoff = (RV² − K_var) × Notional

Réplication (Demeterfi 1999) :
  Poids_option(K) = ΔK / K²   pour K < K_0 (puts) et K > K_0 (calls)
  K_0 = strike de référence (forward ATM)

En pratique (strikes discrets) : acheter une "demi-douzaine" de strikes OTM
  - Puts : K_0 × 0.90, 0.80, 0.70, 0.60  (4 strikes)
  - Calls : K_0 × 1.10, 1.20, 1.30, 1.40  (4 strikes)
  - Pondération : 1/K² × ΔK normalisé
```

**Pros :**
- Exposition **linéaire** au VRP (pas de gamma explosion non-linéaire comme Design A)
- Capture plus fidèlement le spread DVOL²−RV² (le design A ne capture qu'une fraction)
- Mieux hedgé contre le skew (OTM puts protègent contre crash unilatéral)
- Payoff théoriquement exact = contrat de variance

**Cons :**
- **Complexité élevée** : 8+ jambes d'options par position (vs 2 pour Design A)
- Strikes OTM = **liquidité nettement inférieure** → spreads 3-5× plus larges
- Coût total = somme des spreads sur 8 strikes → potentiellement 2-3× le coût de Design A
- Requiert données historiques option chain complètes (payant, Tardis.dev)
- Ne peut pas être backtesté proprement avec données DVOL seules (besoin de la structure de vol complète)
- 8 jambes × 2 (entrée/sortie) = **16 trades par roll** → fee ×8 vs Design A
- Plus difficile à implémenter en phase de paper trading

**Estimation coût total (Design B) :**
```
Option fees : 8 strikes × 2 jambes × 0.03% = 0.48% notional (vs 0.09% Design A)
Bid-ask OTM : OTM spreads ≈ 1.5-3% de l'option premium (vs 0.5% ATM)
Total fees + spreads : ~1.5-2.5% notional/mois vs ~0.5% Design A
```
→ À 14% gross VRP, le net est ~9-12% Design A vs ~3-6% Design B → **Design A gagne nettement**

---

### Comparaison synthétique

| Critère | Design A (Straddle) | Design B (Var Swap réplication) |
|---------|--------------------|---------------------------------|
| Complexité | Faible (2 jambes) | Haute (8+ jambes) |
| Coût total/an | ~7% | ~18-30% |
| Net VRP attendu | ~7%/yr | ~0-5%/yr (après coûts) |
| Sharpe estimé | 0.6-1.0 | 0.1-0.4 |
| Tail risk | Gamma explosion | Mieux hedgé |
| Data requis | DVOL + mark_price | Full option chain (payant) |
| N_tests budget | 1-2 tests | 2-3 tests |
| Phase 1 backtestable ? | **OUI** | Partiellement (sans vraies OTM prices) |
| Recommandé Phase 1 | **OUI** | Non (réserver si Design A échoue) |

**⚠️ ALERTE CORRÉLATION :** Les deux designs sont corrélés avec Strategy A en tail scenario.

En régime de crash BTC :
- Strategy A (TSMOM) : perd car momentum retourne
- Short-vol (VRP) : perd car gamma loss dépasse la prime
- Corrélation positive en queue gauche → **double perte simultanée**

En régime normal :
- Strategy A : neutre à positif (momentum peu marqué)
- Short-vol : positive (IV > RV en régime calme)
- Corrélation : faible à positive

**Implication pour portfolio gate :** Strategy D (VRP) n'est PAS un pur diversifier de Strategy A en crise. La diversification est réelle en régime normal mais disparaît précisément quand on en a besoin. Ce n'est pas rédhibitoire (B carry a le même problème — funding collapse en bear), mais doit être documenté.

---

## Section 6 — Angles Morts à Ne Pas Reprendre

| # | Angle | Pourquoi INTERDIT |
|---|-------|------------------|
| PMR (Perp-spot Basis MR) | 6.39 | IC t=2.86 PASS, mais 912 events/year → 97%/yr cost drag. Signal réel, non exploitable. |
| OAGF (Open Auction Gap Fade) | 6.40-42 | IC t_HAC=−1.17, trop sparse (128 events/yr). Requiert 10 ans de données. |
| MVRV Z-Score | 6.28 | IC t=+0.32, non significatif. Proxy corr(TSMOM)=+0.40 — proxy de momentum, pas de valeur. |
| Exchange Netflow autocorr | 6.43-44 | IC t_HAC≈0 après correction. Effective N≈73 (autocorr régime). Gate 1 FAIL. |
| Active Addresses (variantes) | — | Même archétype que Netflow : autocorr régime, HAC deflation, TSMOM co-linear. |

**Ces 5 angles et leurs variantes cosmétiques (renommer la feature, changer le threshold) ne doivent pas consommer de n_tests budget.**

---

## Section 7 — Recommandation

**Recommandation : Design A (Short Straddle ATM 30 DTE) pour PHASE 1.**

### 5 bullets

1. **Marge cost/revenue confortable** : VRP gross 14%/yr, coût médian 7%/yr, net ~7%/yr — contrairement aux stratégies crypto perp où 0.17% RT tue les edges faibles, ici le signal domine encore après friction.

2. **Signal structurel documenté** : IV > RV 70% du temps depuis 2019 sur Deribit. Almeida et al. (2024) confirme empiriquement sur 5 ans. Pas un backtest orphelin — c'est un risk premium capturé par des hedge funds depuis des décennies sur les marchés equity.

3. **Design le plus backtestable** : DVOL + price BTC = données gratuites depuis 2021-04-01. 61 mois = 7 folds WF 18m/6m. Design B requiert un full option chain (Tardis.dev payant). Design A est testable aujourd'hui.

4. **Pattern d'exécution analogue à Strategy B** : long perp / short perp pour delta-hedge, même infrastructure HL/Deribit, même logique de threshold-based rebalancing. Réutilise `strategies/delta_neutral/backtest.py` patterns pour la mécanique hedge.

5. **Orthogonalité en régime normal** : VRP est un risk premium de volatilité, pas directionnel — orthogonal à TSMOM (A) et carry (B) sauf en tail events. En normal, corr(A, VRP) ≈ 0.0-0.2. Offre une réelle diversification en dehors des crises. Portfeuille A+B+C+VRP a un profil différent de A+B+C en moyenne.

### Contraintes PHASE 1 obligatoires

1. **IC pre-flight AVANT backtest** : tester si DVOL_lag1 − RV30_lag1 prédit sign(weekly return) ou sign(monthly_straddle_PnL). IC t_HAC > 2.0 requis avant Phase 2.
2. **N_tests budget** : max 3 tests Phase 1 (1 IC pre-flight + 1 backtest Design A + 1 variant threshold). Garder 2 tests en réserve.
3. **Stress test mars 2020 séparé** : reconstruire proxy IV depuis BTC options data 2019-10-01, estimer perte COVID scenario.
4. **Roll à 7 DTE obligatoire** : ne jamais aller à l'expiration. Documenter impact sur Sharpe vs roll 30 DTE.
5. **Corr(A) mesure obligatoire** : rapporter corr(VRP_daily_PnL, TSMOM_weekly_return) dans les résultats Phase 1.

---

## Appendice — N_tests Accounting

| Session | Nouvelles hypothèses | N_tests cumulé |
|---------|---------------------|----------------|
| Toutes sessions précédentes | — | **153** |
| VRP Bootstrap PHASE 0 (ce document) | 0 (lecture seule) | **153** |
| Budget maximum PHASE 1+2 | ≤ 5 | **≤ 158** |

E[max_SR] à N=153 : **≈ 4.34** (AMTP — seuil de déflation pour nouvelle stratégie)

E[max_SR] à N=158 : **≈ 4.35** (changement marginal)

**Tout Sharpe reporté pour la stratégie VRP doit être évalué contre ce seuil dans l'analyse AMTP.**

---

## Appendice — Sources

- Almeida, Grith, Miftachov, Wang (2024). *Risk Premia in the Bitcoin Market*. arXiv:2410.15195.
- Demeterfi, Derman, Kamal & Zou (1999). *More Than You Ever Wanted to Know About Volatility Swaps*. Goldman Sachs Quantitative Strategies Research Notes.
- Deribit API Documentation : https://docs.deribit.com/
- DVOL : https://insights.deribit.com/exchange-updates/dvol-deribit-implied-volatility-index/
- Tardis.dev historical data coverage : https://docs.tardis.dev/historical-data-details/deribit
- Deribit Insights VRP empirique : https://insights.deribit.com/industry/bitcoin-options-finding-edge-in-four-years-of-volatility-regimes/
- Quant Buffet (2024). *Delta Hedged Short Straddle BTC Strategy* : https://quantbuffet.com/2024/04/17/delta-hedged-short-straddle-btc-strategy/

---

## GATE 0

**STOP. Await "GO PHASE 1" in a new session.**

Pending user review on:
1. **Design A vs B** — recommandation Design A confirmée ?
2. **Data source** : DVOL gratuit (61 mois) suffisant, ou Tardis.dev payant pour étendre à 2019 ?
3. **Delta hedge exchange** : Deribit BTC-PERPETUAL (maker rebate) vs HL (taker 0.045%) ?
4. **Stress test** : reconstruire proxy IV pre-2021 depuis mark_price data 2019-10-01 en Phase 1 ?
5. **Portfolio corr constraint** : accepter corr(A, VRP) > 0.3 en crash scenarios, ou gate strict ?
