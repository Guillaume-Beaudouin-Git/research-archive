"""Shared harness: deployed MONO book on the canonical cleanroom funnel, with the
wall (campaign horizon + per-attempt timeout) DECOUPLED from the Pace denominator.

The cleanroom engine is IMPORTED and never modified. `cfg["max_cal"]` is read in two
places inside it:
  * engine.run_phase   -> per-attempt calendar TIMEOUT (abandon the attempt)
  * engine._target_for_segment -> Pace() denominator (a SIZING multiplier)
The live EA only has the second. To price the two channels apart we wrap
`_target_for_segment` and override the cfg it sees, leaving the timeout untouched.
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
    # caches are gitignored -> they live in the MAIN checkout only (read-only)
    mod.CACHE = MAIN / "data/ftmo_portfolio/cache"
    mod.AOUT = MAIN / "data/ftmo_portfolio/outputs"
    return mod


E = load_engine()

# Live Swing account, DEPLOYED book = MONO (gold w=0, J1 off, ORB challenge-off).
CFG_LIVE = dict(
    vm=14.0, p2_mult=1.2, on_w=0.6, orb_risk=0.0,
    breaker=0.30, taper=0.02, glide=0.5, pace=1, pace_k=1.0,
    ab_buf=0.02, ab_days=5, margin_cap=0.60, quantize=True,
    mrate=E.MRATE_SWING, brk_mode="daily", brk_needs_pos=True,
)

_ORIG = E._target_for_segment
_PACE_MODE = "coupled"     # "coupled" | "frozen" | "off"
_PACE_DENOM = 91           # used when _PACE_MODE == "frozen"
_SIGN = None               # placebo: per-day +-1 applied to the overnight legs


def _patched(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm):
    if _PACE_MODE == "off":
        cfg = dict(cfg, pace=0)
    elif _PACE_MODE == "frozen":
        cfg = dict(cfg, max_cal=_PACE_DENOM)
    tgt, opened = _ORIG(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm)
    if tgt is None or _SIGN is None or _SIGN[i] > 0:
        return tgt, opened
    if s in (3, 4) and ON[i] > 0:          # only the newly posted overnight leg
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
        _WT = np.zeros((len(d), 2), float)          # gold + J1 OFF
        _ON = np.zeros(len(d), float)
        _ON[np.isin(d.dayofweek, [0, 1])] = 1.0     # overnight sleeve: Mon/Tue
    return _M, _WT, _ON


def block_signs(n: int, block: int, rng) -> np.ndarray:
    """+-1 schedule, persistent in blocks of `block` trading days (matched
    autocorrelation, zero expected edge)."""
    nb = int(np.ceil(n / block))
    return np.repeat(rng.choice([-1.0, 1.0], size=nb), block)[:n]


def eval_wall(wall: int, pace_mode: str = "coupled", pace_denom: int = 91,
              signs=None, starts=None, cfg=None, one_try: bool = True) -> dict:
    """Cohort sweep of the 2-step retry funnel at a given wall."""
    global _PACE_MODE, _PACE_DENOM, _SIGN
    M, WT, ON = init()
    _PACE_MODE, _PACE_DENOM, _SIGN = pace_mode, pace_denom, signs
    cfg = cfg or CFG_LIVE
    funded, times, attempts, one_try_l, deaths = [], [], [], [], []
    for i0 in starts:
        r = E.run_funnel(M, i0, WT, ON, cfg, wall=wall)
        funded.append(bool(r["funded"]))
        attempts.append(r["attempts"])
        if r["funded"]:
            times.append(r["t"])
        if one_try:
            p1 = E.run_phase(M, i0, WT, ON, dict(cfg, target=E.TARGET1, max_cal=wall))
            one_try_l.append(p1["out"] == "pass")
            deaths.append(p1["out"])
    _SIGN = None
    d = pd.Series(deaths).value_counts(normalize=True)
    t = np.asarray(times, float)
    return dict(
        wall=wall, pace_mode=pace_mode, n_cohorts=len(starts),
        p_campaign=float(np.mean(funded)),
        p_one_try=float(np.mean(one_try_l)) if one_try_l else float("nan"),
        avg_attempts=float(np.mean(attempts)),
        median_days=float(np.median(t)) if t.size else float("nan"),
        p90_days=float(np.percentile(t, 90)) if t.size else float("nan"),
        mean_days=float(np.mean(t)) if t.size else float("nan"),
        d_bust_daily=float(d.get("bust_daily", 0.0)),
        d_bust_floor=float(d.get("bust_floor", 0.0)),
        d_timeout=float(d.get("timeout", 0.0)),
        d_abandon=float(d.get("abandon", 0.0)),
        funded_flags=np.asarray(funded, bool),
        times_all=np.array([r for r in times], float),
    )


def cohort_starts(M, runway_days: int, step: int = 7):
    """Fixed cohort set with enough runway for the LONGEST wall tested, so every
    wall is scored on the SAME starts (otherwise the sample moves with the wall)."""
    n = M["n"]
    sel = np.arange(0, n, step)
    return [int(i) for i in sel if i < n - runway_days]
