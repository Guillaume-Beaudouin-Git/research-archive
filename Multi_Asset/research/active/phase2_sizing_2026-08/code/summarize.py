"""Render the decision tables as markdown, straight from the CSVs."""
import numpy as np
import pandas as pd

import p2_lib as L

g = pd.read_csv(L.TAB / "grid_phase2.csv")
VMS = sorted(g.vm_spec.unique())
WKS = sorted(g.weeks.unique())


def pv(val, fmt="{:.1f}", scale=100.0):
    p = g.pivot(index="weeks", columns="vm_spec", values=val) * scale
    return p.map(lambda x: fmt.format(x) if np.isfinite(x) else "--")


def md(p, label):
    head = "| " + label + " | " + " | ".join(f"**{v}**" if v == 14 else str(v)
                                             for v in p.columns) + " |"
    sep = "|---" * (len(p.columns) + 1) + "|"
    body = "\n".join("| " + (f"**{i}**" if i in (2, 5) else str(i)) + " | "
                     + " | ".join(p.loc[i]) + " |" for i in p.index)
    return "\n".join([head, sep, body])


print("### p(pass) REAL — %\n")
print(md(pv("p_pass"), "weeks \\ vm"))
print("\n### p(pass) PLACEBO (matched-persistence sign null, same horizon) — %\n")
print(md(pv("p_placebo"), "weeks \\ vm"))
print("\n### EDGE = real - placebo, pt  (paired block bootstrap CI95)\n")
e = g.copy()
e["cell"] = e.apply(
    lambda r: f"{100*r.edge:+.1f} [{100*r.edge_lo:+.1f},{100*r.edge_hi:+.1f}]"
              + ("!" if abs(r.edge) < r.mde80 else ""), axis=1)
p = e.pivot(index="weeks", columns="vm_spec", values="cell")
print(md(p, "weeks \\ vm"))
print("\n(`!` = |edge| below MDE80 -> UNDERPOWERED cell)\n")

print("\n### p(pass) CI95 (block bootstrap over cohorts) — %\n")
e["cell"] = e.apply(lambda r: f"{100*r.p_pass:.1f} [{100*r.ci_lo:.1f},{100*r.ci_hi:.1f}]",
                    axis=1)
print(md(e.pivot(index="weeks", columns="vm_spec", values="cell"), "weeks \\ vm"))

print("\n### median / p90 calendar days to pass, CONDITIONAL on passing\n")
e["cell"] = e.apply(lambda r: ("--" if not np.isfinite(r.med_cal)
                               else f"{r.med_cal:.0f} / {r.p90_cal:.0f}"), axis=1)
print(md(e.pivot(index="weeks", columns="vm_spec", values="cell"), "weeks \\ vm"))

for lab, col in (("daily barrier (-5 %)", "p_daily"),
                 ("static floor (-10 %)", "p_floor"),
                 ("abandon (5 EOD in the 2 % band)", "p_abandon"),
                 ("NOT REACHED inside the horizon", "p_not_reached")):
    print(f"\n### deaths: {lab} — %\n")
    print(md(pv(col), "weeks \\ vm"))

print("\n### post-2021 era only — p(pass) %  (n = "
      f"{int(g.n_post21.iloc[0])} cohorts)\n")
print(md(pv("p_pass_post21"), "weeks \\ vm"))
print("\n### full-sample minus post-2021, pt\n")
d = (g.pivot(index="weeks", columns="vm_spec", values="p_pass")
     - g.pivot(index="weeks", columns="vm_spec", values="p_pass_post21")) * 100
print(md(d.map(lambda x: f"{x:+.1f}"), "weeks \\ vm"))

print("\n### cross-check: cleanroom + fix_deadlock (no micro-ORB) minus deployed, pt\n")
d = (g.pivot(index="weeks", columns="vm_spec", values="p_pass_cleanroom")
     - g.pivot(index="weeks", columns="vm_spec", values="p_pass")) * 100
print(md(d.map(lambda x: f"{x:+.1f}"), "weeks \\ vm"))

print("\n### marginal p(pass) of one more week, pt — REAL / PLACEBO\n")
r = g.pivot(index="weeks", columns="vm_spec", values="p_pass").diff() * 100
q = g.pivot(index="weeks", columns="vm_spec", values="p_placebo").diff() * 100
cell = r.copy()
for i in r.index:
    for c in r.columns:
        cell.loc[i, c] = ("--" if not np.isfinite(r.loc[i, c])
                          else f"{r.loc[i,c]:+.1f}/{q.loc[i,c]:+.1f}")
print(md(cell, "weeks \\ vm"))
