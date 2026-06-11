"""v2.2.2 PRE-REGISTERED — re-fit du container sous marge SWING (hypothèse 1:30/1:15/1:9).

Baseline 1947163 (v2.2.1) READ-ONLY ; policy signal INTACTE. Arms pré-enregistrés :
  A  vm14 + clip proportionnel dynamique (cap 60%) — reproduction du 71.4
  B  grille statique x0.24 (vm_eff 3.36, design zéro-clip)
  C  vm 6 / 8 / 10 + clip dynamique
  D  vm14 + J1 budget 0.5->0.25 (WT_jpy x0.5) + clip dynamique — margin relief
  E  info comité: meilleur arm @ wall 182 (pas une adoption)
Costs = M_swc du re-cost (swaps mesurés const + commissions), identique au run 71.4.
No-clock = cfg sans max_cal => timeout OFF et PACE OFF (feature d'horloge) — isole le
terme gambler's ruin. Identité de caisse: assertions du moteur armées (toute violation
crash le run). Décision (verbatim mission): max EV s.c. p91>=65 et bust/daily-breach
non dégradés au-delà du bruit CI apparié ; sinon null documenté, A reste.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG / "v22"))
import config_v22 as C22                                   # noqa: E402
import engine_v22 as V                                     # noqa: E402

E = V.E
LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]
TAB = HERE / "tables"
TAB.mkdir(parents=True, exist_ok=True)
t0 = time.time()
rng = np.random.default_rng(42)

SWING = np.array([C22.MARGIN_RATES_SWING[s] for s in LEGS])
POLICY = np.array([C22.MARGIN_RATES_POLICY[s] for s in LEGS])
RECOST = json.loads((PKG / "v22" / "recost" / "summary.json").read_text())
VAL_SWC = C22.FEE + 0.8 * (RECOST["funded_IS"] + RECOST["funded_OOS"]) / 2.0
VAL_COMM = C22.FEE + 0.8 * (RECOST["funded_IS_comm_only"]
                            + RECOST["funded_OOS_comm_only"]) / 2.0
NOCLOCK_MIN_TD = 400          # jours de données requis après start (censure)


def log(m):
    print(f"{m}  [{time.time()-t0:.0f}s]", flush=True)


# ------------------------------------------------------------- stack + arms
def build():
    M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    WT_df, ON_df = E.build_signals()
    WT, ON = V.align(M, WT_df, ON_df)
    bL = np.array([C22.swap_bps(s, "long") for s in LEGS])
    bS = np.array([C22.swap_bps(s, "short") for s in LEGS])
    comm = np.array([C22.comm_rt_bps(s) for s in LEGS])
    M_swc = dict(M)
    M_swc["swL"] = np.tile(bL, (M["n"], 1))
    M_swc["swS"] = np.tile(bS, (M["n"], 1))
    M_swc["rt"] = M["rt"] + comm
    return M, M_swc, WT, ON


ATTEMPTS = []          # recorder global (vidé par sweep)
PACE_SAMPLES = []


def _wrap_run_phase(orig):
    def w(M, i0, WT, ON, cfg, diag=None):
        r = orig(M, i0, WT, ON, cfg, diag=diag)
        ATTEMPTS.append(dict(i0=int(i0), out=r["out"], used=int(r["used"]),
                             end=float(r["end"]), target=cfg.get("target"),
                             phase="P1" if cfg.get("target") == E.TARGET1 else "P2"))
        return r
    return w


def _wrap_tfs(orig):
    def w(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm):
        if s == 4 and cfg.get("pace") and cfg.get("max_cal"):
            eq = bal + E._mtm(pos, avg, px0)
            frac_t = (M["dates"][i] - M["dates"][i0]).days / cfg["max_cal"]
            prog = (eq / E.INIT - 1.0) / cfg["target"]
            pace = float(np.clip(1.0 + cfg.get("pace_k", 1.0)
                                 * (frac_t - max(prog, 0.0)), 0.8, 2.0))
            PACE_SAMPLES.append((pace, prog > 0.8))
        return orig(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm)
    return w


def sweep_funnel(M, WT, ON, cfg, wall, record=False, pace_probe=False):
    rows = []
    orig_rp, orig_tfs = V.run_phase, E._target_for_segment
    if record:
        ATTEMPTS.clear()
        V.run_phase = _wrap_run_phase(orig_rp)
    if pace_probe:
        PACE_SAMPLES.clear()
        E._target_for_segment = _wrap_tfs(orig_tfs)
    try:
        for win, lo, hi in C22.WINDOWS:
            for i0 in V.starts(M, lo, hi, C22.COHORT_STEP):
                r = V.run_funnel(M, int(i0), WT, ON, cfg, wall=wall)
                rows.append(dict(win=win, start=M["dates"][int(i0)],
                                 funded=r["funded"], attempts=r["attempts"], t=r["t"]))
    finally:
        V.run_phase = orig_rp
        E._target_for_segment = orig_tfs
    return pd.DataFrame(rows)


def sweep_noclock_p1(M, WT, ON, cfg):
    """Une tentative P1 par start, SANS horloge (max_cal absent => pace off)."""
    c1 = {k: v for k, v in cfg.items() if k != "max_cal"}
    c1["target"] = E.TARGET1
    hi_idx = M["n"] - NOCLOCK_MIN_TD
    rows = []
    for win, lo, hi in C22.WINDOWS:
        for i0 in V.starts(M, lo, hi, C22.COHORT_STEP):
            if int(i0) >= hi_idx:
                rows.append(dict(win=win, out="censored", used=np.nan))
                continue
            r = V.run_phase(M, int(i0), WT, ON, dict(c1))
            out = "censored" if r["out"] == "timeout" else r["out"]
            rows.append(dict(win=win, out=out, used=r["used"]))
    return pd.DataFrame(rows)


def block_ci(y, B=10, nb=4000, levels=(2.5, 5, 95, 97.5)):
    y = np.asarray(y, float)
    n = len(y)
    out = []
    for _ in range(nb):
        ix = []
        while len(ix) < n:
            s = rng.integers(0, n)
            ix.extend(((s + np.arange(B)) % n).tolist())
        out.append(y[np.array(ix[:n])].mean())
    return np.percentile(out, levels)


def neff(d):
    y = d.sort_values("start").funded.to_numpy(float)
    ac = [pd.Series(y).autocorr(k) for k in range(1, 14)]
    return len(y) / (1 + 2 * sum(max(a, 0) for a in ac if np.isfinite(a)))


def margin_stats():
    ml = np.array(E.MARGIN_LOG)
    if not len(ml):
        return dict(p50=np.nan, p99=np.nan, bind=np.nan, clip_depth=np.nan)
    over = ml[ml > 0.60]
    return dict(p50=float(np.percentile(ml, 50)), p99=float(np.percentile(ml, 99)),
                bind=float((ml > 0.60).mean()),
                clip_depth=float((1 - 0.60 / over).mean()) if len(over) else 0.0)


def attempt_breakdown():
    d = pd.DataFrame(ATTEMPTS)
    p1 = d[d.phase == "P1"]
    p2 = d[d.phase == "P2"]
    tot = max(len(d), 1)
    return dict(
        n_attempts=len(d),
        p1_pass=float((p1.out == "pass").mean()) if len(p1) else np.nan,
        p2_pass=float((p2.out == "pass").mean()) if len(p2) else np.nan,
        timeout=float((d.out == "timeout").sum() / tot),
        bust_daily=float((d.out == "bust_daily").sum() / tot),
        bust_floor=float((d.out == "bust_floor").sum() / tot),
        abandon=float((d.out == "abandon").sum() / tot),
    )


def run_arm(name, M, WT, ON, cfg):
    E.MRATE = SWING.copy()
    E.MARGIN_LOG.clear()
    d91 = sweep_funnel(M, WT, ON, dict(cfg, margin_log=True), 91,
                       record=True, pace_probe=True)
    att_bd = attempt_breakdown()
    mstats = margin_stats()
    pace = np.array([p for p, _ in PACE_SAMPLES])
    glide_on = np.array([g for _, g in PACE_SAMPLES])
    d182 = sweep_funnel(M, WT, ON, cfg, 182)
    d270 = sweep_funnel(M, WT, ON, cfg, 270)
    nc = sweep_noclock_p1(M, WT, ON, cfg)
    nc_ok = nc[nc.out != "censored"]
    p91 = d91.funded.mean()
    ci = block_ci(d91.sort_values("start").funded)
    ev_rows = d91.funded * VAL_SWC - d91.attempts * C22.FEE
    row = dict(
        arm=name, vm=cfg["vm"],
        p91_IS=round(d91[d91.win == "IS"].funded.mean() * 100, 1),
        p91_OOS=round(d91[d91.win == "OOS"].funded.mean() * 100, 1),
        p91=round(p91 * 100, 2),
        p91_ci90=[round(ci[1] * 100, 1), round(ci[2] * 100, 1)],
        p91_ci95=[round(ci[0] * 100, 1), round(ci[3] * 100, 1)],
        n_eff=round(neff(d91)),
        p182=round(d182.funded.mean() * 100, 2),
        p270=round(d270.funded.mean() * 100, 2),
        attempts=round(d91.attempts.mean(), 2),
        attempts_182=round(d182.attempts.mean(), 2),
        t_med=float(d91[d91.funded].t.median()) if d91.funded.any() else np.nan,
        pass_attempt_P1_noclock=round(float((nc_ok.out == "pass").mean()) * 100, 2)
        if len(nc_ok) else np.nan,
        noclock_n=int(len(nc_ok)), noclock_censored=int((nc.out == "censored").sum()),
        ev91=round(float(ev_rows.mean()), 1),
        ev91_val1381=round(float((d91.funded * VAL_COMM
                                  - d91.attempts * C22.FEE).mean()), 1),
        ev182=round(float((d182.funded * VAL_SWC
                           - d182.attempts * C22.FEE).mean()), 1),
        pace_mean=round(float(pace.mean()), 3) if len(pace) else np.nan,
        pace_sat2=round(float((pace >= 1.999).mean()) * 100, 1) if len(pace) else np.nan,
        pace_floor=round(float((pace <= 0.801).mean()) * 100, 1) if len(pace) else np.nan,
        glide_active=round(float(glide_on.mean()) * 100, 1) if len(glide_on) else np.nan,
        **{f"att_{k}": round(v * 100, 2) if isinstance(v, float) else v
           for k, v in att_bd.items()},
        **{f"mg_{k}": round(v, 4) for k, v in mstats.items()},
    )
    d91.to_csv(TAB / f"arm_{name}_91.csv", index=False)
    d182.to_csv(TAB / f"arm_{name}_182.csv", index=False)
    d270.to_csv(TAB / f"arm_{name}_270.csv", index=False)
    nc.to_csv(TAB / f"arm_{name}_noclock.csv", index=False)
    log(f"[{name}] p91 {row['p91']} (IS {row['p91_IS']}/OOS {row['p91_OOS']}) "
        f"p182 {row['p182']} | pass/att P1 no-clock {row['pass_attempt_P1_noclock']} "
        f"| att {row['attempts']} t_med {row['t_med']} | EV {row['ev91']} "
        f"| bind {row['mg_bind']} depth {row['mg_clip_depth']} "
        f"| to/bd/bf/ab {row['att_timeout']}/{row['att_bust_daily']}/"
        f"{row['att_bust_floor']}/{row['att_abandon']} "
        f"| pace sat2 {row['pace_sat2']}% floor {row['pace_floor']}%")
    return row, d91


def paired(dA, dB, B=10, nb=4000):
    a = dA.sort_values("start").reset_index(drop=True)
    b = dB.sort_values("start").reset_index(drop=True)
    assert (a.start.values == b.start.values).all()
    dp = (b.funded.astype(float) - a.funded.astype(float)).to_numpy()
    dev = ((b.funded * VAL_SWC - b.attempts * C22.FEE)
           - (a.funded * VAL_SWC - a.attempts * C22.FEE)).to_numpy(float)
    dbust = None
    ci_p = block_ci(dp)
    ci_e = block_ci(dev)
    return dict(dp=round(dp.mean() * 100, 2),
                dp_ci90=[round(ci_p[1] * 100, 2), round(ci_p[2] * 100, 2)],
                dp_ci95=[round(ci_p[0] * 100, 2), round(ci_p[3] * 100, 2)],
                dev=round(dev.mean(), 1),
                dev_ci90=[round(ci_e[1], 1), round(ci_e[2], 1)],
                dev_ci95=[round(ci_e[0], 1), round(ci_e[3], 1)])


def main():
    M, M_swc, WT, ON = build()
    log("stack chargé (M base + M_swc re-cost)")

    # ---- SANITY GATES (reproduction baseline ±0.5 pt, sinon STOP)
    E.MRATE = POLICY.copy()
    g1 = sweep_funnel(M, WT, ON, dict(C22.CFG_CHALLENGE), 91)
    p_pol = g1.funded.mean() * 100
    log(f"gate policy 87.0: {p_pol:.2f}")
    assert abs(p_pol - 87.01) <= 0.5, f"GATE FAIL policy {p_pol:.2f} != 87.01 -> STOP"
    E.MRATE = SWING.copy()
    g2 = sweep_funnel(M_swc, WT, ON, dict(C22.CFG_CHALLENGE), 91)
    p_swg = g2.funded.mean() * 100
    log(f"gate swing 71.4: {p_swg:.2f}")
    assert abs(p_swg - 71.43) <= 0.5, f"GATE FAIL swing {p_swg:.2f} != 71.43 -> STOP"
    log("GATES PASS (87.0 / 71.4 reproduits)")

    # ---- ARMS
    WT_D = WT.copy()
    WT_D[:, 1] *= 0.5                       # J1 budget 0.5 -> 0.25 (margin relief)
    arms = [
        ("A_vm14_clip", WT, dict(C22.CFG_CHALLENGE)),
        ("B_static_x0.24", WT, dict(C22.CFG_CHALLENGE, vm=14.0 * 0.24)),
        ("C_vm6", WT, dict(C22.CFG_CHALLENGE, vm=6.0)),
        ("C_vm8", WT, dict(C22.CFG_CHALLENGE, vm=8.0)),
        ("C_vm10", WT, dict(C22.CFG_CHALLENGE, vm=10.0)),
        ("D_vm14_J1half", WT_D, dict(C22.CFG_CHALLENGE)),
    ]
    rows, d91s = [], {}
    for name, wt, cfg in arms:
        row, d91 = run_arm(name, M_swc, wt, ON, cfg)
        rows.append(row)
        d91s[name] = d91
    res = pd.DataFrame(rows)
    res.to_csv(TAB / "arms_summary.csv", index=False)

    # ---- deltas appariés vs A + bust apparié
    tor = []
    for name in d91s:
        if name == "A_vm14_clip":
            continue
        pr = paired(d91s["A_vm14_clip"], d91s[name])
        tor.append(dict(arm=name, **pr))
    tor = pd.DataFrame(tor).sort_values("dev", ascending=False)
    tor.to_csv(TAB / "tornado_paired_vs_A.csv", index=False)
    log("tornado:\n" + tor.to_string(index=False))

    # ---- FUNDED check 1 ligne (vm1 + ORB 0.25% taper sous marge swing)
    E.MRATE = SWING.copy()
    E.MARGIN_LOG.clear()
    fcfg = dict(C22.CFG_FUNDED, margin_log=True)
    for win, lo, hi in C22.FUNDED_WINDOWS:
        for i0 in V.starts(M_swc, lo, hi, C22.FUNDED_STEP):
            V.run_funded(M_swc, int(i0), WT, ON, fcfg,
                         horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
    fm = margin_stats()
    log(f"FUNDED sous swing: marge p50 {fm['p50']*100:.0f}% p99 {fm['p99']*100:.0f}% "
        f"bind {fm['bind']*100:.2f}% -> {'AUCUN re-fit requis' if fm['p99'] < 0.6 else 'ATTENTION'}")

    # ---- décision (règle verbatim)
    elig = res[(res.p91 >= 65.0)]
    best = elig.sort_values("ev91", ascending=False).iloc[0]
    verdict = dict(best_arm=str(best["arm"]), best_ev=float(best["ev91"]),
                   A_ev=float(res[res.arm == "A_vm14_clip"].ev91.iloc[0]))
    if best["arm"] != "A_vm14_clip":
        pr = tor[tor.arm == best["arm"]].iloc[0]
        beats = pr["dev_ci90"][0] > 0
        # contrainte bust/daily-breach non dégradés (apparié au bruit CI):
        a_bd = float(res[res.arm == "A_vm14_clip"].att_bust_daily.iloc[0])
        b_bd = float(res[res.arm == best["arm"]].att_bust_daily.iloc[0])
        verdict.update(dev=pr["dev"], dev_ci90=pr["dev_ci90"],
                       beats_A_ci90=bool(beats),
                       bust_daily_A=a_bd, bust_daily_best=b_bd)
        verdict["decision"] = (f"ADOPTER {best['arm']} (futur re-run contractuel v2.3, "
                               "un changement gelé)" if beats else
                               "NULL — aucun arm ne bat A significativement (CI90), A reste")
    else:
        verdict["decision"] = "A reste (meilleur EV) — étude ferme sur null"
    summary = dict(baseline="1947163e8e92b27221cfbd9d08325e6d121796cf",
                   hypothesis="marge SWING officielle 1:30/1:15/1:9 — À CONFIRMER serveur",
                   gates=dict(policy=round(p_pol, 2), swing=round(p_swg, 2)),
                   VAL_swc=round(VAL_SWC, 0), VAL_comm=round(VAL_COMM, 0),
                   funded_margin=fm, verdict=verdict)
    (HERE / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"VERDICT: {verdict['decision']} (best EV ${verdict['best_ev']:+,.0f} "
        f"vs A ${verdict['A_ev']:+,.0f})")
    log("DONE")


if __name__ == "__main__":
    main()
