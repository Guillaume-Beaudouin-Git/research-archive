"""finalize.py — side-by-side p(pass) table (report vs independent) + figures."""
from __future__ import annotations
import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from audit_common import ROOT
import firstpassage as fp

R = ROOT / "research/ftmo_portfolio_audit/results"
F = ROOT / "research/ftmo_portfolio_audit/figures"
F.mkdir(parents=True, exist_ok=True)

g0 = json.load(open(R / "gate0_results.json"))

# ---- side-by-side table ----
report = {
    ("full", 63): 0.485, ("full", 126): 0.580, ("full", 189): 0.531,
    ("oos", 63): 0.549, ("oos", 126): 0.55, ("oos", 189): 0.531,
}
rows = []
for win, key in [("full", "reportSharpe_full_L2.5"), ("oos", "reportSharpe_oos_L2.5"),
                 ("full", "steelman_full_L2.5"), ("oos", "steelman_oos_L2.5")]:
    cc = g0[key]["corrected_cdf"]; au = g0[key]["author_method"]
    for H, mo in [(63, 3), (126, 6), (189, 9)]:
        rep = report.get((win, H), np.nan) if "reportSharpe" in key else np.nan
        rows.append({
            "scenario": key, "window": win, "horizon_mo": mo,
            "REPORT_ppass": rep,
            "indep_author_method": round(au[str(mo)]["mean"], 3),
            "indep_corrected": round(cc[str(H)]["mean"], 3),
            "indep_corrected_ci90": f"[{cc[str(H)]['ci90'][0]:.3f},{cc[str(H)]['ci90'][1]:.3f}]",
        })
tab = pd.DataFrame(rows)
tab.to_csv(R / "ppass_sidebyside.csv", index=False)
print(tab.to_string(index=False))

# outer-resample honest CI at 3mo (the wide one)
print("\nHonest outer-resample 90% CI on p(pass<=3mo):")
for k in ["reportSharpe_oos_L2.5", "reportSharpe_full_L3.0", "steelman_full_L2.5"]:
    o = g0[k]["outer_resample_3mo"]
    print(f"  {k:26s} mean={o['mean']:.3f} 90%CI=[{o['ci90'][0]:.3f},{o['ci90'][1]:.3f}]")

# ---- figure 1: CDF monotone (mine) vs report published points ----
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
H_grid = [63, 126, 189, 252]
for key, lab, col in [("reportSharpe_oos_L2.5", "indep corrected (reportSharpe1.39,OOS,L2.5)", "C0"),
                      ("steelman_full_L2.5", "indep corrected (steelman,full,L2.5)", "C1")]:
    cc = g0[key]["corrected_cdf"]
    y = [cc[str(h)]["mean"] for h in H_grid]
    lo = [cc[str(h)]["ci90"][0] for h in H_grid]
    hi = [cc[str(h)]["ci90"][1] for h in H_grid]
    ax[0].plot([h / 21 for h in H_grid], y, "-o", color=col, label=lab)
    ax[0].fill_between([h / 21 for h in H_grid], lo, hi, color=col, alpha=0.15)
ax[0].plot([3, 6, 9], [0.485, 0.580, 0.531], "ks--", label="REPORT full (NON-MONOTONE)")
ax[0].plot([3, 6, 9], [0.549, 0.55, 0.531], "k^:", label="REPORT OOS")
ax[0].axhline(0.5, color="grey", lw=0.8, ls=":")
ax[0].set_xlabel("horizon (months)"); ax[0].set_ylabel("p(pass)")
ax[0].set_title("p(pass) CDF: independent monotone vs report's published points")
ax[0].legend(fontsize=7); ax[0].grid(alpha=0.3)

# ---- figure 2: leverage curve ----
gC = json.load(open(R / "gate_BCG_results.json"))["gate_C"]
Ls = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
for nm, col in [("steel_full", "C1"), ("repSh_full", "C0"), ("repSh_oos", "C2")]:
    y = [gC[str(L)][nm]["corrected_3mo"] for L in Ls]
    ya = [gC[str(L)][nm]["author_3mo"] for L in Ls]
    ax[1].plot(Ls, y, "-o", color=col, label=f"{nm} (corrected)")
    ax[1].plot(Ls, ya, "--", color=col, alpha=0.6, label=f"{nm} (author method)")
ax[1].axhline(0.549, color="k", ls="--", lw=1, label="report claim 0.549")
ax[1].axhline(0.5, color="grey", lw=0.8, ls=":")
ax[1].axvspan(2.5, 3.0, color="orange", alpha=0.12, label="report L=2.5-3")
ax[1].set_xlabel("portfolio leverage L"); ax[1].set_ylabel("p(pass<=3mo)")
ax[1].set_title("Gate C: leverage sensitivity of p(pass<=3mo)")
ax[1].legend(fontsize=7); ax[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig(F / "ppass_audit.png", dpi=110)
print(f"\nwrote {F/'ppass_audit.png'} and {R/'ppass_sidebyside.csv'}")
