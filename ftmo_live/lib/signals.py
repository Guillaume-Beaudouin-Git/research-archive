"""Signaux des sleeves = cleanroom E.build_signals() sur le cache live.

Même fonction, mêmes octets de code que les 462 cohortes — seul E.CACHE est
redirigé (context manager) vers le cache étendu. E.AOUT (rt costs) reste gelé.
WT.loc[T] est par construction le poids que le sim appliquerait au jour T
(pipeline shift(1) : toutes les couches — sign blend, vol-target, book-vol 60d,
vol-derisk 20d, equity-gate MA100 — n'utilisent que des données <= T-1).
"""
from contextlib import contextmanager
from pathlib import Path
from typing import Tuple

import pandas as pd

import engine as E  # cleanroom (sys.path via lib/__init__)


@contextmanager
def _cache_redirect(cache_dir: Path):
    saved = E.CACHE
    E.CACHE = Path(cache_dir)
    try:
        yield
    finally:
        E.CACHE = saved


def weights_for(target_date: pd.Timestamp, cache_dir: Path) -> Tuple[pd.Series, dict]:
    """(WT.loc[T] [XAUUSD, USDJPY], diagnostics signal) sur le cache étendu.

    Lève KeyError si T absent de l'index (cache non construit pour cette date).
    """
    target_date = pd.Timestamp(target_date).normalize()
    with _cache_redirect(cache_dir):
        WT, ON = E.build_signals()
    row = WT.loc[target_date]
    on_day = bool(ON.loc[target_date] > 0)
    diag = _signal_diag(target_date, cache_dir)
    diag["on_day"] = on_day
    return row, diag


def _signal_diag(t: pd.Timestamp, cache_dir: Path) -> dict:
    """Composants du signal à T-1 (audit trail des targets), recalcul léger."""
    px = pd.read_parquet(Path(cache_dir) / "panel_px.parquet")
    p = px["XAUUSD"].dropna()
    pj = px["USDJPY"].dropna()
    out = dict(gold_last_close=float(p.iloc[-1]), gold_last_date=str(p.index[-1].date()),
               jpy_last_close=float(pj.iloc[-1]), jpy_last_date=str(pj.index[-1].date()))
    if len(pj) > 252:
        out["j1_mom_12_1"] = float(pj.shift(21).iloc[-1] / pj.shift(252).iloc[-1] - 1.0)
    return out


def sim_aligned_signals() -> Tuple[pd.DataFrame, pd.Series]:
    """WT/ON du stack gelé (cache d'origine), pour dry-run et tests."""
    return E.build_signals()
