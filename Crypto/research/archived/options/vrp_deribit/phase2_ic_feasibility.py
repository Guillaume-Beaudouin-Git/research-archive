"""
phase2_ic_feasibility.py — VRP Phase 2 IC Feasibility Test

Hypothesis: DVOL[t-1]^2 - RV30[t-1]^2 predicts forward 16-day delta-hedged
straddle P&L on Deribit BTC options.

Signal (T-1, no look-ahead):
    VRP_signal[t] = DVOL[t]^2 - RV30[t]^2   (variance spread, annualized)

Outcome (T+1 to T+1+HOLD_DAYS):
    PnL%[t] ≈ ½ × N'(0) × (DVOL_entry^2 − RV_realized^2) × T_hold / DVOL_entry
    (Black-Scholes delta-hedge P&L approximation, normalized by notional)

GATE 2 targets: IC > 0.10, t_HAC > 2.5, event count ∈ [12, 50]/yr

N_tests increment: +1 (this IC test) → total 153 → 154.
HARD STOP: output IC results only. Do NOT run backtest (Phase 3).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[4]  # Algo_claude/
CACHE_DIR  = REPO_ROOT / "data" / "vrp" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_PATH = Path(__file__).parent / "phase2_ic_results.json"

# ── Strategy parameters ────────────────────────────────────────────────────────
HOLD_DAYS  = 16          # 30 DTE → 14 DTE roll (Decision 1)
RV_WINDOW  = 30          # days for trailing RV computation
HAC_LAGS   = 6           # Newey-West HAC lags (per CLAUDE.md methodology)
START_DATE = "2021-04-01"  # earliest DVOL data from Deribit

DERIBIT_BASE = "https://www.deribit.com/api/v2"
BN_BASE      = "https://api.binance.com"

# ── API helpers ────────────────────────────────────────────────────────────────

def _to_ms(date_str: str) -> int:
    return int(pd.Timestamp(date_str, tz="UTC").timestamp() * 1000)

def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def fetch_dvol_deribit(currency: str = "BTC") -> pd.Series:
    """
    Fetch DVOL daily candles from Deribit public API.
    Returns Series of DVOL close values, indexed by UTC date.
    Caches result to parquet.

    Deribit returns at most 1000 bars per call and ignores start_timestamp when
    the range exceeds 1000 bars — returning the LAST 1000 in [start, end].
    We therefore paginate backward: each iteration sets end_ms = first_bar - 1ms
    until the first returned bar is at or before START_DATE.
    """
    cache = CACHE_DIR / f"{currency}_dvol_1d.parquet"
    if cache.exists():
        df = pd.read_parquet(cache)
        print(f"  DVOL: loaded {len(df)} days from cache ({df.index[0].date()} → {df.index[-1].date()})")
        return df["dvol"]

    print(f"  DVOL: fetching from Deribit API ({START_DATE} → now) with backward pagination...")
    start_ms = _to_ms(START_DATE)

    # Probe to find a working resolution
    working_resolution = None
    for resolution in ["1D", "86400", "1440"]:
        try:
            r = requests.get(
                f"{DERIBIT_BASE}/public/get_volatility_index_data",
                params={
                    "currency":        currency,
                    "start_timestamp": start_ms,
                    "end_timestamp":   _now_ms(),
                    "resolution":      resolution,
                },
                timeout=30,
            )
            r.raise_for_status()
            data = r.json().get("result", {}).get("data", [])
            if data:
                working_resolution = resolution
                print(f"  DVOL: resolution='{resolution}' works")
                break
        except Exception as exc:
            print(f"  DVOL: resolution='{resolution}' failed: {exc}")

    if working_resolution is None:
        raise RuntimeError("Failed to fetch DVOL data from Deribit. Check API connectivity.")

    # Backward pagination: get chunks from present toward START_DATE
    all_rows: list = []
    current_end_ms = _now_ms()

    while True:
        r = requests.get(
            f"{DERIBIT_BASE}/public/get_volatility_index_data",
            params={
                "currency":        currency,
                "start_timestamp": start_ms,
                "end_timestamp":   current_end_ms,
                "resolution":      working_resolution,
            },
            timeout=30,
        )
        r.raise_for_status()
        chunk = r.json().get("result", {}).get("data", [])
        if not chunk:
            break

        # Prepend chunk (going backward, each chunk is earlier in time)
        all_rows = chunk + all_rows
        first_bar_ts = chunk[0][0]
        last_bar_ts  = chunk[-1][0]
        first_date   = pd.to_datetime(first_bar_ts, unit="ms").date()
        print(f"  DVOL: chunk {len(chunk)} bars  ({first_date} → {pd.to_datetime(last_bar_ts, unit='ms').date()})"
              f"  total={len(all_rows)}")

        # Stop if this chunk already reaches or precedes START_DATE
        if first_bar_ts <= start_ms or len(chunk) < 1000:
            break

        # Next iteration: end just before the first bar of this chunk
        current_end_ms = first_bar_ts - 1
        time.sleep(0.3)

    if not all_rows:
        raise RuntimeError("Failed to fetch any DVOL data from Deribit.")

    # rows format: [[ts_ms, open, high, low, close], ...]
    df = pd.DataFrame(all_rows, columns=["ts_ms", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True).dt.normalize()
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df[["close"]].rename(columns={"close": "dvol"})
    df["dvol"] = df["dvol"].astype(float) / 100.0  # convert % to decimal (e.g. 80.0 → 0.80)
    df.to_parquet(cache)
    print(f"  DVOL: saved {len(df)} days to cache ({df.index[0].date()} → {df.index[-1].date()})")
    return df["dvol"]


def fetch_btc_daily_binance() -> pd.Series:
    """
    Fetch BTC/USDT daily close prices from Binance public API.
    Returns Series of close prices indexed by UTC date.
    Caches result to parquet.
    """
    cache = CACHE_DIR / "BTC_daily_close.parquet"
    if cache.exists():
        df = pd.read_parquet(cache)
        print(f"  BTC:  loaded {len(df)} days from cache ({df.index[0].date()} → {df.index[-1].date()})")
        return df["close"]

    print(f"  BTC:  fetching from Binance API ({START_DATE} → now)...")
    start_ms = _to_ms(START_DATE)
    end_ms   = _now_ms()
    all_klines: list = []

    while True:
        r = requests.get(
            f"{BN_BASE}/api/v3/klines",
            params={
                "symbol":    "BTCUSDT",
                "interval":  "1d",
                "startTime": start_ms,
                "limit":     1000,
            },
            timeout=30,
        )
        r.raise_for_status()
        klines = r.json()
        if not klines:
            break
        all_klines.extend(klines)
        if len(klines) < 1000:
            break
        start_ms = klines[-1][0] + 1
        time.sleep(0.1)

    df = pd.DataFrame(all_klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.normalize()
    df["close"] = df["close"].astype(float)
    df = df.set_index("timestamp")[["close"]].sort_index()
    df.to_parquet(cache)
    print(f"  BTC:  saved {len(df)} days to cache")
    return df["close"]


# ── Signal computation ─────────────────────────────────────────────────────────

def compute_rv(btc_close: pd.Series, window: int = RV_WINDOW) -> pd.Series:
    """
    Trailing realized volatility: sqrt(365/window × Σ r²_d).
    Uses close-to-close log returns.
    """
    log_ret = np.log(btc_close / btc_close.shift(1))
    rv = np.sqrt(log_ret.pow(2).rolling(window).sum() * (365.0 / window))
    rv.name = f"rv{window}"
    return rv


def compute_vrp_signal(dvol: pd.Series, rv: pd.Series) -> pd.Series:
    """
    VRP signal in VARIANCE terms (annualized): DVOL^2 - RV30^2.
    Both inputs must be in decimal (e.g., 0.80 for 80%).
    """
    vrp = dvol.pow(2) - rv.pow(2)
    vrp.name = "vrp_signal"
    return vrp


def compute_straddle_pnl_approx(
    dvol_entry: pd.Series,
    rv_realized_forward: pd.Series,
    hold_days: int = HOLD_DAYS,
) -> pd.Series:
    """
    Black-Scholes approximation of delta-hedged short straddle P&L (% of notional):

        PnL% ≈ ½ × N'(0) × (DVOL_entry² − RV_realized²) × T_hold / DVOL_entry

    Where N'(0) = 0.3989, T_hold = hold_days/365.

    This is the theoretical P&L for a continuously delta-hedged position,
    normalized by underlying notional. Positive → short-vol profitable.
    """
    N_prime_0 = 0.3989270  # standard normal PDF at 0
    T_hold    = hold_days / 365.0

    pnl = (
        0.5
        * N_prime_0
        * (dvol_entry.pow(2) - rv_realized_forward.pow(2))
        * T_hold
        / dvol_entry.clip(lower=0.01)  # avoid division by zero
    )
    pnl.name = "pnl_approx_pct"
    return pnl


def build_aligned_dataset(
    dvol: pd.Series,
    btc_close: pd.Series,
) -> pd.DataFrame:
    """
    Align DVOL + BTC data and compute all signals on a common daily index.

    Signal timing (no look-ahead):
        signal[t] = VRP computed at end of day t (using data up to close of t)
        pnl[t]    = forward P&L from open of t+1 to close of t+HOLD_DAYS

    Returns DataFrame with columns:
        dvol, rv30, vrp_signal, rv_forward, pnl_approx, btc_close
    """
    # Align on common dates
    common = dvol.index.intersection(btc_close.index)
    dvol  = dvol.reindex(common).ffill()
    btc   = btc_close.reindex(common).ffill()

    rv30 = compute_rv(btc, window=RV_WINDOW)

    # VRP signal (lag will be applied in IC test: signal[t-1] → pnl[t:t+HOLD_DAYS])
    vrp = compute_vrp_signal(dvol, rv30)

    # Forward realized vol: realized vol WITHIN the holding period [t+1, t+HOLD_DAYS]
    log_ret = np.log(btc / btc.shift(1))

    # Rolling forward RV over HOLD_DAYS: for each day t, compute RV from t+1 to t+HOLD_DAYS
    rv_forward = (
        log_ret.pow(2)
        .rolling(HOLD_DAYS)
        .sum()
        .shift(-HOLD_DAYS)       # shift backward = forward look
        .apply(lambda x: np.sqrt(x * 365.0 / HOLD_DAYS))
    )
    rv_forward.name = "rv_forward"

    # Forward DVOL at entry (= DVOL[t+1], since we trade at T+1)
    dvol_entry = dvol.shift(-1)  # DVOL at entry = next day's DVOL open
    dvol_entry.name = "dvol_entry"

    # Approximated straddle P&L
    pnl = compute_straddle_pnl_approx(dvol_entry, rv_forward, hold_days=HOLD_DAYS)

    df = pd.concat([dvol, rv30, vrp, dvol_entry, rv_forward, pnl, btc], axis=1)
    df.columns = ["dvol", "rv30", "vrp_signal", "dvol_entry", "rv_forward", "pnl_approx", "btc_close"]
    df = df.dropna()
    return df


# ── IC test ────────────────────────────────────────────────────────────────────

def run_ic_test_hac(
    signal: pd.Series,
    outcome: pd.Series,
    hac_lags: int = HAC_LAGS,
    label: str = "",
) -> dict:
    """
    IC test with HAC-corrected t-statistic.
    Uses OLS regression of ranks(outcome) on ranks(signal) → HAC(maxlags).
    Also reports raw Spearman correlation.
    """
    df = pd.concat([signal.rename("sig"), outcome.rename("out")], axis=1).dropna()
    n = len(df)
    if n < 20:
        return {"n": n, "ic": np.nan, "t_hac": np.nan, "label": label, "error": "insufficient data"}

    spearman_rho, spearman_p = stats.spearmanr(df["sig"], df["out"])

    # HAC t-stat via OLS on standardized (ranked) values
    rank_sig = df["sig"].rank()
    rank_out = df["out"].rank()
    X = sm.add_constant(rank_sig.values)
    model = sm.OLS(rank_out.values, X)
    res = model.fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    t_hac = float(res.tvalues[1])

    return {
        "label":        label,
        "n_obs":        n,
        "ic":           round(float(spearman_rho), 4),
        "spearman_p":   round(float(spearman_p), 4),
        "t_hac":        round(t_hac, 3),
        "ic_significant": abs(t_hac) > 2.5 and float(spearman_rho) > 0.10,
    }


def run_yearly_ic(df: pd.DataFrame, signal_col: str, outcome_col: str) -> dict:
    """Year-by-year IC breakdown (sign stability check)."""
    results = {}
    for year, grp in df.groupby(df.index.year):
        if len(grp) < 15:
            results[year] = {"n": len(grp), "ic": np.nan, "positive": None}
            continue
        rho, p = stats.spearmanr(grp[signal_col].dropna(), grp[outcome_col].dropna())
        results[year] = {
            "n":        len(grp),
            "ic":       round(float(rho), 4),
            "positive": bool(rho > 0),
        }
    n_positive = sum(1 for v in results.values() if v.get("positive") is True)
    n_total    = sum(1 for v in results.values() if v.get("positive") is not None)
    results["_summary"] = {
        "pct_positive_years": round(n_positive / n_total, 3) if n_total > 0 else None,
        "n_years": n_total,
    }
    return results


def evaluate_gates(ic_full: dict, ic_monthly: dict, yearly: dict) -> dict:
    """Apply GATE 2 criteria and return pass/fail per criterion."""
    ic_val    = ic_full.get("ic", 0)
    t_hac_val = ic_full.get("t_hac", 0)
    pct_pos   = yearly.get("_summary", {}).get("pct_positive_years", 0) or 0

    gates = {
        "G1_ic_magnitude":    {"threshold": "> 0.10",  "value": ic_val,    "pass": ic_val > 0.10},
        "G2_t_hac":           {"threshold": "> 2.50",  "value": t_hac_val, "pass": t_hac_val > 2.50},
        "G3_ic_direction":    {"threshold": "> 0",     "value": ic_val,    "pass": ic_val > 0},
        "G4_subperiod_stab":  {"threshold": ">= 0.67 years positive",
                               "value": pct_pos, "pass": pct_pos >= 0.67},
        "G5_event_count":     {"threshold": "[12, 50]/yr",
                               "note": "monthly rebalance = ~22/yr (1 per 16 days)", "pass": True},
    }

    n_pass  = sum(1 for g in gates.values() if g.get("pass"))
    verdict = "PASS" if n_pass >= 4 else ("BORDERLINE" if n_pass == 3 else "FAIL")
    gates["_verdict"] = {
        "pass_count": n_pass,
        "total_gates": 5,
        "verdict": verdict,
        "action": {
            "PASS":       "Proceed to Phase 3 (with user GO)",
            "BORDERLINE": "Flag for user review — do NOT auto-proceed",
            "FAIL":       "ARCHIVE vrp_deribit angle",
        }.get(verdict, "unknown"),
    }
    return gates


# ── Reporting ─────────────────────────────────────────────────────────────────

def compute_descriptive_stats(df: pd.DataFrame) -> dict:
    """Summary statistics for signal and P&L."""
    vrp = df["vrp_signal"]
    pnl = df["pnl_approx"]
    dvol = df["dvol"]
    rv30 = df["rv30"]

    return {
        "date_range": {
            "start": str(df.index[0].date()),
            "end":   str(df.index[-1].date()),
            "n_days": len(df),
        },
        "dvol_stats": {
            "mean": round(float(dvol.mean()), 4),
            "std":  round(float(dvol.std()),  4),
            "min":  round(float(dvol.min()),  4),
            "max":  round(float(dvol.max()),  4),
        },
        "rv30_stats": {
            "mean": round(float(rv30.mean()), 4),
            "std":  round(float(rv30.std()),  4),
        },
        "vrp_signal_stats": {
            "mean":     round(float(vrp.mean()), 4),
            "std":      round(float(vrp.std()),  4),
            "pct_positive": round(float((vrp > 0).mean()), 3),
            "annualized_vrp_mean": round(float(vrp.mean()), 4),
        },
        "pnl_approx_stats": {
            "mean_per_cycle":  round(float(pnl.mean()), 4),
            "std_per_cycle":   round(float(pnl.std()),  4),
            "pct_positive":    round(float((pnl > 0).mean()), 3),
            "sharpe_raw":      round(float(pnl.mean() / pnl.std() * np.sqrt(365 / HOLD_DAYS)), 3),
        },
    }


def sample_monthly_observations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sample at cycle start frequency (~every HOLD_DAYS days) for non-overlapping IC.
    Returns one observation per cycle to avoid overlap bias.
    """
    cycle_starts = df.index[::HOLD_DAYS]
    return df.reindex(cycle_starts).dropna()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n══════════════════════════════════════════════════════════════════════")
    print(" VRP PHASE 2 — IC FEASIBILITY TEST")
    print(" Signal: DVOL[t-1]^2 - RV30[t-1]^2 → 16d delta-hedged straddle PnL")
    print("══════════════════════════════════════════════════════════════════════\n")

    # ── 1. Load data ─────────────────────────────────────────────────────────
    print("── Fetching data ──────────────────────────────────────────────────")
    dvol      = fetch_dvol_deribit("BTC")
    btc_close = fetch_btc_daily_binance()

    # ── 2. Build aligned dataset ─────────────────────────────────────────────
    print("\n── Building signals ───────────────────────────────────────────────")
    df = build_aligned_dataset(dvol, btc_close)
    print(f"  Aligned data: {len(df)} days ({df.index[0].date()} → {df.index[-1].date()})")

    # Signal: lagged by 1 day (trade at T+1, signal from T)
    signal_full = df["vrp_signal"].shift(1).rename("vrp_lag1")
    outcome_full = df["pnl_approx"]

    # ── 3. IC tests ─────────────────────────────────────────────────────────
    print("\n── IC tests ───────────────────────────────────────────────────────")

    # 3a. Full daily sample (overlapping 16-day windows, HAC corrects for overlap)
    aligned_full = pd.concat([signal_full, outcome_full], axis=1).dropna()
    ic_full = run_ic_test_hac(
        aligned_full["vrp_lag1"],
        aligned_full["pnl_approx"],
        hac_lags=HAC_LAGS,
        label="daily_overlapping_HAC6",
    )

    # 3b. Non-overlapping sample (1 obs per cycle, ~every 16 days)
    df_monthly = sample_monthly_observations(df)
    signal_monthly  = df_monthly["vrp_signal"].shift(1)
    outcome_monthly = df_monthly["pnl_approx"]
    ic_monthly = run_ic_test_hac(
        signal_monthly, outcome_monthly,
        hac_lags=min(HAC_LAGS, len(df_monthly) // 5),  # adjust lags for smaller n
        label="non_overlapping_cycle_sample",
    )

    # 3c. Year-by-year IC
    df_for_yearly = df.copy()
    df_for_yearly["vrp_lag1"] = df_for_yearly["vrp_signal"].shift(1)
    df_for_yearly = df_for_yearly.dropna(subset=["vrp_lag1", "pnl_approx"])
    yearly_ic = run_yearly_ic(df_for_yearly, "vrp_lag1", "pnl_approx")

    # ── 4. Descriptive stats ─────────────────────────────────────────────────
    desc = compute_descriptive_stats(df)

    # ── 5. GATE 2 evaluation ─────────────────────────────────────────────────
    gates = evaluate_gates(ic_full, ic_monthly, yearly_ic)

    # ── 6. Print results ─────────────────────────────────────────────────────
    print("\n══════════════════════════════════════════════════════════════════════")
    print(" DESCRIPTIVE STATISTICS")
    print("══════════════════════════════════════════════════════════════════════")
    print(f"  Data range   : {desc['date_range']['start']} → {desc['date_range']['end']} ({desc['date_range']['n_days']} days)")
    print(f"  DVOL mean    : {desc['dvol_stats']['mean']:.2%}  (std {desc['dvol_stats']['std']:.2%})")
    print(f"  RV30 mean    : {desc['rv30_stats']['mean']:.2%}  (std {desc['rv30_stats']['std']:.2%})")
    print(f"  VRP signal   : mean={desc['vrp_signal_stats']['mean']:.4f}  pct_positive={desc['vrp_signal_stats']['pct_positive']:.0%}")
    print(f"  PnL% (cycle) : mean={desc['pnl_approx_stats']['mean_per_cycle']:.4f}  std={desc['pnl_approx_stats']['std_per_cycle']:.4f}")
    print(f"  PnL Sharpe   : {desc['pnl_approx_stats']['sharpe_raw']:.3f}  (raw, pre-costs)")

    print("\n══════════════════════════════════════════════════════════════════════")
    print(" IC TEST RESULTS")
    print("══════════════════════════════════════════════════════════════════════")
    print(f"\n  [DAILY OVERLAPPING — primary, HAC({HAC_LAGS})]")
    print(f"    n_obs   : {ic_full['n_obs']}")
    print(f"    IC      : {ic_full['ic']:.4f}  (Spearman ρ)")
    print(f"    t_HAC   : {ic_full['t_hac']:.3f}")
    print(f"    p_Spear : {ic_full.get('spearman_p', 'n/a')}")

    print(f"\n  [NON-OVERLAPPING CYCLE SAMPLE — secondary]")
    print(f"    n_obs   : {ic_monthly['n_obs']}")
    print(f"    IC      : {ic_monthly['ic']:.4f}")
    print(f"    t_HAC   : {ic_monthly['t_hac']:.3f}")

    print("\n  [YEAR-BY-YEAR IC]")
    for yr, v in sorted((k, v) for k, v in yearly_ic.items() if k != "_summary"):
        pos = "+" if v.get("positive") else ("-" if v.get("positive") is False else "?")
        print(f"    {yr} : IC={v['ic']:.4f}  ({pos})  n={v['n']}")
    print(f"  Sub-period stability: {yearly_ic['_summary']['pct_positive_years']:.0%} of years IC > 0")

    print("\n══════════════════════════════════════════════════════════════════════")
    print(" GATE 2 EVALUATION")
    print("══════════════════════════════════════════════════════════════════════")
    for gate_name, gate in gates.items():
        if gate_name.startswith("_"):
            continue
        icon = "✓" if gate.get("pass") else "✗"
        val  = gate.get("value", gate.get("note", ""))
        thr  = gate.get("threshold", "")
        print(f"  {icon} {gate_name:<22} value={val}  (threshold: {thr})")

    verdict_info = gates["_verdict"]
    print(f"\n  VERDICT : {verdict_info['verdict']} ({verdict_info['pass_count']}/{verdict_info['total_gates']} gates)")
    print(f"  ACTION  : {verdict_info['action']}")
    print("══════════════════════════════════════════════════════════════════════")

    print("\n  ⚠️  HARD STOP: Do NOT launch Phase 3 without user GO.")
    print("  N_tests: 153 → 154 (+1 for this IC test)")

    # ── 7. Save JSON results ─────────────────────────────────────────────────
    results = {
        "run_timestamp":  datetime.now(timezone.utc).isoformat(),
        "n_tests_before": 153,
        "n_tests_after":  154,
        "hold_days":      HOLD_DAYS,
        "rv_window":      RV_WINDOW,
        "hac_lags":       HAC_LAGS,
        "descriptive":    desc,
        "ic_daily_overlapping": ic_full,
        "ic_non_overlapping":   ic_monthly,
        "yearly_ic":      {str(k): v for k, v in yearly_ic.items()},
        "gates":          {k: {
            "pass": v.get("pass"),
            "value": str(v.get("value", v.get("note", ""))),
            "threshold": v.get("threshold", ""),
        } for k, v in gates.items() if not k.startswith("_")},
        "verdict": verdict_info,
        "hard_stop": "Do NOT proceed to Phase 3 without explicit user GO.",
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {RESULTS_PATH}")
    print("  Done.\n")


if __name__ == "__main__":
    main()
