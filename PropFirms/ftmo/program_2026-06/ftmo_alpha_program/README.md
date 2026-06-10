# FTMO Alpha Program — Phases 0–2

Execution of the *Propfirm Alpha Research Program* white paper: engineering a systematic
strategy whose **return distribution survives a symmetric drawdown barrier** (the
FTMO Standard evaluation: +10% target / −10% static max-DD / −5% daily floor, no time limit).

An FTMO challenge is a **first-passage problem**, not a profitability problem. The pass
probability is governed by the *shape* of the daily-return distribution against the barrier,
and is **scale-invariant** in account size. The single governing equation (symmetric phase):

```
P(pass one phase) = 1 / (1 + e^(-2 · S_d · n))
S_d = µ/σ  (daily Sharpe)          n = B/σ  (vol-units to the barrier)
```

so the levers are **daily Sharpe** and **per-day volatility** — and, crucially, *lower* σ
(higher n) raises survival. The winning profile is moderate-velocity, high-stability, patient
— the opposite of lumpy momentum books.

## Headline result (honest)

| Stage | Outcome |
|---|---|
| **Phase 0** — first-passage engine | ✅ MC reproduces the closed form to max err **0.0038** (gate passed). Table 1 & Figure 1 reproduced. |
| **Phase 0b** — CFD cost model | ✅ Reconciled to white-paper Table 3 from the realised MT5 spread feed. |
| **Phase 1** — intraday FX/CFD MR feasibility | ⚠️ Raw reversal edge **exists but is marginal** (EURUSD +1.5 bps/trade, t≈1.9). **No instrument clears the 3× cost gate** net of realistic CFD spread. |
| **Phase 2** — full validation | ❌ **NO-GO.** DSR ≈ 0.005 (multiple-testing deflated), walk-forward unstable (3/6 folds +), honest combined **P(pass) tops out at 66%** — never the 70% objective. |
| **Family-3** — intraday index pairs (Addendum B) | ❌ **NO-GO at the 2-leg cost gate.** Divergence reverts intraday (HL ~1.7h ✓) but best gross/cost ratio **0.60** (gate 3×); net Sharpe negative in- and out-of-sample. Structural (L11/L12, doubly binding). |
| **Family-4** — XAUUSD range-fade, honest stop (Addendum C) | ❌ **NO-GO — EDGE failure (terminal).** Gross Sharpe **negative at zero cost**, with/without stop, IS and on the untouched hold-out (OOS gross −1.07). The grid EAs' 90% WR is a pure averaging artefact. Honest FTMO P(pass) **5%** (below the ~30% zero-edge baseline). Not venue-fixable. |
| **Family-5** — equity-index overnight premium (Addendum D) | ❌ **NO-GO net — but the program's first robust gross OOS edge** (gross Sharpe 0.85 IS → **1.78 OOS**, low kurtosis: structural-premium prior *validated*). Net of financing ≈ zero (swap captures it; P(pass) ~30% ≈ zero-edge), directional beta, gap tail-DD 17%. **Carry is fundamental to leveraged overnight equity (embedded in futures basis) → NOT venue-fixable**, unlike a transaction-cost-killed reversal. |
| **Family-6** — BTCUSD intraday momentum (Addendum E) | ❌ **NO-GO under realistic crypto rules — but the first real net-positive, hold-out-surviving edge** (gross IS 1.33 → **OOS 0.80**, net OOS 0.59, per-trade t 2.1). Lumpy momentum: honest hold-out P(pass) ~47% (the 70%+ was *in-sample* — caught by independent verification), collapses at FTMO's reduced crypto daily floor (2–3%), would breach in the 2022 bear. Corroborates L24; real edge, wrong distribution/venue for a symmetric barrier. |

**Verdict: do not fund an evaluation on the current signal.** The validated engine, cost model
and suitability screen are retained for the next candidate.

This is the methodology working as designed: a gated, cost-first pipeline that **kills a candidate
that does not survive honest costing** rather than overfitting it into a false pass.

### EURUSD edge forensics (Addendum A — anti-overfit autopsy)

A dedicated follow-up dug into EURUSD specifically under a strict anti-overfit protocol — all
tuning in-sample (2022–2024), verdict on a **hold-out (2025–2026) never touched for any choice**,
cross-checked on an independent feed (Dukascopy), one pre-registered modification (L10), DSR-deflated.
**The edge is not real:** in-sample Sharpe 0.71 → **−0.12** on the untouched hold-out; only 0.15 on
the independent feed; per-year Sharpe sign-flips every year (+1.4/−1.3/+2.0/−0.6/+0.9); DSR ≈ **0.002**.
The pre-registered overreaction filter lifted the *in-sample* cost ratio but **made the hold-out worse**.
The in-sample 0.71 was in-sample luck + feed-specific microstructure. `run: research_eurusd_edge.py`.

### A methodological lesson (proposed L25)
A per-bar loss **cap** that keeps the position is *not* a stop — it mechanically lifts the mean of a
near-zero-edge series (cap-and-continue). It inflated EURUSD's Sharpe 0.71 → 1.32. Stops must be
modelled as *flatten-for-the-session* (optional stopping preserves the mean on a martingale).

## Layout

```
engine/
  ftmo_first_passage.py   closed-form pass-prob (Eq.1) + block-bootstrap absorbing-barrier simulator
  cfd_costs.py            CFD spread+swap cost model, calibrated to MT5 feed; Table-3 reconciliation
strategy/
  fx_data.py              Dukascopy / MT5 loaders, causal resampling, liquid-hours filter
  intraday_fx_mr.py       causal banded MR signal, per-trade & daily stats, vol-targeting, costs
  intraday_pairs.py       Family-3: market-neutral index-pair spread MR, causal hedge ratio, 2-leg costs
  xauusd_rangefade.py     Family-4: honest gold range-fade, stateful HARD stop (no grid/L25)
  overnight_premium.py    Family-5: equity-index overnight premium (gross vs net-of-swap)
  (Family-6 reuses intraday_fx_mr with an inverted z = momentum; see run_crypto.py)
  book.py                 diversified multi-instrument book (inverse-kurtosis weighting)
run_phase0_theory.py      Phase 0  — theory validation (Table 1, Fig 1, MC-vs-closed-form gate)
run_phase0b_costs.py      Phase 0b — CFD cost reconciliation
run_phase1_feasibility.py Phase 1  — IC + per-trade edge + pre-flight cost gate
run_phase2_validation.py  Phase 2  — suitability, walk-forward, DSR, FTMO MC, required-edge frontier
research_eurusd_edge.py   Addendum A — EURUSD anti-overfit forensics (untouched hold-out + indep. feed)
run_family3_pairs.py      Addendum B — Family-3 intraday index-pair relative-value (2-leg cost gate)
run_family4_xau.py        Addendum C — Family-4 XAUUSD honest range-fade (cost-vs-edge verdict)
run_overnight.py          Addendum D — Family-5 overnight equity premium (edge-vs-carry verdict)
run_crypto.py             Addendum E — Family-6 BTCUSD intraday momentum (edge-vs-distribution/floor)
make_report.py            assemble the PDF research note from results/*.json
                          (audit notes: _audit/{xauusd_rangefade_honest, overnight_premium,
                                        crypto_intraday}_2026-05.md)
run_all.py                run everything end-to-end
tests/test_engine.py      unit tests (closed form, MC reproduction, monotonicity)
figures/  results/        generated outputs
FTMO_Alpha_Program_Phases0-2_Report.pdf   the deliverable
```

## Run

```bash
pip install numpy pandas scipy statsmodels matplotlib reportlab pyarrow
python3 run_all.py        # or run_phase0_theory.py, ... individually
pytest -q tests/          # engine unit tests
```

## Methodology

Excess-return convention, HAC Newey–West t-stats (L8), Deflated Sharpe Ratio (Bailey & López de
Prado, L20), Politis–Romano stationary block bootstrap (loss-clustering preserved), walk-forward
≥5 folds, conservative retail cost markup (L23b), intraday-flat (no swap). Pass-probabilities are
design-stage Monte-Carlo estimates, not realised performance; all rule/cost parameters are
indicative and must be reconciled against the live FTMO portal before deployment.

**Data.** Dukascopy 1-min FX (EURUSD/GBPUSD, 2020–2024) and MT5 1-min CFD panels with realised
spreads (EURUSD, US500, US100, XAUUSD, GER40, US30, to 2026); common 2022–2024 validation window.
