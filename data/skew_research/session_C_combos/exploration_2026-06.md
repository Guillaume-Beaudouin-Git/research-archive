# Combination setups — session_C_combos (5 combos)
*2026-06, MEASURED. Decisive test: **does the combo beat the BEST of its naked bricks?** (prior: 0/5 — layering degrades). GATE-0 FTMO-tradeable basket, daily (OOM-safe). Nothing frozen/merged.*

## TL;DR — 0/5 robustly beat naked (confirms the prior)
**Naked bricks:** trend Sharpe **0.63** (best), MR Sharpe −0.26. The decisive test against 0.63:
- **#1 regime-switch (the thesis) FAILS** (0.29) — detector weakly separates, but the **MR brick is dead in both regimes**, so switching into it degrades. *Anti-correlation needs two LIVE bricks; MR isn't one.*
- **#2 double-timeframe FAILS** (0.53) — alignment just removes trades.
- **#3 RSI-dip KILL** — two-sided fired (long 0.03 / short −0.00 → no edge / long-beta).
- **#4 trend + relative-strength** marginally beats (0.67 vs 0.63) — but **+0.04 over 5 combos = noise, not significant**.
- **#5 BB rev + filter KILL** (Sharpe ~0).

## Detail

### #1 — Trend + MR regime-switched (the structurally-promising thesis)
**Detector-separation test FIRST** (lag-1 return autocorrelation, NOT the ER that failed before):

| | trend-regime | MR-regime |
|---|---:|---:|
| trend-strat daily | +5.63 bps | +4.05 bps |
| MR-strat daily | −2.02 bps | −1.60 bps |

The detector **weakly separates** (trend better in trend-regime; MR less-bad in MR-regime) — BUT **MR is NEGATIVE in both regimes** (no live MR edge anywhere). So the switch is into a dead brick: **regime-switched combo Sharpe 0.29 (skew +0.52) << naked trend 0.63 → FAILS the decisive test.** *The thesis fails not because regime detection is impossible (it weakly works), but because there is no live MR brick to switch into — anti-correlation at the strategy level requires two profitable bricks, and MR on these liquid instruments is dead.* (Note: the switch DOES improve skew, −0.41→+0.52, by sitting out trend's chop losses — but it sacrifices return, so it loses the beat-naked test.)

### #2 — Double-timeframe alignment (daily + weekly)
Combo Sharpe **0.53** (skew −0.42) vs naked trend **0.63** → **does NOT beat naked.** Requiring weekly agreement removes trades without improving the edge — textbook layering-degrades.

### #3 — RSI-dip filtered by LT trend (two-sided FIRST — the beta trap)
LONG-dip-in-uptrend Sharpe **0.03** (skew +4.89); SHORT-rip-in-downtrend Sharpe **−0.00** (skew 0.66). **Both ~0 → no edge; the long-only version would be pure beta. KILL** (the post-limit/MR-reversal trap, caught by the mandatory two-sided test). The huge long-side skew (+4.89) is rare-bounce convexity with no mean edge — a lottery, not a sleeve.

### #4 — Trend + relative-strength confirmation
Combo Sharpe **0.67** (skew −0.34) vs naked trend **0.63** → **marginally beats (+0.04).** But: one marginal beat out of 5 combos tried, +0.04 Sharpe is **within noise (DSR-deflated → not significant)**. Honest read: relative-strength confirmation adds a hair, **not a confident win**; treat as "no robust improvement over naked trend." (If anything it slightly improves skew, −0.41→−0.34.)

### #5 — Bollinger reversion + directional filter
Naked BB rev Sharpe −0.02; +trend-filter Sharpe **+0.04** → **no edge either way. KILL.** (Skew came out **+2.87** with the trend filter — *positive*, contradicting the prior batch's negative-flip, but moot since Sharpe ≈ 0.)

## Verdict
**0/5 combos robustly beat their best naked brick** — consistent with every prior batch: **layering/filtering degrades.** The single marginal "beat" (#4, +0.04) is multiple-testing noise. The structurally-best idea (#1 regime-switch = strategy-level anti-correlation) **fails for an instructive reason: there is no live MR brick to switch into** — the liquid-instrument MR is dead in both regimes, so the switch can only degrade naked trend.

**Lesson candidates (named, not numbered):**
- **"regime-switch can't manufacture anti-correlation from a dead brick"** — the trend+MR switch needs two LIVE bricks; MR is negative in both regimes, so switching into it degrades vs naked trend (the detector separating is necessary but not sufficient).
- **"layering degrades — 0/5 combos beat their best naked brick"** — confirmed again; the one +0.04 beat (#4) is noise.
- **"RSI-dip-in-uptrend = the long-beta / no-edge trap"** — two-sided test fires (long 0.03 / short −0.00); never skip it.
- **"a combo can improve skew while losing Sharpe"** — the regime-switch is more convex (+0.52 vs −0.41) but lower-return; for the profile objective it's tempting, but it still fails the beat-naked decisive test → not a brick.

*Reproduce: `combos_engine.py`. Daily, GATE-0-clean. Stayed in session_C_combos/; nothing frozen/merged.*
