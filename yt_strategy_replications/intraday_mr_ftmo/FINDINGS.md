# FINDINGS — Intraday mean-reversion, FTMO-targeted (feasibility study)
**Date:** 2026-06-20 · **Pre-registration:** `PREREGISTRATION.md` (frozen before any result).
**Mandate:** test the family ranked #1 by `ftmo_profile_study/STUDY_FTMO_COMPATIBLE_PROFILE_2026-06-20.md`
(fast intraday MR, hard-stopped) on the asset classes the `nonovernight_search_findings.md` redirect named
(equity indices / FX). **Author≠auditor:** the negative was re-verified by an independent from-scratch event study.
**Isolation:** additive new folder, **zero git HEAD operations** (shared working dir); live book untouched; nothing deployed.

## 0. Verdict — FALSIFIED (a clean, useful negative)
The price-only intraday mean-reversion family does **not** produce a net-tradable, two-sided edge on
US100 / US500 / US30 / GER40 + EURUSD / GBPUSD / USDJPY at 15-min frequency, across the entire pre-registered
grid and a second MR mechanism (gap fade). It fails **gate 1 (gross two-sided, HAC-t>2.5)** before costs and
**gate 4 (net Sharpe>1 / DSR>0.5)** by a wide margin. The only positive sleeve — the long-leg of up-drifting
indices (US500 long gross SR +0.58, DSR 0.63) — is the textbook **L25 beta trap**: its short leg is −0.87 and
its conditional edge (~1.6 bps) is *smaller than* the unconditional index drift (~1.5–2.2 bps), so it does not
even beat buy-and-hold. Independently confirmed: no sign error, no look-ahead, no cost mistake is hiding an edge.

This is the result the pre-registration anticipated (HMR-3 "expected to fail on FX"); the addition is that it
also fails **gross and two-sided on indices**, not merely on cost. **§4 is necessary, not sufficient** — exactly
the caveat stated when the profile was commissioned: the profile says *what type* to look for; it does not
manufacture an edge that the market does not contain.

## 1. Results — primary config (k=20, z0=2.0, sl=tp=1.0×ATR, H=8), vol-targeted
Per-instrument, gross (cost 0) and net (round-trip = one spread). HAC Newey-West lag-6 t on daily realized P&L.

| sym | n_trades | WR | bars_held | gross both SR / t | **long-only** SR / t | **short-only** SR / t | net@2-3bps SR |
|---|--:|--:|--:|--:|--:|--:|--:|
| US100 | 5,665 | .49 | 3.1 | −0.40 / −1.52 | −0.25 / −0.91 | −0.32 / −1.25 | −2.23 |
| US500 | 5,769 | .49 | 3.0 | −0.22 / −0.87 | **+0.58 / +2.20** (DSR .63) | **−0.87 / −3.46** | −2.61 |
| US30 | 5,230 | .49 | 3.0 | −0.38 / −1.35 | +0.34 / +1.22 | −0.88 / −3.17 | −2.76 |
| GER40 | 6,374 | .50 | 2.6 | +0.04 / +0.12 | +0.17 / +0.59 | −0.12 / −0.41 | −2.63 |
| EURUSD | 10,356 | .50 | 3.1 | −0.16 / −0.74 | −0.18 / −0.80 | −0.04 / −0.17 | −6.21 |
| GBPUSD | 10,448 | .50 | 3.1 | −0.29 / −1.30 | −0.16 / −0.70 | −0.25 / −1.15 | −6.22 |
| USDJPY | 10,816 | .49 | 3.0 | −0.61 / −2.81 | −0.42 / −1.91 | −0.43 / −1.98 | −7.09 |

**Pooled books (equal-risk, vol-targeted):** index gross SR −0.34 (t −1.34), net −3.53; FX gross SR −0.54
(t −2.45, *significantly negative*), net −9.84. Win rate ≈ 0.49 and frac_sl ≈ frac_tp ≈ 0.47 everywhere — a
near-coin-flip 1:1 barrier whose only mover is the unconditional long bias.

## 2. Robustness — the negative survives the whole DoF budget
- **Grid z0∈{1.5,2,2.5} × H∈{4,8,12} (9 configs, index book):** gross both SR ∈ [−0.49, −0.04], **none positive**;
  net@2bps SR ∈ [−5.0, −2.5]. Tightening z0 to 2.5 only approaches break-even gross, never an edge.
- **Momentum flip (trade WITH the z-move):** also gross-negative (SR −0.08 to −0.59). So the extreme-z bars carry
  **no exploitable directional autocorrelation** — it is not "wrong sign," it is *no sign*. Reversion and
  continuation both lose; only beta pays.
- **S2 gap-fade (indices, independent MR mechanism):** pooled gross SR −0.50 (t −1.94), net −1.46. Dead too.

## 3. Independent audit (author≠auditor) — negative CONFIRMED
A from-scratch event study (no reuse of the study code) measured forward returns after |z|≥2:

| | z≤−2 long (need +) | z≥+2 short (need −) | two-sided combined | unconditional |
|---|--:|--:|--:|--:|
| US100 | +1.61 bps (t +1.07) | **+0.09 (t +0.07)** | +0.72 (t 0.78) | +2.22 (t **4.49**) |
| US500 | +1.58 (t +1.36) | **+0.79 (t +0.91)** | +0.36 (t 0.51) | +1.50 (t **3.91**) |
| EURUSD | +0.36 (t +0.86) | −0.22 (t −0.52) | +0.29 (t 1.00) | −0.07 (t −0.53) |

Auditor's checks: sign convention correct (100% of z≤−2 rows have close<SMA), look-ahead impossible (verified on a
synthetic series), event counts 5k–12k/leg. Horizon sweep H∈{1,2,4,8,16,24}: the two-sided signal **never** reaches
|t|≥2.5 (best EURUSD H=2, t 2.08, gross +0.21 bps < ~0.3 bps spread → net-dead). The short-leg is the tell: on
indices it is *positive* (continuation), and the long-leg "edge" is below the unconditional drift → **beta, not alpha**.

## 4. §4 FTMO-compatibility scorecard
The family was chosen because it fits the §4 *structural* axes by construction — and it does:

| §4 axis | required | this family | note |
|---|---|---|---|
| short-hold / intraday-m | ≤1.5 | ✓ (3 bars, hard ATR stop) | structurally fine |
| intermittent / presence | ≤0.4 | ✓ (only \|z\|≥2 events) | structurally fine |
| deleverageable vol | ≤8% funded | ✓ (vol-targeted) | structurally fine |
| two-sided ⇒ tail-decorr | ρ_tail ≤0.3 | ✓ by design | structurally fine |
| **per-active-day EDGE** | **SR ≥1.5** | **✗ — there is no edge** | **the prerequisite fails** |

**Conclusion:** the candidate satisfies every §4 *shape* axis but fails the one that cannot be engineered — a real,
two-sided, net-positive edge. The §4 filter worked as designed (it told us precisely what to build and the audit
confirms the construction is clean); the market simply does not contain a price-only intraday MR edge here.

## 5. Implications & redirect
1. **Generalises L43 / `nonovernight_search_findings` to equity indices.** Retail intraday-flat price-only signals
   were already shown cost-dead on FX and on trend commodities; this extends it to US/DE equity-index CFDs. The
   binding facts are (a) ~5k–11k trades/yr → cost bleed dominates (L33b: need >3 bps gross/trade; best observed
   ~0.2 bps), and (b) 15-min extreme-z bars have ~zero exploitable autocorrelation.
2. **The L25 two-sided test is the cheap decisive falsifier — again.** A naïve long-only "MR" would have shown
   SR +0.58 / DSR 0.63 and been promoted; the short-leg requirement killed it in one line. Keep it mandatory.
3. **Next per the §4 ranking:** rank-1 (price-only intraday MR) is exhausted on free OHLC. Rank-2 —
   **concentrated, defined-risk scheduled-event** — requires a *different data axis* (an economic-event calendar:
   CPI/FOMC/NFP/earnings), not more price-only mining. That is the next feasibility study worth commissioning.
   Alternatively, MR may live only sub-15-min (where autocorrelation can turn negative) but the cost gate worsens
   there — likely a lower-cost-venue / execution problem, not a retail-CFD one.

**Lesson candidate (NAMED, to engrave at reconciliation):**
`price-only-intraday-MR-is-autocorr-and-cost-dead-on-equity-indices-too` — fading extreme 15-min z-moves on
US100/US500/US30/GER40 + EUR/GBP/JPY is gross-negative two-sided across z0∈{1.5,2,2.5}×H∈{4,8,12}, momentum-flip
also negative (no exploitable sign), gap-fade dead; the only positive sleeve is the L25 long-only beta trap.
Generalises L43 from FX to equity-index CFDs. (Family: L25/L33b/L43.)

## 6. Reproduce & ledger
```
cd yt_strategy_replications/intraday_mr_ftmo
/usr/bin/python3 dataload.py            # build 15-min session caches (_cache/, gitignored)
/usr/bin/python3 run_primary.py         # per-instrument gross/net + two-sided + pooled -> results_primary.json
/usr/bin/python3 run_robustness.py      # grid + momentum-flip + gap-fade
```
`n_tests` added by this study ≈ **13** (9 grid + gap + momentum + 2 per-leg), all FAIL — increment the global ledger.

## 7. Isolation & handoff (no git ops were performed here)
This session ran in the **shared** main working dir, which already held uncommitted work from other session(s),
so **no `checkout`/`branch`/`commit`** was run (a HEAD move would corrupt a parallel session — the 2026-06-19
incident). To commit this additive folder cleanly, from a terminal with full Desktop access:
```
cd <HOME>/Desktop/Algo_claude
git fetch origin
git worktree add ../Algo_claude_mr -b claude/intraday_mr_ftmo origin/main
cd ../Algo_claude_mr
cp -R "<HOME>/Desktop/Algo_claude/yt_strategy_replications/intraday_mr_ftmo" \
      yt_strategy_replications/                     # if not already on this branch's tree
git add yt_strategy_replications/intraday_mr_ftmo
git commit -m "intraday MR FTMO feasibility: FALSIFIED (not two-sided, cost-dead); §4 necessary-not-sufficient"
# open PR from claude/intraday_mr_ftmo ; then: git worktree remove ../Algo_claude_mr
```
Run `python3 tools/check_register_integrity.py` in the **main** dir (not a worktree) before the closing commit.
