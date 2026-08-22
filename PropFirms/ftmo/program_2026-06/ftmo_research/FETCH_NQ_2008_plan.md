# NQ 1-min 2008→2025 — Plan d'acquisition et de soudure propre

> **Statut** : PLAN + SCAFFOLDING. Aucun téléchargement déclenché par ce document.
> L'utilisateur exécute le fetch lui-même après lecture.
>
> **Pré-existant** : `data/raw/NQ_1min_2022-12-26_2025-12-11.parquet` (Kaggle, déjà ingéré
> via `data/cache.py::load_nq_1min()`).
> **Manquant** : 2008-01 → 2021-12 (~14 ans).
> **Objectif** : étendre `load_nq_1min` à 2008-2025 **drop-in**, sans corrompre la queue 2022-2025
> par un raccord silencieusement décalé en fuseau/feed (cf. leçon EURGBP, rapport audit
> `verification_2026-05-30.md` : +9.4R t≈48 = artefact MT5+Dukascopy mal souclés).

---

## 1. Recommandation de source

### Comparatif (vérifications à confirmer au moment du fetch — providers évoluent)

| Source | Coût | Profondeur 1-min NQ | Continuous | Roll-dates | Tz par défaut | RTH+ETH | Format |
|---|---|---|---|---|---|---|---|
| **firstratedata.com** | ~$200 one-shot (lifetime+updates +$N) | **2008-01+** affiché sur fiche NQ | back-adjusted **fourni clé en main** (option ratio-adjusted dispo) | métadonnées roll-date téléchargeables séparément | **US/Eastern wall-clock** | les deux, fichier ETH séparé | CSV plat |
| IQFeed (DTN) | $80-150/mo abonnement | ~2007+ via depth fetcher | front-month OU continuous selon config user | gestion roll dans l'app | exchange tz (CT par défaut, configurable) | les deux | flux propriétaire → CSV |
| Polygon.io | $29-200/mo | NQ futures sur tiers supérieurs, profondeur ~2018 seulement | back-adjusted dispo | métadonnées API | UTC ISO8601 | les deux | JSON/Parquet |
| CME DataMine | ~$50-500/an par produit | tick + 1-min depuis ~2007 (archive brute exchange) | **aucun continuous** — front-month brut, user construit | brut, user calcule | exchange time (CT) | les deux | CSV/binaire, volumineux |
| databento.com | pay-per-query (~$100-300 estimé pour NQ 1-min 2008-2021) | 2008+ via archive CME MDP3 | back-adjusted ET raw fournis | exposés | UTC ns | les deux | DBN/CSV/Parquet |

### Recommandation : **firstratedata.com**

Raisons :
1. **Coût/qualité** : meilleur ratio pour un usage one-shot recherche. Pas d'abonnement
   continu à gérer.
2. **Back-adjusted continuous prêt à l'emploi** : pour l'ORB qui travaille en points
   intraday relatifs à l'open 09:30 ET, le back-adjustment ne change que le NIVEAU absolu
   (sans effet sur la mécanique ORB) — et préserve les moves intraday sur chaque journée.
   La discontinuité de niveau aux roll-dates est *entre* les sessions, pas dans
   l'intra-session.
3. **Tz US/Eastern wall-clock** : conforme à la convention Kaggle déjà en place →
   aucun reformatage requis, et surtout pas de re-conversion sujette à off-by-one DST.
4. **Roll-dates métadonnées séparées** : permet la politique "skip roll days" au backtest
   sans rebuilder la série.

### Alternative si budget : databento

Plus cher mais : (a) timestamps UTC ns = source de vérité immune au DST, (b) raw + adjusted
côte à côte = audit possible des roll-mécaniques, (c) refresh scriptable. Surcoût justifié
si l'on prévoit de tester aussi ES/ZN/CL sur 2008+ (économies d'échelle providers).

### À NE PAS retenir

- **CME DataMine** : raw front-month uniquement. Le coût caché = construire le continuous
  back-adjusted soi-même, c'est plusieurs jours d'ingénierie + risque de bugs aux jonctions.
  Ré-inventer ce que firstrate vend $200.
- **Polygon** : profondeur futures réelle ne descend pas à 2008 sur les tiers raisonnables.
- **IQFeed** : abonnement non amorti pour un one-shot.

---

## 2. Roll dates et continuité (gotcha #1)

### Mécanique NQ

Contrats trimestriels Mar/Jun/Sep/Dec (H/M/U/Z), expiration 3ème vendredi du mois.
Roll de fait : ~jeudi/vendredi de la semaine précédant l'expiration (volume crossover).
Sur 2008-2021 ≈ 56 dates de roll attendues (4 × 14 ans).

### Politique pour l'ORB

Pour l'ORB (signal/exit intraday en points relatifs au 09:30 ET) :

- **Niveau absolu** : non pertinent (back-adjustment OK).
- **Intra-session du roll-day** : doit être sur **un seul** contrat. Si le provider roll
  "after close" ou "before open" → OK. Si roll mid-session (très rare chez les providers
  pros) → risque de saut artificiel intra-OR.
- **Open 09:30 ET du roll day vs close 16:00 ET du roll day** : le gap entre les deux peut
  inclure une discontinuité d'ajustement chez certains providers. Le ORB n'utilise pas ce
  gap, mais le verification log doit le détecter pour confirmer.

### Politique retenue

1. **Charger la liste des roll-dates** depuis les métadonnées firstrate (fichier
   séparé) OU via `pandas_market_calendars.CMEFutures` (open source) pour cross-check.
2. **Backtest** : flag `skip_roll_days=True` exposé dans le moteur ORB. Par défaut
   skip → on perd 56/3640 = 1.5% des jours, négligeable, sécurise contre artefacts.
3. **Détection d'anomalie** (script `nq_roll_audit.py`) :
   - Pour chaque date où on a métadonnée roll : vérifier que `open[09:30]` du roll day
     se situe dans `[low, high]` de la session précédente. Si écart > 1.5σ du gap-distribution
     historique → flag.
   - Scan global : tout jour où `|open_09:30 - close_prev_16:00| > 2%` ET non listé
     comme roll-day = artefact suspect → audit manuel.
4. **Audit trail** : produire `data/ftmo_research/output/nq_roll_anomalies_2008_2021.csv`
   au moment de l'ingestion, **commit** ce fichier (petit, audit).

### Code de détection (squelette)

Voir `data/ftmo_research/code/nq_roll_audit.py` (scaffolding, fourni à la fin de ce plan).

---

## 3. Fuseau et DST (gotcha #2)

### Convention

- **Cash open NQ** : 09:30 America/New_York wall-clock.
- **Globex** : 18:00 ET (J-1) → 17:00 ET (J), pause 17:00-18:00. ORB intraday → on
  ne se sert que de 09:30-16:00 ET (RTH cash).
- **DST US** : 2ème dimanche de mars (saut +1h), 1er dimanche de novembre (recul -1h).
  La fenêtre ambiguë (2 AM dupliqué en novembre) n'intersecte PAS 09:30 → pas de
  problème direct sur l'OR.
- **DST EU vs US** : décalées de ~3 semaines/an (mars : US bouge avant EU ; octobre/novembre :
  EU bouge avant US). Si live exécution depuis VPS CET/CEST, on convertit toujours
  UTC → ET — **jamais utiliser le temps système local pour piloter une cron NQ**
  (gotcha live, hors scope de ce fetch, mais à noter dans le moteur).

### Convention retenue à l'ingestion

Tous les loaders renvoient un index `pd.DatetimeIndex` **tz-aware `US/Eastern`** (=
ce que `load_nq_1min` fait déjà avec `ambiguous='infer'` sur la série Kaggle).

Selon la source :
- **firstrate (US/Eastern wall-clock)** : `tz_localize('US/Eastern', ambiguous='infer',
  nonexistent='shift_forward')` — identique au code Kaggle existant → pas de divergence.
- **databento / Polygon (UTC)** : `tz_localize('UTC').tz_convert('US/Eastern')`.
- **CME DataMine (CT)** : `tz_localize('US/Central').tz_convert('US/Eastern')`.

Le QA de soudure (§4) **vérifiera empiriquement** la convention déclarée — ne JAMAIS
faire confiance à la doc seule.

### Code de normalisation (squelette)

```python
def normalize_nq_timestamps(df: pd.DataFrame, source_tz: str,
                            ts_col: str = "timestamp") -> pd.DataFrame:
    """Renvoie df indexé tz-aware US/Eastern, ambiguous='infer'.

    source_tz: 'US/Eastern' | 'UTC' | 'US/Central' | 'Europe/London' ...
    """
    ts = pd.to_datetime(df[ts_col])
    if source_tz == "US/Eastern":
        ts = ts.dt.tz_localize("US/Eastern",
                               ambiguous="infer",
                               nonexistent="shift_forward")
    else:
        ts = ts.dt.tz_localize(source_tz).dt.tz_convert("US/Eastern")
    out = df.drop(columns=[ts_col]).copy()
    out.index = ts
    out.index.name = "timestamp_et"
    return out.sort_index()
```

---

## 4. QA de soudure (le garde-fou EURGBP) — CRITIQUE

### Principe

Le verification log a déjà chopé un faux positif (+9.4R t≈48 sur EURGBP) causé par un
mixage MT5+Dukascopy mal-aligné. Pour la même raison, un fetch firstrate 2008-2021
souclé naïvement au Kaggle 2022-2025 peut produire un *faux signal* indétectable
par les statistiques agrégées.

**Règle** : la soudure n'est pas optionnelle, n'est pas un nice-to-have post-fetch, c'est
le **garde-fou bloquant** avant que les données entrent dans le moteur.

### Cinq tests obligatoires, sur la fenêtre de chevauchement Kaggle ∩ firstrate

La plupart des providers (firstrate inclus) couvrent **aussi** 2022-2025. **Acheter le pack
qui inclut le chevauchement** est essentiel — c'est ce chevauchement qui donne la
preuve empirique de la soudure.

#### Test 1 — Alignement de fuseau via volume spike 09:30 ET

Pour chaque journée du chevauchement :
- Identifier `argmax(volume)` dans la fenêtre `[09:25, 09:35] ET` côté Kaggle et côté nouvelle source.
- **Assertion** : ≥ 98% des jours doivent matcher à la minute exacte.
- 0 jour ne doit dévier de plus de ±1 minute.
- Si fail → `source_tz` mal déclaré, ABORT.

#### Test 2 — Cohérence de niveau de prix sur les bars communs

Pour chaque minute commune :
- `r_kaggle = close_kaggle.pct_change()`, idem `r_new`.
- `corr(r_kaggle, r_new)` sur la fenêtre de chevauchement.
- **Seuil** : corrélation des returns 1-min > 0.999 (= même série modulo arrondi).
- Note : les LEVELS peuvent différer (back-adjustment différent). C'est OK. Les RETURNS
  intraday ne doivent pas — sauf jour de roll (à isoler).

#### Test 3 — Sanité OHLC

- `(high >= max(open, close)) & (high >= low)` : 100% True.
- `(low  <= min(open, close)) & (low <= high)` : 100% True.
- `volume >= 0` : 100% True.
- 0 violation, sinon corruption du dump.

#### Test 4 — Reproduction d'une stat connue

Sur la fenêtre 2022 disponible dans les deux sources :
- Recalculer **mean ORB range** = `mean(high[09:30:09:45] - low[09:30:09:45])` jour à jour.
- Recalculer **hit-rate 1.5R TP** pour le signal iter_10 (entry 09:46, SL min(0.5R, 20pts),
  TP 1.5R, time stop 12:30) — métrique publique du backtest Strategy C.
- **Tolérance** : nouvelle source doit matcher Kaggle à < 0.5% sur mean ORB range, et
  < 2 pts de % sur hit-rate (sur ~250 trades/an, σ ~= 3 pts).
- Si fail → divergence de définition de "bar 09:30" (timestamp = début ou fin de bar ?).

#### Test 5 — Bar-count par session RTH

- Session RTH 09:30-16:00 ET = 390 minutes. Chaque trading day doit avoir **≥ 388 bars
  dans cette fenêtre** (tolérance halt/fast-market ≤ 2 bars manquants).
- Holidays partiels (Black Friday, Christmas Eve) : pre-flag via `pandas_market_calendars.CMEEquity` et exclure de ce test.
- Histogramme bar-count → 0 jour suspect en dehors de [388, 391].

### Décision

| Résultat | Action |
|---|---|
| Tous tests PASS | Génère seam metadata, autorise le merge, écrit `data/raw/NQ_1min_2008-2025_MERGED.parquet` |
| ≥ 1 test FAIL | **ABORT MERGE**. Écrit `data/ftmo_research/output/seam_qa_FAIL_<date>.md` avec diagnostic. Loader refuse de servir `source='merged'`. |

### Code QA (scaffolding complet)

Voir `data/ftmo_research/code/nq_seam_qa.py` (fourni à la fin, runnable une fois le
parquet historique en place).

---

## 5. Ingestion dans le pipeline existant — Plan drop-in

### État cible

```
data/raw/
├── NQ_1min_2008-XX-XX_2021-12-31.parquet      # NOUVEAU : firstrate historique
├── NQ_1min_2022-12-26_2025-12-11.parquet      # EXISTANT : Kaggle (inchangé)
└── NQ_1min_2008-2025_MERGED.parquet           # NOUVEAU : généré par le QA si PASS

data/metadata/
├── NQ_1min_2008-XX-XX_2021-12-31.json         # métadonnée source firstrate
├── NQ_1min_2022-12-26_2025-12-11.json         # existant
└── NQ_1min_2008-2025_MERGED.json              # métadonnée merge + résultat QA

data/ftmo_research/output/
├── nq_seam_qa_<date>.md                       # rapport QA (committé)
└── nq_roll_anomalies_2008_2021.csv            # audit roll-days (committé)
```

### Extension de `load_nq_1min`

Signature étendue, **rétrocompatible** :

```python
def load_nq_1min(path: str | None = None,
                 source: str = "merged") -> pd.DataFrame:
    """
    source:
      - 'kaggle'     → 2022-2025 uniquement (= comportement legacy)
      - 'historical' → 2008-2021 uniquement (firstrate)
      - 'merged'     → 2008-2025 souclé. Refuse si le rapport QA n'est pas PASS.
                       Devient le défaut après validation de la soudure.
    """
```

**Garde-fou API** : `source='merged'` lit la sidecar `NQ_1min_2008-2025_MERGED.json` et
vérifie le champ `seam_qa_status == "PASS"`. Sinon lève `RuntimeError(...)` avec lien
vers le rapport. Aucun chemin silencieux.

### Impact sur le moteur ORB

`data/ftmo_research/audit/orb_core.py::_load_m5` charge actuellement US100 depuis
`m1_panel.parquet` (panel CFD MT5). Pour brancher NQ futures :

```python
@lru_cache(maxsize=8)
def _load_m5(symbol: str) -> pd.DataFrame:
    if symbol == "NQ":
        # Drop-in : charge le merged 2008-2025
        from data.cache import load_nq_1min
        df = load_nq_1min(source="merged")
        df = df[["open", "high", "low", "close"]].copy()
        # orb_core travaille en tz-naive — convertit US/Eastern → naive ET
        df.index = df.index.tz_localize(None)
    elif symbol in ("US100", "US500", ...):
        # comportement existant
        ...
    return df.resample("5min").agg({...}).dropna()
```

Le reste de `orb_core` est inchangé (resample 5min, fenêtrage horaire, calcul R).
Les sleeves NQ deviennent disponibles via :

```python
("NQ", 9, 30, 16, 6),   # 30-min OR, RTH US 09:30 ET
("NQ", 9, 30, 12, 3),   # 15-min OR variante
```

### Gitignore

Ajouter (si pas déjà) :
```
data/raw/NQ_1min_*.parquet
data/raw/NQ_1min_*.csv
!data/ftmo_research/output/nq_seam_qa_*.md
!data/ftmo_research/output/nq_roll_anomalies_*.csv
```

Les CSV bruts et parquets ne sont pas commités (taille + propriété data).
Les rapports QA / audit roll sont commités (audit trail).

---

## 6. Checklist de validation — à cocher avant d'utiliser 2008-2025

- [ ] **OHLC violations = 0** sur `NQ_1min_2008-XX-XX_2021-12-31.parquet` (Test 3).
- [ ] **Liste des roll-dates** extraite : 56 dates attendues (4 × 14 ans, 2008-2021).
       Comparée à `pandas_market_calendars.CMEFutures` → match.
- [ ] **DST spot-checks** : sur chaque (J-DST-+1) de mars 2008-2021 (14 dates) et chaque
       (J-DST-+1) de novembre 2008-2021 (14 dates), vérifier que le bar `09:30:00 ET`
       existe ET correspond à `13:30 UTC` (heure d'été) ou `14:30 UTC` (heure standard).
       0 erreur tolérée.
- [ ] **Soudure QA** : 5 tests PASS (§4). Rapport `nq_seam_qa_<date>.md` committé.
- [ ] **Bar-count par session** : 0 jour avec < 388 bars dans 09:30-16:00 ET hors
       holidays partiels listés.
- [ ] **Reproduction sur chevauchement** : metrics 2022 iter_10 (mean R, hit-rate,
       Sharpe daily) reproduisent sur la nouvelle source dans la tolérance §4 Test 4.
- [ ] **Sidecar metadata** : `NQ_1min_2008-2025_MERGED.json` contient
       `seam_qa_status: PASS`, hash du rapport QA, liste des roll-days, version du
       générateur.
- [ ] **Loader fonctionne** : `load_nq_1min(source='merged')` retourne 2008-01 → 2025-12,
       index strictement croissant, 0 doublon.
- [ ] **Moteur ORB consomme** : `orb_daily_R("NQ", 9, 30, 16, 6)` tourne sans erreur
       sur la fenêtre 2008-2021 ET reproduit sur 2022-2025 les chiffres déjà connus.

---

## 7. Note DAX 2008-2025 (Phase 2)

### Statut

Pas inclus dans ce plan d'exécution — flagé Phase 2 après que NQ pipeline ait atterri.

### Disponibilité Dukascopy

- **Décodeur réutilisable** : `Forex/research/archived/strategy_e_fix_flow/data_setup.py`
  (déjà testé, fetch ~12min/pair-année à 4 threads).
- **Index Dukascopy** : profondeur typique pour DEUIDXEUR (DAX cash) ≈ 2010-2018.
  **À confirmer** par canary fetch sur 2011-01 et 2008-01 avant d'engager.
- Si 2010+ seulement : couvre les chops 2011 et 2015 → suffisant pour ajouter √N
  à la mesure de Strategy 2 sleeves GER40.
- Si 2008-2009 manquant : chercher alternative (Tickdata.com, $$$) ou accepter le gap.

### Gotchas spécifiques DAX

- **Open DAX 09:00 CET** (= 08:00 UTC standard, 07:00 UTC summer). La conversion
  CET/CEST→UTC est gérée par `data_setup.py` via `ZoneInfo("Europe/Paris")`.
- DST EU/US désalignée (§3) → pour les sleeves GER40 @ 16:30 EET qui sont **réactifs
  à l'open US cash 09:30 ET**, le décalage entre les deux DST peut faire que sur
  ~3 semaines/an la fenêtre EET 16:30 NE correspond PAS à 09:30 ET. C'est **un piège
  réel** du backtest cross-source à documenter.
- Dukascopy = CFD spread, pas futures. Pour ORB intraday (points relatifs à l'open
  du jour), magnitude des stops/TPs sera différente vs futures FDAX réel. À mesurer
  empiriquement vs FDAX si disponible plus tard.

### Plan d'action minimal (Phase 2, après NQ)

1. Canary fetch DEUIDXEUR 2011-01 et 2008-01 via le décodeur existant → confirmer
   profondeur disponible.
2. Fetch complet 20XX-2025 (selon profondeur) → cache dans
   `data/raw/dukascopy_GER40_<start>_<end>.parquet`.
3. QA de soudure GER40 nouvelle source vs `m5_indices/GER40_m1_panel.parquet` existant
   (qui est MT5) — mêmes 5 tests que §4 NQ.
4. Ne pas merger DAX MT5 + Dukascopy si soudure FAIL — c'est exactement le scénario
   EURGBP qui a corrompu le verification log.

---

## Annexe A — Scaffolding du QA de soudure

Fichier `data/ftmo_research/code/nq_seam_qa.py` (fourni séparément, runnable
une fois `NQ_1min_2008-XX-XX_2021-12-31.parquet` en place).

Usage prévu :
```bash
/usr/bin/python3 data/ftmo_research/code/nq_seam_qa.py \
    --historical data/raw/NQ_1min_2008-XX-XX_2021-12-31.parquet \
    --kaggle     data/raw/NQ_1min_2022-12-26_2025-12-11.parquet \
    --overlap    2022-12-26:2023-12-31 \
    --out        data/ftmo_research/output/nq_seam_qa_$(date +%F).md
```

Sortie : rapport markdown + exit code 0 (PASS) / 1 (FAIL).

## Annexe B — Scaffolding extension loader

Fichier `data/ftmo_research/code/nq_loader_ext.py` (fourni séparément, à intégrer
dans `data/cache.py` après QA PASS).

---

## Récapitulatif décisionnel

1. **Source** : firstratedata.com $200 one-shot (alternative haut de gamme : databento).
2. **Roll-days** : skip par défaut au backtest, audit séparé.
3. **Tz** : tout en `US/Eastern` tz-aware via `tz_localize/tz_convert` selon convention
   déclarée par la source — **vérifiée empiriquement** par le QA.
4. **Soudure** : 5 tests bloquants. Sans PASS, le loader refuse de servir le merged.
5. **Drop-in moteur** : ajouter une branche `symbol == "NQ"` dans `_load_m5` qui appelle
   `load_nq_1min(source='merged')`. Le reste du moteur est inchangé.
6. **DAX** : Phase 2, après NQ. Décodeur Dukascopy existant réutilisable.
