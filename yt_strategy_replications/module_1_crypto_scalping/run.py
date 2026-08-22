"""
Module 1 runner. For each strategy: backtest across the whole crypto universe
(not one cherry-picked instrument), then build an equal-weight portfolio of the
per-instrument daily realized returns. The portfolio is the honest edge test —
a real edge survives across instruments; a cherry-pick washes out.

Crucially we decompose GROSS (cost=0) vs NET (0.17% round trip) so we can tell
"no predictive edge" apart from "edge exists but trades too often for the cost".

Usage:
    python run.py S1_momentum_breakout S2_sma50_100_cross   # subset
    python run.py ALL
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # project root -> `engine`
sys.path.insert(0, str(HERE))         # module dir   -> `strategies`
from engine import data, backtest as bt, stats as S  # noqa: E402
from strategies import STRATEGIES, COST_RT  # noqa: E402

RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
ANN = 365.0
N_CONFIGS = len(STRATEGIES) * len(data.UNIVERSE)
PAIR_COLS = ["strategy", "pair", "n_trades", "total_return", "sharpe", "max_drawdown",
             "profit_factor", "win_rate", "expectancy", "hac_tstat", "wf_score",
             "avg_bars_held", "pct_long", "frac_tp", "buy_hold_return"]


def _daily(trades, df, col):
    days, _, _ = bt._trading_days_per_year(df.index)
    if trades.empty:
        return pd.Series(0.0, index=days)
    s = (pd.Series(trades[col].to_numpy(float),
                   index=pd.DatetimeIndex(trades["exit_time"]).normalize())
         .groupby(level=0).sum())
    return s.reindex(days, fill_value=0.0)


def run_one(name: str) -> dict:
    cfg = STRATEGIES[name]
    rows, snet, sgross = [], {}, {}
    tot_gross = tot_net = 0.0
    tot_tr = 0
    for pair in data.UNIVERSE:
        df = data.load_crypto(pair)
        sig = cfg["fn"](df)
        tr = bt.run_backtest(df, sig, sl_pct=cfg["sl"], tp_pct=cfg["tp"],
                             cost_rt=COST_RT, allow_long=True, allow_short=cfg["allow_short"])
        m = bt.compute_metrics(tr, df, n_trials=N_CONFIGS, label=f"{name}:{pair}", bootstrap=False)
        m["pair"], m["strategy"] = pair, name
        rows.append(m)
        snet[pair] = _daily(tr, df, "ret_net")
        sgross[pair] = _daily(tr, df, "ret_gross")
        if len(tr):
            tot_gross += float(tr["ret_gross"].sum())
            tot_net += float(tr["ret_net"].sum())
            tot_tr += len(tr)

    pairs_df = pd.DataFrame(rows)[PAIR_COLS]
    pairs_df.to_csv(RESULTS / f"{name}_pairs.csv", index=False)

    net = pd.DataFrame(snet).sort_index().mean(axis=1, skipna=True)
    gross = pd.DataFrame(sgross).sort_index().mean(axis=1, skipna=True)
    nv, gv = net.to_numpy(float), gross.to_numpy(float)
    eq = (1 + net.fillna(0)).cumprod()
    years = max(len(net) / ANN, 1e-9)
    dsr = S.deflated_sharpe_ratio(nv, n_trials=len(STRATEGIES), periods_per_year=ANN)
    _, hac_net = S.hac_tstat(nv)
    _, hac_gross = S.hac_tstat(gv)
    mdd, _ = S.max_drawdown(eq.to_numpy(float))
    folds = S.fold_metrics(nv, 5, ANN)
    pf_series = pairs_df["profit_factor"].replace([np.inf, -np.inf], np.nan)

    summary = dict(
        strategy=name, n_pairs=len(data.UNIVERSE), total_trades=int(tot_tr),
        trades_per_pair_per_year=float(tot_tr / len(data.UNIVERSE) / years),
        expectancy_gross_bps=float(1e4 * tot_gross / tot_tr) if tot_tr else float("nan"),
        expectancy_net_bps=float(1e4 * tot_net / tot_tr) if tot_tr else float("nan"),
        port_sharpe_gross=float(S.sharpe_ratio(gv, ANN)),
        port_sharpe_net=float(S.sharpe_ratio(nv, ANN)),
        port_hac_t_gross=float(hac_gross), port_hac_t_net=float(hac_net),
        median_pair_sharpe_net=float(pairs_df["sharpe"].median()),
        frac_pairs_positive_net=float((pairs_df["sharpe"] > 0).mean()),
        best_pair=str(pairs_df.loc[pairs_df["sharpe"].idxmax(), "pair"]),
        best_pair_sharpe_net=float(pairs_df["sharpe"].max()),
        worst_pair_sharpe_net=float(pairs_df["sharpe"].min()),
        median_win_rate=float(pairs_df["win_rate"].median()),
        median_profit_factor=float(pf_series.median()),
        port_maxdd=float(mdd), port_total_return=float(eq.iloc[-1] - 1),
        port_cagr=float(eq.iloc[-1] ** (1 / years) - 1),
        port_dsr=float(dsr.get("dsr", float("nan"))),
        port_sr_annual=float(dsr.get("sr_annual", float("nan"))),
        port_sr0_annual=float(dsr.get("sr0_annual", float("nan"))),
        port_bootstrap_p=float(S.stationary_bootstrap_pvalue(nv)),
        wf_score=float(folds["wf_score"]), fold_sharpes=folds["fold_sharpes"],
        avg_buy_hold=float(pairs_df["buy_hold_return"].mean()),
        cost_rt=COST_RT, sl=cfg["sl"], tp=cfg["tp"], allow_short=cfg["allow_short"],
    )
    eq.to_frame("equity").to_parquet(RESULTS / f"{name}_equity.parquet")
    net.to_frame("port_daily").to_parquet(RESULTS / f"{name}_portdaily.parquet")
    gross.to_frame("port_gross").to_parquet(RESULTS / f"{name}_portgross.parquet")
    with open(RESULTS / f"{name}_port.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"[{name}] Sharpe gross={summary['port_sharpe_gross']:+.2f} net={summary['port_sharpe_net']:+.2f} | "
          f"E[trade] gross={summary['expectancy_gross_bps']:+.1f}bps net={summary['expectancy_net_bps']:+.1f}bps | "
          f"tr/pair/yr={summary['trades_per_pair_per_year']:.0f} | best={summary['best_pair']}"
          f"({summary['best_pair_sharpe_net']:+.2f}) fracPos={summary['frac_pairs_positive_net']:.0%} | "
          f"DSR={summary['port_dsr']:.2f}")
    return summary


if __name__ == "__main__":
    args = sys.argv[1:] or ["ALL"]
    names = list(STRATEGIES) if args == ["ALL"] else [a for a in args if a in STRATEGIES]
    for nm in names:
        run_one(nm)
