"""Q1 (challenge) + Q2 (funded) sensitivity maps over synthetic profiles."""
from __future__ import annotations
import sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import simulate, simulate_book_plus
RES = Path(__file__).resolve().parent / "results"
SEED = 20260620
SR = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
VOL = [0.05, 0.10, 0.15, 0.20, 0.30, 0.40]


def grid(fn):
    return pd.DataFrame({v: {s: fn(s, v) for s in SR} for v in VOL}).T  # index=vol, cols=SR


print("=== Q1 challenge p_pass (rows=vol, cols=SR) ===")
ppass = grid(lambda s, v: simulate(s, v, stage="challenge", seed=SEED + int(s * 10 + v * 100))["p_pass"])
print((ppass * 100).round(0).astype(int).to_string())

print("\n=== Q2 funded p_survive (1y, with extraction) ===")
def fz(s, v):
    return simulate(s, v, stage="funded", seed=SEED + int(s * 10 + v * 100))
psurv = grid(lambda s, v: fz(s, v)["p_survive"])
print((psurv * 100).round(0).astype(int).to_string())
print("\n=== Q2 E[extracted] $ (1y) ===")
eext = grid(lambda s, v: fz(s, v)["E_extracted"])
print(eext.round(0).astype(int).to_string())
print("\n=== Q2 funded bust-cause: DAILY share of busts (rest = floor) ===")
bd = grid(lambda s, v: fz(s, v)["bust_daily_share"])
print((bd * 100).round(0).astype(int).to_string())
print("\n=== Q2 realised cumulative maxDD (median, no-extraction proxy via cum_maxdd) ===")
dd = grid(lambda s, v: fz(s, v)["cum_maxdd"])
print((dd * 100).round(0).astype(int).to_string())

print("\n=== H-C intermittence: FIX active-day vol=15%, SR_active=1.0, vary presence ===")
sa = 0.15  # active-day annualised vol
for p in [1.0, 0.8, 0.6, 0.4, 0.2]:
    sig_ann = sa * np.sqrt(p)         # overall vol falls with presence
    f = simulate(1.0, sig_ann, presence=p, stage="funded", seed=SEED + int(p * 1000))
    c = simulate(1.0, sig_ann, presence=p, stage="challenge", seed=SEED + int(p * 1000))
    print(f"  presence {p:.1f} -> sig_ann {sig_ann*100:4.1f}% | funded surv {f['p_survive']:.2f} "
          f"E[extr] ${f['E_extracted']:.0f} | challenge p_pass {c['p_pass']:.2f}")

print("\n=== H-D daily tail: SR1.5 vol15%, vary nu (t-tail) and m (intraday excursion) ===")
for nu in [np.inf, 6, 3]:
    for m in [1.0, 1.5, 2.5]:
        f = simulate(1.5, 0.15, nu=nu, m=m, stage="funded", seed=SEED)
        print(f"  nu={str(nu):>4} m={m} : funded surv {f['p_survive']:.2f} | bust daily {f['bust_daily_share']:.0%} | challenge p_pass {simulate(1.5,0.15,nu=nu,m=m,stage='challenge',seed=SEED)['p_pass']:.2f}")

print("\n=== H-F tail co-occurrence with the book (candidate SR1.0 vol10% p0.5 added to book) ===")
for rho in [0.0, 0.3, 0.6, 0.9]:
    r = simulate_book_plus(1.0, 0.10, 0.5, rho, seed=SEED)
    print(f"  rho_tail {rho:.1f} : book+cand surv {r['p_survive']:.2f} | E[extr] ${r['E_extracted']:.0f}")
# book alone baseline
print(f"  book ALONE (calibration): surv {simulate(0.9,0.09,stage='funded',seed=SEED)['p_survive']:.2f}, "
      f"cum_maxdd {simulate(0.9,0.09,stage='funded',seed=SEED)['cum_maxdd']*100:.0f}%")

# heatmaps
for name, g, ttl, fmt in [("ppass", ppass, "Q1 Challenge p_pass", 0), ("psurv", psurv, "Q2 Funded p_survive (1y)", 0),
                          ("eext", eext / 1000, "Q2 E[extracted] $k", 1)]:
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    im = ax.imshow(g.values, cmap="RdYlGn", aspect="auto", origin="lower",
                   vmin=0, vmax=(1 if name != "eext" else None))
    ax.set_xticks(range(len(SR))); ax.set_xticklabels([f"{s:.1f}" for s in SR])
    ax.set_yticks(range(len(VOL))); ax.set_yticklabels([f"{int(v*100)}%" for v in VOL])
    ax.set_xlabel("Sharpe (ann)"); ax.set_ylabel("Vol (ann)"); ax.set_title(ttl)
    for i in range(g.shape[0]):
        for j in range(g.shape[1]):
            ax.text(j, i, f"{g.values[i,j]*(100 if name!='eext' else 1):.{fmt}f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax); fig.tight_layout(); fig.savefig(RES / f"fig_{name}.png", dpi=120); plt.close(fig)
print("\nsaved heatmaps")
