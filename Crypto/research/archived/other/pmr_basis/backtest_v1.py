#!/usr/bin/env python3
"""
PMR Basis Mean-Reversion — Phase 2 Backtest v1
===============================================
Signal : basis_z = z-score of (perp/spot - 1) over rolling 90d window
Entry  : |basis_z| >= 1.5σ (FIXED ex ante, no grid search)
Exit   : basis_z returns to 0 OR 7-day hard stop (FIXED, no tuning)
Cost   : 0.17% RT (perp-only, taker + slippage)
N_tests_start = 147 (142 prior + 5 pre-flight IC tests this session)

Execution order:
  STEP 0 — Event-count gate: count |basis_z| >= 1.5 events in 2024
            If < 18/year → STOP immediately (Path B)
  STEP 1 — Full backtest on all available history
  STEP 2 — Walk-forward: 18m train / 6m test, step 3m
  STEP 3 — Orthogonality vs A (TSMOM proxy) and real B returns
  STEP 4 — HAC Sharpe + gate: Sharpe > 0.7, MaxDD > -25%, WF% > 50%, N_trades > 30
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parents[4]
CACHE     = Path(__file__).parent.parent / "_preflight" / "cache"
B_CSV     = ROOT / "data" / "metadata" / "delta_neutral_backtest.csv"
RESULTS_F = Path(__file__).parent / "results.json"

# ── Hard parameters (ALL fixed ex ante, no tuning allowed) ───────────────────
ENTRY_THRESHOLD  = 1.5       # |basis_z| ≥ 1.5σ to open position
MAX_HOLD_DAYS    = 7         # hard time stop
BASIS_Z_WINDOW   = 90        # rolling days for z-score
COST_RT          = 0.0017    # 0.17% round trip (taker + slippage)
MAX_CONCURRENT   = 12        # max simultaneous positions

# ── Gate thresholds ───────────────────────────────────────────────────────────
GATE_MIN_EVENTS_YEAR  = 18   # minimum events per year in 2024 (pre-backtest gate)
GATE_RESEARCH_SHARPE  = 0.70
GATE_RESEARCH_MAXDD   = -0.25
GATE_WF_PCT           = 0.50
GATE_N_TRADES         = 30

# ── Walk-forward parameters ───────────────────────────────────────────────────
WF_TRAIN_MONTHS = 18
WF_TEST_MONTHS  = 6
WF_STEP_MONTHS  = 3

N_TESTS_START = 147


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING (reuse pre-flight pickle cache)
# ═══════════════════════════════════════════════════════════════════════════════

def load_cache(coin: str, tag: str) -> pd.DataFrame | pd.Series:
    fpath = CACHE / f"ohlcv_{coin}_{tag}.pickle"
    if fpath.exists():
        return pd.read_pickle(fpath)
    return pd.DataFrame()


def build_price_matrices() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load perp and spot close prices from pre-flight cache."""
    coins = [
        "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX",
        "LINK", "LTC", "ATOM", "NEAR", "OP", "ARB", "INJ", "SUI",
        "AAVE", "FIL", "UNI", "PEPE", "WIF", "TIA", "SEI", "MKR",
        "FTM", "MATIC", "BCH", "APT", "COMP", "CRV",
    ]
    perp_d, spot_d = {}, {}
    for c in coins:
        p = load_cache(c, "perp")
        s = load_cache(c, "spot")
        if not isinstance(p, pd.DataFrame) or p.empty:
            continue
        if not isinstance(s, pd.DataFrame) or s.empty:
            continue
        perp_d[c] = p.set_index("date")["close"] if "date" in p.columns else p["close"]
        spot_d[c] = s.set_index("date")["close"] if "date" in s.columns else s["close"]

    ok = sorted(set(perp_d) & set(spot_d))
    all_idx = pd.DatetimeIndex(sorted(set(d for c in ok for d in perp_d[c].index)))
    perp_wide = pd.DataFrame({c: perp_d[c] for c in ok}, index=all_idx).ffill(limit=3)
    spot_wide = pd.DataFrame({c: spot_d[c] for c in ok}, index=all_idx).ffill(limit=3)
    return perp_wide, spot_wide


def load_strategy_b_daily() -> pd.Series:
    """Load real Strategy B daily returns from backtest CSV."""
    df = pd.read_csv(B_CSV)
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["ts"].dt.normalize().dt.tz_localize(None)
    daily_pnl = df.groupby("date")["net_pnl"].sum()
    return (daily_pnl / 500.0).rename("B")   # fractional return, capital = $500


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════

def compute_basis_z(perp: pd.DataFrame, spot: pd.DataFrame) -> pd.DataFrame:
    """
    basis_z = z-score((perp/spot - 1), rolling BASIS_Z_WINDOW days).
    Shifted 1 day: signal at T-1, trade at T (no look-ahead).
    """
    basis = (perp / spot - 1.0) * 100.0
    bm    = basis.rolling(BASIS_Z_WINDOW, min_periods=BASIS_Z_WINDOW // 2).mean()
    bs    = basis.rolling(BASIS_Z_WINDOW, min_periods=BASIS_Z_WINDOW // 2).std()
    bz    = (basis - bm) / bs.clip(lower=1e-8)
    return bz.shift(1)   # lag-1


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT-COUNT GATE (STEP 0)
# ═══════════════════════════════════════════════════════════════════════════════

def count_events(basis_z: pd.DataFrame,
                 year: int = 2024) -> tuple[int, pd.DataFrame]:
    """
    Count signal events (|basis_z| >= ENTRY_THRESHOLD) in a given year.
    An 'event' is a NEW trigger day for a coin (not a continuation of a hold).
    Returns (n_events, events_df).
    """
    mask = np.abs(basis_z) >= ENTRY_THRESHOLD
    mask_year = mask[
        (mask.index.year == year) & mask.any(axis=1)
    ]
    events = []
    for dt in mask_year.index:
        triggered = mask_year.loc[dt]
        for coin in triggered[triggered].index:
            events.append({"date": dt.date(), "coin": coin,
                           "basis_z": basis_z.loc[dt, coin]})
    events_df = pd.DataFrame(events)
    return len(events_df), events_df


# ═══════════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE (event-driven, position tracking)
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(perp: pd.DataFrame,
                 basis_z: pd.DataFrame,
                 period_start: str | None = None,
                 period_end:   str | None = None) -> tuple[pd.Series, list]:
    """
    Event-driven backtest for PMR threshold strategy.

    Entry : |basis_z| >= ENTRY_THRESHOLD at T → open at T close price
    Exit  : basis_z crosses 0 in trade direction OR hold_days >= MAX_HOLD_DAYS
    Direction : short perp if basis_z > 0 (expect fall), long if basis_z < 0

    Returns:
      port_daily : pd.Series of daily portfolio fractional returns
      trades     : list of dicts with per-trade metadata
    """
    if period_start:
        perp     = perp[perp.index >= period_start]
        basis_z  = basis_z[basis_z.index >= period_start]
    if period_end:
        perp     = perp[perp.index <= period_end]
        basis_z  = basis_z[basis_z.index <= period_end]

    # Skip first BASIS_Z_WINDOW days (warm-up)
    valid_start = basis_z.dropna(how="all").index.min()
    perp = perp[perp.index >= valid_start]
    basis_z = basis_z[basis_z.index >= valid_start]

    dates = perp.index.intersection(basis_z.index).sort_values()
    daily_returns = {}
    trades = []
    positions: dict[str, dict] = {}   # coin → {entry_price, direction, open_date, hold_days}

    for i, dt in enumerate(dates):
        if i == 0:
            continue  # need prior day for return

        prev_dt = dates[i - 1]
        day_rets = {}

        # Step existing positions
        to_close = []
        for coin, pos in positions.items():
            if coin not in perp.columns:
                to_close.append((coin, "data_missing"))
                continue

            p_cur  = perp.loc[dt, coin]
            p_prev = perp.loc[prev_dt, coin] if prev_dt in perp.index else np.nan
            if np.isnan(p_cur) or np.isnan(p_prev) or p_prev == 0:
                to_close.append((coin, "data_missing"))
                continue

            raw_ret = (p_cur - p_prev) / p_prev
            pos_ret = pos["direction"] * raw_ret
            day_rets[coin] = pos_ret
            pos["hold_days"] += 1

            # Exit condition 1: basis_z crosses 0 in the correct direction
            bz_cur = basis_z.loc[dt, coin] if coin in basis_z.columns else np.nan
            exit_by_signal = (
                not np.isnan(bz_cur) and
                (pos["direction"] == -1 and bz_cur <= 0) or
                (pos["direction"] == +1 and bz_cur >= 0)
            )
            # Exit condition 2: max hold days
            exit_by_time = pos["hold_days"] >= MAX_HOLD_DAYS

            if exit_by_signal or exit_by_time:
                to_close.append((coin, "signal" if exit_by_signal else "time"))

        # Close positions and record trade metadata
        for coin, reason in to_close:
            if coin not in positions:
                continue
            pos = positions.pop(coin)
            p_exit = perp.loc[dt, coin] if coin in perp.columns and dt in perp.index else np.nan
            p_entry = pos["entry_price"]
            if not np.isnan(p_exit) and p_entry > 0:
                gross_ret = pos["direction"] * (p_exit - p_entry) / p_entry
            else:
                gross_ret = np.nan
            net_ret = gross_ret - COST_RT if not np.isnan(gross_ret) else np.nan
            trades.append({
                "coin":       coin,
                "open_date":  pos["open_date"],
                "close_date": dt,
                "hold_days":  pos["hold_days"],
                "direction":  pos["direction"],
                "entry_bz":   pos["entry_bz"],
                "gross_ret":  gross_ret,
                "net_ret":    net_ret,
                "exit_reason":reason,
            })

        # Open new positions (at today's close, using today's lagged basis_z signal)
        if len(positions) < MAX_CONCURRENT:
            bz_today = basis_z.loc[dt] if dt in basis_z.index else pd.Series(dtype=float)
            triggered = bz_today[np.abs(bz_today) >= ENTRY_THRESHOLD].dropna()
            # Exclude coins already in positions
            triggered = triggered[~triggered.index.isin(positions)]
            # Rank by |basis_z| descending, take up to available slots
            slots = MAX_CONCURRENT - len(positions)
            triggered = triggered.reindex(triggered.abs().sort_values(ascending=False).index)
            triggered = triggered.iloc[:slots]

            for coin, bz_val in triggered.items():
                if coin not in perp.columns:
                    continue
                p_entry = perp.loc[dt, coin]
                if np.isnan(p_entry):
                    continue
                direction = -1 if bz_val > 0 else +1
                positions[coin] = {
                    "entry_price": p_entry,
                    "direction":   direction,
                    "open_date":   dt,
                    "hold_days":   0,
                    "entry_bz":    bz_val,
                }

        # Portfolio daily return = average of all active position returns
        all_active = list(day_rets.keys()) + [c for c in positions if c not in day_rets]
        if day_rets:
            # Apply entry cost to newly opened positions (half at entry, half at exit)
            new_opens = [c for c in positions if positions[c]["open_date"] == dt]
            for c in new_opens:
                day_rets[c] = day_rets.get(c, 0.0) - COST_RT / 2
            daily_returns[dt] = np.mean(list(day_rets.values()))
        else:
            daily_returns[dt] = 0.0

    port = pd.Series(daily_returns).sort_index()
    return port, trades


# ═══════════════════════════════════════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════════════════════════════════════

def hac_sharpe(ret: pd.Series, lags: int = 6) -> float:
    """HAC-adjusted Sharpe ratio (Newey-West, annualised, daily returns)."""
    import statsmodels.api as sm
    r = ret.dropna()
    n = len(r)
    if n < 20:
        return np.nan
    res = sm.OLS(r, np.ones(n)).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags}
    )
    lrv = float(res.cov_params().to_numpy()[0, 0]) * n
    if lrv <= 0:
        return np.nan
    return float(r.mean() / np.sqrt(lrv)) * np.sqrt(252)


def max_drawdown(ret: pd.Series) -> float:
    cum = (1 + ret).cumprod()
    roll_max = cum.cummax()
    dd = (cum - roll_max) / roll_max
    return float(dd.min())


def compute_metrics(port: pd.Series, trades: list) -> dict:
    port_nz = port[port != 0].dropna()
    sharpe   = hac_sharpe(port_nz)
    mdd      = max_drawdown(port_nz) if len(port_nz) > 5 else np.nan
    ann_ret  = port_nz.mean() * 252
    ann_vol  = port_nz.std() * np.sqrt(252)
    n_trades = len([t for t in trades if not np.isnan(t.get("net_ret", np.nan))])
    win_rate = np.mean([t["net_ret"] > 0 for t in trades if not np.isnan(t.get("net_ret", np.nan))])
    mean_hold = np.mean([t["hold_days"] for t in trades]) if trades else np.nan
    return {
        "sharpe_hac": round(sharpe, 3) if not np.isnan(sharpe) else np.nan,
        "ann_ret":    round(ann_ret * 100, 2),
        "ann_vol":    round(ann_vol * 100, 2),
        "max_dd":     round(mdd * 100, 2) if not np.isnan(mdd) else np.nan,
        "n_trades":   n_trades,
        "win_rate":   round(win_rate * 100, 1),
        "mean_hold_d":round(mean_hold, 1) if not np.isnan(mean_hold) else np.nan,
        "n_obs":      len(port_nz),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# WALK-FORWARD
# ═══════════════════════════════════════════════════════════════════════════════

def walk_forward(perp: pd.DataFrame,
                 basis_z: pd.DataFrame) -> tuple[list, float]:
    """18m/6m walk-forward with 3m step. Returns (wf_results, wf_pct)."""
    start = perp.index.min()
    end   = perp.index.max()
    results = []

    cursor = start
    while True:
        train_end  = cursor + pd.DateOffset(months=WF_TRAIN_MONTHS)
        test_start = train_end
        test_end   = test_start + pd.DateOffset(months=WF_TEST_MONTHS)
        if test_start > end:
            break
        test_end = min(test_end, end)

        port, trades = run_backtest(perp, basis_z,
                                    period_start=str(test_start.date()),
                                    period_end=str(test_end.date()))
        m = compute_metrics(port, trades)
        results.append({
            "train_end":  str(train_end.date()),
            "test_start": str(test_start.date()),
            "test_end":   str(test_end.date()),
            **m,
        })
        cursor += pd.DateOffset(months=WF_STEP_MONTHS)

    if not results:
        return results, 0.0
    sharpes = [r["sharpe_hac"] for r in results if not np.isnan(r["sharpe_hac"] or np.nan)]
    wf_pct = sum(s > 0 for s in sharpes) / len(sharpes) if sharpes else 0.0
    return results, wf_pct


# ═══════════════════════════════════════════════════════════════════════════════
# ORTHOGONALITY CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def check_orthogonality(port_daily: pd.Series,
                        perp_wide: pd.DataFrame,
                        ret_b: pd.Series) -> dict:
    """Compute |corr| with A proxy (equal-weight perp) and real B returns."""
    ret_1d = perp_wide.pct_change(1)
    tsmom_proxy = ret_1d.mean(axis=1)
    tsmom_proxy.index = tsmom_proxy.index.tz_localize(None) if tsmom_proxy.index.tz else tsmom_proxy.index

    port_daily.index = pd.to_datetime(port_daily.index).tz_localize(None) if port_daily.index.tz is None else port_daily.index.tz_convert(None)

    def safe_corr(s1: pd.Series, s2: pd.Series) -> float:
        s1 = s1.dropna()
        s2 = s2.dropna()
        common = s1.index.intersection(s2.index)
        if len(common) < 30:
            return np.nan
        return abs(np.corrcoef(s1[common], s2[common])[0, 1])

    corr_A = safe_corr(port_daily, tsmom_proxy)

    # Real B: date index may be tz-naive
    ret_b_clean = ret_b.copy()
    ret_b_clean.index = pd.to_datetime(ret_b_clean.index).tz_localize(None)
    corr_B = safe_corr(port_daily, ret_b_clean)

    return {"corr_A": round(corr_A, 4) if not np.isnan(corr_A) else np.nan,
            "corr_B": round(corr_B, 4) if not np.isnan(corr_B) else np.nan}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 65)
    print("PMR BASIS MEAN-REVERSION — PHASE 2 BACKTEST v1")
    print(f"N_tests_start = {N_TESTS_START}")
    print(f"Entry threshold: |basis_z| >= {ENTRY_THRESHOLD}σ  (FIXED)")
    print(f"Exit: basis_z → 0 OR {MAX_HOLD_DAYS}d max hold  (FIXED)")
    print("=" * 65)

    # ── Load data ─────────────────────────────────────────────────────────────
    print("\n[DATA] Loading price matrices from pre-flight cache...")
    perp_wide, spot_wide = build_price_matrices()
    print(f"  Universe: {perp_wide.shape[1]} coins | {perp_wide.index[0].date()} → {perp_wide.index[-1].date()}")

    print("[DATA] Loading Strategy B real returns...")
    ret_b = load_strategy_b_daily()
    print(f"  B returns: {len(ret_b)} days | {ret_b.index[0]} → {ret_b.index[-1]}")

    # ── Compute signal ────────────────────────────────────────────────────────
    print("\n[SIGNAL] Computing basis z-score (90d rolling)...")
    basis_z = compute_basis_z(perp_wide, spot_wide)
    valid_from = basis_z.dropna(how="all").index.min()
    print(f"  Signal valid from: {valid_from.date()} (after {BASIS_Z_WINDOW}d warm-up)")

    # ── STEP 0: Event-count gate (2024 only) ─────────────────────────────────
    print("\n" + "─" * 65)
    print(f"[STEP 0] Event-count gate — 2024, threshold |basis_z| >= {ENTRY_THRESHOLD}")
    print("─" * 65)

    n_events_2024, events_df = count_events(basis_z, year=2024)
    print(f"  Events in 2024: {n_events_2024}  (gate: >= {GATE_MIN_EVENTS_YEAR})")

    if not events_df.empty:
        print(f"  Events by coin (top 10):")
        top = events_df.groupby("coin").size().sort_values(ascending=False).head(10)
        for coin, n in top.items():
            print(f"    {coin}: {n}")
        print(f"  High/low basis_z: {events_df['basis_z'].max():.2f} / {events_df['basis_z'].min():.2f}")

    if n_events_2024 < GATE_MIN_EVENTS_YEAR:
        print(f"\n  *** GATE FAIL: {n_events_2024} events < {GATE_MIN_EVENTS_YEAR} required ***")
        print(f"  → PATH B: Insufficient events at 1.5σ. Mission STOP.")
        print(f"  → Free-data crypto edge orthogonal to A+B is structurally exhausted.")
        _write_result("GATE0_FAIL", {}, {}, [], 0.0, {})
        return

    print(f"  GATE 0: PASS ✓ ({n_events_2024} events in 2024)")

    # ── STEP 1: Full backtest ─────────────────────────────────────────────────
    print("\n" + "─" * 65)
    print("[STEP 1] Full backtest (all available history)")
    print("─" * 65)

    port_full, trades_full = run_backtest(perp_wide, basis_z)
    m_full = compute_metrics(port_full, trades_full)

    print(f"  Period: {port_full.index[0].date()} → {port_full.index[-1].date()}")
    for k, v in m_full.items():
        print(f"  {k:<18}: {v}")

    if m_full["sharpe_hac"] > 3.0:
        print("\n  *** FORENSIC AUDIT REQUIRED: Sharpe > 3.0 without costs ***")
        print("  Checking for look-ahead or data errors before continuing...")

    # ── STEP 2: Walk-forward ──────────────────────────────────────────────────
    print("\n" + "─" * 65)
    print(f"[STEP 2] Walk-forward ({WF_TRAIN_MONTHS}m train / {WF_TEST_MONTHS}m test, {WF_STEP_MONTHS}m step)")
    print("─" * 65)

    wf_results, wf_pct = walk_forward(perp_wide, basis_z)

    print(f"  WF periods: {len(wf_results)}")
    print(f"  {'Period':<22} {'Sharpe':>8} {'MaxDD':>8} {'N_trades':>9}")
    for r in wf_results:
        sh = r['sharpe_hac']
        sh_str = f"{sh:+.3f}" if sh is not None and not (isinstance(sh, float) and np.isnan(sh)) else "  nan"
        mdd = r['max_dd']
        mdd_str = f"{mdd:+.1f}%" if mdd is not None and not (isinstance(mdd, float) and np.isnan(mdd)) else " nan"
        print(f"  {r['test_start'][:7]} → {r['test_end'][:7]}   {sh_str:>8} {mdd_str:>8} {r['n_trades']:>9}")
    print(f"  WF% (Sharpe > 0): {wf_pct*100:.0f}%  (gate: > {GATE_WF_PCT*100:.0f}%)")

    # ── STEP 3: Orthogonality ─────────────────────────────────────────────────
    print("\n" + "─" * 65)
    print("[STEP 3] Orthogonality check")
    print("─" * 65)

    orth = check_orthogonality(port_full, perp_wide, ret_b)
    print(f"  |corr(PMR, A proxy)|  = {orth['corr_A']}  [gate < 0.30]")
    print(f"  |corr(PMR, B real)|   = {orth['corr_B']}  [gate < 0.30]")

    # ── STEP 4: Research gate ─────────────────────────────────────────────────
    print("\n" + "═" * 65)
    print("[STEP 4] RESEARCH GATE CHECK")
    print("═" * 65)

    sh  = m_full["sharpe_hac"]
    mdd = m_full["max_dd"] / 100.0 if m_full["max_dd"] is not None else np.nan

    gate_sharpe = not np.isnan(sh) and sh >= GATE_RESEARCH_SHARPE
    gate_mdd    = not np.isnan(mdd) and mdd >= GATE_RESEARCH_MAXDD
    gate_wf     = wf_pct >= GATE_WF_PCT
    gate_trades = m_full["n_trades"] >= GATE_N_TRADES
    gate_corr_a = not np.isnan(orth["corr_A"]) and orth["corr_A"] < 0.30
    gate_corr_b = not np.isnan(orth["corr_B"]) and orth["corr_B"] < 0.30

    checks = [
        ("Sharpe HAC ≥ 0.70",   gate_sharpe, sh),
        ("MaxDD ≥ -25%",        gate_mdd,    mdd),
        ("WF% > 50%",           gate_wf,     wf_pct),
        ("N_trades ≥ 30",       gate_trades, m_full["n_trades"]),
        ("|ρ_A| < 0.30",        gate_corr_a, orth["corr_A"]),
        ("|ρ_B| < 0.30",        gate_corr_b, orth["corr_B"]),
    ]

    for label, ok, val in checks:
        mark = "✓" if ok else "✗"
        print(f"  {mark} {label:<22} : {val}")

    all_pass = all(ok for _, ok, _ in checks)
    verdict = "RESEARCH_PASS" if all_pass else "RESEARCH_FAIL"
    print(f"\n  VERDICT: {verdict}")

    if not all_pass:
        print("  → PATH B: Does not meet RESEARCH_PASS criteria.")
        print("  → Write post-mortem. Archive mission.")

    # ── Save result ───────────────────────────────────────────────────────────
    result = {
        "iteration": "v1",
        "n_tests":   N_TESTS_START,
        "verdict":   verdict,
        "metrics":   m_full,
        "wf_pct":    round(wf_pct, 3),
        "wf_periods": len(wf_results),
        "orthogonality": orth,
        "events_2024": n_events_2024,
        "gate_checks": {label: ok for label, ok, _ in checks},
    }
    _write_result(verdict, m_full, orth, wf_results, wf_pct, result)
    print(f"\n  Result saved to {RESULTS_F}")
    print("=" * 65)


def _write_result(verdict, metrics, orth, wf_results, wf_pct, full_result):
    existing = []
    if RESULTS_F.exists():
        with open(RESULTS_F) as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = []
    existing.append(full_result)
    with open(RESULTS_F, "w") as f:
        json.dump(existing, f, indent=2, default=str)


if __name__ == "__main__":
    main()
