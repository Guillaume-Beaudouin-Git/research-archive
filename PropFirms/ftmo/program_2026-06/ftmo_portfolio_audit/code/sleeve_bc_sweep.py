"""
sleeve_bc_sweep.py — charitable parameter sweep for Sleeves B (BTC mom) & C (US30 MR).
Goal: does ANY reasonable config reproduce report (C ~+1.0 OOS pos-every-year; B ~+0.5 OOS)?
Loads each M1 once; re-resamples per freq.
"""
from __future__ import annotations
import itertools
import numpy as np, pandas as pd
from audit_common import load_m1, metrics, per_year_sharpe
from sleeve_bc import build_bars, backtest


def sweep(m1, sym, mode, freqs, windows, sessions, zentries, stops, markups, comm, drop_we, tag):
    best = []
    bars_cache = {}
    for freq, sess in itertools.product(freqs, sessions):
        key = (freq, sess)
        if key not in bars_cache:
            bars_cache[key] = build_bars(m1, freq, sess[0], sess[1], drop_weekend=drop_we)
        bars = bars_cache[key]
        for win, ze, stop, mk in itertools.product(windows, zentries, stops, markups):
            try:
                res = backtest(bars, sym, mode, window=win, z_entry=ze, daily_stop=stop,
                               markup=mk, commission_rt=comm)
            except Exception:
                continue
            net = res["net"]
            mf = metrics(net.loc["2022-01-01":"2026-06-05"])
            mo = metrics(net.loc["2025-01-01":"2026-06-05"])
            yr = per_year_sharpe(net.loc["2022-01-01":"2026-06-05"])
            allpos = all(v > 0 for v in yr.values()) if yr else False
            best.append((mf.get("ann_sharpe", -9), mo.get("ann_sharpe", -9), allpos,
                         f"{freq} sess{sess} w{win} z{ze} stop{stop} mk{mk}",
                         {k: round(v, 2) for k, v in yr.items()}))
    best.sort(key=lambda x: x[1], reverse=True)   # rank by OOS Sharpe
    print(f"\n===== {tag} — top 8 by OOS Sharpe =====")
    print(f"{'fullSh':>7s} {'oosSh':>6s} {'allyr+':>6s}  config")
    for r in best[:8]:
        print(f"{r[0]:>7.2f} {r[1]:>6.2f} {str(r[2]):>6s}  {r[3]}   {r[4]}")
    return best


def main():
    print("loading US30 deep ...", flush=True)
    us30 = load_m1("US30", "deep")
    sweep(us30, "US30", "mr",
          freqs=["30min", "60min", "120min"], windows=[12, 16, 24, 32],
          sessions=[(13, 20), (13, 21), (14, 21), (8, 21)],
          zentries=[1.5, 2.0, 2.5], stops=[0.01, 0.02, 0.03], markups=[2.0],
          comm=0.0, drop_we=True, tag="Sleeve C US30 MR")

    print("\nloading BTC panel ...", flush=True)
    btc = load_m1("BTCUSD", "panel")
    sweep(btc, "BTCUSD", "mom",
          freqs=["60min", "120min", "240min"], windows=[12, 16, 24],
          sessions=[(0, 21), (0, 24)],
          zentries=[1.5, 2.0, 2.5], stops=[0.02, 0.03], markups=[2.0],
          comm=0.00065, drop_we=False, tag="Sleeve B BTC momentum (panel)")
    # also test BTC as MEAN-REVERSION (in case report's 'momentum direction' is mislabeled)
    sweep(btc, "BTCUSD", "mr",
          freqs=["60min", "120min"], windows=[16, 24],
          sessions=[(0, 21)], zentries=[2.0], stops=[0.02], markups=[2.0],
          comm=0.00065, drop_we=False, tag="Sleeve B BTC AS-MR (sanity)")


if __name__ == "__main__":
    main()
