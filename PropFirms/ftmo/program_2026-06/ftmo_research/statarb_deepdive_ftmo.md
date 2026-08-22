# Stat-arb / pairs — FTMO deep-dive (the two-sided-by-construction family)

**Why this family, now:** every prior FTMO failure (ORB, breakout, MR, momentum, carry) died the
same way — the **two-sided test** exposed a one-sided **long-beta in disguise**. Stat-arb is the one
family **market-neutral by construction** (long A / short B → beta cancels), so beta-in-disguise
*cannot* be the killer. It is the family where "there is an alpha" had its **best structural shot**.
Prior stat-arb tests (equity Gatev/cointegration, AUD/NZD) were shallow; this is the depth pass on the
FTMO universe.

**Honest prior:** modest, but for *different* reasons than beta — the stat-arb killers are (a) 2-leg
cost + rebalancing, (b) spread half-life (equity pairs >30d = too slow for FTMO), (c) **OOS
cointegration breakdown** (relations break — the classic killer), (d) short-CFD financing on multi-day
holds (the overnight trap returning).

---

## Verdict up front

> **Stat-arb on FTMO instruments is closed too — and the two-sided-by-construction family fails for its own specific reasons, plus one it shouldn't have.** Across **18 pairs** (indices, FX majors/crosses, gold) and **48 pair×param trials**, there is **no pair with OOS-stable cointegration AND a tradeable half-life AND a net-positive edge after 2-leg cost + financing AND DSR survival.** Best t among net-positive cells = **+1.18** vs a multiple-testing bar ≈ **2.78**.
>
> Four structural killers, each measured:
> 1. **Half-life is multi-week everywhere.** Every pair spread reverts over **22–180 days** (fastest: AUDUSD/NZDUSD 22d). None is intraday-tradeable → holds are forced multi-day → financing applies.
> 2. **OOS cointegration breaks** (the classic killer): of 6 pairs cointegrated in-sample, only **2 survive OOS** — both index pairs. **Every FX pair breaks OOS** (EURUSD/GBPUSD p_oos 0.26, AUDUSD/NZDUSD 0.10).
> 3. **Financing kills the index pairs** (the only OOS-stable ones): ~14-day holds × **1.5 bps/night** ≈ 21 bps financing + 4 bps 2-leg cost ≈ **25 bps**, vs gross spread reversion of only **8–31 bps** → net ≈ 0/negative.
> 4. **The spread is not even two-sided.** Legs are wildly asymmetric (US100/US30: long-spread +79 / short-spread −61 bps) — the spread carries a **relative drift** (NDX structurally out-performed DJI). **Market-neutral-by-construction does NOT imply two-sided-in-spread** — the spread inherits a directional drift. This is the stat-arb analogue of the beta trap, and it appears even here.
>
> The family with the best a-priori shot at a surviving two-sided alpha **also has none** that is tradeable on FTMO.

A clean structural note: a **market-neutral CFD pair pays 2× the broker markup** in financing (the
benchmark rate cancels between the long and short legs) ≈ **5.5 %/yr ≈ 1.5 bps/night — in every rate
era**. Unlike the single-leg overnight harvester (rate-dependent), pair financing is a *structural*
drag, fatal to any spread that takes weeks to revert.

---

## 1. Method

1H aligned closes, 15 instruments, real per-instrument costs from the MT5 `spread` column (FX majors
**0.9–1.2 bps RT/leg**, indices 1.5, gold 2.0). For each pair: Engle-Granger hedge ratio + ADF
cointegration p (full **and** OOS — β fit on first half, ADF on second half), **OU half-life** of the
spread, then a z-score spread-MR backtest — rolling hedge ratio (no look-ahead), entry |z|>z_in, exit
|z|<z_out, **non-overlapping**, P&L on the **fixed-at-entry** hedge ratio, minus **2-leg cost** and
**overnight financing × nights held**, with **long-spread / short-spread legs reported separately**.
N_trials tracked for DSR. Artifacts: `statarb_coint_screen.csv`, `statarb_grid.csv`,
`code/statarb_deepdive.py`.

---

## 2. Cointegration + half-life + OOS stability (18 pairs)

| pair | ret corr | EG p (full) | **EG p (OOS)** | **half-life** | read |
|---|---:|---:|---:|---:|---|
| US500/US30 | 0.89 | 0.003 ✓ | **0.043 ✓** | 24 d | OOS-stable, but slow |
| US100/US30 | 0.76 | 0.011 ✓ | **0.035 ✓** | 37 d | OOS-stable, but slow |
| US100/US500 | 0.93 | 0.019 ✓ | 0.43 ✗ | 39 d | breaks OOS |
| EURUSD/GBPUSD | 0.72 | 0.025 ✓ | 0.26 ✗ | 22 d | breaks OOS |
| AUDUSD/NZDUSD | 0.88 | 0.006 ✓ | 0.10 ✗ | 22 d | breaks OOS |
| USDJPY/AUDJPY | 0.53 | 0.003 ✓ | 0.22 ✗ | 23 d | breaks OOS |
| USDCAD/USDCHF, EURUSD/USDCHF, USDJPY/EURJPY, XAU/AUD, GER40/EUR, … (12 more) | — | >0.05 ✗ | ✗ | 40–180 d | not cointegrated |

**Only 2 of 18 pairs are cointegrated OOS — both index pairs — and both have ~24–37-day half-lives.**
Every FX pair that looks cointegrated in-sample **breaks out of sample**: the documented classic
stat-arb failure mode, confirmed on the FTMO FX universe.

---

## 3. Spread-MR backtest with real 2-leg cost + financing

z_in=2.0, z_out=0.5, rolling β (lookback 500h), rolling z-window 300h:

| pair | n | avg hold (days) | gross (bps) | cost+fin (bps) | **NET (bps)** | t | long-spr / short-spr | two-sided? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| US500/US30 | 77 | 14.6 | +13.0 | 24.8 | **−11.8** | −0.68 | +9.4 / −33.6 | no |
| US100/US30 | 77 | 14.5 | +31.1 | 24.7 | **+6.3** | +0.16 | +78.7 / −60.6 | no |
| US100/US500 | 75 | 14.8 | +7.6 | 25.6 | **−18.0** | −0.79 | +0.3 / −39.9 | no |
| AUDUSD/NZDUSD | 56 | 13.1 | +6.2 | 9.1 | **−2.9** | −0.25 | −12.4 / +6.0 | no |
| EURUSD/GBPUSD | 63 | 10.6 | +6.6 | 7.1 | **−0.5** | −0.04 | −8.2 / +5.0 | no |
| USDJPY/AUDJPY | 51 | 11.6 | −12.9 | 7.7 | **−20.6** | −0.87 | +2.2 / −46.2 | no |

- **Index pairs: financing-killed.** Gross reversion (8–31 bps) ≈ the cost+financing (~25 bps, ~85 % of which is overnight financing over the ~14-day hold). Net ≈ 0/negative.
- **FX pairs: cost-killed.** Gross reversion (6–7 bps) ≈ the 2-leg cost (7–9 bps). Net ≈ 0 — and they aren't OOS-cointegrated anyway.
- **None two-sided.** The long-spread and short-spread legs are never both positive; the spread inherits a relative drift.

### z-threshold sweep (DSR denominator) — 48 trials
| metric | value |
|---|---|
| N_trials (6 pairs × 4 z_in × 2 z_out) | **48** |
| cells NET > 0 | 8 / 24 (with ≥15 trades) |
| cells **two-sided AND NET > 0** | **1** (US100/US30, z_in=3.0 — n=28, t=0.95, ~5 trades/yr) |
| best t among NET>0 | **+1.18** |
| multiple-testing bar (expected max \|t\|, N≈48) | **≈ 2.78** |

The single two-sided-positive cell (US100/US30 at z>3) is **n=28, t=0.95, ≈5 trades/yr → ≈2.4 %/yr**
even taken at face value — too rare and too thin to clear FTMO +10 %/+5 %, and far below DSR.

---

## 4. Survivors → battery

**None.** No pair is simultaneously OOS-cointegrated **and** tradeable-half-life **and** net-positive
after cost+financing **and** two-sided **and** DSR-surviving. The two OOS-stable pairs are
financing-killed and one-sided; the net-positive FX cells aren't OOS-cointegrated and aren't two-sided.
Walk-forward / p(pass) were correctly not spent.

---

## 5. Verdict

**Does a stable-OOS, tradeable-half-life, cost-and-financing-surviving, DSR-surviving FTMO pair exist? —
No.** And this closes the family that had the **best structural chance**:

1. **The half-life wall.** Every FTMO pair spread reverts over **weeks**, not hours. There is no
   intraday-tradeable cointegrated pair in the liquid FTMO universe → holds are unavoidably multi-day →
   financing always applies. (This is the equity-pairs problem, reproduced on indices and FX.)
2. **OOS breakdown** removes every FX pair (only index pairs survive OOS).
3. **Structural financing** (2× markup ≈ 1.5 bps/night, rate-independent) kills the slow index-pair
   spreads — the small reversion can't out-run weeks of financing.
4. **The spread is not two-sided.** The deepest finding: *market-neutral by construction ≠ two-sided in
   spread*. The index spread carries NDX-vs-DJI relative drift; the FX spreads carry their own drift.
   Even here, the "edge" is a one-sided directional bet on the relative trend — the beta trap wearing a
   market-neutral costume.

**The arc's unifying lesson now generalises cleanly:** on liquid retail-accessible instruments, every
intraday/short-horizon family — directional *and* market-neutral — reduces to **one-sided directional
drift after honest costs**. The two-sided, all-regime, cost-surviving alpha is not there; what looks
like edge is always some drift (price, or relative price) that the two-sided/OOS test exposes.

**Where this leaves the FTMO goal (unchanged, now triangulated from three deep-dives + one breadth):**
- A genuine **+EV book run on the funded account** (the project's delta-neutral carry / TSMOM) remains
  the only credible vehicle — FTMO won't accept crypto, so it's a "what to run after funding" point.
- **Breadth (√N)** across many *independently* +EV sleeves, not a single per-trade edge.
- **Sub-bp execution** (market-maker tier) is where the thin, fast spread reversions become tradable —
  not retail FTMO.

**Honest both ways:** not a premature "dead," but a depth-earned one — on the family that, going in, was
the most likely to break the pattern. It didn't. Stat-arb FTMO is closed.

---

### Artifacts
- `code/statarb_deepdive.py` — 1H panel, EG cointegration + OOS, OU half-life, spread-MR backtest with 2-leg cost + financing.
- `statarb_coint_screen.csv` (18 pairs), `statarb_grid.csv` (48 trials). Costs cached from MT5 spreads.
- Series: `MR_deepdive_ftmo.md`, `ALPHA_hunt_ftmo.md`, `OVERNIGHT_drift_hardening.md`.
