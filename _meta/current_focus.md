# Current Focus — Algo_claude
**Last updated**: 2026-06-10
*(Mettre à jour à chaque session. Ce fichier est opérationnel — CLAUDE.md est constitutionnel.)*

---

## Bloquants immédiats

### Strategy B — bascule mainnet (~2026-07-17)
- 60 j live testnet requis (depuis 2026-05-17) ; avant bascule : vérifier notional
  scaling ($500 backtest vs compte réel), critères d'entrée funding (à définir AVANT
  deploy, cf. initial_summary §8), kill switch STOP
- Mesurer swap/funding réel mainnet — prérequis aussi du combined book perso (personal_book)

### VPS — reboot requis + 32 updates (sécurité incluses), uptime 54 j
- Fenêtre proposée : vendredi ≥ 16:30 UTC (hors rebalances B 00:10/08:10/16:10,
  hors Propr lundi 00:05) — procédure + rollback : rapport session 2026-06-10 (M4c)

---

## En cours

### fix_reversal (FX) — migration tz FAITE 2026-06-10, NO-GO confirmé
- Source migrée → deep_history_utc (true UTC 2007-2026) ; anciens résultats invalidés
  (artefacts tz : « Tokyo wide » = rollover broker, levier EOM, émergence 2023+)
- Pattern B segmentation : gross two-sided réel (t=3.55) mais < coût retail →
  L34 candidate à promouvoir (reformulée SANS la clause asymétrie L25)
- Dossier prêt pour archivage + POSTMORTEM après validation L34
- Détail : `Forex/research/active/fix_reversal/FIX_REVERSAL_TZ_MIGRATION.md`

### Portefeuille personnel — re-référencé 2026-06-10
- Book référence = A+B : SR analytique 2.31 ; C dilutif (breakeven SR_C≈0.81) ;
  gate D = 2.54 ; MaxDD book à mesurer sur B mainnet (L14)
- A frozen (Propr breach 05-11) ; HL testnet place encore des fills
- Détail : `_audit/portfolio_recalc_2026-06-10.md`

### Automation
- alpha_hunt : distillation VPS depuis 2026-06-10, chaîne saine (pushes /30 min)
- arxiv : panne 09/06 (race git 06:30 vs alpha_hunt) — patch appliqué session
  2026-06-10 (distillation + flock) ; ⚠ routine cloud à repointer vers
  `_automation/arxiv/_staging/<date>.json`
- Stubs ExitRuleHandler / RegimeFilterHandler toujours REQUIRES_HUMAN

---

## Axes de recherche (par priorité)

| # | Axe | Statut |
|---|-----|--------|
| 1 | FX intraday deepdive (sub-60min FX/XAU/BTC) — SEUL axe propfirm ouvert | actif, N_ledger 240 |
| 2 | Strategy D — D3+D5 portfolio (prereg en cours) | budget 3 mods, 0 consommé |
| 3 | sector_hothand_propfirm (Equities) | audit OBLIGATOIRE (t=10.38 red flag) avant promotion |
| 4 | Commodities XS basis+TSMOM | Phase A non démarrée |
| 5 | ZN Baltussen (bond momentum) | en cours |
| 6 | Token unlocks / VRP short gamma (Crypto) | bootstraps vides |

---

## Décisions pendantes
- L34 (flow-anchored FX = tier institutionnel only) à valider/promouvoir dans CLAUDE.md —
  reformulé post-migration tz (la clause asymétrie L25 saute)
- Propfirm : FTMO Indices CFD = seul véhicule candidat restant (ORB V2+E7 / K5) —
  conditionné à la mesure de coût 15h30 (orb_at_0p4bps : verdict INCERTAIN à 3 bps)
- voie_b_ftmo : sous-jacent mq5 à confirmer manuellement + slip_report.csv à commiter/ignorer
- Panels parquet EET m5_indices : 0 consommateur actif — archivage froid proposé (M1e, rapport 2026-06-10)
- Reddit ×3 alpha_hunt : IP Hetzner bloquée (429 bot-UA / 403 browser-UA) — suppression propre
  vs API OAuth (M4d)
- N_ledger.md (fx_intraday_deepdive) untracked — à commiter
- Secrets crontab → wrapper run_with_env.sh + .env (plan M4a, GO requis)
