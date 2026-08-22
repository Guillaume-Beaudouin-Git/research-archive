"""
Module 2 runner — pin-bar + EMA trend filter.

Replicates the video's two phases on gold H1 (Phase 1 = all pins, Phase 2 = trend-
filtered), then stress-tests: full 19-year sample vs recent 6y, cost sensitivity,
walk-forward, and a cross-instrument generalisation test (a real rejection-candle
edge should not be unique to gold).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from engine import data, backtest as bt, stats as S  # noqa: E402
from strategy import detect_pin_bars, apply_trend_filter, atr_distances, PARAMS  # noqa: E402

RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
COST_RT = 0.0003   # ~3 bps round-trip baseline (realistic gold/indices; conservative for FX)
N_TRIALS = 10
INSTR = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "US500", "US100", "USOIL"]


def run_bt(df, sig, cost_rt=COST_RT):
    sl, tp = atr_distances(df, PARAMS["atr_n"], PARAMS["atr_mult"], PARAMS["rr"])
    return bt.run_backtest(df, sig, sl_dist=sl, tp_dist=tp, cost_rt=cost_rt,
                           max_hold=PARAMS["max_hold"])


def signals(df):
    pin = detect_pin_bars(df, PARAMS["wick_ratio"], PARAMS["body_max_frac"])
    filt = apply_trend_filter(df, pin, PARAMS["ema_fast"], PARAMS["ema_slow"])
    return pin, filt


def main():
    gold = data.load_h1("XAUUSD")
    pin, filt = signals(gold)

    # --- Phase 1 vs Phase 2, full sample and recent 6y ---
    samples = {"full_2007_2026": (None, None), "recent_6y": ("2020-06-05", None)}
    rows = []
    for sname, (a, b) in samples.items():
        sub = gold.loc[(a or gold.index[0]):(b or gold.index[-1])]
        for phase, sg in [("phase1_raw_pins", pin.reindex(sub.index)),
                          ("phase2_trend_filter", filt.reindex(sub.index))]:
            tr = run_bt(sub, sg)
            m = bt.compute_metrics(tr, sub, n_trials=N_TRIALS, label=f"{phase}:{sname}",
                                   bootstrap=(sname == "full_2007_2026"))
            m["phase"], m["sample"] = phase, sname
            rows.append(m)
    res = pd.DataFrame(rows)
    cols = ["sample", "phase", "n_trades", "total_return", "buy_hold_return", "cagr",
            "sharpe", "max_drawdown", "profit_factor", "win_rate", "hac_tstat",
            "wf_score", "dsr", "bootstrap_p", "frac_tp"]
    res[cols].to_csv(RESULTS / "module2_gold_summary.csv", index=False)
    print(res[cols].to_string(index=False))

    # --- cost sensitivity (phase 2, full) ---
    print("\n=== cost sensitivity (phase2 full) ===")
    sens = []
    for c in [0.0, 0.0002, 0.0003, 0.0005, 0.001]:
        m = bt.compute_metrics(run_bt(gold, filt, cost_rt=c), gold, n_trials=N_TRIALS,
                               bootstrap=False)
        sens.append(dict(cost_bps=c * 1e4, sharpe=m["sharpe"], total_return=m["total_return"],
                         hac_t=m["hac_tstat"], n_trades=m["n_trades"]))
        print(f"  cost={c*1e4:4.1f}bps  Sharpe={m['sharpe']:+.2f}  totRet={m['total_return']:+.1%}  HAC_t={m['hac_tstat']:+.2f}")
    pd.DataFrame(sens).to_csv(RESULTS / "module2_cost_sensitivity.csv", index=False)

    # --- cross-instrument generalisation (phase 2, full, 3bps) ---
    print("\n=== cross-instrument (phase2, full, 3bps) ===")
    cross = []
    for sym in INSTR:
        try:
            d = data.load_h1(sym)
        except FileNotFoundError:
            continue
        _, fl = signals(d)
        m = bt.compute_metrics(run_bt(d, fl), d, n_trials=N_TRIALS, bootstrap=False)
        cross.append(dict(symbol=sym, n_trades=m["n_trades"], sharpe=m["sharpe"],
                          hac_t=m["hac_tstat"], total_return=m["total_return"],
                          buy_hold=m["buy_hold_return"], win_rate=m["win_rate"],
                          pf=m["profit_factor"], maxdd=m["max_drawdown"], wf=m["wf_score"]))
        print(f"  {sym}: nTr={m['n_trades']:5d}  Sharpe={m['sharpe']:+.2f}  HAC_t={m['hac_tstat']:+.2f}  "
              f"totRet={m['total_return']:+.0%}  PF={m['profit_factor']:.2f}  WF={m['wf_score']:.0%}")
    cross_df = pd.DataFrame(cross)
    cross_df.to_csv(RESULTS / "module2_cross_instrument.csv", index=False)
    json.dump({"cost_rt": COST_RT, "params": PARAMS,
               "median_cross_sharpe": float(cross_df["sharpe"].median()),
               "frac_instruments_positive": float((cross_df["sharpe"] > 0).mean())},
              open(RESULTS / "module2_meta.json", "w"), indent=2)

    # --- figures ---
    eq1 = bt.equity_curves(run_bt(gold, pin), gold)
    eq2 = bt.equity_curves(run_bt(gold, filt), gold)
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(eq2.index, eq2["strategy"], label="Phase 2 (trend filter)", color="seagreen", lw=1.4)
    ax.plot(eq1.index, eq1["strategy"], label="Phase 1 (all pins)", color="indianred", lw=1.2)
    ax.plot(eq2.index, eq2["buy_hold"], label="Buy & hold gold", color="gray", ls="--", lw=1.0)
    ax.set_yscale("log")
    ax.set_title("Module 2 — gold H1 pin-bar strategy equity (net 3 bps), 2007–2026")
    ax.set_ylabel("Equity (×, log)")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_A_gold_equity.png", dpi=120)
    plt.close(fig)

    cs = cross_df.sort_values("sharpe")
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.barh(cs["symbol"], cs["sharpe"],
            color=["seagreen" if v > 0 else "indianred" for v in cs["sharpe"]])
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title("Module 2 — phase-2 net Sharpe by instrument (H1, 3 bps)")
    ax.set_xlabel("Annualised Sharpe (net)")
    ax.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_B_cross_instrument.png", dpi=120)
    plt.close(fig)
    print("\nfigures:", [p.name for p in sorted(RESULTS.glob('fig_*.png'))])


if __name__ == "__main__":
    main()
