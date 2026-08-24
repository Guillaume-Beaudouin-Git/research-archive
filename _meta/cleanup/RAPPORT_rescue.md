# Rapport de sauvetage des 19 branches GARDER — 2026-08-24

Suite de `_meta/cleanup/RAPPORT_branches.md` (tri des branches, 2026-08-22). Périmètre : les 19
branches classées GARDER (contenu non présent dans `main`, jamais soumises en PR). Pour chacune :
citée quelque part dans le dépôt comme existante (dette de cohérence → remonter) ou livrable fini
(pré-registration + code + résultats + verdict → remonter) ou brouillon (abandonner, le dire ici).

Verdict global : **19/19 REMONTÉES**. Aucune des 19 n'était un brouillon sans verdict — le tri du
2026-08-22 avait déjà filtré ce niveau. Une inexactitude documentaire trouvée en cours de route
(description ZN Baltussen) a été corrigée séparément.

Branche `claude/crypto-audit-2026-05-28` a été éclatée en 6 commits thématiques (crypto-meta,
sr2_hunt, vwap_mr_fade_nq, g1/g2d carry, monti_orb, manual-signal infra) — une seule ligne ci-dessous
la couvre, le détail est dans les messages de commit.

Exclusions par gouvernance data (aucune n'a empêché une remontée, seulement réduit son périmètre) :
`claude/j1-leverage-cap` — `records/*.parquet` + `records/*_events.csv` + `tables/attempts_*.csv`
(≈3,4 Mo de sorties de simulation régénérables par `run_cap.py`) exclus ; code, pré-registration et
tables de résultats agrégés conservés.

## Tableau

| Branche | Contenu | Cité où | Décision | Justification |
|---|---|---|---|---|
| `claude/crypto-audit-2026-05-28` | zn_baltussen (11 fichiers), audit crypto-meta 2026-05-28, sr2_hunt (Equities, 9 phases), vwap_mr_fade_nq (archivé), g1/g2d carry docs, Monti ORB NQ (T0-T6), manual-signal launchd | CLAUDE.md / `_meta/research_active.md` / `_meta/current_focus.md` (zn_baltussen) ; `research_history.md:22` (G1, via POSTMORTEM.md qui cite audit_v1.md) | **REMONTÉ** (6 commits) | zn_baltussen et G1 sont cités ailleurs comme existants ; le reste (sr2_hunt, vwap_mr_fade_nq, Monti ORB) est un livrable fini (prereg/code/résultats/verdict) |
| `feature/iter-11-fast-pivot` | iter_11_fast (variante NQ Tradeify, verdict GO daté 2026-05-26) + copie zn_baltussen (identique par hash à crypto-audit) | zn_baltussen : idem ci-dessus. iter_11_fast : non cité | **REMONTÉ** | livrable fini (prereg + WF + MC sim + verdict) ; verdict antérieur au re-baseline Databento 2026-06-07 et à l'annulation Tradeify 2026-06-10 — conservé comme trace historique, signalé non-actionnable dans le message de commit |
| `claude/h31-cs-fs-dn-test-160` | code (data_prep.py, validation.py) + postmortem.md + pre_spec.md du test #160 | `research_history.md:40` cite `Crypto/research/archived/h31_cs_fs_dn/` (main n'y avait que `results/*.parquet/json`) | **REMONTÉ** | dette de cohérence : le chemin cité existait mais était incomplet (code et récit absents) |
| `claude/asia-23-8-funded` | Gold overnight-drift ASIA_23_8, volet FUNDED-only + stop intraday | non cité dans le dépôt (mémoire utilisateur seulement, hors périmètre) | **REMONTÉ** | livrable fini : prereg + 2 études (challenge + funded) + verdict (c) REJET |
| `claude/soybean-ftmo-feasibility` | Soybean reopen-drift 01:00-07:00 UTC | non cité | **REMONTÉ** | livrable fini : prereg + audit indépendant + verdict (d) NON-VIABLE |
| `claude/overnight-basket-ftmo` | Panier overnight gold+silver+WTI±soybean | non cité | **REMONTÉ** | livrable fini : prereg + audit + verdict (c) NON-VIABLE |
| `claude/overnight-ftmo-improve` | 4 pistes d'amélioration overnight-drift (P0-P3) | non cité | **REMONTÉ** | livrable fini : prereg + 3 tests + verdict global (aucune piste ne débloque) |
| `claude/funded-dynamic-sizing` | Sizing funded dynamique sur coussin réalisé | non cité | **REMONTÉ** | livrable fini : prereg + 6 variantes + verdict (b) statique quasi-optimal |
| `claude/gold-dosing-compare` | Dosage gold ASIA vs or-trend dans le book | non cité | **REMONTÉ** | livrable fini : prereg + audit indépendant + verdict (dosing dilemma prouvé, intégration fermée) |
| `claude/regime-diagnostic` | Diagnostic macro-régime (VIX, dollar, FOMC, jour de semaine) sur les pertes du book | non cité (L54 du registre cite un `regime_overlay_ftmo 07-30` distinct, postérieur) | **REMONTÉ** | livrable fini : prereg (0 essai de stratégie minté, diagnostic pur) + verdict DISPERSED |
| `claude/real-book-metrics-lowcheck` | Audit funded_anatomy + real_metrics compte 3 (gate J1, low-check intraday) | non cité (mémoire utilisateur `real_book_metrics_2026-07.md` / `funded_anatomy_2026-07.md`, hors dépôt) | **REMONTÉ** | livrable fini : audit adversarial author≠auditor + verdict CONFIRM-WITH-CAVEATS |
| `claude/nightly-us100-investigation` | Investigation double-perte nightly US100 (07/07, 07/14) | non cité | **REMONTÉ** | livrable fini : audit + verdict (a) VARIANCE |
| `claude/vm-sweep-study-2026-06-17` | Sweep du multiplicateur vm sur le container Swing 2-step | non cité | **REMONTÉ** | livrable fini : prereg + verdict GARDER vm14 |
| `claude/trend-futures-sleeve` | Sleeve trend multi-asset daily sur futures non-crypto (funnel P1-P4 + DSR) | non cité (mémoire utilisateur `trend_futures_nogo_2026-06.md`, hors dépôt) | **REMONTÉ** | livrable fini : prereg + funnel complet + verdict NO-GO clean kill |
| `claude/j1-leverage-cap` | Cap de levier J1 (USDJPY), 4 arms + Q4 caveat live | non cité | **REMONTÉ** (partiel, records/attempts exclus) | livrable fini : prereg + verdict ADOPT LCAP8 (backtest) + caveat Q4 non résolu (cap seul insuffisant en live) — signalé explicitement dans le commit |
| `claude/breakout-container-combine` | Sleeve breakout à skew positif, test de la logique « container » funded | non cité | **REMONTÉ** | livrable fini : prereg + verdict (b) DILUE |
| `claude/audit-month-end-20260712` | 3 audits adversariaux : month-end bounce BTC/FTMO, BTC comme 5e actif, portage path-aware du book | non cité (sujet distinct de `Multi_Asset/research/active/month_end_vehicle_2026-07/`, qui porte sur ZN/bonds) | **REMONTÉ** | livrable fini : 2 pré-registrations gelées + audits + 3× verdict NO-GO |
| `claude/ftmo-seam-ger40-investigation` | Investigation seam GER40 (96.7 bps) | non cité | **REMONTÉ** | livrable fini, lecture seule, conclusion actée (impact reconcile = 0) ; non superseded par le fix Monday-restamp (bug distinct) |
| `claude/ftmo-seam-realign-2026-06-19` | Outil de réalignement D1 indices (EEST) + rapport avant/après | non cité | **REMONTÉ** | livrable fini (outil + mesure avant/après), explicitement EN ATTENTE DE GO — remonté à l'état « préparé, non déployé », aucune application au book live |

## Correction documentaire connexe

`_meta/research_active.md:32-33` décrivait ZN Baltussen comme contenant `tests/, sigma_estimation/` —
`sigma_estimation/` n'a jamais existé dans le contenu réel remonté (11 fichiers : prespec.md,
feasibility.py, data_setup.py, analysis/, tests/). Corrigé pour refléter le contenu effectif et son
statut réel (FEASIBILITY, canary 1h Sharpe HAC -11.7, full backtest 1-min jamais lancé faute des
données payantes FirstRateData).

## Non touché

Les 3 branches « À TRANCHER PAR L'HUMAIN » (`backup-pre-rebase-2026-06`, `claude/g1-archive-20260526`,
`claude/cleanup-untracked`) sont hors périmètre de cette mission — aucune action prise. Aucune branche
supprimée, aucun chemin de production déplacé/renommé/supprimé, aucun réécriture d'historique.
