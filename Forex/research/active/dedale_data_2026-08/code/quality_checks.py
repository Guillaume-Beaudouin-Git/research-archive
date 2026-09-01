"""
quality_checks.py — certification L52/L56/L60-style pour les séries Dedale acquises.

Toutes les fonctions prennent/retournent des DataFrames pandas au format gabarit
(index timestamp_utc tz-aware UTC, colonnes open/high/low/close) et n'écrivent rien
sur disque elles-mêmes — le script appelant (certify_all.py) assemble le tableau.

Δn_tests = 0 : aucune hypothèse de signal testée ici, uniquement de la QA de données.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def flat_pct_by_year(df: pd.DataFrame) -> pd.Series:
    """% de barres high==low, par année (L60)."""
    flat = (df["high"] == df["low"])
    return (flat.groupby(df.index.year).mean() * 100).round(3)


def gap_report(df: pd.DataFrame, session_gap_minutes: int = 60) -> dict:
    """Trous > session_gap_minutes hors week-end (vendredi soir -> dimanche soir est
    un trou LÉGITIME, exclu via le seuil 24h sur un redémarrage lundi/dimanche).
    Retourne le nb de trous illégitimes et les 5 plus longs, avec leur horodatage
    de début (le dernier timestamp AVANT le trou)."""
    idx = df.index
    ts = idx.to_series()
    deltas = ts.diff().dt.total_seconds().div(60)
    starts = ts.shift(1)
    weekend_reopen = (idx.dayofweek.isin([0, 6])) & (deltas > 24 * 60)
    mask = (deltas > session_gap_minutes) & (~weekend_reopen) & deltas.notna()
    illegit = deltas[mask]
    illegit_starts = starts[mask]
    order = illegit.sort_values(ascending=False).index[:5]
    return dict(
        n_illegit_gaps=int(mask.sum()),
        max_illegit_gap_min=float(illegit.max()) if len(illegit) else 0.0,
        top5_gaps=[dict(start=str(illegit_starts[t]), minutes=round(float(illegit[t]), 1))
                   for t in order],
    )


def weekday_coverage(df: pd.DataFrame, start: str, end: str) -> dict:
    """Jours ouvrés (lun-ven) manquants entièrement dans [start, end]."""
    all_bdays = pd.bdate_range(start, end, tz="UTC")
    present_days = pd.DatetimeIndex(df.index.normalize().unique())
    missing = [d for d in all_bdays if d not in present_days]
    return dict(n_bdays_expected=len(all_bdays), n_bdays_missing=len(missing),
                pct_missing=round(100 * len(missing) / max(1, len(all_bdays)), 3),
                sample_missing=[str(d.date()) for d in missing[:10]])


def cross_check(cross: pd.DataFrame, leg1: pd.DataFrame, leg2: pd.DataFrame,
                 op: str) -> dict:
    """Cohérence de niveau : cross.close vs leg1.close (op) leg2.close, sur
    l'intersection des timestamps. op in {'mul', 'div'} : cross = leg1*leg2 ou leg1/leg2.
    Retourne l'erreur relative médiane et p95 (en bps)."""
    idx = cross.index.intersection(leg1.index).intersection(leg2.index)
    if len(idx) == 0:
        return dict(n=0, note="no overlapping timestamps")
    c = cross.loc[idx, "close"]
    a = leg1.loc[idx, "close"]
    b = leg2.loc[idx, "close"]
    implied = a * b if op == "mul" else a / b
    rel_err_bps = ((c - implied).abs() / c) * 1e4
    return dict(
        n=len(idx),
        median_bps=round(float(rel_err_bps.median()), 3),
        p95_bps=round(float(rel_err_bps.quantile(0.95)), 3),
        max_bps=round(float(rel_err_bps.max()), 3),
    )


def tz_offset_check(mine: pd.DataFrame, reference: pd.DataFrame) -> dict:
    """Décalage de fuseau : pour chaque timestamp commun, écart de close (devrait être
    ~0 si même minute) ; on rapporte aussi le décalage médian en minutes en cherchant,
    pour chaque barre 'mine', le meilleur alignement temporel contre 'reference' (recherche
    de shift qui minimise l'erreur de close sur un échantillon)."""
    idx_common = mine.index.intersection(reference.index)
    direct_match_frac = len(idx_common) / max(1, len(mine))
    if len(idx_common) > 100:
        d = (mine.loc[idx_common, "close"] - reference.loc[idx_common, "close"]).abs()
        max_abs_diff = float(d.max())
        median_abs_diff = float(d.median())
    else:
        max_abs_diff = median_abs_diff = None

    best_shift, best_err = 0, None
    if len(mine) > 200:
        sample = mine.iloc[100:400]
        for shift in range(-5, 6):
            shifted_idx = sample.index + pd.Timedelta(minutes=shift)
            common = shifted_idx.intersection(reference.index)
            if len(common) < 50:
                continue
            s2 = sample.copy()
            s2.index = shifted_idx
            err = (s2.loc[common, "close"] - reference.loc[common, "close"]).abs().mean()
            if best_err is None or err < best_err:
                best_err, best_shift = err, shift

    return dict(
        n_common_ts=int(len(idx_common)),
        direct_match_frac=round(direct_match_frac, 4),
        median_abs_close_diff=median_abs_diff,
        max_abs_close_diff=max_abs_diff,
        best_alignment_shift_min=best_shift,
        best_alignment_mean_err=round(best_err, 6) if best_err is not None else None,
    )
