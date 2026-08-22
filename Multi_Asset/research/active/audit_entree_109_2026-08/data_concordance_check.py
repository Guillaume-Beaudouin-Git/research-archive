"""
Chantier B.0 -- honesty gate (L52/L56/L60) BEFORE using M1 as an intraday arbiter.
Two different pipelines feed this repo's data: the daily OHLC store consumed by
ftmo_lab (panels/m5_indices/*_M1.csv + yfinance, see build_ohlc_store.py) and the
canonical M1 truth store `data/deep_history_utc/` (repaired 2026-06-10, true UTC).
They are NOT guaranteed to agree bar-for-bar (different raw feeds/vintages).
Before trusting M1 to arbitrate which entry level was touched first, measure how
often the two sources even agree on the SAME day's open/high/low, and how many M1
bars are degenerate (high==low, L60 print-settlement check).
"""
import glob, os
import numpy as np, pandas as pd

DAILY_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/archived/oxfordstrat_109_audit/ohlc"
M1_DIR = "<HOME>/Desktop/Algo_claude/data/deep_history_utc"

# Only instruments whose daily bar was built by UTC-midnight-cut M1 resample
# (build_ohlc_store.py M1_RESAMPLE dict) AND that have a deep_history_utc M1 file.
CANDIDATES = ["EURUSD","GBPUSD","USDJPY","USDCHF","USDCAD","AUDUSD","NZDUSD","EURGBP","AUDJPY","XAUUSD"]

rows = []
for t in CANDIDATES:
    m1_path = os.path.join(M1_DIR, f"{t}_M1.csv")
    if not os.path.exists(m1_path):
        rows.append(dict(instr=t, status="NO_M1_FILE")); continue
    daily = pd.read_parquet(os.path.join(DAILY_DIR, f"{t}.parquet"))
    m1 = pd.read_csv(m1_path, usecols=["timestamp_utc","open","high","low","close"])
    m1["dt"] = pd.to_datetime(m1["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    m1 = m1.dropna(subset=["dt"])
    m1["date"] = m1["dt"].dt.normalize()
    # L60: fraction of degenerate M1 bars (print-settlement / flat)
    flat_frac = float((m1["high"] == m1["low"]).mean())
    g = m1.groupby("date").agg(m1_open=("open","first"), m1_high=("high","max"),
                                m1_low=("low","min"), m1_close=("close","last"), n_bars=("open","size"))
    j = daily.join(g, how="inner")
    if len(j) == 0:
        rows.append(dict(instr=t, status="NO_OVERLAP", flat_bar_frac_m1=flat_frac)); continue
    # tolerance: relative to that day's own daily range (open-to-open comparisons are
    # noisy at exact micro-pip level across different feeds/spreads; use range-relative)
    rng = (j["high"] - j["low"]).replace(0, np.nan)
    open_err = (j["open"] - j["m1_open"]).abs() / rng
    high_err = (j["high"] - j["m1_high"]).abs() / rng
    low_err  = (j["low"]  - j["m1_low"]).abs()  / rng
    good_open = (open_err < 0.05)
    good_hl   = (high_err < 0.05) & (low_err < 0.05)
    good_day  = good_open & good_hl
    rows.append(dict(instr=t, status="OK", n_overlap_days=len(j),
                      frac_good_open=float(good_open.mean()), frac_good_hl=float(good_hl.mean()),
                      frac_good_day=float(good_day.mean()),
                      median_open_err_pct_range=float(open_err.median()*100),
                      flat_bar_frac_m1=flat_frac,
                      n_m1_bars_per_day_median=float(j["n_bars"].median())))

out = pd.DataFrame(rows)
out.to_csv("m1_daily_concordance.csv", index=False)
print(out.to_string())
