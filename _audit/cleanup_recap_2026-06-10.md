# Récap cleanup P0+P1 — 2026-06-10

Rollback possible : tag git `pre-cleanup-2026-06-10`. Commits **locaux uniquement** (rien n'a été pushé).

---

## 1. Ce qui a été exécuté

### Commits créés (branch main)
| Commit | Contenu |
|---|---|
| `b8aa9f0` | **Pré-cleanup** : mise sous git du code untracked — `Futures/live/orb_floor_ftmo/` (code live qui n'était PAS dans git), 5 dossiers `PropFirms/ftmo*`, `fix_reversal`, `pairs_btceth_D`, `ftmo_twoSided_makeOrBreak`, `ftmo_3strats_audit_2026-06` (hors parquet 27 Mo), downloaders Forex, `slip_report.csv` voie_b, docs `_audit/` mai-juin, `engine.py` modifié (slippage $19→$29 RT), `_downloads_logs/`. 221 fichiers. |
| `a3f1cea` | **Cleanup P1** (détail ci-dessous) |
| `adde631` | Entrée STRATEGY_RESEARCH_LOG « Backwardation Oil NO-GO » (écrite par ta session parallèle, préservée telle quelle) |
| `0594005` | ⚠️ commit arrivé **pendant** le cleanup, par une **session parallèle** (étude backwardation_oil). Aucun conflit avec les suppressions — vérifié. |

### Supprimé (P0 — hygiène, ~30 Mo)
34 `.DS_Store` · 74 dossiers `__pycache__` · `.pytest_cache/` · `data/deep_history_m1/_tool/node_modules/` (7,3 Mo, `npm i` le recrée) · `engine.py.bak_2026-06-07` + `results.json.bak_2026-06-07` (anciennes versions dans git HEAD) · `process_raw_filter.py.bak` · `oxfordstrat .git/index.lock.bak`

### Supprimé (P1 — doublons, ~880 Mo)
| Quoi | Taille | Canonique conservé |
|---|---|---|
| `_automation/alpha_hunt/_raw/` : sorti de git (git rm --cached, 2 481 fichiers) + purge >7 jours | 722 Mo | dédup logique `_seen.json` ; 683 pulls récents (268 Mo) restent sur disque, désormais gitignorés |
| `data/raw/dukascopy_{EURUSD,GBPUSD}_2020..2024.parquet` (10 annuels) | 86 Mo | `dukascopy_*_2020_2024.parquet` (agrégés) |
| `data/raw/yf_*_1d_*.parquet` | ~5 Mo | caches funnel 2007→2026 (régénérables yfinance) |
| `research/s076_replication/daily/*_EET.parquet` | 4 Mo | `*_UTC.parquet` (tz corrigée) |
| `Forex/research/active/cip_eoq/` (git rm) | 3 Mo | `Forex/research/archived/cip_eoq/` (identique + POSTMORTEM) |
| `graphify-out/` | 1,7 Mo | régénérable |
| caches programmes FTMO **clos** : `ftmo_candidate_funnel{,_v2}/cache`, `paper_triage/cache` | 37 Mo | régénérables depuis `deep_history_utc` ; cache du programme **actif** `fx_intraday_deepdive` intact |

### Bonus inattendu : `.git` 2,1 Go → **52 Mo**
`git gc --prune=now` : ~2 Go d'objets **orphelins** (churn des branches claude/* + force-pushes) purgés + repack. **Le `git filter-repo` prévu en P3 n'est plus nécessaire.** Historique intact, aucun rewrite.

### Gitignore — nouvelles règles (commit `a3f1cea`)
```
_automation/alpha_hunt/_raw/
data/deep_history_utc/
data/deep_history_m1/_cache_duka/
data/panels/m5_indices/
data/*.txt
Futures/research/active/ftmo_3strats_audit_2026-06/results/*.parquet
```

### Vérifications post-exécution (toutes ✓)
cip_eoq archived intact · NQ Kaggle parquet intact · `_frozen/` intact · `deep_history_utc` + `binance/` intacts · fichiers live racine intacts · cache fx_intraday_deepdive intact · `pytest` non lancé (aucun code de `strategies/`/`Portfolio/` modifié, seuls ajouts/suppressions de fichiers non importés).

---

## 2. À COLLER dans CLAUDE.md (lignes prêtes)

> ✅ **APPLIQUÉ le 2026-06-10** (validation utilisateur) — sections a, b, c, d intégrées dans CLAUDE.md,
> plus : pivot propfirm **Tradeify ANNULÉ → FTMO (futures/CFD) + Propr (crypto)** répercuté dans
> Strategy C, Portfolio context, lignes Apex (caduc), Data sources (NQ Databento canonique,
> deep_history_utc M1 canonique), registre FX archivé (cip_eoq). Section e (n_tests) laissée à
> l'utilisateur. `_raw` conservé sur décision utilisateur (pipeline vérifié : fiches distillées
> dans `promising/`, derniers runs 01-02/06 « empty » ; flux interrompu depuis le 2026-06-02 — à
> vérifier sur le VPS). Lignes ci-dessous conservées pour référence.

### a) Section « Repo layout » — ajouter :
```
- Data governance (audit 2026-06-10) :
  - data/raw/ = sources immuables + manifest ; data/cache/ + caches projets = régénérables, gitignorés
  - Une série = un fichier canonique (M1 FX/indices : data/deep_history_utc/, true UTC).
    Les dossiers de recherche RÉFÉRENCENT data/, ne copient jamais.
  - Jamais de blobs data dans git (alpha_hunt/_raw gitignoré depuis 2026-06-10).
  - Un subset (plage plus courte) se supprime après migration des consommateurs — SAUF
    provenance d'une stratégie validée (ex: NQ Kaggle parquet = data de validation de C).
- Audit doublons : _audit/dedup_audit_2026-06-10.md ; cleanup P0+P1 exécuté (tag pre-cleanup-2026-06-10),
  P2 (consolidation FTMO/mtf/audits + migration m5_indices→deep_history_utc) NON exécuté — voir §5 du rapport.
```

### b) Section « Active research » — CORRIGER l'entrée CIP-EOQ :
```
- **CIP-EOQ (FX)** — ARCHIVÉ (Forex/research/archived/cip_eoq/, POSTMORTEM.md).
  La copie active/ était un doublon exact, supprimée au cleanup 2026-06-10.
```
Et AJOUTER (programme actif découvert à la racine `research/`, déplacement prévu en P2) :
```
- **FX intraday deepdive (sub-60min FX/XAU/BTC)** — research/fx_intraday_deepdive/ (sera déplacé
  vers Forex/research/active/ en P2). Suite de l'axe laissé ouvert par le decision memo FTMO 2026-06-08
  (research/PROGRAM_DECISION_MEMO.md : do-not-fund sur free price data, 16 instruments, N≈100).
```

### c) ⚠️ Section « Strategy C » — métriques périmées (à valider par toi)
CLAUDE.md affiche `Sharpe 1.52, MaxDD -13.4%, WF 78%, N=346` mais `results.json` (commité, dernière itération `iter_10_databento_rebaseline` du 2026-06-07, $29 RT slippage L19, Databento 2014-2026) donne :
```
- Backtest RE-BASELINE 2026-06-07 (Databento 2014-2026, $29 RT) : Sharpe 0.41 full / 0.69 sur la
  fenêtre Kaggle 2022-2025, maxDD -53.9% acct, N=765. Métriques historiques (Sharpe 1.52, $19 RT,
  Kaggle seul) NON comparables — voir Futures/research/active/nq_intraday/results.json.
```
→ En l'état, C ne passe plus PROPFIRM_PASS (Sharpe>1.0) sur le re-baseline. À réconcilier avant tout paper trade Tradeify.

### d) Section « VPS » — ajouter :
```
- alpha_hunt: _raw/ gitignoré depuis 2026-06-10 — vérifier que la prochaine PR claude/alpha-hunt-*
  n'ajoute plus de XML (si la routine fait `git add -f`, la patcher). Les pulls locaux restants
  (268 Mo, gitignorés) sont purgeables: rm -rf _automation/alpha_hunt/_raw/*
```

### e) Registre n_tests
L'entrée backwardation_oil (session parallèle, commit `0594005`) annonce « program N réconcilié 112 → 115 » (registre programme, distinct du n_tests=321 global). À réconcilier dans ta convention de comptage.

---

## 3. Reste à faire (NON exécuté — sur ton GO)

> ✅ **P2 PARTIEL exécuté le 2026-06-10** (session parallèle encore active → pas de déplacements) :
> `Forex/data/cache/dukascopy_m5/` supprimé (255 Mo) · `_raw` purgé intégralement après traitement
> du backlog (`process_raw_filter.py` : 1 nouveau, 0 accepté — _automation 993 Mo → 2,4 Mo) ·
> checklist de migration m5_indices écrite : `_audit/m5_indices_migration_checklist_2026-06-10.md`
> (à retenir : `BTCUSD_M1.csv` + `binance/` à EXCLURE de la suppression ; **fix_reversal = seul vrai
> bloquant, sensible tz EET→UTC**) · `_cache_duka` (2,2 Go) CONSERVÉ : source brute d'un build vieux
> de 2 jours qui a connu 2 bugs silencieux pendant sa construction — assurance de rebuild, à
> réévaluer quand deep_history_utc aura été consommé sans incident par plusieurs études.

**P2** (½ journée) : migration des 5 consommateurs de `m5_indices` vers `deep_history_utc` (attention tz EET→UTC) puis suppression des M1 FX dupliqués (1,7 Go) + panels dérivés (~140 Mo) · suppression `dukascopy_m5` (255 Mo) · archive externe `_cache_duka` (2,2 Go) · consolidation FTMO → `PropFirms/ftmo/program_2026-06/` · mtf → `Multi_Asset/research/archived/` · `audit/`+`audit-fetch-B/` → `_audit/` · `docs/`+`readme` → archive · oxfordstrat hors de `data/` · `nq_intraday_vwap` → archived. Script : `scripts/cleanup_dedup_2026-06-10.sh p2` (P2_CONFIRM=1 requis).

**P3** (session dédiée, coordonnée VPS) : déplacement des fichiers live racine (`tsmom_live.py`…) vers `strategies/` + mise à jour crons · unification des 3 implémentations du signal TSMOM + test live==backtest. ~~filter-repo~~ plus nécessaire (gc a suffi).

**Divers** : `package.json` racine (artefact npm orphelin, graphify supprimé) — supprimable · `Claude Vault/` (Obsidian) à sortir du repo manuellement · pousser les 4 commits locaux quand tu es prêt.

---

## 4. Note sessions parallèles

Une session a commité (`0594005`) **pendant** le cleanup. Aucun conflit cette fois, mais pour P2/P3 (déplacements massifs de dossiers) : **aucune session parallèle ne doit tourner**. Le tag `pre-cleanup-2026-06-10` permet un rollback complet de la partie git (`git reset --hard pre-cleanup-2026-06-10` — ne restaure PAS les fichiers untracked supprimés).

## 5. Bilan chiffré

| | Avant | Après |
|---|---|---|
| Repo total (avec .git) | ~19 Go | **17 Go** |
| `.git` | 2,1 Go | **52 Mo** |
| `_automation/` | 993 Mo | 271 Mo |
| Fichiers untracked « bruit » git status | ~3 100 | 648 (reste = matière P2) |
| Code live hors git | orb_floor_ftmo + 5 dossiers PropFirms | **0** |

P2 exécutée ajouterait ~2,1 Go (+2,2 Go d'archive externe optionnelle).
