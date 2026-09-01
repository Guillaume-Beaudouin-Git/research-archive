"""
Construit, depuis le M1 canonique NQ, les structures de session nécessaires au
balayage ORB : fenetres OR (RTH/Globex x 15/30/60min), chemins de surveillance
5min post-OR jusqu'a la cloture RTH, ATR14 quotidien (T-1), VIX aligne, FOMC,
jours feries data-driven.

Ecrit un pickle unique consomme par tous les autres scripts (evite de relire
83 Mo de parquet a chaque run).
"""
import pandas as pd
import numpy as np
import pickle

RAW = "<HOME>/Desktop/Algo_claude/data/raw/NQ_1min_databento_2010-2026.parquet"
VIX = "<HOME>/Desktop/Algo_claude/data/panels/vix.csv"
FOMC = "<HOME>/Desktop/Algo_claude/data/personal_book/post_fomc_drift/data_cache/fomc_events.csv"
OUT = "<HOME>/Desktop/Algo_claude_orbvar/Multi_Asset/research/active/orb_variants_2026-08/code/sessions.pkl"

ET = "America/New_York"


def main():
    print("loading raw M1 ...")
    df = pd.read_parquet(RAW, columns=["open", "high", "low", "close", "is_rth"])
    df.index = df.index.tz_convert(ET)
    df["et_date"] = df.index.date
    df["et_time"] = df.index.time

    rth = df[df["is_rth"]].copy()
    rth_dates = sorted(set(rth["et_date"]))
    print(f"n RTH days = {len(rth_dates)}")

    # ---- daily RTH OHLC (for ATR14, regime blocks) ----
    daily = rth.groupby("et_date").agg(
        d_open=("open", "first"), d_high=("high", "max"),
        d_low=("low", "min"), d_close=("close", "last"),
    )
    daily.index = pd.to_datetime(daily.index)
    prev_close = daily["d_close"].shift(1)
    tr = pd.concat([
        daily["d_high"] - daily["d_low"],
        (daily["d_high"] - prev_close).abs(),
        (daily["d_low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    daily["atr14_t1"] = atr14.shift(1)  # decale T-1, jamais le jour courant

    # ---- 5min RTH bars per day, padded matrix ----
    rth_idx = rth.set_index(rth.index)
    bars5 = rth_idx.resample("5min", label="left", closed="left").agg(
        o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")
    )
    bars5 = bars5.dropna(how="all")
    bars5["et_date"] = bars5.index.tz_convert(ET).date if bars5.index.tz is not None else bars5.index.date
    bars5["et_time"] = bars5.index.tz_convert(ET).time if bars5.index.tz is not None else bars5.index.time

    max_bars = bars5.groupby("et_date").size().max()
    print(f"max 5min bars/day = {max_bars}")

    n = len(rth_dates)
    date_to_i = {d: i for i, d in enumerate(rth_dates)}
    H = np.full((n, max_bars), np.nan, dtype=np.float64)
    L = np.full((n, max_bars), np.nan, dtype=np.float64)
    C = np.full((n, max_bars), np.nan, dtype=np.float64)
    O = np.full((n, max_bars), np.nan, dtype=np.float64)
    T = np.empty((n, max_bars), dtype=object)  # et_time of each 5min bar

    for d, g in bars5.groupby("et_date"):
        i = date_to_i[d]
        m = len(g)
        H[i, :m] = g["h"].values
        L[i, :m] = g["l"].values
        C[i, :m] = g["c"].values
        O[i, :m] = g["o"].values
        T[i, :m] = g["et_time"].values

    # ---- OR windows: RTH open at 09:30, Globex reopen detected from data ----
    # RTH OR: 1min bars in [09:30, 09:30+dur)
    rth1 = rth.copy()
    rth1["mso"] = (rth1.index.hour * 60 + rth1.index.minute) - (9 * 60 + 30)

    or_rth = {}
    for dur in (15, 30, 60):
        sub = rth1[(rth1["mso"] >= 0) & (rth1["mso"] < dur)]
        g = sub.groupby("et_date").agg(or_hi=("high", "max"), or_lo=("low", "min"))
        or_rth[dur] = g

    # Globex reopen: bars with is_rth==False, et_time == 18:00:00 exactly mark the
    # first minute after the daily settlement pause (detected from data, not assumed).
    non_rth = df[~df["is_rth"]].copy()
    reopen_mask = (non_rth.index.hour == 18) & (non_rth.index.minute == 0)
    reopen_bars = non_rth[reopen_mask]
    reopen_dates = sorted(set(reopen_bars["et_date"]))  # calendar date of the 18:00 bar
    print(f"n globex reopen events detected = {len(reopen_dates)}")

    # map each RTH date -> most recent reopen date strictly before it
    reopen_dates_arr = np.array(reopen_dates)
    rth_dates_arr = np.array(rth_dates)
    # searchsorted: find index of last reopen_date < rth_date
    idx = np.searchsorted(reopen_dates_arr, rth_dates_arr, side="left") - 1
    globex_session_start_date = {}
    for j, rd in enumerate(rth_dates):
        k = idx[j]
        if k >= 0:
            globex_session_start_date[rd] = reopen_dates_arr[k]

    or_globex = {}
    non_rth_sorted = non_rth.sort_index()
    nr_ts = non_rth_sorted.index.values.astype("datetime64[ns]")  # naive view, monotonic
    nr_high = non_rth_sorted["high"].to_numpy()
    nr_low = non_rth_sorted["low"].to_numpy()
    for dur in (15, 30, 60):
        starts = []
        ends = []
        valid_rd = []
        for rd in rth_dates:
            gsd = globex_session_start_date.get(rd)
            if gsd is None:
                continue
            start_ts = pd.Timestamp(gsd).tz_localize(ET) + pd.Timedelta(hours=18)
            end_ts = start_ts + pd.Timedelta(minutes=dur)
            valid_rd.append(rd)
            starts.append(start_ts.tz_convert("UTC").tz_localize(None).to_datetime64())
            ends.append(end_ts.tz_convert("UTC").tz_localize(None).to_datetime64())
        starts = np.array(starts, dtype="datetime64[ns]")
        ends = np.array(ends, dtype="datetime64[ns]")
        lo_idx = np.searchsorted(nr_ts, starts, side="left")
        hi_idx = np.searchsorted(nr_ts, ends, side="left")
        or_hi_vals = np.full(len(valid_rd), np.nan)
        or_lo_vals = np.full(len(valid_rd), np.nan)
        for j in range(len(valid_rd)):
            a, b = lo_idx[j], hi_idx[j]
            if b > a:
                or_hi_vals[j] = nr_high[a:b].max()
                or_lo_vals[j] = nr_low[a:b].min()
        g = pd.DataFrame({"et_date": valid_rd, "or_hi": or_hi_vals, "or_lo": or_lo_vals}).set_index("et_date")
        g = g.reindex(rth_dates)
        or_globex[dur] = g

    # ---- post-OR path start bar index, per (open_type, dur): first 5min bar
    # whose et_time is >= (OR window end), within the RTH day matrix. For RTH
    # opens the OR window end is 09:30+dur (still within RTH so simple). For
    # Globex opens, OR is measured overnight but monitoring path is still the
    # RTH day's 5min bars from bar 0 (documented design choice, PREREGISTRATION §4).
    path_start_idx = {}
    for dur in (15, 30, 60):
        # bar k of the day starts at 09:30 + 5*k minutes; we want first k with
        # 9:30+5k >= 9:30+dur  =>  k >= dur/5
        path_start_idx[("RTH", dur)] = int(np.ceil(dur / 5))
        path_start_idx[("Globex", dur)] = 0  # whole RTH day is the monitoring path

    # ---- VIX daily, aligned ----
    vix = pd.read_csv(VIX, parse_dates=["Date"]).set_index("Date")["^VIX"]
    vix.index = vix.index.date

    # ---- FOMC dates ----
    fomc = pd.read_csv(FOMC, parse_dates=["date"])["date"].dt.date.tolist()

    # ---- data-driven holiday flags: gap in RTH date sequence skips a weekday ----
    rth_dates_sorted = rth_dates_arr
    is_day_before_holiday = np.zeros(n, dtype=bool)
    is_day_after_holiday = np.zeros(n, dtype=bool)
    for i in range(n - 1):
        d0 = pd.Timestamp(rth_dates_sorted[i])
        d1 = pd.Timestamp(rth_dates_sorted[i + 1])
        # business days strictly between d0 and d1
        bdays_between = pd.bdate_range(d0 + pd.Timedelta(days=1), d1 - pd.Timedelta(days=1))
        if len(bdays_between) > 0:
            is_day_before_holiday[i] = True
            is_day_after_holiday[i + 1] = True

    out = dict(
        rth_dates=rth_dates,
        daily=daily,
        H=H, L=L, C=C, O=O, T=T,
        or_rth=or_rth, or_globex=or_globex,
        path_start_idx=path_start_idx,
        vix=vix, fomc=fomc,
        is_day_before_holiday=is_day_before_holiday,
        is_day_after_holiday=is_day_after_holiday,
        max_bars=max_bars,
    )
    with open(OUT, "wb") as f:
        pickle.dump(out, f)
    print("saved", OUT)


if __name__ == "__main__":
    main()
