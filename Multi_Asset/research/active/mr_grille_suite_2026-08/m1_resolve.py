"""
Minimal M1 (1-minute) exit resolver for Axis A (wider symmetric brackets) and Axis B
(trailing stops) of mr_grille_suite_2026-08. `audit_moteur_bracket_2026-08/` (the
dedicated resolver project referenced in the mandate) does not exist in this repo at
freeze time (checked by path and by repo-wide filename search) — this module is a
scoped, from-scratch build for exactly the two axes that need it here.

Design (frozen in PREREGISTRATION.md §2): entry direction/distance is decided on
15-min bars (unchanged conditioner machinery); only the EXIT walk is resolved on the
session-filtered 1-min series, starting at the exact entry minute, for up to W
minutes. Same-minute ties (both barriers touched in the identical 1-min bar) are
still resolved stop-first, for consistency with the shared engine's convention —
the point of M1 resolution is to shrink the FREQUENCY of ties, not to change the
tie-break rule.

Fully vectorised across all candidate trades at once via a strided sliding-window
view (no per-trade Python loop, no per-minute Python loop).
"""
from __future__ import annotations
import numpy as np


def _windows(arr: np.ndarray, W: int) -> np.ndarray:
    """Strided (view, not copy) rolling windows of length W: row i = arr[i:i+W]."""
    n = arr.size
    if n < W:
        return np.empty((0, W), dtype=arr.dtype)
    return np.lib.stride_tricks.sliding_window_view(arr, W)


def resolve_bracket_batch(entry_idx: np.ndarray, direction: np.ndarray,
                          sl_dist: np.ndarray, tp_dist: np.ndarray,
                          o1: np.ndarray, h1: np.ndarray, l1: np.ndarray, c1: np.ndarray,
                          W: int):
    """
    entry_idx: int array, row position in the 1-min arrays where the trade enters
      (its OWN bar's open is the fill price — mirrors the shared engine's `h[e:end+1]`
      convention of including the entry bar itself in the barrier search).
    direction: +1/-1 array, same length.
    sl_dist/tp_dist: positive price-distance arrays, same length (already computed
      on 15-min bars at signal time, in the same price units as the 1-min series).
    Returns dict of arrays: exit_idx, exit_px, reason ('sl'/'tp'/'time'), valid (bool).
    """
    n = len(entry_idx)
    valid = entry_idx + W <= len(h1)
    ei = entry_idx.copy()
    ei[~valid] = 0  # dummy, masked out at the end

    entry_px = o1[ei]
    win_h = _windows(h1, W)
    win_l = _windows(l1, W)
    hh = win_h[ei]   # (n, W) — materialised copy via fancy indexing
    ll = win_l[ei]

    is_long = direction > 0
    sl_px = np.where(is_long, entry_px - sl_dist, entry_px + sl_dist)
    tp_px = np.where(is_long, entry_px + tp_dist, entry_px - tp_dist)

    sl_mask = np.where(is_long[:, None], ll <= sl_px[:, None], hh >= sl_px[:, None])
    tp_mask = np.where(is_long[:, None], hh >= tp_px[:, None], ll <= tp_px[:, None])

    sl_hit = sl_mask.any(axis=1); tp_hit = tp_mask.any(axis=1)
    sl_off = np.where(sl_hit, sl_mask.argmax(axis=1), W)
    tp_off = np.where(tp_hit, tp_mask.argmax(axis=1), W)

    both_miss = (~sl_hit) & (~tp_hit)
    pick_sl = sl_off <= tp_off  # tie -> sl (pessimistic), matches shared-engine convention

    exit_offset = np.where(both_miss, W - 1, np.minimum(sl_off, tp_off))
    exit_idx = ei + exit_offset
    reason = np.where(both_miss, "time", np.where(pick_sl, "sl", "tp"))
    exit_px = np.select([~both_miss & pick_sl, ~both_miss & ~pick_sl, both_miss],
                        [sl_px, tp_px, c1[np.clip(exit_idx, 0, len(c1) - 1)]])

    return dict(exit_idx=exit_idx, exit_px=exit_px, reason=reason, valid=valid,
               entry_px=entry_px)


def resolve_bracket_one(idx1: int, direction: float, sl_dist: float, tp_dist: float,
                        o1: np.ndarray, h1: np.ndarray, l1: np.ndarray, c1: np.ndarray, W: int):
    """Scalar (single-trade) counterpart of resolve_bracket_batch, used inside the
    sequential one-position-at-a-time loop in the run_axis_* scripts — a plain W-length
    slice is cheaper than a stride-view + single-row fancy index for n=1 at a time."""
    if idx1 + W > len(h1):
        return None
    entry_px = o1[idx1]
    hh = h1[idx1:idx1 + W]; ll = l1[idx1:idx1 + W]
    if direction > 0:
        sl_px = entry_px - sl_dist; tp_px = entry_px + tp_dist
        sl_mask = ll <= sl_px; tp_mask = hh >= tp_px
    else:
        sl_px = entry_px + sl_dist; tp_px = entry_px - tp_dist
        sl_mask = hh >= sl_px; tp_mask = ll <= tp_px
    sl_off = int(np.argmax(sl_mask)) if sl_mask.any() else W
    tp_off = int(np.argmax(tp_mask)) if tp_mask.any() else W
    if sl_off == W and tp_off == W:
        return dict(exit_idx=idx1 + W - 1, exit_px=float(c1[idx1 + W - 1]), reason="time",
                   entry_px=float(entry_px))
    if sl_off <= tp_off:  # tie -> sl, pessimistic (matches shared-engine convention)
        return dict(exit_idx=idx1 + sl_off, exit_px=float(sl_px), reason="sl", entry_px=float(entry_px))
    return dict(exit_idx=idx1 + tp_off, exit_px=float(tp_px), reason="tp", entry_px=float(entry_px))


def resolve_trailing_one(idx1: int, direction: float, trail_dist: float,
                         o1: np.ndarray, h1: np.ndarray, l1: np.ndarray, c1: np.ndarray, W: int):
    if idx1 + W > len(h1):
        return None
    entry_px = o1[idx1]
    hh = h1[idx1:idx1 + W]; ll = l1[idx1:idx1 + W]
    if direction > 0:
        hwm = np.maximum.accumulate(hh)
        trail = np.maximum(entry_px - trail_dist, hwm - trail_dist)
        hit_mask = ll <= trail
    else:
        lwm = np.minimum.accumulate(ll)
        trail = np.minimum(entry_px + trail_dist, lwm + trail_dist)
        hit_mask = hh >= trail
    if hit_mask.any():
        off = int(np.argmax(hit_mask))
        return dict(exit_idx=idx1 + off, exit_px=float(trail[off]), reason="trail",
                   entry_px=float(entry_px))
    return dict(exit_idx=idx1 + W - 1, exit_px=float(c1[idx1 + W - 1]), reason="time",
               entry_px=float(entry_px))


def resolve_trailing_batch(entry_idx: np.ndarray, direction: np.ndarray, trail_dist: np.ndarray,
                           o1: np.ndarray, h1: np.ndarray, l1: np.ndarray, c1: np.ndarray, W: int):
    """Plain ATR-trailing stop, no fixed take-profit: stop starts at entry -/+ trail_dist,
    trails favourably only (never loosens), using the running high (long) / low (short)
    of the M1 path. Time-stop at the close of the W-th minute if never touched."""
    n = len(entry_idx)
    valid = entry_idx + W <= len(h1)
    ei = entry_idx.copy()
    ei[~valid] = 0

    entry_px = o1[ei]
    win_h = _windows(h1, W)
    win_l = _windows(l1, W)
    hh = win_h[ei]
    ll = win_l[ei]

    is_long = direction > 0
    hwm = np.maximum.accumulate(hh, axis=1)          # running high, inclusive of entry bar
    lwm = np.minimum.accumulate(ll, axis=1)          # running low

    trail_long = np.maximum(entry_px[:, None] - trail_dist[:, None], hwm - trail_dist[:, None])
    trail_short = np.minimum(entry_px[:, None] + trail_dist[:, None], lwm + trail_dist[:, None])
    trail_level = np.where(is_long[:, None], trail_long, trail_short)

    hit_mask = np.where(is_long[:, None], ll <= trail_level, hh >= trail_level)
    hit = hit_mask.any(axis=1)
    off = np.where(hit, hit_mask.argmax(axis=1), W - 1)
    rows = np.arange(n)
    exit_idx = ei + off
    stop_px = trail_level[rows, off]
    exit_px = np.where(hit, stop_px, c1[np.clip(exit_idx, 0, len(c1) - 1)])
    reason = np.where(hit, "trail", "time")

    return dict(exit_idx=exit_idx, exit_px=exit_px, reason=reason, valid=valid, entry_px=entry_px)
