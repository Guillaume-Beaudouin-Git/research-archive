"""
Re-run of the CONFIRMED 8-filter config (see eval_confirmed.py / RAPPORT.md sec5) on an EXTENDED
10-pair universe: the 7 original majors + EURJPY, AUDJPY, EURGBP (M1 parquet caches built from
data/deep_history_utc/ for this run -- previously missing from the scratchpad cache, not a data
gap in the repo itself).

Delta n_tests = 0: same hypothesis, same configuration, universe corrected for a caching omission,
not a new/independent test.

EURJPY is reported SEPARATELY throughout (the pair the author names explicitly as return-driving),
including a decomposition of price vs swap P&L and an explicit check of whether the SHORT leg
exists at all under the swap veto (IS_NEGSWAP_ALLOWED=false) -- the falsification test requested:
if EURJPY only ever trades long under the veto, this is a long-only exposure to a trending asset,
not a two-sided technical edge (L25).
"""
import sys
import math
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

CONFIRMED = {(3, "CROSS"), (3, "TREND"), (4, "TREND"),
             (0, "ANGLE"), (1, "ANGLE"), (2, "ANGLE"), (3, "ANGLE"), (4, "ANGLE")}

# extend the shared engine's pair universe WITHOUT modifying its source file
de.PAIR_CCY.update({
    "EURJPY": ("EUR", "JPY"),
    "AUDJPY": ("AUD", "JPY"),
    "EURGBP": ("EUR", "GBP"),
})
EXTENDED_PAIRS = de.PAIRS + ["EURJPY", "AUDJPY", "EURGBP"]
N_PAIRS = len(EXTENDED_PAIRS)

PRIMARY_START = pd.Timestamp("2018-01-05", tz="UTC")
PRIMARY_END = pd.Timestamp("2024-07-29", tz="UTC")
TARGET = dict(trades_per_pair_year=3.5, win_rate=63.58, hold_days=11.0, worst_trade_pct=-1.27,
              vol_annual_pct=10.91, total_return_pct=60.33)


def fidelity_block(trades: pd.DataFrame, label: str, n_years: float, n_pairs: int, risk_pct=1.0):
    if trades.empty:
        print(f"[{label}] NO TRADES")
        return {}
    n = len(trades)
    tpy = n / (n_pairs * n_years)
    win_rate = (trades["r_multiple"] > 0).mean() * 100.0
    hold = trades["hold_days"].mean()
    worst = trades["r_multiple"].min() * risk_pct

    rf = me.load_rf()
    d = me.add_pnl(trades.sort_values("exit_time"), rf, cost_bps=0.0, swap_haircut=0.85)
    r = d["pnl_net_swap"].values
    bal = np.cumprod(1.0 + r)
    total_return_pct = (bal[-1] - 1.0) * 100.0 if len(bal) else np.nan
    vol_buggy_pct = np.std(r, ddof=1) * math.sqrt(252) * 100.0 if len(r) > 5 else np.nan
    tpy_total = len(d) / n_years
    vol_correct_pct = np.std(r, ddof=1) * math.sqrt(tpy_total) * 100.0 if len(r) > 5 else np.nan

    row = dict(label=label, n=n, trades_per_pair_year=tpy, win_rate=win_rate, hold_days=hold,
               worst_trade_pct=worst, vol_annual_pct_author_convention=vol_buggy_pct,
               vol_annual_pct_correct=vol_correct_pct, total_return_pct=total_return_pct)
    print(f"--- Fidelity [{label}] (n_pairs={n_pairs}) ---")
    for k, v in row.items():
        if k == "label":
            continue
        tgt = TARGET.get(k) or TARGET.get(k.replace("_author_convention", "").replace("_correct", ""))
        print(f"  {k}: {v:.3f}" + (f"   (cible {tgt})" if tgt is not None else ""))
    return row


def eurjpy_breakdown(trades: pd.DataFrame, label: str):
    ej = trades[trades["pair"] == "EURJPY"].copy()
    print(f"\n=== EURJPY breakdown [{label}] === n={len(ej)}")
    if ej.empty:
        print("  NO EURJPY TRADES")
        return dict(label=label, n=0)
    n_buy = (ej["direction"] == "buy").sum()
    n_sell = (ej["direction"] == "sell").sum()
    print(f"  direction counts: buy={n_buy} sell={n_sell}  <-- falsification check: does short exist?")

    rf = me.load_rf()
    d = me.add_pnl(ej.sort_values("exit_time"), rf, cost_bps=2.48, swap_haircut=0.85)
    gross_sum = d["pnl_gross"].sum()
    swap_sum = d["pnl_swap_only"].sum()
    cost_sum = d["pnl_cost_only"].sum()
    net_sum = d["pnl_net_swap"].sum()
    win_rate = (ej["r_multiple"] > 0).mean() * 100.0
    print(f"  win_rate={win_rate:.2f}%  gross(price)_pnl_sum={gross_sum:.4f}  "
          f"swap_pnl_sum={swap_sum:.4f}  cost_pnl_sum={-cost_sum:.4f}  net_pnl_sum={net_sum:.4f}")

    r_gross = d["pnl_gross"].values
    if len(r_gross) > 5:
        tpy = len(d) / max((d["exit_time"].max() - d["entry_time"].min()).days / 365.25, 0.5)
        sh_gross = me.sharpe_annualized(r_gross, tpy)
        mean_g, t_g, n_g = me.hac_tstat(r_gross)
        print(f"  PRICE-ONLY (gross, ex-swap): Sharpe={sh_gross:.3f} HAC_t={t_g:.3f} n={n_g}")
    else:
        sh_gross, t_g = np.nan, np.nan

    row = dict(label=label, n=len(ej), n_buy=int(n_buy), n_sell=int(n_sell), win_rate=win_rate,
               gross_pnl_sum=gross_sum, swap_pnl_sum=swap_sum, cost_pnl_sum=-cost_sum,
               net_pnl_sum=net_sum, price_only_sharpe=sh_gross, price_only_hac_t=t_g)

    if n_sell >= 5:
        d_sell = d[d["direction"] == "sell"]
        mean_s, t_s, n_s = me.hac_tstat(d_sell["pnl_gross"].values)
        print(f"  SELL leg price-only: n={n_s} HAC_t={t_s:.3f}")
        row["sell_price_hac_t"] = t_s
        row["sell_price_n"] = n_s
    else:
        print(f"  SELL leg: only {n_sell} trades -- too few for any HAC/Sharpe claim "
              f"(falsification signal: veto likely blocks short structurally)")
        row["sell_price_hac_t"] = np.nan
        row["sell_price_n"] = int(n_sell)

    if n_buy >= 5:
        d_buy = d[d["direction"] == "buy"]
        mean_b, t_b, n_b = me.hac_tstat(d_buy["pnl_gross"].values)
        print(f"  BUY leg price-only: n={n_b} HAC_t={t_b:.3f}")
        row["buy_price_hac_t"] = t_b
        row["buy_price_n"] = n_b

    # cumulative EURJPY price return, to compare with the ~130->175 buy-and-hold move cited
    close_series = pd.read_parquet(se.CACHE_DIR / "EURJPY_M1.parquet")["close"]
    if not ej.empty:
        w_start = max(ej["entry_time"].min(), close_series.index.min())
        w_end = min(ej["exit_time"].max(), close_series.index.max())
        px_start = close_series.asof(w_start)
        px_end = close_series.asof(w_end)
        bh_return_pct = (px_end / px_start - 1.0) * 100.0
        print(f"  Buy-and-hold EURJPY over same window ({w_start.date()}->{w_end.date()}): "
              f"{px_start:.2f} -> {px_end:.2f} = {bh_return_pct:.1f}%")
        row["buy_and_hold_pct"] = bh_return_pct
    return row


def main():
    tf_cache = {}
    print(f"Building trades for CONFIRMED config, EXTENDED universe ({N_PAIRS} pairs): "
          f"{EXTENDED_PAIRS}")
    summ_full, all_trades = se.run_config(CONFIRMED, pairs=EXTENDED_PAIRS, tf_cache=tf_cache,
                                           verbose=True)
    all_trades.to_csv(OUT_DIR / "trades_CONFIRMED_extended_full.csv", index=False)
    print("Search-stage summary (full history, extended universe):", summ_full)

    mask = (all_trades["entry_time"] >= PRIMARY_START) & (all_trades["exit_time"] <= PRIMARY_END)
    primary_trades = all_trades[mask].copy()
    primary_trades.to_csv(OUT_DIR / "trades_CONFIRMED_extended_primary.csv", index=False)
    n_years_primary = (PRIMARY_END - PRIMARY_START).days / 365.25
    n_years_full = (all_trades["exit_time"].max() - all_trades["entry_time"].min()).days / 365.25

    fid_primary = fidelity_block(primary_trades, "primary_extended_2018-01-05_2024-07-29",
                                  n_years_primary, N_PAIRS)
    fid_full = fidelity_block(all_trades, "full_history_extended_2007-2026", n_years_full, N_PAIRS)
    pd.DataFrame([fid_primary, fid_full]).to_csv(OUT_DIR / "fidelity_CONFIRMED_extended.csv",
                                                  index=False)

    ej_primary = eurjpy_breakdown(primary_trades, "primary_2018-01-05_2024-07-29")
    ej_full = eurjpy_breakdown(all_trades, "full_history_2007-2026")
    pd.DataFrame([ej_primary, ej_full]).to_csv(OUT_DIR / "eurjpy_breakdown.csv", index=False)

    # ---- full harness on extended universe, primary window ----
    rf = me.load_rf()
    scenarios = [("gross", 0.0, 1.0), ("eightcap_raw", 0.75, 0.85), ("ftmo_retail", 2.48, 0.85)]
    tpy_primary = fid_primary["trades_per_pair_year"] * N_PAIRS
    rows = []
    for label, cost_bps, haircut in scenarios:
        d = me.add_pnl(primary_trades, rf, cost_bps=cost_bps, swap_haircut=haircut)
        sh_net_swap = me.sharpe_annualized(d["pnl_net_swap"].values, tpy_primary)
        sh_excess = me.sharpe_annualized(d["pnl_net_swap_excess"].values, tpy_primary)
        mean_r, t, n = me.hac_tstat(d["pnl_net_swap_excess"].values)
        rows.append(dict(scenario=label, cost_bps=cost_bps, n=len(d), sharpe_net_swap=sh_net_swap,
                          sharpe_excess=sh_excess, hac_t=t, gross_pnl_sum=d["pnl_gross"].sum(),
                          swap_pnl_sum=d["pnl_swap_only"].sum(), cost_pnl_sum=-d["pnl_cost_only"].sum(),
                          net_pnl_sum=d["pnl_net_swap"].sum()))
        if label == "ftmo_retail":
            ts = me.two_sided(d, "pnl_net_swap_excess", tpy_primary)
            ts.to_csv(OUT_DIR / "twosided_CONFIRMED_extended_primary.csv", index=False)
            print("Two-sided (extended, primary, FTMO):\n", ts)
            wf = me.walk_forward_folds(d, "pnl_net_swap_excess", n_folds=6)
            wf.to_csv(OUT_DIR / "walkforward_CONFIRMED_extended_primary.csv", index=False)
            print("Walk-forward (extended, primary, FTMO):\n", wf)
            lo, hi, _ = me.block_bootstrap_sharpe(d["pnl_net_swap_excess"].values, tpy_primary,
                                                   block_size=10, n_boot=2000)
            print(f"Bootstrap CI95 (extended, primary, FTMO): [{lo:.3f}, {hi:.3f}]")
            skew = float(pd.Series(d["pnl_net_swap_excess"]).skew())
            kurt = float(pd.Series(d["pnl_net_swap_excess"]).kurt() + 3.0)
            sr = d["pnl_net_swap_excess"].mean() / d["pnl_net_swap_excess"].std(ddof=1)
            print("DSR (n_trials=1):", me.deflated_sharpe(sr, len(d), skew, kurt, n_trials=1))

    res = pd.DataFrame(rows)
    res.to_csv(OUT_DIR / "harness_CONFIRMED_extended_primary.csv", index=False)
    print(res.to_string())

    # ---- 4-year regime buckets, full history, extended universe, FTMO cost ----
    d_full = me.add_pnl(all_trades, rf, cost_bps=2.48, swap_haircut=0.85)
    regime_bounds = [("2007-2010", "2007-01-01", "2010-12-31"),
                      ("2011-2014", "2011-01-01", "2014-12-31"),
                      ("2015-2018", "2015-01-01", "2018-12-31"),
                      ("2019-2021", "2019-01-01", "2021-12-31"),
                      ("2022-2024", "2022-01-01", "2024-12-31"),
                      ("2025-2026", "2025-01-01", "2026-12-31")]
    reg_rows = []
    for name, s, e in regime_bounds:
        g = d_full[(d_full["exit_time"] >= s) & (d_full["exit_time"] <= e)]
        if len(g) < 5:
            reg_rows.append(dict(regime=name, n=len(g)))
            continue
        years = max((pd.Timestamp(e) - pd.Timestamp(s)).days / 365.25, 0.5)
        tpy = len(g) / years
        sh = me.sharpe_annualized(g["pnl_net_swap_excess"].values, tpy)
        mean_r, t, n = me.hac_tstat(g["pnl_net_swap_excess"].values)
        reg_rows.append(dict(regime=name, n=len(g), trades_per_year=tpy, sharpe=sh, hac_mean=mean_r,
                              hac_t=t))
    reg_df = pd.DataFrame(reg_rows)
    reg_df.to_csv(OUT_DIR / "regime_4y_CONFIRMED_extended_full.csv", index=False)
    print("4-year regime split (extended, full history, FTMO):\n", reg_df.to_string())

    wf_full = me.walk_forward_folds(d_full, "pnl_net_swap_excess", n_folds=6)
    wf_full.to_csv(OUT_DIR / "walkforward_CONFIRMED_extended_full.csv", index=False)
    print("Walk-forward (extended, full history, FTMO):\n", wf_full)
    lo2, hi2, _ = me.block_bootstrap_sharpe(d_full["pnl_net_swap_excess"].values,
                                             len(d_full) / n_years_full, block_size=10, n_boot=2000)
    print(f"Bootstrap CI95 (extended, full history, FTMO): [{lo2:.3f}, {hi2:.3f}]")


if __name__ == "__main__":
    main()
