"""Step 3: mandatory controls on every candidate that crosses at the corrected cost.

Nothing here is a re-optimisation. Each block is a falsifier written before it
was run:

  L25  two-sided        - the funnel's `_SS` legs are `-side_long`, an exact
                          mechanical inverse. Verified, then replaced by a real
                          disjoint-leg construction where the spec admits one.
  L38  beta-orthogonality - regress the sleeve on a vol-targeted buy-and-hold of
                          its primary asset. R^2 > 30% => beta timing, not a sleeve.
  L58  matched placebo  - the placebo pool mean must equal the UNCONDITIONAL
                          expectation of the trade shape, else the placebo is
                          biased, not the signal.
  L59  delay+1          - entry AND exit re-priced one bar later.
  DSR  corrected        - canonical dsr.py with a MEASURED trial dispersion taken
                          from the 142 funnel Sharpes (framework.py's DSR uses
                          sigma_SR = 1.0, the known-broken inference layer).

Kill rules, written before running (pre-registration, N2 if ever claimed):
  K1  R^2 vs vol-targeted long gold > 0.30 on active days  -> not a new sleeve.
  K2  event-day mean <= unconditional mean of the same trade shape (one-sided,
      HAC t of the DIFFERENCE < 2.0)                        -> no event alpha.
  K3  actual mean below the 90th percentile of the matched placebo -> REJECTED.
  K4  net mean bps/trade at C3_tail <= 0                    -> cost-dead in the tail.
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
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")

from regold_lib import bs, fw, TOP10, CostModel, measured_costs  # noqa: E402
from regold_lib import METAL_COMM_RT_BPS, SLIP_SIDE_MODEL  # noqa: E402
import dsr as DSR  # noqa: E402

RNG = np.random.default_rng(20260801)


def hac_t(x, lag=6):
    return fw.hac_tstat(np.asarray(x, float), lag=lag)


# ---------------------------------------------------------------------------
# Trade-shape replicas: the SAME geometry, applied to every eligible day.
# ---------------------------------------------------------------------------

def shape_pre_event(instrument="XAUUSD"):
    """close(T-1) -> first M1 bar open at/after the release clock time on T.

    Returns a Series indexed by day T of gross bps for a LONG unit, for every
    trading day, using the modal release time of the funnel's event file.
    """
    daily = bs.get_daily(instrument)
    m1 = bs.get_m1(instrument)
    ev = pd.concat([bs.get_events(e) for e in ("FOMC", "NFP_US", "CPI_US")])
    tmode = ev["time_utc"].dropna().mode().iloc[0]
    hh, mm = (int(v) for v in tmode.split(":"))

    mask = (m1.index.hour == hh) & (m1.index.minute == mm)
    px_at = m1[mask].groupby(m1[mask].index.normalize())["open"].first()
    prev_close = daily["close"].shift(1)
    common = px_at.index.intersection(prev_close.dropna().index)
    g = (px_at.loc[common] / prev_close.loc[common] - 1.0) * 1e4
    return g.dropna(), f"{hh:02d}:{mm:02d}"


def shape_tom(instrument="XAUUSD"):
    """open(T) -> close(T+1), for every trading day (the calendar family shape)."""
    d = bs.get_daily(instrument)
    g = (d["close"].shift(-1) / d["open"] - 1.0) * 1e4
    return g.dropna(), "open->next close"


def event_days(types):
    ev = pd.concat([bs.get_events(t) for t in types])
    return pd.DatetimeIndex(sorted(set(pd.to_datetime(ev["date"]).dt.normalize())))


def tom_days(instrument="XAUUSD"):
    d = bs.get_daily(instrument)
    dom = d.index.day
    return d.index[(dom >= 27) | (dom <= 3)]


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

def control_placebo(shape: pd.Series, sel: pd.DatetimeIndex, n_boot=5000):
    """L49 + L58 matched calendar placebo.

    Primary placebo = CIRCULAR SHIFT of the selection mask along the trading-day
    grid. It preserves the count AND the clustering of the selection exactly
    (turn-of-month days come in runs of 6-7), which an iid label shuffle
    destroys. An iid shuffle is reported alongside as the loose bound.

    L58 control: the placebo pool mean must equal the UNCONDITIONAL expectation
    of the same trade shape. If it does not, the placebo is biased, not the
    signal.
    """
    sel = shape.index.intersection(sel)
    n = len(shape)
    k = len(sel)
    vals = shape.values
    mask = shape.index.isin(sel)
    pool = shape[~mask]
    uncond = float(shape.mean())
    actual = float(shape.loc[sel].mean())

    shifts = RNG.integers(1, n, size=n_boot)
    means_shift = np.array([vals[np.roll(mask, int(s))].mean() for s in shifts])

    perm = np.argsort(RNG.random((n_boot, n)), axis=1)[:, :k]
    means_iid = vals[perm].mean(axis=1)

    sel_vals = shape.loc[sel].values
    return dict(
        n_selected=k, n_pool=int(len(pool)),
        mean_actual_bps=actual,
        mean_unconditional_bps=uncond,
        mean_pool_bps=float(pool.mean()),
        l58_pool_minus_uncond_bps=float(pool.mean() - uncond),
        excess_over_unconditional_bps=float(actual - uncond),
        t_hac_selected_vs_zero=float(hac_t(sel_vals)),
        t_hac_selected_vs_unconditional=float(hac_t(sel_vals - uncond)),
        placebo_shift_p50=float(np.percentile(means_shift, 50)),
        placebo_shift_p90=float(np.percentile(means_shift, 90)),
        placebo_shift_p95=float(np.percentile(means_shift, 95)),
        pct_of_placebo_shift=float((means_shift < actual).mean()),
        placebo_iid_p90=float(np.percentile(means_iid, 90)),
        pct_of_placebo_iid=float((means_iid < actual).mean()),
    )


def control_beta(vt: pd.Series, instrument="XAUUSD"):
    """L38. Regress the vol-targeted sleeve on a vol-targeted buy-and-hold."""
    import statsmodels.api as sm
    d = bs.get_daily(instrument)
    bh = d["close"].pct_change().dropna()
    bh_vt = fw.vol_target(bh, target_annual=0.08, lookback=63)
    bh_vt = bh_vt.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    out = {}
    for tag, idx in (("all_days", vt.index),
                     ("active_days", vt[vt != 0].index)):
        i = pd.DatetimeIndex(idx).intersection(bh_vt.index)
        if len(i) < 60:
            out[tag] = dict(n=len(i))
            continue
        y = vt.reindex(i).values
        X = sm.add_constant(bh_vt.reindex(i).values)
        m = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
        out[tag] = dict(n=int(len(i)), alpha_bps_per_day=float(m.params[0] * 1e4),
                        t_alpha=float(m.tvalues[0]), beta=float(m.params[1]),
                        t_beta=float(m.tvalues[1]), r2=float(m.rsquared))
    return out


def control_delay(spec, model: CostModel, shifts_entry=(0, 1, 5), shifts_exit=(0, 1, 5, 15)):
    """L59. Re-price entry and exit one/five/fifteen minutes later.

    These specs carry no stop, so the L59 stop-fill bias does not apply; what is
    testable is whether the edge survives being executed slightly late.
    """
    inst = spec.params["instrument"]
    m1 = bs.get_m1(inst)
    daily = bs.get_daily(inst)
    fam = spec.family

    rows = []
    if fam in ("event_drift", "multi_event"):
        types = ([spec.params["event_type"]] if fam == "event_drift"
                 else spec.params["event_types"])
        ev = pd.concat([bs.get_events(t) for t in types]).drop_duplicates("date").sort_values("date")
        side = spec.params["side"]
        for se in shifts_entry:
            for sx in shifts_exit:
                g = []
                for _, e in ev.iterrows():
                    ed = pd.Timestamp(e["date"])
                    prev = daily.index[daily.index < ed]
                    if not len(prev):
                        continue
                    t1 = prev[-1]
                    if se == 0:
                        entry = daily.loc[t1, "close"]
                    else:
                        b = m1[m1.index > t1 + pd.Timedelta(days=1) - pd.Timedelta(minutes=1)]
                        b = m1[m1.index >= t1.normalize() + pd.Timedelta(hours=23, minutes=59)]
                        b = b[b.index >= t1.normalize() + pd.Timedelta(minutes=int(se))
                              + pd.Timedelta(days=1)]
                        if not len(b):
                            continue
                        entry = float(b.iloc[0]["open"])
                    ts = e["time_utc"] if pd.notna(e["time_utc"]) else "13:30"
                    try:
                        hh, mm = (int(v) for v in ts.split(":"))
                    except Exception:                                     # noqa: BLE001
                        hh, mm = 13, 30
                    rel = ed + pd.Timedelta(hours=hh, minutes=mm + int(sx))
                    b = m1[m1.index >= rel]
                    if not len(b) or (b.index[0] - rel) > pd.Timedelta(hours=4):
                        continue
                    ex = float(b.iloc[0]["open"])
                    if not np.isfinite(entry) or entry <= 0:
                        continue
                    g.append(side * (ex - entry) / entry * 1e4)
                g = np.array(g)
                if len(g) < 20:
                    continue
                net = g - model.rt_bps + (model.swap_long if side > 0 else model.swap_short)
                rows.append(dict(entry_shift_min=se, exit_shift_min=sx, n=len(g),
                                 gross_bps=float(g.mean()), net_bps=float(net.mean()),
                                 t_hac_net=float(hac_t(net))))
    elif fam == "calendar":
        side = spec.params["side"]
        sel = tom_days(inst)
        d = daily
        for se in shifts_entry:
            for sx in (0,):
                g = []
                for date in sel:
                    i = d.index.get_indexer([date])[0]
                    if i < 0 or i + 1 >= len(d):
                        continue
                    if se == 0:
                        entry = d.iloc[i]["open"]
                    else:
                        b = m1[m1.index >= date + pd.Timedelta(minutes=int(se))]
                        b = b[b.index <= date + pd.Timedelta(hours=6)]
                        if not len(b):
                            continue
                        entry = float(b.iloc[0]["open"])
                    ex = d.iloc[i + 1]["close"]
                    if not np.isfinite(entry) or entry <= 0:
                        continue
                    g.append(side * (ex - entry) / entry * 1e4)
                g = np.array(g)
                if len(g) < 20:
                    continue
                net = g - model.rt_bps + (model.swap_long if side > 0 else model.swap_short)
                rows.append(dict(entry_shift_min=se, exit_shift_min=sx, n=len(g),
                                 gross_bps=float(g.mean()), net_bps=float(net.mean()),
                                 t_hac_net=float(hac_t(net))))
    return rows


def control_two_sided(spec):
    """L25 done honestly.

    The funnel's short leg is `-side_long`: gross_SS == -gross_LO by
    construction, so it carries zero information. A real two-sided test needs a
    CONDITIONER whose sign flips the leg, and both legs must be positive
    independently. These specs are unconditional LONG: no such conditioner
    exists in the spec, so the honest verdict is 'no two-sided form'.

    What CAN be tested with disjoint legs is whether the drift is a property of
    the event or of the prevailing gold trend: split the same events on the sign
    of the trailing 60-day gold return (a conditioner disjoint from the trade
    window) and require the drift on BOTH sides.
    """
    inst = spec.params["instrument"]
    daily = bs.get_daily(inst)
    trend = daily["close"].pct_change(60).shift(1)

    if spec.family in ("event_drift", "multi_event"):
        types = ([spec.params["event_type"]] if spec.family == "event_drift"
                 else spec.params["event_types"])
        sel = event_days(types)
        shape, _ = shape_pre_event(inst)
    else:
        sel = tom_days(inst)
        shape, _ = shape_tom(inst)

    sel = shape.index.intersection(sel)
    tr = trend.reindex(sel)
    out = {}
    for tag, m in (("gold_uptrend", tr > 0), ("gold_downtrend", tr <= 0)):
        s = shape.loc[sel[m.fillna(False).values]]
        out[tag] = dict(n=int(len(s)), mean_bps=float(s.mean()) if len(s) else np.nan,
                        t_hac=float(hac_t(s.values)) if len(s) > 20 else np.nan)
    return out


# ---------------------------------------------------------------------------

def main():
    orig = pd.read_csv(TOP10 / "results/summary_batch_142.csv")
    mc = measured_costs()
    au = mc["XAUUSD"]
    C1 = CostModel("C1_measured",
                   au["spread_med_tail750"] + 2 * SLIP_SIDE_MODEL + METAL_COMM_RT_BPS,
                   au["swap_long_med_2020"], au["swap_short_med_2020"])

    specs = {s.id: s for s in bs.build_specs()}
    survivors = ["me_fom_nfp_cpi_XAUUSD_+1", "ed_cpi_us_XAUUSD_LO", "cal_XAUUSD_tom_+1"]

    vt_wide = pd.read_csv(OUT / "daily_vt_series.csv", index_col=0, parse_dates=True)

    # ---- corrected DSR, measured trial dispersion from the 142 funnel Sharpes
    grid = orig["sharpe_excess"].dropna().values
    recost = pd.read_csv(OUT / "recost.csv")

    report = {"cost_model_C1": dict(rt_bps=C1.rt_bps, swap_long=C1.swap_long,
                                    swap_short=C1.swap_short),
              "funnel_trial_dispersion": {
                  "n_trials_batch": int(len(grid)),
                  "std_sr_observed": float(np.std(grid, ddof=1)),
              },
              "mirror_check_L25": {}, "survivors": {}}

    # L25 mirror evidence over the whole gold perimeter
    for a, b in (("ed_fomc_XAUUSD_LO", "ed_fomc_XAUUSD_SS"),
                 ("ed_nfp_us_XAUUSD_LO", "ed_nfp_us_XAUUSD_SS"),
                 ("ed_cpi_us_XAUUSD_LO", "ed_cpi_us_XAUUSD_SS"),
                 ("gv_XAUUSD_t1.5_cont", "gv_XAUUSD_t1.5_fade"),
                 ("im_XAUUSD_1430_1530_mom", "im_XAUUSD_1430_1530_fade")):
        ga = recost[(recost.id == a) & (recost.model == "C0_catalog")]["mean_bps_per_trade_gross"]
        gb = recost[(recost.id == b) & (recost.model == "C0_catalog")]["mean_bps_per_trade_gross"]
        if len(ga) and len(gb):
            report["mirror_check_L25"][f"{a}|{b}"] = dict(
                gross_a=float(ga.iloc[0]), gross_b=float(gb.iloc[0]),
                sum=float(ga.iloc[0] + gb.iloc[0]))

    shapes = {}
    shapes["pre_event"] = shape_pre_event("XAUUSD")
    shapes["tom"] = shape_tom("XAUUSD")

    for sid in survivors:
        spec = specs[sid]
        blk = {"family": spec.family}
        row = recost[(recost.id == sid) & (recost.model == "C1_measured")].iloc[0]
        blk["at_C1"] = {k: float(row[k]) for k in
                        ("mean_bps_per_trade_net", "sharpe_excess", "hac_t_excess",
                         "max_dd_pct", "wf_pass_rate", "p_pass_2phase_static",
                         "med_days_2phase_static", "p_bust_static")}
        row3 = recost[(recost.id == sid) & (recost.model == "C3_tail")].iloc[0]
        blk["at_C3_tail"] = {k: float(row3[k]) for k in
                             ("mean_bps_per_trade_net", "sharpe_excess",
                              "p_pass_2phase_static")}

        # ---- DSR corrected
        vt = vt_wide[f"{sid}|C1_measured"].dropna()
        sd_used = DSR.estimate_std_sr_trials(grid, periods_per_year=252, n_obs=len(vt))
        for n_tr, lab in ((16, "N=16 gold perimeter"), (142, "N=142 funnel batch"),
                          (164, "N=164 program funnel")):
            o = DSR.deflated_sharpe_ratio(vt.values, n_trials=n_tr, periods_per_year=252,
                                          rf=0.0, mean_sr_trials=0.0, std_sr_trials=sd_used)
            blk.setdefault("dsr_corrected", {})[lab] = dict(
                sharpe=o["sharpe"], sr_benchmark=o["sr_benchmark"], dsr=o["dsr"],
                passed=bool(o["passed"]), std_sr_trials=float(sd_used))

        # ---- L38
        blk["L38_beta_orthogonality"] = control_beta(vt)

        # ---- L58/L49 placebo + unconditional
        if spec.family in ("event_drift", "multi_event"):
            shape, clock = shapes["pre_event"]
            types = ([spec.params["event_type"]] if spec.family == "event_drift"
                     else spec.params["event_types"])
            sel = event_days(types)
            blk["trade_shape"] = f"close(T-1) -> {clock} on T"
        else:
            shape, clock = shapes["tom"]
            sel = tom_days()
            blk["trade_shape"] = clock
        blk["L58_placebo"] = control_placebo(shape, sel)

        # ---- L25 disjoint-leg substitute
        blk["L25_disjoint_legs"] = control_two_sided(spec)

        # ---- L59 delay
        blk["L59_delay"] = control_delay(spec, C1)

        report["survivors"][sid] = blk
        print(f"--- {sid} done")

    (OUT / "controls.json").write_text(json.dumps(report, indent=2, default=float))
    print(json.dumps(report, indent=2, default=float))


if __name__ == "__main__":
    main()
