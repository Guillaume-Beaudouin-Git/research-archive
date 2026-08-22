# NQ futures 1-min Databento — Rapport de nettoyage et de validation

> **Source** : Databento `GLBX.MDP3` schema `ohlcv-1m`, parent symbol `NQ.FUT`
> (= **TOUS** les contrats outright NQ futures sur la fenêtre).
> Fichier brut : `data/GLBX-20260601-FP4HWRA58K/glbx-mdp3-20100606-20260531.ohlcv-1m.dbn.zst`
> (107 MB compressé .zst).
>
> **Décision méthodologique** : single-source. On REMPLACE l'ancien Kaggle 2022-2025,
> on ne joint pas. Pas de risque de soudure (cf. leçon EURGBP).
>
> **Instrument** : NQ FUTURES (E-mini Nasdaq-100), pas le US100 CFD utilisé dans
> les analyses 2022-2025 précédentes. Même sous-jacent (Nasdaq-100), instrument
> différent (microstructure, sessions, coûts différents). C'est désormais la
> source de vérité pour tout backtest NQ.

---

## 1. Stats du parquet propre

| Métrique | Valeur |
|---|---|
| Path | `data/raw/NQ_1min_databento_2010-2026.parquet` |
| Taille | 83.9 MB (compression snappy) |
| Rows | **5,123,288** bars 1-minute |
| Date range (UTC) | 2010-06-07 04:00 → 2026-05-29 20:59 |
| Trading dates (ET) | **4,105** |
| Index | `timestamp_utc`, DatetimeIndex tz-aware **UTC** |
| Colonnes | `open, high, low, close` (float32) ; `volume` (int64) ; `symbol` (string) ; `is_roll_day` (bool) ; `is_rth` (bool) |

### Continuous front-month construction

- Source amont = 7,133,674 lignes, **158 symbols distincts** (outrights + spreads).
- **Spreads filtrés** : 519,989 lignes (118 symboles avec `-`), p. ex. `NQM6-NQU6`. Conservés zéro car ce sont des
  instruments synthétiques, non-tradés en outright.
- **Front-month logic** : pour chaque ET trading date, le contrat avec le plus de
  volume RTH (09:30-16:00 ET) devient le front. Tous les bars de ce contrat ce jour-là
  forment la série continue.
- **Distinct front contracts** sur 2010-2026 : **40** (NQ + cycle H/M/U/Z, 16 ans).
- **Pas de price-adjustment** : niveaux conservés bruts. L'ORB travaille en points
  relatifs au 09:30 ET → l'ajustement de niveau est sans effet sur le signal.

### `is_roll_day` flagging

- **64 roll days détectés** (== 16 ans × 4 trim). Match exact à l'attendu.
- Premiers : `2010-06-10, 2010-09-10, 2010-12-10, 2011-03-11, 2011-06-10, ...`
- Derniers : `2024-03-11, 2024-06-17, 2024-09-16, 2024-12-17, 2025-03-18, 2025-06-16, 2025-09-15, 2025-12-15, 2026-03-16`
- Mécanique détectée : `front_month(t)` change vs `front_month(t-1)`. Volume-based
  rolls naturels (CME mécanique standard).
- **Politique : skip au backtest** (flag conservé, pas supprimé du parquet).

---

## 2. Data-quality

### 2.1 OHLC sanity → **0 violation**

```
high_violations = 0   (high >= max(open, close, low))
low_violations  = 0   (low  <= min(open, close, high))
volume < 0      = 0
```
Sur 5,123,288 bars. Pas un single bar mal formé.

### 2.2 Cash-open volume spike à 09:30 ET → **76.7 % global**

Pour chaque journée, on cherche l'argmax(volume) dans la fenêtre 09:25-09:35 ET.
La distribution **par minute** sur 4,105 jours :

| Minute ET | Count | % |
|---|---|---|
| 09:26 | 1 | 0.02% |
| 09:28 | 3 | 0.07% |
| 09:29 | 4 | 0.10% |
| **09:30** | **3,149** | **76.71%** |
| 09:31 | 305 | 7.43% |
| 09:32 | 202 | 4.92% |
| 09:33 | 111 | 2.70% |
| 09:34 | 92 | 2.24% |
| 09:35 | 238 | 5.80% |

96 % du volume max tombe **dans 09:30-09:35 ET**. Le spike est bien aligné, l'index UTC
+ la conversion ET sont corrects.

**Par année** (échantillon) :

| 2010 | 2011 | 2012 | 2013 | 2014 | ... | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| 74.5% | 69.8% | 76.5% | 85.3% | 77.2% | ... | 88.0% | 75.5% | 79.2% | 84.8% | 99.1% |

Les années anciennes (2010-2012) sont plus dispersées (microstructure différente,
pré-HFT mature). 2026 ne couvre que 5 mois, donc le 99 % est partiel.

→ **conclusion** : pas d'erreur de timezone (sinon ce serait ≈ 0%). DST géré
correctement par `tz_convert("US/Eastern")`.

### 2.3 DST spot-check → **0 mismatch**

32 spot-checks : pour chaque année 2010-2025, on a pris :
- un lundi/mardi en **mars** (DST active) : 09:30 ET doit = 13:30 UTC
- un lundi/mardi en **novembre** (DST inactive) : 09:30 ET doit = 14:30 UTC

→ Tous les 32 samples sont corrects. La conversion UTC → ET via pandas/zoneinfo gère
proprement les bascules DST 2eᵉ dim mars / 1ᵉʳ dim novembre.

### 2.4 OR window gaps → **5 / 4,105 sessions** (0.12 %)

La fenêtre OR 09:30-09:45 ET doit contenir 15 bars 1-min. 5 sessions sur 4,105 (0.12 %)
en ont moins. Négligeable, et probablement halt/fast-market (à confirmer en croisant
avec `condition.json` ou holiday calendar) — pas un défaut structurel.

### 2.5 Degraded days (`condition.json`) → **29 / 5,006** (0.58 %)

29 jours sont flaggés `"condition": "degraded"` par Databento (jamais
`"missing"` ou `"unavailable"`) :

```
2014-06-11 / 2014-06-12 / 2014-06-13 / 2014-06-15
2014-09-22 / 2014-09-23 / 2014-09-24 / 2014-09-25
2014-12-31 / 2017-11-13 / 2018-10-21 / 2019-01-15
2019-02-22 / 2019-03-13 / 2019-03-26 / 2020-02-27
2020-02-28 / 2020-06-30 / 2020-07-01 / 2021-12-05
2022-01-02 / 2025-09-17 / 2025-09-24 / 2025-11-28
2026-03-15 / 2026-03-16 / 2026-04-10 / 2026-05-24 / 2026-05-31
```

Note : les dates "connues" listées dans le prompt (`2020-06-22, 2021-07-07,
2021-10-26, 2022-09-19`) n'apparaissent PAS comme "degraded" dans le fichier
fourni — probablement des dates problématiques pour d'autres produits CME (pas NQ
spécifiquement). Le `condition.json` du job Databento est NQ-spécifique.

**Politique** : ne pas supprimer ces 29 jours du parquet, les flagger plutôt
(TODO : ajouter colonne `is_degraded` au prochain rebuild). Pour le backtest,
le moteur peut les exclure en croisant avec ce fichier.

---

## 3. Reconciliation 2022-2025 vs US100 CFD — **MATCH après correction tz**

### Découverte importante : `m1_panel.parquet` est mal labelisé

Première passe naïve : returns correlation 1-min NQ futures vs US100 CFD = **0.04**.
Quasi nulle. Drapeau rouge immédiat.

**Cause racine identifiée** par sweep d'offset horaire :

```
shift= -7h  corr=0.019
shift= -6h  corr=0.026
shift= -3h  corr=0.627   ← peak
shift= -2h  corr=0.364
shift= +0h  corr=0.010   ← naïf (assumé UTC)
shift= +3h  corr=-0.005
```

→ l'index `m1_panel.parquet`, **nommé `timestamp_utc`**, est en fait du **broker
wall-clock Europe/Athens** (EET hiver UTC+2 / EEST été UTC+3). C'est une convention
classique MT5 (les exports MetaTrader donnent l'heure serveur, et l'ingest a labellé
naïvement `timestamp_utc`).

Confirmation : profil horaire de `|log return|` US100 pique à h=17 du fichier,
soit 14h UTC = 10h ET = US morning peak.

### Reconciliation corrigée

Après tz_localize `Europe/Athens` puis tz_convert UTC :

| Métrique | Valeur |
|---|---|
| **Returns corr 1-min** | **0.9033** |
| **Returns corr 5-min** | **0.9244** |
| **Returns corr 1-hour** | **0.9314** |
| **ORB% daily corr** | **0.9527** (n=1,031 jours) |
| Mean ORB% NQ futures | 0.5311 % |
| Mean ORB% US100 CFD | 0.5088 % |
| Ratio NQ / US100 | **1.04×** (essentiellement identique) |
| **Verdict** | **MATCH** |

→ Le pipeline NQ futures **reproduit fidèlement** ce que le US100 CFD donnait
sur 2022-2025. La méthodologie d'audit / d'analyse précédente sur le CFD est
transférable au futures (avec ajustements de coûts/microstructure, mais le
signal directionnel est le même).

### Implication méthodologique

L'analyse 2022-2025 antérieure utilisait `m1_panel.parquet[US100]` dont l'index
est mal nommé. Le moteur `orb_core.py` utilise des filtres `hour, minute` en
broker-time donc fonctionne sans le savoir : `("US100", 16, 30, ...)` correspond
à 16:30 EET ≈ 09:30 ET, ce qui est la cash open ciblée — sauf pendant les
~3 semaines/an de désalignement DST EU vs US.

**À surveiller** : ajouter une note dans `audit/orb_core.py` que l'index du panel
est en broker-time EET/EEST, pas en UTC malgré le nom. Hors scope de cette ingestion
NQ — flag séparé pour cleanup futur.

---

## 4. Drop-in pour le moteur ORB

### Loader

Le parquet est prêt à être servi via une extension de `data/cache.py::load_nq_1min`.
Patch suggéré :

```python
# data/cache.py
_NQ_DATABENTO = _RAW / "NQ_1min_databento_2010-2026.parquet"

def load_nq_1min(path: str | None = None,
                 source: str = "databento") -> pd.DataFrame:
    if source == "databento":
        return pd.read_parquet(_NQ_DATABENTO, engine="pyarrow")
    if source == "kaggle":
        # comportement legacy 2022-2025 (à déprécier)
        ...
```

L'utilisateur devrait basculer **source='databento'** comme défaut.

### Branche moteur ORB

Dans `data/ftmo_research/audit/orb_core.py::_load_m5`, ajouter une branche :

```python
@lru_cache(maxsize=8)
def _load_m5(symbol: str) -> pd.DataFrame:
    if symbol == "NQ":
        from data.cache import load_nq_1min
        df = load_nq_1min(source="databento")
        # NQ parquet: index tz-aware UTC. orb_core attend tz-naive wall-clock.
        # Convention NQ = US/Eastern (cash open 09:30 ET = signal naturel).
        df = df[df["is_rth"]]                    # garde RTH = 09:30→15:59 ET
        df = df[~df["is_roll_day"]]              # skip roll days
        df.index = df.index.tz_convert("US/Eastern").tz_localize(None)
        df = df[["open", "high", "low", "close"]].copy()
    elif symbol in ("US100", "US500", "US30", "US2000"):
        df = pd.read_parquet(DATA / "m1_panel.parquet")[symbol].dropna()
        # NB : index nommé timestamp_utc mais wall-clock EET/EEST (broker).
    else:
        ...
    return df.resample("5min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
```

### Sleeves NQ recommandés

Une fois le `_load_m5("NQ")` en place, ajouter dans `SLEEVES` :

```python
SLEEVES = [
    ("NQ", 9, 30, 16, 6),       # 30-min OR, RTH US 09:30 ET → cash close 16:00 ET
    # variantes possibles :
    # ("NQ", 9, 30, 12, 3),     # 15-min OR variante (à benchmarker)
    # ("NQ", 9, 30, 16, 3),     # 15-min OR + close session entière
]
COST_POINTS["NQ"] = 1.0     # ~4 ticks RT MNQ ($2.15)
```

NB : le sleeve **GER40 reste sur Dukascopy** (à fetcher Phase 2, plan séparé).
Le fetch Databento couvre **seulement US100 → NQ**, c'est la réalité de ce qui
a été acheté.

---

## 5. Limites et points à surveiller

1. **Single-source assumée saine** : pas de cross-validation avec un fournisseur
   tiers. Le pipeline interne (DBN → parquet) est validé par la reconciliation
   vs US100 CFD ; l'absolu (vs un troisième dataset) n'est pas vérifié.
2. **Cash-open spike pas à 100 %** : 76 % global, 88 % en 2022, 99 % en 2026.
   La dispersion reflète la microstructure (pre-open auctions, post-2008
   evolution HFT), pas un défaut de timestamps. Mais : tout signal qui repose
   *exclusivement* sur le bar 09:30 exact devrait avoir un test de robustesse à
   ±1 minute.
3. **`condition.json`** ne couvre PAS les dates "anomalies connues" mentionnées
   dans le prompt utilisateur (2020-06-22 etc). Soit ces dates étaient pour
   un autre produit, soit le fichier degraded est conservateur. À cross-checker
   au cas par cas si une stat 2020 paraît bizarre.
4. **Pas de price-adjustment** sur les rolls. Si un signal nécessite la
   continuité over-night (carry, gap-fill) → recalculer un back-adjusted continuous
   ou skip les roll days.
5. **GER40 manquant** : ce dataset ne contient PAS le sleeve GER40. La validation
   étendue 2-sleeves de Strategy 2 requiert un fetch Dukascopy DAX (Phase 2,
   décodeur existant `Forex/research/archived/strategy_e_fix_flow/data_setup.py`).
6. **m1_panel.parquet index est en broker-EET** malgré le nom `timestamp_utc`.
   Side-channel à noter dans le code ; pas bloquant pour ce travail mais important
   pour toute future analyse cross-instrument utilisant ce panel.

---

## 6. Fichiers produits

| Fichier | Rôle |
|---|---|
| `data/raw/NQ_1min_databento_2010-2026.parquet` | **Le parquet propre — drop-in pour ORB engine** |
| `data/metadata/NQ_1min_databento_2010-2026.json` | Sidecar metadata (stats, DQ, recon) |
| `data/ftmo_research/output/nq_reconcile_us100.json` | Détails reconciliation NQ futures vs US100 CFD |
| `data/ftmo_research/code/nq_databento_ingest.py` | Pipeline d'ingestion (re-runnable) |
| `data/ftmo_research/code/nq_reconcile_us100.py` | Script de reconciliation (re-runnable) |
| `data/ftmo_research/DATA_NQ_cleaned_report.md` | Ce rapport |

---

## 7. Récapitulatif décisionnel

| Question | Réponse |
|---|---|
| Pipeline sain ? | **OUI** : 0 violation OHLC, 64/64 rolls détectés, 32/32 DST spot-checks OK |
| Reconciliation vs analyse précédente ? | **MATCH** (corr 5-min 0.92, ORB corr 0.95) après fix tz du panel CFD |
| Drop-in pour `orb_core.py` ? | **OUI** — patch documenté §4 ; un seul fichier à éditer |
| Données 2008-2009 ? | **NON** — Databento NQ commence 2010-06-06. Acceptable (couvre 2 chops majeurs 2011, 2015, 2018, 2020, 2022) |
| GER40 inclus ? | **NON** — fetch Databento US100/NQ seul. Phase 2 = Dukascopy DAX |
| Soudure Kaggle ? | **N/A** — décision single-source. Kaggle 2022-2025 obsolète à partir de maintenant |
