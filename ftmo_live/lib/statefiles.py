"""Protocole fichiers brain <-> EA <-> supervisor/reconcile (MQL5/Files).

- targets.json  (brain -> EA)   : clés plates préfixées ea_* (parse MQL5 par
  recherche de clé) + blob "audit" complet. Écriture atomique tmp+rename.
- state.json    (EA -> python)  : heartbeat M1, room/floors/positions/états.
- fills.csv     (EA append)     : req/fill par jambe, slippage, latence.
- swaps_billed.csv (EA append)  : swap facturé par symbole et par nuit.
- market_export.json (EA -> brain) : 520 barres D1 x 4 jambes + specs contrats.
- FLAT          (humain/superviseur) : kill-file -> flatten + disable.
"""
import csv
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd

from . import LIVE_ROOT, RUNTIME

PARIS = ZoneInfo("Europe/Paris")
TS_FMT = "%Y.%m.%d %H:%M:%S"

TARGETS_SCHEMA = "ftmo_live.targets.v1"
STATE_SCHEMA = "ftmo_live.state.v1"

FILLS_COLUMNS = ["ts_server", "ts_paris", "phase", "reason", "symbol", "side",
                 "lots", "req_price", "fill_price", "slip_bps", "latency_ms",
                 "order_ticket", "deal_ticket", "position_id", "magic", "comment"]
SWAPS_COLUMNS = ["date_paris", "symbol", "lots_held", "notional_usd", "swap_usd"]


def now_paris() -> datetime:
    return datetime.now(tz=PARIS)


def fmt_ts(dt: datetime) -> str:
    return dt.strftime(TS_FMT)


def parse_ts(s: str) -> datetime:
    return datetime.strptime(s, TS_FMT)


def mt5_files_dir() -> Path:
    d = os.environ.get("FTMO_LIVE_MT5_FILES")
    if not d:
        raise RuntimeError("FTMO_LIVE_MT5_FILES non défini (voir .env.example)")
    p = Path(d)
    if not p.is_dir():
        raise RuntimeError(f"FTMO_LIVE_MT5_FILES introuvable: {p}")
    return p


def atomic_write_json(path: Path, payload: dict) -> None:
    """tmp + rename (même fs) — l'EA ne lit jamais un fichier partiel."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=1, sort_keys=False, default=str)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def build_targets(spec_sha: str, valid_for: pd.Timestamp, phase_hint: str,
                  weights: Dict[str, float], on_day: bool, mode_params: dict,
                  audit: dict) -> dict:
    """targets.json — champs EA plats ea_* + audit imbriqué."""
    return {
        "schema": TARGETS_SCHEMA,
        "ea_spec_sha256": spec_sha,
        "ea_generated_at_paris": fmt_ts(now_paris().replace(tzinfo=None)),
        "ea_valid_for_date": str(pd.Timestamp(valid_for).date()),
        "ea_phase_hint": phase_hint,
        "ea_w_xauusd": round(float(weights["XAUUSD"]), 8),
        "ea_w_usdjpy": round(float(weights["USDJPY"]), 8),
        "ea_on_day": int(bool(on_day)),
        "ea_vm": mode_params["vm"],
        "ea_on_w": mode_params["on_w"],
        "ea_orb_risk": mode_params["orb_risk"],
        "ea_micro_orb": int(bool(mode_params["micro_orb"])),
        "ea_breaker": mode_params["breaker"],
        "ea_taper": mode_params["taper"],
        "ea_glide": mode_params["glide"],
        "ea_pace": int(mode_params.get("pace", 0)),
        "ea_margin_cap": mode_params["margin_cap"],
        "audit": audit,
    }


def targets_age_h(targets: dict, now: Optional[datetime] = None) -> float:
    gen = parse_ts(targets["ea_generated_at_paris"])
    now = now or now_paris().replace(tzinfo=None)
    return (now - gen).total_seconds() / 3600.0


def read_state(files_dir: Path) -> Optional[dict]:
    return read_json(files_dir / "state.json")


def state_age_s(state: dict, now: Optional[datetime] = None) -> float:
    now = now or now_paris().replace(tzinfo=None)
    return (now - parse_ts(state["ts_paris"])).total_seconds()


def append_csv(path: Path, columns: List[str], row: dict) -> None:
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        if new:
            w.writeheader()
        w.writerow({c: row.get(c, "") for c in columns})


def read_fills(files_dir: Path, date_paris: Optional[str] = None) -> pd.DataFrame:
    p = files_dir / "fills.csv"
    if not p.exists():
        return pd.DataFrame(columns=FILLS_COLUMNS)
    df = pd.read_csv(p)
    if date_paris is not None and len(df):
        # l'EA horodate "YYYY.MM.DD HH:MM:SS" ; date_paris arrive en "YYYY-MM-DD"
        days = df["ts_paris"].astype(str).str[:10].str.replace(".", "-", regex=False)
        df = df[days == str(date_paris)]
    return df


def read_swaps_billed(files_dir: Path, date_paris: Optional[str] = None) -> pd.DataFrame:
    p = files_dir / "swaps_billed.csv"
    if not p.exists():
        return pd.DataFrame(columns=SWAPS_COLUMNS)
    df = pd.read_csv(p)
    if date_paris is not None and len(df):
        df = df[df["date_paris"].astype(str) == date_paris]
    return df


def write_brain_status(status: str, detail: dict) -> Path:
    """Statut du dernier run brain (supervisor alerte sur != OK)."""
    RUNTIME.mkdir(parents=True, exist_ok=True)
    p = RUNTIME / "brain_status.json"
    atomic_write_json(p, dict(status=status, ts_paris=fmt_ts(
        now_paris().replace(tzinfo=None)), **detail))
    return p


def read_brain_status() -> Optional[dict]:
    return read_json(RUNTIME / "brain_status.json")
