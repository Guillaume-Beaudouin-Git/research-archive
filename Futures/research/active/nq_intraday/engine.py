"""
engine.py — NQ intraday backtest engine
========================================
Shared infrastructure for all nq_intraday iterations.

NQ CONTRACT SPECS:
  Point value : $20 / point
  Tick size   : 0.25 pts = $5
  Cost        : $4.50 commission + 1-tick ($5) slippage = $9.50/side = $19 RT
  RTH         : 09:30-16:00 US/Eastern
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm

log = logging.getLogger(__name__)

POINT_VALUE   = 20.0     # USD per NQ point
TICK_SZ       = 0.25     # minimum tick
COST_RT       = 19.0     # round-trip USD cost (commission + 1-tick slip each side)
RTH_START     = "09:30"
RTH_END       = "16:00"

RESULTS_PATH  = Path(__file__).parent / "results.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rth_mask(df: pd.DataFrame) -> pd.Series:
    """Boolean mask: True for bars inside RTH (09:30-15:59 inclusive)."""
    t = df.index.time
    import datetime
    s = datetime.time(9, 30)
    e = datetime.time(15, 59)
    return pd.Series((t >= s) & (t <= e), index=df.index)


def _daily_series(df: pd.DataFrame) -> pd.Series:
    """Return a series of unique trading dates from tz-aware index."""
    return pd.Series(df.index.normalize().unique())


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class NQBacktestEngine:
    """Reusable NQ 1-min backtest engine."""

    def __init__(self, df_1min: pd.DataFrame):
        """
        df_1min : tz-aware (US/Eastern) DatetimeIndex,
                  columns: open, high, low, close, volume, vwap_rth, vwap_eth
        """
        self.df = df_1min.copy()
        self.rth = self.df[_rth_mask(self.df)].copy()
        log.info(
            "Engine loaded: %d total bars, %d RTH bars, "
            "%s → %s",
            len(self.df), len(self.rth),
            self.df.index[0].date(), self.df.index[-1].date(),
        )

    # ------------------------------------------------------------------
    def resample(self, freq: str, rth_only: bool = True) -> pd.DataFrame:
        """Resample to e.g. '5T', '15T', '30T'. RTH only by default."""
        src = self.rth if rth_only else self.df
        r = src.resample(freq, label="right", closed="right").agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        ).dropna(subset=["open"])
        return r

    # ------------------------------------------------------------------
    def run(self, signals: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
        """
        Execute signals on 1-min bar data.

        signals columns (indexed by signal-fire timestamp):
          direction  : +1 long / -1 short
          tp_points  : take-profit in NQ points
          sl_points  : stop-loss in NQ points (positive value)
          exit_time  : pd.Timestamp for time stop (same date, ET tz)

        Entry: next bar open after signal timestamp.
        Exit : first of TP hit (high/low test), SL hit, time stop (bar close).

        Returns
        -------
        trade_log : DataFrame, one row per trade
        metrics   : dict
        """
        trades: List[dict] = []

        for sig_ts, sig in signals.iterrows():
            direction = int(sig["direction"])
            tp_pts    = float(sig["tp_points"])
            sl_pts    = float(sig["sl_points"])
            exit_ts   = sig["exit_time"]

            # Find entry bar (first bar strictly after signal time)
            future = self.rth[self.rth.index > sig_ts]
            if future.empty:
                continue
            entry_bar  = future.index[0]
            entry_price = float(future.iloc[0]["open"])

            if direction == 1:
                tp_price = entry_price + tp_pts
                sl_price = entry_price - sl_pts
            else:
                tp_price = entry_price - tp_pts
                sl_price = entry_price + sl_pts

            # Walk bars until exit
            window = self.rth[
                (self.rth.index >= entry_bar) &
                (self.rth.index <= exit_ts)
            ]

            exit_price  = None
            exit_reason = "time"
            bars_held   = 0

            for bar_ts, bar in window.iterrows():
                bars_held += 1
                if direction == 1:
                    if float(bar["low"])  <= sl_price:
                        exit_price  = sl_price
                        exit_reason = "sl"
                        break
                    if float(bar["high"]) >= tp_price:
                        exit_price  = tp_price
                        exit_reason = "tp"
                        break
                else:
                    if float(bar["high"]) >= sl_price:
                        exit_price  = sl_price
                        exit_reason = "sl"
                        break
                    if float(bar["low"])  <= tp_price:
                        exit_price  = tp_price
                        exit_reason = "tp"
                        break

            if exit_price is None:
                # Time stop: exit at last bar close in window
                if window.empty:
                    continue
                exit_price  = float(window.iloc[-1]["close"])
                exit_reason = "time"

            pnl_pts = direction * (exit_price - entry_price)
            pnl_usd = pnl_pts * POINT_VALUE - COST_RT

            trades.append({
                "signal_ts":   sig_ts,
                "entry_ts":    entry_bar,
                "exit_ts":     window.index[-1] if exit_reason == "time"
                               else bar_ts,
                "direction":   direction,
                "entry_price": entry_price,
                "exit_price":  exit_price,
                "exit_reason": exit_reason,
                "pnl_pts":     round(pnl_pts, 4),
                "pnl_usd":     round(pnl_usd, 2),
                "bars_held":   bars_held,
                "tp_pts":      tp_pts,
                "sl_pts":      sl_pts,
            })

        trade_log = pd.DataFrame(trades)
        metrics   = self.metrics(trade_log) if len(trade_log) > 0 else {}
        return trade_log, metrics

    # ------------------------------------------------------------------
    def metrics(self, trade_log: pd.DataFrame) -> dict:
        """Compute standard performance metrics from trade_log."""
        if trade_log.empty:
            return {"n_trades": 0}

        tl = trade_log.copy()
        tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()

        n       = len(tl)
        winners = tl[tl["pnl_usd"] > 0]
        losers  = tl[tl["pnl_usd"] <= 0]

        win_rate = len(winners) / n if n > 0 else np.nan
        avg_w    = winners["pnl_usd"].mean() if len(winners) > 0 else 0.0
        avg_l    = losers["pnl_usd"].mean()  if len(losers)  > 0 else 0.0
        gross_w  = winners["pnl_usd"].sum()
        gross_l  = abs(losers["pnl_usd"].sum())
        pf       = gross_w / gross_l if gross_l > 0 else np.nan

        # Daily P&L → Sharpe
        daily_pnl = tl.groupby("date")["pnl_usd"].sum()
        # Re-index to all trading days in the sample
        all_dates = pd.bdate_range(
            tl["date"].min(), tl["date"].max(), freq="C",
            holidays=[]
        )
        daily_pnl = daily_pnl.reindex(
            pd.DatetimeIndex(all_dates).normalize(), fill_value=0.0
        )
        sharpe_d = self._sharpe_hac_daily(daily_pnl)

        # Drawdown on cumulative P&L
        cum = daily_pnl.cumsum()
        dd  = (cum - cum.cummax()) / max(cum.cummax().max(), 1.0)
        max_dd = float(dd.min()) if len(dd) > 0 else np.nan

        # Pct time in market
        total_rth_bars = len(self.rth)
        bars_in_mkt    = tl["bars_held"].sum()
        pct_in_mkt     = bars_in_mkt / total_rth_bars if total_rth_bars > 0 else np.nan

        return {
            "n_trades":        int(n),
            "win_rate":        round(float(win_rate), 4),
            "avg_trade_usd":   round(float(tl["pnl_usd"].mean()), 2),
            "avg_winner_usd":  round(float(avg_w), 2),
            "avg_loser_usd":   round(float(avg_l), 2),
            "profit_factor":   round(float(pf), 4) if np.isfinite(pf) else None,
            "sharpe_daily_hac":round(float(sharpe_d), 4) if np.isfinite(sharpe_d) else None,
            "max_dd_pct":      round(float(max_dd), 4),
            "best_day_usd":    round(float(daily_pnl.max()), 2),
            "worst_day_usd":   round(float(daily_pnl.min()), 2),
            "pct_time_in_mkt": round(float(pct_in_mkt), 4),
            "avg_bars_held":   round(float(tl["bars_held"].mean()), 1),
            "total_pnl_usd":   round(float(tl["pnl_usd"].sum()), 2),
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _sharpe_hac_daily(daily_pnl: pd.Series) -> float:
        """
        HAC-adjusted annualised Sharpe on daily P&L dollar series.
        LRV formula: LRV = cov_params[0,0] × n.
        Falls back to plain if n < 48.
        """
        r = daily_pnl.dropna()
        n = len(r)
        if n < 10:
            return np.nan
        mean = float(r.mean())
        std  = float(r.std(ddof=1))
        if std < 1e-9:
            return np.nan
        if n < 48:
            return mean / std * np.sqrt(252)
        reg = sm.OLS(r, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
        lrv     = float(reg.cov_params().iloc[0, 0]) * n
        hac_std = np.sqrt(max(lrv, 1e-24))
        if hac_std < 1e-12:
            return np.nan
        return mean / hac_std * np.sqrt(252)

    # ------------------------------------------------------------------
    def walk_forward(
        self,
        signal_fn: Callable[[pd.DataFrame, dict], pd.DataFrame],
        params:       dict,
        train_months: int = 12,
        test_months:  int = 6,
    ) -> dict:
        """
        Rolling walk-forward.
        signal_fn(df_1min_window, params) -> signals DataFrame
        Returns per-window metrics + aggregate pct_positive.
        """
        dates    = pd.Series(
            self.rth.index.normalize().unique()
        ).sort_values()
        total_m  = (dates.iloc[-1].year  - dates.iloc[0].year) * 12 + \
                   (dates.iloc[-1].month - dates.iloc[0].month)

        windows: List[dict] = []
        start_m = 0
        while start_m + train_months + test_months <= total_m:
            train_start = dates.iloc[0] + pd.DateOffset(months=start_m)
            train_end   = train_start   + pd.DateOffset(months=train_months)
            test_end    = train_end     + pd.DateOffset(months=test_months)

            oos = self.rth[
                (self.rth.index >= train_end) &
                (self.rth.index <  test_end)
            ]
            if len(oos) < 100:
                start_m += test_months
                continue

            eng_oos = NQBacktestEngine.__new__(NQBacktestEngine)
            eng_oos.df  = oos
            eng_oos.rth = oos

            try:
                sigs = signal_fn(oos, params)
                if sigs.empty:
                    start_m += test_months
                    continue
                _, met = eng_oos.run(sigs)
                windows.append({
                    "train_start": str(train_start.date()),
                    "train_end":   str(train_end.date()),
                    "test_end":    str(test_end.date()),
                    **met,
                })
            except Exception as e:
                log.warning("WF window failed: %s", e)

            start_m += test_months

        if not windows:
            return {"n_windows": 0, "wf_pct_positive": np.nan, "windows": []}

        pnls    = [w.get("total_pnl_usd", 0) for w in windows]
        pct_pos = float(np.mean([p > 0 for p in pnls])) * 100
        return {
            "n_windows":        len(windows),
            "wf_pct_positive":  round(pct_pos, 1),
            "windows":          windows,
        }

    # ------------------------------------------------------------------
    def bootstrap_ev(
        self,
        trade_log: pd.DataFrame,
        n_boot:    int = 10_000,
    ) -> dict:
        """
        Bootstrap expected value test.
        Returns: p_ev_zero (P(EV ≤ 0)), ci_low, ci_high (95%).
        """
        if trade_log.empty:
            return {"p_ev_zero": np.nan, "ci_low": np.nan, "ci_high": np.nan}
        pnls = trade_log["pnl_usd"].values
        rng  = np.random.default_rng(42)
        boot_means = np.array([
            rng.choice(pnls, size=len(pnls), replace=True).mean()
            for _ in range(n_boot)
        ])
        p_ev_zero = float((boot_means <= 0).mean())
        ci_low    = float(np.percentile(boot_means, 2.5))
        ci_high   = float(np.percentile(boot_means, 97.5))
        return {
            "p_ev_zero": round(p_ev_zero, 4),
            "ci_low":    round(ci_low, 2),
            "ci_high":   round(ci_high, 2),
        }


# ---------------------------------------------------------------------------
# Results store
# ---------------------------------------------------------------------------

def append_result(result: dict) -> None:
    """Append one iteration result to results.json."""
    existing: List[dict] = []
    if RESULTS_PATH.exists():
        try:
            existing = json.loads(RESULTS_PATH.read_text())
        except Exception:
            existing = []
    # Replace if same iteration key already exists
    key = result.get("iteration", "")
    existing = [r for r in existing if r.get("iteration") != key]
    existing.append(result)
    RESULTS_PATH.write_text(json.dumps(existing, indent=2))
    log.info("Saved result → %s  [%s]", RESULTS_PATH.name, key)


def load_results() -> List[dict]:
    if not RESULTS_PATH.exists():
        return []
    try:
        return json.loads(RESULTS_PATH.read_text())
    except Exception:
        return []


def print_comparison_table(results: List[dict]) -> None:
    """Print a sorted comparison table of all variants."""
    if not results:
        print("No results yet.")
        return
    rows = sorted(results, key=lambda r: r.get("sharpe_daily_hac") or -99, reverse=True)
    print("\n" + "=" * 100)
    print(f"{'Iter':<8} {'N':>5} {'WR':>6} {'AvgTrd':>8} {'PF':>6} "
          f"{'Sharpe':>8} {'MaxDD':>8} {'WF%':>6} {'P(EV≤0)':>8} {'Verdict':<10}")
    print("-" * 100)
    for r in rows:
        print(
            f"{r.get('iteration','?'):<8} "
            f"{r.get('n_trades',0):>5} "
            f"{r.get('win_rate',0)*100:>5.1f}% "
            f"{r.get('avg_trade_usd',0):>8.1f} "
            f"{r.get('profit_factor') or 0:>6.3f} "
            f"{r.get('sharpe_daily_hac') or 0:>8.3f} "
            f"{r.get('max_dd_pct',0)*100:>7.1f}% "
            f"{r.get('wf_pct_positive') or 0:>5.1f}% "
            f"{r.get('p_ev_zero') or 1:>8.3f} "
            f"{r.get('verdict','?'):<10}"
        )
    print("=" * 100)
