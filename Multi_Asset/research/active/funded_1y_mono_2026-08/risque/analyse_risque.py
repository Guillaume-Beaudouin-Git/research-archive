"""Analyse de RISQUE du compte FTMO funded — retraits, drawdowns, ruine.

Entree : out/paths_2ans.parquet (280 cohortes x 3 scenarios x 504 jours trades).
Aucune re-simulation : on ne fait que MESURER les trajectoires deja produites par
code/run_2ans_path.py (clone instrumente de engine_v22.run_funded).

Geometrie (rappel, mesuree ailleurs, non re-derivee ici) :
  INIT 10_000 | FLOOR statique 9_000 | barriere daily = solde d'ouverture - 500
  lim_eff = max(daily, statique) | retrait tous les 14 jours trades, solde -> 10_000
  split trader 0.8
=> le buffer ne grandit JAMAIS : pas de compounding, hasard de ruine constant.

Sorties : drawdowns.csv, payouts.csv, resume_risque.csv, + tables texte pour RAPPORT.md
"""
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("<HOME>/Desktop/Algo_claude/Multi_Asset/"
            "research/active/funded_1y_mono_2026-08")
OUT = BASE / "out"
R = BASE / "risque"
INIT, FLOOR, BUDGET, SPLIT, WD = 10_000.0, 9_000.0, 500.0, 0.8, 14
HORIZONS = [("3m", 63), ("6m", 126), ("1an", 252), ("2ans", 504)]
FEE_USD = 115.0          # fee FTMO 99 EUR, ~1.16 USD/EUR (CARTE_EV_2026-08-20.md:423)

# ---------------------------------------------------------------- chargement
P = pd.read_parquet(OUT / "paths_2ans.parquet").sort_values(
    ["scenario", "cohort", "jour"], kind="stable").reset_index(drop=True)

# la ligne de BUST est enregistree avec `days` NON incremente -> jour duplique.
# On la re-etiquette jour = life+1 : le bust survient PENDANT la journee suivante,
# journee qui ne se termine jamais.
dup = P.duplicated(["scenario", "cohort", "jour"], keep="first")
P.loc[dup, "jour"] += 1
P["bust_row"] = dup
assert not P.duplicated(["scenario", "cohort", "jour"]).any()

# jour 0 explicite : le compte demarre a 10 000 (necessaire pour dater les DD initiaux)
z = (P.groupby(["scenario", "cohort"], as_index=False).first()
     [["scenario", "cohort"]].assign(jour=0, bal=INIT, eq_min=INIT, cum_wd=0.0,
                                     equity_totale=INIT, bust_row=False))
P = pd.concat([P, z]).sort_values(["scenario", "cohort", "jour"],
                                  kind="stable").reset_index(drop=True)

SC = ["0.96_mesure", "ORB_OFF", "2.17_allin"]

# dates de depart des cohortes : meme grille V.starts(M, idx.min(), idx.max(), 10)
# que run_deploye.py, dont les cohortes 1an SONT enregistrees avec leur `start`.
_dep = pd.read_csv(OUT / "cohortes_deploye.csv.gz")
STARTS = (_dep[(_dep.horizon == "1an") & (_dep.scenario == "ORB_OFF")]
          .start.reset_index(drop=True))
print(f"[V] grille de departs : {len(STARTS)} dates, {STARTS.iloc[0]} -> "
      f"{STARTS.iloc[-1]} (pas = 10 jours trades)")
life = P[~P.bust_row].groupby(["scenario", "cohort"]).jour.max().rename("life")
busted = P.groupby(["scenario", "cohort"]).bust_row.any().rename("busted")
COH = pd.concat([life, busted], axis=1).reset_index()
print(f"[V] cohortes : {COH.groupby('scenario').size().to_dict()}")
print(f"[V] busts    : {COH.groupby('scenario').busted.sum().to_dict()}")

# ---------------------------------------------------------------- 1. RETRAITS
pay = P[P.cum_wd.diff().fillna(0) > 0].copy()
first = P.groupby(["scenario", "cohort"]).head(1).index
pay = pay[~pay.index.isin(first)]
pay["montant_usd"] = P.cum_wd.diff().loc[pay.index]
pay = pay[pay.montant_usd > 0]
pay["n_payout"] = pay.groupby(["scenario", "cohort"]).cumcount() + 1
pay["montant_net_trader"] = SPLIT * pay.montant_usd
PAY = pay[["scenario", "cohort", "n_payout", "jour", "montant_usd",
           "montant_net_trader"]].reset_index(drop=True)
PAY.to_csv(R / "payouts.csv", index=False)
print(f"[V] payouts.csv : {len(PAY)} lignes")

# --------------------------------------------------------------- 2. DRAWDOWNS
def episodes(jours, vals):
    """Episodes de drawdown : (debut=jour du plus-haut, trough, recovery)."""
    out = []
    peak, peak_j = vals[0], jours[0]
    t_i = None
    for k in range(1, len(vals)):
        v = vals[k]
        if v >= peak - 1e-9:
            if t_i is not None:
                out.append((peak_j, jours[t_i], vals[t_i], peak, jours[k], True))
                t_i = None
            peak, peak_j = v, jours[k]
        else:
            if t_i is None or v < vals[t_i]:
                t_i = k
    if t_i is not None:
        out.append((peak_j, jours[t_i], vals[t_i], peak, jours[-1], False))
    return out


rows = []
for (s, c), g in P.groupby(["scenario", "cohort"], sort=False):
    j = g.jour.to_numpy()
    for base, col in (("solde", "bal"), ("valeur_eco", "equity_totale")):
        v = g[col].to_numpy(float)
        for pj, tj, tv, pv, rj, rec in episodes(j, v):
            amp = pv - tv
            if amp < 0.50:                       # bruit sub-dollar : ignore
                continue
            rows.append((s, c, base, pj, tj, (rj - pj - 1) if rec else (j[-1] - pj),
                         amp, 100 * amp / pv, int(rec),
                         (rj - tj) if rec else np.nan))
DD = pd.DataFrame(rows, columns=["scenario", "cohort", "base", "debut_jour",
                                 "fin_jour", "duree_j", "amplitude_usd",
                                 "amplitude_pct", "recouvre", "jours_recouvrement"])
DD.to_csv(R / "drawdowns.csv", index=False)
print(f"[V] drawdowns.csv : {len(DD)} lignes "
      f"({DD.groupby('base').size().to_dict()})")

# ------------------------------------------------- 3. metriques par horizon
def q(x, p):
    return float(np.quantile(x, p)) if len(x) else np.nan


res = []
for s in SC:
    Ps = P[P.scenario == s]
    for lab, H in HORIZONS:
        sub = Ps[Ps.jour <= H]
        gg = sub.groupby("cohort")
        n = gg.ngroups
        bust = gg.bust_row.any()
        # valeur economique et cash a l'horizon (derniere obs <= H)
        last = sub.sort_values("jour").groupby("cohort").tail(1).set_index("cohort")
        eco = SPLIT * (last.equity_totale - INIT)
        cash = SPLIT * last.cum_wd
        npay = PAY[(PAY.scenario == s) & (PAY.jour <= H)].groupby("cohort").size()
        npay = npay.reindex(last.index).fillna(0)
        # temps sous plus-haut / sous 10k (jours trades effectifs)
        d = sub[sub.jour > 0]
        rmax = d.groupby("cohort").bal.cummax()
        f_high = (d.bal < rmax - 1e-9).groupby(d.cohort).mean()
        f_10k = (d.bal < INIT - 1e-9).groupby(d.cohort).mean()
        rmax_e = d.groupby("cohort").equity_totale.cummax()
        f_high_e = (d.equity_totale < rmax_e - 1e-9).groupby(d.cohort).mean()
        eqmin = d.groupby("cohort").eq_min.min()
        # pires DD dans l'horizon — recalcul sur la serie TRONQUEE (pas de fuite
        # d'un creux posterieur a H dans le chiffre de l'horizon H)
        w = {}
        for base, col in (("solde", "bal"), ("valeur_eco", "equity_totale")):
            ss = sub.sort_values("jour")
            cm = ss.groupby("cohort")[col].cummax()
            w[base] = (cm - ss[col]).groupby(ss.cohort).max().reindex(last.index)
        res.append(dict(
            scenario=s, horizon=lab, jours=H, n_cohortes=n,
            p_bust_pct=100 * bust.mean(),
            p_net_neg_pct=0.0,                       # impossible par construction
            p_net_inf_fee_pct=100 * (eco < FEE_USD).mean(),
            p_zero_payout_pct=100 * (npay == 0).mean(),
            payouts_med=npay.median(), payouts_p10=q(npay, .10),
            payouts_p90=q(npay, .90),
            net_eco_med=eco.median(), net_eco_p10=q(eco, .10),
            net_eco_p90=q(eco, .90),
            cash_retire_med=cash.median(),
            dd_solde_med=w["solde"].median(), dd_solde_p90=q(w["solde"], .90),
            dd_solde_p99=q(w["solde"], .99), dd_solde_max=w["solde"].max(),
            dd_eco_med=w["valeur_eco"].median(), dd_eco_p90=q(w["valeur_eco"], .90),
            dd_eco_p99=q(w["valeur_eco"], .99), dd_eco_max=w["valeur_eco"].max(),
            pct_temps_sous_plushaut_solde=100 * f_high.median(),
            pct_temps_sous_plushaut_eco=100 * f_high_e.median(),
            pct_temps_sous_10k=100 * f_10k.median(),
            eq_min_med=eqmin.median(), eq_min_p10=q(eqmin, .10),
            eq_min_p01=q(eqmin, .01), eq_min_min=eqmin.min(),
            buffer_conso_med_pct=100 * (INIT - eqmin.median()) / (INIT - FLOOR),
            buffer_conso_p90_pct=100 * (INIT - q(eqmin, .10)) / (INIT - FLOOR),
        ))
RES = pd.DataFrame(res)
RES.to_csv(R / "resume_risque.csv", index=False)
print(f"[V] resume_risque.csv : {len(RES)} lignes")

# ------------------------------------------------------------- 4. impressions
pd.set_option("display.width", 200, "display.max_columns", 60)

print("\n" + "=" * 100)
print("RETRAITS")
print("=" * 100)
for s in SC:
    p = PAY[PAY.scenario == s]
    l = COH[COH.scenario == s]
    n1 = p[p.jour <= 252].groupby("cohort").size().reindex(range(280)).fillna(0)
    n2 = p.groupby("cohort").size().reindex(range(280)).fillna(0)
    f = p[p.n_payout == 1].groupby("cohort").jour.min().reindex(range(280))
    itv = p.sort_values(["cohort", "jour"]).groupby("cohort").jour.diff().dropna()
    win = np.floor(l.set_index("cohort").life / WD)
    zero = 1 - (n2 / win).clip(upper=1)
    print(f"\n-- {s}")
    print(f"   n retraits 1an  : med {n1.median():.0f}  p10 {n1.quantile(.1):.0f} "
          f" p90 {n1.quantile(.9):.0f}  moy {n1.mean():.2f}  min {n1.min():.0f} max {n1.max():.0f}")
    print(f"   n retraits 2ans : med {n2.median():.0f}  p10 {n2.quantile(.1):.0f} "
          f" p90 {n2.quantile(.9):.0f}  moy {n2.mean():.2f}  min {n2.min():.0f} max {n2.max():.0f}")
    print(f"   montant BRUT/retrait : med ${p.montant_usd.median():.0f}  "
          f"p10 ${p.montant_usd.quantile(.1):.0f}  p25 ${p.montant_usd.quantile(.25):.0f} "
          f" p75 ${p.montant_usd.quantile(.75):.0f}  p90 ${p.montant_usd.quantile(.9):.0f} "
          f" max ${p.montant_usd.max():.0f}  (N={len(p)})")
    print(f"   montant NET trader   : med ${p.montant_net_trader.median():.0f}  "
          f"p90 ${p.montant_net_trader.quantile(.9):.0f}")
    print(f"   delai 1er retrait (jours trades) : med {f.median():.0f}  "
          f"p25 {f.quantile(.25):.0f}  p75 {f.quantile(.75):.0f}  p90 {f.quantile(.9):.0f} "
          f" max {f.max():.0f}  jamais: {int(f.isna().sum())}/280")
    print(f"   intervalle entre 2 retraits : med {itv.median():.0f}  p75 {itv.quantile(.75):.0f} "
          f" p90 {itv.quantile(.9):.0f}  max {itv.max():.0f}")
    print(f"   fenetres de 14j SANS retrait : {100*zero.mean():.1f} % "
          f"(med par cohorte {100*zero.median():.1f} %)")

print("\n" + "=" * 100)
print("DRAWDOWNS — distributions (toutes cohortes, 2 ans)")
print("=" * 100)
for base in ("solde", "valeur_eco"):
    print(f"\n### base = {base}")
    hdr = (f"{'scenario':<13}{'N_dd':>7}{'/an':>6}{'amp med':>9}{'p75':>7}{'p90':>7}"
           f"{'p99':>8}{'max':>8}{'amp% med':>10}{'p90%':>7}{'dur med':>9}{'p90':>6}"
           f"{'max':>6}{'rec med':>9}{'p90':>6}{'%non rec':>10}")
    print(hdr); print("-" * len(hdr))
    for s in SC:
        d = DD[(DD.scenario == s) & (DD.base == base)]
        nc = 280
        print(f"{s:<13}{len(d):>7}{len(d)/nc/2:>6.1f}{d.amplitude_usd.median():>9.0f}"
              f"{d.amplitude_usd.quantile(.75):>7.0f}{d.amplitude_usd.quantile(.9):>7.0f}"
              f"{d.amplitude_usd.quantile(.99):>8.0f}{d.amplitude_usd.max():>8.0f}"
              f"{d.amplitude_pct.median():>10.2f}{d.amplitude_pct.quantile(.9):>7.2f}"
              f"{d.duree_j.median():>9.0f}{d.duree_j.quantile(.9):>6.0f}{d.duree_j.max():>6.0f}"
              f"{d.jours_recouvrement.median():>9.0f}"
              f"{d.jours_recouvrement.quantile(.9):>6.0f}"
              f"{100*(1-d.recouvre.mean()):>9.1f}%")

print("\n--- PIRE drawdown par cohorte (max drawdown), par horizon [serie tronquee a H]")
hdr = (f"{'scenario':<13}{'base':<12}{'hor':<6}{'med':>8}{'p75':>8}{'p90':>8}{'p99':>8}"
       f"{'max':>8}{'med%':>7}{'p90%':>7}")
print(hdr); print("-" * len(hdr))
for s in SC:
    for base, col in (("solde", "bal"), ("valeur_eco", "equity_totale")):
        for lab, H in HORIZONS:
            ss = P[(P.scenario == s) & (P.jour <= H)].sort_values("jour")
            cm = ss.groupby("cohort")[col].cummax()
            x = (cm - ss[col]).groupby(ss.cohort).max()
            xp = (100 * (cm - ss[col]) / cm).groupby(ss.cohort).max()
            print(f"{s:<13}{base:<12}{lab:<6}{x.median():>8.0f}{x.quantile(.75):>8.0f}"
                  f"{x.quantile(.9):>8.0f}{x.quantile(.99):>8.0f}{x.max():>8.0f}"
                  f"{xp.median():>7.2f}{xp.quantile(.9):>7.2f}")

print("\n--- % du temps sous le plus-haut / sous 10 000 (mediane des cohortes, 2 ans)")
for s in SC:
    d = P[(P.scenario == s) & (P.jour > 0)]
    rm = d.groupby("cohort").bal.cummax()
    rme = d.groupby("cohort").equity_totale.cummax()
    a = (d.bal < rm - 1e-9).groupby(d.cohort).mean()
    b = (d.bal < INIT - 1e-9).groupby(d.cohort).mean()
    c = (d.equity_totale < rme - 1e-9).groupby(d.cohort).mean()
    e = (d.equity_totale < INIT - 1e-9).groupby(d.cohort).mean()
    print(f"  {s:<13} sous plus-haut SOLDE {100*a.median():5.1f}% "
          f"[p10 {100*a.quantile(.1):.0f} p90 {100*a.quantile(.9):.0f}] | "
          f"sous plus-haut ECO {100*c.median():5.1f}% | "
          f"solde<10k {100*b.median():5.1f}% | eco<10k {100*e.median():5.1f}%")

print("\n" + "=" * 100)
print("RUINE")
print("=" * 100)
print(f"{'scenario':<13}{'3m':>8}{'6m':>8}{'1an':>8}{'2ans':>8}   (P(bust) %, N=280)")
for s in SC:
    r = []
    for lab, H in HORIZONS:
        sub = P[(P.scenario == s) & (P.jour <= H)]
        r.append(100 * sub.groupby("cohort").bust_row.any().mean())
    print(f"{s:<13}" + "".join(f"{x:>8.2f}" for x in r))

print("\n--- anatomie des busts (N total = %d)" % int(COH.busted.sum()))
for (s, c) in COH[COH.busted][["scenario", "cohort"]].itertuples(index=False):
    g = P[(P.scenario == s) & (P.cohort == c)].sort_values("jour")
    b = g[g.bust_row].iloc[0]
    prev = g[~g.bust_row].iloc[-1]
    lim_daily = prev.bal - BUDGET
    kind = "daily" if lim_daily > FLOOR else "statique"
    st = STARTS.iloc[c] if c < len(STARTS) else "?"
    print(f"  {s:<13} coh {c:>3} (depart {st}) | bust jour {int(b.jour):>4}/504 | solde ouverture "
          f"{prev.bal:8.0f} | lim_eff {max(lim_daily, FLOOR):8.0f} ({kind}) | "
          f"eq au bust {b.bal:8.0f} | perte du jour {prev.bal - b.bal:7.0f} | "
          f"cash deja retire ${b.cum_wd:6.0f} | jours sous 9500 avant: "
          f"{int((g[~g.bust_row].bal < 9500).sum()):>3}")

print("\n--- equite MINIMALE atteinte (point le plus proche de la mort), 2 ans")
hdr = f"{'scenario':<13}{'med':>9}{'p25':>9}{'p10':>9}{'p05':>9}{'p01':>9}{'min':>9}{'buf med':>9}"
print(hdr); print("-" * len(hdr))
for s in SC:
    d = P[(P.scenario == s) & (P.jour > 0)].groupby("cohort").eq_min.min()
    print(f"{s:<13}{d.median():>9.0f}{d.quantile(.25):>9.0f}{d.quantile(.1):>9.0f}"
          f"{d.quantile(.05):>9.0f}{d.quantile(.01):>9.0f}{d.min():>9.0f}"
          f"{100*(INIT-d.median())/(INIT-FLOOR):>8.0f}%")
    for thr in (9750, 9500, 9250, 9100, 9050):
        print(f"      P(eq_min < {thr}) = {100*(d < thr).mean():5.1f}%", end="")
    print()

print("\n--- pire perte INTRADAY d'une seule journee (bal_open - eq_min du jour), "
      "hors journees de bust")
for s in SC:
    d = P[(P.scenario == s) & (P.jour > 0) & (~P.bust_row)].sort_values(
        ["cohort", "jour"]).copy()
    d["open"] = d.groupby("cohort").bal.shift(1).fillna(INIT)
    d["dip"] = d.open - d.eq_min
    d["daily_room"] = d.open - np.maximum(d.open - BUDGET, FLOOR)
    d["use"] = 100 * d.dip / d.daily_room
    print(f"  {s:<13} dip med ${d.dip.median():5.0f} p90 ${d.dip.quantile(.9):5.0f} "
          f"p99 ${d.dip.quantile(.99):5.0f} p999 ${d.dip.quantile(.999):5.0f} "
          f"max ${d.dip.max():5.0f} | % de la marge du jour consommee : med "
          f"{d.use.median():4.1f}% p99 {d.use.quantile(.99):5.1f}% max {d.use.max():5.1f}%")

print("\n" + "=" * 100)
print("SERIES OPERATIONNELLES — combien de temps l'ecran reste rouge")
print("=" * 100)


def streaks(mask):
    """longueurs des sequences consecutives de True."""
    out, run = [], 0
    for m in mask:
        if m:
            run += 1
        elif run:
            out.append(run); run = 0
    if run:
        out.append(run)
    return out


for s in SC:
    d = P[(P.scenario == s) & (P.jour > 0)]
    L, Le, prem = [], [], []
    for c, g in d.groupby("cohort"):
        g = g.sort_values("jour")
        a = streaks((g.bal < INIT - 1e-9).to_numpy())
        b = streaks((g.equity_totale < INIT - 1e-9).to_numpy())
        L.append(max(a) if a else 0)
        Le.append(max(b) if b else 0)
        pos = g[g.equity_totale > INIT + 1e-9]
        prem.append(pos.jour.iloc[0] if len(pos) else np.nan)
    L, Le, prem = np.array(L), np.array(Le), np.array(prem, float)
    print(f"  {s:<13} plus longue serie SOLDE<10k : med {np.median(L):.0f} j "
          f"p75 {np.quantile(L,.75):.0f}  p90 {np.quantile(L,.9):.0f}  max {L.max():.0f}")
    print(f"  {'':<13} plus longue serie VALEUR ECO<10k : med {np.median(Le):.0f} j "
          f"p90 {np.quantile(Le,.9):.0f}  max {Le.max():.0f}")
    pr = prem[~np.isnan(prem)]
    print(f"  {'':<13} 1er jour ou la valeur eco repasse >0 : med {np.median(pr):.0f} j "
          f"p75 {np.quantile(pr,.75):.0f}  p90 {np.quantile(pr,.9):.0f}  "
          f"jamais {int(np.isnan(prem).sum())}/280")

print("\n--- cash NET encaisse (cumul, part trader) par horizon")
hdr = f"{'scenario':<13}{'hor':<6}{'p10':>9}{'p25':>9}{'med':>9}{'p75':>9}{'p90':>9}{'moy':>9}"
print(hdr); print("-" * len(hdr))
for s in SC:
    for lab, H in HORIZONS:
        v = SPLIT * P[(P.scenario == s) & (P.jour == H)].cum_wd
        if not len(v):
            v = SPLIT * (P[(P.scenario == s) & (P.jour <= H)].sort_values("jour")
                         .groupby("cohort").tail(1).cum_wd)
        print(f"{s:<13}{lab:<6}{v.quantile(.1):>9.0f}{v.quantile(.25):>9.0f}"
              f"{v.median():>9.0f}{v.quantile(.75):>9.0f}{v.quantile(.9):>9.0f}{v.mean():>9.0f}")

# ------------------------------------------- eventail pour trace graphique
fan = []
for s in SC:
    d = P[(P.scenario == s) & (P.jour > 0)]
    for j, g in d.groupby("jour"):
        eco = SPLIT * (g.equity_totale - INIT)
        fan.append(dict(scenario=s, jour=j, n_vivantes=len(g),
                        **{f"eco_p{int(100*p):02d}": eco.quantile(p)
                           for p in (.05, .10, .25, .50, .75, .90, .95)},
                        **{f"bal_p{int(100*p):02d}": g.bal.quantile(p)
                           for p in (.05, .10, .25, .50, .75, .90, .95)},
                        cash_med=SPLIT * g.cum_wd.median(),
                        eq_min_p05=g.eq_min.quantile(.05),
                        eq_min_min=g.eq_min.min()))
pd.DataFrame(fan).to_csv(R / "trajectoires_quantiles.csv", index=False)
print(f"[V] trajectoires_quantiles.csv : {len(fan)} lignes (eventail par jour, pour trace)")

print("\n" + "=" * 100)
print("ALIGNEMENT CALENDAIRE — les cohortes se CHEVAUCHENT, quelle est la vraie taille "
      "d'echantillon ?")
print("=" * 100)
# grille : starts = dates_idx[10*c] ; la ligne jour=j de la cohorte c porte sur
# l'indice marche absolu a = 10*c + j - 1  (verifie : les 7 busts -> a = 809 = 2016-11-09)
DIDX = pd.to_datetime(pd.read_csv(R / "dates_idx.csv").date)
P["abs"] = 10 * P.cohort + P.jour - 1
P.loc[P.jour == 0, "abs"] = np.nan
span = int(P["abs"].max() - P["abs"].min() + 1)
print(f"[V] indice marche : {len(DIDX)} jours trades, {DIDX.iloc[0].date()} -> "
      f"{DIDX.iloc[-1].date()}")
print(f"[V] les 280 cohortes couvrent {span} jours trades = {span/252:.1f} ans "
      f"=> {span/504:.1f} fenetres de 2 ans INDEPENDANTES (et non 280)")
print(f"[V] deux cohortes voisines partagent {100*(504-10)/504:.1f} % de leurs jours")

for s in SC:
    d = P[(P.scenario == s) & (P.jour > 0)].sort_values(["cohort", "jour"]).copy()
    d["pnl"] = d.groupby("cohort").equity_totale.diff()
    d.loc[d.groupby("cohort").head(1).index, "pnl"] = d.equity_totale - INIT
    d["date"] = DIDX.to_numpy()[d["abs"].astype(int).to_numpy()]
    agg = d.groupby("date").pnl.agg(["mean", "median", "min", "size"])
    w = agg.sort_values("mean").head(6)
    print(f"\n-- {s} : 6 PIRES journees calendaires (P&L moyen sur les cohortes vivantes)")
    for dt, r in w.iterrows():
        print(f"   {dt.date()}  moy ${r['mean']:8.2f}  med ${r['median']:8.2f}  "
              f"pire ${r['min']:8.2f}  N cohortes {int(r['size']):>3}")
    bad = agg[agg["mean"] < -100]
    print(f"   journees a P&L moyen < -$100 : {len(bad)} sur {len(agg)} "
          f"({100*len(bad)/len(agg):.2f} %)")

print("\n--- la nuit qui tue : 2016-11-09 (soir d'election US)")
KEY = 809
for s in SC:
    d = P[(P.scenario == s) & (P.jour > 0)].sort_values(["cohort", "jour"]).copy()
    d["prev"] = d.groupby("cohort").bal.shift(1).fillna(INIT)
    k = d[d["abs"] == KEY]
    if not len(k):
        continue
    loss = k.prev - k.eq_min
    fatal = k.prev - loss  # equite au creux
    print(f"  {s:<13} N cohortes vivantes ce jour-la : {len(k):>3} | "
          f"perte intraday med ${loss.median():6.0f} p90 ${loss.quantile(.9):6.0f} "
          f"max ${loss.max():6.0f} | solde d'ouverture necessaire pour survivre : "
          f"> ${(FLOOR + loss).max():.0f} | cohortes mortes : {int(k.bust_row.sum())}")
    print(f"  {'':<13} solde d'ouverture ce jour : med ${k.prev.median():.0f} "
          f"p10 ${k.prev.quantile(.1):.0f} min ${k.prev.min():.0f} | "
          f"deja sous 9500 : {int((k.prev < 9500).sum())}/{len(k)}")

print("\n--- decomposition de P(bust) : exposition a la date fatale x mortalite conditionnelle")
for s in SC:
    d = P[P.scenario == s]
    cont = d[d["abs"] == KEY].cohort.nunique()
    dead = d[d.bust_row].cohort.nunique()
    print(f"  {s:<13} cohortes couvrant 2016-11-09 : {cont}/280 = {100*cont/280:.1f} % | "
          f"mortes {dead} => P(mort | exposee) = {100*dead/max(cont,1):.1f} % "
          f"=> produit {100*cont/280*dead/max(cont,1):.2f} %")

print("\n--- ou se trouve le solde d'ouverture (toutes cohortes x tous jours)")
for s in SC:
    d = P[(P.scenario == s) & (~P.bust_row) & (P.jour > 0)].sort_values(["cohort", "jour"])
    o = d.groupby("cohort").bal.shift(1).fillna(INIT)
    print(f"  {s:<13} med ${o.median():.0f} p25 ${o.quantile(.25):.0f} p10 ${o.quantile(.1):.0f} "
          f"p05 ${o.quantile(.05):.0f} p01 ${o.quantile(.01):.0f} min ${o.min():.0f} | "
          f"P(<9302 = seuil fatal 2016-11-09) {100*(o < 9302).mean():.2f} % des journees | "
          f"P(<9500) {100*(o < 9500).mean():.2f} %")

print("\n--- distribution du P&L QUOTIDIEN (valeur economique, brut avant split)")
for s in SC:
    d = P[(P.scenario == s) & (P.jour > 0)].sort_values(["cohort", "jour"]).copy()
    x = d.groupby("cohort").equity_totale.diff().dropna()
    print(f"  {s:<13} N={len(x)} moy ${x.mean():+.2f} med ${x.median():+.2f} sd ${x.std():.2f} | "
          f"p01 ${x.quantile(.01):.0f} p05 ${x.quantile(.05):.0f} p95 ${x.quantile(.95):.0f} "
          f"p99 ${x.quantile(.99):.0f} | min ${x.min():.0f} max ${x.max():.0f} | "
          f"skew {x.skew():.2f} kurt {x.kurtosis():.1f} | "
          f"jours + {100*(x > 0).mean():.1f}% / plats {100*(x.abs() < .01).mean():.1f}% / "
          f"- {100*(x < -.01).mean():.1f}%")

print("\n--- trajectoire mediane / p10 de la valeur economique nette (part trader)")
JAL = [21, 42, 63, 126, 189, 252, 378, 504]
print(f"{'scenario':<13}" + "".join(f"{'j'+str(j):>9}" for j in JAL))
for s in SC:
    row = []
    for j in JAL:
        v = SPLIT * (P[(P.scenario == s) & (P.jour == j)].equity_totale - INIT)
        row.append(v.median())
    print(f"{s:<13}" + "".join(f"{x:>9.0f}" for x in row))
print("  (p10)")
for s in SC:
    row = []
    for j in JAL:
        v = SPLIT * (P[(P.scenario == s) & (P.jour == j)].equity_totale - INIT)
        row.append(v.quantile(.10))
    print(f"{s:<13}" + "".join(f"{x:>9.0f}" for x in row))
print("  (p90)")
for s in SC:
    row = []
    for j in JAL:
        v = SPLIT * (P[(P.scenario == s) & (P.jour == j)].equity_totale - INIT)
        row.append(v.quantile(.90))
    print(f"{s:<13}" + "".join(f"{x:>9.0f}" for x in row))
