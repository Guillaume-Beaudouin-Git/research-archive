# Personal Book — Registry

> **Statut** : registre, pas une nouvelle recherche. **Aucun chiffre n'est re-mesuré ici.** Toutes les métriques pointent vers leur source canonique.
> **MAJ** : 2026-06-04 (création).

---

## TL;DR

Stratégies **validées** ou **prometteuses** qui ne sont **PAS tradeables FTMO** (= échouent Gate-0 instrument-availability) mais qui sont déployables sur compte courtier réel. L'objet est de séparer proprement deux pipelines :
- les candidats FTMO (challenge propfirm, sous contraintes barrière/daily-DD/univers FTMO),
- le **personal book** (compte courtier classique, sans contrainte d'univers — TLT/IEF/ZN, VXX, perps crypto, HL, etc.).

---

## Organisation

```
data/personal_book/
  README.md          ← ce fichier (index + matrice de statut)
  sleeves/           ← stratégies VALIDÉES (phase 2 complète)
  _candidates/       ← stratégies prometteuses mais non-finalisées (phase 2 incomplète,
                       ou phase 2 complète avec verdict mitigé documenté)
```

### `sleeves/` — validées, déployables hors-FTMO

| Fiche | Edge | Instrument | Source canonique |
|---|---|---|---|
| [`b1_month_end_bond_rally.md`](sleeves/b1_month_end_bond_rally.md) | **Meilleur edge de l'arc skew_research.** Long Treasury 3 derniers j du mois. t=4,65, 23/23 ans positifs, cost-immune (breakeven 12,5 bps/nuit), regime-proof (survit hausse taux 2022+), flow-not-beta (+33,5 bps excès vs +4 baseline), décorrélé −0,03. | TLT / IEF (ETF) ou ZN / ZB (futures Treasury) | `data/skew_research/session_3/exploration_2026-06.md` |
| [`a_tsmom_v3_crypto.md`](sleeves/a_tsmom_v3_crypto.md) | TSMOM long-only BTC/ETH/SOL hebdo, vol-targeted 18 %. SR OOS 1,33, MaxDD −6,9 %. Live mais gelé (Propr breach 2026-05-11). | Crypto perps (Propr, HL, Binance) | `strategies/tsmom_v2_propfirm/` + `CLAUDE.md` |
| [`b_delta_neutral_carry_hl.md`](sleeves/b_delta_neutral_carry_hl.md) | Delta-neutral funding carry sur HL perps. SR backtest 4,10 / proxy live 2,0. HL testnet live depuis 2026-05-17, mainnet pending. | Hyperliquid perps (HL testnet/mainnet) | `strategies/delta_neutral/` + `CLAUDE.md` |

### `_candidates/` — prometteuses mais non-finalisées

| Fiche | Bloc | Pourquoi candidat | Source |
|---|---|---|---|
| [`longvol_vxx_tail_hedge.md`](_candidates/longvol_vxx_tail_hedge.md) | Phase-2 complète. **NON-rentable** en overlay naïf (drag −2,8 %/an pour 1 pp DD). À reconsidérer SI timing VIX/VIX3M (dépasse signal naïf L10). | Skew +1,86 ; corr equity −0,748 ; mais theta bleed dominant. | `MERGE_portfolio_2026-06.md` §5 |
| [`vix_soq_expiry_intraday.md`](_candidates/vix_soq_expiry_intraday.md) | Near-miss daily (t=1,76 sur VIXY < gate 2). Edge réel suspecté **intraday auction SOQ** — non mesurable sans data intraday VIXY/VIX futures. | Skew_horizon +1,43, décorrélé, ~12 évts/an. Le vrai edge vit en granularité SOQ-print. | `session_structural_dislocations/exploration_2026-06.md` |
| [`mr_reversal_1d_spx.md`](_candidates/mr_reversal_1d_spx.md) | Skew daily +0,71 confirmé MAIS **délai+1 collapse SR 0,57→0,08** → exécution close-print non capturable retail. À re-mesurer en open→close avant promotion. | t=3,61 raw, mais asymétrique (long-après-baisse SR 1,11 vs short SR 0,28) ; décay OOS 0,76→0,33. | `session_vol_tail/exploration_2026-06.md` |

---

## Matrice de statut — tout l'arc de recherche

Légende :
- **FTMO** : ✅ tradeable / ❌ Gate-0 instrument / ⚠ partiel (proxy possible mais avec compromis)
- **Perso** : ✅ tradeable compte courtier classique / N-A si non-déployable
- **Statut** : LIVE / VALIDATED / CANDIDATE / DEAD / FROZEN
- **Localisation** : où dans le repo

### A — Stratégies LIVE / déployables (production ou paper-ready)

| Stratégie | FTMO | Perso | Statut | Localisation |
|---|:---:|:---:|---|---|
| Strategy A — TSMOM v3 crypto BTC/ETH/SOL | ❌ (no SOL, no perps funding) | ✅ | **LIVE** (Propr gelé 2026-05-11 ; HL testnet daily) | `strategies/tsmom_v2_propfirm/` |
| Strategy B — Delta-neutral carry HL | ❌ (no HL, no perps) | ✅ | **LIVE** (HL testnet depuis 2026-05-17, mainnet ~2026-07) | `strategies/delta_neutral/` |
| **B1 — Month-end bond rally** | ❌ (no bonds, no ETF) | ✅ | **VALIDATED** (phase-2 complète, à déployer) | [`sleeves/b1_month_end_bond_rally.md`](sleeves/b1_month_end_bond_rally.md) |
| Strategy C — NQ ORB iter_10 (Tradeify $25K) | ✅ (NQ = US100 CFD) | ✅ | **NO-GO** confirmé (validation 2026-06, SR 0,51 sur 16 ans, DSR fail, p(pass) 24 % réel) | `Futures/live/strategy_c_live/` (paper non démarré) |
| ORB V2+E7 / K5 (sweep FTMO US100) | ⚠ (CFD spread 6-10 bps tue) | — | **CLOSED** (placebo proof : K5 100 % = no-bust × unlimited time, pas edge) | `data/ftmo_research/_CANONICAL_STATE.md` |
| TSMOM trend multi-actifs (futures + crypto sleeve) | ✅ (Forex/Indices/Commodities/Stocks/Crypto OK) | ✅ | **CANDIDATE FTMO** (le seul positif validé OOS — voir `_CANONICAL_STATE.md` §⚠ MAJ) | `data/ftmo_research/IDEA_TSMOM.md` |
| D3+D5 NQ intraday combo (Strategy D) | ✅ (NQ) | ✅ | **PRE-REGISTERED** (test OOS pending) | `Futures/research/active/strategy_d/` |

### B — Sleeves skew_research

| Sleeve (session) | FTMO | Perso | Statut | Pourquoi |
|---|:---:|:---:|---|---|
| **B1 dash-for-cash bond** (session_3) | ❌ | ✅ | **VALIDATED** | t=4,65, 23/23 ans, regime-proof, flow-not-beta, cost-immune |
| C1 Pré-FOMC drift (session_3) | ✅ (NQ/indices) | ✅ | **VALIDATED-fragile** | t=2,58 narrow / 1,97 wide, **décay récent 80 %** sur 2023+ (29,8 → 6,1 bp/évt) |
| MR-reversal 1j SPX (session_vol_tail) | ⚠ (ES futures OK, SPY ETF ❌) | ⚠ | **CANDIDATE** | skew +0,71 mais délai+1 SR→0,08 |
| VIX-term carry timé (session_vol_tail) | ❌ (VIXY ETF) | ✅ | DEAD-for-portfolio | SR 0,69 ok standalone, mais corr +0,44 TSMOM = redondant trend, beta+0,26 equity |
| TREND 60j SPX (session_vol_tail) | ✅ (US500 CFD) | ✅ | DEAD | SR 0,11 t=0,57 — sous-significatif |
| VRP short-vol (session_vol_tail) | ❌ (VIXY) | — | DEAD | skew −1,70 natif, cost-killed |
| Long-vol VXX (session_cowork) | ❌ (ETN) | ⚠ | **CANDIDATE (non-rentable naïf)** | skew +1,86, corr −0,748 equity, mais drag −2,8 %/an |
| Donchian breakout (session_cowork) | ✅ | ✅ | DEAD | SR 0,35 IS → 0,18 OOS, swap-killed (L33) |
| XS-momentum basket (session_cowork) | ✅ | ✅ | DEAD | t=1,95, skew −0,16 wrong-profile |
| Carry+trend AQR (session_cowork) | ✅ | ✅ | DEAD (cited) | carry-crash skew−, beta-proxy (L32) |
| VIX expiry SOQ (session_structural_dislocations) | ❌ (VIXY) | ⚠ | **CANDIDATE** | t=1,76 < 2 daily, edge intraday non mesurable |
| Lev-ETF EOD rebalance (session_structural_dislocations) | ✅ (NQ proxy) | ✅ | DEAD | t=1,28-1,73 sous-puissant (et look-ahead attrapé sur variante sale) |
| Index reconstitution flux (session_structural_dislocations) | ❌ | ⚠ | DEAD | dates non-dispo + ETF sectoriels exclus + indice rebalancé net≈0 |
| CIP-EOQ cross-currency basis (session_structural_dislocations) | ❌ | ❌ | DEAD | μ net 1-3 bps ≪ 3×coût 24 bps ; forwards observés payants |
| Dividend futures / ex-div (session_structural_dislocations) | ❌ | ❌ | DEAD | data propriétaire |
| Dispersion (session_vol_tail) | ❌ | ❌ | DEAD | IV options composants non-dispo gratuit |
| Lead-lag cuivre → SP500 (session_crossasset_leadlag) | ✅ | ✅ | DEAD | arbitré tous horizons (t∈[−1,5; +0,3]) |
| Oil term-struct timé (session_crossasset_leadlag) | ✅ | ✅ | DEAD | carry-direction négative t=−2,62 ; inverse mono-épisode 2020 |
| Gold / real-rates (session_crossasset_leadlag) | ✅ | ✅ | DEAD | t=0,53, skew_M −0,43, régime-instable |
| Credit momentum HYG/IEF (session_crossasset_leadlag) | ❌ (ETF) | ✅ | DEAD-no-edge | t=−0,00 ; forme parfaite mais zéro alpha |
| Carry FX G10 hedgé-vol (session_crossasset_leadlag) | ✅ (FX) | ✅ | DEAD (cited archive) | G10 carry dead post-GFC ; L11 3× gate fail |
| TOM multi-actifs (session_3) | ⚠ | ✅ | DEAD | null toutes classes : SPY t=1,0 / TLT t=−0,17 / DBC t=−0,76 / GLD t=1,3 |
| B1b rebalance LS eq-bond (session_3) | ❌ | ⚠ | DEAD | wrong-signed −22,4 bps, t=−1,44, skew −0,78 |
| B3 window dressing fin de Q (session_3) | ✅ | ✅ | DEAD | t=0,40 no-edge |
| B3' réversion début Q (session_3) | ✅ | ✅ | DEAD | t=0,96 |
| Last-hour momentum SPX (session_3) | ✅ | ✅ | DEAD | t=−0,13 |
| Overnight conditionnel −intra×over (session_3) | ✅ | ✅ | DEAD | t=0,27 ; inconditionnel +4,9 t=4,04 mais beta (skew −0,70, archivé) |
| OPEX quad-witching (session_3) | ✅ | ✅ | DEAD | quad-day −25 bps t=−1,96 (short-able mais skew −0,95, mauvais profil) |
| PEAD index/mega-caps (session_3) | ✅ | ✅ | DEAD (archive) | pas de data earnings ; mort large-caps post-2006 |
| Bond momentum proxy (session_vol_tail) | ❌ | ✅ | DEAD | t=−0,07 ; Baltussen intraday data-blocked → actif `zn_baltussen` |

### C — Sleeves trend / autres research streams (référence)

| Sleeve | FTMO | Perso | Statut | Localisation |
|---|:---:|:---:|---|---|
| J1 USDJPY TSMOM + G1 Gold TSMOM book | ✅ (USDJPY = Forex, Gold = Commodity) | ✅ | **NOT-AN-ARTIFACT-dilutif-A-A+B-KEEP-AS-CV** (SR book 0,70 dilue SR 2,36 → 2,31) | `data/trend_research/trend_verification_2026-06.md`, `STRATEGY_RESEARCH_LOG.md` §Trend book |
| Strategy E — WMR Fix + EOM USD Flow | ✅ (FX) | ✅ | DEAD-L23 (regulatory window kill post-BIS 2015) | `Forex/research/archived/strategy_e_fix_flow/POSTMORTEM.md` |
| Strategy G1 — Carry G10 cond VXY+Fed | ✅ (FX) | ✅ | DEAD-L11-3×-gate | `Forex/research/archived/g1_carry_conditional/POSTMORTEM.md` |
| Strategy F2 — Asian Range Breakout LO | ✅ (FX) | ✅ | DEAD-L11b-binary-TPSL | `Forex/research/archived/strategy_f2_asian_breakout/POSTMORTEM.md` |

---

## Réconciliation amont (sources canoniques — ne PAS dupliquer)

- **`CLAUDE.md` (racine repo)** — § Strategy A/B/C, § Methodology lessons L11-L24, § Research history n_tests=321.
- **`data/ftmo_research/_CANONICAL_STATE.md`** — verdict FTMO (ORB clos, TSMOM trend candidate). Source de vérité FTMO.
- **`STRATEGY_RESEARCH_LOG.md` (racine repo)** — log par strategy (Strategy C iter_10 verdict 2026-06, Trend book J1+G1 reconciliation).
- **`data/skew_research/MERGE_portfolio_2026-06.md`** — synthèse cross-session (corrélations 2018-2026, p(funded) par portfolio).
- **`data/skew_research/session_3/exploration_2026-06.md`** — source B1 (PHASE 2 complète).
- **`data/skew_research/session_*/exploration_2026-06.md`** — sources individuelles par session.

**Si un chiffre dans ce dossier diffère d'une source amont** → la source amont gagne, ce dossier doit être corrigé. C'est un registre, pas une re-mesure.

---

## Que vit ici, que ne vit pas ici

| Catégorie | Vit dans `personal_book/` ? |
|---|:---:|
| Stratégie validée FTMO-incompatible (instrument) | ✅ `sleeves/` |
| Stratégie prometteuse FTMO-incompatible, phase-2 incomplète ou verdict mitigé | ✅ `_candidates/` |
| Stratégie validée FTMO-compatible | ❌ → reste dans `Futures/`, `Forex/`, etc., et figure dans la matrice ici pour traçabilité |
| Stratégie morte (DEAD) | ❌ → matrice uniquement, pas de fiche dédiée |
| Stratégie active en recherche (`research/active/`) | ❌ → matrice uniquement |
| Live infra / VPS / brokers | ❌ → `strategies/`, `Futures/live/`, etc. |

---

## Prochaines étapes (suggérées, hors-scope de ce registre)

1. **Déployer B1** : choisir TLT/IEF (ETF compte courtier) vs ZN futures (compte CME). Sizer par trade (~37,5 bps moyenne, std-dev à mesurer broker). Capital ~5-10 % du book ; ~12 trades/an, série quasi-zéro entre.
2. **Réveiller A** : si Apex EOD trailing s'avère viable (cf. `PropFirms/comparison.md`), porter le sleeve crypto-TSMOM hors-Propr. Sinon, garder en attente HL mainnet (B promu d'abord).
3. **Promouvoir B mainnet** : barrière 60 jours live testnet → ~2026-07-17.
4. **MR-reversal phase 2bis** : tester open→close au lieu de close→close. Si l'edge survit, promouvoir en `sleeves/`.
5. **VIX SOQ phase 2bis** : acquérir data intraday VIXY/VIX futures, re-mesurer fenêtre post-print SOQ.
