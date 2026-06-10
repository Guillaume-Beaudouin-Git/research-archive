# SYNTHESIS — Institutional deep-dive on intraday FX (M1, 2007–2026)

**Date:** 2026-06-09 · **Run:** autonomous /goal, one hypothesis fully deep-dived at a time.
**Data:** `data/deep_history_utc/` — 10 FX majors M1, **TRUE UTC verified empirically** (spread-min 14:00 UTC,
vol-max 14–16 UTC, Fri/Sun seam 21:00 UTC, 0 Saturday bars), real calibrated spread, +50 % stress leg.
**Infra reused verbatim:** `CFDCostModel`, `ftmo_first_passage.combined_pass_prob_empirical`, `dsr.py`,
funnel noise-floor machinery (via `funnel_lib`). New intraday cache + loader under `cache/`, `fx_intraday_lib.py`.
**Cumulative trial count: 108 → 240** (full audit in `N_ledger.md`).

---

## 1. Bottom line

Three economically-distinct, mechanism-led intraday-FX hypotheses were each pre-registered (frozen before
any result), IC-gated, and falsification-tested. **All three are clean negatives, and they fail for one
shared structural reason:**

> **The retail FTMO-MT5 CFD round-trip cost (~2–5 bps) is an order of magnitude larger than the gross
> intraday-FX microstructure signal that actually exists (sub-bps), and where a larger gross signal exists
> it is either fully priced within the spread-spike window (news) or has decayed to zero post-2015
> (seasonal). Retail FX intraday-flat is a cost-dead space.**

This is not a new failure mode — it is the same wall that killed the burned generic intraday MR (B1,
cost-ratio 2.49 < 3.0), the WMR fix (B5) and the fix-reversal (B6, net −1.78 bps, L34). This run **extends
that conclusion from specific windows to the whole retail FX intraday-flat space**, across the three
orthogonal signal classes (reversal, momentum/drift, seasonality) that remained untested.

---

## 2. Per-hypothesis verdicts

| H | Hypothesis | Mechanism real? | Gross signal | Net verdict | Why dead |
|---|---|---|---|---|---|
| **H1** | London-open reversal of the Asian-session displacement (European pairs) | **YES** — textbook (port HAC-t 2.11 European vs −0.57 Asia-native; delay-robust) | ~0.5 bps/trade (Sharpe 0.60, **at the N=127 noise floor 0.585**) | **DEAD** (net Sharpe −0.4…−2.6 all pairs/windows; best gross/cost ratio 0.287 ≪ 1.5) | **L34 cost-kill ~5–10×** + one-sided (L25): 85 % is shorting EUR/GBP after Asian rallies |
| **H2** | Post-USD-news intraday continuation (first-hour drift) | **NO** | ~0 (pooled cont HAC-t **0.19**) | **DEAD** (net Sharpe −2.7…−3.4) | No drift after the first 15 min (priced in the impulse); cost-dead inside it (spread spike) |
| **H3** | Day-of-week × session intraday-flat seasonal (100-cell scan) | **NO** (best cell at the 100-cell luck ceiling) | best net cell decays to 0 post-2015 | **DEAD** (WF sleeve net Sharpe **−4.27**; DSR 0; p(pass) 0.0002) | No cost-beating seasonal; EURUSD-Friday is a decayed pre-2015 regime artifact (F6) |

**p(pass) (FTMO 2-step, first-passage):** H1 net 0.031, H2 ~0, H3 0.0002. **FundedNext / any symmetric-barrier
geometry: moot** — all three net series have *negative* Sharpe, which every barrier geometry rejects.
Swap-free intraday-flat was the favorable case and it still loses — the failure is the **spread**, not swap.

---

## 3. What we genuinely learned (positive knowledge from negatives)

1. **The London-open session-handoff reversal is REAL** (H1): the overnight displacement of *European* FX
   majors partially reverts in the London morning — present in EUR/GBP/CHF/CAD, **absent / slight
   continuation in Asia-native JPY/AUD/NZD** (the mechanism-driven contrast fired exactly as pre-registered),
   delay-robust (not a fill artifact). It was **untested** in the repo. It is simply too small (~0.5 bps) for
   retail cost. *This is new, citable structural knowledge — not just a "no".*
2. **Intraday FX post-news drift does not exist** at tradeable (≥15-min) horizons (H2): the surprise is
   priced in the first impulse; the daily-horizon post-event momentum the repo found does **not** have an
   intraday M1 analog on FX.
3. **No intraday-flat FX seasonal survives** (H3): the one historical pattern (EUR/GBP weakness into the
   Friday London session = USD-into-weekend squaring) **decayed monotonically to zero by 2021–2026** —
   another instance of L23 (algoization erases retail microstructure edges).

---

## 4. Candidate lessons (proposed — for user ratification into CLAUDE.md)

> **L43 — Retail FX intraday-flat microstructure is cost-dead across reversal, drift, and seasonality.**
> The exploitable gross signal in retail M1 FX (post-spread, intraday-flat) is sub-bps, while FTMO-MT5 CFD
> RT cost is ~2–5 bps. Verified on 2007–2026, 10 majors, true-UTC, across three orthogonal angles: (a)
> session-handoff reversal — real (European-pair-specific, delay-robust) but ~0.5 bps, net Sharpe < 0 across
> all windows; (b) post-news continuation — absent (pooled t 0.19); (c) dow×session seasonal — no
> cost-beating cell, best is a decayed pre-2015 artifact. **Generalizes L34 from fix windows to the entire
> retail FX intraday-flat space.** Pre-flight rule stands: any retail FX intraday flow edge must clear
> `gross_per_trade / cost_p95 ≥ 1.5` or it is dead — none here reached 0.36.
>
> **L44 (corollary) — The mechanism-driven cross-sectional contrast is the cheap, decisive IC falsifier.**
> Splitting the universe by *where the mechanism should/shouldn't apply* (H1: European vs Asia-native) turned
> a "weak pooled t" into a clean verdict: the edge concentrated exactly where predicted (HAC-t 2.11 vs −0.57),
> proving the signal is real *and* isolating that its death is cost, not absence. Pre-register the contrast
> pool, not just the primary pool.

---

## 5. Burn list (append to CLAUDE.md FX intraday section)

New burns from this run (all 2007–2026, true-UTC, real cost +50 % stress, DSR-deflated at cumulative N):
- **London-open Asian-drift reversal** (H1) — real mechanism, net-dead, one-sided. `REPORT_H1.md`.
- **Intraday post-USD-news continuation/fade** (H2) — no edge ≥15 min, cost-dead below. `REPORT_H2.md`.
- **Intraday-flat dow×session FX seasonal** (H3) — no cost-beating cell; Friday USD-into-weekend decayed
  to 0 post-2015. `REPORT_H3.md`.

Pre-existing burns re-confirmed/cited: generic intraday MR (B1), generic momentum (B2), London ORB v1 (B3),
F2 Asian breakout (B4), WMR fix (B5), fix-reversal (B6), G10 carry / round-number (B7).

**Net: the retail-accessible intraday-FX signal space (reversal / momentum / breakout / fix / news /
seasonality / carry) is now comprehensively burned.** Do not re-propose any of these on retail M1+spread data.

---

## 6. Untested — only because the data/execution don't exist on disk (the honest frontier)

These are NOT claimed dead; they are **out of reach with retail M1 OHLCV+spread** and would require resources
the program doesn't have:
- **Order-flow / trade-direction** (signed volume, OFI) — the actual driver of the H1 reversal; would
  separate informed from noise flow. Needs L2/tick-with-aggressor data.
- **Quote depth / full LOB** — to model the true execution cost at the release second (H2) and intraday
  liquidity holes. The 15-min median spread under-resolves the spike.
- **Sub-minute spread** — to know whether a <15-min post-news edge exists *and* whether it could ever be
  executed inside the spread spike (prior: cost-dead).
- **Institutional cost tier (≤1 bp RT)** — the H1 reversal (gross/cost ≈ 0.6/1.0–1.5) *plausibly* clears at
  institutional spreads; this is the L34/L43 boundary, structurally inaccessible to a retail prop-firm book.

---

## 7. Recommendation

**Stop retail FX intraday microstructure research — the space is exhausted and cost-dead** (this run + the
prior burns). The program's edge does not live in retail FX intraday; it lives (if anywhere) in the
documented sub-threshold books (Ross-Hook, TSMOM) under a non-symmetric / personal-book container, or in the
order-flow/institutional frontier that is off-limits on disk. Redirect intraday effort away from FX-on-MT5.

*All numbers reproducible from `results/*.json` via the scripts in this directory under
`<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/python3`. READ-ONLY on source data
and prior deliverables throughout; nothing fabricated; missing/unresolvable reported as such.*
