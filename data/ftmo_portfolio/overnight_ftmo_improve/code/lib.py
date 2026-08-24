"""Shared helpers for pistes 1-3. Reuses overnight_series internals + basket_inject (funded
ablation on canonical FUNDED_WINDOWS) + basket_fp (challenge). Builds custom per-piste daily
(net, low) series: overlay-gated gold (P1), silver-gold spread (P2), early-exit (P3)."""
import sys, glob, importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import overnight_series as OS
import basket_series as BS
import basket_inject as BI
import basket_fp as FP
V, C22, E = BI.V, BI.C22, BI.E
REPO = "<HOME>/Desktop/Algo_claude"
ANN = 252.0
SYM = {"GOLD": "XAUUSD", "SILVER": "XAGUSD", "WTI": "USOIL", "SOYBEAN": "SOYBEAN"}


def _paths(name, hours, which):
    """Per-aday hourly path from entry: which in {low, high, close}. low/high = running within-bar
    extreme; close = hourly-close cumret. Returns DataFrame columns p_<h>."""
    s = OS.SPECS[name]
    h1 = OS._load_h1(s["sym"])
    lr = np.log(h1["close"] / h1["close"].shift(1))
    gap = np.log(h1[{"low": "low", "high": "high", "close": "close"}[which]] / h1["close"])
    aday = (h1.index - pd.Timedelta(hours=s["anchor"])).normalize()
    df = pd.DataFrame({"lr": lr, "gap": gap, "aday": aday, "hour": h1.index.hour}).dropna()
    if s["lo"]:
        df = df[df.index >= pd.Timestamp(s["lo"])]
    df = df[df["hour"].isin(hours)].sort_index()
    df["cum"] = df.groupby("aday")["lr"].cumsum()
    df["path"] = df["cum"] + (0.0 if which == "close" else df["gap"])
    agg = {"low": "min", "high": "max", "close": "last"}[which]
    p = df.pivot_table(index="aday", columns="hour", values="path", aggfunc=agg)
    return p.reindex(columns=OS.GRID).rename(columns={h: f"p_{h}" for h in OS.GRID})


def sleeve(name, hours=None, spread_bps=2.0):
    """Single-sleeve daily (pos, win_w, net, low) indexed by EXIT-morning book date.
    hours=None -> full window; custom hours -> early-exit variant (recomputes VT+low)."""
    s = OS.SPECS[name]
    hours = s["hours"] if hours is None else hours
    piv = OS._hourly_pivot(s["sym"], s["anchor"])
    if s["lo"]:
        piv = piv.loc[s["lo"]:]
    win_w = OS._wins(OS._win_ret(piv, hours))
    pos = OS._vt(win_w)
    sp = spread_bps * 1e-4
    net = pos * (np.exp(win_w) - 1.0) - pos.abs() * sp
    lp = _paths(name, hours, "low")
    cols = [f"p_{h}" for h in hours]
    lp = lp[[c for c in cols if c in lp.columns]].reindex(win_w.index)
    posa = pos.reindex(lp.index)
    dip = (np.exp(lp) - 1.0).mul(posa, axis=0)
    low = dip.min(axis=1) - posa.abs() * (sp / 2.0)
    out = pd.DataFrame({"pos": pos, "win_w": win_w, "net": net, "low": low}).dropna(subset=["pos", "net"])
    out = out[out["pos"] > 0]
    out["low"] = np.minimum(out["low"], out["net"])
    if s["shift"]:
        out.index = out.index + pd.Timedelta(days=1)
    return out.groupby(out.index.normalize()).last()


def dxy_gate(book_index):
    """Causal regime gate from FRED DTWEXBGS: 1.0 if 63-obs USD momentum <= 0 (USD not appreciating),
    else 0.0; shift(1); ffill; default 1.0 (trade-on) where unknown (pre-2010)."""
    f = sorted(glob.glob(f"{REPO}/data/raw/fred_*DTWEXBGS*.parquet"))[0]
    s = pd.read_parquet(f)["dtwexbgs"].dropna()
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    mom = s - s.shift(63)
    gate = (mom <= 0).astype(float).shift(1)             # causal: trade only if USD not appreciating
    bi = pd.to_datetime(pd.Index(book_index)).normalize()
    g = gate.reindex(gate.index.union(bi)).sort_index().ffill().reindex(bi)
    return g.fillna(1.0).to_numpy()


def spread(beta, spread_bps=2.0):
    """Silver-long - beta*gold-short. Built on the ADAY grid then shifted to book date.
    net = pos_s*ret_s - beta*pos_g*ret_g - (pos_s+beta*pos_g)*sp (each leg pays spread on its notional).
    low = worst combined per-hour CLOSE MtM (silver dip - beta*gold dip; short gold worst when gold up)."""
    sp = spread_bps * 1e-4

    def leg(name):
        s = OS.SPECS[name]
        piv = OS._hourly_pivot(s["sym"], s["anchor"])
        if s["lo"]:
            piv = piv.loc[s["lo"]:]
        win = OS._wins(OS._win_ret(piv, s["hours"]))
        pos = OS._vt(win)
        cp = _paths(name, s["hours"], "close")           # aday x hour close-cumret
        return win, pos, cp
    ws, ps, scp = leg("SILVER")
    wg, pg, gcp = leg("GOLD")
    idx = ps.index.union(pg.index)
    ps = ps.reindex(idx).fillna(0.0); pg = pg.reindex(idx).fillna(0.0)
    ws = ws.reindex(idx).fillna(0.0); wg = wg.reindex(idx).fillna(0.0)
    net = ps * (np.exp(ws) - 1.0) - beta * pg * (np.exp(wg) - 1.0) - (ps + beta * pg) * sp
    sdip = (np.exp(scp.reindex(idx)) - 1.0).mul(ps, axis=0)
    gdip = (np.exp(gcp.reindex(idx)) - 1.0).mul(pg, axis=0)
    comb = sdip - beta * gdip                            # per-hour combined MtM
    low = comb.min(axis=1) - (ps + beta * pg) * (sp / 2.0)
    out = pd.DataFrame({"net": net, "low": np.minimum(low, net)})
    out = out[(ps > 0) | (pg > 0)].dropna()
    out.index = out.index + pd.Timedelta(days=1)         # both gold/silver shift to exit-morning
    return out.groupby(out.index.normalize()).last()


# ---------------- funded ablation (canonical FUNDED_WINDOWS) + challenge ----------------
_M = None
def stack():
    global _M
    if _M is None:
        _M = BI.load_basket_stack()
    return _M


def fstarts():
    M = stack()
    return np.concatenate([V.starts(M, lo, hi, C22.FUNDED_STEP) for _, lo, hi in C22.FUNDED_WINDOWS])


def book_only_survive():
    M = stack(); WT, ON = E.align_signals(M, *E.build_signals())
    BI.set_basket(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
    cfg = dict(C22.CFG_FUNDED, basket_on=False)
    lives = [V.run_funded(M, int(i0), WT, ON, cfg, horizon=C22.FUNDED_HORIZON,
                          wd_every=C22.FUNDED_WD_EVERY)["life"] for i0 in fstarts()]
    return float((np.array(lives) >= 252).mean())


def funded_with(net_book, low_book, K=1.0):
    """book + sleeve survive252 on canonical FUNDED_WINDOWS; net_book/low_book aligned to M dates."""
    M = stack(); WT, ON = E.align_signals(M, *E.build_signals())
    BI.set_basket(M, K * net_book, K * low_book, (net_book != 0).astype(float))
    cfg = dict(C22.CFG_FUNDED, basket_on=True, basket_lev=1.0)
    out = [V.run_funded(M, int(i0), WT, ON, cfg, horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
           for i0 in fstarts()]
    lives = np.array([r["life"] for r in out])
    wd = np.array([0.0 if r["busted"] else 0.8 * (r["wd"] + r["residual"]) for r in out])
    BI.set_basket(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
    return float((lives >= 252).mean()), float(wd.mean()) + 96.0


def align(series):
    return BS.align_to_book(series, stack()["dates_idx"])


def challenge(net_series, low_series, K=1.0):
    M = stack()
    net = align(net_series) * K; low = align(low_series) * K
    traded = (net != 0)
    dates = M["dates_idx"]
    starts = np.concatenate([V.starts(M, lo, hi, C22.COHORT_STEP) for _, lo, hi in C22.WINDOWS])
    r = FP.cohort_run(net, low, traded, dates, starts, wall=C22.WALL)
    return r


def sharpe(x):
    x = np.asarray(x, float); x = x[x != 0]
    return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else float("nan")


def maxdd(net_series):
    eq = (1 + net_series).cumprod().to_numpy()
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def dsr(net_series, n_trials=160):
    from scipy.stats import skew, kurtosis, norm
    r = np.asarray(net_series, float); r = r[r != 0]; T = len(r)
    if T < 20 or r.std() == 0:
        return float("nan")
    sr = r.mean() / r.std()
    g3, g4 = float(skew(r)), float(kurtosis(r, fisher=False))
    em = 0.5772156649
    sr0 = (1 / np.sqrt(T)) * ((1 - em) * norm.ppf(1 - 1.0 / n_trials) + em * norm.ppf(1 - 1.0 / (n_trials * np.e)))
    den = 1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2
    return float(norm.cdf((sr - sr0) * np.sqrt(T - 1) / np.sqrt(den))) if den > 0 else float("nan")
