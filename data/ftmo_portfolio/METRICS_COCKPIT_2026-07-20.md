# FTMO METRICS COCKPIT — the quant's dashboard for the funded project (2026-07-20)

Everything needed to improve the book + maximize campaign EV, organized by the **3 levers: SIZING · TIMING ·
PORTFOLIO**. Static −10% floor, 2-step, vm14 challenge. Sources: cleanroom cohorts (`outputs/*challenge*.csv`),
`phase1c_sleeves.parquet`, and prior established studies (vm-sweep, funded-anatomy, real-book-metrics).

## 0. THE SCOREBOARD (current operation, canonical)
| Metric | Value | Source |
|---|---|---|
| p(pass) single challenge (1-try) | **23.4%** | full 2013+ cohorts |
| p(fund within k attempts) | 1:26% · 2:50% · **3:62%** · **4:71%** · 5:79% · ceiling **82%** | OOS retry cohorts |
| avg attempts to fund | **3.17** | OOS |
| time-to-fund | median **34d** · p75 54d · wall 91d | OOS |
| p(fund) vs day-budget | ≤30d 38% · ≤60d 66% · ≤90d 81% | OOS |
| **EV per campaign** (challenge→funded) | **+$680 to +$740** | real-book / vm-sweep |
| funded cash-flow | ~**$197/mo**, break-even median mo5, P(>0) 66% | funded-anatomy |
| combined book | SR 0.69, annRet 11.2%, maxDD −21.2% | this audit |

**The EV equation (how the levers combine):**
`EV_campaign = p(fund) · E[funded_value] − E[attempts] · fee`
- `p(fund)` ← sizing (vm) × timing (season + #retries) × portfolio (sleeves)
- `E[funded_value]` ← funded sizing (vm≈0.85) × sleeve edge × longevity
- `E[attempts]` ← 1-try rate (portfolio + timing) → drives fee burn

---
## LEVER 1 — SIZING (vm, per-sleeve budget, margin cap)
**Metrics to track:**
| Metric | Current / finding |
|---|---|
| p(pass) vs vm | vm14 = **71.4%**; **plateau vm[10-30]** (flat) |
| EV vs vm | peak ≈ vm14 **+$740**; EV plateau, cap-60% floors EV≥0 |
| bust prob vs vm (daily vs floor split) | daily-barrier dominant (funded-anatomy: 98% daily) |
| time-to-pass vs vm | aggression does NOT sprint (t_median ↑ with vm) |
| margin footprint vs vm | cap **60% equity** (p99 was 93% uncapped) |
| **funded-stage vm** | **vm≈0.85 optimal** (converts 55/58 busts, +EV $157 Pareto) |
| Kelly-optimal vm | near vm14 challenge / vm1.0-0.85 funded |
**Verdict:** vm is **near-optimal and on a plateau → LOW remaining upside.** Don't over-invest here. The one
real move is the challenge→funded **switch (vm14→~1.0)** which carries most operation EV (+$4→+$880).

---
## LEVER 2 — TIMING (season, #attempts, stopping rule)
**Metrics to track:**
| Metric | Finding |
|---|---|
| p(pass) by QUARTER (1-try) | **Q1 10.7% · Q2 34.6% · Q3 18.8% · Q4 28.3%** |
| p(pass) by month | Jan 4% · **Apr 41%** · **Oct 40%** · Aug/Sep 15% |
| p(fund) vs #attempts | 26/50/62/71/79% — **diminishing returns, ceiling 82% @ ~5 attempts** |
| p(fund) vs time-budget | ≤30d 38% · ≤60d 66% · ≤90d 81% (wall) |
| regime (vol) at launch | **FLAT** (23% ±1 across vol terciles); high-vol only SLOWER (117 vs 69d) |
| serial dependence | empirical retry (50/62%) > i.i.d. (41/55%) → favorable periods cluster |
**Verdict:** timing is the **FREE lever.** Actions: (1) **launch in April or October, never Jan-Feb** (~3×
quarter effect, ~10× Jan-vs-Apr single-try); (2) **cap retries at ~4-5** (past that, marginal p ≈ 3pt but fee
burn continues → EV turns negative — compute the exact abandon-k); (3) **don't wait for a vol regime** (no effect).

---
## LEVER 3 — PORTFOLIO (improve / replace / add sleeves)
**Per-sleeve metrics (2013-2026):**
| Sleeve | SR | maxDD | skew | var-contrib | **marginal p(pass)** (measured 2026-07-20) |
|---|---|---|---|---|---|
| gold (XAU TSMOM) | 0.39 | −22.5% | **+2.99** | **65%** | **+10.8pt** — ENGINE |
| J1 (USDJPY 12-1) | 0.49 | **−26.4%** | −0.22 | 25% | **+2.8pt** — WEAK, decayed (2022 SR1.69→2026 0.01); mods cost −0.4/−0.9pt |
| overnight (US100+GER40) | 0.51 | −9.0% | +1.36 | 10% | **+10.4pt** — ENGINE |
| ORB (US100) | 0.29 | — | +1.76 | ~0 | **+81.8pt** — ELIGIBILITY backbone (min-trading-days; −2.6pt P&L but book→2.8% without it) |

**Full book pooled p(pass) = 84.6%** (IS 89.3 / OOS 79.9), 3.37 att. J1-suspension-gate delta = **−0.43pt
pooled / −0.87pt OOS** (tail-protection vs the USDJPY-160 intervention breach, NOT a p(pass) enhancer).
Key reframe: ORB is the min-trading-days enabler (+81.8pt), not a drag — any replacement must preserve
day-coverage. gold+overnight are the p(pass) engines. **J1 = replacement candidate** (25% variance for +2.8pt).
- **Correlations all 0.05-0.10** (real decorrelation = the book's core asset).
- **New/replacement-sleeve GATE** (what a candidate must clear): (a) corr < 0.2 to existing sleeves; (b)
  **marginal p(pass) > 0** via ablation on the funnel (the true test, not standalone Sharpe); (c) positive or
  low-neg skew (protects the daily barrier); (d) low ex-kurt / bounded left tail; (e) adds trading-days OR
  low-DD exposure. The overnight profile (low-vol, +skew, +12pt) is the template; gold (high +skew) is the engine.
- **Ideal FTMO sleeve (L24):** high DAILY Sharpe + win>55% + win/loss≈1 + low kurtosis + materializes ≤40d.
**Verdict:** highest remaining upside. Priorities: (1) **decide J1** — decayed edge, deepest DD, 25% variance;
replace or down-weight toward gold; (2) **hunt one new decorrelated +skew sleeve** measured by MARGINAL p(pass),
not Sharpe; (3) the mover is trading-days + low-DD (overnight-like), not raw Sharpe.

---
## What a quant should MEASURE NEXT (missing / stale)
1. **Re-run the cohort funnel with the CURRENT book** (July J1 suspension gate + restamp) — the cohorts above
   are the June v2 book; refresh p(pass)/EV post-USDJPY-mods (study says +~0.65pt, verify).
2. **Per-sleeve seasonality** — decompose the Q1 hole (is it gold, J1, or overnight?) to time launches better.
3. **Exact abandon-k** — the retry count where marginal EV crosses 0 (fee vs +Δp), to cap campaigns.
4. **Marginal-p(pass) ablation table for every sleeve** at the current config (the true sleeve-value metric).
5. **DSR/deflation per sleeve** (esp. J1) — confirm the decayed edge isn't already noise.
6. **CIs via path-bootstrap** — all the above is one market history; block-bootstrap the cohort outcomes.

## One-line strategy
Sizing is maxed (plateau). **Timing is a free ~+10-25pt** (launch Apr/Oct, cap retries ~5). **Portfolio is the
real research frontier**: J1 has decayed — replace/down-weight it and add one decorrelated +skew sleeve judged
by MARGINAL p(pass). EV is maximized by p(fund) × funded-value − fee-burn; the switch to funded vm≈1.0 carries most of it.
