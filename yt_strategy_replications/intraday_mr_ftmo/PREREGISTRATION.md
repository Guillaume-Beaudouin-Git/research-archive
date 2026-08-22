# PRE-REGISTRATION (FROZEN before results) — Intraday mean-reversion, FTMO-targeted
**Date frozen:** 2026-06-20 · **Author:** research session · **Auditor:** separate subagent (post-hoc).
**Mandate:** the FTMO-compatible-profile study (`ftmo_profile_study/STUDY_FTMO_COMPATIBLE_PROFILE_2026-06-20.md`)
ranked **fast intraday mean-reversion, hard-stopped** as the #1 family to fit both FTMO stages, to be
searched on **equity indices / FX** (the `nonovernight_search_findings.md` redirect: the Gao/overreaction
mechanisms live on indices, not the trend commodities). This study tests that family.

> Frozen prior to running any backtest. Universe, signal definitions, parameter grids, costs, gates and
> directional hypotheses below are fixed. Results live in separate files. No strategy is deployed; the live
> book is read-only; no git HEAD operations (shared working dir).

## 1. Why MR and not momentum (mechanism)
Equity-index intraday literature carries TWO effects: Gao (2018) intraday *momentum* (first-30 → last-30)
and short-horizon *reversal* / overreaction (Lehmann 1990; Lo-MacKinlay 1990, intraday analogue). For FTMO
§4 fit we need **short holds + hard stops + intermittence** — that is the *reversal* family (momentum needs to
let winners run → long holds → high intraday excursion m, which the funded daily barrier punishes). We test
reversal of an *extreme* intraday move, two-sided, hard-stopped, intraday-flat (swap-free → carry-immune, L36).

## 2. Universe (liquid, FTMO-tradable, true-UTC deep_history)
- **Indices (primary):** US100 (NQ), US500 (ES), US30 (Dow), GER40 (DAX) — 2013→2026-06, M1.
- **FX (contrast, expected weaker per L43):** EURUSD, GBPUSD, USDJPY — 2007→2026-06, M1.
Per-instrument time-series tests, pooled equal-risk into a book; per-instrument also reported.
This is NOT a cross-sectional ranker → the N≥30 rule does not apply (it targets XS small-universe AMTP).

## 3. Signal — PRIMARY S1: intraday extreme-move z-reversal (two-sided, hard-stopped)
Bars: **15-min**, restricted to each instrument's **liquid session** (indices: 13:30–20:00 UTC cash RTH;
FX: 07:00–16:00 UTC London/NY overlap). Computed causally; execution lag handled by the engine
(signal at close t → enter open t+1).
- `z_t = (close_t − SMA_k(close)) / STD_k(close)` over the trailing **k=20** session bars.
- **Entry:** `z_t ≤ −z0` → **long** (fade the down-move); `z_t ≥ +z0` → **short** (fade the up-move); else flat.
  Trading only the extremes makes it **intermittent** (low presence, §4 axis 3).
- **Exit:** intrabar, pessimistic stop-first tie-break (engine default):
  - hard **stop** `sl = s_sl × ATR_k` (the §4/L25 hard stop),
  - **target** `tp = s_tp × ATR_k` (reversion to mean),
  - **time-stop** at `H` bars OR forced flat at session end (intraday-flat ⇒ swap-free).
  To guarantee intraday-flat, the signal is set to 0 in the last `H` bars of each session (no entry can
  cross the close).
- **Frozen primary parameters (a priori, not optimised):** `k=20`, `z0=2.0`, `s_sl=1.0`, `s_tp=1.0`
  (symmetric 1:1 — MR does not need an asymmetric payoff), `H=8` bars (2h cap).
- **Pre-declared robustness grid (reported, DSR-penalised, NOT for selection):**
  `z0 ∈ {1.5, 2.0, 2.5}` × `H ∈ {4, 8, 12}` = 9 configs. `s_sl=s_tp` held at 1.0. This is the entire
  researcher degrees-of-freedom budget (CLAUDE.md: ≤3 modification axes; here 2: z0, H).

## 4. Signal — SECONDARY S2: overnight/weekend gap fade (indices only, robustness)
At the first RTH bar, if the open-vs-prior-RTH-close gap `|g| ≥ g0·σ_daily` (g0=1.0), trade against it
(gap up → short, gap down → long), same hard-stop/time-stop/intraday-flat machinery. One config only
(g0=1.0, s_sl=s_tp=1.0, H=session-end). Reported as an independent MR cross-check, not optimised.

## 5. Costs (round-trip, as fraction of notional)
RT cost = one full quoted bid-ask spread (buy ask on entry, sell bid on exit). **Measured** per instrument
from the deep_history `spread` column (median during session), and **stressed** at conservative floors
because the calibrated spread is raw-tight vs FTMO retail:
- report net at `cost_rt ∈ {measured, 2 bps, 3 bps}` for indices; `{measured, 3 bps, 5 bps}` for FX.
- L33b gate: an intraday-flat signal needs **gross/trade > 3 bps** to survive a 3 bps RT.
No swap (intraday-flat). No overnight RF adjustment needed (flat at day boundaries; intraday RF ≈ 0).

## 6. Position sizing — daily vol targeting (CLAUDE.md mandatory)
Per-trade notional scaled by `min(target_vol / realized_vol_{t-1}, cap=3)`, realized vol = rolling 20-session-bar
std annualised, **shifted 1 bar** (causal). Headline decision series = daily realized P&L on this vol-targeted
notional. Vol target set so the *pooled book* runs at the analysis vol; the §4 mapping then asks at what vol
the edge still survives (deleverageability).

## 7. Gates (pre-registered thresholds)
1. **Gross feasibility (IC):** pooled HAC lag-6 t-stat **> 2.5** on daily realized returns.
2. **Two-sided (L25, decisive):** long-leg AND short-leg HAC-t **both > 0** (ideally both > 1.65). A one-sided
   "MR" is drift/beta in disguise → reject the MR claim.
3. **Mechanism contrast (L44):** edge stronger in high-realized-vol tercile than low (pre-registered split).
4. **Net performance:** at the *measured* cost, pooled **Sharpe > 1.0** AND **DSR > 0.5** (`n_trials` = total
   configs × instruments run in the study).
5. **Walk-forward:** ≥5 folds, **WF score > 50%** (fraction of folds with positive Sharpe).
6. **Robustness:** net Sharpe > 0 across the 9-config grid majority; survives the 3 bps cost stress (indices).
7. **§4 FTMO mapping (the point):** estimate the candidate's (vol-deleverageability, presence, intraday-m
   proxy = avg adverse excursion / σ, two-sidedness ⇒ tail-decorrelation prior). Compatible only if it can
   run ≤8% vol, presence ≤0.4, m ≤1.5, with hard stops bounding cum-DD ≤8%.

## 8. Pre-registered directional hypotheses
- **HMR-1:** S1 is two-sided positive **gross** on indices (both legs HAC-t > 1.65, pooled t > 2.5).
- **HMR-2:** the edge concentrates in the high-vol regime and near the cash open (L44 contrast > 0).
- **HMR-3 (the live question):** net of the *measured* index CFD spread, S1 clears Sharpe > 1 AND DSR > 0.5
  on the index book. Honest prior: **plausible on indices, expected to FAIL on FX** (L43 retail FX intraday-flat
  is cost-dead; L33b 3 bps floor).
- **HMR-4 (decisive):** IF an edge survives net, it maps onto the §4 profile (deleverageable, presence ≤0.4,
  m ≤1.5, two-sided ⇒ tail-decorrelated from the overnight-drift book) → first real FTMO-compatible candidate.
- **Falsification is a valid, useful outcome:** if S1 dies net (the likely L33b/L43 result), the deliverable
  states that the §4-recommended family is *also* cost-gated on free index/FX data at this frequency, and the
  search must move to (a) finer execution / lower-cost venue, or (b) the defined-risk event family (§4 rank 2).

## 9. What the deliverable states
Per-instrument and pooled tables (gross, net@measured, net@stress), the two-sided decomposition, the L44
contrast, WF folds, DSR, and the §4 scorecard with a clear PASS/FAIL verdict against the gates above.
No deployment; live book untouched; isolation = additive new folder, zero git HEAD ops.
