"""
step0_cost_calibration.py — FTMO MT5 EURUSD cost gate (the decisive pre-flight).

The point of Step 0 is to settle the cost question BEFORE running the backtest.
Fix-reversal entries cluster at session opens / post-fix / Asian thin hours where
the spread is structurally wider. So the per-entry expected cost is NOT the
unconditional median; it's the spread distribution evaluated INSIDE the trading
windows we actually use.

Outputs
-------
1. Unconditional spread distribution (anchor).
2. Conditional spread at:
   - Tokyo fix window  (00:55 UTC ± 5 min)        — JPY no DST
   - ECB fix window    (13:15 UTC ± 5 min winter, 12:15 ± 5 summer)
   - London fix window (16:00 UTC ± 5 min winter, 15:00 ± 5 summer)
   - Asian session     (00:00-07:00 UTC)          — thinnest liquidity
   - London open       (07:00-08:00 UTC)
   - NY  open          (13:00-14:00 UTC winter, 12:00-13:00 UTC summer)
3. Cost stack (bps RT) = spread + slippage (ATR-scaled) + commission ($5/lot/RT).
4. Persisted to step0_costs.json for the Step 1 backtest.

References
----------
- FTMO MT5 spread points → bps: 1 point = 1e-5 (EURUSD, 5 decimals).
- FTMO FX commission: $2.5 / lot / side = $5 RT (ftmo_specs.csv).
- Data: data/deep_history_utc/EURUSD_M1.csv (TRUE UTC, 2007-2026, calibrated spread).
  Migrated 2026-06-10 from m5_indices/EURUSD_M1.csv (EET mislabeled UTC) — see
  FIX_REVERSAL_TZ_MIGRATION.md. Pre-migration results: *.pre_tz_migration.*.
- Cost markup 1.0 (feed-raw) AND 2.0 (retail-vs-feed, L23b).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]
PANEL = REPO / "data/deep_history_utc/EURUSD_M1.csv"
OUTDIR = Path(__file__).resolve().parent

POINT = 1e-5                # EURUSD decimals=5
PIP = 1e-4
COMMISSION_USD_PER_LOT_RT = 5.0  # 2.5/side per ftmo_specs.csv
LOT_NOTIONAL_EUR = 100_000

# Fix windows (UTC). Tokyo no DST. ECB+London follow DST.
# For simplicity report both winter and summer side-by-side.
FIX_WINDOWS = {
    "Tokyo_09:55_JST":     ("00:50", "01:00"),                      # year-round
    "ECB_14:15_CET_winter":  ("13:10", "13:20"),
    "ECB_14:15_CEST_summer": ("12:10", "12:20"),
    "London_16:00_GMT":   ("15:55", "16:05"),                       # winter (GMT=UTC)
    "London_16:00_BST":   ("14:55", "15:05"),                       # summer (BST=UTC+1)
}
SESSION_WINDOWS = {
    "Asian_thin_00-07": ("00:00", "07:00"),
    "London_open_07-08": ("07:00", "08:00"),
    "NY_open_13-14_winter": ("13:00", "14:00"),
    "NY_open_12-13_summer": ("12:00", "13:00"),
}


def load_panel() -> pd.DataFrame:
    df = pd.read_csv(PANEL,
                     usecols=["timestamp_utc", "open", "high", "low", "close",
                              "spread"])
    df["ts"] = pd.to_datetime(df["timestamp_utc"],
                              format="%Y.%m.%d %H:%M:%S", errors="coerce")
    df = df.dropna(subset=["ts"]).set_index("ts").sort_index()
    df.index = df.index.tz_localize("UTC")
    df["spread"] = df["spread"].astype(int)
    return df


def is_dst_summer(ts: pd.DatetimeIndex) -> pd.Series:
    """Crude DST flag: April-October = summer (Europe DST window approx)."""
    return ts.month.isin([4, 5, 6, 7, 8, 9, 10])


def spread_stats(s: pd.Series, label: str, count_only_positive: bool = True) -> dict:
    sp = s[s > 0] if count_only_positive else s
    if len(sp) == 0:
        return {"label": label, "N": 0}
    px_median = 1.13  # EURUSD canonical mid
    out = {
        "label": label,
        "N": int(len(sp)),
        "med_pts": int(sp.median()),
        "p75_pts": int(sp.quantile(0.75)),
        "p90_pts": int(sp.quantile(0.90)),
        "p95_pts": int(sp.quantile(0.95)),
        "p99_pts": int(sp.quantile(0.99)),
    }
    for key, q in [("med", 0.50), ("p75", 0.75), ("p90", 0.90),
                   ("p95", 0.95), ("p99", 0.99)]:
        rt_bps = sp.quantile(q) * POINT / px_median * 1e4
        out[f"{key}_bps_RT"] = round(rt_bps, 3)
    return out


def filter_window(df: pd.DataFrame, start: str, end: str,
                  summer_only: bool = False, winter_only: bool = False) -> pd.DataFrame:
    """Return rows where intraday UTC time is in [start, end]."""
    h_start, m_start = map(int, start.split(":"))
    h_end,   m_end   = map(int, end.split(":"))
    minute_of_day = df.index.hour * 60 + df.index.minute
    start_min, end_min = h_start * 60 + m_start, h_end * 60 + m_end
    if end_min < start_min:
        in_win = (minute_of_day >= start_min) | (minute_of_day < end_min)
    else:
        in_win = (minute_of_day >= start_min) & (minute_of_day < end_min)
    if summer_only:
        in_win = in_win & is_dst_summer(df.index)
    if winter_only:
        in_win = in_win & (~is_dst_summer(df.index))
    return df.loc[in_win]


def atr_m1(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Simple M1 ATR over `window` bars."""
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"]  - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


def main() -> dict:
    df = load_panel()
    print(f"[load] {len(df):,} M1 bars | {df.index.min().date()} → "
          f"{df.index.max().date()}\n")

    out = {"meta": {"data_source": str(PANEL.relative_to(REPO)),
                    "first_bar": str(df.index.min()),
                    "last_bar":  str(df.index.max()),
                    "n_rows": int(len(df)),
                    "point_size_EURUSD": POINT,
                    "commission_usd_per_lot_RT": COMMISSION_USD_PER_LOT_RT,
                    "lot_notional_EUR": LOT_NOTIONAL_EUR,
                    "commission_bps_RT_at_1.13": round(
                        COMMISSION_USD_PER_LOT_RT
                        / (1.13 * LOT_NOTIONAL_EUR) * 1e4, 3)}}

    print(f"FTMO FX commission: ${COMMISSION_USD_PER_LOT_RT}/lot RT "
          f"= {out['meta']['commission_bps_RT_at_1.13']:.2f} bps RT (at 1.13)\n")

    # unconditional
    out["unconditional"] = spread_stats(df["spread"], "ALL_BARS")
    print(f"[ALL] {out['unconditional']}\n")

    # fix windows
    out["fix_windows"] = {}
    print("─ Fix windows (the entry moments — the user's gate) ─")
    for name, (s, e) in FIX_WINDOWS.items():
        summer = "summer" in name.lower()
        winter = "winter" in name.lower() or ("GMT" in name)
        slc = filter_window(df, s, e, summer_only=summer, winter_only=winter)
        st = spread_stats(slc["spread"], name)
        out["fix_windows"][name] = st
        print(f"  {name:35s} N={st['N']:>6,}  med={st['med_pts']:>3} pts "
              f"({st['med_bps_RT']:.2f} bps)  "
              f"p95={st['p95_pts']:>3} ({st['p95_bps_RT']:.2f} bps)  "
              f"p99={st['p99_pts']:>3} ({st['p99_bps_RT']:.2f} bps)")

    # session windows
    out["session_windows"] = {}
    print("\n─ Session windows ─")
    for name, (s, e) in SESSION_WINDOWS.items():
        summer = "summer" in name.lower()
        winter = "winter" in name.lower()
        slc = filter_window(df, s, e, summer_only=summer, winter_only=winter)
        st = spread_stats(slc["spread"], name)
        out["session_windows"][name] = st
        print(f"  {name:35s} N={st['N']:>6,}  med={st['med_pts']:>3} pts "
              f"({st['med_bps_RT']:.2f} bps)  "
              f"p95={st['p95_pts']:>3} ({st['p95_bps_RT']:.2f} bps)  "
              f"p99={st['p99_pts']:>3} ({st['p99_bps_RT']:.2f} bps)")

    # ATR-based slippage (worst case: 0.5×ATR M1 at fix windows)
    df["atr_m1"] = atr_m1(df, 20)
    london_fix = filter_window(df, "15:55", "16:05", winter_only=True)
    atr_lf = float(london_fix["atr_m1"].dropna().median())
    px_med = float(df["close"].median())
    slip_bps = 0.5 * atr_lf / px_med * 1e4
    out["slippage_atr_05x_londonfix_bps"] = round(slip_bps, 3)
    out["slippage_note"] = (
        "0.5 × median ATR_M1(20) inside London fix window, in bps. "
        "Used as adverse slippage stress for fix-entry strategies.")
    print(f"\n[slip] 0.5 × ATR_M1(20) median in London fix window = "
          f"{slip_bps:.2f} bps")

    # Final cost stacks — what the backtest will use
    p95_london = out["fix_windows"]["London_16:00_GMT"]["p95_bps_RT"]
    p95_tokyo  = out["fix_windows"]["Tokyo_09:55_JST"]["p95_bps_RT"]
    p95_ecb_w  = out["fix_windows"]["ECB_14:15_CET_winter"]["p95_bps_RT"]
    p95_asian  = out["session_windows"]["Asian_thin_00-07"]["p95_bps_RT"]
    comm = out["meta"]["commission_bps_RT_at_1.13"]
    out["cost_stack_RT_bps"] = {
        "London_fix_p95":  {"spread": p95_london, "comm": comm, "slip": round(slip_bps,2),
                            "total_markup1": round(p95_london + comm + slip_bps, 2),
                            "total_markup2": round(p95_london*2 + comm + slip_bps, 2)},
        "Tokyo_fix_p95":   {"spread": p95_tokyo,  "comm": comm, "slip": round(slip_bps,2),
                            "total_markup1": round(p95_tokyo + comm + slip_bps, 2),
                            "total_markup2": round(p95_tokyo*2 + comm + slip_bps, 2)},
        "ECB_fix_p95_winter": {"spread": p95_ecb_w, "comm": comm, "slip": round(slip_bps,2),
                            "total_markup1": round(p95_ecb_w + comm + slip_bps, 2),
                            "total_markup2": round(p95_ecb_w*2 + comm + slip_bps, 2)},
        "Asian_thin_p95":  {"spread": p95_asian,  "comm": comm, "slip": round(slip_bps,2),
                            "total_markup1": round(p95_asian + comm + slip_bps, 2),
                            "total_markup2": round(p95_asian*2 + comm + slip_bps, 2)},
    }

    print("\n─ Cost stack (bps RT) — what Step 1 backtest will charge ─")
    print(f"  {'window':25s} {'spread_p95':>11s} {'comm':>6s} {'slip':>6s} "
          f"{'tot×1':>7s} {'tot×2':>7s}")
    for k, v in out["cost_stack_RT_bps"].items():
        print(f"  {k:25s} {v['spread']:>11.2f} {v['comm']:>6.2f} {v['slip']:>6.2f} "
              f"{v['total_markup1']:>7.2f} {v['total_markup2']:>7.2f}")

    with open(OUTDIR / "step0_costs.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nsaved → {OUTDIR / 'step0_costs.json'}")
    return out


if __name__ == "__main__":
    main()
