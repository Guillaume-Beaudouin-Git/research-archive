"""Q2-Q5 : verdict corrige par jambe, avant/apres correction, vs R2.

Reutilise (lecture seule) les mesures deja produites et validees par le volet
soeur `orb_cost_funded_2026-08` (2026-08-12/21), sans les recalculer depuis
zero (Delta n_tests = 0 : on re-price, on ne re-teste rien) :

  - Q2 (entree) : `entry_cost/out/` a mesure le canal GAP a l'entree = 11/4013
    (0.274%), tous d'exactement 1 tick -> economiquement nul (0.0000287 R en
    "gap pur"). Le tick lui-meme (b1_plus1tick, +0.0109 R/trade) EST le
    plancher microstructurel minimal, mais il ne doit PAS etre cumule avec un
    cout de spread RT complet (le tick ~= le spread inside sur NQ RTH) - voir
    entry_cost/RAPPORT.md §3.1 "attention au double comptage".
  - Q3 (sortie) : `exit_cost/out/b2_exit_stop.txt` a mesure le canal GAP a la
    sortie STOP = 0/1587 (0.00%) en M1 ET en M5 - le canal L59 est VIDE ici
    (mecanisme : intraday RTH continu, pas de gap overnight). Ce script
    verifie EN PLUS, ce qui n'etait pas fait, la fidelite des sorties
    TIME_STOP (pas de TP dans ce ledger - voir note ci-dessous) : exit_px vs
    dernier close M1 RTH du jour.
  - Q6 (vehicule) : le ledger est NQ futures ; la mesure de spread natif FTMO
    (0.96-1.05 bps, `PREREGISTRATION.md` AMENDEMENT n1) vient du CFD US100 -
    c'est la SEULE piece "cout" qui vient d'un instrument different du ledger,
    et c'est deliberement le cas : le gap-a-l'entree/sortie est mesure SUR
    NQ (le vehicule du ledger), le spread bid/ask est mesure SUR US100.cash
    (le vehicule de PRODUCTION), parce que c'est le spread qui domine
    economiquement (1.0-2.2 bps contre 0.0000287-0.0109 R de gap) et qu'un
    spread NQ CME n'est pas le cout paye en production.

Ce script calcule, INDEPENDAMMENT, le verdict par JAMBE (long / short) avant
et apres correction, avec HAC lag-6 + block-bootstrap (reutilise b_common),
et localise le point mort de la jambe courte sur la serie corrigee.

Aucune modification du ledger. Ecriture uniquement dans out/.
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

MAIN = Path("<HOME>/Desktop/Algo_claude")
ENTRY_REPRICED = MAIN / "Multi_Asset/research/active/orb_cost_funded_2026-08/entry_cost/out/R_repriced_entry.parquet"


def leg_stats(r: np.ndarray) -> dict:
    mean, se, t = bc.hac_tstat(r, lags=6)
    lo, hi, _ = bc.boot_ci(r, n_boot=5000, mean_block=10.0)
    return dict(N=len(r), mean_R=mean, se_hac6=se, t_hac6=t, ci95_lo=lo, ci95_hi=hi,
                r2_pass=bool(t > 2.0 and not (lo <= 0 <= hi)))


def main() -> None:
    led = bc.load_ledger()
    entry = pd.read_parquet(ENTRY_REPRICED)

    assert (led["r_gross"].values == entry["r_gross"].values).all() if "r_gross" in entry else True

    direction = led["direction"].to_numpy()
    r_gross = led["r_gross"].to_numpy(dtype=float)
    lev = entry["lev"].to_numpy(dtype=float)  # entry/|entry-stop_eff|, per trade

    long_m = direction == 1
    short_m = direction == -1
    print(f"N total={len(led)}  long={long_m.sum()}  short={short_m.sum()}")

    # ------------------------------------------------------------------
    # Q3b — fidelite des sorties TIME_STOP (pas de TP dans ce ledger)
    # ------------------------------------------------------------------
    db = bc.m1_rth()
    ts_rows = []
    for dt, r in led[led["outcome"] == "TIME_STOP"].iterrows():
        d = pd.Timestamp(dt).normalize()
        b = db.bounds.get(d)
        if b is None:
            continue
        i0, i1 = b
        ts_rows.append((dt, db.c[i1 - 1], r["exit_px"]))
    TS = pd.DataFrame(ts_rows, columns=["date", "m1_last_close", "exit_px_ledger"]).set_index("date")
    ts_exact = int((TS["m1_last_close"] == TS["exit_px_ledger"]).sum())
    print("\n" + "=" * 96)
    print("Q3b — FIDELITE DES SORTIES TIME_STOP (pas de TP dans ce ledger — outcome in {STOP, TIME_STOP} uniquement)")
    print("=" * 96)
    print(f"  N TIME_STOP = {len(TS)}")
    print(f"  exit_px == dernier close M1 RTH du jour, exact : {ts_exact}/{len(TS)} ({100*ts_exact/len(TS):.3f}%)")
    print("  Lecture : pas de seuil de prix a franchir (sortie deterministe sur le temps),")
    print("  donc pas de canal GAP au sens L59. L'idealisation residuelle est la meme")
    print("  microstructure (spread/tick) qu'un ordre marche quelconque a la cloture RTH —")
    print("  deja incluse dans le cout de spread mesure ci-dessous (Q6), pas un canal a part.")

    pd.DataFrame([dict(metric="n_time_stop", value=len(TS)),
                  dict(metric="n_exact_close_match", value=ts_exact),
                  dict(metric="pct_exact", value=100 * ts_exact / len(TS)),
                  dict(metric="n_stop_outcomes", value=int((led['outcome']=='STOP').sum())),
                  dict(metric="n_tp_outcomes_note", value=0)]
                 ).to_csv(OUT / "q3b_timestop_fidelity.csv", index=False)

    # ------------------------------------------------------------------
    # Q4/Q5 — verdict par jambe, avant/apres correction, sweep de cout
    # ------------------------------------------------------------------
    # cout RT en bps -> R par trade : cost_R = bps * 1e-4 * lev  (lev = entry/|entry-stop_eff|)
    # bps testes : 0 (reference/avant correction) ; 0.962 et 1.045 (fenetre ORB / mediane
    # toutes heures, spread natif FTMO US100, AMENDEMENT n1) ; 1.80 (ancienne entree R2,
    # cross-broker, gardee pour continuite historique) ; 2.17 (tout-compris n=12 fills reels).
    cost_levels = {
        "0.00_reference_avant_correction": 0.0,
        "0.962_spread_natif_fenetre_ORB": 0.962,
        "1.045_spread_natif_median_allhours": 1.045,
        "1.80_ancienne_entree_R2_cross_broker": 1.80,
        "2.17_tout_compris_n12_fills_reels": 2.17,
    }

    rows = []
    for label, bps in cost_levels.items():
        cost_R = bps * 1e-4 * lev
        r_net = r_gross - cost_R
        for name, m in [("ALL", np.ones(len(r_net), bool)), ("LONG", long_m), ("SHORT", short_m)]:
            s = leg_stats(r_net[m])
            s.update(cost_bps=bps, cost_label=label, leg=name)
            rows.append(s)

    V = pd.DataFrame(rows)[["cost_label", "cost_bps", "leg", "N", "mean_R", "se_hac6",
                             "t_hac6", "ci95_lo", "ci95_hi", "r2_pass"]]
    V.to_csv(OUT / "q4_verdict_by_leg_cost_sweep.csv", index=False)

    print("\n" + "=" * 96)
    print("Q4/Q5 — VERDICT PAR JAMBE, SWEEP DE COUT (R2 = t HAC(6) > 2.0 ET IC95 excluant 0)")
    print("=" * 96)
    with pd.option_context("display.width", 160, "display.max_rows", 50):
        print(V.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    # sanity: reproduce the task's stated "valeurs de reference" at bps=0
    ref0 = V[(V.cost_bps == 0.0)]
    print("\n  Verification vs valeurs de reference (avant correction, r_gross) :")
    for leg in ["ALL", "LONG", "SHORT"]:
        row = ref0[ref0.leg == leg].iloc[0]
        print(f"    {leg:5s}  N={int(row.N):5d}  mean_R={row.mean_R:+.4f}  t_HAC6={row.t_hac6:.3f}")

    # ------------------------------------------------------------------
    # Q5 — point mort (breakeven) de la jambe courte, sur mean_R et sur t=2.0
    # ------------------------------------------------------------------
    def short_mean_at(bps: float) -> float:
        cost_R = bps * 1e-4 * lev[short_m]
        return float(np.mean(r_gross[short_m] - cost_R))

    def short_t_at(bps: float) -> float:
        cost_R = bps * 1e-4 * lev[short_m]
        _, _, t = bc.hac_tstat(r_gross[short_m] - cost_R, lags=6)
        return t

    # bissection simple sur une grille fine
    grid = np.linspace(0, 5, 20001)
    means = np.array([short_mean_at(b) for b in grid])
    ts = np.array([short_t_at(b) for b in grid])

    be_mean_idx = np.argmin(np.abs(means))
    be_mean_bps = float(grid[be_mean_idx])

    below2 = np.where(ts <= 2.0)[0]
    be_t2_bps = float(grid[below2[0]]) if len(below2) else float("nan")

    print("\n" + "=" * 96)
    print("Q5 — POINT MORT DE LA JAMBE COURTE (recalcule independamment)")
    print("=" * 96)
    print(f"  Point mort MOYENNE (mean_R_short = 0)      : {be_mean_bps:.3f} bps RT")
    print(f"  Point mort SEUIL R2 (t_HAC6_short = 2.0)   : {be_t2_bps:.3f} bps RT"
          f"  (short passe SOUS t=2.0 des la premiere unite de cout : t a 0 bps = {ts[0]:.3f})")
    print(f"  Reference AMENDEMENT n1 (methode differente, cout total non decompose par bps fin) : 1.94 bps")

    pd.DataFrame([
        dict(metric="short_breakeven_mean_bps", value=be_mean_bps),
        dict(metric="short_breakeven_t2_bps", value=be_t2_bps),
        dict(metric="short_t_at_0bps", value=float(ts[0])),
        dict(metric="short_mean_at_0bps", value=float(means[0])),
        dict(metric="reference_amendement_n1_bps", value=1.94),
    ]).to_csv(OUT / "q5_short_breakeven.csv", index=False)

    curve = pd.DataFrame({"cost_bps": grid, "short_mean_R": means, "short_t_hac6": ts})
    curve.to_csv(OUT / "q5_short_breakeven_curve.csv", index=False)

    # ------------------------------------------------------------------
    # sum-R view (comme AMENDEMENT n1 §complement A1) pour contexte P&L total
    # ------------------------------------------------------------------
    print("\n" + "=" * 96)
    print("Sum(R) par jambe et par cout (contexte P&L total, risque fixe -> Sigma R compte, pas la moyenne)")
    print("=" * 96)
    sum_rows = []
    for label, bps in cost_levels.items():
        cost_R = bps * 1e-4 * lev
        r_net = r_gross - cost_R
        row = dict(cost_label=label, cost_bps=bps,
                   sum_long=float(r_net[long_m].sum()), sum_short=float(r_net[short_m].sum()),
                   sum_all=float(r_net.sum()))
        row["long_only_vs_two_sided_pct"] = 100 * (row["sum_long"] - row["sum_all"]) / abs(row["sum_all"])
        sum_rows.append(row)
    S = pd.DataFrame(sum_rows)
    S.to_csv(OUT / "q4_sumR_by_leg_cost_sweep.csv", index=False)
    print(S.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    print(f"\nEcrit : {OUT/'q4_verdict_by_leg_cost_sweep.csv'}")
    print(f"Ecrit : {OUT/'q5_short_breakeven.csv'} + q5_short_breakeven_curve.csv")
    print(f"Ecrit : {OUT/'q4_sumR_by_leg_cost_sweep.csv'}")
    print(f"Ecrit : {OUT/'q3b_timestop_fidelity.csv'}")


if __name__ == "__main__":
    main()
