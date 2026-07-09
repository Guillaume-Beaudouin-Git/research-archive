# Phase B Results — Dual vs Single Momentum (commodity futures)

**Date:** 2026-07-09 · **Pre-registration:** `../PHASE_B_PREREGISTRATION_dual_momentum_2026-07-09.md`
(frozen before this run; no deviation from §4–§7). **Data:** 24 continuous futures,
2005-01 → 2026-07, 259 monthly obs. Grid: 8 (L,s) cells × {XS, DUAL} = 16 configs.

## Verdict: **FALSIFIED — not deployable** (clean, as the prior expected)

`G1=False · G2=True · G3=False · G5=False · DSR=0.004 (FAIL)` → deployable = **False**.

| Gate | Result | Pass |
|---|---|:--:|
| 1 — Sharpe stability (DUAL std < XS std) | XS std 0.111 vs **DUAL std 0.146** (more dispersed) | ✗ |
| 2 — MaxDD matched-vol (DUAL less negative) | XS median −0.544 vs DUAL −0.506 (marginal) | ✓ |
| 3 — Two-sided (both legs +, best DUAL cell) | long_sr +0.37 but **short_sr −0.56** | ✗ |
| 4 — IC (monthly XS, HAC lag2) | **negative & significant**: ic_t −2.6 to −3.4 on several cells | — |
| 5 — OOS post-2015 (best DUAL cell) | sr_pre −0.12, **sr_post −0.25** | ✗ |
| 6 — DSR (best DUAL, 16 trials) | monthly SR −0.056, **DSR 0.004** | ✗ |

**Every one of the 16 configs has a negative net monthly Sharpe** (XS −0.22 to −0.54;
DUAL −0.19 to −0.53). Annualised turnover 14–24× → cost drag ≈ 0.15–0.20%/yr: **cost is
NOT the killer** (as pre-registered), the signal is.

## Why it fails (mechanism, not noise)
- **Commodity cross-sectional momentum is REVERSAL over 2005–2026.** The IC is negative and
  significant (t down to −3.4): high-past-return commodities *under*perform next month. The
  short leg confirms it — shorting low-momentum names **loses** (short_sr ≈ −0.5 to −0.9)
  because low-past-return commodities rebound. The whole XS-momentum construction points the
  wrong way.
- **Dual momentum cannot rescue a wrong-signed signal.** Its flat-to-cash mechanism works as
  designed — it trims matched-vol MaxDD a hair (Gate 2, the only "win") — but there is no
  alpha to manage. DUAL is even *more* dispersed across params (Gate 1 fails), the opposite
  of the paper's robustness claim (which was measured on N=4 ETFs, 2007–2026; L5 + N≪30).

## Honest caveats
- **N ≈ 20–24 < 30** (methodology floor). The XS test is *suggestive*, per the pre-reg — but
  the three decisive negatives (two-sided fail, DSR 0.004, significantly-negative IC) all
  agree, so the "no" is robust, not a small-N artefact.
- This kills the **dual-momentum enhancement of the S_TSMOM leg**, NOT the whole
  `xs_basis_tsmom` mission: the **S_BASIS leg is untested** (needs `fetch_front_second.py`;
  Phase A basis coverage only 13%). Commodity XS is known to be **basis/roll-yield driven,
  not price-momentum driven** — consistent with this reversal finding.

## Constructive by-product (NOT acted on — needs its own pre-registration)
The significantly-negative IC is a *measured* pre-registered output (Gate 4), and it points
at **cross-sectional reversal / basis-carry** as the live axis in commodities. This is a
NEW hypothesis: inverting or reframing the signal now would be HARKing/data-snooping against
this run's frozen spec. Logged for a **separate, freshly pre-registered** test (which also
motivates finishing the S_BASIS leg — Erb-Harvey basis is the natural mechanism behind a
commodity XS reversal). No performance number is reported for it here, by design.

## n_tests
Proposed (not graved): **+16** DSR trials for this Phase B grid. Reconcile manually.

## Artefacts
- `results/phase_b_dual_momentum_grid.csv` — full 16-config table.
- `signals/momentum.py` — signals + monthly backtest.
- price cache `data/cache/continuous_close_2005_2026.parquet` (gitignored, regenerable via
  `data/fetch_continuous.py`).

---
*Backtest run 2026-07-09 on the frozen pre-registration. FALSIFIED cleanly; the prior
("commodity XS momentum decayed post-2015 → low base rate") is confirmed, with the sharper
finding that it is not merely decayed but sign-flipped to reversal.*
