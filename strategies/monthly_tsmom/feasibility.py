"""
strategies/monthly_tsmom/feasibility.py

Signal 33 — Monthly TSMOM on 40 assets
Hypothesis: monthly rebalance (cost 2%/yr) + large universe (40 assets)
outperforms weekly TSMOM v3 (cost 8.8%/yr, 10 assets, known Sharpe 1.33).

Signal: equal-weight average of TSMOM at 1m/3m/6m lookbacks.
  All three normalized by vol_1m (common scaling factor).
  Long-only, top-10 by signal, vol-targeted at 15%.
  Monthly rebalance = first trading Monday of each month.

Key question: does cost reduction alone rescue the edge?
  Weekly cost: 52 × 0.17% × ~40% turnover = ~3.5%/yr actual
  Monthly cost: 12 × 0.17% × ~40% turnover = ~0.8%/yr actual
"""

import time as _time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore")

# ── Config ─────────────────────────────────────────────────────────────────────
START       = "2020-01-01"
END         = "2026-05-14"
TOP_N       = 40
LONG_N      = 10
VOL_TARGET  = 0.15
GROSS_CAP   = 0.90
COST_RT     = 0.0017
MIN_DAYS    = 365
VOL_FLOOR   = 0.01

HL_API  = "https://api.hyperliquid.xyz/info"
BIN_URL = "https://api.binance.com/api/v3/klines"
FIG_OUT = Path("strategies/monthly_tsmom/feasibility_results.png")

STABLECOINS = {
    "USDC","USDT","BUSD","DAI","TUSD","USDE","FDUSD",
    "SUSD","USDD","USDX","GHO","FRAX","LUSD","DOLA","USDP",
    "USDB","USDJ","CUSD","HUSD","GUSD",
}


# ── Universe ───────────────────────────────────────────────────────────────────

def fetch_hl_universe(top_n: int) -> list[str]:
    r = requests.post(HL_API, json={"type": "metaAndAssetCtxs"}, timeout=30)
    r.raise_for_status()
    data  = r.json()
    meta  = data[0]["universe"]
    ctxs  = data[1]
    assets = []
    for i, asset in enumerate(meta):
        name = asset["name"]
        if name.upper() in STABLECOINS:
            continue
        ctx = ctxs[i] if i < len(ctxs) else {}
        vol = float(ctx.get("dayNtlVlm", 0) or 0)
        assets.append({"coin": name, "vol": vol})
    assets.sort(key=lambda x: x["vol"], reverse=True)
    return [a["coin"] for a in assets[:top_n]]


# ── Data ───────────────────────────────────────────────────────────────────────

def fetch_binance_daily(symbol: str, start: str, end: str) -> pd.Series:
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
                return pd.Series(dtype=float)
            r.raise_for_status()
            rows = r.json()
        except Exception:
            return pd.Series(dtype=float)
        if not rows:
            break
        all_rows.extend(rows)
        last_open = int(rows[-1][0])
        cur = last_open + 86_400_000
        _time.sleep(0.04)
    if not all_rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(all_rows, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_vol","n_trades","taker_base","taker_quote","_"
    ])
    df["time"] = pd.to_datetime(df["open_time"].astype(np.int64), unit="ms", utc=True)
    s = df.set_index("time")["close"].astype(float).sort_index()
    return s[~s.index.duplicated(keep="last")]


def load_prices(coins: list[str], start: str, end: str) -> pd.DataFrame:
    prices = {}
    for coin in coins:
        sym = coin + "USDT"
        s   = fetch_binance_daily(sym, start, end)
        n   = len(s.dropna())
        if n >= MIN_DAYS:
            prices[coin] = s
            print(f"    {sym}: {n}d  OK")
        else:
            print(f"    {sym}: {n}d  SKIP")
    df = pd.DataFrame(prices)
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


# ── Rebalance Dates ────────────────────────────────────────────────────────────

def get_monthly_rebalance_dates(start: str, end: str,
                                 trading_days: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """First trading Monday of each calendar month."""
    dates = []
    cur = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")

    while cur <= end_ts:
        first = cur.replace(day=1)
        # Days until next Monday (Mon=0, so delta = (7 - weekday) % 7)
        delta = (7 - first.weekday()) % 7
        first_monday = first + pd.Timedelta(days=delta)
        # First trading day on or after first_monday
        valid = trading_days[trading_days >= first_monday]
        if not valid.empty:
            dates.append(valid[0])
        # Advance to next month
        if cur.month == 12:
            cur = pd.Timestamp(year=cur.year + 1, month=1, day=1, tz="UTC")
        else:
            cur = pd.Timestamp(year=cur.year, month=cur.month + 1, day=1, tz="UTC")

    return pd.DatetimeIndex(sorted(set(dates)))


# ── Signal ─────────────────────────────────────────────────────────────────────

def compute_signal_at(prices: pd.DataFrame, t_loc: int) -> pd.Series | None:
    """
    Monthly TSMOM signal at row index t_loc.
    Uses close through t_loc-1 (no look-ahead).
    Signal = mean([tanh(cumret_1m / (vol_1m × √21)),
                    tanh(cumret_3m / (vol_1m × √63)),
                    tanh(cumret_6m / (vol_1m × √126))])
    Clipped to [0,1] (long-only).
    """
    MIN_HIST = 128     # ~6m + buffer
    if t_loc < MIN_HIST:
        return None

    log_r = np.log(prices / prices.shift(1))

    # vol_1m: 1-month raw daily std (NOT annualized) for t-stat denominator
    # t-stat = cumret / (daily_std × sqrt(L)) — same convention as TSMOM v3
    vol_1m_tstat = log_r.iloc[t_loc - 21 : t_loc].std().clip(lower=1e-4)

    # Cumulative returns (close[t-1] vs close[t-1-L])
    p_now  = prices.iloc[t_loc - 1]
    p_1m   = prices.iloc[t_loc - 22]
    p_3m   = prices.iloc[t_loc - 64]
    p_6m   = prices.iloc[t_loc - 127]

    cumret_1m = np.log(p_now / p_1m)
    cumret_3m = np.log(p_now / p_3m)
    cumret_6m = np.log(p_now / p_6m)

    sig_1m = np.tanh(cumret_1m / (vol_1m_tstat * np.sqrt(21)))
    sig_3m = np.tanh(cumret_3m / (vol_1m_tstat * np.sqrt(63)))
    sig_6m = np.tanh(cumret_6m / (vol_1m_tstat * np.sqrt(126)))

    signal = ((sig_1m + sig_3m + sig_6m) / 3).clip(lower=0, upper=1)
    return signal.dropna()


def compute_weights_at(signal: pd.Series, vol_1m: pd.Series,
                        long_n: int = LONG_N,
                        vol_target: float = VOL_TARGET,
                        gross_cap: float = GROSS_CAP) -> pd.Series:
    """Top-long_n assets by signal, vol-targeted."""
    if signal is None or signal.empty:
        return pd.Series(dtype=float)
    top     = signal.nlargest(long_n)
    # weight = (vol_target / vol_1m).clip(0.1, 2.0) × signal
    w_ratio = (vol_target / vol_1m[top.index]).clip(lower=0.10, upper=2.0)
    weights = (w_ratio * top).dropna()
    gross   = weights.sum()
    if gross > gross_cap:
        weights *= gross_cap / gross
    return weights


# ── Backtest ───────────────────────────────────────────────────────────────────

def backtest_monthly(rebalance_dates: pd.DatetimeIndex,
                     weights_dict: dict,
                     prices_daily: pd.DataFrame,
                     cost_rt: float = COST_RT) -> tuple[pd.Series, pd.DataFrame]:
    """
    Monthly-hold backtest.
    Positions set at rebalance date, held until next rebalance.
    Cost charged only on rebalance days (turnover = weight change).
    Returns (daily_pnl, daily_weights).
    """
    log_r = np.log(prices_daily / prices_daily.shift(1)).fillna(0)
    all_cols = prices_daily.columns
    daily_weights = pd.DataFrame(0.0, index=prices_daily.index, columns=all_cols)

    rebal_list = sorted(rebalance_dates)
    for idx, rd in enumerate(rebal_list):
        next_rd = rebal_list[idx + 1] if idx + 1 < len(rebal_list) else prices_daily.index[-1]
        w = weights_dict.get(rd, pd.Series(dtype=float))
        mask = (prices_daily.index >= rd) & (prices_daily.index < next_rd)
        for coin, wt in w.items():
            if coin in daily_weights.columns:
                daily_weights.loc[mask, coin] = wt

    shifted  = daily_weights.shift(1).fillna(0)
    pnl_g    = (shifted * log_r).sum(axis=1)
    turnover = shifted.diff().abs().sum(axis=1)  # non-zero only on rebalance days
    cost     = turnover * cost_rt
    return (pnl_g - cost), daily_weights


def backtest_weekly_reference(prices: pd.DataFrame,
                               L: int = 28,
                               long_n: int = LONG_N,
                               vol_target: float = VOL_TARGET,
                               gross_cap: float = GROSS_CAP,
                               cost_rt: float = COST_RT) -> pd.Series:
    """TSMOM v3 weekly on the same universe for comparison."""
    log_r   = np.log(prices / prices.shift(1))
    cumret  = log_r.rolling(L).sum()
    vol     = log_r.rolling(L).std() * np.sqrt(252)
    sig     = np.tanh(cumret / (vol.clip(lower=1e-6) * np.sqrt(L)))
    sig     = sig.clip(lower=0, upper=1).resample("W-FRI").last()
    # Top-long_n weekly
    ranks_w = sig.rank(axis=1, ascending=False)
    mask_w  = (ranks_w <= long_n).astype(float)
    # Vol target
    vol_w   = log_r.rolling(L).std() * np.sqrt(252)
    vol_w   = vol_w.resample("W-FRI").last().clip(lower=VOL_FLOOR)
    raw_w   = mask_w.multiply((vol_target / vol_w).clip(0.10, 2.0))
    gross   = raw_w.sum(axis=1).replace(0, 1e-9)
    scale   = (gross_cap / gross).clip(upper=1.0)
    w_week  = raw_w.multiply(scale, axis=0)
    sig_d   = w_week.reindex(prices.index, method="ffill")
    log_d   = np.log(prices / prices.shift(1)).fillna(0)
    vol_d   = log_d.rolling(28, min_periods=14).std() * np.sqrt(252)
    # Actually just use the weekly weights as-is (forward-filled)
    shifted = sig_d.shift(1).fillna(0)
    pnl_g   = (shifted * log_d).sum(axis=1)
    turn    = shifted.diff().abs().sum(axis=1)
    return pnl_g - turn * cost_rt


# ── Metrics ────────────────────────────────────────────────────────────────────

def metrics(pnl: pd.Series, label: str = "") -> dict:
    ann = pnl.mean() * 252
    vol = pnl.std()  * np.sqrt(252)
    sh  = ann / vol if vol > 0 else 0.0
    cum = pnl.cumsum()
    dd  = (cum - cum.cummax()).min()
    # Sortino
    neg = pnl[pnl < 0]
    ds  = neg.std() * np.sqrt(252) if len(neg) > 10 else vol
    sor = ann / ds if ds > 0 else 0.0
    # Profit factor
    wins  = pnl[pnl > 0].sum()
    loss  = pnl[pnl < 0].sum()
    pf    = wins / (-loss) if loss < 0 else float("inf")
    return {
        "label": label, "sharpe": round(sh, 3), "sortino": round(sor, 3),
        "maxdd": round(dd * 100, 2), "annual_ret": round(ann * 100, 2),
        "profit_factor": round(pf, 3),
    }


def sub_period_sharpes(pnl: pd.Series) -> dict:
    out = {}
    for yr in sorted(pnl.index.year.unique()):
        s = pnl[pnl.index.year == yr]
        if len(s) < 30:
            continue
        v = s.std() * np.sqrt(252)
        out[yr] = round(s.mean() * 252 / v, 3) if v > 0 else 0.0
    return out


def walk_forward_sharpes(pnl: pd.Series, n_windows: int = 4) -> dict:
    total = len(pnl)
    wlen  = total // n_windows
    out   = {}
    for i in range(n_windows):
        s_i = i * wlen
        e_i = (i + 1) * wlen if i < n_windows - 1 else total
        w   = pnl.iloc[s_i:e_i]
        v   = w.std() * np.sqrt(252)
        sh  = round(w.mean() * 252 / v, 3) if v > 0 else 0.0
        lbl = f"{w.index[0].year}"
        out[lbl] = sh
    return out


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_results(results: dict, monthly_weights: pd.DataFrame, fig_path: Path) -> None:
    fig = plt.figure(figsize=(16, 12))
    gs  = gridspec.GridSpec(2, 2, hspace=0.38, wspace=0.30)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    palette = {"Monthly-40": "#4CAF50", "Weekly-40": "#FF9800"}

    # 1 — Equity curves
    for key, res in results.items():
        p = res["pnl"]
        m = res["m"]
        ax1.plot(p.index, p.cumsum() * 100,
                 label=f"{key}  S={m['sharpe']:.2f}  DD={m['maxdd']:.1f}%",
                 color=palette.get(key, "gray"), lw=1.5)
    ax1.set_title("Equity Curves (cum. log-ret %)", fontsize=11)
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.3)
    ax1.set_ylabel("%")

    # 2 — Sub-period Sharpe by year
    all_years = sorted({yr for res in results.values()
                        for yr in res.get("sub_sharpes", {})})
    x     = np.arange(len(all_years))
    width = 0.35
    for idx, (key, res) in enumerate(results.items()):
        vals = [res.get("sub_sharpes", {}).get(yr, 0) for yr in all_years]
        ax2.bar(x + idx * width, vals, width,
                label=key, color=palette.get(key, "gray"), alpha=0.85)
    ax2.axhline(0, color="black", lw=0.8)
    ax2.set_xticks(x + width / 2)
    ax2.set_xticklabels(all_years)
    ax2.set_title("Sub-Period Sharpe by Year", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.3, axis="y")

    # 3 — Rolling 12m Sharpe
    for key, res in results.items():
        p = res["pnl"]
        roll = p.rolling(252).apply(
            lambda x: (x.mean() * 252) / (x.std() * np.sqrt(252)) if x.std() > 0 else np.nan
        )
        ax3.plot(p.index, roll, label=key, color=palette.get(key, "gray"), lw=1.5)
    ax3.axhline(0, color="black", lw=0.8)
    ax3.axhline(1, color="gray",  lw=0.8, ls="--", alpha=0.6, label="Sharpe=1")
    ax3.set_title("Rolling 12m Sharpe", fontsize=11)
    ax3.legend(fontsize=9)
    ax3.grid(alpha=0.3)

    # 4 — Monthly active positions count
    monthly_res = results.get("Monthly-40", {})
    if "weights_dict" in monthly_res:
        wd = monthly_res["weights_dict"]
        n_pos = pd.Series(
            {rd: len(w) for rd, w in wd.items()},
            dtype=float
        )
        ax4.bar(n_pos.index, n_pos.values, color="#4CAF50", alpha=0.7, width=20)
        ax4.axhline(LONG_N, color="red", lw=1, ls="--", label=f"Target n={LONG_N}")
        ax4.set_title("Active Positions per Month", fontsize=11)
        ax4.legend(fontsize=9)
        ax4.grid(alpha=0.3, axis="y")
        ax4.set_ylabel("n positions")
    else:
        ax4.text(0.5, 0.5, "n/a", ha="center", va="center", transform=ax4.transAxes)

    fig.suptitle(
        f"Signal 33 — Monthly TSMOM on {TOP_N} Assets\n"
        "Mean of 1m/3m/6m lookbacks | First Monday rebalance | Long-only top-10",
        fontsize=12, y=0.99
    )
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {fig_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    t0 = _time.time()
    print("=" * 70)
    print("MONTHLY TSMOM — 40 Assets, 1m/3m/6m Average, Monthly Rebalance")
    print("Signal 33 — Strategy C candidate")
    print(f"Cost advantage: monthly 2%/yr vs weekly 8.8%/yr")
    print("=" * 70)

    # ── Step 1: Universe ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 1 — HL TOP-40 UNIVERSE (>$100M/day volume)")
    print(f"{'='*70}")
    coins = fetch_hl_universe(TOP_N)
    print(f"  {len(coins)} qualifying coins: {coins}")

    # ── Step 2: Prices ────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"STEP 2 — LOAD PRICES  ({START} → {END})")
    print(f"{'='*70}")
    prices = load_prices(coins, START, END)
    n_a = len(prices.columns)
    print(f"  Loaded: {n_a} assets × {len(prices)} days")

    # ── Step 3: Monthly rebalance dates ───────────────────────────────────────
    rebal_dates = get_monthly_rebalance_dates(START, END, prices.index)
    print(f"\n  Monthly rebalance dates: {len(rebal_dates)} months")
    print(f"  First 3: {list(rebal_dates[:3])}")

    # ── Step 4: Compute monthly signals ──────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 4 — MONTHLY SIGNAL COMPUTATION")
    print(f"{'='*70}")

    log_r = np.log(prices / prices.shift(1))
    weights_dict = {}
    signal_history = []

    for rd in rebal_dates:
        t_loc = prices.index.get_loc(rd)
        sig   = compute_signal_at(prices, t_loc)
        if sig is None or sig.empty:
            continue
        vol_1m = (log_r.iloc[t_loc - 21 : t_loc].std() * np.sqrt(252)).clip(lower=VOL_FLOOR)
        w      = compute_weights_at(sig, vol_1m)
        weights_dict[rd] = w
        signal_history.append({"date": rd, "n_assets": len(w), "gross": w.sum()})

    df_sig = pd.DataFrame(signal_history).set_index("date")
    print(f"  Signal computed for {len(weights_dict)} months")
    print(f"  Avg positions per month: {df_sig['n_assets'].mean():.1f}")
    print(f"  Avg gross exposure:      {df_sig['gross'].mean():.3f}")

    # Sample: first rebalance
    first_rd = list(weights_dict.keys())[0]
    print(f"\n  Sample ({first_rd.date()}):")
    for coin, wt in weights_dict[first_rd].items():
        print(f"    {coin}: {wt:.4f}")

    # ── Step 5: Backtest ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 5 — BACKTEST")
    print(f"{'='*70}")

    pnl_monthly, daily_w = backtest_monthly(
        pd.DatetimeIndex(list(weights_dict.keys())),
        weights_dict, prices
    )
    pnl_weekly = backtest_weekly_reference(prices)

    # Trim to same period
    common = pnl_monthly.index.intersection(pnl_weekly.index)
    pnl_m  = pnl_monthly[common]
    pnl_w  = pnl_weekly[common]

    m_monthly = metrics(pnl_m, "Monthly-40")
    m_weekly  = metrics(pnl_w, "Weekly-40")

    print(f"  {'Variant':<22} {'Sharpe':>7} {'Sortino':>8} {'MaxDD':>8} {'AnnRet':>8} {'PF':>6}")
    print(f"  {'-'*60}")
    print(f"  {'TSMOM v3 (known)':<22} {'1.33':>7} {'n/a':>8} {'-6.9%':>8} {'n/a':>8} {'n/a':>6}")
    for m in (m_monthly, m_weekly):
        print(f"  {m['label']:<22} {m['sharpe']:>7.3f} {m['sortino']:>8.3f} "
              f"{m['maxdd']:>7.1f}% {m['annual_ret']:>7.1f}% {m['profit_factor']:>6.3f}")

    # Cost breakdown
    monthly_cost = daily_w.shift(1).fillna(0).diff().abs().sum(axis=1)
    annual_cost_m = monthly_cost.mean() * 252 * COST_RT * 100
    print(f"\n  Monthly-40 actual annual cost drag: {annual_cost_m:.2f}%/yr")

    # Turnover per rebalance
    rebal_turnover = []
    for idx, rd in enumerate(sorted(weights_dict.keys())):
        if idx == 0:
            continue
        prev_rd = sorted(weights_dict.keys())[idx - 1]
        w_new = weights_dict[rd].reindex(prices.columns).fillna(0)
        w_old = weights_dict[prev_rd].reindex(prices.columns).fillna(0)
        rebal_turnover.append((w_new - w_old).abs().sum())
    print(f"  Avg turnover per rebalance: {np.mean(rebal_turnover):.4f} "
          f"({np.mean(rebal_turnover)*100:.1f}% of portfolio)")

    # ── Step 6: Sub-period analysis ───────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 6 — SUB-PERIOD SHARPE")
    print(f"{'='*70}")

    sub_m = sub_period_sharpes(pnl_m)
    sub_w = sub_period_sharpes(pnl_w)
    print(f"  {'Year':<8} {'Monthly-40':>12} {'Weekly-40':>12}")
    print(f"  {'-'*35}")
    for yr in sorted(set(sub_m) | set(sub_w)):
        tag = "  ← bear" if yr == 2022 else ""
        print(f"  {yr:<8} {sub_m.get(yr, 0):>+12.3f} {sub_w.get(yr, 0):>+12.3f}{tag}")

    # ── Step 7: Walk-forward ──────────────────────────────────────────────────
    wf_m = walk_forward_sharpes(pnl_m)
    wf_w = walk_forward_sharpes(pnl_w)
    print(f"\n{'='*70}")
    print("STEP 7 — WALK-FORWARD OOS WINDOWS")
    print(f"{'='*70}")
    print(f"  {'Window':<10} {'Monthly-40':>12} {'Weekly-40':>12}")
    print(f"  {'-'*35}")
    for wd in sorted(wf_m.keys()):
        print(f"  {wd:<10} {wf_m.get(wd, 0):>+12.3f} {wf_w.get(wd, 0):>+12.3f}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("VERDICT")
    print(f"{'='*70}")
    sh = m_monthly["sharpe"]
    dd = m_monthly["maxdd"]
    bear_ok = sub_m.get(2022, -99) > -0.5

    if sh >= 1.0 and dd > -15 and bear_ok:
        verdict = f"DEPLOY — Sharpe={sh:.3f} ≥ 1.0  MaxDD={dd:.1f}% ≤ 15%  2022 bear OK"
    elif sh >= 0.8:
        verdict = f"PROMISING — Sharpe={sh:.3f} ≥ 0.8; further refinement warranted"
    elif sh >= 0.6:
        verdict = f"PROMISING — Sharpe={sh:.3f} ≥ 0.6; consider larger universe or tuning"
    else:
        verdict = f"SKIP — Sharpe={sh:.3f} < 0.6 (monthly rebalance doesn't rescue edge)"

    print(f"\n  Monthly-40: Sharpe={sh:.3f}  MaxDD={dd:.1f}%  2022={sub_m.get(2022,'n/a')}")
    print(f"  Weekly-40:  Sharpe={m_weekly['sharpe']:.3f}  (same universe, weekly cost)")
    print(f"\n  >>> {verdict}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    results = {
        "Monthly-40": {"pnl": pnl_m, "m": m_monthly,
                        "sub_sharpes": sub_m, "weights_dict": weights_dict},
        "Weekly-40":  {"pnl": pnl_w, "m": m_weekly,
                        "sub_sharpes": sub_w},
    }
    plot_results(results, daily_w, FIG_OUT)

    elapsed = (_time.time() - t0) / 60
    print(f"\nTotal runtime: {elapsed:.1f} min")
    print(f"Verdict: {verdict.split(' — ')[0]}")


if __name__ == "__main__":
    main()
