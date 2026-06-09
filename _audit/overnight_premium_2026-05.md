# Equity-index overnight premium — structural-premium probe (Family-5)

**Date:** 2026-05-31 · **Sprint:** carte-blanche, Family-5 · **Verdict: NO-GO net — but the most informative result of the program**
**Code:** `PropFirms/ftmo_alpha_program/strategy/overnight_premium.py`, `run_overnight.py`
**Data:** MT5 1-min US500/US100/US30 panels, 2020–2026. **Protocol:** IS 2022-2024; verdict on the **untouched hold-out 2025-2026**; cost gate net-of-swap first; DSR true trial count; FTMO MC honest.

---

## The prior (and why it is not family-hopping)

Four prior families died as microstructure reversal edges with no robust gross OOS edge. The only
barrier-friendly distribution in the book's history (Strategy B) came from a **structural premium**.
Premia are compensation for risk borne — they do not decay like microstructure. The best-documented
premium available on an FTMO instrument is the **equity-index overnight premium** (Cooper-Cliff-Gulen;
Lou-Polk-Skouras): indices earn their drift *close→open*, not *open→close*. This is structurally
different from the four nulls: a **risk premium** (not reversal), **1 trade/night** (cost is a fixed
tax, not turnover-scaled), and it **holds the risk overnight** (the opposite of intraday-flat — the
holding *is* the premium). Test designed to split GO / VENUE-failure / EDGE-failure.

## Étape 0 — the premium is real (gross), IS 2022-2024

Night/day decomposition (weekday holds only; FTMO forbids weekend holding):

| index | overnight (gross) | annSharpe | win rate | daily kurtosis | intraday (gross) |
|---|---|---|---|---|---|
| US500 | 8.3%/yr | 0.69 | 53.1% | **2.6** | 1.3%/yr |
| US100 | **13.2%/yr** | **0.85** | 53.9% | **2.5** | 0.5%/yr |
| US30 | 4.5%/yr | 0.43 | 51.9% | 3.7 | 2.4%/yr |

The night effect is present and, critically, **low-kurtosis (2.5–2.6 < 3)** — the barrier-friendly
grind the program had not found in four families. Intraday legs are ~0: textbook decomposition.

## Étape 1–2 — gates (canonical: US100, swap 2 bps/night, CFD ×3, weekday-only)

| Gate | Result | Verdict |
|---|---|---|
| **Gross-only Sharpe (zero cost)** | IS **0.85** → OOS **1.78** (untouched) | **survives** — first robust gross OOS edge in the program |
| **Cost L11 net-of-swap** (ratio gross/cost) | 1.39 @1bps · **1.00 @2bps** · 0.78 @3bps | **FAIL** (< 3) |
| Net Sharpe | IS **0.00** → OOS 0.67 (marginal, swap-sensitive) | thin |
| Daily kurtosis | 3.16 | borderline |
| **Tail-DD** P(touch −8%/60 sessions) | **17.3%** | FAIL (< 10%) — overnight-gap left tail |
| Per-year net Sharpe | −0.07 / −0.30 / +0.32 / −0.00 / **+1.67** | directional, regime-dependent |
| DSR (n_trials=20) | 0.001 | FAIL |
| **FTMO MC honest** P(pass) | 28% (σd 1%) · 30% (σd 0.8%) · 23% (σd 0.6%) | FAIL — ≈ the **zero-edge** baseline |

## Verdict — NO-GO net, and a crucial refinement of the venue pivot

The structural-premium prior is **validated**: the overnight premium is the program's first robust
gross out-of-sample edge (gross Sharpe 0.85 IS → 1.78 OOS, low kurtosis). But:

1. **Net of financing it is ≈ zero on a leveraged account** — cost ratio ~1.0 at a realistic 2 bps/night
   swap; net Sharpe IS 0.00; FTMO P(pass) peaks ~30%, which is exactly the **zero-edge** combined
   baseline. The CFD swap consumes the premium.
2. **The edge is directional equity beta**, not alpha: net per-year Sharpe flips sign with the market
   regime (positive only in the bull years 2024/2026), and it carries an **overnight-gap left tail**
   (tail-DD 17% > 10%) — a barrier risk in its own right.
3. **The financing is NOT a retail-CFD tax — it is fundamental.** The cost of carry of leveraged
   overnight equity is embedded in the equity-index **futures basis** too (F = S·e^{(r−q)T} decays to
   spot). So holding the premium on futures does **not** escape it — unlike the HF-reversal case, where
   futures' ~10× lower *transaction* cost would help. The only venue that avoids the carry is holding
   the **cash index unleveraged**, which no propfirm challenge does.

This is the sharpest distinction the whole program produced. It refines the earlier venue thesis: the
venue pivot rescues *transaction-cost*-killed edges (reversal), **not** *carry*-killed edges
(overnight premium). The premium is real but its harvesting cost is intrinsic to leverage.

**Place in the program (5 families).** Four microstructure families: no robust gross edge. One
structural premium: robust gross edge, but leveraged-beta, carry-captured on any leveraged venue, and
gap-tail-risky. **The combination the barrier requires — robust + barrier-friendly + cheaply
harvestable under leverage + non-directional — does not exist in the FTMO-available instrument/venue
set.** Measured, not assumed. This closes the search on a strong footing.
