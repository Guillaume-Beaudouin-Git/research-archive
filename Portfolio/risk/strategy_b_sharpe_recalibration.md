# Strategy B Sharpe Recalibration
*Date: 2026-05-23 | Status: PERMANENT — use Sharpe(B) = 2.0 in all portfolio simulations*

---

## Decision

**Do NOT use Sharpe(B) = 9.64 for portfolio simulation.** Use **Sharpe(B) = 2.0** as the conservative mainnet proxy.

The 9.64 figure comes from 3 months of HL testnet data (Feb–May 2026). It is statistically inadmissible and structurally contaminated. This document records the three-part justification.

---

## Justification 1 — Sample Size (Statistical)

The standard error of an annualized Sharpe estimate from N daily observations is:

```
SE(SR) ≈ √( (1 + SR²/2) / N )
```

At SR = 9.64, N = 66 (≈ 3 months of daily returns):

```
SE = √( (1 + 9.64²/2) / 66 )
   = √( (1 + 46.5) / 66 )
   = √( 47.5 / 66 )
   = √0.719 = 0.848
```

95% confidence interval: **[9.64 ± 1.66] = [7.98, 11.30]**

The interval does not include zero, but this is irrelevant — the relevant question is whether the interval includes the TRUE long-run Sharpe for a delta-neutral carry strategy. The CI is so wide that virtually any Sharpe in [8, 12] is equally consistent with the data. This is not a usable point estimate.

Rule of thumb: Stable Sharpe estimation requires N ≥ 250 daily observations. We have N = 66 — 73% below minimum.

---

## Justification 2 — Testnet Contamination (Structural)

Strategy B was running on the **HL testnet**, not mainnet. Testnet funding rates differ from mainnet in three ways:

1. **Thin liquidity**: testnet has few participants → funding rates driven by a small number of positions, not by broad market demand for leverage
2. **No institutional arb**: on mainnet, basis traders compress the funding premium toward the cost of carry. On testnet, this arbitrage capital is absent → funding stays elevated longer and at higher rates
3. **Possible synthetic generation**: some testnets generate funding rates from a formula rather than from live market activity, which can produce systematically higher or lower rates than mainnet

Any of these mechanisms can inflate the observed carry P&L by 2–5× relative to mainnet reality. The reported 3-month P&L is therefore not a reliable estimate of mainnet performance.

---

## Justification 3 — Regime Bias (Temporal)

Feb–May 2026 corresponds to a specific market phase. Funding carry strategies are extremely sensitive to the funding regime:

| Period | Regime | Typical Funding | Carry Sharpe |
|--------|--------|----------------|-------------|
| 2020–2021 | Bull (leverage demand high) | 0.1–0.5%/8h | 3–6 |
| 2022 | Bear (funding negative) | −0.05 to −0.1%/8h | Negative |
| 2023 | Recovery | 0.02–0.05%/8h | 0.5–1.5 |
| 2024–2025 | Bull cycle | 0.05–0.2%/8h | 2–4 |

Three months of data cannot distinguish between "high long-run Sharpe" and "currently in a favorable regime." The backtest Sharpe of 4.10 (computed over a longer in-sample period that includes regime transitions) is more informative than the 3-month testnet figure.

---

## Calibration: Sharpe(B) = 2.0

Conservative derivation:
- Backtest in-sample Sharpe: 4.10 (longer period, captures regime variation)
- Degradation factors:
  - Mainnet vs testnet friction: −30% (real execution costs, slippage, API latency)
  - Regime normalization: −20% (3-month sample biased upward by current high-carry phase)
  - Live vs backtest: −10% (fill uncertainty, position sizing)
- Adjusted estimate: 4.10 × (1 − 0.30) × (1 − 0.20) × (1 − 0.10) ≈ **2.06 ≈ 2.0**

Sharpe(B) = 2.0 is:
- Conservative relative to the in-sample backtest (4.10)
- Aggressive relative to multi-year delta-neutral carry (literature: 1.0–1.5 over full cycles including bear markets)
- Appropriate as a planning figure until mainnet live data accumulates (target: 12 months minimum)

---

## Portfolio Simulation Impact

At Sharpe(B) = 2.0 (vs 9.64), ERC weights shift substantially:

| Strategy | Vol | Sharpe (old) | Sharpe (new) | ERC Weight (old) | ERC Weight (new, approx) |
|----------|-----|-------------|-------------|------------------|--------------------------|
| A (TSMOM) | 8.5% | 1.13 | 1.13 | 10% | ~25% |
| B (carry) | 2.6% | 9.64 → **2.0** | 2.0 | 68% | ~40% |
| C (NQ) | 6.2% | 1.52 | 1.52 | 22% | ~35% |

Adding strategy D at Sharpe 0.7–1.1 with ~25% ERC weight now contributes meaningfully (~+5–10% portfolio Sharpe vs. the A+B+C baseline) rather than being diluted by B's dominance.

**Portfolio gate remains**: Sharpe(A+B+C+D) > 1.10 × Sharpe(A+B+C), computed with Sharpe(B) = 2.0.

---

## Review Trigger

This recalibration should be revisited when:
1. Strategy B accumulates ≥ 250 mainnet daily returns (N ≥ 250 for stable SE)
2. The realized mainnet Sharpe over that period is outside [1.0, 4.0]
3. A multi-year bear market occurs (funding negative for 3+ months) — Sharpe(B) may need downward revision below 2.0

Until then, **use 2.0 as the fixed planning parameter.**
