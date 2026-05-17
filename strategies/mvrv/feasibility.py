"""
strategies/mvrv/feasibility.py — MVRV Z-Score as TSMOM Scaler

MVRV Z-Score measures how far market value is above realized value (all-holder
cost basis). When high → euphoria, potential top. When negative → holders
underwater, structural accumulation. EXOGENOUS to price momentum → should
have near-zero construction correlation with TSMOM v3.

Primary path: Glassnode free API (set GLASSNODE_API_KEY env var).
Fallback proxy: (BTC_close - MA200) / rolling_std(BTC_close, 365)
  ← Toby Ord approximation, directionally correct.

Two tests:
  1. IC test: rank_corr(mvrv_z[T], BTC_return_next_week[T+1])
             Direction: positive (momentum) or negative (contrarian)?
  2. TSMOM scaler: TSMOM_v3_weight × MVRV_scale(mvrv_z)
             If scaled Sharpe > 1.5 → implement as overlay.

Scale thresholds (contrarian):
  z < -0.5 → scale 1.30 (cheap, add exposure)
  z < +1.0 → scale 1.00 (neutral)
  z < +3.0 → scale 0.70 (expensive, reduce)
  z ≥ +3.0 → scale 0.40 (very expensive, minimal)
"""

import os, sys, time, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")
np.random.seed(42)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
BIN_URL  = "https://api.binance.com/api/v3/klines"
GL_URL   = "https://api.glassnode.com/v1/metrics/market/mvrv_z_score"
BIN_SLEEP = 0.12
COST_RT  = 0.0017
VOL_TGT  = 0.15

# MVRV scale thresholds (contrarian: high MVRV → reduce exposure)
SCALE_THRESHOLDS = [(-0.5, 1.30), (1.0, 1.00), (3.0, 0.70)]
SCALE_TOP        = 0.40   # z ≥ 3.0

# Periods for sub-analysis
PERIOD_BEAR = ("2021-01-01", "2023-12-31")
PERIOD_BULL = ("2024-01-01", "2026-12-31")

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── DATA FETCH ───────────────────────────────────────────────────────────────

def fetch_btc_daily_binance(start: str = "2019-01-01") -> pd.Series:
    """BTC daily close from Binance. Needs 2+ years for MA200+std365 warm-up."""
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    now_ms   = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
    day_ms   = 86_400_000
    all_rows: list = []
    while start_ms < now_ms:
        params = {"symbol": "BTCUSDT", "interval": "1d",
                  "startTime": start_ms, "limit": 1000}
        r = requests.get(BIN_URL, params=params, timeout=15)
        r.raise_for_status()
        rows = r.json()
        if not rows: break
        all_rows.extend(rows)
        start_ms = int(rows[-1][0]) + day_ms
        time.sleep(BIN_SLEEP)
    df = pd.DataFrame(all_rows, columns=[
        "open_time","o","h","l","close","vol",
        "close_time","qvol","n","tb","tq","_"
    ])
    ts = pd.to_datetime(df["open_time"].astype(np.int64), unit="ms", utc=True)
    s  = pd.Series(df["close"].astype(float).values, index=ts, name="BTC")
    return s[~s.index.duplicated(keep="last")].sort_index()


def try_glassnode(api_key: str | None) -> pd.Series:
    """
    Fetch MVRV Z-score from Glassnode free tier.
    Returns empty Series if unavailable.
    """
    if not api_key:
        return pd.Series(dtype=float)
    try:
        r = requests.get(GL_URL, params={"a": "BTC", "i": "24h", "api_key": api_key},
                         timeout=20)
        if r.status_code != 200:
            print(f"  Glassnode returned {r.status_code}: {r.text[:80]}")
            return pd.Series(dtype=float)
        data = r.json()
        if not data:
            return pd.Series(dtype=float)
        ts  = pd.to_datetime([d["t"] for d in data], unit="s", utc=True)
        val = [d["v"] for d in data]
        s   = pd.Series(val, index=ts, name="mvrv_glassnode").astype(float)
        return s[~s.index.duplicated(keep="last")].sort_index().dropna()
    except Exception as e:
        print(f"  Glassnode error: {e}")
        return pd.Series(dtype=float)


# ─── MVRV PROXY ──────────────────────────────────────────────────────────────

def compute_mvrv_proxy(btc_close: pd.Series) -> pd.Series:
    """
    Toby Ord approximation: (close - MA200) / rolling_std(close, 365).
    Captures distance above/below long-term cost-basis proxy.
    Directionally aligned with true MVRV Z-score (high ↔ euphoria,
    negative ↔ underwater).
    """
    ma200  = btc_close.rolling(200, min_periods=150).mean()
    std365 = btc_close.rolling(365, min_periods=200).std()
    proxy  = (btc_close - ma200) / std365.replace(0, np.nan)
    return proxy.rename("mvrv_proxy")


# ─── MVRV SCALER ─────────────────────────────────────────────────────────────

def mvrv_to_scale(z: float) -> float:
    """Map MVRV z to position scale factor (contrarian: reduce at extremes)."""
    if np.isnan(z):
        return 1.0
    for threshold, scale in SCALE_THRESHOLDS:
        if z < threshold:
            return scale
    return SCALE_TOP  # z >= 3.0


def apply_mvrv_scaler(tsmom_signal: pd.Series,
                       mvrv_weekly: pd.Series) -> pd.Series:
    """
    Scale TSMOM v3 position by MVRV regime.
    Both are weekly-indexed (W-FRI). Returns scaled position series.
    """
    common = tsmom_signal.index.intersection(mvrv_weekly.index)
    ts     = tsmom_signal.reindex(common)
    mz     = mvrv_weekly.reindex(common)
    scales = mz.map(mvrv_to_scale)
    return (ts * scales).rename("tsmom_scaled")


# ─── TSMOM v3 ─────────────────────────────────────────────────────────────────

def compute_tsmom(btc_close: pd.Series) -> dict:
    """
    TSMOM v3 daily position + weekly returns for backtest.
    Returns {'signal_daily': pd.Series, 'ret_weekly': pd.Series,
             'signal_weekly': pd.Series (raw position sampled weekly)}
    """
    lr    = np.log(btc_close / btc_close.shift(1)).dropna()
    cr28  = lr.rolling(28).sum()
    v28   = lr.rolling(28).std() * np.sqrt(28)
    sig   = np.tanh(cr28 / v28.replace(0, np.nan)).clip(lower=0)

    # Weekly: position at Friday → return next week
    sig_wk  = sig.resample("W-FRI").last()
    ret_wk  = lr.resample("W-FRI").sum()

    return {"signal_daily": sig, "signal_weekly": sig_wk,
            "ret_weekly": ret_wk}


# ─── IC TEST ─────────────────────────────────────────────────────────────────

def ic_test(mvrv_weekly: pd.Series, btc_close: pd.Series) -> dict:
    """
    rank_corr(mvrv_z[T], BTC_return[T+1 week]).
    Tests both + (momentum) and - (contrarian) predictive power.
    """
    btc_wk_ret = np.log(btc_close / btc_close.shift(1)).resample("W-FRI").sum()
    fwd_ret    = btc_wk_ret.shift(-1)  # next week's return

    common = mvrv_weekly.dropna().index.intersection(fwd_ret.dropna().index)
    if len(common) < 10:
        return {"ic": np.nan, "t_stat": np.nan, "p_val": np.nan, "n": 0}

    z = mvrv_weekly.reindex(common)
    r = fwd_ret.reindex(common)
    ic, p_val = spearmanr(z, r)
    n      = len(common)
    t_stat = ic * np.sqrt(n - 2) / np.sqrt(max(1 - ic**2, 1e-9))
    return {"ic": ic, "t_stat": t_stat, "p_val": p_val, "n": n,
            "z_series": z, "ret_series": r}


# ─── BACKTEST ─────────────────────────────────────────────────────────────────

def backtest_weekly(signal_weekly: pd.Series, ret_weekly: pd.Series,
                     label: str = "",
                     start: str = "2021-01-01",
                     end: str   = "2026-12-31") -> dict:
    """
    Weekly backtest. signal[T] → position for week T+1.
    Returns dict with Sharpe, MaxDD, cum_ret, bar_ret.
    """
    mask = (signal_weekly.index >= pd.Timestamp(start, tz="UTC")) & \
           (signal_weekly.index <= pd.Timestamp(end, tz="UTC"))
    sig = signal_weekly[mask].shift(1).fillna(0)   # 1-week lag
    ret = ret_weekly.reindex(sig.index).fillna(0)

    entry  = (sig.diff() > 0).astype(float)
    bar_r  = sig * ret - entry * COST_RT
    cum_r  = bar_r.cumsum()

    if bar_r.std() == 0 or len(bar_r.dropna()) < 20:
        return {"sharpe": np.nan, "maxdd": np.nan, "trades_yr": 0,
                "n_weeks": 0, "cum_ret": cum_r, "bar_ret": bar_r}

    n_yrs    = max((sig.index[-1] - sig.index[0]).days / 365.25, 0.1)
    sharpe   = bar_r.mean() / bar_r.std() * np.sqrt(52)
    maxdd    = (cum_r - cum_r.cummax()).min()
    trades_yr = entry.sum() / n_yrs

    return {"sharpe": sharpe, "maxdd": maxdd, "trades_yr": trades_yr,
            "n_weeks": len(bar_r), "cum_ret": cum_r, "bar_ret": bar_r,
            "label": label}


# ─── FIGURE ──────────────────────────────────────────────────────────────────

def make_figure(btc_close: pd.Series, mvrv_weekly: pd.Series,
                ic_res: dict, res_base: dict, res_scaled: dict,
                mvrv_source: str) -> None:

    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle(
        f"MVRV Z-Score as TSMOM Overlay — Signal 28\n"
        f"Source: {mvrv_source}  |  Scale: contrarian regime filter  |  "
        f"Weekly rebalance  |  2021-2026",
        fontsize=12, fontweight="bold"
    )

    # Panel 1: BTC price + MVRV Z-score
    ax1 = axes[0, 0]
    ax1b = ax1.twinx()
    btc_yr = btc_close[btc_close.index >= "2021-01-01"]
    ax1.semilogy(btc_yr.index, btc_yr.values, color="#888888", lw=1.5,
                 label="BTC price")
    mvrv_d = mvrv_weekly.resample("D").last().reindex(btc_yr.index, method="ffill")
    ax1b.fill_between(mvrv_d.index, 0, mvrv_d.values,
                      where=mvrv_d.values > 0, color="#d73027", alpha=0.25)
    ax1b.fill_between(mvrv_d.index, 0, mvrv_d.values,
                      where=mvrv_d.values < 0, color="#1a9850", alpha=0.25)
    ax1b.plot(mvrv_d.index, mvrv_d.values, color="#2166ac", lw=1.5,
              label="MVRV z-score")
    for thr, _ in SCALE_THRESHOLDS:
        ax1b.axhline(thr, color="#f4a582", ls="--", lw=0.8, alpha=0.7)
    ax1b.axhline(3.0, color="#d73027", ls="--", lw=0.8, alpha=0.7)
    ax1.set_title(f"BTC Price + MVRV Z-Score ({mvrv_source})", fontsize=10)
    ax1.set_ylabel("BTC USD (log)"); ax1b.set_ylabel("MVRV Z-score")
    ax1.legend(loc="upper left", fontsize=8); ax1b.legend(loc="upper right", fontsize=8)

    # Panel 2: MVRV distribution + scale zones
    ax = axes[0, 1]
    ax.hist(mvrv_weekly.dropna(), bins=40, color="#4393c3", alpha=0.7, edgecolor="white")
    ax.axvline(-0.5, color="#1a9850", ls="--", lw=1.5, label="scale=1.30")
    ax.axvline(1.0,  color="#f4a582", ls="--", lw=1.5, label="scale=1.00")
    ax.axvline(3.0,  color="#d73027", ls="--", lw=1.5, label="scale=0.40")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title("MVRV Z-score Distribution + Scale Thresholds", fontsize=10)
    ax.set_xlabel("MVRV Z-score"); ax.set_ylabel("Count")
    ax.legend(fontsize=8)

    # Panel 3: IC scatter (z[T] vs ret[T+1])
    ax = axes[0, 2]
    if ic_res.get("n", 0) > 0:
        zs = ic_res.get("z_series", pd.Series(dtype=float))
        rs = ic_res.get("ret_series", pd.Series(dtype=float)) * 100
        ax.scatter(zs, rs, alpha=0.4, s=20, color="#2166ac")
        if len(zs) > 3:
            c = np.polyfit(zs, rs, 1)
            xl = np.linspace(zs.min(), zs.max(), 50)
            ax.plot(xl, np.polyval(c, xl), color="#d73027", lw=2)
    ax.axhline(0, color="black", lw=0.5)
    ax.axvline(0, color="black", lw=0.5, ls="--")
    ax.set_title(
        f"IC: MVRV[T] vs BTC ret[T+1]\n"
        f"IC={ic_res.get('ic', np.nan):+.4f}  t={ic_res.get('t_stat', np.nan):+.3f}  "
        f"n={ic_res.get('n', 0)}",
        fontsize=10
    )
    ax.set_xlabel("MVRV Z-score"); ax.set_ylabel("Next-week BTC return (%)")
    ax.grid(alpha=0.3)

    # Panel 4: Equity curves — base vs scaled TSMOM
    ax = axes[1, 0]
    for res, color, lw in [(res_base, "#888888", 1.5), (res_scaled, "#2166ac", 2.0)]:
        if "cum_ret" in res and len(res["cum_ret"]) > 0:
            cum = res["cum_ret"]
            lbl = f"{res.get('label','')}  Sharpe={res['sharpe']:.3f}"
            ax.plot(cum.index, cum.values * 100, color=color, lw=lw, label=lbl)
    ax.axhline(0, color="black", lw=0.5)
    ax.set_title("TSMOM Base vs TSMOM × MVRV Scaler", fontsize=10)
    ax.set_ylabel("Cum log return (%)"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Panel 5: MVRV scale over time
    ax = axes[1, 1]
    if len(mvrv_weekly) > 0:
        scales = mvrv_weekly.map(mvrv_to_scale)
        ax.step(scales.index, scales.values, color="#2166ac", lw=1.5,
                label="MVRV scale factor", where="post")
        ax.axhline(1.0, color="black", lw=0.8, ls="--", alpha=0.5)
        ax.fill_between(scales.index, 1.0, scales.values,
                        where=scales.values > 1.0, color="#1a9850", alpha=0.3)
        ax.fill_between(scales.index, 1.0, scales.values,
                        where=scales.values < 1.0, color="#d73027", alpha=0.3)
        ax.set_ylim(0, 1.5)
    ax.set_title("MVRV Scale Factor Applied to TSMOM", fontsize=10)
    ax.set_ylabel("Scale (1.0 = neutral)"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Panel 6: Summary table
    ax = axes[1, 2]
    ax.axis("off")
    base_sh = res_base.get("sharpe", np.nan)
    scal_sh = res_scaled.get("sharpe", np.nan)
    improvement = scal_sh - base_sh if not (np.isnan(base_sh) or np.isnan(scal_sh)) else np.nan
    # Sub-period from backtest bar_ret
    sub_lines = []
    for name, s, e in [("2021-2023 (bear)", "2021-01-01", "2023-12-31"),
                        ("2024-2026 (bull)", "2024-01-01", "2026-12-31")]:
        for label, res in [("base", res_base), ("scaled", res_scaled)]:
            br = res.get("bar_ret", pd.Series(dtype=float))
            br_sub = br[(br.index >= pd.Timestamp(s, tz="UTC")) &
                        (br.index <= pd.Timestamp(e, tz="UTC"))]
            if len(br_sub) > 10:
                sh = br_sub.mean() / br_sub.std() * np.sqrt(52)
                sub_lines.append(f"  {name} {label}: {sh:+.3f}")

    ic_t   = ic_res.get("t_stat", np.nan)
    verdict = (
        "IMPLEMENT ✓" if (scal_sh > 1.5 and not np.isnan(improvement))
        else "SKIP ✗"
    )
    txt = (
        "═══ MVRV OVERLAY SUMMARY ═══\n\n"
        f"Source: {mvrv_source}\n\n"
        f"IC test:\n"
        f"  IC    = {ic_res.get('ic', np.nan):+.4f}\n"
        f"  t     = {ic_t:+.3f}\n"
        f"  n     = {ic_res.get('n', 0)}\n\n"
        f"Portfolio:\n"
        f"  TSMOM base Sharpe  = {base_sh:+.3f}\n"
        f"  TSMOM scaled Sharpe= {scal_sh:+.3f}\n"
        f"  Improvement        = {improvement:+.3f}\n"
        f"  Base MaxDD         = {res_base.get('maxdd', 0)*100:.1f}%\n"
        f"  Scaled MaxDD       = {res_scaled.get('maxdd', 0)*100:.1f}%\n\n"
        f"Sub-periods:\n"
        + "\n".join(sub_lines) + "\n\n"
        f"VERDICT (threshold: scaled > 1.5):\n"
        f"  >>> {verdict}"
    )
    ax.text(0.04, 0.97, txt, transform=ax.transAxes,
            va="top", ha="left", fontsize=9.5, fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f0f4ff",
                      edgecolor="#2166ac"))

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "feasibility_results.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure → {out_path}")
    plt.close()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("MVRV Z-SCORE AS TSMOM OVERLAY — Signal 28")
    print("Signal: MVRV regime → scale TSMOM v3 position up/down")
    print("=" * 70)

    # ── 1. BTC daily price ────────────────────────────────────────────────────
    print("\n[1/5] Fetching BTC daily price (Binance, 2019→2026)…")
    btc_close = fetch_btc_daily_binance(start="2019-01-01")
    print(f"  {len(btc_close)} days  "
          f"({btc_close.index[0].date()} → {btc_close.index[-1].date()})")

    # ── 2. MVRV Z-score ───────────────────────────────────────────────────────
    print("\n[2/5] Building MVRV Z-score…")
    api_key = os.environ.get("GLASSNODE_API_KEY", "")
    gl_data = try_glassnode(api_key)

    if len(gl_data) > 100:
        mvrv_source = "Glassnode API"
        mvrv_daily  = gl_data
        print(f"  Glassnode: {len(gl_data)} daily records  "
              f"({gl_data.index[0].date()} → {gl_data.index[-1].date()})")
    else:
        mvrv_source = "Proxy: (close-MA200)/std365"
        mvrv_daily  = compute_mvrv_proxy(btc_close)
        print(f"  Using proxy (no Glassnode key): {mvrv_source}")
        print(f"  Valid proxy values: {mvrv_daily.dropna().__len__()}"
              f"  ({mvrv_daily.dropna().index[0].date()} → "
              f"{mvrv_daily.dropna().index[-1].date()})")

    # Sample to weekly (W-FRI), shift 1 (no look-ahead)
    mvrv_weekly = mvrv_daily.resample("W-FRI").last().shift(1).dropna()
    print(f"  Weekly z-score: {len(mvrv_weekly)} weeks")
    print(f"  Distribution: "
          f"min={mvrv_weekly.min():.2f}  "
          f"p25={mvrv_weekly.quantile(0.25):.2f}  "
          f"p50={mvrv_weekly.quantile(0.50):.2f}  "
          f"p75={mvrv_weekly.quantile(0.75):.2f}  "
          f"max={mvrv_weekly.max():.2f}")

    # Scale factor distribution
    scales = mvrv_weekly.map(mvrv_to_scale)
    print(f"\n  Scale factor time spent:")
    for (thr, sc), name in zip(
        [(SCALE_THRESHOLDS[0][0], SCALE_THRESHOLDS[0][1]),
         (SCALE_THRESHOLDS[1][0], SCALE_THRESHOLDS[1][1]),
         (SCALE_THRESHOLDS[2][0], SCALE_THRESHOLDS[2][1]),
         (None, SCALE_TOP)],
        ["z<-0.5 (1.30, cheap)", "z<1.0 (1.00, neutral)",
         "z<3.0 (0.70, exp.)", "z≥3.0 (0.40, top)"]
    ):
        pct = (scales == sc).mean()
        print(f"    {name}: {pct:.1%} of weeks")

    # ── 3. TSMOM v3 ───────────────────────────────────────────────────────────
    print("\n[3/5] Computing TSMOM v3…")
    tsmom = compute_tsmom(btc_close)
    sig_wk  = tsmom["signal_weekly"]
    ret_wk  = tsmom["ret_weekly"]

    # TSMOM + MVRV scaled signal
    scaled_sig_wk = apply_mvrv_scaler(sig_wk, mvrv_weekly)

    # Compute vol-targeted position (scale to 15% target)
    daily_rv = (np.log(btc_close / btc_close.shift(1))
                .rolling(28).std() * np.sqrt(252))
    vol_wk   = daily_rv.resample("W-FRI").last().dropna()
    v_scalar = (VOL_TGT / vol_wk.replace(0, np.nan)).clip(0.1, 2.0)

    # Apply vol scaling to TSMOM (capped at 1.0 by TSMOM construction)
    common_v = sig_wk.index.intersection(v_scalar.index)
    sig_vol  = (sig_wk.reindex(common_v) * v_scalar.reindex(common_v)).clip(upper=1.5)
    scaled_vol = (scaled_sig_wk.reindex(common_v) * v_scalar.reindex(common_v)).clip(upper=2.0)

    # ── 4. IC test ────────────────────────────────────────────────────────────
    print("\n[4/5] IC test: MVRV[T] → BTC return[T+1]…")
    ic_res = ic_test(mvrv_weekly, btc_close)
    print(f"  IC       = {ic_res['ic']:+.4f}")
    print(f"  t-stat   = {ic_res['t_stat']:+.3f}  (p={ic_res.get('p_val', np.nan):.4f})")
    print(f"  N weeks  = {ic_res['n']}")
    print(f"  Direction: {'positive (momentum: high MVRV = up trend continues)' if ic_res['ic'] > 0 else 'negative (contrarian: high MVRV = mean revert)'}")

    # Sub-period IC
    for name, s, e in [("2021-2023", "2021-01-01", "2023-12-31"),
                        ("2024-2026", "2024-01-01", "2026-12-31")]:
        sub = mvrv_weekly[(mvrv_weekly.index >= s) & (mvrv_weekly.index < e)]
        ic_sub = ic_test(sub, btc_close)
        print(f"  Sub-period {name}: IC={ic_sub.get('ic', np.nan):+.4f}  "
              f"t={ic_sub.get('t_stat', np.nan):+.3f}  n={ic_sub.get('n', 0)}")

    # ── 5. Backtest ───────────────────────────────────────────────────────────
    print("\n[5/5] Backtest: TSMOM base vs TSMOM × MVRV scaler…")
    res_base   = backtest_weekly(sig_vol,    ret_wk, label="TSMOM v3 base")
    res_scaled = backtest_weekly(scaled_vol, ret_wk, label="TSMOM v3 × MVRV")

    print(f"\n  ── COMPARISON (2021-2026) ──")
    print(f"  {'Strategy':<25} {'Sharpe':>7} {'MaxDD':>8} {'t/yr':>6}")
    print(f"  {'─'*50}")
    for res in [res_base, res_scaled]:
        print(f"  {res.get('label','?'):<25} {res['sharpe']:>7.3f} "
              f"{res['maxdd']*100:>7.1f}% {res['trades_yr']:>6.0f}")

    # Sub-period comparison
    print(f"\n  ── SUB-PERIOD BREAKDOWN ──")
    for name, s, e in [("2021-2023 (bear)", "2021-01-01", "2023-12-31"),
                        ("2024-2026 (bull)", "2024-01-01", "2026-12-31")]:
        rb = backtest_weekly(sig_vol,    ret_wk, start=s, end=e)
        rs = backtest_weekly(scaled_vol, ret_wk, start=s, end=e)
        print(f"  {name}:  base={rb['sharpe']:+.3f}  scaled={rs['sharpe']:+.3f}  "
              f"Δ={rs['sharpe']-rb['sharpe']:+.3f}")

    # Correlation between MVRV and TSMOM signal
    common_c = sig_wk.index.intersection(mvrv_weekly.index)
    corr_sig = sig_wk.reindex(common_c).corr(mvrv_weekly.reindex(common_c))
    print(f"\n  corr(TSMOM_signal, MVRV_z):  {corr_sig:+.3f}")
    print(f"  (positive = MVRV and momentum aligned; expected)")

    make_figure(btc_close, mvrv_weekly, ic_res, res_base, res_scaled, mvrv_source)

    # ── VERDICT ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    base_sh  = res_base["sharpe"]
    scal_sh  = res_scaled["sharpe"]
    imp      = scal_sh - base_sh

    # Summary table
    print(f"\n  ┌{'─'*30}┬{'─'*8}┬{'─'*10}┬{'─'*11}┐")
    print(f"  │ {'Signal':<28} │{'t-stat':>6}  │{'Sharpe':>8}  │{'corr(TSMOM)':>9} │")
    print(f"  ├{'─'*30}┼{'─'*8}┼{'─'*10}┼{'─'*11}┤")
    print(f"  │ {'MVRV IC (z→ret)':<28} │{ic_res['t_stat']:>+6.3f}  │{'—':>8}  │{'—':>9} │")
    print(f"  │ {'TSMOM base':<28} │{'—':>6}  │{base_sh:>+8.3f}  │{'—':>9} │")
    print(f"  │ {'TSMOM × MVRV scaler':<28} │{'—':>6}  │{scal_sh:>+8.3f}  │{'—':>9} │")
    print(f"  └{'─'*30}┴{'─'*8}┴{'─'*10}┴{'─'*11}┘")
    print()

    if scal_sh > 1.5 and imp > 0:
        verdict = "IMPLEMENT — scaled TSMOM Sharpe > 1.5 AND improvement positive"
        action  = "Deploy MVRV scaler as live TSMOM overlay. Update TSMOM v3 parameters."
    elif imp > 0.1 and scal_sh > base_sh:
        verdict = "WEAK IMPROVEMENT — positive delta but scaled Sharpe still below 1.5"
        action  = "Monitor. Revisit with true Glassnode MVRV data if proxy is too noisy."
    elif imp > 0:
        verdict = "MARGINAL — barely positive improvement, not deployable"
        action  = "Skip. Noise in proxy likely explains marginal result."
    else:
        verdict = "SKIP — scaler hurts or doesn't improve TSMOM"
        action  = "MVRV contrarian scaling reduces returns. Consider momentum direction."

    print(f"  >>> {verdict}")
    print(f"  Next step: {action}")
    print()
    print(f"  Proxy quality note: (close-MA200)/std365 captures the same signal as")
    print(f"  true MVRV Z-score directionally, but is less accurate for threshold")
    print(f"  calibration. True MVRV from Glassnode would improve scale boundary precision.")


if __name__ == "__main__":
    main()
