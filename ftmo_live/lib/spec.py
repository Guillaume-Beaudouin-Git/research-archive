"""Accès spec v2.2 — délègue intégralement au loader épinglé v22/ea/brain.py (79c6912).

Aucun rechargement parallèle du yaml : import du module loader sous le nom
`v22ea_brain` (collision évitée avec ftmo_live/brain.py), puis accesseurs.
"""
import hashlib
import importlib.util
from functools import lru_cache
from typing import Optional

from . import EA_DIR, LEGS, PIN_MQH_SHA256, REPO

_LOADER_PATH = EA_DIR / "brain.py"


@lru_cache(maxsize=1)
def loader():
    """Module v22/ea/brain.py importé sous le nom v22ea_brain."""
    spec = importlib.util.spec_from_file_location("v22ea_brain", _LOADER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # shim déploiement: REPO est hardcodé chemin Mac dans le loader gelé —
    # repointé vers la racine réelle (no-op sur le Mac, requis sur le VPS)
    mod.REPO = REPO
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


def risk_overlays(s: Optional[dict] = None) -> dict:
    """Bloc v2.8 : overlays de risque HORS challenge.config (drift-check intact).

    `.get` et pas `[...]` : le bloc n'existe pas dans les specs gelées antérieures
    à v2.2.2 — un accesseur qui lèverait sur une spec ancienne rendrait le code
    incapable de tourner sur un rollback.
    """
    s = s or load()
    return dict(s.get("risk_overlays") or {})


def leg_lev_cap_vector(s: Optional[dict] = None,
                       scope: str = "challenge") -> Optional[list]:
    """Vecteur [XAUUSD, USDJPY, US100, GER40] de caps de notionnel/equity, ou None.

    None (overlay absent, enabled=false, ou scope hors `applies_to`) => NO-OP
    STRICT côté moteur : tous les chiffres pinnés v2.2 se reproduisent à
    l'identique. `applies_to` est respecté ici, sinon le yaml mentirait sur son
    propre périmètre.
    """
    ro = risk_overlays(s).get("leg_leverage_cap") or {}
    if not ro.get("enabled"):
        return None
    if scope not in (ro.get("applies_to") or []):
        return None
    caps = ro.get("caps") or {}
    return [caps.get(leg) for leg in LEGS]


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
