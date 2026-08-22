"""Robustesse: grille de paramètres, sensibilité aux coûts, cross-check CFD.

Chemin rapide numpy (state machine vectorisée par symbole) — mêmes conventions
que engine.backtest_sleeves (fills au close du signal, slippage par côté).
Validé contre le moteur de référence dans tests_validation.py.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

import data
import metrics


def fast_sleeve_equity(close: np.ndarray, entry: np.ndarray, exit_: np.ndarray,
                       slip: float, sleeve0: float) -> tuple[np.ndarray, list[float]]:
    """Équité d'un sleeve all-in/all-out + liste des rendements de trades."""
    n = len(close)
    eq = np.empty(n)
    cash, shares, entry_px = sleeve0, 0.0, np.nan
    trade_rets: list[float] = []
    for i in range(n):
        px = close[i]
        if shares > 0.0 and exit_[i]:
            fill = px * (1 - slip)
            cash, shares = shares * fill, 0.0
            trade_rets.append(fill / entry_px - 1)
        elif shares == 0.0 and entry[i]:
            entry_px = px * (1 + slip)
            shares, cash = cash / entry_px, 0.0
        eq[i] = cash + shares * px
    return eq, trade_rets


def run_config(closes: pd.DataFrame, entry_lb: int, exit_lb: int, ma_len: int,
               slippage_bps: float, start: str, end: str,
               capital: float = 100_000.0) -> dict:
    slip = slippage_bps * 1e-4
    symbols = list(closes.columns)
    sleeve0 = capital / len(symbols)
    eqs, all_rets = [], []
    for sym in symbols:
        c_full = closes[sym].dropna()
        sma = c_full.rolling(ma_len, min_periods=ma_len).mean()
        ent = (c_full <= c_full.rolling(entry_lb).min()) & (c_full > sma)
        exi = c_full >= c_full.rolling(exit_lb).max()
        m = (c_full.index >= start) & (c_full.index <= end)
        eq, tr = fast_sleeve_equity(c_full[m].values, ent[m].values, exi[m].values,
                                    slip, sleeve0)
        eqs.append(pd.Series(eq, index=c_full.index[m]))
        all_rets += tr
    port = pd.concat(eqs, axis=1).ffill().bfill().sum(axis=1)
    r = port.pct_change().dropna()
    tr_arr = np.array(all_rets)
    mdd = (port / port.cummax() - 1).min()
    return {
        "entry_lb": entry_lb, "exit_lb": exit_lb, "ma_len": ma_len,
        "slippage_bps": slippage_bps,
        "cagr": metrics.cagr(port), "sharpe": metrics.sharpe(r),
        "max_drawdown": float(mdd),
        "n_trades": int(len(tr_arr)),
        "win_rate": float((tr_arr > 0).mean()) if len(tr_arr) else np.nan,
        "avg_trade_ret": float(tr_arr.mean()) if len(tr_arr) else np.nan,
        "equity": port,
    }


def main() -> None:
    etf = data.load_etf_closes()
    START, END = "2005-09-01", "2026-05-27"

    # 1) Grille entry x exit x MA (slippage fixe 5 bps)
    rows = []
    for ma in (100, 150, 200):
        for e_in in range(5, 11):
            for e_out in range(5, 11):
                r = run_config(etf, e_in, e_out, ma, 5.0, START, END)
                r.pop("equity")
                rows.append(r)
    grid = pd.DataFrame(rows)
    grid.to_csv("grid_results.csv", index=False)
    print("Grille:", len(grid), "configs | Sharpe min/med/max:",
          f"{grid.sharpe.min():.2f}/{grid.sharpe.median():.2f}/{grid.sharpe.max():.2f}")
    base = grid.query("entry_lb==7 and exit_lb==7 and ma_len==200").iloc[0]
    print(f"Base 7/7/200: Sharpe={base.sharpe:.2f} | rang percentile="
          f"{(grid.sharpe < base.sharpe).mean():.0%}")

    # 2) Sensibilité aux coûts
    cost_rows = []
    for bps in (0.0, 2.5, 5.0, 10.0, 20.0):
        r = run_config(etf, 7, 7, 200, bps, START, END)
        r.pop("equity")
        cost_rows.append(r)
    costs = pd.DataFrame(cost_rows)
    costs.to_csv("cost_sensitivity.csv", index=False)
    print("\nCoûts:")
    print(costs[["slippage_bps", "cagr", "sharpe", "win_rate"]].to_string(index=False))

    # 3) Cross-check CFD (US500/US100/XAUUSD) — autre source, autre venue
    cfd = data.load_cfd_ohlc()
    cfd_closes = pd.DataFrame({k: v["close"] for k, v in cfd.items()}).dropna()
    res_cfd = run_config(cfd_closes, 7, 7, 200, 5.0, "2008-01-01", "2026-06-05")
    eq_cfd = res_cfd.pop("equity")
    eq_cfd.to_csv("eq_cfd_sleeves.csv")
    # comparaison ETF même fenêtre
    res_etf_match = run_config(etf, 7, 7, 200, 5.0, "2008-01-01", "2026-05-27")
    res_etf_match.pop("equity")
    json.dump({"cfd": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                       for k, v in res_cfd.items()},
               "etf_same_window": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                                   for k, v in res_etf_match.items()}},
              open("results_cfd.json", "w"), indent=1)
    print("\nCFD 2008-2026:", {k: round(v, 3) for k, v in res_cfd.items()
                               if isinstance(v, (int, float))})
    print("ETF 2008-2026:", {k: round(v, 3) for k, v in res_etf_match.items()
                             if isinstance(v, (int, float))})


if __name__ == "__main__":
    main()
