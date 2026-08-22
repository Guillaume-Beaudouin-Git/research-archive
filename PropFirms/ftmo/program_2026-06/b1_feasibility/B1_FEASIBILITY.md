# B1 IC Feasibility Gate — FINRA short-volume → NQ overnight

**Date:** 2026-06-08 · **Question (one):** does FINRA daily short-volume, lagged J+1 and mapped to the NQ overnight (cash close→open) return, produce a real IC at N≥50 events/yr, net of cost? · **This is an IC gate, not a backtest** (no p(pass), no strategy, no parameter search). Code: `fetch_finra.py`, `ic_test.py`; data: `finra_shortvol_universe.parquet`, `ic_results.json`.

## ⛔ VERDICT: **FAIL** (closed at Gate 4 — IC significance). The signal does not clear the project standard (|HAC t|>2.5 & N≥50/yr) on a causal, survivorship-honest basis.

The cost axis is **not** the problem — the brief's thesis is confirmed (NQ overnight dodges the swap killer). The problem is the **raw IC isn't there**: the zero-survivorship signal is null, and the only near-miss is survivorship-inflated and still below the bar. **A full backtest is not justified — B1 is closed cheaply.**

---

## Gate 1 — DATA EXISTENCE: ✅ obtained (with a depth caveat)
- FINRA was **not** on disk. It **is** freely fetchable (FINRA CDN `cdn.finra.org/equity/regsho/daily/CNMSshvol{YYYYMMDD}.txt`, pipe-delimited). Fetched **1,899 trading days, 2018-08-01 → 2026-02-20** (~7.5 yrs; QQQ covered all 1,899 days; ~250 days/yr). 105,172 rows for a 57-symbol universe.
- **[FLAG] Depth limit:** the CDN served files only from **2018-08** on this path — *not* the "2009+" the triage assumed. Pre-2018-08 returned 404 (would need a different FINRA archive). 7.5 yrs is ample for the gate (N/yr ~250, 9 calendar years of sign-stability), but the deep history is **not** freely on this endpoint — reported, not invented.
- NQ overnight target reused verbatim: `data/overnight_research/nq_rth_daily.parquet` `ov_bps` (close→open), σ = **77.5 bps**, 2010–2026.

## Gate 2 — SURVIVORSHIP (the hidden data cost): handled two ways
- **QQQ-direct short ratio = ZERO survivorship** (QQQ is always the NDX-100 ETF; one symbol, no constituent mapping). This is the *clean* primary signal.
- **NDX-aggregate short ratio** (Σ short / Σ total over ~50 mega-caps) uses **TODAY's constituents → SURVIVORSHIP-OPTIMISTIC**. Its IC is an **upper bound**; the point-in-time IC would be weaker. I could not source historical point-in-time NDX membership for free, so the aggregate result is explicitly treated as an optimistic ceiling.

## Gate 3 — SIGNAL CONSTRUCTION (causal): short-vol ratio, level + change, lag ≥ 2
FINRA session-e short ratio is a **full-day total finalised after close_e** (published evening/next-morning), so the earliest close at which it is known is **close_{e+1}** → it can only predict the overnight into **e+2**. Hence `predictor[d] = signal[d-2 sessions]` (**lag 2 = minimum causal**; lag 1 would be look-ahead and is **excluded**). Reported lag 2 (primary) and lag 3 (robustness). Two-sided (sign read from the IC).

## Gate 4 — IC TEST (Spearman + Pearson, HAC Newey-West t): **FAIL**
16 causal variants (4 signals × {level,chg} × {lag2,lag3}). Strongest by |HAC t|:

| signal | lag | N | N/yr | Spearman IC | Pearson IC | **HAC t** | yrs +/− |
|---|--:|--:|--:|--:|--:|--:|--:|
| NDXagg_sr.chg (survivorship⚠) | 3 | 1848 | 244 | −0.047 | −0.058 | **−2.37** | 2/7 |
| NDXagg_sr.level (survivorship⚠) | 3 | 1899 | 251 | −0.058 | −0.056 | **−2.27** | **0/9** |
| NDXagg_sr.level (survivorship⚠) | 2 | 1899 | 251 | −0.061 | −0.057 | −2.18 | 1/8 |
| QQQ_sr.chg (**clean**) | 2 | 1848 | 244 | +0.024 | +0.031 | +1.39 | 7/2 |
| QQQ_sr.level (**clean**) | 3 | 1899 | 251 | −0.058 | −0.024 | −1.02 | 4/5 |
| TQQQ/SQQQ_sr.* (clean) | 2/3 | ~1880 | ~248 | ±0.01-0.03 | ±0.01-0.02 | \|t\|<1.0 | mixed |

- **The zero-survivorship signals (QQQ, TQQQ, SQQQ) are NULL** — every clean variant has |HAC t| ≤ 1.4. The directly-tradable, no-mapping signal carries **no overnight IC**.
- **The only near-miss is the survivorship-OPTIMISTIC NDX aggregate:** a *persistent, sign-stable negative* relationship (higher NDX short ratio → weaker next overnight = the **informed-short / continuation** direction, all 9 years negative for the level), but **|HAC t| ≈ 2.2–2.4 < 2.5**. And because it is an **upper bound** (today's constituents), the true point-in-time t is **lower** → clearly sub-gate.
- **Multiple testing:** 16 IC variants were examined; the project's t>2.5 is a *single-test* bar — a 16-test honest threshold is ≈|t|>2.9 (Bonferroni 5%). The best (2.37) fails even the un-adjusted 2.5, and fails the adjusted bar by more.
- **N/yr ≈ 244–251 ≫ 50** ✅ — the event-count gate passes; it is the **significance** gate that fails.

## Gate 5 — COST SANITY (one breakeven, not a strategy): cost is NOT the limiter
Gross edge per overnight from a sign-following position ≈ |IC| × σ_ov × E|z| (σ_ov=77.5 bps, E|z|≈0.8):

| | breakeven \|IC\| | best-IC gross/night | clean-QQQ gross/night |
|---|--:|--:|--:|
| **NQ** ($20/pt, ~$5–15 RT = 0.12–0.36 bps) | **0.004** | 3.6 bps (IC .058) | ~1.2 bps (IC .02) |
| **MNQ** ($2/pt, $4–6 RT = 0.95–1.43 bps) | **0.019** | 3.6 bps | ~1.2 bps |

The overnight move (σ 77.5 bps) **dwarfs** NQ-futures overnight cost — breakeven |IC| is just **0.004 (NQ) / 0.019 (MNQ)**. **The brief's central thesis is confirmed: the swap-free NQ-overnight axis would happily monetise even a small *real* IC.** The failure is **not** cost; it is that the IC is null (clean) or sub-threshold + survivorship-inflated (aggregate).

---

## Decision
**FAIL at Gate 4. Do NOT advance B1 to a full pre-registered backtest** — it would burn effort and an N-inflating trial on a signal that doesn't clear the IC gate. Two honest nuances, both reported not hidden:
1. **The cost/axis thesis was right** — NQ overnight is genuinely the swap-free, low-cost lane; if a real overnight IC existed it would be tradable. So the structural idea behind B1 is sound; the *specific FINRA short-volume signal* is what's absent.
2. **The one near-miss** (NDX-aggregate short-ratio → negative overnight IC, stable across 9 years) is **survivorship-optimistic and still |t|<2.5**. The *only* thing that could change the verdict is **point-in-time NDX constituents** (not free here) — and even granting them, the upper-bound t (2.37) is below the gate, so the expected point-in-time result is a clearer fail. Not worth the data-acquisition cost on this evidence.

**Bottom line:** B1's three-wall thesis (new data + overnight axis + swap-free futures) holds on the *axis* but not the *signal*. A clean, cheap FAIL — exactly the point of the gate.

*Causal (lag ≥ 2, lag-1 excluded as look-ahead); HAC t-stats; survivorship flagged and treated as an upper bound; FINRA depth limit reported; READ-ONLY on repo data, wrote only under `research/b1_feasibility/`; nothing fabricated — the data that wasn't freely available (pre-2018 FINRA, point-in-time constituents) is reported as a limit, not guessed.*
