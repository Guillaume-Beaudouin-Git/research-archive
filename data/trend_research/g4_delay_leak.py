"""
G4 — Test délai+1 résiduel (L26).

Le rapport admet avoir attrapé un bug look-ahead trailing-stop (SR 2.05 → 0.32).
On vérifie qu'il n'en reste aucun en délayant le signal d'un jour supplémentaire
sur J1, G1, book.

Logique : si pos[t] n'utilise QUE des données ≤ t-1 (comme prétendu), alors
ajouter shift(+1) au signal doit DÉTÉRIORER ou laisser stable (perte d'1 jour
d'info), JAMAIS améliorer. Si le SR monte avec délai+1 → leak résiduel.

On teste aussi délai+2, délai+3 pour profiler la décroissance attendue.
Et inversement délai−1 (anti-causal, infaisable mais utile comme sanity) :
ça doit AMÉLIORER si le signal capture du trend, et fortement améliorer si
on triche.
"""
from __future__ import annotations
import json
import urllib.request

import numpy as np
import pandas as pd

ANN = np.sqrt(252)


def yahoo_close(ticker):
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


def declitch(s, thresh=0.05):
    r = s.pct_change()
    bad = (r.abs() > thresh) & ((r + r.shift(-1)).abs() < thresh / 2)
    out = s.copy()
    out[bad] = np.nan
    return np.exp(np.log(out).interpolate())


def tsmom(px):
    return np.sign(px.shift(22) / px.shift(252) - 1.0)


def vol_target_pos(px, sig, tgt=0.10, w=20, cap=3.0):
    r = px.pct_change()
    rv = r.rolling(w).std().shift(1) * ANN
    return (tgt / rv).clip(upper=cap) * sig


def sharpe(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * ANN) if x.std() > 0 else float("nan")


def compute_pnl(px, sig_base, carry, spread_bp, swap_kind, delay):
    """
    sig_base : signal "natural" (=tsmom, déjà laggé d'office par construction)
    delay : nb jours de SHIFT additionnel positif (=futurisé en signal) ou
            négatif (=anti-causal, sanity check).
    """
    sig = sig_base.shift(delay) if delay != 0 else sig_base
    pos = vol_target_pos(px, sig)
    r = px.pct_change()
    base = pos * r - pos.diff().abs().fillna(0.0) * spread_bp / 1e4
    if swap_kind == "J":
        swap = pos * carry / 100.0 / 252.0
    elif swap_kind == "G":
        swap = -(carry.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos.clip(lower=0)
    else:
        swap = pd.Series(0.0, index=pos.index)
    return (base + swap).dropna()


def main():
    print("G4 — Test délai+1 résiduel\n")
    jpy = declitch(yahoo_close("JPY=X"), 0.05)
    gold = declitch(yahoo_close("GC=F"), 0.08)
    irx = yahoo_close("%5EIRX")

    us = irx.reindex(jpy.index).ffill()
    jp = pd.Series(0.0, index=jpy.index)
    jp[jpy.index >= "2024-03-01"] = 0.25
    jp[jpy.index >= "2024-07-01"] = 0.50
    carry_jp = (us - jp).shift(2)
    us_g = irx.reindex(gold.index).ffill().shift(2)

    # signaux "naturels" (laggés d'office)
    mom_j = tsmom(jpy)
    sig_j = pd.Series(np.where(np.sign(carry_jp).fillna(0) == mom_j, mom_j, 0.0),
                      index=jpy.index)
    mom_g = tsmom(gold)
    sig_g = mom_g

    print(f"  {'delay (j)':>10} {'SR J1':>9} {'SR G1':>9} {'SR book':>9}")
    delays = [-3, -2, -1, 0, 1, 2, 3, 5, 10]
    rows = []
    for d in delays:
        pnl_j = compute_pnl(jpy, sig_j, carry_jp, 0.6, "J", d)
        pnl_g = compute_pnl(gold, sig_g, us_g, 1.5, "G", d)
        # book equal-risk : il faut une normalisation cohérente
        df = pd.concat([pnl_j.rename("J"), pnl_g.rename("G")], axis=1).dropna()
        if df["J"].std() > 0 and df["G"].std() > 0:
            book = df["J"] / df["J"].std() + df["G"] / df["G"].std()
            sr_book = sharpe(book)
        else:
            sr_book = float("nan")
        sr_j = sharpe(pnl_j)
        sr_g = sharpe(pnl_g)
        rows.append((d, sr_j, sr_g, sr_book))
        prefix = "← anti-causal (sanity)" if d < 0 else ("← baseline" if d == 0 else "← futurise (perte d'info)")
        print(f"  {d:>10} {sr_j:+9.3f} {sr_g:+9.3f} {sr_book:+9.3f}   {prefix if abs(d) <= 1 else ''}")

    # Vérification cible : SR(delay=+1) < SR(delay=0) sur les trois, et idéalement
    # SR(delay=-1) > SR(delay=0) ; sinon flag.
    print("\n=== Verdict de leak ===")
    sr0_j = next(r[1] for r in rows if r[0] == 0)
    sr1_j = next(r[1] for r in rows if r[0] == 1)
    sr0_g = next(r[2] for r in rows if r[0] == 0)
    sr1_g = next(r[2] for r in rows if r[0] == 1)
    sr0_b = next(r[3] for r in rows if r[0] == 0)
    sr1_b = next(r[3] for r in rows if r[0] == 1)

    def verdict(sr_base, sr_lag):
        d = sr_lag - sr_base
        if d > 0.10:
            return f"❌ LEAK PROBABLE (+{d:.2f} SR avec délai+1)"
        if d > 0.0:
            return f"⚠ borderline (+{d:.2f}), proche bruit"
        return f"✓ OK ({d:+.2f})"

    print(f"  J1   : SR(0)={sr0_j:+.3f}  SR(+1)={sr1_j:+.3f}  → {verdict(sr0_j, sr1_j)}")
    print(f"  G1   : SR(0)={sr0_g:+.3f}  SR(+1)={sr1_g:+.3f}  → {verdict(sr0_g, sr1_g)}")
    print(f"  Book : SR(0)={sr0_b:+.3f}  SR(+1)={sr1_b:+.3f}  → {verdict(sr0_b, sr1_b)}")

    # Sanity check anti-causal
    srm1_j = next(r[1] for r in rows if r[0] == -1)
    srm1_g = next(r[2] for r in rows if r[0] == -1)
    srm1_b = next(r[3] for r in rows if r[0] == -1)
    print(f"\n  Sanity anti-causal (délai −1) :")
    print(f"  J1 SR(0)={sr0_j:+.3f}, SR(-1)={srm1_j:+.3f} (devrait être > si signal a une corr forward)")
    print(f"  G1 SR(0)={sr0_g:+.3f}, SR(-1)={srm1_g:+.3f}")
    print(f"  Book SR(0)={sr0_b:+.3f}, SR(-1)={srm1_b:+.3f}")

    df_out = pd.DataFrame(rows, columns=["delay", "SR_J1", "SR_G1", "SR_book"])
    df_out.to_csv("<HOME>/Desktop/Algo_claude/data/trend_research/g4_delay_grid.csv", index=False)
    print("\nSAVED → g4_delay_grid.csv")


if __name__ == "__main__":
    main()
