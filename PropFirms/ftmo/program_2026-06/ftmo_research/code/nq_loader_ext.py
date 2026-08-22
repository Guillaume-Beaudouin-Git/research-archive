"""
nq_loader_ext.py — Extension proposée de `data/cache.py::load_nq_1min` pour
                   servir 2008-2025 (merged) en plus de 2022-2025 (Kaggle).

À intégrer DANS data/cache.py une fois le QA de soudure PASS (cf.
data/ftmo_research/FETCH_NQ_2008_plan.md §5).

Garde-fous API :
  - `source='merged'` lit la sidecar `NQ_1min_2008-2025_MERGED.json` et exige
    `seam_qa_status == "PASS"`. Sinon lève RuntimeError. Aucun chemin silencieux
    vers un merged non validé.
  - `source='kaggle'` conserve le comportement legacy strict (rétrocompat).
  - `source='historical'` sert uniquement le parquet firstrate (utile pour
    audits/diagnostics, jamais en production de backtest).

Branche moteur ORB : ajouter dans `data/ftmo_research/audit/orb_core.py::_load_m5`
une branche `symbol == "NQ"` qui appelle `load_nq_1min(source="merged")`, drop
tz-info, resample 5min. Le reste de orb_core est inchangé.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2] / "data"      # → Algo_claude/data/
_RAW = _ROOT / "raw"
_META = _ROOT / "metadata"

# Paths (alignés sur le plan §5)
_PATH_KAGGLE     = _RAW / "NQ_1min_2022-12-26_2025-12-11.parquet"
_PATH_HISTORICAL = _RAW / "NQ_1min_2008-XX-XX_2021-12-31.parquet"   # à renommer après fetch
_PATH_MERGED     = _RAW / "NQ_1min_2008-2025_MERGED.parquet"
_META_MERGED     = _RAW / "NQ_1min_2008-2025_MERGED.json"


def _assert_merged_qa_pass() -> dict:
    """
    Refuse de servir le merged tant que le QA n'est pas PASS.

    Returns la sidecar metadata si OK.
    Raises RuntimeError sinon.
    """
    if not _META_MERGED.exists():
        raise RuntimeError(
            f"Merged metadata missing: {_META_MERGED}\n"
            "Le merged 2008-2025 n'a pas été validé par le QA de soudure. "
            "Lance: data/ftmo_research/code/nq_seam_qa.py "
            "(cf. data/ftmo_research/FETCH_NQ_2008_plan.md §4)."
        )
    meta = json.loads(_META_MERGED.read_text())
    status = meta.get("seam_qa_status")
    if status != "PASS":
        raise RuntimeError(
            f"Merged QA status = {status!r} (expected 'PASS'). "
            f"Voir le rapport (hash {meta.get('seam_qa_hash', '?')[:12]}). "
            "Loader refuse de servir un merged non validé."
        )
    return meta


def load_nq_1min(path: str | None = None,
                 source: str = "merged") -> pd.DataFrame:
    """
    NQ 1-min loader étendu.

    Parameters
    ----------
    path : str | None
        Override explicit pour cas legacy (path vers un CSV Kaggle).
        Si fourni, force source='kaggle' (cohérence rétrocompat).
    source : 'merged' | 'kaggle' | 'historical'
        - 'merged' (défaut une fois QA PASS) : 2008-2025 souclé.
        - 'kaggle' : 2022-2025 seulement (= comportement legacy).
        - 'historical' : 2008-2021 firstrate seul (audit, pas backtest prod).

    Returns
    -------
    pd.DataFrame indexé `timestamp_et` (DatetimeTZDtype US/Eastern),
    columns: open, high, low, close, volume (+ vwap_rth/vwap_eth si dispos).
    """
    if path is not None:
        # Override legacy → comportement strict Kaggle
        from data.cache import load_nq_1min as _legacy_load_nq_1min
        return _legacy_load_nq_1min(path=path)

    if source == "kaggle":
        if not _PATH_KAGGLE.exists():
            raise FileNotFoundError(
                f"Kaggle parquet not found: {_PATH_KAGGLE}\n"
                "Build it first via data/cache.py::load_nq_1min() avec le CSV."
            )
        log.info("Loading NQ source=kaggle → %s", _PATH_KAGGLE.name)
        return pd.read_parquet(_PATH_KAGGLE, engine="pyarrow")

    if source == "historical":
        if not _PATH_HISTORICAL.exists():
            raise FileNotFoundError(
                f"Historical parquet not found: {_PATH_HISTORICAL}\n"
                "Fetch firstrate NQ 1-min 2008-2021 et ingère-le ici, "
                "tz-aware US/Eastern. Cf. plan §1, §3."
            )
        log.info("Loading NQ source=historical → %s", _PATH_HISTORICAL.name)
        return pd.read_parquet(_PATH_HISTORICAL, engine="pyarrow")

    if source == "merged":
        if not _PATH_MERGED.exists():
            raise FileNotFoundError(
                f"Merged parquet not found: {_PATH_MERGED}\n"
                "Lance le QA de soudure (cf. plan §4) qui le génère si PASS."
            )
        _assert_merged_qa_pass()
        log.info("Loading NQ source=merged → %s", _PATH_MERGED.name)
        return pd.read_parquet(_PATH_MERGED, engine="pyarrow")

    raise ValueError(f"Unsupported source={source!r}. "
                     "Use one of: 'merged', 'kaggle', 'historical'.")


# ─────────────────────────────────────────────────────────────────────────────
# Patch suggéré pour data/ftmo_research/audit/orb_core.py::_load_m5
# ─────────────────────────────────────────────────────────────────────────────
#
# @lru_cache(maxsize=8)
# def _load_m5(symbol: str) -> pd.DataFrame:
#     if symbol == "NQ":
#         # Drop-in : 2008-2025 merged
#         from data.cache import load_nq_1min
#         df = load_nq_1min(source="merged")
#         df = df[["open", "high", "low", "close"]].copy()
#         # orb_core travaille en tz-naive — drop tz mais reste en wall-clock ET
#         df.index = df.index.tz_localize(None)
#     elif symbol in ("US100", "US500", "US30", "US2000"):
#         df = pd.read_parquet(DATA / "m1_panel.parquet")[symbol].dropna()
#     else:
#         df = pd.read_parquet(DATA / f"{symbol}_m1_panel.parquet")
#         df.index = pd.to_datetime(df.index)
#         if df.index.tz is not None:
#             df.index = df.index.tz_localize(None)
#         df = df[["open", "high", "low", "close"]].dropna()
#     return df.resample("5min").agg(
#         {"open": "first", "high": "max", "low": "min", "close": "last"}
#     ).dropna()
#
# Sleeves NQ à ajouter dans SLEEVES (orb_core.py) :
#   ("NQ", 9, 30, 16, 6),    # 30-min OR, RTH US 09:30 ET
#   ("NQ", 9, 30, 12, 3),    # 15-min OR variante (à benchmarker)
#
# Et étendre COST_POINTS pour NQ futures :
#   COST_POINTS = {"US100": 3.0, "GER40": 1.5, "NQ": 1.0}  # ~4 ticks RT MNQ
# ─────────────────────────────────────────────────────────────────────────────
