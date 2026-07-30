# RESULTS — Regime overlay on the deployed FTMO book

**Verdict: REJECTED.** The overlay raises p(pass), but a *constant* multiplier carrying the same
volatility raises it **more**, and on real historical paths the overlay sits **inside its own placebo
band**. It is a de-lever in disguise, and a worse one than the `vm` knob we already have.

Design frozen in `PREREGISTRATION.md` before any number below was computed. Sample 2013-10-01 →
2026-06-05, N = 3,295 engine days. Nothing outside this folder was written; nothing committed.

---

## 1. The L15 condition — answered first, because it is the cheap test

L15: *regime overlays are only useful on strategies with MaxDD > 20%.*

| object | ann vol | Sharpe | **MaxDD** | worst day | skew | ex-kurt |
|---|---:|---:|---:|---:|---:|---:|
| **Deployed MONO book, live sizing (vm 14 × on_w 0.6)** | 77.5% | 1.15 | **−81.0%** | −31.9% | +1.13 | 10.1 |
| Same sleeve at canonical unit vol-scaling (audited `phase1c_sleeves`) | 5.5% | 0.51 | −9.0% | −1.9% | +1.36 | 24 |

**The L15 condition is MET — and comfortably (−81%).** This is worth stating plainly because L15 is a
statement about a *strategy*, and MaxDD is not scale-invariant: the same overnight sleeve is a −9%
object at research vol-targeting and an −81% object at the leverage the challenge is actually run at.
So L15 did **not** foreclose this branch — the test below is the real decision, not a formality.

(The −81% is the *unconstrained* counterfactual: live, the account dies at the −10% floor long before.
That is the point — the book is far more levered than the barrier geometry tolerates, which is exactly
the condition under which *any* size reduction looks like it helps. Hence the two mandatory controls.)

## 2. What was reconstructed, and from what

The deployed book is **MONO**: `w_xau = 0`, J1 off by its own gate, ORB challenge-off. What trades is
the overnight sleeve — **US100 22:05→15:30 and GER40 17:35→09:00, Mondays and Tuesdays only**.
Reconstruction (`build_book.py`) imports the audited cleanroom engine
(`data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py`) read-only and reuses its accounting:
signed-$ notional, harmonic average entry, half-RT bps on |Δnotional|, nightly **measured asymmetric**
FTMO swaps, 0.01-lot quantization, 60% margin cap at live **Swing** margin rates, EA v2.4 breaker.
Equity is renormalised to 10k each close, which pins `taper = glide = pace = 1` and yields the return
stream at constant deployed leverage.

Sanity: active on 59.4% of days, on Mon/Tue/Wed only (positions span the night into the next session);
corr with the audited `overnight` sleeve **0.80**, implied leverage **10.6×** — consistent.

**Costs**: the `spread` column of `data/deep_history_utc/` is **not used anywhere** in this study (it is
empty on a large share of bars and understates the real FTMO round-trip by ~2.4×). Costs come from the
audited measured RT-bps panel and the measured asymmetric swap panels. `deep_history_utc/US100_M1.csv`
is used **only** as a price series for the MA200 (cross-check vs `panel_px`: corr 0.999979).

## 3. No look-ahead — verified, not asserted

US100 risk is posted at **22:05 CET = 16:05 ET**, i.e. *before* the 16:15 ET VIX print of the same
date; GER40 at 17:35 CET is 4.5h earlier still. Same-date VIX would therefore be look-ahead. Every
input is reindexed onto the engine calendar and then **lagged one full engine day**.
`regime_signals.assert_no_lookahead` verifies this mechanically at 60 cut dates by rebuilding the
exposures from truncated inputs and requiring every past exposure to be unchanged — **PASS**.

| variant | stress days | mean exposure |
|---|---:|---:|
| O1 VIX/VIX3M > 1.00 | 7.5% | 0.947 |
| O2 US100 < MA200 | 17.7% | 0.876 |
| O3 either | 21.1% | 0.852 |

## 4. The mechanism — the signal is real, and it points the wrong way

Book returns on stress vs non-stress days (baseline book, no overlay applied):

| variant | mean return, stress | mean, calm | vol, stress | vol, calm | P(day < −5%), stress | calm |
|---|---:|---:|---:|---:|---:|---:|
| O1 VIX term | **+218 bp** | +21 bp | 9.77% | 4.21% | 12.1% | 6.4% |
| O2 MA200 | **+72 bp** | +28 bp | 6.62% | 4.42% | 11.8% | 5.8% |
| O3 both | **+85 bp** | +22 bp | 7.38% | 3.95% | 12.5% | 5.3% |

The regime signal is a **genuine volatility forecaster** — 2.3× the daily vol and ~2× the frequency of
−5% days. That part of the public claim survives contact with our data. But this book is a **long
overnight index premium**, and that premium is *paid for bearing exactly this risk*: its mean daily
return is **3-10× higher** in the stress regime. Cutting exposure there removes the tail **and** the
earnings. Overlaid Sharpe falls **1.15 → 0.98 / 1.02 / 1.02**, while a uniform de-lever of the same
volatility **raises** it to 1.24-1.29.

## 5. Decision metric — Δp(pass) and Δduration

FTMO 2-phase barriers via `Portfolio/admission/barrier.py` (+10% / +5%, −5% daily, −10% static floor,
min 4 trading days, no time limit). Stationary block bootstrap, mean block 10 days, **20,000 paths, all
variants on the same draws** (paired). The path-vectorised runner in `campaign.py` reproduces
`barrier.simulate_campaign` **exactly** (bit-for-bit on 500 paths, p_pass 0.1660).

| variant | p(pass) | Δp | 95% CI (paired) | fail daily | fail floor | median days | p90 days |
|---|---:|---:|---:|---:|---:|---:|---:|
| **baseline** | 18.00% | — | — | 79.3% | 2.7% | 18 | 34 |
| O1 VIX term | 18.97% | +0.97pt | [+0.77, +1.16] | 78.2% | 2.8% | 18 | 34 |
| O2 MA200 | 21.37% | +3.37pt | [+3.01, +3.70] | 74.4% | 4.3% | 20 | 41 |
| O3 both | 21.75% | +3.76pt | [+3.39, +4.11] | 73.9% | 4.3% | 20 | 41 |
| *de-lever, vol-matched to O1* (c=0.839) | **21.07%** | +3.07pt | [+2.76, +3.38] | 75.5% | 3.4% | 20 | 39 |
| *de-lever, vol-matched to O2* (c=0.829) | **21.42%** | +3.41pt | [+3.09, +3.74] | 75.1% | 3.5% | 20 | 40 |
| *de-lever, vol-matched to O3* (c=0.729) | **22.29%** | +4.29pt | [+3.87, +4.71] | 73.9% | 3.9% | 22 | 45 |
| de-lever, mean-exposure-matched to O3 (c=0.852) | 20.61% | +2.61pt | [+2.32, +2.90] | 76.2% | 3.2% | 19 | 38 |

Read the pairs, not the rows: **every overlay is matched or beaten by a constant number.** O1 gains
+0.97pt where its de-lever gains +3.07pt; O3 gains +3.76pt where its de-lever gains +4.29pt. Not one
overlay clears its own volatility-matched control — pre-registered condition (c) fails for all three.

**Duration gets worse, not better**: median time-to-funded 18 → 20 days, p90 34 → 41. The p(pass) gain
is bought with a slower challenge, which is the standard de-levering trade, not a regime effect.

**Death decomposition** behaves as theory says it should — the daily-barrier channel drops (79.3% →
73.9%) while floor deaths *rise* (2.7% → 4.3%, surviving longer at smaller size lets more paths bleed
to the floor). So condition (d) is satisfied. It just does not matter: the constant multiplier moves
the same channel by the same amount.

### Placebo — same duty cycle, same clustering, shuffled alignment (60 circular rotations)

| variant | real p(pass) | placebo p50 | placebo p95 | placebo max | percentile of real |
|---|---:|---:|---:|---:|---:|
| O1 VIX term | 18.40% | 18.29% | 19.48% | 20.18% | **0.55** |
| O2 MA200 | 21.27% | 19.43% | 20.63% | 21.32% | 0.98 |
| O3 both | 21.72% | 19.48% | 21.00% | 21.37% | 1.00 |

(baseline on this path subset: 17.47%.)

The placebo is the finding. A **randomly placed** exposure schedule with the same 21% duty cycle gains
**+2.0pt** on its own. O1's real signal lands at the 55th percentile of its own placebo — pure noise.
O2/O3 do clear placebo p95, so a *sliver* of genuine regime alignment exists (~+0.7-1.0pt over a random
schedule) — but it is smaller than the gap to the trivial constant control, so it buys nothing.

## 6. Confirmation on real historical paths (canonical cohort funnel)

The bootstrap resamples blocks. `cohort_funnel.py` re-runs the same question on the actual market
history with the project's canonical metric: cleanroom 2-step retry funnel, 91-day wall, cohort starts
every 7 days (N = 454), overlay injected into the engine's own sizing function.

| variant | p(campaign) | p(1-try) | median days | fail daily | fail floor |
|---|---:|---:|---:|---:|---:|
| baseline | 7.05% | 25.99% | 53.5 | 11.5% | 37.4% |
| O1 VIX term | 7.05% | 26.21% | 51.5 | 13.4% | 36.3% |
| O2 MA200 | 7.27% | 27.31% | 54.0 | 12.6% | 36.1% |
| O3 both | 7.05% | 26.65% | 54.5 | 13.4% | 35.5% |
| **de-lever vol-matched to O1** | **8.15%** | 29.52% | 61.0 | 10.4% | 34.8% |
| **de-lever vol-matched to O3** | **9.47%** | 27.53% | 57.0 | 9.9% | 34.6% |

Cohort placebo band on the best variant (O2, 24 rotations): real 7.27% vs placebo p50 6.83%, **p95
8.12%**, max 8.59% → real sits at the **75th percentile of its own placebo**. On 1-try: real 27.3% vs
placebo p95 28.6%, **71st percentile**.

On real paths the overlay's Δp(campaign) is **+0.0 to +0.2pt**, it is **inside its placebo band**, and
the constant de-lever delivers **+1.1 to +2.4pt**. Same verdict, arrived at independently.

> **Absolute levels here are not the canonical campaign figure.** 7% p(campaign) reflects the book as
> *currently deployed* — MONO, ORB off, whole sample, 91-day wall — not the ~80% headline of the
> 4-sleeve book. That gap is a restatement of the desk-audit finding that the deployed book is mono,
> not a new result, and it is irrelevant to the comparison, which is paired across identical
> conventions.

## 7. Verdict against the pre-registered rule

| condition | O1 | O2 | O3 |
|---|:--:|:--:|:--:|
| (a) Δp > 0, paired CI excludes 0 | ✅ | ✅ | ✅ |
| (b) beats placebo p95 | ❌ (p55) | ✅ bootstrap / ❌ cohort (p75) | ✅ bootstrap / — |
| (c) **beats vol-matched uniform de-lever** | ❌ | ❌ | ❌ |
| (d) gain on the daily-barrier channel | ✅ | ✅ | ✅ |

**REJECTED**, on the condition the pre-registration made decisive. The overlay's entire effect is
explained by "the book traded smaller", and the free `vm` parameter does that strictly better — with no
yfinance dependency, no VIX3M staleness (its feed was already 7 days stale at the time of this study),
and no new live failure mode.

## 8. What this closes, and the one thing it does not

- **Closed**: exogenous regime overlays (VIX term structure, price vs MA200) as a p(pass) lever on the
  deployed FTMO book. Do not re-propose without a *different* mechanism.
- **Generalises L15**: the sharper statement is not about MaxDD. This book has MaxDD −81%, met L15's
  condition, and the overlay still failed. The binding condition is whether the regime that predicts
  the **variance** also predicts the **mean in the same direction**. Here it predicts the mean in the
  *opposite* direction — the overnight premium is compensation for the stress regime — so any cut is a
  cut in the earning days. A regime overlay can only help when high-vol regimes are also low- or
  negative-return regimes for that specific book.
- **Not a recommendation to change `vm`.** This study measures p(pass) only. That a constant c ≈ 0.73
  raises p(pass) ~4pt is consistent with the existing vm-sweep result that p(pass) rises as size falls
  while **EV plateaus over vm ∈ [10, 30]** — because a slower, smaller challenge also earns less once
  funded. p(pass) is not EV. Nothing here justifies re-sizing the live account.

## 9. Reproduce

```
/usr/bin/python3 build_book.py      # book reconstruction + L15 MaxDD
/usr/bin/python3 regime_signals.py  # exposures + look-ahead assertion
/usr/bin/python3 run_overlay.py     # bootstrap: main table + placebo band  -> outputs/
/usr/bin/python3 cohort_funnel.py   # real-path cohort confirmation          -> outputs/
```
Outputs: `outputs/main_table.csv`, `outputs/placebo_table.csv`, `outputs/cohort_table.csv`,
`outputs/cohort_placebo.json`, `outputs/meta.json`. Caches in `cache/` are regenerable.
