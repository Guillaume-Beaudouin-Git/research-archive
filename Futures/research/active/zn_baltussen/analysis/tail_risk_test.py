"""
Tail-risk stress test for ZN Baltussen intraday momentum.

Three documented crisis episodes:
  1. Sep 17, 2019  — repo market spike (overnight repo rate > 10%)
  2. Mar 18-20, 2020 — dash-for-cash (Treasury liquidation, Fed intervenes)
  3. Apr 8-9, 2025  — tariff shock (Liberation Day aftermath, ZN volatility surge)

For each episode:
  - Simulate Baltussen signal P&L using whatever data is available
  - Report max single-day loss vs expected annual profit
  - FLAG if max loss > 50% of expected annual profit (tail-risk binding)

Run:  python -m Futures.research.active.zn_baltussen.analysis.tail_risk_test
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).parents[5]
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
from Futures.research.active.zn_baltussen.feasibility import (
    ACCOUNT_SIZE,
    COST_RT_USD,
    SL_TICKS,
    _pnl_single_trade,
    run_backtest,
)

log = logging.getLogger(__name__)

RESULTS_PATH = Path(__file__).parent / "results.json"

# ── episode definitions ───────────────────────────────────────────────────────

EPISODES: list[dict] = [
    {
        "name":        "repo_crisis_2019",
        "label":       "Sep 2019 Repo Market Spike",
        "dates":       ["2019-09-16", "2019-09-17", "2019-09-18"],
        "description": (
            "Overnight repo rate spiked to >10% due to Treasury supply + quarter-end "
            "cash demand. Fed intervened with emergency repos. ZN volatile around FOMC "
            "decision (Sep 18 rate cut). Tail-risk: intraday momentum against rate spike."
        ),
    },
    {
        "name":        "dash_for_cash_2020",
        "label":       "Mar 2020 Dash-for-Cash",
        "dates":       ["2020-03-18", "2020-03-19", "2020-03-20"],
        "description": (
            "COVID-19 liquidity crisis. Institutional investors sold Treasuries for "
            "cash, causing paradoxical ZN sell-off during equity crash. Fed eventually "
            "intervened with QE. Most dangerous tail episode for ZN long bias."
        ),
    },
    {
        "name":        "tariff_shock_2025",
        "label":       "Apr 2025 Tariff Shock",
        "dates":       ["2025-04-07", "2025-04-08", "2025-04-09"],
        "description": (
            "Liberation Day tariff announcement aftermath. ZN saw unusual volatility "
            "as flight-to-safety competed with fiscal concerns about Treasury supply. "
            "Intraday momentum potentially disrupted by erratic directional reversals."
        ),
    },
]


# ── per-episode analysis ──────────────────────────────────────────────────────

def _simulate_episode(
    episode: dict,
    sessions: pd.DataFrame,
    df_1h: pd.DataFrame,
) -> dict:
    """Simulate P&L for a single episode's dates."""
    episode_dates = [pd.Timestamp(d) for d in episode["dates"]]
    # Filter sessions to episode dates
    ep_sessions = sessions[sessions.index.isin(episode_dates)]

    if ep_sessions.empty:
        return {
            "name":        episode["name"],
            "label":       episode["label"],
            "status":      "NO_DATA",
            "dates_found": 0,
        }

    pnl = run_backtest(ep_sessions, df_1h, cost_rt=COST_RT_USD, event_only=False,
                       vix_skip=0.0)  # no VIX filter — stress test needs full exposure

    if pnl.empty:
        return {
            "name":    episode["name"],
            "label":   episode["label"],
            "status":  "NO_TRADES",
            "dates_found": len(ep_sessions),
        }

    daily = pnl.reindex(pd.DatetimeIndex(episode_dates)).dropna()

    return {
        "name":          episode["name"],
        "label":         episode["label"],
        "dates_found":   len(ep_sessions),
        "n_trades":      len(daily),
        "pnl_by_date":   {str(d.date()): round(float(v), 2)
                          for d, v in daily.items()},
        "total_pnl_usd": round(float(daily.sum()), 2),
        "max_loss_usd":  round(float(daily.min()), 2),
        "max_gain_usd":  round(float(daily.max()), 2),
        "status":        "OK",
    }


def _flag_tail_risk(
    episode_result: dict,
    annual_expected_pnl: float,
) -> dict:
    """
    Apply FLAG criterion: max_loss > 50% of annual_expected_pnl.
    A single episode spanning 3 days is bounded to the 3-day analog:
    3-day expected P&L = annual_expected_pnl * 3/252.
    However, the spec comparison is against annual expected (conservative).
    """
    if episode_result.get("status") not in ("OK",):
        return {**episode_result, "tail_flag": "NO_DATA", "ratio": None}

    max_loss = abs(episode_result.get("max_loss_usd", 0) or 0)
    ratio    = max_loss / annual_expected_pnl if annual_expected_pnl > 0 else np.inf
    flag     = "BINDING" if ratio > 0.50 else "OK"

    return {
        **episode_result,
        "annual_expected_pnl_usd": round(annual_expected_pnl, 2),
        "ratio_loss_to_annual":    round(float(ratio), 3),
        "tail_flag":               flag,
    }


# ── expected annual P&L estimation ───────────────────────────────────────────

def _estimate_annual_pnl(
    sessions: pd.DataFrame,
    df_1h: pd.DataFrame,
    n_years: float = 1.0,
) -> float:
    """
    Estimate annual P&L from full backtest period for normalization.
    Returns average annual P&L in USD (before tail episodes).
    """
    pnl = run_backtest(sessions, df_1h, cost_rt=COST_RT_USD,
                       event_only=False, vix_skip=0.0)
    if pnl.empty or n_years <= 0:
        return 0.0
    return float(pnl.sum() / n_years)


# ── main runner ───────────────────────────────────────────────────────────────

def run_tail_risk_tests(
    sessions: pd.DataFrame,
    df_1h: pd.DataFrame,
    n_years: float = 1.0,
) -> dict:
    """
    Run all three episode stress tests and produce results.json summary.

    Parameters
    ----------
    sessions   : output of compute_session_features (full period)
    df_1h      : raw intraday bars
    n_years    : number of years in backtest (for annualising expected P&L)
    """
    annual_expected = _estimate_annual_pnl(sessions, df_1h, n_years)
    log.info("Annual expected P&L (no stress filter): $%.0f", annual_expected)

    episode_results = []
    for ep in EPISODES:
        raw = _simulate_episode(ep, sessions, df_1h)
        flagged = _flag_tail_risk(raw, annual_expected)
        episode_results.append(flagged)
        log.info(
            "Episode %-30s  max_loss=$%7.0f  ratio=%.2f  flag=%s",
            ep["label"],
            abs(flagged.get("max_loss_usd") or 0),
            flagged.get("ratio_loss_to_annual") or 0,
            flagged.get("tail_flag", "N/A"),
        )

    binding = [e for e in episode_results if e.get("tail_flag") == "BINDING"]
    no_data = [e for e in episode_results if e.get("tail_flag") == "NO_DATA"]

    overall = (
        "TAIL_RISK_BINDING" if binding else
        "PARTIAL_DATA"      if no_data else
        "OK"
    )

    result = {
        "annual_expected_pnl_usd": round(annual_expected, 2),
        "n_years":                 round(n_years, 1),
        "episodes":                episode_results,
        "binding_episodes":        [e["name"] for e in binding],
        "missing_data_episodes":   [e["name"] for e in no_data],
        "overall_tail_verdict":    overall,
        "methodology_note": (
            "Tail flag = max single-day loss > 50% of annual expected P&L. "
            "NO_DATA for pre-yfinance-window episodes (2019/2020) if only 1h data available."
        ),
    }
    return result


def main() -> None:
    """Standalone runner — uses available data."""
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    # Determine available data range
    df_full, src = load_zn_intraday(start="2018-01-01", end="2025-12-31")
    if df_full.empty:
        # fallback to 1h window
        df_full, src = load_zn_intraday(start="2024-07-01", end="2025-12-31")

    if df_full.empty:
        print("ERROR: No data available for tail-risk tests.")
        print("  Episodes 2019/2020 require paid 1-min data (see prespec.md).")
        return

    data_start = df_full.index.min().strftime("%Y-%m-%d")
    data_end   = df_full.index.max().strftime("%Y-%m-%d")
    n_years    = (df_full.index.max() - df_full.index.min()).days / 365.25

    vix = load_vix(
        (df_full.index.min() - pd.Timedelta(days=5)).strftime("%Y-%m-%d"),
        data_end,
    )
    cal = build_macro_calendar(
        start_year=int(data_start[:4]),
        end_year=int(data_end[:4]),
    )
    sessions = compute_session_features(df_full, src, calendar=cal, vix=vix)

    result = run_tail_risk_tests(sessions, df_full, n_years=n_years)
    result["data_start"] = data_start
    result["data_end"]   = data_end
    result["source"]     = src.name

    print("\n" + "=" * 60)
    print("  STOP-POINT 3 (partial) — Tail-risk stress test")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))

    # Merge into analysis/results.json
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as fh:
            existing = json.load(fh)
    existing["tail_risk"] = result
    with open(RESULTS_PATH, "w") as fh:
        json.dump(existing, fh, indent=2, default=str)
    log.info("Tail-risk results saved → %s", RESULTS_PATH)


if __name__ == "__main__":
    main()
