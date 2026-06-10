# REPORT — H2: Post-scheduled-news intraday drift (USD majors)

**Status:** CLOSED at the Phase-1 IC gate. **Verdict: DEAD — no exploitable intraday post-news continuation
+ cost-killed.** Cleaner null than H1 (which had a real-but-tiny gross signal); H2 has essentially **no
signal** at tradeable horizons. **Cumulative N after H2: 140** (127 + 1 IC + 12 grid; see `N_ledger.md`).

---

## 1. Hypothesis (frozen — PRE_REGISTRATION.md ADDENDUM)

After a high-impact USD release, the first-15-min impulse **continues** over the next ~45 min (underreaction
/ staggered repricing). Universe EURUSD/GBPUSD/USDJPY; USD HIGH events 2018–2026 (calendar verified
true-UTC: NFP 12:30/13:30, FOMC 18:00/19:00 UTC). Entry at r+30 (delay+1, **after** the seconds-long spread
spike → tight ~1-pt spread), exit r+60, intraday-flat. Two-sided. Gate: pooled HAC|t|>2.5, sign=continuation,
L34 gross/cost ≥ 1.5.

## 2. Phase-1 IC gate — `results/h2_phase1_ic.json`

| pair | N (per yr) | corr(impulse,cont) | HAC-t | Spearman | gross bps | cost bps | **net Sharpe** | gross-t |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | 1036 (128) | +0.017 | 1.07 | +0.008 | 0.22 | 2.38 | **−2.71** | 0.58 |
| GBPUSD | 1034 (128) | +0.062 | 1.18 | +0.038 | 0.18 | 2.81 | **−3.06** | 0.41 |
| USDJPY | 1034 (128) | +0.013 | 0.26 | −0.014 | −0.18 | 2.57 | **−3.37** | −0.45 |
| **pooled** | 1036 days | — | **0.19** | — | 0.07 | 2.59 | — | — |

- **F1 FAIL:** pooled continuation HAC-t = **0.19** ≪ 2.5. No predictive content (impulse does not predict
  the next-45-min move). Power is ample (N≈128/yr ≫ 50). This is consistent with efficiency: the news is
  priced in the first 15 min; nothing exploitable remains.
- **Direction split:** cont-up −0.12 bps (t −0.35), cont-dn +0.28 bps (t 0.80) — neither significant.
- **F5/L34 FAIL:** gross 0.07 bps / cost 2.59 bps = ratio **0.028** ≪ 1.5. Net Sharpe −2.7 to −3.4 all pairs.

## 3. Bulletproofing the null — `results/h2_phase1_surface.json`

Grid impulse{15,30} × hold{30,60,120} × {all-USD-HIGH, majors NFP/CPI/FOMC}, 12 cells (each +1 to N):

| event-set | best |cont_t| | gross/cost (best) | net Sharpe range |
|---|---|---|---|
| all USD HIGH | **2.33** (i30,h60) — still < 2.5, best of 12 | 0.104 | −2.6 … −6.4 |
| majors (NFP/CPI/FOMC) | 1.20 (mostly **insignificant / slight fade**) | ≤ 0 (gross **negative**) | −3.3 … −7.6 |

- **Best continuation t across all 12 cells = 2.33** (cherry-picked → deflated ≈ 0), gross/cost 0.104.
- **Majors-only** (the truly market-moving releases): continuation **absent or negative** (gross −0.4 to
  −1.8 bps). The faint all-USD-HIGH positive is driven by **minor releases** (illiquidity microstructure),
  not the big events — not a tradeable drift.
- Every cell: net Sharpe deeply negative, gross/cost ≪ 1.5.

## 4. Verdict

**H2 = DEAD (no edge + cost-killed).** The intraday post-news continuation does not exist at cost-viable
(≥15-min, post-spike) horizons on FX majors; for the major events it is absent or weakly reversing.

- **Boundary (untested-for-lack-of-finer-cache):** sub-15-min impulse (e.g. 5-min reaction → 15-min drift)
  is not resolvable with the 15-min cache. But entering there pays the **seconds-long release spread spike**
  (EURUSD can blow from 1 → tens of pts) → **cost-dead by construction**. So: the drift-bearing window (if
  any) is < 15 min and cost-dead; the cost-viable window (≥ 15 min) has no drift. Either way untradeable.
- Re-confirms the repo's daily finding (post-event momentum is a *daily* phenomenon at best; intraday FX
  has nothing) and the B3-AngleB spike-fade failure. Adds the **intraday continuation** angle to the burn list.

### What's burned now
- **H2 intraday post-USD-news continuation/fade on FX majors** — no edge at ≥15-min horizons, cost-dead below.
  Do not re-test on retail M1+calendar. *Untested-for-lack-of-data:* sub-minute order-flow / tick spread at
  release (would need L1 depth + sub-15-min spread, not on disk) — but cost-dead prior is strong.
