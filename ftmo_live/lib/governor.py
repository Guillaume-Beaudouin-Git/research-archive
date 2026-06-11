"""Gouverneur de sizing = appels DIRECTS à cleanroom E._target_for_segment.

vm/taper/glide/pace/margin-cap/quantize : aucun de ces calculs n'est réécrit —
le préview des cibles vient de la fonction du sim avec un M-stub à 2 dates
(i0 = début de tentative, i = aujourd'hui). Les composants taper/glide/pace
exposés pour le reporting sont EXTRAITS par appels-sonde à la même fonction
(jamais recalculés par une formule locale).
"""
from typing import Dict, Optional

import numpy as np
import pandas as pd

import engine as E  # cleanroom

from . import LEGS
from . import spec as S

PHASES = ("P1", "P2", "FUNDED")


def phase_cfg(phase: str) -> dict:
    """cfg sim de la phase: P1/P2 = challenge (P2 -> vm x p2_mult), FUNDED = funded."""
    sp = S.load()
    if phase == "FUNDED":
        cfg = dict(S.funded_cfg(sp))
        cfg["max_cal"] = None
        return cfg
    cfg = dict(S.challenge_cfg(sp))
    cfg["target"] = float(S.rules(sp)["targets"]["phase1" if phase == "P1" else "phase2"])
    cfg["max_cal"] = S.wall_days(sp)
    if phase == "P2":
        cfg["vm"] = cfg["vm"] * cfg.get("p2_mult", 1.0)
    return cfg


def _stub(attempt_start: pd.Timestamp, today: pd.Timestamp) -> dict:
    return {"dates": [pd.Timestamp(attempt_start), pd.Timestamp(today)]}


def _call(s_idx: int, cfg: dict, wt_row, on_flag: float, bal: float,
          pos: np.ndarray, avg: np.ndarray, px0: np.ndarray,
          attempt_start: pd.Timestamp, today: pd.Timestamp,
          quantize: bool, margin_cap: Optional[float]):
    c = dict(cfg)
    c["quantize"] = quantize
    c["margin_cap"] = margin_cap
    M = _stub(attempt_start, today)
    WT = np.array([[0.0, 0.0], [float(wt_row[0]), float(wt_row[1])]])
    ON = np.array([0.0, float(on_flag)])
    tgt, opened = E._target_for_segment(
        s_idx, 1, M, WT, ON, c, bal, pos.copy(), avg.copy(), px0, 0, c["vm"])
    return tgt, opened


def preview(phase: str, wt_row, on_day: bool, bal: float, pos_usd: np.ndarray,
            avg_px: np.ndarray, px_now: np.ndarray,
            attempt_start: pd.Timestamp, today: pd.Timestamp) -> Dict:
    """Cibles 22:05 (s=4) et 17:35 GER40 (s=3) + composants du gouverneur.

    pos_usd/avg_px/px_now : vecteurs ordonnés LEGS = [XAUUSD, USDJPY, US100, GER40].
    Cibles en USD notionnel signé, version sim-quantisée ET pré-quantisation.
    """
    cfg = phase_cfg(phase)
    on = 1.0 if on_day else 0.0
    args = (bal, pos_usd, avg_px, px_now, attempt_start, today)

    tgt_q, opened = _call(4, cfg, wt_row, on, *args, quantize=True,
                          margin_cap=cfg.get("margin_cap"))
    tgt_raw, _ = _call(4, cfg, wt_row, on, *args, quantize=False, margin_cap=None)
    tgt_on_q = None
    if on_day:
        tgt_on_q, _ = _call(3, cfg, wt_row, on, *args, quantize=True,
                            margin_cap=cfg.get("margin_cap"))

    eq = bal + E._mtm(pos_usd, avg_px, px_now)
    scale_full = _probe_scale(cfg, *args)
    scale_taper = _probe_scale({**cfg, "glide": 1.0, "pace": 0}, *args)
    scale_glide = _probe_scale({**cfg, "pace": 0}, *args)
    vm = cfg["vm"]
    out = dict(
        phase=phase, eq_used=eq, bal_used=bal,
        targets_usd_quantized={l: float(tgt_q[k]) for k, l in enumerate(LEGS)},
        targets_usd_raw={l: float(tgt_raw[k]) for k, l in enumerate(LEGS)},
        opened_flag=bool(opened),
        governor=dict(
            vm=vm,
            taper=float(scale_taper / vm) if vm else 0.0,
            glide=float(scale_glide / scale_taper) if scale_taper else 1.0,
            pace=float(scale_full / scale_glide) if scale_glide else 1.0,
            scale=float(scale_full),
        ),
    )
    if tgt_on_q is not None:
        out["ger40_1735_usd_quantized"] = float(tgt_on_q[3])
    return out


def _probe_scale(cfg: dict, bal, pos, avg, px0, attempt_start, today) -> float:
    """scale = vm*taper*glide*pace, extrait par appel-sonde (poids unité, sans cap)."""
    eq = bal + E._mtm(pos, avg, px0)
    if eq <= 0:
        return 0.0
    tgt, _ = _call(4, cfg, (1.0, 0.0), 0.0, bal, pos, avg, px0,
                   attempt_start, today, quantize=False, margin_cap=None)
    return float(tgt[0] / eq)
