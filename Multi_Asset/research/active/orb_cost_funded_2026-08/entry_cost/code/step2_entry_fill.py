"""Volet A / étape 2 — coût réel de l'ENTRÉE stop de l'ORB, mesuré sur M1 Databento.

Fenêtre OR validée à l'étape 1 : 09:30-10:00 America/New_York (horloge d'échange, DST natif).
Corroborée par le code LIVE (`ftmo_live/mt5/book_executor.mq5:1027-1035`) : OR = bornes des
barres M5 15:30->16:00 **heure serveur Paris**, soit 09:30-10:00 New York.

Le LIVE place des ordres STOP AU REPOS (`ORDER_TYPE_BUY_STOP` @ or_hi / `SELL_STOP` @ or_lo,
`req.price = level` sans offset, book_executor.mq5:628-648, 1051-1071). Le modèle de fill
physiquement correct est donc « stop devenu ordre au marché au touch », = régime (b).

Régimes de remplissage mesurés :
  (a)  fill = level                                   (hypothèse du ledger)
  (b)  fill = max(open_M1, level) [long]              stop-market, pas de traversée
  (b1) fill = (b) + 1 tick                            plancher de traversée non nulle
  (c25/c50) fill = (b) + lam*(extremum_M1 - (b))      traversée intra-barre, lam=0.25/0.50
  (c2) fill = open de la barre M1 SUIVANTE            delay+1 M1 (borne haute de latence)
  (m5) fill = open de la barre M5 de déclenchement    ce qu'un système bar-driven paierait

Ancrage du déclenchement : la barre M5 de déclenchement est prise DIRECTEMENT du ledger
(`ttb_5min`), ce qui garantit l'alignement exact avec les trades re-pricés. La barre M1 de
déclenchement est la première barre de cette fenêtre M5 qui franchit `level`.

Devise commune (prereg §2) : points, bps de prix, R.
Sizing pré-calculé au niveau déclencheur (le lot est calculé à 16:00 Paris, avant le fill)
=> cost_R = cost_points / |level - stop_eff|, cohérent avec le haircut du ledger.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
LEDGER = REPO / "PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet"
M1 = REPO / "data/raw/NQ_1min_databento_2010-2026.parquet"
BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "out"
OUT.mkdir(parents=True, exist_ok=True)

TICK = 0.25
OR_START_MIN = 9 * 60 + 30
OR_END_MIN = 10 * 60
SESSION_END_MIN = 16 * 60


def load_m1() -> pd.DataFrame:
    df = pd.read_parquet(M1, columns=["open", "high", "low", "close", "volume"])
    et = df.index.tz_convert("America/New_York")
    df["et_date"] = et.normalize().tz_localize(None)
    df["et_min"] = et.hour * 60 + et.minute
    return df


def main() -> None:
    led = pd.read_parquet(LEDGER)
    m1 = load_m1()

    # ---------- contrôle 1 : reproduction de l'OR sur les 4013 dates -------------
    orw = m1[(m1["et_min"] >= OR_START_MIN) & (m1["et_min"] < OR_END_MIN)]
    org = orw.groupby("et_date").agg(hi=("high", "max"), lo=("low", "min"),
                                     nbar=("high", "size"))
    chk = led[["or_hi", "or_lo"]].join(org, how="left")
    chk["exact"] = (np.abs(chk["hi"] - chk["or_hi"]) < TICK / 2) & (
        np.abs(chk["lo"] - chk["or_lo"]) < TICK / 2)
    chk.to_csv(OUT / "step2_or_reproduction_full.csv")
    print(f"[OR] reproduction exacte au tick : {int(chk['exact'].sum())}/{len(chk)} "
          f"({chk['exact'].mean():.4%}) | barres M1/OR médiane {org['nbar'].median():.0f}")

    # ---------- fenêtre post-OR (prev/next calculés sur la session ENTIÈRE) ------
    sess = m1[(m1["et_min"] >= OR_START_MIN) & (m1["et_min"] < SESSION_END_MIN)].copy()
    sess = sess[sess["et_date"].isin(led.index)].sort_index()
    sess = sess.reset_index().rename(columns={"timestamp_utc": "ts"})
    sess["next_open"] = sess.groupby("et_date")["open"].shift(-1)
    sess["prev_close"] = sess.groupby("et_date")["close"].shift(1)
    sess["prev_high"] = sess.groupby("et_date")["high"].shift(1)
    sess["prev_low"] = sess.groupby("et_date")["low"].shift(1)
    sess["prev_ts"] = sess.groupby("et_date")["ts"].shift(1)
    post = sess[sess["et_min"] >= OR_END_MIN].copy()
    post["k5"] = (post["et_min"] - OR_END_MIN) // 5

    lv_map = led["level"]
    dr_map = led["direction"]
    lv = lv_map.reindex(post["et_date"].values).values
    dr = dr_map.reindex(post["et_date"].values).values
    post["touch"] = np.where(dr > 0, post["high"].values >= lv - 1e-9,
                             post["low"].values <= lv + 1e-9)
    post["brk"] = np.where(dr > 0, post["high"].values > lv + 1e-9,
                           post["low"].values < lv - 1e-9)

    # ---------- A) déclenchement ANCRÉ sur le ledger (ttb_5min) ------------------
    key = pd.MultiIndex.from_arrays([post["et_date"], post["k5"]])
    want = pd.MultiIndex.from_arrays([led.index, led["ttb_5min"].values])
    sel = post[key.isin(want) & post["touch"].values].copy()
    trig = sel.groupby("et_date").head(1).set_index("et_date")
    # 2 jours de halt COVID (2020-03-09/12) : la barre M5 ttb_5min du ledger ne contient
    # aucun touch M1 (interruption de cotation). Repli documenté sur la 1re barre M1 qui
    # franchit le niveau au sens strict.
    fallback = post[post["brk"].values].groupby("et_date").head(1).set_index("et_date")
    miss = led.index.difference(trig.index)
    if len(miss):
        trig = pd.concat([trig, fallback.reindex(miss)]).sort_index()
        print(f"[TRIG] repli halt sur {len(miss)} jour(s) : {list(miss.date)}")

    # ---------- B) déclenchement LIVE-fidèle (stop au repos, 1er touch post-10:00)
    live_first = post[post["touch"].values].groupby("et_date").head(1).set_index("et_date")
    # ---------- C) déclenchement « break strict » (convention du ledger, M1) -----
    brk_first = post[post["brk"].values].groupby("et_date").head(1).set_index("et_date")

    df = led.join(
        trig[["ts", "open", "high", "low", "close", "volume", "k5",
              "next_open", "prev_close", "prev_high", "prev_low",
              "prev_ts"]].add_prefix("t_"))
    df = df.join(live_first[["ts", "k5", "open"]].add_prefix("live_"))
    df = df.join(brk_first[["ts", "k5"]].add_prefix("brk_"))

    n_ok = int(df["t_open"].notna().sum())
    print(f"[TRIG] barre M1 dans la barre M5 ttb_5min du ledger : {n_ok}/{len(df)}")
    print(f"[TRIG] break strict M1 tombe dans la barre ttb_5min : "
          f"{(df['brk_k5'] == df['ttb_5min']).mean():.4%}")
    print(f"[TRIG] stop AU REPOS aurait déclenché plus tôt (touch < ttb_5min) : "
          f"{(df['live_k5'] < df['ttb_5min']).mean():.4%} des jours")

    # ---------- ouverture de la barre M5 de déclenchement ------------------------
    m5g = post.groupby(["et_date", "k5"])
    m5 = pd.DataFrame({"o": m5g["open"].first(), "c": m5g["close"].last()})
    idx = pd.MultiIndex.from_arrays([df.index, df["ttb_5min"].values])
    df["m5_open"] = m5["o"].reindex(idx).values
    df["m5_close"] = m5["c"].reindex(idx).values

    d = df["direction"].astype(float)
    lvl = df["level"].astype(float)
    risk = (df["level"] - df["stop_eff"]).abs().astype(float)
    df["risk_pts"] = risk
    df["lev"] = df["entry"] / (df["entry"] - df["stop_eff"]).abs()

    # ---------- gap d'entrée : la barre déclenche-t-elle DÉJÀ au-delà ? ----------
    df["open_beyond_pts"] = (df["t_open"] - lvl) * d
    df["is_gap"] = df["open_beyond_pts"] > 1e-9
    df["m5_open_beyond_pts"] = (df["m5_open"] - lvl) * d
    df["m5_is_gap"] = df["m5_open_beyond_pts"] > 1e-9
    df["prev_gap_min"] = (df["t_ts"] - df["t_prev_ts"]).dt.total_seconds() / 60.0
    df["jump_pts"] = (df["t_open"] - df["t_prev_close"]) * d
    df["bar_range_pts"] = df["t_high"] - df["t_low"]
    df["excursion_beyond_pts"] = (np.where(d > 0, df["t_high"], df["t_low"]) - lvl) * d

    # ---------- les régimes de fill ---------------------------------------------
    fb = np.where(d > 0, np.maximum(df["t_open"], lvl), np.minimum(df["t_open"], lvl))
    extr = np.where(d > 0, df["t_high"], df["t_low"])
    fills = {
        "a_ideal": lvl.values,
        "b_stop_market": fb,
        "b1_plus1tick": fb + d.values * TICK,
        "c25_trav": fb + 0.25 * (extr - fb),
        "c50_trav": fb + 0.50 * (extr - fb),
        "c2_delay1_M1": np.where(d > 0, np.maximum(df["t_next_open"], fb),
                                 np.minimum(df["t_next_open"], fb)),
        # diagnostic de contraste : ce que paierait un système NON stop-au-repos qui
        # détecterait la cassure à la clôture de la barre M5 et enverrait un ordre marché.
        "m5close_bardriven": np.where(d > 0, np.maximum(df["m5_close"], lvl),
                                      np.minimum(df["m5_close"], lvl)),
    }
    for name, f in fills.items():
        cost_pts = (f - lvl.values) * d.values
        df[f"fill_{name}"] = f
        df[f"cost_pts_{name}"] = cost_pts
        df[f"cost_bps_{name}"] = cost_pts / lvl.values * 1e4
        df[f"cost_R_{name}"] = cost_pts / risk.values
        df[f"R_{name}"] = df["r_gross"].values - cost_pts / risk.values
        newrisk = np.abs(f - df["stop_eff"].values)
        df[f"Radapt_{name}"] = (df["exit_px"].values - f) * d.values / newrisk

    df.to_parquet(OUT / "step2_trades_enriched.parquet")

    print("\n[GAP] barre M1 de déclenchement ouvrant au-delà du niveau : "
          f"{df['is_gap'].mean():.4%}  (N={len(df)})")
    print("[GAP] barre M5 de déclenchement ouvrant au-delà du niveau : "
          f"{df['m5_is_gap'].mean():.4%}")
    for k in fills:
        print(f"  {k:14s} cost_pts moy {df[f'cost_pts_{k}'].mean():8.4f} | "
              f"bps {df[f'cost_bps_{k}'].mean():7.4f} | "
              f"R {df[f'cost_R_{k}'].mean():8.5f} | "
              f"mean R_net {df[f'R_{k}'].mean():+.5f}")


if __name__ == "__main__":
    main()
