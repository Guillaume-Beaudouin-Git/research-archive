"""Volet 2 — funded overlays: Δbusts / ΔEV vs baseline (paired, block-boot), magnitude vs conversion.
Overlays (funded-only, gate J1 ON base): gold vol-gate, jpy vol-gate, vm{0.85,0.7,0.5}."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB = HERE / "tables"
FEE = 96.0
P_CH, ATT_CH = 0.697, 3.29        # challenge p_pass/attempts (real_metrics swing_ON_low)
rng = np.random.default_rng(23)

base = pd.read_csv(TAB / "runs_baseline.csv").sort_values("run_id").reset_index(drop=True)
n = len(base)
IDX = []
for _ in range(3000):
    ix = []
    while len(ix) < n:
        s = rng.integers(0, n)
        ix.extend(((s + np.arange(10)) % n).tolist())
    IDX.append(np.array(ix[:n]))


def ci(delta):
    d = np.asarray(delta, float)
    bs = np.array([d[ix].mean() for ix in IDX])
    return float(d.mean()), float(np.percentile(bs, 5)), float(np.percentile(bs, 95))


def val_ev(df):
    extr = (df[df.win == "IS"].extr.mean() + df[df.win == "OOS"].extr.mean()) / 2
    VAL = FEE + 0.8 * extr
    return VAL, P_CH * VAL - ATT_CH * FEE


VAL_b, EV_b = val_ev(base)
CONFIGS = ["gold_gate", "jpy_gate", "vm085", "vm070", "vm050"]
rows = []
print(f"BASELINE (gate ON, low, vm1): bust {100*base.busted.mean():.1f}% ({int(base.busted.sum())})  "
      f"E[extr] ${base.extr.mean():,.0f}  VAL ${VAL_b:,.0f}  EV ${EV_b:+,.0f}\n")
for cfg in CONFIGS:
    d = pd.read_csv(TAB / f"runs_{cfg}.csv").sort_values("run_id").reset_index(drop=True)
    assert (d.run_id.values == base.run_id.values).all()
    VAL_c, EV_c = val_ev(d)
    dbust, dbl, dbh = ci(d.busted.values.astype(float) - base.busted.values.astype(float))
    dext, del_, deh = ci(d.extr.values - base.extr.values)
    # conversion accounting
    saved = int((base.busted & ~d.busted).sum())
    harmed = int((~base.busted & d.busted).sum())
    both = int((base.busted & d.busted).sum())
    # magnitude: for runs busted in BOTH, did the day-loss shrink? (need bust logs)
    rows.append(dict(config=cfg, bust_pct=100 * d.busted.mean(), n_bust=int(d.busted.sum()),
                     d_bust_pp=100 * dbust, d_bust_ci=f"[{100*dbl:+.1f},{100*dbh:+.1f}]",
                     E_extr=d.extr.mean(), VAL=VAL_c, EV=EV_c, dEV=EV_c - EV_b,
                     saved=saved, harmed=harmed, both_bust=both,
                     verdict="conversion" if saved > harmed else "magnitude/none"))
    print(f"[{cfg:9s}] bust {100*d.busted.mean():4.1f}% ({int(d.busted.sum())})  "
          f"Δbust {100*dbust:+.1f}pp [{100*dbl:+.1f},{100*dbh:+.1f}]  "
          f"VAL ${VAL_c:,.0f}  EV ${EV_c:+,.0f} (Δ${EV_c-EV_b:+,.0f})  "
          f"saved {saved} harmed {harmed} both {both} -> {'CONVERSION' if saved>harmed else 'weak'}")

R = pd.DataFrame(rows)
R.to_csv(TAB / "overlay_deltas.csv", index=False)

# magnitude check on the OR gate: among still-busting runs, is the day-loss smaller?
print("\n--- magnitude vs conversion (gold_gate) ---")
try:
    bb = pd.read_csv(TAB / "busts_baseline.csv")
    bg = pd.read_csv(TAB / "busts_gold_gate.csv")
    gold_base = bb[bb.dom_leg == "XAUUSD"]
    gold_gate = bg[bg.dom_leg == "XAUUSD"]
    print(f"  XAU-dominant busts: baseline {len(gold_base)} -> gold_gate {len(gold_gate)} "
          f"({'CONVERTED away' if len(gold_gate)<len(gold_base) else 'unchanged'})")
    print(f"  median day-loss XAU busts: baseline ${gold_base.daily_loss.median():,.0f} -> "
          f"gate ${gold_gate.daily_loss.median():,.0f}" if len(gold_gate) else "  gate: 0 XAU busts left")
except Exception as e:
    print("  (skip)", e)

print("\n=== SUMMARY (Δbusts / ΔEV) ===")
print(R[["config", "bust_pct", "d_bust_pp", "dEV", "saved", "harmed", "verdict"]].round(1).to_string(index=False))
(TAB / "overlay_summary.json").write_text(R.to_json(orient="records", indent=1))
