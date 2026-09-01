# RAPPORT_DONNEES — acquisition FX manquantes pour Dédale (2026-08)

Mandat : livrer GBPJPY (priorité absolue, citée nommément par l'auteur de Dédale
comme porteuse de l'essentiel du rendement avec EURJPY — cf.
`Forex/research/active/dedale_config_2026-08/RAPPORT.md`) + les croix yen restantes
(CADJPY, NZDJPY, CHFJPY) + les croix résiduelles, **avec certification de qualité
prouvée, pas supposée**. Δn_tests = 0 (aucune hypothèse de signal testée ici).

## 0. Source et pipeline

Décodeur réutilisé TEL QUEL : `data/deep_history_m1/duka_m1_backfill.py`
(`_fetch`, `_decode`, `fetch_day`) — c'est le décodeur CANONIQUE qui a produit
`data/deep_history_utc/` (0 mismatch OHLC vs `dukascopy-node`, cf.
`data/deep_history_m1/gate1_decoder_check.py` et
`_audit/2026-06_instrument_schema/MANIFEST_commodities.md`). Endpoint BID+ASK
`candles_min_1.bi5` (candles natives M1, PAS des ticks agrégés) — donc les séries
livrées ici sont du **vrai M1**, pas du M5 relabellisé.

⚠ Vérification du quirk d'ordre d'octets AVANT tout téléchargement (`duka_m1_backfill.py:137-139`) :
le record 24 octets `>iiiiif` se lit `(sec, OPEN, CLOSE, LOW, HIGH, volume)` — **PAS OHLC**. Notre
script `code/download_pairs.py` importe cette fonction directement (pas de réécriture du
décodage), donc hérite de cette correction sans risque de régression. Guard actif dans
`download_year`/`assemble` : toute année avec >0.1% de violations OHLC (`h<o`, `h<c`, `h<l`,
`l>o`, `l>c`, prix ≤0) n'est PAS mise en cache et part dans `_failed/`.

Débit réel mesuré : ~6 min / symbole-année à 5 threads (candles M1 natives = 1
fichier BID + 1 ASK par jour, PAS 24 fichiers/heure comme l'endpoint ticks du
`dukascopy_downloader_m5.py` existant — donc plus rapide que prévu par les notes
de ce dernier). 503 intermittents observés au démarrage de session (proxy Dukascopy
sous charge) — RÉSOLU par retry/backoff déjà présent dans `_fetch` (8 tentatives,
backoff exponentiel plafonné) : succès dès le 2e/3e essai en pratique.

Code : `code/download_pairs.py` (téléchargement + assemblage), `code/quality_checks.py`
(certification), `code/certify_all.py` (orchestrateur qui écrit `certification/<PAIR>.json`).

## 1. Vérification du fuseau horaire (L52/L56) — PROUVÉE, décalage nul

Protocole : téléchargement indépendant EURUSD (5 jours ouvrés, 2024-01-08→01-12,
via notre pipeline) vs `data/deep_history_utc/EURUSD_M1.csv` (référence déjà
établie, extraction grep sur la même fenêtre).

| Métrique | Valeur |
|---|---|
| Barres communes (intersection timestamp exact) | 7 061 / 7 063 (99.97%) |
| Décalage médian (recherche d'alignement ±5 min) | **0 minute** |
| \|close_mine − close_ref\| médian | 1.0e-5 (≈0.1 pip, résiduel bid/tick) |
| \|close_mine − close_ref\| p95 | 5.0e-5 |
| \|close_mine − close_ref\| max | 9.1e-4 |

**Le décalage médian est nul : le fuseau Dukascopy est bien UTC vrai, confirmé au
tick sur un échantillon indépendant.** Les résidus (médiane ~0.1 pip) sont de l'ordre
du bruit BID inter-feed, pas d'un décalage temporel — le test d'alignement par
recherche de shift (−5..+5 min) confirme shift optimal = 0.

Sanity-check méthode supplémentaire (sur données déjà établies, pas une nouvelle
mesure du fuseau mais une validation de `quality_checks.cross_check`) :
EURJPY vs EURUSD×USDJPY sur l'historique complet 2007-2026 (7 241 919 barres
communes) → erreur médiane 0.231 bps, p95 1.99 bps — cohérence de niveau conforme
à ce qu'on attend de trois cotations BID indépendantes (pas simultanées à la
milliseconde près), valide la métrique de cross-check utilisée plus bas.

## 2. Séries acquises — tableau de certification

*(rempli au fil de l'acquisition ; voir `certification/<PAIR>.json` pour le détail
complet par année. Ce tableau est mis à jour en fin de session, pas en temps réel —
consulter les JSON pour l'état le plus frais si la session a été interrompue.)*

| Paire | Période couverte | N barres | Granularité | Décalage fuseau | % flat max (année) | Trous illégitimes | Cross-check médian/p95 (bps) | Statut |
|---|---|---|---|---|---|---|---|---|
| GBPJPY | *(en cours)* | | M1 native | 0 min (pipeline partagé §1) | | | GBPUSD×USDJPY | *(en cours)* |
| CADJPY | *(en cours)* | | M1 native | 0 min | | | USDJPY/USDCAD | *(en cours)* |
| NZDJPY | *(en cours)* | | M1 native | 0 min | | | NZDUSD×USDJPY | *(en cours)* |
| CHFJPY | *(en cours)* | | M1 native | 0 min | | | USDJPY/USDCHF | *(en cours)* |

## 3. Séries certifiées utilisables

*(à remplir)*

## 4. Séries à ne pas utiliser, et pourquoi

*(à remplir)*

## 5. Ce qui n'a pas pu être fait dans cette session

*(à remplir)*
