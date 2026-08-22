"""Reconstruction des séries de rendement sleeve-par-sleeve du book FTMO funded.

Book funded déployé (compte <ACCOUNT_ID>, $10 000) — spec `data/ftmo_portfolio/v22/spec_v22.yaml`
section `funded` : vm=1.0, on_w=0.35, orb_risk=0.0025, glide=1.0, pace=0, taper=0.02.

Trois sleeves actives :
  on_us100 : long US100.cash, 22:05 Paris -> 15:30 Paris J+1, lundi et mardi seulement.
  on_ger40 : long GER40.cash, 17:35 Paris -> 09:00 Paris J+1, lundi et mardi seulement.
  orb      : breakout US100 OR 15:30-16:00, risque 0.25% du compte, time-stop 22:00.
XAUUSD et USDJPY sont à poids ZÉRO dans la config funded -> sleeves inactives.

Sortie : `daily_raw.csv` (grain journalier, toutes les composantes séparées).
Les agrégations mensuelles et les métriques sont dans `metrics.py`.

Interpréteur : /usr/bin/python3
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
CACHE = ROOT / "data/ftmo_portfolio/cache"
OUT = Path(__file__).resolve().parent

INIT = 10_000.0
ON_W = 0.35            # spec funded : on_w * vm(1.0) ; gouverneur = 1.0 hors zone de taper
ORB_RISK = 0.0025      # FU_ORB_RISK, sur ACCOUNT_SIZE_USD (constante), pas sur l'équité

# Coûts RT mesurés en natif (semaine du 2026-08-17), bps aller-retour.
RT_BPS = {"US100": 1.045, "GER40": 1.017, "XAUUSD": 2.037, "USDJPY": 0.379}
RT_BPS_AT_ENTRY = {"US100": 1.039, "GER40": 0.941}   # variante horodatée (sensibilité)

# Ancre swap corrigée, mesurée sur `swaps_billed_live.csv` (facture FTMO réelle).
SWAP_MEASURED = {"US100": None, "GER40": None}       # rempli plus bas depuis la facture

SCHED = {"0900": 9 * 60, "1530": 15 * 60 + 30, "1735": 17 * 60 + 35, "2205": 22 * 60 + 5}


# --------------------------------------------------------------------- data
def load_m5() -> pd.DataFrame:
    """Panel M5 audité. Index = horloge PARIS (vérifié : pic de vol US100 à 15:30-16:00,
    GER40 à 09:00-09:30 ; le fichier source `US100_m5_close.parquet` porte un index
    tz-aware Europe/Paris). Le nom de colonne `timestamp_utc` du panel est FAUX (L52)."""
    m5 = pd.read_parquet(CACHE / "sim_m5_repaired.parquet")[["US100", "GER40"]]
    return m5.ffill()


def ger40_hole_mask(m5: pd.DataFrame) -> pd.DataFrame:
    """Masque des trous GER40 2018-2021 (< 50 barres/jour dans le fichier PRE-repair),
    identique au moteur cleanroom `engine.load_market`."""
    raw_g = pd.read_parquet(CACHE / "sim_m5.parquet")["GER40"]
    w = raw_g.loc["2018":"2021"].dropna()
    per_day = w.groupby(w.index.date).size()
    holes = {d.date() for d in pd.bdate_range("2018-01-01", "2021-12-31")
             if per_day.get(d.date(), 0) < 50}
    day_of = pd.Series(m5.index.date, index=m5.index)
    m5 = m5.copy()
    m5.loc[day_of.isin(holes).values, "GER40"] = np.nan
    return m5


def day_table(m5: pd.DataFrame) -> pd.DataFrame:
    """Un enregistrement par séance : prix à chaque heure planifiée + dernier prix."""
    mins = m5.index.hour * 60 + m5.index.minute
    rows = []
    for d, g in m5.groupby(m5.index.date):
        if len(g) < 30:
            continue
        gm = (g.index.hour * 60 + g.index.minute).to_numpy()
        rec = {"date": pd.Timestamp(d)}
        for name, t in SCHED.items():
            j = int(np.searchsorted(gm, t, side="left"))
            for c in ("US100", "GER40"):
                rec[f"{c}_{name}"] = float(g[c].to_numpy()[j]) if j < len(gm) else np.nan
        for c in ("US100", "GER40"):
            rec[f"{c}_last"] = float(g[c].to_numpy()[-1])
        rows.append(rec)
    return pd.DataFrame(rows).set_index("date")


# ------------------------------------------------------------------- swaps
def measured_swap_bps() -> dict:
    """bps/nuit facturés réellement, depuis `swaps_billed_live.csv` (N nuits réelles)."""
    bill = pd.read_csv(ROOT / "data/ftmo_portfolio/swaps_billed_live.csv")
    bill["sym"] = bill["symbol"].str.replace(".cash", "", regex=False)
    bill["bps"] = bill["swap_usd"] / bill["notional_usd"] * 1e4
    g = bill.groupby("sym")["bps"]
    return {k: dict(mean=float(v.mean()), n=int(v.count()), std=float(v.std()))
            for k, v in g}


# ------------------------------------------------------------- OR (US100 M1)
def or_width() -> pd.DataFrame:
    """Vrai high/low de l'opening range 15:30-15:59 Paris depuis les barres M1 UTC
    canoniques `data/deep_history_utc/US100_M1.csv` (OHLC réel, pas des closes M5)."""
    p = ROOT / "data/deep_history_utc/US100_M1.csv"
    df = pd.read_csv(p, usecols=["timestamp_utc", "high", "low", "close"],
                     parse_dates=["timestamp_utc"],
                     date_format="%Y.%m.%d %H:%M:%S")
    idx = df["timestamp_utc"].dt.tz_localize("UTC").dt.tz_convert("Europe/Paris")
    df = df.set_index(idx).drop(columns=["timestamp_utc"])
    hm = df.index.hour * 60 + df.index.minute
    win = df[(hm >= 15 * 60 + 30) & (hm < 16 * 60)]
    g = win.groupby(win.index.date)
    out = pd.DataFrame({"or_hi": g["high"].max(), "or_lo": g["low"].min(),
                        "or_end_close": g["close"].last(), "or_bars": g["close"].size()})
    out.index = pd.to_datetime(out.index)
    out["or_range"] = out["or_hi"] - out["or_lo"]
    out["or_bps"] = out["or_range"] / out["or_end_close"] * 1e4
    return out


# ------------------------------------------------------------------- build
def build() -> pd.DataFrame:
    m5 = ger40_hole_mask(load_m5())
    D = day_table(m5)
    dates = D.index

    swL = pd.read_parquet(CACHE / "panel_swapL.parquet")[["US100", "GER40"]]
    mult = pd.read_parquet(CACHE / "panel_mult.parquet")[["US100", "GER40"]]
    swL = swL.reindex(dates).ffill()
    mult = mult.reindex(dates).fillna(1.0)

    meas = measured_swap_bps()
    for k in ("US100", "GER40"):
        SWAP_MEASURED[k] = meas[k]["mean"]

    nxt = pd.Series(list(dates[1:]) + [pd.NaT], index=dates)
    is_on = pd.Series(dates.dayofweek.isin([0, 1]), index=dates)

    out = pd.DataFrame(index=dates)
    out["is_on_day"] = is_on.astype(int)
    out["next_date"] = nxt
    out["gap_days"] = (pd.to_datetime(nxt) - dates.to_series()).dt.days

    # ---- jambes ON : prix d'entrée le jour D, prix de sortie la séance suivante
    for sym, ent, ex in (("US100", "2205", "1530"), ("GER40", "1735", "0900")):
        p_in = D[f"{sym}_{ent}"]
        p_out = D[f"{sym}_{ex}"].reindex(nxt.values)
        p_out.index = dates
        live = is_on & p_in.notna() & p_out.notna()
        gross = (p_out / p_in - 1.0).where(live, 0.0).fillna(0.0)
        # coût : demi-RT à l'ouverture + demi-RT à la fermeture, sur le notionnel
        cost = np.where(live, ON_W * RT_BPS[sym] / 1e4, 0.0)
        # swap : posté à l'EOD de la nuit tenue, sur le notionnel tenu
        sw_panel = np.where(live, ON_W * swL[sym].to_numpy() / 1e4 * mult[sym].to_numpy(), 0.0)
        corr = SWAP_MEASURED[sym] / float(swL[sym].iloc[-1])
        sw_meas = sw_panel * corr
        tag = "us100" if sym == "US100" else "ger40"
        out[f"on_{tag}_live"] = live.astype(int)
        out[f"on_{tag}_px_ret"] = gross.to_numpy()
        out[f"on_{tag}_gross"] = ON_W * gross.to_numpy()
        out[f"on_{tag}_cost"] = -cost
        out[f"on_{tag}_swap_panel"] = sw_panel
        out[f"on_{tag}_swap_meas"] = sw_meas
        out[f"on_{tag}"] = ON_W * gross.to_numpy() - cost + sw_panel
        out[f"on_{tag}_swapcorr"] = ON_W * gross.to_numpy() - cost + sw_meas

    # ---- ORB : ledger canonique era-costé (R déjà net de coût)
    R = pd.read_parquet(CACHE / "orb_e7_Rera.parquet")["R"].reindex(dates).fillna(0.0)
    ORW = or_width().reindex(dates)
    lots = np.floor(ORB_RISK * INIT / ORW["or_range"].to_numpy() / 0.01) * 0.01
    notional = lots * ORW["or_end_close"].to_numpy()
    out["orb_R"] = R.to_numpy()
    out["orb"] = ORB_RISK * R.to_numpy()
    out["orb_live"] = (R != 0).astype(int)
    out["orb_or_bps"] = ORW["or_bps"].to_numpy()
    out["orb_notional_usd"] = np.where(R.to_numpy() != 0, notional, np.nan)
    out["orb_w"] = out["orb_notional_usd"] / INIT

    # ---- sous-jacents : buy-and-hold close-to-close SUR LA MÊME SOURCE M5
    for sym, tag in (("US100", "us100"), ("GER40", "ger40")):
        r = D[f"{sym}_last"].pct_change().fillna(0.0)
        out[f"und_{tag}"] = r.to_numpy()
        out[f"bh_{tag}"] = ON_W * r.to_numpy()
        sw = ON_W * swL[sym].to_numpy() / 1e4 * mult[sym].to_numpy()
        out[f"bh_{tag}_swap"] = sw
        out[f"bh_{tag}_net"] = ON_W * r.to_numpy() + sw

    out["portefeuille"] = out["on_us100"] + out["on_ger40"] + out["orb"]
    out["portefeuille_swapcorr"] = (out["on_us100_swapcorr"] + out["on_ger40_swapcorr"]
                                    + out["orb"])
    # sleeves inactives — poids zéro dans la config funded
    out["xau"] = 0.0
    out["j1"] = 0.0
    return out


if __name__ == "__main__":
    df = build()
    df.to_csv(OUT / "daily_raw.csv", float_format="%.10g")
    meas = measured_swap_bps()
    print("swap mesuré (facture) :", meas)
    print("panel dernier :", pd.read_parquet(CACHE / "panel_swapL.parquet")
          [["US100", "GER40"]].iloc[-1].to_dict())
    print("N séances", len(df), df.index.min().date(), df.index.max().date())
    for c in ("on_us100", "on_ger40", "orb"):
        live = df[f"{c}_live"] if f"{c}_live" in df else df["orb_live"]
        print(f"{c:10s} N_trades={int(live.sum()):5d}  "
              f"somme={df[c].sum()*100:8.2f}%  moy/trade={df[c].sum()/max(live.sum(),1)*1e4:7.2f} bps")
    print("gap_days sur jours ON:",
          df.loc[df.is_on_day == 1, "gap_days"].value_counts().head(5).to_dict())
    print("OR bars/jour médian:", np.nanmedian(df["orb_or_bps"]))
    print("orb_w moyen:", df["orb_w"].mean(), "médian:", df["orb_w"].median())
