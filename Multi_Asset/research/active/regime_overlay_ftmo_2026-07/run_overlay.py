"""Driver: overlay vs placebo vs uniform de-lever, decided on p(pass) and time-to-funded.

Everything is frozen in PREREGISTRATION.md. Nothing here tunes a threshold.
"""
from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd

import build_book as B
import campaign as C
import regime_signals as S
from Portfolio.admission.barrier import BarrierConfig

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)

N_PLACEBO = 60          # circular rotations per variant
N_PATHS = 20_000        # main variants
N_PATHS_PLACEBO = 4_000  # placebo band (subset of the SAME paths -> still paired)
VARIANTS = ["O1_vixterm", "O2_ma200", "O3_both"]

_M = _WT = _ON = None


def _init():
    global _M, _WT, _ON
    _M = B.build_market()
    dates = pd.DatetimeIndex(_M["dates"])
    _WT, _ON = B.mono_signals(dates)


def _run(mult):
    return B.run_book(_M, _WT, _ON, B.CFG_MONO, mult)["ret"].to_numpy()


def _run_many(mults, workers=8):
    with mp.Pool(workers, initializer=_init) as pool:
        return pool.map(_run, mults)


def solve_delever(target_vol, base_vol, tol=5e-3, iters=6):
    """Constant multiplier reproducing `target_vol` daily volatility."""
    c = target_vol / base_vol
    for _ in range(iters):
        r = _run(np.full(len(_M["dates"]), c))
        v = r.std(ddof=1)
        if abs(v / target_vol - 1.0) < tol:
            return c, r, v
        c *= target_vol / v
    return c, r, v


def main():
    _init()
    dates = pd.DatetimeIndex(_M["dates"])
    n = len(dates)
    ex = S.build_exposures(dates)
    ex.to_parquet(CACHE / "exposures.parquet")
    S.assert_no_lookahead(dates)
    print("look-ahead assertion: PASS")

    series = {}
    series["baseline"] = _run(np.ones(n))
    ov = _run_many([ex[v].to_numpy() for v in VARIANTS])
    for v, r in zip(VARIANTS, ov):
        series[v] = r

    base_vol = series["baseline"].std(ddof=1)
    delever = {}
    for v in VARIANTS:
        tv = series[v].std(ddof=1)
        c, r, got = solve_delever(tv, base_vol)
        delever[v] = {"c": float(c), "vol_target": float(tv), "vol_got": float(got)}
        series[f"delever_vol_{v}"] = r
        cm = float(ex[v].mean())
        series[f"delever_mean_{v}"] = _run(np.full(n, cm))
        delever[v]["c_mean_expo"] = cm
    print("de-lever calibration:", json.dumps(delever, indent=2))

    # ---- placebo: circular rotations, identical duty cycle and run-length structure
    rng = np.random.default_rng(11)
    placebo_series = {}
    for v in VARIANTS:
        e = ex[v].to_numpy()
        shifts = rng.choice(np.arange(30, n - 30), size=N_PLACEBO, replace=False)
        mults = [np.roll(e, int(s)) for s in shifts]
        placebo_series[v] = _run_many(mults)
        np.save(CACHE / f"placebo_shifts_{v}.npy", shifts)
        print(f"placebo {v}: {N_PLACEBO} rotations done")

    np.savez_compressed(CACHE / "series.npz", **series)

    # ---- campaign evaluation, all variants on the SAME draws
    cfg = BarrierConfig()
    C.validate(series["baseline"], cfg, n_paths=500)
    idx = C.draw_paths(n, N_PATHS, cfg, mean_block=10.0, seed=0)

    res = {k: C.campaign(v, idx, cfg) for k, v in series.items()}
    rows = []
    base_out = res["baseline"]["out"]
    for k, r in res.items():
        s = C.summarize(r)
        d, lo, hi = C.paired_delta_ci(base_out, r["out"])
        s.update(name=k, delta_p=d, delta_lo=lo, delta_hi=hi,
                 delta_median_days=s["median_days"] - C.summarize(res["baseline"])["median_days"])
        rows.append(s)
    tab = pd.DataFrame(rows).set_index("name")
    tab.to_csv(OUT / "main_table.csv")
    print("\n=== MAIN TABLE ===")
    print(tab[["p_pass", "delta_p", "delta_lo", "delta_hi", "p_fail_daily",
               "p_fail_floor", "p_timeout", "median_days", "p90_days"]].to_string(
        float_format=lambda x: f"{x:.4f}"))

    # ---- placebo bands on the paired path subset
    idx_p = idx[:N_PATHS_PLACEBO]
    pb_rows = []
    for v in VARIANTS:
        ps = [C.summarize(C.campaign(s, idx_p, cfg)) for s in placebo_series[v]]
        pp = np.array([x["p_pass"] for x in ps])
        md = np.array([x["median_days"] for x in ps])
        real = C.summarize(C.campaign(series[v], idx_p, cfg))
        base = C.summarize(C.campaign(series["baseline"], idx_p, cfg))
        pb_rows.append(dict(
            variant=v, n_placebo=len(pp),
            p_pass_real=real["p_pass"], p_pass_base=base["p_pass"],
            placebo_mean=pp.mean(), placebo_p05=np.percentile(pp, 5),
            placebo_p50=np.percentile(pp, 50), placebo_p95=np.percentile(pp, 95),
            placebo_max=pp.max(),
            pctile_of_real=float((pp < real["p_pass"]).mean()),
            median_days_real=real["median_days"],
            placebo_days_p50=np.nanpercentile(md, 50),
            placebo_days_p05=np.nanpercentile(md, 5),
        ))
    pb = pd.DataFrame(pb_rows).set_index("variant")
    pb.to_csv(OUT / "placebo_table.csv")
    print("\n=== PLACEBO BAND (same duty cycle, same clustering, shuffled alignment) ===")
    print(pb.to_string(float_format=lambda x: f"{x:.4f}"))

    meta = dict(n_days=int(n), period=[str(dates.min().date()), str(dates.max().date())],
                delever=delever, n_paths=N_PATHS, n_paths_placebo=N_PATHS_PLACEBO,
                n_placebo=N_PLACEBO,
                book=B.summarize(pd.Series(series["baseline"], index=dates)),
                stress_rate={v: float(ex[v + "_stress"].mean()) for v in VARIANTS},
                mean_expo={v: float(ex[v].mean()) for v in VARIANTS})
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, default=float))
    print("\nwrote outputs/")


if __name__ == "__main__":
    main()
