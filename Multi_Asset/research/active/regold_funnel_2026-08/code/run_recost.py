"""Step 1-2: inventory the gold perimeter, reproduce it at catalog cost,
then re-price it at the measured cost. No re-optimisation, no spec change.

Outputs (CSV, small):
  perimeter.csv     - the 16 XAUUSD-touching specs and their original verdict
  reproduction.csv  - original vs re-run at CATALOG cost (harness validation)
  recost.csv        - before/after under each cost denominator
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(HERE))

from regold_lib import (  # noqa: E402
    TOP10, MAIN, CostModel, measured_costs, ftmo_mc_static,
    METAL_COMM_RT_BPS, SLIP_SIDE_MODEL, SLIP_SIDE_MEDIAN, SLIP_SIDE_P95,
    bs, fw,
)
import run_batch as rb  # noqa: E402


GOLD_TOKEN = "XAU"


def gold_specs():
    return [s for s in bs.build_specs()
            if GOLD_TOKEN in s.id or GOLD_TOKEN in str(s.params)]


def evaluate(sid, name, trades, rf, n_trials, mc_kwargs=None):
    """run_batch.evaluate_trades, with the MLL ratchet replaced by the static
    floor. Everything upstream of the MC is byte-identical to the original."""
    res = rb.evaluate_trades(sid, name, trades, rf, n_amtp_trials=n_trials)
    d = res.__dict__.copy()
    if res.n_trades >= 20 and res.n_days > 0:
        dmin = pd.to_datetime(trades["exit_date"]).min()
        dmax = pd.to_datetime(trades["exit_date"]).max()
        daily = bs.trades_to_daily_pnl(trades, pd.date_range(dmin, dmax, freq="B"))
        bd = pd.date_range(daily.index.min(), daily.index.max(), freq="B")
        daily = daily.reindex(bd).fillna(0.0)
        vt = fw.vol_target(daily, target_annual=0.08, lookback=63)
        vt = vt.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        mc = ftmo_mc_static(vt, n_runs=5000, **(mc_kwargs or {}))
        d["p_pass_p1_static"] = mc["p_pass_p1"]
        d["p_pass_2phase_static"] = mc["p_pass_p1_p2"]
        d["p_bust_static"] = mc["p_bust"]
        d["med_days_p1_static"] = mc["med_days_p1"]
        d["med_days_2phase_static"] = mc["med_days_total"]
        d["_vt"] = vt
    return d


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    orig = pd.read_csv(TOP10 / "results/summary_batch_142.csv")
    specs_all = bs.build_specs()
    n_trials = len(specs_all)
    gs = gold_specs()
    print(f"total specs in funnel batch: {len(specs_all)}  |  gold-touching: {len(gs)}")

    mc = measured_costs()
    print(json.dumps(mc, indent=2))
    (OUT / "measured_costs.json").write_text(json.dumps(mc, indent=2))

    au = mc["XAUUSD"]
    ag = mc["XAGUSD"]

    # --- cost denominators -------------------------------------------------
    au_rt_audit = au["spread_med_tail750"] + 2 * SLIP_SIDE_MODEL + METAL_COMM_RT_BPS
    au_rt_centre = au["spread_med_2020"] + 2 * SLIP_SIDE_MEDIAN + METAL_COMM_RT_BPS
    au_rt_tail = au["spread_p75_2020"] + 2 * SLIP_SIDE_P95 + METAL_COMM_RT_BPS

    MODELS = {
        # what the funnel actually used
        "C0_catalog": CostModel("C0_catalog", 3.50, -2.9, -2.9,
                                "framework.py:29, 'per rules.md' - catalog, unmeasured"),
        # the audit's headline measured number, model slippage provision kept
        "C1_measured": CostModel("C1_measured", au_rt_audit,
                                 au["swap_long_med_2020"], au["swap_short_med_2020"],
                                 "spread_med(tail750) + 2x0.50 slip + 0.14 comm; swap measured 2020+"),
        # expectation-honest: realized median slippage instead of the p95-sized provision
        "C2_centre": CostModel("C2_centre", au_rt_centre,
                               au["swap_long_med_2020"], au["swap_short_med_2020"],
                               "spread_med(2020+) + 2x0.10 realized-median slip + comm"),
        # barrier-honest: p75 spread + p95 slippage on every trade
        "C3_tail": CostModel("C3_tail", au_rt_tail,
                             au["swap_long_med_2020"], au["swap_short_med_2020"],
                             "spread_p75(2020+) + 2x1.485 p95 slip + comm"),
    }
    for m in MODELS.values():
        print(f"{m.name:<14} RT={m.rt_bps:6.3f}  swapL={m.swap_long:6.3f}  swapS={m.swap_short:6.3f}  # {m.note}")

    rf = fw.load_rf_daily()

    ledgers, rows_repro, rows = {}, [], []
    vt_store = {}
    for spec in gs:
        try:
            tr = bs.FAMILY_HANDLERS[spec.family](spec.params)
        except Exception as e:                                    # noqa: BLE001
            rows.append(dict(id=spec.id, family=spec.family, model="ALL",
                             status=f"DATA-UNAVAILABLE: {type(e).__name__}: {e}"))
            print(f"  !! {spec.id}: {type(e).__name__}: {e}")
            continue
        if tr.empty:
            rows.append(dict(id=spec.id, family=spec.family, model="ALL",
                             status="DATA-UNAVAILABLE: empty ledger"))
            print(f"  !! {spec.id}: empty ledger")
            continue
        ledgers[spec.id] = tr

        for mname, model in MODELS.items():
            tr_m = model.apply(tr)
            d = evaluate(spec.id, spec.name, tr_m, rf, n_trials)
            vt = d.pop("_vt", None)
            if vt is not None:
                vt_store[(spec.id, mname)] = vt
            d.update(id=spec.id, family=spec.family, model=mname,
                     rt_bps=model.rt_bps, swapL=model.swap_long, swapS=model.swap_short)
            rows.append(d)
            if mname == "C0_catalog":
                o = orig[orig["id"] == spec.id]
                if len(o):
                    o = o.iloc[0]
                    rows_repro.append(dict(
                        id=spec.id, n_trades_orig=o["n_trades"], n_trades_new=d["n_trades"],
                        gross_orig=o["mean_bps_per_trade_gross"], gross_new=d["mean_bps_per_trade_gross"],
                        net_orig=o["mean_bps_per_trade_net"], net_new=d["mean_bps_per_trade_net"],
                        sr_orig=o["sharpe_excess"], sr_new=d["sharpe_excess"],
                        mdd_orig=o["max_dd_pct"], mdd_new=d["max_dd_pct"],
                        t_orig=o["hac_t_excess"], t_new=d["hac_t_excess"]))
        print(f"  ok {spec.id:<32} n={len(tr):>4}")

    pd.DataFrame(rows_repro).to_csv(OUT / "reproduction.csv", index=False)
    df = pd.DataFrame(rows)
    keep = ["id", "family", "model", "rt_bps", "swapL", "swapS", "n_trades",
            "mean_bps_per_trade_gross", "mean_bps_per_trade_net", "cost_gate_ratio",
            "sharpe_excess", "max_dd_pct", "hac_t_excess", "dsr", "dsr_passes",
            "wf_n_folds", "wf_pass_rate", "amtp_p_value",
            "p_pass_p1_static", "p_pass_2phase_static", "p_bust_static",
            "med_days_p1_static", "med_days_2phase_static",
            "ftmo_p_pass_p1", "ftmo_p_pass_p1_p2", "status", "notes"]
    for c in keep:
        if c not in df.columns:
            df[c] = np.nan
    df[keep].to_csv(OUT / "recost.csv", index=False)

    # perimeter table
    per = orig[orig["id"].isin([s.id for s in gs])][
        ["id", "n_trades", "mean_bps_per_trade_gross", "mean_bps_per_trade_net",
         "cost_gate_ratio", "sharpe_excess", "max_dd_pct", "hac_t_excess",
         "wf_pass_rate", "ftmo_p_pass_p1_p2", "research_pass", "propfirm_pass", "notes"]]
    per.to_csv(OUT / "perimeter.csv", index=False)

    # store vol-targeted series of the corrected screen for the control tests
    if vt_store:
        wide = pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in vt_store.items()
                             if k[1] in ("C0_catalog", "C1_measured")})
        wide.to_csv(OUT / "daily_vt_series.csv")

    print("\n=== reproduction check (catalog cost) ===")
    r = pd.DataFrame(rows_repro)
    if len(r):
        r["d_gross"] = (r["gross_new"] - r["gross_orig"]).abs()
        r["d_sr"] = (r["sr_new"] - r["sr_orig"]).abs()
        print(r[["id", "n_trades_orig", "n_trades_new", "d_gross", "d_sr"]].to_string(index=False))
        print(f"max |d_gross| = {r['d_gross'].max():.6f} bps   max |d_SR| = {r['d_sr'].max():.6f}")


if __name__ == "__main__":
    main()
