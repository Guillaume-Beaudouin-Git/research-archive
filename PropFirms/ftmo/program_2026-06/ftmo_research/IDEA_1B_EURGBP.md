# Idea 1B — EUR/GBP mean-reversion (single-leg) — PRE-REGISTRATION
*Frozen 2026-06-03 BEFORE results. Inherits the full frozen spec of `IDEA_1A_AUDNZD.md` (same engine, same signal, same pre-registered grid, same acceptance criteria); only the instrument changes. Purpose: option (a) — test whether the "FX cross-level reversion" branch is dead, not just AUD/NZD.*

## Hypothesis
EUR and GBP are deeply linked (UK↔EU are each other's largest trade/financial partners; ECB↔BoE co-movement). The cross **EURGBP** is historically range-prone → fast deviations from an adaptive fair value revert. Single compliant symbol (the cross IS the spread) → no two-leg hedging-rule issue.

## Known risk (stated up front)
2016–2020 (Brexit) was a multi-year structural **trend** in EURGBP, not a range — the same trend-fade failure mode that killed 1A may recur. This test will show whether the branch generalizes to a kill.

## Data
Synthetic daily EURGBP = EURUSD_close / GBPUSD_close (yfinance daily, 2015-01 → 2026-05, same-source → USD cancels → clean), mirroring 1A. Cost grounding from EURGBP MT5 M1 spread (2021–2025).

## Spec, grid, acceptance criteria
**Identical to 1A** (W∈{40,60,90}, Z_in∈{1.5,2,2.5}, Z_stop∈{3,4}; baseline 60/2/3; causal t+1 fill; reversion gate Hurst<0.5/VR<1/half-life; raw-return significance + DSR on the 18 trials; OOS 2021–2026; charter Part D checklist).

---

# RESULTS & VERDICT (2026-06-03)

## FINAL VERDICT: ❌ KILL — deep validation on clean 27-year data shows no significant edge. The 3.5y "promise" was small-sample / single-regime overfit. (And a spectacular synthetic-data result was caught earlier as an ARTIFACT and retracted.)

> **Deep-validation update (clean ECB EURGBP 1999–2026, return-corr 0.99 vs real):**
> - Gate Hurst 0.46, half-life 22d (weakly reverting).
> - Baseline 60/2/3: **+15% over 27 YEARS (~0.5%/yr), t=0.58** — insignificant. Best of 18 grid configs **t=1.45** (need ~2.4 after 18 trials) → **not significant**. **14/27 years positive = coin-flip** (worst −11.7% in 2008).
> - Cost sweep: t falls 0.68→0.18 (1→6 pips).
> - **FTMO 2-step first-passage (daily-MTM, contiguous): p(funded) 20–34%, bust 62–78%** at L=5–20× → fails the barrier.
> - The earlier 3.5y M1 result (16/17 positive, t=5.8) was **overfit to the 2022–25 reversion regime**; it does not survive the 27-year sample.
> **Conclusion: EURGBP single-leg reversion has no robust, significant, deployable edge. KILL.**
>
> **Data-methodology win (log to protocol):** yfinance daily FX — ratio AND direct ticker — is **corrupted for daily-return analysis** (return-corr ≈ 0 vs real). The **ECB euro reference rates** (official daily fixing, 1999+) are clean (return-corr 0.99 when sampled at the same 15:00 UTC). Use ECB / real-broker M1 for FX, never yfinance daily.

---

## (earlier) interim verdict: 🟡 PROMISING-BUT-UNDERPOWERED on 3.5y — superseded by the KILL above.

### The artifact catch (charter validation working as designed)
First pass on **synthetic daily EURGBP = yfinance EURUSD/GBPUSD** looked spectacular: **18/18 grid configs positive in-sample AND OOS, best t=+3.90, positive skew**. The mandatory anti-artifact check killed the celebration:
- synthetic vs **real** EURGBP: **level corr 0.98 but daily-RETURN corr 0.018** → the yfinance daily USD-pair closes are not time-aligned; the ratio's day-to-day returns are largely **phantom**. The backtest was mean-reverting synthetic noise. **The 18/18 / t=3.9 synthetic result is RETRACTED.** (Same artifact class as the historical "+9.4R EURGBP" desync.)

### On REAL direct-cross data (EURGBP M1, 2021-12 → 2025-06, n≈900 days)
- **Mean-reversion gate is the strongest of any cross tested:** Hurst **0.352**, VR(10) 0.732, half-life **12 days** → genuinely reverting (not a random walk like AUDNZD's 0.47).
- Pre-registered grid: **16/17 configs positive** (broad, not cherry-picked); best t=+5.83 (W60/2.5/4) — but that config has only **n=11 trades**.
- **Cost-robust** on the synthetic sweep (survived to 8 pips); to be re-confirmed on real data.

### Honest caveats (why it's not promoted yet)
- **Underpowered:** only **3.5 years** of real direct-cross data (2022–2025) = **one macro regime** (post-COVID hiking cycle). Best t-stats sit on **tiny trade counts (n=8–11)**. The broad 16/17-positive is the real signal; the high-t single configs are fragile.
- Needs **longer real EURGBP history** (not yfinance ratios) to confirm across regimes, plus a proper first-passage FTMO sim on clean data with small-N CIs.

### Acceptance checklist status
✅ single-leg compliant · ✅ no-look-ahead · ✅ mean-reversion confirmed (Hurst 0.35, strongest tested) · ✅ artifact-screened (real-data) · 🟡 edge positive & broad on clean data BUT small-N/single-regime · ⏳ OOS-across-regimes unproven (data-limited) · ⏳ first-passage not yet run on clean data · ⏳ DSR fragile at n≈11. → **Promote to deeper validation, do NOT deploy.**

### Net for option (a): the "FX cross branch is dead" hypothesis is NOT confirmed.
On clean data the branch is alive-but-underpowered, **EURGBP the standout** (Hurst 0.35, 16/17 positive). The blocker is **data length** (real direct-cross history), not the idea.

