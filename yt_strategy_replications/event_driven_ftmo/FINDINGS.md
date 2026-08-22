# FINDINGS (PRELIMINARY) — Event-driven, defined-risk, FTMO-targeted
**Date:** 2026-06-20 · **Pre-registration:** `PREREGISTRATION.md` (frozen before any price-outcome contact).
**Mandate:** §4 rank-2 family (concentrated, defined-risk, scheduled-event) from the FTMO-compatible-profile study.
**Confidence tag (per pre-reg):** reimplemented engine → a POSITIVE would be a *candidate* for audited-engine
revalidation; this is a **NEGATIVE → definitive**. Independently re-verified (author≠auditor). No git HEAD ops;
live book untouched; nothing deployed.

## 0. Verdict — NOT §4-viable on free CFD data (two independent kills)
Scheduled US macro events (CPI / NFP / FOMC) on US500 / US100 / XAUUSD offer **no tradable, two-sided,
defined-risk intraday edge** on naked CFDs, for two independent reasons:
1. **No edge survives the release bar.** The surprise is fully priced *inside* the 5-min release bar (positive
   control fires: hot CPI loads −2.2 to −2.6 t on the release-bar return — equities & gold down, economically
   coherent). The **post-release** drift is insignificant, **not two-sided**, and **sign-flips by regime**
   (CPI 2018-21 −6.3 bps → 2022-26 +3.4; FOMC +9 → −18) — the exact L33 regime trap that killed post-FOMC drift.
   Pooled post-release continuation is negative (CPI −1.2, NFP −2.8, FOMC −3.7 bps/event; DSR≈0 at N=110).
2. **Risk is undefinable on naked CFD.** The release bar is a **3–4×ATR shock** (full range 6–7×ATR); a 1×ATR
   hard stop is **gapped through ~90% of the time** (P(|r0|>1ATR) 65–96%; post-entry adverse excursion 3–6×ATR).
   The intraday excursion m ≈ 3–6 **dwarfs the §4 ceiling of 1.5** → a naked directional event trade violates the
   funded daily barrier. Only **options** (loss capped at premium) deliver true defined risk — outside free-CFD/FTMO-CFD scope.

The §4 profile again did its job: the event family *structurally* fits presence/intermittence, but fails the
two axes that matter here (a real two-sided edge, and a bounded excursion). **§4 necessary, not sufficient** — confirmed a second time.

## 1. Phase-0 (L48) — already killed in-repo, not re-mined
- Post-FOMC drift (Treasuries): dead post-2015, sign-inverts 2022 (`post_fomc_drift/report.md`). Bonds, Gate-0.
- Savor-Wilson announcement-day premium (US500): drift accrues off-event, β −3.15 bp (`announcement_premium/report.md`). Daily long-only.
- This study is the untested cell: **intraday, surprise-conditioned, two-sided, defined-risk** reaction on equities+gold.

## 2. HEV-1 — release-bar loads on surprise (POSITIVE CONTROL, validates alignment)
Regress release-bar return on standardized surprise (HAC lag-6):

| | US500 | US100 | XAUUSD |
|---|--:|--:|--:|
| CPI slope t / R² | −2.23 / .23 | −2.34 / .22 | −2.58 / .21 |
| NFP slope t / R² | +0.48 / .00 | −1.00 / .00 | −1.82 / .09 |

CPI fires cleanly and economically (hot inflation → equities & gold down). NFP is multi-factor (wages/revisions) →
weak single-surprise loading, as expected. FOMC rate-surprise ≈ 0 (ZIRP era) → degenerate, used only below.
**Alignment & timestamps are correct** — so the HEV-2 negative is not an artifact.

## 3. HEV-2 — tradable post-release continuation (THE edge test) → FAIL
Enter at the bar AFTER the release bar (t0+5min), exit t0+60min, direction = sign(release move). Per-event bps, HAC-t:

| pooled (3 instruments) | n | continuation bps/ev | t_HAC | two-sided? | regime 18-21 → 22-26 | DSR(N=110) |
|---|--:|--:|--:|:--:|--:|--:|
| CPI | 294 | −1.22 | −0.61 | no | sign-flips | 0.001 |
| NFP | 300 | −2.80 | −1.16 | no | negative both | 0.000 |
| FOMC | 198 | −3.66 | −0.75 | no | sign-flips | 0.000 |

Legs never both positive (e.g. US100 NFP up −6.2 / dn −9.5; US500 CPI up −0.1 / dn −2.9). Independent audit pooled
all events×indices: −3.5 bps, t −2.02 (mild reversion *against* entry, wrong sign, and below the ~5–10 bps CFD RT).
No horizon/threshold sweep was run (anti-mining): one fixed window, as pre-registered.

## 4. HEV-4 — defined-risk falsification (the §4 disqualifier) → risk NOT definable
Release-bar move and post-entry adverse excursion in pre-event-ATR units (median):

| | |r0|/ATR | P(\|r0\|>1ATR) | post-entry MAE/ATR |
|---|--:|--:|--:|
| CPI (US500/US100/XAU) | 3.6 / 3.5 / 2.8 | .77 / .80 / .80 | 3.0 / 3.2 / 3.2 |
| NFP | 3.6 / 3.3 / 3.4 | .93 / .77 / .82 | 3.9 / 4.2 / 3.7 |
| FOMC | 2.3 / 2.2 / 2.5 | .73 / .65 / .73 | 5.2 / 4.7 / 5.9 |

Auditor (independent): release-bar full range 6–7×ATR, worst-side excursion vs a 1-ATR stop median ~5.5×, P(>1ATR)
89–96%, P(>2ATR) 72–90%. **A hard stop is gapped ~90% of the time** → naked-CFD "defined risk" is illusory; the
effective intraday-m is 3–6.

## 5. §4 scorecard
| §4 axis | required | event family (naked CFD) | |
|---|---|---|---|
| presence / intermittent | ≤0.4 | ✓ (≈3 events/mo) | pass |
| deleverageable vol | ≤8% | ✓ | pass |
| two-sided ⇒ tail-decorr | ρ_tail ≤0.3 | ✓ by design | pass |
| **intraday excursion m** | **≤1.5** | **✗ 3–6 (release shock)** | **FAIL** |
| **per-active-event EDGE** | **net>0, two-sided, regime-stable** | **✗ none** | **FAIL** |

## 6. Independent audit (author≠auditor)
From-scratch reimplementation confirmed: positive control fires (CPI slope −2.24/−2.14 t, R²≈.23), release bar is a
multi-ATR shock (P(>1ATR) 89–96%, stop gapped ~90%), no two-sided/regime-stable post-release edge (pooled −3.5 bps,
t −2.02), no bug or look-ahead (ATR strictly pre-t0, entry strictly post-release bar, DST handled by true-UTC).
**Negative CONFIRMED.**

## 7. Implications & redirect
- **§4 ranking now empirically resolved on free data:** rank-1 (price-only intraday MR) falsified; rank-2
  (defined-risk event) falsified on naked CFD. The recurring blocker is the §4 study's own thesis: *the profile is
  a filter, not an edge generator.*
- **The only §4-viable event vehicle is options** (loss capped at premium → true defined risk, bounded m). FTMO/CFD
  has no options → this family cannot fit §4 in the current execution venue. Off-table without a venue change.
- **Free price+calendar data is now exhausted** for both top §4 families (extends L43 / `nonovernight_search`).
  The live levers remaining are the §4 study's strategic ones: multi-account architecture, a lower-cost/finer
  execution venue, or a genuinely different data axis (e.g. order-flow, options surface) — not more free-OHLC mining.

**Lesson candidate (NAMED, to engrave at reconciliation):**
`scheduled-macro-events-are-priced-in-the-release-bar-and-undefinable-on-naked-CFD` — the surprise loads on the
5-min release bar (CPI t≈−2.3, equities+gold down) but post-release drift is not two-sided, sign-flips by regime
(L33), and is sub-cost; the release bar is a 3–7×ATR shock so a 1×ATR stop gaps ~90% (effective m≈3–6 ≫ §4's 1.5).
Naked-CFD event trades fail §4 on BOTH edge and defined-risk; only options qualify. Complements the
`announcement_premium` and `post_fomc_drift` kills. (Family: L25/L31/L33/L42.)

## 8. Reproduce, ledger & handoff (no git ops performed)
```
cd yt_strategy_replications/event_driven_ftmo
/usr/bin/python3 event_study.py    # -> results_event.json, prints HEV-1/2/4 tables
```
Calendar source: `data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv` (TradingView, ISO-UTC,
actual/forecast; provenance `calendar_gap_report.md`). Dates known-in-advance → look-ahead-safe (L1/L26).
`n_tests` added ≈ **9** (3 events × 3 instruments, one fixed window each), all FAIL — increment the program ledger.
**Isolation:** additive folder, zero git HEAD ops (shared working dir; 2026-06-19 incident). Commit recipe identical
to `intraday_mr_ftmo/FINDINGS.md §7` (worktree off origin/main, copy folder, commit, PR); run
`tools/check_register_integrity.py` in the **main** dir before the closing commit.
