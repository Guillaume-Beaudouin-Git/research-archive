"""Funded 2 ANS — trajectoire complete, book REELLEMENT DEPLOYE (jambes ON + ORB).

Motif : le taux de bust est une metrique BINAIRE et TARDIVE. Ce qui informe la
decision, c'est la trajectoire : combien de comptes derivent vers le plancher
$9,000, a quelle vitesse, et combien de temps ils passent sous $10,000.

Clone INSTRUMENTE de funded_instr.run_funded_instr (lui-meme clone prouve equivalent
de engine_v22.run_funded). AUCUNE modification des sources : on RECOPIE la boucle et
on n'ajoute que de l'enregistrement. Aucun effet sur la trajectoire.

Enregistre par jour : balance de cloture, equite MINIMALE intraday, retraits cumules.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "data" / "ftmo_portfolio" / "v22"))
sys.path.insert(0, str(ROOT / "Multi_Asset/research/active/orb_cost_funded_2026-08/funded_vm/code"))
import engine_v22 as V
import config_v22 as C22

E = V.E
INIT, FLOOR, BUDGET = V.INIT, V.FLOOR, V.BUDGET
OUT = ROOT / "Multi_Asset/research/active/funded_1y_mono_2026-08/out"
SPLIT, WD, VM, HORIZON = 0.8, 14, 1.00, 504          # 504 jours trades = 2 ans


def run_path(M, i0, WT, ON, cfg, horizon=HORIZON, wd_every=WD):
    """Identique a funded_instr.run_funded_instr + enregistrement de la trajectoire."""
    bal = INIT
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    total_wd, n_pay, days = 0.0, 0, 0
    n_brk = 0
    i = i0
    path = []                                          # (jour, bal_fin, eq_min, cum_wd)
    while i < M["n"] and days < horizon:
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = E.breaker_line(bal, cfg)
        px_day, bounds = M["days"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        flat_today = False
        eq_min_day = bal
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b:
                continue
            seg = px_day[a:b]
            if s == 4 and orb_live:
                bal += orb_risk * M["orb_R"][i]
                orb_live = False
            dip = 1.31 * orb_risk if (orb_live and s in (2, 3)) else 0.0
            if not flat_today:
                tgt, _ = E._target_for_segment(s, i, M, WT, ON, cfg, bal, pos,
                                               avg, seg[0], i0, cfg["vm"])
                if tgt is not None:
                    bal = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            if len(eq):
                eq_min_day = min(eq_min_day, float(eq.min()))
            bad = eq < lim_eff
            brk = eq < brk_line
            if cfg.get("brk_needs_pos") and not np.any(pos):
                brk = brk & False
            tb = int(np.argmax(bad)) if bad.any() else len(seg)
            tk = int(np.argmax(brk)) if brk.any() else len(seg)
            if min(tb, tk) < len(seg):
                if tb <= tk:
                    e = float(eq[tb])
                    path.append((days, e, e, total_wd))
                    return dict(wd=total_wd, payouts=n_pay, life=days, busted=True,
                                residual=0.0, n_brk=n_brk), path
                bal = E._flat(pos, avg, bal, seg[tk], M["rt"])
                n_brk += 1
                flat_today = True
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        days += 1
        i += 1
        if days % wd_every == 0 and bal > INIT:
            total_wd += bal - INIT
            n_pay += 1
            bal = INIT
        path.append((days, bal, eq_min_day, total_wd))
    px_last = M["days"][min(i, M["n"] - 1)][0][-1]
    res = max(bal + E._mtm(pos, avg, px_last) - INIT, 0.0)
    return dict(wd=total_wd, payouts=n_pay, life=days, busted=False,
                residual=res, n_brk=n_brk), path


SCENARIOS = [("ORB_OFF", None), ("0.96_mesure", 0.96), ("2.17_allin", 2.17)]

rows, paths = [], []
for nom, cout in SCENARIOS:
    M = V.load_stack(orb_rt_bps=("era" if cout is None else cout))
    WT_df, ON_df = V.E.build_signals()
    WT_full, ON = V.align(M, WT_df, ON_df)
    WT_mono = np.zeros_like(WT_full)                   # or = 0, J1 = 0 (regime actuel)
    idx = M["dates_idx"]
    cfg = dict(C22.CFG_FUNDED_V28, vm=VM,
               orb_risk=(0.0 if cout is None else 0.0025))
    for cid, i0 in enumerate(V.starts(M, idx.min(), idx.max(), 10)):
        if i0 + HORIZON >= M["n"]:
            continue
        r, p = run_path(M, int(i0), WT_mono, ON, cfg)
        r.update(scenario=nom, cohort=cid, start=idx[int(i0)])
        rows.append(r)
        for (dd, bb, em, cw) in p:
            paths.append((nom, cid, dd, bb, em, cw))
    print(f"  fait : {nom}", flush=True)

d = pd.DataFrame(rows)
d["brut"] = d.wd + d.residual
d["net_trader"] = SPLIT * d.brut
P = pd.DataFrame(paths, columns=["scenario", "cohort", "jour", "bal", "eq_min", "cum_wd"])
P["equity_totale"] = P.bal + P.cum_wd                  # valeur economique du compte
P.to_parquet(OUT / "paths_2ans.parquet", index=False)

# --- metriques de PROXIMITE AU PLANCHER, par cohorte -------------------------
g = P.groupby(["scenario", "cohort"])
prox = g.agg(eq_min_ever=("eq_min", "min"),
             bal_min=("bal", "min"),
             jours=("jour", "max")).reset_index()
sous10k = (P.assign(u=P.bal < INIT).groupby(["scenario", "cohort"]).u.mean()
           .rename("frac_sous_10k").reset_index())
prox = prox.merge(sous10k, on=["scenario", "cohort"]).merge(
    d[["scenario", "cohort", "net_trader", "payouts", "busted", "n_brk"]],
    on=["scenario", "cohort"])
prox["buffer_conso_pct"] = 100 * (INIT - prox.eq_min_ever) / (INIT - FLOOR)
prox.to_csv(OUT / "proximite_plancher_2ans.csv", index=False)

print("\n" + "=" * 108)
print("FUNDED 2 ANS — book deploye (jambes ON + ORB), vm 1.0, or & J1 a zero")
print("=" * 108)
h = (f"{'scenario':<13}{'N':>4}{'net MED':>9}{'p5':>8}{'p25':>8}{'p75':>9}"
     f"{'eqmin MED':>11}{'buffer%':>9}{'P<9500':>8}{'P<9250':>8}{'bust':>7}"
     f"{'%tps<10k':>10}{'payouts':>9}")
print(h); print("-" * len(h))
agg = []
for s, q in prox.groupby("scenario", sort=False):
    n = len(q)
    row = dict(scenario=s, n=n,
               net_med=q.net_trader.median(), p5=q.net_trader.quantile(.05),
               p25=q.net_trader.quantile(.25), p75=q.net_trader.quantile(.75),
               eqmin_med=q.eq_min_ever.median(),
               buffer_med=q.buffer_conso_pct.median(),
               p9500=100 * (q.eq_min_ever < 9500).mean(),
               p9250=100 * (q.eq_min_ever < 9250).mean(),
               bust=100 * q.busted.mean(),
               tps=100 * q.frac_sous_10k.median(),
               payouts=q.payouts.mean())
    agg.append(row)
    print(f"{s:<13}{n:>4}{row['net_med']:>9.0f}{row['p5']:>8.0f}{row['p25']:>8.0f}"
          f"{row['p75']:>9.0f}{row['eqmin_med']:>11.0f}{row['buffer_med']:>8.0f}%"
          f"{row['p9500']:>7.0f}%{row['p9250']:>7.0f}%{row['bust']:>6.0f}%"
          f"{row['tps']:>9.0f}%{row['payouts']:>9.1f}")
pd.DataFrame(agg).to_csv(OUT / "resume_2ans.csv", index=False)

# --- EVOLUTION du PnL par trimestre ------------------------------------------
print("\n" + "=" * 108)
print("EVOLUTION — valeur economique cumulee (retraits + solde - 10000), part trader 0.8")
print("=" * 108)
JAL = [63, 126, 189, 252, 315, 378, 441, 504]
h2 = f"{'scenario':<13}" + "".join(f"{'T'+str(k+1):>11}" for k in range(len(JAL)))
print(h2); print("-" * len(h2))
ev = []
for s in [x[0] for x in SCENARIOS]:
    q = P[P.scenario == s]
    med, p25l = [], []
    for j in JAL:
        v = q[q.jour == j]
        val = SPLIT * (v.equity_totale - INIT)
        med.append(val.median() if len(val) else np.nan)
        p25l.append(val.quantile(.25) if len(val) else np.nan)
    ev.append(dict(scenario=s, **{f"T{k+1}_med": m for k, m in enumerate(med)},
                   **{f"T{k+1}_p25": m for k, m in enumerate(p25l)}))
    print(f"{s:<13}" + "".join(f"{m:>11.0f}" for m in med))
print("\n  (p25 = quart le moins favorable)")
for r in ev:
    print(f"{r['scenario']:<13}" + "".join(f"{r[f'T{k+1}_p25']:>11.0f}" for k in range(len(JAL))))
pd.DataFrame(ev).to_csv(OUT / "evolution_2ans.csv", index=False)
