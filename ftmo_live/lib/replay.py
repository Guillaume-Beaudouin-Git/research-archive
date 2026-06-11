"""Replay modèle d'UNE journée live — composition des atomes du sim.

Politique (cibles, quantize, margin cap) = E._target_for_segment via
governor._call ; comptabilité = E._trade_to/_flat/_mtm ; segments = E.SCHED_MIN ;
coûts = ancres RT yaml (half-RT sur |Δnotional|, sémantique sim) ; micro-ORB =
miroir V2+E7 (invariants). Même pattern que engine_v22.run_phase (boucle re-
dérivée, atomes importés — précédent v2.2/j1_engine).

Sert reconcile.py : Δ = réel − modèle, décomposé signal/coût/timing/micro/swap.
"""
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import engine as E  # cleanroom

from . import LEGS
from . import governor, invariants as inv
from . import spec as S

US100_USD_PER_PT_PER_LOT = 1.0  # mqh: risk 0.01 lot x OR_range pts (~$1/pt/lot)


def _rt_vec() -> np.ndarray:
    a = S.rt_anchors_allin_bps()      # v2.2.1: spread + commissions mesurées
    return np.array([a[l] for l in LEGS], float)


def _m5_matrix(m5: Dict[str, List[Tuple[str, float]]]) -> Tuple[np.ndarray, List[int]]:
    """(matrice closes [T,4], minutes Paris) sur l'union des horodatages."""
    series = {}
    for l in LEGS:
        rows = m5.get(l, [])
        idx = [int(t[:2]) * 60 + int(t[3:5]) for t, _ in rows]
        series[l] = pd.Series([float(v) for _, v in rows], index=idx)
    minutes = sorted(set().union(*[set(s.index) for s in series.values()])) or [0]
    px = np.full((len(minutes), 4), np.nan)
    for k, l in enumerate(LEGS):
        if len(series[l]):
            px[:, k] = series[l].reindex(minutes).ffill().to_numpy(float)
    return px, minutes


def replay_day(date: pd.Timestamp, phase: str, attempt_start: pd.Timestamp,
               sod_balance: float, sod_pos_usd: np.ndarray, sod_avg: np.ndarray,
               weights: Tuple[float, float], on_day: bool,
               m5_paris: Dict[str, list], micro_enabled: Optional[bool] = None) -> dict:
    """Rejoue la journée `date` aux prix M5 et à la politique v2.2. Retourne
    balance/equity EOD modèle (mark 22:55), trades par segment, micro, breaker."""
    cfg = governor.phase_cfg(phase)
    init = S.account_size()
    rt = _rt_vec()
    px, minutes = _m5_matrix(m5_paris)
    bounds = [int(np.searchsorted(minutes, t, side="left")) for t in E.SCHED_MIN]
    cuts = [0] + bounds + [len(minutes)]

    bal = float(sod_balance)
    pos = sod_pos_usd.astype(float).copy()
    avg = sod_avg.astype(float).copy()
    lim = inv.lim_eff(bal, init)
    brk = inv.breaker_line(bal, cfg["breaker"], init)
    tgt_eq = inv.target_equity(cfg["target"], init) if phase != "FUNDED" else np.inf
    micro_on = cfg.get("micro_orb", False) if micro_enabled is None else micro_enabled

    trades, events = [], []
    flat_today = False
    opened = bool(on_day)                       # sémantique 605f4a4 (s=3 marque opened)
    micro = _micro_model(m5_paris.get("US100", []), micro_on, on_day)

    def seg_target(s_idx: int, px_row: np.ndarray):
        wt = (weights[0], weights[1])
        return governor._call(s_idx, cfg, wt, 1.0 if on_day else 0.0, bal, pos, avg,
                              px_row, attempt_start, date, quantize=True,
                              margin_cap=cfg.get("margin_cap"))

    for s in range(5):
        a, b = cuts[s], cuts[s + 1]
        if a >= b:
            continue
        seg = px[a:b]
        if s == 4 and micro["fired"] and not opened:
            bal += micro["pnl_usd"]
            opened = True
        if not flat_today:
            tgt = None
            if s == 1 and pos[3] != 0.0:
                tgt = pos.copy(); tgt[3] = 0.0
            elif s == 2 and pos[2] != 0.0:
                tgt = pos.copy(); tgt[2] = 0.0
            elif s == 3 and on_day:
                tgt, _ = seg_target(3, seg[0])
            elif s == 4:
                tgt, _ = seg_target(4, seg[0])
            if tgt is not None:
                pos_before = pos.copy()
                b2 = E._trade_to(pos, avg, bal, np.asarray(tgt, float), seg[0], rt)
                tgt_a = np.asarray(tgt, float)
                cost_model = float(np.nansum(np.where(
                    np.isfinite(seg[0]), np.abs(tgt_a - pos_before), 0.0) * rt / 2.0) / 1e4)
                trades.append(dict(seg=s, minute=minutes[a],
                                   tgt={l: float(tgt_a[k]) for k, l in enumerate(LEGS)},
                                   pos_before={l: float(pos_before[k])
                                               for k, l in enumerate(LEGS)},
                                   px={l: float(seg[0][k]) for k, l in enumerate(LEGS)},
                                   cost_model_usd=round(cost_model, 6),
                                   bal_delta=round(b2 - bal, 6)))
                bal = b2
        pl = np.zeros(len(seg))
        for k in range(4):
            if pos[k] != 0.0 and np.isfinite(avg[k]):
                col = seg[:, k]
                pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
        eq = bal + pl
        hb = eq < brk
        ht = eq >= tgt_eq
        tb = int(np.argmax(hb)) if hb.any() else len(seg)
        th = int(np.argmax(ht)) if ht.any() else len(seg)
        if min(tb, th) < len(seg):
            j = min(tb, th)
            bal = E._flat(pos, avg, bal, seg[j], rt)
            flat_today = True
            events.append(dict(kind="breaker" if tb <= th else "target_lock",
                               minute=minutes[a + j], eq=float(eq[j])))
    eod_px = px[-1]
    return dict(model_balance=bal, model_equity=bal + E._mtm(pos, avg, eod_px),
                model_pos_usd={l: float(pos[k]) for k, l in enumerate(LEGS)},
                trades=trades, events=events, micro=micro,
                lim_eff=lim, breaker_line=brk,
                eod_px={l: float(eod_px[k]) for k, l in enumerate(LEGS)})


def _micro_model(m5_us100: list, micro_on: bool, on_day: bool) -> dict:
    """Miroir V2+E7 sur le chemin M5 US100 du jour (closes ; hi/lo ≈ closes —
    granularité export ; le réel raffine, l'écart part en Δ_micro_exec)."""
    out = dict(armed=False, fired=False, pnl_usd=0.0)
    if not micro_on or on_day or len(m5_us100) < 10:
        return out
    closes = {int(t[:2]) * 60 + int(t[3:5]): float(v) for t, v in m5_us100}
    or_keys = [m for m in closes if E.SCHED_MIN[1] <= m < E.SCHED_MIN[1] + 30]
    post_keys = sorted(m for m in closes if E.SCHED_MIN[1] + 30 <= m <= 22 * 60)
    if len(or_keys) < 4 or len(post_keys) < 3:
        return out
    vals = [closes[m] for m in sorted(or_keys)]
    or_hi, or_lo = inv.or_levels(vals, vals)
    if not inv.v2_width_ok(or_hi, or_lo, vals[-1]):
        return out
    out["armed"] = True
    hh = [closes[m] for m in post_keys]
    brk = inv.orb_break(hh, hh, or_hi, or_lo)
    if brk is None:
        return out
    ex = inv.e7_exit(hh[brk["bar"]:], hh[brk["bar"]:], hh[brk["bar"]:],
                     brk["level"], brk["stop"], brk["direction"])
    lots = float(S.micro_orb()["size_lots"])
    pnl = (ex["exit_px"] - brk["level"]) * brk["direction"] * lots \
        * US100_USD_PER_PT_PER_LOT
    out.update(fired=True, pnl_usd=round(pnl, 4), or_hi=or_hi, or_lo=or_lo,
               direction=brk["direction"], entry=brk["level"], exit=ex)
    return out
