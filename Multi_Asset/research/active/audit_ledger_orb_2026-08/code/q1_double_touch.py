"""Q1 - double-touch : combien de journees voient les DEUX niveaux de l'OR
franchis, et comment la direction a-t-elle ete choisie ?

Le ledger `nq_v2_trades.parquet` porte EXACTEMENT 1 trade / 1 direction par
jour (4013 jours). Cette mesure n'a jamais ete auditee (cf. RAPPORT parent,
question 1). Elle est INDEPENDANTE des volets entry_cost/exit_cost deja
executes (2026-08-12/21) - Delta n_tests = 0, aucune hypothese nouvelle,
mesure structurelle du ledger existant.

Methode :
  - OR verifie ailleurs (entry_cost/step1-2) : 09:30-10:00 ET (30 min),
    reproduction or_hi/or_lo 4013/4013 au tick. On reutilise le meme calcul
    de fenetre (b_common.OR_BARS=6 barres M5) mais on travaille en M1 pour
    la resolution de l'ordre chronologique des franchissements.
  - Pour chaque jour : on scanne les barres M1 RTH de 10:00 ET (fin de l'OR)
    a 15:59 ET (derniere barre RTH, cf. is_rth) et on releve :
      idx_up = premiere barre M1 avec high >= or_hi
      idx_dn = premiere barre M1 avec low  <= or_lo
  - Classement :
      SINGLE      : un seul cote franchi (ou aucun)
      DOUBLE_ORD  : les deux cotes franchis, ordre resolu au M1 (idx_up != idx_dn)
      DOUBLE_AMBIG: les deux cotes franchis DANS LA MEME BARRE M1 (idx_up==idx_dn)
                    -> irreductible a cette resolution (meme signature que
                    l'ambiguite d'entree mesuree sur le corpus 109, 14.7-27.4%)
  - Concordance avec le `direction` du ledger (1=long/up, -1=short/down).
  - Pour les jours DOUBLE_* : R contrefactuel si la direction avait ete
    l'AUTRE cote (mesure d'exposition, PAS une optimisation - aucune
    modification du signal, juste la taille de l'inconnue).

Lecture seule sur ledger + M1. Ecriture uniquement dans out/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
REPO = HERE.parents[5]  # .../Algo_claude_orbledger
OUT = HERE.parents[1] / "out"
OUT.mkdir(exist_ok=True)

# reuse the shared loader/HAC/bootstrap module written for the sibling audit
BCOMMON_DIR = REPO / "Multi_Asset/research/active/orb_cost_funded_2026-08/exit_cost/code"
sys.path.insert(0, str(BCOMMON_DIR))
import b_common as bc  # noqa: E402

MAIN = Path("<HOME>/Desktop/Algo_claude")


def main() -> None:
    ledger = bc.load_ledger()
    db = bc.m1_rth()  # M1 RTH bars, roll-days excluded, tz-aware UTC index

    et_idx = db.ts.tz_convert("America/New_York")
    mod = et_idx.hour.to_numpy() * 60 + et_idx.minute.to_numpy()  # minute-of-day ET
    day_naive = db.day  # datetime64[ns] normalized, tz-naive (matches ledger.index dtype after normalize)

    # OR window: 09:30-09:59 ET inclusive (6 x M1... but ledger OR is on M5 grid,
    # bars 09:30..09:55 = 6 M5 bars = 30 min). Post-OR scan window: 10:00-15:59 ET.
    OR_START, OR_END_EXCL = 9 * 60 + 30, 10 * 60          # [570, 600)
    SCAN_START, SCAN_END_EXCL = 10 * 60, 16 * 60          # [600, 960)

    rows = []
    n_days = len(ledger)
    ledger_dates = ledger.index

    for i, dt in enumerate(ledger_dates):
        d = pd.Timestamp(dt).normalize()
        bounds = db.bounds.get(d)
        if bounds is None:
            rows.append(dict(date=d, status="NO_M1_DATA"))
            continue
        i0, i1 = bounds
        m = mod[i0:i1]
        hi = db.h[i0:i1]
        lo = db.lo[i0:i1]
        ts_day = db.ts[i0:i1]

        or_mask = (m >= OR_START) & (m < OR_END_EXCL)
        scan_mask = (m >= SCAN_START) & (m < SCAN_END_EXCL)

        if or_mask.sum() == 0 or scan_mask.sum() == 0:
            rows.append(dict(date=d, status="INSUFFICIENT_BARS"))
            continue

        or_hi_m1 = hi[or_mask].max()
        or_lo_m1 = lo[or_mask].min()

        scan_idx = np.flatnonzero(scan_mask)
        scan_hi = hi[scan_idx]
        scan_lo = lo[scan_idx]
        scan_ts = ts_day[scan_idx]

        up_hits = np.flatnonzero(scan_hi >= or_hi_m1)
        dn_hits = np.flatnonzero(scan_lo <= or_lo_m1)

        has_up = len(up_hits) > 0
        has_dn = len(dn_hits) > 0

        row = dict(
            date=d,
            or_hi_m1=or_hi_m1, or_lo_m1=or_lo_m1,
            or_hi_ledger=ledger.loc[dt, "or_hi"], or_lo_ledger=ledger.loc[dt, "or_lo"],
            direction_ledger=int(ledger.loc[dt, "direction"]),
            level_ledger=ledger.loc[dt, "level"],
            r_gross_ledger=ledger.loc[dt, "r_gross"],
        )

        if not has_up and not has_dn:
            row["status"] = "NEITHER_TOUCHED"
        elif has_up and not has_dn:
            row["status"] = "SINGLE_UP"
            row["idx_up"] = int(up_hits[0])
            row["ts_up"] = scan_ts[up_hits[0]]
        elif has_dn and not has_up:
            row["status"] = "SINGLE_DN"
            row["idx_dn"] = int(dn_hits[0])
            row["ts_dn"] = scan_ts[dn_hits[0]]
        else:
            iu, idn = int(up_hits[0]), int(dn_hits[0])
            row["idx_up"] = iu
            row["idx_dn"] = idn
            row["ts_up"] = scan_ts[iu]
            row["ts_dn"] = scan_ts[idn]
            if iu == idn:
                row["status"] = "DOUBLE_AMBIG"
                row["first_side_m1"] = "AMBIG"
            else:
                row["status"] = "DOUBLE_ORD"
                row["first_side_m1"] = "UP" if iu < idn else "DN"

        rows.append(row)

    out = pd.DataFrame(rows).set_index("date")
    out.to_parquet(OUT / "q1_double_touch_per_day.parquet")

    n = len(out)
    print("=" * 96)
    print("Q1 - DOUBLE TOUCHE : jours ou les DEUX niveaux de l'OR sont franchis (post-OR, jusqu'a 15:59 ET)")
    print("=" * 96)
    print(f"N jours ledger = {n_days} | N mesures = {n}")
    print(out["status"].value_counts())
    print()

    for s in ["NO_M1_DATA", "INSUFFICIENT_BARS", "NEITHER_TOUCHED"]:
        c = (out["status"] == s).sum()
        print(f"  {s:20s}: {c:5d} ({100*c/n:.3f}%)")

    single_up = (out["status"] == "SINGLE_UP").sum()
    single_dn = (out["status"] == "SINGLE_DN").sum()
    single = single_up + single_dn
    double_ord = (out["status"] == "DOUBLE_ORD").sum()
    double_amb = (out["status"] == "DOUBLE_AMBIG").sum()
    double_total = double_ord + double_amb

    print(f"\n  SINGLE (un seul cote franchi)          : {single:5d} ({100*single/n:.3f}%)  [up={single_up}, dn={single_dn}]")
    print(f"  DOUBLE (les deux cotes franchis)        : {double_total:5d} ({100*double_total/n:.3f}%)")
    print(f"    dont DOUBLE_ORD  (ordre resolu M1)    : {double_ord:5d} ({100*double_ord/n:.3f}%)")
    print(f"    dont DOUBLE_AMBIG (meme barre M1)     : {double_amb:5d} ({100*double_amb/n:.3f}%)  <- irreductible a cette resolution")

    # concordance direction ledger vs premier franchissement M1
    def implied_dir(row):
        if row["status"] == "SINGLE_UP":
            return 1
        if row["status"] == "SINGLE_DN":
            return -1
        if row["status"] == "DOUBLE_ORD":
            return 1 if row["first_side_m1"] == "UP" else -1
        return np.nan  # ambig or no-data: no M1-implied direction

    out["direction_implied_m1"] = out.apply(implied_dir, axis=1)
    resolved = out.dropna(subset=["direction_implied_m1"])
    concordant = (resolved["direction_implied_m1"] == resolved["direction_ledger"]).sum()
    print(f"\n  Concordance direction ledger vs 1er franchissement M1 (jours resolus, N={len(resolved)}) : "
          f"{concordant}/{len(resolved)} ({100*concordant/len(resolved):.3f}%)")

    # breakdown of concordance by SINGLE vs DOUBLE_ORD
    for s in ["SINGLE_UP", "SINGLE_DN", "DOUBLE_ORD"]:
        sub = out[out["status"] == s]
        if len(sub) == 0:
            continue
        conc = (sub["direction_implied_m1"] == sub["direction_ledger"]).sum()
        print(f"    {s:12s} N={len(sub):5d}  concordant={conc:5d} ({100*conc/len(sub):.3f}%)")

    # among DOUBLE_AMBIG: what did the ledger pick, and what's the counterfactual R
    # of the OTHER side (using r_gross scaled by the sign flip; approximate: since
    # the OTHER side's stop/level are the mirror trade, we report the ledger's own
    # r_gross with sign-flip context only as an EXPOSURE bound, not a re-test).
    amb = out[out["status"] == "DOUBLE_AMBIG"].copy()
    if len(amb) > 0:
        amb["gap_to_2nd_bar_min"] = 0  # same bar by construction
        print(f"\n  DOUBLE_AMBIG (N={len(amb)}) : direction ledger retenue vs r_gross observe (la contrepartie n'est PAS mesurable")
        print("  a la resolution M1 - c'est precisement l'ambiguite. On rapporte seulement l'exposition :")
        print(f"    r_gross moyen sur ces jours (direction ledger) : {amb['r_gross_ledger'].mean():+.4f}")
        print(f"    part de N total                                : {100*len(amb)/n:.3f}%")

    # timing gap distribution for DOUBLE_ORD (how close in time were the two touches?)
    dord = out[out["status"] == "DOUBLE_ORD"].copy()
    if len(dord) > 0:
        gap_min = (dord["idx_dn"] - dord["idx_up"]).abs()
        print(f"\n  DOUBLE_ORD (N={len(dord)}) : ecart en barres M1 entre le 1er et le 2eme franchissement")
        print(f"    p10={gap_min.quantile(.10):.0f}  p50={gap_min.quantile(.50):.0f}  "
              f"p90={gap_min.quantile(.90):.0f}  max={gap_min.max():.0f}")

    summary = pd.DataFrame([
        dict(metric="n_days_ledger", value=n_days),
        dict(metric="n_days_measured", value=n),
        dict(metric="n_single", value=int(single), pct=100*single/n),
        dict(metric="n_single_up", value=int(single_up), pct=100*single_up/n),
        dict(metric="n_single_dn", value=int(single_dn), pct=100*single_dn/n),
        dict(metric="n_double_total", value=int(double_total), pct=100*double_total/n),
        dict(metric="n_double_ord", value=int(double_ord), pct=100*double_ord/n),
        dict(metric="n_double_ambig", value=int(double_amb), pct=100*double_amb/n),
        dict(metric="n_neither", value=int((out['status']=='NEITHER_TOUCHED').sum()),
             pct=100*(out['status']=='NEITHER_TOUCHED').sum()/n),
        dict(metric="concordance_resolved_pct", value=concordant, pct=100*concordant/len(resolved)),
    ])
    summary.to_csv(OUT / "q1_double_touch_summary.csv", index=False)

    out_export = out.copy()
    for c in ["ts_up", "ts_dn"]:
        if c in out_export.columns:
            out_export[c] = out_export[c].astype(str)
    out_export.to_csv(OUT / "q1_double_touch_per_day.csv")

    print(f"\nEcrit : {OUT/'q1_double_touch_summary.csv'}")
    print(f"Ecrit : {OUT/'q1_double_touch_per_day.csv'} (+ .parquet)")


if __name__ == "__main__":
    main()
