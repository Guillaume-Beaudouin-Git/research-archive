"""Volet C / H3 — profil intra-journalier du spread US100 (contrôle GER40).

Lit `data/deep_history_utc/<SYM>_M1.csv` en LECTURE SEULE.

Trois précautions imposées par le cadrage :
  1. La colonne `spread` de deep_history_utc est interdite comme MESURE DE NIVEAU.
     On l'utilise ici pour deux choses seulement :
       (a) la FORME intra-journalière (ratio heure / médiane journalière) ;
       (b) la part de barres à spread nul (contrôle de qualité, L60).
     Le NIVEAU est ancré ailleurs (fills live + segment natif MT5/FTMO-Demo).
  2. Le manifest déclare `backfill_before_rows` : la partie ancienne est
     RECONSTRUITE depuis Dukascopy avec un spread MODÉLISÉ
     (`spread_model=multiplicative`, `index_spread_tick_round=10`).
     Elle est identifiée et exclue de toute statistique de spread.
  3. Vérification de fuseau AVANT découpe horaire (L52/L56) : corrélation du
     profil d'activité hiver-vs-été dans l'horloge UTC et dans l'horloge Paris.

Sorties : out/s2_*.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
M1 = ROOT / "data" / "deep_history_utc"
OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(parents=True, exist_ok=True)

DIGITS = {"US100": 2, "GER40": 2, "US500": 2, "US30": 2}


def load(sym: str) -> pd.DataFrame:
    f = M1 / f"{sym}_M1.csv"
    df = pd.read_csv(
        f,
        usecols=["timestamp_utc", "close", "spread", "tick_volume"],
        dtype={"close": "float64", "spread": "int32", "tick_volume": "int64"},
    )
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    df = df.drop(columns=["timestamp_utc"])
    df.index = ts
    point = 10.0 ** (-DIGITS[sym])
    df["sp_bps"] = df["spread"].astype("float64") * point / df["close"] * 1e4
    df["sp_pts"] = df["spread"].astype("float64") * point
    return df.sort_index()


def native_cutover(df: pd.DataFrame) -> pd.Timestamp:
    """Date de bascule Dukascopy(backfill) -> MT5/FTMO-Demo(natif).

    Discriminant du MANIFEST : les segments Dukascopy sont filtrés-session
    (~390-900 barres/jour) vs MT5 24h (~1300-1400). On prend le premier mois
    dont la MEDIANE de barres/jour ouvre >= 1200.
    """
    bpd = df.groupby(df.index.date).size()
    bpd.index = pd.to_datetime(bpd.index)
    med = bpd.resample("MS").median()
    ok = med[med >= 1200]
    t = ok.index[0] if len(ok) else df.index[0].tz_localize(None)
    return pd.Timestamp(t).tz_localize("UTC")


def monthly_diag(df: pd.DataFrame, sym: str) -> pd.DataFrame:
    """Diagnostic de régime de source : barres/jour et spread, par mois."""
    bpd = df.groupby(df.index.date).size()
    bpd.index = pd.to_datetime(bpd.index)
    m = pd.DataFrame({"bars_par_jour": bpd.resample("MS").median()})
    nz = df[df["spread"] > 0]
    m["sp_med_bps"] = nz["sp_bps"].resample("MS").median().tz_localize(None)
    m["sp_med_pts"] = nz["sp_pts"].resample("MS").median().tz_localize(None)
    m["zero_frac"] = (df["spread"] == 0).resample("MS").mean().tz_localize(None)
    m.insert(0, "symbol", sym)
    return m.reset_index().rename(columns={"index": "mois"})


def tz_falsification(df: pd.DataFrame, sym: str) -> pd.DataFrame:
    """L56 : le profil d'activité est-il ancré à UTC ou à l'horloge d'échange ?

    On corrèle le profil horaire (tick_volume médian) hiver vs été dans les deux
    horloges. L'horloge correcte est celle où la corrélation est HAUTE.
    """
    d = df[df["tick_volume"] > 0].copy()
    d["h_utc"] = d.index.hour
    par = d.index.tz_convert("Europe/Paris")
    d["h_par"] = par.hour
    d["is_dst"] = par.map(lambda t: t.dst().total_seconds() > 0)
    rows = []
    for lbl, col in (("UTC", "h_utc"), ("Paris", "h_par")):
        w = d[~d["is_dst"]].groupby(col)["tick_volume"].median()
        s = d[d["is_dst"]].groupby(col)["tick_volume"].median()
        j = pd.concat([w.rename("hiver"), s.rename("ete")], axis=1).dropna()
        rows.append({"symbol": sym, "horloge": lbl, "n_heures": len(j),
                     "corr_hiver_ete": float(np.corrcoef(j["hiver"], j["ete"])[0, 1])})
    return pd.DataFrame(rows)


def profile(df: pd.DataFrame, sym: str, t0: pd.Timestamp) -> tuple:
    d = df.loc[df.index >= t0].copy()
    d = d[d["tick_volume"] > 0]                       # barres réellement cotées
    par = d.index.tz_convert("Europe/Paris")
    d["hm"] = par.hour * 60 + par.minute
    d["h"] = par.hour
    d["year"] = par.year
    d["dow"] = par.dayofweek
    d = d[d["dow"] < 5]

    # --- qualité : part de barres à spread nul, par an (L60) ---
    q = d.groupby("year").agg(
        n_bars=("sp_bps", "size"),
        zero_frac=("spread", lambda x: float((x == 0).mean())),
        sp_med_bps=("sp_bps", "median"),
        sp_p75_bps=("sp_bps", lambda x: float(np.percentile(x, 75))),
        sp_p95_bps=("sp_bps", lambda x: float(np.percentile(x, 95))),
        sp_med_pts=("sp_pts", "median"),
    ).reset_index()
    q.insert(0, "symbol", sym)

    # --- profil horaire (horloge Paris), spread nul EXCLU du calcul de niveau ---
    dz = d[d["spread"] > 0]
    hp = dz.groupby("h").agg(
        n=("sp_bps", "size"),
        med_bps=("sp_bps", "median"),
        p75_bps=("sp_bps", lambda x: float(np.percentile(x, 75))),
        p95_bps=("sp_bps", lambda x: float(np.percentile(x, 95))),
        med_pts=("sp_pts", "median"),
        vol_med=("tick_volume", "median"),
    ).reset_index()
    hp.insert(0, "symbol", sym)
    day_med = float(dz["sp_bps"].median())
    hp["ratio_vs_jour"] = hp["med_bps"] / day_med

    # --- fenêtres opérationnelles de l'ORB live (horloge Paris) ---
    wins = {
        "OR_build_1530_1600": (15 * 60, 16 * 60),
        "entree_1600_1630": (16 * 60, 16 * 60 + 30),
        "entree_large_1600_1700": (16 * 60, 17 * 60),
        "vie_du_trade_1600_2200": (16 * 60, 22 * 60),
        "time_stop_2155_2205": (21 * 60 + 55, 22 * 60 + 5),
        "post_cloture_2200_2230": (22 * 60, 22 * 60 + 30),
        "journee_entiere": (0, 24 * 60),
    }
    rw = []
    for name, (a, b) in wins.items():
        m = dz[(dz["hm"] >= a) & (dz["hm"] < b)]
        mall = d[(d["hm"] >= a) & (d["hm"] < b)]
        if len(m) == 0:
            continue
        rw.append({
            "symbol": sym, "fenetre": name, "n_bars": len(m),
            "zero_frac": float((mall["spread"] == 0).mean()),
            "med_bps": float(m["sp_bps"].median()),
            "p75_bps": float(np.percentile(m["sp_bps"], 75)),
            "p90_bps": float(np.percentile(m["sp_bps"], 90)),
            "p95_bps": float(np.percentile(m["sp_bps"], 95)),
            "med_pts": float(m["sp_pts"].median()),
            "ratio_vs_jour": float(m["sp_bps"].median()) / day_med,
        })
    return q, hp, pd.DataFrame(rw)


def main() -> None:
    syms = sys.argv[1:] or ["US100", "GER40"]
    Q, H, W, T, C, M = [], [], [], [], [], []
    for s in syms:
        df = load(s)
        t0 = native_cutover(df)
        bpd = df.groupby(df.index.date).size()
        bpd.index = pd.to_datetime(bpd.index)
        cut = t0.tz_localize(None)
        C.append({"symbol": s, "n_rows": len(df),
                  "start": str(df.index[0]), "end": str(df.index[-1]),
                  "cutover_natif_mt5": str(t0.date()),
                  "bars_par_jour_avant": float(bpd[bpd.index < cut].median())
                  if (bpd.index < cut).any() else np.nan,
                  "bars_par_jour_apres": float(bpd[bpd.index >= cut].median()),
                  "pct_rows_natif": float((df.index >= t0).mean())})
        T.append(tz_falsification(df, s))
        M.append(monthly_diag(df, s))
        q, h, w = profile(df, s, t0)
        Q.append(q); H.append(h); W.append(w)
        # profil sur les 3 dernières années seulement (régime de coût courant)
        q3, h3, w3 = profile(df, s, df.index[-1] - pd.Timedelta(days=1095))
        w3["fenetre"] = w3["fenetre"] + "__3y"
        h3["symbol"] = s + "__3y"
        W.append(w3); H.append(h3)
        print(f"[{s}] cutover natif {t0.date()}  n={len(df)}", flush=True)

    pd.concat(M).to_csv(OUT / "s2_diag_mensuel.csv", index=False)
    pd.DataFrame(C).to_csv(OUT / "s2_couverture.csv", index=False)
    pd.concat(T).to_csv(OUT / "s2_tz_falsification.csv", index=False)
    pd.concat(Q).to_csv(OUT / "s2_qualite_par_an.csv", index=False)
    pd.concat(H).to_csv(OUT / "s2_profil_horaire_paris.csv", index=False)
    pd.concat(W).to_csv(OUT / "s2_fenetres.csv", index=False)
    print("ok")


if __name__ == "__main__":
    main()
