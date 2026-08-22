# Dédale (carry+trend) + swap-sign rule — FTMO evaluation

**Mandate:** (A) backtest the friend's Dédale FX algo in our framework — only-positive-swap side,
trend-filtered, **real FTMO swaps**, OOS, max-DD vs the 10% floor, FTMO p(pass) — to answer "does it
beat the ~50% / ORB+floor incumbent today?" (B) adopt Dédale's smartest idea — the **swap-sign rule**
(never hold the negative-swap side overnight) — into our overnight harvester and swing-MR, and measure
the effect.

Dédale logic (from the .mq5): `if(swap_long<=0) no buy; if(swap_short<=0) no sell` → trade **only the
side that pays positive swap**, multi-TF TDI trend filter, pivot SL/TP at ~50% win-prob (RR≈1), held
overnight to collect carry. It is *trend-following carry trading*.

---

## Verdict

> **Dédale does NOT beat the incumbent today.** At real FTMO swaps (post-2024 decay), the 7-sleeve carry-trend portfolio is **flat — Sharpe −0.05, −0.1%/yr — and its FTMO 2-step p(pass) is 22–30%**, *below* random (33%) and well below ORB+floor (~46–50%). It is a **trend strategy with a now-tiny carry kicker**: on USDJPY, +22.1% of the +22.8% total is *price* (the JPY uptrend), only **+2.2% is swap over 7.4 years (~0.3%/yr)**. It worked in the 2022–24 carry regime (USDJPY long +24.5% pre-2024H2) and **decayed since** (post-2024H2 −1.7%) — exactly the alpha-decay the author documents himself.
>
> **The swap-sign rule is a genuine keeper — as cost discipline, not as an alpha source.** It cleanly explains why the overnight harvester is structurally dead on indices, and it modestly improves FX multi-day strategies by avoiding the expensive financing side. But it cannot manufacture EV where the underlying edge has decayed.

---

## A. Dédale in our framework (real swaps, 2018–2025)

Per-sleeve, only-positive-swap side, trend-filtered (hold when trend aligns with carry side, else flat):

| sleeve | side | swap bps/night | total | **price** | **swap** | Sharpe | maxDD | pre-2024H2 | post-2024H2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| USDJPY | long | +0.20 | +22.8% | **+22.1%** | **+2.2%** | 0.50 | −15.1% | **+24.5%** | **−1.7%** |
| USDCHF | long | +0.19 | +4.4% | +4.3% | +0.7% | 0.23 | −10.6% | −0.6% | +5.0% |
| USDCAD | long | +0.05 | −13.4% | −12.3% | +0.5% | −0.34 | −20.4% | −15.6% | +2.1% |
| EURUSD | short | +0.05 | −1.3% | −0.7% | +0.4% | −0.04 | −12.1% | +2.4% | −3.8% |
| EURGBP | short | +0.05 | −11.8% | −11.1% | +0.2% | −0.93 | −12.4% | −8.7% | −3.0% |
| EURJPY | long | +0.06 | −3.8% | −3.5% | +0.3% | −0.16 | −11.8% | +4.2% | −8.0% |
| AUDJPY | long | +0.31 | −3.6% | −4.3% | +1.4% | −0.15 | −14.2% | −1.6% | −1.9% |
| **Portfolio (eq-wt)** | — | — | **−0.1%/yr** | — | — | **−0.05** | **−6.8%** | +0.7% | −1.6% |

**Four honest findings:**
1. **The swap is a tiny kicker now, not the edge.** 0.2–2.2% over multi-year (~0.3–0.4%/yr). The author's **+1.53%/8mo (≈2.3%/yr)** came from the 2022–24 high-carry regime (JPY differential ~5–6%); the real FTMO swap today is ~0.7%/yr gross and ~0.3%/yr after the trend filter sits some of it out. **The carry decayed with the macro spread.**
2. **The "edge" was the JPY uptrend (beta), not carry-alpha.** +22.1% price vs +2.2% swap on USDJPY. Strip the 2022–24 USD/JPY trend and there's no edge.
3. **The trend filter is the one sound element** — it *did* protect the unwind (USDJPY post-2024 **−1.7%** vs a raw −12% drop; it exited on the trend flip). Good design, but it converts the strategy into pure trend (beta).
4. **DD breaches the 10% floor per-sleeve** (−15 to −20%); only the 7-sleeve portfolio gets DD < 10% (−6.8%) — but then return ≈ 0. **p(pass) 22–30%** at every leverage.

**Reconciliation with his +8.96% / Sharpe 2.29:** that was a *favorable 8-month window* (Sep-2024→Mar-2025), a specific multi-asset selection, pivot-bracket sizing, and a **Sharpe he himself flags as inflated** (fixed 1% SL → low return vol). He also documents the plateau/decay in that very window. Our 2018–2025, 7-sleeve view shows the **regime-dependence** behind the favorable snapshot. Both are true: it worked in the carry regime, it has decayed.

## B. The swap-sign rule, adopted into our strategies

**B1 — Overnight harvester (indices).** Real **US100 long swap = −3.31 bps/night**. The overnight equity
premium is a *long* phenomenon, but the positive-swap side of US100 is *short* — you cannot collect the
long premium without paying the swap. p_funded at the real swap:

| swap (bps/night) | net edge | p_funded (k=0.75) |
|---|---:|---:|
| 0 (swap-free) | +3.5 | 80% |
| 2.0 (my earlier estimate) | +1.5 | 55% |
| **3.31 (real US100)** | **+0.2** | **31%** |

→ The swap-sign rule says *don't hold an index long overnight* — which is **structurally fatal to the
harvester** (and updates the hardening report: real swap → ~31%, worse than the prior <50%).

**B2 — Swing-MR (FX).** Filtering EURGBP swing-MR to its swap-positive (short) side:

| variant | n | mean net (bps) | t |
|---|---:|---:|---:|
| unfiltered (two-sided) | 74 | +28.6 | 3.53 |
| **swap-sign filtered (short-only)** | 39 | **+35.1** | **3.87** |

→ A modest, sound improvement (avoids the −1.19/night long financing, keeps the stronger leg) — but it
**halves the sample, makes the strategy one-sided, and does not fix the OOS decay** we already found.

**Net rule:** keep it as a **hard cost-discipline filter** — never hold the negative-swap side overnight;
it flags structurally-doomed configurations (long index overnight) and shaves financing off FX
multi-day holds. It is not an alpha generator.

## Verdict

- **Dédale today:** flat at real swaps (p(pass) 22–30%) — does **not** beat ORB+floor (~46–50%). It was a regime trade (2022–24 JPY carry-trend) now decayed; the carry kicker is ~0.3%/yr; the trend filter (crash protection) is the keeper idea, but it leaves you holding pure trend/beta with per-sleeve DD > 10%.
- **Swap-sign rule:** a real, reusable cost-discipline win — it explains and confirms the overnight-indices death (31%) and trims FX financing — but it cannot create EV where the edge has decayed.
- **For the FTMO goal:** neither changes the conclusion. The incumbent (ORB-30min + floor) remains the best vehicle; Dédale's value to *us* is the swap-sign discipline, which we adopt going forward.

---

### Artifacts
- Real swaps: `outputs/swing/ftmo_specs.csv` (your upload). Backtest code inline (carry-trend sleeves, swap-sign filter); reuses `swing_deepdive.py`, `overnight_harvester_sim.py`.
- Friend's algos assessed: `DédaleFormation.mq5` (carry+trend), `PropFirmProtector.mq5` (DD guard — competent, doesn't prevent overnight gaps).
