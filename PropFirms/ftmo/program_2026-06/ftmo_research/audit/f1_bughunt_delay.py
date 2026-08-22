"""
f1_bughunt_delay.py — Clean execution test (CRITICAL).

Re-extract trade-level dataset with proper next-bar-open execution
(plus 1-bar and 2-bar delay variants), then test the F1 filter.

Three execution models tested:
  EXEC_0 (current/buggy) : detect break via H[bi] > or_hi, enter at or_hi (SAME bar)
  EXEC_NEXT_OPEN         : detect break via close[bi] > or_hi, enter at open[bi+1]
                            (this is the truly clean point-in-time model)
  EXEC_DELAY_1           : detect break via H[bi] > or_hi (legacy), enter at open[bi+1]
                            (orb_core.py's existing delay_bars=1 mode)
  EXEC_DELAY_2           : detect via H[bi], enter at open[bi+2]

For each model:
  1. Extract trade dataset with feature time_to_break_5min still defined the same way
     (= bars after OR close before break — point-in-time feature)
  2. Compute F1 effect: mean R baseline vs F1 (top quintile of ttb=0 specifically,
     plus q=0.5 threshold)
  3. Compare across models

**Expected if F1 is a same-bar artifact**:
  EXEC_0 F1 mean R = +0.44
  EXEC_DELAY_1 F1 mean R should collapse toward baseline mean R ≈ +0.05-0.10
  EXEC_NEXT_OPEN F1 mean R should be even closer to baseline
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


def extract_with_exec(symbol: str, oh: int, om: int, ch: int, or_bars: int,
                       exec_model: str = "EXEC_0",
                       lo: str = "2022", hi: str = "2025") -> pd.DataFrame:
    """
    Extract trades with one of four execution models.

    EXEC_0: detect via H/L intra-bar, enter at or_hi/or_lo (SAME bar fill at level)
    EXEC_NEXT_OPEN: detect via CLOSE breach, enter at open of bar+1
    EXEC_DELAY_1: detect via H/L (legacy), enter at open of bar+1; cancel if opposite hit on bi
    EXEC_DELAY_2: detect via H/L, enter at open of bar+2; cancel if opposite hit on bi or bi+1
    """
    df = _load_m5(symbol)
    h, m = df.index.hour, df.index.minute
    sess = df[((h > oh) | ((h == oh) & (m >= om))) & (h < ch)].copy()
    sess["day"] = sess.index.date
    cost = COST_POINTS[symbol]
    rows = []
    for day, g in sess.groupby("day"):
        day_ts = pd.Timestamp(day)
        H, L, C, O = g["high"].values, g["low"].values, g["close"].values, g["open"].values
        if len(H) < or_bars + 5:
            continue
        or_hi = H[:or_bars].max()
        or_lo = L[:or_bars].min()
        or_range = or_hi - or_lo
        if or_range <= 0:
            continue

        # Break detection — depends on model
        if exec_model == "EXEC_NEXT_OPEN":
            # Detect via CLOSE breach (point-in-time, only known at bar close)
            close_post = C[or_bars:]
            up = np.where(close_post > or_hi)[0]
            dn = np.where(close_post < or_lo)[0]
        else:
            # Legacy: detect via H/L intra-bar (the buggy way)
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

        # Time-to-break stays the same definition
        ttb = iu if iu < 10**9 else idn

        # Entry — depends on model
        if exec_model == "EXEC_0":
            # Same-bar fill at level (BUGGY: assumes perfect fill at or_hi/or_lo)
            entry_bar = bi
            entry = level
        elif exec_model == "EXEC_NEXT_OPEN":
            # CLEAN: enter at open of bar bi+1
            if bi + 1 >= len(g):
                continue
            entry_bar = bi + 1
            entry = O[bi + 1]
        elif exec_model == "EXEC_DELAY_1":
            # Legacy delay: break via H/L, enter at open of bi+1
            # Cancel if opposite side hit during bar bi
            interim_h = H[bi:bi+1]
            interim_l = L[bi:bi+1]
            if direction == 1:
                if (interim_l <= stop_level).any():
                    continue
            else:
                if (interim_h >= stop_level).any():
                    continue
            if bi + 1 >= len(g):
                continue
            entry_bar = bi + 1
            entry = O[bi + 1]
        elif exec_model == "EXEC_DELAY_2":
            interim_h = H[bi:bi+2]
            interim_l = L[bi:bi+2]
            if direction == 1:
                if (interim_l <= stop_level).any():
                    continue
            else:
                if (interim_h >= stop_level).any():
                    continue
            if bi + 2 >= len(g):
                continue
            entry_bar = bi + 2
            entry = O[bi + 2]
        else:
            raise ValueError(f"Unknown exec_model {exec_model}")

        # Exit (find stop or close)
        fh, fl = H[entry_bar:], L[entry_bar:]
        if direction == 1:
            hit = np.where(fl <= stop_level)[0]
        else:
            hit = np.where(fh >= stop_level)[0]
        if len(hit):
            exit_px = stop_level
        else:
            exit_px = C[-1]
        r_realised = (direction * (exit_px - entry) - cost) / or_range

        rows.append({
            "date": day_ts,
            "sleeve": f"{symbol}_{oh:02d}{om:02d}_{or_bars}",
            "symbol": symbol,
            "exec_model": exec_model,
            "or_range": or_range,
            "ttb_5min": ttb,
            "direction": direction,
            "level": level,
            "entry": entry,
            "entry_bar_idx": entry_bar,
            "bi": bi,
            "exit_px": exit_px,
            "r_realised": r_realised,
        })
    df_out = pd.DataFrame(rows)
    if len(df_out):
        df_out = df_out.set_index("date").loc[lo:hi]
    return df_out


def extract_all_exec(exec_model: str, lo="2022", hi="2025") -> pd.DataFrame:
    parts = []
    for sleeve_name, symbol, oh, om, ch, or_bars in SLEEVES:
        df = extract_with_exec(symbol, oh, om, ch, or_bars, exec_model, lo, hi)
        if len(df):
            parts.append(df)
    return pd.concat(parts).sort_index() if parts else pd.DataFrame()


def compare_models(quantile: float = 0.5):
    print("=" * 95)
    print(f"Comparing 4 exec models on F1 filter (ttb ≤ q{quantile})")
    print("=" * 95)
    results = {}
    for model in ["EXEC_0", "EXEC_DELAY_1", "EXEC_DELAY_2", "EXEC_NEXT_OPEN"]:
        print(f"\nExtracting {model}...")
        df = extract_all_exec(model)
        if df.empty:
            continue
        threshold = df["ttb_5min"].quantile(quantile)
        keep = df["ttb_5min"] <= threshold
        baseline_meanR = df["r_realised"].mean()
        f1_meanR = df[keep]["r_realised"].mean()
        n_total = len(df)
        n_f1 = int(keep.sum())
        results[model] = {
            "n_total": n_total,
            "n_F1": n_f1,
            "retention": n_f1 / n_total * 100,
            "threshold": threshold,
            "mean_R_baseline": baseline_meanR,
            "std_R_baseline": df["r_realised"].std(),
            "mean_R_F1": f1_meanR,
            "std_R_F1": df[keep]["r_realised"].std(),
            "delta_mean_R": f1_meanR - baseline_meanR,
            "hit_rate_baseline": (df["r_realised"] > 0).mean() * 100,
            "hit_rate_F1": (df[keep]["r_realised"] > 0).mean() * 100,
            "top10_pct_baseline": df["r_realised"].quantile(0.90),
        }
    res = pd.DataFrame(results).T
    return res


if __name__ == "__main__":
    res = compare_models(quantile=0.5)
    print()
    print("=" * 95)
    print("BUG HUNT — execution model effect on F1")
    print("=" * 95)
    print(res.round(3).to_string())
    print()
    # Compute ratio
    print("=" * 95)
    print("Delta F1 vs baseline by exec model")
    print("=" * 95)
    base0 = res.loc["EXEC_0", "mean_R_baseline"]
    f1_0 = res.loc["EXEC_0", "mean_R_F1"]
    print(f"\n  EXEC_0 (BUGGY same-bar at level):")
    print(f"     baseline meanR = {base0:+.3f}, F1 meanR = {f1_0:+.3f}, ratio = {f1_0/base0:.2f}× baseline")
    for m in ["EXEC_DELAY_1", "EXEC_DELAY_2", "EXEC_NEXT_OPEN"]:
        if m in res.index:
            b = res.loc[m, "mean_R_baseline"]
            f = res.loc[m, "mean_R_F1"]
            print(f"\n  {m}:")
            print(f"     baseline meanR = {b:+.3f}, F1 meanR = {f:+.3f}, ratio = {f/b:.2f}× baseline")
            print(f"     F1 collapse vs EXEC_0: {(f/f1_0)*100:.1f}% of original F1 effect")

    res.to_csv("f1_bughunt_delay_test.csv")
