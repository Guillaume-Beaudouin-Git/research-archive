"""Aggregate the 2x2 x margin design into the deliverable:
  triplet (p_pass / attempts / time) + p_funded + EV, gate ON + low-check (account 3),
  paired block-bootstrap deltas (gate alone / low-check alone / combined), re-purchase
  distribution (challenges + total time to first pass), funded VAL/EV, sleeve attribution.
Convention: VAL=FEE+0.8*E[extr] (recost), FEE=96, block=10, 3000 draws, seed=23."""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB = HERE / "tables"; REC = HERE / "records"
FEE = 96.0
LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]
rng = np.random.default_rng(23)


def load(tag):
    return pd.read_csv(TAB / f"cohorts_{tag}.csv", parse_dates=["start"]).sort_values("cohort").reset_index(drop=True)


# ---- block-bootstrap indices (shared, matched to aggregate_suspend) ----
base_any = load("swing_OFF_close")
n = len(base_any)
B = 10
IDX = []
for _ in range(3000):
    ix = []
    while len(ix) < n:
        s = rng.integers(0, n)
        ix.extend(((s + np.arange(B)) % n).tolist())
    IDX.append(np.array(ix[:n]))


def boot_ci(delta):
    delta = np.asarray(delta, float)
    boots = np.array([delta[ix].mean() for ix in IDX])
    return dict(mean=float(delta.mean()), lo90=float(np.percentile(boots, 5)),
                hi90=float(np.percentile(boots, 95)), lo95=float(np.percentile(boots, 2.5)),
                hi95=float(np.percentile(boots, 97.5)))


def neff(d):
    y = d.sort_values("start").funded.to_numpy(float)
    ac = [pd.Series(y).autocorr(k) for k in range(1, 14)]
    return len(y) / (1 + 2 * sum(max(a, 0) for a in ac if np.isfinite(a)))


# ---- funded VAL per (gate, mode) ----
fund = pd.read_csv(TAB / "funded_all.csv")
VALS = {}
for (g, mo), grp in fund.groupby(["gate", "mode"]):
    extr = (grp[grp.win == "IS"].extr.mean() + grp[grp.win == "OOS"].extr.mean()) / 2
    VALS[(g, mo)] = dict(extr=float(extr), VAL=float(FEE + 0.8 * extr),
                         p_nobust=float(1 - grp.busted.mean()))


def cell_summary(tag, margin, gate, mode):
    d = load(tag)
    p = d.funded.mean()
    att = d.attempts.mean()
    val = VALS.get((gate, mode if mode in ("close", "low", "low_dom") else "low"),
                   VALS.get((gate, "close")))["VAL"]
    ev = p * val - att * FEE
    return dict(tag=tag, margin=margin, gate=gate, mode=mode, n=n,
                p_pooled=float(p), p_IS=float(d[d.win == "IS"].funded.mean()),
                p_OOS=float(d[d.win == "OOS"].funded.mean()),
                attempts_per_campaign=float(att),
                med_t_funded=float(d.loc[d.funded, "t"].median()) if d.funded.any() else np.nan,
                VAL=float(val), EV=float(ev))


MARGINS, GATES, MODES = ["policy", "swing"], ["OFF", "ON"], ["close", "low", "low_both", "low_dom"]
summ = [cell_summary(f"{m}_{g}_{mo}", m, g, mo) for m in MARGINS for g in GATES for mo in MODES]
S = pd.DataFrame(summ)
S.to_csv(TAB / "summary_cells.csv", index=False)

# ---- paired deltas vs baseline (margin_OFF_close) ----
deltas = []
for m in MARGINS:
    base = load(f"{m}_OFF_close")
    for g in GATES:
        for mo in MODES:
            if g == "OFF" and mo == "close":
                continue
            d = load(f"{m}_{g}_{mo}")
            dp = boot_ci(d.funded.values.astype(float) - base.funded.values.astype(float))
            deltas.append(dict(margin=m, gate=g, mode=mo, kind=(
                "gate" if (g == "ON" and mo == "close") else
                "lowcheck" if (g == "OFF" and mo in ("low", "low_both")) else
                "combined" if (g == "ON" and mo in ("low", "low_both")) else "other"),
                dp=100 * dp["mean"], lo90=100 * dp["lo90"], hi90=100 * dp["hi90"],
                lo95=100 * dp["lo95"], hi95=100 * dp["hi95"]))
D = pd.DataFrame(deltas)
D.to_csv(TAB / "paired_deltas.csv", index=False)


# ---- re-purchase bootstrap: challenges + total time to FIRST pass ----
def repurchase(tag, n_boot=20000, gap=3):
    d = load(tag)
    fu = d.funded.values
    at = d.attempts.values
    cd = d.camp_days.values
    tt = d.t.values
    N = len(d)
    ncamp = np.empty(n_boot); nch = np.empty(n_boot); tim = np.empty(n_boot)
    for b in range(n_boot):
        camps = 0; ch = 0; tm = 0.0
        while True:
            j = rng.integers(0, N)
            camps += 1; ch += at[j]
            if fu[j]:
                tm += tt[j]; break
            tm += cd[j] + gap
            if camps > 200:
                break
        ncamp[b] = camps; nch[b] = ch; tim[b] = tm
    q = lambda a, p: float(np.percentile(a, p))
    return dict(tag=tag,
                campaigns_mean=float(ncamp.mean()), campaigns_med=q(ncamp, 50), campaigns_p90=q(ncamp, 90),
                challenges_mean=float(nch.mean()), challenges_med=q(nch, 50), challenges_p90=q(nch, 90),
                totaldays_mean=float(tim.mean()), totaldays_med=q(tim, 50), totaldays_p90=q(tim, 90),
                geometric_1overp=float(1 / d.funded.mean()) if d.funded.mean() > 0 else np.inf)


REPU = [repurchase(t) for t in ["swing_OFF_close", "swing_ON_close", "swing_ON_low", "swing_ON_low_dom", "swing_ON_low_both"]]
R = pd.DataFrame(REPU)
R.to_csv(TAB / "repurchase.csv", index=False)


# ---- sleeve attribution of low-check busts (account 3: swing_ON_low) ----
def sleeve_attrib(tag):
    p = REC / f"events_{tag}.csv"
    if not p.exists() or p.stat().st_size < 5:
        return None
    ev = pd.read_csv(p)
    # dominant adverse leg per bust = most negative u_
    ucols = [f"u_{l}" for l in LEGS]
    ev["dom"] = ev[ucols].idxmin(axis=1).str.replace("u_", "")
    return ev.groupby("dom").size().to_dict(), len(ev)


ATTR = {}
for tag in ["swing_ON_low", "swing_ON_low_dom", "swing_OFF_low", "swing_ON_low_both"]:
    a = sleeve_attrib(tag)
    if a:
        ATTR[tag] = dict(by_dominant_leg=a[0], n_bust_events=a[1])

# ================= REPORT =================
pd.set_option("display.width", 240)
print("=" * 96)
print("SUMMARY CELLS (p in %, EV in $)")
print(S.assign(p_pooled=100 * S.p_pooled, p_IS=100 * S.p_IS, p_OOS=100 * S.p_OOS).round(2).to_string(index=False))
print("\nPAIRED DELTAS vs {margin}_OFF_close (pts, block-boot seed23, CI90/95)")
print(D.round(2).to_string(index=False))
print("\nRE-PURCHASE to first pass (SWING)")
print(R.round(2).to_string(index=False))
print("\nFUNDED VAL by (gate,mode):", json.dumps({f"{g}/{mo}": {k: round(v, 1) for k, v in d.items()}
      for (g, mo), d in VALS.items()}, indent=0))
print("\nSLEEVE ATTRIBUTION of intra-bar low-check busts:", json.dumps(ATTR, indent=1))

# headline
acct3 = S[(S.margin == "swing") & (S.gate == "ON") & (S['mode'] == "low")].iloc[0]
basel = S[(S.margin == "swing") & (S.gate == "OFF") & (S['mode'] == "close")].iloc[0]
comb = D[(D.margin == "swing") & (D.kind == "combined") & (D['mode'] == "low")].iloc[0]
gate_d = D[(D.margin == "swing") & (D.kind == "gate")].iloc[0]
lc_d = D[(D.margin == "swing") & (D.kind == "lowcheck") & (D['mode'] == "low")].iloc[0]
r3 = R[R.tag == "swing_ON_low"].iloc[0]
print("\n" + "=" * 96)
print(f"ACCOUNT 3 (SWING + gate ON + low-check) : p_pass={100*acct3.p_pooled:.2f}%  "
      f"attempts/campaign={acct3.attempts_per_campaign:.2f}  med_t_fund={acct3.med_t_funded:.0f}d  "
      f"EV=${acct3.EV:+.0f}")
print(f"  re-purchase: E[campaigns]={r3.campaigns_mean:.2f} (1/p={r3.geometric_1overp:.2f})  "
      f"E[challenges]={r3.challenges_mean:.2f}  E[total days to pass]={r3.totaldays_mean:.0f}  "
      f"(med {r3.totaldays_med:.0f}, p90 {r3.totaldays_p90:.0f})")
print(f"BASELINE (SWING + gate OFF + close) : p_pass={100*basel.p_pooled:.2f}%  EV=${basel.EV:+.0f}  "
      f"[cited 71.4% / +$740]")
print(f"DECOMP (SWING pts): gate={gate_d.dp:+.2f}[{gate_d.lo90:+.2f},{gate_d.hi90:+.2f}]  "
      f"lowcheck={lc_d.dp:+.2f}[{lc_d.lo90:+.2f},{lc_d.hi90:+.2f}]  "
      f"combined={comb.dp:+.2f}[{comb.lo90:+.2f},{comb.hi90:+.2f}]")
verdict = dict(account3=dict(p_pass=round(100 * acct3.p_pooled, 2),
               attempts_per_campaign=round(acct3.attempts_per_campaign, 2),
               med_t_fund=round(acct3.med_t_funded, 0), EV=round(acct3.EV, 0),
               E_campaigns=round(r3.campaigns_mean, 2), E_challenges=round(r3.challenges_mean, 2),
               E_total_days=round(r3.totaldays_mean, 0)),
               baseline=dict(p_pass=round(100 * basel.p_pooled, 2), EV=round(basel.EV, 0)),
               decomp=dict(gate=[round(gate_d.dp, 2), round(gate_d.lo90, 2), round(gate_d.hi90, 2)],
                           lowcheck=[round(lc_d.dp, 2), round(lc_d.lo90, 2), round(lc_d.hi90, 2)],
                           combined=[round(comb.dp, 2), round(comb.lo90, 2), round(comb.hi90, 2)]),
               sleeve_attrib=ATTR, N_eff=round(neff(base_any), 1))
(TAB / "verdict.json").write_text(json.dumps(verdict, indent=2))
print("\nverdict.json written")
