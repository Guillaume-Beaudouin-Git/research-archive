"""Historical context that IS reproducible from the data actually in hand:
rate levels vs their own history, how unusual "near the ATH" is, and a
breadth breakdown.

Deliberately NOT here: a historical percentile for the index P/E. Building
one needs a vetted index-level earnings history (Nasdaq/STOXX/Bloomberg),
which is not obtainable from the free sources used in this dossier. The
report says so rather than substituting a number.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def us10y_history() -> pd.Series:
    p = CACHE / "tnx_history.csv"
    if p.exists():
        s = pd.read_csv(p, index_col=0, parse_dates=True).iloc[:, 0]
    else:
        h = yf.Ticker("^TNX").history(period="max")["Close"]
        h.index = pd.to_datetime(h.index).tz_localize(None)
        h.to_csv(p)
        s = h
    return s.dropna()


def pctile(s: pd.Series, v: float) -> float:
    return float((s <= v).mean() * 100)


def ath_proximity(name: str) -> dict:
    px = pd.read_csv(CACHE / f"index_history_{name}.csv", index_col=0,
                     parse_dates=True)["Close"].dropna()
    dd = px / px.cummax() - 1.0
    cur = float(dd.iloc[-1])
    out = {}
    for thr in [0.0, -0.01, -0.03, -0.05, -0.10, -0.20]:
        out[f"pct_of_sessions_within_{abs(thr)*100:.0f}pct_of_ATH"] = float((dd >= thr).mean() * 100)
    out["current_drawdown_pct"] = cur * 100
    out["current_dd_percentile"] = pctile(dd, cur)  # 100 = at the high
    # same, restricted to the last 10 years
    dd10 = dd.loc[dd.index[-1] - pd.DateOffset(years=10):]
    out["pct_of_sessions_within_3pct_of_ATH_last10y"] = float((dd10 >= -0.03).mean() * 100)
    return out


def breadth_detail(name: str) -> dict:
    b = pd.read_csv(CACHE / f"breadth_{name}.csv")
    ok = b[b.n_obs > 0].copy()
    ok["dd_from_52w_high_pct"] = (ok["last"] / ok["high52w"] - 1) * 100
    has_ma = ok[ok.ma200.notna()]
    return {
        "n_with_data": int(len(ok)),
        "n_total": int(len(b)),
        "n_with_200d_history": int(len(has_ma)),
        "above_ma200_n": int(has_ma.above_ma200.sum()),
        "above_ma200_pct": float(has_ma.above_ma200.mean() * 100),
        "within_5pct_52w_high_n": int(ok.within_5pct_of_52w_high.sum()),
        "within_5pct_52w_high_pct": float(ok.within_5pct_of_52w_high.mean() * 100),
        "within_10pct_52w_high_pct": float((ok.dd_from_52w_high_pct >= -10).mean() * 100),
        "median_dd_from_52w_high_pct": float(ok.dd_from_52w_high_pct.median()),
        "n_more_than_20pct_below_52w_high": int((ok.dd_from_52w_high_pct < -20).sum()),
    }


if __name__ == "__main__":
    out = {}
    tnx = us10y_history()  # ^TNX already quotes the yield in percent (verified vs Treasury)
    agg = json.loads((CACHE / "aggregates.json").read_text())
    ust = agg["rates"]["us10y_nominal_pct"]
    out["us10y"] = {
        "yfinance_TNX_last": float(tnx.iloc[-1]),
        "yfinance_TNX_last_date": str(tnx.index[-1].date()),
        "treasury_official": ust,
        "abs_gap_bp": abs(float(tnx.iloc[-1]) - ust) * 100,
        "percentile_full_hist": pctile(tnx, ust),
        "percentile_last_20y": pctile(tnx.loc[tnx.index[-1] - pd.DateOffset(years=20):], ust),
        "percentile_last_10y": pctile(tnx.loc[tnx.index[-1] - pd.DateOffset(years=10):], ust),
        "hist_start": str(tnx.index[0].date()),
    }
    ecb = pd.read_csv(CACHE / "ecb_ea_aaa_10y.csv")[["TIME_PERIOD", "OBS_VALUE"]].dropna()
    ecb = ecb.set_index("TIME_PERIOD").OBS_VALUE.sort_index()
    cur_ea = agg["rates"]["ea_aaa_10y_pct"]
    out["ea10y"] = {
        "level": cur_ea,
        "percentile_since_2005": pctile(ecb, cur_ea),
        "percentile_last_10y": pctile(ecb.loc[str(pd.Timestamp(ecb.index[-1]) - pd.DateOffset(years=10)):], cur_ea),
        "hist_start": str(ecb.index[0]),
    }

    for n in ["NDX", "DAX"]:
        out[n] = {"ath_proximity": ath_proximity(n), "breadth": breadth_detail(n)}

    (CACHE / "context.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
