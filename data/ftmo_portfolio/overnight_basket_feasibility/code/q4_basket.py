"""Q4 — shared operational risk of the basket (swap/spread/margin), read-only on live infra.

(a) Swap-free: do the 4 windows avoid the 00:00-server rollover (21:00 UTC summer / 22:00 UTC winter)?
(b) Swap counterfactual: if a leg paid -3 to -4 bp/night, does it sink its (thin) edge?
(c) Margin: basket footprint under the 60% cap + overlap with the live book (XAU double-count + GER40).
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import overnight_series as OS

OUT = Path(__file__).resolve().parent.parent / "results"

# gross per-day edge (bp) per sleeve, from Q1 (report): silver 5.30, WTI 3.51, gold ~asia, soybean ~5.9 raw
EDGE_BP = {"GOLD": 5.0, "SILVER": 5.30, "WTI": 3.51, "SOYBEAN": 5.92}
# windows (UTC entry->exit); rollover at 21:00 (summer EEST) / 22:00 (winter EET) UTC
WINDOWS = {"GOLD": (23, 7), "SILVER": (23, 7), "WTI": (23, 7), "SOYBEAN": (1, 7)}


def crosses_rollover(entry, exit_, roll):
    # holding interval on a 0..47h axis; window crosses if a rollover instant is strictly inside
    e = entry; x = exit_ + (24 if exit_ <= entry else 0)
    for r in (roll, roll + 24):
        if e < r < x:
            return True
    return False


def main():
    res = {}
    # (a) swap-free timing
    sw = {}
    for nm, (en, ex) in WINDOWS.items():
        summer = crosses_rollover(en, ex, 21)
        winter = crosses_rollover(en, ex, 22)
        sw[nm] = dict(window=f"{en:02d}:00->{ex:02d}:00 UTC", crosses_summer=summer, crosses_winter=winter,
                      swap_free=not (summer or winter))
    res["swap_free"] = sw
    print("=== (a) swap-free timing (rollover 21:00 summer / 22:00 winter UTC) ===")
    for nm, v in sw.items():
        print(f"  {nm:8s} {v['window']}  crosses rollover? summer {v['crosses_summer']} / winter {v['crosses_winter']}  "
              f"-> swap-free {v['swap_free']}")
    res["all_swap_free"] = all(v["swap_free"] for v in sw.values())

    # (b) swap counterfactual: -3.5 bp/night vs each leg's gross edge
    print("\n=== (b) swap counterfactual (if a leg were NOT swap-free, -3.5 bp/night) ===")
    cf = {}
    for nm, e in EDGE_BP.items():
        cf[nm] = dict(gross_bp=e, net_if_swap_m3_5=round(e - 3.5, 2), survives=bool(e - 3.5 > 1.0))
        print(f"  {nm:8s} gross {e:.2f} bp/day -> if swap -3.5: {e-3.5:+.2f} bp  "
              f"{'survives' if e-3.5>1.0 else 'DEAD (edge wiped)'}")
    res["swap_counterfactual"] = cf
    print("  => WTI (thinnest, 3.51bp) is wiped by a 3.5bp swap; swap-free is LOAD-BEARING for WTI.")

    # (c) margin footprint (basket adds separate instruments under the 60% cap)
    # FTMO Swing rates (assumed; XAU known 1/9; metals/energy/ag commodity CFD ~1/10): confirm live
    RATE = {"GOLD": 1/9, "SILVER": 1/9, "WTI": 1/10, "SOYBEAN": 1/10}
    print("\n=== (c) margin footprint (basket margin / equity), assumed Swing rates ===")
    marg = {}
    for tag, sl in [("B3", ("GOLD", "SILVER", "WTI")), ("B4", ("GOLD", "SILVER", "WTI", "SOYBEAN"))]:
        N = len(sl)
        # per-sleeve avg |pos| (VT ~1.0); use realized mean of pos
        avgpos = {nm: float(OS.build(nm, 2.0)["pos"].mean()) for nm in sl}
        per_K = {}
        for K in (1.0, 2.0, 3.0):
            m = sum((1.0 / N) * K * avgpos[nm] * RATE[nm] for nm in sl)
            per_K[K] = round(m, 3)
        marg[tag] = dict(rates={nm: round(RATE[nm], 3) for nm in sl}, margin_frac_by_K=per_K)
        print(f"  {tag}: margin/equity  " + "  ".join(f"K{K}: {per_K[K]:.2f}" for K in (1.0, 2.0, 3.0)))
    res["margin"] = marg
    res["margin_note"] = ("book live already holds XAU (or-trend, continuous Swing) + GER40 overnight (Mon/Tue, "
                          "17:35->09:00) during 23:00-07:00 UTC; the basket ADDS XAU(again, double-count)+XAG+"
                          "USOIL(+soybean). Book binds the 60% cap ~56% of days (asia spec) -> basket stacks on "
                          "top -> combined >60% at K>=2 during the overlap -> forced de-lever (engine does not "
                          "model intra-window margin). XAU is held TWICE (book or-trend + basket gold leg).")
    print("  " + res["margin_note"][:120] + "...")

    (OUT / "q4_basket.json").write_text(json.dumps(res, indent=2, default=str))
    print("\nwritten q4_basket.json")


if __name__ == "__main__":
    main()
