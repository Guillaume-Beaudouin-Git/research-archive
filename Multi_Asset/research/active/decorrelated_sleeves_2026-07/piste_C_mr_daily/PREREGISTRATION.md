# PRE-REGISTRATION — Piste C: Daily / multi-day mean-reversion on indices after excess

**Frozen:** 2026-07-08 13:52 UTC · **Status:** design frozen BEFORE any result. Additive, no git-HEAD ops, live book untouched.
**Reconciliation policy:** independent fresh pass; in-repo precedent (`MR_deepdive_ftmo.md`,
`yt_strategy_replications/intraday_mr_ftmo/FINDINGS.md`) consulted only in final synthesis.

---

## 0. Prior & the legitimacy test (declared honestly)
The **intraday 15-min** MR-on-indices family is already falsified in-repo as a **beta trap** (the short
leg loses to index drift). This piste is legitimate **only if it differs materially** — here by
**horizon** (daily / multi-day holds, not 15-min) and by **excess definition** (RSI / Bollinger / long-MA
deviation over days, not a 30-min band). The decisive test is **identical and non-negotiable**: does the
**SHORT leg** (fade overbought) make money, or is it merely a bet against the indices' up-drift? If, after
framing, the short leg fails the same way the 15-min version did, we say so plainly and stop — no rescue.

A structural note we will measure, not assume: at daily horizon **swap asymmetry helps the short leg**
(shorting US100 ≈ +0.09 bps/night, longing ≈ −2.13). So if the short leg still fails, the killer is the
**drift (beta)**, not financing — a clean isolation the intraday study could not make (it was swap-free).

## 1. Hypothesis
**H_C:** at daily/multi-day horizon, fading an "excess" (RSI/Bollinger/long-MA deviation) on equity
indices yields a **two-sided** net edge (short leg net-positive), surviving real FTMO cost incl. overnight swap.
**H0:** the short leg loses to drift (same beta trap as the 15-min version) → the "reversion" is the
period's directional drift; only the long/beta leg pays.

## 2. Universe & data (frozen)
- Primary: **US100, US500, US30, GER40** (indices — where the intraday version was falsified, so the
  horizon contrast is clean). Breadth: **XAUUSD, EURUSD, USDJPY**.
- Bars: **daily** UTC closes. Sample: indices 2013→2026, others 2007→2026.

## 3. "Excess" definitions (frozen — 3 orthogonal)
1. **RSI(2) Connors** extremes: oversold RSI2 < 10 (long), overbought RSI2 > 90 (short).
2. **RSI(14)** extremes: < 30 (long), > 70 (short).
3. **Bollinger %b(20,2)**: close below lower band %b<0 (long), above upper %b>1 (short); and a
   **long-MA deviation** z = z-score of (close/SMA50 − 1) over 100d, |z|>2.
Each is evaluated independently (orthogonal excess definitions), not combined into one meta-signal.

## 4. Signal & execution (frozen)
- **Entry:** long on oversold, short on overbought (per §3 definition), **only the extreme** (intermittent).
- **Exit:** reversion to neutral (RSI back through 50 / %b>0.5 / z→0) OR time-stop = 10 trading days OR
  **hard stop** = adverse move ≥ 2.0×ATR(14) from entry (excess deepens = thesis wrong, cut).
- **Timing:** signal on close T−1, execute at close T (1-bar delay). Non-overlapping per instrument.
- **Grid (search space for DSR):** 3 excess definitions × threshold{base, tight} × exit{reversion, time-stop}
  = 12 configs × 7 instruments = **84 trials** tracked for DSR.
- **Cost (NET):** round trip = `rt_cost_bps` (active fill) **+ overnight swap × nights held** (asymmetric,
  measured anchors; long index pays ~−1.5 to −2.1, short ~0). Stress swap ×1.5, slip ×1.5.
- **Vol targeting:** 10% annual (63d rolling σ) for comparability.

## 5. Two-sided requirement (THE decisive test)
Long-leg (fade oversold) and short-leg (fade overbought) P&L reported **separately** and compared to the
**unconditional drift** of each instrument. Qualify only if **short-leg net ≥ 0 with HAC t > −1 AND the
long-leg conditional edge exceeds the unconditional drift** (i.e. it beats buy-and-hold, not just rides it).

## 6. Success / fail thresholds (frozen)
| Gate | RESEARCH_PASS | PROPFIRM_PASS |
|---|---|---|
| Net Sharpe (two-sided book) | > 0.7 | > 1.0 |
| HAC t (lag-6) | > 2.5 | > 2.5 |
| Short-leg net | ≥ 0 (t>−1) | > 0 |
| Long-leg beats unconditional drift | required | required |
| Walk-forward folds positive | > 50% | > 60% |
| Max drawdown | < −25% | < −10% |
| DSR (N=84) | > 0.5 | > 0.95 |

## 7. Pre-declared falsification triggers (any ⇒ FALSIFIED, named mechanism)
- **F1:** short-leg net < 0 (t < −1) → "beta trap — same as the 15-min version, horizon didn't help".
- **F2:** long-leg conditional edge ≤ unconditional drift → "riding beta, not alpha (L25)".
- **F3:** two-sided book net Sharpe < 0.7 after cost → "no tradeable two-sided edge".
- **F4:** best DSR < 0.5 → "multiple-testing artefact".

## 8. Candidate criterion & re-test plan — as Piste A §8. If it collapses to the falsified 15-min beta trap, declare it and do not spend WF/bootstrap.
**Modifications budget:** 3.
