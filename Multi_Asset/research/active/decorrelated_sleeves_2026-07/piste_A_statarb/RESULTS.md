# RESULTS — Piste A: Stat-arb / pairs (cointegration) on FTMO

**Run:** 2026-07-08, daily UTC, 2007/2013→2026. Protocol = frozen `PREREGISTRATION.md`.
**Artifacts:** `coint_screen.csv`, `backtest_grid.csv` (96 trials), `summary.json`, `autopsy_A.py` output.
> **⚠ Correction 2026-07-08:** a financing sign bug (fixed) had inflated the backtest Sharpe cells — e.g.
> the "seductive" US500/US30 cell was **0.97 with the bug, 0.27 corrected** (best two-sided now 0.27). The
> **verdict is UNCHANGED and cleaner**: the falsification rests on the cointegration screen (0/12 OOS-coint,
> half-life 112–566 d), which is financing-independent. See `../iteration_2/CORRECTION_2026-07-08.md`.

## Verdict: **FALSIFIED** — 3 of 5 pre-registered triggers fired (F1, F2, F4).

The family produces a *seductive* in-sample Sharpe (~1.0 on several index pairs) that is **not** a
mean-reversion edge: it is slow **relative-drift** capture on **non-cointegrated** spreads, concentrated
in the direction the sample happened to trend. Every pre-registered structural gate rejects it.

---

## 1. Cointegration screen (the decisive gate) — F1 + F2 fired

| pair | ret-corr | EG p (full) | **EG p (OOS)** | Johansen r≥1 | **half-life (d)** |
|---|--:|--:|--:|:--:|--:|
| US100/US500 | 0.93 | 0.085 | **0.61** | no | 194 |
| US100/US30 | 0.81 | 0.008 ✓ | **0.12** ✗ | no | 112 |
| US500/US30 | 0.94 | 0.226 | **0.82** ✗ | no | 253 |
| US500/GER40 | 0.79 | 0.080 | **0.17** | no | 191 |
| EURUSD/GBPUSD | 0.63 | 0.014 ✓ | **0.060** ✗ | yes | 222 |
| AUDUSD/NZDUSD | 0.83 | 0.187 | 0.50 | no | 345 |
| XAUUSD/XAGUSD | 0.79 | 0.109 | 0.38 | no | 387 |
| *(12 pairs total — full table in `coint_screen.csv`)* | | | | | |

- **F1 — 0/12 pairs OOS-cointegrated** (β fit on first half, ADF on second half; best = EURUSD/GBPUSD p=0.060). Per-year cointegration fraction is **14–29 %** ≈ the 5 % false-positive rate compounded → **no stable structural anchor.** A trader standing at any point in time, using only past data, would not find a stationary spread — the classic look-ahead the family bakes in.
- **F2 — half-life wall.** Every spread reverts over **112–566 days** (minimum 112). There is no fast/intraday-reverting pair in the liquid FTMO universe → holds are forced to **months** (measured avg **63–82 days**).

## 2. The high-Sharpe cells are a relative-drift beta trap — F4 fired

The top backtest cells look promotable at a glance; the two-sided autopsy shows what they are:

| cell | net Sharpe | HAC t (daily) | n_trades | avg hold | **long-spread leg** | **short-spread leg** |
|---|--:|--:|--:|--:|--:|--:|
| US500/US30 (z2.0) | 0.97 | 3.72 | 35 | 80 d | **+283 bps, 83 % win** | +148 bps, **53 % win** |
| US30/GER40 (z1.5) | 0.90 | 3.63 | 42 | 63 d | **+420 bps, 87 % win** | +95 bps, **58 % win** |
| US100/US500 (z1.5) | 0.76 | 2.60 | 36 | 82 d | **+322 bps, 83 % win** | +66 bps, **50 % win** |

- **The edge is one-directional.** In every cell the profitable leg is the one **aligned with the realised 2013–2026 relative trend** (S&P > Dow, US > DAX): long-spread wins **83–87 %**, short-spread is a **50–58 % coin-flip**. "Two-sided net ≥ 0" is satisfied only because the sample's drift direction paid; the *symmetric* reversion the hypothesis requires is absent. This is exactly the pre-registered **F4** mechanism — *market-neutral by construction ≠ two-sided in spread; the spread inherits a directional drift.*
- **Significance is autocorrelation-inflated.** Daily HAC t = 3.7 treats ~2,850 highly autocorrelated days (80-day holds) as independent. The honest count is **N_eff = 35 trades**; trade-level block-bootstrap p = 0.004 (real in-sample, but on a non-cointegrated, direction-concentrated bet). Daily DSR reads 0.89 but is overstated for the same N_eff reason.

## 3. FTMO-specific kills (independent of the above)
Even granting the in-sample Sharpe, this cannot be an FTMO sleeve:
1. **Presence ≈ 1.0** (80-day holds, always in a position) → §4 ranks this **REJECT** (needs presence ≤ 0.4). It is the *photographic negative* of the intermittent, hard-stopped profile the book needs.
2. **~2.7 trades/yr** cannot compound to **+10 %** inside the 91-day challenge window.
3. In-sample MaxDD −7.8 %, but an **OOS relative-drift reversal** (the sample's trend un-winding) breaches the −10 % static floor — the same tail that makes the "edge" untrustworthy makes it un-survivable.
4. **FTMO hedging rule** forbids opposing positions on correlated instruments → the 2-leg construction is not even placeable; a single-leg expression discards the hedge and reverts to directional beta.

## 4. §4 profile scorecard
| §4 axis | required | this family | |
|---|---|---|:--:|
| tail-decorrelation vs book | ρ_tail ≤ 0.3 | ✓ (genuinely market-beta-neutral) | ✓ |
| presence-in-position | ≤ 0.4 | ✗ **≈1.0 (80-day holds)** | ✗ |
| per-active-day edge | SR ≥ 1.5 | ✗ (no symmetric edge; drift only) | ✗ |
| deleverageable / bounded excursion | ✓ | ⚠ divergence tail (coint break) | ⚠ |
| **stable OOS anchor (prerequisite)** | **required** | ✗ **0/12** | ✗ |

## 5. What would have to be true to revisit (not currently in scope)
A pair with a **hard structural convergence mechanism** (ETF create/redeem, index-inclusion, physically-linked contracts) rather than statistical co-movement — none exists in the liquid FTMO CFD set. Sub-bar (market-maker-tier) execution could make a fast spread tradeable, but that is not retail FTMO. **No re-test on the audited engine is warranted:** the failure is at the cointegration-stability layer, upstream of any engine.

**Reconciliation with in-repo precedent:** deferred to `synthesis/` — this fresh daily pass independently reproduces the deep-dive's four killers, and finds cointegration *weaker* still at daily frequency (0/12 OOS vs the 1H pass's 2/18; half-lives 112–566 d vs 22–180 d).
