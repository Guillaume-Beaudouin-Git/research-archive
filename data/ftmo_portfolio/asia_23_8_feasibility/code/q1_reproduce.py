"""Q1 — Reproduction of ASIA_23_8 headline metrics on the current stack.

Reuses yt_strategy_replications/gold_research/strategy_overnight.py (backtest) and
engine/stats.py (metrics). Compares to BOTH the report (1.10/0.96/-19.4%/+0.35/t4.8/DSR0.99)
and the code docstring (1.18/1.07/-15.6%/t3.9/DSR0.92). Read-only; writes results JSON.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

YT = Path("<HOME>/Desktop/Algo_claude/yt_strategy_replications")
sys.path.insert(0, str(YT))
sys.path.insert(0, str(YT / "gold_research"))
from engine import data, stats as S          # noqa: E402
import strategy_overnight as SO               # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "results"
OUT.mkdir(exist_ok=True)


def load_h1():
    try:
        return data.load_h1("XAUUSD")
    except (FileNotFoundError, OSError):
        print("building XAUUSD H1 cache from M1 (466MB, ~1min)...", flush=True)
        return data.build_deephist_h1("XAUUSD")


def metrics(net: pd.Series, gold_daily: pd.Series, label: str) -> dict:
    r = net.to_numpy(float)
    n = r.size
    yrs = (net.index[-1] - net.index[0]).days / 365.25
    obs_per_yr = n / yrs
    eq = (1 + net).cumprod().to_numpy()
    mdd, _ = S.max_drawdown(eq)
    # OOS = last 40%
    cut = int(np.floor(n * 0.6))
    oos = r[cut:]
    mean_d, t_hac = S.hac_tstat(r, lags=6)
    dsr = S.deflated_sharpe_ratio(r, 90, periods_per_year=252)
    # beta vs buy&hold gold (daily), HAC alpha
    g = gold_daily.reindex(net.index).to_numpy(float)
    ok = np.isfinite(g) & np.isfinite(r)
    import statsmodels.api as sm
    X = sm.add_constant(g[ok])
    reg = sm.OLS(r[ok], X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    out = dict(
        label=label, n_obs=int(n), years=round(yrs, 2), obs_per_year=round(obs_per_yr, 1),
        ann_return_pct=round((eq[-1] ** (1 / yrs) - 1) * 100, 2),
        ann_vol_pct=round(r.std(ddof=1) * np.sqrt(252) * 100, 2),
        sharpe_252=round(S.sharpe_ratio(r, 252), 3),
        sharpe_obsyr=round(S.sharpe_ratio(r, obs_per_yr), 3),
        sortino_252=round(S.sortino_ratio(r, 252), 3),
        oos_sharpe_252=round(S.sharpe_ratio(oos, 252), 3),
        maxdd_pct=round(mdd * 100, 2),
        skew_daily=round(float(pd.Series(r).skew()), 3),
        kurt_daily=round(float(pd.Series(r).kurt()) + 3.0, 2),  # non-excess
        hit_daily_pct=round((r > 0).mean() * 100, 2),
        worst_day_pct=round(r.min() * 100, 2),
        dsr_90=round(dsr["dsr"], 3),
        t_hac=round(t_hac, 3),
        beta_vs_gold=round(float(reg.params[1]), 4),
        alpha_bp_day=round(float(reg.params[0]) * 1e4, 2),
        alpha_t_hac=round(float(reg.tvalues[0]), 3),
        r2_vs_gold=round(float(reg.rsquared), 4),
        wf=S.fold_metrics(r, 5, 252),
    )
    return out


def main():
    h1 = load_h1()
    h1 = h1[["open", "high", "low", "close"]].copy()
    print(f"H1 loaded: {h1.index[0]} -> {h1.index[-1]}  ({len(h1)} bars)", flush=True)
    # buy&hold gold daily close-to-close
    gold_daily = np.log(h1["close"].resample("1D").last()).diff()
    gold_daily.index = gold_daily.index.normalize()

    res = {}
    for sp in (1.0, 1.5, 2.0):
        bt = SO.backtest(h1, spread_bps=sp, swap_bps=0.0)
        net = bt["net"]
        # align gold_daily to aday index (entry UTC date)
        gd = gold_daily.reindex(net.index)
        m = metrics(net, gd, f"spread_{sp}bp")
        res[f"spread_{sp}bp"] = m
        print(f"\n=== spread {sp}bp ===")
        for k, v in m.items():
            print(f"  {k}: {v}")

    # year-by-year raw drift (pre-VT, pre-cost) + net sharpe (the report's attribution table)
    onr = SO.overnight_returns(h1)            # raw window log-return per aday
    bt15 = SO.backtest(h1, spread_bps=1.5, swap_bps=0.0)
    yearly = []
    for yr, idx in bt15.groupby(bt15.index.year).groups.items():
        seg = bt15.loc[idx]
        raw = onr.reindex(seg.index)
        yearly.append(dict(year=int(yr), n=len(seg),
                           raw_drift_bp=round(raw.mean() * 1e4, 2),
                           net_sharpe_252=round(S.sharpe_ratio(seg["net"].to_numpy(), 252), 2),
                           avg_vt=round(seg["position"].mean(), 2),
                           worst_day_pct=round(seg["net"].min() * 100, 2)))
    res["yearly_drift"] = yearly
    print("\n=== year-by-year (spread 1.5bp) ===")
    for y in yearly:
        print(f"  {y['year']}: raw {y['raw_drift_bp']:+.1f}bp  SR {y['net_sharpe_252']:+.2f}"
              f"  VT {y['avg_vt']:.2f}  worst {y['worst_day_pct']:.1f}%")

    # monthly skew (L39: report both daily and monthly)
    net15 = bt15["net"]
    monthly = (1 + net15).resample("ME").prod() - 1
    res["monthly_skew"] = round(float(monthly.skew()), 3)
    res["monthly_hit_pct"] = round((monthly > 0).mean() * 100, 2)
    res["worst_month_pct"] = round(monthly.min() * 100, 2)
    print(f"\nmonthly skew {res['monthly_skew']:+.2f}  hit {res['monthly_hit_pct']:.1f}%"
          f"  worst month {res['worst_month_pct']:.1f}%")

    (OUT / "q1_reproduction.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten {OUT/'q1_reproduction.json'}")


if __name__ == "__main__":
    main()
