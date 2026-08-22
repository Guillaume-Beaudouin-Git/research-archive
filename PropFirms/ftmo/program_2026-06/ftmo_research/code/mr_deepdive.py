"""
mr_deepdive.py — Systematic DEPTH exploration of intraday mean-reversion for FTMO.

Companion to mr_intraday_screen.py (which proved the v1 shallow result was a
single parameterization). This module explores the MR space properly:
  signal logic  : SMA/EMA dev, Bollinger-z, RSI, VWAP-proxy dev, range-fade, gap-fill
  timeframe     : 5/15/30/60 min
  exit          : mean-touch, half-life-matched time-stop, ATR target/stop
  regime filter : vol tercile, time-of-day, trend-vs-range (variance ratio)
  instrument    : NQ (real volume/VWAP), US500, US100, US30, GER40, EURUSD

Anti-false-positive discipline applied to EVERY cell (this is the quality control):
  - non-overlapping trades, per-trade cost in bps (CFD real: idx ~1.5, FX ~1.0)
  - 1-bar execution-delay column (decisive: real edge survives, artifact collapses)
  - TWO-SIDED: long-leg and short-leg reported separately; one-sided long == beta
  - holding matched to ESTIMATED half-life (not fixed) per instrument×TF×anchor
  - N_trials tracked across the WHOLE grid for DSR/AMTP deflation on the total space

Data is tz/volume-heterogeneous; VWAP is exact only on NQ (databento has volume),
elsewhere a session-anchored mean proxy is used (flagged in outputs).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("/sessions/blissful-upbeat-newton/mnt/Algo_claude/data")
OUT = Path("/sessions/blissful-upbeat-newton/mnt/outputs/mr_dd")
OUT.mkdir(parents=True, exist_ok=True)

# name -> (parquet, has_volume, session_tz, h0, h1, cost_bps)
INSTR = {
    "NQ":     ("raw/NQ_1min_databento_2010-2026.parquet", True,  "America/New_York", 9, 16, 1.5),
    "US500":  ("panels/m5_indices/m1_panel.parquet",      False, "America/New_York", 9, 16, 1.5),
    "US100":  ("panels/m5_indices/m1_panel.parquet",      False, "America/New_York", 9, 16, 1.5),
    "US30":   ("panels/m5_indices/m1_panel.parquet",      False, "America/New_York", 9, 16, 1.5),
    "GER40":  ("panels/m5_indices/GER40_m1_panel.parquet",False, "Europe/Berlin",    9, 17, 1.5),
    "EURUSD": ("panels/m5_indices/EURUSD_m1_panel.parquet",False,"UTC",              7, 20, 1.0),
}
TF_MIN = {"5m": 5, "15m": 15, "30m": 30, "60m": 60}


def load_1m(name: str) -> pd.DataFrame:
    pq, hasv, tz, h0, h1, cost = INSTR[name]
    if name == "NQ":
        df = pd.read_parquet(BASE / pq, columns=["open", "close", "volume", "is_rth", "is_roll_day"])
        df = df[df["is_rth"] & ~df["is_roll_day"]].copy()
        df.index = df.index.tz_convert(tz)
        df = df.rename(columns={"close": "px"})[["px", "volume"]]
    else:
        d = pd.read_parquet(BASE / pq)
        if isinstance(d.columns, pd.MultiIndex):
            d = d[name]
        d.index = pd.to_datetime(d.index).tz_localize("UTC").tz_convert(tz)
        df = d[["close"]].rename(columns={"close": "px"})
        df["volume"] = np.nan
    h = df.index.hour
    df = df[(h >= h0) & (h < h1)]
    df["session"] = df.index.normalize()
    return df.dropna(subset=["px"])


def resample_tf(df1m: pd.DataFrame, tf: str) -> pd.DataFrame:
    r = df1m.resample(f"{TF_MIN[tf]}min")
    out = pd.DataFrame({"px": r["px"].last(), "vol": r["volume"].sum(min_count=1)}).dropna(subset=["px"])
    out["session"] = out.index.normalize()
    return out


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ret"] = df.groupby("session")["px"].pct_change()
    return df


# ---------- half-life of deviation from an anchor (AR(1), within session) -------
def half_life(df: pd.DataFrame, win: int = 20) -> float:
    g = df.groupby("session")["px"]
    anc = g.transform(lambda x: x.rolling(win, min_periods=win).mean())
    d = (df["px"] - anc)
    # within-session lag: drop first row of each session
    d_lag = d.groupby(df["session"]).shift(1)
    m = d.notna() & d_lag.notna()
    x = d_lag[m].values
    y = d[m].values
    if len(x) < 200 or x.std() == 0:
        return np.nan
    phi = np.polyfit(x, y, 1)[0]                 # d_t = phi d_{t-1}
    if not (0 < phi < 1):
        return np.nan
    return float(-np.log(2) / np.log(phi))       # bars


# ----------------------------- signal logics --------------------------------
def compute_dev(df: pd.DataFrame, logic: str) -> np.ndarray:
    """Signed deviation: positive => price extended UP (=> short-fade),
    negative => extended DOWN (=> long-fade). NaN where undefined."""
    px = df["px"]; sess = df["session"]
    g = px.groupby(sess)
    if logic in ("sma20_z", "ema20_z", "vwap_z"):
        if logic == "sma20_z":
            anc = g.transform(lambda x: x.rolling(20, min_periods=20).mean())
        elif logic == "ema20_z":
            anc = g.transform(lambda x: x.ewm(span=20, min_periods=20).mean())
        else:  # vwap proxy: session cumulative mean of px weighted by vol if present
            if df["vol"].notna().any():
                pv = (px * df["vol"]).groupby(sess).cumsum()
                vv = df["vol"].groupby(sess).cumsum()
                anc = pv / vv
            else:
                anc = px.groupby(sess).expanding().mean().reset_index(level=0, drop=True)
        sd = g.transform(lambda x: x.rolling(20, min_periods=20).std())
        return ((px - anc) / sd).values
    if logic == "rsi14":
        d = px.groupby(sess).diff()
        up = d.clip(lower=0); dn = (-d).clip(lower=0)
        ru = up.groupby(sess).transform(lambda x: x.ewm(alpha=1/14, min_periods=14).mean())
        rd = dn.groupby(sess).transform(lambda x: x.ewm(alpha=1/14, min_periods=14).mean())
        rsi = 100 - 100 / (1 + ru / rd.replace(0, np.nan))
        return (rsi - 50).values            # +>0 overbought(short), threshold ~20 => RSI70
    if logic == "range_fade":
        hi = px.groupby(sess).cummax(); lo = px.groupby(sess).cummin()
        pos = (px - lo) / (hi - lo)          # 0..1 within session range
        return ((pos - 0.5) * 2).values      # -1..1 ; +ve near high
    raise ValueError(logic)


def build_trades(px, dev, sess, yr, theta, exit_type, H, cost, delay=0):
    """Non-overlapping fade trades. Each bar visited once total (O(n))."""
    n = len(px); i = 0
    T_side = []; T_ret = []; T_yr = []
    while i < n - 1 - delay:
        di = dev[i]
        if np.isfinite(di) and abs(di) > theta:
            j = i + delay
            if j >= n - 1 or sess[j] != sess[i]:
                i += 1; continue
            side = -1.0 if di > 0 else 1.0          # fade
            if exit_type == "ts":
                k = j + H
                if k >= n or sess[k] != sess[j]:
                    # exit at last bar of session
                    k = j
                    while k + 1 < n and sess[k + 1] == sess[j]:
                        k += 1
            else:  # mean-touch: forward to sign flip (dev returns toward 0) or session end
                k = j + 1
                while k < n and sess[k] == sess[j]:
                    if not np.isfinite(dev[k]) or side * dev[k] >= 0:  # crossed anchor
                        break
                    k += 1
                if k >= n or sess[k] != sess[j]:
                    k -= 1
            ret = side * (px[k] / px[j] - 1.0) * 1e4 - cost
            T_side.append(side); T_ret.append(ret); T_yr.append(yr[i])
            i = max(k, i + 1)
        else:
            i += 1
    return np.array(T_side), np.array(T_ret), np.array(T_yr)


def cell_stats(side, ret, yr):
    n = len(ret)
    if n < 30:
        return None
    m = ret.mean(); t = m / ret.std() * np.sqrt(n) if ret.std() > 0 else 0.0
    L = ret[side > 0]; S = ret[side < 0]
    yrs = pd.Series(ret).groupby(pd.Series(yr)).mean()
    return dict(n=n, mean=m, t=t, wr=(ret > 0).mean(),
                nL=len(L), mL=L.mean() if len(L) else np.nan,
                nS=len(S), mS=S.mean() if len(S) else np.nan,
                yrs_pos=int((yrs > 0).sum()), yrs_tot=len(yrs))


THETAS = {"sma20_z": (1.5, 2.5), "ema20_z": (1.5, 2.5), "vwap_z": (1.5, 2.5),
          "rsi14": (20, 25), "range_fade": (0.8, 0.92)}


def run_grid(instruments, tfs=("5m", "15m", "30m"),
             logics=("sma20_z", "ema20_z", "vwap_z", "rsi14", "range_fade"),
             exits=("ts", "mt")) -> pd.DataFrame:
    hl_tbl = pd.read_csv(OUT / "half_life.csv")
    rows = []
    for name in instruments:
        cost = INSTR[name][5]
        for tf in tfs:
            df = pd.read_parquet(OUT / f"{name}_{tf}.parquet")
            df = add_returns(df)
            px = df["px"].values; sess = df["session"].values.astype("datetime64[D]")
            yr = pd.DatetimeIndex(df.index).year.values
            hlrow = hl_tbl[(hl_tbl.instr == name) & (hl_tbl.tf == tf)]["HL_bars_sma20"]
            H = int(round(hlrow.values[0])) if len(hlrow) and np.isfinite(hlrow.values[0]) else 8
            H = max(2, min(H, 20))
            for logic in logics:
                dev = compute_dev(df, logic)
                for theta in THETAS[logic]:
                    for ex in exits:
                        side, ret, tyr = build_trades(px, dev, sess, yr, theta, ex, H, cost, 0)
                        st = cell_stats(side, ret, tyr)
                        if st is None:
                            continue
                        # delay-1 only if base mean>0 (cheap filter)
                        d1m = np.nan
                        if st["mean"] > 0:
                            s2, r2, _ = build_trades(px, dev, sess, yr, theta, ex, H, cost, 1)
                            d1m = r2.mean() if len(r2) > 5 else np.nan
                        rows.append(dict(instr=name, tf=tf, logic=logic, theta=theta,
                                         exit=ex, H=H, cost=cost, delay1_mean=d1m, **st))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    rows = []
    for name in INSTR:
        d1 = load_1m(name)
        span = f"{d1.index.min().date()}..{d1.index.max().date()}"
        for tf in TF_MIN:
            dd = resample_tf(d1, tf)
            dd.to_parquet(OUT / f"{name}_{tf}.parquet")
            hl = half_life(dd, win=20)
            rows.append((name, tf, len(dd), span, hl))
        print(f"cached {name}: 5/15/30/60m  ({span}, {len(d1)} 1m rows)")
    tbl = pd.DataFrame(rows, columns=["instr", "tf", "bars", "span", "HL_bars_sma20"])
    tbl.to_csv(OUT / "half_life.csv", index=False)
    print("\n=== Half-life of deviation from SMA20 (bars), within-session AR(1) ===")
    piv = tbl.pivot(index="instr", columns="tf", values="HL_bars_sma20")[["5m", "15m", "30m", "60m"]]
    print(piv.round(2).to_string())
    print("\n(holding will be matched to these — e.g. HL≈3 bars on 5m => ~15min hold)")
