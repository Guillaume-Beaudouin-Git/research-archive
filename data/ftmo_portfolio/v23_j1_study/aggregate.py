"""v2.3 J1 study — paired aggregation, CIs, decision evaluation.

Usage: python3 aggregate.py [--val 1204] [--arms baseline,A_raw,...]
Pairing: per-cohort deltas vs baseline; circular block bootstrap (block=10 cohorts,
3000 draws, seed 23 — v2.1 convention). CIs at 90% (decision) and 95% (comparability).
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB = HERE / "tables"
REC = HERE / "records"
FEE = 96.0

args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
# v2.2 contractual funded value (PORTFOLIOS_v2.2.md: VAL = $96 + 0.8 x $1,658 = $1,422)
VAL = float(args.get("--val", 1422.0))
print(f"EV convention: VAL=${VAL:.0f} (v2.2 contractual), FEE=${FEE:.0f}")

ARMS = args.get("--arms", "A_raw,A_iso,B_raw,B_iso,C_raw,C_iso").split(",")
ARMS = [a for a in ARMS if (TAB / f"cohorts_{a}.csv").exists()]
print(f"arms found: {ARMS}")

base = pd.read_csv(TAB / "cohorts_baseline.csv", parse_dates=["start"]).sort_values("cohort")
n = len(base)


def neff(d):
    """v2.2 battery convention: autocorrelation ESS on the funded vector."""
    y = d.sort_values("start").funded.to_numpy(float)
    ac = [pd.Series(y).autocorr(k) for k in range(1, 14)]
    return len(y) / (1 + 2 * sum(max(a, 0) for a in ac if np.isfinite(a)))


N_EFF = neff(base)

rng = np.random.default_rng(23)
B = 10
_IDX = []
for _ in range(3000):
    ix = []
    while len(ix) < n:
        s = rng.integers(0, n)
        ix.extend(((s + np.arange(B)) % n).tolist())
    _IDX.append(np.array(ix[:n]))


def boot_ci(delta):
    """Mean + percentile CIs of a per-cohort delta vector (paired, circular blocks)."""
    delta = np.asarray(delta, float)
    boots = np.array([delta[ix].mean() for ix in _IDX])
    return dict(mean=float(delta.mean()),
                lo90=float(np.percentile(boots, 5)), hi90=float(np.percentile(boots, 95)),
                lo95=float(np.percentile(boots, 2.5)), hi95=float(np.percentile(boots, 97.5)))


def cohort_metrics(arm):
    d = pd.read_csv(TAB / f"cohorts_{arm}.csv", parse_dates=["start"]).sort_values("cohort")
    att = pd.read_csv(TAB / f"attempts_{arm}.csv")
    ev = REC / f"{arm}_events.csv"
    ev = pd.read_csv(ev) if ev.stat().st_size > 5 else pd.DataFrame(
        columns=["cohort", "gap_day", "gap_pnl_jpy", "kind", "weekday"])
    busts = att[att.out.isin(["bust_daily", "bust_floor"])]
    bc = busts.groupby("cohort").size()
    d["bust_n"] = d.cohort.map(bc).fillna(0.0)
    if len(ev):
        mb = ev[ev.gap_day].groupby("cohort").size()
        gj = ev[ev.gap_day].groupby("cohort").gap_pnl_jpy.sum()
    else:
        mb = pd.Series(dtype=float); gj = pd.Series(dtype=float)
    d["monday_busts"] = d.cohort.map(mb).fillna(0.0)
    d["j1_gap_pnl"] = d.cohort.map(gj).fillna(0.0)
    d["evc"] = d.funded * VAL - d.attempts * FEE
    return d, att, ev


base_m, base_att, base_ev = cohort_metrics("baseline")
assert (base_m.cohort.values == base.cohort.values).all()

summary, deltas, decisions = [], [], []
for arm in ["baseline"] + ARMS:
    d, att, ev = cohort_metrics(arm)
    assert (d.cohort.values == base_m.cohort.values).all(), f"cohort grid mismatch {arm}"
    days = pd.read_parquet(REC / f"{arm}_days.parquet")
    book = days[["gold", "jpy", "on_us", "on_ger"]].sum(axis=1) + days.orb + days.micro + days.fix
    var_b = book.var()
    shares = {f"risk_{k}": float(np.cov(days[k], book)[0, 1] / var_b)
              for k in ["gold", "jpy", "on_us", "on_ger"]}
    mg = pd.read_parquet(REC / f"{arm}_margins.parquet")
    s = dict(arm=arm, n=n, N_eff=round(N_EFF, 1),
             p_pooled=d.funded.mean(), p_IS=d[d.win == "IS"].funded.mean(),
             p_OOS=d[d.win == "OOS"].funded.mean(),
             attempts=d.attempts.mean(),
             med_t=float(d.loc[d.funded, "t"].median()),
             EV=d.funded.mean() * VAL - d.attempts.mean() * FEE,
             bust_per_cohort=d.bust_n.mean(),
             bust_share_att=len(att[att.out.isin(["bust_daily", "bust_floor"])]) / max(len(att), 1),
             monday_busts_per_cohort=d.monday_busts.mean(),
             j1_gap_pnl_per_cohort=d.j1_gap_pnl.mean(),
             margin_p50=float(mg.need.quantile(0.50)), margin_p99=float(mg.need.quantile(0.99)),
             margin_bind=float(mg.bind.mean()),
             j1_turn_day=float(days.turn_jpy.mean()), j1_cost_day=float(days.cost_jpy.mean()),
             j1_drift_day=float(days.jpy.mean()), book_drift_day=float(book.mean()),
             book_vol_day=float(book.std()),
             **shares)
    summary.append(s)
    if arm == "baseline":
        continue
    dp = boot_ci(d.funded.values.astype(float) - base_m.funded.values.astype(float))
    dev = boot_ci(d.evc.values - base_m.evc.values)
    dbust = boot_ci(d.bust_n.values - base_m.bust_n.values)
    dmon = boot_ci(d.monday_busts.values - base_m.monday_busts.values)
    dgap = boot_ci(d.j1_gap_pnl.values - base_m.j1_gap_pnl.values)
    row = dict(arm=arm,
               dp=dp["mean"], dp_lo90=dp["lo90"], dp_hi90=dp["hi90"],
               dp_lo95=dp["lo95"], dp_hi95=dp["hi95"],
               dp_IS=d[d.win == "IS"].funded.mean() - base_m[base_m.win == "IS"].funded.mean(),
               dp_OOS=d[d.win == "OOS"].funded.mean() - base_m[base_m.win == "OOS"].funded.mean(),
               dEV=dev["mean"], dEV_lo90=dev["lo90"], dEV_hi90=dev["hi90"],
               dEV_lo95=dev["lo95"], dEV_hi95=dev["hi95"],
               d_att=d.attempts.mean() - base_m.attempts.mean(),
               d_med_t=float(d.loc[d.funded, "t"].median()
                             - base_m.loc[base_m.funded, "t"].median()),
               dbust=dbust["mean"], dbust_lo90=dbust["lo90"], dbust_hi90=dbust["hi90"],
               dmonday=dmon["mean"], dmonday_lo90=dmon["lo90"], dmonday_hi90=dmon["hi90"],
               dj1gap=dgap["mean"], dj1gap_lo90=dgap["lo90"], dj1gap_hi90=dgap["hi90"])
    deltas.append(row)
    gate = (dp["lo90"] > 0) or (dev["lo90"] > 0)
    bust_adverse = dbust["lo90"] > 0
    monday_adverse = (dmon["lo90"] > 0) or (dgap["hi90"] < 0)
    decisions.append(dict(arm=arm, gate_pass=bool(gate),
                          bust_adverse=bool(bust_adverse),
                          monday_adverse=bool(monday_adverse),
                          qualifies=bool(gate and not bust_adverse and not monday_adverse),
                          dEV=dev["mean"], dp=dp["mean"]))

S = pd.DataFrame(summary)
D = pd.DataFrame(deltas)
S.to_csv(TAB / "summary_arms.csv", index=False)
D.to_csv(TAB / "paired_deltas.csv", index=False)

# B-iso necessity check (pre-registered): FACT_B from measured day-record book vols
if (REC / "B_raw_days.parquet").exists():
    vb = S.loc[S.arm == "baseline", "book_vol_day"].iloc[0]
    vB = S.loc[S.arm == "B_raw", "book_vol_day"]
    if len(vB):
        FACT_B = float(vb / vB.iloc[0])
        need_iso = abs(FACT_B - 1.0) > 0.01
        print(f"FACT_B (measured) = {FACT_B:.4f} -> B_iso "
              f"{'REQUIRED (run it)' if need_iso else '== B_raw (declared, pre-registered rule)'}")
        f = json.loads((HERE / "factors.json").read_text())
        f["FACT_B_measured"] = FACT_B
        f["B_iso_distinct_run"] = bool(need_iso)
        (HERE / "factors.json").write_text(json.dumps(f, indent=2))

qual = [r for r in decisions if r["qualifies"]]
if qual:
    best = sorted(qual, key=lambda r: (-r["dEV"], -r["dp"]))[0]
    verdict = dict(verdict="ADOPT", best=best["arm"], decisions=decisions, VAL=VAL)
else:
    verdict = dict(verdict="NULL — J1 stays", best=None, decisions=decisions, VAL=VAL)
(TAB / "decision.json").write_text(json.dumps(verdict, indent=2))

pd.set_option("display.width", 250)
print(S.round(4).to_string(index=False))
print()
print(D.round(4).to_string(index=False))
print()
print(json.dumps(verdict, indent=2))
