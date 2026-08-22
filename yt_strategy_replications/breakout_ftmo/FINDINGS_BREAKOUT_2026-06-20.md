# FINDINGS — Short-term breakout, FTMO-targeted (§4 rank-3, free data)
**Date:** 2026-06-20 · **Pre-registration:** `PREREGISTRATION.md` (frozen before any price result).
**Type:** STRICT preliminary, reimplemented engine → independently audited (author≠auditor). FREE DATA ONLY.
No git HEAD ops (shared dir, 2026-06-19 incident); live book read-only; nothing deployed.

## 0. Verdict — (b)-refined: a REAL two-sided positive-skew edge, but SUB-THRESHOLD on retail cost
The intraday Donchian breakout is the first price-only family with the **§4-right shape**: genuine **two-sided**,
**not-beta**, **positive-skew** (+1.3 to +2.7) continuation, with excursion bounded by a hard 1×ATR stop. The clearest
real cell is **EURUSD 1h** — net SR +0.59, HAC-t **+2.6**, short-leg +2.5 bps against a *negative* buy-&-hold drift
(−0.03) ⇒ cannot be beta. **But the book magnitude is below every deployable gate:** the two-sided book
(GER40+XAUUSD+EURUSD+GBPUSD) nets **SR +0.43** at the *lower-bound* quoted spread, **≈0 (−0.01) at a realistic 1–2 bps
stress**, HAC-t +1.8 (insignificant), **DSR(N=145) 0.23** (gate 0.5). It FAILS gates 1 (HAC>2.5), 3 (net SR>1 / DSR>0.5),
even at the optimistic cost. Since a verdict that survives the lower-bound cost is the robust one, the robust verdict is
**"fails the deployable gate."**

So: **(b)-refined.** The edge is real and has the structure §4 wants (positive tail, bounded m, two-sided), unlike the
MR (cost-dead, negative tail) and the event family (priced-in, un-boundable risk) — but its **magnitude is too small to
clear retail cost**. Same vehicle conclusion as the sub-scale MR; the new, positive takeaway is that the **positive-skew
trend-continuation SHAPE is validated** as the right structure to pursue (at lower cost, or with a stronger signal under
a fresh pre-reg). Per the pre-reg, a positive would have been a Claude Code candidate — **this is not that**; it is a
sub-threshold edge, definitive as a NEGATIVE for deployment on free retail data.

## 1. Integrity note — a bug the audit caught (and I corrected)
My first pass (`q2_breakout.py`/`q3_confirm.py`) used the engine's `max_hold` as a fixed **session-bar count**. On a
session-filtered series that silently lets a late-day position **cross the overnight boundary**, capturing overnight
drift → **inflated SR and re-introduced beta**. The independent auditor flagged it (my GER40 1h "+0.96" vs a clean
+0.29–0.41). The canonical result is the **force-flat-at-true-EOD** rerun (`q4_honest.py`); the q2/q3 numbers are
**superseded**. Methodology lesson below. This is exactly why author≠auditor is run on every positive.

## 2. Q1 — does continuation have a gross edge anywhere? (measure-first)
Conditional post-Donchian(20)-break forward return (H=8), two-sided, vs spread. Continuation is **absent/negative at
M5** (EURUSD t −3.5, GBPUSD t −3.1 = false breaks revert; consistent with the MR study), and at M30 the apparent
"continuation" on US indices is **one-legged = beta** (up-break works, down-break reverts). Only **XAUUSD M30** (cont
+2.6 bps, t +2.1, both legs +) and GER40 M30 (t +1.2, both legs +) showed two-sided continuation with amplitude > spread
→ warranted the M30/H1 build. (H1 on the 6.5 h index session can't hold 8 bars → empty; noted.)

## 3. Q2/Q3/Q4 — the breakout net (HONEST, force-flat EOD = `q4_honest.py`)
Donchian breakout, enter next-bar-open, **sl = 1×ATR, tp = 3×ATR, force-flat at true session end**. Two-sided book
(US500/US30 dropped by the pre-registered L25 gate — they are one-legged beta, see controls).

| config | book net SR (measured) | stress SR | HAC-t | WF | DSR(N=145) |
|---|--:|--:|--:|--:|--:|
| 1h D20 | **+0.43** | −0.01 | +1.8 | 80% | 0.226 |
| 30min D20 | +0.37 | −0.31 | +1.7 | 80% | 0.150 |
| 30min D10 | +0.37 | −0.42 | +1.6 | 80% | 0.155 |

Per-instrument (1h D20): **EURUSD +0.59 (t +2.6)**, GER40 +0.41 (t 1.5), XAUUSD +0.12, GBPUSD −0.05. Controls (beta):
**US100 −0.37, US500 −0.45** with short-leg −5 to −8 bps → pure long-drift, correctly excluded by L25.
**Skew positive everywhere (+1.3 to +2.7)** ✓. Trade mix: stop ~40%, **target only 2–12%**, EOD ~35–70% — the 3:1 ATR
target rarely fills inside a session, so the realized (still positive) skew comes from the EOD exit, not the 3R target.

## 4. Two-sided & not-beta — the one thing that IS confirmed
- **Two-sided (L25):** both legs positive on the book (EURUSD legL+0.7/legS+2.5; XAU legL+3.4/legS−0.0; GER40 legL+3.5/
  legS+0.6) — strongest on the short leg for EURUSD.
- **Not beta (drift control):** EURUSD/GBPUSD have **negative** buy-&-hold SR (−0.03 / −0.15) yet net positive → the
  edge is not drift. US-index "breakout" profit was beta (vanishes net + EOD-flat + short leg).
- Independent audit (from raw M1): GER40 1h net SR 0.29 (t 1.07), EURUSD 0.56 (t 2.55), both legs +, no look-ahead
  (timing checks exact; same-bar cheat moved SR <0.01), not bounce; **magnitude < RESEARCH_PASS 0.7, "~1+" not reproducible.**

## 5. Q3 — §4 scorecard (is breakout closer than MR?)
| §4 axis | required | breakout | vs MR |
|---|---|---|---|
| TAIL / skew | positive | **✓ +1.3..+2.7** | **better** (MR negative) |
| intraday-m | ≤1.5 | ✓ (1×ATR stop; no event-gap) | better (events gapped) |
| presence/intermittent | ≤0.4 | ✓ (few breaks/day) | similar |
| two-sided ⇒ tail-decorr | yes | ✓ (both legs, not-beta) | similar |
| **per-trade EDGE / Sharpe** | **net SR>1, DSR>0.5** | **✗ SR ~0.4 (≈0 at stress), DSR 0.23** | the blocker |

**The breakout is the closest STRUCTURAL §4 fit found** (positive tail + bounded excursion) — but the **edge magnitude
is the blocker**, exactly as §4 predicted for a "medium fit." A positive tail does not rescue a sub-gate Sharpe.

## 6. Redirect (per the pre-registered map)
Verdict (b)-refined ⇒ the edge is real (two-sided, not-beta, positive-skew) but cost leaves no margin at retail. Same
direction as sub-scale MR: **price-only momentum/continuation is real but retail-cost-marginal**. Levers (order-flow is
blocked per the data inventory — no depth/signed volume for indices/FX in the store):
1. **Lower-cost vehicle** (DMA/futures) — EURUSD 1h (t 2.6) and the positive-skew structure would have real margin at
   ≤~0.1 bps; the §4-shape is deployable there, not at retail CFD.
2. **A stronger / conditioned breakout** (regime, volatility-state, multi-instrument confirmation) — but ONLY under a
   fresh pre-registration (the anti-mining budget here is spent: 6 configs, all reported).
3. **Portfolio use:** even a sub-1 Sharpe positive-skew sleeve can *improve a book* (the §4 container logic) if it is
   tail-decorrelated from the existing overnight-drift book — worth a dedicated combine-study, not a standalone deploy.

Price-only OHLC is now mapped end-to-end: reversion (MR) and continuation (breakout), all scales — both real at fine
scale, both retail-cost-marginal; only the institutional vehicle or a non-price data axis changes the verdict.

**Lesson candidates (NAMED, to engrave at reconciliation):**
- `intraday-breakout-is-two-sided-positive-skew-but-sub-threshold-net-on-retail-CFD` — Donchian (1×/3× ATR, EOD-flat)
  has the §4-right shape (skew +1.3..+2.7, bounded m, two-sided not-beta: EURUSD short-leg +2.5 bps vs negative drift,
  t 2.6) but book net SR ~0.4 at lower-bound spread, ≈0 at realistic cost, DSR 0.15–0.23, HAC-t insignificant → fails
  gates. Continuation real but retail-cost-marginal, mirroring the MR sub-scale verdict. (Family: L25/L34.)
- `intraday-flat-must-force-EOD-not-a-fixed-bar-count` — a fixed `max_hold` on a session-filtered series silently
  crosses the overnight gap → inflated SR + beta leak (caught here: +0.96→+0.41). Always force-flat at the true session
  end for any intraday-flat claim. (Engineering/methodology.)

## 7. Reproduce, ledger & handoff (no git ops)
```
cd yt_strategy_replications/breakout_ftmo
/usr/bin/python3 q1_breakout.py     # continuation vs cost (Q1)
/usr/bin/python3 build_cache.py "US100,US500,US30,GER40"  ; ... "XAUUSD,EURUSD,GBPUSD"  # resample cache
/usr/bin/python3 q4_honest.py       # CANONICAL: force-flat-EOD book (supersedes q2/q3)
```
`n_tests` added ≈ **6** (pre-registered grid), deployable verdict FAIL — increment the program ledger.
Isolation: additive folder, zero git HEAD ops; commit recipe identical to `intraday_mr_ftmo/FINDINGS.md §7`;
run `tools/check_register_integrity.py` in the MAIN dir before any commit.
