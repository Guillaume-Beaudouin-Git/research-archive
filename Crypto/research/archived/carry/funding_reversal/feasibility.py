"""
strategies/funding_reversal/feasibility.py

Signal 35 — Extreme Funding Rate REVERSAL (price signal, not carry income)

Economic mechanism:
  HIGH funding (+2.5σ above 30d mean):
    → Longs massively overleveraged, paying extreme rates
    → Unsustainable → forced deleveraging → price DROP
    → Signal: SHORT the perp

  LOW funding (-2.0σ below 30d mean):
    → Shorts squeezed, paying high rates
    → Forced short cover → price RISE
    → Signal: LONG the perp

Different from tested signals:
  Strategy B (6.13): earns CARRY INCOME when funding > threshold (level)
  Signal 29 (6.29): 2nd derivative of funding trend → SKIP
  XGBoost CS (6.21): funding z-score as one feature among 12 → SKIP
  THIS: first-moment extremity predicts N-day price direction (contrarian)

Assets: BTC, ETH, SOL
Data:   HL funding (data/funding_rates.csv) + Binance daily OHLCV
Period: 2023-05-12 → 2026-04-29 (~3 years, includes 2023 bear + 2024-26 bull)
"""

import time as _time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.stats import spearmanr, ttest_1samp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore")

# ── Config ─────────────────────────────────────────────────────────────────────
ASSETS       = ["BTC", "ETH", "SOL"]
FUND_CSV     = Path("data/funding_rates.csv")
BIN_URL      = "https://api.binance.com/api/v3/klines"
START        = "2023-05-12"
END          = "2026-04-29"

Z_HIGH       = +2.5    # extreme positive funding → SHORT
Z_LOW        = -2.0    # extreme negative funding → LONG
ROLL_W       = 30      # days for rolling z-score window
HOLD_DAYS    = [1, 3, 5, 7]
DEFAULT_HLD  = 5
SL_PCT       = 0.07    # 7% stop-loss (applied directionally)
COST_RT      = 0.0017  # 0.17% round-trip
POS_SIZE     = 0.10    # 10% per trade (event-driven, few triggers)

FIG_OUT = Path("strategies/funding_reversal/feasibility_results.png")


# ── Data Loading ───────────────────────────────────────────────────────────────

def load_funding_daily(start: str, end: str) -> pd.DataFrame:
    """
    Load HL funding rates and normalize to daily mean "8h-equivalent rate".

    HL changed from 8h to 1h payment intervals around Sep 2023.
    Normalization:
      - 8h-era (2023): interval ≈ 8h, rate is already an 8h rate → scale × 1
      - 1h-era (2024+): interval ≈ 1h, multiply × 8 to get 8h-equiv
    Takes daily MEAN of all 8h-equiv rates → consistent across eras.
    """
    raw = pd.read_csv(FUND_CSV)
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True)
    raw = raw.set_index("timestamp").sort_index()

    result = {}
    for sym in ASSETS:
        sub = raw[raw["symbol"] == sym][["funding_rate"]].copy()
        # Compute interval in hours for each record
        dt_h = (sub.index.to_series()
                    .diff()
                    .dt.total_seconds()
                    .div(3600)
                    .fillna(8.0)
                    .clip(lower=0.5, upper=12.0))
        # Scale to 8h-equivalent
        sub["rate_8h"] = sub["funding_rate"] * (8.0 / dt_h.values)
        # Daily mean of 8h-equiv rates
        daily = sub["rate_8h"].resample("1D").mean().dropna()
        daily = daily.loc[start:end]
        result[sym] = daily

    return pd.DataFrame(result).dropna(how="all")


def fetch_binance_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Daily OHLCV from Binance (open/high/low/close)."""
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms   = int(pd.Timestamp(end,   tz="UTC").timestamp() * 1000)
    rows = []
    cur  = start_ms
    while cur < end_ms:
        try:
            r = requests.get(BIN_URL,
                             params={"symbol": symbol, "interval": "1d",
                                     "startTime": cur, "limit": 1000},
                             timeout=15)
            if r.status_code == 400:
                return pd.DataFrame()
            r.raise_for_status()
            batch = r.json()
        except Exception:
            return pd.DataFrame()
        if not batch:
            break
        rows.extend(batch)
        cur = int(batch[-1][0]) + 86_400_000
        _time.sleep(0.04)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_vol","n_trades","taker_base","taker_quote","_"
    ])
    df["time"] = pd.to_datetime(df["open_time"].astype(np.int64), unit="ms", utc=True)
    df = df.set_index("time")[["open","high","low","close"]].astype(float)
    return df[~df.index.duplicated(keep="last")].sort_index()


def load_prices_dict(start: str, end: str) -> dict[str, pd.DataFrame]:
    prices = {}
    for sym in ASSETS:
        df = fetch_binance_ohlcv(sym + "USDT", start, end)
        if not df.empty:
            prices[sym] = df
            print(f"    {sym}: {len(df)}d OK ({df.index[0].date()} → {df.index[-1].date()})")
        else:
            print(f"    {sym}: SKIP")
    return prices


# ── Signal Computation ─────────────────────────────────────────────────────────

def compute_zscore(daily_fund: pd.DataFrame) -> pd.DataFrame:
    """
    z[T] = (fund_mean_8h[T-1] - rolling_mean_30d[T-1]) / rolling_std_30d[T-1]
    Uses funding[T-1] so signal is known at start of day T (no look-ahead).
    Enter at close[T].
    """
    z_df = pd.DataFrame(index=daily_fund.index, columns=daily_fund.columns, dtype=float)
    for sym in daily_fund.columns:
        s    = daily_fund[sym].shift(1)           # fund[T-1] at position T
        mu   = s.rolling(ROLL_W, min_periods=ROLL_W // 2).mean()
        sig  = s.rolling(ROLL_W, min_periods=ROLL_W // 2).std()
        z_df[sym] = (s - mu) / sig.replace(0, np.nan)
    return z_df


# ── IC Analysis ────────────────────────────────────────────────────────────────

def ic_analysis(z_df: pd.DataFrame,
                prices_dict: dict,
                hold_periods: list[int]) -> dict:
    """
    IC = spearmanr(z[T], -fwd_price_ret[T:T+N]) pooled across assets and triggered days.
    Positive IC → high z predicts price DROP (confirms SHORT thesis).
    Negative z predicts price RISE → also captured (sign-consistent).
    Restricted to triggered days: |z| > 0.5 (weak threshold to maximise N).
    """
    results = {}
    for N in hold_periods:
        z_pool, neg_fwd = [], []
        for sym in ASSETS:
            if sym not in prices_dict or sym not in z_df.columns:
                continue
            close = prices_dict[sym]["close"]
            z     = z_df[sym].reindex(close.index, method="ffill")
            fwd   = np.log(close.shift(-N) / close)
            mask  = z.notna() & fwd.notna() & z.abs().gt(0.5)
            if mask.sum() < 10:
                continue
            z_pool.extend(z[mask].values.tolist())
            neg_fwd.extend((-fwd[mask]).values.tolist())

        if len(z_pool) < 10:
            results[N] = {"ic": 0.0, "t": 0.0, "n": 0}
            continue
        ic, _  = spearmanr(z_pool, neg_fwd)
        n      = len(z_pool)
        t_ic   = ic * np.sqrt(n - 2) / max(np.sqrt(max(1 - ic ** 2, 1e-9)), 1e-9)
        results[N] = {"ic": round(ic, 4), "t": round(t_ic, 3), "n": n}
    return results


# ── Trade Simulation ───────────────────────────────────────────────────────────

def simulate_trades(z_df: pd.DataFrame,
                    prices_dict: dict,
                    hold_days: int   = DEFAULT_HLD,
                    sl_pct:    float = SL_PCT) -> list[dict]:
    """
    SHORT when z > Z_HIGH (expect price DROP).
    LONG  when z < Z_LOW  (expect price RISE).
    Entry at close[T] after signal fires at start of T.
    SL for SHORT: exits if high[day] >= entry × (1 + sl_pct)
    SL for LONG:  exits if low[day]  <= entry × (1 - sl_pct)
    Cooldown: no new entry until exit of current trade (per asset).
    """
    all_trades = []
    for sym in ASSETS:
        if sym not in prices_dict or sym not in z_df.columns:
            continue
        df    = prices_dict[sym]
        close = df["close"]
        high  = df["high"]
        low   = df["low"]
        z     = z_df[sym].reindex(close.index, method="ffill")

        last_exit = -999
        for i in range(ROLL_W, len(close) - hold_days - 1):
            if i <= last_exit:
                continue
            zv = z.iloc[i]
            if pd.isna(zv):
                continue
            if zv > Z_HIGH:
                direction = "short"
            elif zv < Z_LOW:
                direction = "long"
            else:
                continue

            entry = close.iloc[i]
            if entry <= 0 or np.isnan(entry):
                continue

            sl_price = (entry * (1 + sl_pct) if direction == "short"
                        else entry * (1 - sl_pct))

            exit_price, exit_type, exit_idx = None, "TIME", i + hold_days
            for j in range(1, hold_days + 1):
                di = i + j
                if di >= len(close):
                    exit_idx = len(close) - 1
                    break
                if direction == "short" and high.iloc[di] >= sl_price:
                    exit_price, exit_type, exit_idx = sl_price, "SL", di
                    break
                if direction == "long"  and low.iloc[di] <= sl_price:
                    exit_price, exit_type, exit_idx = sl_price, "SL", di
                    break

            if exit_price is None:
                exit_idx   = min(i + hold_days, len(close) - 1)
                exit_price = close.iloc[exit_idx]

            sign  = -1 if direction == "short" else 1
            pnl_g = sign * np.log(exit_price / entry)
            all_trades.append({
                "asset":      sym,
                "direction":  direction,
                "entry_date": close.index[i],
                "exit_date":  close.index[exit_idx],
                "pnl_gross":  round(pnl_g, 6),
                "pnl_net":    round(pnl_g - COST_RT, 6),
                "exit_type":  exit_type,
                "z_score":    round(zv, 3),
                "year":       close.index[i].year,
            })
            last_exit = exit_idx
    return all_trades


def portfolio_pnl_daily(trades: list[dict],
                        prices_dict: dict,
                        pos_size: float = POS_SIZE) -> pd.Series:
    """
    Daily portfolio P&L: pos_size × daily log-return in position direction.
    """
    if not trades:
        return pd.Series(dtype=float)
    all_dates = sorted({d for df in prices_dict.values() for d in df.index})
    date_idx  = {d: i for i, d in enumerate(all_dates)}
    pnl_arr   = np.zeros(len(all_dates))

    for tr in trades:
        sym = tr["asset"]
        if sym not in prices_dict:
            continue
        close = prices_dict[sym]["close"]
        if tr["entry_date"] not in close.index:
            continue
        ei   = close.index.get_loc(tr["entry_date"])
        xi   = close.index.get_loc(tr["exit_date"]) if tr["exit_date"] in close.index else min(ei + DEFAULT_HLD, len(close) - 1)
        sign = -1 if tr["direction"] == "short" else 1

        for k in range(ei, xi):
            if k + 1 >= len(close):
                break
            day = close.index[k]
            if day not in date_idx:
                continue
            di = date_idx[day]
            if tr["exit_type"] == "SL" and k + 1 == xi:
                # Final SL day: use SL price vs open
                sl_price = (tr["pnl_net"] + COST_RT + np.log(close.iloc[ei])) * close.iloc[ei]
                pass
            daily_ret = np.log(close.iloc[k + 1] / close.iloc[k])
            pnl_arr[di] += pos_size * sign * daily_ret

    return pd.Series(pnl_arr, index=all_dates)


# ── Metrics ────────────────────────────────────────────────────────────────────

def trade_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0, "n_per_year": 0, "win_rate": 0,
                "profit_factor": 0, "sharpe_trade": 0, "sl_rate": 0,
                "avg_win_pct": 0, "avg_loss_pct": 0}
    pnl  = df["pnl_net"]
    wins = pnl[pnl > 0]
    loss = pnl[pnl < 0]
    pf   = wins.sum() / (-loss.sum()) if loss.sum() < 0 else float("inf")
    wr   = len(wins) / len(pnl)
    span = (df["entry_date"].max() - df["entry_date"].min()).days / 365
    n_yr = len(pnl) / max(span, 1)
    sh   = pnl.mean() * np.sqrt(n_yr) / pnl.std() if pnl.std() > 0 else 0.0
    return {
        "n":            len(pnl),
        "n_per_year":   round(n_yr, 1),
        "win_rate":     round(wr, 3),
        "profit_factor": round(pf, 3),
        "sharpe_trade": round(sh, 3),
        "sl_rate":      round((df["exit_type"] == "SL").mean(), 3),
        "avg_win_pct":  round(wins.mean() * 100 if len(wins) else 0, 2),
        "avg_loss_pct": round(loss.mean() * 100 if len(loss) else 0, 2),
    }


def sub_period_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    out = {}
    for yr in sorted(df["year"].unique()):
        sub = df[df["year"] == yr]["pnl_net"]
        if len(sub) < 3:
            continue
        pf = (sub[sub > 0].sum() / (-sub[sub < 0].sum())
              if sub[sub < 0].sum() < 0 else float("inf"))
        out[yr] = {"n": len(sub), "pf": round(pf, 2), "mean_pct": round(sub.mean() * 100, 3)}
    return out


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_results(z_df: pd.DataFrame,
                 daily_fund: pd.DataFrame,
                 ic_results: dict,
                 trades_df: pd.DataFrame,
                 pnl_port: pd.Series,
                 fig_path: Path) -> None:
    fig = plt.figure(figsize=(16, 12))
    gs  = gridspec.GridSpec(2, 2, hspace=0.40, wspace=0.32)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    # 1 — BTC funding z-score with signal regions
    sym_plot = "BTC"
    if sym_plot in z_df.columns:
        z_s = z_df[sym_plot].dropna()
        ax1.plot(z_s.index, z_s.values, lw=0.8, color="#2196F3", label="z-score")
        ax1.axhline(Z_HIGH, color="red",   lw=1.2, ls="--", label=f"SHORT z>{Z_HIGH}")
        ax1.axhline(Z_LOW,  color="green", lw=1.2, ls="--", label=f"LONG  z<{Z_LOW}")
        ax1.axhline(0,      color="black", lw=0.6)
        # Shade extreme regions
        ax1.fill_between(z_s.index, Z_HIGH, z_s.where(z_s > Z_HIGH),
                         alpha=0.3, color="red",   label="_nolegend_")
        ax1.fill_between(z_s.index, Z_LOW,  z_s.where(z_s < Z_LOW),
                         alpha=0.3, color="green", label="_nolegend_")
        ax1.set_title(f"BTC Funding z-score (30d rolling)", fontsize=10)
        ax1.legend(fontsize=8)
        ax1.grid(alpha=0.3)
        ax1.set_ylabel("z-score")

    # 2 — IC vs hold period
    N_vals = sorted(ic_results.keys())
    ic_vals = [ic_results[N]["ic"] for N in N_vals]
    t_vals  = [ic_results[N]["t"]  for N in N_vals]
    colors  = ["#4CAF50" if ic > 0 else "#F44336" for ic in ic_vals]
    bars    = ax2.bar([str(N) + "d" for N in N_vals], ic_vals,
                      color=colors, alpha=0.85, edgecolor="white")
    ax2b    = ax2.twinx()
    ax2b.plot([str(N) + "d" for N in N_vals], t_vals,
              "D--", color="#FF9800", ms=6, lw=1.5, label="t-stat")
    ax2b.axhline(2.0, color="#FF9800", lw=0.8, ls=":", alpha=0.6)
    ax2b.axhline(-2.0, color="#FF9800", lw=0.8, ls=":", alpha=0.6)
    ax2.axhline(0, color="black", lw=0.8)
    ax2.set_title("IC vs Hold Period\n(IC>0: SHORT thesis confirmed)", fontsize=10)
    ax2.set_ylabel("Spearman IC")
    ax2b.set_ylabel("t-stat", color="#FF9800")
    ax2b.legend(loc="upper right", fontsize=8)
    ax2.grid(alpha=0.3)

    # 3 — Portfolio equity curve
    if not pnl_port.empty and pnl_port.abs().sum() > 0:
        cum = pnl_port.cumsum() * 100
        ax3.plot(cum.index, cum.values, lw=1.5, color="#9C27B0")
        ax3.axhline(0, color="black", lw=0.8)
        ax3.set_title(f"Portfolio Equity Curve\n({POS_SIZE*100:.0f}% per trade, {DEFAULT_HLD}d hold)",
                      fontsize=10)
        ax3.set_ylabel("Cum. log-ret %")
        ax3.grid(alpha=0.3)
    else:
        ax3.text(0.5, 0.5, "No trades", ha="center", va="center", transform=ax3.transAxes)

    # 4 — Trade P&L distribution by direction
    if not trades_df.empty:
        for direction, color, label in [("short", "#F44336", "SHORT"),
                                        ("long",  "#4CAF50", "LONG")]:
            sub = trades_df[trades_df["direction"] == direction]["pnl_net"] * 100
            if not sub.empty:
                ax4.hist(sub.values, bins=20, alpha=0.6, color=color,
                         label=f"{label} (n={len(sub)}, mean={sub.mean():.2f}%)",
                         edgecolor="white")
        ax4.axvline(0, color="black", lw=1.5, ls="--")
        ax4.set_title("Trade P&L Distribution by Direction", fontsize=10)
        ax4.legend(fontsize=8)
        ax4.set_xlabel("P&L %")
        ax4.grid(alpha=0.3)

    fig.suptitle(
        f"Signal 35 — Extreme Funding Reversal: z>{Z_HIGH} → SHORT, z<{Z_LOW} → LONG\n"
        f"Assets: {', '.join(ASSETS)} | {DEFAULT_HLD}d hold | {SL_PCT*100:.0f}% SL | {START}→{END}",
        fontsize=11, y=0.99
    )
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {fig_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    t0 = _time.time()
    print("=" * 70)
    print("EXTREME FUNDING REVERSAL — Contrarian price signal")
    print("Signal 35 — Strategy C candidate")
    print(f"z>{Z_HIGH} → SHORT, z<{Z_LOW} → LONG | {DEFAULT_HLD}d hold | {SL_PCT*100:.0f}% SL")
    print("=" * 70)

    # ── Step 1: Load funding data ─────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 1 — LOAD HL FUNDING DATA (normalized to 8h-equiv)")
    print(f"{'='*70}")
    daily_fund = load_funding_daily(START, END)
    print(f"  Loaded: {len(daily_fund)} days × {len(daily_fund.columns)} assets")
    print(f"  Range: {daily_fund.index[0].date()} → {daily_fund.index[-1].date()}")
    print(f"\n  Funding statistics (daily mean 8h-equiv rate):")
    print(f"  {'Asset':<8} {'Mean%':>8} {'Std%':>8} {'Max%':>8} {'Min%':>8} {'p99%':>8}")
    print(f"  {'-'*50}")
    for sym in ASSETS:
        if sym not in daily_fund.columns:
            continue
        s = daily_fund[sym] * 100
        print(f"  {sym:<8} {s.mean():>8.4f} {s.std():>8.4f} "
              f"{s.max():>8.4f} {s.min():>8.4f} {s.quantile(0.99):>8.4f}")

    # ── Step 2: Load price data ───────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"STEP 2 — LOAD BINANCE OHLCV ({START} → {END})")
    print(f"{'='*70}")
    prices = load_prices_dict(START, END)

    # ── Step 3: Compute z-score signal ───────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 3 — FUNDING Z-SCORE SIGNAL")
    print(f"{'='*70}")
    z_df = compute_zscore(daily_fund)

    # Align z-score to price index
    price_ref = prices[ASSETS[0]]["close"] if ASSETS[0] in prices else None
    if price_ref is not None:
        z_df = z_df.reindex(price_ref.index, method="ffill")

    print(f"  {'Asset':<8} {'n_short':>8} {'n_long':>6} {'total/yr':>9} {'max_z':>7} {'min_z':>7}")
    print(f"  {'-'*45}")
    for sym in ASSETS:
        if sym not in z_df.columns:
            continue
        z = z_df[sym].dropna()
        n_short = (z > Z_HIGH).sum()
        n_long  = (z < Z_LOW).sum()
        span_yr = (z.index[-1] - z.index[0]).days / 365
        total_yr = round((n_short + n_long) / span_yr, 1) if span_yr > 0 else 0
        print(f"  {sym:<8} {n_short:>8} {n_long:>6} {total_yr:>9.1f} "
              f"{z.max():>7.2f} {z.min():>7.2f}")

    # ── Step 4: IC analysis ───────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 4 — IC ANALYSIS (Spearman, pooled across assets)")
    print(f"{'='*70}")
    print(f"  IC > 0 → high z predicts price DROP (SHORT thesis valid)")
    ic_res = ic_analysis(z_df, prices, HOLD_DAYS)
    print(f"  {'Hold':>6} {'IC':>8} {'t-stat':>8} {'n':>6}  Verdict")
    print(f"  {'-'*50}")
    best_N, best_ic = DEFAULT_HLD, 0.0
    for N, r in ic_res.items():
        flag = "✓ PASS" if r["t"] > 1.5 and r["ic"] > 0 else ("✗ FAIL" if r["ic"] <= 0 else "~ WEAK")
        print(f"  {N:>5}d {r['ic']:>8.4f} {r['t']:>8.3f} {r['n']:>6}  {flag}")
        if r["ic"] > best_ic:
            best_ic, best_N = r["ic"], N

    print(f"\n  Best hold period: {best_N}d  (IC={best_ic:.4f})")

    # ── Step 5: Backtest ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"STEP 5 — BACKTEST (default: {DEFAULT_HLD}d  |  best IC: {best_N}d)")
    print(f"{'='*70}")
    print(f"\n  {'Config':<15} {'n':>5} {'n/yr':>6} {'WinRate':>8} {'PF':>7} {'SL%':>7} {'Sharpe':>8}")
    print(f"  {'-'*58}")

    all_config_results = {}
    for N in sorted({DEFAULT_HLD, best_N}):
        trades   = simulate_trades(z_df, prices, hold_days=N)
        df_trades = (pd.DataFrame(trades)
                       .assign(entry_date=lambda d: pd.to_datetime(d["entry_date"]))
                       if trades else pd.DataFrame())
        m = trade_metrics(df_trades)
        all_config_results[N] = (trades, df_trades, m)
        lbl = f"{N}d (best IC)" if N == best_N and N != DEFAULT_HLD else f"{N}d"
        if m["n"] > 0:
            print(f"  {lbl:<15} {m['n']:>5} {m['n_per_year']:>6.1f} "
                  f"{m['win_rate']:>8.1%} {m['profit_factor']:>7.3f} "
                  f"{m['sl_rate']:>7.1%} {m['sharpe_trade']:>8.3f}")
        else:
            print(f"  {lbl:<15}  (no trades)")

    # Detailed analysis of DEFAULT hold
    trades_default, df_default, m_default = all_config_results[DEFAULT_HLD]

    # Direction breakdown
    if not df_default.empty:
        print(f"\n  Direction breakdown ({DEFAULT_HLD}d):")
        print(f"  {'Direction':<12} {'n':>5} {'WinRate':>8} {'PF':>7} {'SL%':>7} {'AvgWin%':>9} {'AvgLoss%':>10}")
        print(f"  {'-'*60}")
        for direction in ["short", "long"]:
            sub_d = df_default[df_default["direction"] == direction]
            if sub_d.empty:
                print(f"  {direction:<12}    0  (no triggers)")
                continue
            m_d = trade_metrics(sub_d)
            print(f"  {direction:<12} {m_d['n']:>5} {m_d['win_rate']:>8.1%} "
                  f"{m_d['profit_factor']:>7.3f} {m_d['sl_rate']:>7.1%} "
                  f"{m_d['avg_win_pct']:>9.2f} {m_d['avg_loss_pct']:>10.2f}")

    # Asset breakdown
    if not df_default.empty:
        print(f"\n  Asset breakdown ({DEFAULT_HLD}d):")
        print(f"  {'Asset':<8} {'n':>5} {'WinRate':>8} {'PF':>7} {'SL%':>7}")
        print(f"  {'-'*42}")
        for sym in ASSETS:
            sub_a = df_default[df_default["asset"] == sym]
            if sub_a.empty:
                continue
            m_a = trade_metrics(sub_a)
            print(f"  {sym:<8} {m_a['n']:>5} {m_a['win_rate']:>8.1%} "
                  f"{m_a['profit_factor']:>7.3f} {m_a['sl_rate']:>7.1%}")

    # ── Step 6: Sub-period analysis ───────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 6 — SUB-PERIOD ANALYSIS")
    print(f"{'='*70}")
    if not df_default.empty:
        sub_p = sub_period_metrics(df_default)
        print(f"  {'Year':<8} {'n':>5} {'PF':>7} {'Mean%':>9}")
        print(f"  {'-'*30}")
        for yr, sp in sub_p.items():
            tag = "  ← bear" if yr == 2023 else ""
            print(f"  {yr:<8} {sp['n']:>5} {sp['pf']:>7.2f} {sp['mean_pct']:>+9.3f}%{tag}")
    else:
        print("  No trades")

    # ── Step 7: Statistical test ──────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 7 — STATISTICAL TEST (fwd returns: conditioned vs unconditional)")
    print(f"{'='*70}")
    for sym in ASSETS:
        if sym not in prices or sym not in z_df.columns:
            continue
        close = prices[sym]["close"]
        z     = z_df[sym].reindex(close.index)
        fwd   = np.log(close.shift(-DEFAULT_HLD) / close)

        cond_short = fwd[(z > Z_HIGH) & fwd.notna()].dropna()
        cond_long  = fwd[(z < Z_LOW)  & fwd.notna()].dropna()
        uncond     = fwd.dropna()

        print(f"\n  {sym}:")
        print(f"    Unconditional {DEFAULT_HLD}d return: mean={uncond.mean()*100:+.3f}%  "
              f"n={len(uncond)}")
        if len(cond_short) >= 3:
            t, p = ttest_1samp(cond_short, uncond.mean())
            print(f"    SHORT-trigger {DEFAULT_HLD}d return: mean={cond_short.mean()*100:+.3f}%  "
                  f"n={len(cond_short)}  t={t:.2f}  p={p:.4f}  "
                  f"{'PASS' if t < -1.5 else 'FAIL'}  (expect < uncond)")
        if len(cond_long) >= 3:
            t, p = ttest_1samp(cond_long, uncond.mean())
            print(f"    LONG-trigger  {DEFAULT_HLD}d return: mean={cond_long.mean()*100:+.3f}%  "
                  f"n={len(cond_long)}   t={t:.2f}  p={p:.4f}  "
                  f"{'PASS' if t > 1.5 else 'FAIL'}  (expect > uncond)")

    # ── Portfolio equity curve ─────────────────────────────────────────────────
    pnl_port = portfolio_pnl_daily(trades_default, prices)

    # ── Verdict ───────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("VERDICT")
    print(f"{'='*70}")
    pf   = m_default.get("profit_factor", 0)
    best_ic_t = ic_res.get(best_N, {}).get("t", 0)
    bear_pf   = sub_period_metrics(df_default).get(2023, {}).get("pf", 0)

    if pf > 1.3 and best_ic_t > 1.5 and bear_pf > 1.0:
        verdict = f"GO — PF={pf:.2f}>1.3  IC-t={best_ic_t:.2f}>1.5  2023 PF={bear_pf:.2f}>1.0"
    elif pf > 1.1 and best_ic_t > 1.0:
        verdict = f"PROMISING — PF={pf:.2f}∈[1.1,1.3]  IC-t={best_ic_t:.2f}>1.0"
    else:
        verdict = (f"SKIP — PF={pf:.2f}<1.1  or  IC-t={best_ic_t:.2f}<1.0  "
                   f"(no statistical edge for price reversal)")

    print(f"\n  Default config ({DEFAULT_HLD}d):")
    print(f"    PF={pf:.3f}  IC-t(best hold={best_N}d)={best_ic_t:.2f}  "
          f"2023 bear PF={bear_pf:.2f}  n={m_default.get('n',0)}")
    print(f"\n  >>> {verdict}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    plot_results(z_df, daily_fund, ic_res, df_default, pnl_port, FIG_OUT)
    elapsed = (_time.time() - t0) / 60
    print(f"\nTotal runtime: {elapsed:.1f} min")
    print(f"Verdict: {verdict.split(' — ')[0]}")


if __name__ == "__main__":
    main()
