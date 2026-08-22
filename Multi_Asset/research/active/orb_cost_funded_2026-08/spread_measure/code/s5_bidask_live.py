"""Volet C / H3 — une mesure DIRECTE du spread US100.cash sur le compte live.

`fills.csv` ne journalise pas de bid/ask (FILLS_COLUMNS, lib/statefiles.py:31).
MAIS `req_price` d'un ordre MARCHÉ vaut `SidePrice(sym, side)` = ASK pour un
achat, BID pour une vente (book_executor.mq5, SendMarket / CloseLegLots).

Donc toute paire (BUY, SELL) sur le MÊME symbole séparée de quelques secondes
donne ask(t1) - bid(t2), c'est-à-dire le spread majoré/minoré du drift de mid
entre les deux instants. C'est la seule mesure de fourchette disponible en live.

Sortie : out/s5_bidask.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "out"

MARKET_REASONS = {"rebalance", "us100_off", "ger40_off", "ger40_on", "breaker_flat",
                  "target_lock_flat", "micro_time", "backstop_open", "backstop_close",
                  "funded_orb_exit"}
MAX_GAP_S = 120


def main() -> None:
    f = pd.read_csv(OUT / "s3_fills_dedup.csv", parse_dates=["ts_paris"])
    f = f[f["reason"].isin(MARKET_REASONS)].copy()
    rows = []
    for sym, g in f.groupby("symbol"):
        g = g.sort_values("ts_paris").reset_index(drop=True)
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                dt = (g.loc[j, "ts_paris"] - g.loc[i, "ts_paris"]).total_seconds()
                if dt > MAX_GAP_S:
                    break
                a, b = g.loc[i], g.loc[j]
                if a["side"] == b["side"]:
                    continue
                ask = a["req_price"] if a["side"] == "BUY" else b["req_price"]
                bid = b["req_price"] if a["side"] == "BUY" else a["req_price"]
                px = (ask + bid) / 2.0
                rows.append({
                    "symbol": sym, "t_buy": str(a["ts_paris"] if a["side"] == "BUY"
                                                else b["ts_paris"]),
                    "dt_s": dt, "reason_1": a["reason"], "reason_2": b["reason"],
                    "ask": ask, "bid": bid, "spread_pts": ask - bid,
                    "spread_bps": (ask - bid) / px * 1e4})
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "s5_bidask.csv", index=False)
    print("=== paires (BUY, SELL) même symbole, écart <= 120 s ===")
    if len(r):
        print(r.round(4).to_string(index=False))
        print("\n=== resume (dt <= 5 s : drift de mid negligeable) ===")
        tight = r[r["dt_s"] <= 5]
        print(tight.round(4).to_string(index=False))
    else:
        print("aucune paire")

    # fenêtre pré-enregistrée : combien d'entrées ORB dans 16:00-16:30 ?
    o = pd.read_csv(OUT / "s3_orb_fills.csv", parse_dates=["ts_paris"])
    e = o[o["reason"] == "micro_entry"].copy()
    hm = e["ts_paris"].dt.hour * 60 + e["ts_paris"].dt.minute
    print("\n=== procédure pré-enregistrée : N=60 fills actifs 16:00-16:30 ===")
    print("entrées ORB TOTAL          :", len(e))
    print("entrées dans [16:00,16:30) :", int(((hm >= 960) & (hm < 990)).sum()))
    print("entrées dans [16:00,17:00) :", int(((hm >= 960) & (hm < 1020)).sum()))
    print("sorties ORB TOTAL          :",
          int((o["leg"].isin(["sortie", "sortie_gouverneur"])).sum()))
    print("jours de trading ORB       :", e["ts_paris"].dt.date.nunique())


if __name__ == "__main__":
    main()
