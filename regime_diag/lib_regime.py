"""Regime panel aligned to book trading dates (PRE_REGISTRATION §2).
All macro levels lagged 1 trading day (value as of prior close) => strictly T-1/causal.
Also exposes contemporaneous (T) versions for the 'trap' check, and the secondary axes.
Read-only on main-dir data files (absolute paths)."""
import numpy as np, pandas as pd
M = "<HOME>/Desktop/Algo_claude"

def _asof_lag(series, book_dates, lag=1):
    """Reindex a (possibly holiday-gapped) macro series to book dates by last-available
    value (value at T close), then shift by `lag` trading days => value known at T-lag."""
    s = series.reindex(series.index.union(book_dates)).sort_index().ffill()
    s = s.reindex(book_dates)
    return s.shift(lag)

def _terciles(s, labels):
    out = pd.Series(index=s.index, dtype=object)
    ok = s.notna()
    out[ok] = pd.qcut(s[ok], 3, labels=labels)
    return out

def _quintiles(s):
    out = pd.Series(index=s.index, dtype=object)
    ok = s.notna()
    out[ok] = pd.qcut(s[ok], 5, labels=[f"q{i}" for i in range(1, 6)])
    return out

def event_window(book_dates, event_dates, w=1):
    """Boolean over book_dates: within w trading days of any event date (nearest-snap)."""
    bd = pd.DatetimeIndex(book_dates); flag = np.zeros(len(bd), bool)
    bn = bd.normalize()
    for d in pd.to_datetime(pd.Series(event_dates).dropna()).dt.normalize().unique():
        j = int(np.argmin(np.abs((bn - d).values.astype('timedelta64[D]').astype(int))))
        for k in range(j - w, j + w + 1):
            if 0 <= k < len(bd): flag[k] = True
    return pd.Series(flag, index=bd)

def build_panel(book_dates):
    bd = pd.DatetimeIndex(book_dates)
    P = pd.DataFrame(index=bd)
    # --- A1 VOL: VIX
    vix = pd.read_csv(f"{M}/data/panels/vix.csv", parse_dates=["Date"]).set_index("Date")["^VIX"]
    vvix = pd.read_csv(f"{M}/data/panels/vix.csv", parse_dates=["Date"]).set_index("Date")["^VVIX"]
    vlag = _asof_lag(vix, bd); P["vix_lag"] = vlag
    P["A1_vol"] = _terciles(vlag, ["lo", "mid", "hi"])
    P["A1_vol_q"] = _quintiles(vlag)
    P["vix_ct"] = _asof_lag(vix, bd, lag=0)
    P["A1_vol_ct"] = _terciles(P["vix_ct"], ["lo", "mid", "hi"])
    P["A1_vvix"] = _terciles(_asof_lag(vvix, bd), ["lo", "mid", "hi"])      # secondary
    # --- A2 DOLLAR: DXY (DTWEXBGS) 3m momentum
    fred = pd.read_parquet(f"{M}/data/raw/fred_BAMLH0A0_DGS3MO_DTWEXBGS_d06fce80fc.parquet")
    dxy = fred["dtwexbgs"].dropna()
    dxy_mom = dxy / dxy.shift(63) - 1.0
    P["dxy_mom_lag"] = _asof_lag(dxy_mom, bd)
    P["A2_usd"] = _terciles(P["dxy_mom_lag"], ["usd_dn", "flat", "usd_up"])
    P["A2_usd_ct"] = _terciles(_asof_lag(dxy_mom, bd, lag=0), ["usd_dn", "flat", "usd_up"])
    # --- A3 CREDIT: HY OAS level + change
    oas = fred["bamlh0a0hym2"].dropna()
    P["oas_lag"] = _asof_lag(oas, bd)
    P["A3_credit"] = _terciles(P["oas_lag"], ["tight", "mid", "wide"])
    P["A3_credit_ct"] = _terciles(_asof_lag(oas, bd, lag=0), ["tight", "mid", "wide"])
    P["A3_oas_chg"] = _terciles(_asof_lag(oas - oas.shift(21), bd), ["narrowing", "flat", "widening"])  # secondary
    # --- A4 ANNOUNCE: FOMC ±1 (full sample, pre-scheduled => causal by construction)
    fomc = pd.read_csv(f"{M}/data/personal_book/post_fomc_drift/data_cache/fomc_events.csv")["date"]
    P["A4_fomc"] = np.where(event_window(bd, fomc, 1).values, "fomc", "no")
    # secondary 2020+ announce
    ec = pd.read_csv(f"{M}/data/panels/economic_calendar.csv")
    nfp = ec.loc[ec.event == "NFP", "date"]; cpi = ec.loc[ec.event == "CPI", "date"]
    P["A4_nfp"] = np.where(event_window(bd, nfp, 1).values, "nfp", "no")
    P["A4_cpi"] = np.where(event_window(bd, cpi, 1).values, "cpi", "no")
    nv = pd.read_csv(f"{M}/Forex/data/news_events_2020_2025.csv", comment="#")
    boj = nv.loc[nv["event_type"].astype(str).str.contains("BOJ", case=False, na=False), "date"]
    P["A4_boj"] = np.where(event_window(bd, boj, 1).values, "boj", "no")
    P["post2020"] = bd >= pd.Timestamp("2020-01-01")
    # --- Q3 day of week
    P["dow"] = bd.dayofweek
    return P

# axis registry: name -> (column, kind, risk_off_bucket)
PRIMARY_AXES = {
    "A1_vol":    ("A1_vol", "cat", "hi"),
    "A2_usd":    ("A2_usd", "cat", None),       # both tails plausible; data-driven worst
    "A3_credit": ("A3_credit", "cat", "wide"),
    "A4_fomc":   ("A4_fomc", "bin", "fomc"),
}
CONTEMP_AXES = {"A1_vol": "A1_vol_ct", "A2_usd": "A2_usd_ct", "A3_credit": "A3_credit_ct"}

if __name__ == "__main__":
    import pickle, sys
    from pathlib import Path
    HERE = Path(__file__).resolve().parent
    BD = pd.read_parquet(HERE / "_cache/book_daily.parquet")
    P = build_panel(BD.index)
    P.to_parquet(HERE / "_cache/regime_panel.parquet")
    print("panel", P.shape, "->", HERE / "_cache/regime_panel.parquet")
    for c in ["A1_vol", "A2_usd", "A3_credit", "A4_fomc", "A4_nfp", "A4_boj"]:
        vc = P[c].value_counts(dropna=False).to_dict()
        print(f"  {c}: {vc}")
    print("  coverage NaN:", {c: int(P[c].isna().sum()) for c in ["A1_vol","A2_usd","A3_credit"]})
    print("  post2020 days:", int(P.post2020.sum()), "/", len(P))
    print("  vix_lag range", f"{P.vix_lag.min():.1f}..{P.vix_lag.max():.1f}",
          "oas_lag", f"{P.oas_lag.min():.2f}..{P.oas_lag.max():.2f}",
          "dxy_mom_lag", f"{P.dxy_mom_lag.min():.3f}..{P.dxy_mom_lag.max():.3f}")
