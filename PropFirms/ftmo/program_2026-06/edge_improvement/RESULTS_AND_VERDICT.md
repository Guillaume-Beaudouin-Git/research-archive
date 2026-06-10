# Edge improvement — results & verdict

Pre-registered set in `PRE_REGISTRATION.md` (frozen before running). All causal, real cost incl. **real per-night swap**, untouched OOS 2025-01→2026-06, walk-forward 6 folds, DSR at **cumulative N = 103** (97 funnels + 6 here; true N ≥ 500 also shown). Engine + cost model + DSR reused verbatim. Code: `run_improvements.py`; data: `results/improvement_results.json`.

## VERDICT: **No principled improvement clears the bar. The edges are structurally sub-threshold even when honestly, optimally engineered.**

Max OOS 12-mo p(pass) across all variants = **0.329 (the baseline)**; no CI-lower approaches 0.50; max DSR = 0.334 (N=103) / 0.174 (N=500) — all fail DSR>0.5. The √N combination does **not** help, because on FTMO-correct instruments the second edge (swap-net TSMOM) is **net-negative** — it dilutes RH rather than diversifying it.

## 1. The edges, honestly costed (full-history annualised Sharpe + CI)

| series | full | IS [90% CI] | OOS 25-26 [90% CI] | exkurt |
|---|--:|--:|--:|--:|
| **Ross Hook (deployable)** | +0.53 | +0.52 [0.22, 0.79] | **−0.07** [−0.88, 0.95] | 45 |
| TSMOM baseline (ETF proxies, swap-net) | +0.02 | −0.04 [−0.42, 0.32] | +0.92 [−0.57, 2.45] | 10 |
| **TSMOM I1 (FTMO-native CFDs) — swap-FREE ref** | **+1.11** | +0.95 [0.53, 1.37] | +0.89 [−0.60, 2.44] | 11 |
| **TSMOM I1 (FTMO-native CFDs) — swap-NET** | **−0.48** | −0.64 [−1.41, 0.19] | +0.31 [−1.42, 2.32] | 6 |

**Headline finding — instrument-correctness helped GROSS, swap then buried it.** Rebuilding TSMOM on FTMO-executable CFDs (US500/US100/GER40/XAUUSD/BTC) instead of the non-FTMO ETF proxies (GLD/SLV/USO) **lifted the swap-free Sharpe to +1.11** (cleaner instruments, and it drops the kurtosis-heavy ETF legs). **But swap-net it falls to −0.48 — *worse* than the ETF basket (+0.02).** Why: the equity+gold basket is structurally **long-biased** across the 2014-26 bull market, so it pays the measured −3.08 bps/night long-financing on leveraged (vol-targeted) notional almost continuously; the ETF basket's oil/silver shorts had *earned* some financing that offset it. The swap-free→swap-net bracket (**+1.11 → −0.48**) is the whole story: **real overnight financing on a long-biased multi-day trend book is the binding killer**, and it is *harder*, not easier, on the FTMO-correct instruments. (RH's swap is an uncosted multi-day residual — its true deployable Sharpe is somewhat below 0.53.)

## 2. Results table — every pre-registered book (L fixed ex-ante on IS)

| id | book | hist range | full Sh | IS | OOS | exk | WF folds (6) | %pos | DSR N103 / N500 | p(pass) OOS 6mo [CI] | OOS 12mo [CI] |
|---|---|---|--:|--:|--:|--:|---|--:|--:|--:|--:|
| **B0** | baseline RH+ETF-TSMOM (equal) | 2007-26 | 0.30 | 0.30 | 0.29 | 13.7 | .92/.32/−.04/.75/−.54/.27 | 67% | 0.118/0.045 | 0.234 [0.06, 0.57] | **0.329** [0.08, 0.71] |
| I2 | RH-alone (vol-targeted) | 2007-26 | 0.53 | 0.63 | −0.10 | 40.2 | .63/.71/−.04/1.05/.74/.26 | 83% | **0.334**/0.174 | 0.244 [0.08, 0.44] | 0.300 [0.11, 0.55] |
| I3 | ERC(RH + I1-TSMOM) | 2014-26 | 0.46 | 0.57 | −0.10 | 31.2 | −1.03/.86/1.13/.53/1.14/−.05 | 67% | 0.173/0.073 | 0.186 [0.04, 0.38] | 0.265 [0.07, 0.51] |
| I4 | const-vol book (equal) | 2014-26 | 0.20 | 0.27 | −0.28 | 25.4 | −1.14/.76/1.02/.51/.78/−.19 | 67% | 0.033/0.009 | 0.223 [0.09, 0.43] | 0.262 [0.12, 0.45] |
| **I5** | **improved (RH+I1, ERC, const-vol)** | 2014-26 | 0.46 | 0.53 | 0.04 | **13.4** | −.76/.86/1.21/.52/1.04/.07 | **83%** | 0.168/0.07 | 0.278 [0.13, 0.46] | 0.297 [0.14, 0.48] |
| I6 | best-case (RH+I1-crypto0, ERC, const-vol) | 2015-26 | 0.63 | 0.75 | 0.04 | 13.0 | .53/.32/1.01/1.24/.82/−.06 | 83% | 0.321/0.164 | 0.278 [0.13, 0.46] | 0.297 [0.14, 0.48] |

## 3. Best improved book vs survivors baseline
- **I5/I6 vs B0:** the principled stack (FTMO-native instruments + ERC + constant-vol) **improved the SHAPE** — excess kurtosis 13.7→13.0 and, vs the ERC-only I3 (kurt 31), constant-vol roughly **halved kurtosis** and lifted walk-forward %-positive to **83%** (vs 67%). But it **did not lift p(pass)**: OOS 12-mo went 0.329 (B0) → 0.297 (I5/I6) — *flat-to-slightly-lower*. The improvement bought robustness (smoother path, fewer negative folds), not financiability.
- **RH-alone (I2)** has the best DSR (0.334) and a real IS edge (0.63), but **OOS −0.10** (RH had a weak 2025-26) and excess kurtosis 40 — not deployable, and not improved by adding net-negative TSMOM.
- **Every horizon, every book: p(pass) point ≤ 0.33, CI-lower ≤ 0.14, DSR ≤ 0.33.** The bar (0.50 / DSR 0.5) is not approached.

## 4. Why principled engineering can't rescue these (the structural read)
1. **Swap dominates.** TSMOM's deployable Sharpe is bracketed −0.48 (swap-net) to +1.11 (swap-free) purely by overnight financing on a long-biased trend book. No allowed transform removes it (TSMOM *is* a multi-day-hold edge — it cannot be made intraday-flat without ceasing to be TSMOM).
2. **Only N=2 correlated momentum legs.** The √N lever needs ≥3 decorrelated edges; Sleeve C (MR) already failed inclusion, so combining RH with a net-negative TSMOM dilutes rather than diversifies.
3. **RH's recent OOS is negative**, so the single strongest edge isn't carrying the book either.
4. The improvements that *did* help (constant-vol shape, instrument correctness on gross) move kurtosis and robustness, not the post-cost mean — which is what the symmetric ±target/floor barrier prices.

**This confirms `research/PROGRAM_DECISION_MEMO.md`:** the lever is **swap measurement/reduction + a non-symmetric container** (where a +1.11 swap-free / robust-shape trend book could live), **not** further engineering of the symmetric-FTMO book. Empty result, honestly earned — not padded.
