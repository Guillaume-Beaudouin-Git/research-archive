# REPORT — Non-crypto multi-asset daily trend sleeve on FUTURES

**Date:** 2026-06-14 · **Status:** research, not investment advice
**Pre-registration:** `PREREG.md` (locked + git-committed `6163805` BEFORE any data/signal contact)
**Engine/data verified:** V1–V7 PASS (`verify.py`) · **Trials:** `trials_log.csv` (50 logged, 29 distinct DSR trials)

---

## 0. VERDICT — **NO-GO (NO SLOT). Clean kill.**

A non-crypto multi-asset daily trend sleeve on futures **does not** earn a slot in the A+B book.
The corner that was killed on FTMO by the overnight CFD swap (L36) is **legitimately open on
futures** — and the futures version is confirmed **cost/​swap-immune** (Sharpe 0.50→0.47 at 3× all
frictions). But removing the swap reveals the underlying edge was **merely thin, not merely
cost-burdened**. Three of the four pre-registered kill criteria fire, and no single configuration
passes the kill criteria *and* the gates simultaneously:

| | K1 DSR | K2 two-sided | K3 marginal-to-A+B | K4 walk-forward | RESEARCH_PASS (SR>0.7) | Book-slot |
|---|---|---|---|---|---|---|
| two-sided base (pre-reg primary, SR 0.50) | **KILL** (−0.33) | **KILL** (shorts lose 5/7 assets) | **NO SLOT** (ERC 2.31→1.95) | ok | ✗ (0.50) | ✗ |
| long_only (K2 survivor, SR 0.68) | **KILL** (−0.15) | survives | **NO SLOT** (ERC →2.03) | ok | ✗ (0.68) | ✗ |
| H1b short-energy-only (SR 0.87) | barely (+0.04) | **KILL** (CL short = 2014–16 artifact) | **NO SLOT** (ERC →2.10) | ok | ✓ | ✗ |

**The configs that survive K2 fail K1; the config that survives K1 fails K2. None gets a book slot.**

**Honest forward probability.** The full-sample Sharpe (0.50 two-sided / 0.68 long-only) is a blend
of a weak 2014–2019 regime (Sharpe ~0.21) and an exceptional 2020–2026 trend regime (Sharpe
~0.68–1.02). Absent another COVID/2022-style macro-trend regime, the **forward-expected standalone
Sharpe is ~0.2–0.5**, and the **marginal contribution to the A+B book is ≤ 0** under the project's
own equal-risk methodology. Probability this clears the Book-slot bar on a forward sample: **low
(≈10–20%), and only in a sustained strong-trend regime** — not a basis for deployment.

---

## 1. What was tested (pre-registered, locked)

The verified Ed-Seykota engine from the PRIOR (`data/seykota_trend/`, full-system 0.94 / long-only
1.19) — but that prior was **CFD/spot and ~55% BTC+ETH** (BTC 44% + ETH 11%). This study re-ran the
**same rules on NON-CRYPTO FUTURES** with a futures-correct cost model and a marginal-to-A+B lens:

- **Universe (core):** NQ, ES, GC, CL, 6E, 6A, 6B (sized as micros MNQ/MES/MGC/MCL/M6E/M6A/M6B for a
  $100k book). Extension (Phase 4): RTY, SI, ZN.
- **Data:** yfinance continuous `=F` + proportional back-adjustment (roll-window argmax-gap
  neutralization). **Validated against the local Databento NQ gold** (weekly return corr **0.975**,
  monthly **0.991**, ann. vols 0.215 vs 0.213). Period 2014-01 → 2026-06.
- **Costs (futures-correct, no swap):** per-side 0.57–2.11 bp (from each micro's tick/notional +
  commission); explicit roll cost 0.33–1.54 bp/roll; carry is in the back-adjusted series (L5).
- **System:** pre-registered primary = EMA100 filter, 20d Donchian breakout, ATR14 Wilder, 3×ATR
  ratcheting trailing stop, ≤3 pyramids @0.5×ATR, 1% fixed-fractional risk, two-sided, cash account.
- **Execution (verified):** signal close-J → fill open-J+1; intrabar stops; gaps fill at the open
  worse than the stop (L1/L26). Accounting identity holds to the cent incl. roll cost (V1).

---

## 2. Funnel, phase by phase

### Phase 1 — IC feasibility → MARGINAL (proceed under locked rule)
Pooled TSMOM IC (excess, HAC lag-6): the only signals with content are **medium-term momentum**
(trail 60/120/250d, **t_HAC ≈ 2.0**, overlay Sharpe ~0.55) — below the strict 2.5 gate, i.e.
MARGINAL. The **20-day breakout entry is indistinguishable from a block-shuffle placebo** (actual
forward payoff at the 47th percentile of placebo). The trend signal is weak; the breakout *timing*
adds nothing beyond momentum tilt. Locked rule → PROCEED (DSR/WF decisive), flagged.

### Phase 2 — full backtest
Pre-registered primary (cash, fractional): **Sharpe 0.50, CAGR 5.9%, MaxDD −25.9%, daily skew
−0.76 (wrong sign for trend), longest drawdown 5.1 years.** On the **integer-micro $100k book the
Sharpe falls to 0.31** (lumpiness ≈ halves it; ~1 MNQ ≈ 40% gross — the book is too small for 7
micros at this risk). Costs ($4.4k/12.5y) are not the killer. **Directional split: long +132.7k,
short −27.4k** — shorts lose on NQ/ES/GC/6A/6E, profit only on CL/6B (→ K2).

### Phase 3 — robustness
- **Parameter grid plateau 0.34–0.66** — a plateau (no overfit spike), but the *entire plateau is
  sub-0.70*; in-sample best EMA200/bk40 = 0.66 (slow trend), still < RESEARCH_PASS.
- **Ablations:** long_only **0.68** (best robust config); no-EMA 0.42; no-pyramid 0.23; stop-4× 0.14.
- **Regime concentration (the deep problem):** IS 2014–2019 Sharpe **0.21** vs OOS 2020–2026
  **0.68 (two-sided) / 1.02 (long-only)**. Block walk-forward: two-sided [0.12, 0.21, 0.16, 0.71,
  0.89, 0.58]; long_only has a **−1.35** block in 2014–15. The edge lives in 2020–2026.
- **Bootstrap (L=20):** base Sharpe 95% CI **[0.05, 0.99]** — lower bound barely clears zero.
- **Cost stress ×1/×2/×3:** 0.50→0.47 (base), 0.68→0.65 (long_only) — **swap/cost-immune** ✓.

### Phase 4 — rescue hypotheses
- **H1 conditional shorts.** **H1b (short energy/CL only, long elsewhere)** looks best — **Sharpe
  0.87, MaxDD −18.6%, skew −0.11, corr-to-ES +0.09 (decorrelated)** — and it is the *pre-registered*
  "short only assets without positive carry" rule. **But its short leg fails K2 per-subperiod: CL
  short = +$39,982 in 2014–2019 (the oil collapse) and −$3,398 in 2020–2026.** H1b's appeal is a
  2014–16 oil-bear artifact resting on a single energy instrument. K2 → killed.
- **H2 portfolio vol-target + cluster budgets.** Not validated: a clean two-sided overlay *hurt*
  (0.52→0.32); the long-biased "lift" sits on a returns reconstruction that already mis-states the
  base (0.56 vs true 0.68), so it is an artifact. A credible H2 needs an in-engine implementation;
  pure scalar vol-targeting is Sharpe-neutral. No reliable improvement.
- **H3 breadth.** **FAILS** — adding RTY/SI/ZN *lowers* Sharpe (two-sided 0.50→0.28, long-only
  0.68→0.54); the param ensemble {20,40,55}×{2,3} recovers only to 0.43/0.57. The extra instruments
  dilute rather than diversify on this sample (correlated/choppy, ZN's 2022 rate shock).
- **Crypto short-only ablation.** A bear-convexity hedge (2018 +44%, 2022 +27%; bleeds in bull
  years; standalone Sharpe 0.53). Negatively correlated to A — a *hedge for A in crypto bears*, not
  an additive sleeve. Out of the core by construction (avoids double-counting A's longs).

### The four kill criteria
- **K1 (DSR).** N = 29 distinct backtests; E[max SR | N] benchmark = **0.827**. Deflated value
  (SR − E[max]): two-sided **−0.33** (PSR 0.13), long_only **−0.15** (PSR 0.31) → **KILL**. Only H1b
  (0.87) clears it (+0.04, PSR 0.56) — and H1b fails K2; at any higher N it fails too.
- **K2 (two-sided, L25).** The short leg has no consistent edge: it loses on 5/7 assets in the
  symmetric system and, when conditioned to energy (H1b), is a single-period (2014–16) artifact.
  Symmetric system **killed**; only long-biased survives.
- **K3 (marginal-to-A+B).** See §3 — **NO SLOT** for all candidates.
- **K4 (walk-forward).** No ≥2-of-≥5 sign-flips and OOS-as-a-whole > 0.5 → the binary gate *passes*,
  but the IS/OOS 0.21→1.02 split means this is regime luck, not a stable edge. K4 is the *only*
  criterion not tripped, and only on a technicality.

---

## 3. Marginal contribution to the A+B book (the real deliverable)

Book params (CLAUDE.md / `_audit/portfolio_recalc_2026-06-10.md`): SR_A 1.33, SR_B 2.0 (proxy, L14),
ρ_AB 0.039 → **canonical equal-risk book Sharpe 2.310** (reproduced exactly). A reconstructed from
crypto (Sharpe 1.24 ≈ documented), B from the delta-neutral ledger (sparse, n=94).

| sleeve | SR | corr→A (monthly) | ERC book (from 2.310) | tangency Δ | D-gate 2.54 |
|---|---|---|---|---|---|
| two-sided | 0.50 | 0.10 | **1.95 (−0.36)** | +0.010 | FAIL |
| long_only | 0.68 | 0.21 | **2.03 (−0.28)** | +0.000 | FAIL |
| H1b | 0.87 | 0.20 | **2.10 (−0.21)** | +0.003 | FAIL |

**Under the project's own equal-risk methodology, every candidate sleeve LOWERS the book Sharpe**
(it is too low-Sharpe to deserve equal risk against a 2.31 incumbent). At *optimal* tangency
weighting the marginal is **negligible (+0.00 to +0.01)**. The decorrelation is genuine
(corr→A 0.10–0.21 < 0.4 ✓) — **the bar that fails is Sharpe, not correlation.** Robust to a more
conservative B proxy (SR_B 1.5 → book 1.96 → +sleeve 1.69, still dilutive).

**The central dilemma.** The two-sided version is the *good diversifier* (corr-to-ES −0.06,
+0.34%/mo in equity-down months) but is only Sharpe 0.50 and K2-killed. Going long-only to fix K2
lifts Sharpe to 0.68 **but destroys the diversification** (corr-to-ES +0.46, −1.04%/mo in
equity-down months, skew −1.05) — it becomes long-equity-beta. **You can have decorrelation OR
(modest) Sharpe, not both — and neither earns a slot against a 2.31 book.**

---

## 4. Conditions that would change the verdict (revisit triggers)
1. **Incumbent book degrades.** The "NO SLOT" is against a *claimed* 2.31 book resting on B's
   testnet proxy SR 2.0 (L14, mainnet unproven). If B underdelivers (say book ~1.0–1.3), a
   decorrelated 0.5 sleeve could add — re-run §3 with the realized B mainnet Sharpe.
2. **True breadth.** A real CTA-style 25–50-instrument universe (the prior's Axis 3) might lift the
   trend Sharpe via √N diversification. This was *not* achievable with 3 added futures (H3 failed);
   it needs a genuinely decorrelated multi-sector futures panel (rates, ags, softs, non-US indices).
3. **A persistent strong-trend regime** continues. The edge is real *in* 2020–2026; if that regime
   persists the standalone Sharpe stays ~0.7–1.0. Not investable on that hope.

None of these is a "tweak"; they are different studies. Per the locked rule, **sunk cost is not a
justification** — this is a clean kill, logged as a deliverable.

## 5. Deployable config
**None.** NO-GO. No configuration passes RESEARCH_PASS ∧ Book-slot ∧ (¬K1 ∧ ¬K2 ∧ ¬K3).

## 6. Candidate lessons (named, not numbered — engrave at reconciliation per CLAUDE.md)
- **`futures-removes-swap-but-edge-was-thin`**: the futures re-test confirms swap was the FTMO
  killer (cost-immune: 0.50→0.47 @3×), but the swap-free edge is sub-threshold (SR 0.50) — the
  weekly/daily non-crypto trend corner is closed on its *own thinness*, not on costs. Complements L36.
- **`trend-decorrelation-vs-sharpe-tradeoff`**: the L25/K2 fix for a long-drift universe (drop the
  value-destroying shorts) *destroys* the crisis-alpha that justifies a trend sleeve (corr-to-equity
  −0.06→+0.46). Decorrelation and Sharpe are in tension here; report both with every directional
  ablation. Extends L37/L38 (a long-biased trend sleeve = timing on beta).
- **`conditional-short-energy-is-a-2014-16-artifact`**: "short only no-carry assets" looks like a
  clean rescue (0.87, decorrelated) but with N=1 energy instrument it is the 2014–16 oil bear in
  disguise (+$40k vs −$3.4k post-2020) — K2 per-subperiod catches what the headline hides.
- **`incumbent-book-too-good-for-a-0.5-sleeve`**: a 0.5–0.7 Sharpe diversifier cannot raise a 2.31
  ERC book; under equal-risk it dilutes, at tangency it adds ~0. The book-slot bar is Sharpe, not
  correlation (corr→A 0.10 was fine). Same shape as the Double-7 "tail-smoother not Sharpe enhancer".
- **`seykota-094-was-55pct-crypto`**: the prior's headline 0.94/1.19 is a crypto result (BTC 44% +
  ETH 11%); the non-crypto futures remainder is SR ~0.50 — always decompose a multi-asset trend
  headline by asset before treating it as a non-crypto prior.

## 7. Reproduction
```
PY="/Users/.../Unholy returns/Python3.12.9/myenv/bin/python"   # pandas/pyarrow/statsmodels/yfinance
$PY strategies/trend_futures/data_build.py        # build continuous bars (network: yfinance)
$PY strategies/trend_futures/verify.py            # V1-V7
$PY strategies/trend_futures/funnel_p1_ic.py      # Phase 1 IC gate
$PY strategies/trend_futures/funnel_p2_backtest.py# Phase 2 + trial ledger seed
$PY strategies/trend_futures/funnel_p3_robust.py  # Phase 3 grid/ablation/WF/bootstrap
$PY strategies/trend_futures/funnel_p4.py         # Phase 4 H1/H2/H3 + crypto-short
$PY strategies/trend_futures/funnel_dsr.py        # K1 DSR over full trial count
$PY strategies/trend_futures/funnel_p8_marginal.py# K3 marginal-to-A+B (network: yfinance)
```
Artifacts: `results/*.json|*.parquet`, `daily/*.parquet` (regenerable, gitignored), `trials_log.csv`.
Separate program — `PREREG.md`/this report do **not** touch the FTMO `REGISTER.md`.
