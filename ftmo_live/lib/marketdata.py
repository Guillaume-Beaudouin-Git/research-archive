"""Cache live = panels gelés + extension D1 exportée par l'EA + ancres yaml.

Le sim (462 cohortes) lit cache/panel_{px,rets,swapL,swapS,mult}.parquet ; le live
étend ces mêmes fichiers (jamais modifiés en place — copie étendue dans
ftmo_live/runtime/cache_live/) :
  px    : closes D1 de l'EA pour dates > fin du panel gelé (4 jambes, reste NaN)
  rets  : ratio sur la série fusionnée (sémantique pct_change du panel, vérifiée ==)
  swaps : ffill du panel gelé — ses dernières lignes SONT les ancres mesurées du
          yaml (vérifié −2.241/−1.607) ; assert anti-désync vs spec.swap_anchors
  mult  : règle calendaire du yaml (indices vendredi ×3, métaux/FX mercredi ×3)
  + ligne NaN à target_date T → WT.loc[T] de build_signals = signal causal exact
    (données ≤ T−1), même code path que le sim.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from . import PKG, LEGS
from . import spec as S
from . import swaps as SW

FROZEN_CACHE = PKG / "cache"
EXPORT_MAX_AGE_H = 6.0
SEAM_WARN_BPS = 30.0
SEAM_LOOKBACK = 5
SWAP_ANCHOR_GAP_WARN_BPS = 0.5   # panel gelé vs ancre mesurée (informatif, attendu post-recost)


class MarketDataError(RuntimeError):
    pass


def load_export(path: Path, now: Optional[datetime] = None,
                max_age_h: float = EXPORT_MAX_AGE_H) -> dict:
    """market_export.json de l'EA. MarketDataError si absent/stale/incomplet."""
    if not path.exists():
        raise MarketDataError(f"export EA absent: {path}")
    exp = json.loads(path.read_text())
    gen = datetime.strptime(exp["generated_at_paris"], "%Y.%m.%d %H:%M:%S")
    now = now or datetime.now()
    age_h = (now - gen).total_seconds() / 3600.0
    if age_h > max_age_h:
        raise MarketDataError(
            f"export EA stale {age_h:.1f}h > {max_age_h}h (généré {gen}) — "
            "pas de close T-1 fiable, brain refuse d'écrire targets")
    missing = [l for l in LEGS if l not in exp.get("symbols", {})]
    if missing:
        raise MarketDataError(f"export EA incomplet, jambes manquantes: {missing}")
    return exp


def _export_closes(exp: dict, leg: str) -> pd.Series:
    rows = exp["symbols"][leg]["d1"]
    idx = pd.to_datetime([r[0] for r in rows], format="%Y.%m.%d")
    return pd.Series([float(r[4]) for r in rows], index=idx, name=leg).sort_index()


def _seam_bps(frozen: pd.Series, live: pd.Series) -> float:
    common = frozen.dropna().index.intersection(live.dropna().index)
    if len(common) == 0:
        return np.nan
    tail = common[-SEAM_LOOKBACK:]
    return float(((live[tail] / frozen[tail] - 1.0).abs() * 1e4).max())


def build_live_cache(export: dict, target_date: pd.Timestamp,
                     out_dir: Path) -> dict:
    """Écrit les 5 panels étendus dans out_dir ; retourne les diagnostics.

    target_date = date de trade T (rebalance 22:05) ; la dernière barre close
    utilisée est strictement < T (les barres D1 de date >= T sont écartées,
    couvrant la barre in-progress de l'export 21:45).
    """
    target_date = pd.Timestamp(target_date).normalize()
    px = pd.read_parquet(FROZEN_CACHE / "panel_px.parquet")
    rets = pd.read_parquet(FROZEN_CACHE / "panel_rets.parquet")
    sL = pd.read_parquet(FROZEN_CACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(FROZEN_CACHE / "panel_swapS.parquet")
    mu = pd.read_parquet(FROZEN_CACHE / "panel_mult.parquet")
    frozen_end = px.index.max()

    closes = {l: _export_closes(export, l) for l in LEGS}
    seams = {l: _seam_bps(px[l], closes[l]) for l in LEGS}

    new_dates = sorted(set().union(*[
        set(c.index[(c.index > frozen_end) & (c.index < target_date)])
        for c in closes.values()]))
    idx_ext = px.index.append(pd.DatetimeIndex(new_dates + [target_date]))
    idx_ext = pd.DatetimeIndex(sorted(set(idx_ext)))

    px_e = px.reindex(idx_ext)
    for l in LEGS:
        ext = closes[l]
        ext = ext[(ext.index > frozen_end) & (ext.index < target_date)]
        px_e.loc[ext.index, l] = ext.values

    rets_e = rets.reindex(idx_ext)
    for l in LEGS:
        s = px_e[l]
        new = [d for d in idx_ext if d > frozen_end and d < target_date]
        for d in new:
            prev = s.loc[:d].dropna()
            prev = prev[prev.index < d]
            if len(prev) and np.isfinite(s[d]):
                rets_e.loc[d, l] = s[d] / prev.iloc[-1] - 1.0

    # extension swap = points MESURÉS datés -> bps au prix du jour (v2.2.1) ;
    # l'écart panel-gelé vs ancre est ATTENDU (prix a bougé) — warn informatif
    sL_e = sL.reindex(idx_ext)
    sS_e = sS.reindex(idx_ext)
    anchor_gap = {}
    for l in LEGS:
        last_L = float(sL[l].dropna().iloc[-1])
        anchor_gap[l] = round(last_L - SW.swap_bps(l, "long"), 3)
        px_known = px_e[l].ffill()
        for d in idx_ext[idx_ext > frozen_end]:
            p = px_known.loc[d]
            if not np.isfinite(p):
                continue
            sL_e.loc[d, l] = SW.swap_bps(l, "long", p)
            sS_e.loc[d, l] = SW.swap_bps(l, "short", p)
        sL_e[l] = sL_e[l].ffill()
        sS_e[l] = sS_e[l].ffill()

    mu_e = mu.reindex(idx_ext)
    for l in LEGS:
        new_mask = mu_e.index > frozen_end
        mu_e.loc[new_mask, l] = [
            float(SW.night_multiplier(l, d)) for d in mu_e.index[new_mask]]

    out_dir.mkdir(parents=True, exist_ok=True)
    px_e.to_parquet(out_dir / "panel_px.parquet")
    rets_e.to_parquet(out_dir / "panel_rets.parquet")
    sL_e.to_parquet(out_dir / "panel_swapL.parquet")
    sS_e.to_parquet(out_dir / "panel_swapS.parquet")
    mu_e.to_parquet(out_dir / "panel_mult.parquet")

    last_closed = {l: str(px_e[l].dropna().index.max().date()) for l in LEGS}
    diag = dict(frozen_end=str(frozen_end.date()), target_date=str(target_date.date()),
                n_extended=len(new_dates), seams_bps=seams, last_closed=last_closed,
                seam_warn=[l for l, b in seams.items()
                           if np.isfinite(b) and b > SEAM_WARN_BPS],
                swap_anchor_gap_bps=anchor_gap,
                swap_anchor_gap_warn=[l for l, g in anchor_gap.items()
                                      if abs(g) > SWAP_ANCHOR_GAP_WARN_BPS])
    return diag


def expected_bdays_gap(frozen_end: pd.Timestamp, target_date: pd.Timestamp) -> int:
    """Jours ouvrés attendus entre fin du panel gelé (exclu) et T (exclu)."""
    days = pd.bdate_range(frozen_end + timedelta(days=1),
                          target_date - timedelta(days=1))
    return len(days)


def build_truncated_cache(target_date: pd.Timestamp, out_dir: Path) -> dict:
    """Cache dry-run : panels gelés tronqués STRICTEMENT < T + ligne NaN à T.

    Reproduit la situation live (données <= T-1 seulement) sur l'historique gelé —
    support du test « brain vs cibles du simulateur » (tolérance = quantization).
    """
    target_date = pd.Timestamp(target_date).normalize()
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("panel_px", "panel_rets", "panel_swapL", "panel_swapS", "panel_mult"):
        df = pd.read_parquet(FROZEN_CACHE / f"{name}.parquet")
        cut = df[df.index < target_date]
        cut = cut.reindex(cut.index.append(pd.DatetimeIndex([target_date])))
        if name in ("panel_swapL", "panel_swapS"):
            cut = cut.ffill()
        elif name == "panel_mult":
            for l in LEGS:
                cut.loc[target_date, l] = float(SW.night_multiplier(l, target_date))
        cut.to_parquet(out_dir / f"{name}.parquet")
    return dict(target_date=str(target_date.date()), mode="truncated_frozen")
