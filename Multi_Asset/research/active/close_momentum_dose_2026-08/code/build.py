"""Step 1: clock falsification (L56) + daily anchor table build.

Reads data/deep_history_utc/*_M1.csv from the MAIN repo dir, read-only.
Writes per-instrument daily anchor parquet to scratchpad (no repo blobs).
"""
import sys
import numpy as np
import pandas as pd

RAW = "<HOME>/Desktop/Algo_claude/data/deep_history_utc"
OUT = "<SCRATCH>"

SPEC = {
    "US500":  dict(tz="America/New_York", open_h=9,  open_m=30, sig_h=15, sig_m=30, close_h=16, close_m=0),
    "US100":  dict(tz="America/New_York", open_h=9,  open_m=30, sig_h=15, sig_m=30, close_h=16, close_m=0),
    "US30":   dict(tz="America/New_York", open_h=9,  open_m=30, sig_h=15, sig_m=30, close_h=16, close_m=0),
    "GER40":  dict(tz="Europe/Berlin",    open_h=9,  open_m=0,  sig_h=17, sig_m=0,  close_h=17, close_m=30),
    "XAUUSD": dict(tz="America/New_York", open_h=9,  open_m=30, sig_h=15, sig_m=30, close_h=16, close_m=0),
}


def load(sym):
    df = pd.read_csv(
        f"{RAW}/{sym}_M1.csv",
        usecols=["timestamp_utc", "open", "high", "low", "close"],
        dtype={"open": "float64", "high": "float64", "low": "float64", "close": "float64"},
    )
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    df = df.drop(columns=["timestamp_utc"])
    df.index = ts
    return df.sort_index()


def clock_test(df, tz, sym):
    """L56: winter-vs-summer hourly |return| profile correlation, exchange clock vs UTC."""
    r = (df["close"] / df["close"].shift(1) - 1.0).abs() * 1e4
    out = {}
    for name, idx in (("EXCH", df.index.tz_convert(tz)), ("UTC", df.index)):
        mo = idx.month.values
        hr = idx.hour.values
        winter = np.isin(mo, [12, 1, 2])
        summer = np.isin(mo, [6, 7, 8])
        pw = pd.Series(r.values[winter]).groupby(hr[winter]).mean()
        ps = pd.Series(r.values[summer]).groupby(hr[summer]).mean()
        j = pd.concat([pw, ps], axis=1).dropna()
        # correlate the SHAPE (normalised profiles), 24 hourly cells
        a = (j.iloc[:, 0] / j.iloc[:, 0].mean()).values
        b = (j.iloc[:, 1] / j.iloc[:, 1].mean()).values
        out[name] = float(np.corrcoef(a, b)[0, 1])
    print(f"  CLOCK {sym}: corr(hiver,ete) exchange={out['EXCH']:.3f}  utc={out['UTC']:.3f}")
    return out


def anchors(df, spec, sym):
    loc = df.index.tz_convert(spec["tz"])
    day = loc.normalize()
    mins = loc.hour.values * 60 + loc.minute.values
    o_m = spec["open_h"] * 60 + spec["open_m"]
    s_m = spec["sig_h"] * 60 + spec["sig_m"]
    c_m = spec["close_h"] * 60 + spec["close_m"]

    d = pd.DataFrame({
        "day": day.values, "m": mins,
        "o": df["open"].values, "h": df["high"].values,
        "l": df["low"].values, "c": df["close"].values,
    })
    # exact-minute picks; bar stamped T covers [T, T+1)
    def pick(target, col):
        s = d.loc[d["m"] == target, ["day", col]].drop_duplicates("day").set_index("day")[col]
        return s

    px = pd.DataFrame({
        "p_open":  pick(o_m, "o"),              # price at session open
        "p_sig":   pick(s_m - 1, "c"),          # price at signal time (close of prior bar)
        "p_entry": pick(s_m, "c"),              # delay+1: close of the bar AFTER the signal
        "p_exit":  pick(c_m - 1, "c"),          # price at cash close
        "p_exit_early": pick(c_m - 2, "c"),     # robustness: one bar earlier
    })
    px = px.dropna()

    # L60: zero-range bar share inside the TRADE window, per year
    win = d[(d["m"] >= s_m) & (d["m"] < c_m)]
    zr = (win["h"] == win["l"]).groupby(pd.DatetimeIndex(win["day"]).year).mean()
    zr.name = "zero_range_share"

    px["R_day"] = (px["p_sig"] / px["p_open"] - 1.0) * 1e4
    px["r_win"] = (px["p_exit"] / px["p_entry"] - 1.0) * 1e4
    px["r_win_early"] = (px["p_exit_early"] / px["p_entry"] - 1.0) * 1e4
    px = px[np.isfinite(px["R_day"]) & np.isfinite(px["r_win"])]
    px = px[px["R_day"] != 0.0]
    print(f"  {sym}: N={len(px)}  {px.index.min().date()} -> {px.index.max().date()}")
    return px, zr


if __name__ == "__main__":
    clocks = {}
    for sym in sys.argv[1:]:
        print(f"[{sym}] loading...")
        df = load(sym)
        clocks[sym] = clock_test(df, SPEC[sym]["tz"], sym)
        px, zr = anchors(df, SPEC[sym], sym)
        px.to_parquet(f"{OUT}/{sym}_daily.parquet")
        zr.to_frame().to_parquet(f"{OUT}/{sym}_zerorange.parquet")
        del df
    pd.DataFrame(clocks).T.to_csv(f"{OUT}/clock_test_{'_'.join(sys.argv[1:])}.csv")
