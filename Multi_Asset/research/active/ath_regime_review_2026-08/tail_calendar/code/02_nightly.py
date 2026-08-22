"""Reconstruction du rendement PAR NUIT des deux jambes overnight + chemin M5.

Horloge : sim_m5_repaired.parquet est verifie CET/CEST (cf. 01_tz_verify.py),
malgre le nom d'index `timestamp_utc`. Les horaires de sleeve sont donc lus
directement sur l'index.

Sleeve (spec_v22.yaml challenge.schedule_cet) :
  GER40 : entree 17:35 CET jour D  -> sortie 09:00 CET jour D+1
  US100 : entree 22:05 CET jour D  -> sortie 15:30 CET jour D+1
  D in {lundi, mardi}, long, aucun signal conditionnel.

Objets produits, PAR NUIT :
  - rendement de chaque jambe entree->sortie (close M5)
  - chemin M5 du P&L flottant COMBINE (les deux jambes se chevauchent 22:05->09:00)
  - MAE : minimum du flottant combine (c'est LUI que la barriere daily mord)
  - pire saut M5 unique (ce que le breaker discret ne peut pas devancer)
  - saut du HALT quotidien 22:45->00:05 CET (aucune cotation : intradable)

Sortie : out/nightly.parquet, out/nightly.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

# --- geometrie du sleeve (CET)
GER_IN, GER_OUT = 17 * 60 + 35, 9 * 60
US_IN, US_OUT = 22 * 60 + 5, 15 * 60 + 30
ON_DOW = (0, 1)  # lundi, mardi

# --- couts (spec_v22.yaml cost_anchors ; mesures 2026-06-10)
RT_BPS = {"US100": 2.2, "GER40": 2.2}          # aller-retour
SWAP_BPS_LONG = {"US100": -2.126, "GER40": -1.564}  # par nuit
TRIPLE_DOW = 4  # vendredi = swap x3 pour les indices (non atteint par Mon/Tue)


def load_m5() -> pd.DataFrame:
    m5 = pd.read_parquet(ROOT / "data/ftmo_portfolio/cache/sim_m5_repaired.parquet")
    m5 = m5[["US100", "GER40"]].sort_index()
    # masque de trous GER40 2018-2021 (miroir engine.load_market)
    raw_g = pd.read_parquet(ROOT / "data/ftmo_portfolio/cache/sim_m5.parquet")["GER40"]
    w = raw_g.loc["2018":"2021"].dropna()
    per_day = w.groupby(w.index.date).size()
    holes = {d.date() for d in pd.bdate_range("2018-01-01", "2021-12-31")
             if per_day.get(d.date(), 0) < 50}
    day_of = pd.Series(m5.index.date, index=m5.index)
    m5.loc[day_of.isin(holes).values, "GER40"] = np.nan
    return m5


def minute_of_day(idx) -> np.ndarray:
    return idx.hour * 60 + idx.minute


def px_at(day_bars: pd.Series, target_min: int, mode: str):
    """Prix a l'horaire cible. mode='at_or_before' (entree), 'at_or_after' (sortie)."""
    s = day_bars.dropna()
    if s.empty:
        return np.nan, pd.NaT
    mins = minute_of_day(s.index)
    if mode == "at_or_before":
        m = mins <= target_min
    else:
        m = mins >= target_min
    if not m.any():
        return np.nan, pd.NaT
    sub = s[m]
    ts = sub.index[-1] if mode == "at_or_before" else sub.index[0]
    # tolerance : ne pas accepter un prix a plus de 60 min de la cible
    if abs(int(minute_of_day(pd.DatetimeIndex([ts]))[0]) - target_min) > 60:
        return np.nan, pd.NaT
    return float(sub.loc[ts]), ts


def main():
    m5 = load_m5()
    days = sorted({d for d in m5.index.date})
    day_index = {d: i for i, d in enumerate(days)}
    by_day = {d: g for d, g in m5.groupby(m5.index.date)}

    rows = []
    for d in days:
        ts_d = pd.Timestamp(d)
        if ts_d.dayofweek not in ON_DOW:
            continue
        i = day_index[d]
        if i + 1 >= len(days):
            continue
        d1 = days[i + 1]
        # la sortie doit etre le jour de bourse SUIVANT, pas plus de 4 jours apres
        if (pd.Timestamp(d1) - ts_d).days > 4:
            continue
        g0, g1 = by_day[d], by_day[d1]

        rec = dict(entry_date=ts_d, exit_date=pd.Timestamp(d1), dow=ts_d.dayofweek)

        legs = {}
        for leg, tin, tout, gin in [("GER40", GER_IN, GER_OUT, g0),
                                    ("US100", US_IN, US_OUT, g0)]:
            p_in, t_in = px_at(gin[leg], tin, "at_or_before")
            p_out, t_out = px_at(g1[leg], tout, "at_or_after")
            rec[f"{leg}_in"], rec[f"{leg}_out"] = p_in, p_out
            rec[f"{leg}_t_in"], rec[f"{leg}_t_out"] = t_in, t_out
            r = p_out / p_in - 1.0 if np.isfinite(p_in) and np.isfinite(p_out) else np.nan
            rec[f"{leg}_ret"] = r
            legs[leg] = (t_in, t_out, p_in)

        # --- chemin M5 du flottant COMBINE (unites = fraction de notionnel par jambe)
        t0 = min([t for t, _, _ in legs.values() if pd.notna(t)], default=pd.NaT)
        t1 = max([t for _, t, _ in legs.values() if pd.notna(t)], default=pd.NaT)
        if pd.notna(t0) and pd.notna(t1):
            win = m5.loc[t0:t1]
            comb = pd.Series(0.0, index=win.index)
            nlegs = pd.Series(0.0, index=win.index)
            for leg, (t_in, t_out, p_in) in legs.items():
                if pd.isna(t_in) or pd.isna(t_out) or not np.isfinite(p_in):
                    continue
                p_out = rec[f"{leg}_out"]
                seg = win[leg].ffill()
                pnl = (seg / p_in - 1.0)
                # 0 avant l'entree ; flottant pendant la detention ; REALISE apres
                # (fermer une jambe ne remet PAS l'equite a zero : le P&L passe en
                # balance, la courbe d'equite est continue).
                pnl = pnl.where((win.index >= t_in) & (win.index <= t_out), np.nan)
                pnl[win.index > t_out] = p_out / p_in - 1.0
                pnl[win.index < t_in] = 0.0
                comb = comb + pnl.ffill().fillna(0.0)
                nlegs = nlegs + ((win.index >= t_in) & (win.index <= t_out)).astype(float)
            rec["mae_comb"] = float(comb.min())          # pire flottant combine
            rec["end_comb"] = float(comb.iloc[-1])
            rec["max_legs_open"] = float(nlegs.max())
            # pire saut M5 unique du flottant combine
            dcomb = comb.diff().dropna()
            rec["worst_m5_jump"] = float(dcomb.min()) if len(dcomb) else np.nan
            rec["mae_ts"] = comb.idxmin()
        else:
            rec["mae_comb"] = rec["end_comb"] = rec["worst_m5_jump"] = np.nan
            rec["max_legs_open"] = np.nan
            rec["mae_ts"] = pd.NaT

        # --- saut du HALT quotidien (derniere cotation avant 23:00 -> premiere apres 00:00)
        for leg in ("US100", "GER40"):
            p_pre, t_pre = px_at(g0[leg], 22 * 60 + 50, "at_or_before")
            s1 = g1[leg].dropna()
            if len(s1) and np.isfinite(p_pre):
                rec[f"{leg}_halt_gap"] = float(s1.iloc[0] / p_pre - 1.0)
            else:
                rec[f"{leg}_halt_gap"] = np.nan
        rows.append(rec)

    df = pd.DataFrame(rows).set_index("entry_date").sort_index()

    # --- P&L par jambe, net de couts, en fraction de NOTIONNEL
    for leg in ("US100", "GER40"):
        cost = RT_BPS[leg] / 1e4                       # aller-retour complet
        swap = SWAP_BPS_LONG[leg] / 1e4                # 1 nuit
        df[f"{leg}_net"] = df[f"{leg}_ret"] - cost + swap

    df["comb_gross"] = df["US100_ret"].fillna(0) + df["GER40_ret"].fillna(0)
    df["comb_net"] = df["US100_net"].fillna(0) + df["GER40_net"].fillna(0)
    df["n_legs"] = df[["US100_ret", "GER40_ret"]].notna().sum(axis=1)

    df.to_parquet(OUT / "nightly.parquet")
    df.to_csv(OUT / "nightly.csv")

    print(f"nuits ON reconstruites : {len(df)}  ({df.index.min().date()} -> {df.index.max().date()})")
    print(df["n_legs"].value_counts().sort_index().to_string())
    print("\njambes disponibles :")
    for leg in ("US100", "GER40"):
        s = df[f"{leg}_ret"].dropna()
        print(f"  {leg}: n={len(s)}  {s.index.min().date()} -> {s.index.max().date()}")
    print("\n-> out/nightly.parquet")


if __name__ == "__main__":
    main()
