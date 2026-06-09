"""
Independent re-implementation of S1 (Momentum intraday US100) from the PDF.

Spec (PDF page 5):
  Logique : À 11:00 ET (ouverture + 90 min), signe du rdt depuis 09:30.
            Long si positif, short si négatif. Filtre |mouvement| > 0.3 × ATR.
  Stop     : 3 × ATR(14)  (daily ATR, Wilder)
  Sortie   : 16:00 ET (clôture) ou stop
  Flat overnight.
  Anti-look-ahead : signal close de bar i, entry open de bar i+1.

NQ databento 1-min RTH, 2010-06-06 → 2026-05-31, front-month continuous.

We DO NOT use the report's code. Implementation built from the narrative spec.

Outputs (results/):
  - s1_trades.parquet  : one row per trade attempted (date, dir, entry, exit, stop, pnl_R, hit_stop)
  - s1_daily.parquet   : one row per session day (R-multiple of the day's S1 trade or 0)
  - s1_summary.json    : key metrics overall and per regime
"""
import json
from datetime import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
DATA = ROOT / "Futures/research/active/ftmo_3strats_audit_2026-06/results"

ATR_LEN = 14
SIGNAL_HOUR = time(11, 0)  # 11:00 ET signal computed from 09:30 → 11:00
OPEN_HOUR = time(9, 30)
EXIT_HOUR = time(16, 0)
ATR_FILTER_MULT = 0.3
STOP_MULT = 3.0


def wilder_atr(daily: pd.DataFrame, n: int = 14) -> pd.Series:
    """Wilder ATR on daily OHLC (true range, Wilder EMA)."""
    h, l, c = daily["high"], daily["low"], daily["close"]
    tr1 = h - l
    tr2 = (h - c.shift(1)).abs()
    tr3 = (l - c.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # Wilder smoothing: ATR_t = (ATR_{t-1}*(n-1) + TR_t)/n; seed = first n TR mean
    atr = np.full(len(tr), np.nan)
    tr_v = tr.values
    if len(tr_v) < n:
        return pd.Series(atr, index=daily.index)
    atr[n - 1] = np.nanmean(tr_v[:n])
    for i in range(n, len(tr_v)):
        prev = atr[i - 1]
        cur = tr_v[i]
        if np.isnan(prev) or np.isnan(cur):
            atr[i] = prev
        else:
            atr[i] = (prev * (n - 1) + cur) / n
    return pd.Series(atr, index=daily.index)


def main() -> None:
    p_min = DATA / "nq_1m_rth_2010_2026.parquet"
    p_d = DATA / "nq_daily_rth_2010_2026.parquet"
    print(f"[load] {p_min}", flush=True)
    m = pd.read_parquet(p_min)
    d = pd.read_parquet(p_d)
    d.index = pd.to_datetime(d.index)
    print(f"[load] min rows={len(m):,}  daily rows={len(d):,}", flush=True)

    # ATR on daily — use Wilder
    d["atr14"] = wilder_atr(d, ATR_LEN)
    # ATR available at signal time is yesterday's ATR (no look-ahead).
    d["atr_for_signal"] = d["atr14"].shift(1)
    # Daily return for benchmark regression (RTH-only)
    d["ret_d"] = d["close"].pct_change()

    # Extract per-day prices we need:
    #   open(09:30)  = open of 09:30 bar
    #   signal_px    = open(11:00 bar) ≡ close of 10:59 bar (no look-ahead at signal computed at 10:59:59)
    #   entry_px     = open(11:00 bar)   (= signal_px, since entry is at the 11:00 open just after signal close)
    #   We then track high/low/close per intraday bar from 11:00 to 16:00 to detect stop / EOD exit.
    m = m.copy()
    m["date"] = m.index.normalize()
    m["t"] = m.index.time
    # Identify bars
    opens_0930 = m[m["t"] == OPEN_HOUR].groupby("date")["open"].first()
    opens_1100 = m[m["t"] == SIGNAL_HOUR].groupby("date")["open"].first()
    # For EOD exit price: take the close of the LAST bar of the session for that date
    last_bar = m.groupby("date").tail(1).set_index("date")["close"]
    last_bar.name = "eod_close"

    # Walk-the-bars: from 11:00 (inclusive) to 16:00 (inclusive), get list of bars per date
    intraday_post = m[(m["t"] >= SIGNAL_HOUR) & (m["t"] <= EXIT_HOUR)].copy()
    print(f"[intra] post-signal rows={len(intraday_post):,}", flush=True)

    # Build per-day session DataFrame
    days = sorted(set(opens_0930.index) & set(opens_1100.index))
    print(f"[days] usable session days={len(days):,}", flush=True)

    # Pre-group intraday_post by date for fast access
    intraday_grp = {date: g for date, g in intraday_post.groupby("date")}

    records = []
    for dt in days:
        try:
            o930 = opens_0930.loc[dt]
            o1100 = opens_1100.loc[dt]
        except KeyError:
            continue
        if np.isnan(o930) or np.isnan(o1100):
            continue
        # ATR at signal time = previous day's ATR
        try:
            atr = d.loc[dt, "atr_for_signal"]
        except KeyError:
            continue
        if np.isnan(atr) or atr <= 0:
            continue

        move = o1100 - o930  # price-point move 09:30 → 11:00
        move_abs = abs(move)
        # Filter
        if move_abs <= ATR_FILTER_MULT * atr:
            records.append(
                {
                    "date": dt,
                    "atr14": atr,
                    "o930": o930,
                    "o1100": o1100,
                    "move": move,
                    "direction": 0,
                    "entry": np.nan,
                    "exit": np.nan,
                    "hit_stop": False,
                    "pnl_pts": 0.0,
                    "pnl_R": 0.0,
                }
            )
            continue

        direction = 1 if move > 0 else -1
        entry = o1100
        if direction == 1:
            stop = entry - STOP_MULT * atr
        else:
            stop = entry + STOP_MULT * atr

        # Walk intraday post-bars
        gpost = intraday_grp.get(dt)
        if gpost is None or len(gpost) == 0:
            continue
        hit_stop = False
        exit_px = gpost["close"].iloc[-1]  # default: last close
        if direction == 1:
            # Stop hit if any low <= stop
            lows = gpost["low"].values
            mask = lows <= stop
            if mask.any():
                hit_stop = True
                exit_px = stop
        else:
            highs = gpost["high"].values
            mask = highs >= stop
            if mask.any():
                hit_stop = True
                exit_px = stop

        pnl_pts = (exit_px - entry) * direction
        pnl_R = pnl_pts / (STOP_MULT * atr)
        records.append(
            {
                "date": dt,
                "atr14": atr,
                "o930": o930,
                "o1100": o1100,
                "move": move,
                "direction": direction,
                "entry": entry,
                "exit": exit_px,
                "hit_stop": hit_stop,
                "pnl_pts": pnl_pts,
                "pnl_R": pnl_R,
            }
        )

    tr = pd.DataFrame(records).set_index("date").sort_index()
    p_tr = DATA / "s1_trades.parquet"
    tr.to_parquet(p_tr)
    print(f"[save] {p_tr}  rows={len(tr):,}", flush=True)

    # Daily series in R
    daily = tr[["pnl_R", "direction"]].copy()
    # Aggregate (one trade/day max, no aggregation needed)
    p_da = DATA / "s1_daily.parquet"
    daily.to_parquet(p_da)
    print(f"[save] {p_da}", flush=True)

    # Summary
    traded = tr[tr["direction"] != 0]
    n_trades = len(traded)
    n_long = int((traded["direction"] == 1).sum())
    n_short = int((traded["direction"] == -1).sum())
    mean_R = float(daily["pnl_R"].mean())
    std_R = float(daily["pnl_R"].std(ddof=0))
    sharpe = mean_R / std_R * np.sqrt(252) if std_R > 0 else float("nan")

    # Cumulative R-equity
    eq = daily["pnl_R"].cumsum()
    peak = eq.cummax()
    dd = eq - peak
    max_dd_R = float(dd.min())

    # Per direction
    pnl_long = float(traded.loc[traded["direction"] == 1, "pnl_R"].sum())
    pnl_short = float(traded.loc[traded["direction"] == -1, "pnl_R"].sum())
    mean_R_long = float(traded.loc[traded["direction"] == 1, "pnl_R"].mean()) if n_long else 0.0
    mean_R_short = float(traded.loc[traded["direction"] == -1, "pnl_R"].mean()) if n_short else 0.0

    win_long = float((traded.loc[traded["direction"] == 1, "pnl_R"] > 0).mean()) if n_long else 0.0
    win_short = float((traded.loc[traded["direction"] == -1, "pnl_R"] > 0).mean()) if n_short else 0.0

    # Per regime split (calendar sub-periods)
    regimes = {
        "pre_2015": ("2010-06-06", "2014-12-31"),
        "2015_2019": ("2015-01-01", "2019-12-31"),
        "2020_2022": ("2020-01-01", "2022-12-31"),
        "2023_2026": ("2023-01-01", "2026-05-31"),
    }
    regime_stats = {}
    for label, (a, b) in regimes.items():
        sub = daily.loc[a:b]
        sub_tr = traded.loc[a:b]
        if len(sub) == 0:
            regime_stats[label] = None
            continue
        nl = int((sub_tr["direction"] == 1).sum())
        ns = int((sub_tr["direction"] == -1).sum())
        regime_stats[label] = {
            "n_sessions": int(len(sub)),
            "n_trades": int(len(sub_tr)),
            "n_long": nl,
            "n_short": ns,
            "mean_R_day": float(sub["pnl_R"].mean()),
            "std_R_day": float(sub["pnl_R"].std(ddof=0)),
            "sharpe_R": (
                float(sub["pnl_R"].mean() / sub["pnl_R"].std(ddof=0) * np.sqrt(252))
                if sub["pnl_R"].std(ddof=0) > 0
                else None
            ),
            "sum_R": float(sub["pnl_R"].sum()),
            "sum_R_long": float(sub_tr.loc[sub_tr["direction"] == 1, "pnl_R"].sum()) if nl else 0.0,
            "sum_R_short": float(sub_tr.loc[sub_tr["direction"] == -1, "pnl_R"].sum()) if ns else 0.0,
            "max_dd_R": float((sub["pnl_R"].cumsum() - sub["pnl_R"].cumsum().cummax()).min()),
        }

    summary = {
        "data_window": ["2010-06-06", "2026-05-31"],
        "n_sessions": int(len(daily)),
        "n_trades_total": n_trades,
        "n_long": n_long,
        "n_short": n_short,
        "trades_per_day": n_trades / len(daily) if len(daily) else None,
        "mean_R_day": mean_R,
        "std_R_day": std_R,
        "sharpe_R_annual": sharpe,
        "win_rate_overall": float((traded["pnl_R"] > 0).mean()) if n_trades else None,
        "win_rate_long": win_long,
        "win_rate_short": win_short,
        "mean_R_per_trade_long": mean_R_long,
        "mean_R_per_trade_short": mean_R_short,
        "sum_R_long": pnl_long,
        "sum_R_short": pnl_short,
        "max_dd_R_eq": max_dd_R,
        "regimes": regime_stats,
    }
    p_sum = DATA / "s1_summary.json"
    p_sum.write_text(json.dumps(summary, indent=2, default=str))
    print(f"[save] {p_sum}", flush=True)
    print("--- SUMMARY ---", flush=True)
    print(json.dumps(summary, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
