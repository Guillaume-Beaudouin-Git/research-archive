"""The decisive control: a placebo band on the DECISION metric, not on the t-stat.

V+ (cut at the high) beats its volatility-matched constant de-lever by ~1pt of p(pass).
The pre-registration requires that gap to be read against the null of "ANY exposure
schedule with this duty cycle and this persistence", realised as circular rotations of the
V+ schedule. The 2026-07 study found a randomly placed schedule of the same duty cycle
worth +2.0pt on its own, so an unbanded +1pt is not evidence.

Phase-2 geometry (+5%), corrected min-trading-days backstop.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
OVERLAY = REPO / "Multi_Asset/research/active/regime_overlay_ftmo_2026-07"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "outputs"

sys.path.insert(0, str(OVERLAY))
sys.path.insert(0, str(REPO))
import build_book as B  # noqa: E402
from Portfolio.admission.barrier import BarrierConfig  # noqa: E402

import decision as D  # noqa: E402

N_ROT = 120
N_PATHS = 8_000

_M = _WT = _ON = _IDX = None
_CFG = BarrierConfig()


def _init():
    global _M, _WT, _ON, _IDX
    _M = B.build_market()
    dates = pd.DatetimeIndex(_M["dates"])
    _WT, _ON = B.mono_signals(dates)
    _IDX = D.draw(_M["n"], N_PATHS, _CFG.horizon_days + 5, seed=0)


def _eval(expo):
    r, a = D.series_for(_M, _WT, _ON, expo)
    res = D.run_p2(r, a, _IDX, _CFG, flat_after_target=True)
    s = D.summarize(res)
    s["ann_vol"] = float(r.std(ddof=1) * np.sqrt(252.0))
    return s


def main() -> None:
    OUT.mkdir(exist_ok=True)
    _init()
    n = _M["n"]
    cond = pd.read_parquet(CACHE / "conditioners.parquet")

    band = {}
    for cc in ("C1", "C2"):
        b0 = (cond[f"{cc}_US100"] <= 0.01).fillna(False).to_numpy()
        real = np.where(b0, D.CUT, 1.0)
        rng = np.random.default_rng(31)
        shifts = rng.choice(np.arange(30, n - 30), size=N_ROT, replace=False)
        jobs = [None, real] + [np.roll(real, int(s)) for s in shifts]
        with mp.Pool(8, initializer=_init) as pool:
            res = pool.map(_eval, jobs)
        base, rl, pl = res[0], res[1], res[2:]
        pp = np.array([x["p_pass"] for x in pl])
        md = np.array([x["median_days"] for x in pl])
        band[cc] = dict(
            baseline_p=base["p_pass"], baseline_median_days=base["median_days"],
            real_p=rl["p_pass"], real_median_days=rl["median_days"],
            real_dp_pt=float((rl["p_pass"] - base["p_pass"]) * 100),
            placebo_p05=float(np.percentile(pp, 5)),
            placebo_p50=float(np.percentile(pp, 50)),
            placebo_p95=float(np.percentile(pp, 95)),
            placebo_max=float(pp.max()),
            placebo_mean_dp_pt=float((pp.mean() - base["p_pass"]) * 100),
            pctile_of_real=float((pp < rl["p_pass"]).mean()),
            placebo_median_days_p50=float(np.median(md)),
            n_rot=int(N_ROT), n_paths=int(N_PATHS),
        )
        b = band[cc]
        print(f"\n=== PLACEBO BAND ON p(pass), V+ {cc} (PHASE 2, +5%) ===")
        print(f"baseline                {b['baseline_p']:.4f}   median {b['baseline_median_days']:.0f}d")
        print(f"REAL V+                 {b['real_p']:.4f}   median {b['real_median_days']:.0f}d "
              f"({b['real_dp_pt']:+.2f}pt)")
        print(f"placebo p50 / p95 / max {b['placebo_p50']:.4f} / {b['placebo_p95']:.4f} / "
              f"{b['placebo_max']:.4f}   (random schedule alone: {b['placebo_mean_dp_pt']:+.2f}pt)")
        print(f"percentile of real      {b['pctile_of_real']:.3f}"
              f"   -> {'ABOVE p95' if b['pctile_of_real'] >= 0.95 else 'INSIDE BAND'}")

    (OUT / "placebo_decision.json").write_text(json.dumps(band, indent=2, default=float))


if __name__ == "__main__":
    main()
