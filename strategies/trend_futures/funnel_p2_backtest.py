"""
Phase 2 — full event-driven backtest on the non-crypto futures CORE universe
(PREREG section 7). Single $100k account; fractional (clean signal) and
integer-micro ($100k lumpiness) variants. Accounting identity verified in V1.
Produces full metrics, per-asset + directional attribution (K2 evidence), and
saves equity/trades/metrics. Resets and seeds the trial ledger.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd

from engine import Params, load_universe, simulate, build_costs, load_specs
from metrics import equity_metrics, trade_metrics, per_asset_table
import trials

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"; RESULTS.mkdir(exist_ok=True)
CORE = ["NQ", "ES", "GC", "CL", "6E", "6A", "6B"]
START, END = "2014-01-01", "2026-06-12"


def run(p: Params, label: str, per_side, roll_bp, mult, data):
    res = simulate(data, p, 100_000, per_side, roll_bp, mult, start=START, end=END)
    ec, tr = res["equity"], res["trades"]
    em = equity_metrics(ec, rf_annual=0.0)   # engine return = futures-P&L excess return (no rf on collateral)
    tm = trade_metrics(tr)
    ec.to_parquet(RESULTS / f"equity_{label}.parquet")
    tr.to_parquet(RESULTS / f"trades_{label}.parquet")
    return res, em, tm


def directional_split(tr: pd.DataFrame):
    out = {}
    for tag, sub in [("full", tr),
                     ("2014-2019", tr[tr.exit_date < "2020-01-01"]),
                     ("2020-2026", tr[tr.exit_date >= "2020-01-01"])]:
        out[tag] = dict(long=float(sub[sub.direction > 0].pnl_net.sum()),
                        short=float(sub[sub.direction < 0].pnl_net.sum()))
    return out


def main():
    trials.reset()
    specs = load_specs()
    per_side, roll_bp, mult = build_costs(specs)
    data = load_universe(CORE)
    print("per-side cost (bp):", {s: round(per_side[s] * 1e4, 2) for s in CORE})
    print("roll cost   (bp):", {s: round(roll_bp[s] * 1e4, 2) for s in CORE})

    # --- base, cash, fractional (PRE-REGISTERED PRIMARY) ---
    res, em, tm = run(Params(max_gross=1.0, integer_contracts=False), "base_cash_frac", per_side, roll_bp, mult, data)
    print(f"\n=== BASE cash fractional (pre-registered primary) ===")
    for k in ["sharpe", "cagr", "ann_vol", "max_drawdown", "calmar", "sortino", "skew", "longest_dd_days",
              "avg_gross_exposure", "pct_days_in_market"]:
        print(f"  {k:20s} {em[k]:.3f}")
    for k in ["n_trades", "win_rate", "profit_factor", "expectancy_R", "win_loss_ratio", "avg_holding_days", "total_costs"]:
        print(f"  {k:20s} {tm[k]:.3f}")
    print(f"  roll_cost_total      {res['total_roll_cost']:.0f}")
    trials.log_trial("P2", "base_cash_frac", em["sharpe"], em["cagr"], em["max_drawdown"], tm["n_trades"],
                     dsr_count=True, notes="pre-registered primary (EMA100/20bk/3ATR/0.5pyr, two-sided)")

    pat = per_asset_table(res["trades"])
    print("\n  per-asset attribution:")
    print(pat.to_string(index=False,
          formatters={"win_rate": "{:.2f}".format, "pnl_net": "{:,.0f}".format, "profit_factor": "{:.2f}".format,
                      "avg_R": "{:.2f}".format, "long_share": "{:.2f}".format,
                      "long_pnl": "{:,.0f}".format, "short_pnl": "{:,.0f}".format}))
    ds = directional_split(res["trades"])
    print("\n  directional split (long vs short net PnL $):")
    for tag, v in ds.items():
        print(f"    {tag:10s} long={v['long']:>10,.0f}  short={v['short']:>10,.0f}")

    # --- base, cash, integer micro ($100k lumpiness) ---
    res_i, em_i, tm_i = run(Params(max_gross=1.0, integer_contracts=True), "base_cash_int", per_side, roll_bp, mult, data)
    print(f"\n=== BASE cash integer-micro ($100k lumpiness) ===")
    print(f"  sharpe={em_i['sharpe']:.3f}  cagr={em_i['cagr']:.1%}  maxDD={em_i['max_drawdown']:.1%}  "
          f"ann_vol={em_i['ann_vol']:.3f}  avg_gross={em_i['avg_gross_exposure']:.2f}  n_trades={tm_i['n_trades']}")
    print(f"  (fractional realized vol {em['ann_vol']:.3f} vs integer {em_i['ann_vol']:.3f} — lumpiness gap)")
    trials.log_trial("P2", "base_cash_int", em_i["sharpe"], em_i["cagr"], em_i["max_drawdown"], tm_i["n_trades"],
                     dsr_count=False, notes="integer-micro execution variant of base (not a new signal)")

    json.dump({"base_cash_frac": em, "base_cash_int": em_i, "trade_frac": tm,
               "directional_split": ds, "per_asset": pat.to_dict("records"),
               "per_side_bp": {s: per_side[s] * 1e4 for s in CORE}},
              open(RESULTS / "p2_summary.json", "w"), indent=2, default=str)
    print("\nsaved results/p2_summary.json + equity/trades parquet")


if __name__ == "__main__":
    main()
