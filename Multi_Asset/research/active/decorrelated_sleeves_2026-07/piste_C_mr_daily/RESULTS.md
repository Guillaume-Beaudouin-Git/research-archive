# RESULTS — Piste C: Daily / multi-day MR on indices after excess

**Run:** 2026-07-08, daily UTC, 2007/2013→2026. Protocol = frozen `PREREGISTRATION.md`. 84 trials.
**Artifacts:** `backtest_grid.csv`, `summary.json`.
> **⚠ Correction 2026-07-08:** a financing sign bug (fixed) inflated the net Sharpe cells (best 0.53→**0.36**
> corrected). **Verdict UNCHANGED**: the short leg is net-negative on all indices (beta trap) — that finding
> is about the *sign* of the drift, unaffected by the swap magnitude. See `../iteration_2/CORRECTION_2026-07-08.md`.

## Verdict: **FALSIFIED** — it is the same beta trap as the already-falsified 15-min version. The horizon change did not rescue the short leg (F1 + F3 fired).

The user's own legitimacy test — *"be honest: if after framing it looks like the MR already falsified,
say so"* — resolves cleanly: **it does.** Moving from 15-min to daily/multi-day, and from a 30-min band
to RSI/Bollinger excess, changed nothing that matters. The short leg still loses to index drift.

---

## 1. The decisive two-sided test — short leg (fade overbought) on indices

| instrument | short-leg mean (bps/day-in-pos) | short-leg HAC t | long-leg mean | uncond. drift |
|---|--:|--:|--:|--:|
| US100 | **−4.0** | −1.35 | +27.2 | +6.0 |
| US500 | **−3.5** | −1.55 (RSI2 cell **−2.22**) | +10.9 | +4.1 |
| US30 | **−2.1** | −0.77 | +8.2 | +3.2 |
| GER40 | **−0.8** | −0.20 | +8.6 | +2.9 |
| XAUUSD | **−2.8** | −0.78 | +7.0 | +3.2 |

**Across all 48 index cells (4 indices × 3 excess defs × 2 thresholds × 2 exits):**
short-leg net>0 in only **6/48** (≈ chance), **0/48** significant (t>2); mean short-leg t = **−0.97**.
On US500-RSI2 the short leg is **significantly negative** (t −2.22) — you *lose* fading S&P strength.
Robust across RSI(2), RSI(14) and Bollinger %b — not a single-definition artefact.

**Reading:** the long leg is strong (US100 +27, up to +50 bps/day-in-position on RSI14) but that is
**buy-the-dip index beta** — it is long the index, timed on pullbacks, and it does not have a symmetric
counterpart. A one-sided long that only pays because the index drifts up = **L25 beta trap**, identical
in signature to the falsified 15-min study.

## 2. Clean swap isolation (what daily adds over the swap-free intraday study)
At daily horizon the **swap asymmetry favours the short leg** (shorting US100 earns **+0.09 bps/night**;
longing pays −2.13). So the short-leg failure is **not** financing — it is purely the drift/beta. The
intraday study (swap-free) could not make this isolation; the daily pass proves the killer is directional
drift, full stop.

## 3. No cell is deployable
- **Best net Sharpe anywhere = 0.525; 0/84 cells exceed the 0.7 RESEARCH_PASS gate** (F3 fired).
- The only faintly two-sided cells are **FX, not indices** — USDJPY-Bollinger (short +3.0 bps, t 1.42,
  net SR 0.39) and EURUSD-RSI2 (short +2.2, t 1.73, net SR 0.32). None is significant, none clears 0.7,
  and USDJPY's best cell has MaxDD **−12.7 %** (> −10 % floor). These match the repo's known
  EURUSD-midday / weak-FX-reversal knife-edge, not a new edge.
- DSR footnote: the top USDJPY cell scores DSR 0.965, i.e. its 0.53 Sharpe is *not a fluke* — but a
  real-and-low 0.53 still fails the deployable bar. DSR confirms honesty, it does not manufacture size.

## 4. §4 profile scorecard
| §4 axis | required | this family | |
|---|---|---|:--:|
| two-sided ⇒ tail-decorrelation | short leg net ≥ 0 | ✗ **−2.6 bps mean, indices** | ✗ |
| per-active-day edge | SR ≥ 1.5 | ✗ (best book SR 0.53) | ✗ |
| short-hold / intraday-m | ≤ 1.5 | ✓ (≤10-day, 2×ATR stop) | ✓ |
| deleverageable | ✓ | ✓ | ✓ |

Shape axes fine; the **edge axis fails** — §4 is necessary, not sufficient (same conclusion the profile
study reached for intraday MR).

## 5. What would have to be true to revisit
A genuinely two-sided daily reversion would need the SHORT leg to pay on a **non-up-drifting** universe
(the FX blips hint at this but are sub-threshold and carry-era-fragile). On up-drifting equity indices
the short leg cannot escape the drift. **No audited-engine re-test warranted** — it fails the two-sided
prerequisite upstream of any engine.

**Reconciliation:** deferred to `synthesis/` — independently reproduces `MR_deepdive_ftmo.md` (beta trap
on indices; knife-edge on FX), extended to the daily horizon with the swap-isolation addition above.
