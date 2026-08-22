# Edge improvement — disciplined, pre-registered enhancement of the two real edges

Take the program's two **real-but-sub-threshold** edges — Ross Hook (deployable ~0.53 full / −0.07 OOS) and multi-asset TSMOM — and test a SMALL, FIXED set of principled, near-zero-parameter improvements **without overfitting**. Not a variant hunt: the set was frozen before running, and DSR is deflated at the **cumulative** N (97 prior + 6 here).

## Verdict (one line)
**No principled improvement clears the bar.** Best OOS 12-mo p(pass) = 0.329 (baseline), DSR ≤ 0.334, no CI near 0.50 → the edges are **structurally sub-threshold for the symmetric FTMO barrier even when honestly, optimally engineered**. The binding killer is **real overnight swap** on a long-biased multi-day trend book (TSMOM gross +1.11 → net −0.48 on FTMO-correct instruments).

## Read in order
1. **`PRE_REGISTRATION.md`** — the ≤8 improvements + rationale + binding gate, frozen before any backtest.
2. **`RESULTS_AND_VERDICT.md`** — edges table, full results table (WF + full/IS/OOS Sharpe + CI + DSR@N + p(pass)±CI), best book vs baseline, structural read.
3. `results/improvement_results.json` — machine-readable.

## What was tested (6 pre-registered variants → cumulative N = 103; true N ≥ 500 also reported)
I1 FTMO-CFD-native TSMOM (correct instruments + real CFD swap) · I2 RH-alone · I3 ERC weighting · I4 constant-vol book · I5 improved book (RH+I1+ERC+const-vol) · I6 best-case (crypto-swap 0). All causal, real-cost incl. swap, untouched OOS, walk-forward 6 folds.

## Key findings
- **Instrument correctness helped gross, swap buried net:** FTMO-native TSMOM swap-free **+1.11** (beats ETF-proxy basket) but swap-net **−0.48** (worse) — a long-biased equity+gold trend book pays the −3.08 bps/night long financing continuously over the 2014-26 bull market.
- **Constant-vol targeting** is a real *shape* win (kurtosis 31→13, walk-forward 83% positive) but does not move p(pass).
- **Combining doesn't help** — with swap-net TSMOM net-negative on FTMO instruments, the √N lever dilutes RH instead of diversifying it; no book beats the baseline's OOS point estimate.

## Reused infra (verbatim — nothing rebuilt)
`research/ftmo_candidate_funnel/funnel_lib.py` (true-UTC daily + `CFDCostModel`) · `research/ftmo_portfolio_audit/code/firstpassage.py` (monotone 2-phase engine) · survivors `tsmom_regen.strat()` construction + measured swap rates (`research/ftmo_survivors_book/swap_sensitivity/`) · `dsr` (Bailey-LdP). RH series: `research/s076_replication/results/mtm_deployable.csv`.

## Reproduce
```bash
PY="<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/python"
"$PY" research/edge_improvement/run_improvements.py    # ~22 min (outer-bootstrap p(pass) CIs)
```

## Where this leaves it
Consistent with `research/PROGRAM_DECISION_MEMO.md`: principled engineering does not rescue the symmetric-FTMO book. The remaining levers are **measure/reduce real swap** (it brackets TSMOM from −0.48 to +1.11) and **a non-symmetric container** where a swap-free +1.11, low-kurtosis, 83%-positive-fold trend book could actually live — not more signal or portfolio engineering on this universe.
