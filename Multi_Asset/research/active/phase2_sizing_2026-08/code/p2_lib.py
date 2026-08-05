"""Phase-2 sizing harness — DEPLOYED MONO book, single attempt.

What this is
------------
`engine.run_phase(target=TARGET2=0.05)` from a fresh $10,000 phase-2 account IS a
phase 2: FTMO resets the balance to the initial capital between phases, so the
$11,006.08 that closed phase 1 does not carry over. Barriers in the engine are
already the phase-2 ones: daily = balance@day-open − 5 % of INITIAL, checked on the
M5 equity path; hard floor = STATIC 90 % of initial (`lim_eff = max(limit, FLOOR)`).
No ratchet.

Two things this module fixes relative to the inherited harness
--------------------------------------------------------------
1. **The min-trading-days counter is the REAL one.** The frozen spec carries BOTH
   `micro_orb: true` AND `fix_deadlock: true` (`spec_v22.yaml:30,33`);
   `wall_lib.CFG_LIVE` carries NEITHER, and `engine.run_phase` latches `flat_today`
   the moment equity touches target (engine.py:322-325), so an account that earns
   +5 % before opening 4 trading days is frozen and later written off as a TIMEOUT.
   Those are winners counted as deaths.
   The two counters are NOT interchangeable on this book, and the difference is
   structural, not cosmetic:
     * `fix_deadlock` (cleanroom) ticks the counter ONLY once equity is already at or
       above target ($1 token trade).
     * `micro_orb` (v2.2 engine = the deployed EA) posts a 0.01-lot US100 ORB trade on
       ANY day where nothing else opened by 21:30 — i.e. it ticks on Wed/Thu/Fri too,
       unconditionally on equity.
   In the DEPLOYED MONO book only Mon and Tue carry the overnight sleeve, so
   `E._target_for_segment` returns `opened=True` on Mon/Tue ONLY. Without the
   micro-ORB, 4 trading days therefore need 4 Mon/Tue = TWO calendar weeks. With it,
   4 consecutive sessions suffice. BASE CASE = the v2.2 engine with micro-ORB, i.e.
   the deployed spec; the cleanroom + `fix_deadlock` is carried as the cross-check.
2. **The Pace denominator is DECOUPLED from the analysis horizon.** `cfg["max_cal"]`
   is read twice inside the engine: as the per-attempt calendar timeout
   (`run_phase`) and as the Pace denominator (`_target_for_segment`). The live EA
   only has the second, pinned at `mission_wall_days = 91` in the frozen spec. The
   horizon here is an ANALYSIS variable, so it must not move the sizing.

Consequence of (2): with the Pace denominator frozen, `max_cal` enters `run_phase`
ONLY at the timeout check. So ONE run per (cohort, vm) with a long cap yields the
resolution day, and p(outcome | horizon H) = P(resolved as `outcome` at calendar day
<= H). This is an EXACT identity, not an approximation — verified in
`validate_identity.py`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
ENGINE_PATH = MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py"
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"
TAB = HERE.parent / "tables"


def load_engine():
    sys.path.insert(0, str(ENGINE_PATH.parent))
    spec = importlib.util.spec_from_file_location("engine", ENGINE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["engine"] = mod
    sys.modules["cleanroom_engine"] = mod
    spec.loader.exec_module(mod)
    mod.CACHE = MAIN / "data/ftmo_portfolio/cache"     # gitignored -> main checkout
    mod.AOUT = MAIN / "data/ftmo_portfolio/outputs"
    return mod


E = load_engine()


def load_v22():
    """The v2.2 contractual engine (micro-ORB) — the DEPLOYED spec's counter."""
    p = MAIN / "data/ftmo_portfolio/v22"
    sys.path.insert(0, str(p))
    spec = importlib.util.spec_from_file_location("engine_v22", p / "engine_v22.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["engine_v22"] = mod
    spec.loader.exec_module(mod)
    return mod


V = load_v22()

# Deployed live config: Swing margin, EA v2.4+ breaker semantics, MONO book
# (gold w=0, J1 off, ORB challenge-off). p2_mult 1.2 is the SPEC value
# (spec_v22.yaml:35) applied by ftmo_live/lib/governor.py:67 for phase 2.
# micro_orb + fix_deadlock are BOTH in the frozen challenge config
# (spec_v22.yaml:30,33) — the inherited CFG_LIVE literal carries neither.
CFG_LIVE = dict(
    vm=14.0, p2_mult=1.2, on_w=0.6, orb_risk=0.0,
    breaker=0.30, taper=0.02, glide=0.5, pace=1, pace_k=1.0,
    ab_buf=0.02, ab_days=5, margin_cap=0.60, quantize=True,
    mrate=E.MRATE_SWING, brk_mode="daily", brk_needs_pos=True,
    micro_orb=True,                    # <-- the DEPLOYED day counter
    fix_deadlock=True,                 # <-- engine backstop, also in the frozen spec
)

PACE_DENOM = 91          # mission_wall_days, frozen spec — NOT the analysis horizon
LONG_CAP = 80            # calendar cap for the resolution run (> longest horizon 70)

_ORIG = E._target_for_segment
_DENOM = PACE_DENOM
_SIGN = None
_PACE_ON = True


def _patched(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm):
    if not _PACE_ON:
        cfg = dict(cfg, pace=0)
    else:
        cfg = dict(cfg, max_cal=_DENOM)
    tgt, opened = _ORIG(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm)
    if tgt is None or _SIGN is None or _SIGN[i] > 0:
        return tgt, opened
    if s in (3, 4) and ON[i] > 0:          # only the newly posted overnight leg
        leg = 3 if s == 3 else 2
        tgt = tgt.copy()
        tgt[leg] = -tgt[leg]
    return tgt, opened


E._target_for_segment = _patched


def set_pace(denom: int | None = PACE_DENOM, on: bool = True):
    global _DENOM, _PACE_ON
    _DENOM, _PACE_ON = (denom if denom else PACE_DENOM), on


def set_signs(signs):
    global _SIGN
    _SIGN = signs


_CACHE: dict = {}


def market(swap_mul=1.0, spread_mul=1.0, leg_swap_mul=None, v22: bool = True):
    """Market stack. `leg_swap_mul` = per-leg multiplier on the swap panels, used to
    price the measured live swap drift (US100 x0.990, GER40 x1.124).

    `v22=True` adds the micro-ORB arrays; it also turns M["dates"] into a plain list
    (engine_v22 hot-loop convention) and keeps the DatetimeIndex under "dates_idx".
    Both engines index dates the same way, so one stack serves both.
    """
    key = (swap_mul, spread_mul, tuple(leg_swap_mul) if leg_swap_mul else None, v22)
    if key not in _CACHE:
        if v22:
            M = V.load_stack(swap_mul=swap_mul, spread_mul=spread_mul)
        else:
            M = E.load_market(swap_mul=swap_mul, spread_mul=spread_mul)
            M["dates_idx"] = M["dates"]
            M["dates"] = list(M["dates"])
        if leg_swap_mul is not None:
            k = np.asarray(leg_swap_mul, float)[None, :]
            M = dict(M, swL=M["swL"] * k, swS=M["swS"] * k)
        _CACHE[key] = M
    return _CACHE[key]


def book_mono(M):
    """The DEPLOYED book: gold w=0, J1 off; overnight indices sleeve Mon+Tue only."""
    d = pd.DatetimeIndex(M["dates_idx"])
    WT = np.zeros((len(d), 2), float)
    ON = np.zeros(len(d), float)
    ON[np.isin(d.dayofweek, [0, 1])] = 1.0
    return WT, ON


def book_full(M):
    """Contrefactuel only: the 4-sleeve book (gold + J1 re-armed)."""
    WT, ON = E.build_signals()
    d = pd.DatetimeIndex(M["dates_idx"])
    return (WT.reindex(d).fillna(0.0).to_numpy(float),
            ON.reindex(d).fillna(0.0).to_numpy(float))


def block_signs(n: int, block: int, rng) -> np.ndarray:
    """+-1 schedule persistent in blocks of `block` trading days: matched
    autocorrelation, zero expected edge. The placebo."""
    nb = int(np.ceil(n / block))
    return np.repeat(rng.choice([-1.0, 1.0], size=nb), block)[:n]


# ------------------------------------------------------------------ resolution
def resolve(M, WT, ON, starts, vm_spec: float, target: float = E.TARGET2,
            cfg=None, cap: int = LONG_CAP, engine="v22") -> pd.DataFrame:
    """One long run per cohort. Returns outcome + CALENDAR days at resolution.

    `vm_spec` is the SPEC knob (the deployed value is 14). The engine multiplies it
    by p2_mult for phase 2 exactly as governor.phase_cfg('P2') does, so the effective
    phase-2 vm is vm_spec * 1.2.
    """
    base = cfg or CFG_LIVE
    mult = base.get("p2_mult", 1.0) if target == E.TARGET2 else 1.0
    c = dict(base, target=target, max_cal=cap, vm=vm_spec * mult)
    run = V.run_phase if engine == "v22" else E.run_phase
    rows = []
    dates = M["dates"]
    for i0 in starts:
        r = run(M, i0, WT, ON, c)
        cal = int((dates[r["last"]] - dates[i0]).days)
        rows.append((int(i0), str(dates[i0].date()), r["out"], cal,
                     int(r["used"]), float(r["end"])))
    return pd.DataFrame(rows, columns=["i0", "date", "out", "cal_days",
                                       "td_used", "end_bal"])


OUTS = ("pass", "bust_daily", "bust_floor", "abandon", "timeout")


def horizon_stats(res: pd.DataFrame, H: int) -> dict:
    """Collapse a resolution frame onto a calendar horizon H. Exact identity with
    re-running the engine at max_cal=H (see validate_identity.py)."""
    within = res["cal_days"] <= H
    out = res["out"].where(within, "not_reached")
    n = len(res)
    p = {k: float((out == k).mean()) for k in OUTS}
    p["not_reached"] = float((out == "not_reached").mean())
    d = res.loc[within & (res["out"] == "pass"), "cal_days"].to_numpy(float)
    td = res.loc[within & (res["out"] == "pass"), "td_used"].to_numpy(float)
    return dict(
        H=H, n=n, p_pass=p["pass"],
        p_daily=p["bust_daily"], p_floor=p["bust_floor"],
        p_abandon=p["abandon"], p_not_reached=p["not_reached"] + p["timeout"],
        med_cal=float(np.median(d)) if d.size else np.nan,
        p90_cal=float(np.percentile(d, 90)) if d.size else np.nan,
        med_td=float(np.median(td)) if td.size else np.nan,
        mean_cal_all=float(np.minimum(res["cal_days"], H).mean()),
        pass_flags=(within & (res["out"] == "pass")).to_numpy(bool),
    )


# ------------------------------------------------------------------ inference
def block_boot_ci(flags: np.ndarray, block: int, n_boot: int = 4000,
                  seed: int = 0, alpha: float = 0.05):
    """Politis-Romano circular block bootstrap over the COHORT axis (cohorts are
    7 trading days apart; an attempt spanning k trading days overlaps ceil(k/7)
    of them, which is the dependence unit)."""
    rng = np.random.default_rng(seed)
    n = len(flags)
    nb = int(np.ceil(n / block))
    idx = (np.arange(block)[None, :] +
           rng.integers(0, n, size=(n_boot, nb))[:, :, None]) % n
    samp = flags[idx.reshape(n_boot, -1)[:, :n]].mean(axis=1)
    return (float(np.quantile(samp, alpha / 2)), float(np.quantile(samp, 1 - alpha / 2)))


def paired_block_boot(a: np.ndarray, b: np.ndarray, block: int, n_boot: int = 4000,
                      seed: int = 0, alpha: float = 0.05):
    """CI of mean(a) - mean(b) on the SAME resampled cohorts (paired)."""
    rng = np.random.default_rng(seed)
    n = len(a)
    nb = int(np.ceil(n / block))
    idx = ((np.arange(block)[None, :] +
            rng.integers(0, n, size=(n_boot, nb))[:, :, None]) % n
           ).reshape(n_boot, -1)[:, :n]
    d = a[idx].mean(axis=1) - b[idx].mean(axis=1)
    return (float(np.quantile(d, alpha / 2)), float(np.quantile(d, 1 - alpha / 2)),
            float(d.std(ddof=1)))


def block_for_horizon(H_cal: int, step: int = 7) -> int:
    """Dependence unit in cohorts: an attempt of H calendar days spans ~5H/7 trading
    days; cohorts are `step` trading days apart."""
    td = 5.0 * H_cal / 7.0
    return max(2, int(np.ceil(td / step)) + 1)


def cohort_starts(M, runway_td: int, step: int = 7, lo=None, hi=None):
    """FIXED cohort set with enough runway for the LONGEST horizon, so every cell is
    scored on the SAME starts (otherwise the sample moves with the horizon)."""
    n = M["n"]
    dates = pd.DatetimeIndex(M["dates_idx"])
    sel = np.arange(0, n - runway_td, step)
    if lo is not None:
        sel = sel[dates[sel] >= pd.Timestamp(lo)]
    if hi is not None:
        sel = sel[dates[sel] <= pd.Timestamp(hi)]
    return [int(i) for i in sel]
