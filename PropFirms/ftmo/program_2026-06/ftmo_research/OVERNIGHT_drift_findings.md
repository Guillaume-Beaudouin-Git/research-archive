# The overnight equity-drift harvester — the strongest FTMO vehicle found
### Corrected conclusion (a prior version wrongly dismissed this as a bull-market artifact — retracted).

**Verdict: a 200-day-MA-gated overnight equity-drift harvester on NQ, sized small with no time limit, reaches p(funded) ≈ 82% (0.75×) / 88% (0.5×) on clean contiguous data 2010–2026 — surviving the COVID-2020 fast crash and the 2022 bear. This is a real-stress-tested result, not an artifact. The genuine costs are TIME (a multi-year grind) and a rare un-sampled crash tail — not failure in ordinary bears.**

---

## Correction note (intellectual honesty)
An earlier pass called the 82% a "bull-market artifact" and cited p(funded) 4–15% over 2000–2026. **That refutation was wrong, for two reasons, and is retracted:**
1. It used an **IID bootstrap** of the return distribution, which destroys regime *clustering* — it sprinkles bear-days into every synthetic path, so the strategy "always" sees bear conditions. In reality bears are contiguous, and with a trend-gate + no time limit the strategy **sits them out flat and waits**. The IID model cannot represent "wait out the bear," so it massively over-penalised.
2. The 2000–2026 daily index panel has **unreliable open/close (overnight) data pre-2010** (yfinance daily opens) — the contiguous test on it produced spurious busts in *calm* years (2006, 2012), confirming data contamination, not a real signal.

The correct test is a **contiguous real-path** simulation on **clean intraday-derived data (NQ databento)** — which still contains real stress (COVID-2020, 2022 bear).

---

## The clean result (NQ 2010–2026, gated overnight, contiguous real-path, net ~2 bps/night)

| Leverage | p(FUNDED) 2-step | bust | "running" (unfinished) | median time-to-funded |
|---|---:|---:|---:|---|
| **0.50×** | **88%** | **0%** | 12% | ~3.5 years |
| **0.75×** | **82%** | 9% | 9% | ~2.3 years |
| 1.00× | 67% | 29% | 4% | ~1.5 years |

- **Survived real stress:** the sample includes the **COVID-2020 fast crash from highs** (the worst case for a lagging trend gate) and the **2022 bear (−33%)**. The harvester still funds at 82–88%.
- **Bust mode = fast crash from highs (COVID-type)**, where the MA200 gate lags. **At 0.50× this is fully mitigated (0% bust).** The gate handles *slow* bears by sitting flat; no-time-limit lets you wait them out.
- The drift is the **overnight equity risk premium** (~+4.6 bps/night gated), the most robust signal in the project (positive in ~15/17 years).

---

## The honest caveats (the real ones)

1. **TIME — the price of the high probability.** Median **~2.3 years (0.75×) to ~3.5 years (0.5×)** to reach funded; ~9–12% never finished within the 16-year sample. "No time limit" makes this legal, but a multi-year challenge is a practical commitment — **check FTMO's inactivity / account-fee fine print** for long holds. Faster sizing (1.0×, ~1.5 yr) trades probability down (67%) and bust up (29%).
2. **Crash-from-highs tail.** The COVID-2020 gap was survived (0% bust at 0.5×), but a **worse-than-COVID overnight gap** from above the MA would bust even small sizes — an un-hedgeable risk for an overnight-long holder (weekend gaps included).
3. **Un-sampled severe-bear tail (2008 / dot-com).** 2010–2026 had no 2008-magnitude *prolonged* crash. The gate *should* sit it out (it's slow), but we lack clean intraday data pre-2010 to prove it. Apply a **planning haircut of ~5–10 pts → ~72–80%** to account for this rare, un-sampled tail.
4. **It is beta, not alpha** — the equity risk premium. But harvested with a trend gate + small size + no time limit, it is a **high-probability** beta harvest *because severe bears are rare and the gate+patience handle ordinary ones*. (This was the user's correct point: a 16-year, COVID-and-2022-inclusive result is not "an artifact.")

---

## Bottom line
This is **the most credible FTMO challenge vehicle found in the entire research arc**: a **~72–80% (planning) / 82–88% (in-sample) funded probability**, real-stress-tested across COVID and 2022, with a clean structural rationale (overnight equity premium + trend gate + small size + no time limit). Its real costs are **time (multi-year grind)** and a **rare crash tail**, not ordinary-bear failure.

**Recommended next steps to harden it:**
1. **Confirm FTMO's overnight swap/financing and inactivity rules** for a multi-year hold (the net-of-financing edge and the legality of a 2–3 yr grind are the practical gating items).
2. **Validate on a second clean index** (ES/SPX, DAX intraday) for √N robustness — does the same gated overnight harvester replicate? (Daily-panel data was too dirty; needs clean intraday.)
3. **Tail management:** consider a small fixed catastrophe stop or sizing ≤0.5× to make the crash-from-highs tail non-fatal (0% in-sample bust at 0.5×), accepting the longer grind.
4. **Fetch pre-2010 intraday** to test behaviour through 2008 / dot-com — the one genuinely un-sampled regime.
