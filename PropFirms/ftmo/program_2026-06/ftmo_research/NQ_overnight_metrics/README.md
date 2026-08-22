# NQ overnight-drift harvester — full metrics dossier

*Clean contiguous real-path on `NQ_1min_databento_2010-2026` (RTH cash, roll days skipped). 4,041 trading days, 2010-06-07 → 2026-05-29. Net of **2 bps/night** (spread+commission; overnight **swap not yet included** — see caveat). No look-ahead: the MA200 gate decision uses closes ≤ t; the overnight return is open(t+1)/close(t)−1.*

---

## ⚠ Read this first — the weekly question

**This strategy does not pass in weeks. p(pass) within 1–10 weeks ≈ 0% at every deployable sizing.** That is structural, not a data quirk:

> Gross drift ≈ **+5.6 bps/night** × ~5 nights/week ≈ **+28 bps/week** at 1× exposure. To reach the +10% Phase-1 target in one week you'd need ~**35× leverage**, which breaches the 5% daily-loss limit on the first adverse night. The overnight equity premium is a **slow beta harvest** — its entire viability comes from *"no time limit"*, not from speed.

So the meaningful clock is **months/years**, not weeks. The full curve is below.

---

## 1. Headline — FTMO 2-step funded probability by sizing

Sizing = constant fraction of equity held in NQ overnight (the "leverage" L on the overnight position). Chained: P1 +10% → P2 +5%, 5% daily loss, $9,000 static floor, no time limit. Rolling start every trading day (4,035 starts).

| Sizing | p(funded) *total*¹ | p(funded) *terminal*² | p(P1) | p(P2 \| P1) | bust | still running | median time-to-funded |
|---|---:|---:|---:|---:|---:|---:|---:|
| **0.50×** | **88.3%** | **100%** | 91.1% | 96.9% | **0.0%** | 11.7% | **3.51 yr** |
| **0.75×** | **81.5%** | 89.9% | 92.2% | 88.4% | 9.2% | 9.3% | **2.36 yr** |
| **1.00×** | **66.0%** | 69.1% | 79.4% | 83.1% | 29.5% | 4.5% | **1.56 yr** |

¹ *total* = funded / all starts (a start that ran out of 16-yr data still unfinished counts as a fail — conservative lower bound).
² *terminal* = funded / (funded + bust), i.e. conditional on reaching a verdict. At 0.5× **nothing ever busts** → 100%.

**The trade-off is pure first-passage:** smaller size → higher p(funded) and lower bust, paid for with a longer grind. 0.5× is the safe-but-slow corner (0% bust, ~3.5 yr); 1.0× is fast-but-fragile (29% bust, ~1.5 yr).

Time-to-funded spread (trading-day percentiles → years):

| Sizing | p25 | median | p75 |
|---|---:|---:|---:|
| 0.50× | 2.13 yr | 3.51 yr | 5.55 yr |
| 0.75× | 1.33 yr | 2.36 yr | 3.44 yr |
| 1.00× | 0.89 yr | 1.56 yr | 2.36 yr |

---

## 2. p(pass) vs horizon — the real curve

**By week (1–10):** essentially **0.0%** for 0.5× and 0.75×; 1.0× reaches just 0.1% (wk 9) / 0.3% (wk 10). The challenge is effectively never won inside 10 weeks.

**By month (cumulative incidence of funded):**

| horizon | 0.50× | 0.75× | 1.00× |
|---|---:|---:|---:|
| 6 mo | 0.0% | 3.6% | 6.6% |
| 12 mo | 3.6% | 11.3% | 22.5% |
| 24 mo | 23.6% | 34.0% | 45.2% |
| 36 mo | 39.3% | 58.5% | 55.8% |
| 48 mo | 57.6% | 75.1% | 69.1% |
| 60 mo | 67.1% | 86.6% | 69.1% |

(1.0× plateaus at 69% because the remaining ~30% have already busted — they never fund at any horizon. 0.5× keeps climbing past 60 mo toward its 88% asymptote.) See `fig1_p_pass_curve.png`.

---

## 3. Signal quality — nightly statistics

Per traded night (gate on), the realized overnight return:

| | n | mean | std | Sharpe (ann.) | skew | hit-rate |
|---|---:|---:|---:|---:|---:|---:|
| **net** (−2 bps) | 3,196 | **+3.59 bps** | 65.7 bps | **0.87** | **−0.76** | 55.8% |
| gross | 3,196 | +5.59 bps | 65.7 bps | **1.35** | −0.76 | 57.6% |

The gross Sharpe **1.35** is the independently-verified figure for the overnight equity premium. **Skew is mildly negative (−0.76)** — the known signature of overnight risk (small steady gains, occasional gap-down). This matters for the FTMO barrier: it's *not* a tail-lumpy positive-skew lottery (good), but the left tail is the bust vector (the COVID gap).

---

## 4. Equity-curve metrics (compounded, all valid nights incl. flat gate-off days)

| Sizing | CAGR | max drawdown | Calmar | Sharpe (ann.) | skew (active days) |
|---|---:|---:|---:|---:|---:|
| 0.50× | 3.71% | −9.14% | 0.41 | 0.79 | −0.76 |
| 0.75× | 5.53% | −13.50% | 0.41 | 0.79 | −0.76 |
| 1.00× | 7.32% | −17.70% | 0.41 | 0.79 | −0.76 |

Calmar (0.41) and Sharpe (0.79) are **leverage-invariant** under linear sizing — only the *level* of CAGR and maxDD scale. Equity-curve Sharpe (0.79) sits below the traded-night Sharpe (0.87) because flat gate-off days dilute it. **Worst single traded night: 2020-03-09, −6.51%** (the COVID gap from highs — the bust vector).

---

## 5. Regime behaviour — why the gate works and where it bleeds

Net strategy return by year (1.0× nightly) with gate-on fraction (`fig2_by_year.png`, `regime_by_year.csv`):

| Regime | Example years | What the harvester does |
|---|---|---|
| **Trending-up (its home)** | 2013 (+8.8%), 2017 (+10.5%), 2019 (+9.9%), 2020 (+26%), 2021 (+11%), 2024 (+24.5%), 2025 (+17.4%) | Gate on ~85–100%, harvests the drift. |
| **Sustained bear** | **2022: gate only 6.7% on (17 nights), −5.6%** while NQ **−33%** | **Gate sits flat → capital preserved.** This is the whole thesis — no time limit lets you wait it out. |
| **Chop / whipsaw around the MA** | **2016: −9.0%** (gate 67% on); 2026-partial −4.9% | **The worst regime** — gate flips on/off and the drift is negative. Bleeds (doesn't bust). |
| **Fast crash from highs** | **COVID 2020-03**: gate still 91% on (MA lags) → −6.51% night | **The bust tail.** Fatal at 1.0× only; survived at 0.5×/0.75×. |

Positive in **13 of 16 full years**. The gate's value is asymmetric: it brilliantly sits out *slow* bears (2022), but *lags* fast crashes from highs (2020) — which is precisely the un-hedgeable tail.

---

## 6. Honest caveats (what's not yet in these numbers)

1. **Overnight financing / swap is NOT yet subtracted.** FTMO charges a standard overnight swap on index CFDs (~2 bps/night at current ~5% rates; ~0 in the 2010-21 ZIRP era). A challenge *started today* and held for years would pay today's rate the whole time, cutting recent-era net from ~3.6 → ~1.6 bps/night — materially lengthening the grind and lowering these p(pass) figures. **Swap-free Islamic / 2-Step Swing accounts would neutralise this.** Quantifying it is the open Check 1 in `../OVERNIGHT_drift_hardening` (in progress).
2. **The crash-from-highs tail is un-hedgeable.** 2010-2026 contained COVID (survived at ≤0.75×) but **no 2008/1987-magnitude overnight gap**. A worse-than-COVID gap from above the MA busts even small sizes. Apply a planning haircut.
3. **It is beta, not alpha** — the equity risk premium, harvested with a trend gate + small size + no time limit. High-probability *because* severe bears are rare and the gate+patience handle ordinary ones, but it is not market-neutral and it bleeds in chop years (2016: −9%).
4. **Time is the real price.** Median 1.5–3.5 yr and 5–12% of starts never finish within 16 years. Confirm FTMO's inactivity / account-fee / expiration rules for a multi-year hold (open Check 3).

---

## Files in this folder

| File | Contents |
|---|---|
| `README.md` | this dossier |
| `NQ_overnight_metrics.xlsx` | all tables (Overview, Nightly, EquityCurve, FTMO_by_sizing, p_pass_by_week, p_pass_by_month, regime_by_year) |
| `metrics_summary.json` | full machine-readable results |
| `regime_by_year.csv` | per-year nights, gate-on %, net %, worst night, NQ buy-&-hold |
| `p_pass_by_week_*.csv`, `p_pass_by_month_*.csv` | cumulative-incidence tables per sizing |
| `fig1_p_pass_curve.png` | p(pass) vs horizon (months), 3 sizings |
| `fig2_by_year.png` | yearly net return + gate-on fraction |
| `fig3_outcomes.png` | funded / running / bust split per sizing |
| `nq_metrics.py` | the full reproducible script |
