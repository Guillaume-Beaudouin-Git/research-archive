"""Analyses complémentaires : trajectoire $ funded, découpage temporel, test de
timing horaire (fenêtre ON vs 24h sur les MÊMES jours), bootstrap par blocs,
sous-échantillon GER40 sans trous. Écrit `analyse.txt` + `annuel.csv`.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

OUT = Path(__file__).resolve().parent
INIT = 10_000.0
W = 0.35
rng = np.random.default_rng(20260820)

d = pd.read_csv(OUT / "daily_raw.csv", index_col=0, parse_dates=True)
L = []
P = L.append


def hac_t(x, lags=6):
    fit = sm.OLS(np.asarray(x, float), np.ones(len(x))).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(fit.params[0]), float(fit.tvalues[0])


def block_boot(x, nb=5000, bl=21):
    x = np.asarray(x, float)
    n = len(x)
    k = int(np.ceil(n / bl))
    starts = rng.integers(0, n - bl, size=(nb, k))
    idx = (starts[:, :, None] + np.arange(bl)[None, None, :]).reshape(nb, -1)[:, :n]
    return np.percentile(x[idx].mean(axis=1), [2.5, 97.5])


# ------------------------------------------------------- 1. trajectoire funded
P("=" * 78)
P("1. TRAJECTOIRE $ SUR UN COMPTE FUNDED ($10 000, plancher STATIQUE $9 000,")
P("   perte quotidienne max 5% = $500). Sizing en % d'equite, gains RETIRES")
P("   => trajectoire ARITHMETIQUE (le buffer ne grandit jamais, cf. MEMORY).")
P("=" * 78)
for name in ("on_us100", "on_ger40", "orb", "portefeuille"):
    eq = INIT + INIT * d[name].cumsum()
    dd = eq - eq.cummax()
    worst_day = d[name].min() * INIT
    n_breach_daily = int((d[name] * INIT < -500).sum())
    P(f"{name:14s} eq_min=${eq.min():9.2f}  eq_fin=${eq.iloc[-1]:9.2f}  "
      f"DD_max=${dd.min():8.2f} ({dd.min()/INIT*100:6.2f}%)  "
      f"pire_jour=${worst_day:7.2f}  jours<-5%: {n_breach_daily}")
P("")
P("Note : la trajectoire ci-dessus IGNORE le breaker M5 et le plancher (elle")
P("mesure le signal, pas le compte). Un compte funded reel serait TERMINE a la")
P("premiere touche de $9 000.")
eqp = INIT + INIT * d["portefeuille"].cumsum()
below = eqp < 9000
P(f"portefeuille : seances sous $9 000 = {int(below.sum())} / {len(d)} ; "
  f"premiere le {d.index[below][0].date() if below.any() else 'jamais'}")

# ------------------------------------------------------- 2. decoupage annuel
P("")
P("=" * 78)
P("2. DECOUPAGE ANNUEL (rendement en % d'equite, somme arithmetique)")
P("=" * 78)
ann = d.groupby(d.index.year)[["on_us100", "on_ger40", "orb", "portefeuille",
                               "bh_us100", "bh_ger40"]].sum() * 100
ann["N_on"] = d.groupby(d.index.year)["is_on_day"].sum()
ann["N_ger40"] = d.groupby(d.index.year)["on_ger40_live"].sum()
ann.round(2).to_csv(OUT / "annuel.csv")
P(ann.round(2).to_string())
P("")
P("Stabilite : moyenne mensuelle du portefeuille par sous-periode")
for a, b in (("2013", "2017"), ("2018", "2021"), ("2022", "2026")):
    s = d.loc[a:b, "portefeuille"]
    mu, t = hac_t(s)
    P(f"  {a}-{b}: {mu*INIT*21:7.2f} $/mois  t_HAC6(journalier)={t:5.2f}  N={len(s)}")

# ------------------------------------------- 3. test de timing : fenetre vs 24h
P("")
P("=" * 78)
P("3. TEST DE TIMING (le coeur de la question beta-vs-alpha)")
P("   Sur les MEMES jours ON, comparer la fenetre tenue au buy-and-hold 24h")
P("   couvrant le meme intervalle, AU MEME NOTIONNEL. Prix bruts, sans cout :")
P("   si la fenetre ne bat pas le 24h, il n'y a pas de timing, juste moins de beta.")
P("=" * 78)
m5 = pd.read_parquet("<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/"
                     "cache/sim_m5_repaired.parquet")[["US100", "GER40"]].ffill()
last = m5.groupby(m5.index.date).last()
last.index = pd.to_datetime(last.index)
last = last.reindex(d.index)
nxt24 = last.shift(-1) / last - 1.0
for sym, tag in (("US100", "us100"), ("GER40", "ger40")):
    live = d[f"on_{tag}_live"] == 1
    win = d.loc[live, f"on_{tag}_px_ret"]
    full = nxt24.loc[live, sym]
    ok = win.notna() & full.notna()
    win, full = win[ok], full[ok]
    mw, tw = hac_t(win)
    mf, tf = hac_t(full)
    diff = win - full
    md, td = hac_t(diff)
    P(f"{sym}: N={len(win)}")
    P(f"   fenetre tenue      {mw*1e4:7.2f} bps/jour-ON  t_HAC6={tw:5.2f}  "
      f"vol={win.std()*1e4:7.1f} bps")
    P(f"   24h meme intervalle{mf*1e4:7.2f} bps/jour-ON  t_HAC6={tf:5.2f}  "
      f"vol={full.std()*1e4:7.1f} bps")
    P(f"   DIFFERENCE         {md*1e4:7.2f} bps          t_HAC6={td:5.2f}   "
      f"=> {'la fenetre AJOUTE' if td > 2 else 'PAS de timing significatif'}")
    P(f"   part de la variance 24h captee par la fenetre : "
      f"{win.var()/full.var()*100:5.1f}%  ; corr(fenetre,24h)={win.corr(full):.3f}")

# --------------------------------------------- 4. bootstrap par blocs
P("")
P("=" * 78)
P("4. BOOTSTRAP PAR BLOCS (blocs de 21 seances, 5 000 tirages) — IC95 sur la")
P("   moyenne journaliere, convertie en $/mois. Jamais d'iid (clusters de trades).")
P("=" * 78)
for name in ("on_us100", "on_ger40", "orb", "portefeuille"):
    for lab, s in (("vie", d[name]), ("2ans", d.loc["2024-06":"2026-05", name])):
        lo, hi = block_boot(s.to_numpy())
        mu, t = hac_t(s.to_numpy())
        P(f"{name:14s} {lab:5s} moy={mu*INIT*21:8.2f} $/mois  "
          f"IC95=[{lo*INIT*21:8.2f}, {hi*INIT*21:8.2f}]  t_HAC6={t:5.2f}  "
          f"{'contient zero' if lo <= 0 <= hi else 'exclut zero'}")

# --------------------------------------------- 5. GER40 hors trous
P("")
P("=" * 78)
P("5. GER40 : sous-echantillon SANS les trous de donnees 2018-2021")
P("=" * 78)
onl = d.is_on_day == 1
miss = onl & (d.on_ger40_live == 0)
P(f"jours ON total={int(onl.sum())} ; sans jambe GER40={int(miss.sum())} "
  f"({miss.sum()/onl.sum()*100:.1f}%)")
P("  par annee : " + str(d.loc[miss].groupby(d.loc[miss].index.year).size().to_dict()))
sub = d.loc[(d.index < "2018-01-01") | (d.index >= "2022-01-01")]
mu, t = hac_t(sub["on_ger40"])
lo, hi = block_boot(sub["on_ger40"].to_numpy())
P(f"on_ger40 hors 2018-2021 : {mu*INIT*21:7.2f} $/mois  t_HAC6={t:5.2f}  "
  f"IC95=[{lo*INIT*21:.2f}, {hi*INIT*21:.2f}]  N={len(sub)}")
mu2, t2 = hac_t(d["on_ger40"])
P(f"on_ger40 tout l'echantillon : {mu2*INIT*21:7.2f} $/mois  t_HAC6={t2:5.2f}")

# --------------------------------------------- 6. sensibilite aux couts
P("")
P("=" * 78)
P("6. SENSIBILITE AU COUT (le gate qui a tue toutes les familles precedentes)")
P("=" * 78)
for tag, sym in (("us100", "US100"), ("ger40", "GER40")):
    g = d[f"on_{tag}_gross"].sum()
    live = d[f"on_{tag}_live"].sum()
    gpt = g / live * 1e4 / W        # gross par trade, en bps de NOTIONNEL
    P(f"on_{tag}: gross/trade = {gpt:6.2f} bps de notionnel ; "
      f"cout RT mesure = {1.045 if tag=='us100' else 1.017:.3f} bps ; "
      f"swap/nuit = {abs(d[f'on_{tag}_swap_panel'].sum())/live*1e4/W:.3f} bps")
    tot = (1.045 if tag == "us100" else 1.017) + abs(d[f"on_{tag}_swap_panel"].sum()) / live * 1e4 / W
    P(f"   ratio gross/cout_total = {gpt/tot:5.2f}  "
      f"(gate L11b : > 3 requis ; gate pre-vol L43 : > 1.5)")
    # point mort
    P(f"   cout total qui annule l'edge : {gpt:.2f} bps/trade "
      f"(actuel {tot:.2f}, marge x{gpt/tot:.2f})")
g = d["orb"].sum() / d["orb_live"].sum() * 1e4
P(f"orb   : net/trade = {g:.2f} bps d'equite (ledger deja coste, era)")

(OUT / "analyse.txt").write_text("\n".join(L))
print("\n".join(L))
