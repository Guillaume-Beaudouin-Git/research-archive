"""Accès spec v2.2 — délègue intégralement au loader épinglé v22/ea/brain.py (79c6912).

Aucun rechargement parallèle du yaml : import du module loader sous le nom
`v22ea_brain` (collision évitée avec ftmo_live/brain.py), puis accesseurs.
"""
import hashlib
import importlib.util
from functools import lru_cache
from typing import Optional

from . import EA_DIR, PIN_MQH_SHA256

_LOADER_PATH = EA_DIR / "brain.py"


@lru_cache(maxsize=1)
def loader():
    """Module v22/ea/brain.py importé sous le nom v22ea_brain."""
    spec = importlib.util.spec_from_file_location("v22ea_brain", _LOADER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@lru_cache(maxsize=1)
def load() -> dict:
    """Spec yaml épinglée (hash + drift-check + pins) via le loader. SpecError sinon."""
    return loader().load()


def verify_mqh_pin() -> None:
    """sha256(spec_v22.mqh) doit == pin 1d834546… (ancre #20). RuntimeError sinon."""
    sha = hashlib.sha256((EA_DIR / "spec_v22.mqh").read_bytes()).hexdigest()
    if sha != PIN_MQH_SHA256:
        raise RuntimeError(
            f"spec_v22.mqh sha {sha[:12]}… != pin {PIN_MQH_SHA256[:12]}… — "
            "mqh régénéré sans re-gel (ancre #20) : STOP")


def spec_sha256() -> str:
    return loader().PIN_SHA256


# ---- accesseurs (zéro constante locale) ----
def challenge_cfg(s: Optional[dict] = None) -> dict:
    s = s or load()
    return s["challenge"]["config"]


def funded_cfg(s: Optional[dict] = None) -> dict:
    s = s or load()
    return s["funded"]["config"]


def rules(s: Optional[dict] = None) -> dict:
    s = s or load()
    return s["account"]["rules"]


def account_size(s: Optional[dict] = None) -> float:
    s = s or load()
    return float(s["account"]["size_usd"])


def micro_orb(s: Optional[dict] = None) -> dict:
    s = s or load()
    return s["challenge"]["micro_orb_day_counter"]


def schedule_cet(s: Optional[dict] = None) -> dict:
    s = s or load()
    return s["challenge"]["schedule_cet"]


def swap_anchors_bps(s: Optional[dict] = None) -> dict:
    """Ancres swap mesurées (bps/nuit) par jambe+side, ex 'US100_long': -2.241."""
    s = s or load()
    return dict(s["cost_anchors"]["swap_bps_per_night_measured"])


def rt_anchors_bps(s: Optional[dict] = None) -> dict:
    s = s or load()
    return dict(s["cost_anchors"]["rt_bps_legs"])


def rt_anchors_allin_bps(s: Optional[dict] = None) -> dict:
    """RT spread + commissions (v2.2.1) — modèle de coût forward/reconcile."""
    s = s or load()
    return dict(s["cost_anchors"]["rt_bps_legs_allin"])


def measured_specs(s: Optional[dict] = None) -> dict:
    """Bloc v2.2.1 : specs mesurées datées (points, triple_dow, marge, bornes)."""
    s = s or load()
    return s["measured_specs"]


def triple_days(s: Optional[dict] = None) -> dict:
    """{'indices': 'vendredi', 'metaux_fx': 'mercredi'}."""
    s = s or load()
    return dict(s["cost_anchors"]["triple_days"])


def withdrawals(s: Optional[dict] = None) -> dict:
    s = s or load()
    return s["funded"]["withdrawals"]


def wall_days(s: Optional[dict] = None) -> int:
    s = s or load()
    return int(s["account"]["mission_wall_days"])
