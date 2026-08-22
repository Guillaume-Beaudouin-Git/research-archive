"""Volet C / H4 — véhicule : ledger NQ futures vs exécution US100.cash CFD (L33).

Sources (LECTURE SEULE) :
  PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet
  specs live US100.cash lues sur le terminal FTMO (market_export.json, VPS) :
      contract=1.0, tick_size=0.01, tick_value=0.01 USD, digits=2,
      margin_rate=0.066667, swap_long=-620.43 pts, swap_short=+2.91 pts
  PropFirms/ftmo/rules.md:118  -> indices : commission ZÉRO

Sortie : out/s4_*.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
LEDGER = (ROOT / "PropFirms" / "ftmo" / "program_2026-06" / "ftmo_research" /
          "audit" / "nq_v2_trades.parquet")
OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(parents=True, exist_ok=True)

# --- spécifications d'instrument -------------------------------------------
# NQ / MNQ : CME. tick 0.25 pt. NQ = 20 USD/pt, MNQ = 2 USD/pt.
NQ_TICK_PTS = 0.25
NQ_USD_PER_PT = 20.0
MNQ_USD_PER_PT = 2.0
NQ_COMM_RT_USD = 4.00       # IBKR/Tradovate ordre de grandeur, RT, 1 contrat NQ
MNQ_COMM_RT_USD = 2.15      # CLAUDE.md §Costs : "Futures MNQ ~$2.15 RT (Tradovate)"
# US100.cash CFD FTMO
CFD_TICK_PTS = 0.01
CFD_USD_PER_PT_PER_LOT = 1.0
CFD_COMM_RT_USD = 0.0       # rules.md:118 — zéro commission sur les indices


def main() -> None:
    d = pd.read_parquet(LEDGER)
    d = d.copy()
    d["lev"] = d["entry"] / (d["entry"] - d["stop_eff"]).abs()
    d["stop_dist_pts"] = (d["entry"] - d["stop_eff"]).abs()
    d["year"] = d.index.year

    # ---- 1. sensibilité coût -> R, par trade (et pas seulement à la médiane) ----
    lev = d["lev"]
    sens = {
        "N_trades": int(len(d)),
        "lev_med": float(lev.median()), "lev_moy": float(lev.mean()),
        "lev_p10": float(np.percentile(lev, 10)), "lev_p90": float(np.percentile(lev, 90)),
        "lev_p99": float(np.percentile(lev, 99)), "lev_max": float(lev.max()),
        "R_par_bps_a_la_mediane": float(lev.median()) / 1e4,
        "R_par_bps_en_MOYENNE_de_trades": float(lev.mean()) / 1e4,
        "r_gross_moyen": float(d["r_gross"].mean()),
        "stop_dist_pts_med": float(d["stop_dist_pts"].median()),
        "entry_med": float(d["entry"].median()),
        "part_long": float((d["direction"] > 0).mean()),
        "part_STOP": float((d["outcome"] == "STOP").mean()),
        "part_TIME_STOP": float((d["outcome"] == "TIME_STOP").mean()),
    }
    # bps de RT qui annule r_gross, en utilisant le lev de CHAQUE trade
    for bp in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]:
        sens[f"r_net_moyen_a_{bp}bps"] = float((d["r_gross"] - bp * 1e-4 * lev).mean())
    be = d["r_gross"].mean() / (1e-4 * lev.mean())
    sens["RT_bps_de_point_mort"] = float(be)
    pd.Series(sens).to_csv(OUT / "s4_sensibilite.csv", header=["valeur"])

    # ---- 2. granularité de tick, en bps, sur l'histoire du ledger ----
    g = d.groupby("year").agg(px=("entry", "median"),
                              stop=("stop_dist_pts", "median"),
                              n=("entry", "size"))
    g["tick_NQ_bps"] = NQ_TICK_PTS / g["px"] * 1e4
    g["tick_CFD_bps"] = CFD_TICK_PTS / g["px"] * 1e4
    g["tick_NQ_en_pct_du_stop"] = NQ_TICK_PTS / g["stop"] * 100
    g["tick_CFD_en_pct_du_stop"] = CFD_TICK_PTS / g["stop"] * 100
    g.reset_index().to_csv(OUT / "s4_granularite_par_an.csv", index=False)

    # ---- 3. structure de coût comparée, aux niveaux de prix du ledger ----
    rows = []
    for px in [1850.0, 5000.0, 12000.0, 20000.0, 30000.0]:
        # futures : spread 1 tick + commission ; slippage traité à part
        nq_notional = NQ_USD_PER_PT * px
        mnq_notional = MNQ_USD_PER_PT * px
        rows.append({
            "prix_indice": px,
            "NQ_spread_bps": NQ_TICK_PTS / px * 1e4,
            "NQ_comm_bps": NQ_COMM_RT_USD / nq_notional * 1e4,
            "NQ_RT_bps": NQ_TICK_PTS / px * 1e4 + NQ_COMM_RT_USD / nq_notional * 1e4,
            "MNQ_spread_bps": NQ_TICK_PTS / px * 1e4,
            "MNQ_comm_bps": MNQ_COMM_RT_USD / mnq_notional * 1e4,
            "MNQ_RT_bps": NQ_TICK_PTS / px * 1e4 + MNQ_COMM_RT_USD / mnq_notional * 1e4,
            # CFD : le spread est en POINTS d'indice, invariant de taille de lot
            "CFD_spread_0p65pt_bps": 0.65 / px * 1e4,
            "CFD_spread_0p80pt_bps": 0.80 / px * 1e4,
            "CFD_spread_1p90pt_bps": 1.90 / px * 1e4,
            "CFD_comm_bps": CFD_COMM_RT_USD,
        })
    pd.DataFrame(rows).to_csv(OUT / "s4_structure_cout.csv", index=False)

    # ---- 4. base cash-future : drift de portage sur la durée de vie du trade ----
    # US100.cash = indice CASH ; NQ = FUTURE. Le future converge vers le cash au
    # rythme du portage net (r - q). Sur un trade tenu H heures, le future dérive
    # de -(r-q)*H/8760 en relatif. Effet DIRECTIONNEL, pas un coût de spread.
    basis = []
    for rq in [0.02, 0.035, 0.05]:
        for H in [2.0, 4.0, 6.0]:
            basis.append({"carry_net_annuel": rq, "heures_tenues": H,
                          "drift_future_bps": -rq * H / 8760 * 1e4,
                          "en_R_au_lev_median": -rq * H / 8760 * float(lev.median())})
    pd.DataFrame(basis).to_csv(OUT / "s4_base_cash_future.csv", index=False)

    print("=== sensibilité ledger ===")
    print(pd.Series(sens).round(5).to_string())
    print("\n=== granularité de tick, par an ===")
    print(g.round(4).to_string())
    print("\n=== structure de coût NQ / MNQ / CFD (bps RT) ===")
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    print("\n=== base cash-future ===")
    print(pd.DataFrame(basis).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
