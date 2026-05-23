"""
Forex/research/active/strategy_e_fix_flow/stylized_facts.py
=============================================================
WMR Fix W-shape (H1) and EOM USD flow (H2) — stylized facts pipeline.
TDD canary: load_pair_data('EURUSD', [2016]).
Main run requires 60/60 parquets in CACHE_DIR.
"""
from __future__ import annotations

import json
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandas_market_calendars as pmc
import statsmodels.api as sm

warnings.filterwarnings("ignore")

REPO_ROOT  = Path(__file__).resolve().parents[4]
CACHE_DIR  = REPO_ROOT / "Forex" / "data" / "cache" / "dukascopy_m5"
OUTPUT_DIR = Path(__file__).resolve().parent
PLOTS_DIR  = OUTPUT_DIR / "plots"

LONDON = ZoneInfo("Europe/London")

_lse_cal: object | None = None


def _get_lse_cal():
    global _lse_cal
    if _lse_cal is None:
        _lse_cal = pmc.get_calendar("LSE")
    return _lse_cal


# ── data loading ──────────────────────────────────────────────────────────────

def load_pair_data(pair: str, years: list[int]) -> pd.DataFrame:
    """Load and concatenate cached M5 parquets. Returns UTC-indexed OHLC."""
    frames = []
    for year in sorted(years):
        pq = CACHE_DIR / f"{pair}_{year}_M5.parquet"
        if pq.exists():
            frames.append(pd.read_parquet(pq))
    if not frames:
        raise FileNotFoundError(f"No cached M5 data for {pair} years={years}")
    df = pd.concat(frames).sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    elif str(df.index.tz) != "UTC":
        df.index = df.index.tz_convert("UTC")
    return df


# ── fix window ────────────────────────────────────────────────────────────────

def compute_fix_window_utc(d: date) -> tuple[datetime, datetime]:
    """15:57:30–16:02:30 London → UTC. Handles BST (summer = UTC+1)."""
    utc = timezone.utc
    fix_start = datetime(d.year, d.month, d.day, 15, 57, 30, tzinfo=LONDON)
    fix_end   = datetime(d.year, d.month, d.day, 16,  2, 30, tzinfo=LONDON)
    return fix_start.astimezone(utc), fix_end.astimezone(utc)


def is_london_trading_day(d: date) -> bool:
    """True if d is an LSE trading day (excludes weekends and UK holidays)."""
    cal = _get_lse_cal()
    ts = pd.Timestamp(d)
    return len(cal.schedule(start_date=ts, end_date=ts)) > 0


# ── returns around fix ────────────────────────────────────────────────────────

def compute_returns_relative_to_fix(
    df: pd.DataFrame,
    fix_time_utc: datetime,
    window_minutes_before: int = 180,
    window_minutes_after: int = 60,
) -> pd.Series:
    """
    Log price trajectory vs fix price. Index = integer minutes from fix
    (−window_before … 0 … +window_after). Length = 241.
    M5 close forward-filled to 1-minute resolution.
    """
    t0    = fix_time_utc.replace(second=0, microsecond=0)
    start = t0 - timedelta(minutes=window_minutes_before)
    end   = t0 + timedelta(minutes=window_minutes_after)
    idx   = range(-window_minutes_before, window_minutes_after + 1)

    # grab a bit extra so ffill reaches 'start'
    chunk = df["close"].loc[
        start - timedelta(minutes=10) : end + timedelta(minutes=5)
    ]
    if chunk.empty:
        return pd.Series(np.nan, index=idx)

    # upsample M5 → 1min via forward-fill
    minute_prices = chunk.resample("1min").ffill()
    target_idx    = pd.date_range(start=start, end=end, freq="1min", tz="UTC")
    minute_prices = minute_prices.reindex(target_idx, method="ffill")

    # reference price at t0 (index position window_minutes_before)
    ref = minute_prices.iloc[window_minutes_before]
    if pd.isna(ref) or ref <= 0:
        return pd.Series(np.nan, index=idx)

    log_ret       = np.log(minute_prices / ref)
    log_ret.index = idx
    return log_ret


def build_returns_panel(df: pd.DataFrame, pair: str) -> pd.DataFrame:
    """
    DataFrame shape: (n_trading_days, 241).
    Rows = London trading days; columns = minute offsets −180..+60.
    """
    all_days = sorted({ts.date() for ts in df.index.normalize().unique()})

    cal      = _get_lse_cal()
    schedule = cal.schedule(
        start_date=pd.Timestamp(all_days[0]),
        end_date=pd.Timestamp(all_days[-1]),
    )
    lse_days = {ts.date() for ts in schedule.index}

    rows: dict = {}
    for d in all_days:
        if d not in lse_days:
            continue
        fix_start, _ = compute_fix_window_utc(d)
        series = compute_returns_relative_to_fix(df, fix_start)
        if not series.isna().all():
            rows[d] = series.values

    if not rows:
        return pd.DataFrame()

    cols = list(range(-180, 61))
    return pd.DataFrame.from_dict(rows, orient="index", columns=cols)


# ── aggregate stats ───────────────────────────────────────────────────────────

def _t_hac(s: pd.Series, maxlags: int = 6) -> float:
    """Newey-West HAC t-stat for H0: mean = 0."""
    vals = s.dropna().values if isinstance(s, pd.Series) else s[~np.isnan(s)]
    if len(vals) < maxlags + 2:
        return np.nan
    X   = np.ones((len(vals), 1))
    res = sm.OLS(vals, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    return float(res.tvalues[0])


def aggregate_w_shape(returns_panel: pd.DataFrame) -> pd.DataFrame:
    """
    Per-minute-offset statistics across trading days.
    Returns DataFrame (241 rows) with: mean, std, n, t_hac, ci95_low, ci95_high.
    """
    data    = returns_panel.values.astype(float)  # (n_days, 241)
    n_days, n_cols = data.shape

    means  = np.nanmean(data, axis=0)
    stds   = np.nanstd(data, axis=0)
    ns     = (~np.isnan(data)).sum(axis=0)
    t_hacs = np.array([
        _t_hac(returns_panel.iloc[:, j]) for j in range(n_cols)
    ])

    # vectorised 1000-sample block bootstrap for 95% CI on mean
    np.random.seed(42)
    n_boot   = 1000
    boot_idx = np.random.randint(0, n_days, size=(n_boot, n_days))
    boot_means = np.zeros((n_boot, n_cols))
    for i in range(n_boot):
        boot_means[i] = np.nanmean(data[boot_idx[i]], axis=0)

    ci_low  = np.percentile(boot_means, 2.5,  axis=0)
    ci_high = np.percentile(boot_means, 97.5, axis=0)

    return pd.DataFrame(
        {"mean": means, "std": stds, "n": ns, "t_hac": t_hacs,
         "ci95_low": ci_low, "ci95_high": ci_high},
        index=returns_panel.columns,
    )


# ── H1 — W-shape fade ─────────────────────────────────────────────────────────

def test_h1_w_shape(returns_panel: pd.DataFrame) -> dict:
    """
    Contrarian fade: sign of 30-min pre-fix drift → short/long at fix open.
    Trade return = −sign(pre_drift) × (return at t=+60).
    Gate: t_HAC > 2.0.
    """
    pre_drift   = returns_panel.loc[:, 0]  - returns_panel.loc[:, -30]
    post_return = returns_panel.loc[:, 60] - returns_panel.loc[:, 0]
    fade_return = -np.sign(pre_drift) * post_return

    t    = _t_hac(fade_return)
    n    = int(fade_return.notna().sum())
    mean = float(fade_return.mean())

    return {"mean": mean, "t_hac": float(t), "n": n,
            "verdict": "PASS" if t > 2.0 else "FAIL"}


# ── H2 — EOM USD flow ─────────────────────────────────────────────────────────

def detect_eom_days(dates) -> pd.DatetimeIndex:
    """Last LSE trading day of each calendar month in dates."""
    cal    = _get_lse_cal()
    result = []
    for m in pd.DatetimeIndex(dates).to_period("M").unique():
        m_start = m.to_timestamp("D", how="start")
        m_end   = m.to_timestamp("D", how="end")
        sched   = cal.schedule(start_date=pd.Timestamp(m_start),
                               end_date=pd.Timestamp(m_end))
        if len(sched) > 0:
            result.append(sched.index[-1].date())
    return pd.DatetimeIndex(result)


def load_spx_msci_mtd(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """
    SPX vs ACWX MTD return difference → EOM USD-selling signal.
    Signal = True when SPX MTD − ACWX MTD > 2% on last London business day.
    Requires yfinance and external network access (not available in routine mode).
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("yfinance required for H2: pip install yfinance")

    start = pd.Timestamp(min(dates)) - timedelta(days=35)
    end   = pd.Timestamp(max(dates)) + timedelta(days=5)

    spx  = yf.download("^GSPC", start=start, end=end, progress=False)["Close"].squeeze()
    acwx = yf.download("ACWX",  start=start, end=end, progress=False)["Close"].squeeze()

    rows = []
    for d in dates:
        m_start      = pd.Timestamp(d.replace(day=1))
        d_ts         = pd.Timestamp(d)
        spx_s        = spx.loc[:m_start].iloc[-1] if len(spx.loc[:m_start]) else np.nan
        spx_e        = spx.loc[:d_ts].iloc[-1]    if len(spx.loc[:d_ts])    else np.nan
        acwx_s       = acwx.loc[:m_start].iloc[-1] if len(acwx.loc[:m_start]) else np.nan
        acwx_e       = acwx.loc[:d_ts].iloc[-1]    if len(acwx.loc[:d_ts])    else np.nan
        spx_mtd      = np.log(spx_e / spx_s)  if (spx_s  and not pd.isna(spx_s))  else np.nan
        acwx_mtd     = np.log(acwx_e / acwx_s) if (acwx_s and not pd.isna(acwx_s)) else np.nan
        signal       = bool((spx_mtd - acwx_mtd) > 0.02) if not (pd.isna(spx_mtd) or pd.isna(acwx_mtd)) else False
        rows.append({"date": d, "spx_mtd": spx_mtd, "acwx_mtd": acwx_mtd, "signal": signal})

    return pd.DataFrame(rows).set_index("date")


def test_h2_eom_usd_flow(returns_panel: pd.DataFrame,
                          eom_signal: pd.DataFrame) -> dict:
    """
    On EOM signal days: long pair (short USD) from fix to +90 min.
    Returns from returns_panel are already relative to fix (t=0).
    Gate: t_HAC > 1.5 AND n ≥ 80.
    """
    signal_days = eom_signal[eom_signal["signal"]].index
    panel_days  = pd.DatetimeIndex(returns_panel.index)
    overlap     = [d for d in signal_days if d in panel_days]

    if not overlap:
        return {"mean": np.nan, "t_hac": np.nan, "n": 0, "verdict": "FAIL"}

    sub   = returns_panel.loc[overlap]
    # return at t=+90 relative to fix (panel col 90, already vs fix=0)
    col   = 90 if 90 in sub.columns else sub.columns[-1]
    trade = sub[col].dropna()

    t    = _t_hac(trade)
    n    = int(trade.notna().sum())
    mean = float(trade.mean())

    return {"mean": mean, "t_hac": float(t), "n": n,
            "verdict": "PASS" if (t > 1.5 and n >= 80) else "FAIL"}


def test_h3_independence(h1_series: pd.Series, h2_series: pd.Series) -> float:
    """Pearson correlation between H1 and H2 daily trade returns."""
    aligned = pd.concat([h1_series, h2_series], axis=1).dropna()
    if len(aligned) < 5:
        return np.nan
    return float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))


# ── plots ─────────────────────────────────────────────────────────────────────

def plot_w_shape(agg: pd.DataFrame, pair: str, label: str = "") -> Path:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 5))
    x = agg.index.astype(int)
    ax.plot(x, agg["mean"] * 100, "b-", lw=1.5, label="Mean log-return (%)")
    ax.fill_between(x, agg["ci95_low"] * 100, agg["ci95_high"] * 100,
                    alpha=0.2, color="blue", label="95% CI (bootstrap)")
    ax.axvline(0, color="red",   lw=1.2, linestyle="--", label="Fix open (t=0)")
    ax.axhline(0, color="black", lw=0.5, linestyle="-")
    ax.set_xlabel("Minutes relative to fix open")
    ax.set_ylabel("Log-return vs fix (%)")
    ax.set_title(f"{pair} — W-shape around WMR Fix  {label}")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    out = PLOTS_DIR / f"w_shape_{pair}_{label}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF"]
    years = list(range(2016, 2026))

    all_results: dict = {}

    for pair in pairs:
        try:
            df = load_pair_data(pair, years)
        except FileNotFoundError:
            print(f"  SKIP {pair}: no cached data")
            continue

        print(f"  {pair}: {len(df):,} rows …", flush=True)
        panel = build_returns_panel(df, pair)
        agg   = aggregate_w_shape(panel)

        plot_w_shape(agg, pair, label=f"{years[0]}-{years[-1]}")

        h1 = test_h1_w_shape(panel)

        eom_days   = detect_eom_days(pd.DatetimeIndex(panel.index))
        eom_signal = load_spx_msci_mtd(eom_days)
        h2         = test_h2_eom_usd_flow(panel, eom_signal)

        pre_drift  = panel.loc[:, 0]  - panel.loc[:, -30]
        post_ret   = panel.loc[:, 60] - panel.loc[:, 0]
        h1_series  = pd.Series(-np.sign(pre_drift) * post_ret, index=panel.index)
        h2_series  = panel[90].dropna() if 90 in panel.columns else pd.Series(dtype=float)
        h3_corr    = test_h3_independence(h1_series, h2_series)

        all_results[pair] = {"h1": h1, "h2": h2, "h3_corr": float(h3_corr)}
        print(f"    H1 {h1['verdict']} t={h1['t_hac']:.2f} | "
              f"H2 {h2['verdict']} t={h2['t_hac']:.2f} | "
              f"H3 corr={h3_corr:.3f}")

    results_path = OUTPUT_DIR / "results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    report = ["# Strategy E — Stylized Facts Report\n"]
    for pair, res in all_results.items():
        report.append(f"## {pair}")
        report.append(f"- H1 (W-shape): {res['h1']['verdict']}  t={res['h1']['t_hac']:.2f}  n={res['h1']['n']}")
        report.append(f"- H2 (EOM flow): {res['h2']['verdict']}  t={res['h2']['t_hac']:.2f}  n={res['h2']['n']}")
        report.append(f"- H3 corr: {res['h3_corr']:.3f}\n")
    with open(OUTPUT_DIR / "report.md", "w") as f:
        f.write("\n".join(report))

    print(f"\nResults → {results_path}")


if __name__ == "__main__":
    main()
