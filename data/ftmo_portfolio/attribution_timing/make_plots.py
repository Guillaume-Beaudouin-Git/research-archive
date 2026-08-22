"""Plots: weights time-series, waterfall, LOO tornado, p-by-start-bucket."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
TAB = HERE / "tables"
PLOTS = HERE / "plots"; PLOTS.mkdir(exist_ok=True)
SLEEVES = dict(gold=["gold"], jpy=["jpy"], overnight=["on_us", "on_ger"], orb=["orb"])
COL = dict(gold="#C9A227", jpy="#4477AA", overnight="#AA3377", orb="#228833")

df = pd.read_parquet(HERE / "baseline_day_records.parquet")
df["overnight"] = df.on_us + df.on_ger
df["total"] = df[["gold", "jpy", "on_us", "on_ger", "orb", "fix"]].sum(axis=1)

# --- 1. rolling realized risk shares (by calendar date, 126d window) ---
by_date = df.groupby("date")[["gold", "jpy", "overnight", "orb", "total"]].mean()
fig, ax = plt.subplots(figsize=(11, 4.5))
roll_var = by_date.total.rolling(126).var()
for s in ("gold", "jpy", "overnight", "orb"):
    share = by_date[s].rolling(126).cov(by_date.total) / roll_var
    ax.plot(by_date.index, share, label=s, color=COL[s], lw=1.2)
ax.axhline(0, color="k", lw=0.5)
ax.set_title("Realized risk share (126d rolling cov/var of book daily P&L, cohort-averaged)")
ax.set_ylabel("share of book variance"); ax.legend(ncol=4); ax.set_ylim(-0.3, 1.1)
fig.tight_layout(); fig.savefig(PLOTS / "p1_risk_shares_ts.png", dpi=130)

# --- 2. waterfall: cohort-level mean P&L by sleeve, funded vs not (pooled) ---
coh = pd.read_csv(TAB / "cohort_outcomes_baseline.csv")
cg = df.groupby("cohort")[["gold", "jpy", "overnight", "orb"]].sum()
cg = cg.merge(coh.set_index("cohort")[["funded"]], left_index=True, right_index=True)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, fl, ttl in ((axes[0], True, "FUNDED cohorts"),
                    (axes[1], False, "NOT-FUNDED cohorts")):
    m = cg[cg.funded == fl][["gold", "jpy", "overnight", "orb"]].mean()
    cum = 0
    for s in ("gold", "jpy", "overnight", "orb"):
        ax.bar(s, m[s], bottom=cum if m[s] > 0 else cum + m[s],
               color=COL[s], alpha=0.85)
        cum += m[s]
    ax.bar("TOTAL", m.sum(), color="#666666")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_title(f"{ttl} (n={int((cg.funded == fl).sum())})")
    ax.set_ylabel("mean cumulative P&L per cohort ($)")
fig.suptitle("P&L waterfall by sleeve — pooled 2013-2026, all attempts")
fig.tight_layout(); fig.savefig(PLOTS / "p2_waterfall.png", dpi=130)

# --- 3. LOO tornado with CIs ---
cf = pd.read_csv(TAB / "p2_counterfactuals.csv")
loo = cf[cf.arm.str.startswith("loo")].copy()
loo["lbl"] = loo.arm.str.replace("loo_", "")
loo = loo.sort_values("dp")
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ypos = np.arange(len(loo))
ax.barh(ypos, loo.dp * 100, color=["#AA3377" if "on" in a else
                                   "#C9A227" if "gold" in a else
                                   "#4477AA" if "jpy" in a else "#228833"
                                   for a in loo.arm], alpha=0.8)
ax.errorbar(loo.dp * 100, ypos,
            xerr=[(loo.dp - loo.dp_lo) * 100, (loo.dp_hi - loo.dp) * 100],
            fmt="none", ecolor="k", capsize=3, lw=1)
ax.set_yticks(ypos); ax.set_yticklabels(loo.lbl)
ax.axvline(0, color="k", lw=0.8)
ax.set_xlabel("Δ p(funded ≤91d) vs baseline, pts (paired, block-bootstrap CI95)")
ax.set_title("Leave-one-out — pooled 2013-2026 (baseline 84.6%)")
fig.tight_layout(); fig.savefig(PLOTS / "p2_loo_tornado.png", dpi=130)

# --- 4. p by start bucket with CIs ---
if not (TAB / "p3_buckets.csv").exists():
    print("p3_buckets.csv not ready — skipping plot 4")
    sys.exit(0)
bk = pd.read_csv(TAB / "p3_buckets.csv")
fig, ax = plt.subplots(figsize=(13, 5))
x = np.arange(len(bk))
colors = {"H1": "#4477AA", "H2": "#EE6677", "H3": "#228833",
          "H4": "#C9A227", "H5": "#BBBBBB"}
ax.bar(x, bk.p * 100, color=[colors[h] for h in bk.hyp], alpha=0.85)
ax.errorbar(x, bk.p * 100, yerr=[(bk.p - bk.ci_lo) * 100, (bk.ci_hi - bk.p) * 100],
            fmt="none", ecolor="k", capsize=2, lw=0.8)
p_all = pd.read_csv(TAB / "p3_step1_cohorts.csv").funded.mean()
ax.axhline(p_all * 100, color="k", ls="--", lw=1,
           label=f"unconditional {p_all*100:.1f}%")
ax.set_xticks(x)
ax.set_xticklabels(bk.bucket.str.replace("wd=", "").str
                   .replace("month=", "m").str.replace("_week", "wk"),
                   rotation=70, fontsize=7)
ax.set_ylabel("p(funded ≤91d) %")
ax.set_title("Start-timing buckets H1-H5 (block-bootstrap CI95) — "
             "deflation bar for best bucket: 2.57σ")
ax.legend()
fig.tight_layout(); fig.savefig(PLOTS / "p3_start_buckets.png", dpi=130)
print("plots saved:", [p.name for p in PLOTS.glob("*.png")])
