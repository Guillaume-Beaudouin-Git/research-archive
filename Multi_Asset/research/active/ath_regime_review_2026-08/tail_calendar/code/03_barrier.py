"""Marche de barriere M5, nuit par nuit, sur la geometrie P2 fraiche.

Geometrie (confirmee par le porteur du risque + verifiee contre le code) :
  equite initiale        10 000
  ancre de balance       10 000 a 00:00 CET (aucun trade realise -> INCHANGEE
                         pendant toute la detention, donc UNE seule barriere
                         effective couvre les deux jours civils de la nuit)
  budget daily           5% x initial = 500      -> limite daily   9 500
  plancher statique      90% x initial           -> plancher       9 000
  limite dure FTMO       max(daily, statique)    -> 9 500  (le DAILY mord)
  ligne de breaker v2.4  daily + 0.30 x budget   -> 9 650
    (invariants.breaker_line(10000, 0.30) == 9650.0, teste ftmo_live/tests)

Equite(t) = E0 x (1 + L x comb(t)), comb = somme des flottants par jambe
(notionnel par jambe = L x E0).

Latence du breaker : l'EA detecte a la CLOTURE d'une barre M5 et envoie l'ordre ;
le fill realiste est la barre SUIVANTE. On rapporte les deux (fill a la barre de
detection = optimiste ; fill barre suivante = realiste). Pendant le halt quotidien
(~22:45 -> 00:05 CET) il n'existe AUCUNE barre : le breaker est aveugle par
construction.

Sortie : out/barrier_L{L}.csv, out/barrier_summary.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "out"

E0 = 10_000.0
BUDGET = 0.05 * E0
FLOOR = 0.90 * E0
BRK_FRAC = 0.30

LIM_DAILY = E0 - BUDGET          # 9500
LIM_STATIC = FLOOR               # 9000
LIM_EFF = max(LIM_DAILY, LIM_STATIC)   # 9500 -> le daily mord
BRK_LINE = LIM_DAILY + BRK_FRAC * BUDGET  # 9650

GER_IN, GER_OUT = 17 * 60 + 35, 9 * 60
US_IN, US_OUT = 22 * 60 + 5, 15 * 60 + 30
ON_DOW = (0, 1)

RT_BPS = {"US100": 2.2, "GER40": 2.2}
SWAP_BPS_LONG = {"US100": -2.126, "GER40": -1.564}

LEVERAGES = [4.5, 10.6, 16.8]   # 4.5 = cap marge Swing mesure ; 10.6 = deploye


def load_m5():
    m5 = pd.read_parquet(ROOT / "data/ftmo_portfolio/cache/sim_m5_repaired.parquet")
    m5 = m5[["US100", "GER40"]].sort_index()
    raw_g = pd.read_parquet(ROOT / "data/ftmo_portfolio/cache/sim_m5.parquet")["GER40"]
    w = raw_g.loc["2018":"2021"].dropna()
    per_day = w.groupby(w.index.date).size()
    holes = {d.date() for d in pd.bdate_range("2018-01-01", "2021-12-31")
             if per_day.get(d.date(), 0) < 50}
    day_of = pd.Series(m5.index.date, index=m5.index)
    m5.loc[day_of.isin(holes).values, "GER40"] = np.nan
    return m5


def mod_of(idx):
    return idx.hour * 60 + idx.minute


def px_at(day_bars, target_min, mode):
    s = day_bars.dropna()
    if s.empty:
        return np.nan, pd.NaT
    mins = mod_of(s.index)
    m = (mins <= target_min) if mode == "before" else (mins >= target_min)
    if not m.any():
        return np.nan, pd.NaT
    sub = s[m]
    ts = sub.index[-1] if mode == "before" else sub.index[0]
    if abs(int(mod_of(pd.DatetimeIndex([ts]))[0]) - target_min) > 60:
        return np.nan, pd.NaT
    return float(sub.loc[ts]), ts


def build_paths():
    """Genere (date, comb_path) pour chaque nuit ON."""
    m5 = load_m5()
    days = sorted({d for d in m5.index.date})
    by_day = {d: g for d, g in m5.groupby(m5.index.date)}
    for i, d in enumerate(days):
        ts_d = pd.Timestamp(d)
        if ts_d.dayofweek not in ON_DOW or i + 1 >= len(days):
            continue
        d1 = days[i + 1]
        if (pd.Timestamp(d1) - ts_d).days > 4:
            continue
        g0, g1 = by_day[d], by_day[d1]
        legs = {}
        for leg, tin, tout in [("GER40", GER_IN, GER_OUT), ("US100", US_IN, US_OUT)]:
            p_in, t_in = px_at(g0[leg], tin, "before")
            p_out, t_out = px_at(g1[leg], tout, "after")
            if np.isfinite(p_in) and np.isfinite(p_out):
                legs[leg] = (t_in, t_out, p_in, p_out)
        if not legs:
            continue
        t0 = min(v[0] for v in legs.values())
        t1 = max(v[1] for v in legs.values())
        win = m5.loc[t0:t1]
        comb = pd.Series(0.0, index=win.index)
        for leg, (t_in, t_out, p_in, p_out) in legs.items():
            # 0 avant l'entree ; flottant pendant la detention ; REALISE apres la
            # sortie (fermer une jambe deplace son P&L de flottant vers balance :
            # l'equite est CONTINUE, elle ne retombe pas a zero).
            seg = win[leg].ffill()
            pnl = (seg / p_in - 1.0)
            held = (win.index >= t_in) & (win.index <= t_out)
            pnl = pnl.where(held, np.nan)
            pnl[win.index > t_out] = p_out / p_in - 1.0
            pnl[win.index < t_in] = 0.0
            comb = comb + pnl.ffill().fillna(0.0)
        rets = {leg: legs[leg][3] / legs[leg][2] - 1.0 for leg in legs}
        stale = win[list(legs)].isna().all(axis=1).to_numpy()
        yield ts_d, comb, rets, set(legs), stale


def barrier_walk(comb: pd.Series, L: float, stale=None):
    """Marche de barriere. Renvoie aussi le MECANISME du bust :

    'saute'  : la barre precedente etait AU-DESSUS de la ligne de breaker et la
               suivante est DEJA sous la limite dure -> le breaker discret n'a
               jamais eu de barre pour agir (c'est le mecanisme du breach
               <ACCOUNT_ID> : la liquidation continue bat un check discret M5).
    'halt'   : ce saut est celui du halt quotidien (~22:45 -> 00:05 CET), ou il
               n'existe litteralement aucune barre M5.
    'graduel': l'equite a traverse la ligne de breaker sur une barre, puis la
               limite dure sur une barre ulterieure (le breaker avait la main).
    """
    eq = E0 * (1.0 + L * comb.to_numpy())
    idx = np.where(eq < BRK_LINE)[0]
    ibust = np.where(eq < LIM_EFF)[0]
    out = dict(mae_comb=float(comb.min()), min_eq_nostop=float(eq.min()),
               brk_hit=bool(len(idx)), bust_nostop=bool(eq.min() < LIM_EFF),
               floor_nostop=bool(eq.min() < LIM_STATIC), mech="", bust_tod="")
    if len(ibust):
        j = int(ibust[0])
        prev_eq = eq[j - 1] if j > 0 else E0
        out["bust_tod"] = comb.index[j].strftime("%H:%M")
        if prev_eq >= BRK_LINE:                       # aucune barre exploitable
            # la grille M5 porte des lignes RANCES pendant le halt (~22:45->00:05
            # CET) : le saut n'est pas detectable par l'ecart d'horodatage, il
            # l'est par l'absence de cotation sur les barres precedentes.
            out["mech"] = "halt" if stale is not None and bool(stale[j - 1]) else "saute"
        else:
            out["mech"] = "graduel"
    if not len(idx):
        out.update(eq_flat_opt=np.nan, eq_flat_real=np.nan,
                   bust_opt=False, bust_real=False, floor_real=False, brk_ts=pd.NaT)
        return out
    k = int(idx[0])
    kr = min(k + 1, len(eq) - 1)
    out.update(eq_flat_opt=float(eq[k]), eq_flat_real=float(eq[kr]),
               bust_opt=bool(eq[k] < LIM_EFF), bust_real=bool(eq[kr] < LIM_EFF),
               floor_real=bool(eq[kr] < LIM_STATIC), brk_ts=comb.index[k])
    return out


def main():
    paths = list(build_paths())
    print(f"nuits avec chemin M5 exploitable : {len(paths)}")

    base = []
    for d, comb, rets, legset, _st in paths:
        # saut du halt : derniere barre <=22:50 -> premiere barre du jour suivant
        c = comb
        same_day = c.index.normalize() == d
        pre = c[same_day & (mod_of(c.index) <= 22 * 60 + 50)]
        post = c[~same_day]
        halt = float(post.iloc[0] - pre.iloc[-1]) if len(pre) and len(post) else np.nan
        base.append(dict(date=d, dow=d.dayofweek, n_legs=len(legset),
                         us100_ret=rets.get("US100", np.nan),
                         ger40_ret=rets.get("GER40", np.nan),
                         comb_gross=sum(rets.values()),
                         comb_net=sum(rets[l] - RT_BPS[l] / 1e4 + SWAP_BPS_LONG[l] / 1e4
                                      for l in rets),
                         mae_comb=float(comb.min()),
                         worst_m5_jump=float(comb.diff().min()),
                         halt_gap=halt))
    bdf = pd.DataFrame(base).set_index("date")

    summ = {}
    for L in LEVERAGES:
        rows = []
        for (d, comb, _, _, st) in paths:
            r = barrier_walk(comb, L, st)
            r["date"] = d
            rows.append(r)
        df = pd.DataFrame(rows).set_index("date").drop(columns=["mae_comb"])
        df = bdf.join(df, how="left")
        df["era"] = pd.cut(df.index, bins=pd.to_datetime(
            ["2013-01-01", "2018-01-01", "2020-01-01", "2022-01-01", "2024-01-01", "2027-01-01"]),
            labels=["2013-2017", "2018-2019", "2020-2021", "2022-2023", "2024-2026"])
        df.to_csv(OUT / f"barrier_L{L}.csv")
        n = len(df)
        summ[str(L)] = dict(
            n_nights=n,
            thr_breaker_comb=-0.035 / L, thr_bust_comb=-0.05 / L, thr_floor_comb=-0.10 / L,
            brk_hit=int(df.brk_hit.sum()), brk_hit_pct=100 * df.brk_hit.mean(),
            bust_nostop=int(df.bust_nostop.sum()), bust_nostop_pct=100 * df.bust_nostop.mean(),
            bust_real=int(df.bust_real.sum()), bust_real_pct=100 * df.bust_real.mean(),
            floor_nostop=int(df.floor_nostop.sum()),
            floor_real=int(df.floor_real.sum()),
            gap_kill=int((df.brk_hit & df.bust_real).sum()),
        )
        print(f"\n=== L = {L}x par jambe ===")
        print(f" seuils en mouvement COMBINE : breaker {-3.5/L:.3f}%  bust {-5.0/L:.3f}%  "
              f"plancher {-10.0/L:.3f}%")
        print(f" breaker touche      : {df.brk_hit.sum():4d} / {n}  ({100*df.brk_hit.mean():5.2f}%)")
        print(f" bust SANS breaker   : {df.bust_nostop.sum():4d} / {n}  ({100*df.bust_nostop.mean():5.2f}%)")
        print(f" bust MALGRE breaker : {df.bust_real.sum():4d} / {n}  ({100*df.bust_real.mean():5.2f}%)")
        print(f" plancher 9000 franchi (sans stop / malgre breaker) : "
              f"{df.floor_nostop.sum()} / {df.floor_real.sum()}")
        hg = df["halt_gap"].dropna()
        print(f" saut du HALT seul (intradable) : consomme le budget daily "
              f"({(hg * L <= -0.05).sum()} nuits, {100*(hg*L<=-0.05).mean():.2f}%) ; "
              f"franchit le plancher 9000 ({(hg * L <= -0.10).sum()} nuits)")
        bb = df[df.bust_nostop]
        print(f" mecanisme du bust (sur les {len(bb)} nuits qui touchent 9500) :")
        print("   " + bb["mech"].value_counts().to_string().replace("\n", "\n   "))
        print(" par sous-periode :")
        g = df.groupby("era", observed=True).agg(
            n=("brk_hit", "size"), brk=("brk_hit", "sum"),
            bust_ns=("bust_nostop", "sum"), bust_r=("bust_real", "sum"),
            floor_r=("floor_real", "sum"))
        g["brk_%"] = (100 * g.brk / g.n).round(2)
        g["bust_r_%"] = (100 * g.bust_r / g.n).round(2)
        print(g.to_string())

    (OUT / "barrier_summary.json").write_text(json.dumps(summ, indent=2, default=str))
    bdf.to_csv(OUT / "nightly_base.csv")
    print("\n-> out/barrier_L*.csv, out/barrier_summary.json")


if __name__ == "__main__":
    main()
