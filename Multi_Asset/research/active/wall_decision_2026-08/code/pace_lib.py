"""GAP 1 harness — ASYMMETRIC decomposition of the Pace channel.

    Pace = clip(1 + K*(frac_t - max(prog,0)), 0.8, 2.0),  K = 1.0,
    frac_t = elapsed_calendar_days / WALL_DAYS,  prog = (eq/INIT - 1)/target.

The multiplier has two legs with OPPOSITE risk signs, and averaging them erases the
question:
  * HIGH leg  (x > 1, account BEHIND):  up to 2.0x  -> adds leverage NEAR the floor.
  * LOW  leg  (x < 1, account AHEAD):   down to 0.8 -> protects a lead.

Modes implemented (all EXACT, no re-derivation of taper/glide/caps/quantization):
  coupled  : engine default, pace denominator = cfg["max_cal"]
  frozen   : same but denominator pinned at `pace_denom`
  off      : pace == 1
  hi_only  : pace = max(x, 1)   -> only the amplification leg survives
  lo_only  : pace = min(x, 1)   -> only the protective leg survives

Mechanism: `engine._target_for_segment` computes `scale = vm * taper * glide * pace`
and receives `vm` as an ARGUMENT. So we recompute the raw pace `x` (the engine's own
two lines), then call the ORIGINAL with `cfg["pace"]=0` and `vm -> vm * p_target`.
Identical arithmetic, every downstream cap and the quantizer untouched.
Non-regression: mode "frozen" with denom == wall must reproduce "coupled" bit-for-bit.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
ENGINE_PATH = MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py"


def load_engine():
    spec = importlib.util.spec_from_file_location("cleanroom_engine", ENGINE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cleanroom_engine"] = mod
    spec.loader.exec_module(mod)
    mod.CACHE = MAIN / "data/ftmo_portfolio/cache"          # gitignored -> MAIN only
    mod.AOUT = MAIN / "data/ftmo_portfolio/outputs"
    return mod


E = load_engine()

# DEPLOYED book: MONO (gold w=0, J1 off, ORB challenge-off), live Swing margin,
# EA v2.4 breaker semantics. Identical to wall_economics_2026-08/code/wall_lib.py.
CFG_LIVE = dict(
    vm=14.0, p2_mult=1.2, on_w=0.6, orb_risk=0.0,
    breaker=0.30, taper=0.02, glide=0.5, pace=1, pace_k=1.0,
    ab_buf=0.02, ab_days=5, margin_cap=0.60, quantize=True,
    mrate=E.MRATE_SWING, brk_mode="daily", brk_needs_pos=True,
)

PACE_MIN, PACE_MAX = 0.8, 2.0

_ORIG = E._target_for_segment
_MODE = "coupled"
_DENOM = 91
_SIGN = None
# duty-cycle instrumentation: counts of risk-posting segments by leg
LEG_LOG = {"hi": 0, "lo": 0, "flat": 0, "n": 0, "sum_x": 0.0, "max_x": 0.0}
_LOG_ON = False


def raw_pace(i, M, cfg, bal, pos, avg, px0, i0, denom):
    """The engine's own two lines, verbatim."""
    eq = bal + E._mtm(pos, avg, px0)
    prog = (eq / E.INIT - 1.0) / cfg["target"]
    frac_t = (M["dates"][i] - M["dates"][i0]).days / denom
    x = 1.0 + cfg.get("pace_k", 1.0) * (frac_t - max(prog, 0.0))
    return float(np.clip(x, PACE_MIN, PACE_MAX)), frac_t, prog


def _patched(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm):
    if _MODE == "coupled" and not _LOG_ON:
        tgt, opened = _ORIG(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm)
    else:
        denom = _DENOM if _MODE == "frozen" else cfg.get("max_cal")
        if not cfg.get("pace") or not denom:
            p = 1.0
            x = 1.0
        else:
            x, _, _ = raw_pace(i, M, cfg, bal, pos, avg, px0, i0, denom)
            p = {"off": 1.0, "hi_only": max(x, 1.0), "lo_only": min(x, 1.0)}.get(_MODE, x)
        if _LOG_ON and s in (3, 4):
            LEG_LOG["n"] += 1
            LEG_LOG["sum_x"] += x
            LEG_LOG["max_x"] = max(LEG_LOG["max_x"], x)
            LEG_LOG["min_x"] = min(LEG_LOG.get("min_x", 9.9), x)
            LEG_LOG["hi" if x > 1.0 else ("lo" if x < 1.0 else "flat")] += 1
        tgt, opened = _ORIG(s, i, M, WT, ON, dict(cfg, pace=0), bal, pos, avg,
                            px0, i0, vm * p)
    if tgt is None or _SIGN is None or _SIGN[i] > 0:
        return tgt, opened
    if s in (3, 4) and ON[i] > 0:               # placebo: flip the newly posted leg
        leg = 3 if s == 3 else 2
        tgt = tgt.copy()
        tgt[leg] = -tgt[leg]
    return tgt, opened


E._target_for_segment = _patched

_M = _WT = _ON = None


def init():
    global _M, _WT, _ON
    if _M is None:
        _M = E.load_market()
        d = pd.DatetimeIndex(_M["dates"])
        _WT = np.zeros((len(d), 2), float)          # gold + J1 OFF -> MONO book
        _ON = np.zeros(len(d), float)
        _ON[np.isin(d.dayofweek, [0, 1])] = 1.0     # overnight sleeve: Mon/Tue
    return _M, _WT, _ON


def block_signs(n: int, block: int, rng) -> np.ndarray:
    nb = int(np.ceil(n / block))
    return np.repeat(rng.choice([-1.0, 1.0], size=nb), block)[:n]


def cohort_starts(M, runway_days: int, step: int = 7):
    n = M["n"]
    return [int(i) for i in np.arange(0, n, step) if i < n - runway_days]


def eval_wall(wall, mode="coupled", pace_denom=91, signs=None, starts=None,
              cfg=None, one_try=True, log_legs=False):
    """Cohort sweep of the 2-step retry funnel. Returns aggregates + per-cohort flags."""
    global _MODE, _DENOM, _SIGN, _LOG_ON
    M, WT, ON = init()
    _MODE, _DENOM, _SIGN, _LOG_ON = mode, pace_denom, signs, log_legs
    for k in LEG_LOG:
        LEG_LOG[k] = 0 if k != "sum_x" and k != "max_x" else 0.0
    cfg = cfg or CFG_LIVE
    funded, times, attempts, one_l, deaths, used = [], [], [], [], [], []
    for i0 in starts:
        r = E.run_funnel(M, i0, WT, ON, cfg, wall=wall)
        funded.append(bool(r["funded"]))
        attempts.append(r["attempts"])
        if r["funded"]:
            times.append(r["t"])
        if one_try:
            p1 = E.run_phase(M, i0, WT, ON, dict(cfg, target=E.TARGET1, max_cal=wall))
            one_l.append(p1["out"] == "pass")
            deaths.append(p1["out"])
            used.append(p1.get("used", np.nan))
    legs = dict(LEG_LOG)
    _SIGN, _LOG_ON = None, False
    d = pd.Series(deaths).value_counts(normalize=True) if deaths else pd.Series(dtype=float)
    t = np.asarray(times, float)
    out = dict(
        wall=wall, mode=mode, pace_denom=pace_denom, n_cohorts=len(starts),
        p_campaign=float(np.mean(funded)),
        p_one_try=float(np.mean(one_l)) if one_l else np.nan,
        avg_attempts=float(np.mean(attempts)),
        median_days=float(np.median(t)) if t.size else np.nan,
        mean_days=float(np.mean(t)) if t.size else np.nan,
        p90_days=float(np.percentile(t, 90)) if t.size else np.nan,
        d_bust_daily=float(d.get("bust_daily", 0.0)),
        d_bust_floor=float(d.get("bust_floor", 0.0)),
        d_timeout=float(d.get("timeout", 0.0)),
        d_abandon=float(d.get("abandon", 0.0)),
        median_used=float(np.median(used)) if used else np.nan,
    )
    if log_legs and legs["n"]:
        out.update(leg_hi=legs["hi"] / legs["n"], leg_lo=legs["lo"] / legs["n"],
                   leg_flat=legs["flat"] / legs["n"],
                   mean_x=legs["sum_x"] / legs["n"], max_x=legs["max_x"],
                   n_segments=legs["n"])
    out["funded_flags"] = np.asarray(funded, bool)
    out["onetry_flags"] = np.asarray(one_l, bool)
    out["floor_flags"] = np.asarray([o == "bust_floor" for o in deaths], bool)
    out["daily_flags"] = np.asarray([o == "bust_daily" for o in deaths], bool)
    return out


def attempt_profile(starts, wall, mode="coupled", pace_denom=91, cfg=None,
                    max_cal_phase=None):
    """PER-COHORT leg exposure + outcome of the FIRST attempt (run_phase).

    Needed for the conditional (surface) estimands: the aggregate contrast dilutes a
    leg's effect over the cohorts where that leg never armed. Here every cohort carries
    its own duty cycle, so the treated subset can be isolated and paired.
    `max_cal_phase` lets the ABANDON horizon differ from the Pace denominator (the
    A-without-B configuration).
    """
    global _MODE, _DENOM, _SIGN, _LOG_ON
    M, WT, ON = init()
    _MODE, _DENOM, _SIGN, _LOG_ON = mode, pace_denom, None, True
    cfg = cfg or CFG_LIVE
    rows = []
    for i0 in starts:
        for k in LEG_LOG:
            LEG_LOG[k] = 0.0 if k in ("sum_x", "max_x") else 0
        LEG_LOG["min_x"] = 9.9
        r = E.run_phase(M, i0, WT, ON,
                        dict(cfg, target=E.TARGET1,
                             max_cal=max_cal_phase if max_cal_phase else wall))
        n = max(LEG_LOG["n"], 1)
        rows.append(dict(
            i0=i0, out=r["out"], used=r.get("used", np.nan),
            n_seg=LEG_LOG["n"],
            f_hi=LEG_LOG["hi"] / n, f_lo=LEG_LOG["lo"] / n,
            mean_x=LEG_LOG["sum_x"] / n, max_x=LEG_LOG["max_x"],
            min_x=LEG_LOG["min_x"] if LEG_LOG["min_x"] < 9.9 else np.nan,
        ))
    _LOG_ON = False
    d = pd.DataFrame(rows)
    d["mode"] = mode
    d["wall"] = wall
    return d


# ---------------------------------------------------------------- inference
def block_boot_delta(a: np.ndarray, b: np.ndarray, block: int, n_boot: int = 4000,
                     seed: int = 3) -> tuple[float, float, float]:
    """Paired block bootstrap over COHORTS (same starts in both arms).

    Cohorts are `step` trading days apart and each campaign spans many of them, so
    neighbouring cohorts share most of their path -> resample CONTIGUOUS BLOCKS of
    cohorts, never single cohorts (iid over cohorts would understate the CI badly).
    """
    d = a.astype(float) - b.astype(float)
    n = d.size
    nb = int(np.ceil(n / block))
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, max(n - block, 1), size=(n_boot, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_boot, -1)
    idx = np.minimum(idx[:, :n], n - 1)
    m = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def cohort_block_len(cycle_days: float, step: int = 7) -> int:
    """Number of cohorts a single campaign spans = the dependence length."""
    td = cycle_days * 252.0 / 365.0
    return max(int(np.ceil(td / step)), 1)
