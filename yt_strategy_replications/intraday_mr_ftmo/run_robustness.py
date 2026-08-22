"""
Robustness for the negative result: (1) S1 grid z0 x H over the index book
(gross two-sided + net@2bps), (2) the autocorrelation sign check (does MOMENTUM
work where reversion failed?), (3) S2 gap-fade secondary. Confirmatory; vectorized.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import dataload as DL, signals as SIG
from engine import backtest as BT, stats as S
INDICES = DL.INDICES
PPY = 252.0


def bpy(sym): return (26 if sym in INDICES else 36) * 252.0


def daily(trades, scale, cost, days):
    if trades.empty: return pd.Series(0.0, index=days)
    s = np.nan_to_num(scale.reindex(trades["entry_time"]).to_numpy(), nan=0.0)
    ret = s * (trades["ret_gross"].to_numpy() - cost)
    d = pd.DatetimeIndex(trades["exit_time"]).normalize()
    return pd.Series(ret, index=d).groupby(level=0).sum().reindex(days, fill_value=0.0)


def pooled(series_list):
    dr = pd.concat(series_list, axis=1).fillna(0.0).mean(axis=1)
    _, ht = S.hac_tstat(dr.to_numpy(), 6)
    return S.sharpe_ratio(dr.to_numpy(), PPY), ht


def load_all():
    data = {}
    for s in INDICES:
        df = DL.load(s)
        data[s] = (df, SIG.vol_target_scale(df, bars_per_year=bpy(s)),
                   pd.DatetimeIndex(df["session_date"].drop_duplicates().to_numpy()),
                   float(df["spread_bps"].median()) / 1e4)
    return data


def main():
    data = load_all()
    print("=== S1 grid (index book pooled): gross both / net@2bps ===")
    print(f"{'z0':>4} {'H':>3} | {'grossSR':>8} {'grossT':>7} | {'net2SR':>8} {'net2T':>7}")
    for z0 in (1.5, 2.0, 2.5):
        for H in (4, 8, 12):
            g, n2 = [], []
            for s in INDICES:
                df, scale, days, _ = data[s]
                sig, sl, tp = SIG.zscore_reversal(df, k=20, z0=z0, s_sl=1.0, s_tp=1.0, H=H)
                tr = BT.run_backtest_vectorized(df, sig, sl_dist=sl, tp_dist=tp, cost_rt=0.0,
                                                max_hold=H, allow_long=True, allow_short=True)
                g.append(daily(tr, scale, 0.0, days)); n2.append(daily(tr, scale, 0.0002, days))
            gs, gt = pooled(g); ns, nt = pooled(n2)
            print(f"{z0:>4} {H:>3} | {gs:>+8.2f} {gt:>+7.2f} | {ns:>+8.2f} {nt:>+7.2f}")

    print("\n=== MOMENTUM check (flip the sign: trade WITH the z-move), primary z0=2 H=8, gross ===")
    print(f"{'sym':>6} | {'momSR':>7} {'momT':>7}  (if positive: intraday autocorr is +, i.e. NOT mean-reverting)")
    for s in INDICES:
        df, scale, days, _ = data[s]
        sig, sl, tp = SIG.zscore_reversal(df, k=20, z0=2.0, s_sl=1.0, s_tp=1.0, H=8)
        tr = BT.run_backtest_vectorized(df, -np.asarray(sig), sl_dist=sl, tp_dist=tp, cost_rt=0.0,
                                        max_hold=8, allow_long=True, allow_short=True)
        dr = daily(tr, scale, 0.0, days); _, t = S.hac_tstat(dr.to_numpy(), 6)
        print(f"{s:>6} | {S.sharpe_ratio(dr.to_numpy(), PPY):>+7.2f} {t:>+7.2f}")

    print("\n=== S2 gap-fade (indices), gross both / net@2bps ===")
    print(f"{'sym':>6} | {'n':>5} | {'grossSR':>8} {'grossT':>7} | {'net2SR':>8} {'net2T':>7}")
    gg, gn = [], []
    for s in INDICES:
        df, scale, days, _ = data[s]
        sig, sl, tp = SIG.gap_fade(df, g0=1.0, s_sl=1.0, s_tp=1.0)
        tr = BT.run_backtest_vectorized(df, sig, sl_dist=sl, tp_dist=tp, cost_rt=0.0,
                                        max_hold=26, allow_long=True, allow_short=True)
        dg = daily(tr, scale, 0.0, days); dn = daily(tr, scale, 0.0002, days)
        gg.append(dg); gn.append(dn)
        _, gt = S.hac_tstat(dg.to_numpy(), 6); _, nt = S.hac_tstat(dn.to_numpy(), 6)
        print(f"{s:>6} | {len(tr):>5} | {S.sharpe_ratio(dg.to_numpy(),PPY):>+8.2f} {gt:>+7.2f} | "
              f"{S.sharpe_ratio(dn.to_numpy(),PPY):>+8.2f} {nt:>+7.2f}")
    gs, gt = pooled(gg); ns, nt = pooled(gn)
    print(f"{'POOL':>6} |       | {gs:>+8.2f} {gt:>+7.2f} | {ns:>+8.2f} {nt:>+7.2f}")


if __name__ == "__main__":
    main()
