# XAUUSD intraday range-fade — honest reconstruction (no grid)

**Date:** 2026-05-31 · **Sprint:** Family-4 (gold range-fade) · **Verdict: NO-GO — EDGE FAILURE (terminal)**
**Code:** `PropFirms/ftmo_alpha_program/strategy/xauusd_rangefade.py`, `run_family4_xau.py`
**Data:** MT5 1-min XAUUSD panel (`data/panels/m5_indices/XAUUSD_M1.csv`), 2020–2026.
**Protocol:** characterise IS 2022-2024, render verdict on the **untouched hold-out 2025-2026**; cost gate L11 first; DSR at the honest trial count; FTMO Monte-Carlo honest. No tuning to pass a gate.

---

## Étape 0 — Mechanism note (the testable prior)

**Declared mechanism.** Retail "gold scalper" EAs fade extensions of the intraday range, most
aggressively in the **Asian session (≈00–08 UTC)**. Recon confirms the regime prior: in Asia,
XAUUSD realised |ret| is **2–6 bps/30min** vs **8–14 bps** in the US data session (12:30–14:00
UTC CPI/FOMC). Asia is the low-vol, range-bound window where mean-reversion *should* live. Spread
is mildly wider in Asia ($0.13–0.19) than the US session ($0.08–0.11); the 21–22 UTC rollover
blow-out is excluded (Phase 0b).

**Grid signature — NOT reproduced (this is the point).** The EAs' advertised 90%+ win rate is an
**artefact of grid/martingale averaging into losers**, not an edge. Toxicity removed in this study:
(1) one position at a time, never averaging/lot-progression; (2) a **hard per-trade stop that exits
and realises the loss**, never a cap-and-continue (L25); (3) intraday-flat (no swap/gap). Under
FTMO's *equity* drawdown (floating losses included), a grid touches the −10% static floor in one
CPI/FOMC trend session — and the lot-consistency / cumulative-exposure rules make it non-deployable
regardless. The grid is a mechanism source, never code to copy.

**Honest reconstruction.** z-score of log price vs a causal 16-bar range; fade |z|>2, exit on
reversion (|z|<0.5), hard stop, intraday-flat in Asia. Optional backward-looking regime filter
tested on/off (a frequency/shape lever, **not** a tail protector — the stop bounds the tail).
Modifications counted: stop level {0.3, 0.5, 0.7%}, filter {on, off} → trial count set to 50 for DSR
(conservatively absorbing prior XAU work).

---

## Étape 1–2 — Results and gates (canonical: hard stop 0.5%, no filter, CFD ×3)

### The decisive isolation — GROSS (zero-cost) Sharpe

This separates *cost* from *edge*. If the only configuration with positive gross is the no-stop one,
the "edge" is the grid toxicity. Here **none is positive** — IS or on the untouched hold-out:

| Configuration | IS gross Sharpe | OOS gross Sharpe (untouched) | per-trade WR |
|---|---|---|---|
| no stop (hold to reversion/EOD) | **−0.12** | **−1.07** | 57% |
| hard stop 0.5% | −0.31 | −0.59 | 57% |
| hard stop 0.5% + regime filter | −0.41 | −0.25 | 58% |

Per-trade win rate is 56–58% (a *weak* reversion tendency exists) but **gross expectancy is
negative**: the occasional Asia trend day (overnight macro shock) produces losses that swamp the
small range-fade wins. The grid hides exactly these by averaging down instead of taking the loss.

### Gate battery (mandated order)

| Gate | Result | Verdict |
|---|---|---|
| **1. Pre-flight cost L11** | gross **−5.0%/yr** vs cost 18.7%/yr, ratio **−0.27** | **FAIL** (no gross edge to cover any cost) |
| **2a. Daily kurtosis** | 4.5 | FAIL (gate < 3) |
| **2b. Tail-DD** P(touch −8%/60 sessions) | **50.6%** | FAIL (gate < 10%) |
| **3. Hold-out 2025-26 (untouched)** | IS net −1.45 → **OOS net −1.23** | FAIL |
| **3b. Per-year Sharpe** | 2022 −0.6 · 2023 −1.5 · 2024 −2.1 · 2025 −2.2 · 2026 +0.7 | consistently negative |
| **4. DSR** (Bailey–López de Prado, n_trials=50) | **0.000** | FAIL (gate ≥ 0.95) |
| **5. FTMO Monte-Carlo (honest, no time limit)** | combined P(pass) **5.0%** (σd 1%), 1.1% (σd 0.6%) | FAIL (vs 70%) |

The FTMO P(pass) of 5% is **below the ~30% zero-edge baseline** — a negative-drift book does *worse*
than a coin flip against a symmetric barrier. Cross-feed validation was unavailable (no independent
XAUUSD feed exists in the repo; per-year stability + the untouched hold-out substitute, flagged).

---

## Verdict — NO-GO, and it is an EDGE failure (not cost)

The sprint's single question — *is there a real range-fade edge once the grid is replaced by an
honest stop?* — is answered: **no, and the failure is at the edge, not the cost.** Gross Sharpe is
negative at **zero cost**, **with and without the stop**, **in-sample and on the untouched hold-out**.
There is no positive gross expectancy to be eaten by the spread; the EAs' 90% win rate is confirmed
as a grid-management artefact. **Terminal for this mechanism.**

This does **not** reopen the venue pivot: a cheaper venue (futures) cannot rescue a negative gross
edge. Contrast with what a *cost* failure would have implied (real gross OOS edge, eaten by CFD
spread ×3 → potentially venue-fixable, and a reopening of the venue↔distribution thesis with a
surviving edge in hand). That branch did not occur.

**Place in the program.** Fourth independent mechanism (after FX intraday MR, index-CFD MR, index
pairs) to fail, and the third to fail at *robustness/edge* rather than cost. The earlier venue
diagnostic already showed the best FX candidate (EURUSD) has OOS gross Sharpe ≈ 0.11 — i.e. no robust
edge even at zero cost. The weight of evidence now favours the **"no robust alpha across the tested
mechanisms"** thesis over the **"alpha exists but is unsellable on retail CFD"** thesis. The closing
synthesis is calibrated accordingly.
