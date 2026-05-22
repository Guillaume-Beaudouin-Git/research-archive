# Bootstrap Notes — FX Algo Research (FTMO/MFF Propfirm)

*Generated: 2026-05-22 | Sources: README §1-12, tsmom_v2_propfirm/, nq_intraday/, data/cache.py, Forex/research/archived/ (3 dirs, 4 strategies), Portfolio/integration/initial_summary.md*

---

## 10 Lessons from the Full Codebase

**L1 — Signal T-1 / Trade T, sans exception.**
Le failure MLP (6.1) est le diagnostic canonique : 100% des bars BUY avaient Close > Open → look-ahead. En FX intraday, vérifier que le signal de 07:59 UTC ne peut pas prédire le close du même bar 08:00 UTC. Le test : `assert signal.corr(same_bar_return) < 0.01`.

**L2 — Feasibility IC et backtest doivent mesurer la même paire signal→outcome.**
Vol-regime MR (6.9) : IC mesuré intra-week rank correlation, backtest mesuré Monday-open→Friday-close P&L → false positive Sharpe −0.85. En FX : si IC est mesuré sur 1h forward, le backtest doit exécuter sur 1h forward exactement, pas "end of session".

**L3 — IC > 0 est nécessaire mais pas suffisant. Vérifier n_trades × cost_rt < gross return.**
LSTM 4h (6.23) : AUC=0.64, signal réel, mais 117 trades/an × 0.17% = 19.95%/an de drag → Sharpe=+0.022. En FX FTMO : EUR/USD 1.0 pip RT = ~0.0084% sur 1.08. Stratégie intraday 50 trades/mois = 600 trades/an × 0.0084% = 5%/an coût minimum. TP moyen doit dépasser 8+ pips brut.

**L4 — Sizing propfirm = fixed fractional 0.5-1% risk/trade, PAS vol-target.**
Vol-target classique (15% annualisé) devient sur-leveragé en régimes de faible vol FX (ex: EUR/USD 6% vol annualisé → levier ×2.5). Un jour de 1σ adverse = −0.06% × 2.5 = −0.15% seulement, mais un event gap de 5σ = −0.75% par trade × plusieurs positions simultanées peut dépasser le daily DD 5%. Utiliser `risk_pct = 0.005`, `lots = risk_pct × equity / stop_pips / pip_value`.

**L5 — RESEARCH_PASS ≠ PROPFIRM_PASS — deux seuils distincts.**
Framework deux-tier (README §10) : RESEARCH_PASS = Sharpe HAC > 0.8, MaxDD > −15%, WF > 50%. PROPFIRM_PASS (PRIMARY) = Monte Carlo 10k runs → P(pass) > 60%, P(daily DD hit) < 5%, P(max DD hit) < 15%. NQ ORB (Strategy C) a RESEARCH_PASS (Sharpe 1.52) mais 3/4 critères propfirm seulement — le MaxDD trailing (−13.4%) bloque C4. Pour FX/FTMO, la contrainte primaire est P(daily_loss > 4%) < 1% sur 1000 jours.

**L6 — HAC Newey-West maxlags=6 est obligatoire pour tous les t-stats alpha.**
Multi-asset TSMOM (§8.2) : OLS alpha t=2.4 → HAC t=1.31 (non significatif) après correction. Toujours `sm.OLS().fit(cov_type='HAC', cov_kwds={'maxlags': 6})`. Le Sharpe simple (mean/σ × √N) est correct ; le HAC s'applique uniquement aux t-stats de régression alpha.

**L7 — AMTP (approx_multi_test_penalty) compte N_tests cumulé = 82 + tests futurs.**
À n=82, E[max_SR] ≈ 2.07 mensuel → annualisé ~7.1 → toutes les stratégies avec Sharpe < 7 sont potentiellement des faux positifs si testées seules. En pratique : utiliser le seuil RESEARCH_PASS Sharpe brut > 0.8 AVANT costs comme filtre préliminaire, puis DSR avec n actuel. Pour FX, n_tests démarre à 82 (crypto + multi-asset + FX archivés).

**L8 — Le Monte Carlo propfirm est LA métrique primaire, pas le Sharpe.**
Propr ceiling structural = 39% (β_crypto trop élevé, crash corrélés). FTMO structure différente (5% daily DD vs 3% Propr) → expected ceiling 55-65%. Pour FX FTMO : simuler 10k runs × 60 jours avec daily DD reset, capital initial $100K, sizing fixe, spread variable par session. `P(pass) > 60%` est le gate ultime.

**L9 — hit_rate > 45% ET avg_win/avg_loss > 1.3 sont des conditions NÉCESSAIRES pour propfirm.**
Avec daily DD 5% et max DD 10%, une série de pertes consécutives > 5 trades (typique avec hit_rate < 45%) peut atteindre le daily limit. Les paramètres cibles : hit_rate ≥ 50% (idéalement 55%), R:R ≥ 1.5 (TP = 1.5× SL), max consecutive losses ≤ 5. Ces contraintes orientent vers les stratégies breakout/momentum intraday, PAS carry/MR pur.

**L10 — Archiver proprement = un succès scientifique.**
Chaque SKIP documente : signal, IC, t-stat, root cause structurelle, leçon. N_tests++ même sur abandon. 82 tests → connaissance précieuse sur ce qui NE fonctionne PAS en crypto/FX. Un Sharpe brut < 0.6 → archive immédiate sans backtest complet (économie de N_tests).

---

## 4 Raisons d'Échec des FX Archivés

### FX-1 — Carry FRED G10 (`fx_carry_fred/`) : WEAK
**Résultats** : IC=+0.027, t=2.02 (WEAK), Sharpe=−0.13, MaxDD=−53%.
**Raison d'échec** : L'IC carry est réel (forward premium puzzle confirmé, Brunnermeier et al. 2008) mais la distribution des returns est right-skewed avec fat left tail. Les unwind events (GFC 2008 MaxDD −24%, COVID 2020 MaxDD −21% en 15 semaines, EM unwind 2015 MaxDD −15%) détruisent 12+ mois de carry accumulé en quelques semaines. En L/S brut sans crash protection, le Sharpe full-sample est négatif. Le carry G10 nécessite un filtre trend (Asness et al. 2009) ou un timing de crash — incompatible avec les règles propfirm raw (DD max 10%) en format L/S standard.

### FX-2 — CS Momentum 12M-1M G10 (`fx_momentum_monthly/`) : SKIP
**Résultats** : IC=−0.024, t=−0.83, Sharpe=−0.06, MaxDD=−42%.
**Raison d'échec** : Le facteur est mort en G10 depuis 2011. Deux causes structurelles : (a) arbitrage post-publication du Menkhoff et al. (2012) — le signal a été massivement répliqué depuis publication ; (b) interventions systématiques des banques centrales contre les devises gagnantes : SNB CHF floor 2011-2015, ECB QE 2015-2018, BOJ Yield Curve Control 2016-2024 créent des reversals abruptes contre la direction momentum. IC négatif (pas juste nul) — le signal prédit activement la mauvaise direction depuis 2011.

### FX-3 — TSMOM tanh 12M G10 (`fx_momentum_monthly/`) : SKIP
**Résultats** : IC=−0.025, t=−0.87, Sharpe=−0.13, MaxDD=−23%.
**Raison d'échec** : Même conclusion que FX-2, même cause. Le TSMOM (crypto Strategy A, Sharpe 1.33) ne se transfère pas au G10 FX car les crypto n'ont pas d'ancre banque centrale — le momentum crypto peut persister 12-24 mois. En FX G10, les BC interviennent activement dès qu'une devise s'apprécie trop. Note : le vol-scaling (tanh) réduit MaxDD de −42% à −23% — confirmation que la mécanique de scaling est correcte, mais l'IC négatif disqualifie le signal quel que soit le sizing.

### FX-4 — Carry G10+EM (`fx_carry_em/`) : SKIP
**Résultats** : 1W IC=+0.001 (zéro), 4W IC=−0.022, Sharpe=−0.49, MaxDD=−77%.
**Raison d'échec** : L'ajout des EM (BRL, MXN, ZAR, TRY) dilue puis inverse le signal G10 carry. Root cause : "peso problem" — les hauts différentiels EM (TRY 40-50%/an, BRL 13%/an) reflètent une dépréciation anticipée intégrée dans les taux, pas un premium de portage exploitable. En pratique, les hautes devises EM se déprécient systématiquement plus vite que leur carry ne compense. COVID MaxDD=−21% (marginalement propfirm-compatible) mais Sharpe=−0.49 disqualifie l'approche. EM spreads 60 bps RT (vs 15 bps G10) aggravent le calcul cost.

---

## Conventions Code

Toutes issues des scripts live (`tsmom_v2_propfirm/`, `nq_intraday/`) :

```python
# Type hints obligatoires
def compute_signal(px: pd.DataFrame, lookback: int = LB) -> pd.Series:

# Constantes nommées (pas de magic numbers)
LOOKBACK_DAYS: int = 20
RISK_PCT: float = 0.005          # 0.5% risk per trade
MIN_RANGE_PIPS: float = 10.0    # minimum pre-session range
COST_RT_PIPS: float = 1.0       # EUR/USD round-trip

# Seed fixé
rng = np.random.default_rng(42)

# Docstrings NumPy
"""
Parameters
----------
px : pd.DataFrame
    OHLCV avec index DatetimeIndex tz-aware UTC
lookback : int
    Lookback en barres (pas en jours calendaires)

Returns
-------
pd.Series
    Signal T-1 indexé sur les mêmes timestamps que px
"""

# Anti look-ahead : shift explicite
signal = compute_raw_signal(px)
signal_lagged = signal.shift(1)   # T-1 pour trade T

# Cache obligatoire
from data.cache import get_cached_or_fetch
df = get_cached_or_fetch("EURUSD=X", start="2019-01-01", end="2026-05-22", interval="1d")

# Fichiers numérotés
# iter_01.py → iter_02.py → iter_03.py (max 3 post-v1)

# Commit par phase
# git commit -m "[phase 2] fx_session_breakout: data + IC feasibility (IC=0.045, t=3.2)"
```

5 fixes méthodologiques obligatoires (§10, methodology_audit.py) :
1. Excess returns : subtract daily RF (FRED DTB3) avant tout calcul P&L/régression
2. HAC SE : `sm.OLS().fit(cov_type='HAC', cov_kwds={'maxlags': 6})` pour t-stats alpha
3. Daily vol targeting : vol daily × √252, PAS `monthly_returns.rolling(3).std()`
4. Diagnostics signal spécifiques à la stratégie (hit_rate, quintile monotonicity)
5. `approx_multi_test_penalty` (pas "DSR") — naming honnête avec limitations documentées

---

## Infra Data

### `data/cache.py` — API publique (réutilisation OBLIGATOIRE)

```python
from data.cache import get_cached_or_fetch, load_nq_1min

# Cache générique yfinance (FX weekly/daily)
df = get_cached_or_fetch(
    ticker="EURUSD=X",
    start="2019-01-01",
    end="2026-05-22",
    interval="1d",            # "1d", "1wk", "1h" (yfinance)
    source="yfinance",        # seule source implémentée
    max_age_days=1.0,
)
# Retourne DataFrame avec colonnes lowercase : open, high, low, close, volume
# Cache : data/raw/yf_{ticker}_{interval}_{hash}.parquet
# Métadata : data/metadata/yf_{ticker}_{interval}_{hash}.json
```

**Extension nécessaire pour FX 1min/tick** : `get_cached_or_fetch` ne supporte que yfinance. Pour Dukascopy (tick→1min), implémenter dans un fichier séparé (`Forex/research/active/<slug>/data_fx.py`) avec la même interface parquet. Packages candidats :
- `pip install dukascopy-python` (API Python non-officielle Dukascopy)
- `histdata.com` ZIP download → parser custom
- `yfinance` 1h max pour FX (qualité insuffisante pour intraday)

**Rates FRED** (pour carry ou excess returns) :
```python
from pandas_datareader.data import DataReader
dtb3 = DataReader("DTB3", "fred", "2019-01-01", "2026-05-22").iloc[:, 0]
euribor = DataReader("IR3TIB01EZM156N", "fred", "2019-01-01", "2026-05-22").iloc[:, 0]
```

**XXXUSD convention** (inversion pour paires USD-base) :
```python
if ccy in {"EUR", "GBP", "AUD", "NZD"}:
    px = yf.download(f"{ccy}USD=X", ...)["Close"]
else:  # USDJPY, USDCHF, etc.
    px = 1.0 / yf.download(f"{ccy}=X", ...)["Close"]
```

### Spread variable par session (OBLIGATOIRE pour backtest réaliste)

```python
SESSION_SPREAD_PIPS = {
    "asia":   1.5,   # 22:00-07:00 UTC (EUR/USD)
    "europe": 0.8,   # 07:00-16:00 UTC
    "us":     0.9,   # 13:00-22:00 UTC
    "news":   4.0,   # NFP/CPI/FOMC ±15min
}
```

### Structure dossier recherche (template NQ ORB)

```
Forex/research/active/<slug>/
├── __init__.py
├── HYPOTHESIS.md           # edge, propfirm fit, hit rate attendu, R:R
├── data_fx.py              # fetch + cache Dukascopy/yfinance FX
├── iter_01.py              # feasibility : signal + IC brut
├── iter_02.py              # backtest vectorisé + WF + propfirm sim
├── iter_03.py              # validation finale + stress tests
├── results.json            # métriques clés (Sharpe, MaxDD, WF%, P(pass))
└── DECISION.md             # GO/SKIP + explication
```

---

## 3 Angles Propfirm-Compatibles

### Angle A — London Open Session Breakout (ORB-FX)

**Edge hypothesis** : La session asiatique (23:00-06:59 UTC) établit un range d'équilibre quand les institutions US/EU sont inactives. À l'ouverture Londres (07:00-09:00 UTC), les flux institutionnels européens créent un breakout directionnel au-dessus ou au-dessous du range asiatique. Analogue au NQ ORB (Strategy C, Sharpe 1.52, RESEARCH_PASS), adapté au marché FX continu.

**Propfirm fit** :
- Hit rate attendu : 45-55% (momentum session, pas reversal)
- R:R cible : 1:2 (SL = 50% range, TP = 1× range) → avg_win/avg_loss ≈ 1.5-2.0
- Max consecutive losses : ~6 (calculable via binomial sur 45-55% hit rate)
- Frequency : 1 trade/jour/paire → 20-25 trades/mois sur EUR/USD+GBP/USD
- Cost : EUR/USD 1.0 pip RT = 0.0083% sur 1.20 → TP cible minimum 15 pips

**Instruments** : EUR/USD, GBP/USD (spreads les plus faibles FTMO Astra 0.6-1.2 pips)

**Signal T-1** : range asiatique calculé sur session T-1 (23:00-06:59 UTC clôturé avant entrée 07:00)

**Données** : 1min Dukascopy 2019-2026 (Dukascopy a ses propres données OHLC 1min gratuites et de qualité institutionnelle)

**Risk sizing** : `risk_pct = 0.005` (0.5%/trade), `SL_pips = 0.5 × asian_range_pips`, `lots = (equity × risk_pct) / (SL_pips × pip_value_per_lot)`

---

### Angle B — News-Fade Post-NFP/ECB/FOMC

**Edge hypothesis** : Les spikes de prix immédiatement post-annonce macroéconomique (NFP ±30 pips, ECB ±50 pips, FOMC ±40 pips en 5 minutes) se partial-fade dans les 30-90 minutes suivantes. Les market makers élargissent les spreads pendant l'annonce puis reprennent la liquidité → reversion vers le mean pré-annonce à 60-70% de fréquence.

**Propfirm fit** :
- Hit rate attendu : 55-65% (reversion après over-reaction, bien documenté en microstructure FX)
- R:R cible : 1:1.5 (SL = spike high/low + buffer, TP = 50-70% fade)
- Frequency : ~8-10 events/mois majeurs (4 NFP, 8 ECB/FOMC) → 16-20 trades/mois EUR/USD+GBP/USD
- Challenge : spread à +2-5 pips pendant l'event → modéliser explicitement dans le coût d'entrée
- Filtre : entrer uniquement si spike > 2× ATR(14) du jour précédent (éviter les non-events)

**Données** : Calendrier économique (forexfactory.com API ou fichier CSV) + 1min Dukascopy 2019-2026

**Anti-look-ahead** : Signal = spike mesuré à T+5min après annonce, trade à T+5min+1bar, SL/TP calculés sur données T+4min. Pas de connaissance du résultat de l'annonce dans le signal.

---

### Angle C — AUD/JPY Risk-On/Off Intraday (Equity-FX Momentum)

**Edge hypothesis** : AUD/JPY est la paire FX "risk barometer" classique : AUD = commodities + growth (Australie) / JPY = safe haven. Corrélation empirique avec SPY/VIX : quand S&P 500 chute > 0.8% sur une session, JPY s'apprécie systématiquement dans les 2-8h suivantes (flight to safety). Signal lag-1 quotidien : retour SPY la veille + VIX change → direction USD/JPY et AUD/USD du lendemain.

**Propfirm fit** :
- IC attendu > 0.04 à horizon 4h (cross-asset momentum lag, non-arbitragé car FX marché séparé)
- Hit rate attendu : 50-58% (directionnel, pas mean-reversion)
- R:R cible : 1:2 avec time-stop 4h (session complète)
- Frequency : 10-15 trades/mois (filtre sur signal magnitude pour éviter les jours neutres)
- Correlation avec strategies crypto A/B/C : faible par construction (FX ≠ crypto), à confirmer

**Instruments** : USD/JPY (spread 0.7-1.0 pip RT FTMO), AUD/USD (spread 0.8-1.2 pip RT)

**Signal** : `signal[t] = sign(SPY_ret[t-1]) × sign(VIX_chg[t-1])` — long AUD/JPY si equity monte + VIX baisse, short si equity tombe + VIX monte. Zéro si signaux contradictoires.

**Données** : SPY + VIX via yfinance (get_cached_or_fetch), AUD/USD + USD/JPY via yfinance ou Dukascopy

---

## Décision GATE 0

Bootstrap complet. Les 4 stratégies FX archivées échouent toutes sur des causes structurelles distinctes (carry crash risk, momentum mort post-publication CB, peso problem EM). Les 3 angles proposés sont structurellement différents des archivés : orientation intraday (pas weekly/monthly), sizing fixed fractional (pas L/S carry pur), hit rate > 45% comme contrainte primaire.

**Recommandation** : Commencer par Angle A (London Open Breakout) — analogie la plus directe avec Strategy C (NQ ORB, RESEARCH_PASS validé), edge économique défendable, données Dukascopy 1min gratuites disponibles.

**GATE 0 : STOP. Attendre "GO PHASE 1" explicite.**
