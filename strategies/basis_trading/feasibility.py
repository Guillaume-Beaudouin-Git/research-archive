"""
strategies/basis_trading/feasibility.py

Signal 36 — Perp-Spot Basis Mean Reversion
Source: He & Manela (2024), arXiv 2212.06888
"High Sharpe ratios even for highest trading cost tier on Binance."

Economic mechanism:
  basis[T] = (perp_price[T] - spot_price[T]) / spot_price[T] × 100%

  When perp at significant PREMIUM to spot (basis_z > +1.5):
    → Arbitrageurs buy spot + short perp (convergence trade)
    → Positive funding drains longs → perp underperforms spot
    → Signal: SHORT perp (bet on convergence)

  When perp at DISCOUNT to spot (basis_z < -1.5):
    → Arbitrageurs short spot + buy perp
    → Negative funding drains shorts → perp outperforms spot
    → Signal: LONG perp (bet on convergence)

Different from Strategy B (6.13):
  Strategy B: earns FUNDING INCOME by holding a delta-neutral position
  Basis trade: earns PRICE CONVERGENCE (pure perp directional, no spot leg)

Basis and funding are related (both positive when perp > spot), but:
  - Funding = rate of carrying cost (flow, 1h settlement)
  - Basis = accumulated price dislocation (stock, can be large/small independently)
  A large premium can persist for days before funding forces convergence.
  The trade bets on reversion within 10 days.

Assets: BTC, ETH, SOL
Perp prices: HL mark prices (strategies/cs_carry/data/prices_daily.csv)
Spot prices:  yfinance BTC-USD, ETH-USD, SOL-USD (daily close)
Period: 2024-01-01 → 2026-05-10 (~16 months, only era with both datasets)
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
ASSETS        = ["BTC", "ETH", "SOL"]
SPOT_URL      = "https://api.binance.com/api/v3/klines"
PERP_URL      = "https://fapi.binance.com/fapi/v1/klines"   # Binance perpetual futures
START         = "2021-01-01"   # Binance USDT perp data available back to 2019+
END           = "2026-05-10"

Z_ENTER       = 1.5   # |basis_z| > 1.5 → enter
Z_EXIT        = 0.5   # |basis_z| < 0.5 → exit (mean reversion complete)
ROLL_W        = 30    # days for z-score window
MAX_HOLD      = 10    # maximum hold days if exit condition not met
SL_PCT        = 0.07  # 7% stop-loss (applied directionally on perp)
COST_RT       = 0.0017
POS_SIZE      = 0.10  # 10% per trade

FIG_OUT = Path("strategies/basis_trading/feasibility_results.png")

YF_MAP = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD"}


# ── Data Loading ───────────────────────────────────────────────────────────────

def _fetch_klines(url: str, symbol: str, start: str, end: str) -> pd.DataFrame:
    """Generic Binance klines fetcher (spot or futures)."""
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms   = int(pd.Timestamp(end,   tz="UTC").timestamp() * 1000)
    rows = []
    cur  = start_ms
    while cur < end_ms:
        try:
            r = requests.get(url,
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
    df = df.set_index("time")[["open","high","low","close"]].astype(float).sort_index()
    return df[~df.index.duplicated(keep="last")]


def load_perp_prices(assets: list[str]) -> pd.DataFrame:
    """
    Load Binance USDT perpetual futures daily close prices.
    Basis = (perp_close - spot_close) / spot_close × 100%.
    Using Binance perp vs Binance spot = self-consistent; same exchange as He & Manela (2024).
    """
    result = {}
    for sym in assets:
        df = _fetch_klines(PERP_URL, sym + "USDT", START, END)
        if not df.empty:
            result[sym] = df["close"]
            print(f"    {sym} (Binance perp): {len(df)}d OK "
                  f"({df.index[0].date()} → {df.index[-1].date()})")
        else:
            print(f"    {sym} perp: SKIP")
    out = pd.DataFrame(result)
    out.index = pd.to_datetime(out.index, utc=True)
    return out.loc[START:END]


def load_spot_prices(assets: list[str]) -> pd.DataFrame:
    """Load Binance spot daily close prices (same exchange as perp for clean basis)."""
    result = {}
    for sym in assets:
        df = _fetch_klines(SPOT_URL, sym + "USDT", START, END)
        if not df.empty:
            result[sym] = df["close"]
            print(f"    {sym} (Binance spot): {len(df)}d OK")
        else:
            print(f"    {sym}: SKIP")
    out = pd.DataFrame(result)
    out.index = pd.to_datetime(out.index, utc=True)
    return out.loc[START:END]


def load_perp_ohlcv(assets: list[str]) -> dict[str, pd.DataFrame]:
    """Load Binance perpetual futures OHLCV for SL simulation."""
    result = {}
    for sym in assets:
        df = _fetch_klines(PERP_URL, sym + "USDT", START, END)
        if not df.empty:
            result[sym] = df
    return result


# ── Basis & Signal ─────────────────────────────────────────────────────────────

def compute_basis(perp: pd.DataFrame, spot: pd.DataFrame) -> pd.DataFrame:
    """
    basis[T] = (perp[T] - spot[T]) / spot[T] × 100%
    Align on common UTC date index.
    """
    common_idx = perp.index.normalize().intersection(spot.index.normalize())
    basis = pd.DataFrame(index=common_idx, columns=ASSETS, dtype=float)
    for sym in ASSETS:
        if sym not in perp.columns or sym not in spot.columns:
            continue
        p = perp[sym].reindex(common_idx)
        s = spot[sym].reindex(common_idx)
        basis[sym] = (p - s) / s * 100.0
    return basis.dropna(how="all")


def compute_basis_zscore(basis: pd.DataFrame) -> pd.DataFrame:
    """
    basis_z[T] = (basis[T-1] - rolling_mean_30d[T-1]) / rolling_std_30d[T-1]
    Shift-1 ensures no look-ahead: signal known at start of day T, enter at close[T].
    """
    z_df = pd.DataFrame(index=basis.index, columns=basis.columns, dtype=float)
    for sym in basis.columns:
        s    = basis[sym].shift(1)
        mu   = s.rolling(ROLL_W, min_periods=ROLL_W // 2).mean()
        sig  = s.rolling(ROLL_W, min_periods=ROLL_W // 2).std()
        z_df[sym] = (s - mu) / sig.replace(0, np.nan)
    return z_df


# ── IC Analysis ────────────────────────────────────────────────────────────────

def ic_analysis(basis_z: pd.DataFrame,
                perp_prices: pd.DataFrame,
                hold_periods: list[int]) -> dict:
    """
    IC = spearmanr(basis_z[T], -fwd_perp_return[T:T+N]) for triggered days.
    Positive IC → high basis_z (perp premium) predicts perp DROP (SHORT thesis).
    """
    results = {}
    for N in hold_periods:
        z_pool, neg_fwd = [], []
        for sym in ASSETS:
            if sym not in basis_z.columns or sym not in perp_prices.columns:
                continue
            perp  = perp_prices[sym].reindex(basis_z.index)
            z     = basis_z[sym]
            fwd   = np.log(perp.shift(-N) / perp)
            mask  = z.notna() & fwd.notna() & z.abs().gt(0.3)
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

def simulate_trades(basis_z:    pd.DataFrame,
                    basis:      pd.DataFrame,
                    perp_ohlcv: dict,
                    perp_close: pd.DataFrame,
                    max_hold:   int   = MAX_HOLD,
                    sl_pct:     float = SL_PCT) -> list[dict]:
    """
    SHORT perp when basis_z > +Z_ENTER (perp at premium → expect perp to drop).
    LONG  perp when basis_z < -Z_ENTER (perp at discount → expect perp to rise).
    Exit when |basis_z| < Z_EXIT (mean reversion complete) OR max_hold days.
    SL for SHORT: perp price rises 7% above entry.
    SL for LONG:  perp price falls 7% below entry.
    """
    all_trades = []
    for sym in ASSETS:
        if sym not in basis_z.columns or sym not in perp_close.columns:
            continue
        z     = basis_z[sym]
        bz    = basis[sym]
        close = perp_close[sym].reindex(z.index)

        # Get OHLCV for SL simulation (high/low)
        if perp_ohlcv.get(sym) is not None:
            ohlcv = perp_ohlcv[sym]
            high  = ohlcv["high"].reindex(z.index, method="ffill")
            low   = ohlcv["low"].reindex(z.index, method="ffill")
        else:
            high = close  # conservative: use close as proxy for high/low
            low  = close

        last_exit = -999
        for i in range(ROLL_W, len(close) - max_hold - 1):
            if i <= last_exit:
                continue
            zv = z.iloc[i]
            if pd.isna(zv):
                continue
            if zv > Z_ENTER:
                direction = "short"
            elif zv < -Z_ENTER:
                direction = "long"
            else:
                continue

            entry = close.iloc[i]
            if entry <= 0 or np.isnan(entry):
                continue

            sl_price = (entry * (1 + sl_pct) if direction == "short"
                        else entry * (1 - sl_pct))

            exit_price, exit_type, exit_idx = None, "TIME", i + max_hold
            for j in range(1, max_hold + 1):
                di = i + j
                if di >= len(close):
                    exit_idx = len(close) - 1
                    break
                # Check SL
                if direction == "short" and high.iloc[di] >= sl_price:
                    exit_price, exit_type, exit_idx = sl_price, "SL", di
                    break
                if direction == "long"  and low.iloc[di] <= sl_price:
                    exit_price, exit_type, exit_idx = sl_price, "SL", di
                    break
                # Check mean-reversion exit: |basis_z| < Z_EXIT
                bz_val = bz.iloc[di]
                if not pd.isna(bz_val) and abs(bz_val) < Z_EXIT:
                    exit_type, exit_idx = "MR", di
                    break

            if exit_price is None:
                exit_idx   = min(exit_idx, len(close) - 1)
                exit_price = close.iloc[exit_idx]

            sign  = -1 if direction == "short" else 1
            pnl_g = sign * np.log(exit_price / entry)
            hold  = exit_idx - i

            all_trades.append({
                "asset":       sym,
                "direction":   direction,
                "entry_date":  close.index[i],
                "exit_date":   close.index[exit_idx],
                "hold_days":   hold,
                "pnl_gross":   round(pnl_g, 6),
                "pnl_net":     round(pnl_g - COST_RT, 6),
                "exit_type":   exit_type,
                "basis_z":     round(zv, 3),
                "year":        close.index[i].year,
            })
            last_exit = exit_idx
    return all_trades


# ── Metrics ────────────────────────────────────────────────────────────────────

def trade_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0, "n_per_year": 0, "win_rate": 0,
                "profit_factor": 0, "sharpe_trade": 0, "sl_rate": 0,
                "mr_rate": 0, "avg_hold": 0}
    pnl  = df["pnl_net"]
    wins = pnl[pnl > 0]
    loss = pnl[pnl < 0]
    pf   = wins.sum() / (-loss.sum()) if loss.sum() < 0 else float("inf")
    wr   = len(wins) / len(pnl)
    span = (df["entry_date"].max() - df["entry_date"].min()).days / 365
    n_yr = len(pnl) / max(span, 1)
    sh   = pnl.mean() * np.sqrt(n_yr) / pnl.std() if pnl.std() > 0 else 0.0
    return {
        "n":             len(pnl),
        "n_per_year":    round(n_yr, 1),
        "win_rate":      round(wr, 3),
        "profit_factor": round(pf, 3),
        "sharpe_trade":  round(sh, 3),
        "sl_rate":       round((df["exit_type"] == "SL").mean(), 3),
        "mr_rate":       round((df["exit_type"] == "MR").mean(), 3),
        "avg_hold":      round(df["hold_days"].mean(), 1),
        "avg_win_pct":   round(wins.mean() * 100 if len(wins) else 0, 2),
        "avg_loss_pct":  round(loss.mean() * 100 if len(loss) else 0, 2),
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

def plot_results(basis:     pd.DataFrame,
                 basis_z:   pd.DataFrame,
                 ic_res:    dict,
                 trades_df: pd.DataFrame,
                 fig_path:  Path) -> None:
    fig = plt.figure(figsize=(16, 12))
    gs  = gridspec.GridSpec(2, 2, hspace=0.40, wspace=0.32)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    # 1 — BTC basis time series with z-score bands
    sym_plot = "BTC"
    if sym_plot in basis.columns and sym_plot in basis_z.columns:
        b  = basis[sym_plot].dropna()
        bz = basis_z[sym_plot].reindex(b.index)
        ax1.plot(b.index, b.values, lw=1.2, color="#2196F3", label="Basis %")
        ax1.axhline(0, color="black", lw=0.8)
        # Mark extreme regions
        long_mask  = bz < -Z_ENTER
        short_mask = bz >  Z_ENTER
        ax1.fill_between(b.index, 0, b.where(short_mask), alpha=0.3,
                         color="red", label=f"SHORT region (z>{Z_ENTER})")
        ax1.fill_between(b.index, 0, b.where(long_mask),  alpha=0.3,
                         color="green", label=f"LONG region (z<-{Z_ENTER})")
        ax1.set_title("BTC Perp-Spot Basis % (HL perp vs yfinance spot)", fontsize=10)
        ax1.legend(fontsize=8)
        ax1.grid(alpha=0.3)
        ax1.set_ylabel("Basis %")

    # 2 — IC vs hold period
    N_vals  = sorted(ic_res.keys())
    ic_vals = [ic_res[N]["ic"] for N in N_vals]
    t_vals  = [ic_res[N]["t"]  for N in N_vals]
    colors  = ["#4CAF50" if v > 0 else "#F44336" for v in ic_vals]
    ax2.bar([str(N) + "d" for N in N_vals], ic_vals,
            color=colors, alpha=0.85, edgecolor="white")
    ax2b = ax2.twinx()
    ax2b.plot([str(N) + "d" for N in N_vals], t_vals, "D--",
              color="#FF9800", ms=6, lw=1.5, label="t-stat")
    ax2b.axhline(2.0,  color="#FF9800", lw=0.8, ls=":", alpha=0.6)
    ax2b.axhline(-2.0, color="#FF9800", lw=0.8, ls=":", alpha=0.6)
    ax2.axhline(0, color="black", lw=0.8)
    ax2.set_title("IC vs Hold Period\n(IC>0: HIGH basis predicts perp DROP)", fontsize=10)
    ax2.set_ylabel("Spearman IC")
    ax2b.set_ylabel("t-stat", color="#FF9800")
    ax2b.legend(loc="upper right", fontsize=8)
    ax2.grid(alpha=0.3)

    # 3 — Trade P&L distribution by direction
    if not trades_df.empty:
        for direction, color, label in [("short", "#F44336", "SHORT (perp premium→drop)"),
                                        ("long",  "#4CAF50", "LONG  (perp discount→rise)")]:
            sub = trades_df[trades_df["direction"] == direction]["pnl_net"] * 100
            if not sub.empty:
                ax3.hist(sub.values, bins=20, alpha=0.6, color=color,
                         label=f"{label} (n={len(sub)}, mean={sub.mean():.2f}%)",
                         edgecolor="white")
        ax3.axvline(0, color="black", lw=1.5, ls="--")
        ax3.set_title("Trade P&L Distribution", fontsize=10)
        ax3.legend(fontsize=8)
        ax3.set_xlabel("P&L %")
        ax3.grid(alpha=0.3)

    # 4 — Exit type breakdown by year
    if not trades_df.empty and "exit_type" in trades_df.columns:
        yr_groups = trades_df.groupby(["year", "exit_type"]).size().unstack(fill_value=0)
        yr_groups.plot(kind="bar", ax=ax4, stacked=True,
                       color={"MR": "#4CAF50", "SL": "#F44336", "TIME": "#FF9800"},
                       alpha=0.85, edgecolor="white")
        ax4.set_title("Exit Type by Year\n(MR=mean-revert, SL=stop-loss, TIME=timeout)",
                      fontsize=10)
        ax4.set_ylabel("Trade count")
        ax4.legend(fontsize=8)
        ax4.grid(alpha=0.3, axis="y")
        ax4.tick_params(axis="x", rotation=0)

    fig.suptitle(
        f"Signal 36 — Perp-Spot Basis Mean Reversion (He & Manela 2024)\n"
        f"basis_z>{Z_ENTER} → SHORT perp, basis_z<-{Z_ENTER} → LONG perp | "
        f"Exit: |z|<{Z_EXIT} OR {MAX_HOLD}d | {SL_PCT*100:.0f}% SL | {START}→{END}",
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
    print("PERP-SPOT BASIS MEAN REVERSION — He & Manela (2024)")
    print("Signal 36 — Strategy C candidate")
    print(f"basis_z>{Z_ENTER} → SHORT perp, basis_z<-{Z_ENTER} → LONG perp")
    print(f"Exit: |basis_z|<{Z_EXIT} OR {MAX_HOLD}d max | {SL_PCT*100:.0f}% SL")
    print("=" * 70)

    # ── Step 1: Load data ─────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 1 — LOAD PERP (HL) + SPOT (yfinance) PRICES")
    print(f"{'='*70}")
    print("  Loading HL perp prices from cs_carry/data/prices_daily.csv...")
    perp_prices = load_perp_prices(ASSETS)
    print(f"    {len(perp_prices)}d × {len(perp_prices.columns)} assets  "
          f"({perp_prices.index[0].date()} → {perp_prices.index[-1].date()})")

    print("\n  Loading spot prices...")
    spot_prices = load_spot_prices(ASSETS)
    if spot_prices.empty:
        print("  ERROR: No spot prices loaded. Aborting.")
        return

    # ── Step 2: Compute basis ─────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 2 — BASIS COMPUTATION")
    print(f"{'='*70}")
    basis = compute_basis(perp_prices, spot_prices)
    print(f"  Common days: {len(basis)}")
    print(f"\n  Basis statistics (%) = (HL_perp - spot) / spot × 100:")
    print(f"  {'Asset':<8} {'Mean%':>8} {'Std%':>8} {'Max%':>8} {'Min%':>8} "
          f"{'p5%':>8} {'p95%':>8}")
    print(f"  {'-'*58}")
    for sym in ASSETS:
        if sym not in basis.columns:
            continue
        b = basis[sym].dropna()
        print(f"  {sym:<8} {b.mean():>8.4f} {b.std():>8.4f} "
              f"{b.max():>8.4f} {b.min():>8.4f} "
              f"{b.quantile(0.05):>8.4f} {b.quantile(0.95):>8.4f}")

    # ── Step 3: Compute z-score signal ────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 3 — BASIS Z-SCORE SIGNAL")
    print(f"{'='*70}")
    basis_z = compute_basis_zscore(basis)
    print(f"  {'Asset':<8} {'n_short':>8} {'n_long':>7} {'total/yr':>10} "
          f"{'max_z':>7} {'min_z':>7}")
    print(f"  {'-'*50}")
    for sym in ASSETS:
        if sym not in basis_z.columns:
            continue
        z = basis_z[sym].dropna()
        n_short = (z > Z_ENTER).sum()
        n_long  = (z < -Z_ENTER).sum()
        span_yr = (z.index[-1] - z.index[0]).days / 365
        total_yr = round((n_short + n_long) / span_yr, 1) if span_yr > 0 else 0
        print(f"  {sym:<8} {n_short:>8} {n_long:>7} {total_yr:>10.1f} "
              f"{z.max():>7.2f} {z.min():>7.2f}")

    # ── Step 4: IC analysis ───────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 4 — IC ANALYSIS (Spearman, pooled)")
    print(f"{'='*70}")
    print("  IC > 0 → high basis_z (perp premium) predicts perp price DROP")
    ic_res = ic_analysis(basis_z, perp_prices, [3, 5, 7, 10])
    print(f"  {'Hold':>6} {'IC':>8} {'t-stat':>8} {'n':>6}  Verdict")
    print(f"  {'-'*50}")
    best_N, best_ic = MAX_HOLD, 0.0
    for N, r in ic_res.items():
        flag = "✓ PASS" if r["t"] > 1.5 and r["ic"] > 0 else ("✗ FAIL" if r["ic"] <= 0 else "~ WEAK")
        print(f"  {N:>5}d {r['ic']:>8.4f} {r['t']:>8.3f} {r['n']:>6}  {flag}")
        if r["ic"] > best_ic:
            best_ic, best_N = r["ic"], N

    # ── Step 5: Fetch perp OHLCV for SL simulation ────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 5 — FETCH HL CANDLEDATA FOR SL SIMULATION")
    print(f"{'='*70}")
    perp_ohlcv = load_perp_ohlcv(ASSETS)

    # ── Step 6: Backtest ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 6 — BACKTEST")
    print(f"{'='*70}")
    trades   = simulate_trades(basis_z, basis, perp_ohlcv, perp_prices)
    df_trades = (pd.DataFrame(trades)
                   .assign(entry_date=lambda d: pd.to_datetime(d["entry_date"]))
                 if trades else pd.DataFrame())
    m = trade_metrics(df_trades)

    print(f"\n  Overall ({MAX_HOLD}d max hold):")
    if m["n"] > 0:
        print(f"    Trades: {m['n']} total  ({m['n_per_year']:.1f}/yr)")
        print(f"    Win rate: {m['win_rate']:.1%}  "
              f"avg_win={m['avg_win_pct']:.2f}%  avg_loss={m['avg_loss_pct']:.2f}%")
        print(f"    Profit factor: {m['profit_factor']:.3f}  "
              f"SL rate: {m['sl_rate']:.1%}  MR exit rate: {m['mr_rate']:.1%}")
        print(f"    Avg hold: {m['avg_hold']:.1f}d  Trade Sharpe: {m['sharpe_trade']:.3f}")
    else:
        print("    No trades triggered.")

    # Direction breakdown
    if not df_trades.empty:
        print(f"\n  Direction breakdown:")
        print(f"  {'Direction':<12} {'n':>5} {'WinRate':>8} {'PF':>7} {'SL%':>7} "
              f"{'MR%':>6} {'AvgHold':>9}")
        print(f"  {'-'*57}")
        for direction in ["short", "long"]:
            sub_d = df_trades[df_trades["direction"] == direction]
            if sub_d.empty:
                print(f"  {direction:<12}    0  (no triggers)")
                continue
            m_d = trade_metrics(sub_d)
            print(f"  {direction:<12} {m_d['n']:>5} {m_d['win_rate']:>8.1%} "
                  f"{m_d['profit_factor']:>7.3f} {m_d['sl_rate']:>7.1%} "
                  f"{m_d['mr_rate']:>6.1%} {m_d['avg_hold']:>9.1f}d")

    # Asset breakdown
    if not df_trades.empty:
        print(f"\n  Asset breakdown:")
        print(f"  {'Asset':<8} {'n':>5} {'WinRate':>8} {'PF':>7} {'SL%':>7} {'MR%':>6}")
        print(f"  {'-'*42}")
        for sym in ASSETS:
            sub_a = df_trades[df_trades["asset"] == sym]
            if sub_a.empty:
                continue
            m_a = trade_metrics(sub_a)
            print(f"  {sym:<8} {m_a['n']:>5} {m_a['win_rate']:>8.1%} "
                  f"{m_a['profit_factor']:>7.3f} {m_a['sl_rate']:>7.1%} "
                  f"{m_a['mr_rate']:>6.1%}")

    # ── Step 7: Sub-period analysis ───────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 7 — SUB-PERIOD ANALYSIS")
    print(f"{'='*70}")
    if not df_trades.empty:
        sub_p = sub_period_metrics(df_trades)
        print(f"  {'Year':<8} {'n':>5} {'PF':>7} {'Mean%':>9}")
        print(f"  {'-'*30}")
        for yr, sp in sub_p.items():
            print(f"  {yr:<8} {sp['n']:>5} {sp['pf']:>7.2f} {sp['mean_pct']:>+9.3f}%")
    else:
        print("  No trades")

    # ── Step 8: Statistical test ──────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 8 — STATISTICAL TEST")
    print(f"{'='*70}")
    print("  Does basis_z predict 5-day perp return (signed for direction)?")
    for sym in ASSETS:
        if sym not in perp_prices.columns or sym not in basis_z.columns:
            continue
        perp  = perp_prices[sym].reindex(basis_z.index)
        z     = basis_z[sym]
        fwd5  = np.log(perp.shift(-5) / perp)
        cond_s = fwd5[(z > Z_ENTER)  & fwd5.notna()].dropna()
        cond_l = fwd5[(z < -Z_ENTER) & fwd5.notna()].dropna()
        uncond = fwd5.dropna()
        print(f"\n  {sym}:  unconditional 5d={uncond.mean()*100:+.3f}%  n={len(uncond)}")
        if len(cond_s) >= 3:
            t, p = ttest_1samp(cond_s, uncond.mean())
            print(f"    SHORT signal (z>{Z_ENTER}): mean={cond_s.mean()*100:+.3f}%  "
                  f"n={len(cond_s)}  t={t:.2f}  {'PASS (< uncond)' if t < -1.0 else 'FAIL'}")
        if len(cond_l) >= 3:
            t, p = ttest_1samp(cond_l, uncond.mean())
            print(f"    LONG  signal (z<-{Z_ENTER}): mean={cond_l.mean()*100:+.3f}%  "
                  f"n={len(cond_l)}  t={t:.2f}  {'PASS (> uncond)' if t > 1.0 else 'FAIL'}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("VERDICT")
    print(f"{'='*70}")
    pf       = m.get("profit_factor", 0)
    best_t   = ic_res.get(best_N, {}).get("t", 0)
    bear_pf  = sub_period_metrics(df_trades).get(2024, {}).get("pf", 0)  # earliest year

    if pf > 1.3 and best_t > 1.5:
        verdict = f"GO — PF={pf:.2f}>1.3  IC-t={best_t:.2f}>1.5"
    elif pf > 1.1 and best_t > 1.0:
        verdict = f"PROMISING — PF={pf:.2f}∈[1.1,1.3]  IC-t={best_t:.2f}>1.0"
    else:
        verdict = (f"SKIP — PF={pf:.2f}<1.1  or  IC-t={best_t:.2f}<1.0  "
                   f"(basis convergence not confirmed at HL perp granularity)")

    print(f"\n  {m.get('n',0)} total trades  PF={pf:.3f}  IC-t(best {best_N}d)={best_t:.2f}")
    print(f"\n  >>> {verdict}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    plot_results(basis, basis_z, ic_res, df_trades, FIG_OUT)
    elapsed = (_time.time() - t0) / 60
    print(f"\nTotal runtime: {elapsed:.1f} min")
    print(f"Output: {FIG_OUT}")
    print(f"Verdict: {verdict.split(' — ')[0]}")


if __name__ == "__main__":
    main()
