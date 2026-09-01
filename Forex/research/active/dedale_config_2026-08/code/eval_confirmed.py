"""
Full, single evaluation of the CONFIRMED "Dedale" filter config, identified via external
documentary source (Algorithm_Brieuc/recapitulatif_parametres.md, a transcription of the MT5
Inputs tab screenshots) + a labeling-bug fix in DedaleFormation.mq5 lines 69-78 (the five
TDI_TIMEFRAME{0-4}_ANGLE booleans carry the DISPLAY comment "// Tendance TDI {0-4}", byte-identical
to the TDI_TIMEFRAME{0-4}_TREND comments declared just above -- MT5 shows two visually
indistinguishable "Tendance TDI" blocks; declaration order resolves "serie 1"=TREND (lines 69-73),
"serie 2"=ANGLE (lines 74-78)).

CONFIRMED_FILTERS (8 of 15 active, global AND, verified against recap doc + source line order):
  TDI_TIMEFRAME3_CROSS = true   (H4 cross)
  TDI_TIMEFRAME3_TREND = true   (H4 trend)
  TDI_TIMEFRAME4_TREND = true   (D1 trend)
  TDI_TIMEFRAME{0,1,2,3,4}_ANGLE = true   (all 5 timeframes)
This is NOT a swept/selected candidate -- Delta n_tests = 1.
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

PRIMARY_START = pd.Timestamp("2018-01-05", tz="UTC")
PRIMARY_END = pd.Timestamp("2024-07-29", tz="UTC")
TARGET = dict(trades_per_pair_year=3.5, win_rate=63.58, hold_days=11.0, worst_trade_pct=-1.27,
              vol_annual_pct=10.91, total_return_pct=60.33)

N_PAIRS = 7


def fidelity_block(trades: pd.DataFrame, label: str, n_years: float, risk_pct=1.0):
    if trades.empty:
        print(f"[{label}] NO TRADES")
        return {}
    n = len(trades)
    tpy = n / (N_PAIRS * n_years)
    win_rate = (trades["r_multiple"] > 0).mean() * 100.0
    hold = trades["hold_days"].mean()
    worst = trades["r_multiple"].min() * risk_pct

    # equity curve: compound pnl_net_swap (price + realistic swap, no execution cost) chronologically
    d = trades.sort_values("exit_time").copy()
    risk_amt = risk_pct / 100.0
    # per-trade % return on current balance (r_multiple * risk_pct, plus swap/notional term already
    # folded into pnl_net_swap via add_pnl -- but add_pnl needs rf and cost scenario; use haircut .85, cost 0
    rf = me.load_rf()
    d = me.add_pnl(d, rf, cost_bps=0.0, swap_haircut=0.85)
    # pnl_net_swap is already in "risk_amount units" (risk_pct% of a reference balance) -- treat as
    # the per-trade compounding return step (standard R-multiple -> % equity convention already used
    # throughout dedale_engine/metrics)
    balance = 1.0
    curve = []
    for _, row in d.iterrows():
        balance *= (1.0 + row["pnl_net_swap"])
        curve.append((row["exit_time"], balance))
    curve_df = pd.DataFrame(curve, columns=["exit_time", "balance"]).set_index("exit_time")
    total_return_pct = (curve_df["balance"].iloc[-1] / curve_df["balance"].iloc[0] - 1.0) * 100.0 \
        if len(curve_df) > 1 else np.nan
    daily = curve_df["balance"].resample("1D").last().ffill()
    daily_ret = daily.pct_change().dropna()
    vol_annual_pct = daily_ret.std() * math.sqrt(252) * 100.0 if len(daily_ret) > 5 else np.nan

    row = dict(label=label, n=n, trades_per_pair_year=tpy, win_rate=win_rate, hold_days=hold,
               worst_trade_pct=worst, vol_annual_pct=vol_annual_pct,
               total_return_pct=total_return_pct)
    print(f"--- Fidelity [{label}] ---")
    for k, v in row.items():
        if k == "label":
            continue
        tgt = TARGET.get(k)
        print(f"  {k}: {v:.3f}" + (f"   (cible {tgt})" if tgt is not None else ""))
    return row


def main():
    tf_cache = {}
    print("Building trades for CONFIRMED config across 7 pairs (full history 2007-2026)...")
    summ_full, all_trades = se.run_config(CONFIRMED, tf_cache=tf_cache, verbose=True)
    all_trades.to_csv(OUT_DIR / "trades_CONFIRMED_full.csv", index=False)
    print("Search-stage summary (full history):", summ_full)

    # primary window slice (exact author window)
    mask = (all_trades["entry_time"] >= PRIMARY_START) & (all_trades["exit_time"] <= PRIMARY_END)
    primary_trades = all_trades[mask].copy()
    primary_trades.to_csv(OUT_DIR / "trades_CONFIRMED_primary.csv", index=False)
    n_years_primary = (PRIMARY_END - PRIMARY_START).days / 365.25
    n_years_full = (all_trades["exit_time"].max() - all_trades["entry_time"].min()).days / 365.25

    fid_primary = fidelity_block(primary_trades, "primary_2018-01-05_2024-07-29", n_years_primary)
    fid_full = fidelity_block(all_trades, "full_history_2007-2026", n_years_full)
    pd.DataFrame([fid_primary, fid_full]).to_csv(OUT_DIR / "fidelity_CONFIRMED.csv", index=False)

    # ---- full harness evaluation (primary window, matching author's window) ----
    rf = me.load_rf()
    scenarios = [("gross", 0.0, 1.0), ("eightcap_raw", 0.75, 0.85), ("ftmo_retail", 2.48, 0.85)]
    tpy_primary = fid_primary["trades_per_pair_year"] * N_PAIRS
    rows = []
    for label, cost_bps, haircut in scenarios:
        d = me.add_pnl(primary_trades, rf, cost_bps=cost_bps, swap_haircut=haircut)
        sh_net_swap = me.sharpe_annualized(d["pnl_net_swap"].values, tpy_primary)
        sh_excess = me.sharpe_annualized(d["pnl_net_swap_excess"].values, tpy_primary)
        mean_r, t, n = me.hac_tstat(d["pnl_net_swap_excess"].values)
        gross_sum = d["pnl_gross"].sum()
        swap_sum = d["pnl_swap_only"].sum()
        cost_sum = d["pnl_cost_only"].sum()
        net_sum = d["pnl_net_swap"].sum()
        swap_share = swap_sum / net_sum if net_sum != 0 else np.nan
        rows.append(dict(scenario=label, cost_bps=cost_bps, n=len(d), sharpe_net_swap=sh_net_swap,
                          sharpe_excess=sh_excess, hac_t=t, gross_pnl_sum=gross_sum,
                          swap_pnl_sum=swap_sum, cost_pnl_sum=-cost_sum, net_pnl_sum=net_sum,
                          swap_share_of_net=swap_share))
        if label == "ftmo_retail":
            ts = me.two_sided(d, "pnl_net_swap_excess", tpy_primary)
            ts.to_csv(OUT_DIR / "twosided_CONFIRMED_primary.csv", index=False)
            print("Two-sided (primary, FTMO):\n", ts)

            wf = me.walk_forward_folds(d, "pnl_net_swap_excess", n_folds=6)
            wf.to_csv(OUT_DIR / "walkforward_CONFIRMED_primary.csv", index=False)
            print("Walk-forward 5 folds (primary, FTMO):\n", wf)

            lo, hi, boots = me.block_bootstrap_sharpe(d["pnl_net_swap_excess"].values,
                                                       tpy_primary, block_size=10, n_boot=2000)
            print(f"Block-bootstrap CI95 (primary, FTMO, excess): [{lo:.3f}, {hi:.3f}]")

            skew = float(pd.Series(d["pnl_net_swap_excess"]).skew())
            kurt = float(pd.Series(d["pnl_net_swap_excess"]).kurt() + 3.0)
            sr_per_trade = d["pnl_net_swap_excess"].mean() / d["pnl_net_swap_excess"].std(ddof=1)
            dsr1 = me.deflated_sharpe(sr_per_trade, len(d), skew, kurt, n_trials=1)
            print("DSR (n_trials=1, single pre-specified config):", dsr1)

            regime_bounds = [("2007-2010", "2007-01-01", "2010-12-31"),
                              ("2011-2014", "2011-01-01", "2014-12-31"),
                              ("2015-2018", "2015-01-01", "2018-12-31"),
                              ("2019-2021", "2019-01-01", "2021-12-31"),
                              ("2022-2024", "2022-01-01", "2024-12-31"),
                              ("2025-2026", "2025-01-01", "2026-12-31")]

    res = pd.DataFrame(rows)
    res.to_csv(OUT_DIR / "harness_CONFIRMED_primary.csv", index=False)
    print(res.to_string())

    # ---- 4-year regime buckets on FULL HISTORY, 2022-2024 isolated ----
    rf2 = me.load_rf()
    d_full = me.add_pnl(all_trades, rf2, cost_bps=2.48, swap_haircut=0.85)
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
            reg_rows.append(dict(regime=name, n=len(g), sharpe=np.nan, hac_t=np.nan))
            continue
        years = max((pd.Timestamp(e) - pd.Timestamp(s)).days / 365.25, 0.5)
        tpy = len(g) / years
        sh = me.sharpe_annualized(g["pnl_net_swap_excess"].values, tpy)
        mean_r, t, n = me.hac_tstat(g["pnl_net_swap_excess"].values)
        reg_rows.append(dict(regime=name, n=len(g), trades_per_year=tpy, sharpe=sh, hac_mean=mean_r,
                              hac_t=t))
    reg_df = pd.DataFrame(reg_rows)
    reg_df.to_csv(OUT_DIR / "regime_4y_CONFIRMED_full.csv", index=False)
    print("4-year regime split (full history, FTMO cost, excess-RF):\n", reg_df.to_string())

    # ---- full-history walk-forward (>=5 folds) ----
    wf_full = me.walk_forward_folds(d_full, "pnl_net_swap_excess", n_folds=6)
    wf_full.to_csv(OUT_DIR / "walkforward_CONFIRMED_full.csv", index=False)
    print("Walk-forward (full history, FTMO):\n", wf_full)

    lo2, hi2, _ = me.block_bootstrap_sharpe(d_full["pnl_net_swap_excess"].values,
                                             len(d_full) / n_years_full, block_size=10, n_boot=2000)
    print(f"Block-bootstrap CI95 (full history, FTMO, excess): [{lo2:.3f}, {hi2:.3f}]")


if __name__ == "__main__":
    main()
