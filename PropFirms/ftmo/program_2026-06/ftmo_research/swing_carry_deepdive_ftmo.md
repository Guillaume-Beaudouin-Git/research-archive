# Swing & multi-day carry — FTMO deep-dive

**Mandate:** the intraday menu is closed (everything = one-sided beta after honest costs). This pass opens
the **swing / multi-day horizon** — does a *longer* hold escape the intraday beta trap? — and tests
**multi-day FX carry**, using the **real FTMO swap rates** (uploaded `instruments_specs.csv`), which are
decisive for carry and pin the financing for swing.

**Discipline:** non-overlap; per-trade bps cost; **real asymmetric FTMO swap per night** (long vs short,
from the platform specs); 1-day delay; **two-sided** (long-leg vs short-leg); OOS split; DSR on the
total swing space.

---

## Verdict up front

> **The swing horizon produced the arc's first genuinely promising candidate — and the battery correctly killed it.** Swing **mean-reversion** (fade a 3–5-day move, hold ~5 days) reached **in-sample t = 3.53** on EURGBP (two-sided, delay-robust, survives the real swaps) — the first cell ever to clear a DSR bar. But the full battery dismantled it:
> - **Alpha decay OOS:** US500 swing-MR **train (≤2013) t=2.92 → test (>2013) t=0.42** (short-term reversal arbitraged away post-2013); EURGBP **train t=3.75 → test (2024–25) t=0.89**. The high full-sample t is the in-sample peak of a *decaying* effect.
> - **No cross-sectional generalization:** applying the EURGBP-best logic uniformly, only **2 of 18 instruments** are two-sided positive; most are *negative*. A robust effect would be broad; this is a few range-bound instruments in a favourable window.
>
> **Swing momentum** is beta (delay-collapses, one-sided), same as intraday. **Multi-day carry is dead** on the real FTMO swaps: the receivable side is **< 1.2 %/yr** (markup-eaten), and the unwind drawdown is **−15 % to −20 % even unleveraged** — it breaches the −10 % FTMO floor before any leverage that could reach +10 %.
>
> **No deployable swing/carry FTMO alpha.** But this is the closest the research came, and the two-stage process worked exactly as designed: the pre-filter surfaced a real-looking candidate, the battery (OOS + cross-instrument + real swaps) exposed it as decayed and non-general.

**Bonus correction:** the real **US100 swap is −3.31 bps/night long** (vs my 2 bps estimate) → the
overnight harvester is *worse* than `OVERNIGHT_drift_hardening.md` concluded (deployable < 50 %).

---

## 1. Real FTMO swaps (from your platform specs)

Converted to bps/night at current price (`points × 10^−digits / price`):

| instrument | swap long | swap short | note |
|---|---:|---:|---|
| EURGBP | −1.19 | +0.05 | long pays, short ~free |
| USDJPY | +0.20 | −1.60 | tiny long carry, costly short |
| AUDJPY | +0.31 | −1.67 | JPY-cross carry, tiny |
| EURJPY | +0.06 | −0.72 | — |
| US100 | **−3.31** | +0.12 | index long very costly overnight |

The asymmetry (you pay more than fair on the costly side, receive less than fair on the carry side) is
the broker markup — confirming your note that the **missing instruments are "just negative"** (no
positive carry to harvest). For market-neutral or two-sided swing-MR this is a modest, manageable drag;
for carry it is fatal.

## 2. Swing mean-reversion — promising in-sample, killed by the battery

Best cells, **net of the real swaps**, two-sided, delay-robust:

| instrument | logic | n | net (bps) | t | delay-1 | long/short | history |
|---|---|---:|---:|---:|---:|---:|---|
| EURGBP | fade-5d, mean-exit | 74 | +28.6 | **3.53** | +26.2 | +20.4 / +37.2 | 3.5 yr ⚠ |
| EURGBP | RSI-2, mean-exit | 84 | +23.9 | 2.96 | +20.5 | +10.1 / +37.7 | 3.5 yr ⚠ |
| US500 | fade-3d, time-exit | 828 | +21.4 | 2.51 | +7.4 | +27.7 / +16.1 | **27 yr** |
| USDJPY | Bollinger-2.5 | 39 | +40.9 | 2.02 | +41.9 | +49.3 / +32.1 | 8 yr |

**Battery — the kill:**

| test | result |
|---|---|
| **US500 OOS** | train ≤2013 **t=2.92** → test >2013 **t=0.42** (short leg −9.9). Effect **decayed post-2013**. |
| **EURGBP OOS** | train ≤2023 **t=3.75** → test 2024–25 **t=0.89** (long leg −10.9). 3.5-yr sample, edge in first half. |
| **Cross-instrument** (nday_rev uniform) | **2 / 18** two-sided positive; 11/18 net-negative (US100 −20, US30 −24, USDJPY −31…). **No generalization.** |
| **Real swaps** | NOT the killer — EURGBP held (+29.8 → +28.6). Decay + non-generalization is the killer. |

Short-term reversal was a real effect (strong pre-2013 on US indices, 2022–23 on EURGBP) that has been
**progressively arbitraged**. It is instrument- and period-specific, not a robust two-sided alpha. The
in-sample t=3.53 is survivorship over the search, not a durable edge.

**Swing momentum:** weak, one-sided, delay-fragile (best two-sided cell collapses under 1-bar delay) —
the equity drift at a longer frequency. Beta, same as intraday.

## 3. Multi-day carry — dead on the real swaps + crash tail

| pair | receivable carry (1×) | worst drawdown | worst 30-day |
|---|---:|---:|---:|
| USDJPY | +0.73 %/yr | **−14.8 %** | −10.2 % |
| AUDJPY | +1.13 %/yr | **−20.2 %** | −11.8 % |
| EURJPY | +0.22 %/yr | −11.0 % | −7.8 % |
| USDCHF | +0.58 %/yr | −20.2 % | −9.8 % |

Two independent kills: (a) the **carry is tiny** (< 1.2 %/yr — the FTMO markup eats the rate
differential, exactly as the swap specs show); (b) the **unwind drawdown (−15 to −20 %) breaches the
−10 % FTMO total floor even at 1× notional** — and any leverage to make the carry reach +10 %/yr makes
the unwind instantly fatal. Carry is structurally incompatible with the FTMO drawdown box. (Confirms
the prior `SCAN_ftmo_families` carry result, now with real FTMO swaps.)

## 4. Verdict

**Does a deployable swing or multi-day-carry FTMO alpha exist? — No.** But honestly:
- **Swing-MR is the strongest signal the arc has produced** — it cleared the two-sided + delay + (in-sample) DSR gates that killed everything intraday. It fails only at the **OOS / cross-sectional** stage: the short-term-reversal edge has **decayed** (post-2013 indices) and is **not general** (2/18 instruments). That is a *higher-quality* "no" than the intraday families, and it points at where any residual edge lives: **range-bound instruments, recent regimes, mean-reversion not momentum.**
- **Carry is closed** by the real swaps (tiny receivable) + the −10 % floor (unwind tail).
- **The incumbent challenge vehicle remains ORB-30min + floor_taper (~46–50 %).** Nothing here beats it.

**Where this leaves the search:** the swing-MR decay result suggests the only place a two-sided edge
*recently* existed is **range-bound FX crosses (EURGBP-type) with mean-reversion** — but it is thin,
decaying, and small-sample. A credible next step is **not another family** but a **breadth basket** of
the few instruments that *do* show two-sided swing-MR (EURGBP, UK100, USDJPY, AUDJPY/EURJPY) sized small
— accepting it is weak and may already be arbitraged — versus simply running **ORB-30min + floor** as the
pragmatic vehicle. Find durable EV first; the swing horizon, like the intraday, does not supply it.

---

### Artifacts
- `code/swing_deepdive.py` (engine), `outputs/swing/*_grid.csv`, `outputs/swing/ftmo_specs.csv` (your real swaps).
- Real swaps also update `OVERNIGHT_drift_hardening.md` (US100 long −3.31 bps/night → overnight worse).
