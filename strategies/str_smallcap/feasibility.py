"""
strategies/str_smallcap/feasibility.py — Short-Term Reversal on Small-Cap Crypto

Hypothesis (Zaremba et al. 2021, J. Portfolio Management):
  Short-term reversal FAILS on large-cap crypto (confirmed: 6.8, IC t-stat 0.85)
  but WORKS on small-caps (top-100 to top-500 by market cap): documented t-stat > 3.
  Economic mechanism: thin liquidity + retail overreaction → mean revert within 1 week.

Signal: STR = -1 × last_week_return  (long worst performers from last week)
Universe: CoinGecko top 50–250 by market cap (rank 50 = enough liquidity, 250 = still trackable)
Filter: exclude stablecoins, wrapped tokens, leveraged tokens
Long-only top-10 portfolio (no shorting small-caps — confirmed failure pattern)
Weekly rebalance, equal weight, cost 0.34% RT (conservative for small-caps)

Data: CoinGecko free API, 2 years of daily prices resampled to weekly.
Note: uses CURRENT market cap rankings (survivorship bias documented below).

Execution constraint: CANNOT run on Hyperliquid (small-caps not listed).
Would require Binance Spot, KuCoin, or Gate.io. Documented in verdict.

Expected diversification: near-zero corr with TSMOM (different universe, opposite direction)
vs the 6.8 large-cap reversal that showed t-stat only 0.85 (not worth deploying).
"""

import os, sys, time, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import requests
from datetime import datetime, timezone, timedelta
from scipy.stats import spearmanr, ttest_1samp

warnings.filterwarnings("ignore")
np.random.seed(42)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
CG_BASE   = "https://api.coingecko.com/api/v3"
CG_SLEEP  = 0.6      # seconds between CoinGecko API calls (free tier: ~30 req/min)
BIN_URL   = "https://api.binance.com/api/v3/klines"
BIN_SLEEP = 0.1      # seconds between Binance API calls (free, generous limits)
RANK_MIN  = 51       # start rank (exclude top-50 large-caps)
RANK_MAX  = 250      # end rank
MIN_WEEKS = 52       # minimum weekly return history required
N_LONG    = 10       # number of coins in long portfolio
COST_RT   = 0.0034   # 0.34% RT for small-caps (higher slippage vs Propr 0.17%)
VOL_TGT   = 0.15     # not applied here (equal weight, data quality concerns)

# Period for backtest
BACKTEST_START = "2023-01-01"   # enough post-FTX data
TEST_SPLIT     = "2024-07-01"   # train/test split for sub-period stability

OUT_DIR  = os.path.dirname(os.path.abspath(__file__))

# Known stablecoins and wrapped tokens to exclude (symbol-based)
EXCLUDE_SYMBOLS = {
    # Stablecoins
    "USDT","USDC","BUSD","DAI","TUSD","USDP","GUSD","FRAX","USDD","FDUSD",
    "PYUSD","CRVUSD","EURC","EURT","PAX","SUSD","LUSD","DOLA","CUSD","AUSD",
    "USDE","USDY","USDM","YUSD","USDX","MUSD","USDZ","XUSD","RUSD","EURS",
    "SEUR","AGEUR","RAI","BEAN","VOLT","FLOAT","FEI","OUSD","GRAI","MKUSD",
    "CYGNUS","ALUSD","MIMATIC","DOLA",
    # Wrapped / staked / bridged
    "WBTC","WETH","WBNB","WSOL","WAVAX","WFTM","STETH","CBETH","RETH","SFRXETH",
    "WSTETH","LIDO","WMATIC","WGLMR","WXRP","WDOT","WLINK","WADA","WLTC",
    "BBTC","HBTC","PBTC","RENBTC","SBTC","TBTC","IMBTC","OBTC",
    # Leveraged tokens (usually 3L, 3S, BULL, BEAR in name)
}

EXCLUDE_KEYWORDS = [
    "wrapped","staked","liquid staking","bridged","pegged","lending","yield",
    "leveraged","3x","bull","bear","short","inverse","synthetic",
    "tether","usd coin","binance usd","pax dollar","true usd",
    "aave","compound","yearn","curve","convex",  # DeFi protocol tokens (high corr with DeFi index)
]


# ─── COINGECKO API ───────────────────────────────────────────────────────────

def _cg_get(endpoint: str, params: dict = None, timeout: int = 15) -> dict | list:
    url = f"{CG_BASE}{endpoint}"
    headers = {"Accept": "application/json",
               "User-Agent": "Mozilla/5.0 AlgoResearch/1.0"}
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 429:
                print(f"  [rate limit] sleeping 60s…", end="", flush=True)
                time.sleep(60)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 2: raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Failed after 3 attempts: {url}")


def fetch_top_coins(n: int = 250) -> list[dict]:
    """Fetch top n coins by market cap (current snapshot)."""
    all_coins = []
    per_page  = 100
    for page in range(1, (n // per_page) + 2):
        data = _cg_get("/coins/markets", params={
            "vs_currency": "usd", "order": "market_cap_desc",
            "per_page": min(per_page, n - len(all_coins)),
            "page": page, "sparkline": "false",
            "price_change_percentage": "7d"
        })
        if not data: break
        all_coins.extend(data)
        if len(all_coins) >= n: break
        time.sleep(CG_SLEEP)
    return all_coins[:n]


def is_excluded(coin: dict) -> bool:
    symbol = coin.get("symbol", "").upper()
    name   = coin.get("name",   "").lower()
    if symbol in EXCLUDE_SYMBOLS:
        return True
    for kw in EXCLUDE_KEYWORDS:
        if kw in name:
            return True
    return False


def _bin_klines(symbol: str, interval: str, start_ms: int) -> pd.Series:
    """
    Fetch Binance klines from start_ms to now. Returns close price Series.
    Index: open_time (UTC). Free API, no auth.
    """
    now_ms   = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
    all_rows: list = []
    cur = start_ms
    week_ms = 7 * 24 * 3600 * 1000
    day_ms  = 24 * 3600 * 1000
    step    = week_ms if interval == "1w" else day_ms
    while cur < now_ms:
        params = {"symbol": symbol, "interval": interval,
                  "startTime": cur, "limit": 1000}
        r = requests.get(BIN_URL, params=params, timeout=15)
        if r.status_code == 400:    # symbol not on Binance
            return pd.Series(dtype=float)
        if r.status_code == 429:
            time.sleep(10); continue
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        all_rows.extend(rows)
        cur = int(rows[-1][0]) + step
        time.sleep(BIN_SLEEP)
    if not all_rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(all_rows, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_vol","n_trades","taker_base","taker_quote","_"
    ])
    ts = pd.to_datetime(df["open_time"].astype(np.int64), unit="ms", utc=True)
    s  = pd.Series(df["close"].astype(float).values, index=ts)
    return s[~s.index.duplicated(keep="last")].sort_index()


def fetch_binance_weekly(symbol: str, start: str = "2022-01-01") -> pd.Series:
    """
    Weekly close price from Binance spot USDT pair.
    Binance 1w candles open on Monday; we offset index by +4 days to Friday
    so the series aligns with W-FRI convention used elsewhere.
    """
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    s = _bin_klines(symbol, "1w", start_ms)
    if s.empty:
        return s
    # Monday open_time → Friday (W-FRI alignment)
    s.index = s.index + pd.Timedelta(days=4)
    s.name  = symbol
    return s


def fetch_binance_daily(symbol: str = "BTCUSDT",
                         start: str = "2022-01-01") -> pd.Series:
    """Daily close price from Binance. Used for BTC TSMOM computation."""
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    s = _bin_klines(symbol, "1d", start_ms)
    s.name = symbol
    return s


# ─── WEEKLY RETURNS ───────────────────────────────────────────────────────────

def to_weekly(daily_prices: pd.Series) -> pd.Series:
    """Friday close weekly return."""
    wk = daily_prices.resample("W-FRI").last().dropna()
    return np.log(wk / wk.shift(1)).dropna()


def build_return_matrix(weekly_ret_dict: dict[str, pd.Series]) -> pd.DataFrame:
    """
    Align all coin weekly return series into a single DataFrame.
    Rows = weeks, columns = coin symbols.
    """
    df = pd.DataFrame(weekly_ret_dict)
    return df.sort_index()


# ─── TSMOM v3 (for correlation) ───────────────────────────────────────────────

def fetch_btc_tsmom_weekly() -> pd.Series:
    """Pull BTC daily from Binance and reconstruct TSMOM v3 weekly returns."""
    print("  Fetching BTC daily prices from Binance for TSMOM reference…")
    btc_daily = fetch_binance_daily("BTCUSDT", start="2022-01-01")
    if btc_daily.empty:
        return pd.Series(dtype=float)
    lr    = np.log(btc_daily / btc_daily.shift(1)).dropna()
    cr28  = lr.rolling(28).sum()
    v28   = lr.rolling(28).std() * np.sqrt(28)
    sig   = np.tanh(cr28 / v28.replace(0, np.nan)).clip(lower=0)
    strat = sig.shift(1) * lr
    return strat.resample("W-FRI").sum()


# ─── CROSS-SECTIONAL IC ───────────────────────────────────────────────────────

def compute_ic_series(ret_matrix: pd.DataFrame,
                       min_coins: int = 10) -> pd.Series:
    """
    For each week T: IC = spearmanr(-ret[T-1], ret[T]) across all coins.
    Returns Series of weekly IC values (only where ≥ min_coins have valid data).
    """
    ics = {}
    weeks = ret_matrix.index.tolist()
    for i in range(1, len(weeks)):
        T     = weeks[i]
        T_lag = weeks[i - 1]
        sig   = -ret_matrix.loc[T_lag].dropna()   # STR signal: negative last-week return
        out   = ret_matrix.loc[T].dropna()
        valid = sig.index.intersection(out.index)
        if len(valid) < min_coins:
            continue
        ic, _ = spearmanr(sig[valid], out[valid])
        ics[T] = ic
    return pd.Series(ics)


# ─── PORTFOLIO BACKTEST ───────────────────────────────────────────────────────

def portfolio_backtest(ret_matrix: pd.DataFrame,
                        tsmom_wk: pd.Series,
                        start: str = BACKTEST_START,
                        n_long: int = N_LONG,
                        cost_rt: float = COST_RT) -> dict:
    """
    Long-only top-N reversal portfolio (worst performers from last week).
    Equal weight, weekly rebalance, cost on turnover.
    """
    ret_matrix = ret_matrix[ret_matrix.index >= start].copy()
    weekly_ret_port = []
    prev_portfolio  = set()

    for i in range(1, len(ret_matrix)):
        T     = ret_matrix.index[i]
        T_lag = ret_matrix.index[i - 1]

        signal = -ret_matrix.loc[T_lag].dropna()
        if len(signal) < n_long * 2:
            weekly_ret_port.append((T, np.nan))
            continue

        # Long top-N by signal (worst performers = highest reversal score)
        top_n  = signal.nlargest(n_long).index.tolist()
        cur_portfolio = set(top_n)

        # Returns for this week's portfolio
        week_rets = ret_matrix.loc[T, top_n].dropna()
        port_ret  = week_rets.mean() if len(week_rets) > 0 else 0.0

        # Turnover cost (proportion of portfolio that changed)
        if prev_portfolio:
            n_changed  = len(cur_portfolio - prev_portfolio)
            turnover   = n_changed / n_long
            port_ret  -= turnover * cost_rt

        weekly_ret_port.append((T, port_ret))
        prev_portfolio = cur_portfolio

    port_series = pd.Series(
        [r for _, r in weekly_ret_port],
        index=[t for t, _ in weekly_ret_port]
    ).dropna()
    port_series = port_series[port_series.index >= start]

    if len(port_series) < 10:
        return {"sharpe": np.nan, "maxdd": np.nan, "corr_tsmom": np.nan,
                "n_weeks": 0, "port_series": pd.Series(dtype=float)}

    cum_ret = port_series.cumsum()
    sharpe  = port_series.mean() / port_series.std() * np.sqrt(52) if port_series.std() > 0 else 0.0
    maxdd   = (cum_ret - cum_ret.cummax()).min()

    common  = port_series.index.intersection(tsmom_wk.index)
    corr_t  = port_series.loc[common].corr(tsmom_wk.loc[common]) if len(common) > 10 else np.nan

    return {
        "sharpe": sharpe, "maxdd": maxdd,
        "corr_tsmom": corr_t, "n_weeks": len(port_series),
        "port_series": port_series, "cum_ret": cum_ret
    }


# ─── FIGURES ─────────────────────────────────────────────────────────────────

def make_figure(ic_series: pd.Series, ic_full: float, ic_t: float,
                res_full: dict, res_train: dict, res_test: dict,
                ret_matrix: pd.DataFrame, tsmom_wk: pd.Series) -> None:

    fig = plt.figure(figsize=(20, 14))
    fig.suptitle(
        "STR Small-Cap Feasibility — Strategy C Candidate\n"
        f"Universe: CoinGecko rank {RANK_MIN}–{RANK_MAX}  |  "
        f"Long-only top-{N_LONG} reversals  |  Weekly rebalance",
        fontsize=13, fontweight="bold", y=0.995
    )
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.38)

    # ── Panel 1: Rolling IC (12-week) ────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :2])
    ic_roll = ic_series.rolling(12).mean()
    ax1.fill_between(ic_series.index, 0, ic_series.values,
                     where=ic_series.values > 0, color="#1a9850", alpha=0.4)
    ax1.fill_between(ic_series.index, 0, ic_series.values,
                     where=ic_series.values < 0, color="#d73027", alpha=0.4)
    ax1.plot(ic_roll.index, ic_roll.values, color="#2166ac", lw=2,
             label="12-week rolling IC")
    ax1.axhline(0, color="black", lw=0.8)
    ax1.axhline(ic_full, color="#2166ac", ls="--", lw=1.2,
                label=f"Mean IC={ic_full:.4f}  t={ic_t:.2f}")
    ax1.axvline(pd.Timestamp(TEST_SPLIT), color="orange", ls="--", lw=1.2,
                label=f"Train|Test split {TEST_SPLIT}")
    ax1.set_title("Cross-Sectional IC over Time — STR signal", fontsize=11)
    ax1.set_ylabel("IC (rank correlation)"); ax1.legend(fontsize=9)
    ax1.grid(alpha=0.3)

    # ── Panel 2: IC distribution ─────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.hist(ic_series.dropna(), bins=30, color="#2166ac", alpha=0.7,
             edgecolor="white")
    ax2.axvline(0, color="black", lw=1)
    ax2.axvline(ic_full, color="#d73027", ls="--", lw=1.5,
                label=f"Mean={ic_full:.4f}")
    ax2.set_title("IC Distribution", fontsize=10)
    ax2.set_xlabel("Weekly IC"); ax2.set_ylabel("Count"); ax2.legend(fontsize=9)

    # ── Panel 3: Equity curve ────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, :2])
    if "cum_ret" in res_full and len(res_full["cum_ret"]) > 0:
        cum = res_full["cum_ret"]
        ax3.plot(cum.index, cum.values * 100, color="#2166ac", lw=2,
                 label=f"STR Top-{N_LONG} (Sharpe={res_full['sharpe']:.2f}  "
                        f"MaxDD={res_full['maxdd']*100:.1f}%  "
                        f"corr(TSMOM)={res_full['corr_tsmom']:.3f})")
        ax3.axvline(pd.Timestamp(TEST_SPLIT), color="orange", ls="--", lw=1.2,
                    label="Train|Test split")
        # TSMOM for reference
        ts_cum = tsmom_wk[tsmom_wk.index >= BACKTEST_START].cumsum() * 100
        ax3.plot(ts_cum.index, ts_cum.values, color="gray", lw=1, ls="--",
                 alpha=0.7, label="TSMOM v3 reference (BTC)")
    ax3.axhline(0, color="black", lw=0.5)
    ax3.set_title(f"Equity Curve — STR Small-Cap Top-{N_LONG} (log return)", fontsize=11)
    ax3.set_ylabel("Cumulative log return (%)"); ax3.set_xlabel("Date")
    ax3.legend(fontsize=9); ax3.grid(alpha=0.3)

    # ── Panel 4: Sub-period summary ───────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.axis("off")
    n_coins = len(ret_matrix.columns)
    n_weeks = len(ic_series.dropna())

    ic_train = ic_series[ic_series.index < TEST_SPLIT].dropna()
    ic_test  = ic_series[ic_series.index >= TEST_SPLIT].dropna()
    ic_t_tr  = (ic_train.mean() / (ic_train.std() / np.sqrt(len(ic_train)))
                if len(ic_train) > 1 else np.nan)
    ic_t_te  = (ic_test.mean()  / (ic_test.std()  / np.sqrt(len(ic_test)))
                if len(ic_test) > 1 else np.nan)

    txt = (
        "═══ RESULTS SUMMARY ═══\n\n"
        f"Universe: {n_coins} coins (rank {RANK_MIN}–{RANK_MAX})\n"
        f"Weeks with IC: {n_weeks}\n\n"
        f"IC (full period)\n"
        f"  Mean = {ic_full:.4f}\n"
        f"  t-stat = {ic_t:.3f}\n\n"
        f"Sub-period IC:\n"
        f"  Train ({BACKTEST_START}–{TEST_SPLIT[:7]}):\n"
        f"    IC={ic_train.mean():.4f}  t={ic_t_tr:.2f}\n"
        f"  Test ({TEST_SPLIT[:7]}–2026):\n"
        f"    IC={ic_test.mean():.4f}  t={ic_t_te:.2f}\n\n"
        f"Portfolio (Sharpe/MaxDD):\n"
        f"  Full:  {res_full['sharpe']:.3f} / {res_full['maxdd']*100:.1f}%\n"
        f"  Train: {res_train['sharpe']:.3f} / {res_train['maxdd']*100:.1f}%\n"
        f"  Test:  {res_test['sharpe']:.3f} / {res_test['maxdd']*100:.1f}%\n\n"
        f"corr(TSMOM): {res_full['corr_tsmom']:.3f}\n\n"
        f"⚠ Survivorship bias: uses current\n"
        f"  top-250 ranking (not historical).\n"
        f"  IC understated (failures excluded)."
    )
    ax4.text(0.05, 0.95, txt, transform=ax4.transAxes,
             va="top", ha="left", fontsize=9.5, fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.6", facecolor="#f0f4ff",
                       edgecolor="#2166ac"))

    out_path = os.path.join(OUT_DIR, "feasibility_results.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure → {out_path}")
    plt.close()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("STR SMALL-CAP FEASIBILITY — Strategy C Candidate (Zaremba 2021)")
    print(f"Universe: CoinGecko rank {RANK_MIN}–{RANK_MAX}  |  "
          f"Long-only top-{N_LONG} reversals  |  Weekly rebalance")
    print("=" * 70)

    # ── 1. TSMOM reference ────────────────────────────────────────────────────
    print("\n[1/5] Fetching BTC TSMOM reference…")
    tsmom_wk = fetch_btc_tsmom_weekly()
    print(f"  TSMOM weekly: {len(tsmom_wk)} weeks  "
          f"({tsmom_wk.index[0].date()} → {tsmom_wk.index[-1].date()})")

    # ── 2. Fetch universe ─────────────────────────────────────────────────────
    print(f"\n[2/5] Fetching top {RANK_MAX} coins from CoinGecko…")
    all_coins = fetch_top_coins(RANK_MAX)
    print(f"  Retrieved {len(all_coins)} coins")

    # Filter to rank 51-250, exclude stablecoins/wrapped
    universe: list[dict] = []
    for i, coin in enumerate(all_coins):
        rank = i + 1
        if rank < RANK_MIN or rank > RANK_MAX:
            continue
        if is_excluded(coin):
            continue
        universe.append({"id": coin["id"], "symbol": coin["symbol"],
                          "name": coin["name"], "rank": rank})

    print(f"  Universe after filtering: {len(universe)} coins")
    print(f"  Excluded: {RANK_MAX - RANK_MIN + 1 - len(universe)} "
          f"(stablecoins, wrapped, large-caps)")
    if len(universe) < 20:
        print("ERROR: Insufficient universe. Check API or filters."); return

    # ── 3. Fetch price history (Binance USDT pairs) ───────────────────────────
    print(f"\n[3/5] Fetching weekly prices from Binance for {len(universe)} coins…")
    print(f"  (estimated time: ~{len(universe) * BIN_SLEEP / 60:.1f} min)")

    weekly_ret_dict: dict[str, pd.Series] = {}
    n_failed = 0

    for i, coin in enumerate(universe):
        bin_sym = coin["symbol"].upper() + "USDT"
        print(f"  [{i+1:3d}/{len(universe)}] {bin_sym:10s} "
              f"(rank {coin['rank']:3d}) … ", end="", flush=True)
        try:
            wk_prices = fetch_binance_weekly(bin_sym, start=BACKTEST_START)
            if len(wk_prices) < MIN_WEEKS:
                print(f"insufficient history ({len(wk_prices)} weeks)")
                n_failed += 1
                continue
            wk_ret = to_weekly(wk_prices)
            if len(wk_ret) < MIN_WEEKS:
                print(f"only {len(wk_ret)} weekly obs")
                n_failed += 1
                continue
            weekly_ret_dict[coin["symbol"]] = wk_ret
            print(f"OK ({len(wk_ret)} weeks, "
                  f"{wk_ret.index[0].date()} → {wk_ret.index[-1].date()})")
        except Exception as e:
            print(f"FAILED: {e}")
            n_failed += 1

    print(f"\n  Successfully fetched: {len(weekly_ret_dict)} coins  "
          f"({n_failed} failed/skipped)")
    if len(weekly_ret_dict) < 20:
        print("ERROR: Too few coins. Exiting."); return

    # ── 4. Build return matrix and IC analysis ────────────────────────────────
    print("\n[4/5] Cross-sectional IC analysis…")
    ret_matrix = build_return_matrix(weekly_ret_dict)
    print(f"  Return matrix: {ret_matrix.shape[0]} weeks × {ret_matrix.shape[1]} coins")
    print(f"  Period: {ret_matrix.index[0].date()} → {ret_matrix.index[-1].date()}")
    print(f"  Median data coverage: {ret_matrix.notna().mean(axis=1).median():.1%} per week")

    # Full IC series
    ic_series = compute_ic_series(ret_matrix[ret_matrix.index >= BACKTEST_START])
    print(f"\n  IC series: {len(ic_series)} weeks")

    if len(ic_series) == 0:
        print("ERROR: No valid IC weeks computed."); return

    ic_full = ic_series.mean()
    n_ic    = len(ic_series)
    ic_t, ic_p = ttest_1samp(ic_series.dropna(), 0)
    ic_sem  = ic_series.std() / np.sqrt(n_ic)

    print(f"\n  ── OVERALL IC (full period {BACKTEST_START} → present) ──")
    print(f"    Mean IC    : {ic_full:+.4f}")
    print(f"    IC t-stat  : {ic_t:+.3f}  (p={ic_p:.4f})")
    print(f"    IC std     : {ic_series.std():.4f}")
    print(f"    IC > 0 pct : {(ic_series > 0).mean():.1%}")
    print(f"    N weeks    : {n_ic}")
    print(f"    Expected from Zaremba (2021): t-stat > 3.0 on top-100 to top-500")

    # Sub-period stability
    for period_name, mask in [
        (f"Train {BACKTEST_START}–{TEST_SPLIT[:7]}", ic_series.index < TEST_SPLIT),
        (f"Test  {TEST_SPLIT[:7]}–present",          ic_series.index >= TEST_SPLIT),
    ]:
        s = ic_series[mask].dropna()
        if len(s) < 5:
            print(f"  {period_name}: insufficient data")
            continue
        t_sub = ttest_1samp(s, 0).statistic
        print(f"  {period_name}: IC={s.mean():+.4f}  t={t_sub:+.2f}  n={len(s)}")

    # Best / worst weeks
    top5_wk  = ic_series.nlargest(5)
    bot5_wk  = ic_series.nsmallest(5)
    print(f"\n  Top-5 IC weeks: {list(zip(top5_wk.index.date, top5_wk.round(3)))}")
    print(f"  Bot-5 IC weeks: {list(zip(bot5_wk.index.date, bot5_wk.round(3)))}")

    # ── 5. Portfolio backtest ─────────────────────────────────────────────────
    print("\n[5/5] Portfolio backtest (long-only top-10 reversals)…")
    res_full  = portfolio_backtest(ret_matrix, tsmom_wk, start=BACKTEST_START)
    res_train = portfolio_backtest(ret_matrix, tsmom_wk, start=BACKTEST_START,
                                   n_long=N_LONG, cost_rt=COST_RT)
    res_test  = portfolio_backtest(ret_matrix, tsmom_wk, start=TEST_SPLIT)
    # Re-run with test dates only for the sub-period backtest
    res_train_only = portfolio_backtest(
        ret_matrix[ret_matrix.index < TEST_SPLIT], tsmom_wk,
        start=BACKTEST_START
    )
    res_test_only  = portfolio_backtest(
        ret_matrix[ret_matrix.index >= TEST_SPLIT], tsmom_wk,
        start=TEST_SPLIT
    )

    print(f"\n  ── PORTFOLIO RESULTS ──")
    for name, res in [("Full period", res_full),
                       (f"Train (<{TEST_SPLIT[:7]})", res_train_only),
                       (f"Test  (≥{TEST_SPLIT[:7]})", res_test_only)]:
        print(f"  {name:25s}  Sharpe={res['sharpe']:+.3f}  "
              f"MaxDD={res['maxdd']*100:.1f}%  "
              f"corr(TSMOM)={res['corr_tsmom']:.3f}  "
              f"n={res['n_weeks']}")

    # Figure
    make_figure(ic_series, ic_full, ic_t, res_full,
                res_train_only, res_test_only, ret_matrix, tsmom_wk)

    # ── VERDICT ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    stable  = (ic_series[ic_series.index < TEST_SPLIT].mean() > 0 and
               ic_series[ic_series.index >= TEST_SPLIT].mean() > 0)
    sig_ic  = abs(ic_t) > 2.0
    good_corr = abs(res_full["corr_tsmom"]) < 0.40
    sh = res_full["sharpe"]

    print(f"  IC t-stat (full period):  {ic_t:+.3f}  "
          f"({'✓ significant' if sig_ic else '✗ not significant'} at t>2)")
    print(f"  IC consistent (both sub-periods): {'✓ YES' if stable else '✗ NO'}")
    print(f"  corr(TSMOM): {res_full['corr_tsmom']:+.3f}  "
          f"({'✓ diversifying' if good_corr else '✗ too correlated'})")
    print(f"  Portfolio Sharpe (full): {sh:+.3f}")
    print()
    print(f"  ⚠ Survivorship bias: universe = current top-{RANK_MAX} "
          f"(historical rankings unavailable via free API)")
    print(f"  ⚠ Execution venue: CANNOT run on Hyperliquid "
          f"(small-caps not listed there)")
    print(f"     Requires: Binance Spot, KuCoin, Gate.io, or similar")
    print()

    if sig_ic and stable and sh > 0.6 and good_corr:
        verdict = "STRONG — Zaremba effect confirmed; plan execution venue separately"
    elif sig_ic and stable and good_corr:
        verdict = "PROMISING — IC real, but Sharpe may be overstated by survivorship bias"
    elif sig_ic and not stable:
        verdict = "WEAK — IC significant full-period but sub-period inconsistency"
    elif not sig_ic:
        verdict = "SKIP — IC not significant; large-cap failure extends to this universe"
    else:
        verdict = "WEAK — IC real but Sharpe too low vs costs at this fee level"

    print(f"  >>> {verdict}")
    print()
    print("  Comparison to 6.8 large-cap STR (DO NOT RE-TEST):")
    print("    6.8 (large-cap, top-20): IC t-stat 0.85 → SKIP")
    print(f"    6.24 (rank {RANK_MIN}-{RANK_MAX}): IC t-stat {ic_t:.2f} "
          f"(Zaremba predicts >3.0)")
    print()
    print("  If STRONG/PROMISING: next step = verify with HISTORICAL market-cap")
    print("    rankings to eliminate survivorship bias before live deployment.")


if __name__ == "__main__":
    main()
