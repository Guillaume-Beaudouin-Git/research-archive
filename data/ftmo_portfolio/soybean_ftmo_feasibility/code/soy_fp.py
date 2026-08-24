"""Lean standalone FTMO 2-step first-passage for SOYBEAN (book OFF).

Verbatim copy of asia_fp.py (the engine is instrument-agnostic: a daily first-passage on
$-additive increments with an intraday-low barrier). Increments per book day i:
  P&L_i      = INIT * net[i]      (net already K-scaled + stopped/skipped by soy_stop)
  intraday   = INIT * low[i]      (worst mark-to-market in the 01:00-07:00 window, same scaling)
FTMO 10k 2-step, $-additive (rules are % of INITIAL, not compounding):
  daily loss : equity >= balance@day-start - $500
  max loss   : equity >= $9000 (static floor)
  targets    : P1 balance>=11000, P2 balance>=10500 ; min 4 traded days/phase
  funnel     : P1 -> +3 idx gap -> P2 ; bust/timeout -> +2 idx retry ; wall 91 calendar days.
Cohort starts identical to the canonical book (every 7 days within IS/OOS windows).
Validated |Δ|<=0.5pt against the audited bar engine (book-off) in q2_sim.py.
"""
import numpy as np

INIT, BUDGET, FLOOR = 10000.0, 500.0, 9000.0
T1, T2, MINDAYS = 0.10, 0.05, 4


def _phase(net, low, traded, dates, start, target, wall_end):
    bal = INIT
    tgt = INIT * (1 + target)
    opened = 0
    mn = bal
    i = start
    n = len(net)
    while i < n:
        if (dates[i] - dates[start]).days > wall_end:
            return "timeout", i, mn
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        if traded[i]:
            eq_low = bal + INIT * (low[i])      # low already includes K (see soy_stop)
            mn = min(mn, eq_low)
            if eq_low < lim_eff:
                return ("bust_daily" if eq_low >= FLOOR else "bust_floor"), i, mn
            bal += INIT * (net[i])
            opened += 1
        mn = min(mn, bal)
        if bal >= tgt and opened >= MINDAYS:
            return "pass", i, mn
        i += 1
    return "timeout", n - 1, mn


def run_campaign(net, low, traded, dates, start, wall=91, gap=3, retry=2):
    i = start
    attempts = 0
    n = len(net)
    outcomes = []
    while True:
        if (dates[min(i, n - 1)] - dates[start]).days > wall or i >= n - 5:
            return dict(funded=False, attempts=attempts, t=np.nan, outcomes=outcomes, min_eq=mn1)
        attempts += 1
        o1, last1, mn1 = _phase(net, low, traded, dates, i, T1, wall)
        outcomes.append(o1)
        if o1 == "pass":
            j = min(last1 + gap, n - 1)
            if (dates[j] - dates[start]).days > wall:
                return dict(funded=False, attempts=attempts, t=np.nan, outcomes=outcomes, min_eq=mn1)
            o2, last2, mn2 = _phase(net, low, traded, dates, j, T2, wall)
            outcomes.append(o2)
            if o2 == "pass":
                t = (dates[last2] - dates[start]).days
                return dict(funded=(t <= wall), attempts=attempts, t=t if t <= wall else np.nan,
                            outcomes=outcomes, min_eq=mn1)
            if o2 == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan, outcomes=outcomes, min_eq=mn1)
            i = min(last2 + retry, n - 1)
        else:
            if o1 == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan, outcomes=outcomes, min_eq=mn1)
            i = min(last1 + retry, n - 1)


def cohort_run(net, low, traded, dates, starts, wall=91):
    funded, attempts, ts, min_eqs, all_out = [], [], [], [], []
    for s in starts:
        r = run_campaign(net, low, traded, dates, int(s), wall)
        funded.append(r["funded"]); attempts.append(r["attempts"])
        ts.append(r["t"]); min_eqs.append(r["min_eq"]); all_out += r["outcomes"]
    funded = np.array(funded); attempts = np.array(attempts)
    out = np.array(all_out)
    n_bust = np.isin(out, ["bust_daily", "bust_floor"]).sum()
    return dict(
        p_funded=float(funded.mean()), n=len(funded),
        attempts_mean=float(attempts.mean()),
        med_t=float(np.nanmedian(ts)) if np.isfinite(ts).any() else np.nan,
        p_bust_per_attempt=float(n_bust / max(1, len(out))),
        p_bust_daily=float(np.isin(out, ["bust_daily"]).sum() / max(1, len(out))),
        p_bust_floor=float(np.isin(out, ["bust_floor"]).sum() / max(1, len(out))),
        min_eq_pct=(np.array(min_eqs) / INIT - 1.0) * 100.0,
        funded_arr=funded,
    )
