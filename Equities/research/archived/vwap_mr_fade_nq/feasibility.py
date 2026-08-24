"""
VWAP MR Fade NQ — Feasibility backtest.

Pre-spec: Equities/research/active/vwap_mr_fade_nq/prespec.md
Reference: Adams-Dim-Eraker-Fontaine-Ornthanalai-Vilkov 2025 SSRN 5641974

Signal (pre-registered):
  dev = close - vwap_rth
  sigma_30 = rolling 30-bar std(dev)
  Z = dev / sigma_30
  Entry: |Z[T]| > 2.0, FADE direction, at open[T+1]
  TP:   |Z| ≤ 0.5  → exit at open[T'+1]
  SL:   |Z| > |Z_entry| + 1.0 → exit at open[T'+1]
  Time: 30 bars after entry → exit at open[T_entry+31]

Windows (pre-registered):
  VARIANT_A: 10:30–15:00 ET
  VARIANT_B: 10:00–15:30 ET

Cost: $1.80 RT MNQ = 0.9 NQ pts
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parents[4]))
from Equities.research.active.vwap_mr_fade_nq.data_setup import load_nq_rth, validate_data

# ── Constants (pre-registered, do not modify post-failure) ──────────────────
Z_ENTRY_THRESHOLD = 2.0
Z_TP_THRESHOLD = 0.5
Z_SL_EXTENSION = 1.0
TIME_STOP_BARS = 30
COST_RT_PTS = 0.9  # $1.80 / $2.00 per MNQ pt
SIGMA_WINDOW = 30

WINDOWS: dict[str, tuple[str, str]] = {
    "VARIANT_A": ("10:30", "15:00"),
    "VARIANT_B": ("10:00", "15:30"),
}


def compute_z_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add deviation, sigma_30, and Z columns. Per-session rolling to avoid cross-day contamination."""
    out = df.copy()
    out["dev"] = out["close"] - out["vwap_rth"]

    def _rolling_std(grp: pd.DataFrame) -> pd.Series:
        return grp["dev"].rolling(SIGMA_WINDOW, min_periods=SIGMA_WINDOW).std()

    out["sigma_30"] = out.groupby(out.index.date, group_keys=False).apply(_rolling_std)
    out["Z"] = out["dev"] / out["sigma_30"]
    return out


def _simulate_trades(
    df_day: pd.DataFrame,
    entry_start: str,
    entry_end: str,
) -> list[dict]:
    """Simulate trades for a single session. Signal on bar T, entry at open[T+1]."""
    bars = df_day.reset_index()
    n = len(bars)
    trades = []
    in_trade = False
    entry_bar_idx = -1
    entry_price = np.nan
    direction = 0  # +1 long, -1 short
    z_entry_abs = np.nan

    # Eligible entry window (time of bar T)
    entry_start_t = pd.Timestamp(entry_start).time()
    entry_end_t = pd.Timestamp(entry_end).time()

    for i in range(n - 1):  # need T+1 for entry/exit price
        bar = bars.iloc[i]
        bar_time = bar["timestamp_et"].time()
        z = bar["Z"]

        if in_trade:
            bars_held = i - entry_bar_idx
            z_abs = abs(z)

            tp_hit = z_abs <= Z_TP_THRESHOLD
            sl_hit = z_abs > z_entry_abs + Z_SL_EXTENSION
            time_hit = bars_held >= TIME_STOP_BARS

            if tp_hit or sl_hit or time_hit:
                exit_price = bars.iloc[i + 1]["open"]
                pnl_pts = (exit_price - entry_price) * direction - COST_RT_PTS
                reason = "TP" if tp_hit else ("SL" if sl_hit else "TIME")
                trades.append(
                    {
                        "entry_time": bars.iloc[entry_bar_idx + 1]["timestamp_et"],
                        "exit_time": bars.iloc[i + 1]["timestamp_et"],
                        "direction": direction,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "z_entry": z_entry_abs * direction,
                        "z_exit": z,
                        "bars_held": bars_held,
                        "pnl_pts": pnl_pts,
                        "pnl_usd": pnl_pts * 2.0,
                        "exit_reason": reason,
                    }
                )
                in_trade = False

        if not in_trade and not np.isnan(z):
            in_window = entry_start_t <= bar_time <= entry_end_t
            if in_window and abs(z) > Z_ENTRY_THRESHOLD:
                dir_ = -1 if z > 0 else 1  # FADE: short if Z>2, long if Z<-2
                entry_price = bars.iloc[i + 1]["open"]
                direction = dir_
                z_entry_abs = abs(z)
                entry_bar_idx = i
                in_trade = True

    # Force-close at last bar if still open
    if in_trade and entry_bar_idx < n - 1:
        exit_price = bars.iloc[-1]["close"]
        pnl_pts = (exit_price - entry_price) * direction - COST_RT_PTS
        bars_held = (n - 1) - entry_bar_idx
        trades.append(
            {
                "entry_time": bars.iloc[entry_bar_idx + 1]["timestamp_et"],
                "exit_time": bars.iloc[-1]["timestamp_et"],
                "direction": direction,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "z_entry": z_entry_abs * direction,
                "z_exit": bars.iloc[-1]["Z"],
                "bars_held": bars_held,
                "pnl_pts": pnl_pts,
                "pnl_usd": pnl_pts * 2.0,
                "exit_reason": "EOD",
            }
        )

    return trades


def run_backtest(
    df: pd.DataFrame,
    variant: Literal["VARIANT_A", "VARIANT_B"],
    canary: bool = False,
) -> dict:
    """Run the VWAP MR fade backtest for a given variant.

    Args:
        df: RTH bars with Z-score columns (from compute_z_scores).
        variant: VARIANT_A or VARIANT_B.
        canary: If True, restrict to 2024 data only.
    """
    entry_start, entry_end = WINDOWS[variant]

    if canary:
        df = df[df.index.year == 2024]

    all_trades: list[dict] = []
    for date, grp in df.groupby(df.index.date):
        day_trades = _simulate_trades(grp, entry_start, entry_end)
        all_trades.extend(day_trades)

    if not all_trades:
        return {"variant": variant, "canary": canary, "n_trades": 0, "error": "no_trades"}

    tdf = pd.DataFrame(all_trades)
    tdf["date"] = pd.to_datetime(tdf["entry_time"]).dt.date

    # Daily P&L for Sharpe
    daily_pnl = tdf.groupby("date")["pnl_pts"].sum()
    n_days = (daily_pnl.index[-1] - daily_pnl.index[0]).days + 1
    # Annualise: fill missing days with 0
    idx = pd.date_range(daily_pnl.index[0], daily_pnl.index[-1], freq="D")
    daily_pnl_full = daily_pnl.reindex(idx, fill_value=0.0)

    mean_d = daily_pnl_full.mean()
    std_d = daily_pnl_full.std(ddof=1)
    sharpe = (mean_d / std_d * np.sqrt(252)) if std_d > 0 else 0.0

    # HAC Sharpe (Newey-West lag-6)
    try:
        import statsmodels.api as sm

        pnl_arr = daily_pnl_full.values.astype(float)
        ones = np.ones(len(pnl_arr))
        ols = sm.OLS(pnl_arr, ones).fit(
            cov_type="HAC", cov_kwds={"maxlags": 6}
        )
        t_hac = float(ols.tvalues[0])
        sharpe_hac = t_hac / np.sqrt(len(pnl_arr) / 252)
    except Exception:
        t_hac = float("nan")
        sharpe_hac = float("nan")

    # Cumulative P&L for MaxDD
    cum = daily_pnl_full.cumsum()
    rolling_max = cum.cummax()
    dd = (cum - rolling_max)
    max_dd_pts = float(dd.min())

    n_trades = len(tdf)
    winners = tdf[tdf["pnl_pts"] > 0]
    losers = tdf[tdf["pnl_pts"] <= 0]
    win_rate = len(winners) / n_trades if n_trades > 0 else 0.0

    exit_reasons = tdf["exit_reason"].value_counts().to_dict()

    return {
        "variant": variant,
        "canary": canary,
        "period_start": str(tdf["date"].min()),
        "period_end": str(tdf["date"].max()),
        "n_trades": n_trades,
        "n_trading_days": int(len(daily_pnl)),
        "win_rate": round(win_rate, 4),
        "avg_win_pts": round(float(winners["pnl_pts"].mean()), 3) if len(winners) else None,
        "avg_loss_pts": round(float(losers["pnl_pts"].mean()), 3) if len(losers) else None,
        "avg_bars_held": round(float(tdf["bars_held"].mean()), 1),
        "sharpe_naive": round(sharpe, 3),
        "sharpe_hac": round(sharpe_hac, 3),
        "t_hac": round(t_hac, 3),
        "max_dd_pts": round(max_dd_pts, 2),
        "total_pnl_pts": round(float(tdf["pnl_pts"].sum()), 2),
        "total_pnl_usd": round(float(tdf["pnl_usd"].sum()), 2),
        "exit_reasons": exit_reasons,
    }


def print_report(res: dict) -> None:
    label = f"{res['variant']} {'[CANARY 2024]' if res['canary'] else '[FULL]'}"
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    if "error" in res:
        print(f"  ERROR: {res['error']}")
        return
    print(f"  Period:        {res['period_start']} → {res['period_end']}")
    print(f"  N trades:      {res['n_trades']}")
    print(f"  Win rate:      {res['win_rate']:.1%}")
    print(f"  Avg win:       {res['avg_win_pts']} pts")
    print(f"  Avg loss:      {res['avg_loss_pts']} pts")
    print(f"  Avg hold:      {res['avg_bars_held']} bars")
    print(f"  Sharpe naive:  {res['sharpe_naive']}")
    print(f"  Sharpe HAC:    {res['sharpe_hac']}  (t={res['t_hac']})")
    print(f"  MaxDD:         {res['max_dd_pts']} pts")
    print(f"  Total P&L:     {res['total_pnl_pts']} pts / ${res['total_pnl_usd']:.0f}")
    print(f"  Exit reasons:  {res['exit_reasons']}")


def main() -> None:
    print("Loading NQ 1-min RTH data...")
    df = load_nq_rth()
    stats = validate_data(df)
    print(f"\n── Data validation ──")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n\nComputing Z-scores (per-session rolling)...")
    df = compute_z_scores(df)
    valid = df["Z"].notna().sum()
    print(f"  Valid Z-score bars: {valid:,} / {len(df):,}")

    # ── STOP-POINT 1 ──────────────────────────────────────────
    print("\n\n── STOP-POINT 1: Data & Z-score ✓ ──")
    print("  Awaiting STOP-POINT 2: Canary 2024 backtest")

    # ── STOP-POINT 2: Canary 2024 ─────────────────────────────
    results_canary = {}
    for variant in ("VARIANT_A", "VARIANT_B"):
        res = run_backtest(df, variant, canary=True)
        print_report(res)
        results_canary[variant] = res

    out_path = Path(__file__).parent / "analysis" / "canary_results.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results_canary, f, indent=2, default=str)
    print(f"\nCanary results saved → {out_path}")

    # ── STOP-POINT 3 check (gate before full backtest) ─────────
    print("\n\n── STOP-POINT 2 gate check ──")
    va = results_canary.get("VARIANT_A", {})
    vb = results_canary.get("VARIANT_B", {})

    any_canary_pass = (
        (va.get("n_trades", 0) >= 50)
        and (va.get("sharpe_naive", -99) > 0 or vb.get("sharpe_naive", -99) > 0)
    )
    print(f"  VARIANT_A: N={va.get('n_trades')}, SR={va.get('sharpe_naive')}, WR={va.get('win_rate')}")
    print(f"  VARIANT_B: N={vb.get('n_trades')}, SR={vb.get('sharpe_naive')}, WR={vb.get('win_rate')}")
    print(f"\n  Canary pipeline pass (any SR>0, N≥50): {any_canary_pass}")
    print("\nSTOP — review canary results above before running full backtest.")
    print("If pipeline looks correct, re-run with --full flag:")
    print("  python -m Equities.research.active.vwap_mr_fade_nq.feasibility --full")


def run_full() -> None:
    """Full 2023-2025 backtest. Run only after canary validation."""
    print("Loading NQ 1-min RTH data (full 2023-2025)...")
    df = load_nq_rth()
    df = df[df.index.year >= 2023]
    df = compute_z_scores(df)

    results_full = {}
    for variant in ("VARIANT_A", "VARIANT_B"):
        res = run_backtest(df, variant, canary=False)
        print_report(res)
        results_full[variant] = res

    out_path = Path(__file__).parent / "analysis" / "full_results.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results_full, f, indent=2, default=str)
    print(f"\nFull results saved → {out_path}")


if __name__ == "__main__":
    if "--full" in sys.argv:
        run_full()
    else:
        main()
