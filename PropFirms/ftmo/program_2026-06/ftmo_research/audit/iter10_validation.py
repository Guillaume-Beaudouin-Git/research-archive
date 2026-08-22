"""
iter10_validation.py — Reproduce Strategy C iter_10 on NQ Databento 2010-2026.

iter_10 spec (canonical, from Futures/research/active/nq_intraday/iter_05.py +
iter_08 8b + signal_engine.py + CLAUDE.md):

  Universe : NQ futures, 1-min RTH bars (09:30-15:59 US/Eastern).
  Window   : Opening 09:30-09:45 (16 bars, 1-min granularity).

  Per-day features:
    open_p   = first 1-min bar open at 09:30
    close_p  = last  1-min bar close at 09:45
    rng      = |close_p - open_p|           # directional move (NOT H-L)
    direction= sign(close_p - open_p)        # +1 long / -1 short
    vwap_rth = cumulative HLC3 × volume from 09:31 to 09:45  # vwap_rth at 09:45
    gap_pct  = (today_rth_open - prev_rth_close) / prev_rth_close

  Filters:
    M1: rng >= 30 points
    A:  vwap_ok = (dir== 1 and close_p > vwap_rth_at_09:45) or
                  (dir==-1 and close_p < vwap_rth_at_09:45)
    B:  abs(gap_pct) <= 0.012

  Exit rules:
    Entry  = open of first 1-min bar AFTER 09:45 = 09:46 open
    tp_pts = rng * 1.5
    sl_pts = min(rng * 0.5, 20.0)            # 20 pts cap = $400 at NQ $20/pt
    Time stop = 12:30 ET (exit at close of bar)
    On per-bar walk: check SL first then TP (engine.py convention).

  Cost: $19 RT per contract (= 1 pt RT at $20/pt) — engine.py default.
        Adjusted for stress via cost_mult.

Outputs:
  - iter10_trades.parquet (per-trade log)
  - iter10_daily_pnl.parquet (daily P&L)
  - iter10_features.parquet (per-day features pre-filter)
  - iter10_validation_output.txt (CLI summary)
"""
from __future__ import annotations
from pathlib import Path
import datetime
import logging
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT.parents[1]
NQ_PARQUET = DATA_ROOT / "raw" / "NQ_1min_databento_2010-2026.parquet"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---- NQ contract specs ----
POINT_VALUE_USD = 20.0     # NQ full contract
COST_RT_USD = 19.0         # default round-trip cost (engine.py)
TICK_SZ = 0.25

# ---- Strategy parameters (iter_10 canonical) ----
TP_RATIO = 1.5
SL_RATIO = 0.5
SL_CAP_PTS = 20.0          # = $400 at NQ $20/pt
GAP_FILTER = 0.012
RANGE_MIN_PTS = 30
T_OR_START = datetime.time(9, 30)
T_OR_END = datetime.time(9, 45)
T_TIME_STOP = datetime.time(12, 30)
T_RTH_START = datetime.time(9, 30)
T_RTH_END = datetime.time(15, 59)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_rth_1min(skip_roll: bool = True) -> pd.DataFrame:
    """Load NQ 1-min Databento, RTH only, tz-aware US/Eastern."""
    df = pd.read_parquet(NQ_PARQUET, columns=["open", "high", "low", "close",
                                                "volume", "is_roll_day", "is_rth"])
    if skip_roll:
        df = df[~df["is_roll_day"]]
    df = df[df["is_rth"]].copy()
    df = df.drop(columns=["is_roll_day", "is_rth"])
    df.index = df.index.tz_convert("US/Eastern")
    df = df.sort_index()
    return df


def precompute_vwap_rth(df: pd.DataFrame) -> pd.Series:
    """Cumulative VWAP from 09:31 ET per day (HLC3 × volume).

    Matches Kaggle convention from signal_engine.py: 09:30 bar has vwap_rth = 0,
    cumulation starts at 09:31.
    """
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3.0
    df_local = df.copy()
    df_local["hlc3_vol"] = hlc3 * df["volume"]
    # mask : 09:31 <= time, used for cumulative
    t = df.index.time
    after_open = t > T_OR_START   # strictly after 09:30 ⇒ from 09:31
    df_local["hlc3_vol_m"] = df_local["hlc3_vol"].where(after_open, 0.0)
    df_local["vol_m"] = df["volume"].where(after_open, 0.0)
    # cumulative per day
    day = df.index.normalize()
    df_local["cum_hlc3v"] = df_local["hlc3_vol_m"].groupby(day).cumsum()
    df_local["cum_v"] = df_local["vol_m"].groupby(day).cumsum()
    vwap = df_local["cum_hlc3v"] / df_local["cum_v"].replace(0, np.nan)
    vwap.name = "vwap_rth"
    return vwap


# ---------------------------------------------------------------------------
# Feature builder + signal builder (iter_10 spec)
# ---------------------------------------------------------------------------

def build_opening_features(df: pd.DataFrame, vwap: pd.Series) -> pd.DataFrame:
    """Per-day features matching iter_05.build_opening_features.

    Vectorized via groupby.  Same semantics, ~100× faster than the per-date
    O(N²) loop.
    """
    df2 = df.copy()
    df2["vwap_rth"] = vwap
    # Tag each bar with its date and an "is_opening" flag
    t = df2.index.time
    df2["_day"] = df2.index.normalize()
    df2["_is_open"] = (t >= T_OR_START) & (t <= T_OR_END)
    op = df2[df2["_is_open"]].copy()

    g = op.groupby("_day", sort=True)
    out = pd.DataFrame(index=g.size().index.rename("date"))
    out["n_bars"] = g.size()
    out["open_price"] = g["open"].first()
    out["close_price"] = g["close"].last()
    # sig_ts = timestamp of last bar in opening (= 09:45)
    out["sig_ts"] = g.apply(lambda x: x.index[-1])
    out["vwap_at_sig"] = g["vwap_rth"].last()
    out = out[out["n_bars"] >= 2].copy()
    out["rng"] = (out["close_price"] - out["open_price"]).abs()
    out = out[out["rng"] >= 1.0].copy()
    out["direction"] = np.where(out["close_price"] > out["open_price"], 1, -1)
    out["vwap_ok"] = ((out["direction"] == 1) & (out["close_price"] > out["vwap_at_sig"])) | \
                     ((out["direction"] == -1) & (out["close_price"] < out["vwap_at_sig"]))

    # Gap = (today_rth_open - prev_rth_close) / prev_rth_close
    daily_open = df["open"].resample("B").first().dropna()
    daily_close = df["close"].resample("B").last().dropna()
    # build dictionary by date (date naive comparison)
    daily_open.index = pd.DatetimeIndex(daily_open.index).normalize()
    daily_close.index = pd.DatetimeIndex(daily_close.index).normalize()
    prev_close = daily_close.shift(1)
    gap = (daily_open - prev_close) / prev_close
    out["gap_pct"] = gap.reindex(out.index).values

    out["date"] = out.index
    # exit_time = today's 12:30 ET as tz-aware
    def _exit_time(d, sig):
        ts = pd.Timestamp(d.year, d.month, d.day,
                          T_TIME_STOP.hour, T_TIME_STOP.minute, 0,
                          tzinfo=sig.tzinfo)
        return ts
    out["exit_time"] = [
        _exit_time(d, sig) for d, sig in zip(out["date"], out["sig_ts"])
    ]
    out = out.reset_index(drop=True)
    return out[["date", "sig_ts", "direction", "open_price", "close_price",
                "rng", "vwap_at_sig", "vwap_ok", "gap_pct", "exit_time"]]


def build_iter10_signals(feats: pd.DataFrame,
                          range_min_pts: float = RANGE_MIN_PTS,
                          gap_filter: float = GAP_FILTER,
                          sl_cap_pts: float = SL_CAP_PTS) -> pd.DataFrame:
    """Apply iter_10 filters: VWAP confirmation, gap ≤ 1.2%, rng ≥ 30 pts."""
    f = feats.copy()
    # M1: range ≥ 30 pts
    f = f[f["rng"] >= range_min_pts]
    # A: VWAP confirmation
    f = f[f["vwap_ok"]]
    # B: gap ≤ 1.2%
    f = f[f["gap_pct"].abs() <= gap_filter]
    rows = []
    for _, row in f.iterrows():
        rng = float(row["rng"])
        sl_pts = min(rng * SL_RATIO, sl_cap_pts)
        tp_pts = rng * TP_RATIO
        rows.append({
            "signal_ts": row["sig_ts"],
            "direction": int(row["direction"]),
            "tp_points": tp_pts,
            "sl_points": sl_pts,
            "exit_time": row["exit_time"],
            "rng": rng,
            "gap_pct": row["gap_pct"],
            "vwap_at_sig": row["vwap_at_sig"],
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("signal_ts")


# ---------------------------------------------------------------------------
# Engine — replicate engine.py.run() exactly
# ---------------------------------------------------------------------------

def run_signals(rth: pd.DataFrame, signals: pd.DataFrame,
                 cost_rt_usd: float = COST_RT_USD,
                 point_value: float = POINT_VALUE_USD) -> pd.DataFrame:
    """Execute signals on 1-min bars.

    Entry: first bar STRICTLY AFTER signal timestamp (= 09:46).
    Exit: TP or SL first (SL priority within same bar), or time stop at exit_time.
    """
    trades = []
    rth_sorted = rth.sort_index()
    for sig_ts, sig in signals.iterrows():
        direction = int(sig["direction"])
        tp_pts = float(sig["tp_points"])
        sl_pts = float(sig["sl_points"])
        exit_ts = sig["exit_time"]

        future = rth_sorted[rth_sorted.index > sig_ts]
        if future.empty:
            continue
        entry_bar = future.index[0]
        entry_price = float(future.iloc[0]["open"])

        if direction == 1:
            tp_price = entry_price + tp_pts
            sl_price = entry_price - sl_pts
        else:
            tp_price = entry_price - tp_pts
            sl_price = entry_price + sl_pts

        window = rth_sorted[(rth_sorted.index >= entry_bar) &
                             (rth_sorted.index <= exit_ts)]
        exit_price = None
        exit_reason = "time"
        bars_held = 0
        last_bar_ts = entry_bar
        for bar_ts, bar in window.iterrows():
            bars_held += 1
            last_bar_ts = bar_ts
            bar_h = float(bar["high"])
            bar_l = float(bar["low"])
            if direction == 1:
                if bar_l <= sl_price:
                    exit_price = sl_price
                    exit_reason = "sl"
                    break
                if bar_h >= tp_price:
                    exit_price = tp_price
                    exit_reason = "tp"
                    break
            else:
                if bar_h >= sl_price:
                    exit_price = sl_price
                    exit_reason = "sl"
                    break
                if bar_l <= tp_price:
                    exit_price = tp_price
                    exit_reason = "tp"
                    break
        if exit_price is None:
            if window.empty:
                continue
            exit_price = float(window.iloc[-1]["close"])
            exit_reason = "time"
            last_bar_ts = window.index[-1]
        pnl_pts = direction * (exit_price - entry_price)
        pnl_usd = pnl_pts * point_value - cost_rt_usd
        trades.append({
            "signal_ts": sig_ts,
            "entry_ts": entry_bar,
            "exit_ts": last_bar_ts,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "rng": float(sig.get("rng", np.nan)),
            "gap_pct": float(sig.get("gap_pct", np.nan)),
            "tp_pts": tp_pts,
            "sl_pts": sl_pts,
            "pnl_pts": round(pnl_pts, 4),
            "pnl_usd": round(pnl_usd, 2),
            "bars_held": bars_held,
        })
    return pd.DataFrame(trades)


# ---------------------------------------------------------------------------
# Metrics (matches engine.py.metrics + sharpe HAC daily)
# ---------------------------------------------------------------------------

def sharpe_hac_daily(daily_pnl: pd.Series) -> float:
    """HAC-adjusted annualized Sharpe on daily PnL series (USD)."""
    r = daily_pnl.dropna()
    n = len(r)
    if n < 10:
        return float("nan")
    mean = float(r.mean())
    std = float(r.std(ddof=1))
    if std < 1e-9:
        return float("nan")
    if n < 48:
        return mean / std * np.sqrt(252)
    reg = sm.OLS(r, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    lrv = float(reg.cov_params().iloc[0, 0]) * n
    hac_std = np.sqrt(max(lrv, 1e-24))
    if hac_std < 1e-12:
        return float("nan")
    return mean / hac_std * np.sqrt(252)


def metrics(trade_log: pd.DataFrame, rth_total_bars: int | None = None) -> dict:
    if trade_log.empty:
        return {"n_trades": 0}
    tl = trade_log.copy()
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize().dt.tz_localize(None)
    n = len(tl)
    winners = tl[tl["pnl_usd"] > 0]
    losers = tl[tl["pnl_usd"] <= 0]
    win_rate = len(winners) / n if n > 0 else float("nan")
    avg_w = float(winners["pnl_usd"].mean()) if len(winners) > 0 else 0.0
    avg_l = float(losers["pnl_usd"].mean()) if len(losers) > 0 else 0.0
    gross_w = float(winners["pnl_usd"].sum())
    gross_l = abs(float(losers["pnl_usd"].sum()))
    pf = gross_w / gross_l if gross_l > 0 else float("nan")
    # Daily PnL over business days
    daily_pnl = tl.groupby("date")["pnl_usd"].sum()
    all_dates = pd.bdate_range(daily_pnl.index.min(), daily_pnl.index.max())
    daily_pnl = daily_pnl.reindex(all_dates, fill_value=0.0)
    sh = sharpe_hac_daily(daily_pnl)
    cum = daily_pnl.cumsum()
    starting = 25_000.0
    eq = starting + cum
    dd_dollar = eq - eq.cummax()
    dd_pct = dd_dollar / eq.cummax()
    max_dd_pct = float(dd_pct.min()) if len(dd_pct) > 0 else float("nan")
    max_dd_dollar = float(dd_dollar.min()) if len(dd_dollar) > 0 else float("nan")
    return {
        "n_trades": int(n),
        "win_rate": round(float(win_rate), 4),
        "avg_trade_usd": round(float(tl["pnl_usd"].mean()), 2),
        "avg_winner_usd": round(float(avg_w), 2),
        "avg_loser_usd": round(float(avg_l), 2),
        "profit_factor": round(float(pf), 4) if np.isfinite(pf) else None,
        "sharpe_daily_hac": round(float(sh), 4) if np.isfinite(sh) else None,
        "max_dd_pct": round(float(max_dd_pct), 4),
        "max_dd_dollar": round(max_dd_dollar, 2),
        "best_day_usd": round(float(daily_pnl.max()), 2),
        "worst_day_usd": round(float(daily_pnl.min()), 2),
        "avg_bars_held": round(float(tl["bars_held"].mean()), 1),
        "total_pnl_usd": round(float(tl["pnl_usd"].sum()), 2),
    }


def walk_forward(rth: pd.DataFrame, feats: pd.DataFrame,
                  train_months: int = 12, test_months: int = 6,
                  cost_rt_usd: float = COST_RT_USD) -> dict:
    """Rolling WF: train_months in-sample, then test_months OOS, advance test_months."""
    dates = pd.Series(rth.index.normalize().unique()).sort_values()
    if len(dates) == 0:
        return {"n_windows": 0}
    total_m = ((dates.iloc[-1].year - dates.iloc[0].year) * 12 +
                (dates.iloc[-1].month - dates.iloc[0].month))
    windows = []
    start_m = 0
    while start_m + train_months + test_months <= total_m:
        train_start = dates.iloc[0] + pd.DateOffset(months=start_m)
        train_end = train_start + pd.DateOffset(months=train_months)
        test_end = train_end + pd.DateOffset(months=test_months)
        feats_oos = feats[(feats["date"] >= train_end) & (feats["date"] < test_end)]
        if len(feats_oos) < 10:
            start_m += test_months
            continue
        sigs = build_iter10_signals(feats_oos)
        if sigs.empty:
            start_m += test_months
            continue
        rth_oos = rth[(rth.index >= train_end) & (rth.index < test_end)]
        tl = run_signals(rth_oos, sigs, cost_rt_usd=cost_rt_usd)
        if tl.empty:
            start_m += test_months
            continue
        met = metrics(tl)
        windows.append({
            "train_start": str(train_start.date()),
            "train_end": str(train_end.date()),
            "test_end": str(test_end.date()),
            **met,
        })
        start_m += test_months
    if not windows:
        return {"n_windows": 0, "wf_pct_positive": float("nan"), "windows": []}
    pnls = [w.get("total_pnl_usd", 0) for w in windows]
    pct_pos = float(np.mean([p > 0 for p in pnls])) * 100
    return {
        "n_windows": len(windows),
        "wf_pct_positive": round(pct_pos, 1),
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log.info("Loading NQ 1-min RTH...")
    df = load_rth_1min(skip_roll=True)
    log.info(f"  {len(df)} bars, {df.index.min()} -> {df.index.max()}")

    log.info("Precomputing vwap_rth (HLC3×vol cumulative from 09:31)...")
    vwap = precompute_vwap_rth(df)
    log.info(f"  vwap_rth NaN: {vwap.isna().sum()}")

    log.info("Building opening features...")
    feats = build_opening_features(df, vwap)
    log.info(f"  {len(feats)} day-features")

    feats.to_parquet(ROOT / "iter10_features.parquet")

    log.info("Building iter_10 signals (filters: vwap_ok + gap ≤ 1.2% + rng ≥ 30 pts)...")
    sigs = build_iter10_signals(feats)
    log.info(f"  {len(sigs)} signals retained after filters")
    log.info(f"  Retention rate: {len(sigs) / len(feats) * 100:.1f}%")

    print()
    print("=" * 90)
    print("FULL SAMPLE (2010-2026) — iter_10 spec")
    print("=" * 90)
    tl = run_signals(df, sigs, cost_rt_usd=COST_RT_USD)
    met = metrics(tl)
    for k, v in met.items():
        print(f"  {k:25s}: {v}")
    tl.to_parquet(ROOT / "iter10_trades.parquet")
    print()

    # Walk-forward
    print("=" * 90)
    print("WALK-FORWARD — 12m train / 6m test on full sample")
    print("=" * 90)
    wf = walk_forward(df, feats, train_months=12, test_months=6)
    print(f"  n_windows: {wf.get('n_windows', 0)}")
    print(f"  wf_pct_positive: {wf.get('wf_pct_positive', float('nan'))}")
    for w in wf.get("windows", []):
        sr = w.get('sharpe_daily_hac')
        sr_str = f"{sr:+.2f}" if sr is not None else "N/A"
        print(f"  {w['train_end']:>10} -> {w['test_end']:>10}: "
               f"n={w.get('n_trades', 0)}, pnl=${w.get('total_pnl_usd', 0):,.0f}, "
               f"SR={sr_str}")
    print()

    # 2022-2025 anchor (matches Kaggle backtest period)
    print("=" * 90)
    print("RECONCILIATION ANCHOR — 2022-2025 only")
    print("=" * 90)
    feats_2025 = feats[(feats["date"] >= "2022-01-01") & (feats["date"] < "2026-01-01")]
    sigs_2025 = build_iter10_signals(feats_2025)
    df_2025 = df[(df.index >= "2022-01-01") & (df.index < "2026-01-01")]
    tl_2025 = run_signals(df_2025, sigs_2025, cost_rt_usd=COST_RT_USD)
    met_2025 = metrics(tl_2025)
    print(f"  feats: {len(feats_2025)} day-candidates, signals retained: {len(sigs_2025)}")
    for k, v in met_2025.items():
        print(f"  {k:25s}: {v}")
    print()
    print(f"  REPORTED iter_10 (CLAUDE.md): Sharpe 1.52, MaxDD -13.4%, WF 78%, N=346")
