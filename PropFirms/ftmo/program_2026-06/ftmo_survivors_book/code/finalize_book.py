"""finalize_book.py — p(pass) table CSV + leverage-sweep / CI figure for the survivors book."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path("<HOME>/Desktop/Algo_claude")
OUT = ROOT / "research/ftmo_survivors_book/results"
FIG = ROOT / "research/ftmo_survivors_book/figures"; FIG.mkdir(parents=True, exist_ok=True)
rep = json.load(open(OUT / "book_results.json"))
books = rep["books"]
HB = [k for k in books if k.startswith("HONEST")][0]

# ---- p(pass) table CSV (all books) ----
rows = []
for bname, b in books.items():
    for cell, v in b["ppass_table"].items():
        win, hz = cell.split("_")
        rows.append({"book": bname, "Lstar_IS": b["Lstar_fixed_on_IS"], "window": win,
                     "horizon": hz, "p_pass": v["p"], "ci90_lo": v["ci90"][0], "ci90_hi": v["ci90"][1]})
tab = pd.DataFrame(rows)
tab.to_csv(OUT / "ppass_table.csv", index=False)
print(tab.to_string(index=False))

# ---- figure ----
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
Ls = [1.5, 2.0, 2.5, 3.0, 3.5]
colors = {HB: "C3", "optimistic_swapFREE_TSMOM": "C0", "swapnet_crypto0_TSMOM": "C1",
          "incl_C_show(RH+TSMOMnet+C)": "C2"}
for bname, b in books.items():
    sw = b["leverage_sweep"]
    y = [sw[str(L)]["OOS_12mo"] for L in Ls]
    yi = [sw[str(L)]["IS_12mo"] for L in Ls]
    c = colors.get(bname, "grey")
    ax[0].plot(Ls, y, "-o", color=c, label=f"{bname[:26]} OOS")
    ax[0].plot(Ls, yi, "--", color=c, alpha=0.5)
    Ls_star = b["Lstar_fixed_on_IS"]
    ax[0].axvline(Ls_star, color=c, ls=":", alpha=0.4)
ax[0].axhline(0.5, color="k", lw=1, ls="--", label="0.50 bar")
ax[0].set_xlabel("leverage L"); ax[0].set_ylabel("p(pass<=12mo)")
ax[0].set_title("Leverage sweep (solid=OOS, dashed=IS; dotted=L* fixed on IS)")
ax[0].legend(fontsize=6.5); ax[0].grid(alpha=0.3)

# CI bar chart for honest book
b = books[HB]; cells = ["IS_6mo", "IS_12mo", "OOS_6mo", "OOS_12mo"]
xs = np.arange(len(cells)); p = [b["ppass_table"][c]["p"] for c in cells]
lo = [b["ppass_table"][c]["p"] - b["ppass_table"][c]["ci90"][0] for c in cells]
hi = [b["ppass_table"][c]["ci90"][1] - b["ppass_table"][c]["p"] for c in cells]
ax[1].bar(xs, p, color=["C7", "C7", "C3", "C3"], alpha=0.8)
ax[1].errorbar(xs, p, yerr=[lo, hi], fmt="none", ecolor="k", capsize=5)
ax[1].axhline(0.5, color="k", lw=1, ls="--")
ax[1].set_xticks(xs); ax[1].set_xticklabels(cells)
ax[1].set_ylabel("p(pass)"); ax[1].set_ylim(0, 0.9)
ax[1].set_title(f"HONEST book p(pass) +/- 90% CI  (L*={b['Lstar_fixed_on_IS']}, IS-fixed)")
for x, pv in zip(xs, p):
    ax[1].text(x, pv + 0.02, f"{pv:.2f}", ha="center", fontsize=9)
ax[1].grid(alpha=0.3, axis="y")
plt.tight_layout(); plt.savefig(FIG / "survivors_ppass.png", dpi=110)
print(f"\nwrote {FIG/'survivors_ppass.png'} and {OUT/'ppass_table.csv'}")
print(f"\nHONEST book = {HB}")
print(f"  OOS 6mo  p(pass)={b['ppass_table']['OOS_6mo']['p']}  CI{b['ppass_table']['OOS_6mo']['ci90']}")
print(f"  OOS 12mo p(pass)={b['ppass_table']['OOS_12mo']['p']}  CI{b['ppass_table']['OOS_12mo']['ci90']}")
