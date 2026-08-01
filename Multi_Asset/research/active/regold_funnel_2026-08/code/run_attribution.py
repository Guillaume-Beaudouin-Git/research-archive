"""Step 4: attribute the re-screen delta to the SPREAD fix vs the SWAP fix,
and the closing sanity numbers (gold drift over the window, trial dispersion
with and without the mechanical mirrors, Sidak AMTP).

All three survivors are LONG, 1 night, so the per-trade charge decomposes in
closed form; the Sharpe / p(pass) legs still need a re-run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")

from regold_lib import bs, fw, TOP10, CACHE, CostModel, measured_costs  # noqa: E402
from regold_lib import METAL_COMM_RT_BPS, SLIP_SIDE_MODEL, ftmo_mc_static  # noqa: E402
import run_batch as rb  # noqa: E402
import dsr as DSR  # noqa: E402

SURV = ["me_fom_nfp_cpi_XAUUSD_+1", "ed_cpi_us_XAUUSD_LO", "cal_XAUUSD_tom_+1"]


def main():
    mc = measured_costs()
    au = mc["XAUUSD"]
    rt_meas = au["spread_med_tail750"] + 2 * SLIP_SIDE_MODEL + METAL_COMM_RT_BPS

    MODELS = {
        "C0_catalog":      CostModel("C0_catalog", 3.50, -2.9, -2.9),
        "D1_spread_only":  CostModel("D1_spread_only", rt_meas, -2.9, -2.9),
        "D2_swap_only":    CostModel("D2_swap_only", 3.50,
                                     au["swap_long_med_2020"], au["swap_short_med_2020"]),
        "C1_measured":     CostModel("C1_measured", rt_meas,
                                     au["swap_long_med_2020"], au["swap_short_med_2020"]),
    }

    specs = {s.id: s for s in bs.build_specs()}
    rf = fw.load_rf_daily()
    rows = []
    for sid in SURV:
        spec = specs[sid]
        tr = bs.FAMILY_HANDLERS[spec.family](spec.params)
        for mname, m in MODELS.items():
            t = m.apply(tr)
            r = rb.evaluate_trades(sid, spec.name, t, rf, n_amtp_trials=142)
            dmin, dmax = pd.to_datetime(t["exit_date"]).min(), pd.to_datetime(t["exit_date"]).max()
            daily = bs.trades_to_daily_pnl(t, pd.date_range(dmin, dmax, freq="B"))
            bd = pd.date_range(daily.index.min(), daily.index.max(), freq="B")
            daily = daily.reindex(bd).fillna(0.0)
            vt = fw.vol_target(daily, target_annual=0.08, lookback=63)
            vt = vt.replace([np.inf, -np.inf], np.nan).fillna(0.0)
            sim = ftmo_mc_static(vt, n_runs=5000)
            rows.append(dict(id=sid, model=mname, rt_bps=round(m.rt_bps, 3),
                             swapL=round(m.swap_long, 3),
                             charge_per_trade=round(m.rt_bps - m.swap_long, 3),
                             net_bps=r.mean_bps_per_trade_net,
                             sharpe_excess=r.sharpe_excess,
                             t_hac=r.hac_t_excess,
                             p_pass_2phase=sim["p_pass_p1_p2"],
                             med_days_2phase=sim["med_days_total"]))
        print("done", sid)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "cost_attribution.csv", index=False)
    print(df.round(4).to_string(index=False))

    # ---- closing numbers -------------------------------------------------
    d = bs.get_daily("XAUUSD")
    yrs = (d.index[-1] - d.index[0]).days / 365.25
    tot = d["close"].iloc[-1] / d["close"].iloc[0] - 1
    orig = pd.read_csv(TOP10 / "results/summary_batch_142.csv")
    s = orig["sharpe_excess"].dropna()

    # mirror-free trial dispersion: keep one leg of each exact mirror pair
    g = orig.set_index("id")["mean_bps_per_trade_gross"]
    mirror_ids = set()
    for a in g.index:
        for b in g.index:
            if a < b and np.isfinite(g[a]) and abs(g[a] + g[b]) < 1e-9 and abs(g[a]) > 1e-9:
                mirror_ids.add(b)
    s_nm = orig[~orig["id"].isin(mirror_ids)]["sharpe_excess"].dropna()

    tstats = orig["hac_t_excess"].dropna()
    close = {
        "window": f"{d.index[0].date()} -> {d.index[-1].date()} ({yrs:.2f}y)",
        "gold_total_return_pct": round(tot * 100, 1),
        "gold_annualised_pct": round(((1 + tot) ** (1 / yrs) - 1) * 100, 2),
        "gold_mean_daily_bps": round(float(d["close"].pct_change().mean() * 1e4), 2),
        "n_exact_mirror_legs_in_142": len(mirror_ids),
        "std_sr_trials_all142": round(float(s.std(ddof=1)), 4),
        "std_sr_trials_mirror_free": round(float(s_nm.std(ddof=1)), 4),
        "n_mirror_free": int(len(s_nm)),
    }
    for lab, sd, n in (("all142", s.std(ddof=1), 142),
                       ("mirror_free", s_nm.std(ddof=1), len(s_nm))):
        close[f"sr_benchmark_{lab}"] = round(float(DSR._expected_max_sr(n, 0.0, sd)), 3)

    # Sidak AMTP on the surviving t-stats, against the funnel counts
    vt_wide = pd.read_csv(OUT / "daily_vt_series.csv", index_col=0, parse_dates=True)
    rec = pd.read_csv(OUT / "recost.csv")
    close["amtp_sidak"] = {}
    for sid in SURV:
        t = float(rec[(rec.id == sid) & (rec.model == "C1_measured")]["hac_t_excess"].iloc[0])
        p = 2 * (1 - norm.cdf(abs(t)))
        close["amtp_sidak"][sid] = {
            "t_hac": round(t, 3), "p_raw": round(p, 5),
            "p_sidak_N16": round(1 - (1 - p) ** 16, 4),
            "p_sidak_N142": round(1 - (1 - p) ** 142, 4),
            "p_sidak_N164": round(1 - (1 - p) ** 164, 4),
        }
    (OUT / "closing_numbers.json").write_text(json.dumps(close, indent=2))
    print(json.dumps(close, indent=2))


if __name__ == "__main__":
    main()
