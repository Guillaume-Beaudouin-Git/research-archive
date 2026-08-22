"""Re-audit of the top10_test funnel: baseline reproduction + 6 defects,
each repaired ONE AT A TIME, then all together.

Usage: python3 run_reaudit.py [--sample-floor 2019-01-01]
Writes out/summary_<config>.csv for every config.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import asdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strategies_repaired import build_specs, FAMILY_HANDLERS, Cfg
from engine import evaluate_trades, load_rf_daily, amtp_bonferroni

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")

# (config name, Cfg for the trade generator, eval kwargs)
CONFIGS = [
    ("base",  Cfg(),                      dict(dsr_fixed=False, floor_mode="ratchet")),
    ("D1_dsr", Cfg(),                     dict(dsr_fixed=True,  floor_mode="ratchet")),
    ("D2_clock", Cfg(clock="utc"),        dict(dsr_fixed=False, floor_mode="ratchet")),
    ("D3_costs", Cfg(costs=True),         dict(dsr_fixed=False, floor_mode="ratchet")),
    ("D4_floor", Cfg(),                   dict(dsr_fixed=False, floor_mode="static")),
    ("D5_swaps", Cfg(swaps=True),         dict(dsr_fixed=False, floor_mode="ratchet")),
    ("D6_order", Cfg(typed_order=True),   dict(dsr_fixed=False, floor_mode="ratchet")),
    ("ALL",   Cfg(clock="utc", costs=True, swaps=True, typed_order=True),
     dict(dsr_fixed=True, floor_mode="static")),
]


def run_config(name, cfg, ev, specs, rf, floor, n_boot, mc_runs):
    rows, series = [], {}
    t0 = time.time()
    for i, s in enumerate(specs):
        try:
            tr = FAMILY_HANDLERS[s.family](s.params, cfg)
            if not tr.empty and floor is not None:
                tr = tr[pd.to_datetime(tr["exit_date"]) >= floor]
            r, exc = evaluate_trades(s.id, s.name, tr, rf, n_trials=len(specs),
                                     n_boot=n_boot, mc_runs=mc_runs,
                                     return_series=True, **ev)
        except Exception as e:                      # noqa: BLE001
            from engine import Res
            r, exc = Res(id=s.id, name=s.name, notes=f"ERROR: {e}"), None
        r.family, r.asset_class, r.order_type = s.family, s.asset_class, s.order_type
        rows.append(asdict(r))
        if exc is not None:
            series[s.id] = exc
        if (i + 1) % 40 == 0:
            print(f"  [{name}] {i+1}/{len(specs)}  {time.time()-t0:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    df["amtp_p_value"] = amtp_bonferroni(df["hac_t_excess"].tolist())
    return df, series


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-floor", default="2019-01-01")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--mc-runs", type=int, default=2000)
    ap.add_argument("--configs", default="")
    a = ap.parse_args()
    floor = pd.Timestamp(a.sample_floor) if a.sample_floor else None
    os.makedirs(OUT, exist_ok=True)
    specs = build_specs()
    rf = load_rf_daily()
    todo = [c for c in CONFIGS if not a.configs or c[0] in a.configs.split(",")]

    # Trial dispersion for the REPAIRED DSR: the empirical sd of the family's
    # Sharpes (dsr.estimate_std_sr_trials), floored at the sampling noise.
    # Requires the baseline pass first, so it is computed lazily.
    std_sr = None
    base_path = f"{OUT}/summary_base.csv"

    def _std_sr():
        from dsr import estimate_std_sr_trials
        b = pd.read_csv(base_path)
        sh = b["sharpe_excess"].replace([np.inf, -np.inf], np.nan).dropna()
        n_obs = int(b["n_days"].replace(0, np.nan).median())
        v = estimate_std_sr_trials(sh.tolist(), periods_per_year=252, n_obs=n_obs)
        print(f"  std_sr_trials = {v:.4f} (n_obs median {n_obs}, "
              f"observed sd {sh.std(ddof=1):.4f})", flush=True)
        return v

    for name, cfg, ev in todo:
        print(f"=== {name} ===", flush=True)
        ev = dict(ev)
        if ev.get("dsr_fixed") and os.path.exists(base_path):
            if std_sr is None:
                std_sr = _std_sr()
            ev["std_sr_trials"] = std_sr
        df, series = run_config(name, cfg, ev, specs, rf, floor, a.n_boot, a.mc_runs)
        df.to_csv(f"{OUT}/summary_{name}.csv", index=False)
        if name in ("base", "ALL"):
            pd.DataFrame(series).to_parquet(f"{OUT}/series_{name}.parquet")
        n_rp = int(df["research_pass"].sum())
        strict = df[(df.sharpe_excess > 0.7) & (df.max_dd_pct > -0.25)
                    & (df.wf_pass_rate > 0.5) & (df.hac_t_excess > 2.5) & df.dsr_passes]
        print(f"  research_pass={n_rp}  strict_survivors={len(strict)}"
              f"  {list(strict.id)}", flush=True)


if __name__ == "__main__":
    main()
