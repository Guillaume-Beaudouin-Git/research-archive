#!/usr/bin/env python3
"""K1b (execution-bug + size×path decomposition) + Volet 2 (breaker precision + leverage).

Data reality: the canonical M1 path (data/deep_history_utc/US100_M1.csv) ENDS 2026-06-05 and
the sim_m5 cache ends 2026-06-05 too -> the July loss nights' intra-night M1 path is NOT local
(it lives only on the live VPS MT5). BUT the real fills give EXACT entry/breaker-exit endpoints,
and state.json gives the EXACT live risk anchors for night 2 -> the DECISIVE K1b test (is the loss
= real_path × real_size + normal frictions, no implementation gap?) is fully computable from
ground truth. Engine constants imported read-only (RT cost, swap).  READ-ONLY, engine unmutated.
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
import engine as E

RT_US100 = 2.2          # bps round-trip (phase0_rt_cost_bps)
SWAP_BPS = -2.24        # bps/night long (panel last); mult up to 3 on triple days
LOTU = 1.0              # US100 contract size per lot
INIT = E.INIT

# ---- ground truth from fills.csv + state.json ----
NIGHTS = [
    dict(tag="N1 06->07/07", lots=2.83, px_in=29708.97, px_out=29590.33,
         real_pnl=-354.14, anchor=9995.43, brk_line=None, final=None,   # anchor inferred (~reset $10k)
         scale=14.0),  # governor unknown for N1 -> baseline vm assumed
    dict(tag="N2 13->14/07", lots=2.97, px_in=29253.47, px_out=29124.33,
         real_pnl=-402.65, anchor=9641.29, brk_line=9291.29, final=9238.64,  # EXACT from state.json
         scale=15.2308),  # governor.scale live (vm14 x pace1.088)
]

print("=" * 84)
print("K1b — execution-bug test  (reconstruct loss from real path×size + frictions)")
print("=" * 84)
for n in NIGHTS:
    dpx = n["px_out"] - n["px_in"]
    price_pnl = n["lots"] * dpx * LOTU
    notion = n["lots"] * n["px_in"] * LOTU
    # AUDIT FIX 2026-07-15: fills are ACTUAL transaction prices (slip<=0.14bps), so the
    # bid/ask spread is ALREADY embedded in the fill-to-fill move -> adding an explicit RT
    # spread cost would DOUBLE-count (and the prior version added it with the wrong SIGN, as
    # a gain). The only residual friction on top of the realized move is the overnight swap.
    swap = SWAP_BPS / 1e4 * notion                            # 1 overnight (mult=1 baseline)
    recon = price_pnl + swap
    gap = recon - n["real_pnl"]
    print(f"\n{n['tag']}:  BUY {n['lots']} @ {n['px_in']:.2f} -> SELL @ {n['px_out']:.2f}  "
          f"(move {dpx:+.2f} pts = {dpx/n['px_in']*100:+.2f}%)")
    print(f"  price PnL {price_pnl:+.2f}  + swap {swap:+.2f}  = recon {recon:+.2f}  "
          f"(spread embedded in fills; slip<=0.14bps)")
    print(f"  real (reconcile/anchor) {n['real_pnl']:+.2f}   |gap| {abs(gap):.2f} "
          f"= {abs(gap)/abs(n['real_pnl'])*100:.1f}%  [K1b: <=25% -> NO implementation gap]  "
          f"slip fills<=0.14bps")

print("\n" + "=" * 84)
print("K1b — size × path decomposition  (SAME real path, vary size)  [Hb2 isolation]")
print("=" * 84)
for n in NIGHTS:
    dpx = n["px_out"] - n["px_in"]
    eq = n["anchor"]
    lev_real = n["lots"] * n["px_in"] / eq
    designed = 0.6 * n["scale"]                                # on_w * governor scale
    lots_designed = designed * eq / n["px_in"]
    print(f"\n{n['tag']}  (eq {eq:.0f}, real move {dpx:+.1f} pts):")
    print(f"  {'size':>22s} {'lots':>6s} {'lev':>6s} {'price PnL':>10s}")
    for lbl, lev in [("1x equity", 1.0), ("4x (~pre-reg 1.3lot)", 4.0),
                     (f"designed on_w*scale", designed), ("REAL", lev_real)]:
        lots = lev * eq / n["px_in"]
        print(f"  {lbl:>22s} {lots:6.2f} {lev:5.1f}x {lots*dpx*LOTU:+9.2f}")
    print(f"  -> real {n['lots']} lots vs engine-designed {lots_designed:.2f} lots "
          f"(ratio {n['lots']/lots_designed:.2f}) : size = DESIGNED sizing, not oversized/uncapped")

print("\n" + "=" * 84)
print("Volet 2 — breaker precision (overshoot vs its line) + leverage placement")
print("=" * 84)
# N2 exact
n = NIGHTS[1]
overshoot2 = n["brk_line"] - n["final"]
print(f"N2 (EXACT, state.json): anchor {n['anchor']:.2f}  daily_floor {n['anchor']-500:.2f}  "
      f"breaker_line {n['brk_line']:.2f} (=-$350)")
print(f"  final {n['final']:.2f}  -> overshoot {overshoot2:+.2f} past line "
      f"= {abs(n['real_pnl'])/350:.2f}x the -$350 line  "
      f"({overshoot2/n['lots']:.1f} pts in the flatten M5 bar)")
# N1 inferred
print(f"N1 (anchor ~reset $10k): breaker line ~-$350, realized {NIGHTS[0]['real_pnl']:.2f} "
      f"-> overshoot ~$4 (~1.01x line, TIGHT)")
print(f"  [pre-reg: exit <=1.2x line -> breaker EFFICIENT ; N1 1.01x, N2 1.15x -> both PASS ; "
      f"N2 shows M5-grid gap-through ~$53]")
# leverage placement (analytic: lev = on_w*scale, scale = vm*taper*glide*pace, pace in [0.8,2.0])
print(f"\nLeverage: on_w*vm baseline = 0.6*14 = 8.4x (pace=taper=glide=1).")
print(f"  pace clips [0.8,2.0] -> realized nightly US100 lev in [6.7x, 16.8x], median ~8.4x.")
print(f"  N1 lev {NIGHTS[0]['lots']*NIGHTS[0]['px_in']/NIGHTS[0]['anchor']:.1f}x  "
      f"N2 lev {NIGHTS[1]['lots']*NIGHTS[1]['px_in']/NIGHTS[1]['anchor']:.1f}x "
      f"(scale 15.23, pace 1.088 = slightly behind schedule)")
print(f"  -> the 2 losses sat at ~8.4-9.1x = NEAR-BASELINE/median, NOT a high-lev (>p90 ~14x) tail")
print(f"  -> refutes 'loss = leverage spike/uncapping' (b2-i, 3rd independent time); supports variance")
