# Algo_claude — Project memory for Claude Code

## Profil
M1 IEF (Ingénierie Économique et Financière), Univ. Rennes 1. Solo algo researcher. Objectif : hedge fund systématique (CFM/Qube/Squarepoint/Jump après M2). Python vectorisé, pandas/numpy/statsmodels, VPS Linux, HL REST/WS, Propr/Tradovate API. FR + EN.

## Hard rules (NEVER violate)
- Signal at T-1, trade at T. No exceptions.
- Excess returns (vs cash rate), HAC lag-6, AMTP if n_tests > 1.
- Walk-forward ≥5 folds — never single split.
- Daily vol targeting.
- N ≥ 30 instruments for cross-sectional strategies.
- Max 3 modifications per strategy hypothesis.

## Two-tier gates
- RESEARCH_PASS: Sharpe>0.7, MaxDD<-25%, WF>50%
- PROPFIRM_PASS: Sharpe>1.0, MaxDD<-10%, WF>60%

## Costs (round-trip)
- Crypto 0.17% | Futures MNQ ~$2.15 RT (Tradovate) | Equities 0.05-0.10% | FX 0.15% | Commodity futures 0.015%

## Live strategies snapshot

### Strategy A — TSMOM v3 (FROZEN 2026-05-30 — Propr gelé depuis 2026-05-11 ; HL testnet daily place encore des fills)
- Signal: `tanh(cumret_28d / (vol_28d × sqrt(28))).clip(lower=0)`, long-only
- Vol: log returns, 28-bar window, sqrt(365) annualization — MUST match backtest
- Assets: BTC, ETH, SOL | Rebalance: Monday 00:05 UTC (Propr) + daily 00:05 UTC (HL testnet)
- Validation: Sharpe 1.33 OOS, MaxDD -6.9% (source: signal.py:13 docstring ; results.json formel INTROUVABLE)
- VOL_TARGET_LIVE=0.18 | guardrails RUNTIME-ACTIVE Propr: MAX_DAILY_DD=2.8%, MAX_TOTAL_DD=5.5% (execution/__init__.py:46-47). Défaut canonique nouvelles stratégies: `Portfolio/risk/propfirm_canonical.py` (FTMO 5/10). config.py:55-56 (4.5%/9%) = HyroTrader legacy, non consommé en live.
- Status: cron Propr `5 0 * * 1 run_rebalance` installée, sans fill depuis 2026-05-11 16:44 UTC (breach) ; cron HL testnet `5 0 * * *` place encore des fills (logs/fills.csv 2026-05-28 SOL sell).
- Structural ceiling: 39% Propr pass rate (β_crypto floor, 3% daily DD limit). Alternative Apex CADUC 2026-06-10.
- Frozen artifacts: `Crypto/research/archived/_frozen/strategy_a_propr_2026-05-30/` (code+state)

### Strategy B — Delta-neutral carry (HL testnet LIVE since 2026-05-17)
- Pair active au 2026-05-30: HMSTR seule (TST/MEGA historiques, flat). État volatile, ne pas figer ici — voir state.json VPS. Rebalance: every 8h (00:10, 08:10, 16:10 UTC)
- ⚠ **Backtest Sharpe 4.10 / MaxDD -0.52% : CADUC (2026-07-29)** — décrivait une rotation LENTE. Break-even aux coûts réels : SR>0 si hold ≥10j ; à la rotation **LIVE de 8h → SR ≈ -114**. Concordant avec `data/funding_carry/walkforward_results.csv` (folds 8h **0/4 positifs** ; net_sharpe moyen -1.55 sur 29 folds ; carry +325 réel mais price -594, fees -350). WF disponible **3 folds / 94j < hard rule 5 folds ⇒ INADMISSIBLE**. **Aucun Sharpe de B n'est citable** tant qu'un WF ≥5 folds sur la config 8h n'existe pas. Hypothèse vivante : variante à rotation ≥10j (données déjà présentes).
- VIABLE_ASSETS: TST, MEGA, WLD, STX, WIF, BIO, TRUMP, HMSTR
- MIN_VOL_USD=1_000_000 | CARRY_FLOOR_8H=0.0034/(30×3) | NOTIONAL_USD=50
- Kill switch: checks STOP file on each run
- Status: EXECUTION-VALIDATED, mainnet pending (~60-day live required, ~2026-07-17)

### Strategy C — NQ Opening Momentum iter_10 (Tradeify ANNULÉ 2026-06-10 — pas de véhicule propfirm)
- Signal ORB 09:30-09:45, entrée 09:46 ET, VWAP + gap<1.2% + OR≥30pts + $400 SL cap, TP 1.5R, stop 12:30 ET. Détail → `_meta/research_active.md`.
- **RE-BASELINE 2026-06-07** (Databento 2014-2026, slippage $29 RT per L19) : **Sharpe 0.41** full / 0.69 fenêtre Kaggle, maxDD -53.9%, N=765 ⇒ **sous PROPFIRM_PASS**. Le backtest Kaggle 2022-25 (SR 1.52) est **PÉRIMÉ**. Source `Futures/research/active/nq_intraday/results.json`.
- **ANNULÉ 2026-06-10** : FTMO ne supporte pas les futures CME (L22c) ⇒ pas de véhicule. Code et infra conservés, réutilisables.

## Portfolio context
- Personal book: A (TSMOM, paused) + B (HL testnet, mainnet ~Jul 2026)
- Propfirm book: **FTMO (CFD) + Propr (crypto)**. FTMO ne supporte ni futures CME (L22c) ni CFD obligataire (`PropFirms/ftmo/rules.md:135-143`).
  ⚠ **Volet « firmes futures écartées en bloc » du gel 2026-06-10 LEVÉ (2026-07-30, L51)** : il reposait sur un modèle mental ACTIONS (« daily-flat ⇒ pas de tenue multi-jours »), faux pour le CME — daily-flat ne coupe que la pause de settlement, et MyFundedFutures autorise l'overnight sur tous ses plans. Apex / Topstep / MFFU redeviennent **évaluables au cas par cas**, sous le test L53 d'abord (si la marge du lot minimum tient dans le capital perso, le propfirm n'apporte rien).
- **Le compte IBKR personnel est un VÉHICULE DE PREMIÈRE CLASSE, pas un repli** : pas de barrière, pas d'horloge, 100 % du P&L, futures ~0.4 bps RT contre 2-7 bps en CFD retail. Toute stratégie tuée sur le VÉHICULE ou sur le COÛT CFD doit y être re-évaluée (politique de ré-ouverture, §registre L).
- **Book de référence = A SEUL — SR 0.57** (recalc 2026-07-29 : A live BTC/ETH/SOL, rendements **EXCESS**, IC95 **[-0.50, 1.63] — contient zéro**). Fourchette défendable **0.57** (A seul) → **1.85** (A + proxy B optimiste). **L'ancien 2.31 est CADUC** : il combinait SR_A=1.33 (univers **14 coins**, **gross-of-RF** — ni la config live, ni de l'excess ; les séries donnent 1.251 gross / 0.768 excess à 14 coins, **0.566 excess** sur la config live) et SR_B=2.0, proxy d'un backtest non représentatif de la rotation live (cf. Strategy B). Recalcul `Portfolio/admission/`.
- **Admission d'une sleeve : ΔSR_book > 0 au poids ERC**, significatif au **block-bootstrap** (jamais iid), Šidák si essais multiples, **effet minimum détectable rapporté**. ΔSR positif dans le bruit = **UNDERPOWERED, pas PASS**. **L'ancien « 1.10 × SR_book = 2.54 » est ABANDONNÉ** : il exigeait d'un diversifieur qu'il soit un amplificateur de rendement — à ρ=0 il demandait SR≥0.553 quand le seuil correct est **0**, et à ρ=-0.10 il rejetait des sleeves de SR négatif pourtant accrétives ; c'est ce gate qui a laissé le livre MONO. Mesuré sur le livre réel (flat **60.5 %** des jours) : sleeve flat-filling à SR solo 0.62, ρ≈0 → **p(pass) 0.115→0.167 et durée médiane 22j→10j** (vm=14).
- **Pour un challenge, trancher sur Δp(pass) et Δdurée, PAS sur ΔSR.** Outil `Portfolio/admission/` (`marginal.py` = critère + hurdle fermé en ρ ; `barrier.py` = barrières FTMO -5%/-10%, p(pass), durée, deltas appariés).
- Propfirms do NOT accept crypto/delta-neutral → A and B stay personal book

## Repo layout
- Live crypto: `strategies/{tsmom_v2_propfirm, delta_neutral}`
- NQ live: `Futures/live/strategy_c_live/` (config, tradovate_client, signal_engine, guardrails)
- Active research: `<AssetClass>/research/active/` | Archived: `<AssetClass>/research/archived/`
- Programmes propfirm (clos): `PropFirms/<firm>/program_<date>/`. Programme FTMO 10k juin 2026 (memo + funnel v1/v2 + portfolio_audit + survivors_book + ftmo_research + alpha_program + …) consolidé dans `PropFirms/ftmo/program_2026-06/` (P2 2026-06-10 ; anciens chemins `research/`, `data/ftmo_research/`, `PropFirms/ftmo_*` — citations historiques non réécrites).
- Portfolio state: `Portfolio/state/portfolio_state.py`
- Automation: `_automation/alpha_hunt/` (scraper pipeline, `promising/` staged for feasibility) ; `_automation/feasibility/` (3-level gate orchestrator + 4 handlers: SkipMonth, ExitRule, RegimeFilter, Generic) ; `_automation/arxiv/` (daily q-fin scan) ; `_automation/synthesis/` (weekly cross-paper)
- Data governance (audit 2026-06-10, `_audit/dedup_audit_2026-06-10.md`) → règles complètes dans `_meta/data_governance.md`. Noyau : `data/raw/` = sources immuables (+ manifest `data/metadata/`), caches régénérables et gitignorés ; **une série = un fichier canonique**, la recherche RÉFÉRENCE `data/` et ne copie jamais ; jamais de blobs data dans git ; un subset ne se supprime qu'après migration de ses consommateurs, sauf s'il est la provenance d'une stratégie validée. Cleanup P0+P1+P2 fait 2026-06-10 (tag `pre-cleanup-2026-06-10`, .git 2.1Go→~65Mo, `_audit/cleanup_recap_2026-06-10.md`) ; deep_history_utc RÉPARÉ (backups `*_M1.csv.pre_repair_backup` ~1.1Go à conserver).

## Python envs
- Research: /usr/bin/python3 | Live VPS: ~/venv/ | Local: <HOME>/Desktop/Unholy returns/Python3.12.9/myenv/

## VPS
- Hetzner CX22, <VPS_IP>, user algo. SSH: `ssh -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP>`
- Crons réelles vérifiées 2026-05-30 (`_audit/verification_2026-05-30.md` V2) : `5 0 * * *` A daily HL testnet (`run_tsmom.sh --live --private-key <REDACTED>`, place des fills) | `30 0 * * *` A monitor (`run_monitor.sh`) | `5 0 * * 1` A weekly Propr rebalance (inline `PROPR_API_KEY=<REDACTED>`, gelée 2026-05-11) | `30 8 * * *` A daily Propr summary | `10 0,8,16 * * *` B delta-neutral (source .env) | `*/2 13-17 * * 1-5` C watchdog (×2 = DOUBLON) | `30 6 * * 1-5` `fetch_arxiv.sh` (silent fail) | `*/30 * * * *` `fetch_alpha_sources.sh` | `@reboot` screen mt5
- `fetch_alpha_sources.sh` PATCHÉ 2026-06-10 : distillation sur le VPS (process_raw_filter.py après fetch), push limité à `_seen/` + `_staging/` (anti-churn _stats.json), XML VPS-local purgé >7j. Chaîne JAMAIS en panne (le « dernier XML 02/06 » = repo local pas pullé). Reddit ×3 en 429 chronique (UA bloqué). Log `logs/alpha_hunt_fetch.log` (VPS). TODO : `fetch_arxiv.sh` pousse encore du raw XML (`_automation/arxiv/_raw/`, 1/j) — même patch applicable.
- Aucune cron NQ paper (`25 13 * * 1-5` / `25 14 * * 1-5`) n'existe → Strategy C non automatisée. Cleanup proposé non appliqué : `_audit/lot7_crontab_diff_2026-05-30.txt` + wrapper `scripts/run_with_env.sh`.

## CI / GitHub Actions
- `.github/workflows/auto-merge.yml` (201 lignes) : squash-merge automatique des PR `claude/*` après tous checks verts.
- **GARDE 1 — chemins sensibles = échec dur, PAS d'étiquetage.** Si les changements touchent
  `Futures/live/`, `Portfolio/`, `strategies/`, `.github/`, `*.mq5` (regex `auto-merge.yml:56`), le
  step sort en `exit 1` (`auto-merge.yml:48-69`) : le job échoue, la PR n'est pas auto-mergée. **Il
  n'y a aucun appel `addLabels` à cette étape** — la PR n'est PAS étiquetée `needs-human-review`
  (contrairement à ce qu'une version antérieure de cette section affirmait). Le blocage est réel ;
  seule sa description était fausse.
- ⚠ **`ftmo_live/` est absent de ce regex** (GARDE 1 ne liste que les 4 chemins ci-dessus + `.mq5`)
  alors que c'est le code Python réellement déployé par le pull VPS toutes les 30 min. En pratique
  il reste bloqué quand même, mais par un garde différent : voir GARDE 2.
- **GARDE 2 — restriction `_automation/`-only** (`auto-merge.yml:71-96`) : une PR modifiant un
  fichier HORS `_automation/` n'est pas éligible à l'auto-merge — c'est ce garde, pas GARDE 1, qui
  bloque de fait toute PR touchant `ftmo_live/`.
- **GARDE 3 — étiquetage `needs-human-review`** (`auto-merge.yml:98-118`) : seul endroit du workflow
  qui pose ce label + commente la PR, déclenché par GARDE 2 (fichiers hors `_automation/`), pas par
  GARDE 1.
- Notification Telegram sur échec de rebase/squash-merge (`auto-merge.yml:186-201`). Source vérité
  `_audit/verification_2026-05-30.md` V12 (description du mécanisme depuis corrigée par audit de
  navigabilité 2026-08-22, `_meta/cleanup/RAPPORT_navigabilite.md` §1).

## Code style
Production-quality Python: typed, vectorized, pandas/numpy. No matplotlib in core logic — separate plotting module. Tests for any function in strategies/ or Portfolio/. No comments stating the obvious; docstrings for public APIs.

## Methodology lessons

### Core (toujours appliquer, 1-10 universels)
Leçons 1, 2, 8, 10 = les Hard rules ci-dessus (signal T-1/trade T ; WF > single split + AMTP ; excess returns + HAC lag-6 + daily vol targeting ; max 3 mods). Leçon 9 = §Costs (crypto 0.17% RT | futures ~0.01% RT | equities 0.05-0.10% RT). Restantes :
3. Vol scaling essential. Always compute cost drag first.
4. β-dominance: need L/S or multi-asset to avoid beta exposure.
5. ETFs ≠ futures: roll drag contaminates momentum on commodity ETFs.
6. Small universe + AMTP = everything fails. N≥30 instruments minimum.
7. Propfirm match: align frequency, sizing, DD model type, consistency cap, DLL (or absence), min trading days, lock mechanism to strategy profile. Run trailing_dd_simulator.py with firm-specific PropfirmConfig before any purchase. Config: PropFirms/<firm>/rules.md.

### Registre L — index L11-L50 (texte intégral verbatim : `_meta/lessons_registry.md`)
Chaque ligne = verdict + chiffre opératoire ; dérivations, contre-exemples et chemins dans le fichier registre. L51-L55 gravées en entier ci-dessous.
**Crypto structural** (canonique depuis README §6.50) — L11 long-only CS crypto = β-dominated (corr_A ≥ 0.80 quel que soit l'IC), seule issue delta-neutral. L11b binary TP/SL : gate IJR mal calibré (C/√N décroissant en N), gate correct **E[gross/trade] > 3 × cost/trade**, IC pré-registrée depuis la lit (1er cas F2 Asian Range Breakout, archivé 2026-05-26). L12 plafond d'événements : à 0.17% RT ≈ **29 events/yr**/position pour 5%/yr net. L12b déflation HAC : half-life > 30d → N_eff << N (ETH netflow t 2.58 → **HAC 0.11**, N_eff≈73/3398). L13 VRP en unités de VARIANCE, pas % notionnel (BTC gross 4.4%/yr vs coûts 8.9% → net **-4.46%/yr**). L14 Sharpe testnet inadmissible (N<250) : SR(B)=9.64 → proxy **2.0**. L15 overlay de régime sur SR>1.0 = lift sub-seuil (~1.7%/yr) et seulement si MaxDD>20% — **condition corrigée par L54**. L17/L18 F&G velocity + Wikipedia attention = proxies de momentum / IC nul → branches sentiment CLOSED, taxonomie Da et al. épuisée (`Crypto/research/archived/other/wav_h3/`).
**FX structural** — L23 kill « fenêtre réglementaire » : edge adossé à un fixing élargi/restructuré (BIS WMR fév. 2015 1min→5min, MiFID II 2018) NON prédictif post-réforme, exiger ≥2 ans post-changement. L23b edge médié HFT dans la lit ≠ tradabilité retail → check de tier de coût (institutionnel 0.5-1.5bp RT vs retail 2-7bp RT), sceptique par défaut.
**Propfirm structural** — L19 NQ market impact : slippage baseline **4 ticks RT ($2/MNQ)**, jusqu'à **3×** sur fills adverses, ASYMÉTRIQUE, stresser ≥1.5× dans sizing_analysis.py. L20 DSR obligatoire dès **N_mod ≥ 2** (iter_10 : 1.52 → **1.0-1.1**), avant toute citation de Sharpe. L21 fourchettes Sharpe par catégorie : CS académique daily 0.3–1.2 | day-trade mono-instrument 0.8–2.0 | DN carry crypto 1.5–4.0 ; >2× → audit DSR/cherry-pick. L22 sim MC obligatoire avant achat : config canonique (eval DD $1,000, funded DD $1,000, lock $26,100, phases séparées), consistency cap $600/j liant à 4 MNQ (avg winner $628), **FTMO ≠ futures CME** (→ Tradeify/Apex/Topstep/MFFU), générateur trade-based calibré (`Portfolio/risk/trailing_dd_simulator.py`). L24 p(pass) dépend de la **FORME** de la distribution quotidienne face à une barrière **SYMÉTRIQUE**, PAS de la taille du compte (C plafonne ~44% de $10k à $200k) ; lumpy (WR 27.75%, 3.7×) plafonné **44-54%** ; **FTMO-SUITABLE** = Sharpe DAILY élevé + WR>55% + win/loss ≈1 + kurtosis basse + fréquence (edge en ≤40 séances).
**CFD/FTMO execution & structure (L25-L36, gravé 2026-06-10)** — L25 two-sided obligatoire : un vrai edge directionnel est positif sur LES DEUX jambes (toutes les familles FTMO testées = long-leg-only = beta). L26 delay-1 / same-bar : valider en trades non chevauchants + test de délai 1 barre ; ambiguïté de timestamp → barre SUIVANTE. L27 market-neutral *par construction* ≠ two-sided *en spread* (un spread cointégré hérite d'un drift relatif → échoue L25). L28 une paire CFD market-neutral paie **2× le markup** de financement ≈ **1.5 bps/nuit** → fatal aux spreads à retour en semaines. L29 holding calé sur la half-life = nécessaire non suffisant (retire un confondant, ne crée pas d'EV). L30 swaps FTMO ASYMÉTRIQUES (`ftmo_swaps.py`) : jamais tenir la jambe à swap négatif overnight ; US100 long **−3.31 bps/nuit** ⇒ harvester 82%→31% (capture mesurée long −662.4 / short +28.58). L31 alpha-decay carry/reversal (JPY carry 2022-24, US-idx STR pré-2013, EURGBP 2022-23) : split OOS/post-régime OBLIGATOIRE, queues d'unwind (−15/−20%) percent le floor 10%. L32 carry commodities CFD retail non collectable d'un côté (jambe short-contango −46+ bps/mois de swap). L32b le côté collectable est un crédit, pas un edge : long-only oil gaté sur backwardation ≈ **0 sur 19 ans** (+0.96%/yr de swap annulé par −1.03%/yr de beta prix) → **deux côtés du carry CFD fermés**. L33 c'est la STRUCTURE DE COÛT de l'instrument réel qui décide (un backtest à 2 bps ne transfère pas à un CFD 6-10 bps ; ORB mean_R change de signe entre 2 et 3 bps ; swap sur le NOTIONNEL TENU par jambe, dans les deux sens). L33b en intraday-flat (zéro swap) le coût liant est le SPREAD : il faut **>3 bps de gross** pour exister (Gao time-of-day ≈0 gross → −3 bps net, t −6). L34 flow-anchored FX = tier institutionnel seulement : le seul survivant en gross (Ranaldo, two-sided, t=3.55, **2.07 bps/j**) meurt sur le coût retail (besoin <~1 bp RT/jambe vs **2.48** mesuré). L35 le sizing DP-optimal est le **PLAFOND** de toute politique de sizing (ORB single-attempt FTMO 2-step = **33%** full-sample) — le levier c'est l'edge, pas le money management. L36 le carry overnight AGRÉGÉ pré-tue toute prime tenue sur FTMO : all-in book (~6.75%/yr de swap + ~1.25% de commission) ≈ toute la prime trend multi-asset (~8%/yr) → **net Sharpe 0.0** ; seules échappatoires intraday-flat (puis L33b) ou prime ≫ carry (classe precious-Q1).
**Trend/book & FX intraday (L37-L44)** — L37 sanity-check de filtre : si sign(filtre) ≠ signal natif <5% du temps, le filtre est cosmétique — nommer la sleeve pour ce qu'elle est (J1 = TSMOM long-only USDJPY, pas « carry-aligned trend »). L38 test de β-orthogonalité : régresser toute « prime structurelle » sur un buy-and-hold vol-targeté de son actif primaire, rapporter (β, α HAC, R²) ; **R² > 30% ⇒ pas orthogonal**, c'est du timing sur beta. L39 dissociation de skew : daily peut être négatif quand monthly est positif — le daily lie la barrière FTMO 5%, le monthly le book perso ; rapporter LES DEUX. L40-L41 **RÉSERVÉS** (arc top10-rigorous 2026-06, rapport hors-repo) — ne pas réattribuer. L42 le drift pré-FOMC est réel sur indices actions (8 instruments) ; le REVERSAL post-event est le mauvais sens, le momentum post-event continue (25/142 cellules AMTP-significatives négatives) — ⚠ **sans AUCUN support two-sided** : les colonnes `_SS` du batch sont `side=-side_long`, 24/24 paires miroir exactes, elles ne testent rien (2026-08-01). L43 FX intraday-flat retail cost-dead sur reversal/drift/saisonnalité (2007-2026, 10 majors, true-UTC) : gross exploitable sub-bps vs 2-5 bps CFD RT ; pre-flight **gross_per_trade / cost_p95 ≥ 1.5** ou mort (meilleur observé **0.36**). ⚠ **L43 est STRICTEMENT FX — ne jamais la citer pour les indices** (le 0.36 est un ratio FX ; gross indices ≈ 1.6 bps, 4× le FX). La mort des indices vient d'ailleurs et proprement : `intraday_mr_ftmo` (vrai UTC, gate au gross). L44 le contraste cross-sectionnel piloté par le mécanisme est le falsificateur d'IC le moins cher (Europe t 2.11 vs Asie-native −0.57 : signal réel, mort = coût).
**Renumérotés & nouveaux (L45-L50, réconciliation 2026-06-10)** — L45 TSMOM crypto-CFD two-sided infaisable sur FTMO, kill 3 axes : jambe short non significative même à **swap=0** (BTC t 0.28, N=205), jambe long ≡ Strategy A long-only (⇒ L11 β-long déguisé), 7 nuits × swap crypto FTMO ≈ **19 bps/trade** → classe momentum-crypto-hebdo FERMÉE sur CFD (reste non-CFD/Propr ou intraday-flat). L46 checklist d'honnêteté propfirm : un ledger canonique + coût réel mesuré + spec gelée + régime full-sample ⇒ les changements de signe entre rapports disparaissent (tous les sign-flips ORB historiques = différence d'hypothèse de coût sur le même ledger). L47 annualiser en **√(obs/an)**, pas √252 : un edge hebdo s'annualise en √52, √252 gonfle le Sharpe **×2.2**. L48 un registry-check doit balayer les chemins CONSOLIDÉS (un grep limité aux chemins historiques renvoie de faux « fichier supprimé » et a failli dégrader un STOP en caveat) — chaque essai évité protège le DSR de tous les candidats suivants. L49 l'unlock-drift est du short-alt-beta : net +337 bps/événement, t 2.90, N=578, non décayé, DSR 0.94, et pourtant SOUS la médiane d'un **PLACEBO CALENDAIRE apparié** vol-matched (p95 +539) ⇒ tout claim calendaire sur un univers structurellement baissier doit passer un placebo apparié (famille L11, même signature que announcement_premium). L50 les extrêmes de funding confirment le MOMENTUM à travers exchange et cycle : README §6.35 (HL, z-score, 2023-26) répliqué sur Binance (percentile trailing-1y, 2020-26, 13 perps, 2,195 événements) — funding haut extrême → **CONTINUATION** (+20/+30/+113 bps à 8h/24h/72h ; +239 @72h en 2020-21) ⇒ famille funding-contrarian fermée au tier exchange-perp, overlays de sizing sur percentile de funding sans fondation IC.

### Véhicule, sessions & ré-ouverture — registre L (L51-L55, gravé 2026-07-30)
L51. **Un jour de trading futures n'est PAS un jour calendaire ; « no overnight » ne forfait pas la nuit.** Session CME de ZN = 18:00 ET (J-1) → 17:00 ET (J) ; une règle daily-flat de propfirm futures ne coupe que la **pause de settlement** (Apex 4.0 : flat 16:59 → reprise 18:00 ; Topstep 16:10 → 18:00 ; MyFundedFutures : tenue overnight AUTORISÉE sur tous les plans). Mesuré sur month-end ZN : la jambe TENUE par un compte daily-flat porte **92.9 %** de l'effet (+16.25 bps, t 4.79), la jambe abandonnée est nulle (+1.24, t 1.43, p 0.168). **Gel 2026-06-10 (« toutes les firmes futures sont daily-flat ⇒ tenues multi-jours disqualifiées ») LEVÉ : modèle mental ACTIONS, il pré-tuait des candidats sans rapport.** (month_end_vehicle 07-30.)
L52. **Ne jamais faire confiance au nom d'un champ de provider ; et une décomposition intraday/overnight n'est pas définie sans dire DE QUEL JOUR on parle.** `yfinance ZN=F` daily `Open` = ouverture **Globex 18:00 ET du jour calendaire PRÉCÉDENT** (71.6 % exact au tick, médiane 0 tick), `Close` = settlement 15:00 ET — alors que `TLT.Open` est bien 09:30 ET. Donc « open→close capture 93 % » ne dit PAS « l'effet est intraday » mais « la session CME de 21 h capture 93 % ». Même effet découpé sur la journée cash US : 56/44 sur TLT ; version RTH-only sur ZN ne garde que 27-51 % **en perdant la significativité**. Tick-matcher les barres daily contre des barres horaires indépendantes AVANT toute décomposition. (month_end_vehicle 07-30.)
L53. **Si la marge du lot minimum tient dans le capital personnel, le propfirm n'apporte RIEN — test de 5 minutes, à faire AVANT toute simulation.** Un propfirm vend du levier sur du capital qu'on n'a pas ; 1 ZN ne demande que ~$1 800 de marge, soit 14 % d'un compte de $13 k. Compte perso : **+$2 275/an (+17.6 %), Sharpe 0.92 net, 100 % du P&L**, sans barrière ni horloge ni frais. Route propfirm : 11 mois, $639, 80 % du P&L d'UN contrat, sous une barrière qu'un événement historique a déjà franchie (pire événement −$2 009 vs buffer $2 000 : **le lot minimum couvre toute la barrière de mort**), sur un plan legacy non achetable. **Strictement dominée.** Process : la matrice de véhicule passe AVANT le backtest (correctif du biais « véhicule en dernier »). (month_end_vehicle 07-30.)
L54. **La condition liante d'un overlay de régime n'est PAS le MaxDD (correction de L15) : c'est que le régime prédisant la VARIANCE prédise la MOYENNE dans le MÊME SENS.** Le book MONO déployé a un MaxDD de −81 % (condition L15 remplie) et l'overlay a quand même échoué : les flags prédisent bien la variance (vol stress 9.8 % vs 4.2 %) mais le book gagne **+218 bps vs +21 bps** sur ces mêmes jours — la prime overnight EST la rémunération de ce risque, donc toute coupe retranche les jours qui paient. Aucune variante ne bat son **dé-levier à volatilité égale** (O3 : +3.76 pt vs +4.29 pt) ni son placebo à duty cycle identique (+2.0 pt seul ; O1 au 55e percentile) ; la durée EMPIRE (médiane 18→20 j). ⇒ Un overlay de régime n'aide qu'un book dont les régimes de haute vol sont AUSSI ses régimes de bas rendement. **Et le MaxDD n'est pas invariant d'échelle** : la même sleeve est à −9 % au vol-targeting de recherche et −81 % à vm 14× ⇒ toute condition en MaxDD s'évalue **au levier DÉPLOYÉ**. (regime_overlay_ftmo 07-30.)
L55. **La pondération inverse-vol sur un univers macro mixte est un amplificateur de swap sur CFD.** Mesuré sur CS macro momentum 17 instruments : le FX porte **53 % du notionnel**, contribue **−7.8 %** du gross P&L et un quart de la facture de swap — les jambes basse-vol raflent le gros notionnel, donc le gros portage, pour la plus faible contribution. Swap 3.47 %/an contre 7.25 %/an de gross = **48 % de la prime** (L36 mesuré, non supposé). Et ralentir n'échappe pas au carry (mensuel : gross SR 0.846→0.423 pour 0.09 pt/an économisé — le swap porte sur le notionnel TENU). (cs_macro_momentum 07-29.)

L56. **Un drift de session est ancré à l'horloge de l'ÉCHANGE (avec son DST), PAS à UTC — et une mesure H1 inclut silencieusement le gap de halt non tradable.** Le drift overnight or/argent ne vient pas de la « demande physique asiatique » : il tient entièrement dans la **première heure après la réouverture Globex 18:00 ET**, soit 1-2 h AVANT Tokyo. **Test de falsification, gratuit** : corréler le profil horaire hiver-vs-été dans les DEUX horloges — ici 0.70 (or) / 0.86 (argent) en ET contre **0.04 / 0.20 en UTC**. La fenêtre héritée « 23:00-07:00 UTC » était juste en hiver et **une heure en retard tout l'été** ⇒ la moitié de l'échantillon mesurait à côté (or été SR 0.52 vs hiver 1.62 ; horloge corrigée → 1.23, p 0.002). Corollaire : quand l'heure de settlement n'est pas cotée, la barre H1 **agrège le gap de halt**, que personne ne peut trader — part du gap : or 17.5 %, WTI 35.5 %, **argent 59.3 %** (77.5 % l'été). **Mesurer la part du gap AVANT toute revendication de performance.** (overnight_futures 07-30.)
L57. **Le coût FIXE domine en bps sur petit notionnel : un micro-future n'est « propre » que si son notionnel dilue la commission.** $1.70 fixe sur $6-7 k de notionnel = **2.3-2.8 bps à lui seul**, plus que tout le budget d'edge du soja ; le même frais sur les $40 k de MGC ne vaut que **0.66 bps**. Le « les futures sont la route propre » est FAUX pour les petits contrats. Et la granularité ne mord PAS en imposant du levier (1 MGC = 0.12 Kelly) : **elle mord en INTERDISANT le vol-targeting** — 1 lot ou rien coûte 0.35 de Sharpe, retourne le skew **+0.99 → −0.49** et ouvre une queue de **−18.4 % sur une seule session**. Rapporter le skew et la queue single-session de toute sleeve déployée à lot fixe. (overnight_futures 07-30.)
L58. **Un placebo apparié peut FABRIQUER un PASS : valider sa baseline contre l'espérance INCONDITIONNELLE (extension de L49).** Le placebo pré-enregistré du cycle d'adjudication a rendu un faux PASS avec une baseline de −5.88 bps là où la forme de trade inconditionnelle vaut +0.10 : ZN a une forte saisonnalité **jour-du-mois** (jours 16-20 : −10.79 bps, t −3.38) et le blackout ±3 j autour des adjudications — qui retire 38 % des jours centrés mi-mois — a poussé le pool dans ce creux. **Le blackout et l'appariement calendaire ont interagi.** Contrôle à coût nul : la moyenne du pool placebo doit égaler l'espérance inconditionnelle de la forme de trade ; sinon le placebo est biaisé, pas le signal. (treasury_auction 07-30.)
L59. **Le delay+1 ne certifie que l'ENTRÉE — re-pricer la SORTIE séparément** (stop-entry/bracket-exit). Sorties remplies au stop EXACT alors que **25 % des barres de stop ouvrent au-delà** ⇒ SR 0.99 → **0.49**. Toute la famille stop-entry des 109 (Crabel, ORB, NR7…) est validée de façon **incomplète**. Même dossier : vérifier le **swap dans le coût** (8 nuits sans swap = 43-53 % du gross) et tester **à géométrie de sortie constante** — l'edge Gap Pattern y passe à **−0.020** contre **+0.041** en entrée inconditionnelle : il était dans la sortie, pas le signal. (gap_pattern_rehab 07-31.)
L60. **Mesurer la part de barres à fourchette NULLE avant d'utiliser une série : un print de règlement n'est pas un prix.** XPTUSD/XPDUSD (yfinance) : fourchette médiane **ZÉRO**, 61/69 % de barres `high==low==close`, « gap » apparent 79/74 % — pour **32 % du P&L** (51 % avec XAGUSD) ; sur données brokers seules l'edge tombe à ~0. `ohlc/` mélange **3 qualités sans marquage**. Contrôle gratuit par série et par année. (gap_pattern_rehab 07-31.)

### Politique de RÉ-OUVERTURE des familles archivées (2026-07-30)
**Une archive n'est pas un cimetière.** Le critère de ré-ouverture est la NATURE du kill, pas son existence :

| Nature du kill d'origine | Statut | Justification |
|---|---|---|
| **Mécanique** — signal inexistant : gross ≈ 0, two-sided négatif à coût NUL, régime-dépendant, sous placebo | **RESTE FERMÉ** | recalibrer une statistique ne ressuscite pas un gross de 0.00 bps |
| **Véhicule** — pas d'instrument, contraintes de barrière, granularité de lot | **ROUVRABLE** | prouvé : month-end rejeté 2× sur le véhicule, vivant sur le compte perso (L53) |
| **Coût** — tué au tarif CFD retail (2-7 bps RT) | **ROUVRABLE** | le coût futures (~0.4 bps RT sur MNQ) change le gate d'un ordre de grandeur |
| **Puissance** — IC contenant zéro sur échantillon tronqué/court | **ROUVRABLE** | UNDERPOWERED ≠ REJECTED ; échantillon parfois tronqué par un fichier d'entrée (pre-FOMC : 49 événements au lieu de 102 disponibles) |
| **Géométrie** — barrière, sizing, horloge | **ROUVRABLE** | ~60 % du p(pass) vient de la géométrie, pas de l'alpha |

Discipline : rouvrir exige un **angle explicitement nouveau**, écrit AVANT de toucher la donnée, et relevant de l'une des quatre catégories rouvrables. Rouvrir pour re-tester le même angle = data-mining, et déflate le DSR de tous les candidats.

### Aliases historiques (citations dans les artefacts ≠ numéro gravé — artefacts JAMAIS réécrits)
→ table complète dans `_meta/l_aliases.md` : "L33 candidate"→**L45**, "L34 (proposé)"→**L46**, "L36 existant (√52)" (phantom)→**L47**, "L33-bis"→**L33b**, **L16 = vacant** (ne pas réattribuer), L40/L41 réservés (rapport hors-repo).

## Methodology toolkit
- **Significance**: HAC Newey-West (lag-6) t-stat, threshold t > 2.5 for IC feasibility
- **Multiple testing**: AMTP when n_tests > 1; DSR (Bailey-LdP) for n_mod > 5
- **Bootstrap**: block bootstrap (Politis-Romano) — iid forbidden when trade clusters exist
- **Walk-forward**: expanding window ≥5 folds (single split forbidden)
- **IC → net Sharpe** (Israel-Jiang-Ross 2017): expected_gross_alpha ≈ 0.40 × IC × √breadth × σ_target; require gross > 3×cost_drag. Daily ETF (0.10% RT): IC>0.08. Daily futures (0.01% RT): IC>0.04. Monthly-rebal (breadth ~12): cost gate essentially absent.
- **FX carry regime-dependence**: 2005-2007 pre-GFC drives all G10 carry IC. Always check per-decade IC breakdown before calling carry feasible.
- **5 mandatory script fixes**: (1) Excess returns: subtract daily RF (FRED DTB3) from all asset returns ; (2) HAC SE: sm.OLS().fit(cov_type='HAC', cov_kwds={'maxlags': 6}) ; (3) Daily vol targeting: 63d rolling std × √252, sampled at month-ends ; (4) TSMOM diagnostics: dir accuracy ≥53%, quintile monotonicity, convexity β test ; (5) Honest naming: approx_multi_test_penalty (not "DSR").

## Data sources
- Crypto OHLCV: Binance daily klines (free, unlimited) + HL 4h/1h snapshots
- Funding rates: Hyperliquid 8h, cached CSV in data/funding_carry/
- NQ 1-min: `data/raw/NQ_1min_databento_2010-2026.parquet` (CANONIQUE, source GLBX dbn.zst) + `data/raw/NQ_1min_2022-12-26_2025-12-11.parquet` (ex-Kaggle — provenance de la validation historique de C, à conserver ; CSV Kaggle d'origine n'existe plus)
- FX/indices M1 canonique: `data/deep_history_utc/` (true UTC 2007→2026-06, spread calibré, MANIFEST machine-généré, trous 2018-2021 réparés 2026-06-10). m5_indices (P2 fait) : 13 M1 EET supprimés ; restent `US2000_M1.csv` (pas de superset), `binance/` (crypto M1), panels parquet EET (`*_m1_panel.parquet`, consommés par du code actif — migration tz à prévoir, `_audit/m5_indices_migration_checklist_2026-06-10.md`).
- ⚠ **La colonne `spread` de `deep_history_utc` est INUTILISABLE SEULE (mesuré 2026-07-29/30)** : (a) **massivement non peuplée sur le FX** — EURUSD **66/69/63 %** de barres à spread NUL en 2021/2022/2023, GBPUSD 33 % en 2022, GER40 22 % à 19:00 UTC, et **US30 79.7/100/74.9 % en 2019/2020/2021** (« indices propres » est FAUX — corrigé 2026-08-01) ; (b) sous-estimation du RT FTMO réel d'environ 2.4× là où elle est peuplée. ⇒ Tout coût sur cette seule colonne est **optimiste** : utiliser le panel RT mesuré + swaps mesurés. Familles tuées SUR LE COÛT (L43, L34) ⇒ **renforcées** ; tout PASS sur du FX 2021-2023 ou du US30 est à re-vérifier. ⚠ **Deux tables de coûts INCOMPATIBLES coexistent** (`COST_AUDIT.md` 2026-08-01) : `top10_test/framework.py` (catalogue, a filtré les 164 tests) facture l'or **3.5 bps** contre **1.84 mesuré** ⇒ or sur-pénalisé **1.9×** ; et `phase0_rt_cost_bps.csv` ne mesure JAMAIS les indices (1.2 codé en dur alors que le cache donne 0.47-0.82). Coût indices réel ≈ **1.8 bps RT**.
- Commodity futures: yfinance =F tickers (CL=F, GC=F, …) — continuous front-month. ⚠ **Ne jamais faire confiance au nom d'un champ** : `ZN=F.Open` = ouverture Globex 18:00 ET du jour calendaire PRÉCÉDENT, pas une ouverture de séance US (L52).
- FX M5: Dukascopy bi5 custom decoder in `Forex/research/archived/strategy_e_fix_flow/data_setup.py` + `Forex/data/dukascopy_downloader_m5.py`. DL ~12min/pair-year, 4 threads. Cache dukascopy_m5 SUPPRIMÉ 2026-06-10 (P2 partiel) — régénérable, ou resampler deep_history_utc M1.
- Equities: yfinance + Tiingo (limited free tier)
- FRED: DTB3 (RF daily), interbank rates monthly
- HL API constraint: no candle data before Nov 2022; gap Dec 2022–Dec 2023

## Research history (n_tests = 321 global — ledger canonique)
Convention + milestones séquentiels (83/142/159/170/175/180/321, règle d'incrément, jonction global↔programme, sous-totaux qui SE CHEVAUCHENT donc jamais additionnés) → `_meta/n_tests_ledger.md`. Noyau : GLOBAL 321 FIGÉ 2026-05-30 ; depuis 2026-06 chaque programme tient son compteur LOCAL et son delta est réconcilié ici à la clôture.

### ✓ Validated and live/ready
- Crypto TSMOM v3 (Strategy A) — ⚠ le « 1.33 OOS » est un GROSS-of-RF sur 14 coins ; config live (BTC/ETH/SOL) en EXCESS = **0.566**, IC95 [-0.50, 1.63] (recalc 2026-07-29)
- Delta-neutral carry HL (Strategy B) — ⚠ Sharpe NON CITABLE (2026-07-29) : backtest = rotation lente, config live 8h négative, WF 3 folds < 5
- NQ opening momentum iter_10 (Strategy C) — ⚠ re-baseline 2026-06-07 : Sharpe 0.41 ($29 RT, Databento 2014-2026) ; le 1.52 historique (Kaggle, $19 RT) est périmé. Tradeify annulé 2026-06-10.

### Active research (in progress)
⚠ **Le chantier le plus actif est `Multi_Asset/research/active/`** (48 dossiers 2026-07/2026-08,
source des leçons L51-L60) — indexé dans `_meta/research_active.md` §Tronc Multi_Asset (ajouté
2026-08-24 ; absent de la liste ci-dessous, restée à l'inventaire 2026-05-30). Vue narrative :
`Multi_Asset/README.md`.

Inventaire 2026-05-30 (hors Multi_Asset) — détail complet (chemins, n_test, métriques, caveats) →
`_meta/research_active.md`. Chantiers ouverts : **Strategy D** D3+D5 portfolio (`Futures/research/active/strategy_d/`, budget 3 mods 0 consumed) ; **Commodities XS Basis+TSMOM** (`Commodities/research/active/xs_basis_tsmom/`, n≤279, phase A incomplète) ; **Voie B FTMO** (`Futures/research/active/voie_b_ftmo/`, sous-jacent [À CONFIRMER MANUELLEMENT]) ; **sector_hothand_propfirm** (`Equities/research/active/sector_hothand_propfirm/` — t_HAC 10.38 = drapeau rouge, MDD -13.3% > limite FTMO 10% ⇒ BREACH en l'état, audit obligatoire) ; **FX intraday deepdive** (`Forex/research/active/fx_intraday_deepdive/`) ; **ZN Baltussen** (`Futures/research/active/zn_baltussen/`) ; **Token unlocks** + **VRP short gamma** (bootstrap vides). ARCHIVÉS : CIP-EOQ (`Forex/research/archived/cip_eoq/`), NQ intraday VWAP (`Futures/research/archived/nq_intraday_vwap/`, N=19 insuffisant).

### ✗ Archived / Deferred / Untested — inventaire complet
→ voir `research_history.md` (racine du repo ; registre « DO NOT re-propose » : Crypto n=159, FX n=181, Equities/ETF/Futures, Options n=1, Deferred, Untested paid-data/new-infra). Sorti de ce fichier constitutionnel pour tenir sous la limite Claude Code ; consulté à l'évaluation d'une nouvelle idée, pas à chaque session. Aucune info perdue.

## Automation infrastructure
- `_automation/alpha_hunt/`: VPS cron scrapes Reddit/HN/Quantocracy/SSRN/GitHub, applies L0/L1/L2 filters, stages items in `promising/`. Dedup via `_seen.json`.
- `_automation/feasibility/`: 3-level gate pipeline (A: IC; B: WF+bootstrap+DSR; C: sanity checks). Handlers dispatch by hypothesis type (SkipMonth, ExitRule, RegimeFilter, Generic fallback).
- Routines run on Anthropic cloud — no external API access, repo data only.
- Each routine commits to `claude/<routine-name>-<date>` and opens a PR.

## Current focus
→ see `_meta/current_focus.md` (updated each session; blockers, in-progress work, next priorities — séparé de ce fichier constitutionnel pour éviter la dette de maintenance)

## Parallel session coordination (READ BEFORE LAUNCHING /goal)
- Before any /goal: `git pull origin main` and read this CLAUDE.md.
- **Worktree isolation — un worktree = une session ; JAMAIS deux sessions dans le même répertoire** (`.git/HEAD` partagé → un checkout/commit déplace le HEAD sous l'autre session ; incident 2026-06-19 : commit asia_23_8 atterri sur la branche soybean, réparé par cherry-pick + `branch -f`). Nouvelle tâche → worktree dédié, branche neuve depuis `origin/main` (toujours, → PR propre) : `git fetch origin && git worktree add .worktrees/<tache> -b claude/<tache> origin/main && cd .worktrees/<tache>`. Branche existante : `git worktree add .worktrees/<tache> claude/<branche>`. `git worktree list` pour inspecter ; après merge `git worktree remove .worktrees/<tache>`. ⚠ **Les worktrees vivent dans `.worktrees/` À L'INTÉRIEUR du dépôt (gitignoré), JAMAIS dans `../`** — la convention `../Algo_claude_<tache>` (en vigueur jusqu'au 2026-08-29) éparpillait onze dossiers sur le Bureau ; corrigée à la demande de l'utilisateur. En fin de tâche : rapatrier les artefacts dans le dépôt principal, pousser la branche sur `origin`, puis `git worktree remove`. Ne jamais `branch -f`/rebaser la branche d'une session ACTIVE sans la prévenir (son HEAD devient incohérent).
- Never create parallel infrastructure folders without checking existing live/ first.
- Strategy C canonical live infra: Futures/live/strategy_c_live/ (NOT strategy_c_paper/). strategy_c_paper/: ONLY pre-existing log infra (log_trade.py, paper_trade_log.csv).
- For new asset classes, check Research history before assuming nothing was tested.
- **Phase-0 / lesson sweeps (L48)**: grep BOTH the historical cited paths (`data/ftmo_research/`, `research/`, `data/oxfordstrat_109/` — non réécrits) AND the consolidated dirs (`PropFirms/ftmo/program_2026-06/**`) AND `data/skew_research/session_*` AND funnel CSVs. La L-registry ci-dessus (L11-L55) est la constitution ; les rapports de session peuvent citer des alias — voir la table. Lesson minting en session = NAMED candidates only ; numéros gravés ici à la réconciliation (no number minting inside a session).
- **Worktree + artefacts locaux : CODE (tracké) vs DONNÉES (locales).** Règle : **tout code importé par du code tracké EST tracké.** Le moteur cleanroom `audit_v2_independent/cleanroom/engine.py` est une **librairie canonique TRACKÉE** (PR #400, 2026-07-21) : 9 modules trackés en dépendent, dont le code LIVE `ftmo_live/lib/{invariants,governor,replay,signals}.py` (miroir sim↔live de l'EA réel) + les 3 moteurs sim. Le laisser « local » rendait `ftmo_live/lib/` non-importable sur un checkout frais et laissait le moteur dériver hors PR ; il vit désormais dans CHAQUE checkout (worktree inclus). Les `cleanroom/run_phase*.py` (one-off, importés par personne) restent locaux. En revanche **caches régénérables** (`data/ftmo_portfolio/cache/*.parquet`, `data_cache/`, panels) et dirs data cités dans REGISTER.md restent **locaux/gitignored** → absents d'un worktree frais : une session en worktree les **importe du main dir par chemin absolu** (`<HOME>/Desktop/Algo_claude/…`), read-only.
- **Session close (obligatoire)**: `python3 tools/check_register_integrity.py` (fail-loud: cited paths exist + git-tracked, N chain monotonic) — fix findings BEFORE the closing commit. **Lancer ce check dans le MAIN working dir, JAMAIS dans un worktree** : un worktree n'a pas les dirs locaux/gitignored cités → faux `MISSING` (l'intégrité canonique se vérifie là où vivent les artefacts locaux).
