"""TEST 1b — DSR data-driven : dispersion du SR de la MEME regle a travers la
grille calendaire (weekday x week-rank), 2023+, pre<0, 08:00->11:59, net@11.9bps.
C'est le DOF 'jour retenu' que TEST 1.2 exige de compter, mesure sur donnees."""
import numpy as np, pandas as pd
from scipy.stats import norm, skew, kurtosis
from pathlib import Path

ROOT = Path("<HOME>/Desktop/Algo_claude")
COST = 0.00119
daily = pd.read_parquet(ROOT / "outputs/audit_month_end/data/daily_features.parquet")
daily.index = pd.to_datetime(daily.index)
d = daily.dropna(subset=["o04", "o08", "c1159", "low_min"]).copy()
d["pre"] = d.o08 / d.o04 - 1
d["net"] = d.c1159 / d.o08 - 1 - COST
d["dow"] = d.index.dayofweek          # Mon=0..Sun=6
d["ym"] = d.index.year * 100 + d.index.month
# week-rank of this weekday within its month (1st,2nd,... of that dow); and is-last
d["wk_rank"] = d.groupby(["ym", "dow"]).cumcount() + 1
d["wk_last"] = d.groupby(["ym", "dow"])["wk_rank"].transform("max") == d["wk_rank"]
d23 = d[(d.index.year >= 2023) & (d.pre < 0)].copy()

DOW = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri"}
cells = []
print("=== calendar grid (2023+, pre<0, same rule) — per-trade SR ===")
for dow in range(5):
    for rank_label, sel in [("1st", d23[(d23.dow == dow) & (d23.wk_rank == 1)]),
                            ("2nd", d23[(d23.dow == dow) & (d23.wk_rank == 2)]),
                            ("3rd", d23[(d23.dow == dow) & (d23.wk_rank == 3)]),
                            ("4th", d23[(d23.dow == dow) & (d23.wk_rank == 4)]),
                            ("last", d23[(d23.dow == dow) & (d23.wk_last)])]:
        x = sel.net.values
        if len(x) >= 5:
            sr = x.mean() / x.std(ddof=1)
            cells.append((f"{DOW[dow]}-{rank_label}", len(x), x.mean(), sr))
sr_grid = np.array([c[3] for c in cells])
for nm, n, m, sr in sorted(cells, key=lambda c: -c[3]):
    star = "  <-- SURVIVOR" if nm == "Fri-last" else ""
    print(f"  {nm:10s} N={n:3d} mean={m*100:+.3f}% SR={sr:+.4f}{star}")

surv = d23[(d23.dow == 4) & (d23.wk_last)].net.values
SR_obs = surv.mean() / surv.std(ddof=1)
g3 = float(skew(surv, bias=False)); g4 = float(kurtosis(surv, fisher=False, bias=False))
sd_grid = sr_grid.std(ddof=1)
n_cells = len(cells)
print(f"\ncells={n_cells}  sd(SR across cells)={sd_grid:.4f}  SR_obs(Fri-last)={SR_obs:.4f}")
print(f"survivor rank among cells: {int((sr_grid > SR_obs).sum())+1} / {n_cells}")


def dsr(SR_obs, sd_t, Nt, T, g3, g4):
    gamma = 0.5772156649
    z1 = norm.ppf(1 - 1.0 / Nt); z2 = norm.ppf(1 - 1.0 / (Nt * np.e))
    SR0 = sd_t * ((1 - gamma) * z1 + gamma * z2)
    denom = np.sqrt(1 - g3 * SR_obs + (g4 - 1) / 4.0 * SR_obs**2)
    return norm.cdf((SR_obs - SR0) * np.sqrt(T - 1) / denom), SR0


print("\n[DSR with EMPIRICAL calendar-grid dispersion]")
for Nt in [n_cells, n_cells * 3, 40]:   # x3 ~ (regime {full/2023+/pre22}) DOF; 40 ~ + window/horizon
    dd, sr0 = dsr(SR_obs, sd_grid, Nt, len(surv), g3, g4)
    print(f"  N_trials={Nt:3d}: SR0={sr0:.4f}  DSR={dd:.4f}")

# placebo: how many of the 25 raw cells (no min-N filter) beat survivor mean?
print("\n[cross-check] mean net by cell incl small-N (for TEST3 context):")
for dow in [3, 4]:  # Thu, Fri
    for rk in ["1st", "2nd", "3rd", "4th", "last"]:
        if rk == "last":
            sel = d23[(d23.dow == dow) & (d23.wk_last)]
        else:
            sel = d23[(d23.dow == dow) & (d23.wk_rank == {"1st":1,"2nd":2,"3rd":3,"4th":4}[rk])]
        if len(sel):
            print(f"  {DOW[dow]}-{rk:4s} N={len(sel):3d} mean={sel.net.mean()*100:+.3f}% t={sel.net.mean()/(sel.net.std(ddof=1)/np.sqrt(len(sel))):+.2f}")
