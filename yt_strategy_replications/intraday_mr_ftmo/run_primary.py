"""
PRIMARY config (k=20, z0=2.0, s_sl=s_tp=1.0, H=8): gross two-sided falsification,
per-leg decomposition (L25), net at measured/2bps/3bps, pooled index book.
Costs applied analytically: with vol-target notional scale s, ret_net = s*(ret_gross - cost_rt).
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import dataload as DL
import signals as SIG
from engine import backtest as BT
from engine import stats as S

INDICES, FX = DL.INDICES, DL.FX
PPY = 252.0
K, Z0, S_SL, S_TP, H = 20, 2.0, 1.0, 1.0, 8
N_TRIALS = 18  # provisional (primary + per-leg); final DSR uses the full study count


def bars_per_year(sym):
    return (26 if sym in INDICES else 36) * 252.0


def trade_daily(trades, scale, cost_rt, all_days):
    if trades.empty:
        return pd.Series(0.0, index=all_days)
    s = np.nan_to_num(scale.reindex(trades["entry_time"]).to_numpy(), nan=0.0)
    ret = s * (trades["ret_gross"].to_numpy() - cost_rt)
    day = pd.DatetimeIndex(trades["exit_time"]).normalize()
    dr = pd.Series(ret, index=day).groupby(level=0).sum()
    return dr.reindex(all_days, fill_value=0.0)


def metrics(dr, n_trials=N_TRIALS, bootstrap=False):
    dr = dr[dr.index.notna()]
    eq = np.cumprod(1 + dr.to_numpy())
    mdd, _ = S.max_drawdown(eq)
    hm, ht = S.hac_tstat(dr.to_numpy(), lags=6)
    dsr = S.deflated_sharpe_ratio(dr.to_numpy(), n_trials=n_trials, periods_per_year=PPY)
    folds = S.fold_metrics(dr.to_numpy(), n_folds=5, periods_per_year=PPY)
    out = dict(sharpe=S.sharpe_ratio(dr.to_numpy(), PPY), hac_t=ht, hac_mean_bps=hm * 1e4,
               dsr=dsr.get("dsr", float("nan")), wf=folds["wf_score"],
               mdd=mdd, n_days=int((dr != 0).sum()))
    if bootstrap:
        out["boot_p"] = S.stationary_bootstrap_pvalue(dr.to_numpy())
    return out


def run_symbol(sym):
    df = DL.load(sym)
    sig, sl, tp = SIG.zscore_reversal(df, k=K, z0=Z0, s_sl=S_SL, s_tp=S_TP, H=H)
    scale = SIG.vol_target_scale(df, k=K, bars_per_year=bars_per_year(sym))
    days = df["session_date"].drop_duplicates().to_numpy()
    days = pd.DatetimeIndex(days)
    med_cost = float(df["spread_bps"].median()) / 1e4

    def bt(allow_long, allow_short):
        return BT.run_backtest_vectorized(df, sig, sl_dist=sl, tp_dist=tp, cost_rt=0.0,
                                          max_hold=H, allow_long=allow_long, allow_short=allow_short)

    tr_both = bt(True, True); tr_long = bt(True, False); tr_short = bt(False, True)
    res = {"sym": sym, "n_trades": int(len(tr_both)),
           "med_spread_bps": round(med_cost * 1e4, 3),
           "avg_bars_held": round(float(tr_both["bars_held"].mean()), 2) if len(tr_both) else float("nan"),
           "frac_sl": round(float((tr_both["reason"] == "sl").mean()), 3) if len(tr_both) else float("nan"),
           "frac_tp": round(float((tr_both["reason"] == "tp").mean()), 3) if len(tr_both) else float("nan"),
           "win_rate": round(float((tr_both["ret_gross"] > 0).mean()), 3) if len(tr_both) else float("nan")}
    res["gross"] = metrics(trade_daily(tr_both, scale, 0.0, days))
    res["gross_long"] = metrics(trade_daily(tr_long, scale, 0.0, days))
    res["gross_short"] = metrics(trade_daily(tr_short, scale, 0.0, days))
    stress = [med_cost, 0.0002, 0.0003] if sym in INDICES else [med_cost, 0.0003, 0.0005]
    res["net"] = {f"{c*1e4:.1f}bps": metrics(trade_daily(tr_both, scale, c, days)) for c in stress}
    # store the per-day series for pooling (measured cost)
    res["_daily_gross"] = trade_daily(tr_both, scale, 0.0, days)
    res["_daily_net2"] = trade_daily(tr_both, scale, 0.0002 if sym in INDICES else 0.0003, days)
    return res


def fmt(m):
    return (f"SR {m['sharpe']:+.2f} | HACt {m['hac_t']:+.2f} | mean {m['hac_mean_bps']:+.2f}bps/d "
            f"| DSR {m['dsr']:.2f} | WF {m['wf']:.0%} | MDD {m['mdd']:.1%} | n {m['n_days']}")


if __name__ == "__main__":
    allres = {}
    print("=" * 100)
    for sym in INDICES + FX:
        r = run_symbol(sym); allres[sym] = r
        print(f"\n### {sym}  n_trades={r['n_trades']}  bars_held={r['avg_bars_held']}  "
              f"WR={r['win_rate']}  frac_sl={r['frac_sl']} frac_tp={r['frac_tp']}  spr={r['med_spread_bps']}bps")
        print(f"  GROSS  both : {fmt(r['gross'])}")
        print(f"  GROSS  long : {fmt(r['gross_long'])}")
        print(f"  GROSS  short: {fmt(r['gross_short'])}")
        for c, m in r["net"].items():
            print(f"  NET {c:>7}: {fmt(m)}")

    # pooled index book (equal-weight daily, vol-targeted)
    def pool(key, syms, n_trials):
        mat = pd.concat([allres[s][key] for s in syms], axis=1).fillna(0.0)
        dr = mat.mean(axis=1)
        return metrics(dr, n_trials=n_trials, bootstrap=False), dr

    print("\n" + "=" * 100)
    for label, syms in [("INDEX book", INDICES), ("FX book", FX), ("ALL", INDICES + FX)]:
        mg, _ = pool("_daily_gross", syms, N_TRIALS)
        mn, drn = pool("_daily_net2", syms, N_TRIALS)
        print(f"\n>>> {label} ({'+'.join(syms)})")
        print(f"    POOLED GROSS     : {fmt(mg)}")
        print(f"    POOLED NET(2/3bp): {fmt(mn)}")

    # persist headline (drop the heavy series)
    clean = {s: {k: v for k, v in r.items() if not k.startswith("_daily")} for s, r in allres.items()}
    (HERE / "results_primary.json").write_text(json.dumps(clean, indent=2, default=float))
    print("\nsaved results_primary.json")
