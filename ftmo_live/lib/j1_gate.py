"""J1 (USDJPY) intervention-zone suspension gate — brain-side risk overlay.

Zeroes the J1 weight (weights["USDJPY"]=0 -> ea_w_usdjpy=0 -> the frozen EA flattens J1 at the
22:05 rebalance and does not reopen) while USD/JPY sits in the BoJ/MoF intervention zone.

Deterministic function of the USD/JPY daily close (NO persisted state). Frozen thresholds ratified
2026-07-03: T_off=160, T_on=155, N=10. `_off_state` is byte-identical to the audited study
`data/ftmo_portfolio/j1_suspend_study/gate.py:off_state` (the backtest that measured Δp +0.65
[0,+1.95] pts, cost gate PASS).

Fail-safe policy (this overlay's whole point is to prevent the intervention-flash catastrophe that
killed 2 accounts, so it fails toward PROTECTION):
  - config missing / corrupt  -> hardcoded DEFAULTS (protection stays ON).
  - config enabled=false      -> explicit opt-out (J1 trades normally).
  - USD/JPY data unreadable    -> fail-CLOSED (suspend J1) + reason, so we never trade J1 blind.
Never raises: `evaluate()` always returns a dict; the brain must not crash on a gate glitch.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import LIVE_ROOT

CONFIG_PATH = LIVE_ROOT / "config" / "j1_gate.json"
DEFAULTS = dict(enabled=True, t_off=160.0, t_on=155.0, n_resume=10)


def _load_config():
    """Return (cfg, source). Missing/corrupt -> DEFAULTS (fail toward protection)."""
    try:
        raw = json.loads(CONFIG_PATH.read_text())
        cfg = dict(DEFAULTS)
        for k in DEFAULTS:
            if k in raw:
                cfg[k] = raw[k]
        cfg["enabled"] = bool(cfg["enabled"])
        cfg["t_off"] = float(cfg["t_off"])
        cfg["t_on"] = float(cfg["t_on"])
        cfg["n_resume"] = int(cfg["n_resume"])
        if not (cfg["t_on"] < cfg["t_off"] and cfg["n_resume"] >= 1):
            return dict(DEFAULTS), "default_failsafe_bad_values"
        return cfg, "config"
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError, TypeError, KeyError):
        return dict(DEFAULTS), "default_failsafe"


def _off_state(close: pd.Series, t_off: float, t_on: float, n: int) -> pd.Series:
    """OFF-state per date (True = J1 suspended). NON-causal (uses close[t] itself).
    IDENTICAL logic to the audited study gate.off_state. Start ON; OFF latches on close>=t_off;
    resumes only after n consecutive closes<=t_on (a single close>t_on resets the counter)."""
    c = close.to_numpy(float)
    off = np.zeros(len(c), dtype=bool)
    state = False
    run_below = 0
    for i in range(len(c)):
        if not state:
            if np.isfinite(c[i]) and c[i] >= t_off:
                state = True
                run_below = 0
        else:
            if np.isfinite(c[i]) and c[i] <= t_on:
                run_below += 1
                if run_below >= n:
                    state = False
                    run_below = 0
            else:
                run_below = 0
        off[i] = state
    return pd.Series(off, index=close.index)


def _evaluate(cache) -> dict:
    """J1 suspension decision for tonight's 22:05 targets. `cache` = brain's live cache dir.

    The live cache ends at the last COMPLETE daily close (<= T-1), so off.iloc[-1] is the causal
    decision for day T — same semantics as the backtest's suspend_causal = off_state.shift(1).
    """
    cfg, source = _load_config()
    out = dict(source=source, enabled=cfg["enabled"], t_off=cfg["t_off"],
               t_on=cfg["t_on"], n_resume=cfg["n_resume"])
    if not cfg["enabled"]:
        return dict(out, suspend=False, level=None, reason="disabled")
    try:
        px = pd.read_parquet(Path(cache) / "panel_px.parquet")["USDJPY"].dropna()
    except (FileNotFoundError, KeyError, OSError, ValueError):
        px = None
    if px is None or len(px) == 0:
        return dict(out, suspend=True, level=None, reason="failclosed_no_usdjpy_data")
    off = _off_state(px, cfg["t_off"], cfg["t_on"], cfg["n_resume"])
    suspend = bool(off.iloc[-1])
    return dict(out, suspend=suspend, level=float(px.iloc[-1]),
                last_close_date=str(px.index[-1].date()),
                reason="in_zone" if suspend else "out_of_zone")


def evaluate(cache) -> dict:
    """Public entry point — NEVER raises (audit B9 hardening). Any unexpected error degrades to
    fail-CLOSED (suspend J1): a gate glitch flattens J1 rather than leaving a ~16x long open. The
    brain must not crash on a gate glitch, and a brain crash would itself fail-OPEN (stale targets
    -> EA 'gestion seule' holds J1)."""
    try:
        return _evaluate(cache)
    except Exception as e:                       # noqa: BLE001 — live-money path: fail to protection
        return dict(suspend=True, level=None, reason="failclosed_exception", error=repr(e),
                    source="failsafe", enabled=True, t_off=DEFAULTS["t_off"],
                    t_on=DEFAULTS["t_on"], n_resume=DEFAULTS["n_resume"])
