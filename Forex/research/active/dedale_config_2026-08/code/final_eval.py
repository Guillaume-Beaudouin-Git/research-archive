"""
Single, pre-committed harness evaluation of ONE candidate config (chosen by minimal distance to
the author's declared metadata in config_search_results.csv / combo_search_results.csv -- NEVER
by Sharpe/P&L). Run exactly once per candidate reported in RAPPORT.md.

Usage: /usr/bin/python3 final_eval.py "TDI_TIMEFRAME0_CROSS+TDI_TIMEFRAME4_CROSS"
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import search_engine as se  # noqa: E402
import dedale_engine as de  # noqa: E402

ENGINE_DIR = Path("<HOME>/Desktop/Algo_claude_dedale2/Forex/research/active/"
                   "dedale_strategy_2026-08/code")
sys.path.insert(0, str(ENGINE_DIR))
import metrics as me  # noqa: E402

OUT_DIR = HERE.parent


def parse_config(name: str) -> set:
    if name in ("A_no_filter", "", None):
        return set()
    fset = set()
    for tok in name.split("+"):
        # TDI_TIMEFRAMEk_KIND
        rest = tok.replace("TDI_TIMEFRAME", "")
        tf_str, kind = rest.split("_", 1)
        fset.add((int(tf_str), kind))
    return fset


def main(config_name: str):
    fset = parse_config(config_name)
    print(f"Evaluating config: {config_name} -> {sorted(fset)}")
    tf_cache = {}
    summ, all_trades = se.run_config(fset, tf_cache=tf_cache, verbose=True)
    print("Search-stage summary (identification metrics):", summ)
    all_trades.to_csv(OUT_DIR / f"trades_final_{config_name.replace('+','_')}.csv", index=False)

    rf = me.load_rf()
    scenarios = [
        ("gross", 0.0, 1.0),
        ("eightcap_raw", 0.75, 0.85),
        ("ftmo_retail", 2.48, 0.85),
    ]
    rows = []
    tpy = summ["trades_per_pair_year"] * 7  # total trades/year across the 7-pair reproduction
    for label, cost_bps, haircut in scenarios:
        d = me.add_pnl(all_trades, rf, cost_bps=cost_bps, swap_haircut=haircut)
        sh_net_swap = me.sharpe_annualized(d["pnl_net_swap"].values, tpy)
        sh_excess = me.sharpe_annualized(d["pnl_net_swap_excess"].values, tpy)
        mean_r, t, n = me.hac_tstat(d["pnl_net_swap_excess"].values)
        swap_share = d["pnl_swap_only"].sum() / d["pnl_net_swap"].sum() if d["pnl_net_swap"].sum() != 0 else np.nan
        rows.append(dict(scenario=label, cost_bps=cost_bps, haircut=haircut, n=len(d),
                          sharpe_net_swap=sh_net_swap, sharpe_excess=sh_excess,
                          hac_t=t, swap_share_of_net=swap_share,
                          net_pnl_sum=d["pnl_net_swap"].sum(), gross_pnl_sum=d["pnl_gross"].sum(),
                          swap_pnl_sum=d["pnl_swap_only"].sum(), cost_pnl_sum=-d["pnl_cost_only"].sum()))
        if label == "ftmo_retail":
            ts = me.two_sided(d, "pnl_net_swap_excess", tpy)
            ts.to_csv(OUT_DIR / f"twosided_final_{config_name.replace('+','_')}.csv", index=False)
            rg = me.regime_split(d, "pnl_net_swap_excess")
            rg.to_csv(OUT_DIR / f"regime_final_{config_name.replace('+','_')}.csv", index=False)
            print("Two-sided:\n", ts)
            print("Regime split:\n", rg)

    res = pd.DataFrame(rows)
    res.to_csv(OUT_DIR / f"final_eval_{config_name.replace('+','_')}.csv", index=False)
    print(res.to_string())


if __name__ == "__main__":
    main(sys.argv[1])
