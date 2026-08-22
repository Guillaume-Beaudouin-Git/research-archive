# FTMO Candidate Funnel — Limitations & what is NOT testable on our data

Reported honestly, not papered over. Anything below that would change the headline is flagged **[material]**.

## 1. The binding constraint: 17-month OOS × N=66 is near-impossible to clear — and that's correct
- **[material]** OOS = 2025-01-01 → 2026-06-05 ≈ 370 business days. The standard error of a 370-day annualised Sharpe under the null is ≈ √(252/370) ≈ **0.83**. The observed cross-trial OOS-Sharpe dispersion is **0.73** — *below* the noise SE — i.e. the 66 outcomes are indistinguishable from noise. A wider search over a longer OOS would be needed to certify anything; on this hold-out, the honest power simply isn't there. This is a property of the data, not a bug, and it is why the certified shortlist is empty.
- A longer OOS (e.g. 2022-2026) would raise power but is **not permitted** here (the brief fixes OOS = 2025-26). Fuller validation should re-run with a multi-year, walk-forward OOS.

## 2. **[material]** DSR is sensitive to N and to the trial-Sharpe dispersion σ_SR — both were set conservatively/honestly
- The E[max] benchmark scales with both N and σ_SR. Three defensible deflations were reported (σ=1.0 → bar 2.38; σ_OOS=0.73 → bar 1.74; σ_full=0.35 → bar 0.83). **Two of three give 0 survivors.**
- **N-sensitivity, stated plainly:** at the honest **N=66** (every variant backtested, incl. per-pair legs and K/threshold sub-parameters — exactly what the brief mandates), the best candidate (TSMOM-K200) scores DSR **0.45 (fail)**. It would only cross 0.5 if N were *understated* to ≈40. The brief is explicit that understating N makes the bar fake — so the honest large N is what (correctly) kills the near-miss. N=66 is itself a **floor**: implicit parameter choices (z-cap=2.0, inv-vol lookback=60, RSI 10/90, vol-regime windows) add un-counted degrees of freedom, so the true bar is *at least* this high.
- σ_full giving 5 "survivors" mixes a long-sample dispersion with a short-sample candidate Sharpe — inconsistent, hence demoted to a sensitivity only.

## 3. Cost model — reused but with assumptions
- Reuses `cfd_costs.CFDCostModel` (real per-bar feed spread × **markup 3.0**) + FTMO commission/slippage added in bps. Markup 3.0 is the program-standard conservative retail factor (L23b); a lower markup would lift marginal candidates slightly but none is near the bar.
- **Daily** representative spread = the day's *median* M1 spread. Real fills cross the spread at the *execution instant*, which for some signals (gap, event) is a higher-spread moment → costs here may be **mildly optimistic** for intraday-timed entries. Conversely, holding-period **swap** is set to 0 (most candidates are daily-rebalanced, near-flat overnight in net terms); genuinely multi-day-hold trend candidates (TSMOM K=200) would pay some financing not modelled here → their net is **mildly optimistic**. Not enough to rescue a 0.45.
- FX-cross point sizes (AUDJPY/EURJPY=1e-3, others=1e-5) were added to the model's DECIMALS map in-memory (cost-model file untouched).

## 4. **[material]** Splice-seam & extreme-day nulling
- Index 2017/18 feed-level jumps over holidays produced impossible daily returns (US100 +141%, US500 +66%); these were **nulled** (set to 0) via per-class caps (idx/xau 0.15, fx 0.13, btc 0.40). Also nulled: USDCHF ×2 (2015 SNB), AUDJPY ×2 (2008 carry-unwind). Nulling the SNB/2008 days is *defensible* (retail couldn't trade through them — gaps, requotes, blown brokers) but it does remove genuine extreme events; an FX mean-reversion book that "wanted" those days is being given a pass it wouldn't get live. Counts logged in `summary.json::artifacts_nulled` (≤2 per instrument).

## 5. Daily-bar convention
- Bars are 22:00-UTC-anchored ("FX day", NY 17:00 close), Mon-Fri, tiny-stub days (<30 M1 bars) dropped. The DST wobble (21:00 vs 22:00 UTC) is unmodelled (immaterial for daily close-to-close). FTMO's actual daily-loss reset is on **broker server time (CE(S)T)**, not this anchor — so the p_funded daily-floor timing is approximate.
- **[material]** p_funded feeds the first-passage engine **close-to-close** daily returns; the FTMO −5% **daily** floor and −10% **static** floor are breached on *intraday* excursions that a daily series cannot see. p_funded is therefore **optimistic** (real intraday paths touch floors more often). It is reported as colour only — **it is not the gate.**

## 6. Event strategies (calendar 2018+)
- The economic calendar (`economic_calendar_2018_2026.csv`, TradingView, no-key, gray-area ToS) covers **2018-2026 only** → event candidates have ~7y IS + ~1.4y OOS and ~8-12 events/yr → OOS event counts of ≈10-12, giving **excess kurtosis 60-300** and statistically meaningless OOS Sharpes. Pre-FOMC drift (the registry's strongest event lead) **reversed** on the 2025-26 OOS (−1.14). Verdict: event edges are real-but-unprovable on this OOS length.

## 7. BTC specifics
- BTC daily = `data/panels/btc_full.csv` (yfinance BTC-USD, daily **close only**, 2014+). No intraday/OHLC → gap-fade not testable on BTC. Day boundary is yfinance UTC-midnight, **not** FTMO's BTC CFD session (which is weekend-closed and EET-stamped on the separate MT5 BTC panel — *that* panel was avoided here). BTC cost = fixed bps (2.3 spread × markup + 8.5 add incl. 0.065% RT). Weekend handling: BTC restricted to business days (Fri→Mon close) for FTMO-realism, but real FTMO BTC weekend gaps are not modelled.

## 8. What is NOT testable on our data (reported, not invented)
- **True intraday execution / microstructure**: ORB, VWAP-MR, session-scalping require sub-minute fill modelling and news-time spread spikes we don't simulate at daily resolution → pre-excluded (and registry-dead anyway).
- **FTMO server-time daily reset** and **real intraday floor excursions** — only approximable.
- **Instruments beyond the 16 cached**: the `ftmo_close` panel has AUS200/UK100/JP225/HK50/EU50/US2000 but with **no per-bar spread** → no validated cost → excluded. No XAGUSD (silver), no energy (CL/NG), no single-stock CFDs → commodity-pair and equity-event RV not testable.
- **Options / VRP / vol-surface** — not FTMO-executable; excluded by mandate.
- **Real FTMO crypto swap & weekend gap behaviour**, and **per-account consistency/scaling rules** beyond the static 2-step barriers.
- **Live slippage asymmetry** (L19: losing trades near stops fill worse) — modelled only as a flat bps add.

## 9. Honest scope of the conclusion
This is a **triage**, not a full validation. "0 certified survivors" means *no candidate earned the right to a paid FTMO challenge on this evidence* — it does **not** prove every mechanism is dead (a longer OOS, beta-neutralisation of the low-vol-drift shape, or proper intraday modelling could revive one or two). The one lead worth fuller work (TSMOM-K200 basket, near-miss) and the cleanest *shape* (F1 low-vol-drift, beta-tinged) are named in `SHORTLIST.md` precisely so the next, more rigorous pass knows where to point — at a multi-year walk-forward OOS with intraday-aware floors, not at this 17-month window.
