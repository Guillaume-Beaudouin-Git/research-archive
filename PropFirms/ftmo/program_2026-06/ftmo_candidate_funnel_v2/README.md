# FTMO 10k 2-step — Candidate Funnel, ITERATION 2

Second-iteration triage that searches **only the spaces iteration 1 structurally did not cover**, with a noise floor pre-registered **before** any backtest and DSR deflated at the **cumulative** trial count (multiple testing does not reset across iterations).

## VERDICT — did v2 find anything iteration 1 missed?
**No. v2 confirms the free-price-data ceiling from a genuinely new angle — and adds one new structural fact.**
- **0 DSR-certified survivors; 0 of 27 candidates beat the pre-registered noise floor** (max OOS Sharpe **1.50** vs floor **2.13** at cumulative N=97).
- The genuine-edge OOS-Sharpe dispersion (**0.690**, cost-suicide strategies excluded) is **again below the noise SE (0.845)** — outcomes indistinguishable from coin-flips, exactly as in iteration 1, now reached from the uncovered spaces. **Second exhaustion VERIFIED.**
- **New structural finding (iter-1 was daily-only, could not show this):** index intraday returns at **15/30min do NOT mean-revert** — session-fade **gross** IS Sharpe is negative for all 8 index×frequency combos. The "intraday reversion" premise fails *before costs*; costs then bury it. This closes the sub-60min index-reversion question, not just at the cost margin but at the **mechanism** level.
- Multi-leg RV (space A): no gross edge to dilute costs against; the only FTMO-compliant structure (equity-vs-gold) is flat-to-negative; the rest violate the hedging rule anyway.
- Regime/calendar conditioning (space B): only sub-threshold lift (confirms L15) — the conditioned TSMOM is the *same* sub-threshold premium iter-1 already characterised, never above the floor.

The honest read: on **free price data, the FTMO-executable 16-instrument universe, at daily-and-coarser frequency, with real costs**, the symmetric-barrier edge is exhausted across two independent search iterations (97 cumulative trials). The remaining avenues are **not new signals** but a **new data source** (more, less-correlated legs with validated spreads — paid) or a **different container** (personal book / trailing-DD firm where the floor isn't symmetric to the target). Both are flagged in `LIMITATIONS.md`, not claimed.

## Read in this order
1. **`NOISE_FLOOR.md`** — output (1): the pre-registered floor (SE0=0.845, threshold 2.13 at N=97) + that nothing beat it.
2. **`SHORTLIST.md`** — output (2): the **empty** survivor list + near-miss table + mutual/tail correlation matrix.
3. **`LONGLIST.md`** — output (3): all 27 v2 configs (A/B/C) with one-line kills + the 70 burned referenced as pre-excluded.
4. **`LIMITATIONS.md`** — output (4): intraday/RV/DSR caveats + what's not testable.

## Code (this folder; reuses iter-1 `funnel_lib.py` + CFDCostModel + ftmo_first_passage + dsr.py verbatim)
- `build_intraday_cache.py` — M1 → 15/30min index bars (`cache/`). READ-ONLY source.
- `gate0_noise_floor.py` — pre-registered floor (analytic Lo-SE + permutation) → `results/noise_floor.json`.
- `v2_lib.py` — intraday-flat MR engine, multi-leg RV builders, causal regime conditioning.
- `run_v2.py` — 27-config roster (spaces A/B/C), DSR at cumulative N=97, exhaustion test → `results/`.

## Reproduce
```bash
PY="<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/python"
"$PY" research/ftmo_candidate_funnel_v2/build_intraday_cache.py   # ~12s, READ-ONLY
"$PY" research/ftmo_candidate_funnel_v2/gate0_noise_floor.py       # freezes the floor FIRST
"$PY" research/ftmo_candidate_funnel_v2/run_v2.py                  # ~3s
```

## Key artifacts (`results/`)
`noise_floor.json` (frozen floor) · `v2_all_trials.csv/json` (27 configs) · `v2_summary.json` (cumulative N, floor, dispersion, exhaustion flag) · `v2_top_corr.csv` (near-miss correlation).

## Cumulative honesty ledger
N = **97** = 66 funnel + 4 step-2 + 27 v2. Multiple testing carried forward across all three runs. A third iteration on this universe/data would raise N further and the bar with it — so the rational next move is **not** another price-signal search but the data/container avenues above.
