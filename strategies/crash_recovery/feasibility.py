"""
strategies/crash_recovery/feasibility.py

Signal 34 — Crash Recovery Dip-Buying with Hard Stop-Loss
Hypothesis: large-cap crypto -8% in 3 days triggers forced liquidations
creating oversold conditions → mean-reversion snap-back within 5 days.
Different from MR attempts (6.2, 6.9, 6.11): event-triggered only,
hard stop-loss prevents blow-up, 5-day hold limits cost drag.

Assets: BTC, ETH, SOL, BNB, AVAX (5 most liquid, full price history)
Data: Binance daily OHLCV 2018-2026

Key test:
  Is mean(fwd_5d | crash) > 2 × mean(fwd_5d | unconditional) AND t-stat > 2.0?
  Threshold sensitivity: -5% to -15% in 3d, hold 3/5/7 days.
  Sub-period: 2022 bear market performance (most critical).
"""

import time as _time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore")

# ── Config ─────────────────────────────────────────────────────────────────────
START       = "2018-01-01"
END         = "2026-05-14"
ASSETS      = ["BTC", "ETH", "SOL", "BNB", "AVAX"]
DEFAULT_THR = -0.08     # -8% in 3 days
DEFAULT_HLD = 5         # 5-day hold
SL_PCT      = -0.05     # -5% stop-loss
VOL_MULT    = 2.5       # vol filter: vol_5d < vol_20d × VOL_MULT
POS_SIZE    = 0.02      # 2% of capital per trade
MAX_POS     = 3         # max concurrent positions
COST_RT     = 0.0017    # 0.17% round-trip

THRESHOLDS   = [-0.05, -0.08, -0.10, -0.15]
HOLD_PERIODS = [3, 5, 7]

BIN_URL = "https://api.binance.com/api/v3/klines"
FIG_OUT = Path("strategies/crash_recovery/feasibility_results.png")


# ── Data ───────────────────────────────────────────────────────────────────────

def fetch_binance_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Fetch daily OHLCV from Binance. Returns df with open/high/low/close/volume."""
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms   = int(pd.Timestamp(end,   tz="UTC").timestamp() * 1000)
    all_rows = []
    cur = start_ms
    while cur < end_ms:
        try:
            r = requests.get(BIN_URL,
                             params={"symbol": symbol, "interval": "1d",
                                     "startTime": cur, "limit": 1000},
                             timeout=15)
            if r.status_code == 400:
                return pd.DataFrame()
            r.raise_for_status()
            rows = r.json()
        except Exception:
            return pd.DataFrame()
        if not rows:
            break
        all_rows.extend(rows)
        last_open = int(rows[-1][0])
        cur = last_open + 86_400_000
        _time.sleep(0.04)
    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_vol","n_trades","taker_base","taker_quote","_"
    ])
    df["time"] = pd.to_datetime(df["open_time"].astype(np.int64), unit="ms", utc=True)
    df = (df.set_index("time")[["open","high","low","close","volume"]]
            .astype(float).sort_index())
    return df[~df.index.duplicated(keep="last")]


def load_all_ohlcv(assets: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    prices = {}
    for asset in assets:
        sym = asset + "USDT"
        df  = fetch_binance_ohlcv(sym, start, end)
        if not df.empty:
            prices[asset] = df
            print(f"    {sym}: {len(df)}d  OK ({df.index[0].date()} → {df.index[-1].date()})")
        else:
            print(f"    {sym}: SKIP")
    return prices


# ── Signal & Trade Simulation ──────────────────────────────────────────────────

def simulate_trades_for_config(prices_dict: dict[str, pd.DataFrame],
                                threshold: float,
                                hold_days: int,
                                sl_pct: float  = SL_PCT,
                                vol_mult: float = VOL_MULT,
                                cost_rt: float  = COST_RT) -> list[dict]:
    """
    For each asset, find all crash-signal days and simulate trades.
    Entry at close of signal day (simplified — avoids open price ambiguity).
    Exit: SL if low ≤ entry × (1+sl_pct) on any subsequent day;
          else close of day (entry_idx + hold_days).
    No look-ahead: signal uses only data known at close of T.
    Returns list of trade dicts.
    """
    all_trades = []
    cooldown_days = hold_days  # no re-entry while position open

    for asset, df in prices_dict.items():
        close   = df["close"]
        low     = df["low"]
        log_r   = np.log(close / close.shift(1))

        # 3-day return: log(close[T] / close[T-3]) -- uses close T-3 to close T
        # Signal fires at end of day T (known), entry at next day's open ≈ close[T]
        ret_3d  = np.log(close / close.shift(3))

        # Vol filter: 5d vol < 20d vol × vol_mult
        vol_5d  = log_r.rolling(5,  min_periods=3).std()
        vol_20d = log_r.rolling(20, min_periods=10).std()
        vol_ok  = vol_5d < vol_20d * vol_mult

        last_trade_exit = -999
        for i in range(3, len(close) - hold_days - 1):
            if i <= last_trade_exit:
                continue  # cooldown
            t     = close.index[i]
            # Signal: -8% in 3 days AND not in extreme vol spike
            if ret_3d.iloc[i] >= threshold:
                continue
            if not vol_ok.iloc[i]:
                continue

            # Entry price = close[i] (simplified; avoids open look-ahead)
            entry_price = close.iloc[i]
            if entry_price <= 0 or np.isnan(entry_price):
                continue
            sl_price    = entry_price * (1 + sl_pct)

            exit_price  = None
            exit_type   = "TIME"
            exit_idx    = i + hold_days

            for j in range(1, hold_days + 1):
                day_idx = i + j
                if day_idx >= len(close):
                    exit_idx = len(close) - 1
                    break
                if low.iloc[day_idx] <= sl_price:
                    exit_price = sl_price   # SL hit (worst-case exit)
                    exit_type  = "SL"
                    exit_idx   = day_idx
                    break

            if exit_price is None:
                exit_idx   = min(i + hold_days, len(close) - 1)
                exit_price = close.iloc[exit_idx]

            pnl_gross = np.log(exit_price / entry_price)
            pnl_net   = pnl_gross - cost_rt

            all_trades.append({
                "asset":       asset,
                "entry_date":  t,
                "exit_date":   close.index[exit_idx],
                "entry_price": entry_price,
                "exit_price":  exit_price,
                "pnl_gross":   round(pnl_gross, 6),
                "pnl_net":     round(pnl_net, 6),
                "exit_type":   exit_type,
                "ret_3d":      round(ret_3d.iloc[i], 4),
                "year":        t.year,
            })
            last_trade_exit = exit_idx

    return all_trades


def portfolio_pnl(trades: list[dict],
                  prices_dict: dict[str, pd.DataFrame],
                  pos_size: float = POS_SIZE) -> pd.Series:
    """
    Daily portfolio P&L from trade list.
    Each trade contributes pos_size × daily_return on each active day.
    """
    if not trades:
        return pd.Series(dtype=float)

    # Build a common daily index
    all_dates = sorted({d for df in prices_dict.values()
                        for d in df.index})
    date_idx  = {d: i for i, d in enumerate(all_dates)}
    pnl_arr   = np.zeros(len(all_dates))
    wgt_arr   = np.zeros(len(all_dates))

    for tr in trades:
        asset = tr["asset"]
        if asset not in prices_dict:
            continue
        df    = prices_dict[asset]
        close = df["close"]

        eid   = tr["entry_date"]
        xid   = tr["exit_date"]
        if eid not in close.index or xid not in close.index:
            continue

        ei = close.index.get_loc(eid)
        xi = close.index.get_loc(xid)

        for k in range(ei, xi):
            if k + 1 >= len(close):
                break
            day  = close.index[k]
            nday = close.index[k + 1]
            if day not in date_idx or nday not in date_idx:
                continue
            di = date_idx[day]
            # Check SL
            if tr["exit_type"] == "SL" and nday >= xid:
                daily_ret = np.log(tr["exit_price"] / close.iloc[k])
            else:
                daily_ret = np.log(close.iloc[k + 1] / close.iloc[k])
            pnl_arr[di] += pos_size * daily_ret
            wgt_arr[di] += pos_size

    series = pd.Series(pnl_arr, index=all_dates)
    return series


def trades_to_df(trades: list[dict]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["entry_date"] = pd.to_datetime(df["entry_date"], utc=True)
    df["exit_date"]  = pd.to_datetime(df["exit_date"],  utc=True)
    return df


# ── Statistical Test ───────────────────────────────────────────────────────────

def statistical_test(prices_dict: dict[str, pd.DataFrame],
                     threshold: float, hold_days: int) -> dict:
    """
    Compare: conditional mean return (post-crash) vs unconditional mean.
    Pooled across all assets.
    Returns: t_stat, p_value, conditional_mean, unconditional_mean, n_triggers.
    """
    all_cond  = []
    all_uncond = []

    for asset, df in prices_dict.items():
        close  = df["close"]
        log_r  = np.log(close / close.shift(1))
        ret_3d = np.log(close / close.shift(3))
        vol_5d  = log_r.rolling(5, min_periods=3).std()
        vol_20d = log_r.rolling(20, min_periods=10).std()

        # Forward return: sum of log_ret over [i+1, i+hold_days]
        fwd_ret = log_r.shift(-1).rolling(hold_days).sum().shift(-(hold_days-1))

        for i in range(3, len(close) - hold_days - 1):
            if np.isnan(fwd_ret.iloc[i]):
                continue
            r_fwd = fwd_ret.iloc[i]
            all_uncond.append(r_fwd)

            if ret_3d.iloc[i] < threshold:
                if vol_5d.iloc[i] < vol_20d.iloc[i] * VOL_MULT:
                    all_cond.append(r_fwd)

    if len(all_cond) < 5:
        return {"t_stat": 0, "p_value": 1, "conditional_mean": 0,
                "unconditional_mean": np.mean(all_uncond), "n_triggers": 0}

    uncond_mean = np.mean(all_uncond)
    cond_mean   = np.mean(all_cond)
    # One-sample t-test: is conditional mean > unconditional mean?
    t, p = stats.ttest_1samp(all_cond, uncond_mean if len(all_uncond) > 0 else 0)
    return {
        "t_stat": round(t, 3),
        "p_value": round(p, 4),
        "conditional_mean": round(cond_mean, 5),
        "unconditional_mean": round(uncond_mean, 5),
        "n_triggers": len(all_cond),
        "pass": cond_mean > 2 * uncond_mean and t > 2.0,
    }


# ── Metrics ────────────────────────────────────────────────────────────────────

def trade_metrics(trades_df: pd.DataFrame) -> dict:
    if trades_df.empty:
        return {"n": 0, "sharpe": 0, "profit_factor": 0, "win_rate": 0}
    pnl   = trades_df["pnl_net"]
    wins  = pnl[pnl > 0]
    loss  = pnl[pnl < 0]
    pf    = wins.sum() / (-loss.sum()) if len(loss) > 0 and loss.sum() < 0 else float("inf")
    wr    = len(wins) / len(pnl)
    n_yr  = len(pnl) / max(1, (trades_df["entry_date"].max() - trades_df["entry_date"].min()).days / 365)
    # Sharpe estimate from trade P&L
    sh    = (pnl.mean() * np.sqrt(n_yr)) / pnl.std() if pnl.std() > 0 else 0.0
    return {
        "n": len(pnl),
        "n_per_year": round(n_yr, 1),
        "win_rate": round(wr, 3),
        "avg_win": round(wins.mean() if len(wins) > 0 else 0, 5),
        "avg_loss": round(loss.mean() if len(loss) > 0 else 0, 5),
        "profit_factor": round(pf, 3),
        "sharpe_trade": round(sh, 3),
        "sl_rate": round((trades_df["exit_type"] == "SL").mean(), 3),
    }


def sub_period_metrics(trades_df: pd.DataFrame) -> dict:
    if trades_df.empty:
        return {}
    out = {}
    for yr in sorted(trades_df["year"].unique()):
        sub = trades_df[trades_df["year"] == yr]["pnl_net"]
        if len(sub) < 3:
            continue
        pf = (sub[sub > 0].sum() / (-sub[sub < 0].sum())
              if sub[sub < 0].sum() < 0 else float("inf"))
        out[yr] = {"n": len(sub), "pf": round(pf, 2), "mean": round(sub.mean(), 4)}
    return out


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_results(best_trades_df: pd.DataFrame,
                 grid_results:   dict,
                 stat_test:      dict,
                 prices_dict:    dict,
                 pnl_portfolio:  pd.Series,
                 fig_path:       Path) -> None:
    fig = plt.figure(figsize=(16, 12))
    gs  = gridspec.GridSpec(2, 2, hspace=0.40, wspace=0.30)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    # 1 — Portfolio equity curve (best config)
    if not pnl_portfolio.empty:
        cum = pnl_portfolio.cumsum() * 100
        ax1.plot(cum.index, cum.values, color="#2196F3", lw=1.5)
        m = trade_metrics(best_trades_df) if not best_trades_df.empty else {}
        title_str = (f"Portfolio Equity (2% per trade)\n"
                     f"n={m.get('n',0)}  PF={m.get('profit_factor','?'):.2f}  "
                     f"WR={m.get('win_rate',0):.1%}")
        ax1.set_title(title_str, fontsize=10)
        ax1.set_ylabel("Cum. log-ret %")
        ax1.grid(alpha=0.3)
        ax1.axhline(0, color="black", lw=0.8)

    # 2 — Trade P&L distribution (winner/loser histogram)
    if not best_trades_df.empty:
        pnl_vals = best_trades_df["pnl_net"].values * 100
        ax2.hist(pnl_vals, bins=30, color="#4CAF50", alpha=0.7, edgecolor="white")
        ax2.axvline(0, color="red", lw=1.5, ls="--")
        ax2.axvline(pnl_vals.mean(), color="blue", lw=1.5, ls="-", label=f"mean={pnl_vals.mean():.2f}%")
        sl_pct_actual = (best_trades_df["exit_type"] == "SL").mean()
        ax2.set_title(f"Trade P&L Distribution\nSL rate={sl_pct_actual:.1%}", fontsize=10)
        ax2.legend(fontsize=9)
        ax2.grid(alpha=0.3)
        ax2.set_xlabel("P&L %")

    # 3 — Threshold sensitivity heat map (Profit Factor)
    thresholds   = sorted({k[0] for k in grid_results})
    hold_periods = sorted({k[1] for k in grid_results})
    pf_matrix    = np.full((len(thresholds), len(hold_periods)), np.nan)
    for (thr, hld), res in grid_results.items():
        i = thresholds.index(thr)
        j = hold_periods.index(hld)
        pf_matrix[i, j] = res.get("profit_factor", np.nan)
    im = ax3.imshow(pf_matrix, aspect="auto", cmap="RdYlGn",
                    vmin=0.8, vmax=1.5, interpolation="nearest")
    ax3.set_xticks(range(len(hold_periods)))
    ax3.set_xticklabels([f"{h}d" for h in hold_periods])
    ax3.set_yticks(range(len(thresholds)))
    ax3.set_yticklabels([f"{t*100:.0f}%" for t in thresholds])
    ax3.set_xlabel("Hold period")
    ax3.set_ylabel("Crash threshold")
    ax3.set_title("Profit Factor: threshold × hold_period", fontsize=10)
    plt.colorbar(im, ax=ax3)
    for i in range(len(thresholds)):
        for j in range(len(hold_periods)):
            v = pf_matrix[i, j]
            if not np.isnan(v):
                ax3.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9)

    # 4 — Post-crash return distribution vs unconditional
    if not best_trades_df.empty and prices_dict:
        # Collect post-crash fwd returns
        cond_rets   = best_trades_df["pnl_gross"].values * 100
        # Unconditional hold_days fwd returns (sample)
        uncond_rets = []
        for asset, df in prices_dict.items():
            close = df["close"]
            log_r = np.log(close / close.shift(1))
            fwd   = log_r.shift(-1).rolling(DEFAULT_HLD).sum().shift(-(DEFAULT_HLD-1)).dropna()
            uncond_rets.extend(fwd.values * 100)
        uncond_rets = np.array(uncond_rets)
        ax4.hist(uncond_rets, bins=60, alpha=0.5, color="gray",
                 density=True, label=f"Unconditional (n={len(uncond_rets):,})")
        ax4.hist(cond_rets,   bins=20, alpha=0.7, color="#F44336",
                 density=True, label=f"Post-crash (n={len(cond_rets)})")
        ax4.axvline(np.mean(cond_rets), color="#F44336", lw=2, ls="--",
                    label=f"Crash mean={np.mean(cond_rets):.1f}%")
        ax4.axvline(np.mean(uncond_rets), color="gray", lw=2, ls="--",
                    label=f"Uncond mean={np.mean(uncond_rets):.1f}%")
        t_stat = stat_test.get("t_stat", 0)
        ax4.set_title(f"Post-Crash vs Unconditional Returns\nt-stat={t_stat:.2f}", fontsize=10)
        ax4.legend(fontsize=8)
        ax4.grid(alpha=0.3)
        ax4.set_xlabel(f"{DEFAULT_HLD}-day forward return %")

    fig.suptitle(
        f"Signal 34 — Crash Recovery: >{abs(DEFAULT_THR)*100:.0f}% drop in 3d → "
        f"{DEFAULT_HLD}d hold + {abs(SL_PCT)*100:.0f}% SL\n"
        f"Assets: {', '.join(ASSETS)} | 2% per trade | {START}→{END}",
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
    print("CRASH RECOVERY — Dip-Buying with Hard Stop-Loss")
    print("Signal 34 — Strategy C candidate")
    print(f"Signal: <{abs(DEFAULT_THR)*100:.0f}% in 3d + vol filter → "
          f"{DEFAULT_HLD}d hold + {abs(SL_PCT)*100:.0f}% SL")
    print(f"Assets: {', '.join(ASSETS)}")
    print("=" * 70)

    # ── Step 1: Data ──────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"STEP 1 — LOAD OHLCV ({START} → {END})")
    print(f"{'='*70}")
    prices = load_all_ohlcv(ASSETS, START, END)
    print(f"  Loaded {len(prices)} assets")

    # ── Step 2: Threshold sensitivity grid ───────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 2 — THRESHOLD SENSITIVITY GRID")
    print(f"{'='*70}")
    print(f"  {'Threshold':>12} {'Hold':>6} {'n_trades':>9} {'n/yr':>7} "
          f"{'WinRate':>9} {'PF':>7} {'SL_rt':>8} {'t-stat':>8}")
    print(f"  {'-'*75}")

    grid_results = {}
    for thr in THRESHOLDS:
        for hld in HOLD_PERIODS:
            trades = simulate_trades_for_config(prices, thr, hld)
            df     = trades_to_df(trades)
            m      = trade_metrics(df)
            st     = statistical_test(prices, thr, hld)
            grid_results[(thr, hld)] = {**m, "t_stat": st["t_stat"],
                                         "cond_mean": st["conditional_mean"],
                                         "uncond_mean": st["unconditional_mean"]}
            pass_flag = "✓" if st["pass"] else " "
            print(f"  {thr*100:>11.0f}% {hld:>6}d {m['n']:>9} {m['n_per_year']:>7.1f} "
                  f"{m['win_rate']:>9.1%} {m['profit_factor']:>7.2f} "
                  f"{m['sl_rate']:>8.1%} {st['t_stat']:>8.2f} {pass_flag}")

    # ── Step 3: Best configuration ────────────────────────────────────────────
    # Best by profit factor with at least 30 total trades
    best_key = max(
        (k for k, v in grid_results.items() if v["n"] >= 30),
        key=lambda k: grid_results[k]["profit_factor"],
        default=(DEFAULT_THR, DEFAULT_HLD)
    )
    best_thr, best_hld = best_key
    print(f"\n  Best config: threshold={best_thr*100:.0f}%  hold={best_hld}d  "
          f"PF={grid_results[best_key]['profit_factor']:.3f}")

    # ── Step 4: Detailed analysis of best config + default config ─────────────
    print(f"\n{'='*70}")
    print(f"STEP 3 — DETAILED ANALYSIS (default: {DEFAULT_THR*100:.0f}%/{DEFAULT_HLD}d  "
          f"| best: {best_thr*100:.0f}%/{best_hld}d)")
    print(f"{'='*70}")

    for label, thr, hld in [("Default", DEFAULT_THR, DEFAULT_HLD),
                              ("Best",    best_thr,    best_hld)]:
        trades = simulate_trades_for_config(prices, thr, hld)
        df     = trades_to_df(trades)
        m      = trade_metrics(df)
        st     = statistical_test(prices, thr, hld)
        sub    = sub_period_metrics(df)

        print(f"\n  ── {label} ({thr*100:.0f}%/{hld}d) ──────────────────────────────────")
        print(f"  Trades: {m['n']} total  ({m['n_per_year']:.1f}/yr)")
        print(f"  Win rate: {m['win_rate']:.1%}  avg_win={m['avg_win']*100:.2f}%  "
              f"avg_loss={m['avg_loss']*100:.2f}%")
        print(f"  Profit factor: {m['profit_factor']:.3f}  SL rate: {m['sl_rate']:.1%}")
        print(f"  Trade Sharpe: {m['sharpe_trade']:.3f}")
        print(f"\n  Statistical test (fwd {hld}d returns):")
        print(f"    Post-crash mean: {st['conditional_mean']*100:.3f}%  "
              f"(n={st['n_triggers']})")
        print(f"    Unconditional:   {st['unconditional_mean']*100:.3f}%")
        ratio = (st['conditional_mean'] / st['unconditional_mean']
                 if st['unconditional_mean'] > 0 else 0)
        print(f"    Ratio cond/uncond: {ratio:.2f}x  (pass if > 2.0×)")
        print(f"    t-stat: {st['t_stat']:.2f}  p={st['p_value']:.4f}  "
              f"{'PASS' if st['pass'] else 'FAIL'}")

        print(f"\n  Sub-period breakdown:")
        for yr, sp in sub.items():
            tag = "  ← bear" if yr == 2022 else ""
            print(f"    {yr}: n={sp['n']:>2}  PF={sp['pf']:.2f}  "
                  f"mean={sp['mean']*100:+.2f}%{tag}")

    # ── Step 5: Asset breakdown ────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 4 — ASSET BREAKDOWN (default config)")
    print(f"{'='*70}")
    default_trades = simulate_trades_for_config(prices, DEFAULT_THR, DEFAULT_HLD)
    df_default = trades_to_df(default_trades)
    if not df_default.empty:
        print(f"  {'Asset':<8} {'n':>5} {'WinRate':>9} {'PF':>7} {'SL_rt':>8}")
        print(f"  {'-'*40}")
        for asset in ASSETS:
            sub_a = df_default[df_default["asset"] == asset]
            if sub_a.empty:
                continue
            m_a = trade_metrics(sub_a)
            print(f"  {asset:<8} {m_a['n']:>5} {m_a['win_rate']:>9.1%} "
                  f"{m_a['profit_factor']:>7.2f} {m_a['sl_rate']:>8.1%}")

    # ── Step 6: Walk-forward (3 windows) ──────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 5 — WALK-FORWARD (3 windows, default config)")
    print(f"{'='*70}")
    if not df_default.empty:
        min_y = df_default["entry_date"].min().year
        max_y = df_default["entry_date"].max().year
        years = list(range(min_y, max_y + 1))
        n_win = 3
        win_len = len(years) // n_win
        print(f"  {'Window':<15} {'n':>5} {'PF':>7} {'t-stat':>8}")
        print(f"  {'-'*38}")
        for i in range(n_win):
            ys = years[i * win_len:(i + 1) * win_len]
            if not ys:
                continue
            sub_wf = df_default[df_default["year"].isin(ys)]
            if sub_wf.empty:
                continue
            m_wf = trade_metrics(sub_wf)
            st_wf = statistical_test(
                {a: prices[a] for a in ASSETS if a in prices},
                DEFAULT_THR, DEFAULT_HLD
            )
            print(f"  {ys[0]}-{ys[-1]:<10} {m_wf['n']:>5} {m_wf['profit_factor']:>7.2f} "
                  f"{st_wf['t_stat']:>8.2f}")

    # ── Portfolio P&L ─────────────────────────────────────────────────────────
    pnl_port = portfolio_pnl(default_trades, prices)
    if not pnl_port.empty:
        active_days = pnl_port[pnl_port != 0]
        if len(active_days) > 10:
            v_ann  = active_days.std() * np.sqrt(252)
            sh_act = active_days.mean() * 252 / v_ann if v_ann > 0 else 0
            sh_all = pnl_port.mean() * 252 / (pnl_port.std() * np.sqrt(252))
            cum_ret = pnl_port.sum()
            print(f"\n  Portfolio (2% per trade):")
            print(f"    Cumulative return: {cum_ret*100:.1f}%")
            print(f"    Full-period Sharpe (incl cash drag): {sh_all:.3f}")
            print(f"    Active-days Sharpe ({len(active_days)}d active): {sh_act:.3f}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("VERDICT")
    print(f"{'='*70}")

    best_m  = grid_results.get(best_key, {})
    best_st = statistical_test(prices, best_thr, best_hld)
    pf      = best_m.get("profit_factor", 0)
    t_stat  = best_st.get("t_stat", 0)
    bear_pf = sub_period_metrics(
        trades_to_df(simulate_trades_for_config(prices, best_thr, best_hld))
    ).get(2022, {}).get("pf", 0)

    if pf > 1.3 and t_stat > 2.0 and bear_pf > 1.0:
        verdict = f"GO — PF={pf:.2f}>1.3  t={t_stat:.2f}>2.0  2022 bear PF={bear_pf:.2f}>1.0"
    elif pf > 1.1 and t_stat > 1.5:
        verdict = f"PROMISING — PF={pf:.2f}∈[1.1,1.3]  t={t_stat:.2f}>1.5"
    else:
        verdict = f"SKIP — PF={pf:.2f}<1.1  or  t={t_stat:.2f}<1.5  (no statistical edge)"

    print(f"\n  Best config ({best_thr*100:.0f}%/{best_hld}d):")
    print(f"    PF={pf:.3f}  t-stat={t_stat:.2f}  2022 bear PF={bear_pf:.2f}")
    print(f"\n  >>> {verdict}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    best_trades = simulate_trades_for_config(prices, best_thr, best_hld)
    plot_results(
        best_trades_df  = trades_to_df(best_trades),
        grid_results    = grid_results,
        stat_test       = best_st,
        prices_dict     = prices,
        pnl_portfolio   = pnl_port,
        fig_path        = FIG_OUT,
    )

    elapsed = (_time.time() - t0) / 60
    print(f"\nTotal runtime: {elapsed:.1f} min")
    print(f"Output: {FIG_OUT}")
    print(f"Verdict: {verdict.split(' — ')[0]}")


if __name__ == "__main__":
    main()
