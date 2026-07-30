"""Step 2 (H2 / L52) — validate the session map on REAL futures bars.

We trust no field name. Yahoo hourly bars for GC=F / SI=F / CL=F / ZS=F over the
maximum available window (~730d), converted to explicit UTC, then to US Eastern.

Checks (pre-registered):
  K-calendar: the 1h settlement halt must appear where the theory puts it
              (17:00-18:00 ET = 22-23 UTC winter / 21-22 UTC summer for GC/SI/CL;
               long halt for ZS).
  K1: >10% of days without a complete window on the futures -> REJECTED.
  K2: corr(window_ret_fut, window_ret_cfd) < 0.80 -> proxy invalid -> REJECTED.
  K3: opposite sign of drift vs CFD on the same period -> REJECTED.
Sample is ~730d: sufficient for MAPPING, explicitly insufficient for a Sharpe.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from common import OUT, SLEEVES, hac_t, load_h1, us_dst, window_returns

CACHE = OUT.parent / "code" / "_futcache"
CACHE.mkdir(exist_ok=True)
REOPEN_ET = {"GOLD": 18, "SILVER": 18, "WTI": 18, "SOYBEAN": 20}
WINDOW_HOURS = {"GOLD": 8, "SILVER": 8, "WTI": 8, "SOYBEAN": 6}


def fetch_1h(sym: str) -> pd.DataFrame:
    f = CACHE / f'{sym.replace("=", "_")}_1h.parquet'
    if f.exists():
        return pd.read_parquet(f)
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/"
           f'{urllib.parse.quote(sym)}?range=730d&interval=1h')
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=45))
            break
        except Exception as e:                                   # noqa: BLE001
            print(f"  retry {sym} ({e})")
            time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError(f"fetch failed {sym}")
    r = d["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"ts_utc": pd.to_datetime(r["timestamp"], unit="s", utc=True),
                       "open": q["open"], "high": q["high"], "low": q["low"],
                       "close": q["close"], "volume": q["volume"]}).dropna(subset=["close"])
    df["meta_tz"] = r["meta"].get("exchangeTimezoneName")
    df.to_parquet(f)
    return df


rows, calrows, futdaily = [], [], []
for name, sp in SLEEVES.items():
    fut = fetch_1h(sp["fut"])
    ts = pd.DatetimeIndex(fut["ts_utc"]).tz_convert("UTC").tz_localize(None)
    dst = us_dst(ts)
    et = ts - pd.to_timedelta(np.where(dst, 4, 5), unit="h")
    fut = fut.assign(utc=ts, et=et, dst=dst, et_h=pd.DatetimeIndex(et).hour,
                     utc_h=ts.hour).sort_values("utc")
    print(f'\n=== {name} {sp["fut"]}  meta_tz={fut["meta_tz"].iloc[0]}  '
          f'{ts.min().date()} -> {ts.max().date()}  n={len(fut)}')

    # --- calendar check: bar count per UTC hour x DST
    nd = {reg: pd.DatetimeIndex(fut.loc[m, "utc"]).normalize().nunique()
          for reg, m in (("winter", ~fut["dst"]), ("summer", fut["dst"]))}
    for reg, m in (("winter", ~fut["dst"].to_numpy()), ("summer", fut["dst"].to_numpy())):
        sub = fut[m]
        c = sub.groupby("utc_h").size() / max(nd[reg], 1)
        for h in range(24):
            calrows.append(dict(sleeve=name, sym=sp["fut"], dst=reg, utc_hour=h,
                                bars_per_day=round(float(c.get(h, 0.0)), 3)))
        low = [h for h in range(24) if c.get(h, 0.0) < 0.15]
        print(f"  {reg}: quiet UTC hours (<0.15 bars/day) = {low}")

    # --- window return on futures, exchange-anchored (spec B), gap-excluded
    ro, hours = REOPEN_ET[name], WINDOW_HOURS[name]
    sess = pd.DatetimeIndex(np.unique(pd.DatetimeIndex(fut["et"]).normalize()))
    keys = pd.DatetimeIndex(fut["et"]).asi8
    c_vals = fut["close"].to_numpy()
    o_vals = fut["open"].to_numpy()
    H = np.int64(3_600_000_000_000)
    base = (sess + pd.Timedelta(hours=ro)).asi8

    # L52: Yahoo hourly bars are LEFT-labelled (verified: no bar stamped 17:00 ET,
    # first session bar stamped 18:00 ET). So the ENTRY price at the reopen is the
    # OPEN of the bar stamped `ro`, not its close (its close is one hour later and
    # would skip the reopen hour = the entire edge).
    def at(t, mode, tol_min, field):
        vals = o_vals if field == "open" else c_vals
        tol = np.int64(tol_min) * np.int64(60_000_000_000)
        if mode == "last":
            i = np.searchsorted(keys, t, "left") - 1
            ok = (i >= 0) & (t - keys[np.clip(i, 0, len(keys) - 1)] <= tol)
        else:
            i = np.searchsorted(keys, t, "left")
            ok = (i < len(keys)) & (keys[np.clip(i, 0, len(keys) - 1)] - t <= tol)
        v = vals[np.clip(i, 0, len(keys) - 1)].astype(float)
        v[~ok] = np.nan
        return v

    # ZS has a ~5.5h halt (14:20->20:00 ET), not a 1h one -> wider pre-halt tolerance.
    pre_tol = 480 if name == "SOYBEAN" else 120
    p_pre = at(base - H, "last", pre_tol, "close")        # price at the halt start
    p_open = at(base, "first", 90, "open")                # price AT the reopen
    p_h1 = at(base, "first", 90, "close")                 # price 1h after the reopen
    p_end = at(base + (hours - 1) * H, "first", 90, "close")   # price at window end
    ok = (np.isfinite(p_pre) & np.isfinite(p_open) & np.isfinite(p_end)
          & np.isfinite(p_h1))
    fw = pd.DataFrame(dict(gap=np.log(p_open / p_pre),
                           hour1_cap=np.log(p_h1 / p_open),
                           window_cap=np.log(p_end / p_open)), index=sess)[ok]
    fw = fw[fw.index.dayofweek != 5]           # no Saturday session; Sunday evening IS one
    for c in ["gap", "hour1_cap", "window_cap"]:
        lo, hi = fw[c].quantile([0.005, 0.995])
        fw[c] = fw[c].clip(lo, hi)

    cal_days = pd.date_range(sess.min(), sess.max())
    n_possible = int((cal_days.dayofweek != 5).sum() * 5 / 6)   # ~5 sessions/week
    completeness = len(fw) / max(n_possible, 1)

    # --- CFD comparison on the SAME period, same anchor
    h1 = load_h1(sp["cfd"])
    cfd_w = window_returns(h1, sp["start_utc_winter"], sp["hours"], anchor="exchange")
    common = fw.index.intersection(cfd_w.index)
    corr = float(np.corrcoef(fw.loc[common, "window_cap"], cfd_w.loc[common])[0, 1]) \
        if len(common) > 50 else float("nan")

    r = dict(sleeve=name, sym=sp["fut"], n_fut_sessions=len(fw),
             completeness=round(completeness, 3),
             fut_gap_bps=round(1e4 * fw["gap"].mean(), 2),
             fut_hour1_cap_bps=round(1e4 * fw["hour1_cap"].mean(), 2),
             fut_window_cap_bps=round(1e4 * fw["window_cap"].mean(), 2),
             fut_t_window_cap=round(hac_t(fw["window_cap"])[1], 2),
             n_common=len(common), corr_fut_cfd=round(corr, 3))
    if len(common) > 50:
        r["cfd_window_bps_samePeriod"] = round(1e4 * cfd_w.loc[common].mean(), 2)
        r["fut_window_bps_samePeriod"] = round(1e4 * fw.loc[common, "window_cap"].mean(), 2)
    rows.append(r)
    fw.insert(0, "sleeve", name)
    futdaily.append(fw)

res = pd.DataFrame(rows)
cal = pd.DataFrame(calrows)
pd.set_option("display.width", 260, "display.max_columns", 40)
print("\n\n=== H2 futures validation ===")
print(res.to_string(index=False))
res.to_csv(OUT / "step2_futures_validation.csv", index=False)
cal.to_csv(OUT / "step2_futures_calendar.csv", index=False)
pd.concat(futdaily).to_csv(OUT / "step2_futures_daily.csv")
