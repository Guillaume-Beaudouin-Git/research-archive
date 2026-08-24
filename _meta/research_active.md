# Active research — inventaire détaillé (vérifié 2026-05-30)

Sorti de `CLAUDE.md` §Research history (2026-07-30) pour tenir sous la limite de chars Claude Code.
Contenu intégral, aucune info perdue. `CLAUDE.md` conserve la LISTE des chantiers ; le détail est
ici. État courant / blockers : `_meta/current_focus.md`. Familles fermées : `research_history.md` (racine).

- **Strategy D — D3+D5 portfolio** (Futures, propfirm-targeted, decorrelated to C) : D3 (Opening
  range mid-fade 09:45-11:00, n_test=156, corr_C=-0.21) + D5 (Afternoon BB squeeze breakout
  14:00-15:30, n_test=158, corr_C=-0.05). Both failed individually (Sharpe=-1.08/-1.32) ; portfolio
  combination + regime filter under study. Pré-reg :
  `Futures/research/active/strategy_d/hypotheses_preregistered.md`. Signals canoniques :
  `Futures/research/active/nq_intraday/analysis/`. Infra paper fusionnée (P2 2026-06-10) :
  `Futures/research/active/strategy_d/infra/` (ex strategy_d_nq). Budget 3 mods, 0 consumed.
- **Commodities XS — Basis + TSMOM** (n≤279) : S_TSMOM (Moskowitz 2012) + S_BASIS (Erb-Harvey 2006),
  24 continuous contracts, monthly CS IC scan. Phase A (data fetch + roll validation) not complete.
  `Commodities/research/active/xs_basis_tsmom/`
- **Voie B FTMO (Strategy A pivot)** — full study EA mq5 + slip_analysis + reconciliation.md.
  `Futures/research/active/voie_b_ftmo/` (26 fichiers, dernière modif 2026-05-29 ;
  results/slip_report.csv dans git status, à commiter ou ignorer). [À CONFIRMER MANUELLEMENT]
  sous-jacent ciblé (mq5 = quel symbole ?).
- **sector_hothand_propfirm (Equities)** — phase 1 baseline + Monte Carlo.
  `Equities/research/active/sector_hothand_propfirm/` (12 fichiers). t_HAC alpha=10.38, SR_net=2.05,
  DSR=2.01, WF 5/5, MDD -13.3%. ⚠ t-stat 10 = drapeau rouge → audit obligatoire avant promotion
  (`_audit/sector_hothand_audit_2026-05-30.md`). MDD -13% > limite FTMO 10% → en l'état BREACH.
- **CIP-EOQ (FX)** — **ARCHIVÉ** : `Forex/research/archived/cip_eoq/` (POSTMORTEM). Copie
  `active/cip_eoq` = doublon exact, supprimée au cleanup 2026-06-10.
- **FX intraday deepdive (sub-60min FX/XAU/BTC)** — `Forex/research/active/fx_intraday_deepdive/`
  (déplacé en P2 depuis research/, cache intact, chemins relatifs ✓). Suite de l'axe laissé ouvert
  par le decision memo FTMO 2026-06-08
  (`PropFirms/ftmo/program_2026-06/PROGRAM_DECISION_MEMO.md` : do-not-fund sur free price data /
  16 instruments / N≈100).
- **ZN Baltussen (Futures)** — last-30-min momentum en ZN, Baltussen-Da-Lammers-Martens 2021 JFE.
  `Futures/research/active/zn_baltussen/` (prespec.md, feasibility.py, data_setup.py, analysis/,
  tests/ — remonté 2026-08-24, absent de main depuis le nettoyage de branches ; canary 1h yfinance
  Sharpe HAC -11.7, full backtest 1-min jamais lancé faute des données payantes FirstRateData).
  Statut réel : FEASIBILITY, pas de résultat exploitable pour l'instant.
- **NQ intraday VWAP (Strategy D iter_01)** — **ARCHIVÉ en P2** :
  `Futures/research/archived/nq_intraday_vwap/` (verdict « FAIL — INSUFFICIENT SAMPLE, N=19 over
  3 years », n_tests=130).
- **Token unlocks (Crypto)** — bootstrap seul, vide.
  `Crypto/research/active/token_unlocks/_bootstrap_notes.md`.
- **VRP short gamma (Crypto)** — bootstrap seul, vide.
  `Crypto/research/active/vrp_short_gamma/_bootstrap_vrp_notes.md`.

## Strategy C — détails opérationnels archivés (projet propfirm ANNULÉ 2026-06-10)
- Signal : direction of 09:30-09:45 ORB, entry at 09:46 ET. Filters : VWAP confirmation + gap < 1.2%
  + opening range ≥ 30pts + $400 SL cap. TP 1.5R | SL min(0.5R, 20pts) | Time stop 12:30 ET.
- Backtest HISTORIQUE (Kaggle 2022-2025, $19 RT) : Sharpe 1.52, MaxDD -13.4%, WF 78% (7/9), N=346 —
  PÉRIMÉ.
- Infra conservée (réutilisable) : `Futures/live/strategy_c_live/` (Tradovate client, signal_engine,
  guardrails), sizing_policy.md, PropFirms/tradeify/rules.md. Piste FTMO CFD distincte :
  `Futures/live/orb_floor_ftmo/` (voir DEPLOYMENT.md).
- [OBSOLÈTE 2026-06-10] Tradeify constants : eval_DD=$1,000 funded_DD=$1,000 lock=$26,100
  floor=$25,100 (confirmé 2026-05-25).
- [OBSOLÈTE] VPS cron paper `25 13/14 * * 1-5` — jamais installée (vérifié 2026-05-30) ; aucune cron
  NQ paper `25 13 * * 1-5` / `25 14 * * 1-5` n'existe → Strategy C n'est pas automatisée (cohérent
  avec « execution not started »).
