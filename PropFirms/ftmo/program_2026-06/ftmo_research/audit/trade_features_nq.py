"""
trade_features_nq.py — Per-trade dataset extraction on CLEAN NQ futures data.

Phase 1 audit context:
- Original `trade_features.py` had a look-ahead bug at line 180
  (`time_to_break_5min` used `iu` for short trades, which is observed
  AFTER the trade trigger `idn`).
- This builder is the corrected reference implementation, on the clean
  Databento NQ 2010-2026 dataset.
- Each feature is computed point-in-time (≤ entry bar) and direction-symmetric
  where applicable.
- `time_to_break_buggy` is kept in parallel to allow reproducing the bug for
  audit purposes. `time_to_break_5min` is the corrected version.

Execution:
- Default: next-bar-open (clean). The orb_core.py default of same-bar fill at
  level is optimistic; we evaluate on clean exec.
- Cost: ~1.0 point RT (= 4 ticks MNQ ~$2.15 at Tradovate).
- Risk: 1R = OR range (high - low of the opening window).

Sleeve:
- NQ @ 09:30 ET, 30-min OR (6 5-min bars), exit at 16:00 ET (RTH close).

Outputs:
- `trade_dataset_nq.parquet` — full dataset with all features.
- Console summary.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[2]  # = .../Algo_claude/data
NQ_PARQUET = DATA_ROOT / "raw" / "NQ_1min_databento_2010-2026.parquet"

# Cost in INDEX POINTS (round-trip).  4 ticks * 0.25 pts = 1.0 RT.
COST_POINTS_NQ = 1.0

# Sleeve config: NQ cash open 09:30 ET, 30-min OR, RTH close 16:00 ET.
OPEN_H_ET, OPEN_M_ET = 9, 30
CLOSE_H_ET = 16
OR_BARS_5M = 6


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_nq_5min() -> pd.DataFrame:
    """Load NQ 1-min databento, skip roll days, convert to ET tz-naive, resample 5-min.

    Returns OHLCV at 5-min granularity, ET wall-clock index.
    """
    df = pd.read_parquet(NQ_PARQUET, columns=["open", "high", "low", "close",
                                                "volume", "is_roll_day"])
    # Skip roll days entirely
    df = df[~df["is_roll_day"]].drop(columns="is_roll_day")
    # tz: UTC -> ET, then drop tz for downstream date-arithmetic
    df.index = df.index.tz_convert("US/Eastern").tz_localize(None)
    df = df.sort_index()
    df5 = df.resample("5min").agg(
        {"open": "first", "high": "max", "low": "min",
         "close": "last", "volume": "sum"}
    ).dropna()
    return df5


# ---------------------------------------------------------------------------
# Daily-level prior helpers (point-in-time = shift(1))
# ---------------------------------------------------------------------------

def _session_daily(df_session: pd.DataFrame) -> pd.DataFrame:
    """Daily aggregates of the session (RTH window applied).

    Returns DataFrame indexed by date with columns: high, low, close, volume.
    """
    g = df_session.copy()
    g["day"] = g.index.normalize()
    out = g.groupby("day").agg(high=("high", "max"),
                                low=("low", "min"),
                                close=("close", "last"),
                                volume=("volume", "sum"))
    return out


def _build_prior_features(df_session: pd.DataFrame) -> pd.DataFrame:
    """Compute prior-day H/L/Close/return, indexed by today's date.

    All values are PRIOR — i.e. usable strictly before today's open.
    """
    d = _session_daily(df_session)
    out = pd.DataFrame(index=d.index)
    out["pdh"] = d["high"].shift(1)
    out["pdl"] = d["low"].shift(1)
    out["prev_close"] = d["close"].shift(1)
    out["prev_volume"] = d["volume"].shift(1)
    # prior day return: yesterday's session return = close_t-1 / close_t-2 - 1
    daily_ret = d["close"] / d["close"].shift(1) - 1
    out["prior_day_return"] = daily_ret.shift(1)
    # 20-day prior ATR (session range), shifted
    daily_range = (d["high"] - d["low"]).shift(1)  # prior day's range
    out["atr20"] = daily_range.rolling(20).mean().shift(0)  # rolling already includes shift(1) effect
    # Wait — atr should use last 20 prior days, not 19+today.  Reconstruct:
    out["atr20"] = (d["high"] - d["low"]).rolling(20).mean().shift(1)
    # prior-day volume rolling median (for or_vol_ratio normalisation)
    out["vol_median_20"] = d["volume"].rolling(20).median().shift(1)
    return out


# ---------------------------------------------------------------------------
# Per-trade extraction
# ---------------------------------------------------------------------------

def extract_trades_nq(or_bars: int = OR_BARS_5M,
                       open_h: int = OPEN_H_ET,
                       open_m: int = OPEN_M_ET,
                       close_h: int = CLOSE_H_ET,
                       cost_mult: float = 1.0,
                       slip_R: float = 0.0,
                       lo: str | None = "2010",
                       hi: str | None = "2026") -> pd.DataFrame:
    """Build per-trade dataset for NQ ORB.

    For each session:
      - identify OR window (or_bars 5-min bars starting at open_h:open_m)
      - identify first break (long if iu<=idn, short otherwise)
      - record entry / exit / R under TWO execution models:
          - EXEC_LEVEL : same-bar fill at break level (optimistic, legacy)
          - EXEC_NEXTOPEN : next-bar-open after break (clean)
      - record features known at OR-close + at break (point-in-time)
      - record `time_to_break_buggy` (=iu/idn-confused as in legacy) for audit
    """
    df5 = load_nq_5min()
    h, m = df5.index.hour, df5.index.minute
    # Session window: from open_h:open_m to close_h:00 ET (close_h exclusive)
    sess = df5[((h > open_h) | ((h == open_h) & (m >= open_m))) & (h < close_h)].copy()
    sess["day"] = sess.index.normalize()

    prior = _build_prior_features(sess)
    cost = COST_POINTS_NQ * cost_mult

    rows = []
    for day, g in sess.groupby("day"):
        H = g["high"].values.astype(np.float64)
        L = g["low"].values.astype(np.float64)
        C = g["close"].values.astype(np.float64)
        O = g["open"].values.astype(np.float64)
        V = g["volume"].values.astype(np.float64)
        if len(H) < or_bars + 3:
            continue

        # === Opening Range (OR), bars 0..or_bars-1 ===
        or_hi = H[:or_bars].max()
        or_lo = L[:or_bars].min()
        or_range = or_hi - or_lo
        if or_range <= 0:
            continue
        risk = or_range

        # OR-close descriptors (future-blind)
        twap_or = ((H[:or_bars] + L[:or_bars] + C[:or_bars]) / 3).mean()
        or_vol_total = V[:or_bars].sum()
        or_v = V[:or_bars]
        or_c = C[:or_bars]
        # True VWAP during OR = sum(close * vol) / sum(vol)
        vwap_or_true = float((or_c * or_v).sum() / or_v.sum()) if or_v.sum() > 0 else float(np.nan)
        # OR volume skew: where did volume cluster within OR price range?
        # midpoint = (or_hi + or_lo)/2; ratio = vol in upper half - vol in lower half
        or_mid = (or_hi + or_lo) / 2
        bar_mids = (H[:or_bars] + L[:or_bars]) / 2
        upper_mask = bar_mids > or_mid
        lower_mask = ~upper_mask
        upper_vol = or_v[upper_mask].sum()
        lower_vol = or_v[lower_mask].sum()
        if upper_vol + lower_vol > 0:
            or_vol_skew = (upper_vol - lower_vol) / (upper_vol + lower_vol)
        else:
            or_vol_skew = float(np.nan)
        # OR realized vol std (5-min returns)
        if or_bars >= 2:
            or_rets = pd.Series(C[:or_bars]).pct_change().dropna()
            or_vol_5m_std = float(or_rets.std()) if len(or_rets) > 0 else float(np.nan)
        else:
            or_vol_5m_std = float(np.nan)

        # === Break detection ===
        up = np.where(H[or_bars:] > or_hi)[0]
        dn = np.where(L[or_bars:] < or_lo)[0]
        iu = up[0] if len(up) else 10**9
        idn = dn[0] if len(dn) else 10**9
        if iu == idn == 10**9:
            continue
        if iu <= idn:
            direction = 1
            level = or_hi
            stop_level = or_lo
            bi = or_bars + iu
        else:
            direction = -1
            level = or_lo
            stop_level = or_hi
            bi = or_bars + idn

        # === time_to_break ===
        # CORRECT: bi - or_bars = real trigger bar offset (iu for long, idn for short)
        time_to_break_5min = bi - or_bars
        # BUGGY (legacy line 180): always picks iu if available — look-ahead for shorts
        time_to_break_buggy = iu if iu < 10**9 else idn

        # === OR-touches (counted strictly before bi) ===
        if direction == 1:
            touches = int((H[:bi] >= or_hi - 1e-6).sum())
        else:
            touches = int((L[:bi] <= or_lo + 1e-6).sum())

        # === Distance to TWAP / VWAP at break (signed, R-units, symmetric) ===
        dist_twap_at_break_R = ((level - twap_or) / risk) * direction
        dist_vwap_at_break_R = ((level - vwap_or_true) / risk) * direction if not np.isnan(vwap_or_true) else float(np.nan)

        # === Prior day distances ===
        day_ts = pd.Timestamp(day)
        pdh_val = prior["pdh"].get(day_ts, np.nan)
        pdl_val = prior["pdl"].get(day_ts, np.nan)
        prev_close_val = prior["prev_close"].get(day_ts, np.nan)
        prev_volume_val = prior["prev_volume"].get(day_ts, np.nan)
        pdr = prior["prior_day_return"].get(day_ts, np.nan)
        atr20 = prior["atr20"].get(day_ts, np.nan)
        vol_med_20 = prior["vol_median_20"].get(day_ts, np.nan)

        dist_to_pdh_R = ((level - pdh_val) / risk) * direction if not pd.isna(pdh_val) else float(np.nan)
        dist_to_pdl_R = ((level - pdl_val) / risk) * direction if not pd.isna(pdl_val) else float(np.nan)
        or_range_atr_ratio = or_range / atr20 if (not pd.isna(atr20) and atr20 > 0) else float(np.nan)
        or_vol_ratio_20d = or_vol_total / vol_med_20 if (not pd.isna(vol_med_20) and vol_med_20 > 0) else float(np.nan)

        # === Gap ===
        if not pd.isna(prev_close_val):
            gap_abs = O[0] - prev_close_val
            gap_pct = gap_abs / prev_close_val if prev_close_val else float(np.nan)
            gap_dir = float(np.sign(gap_abs))
            overnight_pre_close = abs(O[0] - prev_close_val)
            overnight_range_ratio = or_range / overnight_pre_close if overnight_pre_close > 0 else float(np.nan)
        else:
            gap_abs = gap_pct = gap_dir = overnight_range_ratio = float(np.nan)

        # === Concordance (direction-conditional, future-blind in inputs) ===
        gap_concord = float(direction == gap_dir) if not pd.isna(gap_dir) and gap_dir != 0 else float(np.nan)
        prior_day_concord = float(direction == np.sign(pdr)) if not pd.isna(pdr) and pdr != 0 else float(np.nan)
        # OR volume concordance: positive if vol clustered on breakout side
        or_vol_concord = or_vol_skew * direction if not np.isnan(or_vol_skew) else float(np.nan)

        # === Pre-break activity (bars or_bars .. bi-1) ===
        # NB: bi > or_bars by construction (break occurs at index bi, bi-1 is the
        # last closed bar before break detection).
        pre_break_slice_v = V[or_bars:bi] if bi > or_bars else np.array([])
        pre_break_slice_h = H[or_bars:bi] if bi > or_bars else np.array([])
        pre_break_slice_l = L[or_bars:bi] if bi > or_bars else np.array([])
        if len(pre_break_slice_v):
            vol_pre_break = float(pre_break_slice_v.sum())
            pre_break_range = float(pre_break_slice_h.max() - pre_break_slice_l.min())
        else:
            vol_pre_break = 0.0
            pre_break_range = 0.0

        # === Exit / R under TWO execution models ===
        slip_pts = slip_R * risk

        # --- EXEC_LEVEL: legacy same-bar fill at level ---
        entry_L = level + direction * slip_pts
        stop_eff_L = stop_level - direction * slip_pts
        fh_L, fl_L = H[bi:], L[bi:]
        if direction == 1:
            hit_L = np.where(fl_L <= stop_eff_L)[0]
        else:
            hit_L = np.where(fh_L >= stop_eff_L)[0]
        if len(hit_L):
            exit_L = stop_eff_L
            outcome_L = "STOP"
            time_to_exit_L = int(hit_L[0])
        else:
            exit_L = C[-1]
            outcome_L = "TIME_STOP"
            time_to_exit_L = len(fh_L) - 1
        r_exec_level = (direction * (exit_L - entry_L) - cost) / risk

        # --- EXEC_NEXTOPEN: enter at next bar's open after break ---
        if bi + 1 < len(g):
            entry_N = float(O[bi + 1]) + direction * slip_pts
            stop_eff_N = stop_level - direction * slip_pts
            fh_N = H[bi + 1:]
            fl_N = L[bi + 1:]
            if direction == 1:
                hit_N = np.where(fl_N <= stop_eff_N)[0]
            else:
                hit_N = np.where(fh_N >= stop_eff_N)[0]
            if len(hit_N):
                exit_N = stop_eff_N
                outcome_N = "STOP"
                time_to_exit_N = int(hit_N[0])
            else:
                exit_N = float(C[-1])
                outcome_N = "TIME_STOP"
                time_to_exit_N = len(fh_N) - 1
            r_exec_nextopen = (direction * (exit_N - entry_N) - cost) / risk
        else:
            r_exec_nextopen = float(np.nan)
            outcome_N = "NO_ENTRY"
            time_to_exit_N = 0
            entry_N = float(np.nan)
            exit_N = float(np.nan)

        rows.append({
            "date": day_ts,
            "symbol": "NQ",
            "sleeve": "NQ_0930_30m",
            "day_of_week": day_ts.dayofweek,
            "or_high": or_hi,
            "or_low": or_lo,
            "or_range": or_range,
            "or_range_atr_ratio": or_range_atr_ratio,
            "or_vol_5m_std": or_vol_5m_std,
            "or_vol_total": or_vol_total,
            "or_vol_ratio_20d": or_vol_ratio_20d,
            "or_vol_skew": or_vol_skew,        # range-bounded [-1, +1], direction-independent
            "or_vol_concord": or_vol_concord,   # = or_vol_skew * direction
            "twap_or": twap_or,
            "vwap_or_true": vwap_or_true,
            "gap_abs": gap_abs,
            "gap_pct": gap_pct,
            "gap_dir": gap_dir,
            "gap_concord": gap_concord,
            "breakout_level": level,
            "breakout_dir": direction,
            "dist_twap_at_break_R": dist_twap_at_break_R,
            "dist_vwap_at_break_R": dist_vwap_at_break_R,
            "time_to_break_5min": time_to_break_5min,   # CORRECT
            "time_to_break_buggy": time_to_break_buggy,  # LEGACY (look-ahead)
            "or_touches": touches,
            "dist_to_pdh_R": dist_to_pdh_R,
            "dist_to_pdl_R": dist_to_pdl_R,
            "overnight_range_ratio": overnight_range_ratio,
            "prior_day_return": pdr,
            "prior_day_concord": prior_day_concord,
            "vol_pre_break": vol_pre_break,
            "pre_break_range_R": pre_break_range / risk if risk > 0 else float(np.nan),
            "r_exec_level": r_exec_level,         # legacy same-bar
            "r_exec_nextopen": r_exec_nextopen,   # clean
            "outcome_level": outcome_L,
            "outcome_nextopen": outcome_N,
            "time_to_exit_level": time_to_exit_L,
            "time_to_exit_nextopen": time_to_exit_N,
            "entry_level": float(level),
            "entry_nextopen": float(entry_N),
            "or_bars_used": or_bars,
            "iu_raw": iu if iu < 10**9 else -1,
            "idn_raw": idn if idn < 10**9 else -1,
            "bi_raw": bi,
        })
    out = pd.DataFrame(rows).set_index("date")
    if lo or hi:
        out = out.loc[lo:hi]
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Loading NQ 5-min...")
    df = extract_trades_nq()
    print(f"Total trades: {len(df)}")
    print(f"Date range: {df.index.min()} -> {df.index.max()}")
    print()
    print("Direction balance:")
    print(df["breakout_dir"].value_counts().to_string())
    print()
    print("Mean R baseline (EXEC_LEVEL vs EXEC_NEXTOPEN):")
    print(df[["r_exec_level", "r_exec_nextopen"]].describe().round(4))
    print()
    print("Mean R by direction (EXEC_NEXTOPEN):")
    print(df.groupby("breakout_dir")["r_exec_nextopen"].mean().round(4))
    print()
    print("== ttb sanity ==")
    print(f"  ttb_correct vs ttb_buggy mismatch: {(df['time_to_break_5min'] != df['time_to_break_buggy']).sum()} trades")
    print(f"  Of those, by direction: {df[df['time_to_break_5min'] != df['time_to_break_buggy']]['breakout_dir'].value_counts().to_dict()}")
    print()
    print("Feature availability (% non-null):")
    feat_cols = ["or_range_atr_ratio", "gap_abs", "gap_pct",
                 "dist_twap_at_break_R", "dist_vwap_at_break_R",
                 "time_to_break_5min", "time_to_break_buggy",
                 "or_touches", "or_vol_5m_std",
                 "or_vol_total", "or_vol_ratio_20d", "or_vol_skew", "or_vol_concord",
                 "dist_to_pdh_R", "dist_to_pdl_R", "overnight_range_ratio",
                 "prior_day_return", "gap_concord", "prior_day_concord",
                 "vol_pre_break", "pre_break_range_R"]
    for c in feat_cols:
        if c in df.columns:
            pct = (df[c].notna().sum() / len(df)) * 100
            print(f"  {c:25s}: {pct:.1f}%")
    out_path = Path(__file__).resolve().parent / "trade_dataset_nq.parquet"
    df.to_parquet(out_path)
    print(f"\nSaved -> {out_path} ({len(df)} rows)")
