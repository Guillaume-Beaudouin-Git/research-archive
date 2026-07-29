"""Paired FTMO 2-phase campaign evaluation, vectorised across bootstrap paths.

``Portfolio/admission/barrier.py`` is the reference implementation but loops one path at
a time, which is too slow for a placebo band (hundreds of series). This module runs the
identical barrier logic vectorised over paths and is validated to reproduce
``barrier.simulate_campaign`` EXACTLY on the same seed (see ``validate``): same bootstrap
draw order, same barrier ordering (daily checked before floor), same min-trading-days
rule, same pass condition.

All variants are evaluated on the SAME pre-drawn index matrix, so every Delta is paired
and free of Monte-Carlo noise across variants; the CI on Delta p is a paired bootstrap
over paths (equivalently McNemar on the discordant pairs).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(REPO))

from Portfolio.admission.barrier import BarrierConfig  # noqa: E402
from Portfolio.admission.marginal import stationary_bootstrap_indices  # noqa: E402

PASS, FLOOR, DAILY, TIMEOUT = 0, 1, 2, 3


def draw_paths(n_obs: int, n_paths: int, cfg: BarrierConfig, mean_block: float = 10.0,
               seed: int = 0) -> np.ndarray:
    """Index matrix (n_paths, horizon). Draw order identical to barrier.simulate_campaign."""
    rng = np.random.default_rng(seed)
    horizon = 2 * cfg.horizon_days + 10
    reps = int(np.ceil(horizon / n_obs)) + 1
    out = np.empty((n_paths, horizon), dtype=np.int32)
    for p in range(n_paths):
        idx = np.concatenate(
            [stationary_bootstrap_indices(n_obs, mean_block, rng) for _ in range(reps)]
        )[:horizon]
        out[p] = idx
    return out


def _run_phase_vec(R: np.ndarray, start: np.ndarray, target: float, cfg: BarrierConfig,
                   min_days: int, max_days: int):
    """Vectorised mirror of barrier._run_phase over paths.

    R: (P, horizon) return matrix. start: (P,) phase start offsets.
    Returns (outcome codes (P,), index_after (P,)).
    """
    P, H = R.shape
    bal = np.ones(P)
    traded = np.zeros(P, dtype=np.int32)
    out = np.full(P, -1, dtype=np.int8)
    end = np.zeros(P, dtype=np.int32)
    floor = 1.0 - cfg.static_floor
    goal = 1.0 + target
    limit = max_days if max_days > 0 else cfg.horizon_days
    live = np.ones(P, dtype=bool)

    for k in range(limit):
        i = start + k
        over = live & (i >= H)
        if over.any():                      # ran off the end of the path
            out[over] = TIMEOUT
            end[over] = i[over]
            live &= ~over
        if not live.any():
            break
        idx = np.where(live)[0]
        r = R[idx, i[idx]]
        day_open = bal[idx]
        nb = day_open * (1.0 + r)
        bal[idx] = nb
        traded[idx] += (r != 0.0)

        hit_daily = nb <= day_open * (1.0 - cfg.daily_stop)
        hit_floor = (~hit_daily) & (nb <= floor)
        hit_pass = (~hit_daily) & (~hit_floor) & (nb >= goal) & (traded[idx] >= min_days)

        for mask, code in ((hit_daily, DAILY), (hit_floor, FLOOR), (hit_pass, PASS)):
            if mask.any():
                sel = idx[mask]
                out[sel] = code
                end[sel] = i[sel] + 1
                live[sel] = False

    still = np.where(live)[0]
    if still.size:
        out[still] = TIMEOUT
        end[still] = start[still] + limit
    return out, end


def campaign(series: np.ndarray, idx: np.ndarray, cfg: BarrierConfig):
    """Run the 2-phase funnel for one return series on the pre-drawn paths.

    Returns dict with per-path outcome codes and days-to-funded (nan when not funded).
    """
    R = series[idx]
    P = R.shape[0]
    start = np.zeros(P, dtype=np.int32)
    o1, i1 = _run_phase_vec(R, start, cfg.target_p1, cfg, cfg.min_days_p1, cfg.max_days_p1)
    out = o1.copy()
    days = np.full(P, np.nan)
    go = o1 == PASS
    if go.any():
        o2, i2 = _run_phase_vec(R[go], i1[go], cfg.target_p2, cfg,
                                cfg.min_days_p2, cfg.max_days_p2)
        sel = np.where(go)[0]
        out[sel] = o2
        funded = o2 == PASS
        days[sel[funded]] = i2[funded]
    return {"out": out, "days": days}


def summarize(res: dict) -> dict:
    out, days = res["out"], res["days"]
    n = float(len(out))
    fd = days[~np.isnan(days)]
    return {
        "p_pass": float((out == PASS).mean()),
        "p_fail_daily": float((out == DAILY).mean()),
        "p_fail_floor": float((out == FLOOR).mean()),
        "p_timeout": float((out == TIMEOUT).mean()),
        "median_days": float(np.median(fd)) if fd.size else np.nan,
        "p90_days": float(np.percentile(fd, 90)) if fd.size else np.nan,
        "n_paths": int(n),
    }


def paired_delta_ci(out_a: np.ndarray, out_b: np.ndarray, n_boot: int = 4000,
                    seed: int = 7) -> tuple[float, float, float]:
    """Paired bootstrap CI on p(pass|b) - p(pass|a) over the shared paths."""
    a = (out_a == PASS).astype(float)
    b = (out_b == PASS).astype(float)
    d = b - a
    rng = np.random.default_rng(seed)
    n = len(d)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        boot[i] = d[rng.integers(0, n, n)].mean()
    return float(d.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def validate(series: np.ndarray, cfg: BarrierConfig, n_paths: int = 500,
             mean_block: float = 10.0, seed: int = 0) -> None:
    """Assert this vectorised engine reproduces barrier.simulate_campaign exactly."""
    from Portfolio.admission.barrier import simulate_campaign

    ref = simulate_campaign(series, cfg, n_paths=n_paths, mean_block=mean_block, seed=seed)
    idx = draw_paths(len(series), n_paths, cfg, mean_block, seed)
    mine = summarize(campaign(series, idx, cfg))
    checks = {
        "p_pass": (ref.p_pass, mine["p_pass"]),
        "p_fail_daily": (ref.p_fail_daily, mine["p_fail_daily"]),
        "p_fail_floor": (ref.p_fail_floor, mine["p_fail_floor"]),
        "p_timeout": (ref.p_timeout, mine["p_timeout"]),
        "median_days": (ref.median_days_to_funded, mine["median_days"]),
    }
    bad = {k: v for k, v in checks.items()
           if not (np.isnan(v[0]) and np.isnan(v[1])) and abs(v[0] - v[1]) > 1e-12}
    if bad:
        raise AssertionError(f"vectorised engine diverges from barrier.py: {bad}")
    print(f"validation vs Portfolio/admission/barrier.py: EXACT match on {n_paths} paths "
          f"(p_pass={ref.p_pass:.4f})")
