"""
Build decayed macro currency scores from the ForexFactory calendar
(Actual/Forecast/Previous, 2007-2025-04, source: Hugging Face
Ehsanrs2/Forex_Factory_Calendar, MIT license, downloaded anonymously).

Pre-registered choices (declared BEFORE any IC is computed):
  - xi candidates (3): sign(surprise), expanding z-score, winsorized z-score (clip +-3)
  - categories: Growth, Inflation, Employment, Confidence used by default;
    Rates EXCLUDED by default (author's own stated mechanism: rate changes are
    priced near-instantly, half-life -> 0, per the video transcript) but kept
    as a labeled secondary robustness variant.
  - category weights: equal (agnostic baseline). No ML fit (that piece of Dedale's
    method -- "fitted a la De Prado" -- is undisclosed and NOT reconstructed here).
  - lambda (decay): grid of half-lives {3,7,14,30,60,90} calendar days, SELECTED
    per walk-forward fold on the TRAINING portion only, evaluated OOS.
  - Delta t measured in calendar days (event timestamps are date-precise for
    ~70% of rows; ~30% have a defaulted 00:00 local time -- see caveats in report).
"""
import re
import numpy as np
import pandas as pd
from categorize import categorize

CACHE = "<SCRATCH>"
CCYS = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]


def parse_numeric(s):
    """FF Actual/Forecast/Previous carry unit suffixes (%, K, M, B, T) and commas."""
    if pd.isna(s):
        return np.nan
    s = str(s).strip()
    if s == "":
        return np.nan
    mult = 1.0
    if s.endswith("%"):
        s = s[:-1]
    m = re.match(r"^(-?[\d,.]+)([KMBT])?$", s)
    if not m:
        return np.nan
    num, suf = m.groups()
    num = num.replace(",", "")
    try:
        val = float(num)
    except ValueError:
        return np.nan
    mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}.get(suf, 1.0)
    return val * mult


def load_events():
    df = pd.read_csv(f"{CACHE}/forex_factory_calendar_2007_2025.csv", low_memory=False)
    df = df[df["Impact"].isin(["High Impact Expected", "Medium Impact Expected"])]
    df = df[df["Currency"].isin(CCYS)].copy()
    df["category"] = df["Event"].apply(categorize)
    df = df.dropna(subset=["category"])
    df["dt"] = pd.to_datetime(df["DateTime"], utc=True, errors="coerce")
    df = df.dropna(subset=["dt"])
    df["date"] = df["dt"].dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)
    df["actual_n"] = df["Actual"].apply(parse_numeric)
    df["forecast_n"] = df["Forecast"].apply(parse_numeric)
    df = df.dropna(subset=["actual_n", "forecast_n"])
    df["surprise"] = df["actual_n"] - df["forecast_n"]
    df = df.sort_values(["Currency", "Event", "date"]).reset_index(drop=True)

    # expanding (causal) z-score per (Currency, Event) series, min 8 prior obs
    def zscore_causal(g):
        s = g["surprise"]
        # std of PRIOR surprises only (shift(1) then expanding), ddof=1
        prior_std = s.shift(1).expanding(min_periods=8).std()
        return s / prior_std

    df["z"] = df.groupby(["Currency", "Event"], group_keys=False).apply(zscore_causal)
    df["z"] = df["z"].replace([np.inf, -np.inf], np.nan)  # zero-variance trailing window -> undefined
    df["z_clip"] = df["z"].clip(-3, 3)
    df["sign"] = np.sign(df["surprise"])
    df = df.dropna(subset=["z"])  # drop burn-in rows lacking enough history (or zero-variance window)
    return df


def decayed_currency_scores(events, ccy, xi_col, half_life_days, categories):
    """Recursive exponential-decay score for one currency, one xi transform, one
    half life, restricted to `categories`. Returns a daily Series indexed by date
    (forward-filled onto every calendar day between first and last event, decayed)."""
    sub = events[(events["Currency"] == ccy) & (events["category"].isin(categories))]
    sub = sub.dropna(subset=[xi_col])
    if sub.empty:
        return pd.Series(dtype=float)
    lam = np.log(2) / half_life_days
    # aggregate same-day, same-category contributions equally weighted, then
    # average across categories present that day (equal category weight)
    daily_cat = sub.groupby(["date", "category"])[xi_col].mean().unstack("category")
    daily_contrib = daily_cat.mean(axis=1, skipna=True)  # equal weight across categories present
    daily_contrib = daily_contrib.sort_index()
    full_idx = pd.date_range(daily_contrib.index.min(), daily_contrib.index.max(), freq="D")
    contrib = daily_contrib.reindex(full_idx, fill_value=0.0)
    # recursive decay: S[t] = S[t-1]*exp(-lam) + contrib[t]
    decay = np.exp(-lam)
    vals = contrib.values
    out = np.zeros(len(vals))
    running = 0.0
    for i in range(len(vals)):
        running = running * decay + vals[i]
        out[i] = running
    return pd.Series(out, index=full_idx)


if __name__ == "__main__":
    ev = load_events()
    print("Events after cleaning (surprise+z computable):", len(ev))
    print(ev.groupby("Currency").size())
    print(ev.groupby("category").size())
    ev.to_parquet(f"{CACHE}/ff_events_clean.parquet")
    print("saved ->", f"{CACHE}/ff_events_clean.parquet")
