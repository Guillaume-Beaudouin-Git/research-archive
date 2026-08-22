"""VOLET D — agrégation, bootstrap par blocs, frontière de Pareto, IS vs OOS.

Critère de classement PRIMAIRE (cf. cahier des charges) : en funded le buffer ne
grandit jamais (retrait -> balance = 10 000 tous les 14 jours tradés, plancher
statique 9 000, plancher daily = balance - 500). Le hasard de ruine par période
est donc constant et ce qu'on maximise est

    V_inf = 0.8 x mu_periode / h_ruine_periode        [$ , horizon-libre]

et non le Sharpe ni un taux de croissance. EV504 (= 0.8 x E[wd + residual] sur
l'horizon 504 j) est rapportée en parallèle : elle est TRONQUÉE par l'horizon et
sous-estime d'autant plus les vm survivants.

Incertitude : bootstrap par BLOCS circulaires. Les cohortes sont espacées de 12
jours tradés et durent jusqu'à 504 -> 42 cohortes consécutives partagent des
données. Bloc B=42 (chevauchement apparié) en primaire, B=12 en secondaire.
iid interdit.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
WD_EVERY = 14
SPLIT = 0.8
B_PRIM, B_SEC, NB = 42, 12, 4000
rng = np.random.default_rng(2026)

d = pd.read_csv(OUT / "funded_cohorts.csv.gz")
d["start"] = pd.to_datetime(d["start"])
d = d.sort_values(["cost", "vm", "win", "start"]).reset_index(drop=True)
d["extr"] = d["wd"] + d["residual"]
d["exposure"] = d["life"] / WD_EVERY


# ------------------------------------------------------------------ stats
def cell_stats(g):
    expo = g.exposure.sum()
    nb_bust = int(g.busted.sum())
    h = nb_bust / expo if expo > 0 else np.nan
    mu = g.wd.sum() / expo if expo > 0 else np.nan
    vinf = SPLIT * mu / h if h > 0 else np.inf
    bk = g.loc[g.busted, "bust_kind"]
    return dict(
        n=len(g),
        bust=g.busted.mean(),
        ev504=SPLIT * g.extr.mean(),
        payouts=g.payouts.mean(),
        life_med=g.life.median(),
        life_mean=g.life.mean(),
        h_period=h,
        mu_period=mu,
        v_inf=vinf,
        n_bust=nb_bust,
        bust_daily_share=(bk == "daily").mean() if len(bk) else np.nan,
        dayloss_med=g.loc[g.busted, "bust_dayloss"].median(),
        wd_mean=g.wd.mean(),
        resid_mean=g.residual.mean(),
    )


def blocks(n, B, nb, rg):
    """Indices de bootstrap par blocs circulaires : (nb, n)."""
    k = int(np.ceil(n / B))
    st = rg.integers(0, n, size=(nb, k))
    off = np.arange(B)
    ix = (st[:, :, None] + off[None, None, :]).reshape(nb, k * B) % n
    return ix[:, :n]


def boot_stat(g, ix, fn):
    arr = {c: g[c].to_numpy(float) for c in
           ("busted", "extr", "wd", "exposure")}
    return np.array([fn({c: v[row] for c, v in arr.items()}) for row in ix])


def f_bust(a):
    return a["busted"].mean()


def f_ev(a):
    return SPLIT * a["extr"].mean()


def f_vinf(a):
    expo = a["exposure"].sum()
    nb_ = a["busted"].sum()
    if nb_ == 0 or expo == 0:
        return np.nan
    return SPLIT * (a["wd"].sum() / expo) / (nb_ / expo)


def neff(y):
    y = np.asarray(y, float)
    if y.std() == 0:
        return float(len(y))
    ac = [pd.Series(y).autocorr(k) for k in range(1, 60)]
    s = sum(max(a, 0) for a in ac if np.isfinite(a))
    return len(y) / (1 + 2 * s)


# ------------------------------------------------- table principale 2-D
rows = []
for (cost, vm, win), g in d.groupby(["cost", "vm", "win"], sort=False):
    g = g.sort_values("start")
    s = cell_stats(g)
    ix = blocks(len(g), B_PRIM, NB, np.random.default_rng(abs(hash((cost, win))) % 2**31))
    bb = boot_stat(g, ix, f_bust)
    be = boot_stat(g, ix, f_ev)
    bv = boot_stat(g, ix, f_vinf)
    s.update(cost=cost, vm=vm, win=win,
             bust_lo=np.percentile(bb, 2.5), bust_hi=np.percentile(bb, 97.5),
             ev504_lo=np.percentile(be, 2.5), ev504_hi=np.percentile(be, 97.5),
             vinf_lo=np.nanpercentile(bv, 2.5), vinf_hi=np.nanpercentile(bv, 97.5),
             n_eff=neff(g.busted.to_numpy(float)))
    rows.append(s)

# pooled = IS et OOS empilées (moyenne non pondérée des 2 fenêtres pour l'EV,
# pooling par exposition pour le hasard)
for (cost, vm), g in d.groupby(["cost", "vm"], sort=False):
    s = cell_stats(g.sort_values("start"))
    s.update(cost=cost, vm=vm, win="POOL", bust_lo=np.nan, bust_hi=np.nan,
             ev504_lo=np.nan, ev504_hi=np.nan, vinf_lo=np.nan, vinf_hi=np.nan,
             n_eff=np.nan)
    rows.append(s)

G = pd.DataFrame(rows)
cols = ["cost", "vm", "win", "n", "n_eff", "bust", "bust_lo", "bust_hi",
        "ev504", "ev504_lo", "ev504_hi", "payouts", "life_med", "life_mean",
        "h_period", "mu_period", "v_inf", "vinf_lo", "vinf_hi", "n_bust",
        "bust_daily_share", "dayloss_med", "wd_mean", "resid_mean"]
G = G[cols].sort_values(["cost", "win", "vm"])
G.to_csv(OUT / "vm_orb_grid.csv", index=False)
print(f"grille: {len(G)} lignes -> out/vm_orb_grid.csv")

# --------------------------------------------- deltas appariés vs vm 1.00
pr = []
for (cost, win), g in d.groupby(["cost", "win"], sort=False):
    piv = {vm: gg.sort_values("start") for vm, gg in g.groupby("vm")}
    n = len(piv[1.00])
    ix = blocks(n, B_PRIM, NB, np.random.default_rng(abs(hash((cost, win, "p"))) % 2**31))
    base = piv[1.00]
    for vm, gg in piv.items():
        if vm == 1.00:
            continue
        assert (gg.start.to_numpy() == base.start.to_numpy()).all()
        db = boot_stat(gg, ix, f_bust) - boot_stat(base, ix, f_bust)
        de = boot_stat(gg, ix, f_ev) - boot_stat(base, ix, f_ev)
        dv = boot_stat(gg, ix, f_vinf) - boot_stat(base, ix, f_vinf)
        pr.append(dict(cost=cost, win=win, vm=vm, n=n,
                       d_bust=gg.busted.mean() - base.busted.mean(),
                       d_bust_lo=np.percentile(db, 2.5),
                       d_bust_hi=np.percentile(db, 97.5),
                       d_ev=SPLIT * (gg.extr.mean() - base.extr.mean()),
                       d_ev_lo=np.percentile(de, 2.5),
                       d_ev_hi=np.percentile(de, 97.5),
                       d_vinf=cell_stats(gg)["v_inf"] - cell_stats(base)["v_inf"],
                       d_vinf_lo=np.nanpercentile(dv, 2.5),
                       d_vinf_hi=np.nanpercentile(dv, 97.5)))
P = pd.DataFrame(pr).sort_values(["cost", "win", "vm"])
P.to_csv(OUT / "paired_vs_vm100.csv", index=False)
print("deltas appariés -> out/paired_vs_vm100.csv")

# ------------------------------------------------------- frontière Pareto
par = []
for (cost, win), g in G[G.win != "POOL"].groupby(["cost", "win"]):
    for _, r in g.iterrows():
        dom = ((g.bust <= r.bust) & (g.ev504 >= r.ev504)
               & ((g.bust < r.bust) | (g.ev504 > r.ev504))).any()
        par.append(dict(cost=cost, win=win, vm=r.vm, bust=r.bust,
                        ev504=r.ev504, v_inf=r.v_inf, pareto=not dom))
pd.DataFrame(par).to_csv(OUT / "pareto.csv", index=False)

# ------------------------------------------------------- anatomie des busts
b = d[d.busted].copy()
an = b.groupby(["cost", "vm", "win"]).agg(
    n_bust=("busted", "size"),
    daily=("bust_kind", lambda x: (x == "daily").sum()),
    floor=("bust_kind", lambda x: (x == "floor").sum()),
    dayloss_p25=("bust_dayloss", lambda x: np.percentile(x, 25)),
    dayloss_med=("bust_dayloss", "median"),
    dayloss_p75=("bust_dayloss", lambda x: np.percentile(x, 75)),
    dayloss_max=("bust_dayloss", "max"),
    life_med=("life", "median")).reset_index()
an.to_csv(OUT / "bust_anatomy.csv", index=False)

# ------------------- conversion appariée des busts vm1.00 -> vm' (mécanisme)
cv = []
for (cost, win), g in d.groupby(["cost", "win"], sort=False):
    piv = {vm: gg.sort_values("start").reset_index(drop=True)
           for vm, gg in g.groupby("vm")}
    base = piv[1.00]
    bb = base.busted.to_numpy(bool)
    for vm, gg in piv.items():
        if vm == 1.00:
            continue
        v = gg.busted.to_numpy(bool)
        cv.append(dict(cost=cost, win=win, vm=vm,
                       n=len(base), n_bust_base=int(bb.sum()),
                       saved=int((bb & ~v).sum()), new_bust=int((~bb & v).sum()),
                       n_bust_vm=int(v.sum()),
                       dayloss_med_base=base.loc[bb, "bust_dayloss"].median(),
                       dayloss_med_vm=gg.loc[v, "bust_dayloss"].median()))
pd.DataFrame(cv).to_csv(OUT / "bust_conversion.csv", index=False)

print("\n=== vm x cost : bust (%) / EV504 ($) / V_inf ($), par fenêtre ===")
for win in ("IS", "OOS"):
    for metric, fmt in (("bust", lambda v: f"{v*100:5.1f}"),
                        ("ev504", lambda v: f"{v:6.0f}"),
                        ("v_inf", lambda v: f"{v:7.0f}")):
        t = G[G.win == win].pivot(index="vm", columns="cost", values=metric)
        t = t[[c for c in ("era", "1.0", "1.8", "2.2", "3.0", "OFF") if c in t]]
        print(f"\n-- {win} {metric} --")
        print(t.applymap(fmt).to_string())
