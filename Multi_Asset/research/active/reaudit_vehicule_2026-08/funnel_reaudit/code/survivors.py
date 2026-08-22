"""Full P1 diagnostics for every candidate that reaches RESEARCH_PASS in ANY
configuration: walk-forward >=5 expanding folds, HAC lag-6, block bootstrap
(Politis-Romano), repaired DSR under both defensible trial dispersions, the
two-sided mirror check, and the correlation to the DEPLOYED overnight sleeve.
"""
from __future__ import annotations

import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from strategies_repaired import build_specs, FAMILY_HANDLERS, Cfg
from engine import (evaluate_trades, load_rf_daily, walk_forward_folds, _sharpe,
                    block_bootstrap_sharpe, hac_tstat)
from data_layer import overnight_sleeve_daily
from dsr import (deflated_sharpe_ratio, estimate_std_sr_trials,
                 sampling_noise_floor_sr, DSRCalibrationWarning)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
FLOOR = pd.Timestamp("2020-01-01")

CANDIDATES = {
    # id -> config under which it reaches RESEARCH_PASS
    "ed_fomc_US30_LO":          ("base", Cfg()),
    "ed_fomc_GER40_LO":         ("base", Cfg()),
    "me_fom_nfp_cpi_XAUUSD_+1": ("base", Cfg()),
    "ed_cpi_us_XAUUSD_LO":      ("D3_costs", Cfg(costs=True)),
    "ed_fomc_USDJPY_LO":        ("ALL", Cfg(clock="utc", costs=True, swaps=True, typed_order=True)),
    "ed_boj_rate_USDJPY_LO":    ("ALL", Cfg(clock="utc", costs=True, swaps=True, typed_order=True)),
    "ed_fomc_GER40_LO@ALL":     ("ALL", Cfg(clock="utc", costs=True, swaps=True, typed_order=True)),
}
MIRROR = {"ed_fomc_US30_LO": "ed_fomc_US30_SS", "ed_fomc_GER40_LO": "ed_fomc_GER40_SS",
          "ed_cpi_us_XAUUSD_LO": "ed_cpi_us_XAUUSD_SS",
          "ed_fomc_USDJPY_LO": "ed_fomc_USDJPY_SS",
          "ed_boj_rate_USDJPY_LO": "ed_boj_rate_USDJPY_SS",
          "ed_fomc_GER40_LO@ALL": "ed_fomc_GER40_SS",
          "me_fom_nfp_cpi_XAUUSD_+1": "me_fom_nfp_cpi_EURUSD_-1"}


def series_for(sid, cfg, specs, rf):
    s = specs[sid.split("@")[0]]
    tr = FAMILY_HANDLERS[s.family](s.params, cfg)
    if not tr.empty:
        tr = tr[pd.to_datetime(tr["exit_date"]) >= FLOOR]
    r, exc = evaluate_trades(sid, s.name, tr, rf, n_trials=142, n_boot=5000,
                             mc_runs=5000, return_series=True)
    return r, exc, tr


def main():
    specs = {s.id: s for s in build_specs()}
    rf = load_rf_daily()
    base = pd.read_csv(f"{OUT}/summary_base.csv")
    sh = base["sharpe_excess"].replace([np.inf, -np.inf], np.nan).dropna().tolist()
    t2 = pd.read_csv(f"{OUT}/tier2_base.csv")
    sh_all = sh + t2["sharpe_excess"].dropna().tolist()
    n_obs = int(base["n_days"].replace(0, np.nan).median())
    std_emp = estimate_std_sr_trials(sh_all, periods_per_year=252, n_obs=n_obs)
    std_floor = sampling_noise_floor_sr(n_obs, 252)

    print(f"n_obs (median) = {n_obs}")
    print(f"std_sr_trials  empirical = {std_emp:.4f} | sampling floor = {std_floor:.4f}")

    sleeve = overnight_sleeve_daily()
    print(f"overnight sleeve: N={len(sleeve)} bdays  "
          f"{sleeve.index[0].date()} -> {sleeve.index[-1].date()}  "
          f"active days={(sleeve != 0).sum()}  SR={_sharpe(sleeve.values, 252):.3f}")

    rows = []
    for sid, (cfgname, cfg) in CANDIDATES.items():
        r, exc, tr = series_for(sid, cfg, specs, rf)
        wf = walk_forward_folds(exc, n_folds=5, min_train_years=1.5)
        bs = block_bootstrap_sharpe(exc.values, n_boot=5000, block_len=5)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DSRCalibrationWarning)
            d_emp = deflated_sharpe_ratio(exc.values, n_trials=162, periods_per_year=252,
                                          rf=0.0, std_sr_trials=std_emp)
            d_flr = deflated_sharpe_ratio(exc.values, n_trials=162, periods_per_year=252,
                                          rf=0.0, std_sr_trials=std_floor)
        # mirror (two-sided support, L25/L42)
        msid = MIRROR.get(sid)
        m_sr = np.nan
        if msid and msid in specs:
            mr, mexc, mtr = series_for(msid, cfg, specs, rf)
            m_sr = mr.sharpe_excess
        # correlation to the deployed overnight sleeve
        j = pd.concat([exc.rename("cand"), sleeve.rename("sleeve")], axis=1).dropna()
        rho = float(j["cand"].corr(j["sleeve"])) if len(j) > 30 else np.nan
        both = j[(j["cand"] != 0) & (j["sleeve"] != 0)]
        rho_active = float(both["cand"].corr(both["sleeve"])) if len(both) > 30 else np.nan
        rows.append({
            "id": sid, "config": cfgname, "n_trades": r.n_trades,
            "n_days": r.n_days, "n_per_year_emp": round(r.n_per_year_emp, 1),
            "gross_bps_per_trade": r.mean_bps_per_trade_gross,
            "net_bps_per_trade": r.mean_bps_per_trade_net,
            "cost_gate_ratio": r.cost_gate_ratio,
            "sharpe_excess": r.sharpe_excess, "max_dd_pct": r.max_dd_pct,
            "hac_t_lag6": r.hac_t_excess,
            "wf_n_folds": len(wf),
            "wf_pass_rate": sum(1 for f in wf if f["sr_test"] > 0) / len(wf) if wf else 0,
            "wf_sr_test": [round(f["sr_test"], 3) for f in wf],
            "boot_sr_lo95": bs["sr_lo95"], "boot_sr_hi95": bs["sr_hi95"],
            "boot_excludes_0": bool(bs["sr_lo95"] > 0),
            "dsr_emp_disp": d_emp["dsr"], "dsr_sampling_floor": d_flr["dsr"],
            "sr_benchmark_emp": d_emp["sr_benchmark"],
            "sr_benchmark_floor": d_flr["sr_benchmark"],
            "mirror_id": msid, "mirror_sharpe": m_sr,
            "rho_overnight_sleeve": rho, "rho_overlap_days_only": rho_active,
            "n_overlap_days": int(len(both)),
            "ftmo_p_pass_p1": r.ftmo_p_pass_p1,
        })
        print(f"{sid:28s} SR={r.sharpe_excess:.3f} t={r.hac_t_excess:.2f} "
              f"WF={len(wf)}f {rows[-1]['wf_pass_rate']:.0%} "
              f"CI=[{bs['sr_lo95']:.3f},{bs['sr_hi95']:.3f}] "
              f"DSR_emp={d_emp['dsr']:.2e} DSR_floor={d_flr['dsr']:.2e} "
              f"rho={rho:+.3f} mirror_SR={m_sr:.3f}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/survivor_diagnostics.csv", index=False)
    meta = {"std_sr_trials_empirical": std_emp, "std_sr_trials_sampling_floor": std_floor,
            "n_obs_median": n_obs, "n_trials": 162,
            "sleeve_sharpe": _sharpe(sleeve.values, 252),
            "sleeve_n_bdays": int(len(sleeve)),
            "sleeve_active_days": int((sleeve != 0).sum())}
    with open(f"{OUT}/dsr_calibration.json", "w") as f:
        json.dump(meta, f, indent=2)
    sleeve.to_frame("ret").to_csv(f"{OUT}/overnight_sleeve_daily.csv")


if __name__ == "__main__":
    main()
