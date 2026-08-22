"""
trade_step4_exits.py — Exit engineering (L19 mod #2).

The current rule: exit at session close (no target, no trailing).
Rationale per the original report: the positive skew IS the edge — any target,
trailing, or breakeven-stop destroys the right tail.

We test variants that *might* preserve the skew while reducing slow-bust risk:

  V1: Baseline (exit at close)
  V2: Scale-out 1/3 at +1.5R, runner to close (locks partial profit while
      keeping 2/3 of the runner exposure)
  V3: Scale-out 1/2 at +2R, runner to close
  V4: Tight trailing after +2R (give back 0.5R from local peak after reaching +2R)
  V5: Time-stop early (close at midday +2h instead of session close)

For each variant compute:
  - mean R, std R, Sharpe
  - top-decile capture (must NOT drop materially)
  - MaxDD on compounded equity (slow-bust proxy)
  - per-fold breakdown

Implementation: we replay each trade using the M1 panel high/low path to compute
where the variant would have exited. We need bar-by-bar OHLC AFTER entry.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from functools import lru_cache

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


def simulate_trade_with_variant(symbol, oh, om, ch, or_bars, day_data,
                                 variant: str, cost_pts: float, slip_R: float = 0.0):
    """
    Simulate one trade with a specified exit variant.
    Returns r_realised, outcome, exit_bar_index.

    day_data: DataFrame slice of the day's session bars.
    """
    H = day_data["high"].values
    L = day_data["low"].values
    C = day_data["close"].values
    O = day_data["open"].values
    if len(H) < or_bars + 3:
        return None
    or_hi = H[:or_bars].max()
    or_lo = L[:or_bars].min()
    risk = or_hi - or_lo
    if risk <= 0:
        return None
    up = np.where(H[or_bars:] > or_hi)[0]
    dn = np.where(L[or_bars:] < or_lo)[0]
    iu = up[0] if len(up) else 10**9
    idn = dn[0] if len(dn) else 10**9
    if iu == idn == 10**9:
        return None
    if iu <= idn:
        direction, level, stop_level = 1, or_hi, or_lo
        bi = or_bars + iu
    else:
        direction, level, stop_level = -1, or_lo, or_hi
        bi = or_bars + idn

    slip_pts = slip_R * risk
    entry = level + direction * slip_pts
    stop_eff = stop_level - direction * slip_pts

    fh, fl = H[bi:], L[bi:]
    n_post = len(fh)

    if variant == "V1_close":
        # Standard exit at close (or stop)
        if direction == 1:
            stop_hit = np.where(fl <= stop_eff)[0]
        else:
            stop_hit = np.where(fh >= stop_eff)[0]
        if len(stop_hit):
            exit_px = stop_eff
        else:
            exit_px = C[-1]
        r = (direction * (exit_px - entry) - cost_pts) / risk
        return r

    if variant in ("V2_scale1.5", "V3_scale2"):
        # Scale-out: take partial at +X R (only if reached) then runner to close (or stop).
        if variant == "V2_scale1.5":
            partial_target_R = 1.5
            partial_frac = 1.0 / 3.0
        else:
            partial_target_R = 2.0
            partial_frac = 0.5
        partial_target_px = entry + direction * partial_target_R * risk
        if direction == 1:
            tgt_hit = np.where(fh >= partial_target_px)[0]
            stop_hit = np.where(fl <= stop_eff)[0]
        else:
            tgt_hit = np.where(fl <= partial_target_px)[0]
            stop_hit = np.where(fh >= stop_eff)[0]
        first_tgt = tgt_hit[0] if len(tgt_hit) else 10**9
        first_stop = stop_hit[0] if len(stop_hit) else 10**9
        # Case A: stop hit before target -> full position stops out
        if first_stop < first_tgt:
            exit_px = stop_eff
            r = (direction * (exit_px - entry) - cost_pts) / risk
            return r
        # Case B: target NEVER hit (and stop never hit) -> exit full at close (no partial)
        if first_tgt == 10**9:
            exit_px = C[-1]
            r = (direction * (exit_px - entry) - cost_pts) / risk
            return r
        # Case C: target hit first -> take partial; runner continues with same stop
        if direction == 1:
            stop_hit_runner = np.where(fl[first_tgt:] <= stop_eff)[0]
        else:
            stop_hit_runner = np.where(fh[first_tgt:] >= stop_eff)[0]
        if len(stop_hit_runner):
            runner_exit_px = stop_eff
        else:
            runner_exit_px = C[-1]
        partial_r = partial_target_R - cost_pts / risk / 2  # half cost on partial leg
        runner_r = (direction * (runner_exit_px - entry) - cost_pts / 2) / risk
        r = partial_frac * partial_r + (1 - partial_frac) * runner_r
        return r

    if variant == "V4_trail_after_2R":
        # Trail after +2R: once profit reaches +2R, ratchet stop to (peak - 0.5R)
        if direction == 1:
            tgt2 = np.where(fh >= entry + 2 * risk)[0]
        else:
            tgt2 = np.where(fl <= entry - 2 * risk)[0]
        # Before +2R: just standard stop_eff
        # After +2R: trailing stop
        if not len(tgt2):
            # never reached +2R: standard exit
            if direction == 1:
                stop_hit = np.where(fl <= stop_eff)[0]
            else:
                stop_hit = np.where(fh >= stop_eff)[0]
            if len(stop_hit):
                exit_px = stop_eff
            else:
                exit_px = C[-1]
            r = (direction * (exit_px - entry) - cost_pts) / risk
            return r
        # Reached +2R at index t2
        t2 = tgt2[0]
        # Check if stop hit before t2
        if direction == 1:
            stop_hit_before = np.where(fl[:t2] <= stop_eff)[0]
        else:
            stop_hit_before = np.where(fh[:t2] >= stop_eff)[0]
        if len(stop_hit_before):
            exit_px = stop_eff
            r = (direction * (exit_px - entry) - cost_pts) / risk
            return r
        # After t2: trail. peak starts at the 2R level
        if direction == 1:
            peak = max(entry + 2 * risk, fh[t2])
        else:
            peak = min(entry - 2 * risk, fl[t2])
        trail_dist = 0.5 * risk
        post_t2_H = fh[t2:]
        post_t2_L = fl[t2:]
        exit_px = None
        for k in range(len(post_t2_H)):
            if direction == 1:
                peak = max(peak, post_t2_H[k])
                trailing_stop = peak - trail_dist
                if post_t2_L[k] <= trailing_stop:
                    exit_px = trailing_stop
                    break
            else:
                peak = min(peak, post_t2_L[k])
                trailing_stop = peak + trail_dist
                if post_t2_H[k] >= trailing_stop:
                    exit_px = trailing_stop
                    break
        if exit_px is None:
            exit_px = C[-1]
        r = (direction * (exit_px - entry) - cost_pts) / risk
        return r

    if variant == "V5_early_close":
        # Exit at +24 bars (= 2 hours) after breakout instead of session close
        max_bars = 24
        effective_n = min(max_bars, n_post)
        fh_eff = fh[:effective_n]
        fl_eff = fl[:effective_n]
        if direction == 1:
            stop_hit = np.where(fl_eff <= stop_eff)[0]
        else:
            stop_hit = np.where(fh_eff >= stop_eff)[0]
        if len(stop_hit):
            exit_px = stop_eff
        else:
            # Exit at the chosen bar's close
            close_idx = min(effective_n - 1, n_post - 1)
            exit_px = day_data["close"].values[bi + close_idx]
        r = (direction * (exit_px - entry) - cost_pts) / risk
        return r
    raise ValueError(f"Unknown variant {variant}")


def extract_trades_with_variant(variant: str, lo="2022", hi="2025",
                                 slip_R: float = 0.0) -> pd.DataFrame:
    parts = []
    for sleeve_name, symbol, oh, om, ch, or_bars in SLEEVES:
        df = _load_m5(symbol)
        h, m = df.index.hour, df.index.minute
        sess = df[((h > oh) | ((h == oh) & (m >= om))) & (h < ch)].copy()
        sess["day"] = sess.index.date
        cost_pts = COST_POINTS[symbol]
        rows = []
        for day, g in sess.groupby("day"):
            r = simulate_trade_with_variant(symbol, oh, om, ch, or_bars, g,
                                             variant, cost_pts, slip_R=slip_R)
            if r is not None:
                rows.append({"date": pd.Timestamp(day), "sleeve": sleeve_name,
                              "symbol": symbol, "r_realised": r})
        df_v = pd.DataFrame(rows).set_index("date")
        parts.append(df_v.loc[lo:hi])
    return pd.concat(parts).sort_index()


if __name__ == "__main__":
    variants = ["V1_close", "V2_scale1.5", "V3_scale2", "V4_trail_after_2R", "V5_early_close"]
    summary = []
    for v in variants:
        print(f"Running variant {v}...")
        df_v = extract_trades_with_variant(v, lo="2022", hi="2025")
        # Top-decile R from V1 baseline
        if v == "V1_close":
            v1_top10 = df_v["r_realised"].quantile(0.90)
        # Compute equity / DD via 0.50% block-cap (similar to optim final)
        risk_block = 0.005
        # Each sleeve gets share of block, sum daily
        pivoted = df_v.pivot_table(values="r_realised", index=df_v.index,
                                     columns="sleeve", aggfunc="first")
        # AM block = GER40_1000_30m (1 sleeve at full risk_block)
        # PM block = US100 + GER40_1630_15m at risk_block/2
        am_cols = ["GER40_1000_30m"]
        pm_cols = ["US100_1630_30m", "GER40_1630_15m"]
        for c in am_cols + pm_cols:
            if c not in pivoted.columns:
                pivoted[c] = np.nan
        am = pivoted[am_cols].fillna(0.0).sum(axis=1) * risk_block
        pm = (pivoted[pm_cols].fillna(0.0) * (risk_block / 2)).sum(axis=1)
        daily_pnl = (am + pm).fillna(0.0)
        eq = (1 + daily_pnl).cumprod()
        max_dd = (eq / eq.cummax() - 1).min() * 100
        sharpe = daily_pnl.mean() / daily_pnl.std() * np.sqrt(252) if daily_pnl.std() > 0 else 0
        # Top decile preservation: % of trades >= V1_top10
        top10_in_variant = (df_v["r_realised"] >= v1_top10).sum() / len(df_v) * 100
        # Total return
        total_ret = (eq.iloc[-1] - 1) * 100
        summary.append({
            "variant": v,
            "n_trades": len(df_v),
            "mean_R": df_v["r_realised"].mean(),
            "std_R": df_v["r_realised"].std(),
            "skew_R": df_v["r_realised"].skew(),
            "top10_share_in_variant_pct": top10_in_variant,
            "daily_sharpe_ann": sharpe,
            "max_dd_pct": max_dd,
            "total_return_pct": total_ret,
        })
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv("trade_step4_exits.csv", index=False)
    print()
    print("=" * 90)
    print("STEP 4 — Exit variants summary (block-cap 0.50%, 2022-2025)")
    print("=" * 90)
    print(summary_df.round(3).to_string(index=False))
