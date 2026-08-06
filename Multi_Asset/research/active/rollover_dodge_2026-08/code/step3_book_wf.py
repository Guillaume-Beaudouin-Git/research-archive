"""Etape 3 — BOOK au schedule REEL (chaque jambe a son heure live), walk-forward,
sensibilite au swap, et verification de la verite terrain du swap facture.

BOOK_LIVE  = 0.6 x US100(entree 22:05) + 0.6 x GER40(entree 17:35), 1 nuit de swap/jambe
BOOK_DODGE = 0.6 x US100(entree 00:05) + 0.6 x GER40(entree 00:05), 0 nuit de swap
Sorties identiques dans les deux cas (15:30 / 09:00) -> geometrie de sortie constante (L59).
"""
from __future__ import annotations
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from common import (hac_t, block_bootstrap_mean, sharpe_ann, ERA_CUT, RT_BPS,
                    SWAP_LONG_BPS, SWAP_LIVE_BPS)  # noqa
from step2_variants import leg_table, LIVE, DODGE, W  # noqa
try:
    from dsr import deflated_sharpe_ratio, sampling_noise_floor_sr
    HAVE_DSR = True
except Exception as e:                                            # pragma: no cover
    print("[dsr] indisponible:", e); HAVE_DSR = False

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
N_TRIALS = 8   # essais de ce diagnostic : 8 heures d'entree balayees (step2)


def build_book():
    legs = {s: leg_table(s).set_index("D") for s in ("US100", "GER40")}
    idx = legs["US100"].index.intersection(legs["GER40"].index)
    need = {"US100": [f"g_{LIVE['US100']}", f"g_{DODGE}"],
            "GER40": [f"g_{LIVE['GER40']}", f"g_{DODGE}"]}
    m = pd.Series(True, index=idx)
    for lg, cs in need.items():
        m &= legs[lg].loc[idx, cs].notna().all(axis=1)
    idx = idx[m.values]
    out = pd.DataFrame(index=idx)
    for lg in ("US100", "GER40"):
        out[f"{lg}_live_g"] = legs[lg].loc[idx, f"g_{LIVE[lg]}"].values
        out[f"{lg}_dodge_g"] = legs[lg].loc[idx, f"g_{DODGE}"].values
    return out


def nets(bk, swap_tbl):
    live = W * sum(bk[f"{lg}_live_g"] + swap_tbl[lg] - RT_BPS[lg] for lg in ("US100", "GER40"))
    dodge = W * sum(bk[f"{lg}_dodge_g"] + 0.0 - RT_BPS[lg] for lg in ("US100", "GER40"))
    return live.values, dodge.values


def main():
    bk = build_book()
    era = np.where(bk.index < ERA_CUT, "pre-2021", "post-2021")
    years = (bk.index.max() - bk.index.min()).days / 365.25
    opy = len(bk) / years
    print(f"BOOK apparie : N={len(bk)}  {bk.index.min().date()} -> {bk.index.max().date()}"
          f"   ({(era=='post-2021').sum()} post-2021)  -> {opy:.0f} evenements/an")

    rows = []
    for swap_name, tbl in (("ancre_spec", SWAP_LONG_BPS), ("live_mesure", SWAP_LIVE_BPS),
                           ("live_+17pct", {k: v * 1.17 for k, v in SWAP_LIVE_BPS.items()}),
                           ("swap_ZERO_hypothetique", {k: 0.0 for k in SWAP_LIVE_BPS})):
        lv, dg = nets(bk, tbl)
        for e in ("post-2021", "TOTAL"):
            m = np.ones(len(bk), bool) if e == "TOTAL" else (era == "post-2021")
            for lab, x in (("BOOK_LIVE", lv[m]), ("BOOK_DODGE", dg[m]),
                           ("DELTA(dodge-live)", (dg - lv)[m])):
                mm, tt, N = hac_t(x)
                lo90, hi90, lo95, hi95 = block_bootstrap_mean(x, block=10)
                d = {"swap_hyp": swap_name, "era": e, "serie": lab, "N": N,
                     "mean_bps": mm, "t_hac6": tt, "sharpe_ann": sharpe_ann(x / 1e4, opy),
                     "boot_lo90": lo90, "boot_hi90": hi90, "boot_lo95": lo95, "boot_hi95": hi95}
                if HAVE_DSR and lab != "DELTA(dodge-live)":
                    try:
                        fl = sampling_noise_floor_sr(len(x), periods_per_year=int(round(opy)))
                        r = deflated_sharpe_ratio(x / 1e4, n_trials=N_TRIALS,
                                                  periods_per_year=int(round(opy)),
                                                  std_sr_trials=fl, rf=0.0)
                        d["dsr"] = float(r["dsr"]) if isinstance(r, dict) else float(r)
                    except Exception as ex:
                        d["dsr"] = np.nan; print("  [dsr]", ex)
                rows.append(d)
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(OUT, "step3_book_paired.csv"), index=False)

    # ---------------- walk-forward sur le DELTA APPARIE (6 folds egaux) ----------
    lv, dg = nets(bk, SWAP_LONG_BPS)
    delta = dg - lv
    wf = []
    for nf in (5, 6):
        cuts = np.array_split(np.arange(len(bk)), nf)
        for i, c in enumerate(cuts, 1):
            mm, tt, N = hac_t(delta[c])
            wf.append({"n_folds": nf, "fold": i,
                       "start": str(bk.index[c[0]].date()), "end": str(bk.index[c[-1]].date()),
                       "delta_mean_bps": mm, "t_hac6": tt, "N": N,
                       "live_mean": float(np.mean(lv[c])), "dodge_mean": float(np.mean(dg[c]))})
    wfd = pd.DataFrame(wf)
    wfd.to_csv(os.path.join(OUT, "step3_walkforward_delta.csv"), index=False)

    # ---------------- verite terrain : swap facture live -------------------------
    sw = pd.read_csv("<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/"
                     "swaps_billed_live.csv", parse_dates=["date_paris"])
    sw["dow"] = sw["date_paris"].dt.day_name()
    sw["bps"] = 1e4 * sw["swap_usd"] / sw["notional_usd"]
    sw["ancre_bps"] = sw["symbol"].str.replace(".cash", "", regex=False).map(SWAP_LONG_BPS)
    sw["ecart_pct"] = 100 * (sw["bps"] / sw["ancre_bps"] - 1)
    sw.to_csv(os.path.join(OUT, "step3_swap_groundtruth.csv"), index=False)

    pd.set_option("display.width", 200)
    print("\n=== BOOK au schedule REEL — apparie ===")
    for e in ("post-2021", "TOTAL"):
        for swap_name in ("ancre_spec", "live_mesure", "live_+17pct", "swap_ZERO_hypothetique"):
            s = res[(res.era == e) & (res.swap_hyp == swap_name)]
            print(f"\n-- {e} / swap {swap_name} --")
            print(s[["serie", "N", "mean_bps", "t_hac6", "sharpe_ann", "boot_lo90",
                     "boot_hi90"] + (["dsr"] if "dsr" in s else [])]
                  .to_string(index=False, float_format=lambda x: f"{x:8.3f}"))

    print("\n=== Walk-forward du DELTA apparie (dodge - live), swap = ancre ===")
    print(wfd.to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
    for nf in (5, 6):
        s = wfd[wfd.n_folds == nf]
        print(f"  folds ou le dodge AMELIORE : {int((s.delta_mean_bps>0).sum())}/{nf}")

    print("\n=== Verite terrain : swap FACTURE sur le compte (nuits ON) ===")
    print(sw[["date_paris", "dow", "symbol", "notional_usd", "swap_usd", "bps",
              "ancre_bps", "ecart_pct"]].to_string(index=False,
                                                   float_format=lambda x: f"{x:9.3f}"))


if __name__ == "__main__":
    main()
