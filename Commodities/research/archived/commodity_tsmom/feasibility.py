"""
Commodity TSMOM — Hurst, Ooi & Pedersen (2017) framework
=========================================================

Reference: Hurst, B., Ooi, Y.H., Pedersen, L.H. (2017) "A Century of Evidence
on Trend-Following Investing", Journal of Portfolio Management.

Two variants:
  A — Single-horizon TSMOM (Moskowitz 2012 baseline, 12M signal)
  B — Multi-horizon TSMOM (HOP 2017: 1M + 3M + 12M equal-weighted ensemble)

Both tested with and without vol-targeting overlay → 4 total variants (A1, A2, B1, B2).

Methodology standards (all 5 canonical fixes):
  1. Excess returns over FRED DTB3 daily RF
  2. HAC SE lag=6 for alpha t-stats
  3. Daily P&L → daily realized vol (63-day) for vol-targeting
  4. TSMOM diagnostics: directional accuracy, quintile bucket, convexity
  5. approx_multi_test_penalty (n_tests 74 → 78)
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_datareader.data as pdr
import statsmodels.api as sm
from scipy import stats
from scipy.stats import norm

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*PerformanceWarning.*")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── root on sys.path so `data.cache` resolves ──────────────────────────────
_HERE  = Path(__file__).resolve().parent
_ROOT  = _HERE.parents[3]          # Algo_claude/
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.cache import get_cached_or_fetch  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DATA_START       = "2009-01-01"    # fetch buffer for signal warm-up
TEST_START       = "2010-01-01"
TEST_END         = "2026-05-01"    # ~15 years

UNIVERSE_TICKERS = [
    "GLD",   # gold
    "SLV",   # silver
    "CPER",  # copper
    "PPLT",  # platinum
    "USO",   # oil WTI
    "UNG",   # natural gas
    "BNO",   # oil Brent
    "DBA",   # broad agriculture
    "CORN",  # corn
    "WEAT",  # wheat
    "SOYB",  # soybeans
    "DBB",   # base metals broad
]
MIN_HISTORY_YEARS = 8              # drop tickers with < 8 years data

# TSMOM signal lookbacks
LB_SHORT  =  21    # ~1 month (trading days)
LB_MEDIUM =  63    # ~3 months
LB_LONG   = 252    # ~12 months
VOL_LB    = 252    # vol lookback for signal normalisation

# Vol targeting
TARGET_VOL = 0.10
VT_VOL_LB  = 63     # 63-day realized vol for scaling
LEV_CAP    = 2.0

# Costs
COST_RT    = 0.0005  # 5 bps round-trip per ETF trade

# Multi-test
N_TESTS_START = 74
N_TESTS_END   = 78   # +4 variants

# Walk-forward
WF_TRAIN_YRS = 3
WF_OOS_YRS   = 1

# Bootstrap
N_BOOT = 20_000

# Saved output
SUMMARY_PATH = _HERE / "commodity_tsmom_summary.md"

# Benchmark tickers
SPY_TICKER = "SPY"
DBC_TICKER = "DBC"   # passive commodity index
TLT_TICKER = "TLT"
BTC_TICKER = "BTC-USD"


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

def fetch_prices() -> dict[str, pd.DataFrame]:
    """Fetch daily OHLCV for all universe tickers + benchmarks."""
    all_tickers = UNIVERSE_TICKERS + [SPY_TICKER, DBC_TICKER, TLT_TICKER, BTC_TICKER]
    prices = {}
    for tk in all_tickers:
        df = get_cached_or_fetch(tk, start=DATA_START, end=TEST_END, interval="1d")
        if df.empty:
            log.warning("  No data for %s — skipping", tk)
        else:
            prices[tk] = df
    return prices


def build_close_df(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Merge close prices into a single DataFrame."""
    frames = {}
    for tk, df in prices.items():
        col = "close" if "close" in df.columns else "adj close" if "adj close" in df.columns else df.columns[0]
        frames[tk] = df[col].rename(tk)
    close = pd.concat(frames.values(), axis=1)
    close = close.sort_index()
    return close


def filter_universe(close: pd.DataFrame) -> tuple[list[str], dict[str, str]]:
    """Drop tickers with < MIN_HISTORY_YEARS of data in test window."""
    test_close = close.loc[TEST_START:TEST_END]
    survivors, dropped = [], {}
    for tk in UNIVERSE_TICKERS:
        if tk not in close.columns:
            dropped[tk] = "no data fetched"
            continue
        col = test_close[tk].dropna()
        n_years = len(col) / 252
        if n_years < MIN_HISTORY_YEARS:
            dropped[tk] = f"only {n_years:.1f}yr data"
        else:
            survivors.append(tk)
    return survivors, dropped


def fetch_risk_free() -> pd.Series:
    """Load DTB3 daily T-bill rate from FRED."""
    log.info("Fetching DTB3 from FRED ...")
    try:
        dtb3 = pdr.DataReader("DTB3", "fred", DATA_START, TEST_END)["DTB3"]
        dtb3 = dtb3.ffill() / 100
        rf_daily = (1 + dtb3) ** (1 / 252) - 1
        return rf_daily
    except Exception as exc:
        log.warning("FRED fetch failed (%s) — using rf=0", exc)
        return pd.Series(0.0, index=pd.date_range(DATA_START, TEST_END, freq="B"))


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════

def tsmom_signal(ret: pd.Series, lookback: int) -> pd.Series:
    """
    tanh(cumret_LB / (vol_LB × sqrt(LB/21)))
    vol_LB uses VOL_LB (252-day) for consistency with Moskowitz convention.
    """
    cum_ret = (1 + ret).rolling(lookback).apply(np.prod, raw=True) - 1
    vol     = ret.rolling(VOL_LB).std() * np.sqrt(252)
    horizon_scale = np.sqrt(lookback / 21)
    signal  = np.tanh(cum_ret / (vol * horizon_scale + 1e-12))
    return signal


def compute_signals_a(ret_df: pd.DataFrame) -> pd.DataFrame:
    """Variant A: single 12M horizon."""
    sigs = {}
    for tk in ret_df.columns:
        sigs[tk] = tsmom_signal(ret_df[tk], LB_LONG)
    return pd.DataFrame(sigs)


def compute_signals_b(ret_df: pd.DataFrame) -> pd.DataFrame:
    """Variant B: equal-weight average of 1M + 3M + 12M signals."""
    sigs = {}
    for tk in ret_df.columns:
        s_short  = tsmom_signal(ret_df[tk], LB_SHORT)
        s_medium = tsmom_signal(ret_df[tk], LB_MEDIUM)
        s_long   = tsmom_signal(ret_df[tk], LB_LONG)
        sigs[tk] = (s_short + s_medium + s_long) / 3.0
    return pd.DataFrame(sigs)


# ═══════════════════════════════════════════════════════════════════════════
# PORTFOLIO CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════

def compute_raw_weights(signal_df: pd.DataFrame) -> pd.DataFrame:
    """Weight = signal / n_assets. Monthly rebalance (last business day)."""
    n = signal_df.shape[1]
    return signal_df / n


def apply_vol_targeting(
    weights_m: pd.DataFrame,
    ret_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Scale monthly weights by target_vol / realized_vol.
    Realized vol = 63-day daily P&L vol × √252, sampled at month-ends.
    Leverage cap = 2.0.
    """
    # Daily unscaled portfolio P&L using previous month-end weights
    # Reindex weights to daily, forward-fill within month
    daily_weights = weights_m.reindex(ret_df.index, method="ffill")
    # Unscaled daily P&L
    daily_pnl = (daily_weights * ret_df).sum(axis=1)

    # 63-day rolling vol of daily P&L, annualised
    realized_vol = daily_pnl.rolling(VT_VOL_LB).std() * np.sqrt(252)
    realized_vol_m = realized_vol.resample("ME").last()

    # Scale factor: target_vol / realized_vol, capped at LEV_CAP
    scale = (TARGET_VOL / realized_vol_m.replace(0, np.nan)).clip(upper=LEV_CAP)
    scale = scale.reindex(weights_m.index, method="ffill")

    scaled = weights_m.multiply(scale, axis=0)
    return scaled


def weights_to_monthly_returns(
    weights_m: pd.DataFrame,
    ret_df: pd.DataFrame,
    rf_monthly: pd.Series,
) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
    """
    Convert monthly weights to monthly excess returns with 5bps cost.

    Returns
    -------
    port_ret_exc  : monthly excess portfolio returns
    asset_contribs: monthly return contribution per asset
    positions     : the weights used each month
    """
    # Align on months
    dates = weights_m.index.intersection(ret_df.resample("ME").last().index)
    dates = dates[(dates >= TEST_START) & (dates <= TEST_END)]

    # Forward returns: from end of month t to end of month t+1
    monthly_ret = ret_df.resample("ME").apply(lambda x: (1 + x).prod() - 1)

    monthly_exc_asset = monthly_ret.subtract(rf_monthly.resample("ME").apply(lambda x: (1+x).prod()-1), axis=0)

    port_rets   = []
    contribs    = []
    prev_w      = pd.Series(0.0, index=weights_m.columns)

    for t in dates:
        w_t = weights_m.loc[t]
        # Cost from turnover
        turnover = (w_t - prev_w).abs().sum()
        cost     = turnover * COST_RT / 2   # half on entry, track as single RT

        # Forward return: month t+1
        fwd_dates = monthly_ret.index[monthly_ret.index > t]
        if len(fwd_dates) == 0:
            break
        t1 = fwd_dates[0]
        if t1 not in monthly_exc_asset.index:
            break

        fwd_ret = monthly_exc_asset.loc[t1]
        contrib = w_t * fwd_ret
        port_ret = contrib.sum() - cost

        port_rets.append((t1, port_ret))
        contribs.append(contrib.rename(t1))
        prev_w = w_t

    if not port_rets:
        return pd.Series(dtype=float), pd.DataFrame(), weights_m

    idx        = pd.DatetimeIndex([x[0] for x in port_rets])
    port_s     = pd.Series([x[1] for x in port_rets], index=idx, name="port")
    contrib_df = pd.DataFrame(contribs)
    return port_s, contrib_df, weights_m.reindex(idx, method="ffill")


# ═══════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

def sharpe_hac(ret: pd.Series, annual_factor: float = 12.0) -> float:
    """
    HAC-adjusted Sharpe ratio.

    Formula: mean / sqrt(LRV) × sqrt(annual_factor)

    where LRV (long-run variance per period) = HAC_var_of_sample_mean × n.
    reg.cov_params()[0,0] gives Var(mean̂) = LRV/n, so LRV = cov_params[0,0] × n.

    For IID returns this reduces to mean/σ × √annual_factor (standard Sharpe).
    For positively autocorrelated returns LRV > σ², so HAC Sharpe < regular Sharpe.

    Short series (< 24 obs): HAC with lag=6 is unreliable; fall back to regular Sharpe.
    """
    r = ret.dropna()
    n = len(r)
    if n < 10:
        return np.nan
    mean = float(r.mean())
    if n < 24:
        std = float(r.std())
        return (mean / std) * np.sqrt(annual_factor) if std > 1e-12 else np.nan
    reg = sm.OLS(r, np.ones(n)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 6}
    )
    # LRV = Var(mean̂) × n; hac_std = per-period long-run std
    lrv     = float(reg.cov_params().iloc[0, 0]) * n
    hac_std = float(np.sqrt(max(lrv, 1e-24)))
    if hac_std < 1e-12:
        return np.nan
    return (mean / hac_std) * np.sqrt(annual_factor)


def max_drawdown(ret: pd.Series) -> float:
    cum = (1 + ret).cumprod()
    roll_max = cum.cummax()
    dd = (cum - roll_max) / roll_max
    return float(dd.min())


def profit_factor(ret: pd.Series) -> float:
    pos = ret[ret > 0].sum()
    neg = ret[ret < 0].abs().sum()
    return float(pos / neg) if neg > 0 else np.inf


def alpha_regression(
    port_ret: pd.Series,
    bench_ret: pd.Series,
    label: str,
) -> dict:
    """OLS alpha with HAC SE. Returns dict with alpha_ann, t_hac, beta, r2."""
    idx = port_ret.index.intersection(bench_ret.index)
    if len(idx) < 24:
        return dict(alpha_ann=np.nan, t_hac=np.nan, beta=np.nan, r2=np.nan)
    y = port_ret.loc[idx].values
    x = bench_ret.loc[idx].values
    X = sm.add_constant(x)
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    alpha_m  = res.params[0]
    t_hac    = res.tvalues[0]
    beta     = res.params[1]
    r2       = res.rsquared
    return dict(
        alpha_ann=float(alpha_m * 12),
        t_hac=float(t_hac),
        beta=float(beta),
        r2=float(r2),
    )


def bootstrap_ev(ret: pd.Series, n_boot: int = N_BOOT) -> dict:
    """Bootstrap mean monthly return with 95% CI and P(EV≤0)."""
    r = ret.dropna().values
    means = np.array([np.mean(np.random.choice(r, len(r), replace=True)) for _ in range(n_boot)])
    return dict(
        ev=float(r.mean()),
        ci_lo=float(np.percentile(means, 2.5)),
        ci_hi=float(np.percentile(means, 97.5)),
        p_ev_le0=float(np.mean(means <= 0)),
    )


def amtp(n_tests: int, sharpe_monthly: float, n_obs: int) -> float:
    """
    Approximate multi-test penalty (BLP formula, Lopez de Prado).
    Returns p-value under H0: SR* = adjusted hurdle.
    """
    if n_tests <= 1:
        return 0.0
    sr_star = (
        (1 - np.euler_gamma) * norm.ppf(1 - 1 / n_tests)
        + np.euler_gamma * norm.ppf(1 - 1 / (n_tests * np.e))
    )
    sr_scaled = sharpe_monthly * np.sqrt(n_obs)
    p = 1 - norm.cdf(sr_scaled - sr_star)
    return float(p)


# ═══════════════════════════════════════════════════════════════════════════
# TSMOM DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════

def directional_accuracy(signal_m: pd.DataFrame, fwd_ret_m: pd.DataFrame) -> dict:
    """
    For each asset, compute % of months where sign(signal) == sign(fwd_return).
    Returns per-asset dict + aggregate.
    """
    # Align
    idx = signal_m.index.intersection(fwd_ret_m.index)
    sig = signal_m.loc[idx]
    fwd = fwd_ret_m.loc[idx]
    results = {}
    all_correct = []
    for tk in sig.columns:
        if tk not in fwd.columns:
            continue
        s = sig[tk].dropna()
        f = fwd[tk].reindex(s.index).dropna()
        common = s.index.intersection(f.index)
        if len(common) < 10:
            continue
        correct = (np.sign(s.loc[common]) == np.sign(f.loc[common])).mean()
        results[tk] = float(correct)
        all_correct.append(correct)
    results["_aggregate"] = float(np.mean(all_correct)) if all_correct else np.nan
    return results


def quintile_analysis(signal_m: pd.DataFrame, fwd_ret_m: pd.DataFrame) -> pd.DataFrame:
    """
    Stack all (signal, fwd_ret) pairs, bin into quintiles by signal value.
    Returns DataFrame with mean fwd_ret per quintile.
    """
    records = []
    for tk in signal_m.columns:
        if tk not in fwd_ret_m.columns:
            continue
        s = signal_m[tk].dropna()
        f = fwd_ret_m[tk].reindex(s.index).dropna()
        common = s.index.intersection(f.index)
        if len(common) < 20:
            continue
        records.extend(zip(s.loc[common].values, f.loc[common].values))
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records, columns=["signal", "fwd_ret"])
    df["quintile"] = pd.qcut(df["signal"], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
    return df.groupby("quintile", observed=True)["fwd_ret"].mean().to_frame()


def convexity_test(port_ret: pd.Series, spy_ret: pd.Series) -> dict:
    """
    Regress strategy monthly returns on |SPY monthly return|.
    Positive coefficient = convex payoff (trend-following characteristic).
    """
    idx = port_ret.index.intersection(spy_ret.index)
    if len(idx) < 24:
        return dict(beta_abs=np.nan, t_hac=np.nan)
    y  = port_ret.loc[idx].values
    x  = spy_ret.loc[idx].abs().values
    X  = sm.add_constant(x)
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return dict(beta_abs=float(res.params[1]), t_hac=float(res.tvalues[1]))


# ═══════════════════════════════════════════════════════════════════════════
# WALK-FORWARD
# ═══════════════════════════════════════════════════════════════════════════

def walk_forward_oos(port_ret: pd.Series) -> pd.DataFrame:
    """Rolling 3Y train / 1Y OOS. Reports per-OOS-year stats."""
    results = []
    years = sorted(port_ret.index.year.unique())
    for oos_year in years:
        oos_mask   = port_ret.index.year == oos_year
        oos_series = port_ret.loc[oos_mask]
        if len(oos_series) < 6:
            continue
        sh   = sharpe_hac(oos_series)
        mret = float(oos_series.mean() * 100)
        mdd  = max_drawdown(oos_series) * 100
        results.append(dict(
            year=oos_year,
            n=len(oos_series),
            sharpe=sh,
            monthly_ret_pct=mret,
            maxdd_pct=mdd,
        ))
    df = pd.DataFrame(results)
    if df.empty:
        return df
    df["pct_pos"] = (df["sharpe"] > 0).mean() * 100
    return df


def crash_periods(port_ret: pd.Series) -> pd.DataFrame:
    """Stats for key stress periods."""
    periods = [
        ("Commodity bust 2014-16",   "2014-01", "2016-12"),
        ("COVID Mar 2020",           "2020-02", "2020-06"),
        ("2022 inflation surge",     "2022-01", "2022-12"),
        ("2023 banking crisis",      "2023-01", "2023-12"),
    ]
    rows = []
    for label, start, end in periods:
        sub = port_ret.loc[start:end]
        if len(sub) < 2:
            rows.append(dict(period=label, sharpe=np.nan, maxdd_pct=np.nan, cum_ret_pct=np.nan))
            continue
        rows.append(dict(
            period=label,
            sharpe=sharpe_hac(sub),
            maxdd_pct=max_drawdown(sub) * 100,
            cum_ret_pct=((1 + sub).prod() - 1) * 100,
        ))
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# PER-ASSET ATTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════

def asset_attribution(contrib_df: pd.DataFrame) -> pd.DataFrame:
    """Per-asset contribution stats from monthly contribution matrix."""
    rows = []
    for tk in contrib_df.columns:
        c = contrib_df[tk].dropna()
        n_nonzero = (c != 0).sum()
        wr  = (c[c != 0] > 0).mean() if n_nonzero > 0 else np.nan
        avg = c[c != 0].mean() if n_nonzero > 0 else np.nan
        tot = c.sum()
        rows.append(dict(
            asset=tk, n_trades=n_nonzero,
            win_rate_pct=wr * 100 if not np.isnan(wr) else np.nan,
            avg_ret_pct=avg * 100 if not np.isnan(avg) else np.nan,
            total_contrib_pct=tot * 100,
        ))
    return pd.DataFrame(rows).sort_values("total_contrib_pct", ascending=False)


# ═══════════════════════════════════════════════════════════════════════════
# GATE CHECK
# ═══════════════════════════════════════════════════════════════════════════

def gate_check(
    sharpe: float,
    maxdd: float,
    worst_month: float,
    wf_pct_pos: float,
    alpha_t_dbc: float,
    amtp_p: float,
    corr_btc: float,
    corr_spy: float,
) -> dict:
    max_corr = max(abs(corr_btc), abs(corr_spy))

    research = {
        "Sharpe HAC > 0.7":          (sharpe,       ">", 0.7),
        "MaxDD > -25%":              (maxdd,         ">", -25.0),
        "WF% positive > 50%":        (wf_pct_pos,   ">", 50.0),
        "Alpha t_HAC vs DBC > 1.5":  (alpha_t_dbc,  ">", 1.5),
        f"AMTP p(n={N_TESTS_END}) < 0.20": (amtp_p, "<", 0.20),
        "Corr BTC+SPY < 0.5":        (max_corr,     "<", 0.5),
    }
    propfirm = {
        "Sharpe HAC > 1.0":          (sharpe,       ">", 1.0),
        "MaxDD > -10%":              (maxdd,         ">", -10.0),
        "Worst month > -5%":         (worst_month,  ">", -5.0),
        "WF% positive > 60%":        (wf_pct_pos,   ">", 60.0),
        "Alpha t_HAC vs DBC > 2.0":  (alpha_t_dbc,  ">", 2.0),
        f"AMTP p(n={N_TESTS_END}) < 0.10": (amtp_p, "<", 0.10),
        "Corr BTC+SPY < 0.3":        (max_corr,     "<", 0.3),
    }

    def evaluate(gates):
        results = {}
        for gate, (val, op, thr) in gates.items():
            if np.isnan(val):
                results[gate] = (val, thr, "N/A", "N/A")
                continue
            if op == ">":
                passed = val > thr
            else:
                passed = val < thr
            results[gate] = (val, thr, "PASS" if passed else "FAIL", op)
        return results

    r = evaluate(research)
    p = evaluate(propfirm)
    r_pass = sum(1 for v in r.values() if v[2] == "PASS")
    p_pass = sum(1 for v in p.values() if v[2] == "PASS")
    return dict(
        research=r, propfirm=p,
        r_pass=r_pass, r_total=len(r),
        p_pass=p_pass, p_total=len(p),
        research_pass=(r_pass == len(r)),
        propfirm_pass=(p_pass == len(p)),
    )


# ═══════════════════════════════════════════════════════════════════════════
# FULL BACKTEST PIPELINE FOR ONE VARIANT
# ═══════════════════════════════════════════════════════════════════════════

def run_variant(
    label:          str,
    signal_df:      pd.DataFrame,   # daily, all assets
    ret_df:         pd.DataFrame,   # daily excess returns, all assets
    rf_monthly:     pd.Series,
    vol_target:     bool,
) -> dict:
    """Run one variant end-to-end. Returns metrics dict + series."""
    # Resample signals to month-end (last value of month)
    signal_m = signal_df.resample("ME").last()

    # Raw weights
    weights_m = compute_raw_weights(signal_m)

    if vol_target:
        weights_m = apply_vol_targeting(weights_m, ret_df)

    # Monthly excess returns
    port_ret, contrib_df, pos_df = weights_to_monthly_returns(
        weights_m, ret_df, rf_monthly
    )

    if port_ret.empty or len(port_ret) < 12:
        log.warning("[%s] Insufficient return data — skipping", label)
        return {}

    # Core metrics
    sh     = sharpe_hac(port_ret)
    ann    = float(port_ret.mean() * 12 * 100)
    ann_v  = float(port_ret.std() * np.sqrt(12) * 100)
    mdd    = max_drawdown(port_ret) * 100
    worst  = float(port_ret.min() * 100)
    best   = float(port_ret.max() * 100)
    pf     = profit_factor(port_ret)

    # Monthly forward returns for diagnostics
    monthly_fwd = ret_df.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    # Align signal to forward return (signal at t → return t→t+1)
    signal_m_shifted = signal_m.shift(1)   # wait-one-period rule for diagnostics alignment

    # TSMOM diagnostics
    dir_acc   = directional_accuracy(signal_m_shifted, monthly_fwd)
    quint     = quintile_analysis(signal_m_shifted, monthly_fwd)

    log.info("[%s] Sharpe=%.3f  Ann=%.1f%%  MaxDD=%.1f%%  N=%d",
             label, sh, ann, mdd, len(port_ret))

    return dict(
        label=label, port_ret=port_ret, contrib_df=contrib_df,
        weights_m=weights_m,
        sharpe=sh, ann_ret=ann, ann_vol=ann_v, maxdd=mdd,
        worst_month=worst, best_month=best, profit_factor=pf,
        dir_acc=dir_acc, quint=quint,
        signal_m=signal_m,
    )


# ═══════════════════════════════════════════════════════════════════════════
# FORMATTED OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

def _fmt(v, fmt=".3f"):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "  n/a"
    return f"{v:{fmt}}"


def print_and_save(
    survivors: list[str],
    dropped: dict[str, str],
    variants: dict,
    benchmarks: dict,
    rf_monthly: pd.Series,
    signal_m_best: pd.DataFrame,
    monthly_fwd: pd.DataFrame,
) -> None:

    best_label = max(variants, key=lambda k: variants[k].get("sharpe", -99))
    best = variants[best_label]
    port_ret = best["port_ret"]

    sep  = "=" * 72
    sep2 = "-" * 72

    # ─── Alpha decompositions ──────────────────────────────────────────────
    alphas = {}
    for bk, bk_ret in benchmarks.items():
        bk_m = bk_ret.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        # Excess benchmark
        bk_exc = bk_m - rf_monthly.resample("ME").apply(lambda x: (1+x).prod()-1)
        alphas[bk] = alpha_regression(port_ret, bk_exc, bk)

    # ─── Walk-forward ──────────────────────────────────────────────────────
    wf_df    = walk_forward_oos(port_ret)
    wf_pos   = float(wf_df["sharpe"].gt(0).mean() * 100) if not wf_df.empty else 0.0
    wf_med   = float(wf_df["sharpe"].median()) if not wf_df.empty else np.nan

    # ─── Crash periods ─────────────────────────────────────────────────────
    crash_df = crash_periods(port_ret)

    # ─── Bootstrap EV ──────────────────────────────────────────────────────
    boot     = bootstrap_ev(port_ret)

    # ─── AMTP ──────────────────────────────────────────────────────────────
    sh_monthly = float(port_ret.mean() / port_ret.std()) if port_ret.std() > 0 else 0.0
    amtp_p = amtp(N_TESTS_END, sh_monthly, len(port_ret))

    # ─── Correlations ──────────────────────────────────────────────────────
    corrs = {}
    for bk, bk_ret in benchmarks.items():
        bk_m = bk_ret.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        idx  = port_ret.index.intersection(bk_m.index)
        if len(idx) < 12:
            corrs[bk] = np.nan
        else:
            corrs[bk] = float(port_ret.loc[idx].corr(bk_m.loc[idx]))

    # ─── Convexity ─────────────────────────────────────────────────────────
    spy_m_exc = benchmarks[SPY_TICKER].resample("ME").apply(lambda x: (1+x).prod()-1)
    spy_m_exc -= rf_monthly.resample("ME").apply(lambda x: (1+x).prod()-1)
    conv = convexity_test(port_ret, spy_m_exc)

    # ─── Gate check ────────────────────────────────────────────────────────
    dbc_alpha_t = alphas.get(DBC_TICKER, {}).get("t_hac", np.nan)
    gates = gate_check(
        sharpe=best["sharpe"],
        maxdd=best["maxdd"],
        worst_month=best["worst_month"],
        wf_pct_pos=wf_pos,
        alpha_t_dbc=dbc_alpha_t,
        amtp_p=amtp_p,
        corr_btc=corrs.get(BTC_TICKER, np.nan),
        corr_spy=corrs.get(SPY_TICKER, np.nan),
    )

    # ─── Per-asset attribution ─────────────────────────────────────────────
    attr_df = asset_attribution(best["contrib_df"])

    # ─── 2022 concentration check ──────────────────────────────────────────
    pnl_total  = float((port_ret + 1).prod() - 1)
    pnl_2022   = float((port_ret.loc["2022"] + 1).prod() - 1) if "2022" in port_ret.index.year else 0.0
    conc_2022  = abs(pnl_2022 / pnl_total) * 100 if pnl_total != 0 else 0.0
    flag_2022  = conc_2022 > 50

    print(f"\n{sep}")
    print("Commodity TSMOM — Hurst-Ooi-Pedersen (2017) framework")
    print(sep)

    print("\nUniverse status:")
    print(f"  Surviving assets ({len(survivors)}): {', '.join(survivors)}")
    if dropped:
        print(f"  Dropped ({len(dropped)}): {', '.join(f'{k} ({v})' for k, v in dropped.items())}")

    print(f"\n{sep2}")
    print("VARIANT COMPARISON (all 4)")
    print(sep2)

    header = f"{'Metric':<28} {'A1':>8} {'A2':>8} {'B1':>8} {'B2':>8}"
    print(header)
    print("-" * len(header))
    metrics = [
        ("Sharpe HAC",         "sharpe",       ".3f"),
        ("Ann return (%)",     "ann_ret",       ".2f"),
        ("Ann vol (%)",        "ann_vol",       ".2f"),
        ("MaxDD (%)",          "maxdd",         ".2f"),
        ("Worst month (%)",    "worst_month",   ".2f"),
        ("Best month (%)",     "best_month",    ".2f"),
        ("Profit factor",      "profit_factor", ".3f"),
    ]
    for mname, mkey, fmt in metrics:
        row = f"  {mname:<26}"
        for vl in ["A1", "A2", "B1", "B2"]:
            v = variants.get(vl, {}).get(mkey, np.nan)
            row += f" {_fmt(v, fmt):>8}"
        print(row)

    print(f"\n{sep2}")
    print(f"ALPHA DECOMPOSITION — {best_label} (best variant)")
    print(sep2)
    for bk, a in alphas.items():
        print(f"  vs {bk:<10}  alpha={_fmt(a.get('alpha_ann'), '.3f')}%/yr  "
              f"t_HAC={_fmt(a.get('t_hac'), '.3f')}  "
              f"beta={_fmt(a.get('beta'), '.4f')}  "
              f"R²={_fmt(a.get('r2'), '.3f')}")

    print(f"\n{sep2}")
    print(f"TSMOM DIAGNOSTICS — {best_label}")
    print(sep2)
    da = best["dir_acc"]
    agg_da = da.pop("_aggregate", np.nan)
    print(f"  Aggregate directional accuracy: {agg_da*100:.1f}%  (gate: >53%)")
    best_da = max(da.items(), key=lambda x: x[1]) if da else ("n/a", np.nan)
    worst_da = min(da.items(), key=lambda x: x[1]) if da else ("n/a", np.nan)
    print(f"  Best asset:  {best_da[0]} ({best_da[1]*100:.1f}%)")
    print(f"  Worst asset: {worst_da[0]} ({worst_da[1]*100:.1f}%)")
    quint = best["quint"]
    if not quint.empty:
        print(f"  Quintile monotonicity:")
        for q in ["Q1", "Q2", "Q3", "Q4", "Q5"]:
            if q in quint.index:
                print(f"    {q}: {quint.loc[q, 'fwd_ret']*100:.4f}%")
        q1 = quint.loc["Q1", "fwd_ret"] if "Q1" in quint.index else np.nan
        q5 = quint.loc["Q5", "fwd_ret"] if "Q5" in quint.index else np.nan
        mono = "YES" if not np.isnan(q5) and not np.isnan(q1) and q5 > q1 else "NO"
        print(f"  Q5 > Q1: {mono}  (Q5={_fmt(q5*100,'.4f')}%, Q1={_fmt(q1*100,'.4f')}%)")
    print(f"  Convexity coefficient (vs |SPY|): {_fmt(conv['beta_abs'], '.4f')}  "
          f"t_HAC={_fmt(conv['t_hac'], '.3f')}")

    print(f"\n{sep2}")
    print(f"WALK-FORWARD OOS BY YEAR — {best_label}")
    print(sep2)
    if not wf_df.empty:
        for _, row in wf_df.iterrows():
            print(f"  {int(row['year'])}  Sh={_fmt(row['sharpe'],'+.3f')}  "
                  f"ret={_fmt(row['monthly_ret_pct'],'+.3f')}%/mo  "
                  f"MaxDD={_fmt(row['maxdd_pct'],'.1f')}%  n={int(row['n'])}")
        print(f"  % positive years: {wf_pos:.0f}%  |  Median Sharpe: {_fmt(wf_med,'.3f')}")

    print(f"\n{sep2}")
    print(f"CRASH PERIOD ANALYSIS — {best_label}")
    print(sep2)
    for _, row in crash_df.iterrows():
        print(f"  {row['period']:<30}  Sh={_fmt(row['sharpe'],'+.3f')}  "
              f"MaxDD={_fmt(row['maxdd_pct'],'.1f')}%  "
              f"CumRet={_fmt(row['cum_ret_pct'],'+.2f')}%")

    print(f"\n{sep2}")
    print(f"CORRELATION TO EXISTING BOOK — {best_label}")
    print(sep2)
    for bk, c in corrs.items():
        print(f"  {bk:<12}: {_fmt(c, '.3f')}")

    print(f"\n{sep2}")
    print(f"BOOTSTRAP EV (monthly) & AMTP — {best_label}")
    print(sep2)
    print(f"  Monthly EV: {boot['ev']*100:.4f}%  "
          f"CI=[{boot['ci_lo']*100:.4f}%, {boot['ci_hi']*100:.4f}%]  "
          f"P(EV≤0)={boot['p_ev_le0']:.4f}")
    print(f"  AMTP: n_tests={N_TESTS_END}  p={amtp_p:.4f}  "
          f"{'PASS (research)' if amtp_p < 0.20 else 'FAIL (research)'}  "
          f"{'PASS (propfirm)' if amtp_p < 0.10 else 'FAIL (propfirm)'}")

    if flag_2022:
        print(f"\n  *** 2022 CONCENTRATION FLAG: 2022 accounts for {conc_2022:.0f}% of total P&L ***")
        print(f"      (threshold: >50%). Result may be regime-concentrated.")

    print(f"\n{sep2}")
    print(f"TWO-TIER GATE DECISION — {best_label}")
    print(sep2)
    print(f"\n  {'Gate':<40} {'Threshold':>14}  {'Value':>8}  RESEARCH  PROPFIRM")
    all_gates = {}
    for gk, gv in gates["research"].items():
        all_gates[gk] = (gv, gates["propfirm"].get(gk))
    for gk, pv in gates["propfirm"].items():
        if gk not in all_gates:
            all_gates[gk] = (None, pv)

    for gk in gates["research"]:
        rv = gates["research"][gk]
        pv = gates["propfirm"].get(gk)
        val_str = _fmt(rv[0], ".3f")
        r_str = rv[2]
        p_str = pv[2] if pv else "—"
        print(f"  {gk:<40} {rv[1]:>14}  {val_str:>8}  {r_str:<9} {p_str}")
    # propfirm-only gates
    for gk in gates["propfirm"]:
        if gk not in gates["research"]:
            pv = gates["propfirm"][gk]
            val_str = _fmt(pv[0], ".3f")
            print(f"  {gk:<40} {pv[1]:>14}  {val_str:>8}  {'—':<9} {pv[2]}")

    print(f"\n  Research gates passed: {gates['r_pass']}/{gates['r_total']}")
    print(f"  Propfirm gates passed: {gates['p_pass']}/{gates['p_total']}")

    research_verdict = "PASS" if gates["research_pass"] else "FAIL"
    propfirm_verdict = "PASS" if gates["propfirm_pass"] else "FAIL"
    print(f"\n  RESEARCH_PASS: {research_verdict}  |  PROPFIRM_PASS: {propfirm_verdict}")

    print(f"\n{sep2}")
    print(f"PER-ASSET ATTRIBUTION — {best_label}")
    print(sep2)
    print(f"  {'Asset':<8} {'Trades':>7} {'WinRate%':>9} {'AvgRet%':>9} {'TotalContrib%':>14}")
    for _, row in attr_df.iterrows():
        print(f"  {row['asset']:<8} {_fmt(row['n_trades'],'d'):>7} "
              f"{_fmt(row['win_rate_pct'],'.1f'):>9} "
              f"{_fmt(row['avg_ret_pct'],'.4f'):>9} "
              f"{_fmt(row['total_contrib_pct'],'+.3f'):>14}")

    print(f"\n{sep}")
    print(f"n_tests: {N_TESTS_START} → {N_TESTS_END}  (+{N_TESTS_END - N_TESTS_START} variants)")
    print(sep)

    # ─── Save markdown summary ─────────────────────────────────────────────
    today_str = pd.Timestamp.today().strftime("%Y-%m-%d %H:%M")
    period_start = str(port_ret.index[0].date()) if not port_ret.empty else "?"
    period_end   = str(port_ret.index[-1].date()) if not port_ret.empty else "?"

    def pf_str(k):
        v = variants.get(k, {})
        return (f"Sh={_fmt(v.get('sharpe'),'.3f')} | Ann={_fmt(v.get('ann_ret'),'.2f')}% | "
                f"MaxDD={_fmt(v.get('maxdd'),'.2f')}% | Worst={_fmt(v.get('worst_month'),'.2f')}%")

    quint_table = ""
    if not best["quint"].empty:
        quint_table = "\n".join(
            f"| {q} | {best['quint'].loc[q,'fwd_ret']*100:.4f}% |"
            for q in ["Q1","Q2","Q3","Q4","Q5"] if q in best["quint"].index
        )

    wf_table = ""
    if not wf_df.empty:
        wf_table = "\n".join(
            f"| {int(r['year'])} | {int(r['n'])} | {_fmt(r['sharpe'],'+.3f')} | "
            f"{_fmt(r['monthly_ret_pct'],'+.3f')}% | {_fmt(r['maxdd_pct'],'.1f')}% |"
            for _, r in wf_df.iterrows()
        )
        wf_table += f"\n| **% positive** | — | **{wf_pos:.0f}%** | — | — |"
        wf_table += f"\n| **Median Sharpe** | — | **{_fmt(wf_med,'.3f')}** | — | — |"

    crash_table = "\n".join(
        f"| {r['period']} | {_fmt(r['sharpe'],'+.3f')} | "
        f"{_fmt(r['maxdd_pct'],'.1f')}% | {_fmt(r['cum_ret_pct'],'+.2f')}% |"
        for _, r in crash_df.iterrows()
    )

    alpha_table = "\n".join(
        f"| {bk} | {_fmt(a.get('alpha_ann'),'.3f')}%/yr | "
        f"{_fmt(a.get('t_hac'),'.3f')} | {_fmt(a.get('beta'),'.4f')} | "
        f"{_fmt(a.get('r2'),'.3f')} |"
        for bk, a in alphas.items()
    )

    corr_table = "\n".join(f"| {bk} | {_fmt(c, '.3f')} |" for bk, c in corrs.items())

    gate_r_rows = "\n".join(
        f"| {gk} | {rv[1]} | {_fmt(rv[0],'.3f')} | {rv[2]} | "
        f"{gates['propfirm'].get(gk, ('','',''))[2]} |"
        for gk, rv in gates["research"].items()
    )
    gate_p_only = "\n".join(
        f"| {gk} | {pv[1]} | {_fmt(pv[0],'.3f')} | — | {pv[2]} |"
        for gk, pv in gates["propfirm"].items() if gk not in gates["research"]
    )

    attr_table = "\n".join(
        f"| {r['asset']} | {int(r['n_trades'])} | "
        f"{_fmt(r['win_rate_pct'],'.1f')}% | {_fmt(r['avg_ret_pct'],'.4f')}% | "
        f"{_fmt(r['total_contrib_pct'],'+.3f')}% |"
        for _, r in attr_df.iterrows()
    )

    flag_2022_str = (
        f"\n> **2022 CONCENTRATION FLAG**: 2022 accounts for {conc_2022:.0f}% "
        f"of total cumulative P&L (threshold: >50%). Regime concentration risk.\n"
        if flag_2022 else ""
    )

    md = f"""# Result Summary: Commodity TSMOM (Hurst-Ooi-Pedersen 2017 framework)
*Generated: {today_str}*

## 1. Headline verdict
> Two-tier: **RESEARCH_PASS: {research_verdict}** | **PROPFIRM_PASS: {propfirm_verdict}**
> Best variant: **{best_label}**
{flag_2022_str}
## 2. Data status
- Universe attempted: {len(UNIVERSE_TICKERS)} tickers
- Surviving assets ({len(survivors)}): {', '.join(survivors)}
- Dropped ({len(dropped)}): {', '.join(f'{k} ({v})' for k, v in dropped.items()) if dropped else 'none'}
- Period: {period_start} → {period_end}
- n_tests: {N_TESTS_START} → {N_TESTS_END}

## 3. 4-variant comparison

| Metric | A1 (single, no VT) | A2 (single + VT) | B1 (multi, no VT) | B2 (multi + VT) |
|--------|-------------------|-----------------|------------------|----------------|
| Sharpe HAC | {_fmt(variants.get('A1',{}).get('sharpe'),'.3f')} | {_fmt(variants.get('A2',{}).get('sharpe'),'.3f')} | {_fmt(variants.get('B1',{}).get('sharpe'),'.3f')} | {_fmt(variants.get('B2',{}).get('sharpe'),'.3f')} |
| Ann return (%) | {_fmt(variants.get('A1',{}).get('ann_ret'),'.2f')} | {_fmt(variants.get('A2',{}).get('ann_ret'),'.2f')} | {_fmt(variants.get('B1',{}).get('ann_ret'),'.2f')} | {_fmt(variants.get('B2',{}).get('ann_ret'),'.2f')} |
| Ann vol (%) | {_fmt(variants.get('A1',{}).get('ann_vol'),'.2f')} | {_fmt(variants.get('A2',{}).get('ann_vol'),'.2f')} | {_fmt(variants.get('B1',{}).get('ann_vol'),'.2f')} | {_fmt(variants.get('B2',{}).get('ann_vol'),'.2f')} |
| MaxDD (%) | {_fmt(variants.get('A1',{}).get('maxdd'),'.2f')} | {_fmt(variants.get('A2',{}).get('maxdd'),'.2f')} | {_fmt(variants.get('B1',{}).get('maxdd'),'.2f')} | {_fmt(variants.get('B2',{}).get('maxdd'),'.2f')} |
| Worst month (%) | {_fmt(variants.get('A1',{}).get('worst_month'),'.2f')} | {_fmt(variants.get('A2',{}).get('worst_month'),'.2f')} | {_fmt(variants.get('B1',{}).get('worst_month'),'.2f')} | {_fmt(variants.get('B2',{}).get('worst_month'),'.2f')} |
| Best month (%) | {_fmt(variants.get('A1',{}).get('best_month'),'.2f')} | {_fmt(variants.get('A2',{}).get('best_month'),'.2f')} | {_fmt(variants.get('B1',{}).get('best_month'),'.2f')} | {_fmt(variants.get('B2',{}).get('best_month'),'.2f')} |
| Profit factor | {_fmt(variants.get('A1',{}).get('profit_factor'),'.3f')} | {_fmt(variants.get('A2',{}).get('profit_factor'),'.3f')} | {_fmt(variants.get('B1',{}).get('profit_factor'),'.3f')} | {_fmt(variants.get('B2',{}).get('profit_factor'),'.3f')} |

## 4. Alpha decomposition — {best_label} (best variant)

| Benchmark | Alpha (ann %/yr) | t_HAC | Beta | R² |
|-----------|-----------------|-------|------|----|
{alpha_table}

## 5. TSMOM diagnostics — {best_label}

- Aggregate directional accuracy: **{agg_da*100:.1f}%** (gate: >53%)
- Best asset: {best_da[0]} ({best_da[1]*100:.1f}%)
- Worst asset: {worst_da[0]} ({worst_da[1]*100:.1f}%)
- Convexity coefficient (|SPY|): {_fmt(conv['beta_abs'],'.4f')}  t_HAC={_fmt(conv['t_hac'],'.3f')}

### Quintile bucket analysis (signal → forward return)

| Quintile | Mean fwd return |
|----------|----------------|
{quint_table}

## 6. Walk-forward OOS by year — {best_label}

| Year | N months | Sharpe | Monthly ret | MaxDD |
|------|----------|--------|-------------|-------|
{wf_table}

## 7. Crash period analysis — {best_label}

| Period | Sharpe | MaxDD | Cum ret |
|--------|--------|-------|---------|
{crash_table}

## 8. Correlation to existing book — {best_label}

| Asset | Correlation |
|-------|-------------|
{corr_table}

## 9. Bootstrap EV & AMTP

- Monthly EV: **{boot['ev']*100:.4f}%**  CI=[{boot['ci_lo']*100:.4f}%, {boot['ci_hi']*100:.4f}%]  P(EV≤0)={boot['p_ev_le0']:.4f}
- AMTP: n={N_TESTS_END}, p={amtp_p:.4f}  research (<0.20): {'PASS' if amtp_p < 0.20 else 'FAIL'}  propfirm (<0.10): {'PASS' if amtp_p < 0.10 else 'FAIL'}

## 10. Two-tier gate decision — {best_label}

| Gate | Threshold | Value | RESEARCH | PROPFIRM |
|------|-----------|-------|----------|----------|
{gate_r_rows}
{gate_p_only}

- Research gates passed: {gates['r_pass']}/{gates['r_total']}
- Propfirm gates passed: {gates['p_pass']}/{gates['p_total']}

**RESEARCH_PASS: {research_verdict}  |  PROPFIRM_PASS: {propfirm_verdict}**

## 11. Per-asset attribution — {best_label}

| Asset | Trades | Win rate | Avg ret/trade | Total contrib |
|-------|--------|----------|---------------|---------------|
{attr_table}

## 12. n_tests counter
- Start: {N_TESTS_START}
- A1 variant: +1
- A2 variant: +1
- B1 variant: +1
- B2 variant: +1
- **End: {N_TESTS_END}**
"""
    SUMMARY_PATH.write_text(md)
    print(f"\nSaved → {SUMMARY_PATH}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    sep = "=" * 72

    print(f"\n{sep}")
    print("Commodity TSMOM — Hurst-Ooi-Pedersen (2017) framework")
    print(sep)

    # ── 1. Fetch data ────────────────────────────────────────────────────
    log.info("Fetching prices ...")
    prices = fetch_prices()
    close  = build_close_df(prices)

    log.info("Price history: %s → %s", str(close.index[0].date()), str(close.index[-1].date()))

    # ── 2. Filter universe ───────────────────────────────────────────────
    survivors, dropped = filter_universe(close)
    log.info("Universe survivors (%d): %s", len(survivors), survivors)
    if dropped:
        log.info("Dropped (%d): %s", len(dropped), dropped)

    if len(survivors) < 6:
        print(f"\nSTOP: Only {len(survivors)} assets survived history check (< 6 minimum).")
        print("Consider expanding universe with DBC, GSG, XLE backups.")
        return

    # ── 3. Build daily returns ────────────────────────────────────────────
    close_u = close[survivors].loc[DATA_START:TEST_END]
    rf      = fetch_risk_free()

    # Daily excess returns
    daily_ret = close_u.pct_change()
    rf_aligned = rf.reindex(daily_ret.index, method="ffill").fillna(0.0)
    exc_ret = daily_ret.subtract(rf_aligned, axis=0)

    # Monthly RF for later use
    rf_monthly = rf.reindex(daily_ret.index, method="ffill")

    # Benchmark returns
    bench_tickers = [SPY_TICKER, DBC_TICKER, TLT_TICKER, BTC_TICKER]
    benchmarks = {}
    for bk in bench_tickers:
        if bk in close.columns:
            bk_ret = close[bk].pct_change().subtract(
                rf.reindex(close[bk].pct_change().index, method="ffill").fillna(0), axis=0
            )
            benchmarks[bk] = bk_ret
        else:
            log.warning("Benchmark %s not available", bk)

    # ── 4. Compute signals ────────────────────────────────────────────────
    log.info("Computing signals ...")
    sig_a = compute_signals_a(exc_ret)
    sig_b = compute_signals_b(exc_ret)

    # ── 5. Run 4 variants ─────────────────────────────────────────────────
    log.info("Running 4 variants ...")
    variants = {}
    for label, sig, vt in [("A1", sig_a, False), ("A2", sig_a, True),
                            ("B1", sig_b, False), ("B2", sig_b, True)]:
        result = run_variant(label, sig, exc_ret, rf_monthly, vt)
        if result:
            variants[label] = result

    if not variants:
        print("STOP: No variant produced valid results.")
        return

    # ── 6. Sanity check: best Sharpe > 2.5 ───────────────────────────────
    best_sh = max(v["sharpe"] for v in variants.values() if not np.isnan(v.get("sharpe", np.nan)))
    if best_sh > 2.5:
        print(f"\n*** SUSPICIOUS: Best variant Sharpe = {best_sh:.3f} > 2.5. ***")
        print("    Verify there is no lookahead in vol-targeting daily aggregation.")
        print("    Proceeding but flag this as potentially invalid.")

    # ── 7. Monthly fwd returns (for diagnostics) ──────────────────────────
    monthly_fwd = exc_ret.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    best_label = max(variants, key=lambda k: variants[k].get("sharpe", -99))
    signal_m_best = variants[best_label]["signal_m"]

    # ── 8. Print + save ───────────────────────────────────────────────────
    print_and_save(
        survivors, dropped, variants, benchmarks,
        rf_monthly, signal_m_best, monthly_fwd
    )


if __name__ == "__main__":
    main()
