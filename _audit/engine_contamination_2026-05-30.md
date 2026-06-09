# Engine Contamination Audit — 2026-05-30 (lecture seule)

**Déclencheur** : `_audit/sector_hothand_audit_2026-05-30.md` §1 a identifié un
look-ahead bias structurel dans `Equities/research/active/sector_hothand_propfirm/engine.py:120`
(`entry_px = open_t if open_t < close_tm1 * (1 - daily_stop) else close_tm1`).
Dans le cas normal (~99% des jours), l'engine remplit l'ordre au **prix
ayant servi à former le signal** (close T-1), violation L1.

**Question** : ce pattern est-il propagé ailleurs ? Le scope est-il limité au
sector_hothand isolé, ou un parc de moteurs est-il contaminé ?

**Méthode** : grep exhaustif `entry_px|fill_price|entry_price`, inspection
ligne-par-ligne de chaque moteur identifié, classification du fill (open_t,
next_open, close_t, close_tm1, current-bar-close), confrontation avec L1.

**RIEN n'a été modifié.** Pas de fix, pas de re-run, pas de commit du fix.
Toutes les preuves citent `fichier:ligne`.

---

## §1. Tableau récapitulatif — un moteur par ligne

Légende :
- `LOOK-AHEAD` : confirmation explicite d'un biais.
- `CLEAN`     : convention `signal[t-k] → entry[t+1]` respectée.
- `[À VÉRIFIER]` : pattern complexe non concluant par lecture seule.
- `N/A`       : pas de moteur (hypothèses, infra, data fetch).

| Strategy / dossier | Moteur utilisé | Construction du fill | Verdict | Preuve fichier:ligne |
|---|---|---|---|---|
| **Strategy A — TSMOM Propr** (FROZEN) | `strategies/tsmom_v2_propfirm/backtest_v2.py` | `position = signal × vol_scalar` ; `held = positions.shift(1)` ; `pnl[T] = held[T] × arith_return[T]` (close-to-close) | **CLEAN** | backtest_v2.py:204-209 ; signal.py:18-20 docstring |
| **Strategy A — TSMOM v3 research** | `strategies/tsmom_v3/backtest.py` | `held = positions.shift(1).fillna(0.0)` ; `gross = (held * arith).mean(axis=1)` ; toutes les rolling().shift(1) sur le signal | **CLEAN** | backtest.py:93,184 ; signal.py:21,48,58,70-71 |
| **Strategy B — Delta-neutral carry** (LIVE testnet) | `strategies/delta_neutral/backtest.py` | Walk-forward train/test stricts (`fold_start`/`train_end`/`test_start`/`test_end`) ; sélection univers sur train, P&L sur test ; entry cost déduit au premier bar | **CLEAN** | backtest.py:204-294 (en particulier l.245-254 select sur train, l.266-281 oos pnl) |
| **Strategy C — NQ Opening Momentum** (PAPER ready) | `Futures/research/active/nq_intraday/engine.py` | `future = self.rth[self.rth.index > sig_ts]` (STRICTEMENT après signal) ; `entry_price = float(future.iloc[0]["open"])` | **CLEAN** | engine.py:88-99 docstring + 114-119 |
| **Strategy C — live signal engine** | `Futures/live/strategy_c_live/signal_engine.py` | Signal computation only (ORB + VWAP + filters). N'exécute pas de fills (délégué à tradovate_client / mt5_client). Pas de pattern entry_px = close_tm1. | **CLEAN** | signal_engine.py (171 lignes, aucun match du pattern incriminé) |
| **Strategy D iter_d2_mr (research)** | `Futures/research/active/nq_intraday/analysis/iter_d2_mr.py` | Hérite du pattern Strategy C : `entry_price = float(future.iloc[0]["open"])` | **CLEAN** | iter_d2_mr.py:234,305 |
| **Strategy D iter_d_pairs** | `Futures/research/active/nq_intraday/analysis/iter_d_pairs.py` | [À VÉRIFIER] — non lu en détail, mais utilise les mêmes helpers `propfirm_compat_v2.py` (TV_TRAILING_DD impacté par LOT 3) | **[À VÉRIFIER]** | iter_d_pairs.py:47 import + propfirm_compat_v2 simulation |
| **sector_hothand_propfirm** (active) | `Equities/research/active/sector_hothand_propfirm/engine.py` | `entry_px = open_t if open_t < close_tm1*(1-stop) else close_tm1` — cas normal = close_tm1 (look-ahead) | **LOOK-AHEAD** (CRITIQUE) | engine.py:120 (cf. audit dédié 2026-05-30) |
| **Voie B FTMO (Strategy A pivot)** | `Futures/research/active/voie_b_ftmo/ftmo_voie_b_original.py` + `corr_c_b.py` | Open-to-close US ; signal à 14:30 UTC sur gaps overnight observables ; `entry_price = float(post_orb_to_exit.iloc[0]["open"])` | **CLEAN** | ftmo_voie_b_original.py:1-25 docstring "CAUSAL signal" ; corr_c_b.py:115 |
| **nq_intraday_vwap iter_01** | `Futures/research/active/nq_intraday_vwap/iter_01.py` | `entry_price = close` (where `close` est le close du bar courant au moment où le signal `z > z_thresh` se déclenche) → fill au prix de calcul du signal | **LOOK-AHEAD** (sur strat déjà FAIL N=19) | iter_01.py:266,273 |
| **CIP-EOQ (Forex)** | `Forex/research/active/cip_eoq/sigma_estimation/` | Pas de moteur de backtest (sigma_estimation seul, validate_basis.py) | **N/A** | dir contient sigma_estimation_findings.md + figures/ uniquement |
| **ZN Baltussen (Futures)** | `Futures/research/active/zn_baltussen/` | Aucun .py top-level visible ; sigma_estimation/ + tests/ + __pycache__/ uniquement | **N/A** | aucun fichier .py à la racine du dossier |
| **Strategy D pré-registration** | `Futures/research/active/strategy_d/hypotheses_preregistered.md` | Document Markdown — pas de code | **N/A** | dossier 1 fichier .md |
| **Strategy D NQ infra** | `Futures/research/active/strategy_d_nq/infra/` | run_manual_signal.sh + plist + README | **N/A** | dossier 3 fichiers infra |
| **Commodities XS basis_tsmom** | `Commodities/research/active/xs_basis_tsmom/` | Phase A (data fetch) non terminée — pas de backtest run | **N/A** | dir 19 fichiers majoritairement roll_plots + fetch |
| **Token unlocks (Crypto)** | `Crypto/research/active/token_unlocks/_bootstrap_notes.md` | Bootstrap seul, vide | **N/A** | 1 fichier .md |
| **VRP short gamma (Crypto)** | `Crypto/research/active/vrp_short_gamma/_bootstrap_vrp_notes.md` | Bootstrap seul, vide | **N/A** | 1 fichier .md |
| Crypto archived — funding_carry | `Crypto/research/archived/carry/funding_backtest.py` | `pending_entry_dir`/`pending_entry_sig_bar` queue → fill au bar i+1 sur `px = prices[i+1]` | **CLEAN** | funding_backtest.py:107-108,176-186,228-229 |
| Crypto archived — momentum | `Crypto/research/archived/momentum/momentum_backtest.py` | Split explicite `signal_date` vs `exec_date` ; `opens` utilisés pour entries ; `pending_stop_exits` queue | **CLEAN** | momentum_backtest.py:130 (exec_to_signal), 145-178, 155 |
| Crypto archived — `other/backtest.py` | `Crypto/research/archived/other/backtest.py` | `pending_sig` queue, fill au `open[i+1]`. Docstring fait référence à un bug précédent : "Previously entering at open[i] created a fatal look-ahead bias" → fix appliqué historiquement. | **CLEAN** (correctif appliqué) | other/backtest.py:26-31 docstring ; 110 pending_sig |
| Crypto archived — meta_tsmom | `Crypto/research/archived/ml/meta_tsmom/feasibility.py` | "Entry price = open of day AFTER signal change" (l.156) | **CLEAN** | meta_tsmom/feasibility.py:155-168 |
| Crypto archived — regime_meta | `Crypto/research/archived/regime/regime_meta/backtest.py` | `held = pos.shift(1).fillna(0.0)` ; `arith = close.pct_change()` | **CLEAN** | regime_meta/backtest.py:143-146 |
| Crypto archived — pmr_basis v1 | `Crypto/research/archived/other/pmr_basis/backtest_v1.py` | `signal = basis_z.shift(1)` (lag-1) ; entry à T close après signal connu à T-1 close | **CLEAN** | pmr_basis/backtest_v1.py:112-118,157,244,258 |
| Crypto archived — VRP Deribit | `Crypto/research/archived/options/vrp_deribit/engine.py` | "No signal timing. Premium harvest only" — cycles déterministes, entry à `dvol_a[t]` (vol observée au début du cycle) | **CLEAN** (vol-harvest) | vrp_deribit/engine.py:5,121,150 |
| Crypto archived — crash_recovery | `Crypto/research/archived/patterns/crash_recovery/feasibility.py` | `entry_price = close.iloc[i]` après signal calculé via `ret_3d = log(close / close.shift(3))` au bar i → entry au prix du signal | **LOOK-AHEAD** (archived) | crash_recovery/feasibility.py:133 comment + 149 |
| Crypto archived — orb_crypto | `Crypto/research/archived/patterns/orb_crypto/feasibility.py` | `entry_px = float(df.at[ts_02, "Open"])` (next-bar open) MAIS `df_thr["sig_long"] = ... & (df_thr["entry_px"] > df_thr["high_1h"])` — utilise le prix d'entrée DANS la condition du signal (look-ahead concurrent) | **[À VÉRIFIER]** (signal utilise next-bar open) | orb_crypto/feasibility.py:210,371-372 |
| Crypto archived — weekend_anomaly | `Crypto/research/archived/patterns/weekend_anomaly/run_backtest.py` | "Entry = open of the NEXT bar after Friday 16:00 (= Sat 00:00 open)" | **CLEAN** | weekend_anomaly/run_backtest.py:60-65,103-104 |
| Equities archived — indices_swing | `Equities/research/archived/indices_swing/backtest/engine.py` | `pnl_gross = pos.shift(1) * excess_ret` ; comment "pos[T-1] × excess_ret[T]" | **CLEAN** | indices_swing/backtest/engine.py:1-15,82-90 |
| Equities archived — indices_swing IC scan | `Equities/research/archived/indices_swing/ic_scan/ic_engine.py` | IC mesuré sur `signal[T]` vs `fwd_ret[T]` — pas un moteur de fill | **CLEAN** (mesure IC seule) | ic_engine.py:11,42-54 |
| Futures archived — orb_ivb_nq | `Futures/research/archived/orb_ivb_nq/feasibility.py` | [À VÉRIFIER] — pas inspecté en profondeur, NQ ORB IVB déjà ARCHIVE | **[À VÉRIFIER]** (archived FAIL) | feasibility.py (1300+ lignes non explorées) |
| Futures archived — network_momentum (Multi_Asset) | `Multi_Asset/research/archived/network_momentum/` | Déjà ARCHIVE 2026-05-30 (LOT 2) | **N/A** (verdict FAIL pré-existant) | feasibility_summary.md:9 |
| _automation — feasibility WF | `_automation/feasibility/stats/backtest_wf.py` | `positions = signal.shift(1) * vol_scalar.shift(1)` ; `pnl_gross = positions.shift(1) * log_returns` (double shift, ultra-conservateur) | **CLEAN** (over-conservative) | backtest_wf.py:47,54,85 |
| Portfolio simulator | `Portfolio/risk/trailing_dd_simulator.py` | Monte Carlo sur PnL séries ; n'est pas un moteur signal→fill | **N/A** (sim post-pnl) | trailing_dd_simulator.py:25-44 |

---

## §2. Pattern de contamination — inventaire des occurrences entry/fill suspectes

Grep exhaustif `entry_price|entry_px|fill_price` sur tout le repo (hors `_frozen/`,
`__pycache__/`, `.git/`).

### (a) Cas positifs `entry = close du bar courant au moment du signal`

| Fichier:ligne | Strategy | Construction | Statut |
|---|---|---|---|
| `Equities/research/active/sector_hothand_propfirm/engine.py:120` | sector_hothand | `entry_px = open_t if open_t < close_tm1*(1-stop) else close_tm1` | **LOOK-AHEAD CRITIQUE** (active, audité 2026-05-30) |
| `Futures/research/active/nq_intraday_vwap/iter_01.py:266` | nq_vwap iter_01 | `entry_price = close` (close = bar courant) à signal `z > z_thresh` | **LOOK-AHEAD** (strat déjà FAIL N=19, mais bug à noter) |
| `Futures/research/active/nq_intraday_vwap/iter_01.py:273` | nq_vwap iter_01 | idem, autre direction | **LOOK-AHEAD** |
| `Crypto/research/archived/patterns/crash_recovery/feasibility.py:149` | crash_recovery | `entry_price = close.iloc[i]` au bar de signal | **LOOK-AHEAD** (archived) |

### (b) Cas négatifs (CLEAN) `entry = next-bar open`

| Fichier:ligne | Strategy | Construction | Statut |
|---|---|---|---|
| `Futures/research/active/nq_intraday/engine.py:119` | Strategy C | `entry_price = float(future.iloc[0]["open"])` après `future = rth[index > sig_ts]` | CLEAN |
| `Futures/research/active/nq_intraday/analysis/iter_d2_mr.py:234,305` | iter_d2_mr | idem | CLEAN |
| `Futures/research/active/voie_b_ftmo/corr_c_b.py:115` | Voie B FTMO | `entry_price = float(post_orb_to_exit.iloc[0]["open"])` | CLEAN |
| `Crypto/research/archived/patterns/weekend_anomaly/run_backtest.py:103` | weekend_anomaly | `entry_price = px.loc[entry_ts, "open"]` (entry_ts = ts + 8h) | CLEAN |
| `Crypto/research/archived/momentum/momentum_backtest.py:155` | weekly momentum | `exit_px = opens.get(...)` ; entries également au open via exec_date | CLEAN |
| `Crypto/research/archived/ml/meta_tsmom/feasibility.py:155-168` | meta_tsmom | "Entry price = open of day AFTER signal change" | CLEAN |
| `Crypto/research/archived/carry/funding_backtest.py:182,228` | funding_carry | `entry_price = px` au bar i+1 après pending_entry queued au bar i | CLEAN |
| `strategies/delta_neutral/live_trader.py` | Strategy B live | hyperliquid_client.entryPx (live exchange fill) | CLEAN (live) |

### (c) Cas `position.shift(1)` (vectorisé, équivalent à entry au lendemain)

| Fichier:ligne | Strategy | Construction | Statut |
|---|---|---|---|
| `strategies/tsmom_v2_propfirm/backtest_v2.py:209` | Strategy A v2 | `prev_pos = positions.shift(1).fillna(0.0)` | CLEAN |
| `strategies/tsmom_v3/backtest.py:93,184` | Strategy A v3 | `held = positions.shift(1).fillna(0.0)` | CLEAN |
| `Equities/research/archived/indices_swing/backtest/engine.py:90` | indices_swing | `pnl_gross = pos.shift(1) * excess_ret` | CLEAN |
| `Crypto/research/archived/regime/regime_meta/backtest.py:146` | regime_meta | `held = pos.shift(1).fillna(0.0)` | CLEAN |
| `Crypto/research/archived/other/pmr_basis/backtest_v1.py:118` | pmr_basis | `bz.shift(1)` (signal lag-1) | CLEAN |
| `_automation/feasibility/stats/backtest_wf.py:54,85` | auto WF | `positions = signal.shift(1) * vol_scalar.shift(1)` puis `pnl = positions.shift(1) * log_returns` | CLEAN (over-conservative) |

### (d) Cas ambigus `[À VÉRIFIER]`

| Fichier:ligne | Strategy | Raison du flag |
|---|---|---|
| `Crypto/research/archived/patterns/orb_crypto/feasibility.py:371-372` | orb_crypto | Signal threshold `sig_long = (rvol >= thr) & (entry_px > high_1h)` utilise `entry_px = ts_02_open` dans la condition. Si l'évaluation a lieu APRÈS observation du ts_02_open, c'est borderline ; si AVANT, c'est look-ahead. (archived, faible priorité) |
| `Futures/research/archived/orb_ivb_nq/feasibility.py` | NQ ORB IVB | Non lu en profondeur (1300+ lignes). Archive ; verdict FAIL pré-existant (Conti/Valentini sharpe -0.09/-0.44). |
| `Futures/research/active/nq_intraday/analysis/iter_d_pairs.py` | iter_d_pairs | Pas inspecté ligne-par-ligne. Importe `propfirm_compat_v2` (impacté par LOT 3) ; logique signal/fill non auditée ici. |

---

## §3. Impact sur les stratégies VALIDÉES / LIVE — verdicts explicites

### §3.1 — Strategy C (NQ Opening Momentum iter_10) : **SR 1.52 FIABLE** ✓

**Verdict** : Sharpe 1.52 OOS **n'est PAS contaminé** par le pattern look-ahead
sector_hothand. Le moteur Strategy C utilise l'implémentation canonique :

```python
# Futures/research/active/nq_intraday/engine.py:114-119
future = self.rth[self.rth.index > sig_ts]      # STRICTEMENT après le signal
if future.empty:
    continue
entry_bar  = future.index[0]                     # premier bar postérieur
entry_price = float(future.iloc[0]["open"])      # open de ce bar
```

Le `> sig_ts` (strict, pas `>=`) garantit que le bar d'entrée est **postérieur**
au timestamp du signal. Pour la signature iter_10 :
- Signal calculé entre 09:30 et 09:45 ET (ORB) → `sig_ts ≈ 09:45 ET`
- entry_bar = premier bar avec index > 09:45 → bar 09:46 ET
- entry_price = open du bar 09:46 ET ✓

Identique à la doctrine documentée `engine.py:88-99` :
> Entry: next bar open after signal timestamp.

**Aucune métrique de Strategy C à recomputer.** Sharpe 1.52 / MaxDD -13.4% /
WF 78% / N=346 trades restent valides sous L1.

Le même moteur est partagé par `iter_d2_mr.py:234,305` (Strategy D D2) et par
`iter_05.py / iter_06.py / iter_09.py` (variantes), tous propres.

**Note séparée** : `iter_d_pairs.py` n'a PAS été inspecté ligne-par-ligne dans
ce lot — flaggé `[À VÉRIFIER]` mais probablement clean (même famille).

### §3.2 — Strategy A (TSMOM v3 propfirm) : **SR 1.33 OOS FIABLE** ✓

Toutes les rolling().shift(1) sont en place côté signal (`signal.py:18-20,48,58,
70-71`). Position appliquée avec `positions.shift(1)` (backtest_v2.py:209,
tsmom_v3/backtest.py:93,184). La PnL utilise `arith_return` close-to-close
multiplié par la position lag-1. Pas de prix d'entrée explicite construit dans
le moteur, donc pas de fenêtre pour le pattern look-ahead sector_hothand.

**Strategy A est FROZEN** (LOT 1, 2026-05-30) ; cette validation reste utile au
cas d'un re-déploiement post-pivot.

### §3.3 — Strategy B (Delta-neutral carry) : **Sharpe backtest 4.10 (proxy 2.0)** ✓

Walk-forward avec split train/test stricts (backtest.py:204-294). Sélection
d'univers sur train, exécution OOS sur test. Pas de prix d'entrée "magique" ;
coût d'entrée déduit au premier bar (l.279-281). Pattern conforme L1.

**Strategy B est LIVE testnet** ; validation OK.

### §3.4 — Active research non documentée (re-vérification post-LOT 8)

| Strategy | Engine inspecté | Verdict |
|---|---|---|
| voie_b_ftmo | ftmo_voie_b_original.py + corr_c_b.py | **CLEAN** (open-to-close US, signal observable à 14:30 UTC) |
| strategy_d (pré-reg) | aucun engine encore | **N/A** |
| strategy_d_nq (infra) | aucun engine encore | **N/A** |
| nq_intraday_vwap | iter_01.py | **LOOK-AHEAD** (entry_price = close du bar de signal). Strat **déjà FAIL** N=19 (cf. iter_01_summary.md) — mais le verdict FAIL serait DURCI post-fix (le SR actuel inflatait peut-être l'apparence d'un edge). |
| sector_hothand_propfirm | engine.py | **LOOK-AHEAD CRITIQUE** (déjà audité 2026-05-30) |
| cip_eoq | aucun engine encore | **N/A** (sigma_estimation seul) |
| zn_baltussen | aucun engine à la racine | **N/A** |
| token_unlocks | aucun | **N/A** |
| vrp_short_gamma | aucun | **N/A** |

---

## §4. Synthèse — stratégies dont les métriques sont compromises

### (a) Métriques compromises (à recomputer post-fix)

1. **sector_hothand_propfirm** (active) — TOUTES les métriques compromises :
   - SR_net=2.05, SR_gross=2.52, DSR=2.01, t_HAC=10.4, alpha_ann=0.25, MDD=-13.3%
   - WF OOS folds 1-5 (toutes les SR_oos individuelles sont contaminées par le
     même bug d'engine)
   - FTMO P(pass) (déjà 5.1%, descendrait probablement < 2%)
   - Fichier : `Equities/research/active/sector_hothand_propfirm/results/phase1_baseline.json`

2. **nq_intraday_vwap iter_01** (active) — strat déjà flaggée FAIL pour N=19
   insuffisant. Les chiffres rapportés (`iter_01_summary.md`) sont également
   gonflés par le look-ahead. Le verdict FAIL reste, mais la cause "INSUFFICIENT
   SAMPLE" devrait être complétée par "ENGINE BUG entry_price=close à signal time".

3. **crash_recovery** (archived) — métriques de feasibility compromises.
   ARCHIVED depuis longtemps ; pas de pression à recomputer sauf si jamais
   re-proposée. À noter dans CLAUDE.md si on souhaite verrouiller le verdict.

### (b) Verdict spécifique sur Strategy C (NQ iter_10) : **FIABLE**

Sharpe 1.52, MaxDD -13.4%, WF 78%, N=346 : **fiables**. Aucun recompute
nécessaire. Preuve : `engine.py:115-119` (strict `> sig_ts` + entry au open
postérieur).

Conséquence pour le portfolio :
- Le gate D requirement `Sharpe(A+B+C+D) > 2.46` (CLAUDE.md:65) reste valide
  côté contribution C.
- sector_hothand_propfirm en tant que candidat D : **disqualifié** sous deux
  angles (look-ahead engine.py + MDD -13.3% > FTMO 10%).

### (c) Plan de fix chirurgical recommandé (NON appliqué ici)

Ordre de priorité, du plus urgent au moins :

#### Fix #1 — sector_hothand_propfirm (CRITIQUE, active)

**Fichier** : `Equities/research/active/sector_hothand_propfirm/engine.py:120`

Diff proposé :
```python
# AVANT (l.120)
entry_px = open_t if open_t < close_tm1 * (1 - daily_stop) else close_tm1
# APRÈS
entry_px = open_t   # always: signal at T-1 close → fill at T open
```

Plus la mise à jour de la check L1 (`phase1_baseline.py:564`) qui doit vérifier
NON SEULEMENT le `shift(1)` du signal MAIS AUSSI que `entry_px` n'utilise pas
de prix antérieur au signal.

**Re-run requis** :
- `python phase1_baseline.py` → re-génère `results/phase1_baseline.json` et
  `results/phase1_baseline.png`
- Si SR_net post-fix < 1.0 → `git mv ... → archived/`
- Si SR_net post-fix ≥ 1.0 mais MDD encore > 10% : ajouter overlay leverage cap
  avant FTMO consideration

Branch suggérée : `claude/fix-sector-hothand-engine-lookahead`.
Path covered par hard-fail auto-merge : `Equities/` n'est PAS dans la liste
hard-fail (CLAUDE.md:104-110) — auto-merge possible si seul `Equities/research/`
est touché. **Cependant** la modification d'un engine de stratégie pré-FTMO
devrait passer par revue humaine ; suggérer `needs-human-review` manuel.

#### Fix #2 — nq_intraday_vwap iter_01 (NON urgent, déjà FAIL)

**Fichier** : `Futures/research/active/nq_intraday_vwap/iter_01.py:266,273`

Diff proposé : pivoter vers le pattern Strategy C (`future.iloc[0]["open"]`).
OU : marquer le dossier comme "engine bug — see _audit/" et l'archiver tel
quel (le verdict FAIL N=19 ne changera pas substantiellement).

**Recommandation** : archive sans fix (le sample insuffisant N=19 est de toute
façon disqualifiant ; corriger l'engine ne fait pas passer la stratégie).
`git mv Futures/research/active/nq_intraday_vwap/ → archived/` + note dans le
POSTMORTEM.

#### Fix #3 — Documenter L1 dans CLAUDE.md (méthodologie)

Ajouter à `## Methodology toolkit` un sous-bloc spécifique au check L1 :

> **L1 check granulaire** : ne PAS se contenter de vérifier `signal.shift(1)`.
> Vérifier aussi :
> - le prix d'entrée utilisé dans la PnL (entry_px / entry_price / fill_price)
>   provient-il d'un bar **strictement postérieur** au timestamp du signal ?
> - si oui : strict `> sig_ts`, pas `>=` (pour éviter fill au prix qui a servi
>   au signal).
> - les opérations de stop/cooldown utilisent des prix d'observation, pas le
>   prix qui a fait fire le signal.

Citation des cas réels : sector_hothand (négatif), Strategy C engine (positif).

#### Fix #4 — Audit ligne-par-ligne des `[À VÉRIFIER]`

Avant tout déploiement Strategy D, lire en profondeur :
- `Futures/research/active/nq_intraday/analysis/iter_d_pairs.py`
- `Crypto/research/archived/patterns/orb_crypto/feasibility.py:371-372` (au cas
  où orb_crypto serait jamais re-proposée)

---

## §5. Note méthodologique — pourquoi ce bug est passé

Le sector_hothand `phase1_baseline.py:564` affirmait :
> | L1: signal T-1, trade T open | ✅ engine.run() shift(1) on all signals |

Cette check est INSUFFISANTE. Elle vérifie l'absence de `shift` mal-orienté sur
le signal, mais PAS la cohérence du prix de fill avec le timing du signal.
Pour vraiment garantir L1, il faut tracer le **chemin** :

```
signal[T-1] (data ≤ T-1 close)
   ↓ shift(1) au signal OU à la position
position[T]
   ↓ multiplied by
return[T]
   ↓ où return[T] est construit à partir de
prix_d_entrée[T] et prix_de_sortie[T]
   ↓ avec
prix_d_entrée[T] strictement postérieur à la connaissance de signal[T-1]
```

Le sector_hothand respectait l'étape `shift(1)` mais brisait l'étape
"prix_d_entrée[T] strictement postérieur". Pour future-proof, le check L1
de chaque nouveau moteur doit tracer ce chemin entièrement.

---

**Fin du rapport. Aucun fichier modifié hors `_audit/engine_contamination_2026-05-30.md`.**
