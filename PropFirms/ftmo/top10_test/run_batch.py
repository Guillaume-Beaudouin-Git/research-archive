"""
Run ~140 parameterized strategy specs from batch_strategies.py.
Apply rigorous methodology + AMTP + dual-gate verdict.

Dual gate:
  research_strict: SR>0.7, MaxDD<-25%, WF>50%, HAC_t>2.5, DSR>0.95
  practical_ftmo: p_FTMO>50%, MaxDD<-5%, WF>60%, cost_gate_ratio≥3.0
"""
from __future__ import annotations

import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from framework import (
    StrategyResult, load_rf_daily, hac_tstat, block_bootstrap_sharpe,
    deflated_sharpe, walk_forward_folds, max_drawdown_pct, amtp_bonferroni,
    ftmo_montecarlo, vol_target, _sharpe,
)
from batch_strategies import (
    build_specs, FAMILY_HANDLERS, trades_to_daily_pnl,
)

RESULTS_DIR = Path("<HOME>/Desktop/Algo_claude/PropFirms/ftmo/top10_test/results")


def evaluate_trades(sid: str, name: str, trades_df: pd.DataFrame,
                    rf_daily: pd.Series, n_amtp_trials: int = 142) -> StrategyResult:
    """Compute all stats and run FTMO MC. Vol-target sizing only."""
    res = StrategyResult(id=sid, name=name)
    res.n_trades = len(trades_df)

    if trades_df.empty or len(trades_df) < 20:
        res.notes = f"insufficient n_trades={len(trades_df)}"
        return res

    # Daily PnL
    if "exit_date" not in trades_df.columns:
        res.notes = "no exit_date column"
        return res
    dmin = pd.to_datetime(trades_df["exit_date"]).min()
    dmax = pd.to_datetime(trades_df["exit_date"]).max()
    all_dates = pd.date_range(dmin, dmax, freq="B")
    daily_pnl = trades_to_daily_pnl(trades_df, all_dates)

    # Reindex to business-day grid, fillna(0)
    bdays = pd.date_range(daily_pnl.index.min(), daily_pnl.index.max(), freq="B")
    daily_pnl = daily_pnl.reindex(bdays).fillna(0.0)
    n_active = int((daily_pnl != 0).sum())
    if n_active < 20:
        res.notes = f"n_active={n_active}<20 too sparse"
        res.n_days = n_active
        return res

    # Win rate, WL ratio, costs from trades
    wins = trades_df[trades_df["net_bps"] > 0]
    losses = trades_df[trades_df["net_bps"] < 0]
    res.win_rate = len(wins) / len(trades_df) if len(trades_df) > 0 else 0.0
    avg_win = wins["net_bps"].mean() if len(wins) > 0 else 0.0
    avg_loss = abs(losses["net_bps"].mean()) if len(losses) > 0 else 1.0
    res.wl_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    res.mean_bps_per_trade_gross = trades_df["gross_bps"].mean()
    res.mean_bps_per_trade_net = trades_df["net_bps"].mean()
    cost_total = trades_df["cost_bps"].mean() + abs(trades_df["swap_bps"].mean())
    gross_abs = abs(trades_df["gross_bps"].mean())
    res.cost_gate_ratio = gross_abs / cost_total if cost_total > 0 else 0.0

    # Vol target
    daily_pnl_vt = vol_target(daily_pnl, target_annual=0.08, lookback=63)
    daily_pnl_vt = daily_pnl_vt.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    res.n_days = len(daily_pnl_vt)

    res.sharpe_gross = _sharpe(daily_pnl.values, 252)
    res.sharpe_net = _sharpe(daily_pnl_vt.values, 252)
    rf = rf_daily.reindex(daily_pnl_vt.index).fillna(0.0)
    excess = daily_pnl_vt - rf
    res.sharpe_excess = _sharpe(excess.values, 252)
    res.hac_t_excess = hac_tstat(excess.values, lag=6)
    res.hac_t_net = hac_tstat(daily_pnl_vt.values, lag=6)

    eq = (1 + daily_pnl_vt).cumprod()
    res.max_dd_pct = max_drawdown_pct(eq.values)

    bs = block_bootstrap_sharpe(daily_pnl_vt.values, n_boot=1000, block_len=5)
    res.bootstrap_sr_mean = bs["sr_mean"]
    res.bootstrap_sr_lo95 = bs["sr_lo95"]
    res.bootstrap_sr_hi95 = bs["sr_hi95"]

    sk = float(pd.Series(daily_pnl_vt).skew())
    ku = float(pd.Series(daily_pnl_vt).kurtosis() + 3)
    dsr = deflated_sharpe(res.sharpe_excess, len(daily_pnl_vt),
                          n_trials=n_amtp_trials, skew=sk, kurt=ku)
    res.dsr = dsr["dsr"]
    res.dsr_passes = dsr["dsr_passes"]

    wf = walk_forward_folds(excess, n_folds=5, min_train_years=1.5)
    res.wf_n_folds = len(wf)
    if wf:
        pass_count = sum(1 for f in wf if f["sr_test"] > 0)
        sign_count = sum(1 for f in wf if f["sign_consistent"])
        res.wf_pass_rate = pass_count / len(wf)
        res.wf_sign_consistent_pct = sign_count / len(wf)

    ftmo_res = ftmo_montecarlo(daily_pnl_vt, n_runs=2000, max_days_per_phase=365)
    res.ftmo_p_pass_p1 = ftmo_res.p_pass_p1
    res.ftmo_p_pass_p1_p2 = ftmo_res.p_pass_p1_p2
    res.ftmo_p_bust = ftmo_res.p_bust_dll + ftmo_res.p_bust_mll
    res.ftmo_median_days_p1 = ftmo_res.median_days_pass_p1

    res.research_pass = (res.sharpe_excess > 0.7 and res.max_dd_pct > -0.25
                         and res.wf_pass_rate > 0.50)
    res.propfirm_pass = (res.sharpe_excess > 1.0 and res.max_dd_pct > -0.10
                         and res.wf_pass_rate > 0.60)
    return res


def main():
    rf = load_rf_daily()
    specs = build_specs()
    print(f"\n=== Running {len(specs)} strategy specs ===\n")
    n_amtp = len(specs)
    results = []
    t0 = time.time()
    for i, spec in enumerate(specs):
        elapsed = time.time() - t0
        try:
            trades_df = FAMILY_HANDLERS[spec.family](spec.params)
            r = evaluate_trades(spec.id, spec.name, trades_df, rf, n_amtp_trials=n_amtp)
            r.notes = f"family={spec.family} | {r.notes}".strip(" |")
            if i % 10 == 0 or r.research_pass or r.propfirm_pass or abs(r.hac_t_excess) > 3.0:
                print(f"[{i+1:>3}/{len(specs)} t={elapsed:>5.0f}s] {spec.id[:40]:<40}  "
                      f"n={r.n_trades:>4} SR={r.sharpe_excess:>5.2f} MDD={r.max_dd_pct*100:>5.1f}% "
                      f"WF={r.wf_pass_rate*100:>3.0f}% t={r.hac_t_excess:>5.2f} p_FTMO={r.ftmo_p_pass_p1*100:>4.1f}%")
        except Exception as e:
            r = StrategyResult(id=spec.id, name=spec.name, notes=f"ERROR: {e}")
            print(f"  ERROR in {spec.id}: {e}")
        results.append(r)

    # AMTP
    t_stats = [r.hac_t_excess for r in results]
    p_corr = amtp_bonferroni(t_stats, alpha=0.05)
    for r, p in zip(results, p_corr):
        r.amtp_p_value = p

    df = pd.DataFrame([asdict(r) for r in results])
    df = df.sort_values("sharpe_excess", ascending=False)
    out_csv = RESULTS_DIR / "summary_batch_142.csv"
    df.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")

    # Dual gate
    cols = ["id", "n_trades", "n_days", "sharpe_excess", "max_dd_pct",
            "wf_pass_rate", "hac_t_excess", "dsr", "amtp_p_value",
            "ftmo_p_pass_p1", "research_pass", "propfirm_pass",
            "cost_gate_ratio", "notes"]
    print("\n=== TOP 20 by Sharpe excess ===")
    print(df[cols].head(20).to_string(index=False))

    # Strict survivors
    strict = df[(df["sharpe_excess"] > 0.7) & (df["max_dd_pct"] > -0.25)
                & (df["wf_pass_rate"] > 0.5) & (df["hac_t_excess"] > 2.5)
                & (df["dsr_passes"])]
    print(f"\n=== STRICT SURVIVORS (research_pass + HAC_t>2.5 + DSR pass): {len(strict)} ===")
    if len(strict) > 0:
        print(strict[cols].to_string(index=False))

    # Practical FTMO gate
    practical = df[(df["ftmo_p_pass_p1"] > 0.5) & (df["max_dd_pct"] > -0.05)
                   & (df["wf_pass_rate"] > 0.6) & (df["cost_gate_ratio"] >= 3.0)]
    print(f"\n=== PRACTICAL FTMO GATE (p_FTMO>50% + MDD<-5% + WF>60% + cost_gate≥3): {len(practical)} ===")
    if len(practical) > 0:
        print(practical[cols].to_string(index=False))

    # AMTP-significant in either direction
    amtp_sig = df[df["amtp_p_value"] < 0.05]
    print(f"\n=== AMTP-SIGNIFICANT (Bonferroni × {n_amtp}): {len(amtp_sig)} ===")
    if len(amtp_sig) > 0:
        amtp_sig = amtp_sig.sort_values("hac_t_excess", ascending=False)
        print(amtp_sig[cols].to_string(index=False))


if __name__ == "__main__":
    main()
