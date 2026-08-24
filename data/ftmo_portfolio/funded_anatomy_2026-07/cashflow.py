"""Volet 3 — monthly cash-flow MC (enterprise, 24 calendar months).
Assemble: challenge fees (-$96 x re-purchased challenges) -> funded payouts (0.8 split, bi-weekly,
+$96 refund at first payout) -> re-acquire on funded bust. Break-even month dist, $/month, scaling opt.
Inputs: real_metrics challenge cohorts (swing_ON_low) + funded_anatomy runs/wd_sched (gate ON, low)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB = HERE / "tables"
RM = HERE.parent / "real_metrics_2026-07/tables"
FEE, SPLIT = 96.0, 0.80
TD2CAL = 365.0 / 252.0            # trading-day -> calendar-day
H = 730                           # 24 months horizon (calendar days)
MONTH = 365.0 / 12.0
rng = np.random.default_rng(23)

# challenge campaigns (re-purchase units): funded?, attempts (challenges bought), camp_days
ch = pd.read_csv(RM / "cohorts_swing_ON_low.csv")
CH_F = ch.funded.values.astype(bool); CH_A = ch.attempts.values.astype(int); CH_D = ch.camp_days.values.astype(float)
NCH = len(ch)

# funded trajectories: run_id -> list[(cal_day, amount)] withdrawals + bust cal_day (or None)
def load_funded(tag):
    global runs, wd_by, RUN_IDS, RUN_BUST, RUN_LIFE
    runs = pd.read_csv(TAB / f"runs_{tag}.csv")
    wd = pd.read_csv(TAB / f"wd_sched_{tag}.csv")
    wd_by = {rid: g.sort_values("day")[["day", "amount"]].values for rid, g in wd.groupby("run_id")}
    RUN_IDS = runs.run_id.values
    RUN_BUST = dict(zip(runs.run_id, runs.busted.astype(bool)))
    RUN_LIFE = dict(zip(runs.run_id, runs.life))


load_funded("baseline")


def sample_funded():
    rid = RUN_IDS[rng.integers(0, len(RUN_IDS))]
    sched = wd_by.get(rid, np.empty((0, 2)))
    life_cal = RUN_LIFE[rid] * TD2CAL
    bust_cal = life_cal if RUN_BUST[rid] else None
    return sched, bust_cal, life_cal


def one_campaign(scaling=False):
    """Return (events, funded_inflow, funded_months) over [0,H]. Enterprise: acquire->fund->rebuy.
    Fee-refund + scaling reset PER funded account (a bust -> new account -> new fee)."""
    ev = []
    t = 0.0
    funded_months_active = np.zeros(24, dtype=bool)
    funded_inflow = 0.0
    while t < H:
        # ---- acquisition: buy challenges until one funds ----
        while t < H:
            j = rng.integers(0, NCH)
            ev.append((t, -CH_A[j] * FEE))              # attempts x $96 upfront this campaign
            if CH_F[j]:
                t += CH_D[j]; break                     # funded after camp_days
            t += CH_D[j] + 3.0                          # failed -> re-buy after gap
        if t >= H:
            break
        # ---- funded phase (fresh account) ----
        fund_start = t
        sched, bust_cal, life_cal = sample_funded()
        first_payout_done = False                       # refund is per-account
        scale = 1.0; scale_ms = 0; n_pay_acct = 0
        for day_td, amt in sched:
            dc = day_td * TD2CAL
            if bust_cal is not None and dc > bust_cal:
                break                                   # no withdrawals after bust
            day_cal = fund_start + dc
            if day_cal >= H:
                break
            pay = SPLIT * amt * scale
            if not first_payout_done:
                pay += FEE                              # FTMO refunds this account's fee at 1st payout
                first_payout_done = True
            ev.append((day_cal, pay)); funded_inflow += pay; n_pay_acct += 1
            mi = int(day_cal / MONTH)
            if mi < 24:
                funded_months_active[mi] = True
            if scaling and dc >= (scale_ms + 1) * 4 * MONTH and n_pay_acct >= 2:
                scale_ms += 1; scale *= 1.25            # +25%/4mo if >=2 payouts (milestone proxy)
        t = fund_start + (bust_cal + 5.0 if bust_cal is not None else life_cal)
    return ev, funded_inflow, funded_months_active.sum()


def run_mc(n_boot=20000, scaling=False):
    monthly = np.zeros((n_boot, 24))
    breakeven = np.full(n_boot, np.nan)
    cum24 = np.zeros(n_boot)
    permonth = np.zeros(n_boot)
    for b in range(n_boot):
        ev, f_in, f_months = one_campaign(scaling=scaling)
        m = np.zeros(24)
        for day, amt in ev:
            mi = int(day / MONTH)
            if 0 <= mi < 24:
                m[mi] += amt
        monthly[b] = m
        cs = np.cumsum(m)
        pos = np.where(cs > 0)[0]
        breakeven[b] = pos[0] + 1 if len(pos) else np.nan     # 1-indexed month
        cum24[b] = cs[-1]
        permonth[b] = f_in / max(f_months, 1)
    return dict(monthly=monthly, breakeven=breakeven, cum24=cum24, permonth=permonth)


def report(tag, r):
    be = r["breakeven"]; be_ok = be[~np.isnan(be)]
    q = lambda a, p: float(np.nanpercentile(a, p))
    print(f"\n=== {tag} ===")
    print(f"  break-even month: median {np.nanmedian(be):.0f}  p10 {q(be,10):.0f}  p90 {q(be,90):.0f}  "
          f"never-in-24mo {100*np.isnan(be).mean():.0f}%")
    print(f"  cumulative cash @24mo: median ${np.median(r['cum24']):,.0f}  "
          f"p10 ${q(r['cum24'],10):,.0f}  p90 ${q(r['cum24'],90):,.0f}  P(>0) {100*(r['cum24']>0).mean():.0f}%")
    print(f"  $/month in funded regime: median ${np.median(r['permonth']):,.0f}  "
          f"p10 ${q(r['permonth'],10):,.0f}  p90 ${q(r['permonth'],90):,.0f}")
    mm = r["monthly"].mean(axis=0)
    print("  mean monthly cashflow ($):", " ".join(f"{x:+.0f}" for x in mm[:12]), "...")
    return dict(be_med=float(np.nanmedian(be)), be_p10=q(be, 10), be_p90=q(be, 90),
                never=float(np.isnan(be).mean()), cum24_med=float(np.median(r['cum24'])),
                cum24_p10=q(r['cum24'], 10), cum24_p90=q(r['cum24'], 90),
                pgt0=float((r['cum24'] > 0).mean()), permonth_med=float(np.median(r['permonth'])),
                monthly_mean=mm.tolist())


print(f"challenge campaigns N={NCH} (p_fund {100*CH_F.mean():.1f}%, att {CH_A.mean():.2f})  "
      f"funded runs N={len(runs)} (bust {100*runs.busted.mean():.0f}%)")
base = run_mc(scaling=False)
mbase = report("BASE vm1 funded (no scaling)", base)
scal = run_mc(scaling=True)
mscal = report("SCALING (+25%/4mo on milestone)", scal)

# V2->V3 link: cash-flow if funded ran at vm0.85 (2% bust instead of 30%)
mvm085 = None
if (TAB / "runs_vm085.csv").exists() and (TAB / "wd_sched_vm085.csv").exists():
    load_funded("vm085")
    print(f"\n[vm0.85 funded: bust {100*runs.busted.mean():.1f}%]")
    r085 = run_mc(scaling=False)
    mvm085 = report("vm0.85 FUNDED (V2 signal, no scaling)", r085)
    load_funded("baseline")

# discounting sensitivity (0.5%/month) on the BASE monthly means
disc = np.array([(1.005) ** -mi for mi in range(24)])
mm = base["monthly"].mean(axis=0)
cs_nom = np.cumsum(mm); cs_dis = np.cumsum(mm * disc)
be_nom = next((i + 1 for i, v in enumerate(cs_nom) if v > 0), None)
be_dis = next((i + 1 for i, v in enumerate(cs_dis) if v > 0), None)
print(f"\nDISCOUNTING (0.5%/mo): break-even nominal month {be_nom} vs discounted {be_dis} "
      f"-> {'unchanged' if be_nom==be_dis else 'shifts'}")

import json
(TAB / "cashflow_summary.json").write_text(json.dumps(
    dict(base=mbase, scaling=mscal, vm085=mvm085,
         discount_be_nominal=be_nom, discount_be_discounted=be_dis,
         inputs=dict(challenge_N=int(NCH), funded_N=int(len(runs)),
                     funded_bust_rate=float(runs.busted.mean()))), indent=2))
print("\ncashflow_summary.json written")
