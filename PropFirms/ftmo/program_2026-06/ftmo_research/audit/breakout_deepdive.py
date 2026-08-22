"""
breakout_deepdive.py — Phase 1: broad scan of breakout/trend family on NQ 2010-2026.

Anti-overfit framework (per brief):
  - One trade per day max (non-overlapping).
  - Cost in bps (1 bp RT for NQ futures-equivalent).
  - Metric = mean net R per trade, t-stat with day-clustered SE.
  - PRIMARY filter: TWO-SIDED requirement (short leg net ≥ ~0). One-sided long
    = beta in disguise (L25), REJECTED.
  - Delay sensitivity: test 0-bar (same-bar fill) AND 1-bar (next-bar-open).
  - Report by-year + by-regime breakdown.

Signal logic variants in Phase 1:
  S1: ORB 30-min (= baseline reference)
  S2: ORB 15-min
  S3: ORB 60-min
  S4: Donchian 20-bar 5-min (= 100 min lookback)
  S5: Donchian 60-bar 5-min (= 300 min lookback)
  S6: Vol breakout: close > prev_close + 1.5 × ATR_20d
  S7: Squeeze breakout: enter when 5-bar range < 50% of 20-bar avg range, dir = first break
  S8: PDH/PDL breakout (prior-day high/low)
  S9: Bollinger band breakout (close > BB_upper or close < BB_lower, 20-period 2-sigma)
  S10: Range expansion: enter when current bar's range > 1.5 × ATR_20

All use EOD exit (= last RTH bar close) + stop at opposite-side breakout level
(or analogous reference). Cost = 1 bp × price / 10000 per trade.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from functools import lru_cache
from scipy import stats


DATA_PATH = Path(__file__).resolve().parents[1].parent / "raw" / "NQ_1min_databento_2010-2026.parquet"
COST_BPS_RT = 1.0  # NQ futures-equivalent realistic round-trip


@lru_cache(maxsize=2)
def load_nq_5min() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    df = df[df["is_rth"] & ~df["is_roll_day"]].copy()
    df_5m = df.groupby(df.index.date).apply(
        lambda g: g[["open", "high", "low", "close", "volume"]].resample("5min").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        ).dropna()
    )
    return df_5m.reset_index(level=0, drop=True)


# ---------- Signal generators ----------
# Each returns: (direction, level, stop_level, entry_bar_idx) or None

def signal_orb(day_bars: pd.DataFrame, or_bars: int) -> dict | None:
    H = day_bars["high"].values
    L = day_bars["low"].values
    C = day_bars["close"].values
    if len(H) < or_bars + 3:
        return None
    or_hi = H[:or_bars].max()
    or_lo = L[:or_bars].min()
    if or_hi - or_lo <= 0:
        return None
    up = np.where(C[or_bars:] > or_hi)[0]
    dn = np.where(C[or_bars:] < or_lo)[0]
    iu = up[0] if len(up) else 10**9
    idn = dn[0] if len(dn) else 10**9
    if iu == idn == 10**9:
        return None
    if iu <= idn:
        return {"direction": 1, "level": or_hi, "stop_level": or_lo,
                "entry_bar": or_bars + iu, "or_range": or_hi - or_lo}
    return {"direction": -1, "level": or_lo, "stop_level": or_hi,
            "entry_bar": or_bars + idn, "or_range": or_hi - or_lo}


def signal_donchian(day_bars: pd.DataFrame, lookback: int) -> dict | None:
    H = day_bars["high"].values
    L = day_bars["low"].values
    C = day_bars["close"].values
    if len(H) < lookback + 3:
        return None
    # Trail rolling high/low up to bar t-1
    for i in range(lookback, len(H) - 1):
        hi_lb = H[i - lookback:i].max()
        lo_lb = L[i - lookback:i].min()
        if hi_lb - lo_lb <= 0:
            continue
        if C[i] > hi_lb:
            return {"direction": 1, "level": hi_lb, "stop_level": lo_lb,
                    "entry_bar": i, "or_range": hi_lb - lo_lb}
        if C[i] < lo_lb:
            return {"direction": -1, "level": lo_lb, "stop_level": hi_lb,
                    "entry_bar": i, "or_range": hi_lb - lo_lb}
    return None


def signal_vol_breakout(day_bars: pd.DataFrame, prior_close: float,
                         atr20: float, mult: float = 1.5) -> dict | None:
    """First bar whose close exceeds prior_close ± mult × ATR_20."""
    if pd.isna(prior_close) or pd.isna(atr20) or atr20 <= 0:
        return None
    C = day_bars["close"].values
    thr_up = prior_close + mult * atr20
    thr_dn = prior_close - mult * atr20
    for i in range(len(C)):
        if C[i] > thr_up:
            return {"direction": 1, "level": thr_up, "stop_level": thr_dn,
                    "entry_bar": i, "or_range": thr_up - thr_dn}
        if C[i] < thr_dn:
            return {"direction": -1, "level": thr_dn, "stop_level": thr_up,
                    "entry_bar": i, "or_range": thr_up - thr_dn}
    return None


def signal_squeeze(day_bars: pd.DataFrame, recent_lb: int = 5,
                    long_lb: int = 20, compression: float = 0.5) -> dict | None:
    """Enter on first break after compression: recent N-bar range < compression × long N-bar avg range."""
    H = day_bars["high"].values
    L = day_bars["low"].values
    C = day_bars["close"].values
    if len(H) < long_lb + 5:
        return None
    for i in range(long_lb, len(H) - 2):
        recent_range = H[i - recent_lb:i].max() - L[i - recent_lb:i].min()
        long_avg = np.mean([H[j] - L[j] for j in range(i - long_lb, i)])
        if long_avg <= 0:
            continue
        if recent_range >= compression * long_avg:
            continue
        # Compression detected at bar i — look for break in next bars
        ref_hi = H[i - recent_lb:i].max()
        ref_lo = L[i - recent_lb:i].min()
        for k in range(i, min(i + 12, len(C) - 1)):  # window 12 bars = 1h
            if C[k] > ref_hi:
                return {"direction": 1, "level": ref_hi, "stop_level": ref_lo,
                        "entry_bar": k, "or_range": ref_hi - ref_lo}
            if C[k] < ref_lo:
                return {"direction": -1, "level": ref_lo, "stop_level": ref_hi,
                        "entry_bar": k, "or_range": ref_hi - ref_lo}
        # If no break in window, continue scanning
    return None


def signal_pdh_pdl(day_bars: pd.DataFrame, pdh: float, pdl: float) -> dict | None:
    """Break of prior-day high (long) or low (short). First break wins."""
    if pd.isna(pdh) or pd.isna(pdl) or pdh - pdl <= 0:
        return None
    C = day_bars["close"].values
    for i in range(len(C)):
        if C[i] > pdh:
            return {"direction": 1, "level": pdh, "stop_level": pdl,
                    "entry_bar": i, "or_range": pdh - pdl}
        if C[i] < pdl:
            return {"direction": -1, "level": pdl, "stop_level": pdh,
                    "entry_bar": i, "or_range": pdh - pdl}
    return None


def signal_bollinger(day_bars: pd.DataFrame, period: int = 20,
                      sigma: float = 2.0) -> dict | None:
    """Close crosses BB upper or lower band."""
    C = day_bars["close"].values
    if len(C) < period + 3:
        return None
    for i in range(period, len(C) - 1):
        sma = C[i - period:i].mean()
        std = C[i - period:i].std()
        if std <= 0:
            continue
        bb_up = sma + sigma * std
        bb_dn = sma - sigma * std
        if C[i] > bb_up:
            return {"direction": 1, "level": bb_up, "stop_level": bb_dn,
                    "entry_bar": i, "or_range": bb_up - bb_dn}
        if C[i] < bb_dn:
            return {"direction": -1, "level": bb_dn, "stop_level": bb_up,
                    "entry_bar": i, "or_range": bb_up - bb_dn}
    return None


def signal_range_expansion(day_bars: pd.DataFrame, atr_period: int = 20,
                            mult: float = 1.5) -> dict | None:
    """Enter when intra-day bar's range exceeds mult × ATR_20."""
    H = day_bars["high"].values
    L = day_bars["low"].values
    C = day_bars["close"].values
    O = day_bars["open"].values
    if len(H) < atr_period + 3:
        return None
    for i in range(atr_period, len(H) - 1):
        atr = np.mean([H[j] - L[j] for j in range(i - atr_period, i)])
        if atr <= 0:
            continue
        bar_range = H[i] - L[i]
        if bar_range > mult * atr:
            # Direction = sign of body
            if C[i] > O[i]:
                return {"direction": 1, "level": H[i], "stop_level": L[i],
                        "entry_bar": i, "or_range": H[i] - L[i]}
            elif C[i] < O[i]:
                return {"direction": -1, "level": L[i], "stop_level": H[i],
                        "entry_bar": i, "or_range": H[i] - L[i]}
    return None


# ---------- Trade extraction & R computation ----------

def extract_trade_R(day_bars: pd.DataFrame, sig: dict, exec_model: str = "EXEC_0",
                     cost_bps: float = COST_BPS_RT) -> dict | None:
    """Given signal, compute net R for a given exec_model."""
    if sig is None:
        return None
    direction = sig["direction"]
    level = sig["level"]
    stop_level = sig["stop_level"]
    or_range = sig["or_range"]
    bi = sig["entry_bar"]
    H = day_bars["high"].values
    L = day_bars["low"].values
    C = day_bars["close"].values
    O = day_bars["open"].values
    if bi >= len(H):
        return None

    # Entry
    if exec_model == "EXEC_0":
        if bi >= len(O):
            return None
        # Same-bar fill at level (dormant stop)
        entry = level
        entry_bar = bi
    elif exec_model == "EXEC_NEXT_OPEN":
        if bi + 1 >= len(O):
            return None
        entry = O[bi + 1]
        entry_bar = bi + 1
    else:
        raise ValueError(exec_model)

    # Cost in points
    cost_pts = cost_bps * level / 10000.0

    # Find exit (stop or EOD close)
    fh = H[entry_bar:]
    fl = L[entry_bar:]
    if direction == 1:
        hit = np.where(fl <= stop_level)[0]
    else:
        hit = np.where(fh >= stop_level)[0]
    if len(hit):
        exit_px = stop_level
        outcome = "STOP"
    else:
        exit_px = C[-1]
        outcome = "EOD"
    r_gross = direction * (exit_px - entry) / or_range
    r_net = r_gross - cost_pts / or_range
    return {
        "direction": direction, "level": level, "or_range": or_range,
        "entry": entry, "exit_px": exit_px, "outcome": outcome,
        "r_gross": r_gross, "r_net": r_net,
    }


# ---------- Main extraction loop ----------

_PER_DAY_BARS_CACHE = None


def _get_per_day_bars():
    """Pre-compute per-day bars dict ONCE (cached)."""
    global _PER_DAY_BARS_CACHE
    if _PER_DAY_BARS_CACHE is None:
        df_5m = load_nq_5min()
        # Group once, dict of date -> DataFrame
        _PER_DAY_BARS_CACHE = {pd.Timestamp(day): grp for day, grp in df_5m.groupby(df_5m.index.date)}
    return _PER_DAY_BARS_CACHE


def extract_all_trades(signal_fn, signal_kwargs: dict, signal_name: str,
                        cost_bps: float = COST_BPS_RT,
                        needs_prior_data: bool = False) -> pd.DataFrame:
    """Run a single signal across all days. Returns trade-level DataFrame."""
    per_day = _get_per_day_bars()
    days = sorted(per_day.keys())
    rows = []
    # Pre-compute prior day metrics if needed
    if needs_prior_data:
        df_5m = load_nq_5min()
        daily_close = df_5m.groupby(df_5m.index.date)["close"].last()
        daily_high = df_5m.groupby(df_5m.index.date)["high"].max()
        daily_low = df_5m.groupby(df_5m.index.date)["low"].min()
        prior_close_map = {pd.Timestamp(k): v for k, v in daily_close.shift(1).to_dict().items()}
        atr20_map = {pd.Timestamp(k): v for k, v in (daily_high - daily_low).rolling(20).mean().shift(1).to_dict().items()}
        pdh_map = {pd.Timestamp(k): v for k, v in daily_high.shift(1).to_dict().items()}
        pdl_map = {pd.Timestamp(k): v for k, v in daily_low.shift(1).to_dict().items()}
    else:
        prior_close_map = atr20_map = pdh_map = pdl_map = {}

    # Pre-compute signature inspection ONCE
    import inspect as _inspect
    params_set = set(_inspect.signature(signal_fn).parameters.keys())

    for day in days:
        day_bars = per_day[day]
        if len(day_bars) < 30:
            continue
        # Build signal kwargs with prior data if needed
        kwargs = signal_kwargs.copy()
        if needs_prior_data:
            if "prior_close" in params_set:
                kwargs["prior_close"] = prior_close_map.get(day, np.nan)
            if "atr20" in params_set:
                kwargs["atr20"] = atr20_map.get(day, np.nan)
            if "pdh" in params_set:
                kwargs["pdh"] = pdh_map.get(day, np.nan)
            if "pdl" in params_set:
                kwargs["pdl"] = pdl_map.get(day, np.nan)
        sig = signal_fn(day_bars, **kwargs)
        if sig is None:
            continue
        # Compute R for both exec models
        r_exec0 = extract_trade_R(day_bars, sig, exec_model="EXEC_0", cost_bps=cost_bps)
        r_exec1 = extract_trade_R(day_bars, sig, exec_model="EXEC_NEXT_OPEN", cost_bps=cost_bps)
        if r_exec0 is None:
            continue
        rows.append({
            "date": pd.Timestamp(day),
            "signal": signal_name,
            "direction": sig["direction"],
            "level": sig["level"],
            "or_range": sig["or_range"],
            "r_gross_exec0": r_exec0["r_gross"],
            "r_net_exec0": r_exec0["r_net"],
            "r_net_exec1": r_exec1["r_net"] if r_exec1 else np.nan,
            "outcome_exec0": r_exec0["outcome"],
        })
    return pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame()


def cluster_t_stat(values: np.ndarray, days: np.ndarray) -> float:
    """t-stat with day-cluster SE (block bootstrap)."""
    mask = ~np.isnan(values)
    v = values[mask]
    d = days[mask]
    if len(v) < 30:
        return float("nan")
    mean = v.mean()
    # Cluster bootstrap SE
    rng = np.random.default_rng(7)
    df_local = pd.DataFrame({"v": v, "d": d})
    days_u = df_local["d"].unique()
    means = []
    for _ in range(500):
        sampled = rng.choice(days_u, size=len(days_u), replace=True)
        sub = df_local[df_local["d"].isin(sampled)]
        if len(sub):
            means.append(sub["v"].mean())
    se = float(np.std(means)) if means else float("nan")
    return mean / se if se > 0 else float("nan")


def compute_metrics(df_trades: pd.DataFrame, r_col: str = "r_net_exec0") -> dict:
    """Compute headline metrics including long/short split."""
    if df_trades.empty:
        return {}
    days = df_trades.index.values
    overall_t = cluster_t_stat(df_trades[r_col].values, days)
    long_t = cluster_t_stat(
        df_trades[df_trades["direction"] == 1][r_col].values,
        df_trades[df_trades["direction"] == 1].index.values
    )
    short_t = cluster_t_stat(
        df_trades[df_trades["direction"] == -1][r_col].values,
        df_trades[df_trades["direction"] == -1].index.values
    )
    return {
        "n_total": len(df_trades),
        "n_long": int((df_trades["direction"] == 1).sum()),
        "n_short": int((df_trades["direction"] == -1).sum()),
        "mean_R_total": df_trades[r_col].mean(),
        "mean_R_long": df_trades[df_trades["direction"] == 1][r_col].mean(),
        "mean_R_short": df_trades[df_trades["direction"] == -1][r_col].mean(),
        "t_stat_total": overall_t,
        "t_stat_long": long_t,
        "t_stat_short": short_t,
        "skew": df_trades[r_col].skew(),
        "hit_rate_total": (df_trades[r_col] > 0).mean() * 100,
        "hit_rate_long": (df_trades[df_trades["direction"] == 1][r_col] > 0).mean() * 100,
        "hit_rate_short": (df_trades[df_trades["direction"] == -1][r_col] > 0).mean() * 100,
    }


# ---------- Phase 1 broad scan ----------

VARIANTS = [
    # (signal_name, signal_fn, signal_kwargs, needs_prior_data)
    ("ORB_30min",    signal_orb,             {"or_bars": 6}, False),
    ("ORB_15min",    signal_orb,             {"or_bars": 3}, False),
    ("ORB_60min",    signal_orb,             {"or_bars": 12}, False),
    ("Donchian_20",  signal_donchian,        {"lookback": 20}, False),
    ("Donchian_60",  signal_donchian,        {"lookback": 60}, False),
    ("Vol_break_1.5ATR", signal_vol_breakout, {"mult": 1.5}, True),
    ("Squeeze",      signal_squeeze,         {"recent_lb": 5, "long_lb": 20, "compression": 0.5}, False),
    ("PDH_PDL",      signal_pdh_pdl,         {}, True),
    ("Bollinger_20_2sigma", signal_bollinger, {"period": 20, "sigma": 2.0}, False),
    ("Range_expansion_1.5", signal_range_expansion, {"atr_period": 20, "mult": 1.5}, False),
]


if __name__ == "__main__":
    print("=" * 110)
    print("PHASE 1 — Broad scan, breakout/trend family on NQ 2010-2026 (cost 1 bp RT)")
    print("=" * 110)
    print(f"\n{len(VARIANTS)} variants × NQ 5-min, EOD exit, same-bar fill (EXEC_0)\n")
    all_metrics = []
    all_trades = {}
    for vname, vfn, vkwargs, needs_prior in VARIANTS:
        print(f"\n--- {vname} ---")
        df = extract_all_trades(vfn, vkwargs, vname, cost_bps=COST_BPS_RT,
                                  needs_prior_data=needs_prior)
        if df.empty:
            print(f"  No trades extracted")
            continue
        m = compute_metrics(df, r_col="r_net_exec0")
        m["variant"] = vname
        # delay-1 metrics
        m1 = compute_metrics(df, r_col="r_net_exec1")
        m["mean_R_total_delay1"] = m1.get("mean_R_total")
        m["mean_R_short_delay1"] = m1.get("mean_R_short")
        m["t_stat_short_delay1"] = m1.get("t_stat_short")
        all_metrics.append(m)
        all_trades[vname] = df
        # Print quick summary
        print(f"  n={m['n_total']} (long={m['n_long']}, short={m['n_short']})")
        print(f"  Net mean R (EXEC_0): total={m['mean_R_total']:+.4f}, "
              f"long={m['mean_R_long']:+.4f} (t={m['t_stat_long']:+.2f}), "
              f"short={m['mean_R_short']:+.4f} (t={m['t_stat_short']:+.2f})")
        print(f"  Delay-1 short mean R: {m['mean_R_short_delay1']:+.4f} (t={m['t_stat_short_delay1']:+.2f})")
        print(f"  Skew: {m['skew']:.2f}, hit rate: {m['hit_rate_total']:.1f}%")

    # Summary table
    df_metrics = pd.DataFrame(all_metrics)
    df_metrics.to_csv("breakout_phase1_metrics.csv", index=False)
    print()
    print("=" * 110)
    print("PHASE 1 SUMMARY TABLE")
    print("=" * 110)
    cols = ["variant", "n_total", "n_long", "n_short",
            "mean_R_total", "mean_R_long", "mean_R_short",
            "t_stat_total", "t_stat_long", "t_stat_short",
            "mean_R_short_delay1", "t_stat_short_delay1", "skew"]
    print(df_metrics[cols].round(3).to_string(index=False))

    # Two-sided filter
    print()
    print("=" * 110)
    print("TWO-SIDED filter (L25): short leg mean_R_net ≥ -0.02 AND short t-stat > -1")
    print("=" * 110)
    df_metrics["two_sided_pass"] = (df_metrics["mean_R_short"] >= -0.02) & (df_metrics["t_stat_short"] > -1)
    survivors = df_metrics[df_metrics["two_sided_pass"]].copy()
    print(f"\nSurvivors: {len(survivors)}/{len(df_metrics)}")
    print(survivors[["variant", "mean_R_total", "mean_R_long", "mean_R_short",
                      "t_stat_total", "t_stat_short", "n_total"]].round(3).to_string(index=False))
    # Save trades for survivors
    for vname in survivors["variant"]:
        all_trades[vname].to_parquet(f"breakout_phase1_trades_{vname}.parquet")
    df_metrics.to_csv("breakout_phase1_full.csv", index=False)
    print(f"\nSaved trade datasets for {len(survivors)} survivors")
