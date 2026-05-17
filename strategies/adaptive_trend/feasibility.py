"""
strategies/adaptive_trend/feasibility.py

Signal 31 — AdaptiveTrend: multi-timeframe TSMOM with adaptive lookback weights
Source: AdaptiveTrend (arXiv 2602.11708) — reported Sharpe 2.41 on 150+ pairs
Hypothesis: adaptive softmax weights across [14,28,56,112]d lookbacks, driven by
rolling 12-week cross-sectional IC, outperform fixed 28d TSMOM on a larger universe.

Key tests:
  (A) Does ADAPTIVE weighting improve over fixed 28d on 10 assets?
  (B) Does a LARGER UNIVERSE (30 assets) improve Sharpe further?
  (C) Is correlation with carry (Strategy B) negative? (Robot Wealth hypothesis)

Baseline: TSMOM v3, 10 assets, fixed 28d → Sharpe 1.33 (known)
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
START       = "2021-01-01"
END         = "2026-05-14"
LOOKBACKS   = [14, 28, 56, 112]
VOL_TARGET  = 0.15
GROSS_CAP   = 0.90
COST_RT     = 0.0017           # 0.17% round-trip
TOP_N       = 30
IC_WINDOW   = 12               # 12-week rolling IC
MIN_DAYS    = 365

HL_API  = "https://api.hyperliquid.xyz/info"
BIN_URL = "https://api.binance.com/api/v3/klines"
FIG_OUT = Path("strategies/adaptive_trend/feasibility_results.png")

STABLECOINS = {
    "USDC", "USDT", "BUSD", "DAI", "TUSD", "USDE", "FDUSD",
    "SUSD", "USDD", "USDX", "GHO", "FRAX", "LUSD", "DOLA", "USDP",
    "USDB", "USDJ", "CUSD", "HUSD", "GUSD",
}


# ── Universe ───────────────────────────────────────────────────────────────────

def fetch_hl_universe(top_n: int = 30) -> list[str]:
    """Fetch top-N HL perps by 24h notional volume, excluding stablecoins."""
    r = requests.post(HL_API, json={"type": "metaAndAssetCtxs"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    meta_assets = data[0]["universe"]
    asset_ctxs  = data[1]

    assets = []
    for i, asset in enumerate(meta_assets):
        name = asset["name"]
        if name.upper() in STABLECOINS:
            continue
        ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}
        vol = float(ctx.get("dayNtlVlm", 0) or 0)
        assets.append({"coin": name, "vol": vol})

    assets.sort(key=lambda x: x["vol"], reverse=True)
    return [a["coin"] for a in assets[:top_n]]


# ── Data ───────────────────────────────────────────────────────────────────────

def fetch_binance_daily(symbol: str, start: str, end: str) -> pd.Series:
    """Fetch daily close prices from Binance. Returns empty Series if unavailable."""
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
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "n_trades", "taker_base", "taker_quote", "_"
    ])
    df["time"] = pd.to_datetime(df["open_time"].astype(np.int64), unit="ms", utc=True)
    s = df.set_index("time")["close"].astype(float).sort_index()
    return s[~s.index.duplicated(keep="last")]


def load_prices(coins: list[str], start: str, end: str) -> pd.DataFrame:
    """Load daily close prices for all coins. Skip assets with < MIN_DAYS data."""
    prices = {}
    for coin in coins:
        sym = coin + "USDT"
        s = fetch_binance_daily(sym, start, end)
        n = len(s.dropna())
        if n >= MIN_DAYS:
            prices[coin] = s
            print(f"    {sym}: {n}d  OK")
        else:
            print(f"    {sym}: {n}d  SKIP")
    df = pd.DataFrame(prices)
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


# ── Signal ─────────────────────────────────────────────────────────────────────

def compute_tsmom_fixed(prices: pd.DataFrame, L: int = 28) -> pd.DataFrame:
    """TSMOM v3: tanh(cumret_L / (vol_L × √L)), long-only, weekly rebalance."""
    log_r   = np.log(prices / prices.shift(1))
    cumret  = log_r.rolling(L).sum()
    vol     = log_r.rolling(L).std() * np.sqrt(252)
    sig     = np.tanh(cumret / (vol.clip(lower=1e-6) * np.sqrt(L)))
    return sig.clip(lower=0, upper=1).resample("W-FRI").last()


def compute_adaptive_signal(prices: pd.DataFrame,
                             lookbacks: list[int] = LOOKBACKS,
                             ic_window: int = IC_WINDOW) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Adaptive multi-lookback TSMOM signal.
    Weights per lookback = softmax(rolling 12w cross-sectional IC).
    No look-ahead: IC at week T uses signal[T-1] vs ret[T], known by week T.
    Returns (signal_weekly, weight_df) both indexed by weekly dates.
    """
    log_r  = np.log(prices / prices.shift(1))
    weekly = prices.resample("W-FRI").last()
    rets_w = np.log(weekly / weekly.shift(1))
    fwd_w  = rets_w.shift(-1)   # next week's return (target, known 1 week later)

    # Individual lookback signals (weekly)
    sigs = {}
    for L in lookbacks:
        cumret = log_r.rolling(L).sum()
        vol    = log_r.rolling(L).std() * np.sqrt(252)
        raw    = np.tanh(cumret / (vol.clip(lower=1e-6) * np.sqrt(L)))
        sigs[L] = raw.resample("W-FRI").last()

    # Cross-sectional IC at each week
    # ic_raw[L][t] = spearmanr(signal_L[:,t], fwd_ret[:,t]) -- known at end of t+1
    ic_raw = {}
    for L in lookbacks:
        ic_vals = []
        for t in weekly.index:
            if t not in fwd_w.index:
                ic_vals.append(np.nan)
                continue
            s_t = sigs[L].loc[t].dropna()
            r_t = fwd_w.loc[t].dropna()
            common = s_t.index.intersection(r_t.index)
            if len(common) < 5:
                ic_vals.append(np.nan)
            else:
                ic_vals.append(stats.spearmanr(s_t[common], r_t[common])[0])
        ic_raw[L] = pd.Series(ic_vals, index=weekly.index)

    # Rolling IC → shift(1): weights at T use IC through T-1 (no look-ahead)
    ic_df = pd.DataFrame(ic_raw).rolling(ic_window, min_periods=1).mean().shift(1)

    # Softmax across lookbacks
    def _softmax(row: pd.Series) -> np.ndarray:
        v = row.fillna(0).values.astype(float)
        e = np.exp(v - v.max())
        return e / e.sum()

    weight_df = ic_df.apply(_softmax, axis=1, result_type="expand")
    weight_df.columns = lookbacks

    # Combined signal
    combined = pd.DataFrame(0.0, index=weekly.index, columns=weekly.columns)
    for L in lookbacks:
        sig_L = sigs[L].reindex(weekly.index)
        w_L   = weight_df[L].reindex(weekly.index).fillna(1.0 / len(lookbacks))
        combined += sig_L.multiply(w_L, axis=0)

    combined = combined.clip(lower=0, upper=1)
    return combined, weight_df


# ── Backtest ───────────────────────────────────────────────────────────────────

def backtest_vol_target(signal_weekly: pd.DataFrame,
                        prices_daily: pd.DataFrame,
                        vol_target: float = VOL_TARGET,
                        gross_cap: float  = GROSS_CAP,
                        cost_rt: float    = COST_RT) -> pd.Series:
    """Vol-targeted backtest. Weekly signal → daily positions. Returns daily net log-ret."""
    common = signal_weekly.columns.intersection(prices_daily.columns)
    sig_w  = signal_weekly[common]
    p_d    = prices_daily[common]

    log_r    = np.log(p_d / p_d.shift(1)).fillna(0)
    vol_d    = log_r.rolling(28, min_periods=14).std() * np.sqrt(252)
    vol_d    = vol_d.clip(lower=0.05)

    # Forward-fill weekly signal to daily (weights set Friday, active next week)
    sig_d    = sig_w.reindex(p_d.index, method="ffill")

    # Vol-targeted raw weights: w_i = (vol_target / vol_i) × signal_i
    raw_w    = sig_d.divide(vol_d) * vol_target

    # Scale to gross cap
    gross    = raw_w.abs().sum(axis=1).replace(0, 1e-9)
    scale    = (gross_cap / gross).clip(upper=1.0)
    weights  = raw_w.multiply(scale, axis=0)

    shifted  = weights.shift(1).fillna(0)          # lag 1 day: no look-ahead
    pnl_g    = (shifted * log_r).sum(axis=1)
    turnover = shifted.diff().abs().sum(axis=1)
    cost     = turnover * cost_rt

    return (pnl_g - cost)


# ── Metrics ────────────────────────────────────────────────────────────────────

def metrics(pnl: pd.Series) -> dict:
    ann   = pnl.mean() * 252
    vol   = pnl.std()  * np.sqrt(252)
    sh    = ann / vol if vol > 0 else 0.0
    cum   = pnl.cumsum()
    dd    = (cum - cum.cummax()).min()
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
    """Fetch 8h Binance futures funding rates."""
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    all_rows = []
    cur = start_ms
    now_ms = int(_time.time() * 1000)

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
    """
    BTC+ETH funding carry proxy. Daily return ≈ sum of 3 funding payments.
    Represents the simplified Strategy B P&L.
    """
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    btc_f = fetch_binance_funding("BTCUSDT", start_ms)
    eth_f = fetch_binance_funding("ETHUSDT", start_ms)

    if btc_f.empty and eth_f.empty:
        print("    WARNING: funding data unavailable")
        return pd.Series(dtype=float)

    combined = pd.concat([btc_f.rename("BTC"), eth_f.rename("ETH")],
                         axis=1, join="outer").mean(axis=1)
    # Daily sum: 3 payments/day each at rate ~ 0.01%
    daily = combined.resample("D").sum()
    return daily   # raw (positive when funding positive)


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_results(results: dict, fig_path: Path) -> None:
    fig = plt.figure(figsize=(16, 12))
    gs  = gridspec.GridSpec(2, 2, hspace=0.38, wspace=0.30)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    palette = {"TSMOM-10-fixed": "#2196F3",
               "Adaptive-10":    "#FF9800",
               "Adaptive-30":    "#4CAF50"}

    # 1 — Equity curves
    for key, res in results.items():
        p = res["pnl"]
        m = res["m"]
        ax1.plot(p.index, p.cumsum() * 100,
                 label=f"{key}  S={m['sharpe']:.2f}  DD={m['maxdd']:.1f}%",
                 color=palette.get(key, "gray"))
    ax1.set_title("Equity Curves (cum. log-ret %)", fontsize=11)
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)
    ax1.set_ylabel("%")

    # 2 — Adaptive lookback weights (30-asset)
    if "adapt_weights" in results.get("Adaptive-30", {}):
        wt = results["Adaptive-30"]["adapt_weights"]
        colors_lb = {14: "#E91E63", 28: "#9C27B0", 56: "#3F51B5", 112: "#009688"}
        bottom = np.zeros(len(wt))
        for L in LOOKBACKS:
            if L not in wt.columns:
                continue
            vals = wt[L].fillna(0.25).values
            ax2.fill_between(wt.index, bottom, bottom + vals,
                             label=f"{L}d", alpha=0.8, color=colors_lb[L])
            bottom = bottom + vals
        ax2.set_title("Adaptive Lookback Weights — 30-asset", fontsize=11)
        ax2.set_ylim(0, 1.05)
        ax2.legend(fontsize=8)
        ax2.grid(alpha=0.3)
        ax2.set_ylabel("weight")
    else:
        ax2.text(0.5, 0.5, "weights n/a", ha="center", va="center",
                 transform=ax2.transAxes)

    # 3 — Sub-period Sharpe by year
    all_years = sorted({yr for res in results.values()
                        for yr in res.get("sub_sharpes", {}).keys()})
    x     = np.arange(len(all_years))
    width = 0.25
    for idx, (key, res) in enumerate(results.items()):
        vals = [res.get("sub_sharpes", {}).get(yr, 0) for yr in all_years]
        ax3.bar(x + idx * width, vals, width,
                label=key, color=palette.get(key, "gray"), alpha=0.85)
    ax3.axhline(0, color="black", lw=0.8)
    ax3.set_xticks(x + width)
    ax3.set_xticklabels(all_years)
    ax3.set_title("Sub-Period Sharpe by Year", fontsize=11)
    ax3.legend(fontsize=8)
    ax3.grid(alpha=0.3, axis="y")

    # 4 — Rolling 52w Sharpe
    for key, res in results.items():
        p = res["pnl"]
        roll = p.rolling(252).apply(
            lambda x: (x.mean() * 252) / (x.std() * np.sqrt(252)) if x.std() > 0 else np.nan
        )
        ax4.plot(p.index, roll, label=key, color=palette.get(key, "gray"))
    ax4.axhline(0, color="black", lw=0.8)
    ax4.axhline(1, color="gray",  lw=0.8, ls="--", alpha=0.6)
    ax4.set_title("Rolling 52-week Sharpe", fontsize=11)
    ax4.legend(fontsize=8)
    ax4.grid(alpha=0.3)

    fig.suptitle("Signal 31 — AdaptiveTrend: Multi-Timeframe TSMOM\n"
                 "Adaptive weights (softmax IC) vs fixed 28d | 10 assets vs 30 assets",
                 fontsize=12, y=0.99)
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {fig_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    t0 = _time.time()
    print("=" * 70)
    print("ADAPTIVE TREND — Multi-Timeframe TSMOM with Adaptive Lookback Weights")
    print("Signal 31 — Strategy C candidate")
    print("=" * 70)

    # ── Step 1: Universe ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 1 — HL TOP-30 UNIVERSE")
    print(f"{'='*70}")
    top30 = fetch_hl_universe(TOP_N)
    print(f"  Top-30 coins: {top30}")

    # ── Step 2: Prices ────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"STEP 2 — LOAD PRICES  ({START} → {END})")
    print(f"{'='*70}")
    prices_all = load_prices(top30, START, END)
    n_assets   = len(prices_all.columns)
    print(f"  Loaded: {n_assets} assets × {len(prices_all)} days")

    # 10-asset subset = first 10 available (already sorted by HL volume)
    top10  = [c for c in top30 if c in prices_all.columns][:10]
    p10    = prices_all[top10]
    p30    = prices_all
    print(f"  10-asset subset: {top10}")

    # ── Step 3: Carry proxy ───────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 3 — CARRY PROXY (BTC+ETH funding rates, Binance futures)")
    print(f"{'='*70}")
    carry = build_carry_proxy(START)
    if not carry.empty:
        daily_mean  = carry.mean()
        annual_rate = daily_mean * 365 * 100
        print(f"  {len(carry)} days | mean daily rate: {daily_mean:.5f} "
              f"({annual_rate:.2f}%/yr)")
    else:
        print("  No carry proxy data.")

    # ── Step 4: Build 3 strategies ────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 4 — BUILD STRATEGIES")
    print(f"{'='*70}")
    results = {}

    # Strategy 1: TSMOM fixed 28d on 10 assets
    print("\n  [1/3] TSMOM-10-fixed (baseline, fixed 28d) ...")
    sig_f10      = compute_tsmom_fixed(p10, L=28)
    pnl_f10      = backtest_vol_target(sig_f10, p10)
    results["TSMOM-10-fixed"] = {
        "pnl": pnl_f10,
        "m":   metrics(pnl_f10),
        "sub_sharpes": sub_period_sharpes(pnl_f10),
    }
    m = results["TSMOM-10-fixed"]["m"]
    print(f"    Sharpe={m['sharpe']:.3f}  MaxDD={m['maxdd']:.1f}%  "
          f"AnnRet={m['annual_ret']:.1f}%")

    # Strategy 2: Adaptive on 10 assets
    print("\n  [2/3] Adaptive-10 (adaptive weights, 10 assets) ...")
    sig_a10, wt10 = compute_adaptive_signal(p10, LOOKBACKS, IC_WINDOW)
    pnl_a10       = backtest_vol_target(sig_a10, p10)
    results["Adaptive-10"] = {
        "pnl": pnl_a10,
        "m":   metrics(pnl_a10),
        "sub_sharpes": sub_period_sharpes(pnl_a10),
        "adapt_weights": wt10,
    }
    m = results["Adaptive-10"]["m"]
    print(f"    Sharpe={m['sharpe']:.3f}  MaxDD={m['maxdd']:.1f}%  "
          f"AnnRet={m['annual_ret']:.1f}%")
    print(f"    Mean lookback weights: "
          + "  ".join(f"{L}d={wt10[L].mean():.3f}" for L in LOOKBACKS))

    # Strategy 3: Adaptive on 30 assets
    print("\n  [3/3] Adaptive-30 (adaptive weights, 30 assets) ...")
    sig_a30, wt30 = compute_adaptive_signal(p30, LOOKBACKS, IC_WINDOW)
    pnl_a30       = backtest_vol_target(sig_a30, p30)
    results["Adaptive-30"] = {
        "pnl": pnl_a30,
        "m":   metrics(pnl_a30),
        "sub_sharpes": sub_period_sharpes(pnl_a30),
        "adapt_weights": wt30,
    }
    m = results["Adaptive-30"]["m"]
    print(f"    Sharpe={m['sharpe']:.3f}  MaxDD={m['maxdd']:.1f}%  "
          f"AnnRet={m['annual_ret']:.1f}%")
    print(f"    Mean lookback weights: "
          + "  ".join(f"{L}d={wt30[L].mean():.3f}" for L in LOOKBACKS))

    # ── Step 5: Correlations ──────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 5 — CORRELATIONS")
    print(f"{'='*70}")

    pnl_ref = pnl_f10  # Strategy A proxy
    for key in ("Adaptive-10", "Adaptive-30"):
        pnl = results[key]["pnl"]
        idx = pnl.index.intersection(pnl_ref.index)
        cA  = pnl[idx].corr(pnl_ref[idx])
        results[key]["corr_A"] = round(cA, 3)
        print(f"  {key}: corr(strategy, TSMOM-10-fixed) = {cA:+.3f}")
    results["TSMOM-10-fixed"]["corr_A"] = 1.000

    if not carry.empty:
        for key, res in results.items():
            pnl = res["pnl"]
            idx = pnl.index.intersection(carry.index)
            if len(idx) < 100:
                res["corr_B"] = float("nan")
                print(f"  {key}: corr(strategy, carry) = n/a ({len(idx)} overlap)")
                continue
            cB = pnl[idx].corr(carry[idx])
            res["corr_B"] = round(cB, 3)
            print(f"  {key}: corr(strategy, carry) = {cB:+.3f}")

    # ── Step 6: Comparison table ──────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 6 — COMPARISON TABLE")
    print(f"{'='*70}")
    header = f"  {'Strategy':<28} {'Sharpe':>7} {'MaxDD':>8} {'AnnRet':>8} {'corrA':>7} {'corrB':>7}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    # Known TSMOM v3 baseline
    print(f"  {'TSMOM v3 (known baseline)':<28} {'1.33':>7} {'-6.9%':>8} "
          f"{'n/a':>8} {'+1.00':>7} {'+0.07':>7}")

    for key, res in results.items():
        m    = res["m"]
        cA   = res.get("corr_A", float("nan"))
        cB   = res.get("corr_B", float("nan"))
        cA_s = f"{cA:+.3f}" if not np.isnan(cA) else "  n/a"
        cB_s = f"{cB:+.3f}" if not np.isnan(cB) else "  n/a"
        print(f"  {key:<28} {m['sharpe']:>7.3f} {m['maxdd']:>7.1f}% "
              f"{m['annual_ret']:>7.1f}% {cA_s:>7} {cB_s:>7}")

    # ── Step 7: A+B+C test if warranted ──────────────────────────────────────
    for key, res in results.items():
        cB = res.get("corr_B", 0.0)
        sh = res["m"]["sharpe"]
        if np.isnan(cB):
            continue
        if cB < -0.1 and sh > 0.5 and not carry.empty:
            print(f"\n  >>> {key}: corrB={cB:.3f} < -0.1  AND  Sharpe={sh:.3f} > 0.5")
            print(f"  >>> Computing A+B+C combined Sharpe ...")
            pnl_A = pnl_f10
            pnl_B = carry
            pnl_C = res["pnl"]
            idx3  = pnl_A.index.intersection(pnl_B.index).intersection(pnl_C.index)
            if len(idx3) > 100:
                def norm(p):
                    v = p.std() * np.sqrt(252)
                    return p * (0.15 / v) if v > 0 else p
                comb  = (norm(pnl_A[idx3]) + norm(pnl_B[idx3]) + norm(pnl_C[idx3])) / 3
                v3    = comb.std() * np.sqrt(252)
                s3    = comb.mean() * 252 / v3 if v3 > 0 else 0.0
                print(f"  A+B+C Sharpe: {s3:.3f}  (A+B baseline: 2.61)")

    # ── Step 8: Sub-period breakdown ──────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 7 — SUB-PERIOD SHARPE")
    print(f"{'='*70}")
    for key, res in results.items():
        print(f"  {key}:")
        for yr, sh in res.get("sub_sharpes", {}).items():
            tag = "← bear" if yr == 2022 else ""
            print(f"    {yr}: {sh:+.3f}  {tag}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("VERDICT")
    print(f"{'='*70}")

    best_key = max(results, key=lambda k: results[k]["m"]["sharpe"])
    best     = results[best_key]
    sh       = best["m"]["sharpe"]
    cA       = best.get("corr_A", float("nan"))
    cB       = best.get("corr_B", float("nan"))

    if sh >= 0.8 and not np.isnan(cB) and cB < 0.0:
        verdict = "PROMISING — negative carry correlation AND Sharpe > 0.8"
    elif sh >= 1.3 and (np.isnan(cA) or cA >= 0.8):
        verdict = "IMPROVEMENT — replaces/enhances TSMOM v3 parameter"
    elif sh >= 0.6:
        verdict = "PROMISING — Sharpe > 0.6; further refinement warranted"
    else:
        verdict = f"SKIP — best Sharpe={sh:.3f} < 0.6 across all variants"

    cA_s = f"{cA:+.3f}" if not np.isnan(cA) else "n/a"
    cB_s = f"{cB:+.3f}" if not np.isnan(cB) else "n/a"
    print(f"\n  Best: {best_key}")
    print(f"  Sharpe={sh:.3f} | corrA={cA_s} | corrB={cB_s}")
    print(f"\n  >>> {verdict}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    plot_results(results, FIG_OUT)

    elapsed = (_time.time() - t0) / 60
    print(f"\nTotal runtime: {elapsed:.1f} min")
    print(f"Verdict: {verdict.split(' — ')[0]}")


if __name__ == "__main__":
    main()
