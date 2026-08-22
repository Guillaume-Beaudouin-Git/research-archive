"""Tier 2 — the 20 'rigorous' candidates (run_tests.py + strategies_v2.py).

Their raw inputs (dukascopy M5, ftmo_research, m5_indices M1 CSVs) were deleted,
but the funnel SAVED the full trade ledgers (results/trades_*.csv: gross_bps,
cost_bps, swap_bps, n_nights, asset, side) and the exact daily PnL index
(results/daily_pnl_*.csv). So defects 1, 3, 4, 5 and 6 can be re-applied
EXACTLY, by re-costing the stored gross. Defect 2 (clock) cannot: it changes the
signal itself, and the price series are gone. That is stated in the report.
"""
from __future__ import annotations

import glob
import os
import sys
from dataclasses import asdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from costs import COST_CATALOG, COST_MEASURED, SWAP_CATALOG, SWAP_MEASURED_BY_SYMBOL
from engine import (Res, _sharpe, hac_tstat, block_bootstrap_sharpe, vol_target,
                    walk_forward_folds, max_drawdown_pct, ftmo_montecarlo,
                    deflated_sharpe_broken, load_rf_daily, amtp_bonferroni)

SRC = ("<HOME>/Desktop/Algo_claude/PropFirms/ftmo/"
       "program_2026-06/top10_test/results")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")

# asset label -> (list of (symbol, asset_class, side_multiplier_vs_trade_side))
LEG_MAP = {
    "US500":   [("US500", "Index_CFD_major", +1)],
    "US100":   [("US100", "Index_CFD_major", +1)],
    "GER40":   [("GER40", "Index_CFD_major", +1)],
    "UK100":   [("UK100", "Index_CFD_major", +1)],
    "EURUSD":  [("EURUSD", "FX_major", +1)],
    "USDJPY":  [("USDJPY", "FX_major", +1)],
    "EUR-GBP": [("EURUSD", "FX_major", +1), ("GBPUSD", "FX_major", -1)],
    "NDX-SPX": [("US100", "Index_CFD_major", +1), ("US500", "Index_CFD_major", -1)],
}

# Strategies whose EXIT is a resting stop / bracket (run_tests.py:87-123, 177-191,
# and the gap-fill family). Defect 6 charges the resting-stop tier on that leg.
BRACKET_EXIT = {"ang_025", "ang_025_flip", "ang_025_flip_mod2", "ang_025_flip_mod3",
                "ang_019", "lit_021", "lit_020"}
SLIP_RESTING_STOP = 2.169


def recost(sid: str, tr: pd.DataFrame, costs: bool, swaps: bool, typed: bool):
    """Rebuild cost_bps / swap_bps / net_bps from the stored gross_bps."""
    ct = COST_MEASURED if costs else COST_CATALOG
    out = tr.copy()
    cost, swap = [], []
    for _, r in tr.iterrows():
        legs = LEG_MAP[r["asset"]]
        c = sum(ct[cls] for _, cls, _ in legs)
        if typed and sid in BRACKET_EXIT:
            c += SLIP_RESTING_STOP          # exit leg only; entry is a market fill
        nights_per_leg = int(r["n_nights"]) // len(legs)
        s = 0.0
        for sym, cls, mult in legs:
            side = int(r["side"]) * mult
            if swaps and sym in SWAP_MEASURED_BY_SYMBOL:
                lo, sh = SWAP_MEASURED_BY_SYMBOL[sym]
                per = lo if side > 0 else sh
            elif swaps and sym in ("US500", "US100", "US30", "UK100"):
                lo, sh = SWAP_MEASURED_BY_SYMBOL["US100"]   # index proxy
                per = lo if side > 0 else sh
            else:
                per = SWAP_CATALOG[cls]
            s += nights_per_leg * per
        cost.append(c)
        swap.append(s)
    out["cost_bps"] = cost
    out["swap_bps"] = swap
    out["net_bps"] = out["gross_bps"] - out["cost_bps"] + out["swap_bps"]
    return out


def evaluate(sid, name, tr, idx, rf, dsr_fixed, floor_mode, n_trials, std_sr,
             n_boot=2000, mc_runs=3000, return_series=False):
    res = Res(id=sid, name=name)
    res.n_trades = len(tr)
    t = tr.copy()
    t["exit_date"] = pd.to_datetime(t["exit_date"]).dt.normalize()
    by = t.groupby("exit_date")["net_bps"].sum() / 10000.0
    full = by.index.union(idx).sort_values()
    daily = pd.Series(0.0, index=full)
    daily.loc[by.index] = by.values
    bd = pd.date_range(daily.index.min(), daily.index.max(), freq="B")
    daily = daily.reindex(bd).fillna(0.0)

    res.win_rate = float((t.net_bps > 0).mean())
    res.mean_bps_per_trade_gross = float(t.gross_bps.mean())
    res.mean_bps_per_trade_net = float(t.net_bps.mean())
    ctot = t.cost_bps.mean() + abs(t.swap_bps.mean())
    res.cost_gate_ratio = float(abs(t.gross_bps.mean()) / ctot) if ctot > 0 else 0.0

    vt = vol_target(daily, target_annual=0.08, lookback=63)
    vt = vt.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    res.n_days = len(vt)
    yrs = (vt.index[-1] - vt.index[0]).days / 365.25
    res.n_per_year_emp = len(vt) / yrs if yrs > 0 else np.nan
    excess = vt - rf.reindex(vt.index).ffill().fillna(0.0)
    res.sharpe_excess = _sharpe(excess.values, 252)
    res.hac_t_excess = hac_tstat(excess.values, lag=6)
    res.max_dd_pct = max_drawdown_pct((1 + vt).cumprod().values)
    bs = block_bootstrap_sharpe(vt.values, n_boot=n_boot, block_len=5)
    res.bootstrap_sr_mean, res.bootstrap_sr_lo95, res.bootstrap_sr_hi95 = (
        bs["sr_mean"], bs["sr_lo95"], bs["sr_hi95"])
    if dsr_fixed:
        import warnings
        from dsr import deflated_sharpe_ratio, DSRCalibrationWarning
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DSRCalibrationWarning)
            o = deflated_sharpe_ratio(excess.values, n_trials=n_trials,
                                      periods_per_year=252, rf=0.0,
                                      std_sr_trials=std_sr)
        res.dsr, res.dsr_passes = o["dsr"], bool(o["dsr"] >= 0.95)
    else:
        d = deflated_sharpe_broken(res.sharpe_excess, len(vt), n_trials=1,
                                   skew=float(pd.Series(vt).skew()),
                                   kurt=float(pd.Series(vt).kurtosis() + 3))
        res.dsr, res.dsr_passes = d["dsr"], d["dsr_passes"]
    wf = walk_forward_folds(excess, n_folds=5, min_train_years=2.0)
    res.wf_n_folds = len(wf)
    if wf:
        res.wf_pass_rate = sum(1 for f in wf if f["sr_test"] > 0) / len(wf)
    mc = ftmo_montecarlo(vt, n_runs=mc_runs, max_days_per_phase=365,
                         floor_mode=floor_mode)
    res.ftmo_p_pass_p1, res.ftmo_p_pass_p1_p2 = mc.p_pass_p1, mc.p_pass_p1_p2
    res.ftmo_p_bust = mc.p_bust_dll + mc.p_bust_mll
    res.ftmo_median_days_p1 = mc.median_days_pass_p1
    res.research_pass = bool(res.sharpe_excess > 0.7 and res.max_dd_pct > -0.25
                             and res.wf_pass_rate > 0.50)
    res.propfirm_pass = bool(res.sharpe_excess > 1.0 and res.max_dd_pct > -0.10
                             and res.wf_pass_rate > 0.60)
    res.order_type = "resting_stop_exit" if sid in BRACKET_EXIT else "scheduled_market"
    return (res, excess) if return_series else res


CONFIGS = [
    ("base",     dict(costs=False, swaps=False, typed=False), dict(dsr_fixed=False, floor_mode="ratchet")),
    ("D1_dsr",   dict(costs=False, swaps=False, typed=False), dict(dsr_fixed=True,  floor_mode="ratchet")),
    ("D3_costs", dict(costs=True,  swaps=False, typed=False), dict(dsr_fixed=False, floor_mode="ratchet")),
    ("D4_floor", dict(costs=False, swaps=False, typed=False), dict(dsr_fixed=False, floor_mode="static")),
    ("D5_swaps", dict(costs=False, swaps=True,  typed=False), dict(dsr_fixed=False, floor_mode="ratchet")),
    ("D6_order", dict(costs=False, swaps=False, typed=True),  dict(dsr_fixed=False, floor_mode="ratchet")),
    ("ALL",      dict(costs=True,  swaps=True,  typed=True),  dict(dsr_fixed=True,  floor_mode="static")),
]

N_TRIALS = 162   # 142 batch + 20 rigorous = the funnel's distinct hypotheses


def main():
    os.makedirs(OUT, exist_ok=True)
    rf = load_rf_daily()
    ids = sorted(os.path.basename(f)[7:-4] for f in glob.glob(f"{SRC}/trades_*.csv"))
    ledgers = {s: pd.read_csv(f"{SRC}/trades_{s}.csv") for s in ids}
    idxs = {}
    for s in ids:
        d = pd.read_csv(f"{SRC}/daily_pnl_{s}.csv", index_col=0, parse_dates=True)
        idxs[s] = d.index
    std_sr = None
    for name, rc, ev in CONFIGS:
        rows, series = [], {}
        for s in ids:
            tr = recost(s, ledgers[s], **rc)
            r, exc = evaluate(s, s, tr, idxs[s], rf, n_trials=N_TRIALS,
                              std_sr=std_sr, return_series=True, **ev)
            rows.append(asdict(r))
            series[s] = exc
        df = pd.DataFrame(rows)
        df["amtp_p_value"] = amtp_bonferroni(df["hac_t_excess"].tolist())
        df.to_csv(f"{OUT}/tier2_{name}.csv", index=False)
        if name == "base":
            from dsr import estimate_std_sr_trials
            b142 = pd.read_csv(f"{OUT}/summary_base.csv")
            allsh = pd.concat([b142["sharpe_excess"], df["sharpe_excess"]])
            allsh = allsh.replace([np.inf, -np.inf], np.nan).dropna()
            std_sr = estimate_std_sr_trials(allsh.tolist(), periods_per_year=252,
                                            n_obs=int(df["n_days"].median()))
            print(f"std_sr_trials (162 trials) = {std_sr:.4f}", flush=True)
            pd.DataFrame(series).to_parquet(f"{OUT}/tier2_series_base.parquet")
        print(f"{name}: research_pass={int(df.research_pass.sum())} "
              f"SR>0.7={int((df.sharpe_excess>0.7).sum())}", flush=True)


if __name__ == "__main__":
    main()
