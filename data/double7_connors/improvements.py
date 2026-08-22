"""Trois axes d'amélioration testés sur 2005/2006 -> 2026.

Axe 1 — Dimensionnement: vol targeting par position (sans stop), au lieu
        d'all-in par sleeve. f_t = clip(sigma_cible / sigma_realisee, 0, f_max).
Axe 2 — Logique de sortie: time-stop, sortie MA5, premier close haussier.
Axe 3 — Breadth: univers élargi à 15 instruments + analyse conditionnelle VIX.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

import data
import metrics


# ------------------------------------------------------------------ #
# State machine générique (extension du chemin rapide de research_grid)
# ------------------------------------------------------------------ #

def sleeve_run(close: np.ndarray, entry: np.ndarray, exit_: np.ndarray,
               frac: np.ndarray | None, slip: float, sleeve0: float,
               time_stop: int | None = None) -> tuple[np.ndarray, list[dict]]:
    """Sleeve avec fraction investie variable et time-stop optionnel.

    frac[i]: fraction de l'équité du sleeve investie si entrée à la barre i
             (None => all-in, comportement de base).
    time_stop: nombre max de barres en position (sortie au close).
    """
    n = len(close)
    eq = np.empty(n)
    cash, shares, entry_px, entry_bar = sleeve0, 0.0, np.nan, -1
    trades: list[dict] = []
    for i in range(n):
        px = close[i]
        if shares > 0.0:
            timed_out = time_stop is not None and (i - entry_bar) >= time_stop
            if exit_[i] or timed_out:
                fill = px * (1 - slip)
                cash += shares * fill
                trades.append(dict(ret=fill / entry_px - 1, bars=i - entry_bar,
                                   reason="time" if (timed_out and not exit_[i]) else "signal"))
                shares = 0.0
        elif entry[i]:
            f = 1.0 if frac is None else frac[i]
            if f > 0:
                entry_px = px * (1 + slip)
                notional = cash * min(f, 1.0)
                shares = notional / entry_px
                cash -= notional
                entry_bar = i
        eq[i] = cash + shares * px
    return eq, trades


def portfolio(closes: pd.DataFrame, signal_fn, frac_fn=None, slip_bps: float = 5.0,
              start: str = "2005-09-01", end: str = "2026-05-27",
              capital: float = 100_000.0, time_stop: int | None = None) -> dict:
    slip = slip_bps * 1e-4
    symbols = list(closes.columns)
    sleeve0 = capital / len(symbols)
    eqs, all_tr = [], []
    for sym in symbols:
        c = closes[sym].dropna()
        ent, exi = signal_fn(c)
        m = (c.index >= start) & (c.index <= end)
        frac = None
        if frac_fn is not None:
            frac = frac_fn(c)[m].values
        eq, tr = sleeve_run(c[m].values, ent[m].values, exi[m].values, frac, slip,
                            sleeve0, time_stop)
        eqs.append(pd.Series(eq, index=c.index[m]))
        for t in tr:
            t["symbol"] = sym
        all_tr += tr
    port = pd.concat(eqs, axis=1).ffill().bfill().sum(axis=1)
    r = port.pct_change().dropna()
    tr_df = pd.DataFrame(all_tr)
    mdd = (port / port.cummax() - 1).min()
    return dict(equity=port, trades=tr_df, cagr=metrics.cagr(port),
                sharpe=metrics.sharpe(r), sortino=metrics.sortino(r),
                max_drawdown=float(mdd),
                calmar=metrics.cagr(port) / abs(mdd),
                n_trades=len(tr_df),
                win_rate=float((tr_df.ret > 0).mean()) if len(tr_df) else np.nan,
                worst_trade=float(tr_df.ret.min()) if len(tr_df) else np.nan,
                avg_trade=float(tr_df.ret.mean()) if len(tr_df) else np.nan)


# Signaux ------------------------------------------------------------ #

def sig_double7(entry_lb=7, exit_lb=7, ma_len=200):
    def f(c: pd.Series):
        sma = c.rolling(ma_len, min_periods=ma_len).mean()
        ent = ((c <= c.rolling(entry_lb).min()) & (c > sma)).fillna(False)
        exi = (c >= c.rolling(exit_lb).max()).fillna(False)
        return ent, exi
    return f


def sig_exit_ma5(entry_lb=7, ma_len=200):
    """Sortie Connors alternative: close > SMA(5)."""
    def f(c: pd.Series):
        sma = c.rolling(ma_len, min_periods=ma_len).mean()
        ent = ((c <= c.rolling(entry_lb).min()) & (c > sma)).fillna(False)
        exi = (c > c.rolling(5).mean()).fillna(False)
        return ent, exi
    return f


def sig_exit_first_up(entry_lb=7, ma_len=200):
    """Sortie au premier close haussier (close > close[-1])."""
    def f(c: pd.Series):
        sma = c.rolling(ma_len, min_periods=ma_len).mean()
        ent = ((c <= c.rolling(entry_lb).min()) & (c > sma)).fillna(False)
        exi = (c > c.shift(1)).fillna(False)
        return ent, exi
    return f


def frac_voltarget(target_ann: float = 0.18, f_max: float = 1.0, window: int = 20):
    """Fraction investie pour viser `target_ann` de vol annualisée par position."""
    def f(c: pd.Series) -> pd.Series:
        sig = c.pct_change().rolling(window, min_periods=window).std() * np.sqrt(252)
        return (target_ann / sig).clip(upper=f_max).fillna(0.0)
    return f


def main() -> None:
    etf = data.load_etf_closes()
    out: dict[str, dict] = {}

    def record(name: str, res: dict, eq_file: str | None = None) -> None:
        if eq_file:
            res["equity"].to_csv(eq_file)
        out[name] = {k: v for k, v in res.items() if isinstance(v, (int, float))}
        print(f"{name:<34} CAGR={res['cagr']:+.2%} Sharpe={res['sharpe']:.2f} "
              f"Sortino={res['sortino']:.2f} MaxDD={res['max_drawdown']:.1%} "
              f"Calmar={res['calmar']:.2f} WR={res['win_rate']:.1%} "
              f"worst={res['worst_trade']:.1%} n={res['n_trades']}")

    # Base
    base = portfolio(etf, sig_double7())
    record("base_7_7_200", base, "eq_imp_base.csv")

    # Axe 1 — vol targeting par position (18% cible, sans levier)
    record("axe1_voltarget18", portfolio(etf, sig_double7(), frac_voltarget(0.18)),
           "eq_imp_voltarget.csv")
    record("axe1_voltarget12", portfolio(etf, sig_double7(), frac_voltarget(0.12)))

    # Axe 2 — sorties
    record("axe2_timestop10", portfolio(etf, sig_double7(), time_stop=10),
           "eq_imp_timestop.csv")
    record("axe2_timestop5", portfolio(etf, sig_double7(), time_stop=5))
    record("axe2_exit_ma5", portfolio(etf, sig_exit_ma5()))
    record("axe2_exit_firstup", portfolio(etf, sig_exit_first_up()))

    # Axe 3 — breadth: univers 15 instruments (fenêtre commune, base recalée)
    uni = data.load_extended_universe()
    S15 = "2006-12-01"
    record("axe3_univers15", portfolio(uni, sig_double7(), start=S15),
           "eq_imp_univers15.csv")
    record("base_3etf_meme_fenetre", portfolio(etf, sig_double7(), start=S15))
    # combo: breadth + vol target + time stop
    record("combo_15_volt_ts10",
           portfolio(uni, sig_double7(), frac_voltarget(0.18), start=S15, time_stop=10),
           "eq_imp_combo.csv")

    json.dump(out, open("results_improvements.json", "w"), indent=1, default=float)
    print("saved results_improvements.json")


if __name__ == "__main__":
    main()
