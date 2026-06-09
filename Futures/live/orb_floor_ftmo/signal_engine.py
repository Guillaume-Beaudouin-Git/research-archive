"""
signal_engine.py — ORB V2+E7 signal generator for live US100 CFD execution.

V2 = OR width filter in %/ATR (NOT points-fixed, that was the instrument-price trap)
E7 = trail-to-breakeven after +1R (lock_R=0)
Time-stop = 12:30 ET (≈ 16:30 UTC DST / 17:30 UTC standard)

Signal flow:
  09:30 ET — US cash open. Mark OR start.
  09:45 ET — OR end. Compute or_hi, or_lo, or_range. Apply V2 filter.
              If V2 fails → no trade today.
  09:46+ ET — wait for first break (close above or_hi OR below or_lo).
  Entry: at next-bar open after CONFIRMED close-break (= delay-1 clean exec, L26).
  Initial SL: opposite side of OR (= 1R).
  Manage: when MFE ≥ +1R → move SL to entry (BE). Hold until time-stop or stop hit.
  Exit: at 12:30 ET if still open OR at stop fill.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import time, datetime, timezone


@dataclass
class V2FilterSpec:
    """V2: OR-width filter.

    min_pct: minimum OR range as fraction of price (e.g. 0.001 = 0.1% = 10 bps).
    min_atr_ratio: minimum OR range / ATR_20d ratio (e.g. 0.30).
    Use whichever is non-None (or both → AND).
    """
    min_pct: float | None = 0.001       # 10 bps of price floor (the "bps_10")
    min_atr_ratio: float | None = None  # alternative: OR / ATR_20d


@dataclass
class E7ExitSpec:
    """E7: trail to breakeven."""
    trigger_R: float = 1.0  # at +1R, ratchet stop to entry
    lock_R: float = 0.0     # lock to BE (= entry)
    time_stop_et: time = time(12, 30)  # 12:30 ET


@dataclass
class ORState:
    """The OR data computed at OR-end (09:45 ET)."""
    date: datetime
    or_hi: float
    or_lo: float
    or_range: float        # absolute pts
    or_range_pct: float    # fraction of OR mid-price
    atr_20d: float | None  # 20-day ATR (in pts), for V2 ratio
    or_range_atr_ratio: float | None  # OR range / ATR_20d
    or_mid: float          # midpoint price (= reference for V2 %)


def is_v2_pass(state: ORState, spec: V2FilterSpec) -> tuple[bool, str]:
    """Check V2 filter. Returns (pass, reason)."""
    reasons = []
    if spec.min_pct is not None:
        if state.or_range_pct < spec.min_pct:
            return False, f"OR width {state.or_range_pct*1e4:.1f}bps < V2 threshold {spec.min_pct*1e4:.1f}bps"
        reasons.append(f"V2_pct OK ({state.or_range_pct*1e4:.1f}bps)")
    if spec.min_atr_ratio is not None and state.or_range_atr_ratio is not None:
        if state.or_range_atr_ratio < spec.min_atr_ratio:
            return False, f"OR/ATR {state.or_range_atr_ratio:.2f} < V2 threshold {spec.min_atr_ratio:.2f}"
        reasons.append(f"V2_atr OK ({state.or_range_atr_ratio:.2f})")
    return True, " + ".join(reasons) if reasons else "no V2 filter active"


@dataclass
class Trade:
    """Live trade state."""
    date: datetime
    direction: int  # 1 = long, -1 = short
    entry_px: float
    entry_time: datetime
    initial_sl: float
    risk_R: float    # or_range
    target_be_px: float | None = None  # entry + direction × trigger_R × risk
    current_sl: float = 0.0
    moved_to_BE: bool = False
    exit_px: float | None = None
    exit_time: datetime | None = None
    exit_reason: str = ""
    r_realised: float | None = None


def open_trade(state: ORState, direction: int, entry_px: float,
                entry_time: datetime, exit_spec: E7ExitSpec) -> Trade:
    """Open a new ORB trade after a confirmed break."""
    risk_R = state.or_range
    sl = state.or_lo if direction == 1 else state.or_hi
    target_be = entry_px + direction * exit_spec.trigger_R * risk_R
    return Trade(
        date=state.date,
        direction=direction,
        entry_px=entry_px,
        entry_time=entry_time,
        initial_sl=sl,
        risk_R=risk_R,
        target_be_px=target_be,
        current_sl=sl,
    )


def update_trade(t: Trade, current_high: float, current_low: float,
                  current_close: float, now: datetime,
                  exit_spec: E7ExitSpec) -> dict:
    """
    Per-bar update. Returns:
      - status: "open" / "stopped" / "time_stop"
      - new_sl: updated stop level (may be unchanged)
      - exit_action: None / "close_at_stop" / "close_at_market"
    """
    direction = t.direction

    # Check stop hit
    if direction == 1:
        if current_low <= t.current_sl:
            t.exit_px = t.current_sl
            t.exit_time = now
            t.exit_reason = "stop" if not t.moved_to_BE else "stop_BE"
            t.r_realised = direction * (t.exit_px - t.entry_px) / t.risk_R
            return {"status": "stopped", "trade": t}
    else:
        if current_high >= t.current_sl:
            t.exit_px = t.current_sl
            t.exit_time = now
            t.exit_reason = "stop" if not t.moved_to_BE else "stop_BE"
            t.r_realised = direction * (t.exit_px - t.entry_px) / t.risk_R
            return {"status": "stopped", "trade": t}

    # Check trail-to-BE trigger
    if not t.moved_to_BE:
        if direction == 1:
            if current_high >= t.target_be_px:
                t.current_sl = t.entry_px  # BE
                t.moved_to_BE = True
        else:
            if current_low <= t.target_be_px:
                t.current_sl = t.entry_px
                t.moved_to_BE = True

    # Time stop
    now_et_hour = (now.hour - 5) % 24  # naive UTC→ET (DST: -4, std: -5)
    now_et_time = time(now_et_hour, now.minute)
    if now_et_time >= exit_spec.time_stop_et:
        t.exit_px = current_close
        t.exit_time = now
        t.exit_reason = "time_stop"
        t.r_realised = direction * (t.exit_px - t.entry_px) / t.risk_R
        return {"status": "time_stop", "trade": t}

    return {"status": "open", "trade": t}


def compute_or_state(bars_09_30_to_09_45: list[dict], atr_20d: float | None,
                      date: datetime) -> ORState:
    """
    Given list of 1-min bars covering 09:30:00 to 09:45:00 ET, compute the OR.
    Each bar dict: {"high": float, "low": float, "close": float, "open": float}
    """
    if not bars_09_30_to_09_45:
        return None
    or_hi = max(b["high"] for b in bars_09_30_to_09_45)
    or_lo = min(b["low"] for b in bars_09_30_to_09_45)
    or_range = or_hi - or_lo
    or_mid = (or_hi + or_lo) / 2
    or_range_pct = or_range / or_mid if or_mid > 0 else 0
    or_range_atr_ratio = or_range / atr_20d if atr_20d and atr_20d > 0 else None
    return ORState(
        date=date,
        or_hi=or_hi, or_lo=or_lo, or_range=or_range, or_mid=or_mid,
        or_range_pct=or_range_pct, atr_20d=atr_20d,
        or_range_atr_ratio=or_range_atr_ratio,
    )


def check_breakout(close_now: float, or_hi: float, or_lo: float) -> int | None:
    """After OR ends and a bar closes, return 1 (up break), -1 (down break), or None."""
    if close_now > or_hi:
        return 1
    if close_now < or_lo:
        return -1
    return None


if __name__ == "__main__":
    # Sanity demo
    from datetime import datetime
    print("=" * 80)
    print("Signal engine sanity — synthetic day")
    print("=" * 80)
    # Synthetic 15 × 1-min bars 09:30:00 → 09:44:00 ET
    bars = [
        {"high": 25010, "low": 24995, "close": 25005, "open": 25000},
        {"high": 25020, "low": 25000, "close": 25015, "open": 25005},
        {"high": 25025, "low": 25008, "close": 25018, "open": 25015},
        {"high": 25030, "low": 25012, "close": 25022, "open": 25018},
        {"high": 25030, "low": 25015, "close": 25024, "open": 25022},
    ] + [{"high": 25030, "low": 25010, "close": 25020, "open": 25020}] * 10
    state = compute_or_state(bars, atr_20d=200.0, date=datetime(2026, 6, 2))
    print(f"OR computed: hi={state.or_hi}, lo={state.or_lo}, range={state.or_range}, "
          f"mid={state.or_mid}, range_pct={state.or_range_pct*1e4:.1f}bps")
    print(f"OR/ATR ratio: {state.or_range_atr_ratio:.3f}")

    v2 = V2FilterSpec(min_pct=0.001)
    passes, why = is_v2_pass(state, v2)
    print(f"V2 check (min 10bps): {'PASS' if passes else 'FAIL'} — {why}")

    e7 = E7ExitSpec()
    if passes:
        # Simulate a break at 09:46 close=25032 → direction=1
        bk = check_breakout(25032, state.or_hi, state.or_lo)
        print(f"Break direction: {bk}")
        if bk:
            # Entry at next-bar open say 25033
            t = open_trade(state, direction=bk, entry_px=25033,
                            entry_time=datetime(2026, 6, 2, 13, 47),
                            exit_spec=e7)
            print(f"Opened trade: dir={t.direction}, entry={t.entry_px}, "
                  f"SL={t.current_sl}, target_BE={t.target_be_px}")
            # Simulate price rallying past BE target
            res = update_trade(t, current_high=25067, current_low=25033, current_close=25060,
                                now=datetime(2026, 6, 2, 14, 30), exit_spec=e7)
            print(f"After +1R rally: moved_to_BE={t.moved_to_BE}, SL={t.current_sl}, "
                  f"status={res['status']}")
            # Simulate time-stop at 12:30 ET ≈ 16:30 UTC DST → use 17:30 UTC
            res = update_trade(t, current_high=25080, current_low=25060, current_close=25075,
                                now=datetime(2026, 6, 2, 16, 30), exit_spec=e7)
            print(f"At 12:30 ET: status={res['status']}, exit_px={t.exit_px}, "
                  f"r_realised={t.r_realised:.2f}, reason={t.exit_reason}")
