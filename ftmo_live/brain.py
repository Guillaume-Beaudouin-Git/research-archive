#!/usr/bin/env python3
"""brain.py — cron 21:50 Europe/Paris : signaux v2.2 -> targets.json.

Chaîne (zéro constante manuelle, ancre #19/#20) :
  spec_v22.yaml @ pin dd6ab126 (loader v22/ea/brain.py, drift-check) +
  mqh @ pin 1d834546 -> panels gelés + extension D1 de l'EA -> E.build_signals()
  (cleanroom, code path 462 cohortes) -> WT.loc[T] -> gouverneur (sondes
  E._target_for_segment) -> targets.json (clés EA plates + audit complet +
  prévision swaps ancres yaml).

Le brain n'envoie AUCUN ordre. Les poids sont causaux (données <= T-1) ; l'EA
applique le gouverneur sur SON equity au moment des fills (sémantique sim).
ORB_RT_BPS reste lu du yaml (era) — aucun ré-ancrage avant le verdict N=60 du
2026-06-15 (procédure NONREGRESSION §ORB_RT_BPS).

Usage:
  brain.py --check
  brain.py                          # production (lit market_export, écrit targets)
  brain.py --dry-run --as-of YYYY-MM-DD [--equity 10000 --balance 10000
           --phase P1 --attempt-start YYYY-MM-DD] [--json]
"""
import argparse
import json
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import LEGS, LIVE_CACHE, PIN_COMMITS  # noqa: E402
from lib import governor, invariants, marketdata, signals, spec, statefiles, swaps  # noqa: E402

OFF_SCHEDULE_BEFORE_H = 15  # un run production avant 15:00 Paris = anormal (warn)
STATE_FRESH_S = 600


def _phase_mode_params(phase: str) -> dict:
    """Échos de mode pour cross-check EA (valeurs PHASE-EFFECTIVES du yaml)."""
    cfg = governor.phase_cfg(phase)
    keys = ("vm", "on_w", "orb_risk", "micro_orb", "breaker", "taper", "glide",
            "pace", "margin_cap")
    return {k: cfg.get(k) for k in keys}


def _positions_vec(state: dict):
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    px = np.full(4, np.nan)
    for p in (state or {}).get("positions", []):
        leg = p.get("leg")
        if leg in LEGS:
            k = LEGS.index(leg)
            pos[k] = float(p["notional_usd"]) * (1 if int(p["dir"]) > 0 else -1)
            avg[k] = float(p["avg"])
    for leg, sp in ((state or {}).get("symbol_specs") or {}).items():
        if leg in LEGS and float(sp.get("price", 0)) > 0:
            px[LEGS.index(leg)] = float(sp["price"])
    return pos, avg, px


def run(dry_run: bool = False, as_of: str = None, equity: float = None,
        balance: float = None, phase: str = None, attempt_start: str = None,
        cache_dir: Path = None, write: bool = True, emit_json: bool = False) -> dict:
    sp = spec.load()
    spec.verify_mqh_pin()
    miss = spec.loader().verify_pins_in_repo()
    audit = dict(pins=PIN_COMMITS, pins_missing_in_repo=miss)

    now = statefiles.now_paris().replace(tzinfo=None)
    target_date = pd.Timestamp(as_of).normalize() if as_of else pd.Timestamp(now.date())

    if dry_run:
        cache = cache_dir or (LIVE_CACHE / f"dryrun_{target_date.date()}")
        audit["data"] = marketdata.build_truncated_cache(target_date, cache)
        state = None
    else:
        files_dir = statefiles.mt5_files_dir()
        export = marketdata.load_export(files_dir / "market_export.json", now=now)
        cache = cache_dir or (LIVE_CACHE / str(target_date.date()))
        audit["data"] = marketdata.build_live_cache(export, target_date, cache)
        # v2.2.1 — specs live (EA) vs ancres datées du yaml (immunisation dérive)
        live = {}
        for leg, sp in export.get("symbols", {}).items():
            if leg in LEGS:
                r3d = sp.get("swap_r3d")
                live[leg] = dict(
                    swap_long_pts=sp.get("swap_long"),
                    swap_short_pts=sp.get("swap_short"),
                    rollover3days_dow_py=None if r3d is None else (int(r3d) + 6) % 7,
                    margin_rate=sp.get("margin_rate_live"))
        breaches = swaps.check_live_bounds(live)
        audit["live_spec_bounds"] = breaches if breaches else "OK"
        if now.hour < OFF_SCHEDULE_BEFORE_H:
            audit["warn_off_schedule"] = statefiles.fmt_ts(now)
        state = statefiles.read_state(files_dir)
        if state is not None and statefiles.state_age_s(state, now) > STATE_FRESH_S:
            audit["warn_state_stale_s"] = round(statefiles.state_age_s(state, now))
            state = None

    wt_row, sig_diag = signals.weights_for(target_date, cache)
    on_day = bool(sig_diag["on_day"])
    weights = {"XAUUSD": float(wt_row["XAUUSD"]), "USDJPY": float(wt_row["USDJPY"])}
    audit["signals"] = sig_diag
    audit["weights"] = weights

    phase = phase or (state or {}).get("phase") or "P1"
    bal = balance if balance is not None else float((state or {}).get(
        "balance", spec.account_size(sp)))
    att = pd.Timestamp(attempt_start) if attempt_start else pd.Timestamp(
        (state or {}).get("attempt_start", str(target_date.date())))

    pos, avg, px = _positions_vec(state)
    if not np.isfinite(px).all():
        last = pd.read_parquet(Path(cache) / "panel_px.parquet")[LEGS].ffill().iloc[-1]
        px = np.where(np.isfinite(px), px, last.to_numpy(float))
    if balance is None and equity is not None:
        bal = equity  # dry-run compte flat: equity == balance
    preview = governor.preview(phase, (weights["XAUUSD"], weights["USDJPY"]),
                               on_day, bal, pos, avg, px, att, target_date)
    preview["preview_basis"] = "state_live" if state is not None else "fallback"
    audit["governor_preview"] = preview

    tonight = dict(preview["targets_usd_quantized"])
    if on_day and pos[3] == 0.0 and "ger40_1735_usd_quantized" in preview:
        tonight["GER40"] = preview["ger40_1735_usd_quantized"]
    elif pos[3] != 0.0:
        tonight["GER40"] = float(pos[3])
    audit["swap_forecast_tonight"] = swaps.forecast_night(tonight, target_date)

    mode = _phase_mode_params(phase)
    targets = statefiles.build_targets(spec.spec_sha256(), target_date, phase,
                                       weights, on_day, mode, audit)
    out_path = None
    if write and not dry_run:
        out_path = statefiles.mt5_files_dir() / "targets.json"
        statefiles.atomic_write_json(out_path, targets)
    result = dict(status="OK", target_date=str(target_date.date()), weights=weights,
                  on_day=on_day, phase=phase, written=str(out_path) if out_path else None,
                  seams=audit["data"].get("seams_bps"), targets=targets)
    if emit_json:
        print(json.dumps(targets, indent=1, default=str))
    else:
        print(f"brain OK {target_date.date()} phase={phase} on_day={int(on_day)} "
              f"w_xau={weights['XAUUSD']:+.4f} w_jpy={weights['USDJPY']:+.4f} "
              f"scale={preview['governor']['scale']:.2f} "
              f"-> {out_path or '(dry-run, non écrit)'}")
    return result


def check() -> None:
    sp = spec.load()
    spec.verify_mqh_pin()
    miss = spec.loader().verify_pins_in_repo()
    print(f"spec OK {sp['meta']['version']} sha {spec.spec_sha256()[:12]}… ; "
          f"mqh pin OK ; pins repo: "
          f"{'tous présents' if not miss else 'MANQUANTS ' + str(miss)}")
    print(f"challenge: vm={spec.challenge_cfg(sp)['vm']} orb_risk="
          f"{spec.challenge_cfg(sp)['orb_risk']} micro={spec.challenge_cfg(sp)['micro_orb']}"
          f" | funded: vm={spec.funded_cfg(sp)['vm']} ORB_RT_BPS="
          f"{sp['funded']['ORB_RT_BPS']['value']} (pas de ré-ancrage avant verdict N=60)")
    try:
        d = statefiles.mt5_files_dir()
        print(f"MT5 files dir: {d} ; market_export "
              f"{'présent' if (d / 'market_export.json').exists() else 'ABSENT'} ; "
              f"state.json {'présent' if (d / 'state.json').exists() else 'ABSENT'}")
    except RuntimeError as e:
        print(f"env: {e}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--equity", type=float, default=None)
    ap.add_argument("--balance", type=float, default=None)
    ap.add_argument("--phase", default=None, choices=[None, "P1", "P2", "FUNDED"])
    ap.add_argument("--attempt-start", default=None)
    ap.add_argument("--cache-dir", default=None)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        check()
        return 0
    try:
        run(dry_run=a.dry_run, as_of=a.as_of, equity=a.equity, balance=a.balance,
            phase=a.phase, attempt_start=a.attempt_start,
            cache_dir=Path(a.cache_dir) if a.cache_dir else None,
            write=not a.no_write, emit_json=a.json)
        if not a.dry_run:
            statefiles.write_brain_status("OK", dict())
        return 0
    except Exception as e:
        if not a.dry_run:
            statefiles.write_brain_status("ERROR", dict(error=repr(e)))
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
