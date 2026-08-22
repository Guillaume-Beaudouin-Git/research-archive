# Gate 0 — Pre-registered noise floor (frozen BEFORE any v2 backtest)

Output (1) of the brief. The floor was computed and frozen to `results/noise_floor.json` **before** a single v2 candidate was scored — so the bar cannot be moved to fit a result.

## The question
Over the OOS hold-out **2025-01-01 → 2026-06-05 (T = 369 business days)**, how large an OOS annualised Sharpe arises from **pure luck** once you account for trying N strategies? A real edge must EXCEED it.

## Two independent estimates of the no-edge Sharpe SE (H0: true SR = 0)
| method | value |
|---|--:|
| Analytic (Lo 2002, Gaussian) = √(252/369) | 0.826 |
| Permutation — block-random sign on real index returns (net of cost) | 0.790 |
| Permutation — circular-shift-misaligned real signals (preserves autocorr + fat tails) | 0.845 |
| **SE0 (frozen = most conservative)** | **0.845** |

OOS index excess kurtosis = 21.4 (fat-tailed), which the permutation captures and the Gaussian does not — hence the permutation circular-shift SE (0.845) ≥ Gaussian (0.826) is used.

## The frozen threshold: OOS Sharpe a candidate must EXCEED to beat noise at cumulative N
`threshold(N) = SE0 · E[max of N iid N(0,1)]` (Bailey–López de Prado expected max).

| cumulative N | 70 | 97 (this iteration) | 110 | 120 |
|---|--:|--:|--:|--:|
| **OOS Sharpe to beat noise** | 2.03 | **2.13** | 2.17 | 2.19 |

> Multiple testing is **cumulative across iterations**: N = 70 burned (66 funnel + 4 step-2) + 27 v2 = **97**. The pre-registered bar for this iteration is **OOS Sharpe > 2.13**.

## Did any v2 candidate beat it?
**No.** Across all 27 v2 candidates the **maximum OOS Sharpe was 1.50** (`A.xsmom_idxgold_k60`, which has IS Sharpe −0.46 → OOS-luck, and is FTMO-non-compliant). 0 candidates exceeded 2.13; 0 cleared DSR>0.5.

Post-search check (the brief's exhaustion test): excluding the deliberately-included cost-suicide strategies (high-turnover intraday + triangular, all NET < −2 by construction), the **genuine-edge OOS-Sharpe dispersion = 0.690**, again **below the noise SE (0.845)** — i.e. the spread of real-candidate outcomes is *smaller* than chance would produce. **Universe exhausted at real cost, from a new angle. No lucky tail was hunted.**
