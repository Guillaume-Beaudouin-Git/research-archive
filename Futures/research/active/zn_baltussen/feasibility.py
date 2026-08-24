"""
Baltussen 2021 ZN intraday momentum — feasibility backtest.

H1: all days, Baltussen pure signal
H2: event-conditional days only (FOMC/NFP/CPI/PCE)
H3: sub-period stability (2018-2021 vs 2022-2025)

Run:  python -m Futures.research.active.zn_baltussen.feasibility [--canary]
      --canary : run on available 1h data only (canary mode, STOP-POINT 2)
      (default): full run 2018-2025 (requires 1-min data, STOP-POINT 3)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_REPO = Path(__file__).parents[4]
sys.path.insert(0, str(_REPO))

from Futures.research.active.zn_baltussen.data_setup import (
    DataSource,
    ZN_POINT_VALUE,
    ZN_TICK_VALUE,
    build_macro_calendar,
    compute_session_features,
    load_vix,
    load_zn_intraday,
)
from Portfolio.reporting.metrics import (
    compute_all_metrics,
    fetch_risk_free,
    hac_sharpe_ratio,
    to_excess_returns,
)
from Portfolio.reporting.metrics import compute_psr_dsr

log = logging.getLogger(__name__)

# ── cost / risk constants ─────────────────────────────────────────────────────
COST_RT_USD: float  = 20.0    # round-trip: commission + 0.5-tick spread
COST_RT_STRESS: float = 35.0  # stress scenario
SL_TICKS: int       = 8       # hard stop: 8 ticks = $125
VIX_SKIP: float     = 25.0    # skip day if VIX close > threshold
ACCOUNT_SIZE: float = 50_000.0
N_TRIALS_DSR: int   = 180     # global n_tests for DSR (see CLAUDE.md research history + this run)

RESULTS_PATH = Path(__file__).parent / "analysis" / "results.json"

# ── walk-forward parameters ───────────────────────────────────────────────────
WF_N_FOLDS: int = 5


# ── single-trade P&L ─────────────────────────────────────────────────────────

def _pnl_single_trade(
    direction: int,
    entry: float,
    exit_proxy: float,
    bar_high: float,
    bar_low: float,
    cost_rt: float,
) -> float:
    """
    Compute net P&L in USD for one ZN trade.

    Parameters
    ----------
    direction   : +1 (long) or -1 (short)
    entry       : entry price (Open of 15:00 bar)
    exit_proxy  : target exit price (15:30 proxy)
    bar_high    : High of the 15:00-16:00 bar (for SL check on short)
    bar_low     : Low  of the 15:00-16:00 bar (for SL check on long)
    cost_rt     : round-trip cost in USD

    Returns
    -------
    float : net P&L in USD per contract
    """
    sl_pts = SL_TICKS * (1.0 / 64.0)

    if direction == 1:
        sl_price = entry - sl_pts
        if bar_low <= sl_price:
            gross = (sl_price - entry) * ZN_POINT_VALUE
        else:
            gross = (exit_proxy - entry) * ZN_POINT_VALUE
    else:
        sl_price = entry + sl_pts
        if bar_high >= sl_price:
            gross = (entry - sl_price) * ZN_POINT_VALUE
        else:
            gross = (entry - exit_proxy) * ZN_POINT_VALUE

    return gross - cost_rt


# ── backtest core ─────────────────────────────────────────────────────────────

def run_backtest(
    sessions: pd.DataFrame,
    df_1h: pd.DataFrame,
    cost_rt: float = COST_RT_USD,
    event_only: bool = False,
    vix_skip: float = VIX_SKIP,
) -> pd.Series:
    """
    Simulate the Baltussen 30-min signal over a session DataFrame.

    Parameters
    ----------
    sessions    : output of compute_session_features(), index = date
    df_1h       : raw intraday bars (tz-aware US/Eastern) for SL computation
    cost_rt     : round-trip cost in USD
    event_only  : if True, only trade on is_event_day == True
    vix_skip    : skip day if VIX close exceeds this level

    Returns
    -------
    pd.Series
        Daily P&L in USD, index = date. NaN for skipped days.
    """
    tz = "America/New_York"
    if df_1h.index.tz is None:
        df_1h = df_1h.copy()
        df_1h.index = df_1h.index.tz_localize(tz)
    else:
        df_1h = df_1h.copy()
        df_1h.index = df_1h.index.tz_convert(tz)

    pnl_rows: list[tuple] = []

    for date, row in sessions.iterrows():
        # Filters
        if vix_skip > 0 and row["vix_close"] > vix_skip:
            continue
        if event_only and not row["is_event_day"]:
            continue

        direction   = int(row["direction"])
        entry       = float(row["p_1500"])
        exit_proxy  = float(row["p_exit_proxy"])

        # Retrieve bar High/Low for intra-bar SL approximation
        d_ts    = pd.Timestamp(date, tz=tz)
        bar_idx = d_ts.replace(hour=15, minute=0)
        bar_window = df_1h.loc[
            (df_1h.index >= bar_idx) &
            (df_1h.index < bar_idx + pd.Timedelta(hours=1))
        ]

        if bar_window.empty or entry <= 0:
            continue

        bar_high = float(bar_window["high"].max())
        bar_low  = float(bar_window["low"].min())

        pnl_usd = _pnl_single_trade(
            direction, entry, exit_proxy, bar_high, bar_low, cost_rt
        )
        pnl_rows.append((date, pnl_usd))

    if not pnl_rows:
        return pd.Series(dtype=float, name="pnl_usd")

    pnl = pd.Series(
        {d: v for d, v in pnl_rows},
        name="pnl_usd",
    )
    pnl.index = pd.DatetimeIndex(pnl.index)
    return pnl.sort_index()


def _pnl_to_returns(pnl: pd.Series, account_size: float = ACCOUNT_SIZE) -> pd.Series:
    """Convert dollar P&L to daily return fraction (P&L / account_size)."""
    r = pnl / account_size
    r.name = "returns"
    return r


def _compute_metrics_block(
    pnl: pd.Series,
    label: str,
    n_trials: int = N_TRIALS_DSR,
) -> dict:
    """Compute full metric suite for a P&L series."""
    if pnl.empty or len(pnl) < 10:
        return {"label": label, "verdict": "INSUFFICIENT_DATA", "n_trades": len(pnl)}

    returns = _pnl_to_returns(pnl)
    rf = fetch_risk_free(returns.index.min(), returns.index.max())
    metrics = compute_all_metrics(returns, benchmark=None, n_trials=n_trials, rf=rf)

    win_rate = float((pnl > 0).mean())
    avg_win  = float(pnl[pnl > 0].mean()) if (pnl > 0).any() else np.nan
    avg_loss = float(pnl[pnl < 0].mean()) if (pnl < 0).any() else np.nan

    return {
        "label":          label,
        "n_trades":       len(pnl),
        "sharpe_hac":     round(float(metrics["sharpe_hac"]), 3),
        "sharpe_t_stat":  round(float(metrics["sharpe_t_stat"]), 3),
        "max_dd":         round(float(metrics["max_dd"]) * 100, 2),
        "ann_return_pct": round(float(metrics["ann_return"]) * 100, 2),
        "win_rate":       round(win_rate, 3),
        "avg_win_usd":    round(avg_win, 2) if not np.isnan(avg_win) else None,
        "avg_loss_usd":   round(avg_loss, 2) if not np.isnan(avg_loss) else None,
        "dsr":            round(float(metrics["dsr"]), 4),
        "dsr_verdict":    metrics["dsr_verdict"],
        "pct_pos_months": round(float(metrics["pct_pos_months"]), 3),
        "n_trials_dsr":   n_trials,
    }


# ── H1: all days ──────────────────────────────────────────────────────────────

def run_h1(
    sessions: pd.DataFrame,
    df_1h: pd.DataFrame,
    cost_rt: float = COST_RT_USD,
) -> dict:
    """H1 — Baltussen pure signal, all non-filtered days."""
    pnl = run_backtest(sessions, df_1h, cost_rt=cost_rt, event_only=False)
    metrics = _compute_metrics_block(pnl, label="H1_all_days")
    metrics["cost_rt_usd"] = cost_rt

    # Gate check
    sr  = metrics.get("sharpe_hac", 0)
    wr  = metrics.get("win_rate", 0)
    n   = metrics.get("n_trades", 0)
    metrics["h1_gate"] = (
        "PASS" if sr >= 1.0 and wr >= 0.53 and n >= 1800 else "FAIL"
    )
    log.info("H1: SR=%.2f WR=%.1f%% N=%d → %s",
             sr, wr * 100, n, metrics["h1_gate"])
    return metrics


# ── H2: event-conditional ─────────────────────────────────────────────────────

def run_h2(
    sessions: pd.DataFrame,
    df_1h: pd.DataFrame,
    cost_rt: float = COST_RT_USD,
) -> dict:
    """H2 — Signal restricted to macro event days."""
    pnl = run_backtest(sessions, df_1h, cost_rt=cost_rt, event_only=True)
    metrics = _compute_metrics_block(pnl, label="H2_event_conditional")
    metrics["cost_rt_usd"] = cost_rt

    event_counts = sessions[sessions["is_event_day"]]["event_type"].value_counts().to_dict()
    metrics["event_type_counts"] = event_counts

    sr  = metrics.get("sharpe_hac", 0)
    wr  = metrics.get("win_rate", 0)
    n   = metrics.get("n_trades", 0)
    metrics["h2_gate"] = (
        "PASS" if sr >= 1.3 and wr >= 0.55 and n >= 350 else "FAIL"
    )
    log.info("H2: SR=%.2f WR=%.1f%% N=%d → %s",
             sr, wr * 100, n, metrics["h2_gate"])
    return metrics


# ── H3: sub-period stability ──────────────────────────────────────────────────

def run_h3(
    sessions: pd.DataFrame,
    df_1h: pd.DataFrame,
    cost_rt: float = COST_RT_USD,
) -> dict:
    """H3 — Sub-period stability: low-rates (2018-2021) vs QT (2022-2025)."""
    cut = pd.Timestamp("2022-01-01")

    sess_a = sessions[sessions.index < cut]
    sess_b = sessions[sessions.index >= cut]

    df_a = df_1h[df_1h.index.year < 2022] if not df_1h.empty else df_1h
    df_b = df_1h[df_1h.index.year >= 2022] if not df_1h.empty else df_1h

    pnl_a = run_backtest(sess_a, df_a, cost_rt=cost_rt, event_only=False)
    pnl_b = run_backtest(sess_b, df_b, cost_rt=cost_rt, event_only=False)

    m_a = _compute_metrics_block(pnl_a, label="H3_2018_2021")
    m_b = _compute_metrics_block(pnl_b, label="H3_2022_2025")

    sr_a = m_a.get("sharpe_hac", 0) or 0
    sr_b = m_b.get("sharpe_hac", 0) or 0
    decay_ratio = (sr_b / sr_a) if sr_a > 0 else np.nan

    h3_gate = "PASS" if (not np.isnan(decay_ratio) and decay_ratio >= 0.60) else "FAIL"
    log.info("H3: SR_A=%.2f SR_B=%.2f decay=%.2f → %s",
             sr_a, sr_b, decay_ratio, h3_gate)

    return {
        "label":       "H3_sub_period",
        "period_a":    m_a,
        "period_b":    m_b,
        "sr_a":        round(sr_a, 3),
        "sr_b":        round(sr_b, 3),
        "decay_ratio": round(float(decay_ratio), 3) if not np.isnan(decay_ratio) else None,
        "h3_gate":     h3_gate,
    }


# ── walk-forward ──────────────────────────────────────────────────────────────

def run_walk_forward(
    sessions: pd.DataFrame,
    df_1h: pd.DataFrame,
    n_folds: int = WF_N_FOLDS,
    cost_rt: float = COST_RT_USD,
    event_only: bool = False,
) -> dict:
    """
    Expanding-window walk-forward (n_folds folds).
    Each fold: train = all prior data, test = next T/n_folds period.
    No training needed (fixed-parameter signal) — test Sharpe recorded per fold.
    """
    dates = sessions.index.sort_values()
    n     = len(dates)
    fold_size = n // n_folds

    fold_results: list[dict] = []
    positive_folds = 0

    for k in range(n_folds):
        test_start = dates[k * fold_size]
        test_end   = dates[min((k + 1) * fold_size - 1, n - 1)]
        test_sess  = sessions.loc[test_start:test_end]
        test_df    = df_1h.loc[
            df_1h.index.normalize() >= pd.Timestamp(test_start, tz=df_1h.index.tz)
        ].loc[
            df_1h.index.normalize() <= pd.Timestamp(test_end, tz=df_1h.index.tz) + pd.Timedelta(days=1)
        ] if not df_1h.empty else df_1h

        pnl = run_backtest(test_sess, test_df, cost_rt=cost_rt, event_only=event_only)
        if pnl.empty or len(pnl) < 5:
            fold_results.append({
                "fold": k + 1,
                "test_start": str(test_start.date()),
                "test_end":   str(test_end.date()),
                "n_trades":   0,
                "sharpe":     None,
                "positive":   None,
            })
            continue

        returns = _pnl_to_returns(pnl)
        r_excess = to_excess_returns(returns)
        sr, _, _ = hac_sharpe_ratio(r_excess)
        is_pos = bool(sr > 0)
        if is_pos:
            positive_folds += 1

        fold_results.append({
            "fold":       k + 1,
            "test_start": str(test_start.date()),
            "test_end":   str(test_end.date()),
            "n_trades":   len(pnl),
            "sharpe":     round(float(sr), 3),
            "positive":   is_pos,
        })
        log.info("WF fold %d/%d: %s→%s N=%d SR=%.2f",
                 k + 1, n_folds, test_start.date(), test_end.date(), len(pnl), sr)

    valid_folds = [f for f in fold_results if f["sharpe"] is not None]
    wf_pct = (positive_folds / len(valid_folds) * 100) if valid_folds else 0.0

    return {
        "n_folds":       n_folds,
        "positive_folds": positive_folds,
        "valid_folds":   len(valid_folds),
        "wf_pct":        round(wf_pct, 1),
        "wf_gate":       "PASS" if wf_pct >= 60.0 else "FAIL",
        "folds":         fold_results,
    }


# ── CPCV (optional, requires skfolio) ────────────────────────────────────────

def run_cpcv_if_available(
    sessions: pd.DataFrame,
    df_1h: pd.DataFrame,
    cost_rt: float = COST_RT_USD,
    event_only: bool = False,
) -> Optional[dict]:
    """Run CPCV validation if skfolio is available."""
    try:
        from Portfolio.validation.cpcv import run_cpcv
    except ImportError:
        return None

    def _bt_fn(train_idx: np.ndarray, test_idx: np.ndarray) -> float:  # noqa: ARG001
        test_dates = sessions.index[test_idx]
        test_sess  = sessions.loc[test_dates]
        pnl = run_backtest(test_sess, df_1h, cost_rt=cost_rt, event_only=event_only)
        if pnl.empty or len(pnl) < 5:
            return 0.0
        r = to_excess_returns(_pnl_to_returns(pnl))
        sr, _, _ = hac_sharpe_ratio(r)
        return float(sr) if not np.isnan(sr) else 0.0

    result = run_cpcv(
        returns=_pnl_to_returns(
            run_backtest(sessions, df_1h, cost_rt=cost_rt, event_only=event_only)
        ),
        backtest_fn=_bt_fn,
        target_n_paths=30,
        target_train_size=252,
        verbose=True,
    )
    return {
        "cpcv_mean":   round(float(result["mean"]), 3),
        "cpcv_median": round(float(result["median"]), 3),
        "cpcv_ci_5":   round(float(result["ci_5_95"][0]), 3),
        "cpcv_ci_95":  round(float(result["ci_5_95"][1]), 3),
        "n_paths":     result["n_paths"],
    }


# ── canary (2024 data) ────────────────────────────────────────────────────────

def run_canary(
    start: str = "2024-07-01",
    end:   str = "2024-12-31",
) -> dict:
    """
    STOP-POINT 2: canary backtest on available 1h data.
    Structural test only — checks signal fires, TDD pytest, basic equity curve.
    """
    log.info("CANARY MODE: %s → %s", start, end)

    df, src = load_zn_intraday(start=start, end=end)
    if df.empty:
        return {"error": f"No data for {start}→{end}. Adjust date range."}

    vix = load_vix(
        (pd.Timestamp(start) - pd.Timedelta(days=5)).strftime("%Y-%m-%d"), end
    )
    cal = build_macro_calendar(int(start[:4]), int(end[:4]))
    cal_window = cal[
        (cal["date"] >= pd.Timestamp(start)) &
        (cal["date"] <= pd.Timestamp(end))
    ]

    sessions = compute_session_features(df, src, calendar=cal_window, vix=vix)
    if sessions.empty:
        return {"error": "No sessions extracted from data"}

    pnl_h1 = run_backtest(sessions, df, cost_rt=COST_RT_USD, event_only=False)
    pnl_h2 = run_backtest(sessions, df, cost_rt=COST_RT_USD, event_only=True)

    m_h1 = _compute_metrics_block(pnl_h1, label="canary_H1", n_trials=1)
    m_h2 = _compute_metrics_block(pnl_h2, label="canary_H2", n_trials=1)

    n_event = int(sessions["is_event_day"].sum())
    result = {
        "mode":           "canary",
        "start":          start,
        "end":            end,
        "source":         src.name,
        "n_sessions":     len(sessions),
        "n_event_days":   n_event,
        "h1_metrics":     m_h1,
        "h2_metrics":     m_h2,
        "note":           "1h approximation — SL intra-bar, exit proxy midpoint",
    }
    return result


# ── full run 2018-2025 ────────────────────────────────────────────────────────

def run_full(
    start: str = "2018-01-01",
    end:   str = "2025-12-31",
) -> dict:
    """
    STOP-POINT 3: full backtest H1 + H2 + H3 + walk-forward + CPCV + DSR.
    Requires 1-min data (data/raw/ZN_1min.csv or ZN_1min_cache.parquet).
    """
    log.info("FULL RUN: %s → %s", start, end)

    df, src = load_zn_intraday(start=start, end=end)
    if df.empty:
        return {
            "error": "No 1-min data available for 2018-2025.",
            "action_required": (
                "Download ZN 1-min from FirstRateData (~$99) and save to "
                "data/raw/ZN_1min.csv, OR set up Databento."
            ),
        }
    if src != DataSource.LOCAL_1MIN:
        return {
            "error": f"Full run requires 1-min data; got {src.name}.",
            "action_required": "See prespec.md §Data resolution note",
        }

    vix = load_vix(
        (pd.Timestamp(start) - pd.Timedelta(days=5)).strftime("%Y-%m-%d"), end
    )
    cal = build_macro_calendar(int(start[:4]), int(end[:4]))

    sessions = compute_session_features(df, src, calendar=cal, vix=vix)
    if sessions.empty:
        return {"error": "No sessions extracted"}

    log.info("Sessions loaded: %d", len(sessions))

    h1 = run_h1(sessions, df)
    h2 = run_h2(sessions, df)
    h3 = run_h3(sessions, df)
    wf = run_walk_forward(sessions, df, n_folds=WF_N_FOLDS)
    cpcv = run_cpcv_if_available(sessions, df, event_only=False)

    # Stress cost
    pnl_stress = run_backtest(sessions, df, cost_rt=COST_RT_STRESS, event_only=False)
    m_stress = _compute_metrics_block(pnl_stress, label="H1_stress_cost_35",
                                       n_trials=N_TRIALS_DSR)

    # Overall verdict
    gates = {
        "h1": h1.get("h1_gate", "FAIL"),
        "h2": h2.get("h2_gate", "FAIL"),
        "h3": h3.get("h3_gate", "FAIL"),
        "wf": wf.get("wf_gate", "FAIL"),
    }
    all_pass = all(v == "PASS" for v in gates.values())
    any_h1_pass = gates["h1"] == "PASS"
    research_verdict = (
        "RESEARCH_PASS"  if all_pass else
        "PARTIAL_PASS"   if any_h1_pass else
        "FAIL_ARCHIVE"
    )

    result = {
        "run_mode":         "full",
        "start":            start,
        "end":              end,
        "source":           src.name,
        "n_sessions":       len(sessions),
        "n_event_days":     int(sessions["is_event_day"].sum()),
        "h1":               h1,
        "h2":               h2,
        "h3":               h3,
        "walk_forward":     wf,
        "h1_stress_cost":   m_stress,
        "cpcv":             cpcv,
        "gates":            gates,
        "research_verdict": research_verdict,
    }
    return result


# ── entrypoint ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Baltussen ZN feasibility backtest")
    parser.add_argument("--canary", action="store_true",
                        help="Run canary on available 1h data (STOP-POINT 2)")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end",   default=None)
    args = parser.parse_args()

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    if args.canary:
        start = args.start or "2024-07-01"
        end   = args.end   or "2024-12-31"
        result = run_canary(start=start, end=end)
        print("\n" + "=" * 60)
        print("  STOP-POINT 2 — Canary backtest results")
        print("=" * 60)
    else:
        start = args.start or "2018-01-01"
        end   = args.end   or "2025-12-31"
        result = run_full(start=start, end=end)
        print("\n" + "=" * 60)
        print("  STOP-POINT 3 — Full backtest results")
        print("=" * 60)

    print(json.dumps(result, indent=2, default=str))

    out_key = "canary" if args.canary else "full"
    existing: dict = {}
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as fh:
            existing = json.load(fh)
    existing[out_key] = result
    with open(RESULTS_PATH, "w") as fh:
        json.dump(existing, fh, indent=2, default=str)
    log.info("Results saved → %s", RESULTS_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    main()
