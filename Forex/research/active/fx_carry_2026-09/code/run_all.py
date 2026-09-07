"""
Main orchestration — Part A (filter vs placebo), Part D (two-sided legs).
Writes all intermediate CSVs to ../results/ as it goes (no monitors armed).
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from rates import all_differentials, PAIR_CCY
from engine import backtest, direction_from_diff, direction_random, rebalance_dates, portfolio_return
from stats_tools import excess_returns, load_rf_daily, sharpe, hac_tstat, block_bootstrap_sharpe_ci, walk_forward, mde_sharpe

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
RES = BASE / "results"
RES.mkdir(parents=True, exist_ok=True)

FTMO_COST_BPS = 2.48
PAIRS = list(PAIR_CCY.keys())

WINDOWS = {
    "full_2007_2026": (None, None),
    "primary_2018_2024": ("2018-01-01", "2024-07-29"),
    "recent_2026": ("2026-01-01", None),
}


def slice_window(s: pd.Series, w):
    lo, hi = WINDOWS[w]
    if lo:
        s = s[s.index >= pd.Timestamp(lo, tz="UTC")]
    if hi:
        s = s[s.index <= pd.Timestamp(hi, tz="UTC")]
    return s


def main():
    close = pd.read_parquet(DATA / "daily_close.parquet")
    close.index = pd.to_datetime(close.index)
    diffs = all_differentials(PAIRS, close.index.tz_localize(None))
    diffs.index = close.index  # restore tz-aware to match

    rf = load_rf_daily(close.index)

    rows = []
    pair_net_real = {}
    pair_net_reverse = {}
    pair_net_bh = {}
    placebo_summary = []

    n_random = 200
    rng = np.random.default_rng(20260902)

    for pair in PAIRS:
        print(f"[run_all] {pair} ...", flush=True)
        px = close[pair].dropna()
        diff = diffs[pair].reindex(px.index)
        rebal = rebalance_dates(px.index)

        dir_real = direction_from_diff(diff, rebal)
        dir_reverse = -dir_real
        dir_bh = pd.Series(1.0, index=px.index)

        df_real = backtest(px, pair, dir_real, FTMO_COST_BPS)
        df_reverse = backtest(px, pair, dir_reverse, FTMO_COST_BPS)
        df_bh = backtest(px, pair, dir_bh, FTMO_COST_BPS)

        pair_net_real[pair] = df_real
        pair_net_reverse[pair] = df_reverse
        pair_net_bh[pair] = df_bh

        # random placebo distribution (matched rebalance cadence & vol targeting)
        placebo_sharpes = []
        for i in range(n_random):
            dir_rand = direction_random(px.index, rebal, rng)
            df_rand = backtest(px, pair, dir_rand, FTMO_COST_BPS)
            ex = excess_returns(df_rand["net_pnl"], rf)
            placebo_sharpes.append(sharpe(ex))
        placebo_sharpes = np.array(placebo_sharpes)

        for wname in WINDOWS:
            r_real = slice_window(excess_returns(df_real["net_pnl"], rf), wname)
            r_rev = slice_window(excess_returns(df_reverse["net_pnl"], rf), wname)
            r_bh = slice_window(excess_returns(df_bh["net_pnl"], rf), wname)

            sh_real = sharpe(r_real)
            mu_real, t_real = hac_tstat(r_real)
            lo, hi, _ = block_bootstrap_sharpe_ci(r_real)
            wf = walk_forward(r_real) if wname == "primary_2018_2024" else None

            sh_rev = sharpe(r_rev)
            sh_bh = sharpe(r_bh)

            pctile = float((placebo_sharpes < sh_real).mean()) * 100 if wname == "full_2007_2026" else np.nan

            rows.append(dict(
                pair=pair, window=wname, n_obs=len(r_real),
                sharpe_real=sh_real, hac_t_real=t_real,
                boot_ci_lo=lo, boot_ci_hi=hi,
                sharpe_reverse=sh_rev, sharpe_buyhold=sh_bh,
                placebo_mean=placebo_sharpes.mean() if wname == "full_2007_2026" else np.nan,
                placebo_p5=np.percentile(placebo_sharpes, 5) if wname == "full_2007_2026" else np.nan,
                placebo_p95=np.percentile(placebo_sharpes, 95) if wname == "full_2007_2026" else np.nan,
                real_vs_placebo_pctile=pctile,
                wf_folds=str(wf) if wf else "",
                wf_pct_positive=(sum(f > 0 for f in wf) / len(wf) * 100) if wf else np.nan,
            ))

    results = pd.DataFrame(rows)
    results.to_csv(RES / "part_a_filter_vs_placebo.csv", index=False)
    print("Wrote", RES / "part_a_filter_vs_placebo.csv", results.shape)

    # Portfolio (equal-weight across 9 pairs)
    port_real = portfolio_return(pair_net_real)
    port_reverse = portfolio_return(pair_net_reverse)
    port_bh = portfolio_return(pair_net_bh)

    port_rows = []
    for wname in WINDOWS:
        r_real = slice_window(excess_returns(port_real, rf), wname)
        r_rev = slice_window(excess_returns(port_reverse, rf), wname)
        r_bh = slice_window(excess_returns(port_bh, rf), wname)
        sh = sharpe(r_real)
        mu, t = hac_tstat(r_real)
        lo, hi, _ = block_bootstrap_sharpe_ci(r_real)
        wf = walk_forward(r_real) if wname == "primary_2018_2024" else None
        port_rows.append(dict(
            window=wname, n_obs=len(r_real),
            sharpe_real=sh, hac_t=t, boot_lo=lo, boot_hi=hi,
            sharpe_reverse=sharpe(r_rev), sharpe_buyhold=sharpe(r_bh),
            wf_folds=str(wf) if wf else "", mde=mde_sharpe(len(r_real)) if len(r_real) else np.nan,
        ))
    port_df = pd.DataFrame(port_rows)
    port_df.to_csv(RES / "part_a_portfolio.csv", index=False)
    print("Wrote", RES / "part_a_portfolio.csv")
    print(port_df)

    # Part D: two-sided legs, separately, full history + primary window
    leg_rows = []
    for pair in PAIRS:
        px = close[pair].dropna()
        diff = diffs[pair].reindex(px.index)
        rebal = rebalance_dates(px.index)
        dir_real = direction_from_diff(diff, rebal)
        for leg_name, leg_mask_val in [("long_leg", 1), ("short_leg", -1)]:
            dir_leg = dir_real.where(dir_real == leg_mask_val, 0.0)
            df_leg = backtest(px, pair, dir_leg, FTMO_COST_BPS)
            for wname in ["full_2007_2026", "primary_2018_2024"]:
                r = slice_window(excess_returns(df_leg["net_pnl"], rf), wname)
                r_active = r[df_leg["pos"].reindex(r.index) != 0]
                sh = sharpe(r)
                mu, t = hac_tstat(r)
                n_active = int((df_leg["pos"].reindex(slice_window(df_leg["pos"], wname).index) != 0).sum()) if wname in WINDOWS else np.nan
                leg_rows.append(dict(pair=pair, leg=leg_name, window=wname, n_obs=len(r),
                                      n_active_days=n_active, sharpe=sh, hac_t=t))
    legs_df = pd.DataFrame(leg_rows)
    legs_df.to_csv(RES / "part_d_two_sided_legs.csv", index=False)
    print("Wrote", RES / "part_d_two_sided_legs.csv")

    print("DONE run_all.py")


if __name__ == "__main__":
    main()
