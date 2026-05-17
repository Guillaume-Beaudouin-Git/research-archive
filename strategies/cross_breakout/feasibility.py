"""
strategies/cross_breakout/feasibility.py

Signal 32 — Cross-Sectional Breakout (Robot Wealth approach)
Source: Robot Wealth (2024) — breakout NEGATIVELY correlated with carry
Hypothesis: A CS breakout strategy that is anti-correlated with Strategy B (carry)
would genuinely diversify the A+B portfolio even with moderate positive correlation
to Strategy A (TSMOM v3).

Key difference from our Donchian attempt (6.16, corr 0.675 with TSMOM):
  Donchian was long-only on same 10 assets → inherited beta_crypto
  CS Breakout is market-neutral (long top-N, short bottom-N) → no beta_crypto

Signal:
  breakout_score[i,T] = close[i,T] / rolling_max_21d(close[i,T-21:T-1]) - 1
                      = normalized distance above past 21d high
  Long:  top-5 by score  (recent strength, near/above 21d high)
  Short: bottom-5 by score (recent weakness, far below 21d high)

Critical tests:
  1. Long-leg vs short-leg decomposition
     → if short_leg Sharpe < -0.5: same failure as 6.3; take long-only
     → if short_leg Sharpe > -0.3: L/S genuinely works
  2. corr(breakout, carry) — Robot Wealth predicts NEGATIVE
     → if < -0.1: genuine diversifier, compute A+B+C
  3. corr(breakout, TSMOM) — expected moderate positive (~0.3-0.5)
  4. 2022 bear market: positive Sharpe = true edge, not bull beta
  5. A+B+C Sharpe vs 2.61 baseline
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
START        = "2021-01-01"
END          = "2026-05-14"
UNIVERSE_N   = 20          # top-20 HL perps by volume
LONG_N       = 5           # long top-N
SHORT_N      = 5           # short bottom-N
VOL_LONG     = 0.12        # vol target per long position
VOL_SHORT    = 0.08        # vol target per short position (tighter)
GROSS_CAP    = 0.90
COST_RT      = 0.0017
LOOKBACK_BR  = 21          # 21d high for breakout score
MIN_DAYS     = 365
TSMOM_L      = 28          # TSMOM baseline lookback

HL_API  = "https://api.hyperliquid.xyz/info"
BIN_URL = "https://api.binance.com/api/v3/klines"
FIG_OUT = Path("strategies/cross_breakout/feasibility_results.png")

STABLECOINS = {
    "USDC", "USDT", "BUSD", "DAI", "TUSD", "USDE", "FDUSD",
    "SUSD", "USDD", "USDX", "GHO", "FRAX", "LUSD", "DOLA", "USDP",
    "USDB", "USDJ", "CUSD", "HUSD", "GUSD",
}


# ── Universe ───────────────────────────────────────────────────────────────────

def fetch_hl_universe(top_n: int) -> list[str]:
    r = requests.post(HL_API, json={"type": "metaAndAssetCtxs"}, timeout=30)
    r.raise_for_status()
    data = r.json()
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


# ── Signal ─────────────────────────────────────────────────────────────────────

def compute_breakout_signal(prices: pd.DataFrame,
                             lookback: int = LOOKBACK_BR) -> pd.DataFrame:
    """
    Breakout score: close[T] / rolling_max(close[T-lookback:T-1]) - 1
    Positive = above recent high (strength), negative = below (weakness).
    Returns weekly (W-FRI) signal matrix.
    """
    # Past lookback-day max (shift to exclude current price from rolling max)
    past_max = prices.shift(1).rolling(lookback, min_periods=10).max()
    score    = prices / past_max - 1
    return score.resample("W-FRI").last()


def compute_tsmom_signal(prices: pd.DataFrame, L: int = TSMOM_L) -> pd.DataFrame:
    """TSMOM v3: tanh(cumret_L / (vol_L × √L)), long-only, weekly."""
    log_r  = np.log(prices / prices.shift(1))
    cumret = log_r.rolling(L).sum()
    vol    = log_r.rolling(L).std() * np.sqrt(252)
    sig    = np.tanh(cumret / (vol.clip(lower=1e-6) * np.sqrt(L)))
    return sig.clip(lower=0, upper=1).resample("W-FRI").last()


# ── Backtest ───────────────────────────────────────────────────────────────────

def backtest_ls(signal_weekly: pd.DataFrame,
                prices_daily:  pd.DataFrame,
                long_n:   int   = LONG_N,
                short_n:  int   = SHORT_N,
                vol_long: float = VOL_LONG,
                vol_short:float = VOL_SHORT,
                gross_cap:float = GROSS_CAP,
                cost_rt:  float = COST_RT) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    CS long-short backtest.
    Long top-long_n by score (vol-targeted at vol_long each).
    Short bottom-short_n by score (vol-targeted at vol_short each, positive exposure).
    Returns (total_pnl, long_pnl, short_pnl) as daily net log-ret series.
    """
    common    = signal_weekly.columns.intersection(prices_daily.columns)
    sig_w     = signal_weekly[common]
    p         = prices_daily[common]
    n_assets  = len(common)

    log_r  = np.log(p / p.shift(1)).fillna(0)
    vol_d  = log_r.rolling(28, min_periods=14).std() * np.sqrt(252)
    vol_d  = vol_d.clip(lower=0.05)

    # Forward-fill weekly signal
    sig_d  = sig_w.reindex(p.index, method="ffill")

    # Cross-sectional ranks at each day
    ranks       = sig_d.rank(axis=1, ascending=True)      # 1 = weakest
    long_mask   = (ranks > (n_assets - long_n)).astype(float)   # top-long_n
    short_mask  = (ranks <= short_n).astype(float)              # bottom-short_n

    # Vol-targeted raw weights
    w_long  =  long_mask.divide(vol_d)  * vol_long
    w_short = -short_mask.divide(vol_d) * vol_short   # negative = short

    # Normalize gross exposure
    gross_l = w_long.abs().sum(axis=1).replace(0, 1e-9)
    gross_s = w_short.abs().sum(axis=1).replace(0, 1e-9)
    gross   = (w_long.abs() + w_short.abs()).sum(axis=1).replace(0, 1e-9)
    scale   = (gross_cap / gross).clip(upper=1.0)

    w_long  = w_long.multiply(scale, axis=0)
    w_short = w_short.multiply(scale, axis=0)
    w_total = w_long + w_short

    # Lag 1 day
    wl_s  = w_long.shift(1).fillna(0)
    ws_s  = w_short.shift(1).fillna(0)
    wt_s  = w_total.shift(1).fillna(0)

    # Gross P&L per leg
    pnl_lg = (wl_s  * log_r).sum(axis=1)
    pnl_sh = (ws_s  * log_r).sum(axis=1)
    pnl_tt = (wt_s  * log_r).sum(axis=1)

    # Transaction costs
    def _cost(w):
        return w.diff().abs().sum(axis=1) * cost_rt

    return (pnl_tt - _cost(wt_s),
            pnl_lg - _cost(wl_s),
            pnl_sh - _cost(ws_s))


def backtest_longonly(signal_weekly: pd.DataFrame,
                      prices_daily:  pd.DataFrame,
                      long_n:   int   = LONG_N,
                      vol_each: float = VOL_LONG,
                      gross_cap:float = GROSS_CAP,
                      cost_rt:  float = COST_RT) -> pd.Series:
    """Long-only version: top-long_n assets only."""
    common   = signal_weekly.columns.intersection(prices_daily.columns)
    sig_w    = signal_weekly[common]
    p        = prices_daily[common]
    n_assets = len(common)

    log_r = np.log(p / p.shift(1)).fillna(0)
    vol_d = log_r.rolling(28, min_periods=14).std() * np.sqrt(252)
    vol_d = vol_d.clip(lower=0.05)

    sig_d  = sig_w.reindex(p.index, method="ffill")
    ranks  = sig_d.rank(axis=1, ascending=True)
    mask   = (ranks > (n_assets - long_n)).astype(float)

    raw    = mask.divide(vol_d) * vol_each
    gross  = raw.abs().sum(axis=1).replace(0, 1e-9)
    scale  = (gross_cap / gross).clip(upper=1.0)
    weights = raw.multiply(scale, axis=0)

    shifted  = weights.shift(1).fillna(0)
    pnl_g    = (shifted * log_r).sum(axis=1)
    cost     = shifted.diff().abs().sum(axis=1) * cost_rt
    return pnl_g - cost


# ── Metrics ────────────────────────────────────────────────────────────────────

def metrics(pnl: pd.Series) -> dict:
    ann = pnl.mean() * 252
    vol = pnl.std()  * np.sqrt(252)
    sh  = ann / vol if vol > 0 else 0.0
    cum = pnl.cumsum()
    dd  = (cum - cum.cummax()).min()
    return {"sharpe": round(sh, 3),
            "annual_ret": round(ann * 100, 2),
            "maxdd": round(dd * 100, 2)}


def sub_period_sharpes(pnl: pd.Series) -> dict:
    out = {}
    for yr in sorted(pnl.index.year.unique()):
        s = pnl[pnl.index.year == yr]
        if len(s) < 50:
            continue
        v = s.std() * np.sqrt(252)
        out[yr] = round(s.mean() * 252 / v, 3) if v > 0 else 0.0
    return out


# ── Carry proxy ────────────────────────────────────────────────────────────────

def fetch_binance_funding(symbol: str, start_ms: int) -> pd.Series:
    url      = "https://fapi.binance.com/fapi/v1/fundingRate"
    all_rows = []
    cur      = start_ms
    now_ms   = int(_time.time() * 1000)
    while cur < now_ms:
        try:
            r = requests.get(url,
                             params={"symbol": symbol, "startTime": cur, "limit": 1000},
                             timeout=15)
            if r.status_code != 200:
                break
            rows = r.json()
        except Exception:
            break
        if not rows:
            break
        all_rows.extend(rows)
        last_ts = int(rows[-1]["fundingTime"])
        if last_ts <= cur:
            break
        cur = last_ts + 1
        _time.sleep(0.1)
    if not all_rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(all_rows)
    df["time"] = pd.to_datetime(df["fundingTime"].astype(np.int64), unit="ms", utc=True)
    df["rate"] = df["fundingRate"].astype(float)
    s = df.set_index("time")["rate"].sort_index()
    return s[~s.index.duplicated(keep="last")]


def build_carry_proxy(start: str = START) -> pd.Series:
    """Daily funding carry = mean(BTC+ETH 8h payments summed per day)."""
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    btc_f = fetch_binance_funding("BTCUSDT", start_ms)
    eth_f = fetch_binance_funding("ETHUSDT", start_ms)
    if btc_f.empty and eth_f.empty:
        return pd.Series(dtype=float)
    combined = pd.concat([btc_f.rename("BTC"), eth_f.rename("ETH")],
                         axis=1, join="outer").mean(axis=1)
    return combined.resample("D").sum()


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_results(results: dict, carry: pd.Series, fig_path: Path) -> None:
    fig = plt.figure(figsize=(16, 12))
    gs  = gridspec.GridSpec(2, 2, hspace=0.38, wspace=0.30)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    # 1 — Equity curves: all legs
    palette = {
        "L/S total":   "#2196F3",
        "Long leg":    "#4CAF50",
        "Short leg":   "#F44336",
        "Long-only":   "#FF9800",
        "TSMOM proxy": "#9C27B0",
    }
    for label, pnl in results.get("legs", {}).items():
        m = metrics(pnl)
        ax1.plot(pnl.index, pnl.cumsum() * 100,
                 label=f"{label}  S={m['sharpe']:.2f}",
                 color=palette.get(label, "gray"))
    ax1.set_title("Equity Curves (cum. log-ret %)", fontsize=11)
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)
    ax1.set_ylabel("%")

    # 2 — Rolling correlation: breakout vs TSMOM and vs carry
    pnl_ls = results["legs"]["L/S total"]
    roll52 = 252

    if "tsmom_pnl" in results:
        pnl_ts  = results["tsmom_pnl"]
        idx_ts  = pnl_ls.index.intersection(pnl_ts.index)
        if len(idx_ts) > roll52:
            df_ts = pd.concat([pnl_ls[idx_ts].rename("LS"),
                                pnl_ts[idx_ts].rename("TS")], axis=1)
            roll_corr_ts = df_ts["LS"].rolling(roll52).corr(df_ts["TS"])
            ax2.plot(roll_corr_ts.index, roll_corr_ts,
                     label="corr(breakout, TSMOM)", color="#9C27B0")

    if not carry.empty:
        idx_ca = pnl_ls.index.intersection(carry.index)
        if len(idx_ca) > roll52:
            df_ca = pd.concat([pnl_ls[idx_ca].rename("LS"),
                                carry[idx_ca].rename("carry")], axis=1)
            roll_corr_ca = df_ca["LS"].rolling(roll52).corr(df_ca["carry"])
            ax2.plot(roll_corr_ca.index, roll_corr_ca,
                     label="corr(breakout, carry)", color="#FF5722")

    ax2.axhline(0, color="black", lw=0.8)
    ax2.axhline(-0.1, color="red", lw=0.8, ls="--", alpha=0.5, label="−0.1 threshold")
    ax2.set_title("Rolling 52w Correlation", fontsize=11)
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)
    ax2.set_ylim(-1, 1)

    # 3 — Sub-period Sharpe by year
    strategies_sub = {
        "L/S total":  results.get("sub_ls",   {}),
        "Long-only":  results.get("sub_lo",   {}),
        "TSMOM proxy":results.get("sub_tsmom",{}),
    }
    all_years = sorted({yr for d in strategies_sub.values() for yr in d.keys()})
    x     = np.arange(len(all_years))
    width = 0.25
    for idx, (label, sub) in enumerate(strategies_sub.items()):
        vals = [sub.get(yr, 0) for yr in all_years]
        ax3.bar(x + idx * width, vals, width,
                label=label, color=palette.get(label, "gray"), alpha=0.85)
    ax3.axhline(0, color="black", lw=0.8)
    ax3.set_xticks(x + width)
    ax3.set_xticklabels(all_years)
    ax3.set_title("Sub-Period Sharpe by Year", fontsize=11)
    ax3.legend(fontsize=8)
    ax3.grid(alpha=0.3, axis="y")

    # 4 — Rolling 52w Sharpe (L/S vs long-only)
    for label in ("L/S total", "Long-only"):
        pnl = results["legs"].get(label)
        if pnl is None:
            continue
        roll = pnl.rolling(252).apply(
            lambda x: (x.mean() * 252) / (x.std() * np.sqrt(252)) if x.std() > 0 else np.nan
        )
        ax4.plot(pnl.index, roll, label=label, color=palette.get(label, "gray"))
    ax4.axhline(0, color="black", lw=0.8)
    ax4.axhline(0.8, color="gray", lw=0.8, ls="--", alpha=0.6, label="0.8 target")
    ax4.set_title("Rolling 52w Sharpe", fontsize=11)
    ax4.legend(fontsize=8)
    ax4.grid(alpha=0.3)

    fig.suptitle(
        "Signal 32 — Cross-Sectional Breakout (Robot Wealth approach)\n"
        f"Long top-{LONG_N} / Short bottom-{SHORT_N} by 21d breakout score | "
        f"{UNIVERSE_N}-asset HL universe",
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
    print("CROSS-SECTIONAL BREAKOUT — Robot Wealth approach")
    print("Signal 32 — Strategy C candidate")
    print(f"Universe: top-{UNIVERSE_N} HL perps | Long top-{LONG_N} / Short bottom-{SHORT_N}")
    print(f"Key test: corr(breakout, carry) — Robot Wealth predicts NEGATIVE")
    print("=" * 70)

    # ── Step 1: Universe ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 1 — HL UNIVERSE")
    print(f"{'='*70}")
    top20 = fetch_hl_universe(UNIVERSE_N)
    print(f"  Top-{UNIVERSE_N}: {top20}")

    # ── Step 2: Prices ────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"STEP 2 — LOAD PRICES  ({START} → {END})")
    print(f"{'='*70}")
    prices = load_prices(top20, START, END)
    n_a    = len(prices.columns)
    print(f"  Loaded: {n_a} assets × {len(prices)} days")

    # ── Step 3: Carry proxy ───────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 3 — CARRY PROXY")
    print(f"{'='*70}")
    carry = build_carry_proxy(START)
    if not carry.empty:
        print(f"  {len(carry)} days | mean: {carry.mean():.5f} ({carry.mean()*365*100:.2f}%/yr)")
    else:
        print("  No carry proxy data.")

    # ── Step 4: Signals ───────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 4 — COMPUTE SIGNALS")
    print(f"{'='*70}")
    sig_br = compute_breakout_signal(prices, LOOKBACK_BR)
    sig_ts = compute_tsmom_signal(prices, TSMOM_L)
    print(f"  Breakout signal: {sig_br.shape[0]} weeks × {sig_br.shape[1]} assets")
    print(f"  TSMOM signal:    {sig_ts.shape[0]} weeks × {sig_ts.shape[1]} assets")

    # Sample statistics
    score_mean = sig_br.mean().mean()
    score_neg  = (sig_br < 0).mean().mean()
    print(f"  Breakout score: mean={score_mean:.3f}  "
          f"frac_below_21d_high={score_neg:.1%}")

    # ── Step 5: Backtest ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 5 — BACKTEST")
    print(f"{'='*70}")

    pnl_ls, pnl_long, pnl_short = backtest_ls(sig_br, prices)
    pnl_lo  = backtest_longonly(sig_br, prices)
    pnl_ts  = backtest_longonly(sig_ts, prices,  # TSMOM proxy long-only
                                long_n=10, vol_each=0.15)

    m_ls    = metrics(pnl_ls)
    m_long  = metrics(pnl_long)
    m_short = metrics(pnl_short)
    m_lo    = metrics(pnl_lo)
    m_ts    = metrics(pnl_ts)

    print(f"\n  ── P&L Decomposition ──────────────────────────────────────────")
    print(f"  {'Strategy':<20} {'Sharpe':>7} {'MaxDD':>8} {'AnnRet':>8}")
    print(f"  {'-'*48}")
    print(f"  {'L/S total':<20} {m_ls['sharpe']:>7.3f} {m_ls['maxdd']:>7.1f}% {m_ls['annual_ret']:>7.1f}%")
    print(f"  {'Long leg':<20} {m_long['sharpe']:>7.3f} {m_long['maxdd']:>7.1f}% {m_long['annual_ret']:>7.1f}%")
    print(f"  {'Short leg':<20} {m_short['sharpe']:>7.3f} {m_short['maxdd']:>7.1f}% {m_short['annual_ret']:>7.1f}%")
    print(f"  {'CS breakout long-only':<20} {m_lo['sharpe']:>7.3f} {m_lo['maxdd']:>7.1f}% {m_lo['annual_ret']:>7.1f}%")
    print(f"  {'TSMOM proxy':<20} {m_ts['sharpe']:>7.3f} {m_ts['maxdd']:>7.1f}% {m_ts['annual_ret']:>7.1f}%")

    if m_short["sharpe"] < -0.5:
        print(f"\n  SHORT LEG: Sharpe={m_short['sharpe']:.3f} < -0.5 → "
              f"same failure as 6.3 (crypto losers mean-revert violently)")
    elif m_short["sharpe"] > -0.3:
        print(f"\n  SHORT LEG: Sharpe={m_short['sharpe']:.3f} > -0.3 → L/S works")

    # ── Step 6: Correlations ──────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 6 — CORRELATIONS")
    print(f"{'='*70}")

    # Corr with TSMOM (Strategy A proxy)
    idx_ts = pnl_ls.index.intersection(pnl_ts.index)
    corr_A = pnl_ls[idx_ts].corr(pnl_ts[idx_ts]) if len(idx_ts) > 100 else float("nan")

    # Corr with carry (Strategy B proxy)
    corr_B = float("nan")
    if not carry.empty:
        idx_ca = pnl_ls.index.intersection(carry.index)
        if len(idx_ca) > 100:
            corr_B = pnl_ls[idx_ca].corr(carry[idx_ca])

    corr_A_lo = float("nan")
    corr_B_lo = float("nan")
    idx_ts_lo = pnl_lo.index.intersection(pnl_ts.index)
    if len(idx_ts_lo) > 100:
        corr_A_lo = pnl_lo[idx_ts_lo].corr(pnl_ts[idx_ts_lo])
    if not carry.empty:
        idx_ca_lo = pnl_lo.index.intersection(carry.index)
        if len(idx_ca_lo) > 100:
            corr_B_lo = pnl_lo[idx_ca_lo].corr(carry[idx_ca_lo])

    def _fmt(v):
        return f"{v:+.3f}" if not np.isnan(v) else "  n/a"

    print(f"  {'Strategy':<22} {'corrA(TSMOM)':>14} {'corrB(carry)':>14}")
    print(f"  {'-'*52}")
    print(f"  {'TSMOM v3 (known)':<22} {'  +1.00':>14} {'  +0.07':>14}")
    print(f"  {'L/S total':<22} {_fmt(corr_A):>14} {_fmt(corr_B):>14}")
    print(f"  {'CS breakout long-only':<22} {_fmt(corr_A_lo):>14} {_fmt(corr_B_lo):>14}")

    if not np.isnan(corr_B):
        if corr_B < -0.1:
            print(f"\n  >>> corrB={corr_B:.3f} < -0.1 — NEGATIVE CARRY CORRELATION CONFIRMED")
        else:
            print(f"\n  corrB={corr_B:.3f} — carry correlation not negative (Robot Wealth hypothesis not confirmed)")

    # ── Step 7: Sub-period Sharpe ─────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 7 — SUB-PERIOD SHARPE")
    print(f"{'='*70}")
    sub_ls    = sub_period_sharpes(pnl_ls)
    sub_lo    = sub_period_sharpes(pnl_lo)
    sub_tsmom = sub_period_sharpes(pnl_ts)

    print(f"  {'Year':<8} {'L/S':>8} {'Long-only':>11} {'TSMOM proxy':>13}")
    print(f"  {'-'*44}")
    all_years = sorted(set(sub_ls) | set(sub_lo) | set(sub_tsmom))
    for yr in all_years:
        tag = "  ← bear" if yr == 2022 else ""
        ls_s  = f"{sub_ls.get(yr, 0):+.3f}"  if yr in sub_ls   else "   n/a"
        lo_s  = f"{sub_lo.get(yr, 0):+.3f}"  if yr in sub_lo   else "   n/a"
        ts_s  = f"{sub_tsmom.get(yr, 0):+.3f}" if yr in sub_tsmom else "   n/a"
        print(f"  {yr:<8} {ls_s:>8} {lo_s:>11} {ts_s:>13}{tag}")

    # ── Step 8: A+B+C portfolio test ──────────────────────────────────────────
    combined_sharpe = float("nan")
    if not np.isnan(corr_B) and corr_B < -0.1 and m_ls["sharpe"] > 0.5:
        print(f"\n{'='*70}")
        print("STEP 8 — A+B+C PORTFOLIO TEST")
        print(f"{'='*70}")
        print(f"  corrB={corr_B:.3f} < -0.1  AND  Sharpe={m_ls['sharpe']:.3f} > 0.5")
        print(f"  Computing combined A+B+C Sharpe ...")

        pnl_A  = pnl_ts   # Strategy A proxy (TSMOM)
        pnl_B  = carry     # Strategy B proxy (carry)
        pnl_C  = pnl_ls    # Strategy C (this signal)
        idx3   = pnl_A.index.intersection(pnl_B.index).intersection(pnl_C.index)

        if len(idx3) > 100:
            def norm(p):
                v = p.std() * np.sqrt(252)
                return p * (0.15 / v) if v > 0 else p
            comb = (norm(pnl_A[idx3]) + norm(pnl_B[idx3]) + norm(pnl_C[idx3])) / 3
            v3   = comb.std() * np.sqrt(252)
            combined_sharpe = comb.mean() * 252 / v3 if v3 > 0 else 0.0
            print(f"\n  A+B+C Sharpe: {combined_sharpe:.3f}")
            print(f"  A+B baseline: 2.61")
            if combined_sharpe > 2.61:
                print(f"  >>> IMPROVEMENT: A+B+C={combined_sharpe:.3f} > A+B=2.61 ✓")
            else:
                delta = combined_sharpe - 2.61
                print(f"  >>> No improvement: A+B+C={combined_sharpe:.3f} vs A+B=2.61 ({delta:+.2f})")

    elif not np.isnan(corr_B) and corr_B < -0.1 and m_ls["sharpe"] <= 0.5:
        print(f"\n  corr_B={corr_B:.3f} < -0.1 but Sharpe={m_ls['sharpe']:.3f} too low for A+B+C test")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("VERDICT")
    print(f"{'='*70}")

    corr_B_s = _fmt(corr_B)
    corr_A_s = _fmt(corr_A)

    if not np.isnan(combined_sharpe) and combined_sharpe > 2.61:
        verdict = f"DEPLOY — A+B+C Sharpe={combined_sharpe:.3f} beats 2.61 baseline"
    elif not np.isnan(corr_B) and corr_B < -0.1 and m_ls["sharpe"] > 0.5:
        verdict = (f"PROMISING — corrB={corr_B:.3f} < -0.1 (negative carry corr confirmed) "
                   f"+ Sharpe > 0.5; needs carry correlation verified on live data")
    elif m_ls["sharpe"] >= 0.8 and not np.isnan(corr_B) and abs(corr_B) < 0.3:
        verdict = "PROMISING — Sharpe > 0.8 and low carry correlation"
    elif m_ls["sharpe"] < 0.3:
        verdict = f"SKIP — L/S Sharpe={m_ls['sharpe']:.3f} < 0.3"
    else:
        verdict = f"SKIP — insufficient edge (Sharpe={m_ls['sharpe']:.3f}, corrB={corr_B_s})"

    print(f"\n  L/S Sharpe={m_ls['sharpe']:.3f} | Long Sharpe={m_long['sharpe']:.3f} | "
          f"Short Sharpe={m_short['sharpe']:.3f}")
    print(f"  corrA={corr_A_s} | corrB={corr_B_s}")
    print(f"\n  >>> {verdict}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    plot_results(
        {
            "legs": {
                "L/S total": pnl_ls,
                "Long leg":  pnl_long,
                "Short leg": pnl_short,
                "Long-only": pnl_lo,
            },
            "tsmom_pnl":  pnl_ts,
            "sub_ls":     sub_ls,
            "sub_lo":     sub_lo,
            "sub_tsmom":  sub_tsmom,
        },
        carry,
        FIG_OUT,
    )

    elapsed = (_time.time() - t0) / 60
    print(f"\nTotal runtime: {elapsed:.1f} min")
    print(f"Output: {FIG_OUT}")
    print(f"Verdict: {verdict.split(' — ')[0]}")


if __name__ == "__main__":
    main()
