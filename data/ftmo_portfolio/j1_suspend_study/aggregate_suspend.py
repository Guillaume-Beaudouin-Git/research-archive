"""J1 suspension study — paired aggregation, CIs, tail, decision (PREREGISTRATION.md).

Pairing: per-cohort deltas vs baseline; circular block bootstrap (block=10 cohorts, 3000 draws,
seed=23 — v2.1/levcap convention). CI 90% (decision) + 95% (comparability).
Decision (frozen, asymmetric COST gate): GATE160 is AFFORDABLE iff Δp CI90 not entirely < -2.0 pts
AND ΔEV CI90 not entirely < -$40. Tail protection is prospective (breach replay), not in this MC.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB = HERE / "tables"
REC = HERE / "records"
VAL, FEE = 1422.0, 96.0
ARMS = ["FULLOFF", "GATE160", "GATE158"]

base = pd.read_csv(TAB / "cohorts_baseline.csv", parse_dates=["start"]).sort_values("cohort")
n = len(base)

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
    delta = np.asarray(delta, float)
    boots = np.array([delta[ix].mean() for ix in _IDX])
    return dict(mean=float(delta.mean()),
                lo90=float(np.percentile(boots, 5)), hi90=float(np.percentile(boots, 95)),
                lo95=float(np.percentile(boots, 2.5)), hi95=float(np.percentile(boots, 97.5)))


def neff(d):
    y = d.sort_values("start").funded.to_numpy(float)
    ac = [pd.Series(y).autocorr(k) for k in range(1, 14)]
    return len(y) / (1 + 2 * sum(max(a, 0) for a in ac if np.isfinite(a)))


N_EFF = neff(base)


def load_arm(arm):
    d = pd.read_csv(TAB / f"cohorts_{arm}.csv", parse_dates=["start"]).sort_values("cohort")
    att = pd.read_csv(TAB / f"attempts_{arm}.csv")
    evp = REC / f"{arm}_events.csv"
    ev = pd.read_csv(evp) if evp.stat().st_size > 5 else pd.DataFrame(
        columns=["cohort", "gap_day", "gap_pnl_jpy", "kind", "weekday"])
    busts = att[att.out.isin(["bust_daily", "bust_floor"])]
    d["bust_n"] = d.cohort.map(busts.groupby("cohort").size()).fillna(0.0)
    if len(ev) and "gap_day" in ev and ev.gap_day.any():
        gj = ev[ev.gap_day].groupby("cohort").gap_pnl_jpy.sum()
    else:
        gj = pd.Series(dtype=float)
    d["j1_gap_pnl"] = d.cohort.map(gj).fillna(0.0)
    d["evc"] = d.funded * VAL - d.attempts * FEE
    days = pd.read_parquet(REC / f"{arm}_days.parquet")
    return d, att, ev, days


def tail_and_shares(arm, d, att, ev, days):
    book = days[["gold", "jpy", "on_us", "on_ger"]].sum(axis=1) + days.orb + days.micro + days.fix
    var_b = book.var()
    shares = {f"risk_{k}": float(np.cov(days[k], book)[0, 1] / var_b)
              for k in ["gold", "jpy", "on_us", "on_ger"]}
    worst_jpy_day = float(days.jpy.min()) if len(days) else float("nan")
    worst_book_day = float(book.min()) if len(book) else float("nan")
    worst_gap = float(ev[ev.gap_day].gap_pnl_jpy.min()) if (len(ev) and ev.gap_day.any()) else 0.0
    return dict(worst_jpy_day=worst_jpy_day, worst_book_day=worst_book_day,
                worst_weekend_gap_jpy=worst_gap, **shares)


base_d, base_att, base_ev, base_days = load_arm("baseline")
assert (base_d.cohort.values == base.cohort.values).all()

summary, deltas, decisions = [], [], []
for arm in ["baseline"] + ARMS:
    if not (TAB / f"cohorts_{arm}.csv").exists():
        continue
    d, att, ev, days = load_arm(arm)
    assert (d.cohort.values == base_d.cohort.values).all(), f"grid mismatch {arm}"
    ts = tail_and_shares(arm, d, att, ev, days)
    mg = pd.read_parquet(REC / f"{arm}_margins.parquet")
    s = dict(arm=arm, n=n, N_eff=round(N_EFF, 1),
             p_pooled=d.funded.mean(), p_IS=d[d.win == "IS"].funded.mean(),
             p_OOS=d[d.win == "OOS"].funded.mean(), attempts=d.attempts.mean(),
             med_t=float(d.loc[d.funded, "t"].median()) if d.funded.any() else float("nan"),
             EV=d.funded.mean() * VAL - d.attempts.mean() * FEE,
             bust_per_cohort=d.bust_n.mean(),
             bust_share_att=len(att[att.out.isin(["bust_daily", "bust_floor"])]) / max(len(att), 1),
             margin_p50=float(mg.need.quantile(0.50)) if len(mg) else float("nan"),
             margin_p99=float(mg.need.quantile(0.99)) if len(mg) else float("nan"),
             margin_bind=float(mg.bind.mean()) if len(mg) else float("nan"),
             **ts)
    summary.append(s)
    if arm == "baseline":
        continue
    dp = boot_ci(d.funded.values.astype(float) - base_d.funded.values.astype(float))
    dev = boot_ci(d.evc.values - base_d.evc.values)
    dbust = boot_ci(d.bust_n.values - base_d.bust_n.values)
    dgap = boot_ci(d.j1_gap_pnl.values - base_d.j1_gap_pnl.values)
    row = dict(arm=arm,
               dp=dp["mean"], dp_lo90=dp["lo90"], dp_hi90=dp["hi90"],
               dp_lo95=dp["lo95"], dp_hi95=dp["hi95"],
               dp_IS=d[d.win == "IS"].funded.mean() - base_d[base_d.win == "IS"].funded.mean(),
               dp_OOS=d[d.win == "OOS"].funded.mean() - base_d[base_d.win == "OOS"].funded.mean(),
               dEV=dev["mean"], dEV_lo90=dev["lo90"], dEV_hi90=dev["hi90"],
               d_att=d.attempts.mean() - base_d.attempts.mean(),
               dbust=dbust["mean"], dbust_lo90=dbust["lo90"], dbust_hi90=dbust["hi90"],
               dj1gap=dgap["mean"], dj1gap_lo90=dgap["lo90"], dj1gap_hi90=dgap["hi90"])
    deltas.append(row)
    if arm == "GATE160":
        affordable = (dp["lo90"] >= -2.0) and (dev["lo90"] >= -40.0)
        decisions.append(dict(arm=arm, affordable=bool(affordable),
                              rule="Δp CI90>=-2.0pts AND ΔEV CI90>=-$40",
                              dp=dp["mean"], dp_lo90=dp["lo90"], dEV=dev["mean"], dEV_lo90=dev["lo90"]))

S = pd.DataFrame(summary)
D = pd.DataFrame(deltas)
S.to_csv(TAB / "summary_arms.csv", index=False)
D.to_csv(TAB / "paired_deltas.csv", index=False)
verdict = dict(VAL=VAL, FEE=FEE, N_eff=round(N_EFF, 1), decisions=decisions,
               note="Cost gate only. Tail protection is prospective (breach replay), not this MC.")
(TAB / "decision.json").write_text(json.dumps(verdict, indent=2))

pd.set_option("display.width", 260)
print(f"VAL=${VAL:.0f} FEE=${FEE:.0f} N_eff={N_EFF:.1f} n={n}")
print(S.round(4).to_string(index=False))
print()
print(D.round(4).to_string(index=False))
print()
print(json.dumps(verdict, indent=2))
