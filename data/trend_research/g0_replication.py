"""
G0 — Réplication indépendante hors-pipeline.

Objectif : reproduire J1 ~0.58 / G1 ~0.66 / book ~0.70 / corr ~0.02 sans réutiliser
le code de data/ftmo_research/code/trend_replication.py. Si la structure se
reproduit avec une implémentation différente, l'edge n'est PAS un artefact de
pipeline. Si non, le rapport tombe.

Diffs intentionnels d'implémentation par rapport au script original :
- TSMOM via log-rendement cumulé 12 mois - 1 mois (pas via ratio P[t-22]/P[t-252]).
- Vol-target via rolling std des log-rendements, fenêtre 21 j (~1 mois).
- Carry-filter : sign(US 13w - 0) avant 2024-03, sign(US-BoJ) après. Décalé t-1
  (et pas t-2 comme l'orig — on testera la sensibilité au choix de lag).
- Re-fetch Yahoo par yfinance (alternative à l'urllib direct).

Méthodo (charte) : signal à t-1, trade à t ; bootstrap CI ; pas de tuning.
"""
from __future__ import annotations
import io
import json
import urllib.request
from typing import Optional, Tuple

import numpy as np
import pandas as pd

ANN_SQRT = np.sqrt(252)
SEED = 7


# --------------- DATA -----------------------------------------------------

def yahoo_close(ticker: str) -> pd.Series:
    """Téléchargement Yahoo Finance direct (alt à yfinance hang). 2000-01-01 → today."""
    p1, p2 = 946684800, 1780272000
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    j = json.load(urllib.request.urlopen(req, timeout=20))["chart"]["result"][0]
    s = pd.Series(j["indicators"]["quote"][0]["close"],
                  index=pd.to_datetime(j["timestamp"], unit="s").normalize())
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")]
    return s.sort_index()


def declitch(s: pd.Series, thresh: float = 0.05) -> pd.Series:
    """Tick aberrant : |ret|>thresh suivi d'un renversement net. Interpolation log."""
    r = s.pct_change()
    bad = (r.abs() > thresh) & ((r + r.shift(-1)).abs() < thresh / 2)
    out = s.copy()
    out[bad] = np.nan
    n_bad = int(bad.sum())
    return np.exp(np.log(out).interpolate()), n_bad


# --------------- SIGNAL ---------------------------------------------------

def tsmom_12_1(close: pd.Series) -> pd.Series:
    """
    TSMOM 12-1 (Moskowitz 2012) via log-return cumulé sur la fenêtre [t-252, t-22].
    Définition canonique : signe du momentum 12 mois en excluant le dernier mois.
    Décalage : à t, on connaît log(P[t-22]) - log(P[t-252]) -> signal connu pour
    décision tr[t+1]. On laggera explicitement dans backtest.
    """
    lr = np.log(close)
    mom_12_1 = lr.shift(22) - lr.shift(252)  # log(P[t-22]) - log(P[t-252])
    return np.sign(mom_12_1)


def vol_target_position(close: pd.Series, sig: pd.Series,
                        target_vol: float = 0.10, window: int = 21,
                        leverage_cap: float = 3.0) -> pd.Series:
    """
    pos[t] = sign × clip(target / rv[t-1], cap). rv connue à t-1.
    Implémentation différente : rolling std des LOG returns (vs simple returns du script orig).
    """
    log_r = np.log(close).diff()
    rv = log_r.rolling(window).std().shift(1) * ANN_SQRT  # vol laggée
    raw = (target_vol / rv).clip(upper=leverage_cap)
    return (raw * sig).fillna(0.0)


# --------------- BACKTEST -------------------------------------------------

def pnl(close: pd.Series, pos: pd.Series, spread_bp: float,
        swap_daily: Optional[pd.Series] = None) -> pd.Series:
    """
    PnL strat = pos × ret - turnover×coût + swap.
    Décalage : pos à t est connu fin t-1 ; on multiplie par ret[t]. Pas de leak
    si pos est shifté ≥1 par construction (TSMOM 22+, vol shift(1)).
    swap_daily est en unités de rendement quotidien (déjà annualisé/252).
    """
    ret = close.pct_change()
    turn = pos.diff().abs().fillna(0.0)
    cost = turn * (spread_bp / 1e4)
    out = pos * ret - cost
    if swap_daily is not None:
        out = out + swap_daily.reindex(out.index).fillna(0.0)
    return out.dropna()


def sharpe(x: pd.Series) -> float:
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * ANN_SQRT) if x.std() > 0 else float("nan")


def max_dd(x: pd.Series) -> float:
    eq = (1.0 + pd.Series(x).dropna()).cumprod()
    return float((eq / eq.cummax() - 1).min())


def block_bootstrap_sharpe_ci(x: pd.Series, n_boot: int = 3000,
                              block: int = 21, alpha: float = 0.05,
                              seed: int = SEED) -> Tuple[float, float]:
    a = pd.Series(x).dropna().values
    n = len(a)
    rng = np.random.default_rng(seed)
    n_blocks = n // block + 1
    out = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n - block, n_blocks)
        cat = np.concatenate([a[s:s + block] for s in starts])[:n]
        if cat.std() > 0:
            out[b] = cat.mean() / cat.std() * ANN_SQRT
        else:
            out[b] = 0.0
    return float(np.percentile(out, 100 * alpha / 2)), float(np.percentile(out, 100 * (1 - alpha / 2)))


# --------------- CARRY (proxy) -------------------------------------------

def build_carry_us_jp(idx: pd.DatetimeIndex, irx: pd.Series) -> pd.Series:
    """
    Proxy carry US-JP : ^IRX (T-bill 13w) - taux directeur JP (≈0 avant 2024-03,
    0.25 dès 2024-03, 0.50 dès 2024-07). Tous en %. Pas de shift ici.
    """
    us = irx.reindex(idx).ffill()
    jp = pd.Series(0.0, index=idx, dtype=float)
    jp.loc[idx >= "2024-03-01"] = 0.25
    jp.loc[idx >= "2024-07-01"] = 0.50
    return us - jp


# --------------- MAIN ----------------------------------------------------

def main(verbose: bool = True) -> dict:
    print("Téléchargement Yahoo (JPY=X / GC=F / ^IRX) ...")
    jpy_raw = yahoo_close("JPY=X")
    gold_raw = yahoo_close("GC=F")
    irx = yahoo_close("%5EIRX")  # T-bill 13w
    jpy, n_j = declitch(jpy_raw, 0.05)
    gold, n_g = declitch(gold_raw, 0.08)
    print(f"  JPY=X : {len(jpy)} j (déglitchés {n_j}) | GC=F : {len(gold)} j (déglitchés {n_g})")
    print(f"  Période JPY : {jpy.index.min().date()} → {jpy.index.max().date()}")
    print(f"  Période GC  : {gold.index.min().date()} → {gold.index.max().date()}")

    # ---------- J1 : carry-aligned USDJPY ---------------------------------
    carry_usd_jp = build_carry_us_jp(jpy.index, irx)
    mom_j = tsmom_12_1(jpy)
    # filtre carry-aligned : si signe carry == signe mom alors mom, sinon 0
    sign_carry_lag = np.sign(carry_usd_jp.shift(1))  # carry connue t-1
    mom_j_lag = mom_j.shift(1)                       # signal connu t-1
    aligned = (sign_carry_lag == mom_j_lag).astype(float)
    sig_j = (mom_j_lag * aligned).fillna(0.0)

    pos_j = vol_target_position(jpy, sig_j)
    # swap encaissé sur la position : +carry/100/252 (long USDJPY = receive USD, pay JPY)
    swap_j = (pos_j * carry_usd_jp / 100.0 / 252.0).fillna(0.0)
    pnl_j = pnl(jpy, pos_j, spread_bp=0.6, swap_daily=swap_j)

    # ---------- G1 : Gold TSMOM, funding payé -----------------------------
    mom_g = tsmom_12_1(gold)
    sig_g = mom_g.shift(1)  # connue t-1
    pos_g = vol_target_position(gold, sig_g)
    us_lag = irx.reindex(gold.index).ffill().shift(1)
    # funding négatif : long gold paie taux US sur exposition brute (0.9× shaving broker)
    swap_g_long = -(us_lag.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos_g.clip(lower=0)
    # short gold encaisse taux US si crédité (script orig ne le fait PAS — on teste 2 variantes)
    swap_g_short_credited = -(us_lag.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos_g.clip(upper=0)  # signe positif sur short
    swap_g_short_zero = pd.Series(0.0, index=pos_g.index)

    pnl_g_orig = pnl(gold, pos_g, spread_bp=1.5,
                     swap_daily=swap_g_long + swap_g_short_zero)  # script orig
    pnl_g_credited = pnl(gold, pos_g, spread_bp=1.5,
                         swap_daily=swap_g_long + swap_g_short_credited)  # inline

    # ---------- Rapports -------------------------------------------------
    rep = {}
    for name, p in [("J1 USDJPY carry-aligned", pnl_j),
                    ("G1 Gold (orig swap)", pnl_g_orig),
                    ("G1 Gold (credit shorts)", pnl_g_credited)]:
        sr = sharpe(p)
        mdd = max_dd(p)
        skw = float(p.skew())
        ci = block_bootstrap_sharpe_ci(p)
        years_pos = (p.resample("YE").apply(lambda x: x.sum() > 0).sum()) if len(p) else 0
        n_years = len(p.resample("YE").mean())
        print(f"\n{name}")
        print(f"  Sharpe {sr:+.3f} | skew {skw:+.2f} | MaxDD {100*mdd:.1f}% | "
              f"CI95 [{ci[0]:+.2f}, {ci[1]:+.2f}] | années>0 {years_pos}/{n_years}")
        rep[name] = dict(sharpe=sr, max_dd=mdd, skew=skw, ci95=ci,
                         years_pos=int(years_pos), n_years=int(n_years))

    # ---------- Book equal-risk J1 + G1 ----------------------------------
    df = pd.concat([pnl_j.rename("J"), pnl_g_orig.rename("G_orig"),
                    pnl_g_credited.rename("G_credit")], axis=1).dropna()
    j_unit = df["J"] / df["J"].std()
    g_unit_orig = df["G_orig"] / df["G_orig"].std()
    g_unit_credit = df["G_credit"] / df["G_credit"].std()
    book_orig = j_unit + g_unit_orig
    book_credit = j_unit + g_unit_credit

    print("\n=== BOOK J1+G1 (equal-risk) ===")
    print(f"  corr J vs G(orig)    : {df['J'].corr(df['G_orig']):+.3f}")
    print(f"  corr J vs G(credit)  : {df['J'].corr(df['G_credit']):+.3f}")
    print(f"  book(orig)   Sharpe  : {sharpe(book_orig):+.3f}  skew {book_orig.skew():+.2f}  MDD {100*max_dd(book_orig):.1f}%")
    print(f"  book(credit) Sharpe  : {sharpe(book_credit):+.3f}  skew {book_credit.skew():+.2f}  MDD {100*max_dd(book_credit):.1f}%")
    rep["book_orig"] = dict(sharpe=sharpe(book_orig), skew=float(book_orig.skew()),
                            max_dd=max_dd(book_orig),
                            corr_jg=float(df["J"].corr(df["G_orig"])))
    rep["book_credit"] = dict(sharpe=sharpe(book_credit), skew=float(book_credit.skew()),
                              max_dd=max_dd(book_credit),
                              corr_jg=float(df["J"].corr(df["G_credit"])))

    # sauvegarde PnL pour gates suivants
    out_pnl = pd.concat([pnl_j.rename("pnl_J"),
                         pnl_g_orig.rename("pnl_G_orig"),
                         pnl_g_credited.rename("pnl_G_credit")], axis=1)
    out_pnl["book_orig"] = book_orig
    out_pnl["book_credit"] = book_credit
    out_pnl.to_csv("<HOME>/Desktop/Algo_claude/data/trend_research/g0_pnl.csv")
    pd.DataFrame({"jpy": jpy, "gold": gold, "irx": irx.reindex(jpy.index).ffill(),
                  "carry_us_jp": carry_usd_jp}).to_csv(
        "<HOME>/Desktop/Algo_claude/data/trend_research/g0_prices.csv")
    return rep


if __name__ == "__main__":
    out = main()
    print("\nSAVED → data/trend_research/g0_pnl.csv  +  g0_prices.csv")
