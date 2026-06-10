"""Tornado plot — Δp pooled (pp) per arm with 90%/95% paired block-bootstrap CIs."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
PLOTS = HERE / "plots"; PLOTS.mkdir(exist_ok=True)
D = pd.read_csv(HERE / "tables" / "paired_deltas.csv").sort_values("dp")

fig, ax = plt.subplots(figsize=(9, 0.7 * len(D) + 2))
y = range(len(D))
ax.barh(y, D.dp * 100, color=["#b22222" if v < 0 else "#2e7d32" for v in D.dp],
        alpha=0.55, zorder=2)
ax.errorbar(D.dp * 100, y, xerr=[(D.dp - D.dp_lo95) * 100, (D.dp_hi95 - D.dp) * 100],
            fmt="none", ecolor="#9e9e9e", elinewidth=1.2, capsize=3, zorder=3,
            label="95% CI")
ax.errorbar(D.dp * 100, y, xerr=[(D.dp - D.dp_lo90) * 100, (D.dp_hi90 - D.dp) * 100],
            fmt="none", ecolor="#212121", elinewidth=2.6, capsize=5, zorder=4,
            label="90% CI (decision)")
for yi, (_, r) in zip(y, D.iterrows()):
    ax.annotate(f"ΔEV {r.dEV:+.0f}$", (max(r.dp_hi95 * 100, r.dp * 100) + 0.4, yi),
                va="center", fontsize=9, color="#37474f")
ax.axvline(0, color="k", lw=0.8)
ax.set_yticks(list(y)); ax.set_yticklabels(D.arm)
ax.set_xlabel("Δ p(funded ≤91j) vs v2.2 baseline, points de %")
ax.set_title("v2.3 J1 study — paired LOO deltas on the frozen v2.2 book")
ax.legend(loc="lower right", fontsize=9)
ax.grid(axis="x", alpha=0.25, zorder=1)
fig.tight_layout()
fig.savefig(PLOTS / "tornado.png", dpi=150)
print(f"saved {PLOTS/'tornado.png'}")
