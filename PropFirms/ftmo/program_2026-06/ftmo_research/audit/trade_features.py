"""
trade_features.py — Per-trade dataset extraction with pre-entry features.

For each ORB trade across the 3-sleeve core, compute features known
AT OR-CLOSE (i.e. strictly before entry), plus the realised R + outcome.

NOTE: M1 panels for US100/GER40 do NOT include volume. We use TWAP (time-weighted
average price) instead of VWAP, and skip "volume during OR" entirely.

Timezone: data is in EET (broker server time, UTC+2/3 — verified by the volume
spike at 16:30 = US cash open).

Returns a DataFrame with columns:
  - date, symbol, sleeve, day_of_week
  - or_high, or_low, or_range, or_range_atr_ratio
  - gap, gap_pct, gap_dir
  - twap_or, breakout_level, breakout_dir
  - dist_twap_at_break_R  (signed; >0 means break in direction of TWAP→break)
  - time_to_break_5min   (in 5-min bars, 0 = entered immediately at OR close)
  - or_touches            (count of times the SAME-side border was retested during OR)
  - or_vol_5m_std         (std of 5-min returns during OR)
  - dist_to_pdh_R         (signed in R units; breakout_level - prior_day_high)
  - dist_to_pdl_R         (signed in R units; breakout_level - prior_day_low)
  - overnight_range_ratio (today's open-to-OR-close range / prior overnight range)
  - prior_day_return      (prior day intra-session close-to-close return)
  - r_realised, outcome   (PASS_TGT, STOP, TIME_STOP — TIME_STOP = close-the-day exit)
"""
from __future__ import annotations
from pathlib import Path
from functools import lru_cache
from typing import Iterable
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1].parent / "panels" / "m5_indices"

# Cost in INDEX POINTS (round-trip)
COST_POINTS = {"US100": 3.0, "GER40": 1.5}

# 3 sleeves of the core:  (sleeve_name, symbol, open_h_EET, open_m_EET, close_h_EET, or_bars_5m)
SLEEVES = [
    ("US100_1630_30m", "US100", 16, 30, 23, 6),  # 30-min OR @ US cash open
    ("GER40_1630_15m", "GER40", 16, 30, 22, 3),  # 15-min OR @ Europe reacts to US
    ("GER40_1000_30m", "GER40", 10,  0, 18, 6),  # 30-min OR @ DAX open
]


@lru_cache(maxsize=8)
def _load_m5(symbol: str) -> pd.DataFrame:
    if symbol in ("US100", "US500", "US30", "US2000"):
        df = pd.read_parquet(DATA / "m1_panel.parquet")[symbol].dropna()
    else:
        df = pd.read_parquet(DATA / f"{symbol}_m1_panel.parquet")
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df[["open", "high", "low", "close"]].dropna()
    return df.resample("5min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()


def _compute_daily_atr(df_session: pd.DataFrame, days: int = 20) -> pd.Series:
    """Per-date series of ATR using prior `days` session ranges (exclusive of today)."""
    daily_hi = df_session["high"].resample("D").max()
    daily_lo = df_session["low"].resample("D").min()
    daily_range = (daily_hi - daily_lo).dropna()
    atr = daily_range.rolling(days).mean().shift(1)  # info ≤ J-1
    return atr


def _compute_prior_close(symbol: str, oh: int, om: int, ch: int) -> pd.Series:
    """Last close before today's open at the session level. Date-indexed."""
    df = _load_m5(symbol)
    # session close = last bar before close_h
    h, m = df.index.hour, df.index.minute
    sess = df[((h > oh) | ((h == oh) & (m >= om))) & (h < ch)].copy()
    sess["day"] = sess.index.date
    daily_close = sess.groupby("day")["close"].last()
    daily_close.index = pd.to_datetime(daily_close.index)
    return daily_close


def _compute_prior_day_hl(symbol: str, oh: int, om: int, ch: int) -> tuple[pd.Series, pd.Series]:
    """Prior day session high and low. Indexed by date (today)."""
    df = _load_m5(symbol)
    h, m = df.index.hour, df.index.minute
    sess = df[((h > oh) | ((h == oh) & (m >= om))) & (h < ch)].copy()
    sess["day"] = sess.index.date
    daily_h = sess.groupby("day")["high"].max()
    daily_l = sess.groupby("day")["low"].min()
    daily_h.index = pd.to_datetime(daily_h.index)
    daily_l.index = pd.to_datetime(daily_l.index)
    # Shift to use as PRIOR day H/L for today
    return daily_h.shift(1), daily_l.shift(1)


def _compute_prior_day_return(symbol: str, oh: int, om: int, ch: int) -> pd.Series:
    """Prior day session close-to-close return. Indexed by today's date."""
    daily_close = _compute_prior_close(symbol, oh, om, ch)
    # shift twice: today's "prior day close" is yesterday's, but we want yesterday's
    # daily return = today_close / prev_close - 1, then shift back to today's date
    ret = daily_close / daily_close.shift(1) - 1
    return ret.shift(1)  # today's "prior day return" = yesterday's session return


def extract_trades_for_sleeve(sleeve_name: str, symbol: str,
                              oh: int, om: int, ch: int, or_bars: int,
                              cost_mult: float = 1.0,
                              slip_R: float = 0.0) -> pd.DataFrame:
    """Build the per-trade dataset for one sleeve."""
    df = _load_m5(symbol)
    h, m = df.index.hour, df.index.minute
    sess = df[((h > oh) | ((h == oh) & (m >= om))) & (h < ch)].copy()
    sess["day"] = sess.index.date

    atr = _compute_daily_atr(sess, days=20)
    prior_close = _compute_prior_close(symbol, oh, om, ch)
    pdh, pdl = _compute_prior_day_hl(symbol, oh, om, ch)
    prior_day_ret = _compute_prior_day_return(symbol, oh, om, ch)

    cost = COST_POINTS[symbol] * cost_mult

    rows = []
    for day, g in sess.groupby("day"):
        day_ts = pd.Timestamp(day)
        H, L, C, O = g["high"].values, g["low"].values, g["close"].values, g["open"].values
        if len(H) < or_bars + 3:
            continue
        # OR
        or_hi = H[:or_bars].max()
        or_lo = L[:or_bars].min()
        or_range = or_hi - or_lo
        if or_range <= 0:
            continue
        risk = or_range
        # TWAP during OR (time-weighted avg)
        twap_or = ((H[:or_bars] + L[:or_bars] + C[:or_bars]) / 3).mean()

        # Find breakout
        up = np.where(H[or_bars:] > or_hi)[0]
        dn = np.where(L[or_bars:] < or_lo)[0]
        iu = up[0] if len(up) else 10**9
        idn = dn[0] if len(dn) else 10**9
        if iu == idn == 10**9:
            continue
        if iu <= idn:
            direction, level, stop_level = 1, or_hi, or_lo
            bi = or_bars + iu
        else:
            direction, level, stop_level = -1, or_lo, or_hi
            bi = or_bars + idn

        # Compute features at OR close (post or_bars but pre entry)
        # 1. OR width
        atr_today = atr.get(pd.Timestamp(day), np.nan)
        or_range_atr_ratio = or_range / atr_today if (atr_today and atr_today > 0) else np.nan

        # 2. Gap
        prev_close_val = prior_close.get(pd.Timestamp(day) - pd.Timedelta(days=1), np.nan)
        # Try multiple lookbacks for weekend/holidays
        if pd.isna(prev_close_val):
            for back in range(1, 6):
                v = prior_close.get(pd.Timestamp(day) - pd.Timedelta(days=back), np.nan)
                if not pd.isna(v):
                    prev_close_val = v
                    break
        gap = O[0] - prev_close_val if not pd.isna(prev_close_val) else np.nan
        gap_pct = gap / prev_close_val if not pd.isna(gap) and prev_close_val else np.nan
        gap_dir = np.sign(gap) if not pd.isna(gap) else np.nan

        # 3. Breakout features
        # dist_twap_at_break_R: signed in R units
        # >0 if break is "in concordance" with twap drift (break up & twap < level) or (break down & twap > level)
        # easier: signed twap distance from level, normalized by risk
        twap_diff = (level - twap_or) / risk
        dist_twap_at_break_R = twap_diff * direction  # positive = breakout in concordance with twap-drift

        # 4. Time-to-break in 5-min bars (0 = broke immediately after OR)
        time_to_break = (iu if iu < 10**9 else idn) - 0  # bars after OR close
        if time_to_break < 0:
            time_to_break = 0

        # 5. OR touches: count touches of the breakout-side border BEFORE the break
        if direction == 1:
            touches = int((H[:bi] >= or_hi - 0.001).sum())  # count bars where high touched or_hi
        else:
            touches = int((L[:bi] <= or_lo + 0.001).sum())

        # 6. Realised vol during OR: std of 5-min returns
        if or_bars >= 2:
            or_rets = pd.Series(C[:or_bars]).pct_change().dropna()
            or_vol_5m_std = float(or_rets.std()) if len(or_rets) > 0 else np.nan
        else:
            or_vol_5m_std = np.nan

        # 7. Distance to PDH/PDL (in R units, signed)
        pdh_val = pdh.get(pd.Timestamp(day), np.nan)
        pdl_val = pdl.get(pd.Timestamp(day), np.nan)
        if not pd.isna(pdh_val):
            dist_to_pdh_R = (level - pdh_val) / risk * direction
        else:
            dist_to_pdh_R = np.nan
        if not pd.isna(pdl_val):
            dist_to_pdl_R = (level - pdl_val) / risk * direction
        else:
            dist_to_pdl_R = np.nan

        # 8. Overnight range ratio: today's open-to-OR-close range / prior overnight range
        if not pd.isna(prev_close_val):
            overnight_pre_close = abs(O[0] - prev_close_val)
            overnight_range_ratio = or_range / overnight_pre_close if overnight_pre_close > 0 else np.nan
        else:
            overnight_range_ratio = np.nan

        # 9. Prior day return
        pdr = prior_day_ret.get(pd.Timestamp(day), np.nan)

        # 10. Day of week (0=Mon, 4=Fri)
        dow = day_ts.dayofweek

        # 11. Direction concordance with overnight gap
        gap_concord = float(direction == gap_dir) if not pd.isna(gap_dir) and gap_dir != 0 else np.nan
        prior_day_concord = float(direction == np.sign(pdr)) if not pd.isna(pdr) and pdr != 0 else np.nan

        # === Compute exit (with slippage option) ===
        slip_pts = slip_R * risk
        entry = level + direction * slip_pts
        stop_eff = stop_level - direction * slip_pts

        fh, fl = H[bi:], L[bi:]
        if direction == 1:
            hit = np.where(fl <= stop_eff)[0]
        else:
            hit = np.where(fh >= stop_eff)[0]
        if len(hit):
            exit_px = stop_eff
            outcome = "STOP"
            time_to_exit = int(hit[0])
        else:
            exit_px = C[-1]
            outcome = "TIME_STOP"
            time_to_exit = len(fh) - 1
        r_realised = (direction * (exit_px - entry) - cost) / risk

        rows.append({
            "date": day_ts,
            "symbol": symbol,
            "sleeve": sleeve_name,
            "day_of_week": dow,
            "or_high": or_hi,
            "or_low": or_lo,
            "or_range": or_range,
            "or_range_atr_ratio": or_range_atr_ratio,
            "gap_abs": gap,
            "gap_pct": gap_pct,
            "gap_dir": gap_dir,
            "twap_or": twap_or,
            "breakout_level": level,
            "breakout_dir": direction,
            "dist_twap_at_break_R": dist_twap_at_break_R,
            "time_to_break_5min": time_to_break,
            "or_touches": touches,
            "or_vol_5m_std": or_vol_5m_std,
            "dist_to_pdh_R": dist_to_pdh_R,
            "dist_to_pdl_R": dist_to_pdl_R,
            "overnight_range_ratio": overnight_range_ratio,
            "prior_day_return": pdr,
            "gap_concord": gap_concord,
            "prior_day_concord": prior_day_concord,
            "r_realised": r_realised,
            "outcome": outcome,
            "time_to_exit": time_to_exit,
            "or_bars_used": or_bars,
        })
    return pd.DataFrame(rows).set_index("date")


def extract_all_trades(lo: str = "2022", hi: str = "2025",
                        cost_mult: float = 1.0, slip_R: float = 0.0) -> pd.DataFrame:
    parts = []
    for sleeve_name, symbol, oh, om, ch, or_bars in SLEEVES:
        df = extract_trades_for_sleeve(sleeve_name, symbol, oh, om, ch, or_bars,
                                       cost_mult=cost_mult, slip_R=slip_R)
        df = df.loc[lo:hi]
        parts.append(df)
    out = pd.concat(parts).sort_index()
    return out


if __name__ == "__main__":
    print("Extracting all trades 2022-2025...")
    df = extract_all_trades(lo="2022", hi="2025")
    print(f"Total trades: {len(df)}")
    print(f"By sleeve:")
    print(df.groupby("sleeve").size())
    print()
    print("Mean R by sleeve:")
    print(df.groupby("sleeve")["r_realised"].agg(["mean", "std", "count"]))
    print()
    print("Outcome distribution:")
    print(df["outcome"].value_counts())
    print()
    print("R distribution overall:")
    print(df["r_realised"].describe())
    print()
    print("Feature availability (% non-null):")
    feat_cols = ["or_range_atr_ratio", "gap_abs", "gap_pct", "dist_twap_at_break_R",
                  "time_to_break_5min", "or_touches", "or_vol_5m_std",
                  "dist_to_pdh_R", "dist_to_pdl_R", "overnight_range_ratio",
                  "prior_day_return", "gap_concord", "prior_day_concord"]
    for c in feat_cols:
        if c in df.columns:
            pct = (df[c].notna().sum() / len(df)) * 100
            print(f"  {c:25s}: {pct:.1f}%")
    df.to_parquet("trade_dataset.parquet")
    print(f"\nSaved -> trade_dataset.parquet ({len(df)} rows)")
