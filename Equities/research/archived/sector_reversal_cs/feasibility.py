"""
Cross-Sectional Sector Reversal — Jegadeesh (1990) / Lehmann (1990) framework
==============================================================================

Reference:
  Jegadeesh, N. (1990) "Evidence of Predictable Behavior of Security Returns", JF.
  Lehmann, B.N. (1990) "Fads, Martingales and Market Efficiency", QJE.

Theory:
  Sector ETF weekly returns contain a liquidity-provision component: when a sector
  moves strongly in one week, part of that move compensates market makers for
  absorbing one-sided flow. That compensation reverts over the following week.
  Strategy: rank 9–11 SPDR sector ETFs by trailing 1-week return, short the top 2
  (recent winners due to revert), long the bottom 2 (recent losers due to recover).
  Hold 1 week. Dollar-neutral.

Why this is NOT just inverted momentum:
  - Momentum: multi-month horizon (12M-1M). Driven by information diffusion.
  - Reversal: 1-week horizon. Driven by liquidity microstructure.
  - Both can coexist (Jegadeesh-Titman 1993 acknowledges short-term reversal
    coexisting with medium-term momentum).

Four variants:
  V1 — Pure reversal (1W look-back, 1W hold)
  V2 — Filtered (skip weeks where any sector |ret| > 3σ — genuine information)
  V3 — Vol-targeted (V1 + 8% annual vol target, 21-day lookback, 1.5× cap)
  V4 — Combined (V2 + V3)

Methodology standards (all 5 canonical):
  1. Excess returns over FRED DTB3 daily RF
  2. HAC SE lag-6 for alpha regressions (and Sharpe with correct LRV formula)
  3. Weekly Sharpe = mean / σ × √52 (correct: LRV-based for HAC version)
  4. Strategy diagnostics: hit rate, turnover, SRV factor loading
  5. approx_multi_test_penalty (n_tests 78 → 82)
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
from scipy.stats import norm

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.cache import get_cached_or_fetch  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DATA_START  = "2004-06-01"    # buffer for warm-up
TEST_START  = "2005-01-01"
TEST_END    = "2026-05-01"

# 11 SPDR sector ETFs. XLRE/XLC have later starts.
SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLB", "XLU", "XLRE", "XLC"]
# Approx launch dates (start trading these weeks only after launch)
SECTOR_LAUNCH = {
    "XLRE": pd.Timestamp("2015-10-07"),
    "XLC":  pd.Timestamp("2018-06-25"),
}

N_LONG  = 2    # bottom N sectors: long
N_SHORT = 2    # top N sectors: short

# Costs: 4 bps per one-way trade per sector
COST_ONE_WAY = 0.0004

# Vol targeting
VT_TARGET  = 0.08    # 8% annual vol
VT_LB      = 21      # 21-day rolling vol lookback
VT_LEV_CAP = 1.5

# Multi-test
N_TESTS_START = 78
N_TESTS_END   = 82   # +4 variants

# Bootstrap
N_BOOT = 20_000

# Benchmarks
BENCHMARKS = ["SPY", "TLT", "BTC-USD"]

# Walk-forward: split by calendar year (no free params to calibrate)
WF_MIN_YEAR = 2008

SUMMARY_PATH = _HERE / "sector_reversal_summary.md"


# ═══════════════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════════════

def fetch_all() -> dict[str, pd.Series]:
    """Fetch close prices for all sectors + benchmarks."""
    tickers = SECTORS + BENCHMARKS
    closes = {}
    for tk in tickers:
        df = get_cached_or_fetch(tk, start=DATA_START, end=TEST_END, interval="1d")
        if df.empty:
            log.warning("  No data for %s", tk)
            continue
        col = "close" if "close" in df.columns else df.columns[0]
        closes[tk] = df[col].rename(tk)
    return closes


def fetch_risk_free() -> pd.Series:
    try:
        dtb3 = pdr.DataReader("DTB3", "fred", DATA_START, TEST_END)["DTB3"].ffill() / 100
        return (1 + dtb3) ** (1 / 252) - 1
    except Exception as exc:
        log.warning("FRED fetch failed (%s) — rf=0", exc)
        return pd.Series(0.0, index=pd.date_range(DATA_START, TEST_END, freq="B"))


def fetch_ff_factors() -> pd.DataFrame | None:
    """Fetch FF3 + Momentum + SRV + LRV monthly factors (returns as decimals)."""
    try:
        ff3  = pdr.DataReader("F-F_Research_Data_Factors",  "famafrench",
                              start=DATA_START, end=TEST_END)[0] / 100
        mom  = pdr.DataReader("F-F_Momentum_Factor",         "famafrench",
                              start=DATA_START, end=TEST_END)[0] / 100
        srv  = pdr.DataReader("F-F_ST_Reversal_Factor",      "famafrench",
                              start=DATA_START, end=TEST_END)[0] / 100
        lrv  = pdr.DataReader("F-F_LT_Reversal_Factor",      "famafrench",
                              start=DATA_START, end=TEST_END)[0] / 100
        factors = ff3[["Mkt-RF", "SMB", "HML", "RF"]].copy()
        factors["MOM"]    = mom["Mom"]
        factors["SRV"]    = srv["ST_Rev"]
        factors["LRV"]    = lrv["LT_Rev"]
        factors.index = factors.index.to_timestamp(how="end")
        factors.index = factors.index.normalize()
        log.info("FF factors loaded: %d rows", len(factors))
        return factors
    except Exception as exc:
        log.warning("FF factor fetch failed: %s", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL + SIMULATION
# ═══════════════════════════════════════════════════════════════════════════

def available_sectors_at(week_date: pd.Timestamp) -> list[str]:
    return [s for s in SECTORS
            if week_date >= SECTOR_LAUNCH.get(s, pd.Timestamp("2000-01-01"))]


def simulate_variant(
    weekly_ret:  pd.DataFrame,   # weekly excess returns, index=Friday dates, cols=sectors
    daily_ret:   pd.DataFrame,   # daily excess returns
    label:       str,
    filter_v2:   bool,
    vt_target:   float | None,
) -> dict:
    """
    Simulate one variant. Returns metrics dict with weekly return series.

    Signal timing:
      - Week T: prev_week_ret = weekly_ret.shift(1).loc[T]  (Friday T-1 close → Friday T close)
      - Position held during week T+1 (Monday T+1 open to Friday T+1 close)
      - Return earned: weekly_ret.loc[T+1]
    Implementation: for each row T of weekly_ret, the SIGNAL is the return AT T,
    and the position is applied to the return at T+1. We loop forward.
    """
    dates     = weekly_ret.index
    n_weeks   = len(dates)

    # Rolling 52-week vol per sector (for V2 filter)
    rolling_vol_52 = weekly_ret.rolling(52, min_periods=26).std()

    # Build daily P&L buffer for vol targeting
    daily_pnl_raw = pd.Series(0.0, index=daily_ret.index)

    records    = []   # (date, net_ret, gross_ret, cost, n_long_changes, n_short_changes)
    attr       = {s: {"n_long": 0, "n_short": 0,
                      "pnl_long": 0.0, "pnl_short": 0.0,
                      "wins_long": 0, "wins_short": 0} for s in SECTORS}
    prev_longs  : set[str] = set()
    prev_shorts : set[str] = set()
    prev_scale  = 1.0

    for i in range(1, n_weeks):
        week_date  = dates[i]
        signal_date = dates[i - 1]    # signal from last Friday

        if pd.Timestamp(week_date) < pd.Timestamp(TEST_START):
            continue

        avail = available_sectors_at(week_date)
        if len(avail) < N_LONG + N_SHORT + 1:
            records.append((week_date, 0.0, 0.0, 0.0, 0, 0))
            continue

        # Previous week returns for signal computation
        sig_rets = weekly_ret.loc[signal_date, avail].dropna()
        if len(sig_rets) < N_LONG + N_SHORT + 1:
            records.append((week_date, 0.0, 0.0, 0.0, 0, 0))
            continue

        # ── V2 filter: skip week if any sector had |prev_ret| > 3σ ─────────
        if filter_v2:
            vols = rolling_vol_52.loc[signal_date, avail].dropna()
            if len(vols) == len(sig_rets):
                thresholds = 3.0 * vols
                if (sig_rets.abs() > thresholds).any():
                    # Skip: hold cash
                    records.append((week_date, 0.0, 0.0, 0.0, 0, 0))
                    prev_longs  = set()
                    prev_shorts = set()
                    continue

        # ── Rank and assign positions ────────────────────────────────────────
        ranked  = sig_rets.sort_values()
        longs   = set(ranked.index[:N_LONG])
        shorts  = set(ranked.index[-N_SHORT:])

        # ── This week's returns ──────────────────────────────────────────────
        curr_rets = weekly_ret.loc[week_date, avail].dropna()
        long_ret  = curr_rets.reindex(longs).mean()
        short_ret = curr_rets.reindex(shorts).mean()
        gross_ret = float(long_ret - short_ret)    # L/S spread on $1 L + $1 S

        # ── Costs ────────────────────────────────────────────────────────────
        # Initial entry: no prev positions means all 4 entries are new
        exits_from_longs  = prev_longs  - longs
        entries_to_longs  = longs       - prev_longs
        exits_from_shorts = prev_shorts - shorts
        entries_to_shorts = shorts      - prev_shorts
        n_one_way = (len(exits_from_longs) + len(entries_to_longs) +
                     len(exits_from_shorts) + len(entries_to_shorts))
        cost = n_one_way * COST_ONE_WAY

        # ── Vol targeting scale ──────────────────────────────────────────────
        if vt_target is not None:
            scale = float(np.clip(prev_scale, 1e-3, VT_LEV_CAP))
        else:
            scale = 1.0

        net_ret = gross_ret * scale - cost

        records.append((week_date, net_ret, gross_ret, cost,
                        len(entries_to_longs), len(entries_to_shorts)))

        # ── Daily P&L for vol targeting update ───────────────────────────────
        # Get business days that fall within this week (signal_date to week_date inclusive)
        day_mask = (daily_ret.index > signal_date) & (daily_ret.index <= week_date)
        week_days = daily_ret.index[day_mask]
        if len(week_days) > 0 and vt_target is not None:
            for s in longs:
                if s in daily_ret.columns:
                    daily_pnl_raw.loc[week_days] += (daily_ret.loc[week_days, s] * 0.5 * scale)
            for s in shorts:
                if s in daily_ret.columns:
                    daily_pnl_raw.loc[week_days] -= (daily_ret.loc[week_days, s] * 0.5 * scale)

        # ── Update vol targeting for NEXT week ───────────────────────────────
        if vt_target is not None and week_date in daily_pnl_raw.index:
            # Realized daily vol over last VT_LB days
            idx_pos = daily_pnl_raw.index.get_loc(week_date)
            start_idx = max(0, idx_pos - VT_LB + 1)
            window = daily_pnl_raw.iloc[start_idx:idx_pos + 1]
            realized_vol_ann = float(window.std() * np.sqrt(252))
            if realized_vol_ann > 1e-6:
                prev_scale = float(np.clip(vt_target / realized_vol_ann, 1e-3, VT_LEV_CAP))

        # ── Per-sector attribution ────────────────────────────────────────────
        for s in longs:
            if s in curr_rets.index:
                r = float(curr_rets[s]) * scale
                attr[s]["n_long"]    += 1
                attr[s]["pnl_long"]  += r
                attr[s]["wins_long"] += int(r > 0)
        for s in shorts:
            if s in curr_rets.index:
                r = -float(curr_rets[s]) * scale
                attr[s]["n_short"]    += 1
                attr[s]["pnl_short"]  += r
                attr[s]["wins_short"] += int(r > 0)

        prev_longs  = longs
        prev_shorts = shorts

    # Compile weekly return series
    idx       = pd.DatetimeIndex([r[0] for r in records])
    net_rets  = pd.Series([r[1] for r in records], index=idx)
    gross_rets = pd.Series([r[2] for r in records], index=idx)
    costs_s    = pd.Series([r[3] for r in records], index=idx)

    # Restrict to TEST window
    mask = (net_rets.index >= TEST_START) & (net_rets.index <= TEST_END)
    net_rets   = net_rets[mask]
    gross_rets = gross_rets[mask]
    costs_s    = costs_s[mask]

    n_active = (net_rets != 0).sum()
    hit_rate = float((gross_rets[gross_rets != 0] > 0).mean()) if n_active > 0 else np.nan
    avg_cost = float(costs_s[costs_s > 0].mean()) if (costs_s > 0).any() else 0.0
    annual_cost = avg_cost * 52

    sh  = sharpe_hac_weekly(net_rets)
    mdd = max_drawdown(net_rets)
    ann = float(net_rets.mean() * 52 * 100)
    ann_v = float(net_rets.std() * np.sqrt(52) * 100)
    wst = float(net_rets.min() * 100)
    bst = float(net_rets.max() * 100)
    pf  = profit_factor(net_rets)

    log.info("[%s] Sharpe=%.3f  Ann=%.1f%%  MaxDD=%.1f%%  HitRate=%.1f%%  AnnCost=%.2f%%  N=%d",
             label, sh, ann, mdd * 100, hit_rate * 100, annual_cost * 100, len(net_rets))

    return dict(
        label=label, net_rets=net_rets, gross_rets=gross_rets, costs=costs_s,
        sharpe=sh, ann_ret=ann, ann_vol=ann_v, maxdd=mdd * 100,
        worst_week=wst, best_week=bst, profit_factor=pf,
        hit_rate=hit_rate * 100, avg_weekly_cost=avg_cost * 100,
        annual_cost_drag=annual_cost * 100,
        avg_turnover=float(costs_s[costs_s > 0].count() / len(costs_s)),
        attr=attr,
    )


# ═══════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

def sharpe_hac_weekly(ret: pd.Series) -> float:
    """
    HAC-adjusted Sharpe on weekly returns.
    Correct formula: mean / sqrt(LRV) × sqrt(52)
    where LRV = reg.cov_params()[0,0] × n (long-run variance per period).
    For n < 48 weeks, fall back to simple Sharpe.
    """
    r = ret.dropna()
    n = len(r)
    if n < 10:
        return np.nan
    mean = float(r.mean())
    std  = float(r.std())
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


def max_drawdown(ret: pd.Series) -> float:
    cum = (1 + ret).cumprod()
    return float(((cum - cum.cummax()) / cum.cummax()).min())


def profit_factor(ret: pd.Series) -> float:
    wins  = ret[ret > 0].sum()
    loses = ret[ret < 0].abs().sum()
    return float(wins / loses) if loses > 0 else np.inf


def alpha_regression(
    port_ret: pd.Series,
    bench_ret: pd.Series,
) -> dict:
    """HAC alpha regression. Returns alpha_ann, t_hac, beta, r2."""
    idx = port_ret.index.intersection(bench_ret.index)
    if len(idx) < 24:
        return dict(alpha_ann=np.nan, t_hac=np.nan, beta=np.nan, r2=np.nan)
    y = port_ret.loc[idx].values
    x = bench_ret.loc[idx].values
    valid = np.isfinite(y) & np.isfinite(x)
    y, x = y[valid], x[valid]
    if len(y) < 24:
        return dict(alpha_ann=np.nan, t_hac=np.nan, beta=np.nan, r2=np.nan)
    X = sm.add_constant(x)
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return dict(
        alpha_ann=float(res.params[0] * 52),
        t_hac=float(res.tvalues[0]),
        beta=float(res.params[1]),
        r2=float(res.rsquared),
    )


def six_factor_regression(port_ret_weekly: pd.Series, ff_monthly: pd.DataFrame) -> dict | None:
    """
    Regress monthly-aggregated portfolio excess returns on 6 factors:
    MKT, SMB, HML, MOM, SRV (short-term reversal), LRV (long-term reversal).
    The SRV loading should be POSITIVE if we genuinely capture the ST reversal premium.
    """
    if ff_monthly is None:
        return None
    # Aggregate weekly → monthly
    port_monthly = port_ret_weekly.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    idx = port_monthly.index.intersection(ff_monthly.index)
    if len(idx) < 24:
        return None
    y  = port_monthly.loc[idx].values
    X  = ff_monthly.loc[idx, ["Mkt-RF", "SMB", "HML", "MOM", "SRV", "LRV"]].values
    valid = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    y, X = y[valid], X[valid]
    if len(y) < 24:
        return None
    Xc = sm.add_constant(X)
    res = sm.OLS(y, Xc).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    names = ["alpha_m", "MKT", "SMB", "HML", "MOM", "SRV", "LRV"]
    return {
        names[i]: {"coef": float(res.params[i]), "t": float(res.tvalues[i])}
        for i in range(len(names))
    } | {"r2": float(res.rsquared)}


def bootstrap_ev(ret: pd.Series) -> dict:
    r = ret.dropna().values
    means = np.array([np.mean(np.random.choice(r, len(r), replace=True)) for _ in range(N_BOOT)])
    return dict(
        ev=float(r.mean()),
        ci_lo=float(np.percentile(means, 2.5)),
        ci_hi=float(np.percentile(means, 97.5)),
        p_ev_le0=float(np.mean(means <= 0)),
    )


def amtp(n_tests: int, sharpe_weekly: float, n_obs: int) -> float:
    if n_tests <= 1:
        return 0.0
    sr_star = (
        (1 - np.euler_gamma) * norm.ppf(1 - 1 / n_tests)
        + np.euler_gamma * norm.ppf(1 - 1 / (n_tests * np.e))
    )
    sr_scaled = sharpe_weekly * np.sqrt(n_obs)
    return float(1 - norm.cdf(sr_scaled - sr_star))


def walk_forward(ret: pd.Series) -> pd.DataFrame:
    results = []
    for yr in sorted(ret.index.year.unique()):
        if yr < WF_MIN_YEAR:
            continue
        sub = ret[ret.index.year == yr]
        if len(sub) < 10:
            continue
        results.append(dict(
            year=yr, n=len(sub),
            sharpe=sharpe_hac_weekly(sub),
            monthly_ret_pct=float(sub.mean() * 100),
            maxdd_pct=max_drawdown(sub) * 100,
        ))
    return pd.DataFrame(results)


def crash_analysis(ret: pd.Series) -> pd.DataFrame:
    periods = [
        ("GFC 2008",          "2008-01", "2008-12"),
        ("EuroCrisis 2011",   "2011-01", "2011-12"),
        ("COVID Mar 2020",    "2020-02", "2020-06"),
        ("2022 inflation",    "2022-01", "2022-12"),
        ("2023 banking",      "2023-01", "2023-12"),
    ]
    rows = []
    for label, s, e in periods:
        sub = ret.loc[s:e]
        if len(sub) < 2:
            rows.append(dict(period=label, sharpe=np.nan, maxdd_pct=np.nan,
                             cum_ret_pct=np.nan, hit_pct=np.nan))
            continue
        nz = sub[sub != 0]
        rows.append(dict(
            period=label,
            sharpe=sharpe_hac_weekly(sub),
            maxdd_pct=max_drawdown(sub) * 100,
            cum_ret_pct=((1 + sub).prod() - 1) * 100,
            hit_pct=float((nz > 0).mean() * 100) if len(nz) > 0 else np.nan,
        ))
    return pd.DataFrame(rows)


def gate_check(
    sharpe: float, maxdd: float, worst_week: float, wf_pct_pos: float,
    alpha_t_ew: float, amtp_p: float, corr_btc: float, corr_spy: float,
) -> dict:
    max_corr = max(abs(corr_btc), abs(corr_spy))
    research = {
        "Sharpe HAC > 0.7":             (sharpe,     ">", 0.7),
        "MaxDD > -25%":                 (maxdd,      ">", -25.0),
        "WF% positive > 50%":           (wf_pct_pos, ">", 50.0),
        "Alpha t_HAC vs EW sctrs > 1.5":(alpha_t_ew, ">", 1.5),
        f"AMTP p(n={N_TESTS_END}) < 0.20": (amtp_p, "<", 0.20),
        "Corr BTC+SPY < 0.5":           (max_corr,   "<", 0.5),
    }
    propfirm = {
        "Sharpe HAC > 1.0":             (sharpe,     ">", 1.0),
        "MaxDD > -10%":                 (maxdd,      ">", -10.0),
        "Worst week > -5%":             (worst_week, ">", -5.0),
        "WF% positive > 60%":           (wf_pct_pos, ">", 60.0),
        "Alpha t_HAC vs EW sctrs > 2.0":(alpha_t_ew, ">", 2.0),
        f"AMTP p(n={N_TESTS_END}) < 0.10": (amtp_p, "<", 0.10),
        "Corr BTC+SPY < 0.3":           (max_corr,   "<", 0.3),
    }

    def evaluate(gates):
        out = {}
        for k, (v, op, thr) in gates.items():
            if np.isnan(v):
                out[k] = (v, thr, "N/A")
            elif op == ">":
                out[k] = (v, thr, "PASS" if v > thr else "FAIL")
            else:
                out[k] = (v, thr, "PASS" if v < thr else "FAIL")
        return out

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
# FORMATTED OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

def _f(v, fmt=".3f"):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "   n/a"
    return f"{v:{fmt}}"


def print_and_save(
    variants: dict,
    benchmarks_weekly: dict,
    ew_sector_weekly: pd.Series,
    ff_monthly: pd.DataFrame | None,
    rf_weekly: pd.Series,
) -> None:

    best_label = max(variants, key=lambda k: variants[k].get("sharpe", -99))
    best = variants[best_label]
    port = best["net_rets"]

    sep  = "=" * 72
    sep2 = "-" * 72

    # ── Alpha vs benchmarks ──────────────────────────────────────────────
    alphas = {}
    for bk, bk_w in benchmarks_weekly.items():
        alphas[bk] = alpha_regression(port, bk_w)
    alphas["EW_sectors"] = alpha_regression(port, ew_sector_weekly)

    # ── 6-factor regression ───────────────────────────────────────────────
    six_f = six_factor_regression(port, ff_monthly)

    # ── Walk-forward ─────────────────────────────────────────────────────
    wf_df  = walk_forward(port)
    wf_pos = float((wf_df["sharpe"] > 0).mean() * 100) if not wf_df.empty else 0.0
    wf_med = float(wf_df["sharpe"].median()) if not wf_df.empty else np.nan

    # ── Crash ─────────────────────────────────────────────────────────────
    crash_df = crash_analysis(port)

    # ── Bootstrap ────────────────────────────────────────────────────────
    boot = bootstrap_ev(port)

    # ── AMTP ─────────────────────────────────────────────────────────────
    sh_weekly = float(port.mean() / port.std()) if port.std() > 0 else 0.0
    amtp_p    = amtp(N_TESTS_END, sh_weekly, len(port))

    # ── Correlations ─────────────────────────────────────────────────────
    corrs = {}
    for bk, bk_w in benchmarks_weekly.items():
        idx = port.index.intersection(bk_w.index)
        corrs[bk] = float(port.loc[idx].corr(bk_w.loc[idx])) if len(idx) >= 12 else np.nan
    corrs["EW_sectors"] = (float(port.corr(ew_sector_weekly.reindex(port.index).dropna()))
                           if len(port.index.intersection(ew_sector_weekly.index)) >= 12 else np.nan)

    # ── Gates ─────────────────────────────────────────────────────────────
    alpha_t_ew = alphas["EW_sectors"]["t_hac"]
    gates = gate_check(
        sharpe=best["sharpe"],
        maxdd=best["maxdd"],
        worst_week=best["worst_week"],
        wf_pct_pos=wf_pos,
        alpha_t_ew=alpha_t_ew,
        amtp_p=amtp_p,
        corr_btc=corrs.get("BTC-USD", np.nan),
        corr_spy=corrs.get("SPY", np.nan),
    )

    # ── Sector attribution ────────────────────────────────────────────────
    attr = best["attr"]
    attr_rows = []
    for s in SECTORS:
        a = attr[s]
        wr_l = a["wins_long"] / a["n_long"] * 100 if a["n_long"] > 0 else np.nan
        wr_s = a["wins_short"] / a["n_short"] * 100 if a["n_short"] > 0 else np.nan
        net_pnl = (a["pnl_long"] + a["pnl_short"]) * 100
        attr_rows.append(dict(
            sector=s,
            n_long=a["n_long"], n_short=a["n_short"],
            net_pnl_pct=net_pnl,
            wr_long=wr_l, wr_short=wr_s,
        ))
    attr_df = pd.DataFrame(attr_rows).sort_values("net_pnl_pct", ascending=False)

    # ═══ PRINT ═══════════════════════════════════════════════════════════
    print(f"\n{sep}")
    print("Cross-Sectional Sector Reversal — Jegadeesh (1990) / Lehmann (1990)")
    print(sep)

    print(f"\n{sep2}")
    print("VARIANT COMPARISON (all 4)")
    print(sep2)
    print(f"  {'Metric':<28} {'V1':>8} {'V2':>8} {'V3':>8} {'V4':>8}")
    print("  " + "-" * 60)
    for mname, mkey, fmt in [
        ("Sharpe HAC",       "sharpe",           ".3f"),
        ("Ann return (%)",   "ann_ret",           ".2f"),
        ("Ann vol (%)",      "ann_vol",           ".2f"),
        ("MaxDD (%)",        "maxdd",             ".2f"),
        ("Worst week (%)",   "worst_week",        ".2f"),
        ("Best week (%)",    "best_week",         ".2f"),
        ("Profit factor",    "profit_factor",     ".3f"),
        ("Hit rate (%)",     "hit_rate",          ".1f"),
        ("Ann cost drag (%)","annual_cost_drag",  ".2f"),
    ]:
        row = f"  {mname:<28}"
        for vl in ["V1", "V2", "V3", "V4"]:
            v = variants.get(vl, {}).get(mkey, np.nan)
            row += f" {_f(v, fmt):>8}"
        print(row)

    print(f"\n{sep2}")
    print(f"ALPHA DECOMPOSITION — {best_label} (best variant)")
    print(sep2)
    for bk, a in alphas.items():
        print(f"  vs {bk:<16}  alpha={_f(a.get('alpha_ann'),'.3f')}%/yr  "
              f"t_HAC={_f(a.get('t_hac'),'.3f')}  "
              f"beta={_f(a.get('beta'),'.4f')}  R²={_f(a.get('r2'),'.3f')}")

    print(f"\n{sep2}")
    print(f"6-FACTOR DECOMPOSITION — {best_label}")
    print(sep2)
    if six_f:
        print(f"  {'Factor':<8} {'Coeff':>12} {'t_HAC':>8}")
        factor_names = ["alpha_m", "MKT", "SMB", "HML", "MOM", "SRV", "LRV"]
        for fn in factor_names:
            if fn in six_f:
                coef = six_f[fn]["coef"]
                t    = six_f[fn]["t"]
                ann_note = " (×12=%+.3f%%/yr)" % (coef*12*100) if fn == "alpha_m" else ""
                srv_note = " ← KEY: expect positive" if fn == "SRV" else ""
                print(f"  {fn:<8} {coef:>12.4f} {t:>8.3f}{ann_note}{srv_note}")
        print(f"  R² = {six_f['r2']:.3f}")
    else:
        print("  Factor data unavailable")

    print(f"\n{sep2}")
    print(f"WALK-FORWARD BY YEAR — {best_label}")
    print(sep2)
    if not wf_df.empty:
        for _, r in wf_df.iterrows():
            print(f"  {int(r['year'])}  Sh={_f(r['sharpe'],'+.3f')}  "
                  f"mean={_f(r['monthly_ret_pct'],'+.3f')}%/wk  "
                  f"MaxDD={_f(r['maxdd_pct'],'.1f')}%  n={int(r['n'])}")
        print(f"  % positive years: {wf_pos:.0f}%  |  Median Sharpe: {_f(wf_med,'.3f')}")

    print(f"\n{sep2}")
    print(f"CRASH PERIOD ANALYSIS — {best_label}")
    print(sep2)
    for _, r in crash_df.iterrows():
        print(f"  {r['period']:<25}  Sh={_f(r['sharpe'],'+.3f')}  "
              f"MaxDD={_f(r['maxdd_pct'],'.1f')}%  "
              f"CumRet={_f(r['cum_ret_pct'],'+.2f')}%  "
              f"HitRate={_f(r['hit_pct'],'.1f')}%")

    print(f"\n{sep2}")
    print(f"CORRELATIONS — {best_label}")
    print(sep2)
    for bk, c in corrs.items():
        print(f"  {bk:<16}: {_f(c, '.3f')}")

    print(f"\n{sep2}")
    print(f"BOOTSTRAP EV & AMTP — {best_label}")
    print(sep2)
    print(f"  Weekly EV: {boot['ev']*100:.4f}%  "
          f"CI=[{boot['ci_lo']*100:.4f}%, {boot['ci_hi']*100:.4f}%]  "
          f"P(EV≤0)={boot['p_ev_le0']:.4f}")
    print(f"  AMTP: n={N_TESTS_END}  p={amtp_p:.4f}  "
          f"{'PASS (research)' if amtp_p<0.20 else 'FAIL (research)'}  "
          f"{'PASS (propfirm)' if amtp_p<0.10 else 'FAIL (propfirm)'}")

    print(f"\n{sep2}")
    print(f"TWO-TIER GATE DECISION — {best_label}")
    print(sep2)
    print(f"  {'Gate':<44} {'Thr':>6}  {'Value':>8}  RESEARCH  PROPFIRM")
    for gk, rv in gates["research"].items():
        pv = gates["propfirm"].get(gk)
        print(f"  {gk:<44} {rv[1]:>6}  {_f(rv[0],'.3f'):>8}  "
              f"{rv[2]:<9} {pv[2] if pv else '—'}")
    for gk, pv in gates["propfirm"].items():
        if gk not in gates["research"]:
            print(f"  {gk:<44} {pv[1]:>6}  {_f(pv[0],'.3f'):>8}  {'—':<9} {pv[2]}")
    print(f"\n  Research: {gates['r_pass']}/{gates['r_total']}  "
          f"Propfirm: {gates['p_pass']}/{gates['p_total']}")
    rv_str = "PASS" if gates["research_pass"] else "FAIL"
    pv_str = "PASS" if gates["propfirm_pass"] else "FAIL"
    print(f"\n  RESEARCH_PASS: {rv_str}  |  PROPFIRM_PASS: {pv_str}")

    print(f"\n{sep2}")
    print(f"SECTOR ATTRIBUTION — {best_label}")
    print(sep2)
    print(f"  {'Sector':<6} {'#Long':>6} {'#Short':>7} {'Net P&L%':>9} "
          f"{'WR Long%':>9} {'WR Short%':>10}")
    for _, r in attr_df.iterrows():
        print(f"  {r['sector']:<6} {r['n_long']:>6} {r['n_short']:>7} "
              f"{_f(r['net_pnl_pct'],'+.3f'):>9} "
              f"{_f(r['wr_long'],'.1f'):>9}% {_f(r['wr_short'],'.1f'):>9}%")

    print(f"\n{sep}")
    print(f"n_tests: {N_TESTS_START} → {N_TESTS_END}  (+{N_TESTS_END - N_TESTS_START} variants)")
    print(sep)

    # ─── Save markdown ───────────────────────────────────────────────────
    today_str = pd.Timestamp.today().strftime("%Y-%m-%d %H:%M")
    period_start = str(port.index[0].date()) if not port.empty else "?"
    period_end   = str(port.index[-1].date()) if not port.empty else "?"

    def vv(vl, k, fmt=".3f"):
        return _f(variants.get(vl, {}).get(k, np.nan), fmt)

    srv_note = ""
    if six_f and "SRV" in six_f:
        sc, st = six_f["SRV"]["coef"], six_f["SRV"]["t"]
        srv_note = (f"SRV coeff={sc:.4f} (t={st:.3f}) — "
                    + ("POSITIVE ✓ confirms ST reversal premium captured" if sc > 0 else
                       "NEGATIVE ✗ implementation issue or factor mismatch"))

    wf_table = "\n".join(
        f"| {int(r['year'])} | {int(r['n'])} | {_f(r['sharpe'],'+.3f')} | "
        f"{_f(r['monthly_ret_pct'],'+.4f')}%/wk | {_f(r['maxdd_pct'],'.1f')}% |"
        for _, r in wf_df.iterrows()
    )
    wf_table += f"\n| **% positive** | — | **{wf_pos:.0f}%** | — | — |"
    wf_table += f"\n| **Median Sharpe** | — | **{_f(wf_med,'.3f')}** | — | — |"

    crash_table = "\n".join(
        f"| {r['period']} | {_f(r['sharpe'],'+.3f')} | "
        f"{_f(r['maxdd_pct'],'.1f')}% | {_f(r['cum_ret_pct'],'+.2f')}% | "
        f"{_f(r['hit_pct'],'.1f')}% |"
        for _, r in crash_df.iterrows()
    )

    ff_table = ""
    if six_f:
        ff_table = "\n".join(
            f"| {fn} | {six_f[fn]['coef']:.4f} | {six_f[fn]['t']:.3f} |"
            for fn in ["alpha_m", "MKT", "SMB", "HML", "MOM", "SRV", "LRV"]
            if fn in six_f
        )
        ff_table += f"\nR² = {six_f['r2']:.3f}"

    gate_r_rows = "\n".join(
        f"| {gk} | {rv[1]} | {_f(rv[0],'.3f')} | {rv[2]} | "
        f"{gates['propfirm'].get(gk, ('','',''))[2]} |"
        for gk, rv in gates["research"].items()
    )
    gate_p_only = "\n".join(
        f"| {gk} | {pv[1]} | {_f(pv[0],'.3f')} | — | {pv[2]} |"
        for gk, pv in gates["propfirm"].items() if gk not in gates["research"]
    )

    attr_table = "\n".join(
        f"| {r['sector']} | {int(r['n_long'])} | {int(r['n_short'])} | "
        f"{_f(r['net_pnl_pct'],'+.3f')}% | {_f(r['wr_long'],'.1f')}% | "
        f"{_f(r['wr_short'],'.1f')}% |"
        for _, r in attr_df.iterrows()
    )

    md = f"""# Result Summary: Cross-Sectional Sector Reversal
*Generated: {today_str}*

## 1. Headline verdict
> Two-tier: **RESEARCH_PASS: {rv_str}** | **PROPFIRM_PASS: {pv_str}**
> Best variant: **{best_label}**

{srv_note}

## 2. Data
- Period: {period_start} → {period_end}
- Sectors used: {', '.join(SECTORS)} (XLRE from 2015-10, XLC from 2018-06)
- Weekly observations: {len(port)}
- n_tests: {N_TESTS_START} → {N_TESTS_END}

## 3. 4-variant comparison

| Metric | V1 (pure) | V2 (filtered) | V3 (VT) | V4 (filter+VT) |
|--------|-----------|---------------|---------|----------------|
| Sharpe HAC | {vv('V1','sharpe')} | {vv('V2','sharpe')} | {vv('V3','sharpe')} | {vv('V4','sharpe')} |
| Ann return (%) | {vv('V1','ann_ret','.2f')} | {vv('V2','ann_ret','.2f')} | {vv('V3','ann_ret','.2f')} | {vv('V4','ann_ret','.2f')} |
| Ann vol (%) | {vv('V1','ann_vol','.2f')} | {vv('V2','ann_vol','.2f')} | {vv('V3','ann_vol','.2f')} | {vv('V4','ann_vol','.2f')} |
| MaxDD (%) | {vv('V1','maxdd','.2f')} | {vv('V2','maxdd','.2f')} | {vv('V3','maxdd','.2f')} | {vv('V4','maxdd','.2f')} |
| Worst week (%) | {vv('V1','worst_week','.2f')} | {vv('V2','worst_week','.2f')} | {vv('V3','worst_week','.2f')} | {vv('V4','worst_week','.2f')} |
| Best week (%) | {vv('V1','best_week','.2f')} | {vv('V2','best_week','.2f')} | {vv('V3','best_week','.2f')} | {vv('V4','best_week','.2f')} |
| Profit factor | {vv('V1','profit_factor')} | {vv('V2','profit_factor')} | {vv('V3','profit_factor')} | {vv('V4','profit_factor')} |
| Hit rate (%) | {vv('V1','hit_rate','.1f')} | {vv('V2','hit_rate','.1f')} | {vv('V3','hit_rate','.1f')} | {vv('V4','hit_rate','.1f')} |
| Ann cost drag (%) | {vv('V1','annual_cost_drag','.2f')} | {vv('V2','annual_cost_drag','.2f')} | {vv('V3','annual_cost_drag','.2f')} | {vv('V4','annual_cost_drag','.2f')} |

## 4. 6-factor decomposition — {best_label}

| Factor | Coefficient | t_HAC |
|--------|-------------|-------|
{ff_table}

> **SRV loading**: {srv_note if srv_note else 'see above'}

## 5. Walk-forward by year — {best_label}

| Year | N weeks | Sharpe | Mean ret/wk | MaxDD |
|------|---------|--------|-------------|-------|
{wf_table}

## 6. Crash period analysis — {best_label}

| Period | Sharpe | MaxDD | Cum ret | Hit rate |
|--------|--------|-------|---------|----------|
{crash_table}

## 7. Correlation to existing book

| Asset | Correlation |
|-------|-------------|
{chr(10).join(f'| {bk} | {_f(c,".3f")} |' for bk,c in corrs.items())}

## 8. Two-tier gate decision — {best_label}

| Gate | Threshold | Value | RESEARCH | PROPFIRM |
|------|-----------|-------|----------|----------|
{gate_r_rows}
{gate_p_only}

- Research: {gates['r_pass']}/{gates['r_total']} gates passed
- Propfirm: {gates['p_pass']}/{gates['p_total']} gates passed

**RESEARCH_PASS: {rv_str}  |  PROPFIRM_PASS: {pv_str}**

## 9. Sector attribution — {best_label}

| Sector | #Long | #Short | Net P&L | WR Long | WR Short |
|--------|-------|--------|---------|---------|----------|
{attr_table}

## 10. n_tests
- Start: {N_TESTS_START}
- V1–V4: +4
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
    print("Cross-Sectional Sector Reversal — Jegadeesh (1990) / Lehmann (1990)")
    print(sep)

    # ── 1. Data ─────────────────────────────────────────────────────────
    log.info("Fetching prices ...")
    closes = fetch_all()
    rf     = fetch_risk_free()
    ff_monthly = fetch_ff_factors()

    # Daily close dataframe
    all_tickers = list(closes.keys())
    daily_close = pd.concat(closes.values(), axis=1).sort_index()
    daily_close = daily_close.loc[DATA_START:TEST_END]

    # Daily excess returns
    daily_ret = daily_close.pct_change()
    rf_daily  = rf.reindex(daily_ret.index, method="ffill").fillna(0.0)
    daily_exc = daily_ret.subtract(rf_daily, axis=0)

    # Weekly closes (Friday)
    weekly_close = daily_close.resample("W-FRI").last()
    weekly_ret   = weekly_close.pct_change()

    # Weekly excess returns
    rf_weekly_s = (1 + rf).resample("W-FRI").prod() - 1
    rf_weekly   = rf_weekly_s.reindex(weekly_ret.index, method="ffill").fillna(0.0)

    sector_weekly_exc = pd.DataFrame()
    for s in SECTORS:
        if s in weekly_ret.columns:
            sector_weekly_exc[s] = weekly_ret[s] - rf_weekly

    bench_weekly = {}
    for bk in BENCHMARKS:
        if bk in weekly_ret.columns:
            bench_weekly[bk] = weekly_ret[bk] - rf_weekly

    # Equal-weight sector portfolio (weekly)
    ew_weekly = sector_weekly_exc.mean(axis=1)

    log.info("Data period: %s → %s  (%d weekly rows)",
             str(daily_close.index[0].date()), str(daily_close.index[-1].date()),
             len(weekly_ret))

    # ── 2. Run 4 variants ────────────────────────────────────────────────
    log.info("Running 4 variants ...")
    variants: dict = {}
    for label, filt, vt in [
        ("V1", False, None),
        ("V2", True,  None),
        ("V3", False, VT_TARGET),
        ("V4", True,  VT_TARGET),
    ]:
        variants[label] = simulate_variant(
            sector_weekly_exc,
            daily_exc[SECTORS],
            label,
            filter_v2=filt,
            vt_target=vt,
        )

    # ── 3. Sanity check ──────────────────────────────────────────────────
    best_sh = max(v.get("sharpe", -99) for v in variants.values() if v)
    if best_sh > 2.0:
        print(f"\n*** SUSPICIOUS: Best Sharpe = {best_sh:.3f} > 2.0 ***")
        print("    Checking: (a) signal shift(1), (b) no lookahead in VT, (c) costs applied")
        print("    Review signal logic — proceeding but flag this result.")

    # ── 4. Output ────────────────────────────────────────────────────────
    print_and_save(variants, bench_weekly, ew_weekly, ff_monthly, rf_weekly)


if __name__ == "__main__":
    main()
