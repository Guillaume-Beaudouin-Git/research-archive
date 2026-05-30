# Strategy C — FTMO $10K Monte Carlo (read-only sim, 2026-05-30)

**Objectif** : simuler le passage d'un challenge FTMO 10K avec Strategy C
(NQ opening momentum iter_10), estimer p(pass phase1) × p(pass phase2)
combiné en ≤ 40 jours de trading, sans look-ahead.

**Stratégie auditée** : iter_10, audit `_audit/engine_contamination_2026-05-30.md`
a confirmé **engine.py:115-119 CLEAN** — `future = self.rth[self.rth.index > sig_ts]`
+ `entry_price = future.iloc[0]["open"]`. Sharpe 1.52 / WF 78% / N=346 fiables.

**Aucun trade live. Aucun push.**

---

## ÉTAPE 1 — Sizing (BLOQUANT, résolu)

### Instrument du backtest

**NQ full**, pas MNQ. Preuves :

| Élément | Valeur | Preuve fichier:ligne |
|---|---|---|
| Point value | $20/pt | `Futures/research/active/nq_intraday/engine.py:7,26` |
| RT cost | $19/contract | `engine.py:9,28` |
| Calcul P&L | `pnl_usd = pnl_pts * 20 - 19` | `engine.py:167` |

Le backtest a donc tourné sur **NQ full $20/pt avec coût $19 RT**. Les
métriques rapportées (`results.json` entry iter_10) sont en **$/contrat NQ
full** : avg_winner=$1,571, avg_loser=-$421, max_dd=-13.4%, total=$45,510 sur 346 trades.

### Live cible : MNQ

| Élément | Valeur | Preuve |
|---|---|---|
| Symbole | MNQ | `Futures/live/strategy_c_live/config.py:54` |
| Point value | $2/pt | `config.py:84` |
| RT cost | $2.15/contract | `config.py:86` |

**Conversion analytique NQ→MNQ par contrat** :
- `pnl_mnq = pnl_pts × $2 - $2.15`
- Pour scaler le risque NQ ($400 SL) sur MNQ : il faut **10 MNQ**
  (10 × $2 × 20pts SL = $400)

### Risque sur compte FTMO 10K

Daily limit FTMO 5% = **$500**.

| Instrument | N | SL max ($) | % daily limit | Verdict |
|---|---|---|---|---|
| NQ full | 1 | $400 | **80%** | NON viable — un SL hit = 80% du buffer, deuxième trade losing = breach |
| MNQ | 1 | $40 | 8% | viable mais edge faible |
| MNQ | 3 | $120 | 24% | viable |
| MNQ | 5 | $200 | 40% | viable, marge réduite |
| MNQ | 10 | $400 | 80% | équivalent 1 NQ — même problème |

**Verdict ÉTAPE 1** :
- **C n'est PAS sizable proprement en NQ full sur 10K.** Un seul SL hit
  consomme 80% du daily limit ; deux losses consécutives = breach quasi-certain.
- **C est sizable en MNQ.** Candidats `N ∈ {1, 3, 5, 10}` simulés ci-dessous.
- Le Sharpe HAC est invariant à `N` (mean/std scalent ensemble) ; mais
  l'interaction avec les barrières absorbantes FTMO N'EST PAS invariante. D'où
  la nécessité de la sim Monte Carlo.

---

## ÉTAPE 2 — Sim Monte Carlo

### Pipeline (script `_audit/strategy_c_ftmo10k_sim.py`)

1. **Reconstruction du trade log** via `engine.NQBacktestEngine` + `iter_10_refined.build_signals`.
   Sanity check exécuté :
   - Sharpe HAC = 1.5212 ✓ (results.json = 1.5212)
   - MaxDD = -13.42% ✓
   - Total = $45,510.5 ✓ (= results.json)
   - N = 346 trades ✓
   → moteur reproduit la baseline à la décimale près.

2. **Conversion MNQ** : pour chaque trade, `pnl_per_mnq = pnl_pts × $2 - $2.15`
   ; multiplié par N contrats.

3. **Daily PnL series** : agrégation par jour avec zero-fill des jours
   sans trade (`pd.bdate_range`). T = **772 jours de trading** (2022-12 à 2025-12).

4. **Bootstrap par blocs (Politis-Romano stationary)** :
   `block_size = round(√772) = 28` jours. Préserve l'autocorrélation
   intraday (regroupement temporel des gros winners observés).
   **NE PAS confondre avec iid** : un bootstrap iid sous-estimerait
   le DD breach probability car les days are temporellement corrélés.

5. **Barrières absorbantes FTMO** :
   - Daily limit : breach si `day_pnl ≤ -$500 × max(1, peak_eod_equity/capital)`
     (i.e. 5% trailing depuis EOD peak — interpretation `propfirm_canonical.py:37`)
   - Max DD : breach si `equity ≤ $9,000` (floor static 10%)
   - Success P1 : `equity - $10,000 ≥ $1,000` avant 40 jours sans breach
   - Success P2 : reset à $10K, atteindre +$500 avant 40 jours sans breach
   - Combined : phases tirées indépendamment (Monte Carlo conservateur — la
     vraie passation est séquentielle mais sur deux comptes indépendants
     statistiquement)

6. **20,000 paths × 40 jours × 4 sizing candidates × 2 phases** = ~6.4M points
   simulés. Seed 42.

### Daily PnL distribution (par sizing)

| N MNQ | mean | std | min | max |
|---|---|---|---|---|
| 1 | $5.78/jr | $65.16 | -$44 | $447 |
| 3 | $17.35 | $195.49 | -$132 | $1,341 |
| 5 | $28.92 | $325.82 | -$220 | $2,236 |
| 10 | $57.83 | $651.64 | -$440 | $4,471 |

À N=10, le worst day (-$440) reste sous la daily limit ($500), donc
**daily breach = 0% partout** (cas NQ-équivalent borné par SL hard du backtest).

### Résultats principaux

| N MNQ | p(P1) | p(P2) | **p(combined)** | CI95 combined | Mediane jours total | DD breach P1 | Timeout P1 | P99 max DD P1 |
|---|---|---|---|---|---|---|---|---|
| 1 | 5.25% | 30.15% | **1.58%** | [1.49, 1.68] | 55 | 0.0% | 94.7% | 5.5% |
| 3 | 49.66% | 71.78% | **35.65%** | [35.06, 36.23] | 32 | 11.4% | 38.9% | 14.4% |
| 5 | 61.26% | 71.82% | **43.99%** | [43.38, 44.61] | 20 | 30.4% | 8.3% | 19.4% |
| 10 | 52.69% | 60.70% | **31.99%** | [31.43, 32.54] | 8 | 47.3% | 0.0% | 22.0% |

**Sweet spot** : **N=5 MNQ** maximise p(combined) à **43.99%** [CI95 43.4–44.6],
médiane 20 jours pour les deux phases.

Voir distribution `_audit/strategy_c_ftmo10k_sim_distrib.png` (4 sous-plots :
pass-prob vs sizing, breach decomposition, time-to-pass, tail DD).

### Décomposition des modes de failure (Phase 1)

- **N=1** : 94.7% timeout. Edge trop petit pour atteindre +$1,000 en 40j.
- **N=3** : 38.9% timeout + 11.4% DD breach. Sweet spot risque/timeout faiblement
  équilibré ; p(P1) = 50%.
- **N=5** : 30.4% DD breach + 8.3% timeout. DD breach devient dominant.
- **N=10** : 47.3% DD breach + 0% timeout. Sizing agressif, atteint rapidement
  soit le target soit le floor.

**Phase 2 (+$500) est systématiquement plus facile que P1** (70-72% à N=3-5)
car le target est plus petit ; le bottleneck est P1.

---

## ÉTAPE 3 — Verdict

### Objectif

> p(pass) combiné en ≤ 40 jours > 70% sur compte 10K ?

**NON ATTEINT.** Le maximum atteignable est **p(combined) = 44%** à N=5 MNQ,
loin du seuil 70%.

### Pourquoi ?

1. **Edge insuffisant face aux barrières serrées du 10K**. Strategy C génère des
   **gains lumpy** (win_rate 27.75%, avg_winner $1,571, avg_loser -$421 par NQ
   = ratio 3.7×). Cette asymétrie nécessite plusieurs trades pour réaliser
   l'edge — la sample size par fenêtre de 40j est trop petite (E[trades/40j]
   ≈ 18 dont ~5 winners attendus). La queue domine.

2. **Ratio target/buffer 2:1 contraignant**. Pour atteindre +$1K sans toucher
   le floor à -$1K, il faut un rendement net positif sur la fenêtre 40j.
   À N=5, l'espérance est positive (+$28.9/jr × 40 = +$1,156) mais la
   volatilité est de $326 × √40 = ~$2,062 (sur 40 jr). σ > E → la
   probabilité de finir sous le DD floor est substantielle (P99 max DD =
   19.4% > floor 10%).

3. **DD breach asymétrique**. Phase 1 doit générer +$1K SANS jamais toucher
   -$1K. Strategy C peut produire des séries de drawdowns (avg_loser ≈ 80%
   du daily limit) qui s'enchaînent avant qu'un winner ne les compense.
   À N=10, 47% des paths buster avant atteindre le target.

### Ce qui débloque

| Levier | Impact estimé | Trade-off |
|---|---|---|
| **Compte plus gros (15K, 20K, 25K)** | Compte 25K Tradeify : 2 MNQ donne déjà 57% pass eval 180j (cf. `config.py:13`). Sur 25K, ratio target/DD inverse est 6:1 (target 6%, DD 4% trailing) — beaucoup plus de marge. | Coût challenge plus élevé. |
| **Sizing dynamique inter-phase** : N=5 P1 puis N=2-3 P2 | Marginal +3-5pp (P2 déjà 71% à N=3) | Logique d'exécution plus complexe. |
| **Sizing dynamique intra-phase** : downsize si equity < -3%, upsize si > +5% | +5-10pp estimé | Hors scope (modifie l'engine). |
| **Allonger la fenêtre à 60j** | +10-15pp estimé | Contredit la contrainte perso 40j. |
| **Re-tuner SL_CAP plus serré** (e.g. $250 au lieu de $400) | Réduit DD breach mais réduit aussi avg_winner | Hors scope (modifie le signal, viole "max 3 mods" L10). |
| **Filtre régime** | Inconnu, hors scope (risque overfitting) | — |

### Verdict opérationnel honnête

- **Sur 10K FTMO en 40 jours** : Strategy C iter_10 **NE PASSE PAS** > 70%
  p(pass). Le meilleur sizing trouvé (N=5 MNQ) délivre **44%**, soit
  ~1 chance sur 2.3. Pour une stratégie de pass de challenge, c'est
  insuffisant.

- **L'edge net n'est PAS le problème** (Sharpe 1.52 HAC, WF 78%, avg_trade
  $131/contrat NQ après coûts). Le problème est **structurel** : sur un
  petit compte avec barrières serrées et horizon court, la variance domine
  l'edge. Strategy C est faite pour des comptes de 25K+ où les barrières
  donnent plus d'air.

- **Recommandation forte** : **ne pas acheter un FTMO 10K pour Strategy C.**
  Cibler un compte 25K ou plus (Tradeify Select Flex $25K déjà validé à
  57% pass 180j, FTMO 25K équivalent ou supérieur), OU laisser tourner sur
  un Tradeify $25K (cible live actuelle) et capitaliser l'edge sur les
  payouts plutôt que sur un nouveau challenge 10K.

- **Si l'achat 10K est non-négociable** : démarrer à **N=5 MNQ** (max
  p(pass) au sweet spot), accepter le 44% comme baseline. Tout sizing
  > N=5 augmente la queue DD breach plus vite qu'il n'augmente p(pass).

---

## Annexe — preuves et reproductibilité

| Élément | Source |
|---|---|
| Sharpe / MaxDD / N rapportés | `Futures/research/active/nq_intraday/results.json` entry "iter_10" |
| Engine clean | `engine.py:115-119` (audit `_audit/engine_contamination_2026-05-30.md` §3.1) |
| FTMO 5/10 canoniques | `Portfolio/risk/propfirm_canonical.py:37-38` (daily 5% trailing EOD peak ; max DD 10% static from starting balance) |
| Cost MNQ live | `config.py:86` MNQ_COST_RT = $2.15 |
| Sizing Tradeify 25K référence | `config.py:13` "P(pass eval 180d) = 57.0%" |
| Script de sim | `_audit/strategy_c_ftmo10k_sim.py` (autonome, reproductible avec venv local Python 3.12.9) |
| Résultats numériques | `_audit/strategy_c_ftmo10k_sim_results.json` |
| Distribution plots | `_audit/strategy_c_ftmo10k_sim_distrib.png` |

**Reproduction** :
```bash
"<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/python3" \
  _audit/strategy_c_ftmo10k_sim.py
```
~30 secondes sur M1.
