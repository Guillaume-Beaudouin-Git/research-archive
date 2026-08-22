# Idea 2B — NQ intraday OU mean-reversion (single-leg) — PRE-REGISTRATION
*Frozen 2026-06-03 BEFORE results, per `RESEARCH_PROTOCOL_statarb.md`. Results appended below only.*

## Hypothesis (economic)
Intraday, index price overreacts to short-horizon order flow and reverts toward a local fair value (liquidity provision / inventory effects). Deviations from an intraday rolling fair value are fadeable. **Single instrument (NQ) → fully FTMO-compliant** (no opposing/correlated legs).

## Two decisive risks stated UP FRONT (this idea's likely failure modes)
1. **Bid-ask bounce (artifact):** 1-min reversion is heavily inflated by the bid-ask bounce — spurious negative autocorrelation that is untradeable net of spread. **Decisive test: a 1-bar entry delay.** A real reversion survives it; a bounce artifact collapses.
2. **Cost / turnover (L33):** intraday MR is high-turnover and thin-edge; realistic NQ spread+commission can flip it negative. **Decisive test: measured-cost sweep.** Must survive realistic cost.
*(Prior internal work flagged NQ intraday z-fade as cost-killed/neg-skew. We retest fresh and honestly; if it dies the same way, that is the recorded result.)*

## Data
NQ databento 1-min, **RTH cash only, roll days skipped, US/Eastern, 2010-06→2026-05** (pristine; the cleanest series in the project). Flat overnight (no gap risk).

## Signal (frozen, strictly causal, intraday — resets each session)
Within each RTH session, on 1-min closes, using only bars ≤ t in the session:
- fair value `f_t` = rolling mean of close over **Wmin** bars (baseline 30); `σ_t` = rolling std over Wmin; `z_t = (close_t − f_t)/σ_t`.
- **Entry:** short if `z_t ≥ +Z_in`; long if `z_t ≤ −Z_in` (fade the deviation). Baseline Z_in **2.5**.
- **Fill:** at the **next bar** (t+1) — no same-bar look-ahead. (Delay test = t+2.)
- **Exit:** `z` reverts through 0 (target), OR `|z| ≥ Z_stop` (stop, baseline 4), OR **last bar of session** (force flat — no overnight). One position at a time (single-leg).

## Cost model (the decisive gate)
Round-trip NQ cost in index points; baseline **1.0 pt** (~1 tick spread 0.25pt + commission + slippage). **Sweep 0.25 / 0.5 / 1 / 2 pts.** Require survival at realistic (~0.5–1 pt) cost.

## Evaluation
Per-trade stats; **mean-reversion gate** (intraday Hurst/VR — interpreted with bounce caveat); **1- and 2-bar delay test**; by-year/regime; train(2010–2018)/OOS(2019–2026); **FTMO 2-step first-passage** (daily-MTM, contiguous) + leverage sweep; **DSR** on the grid.

## Pre-registered grid (only this; DSR-corrected)
Wmin ∈ {15, 30, 60}, Z_in ∈ {2.0, 2.5, 3.0}, Z_stop ∈ {4}. Baseline (30, 2.5, 4). ≤9 trials.

## Acceptance (charter Part D — must pass ALL)
single-leg compliant · no-look-ahead · reversion confirmed · **survives 1-bar delay** · **survives measured cost** · positive OOS & across regimes · first-passage p(funded)/bust with CI · DSR-significant · reproducible.

---
*(Results appended below after the engine runs — never above this line.)*

---

# RESULTS & VERDICT (2026-06-03)

## VERDICT: ❌ KILL — no gross edge + catastrophic cost-kill (L33). Decisive, fast.

NQ databento 1-min RTH, 2010–2026, 4,041 days, 1.55M bars. Baseline 30/2.5/4, fill t+1.

- **Turnover: 152,076 trades (~37.6/day).** Pure intraday z-fade fires constantly.
- **No gross edge:** mean **−0.02 bps/trade, t = −1.09, win 48.1%** at ZERO cost. There is essentially no reversion edge in 1-min close-to-close to a rolling mean.
- **Cost sweep (the decisive gate) — dies instantly:** 0.25pt → −0.49 bps (t −24); **0.5pt → −0.96 bps (t −47)**; 1pt → −1.91 bps; 2pt → −3.79 bps. At realistic NQ cost the strategy bleeds ~−0.96 bps × 37 trades/day.
- **Every one of 16 years negative** at 0.5pt (−2.45 → −0.13 bps; the bleed shrinks only because NQ's price level rose, shrinking a fixed-point cost in bps).
- Delay test moot (gross already ≈0; no bounce-driven false positive to collapse). Grid/FTMO first-passage **not run — moot** for a zero-gross, cost-killed signal (it would bust ~surely).

**Diagnosis:** single-instrument intraday mean-reversion on a liquid index has (a) ~no net-of-microstructure edge in close-to-close and (b) ruinous turnover×cost. This is the canonical L33 cost-kill, reproduced cleanly on a fresh pre-registered test.

**Checklist:** ❌ edge positive · ❌ survives measured cost (catastrophic) · (others moot). KILL.

