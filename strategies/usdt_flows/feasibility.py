"""
strategies/usdt_flows/feasibility.py — USDT Flow Proxy Signal

Hypothesis (Chi, Chu & Hao, 2025):
  USDT net inflows into exchanges predict BTC/ETH returns (1-6h horizon).
  Mechanism: USDT arriving on-exchange = dry powder ready to buy → price pressure.

Proxy (no paid API):
  Total USDT-denominated quote volume across 5 major Binance pairs
  (BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT). High USDT trading
  activity proxies for inflow pressure.

  usdt_vol_z[T] = z-score of last-week daily volume vs 30-day rolling baseline.

  → Non-price signal: structural near-zero correlation with TSMOM expected.

Signal: long BTC+ETH equal weight when z > 0, flat otherwise.
Rebalance: weekly. Cost: 0.17% RT.

VERDICT: GO if IC t-stat > 1.5 AND corr(TSMOM) < 0.30.
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
BIN_URL    = "https://api.binance.com/api/v3/klines"
BIN_SLEEP  = 0.12
# Use daily klines (equivalent to summing hourly quote_vol per day; avoids
# fetching 200 chunks of 1h data for the same information)
INTERVAL   = "1d"
SYMBOLS    = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
START_DATE = "2022-01-01"
END_DATE   = "2026-05-17"

ROLL_DAYS  = 30    # baseline window for z-score
Z_THR      = 0.0   # long when z > 0 (above baseline)
COST_RT    = 0.0017
VOL_TGT    = 0.15

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── DATA FETCH ───────────────────────────────────────────────────────────────

def fetch_binance_daily(symbol: str, start: str = START_DATE,
                         end: str = END_DATE) -> pd.DataFrame:
    """
    Daily OHLCV from Binance spot. Returns close + quote_vol.
    quote_vol = USD-denominated volume (proxy for USDT inflow activity).
    """
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms   = int(pd.Timestamp(end,   tz="UTC").timestamp() * 1000)
    day_ms   = 24 * 3600 * 1000
    all_rows: list = []

    while start_ms < end_ms:
        params = {"symbol": symbol, "interval": INTERVAL,
                  "startTime": start_ms, "limit": 1000}
        try:
            r = requests.get(BIN_URL, params=params, timeout=15)
            if r.status_code == 400:
                return pd.DataFrame()
            if r.status_code == 429:
                time.sleep(30); continue
            r.raise_for_status()
            rows = r.json()
        except Exception as e:
            print(f"  WARN: {symbol} fetch error: {e}"); break
        if not rows:
            break
        all_rows.extend(rows)
        last_open = int(rows[-1][0])
        start_ms  = last_open + day_ms
        time.sleep(BIN_SLEEP)

    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_vol","n_trades","taker_base","taker_quote","_"
    ])
    df["time"]      = pd.to_datetime(df["open_time"].astype(np.int64), unit="ms", utc=True)
    df["close"]     = df["close"].astype(float)
    df["quote_vol"] = df["quote_vol"].astype(float)
    df = df.set_index("time").sort_index()
    return df[["close", "quote_vol"]]


# ─── SIGNAL CONSTRUCTION ──────────────────────────────────────────────────────

def build_total_daily_volume(daily_data: dict[str, pd.DataFrame]) -> pd.Series:
    """Sum quote_vol across all symbols → total USDT proxy volume, daily."""
    vols = {sym: df["quote_vol"] for sym, df in daily_data.items() if not df.empty}
    if not vols:
        return pd.Series(dtype=float)
    vol_df = pd.DataFrame(vols).fillna(0)
    return vol_df.sum(axis=1).rename("total_usdt_vol")


def compute_volume_zscore(daily_vol: pd.Series,
                           roll: int = ROLL_DAYS) -> pd.Series:
    """
    Rolling z-score of daily volume vs its own trailing {roll}-day baseline.
    z[T] = (vol[T] - mean(vol[T-roll:T])) / std(vol[T-roll:T])
    """
    roll_mean = daily_vol.rolling(roll, min_periods=roll // 2).mean()
    roll_std  = daily_vol.rolling(roll, min_periods=roll // 2).std()
    return ((daily_vol - roll_mean) / roll_std.replace(0, np.nan)).rename("vol_z")


def build_weekly_signal(daily_vol: pd.Series,
                         roll: int = ROLL_DAYS) -> pd.Series:
    """
    Weekly signal: mean z-score of the 5 business days ending each Friday.
    Resampled to W-FRI.
    """
    z_daily = compute_volume_zscore(daily_vol, roll)
    # Mean z-score within each Mon-Fri window
    wk_z = z_daily.resample("W-FRI").mean().dropna()
    return wk_z


# ─── TSMOM v3 ─────────────────────────────────────────────────────────────────

def compute_tsmom_weekly(btc_daily_close: pd.Series) -> pd.Series:
    """TSMOM v3: tanh(cumret_28d / vol_28d), long-only, weekly."""
    lr   = np.log(btc_daily_close / btc_daily_close.shift(1)).dropna()
    cr28 = lr.rolling(28).sum()
    v28  = lr.rolling(28).std() * np.sqrt(28)
    sig  = np.tanh(cr28 / v28.replace(0, np.nan)).clip(lower=0)
    return (sig.shift(1) * lr).resample("W-FRI").sum()


# ─── IC TEST ─────────────────────────────────────────────────────────────────

def ic_analysis(weekly_z: pd.Series,
                btc_daily_close: pd.Series) -> dict:
    """
    rank_corr(z[T], BTC_return_next_week[T]).
    z at week T → BTC return from Friday T to Friday T+1.
    """
    btc_wk_ret = np.log(btc_daily_close / btc_daily_close.shift(1)).resample("W-FRI").sum()
    # forward return: return of the FOLLOWING week (index T+1)
    fwd_ret    = btc_wk_ret.shift(-1)

    common = weekly_z.dropna().index.intersection(fwd_ret.dropna().index)
    if len(common) < 10:
        return {"ic": np.nan, "t_stat": np.nan, "p_val": np.nan, "n": 0}

    z   = weekly_z.reindex(common)
    ret = fwd_ret.reindex(common)
    ic, p_val = spearmanr(z, ret)
    n  = len(common)
    t  = ic * np.sqrt(n - 2) / np.sqrt(max(1 - ic ** 2, 1e-9))
    return {"ic": ic, "t_stat": t, "p_val": p_val, "n": n,
            "z_series": z, "ret_series": ret}


# ─── BACKTEST ─────────────────────────────────────────────────────────────────

def compute_vol_scalar(daily_close: pd.Series, vol_tgt: float = VOL_TGT) -> pd.Series:
    lr     = np.log(daily_close / daily_close.shift(1)).dropna()
    rv     = lr.rolling(28).std() * np.sqrt(252)
    wk_rv  = rv.resample("W-FRI").last().dropna()
    return (vol_tgt / wk_rv.replace(0, np.nan)).clip(0.1, 2.0)


def backtest(weekly_z: pd.Series,
             btc_close: pd.Series, eth_close: pd.Series,
             tsmom_wk: pd.Series) -> dict:
    """
    Binary signal: 1 when z > Z_THR, else 0.
    Long BTC+ETH (equal weight) vol-scaled to 15%.
    Position at T (formed from signal at T) → return of week T+1.
    """
    # Weekly log returns
    btc_wk = np.log(btc_close / btc_close.shift(1)).resample("W-FRI").sum()
    eth_wk = np.log(eth_close / eth_close.shift(1)).resample("W-FRI").sum()
    port_wk = ((btc_wk + eth_wk) / 2).dropna()

    # Vol scalar (BTC-based)
    v_sc = compute_vol_scalar(btc_close)

    # Signal
    raw_signal = (weekly_z > Z_THR).astype(float)

    # Align all
    common = (raw_signal.index
              .intersection(port_wk.index)
              .intersection(v_sc.index))
    if len(common) < 20:
        return {"sharpe": np.nan, "maxdd": np.nan, "corr_tsmom": np.nan,
                "trades_yr": 0, "port_series": pd.Series(dtype=float)}

    sig   = raw_signal.reindex(common)
    ret   = port_wk.reindex(common)
    v     = v_sc.reindex(common, method="ffill").fillna(1.0)

    # Lag: position formed at T → return at T+1
    pos   = sig.shift(1).fillna(0) * v
    entry = (pos.diff() > 0).astype(float)
    bar_r = pos * ret - entry * COST_RT
    cum_r = bar_r.cumsum()

    n_yrs    = max((common[-1] - common[0]).days / 365.25, 0.1)
    sharpe   = bar_r.mean() / bar_r.std() * np.sqrt(52) if bar_r.std() > 0 else 0.0
    maxdd    = (cum_r - cum_r.cummax()).min()
    trades_yr = entry.sum() / n_yrs

    # TSMOM correlation
    common_t = bar_r.index.intersection(tsmom_wk.index)
    corr_t   = (bar_r.loc[common_t].corr(tsmom_wk.loc[common_t])
                if len(common_t) >= 10 else np.nan)

    # Signal vs TSMOM position correlation (how often do both go long together?)
    tsmom_pos = (tsmom_wk > 0).astype(float)
    common_p  = sig.index.intersection(tsmom_pos.index)
    sig_corr  = (sig.loc[common_p].corr(tsmom_pos.loc[common_p])
                 if len(common_p) >= 10 else np.nan)

    return {
        "sharpe": sharpe, "maxdd": maxdd, "corr_tsmom": corr_t,
        "sig_corr_tsmom": sig_corr, "trades_yr": trades_yr,
        "cum_ret": cum_r, "bar_ret": bar_r, "n_weeks": len(common)
    }


# ─── FIGURE ──────────────────────────────────────────────────────────────────

def make_figure(daily_vol: pd.Series, daily_z: pd.Series,
                weekly_z: pd.Series, ic_res: dict,
                bt_res: dict, tsmom_wk: pd.Series,
                btc_close: pd.Series) -> None:

    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle(
        "USDT Flow Proxy Signal — Strategy C Candidate\n"
        "Signal: z-score of total Binance USDT volume vs 30-day baseline  |  "
        "Long BTC+ETH when z > 0  |  Weekly rebalance",
        fontsize=12, fontweight="bold"
    )

    # Panel 1: Daily USDT volume proxy (log scale)
    ax = axes[0, 0]
    dv = daily_vol / 1e9  # billions
    ax.fill_between(dv.index, 0, dv.values, color="#4393c3", alpha=0.6)
    ax.set_title("Total Binance USDT Volume Proxy (5 pairs)", fontsize=10)
    ax.set_ylabel("USDT Volume (Bn $)")
    ax.set_xlabel("Date"); ax.grid(alpha=0.3)
    ax.xaxis.set_major_locator(plt.MaxNLocator(5))

    # Panel 2: Daily z-score with weekly overlay
    ax = axes[0, 1]
    ax.plot(daily_z.index, daily_z.values, color="#888888", lw=0.6,
            alpha=0.5, label="Daily z-score")
    wz_daily = weekly_z.reindex(daily_z.index, method="ffill")
    ax.plot(wz_daily.index, wz_daily.values, color="#2166ac", lw=1.5,
            label="Weekly z-score (W-FRI)")
    ax.axhline(0, color="black", lw=0.8, ls="--")
    ax.fill_between(wz_daily.index, 0, wz_daily.values,
                    where=wz_daily.values > 0, color="#1a9850", alpha=0.3, label="Signal ON")
    ax.set_title("Volume Z-score (30d rolling baseline)", fontsize=10)
    ax.set_ylabel("Z-score"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
    ax.xaxis.set_major_locator(plt.MaxNLocator(5))

    # Panel 3: IC analysis (scatter z[T] vs ret[T+1])
    ax = axes[0, 2]
    if ic_res["n"] > 0:
        z_s = ic_res.get("z_series", pd.Series(dtype=float))
        r_s = ic_res.get("ret_series", pd.Series(dtype=float))
        ax.scatter(z_s, r_s * 100, alpha=0.4, s=20, color="#2166ac")
        from numpy.polynomial import polynomial as P
        if len(z_s) > 3:
            c = np.polyfit(z_s, r_s * 100, 1)
            x_line = np.linspace(z_s.min(), z_s.max(), 50)
            ax.plot(x_line, np.polyval(c, x_line), color="#d73027", lw=2)
        ax.axhline(0, color="black", lw=0.5)
        ax.axvline(0, color="black", lw=0.5, ls="--")
    ax.set_title(f"IC: z[T] vs BTC ret[T+1]\n"
                 f"IC={ic_res['ic']:+.4f}  t={ic_res['t_stat']:+.3f}  n={ic_res['n']}",
                 fontsize=10)
    ax.set_xlabel("USDT vol z-score"); ax.set_ylabel("Next-week BTC return (%)")
    ax.grid(alpha=0.3)

    # Panel 4: Equity curve
    ax = axes[1, 0]
    if "cum_ret" in bt_res and len(bt_res["cum_ret"]) > 0:
        cum = bt_res["cum_ret"]
        ax.plot(cum.index, cum.values * 100, color="#2166ac", lw=2,
                label=f"USDT signal  Sharpe={bt_res['sharpe']:.3f}")
        # BTC B&H
        btc_r = np.log(btc_close / btc_close.shift(1)).resample("W-FRI").sum().cumsum()
        ax.plot(btc_r.index, btc_r.values * 100, color="#888888", lw=1, ls="--",
                alpha=0.7, label="BTC buy & hold")
        # TSMOM
        ts_cum = tsmom_wk.cumsum()
        ax.plot(ts_cum.index, ts_cum.values * 100, color="#f4a582", lw=1.5,
                ls="-.", alpha=0.8, label="TSMOM v3")
        ax.axhline(0, color="black", lw=0.5)
    ax.set_title("Equity Curve (log return, %)", fontsize=10)
    ax.set_ylabel("Cum log return (%)"); ax.set_xlabel("Date")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Panel 5: Rolling 12-week IC
    ax = axes[1, 1]
    if ic_res["n"] > 0:
        z_s = ic_res.get("z_series", pd.Series(dtype=float))
        r_s = ic_res.get("ret_series", pd.Series(dtype=float))
        ic_roll = pd.Series(
            [spearmanr(z_s.iloc[max(0, i-12):i], r_s.iloc[max(0, i-12):i])[0]
             if i >= 12 else np.nan for i in range(1, len(z_s)+1)],
            index=z_s.index
        )
        ax.fill_between(ic_roll.index, 0, ic_roll.values,
                        where=ic_roll.values > 0, color="#1a9850", alpha=0.4)
        ax.fill_between(ic_roll.index, 0, ic_roll.values,
                        where=ic_roll.values < 0, color="#d73027", alpha=0.4)
        ax.plot(ic_roll.index, ic_roll.values, color="#2166ac", lw=1.5,
                label="12-week rolling IC")
        ax.axhline(0, color="black", lw=0.8)
        ax.axhline(ic_res["ic"], color="#2166ac", ls="--", lw=1,
                   label=f"Mean IC={ic_res['ic']:+.4f}")
    ax.set_title("Rolling 12-week IC", fontsize=10)
    ax.set_ylabel("IC (rank correlation)"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
    ax.xaxis.set_major_locator(plt.MaxNLocator(5))

    # Panel 6: Summary table
    ax = axes[1, 2]
    ax.axis("off")
    txt = (
        "═══ USDT FLOW PROXY SUMMARY ═══\n\n"
        f"IC (full period):\n"
        f"  Mean IC    = {ic_res['ic']:+.4f}\n"
        f"  IC t-stat  = {ic_res['t_stat']:+.3f}\n"
        f"  p-value    = {ic_res.get('p_val', np.nan):.4f}\n"
        f"  N weeks    = {ic_res['n']}\n\n"
        f"Portfolio:\n"
        f"  Sharpe     = {bt_res.get('sharpe', np.nan):+.3f}\n"
        f"  MaxDD      = {bt_res.get('maxdd', 0)*100:.1f}%\n"
        f"  Trades/yr  = {bt_res.get('trades_yr', 0):.0f}\n"
        f"  Cost/yr    ≈ {bt_res.get('trades_yr', 0)*COST_RT*100:.2f}%\n"
        f"  N weeks    = {bt_res.get('n_weeks', 0)}\n\n"
        f"Correlation:\n"
        f"  corr(returns, TSMOM) = {bt_res.get('corr_tsmom', np.nan):+.3f}\n"
        f"  corr(signal, TSMOM_pos) = {bt_res.get('sig_corr_tsmom', np.nan):+.3f}\n\n"
        f"VERDICT:\n"
        f"  GO if IC t > 1.5 AND corr < 0.30\n"
        f"  → {'GO ✓' if (ic_res['t_stat'] > 1.5 and abs(bt_res.get('corr_tsmom', 1)) < 0.30) else 'SKIP ✗'}\n\n"
        f"Signal: z > 0 ({(weekly_z > 0).mean():.1%} of weeks active)\n"
        f"Data: Binance daily klines, 5 pairs\n"
        f"(equiv. to summing hourly quote_vol)"
    )
    ax.text(0.05, 0.97, txt, transform=ax.transAxes,
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
    print("USDT FLOW PROXY SIGNAL — Strategy C Candidate")
    print(f"Proxy: total Binance USDT quote_vol ({', '.join(SYMBOLS)})")
    print(f"Signal: weekly z-score vs {ROLL_DAYS}-day rolling baseline")
    print("=" * 70)

    # ── 1. Fetch data ─────────────────────────────────────────────────────────
    print(f"\n[1/5] Fetching daily OHLCV from Binance ({len(SYMBOLS)} symbols)…")
    daily_data: dict[str, pd.DataFrame] = {}
    for sym in SYMBOLS:
        print(f"  {sym}… ", end="", flush=True)
        df = fetch_binance_daily(sym)
        if df.empty:
            print("FAILED")
        else:
            daily_data[sym] = df
            print(f"OK ({len(df)} days, "
                  f"{df.index[0].date()} → {df.index[-1].date()})")

    if "BTCUSDT" not in daily_data:
        print("ERROR: BTC data unavailable."); return
    if "ETHUSDT" not in daily_data:
        print("ERROR: ETH data unavailable."); return

    btc_close = daily_data["BTCUSDT"]["close"]
    eth_close = daily_data["ETHUSDT"]["close"]

    # ── 2. Build USDT volume proxy ────────────────────────────────────────────
    print("\n[2/5] Building USDT volume proxy…")
    daily_vol = build_total_daily_volume(daily_data)
    daily_z   = compute_volume_zscore(daily_vol, ROLL_DAYS)
    weekly_z  = build_weekly_signal(daily_vol, ROLL_DAYS)

    print(f"  Daily volume: {len(daily_vol)} days, "
          f"mean={daily_vol.mean()/1e9:.1f} Bn USDT/day")
    print(f"  Weekly z-score: {len(weekly_z)} weeks, "
          f"mean={weekly_z.mean():+.3f}, std={weekly_z.std():.3f}")
    print(f"  Signal ON (z > 0): {(weekly_z > 0).mean():.1%} of weeks")

    # Sub-period means
    for name, mask in [
        ("2022",     (weekly_z.index.year == 2022)),
        ("2023",     (weekly_z.index.year == 2023)),
        ("2024",     (weekly_z.index.year == 2024)),
        ("2025-26",  (weekly_z.index.year >= 2025)),
    ]:
        s = weekly_z[mask]
        if len(s) > 0:
            print(f"    {name}: mean z={s.mean():+.3f}  ON={( s > 0).mean():.0%}")

    # ── 3. TSMOM reference ────────────────────────────────────────────────────
    print("\n[3/5] Computing TSMOM v3 reference…")
    tsmom_wk = compute_tsmom_weekly(btc_close)
    tsmom_oos = tsmom_wk[tsmom_wk.index >= "2022-01-01"].dropna()
    if len(tsmom_oos) > 0:
        ts_sharpe = tsmom_oos.mean() / tsmom_oos.std() * np.sqrt(52)
        print(f"  TSMOM v3 Sharpe (2022→2026): {ts_sharpe:.3f}")

    # ── 4. IC test ────────────────────────────────────────────────────────────
    print("\n[4/5] IC analysis…")
    ic_res = ic_analysis(weekly_z, btc_close)
    print(f"  IC (full period):  {ic_res['ic']:+.4f}")
    print(f"  IC t-stat:         {ic_res['t_stat']:+.3f}  (p={ic_res.get('p_val', np.nan):.4f})")
    print(f"  N weeks:           {ic_res['n']}")

    # Sub-period IC
    for name, yr_start, yr_end in [
        ("2022–2023", "2022-01-01", "2024-01-01"),
        ("2024–2026", "2024-01-01", "2026-12-31"),
    ]:
        mask = ((weekly_z.index >= yr_start) & (weekly_z.index < yr_end))
        sub_z = weekly_z[mask].dropna()
        sub_r = (np.log(btc_close / btc_close.shift(1))
                 .resample("W-FRI").sum().shift(-1))
        sub_r = sub_r.reindex(sub_z.index).dropna()
        sub_z = sub_z.reindex(sub_r.index).dropna()
        if len(sub_z) >= 5:
            ic_sub, _ = spearmanr(sub_z, sub_r)
            n_sub     = len(sub_z)
            t_sub     = ic_sub * np.sqrt(n_sub - 2) / np.sqrt(max(1 - ic_sub**2, 1e-9))
            print(f"  Sub-period {name}: IC={ic_sub:+.4f}  t={t_sub:+.3f}  n={n_sub}")

    # ── 5. Backtest ───────────────────────────────────────────────────────────
    print("\n[5/5] Backtest (long BTC+ETH equal weight, vol-scaled 15%)…")
    bt_res = backtest(weekly_z, btc_close, eth_close, tsmom_wk)
    print(f"  Sharpe:          {bt_res['sharpe']:+.3f}")
    print(f"  MaxDD:           {bt_res['maxdd']*100:.1f}%")
    print(f"  Trades/yr:       {bt_res['trades_yr']:.0f}")
    print(f"  Cost/yr:         {bt_res['trades_yr']*COST_RT*100:.2f}%")
    print(f"  corr(TSMOM):     {bt_res['corr_tsmom']:+.3f}")
    print(f"  corr(sig, TSMOM_pos): {bt_res['sig_corr_tsmom']:+.3f}")
    print(f"  N weeks:         {bt_res['n_weeks']}")

    # Figure
    make_figure(daily_vol, daily_z, weekly_z, ic_res, bt_res, tsmom_wk, btc_close)

    # ── VERDICT ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    t_ic   = ic_res["t_stat"]
    c_ts   = abs(bt_res.get("corr_tsmom", 1))
    sh     = bt_res.get("sharpe", 0)

    print(f"  IC t-stat: {t_ic:+.3f}  (threshold: > 1.5)")
    print(f"  corr(TSMOM): {c_ts:+.3f}  (threshold: < 0.30)")
    print(f"  Sharpe: {sh:+.3f}")
    print()

    if t_ic > 1.5 and c_ts < 0.30:
        verdict = ("GO — USDT volume proxy has significant predictive power "
                   "AND diversifies TSMOM")
        action  = "Accept as Strategy C candidate. Test A+B+C portfolio weight."
    elif t_ic > 1.0 and c_ts < 0.40:
        verdict = "WEAK — some IC signal but below threshold or too correlated"
        action  = "Consider combining with TSMOM as an entry filter (not replacement)."
    else:
        verdict = "SKIP — IC not significant or too correlated with TSMOM"
        action  = ("The USDT volume proxy does not capture on-chain inflows at "
                   "weekly frequency. Would need true on-chain data (Glassnode).")

    print(f"  >>> {verdict}")
    print(f"  Next step: {action}")
    print()
    print("  Note on proxy quality: Binance quote_vol includes all USDT trading,")
    print("  not specifically 'stablecoin inflows'. For true Chi et al. (2025)")
    print("  signal, need Glassnode stablecoin exchange flow data (paid API).")


if __name__ == "__main__":
    main()
