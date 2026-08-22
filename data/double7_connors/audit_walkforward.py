"""Audit 1/4 — Walk-forward analysis (ancré + glissant).

Sur chaque fenêtre In-Sample (IS) on sélectionne la configuration
(entry_lb, exit_lb, ma_len) qui maximise le Sharpe, puis on l'applique
TELLE QUELLE sur la fenêtre Out-of-Sample (OOS) suivante. Les segments OOS
concaténés forment une équité walk-forward — la seule honnête, car aucun
paramètre n'y a jamais vu le futur.

Walk-Forward Efficiency (WFE) = perf OOS / perf IS. > ~0.5 = sain.
Indicateurs cachés (warm-up SMA): tous les indicateurs sont calculés sur
l'historique complet, on ne fait que trancher des dates.
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd

import data
import metrics

GRID = [(e, x, m) for m in (100, 150, 200) for e in range(5, 11) for x in range(5, 11)]
SLIP = 5e-4


def precompute_signals(closes: pd.DataFrame) -> dict:
    """{(e,x,m): {sym: (close, entry_bool, exit_bool)}} sur historique complet."""
    cache = {}
    for sym in closes.columns:
        c = closes[sym].dropna()
        for (e, x, m) in GRID:
            sma = c.rolling(m, min_periods=m).mean()
            ent = ((c <= c.rolling(e).min()) & (c > sma)).values
            exi = (c >= c.rolling(x).max()).values
            cache.setdefault((e, x, m), {})[sym] = (c.index.values, c.values, ent, exi)
    return cache


def sleeve_eq(close, entry, exit_, mask, slip, sleeve0):
    cash, shares, epx = sleeve0, 0.0, np.nan
    eq = np.empty(mask.sum())
    rets = []
    j = 0
    for i in range(len(close)):
        if not mask[i]:
            continue
        px = close[i]
        if shares > 0 and exit_[i]:
            fill = px * (1 - slip)
            cash, shares = shares * fill, 0.0
            rets.append(fill / epx - 1)
        elif shares == 0 and entry[i]:
            epx = px * (1 + slip)
            shares, cash = cash / epx, 0.0
        eq[j] = cash + shares * px
        j += 1
    return eq, rets


def run(cache, cfg, dates_idx, start, end, capital=100_000.0):
    syms = list(cache[cfg].keys())
    sleeve0 = capital / len(syms)
    eqs, all_rets = [], []
    for sym in syms:
        idx, close, ent, exi = cache[cfg][sym]
        mask = (idx >= np.datetime64(start)) & (idx <= np.datetime64(end))
        if mask.sum() == 0:
            continue
        eq, rets = sleeve_eq(close, ent, exi, mask, SLIP, sleeve0)
        eqs.append(pd.Series(eq, index=pd.DatetimeIndex(idx[mask])))
        all_rets += rets
    port = pd.concat(eqs, axis=1).ffill().bfill().sum(axis=1)
    return port, all_rets


def sharpe_of(port):
    r = port.pct_change().dropna()
    return np.sqrt(252) * r.mean() / r.std(ddof=1) if r.std(ddof=1) > 0 else np.nan


def walk_forward(cache, dates, is_years, oos_years, anchored, start="2007-01-01"):
    """Retourne (segments_df, equity_oos concaténée chaînée)."""
    t0 = pd.Timestamp(start)
    tend = dates[-1]
    segs = []
    oos_curves = []
    is_start = t0
    oos_start = t0 + pd.DateOffset(years=is_years)
    while oos_start + pd.DateOffset(years=oos_years) <= tend + pd.DateOffset(days=5):
        is_a = is_start if anchored else (oos_start - pd.DateOffset(years=is_years))
        is_b = oos_start - pd.DateOffset(days=1)
        oos_a = oos_start
        oos_b = oos_start + pd.DateOffset(years=oos_years) - pd.DateOffset(days=1)
        # sélection IS
        best, best_sh = None, -np.inf
        is_sh_best = np.nan
        for cfg in GRID:
            p, _ = run(cache, cfg, dates, is_a, is_b)
            sh = sharpe_of(p)
            if np.isfinite(sh) and sh > best_sh:
                best_sh, best, is_sh_best = sh, cfg, sh
        # application OOS
        p_oos, rets = run(cache, best, dates, oos_a, oos_b)
        oos_sh = sharpe_of(p_oos)
        oos_ret = p_oos.iloc[-1] / p_oos.iloc[0] - 1
        segs.append(dict(is_start=str(is_a.date()), is_end=str(is_b.date()),
                         oos_start=str(oos_a.date()), oos_end=str(oos_b.date()),
                         cfg=str(best), is_sharpe=float(is_sh_best),
                         oos_sharpe=float(oos_sh), oos_return=float(oos_ret),
                         n_trades=len(rets)))
        oos_curves.append(p_oos / p_oos.iloc[0])
        oos_start = oos_start + pd.DateOffset(years=oos_years)
    # chaînage des courbes OOS
    chained, level = [], 1.0
    for seg in oos_curves:
        chained.append(seg * level)
        level = chained[-1].iloc[-1]
    equity = pd.concat(chained)
    equity = equity[~equity.index.duplicated(keep="first")]
    return pd.DataFrame(segs), equity


def main():
    etf = data.load_etf_closes()
    cache = precompute_signals(etf)
    dates = etf.index

    out = {}
    for name, is_y, oos_y, anch in [("anchored_5is_2oos", 5, 2, True),
                                    ("rolling_4is_2oos", 4, 2, False),
                                    ("rolling_3is_1oos", 3, 1, False)]:
        segs, eq = walk_forward(cache, dates, is_y, oos_y, anch)
        r = eq.pct_change().dropna()
        sh = np.sqrt(252) * r.mean() / r.std(ddof=1)
        cagr = (eq.iloc[-1] / eq.iloc[0]) ** (252 / len(eq)) - 1
        mdd = (eq / eq.cummax() - 1).min()
        wfe = segs.oos_sharpe.mean() / segs.is_sharpe.mean()
        pos = float((segs.oos_sharpe > 0).mean())
        out[name] = dict(oos_sharpe=float(sh), oos_cagr=float(cagr), oos_maxdd=float(mdd),
                         wfe=float(wfe), pct_oos_positive=pos,
                         n_segments=len(segs),
                         mean_is_sharpe=float(segs.is_sharpe.mean()),
                         mean_oos_sharpe=float(segs.oos_sharpe.mean()),
                         segments=segs.to_dict("records"))
        eq.to_csv(f"wf_equity_{name}.csv")
        print(f"\n=== {name} ===  segments={len(segs)}")
        print(f"  OOS chaîné: Sharpe={sh:.2f} CAGR={cagr:+.2%} MaxDD={mdd:.1%}")
        print(f"  WFE={wfe:.2f} | OOS positifs={pos:.0%} | IS Sharpe moy={segs.is_sharpe.mean():.2f} OOS moy={segs.oos_sharpe.mean():.2f}")
        print(segs[["oos_start", "oos_end", "cfg", "is_sharpe", "oos_sharpe", "oos_return"]].to_string(index=False))

    json.dump(out, open("audit_walkforward.json", "w"), indent=1)
    print("\nsaved audit_walkforward.json")


if __name__ == "__main__":
    main()
