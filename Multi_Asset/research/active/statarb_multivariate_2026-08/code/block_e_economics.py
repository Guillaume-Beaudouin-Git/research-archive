"""BLOC E — le seul survivant converti en métrique de décision.

XAGUSD -> XAUUSD, h=120 min, conditionné sur |mouvement de l'argent| >= q.
Intraday-flat (aucun swap : 2 h de tenue).

Questions, dans l'ordre où le desk les pose :
  E1  combien de trades par an, et quel net par trade au coût CENTRE puis au coût QUEUE
  E2  Sharpe annualisé en sqrt(trades/an) — L47, PAS sqrt(252)
  E3  quel levier faut-il pour viser +10 % en 182 jours, et que devient le plancher
      STATIQUE -10 % à ce levier (le floor lie, 49.7 % des morts, pas la barrière
      journalière)
  E4  bootstrap par BLOCS (Politis-Romano) sur l'IC du net par trade — jamais iid
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

M1DIR = sys.argv[1] if len(sys.argv) > 1 else "m1"

LEAD, FOLL, H = "XAGUSD", "XAUUSD", 120
COST_CENTRE, COST_TAIL = 1.84, 3.88      # COST_AUDIT.md §3
HORIZON_D = 182                           # horizon de décision retenu
TARGET = 0.10                             # phase 1 FTMO
FLOOR = -0.10                             # plancher STATIQUE
DAILY = -0.05
RNG = np.random.default_rng(20260803)


def build(q):
    L = pd.read_parquet(os.path.join(M1DIR, f"{LEAD}.parquet"))
    F = pd.read_parquet(os.path.join(M1DIR, f"{FOLL}.parquet"))
    idx = L.index.intersection(F.index)
    lc = np.log(L["close"].reindex(idx).to_numpy())
    fc = np.log(F["close"].reindex(idx).to_numpy())
    zr = L["zr"].reindex(idx).to_numpy()
    tmin = idx.asi8 // 60_000_000_000
    n = len(idx)
    i = np.arange(H, n - H - 2, H)
    ok = (tmin[i] - tmin[i - H] == H) & (tmin[i + H + 1] - tmin[i + 1] == H)
    sig = lc[i] - lc[i - H]
    ok &= (sig != 0) & (~zr[i])
    i, sig = i[ok], sig[ok]
    fwd = fc[i + H + 1] - fc[i + 1]
    m = np.abs(sig) >= np.quantile(np.abs(sig), q)
    return np.sign(sig[m]) * fwd[m] * 1e4, idx[i][m]


def block_boot(x, bs=20, n=5000):
    nb = int(np.ceil(len(x) / bs))
    out = np.empty(n)
    for j in range(n):
        st = RNG.integers(0, len(x) - bs, nb)
        out[j] = np.concatenate([x[s:s + bs] for s in st]).mean()
    return out


def main():
    for q in (0.95, 0.90):
        g, ts = build(q)
        yrs = (ts[-1] - ts[0]).days / 365.25
        tpy = len(g) / yrs
        print("\n" + "=" * 74)
        print(f"XAGUSD->XAUUSD h={H}min q={q}   n={len(g)}  {yrs:.1f} ans  "
              f"{tpy:.0f} trades/an")
        print("=" * 74)

        for lbl, c in (("centre", COST_CENTRE), ("queue p95", COST_TAIL)):
            net = g - c
            sr = net.mean() / net.std(ddof=1) * np.sqrt(tpy)     # L47
            ann = net.mean() * tpy / 100
            print(f"E1/E2 coût {lbl:>9} {c:.2f}bps : net/trade {net.mean():+6.3f}bps  "
                  f"sd {net.std(ddof=1):7.1f}  SR_ann(sqrt {tpy:.0f}) {sr:+.3f}  "
                  f"rendement 1x {ann:+.2f}%/an")

        net = g - COST_CENTRE
        bb = block_boot(net)
        lo, hi = np.quantile(bb, [0.025, 0.975])
        print(f"E4 bootstrap par blocs (b=20, 5000) : net/trade IC95 "
              f"[{lo:+.3f}, {hi:+.3f}] bps  "
              f"{'contient zéro' if lo <= 0 <= hi else 'exclut zéro'}")

        # E3 — levier requis et risque de plancher statique
        n_tr = int(round(tpy * HORIZON_D / 365.25))
        mu, sd = net.mean() / 1e4, net.std(ddof=1) / 1e4
        lam = TARGET / (mu * n_tr) if mu > 0 else np.nan
        print(f"E3 sur {HORIZON_D} j : {n_tr} trades attendus. "
              f"Levier pour viser +{TARGET:.0%} : x{lam:.1f}")
        if np.isfinite(lam) and lam > 0:
            hit_t = hit_f = 0
            NS = 20000
            for _ in range(NS):
                s = RNG.integers(0, len(net), n_tr)
                path = np.cumsum(net[s] / 1e4 * lam)
                fi = np.argmax(path <= FLOOR) if (path <= FLOOR).any() else 10**9
                ti = np.argmax(path >= TARGET) if (path >= TARGET).any() else 10**9
                if fi < ti:
                    hit_f += 1
                elif ti < 10**9:
                    hit_t += 1
            print(f"   MC iid-trades (indicatif) : atteint +10 % {hit_t/NS:.1%}  |  "
                  f"touche le plancher statique -10 % d'abord {hit_f/NS:.1%}")
            print(f"   choc d'UN trade au levier x{lam:.1f} : "
                  f"1 sd = {sd*lam:.2%} de l'équité, "
                  f"pire trade observé = {net.min()/1e4*lam:+.2%} "
                  f"(barrière journalière {DAILY:.0%})")


if __name__ == "__main__":
    main()
