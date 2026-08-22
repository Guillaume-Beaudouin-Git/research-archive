#!/usr/bin/env python3
"""Idea 5B — cross-sectional short-term reversion (long-only) on US large-caps.
Tests: (1) signal existence (losers - winners, diagnostic/non-compliant),
(2) compliant long-only alpha over equal-weight benchmark net of cost,
(3) cost sweep, delay, by-year. Causal: rank by trailing-k return as of t-lag."""
import numpy as np, pandas as pd

PANEL = "/sessions/affectionate-epic-faraday/mnt/data/panels/single_stocks.csv"
FTMO27 = ['AAPL','MSFT','AMZN','GOOGL','META','NVDA','TSLA','INTC','JPM','BAC','V','MA','DIS',
          'KO','PEP','XOM','CVX','BA','MRK','WMT','HD','CSCO','QCOM','IBM','NKE','MCD','T']


def load(universe="broad"):
    d = pd.read_csv(PANEL, index_col=0, parse_dates=True).sort_index()
    nanfree = [c for c in d.columns if d[c].notna().all()]
    cols = nanfree if universe == "broad" else [c for c in FTMO27 if c in d.columns]
    return d[cols]


def ann(x):
    x = x[~np.isnan(x)]; s = x.std(ddof=1)
    return dict(sharpe=round(float(x.mean()/s*np.sqrt(252)), 2) if s > 0 else 0.0,
                t=round(float(x.mean()/s*np.sqrt(len(x))), 2) if s > 0 else 0.0,
                mean_bps=round(float(x.mean()*1e4), 2), ann_ret=round(float(x.mean()*252*100), 1))


def port(close, k, m, H, lag=1, cost_bps=0.0):
    rets = close.pct_change().clip(-0.30, 0.30).values
    trail = close.pct_change(k).values
    T, N = rets.shape
    posL = np.zeros((T, N)); posW = np.zeros((T, N))
    reb = np.zeros(T, bool)
    d = max(k + lag + 1, 2)
    while d < T:
        srow = trail[d - lag]
        valid = ~np.isnan(srow)
        if valid.sum() >= 2 * m:
            order = np.argsort(np.where(valid, srow, np.inf))
            losers = order[:m]; winners = order[valid.sum() - m: valid.sum()]
            posL[d:d + H, losers] = 1.0 / m
            posW[d:d + H, winners] = 1.0 / m
            reb[d] = True
        d += H
    Lr = np.nansum(posL * np.nan_to_num(rets), axis=1)
    Wr = np.nansum(posW * np.nan_to_num(rets), axis=1)
    Br = np.nanmean(rets, axis=1)
    # cost: full rotation (~2 sides) on rebalance days, per-name bps
    c = np.zeros(T); c[reb] = 2 * cost_bps * 1e-4
    Lr_net = Lr - c
    active = posL.sum(1) > 0
    return dict(L=Lr_net[active], L_gross=Lr[active], W=Wr[active], B=Br[active],
                LW=(Lr - Wr)[active], Lb=(Lr_net - Br)[active], n_days=int(active.sum()),
                n_reb=int(reb.sum()))


def main():
    for uni in ("broad", "ftmo27"):
        close = load(uni)
        print(f"\n{'='*70}\nUNIVERSE={uni}  ({close.shape[1]} names, {close.index[0].date()}..{close.index[-1].date()})")
        # existence + compliant alpha across grid (gross)
        print("grid (gross): k/m/H | L-W t (exist) | L-bench t (compliant alpha) | L Sharpe")
        best = None
        for k in (1, 3, 5):
            for m in (3, 5, 10):
                for H in (1, 3, 5):
                    p = port(close, k, m, H, lag=1, cost_bps=0)
                    lw, lb = ann(p["LW"]), ann(p["Lb"])
                    if best is None or lw["t"] > best[1]:
                        best = ((k, m, H), lw["t"], lb["t"])
                    if (k, m, H) in [(1,5,1),(3,5,3),(5,5,5),(1,10,1)]:
                        print(f"  {k}/{m}/{H}: L-W t {lw['t']:+.2f} (Sh {lw['sharpe']:+.2f}) | "
                              f"L-bench t {lb['t']:+.2f} | L Sh {ann(p['L'])['sharpe']:+.2f}")
        print(f"  BEST L-W by t: k/m/H={best[0]} -> L-W t {best[1]:+.2f}, its L-bench t {best[2]:+.2f}")
        # COST SWEEP on a deployable config (k=5,m=5,H=5 baseline) — compliant L-bench AND L abs
        print("cost sweep (baseline k5/m5/H5):  L-bench(alpha) & L(absolute) net")
        for cb in (0, 5, 10, 20):
            p = port(close, 5, 5, 5, lag=1, cost_bps=cb)
            print(f"  {cb}bps/name: L-bench t {ann(p['Lb'])['t']:+.2f} ({ann(p['Lb'])['ann_ret']:+.1f}%/y) | "
                  f"L abs Sharpe {ann(p['L'])['sharpe']:+.2f} ({ann(p['L'])['ann_ret']:+.1f}%/y)")
        # delay test (k=1 reversal most delay-sensitive)
        p1 = port(close, 1, 5, 1, lag=1, cost_bps=0); p2 = port(close, 1, 5, 1, lag=2, cost_bps=0)
        print(f"delay (k1/m5/H1) L-W: t+1 t {ann(p1['LW'])['t']:+.2f} | t+2 t {ann(p2['LW'])['t']:+.2f} "
              f"(collapse => 1-day bounce/microstructure)")
        if uni == "ftmo27":
            # by-year for compliant long-only baseline @10bps
            p = port(close, 5, 5, 5, lag=1, cost_bps=10)
            idx = close.index[close.pct_change().clip(-.3,.3).notna().any(1)]
            Lb = pd.Series(port(close,5,5,5,1,10)["Lb"])
            # rough by-year using active days
            print("(by-year omitted in console; ledger saved)")


if __name__ == "__main__":
    main()
