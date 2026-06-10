# Checklist migration m5_indices → deep_history_utc (pré-requis suppression P2)

**Objectif** : supprimer les 14 `data/panels/m5_indices/{FX,indices}_M1.csv` (1,7 Go, EET mislabelé UTC,
2022-2025) au profit de `data/deep_history_utc/` (true UTC, 2007→2026-06, spread calibré).
**Statut** : ✅ EXÉCUTÉ le 2026-06-10 soir (P2 complet) — 13 M1 supprimés après vérification
fichier-par-fichier ⊂ deep_history_utc POST-réparation T1-T6. Conservés : US2000_M1.csv (pas de
superset), `*_m1_panel.parquet` EET (code actif), binance/, *_M5.csv, samples, exporters.
Découverte : EURUSD_M1.csv et BTCUSD_M1.csv n'existaient déjà plus (remplacés par les parquet
panels) — fix_reversal cite un CSV absent. RESTE À FAIRE (owner fix_reversal) : migrer vers
deep_history_utc/EURUSD_M1.csv avec l'audit tz ci-dessous ; puis trancher le sort des parquet
panels EET (même logique tz).

## Par consommateur (grep vérifié 2026-06-10)

| Consommateur | Lit | Action requise | Risque |
|---|---|---|---|
| `Crypto/research/active/pairs_btceth_D/validation_D.py` | `m5_indices/binance/{BTC,ETH}USD_M1.csv` | **AUCUNE** — `binance/` est conservé (seule copie crypto M1) | — |
| `strategies/tsmom_v2_propfirm/_breakoutprop_fit.py` | `m5_indices/binance/` | **AUCUNE** (idem) | — |
| `Crypto/research/active/ftmo_twoSided_makeOrBreak/run_kill_test.py` | `m5_indices/BTCUSD_M1.csv` (panel MT5 BTC, racine) | **AUCUNE — MAIS exclure de la suppression** : `BTCUSD_M1.csv` + `BTCUSD_m1_panel.parquet` n'ont PAS de superset dans deep_history_utc (pas de BTC MT5 dedans) | Supprimer ces 2 fichiers par erreur = perte sèche |
| `Forex/research/active/fix_reversal/step0_cost_calibration.py` + `step1_backtest.py` | `m5_indices/EURUSD_M1.csv` | **MIGRER** vers `deep_history_utc/EURUSD_M1.csv` | ⚠ ÉLEVÉ — voir ci-dessous |
| `research/ftmo_portfolio_audit/` (programme CLOS) | m5_indices FX + binance | Aucune migration (verdict figé). Documenter dans son README que la regen nécessitera deep_history_utc après P2 | Reproductibilité de la regen post-P2 |

## ⚠ fix_reversal — le point sensible (NE PAS migrer mécaniquement)

Stratégie de **fixing windows** (Tokyo 00:55 UTC, London 16:00 GMT/BST) → l'alignement horaire EST le signal.
Or `m5_indices/*.csv` a sa colonne `timestamp_utc` en **EET/EEST broker mislabelé UTC** (décalage +2/+3h
selon DST, cf. MANIFEST deep_history). Deux cas :
1. Si le code de fix_reversal traite `timestamp_utc` comme du vrai UTC sans compensation → **les fenêtres
   de fix actuelles sont décalées de 2-3h** et les résultats existants sont à invalider/re-runner.
2. Si une compensation tz existe quelque part → la retirer lors de la migration vers le vrai UTC.

→ Migration = (a) pointer vers `deep_history_utc/EURUSD_M1.csv`, (b) auditer l'hypothèse tz du code,
(c) re-run et comparer : les fenêtres de fix doivent tomber aux heures documentées (vérifiable via
le pattern de volume/spread autour du fix), (d) bonus : échantillon 2007→2026 au lieu de 2022-2025.
**À faire par/avec la session qui possède fix_reversal — pas pendant qu'elle tourne.**

## Fichiers m5_indices : sort prévu en P2 complet

- **SUPPRIMER après migration fix_reversal** : `{AUDJPY,AUDUSD,EURGBP,EURJPY,GBPUSD,GER40,NZDUSD,US100,US2000,US30,US500,USDCAD,USDCHF,USDJPY}_M1.csv` (1,7 Go) + panels dérivés `m1_close.csv`, `m5_{open,high,low,close}.csv` (~140 Mo, régénérables)
- **CONSERVER** : `binance/` (~2,5 Go, seule copie crypto M1), `BTCUSD_M1.csv`, `BTCUSD_m1_panel.parquet`, `*_M5.csv` (6 Mo, à trancher), `sample60d_*` (négligeable), exporters `.mq5/.ex5`
- Fait en P2 partiel 2026-06-10 : `Forex/data/cache/dukascopy_m5/` supprimé (255 Mo — M5 2018-2026 sans
  spread, régénérable par resample de deep_history_utc ou re-download ~12min/paire-an ; consommateurs
  tous archivés/clos : strategy_e, f2, top10_test, audit schema, finalize_B)
