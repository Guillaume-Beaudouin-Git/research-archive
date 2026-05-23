"""
analysis_phase2.py — WAV H3 Phase 2 IC test
============================================

Pre-registered decomposition: Tests A / B / C + lagging gate + D1-D4 + orthogonality.
Gate evaluation order (per HYPOTHESIS_WAV.md):
  GATE 0  → universe size ≥ 20
  GATE 1  → lagging check: corr(attention_z_t, price_ret_7d_prior_t) ≤ 0.30
  GATE 2  → D4: IC_B < 0 (not a momentum proxy)
  GATE 3  → D1: |IC_A| < 0.5 × |IC_B| (WAV dominant over price MR)
  GATE 4  → D2: |IC_B| > |IC_A| AND IC_B < -0.05 AND t_HAC_B < -2.0
  GATE 5  → D3: |IC_B| ≥ 0.01 (not void)
  GATE 6  → orthogonality (informational, not stop)

Usage:
  /usr/bin/python3 analysis_phase2.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ─── Config ──────────────────────────────────────────────────────────────────

SIGNAL_WINDOW_7  = 7
SIGNAL_WINDOW_60 = 60
CS_ZSCORE_MIN_N  = 5       # min tokens for valid CS z-score on a date
ATTN_THRESHOLD   = 1.5     # entry threshold (H3a: top-quintile short)
FWD_DAYS         = 7
HAC_LAG          = 6
MIN_IC_OBS       = 50      # min dates for HAC t-stat
LAGGING_CORR_THR = 0.30
IC_B_DIRECTION_PASS = 0.0  # IC_B must be < 0 (D4)
IC_B_MAGNITUDE_PASS = -0.05
T_HAC_B_PASS        = -2.0
D1_RATIO_THR        = 0.5  # |IC_A| < 0.5 × |IC_B| for D1 pass
D3_VOID_THR         = 0.01
ORTH_THR            = 0.5

DATA_DIR    = Path(__file__).parent / "data"
WIKI_DIR    = DATA_DIR / "wiki"
PRICES_DIR  = DATA_DIR / "prices"

np.random.seed(42)


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_universe() -> list[str]:
    univ_path = DATA_DIR / "universe.json"
    if not univ_path.exists():
        raise FileNotFoundError("Run fetch_data.py first.")
    with open(univ_path) as fh:
        report = json.load(fh)
    return report["_meta"]["valid_tokens"]


def load_wiki_panel(tokens: list[str]) -> pd.DataFrame:
    """Returns wide DataFrame: DatetimeIndex × tokens, values = daily views."""
    frames: dict[str, pd.Series] = {}
    for tok in tokens:
        pq = WIKI_DIR / f"{tok}.parquet"
        if pq.exists():
            frames[tok] = pd.read_parquet(pq)["views"]
    return pd.DataFrame(frames)


def load_price_panel(tokens: list[str]) -> pd.DataFrame:
    """Returns wide DataFrame: DatetimeIndex × tokens, values = daily close."""
    frames: dict[str, pd.Series] = {}
    for tok in tokens:
        pq = PRICES_DIR / f"{tok}.parquet"
        if pq.exists():
            frames[tok] = pd.read_parquet(pq)["close"]
    return pd.DataFrame(frames)


def load_btc_close() -> pd.Series:
    btc_pq = PRICES_DIR / "BTC.parquet"
    if btc_pq.exists():
        return pd.read_parquet(btc_pq)["close"]
    # fallback: any BTC-like file
    fgvd_cache = Path(__file__).parent.parent.parent.parent / (
        "archived/other/fgvd_h1/data/btc_price_raw.parquet"
    )
    if fgvd_cache.exists():
        df = pd.read_parquet(fgvd_cache)
        col = [c for c in df.columns if "close" in c.lower()]
        if col:
            return df[col[0]].dropna().rename("close")
    raise FileNotFoundError("BTC price not found. Run fetch_data.py first.")


# ─── Signal computation ───────────────────────────────────────────────────────

def compute_attention_z(wiki: pd.DataFrame) -> pd.DataFrame:
    """
    attention_raw(t,i) = log(pageviews_7d) - log(7 * pageviews_60d_avg)
    attention_z(t,i)   = CS z-score across tokens at each date t
    """
    # Rolling 7-day sum (inclusive)
    pv7 = wiki.rolling(SIGNAL_WINDOW_7, min_periods=SIGNAL_WINDOW_7).sum()
    # Rolling 60-day average
    pv60 = wiki.rolling(SIGNAL_WINDOW_60, min_periods=SIGNAL_WINDOW_60).mean()
    # Clamp to avoid log(0)
    pv7  = pv7.clip(lower=1.0)
    pv60 = pv60.clip(lower=0.1)
    raw  = np.log(pv7) - np.log(7.0 * pv60)
    # CS z-score
    mu   = raw.mean(axis=1)
    sig  = raw.std(axis=1)
    z    = raw.sub(mu, axis=0).div(sig.replace(0, np.nan), axis=0)
    # Mask dates with too few valid tokens
    n_valid = raw.notna().sum(axis=1)
    z.loc[n_valid < CS_ZSCORE_MIN_N, :] = np.nan
    return z


def compute_price_velocity_z(prices: pd.DataFrame) -> pd.DataFrame:
    """7-day log return, CS z-score."""
    log_ret_7d = np.log(prices).diff(FWD_DAYS)
    mu  = log_ret_7d.mean(axis=1)
    sig = log_ret_7d.std(axis=1)
    z   = log_ret_7d.sub(mu, axis=0).div(sig.replace(0, np.nan), axis=0)
    return z


def compute_forward_return(prices: pd.DataFrame) -> pd.DataFrame:
    """7-day forward log return. Signal at T, return from T+1 to T+8."""
    fwd = np.log(prices.shift(-FWD_DAYS - 1)) - np.log(prices.shift(-1))
    return fwd


# ─── TSMOM signal for orthogonality ──────────────────────────────────────────

def compute_tsmom_btc(btc_close: pd.Series) -> pd.Series:
    """Self-contained TSMOM-28d on BTC. No import from strategies/."""
    log_ret = np.log(btc_close).diff()
    cum_ret = log_ret.rolling(28).sum().shift(1)
    vol     = log_ret.rolling(28).std().shift(1) * np.sqrt(28)
    t_stat  = cum_ret / (vol + 1e-8)
    return np.tanh(t_stat).rename("tsmom_28d")


# ─── IC computation ───────────────────────────────────────────────────────────

def spearman_ic_panel(signal: pd.DataFrame, fwd_ret: pd.DataFrame) -> pd.Series:
    """Per-date cross-sectional Spearman IC (rank correlation signal vs fwd return)."""
    ic_list: list[float] = []
    dates: list[pd.Timestamp] = []

    aligned_signal, aligned_fwd = signal.align(fwd_ret, join="inner", axis=1)
    common_idx = aligned_signal.index.intersection(aligned_fwd.index)

    for dt in common_idx:
        s = aligned_signal.loc[dt].dropna()
        f = aligned_fwd.loc[dt].dropna()
        common = s.index.intersection(f.index)
        if len(common) < 5:
            continue
        rho, _ = stats.spearmanr(s[common].values, f[common].values)
        ic_list.append(rho)
        dates.append(dt)

    return pd.Series(ic_list, index=dates, dtype=float)


def hac_tstat(ic_series: pd.Series, lag: int = HAC_LAG) -> tuple[float, float]:
    """Newey-West HAC t-stat on IC time series."""
    x = ic_series.dropna().values
    n = len(x)
    if n < MIN_IC_OBS:
        return float("nan"), float("nan")

    ic_mean = float(np.mean(x))
    xc      = x - ic_mean

    # Long-run variance via Newey-West
    gamma0 = float(np.mean(xc ** 2))
    lrv    = gamma0
    for k in range(1, lag + 1):
        w     = 1.0 - k / (lag + 1.0)
        gamma = float(np.mean(xc[k:] * xc[:-k]))
        lrv  += 2.0 * w * gamma

    lrv = max(lrv, 1e-12)
    se  = np.sqrt(lrv / n)
    t   = ic_mean / se
    return ic_mean, t


# ─── Lagging gate (pre-IC, GATE 1) ───────────────────────────────────────────

def compute_lagging_correlation(
    attention_z: pd.DataFrame, prices: pd.DataFrame
) -> float:
    """
    corr(attention_z_t, price_ret_7d_prior_t) as panel (stacked) Pearson correlation.
    price_ret_7d_prior = log return of the 7 days BEFORE date t (lagged signal).
    """
    price_ret_prior = np.log(prices).diff(FWD_DAYS)  # 7-day return ending at t

    stacked_attn   = attention_z.stack(dropna=True)
    stacked_prior  = price_ret_prior.reindex_like(attention_z).stack(dropna=True)

    combined = pd.concat([stacked_attn.rename("attn"), stacked_prior.rename("prior")], axis=1).dropna()
    if len(combined) < 100:
        return float("nan")
    rho, _ = stats.pearsonr(combined["attn"].values, combined["prior"].values)
    return float(rho)


# ─── Gate evaluations ─────────────────────────────────────────────────────────

def evaluate_all_gates(
    ic_a: float, t_a: float,
    ic_b: float, t_b: float,
    ic_c: float, t_c: float,
    lagging_corr: float,
    orth_corr: float,
    n_valid_tokens: int,
) -> dict:
    gates: dict[str, dict] = {}
    verdict = "PROCEED"

    # GATE 0 — universe size
    g0_pass = n_valid_tokens >= 20
    gates["GATE_0_universe"] = {
        "n_tokens": n_valid_tokens, "threshold": 20, "pass": g0_pass,
    }
    if not g0_pass:
        return {**gates, "verdict": "STOP_GATE0_SMALL_UNIVERSE"}

    # GATE 1 — lagging check
    g1_pass = (not np.isnan(lagging_corr)) and (lagging_corr <= LAGGING_CORR_THR)
    gates["GATE_1_lagging"] = {
        "corr_attn_price_prior": round(lagging_corr, 4),
        "threshold": LAGGING_CORR_THR, "pass": g1_pass,
        "interpretation": "Wikipedia lags price" if not g1_pass else "OK",
    }
    if not g1_pass:
        return {**gates, "verdict": "STOP_GATE1_LAGGING_PROXY"}

    # GATE 2 — D4 direction
    g2_pass = ic_b < IC_B_DIRECTION_PASS
    gates["GATE_2_D4_direction"] = {
        "IC_B": round(ic_b, 5), "must_be": "< 0", "pass": g2_pass,
        "interpretation": "momentum proxy" if not g2_pass else "contrarian direction",
    }
    if not g2_pass:
        return {**gates, "verdict": "STOP_GATE2_D4_MOMENTUM_PROXY"}

    # GATE 3 — D1 price MR dominance
    abs_a, abs_b = abs(ic_a), abs(ic_b)
    d1_fires = abs_b > 0 and (abs_a >= D1_RATIO_THR * abs_b)
    gates["GATE_3_D1_price_MR"] = {
        "abs_IC_A": round(abs_a, 5), "abs_IC_B": round(abs_b, 5),
        "ratio": round(abs_a / abs_b, 3) if abs_b > 0 else None,
        "threshold": D1_RATIO_THR, "D1_fires": d1_fires,
        "pass": not d1_fires,
    }
    if d1_fires:
        return {**gates, "verdict": "STOP_GATE3_D1_PRICE_MR_DOMINATES"}

    # GATE 4 — D2 WAV magnitude
    d2_a = abs_b > abs_a
    d2_b = ic_b < IC_B_MAGNITUDE_PASS
    d2_c = t_b < T_HAC_B_PASS
    d2_pass = d2_a and d2_b and d2_c
    gates["GATE_4_D2_magnitude"] = {
        "IC_B": round(ic_b, 5), "t_HAC_B": round(t_b, 3),
        "cond_IC_B_gt_IC_A": d2_a, "cond_IC_B_lt_neg005": d2_b, "cond_tHAC_lt_neg2": d2_c,
        "pass": d2_pass,
    }
    if not d2_pass:
        return {**gates, "verdict": "STOP_GATE4_D2_INSUFFICIENT_IC"}

    # GATE 5 — D3 void
    d3_fires = abs_b < D3_VOID_THR
    gates["GATE_5_D3_void"] = {
        "abs_IC_B": round(abs_b, 5), "threshold": D3_VOID_THR, "pass": not d3_fires,
    }
    if d3_fires:
        return {**gates, "verdict": "STOP_GATE5_D3_VOID"}

    # GATE 6 — orthogonality (informational)
    gates["GATE_6_orthogonality"] = {
        "corr_attn_TSMOM": round(orth_corr, 4) if not np.isnan(orth_corr) else None,
        "threshold": ORTH_THR, "pass": abs(orth_corr) < ORTH_THR,
        "note": "informational — not a stop condition",
    }

    return {**gates, "verdict": "PROCEED_TO_PHASE3"}


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("WAV H3 Phase 2 — IC Analysis")
    print("=" * 60)

    # 1. Load universe
    tokens = load_universe()
    print(f"\nValid tokens: {len(tokens)} — {tokens}")

    if len(tokens) < 20:
        print(f"\nGATE 0 FAIL: {len(tokens)} tokens < 20 minimum")
        results = {"verdict": "STOP_GATE0_SMALL_UNIVERSE", "n_tokens": len(tokens)}
        _save(results)
        return

    # 2. Load panels
    wiki   = load_wiki_panel(tokens)
    prices = load_price_panel(tokens)

    # Align to common date range
    common_dates = wiki.index.intersection(prices.index)
    wiki   = wiki.loc[common_dates]
    prices = prices.loc[common_dates]
    print(f"Panel: {len(common_dates)} dates, "
          f"{common_dates[0].date()} → {common_dates[-1].date()}")

    # 3. Compute signals
    print("\nComputing signals...")
    attention_z     = compute_attention_z(wiki)
    price_vel_z     = compute_price_velocity_z(prices)
    fwd_ret         = compute_forward_return(prices)

    # Lag signals by 1 day (signal at T-1, trade at T)
    attention_z_lag  = attention_z.shift(1)
    price_vel_z_lag  = price_vel_z.shift(1)

    signal_a = -price_vel_z_lag           # Test A: naive CS price MR
    signal_b =  attention_z_lag           # Test B: WAV standalone
    signal_c =  attention_z_lag - price_vel_z_lag  # Test C: combined

    # 4. GATE 1 — Lagging check
    print("\nGATE 1: lagging check...")
    lagging_corr = compute_lagging_correlation(attention_z, prices)
    print(f"  corr(attention_z_t, price_ret_7d_prior_t) = {lagging_corr:.4f}")
    if lagging_corr > LAGGING_CORR_THR:
        print(f"  GATE 1 FAIL: corr {lagging_corr:.4f} > {LAGGING_CORR_THR}")
        results = {
            "verdict": "STOP_GATE1_LAGGING_PROXY",
            "lagging_corr": round(lagging_corr, 4),
            "n_tokens": len(tokens),
        }
        _save(results)
        return

    # 5. Compute IC time series
    print("\nComputing cross-sectional ICs (Spearman)...")
    ic_ts_a = spearman_ic_panel(signal_a, fwd_ret)
    ic_ts_b = spearman_ic_panel(signal_b, fwd_ret)
    ic_ts_c = spearman_ic_panel(signal_c, fwd_ret)

    ic_a, t_a = hac_tstat(ic_ts_a)
    ic_b, t_b = hac_tstat(ic_ts_b)
    ic_c, t_c = hac_tstat(ic_ts_c)

    print(f"\n  Test A (−price MR):  IC = {ic_a:+.5f}, t_HAC = {t_a:+.3f}  (n_dates={len(ic_ts_a)})")
    print(f"  Test B (WAV):        IC = {ic_b:+.5f}, t_HAC = {t_b:+.3f}  (n_dates={len(ic_ts_b)})")
    print(f"  Test C (combined):   IC = {ic_c:+.5f}, t_HAC = {t_c:+.3f}  (n_dates={len(ic_ts_c)})")

    # 6. Orthogonality vs TSMOM-28d
    print("\nOrthogonality: corr(attention_z, TSMOM-28d BTC)...")
    try:
        btc_close = load_btc_close()
        tsmom     = compute_tsmom_btc(btc_close)
        # Average attention_z across tokens per date
        attn_mean = attention_z_lag.mean(axis=1).dropna()
        common    = attn_mean.index.intersection(tsmom.index)
        orth_corr = float(stats.pearsonr(attn_mean[common].values, tsmom[common].values)[0]) if len(common) > 50 else float("nan")
        print(f"  corr(attention_z_mean, TSMOM_28d) = {orth_corr:.4f}")
    except Exception as e:
        orth_corr = float("nan")
        print(f"  Orthogonality skipped: {e}")

    # Event count
    n_events = int((attention_z_lag > ATTN_THRESHOLD).sum().sum())
    n_days   = len(common_dates)
    events_per_year = n_events / (n_days / 365.25)
    print(f"\n  Events (attention_z > +{ATTN_THRESHOLD}): {n_events} total, "
          f"{events_per_year:.0f}/year ({n_days/365.25:.1f}yr window)")

    # 7. Gate evaluation
    print("\nEvaluating all gates...")
    gate_results = evaluate_all_gates(
        ic_a, t_a, ic_b, t_b, ic_c, t_c,
        lagging_corr, orth_corr, len(tokens),
    )

    verdict = gate_results["verdict"]
    print(f"\n{'=' * 60}")
    print(f"VERDICT: {verdict}")
    print(f"{'=' * 60}")

    # 8. Save results
    results = {
        "verdict": verdict,
        "n_tokens": len(tokens),
        "tokens": tokens,
        "panel_dates": n_days,
        "panel_start": str(common_dates[0].date()),
        "panel_end":   str(common_dates[-1].date()),
        "lagging_corr": round(lagging_corr, 5),
        "ic_a": round(ic_a, 6) if not np.isnan(ic_a) else None,
        "t_hac_a": round(t_a, 4) if not np.isnan(t_a) else None,
        "ic_b": round(ic_b, 6) if not np.isnan(ic_b) else None,
        "t_hac_b": round(t_b, 4) if not np.isnan(t_b) else None,
        "ic_c": round(ic_c, 6) if not np.isnan(ic_c) else None,
        "t_hac_c": round(t_c, 4) if not np.isnan(t_c) else None,
        "n_events_total": n_events,
        "events_per_year": round(events_per_year, 1),
        "orth_corr_tsmom": round(orth_corr, 4) if not np.isnan(orth_corr) else None,
        "ic_dates_a": len(ic_ts_a), "ic_dates_b": len(ic_ts_b), "ic_dates_c": len(ic_ts_c),
        "gates": gate_results,
    }
    _save(results)


def _save(results: dict) -> None:
    out = DATA_DIR / "phase2_results.json"
    with open(out, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nResults saved → {out}")


if __name__ == "__main__":
    main()
