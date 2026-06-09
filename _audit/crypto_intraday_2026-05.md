# BTCUSD intraday — crypto focus (Family-6), relaxed thresholds

**Date:** 2026-05-31 · **Sprint:** crypto focus, relaxed gates · **Verdict: NO-GO under realistic crypto rules — but the program's FIRST real net-positive, hold-out-surviving edge**
**Code:** `PropFirms/ftmo_alpha_program/strategy/intraday_fx_mr.py` (reused) + `run_crypto.py`
**Data:** MT5 1-min BTCUSD panel, 2020–2026 (the only crypto CFD in the repo). **Protocol:** IS 2022-2024; verdict on the **untouched hold-out 2025-2026**; thresholds relaxed (per request) but integrity gates kept; result **independently verified** by a second agent.

---

## Prior and direction (recon picked it from data)

Crypto is less efficient than FX/index (retail, herding) with large intraday moves that might
overcome a wide CFD spread. Recon: BTC **levels TREND intraday** — the level-fade loses gross
(annSh −0.82 IS); the edge is **MOMENTUM** (follow the breakout). Swaps catastrophic → intraday-flat
(flatten before the daily rollover). Candidate: BTCUSD momentum, 120-min bars, window 16, z_entry 2.0,
hours 00–21 UTC, hard daily-stop 2%, CFD spread ×3. Selected on IS cost-ratio, confirmed OOS.

## What is real (verified, stands)

| | gross (zero cost) | net (×3 spread) |
|---|---|---|
| IS 2022-2024 | annSharpe 1.33 | 0.79 |
| **Hold-out 2025-2026 (untouched)** | **0.80** | **0.59** |

Per-trade t = 2.14; per-year net Sharpe 4/5 positive. **This is the program's first robust,
net-positive edge that survives the untouched hold-out at the Sharpe level** — reproduced exactly and
confirmed look-ahead-free by independent verification (`pos = pos_state.shift(1)`, causal daily-stop;
sign/return placebos collapse gross to ≤0). BTC's CFD spread also collapsed from ~$12 RT (2022-24) to
~$1 (2025-26), so cost is not the binding constraint.

## Why it is still NO-GO for FTMO crypto (two corrections + a regime risk)

The first read suggested P(pass) > 70%. Independent verification corrected it on two counts:

1. **The 70–83% was in-sample.** Read on the **hold-out** (per protocol), combined P(pass) at σd 0.6%
   is only **47%** (Standard 5% floor). The in-sample figure does not transfer.
2. **The crypto daily-loss floor is decisive.** FTMO applies a *reduced* daily limit to crypto. The
   hold-out P(pass) by floor (σd 0.6%): **5% → 47% · 3% → 47% · 2% → 26%**; at σd 1% the collapse is
   sharper (verifier: 3% → 40%, 2% → 7%). This lumpy book's losing days cluster at −2…−4%, so a
   reduced floor breaches them.
3. **Long-bull-biased.** 2022 (BTC bear): net annSharpe −0.24 and **max drawdown 10.9% > the 10% FTMO
   floor → would have breached.** The IS Sharpe is carried by the 2024/2026 up-trends.

Distribution (the root cause): WR ~25%, win/loss ~2.2, **excess kurtosis ~10** — the lumpy,
positive-skew momentum profile. DSR = 0.007 (fails: not robust to multiple-testing + non-normality;
the hold-out survival is the honest counter-evidence — a real tension).

## A real mechanism nuance (worth keeping) — but insufficient

Against a **static** symmetric barrier with **no time limit**, positive-skew momentum (small losses,
big wins) does better than a Gaussian of the same Sharpe (IS empirical 83% vs Gaussian 74%): the fat
**right** tail reaches +target while the thin small losses rarely breach a 5% floor. So it is the
**sign of skew**, not lumpiness alone, that governs barrier fit — a genuine refinement of the *mechanism*.
But it is not enough: on the hold-out, under the reduced crypto floor, and against bear-regime risk,
the edge does not clear the barrier. **Net: this CORROBORATES L24** — lumpy momentum is not a reliable
symmetric-barrier passer — rather than overturning it.

## Verdict

**NO-GO for the FTMO crypto challenge** under realistic (reduced-daily-floor) rules and bear-regime
risk. **But the genuine finding is positive and new:** crypto intraday momentum is the first real,
net-positive, hold-out-surviving edge the program has produced. It is the wrong *distribution/venue*
for a symmetric propfirm barrier, not a non-edge. Its natural home is a directional book without a
symmetric daily-loss barrier (e.g. the personal crypto book alongside Strategy A), not FTMO. The
"promising" first read was an in-sample + too-loose-floor artifact — caught by the discipline of
verifying a positive result on untouched data before believing it.

## Robustness — Donchian breakout (a structurally-distinct momentum formulation)

Tested a classic N-bar Donchian channel breakout (trigger = an actual prior-range break, not a
sigma-extension) with a tight ATR per-trade stop, explicitly to attack the variable that killed the
z-score momentum: can a tight stop keep losing days inside the reduced crypto floor? **Hypothesis
falsified, verdict confirmed.** Code: `strategy/btc_breakout.py`. Best IS config (120-min, channel 24):

- Real net-positive edge that survives the hold-out: gross IS 1.23 -> OOS 0.67; net IS 0.78 -> OOS 0.49.
- Even MORE lumpy than the z-score momentum: WR ~18-35%, kurtosis ~12, worst single day -3.2% (OOS) /
  -4.8% (IS) -- a tight stop does NOT bound the daily loss below a 2-3% reduced floor (multiple
  breakout legs + gap-throughs stack within a day).
- Hold-out FTMO P(pass) at sigma_d 0.6%: 42% (5% & 3% floor) -> 16% (2% floor).
- 2022 bear: net annSharpe -0.67, max drawdown 15.0% > 10% floor -> would have breached (worse than the
  z-score momentum's 11%).

Two independent momentum formulations (sigma-extension banded; Donchian level break) reach the
identical verdict: a real, hold-out-surviving, net-positive crypto edge that is the wrong distribution
for a symmetric barrier and breaches the reduced crypto daily floor. Further momentum variants would be
p-hacking at the variant level -- the wall is structural, not a tuning artefact.
