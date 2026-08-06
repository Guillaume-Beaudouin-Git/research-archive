"""Etape 0 — bornes AVANT tout rendement (L52, L56, L59, L60) + tradabilite du 23:05.

Trois questions, dans cet ordre :
  A. TRADABILITE. Le CFD cote-t-il a 22:35 / 23:05 / 23:35 / 00:05 Paris ? Un CFD
     indice FTMO suit la pause CME (17:00-18:00 ET = 23:00-00:00 Paris toute
     l'annee). Si la borne n'est pas cotee, la variante n'EXISTE pas. Couverture
     de barre M1 minute par minute, 21:00-01:30 Paris, par ere ET par annee.
  B. L56. Dans quelle horloge le profil intra-journalier est-il ancre ? Test
     gratuit : correlation du profil HORAIRE hiver-vs-ete dans les trois horloges
     (Paris, New York, UTC). Statistique a fort rapport signal/bruit = ACTIVITE
     (|rendement| moyen et tick_volume) ; le rendement moyen horaire est rapporte
     aussi mais il est domine par le bruit et ne discrimine rien (montre ici).
  C. L60. Part des barres a fourchette NULLE (high==low), par serie, par annee,
     ET specifiquement sur les bornes horaires utilisees par ce dossier.
"""
from __future__ import annotations
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_m1, stamps, ERA_CUT, TZ  # noqa

ERA_CUT_TZ = ERA_CUT.tz_localize(TZ)

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
os.makedirs(OUT, exist_ok=True)
SYMS = ("US100", "GER40")
CAND = [(22, 5), (22, 35), (22, 45), (23, 5), (23, 35), (0, 5), (0, 35), (1, 5)]


# ---------------------------------------------------------------- A. tradabilite
def coverage_profile(df: pd.DataFrame, sym: str) -> pd.DataFrame:
    idx = df.index
    days = pd.DatetimeIndex(sorted(set(idx.normalize().tz_localize(None))))
    days = days[days.dayofweek < 5]
    have = pd.Series(1, index=idx)
    grid = [(h, m) for h in (21, 22, 23, 0, 1) for m in range(0, 60, 5)]
    rows = []
    eras = [("full", days), ("post-2021", days[days >= ERA_CUT])]
    eras += [(str(y), days[days.year == y]) for y in range(2021, 2027)]
    for era, dsel in eras:
        if len(dsel) == 0:
            continue
        for hh, mm in grid:
            shift = 1 if hh in (0, 1) else 0
            tg = stamps(dsel, hh, mm, day_shift=shift)
            rows.append({"sym": sym, "era": era, "hhmm": f"{hh:02d}:{mm:02d}",
                         "N_days": len(dsel),
                         "cov_exact": float(have.reindex(tg).notna().mean())})
    return pd.DataFrame(rows)


def halt_window(df: pd.DataFrame, sym: str) -> pd.DataFrame:
    """Pour chaque jour ouvre : derniere barre avant 23:30 Paris et premiere barre
    apres. Mesure la BORNE REELLE de la pause, et sa stabilite hiver/ete."""
    idx = df.index
    days = pd.DatetimeIndex(sorted(set(idx.normalize().tz_localize(None))))
    days = days[(days.dayofweek < 5) & (days >= ERA_CUT)]
    s = pd.Series(idx, index=idx)
    piv = pd.Series(index=days, dtype=object)
    last, first = [], []
    anchor = stamps(days, 23, 30)
    for a in anchor:
        pre = s.loc[:a]
        post = s.loc[a:]
        last.append(pre.iloc[-1] if len(pre) else pd.NaT)
        first.append(post.iloc[0] if len(post) else pd.NaT)
    out = pd.DataFrame({"day": days, "last_before": last, "first_after": first})
    out = out.dropna()
    off = np.array([t.utcoffset().total_seconds() / 3600 for t in anchor[:len(out)]])
    out["season"] = np.where(off == 1.0, "hiver(CET)", "ete(CEST)")
    out["last_hm"] = [t.strftime("%H:%M") for t in out["last_before"]]
    out["first_hm"] = [t.strftime("%H:%M") for t in out["first_after"]]
    g = (out.groupby(["season", "last_hm"]).size().rename("n").reset_index()
         .sort_values(["season", "n"], ascending=[True, False]))
    g2 = (out.groupby(["season", "first_hm"]).size().rename("n").reset_index()
          .sort_values(["season", "n"], ascending=[True, False]))
    g["sym"] = sym; g2["sym"] = sym
    return g.head(8), g2.head(8)


# ------------------------------------------------------------------ B. L56 clock
def l56_falsification(df: pd.DataFrame, sym: str) -> pd.DataFrame:
    c = df["close"]
    r = np.log(c / c.shift(1)) * 1e4
    absr = r.abs()
    vol = df["tick_volume"].astype(float)
    off = np.array([t.utcoffset().total_seconds() / 3600 for t in df.index])
    win, sum_ = off == 1.0, off == 2.0
    rows = []
    for tzname in ("Europe/Paris", "America/New_York", "UTC"):
        hh = df.index.tz_convert(tzname).hour
        out = {"sym": sym, "clock": tzname}
        for name, ser in (("abs_ret", absr), ("tick_vol", vol), ("mean_ret", r)):
            a = ser[win].groupby(hh[win]).mean()
            b = ser[sum_].groupby(hh[sum_]).mean()
            j = pd.concat([a, b], axis=1).dropna()
            out[f"corr_{name}"] = float(j.corr().iloc[0, 1])
        rows.append(out)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------- C. L60 zero
def l60_zero_range(df: pd.DataFrame, sym: str) -> pd.DataFrame:
    z = (df["high"] == df["low"])
    g = z.groupby(df.index.year)
    a = pd.DataFrame({"sym": sym, "scope": "all_bars", "year": g.mean().index,
                      "frac_zero_range": g.mean().values, "n_bars": g.size().values})
    # meme mesure restreinte aux bornes horaires du dossier
    rows = []
    for hh, mm in CAND:
        m = (df.index.hour == hh) & (df.index.minute == mm)
        if m.sum() == 0:
            rows.append({"sym": sym, "scope": f"stamp_{hh:02d}:{mm:02d}", "year": -1,
                         "frac_zero_range": np.nan, "n_bars": 0})
            continue
        sub = df[m]
        sub = sub[sub.index >= ERA_CUT_TZ]
        rows.append({"sym": sym, "scope": f"stamp_{hh:02d}:{mm:02d}", "year": -1,
                     "frac_zero_range": float((sub["high"] == sub["low"]).mean()),
                     "n_bars": int(len(sub))})
    return pd.concat([a, pd.DataFrame(rows)])


def main():
    cov, l56, l60, hw1, hw2 = [], [], [], [], []
    for sym in SYMS:
        df = load_m1(sym)
        print(f"[{sym}] {len(df):,} barres  {df.index.min()} -> {df.index.max()}")
        cov.append(coverage_profile(df, sym))
        l56.append(l56_falsification(df, sym))
        l60.append(l60_zero_range(df, sym))
        a, b = halt_window(df, sym)
        hw1.append(a); hw2.append(b)
    cv = pd.concat(cov); cv.to_csv(os.path.join(OUT, "step0_coverage_night.csv"), index=False)
    c56 = pd.concat(l56); c56.to_csv(os.path.join(OUT, "step0_l56_clock.csv"), index=False)
    c60 = pd.concat(l60); c60.to_csv(os.path.join(OUT, "step0_l60_zero_range.csv"), index=False)
    hh1 = pd.concat(hw1); hh2 = pd.concat(hw2)
    pd.concat([hh1.assign(kind="last_before_halt").rename(columns={"last_hm": "hm"}),
               hh2.assign(kind="first_after_halt").rename(columns={"first_hm": "hm"})]
              ).to_csv(os.path.join(OUT, "step0_halt_bounds.csv"), index=False)

    print("\n=== L56 : profil intra-journalier hiver vs ete, par horloge ===")
    print(c56.to_string(index=False))
    print("\n=== Bornes REELLES de la pause (post-2021, modes) ===")
    print(hh1.to_string(index=False)); print(hh2.to_string(index=False))
    print("\n=== L60 : fourchette nulle aux bornes candidates (post-2021) ===")
    print(c60[c60["scope"].str.startswith("stamp")].to_string(index=False))
    print("\n=== L60 : fourchette nulle, toutes barres, >=2021 ===")
    print(c60[(c60["scope"] == "all_bars") & (c60["year"] >= 2021)].to_string(index=False))
    print("\n=== Couverture minute par minute 21:00-01:30 Paris ===")
    for sym in SYMS:
        for era in ("post-2021", "2021", "2023", "2025"):
            s = cv[(cv["sym"] == sym) & (cv["era"] == era)]
            if s.empty:
                continue
            line = " ".join(f"{r.hhmm}={r.cov_exact:.2f}" for r in s.itertuples()
                            if r.cov_exact < 0.995 or r.hhmm.endswith(":05"))
            print(f"[{sym} {era}] {line}")


if __name__ == "__main__":
    main()
