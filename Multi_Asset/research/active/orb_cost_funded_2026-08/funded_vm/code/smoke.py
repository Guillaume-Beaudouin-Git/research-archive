"""Smoke test volet D : charge la pile, vérifie les invariants, mesure le temps.

Lecture seule sur data/ftmo_portfolio/** et audit_v2_independent/**.
"""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "data" / "ftmo_portfolio" / "v22"))
import engine_v22 as V          # noqa: E402
import config_v22 as C22        # noqa: E402
E = V.E

t0 = time.time()
M = V.load_stack(orb_rt_bps="era")
print(f"stack loaded n={M['n']} [{time.time()-t0:.0f}s]", flush=True)
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M, WT_df, ON_df)
print(f"signals [{time.time()-t0:.0f}s]", flush=True)

# --- invariants ---
print("MRATE default (Standard):", E.MRATE)
print("MRATE_SWING            :", C22.MRATE_SWING)
print("CFG_FUNDED_V28         :", C22.CFG_FUNDED_V28)
src = (ROOT / "data/ftmo_portfolio/v22/engine_v22.py").read_text()
fn = src.split("def run_funded")[1]
print("run_funded mentionne ab_days :", "ab_days" in fn, "| zombie :", "zombie" in fn)

for win, lo, hi in C22.FUNDED_WINDOWS:
    st = V.starts(M, lo, hi, C22.FUNDED_STEP)
    print(f"{win}: n_starts={len(st)} de {M['dates'][int(st[0])].date()} "
          f"a {M['dates'][int(st[-1])].date()}")

# --- timing d'un run_funded ---
st = V.starts(M, *C22.FUNDED_WINDOWS[1][1:], C22.FUNDED_STEP)
t1 = time.time()
rs = [V.run_funded(M, int(i0), WT, ON, C22.CFG_FUNDED_V28,
                   horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
      for i0 in st[:10]]
dt = (time.time() - t1) / 10
print(f"run_funded: {dt:.2f}s/cohorte -> grille 48 cellules x ~185 coh = "
      f"{dt*48*185/60:.0f} min mono-coeur")
print(pd.DataFrame(rs))

# --- orb_R : reconstruction locale pour la grille de cout ---
led = pd.read_parquet(V.LEDGER)
lev = (led["entry"] / (led["entry"] - led["stop_eff"]).abs()).astype(float)
print("lev median", lev.median(), "N", len(led))
c_era = V._implied_era_cost(led, lev)
print("cout era implicite bps: p25/p50/p75",
      np.percentile(c_era, [25, 50, 75]).round(3))
for b in ("era", 1.0, 1.8, 2.2, 3.0):
    if b == "era":
        r = pd.read_parquet(E.CACHE / "orb_e7_Rera.parquet")["R"]
    else:
        r = led["r_gross"].astype(float) - float(b) * 1e-4 * lev + 0.015
    print(f"orb_rt_bps={b!s:>4}: mean R {r.mean():+.4f} N {len(r)}")
