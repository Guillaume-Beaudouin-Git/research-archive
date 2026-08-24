"""
K1 — Deflated Sharpe Ratio over the FULL trial count (PREREG section 1, 8).
DSR convention (stated explicitly in REPORT): the kill bar "DSR<=0" is the
deflated-Sharpe haircut, i.e. observed Sharpe - E[max SR | N_trials]; KILL if
<=0 (equivalently the Bailey-LdP PSR(E[maxSR]) <= 0.5). We also print the
Bailey-LdP DSR probability (significance reference 0.95).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from dsr import deflated_sharpe_ratio, _expected_max_sr
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from engine import Params, load_universe, simulate, build_costs, load_specs
from metrics import equity_metrics, daily_returns
import trials as T

CORE = ["NQ", "ES", "GC", "CL", "6E", "6A", "6B"]
specs = load_specs(); PER, ROLL, MULT = build_costs(specs); DATA = load_universe(CORE)
others = tuple(s for s in CORE if s != "CL")


def run(p):
    res = simulate(DATA, p, 100_000, {s: PER[s] for s in CORE}, {s: ROLL[s] for s in CORE}, MULT,
                   start="2014-01-01", end="2026-06-12")
    return daily_returns(res["equity"]), equity_metrics(res["equity"])["sharpe"]


def main():
    tl = pd.read_csv(T.TRIALS)
    dsr_trials = tl[tl["dsr_count"] == True].copy()
    # dedupe distinct backtests by (sharpe, maxdd) signature
    dsr_trials["key"] = dsr_trials["sharpe"].round(3).astype(str) + "_" + dsr_trials["maxdd"].round(3).astype(str)
    distinct = dsr_trials.drop_duplicates("key")
    N = len(distinct)
    sr_vals = distinct["sharpe"].astype(float).values
    mean_sr, std_sr = float(np.mean(sr_vals)), float(np.std(sr_vals, ddof=1))
    print(f"=== Trial ledger ===")
    print(f"  total dsr_count=True rows: {len(dsr_trials)}  |  distinct backtests N = {N}")
    print(f"  trial Sharpe distribution: mean={mean_sr:.3f} std={std_sr:.3f} "
          f"min={sr_vals.min():.2f} max={sr_vals.max():.2f}")
    emax = _expected_max_sr(N, mean_sr, std_sr)
    print(f"  E[max SR | N={N}] benchmark = {emax:.3f}  (a config must beat this for deflated value > 0)\n")

    print("=== DSR for candidate configs (periods/yr=252, excess returns rf=0) ===")
    cands = {"two_sided_base (pre-reg primary)": Params(),
             "long_only (K2 survivor)": Params(long_only=True),
             "H1b_short_CL_only (K2-fails)": Params(long_only_syms=others)}
    rows = []
    for name, p in cands.items():
        dr, sh = run(p)
        res = deflated_sharpe_ratio(dr.values, n_trials=N, periods_per_year=252, rf=0.0,
                                    mean_sr_trials=mean_sr, std_sr_trials=std_sr)
        deflated_value = sh - emax
        k1 = "KILL" if deflated_value <= 0 else "survives"
        rows.append((name, sh, deflated_value, res["dsr"], k1))
        print(f"  {name:34s} Sharpe={sh:5.2f}  deflated(SR-E[max])={deflated_value:+.2f}  "
              f"PSR(E[max])={res['dsr']:.3f}  K1={k1}")
    print(f"\n  (skew/kurt of pre-reg primary: skew={deflated_sharpe_ratio(run(Params())[0].values, N, 252, 0.0)['skewness']:.2f})")


if __name__ == "__main__":
    main()
