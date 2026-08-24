# K1b + Volet 2 — execution, size×path, breaker — 2026-07-15

Ground truth: real fills (exact entry/breaker-exit, slip ≤0.14 bps) + state.json exact risk
anchors (N2). M1 intra-night path unavailable locally (data wall, PREREG §8 amendment); the
endpoint-exact equivalent is decisive for the same K1b test. Engine constants read-only.

## K1b — execution-bug test (is loss = real path × real size + normal frictions?)
| night | move | price PnL | +cost +swap | recon | real | gap |
|---|---|---|---|---|---|---|
| N1 06→07/07 | −118.6 pts (−0.40%) | −335.75 | +18.50 −18.83 | **−336.09** | −354.14 | **5.1%** |
| N2 13→14/07 | −129.1 pts (−0.44%) | −383.55 | +19.11 −19.46 | **−383.89** | −402.65 | **4.7%** |

Both gaps **≪ 25%** → **NO implementation gap.** The loss is fully the real adverse overnight
move × the real size, plus ordinary frictions. Slippage was ~0 (fills = requested prices). A
consistent ~$18/night residual (real slightly worse) = under-modelled friction (swap triple-day
mult / half-spread), immaterial to the verdict. The overnight moves (−0.40%, −0.44%) are
ordinary US100 nights, breaker-truncated — matching Volet 1 (p5.5-7.6 of the nightly distribution).

## K1b — size × path decomposition (same real path, vary size) [Hb2 isolation]
| size | N1 lots / PnL | N2 lots / PnL |
|---|---|---|
| 1× equity | 0.34 / −$40 | 0.33 / −$43 |
| 4× (~pre-reg "1.3 lot") | 1.35 / −$160 | 1.32 / −$170 |
| **engine-designed on_w·scale** | 2.83 / −$335 | 3.01 / −$389 |
| **REAL** | **2.83 / −$336** | **2.97 / −$384** |

**Real size = engine-designed size (ratio 1.00 / 0.99).** The 8.4×/9.0× leverage is the calibrated
`on_w·vm` sizing at that equity — NOT oversized, NOT uncapped (confirms Volet 0: margin cap never
binds on US100). The size effect is Hb2-by-design, not a bug: a 4× book would have lost ~$160-170
instead of ~$335-390 — but Volet 1b proved cutting size slashes drift → WORSE p(pass).

## Volet 2 — breaker precision + leverage placement
- **N2 (EXACT, state.json):** anchor $9,641.29, breaker_line $9,291.29 (= −$350 daily), final
  $9,238.64 → **overshoot $52.65 past the line = 1.15×** (17.7 pts through the flatten M5 bar).
- **N1 (anchor ~reset $10k):** realized −$354.14 vs ~−$350 line → **overshoot ~$4 = 1.01× (tight).**
- Both **≤ 1.2×** (pre-reg efficient threshold) → **breaker WORKED** on continuous US100 (no gap
  blow-through, unlike the JPY intervention flash of the 02/07 breach). N2 shows the M5-grid can
  cost ~$50 on a fast night — a discretization tax, not a breaker failure.
- **Leverage placement:** baseline on_w·vm = 8.4×; pace clips [0.8, 2.0] → nightly US100 lev ∈
  [6.7×, 16.8×], median ~8.4×. The 2 losses sat at **8.4× / 9.0×** (N2 pace 1.088 = slightly behind
  schedule) = **near-baseline/median, NOT a >p90 (~14×) tail** → refutes "loss = leverage
  spike/uncapping" (b2-i) a **third** independent time; supports variance.

## Consolidated verdict inputs (all volets)
- **Losses = variance** (Volet 1: p5.5-7.6; K1b: no bug, gaps 5%/5%; Volet 2: breaker efficient,
  near-baseline leverage). 07/07 real −$354 vs model −$378 (Volet 0), consistent.
- **(b2-i) cap-uncapping / oversizing: REFUTED** (Volet 0 cap never binds; K1b real = designed
  size; Volet 2 lev near-median) — 3× independently.
- **(b2-ii) undamped-vol → more breakers: REFUTED** (Volet 1b: mono breaks LESS, 690 vs 1674/1k).
- **Surviving structural finding (b2-iii) return-starvation:** mono drift 0.29 vs 0.80%/day,
  t_P1 12→35d, p(pass) −37pt, PROVEN by unbounded-horizon = 100% (no structural bust-out; pure
  speed/clock). Remedy = ADD return engines (restamp +12.6pt banked; J1 +30, gold +34) or extend
  horizon (+26pt @182d) — NEVER cut US100 size.

## Infra debt (separate from the strategy verdict)
1. `fills.csv` is not a reliable position ledger (missing closes, spans the 06/24 reset).
2. US100 M1 path post-2026-06-05 is not repatriated → future intra-night replay needs a read-only
   VPS MT5 pull. Both are audit-infrastructure items, not strategy findings.
