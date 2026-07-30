"""Confirmation on REAL historical paths: the canonical cleanroom retry funnel.

The bootstrap answer (run_overlay.py) resamples blocks of the book's returns. This script
answers the same question on the actual market history with the project's canonical
metric — cohort starts every 7 days, 2-step funnel, 91-day wall, retries — by injecting
the overlay into the engine's own sizing function via a wrapper (the engine file is never
modified). Same post-margin-cap semantics as build_book.run_book.
"""
from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd

import build_book as B
import regime_signals as S

E = B.E
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)

CFG_LIVE = dict(
    vm=14.0, p2_mult=1.2, on_w=0.6, orb_risk=0.0,
    breaker=0.30, taper=0.02, glide=0.5, pace=1, pace_k=1.0,
    ab_buf=0.02, ab_days=5, margin_cap=0.60, quantize=True,
    mrate=E.MRATE_SWING, brk_mode="daily", brk_needs_pos=True,
)

_ORIG = E._target_for_segment
_EXPO = None
_M = _WT = _ON = None


def _patched(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm):
    tgt, opened = _ORIG(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm)
    if tgt is None or _EXPO is None or _EXPO[i] == 1.0:
        return tgt, opened
    if s in (3, 4) and ON[i] > 0:
        leg = 3 if s == 3 else 2
        tgt = tgt.copy()
        tgt[leg] *= _EXPO[i]
        if cfg.get("quantize", True):
            step = E.LOT_UNITS[leg] * px0[leg] * E.VSTEP
            if np.isfinite(step) and step > 0:
                tgt[leg] = np.round(tgt[leg] / step) * step
    return tgt, opened


E._target_for_segment = _patched


def _init():
    global _M, _WT, _ON
    _M = B.build_market()
    _WT, _ON = B.mono_signals(pd.DatetimeIndex(_M["dates"]))


def _eval(expo):
    """p(campaign) and p(1-try) over cohort starts for one exposure schedule."""
    global _EXPO
    _EXPO = np.ones(_M["n"]) if expo is None else np.asarray(expo, float)
    starts = E.cohort_starts(_M, _M["dates"][0], _M["dates"][-1], step=7)
    starts = [i for i in starts if i < _M["n"] - 120]
    funded, times, attempts, one_try, deaths = [], [], [], [], []
    for i0 in starts:
        r = E.run_funnel(_M, i0, _WT, _ON, CFG_LIVE, wall=91)
        funded.append(r["funded"])
        attempts.append(r["attempts"])
        if r["funded"]:
            times.append(r["t"])
        p1 = E.run_phase(_M, i0, _WT, _ON, dict(CFG_LIVE, target=E.TARGET1, max_cal=91))
        one_try.append(p1["out"] == "pass")
        deaths.append(p1["out"])
    d = pd.Series(deaths).value_counts(normalize=True)
    return dict(
        n_cohorts=len(starts),
        p_campaign=float(np.mean(funded)),
        p_one_try=float(np.mean(one_try)),
        avg_attempts=float(np.mean(attempts)),
        median_days=float(np.median(times)) if times else float("nan"),
        p90_days=float(np.percentile(times, 90)) if times else float("nan"),
        d_bust_daily=float(d.get("bust_daily", 0.0)),
        d_bust_floor=float(d.get("bust_floor", 0.0)),
        d_timeout=float(d.get("timeout", 0.0)),
        d_abandon=float(d.get("abandon", 0.0)),
    )


def main(n_placebo=24):
    _init()
    dates = pd.DatetimeIndex(_M["dates"])
    ex = S.build_exposures(dates)
    n = len(dates)

    jobs = {"baseline": None}
    for v in ("O1_vixterm", "O2_ma200", "O3_both"):
        jobs[v] = ex[v].to_numpy()
    meta = json.loads((OUT / "meta.json").read_text())
    for v, d in meta["delever"].items():
        jobs[f"delever_vol_{v}"] = np.full(n, d["c"])

    with mp.Pool(8, initializer=_init) as pool:
        res = pool.map(_eval, list(jobs.values()))
    tab = pd.DataFrame(res, index=list(jobs.keys()))
    tab.to_csv(OUT / "cohort_table.csv")
    print("=== COHORT FUNNEL (real historical paths, 91-day wall, retries) ===")
    print(tab.to_string(float_format=lambda x: f"{x:.4f}"))

    # placebo band on the best overlay variant, cohort level
    best = tab.loc[["O1_vixterm", "O2_ma200", "O3_both"], "p_campaign"].idxmax()
    rng = np.random.default_rng(23)
    e = ex[best].to_numpy()
    shifts = rng.choice(np.arange(30, n - 30), size=n_placebo, replace=False)
    with mp.Pool(8, initializer=_init) as pool:
        pres = pool.map(_eval, [np.roll(e, int(s)) for s in shifts])
    pp = np.array([x["p_campaign"] for x in pres])
    p1 = np.array([x["p_one_try"] for x in pres])
    band = dict(best=best, n_placebo=int(n_placebo),
                real_p_campaign=float(tab.loc[best, "p_campaign"]),
                real_p_one_try=float(tab.loc[best, "p_one_try"]),
                base_p_campaign=float(tab.loc["baseline", "p_campaign"]),
                base_p_one_try=float(tab.loc["baseline", "p_one_try"]),
                placebo_campaign_mean=float(pp.mean()),
                placebo_campaign_p05=float(np.percentile(pp, 5)),
                placebo_campaign_p50=float(np.percentile(pp, 50)),
                placebo_campaign_p95=float(np.percentile(pp, 95)),
                placebo_campaign_max=float(pp.max()),
                pctile_real=float((pp < tab.loc[best, "p_campaign"]).mean()),
                placebo_onetry_p50=float(np.percentile(p1, 50)),
                placebo_onetry_p95=float(np.percentile(p1, 95)),
                pctile_real_onetry=float((p1 < tab.loc[best, "p_one_try"]).mean()))
    (OUT / "cohort_placebo.json").write_text(json.dumps(band, indent=2))
    print("\n=== COHORT PLACEBO BAND ===")
    print(json.dumps(band, indent=2))


if __name__ == "__main__":
    main()
