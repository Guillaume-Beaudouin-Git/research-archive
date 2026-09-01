"""Q2 (derapage ENTREE) + Q3a (derapage SORTIE AU STOP), mesure INDEPENDANTE en M1.

Mesure directe, sans dependre des sorties du volet soeur `orb_cost_funded_2026-08`
(dont les resultats concordent - voir RAPPORT.md - mais qui vivent hors de ce
dossier). Delta n_tests = 0 : on re-price un ledger existant, on ne teste rien.

Note de spec (important) : ce ledger (`nq_v2_trades.parquet`, PRESPEC V2 baseline,
`PRESPEC_orb_signature_2026-06.md` §0/§3) a un OR de **30 min** (09:30-10:00 ET,
6 barres M5) et **PAS de TP fixe** : `outcome` ne prend que les valeurs {STOP,
TIME_STOP} (verifie : value_counts() = {TIME_STOP: 2423, STOP: 1590}, aucun 'TP').
Le time-stop est la cloture RTH (~16:00 ET), pas 12:30 ET. Ceci NE correspond PAS
a la description generique "OR 09:30-09:45, TP 1.5R, time-stop 12:30" citee dans
CLAUDE.md pour l'ancienne Strategy C (iter_10, NQ) - ce sont deux sleeves ORB
DIFFERENTES. Le sleeve arme en production funded (`FU_ORB_RISK`) est celui de
CE ledger (V2 baseline, 30 min OR, pas de TP). Donc : aucune sortie TP a mesurer
ici, c'est une non-applicabilite de spec, pas un trou de mesure - documente
explicitement plutot que suppose.

L60 (obligatoire) : on mesure la part de barres M1 a fourchette NULLE (open==
high==low==close) sur les fenetres utilisees AVANT de s'en servir comme prix.

Ecriture uniquement dans out/. Lecture seule sur ledger + M1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
REPO = HERE.parents[5]
OUT = HERE.parents[1] / "out"
OUT.mkdir(exist_ok=True)

BCOMMON_DIR = REPO / "Multi_Asset/research/active/orb_cost_funded_2026-08/exit_cost/code"
sys.path.insert(0, str(BCOMMON_DIR))
import b_common as bc  # noqa: E402

TICK = 0.25  # NQ tick size, points


def main() -> None:
    led = bc.load_ledger()
    db = bc.m1_rth()
    et_idx = db.ts.tz_convert("America/New_York")
    mod = et_idx.hour.to_numpy() * 60 + et_idx.minute.to_numpy()

    print("Outcomes dans le ledger :", led["outcome"].value_counts().to_dict())
    assert set(led["outcome"].unique()) <= {"STOP", "TIME_STOP"}, "outcome inattendu (TP ?)"

    # -------------------------------------------------------------
    # L60 - part de barres a fourchette NULLE sur le M1 RTH complet
    # -------------------------------------------------------------
    flat = (db.o == db.h) & (db.h == db.lo) & (db.lo == db.c)
    print("\n" + "=" * 96)
    print("L60 - CONTROLE PREALABLE : part de barres M1 RTH a fourchette NULLE")
    print("=" * 96)
    print(f"  N barres M1 RTH (hors roll-day) = {len(flat):,}")
    print(f"  fourchette nulle (o=h=l=c)       = {flat.sum():,} ({100*flat.mean():.4f}%)")
    print("  -> lecture : un print de reglement n'est pas un prix (L60). Fraction faible")
    print("     ATTENDUE sur du futures 1-min liquide RTH ; a re-verifier localement autour")
    print("     des barres d'entree/sortie utilisees ci-dessous, pas seulement globalement.")

    entry_rows = []
    exit_rows = []
    flat_flags = []

    for dt, r in led.iterrows():
        d = pd.Timestamp(dt).normalize()
        bounds = db.bounds.get(d)
        direction = int(r["direction"])
        level = float(r["level"])
        stop_eff = float(r["stop_eff"])
        bi = int(r["bi"])
        outcome = r["outcome"]
        risk_pts = abs(level - stop_eff)
        lev = level / risk_pts if risk_pts > 0 else np.nan

        if bounds is None:
            entry_rows.append(dict(date=dt, ok=False, reason="NO_M1_DATA"))
            continue
        i0, i1 = bounds
        m = mod[i0:i1]
        o, h, lo, c = db.o[i0:i1], db.h[i0:i1], db.lo[i0:i1], db.c[i0:i1]

        # ------------------------------------------------------------------
        # ENTREE : barre M1 de declenchement = 1ere barre du bucket M5 `bi`
        # (569+bi*5 .. +5) qui franchit `level` dans le sens de `direction`.
        # ------------------------------------------------------------------
        m5_start = 570 + bi * 5
        m5_mask = (m >= m5_start) & (m < m5_start + 5)
        idxs = np.flatnonzero(m5_mask)
        if len(idxs) == 0:
            entry_rows.append(dict(date=dt, ok=False, reason="NO_M1_IN_M5_WINDOW",
                                    direction=direction, level=level, risk_pts=risk_pts, lev=lev))
            continue

        trig = None
        for k in idxs:
            if direction == 1 and h[k] >= level:
                trig = k
                break
            if direction == -1 and lo[k] <= level:
                trig = k
                break
        if trig is None:
            entry_rows.append(dict(date=dt, ok=False, reason="NO_TRIGGER_IN_WINDOW",
                                    direction=direction, level=level, risk_pts=risk_pts, lev=lev))
            continue

        bar_flat = bool(o[trig] == h[trig] == lo[trig] == c[trig])
        flat_flags.append(bar_flat)

        if direction == 1:
            fill = max(o[trig], level)
            gap_pts = fill - level
        else:
            fill = min(o[trig], level)
            gap_pts = level - fill

        entry_rows.append(dict(
            date=dt, ok=True, direction=direction, level=level, risk_pts=risk_pts, lev=lev,
            entry_bar_open=float(o[trig]), fill_stop_market=float(fill),
            gap_pts=float(gap_pts), gap_bps=float(gap_pts / level * 1e4),
            gap_R=float(gap_pts / risk_pts) if risk_pts > 0 else np.nan,
            gap_ticks=float(gap_pts / TICK), bar_flat=bar_flat,
        ))

        # ------------------------------------------------------------------
        # SORTIE AU STOP (Q3a, L59) : uniquement outcome == STOP. On scanne
        # les barres M1 APRES la barre d'entree (meme jour, RTH) pour trouver
        # la 1ere qui franchit `stop_eff` en sens adverse.
        # ------------------------------------------------------------------
        if outcome != "STOP":
            continue

        scan_idx = np.arange(trig, len(m))  # peut inclure la barre d'entree elle-meme
        st = None
        for k in scan_idx:
            if direction == 1 and lo[k] <= stop_eff:
                st = k
                break
            if direction == -1 and h[k] >= stop_eff:
                st = k
                break
        if st is None:
            exit_rows.append(dict(date=dt, ok=False, reason="STOP_NOT_FOUND_M1",
                                   direction=direction, stop_eff=stop_eff, risk_pts=risk_pts, lev=lev))
            continue

        bar_flat_exit = bool(o[st] == h[st] == lo[st] == c[st])

        if direction == 1:
            fill_s = min(o[st], stop_eff)
            gap_pts_s = stop_eff - fill_s  # >=0, cote adverse
        else:
            fill_s = max(o[st], stop_eff)
            gap_pts_s = fill_s - stop_eff

        exit_rows.append(dict(
            date=dt, ok=True, direction=direction, stop_eff=stop_eff, risk_pts=risk_pts, lev=lev,
            stop_bar_open=float(o[st]), fill_stop_market=float(fill_s),
            same_bar_as_entry=bool(st == trig),
            gap_pts=float(gap_pts_s), gap_bps=float(gap_pts_s / stop_eff * 1e4),
            gap_R=float(gap_pts_s / risk_pts) if risk_pts > 0 else np.nan,
            gap_ticks=float(gap_pts_s / TICK), bar_flat=bar_flat_exit,
        ))

    E = pd.DataFrame(entry_rows).set_index("date")
    X = pd.DataFrame(exit_rows).set_index("date")
    E.to_csv(OUT / "q2_entry_slippage_per_trade.csv")
    X.to_csv(OUT / "q3a_exit_stop_slippage_per_trade.csv")

    # ---------------- summaries ----------------
    print("\n" + "=" * 96)
    print("Q2 - DERAPAGE D'ENTREE (barre M1 de declenchement vs `level`)")
    print("=" * 96)
    ok = E[E["ok"]]
    print(f"  N ledger = {len(led)}  N resolus en M1 = {len(ok)}  ({100*len(ok)/len(led):.3f}%)")
    print(f"  N non resolus : {(~E['ok']).sum()}  raisons: {E.loc[~E['ok'],'reason'].value_counts().to_dict()}")
    n_gap = (ok["gap_pts"] > 0).sum()
    print(f"  barres de declenchement qui OUVRENT AU-DELA du niveau : {n_gap}/{len(ok)} ({100*n_gap/len(ok):.4f}%)")
    print(f"  barres a fourchette nulle (L60) parmi les barres de declenchement : "
          f"{ok['bar_flat'].sum()}/{len(ok)} ({100*ok['bar_flat'].mean():.4f}%)")
    for col, unit in [("gap_pts", "pt"), ("gap_bps", "bps"), ("gap_R", "R")]:
        q = ok[col].describe(percentiles=[.5, .75, .9, .95, .99])
        print(f"  {col:8s} ({unit:3s}): mean={ok[col].mean():+.6f}  p50={q['50%']:.6f}  "
              f"p90={q['90%']:.6f}  p99={q['99%']:.6f}  max={ok[col].max():.6f}")
    mean_gap_R, se_gap_R, t_gap_R = bc.hac_tstat(ok["gap_R"].to_numpy(), lags=6)
    print(f"  gap_R : HAC(6) mean={mean_gap_R:.6f}  t={t_gap_R:.3f}  (N={len(ok)})")
    print(f"  budget d'entree : gross +0.0492 R / trade -> breakeven a "
          f"{0.0492/ok['gap_R'].mean():.2f}x le derapage moyen mesure" if ok['gap_R'].mean() > 0 else "")

    print("\n" + "=" * 96)
    print("Q3a - DERAPAGE DE SORTIE AU STOP (L59) - barre M1 de franchissement vs `stop_eff`")
    print("=" * 96)
    xok = X[X["ok"]]
    print(f"  N sorties STOP dans le ledger = {(led['outcome']=='STOP').sum()}  N resolus en M1 = {len(xok)}")
    print(f"  N non resolus : {(~X['ok']).sum() if len(X) else 0}")
    n_gap_x = (xok["gap_pts"] > 0).sum()
    print(f"  barres de stop qui OUVRENT AU-DELA du stop : {n_gap_x}/{len(xok)} ({100*n_gap_x/len(xok):.4f}%)")
    print(f"  barres a fourchette nulle (L60) parmi les barres de stop : "
          f"{xok['bar_flat'].sum()}/{len(xok)} ({100*xok['bar_flat'].mean():.4f}%)")
    print(f"  barre de stop == barre d'entree : {xok['same_bar_as_entry'].sum()} ({100*xok['same_bar_as_entry'].mean():.4f}%)")
    for col, unit in [("gap_pts", "pt"), ("gap_bps", "bps"), ("gap_R", "R")]:
        q = xok[col].describe(percentiles=[.5, .75, .9, .95, .99])
        print(f"  {col:8s} ({unit:3s}): mean={xok[col].mean():+.6f}  p50={q['50%']:.6f}  "
              f"p90={q['90%']:.6f}  p99={q['99%']:.6f}  max={xok[col].max():.6f}")
    mean_gap_Rx, se_gap_Rx, t_gap_Rx = bc.hac_tstat(xok["gap_R"].to_numpy(), lags=6)
    print(f"  gap_R (STOP) : HAC(6) mean={mean_gap_Rx:.6f}  t={t_gap_Rx:.3f}  (N={len(xok)})")

    print("\n  Sorties au TP : NON APPLICABLE - ce ledger n'a pas de TP fixe "
          "(outcome in {STOP, TIME_STOP} uniquement, 0 trade a TP). Voir docstring / q3b (TIME_STOP).")

    summary = pd.DataFrame([
        dict(section="Q2_entry", N=len(ok), n_gap=int(n_gap), pct_gap=100*n_gap/len(ok),
             mean_gap_pts=ok["gap_pts"].mean(), mean_gap_bps=ok["gap_bps"].mean(),
             mean_gap_R=ok["gap_R"].mean(), t_hac6_gap_R=t_gap_R,
             pct_flat_bar_L60=100*ok['bar_flat'].mean()),
        dict(section="Q3a_exit_stop", N=len(xok), n_gap=int(n_gap_x), pct_gap=100*n_gap_x/len(xok),
             mean_gap_pts=xok["gap_pts"].mean(), mean_gap_bps=xok["gap_bps"].mean(),
             mean_gap_R=xok["gap_R"].mean(), t_hac6_gap_R=t_gap_Rx,
             pct_flat_bar_L60=100*xok['bar_flat'].mean()),
    ])
    summary.to_csv(OUT / "q2_q3a_summary.csv", index=False)

    pd.DataFrame([dict(scope="M1_RTH_all", n=len(flat), n_flat=int(flat.sum()), pct_flat=100*flat.mean()),
                  dict(scope="entry_trigger_bars", n=len(ok), n_flat=int(ok['bar_flat'].sum()), pct_flat=100*ok['bar_flat'].mean()),
                  dict(scope="stop_exit_bars", n=len(xok), n_flat=int(xok['bar_flat'].sum()), pct_flat=100*xok['bar_flat'].mean())]
                 ).to_csv(OUT / "l60_flat_bar_check.csv", index=False)

    print(f"\nEcrit : {OUT/'q2_entry_slippage_per_trade.csv'}")
    print(f"Ecrit : {OUT/'q3a_exit_stop_slippage_per_trade.csv'}")
    print(f"Ecrit : {OUT/'q2_q3a_summary.csv'}")
    print(f"Ecrit : {OUT/'l60_flat_bar_check.csv'}")


if __name__ == "__main__":
    main()
