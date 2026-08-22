"""Audit 4/4 — Stress tests de crise, analyse de drawdown, tail risk.

- Performance sur fenêtres de crise nommées (GFC, taper, Q4-2018, COVID,
  2022, etc.), comparée au buy & hold sur la même fenêtre.
- Top drawdowns: amplitude, durée, temps de récupération.
- Tail risk quotidien: VaR/CVaR 95/99, pire jour, pires séquences.
- Pertes consécutives (trades), recovery factor, Ulcer index.
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd

import data

TD = 252


def drawdown_table(equity: pd.Series, top=6) -> pd.DataFrame:
    dd = equity / equity.cummax() - 1
    is_dd = dd < 0
    groups, start = [], None
    for t, v in is_dd.items():
        if v and start is None:
            start = t
        elif not v and start is not None:
            groups.append((start, t)); start = None
    if start is not None:
        groups.append((start, equity.index[-1]))
    rows = []
    for a, b in groups:
        seg = dd.loc[a:b]
        trough = seg.idxmin()
        depth = seg.min()
        peak_val = equity.loc[a:trough].iloc[0]
        rec = equity.loc[trough:b]
        recovered = rec[rec >= peak_val]
        rec_date = recovered.index[0] if len(recovered) else None
        rows.append(dict(start=a.date(), trough=trough.date(),
                         end=(rec_date.date() if rec_date is not None else None),
                         depth=float(depth),
                         length_days=int((trough - a).days),
                         recovery_days=int((rec_date - trough).days) if rec_date is not None else None,
                         total_days=int(((rec_date or b) - a).days)))
    return pd.DataFrame(rows).sort_values("depth").head(top).reset_index(drop=True)


def crisis_windows(equity: pd.Series, bh: pd.Series):
    wins = {
        "GFC 2007-2009": ("2007-10-09", "2009-03-09"),
        "Flash crash 2010": ("2010-04-23", "2010-07-02"),
        "Crise zone euro 2011": ("2011-05-02", "2011-10-03"),
        "Taper tantrum 2013": ("2013-05-22", "2013-06-24"),
        "Devaluation yuan 2015": ("2015-08-10", "2015-08-25"),
        "Q4 2018 selloff": ("2018-10-01", "2018-12-24"),
        "COVID crash 2020": ("2020-02-19", "2020-03-23"),
        "Bear 2022": ("2022-01-03", "2022-10-12"),
        "Hausse taux 2023 (SVB)": ("2023-03-01", "2023-03-15"),
    }
    rows = []
    for name, (a, b) in wins.items():
        if pd.Timestamp(a) < equity.index[0]:
            continue
        es = equity.loc[a:b]; bs = bh.loc[a:b]
        if len(es) < 2:
            continue
        s_ret = es.iloc[-1] / es.iloc[0] - 1
        b_ret = bs.iloc[-1] / bs.iloc[0] - 1
        s_dd = (es / es.cummax() - 1).min()
        rows.append(dict(crise=name, debut=a, fin=b,
                         strat_ret=float(s_ret), bh_ret=float(b_ret),
                         strat_dd=float(s_dd),
                         protection=float(s_ret - b_ret)))
    return pd.DataFrame(rows)


def tail_metrics(rets: pd.Series):
    r = rets.values
    var95 = np.percentile(r, 5); var99 = np.percentile(r, 1)
    cvar95 = r[r <= var95].mean(); cvar99 = r[r <= var99].mean()
    dd = (1 + rets).cumprod()
    dd = dd / dd.cummax() - 1
    ulcer = np.sqrt(np.mean(dd.values ** 2))
    return dict(worst_day=float(r.min()), best_day=float(r.max()),
                var95=float(var95), cvar95=float(cvar95),
                var99=float(var99), cvar99=float(cvar99),
                ulcer_index=float(ulcer),
                downside_days=float((r < 0).mean()))


def consecutive_losses(trade_rets: np.ndarray):
    max_streak = streak = 0
    cur_dd = worst_run = 0.0
    for x in trade_rets:
        if x <= 0:
            streak += 1; cur_dd += x
            max_streak = max(max_streak, streak)
            worst_run = min(worst_run, cur_dd)
        else:
            streak = 0; cur_dd = 0.0
    return dict(max_consecutive_losses=int(max_streak),
                worst_losing_run_ret=float(worst_run))


def main():
    eq = pd.read_csv("eq_full_sleeves.csv", index_col=0, parse_dates=True).iloc[:, 0]
    bh = pd.read_csv("eq_full_bh.csv", index_col=0, parse_dates=True).iloc[:, 0]
    rets = eq.pct_change().dropna()
    tr = pd.read_csv("trades_full_sleeves.csv").dropna(subset=["pnl"])

    print("=== Top drawdowns ===")
    ddt = drawdown_table(eq, top=6)
    print(ddt.to_string(index=False))

    print("\n=== Fenêtres de crise (stratégie vs buy & hold) ===")
    cw = crisis_windows(eq, bh)
    print(cw.to_string(index=False, float_format=lambda x: f"{x:+.1%}"))

    print("\n=== Tail risk quotidien ===")
    tm = tail_metrics(rets)
    for k, v in tm.items():
        print(f"  {k}: {v:.4f}")

    print("\n=== Séquences de pertes ===")
    cl = consecutive_losses(tr.sort_values("exit_date")["ret"].values)
    print(f"  pertes consécutives max: {cl['max_consecutive_losses']} trades")
    rec_factor = (eq.iloc[-1] / eq.iloc[0] - 1) / abs((eq / eq.cummax() - 1).min())
    print(f"  recovery factor (tot ret / maxDD): {rec_factor:.2f}")
    print(f"  Ulcer index: {tm['ulcer_index']:.4f}")

    out = dict(top_drawdowns=ddt.assign(start=ddt.start.astype(str), trough=ddt.trough.astype(str),
                                        end=ddt.end.astype(str)).to_dict("records"),
               crisis=cw.to_dict("records"),
               tail=tm, consecutive=cl, recovery_factor=float(rec_factor))
    json.dump(out, open("audit_stress.json", "w"), indent=1, default=str)
    np.save("dd_series.npy", (eq / eq.cummax() - 1).values)
    pd.Series((eq / eq.cummax() - 1).values, index=eq.index).to_csv("underwater.csv")
    print("\nsaved audit_stress.json")


if __name__ == "__main__":
    main()
