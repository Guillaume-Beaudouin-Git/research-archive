"""Volet C / H3 — réconciliation du 2.2 bps codé en dur vs la mesure du cache.

Sources (LECTURE SEULE) :
  data/ftmo_portfolio/cache/{US100,GER40,US500,US30}_daily_cet.parquet
  data/ftmo_portfolio/outputs/phase0_rt_cost_bps.csv
  data/ftmo_portfolio/research_panel.py  (mécanisme du défaut, l.68-73)

Sortie : out/s1_*.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
CACHE = ROOT / "data" / "ftmo_portfolio" / "cache"
OUTS = ROOT / "data" / "ftmo_portfolio" / "outputs"
OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(parents=True, exist_ok=True)

SYMS = ["US100", "GER40", "US500", "US30"]
SLIP_INDEX = 0.5           # research_panel.SLIPPAGE_BPS["index"], par côté
DEFAULT_INDEX_SPREAD = 1.2  # research_panel.py:68-73, valeur codée en dur


def main() -> None:
    rows, yr = [], []
    for s in SYMS:
        d = pd.read_parquet(CACHE / f"{s}_daily_cet.parquet")
        d = d[d["n_bars"] > 100]                       # même filtre que research_panel
        sp = d["spread_med_bps"]
        # ce que research_panel CALCULERAIT si les indices étaient chargés
        sp_750 = float(np.nanmedian(sp.tail(750)))
        rows.append({
            "symbol": s, "n_jours": len(d),
            "debut": str(d.index[0].date()), "fin": str(d.index[-1].date()),
            "frac_jours_spread_nul": float((sp == 0).mean()),
            "spread_med_full": float(sp.median()),
            "spread_med_750d": sp_750,
            "spread_med_750d_hors_zero": float(np.nanmedian(sp.tail(750)[sp.tail(750) > 0])),
            "spread_p75_med_750d": float(np.nanmedian(d["spread_p75_bps"].tail(750))),
            "RT_code_en_dur": DEFAULT_INDEX_SPREAD + 2 * SLIP_INDEX,
            "RT_si_mesure_750d": sp_750 + 2 * SLIP_INDEX,
        })
        g = d.groupby(d.index.year).agg(
            n=("spread_med_bps", "size"),
            zero_frac=("spread_med_bps", lambda x: float((x == 0).mean())),
            med=("spread_med_bps", "median"),
            p75=("spread_p75_bps", "median"))
        g.insert(0, "symbol", s)
        yr.append(g.reset_index().rename(columns={"index": "annee"}))

    rec = pd.DataFrame(rows)
    rec.to_csv(OUT / "s1_reconciliation.csv", index=False)
    pd.concat(yr).to_csv(OUT / "s1_spread_par_an.csv", index=False)

    rt = pd.read_csv(OUTS / "phase0_rt_cost_bps.csv", index_col=0)
    rt.columns = ["RT_bps"]
    rt.to_csv(OUT / "s1_phase0_rt_publie.csv")

    print("=== réconciliation ===")
    print(rec.round(4).to_string(index=False))
    print("\n=== phase0_rt_cost_bps.csv publié (extrait indices) ===")
    print(rt.loc[[i for i in rt.index if i in SYMS]].round(3).to_string())
    print("\n=== signature du défaut : combien de symboles portent EXACTEMENT 2.2 ? ===")
    eq = rt[np.isclose(rt["RT_bps"], 2.2)]
    print(eq.to_string(), "  -> n =", len(eq))
    print("\n=== spread par an (US100) ===")
    print(pd.concat(yr).query("symbol=='US100'").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
