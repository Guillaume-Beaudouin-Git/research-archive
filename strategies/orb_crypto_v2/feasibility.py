"""
ORB Crypto v2 — Asian Session Range Breakout Feasibility
Signal 30 in Strategy C search.

Adapted from Fabio Valentini NQ ORB model (2021–2026, Sharpe ~1.4,
P(EV≤0)=0.001, 823 trades, profit factor 1.28 net costs).

Why a different mechanism than TSMOM:
  TSMOM: 28-day cumulative return → captures multi-week directional drift.
  ORB:   Asian session equilibrium → intraday reaction to range boundary.
  Different timescale, different session, structurally zero construction correlation.

Signal timeline (all times UTC, 4h candles indexed by OPEN time):
  00:00 candle  → covers 00:00-04:00  (Asian open bar 1)
  04:00 candle  → covers 04:00-08:00  (Asian open bar 2)
  08:00 candle  → covers 08:00-12:00  (EU/US reaction bar — closes at 12:00)
  12:00 candle  → ENTRY bar (open = entry price)
  16:00 candle  → second hold bar (close = 20:00 UTC = EOD)

Asian range:
  range_high = max(high_00h, high_04h)
  range_low  = min(low_00h,  low_04h)

Breakout signal (confirmed at CLOSE of 08:00 candle = 12:00 UTC, no look-ahead):
  close_08h > range_high  →  LONG

Delta filter proxy (no tick data on HL):
  bar_body_ratio = (close - open) / (high - low + ε)
  Both 00h AND 04h candles must have bar_body_ratio > threshold

Trade:
  Entry : open of 12:00 UTC candle
  TP    : entry + 1.0 × (range_high - range_low)
  SL    : range_low
  EOD   : close of 16:00-20:00 candle (20:00 UTC)
  Cost  : 0.17% RT

Data: HL candleSnapshot 4h, BTC + ETH, 2022-01 → 2026-05.
NOTE: HL data gap Dec 2022 – Dec 2023; those periods are naturally absent.

Run: python strategies/orb_crypto_v2/feasibility.py
"""
from __future__ import annotations

import time as _time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
_rng = np.random.default_rng(42)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

UNIVERSE      = ["BTC", "ETH"]
START         = "2022-01-01"
END           = "2026-05-14"
HL_API        = "https://api.hyperliquid.xyz/info"
INTERVAL_MS   = 4 * 3600 * 1000     # 4 hours in milliseconds
CHUNK         = 5000                 # candles per API batch
COST_RT       = 0.0017              # 0.17% round-trip
TP_MULT       = 1.0                  # TP = entry + TP_MULT × range_width
N_BOOT        = 10_000               # bootstrap iterations
TSMOM_ROLL    = 28                   # TSMOM lookback days

# Three delta-filter configs tested
FILTER_CONFIGS: list[tuple[str, float]] = [
    ("no_filter", 0.00),
    ("mild",      0.20),
    ("strict",    0.40),
]

OUT_DIR = Path(__file__).parent


# ─── DATA LOADING ─────────────────────────────────────────────────────────────

def fetch_hl_4h(coin: str, start: str = START, end: str = END) -> pd.DataFrame:
    """
    Fetch 4h OHLCV from HL candleSnapshot API, chunked to handle long periods.
    Returns DataFrame indexed by UTC open time.

    HL data gap Dec 2022 – Dec 2023: the API returns no candles for that window;
    those periods will simply be absent from the result (not NaN-filled).
    """
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms   = int(pd.Timestamp(end,   tz="UTC").timestamp() * 1000)
    all_rows: list = []
    cur = start_ms

    while cur < end_ms:
        batch_end = min(cur + CHUNK * INTERVAL_MS, end_ms)
        payload   = {
            "type": "candleSnapshot",
            "req":  {"coin": coin, "interval": "4h",
                     "startTime": cur, "endTime": batch_end},
        }
        try:
            r = requests.post(HL_API, json=payload, timeout=30)
            r.raise_for_status()
            candles = r.json()
        except Exception as exc:
            print(f"  [{coin}] API error: {exc}")
            candles = []

        if not candles:
            cur = batch_end + INTERVAL_MS
            _time.sleep(0.05)
            continue

        all_rows.extend(candles)
        cur = int(candles[-1]["t"]) + INTERVAL_MS
        _time.sleep(0.05)

    if not all_rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    # HL API returns list-of-dicts: {t, T, s, i, o, c, h, l, v, n}
    df = pd.DataFrame(all_rows)
    df["time"] = pd.to_datetime(df["t"].astype(np.int64), unit="ms", utc=True)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    df = (df.set_index("time")[["open", "high", "low", "close", "volume"]]
            .astype(float)
            .sort_index())
    df = df[~df.index.duplicated(keep="last")]
    return df


def load_all_data() -> dict[str, pd.DataFrame]:
    print(f"\n{'='*70}")
    print(f"STEP 1 — LOAD HL 4h CANDLES  ({START} → {END})")
    print(f"{'='*70}")
    result: dict[str, pd.DataFrame] = {}
    for coin in UNIVERSE:
        print(f"  {coin} ...", end=" ", flush=True)
        df = fetch_hl_4h(coin)
        if df.empty:
            print("NO DATA — skipping")
            continue
        result[coin] = df
        n_days = df.index.normalize().nunique()
        print(f"{len(df)} bars  {n_days} unique days  "
              f"({df.index[0].strftime('%Y-%m-%d')} → "
              f"{df.index[-1].strftime('%Y-%m-%d')})")
    print(f"  HL data gap Dec 2022 – Dec 2023 expected (candleSnapshot limitation)")
    return result


# ─── SIGNAL GENERATION ────────────────────────────────────────────────────────

def _body_ratio(bar: pd.Series) -> float:
    """Bar body ratio: (close - open) / (high - low). +1 = full bullish candle."""
    span = float(bar["high"]) - float(bar["low"])
    if span < 1e-10:
        return 0.0
    return (float(bar["close"]) - float(bar["open"])) / span


def build_signals(df: pd.DataFrame, body_thr: float) -> pd.DataFrame:
    """
    Identify ORB breakout opportunities for one coin.

    No look-ahead: the range and filter are fully defined by candles closing at
    08:00 UTC (00h) and 12:00 UTC (04h + 08h). The 08h candle closes at 12:00.
    Entry is at the OPEN of the NEXT candle (12:00), which begins the same moment
    the 08h candle closes — no gap-risk, no forward data used.

    Returns one row per triggered signal day.
    """
    rows: list[dict] = []

    zero_bars = df.index[df.index.hour == 0]
    for ts_00 in zero_bars:
        ts_04 = ts_00 + pd.Timedelta(hours=4)
        ts_08 = ts_00 + pd.Timedelta(hours=8)
        ts_12 = ts_00 + pd.Timedelta(hours=12)
        ts_16 = ts_00 + pd.Timedelta(hours=16)

        # Mandatory bars: 00h, 04h, 08h for signal; 12h for entry
        if ts_04 not in df.index or ts_08 not in df.index or ts_12 not in df.index:
            continue

        b00 = df.loc[ts_00]
        b04 = df.loc[ts_04]
        b08 = df.loc[ts_08]
        b12 = df.loc[ts_12]

        # Asian session range (bars 00h and 04h, both closed before breakout check)
        r_high = max(float(b00["high"]), float(b04["high"]))
        r_low  = min(float(b00["low"]),  float(b04["low"]))
        r_wid  = r_high - r_low
        if r_wid <= 0 or np.isnan(r_wid):
            continue

        # Breakout: close of 08h candle (= 12:00 UTC) > Asian range high
        c08 = float(b08["close"])
        if np.isnan(c08) or c08 <= r_high:
            continue

        # Delta filter: both Asian candles must be net bullish by body_thr
        if _body_ratio(b00) <= body_thr or _body_ratio(b04) <= body_thr:
            continue

        entry = float(b12["open"])
        if np.isnan(entry) or entry <= 0:
            continue

        rows.append({
            "date":        ts_00.date(),
            "ts_12":       ts_12,
            "ts_16":       ts_16 if ts_16 in df.index else None,
            "range_high":  r_high,
            "range_low":   r_low,
            "range_width": r_wid,
            "close_08":    c08,
            "br_00":       _body_ratio(b00),
            "br_04":       _body_ratio(b04),
            "entry":       entry,
            "tp":          entry + TP_MULT * r_wid,
            "sl":          r_low,
        })

    return pd.DataFrame(rows)


# ─── TRADE SIMULATION ─────────────────────────────────────────────────────────

def _check_bar(ts, entry: float, tp: float, sl: float,
               df: pd.DataFrame) -> tuple[bool, float, str]:
    """
    Check one 4h bar for TP/SL hit.
    Conservative assumption: if both levels are touched within the bar, SL hit first
    (protects against overstating win rate).
    Returns (exited, exit_price, reason).
    """
    if ts is None or ts not in df.index:
        return False, entry, "missing"
    bar = df.loc[ts]
    lo = float(bar["low"])
    hi = float(bar["high"])
    if lo <= sl:
        return True, sl, "SL"
    if hi >= tp:
        return True, tp, "TP"
    return False, entry, "hold"


def simulate_trade(row: pd.Series, df: pd.DataFrame) -> dict:
    """
    Simulate one ORB long trade through 12:00 and 16:00 candles.

    Hold logic:
      1. Check 12:00 candle (entry at its open, TP/SL can hit within it)
      2. If still open: check 16:00 candle
      3. If still open: EOD exit at close of 16:00 candle (= 20:00 UTC)

    P&L: (exit_price - entry) / entry − COST_RT
    """
    entry = row["entry"]
    tp    = row["tp"]
    sl    = row["sl"]
    ts_12 = row["ts_12"]
    ts_16 = row["ts_16"]

    # Check entry candle (12:00-16:00)
    exited, exit_px, reason = _check_bar(ts_12, entry, tp, sl, df)

    if not exited:
        # Check second hold candle (16:00-20:00)
        exited, exit_px, reason = _check_bar(ts_16, entry, tp, sl, df)
        if not exited:
            # EOD: close of 16:00 candle = 20:00 UTC
            if ts_16 is not None and ts_16 in df.index:
                exit_px = float(df.loc[ts_16, "close"])
            else:
                exit_px = entry   # 0 gross P&L if bar missing (rare)
            reason = "EOD"

    pnl_gross = (exit_px - entry) / entry
    pnl_net   = pnl_gross - COST_RT

    return {
        "exit_px":    exit_px,
        "pnl_gross":  pnl_gross,
        "pnl_net":    pnl_net,
        "exit_reason": reason,
    }


# ─── BACKTEST ─────────────────────────────────────────────────────────────────

def run_backtest(data: dict[str, pd.DataFrame],
                 body_thr: float, label: str) -> dict:
    """
    Run full ORB backtest for one filter config across all coins.

    Portfolio P&L: equal-weight average of all coins with a signal on a given day.
    At most 2 simultaneous positions (BTC and ETH on the same day).
    """
    all_trades: list[dict] = []

    for coin, df in data.items():
        signals = build_signals(df, body_thr)
        if signals.empty:
            continue
        for _, row in signals.iterrows():
            trade = simulate_trade(row, df)
            all_trades.append({
                "coin":        coin,
                "date":        row["date"],
                "entry":       row["entry"],
                "tp":          row["tp"],
                "sl":          row["sl"],
                "range_width": row["range_width"],
                "br_00":       row["br_00"],
                "br_04":       row["br_04"],
                **trade,
            })

    if not all_trades:
        return {"label": label, "trades": pd.DataFrame(),
                "daily_pnl": pd.Series(dtype=float)}

    trades = pd.DataFrame(all_trades)
    trades["date"] = pd.to_datetime(trades["date"])

    # Equal-weight daily P&L (average across coins active that day)
    daily_pnl = trades.groupby("date")["pnl_net"].mean()

    return {"label": label, "trades": trades, "daily_pnl": daily_pnl}


# ─── METRICS ──────────────────────────────────────────────────────────────────

def compute_metrics(bt: dict) -> dict:
    """
    Compute Sharpe, profit factor, P(EV≤0), per-year sub-periods, exit breakdown.
    Bootstrap: 10,000 resamples of trade-level P&L.
    """
    label  = bt["label"]
    trades = bt["trades"]
    daily  = bt["daily_pnl"]

    empty = {"label": label, "n_trades": 0, "sharpe": 0.0,
             "profit_factor": 0.0, "p_ev_zero": 1.0,
             "mdd": 0.0, "ann_ret": 0.0, "trades_per_yr": 0.0,
             "win_rate": 0.0, "avg_win_pct": 0.0, "avg_loss_pct": 0.0,
             "sub_periods": {}, "exit_reasons": {}, "bootstrap_means": np.array([])}

    if trades.empty or len(daily) < 5:
        return empty

    pnl_arr = trades["pnl_net"].values
    winners = pnl_arr[pnl_arr > 0]
    losers  = pnl_arr[pnl_arr <= 0]

    gross_p = float(winners.sum()) if len(winners) else 0.0
    gross_l = float(abs(losers.sum())) if len(losers) else 1e-10
    pf      = gross_p / gross_l

    win_rate = float((pnl_arr > 0).mean())
    avg_win  = float(winners.mean()) if len(winners) else 0.0
    avg_loss = float(losers.mean())  if len(losers)  else 0.0

    # Sharpe on daily P&L (annualised, 252 trading-day convention)
    sharpe = float(daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else 0.0

    # Max drawdown on equity curve
    eq  = (1 + daily).cumprod()
    hwm = eq.cummax()
    mdd = float(((eq - hwm) / hwm).min())

    # Annualised return
    years   = max((daily.index[-1] - daily.index[0]).days / 365.25, 0.1)
    ann_ret = float(eq.iloc[-1] ** (1.0 / years) - 1)
    tpy     = len(trades) / years

    # Bootstrap P(EV ≤ 0): distribution of mean trade return under resampling
    boots = np.array([
        _rng.choice(pnl_arr, size=len(pnl_arr), replace=True).mean()
        for _ in range(N_BOOT)
    ])
    p_ev_zero = float((boots <= 0).mean())

    # Sub-period Sharpe by calendar year
    sub: dict[int, dict] = {}
    for yr in [2022, 2023, 2024, 2025, 2026]:
        mask_d = daily.index.year == yr
        mask_t = trades["date"].dt.year == yr
        if mask_d.sum() < 5:
            continue
        d  = daily[mask_d]
        sp = float(d.mean() / d.std() * np.sqrt(252)) if d.std() > 0 else 0.0
        sub[yr] = {"sharpe": round(sp, 3), "n_trades": int(mask_t.sum())}

    return {
        "label":          label,
        "n_trades":       len(trades),
        "trades_per_yr":  round(tpy, 1),
        "win_rate":       win_rate,
        "avg_win_pct":    round(avg_win  * 100, 3),
        "avg_loss_pct":   round(avg_loss * 100, 3),
        "profit_factor":  round(pf,     3),
        "sharpe":         round(sharpe, 3),
        "mdd":            round(mdd,    4),
        "ann_ret":        round(ann_ret, 4),
        "p_ev_zero":      round(p_ev_zero, 4),
        "sub_periods":    sub,
        "exit_reasons":   trades["exit_reason"].value_counts().to_dict(),
        "bootstrap_means": boots,
        "daily_pnl":      daily,
        "eq_curve":       eq,
    }


# ─── TSMOM CORRELATION ────────────────────────────────────────────────────────

def compute_tsmom_daily(data: dict[str, pd.DataFrame]) -> pd.Series:
    """
    TSMOM v3 portfolio daily return on BTC+ETH (same period as ORB backtest).
    signal = tanh(cumret_28d / (vol_28d × √28)), long-only, 15% vol target.
    Uses daily close resampled from 4h HL data (consistent data source).
    """
    parts: list[pd.Series] = []
    for coin, df in data.items():
        if df.empty:
            continue
        close   = df["close"].resample("1D").last().dropna()
        log_ret = np.log(close / close.shift(1)).dropna()
        cum28   = log_ret.rolling(TSMOM_ROLL).sum().shift(1)
        vol28   = log_ret.rolling(TSMOM_ROLL).std().shift(1)
        signal  = np.tanh(cum28 / (vol28 * np.sqrt(TSMOM_ROLL) + 1e-12)).clip(lower=0)
        vs      = (0.15 / (vol28 * np.sqrt(252) + 1e-12)).clip(0.1, 2.0)
        parts.append((signal * vs * log_ret).dropna())

    if not parts:
        return pd.Series(dtype=float)
    return pd.concat(parts, axis=1).mean(axis=1).dropna()


def pearson_corr(a: pd.Series, b: pd.Series) -> float:
    common = a.index.intersection(b.index)
    if len(common) < 10:
        return float("nan")
    return float(a.reindex(common).corr(b.reindex(common)))


# ─── PRINT RESULTS ────────────────────────────────────────────────────────────

def print_metrics_table(all_metrics: list[dict],
                        tsmom_corrs: dict[str, float]) -> None:
    print(f"\n{'='*70}")
    print("STEP 3 — BACKTEST RESULTS BY FILTER CONFIG")
    print(f"{'='*70}")

    for m in all_metrics:
        lbl  = m["label"]
        corr = tsmom_corrs.get(lbl, float("nan"))
        print(f"\n  ── {lbl} (body_ratio > "
              f"{dict(FILTER_CONFIGS)[lbl]:.2f}) ──────────────────────")
        print(f"  Trades:        {m['n_trades']}  "
              f"({m['trades_per_yr']:.0f}/yr)")
        print(f"  Win rate:      {m['win_rate']:.1%}  "
              f"(avg win {m['avg_win_pct']:+.2f}%  "
              f"avg loss {m['avg_loss_pct']:+.2f}%)")
        print(f"  Profit factor: {m['profit_factor']:.3f}  "
              f"({'PASS' if m['profit_factor'] > 1.0 else 'FAIL'} vs 1.0)")
        print(f"  Sharpe:        {m['sharpe']:+.3f}  "
              f"({'PASS' if m['sharpe'] > 0.8 else 'WEAK' if m['sharpe'] > 0.5 else 'FAIL'})")
        print(f"  MaxDD:         {m['mdd']:.1%}")
        print(f"  Annual ret:    {m['ann_ret']:.1%}")
        print(f"  P(EV≤0):       {m['p_ev_zero']:.4f}  "
              f"({'PASS' if m['p_ev_zero'] < 0.05 else 'FAIL'} vs <0.05)")
        print(f"  corr(TSMOM):   {corr:+.3f}  "
              f"({'PASS' if abs(corr) < 0.30 else 'WARN' if abs(corr) < 0.50 else 'FAIL'})")
        if m.get("exit_reasons"):
            reasons_str = " | ".join(
                f"{k}:{v}" for k, v in sorted(m["exit_reasons"].items()))
            print(f"  Exit reasons:  {reasons_str}")
        if m.get("sub_periods"):
            print(f"  Sub-periods (Sharpe / n_trades):")
            for yr, sp in sorted(m["sub_periods"].items()):
                note = ""
                if yr == 2022 and sp["n_trades"] < 5:
                    note = " ← insufficient data (HL gap)"
                elif yr <= 2023:
                    note = " ← bear / recovery"
                elif yr >= 2024:
                    note = " ← bull"
                print(f"    {yr}: {sp['sharpe']:+.3f}  n={sp['n_trades']}{note}")


def print_verdict(all_metrics: list[dict],
                  tsmom_corrs: dict[str, float]) -> str:
    """Evaluate DEPLOY / PROMISING / SKIP criteria and print structured verdict."""
    print(f"\n{'='*70}")
    print("VERDICT")
    print(f"{'='*70}")

    # Primary evaluation uses strict filter (most demanding)
    primary = next(
        (m for m in all_metrics if m["label"] == "strict"),
        all_metrics[-1],
    )
    corr   = tsmom_corrs.get(primary["label"], 1.0)
    sharpe = primary["sharpe"]
    p_ev   = primary["p_ev_zero"]
    sub    = primary.get("sub_periods", {})

    # Bear-period check (2022 or 2023 as best available bear data)
    bear_yr   = 2022 if 2022 in sub and sub[2022]["n_trades"] >= 5 else 2023
    bear_data = sub.get(bear_yr, {})
    bear_pos  = bear_data.get("sharpe", 0.0) > 0
    bear_n    = bear_data.get("n_trades", 0)
    bear_ok   = bear_pos or bear_n < 5  # insufficient data ≠ bear failure

    # Only-bull test: bear/recovery negative, 2024+ positive
    bear_neg = (sub.get(2022, {}).get("sharpe", 0.0) <= 0 or
                sub.get(2023, {}).get("sharpe", 0.0) <= 0)
    bull_pos = (sub.get(2024, {}).get("sharpe", 0.0) > 0 or
                sub.get(2025, {}).get("sharpe", 0.0) > 0)
    bear_n_sufficient = (sub.get(2022, {}).get("n_trades", 0) +
                         sub.get(2023, {}).get("n_trades", 0)) >= 10

    only_bull = bear_neg and bull_pos and bear_n_sufficient

    # Decide
    if only_bull:
        verdict = "SKIP"
        reason  = "Only profitable in bull era — correlated with BTC beta, not ORB alpha"
    elif abs(corr) > 0.50:
        verdict = "SKIP"
        reason  = (f"corr(TSMOM)={corr:+.3f} > 0.50 — "
                   f"same directional exposure as TSMOM")
    elif sharpe > 0.8 and p_ev < 0.05 and abs(corr) < 0.30 and bear_ok:
        verdict = "DEPLOY"
        reason  = (f"Sharpe={sharpe:.3f}, P(EV≤0)={p_ev:.4f}, "
                   f"corr(TSMOM)={corr:+.3f}, bear period {'positive' if bear_pos else 'no data'}")
    elif sharpe > 0.5 or (0.3 < sharpe <= 0.5 and abs(corr) < 0.30):
        verdict = "PROMISING"
        reason  = (f"Sharpe={sharpe:.3f} in promising range; "
                   f"further data or param tuning may push above 0.8 threshold")
    else:
        verdict = "SKIP"
        reason  = (f"Sharpe={sharpe:.3f} < 0.5 and/or P(EV≤0)={p_ev:.4f} ≥ 0.05")

    # Comparison grid
    header = f"  {'Metric':<26} {'no_filter':>10} {'mild':>10} {'strict':>10}  Threshold  Status"
    print(f"\n{header}")
    print(f"  {'-'*76}")

    def _row(name: str, getter, thr: float, higher_better: bool) -> None:
        vals = [getter(m) for m in all_metrics]
        row  = f"  {name:<26}"
        for v in vals:
            row += f" {v:>10.3f}"
        v_strict = vals[-1]
        passed = v_strict >= thr if higher_better else v_strict <= thr
        op = ">" if higher_better else "<"
        row += f"  {op}{thr:<10} {'PASS' if passed else 'FAIL'}"
        print(row)

    _row("Sharpe (strict)",    lambda m: m["sharpe"],        0.8,  True)
    _row("P(EV≤0)",           lambda m: m["p_ev_zero"],     0.05, False)
    _row("|corr(TSMOM)|",     lambda m: abs(tsmom_corrs.get(m["label"], 1.0)), 0.30, False)
    _row("Profit factor",     lambda m: m["profit_factor"], 1.0,  True)

    if bear_n >= 5:
        print(f"\n  Bear period ({bear_yr}): "
              f"Sharpe={bear_data['sharpe']:+.3f}  n={bear_n}  "
              f"{'POSITIVE ✓' if bear_pos else 'NEGATIVE ✗'}")
    else:
        print(f"\n  Bear period: insufficient HL data (n={bear_n} trades) — "
              f"HL gap Dec 2022 – Dec 2023 limits bear evaluation")

    print(f"\n  >>> {verdict} — {reason}")

    if verdict == "DEPLOY":
        print(f"\n  Recommended next step:")
        print(f"    1. Live paper trade for 30 days (BTC + ETH, 12:00 UTC entry)")
        print(f"    2. Check corr(ORB_live, TSMOM_live) after 50 trades")
        print(f"    3. Size as Strategy C at w_C = 0.15 in A+B+C portfolio")
    elif verdict == "PROMISING":
        print(f"\n  Recommended next step:")
        print(f"    1. Try longer EOD window (hold through next day) or wider TP (1.5R)")
        print(f"    2. Test with ETH-only universe (ETH may have stronger Asian session effect)")
    else:
        print(f"\n  ORB v2 on 4h HL data does not meet Strategy C threshold.")
        print(f"  The Asian session range breakout mechanism may work at higher frequency")
        print(f"  (1h or 30min data) but HL candleSnapshot only provides 4h resolution.")

    return verdict


# ─── PLOTTING ─────────────────────────────────────────────────────────────────

def plot_results(all_metrics: list[dict],
                 tsmom_corrs: dict[str, float],
                 save_path: Path = OUT_DIR / "feasibility_results.png") -> None:
    """
    4-subplot figure matching Fabio Valentini paper style:
      1. Equity curves (BTC+ETH combined) — all 3 filter configs
      2. Win/loss distribution — TP/SL/EOD exit breakdown (bar chart)
      3. Sub-period annual Sharpe — 2022/2023/2024/2025 by config
      4. Bootstrap EV distribution — P(EV≤0) histogram
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    ax1, ax2 = axes[0]
    ax3, ax4 = axes[1]

    fig.suptitle(
        "ORB Crypto v2 — Asian Session Breakout Feasibility\n"
        "BTC + ETH, HL 4h data  |  Entry: 12:00 UTC  |  EOD: 20:00 UTC  |  0.17% RT",
        fontsize=12, fontweight="bold", y=0.98,
    )

    COLORS = {"no_filter": "#95a5a6", "mild": "#3498db", "strict": "#2ecc71"}
    LABELS = {"no_filter": "No filter (>0.00)",
              "mild":      "Mild filter (>0.20)",
              "strict":    "Strict filter (>0.40)"}

    # ── Subplot 1: Equity curves ───────────────────────────────────────────────
    ax1.set_title("Equity Curve — 3 Filter Configs\n($10k normalised)",
                  fontsize=10)
    has_data = False
    for m in all_metrics:
        eq = m.get("eq_curve")
        if eq is None or len(eq) < 2:
            continue
        normalised = eq / eq.iloc[0] * 10_000
        ax1.plot(eq.index, normalised.values,
                 color=COLORS[m["label"]], lw=1.6, alpha=0.85,
                 label=f"{LABELS[m['label']]}  Sharpe={m['sharpe']:+.2f}")
        has_data = True
    if has_data:
        ax1.axhline(10_000, color="black", ls="--", lw=0.8, alpha=0.5)
        ax1.set_ylabel("Portfolio value ($)")
        ax1.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.2)
    else:
        ax1.text(0.5, 0.5, "No backtest data", ha="center", va="center",
                 transform=ax1.transAxes, color="gray", fontsize=12)

    # ── Subplot 2: Exit reason breakdown (bar chart) ───────────────────────────
    ax2.set_title("Exit Reason Distribution by Filter Config", fontsize=10)
    exit_types = ["TP", "SL", "EOD"]
    ec = {"TP": "#2ecc71", "SL": "#e74c3c", "EOD": "#f39c12"}
    x  = np.arange(len(FILTER_CONFIGS))
    width = 0.25
    for i, etype in enumerate(exit_types):
        counts = []
        for m in all_metrics:
            er = m.get("exit_reasons", {})
            total = sum(er.values()) or 1
            counts.append(er.get(etype, 0) / total * 100)
        ax2.bar(x + i * width, counts, width,
                label=etype, color=ec[etype], alpha=0.8, edgecolor="white")
    ax2.set_xticks(x + width)
    ax2.set_xticklabels([LABELS[lbl].split(" ")[0]
                         for lbl, _ in FILTER_CONFIGS], fontsize=9)
    ax2.set_ylabel("% of trades")
    ax2.set_ylim(0, 100)
    ax2.legend(fontsize=9)
    ax2.grid(True, axis="y", alpha=0.2)

    # ── Subplot 3: Sub-period Sharpe ───────────────────────────────────────────
    ax3.set_title("Annual Sharpe by Year and Filter Config", fontsize=10)
    years = sorted({yr for m in all_metrics for yr in m.get("sub_periods", {})})
    if years:
        x3 = np.arange(len(years))
        n  = len(all_metrics)
        bar_w = 0.8 / n
        for j, m in enumerate(all_metrics):
            sub = m.get("sub_periods", {})
            sharpes = [sub.get(yr, {}).get("sharpe", 0.0) for yr in years]
            ns      = [sub.get(yr, {}).get("n_trades", 0) for yr in years]
            bars = ax3.bar(x3 + j * bar_w - 0.4 + bar_w / 2,
                           sharpes, bar_w,
                           color=COLORS[m["label"]], alpha=0.8,
                           label=LABELS[m["label"]].split(" ")[0], edgecolor="white")
            for bar, n_tr, yr_val in zip(bars, ns, sharpes):
                if n_tr > 0:
                    ax3.text(bar.get_x() + bar.get_width() / 2,
                             yr_val + (0.02 if yr_val >= 0 else -0.08),
                             f"n={n_tr}", ha="center", va="bottom",
                             fontsize=6.5, rotation=90)
        ax3.axhline(0, color="black", lw=0.8, ls="--")
        ax3.axhline(0.8, color="#27ae60", lw=1.0, ls=":", alpha=0.7,
                    label="Deploy threshold (0.8)")
        ax3.set_xticks(x3)
        ax3.set_xticklabels(
            [f"{yr}{'†' if yr <= 2023 else ''}" for yr in years], fontsize=9)
        ax3.set_ylabel("Sharpe")
        ax3.legend(fontsize=7)
        ax3.grid(True, axis="y", alpha=0.2)
        ax3.text(0.01, 0.02, "† limited data (HL gap)",
                 transform=ax3.transAxes, fontsize=7, color="gray")
    else:
        ax3.text(0.5, 0.5, "No sub-period data", ha="center", va="center",
                 transform=ax3.transAxes, color="gray", fontsize=12)

    # ── Subplot 4: Bootstrap EV distribution ──────────────────────────────────
    ax4.set_title("Bootstrap Mean Trade Return — P(EV ≤ 0)\n"
                  "(10,000 resamples with replacement)", fontsize=10)
    for m in all_metrics:
        boots = m.get("bootstrap_means")
        if boots is None or len(boots) == 0:
            continue
        p_ev = m["p_ev_zero"]
        ax4.hist(boots * 100, bins=80, alpha=0.55,
                 color=COLORS[m["label"]], edgecolor="none",
                 label=f"{LABELS[m['label']].split(' ')[0]}  P(EV≤0)={p_ev:.4f}")
    ax4.axvline(0, color="red", lw=1.5, ls="--", label="EV = 0")
    ax4.set_xlabel("Mean trade return (%)")
    ax4.set_ylabel("Frequency")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.2)

    # ── Correlation annotation ─────────────────────────────────────────────────
    corr_lines = [
        f"corr(ORB, TSMOM): "
        + "  ".join(f"{lbl}={tsmom_corrs.get(lbl, float('nan')):+.3f}"
                    for lbl, _ in FILTER_CONFIGS)
    ]
    fig.text(0.5, 0.01, "  |  ".join(corr_lines),
             ha="center", fontsize=9, color="#555555",
             style="italic")

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Figure saved → {save_path}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main() -> None:
    import time
    t0 = time.time()

    print("=" * 70)
    print("ORB CRYPTO v2 — ASIAN SESSION RANGE BREAKOUT")
    print("Signal 30 — Strategy C candidate")
    print("=" * 70)

    # ── 1. Data ────────────────────────────────────────────────────────────────
    data = load_all_data()
    if not data:
        print("No data available — exiting.")
        return

    # ── 2. Run 3 filter configs ────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 2 — SIGNAL GENERATION + BACKTEST (3 filter configs)")
    print(f"{'='*70}")

    all_bt: list[dict]      = []
    all_metrics: list[dict] = []

    for label, body_thr in FILTER_CONFIGS:
        print(f"\n  Running config: {label}  (body_ratio > {body_thr:.2f})")
        bt = run_backtest(data, body_thr, label)
        n_trades = len(bt["trades"]) if not bt["trades"].empty else 0
        n_days   = bt["daily_pnl"].notna().sum() if not bt["daily_pnl"].empty else 0
        print(f"  → {n_trades} trades  |  {n_days} active days")
        all_bt.append(bt)
        m = compute_metrics(bt)
        all_metrics.append(m)

    # ── 3. TSMOM correlation ───────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 3 — TSMOM v3 CORRELATION")
    print(f"{'='*70}")

    tsmom_daily = compute_tsmom_daily(data)
    tsmom_corrs: dict[str, float] = {}

    for bt, m in zip(all_bt, all_metrics):
        if bt["daily_pnl"].empty:
            tsmom_corrs[m["label"]] = float("nan")
            continue
        corr = pearson_corr(bt["daily_pnl"], tsmom_daily)
        tsmom_corrs[m["label"]] = corr
        print(f"  {m['label']:<12}: corr(ORB, TSMOM) = {corr:+.4f}  "
              f"n_common_days = "
              f"{len(bt['daily_pnl'].index.intersection(tsmom_daily.index))}")

    print(f"\n  Note: expected near-zero — ORB is intraday (4h), "
          f"TSMOM is weekly (28d cumulative). Any correlation > 0.40 would "
          f"indicate both strategies are just capturing BTC bull-market beta.")

    # ── 4. Results table ───────────────────────────────────────────────────────
    print_metrics_table(all_metrics, tsmom_corrs)

    # ── 5. Verdict ─────────────────────────────────────────────────────────────
    verdict = print_verdict(all_metrics, tsmom_corrs)

    # ── 6. Plot ────────────────────────────────────────────────────────────────
    plot_results(all_metrics, tsmom_corrs)

    elapsed = time.time() - t0
    print(f"\nTotal runtime: {elapsed/60:.1f} min")
    print(f"Output: {OUT_DIR / 'feasibility_results.png'}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
