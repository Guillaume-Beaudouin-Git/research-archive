"""Phases 1 + 2.1/2.4/2.5 — baseline attributed run, weights, decomposition."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import attr_engine as AE
E = AE.E

TAB = HERE / "tables"; TAB.mkdir(exist_ok=True)
t0 = time.time()

M = E.load_market()
WT_df, ON_df = E.build_signals()
WT, ON = E.align_signals(M, WT_df, ON_df)
CFG = dict(E.CFG_V2, fix_deadlock=True)
WINDOWS = (("IS", "2013-10-01", "2019-12-31"), ("OOS", "2020-01-02", "2026-02-25"))

rec, att_log, coh_rows = [], [], []
for win, lo, hi in WINDOWS:
    st = E.cohort_starts(M, lo, hi, 7)
    for i0 in st:
        cid = f"{win}_{M['dates'][int(i0)].date()}"
        r = AE.run_funnel_attr(M, int(i0), WT, ON, CFG, rec, att_log, cid)
        coh_rows.append(dict(cohort=cid, win=win, start=M["dates"][int(i0)],
                             funded=r["funded"], attempts=r["attempts"], t=r["t"]))
coh = pd.DataFrame(coh_rows)
df = pd.DataFrame(rec)
att = pd.DataFrame(att_log)
df["overnight"] = df.on_us + df.on_ger
df["total"] = df[["gold", "jpy", "on_us", "on_ger", "orb", "fix"]].sum(axis=1)
df["win"] = df.cohort.str.split("_").str[0]
print(f"baseline: pooled p={coh.funded.mean()*100:.2f}% "
      f"(IS {coh[coh.win=='IS'].funded.mean()*100:.1f} / "
      f"OOS {coh[coh.win=='OOS'].funded.mean()*100:.1f}) "
      f"day-records={len(df)} attempts={len(att)} [{time.time()-t0:.0f}s]", flush=True)

# identity check: sum of attributed P&L per attempt == end - INIT
g = df.groupby(["cohort", "attempt", "phase"])["total"].sum().reset_index()
m = g.merge(att, on=["cohort", "attempt", "phase"])
m["err"] = m.total - (m["end"] - E.INIT)
print(f"identity check: max |err| = ${m.err.abs().max():.4f} "
      f"(n={len(m)} attempts)  -> {'PASS' if m.err.abs().max() < 0.01 else 'FAIL'}")

df.to_parquet(HERE / "baseline_day_records.parquet")
att.to_csv(TAB / "attempt_log.csv", index=False)
coh.to_csv(TAB / "cohort_outcomes_baseline.csv", index=False)

# ---------------- PHASE 1: realized weights ----------------
print("== P1.1 realized weights ==", flush=True)
led = pd.read_parquet(Path("<HOME>/Desktop/Algo_claude/PropFirms/"
                           "ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet"))
lev = (led["entry"] / (led["entry"] - led["stop_eff"]).abs()).astype(float)
lev_by_date = lev.copy()
df["orb_notional"] = (df.orb_risk *
                      lev_by_date.reindex(pd.to_datetime(df.date)).fillna(0).to_numpy())

rows = []
for win in ("IS", "OOS", "pooled"):
    d = df if win == "pooled" else df[df.win == win]
    gross = {nm: d["pos_" + nm].abs() for nm in AE.LEG_NAMES}
    gross["orb"] = d.orb_notional * (6.5 / 24)        # time-weight: live ~6.5h of 24
    tot = sum(gross.values())
    ok = tot > 0
    # risk shares: cov(pnl_sleeve, pnl_book)/var(book) on day records
    book = d.total
    var_b = book.var()
    for sleeve, cols in AE.SLEEVES.items():
        pnl = d[cols].sum(axis=1) if len(cols) > 1 else d[cols[0]]
        beta = pnl.cov(book) / var_b
        notion = (gross[cols[0]] if sleeve != "overnight"
                  else gross["on_us"] + gross["on_ger"])
        if sleeve == "orb":
            notion = gross["orb"]
        rows.append(dict(win=win, sleeve=sleeve,
                         notional_share=float((notion[ok] / tot[ok]).mean()),
                         notional_x_equity=float(notion.mean() / E.INIT),
                         risk_share=float(beta),
                         drift_usd_day=float(pnl.mean()),
                         vol_usd_day=float(pnl.std()),
                         margin_share=float(np.mean(
                             notion * (0.02 if sleeve != "jpy" else 0.01)) / E.INIT)))
w = pd.DataFrame(rows)
print(w.round(3).to_string(index=False))
w.to_csv(TAB / "p1_realized_weights.csv", index=False)

print("== P1.2 margin cap binding ==")
mp = df.dropna(subset=["margin_pre"])
bind = mp[mp.margin_pre > 0.60]
print(f"rebalance snapshots n={len(mp)}; cap binds {len(bind)/len(mp)*100:.1f}% "
      f"(IS {len(bind[bind.win=='IS'])/max(len(mp[mp.win=='IS']),1)*100:.1f} / "
      f"OOS {len(bind[bind.win=='OOS'])/max(len(mp[mp.win=='OOS']),1)*100:.1f})")
print(f"when binding: pre p50 {bind.margin_pre.median()*100:.0f}% p95 "
      f"{bind.margin_pre.quantile(.95)*100:.0f}% -> scale factor med "
      f"{(0.60/bind.margin_pre).median():.2f} (proportional, all legs equally; "
      f"ORB outside the cap)")

# ---------------- PHASE 2.1: P&L decomposition by outcome ----------------
print("== P2.1 sleeve P&L by attempt outcome ==", flush=True)
agg = df.groupby(["cohort", "attempt", "phase", "win", "att_out"])[
    ["gold", "jpy", "overnight", "orb", "fix", "total"]].sum().reset_index()
out = agg.groupby(["win", "att_out"])[
    ["gold", "jpy", "overnight", "orb", "fix", "total"]].mean().round(0)
print(out.to_string())
out.to_csv(TAB / "p2_pnl_by_outcome.csv")
pool = agg.groupby("att_out")[["gold", "jpy", "overnight", "orb", "fix", "total"]].mean()
pool.to_csv(TAB / "p2_pnl_by_outcome_pooled.csv")

# cohort-level: contribution to funded vs not-funded cohorts
cg = df.groupby("cohort")[["gold", "jpy", "overnight", "orb", "fix", "total"]].sum()
cg = cg.merge(coh.set_index("cohort")[["funded", "win"]], left_index=True, right_index=True)
cf = cg.groupby(["win", "funded"])[["gold", "jpy", "overnight", "orb", "total"]].mean().round(0)
print(cf.to_string())
cf.to_csv(TAB / "p2_pnl_by_cohort_outcome.csv")

# ---------------- PHASE 2.4: drift vs variance ----------------
print("== P2.4 drift vs variance decomposition (pooled day records) ==")
book = df.total
rows = []
for sleeve, cols in AE.SLEEVES.items():
    pnl = df[cols].sum(axis=1) if len(cols) > 1 else df[cols[0]]
    rows.append(dict(sleeve=sleeve,
                     drift_usd_day=pnl.mean(),
                     drift_share=pnl.mean() / book.mean(),
                     var_share=pnl.cov(book) / book.var(),
                     own_vol=pnl.std()))
dv = pd.DataFrame(rows)
print(dv.round(3).to_string(index=False))
dv.to_csv(TAB / "p2_drift_variance.csv", index=False)
print(f"book: mean ${book.mean():.1f}/day  std ${book.std():.0f}/day "
      f"(= {book.std()/E.INIT*100:.1f}%/day on $10k)")

# ---------------- PHASE 2.5: bust attribution ----------------
print("== P2.5 bust-day attribution ==")
bd = df[df.outcome == "bust"].copy()
bd["wd"] = pd.to_datetime(bd.date).dt.dayofweek
cols5 = ["gold", "jpy", "overnight", "orb", "fix"]
print(f"bust days n={len(bd)}; mean P&L by sleeve on breach day ($):")
print(bd[cols5 + ["total"]].mean().round(0).to_string())
mon = bd[bd.wd == 0]
print(f"Monday busts n={len(mon)} ({len(mon)/len(bd)*100:.0f}%); breach-day P&L ($):")
print(mon[cols5 + ["total"]].mean().round(0).to_string())
bd.groupby("wd")[cols5 + ["total"]].mean().round(0).to_csv(TAB / "p2_bust_by_weekday.csv")
print(f"weekend-held sleeves into Monday: gold/jpy only by construction "
      f"(ON legs Mon/Tue nights; ORB intraday) — Monday gap loss split: "
      f"gold ${mon.gold.mean():.0f} jpy ${mon.jpy.mean():.0f}")
print(f"done {time.time()-t0:.0f}s")
