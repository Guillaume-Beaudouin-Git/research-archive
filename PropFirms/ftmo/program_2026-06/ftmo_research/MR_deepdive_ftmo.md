# Mean-Reversion intraday — FTMO deep-dive (depth, not breadth)

**Mandate:** the alpha-hunt's "MR dead" came from **one** parameterization (fade dev-from-30min-mean,
fixed +30min hold, 2 thresholds, 5 instruments). That rejects a *setting*, not a *family*. This is the
proper depth pass: explore the MR space systematically and let the evidence — under the full
anti-false-positive discipline — decide whether a **two-sided, retail-accessible** intraday MR alpha
exists on FTMO instruments.

**Epistemic stance going in:** unknown. Prior hard (arbitraged space) but "hard ≠ impossible," and a
breadth scan cannot settle it. Tested in depth below.

---

## Verdict up front

> **After real depth — ~350 trials across logic × timeframe × exit × threshold × regime × instrument, every cell under non-overlap + per-trade cost + 1-bar-delay + two-sided + DSR-on-the-total-space — there is no two-sided, delay-robust, threshold-robust, OOS-stable, multiple-testing-surviving intraday MR alpha on FTMO instruments. This is now a depth-based verdict on the family, not a shallow one.**
>
> - **Unconditional grid (284 cells):** only **2** were net-positive (t≈0.4), **0 two-sided**. Every net-positive cell is one-sided (the long leg is the up-drift = beta; or, on NQ, a one-sided short).
> - **Regime conditioning (the steelman — "where MR lives"):** surfaced **4 / 60** two-sided-positive cells (US100 high-vol; EURUSD midday). All have **t ≤ 1.44** — below the multiple-testing bar (expected max |t| by chance ≈ **2.94** at N≈350).
> - The most credible single cell, **EURUSD-midday**, is a **knife-edge** (works only at θ=2.0 and only in the 11–14 UTC hour; OOS-train t=0.54), and even if real is **+1.3 %/yr at 1×** — far too thin to reach FTMO +10 % without daily-DD-blowing leverage.
> - **Half-life was estimated and matched** (≈8 bars on 5m/15m), correcting the v1 fixed-30min error. It did not change the conclusion.
>
> The two-sided requirement is the decisive filter and it is never satisfied robustly: what reads as "reversion" on the winning leg is the directional drift of the period. **MR on liquid FTMO majors is beta-contaminated noise, not a symmetric alpha.**

This complements the earlier `ALPHA_hunt_ftmo.md` breadth result — now the MR cell is closed *at depth*.

---

## 1. Method & systematic space

**Discipline applied to every cell (the quality control):** non-overlapping trades; per-trade cost in
bps (CFD real: indices **1.5 bps**, EURUSD **1.0 bps**); **1-bar execution-delay** column (decisive —
real edge survives, artifact collapses, L26); **two-sided** (long-leg & short-leg reported separately —
one-sided long = beta = reject); **holding matched to estimated half-life**; **N_trials tracked across
the whole grid** for DSR/AMTP deflation on the *total* space.

**Half-life (AR(1) of deviation from SMA20, within-session):** ≈ **8–9 bars** on 5m and 15m across all
instruments → holdings set to ~8 bars (≈40 min on 5m, ≈2 h on 15m), *longer* than v1's 6-bar/30-min
exit. (30m/60m intraday too thin for a clean within-session AR(1).)

**Grid (pre-registered):** instruments {NQ (real volume→real VWAP), US500, US100, US30, GER40, EURUSD}
× TF {5m,15m,30m} × logic {SMA20-z, EMA20-z, VWAP-dev, RSI14, range-fade} × threshold {moderate,
extreme} × exit {mean-touch, half-life time-stop}. **284 unconditional cells** + **60 regime-conditional
cells** = **~344 trials.** Raw table: `mr_deepdive_grid.csv`; half-lives: `mr_deepdive_halflife.csv`.

---

## 2. Unconditional grid — 284 cells

| filter | count |
|---|---:|
| total cells (N_trials) | 284 |
| net mean > 0 | **2** |
| two-sided (long-leg > 0 **and** short-leg > 0) | **0** |
| two-sided **and** net > 0 | **0** |

The two net-positive cells are both **NQ 15m EMA-fade θ2.5** (t=0.43): mean +1.6 bps but **long-leg
−4.3 / short-leg +10.2** — a one-sided *short* (fade NQ rallies), not symmetric MR. Every other
net-positive leg across the grid is the **long** side in up-regimes (beta). **No symmetric MR anywhere
unconditionally.**

---

## 3. Regime conditioning — the steelman ("where MR lives")

Re-ran SMA20-z and VWAP-dev (15m, θ2.0, mean-touch) split by **vol tercile**, **time-of-day**, and
**variance-ratio (range vs trend)**. This surfaced the *only* two-sided-positive cells in the study —
**4 of 60** — then put them through the full battery:

| candidate | n | mean (bps) | t | **1-bar delay** | long / short | by-year | battery verdict |
|---|---:|---:|---:|---:|---:|---|---|
| US100 high-vol · VWAP-dev | 213 | +5.62 | 1.43 | +6.16 ✓ | +2.8 / +9.8 | 4/6, **+12 in 2022** dominates | ❌ t<2.94; 2022-concentrated; ~35 tr/yr |
| US100 high-vol · SMA-z | 189 | +5.46 | 1.32 | +4.74 ✓ | +3.6 / +8.3 | 4/6, 2022-driven | ❌ t<2.94; thin frequency |
| **EURUSD midday · SMA-z** | 726 | +1.25 | 1.44 | +1.25 ✓ | +1.2 / +1.3 | **6/7** | ❌ knife-edge; OOS-train t=0.54; too thin |
| US30 high-vol · SMA-z | 268 | +1.73 | 0.63 | **−1.03 ✗** | +0.4 / +3.6 | 5/7, 2020-driven | ❌ **collapses under delay** |

**Multiple-testing bar:** with N≈350 trials, the expected **maximum |t| by pure chance ≈ 2.94**. The best
observed is **1.44**. (Trials are correlated — adjacent thresholds/anchors overlap — so the *effective*
bar is lower; but even at a conservative effective N≈20–30 the chance-max |t| is ≈2.2–2.4, still well
above the observed 1.44.) Nothing clears it.

### The one near-candidate, characterized to exhaustion — EURUSD midday
The most real-looking cell (symmetric legs, survives delay, 6/7 yrs positive) fails every robustness axis:

- **Threshold knife-edge:** θ1.5 → +0.12 (t 0.21); **θ2.0 → +1.25 (t 1.44)**; θ2.5 → −0.98. A real edge is not a single-point spike.
- **Window knife-edge:** 10–13h → +0.15; **11–14h → +1.25**; 12–15h → +0.97; full 9–17h → −0.12. Shift the window an hour and it's gone.
- **OOS-unstable:** train 2020–23 **t = 0.54** (≈ nothing); the effect lives only in 2024–26 (t 2.06). You would not have "found" it on the train period.
- **Feasibility kill:** ~104 trades/yr × 1.25 bps = **+1.3 %/yr** gross at 1×. Reaching FTMO +10 % needs ~8× leverage → the 5 % daily DD breaches long before the target. (US100 high-vol is worse: high-vol is rare → ~35 trades/yr → ~0.2 %/yr.)

A per-trade edge is worthless if its frequency can't compound to the target inside the DD box. Even
granting the EURUSD-midday effect is real, it is **economically too thin for FTMO**.

---

## 4. Full battery on survivors

**No cell qualified as a survivor** (none two-sided AND delay-robust AND threshold/window-robust AND
DSR-surviving), so walk-forward / block-bootstrap p(pass) / reconciliation were correctly **not** spent.
The discipline did its job: it caught the one delay-artifact (US30), demoted the two regime-concentrated
high-vol cells, and exposed the one symmetric cell (EURUSD-midday) as a knife-edge that fails OOS and
feasibility.

---

## 5. Verdict

**Is there a two-sided, delay-robust, cost-surviving, DSR-surviving intraday MR variant on FTMO
instruments? — No, after genuine depth (~350 trials).** And now this is a *family-level* statement
earned by systematic exploration, not an over-generalization from one setting:

1. **Unconditionally, MR is not even one-sided-positive** on these instruments (2/284 cells, t≈0.4) and
   **never two-sided**. NQ/US-tech *trend* intraday; fading loses or is a one-sided short.
2. **Conditioning helps but does not rescue it.** High-vol and midday windows produce weak two-sided
   blips (t≤1.44) that are **regime-concentrated, knife-edge, OOS-unstable**, and **fail DSR** on the
   total search space.
3. **Even the best blip is economically infeasible** for FTMO (+0.2 to +1.3 %/yr) — too thin to reach
   +10 %/+5 % without DD-violating leverage.
4. The recurring failure is **the two-sided test** — the same signature as the whole arc: a "reverting"
   leg that is really the period's directional drift. MR doesn't escape it.

**Constructive read:**
- **Holding-to-half-life mattered methodologically** (v1 exited too early) but did not manufacture EV —
  confirming the v1 "no" wasn't merely a bad-exit artifact; the family is genuinely empty here.
- **If MR lives anywhere for retail, it's in high-vol overreaction reversion** (the US100 high-vol cell
  was the strongest signal) — but it's too **infrequent** to be an FTMO vehicle and too weak to clear DSR.
  A market-maker / sub-bp-cost venue is the only place that thin, frequent edge becomes tradable (cf.
  `STRATEGY_RESEARCH_LOG.md` residual-MR lesson — same conclusion, different market).
- **Next deep-dives (same protocol, one family at a time):** breakout beyond ORB-30min (logics × TF ×
  exits × filters), then high-hit-rate intraday momentum with the two-sided test up front. The
  machinery (`mr_deepdive.py`: half-life, non-overlap engine, regime masks, delay column, DSR bar) is
  reusable as-is.

**Bottom line:** the depth pass upholds the breadth pass — but now legitimately, at the family level.
There is no retail-accessible two-sided intraday MR alpha on liquid FTMO majors. The honest "no" is
earned, and the protocol that earned it (and that would *recognize* a real edge if one appeared) is in place.

---

### Artifacts
- `code/mr_deepdive.py` — half-life estimation, anchors (SMA/EMA/VWAP/RSI/range), vectorized non-overlap
  fade engine, regime masks, the grid runner.
- `mr_deepdive_grid.csv` (284 unconditional cells), `mr_deepdive_halflife.csv`.
- Builds on `mr_intraday_screen.py` (the non-overlap + delay validator) and `ALPHA_hunt_ftmo.md` (breadth).
