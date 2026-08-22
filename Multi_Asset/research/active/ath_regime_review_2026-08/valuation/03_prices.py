"""Index price history + realised-vol / drawdown / ATH stats + constituent breadth.

Sources
  ^NDX    Nasdaq-100 PRICE index (yfinance)
  ^GDAXI  DAX 40 PERFORMANCE index, i.e. total return (yfinance)
          -> the two are NOT like-for-like on drawdown/ATH: the DAX
             reinvests net dividends, which mechanically lifts its
             index level and shortens its drawdowns. Flagged in the report.

Outputs: cache/index_history_{NDX,DAX}.csv, cache/index_stats.json,
         cache/breadth_{NDX,DAX}.csv
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

INDICES = {"NDX": "^NDX", "DAX": "^GDAXI"}


def index_history(name: str, symbol: str) -> pd.DataFrame:
    p = CACHE / f"index_history_{name}.csv"
    if p.exists():
        return pd.read_csv(p, index_col=0, parse_dates=True)
    df = yf.Ticker(symbol).history(period="max", auto_adjust=False)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.to_csv(p)
    return df


def index_stats(name: str, df: pd.DataFrame) -> dict:
    px = df["Close"].dropna()
    r = np.log(px).diff().dropna()

    ath = px.cummax()
    dd = px / ath - 1.0
    last_ath_date = px.index[px.eq(ath)][-1]

    rv20 = r.rolling(20).std() * np.sqrt(252)
    rv60 = r.rolling(60).std() * np.sqrt(252)

    def pct_rank(s: pd.Series) -> float:
        s = s.dropna()
        return float((s <= s.iloc[-1]).mean() * 100)

    return {
        "symbol": INDICES[name],
        "first_date": str(px.index[0].date()),
        "last_date": str(px.index[-1].date()),
        "n_obs": int(len(px)),
        "last_close": float(px.iloc[-1]),
        "all_time_high": float(ath.iloc[-1]),
        "ath_date": str(last_ath_date.date()),
        "pct_below_ath": float(dd.iloc[-1] * 100),
        "days_since_ath_calendar": int((px.index[-1] - last_ath_date).days),
        "sessions_since_ath": int(len(px.loc[last_ath_date:]) - 1),
        "rv20_ann_pct": float(rv20.iloc[-1] * 100),
        "rv60_ann_pct": float(rv60.iloc[-1] * 100),
        "rv20_pctile_full_hist": pct_rank(rv20),
        "rv60_pctile_full_hist": pct_rank(rv60),
        "rv20_pctile_10y": pct_rank(rv20.loc[rv20.index[-1] - pd.DateOffset(years=10):]),
        "rv60_pctile_10y": pct_rank(rv60.loc[rv60.index[-1] - pd.DateOffset(years=10):]),
        "rv20_median_full_hist_pct": float(rv20.median() * 100),
        "rv60_median_full_hist_pct": float(rv60.median() * 100),
        "ret_ytd_pct": float(px.iloc[-1] / px.loc[:f"{px.index[-1].year}-01-01"].iloc[-1] * 100 - 100),
        "ret_1y_pct": float(px.iloc[-1] / px.asof(px.index[-1] - pd.DateOffset(years=1)) * 100 - 100),
        "ret_3y_ann_pct": float((px.iloc[-1] / px.asof(px.index[-1] - pd.DateOffset(years=3))) ** (1 / 3) * 100 - 100),
        "max_dd_full_hist_pct": float(dd.min() * 100),
    }


def breadth(name: str, tickers: list[str]) -> pd.DataFrame:
    p = CACHE / f"breadth_{name}.csv"
    if p.exists():
        return pd.read_csv(p)
    px = yf.download(tickers, period="2y", interval="1d", auto_adjust=True,
                     progress=False, group_by="column")["Close"]
    rows = []
    for t in tickers:
        if t not in px.columns:
            rows.append({"ticker": t, "last": np.nan, "ma200": np.nan,
                         "high52w": np.nan, "n_obs": 0})
            continue
        s = px[t].dropna()
        if len(s) < 30:
            rows.append({"ticker": t, "last": np.nan, "ma200": np.nan,
                         "high52w": np.nan, "n_obs": len(s)})
            continue
        ma200 = s.rolling(200).mean().iloc[-1] if len(s) >= 200 else np.nan
        h52 = s.loc[s.index[-1] - pd.DateOffset(years=1):].max()
        rows.append({"ticker": t, "last": float(s.iloc[-1]),
                     "ma200": float(ma200) if pd.notna(ma200) else np.nan,
                     "high52w": float(h52), "n_obs": int(len(s))})
    df = pd.DataFrame(rows)
    df["above_ma200"] = df["last"] > df["ma200"]
    df["within_5pct_of_52w_high"] = df["last"] >= 0.95 * df["high52w"]
    df.to_csv(p, index=False)
    return df


if __name__ == "__main__":
    stats = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    for name, sym in INDICES.items():
        h = index_history(name, sym)
        stats[name] = index_stats(name, h)
        print(f"{name}: {stats[name]['first_date']} -> {stats[name]['last_date']}, "
              f"close {stats[name]['last_close']:.1f}, "
              f"{stats[name]['pct_below_ath']:.2f}% from ATH "
              f"({stats[name]['sessions_since_ath']} sessions), "
              f"rv20 {stats[name]['rv20_ann_pct']:.1f}% "
              f"(p{stats[name]['rv20_pctile_full_hist']:.0f})")

    ndx = pd.read_csv(CACHE / "constituents_ndx.csv")
    dax = pd.read_csv(CACHE / "constituents_dax.csv")
    for name, tk in [("NDX", list(ndx.ticker)), ("DAX", list(dax.ticker))]:
        b = breadth(name, tk)
        ok = b.n_obs > 0
        print(f"{name} breadth: {b.above_ma200.sum()}/{ok.sum()} above MA200 ; "
              f"{b.within_5pct_of_52w_high.sum()}/{ok.sum()} within 5% of 52w high")

    (CACHE / "index_stats.json").write_text(json.dumps(stats, indent=1))
