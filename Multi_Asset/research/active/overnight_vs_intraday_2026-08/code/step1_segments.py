"""Etape 1 — decomposition TENU / ESQUIVE / 24H aux heures EXACTES du sleeve v2.2.

Semantique reprise de cleanroom/engine.py:393-405 (le moteur qui pilote le live) :
  jour D avec ON[D]=1 (D in {lundi, mardi}) :
     s=3  17:35 CET  -> GER40 ON
     s=4  22:05 CET  -> US100 ON
  jour suivant E = D+1 :
     s=1  09:00 CET  -> GER40 OFF
     s=2  15:30 CET  -> US100 OFF

Decomposition additive exacte en log :
  TENU    = log(P[exit,E]  / P[entry,D])     le segment que la sleeve DETIENT
  ESQUIVE = log(P[entry,E] / P[exit,E])      la seance cash qu'elle EVITE
  24H     = log(P[entry,E] / P[entry,D]) = TENU + ESQUIVE

Sortie : un CSV par instrument avec, par jour d'entree D, les trois rendements bruts
et les composantes de cout.
"""
from __future__ import annotations
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_m1, stamps, px_at, SEG, RT_BPS, SWAP_LONG_BPS, TZ  # noqa

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
TRIPLE_DOW = 4          # spec_v22 measured_specs: triple_dow=4 (vendredi) pour US100 et GER40


def build(sym: str) -> pd.DataFrame:
    df = load_m1(sym)
    close = df["close"]
    ent_h, ent_m = SEG[sym]["entry"]
    ex_h, ex_m = SEG[sym]["exit"]

    days = pd.DatetimeIndex(sorted(set(close.index.normalize().tz_localize(None))))
    days = days[days.dayofweek < 5]

    p_ent = px_at(close, stamps(days, ent_h, ent_m))
    p_ex = px_at(close, stamps(days, ex_h, ex_m))
    p_ent.index, p_ex.index = days, days

    # E = jour ouvre suivant present dans l'index (saute les jours feries sans donnee)
    nxt = pd.Series(days[1:], index=days[:-1]).reindex(days)
    # garde-fou : l'ecart D->E ne doit pas depasser 4 jours calendaires (sinon trou)
    gap = (nxt - pd.Series(days, index=days)).dt.days
    ok = gap.between(1, 4)

    out = pd.DataFrame({"D": days})
    out["E"] = nxt.values
    out["dow_D"] = out["D"].dt.dayofweek
    out["p_ent_D"] = p_ent.values
    out["p_ex_E"] = p_ex.reindex(nxt.values).values
    out["p_ent_E"] = p_ent.reindex(nxt.values).values
    out = out[ok.values].copy()

    out["tenu"] = np.log(out["p_ex_E"] / out["p_ent_D"]) * 1e4
    out["esquive"] = np.log(out["p_ent_E"] / out["p_ex_E"]) * 1e4
    out["h24"] = np.log(out["p_ent_E"] / out["p_ent_D"]) * 1e4
    out["sym"] = sym

    # --- couts -----------------------------------------------------------------
    # rollover FTMO = 00:00 serveur (EET) = 23:00 CET. Les trois segments :
    #   TENU    (entry D -> exit E)  franchit le rollover de la nuit de D  -> 1 nuit
    #   ESQUIVE (exit E -> entry E)  intra-journee                          -> 0 nuit
    #   24H     (entry D -> entry E) franchit le meme unique rollover       -> 1 nuit
    # multiplicateur triple : la nuit de D compte x3 si D est le triple_dow.
    mult = np.where(out["dow_D"].values == TRIPLE_DOW, 3.0, 1.0)
    out["swap_nights_tenu"] = mult
    out["swap_nights_esquive"] = 0.0
    out["swap_nights_h24"] = mult
    out["swap_bps_tenu"] = mult * SWAP_LONG_BPS[sym]
    out["swap_bps_esquive"] = 0.0
    out["swap_bps_h24"] = mult * SWAP_LONG_BPS[sym]
    out["rt_bps"] = RT_BPS[sym]

    # --- desalignement DST CET vs ET (L56) : combien d'heures separe Paris de NY ?
    ny = pd.DatetimeIndex(
        [pd.Timestamp(d.year, d.month, d.day, 12, 0, tz=TZ) for d in out["D"]]
    )
    off_par = np.array([t.utcoffset().total_seconds() / 3600 for t in ny])
    off_ny = np.array([t.tz_convert("America/New_York").utcoffset().total_seconds() / 3600
                       for t in ny])
    out["cet_minus_et"] = off_par - off_ny        # 6 en regime normal
    out["dst_mismatch"] = out["cet_minus_et"] != 6.0

    return out.dropna(subset=["tenu", "esquive", "h24"]).reset_index(drop=True)


def main():
    frames = []
    for sym in ("US100", "GER40"):
        d = build(sym)
        frames.append(d)
        print(f"[{sym}] N={len(d)}  {d['D'].min().date()} -> {d['D'].max().date()}"
              f"  | jours desalignes DST: {d['dst_mismatch'].mean():.2%}")
        print("   check additivite max|tenu+esquive-h24| =",
              float((d["tenu"] + d["esquive"] - d["h24"]).abs().max()))
    all_ = pd.concat(frames)
    all_.to_csv(os.path.join(OUT, "step1_segments.csv"), index=False)
    print("\necrit ->", os.path.join(OUT, "step1_segments.csv"))


if __name__ == "__main__":
    main()
