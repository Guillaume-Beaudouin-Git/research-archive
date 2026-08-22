"""Volet C / H3 — coût d'exécution MESURÉ sur les fills LIVE du compte FTMO.

Source : out/vps_dump.txt (copie lecture-seule des 3 fills.csv du VPS,
récupérée en une seule session SSH).

Sémantique établie en lisant `ftmo_live/mt5/book_executor.mq5` — c'est ce qui
rend les chiffres interprétables :

  * `micro_entry` : ordre PENDING STOP natif posé à 16:00 Paris sur `g_or_hi` /
    `g_or_lo` (PlaceStopOrder, l.1051-1054). Donc `req_price` = LE NIVEAU ORB,
    et `slip_bps = (fill/level - 1)*side*1e4` mesure exactement le
    NIVEAU -> FILL, c'est-à-dire le franchissement (gap-through + latence).
    Le spread N'Y EST PAS : un BUY STOP se déclenche sur l'Ask et se remplit à
    l'Ask ; un SELL STOP sur le Bid et se remplit au Bid.

  * `micro_stop` : sortie SERVEUR sur SL (DEAL_REASON_SL, l.882).
    `fake.req_px = g_or_hi / g_or_lo` = le niveau de stop (l.889).
    Donc slip = STOP -> FILL : c'est la quantité de L59. Valide.

  * `micro_time` / `target_lock_flat` / `us100_off` ... : ordre MARCHÉ
    (SendMarket / CloseLegLots) avec `req.price = SidePrice(sym, side)`
    = ASK pour un achat, BID pour une vente. Le spread est DÉJÀ payé dans
    `req_price` : le slip mesure le dérapage AU-DELÀ du bid/ask.

  * PIÈGE : `DetectServerExits` re-log le MÊME deal de clôture avec un
    `req_px` FAKE (le niveau de stop courant). D'où des lignes jumelles
    (même position_id, même fill_price, même timestamp) portant des slip
    absurdes (-91, -106 bps) : ce sont des lignes de COMPTABILITÉ, pas de
    dérapage. Règle de dédup : à (ts, position_id, fill_price) identiques, on
    garde la ligne de |req - fill| minimal.

Sorties : out/s3_*.csv
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "out"
DUMP = OUT / "vps_dump.txt"

ORB_REASONS = {"micro_entry", "micro_stop", "micro_be", "micro_time"}
ENTRY_REASONS = {"micro_entry"}
EXIT_REASONS = {"micro_stop", "micro_be", "micro_time"}


def parse_dump() -> pd.DataFrame:
    txt = DUMP.read_text()
    blocks, cur, name = {}, [], None
    for ln in txt.splitlines():
        if ln.startswith("###"):
            if name and cur:
                blocks[name] = "\n".join(cur)
            name, cur = ln.strip("#"), []
        elif name:
            cur.append(ln)
    if name and cur:
        blocks[name] = "\n".join(cur)
    frames = []
    for k in ("CUR", "BREACH", "TRIAL"):
        b = blocks.get(k, "")
        if "ts_server" not in b:
            continue
        d = pd.read_csv(io.StringIO(b))
        d["src"] = k
        frames.append(d)
    f = pd.concat(frames, ignore_index=True)
    f["ts_paris"] = pd.to_datetime(f["ts_paris"], format="%Y.%m.%d %H:%M:%S")
    # 1) dédup inter-fichiers (TRIAL est un sous-ensemble de BREACH)
    key = ["ts_paris", "reason", "symbol", "side", "lots", "req_price", "fill_price"]
    f = f.sort_values("src").drop_duplicates(subset=key, keep="first")
    return f.sort_values("ts_paris").reset_index(drop=True)


def dedupe_accounting(f: pd.DataFrame) -> pd.DataFrame:
    """Retire les lignes de re-log à req_px FAKE de DetectServerExits."""
    f = f.copy()
    f["absdiff"] = (f["req_price"] - f["fill_price"]).abs()
    grp = ["ts_paris", "symbol", "fill_price", "position_id"]
    f["_rk"] = f.groupby(grp)["absdiff"].rank(method="first")
    f["_n"] = f.groupby(grp)["absdiff"].transform("size")
    dropped = f[(f["_n"] > 1) & (f["_rk"] > 1)]
    kept = f[~((f["_n"] > 1) & (f["_rk"] > 1))]
    return kept.drop(columns=["_rk", "_n"]), dropped.drop(columns=["_rk", "_n"])


def stats(x: pd.Series) -> dict:
    x = x.astype(float).dropna()
    if len(x) == 0:
        return {}
    return {
        "N": int(len(x)), "moy": float(x.mean()), "med": float(x.median()),
        "sd": float(x.std(ddof=1)) if len(x) > 1 else np.nan,
        "se": float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else np.nan,
        "min": float(x.min()), "p25": float(np.percentile(x, 25)),
        "p75": float(np.percentile(x, 75)), "max": float(x.max()),
        "frac_pos": float((x > 0).mean()), "frac_zero": float((x == 0).mean()),
    }


def boot_ci(x: pd.Series, n: int = 20000, seed: int = 42) -> tuple:
    x = x.astype(float).dropna().values
    if len(x) < 3:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    m = rng.choice(x, size=(n, len(x)), replace=True).mean(axis=1)
    return (float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)))


def main() -> None:
    raw = parse_dump()
    kept, dropped = dedupe_accounting(raw)
    kept.to_csv(OUT / "s3_fills_dedup.csv", index=False)
    dropped.to_csv(OUT / "s3_fills_lignes_comptables_rejetees.csv", index=False)

    orb = kept[kept["reason"].isin(ORB_REASONS) & (kept["symbol"] == "US100.cash")].copy()
    # les clôtures du gouverneur sur le magic micro (220510) sont aussi des sorties ORB
    gov = kept[(kept["magic"] == 220510) & (~kept["reason"].isin(ORB_REASONS))
               & (kept["symbol"] == "US100.cash")].copy()
    gov["leg"] = "sortie_gouverneur"
    orb["leg"] = np.where(orb["reason"].isin(ENTRY_REASONS), "entree", "sortie")
    allorb = pd.concat([orb, gov], ignore_index=True).sort_values("ts_paris")
    allorb["heure_paris"] = allorb["ts_paris"].dt.strftime("%H:%M")
    allorb["pts"] = (allorb["fill_price"] - allorb["req_price"]) * np.where(
        allorb["side"] == "BUY", 1.0, -1.0)
    allorb.to_csv(OUT / "s3_orb_fills.csv", index=False)

    rows = []
    groups = {
        "ENTREE  micro_entry (stop natif, niveau->fill)":
            allorb[allorb["reason"] == "micro_entry"],
        "SORTIE  micro_stop (SL serveur, stop->fill) [L59]":
            allorb[allorb["reason"] == "micro_stop"],
        "SORTIE  micro_time (ordre marche 22:00, au-dela du bid/ask)":
            allorb[allorb["reason"] == "micro_time"],
        "SORTIE  gouverneur (ordre marche, au-dela du bid/ask)":
            allorb[allorb["leg"] == "sortie_gouverneur"],
        "SORTIE  toutes":
            allorb[allorb["leg"].isin(["sortie", "sortie_gouverneur"])],
    }
    for k, g in groups.items():
        st = stats(g["slip_bps"])
        if not st:
            continue
        lo, hi = boot_ci(g["slip_bps"])
        st.update({"groupe": k, "ci95_lo": lo, "ci95_hi": hi,
                   "med_pts": float(g["pts"].median())})
        rows.append(st)
    res = pd.DataFrame(rows).set_index("groupe")
    res.to_csv(OUT / "s3_orb_slip_par_jambe.csv")

    # contexte : le reste du livre (ordres marché, hors ORB), par symbole
    mk = kept[~kept["reason"].isin(ORB_REASONS)].copy()
    ctx = mk.groupby("symbol")["slip_bps"].agg(
        N="size", moy="mean", med="median",
        p95=lambda x: float(np.percentile(x, 95)), max="max").reset_index()
    ctx.to_csv(OUT / "s3_contexte_marche.csv", index=False)

    print("=== fills bruts (3 fichiers, dédup inter-fichiers) :", len(raw))
    print("=== lignes comptables rejetées :", len(dropped))
    print(dropped[["ts_paris", "reason", "side", "req_price", "fill_price",
                   "slip_bps"]].to_string(index=False))
    print("\n=== fills ORB US100.cash retenus :", len(allorb))
    print(allorb[["ts_paris", "heure_paris", "reason", "leg", "side",
                  "req_price", "fill_price", "pts", "slip_bps"]].to_string(index=False))
    print("\n=== slip par jambe (bps, positif = adverse) ===")
    print(res.round(3).to_string())
    print("\n=== contexte ordres marché hors ORB ===")
    print(ctx.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
