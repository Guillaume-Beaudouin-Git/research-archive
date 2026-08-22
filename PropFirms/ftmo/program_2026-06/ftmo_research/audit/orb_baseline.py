"""
orb_baseline.py — 30-min ORB baseline trade builder (multi-index, cost in bps).

Design (per Fil 1 ORB-deepening mission):
  - Universe: indices for FTMO/propfirm (CFD or futures)
      * NQ : Databento NQ_1min_databento_2010-2026.parquet (UTC, raw front-month)
      * US100/US500/US30/US2000: m1_panel.parquet (CFD, broker EET → convert to ET)
      * GER40: GER40_m1_panel.parquet (broker EET → convert to ET, but cash open is 09:00 CET)
  - OR window: 30 minutes from cash-open ET
  - Direction: first break of OR-high (long) or OR-low (short)
  - Stop = opposite side of OR (= 1R, OR range)
  - Exit = at RTH cash close (16:00 ET for US, 17:30 ET for DAX, etc.)
  - Execution: same-bar fill at level (= resting stop, validated realistic per
    OPTIM_execution_realism.md — gap-through ~0% at 1-min)
  - Cost in bps of entry price (NOT fixed points) — the v3 artifact corrected.
    Default: 1.0 bp RT (realistic for retail NQ futures; CFD ~1.5-3 bps).

Outputs per trade:
  - date, symbol, direction, entry_px, exit_px, exit_reason
  - r_realised (= directional return in R units, net of cost)
  - or_high, or_low, or_range (in price points), or_range_bps
  - exit_px_close (for exit-at-close)
  - And alternative exits stored for later (TP@1R, TP@2R, trailing markers)

Engine signature: build_orb_trades(symbol, params) → DataFrame, daily_R Series.
"""
from __future__ import annotations
from pathlib import Path
import datetime
import logging
from dataclasses import dataclass
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT.parents[1]
NQ_PARQUET = DATA_ROOT / "raw" / "NQ_1min_databento_2010-2026.parquet"
PANELS_DIR = DATA_ROOT / "panels" / "m5_indices"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sleeve / instrument metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Sleeve:
    symbol: str            # display
    source: str            # 'databento' | 'm1_panel' | 'ger40' | 'xauusd'
    cash_open_et: datetime.time
    cash_close_et: datetime.time
    or_minutes: int = 30
    # Note: cost is per-call; default chosen for class:
    cost_bps_rt: float = 1.0   # default 1 bp RT


SLEEVES = {
    "NQ":     Sleeve("NQ",    "databento", datetime.time(9, 30),  datetime.time(15, 59), 30, cost_bps_rt=1.0),
    "US100":  Sleeve("US100", "m1_panel",  datetime.time(9, 30),  datetime.time(15, 59), 30, cost_bps_rt=2.0),
    "US500":  Sleeve("US500", "m1_panel",  datetime.time(9, 30),  datetime.time(15, 59), 30, cost_bps_rt=2.0),
    "US30":   Sleeve("US30",  "m1_panel",  datetime.time(9, 30),  datetime.time(15, 59), 30, cost_bps_rt=2.0),
    "US2000": Sleeve("US2000","m1_panel",  datetime.time(9, 30),  datetime.time(15, 59), 30, cost_bps_rt=3.0),
    # DAX (GER40): cash open 09:00 CET = 03:00 ET (DST aware). Use CET wall-clock.
    "GER40":  Sleeve("GER40", "ger40",     datetime.time(9, 0),   datetime.time(17, 30), 30, cost_bps_rt=1.5),
}


# ---------------------------------------------------------------------------
# Data loaders (each returns tz-naive ET wall-clock 1-min OHLC[V])
# ---------------------------------------------------------------------------

def _load_nq() -> pd.DataFrame:
    """Databento NQ futures, UTC → US/Eastern tz-naive, skip is_roll_day."""
    df = pd.read_parquet(NQ_PARQUET, columns=["open", "high", "low", "close",
                                                "volume", "is_roll_day", "is_rth"])
    df = df[~df["is_roll_day"]].drop(columns=["is_roll_day"])
    df.index = df.index.tz_convert("US/Eastern").tz_localize(None)
    # Keep RTH only
    df = df[df["is_rth"]].drop(columns=["is_rth"])
    return df.sort_index()


def _load_m1_panel_symbol(symbol: str) -> pd.DataFrame:
    """m1_panel.parquet is broker EET wall-clock (Europe/Athens) labelled as
    timestamp_utc — bug per CLAUDE.md. We localize EET, then convert to ET tz-naive.
    Cash session window applied by caller.
    """
    panel = pd.read_parquet(PANELS_DIR / "m1_panel.parquet")
    if symbol not in panel.columns.get_level_values(0):
        raise KeyError(f"{symbol} not in m1_panel")
    df = panel[symbol].dropna(how="all").copy()
    df.index = pd.DatetimeIndex(df.index)
    # Treat as Europe/Athens, then convert to US/Eastern, drop tz
    df.index = df.index.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="shift_forward")
    df.index = df.index.tz_convert("US/Eastern").tz_localize(None)
    df = df.sort_index()
    # m1_panel doesn't have volume → set to NaN-like (we won't use volume in baseline)
    df["volume"] = 0
    return df[["open", "high", "low", "close", "volume"]]


def _load_ger40() -> pd.DataFrame:
    """GER40_m1_panel.parquet — broker EET wall-clock per CLAUDE.md convention."""
    df = pd.read_parquet(PANELS_DIR / "GER40_m1_panel.parquet")
    df.index = pd.DatetimeIndex(df.index)
    # Localize EET, convert to Europe/Berlin (since DAX cash hours are CET) — then tz-naive CET
    df.index = df.index.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="shift_forward")
    df.index = df.index.tz_convert("Europe/Berlin").tz_localize(None)
    df = df.sort_index()
    df["volume"] = 0
    return df[["open", "high", "low", "close", "volume"]]


_INSTRUMENT_CACHE: dict[str, pd.DataFrame] = {}


def load_instrument(sleeve: Sleeve) -> pd.DataFrame:
    """Load + tz-convert 1-min OHLCV for a sleeve. Module-level cached."""
    key = f"{sleeve.source}:{sleeve.symbol}"
    if key in _INSTRUMENT_CACHE:
        return _INSTRUMENT_CACHE[key]
    if sleeve.source == "databento":
        df = _load_nq()
    elif sleeve.source == "m1_panel":
        df = _load_m1_panel_symbol(sleeve.symbol)
    elif sleeve.source == "ger40":
        df = _load_ger40()
    else:
        raise ValueError(f"Unknown sleeve source: {sleeve.source}")
    _INSTRUMENT_CACHE[key] = df
    return df


# ---------------------------------------------------------------------------
# Exit logic
# ---------------------------------------------------------------------------

ExitSpec = dict   # {'kind': 'at_close' | 'tp_R' | 'scale_out' | 'trailing' | 'time_stop', ...}


def _run_exit(direction: int, entry_px: float, sl_px: float, tp_px: float | None,
              fh: np.ndarray, fl: np.ndarray, fc: np.ndarray,
              exit_spec: ExitSpec, risk: float) -> tuple[float, str, int]:
    """Walk 1-min bars from entry until exit. SL has same-bar priority over TP.

    Returns (exit_price, exit_reason, bars_held).
    """
    kind = exit_spec.get("kind", "at_close")
    n = len(fh)
    if n == 0:
        return entry_px, "NO_BARS", 0

    if kind == "at_close":
        # Walk until SL hit or last bar
        for i in range(n):
            if direction == 1:
                if fl[i] <= sl_px:
                    return sl_px, "SL", i + 1
            else:
                if fh[i] >= sl_px:
                    return sl_px, "SL", i + 1
        return float(fc[-1]), "CLOSE", n

    if kind == "tp_R":
        # Fixed TP at R-multiple
        for i in range(n):
            if direction == 1:
                if fl[i] <= sl_px:
                    return sl_px, "SL", i + 1
                if fh[i] >= tp_px:
                    return tp_px, "TP", i + 1
            else:
                if fh[i] >= sl_px:
                    return sl_px, "SL", i + 1
                if fl[i] <= tp_px:
                    return tp_px, "TP", i + 1
        return float(fc[-1]), "CLOSE", n

    if kind == "scale_out":
        # Take half at partial_tp_R, run rest to close (with SL still active for the runner)
        scale_R = exit_spec.get("partial_tp_R", 1.0)
        scale_frac = exit_spec.get("partial_frac", 0.5)
        scale_px = entry_px + direction * scale_R * risk
        scaled = False
        scaled_pnl_R = 0.0
        for i in range(n):
            if direction == 1:
                if fl[i] <= sl_px:
                    # SL hit. If we scaled, the realised pnl = scale_frac * scale_R + (1-scale_frac) * (-1)
                    if scaled:
                        # exit_price is composite — we report blended
                        full_pnl_R = scale_frac * scale_R + (1 - scale_frac) * (-1.0)
                        eff_exit_px = entry_px + direction * full_pnl_R * risk
                        return eff_exit_px, "SCALE+SL", i + 1
                    return sl_px, "SL", i + 1
                if not scaled and fh[i] >= scale_px:
                    scaled = True
                    scaled_pnl_R = scale_frac * scale_R
            else:
                if fh[i] >= sl_px:
                    if scaled:
                        full_pnl_R = scale_frac * scale_R + (1 - scale_frac) * (-1.0)
                        eff_exit_px = entry_px + direction * full_pnl_R * risk
                        return eff_exit_px, "SCALE+SL", i + 1
                    return sl_px, "SL", i + 1
                if not scaled and fl[i] <= scale_px:
                    scaled = True
                    scaled_pnl_R = scale_frac * scale_R
        # Reached close
        close_px = float(fc[-1])
        if scaled:
            close_R = direction * (close_px - entry_px) / risk
            full_pnl_R = scale_frac * scale_R + (1 - scale_frac) * close_R
            eff_exit_px = entry_px + direction * full_pnl_R * risk
            return eff_exit_px, "SCALE+CLOSE", n
        return close_px, "CLOSE", n

    if kind == "trailing":
        # Trail SL to entry once profit reaches trigger_R; then trail by trail_R fraction of R
        trigger_R = exit_spec.get("trigger_R", 1.0)
        lock_R = exit_spec.get("lock_R", 0.0)  # 0 = lock at entry (breakeven)
        activated = False
        for i in range(n):
            if direction == 1:
                # Update trailing if activated
                unrealized_R = (fh[i] - entry_px) / risk
                if not activated and unrealized_R >= trigger_R:
                    activated = True
                    new_sl = entry_px + direction * lock_R * risk
                    sl_px = max(sl_px, new_sl)
                # Check SL first then TP (none here)
                if fl[i] <= sl_px:
                    reason = "TRAIL_SL" if activated else "SL"
                    return sl_px, reason, i + 1
            else:
                unrealized_R = (entry_px - fl[i]) / risk
                if not activated and unrealized_R >= trigger_R:
                    activated = True
                    new_sl = entry_px + direction * lock_R * risk
                    sl_px = min(sl_px, new_sl)
                if fh[i] >= sl_px:
                    reason = "TRAIL_SL" if activated else "SL"
                    return sl_px, reason, i + 1
        return float(fc[-1]), "CLOSE", n

    if kind == "time_stop":
        # Exit at fixed time-of-day if no SL/TP hit before.
        n_bars_cap = exit_spec.get("n_bars", 180)  # default = 3h after entry
        for i in range(min(n, n_bars_cap)):
            if direction == 1:
                if fl[i] <= sl_px:
                    return sl_px, "SL", i + 1
            else:
                if fh[i] >= sl_px:
                    return sl_px, "SL", i + 1
        if n_bars_cap < n:
            return float(fc[n_bars_cap - 1]), "TIME_STOP", n_bars_cap
        return float(fc[-1]), "CLOSE", n

    raise ValueError(f"Unknown exit kind: {kind}")


# ---------------------------------------------------------------------------
# Build ORB trades on one instrument
# ---------------------------------------------------------------------------

def build_orb_trades(sleeve: Sleeve,
                      filter_spec: dict | None = None,
                      exit_spec: ExitSpec | None = None,
                      cost_bps_rt: float | None = None) -> pd.DataFrame:
    """Build per-day ORB trades for one instrument.

    filter_spec: optional pre-filter for OR range
      None or {} → no pre-filter
      {'kind': 'pts', 'min_pts': 30} → fixed pts threshold (legacy)
      {'kind': 'pct', 'min_pct': 0.002} → 0.2% of OR-close price
      {'kind': 'atr', 'min_mult': 1.0, 'atr_days': 20} → multiple of ATR20

    exit_spec: see _run_exit
      None / {'kind': 'at_close'} → exit at RTH close (baseline)
      others: TP@KR, scale_out, trailing, time_stop

    cost_bps_rt: override the sleeve default RT cost (in bps of entry price)
    """
    if filter_spec is None:
        filter_spec = {}
    if exit_spec is None:
        exit_spec = {"kind": "at_close"}
    if cost_bps_rt is None:
        cost_bps_rt = sleeve.cost_bps_rt

    log.info(f"  [{sleeve.symbol}] Loading instrument...")
    df = load_instrument(sleeve)

    # Filter to cash session [open, close)
    t = df.index.time
    s = sleeve.cash_open_et
    e = sleeve.cash_close_et
    df = df[(t >= s) & (t <= e)].copy()
    df["day"] = df.index.normalize()

    # Precompute daily ATR for adaptive filter (if needed)
    atr_series = None
    if filter_spec.get("kind") == "atr":
        days = int(filter_spec.get("atr_days", 20))
        daily_hi = df.groupby("day")["high"].max()
        daily_lo = df.groupby("day")["low"].min()
        daily_range = (daily_hi - daily_lo)
        atr_series = daily_range.rolling(days).mean().shift(1)

    rows = []
    for day, g in df.groupby("day"):
        H = g["high"].values.astype(np.float64)
        L = g["low"].values.astype(np.float64)
        C = g["close"].values.astype(np.float64)
        O = g["open"].values.astype(np.float64)
        if len(H) < sleeve.or_minutes + 30:
            continue
        # OR = first or_minutes 1-min bars
        OR = sleeve.or_minutes
        or_hi = H[:OR].max()
        or_lo = L[:OR].min()
        or_range = or_hi - or_lo
        if or_range <= 0:
            continue
        or_close_px = C[OR - 1]   # close of OR window

        # Apply filter
        skip = False
        fk = filter_spec.get("kind")
        if fk == "pts":
            if or_range < float(filter_spec.get("min_pts", 0)):
                skip = True
        elif fk == "pct":
            min_pct = float(filter_spec.get("min_pct", 0.0))
            if or_range / max(1e-9, or_close_px) < min_pct:
                skip = True
        elif fk == "atr":
            atr_val = atr_series.get(day, np.nan) if atr_series is not None else np.nan
            if pd.isna(atr_val) or atr_val <= 0:
                skip = True
            else:
                mult = float(filter_spec.get("min_mult", 0.0))
                if or_range / atr_val < mult:
                    skip = True
        if skip:
            continue

        # Find break
        up = np.where(H[OR:] > or_hi)[0]
        dn = np.where(L[OR:] < or_lo)[0]
        iu = up[0] if len(up) else 10**9
        idn = dn[0] if len(dn) else 10**9
        if iu == idn == 10**9:
            continue
        if iu <= idn:
            direction = 1
            level = or_hi
            stop_level = or_lo
            bi = OR + iu
        else:
            direction = -1
            level = or_lo
            stop_level = or_hi
            bi = OR + idn
        risk = or_range

        # Execution: same-bar fill at level (realistic per OPTIM_execution_realism)
        entry_px = float(level)
        sl_px = float(stop_level)
        # TP price for fixed-TP exits
        tp_R = exit_spec.get("tp_R", None)
        tp_px = entry_px + direction * tp_R * risk if tp_R is not None else None

        # Forward bars from bi (inclusive of bi for SL check — the break bar
        # itself could SL through the OR-other side after triggering, which is
        # rare but possible. We include bi.)
        # Actually for resting stop entered AT level on bi, the bar bi has
        # already moved past level; SL on the opposite side would only fire
        # if bi's range covers BOTH sides — extreme reversal in same bar.
        # Standard convention: walk bars from bi forward; first bar is bi itself
        # but only the part AFTER the trigger is relevant. For simplicity (same
        # as engine.py), include bi and check SL first.
        fh = H[bi:]
        fl = L[bi:]
        fc = C[bi:]
        exit_px, exit_reason, bars_held = _run_exit(direction, entry_px, sl_px,
                                                      tp_px, fh, fl, fc,
                                                      exit_spec, risk)

        # PnL in R units, net of cost. Cost expressed in bps of entry_px → in price units → in R units.
        cost_px = entry_px * (cost_bps_rt / 10000.0)
        r_realised = direction * (exit_px - entry_px) / risk - (cost_px / risk)

        rows.append({
            "date": pd.Timestamp(day),
            "symbol": sleeve.symbol,
            "direction": direction,
            "or_high": or_hi,
            "or_low": or_lo,
            "or_range": or_range,
            "or_range_bps": (or_range / or_close_px) * 10000,
            "or_close_px": or_close_px,
            "entry_px": entry_px,
            "exit_px": exit_px,
            "exit_reason": exit_reason,
            "bars_held": bars_held,
            "r_realised": r_realised,
            "cost_bps_rt": cost_bps_rt,
            "iu_offset": iu if iu < 10**9 else -1,
            "idn_offset": idn if idn < 10**9 else -1,
            "bi_offset": bi,
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.set_index("date")
    return out


def build_daily_R_series(trades: pd.DataFrame, freq: str = "B") -> pd.Series:
    """Convert trades to a daily R series indexed on business days.

    Days with no trade get NaN (which nq_sim treats as no PnL change).
    """
    if trades.empty:
        return pd.Series(dtype=float)
    r = trades["r_realised"]
    # collapse duplicate-day (shouldn't happen for single sleeve) by summing
    r = r.groupby(level=0).sum()
    all_dates = pd.bdate_range(r.index.min(), r.index.max(), freq=freq)
    return r.reindex(all_dates)


# ---------------------------------------------------------------------------
# CLI quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Quick build: NQ baseline 30-min ORB, exit-at-close, cost=1bp RT")
    tl_nq = build_orb_trades(SLEEVES["NQ"], filter_spec={},
                              exit_spec={"kind": "at_close"}, cost_bps_rt=1.0)
    print(f"  Trades: {len(tl_nq)} | {tl_nq.index.min()} -> {tl_nq.index.max()}")
    print(f"  Direction balance: {tl_nq['direction'].value_counts().to_dict()}")
    print(f"  Mean R (net 1bp): {tl_nq['r_realised'].mean():.4f}")
    print(f"  Std R: {tl_nq['r_realised'].std():.4f}")
    print(f"  Hit rate: {(tl_nq['r_realised'] > 0).mean()*100:.1f}%")
    print(f"  Exit reasons: {tl_nq['exit_reason'].value_counts().to_dict()}")
    print()
    print("OR range (bps of price):")
    print(tl_nq["or_range_bps"].describe().round(1).to_string())
    out_path = ROOT / "orb_baseline_nq_trades.parquet"
    tl_nq.to_parquet(out_path)
    print(f"\nSaved → {out_path}")
