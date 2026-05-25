# Tradeify Select Flex $25K — Audit 2026-05-25

Branch: `fix/review-codebase-pre-paper`
Source of truth: `PropFirms/tradeify/rules.md` (last_verified: 2026-05-25)
Trigger: ERRATUM on commit 11c1eca — funded_DD was set to $1,500; correct value is $1,000.

---

## Métriques autoritaires (Select Flex $25K)

| Rule | Value | Source | Notes |
|------|-------|--------|-------|
| Starting capital | $25,000 | rules.md ✓ | |
| Profit target (eval) | $1,500 | rules.md ✓ | 6% of capital |
| Trailing DD (eval) | $1,000 EOD trailing | rules.md ✓ | Eval floor starts at $24,000 |
| Trailing DD (funded) | **$1,000 EOD trailing** | rules.md ✓ (2026-05-25) | **Identical to eval** — NOT $1,500 |
| Daily loss limit (eval) | NONE | rules.md ✓ | |
| Daily loss limit (funded) | NONE | rules.md ✓ | Select Flex differentiator |
| Consistency cap (eval) | 40% of profit target = $600/day | rules.md ✓ | |
| Consistency (funded) | NONE | rules.md ✓ | Select Flex only |
| Min trading days (eval) | 3 | rules.md ✓ | |
| Lock trigger | EOD equity ≥ $26,100 OR first payout | rules.md ✓ | $25,000 + $1,000 + $100 |
| Locked floor | $25,100 | rules.md ✓ | capital + $100 |
| Payout trigger | 5 winning days (≥$100 each) | rules.md ✓ | since last payout |
| Payout amount | 50% of profits, capped at $1,250 | rules.md ✓ | |
| First payout → lock | YES | rules.md ✓ | |
| Challenge cost | $65 (promo MAY), ~$170 standard | rules.md ⚠️ | standard from training data |
| CME futures | YES (NQ, MNQ via Tradovate) | rules.md ✓ | |

---

## Occurrences trouvées

### config.py

| Line | Variable / Context | Value (committed HEAD) | Expected | Status |
|------|-------------------|----------------------|----------|--------|
| 103 | `TRADEIFY_TRAILING_DD_FUNDED` | 1,500 | 1,000 | **WRONG** → corrected in working tree |
| 106 | `TRADEIFY_LOCK_BALANCE` | 26,600 | 26,100 | **WRONG** → corrected in working tree |
| 8 | docstring "locks to $26,600" | $26,600 | $26,100 | **WRONG** → corrected in working tree |
| 95 | comment "Funded trailing DD: $1,500" | $1,500 | $1,000 | **WRONG** → corrected in working tree |
| 97 | comment "Lock trigger: EOD ≥ $26,600" | $26,600 | $26,100 | **WRONG** → corrected in working tree |
| 15 | "Phase 1 — Eval: up to +$1,500 eval target" | $1,500 | $1,500 (profit target) | **CORRECT** (profit target, not DD) |
| 108 | `TRADEIFY_PROFIT_TARGET = 1_500` | 1,500 | 1,500 (profit target) | **CORRECT** |
| — | `DAILY_LOSS_LIMIT_FUNDED_FLEX` | missing | None | **ADDED** in this commit |
| — | `CHALLENGE_COST` | missing | 65 | **ADDED** in this commit |
| — | `TRADEIFY_TRAILING_DD_FUNDED` name | exists | rename → `TRADEIFY_TRAILING_DD` | **RENAMED** (eval=funded identical) |

### challenge_state.py

| Line | Context | Value (committed HEAD) | Expected | Status |
|------|---------|----------------------|----------|--------|
| 11 | docstring "Lock trigger: EOD balance ≥ $26,600" | $26,600 | $26,100 | **WRONG** → corrected in working tree |

### tests/test_tradeify_constants.py

| Line | Context | Value (committed HEAD) | Expected | Status |
|------|---------|----------------------|----------|--------|
| 39 | `TRADEIFY_TRAILING_DD_FUNDED == 1_500` | 1,500 | 1,000 | **WRONG** → corrected in working tree |
| 47 | docstring "funded_DD + $100 = $26,600" | $26,600 | $26,100 | **WRONG** → corrected in working tree |
| 53 | `== expected == 26_600` | 26,600 | 26,100 | **WRONG** → corrected in working tree |
| 105 | `cfg.trailing_dd_funded == config.TRADEIFY_TRAILING_DD_FUNDED` | FUNDED | TRAILING_DD | **RENAMED** in this commit |

### tests/test_challenge_state.py

| Line | Context | Value (committed HEAD) | Expected | Status |
|------|---------|----------------------|----------|--------|
| 4 | docstring "balance >= $26,600" | $26,600 | $26,100 | **WRONG** → corrected in working tree |
| 46 | test docstring "$26,600" | $26,600 | $26,100 | **WRONG** → corrected in working tree |
| 54 | test docstring "below $26,600" | $26,600 | $26,100 | **WRONG** → corrected in working tree |
| 81 | comment "$26,600 AND payout" | $26,600 | $26,100 | **WRONG** → corrected in working tree |

### run_daily.py

| Line | Context | Value (committed HEAD) | Expected | Status |
|------|---------|----------------------|----------|--------|
| 298 | comment "EOD balance >= $26,600" | $26,600 | $26,100 | **WRONG** → corrected in this commit |

### MANUAL_PAPER_TRADE_PROTOCOL.md

| Line | Context | Value | Expected | Status |
|------|---------|-------|----------|--------|
| 112 | "Lock balance = $26,600 (Phase 2.6)" | $26,600 | $26,100 | **WRONG** → corrected in this commit |

### REVIEW_FIXES_2026-05-25.md

| Line | Context | Value | Expected | Status |
|------|---------|-------|----------|--------|
| 58 | "predating both the $26,600 correction" | $26,600 | historical ref (wrong) | **WRONG** → ERRATUM added |
| 102 | "EOD balance >= $26,600" | $26,600 | $26,100 | **WRONG** → corrected in this commit |
| 120 | table: `TRADEIFY_LOCK_BALANCE → 26,600` | 26,600 | 26,100 | **WRONG** → ERRATUM added |
| 123 | table: `TRADEIFY_TRAILING_DD_FUNDED → 1,500` | 1,500 | 1,000 | **WRONG** → ERRATUM added |
| 175 | GO/NO-GO "OR, $26,600" | $26,600 | $26,100 | **WRONG** → corrected in this commit |
| 177 | GO/NO-GO "Lock threshold correct ($26,600)" | $26,600 | $26,100 | **WRONG** → corrected in this commit |
| 87 | "must accumulate $1,500 of capped wins" | $1,500 | $1,500 (profit target) | **CORRECT** |
| 141 | "target=$1,500" | $1,500 | $1,500 (profit target) | **CORRECT** |
| 157 | "eval_DD=$1,500, old wrong config" | $1,500 | explicit "wrong" label | **CORRECT** (historical) |

### Portfolio/risk/trailing_dd_simulator.py

| Line | Context | Value (committed HEAD) | Expected | Status |
|------|---------|----------------------|----------|--------|
| 3 | module docstring "Funded: EOD trailing DD ($1,500)" | $1,500 | $1,000 | **WRONG** → corrected in working tree |
| 35 | `trailing_dd_funded: float = 1_500.0` | 1,500 | 1,000 | **WRONG** → corrected in working tree |
| 284 | docstring "3 MNQ + $1,500 DD: P(pass)≈66%" | $1,500, 66% | $1,000, 53.7% | **WRONG** → corrected in this commit |

### Portfolio/risk/tests/test_trailing_dd_simulator.py

| Line | Context | Value | Expected | Status |
|------|---------|-------|----------|--------|
| 18 | `BASELINE_CONFIG: Historical baseline... $1,500 eval DD` | $1,500 | $1,500 (explicit "old wrong") | **CORRECT** (historical regression fixture) |
| 21-22 | `BASELINE_CONFIG` with `trailing_dd_eval=1_500, trailing_dd_funded=1_500` | $1,500 | $1,500 (historical) | **CORRECT** (intentional old-config fixture) |
| 33 | comment "$25,000 - $1,500 → $23,500" | computed loss of $1,500 | loss of $1,500 (test scenario) | **CORRECT** ($1,500 is loss amount, not DD rule) |
| 69 | comment "equity never reaches $26,600" | $26,600 | $26,100 | **WRONG** → corrected in this commit |
| 80 | comment "lock_threshold 26,600" | $26,600 | $26,100 | **WRONG** → corrected in this commit |

### PropFirms/comparison.md

| Line | Context | Value | Expected | Status |
|------|---------|-------|----------|--------|
| 16 | DD funded column "✓ $1,500" | $1,500 | $1,000 | **WRONG** → corrected in this commit |
| 16 | Lock "EOD≥$26,600 or 1st payout" | $26,600 | $26,100 | **WRONG** → corrected in this commit |
| 31 | "Lock at $26,600 provides breakeven" | $26,600 | $26,100 | **WRONG** → corrected in this commit |

### Futures/research/active/nq_intraday/sizing_analysis.py

| Line | Context | Value (committed HEAD) | Expected | Status |
|------|---------|----------------------|----------|--------|
| 309 | print statement "trailing_dd_funded=$1,500 | lock_trigger=$26,600" | $1,500, $26,600 | $1,000, $26,100 | **WRONG** → corrected in working tree |
| 633 | print statement "funded_DD=$1,500 | lock=$26,600" | $1,500, $26,600 | $1,000, $26,100 | **WRONG** → corrected in working tree |

### validate_tradovate.py

| Line | Context | Value | Expected | Status |
|------|---------|-------|----------|--------|
| 222-223 | T5.2 comment: "trailing DD $1,500" → "$26,000-$24,500=$1,500" | computed value $1,500 | test scenario value | **AMBIGUOUS** — $1,500 is the COMPUTED drawdown in the test (peak $26,000 − current $24,500), not the DD rule limit. The guardrail check ($1,500 ≥ $1,300) remains valid regardless of rule. Not modified. |

### PRE_DEPLOYMENT_AUDIT.md

| Line | Context | Status |
|------|---------|--------|
| 86 | "TRAILING_DD_BREACH: $1,500.00 from peak $51,500" | **AMBIGUOUS** — computed test scenario value, not rule limit |
| 90 | "trailing DD = $1,500. Designed to PASS when GUARDRAIL_TRAILING_DD_USD = $1,750" | **AMBIGUOUS** — historical test design predating $25K config |
| 127 | "${2_000:,} in exception message" | **AMBIGUOUS** — legacy $50K config test |
| 204 | "current=24_500, trailing_dd=1,500 >= 1,300" | **AMBIGUOUS** — computed test scenario value |

All PRE_DEPLOYMENT_AUDIT entries predate the $25K canonical config. Not modified.

---

## Corrections appliquées (ce commit)

| File | Correction | Type |
|------|-----------|------|
| `config.py` | `TRADEIFY_TRAILING_DD_FUNDED = 1_500` → `TRADEIFY_TRAILING_DD = 1_000` | Valeur + renommage |
| `config.py` | `TRADEIFY_LOCK_BALANCE = 26_600` → `26_100` | Valeur |
| `config.py` | Ajout `DAILY_LOSS_LIMIT_FUNDED_FLEX = None` | Nouveau champ |
| `config.py` | Ajout `CHALLENGE_COST = 65` | Nouveau champ |
| `config.py` | Commentaires docstring/guardrails | Textuel |
| `challenge_state.py` | Docstring `$26,600` → `$26,100` | Textuel |
| `tests/test_tradeify_constants.py` | `TRADEIFY_TRAILING_DD_FUNDED` → `TRADEIFY_TRAILING_DD`, valeur 1_500→1_000, 26_600→26_100 | Tests |
| `tests/test_challenge_state.py` | Docstrings/comments `$26,600` → `$26,100` | Textuel |
| `run_daily.py:298` | Comment `$26,600` → `$26,100` | Textuel |
| `MANUAL_PAPER_TRADE_PROTOCOL.md:112` | `$26,600` → `$26,100` | Textuel |
| `REVIEW_FIXES_2026-05-25.md` | ERRATUM section + table ❌ annotations + GO/NO-GO checklist | Documentation |
| `Portfolio/risk/trailing_dd_simulator.py` | Module docstring + `PropfirmConfig.trailing_dd_funded = 1_500` → `1_000` + docstring line 284 | Valeur + textuel |
| `Portfolio/risk/tests/test_trailing_dd_simulator.py` | Comments `$26,600` → `$26,100` (×2) | Textuel |
| `PropFirms/comparison.md` | DD funded `$1,500` → `$1,000`, lock `$26,600` → `$26,100` (×2) | Valeur |
| `Futures/research/active/nq_intraday/sizing_analysis.py` | Print statements `$1,500` → `$1,000`, `$26,600` → `$26,100` | Textuel |
| `CLAUDE.md` | L22 + pin comment strategy C | Documentation |

---

## MC simulation — verdict

**Question**: Les résultats MC (commit 9b88824, N=20k seed=42) utilisaient-ils `funded_DD=$1,500`?

**Réponse**: OUI — à la date du commit 9b88824, `PropfirmConfig.trailing_dd_funded = 1_500`.

**Impact**: NULS. Rerun confirmé 2026-05-25 avec `funded_DD=$1,000` :

| MNQ | P(pass) | P(bust) | P(timeout) | E[days] | Δ vs MC initial |
|-----|---------|---------|------------|---------|-----------------|
| 1   | 37.5%   | 5.1%    | 57.4%      | 122.6d  | 0.0pp |
| **2** | **62.6%** | **34.1%** | **3.2%** | **72.4d** | **0.0pp** |
| 3   | 53.7%   | 46.2%   | 0.0%       | 38.4d   | 0.0pp |
| 4   | 47.4%   | 52.5%   | 0.0%       | 23.6d   | 0.0pp |

Explication: les busts de la phase funded sont négligeables vs eval. Le P(bust) est
dominé par les busts eval (runway DD = 11.8 losses-days à 2 MNQ, busts surviennent
rapidement). **La recommandation 2 MNQ est confirmée et robuste.**

---

## Ambiguous — needs human review

1. **`validate_tradovate.py:222-223`** — `$1,500` = drawdown calculé dans le test
   (peak $26,000 − current $24,500), pas la règle. Test toujours valide.
2. **`PRE_DEPLOYMENT_AUDIT.md:86,90,127,204`** — scénarios de test historiques
   (configs $50K/FTMO legacy), non concernés par la correction $25K.
