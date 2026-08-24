#!/usr/bin/env python3
"""Volet 0 — mono-sleeve composition (real fills) + margin-cap-binding mechanism (audited engine).

READ-ONLY. The audited cleanroom engine is imported from the MAIN dir by absolute path and
NEVER mutated (we only call build_signals / read constants). See PREREG.md §4 Volet 0 + §7.

Part A: reconstruct each ON-night overnight composition from the real fills → M0a, M0b (real).
Part B: with the engine's own WT/ON/MRATE/mcap, compute the 22:05 US100 post-cap size in the
        'full/diversified' vs 'mono-sleeve' regime → does the 60% margin cap BIND on shared
        nights and NOT on mono nights? (the precise Hb2 cause). Validated vs engine margin_log.
"""
import sys, csv
from collections import defaultdict
from pathlib import Path
import numpy as np

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
import engine as E  # audited, read-only

HERE = Path(__file__).resolve().parent
FILLS = HERE / "realdata/fills.csv"
GATE = "2026.07.03"          # J1 gate deployed
SYMS = {"XAUUSD": 0, "USDJPY": 1, "US100.cash": 2, "GER40.cash": 3}
US100_PX = 1.0               # LOT_UNITS US100 = 1.0 -> notional = lots * price

def sgn(side): return 1.0 if side == "BUY" else -1.0

# ================= Part A — real overnight composition =================
rows = list(csv.DictReader(open(FILLS)))
pos = defaultdict(float)         # running signed lots per symbol
overnight = []                   # snapshot of held position after each 22:05 rebalance
for r in rows:
    ts = r["ts_paris"]; sym = r["symbol"]; lots = float(r["lots"]); px = float(r["fill_price"])
    pos[sym] += sgn(r["side"]) * lots
    if r["reason"] == "rebalance" and ts.endswith("22:05:00"):
        # snapshot legs held overnight (round tiny residuals)
        held = {s: round(pos[s], 2) for s in pos if abs(pos[s]) > 0.005}
        # notional per held leg (approx, using this fill's price for US100 legs)
        overnight.append(dict(date=ts[:10], ts=ts, held=dict(held),
                              us100_lots=round(pos["US100.cash"], 2),
                              us100_px=px if sym == "US100.cash" else None))

print("=" * 78)
print("PART A — real overnight composition per 22:05 rebalance (from fills.csv)")
print("=" * 78)
print(f"{'date':11s} {'gate':4s} {'US100 lots':>10s}  legs held overnight (signed lots)")
mono_us100, shared_us100 = [], []
for o in overnight:
    postgate = o["date"] >= GATE
    legs = {k: v for k, v in o["held"].items() if abs(v) > 0.02}   # ignore 0.01 micro dust
    other = [k for k in legs if k != "US100.cash" and abs(legs[k]) > 0.02]
    is_mono = (abs(legs.get("US100.cash", 0)) > 0.02) and len(other) == 0
    tag = "MONO" if is_mono else ("multi" if legs else "-")
    print(f"{o['date']:11s} {'POST' if postgate else 'pre':4s} {o['us100_lots']:>10.2f}  "
          f"{tag:5s} {legs}")
    if abs(o["us100_lots"]) > 0.02:
        (mono_us100 if is_mono else shared_us100).append(abs(o["us100_lots"]))

print("\n--- M0a / M0b (real) ---")
on_nights = [o for o in overnight if o["held"]]
postgate_nights = [o for o in overnight if o["date"] >= GATE and o["held"]]
postgate_mono = [o for o in postgate_nights
                 if abs(o["held"].get("US100.cash", 0)) > 0.02
                 and len([k for k in o["held"] if k != "US100.cash" and abs(o["held"][k]) > 0.02]) == 0]
print(f"M0a: post-gate ON-nights with a held book = {len(postgate_nights)}; "
      f"US100-ALONE (mono) = {len(postgate_mono)} "
      f"({100*len(postgate_mono)/max(1,len(postgate_nights)):.0f}%)")
if mono_us100 and shared_us100:
    import statistics as st
    mm, ms = st.median(mono_us100), st.median(shared_us100)
    print(f"M0b: US100 lots  mono={sorted(mono_us100)} (median {mm:.2f})  "
          f"shared={sorted(shared_us100)} (median {ms:.2f})  ratio={mm/ms:.2f}x "
          f"[threshold 1.5x -> {'CONFIRMS bigger alone' if mm/ms>=1.5 else 'no'}]")

# ================= Part B — margin-cap binding (audited engine) =================
print("\n" + "=" * 78)
print("PART B — does the 60% margin cap BIND (full/diversified) but NOT (mono-sleeve)?")
print("=" * 78)
WT, ON = E.build_signals()                     # audited weights (gold, J1), clipped +/-1.5
cfg = E.CFG_V2
vm, on_w = cfg["vm"], cfg["on_w"]
mcap = cfg.get("margin_cap", 0.60)
MRATE = E.MRATE
INIT = E.INIT
print(f"engine consts: vm={vm} on_w={on_w} mcap={mcap} MRATE={MRATE} INIT={INIT}")

# representative fresh-account night: eq=INIT, scale=vm*taper*glide*pace with taper=glide=pace=1
eq = INIT
scale = vm * 1.0 * 1.0 * 1.0
onmask = ON[ON > 0].index                       # ON days (Mon/Tue)
wt = WT.reindex(onmask).fillna(0.0)

def us100_postcap(wg, wj, ger40_on, eq=eq, scale=scale):
    """22:05 targets and US100 after the engine's margin cap, given gold/J1 weights + GER40 state."""
    tgt = np.array([wg*scale*eq, wj*scale*eq, on_w*scale*eq, (on_w*scale*eq if ger40_on else 0.0)])
    need = float(np.abs(tgt) @ MRATE)
    factor = min(1.0, mcap*eq/need) if need > 0 else 1.0
    binds = need > mcap*eq
    return tgt[2]*factor, need/eq, binds

# regimes over the real ON-day weight distribution
res = defaultdict(list)
for d in onmask:
    wg, wj = float(WT.loc[d, "XAUUSD"]), float(WT.loc[d, "USDJPY"])
    # FULL diversified (real gold+J1 that day, US100+GER40 on)
    u_full, ne_full, b_full = us100_postcap(wg, wj, ger40_on=True)
    # MONO Monday post-gate (gold=0, J1=0, US100 only, GER40 skipped)
    u_mono, ne_mono, b_mono = us100_postcap(0.0, 0.0, ger40_on=False)
    # POST-RESTAMP Monday (gold=0, J1=0, US100+GER40 on)  -- Volet 4 preview
    u_rest, ne_rest, b_rest = us100_postcap(0.0, 0.0, ger40_on=True)
    res["full_u"].append(u_full);  res["full_bind"].append(b_full); res["full_ne"].append(ne_full)
    res["mono_u"].append(u_mono);  res["mono_bind"].append(b_mono)
    res["rest_u"].append(u_rest);  res["rest_bind"].append(b_rest); res["rest_ne"].append(ne_rest)

import numpy as np
fu = np.array(res["full_u"]); mu = np.array(res["mono_u"]); ru = np.array(res["rest_u"])
print(f"\nON-days sampled: {len(fu)}  (real gold/J1 weight distribution, eq={eq:.0f}, scale={scale:.1f})")
print(f"US100 notional  FULL(divers): median ${np.median(fu):,.0f} ({np.median(fu)/eq:.2f}x)  "
      f"p95 ${np.percentile(fu,95):,.0f}")
print(f"US100 notional  MONO(post-gate Mon): ${mu[0]:,.0f} ({mu[0]/eq:.2f}x)  [cap binds: {np.mean(res['mono_bind'])*100:.0f}% of days]")
print(f"US100 notional  POST-RESTAMP Mon (US100+GER40): ${ru[0]:,.0f} ({ru[0]/eq:.2f}x)  [cap binds: {np.mean(res['rest_bind'])*100:.0f}%]")
print(f"\nmargin cap BINDS on FULL/diversified nights: {np.mean(res['full_bind'])*100:.0f}% of ON-days "
      f"(need/eq median {np.median(res['full_ne']):.2f}, cap {mcap})")
print(f"US100(mono) / US100(full) median ratio = {mu[0]/np.median(fu):.2f}x   "
      f"[M0b-mechanism threshold 1.5x -> {'CONFIRMS uncapping' if mu[0]/np.median(fu)>=1.5 else 'below'}]")
print(f"US100(post-restamp Mon) vs US100(mono): {ru[0]/mu[0]:.2f}x  "
      f"-> restamp {'re-bridles US100' if ru[0] < 0.9*mu[0] else 'does NOT re-bridle US100 (cap still slack at 2 on_w legs)'}")
