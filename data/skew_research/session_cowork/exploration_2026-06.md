> **⛔ GATE-0 CORRECTION (added 2026-06):** the "survivor" below, **Long-vol (VXX), is an ETF/VIX product with no FTMO CFD → perso-only, NOT an FTMO sleeve** (GATE-0 FTMO-tradeability fail). It is a real skew+/decorrelated edge but out-of-scope for FTMO. Net FTMO-tradeable survivors from this batch: **0**. See `exploration_datedflows_2026-06.md` for the GATE-0 rule + session bilan.

# Skew-positive sleeve exploration — session_cowork (5 candidates)
*2026-06. Phase 1 exploratory (find the edge, don't kill) → Phase 2 barriers (honest) → Phase 3 portfolio fit (the real criterion: skew+ AND decorrelated). Scope: this session only. Archive reconciled vs `../../ftmo_research/_CANONICAL_STATE.md` + IDEA_* dossiers (no central log found).*

## TL;DR
Of the 5 candidates, **only one has the target profile (skew ≥ 0 AND decorrelated): long-vol / tail (VXX)** — skew **+1.86**, correlation **−0.75 to equity** and −0.06…−0.10 to every other sleeve. **But it is negative-carry (theta bleed, standalone Sharpe −0.34) → it is portfolio *insurance*, not a profit edge.** The trend candidates (TSMOM, Donchian) are skew≈0 and die on held-notional swap (L33); cross-sectional momentum and carry are **wrong-profile (negative skew)**. The one genuinely useful construction is **a trend sleeve + a small long-vol convexity overlay** — decorrelated, and long-vol pays exactly on the correlated-crash day that threatens the trend sleeve's daily cap.

---

## PHASE 1 — raw edge + skew (exploratory, generous gate t>2 & skew≥0, NO cost)

| # | Candidate | mean (bps/d) | t (raw) | **SKEW** | Sharpe | maxDD | raw edge? | → Phase 2? |
|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | TSMOM two-sided *(cited)* | — | — | ~0 daily (+ at trade/mo) | 0.85 gross | −14% | yes (gross) | archive — done |
| 2 | **Donchian breakout** | +1.52 | **+1.98** | **+0.10** | 0.35 | −42% | marginal (≈gate) | **YES (generous)** |
| 3 | XS-momentum (basket) | +1.75 | +1.95 | **−0.16** | 0.40 | −31% | marginal | ⚑ skew<0 = wrong-profile |
| 4 | Carry+trend (AQR) *(cited)* | — | — | **negative** (carry-crash) | — | — | trend yes / carry no | ⚑ wrong-profile, cite |
| 5 | **Long-vol / tail (VXX)** | **−9.99** | −0.97 | **+1.83** | −0.34 | −99% | NO (theta) | **special: convexity → P3** |

**Reading (exploratory, not killing):**
- **Donchian** is the only new candidate near the edge gate *with* positive skew → carried to Phase 2.
- **XS-momentum** has a marginal edge but **mildly negative skew** (momentum-crash signature) — a directional flag (wrong profile for *this* objective), not a kill.
- **Long-vol** is the inverse case: it *fails* the raw-edge gate (negative EV — it bleeds theta) but has **by far the best skew (+1.83)**. Its value is not a standalone edge; it is a **negatively-correlated convexity sleeve** → judged in Phase 3.
- **TSMOM** (cited, `../../ftmo_research/tsmom/`): the program's best candidate; daily skew ~0 (positive at trade horizon); **net of measured swap the edge ≈ container-math** — already characterized, not re-proven.
- **Carry** (cited): native **negative skew** (carry-crash — falsified-as-structural in the parallel J1/G1 work, which found carry = beta-proxy, L32 one-sided-uncollectable). Wrong profile; not pursued.

---

## PHASE 2 — barriers (Donchian; others cited from archive)

**Donchian breakout — confronted (honest, killing):**
- **Cost (L33):** survives turnover spread (Sharpe 0.35→0.32 at 2 bps) but **dies on held-notional swap** (measured equity ~4.5 bps/trading-day → Sharpe **−0.73**, mean −3.12 bps). Same carry trap as TSMOM/overnight — it *holds* positions.
- **Two-sided (L25):** **long-only Sharpe +0.71, short-only −0.20** → long-biased, not a clean two-sided edge (the short breakouts lose). Partial beta.
- **Load-bearing (L26) delay+1:** Sharpe 0.35 → 0.29 → **survives the +1-day delay** (real, not microstructure). ✅ the one clean pass.
- **OOS (L31):** IS 2006–15 Sharpe **0.96** → OOS 2016–26 **0.18** → **decays badly** out-of-sample.
- **Archive:** intraday ORB is archived (killed); daily Donchian is the *trend family* (correlated with TSMOM — Phase 3).
- **Verdict:** marginal, swap-killed, long-biased, OOS-decaying, and redundant with the trend sleeve → **not a robust standalone, not a complementary sleeve.**

**Cited (not re-proven):** TSMOM → net-of-swap ≈ container-math (`tsmom/`). Carry → beta-proxy, negative skew (parallel J1/G1, L32). XS-momentum → wrong-profile + see Phase 3 redundancy.

---

## PHASE 3 — portfolio fit (THE criterion: skew+ AND decorrelated)

Daily-return correlation matrix (common window 2018-01 → 2026-05, n=2094):

| | Donchian | XS-mom | Long-vol | TSMOM | Long-US500 |
|---|---:|---:|---:|---:|---:|
| **Donchian** | 1.00 | −0.11 | −0.09 | −0.06 | +0.06 |
| **XS-mom** | −0.11 | 1.00 | −0.09 | **+0.39** | +0.06 |
| **Long-vol** | −0.09 | −0.09 | 1.00 | −0.10 | **−0.75** |
| **TSMOM** | −0.06 | +0.39 | −0.10 | 1.00 | +0.02 |
| **Long-US500** | +0.06 | +0.06 | **−0.75** | +0.02 | 1.00 |

Daily skew: Long-vol **+1.86**, Donchian +0.11, Long-US500 −0.12, TSMOM −0.15, XS-mom −0.25.

**Complementary-sleeve verdict per candidate:**

| Candidate | skew | standalone SR (net) | corr to equity | corr to other sleeves | **complementary sleeve?** |
|---|---:|---:|---:|---|---|
| **Long-vol (VXX)** | **+1.86** | −0.34 (theta) | **−0.75** | −0.06…−0.10 (all) | **YES — convexity/tail-hedge** (not a profit sleeve) |
| TSMOM (trend core) | −0.15 | ≈0 net-of-swap | +0.02 | +0.39 w/ XS-mom | partial — the trend core, but cost-degraded |
| Donchian | +0.10 | <0 net-of-swap | +0.06 | trend-family | **NO** — redundant + swap-killed + OOS-decay |
| XS-momentum | −0.25 | marginal | +0.06 | **+0.39 w/ TSMOM** | **NO** — wrong-profile + partly redundant |
| Carry | negative | beta-proxy | (beta) | — | **NO** — wrong-profile (L32) |

### The one real construction
**Trend sleeve + a small long-vol convexity overlay.** They are decorrelated (−0.10), and long-vol's **−0.75 equity correlation hedges precisely the residual long-beta and the correlated-crash-day tail** that threatens a trend sleeve under the FTMO daily cap (recall TSMOM's worst day −5.9% on a March-2020-type correlated crash — long-vol spikes exactly then). This is the L7 survival logic: a negatively-correlated convexity sleeve cuts the portfolio's drawdown tail.

**The honest catch:** long-vol is **negative-carry** (−10 bps/day theta, maxDD −99% naive-always-long). A naive always-long-VXX allocation *drags* the portfolio. It is a **tail-hedge allocation decision** (small, carry-aware — ideally tactical, only when the term structure is backwardated, but that exceeds the naive L10 signal), not a free sleeve. Whether the crash-day protection justifies the carry is a portfolio-construction question for the combined book, not a per-sleeve verdict.

---

## Final survivors (for the cross-session portfolio)

| Survivor | skew | SR (standalone, net) | corr to equity | archive status |
|---|---:|---:|---:|---|
| **Long-vol / tail (VXX)** | **+1.86** | −0.34 (negative carry) | **−0.75** | distinct from archived **short-vol/VRP** (which is negative-skew); long-vol = the convexity inverse, **not previously characterized as a hedge sleeve** |
| (Trend / TSMOM = core) | ~0 daily | ≈0 net-of-swap | +0.02 | archived `tsmom/` — cost-degraded |

**Lesson candidates (named, not numbered):**
- **"skew lives at the trade horizon, not daily"** — trend/breakout daily skew ≈ 0; their convexity is at the trade/monthly level. Judge skew at the horizon the strategy trades.
- **"convexity sleeve ≠ edge"** — long-vol has negative standalone EV yet is the most valuable *portfolio* sleeve (−0.75 corr, +1.86 skew). Select sleeves on skew+decorrelation, not standalone Sharpe (exactly the L7 brief).
- **"held-notional swap kills every position-holding trend variant"** — Donchian dies on the same carry that killed TSMOM/overnight (L33 generalizes).
- **"long-vol hedges the trend sleeve's correlated-crash-day tail"** — the specific, useful pairing: long-vol pays on the March-2020-type day that breaches a trend sleeve's daily cap.

*Coordination: written only in `skew_research/session_cowork/`. Archive cited, not re-proven. No other session or the overnight/trend research touched.*
