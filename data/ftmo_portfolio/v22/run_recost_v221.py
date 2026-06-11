"""v2.2.1 RE-COST runner — swaps mesurés (points->bps) + commissions + marge Swing.

Data-only (pré-enregistré): aucun changement signal/vm/budgets/policy. Gates:
  G0 reconstruction des 4 swaps facturés 10->11/06 au centime (sinon STOP) ;
  G1 repro baseline challenge == 87.01 (déterminisme) ;
  G2 |challenge recost - baseline| <= 0.3 pt (sinon STOP + diagnostic).
Sorties: recost/tables/*.csv + recost/summary.json + stdout (tee log).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config_v22 as C22
import engine_v22 as V

E = V.E
LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]
OUT = HERE / "recost"
TAB = OUT / "tables"
TAB.mkdir(parents=True, exist_ok=True)
t0 = time.time()


def log(msg):
    print(f"{msg}  [{time.time()-t0:.0f}s]", flush=True)


# ---------------------------------------------------------------- G0 sanity
def sanity_gate():
    fx_eur = C22.REF_PX["EURUSD"]
    jpy = C22.REF_PX["USDJPY"]
    cases = [  # (sym, lots, mult, facturé_observé_$, quote->USD)
        ("XAUUSD", 0.01, 3, -1.97, 1.0),
        ("USDJPY", 0.10, 3, +0.18, 1.0 / jpy),
        ("US100", 0.10, 1, -0.64, 1.0),
        ("GER40", 0.10, 1, -0.45, fx_eur),
    ]
    rows = []
    for sym, lots, mult, obs, fx in cases:
        pv = C22.point_value_quote(sym)
        rec = C22.MEASURED_SPECS[sym]["swap_long_pts"] * pv * lots * mult * fx
        ok = abs(rec - obs) <= 0.005 + 1e-9
        rows.append(dict(symbol=sym, lots=lots, mult=mult, billed_usd=obs,
                         reconstructed_usd=round(rec, 4), ok=ok))
        log(f"G0 {sym} {lots} lot x{mult}: reconstruit {rec:+.4f} vs facturé "
            f"{obs:+.2f} {'OK' if ok else '*** FAIL ***'}")
    pd.DataFrame(rows).to_csv(TAB / "recost_sanity_gate.csv", index=False)
    if not all(r["ok"] for r in rows):
        log("*** G0 FAIL — mécanique swap non reproduite, STOP ***")
        sys.exit(1)
    log("G0 PASS (4/4 au centime)")


# ---------------------------------------------------------------- stack
def sweep(tag, M, WT, ON, cfg=None, save=True):
    cfg = cfg or C22.CFG_CHALLENGE
    rows = []
    for win, lo, hi in C22.WINDOWS:
        for i0 in V.starts(M, lo, hi, C22.COHORT_STEP):
            r = V.run_funnel(M, int(i0), WT, ON, cfg, wall=C22.WALL)
            rows.append(dict(win=win, start=M["dates"][int(i0)], funded=r["funded"],
                             attempts=r["attempts"], t=r["t"]))
    d = pd.DataFrame(rows)
    log(f"{tag:22s} IS {d[d.win=='IS'].funded.mean()*100:5.1f} "
        f"OOS {d[d.win=='OOS'].funded.mean()*100:5.1f} "
        f"pooled {d.funded.mean()*100:5.2f} att {d.attempts.mean():.2f}")
    if save:
        d.to_csv(TAB / f"recost_{tag}.csv", index=False)
    return d


def funded_runs(tag, M, WT, ON):
    out = {}
    for win, lo, hi in C22.FUNDED_WINDOWS:
        rows = [V.run_funded(M, int(i0), WT, ON, C22.CFG_FUNDED,
                             horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
                for i0 in V.starts(M, lo, hi, C22.FUNDED_STEP)]
        d = pd.DataFrame(rows)
        d["extr"] = d.wd + d.residual
        out[win] = d
        log(f"funded[{tag}] {win}: n={len(d)} E[extr]=${d.extr.mean():,.0f} "
            f"med=${d.extr.median():,.0f} bust={d.busted.mean()*100:.1f}% "
            f"payouts={d.payouts.mean():.1f}")
    return out


def margin_stats(tag):
    ml = np.array(E.MARGIN_LOG)
    st = dict(tag=tag, n=len(ml), p50=np.percentile(ml, 50), p99=np.percentile(ml, 99),
              p999=np.percentile(ml, 99.9), mx=ml.max(), bind=(ml > 0.60).mean())
    log(f"marge[{tag}] p50 {st['p50']*100:.0f}% p99 {st['p99']*100:.0f}% "
        f"p999 {st['p999']*100:.0f}% max {st['mx']*100:.0f}% bind {st['bind']*100:.1f}%")
    return st


def main():
    sanity_gate()

    # cohérence REF_PX vs panel (anti-retype)
    px = pd.read_parquet(E.CACHE / "panel_px.parquet").ffill().iloc[-1]
    for s in LEGS + ["EURUSD"]:
        assert abs(px[s] - C22.REF_PX[s]) < 0.01 + 0.0005 * px[s], \
            f"REF_PX {s} retypé faux: {C22.REF_PX[s]} vs panel {px[s]}"
    log("REF_PX == panel ffill last (anti-retype PASS)")

    M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    WT_df, ON_df = E.build_signals()
    WT, ON = V.align(M, WT_df, ON_df)
    log("stack chargé")

    # ---- G1: repro baseline (déterminisme)
    base = sweep("challenge_base", M, WT, ON)
    p_base = base.funded.mean() * 100
    assert abs(p_base - 87.01) < 0.05, f"G1 FAIL: repro {p_base:.2f} != 87.01"
    log("G1 PASS (repro exacte)")

    # ---- swaps mesurés: bps constants @ REF_PX (forward-cost), mult panel inchangé
    bL = np.array([C22.swap_bps(s, "long") for s in LEGS])
    bS = np.array([C22.swap_bps(s, "short") for s in LEGS])
    old_L = {s: float(pd.read_parquet(E.CACHE / "panel_swapL.parquet")[s].dropna().iloc[-1])
             for s in LEGS}
    old_S = {s: float(pd.read_parquet(E.CACHE / "panel_swapS.parquet")[s].dropna().iloc[-1])
             for s in LEGS}
    pd.DataFrame([dict(symbol=s, side=sd,
                       pts=C22.MEASURED_SPECS[s][f"swap_{sd}_pts"],
                       bps_measured=round(C22.swap_bps(s, sd), 4),
                       bps_old_anchor=round((old_L if sd == "long" else old_S)[s], 4),
                       triple_dow=C22.MEASURED_SPECS[s]["triple_dow"])
                  for s in LEGS for sd in ("long", "short")]
                 ).to_csv(TAB / "recost_swap_anchors.csv", index=False)
    M_sw = dict(M)
    M_sw["swL"] = np.tile(bL, (M["n"], 1))
    M_sw["swS"] = np.tile(bS, (M["n"], 1))
    d_sw = sweep("challenge_swaps", M_sw, WT, ON)

    # ---- + commissions (rt bps RT additionnels, constants par construction)
    comm = np.array([C22.comm_rt_bps(s) for s in LEGS])
    pd.DataFrame([dict(symbol=s, comm_rt_bps=round(float(comm[k]), 4),
                       rt_spread_bps=round(float(M["rt"][k]), 4),
                       rt_total_bps=round(float(M["rt"][k] + comm[k]), 4))
                  for k, s in enumerate(LEGS)]
                 ).to_csv(TAB / "recost_commissions.csv", index=False)
    M_swc = dict(M_sw)
    M_swc["rt"] = M["rt"] + comm
    d_swc = sweep("challenge_recost", M_swc, WT, ON)
    p_swc = d_swc.funded.mean() * 100
    att_swc = d_swc.attempts.mean()
    delta = p_swc - p_base
    log(f"G2 challenge recost {p_swc:.2f} vs base {p_base:.2f} -> Δ {delta:+.2f} pt")
    if abs(delta) > 0.3:
        log("*** G2 FAIL — un coût de swap/commission ne doit pas bouger le "
            "challenge de >0.3 pt : DIAGNOSTIC REQUIS ***")

    # ---- marge: policy (log) / Standard mesurée / Swing (enforced + log)
    mr_sets = dict(
        policy=np.array([C22.MARGIN_RATES_POLICY[s] for s in LEGS]),
        standard=np.array([C22.MARGIN_RATES_STANDARD[s] for s in LEGS]),
        swing=np.array([C22.MARGIN_RATES_SWING[s] for s in LEGS]),
    )
    mrate_saved = E.MRATE.copy()
    mstats, mruns = [], {}
    for name, rates in mr_sets.items():
        E.MRATE = rates
        E.MARGIN_LOG.clear()
        dm = sweep(f"challenge_margin_{name}", M_swc, WT, ON,
                   cfg=dict(C22.CFG_CHALLENGE, margin_log=True))
        st = margin_stats(name)
        st["p_pass"] = dm.funded.mean() * 100
        st["att"] = dm.attempts.mean()
        mstats.append(st)
        mruns[name] = dm
    E.MRATE = mrate_saved
    pd.DataFrame(mstats).to_csv(TAB / "recost_margin.csv", index=False)

    # ---- grille de lots type (vm14, eq=10k, poids typiques) par jeu de marge
    rows = []
    w_typ = dict(XAUUSD=0.5, USDJPY=1.31, US100=0.6, GER40=0.6)  # poids x on_w typiques
    for name, rates in mr_sets.items():
        need = sum(abs(w_typ[s]) * 14.0 * rates[k] for k, s in enumerate(LEGS))
        rows.append(dict(set=name, need_pct_eq=round(need * 100, 1),
                         cap_pct=60.0, scale_if_capped=round(min(1.0, 0.60 / need), 3)))
    pd.DataFrame(rows).to_csv(TAB / "recost_margin_grid.csv", index=False)

    # ---- funded sous coûts mesurés (policy margin) + variante swing margin
    fr = funded_runs("recost", M_swc, WT, ON)
    extr_pooled = (fr["IS"].extr.mean() + fr["OOS"].extr.mean()) / 2
    VAL = C22.FEE + 0.8 * extr_pooled
    ev = p_swc / 100 * VAL - att_swc * C22.FEE
    log(f"VAL recost = 96 + 0.8 x {extr_pooled:,.0f} = ${VAL:,.0f} ; "
        f"EV = {p_swc/100:.3f} x {VAL:,.0f} - {att_swc:.2f} x 96 = ${ev:+,.0f}")
    E.MRATE = mr_sets["swing"]
    fr_sw = funded_runs("recost+swingmargin", M_swc, WT, ON)
    E.MRATE = mrate_saved
    pd.concat([fr["IS"].assign(win="IS", marge="policy"),
               fr["OOS"].assign(win="OOS", marge="policy"),
               fr_sw["IS"].assign(win="IS", marge="swing"),
               fr_sw["OOS"].assign(win="OOS", marge="swing")]
              ).to_csv(TAB / "recost_funded.csv", index=False)

    # ---- turnover par jambe (commissions/jour) : challenge médian + funded médian
    turn = {k: [] for k in range(4)}
    orig_tt = E._trade_to

    def rec_tt(pos, avg, bal, target, prices, rt):
        for k in range(4):
            if np.isfinite(prices[k]):
                turn[k].append(abs(target[k] - pos[k]))
        return orig_tt(pos, avg, bal, target, prices, rt)

    E._trade_to = rec_tt
    mid = int(np.where(M["dates_idx"] >= "2022-01-03")[0][0])
    V.run_funded(M_swc, mid, WT, ON, C22.CFG_FUNDED, horizon=C22.FUNDED_HORIZON,
                 wd_every=C22.FUNDED_WD_EVERY)
    fund_turn = {LEGS[k]: float(np.mean(v)) if v else 0.0 for k, v in turn.items()}
    fund_days = max(len(turn[1]), 1)
    for k in turn:
        turn[k] = []
    V.run_funnel(M_swc, mid, WT, ON, C22.CFG_CHALLENGE, wall=C22.WALL)
    ch_turn = {LEGS[k]: float(np.mean(v)) if v else 0.0 for k, v in turn.items()}
    E._trade_to = orig_tt
    pd.DataFrame([dict(leg=s, fase="funded_vm1",
                       turnover_usd_jour=round(fund_turn[s], 0),
                       comm_usd_jour=round(fund_turn[s] * C22.comm_rt_bps(s) / 2e4, 3))
                  for s in LEGS] +
                 [dict(leg=s, fase="challenge_vm14",
                       turnover_usd_jour=round(ch_turn[s], 0),
                       comm_usd_jour=round(ch_turn[s] * C22.comm_rt_bps(s) / 2e4, 3))
                  for s in LEGS]).to_csv(TAB / "recost_turnover.csv", index=False)
    log(f"turnover funded/j: { {s: round(fund_turn[s]) for s in LEGS} }")
    log(f"turnover challenge/j: { {s: round(ch_turn[s]) for s in LEGS} }")

    # ---- incidence calendrier x3 par sleeve (analytique, arrays)
    dates = M["dates_idx"]
    dow = pd.DatetimeIndex(dates).dayofweek
    held_gold = WT[:, 0] != 0
    held_j1 = WT[:, 1] != 0
    on_night = np.isin(dow, [0, 1])              # jambes ON tenues EOD lun+mar
    rows = []
    for leg, held, trip_dow in (("XAUUSD", held_gold, 2), ("USDJPY", held_j1, 2),
                                ("US100", on_night, 4), ("GER40", on_night, 4)):
        n_trip = int((held & (dow == trip_dow)).sum())
        rows.append(dict(leg=leg, triple_dow=trip_dow,
                         nuits_tenues=int(held.sum()),
                         nuits_triples=n_trip,
                         pct_nuits_triples=round(
                             n_trip / max(int(held.sum()), 1) * 100, 2)))
    inc = pd.DataFrame(rows)
    inc.to_csv(TAB / "recost_calendar_incidence.csv", index=False)
    log(f"incidence x3: {inc.to_dict('records')}")

    summary = dict(
        read_date=C22.SPECS_READ_DATE, source=C22.SPECS_SOURCE,
        challenge_base=round(p_base, 2), challenge_swaps=round(
            d_sw.funded.mean() * 100, 2),
        challenge_recost=round(p_swc, 2), delta_pt=round(delta, 2),
        att_recost=round(att_swc, 2),
        gate_G2="PASS" if abs(delta) <= 0.3 else "FAIL",
        margin=mstats,
        funded_IS=round(fr["IS"].extr.mean(), 0),
        funded_OOS=round(fr["OOS"].extr.mean(), 0),
        funded_IS_swingm=round(fr_sw["IS"].extr.mean(), 0),
        funded_OOS_swingm=round(fr_sw["OOS"].extr.mean(), 0),
        VAL=round(VAL, 0), EV=round(ev, 0),
        baseline_anchors=dict(funded_IS=684, funded_OOS=2632, VAL=1422, EV=926),
    )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    log("summary.json écrit — DONE")


if __name__ == "__main__":
    main()
