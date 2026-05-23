#!/usr/bin/env python3
"""
Pairs Trading Cointegration — Feasibility Study
================================================

Strategy: identify cointegrated pairs via 4-test screen, trade z-score of
log-price spread. Dollar-neutral: long Y / short β·X.

Signal:
  β[t]     = rolling 252-day OLS coefficient (shifted 1: no lookahead)
  spread   = log(Y) - β·log(X)
  z[t]     = (spread[t] - μ_60(spread)) / σ_60(spread)   [contemporary]
  pos[t]   = f(z[t-1])   [shifted 1]

Position rules:
  enter long spread  when z < -2.0
  enter short spread when z > +2.0
  exit              when |z| < 0.5
  stop-loss         when |z| > 3.5

Costs: 6 bps per one-way turn (3 bps/leg × 2 legs).
Portfolio: equal-weight across qualifying pairs, vol-targeted to 8% annual.

Canonical methodology (May 2026):
  - Excess returns over FRED DTB3 daily RF
  - HAC lag-6 for all alpha t-stats
  - Daily Sharpe annualised × √252
  - AMTP (honest naming)

Run:  /usr/bin/python3 -m Equities.research.passed.pairs_cointegration.feasibility
"""

from __future__ import annotations

import sys
import json
import logging
import warnings
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.rolling import RollingOLS
from scipy import stats

# ─── Project root & imports ──────────────────────────────────────────────────
_SCRIPT_DIR  = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parents[3]          # Algo_claude/
sys.path.insert(0, str(_PROJECT_ROOT))

from data.cache import get_cached_or_fetch
from Equities.research.passed.pairs_cointegration.universe import ALL_PAIRS, ALL_TICKERS, CATEGORIES
from Equities.research.passed.pairs_cointegration.cointegration_tests import screen_pair

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────
DATA_START       = "2010-01-01"
DATA_END         = datetime.now().strftime("%Y-%m-%d")

BETA_WINDOW      = 252       # trading days for rolling OLS β
Z_WINDOW         = 60        # trading days for rolling z-score
ENTRY_Z          = 2.0
EXIT_Z           = 0.5
STOP_Z           = 3.5

COST_PER_TURN    = 0.0006    # 6 bps per one-way turn  (3 bps × 2 legs)

VT_TARGET        = 0.08      # 8 % annual vol
VT_LOOKBACK      = 63
VT_CAP           = 2.0       # max leverage multiplier

N_TESTS_START    = 71
BOOTSTRAP_N      = 20_000
HAC_LAGS         = 6

WF_OOS_YEARS     = list(range(2014, 2026))   # 12 OOS years

CRASH_PERIODS = {
    "COVID Mar 2020":  ("2020-02-01", "2020-04-30"),
    "2022 inflation":  ("2022-01-01", "2022-12-31"),
    "2023 banking":    ("2023-03-01", "2023-04-30"),
}


# ─── Data Loading ────────────────────────────────────────────────────────────

def _fetch(ticker: str) -> pd.Series:
    df = get_cached_or_fetch(ticker, DATA_START, DATA_END, interval="1d", max_age_days=1.0)
    if df.empty:
        return pd.Series(dtype=float)
    col = "close" if "close" in df.columns else df.columns[0]
    s   = df[col].dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s.sort_index()


def load_all_prices() -> dict[str, pd.Series]:
    extras = ["SPY", "BTC-USD", "ETH-USD", "TLT"]
    tickers = sorted(set(ALL_TICKERS + extras))
    prices  = {}
    for tkr in tickers:
        try:
            s = _fetch(tkr)
            if len(s) < 252:
                log.warning("%-8s: only %d rows — skipped", tkr, len(s))
                continue
            prices[tkr] = s
            log.info("%-8s: %s → %s (%d days)", tkr, s.index[0].date(), s.index[-1].date(), len(s))
        except Exception as exc:
            log.warning("%-8s: fetch failed — %s", tkr, exc)
    return prices


def load_risk_free() -> pd.Series:
    try:
        import pandas_datareader.data as web
        dtb3     = web.DataReader("DTB3", "fred", DATA_START, DATA_END)
        rf_ann   = dtb3["DTB3"].ffill().fillna(0.0) / 100.0
        rf_daily = (1 + rf_ann) ** (1 / 252) - 1
        rf_daily.index = pd.to_datetime(rf_daily.index).tz_localize(None)
        log.info("DTB3 loaded: %d obs", len(rf_daily))
        return rf_daily
    except Exception as exc:
        log.warning("FRED DTB3 unavailable (%s) — using rf=0", exc)
        return pd.Series(dtype=float)


# ─── Rolling β ───────────────────────────────────────────────────────────────

def _rolling_beta(log_y: pd.Series, log_x: pd.Series) -> pd.Series:
    """
    Rolling OLS β from log_y ~ const + β·log_x, window=BETA_WINDOW.
    Shifted by 1 day → no lookahead.
    """
    lx = log_x.copy()
    lx.name = "X"
    X = pd.DataFrame({"const": 1.0, "X": lx}, index=log_y.index)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rol = RollingOLS(log_y, X, window=BETA_WINDOW, min_nobs=BETA_WINDOW)
        betas = rol.fit(cov_type="nonrobust").params["X"]
    return betas.shift(1)                   # shift(1): use t-1 β for t's spread


# ─── Position state machine ──────────────────────────────────────────────────

def _positions(z_arr: np.ndarray) -> np.ndarray:
    """Convert z-score array to position array via state machine."""
    pos = np.zeros(len(z_arr))
    cur = 0.0
    for i, z in enumerate(z_arr):
        if np.isnan(z):
            cur = 0.0
        elif cur == 0.0:
            if   z >  ENTRY_Z: cur = -1.0    # short spread
            elif z < -ENTRY_Z: cur =  1.0    # long spread
        else:
            if abs(z) < EXIT_Z or abs(z) > STOP_Z:
                cur = 0.0
        pos[i] = cur
    return pos


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _max_drawdown(ret: pd.Series) -> float:
    cum  = (1 + ret).cumprod()
    peak = cum.cummax()
    dd   = (cum - peak) / peak
    return float(dd.min())


def _trade_stats(pos: pd.Series, gross: pd.Series) -> dict:
    """Per-trade statistics from position and gross daily P&L series."""
    pv = pos.values
    rv = gross.reindex(pos.index).fillna(0.0).values
    trades, in_t, pnl, dur = [], False, 0.0, 0
    for i in range(len(pv)):
        if not in_t and pv[i] != 0:
            in_t, pnl, dur = True, rv[i], 1
        elif in_t and pv[i] != 0:
            pnl += rv[i]; dur += 1
        elif in_t and pv[i] == 0:
            trades.append({"pnl": pnl, "dur": dur})
            in_t, pnl, dur = False, 0.0, 0
    if in_t:
        trades.append({"pnl": pnl, "dur": dur})
    if not trades:
        return {"n_trades": 0, "win_rate": 0.0, "avg_trade_pct": 0.0, "avg_hold_days": 0.0}
    pnls = [t["pnl"] for t in trades]
    return {
        "n_trades":      len(trades),
        "win_rate":      float(np.mean(np.array(pnls) > 0)) * 100,
        "avg_trade_pct": float(np.mean(pnls)) * 100,
        "avg_hold_days": float(np.mean([t["dur"] for t in trades])),
    }


def _sharpe(ret: pd.Series) -> float:
    if ret.std() < 1e-10:
        return 0.0
    return float(ret.mean() / ret.std() * np.sqrt(252))


def _hac_alpha(y: pd.Series, x: pd.Series) -> dict:
    """OLS with HAC (Newey-West, lag=HAC_LAGS). Alpha annualised."""
    aligned = pd.concat([y, x], axis=1).dropna()
    if len(aligned) < 50:
        return {"alpha": np.nan, "t_alpha": np.nan, "beta": np.nan, "r2": np.nan}
    Y = aligned.iloc[:, 0].values
    X = sm.add_constant(aligned.iloc[:, 1].values)
    m = sm.OLS(Y, X).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    return {
        "alpha":   float(m.params[0]) * 252,
        "t_alpha": float(m.tvalues[0]),
        "beta":    float(m.params[1]),
        "r2":      float(m.rsquared) * 100,
    }


def _amtp(sharpe_daily: float, n_obs: int, n_tests: int) -> dict:
    """BLP simplified multi-test penalty (honest naming)."""
    eg     = 0.5772156649
    sr_d   = sharpe_daily / np.sqrt(252)
    z      = ((1 - eg) * stats.norm.ppf(1 - 1 / n_tests)
               + eg     * stats.norm.ppf(1 - 1 / (n_tests * np.e)))
    sr_star = z / np.sqrt(n_obs - 1)
    pval    = float(stats.norm.sf((sr_d - sr_star) / np.sqrt(1 / (n_obs - 1))))
    return {"amtp_pvalue": round(pval, 4), "amtp_pass": bool(pval < 0.10)}


def _bootstrap_ev(ret: pd.Series, n: int = BOOTSTRAP_N, seed: int = 42) -> dict:
    """Bootstrap EV with 95% CI (20k resamples of daily returns)."""
    rng    = np.random.default_rng(seed)
    r      = ret.dropna().values
    means  = [rng.choice(r, size=len(r), replace=True).mean() for _ in range(n)]
    means  = np.array(means)
    return {
        "ev_pct":   round(float(np.mean(means)) * 100, 4),
        "ci_lo":    round(float(np.percentile(means, 2.5)) * 100, 4),
        "ci_hi":    round(float(np.percentile(means, 97.5)) * 100, 4),
        "p_neg":    round(float(np.mean(means <= 0)), 4),
    }


# ─── Per-pair backtest ────────────────────────────────────────────────────────

def backtest_pair(
    price_y: pd.Series,
    price_x: pd.Series,
    label:   str = "",
) -> tuple[pd.Series, dict]:
    """
    Single-pair backtest. Returns (net_daily_returns, stats).

    Returns are fractional (not %). Spread return = ret_Y - β·ret_X,
    representing the P&L per dollar of the long leg.
    """
    aligned = pd.concat([price_y, price_x], axis=1).dropna()
    aligned.columns = ["Y", "X"]
    if len(aligned) < BETA_WINDOW + Z_WINDOW + 50:
        return pd.Series(dtype=float), {}

    log_y = np.log(aligned["Y"])
    log_x = np.log(aligned["X"])

    # Rolling β (already shifted 1 inside)
    betas = _rolling_beta(log_y, log_x)

    # Spread and rolling z-score (contemporary at t, then shift(1) for signal)
    spread  = log_y - betas * log_x
    z_mean  = spread.rolling(Z_WINDOW).mean()
    z_std   = spread.rolling(Z_WINDOW).std()
    z_score = (spread - z_mean) / z_std
    z_score[z_std < 1e-8] = np.nan

    z_signal = z_score.shift(1)                    # signal from t-1

    # Positions via state machine
    pos_arr  = _positions(z_signal.values)
    position = pd.Series(pos_arr, index=aligned.index)

    # Daily spread returns (uses lagged β to avoid lookahead)
    ret_y       = log_y.diff()
    ret_x       = log_x.diff()
    spread_ret  = ret_y - betas * ret_x

    # P&L: position[t] was established from z[t-1] → holds from close(t-1) to close(t)
    gross  = position * spread_ret
    delta  = position.diff().abs().fillna(0.0)
    costs  = delta * COST_PER_TURN
    net    = (gross - costs).dropna()
    gross  = gross.reindex(net.index)

    if len(net) < 50 or net.std() < 1e-12:
        return net, {}

    ts        = _trade_stats(position.reindex(net.index), gross)
    time_in   = float((position.reindex(net.index) != 0).mean()) * 100
    ann_cost  = float(delta.reindex(net.index).sum() * COST_PER_TURN * 252 / len(net)) * 100

    stats = {
        "label":         label,
        "n_obs":         len(net),
        "sharpe":        round(_sharpe(net), 3),
        "ann_ret_pct":   round(float(net.mean()) * 252 * 100, 2),
        "ann_vol_pct":   round(float(net.std())  * np.sqrt(252) * 100, 2),
        "maxdd_pct":     round(_max_drawdown(net) * 100, 2),
        "worst_day_pct": round(float(net.min()) * 100, 3),
        "n_trades":      ts["n_trades"],
        "win_rate":      round(ts["win_rate"], 1),
        "avg_trade_pct": round(ts["avg_trade_pct"], 4),
        "avg_hold_days": round(ts["avg_hold_days"], 1),
        "time_in_pct":   round(time_in, 1),
        "ann_cost_pct":  round(ann_cost, 3),
    }
    return net, stats


# ─── Portfolio construction ───────────────────────────────────────────────────

def build_portfolio(pnl_dict: dict[str, pd.Series]) -> tuple[pd.Series, pd.Series]:
    """
    Equal-weight portfolio across all active pairs, then vol-target to VT_TARGET.
    Returns (raw_portfolio, vt_portfolio).
    """
    if not pnl_dict:
        idx   = pd.DatetimeIndex([])
        empty = pd.Series(dtype=float, index=idx)
        return empty, empty

    pnl_df  = pd.DataFrame(pnl_dict).fillna(0.0)
    raw     = pnl_df.mean(axis=1)
    vol     = raw.rolling(VT_LOOKBACK).std() * np.sqrt(252)
    scale   = (VT_TARGET / vol.shift(1)).clip(upper=VT_CAP).fillna(1.0)
    vt      = raw * scale
    return raw, vt


# ─── Static benchmark ─────────────────────────────────────────────────────────

def build_static_portfolio(
    qualifying_keys: list[str],
    prices:          dict[str, pd.Series],
    meta:            dict,
) -> pd.Series:
    """
    Always-in spread portfolio (no z-score timing). Used as alpha benchmark.
    """
    ret_dict = {}
    for key in qualifying_keys:
        cat, y_tkr, x_tkr, _ = meta[key]
        log_y  = np.log(prices[y_tkr])
        log_x  = np.log(prices[x_tkr])
        betas  = _rolling_beta(log_y, log_x)
        sret   = log_y.diff() - betas * log_x.diff()
        ret_dict[key] = sret
    if not ret_dict:
        return pd.Series(dtype=float)
    return pd.DataFrame(ret_dict).mean(axis=1).dropna()


# ─── Walk-forward ─────────────────────────────────────────────────────────────

def run_walk_forward(
    qualifying_keys:    list[str],
    pair_pnl_dict:      dict[str, pd.Series],
    prices:             dict[str, pd.Series],
    meta:               dict,
) -> list[dict]:
    """
    Expanding-history IS window (2 years) + 1-year OOS.
    Retest cointegration in IS window to decide which pairs trade in OOS.
    """
    results = []
    for oos_year in WF_OOS_YEARS:
        is_start  = f"{oos_year - 2}-01-01"
        is_end    = f"{oos_year - 1}-12-31"
        oos_start = f"{oos_year}-01-01"
        oos_end   = f"{oos_year}-12-31"

        active = []
        for key in qualifying_keys:
            cat, y_tkr, x_tkr, _ = meta[key]
            if y_tkr not in prices or x_tkr not in prices:
                continue
            y_is = prices[y_tkr].loc[is_start:is_end]
            x_is = prices[x_tkr].loc[is_start:is_end]
            if len(y_is) < 252 or len(x_is) < 252:
                continue
            sc = screen_pair(y_is, x_is)
            if sc["pass"]:
                active.append(key)

        row = {
            "oos_year":   oos_year,
            "n_active":   len(active),
            "n_trades":   0,
            "sharpe":     np.nan,
            "maxdd_pct":  np.nan,
            "ann_ret_pct": np.nan,
            "notes":      "",
        }
        if not active:
            row["notes"] = "no cointegrated pairs in IS window"
            results.append(row)
            continue

        # Slice OOS P&L from precomputed pair backtests
        oos_pnl_parts = []
        for key in active:
            if key not in pair_pnl_dict:
                continue
            oos_slice = pair_pnl_dict[key].loc[oos_start:oos_end]
            if len(oos_slice) > 0:
                oos_pnl_parts.append(oos_slice)

        if not oos_pnl_parts:
            row["notes"] = "no OOS data"
            results.append(row)
            continue

        oos_port  = pd.concat(oos_pnl_parts, axis=1).fillna(0.0).mean(axis=1)
        _, oos_vt = build_portfolio({f"k{i}": s for i, s in enumerate(oos_pnl_parts)})
        oos_vt    = oos_vt.loc[oos_start:oos_end]

        n_trades_oos = sum(
            int((pair_pnl_dict[k].loc[oos_start:oos_end].diff().abs() > 1e-8).sum())
            for k in active if k in pair_pnl_dict
        )

        row.update({
            "n_trades":    n_trades_oos,
            "sharpe":      round(_sharpe(oos_vt), 3),
            "maxdd_pct":   round(_max_drawdown(oos_vt) * 100, 2),
            "ann_ret_pct": round(float(oos_vt.mean()) * 252 * 100, 2),
        })
        results.append(row)

    return results


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    sep = "=" * 72

    # ── 1. Data ───────────────────────────────────────────────────────────────
    print(sep)
    print("Pairs Trading Cointegration -- Feasibility")
    print(sep)
    print("\nFetching prices ...")
    prices = load_all_prices()
    rf_raw = load_risk_free()

    def rf_aligned(idx):
        if rf_raw.empty:
            return pd.Series(0.0, index=idx)
        return rf_raw.reindex(idx, method="ffill").fillna(0.0)

    # Verify minimum universe
    missing = [t for t in ALL_TICKERS if t not in prices]
    if missing:
        log.warning("Missing tickers: %s", missing)

    # ── 2. Cointegration screening on full sample ─────────────────────────────
    print("\n" + "-" * 72)
    print("COINTEGRATION SCREENING (full sample)")
    print("-" * 72)

    screen_results = {}
    for cat, y_tkr, x_tkr, desc in ALL_PAIRS:
        key = f"{y_tkr}/{x_tkr}"
        if y_tkr not in prices or x_tkr not in prices:
            screen_results[key] = {"pass": False, "reason": "ticker missing",
                                   "cat": cat, "y": y_tkr, "x": x_tkr, "desc": desc}
            continue
        sc = screen_pair(prices[y_tkr], prices[x_tkr])
        sc["cat"]  = cat
        sc["y"]    = y_tkr
        sc["x"]    = x_tkr
        sc["desc"] = desc
        screen_results[key] = sc
        status = "PASS" if sc["pass"] else f"FAIL ({sc['reason']})"
        print(f"  {key:12s} [{cat}] {desc:35s} → {status}  HL={sc.get('half_life', np.nan):.1f}d  H={sc.get('hurst', np.nan):.3f}")

    qualifying_keys = [k for k, v in screen_results.items() if v["pass"]]
    n_qual = len(qualifying_keys)

    print(f"\n  Qualifying pairs: {n_qual} / {len(ALL_PAIRS)}")
    print("  By category:")
    for cat in ["C1", "C2", "C3", "C4"]:
        pairs_cat = [(k, v) for k, v in screen_results.items() if v["cat"] == cat]
        n_pass = sum(1 for _, v in pairs_cat if v["pass"])
        print(f"    {cat}: {n_pass}/{len(pairs_cat)}")

    # STOP condition: < 5 qualifying pairs
    if n_qual < 5:
        print("\n  STOP: < 5 pairs pass cointegration screening.")
        print("  Suggestion: expand universe or lower thresholds.")
        return

    # ── 3. Per-pair backtests ─────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("PER-PAIR BACKTESTS (qualifying pairs only)")
    print("-" * 72)

    pair_pnl  = {}    # key → net daily return series
    pair_stats = {}   # key → stats dict
    meta_map  = {}    # key → (cat, y_tkr, x_tkr, desc)

    for key in qualifying_keys:
        sc = screen_results[key]
        y_tkr, x_tkr = sc["y"], sc["x"]
        label = key
        net, st = backtest_pair(prices[y_tkr], prices[x_tkr], label=label)
        if not st:
            log.warning("%s: backtest returned empty stats", key)
            continue
        pair_pnl[key]   = net
        pair_stats[key] = st
        meta_map[key]   = (sc["cat"], y_tkr, x_tkr, sc["desc"])
        print(f"  {key:12s} Sh={st['sharpe']:+.3f}  MaxDD={st['maxdd_pct']:+.1f}%  "
              f"n={st['n_trades']}  WR={st['win_rate']:.0f}%  HL_realized={st['avg_hold_days']:.0f}d")

    # ── 4. Portfolio construction ─────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("PORTFOLIO (equal-weight, vol-targeted 8%)")
    print("-" * 72)

    port_raw, port_vt = build_portfolio(pair_pnl)
    if len(port_vt) < 50:
        print("  WARN: portfolio has insufficient data.")
        return

    rf_port = rf_aligned(port_vt.index)
    port_exc = port_vt - rf_port

    port_sharpe   = _sharpe(port_exc)
    port_ann_ret  = float(port_exc.mean()) * 252 * 100
    port_ann_vol  = float(port_exc.std())  * np.sqrt(252) * 100
    port_maxdd    = _max_drawdown(port_vt) * 100
    port_worst    = float(port_vt.min()) * 100
    port_best     = float(port_vt.max()) * 100
    port_timein   = float((port_raw != 0).mean()) * 100

    # STOP condition: Sharpe > 3
    if port_sharpe > 3.0:
        print(f"\n  SUSPICIOUS: portfolio Sharpe = {port_sharpe:.2f} > 3.0")
        print("  Verify no lookahead: β shift(1), z-score shift(1), WF IS retest.")
        worst10 = port_vt.nsmallest(10)
        best10  = port_vt.nlargest(10)
        print(f"  Worst 10 days:\n{worst10}")
        print(f"  Best 10 days:\n{best10}")

    print(f"  Portfolio Sharpe (HAC, VT): {port_sharpe:+.3f}")
    print(f"  Ann return: {port_ann_ret:+.2f}%  |  Ann vol: {port_ann_vol:.2f}%")
    print(f"  MaxDD: {port_maxdd:+.1f}%  |  Worst day: {port_worst:+.3f}%")
    print(f"  Time in market: {port_timein:.1f}%")

    # Max concurrent positions
    pos_df        = pd.DataFrame({
        k: (pair_pnl[k].abs() > 1e-8).astype(int)
        for k in pair_pnl
    })
    max_concurrent = int(pos_df.sum(axis=1).max())
    avg_concurrent = float(pos_df.sum(axis=1).mean())
    annual_turnover = float(
        sum(abs(pair_pnl[k].diff()).fillna(0).sum() for k in pair_pnl) / max(1, len(pair_pnl))
    ) * 252 / max(1, len(port_vt)) * 100

    # ── 5. Walk-forward ───────────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("WALK-FORWARD (2-yr IS cointegration retest, 1-yr OOS)")
    print("-" * 72)

    wf_results = run_walk_forward(qualifying_keys, pair_pnl, prices, meta_map)
    print(f"  {'Year':6s}  {'N active':8s}  {'Sharpe':8s}  {'MaxDD':7s}  {'Ann ret':8s}")
    for r in wf_results:
        sh  = f"{r['sharpe']:+.3f}"   if not np.isnan(r['sharpe'])   else " n/a "
        dd  = f"{r['maxdd_pct']:+.1f}%" if not np.isnan(r['maxdd_pct']) else "  n/a "
        ret = f"{r['ann_ret_pct']:+.1f}%" if not np.isnan(r['ann_ret_pct']) else "  n/a "
        print(f"  {r['oos_year']:6d}  {r['n_active']:8d}  {sh:8s}  {dd:7s}  {ret}")

    valid_wf   = [r for r in wf_results if not np.isnan(r["sharpe"])]
    pct_pos_wf = float(sum(1 for r in valid_wf if r["sharpe"] > 0)) / max(1, len(valid_wf)) * 100
    med_sh_wf  = float(np.median([r["sharpe"] for r in valid_wf])) if valid_wf else np.nan
    print(f"\n  % positive OOS years: {pct_pos_wf:.0f}%  |  Median Sharpe: {med_sh_wf:+.3f}")

    # STOP condition: 0% positive years
    if valid_wf and pct_pos_wf == 0:
        print("\n  STOP: 0% positive walk-forward years.")
        print("  Likely fundamental issue (regime breaks, cost underestimation).")
        return

    # ── 6. Crash analysis ─────────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("CRASH PERIOD ANALYSIS (portfolio, vol-targeted)")
    print("-" * 72)

    crash_stats = {}
    for name, (t0, t1) in CRASH_PERIODS.items():
        window = port_vt.loc[t0:t1]
        if len(window) < 5:
            crash_stats[name] = {"cum": np.nan, "maxdd": np.nan, "sharpe": np.nan}
            print(f"  {name:22s}: no data in window")
            continue
        cum_ret = float((1 + window).prod() - 1) * 100
        maxdd   = _max_drawdown(window) * 100
        sh      = _sharpe(window)
        crash_stats[name] = {"cum": round(cum_ret, 2), "maxdd": round(maxdd, 2), "sharpe": round(sh, 3)}
        print(f"  {name:22s}: cum={cum_ret:+.1f}%  MaxDD={maxdd:+.1f}%  Sharpe={sh:+.3f}")

    # ── 7. Alpha decomposition ────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("ALPHA vs BENCHMARKS (portfolio, HAC lag-6)")
    print("-" * 72)

    # SPY B&H
    spy_ret = pd.Series(dtype=float)
    if "SPY" in prices:
        spy_ret = np.log(prices["SPY"]).diff().dropna()
        spy_ret.index = pd.to_datetime(spy_ret.index).tz_localize(None)
    spy_exc = spy_ret - rf_aligned(spy_ret.index)

    alpha_spy = _hac_alpha(port_exc.dropna(), spy_exc)
    print(f"  vs SPY B&H:       alpha={alpha_spy['alpha']:+.2f}%/yr  t_HAC={alpha_spy['t_alpha']:+.3f}  "
          f"beta={alpha_spy['beta']:+.4f}  R²={alpha_spy['r2']:.1f}%")

    # Static L/S benchmark (always-in spread)
    static_port = build_static_portfolio(list(pair_pnl.keys()), prices, meta_map)
    static_exc  = (static_port - rf_aligned(static_port.index)).dropna()

    alpha_static = _hac_alpha(port_exc.dropna(), static_exc)
    print(f"  vs Static L/S:    alpha={alpha_static['alpha']:+.2f}%/yr  t_HAC={alpha_static['t_alpha']:+.3f}  "
          f"beta={alpha_static['beta']:+.4f}  R²={alpha_static['r2']:.1f}%")

    # ── 8. Correlation to existing live book ──────────────────────────────────
    print("\n" + "-" * 72)
    print("CORRELATION TO LIVE BOOK")
    print("-" * 72)

    def daily_ret(tkr):
        if tkr not in prices:
            return pd.Series(dtype=float)
        return np.log(prices[tkr]).diff().dropna()

    corr_assets = {
        "BTC-USD (daily ret)":         daily_ret("BTC-USD"),
        "ETH-USD (daily ret)":         daily_ret("ETH-USD"),
        "BTC TSMOM proxy":             daily_ret("BTC-USD").apply(np.sign),
        "SPY (daily ret)":             daily_ret("SPY"),
        "TLT (daily ret)":             daily_ret("TLT"),
    }
    corr_results = {}
    for name, s in corr_assets.items():
        aligned = pd.concat([port_vt, s], axis=1).dropna()
        if len(aligned) < 50:
            corr_results[name] = np.nan
        else:
            corr_results[name] = round(float(aligned.corr().iloc[0, 1]), 3)
        print(f"  {name:35s}: {corr_results[name]}")

    # ── 9. Bootstrap EV & AMTP ────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("BOOTSTRAP EV & AMTP")
    print("-" * 72)

    bev = _bootstrap_ev(port_exc.dropna())
    print(f"  EV/day: {bev['ev_pct']:+.4f}%  CI=[{bev['ci_lo']:+.4f}%, {bev['ci_hi']:+.4f}%]  P(EV≤0)={bev['p_neg']:.4f}")

    n_tests_end = N_TESTS_START + len(pair_pnl) + 1   # +1 for portfolio
    amtp        = _amtp(_sharpe(port_exc.dropna()), len(port_exc.dropna()), n_tests_end)
    print(f"  AMTP: n_tests={n_tests_end}  p={amtp['amtp_pvalue']}  {'PASS' if amtp['amtp_pass'] else 'FAIL'}")

    # ── 10. Propfirm gate decision ────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("PROPFIRM GATE DECISION")
    print("-" * 72)

    btc_corr = corr_results.get("BTC-USD (daily ret)", np.nan)
    gates = [
        ("Sharpe HAC",              "> 1.0",  port_sharpe,  port_sharpe > 1.0),
        ("MaxDD",                   "> -10%", port_maxdd,   port_maxdd  > -10.0),
        ("Worst single day",        "> -3%",  port_worst,   port_worst  > -3.0),
        ("Walk-forward % positive", "> 60%",  pct_pos_wf,   pct_pos_wf  > 60.0),
        ("Alpha t_HAC vs Static L/S","> 1.5", alpha_static['t_alpha'], alpha_static['t_alpha'] > 1.5),
        (f"AMTP p (n={n_tests_end})","< 0.10", amtp['amtp_pvalue'], amtp['amtp_pass']),
        ("Corr to BTC",             "< 0.3",  btc_corr,     (not np.isnan(btc_corr)) and abs(btc_corr) < 0.3),
    ]
    n_pass = sum(1 for *_, p in gates if p)
    for name, thresh, val, passed in gates:
        v_str = f"{val:+.3f}" if isinstance(val, float) and not np.isnan(val) else str(val)
        print(f"  {'PASS' if passed else 'FAIL'}  {name:35s} {thresh:8s}  {v_str}")
    print(f"\n  Gates passed: {n_pass}/7")

    # Verdict
    if   port_sharpe > 1.2 and port_maxdd > -10.0 and abs(btc_corr or 1) < 0.3:
        verdict = "PASS_PROPFIRM"
    elif port_sharpe > 0.6 and abs(btc_corr or 1) < 0.3 and med_sh_wf > 0.5:
        verdict = "PASS_RESEARCH_ONLY — deploy small size as diversifier"
    elif port_sharpe < 0.5 or pct_pos_wf < 50:
        verdict = "FAIL — archive, move to Candidate 4 (commodity TSMOM)"
    else:
        verdict = "MARGINAL — needs more OOS evidence"
    print(f"\n  Verdict: {verdict}")

    # ── 11. Build & save structured summary ───────────────────────────────────
    print("\n" + "-" * 72)
    print("STRUCTURED SUMMARY")
    print("-" * 72)

    # Per-pair table
    pp_rows = []
    for key in pair_pnl:
        sc = screen_results[key]
        st = pair_stats.get(key, {})
        pp_rows.append({
            "pair":      key,
            "cat":       sc["cat"],
            "hl_screen": round(sc.get("half_life", np.nan), 1),
            "hurst":     round(sc.get("hurst", np.nan), 3),
            "n_trades":  st.get("n_trades", 0),
            "win_rate":  st.get("win_rate", np.nan),
            "sharpe":    st.get("sharpe", np.nan),
            "maxdd":     st.get("maxdd_pct", np.nan),
            "ann_ret":   st.get("ann_ret_pct", np.nan),
            "avg_hold":  st.get("avg_hold_days", np.nan),
        })

    # By-category screening summary
    cat_summary = {}
    for cat in ["C1", "C2", "C3", "C4"]:
        total = sum(1 for k, v in screen_results.items() if v["cat"] == cat)
        passed = sum(1 for k, v in screen_results.items() if v["cat"] == cat and v["pass"])
        cat_summary[cat] = f"{passed}/{total}"

    # Walk-forward table
    wf_table_rows = []
    for r in wf_results:
        wf_table_rows.append({
            "year":        r["oos_year"],
            "n_active":    r["n_active"],
            "n_trades":    r["n_trades"],
            "sharpe":      r["sharpe"] if not np.isnan(r["sharpe"]) else None,
            "maxdd_pct":   r["maxdd_pct"] if not np.isnan(r["maxdd_pct"]) else None,
            "ann_ret_pct": r["ann_ret_pct"] if not np.isnan(r["ann_ret_pct"]) else None,
            "notes":       r.get("notes", ""),
        })

    md_lines = [
        "# Result Summary: Pairs Trading Cointegration — Feasibility",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## 1. Headline verdict",
        f"> **Portfolio (equal-weight, VT 8%)**: {verdict}",
        "",
        "## 2. Data status",
        f"- Period: {DATA_START} → {DATA_END}",
        f"- Pairs screened: {len(ALL_PAIRS)}",
        f"- Pairs passing all 4 cointegration tests: {n_qual}",
        "- By category: " + "  ".join(f"{c}={v}" for c, v in cat_summary.items()),
        "",
        "## 3. Per-pair results (qualifying pairs)",
        "",
        "| Pair | Cat | HL screen | Hurst | # trades | Win% | Sharpe | MaxDD% | Ann ret% | Avg hold |",
        "|------|-----|-----------|-------|----------|------|--------|--------|----------|----------|",
    ]
    for r in pp_rows:
        md_lines.append(
            f"| {r['pair']:12s} | {r['cat']} | {r['hl_screen']:.1f}d | {r['hurst']:.3f} "
            f"| {r['n_trades']} | {r['win_rate']:.0f}% "
            f"| {r['sharpe']:+.3f} | {r['maxdd']:+.1f}% | {r['ann_ret']:+.2f}% | {r['avg_hold']:.0f}d |"
        )
    md_lines += [
        "",
        "## 4. Portfolio metrics (equal-weight, VT 8%)",
        "",
        "| Metric              | Value |",
        "|---------------------|-------|",
        f"| Annual return       | {port_ann_ret:+.2f}% |",
        f"| Annual vol          | {port_ann_vol:.2f}% |",
        f"| Sharpe (HAC)        | {port_sharpe:+.3f} |",
        f"| MaxDD               | {port_maxdd:+.1f}% |",
        f"| Worst single day    | {port_worst:+.3f}% |",
        f"| Best single day     | {port_best:+.3f}% |",
        f"| % time in market    | {port_timein:.1f}% |",
        f"| Max concurrent pos  | {max_concurrent} |",
        f"| Avg concurrent pos  | {avg_concurrent:.1f} |",
        f"| Annual turnover     | {annual_turnover:.1f}% |",
        "",
        "## 5. Walk-forward (portfolio, expanding IS / 1-yr OOS)",
        "",
        "| OOS Year | N active | N trades | Sharpe | MaxDD% | Ann ret% | Notes |",
        "|----------|----------|----------|--------|--------|----------|-------|",
    ]
    for r in wf_table_rows:
        sh  = f"{r['sharpe']:+.3f}"   if r["sharpe"]   is not None else "n/a"
        dd  = f"{r['maxdd_pct']:+.1f}%" if r["maxdd_pct"] is not None else "n/a"
        ret = f"{r['ann_ret_pct']:+.1f}%" if r["ann_ret_pct"] is not None else "n/a"
        md_lines.append(
            f"| {r['year']} | {r['n_active']} | {r['n_trades']} | {sh} | {dd} | {ret} | {r['notes']} |"
        )
    md_lines += [
        f"| **% positive** | — | — | **{pct_pos_wf:.0f}%** | — | — | — |",
        f"| **Median Sharpe** | — | — | **{med_sh_wf:+.3f}** | — | — | — |",
        "",
        "## 6. Crash period stress (portfolio, vol-targeted)",
        "",
        "| Period | Cum ret | MaxDD | Sharpe |",
        "|--------|---------|-------|--------|",
    ]
    for name, cs in crash_stats.items():
        cum = f"{cs['cum']:+.1f}%" if cs["cum"] is not None and not np.isnan(cs["cum"]) else "n/a"
        dd  = f"{cs['maxdd']:+.1f}%" if cs["maxdd"] is not None and not np.isnan(cs["maxdd"]) else "n/a"
        sh  = f"{cs['sharpe']:+.3f}" if cs["sharpe"] is not None and not np.isnan(cs["sharpe"]) else "n/a"
        md_lines.append(f"| {name} | {cum} | {dd} | {sh} |")
    md_lines += [
        "",
        "## 7. Alpha decomposition (portfolio vs benchmarks)",
        "",
        "| Benchmark | Alpha (ann%) | t_HAC | Beta | R² |",
        "|-----------|--------------|-------|------|----|",
        f"| SPY B&H | {alpha_spy['alpha']:+.2f}% | {alpha_spy['t_alpha']:+.3f} | {alpha_spy['beta']:+.4f} | {alpha_spy['r2']:.1f}% |",
        f"| Static L/S (always-in spread) | {alpha_static['alpha']:+.2f}% | {alpha_static['t_alpha']:+.3f} | {alpha_static['beta']:+.4f} | {alpha_static['r2']:.1f}% |",
        "",
        "## 8. Correlation to existing live book",
        "",
        "| Asset / Strategy | Correlation |",
        "|------------------|-------------|",
    ]
    for name, c in corr_results.items():
        md_lines.append(f"| {name} | {c} |")
    md_lines += [
        "",
        "## 9. Propfirm gate decision",
        "",
        "| Gate | Threshold | Value | Pass |",
        "|------|-----------|-------|------|",
    ]
    for gname, thresh, val, passed in gates:
        v_str = f"{val:+.3f}" if isinstance(val, float) and not np.isnan(val) else str(val)
        md_lines.append(f"| {gname} | {thresh} | {v_str} | {'PASS' if passed else 'FAIL'} |")
    md_lines += [
        "",
        "## 10. Cointegration screening detail (all 19 pairs)",
        "",
        "| Pair | Cat | EG p | Johansen trace | Crit95 | HL | Hurst | Result |",
        "|------|-----|------|----------------|--------|----|-------|--------|",
    ]
    for key, sc in screen_results.items():
        eg_p = f"{sc.get('eg_pvalue', np.nan):.3f}" if sc.get("eg_pvalue") is not None else "n/a"
        jo_t = f"{sc.get('johansen_trace', np.nan):.2f}" if sc.get("johansen_trace") is not None else "n/a"
        jo_c = f"{sc.get('johansen_crit95', np.nan):.2f}" if sc.get("johansen_crit95") is not None else "n/a"
        hl   = f"{sc.get('half_life', np.nan):.1f}" if sc.get("half_life") is not None else "n/a"
        hu   = f"{sc.get('hurst', np.nan):.3f}" if sc.get("hurst") is not None else "n/a"
        md_lines.append(
            f"| {key} | {sc.get('cat', '?')} | {eg_p} | {jo_t} | {jo_c} | {hl}d | {hu} | {'PASS' if sc['pass'] else 'FAIL'} |"
        )
    md_lines += [
        "",
        "## 11. Bootstrap EV (portfolio, vol-targeted)",
        "",
        f"- EV/day: {bev['ev_pct']:+.4f}%  [95% CI {bev['ci_lo']:+.4f}%, {bev['ci_hi']:+.4f}%]",
        f"- P(EV ≤ 0): {bev['p_neg']:.4f}",
        "",
        "## 12. n_tests counter",
        "",
        f"- Start: {N_TESTS_START}",
        f"- Per-pair backtests: {len(pair_pnl)} (pairs passing cointegration screen)",
        f"- Portfolio: +1",
        f"- **End: {n_tests_end}**",
        "",
        "## 13. Recommendation",
        "",
        f"> {verdict}",
    ]

    summary_path = _SCRIPT_DIR / "pairs_cointegration_summary.md"
    with open(summary_path, "w") as fh:
        fh.write("\n".join(md_lines))
    log.info("Saved → %s", summary_path)

    print(sep)
    print("\n".join(md_lines))
    print(sep)
    print(f"\nSaved → {summary_path}")


if __name__ == "__main__":
    main()
