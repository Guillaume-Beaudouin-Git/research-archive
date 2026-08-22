# ASIA_23_8 — Code Audit & Risk / Stress-Test Report
### Quant-dev verification + risk-mode stress testing

**Mandate:** verify the gold strategy code is correct (no look-ahead / bias), and if clean, stress-test it to destruction (overfit, Monte Carlo, regimes).

**Verdict:** ✅ **the code is clean (no look-ahead), and the edge is a genuine intraday-timing ALPHA — not gold beta, not a coding artefact, not outlier-driven.** It survives Monte-Carlo, regime splits and multiple-testing penalties. But it has **three real fragilities** that gate deployment: (1) **entry must be at 23:00 UTC to the hour** (1h late ⇒ Sharpe 1.10→0.37), (2) **drawdowns are long** (max −19% but up to ~4.8 years underwater, Calmar 0.39), (3) **execution-cost sensitive** (Sharpe 1.10 @1.5bp → 0.91 @2bp → 0.65 if the swap leaks).

---

## 1. Code & logic audit — no look-ahead, no bias

| Check | Method | Result |
|---|---|---|
| Vol-target causality | `rolling.std().shift(1)` + `expanding().median()` use only past data | ✅ causal |
| Edge ≠ VT artefact | strip vol-targeting, constant long | Sharpe **0.978** (edge exists without VT) |
| Independent reimplementation | rebuild window return from raw H1 closes | return corr **0.996** with the engine |
| Return construction | additive log returns over a hold-to-close window; no intrabar path used → no SL/TP peeking | ✅ |
| Null — short instead of long | flip the position | Sharpe **−2.37** (correctly loses) |
| Null — permutation | shuffle returns | ~1.0 — *correct* for a long-only drift strategy (the edge is the window's positive mean, which is order-invariant; this characterises it as drift-capture, not a bug) |

The execution discipline (position sized from data through day *t*−1, return realised over day *t*'s window) is enforced and verified. **No look-ahead.**

## 2. Is it real, or overfit? — it is real

- **Gap handling.** Trading only **complete windows** (the correct live behaviour — you know intraday whether all 8 hours printed) gives Sharpe **1.10 @1.5 bp** (n=5,018); the gap-filled "trade every day" version is *lower* (0.84), so the headline is not inflated by gap-filling.
- **Not gold beta — the key result.** Regressing the strategy on a buy-&-hold of gold: **β = 0.012, R² = 0.001, α = +2.95 bp/day (HAC t = +4.84), ≈ +7.4 %/yr.** The 8-hour Asian window is essentially **orthogonal to gold's daily move** — this is genuine intraday-timing alpha, *not* the secular-bull beta I had earlier flagged. (Correction to the first report.)
- **Regime persistence.** Net Sharpe positive in **17 of 20 years**, including the **2013–2015 gold bear** — the edge is not the bull market. Worst year −2.2 (2018).
- **Outlier robustness.** Dropping the 20 best days (of ~5,000): Sharpe still **0.82**. Not driven by a handful of prints.
- **Multiple testing.** Deflated Sharpe ≈ 0.9 (90 trials). The window is a *modest* plateau: 23:00 start, length 7–8 both ≈ 1.10; it degrades off-corner (length 6/10 ≈ 0.7–0.8; the 00:00 start fails). Economically anchored (enter right after the rollover).

## 3. The three fragilities (risk mode)

**(a) Entry-time precision is the binding execution risk.**

| Window | Sharpe |
|---|--:|
| base 23:00→07:00 | 1.10 |
| **enter 1h late (00:00→07:00)** | **0.37** |
| exit 1h early (23:00→06:00) | 1.11 |
| exit 1h late (23:00→08:00) | 0.83 |

The alpha is concentrated in the **first hour after the rollover (23:00–00:00 UTC)** — the +2.4 bp/h spike from the EDA. You must be filled at 23:00 sharp; the exit (06:00–07:00) is forgiving. A live implementation needs a reliable 23:00 UTC entry, not a "sometime overnight" fill.

**(b) Drawdowns are shallow but long.** Max DD −19%, but the **longest underwater stretch is ~1,200 trading days (~4.8 years)** — the 2017–2020 grind (see figure). Calmar 0.39. A real allocator must be able to sit through a multi-year flat period.

**(c) Cost / swap sensitivity.**

| Scenario | Sharpe | ann. ret | max DD |
|---|--:|--:|--:|
| 1.0 bp spread | 1.29 | +8.8% | −16% |
| **1.5 bp spread (base)** | **1.10** | +7.5% | −19% |
| 2.0 bp spread | 0.91 | +6.2% | −23% |
| 2.0 bp + weekly swap leak | 0.65 | +4.5% | −27% |

Viability requires confirmed **swap-free rollover (≤22:00 UTC)** *and* **≤1.5 bp** effective spread (limit-order entry in the liquid Asian session). At a 2 bp market order it is sub-1.

## 4. Monte-Carlo

![Stress test](../gold_research/results/fig_stress_test.png)

2,000 stationary-block-bootstrap paths (preserve autocorrelation): **Sharpe median 1.10, 5th pct 0.71, 95th 1.50; P(SR>1) = 66%, P(SR>0.5) = 99%.** Max-DD median −13%, worst-5th −20%. Annual return median +7.5% [5th +4.9%]. The downside tail is benign (even adverse resamples keep Sharpe > 0.7).

---

## Verdict & deployment conditions

**This is a legitimate, clean, low-correlation intraday gold alpha** (α t = 4.8, R² to gold ≈ 0, 17/20 years, MC P(SR>1)=66%) — a rare survivor. It is **not** a curve-fit or a look-ahead artefact. Deploy **only** if all three hold, else expect Sharpe < 1:

1. **23:00 UTC entry to the hour** (the edge lives in the first post-rollover hour);
2. **broker rollover ≤ 22:00 UTC** (swap-free) — verify, including the Wednesday triple-swap;
3. **effective spread ≤ 1.5 bp** (limit orders), and tolerance for **multi-year flat periods**.

**Recommended next steps:** (1) paper-trade the 23:00 UTC fill to measure the real entry slippage — it is the make-or-break variable; (2) build the de-beta'd variant only if you want to suppress the (already tiny) residual gold exposure; (3) size it small in the book — its ~0 correlation to gold and to the crypto/FX sleeves makes it a good diversifier even at Sharpe ~1.

*Reproduce:* `python gold_research/audit_code.py && python gold_research/risk_audit.py && python gold_research/stress_mc.py`
*Artefacts:* `gold_research/results/fig_stress_test.png`.
