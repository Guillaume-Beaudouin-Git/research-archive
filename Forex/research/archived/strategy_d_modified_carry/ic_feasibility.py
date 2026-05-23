"""
Strategy D Modified Carry — IC Feasibility Test
================================================
Phase 1, Step 4: Cross-sectional IC test of raw and REER-modified carry.

Tests (n_tests consumed):
  n=173 — raw carry (z_carry only)
  n=174 — REER-modified carry (0.5 × z_carry + 0.5 × (−z_reer_dev))

Gate (STOP):
  IC_raw < 0.02 → STOP, do not launch full backtest
  IC_modified < IC_raw → REER adds no information, reconsider hypothesis

Gate (GO, soft):
  IC_modified > 0.02 AND t_HAC_lag6 > 1.65

Gate (GO, hard):
  IC_modified > 0.04 AND t_HAC_lag6 > 2.5

Run: python -m Forex.research.active.strategy_d_modified_carry.ic_feasibility
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Adjust sys.path so relative imports work when run as script
_ROOT = Path(__file__).parents[5]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Forex.backtest.metrics import cross_sectional_ic, ic_summary
from Forex.data.fred_loader import load_g10_rates
from Forex.data.bis_reer_loader import load_bis_reer, compute_reer_zscore
from Forex.data.dukascopy_loader import load_fx_returns

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
START       = "2005-01-01"
END         = "2026-05-01"
G10_CCYS    = ["EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "NOK", "SEK"]
REER_WINDOW = 10    # years for rolling z-score
HAC_LAGS    = 6
MIN_OBS_CS  = 5     # minimum non-NaN currencies per period for IC

N_TESTS_RAW_CARRY     = 173
N_TESTS_MODIFIED_REER = 174

_RESULTS_PATH = Path(__file__).parent / "results.json"

# Gate thresholds
IC_STOP_GATE   = 0.02   # IC_raw < 0.02 → archive immediately
IC_SOFT_GATE   = 0.02   # IC_modified > 0.02 (soft GO with t > 1.65)
IC_HARD_GATE   = 0.04   # IC_modified > 0.04 (strong GO with t > 2.5)
T_SOFT         = 1.65
T_HARD         = 2.5


# ─────────────────────────────────────────────────────────────────────────────
# Signal construction (inline, not imported from signal.py)
# ─────────────────────────────────────────────────────────────────────────────

def _cs_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Row-wise cross-sectional z-score."""
    return df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1, ddof=1), axis=0)


def build_raw_carry(rates: pd.DataFrame) -> pd.DataFrame:
    """
    Raw carry = r_foreign - r_USD, cross-sectionally z-scored.
    Signal at T-1 (already shifted by caller).
    """
    usd = rates["USD"]
    ccys = [c for c in G10_CCYS if c in rates.columns]
    carry = rates[ccys].sub(usd, axis=0)
    return _cs_zscore(carry)


def build_modified_carry(
    rates: pd.DataFrame,
    reer:  pd.DataFrame,
    w_carry: float = 0.5,
    w_reer:  float = 0.5,
) -> pd.DataFrame:
    """
    Modified carry = w_carry × z_carry + w_reer × (−z_reer_dev).

    Overvalued currency (positive z_reer) → negative REER signal → reduces
    carry weight. Undervalued → positive → augments carry.

    Signal at T-1 (caller has shifted both inputs).
    """
    z_carry = build_raw_carry(rates)

    ccys_reer = [c for c in G10_CCYS if c in reer.columns]
    z_reer_dev = compute_reer_zscore(reer[ccys_reer], REER_WINDOW)
    reer_signal = -z_reer_dev   # overvalued = reduce

    # Align on common currencies and dates
    common_ccys = list(set(z_carry.columns) & set(reer_signal.columns))
    common_idx  = z_carry.index.intersection(reer_signal.index)

    sig = (w_carry * _cs_zscore(z_carry[common_ccys].loc[common_idx])
           + w_reer * _cs_zscore(reer_signal[common_ccys].loc[common_idx]))
    return sig


# ─────────────────────────────────────────────────────────────────────────────
# VIX regime analysis
# ─────────────────────────────────────────────────────────────────────────────

def _load_vix(start: str, end: str) -> pd.Series:
    """Load VIX monthly closing level via yfinance."""
    try:
        import yfinance as yf
        df = yf.download("^VIX", start=start, end=end, interval="1d",
                         auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            close = df["Close"].iloc[:, 0]
        else:
            close = df["Close"]
        vix_monthly = close.resample("M").last()
        return vix_monthly.rename("VIX")
    except Exception as exc:
        log.warning("VIX fetch failed: %s — regime analysis skipped", exc)
        return pd.Series(dtype=float, name="VIX")


def ic_by_vix_regime(
    ic_series:  pd.Series,
    vix_monthly: pd.Series,
) -> dict[str, dict]:
    """IC summary split by VIX terciles (low/medium/high)."""
    if vix_monthly.empty or ic_series.empty:
        return {}
    aligned = pd.concat([ic_series, vix_monthly], axis=1, join="inner")
    aligned.columns = ["ic", "vix"]
    if len(aligned) < 12:
        return {}
    q33, q66 = aligned["vix"].quantile(0.33), aligned["vix"].quantile(0.66)
    regimes = {
        "low_vix":  aligned[aligned["vix"] <= q33]["ic"],
        "mid_vix":  aligned[(aligned["vix"] > q33) & (aligned["vix"] <= q66)]["ic"],
        "high_vix": aligned[aligned["vix"] > q66]["ic"],
    }
    return {k: ic_summary(v, HAC_LAGS) for k, v in regimes.items()}


def ic_by_decade(ic_series: pd.Series) -> dict[str, dict]:
    """IC summary by decade."""
    out = {}
    for label, (yr_s, yr_e) in [("2005_2010", (2005, 2010)),
                                  ("2010_2018", (2010, 2018)),
                                  ("2018_2026", (2018, 2027))]:
        subset = ic_series.loc[
            (ic_series.index.year >= yr_s) & (ic_series.index.year < yr_e)
        ]
        if len(subset) >= 6:
            out[label] = ic_summary(subset, HAC_LAGS)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> dict:
    log.info("=" * 68)
    log.info("Strategy D — IC Feasibility Test")
    log.info("n=173 (raw carry), n=174 (REER-modified)")
    log.info("=" * 68)

    # ── 1. Load data ──────────────────────────────────────────────────────────
    log.info("[1/5] Loading FRED 3M rates...")
    rates = load_g10_rates(START, END)
    log.info("  Rates shape: %s | range: %s → %s", rates.shape,
             rates.index[0].date(), rates.index[-1].date())

    log.info("[2/5] Loading FX monthly returns (yfinance)...")
    fx_ret = load_fx_returns(G10_CCYS, START, END)
    log.info("  FX returns shape: %s | range: %s → %s", fx_ret.shape,
             fx_ret.index[0].date(), fx_ret.index[-1].date())

    log.info("[3/5] Loading BIS REER (broad, with 1M pub lag)...")
    reer_available = True
    try:
        reer = load_bis_reer(START, END, currencies=G10_CCYS + ["USD"])
        log.info("  REER shape: %s | range: %s → %s", reer.shape,
                 reer.index[0].date(), reer.index[-1].date())
    except Exception as exc:
        log.warning("  BIS REER load failed: %s — modified carry test skipped", exc)
        reer = pd.DataFrame()
        reer_available = False

    # ── 2. Align and compute signals ─────────────────────────────────────────
    log.info("[4/5] Computing signals and IC...")

    # All inputs shifted by 1 (signal at T-1, return at T)
    rates_lagged = rates.shift(1)

    # Signal test 1: raw carry (n=173)
    sig_raw = build_raw_carry(rates_lagged)

    # Align with returns
    idx = sig_raw.index.intersection(fx_ret.index)
    sig_raw_al = sig_raw.loc[idx]
    ret_al     = fx_ret.loc[idx]

    ic_raw_series = cross_sectional_ic(sig_raw_al, ret_al, min_obs=MIN_OBS_CS)
    ic_raw        = ic_summary(ic_raw_series, HAC_LAGS)

    log.info("  RAW CARRY (n=%d): IC_mean=%.4f  IC_std=%.4f  t_HAC=%.2f  n_periods=%d",
             N_TESTS_RAW_CARRY, ic_raw["ic_mean"], ic_raw["ic_std"],
             ic_raw["t_hac_lag6"], ic_raw["ic_n"])

    # Gate check: STOP if IC_raw < 0.02
    if ic_raw["ic_mean"] < IC_STOP_GATE:
        log.warning("  STOP GATE: IC_raw=%.4f < %.2f — ARCHIVE IMMEDIATELY",
                    ic_raw["ic_mean"], IC_STOP_GATE)

    # Signal test 2: REER-modified carry (n=174)
    ic_modified = {}
    ic_modified_series = pd.Series(dtype=float)
    modified_carry_available = False

    if reer_available and not reer.empty:
        reer_lagged = reer.shift(1)   # additional lag: signal uses T-2 REER
        try:
            sig_mod = build_modified_carry(rates_lagged, reer_lagged)
            idx_mod = sig_mod.index.intersection(fx_ret.index)
            ic_mod_series = cross_sectional_ic(
                sig_mod.loc[idx_mod], fx_ret.loc[idx_mod], min_obs=MIN_OBS_CS)
            ic_modified   = ic_summary(ic_mod_series, HAC_LAGS)
            ic_modified_series = ic_mod_series
            modified_carry_available = True

            log.info("  MODIFIED CARRY (n=%d): IC_mean=%.4f  IC_std=%.4f  t_HAC=%.2f  n_periods=%d",
                     N_TESTS_MODIFIED_REER, ic_modified["ic_mean"], ic_modified["ic_std"],
                     ic_modified["t_hac_lag6"], ic_modified["ic_n"])
        except Exception as exc:
            log.warning("  Modified carry computation failed: %s", exc)

    # ── 3. Regime analysis ─────────────────────────────────────────────────
    log.info("[5/5] Regime analysis (VIX + decade)...")
    vix = _load_vix(START, END)
    ic_series_for_regime = ic_modified_series if modified_carry_available else ic_raw_series

    by_vix    = ic_by_vix_regime(ic_series_for_regime, vix)
    by_decade = ic_by_decade(ic_series_for_regime)

    # ── 4. Decision logic ──────────────────────────────────────────────────
    ic_val  = ic_modified.get("ic_mean", np.nan) if modified_carry_available else ic_raw["ic_mean"]
    t_val   = ic_modified.get("t_hac_lag6", np.nan) if modified_carry_available else ic_raw["t_hac_lag6"]

    if ic_raw["ic_mean"] < IC_STOP_GATE:
        recommendation = "STOP"
        recommendation_detail = (
            f"Raw carry IC ({ic_raw['ic_mean']:.4f}) below stop gate ({IC_STOP_GATE}). "
            "No carry edge detected. Archive strategy D."
        )
    elif modified_carry_available and ic_modified.get("ic_mean", 0) < ic_raw["ic_mean"]:
        recommendation = "INCONCLUSIVE"
        recommendation_detail = (
            f"REER modification reduces IC ({ic_modified['ic_mean']:.4f} < {ic_raw['ic_mean']:.4f}). "
            "REER factor adds no value. Consider Modification #1: test without REER."
        )
    elif (np.isfinite(ic_val) and ic_val >= IC_HARD_GATE
            and np.isfinite(t_val) and t_val >= T_HARD):
        recommendation = "GO"
        recommendation_detail = (
            f"IC={ic_val:.4f} > {IC_HARD_GATE} AND t_HAC={t_val:.2f} > {T_HARD}. "
            "Strong signal. Proceed to full backtest."
        )
    elif (np.isfinite(ic_val) and ic_val >= IC_SOFT_GATE
            and np.isfinite(t_val) and t_val >= T_SOFT):
        recommendation = "GO_CAUTIOUS"
        recommendation_detail = (
            f"IC={ic_val:.4f} > {IC_SOFT_GATE} AND t_HAC={t_val:.2f} > {T_SOFT} "
            f"(but below hard gate {T_HARD}). Proceed to full backtest with caution."
        )
    else:
        recommendation = "INCONCLUSIVE"
        recommendation_detail = (
            f"IC={ic_val:.4f}, t_HAC={t_val:.2f}. "
            "IC positive but t-stat below soft gate. Consider extending universe or adding EM."
        )

    # ── 5. Results dict ──────────────────────────────────────────────────────
    results = {
        "strategy": "modified_carry_g10",
        "run_date": datetime.now(timezone.utc).isoformat(),
        "n_tests_consumed": [N_TESTS_RAW_CARRY, N_TESTS_MODIFIED_REER] if modified_carry_available
                             else [N_TESTS_RAW_CARRY],
        "n_tests_total_after": N_TESTS_MODIFIED_REER if modified_carry_available else N_TESTS_RAW_CARRY,
        "universe": f"G10 vs USD ({len([c for c in G10_CCYS if c in sig_raw_al.columns])} currencies)",
        "period": f"{START} to {END}",
        "frequency": "monthly",
        "raw_carry": {
            **ic_raw,
            "n_tests": N_TESTS_RAW_CARRY,
            "gate_stop": ic_raw["ic_mean"] >= IC_STOP_GATE,
        },
        "modified_carry_reer": {
            **(ic_modified if modified_carry_available else {"status": "skipped_reer_unavailable"}),
            "n_tests": N_TESTS_MODIFIED_REER,
            "reer_data_available": reer_available,
            "reer_date_range": (
                f"{reer.index[reer.notna().any(axis=1)].min().date()} → {reer.index[reer.notna().any(axis=1)].max().date()}"
                if reer_available and not reer.empty else "N/A"
            ),
        },
        "ic_by_vix_regime": by_vix,
        "ic_by_decade": by_decade,
        "recommendation": recommendation,
        "recommendation_detail": recommendation_detail,
    }

    _RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str))
    log.info("Results written → %s", _RESULTS_PATH)

    # ── 6. Print summary ────────────────────────────────────────────────────
    print("\n" + "=" * 68)
    print("STRATEGY D — IC FEASIBILITY RESULTS")
    print("=" * 68)
    print(f"\nRaw Carry (n_tests={N_TESTS_RAW_CARRY}):")
    print(f"  IC_mean   = {ic_raw['ic_mean']:.5f}")
    print(f"  IC_std    = {ic_raw['ic_std']:.5f}")
    print(f"  t_HAC_lag6 = {ic_raw['t_hac_lag6']:.3f}")
    print(f"  N periods  = {ic_raw['ic_n']}")
    print(f"  Stop gate  = {'PASS ✓' if ic_raw['ic_mean'] >= IC_STOP_GATE else 'FAIL ✗ — ARCHIVE'}")

    if modified_carry_available:
        print(f"\nREER-Modified Carry (n_tests={N_TESTS_MODIFIED_REER}):")
        print(f"  IC_mean   = {ic_modified['ic_mean']:.5f}")
        print(f"  IC_std    = {ic_modified['ic_std']:.5f}")
        print(f"  t_HAC_lag6 = {ic_modified['t_hac_lag6']:.3f}")
        print(f"  N periods  = {ic_modified['ic_n']}")
        delta = ic_modified['ic_mean'] - ic_raw['ic_mean']
        print(f"  ΔIC vs raw = {delta:+.5f}")
        print(f"  Soft gate  = {'PASS ✓' if ic_modified['ic_mean'] >= IC_SOFT_GATE and ic_modified['t_hac_lag6'] >= T_SOFT else 'FAIL ✗'}")
        print(f"  Hard gate  = {'PASS ✓' if ic_modified['ic_mean'] >= IC_HARD_GATE and ic_modified['t_hac_lag6'] >= T_HARD else 'FAIL ✗'}")

    if by_vix:
        print("\nIC by VIX regime (modified carry):")
        for regime, stats_r in by_vix.items():
            print(f"  {regime:<12s}: IC={stats_r.get('ic_mean', 'N/A'):.4f}  t={stats_r.get('t_hac_lag6', 'N/A'):.2f}  n={stats_r.get('ic_n', 'N/A')}")

    if by_decade:
        print("\nIC by decade (modified carry):")
        for decade, stats_d in by_decade.items():
            print(f"  {decade}: IC={stats_d.get('ic_mean', 'N/A'):.4f}  t={stats_d.get('t_hac_lag6', 'N/A'):.2f}")

    print(f"\n{'=' * 68}")
    print(f"RECOMMENDATION: {recommendation}")
    print(f"  {recommendation_detail}")
    print("=" * 68)

    return results


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("IC feasibility run failed")
        sys.exit(1)
