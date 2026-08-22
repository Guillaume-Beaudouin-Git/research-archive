"""Aggregate Module 1 per-strategy results into a master table + report figures."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from engine import data  # noqa: E402
from strategies import STRATEGIES  # noqa: E402

RESULTS = HERE / "results"
names = list(STRATEGIES)

# ---- master summary table ----
rows = [json.load(open(RESULTS / f"{n}_port.json")) for n in names]
cols = ["strategy", "total_trades", "trades_per_pair_per_year", "expectancy_gross_bps",
        "expectancy_net_bps", "port_sharpe_gross", "port_sharpe_net", "port_hac_t_net",
        "median_pair_sharpe_net", "frac_pairs_positive_net", "best_pair",
        "best_pair_sharpe_net", "port_maxdd", "port_total_return", "port_dsr",
        "port_bootstrap_p", "wf_score"]
master = pd.DataFrame(rows)[cols]
master.to_csv(RESULTS / "module1_summary.csv", index=False)
pd.set_option("display.width", 200, "display.max_columns", 30)
print(master.to_string(index=False))

# ---- per-pair net Sharpe matrix ----
mats = {n: pd.read_csv(RESULTS / f"{n}_pairs.csv").set_index("pair")["sharpe"] for n in names}
shm = pd.DataFrame(mats).T
shm = shm[sorted(shm.columns)]
shm.to_csv(RESULTS / "module1_pair_sharpe_matrix.csv")

# Figure A — heatmap
fig, ax = plt.subplots(figsize=(13, 3.4))
im = ax.imshow(shm.values, aspect="auto", cmap="RdYlGn", vmin=-3, vmax=3)
ax.set_xticks(range(len(shm.columns)))
ax.set_xticklabels([c.replace("USDT", "") for c in shm.columns], rotation=45, ha="right", fontsize=8)
ax.set_yticks(range(len(shm.index)))
ax.set_yticklabels([s.replace("_", " ") for s in shm.index], fontsize=9)
for i in range(shm.shape[0]):
    for j in range(shm.shape[1]):
        ax.text(j, i, f"{shm.values[i, j]:.1f}", ha="center", va="center", fontsize=6)
ax.set_title("Module 1 — net annualised Sharpe by strategy × instrument (5m, 0.17% round-trip)")
fig.colorbar(im, ax=ax, label="Sharpe (net)")
fig.tight_layout()
fig.savefig(RESULTS / "fig_A_sharpe_heatmap.png", dpi=120)
plt.close(fig)

# ---- equal-weight buy & hold daily ----
bh = []
for pair in data.UNIVERSE:
    df = data.load_crypto(pair)
    bh.append(df["close"].groupby(df.index.normalize()).last().pct_change())
bh_cum = pd.concat(bh, axis=1).mean(axis=1, skipna=True).fillna(0).cumsum()

# Figure B — cumulative net P&L all strategies vs EW buy & hold
fig, ax = plt.subplots(figsize=(11, 5))
for n in names:
    s = pd.read_parquet(RESULTS / f"{n}_portdaily.parquet")["port_daily"]
    ax.plot(s.index, s.fillna(0).cumsum() * 100, lw=1.2, label=n.replace("_", " "))
ax.plot(bh_cum.index, bh_cum.values * 100, lw=1.8, color="black", ls="--", label="EW buy & hold (18 coins)")
ax.axhline(0, color="gray", lw=0.8)
ax.set_title("Module 1 — cumulative net P&L (additive, fixed notional), 2021–2026")
ax.set_ylabel("Cumulative return (%)")
ax.legend(loc="lower left", fontsize=8)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(RESULTS / "fig_B_cumulative_pnl.png", dpi=120)
plt.close(fig)

# Figure C — headline S5 gross vs net
n = "S5_vwma_buy_dip"
g = pd.read_parquet(RESULTS / f"{n}_portgross.parquet")["port_gross"]
nt = pd.read_parquet(RESULTS / f"{n}_portdaily.parquet")["port_daily"]
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(g.index, g.fillna(0).cumsum() * 100, lw=1.5, color="steelblue", label="gross (cost = 0)")
ax.plot(nt.index, nt.fillna(0).cumsum() * 100, lw=1.5, color="crimson", label="net (0.17% round-trip)")
ax.axhline(0, color="gray", lw=0.8)
ax.set_title("Module 1 — S5 'VWMA buy-the-dip' (video headline +5,381%): gross vs net, EW across 18 coins")
ax.set_ylabel("Cumulative return (%)")
ax.legend(loc="best")
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(RESULTS / "fig_C_s5_gross_net.png", dpi=120)
plt.close(fig)
print("figures written:", [p.name for p in sorted(RESULTS.glob('fig_*.png'))])
