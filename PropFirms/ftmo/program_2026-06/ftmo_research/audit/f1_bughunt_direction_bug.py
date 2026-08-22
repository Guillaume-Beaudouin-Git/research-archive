"""
f1_bughunt_direction_bug.py — Verify direction-misaligned ttb bug.

In trade_features.py line 180:
    time_to_break = (iu if iu < 10**9 else idn) - 0

For a SHORT trade (direction=-1, idn<iu), the trade trigger is `idn` (down-break time),
but the feature stores `iu` (UP-break time = LOOK-AHEAD).

For LONG trades, iu < idn so the feature stores iu = correct trigger time.

This script:
  1. Re-extracts trades with the CORRECTED ttb = bi - or_bars (= true trigger time).
  2. Compares F1 effect on (a) long-only with buggy ttb (= correct anyway),
     (b) long-only with corrected ttb (same as a),
     (c) short-only with buggy ttb (look-ahead),
     (d) short-only with CORRECTED ttb (no look-ahead),
     (e) all trades with buggy ttb,
     (f) all trades with corrected ttb.

  If F1 effect is mostly carried by short trades with buggy ttb → confirms the bug
  is the source of F1's spectacular edge.
"""
from __future__ import annotations
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd


DATA = Path(__file__).resolve().parents[1].parent / "panels" / "m5_indices"
COST_POINTS = {"US100": 3.0, "GER40": 1.5}
SLEEVES = [
    ("US100_1630_30m", "US100", 16, 30, 23, 6),
    ("GER40_1630_15m", "GER40", 16, 30, 22, 3),
    ("GER40_1000_30m", "GER40", 10,  0, 18, 6),
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


def extract_with_corrected_ttb(lo: str = "2022", hi: str = "2025") -> pd.DataFrame:
    """Re-extract trades with CORRECTED ttb (= bi - or_bars = true trigger bar index)."""
    parts = []
    for sleeve_name, symbol, oh, om, ch, or_bars in SLEEVES:
        df = _load_m5(symbol)
        h, m = df.index.hour, df.index.minute
        sess = df[((h > oh) | ((h == oh) & (m >= om))) & (h < ch)].copy()
        sess["day"] = sess.index.date
        cost = COST_POINTS[symbol]
        rows = []
        for day, g in sess.groupby("day"):
            H, L, C, O = g["high"].values, g["low"].values, g["close"].values, g["open"].values
            if len(H) < or_bars + 3:
                continue
            or_hi = H[:or_bars].max()
            or_lo = L[:or_bars].min()
            or_range = or_hi - or_lo
            if or_range <= 0:
                continue
            up = np.where(H[or_bars:] > or_hi)[0]
            dn = np.where(L[or_bars:] < or_lo)[0]
            iu = up[0] if len(up) else 10**9
            idn = dn[0] if len(dn) else 10**9
            if iu == idn == 10**9:
                continue
            if iu <= idn:
                direction, level, stop_level = 1, or_hi, or_lo
                bi = or_bars + iu
                # BUGGY ttb = iu (correct for long)
                ttb_buggy = iu
                # CORRECTED ttb = bi - or_bars (= iu for long, = idn for short)
                ttb_correct = bi - or_bars
            else:
                direction, level, stop_level = -1, or_lo, or_hi
                bi = or_bars + idn
                # BUGGY ttb = iu (look-ahead for short!)
                ttb_buggy = iu if iu < 10**9 else idn  # fall back to idn if no up-break ever
                ttb_correct = bi - or_bars

            # Standard EXEC_0 entry at level
            entry = level
            fh, fl = H[bi:], L[bi:]
            if direction == 1:
                hit = np.where(fl <= stop_level)[0]
            else:
                hit = np.where(fh >= stop_level)[0]
            if len(hit):
                exit_px = stop_level
            else:
                exit_px = C[-1]
            r = (direction * (exit_px - entry) - cost) / or_range

            rows.append({
                "date": pd.Timestamp(day),
                "sleeve": sleeve_name,
                "direction": direction,
                "or_range": or_range,
                "ttb_buggy": ttb_buggy,
                "ttb_correct": ttb_correct,
                "iu": iu if iu < 10**9 else np.nan,
                "idn": idn if idn < 10**9 else np.nan,
                "r_realised": r,
            })
        if rows:
            parts.append(pd.DataFrame(rows).set_index("date"))
    out = pd.concat(parts).sort_index() if parts else pd.DataFrame()
    return out.loc[lo:hi]


def f1_effect(df: pd.DataFrame, ttb_col: str) -> dict:
    """Apply F1 ttb ≤ median filter; return mean R baseline, mean R F1, delta."""
    thr = df[ttb_col].quantile(0.5)
    keep = df[ttb_col] <= thr
    return {
        "n_total": len(df),
        "n_F1": int(keep.sum()),
        "threshold": float(thr),
        "mean_R_baseline": float(df["r_realised"].mean()),
        "mean_R_F1": float(df[keep]["r_realised"].mean()) if keep.any() else float("nan"),
        "delta_R": float(df[keep]["r_realised"].mean() - df["r_realised"].mean()) if keep.any() else float("nan"),
        "hit_rate_baseline": float((df["r_realised"] > 0).mean() * 100),
        "hit_rate_F1": float((df[keep]["r_realised"] > 0).mean() * 100) if keep.any() else float("nan"),
    }


if __name__ == "__main__":
    print("Re-extracting trades with both buggy and corrected ttb...")
    df = extract_with_corrected_ttb()
    print(f"Trades: {len(df)}")
    print(f"  long: {(df['direction'] == 1).sum()}")
    print(f"  short: {(df['direction'] == -1).sum()}")
    print()

    # Sanity check
    print("=" * 90)
    print("Sanity — ttb_buggy vs ttb_correct mismatch by direction")
    print("=" * 90)
    mismatches = df[df["ttb_buggy"] != df["ttb_correct"]]
    print(f"  Trades where buggy != correct: {len(mismatches)}/{len(df)} = "
          f"{len(mismatches)/len(df)*100:.1f}%")
    print(f"  Of those: long: {(mismatches['direction'] == 1).sum()}, "
          f"short: {(mismatches['direction'] == -1).sum()}")
    print()

    print("=" * 90)
    print("F1 effect by subset and ttb definition")
    print("=" * 90)
    results = {}
    for subset_name, subset in [("ALL", df),
                                 ("LONG only", df[df["direction"] == 1]),
                                 ("SHORT only", df[df["direction"] == -1])]:
        for ttb_col in ["ttb_buggy", "ttb_correct"]:
            r = f1_effect(subset, ttb_col)
            r["subset"] = subset_name
            r["ttb_def"] = ttb_col
            results[(subset_name, ttb_col)] = r
    res_df = pd.DataFrame(results).T.reset_index(drop=True)[
        ["subset", "ttb_def", "n_total", "n_F1", "threshold",
         "mean_R_baseline", "mean_R_F1", "delta_R", "hit_rate_baseline", "hit_rate_F1"]
    ]
    print(res_df.round(3).to_string(index=False))
    print()

    print("=" * 90)
    print("KEY COMPARISON")
    print("=" * 90)
    long_buggy = results[("LONG only", "ttb_buggy")]
    long_correct = results[("LONG only", "ttb_correct")]
    short_buggy = results[("SHORT only", "ttb_buggy")]
    short_correct = results[("SHORT only", "ttb_correct")]
    all_buggy = results[("ALL", "ttb_buggy")]
    all_correct = results[("ALL", "ttb_correct")]

    print(f"\nLONG-only F1 effect:")
    print(f"  buggy   : meanR base={long_buggy['mean_R_baseline']:+.3f}, F1={long_buggy['mean_R_F1']:+.3f}, "
          f"Δ={long_buggy['delta_R']:+.3f}")
    print(f"  correct : meanR base={long_correct['mean_R_baseline']:+.3f}, F1={long_correct['mean_R_F1']:+.3f}, "
          f"Δ={long_correct['delta_R']:+.3f}")
    print(f"  → for LONG, the two should be ~identical (buggy == correct for longs)")

    print(f"\nSHORT-only F1 effect:")
    print(f"  buggy (LOOK-AHEAD)  : meanR base={short_buggy['mean_R_baseline']:+.3f}, "
          f"F1={short_buggy['mean_R_F1']:+.3f}, Δ={short_buggy['delta_R']:+.3f}")
    print(f"  correct             : meanR base={short_correct['mean_R_baseline']:+.3f}, "
          f"F1={short_correct['mean_R_F1']:+.3f}, Δ={short_correct['delta_R']:+.3f}")
    print(f"  → if buggy F1 effect is much larger than correct, BUG CONFIRMED")

    print(f"\nALL trades F1 effect:")
    print(f"  buggy   : meanR base={all_buggy['mean_R_baseline']:+.3f}, F1={all_buggy['mean_R_F1']:+.3f}, "
          f"Δ={all_buggy['delta_R']:+.3f}")
    print(f"  correct : meanR base={all_correct['mean_R_baseline']:+.3f}, F1={all_correct['mean_R_F1']:+.3f}, "
          f"Δ={all_correct['delta_R']:+.3f}")

    # Save
    res_df.to_csv("f1_bughunt_direction_bug.csv", index=False)
    df.to_parquet("f1_bughunt_trades_with_both_ttb.parquet")
