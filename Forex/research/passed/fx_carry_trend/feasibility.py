"""
fx_carry_trend/feasibility.py
==============================
FX Carry + Trend Filter — rescue play on confirmed G10 carry signal.

Motivation
----------
Raw carry (IC=0.027, t=2.02) has a well-documented crash problem:
  GFC 2008:  -24%  (USD funding squeeze; carry unwind)
  EM unwind 2015: -15%
  COVID 2020: -21%

Asness, Moskowitz & Pedersen (2013) show that combining carry with
12M-1M trend filter substantially reduces crash exposure by avoiding
carry positions when trend contradicts.

Strategy variants
-----------------
A (hard filter):   carry rank × 0/1 based on trend alignment.
                   Rank within filtered universe only.
B (soft blend):    0.5×carry_z + 0.5×trend_z. Always rank all 8.
C (momentum stop): Carry base, set weight to 0 where trend contradicts.

Signal timing
-------------
  Week T observation:
    carry[T] = rates[T-1 week] (shift(1) on weekly rates)
    trend[T] = weekly_close[T-5weeks] / weekly_close[T-53weeks] - 1
               (12M-1M momentum, uses data ≤ T-1 week)
  Both are known before week-T open. No lookahead.

Gate targets (crash protection is primary)
------------------------------------------
  RESEARCH_PASS  : Sharpe>0.60, GFC MaxDD>-15%, COVID MaxDD>-12%,
                   MaxDD<-30%, WF%≥40%, Alpha t>1.0, AMTP p<0.30
  PROPFIRM_PASS  : Sharpe>1.0,  GFC MaxDD>-10%, COVID MaxDD>-8%,
                   MaxDD<-15%, WF%≥55%, Alpha t>1.5, AMTP p<0.15

STOP condition
--------------
  If filter fires <10% of weeks during GFC 2008 (2008-01 to 2008-12):
  halt with STOP_FILTER error — filter is not identifying crash regime.

n_tests: 82 -> 85 (3 variants)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf
from pandas_datareader.data import DataReader
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
START = "2005-01-01"
END   = pd.Timestamp.today().strftime("%Y-%m-%d")
COST_RT  = 0.00015                    # 15 bps round-trip (institutional FX)
N_TESTS  = 85                         # running counter after this script

RESULTS_PATH = Path(__file__).parent / "results.json"
SUMMARY_PATH = Path(__file__).parent / "fx_carry_trend_summary.md"

FRED_RATES_3M: Dict[str, str] = {
    "USD": "DTB3",
    "EUR": "IR3TIB01EZM156N",
    "GBP": "IR3TIB01GBM156N",
    "JPY": "IR3TIB01JPM156N",
    "AUD": "IR3TIB01AUM156N",
    "CAD": "IR3TIB01CAM156N",
    "CHF": "IR3TIB01CHM156N",
    "NOK": "IR3TIB01NOM156N",
    "SEK": "IR3TIB01SEM156N",
}

G10_CCYS = ["EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NOK", "SEK"]

# Crash windows for targeted evaluation
CRASH_WINDOWS = {
    "GFC_2008":   ("2008-01-01", "2008-12-31"),
    "EM_2015":    ("2015-06-01", "2015-12-31"),
    "COVID_2020": ("2020-02-01", "2020-06-30"),
}

# Research gates
RESEARCH_GATES = {
    "sharpe":      0.60,
    "max_dd":      -0.30,
    "gfc_max_dd":  -0.15,
    "covid_max_dd":-0.12,
    "wf_pct":      40.0,
    "alpha_t":     1.0,
    "amtp_p":      0.30,
}

PROPFIRM_GATES = {
    "sharpe":      1.00,
    "max_dd":      -0.15,
    "gfc_max_dd":  -0.10,
    "covid_max_dd":-0.08,
    "wf_pct":      55.0,
    "alpha_t":     1.5,
    "amtp_p":      0.15,
}


# ---------------------------------------------------------------------------
# Data fetchers (reused from fx_carry_fred)
# ---------------------------------------------------------------------------
def fetch_fred_rates(tickers: Dict[str, str], start: str, end: str) -> pd.DataFrame:
    series = {}
    for ccy, tk in tickers.items():
        try:
            s = DataReader(tk, "fred", start, end).iloc[:, 0]
            series[ccy] = s
            log.info(f"FRED {ccy:<3s} {tk:<22s} {len(s):>5d} obs")
        except Exception as e:
            log.warning(f"FRED fetch failed for {ccy} ({tk}): {e}")
    if "USD" not in series:
        raise RuntimeError("USD rate (DTB3) is required — aborting.")
    df = pd.concat(series, axis=1).resample("D").last().ffill()
    return df


def _yf_close(ticker: str, start: str, end: str) -> pd.Series:
    px = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if "Close" not in px.columns:
        raise RuntimeError(f"No Close column for {ticker}")
    s = px["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s.dropna()


def fetch_fx_xxx_usd(ccy: str, start: str, end: str) -> pd.Series:
    """Return XXXUSD price. Inverts USD-base pairs (JPY, CAD, CHF, NOK, SEK)."""
    if ccy in {"EUR", "GBP", "AUD", "NZD"}:
        px = _yf_close(f"{ccy}USD=X", start, end)
    else:
        px = 1.0 / _yf_close(f"{ccy}=X", start, end)
    return px.rename(f"{ccy}USD")


def fetch_fx_panel(ccys: List[str], start: str, end: str) -> pd.DataFrame:
    cols = []
    for c in ccys:
        try:
            cols.append(fetch_fx_xxx_usd(c, start, end))
        except Exception as e:
            log.warning(f"yfinance fetch failed for {c}: {e}")
    return pd.concat(cols, axis=1).dropna(how="all")


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------
def build_carry(rates: pd.DataFrame, base_ccys: List[str],
                quote: str = "USD") -> pd.DataFrame:
    """carry[XXXUSD] = r[XXX] - r[USD]. Apply .shift(1) after calling."""
    cols = {}
    for c in base_ccys:
        if c in rates.columns:
            cols[f"{c}USD"] = rates[c] - rates[quote]
    return pd.DataFrame(cols).dropna(how="all")


def build_trend(fx_w: pd.DataFrame) -> pd.DataFrame:
    """
    12M-1M momentum on weekly closes.
    trend[T] = close[T-5] / close[T-53] - 1
    Uses only data ≤ T-1 week (aligns with carry.shift(1) timing).
    No additional shift needed — shift(5) already excludes current week.
    """
    return (fx_w.shift(5) / fx_w.shift(53) - 1)


# ---------------------------------------------------------------------------
# Portfolio construction helpers
# ---------------------------------------------------------------------------
def _rank_weights(signal_row: pd.Series, k: int) -> pd.Series:
    """Long top-k, short bottom-k, equal weight, NaN = 0."""
    s = signal_row.dropna()
    if len(s) < 2 * k:
        return pd.Series(0.0, index=signal_row.index)
    ranked = s.sort_values()
    w = pd.Series(0.0, index=signal_row.index)
    w[ranked.index[-k:]] = 1.0 / k
    w[ranked.index[:k]]  = -1.0 / k
    return w


def build_weights_A(carry: pd.DataFrame, trend: pd.DataFrame,
                    k: int) -> pd.DataFrame:
    """
    Variant A — hard filter:
    Zero out currency where trend contradicts carry direction.
    Rank within the surviving universe.
    """
    # trend_aligned[i,t] = True if sign(carry) == sign(trend)
    carry_sign = np.sign(carry)
    trend_sign = np.sign(trend)
    aligned = (carry_sign == trend_sign)

    filtered = carry.copy()
    filtered[~aligned] = np.nan   # hide contradicting currencies

    cols = carry.columns
    idx  = carry.index.intersection(trend.index)
    filtered = filtered.loc[idx]

    w = pd.DataFrame(0.0, index=idx, columns=cols)
    for t in idx:
        row = filtered.loc[t]
        w.loc[t] = _rank_weights(row, k)
    return w


def build_weights_B(carry: pd.DataFrame, trend: pd.DataFrame,
                    k: int) -> pd.DataFrame:
    """
    Variant B — soft blend:
    combined = 0.5*carry_z + 0.5*trend_z (cross-sectional z-score each week).
    Rank all 8.
    """
    def _zscore(df):
        return df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1, ddof=1), axis=0)

    carry_z = _zscore(carry)
    trend_z = _zscore(trend)
    combined = 0.5 * carry_z + 0.5 * trend_z

    cols = carry.columns
    idx  = carry.index.intersection(trend.index)
    combined = combined.loc[idx]

    w = pd.DataFrame(0.0, index=idx, columns=cols)
    for t in idx:
        row = combined.loc[t]
        w.loc[t] = _rank_weights(row, k)
    return w


def build_weights_C(carry: pd.DataFrame, trend: pd.DataFrame,
                    k: int) -> pd.DataFrame:
    """
    Variant C — momentum stop:
    Use carry ranking as base. Set weight to 0 where trend contradicts
    the carry direction (position removed, not reshuffled).
    """
    cols = carry.columns
    idx  = carry.index.intersection(trend.index)
    carry_idx = carry.loc[idx]
    trend_idx = trend.loc[idx]

    # Base weights from carry ranking
    w = pd.DataFrame(0.0, index=idx, columns=cols)
    for t in idx:
        row = carry_idx.loc[t]
        w.loc[t] = _rank_weights(row, k)

    # Zero out where trend contradicts carry direction
    carry_sign = np.sign(carry_idx)
    trend_sign = np.sign(trend_idx)
    contradicts = (carry_sign != trend_sign) & (w != 0)
    w[contradicts] = 0.0
    return w


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def sharpe_hac_weekly(ret: pd.Series) -> float:
    """
    HAC-adjusted Sharpe ratio (weekly).
    Formula: mean / sqrt(LRV) * sqrt(52)
    where LRV = reg.cov_params()[0,0] * n.
    Falls back to plain Sharpe if n < 48.
    """
    r = ret.dropna()
    n = len(r)
    if n < 10:
        return np.nan
    mean = float(r.mean())
    std  = float(r.std(ddof=1))
    if std < 1e-12:
        return np.nan
    if n < 48:
        return (mean / std) * np.sqrt(52)
    reg = sm.OLS(r, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    lrv     = float(reg.cov_params().iloc[0, 0]) * n
    hac_std = float(np.sqrt(max(lrv, 1e-24)))
    if hac_std < 1e-12:
        return np.nan
    return (mean / hac_std) * np.sqrt(52)


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1.0).min())


def alpha_vs_spx(net_ret: pd.Series, start: str, end: str) -> Tuple[float, float]:
    """
    OLS alpha of weekly net returns vs weekly SPY (proxy MKT factor).
    Returns (alpha_annualised, t_HAC).
    """
    try:
        spy = _yf_close("SPY", start, end)
        spy_w  = spy.resample("W-FRI").last().pct_change().dropna()
        common = net_ret.index.intersection(spy_w.index)
        if len(common) < 52:
            return np.nan, np.nan
        y = net_ret.loc[common].values.astype(float)
        x = spy_w.loc[common].values.astype(float)
        valid = np.isfinite(y) & np.isfinite(x)
        y, x = y[valid], x[valid]
        X = sm.add_constant(x)
        reg = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
        alpha_w = float(reg.params[0])
        t_alpha = float(reg.tvalues[0])
        return alpha_w * 52, t_alpha
    except Exception as e:
        log.warning(f"Alpha regression failed: {e}")
        return np.nan, np.nan


def approx_multi_test_penalty(sharpe: float, n_tests: int,
                               n_years: float) -> float:
    """
    Bailey-Lopez-Prado (2014) approximate formula.
    Returns p-value under H0: all n_tests tests are noise.
    """
    if not np.isfinite(sharpe) or n_tests < 1:
        return np.nan
    # Expected maximum Sharpe under n_tests iid noise trials
    gamma_e = 0.5772156649
    z_expected = (1 - gamma_e) * stats.norm.ppf(1 - 1 / n_tests) + \
                 gamma_e * stats.norm.ppf(1 - 1 / (n_tests * np.e))
    sr_expected = z_expected / np.sqrt(n_years)
    # p-value: probability observed Sharpe <= expected max under noise
    sr_obs_z = sharpe * np.sqrt(n_years)
    p = float(stats.norm.cdf(sr_expected - sr_obs_z))
    return p


def walk_forward_pct(net_ret: pd.Series, freq: str = "Y") -> float:
    """Percentage of OOS years with positive annual return."""
    annual = net_ret.resample(freq).apply(lambda r: (1 + r).prod() - 1).dropna()
    if len(annual) == 0:
        return np.nan
    return float((annual > 0).mean() * 100)


def crash_stats(net_ret: pd.Series,
                windows: Dict[str, Tuple[str, str]]) -> Dict[str, dict]:
    """Per-crash-window Sharpe, MaxDD, total return."""
    results = {}
    for label, (s, e) in windows.items():
        seg = net_ret.loc[s:e].dropna()
        if len(seg) < 4:
            results[label] = {"sharpe": np.nan, "max_dd": np.nan, "total_ret": np.nan}
            continue
        eq = (1 + seg).cumprod()
        results[label] = {
            "sharpe":    float(seg.mean() / seg.std(ddof=1) * np.sqrt(52))
                         if seg.std(ddof=1) > 0 else np.nan,
            "max_dd":    float(max_drawdown(eq)),
            "total_ret": float(eq.iloc[-1] - 1),
        }
    return results


def filter_fire_rate(weights: pd.DataFrame, raw_weights: pd.DataFrame,
                     window: Tuple[str, str]) -> float:
    """
    Fraction of weeks in window where filter changed a position (|w_A - w_raw| > 0).
    """
    s, e = window
    w = weights.loc[s:e]
    rw = raw_weights.loc[s:e]
    if len(w) == 0:
        return np.nan
    changed = (w - rw).abs().sum(axis=1) > 1e-6
    return float(changed.mean())


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------
def run_backtest(weights: pd.DataFrame, ret_w: pd.DataFrame,
                 cost_rt: float = COST_RT) -> Tuple[pd.Series, pd.Series]:
    """
    Returns (net_ret, gross_ret) as weekly series.
    Cost = (turnover/2) * cost_rt (each one-way leg costs cost_rt/2).
    """
    cols = weights.columns.intersection(ret_w.columns)
    w    = weights[cols]
    r    = ret_w[cols]
    idx  = w.index.intersection(r.index)
    w, r = w.loc[idx], r.loc[idx]

    gross = (w * r).sum(axis=1)
    # Turnover: sum of absolute weight changes; divide by 2 to avoid double-count
    turnover = (w - w.shift(1).fillna(0)).abs().sum(axis=1)
    cost     = (turnover / 2.0) * cost_rt
    net      = gross - cost

    return net, gross


# ---------------------------------------------------------------------------
# Two-tier verdict
# ---------------------------------------------------------------------------
def verdict(sharpe: float, max_dd: float, gfc_dd: float, covid_dd: float,
            wf_pct: float, alpha_t: float, amtp_p: float) -> Tuple[str, str]:
    """Returns (research_verdict, propfirm_verdict)."""
    def check(gates):
        ok = (
            sharpe  >= gates["sharpe"]        and
            max_dd  >= gates["max_dd"]        and
            gfc_dd  >= gates["gfc_max_dd"]    and
            covid_dd >= gates["covid_max_dd"] and
            wf_pct  >= gates["wf_pct"]        and
            alpha_t >= gates["alpha_t"]       and
            amtp_p  <= gates["amtp_p"]
        )
        return "PASS" if ok else "FAIL"

    return check(RESEARCH_GATES), check(PROPFIRM_GATES)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("=== FX Carry + Trend Filter — G10 (AMP 2013 framework) ===")

    # ------------------------------------------------------------------
    # 1. Data
    # ------------------------------------------------------------------
    rates  = fetch_fred_rates(FRED_RATES_3M, START, END)
    fx_daily = fetch_fx_panel(G10_CCYS, START, END)
    log.info(f"rates: {rates.shape} | fx_daily: {fx_daily.shape}")

    fx_w    = fx_daily.resample("W-FRI").last()
    # Rename columns to XXXUSD for alignment with carry
    fx_w.columns = [c.replace("USD", "") + "USD" for c in fx_w.columns]
    ret_w   = fx_w.pct_change().dropna(how="all")
    rates_w = rates.resample("W-FRI").last().ffill()

    # ------------------------------------------------------------------
    # 2. Signals
    # ------------------------------------------------------------------
    carry  = build_carry(rates_w, G10_CCYS).shift(1)   # known at T-1 week
    trend  = build_trend(fx_w)                          # shift(5)/shift(53), no extra shift

    # Align all three to common index
    idx = carry.index.intersection(trend.index).intersection(ret_w.index)
    carry_a  = carry.loc[idx]
    trend_a  = trend.loc[idx]
    ret_a    = ret_w.loc[idx]

    n_total = len(idx)
    n_years = n_total / 52.0
    log.info(f"Aligned universe: {n_total} weeks ({n_years:.1f} years)  "
             f"{idx.min().date()} → {idx.max().date()}")

    k = max(1, len(G10_CCYS) // 3)   # k = 2 for 8 currencies
    log.info(f"Tercile k = {k} (long top-{k}, short bottom-{k})")

    # ------------------------------------------------------------------
    # 3. Raw carry baseline (no filter) — for comparison
    # ------------------------------------------------------------------
    w_raw = pd.DataFrame(0.0, index=idx, columns=carry_a.columns)
    for t in idx:
        w_raw.loc[t] = _rank_weights(carry_a.loc[t], k)

    net_raw, gross_raw = run_backtest(w_raw, ret_a)

    # ------------------------------------------------------------------
    # 4. Variant weights
    # ------------------------------------------------------------------
    log.info("Building variant weights...")
    w_A = build_weights_A(carry_a, trend_a, k)
    w_B = build_weights_B(carry_a, trend_a, k)
    w_C = build_weights_C(carry_a, trend_a, k)

    # ------------------------------------------------------------------
    # 5. STOP condition — filter fire rate during GFC 2008
    # ------------------------------------------------------------------
    gfc_window = CRASH_WINDOWS["GFC_2008"]
    fire_A_gfc = filter_fire_rate(w_A, w_raw, gfc_window)
    log.info(f"Variant A filter fire rate (GFC 2008): {fire_A_gfc:.1%}")

    if fire_A_gfc < 0.10:
        print("\n" + "=" * 72)
        print("STOP_FILTER: Variant A filter fired < 10% during GFC 2008.")
        print(f"  Actual fire rate: {fire_A_gfc:.1%}")
        print("  Filter is not identifying crash regime. Halting.")
        print("=" * 72)
        sys.exit(0)

    # ------------------------------------------------------------------
    # 6. Backtests
    # ------------------------------------------------------------------
    log.info("Running backtests...")
    net_A, gross_A = run_backtest(w_A, ret_a)
    net_B, gross_B = run_backtest(w_B, ret_a)
    net_C, gross_C = run_backtest(w_C, ret_a)

    # ------------------------------------------------------------------
    # 7. SPY for alpha regression
    # ------------------------------------------------------------------
    log.info("Fetching SPY for alpha regression...")
    alpha_raw,   t_alpha_raw   = alpha_vs_spx(net_raw,   START, END)
    alpha_A,     t_alpha_A     = alpha_vs_spx(net_A,     START, END)
    alpha_B,     t_alpha_B     = alpha_vs_spx(net_B,     START, END)
    alpha_C,     t_alpha_C     = alpha_vs_spx(net_C,     START, END)

    # ------------------------------------------------------------------
    # 8. Full-period statistics
    # ------------------------------------------------------------------
    def full_stats(net: pd.Series, label: str, w_variant=None) -> dict:
        eq   = (1 + net).cumprod()
        sh   = sharpe_hac_weekly(net)
        mdd  = max_drawdown(eq)
        wfp  = walk_forward_pct(net)
        ann  = float(net.mean() * 52)
        amtp = approx_multi_test_penalty(sh, N_TESTS, n_years)
        cr   = crash_stats(net, CRASH_WINDOWS)

        # Filter fire rates (vs raw)
        fire_overall = np.nan
        fire_gfc     = np.nan
        if w_variant is not None:
            fire_overall = filter_fire_rate(w_variant, w_raw,
                                            (str(idx.min().date()),
                                             str(idx.max().date())))
            fire_gfc = filter_fire_rate(w_variant, w_raw, gfc_window)

        return {
            "label":        label,
            "sharpe_hac":   sh,
            "ann_ret":      ann,
            "max_dd":       mdd,
            "wf_pct":       wfp,
            "amtp_p":       amtp,
            "crash":        cr,
            "fire_rate_all": fire_overall,
            "fire_rate_gfc": fire_gfc,
        }

    stats_raw = full_stats(net_raw, "Raw carry (baseline)")
    stats_A   = full_stats(net_A,   "Variant A (hard filter)",  w_A)
    stats_B   = full_stats(net_B,   "Variant B (soft blend)",   w_B)
    stats_C   = full_stats(net_C,   "Variant C (momentum stop)", w_C)

    # ------------------------------------------------------------------
    # 9. Verdicts
    # ------------------------------------------------------------------
    def get_verdict(s: dict, alpha_t: float) -> Tuple[str, str]:
        gfc_dd  = s["crash"]["GFC_2008"]["max_dd"]
        cov_dd  = s["crash"]["COVID_2020"]["max_dd"]
        return verdict(
            s["sharpe_hac"], s["max_dd"],
            gfc_dd if np.isfinite(gfc_dd) else -99.0,
            cov_dd if np.isfinite(cov_dd) else -99.0,
            s["wf_pct"] if np.isfinite(s["wf_pct"]) else 0.0,
            alpha_t     if np.isfinite(alpha_t)      else 0.0,
            s["amtp_p"] if np.isfinite(s["amtp_p"])  else 1.0,
        )

    rv_A, pv_A = get_verdict(stats_A, t_alpha_A)
    rv_B, pv_B = get_verdict(stats_B, t_alpha_B)
    rv_C, pv_C = get_verdict(stats_C, t_alpha_C)

    # ------------------------------------------------------------------
    # 10. Print results
    # ------------------------------------------------------------------
    header = "\n" + "=" * 80
    print(header)
    print("FX CARRY + TREND FILTER — G10 (AMP 2013 framework)")
    print("=" * 80)

    def _fmt_crash(cr: dict, label: str) -> str:
        gfc = cr.get("GFC_2008",   {})
        em  = cr.get("EM_2015",    {})
        cov = cr.get("COVID_2020", {})
        return (
            f"  Crash [{label}]\n"
            f"    GFC 2008   : MaxDD {gfc.get('max_dd', np.nan):+.1%}  "
            f"Total {gfc.get('total_ret', np.nan):+.1%}\n"
            f"    EM 2015    : MaxDD {em.get('max_dd', np.nan):+.1%}  "
            f"Total {em.get('total_ret', np.nan):+.1%}\n"
            f"    COVID 2020 : MaxDD {cov.get('max_dd', np.nan):+.1%}  "
            f"Total {cov.get('total_ret', np.nan):+.1%}"
        )

    def _print_variant(s: dict, alpha: float, t_a: float,
                       rv: str, pv: str) -> None:
        print(f"\n  [{s['label']}]")
        print(f"    Sharpe (HAC) : {s['sharpe_hac']:+.3f}")
        print(f"    Ann ret      : {s['ann_ret']:+.1%}")
        print(f"    MaxDD        : {s['max_dd']:+.1%}")
        print(f"    WF% positive : {s['wf_pct']:.0f}%")
        print(f"    Alpha (ann)  : {alpha:+.1%}   t = {t_a:+.2f}")
        print(f"    AMTP p-val   : {s['amtp_p']:.3f}")
        if np.isfinite(s['fire_rate_all']):
            print(f"    Filter fire  : {s['fire_rate_all']:.1%} overall  "
                  f"| GFC: {s['fire_rate_gfc']:.1%}")
        print(_fmt_crash(s["crash"], s["label"]))
        print(f"    RESEARCH     : {rv}   PROPFIRM: {pv}")

    # Baseline
    print(f"\n  [Raw carry baseline — for comparison]")
    print(f"    Sharpe (HAC) : {stats_raw['sharpe_hac']:+.3f}")
    print(f"    Ann ret      : {stats_raw['ann_ret']:+.1%}")
    print(f"    MaxDD        : {stats_raw['max_dd']:+.1%}")
    print(f"    Alpha (ann)  : {alpha_raw:+.1%}   t = {t_alpha_raw:+.2f}")
    print(_fmt_crash(stats_raw["crash"], "Raw carry"))

    _print_variant(stats_A, alpha_A, t_alpha_A, rv_A, pv_A)
    _print_variant(stats_B, alpha_B, t_alpha_B, rv_B, pv_B)
    _print_variant(stats_C, alpha_C, t_alpha_C, rv_C, pv_C)

    # ------------------------------------------------------------------
    # 11. Crash protection summary table
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("CRASH PROTECTION TABLE (MaxDD during crash window)")
    print(f"  {'Strategy':<28} {'GFC 2008':>12} {'EM 2015':>12} {'COVID 2020':>12}")
    print("  " + "-" * 68)
    for s_label, s_data in [
        ("Raw carry", stats_raw),
        ("Var A (hard filter)", stats_A),
        ("Var B (soft blend)", stats_B),
        ("Var C (momentum stop)", stats_C),
    ]:
        cr = s_data["crash"]
        gfc = cr.get("GFC_2008",   {}).get("max_dd", np.nan)
        em  = cr.get("EM_2015",    {}).get("max_dd", np.nan)
        cov = cr.get("COVID_2020", {}).get("max_dd", np.nan)
        print(f"  {s_label:<28} {gfc:>+12.1%} {em:>+12.1%} {cov:>+12.1%}")
    print("=" * 80)

    # ------------------------------------------------------------------
    # 12. Save results
    # ------------------------------------------------------------------
    def _serialisable(d: dict) -> dict:
        """Recursively convert numpy scalars for JSON."""
        out = {}
        for k, v in d.items():
            if isinstance(v, dict):
                out[k] = _serialisable(v)
            elif isinstance(v, float) and not np.isfinite(v):
                out[k] = None
            elif isinstance(v, (np.floating, np.integer)):
                out[k] = float(v)
            else:
                out[k] = v
        return out

    results = {
        "n_tests": N_TESTS,
        "period": {"start": str(idx.min().date()), "end": str(idx.max().date())},
        "raw_carry": _serialisable(stats_raw),
        "variant_A": _serialisable(stats_A),
        "variant_B": _serialisable(stats_B),
        "variant_C": _serialisable(stats_C),
        "alpha": {
            "raw":  {"ann": float(alpha_raw),  "t": float(t_alpha_raw)  if np.isfinite(t_alpha_raw)  else None},
            "A":    {"ann": float(alpha_A),     "t": float(t_alpha_A)    if np.isfinite(t_alpha_A)    else None},
            "B":    {"ann": float(alpha_B),     "t": float(t_alpha_B)    if np.isfinite(t_alpha_B)    else None},
            "C":    {"ann": float(alpha_C),     "t": float(t_alpha_C)    if np.isfinite(t_alpha_C)    else None},
        },
        "verdicts": {
            "A": {"research": rv_A, "propfirm": pv_A},
            "B": {"research": rv_B, "propfirm": pv_B},
            "C": {"research": rv_C, "propfirm": pv_C},
        },
        "filter_fire_gfc_A": float(fire_A_gfc) if np.isfinite(fire_A_gfc) else None,
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    log.info(f"Results saved → {RESULTS_PATH}")

    # ------------------------------------------------------------------
    # 13. Markdown summary
    # ------------------------------------------------------------------
    def _dd(s, window):
        v = s["crash"].get(window, {}).get("max_dd", np.nan)
        return f"{v:+.1%}" if np.isfinite(v) else "N/A"

    summary_lines = [
        "# FX Carry + Trend Filter — Feasibility Summary",
        "",
        f"**Run date**: {pd.Timestamp.today().strftime('%Y-%m-%d')}  ",
        f"**Period**: {idx.min().date()} → {idx.max().date()}  ",
        f"**n_tests**: {N_TESTS} (this run adds tests 83, 84, 85)",
        "",
        "## Motivation",
        "Raw FX carry has confirmed predictive power (IC=0.027, t=2.02) but severe",
        "crash drawdowns: GFC -24%, EM unwind -15%, COVID -21%.",
        "AMP (2013): trend filter reduces crash exposure by shorting currencies",
        "where 12M-1M momentum contradicts carry direction.",
        "",
        "## Signal construction",
        "- **Carry**: weekly 3M interbank spread (FRED), shifted 1 week",
        "- **Trend**: `close[T-5w] / close[T-53w] - 1` (12M-1M momentum)",
        "- **Universe**: 8 G10 currencies vs USD",
        "- **Portfolio**: long top-2 / short bottom-2 (equal weight)",
        "- **Cost**: 15 bps RT (institutional FX)",
        "",
        "## Crash protection (MaxDD during crash window)",
        "",
        "| Strategy           | GFC 2008 | EM 2015 | COVID 2020 |",
        "|--------------------|----------|---------|-----------|",
        f"| Raw carry          | {_dd(stats_raw,'GFC_2008')} | {_dd(stats_raw,'EM_2015')} | {_dd(stats_raw,'COVID_2020')} |",
        f"| Var A (hard)       | {_dd(stats_A,'GFC_2008')} | {_dd(stats_A,'EM_2015')} | {_dd(stats_A,'COVID_2020')} |",
        f"| Var B (soft blend) | {_dd(stats_B,'GFC_2008')} | {_dd(stats_B,'EM_2015')} | {_dd(stats_B,'COVID_2020')} |",
        f"| Var C (mom stop)   | {_dd(stats_C,'GFC_2008')} | {_dd(stats_C,'EM_2015')} | {_dd(stats_C,'COVID_2020')} |",
        "",
        "## Full-period statistics",
        "",
        "| Metric       | Raw carry | Var A | Var B | Var C |",
        "|--------------|-----------|-------|-------|-------|",
        f"| Sharpe (HAC) | {stats_raw['sharpe_hac']:+.3f} | {stats_A['sharpe_hac']:+.3f} | {stats_B['sharpe_hac']:+.3f} | {stats_C['sharpe_hac']:+.3f} |",
        f"| Ann ret      | {stats_raw['ann_ret']:+.1%} | {stats_A['ann_ret']:+.1%} | {stats_B['ann_ret']:+.1%} | {stats_C['ann_ret']:+.1%} |",
        f"| MaxDD        | {stats_raw['max_dd']:+.1%} | {stats_A['max_dd']:+.1%} | {stats_B['max_dd']:+.1%} | {stats_C['max_dd']:+.1%} |",
        f"| WF%          | {stats_raw['wf_pct']:.0f}% | {stats_A['wf_pct']:.0f}% | {stats_B['wf_pct']:.0f}% | {stats_C['wf_pct']:.0f}% |",
        f"| Alpha t      | {t_alpha_raw:+.2f} | {t_alpha_A:+.2f} | {t_alpha_B:+.2f} | {t_alpha_C:+.2f} |",
        f"| AMTP p       | {stats_raw['amtp_p']:.3f} | {stats_A['amtp_p']:.3f} | {stats_B['amtp_p']:.3f} | {stats_C['amtp_p']:.3f} |",
        f"| Filter fire (GFC) | — | {fire_A_gfc:.1%} | — | — |",
        "",
        "## Verdicts",
        "",
        f"- **Variant A**: RESEARCH {rv_A} / PROPFIRM {pv_A}",
        f"- **Variant B**: RESEARCH {rv_B} / PROPFIRM {pv_B}",
        f"- **Variant C**: RESEARCH {rv_C} / PROPFIRM {pv_C}",
        "",
        "## Root cause notes",
        "- AMP (2013) documented trend filter reduces carry crash MaxDD by 30-50%",
        "- Filter effectiveness measured by fire rate concentrated in crash windows",
        f"- GFC 2008 filter fire rate (Var A): {fire_A_gfc:.1%}",
        "",
        "## Gates reference",
        "RESEARCH_PASS: Sharpe>0.60, GFC MaxDD>-15%, COVID MaxDD>-12%, MaxDD<-30%, "
        "WF%≥40%, Alpha t>1.0, AMTP p<0.30",
        "PROPFIRM_PASS: Sharpe>1.0, GFC MaxDD>-10%, COVID MaxDD>-8%, MaxDD<-15%, "
        "WF%≥55%, Alpha t>1.5, AMTP p<0.15",
    ]

    SUMMARY_PATH.write_text("\n".join(summary_lines) + "\n")
    log.info(f"Summary saved → {SUMMARY_PATH}")

    print(f"\nn_tests counter: {N_TESTS - 3} → {N_TESTS} (added variants A, B, C)")
    print("DO NOT COMMIT — review crash protection table first.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("feasibility run failed")
        sys.exit(1)
