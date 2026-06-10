"""
iter_01.py — Strategy D: VWAP Mean Reversion NQ Afternoon
==========================================================

Economic rationale: Institutional VWAP slicers dominate execution flow in the
afternoon session (12:30–15:00 ET), creating mean-reverting pressure toward VWAP.
Enter when price has deviated ≥2σ from the rolling 30-min norm AND has been on
one side of VWAP for 3 consecutive 5-min bars.  Exit at VWAP cross or SL.

Variants:
  1a — Base spec (z>2.0, 12:30-15:00, VWAP-cross exit)
  1b — Tighter entry (z>2.5)
  1c — Wider window (11:30-15:30)
  1d — VWAP-touch exit (within 0.1×ATR) instead of full cross

n_tests counter: 126 → 130 after these 4 variants.
"""
from __future__ import annotations

import logging
import sys
import time as _time
import datetime as dt
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).parents[4]
sys.path.insert(0, str(ROOT))

from data.cache import load_nq_1min

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")

# ── Constants ─────────────────────────────────────────────────────────────────
POINT_VALUE    = 20.0    # $/NQ point/contract
COST_RT        = 19.0    # $ round-trip per contract
DOLLAR_RISK    = 300.0   # target $ risk per trade
MAX_CONTRACTS  = 2.0
MIN_CONTRACTS  = 0.1
Z_WINDOW       = 6       # 30-min / 5-min = 6 bars for rolling z-score
CONSEC_BARS    = 3       # consecutive 5-min bars same side of VWAP
MAX_TRADES_DAY = 2
ATR_LOOKBACK   = 5       # days for daily ATR smoothing
N_TESTS        = 130     # cumulative across all NQ research (126 + 4 here)
N_BOOTSTRAP    = 20_000
CAPITAL        = 50_000.0

T_0930 = dt.time(9, 30)
T_1130 = dt.time(11, 30)
T_1230 = dt.time(12, 30)
T_1500 = dt.time(15, 0)
T_1525 = dt.time(15, 25)
T_1530 = dt.time(15, 30)
T_1600 = dt.time(16, 0)

VARIANTS = {
    "1a": dict(z_thresh=2.0, sig_start=T_1230, sig_end=T_1500,
               tp_mode="cross", tp_atr_mult=None),
    "1b": dict(z_thresh=2.5, sig_start=T_1230, sig_end=T_1500,
               tp_mode="cross", tp_atr_mult=None),
    "1c": dict(z_thresh=2.0, sig_start=T_1130, sig_end=T_1530,
               tp_mode="cross", tp_atr_mult=None),
    "1d": dict(z_thresh=2.0, sig_start=T_1230, sig_end=T_1500,
               tp_mode="touch",  tp_atr_mult=0.1),
}

# Walk-forward: 12-month train, 6-month OOS, stepping 6 months
WF_WINDOWS = [
    ("2023-01-01", "2023-12-31", "2024-01-01", "2024-06-30"),
    ("2023-07-01", "2024-06-30", "2024-07-01", "2024-12-31"),
    ("2024-01-01", "2024-12-31", "2025-01-01", "2025-06-30"),
    ("2024-07-01", "2025-06-30", "2025-07-01", "2025-11-30"),
]

OUT_DIR = Path(__file__).parent


# ─────────────────────────────────────────────────────────────────────────────
# Feature computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_features(df_1min: pd.DataFrame) -> pd.DataFrame:
    """
    From 1-min NQ RTH data, compute:
      - Session cumulative VWAP
      - 5-day rolling daily ATR (lagged 1 day, causal)
      - 5-min resampled OHLCV bars
      - Deviation = (close - vwap) / atr_5d
      - Z-score = rolling 30-min (6 bar) normalised deviation

    Returns DataFrame indexed by 5-min bar timestamp.
    """
    rth = df_1min[(df_1min.index.time >= T_0930) &
                  (df_1min.index.time < T_1600)].copy()

    if rth.empty:
        return pd.DataFrame()

    # ── Daily ATR (5-day rolling mean of RTH H-L, shift 1 day — causal) ──────
    daily_hi  = rth["high"].resample("B").max()
    daily_lo  = rth["low"].resample("B").min()
    daily_atr = (daily_hi - daily_lo).rolling(ATR_LOOKBACK, min_periods=2).mean().shift(1)

    # ── Session VWAP (cumulative from 09:30, reset each day) ─────────────────
    rth["_date"] = rth.index.date
    rth["_pv"]   = rth["close"] * rth["volume"]
    rth["_cum_pv"]  = rth.groupby("_date")["_pv"].cumsum()
    rth["_cum_vol"] = rth.groupby("_date")["volume"].cumsum()
    # Avoid divide-by-zero on zero-volume bars
    rth["vwap_1min"] = np.where(
        rth["_cum_vol"] > 0,
        rth["_cum_pv"] / rth["_cum_vol"],
        rth["close"]
    )

    # ── Resample to 5-min OHLCV + VWAP at bar close ──────────────────────────
    agg = {
        "open":       "first",
        "high":       "max",
        "low":        "min",
        "close":      "last",
        "volume":     "sum",
        "vwap_1min":  "last",   # VWAP at end of 5-min bar
    }
    df5 = rth.resample("5min", closed="left", label="left").agg(agg).dropna(subset=["close"])
    df5.rename(columns={"vwap_1min": "vwap"}, inplace=True)

    # Filter back to RTH only (resampler can create out-of-RTH bars)
    df5 = df5[(df5.index.time >= T_0930) & (df5.index.time < T_1600)]

    # ── Merge daily ATR onto 5-min bars ──────────────────────────────────────
    df5["_date"] = df5.index.normalize()
    atr_daily = daily_atr.rename("atr_5d")
    # daily_atr is B-day indexed; merge by date
    atr_map = {ts.date(): v for ts, v in atr_daily.items() if not np.isnan(v)}
    df5["atr_5d"] = df5.index.date
    df5["atr_5d"] = df5["atr_5d"].map(atr_map)

    # ── Deviation and rolling z-score (computed per session) ─────────────────
    df5["dev"] = np.nan
    df5["z"]   = np.nan

    for date_val, sess in df5.groupby(df5.index.date):
        atr = sess["atr_5d"].iloc[0]
        if np.isnan(atr) or atr <= 0:
            continue
        dev = (sess["close"] - sess["vwap"]) / atr
        roll_mean = dev.rolling(Z_WINDOW, min_periods=2).mean()
        roll_std  = dev.rolling(Z_WINDOW, min_periods=2).std()
        z = (dev - roll_mean) / roll_std.replace(0, np.nan)
        df5.loc[sess.index, "dev"] = dev
        df5.loc[sess.index, "z"]   = z

    return df5


# ─────────────────────────────────────────────────────────────────────────────
# Trade simulation
# ─────────────────────────────────────────────────────────────────────────────

def simulate_session(sess_df: pd.DataFrame, cfg: dict) -> list[dict]:
    """
    Simulate VWAP mean-reversion trades for one trading session.
    Returns a list of trade dicts.
    """
    if len(sess_df) < CONSEC_BARS + 1:
        return []

    above_vwap = (sess_df["close"] > sess_df["vwap"]).astype(int)
    below_vwap = (sess_df["close"] < sess_df["vwap"]).astype(int)

    # Rolling minimum over CONSEC_BARS bars: all 3 bars on same side
    consec_above = above_vwap.rolling(CONSEC_BARS).min() == 1
    consec_below = below_vwap.rolling(CONSEC_BARS).min() == 1

    bars    = list(sess_df.itertuples())
    n       = len(bars)
    ca_arr  = consec_above.values
    cb_arr  = consec_below.values

    trades     : list[dict] = []
    trades_today = 0
    position   : Optional[str] = None  # 'long' | 'short'
    entry_price = sl_price = contracts = 0.0
    entry_time  = None

    for i, bar in enumerate(bars):
        ts      = bar.Index
        close   = bar.close
        high    = bar.high
        low     = bar.low
        vwap    = bar.vwap
        z       = bar.z
        atr     = bar.atr_5d

        # ── Exit logic ────────────────────────────────────────────────────────
        if position is not None:
            exit_price = None
            exit_reason = None

            if ts.time() >= T_1525:
                exit_price  = close
                exit_reason = "TIME"
            elif position == "short":
                if high >= sl_price:
                    exit_price  = sl_price
                    exit_reason = "SL"
                elif cfg["tp_mode"] == "cross" and close <= vwap:
                    exit_price  = vwap
                    exit_reason = "TP"
                elif (cfg["tp_mode"] == "touch" and
                      abs(close - vwap) <= cfg["tp_atr_mult"] * atr):
                    exit_price  = close
                    exit_reason = "TP"
            elif position == "long":
                if low <= sl_price:
                    exit_price  = sl_price
                    exit_reason = "SL"
                elif cfg["tp_mode"] == "cross" and close >= vwap:
                    exit_price  = vwap
                    exit_reason = "TP"
                elif (cfg["tp_mode"] == "touch" and
                      abs(close - vwap) <= cfg["tp_atr_mult"] * atr):
                    exit_price  = close
                    exit_reason = "TP"

            if exit_price is not None:
                direction = -1 if position == "short" else 1
                pnl_pts   = direction * (entry_price - exit_price)
                pnl_usd   = pnl_pts * contracts * POINT_VALUE - contracts * COST_RT
                trades.append(dict(
                    date        = ts.date(),
                    direction   = position,
                    entry_time  = entry_time,
                    exit_time   = ts,
                    entry_price = entry_price,
                    exit_price  = exit_price,
                    exit_reason = exit_reason,
                    contracts   = contracts,
                    pnl_pts     = pnl_pts,
                    pnl_usd     = pnl_usd,
                ))
                position = None

        # ── Entry logic ───────────────────────────────────────────────────────
        if (position is None and
                trades_today < MAX_TRADES_DAY and
                cfg["sig_start"] <= ts.time() <= cfg["sig_end"] and
                not np.isnan(z) and
                atr > 0):

            sl_dist  = 0.5 * atr
            ctrs     = float(np.clip(
                DOLLAR_RISK / (sl_dist * POINT_VALUE),
                MIN_CONTRACTS, MAX_CONTRACTS
            ))

            if z > cfg["z_thresh"] and ca_arr[i]:
                position    = "short"
                entry_price = close
                sl_price    = close + sl_dist
                contracts   = ctrs
                entry_time  = ts
                trades_today += 1
            elif z < -cfg["z_thresh"] and cb_arr[i]:
                position    = "long"
                entry_price = close
                sl_price    = close - sl_dist
                contracts   = ctrs
                entry_time  = ts
                trades_today += 1

    # ── Force-close any open position at EOD ─────────────────────────────────
    if position is not None:
        bar = bars[-1]
        direction = -1 if position == "short" else 1
        pnl_pts   = direction * (entry_price - bar.close)
        pnl_usd   = pnl_pts * contracts * POINT_VALUE - contracts * COST_RT
        trades.append(dict(
            date        = bar.Index.date(),
            direction   = position,
            entry_time  = entry_time,
            exit_time   = bar.Index,
            entry_price = entry_price,
            exit_price  = bar.close,
            exit_reason = "EOD",
            contracts   = contracts,
            pnl_pts     = pnl_pts,
            pnl_usd     = pnl_usd,
        ))

    return trades


def run_variant(df5: pd.DataFrame, cfg: dict,
                start: str | None = None,
                end:   str | None = None) -> pd.DataFrame:
    """Run one variant over a date range, return trade log."""
    sub = df5.copy()
    if start:
        sub = sub[sub.index >= pd.Timestamp(start, tz=sub.index.tz)]
    if end:
        sub = sub[sub.index <= pd.Timestamp(end, tz=sub.index.tz)]

    all_trades: list[dict] = []
    for date_val, sess in sub.groupby(sub.index.date):
        all_trades.extend(simulate_session(sess, cfg))

    return pd.DataFrame(all_trades)


# ─────────────────────────────────────────────────────────────────────────────
# Statistics
# ─────────────────────────────────────────────────────────────────────────────

def daily_pnl_series(trade_log: pd.DataFrame,
                     full_range_start: str,
                     full_range_end:   str) -> pd.Series:
    """
    Aggregate trades to daily P&L (fractional return on CAPITAL).
    Non-trading days filled with 0.
    """
    if trade_log.empty:
        idx = pd.date_range(full_range_start, full_range_end, freq="B")
        return pd.Series(0.0, index=idx)

    daily = (trade_log.groupby("date")["pnl_usd"].sum() / CAPITAL)
    daily.index = pd.to_datetime(daily.index)
    full_idx = pd.date_range(full_range_start, full_range_end, freq="B")
    return daily.reindex(full_idx, fill_value=0.0)


def sharpe_hac(daily_ret: pd.Series, lag: int = 6) -> float:
    """HAC Sharpe via manual Newey-West variance of the mean (Bartlett kernel)."""
    r = daily_ret.dropna().values.astype(float)
    n = len(r)
    if n < 20:
        return float("nan")
    mu     = r.mean()
    demeaned = r - mu
    # Newey-West long-run variance: V = gamma_0 + 2*sum w_k*gamma_k
    nw_var = np.mean(demeaned ** 2)  # gamma_0
    for k in range(1, lag + 1):
        gamma_k = np.mean(demeaned[k:] * demeaned[:-k])
        nw_var += 2.0 * (1.0 - k / (lag + 1.0)) * gamma_k  # Bartlett weight
    se_mu   = np.sqrt(max(nw_var / n, 1e-20))
    t_stat  = mu / se_mu
    return float(t_stat * np.sqrt(252))


def max_drawdown(cum_pnl: pd.Series) -> float:
    peak = cum_pnl.cummax()
    dd   = (cum_pnl - peak)
    return float(dd.min())


def profit_factor(trade_log: pd.DataFrame) -> float:
    if trade_log.empty:
        return float("nan")
    gross_win  = trade_log.loc[trade_log["pnl_usd"] > 0, "pnl_usd"].sum()
    gross_loss = trade_log.loc[trade_log["pnl_usd"] < 0, "pnl_usd"].sum()
    return float(gross_win / (-gross_loss)) if gross_loss != 0 else float("inf")


def bootstrap_ev(daily_ret: pd.Series, n_boot: int = N_BOOTSTRAP) -> float:
    """P(expected value ≤ 0) via bootstrap resampling."""
    r = daily_ret.values
    r = r[~np.isnan(r)]
    if len(r) < 10:
        return float("nan")
    rng   = np.random.default_rng(42)
    means = rng.choice(r, size=(n_boot, len(r)), replace=True).mean(axis=1)
    return float((means <= 0).mean())


def amtp(pev: float, n_tests: int = N_TESTS) -> float:
    """Approximate multi-test penalty (Bonferroni on bootstrap p-value)."""
    if np.isnan(pev):
        return float("nan")
    return 1.0 - (1.0 - pev) ** n_tests


def compute_metrics(trade_log: pd.DataFrame,
                    date_start: str,
                    date_end:   str,
                    label: str = "") -> dict:
    """Full metrics suite for one variant / one period."""
    daily = daily_pnl_series(trade_log, date_start, date_end)
    n_trades = len(trade_log)

    sh   = sharpe_hac(daily)
    mdd  = max_drawdown(daily.cumsum())
    pf   = profit_factor(trade_log)
    pev  = bootstrap_ev(daily)
    am   = amtp(pev)
    ann  = float(daily.mean() * 252)
    vol  = float(daily.std() * np.sqrt(252))

    wr = float((trade_log["pnl_usd"] > 0).mean()) if n_trades > 0 else float("nan")
    avg_win  = float(trade_log.loc[trade_log["pnl_usd"] > 0, "pnl_usd"].mean()) if n_trades else float("nan")
    avg_loss = float(trade_log.loc[trade_log["pnl_usd"] < 0, "pnl_usd"].mean()) if n_trades else float("nan")

    exits = trade_log["exit_reason"].value_counts().to_dict() if n_trades else {}

    return dict(
        label    = label,
        n_trades = n_trades,
        ann_ret  = ann,
        ann_vol  = vol,
        sharpe   = sh,
        max_dd   = mdd,
        pf       = pf,
        wr       = wr,
        avg_win  = avg_win,
        avg_loss = avg_loss,
        pev      = pev,
        amtp     = am,
        exits    = exits,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Walk-forward
# ─────────────────────────────────────────────────────────────────────────────

def run_wf(df5: pd.DataFrame, cfg: dict) -> tuple[float, list[dict]]:
    """
    Run walk-forward for one variant.
    Returns (wf_pct_positive, list of per-window metrics dicts).
    """
    window_results = []
    for tr_start, tr_end, te_start, te_end in WF_WINDOWS:
        tlog = run_variant(df5, cfg, start=te_start, end=te_end)
        m = compute_metrics(tlog, te_start, te_end, label=f"{te_start}→{te_end}")
        m["oos_pnl"] = tlog["pnl_usd"].sum() if not tlog.empty else 0.0
        window_results.append(m)

    n_pos = sum(1 for w in window_results if w["oos_pnl"] > 0)
    wf_pct = n_pos / len(window_results) * 100
    return wf_pct, window_results


# ─────────────────────────────────────────────────────────────────────────────
# Correlation with Strategy C (iter_05)
# ─────────────────────────────────────────────────────────────────────────────

def load_strategy_c_daily() -> pd.Series:
    """
    Load Strategy C (iter_05 A$400+B1.2%) daily fractional returns.
    Reuses Portfolio integration loader.
    """
    try:
        from Portfolio.integration.load_returns import load_returns_C
        return load_returns_C()
    except Exception as e:
        log.warning(f"Could not load Strategy C returns: {e}")
        return pd.Series(dtype=float)


def corr_with_c(daily_d: pd.Series, daily_c: pd.Series) -> float:
    """Pearson correlation between D and C daily returns on overlapping non-zero days."""
    if daily_c.empty or daily_d.empty:
        return float("nan")
    # Align on common index
    common = daily_d.index.intersection(daily_c.index)
    if len(common) < 20:
        return float("nan")
    d = daily_d.loc[common]
    c = daily_c.loc[common]
    # Use only days where at least one strategy is non-zero
    mask = (d != 0) | (c != 0)
    if mask.sum() < 20:
        return float("nan")
    return float(d[mask].corr(c[mask]))


# ─────────────────────────────────────────────────────────────────────────────
# Markdown summary writer
# ─────────────────────────────────────────────────────────────────────────────

def _gate_str(val: float, threshold: float, better_below: bool = False) -> str:
    if np.isnan(val):
        return "—"
    passed = (val < threshold) if better_below else (val > threshold)
    return f"{val:.3f} {'✓' if passed else '✗'}"


def write_summary(results: dict, wf_data: dict, corr_cd: dict,
                  c_daily: pd.Series) -> None:
    """Write iter_01_summary.md."""
    path = OUT_DIR / "iter_01_summary.md"

    # Overall verdict: best variant
    valid = {k: v for k, v in results.items() if not np.isnan(v["sharpe"])}
    if valid:
        best_k = max(valid, key=lambda k: valid[k]["sharpe"])
        best   = valid[best_k]
    else:
        best_k = "—"
        best   = {}

    RESEARCH_PASS = (
        best.get("sharpe", 0) > 0.6 and
        best.get("max_dd", -999) > -0.20 * CAPITAL and
        wf_data.get(best_k, {}).get("wf_pct", 0) > 55 and
        best.get("pf", 0) > 1.15 and
        best.get("pev", 1) < 0.10 and
        corr_cd.get(best_k, 1) < 0.3
    )
    PROPFIRM_PASS = (
        best.get("sharpe", 0) > 1.0 and
        best.get("max_dd", -999) > -0.10 * CAPITAL and
        wf_data.get(best_k, {}).get("wf_pct", 0) > 65 and
        best.get("pf", 0) > 1.25 and
        best.get("pev", 1) < 0.05
    )

    verdict = "FAIL"
    if PROPFIRM_PASS:
        verdict = "PROPFIRM_PASS"
    elif RESEARCH_PASS:
        verdict = "RESEARCH_PASS"

    lines = [
        "## Strategy D iter_01: VWAP Mean Reversion NQ Afternoon",
        "",
        f"*Generated: {dt.date.today().isoformat()}  |  n_tests after: {N_TESTS}*",
        "",
        "### 1. Headline verdict",
        f"**{verdict}** (best variant: {best_k})",
        "",
        "### 2. Variant comparison (full period 2023-01-01 → 2025-12-11)",
        "",
        "| Variant | Sharpe HAC | MaxDD ($) | MaxDD% | PF | WF% | N | P(EV≤0) | AMTP | corr(C,D) |",
        "|---------|-----------|----------|--------|-----|-----|---|---------|------|-----------|",
    ]

    for k, m in results.items():
        wf_pct  = wf_data.get(k, {}).get("wf_pct", float("nan"))
        corr_v  = corr_cd.get(k, float("nan"))
        mdd_pct = m["max_dd"] / CAPITAL * 100 if not np.isnan(m["max_dd"]) else float("nan")
        lines.append(
            f"| {k} | {m['sharpe']:.3f} | ${m['max_dd']:,.0f} | {mdd_pct:.1f}% "
            f"| {m['pf']:.3f} | {wf_pct:.0f}% | {m['n_trades']} "
            f"| {m['pev']:.3f} | {m['amtp']:.3f} | {corr_v:.3f} |"
        )

    lines += ["",
        "### 3. Trade statistics (best variant)",
        "",
        f"- N trades: {best.get('n_trades', '—')}",
        f"- Win rate: {best.get('wr', float('nan')):.1%}",
        f"- Avg win: ${best.get('avg_win', 0):.2f}",
        f"- Avg loss: ${best.get('avg_loss', 0):.2f}",
        f"- Ann return: {best.get('ann_ret', 0)*100:.1f}%",
        f"- Ann vol: {best.get('ann_vol', 0)*100:.1f}%",
        f"- Exit reasons: {best.get('exits', {})}",
        "",
    ]

    # WF window detail
    lines.append("### 4. Walk-forward windows (best variant)")
    lines.append("")
    lines.append("| Window | OOS P&L | Sharpe | N trades |")
    lines.append("|--------|---------|--------|----------|")
    for w in wf_data.get(best_k, {}).get("windows", []):
        lines.append(f"| {w['label']} | ${w['oos_pnl']:,.0f} | {w['sharpe']:.3f} | {w['n_trades']} |")
    lines.append("")

    # Gate check
    lines += [
        "### 5. Gate check",
        "",
        "**RESEARCH_PASS gates:**",
        f"- Sharpe HAC > 0.6: {_gate_str(best.get('sharpe', float('nan')), 0.6)}",
        f"- MaxDD > -$10K: {_gate_str(best.get('max_dd', float('nan')), -10000, better_below=False)}",
        f"- WF% > 55%: {_gate_str(wf_data.get(best_k, {}).get('wf_pct', float('nan')), 55)}",
        f"- PF > 1.15: {_gate_str(best.get('pf', float('nan')), 1.15)}",
        f"- P(EV≤0) < 0.10: {_gate_str(best.get('pev', float('nan')), 0.10, better_below=True)}",
        f"- corr(C,D) < 0.30: {_gate_str(corr_cd.get(best_k, float('nan')), 0.30, better_below=True)}",
        "",
        "**PROPFIRM_PASS gates:**",
        f"- Sharpe HAC > 1.0: {_gate_str(best.get('sharpe', float('nan')), 1.0)}",
        f"- MaxDD > -$5K: {_gate_str(best.get('max_dd', float('nan')), -5000, better_below=False)}",
        f"- WF% > 65%: {_gate_str(wf_data.get(best_k, {}).get('wf_pct', float('nan')), 65)}",
        f"- PF > 1.25: {_gate_str(best.get('pf', float('nan')), 1.25)}",
        f"- P(EV≤0) < 0.05: {_gate_str(best.get('pev', float('nan')), 0.05, better_below=True)}",
        "",
        "### 6. Interpretation",
        "",
    ]

    if verdict == "PROPFIRM_PASS":
        lines += [
            "Strategy D passes PROPFIRM gates. Proceed to: walk-forward with parameter search "
            "(if any), cross-instrument validation, and live paper trading.",
        ]
    elif verdict == "RESEARCH_PASS":
        lines += [
            "Strategy D passes RESEARCH gates — real edge, not deployable standalone at Propr. "
            "Key use: diversifier with Strategy C in portfolio. Re-evaluate after improving "
            "exit logic or wider time window.",
        ]
    else:
        lines += [
            "Strategy D FAILS all gates. VWAP reversion in NQ afternoon does not produce "
            "sufficient edge to overcome $19 RT costs at this parameterisation. "
            "Do not proceed with further iterations unless a fundamentally different "
            "signal construction is identified.",
        ]

    path.write_text("\n".join(lines) + "\n")
    log.info(f"Summary written → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = _time.time()
    log.info("=== Strategy D iter_01: VWAP Mean Reversion NQ Afternoon ===")

    # ── Load and prepare data ─────────────────────────────────────────────────
    log.info("Loading NQ 1-min data...")
    df = load_nq_1min()
    log.info(f"  Loaded: {len(df):,} rows  {df.index[0]} → {df.index[-1]}")

    log.info("Computing 5-min features (VWAP, ATR, deviation, z-score)...")
    df5 = compute_features(df)
    log.info(f"  5-min bars: {len(df5):,}  {df5.index[0]} → {df5.index[-1]}")

    # ── Strategy C correlation baseline ──────────────────────────────────────
    log.info("Loading Strategy C daily returns for correlation...")
    c_daily = load_strategy_c_daily()
    if not c_daily.empty:
        log.info(f"  Strategy C: {len(c_daily)} obs  {c_daily.index[0].date()} → {c_daily.index[-1].date()}")

    # ── Run all 4 variants ────────────────────────────────────────────────────
    FULL_START = "2023-01-01"
    FULL_END   = "2025-12-11"

    results: dict  = {}
    wf_data: dict  = {}
    corr_cd: dict  = {}

    for vname, cfg in VARIANTS.items():
        log.info(f"\n{'─'*60}")
        log.info(f"Variant {vname}: z_thresh={cfg['z_thresh']}  "
                 f"window={cfg['sig_start'].strftime('%H:%M')}–{cfg['sig_end'].strftime('%H:%M')}  "
                 f"tp={cfg['tp_mode']}")

        trade_log = run_variant(df5, cfg, start=FULL_START, end=FULL_END)
        m = compute_metrics(trade_log, FULL_START, FULL_END, label=vname)
        results[vname] = m

        # Walk-forward
        wf_pct, wf_windows = run_wf(df5, cfg)
        wf_data[vname] = {"wf_pct": wf_pct, "windows": wf_windows}

        # Correlation with C
        daily_d = daily_pnl_series(trade_log, FULL_START, FULL_END)
        corr_v  = corr_with_c(daily_d, c_daily)
        corr_cd[vname] = corr_v

        log.info(f"  N={m['n_trades']}  Sh={m['sharpe']:.3f}  MaxDD={m['max_dd']:.0f}  "
                 f"PF={m['pf']:.3f}  WF={wf_pct:.0f}%  P(EV≤0)={m['pev']:.3f}  "
                 f"corr(C,D)={corr_v:.3f}")
        log.info(f"  WR={m['wr']:.1%}  AvgWin=${m['avg_win']:.1f}  AvgLoss=${m['avg_loss']:.1f}  "
                 f"Exits: {m['exits']}")

    # ── Print comparison table ────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("STRATEGY D iter_01 — RESULTS")
    print("=" * 90)
    print(f"{'Variant':<8} {'Sharpe':>8} {'MaxDD$':>10} {'PF':>7} {'WF%':>6} "
          f"{'N':>5} {'P(EV≤0)':>9} {'AMTP':>7} {'corr(C)':>8}")
    print("-" * 90)
    for vname in VARIANTS:
        m  = results[vname]
        wf = wf_data[vname]["wf_pct"]
        cc = corr_cd[vname]
        print(f"  {vname:<6} {m['sharpe']:>8.3f} {m['max_dd']:>10,.0f} {m['pf']:>7.3f} "
              f"{wf:>5.0f}% {m['n_trades']:>5} {m['pev']:>9.3f} {m['amtp']:>7.3f} {cc:>8.3f}")

    print("=" * 90)
    print()

    # ── Gate check ────────────────────────────────────────────────────────────
    print("GATE SUMMARY:")
    print(f"  RESEARCH_PASS requires: Sh>0.6, MaxDD>-20%, WF>55%, PF>1.15, P(EV≤0)<0.10, corr(C,D)<0.30")
    print(f"  PROPFIRM_PASS requires: Sh>1.0, MaxDD>-10%, WF>65%, PF>1.25, P(EV≤0)<0.05")
    print()

    best_k = max(results, key=lambda k: results[k].get("sharpe", -99))
    best = results[best_k]
    r_pass = (best["sharpe"] > 0.6 and best["max_dd"] > -10000 and
              wf_data[best_k]["wf_pct"] > 55 and best["pf"] > 1.15 and
              best["pev"] < 0.10 and corr_cd[best_k] < 0.30)
    p_pass = (best["sharpe"] > 1.0 and best["max_dd"] > -5000 and
              wf_data[best_k]["wf_pct"] > 65 and best["pf"] > 1.25 and best["pev"] < 0.05)

    if p_pass:
        verdict = "PROPFIRM_PASS"
    elif r_pass:
        verdict = "RESEARCH_PASS"
    else:
        verdict = "FAIL"

    print(f"  Best variant: {best_k}  →  VERDICT: {verdict}")
    print(f"  n_tests: {N_TESTS - 4} → {N_TESTS}")
    print()

    # ── Write summary ─────────────────────────────────────────────────────────
    write_summary(results, wf_data, corr_cd, c_daily)

    elapsed = _time.time() - t0
    log.info(f"Total runtime: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
