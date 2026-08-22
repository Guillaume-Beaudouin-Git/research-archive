"""
swing_deepdive.py — Swing / multi-day deep-dive for FTMO.

Tests whether a LONGER holding horizon (days–weeks) escapes the intraday beta
trap. Same discipline: non-overlap, per-trade bps cost + MULTI-DAY FINANCING
(swap each night held), 1-day execution-delay column, TWO-SIDED test (long vs
short legs), DSR on total space.

Daily bars: indices 2000-2026 (ftmo OHLC), FX/gold 2018-2025 (cached 1H->daily).
Financing per night: index CFD ~1.5 bps (2x markup, rate-independent), FX ~0.5,
gold ~1.0 (carry handled exactly in the separate carry deep-dive).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

D = Path("/sessions/blissful-upbeat-newton/mnt/outputs/swing")
COST = {s: 1.5 for s in ["US100", "US500", "US30", "GER40", "UK100", "JP225", "AUS200"]}
COST.update({s: 1.0 for s in ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY",
                              "USDCAD", "USDCHF", "EURGBP", "EURJPY", "AUDJPY"]})
COST["XAUUSD"] = 2.0
FIN = {**{s: 1.5 for s in COST}, **{s: 0.5 for s in COST if "USD" in s or len(s) == 6}}
for s in ["US100", "US500", "US30", "GER40", "UK100", "JP225", "AUS200"]:
    FIN[s] = 1.5
FIN["XAUUSD"] = 1.0

# Real FTMO swap guardrail (the Dédale swap-sign rule). Optional: used by trades_guarded.
try:
    import ftmo_swaps as _fs
except Exception:
    _fs = None


def load(name):
    df = pd.read_parquet(D / f"{name}_D.parquet")
    df["ret"] = df["close"].pct_change()
    return df


def rsi(close, n):
    d = close.diff(); up = d.clip(lower=0); dn = (-d).clip(lower=0)
    ru = up.ewm(alpha=1/n, min_periods=n).mean(); rd = dn.ewm(alpha=1/n, min_periods=n).mean()
    return 100 - 100 / (1 + ru / rd.replace(0, np.nan))


def signal(df, family, logic, p):
    c = df["close"]
    if family == "swing_mom":
        if logic == "donchian":
            hi = c.rolling(p).max().shift(1); lo = c.rolling(p).min().shift(1)
            return np.where(c > hi, 1, np.where(c < lo, -1, 0))
        if logic == "tsmom":
            r = c / c.shift(p) - 1
            sd = df["ret"].rolling(max(p, 20)).std()
            z = r / (sd * np.sqrt(p))
            return np.where(z > 0.5, 1, np.where(z < -0.5, -1, 0))
        if logic == "ma_cross":
            fast = c.rolling(p).mean(); slow = c.rolling(p * 4).mean()
            up = (fast > slow) & (fast.shift(1) <= slow.shift(1))
            dn = (fast < slow) & (fast.shift(1) >= slow.shift(1))
            return np.where(up, 1, np.where(dn, -1, 0))
    if family == "swing_mr":
        if logic == "rsi2":
            r = rsi(c, 2)
            return np.where(r < p, 1, np.where(r > 100 - p, -1, 0))   # oversold->long
        if logic == "bollinger":
            m = c.rolling(20).mean(); sd = c.rolling(20).std(); z = (c - m) / sd
            return np.where(z < -p, 1, np.where(z > p, -1, 0))
        if logic == "nday_rev":
            r = c / c.shift(p) - 1; sd = df["ret"].rolling(20).std()
            z = r / (sd * np.sqrt(p))
            return np.where(z < -1.0, 1, np.where(z > 1.0, -1, 0))      # fade move
    raise ValueError((family, logic))


def trades(df, sig, exit_mode, H, cost, fin, delay=0):
    c = df["close"].values; idx = df.index
    # MR mean anchor for mean-touch
    anc = df["close"].rolling(20).mean().values
    n = len(c); i = 0; sd = []; rt = []; ty = []
    while i < n - 1 - delay:
        s = sig[i]
        if s != 0 and np.isfinite(c[i]):
            j = i + delay
            if j >= n - 1:
                break
            if exit_mode == "time":
                k = min(j + H, n - 1)
            else:  # mean-touch (for MR): exit when price crosses its 20d mean
                k = j + 1
                while k < n - 1 and (not np.isfinite(anc[k]) or s * (c[k] - anc[k]) < 0):
                    k += 1
                k = min(k, n - 1)
            nights = max(1, (idx[k] - idx[j]).days)
            ret = s * (c[k] / c[j] - 1) * 1e4 - cost - nights * fin
            sd.append(s); rt.append(ret); ty.append(idx[i].year); i = max(k, i + 1)
        else:
            i += 1
    return np.array(sd, float), np.array(rt), np.array(ty)


def trades_guarded(df, sig, instrument, exit_mode, H, cost, swap_sign=True, delay=0):
    """trades() with the REAL asymmetric FTMO swap per side and (optionally) the
    swap-sign filter: only take trades whose holding direction pays positive swap
    (never pay financing overnight). fin is SIGNED bps/night (<0 = you pay); it is
    ADDED to the per-trade return. Falls back to -0.5 bps/night if ftmo_swaps missing."""
    px = df["close"].values
    idx = df.index
    anc = df["close"].rolling(20).mean().values
    n = len(px); i = 0; sd = []; rt = []; ty = []
    while i < n - 1 - delay:
        s = sig[i]
        if s != 0 and np.isfinite(px[i]):
            if swap_sign and _fs is not None and not _fs.swap_allowed(instrument, int(s)):
                i += 1; continue                      # skip the negative-swap side
            j = i + delay
            if j >= n - 1:
                break
            if exit_mode == "time":
                k = min(j + H, n - 1)
            else:
                k = j + 1
                while k < n - 1 and (not np.isfinite(anc[k]) or s * (px[k] - anc[k]) < 0):
                    k += 1
                k = min(k, n - 1)
            nights = max(1, (idx[k] - idx[j]).days)
            fin = _fs.swap_bps(instrument, int(s)) if _fs is not None else -0.5   # signed
            ret = s * (px[k] / px[j] - 1) * 1e4 - cost + nights * fin
            sd.append(s); rt.append(ret); ty.append(idx[i].year); i = max(k, i + 1)
        else:
            i += 1
    return np.array(sd, float), np.array(rt), np.array(ty)


def stats(sd, rt, ty):
    n = len(rt)
    if n < 30:
        return None
    m = rt.mean(); t = m / rt.std() * np.sqrt(n) if rt.std() > 0 else 0
    L = rt[sd > 0]; S = rt[sd < 0]
    yrs = pd.Series(rt).groupby(pd.Series(ty)).mean()
    return dict(n=n, mean=m, t=t, wr=(rt > 0).mean(),
                mL=L.mean() if len(L) else np.nan, mS=S.mean() if len(S) else np.nan,
                two_sided=bool(len(L) and len(S) and L.mean() > 0 and S.mean() > 0),
                yrs_pos=int((yrs > 0).sum()), yrs_tot=len(yrs))


GRID = {
    "swing_mom": {"donchian": (10, 20), "tsmom": (10, 20), "ma_cross": (10, 20)},
    "swing_mr": {"rsi2": (10, 5), "bollinger": (2.0, 2.5), "nday_rev": (3, 5)},
}


def run(family, instruments):
    rows = []
    for name in instruments:
        df = load(name); cost = COST[name]; fin = FIN[name]
        for logic, params in GRID[family].items():
            exits = ("time",) if family == "swing_mom" else ("time", "mean")
            Hs = (5, 10) if family == "swing_mom" else (5,)
            for p in params:
                sig = signal(df, family, logic, p)
                for ex in exits:
                    for H in Hs:
                        s0, r0, y0 = trades(df, sig, ex, H, cost, fin, 0)
                        st = stats(s0, r0, y0)
                        if st is None:
                            continue
                        d1 = np.nan
                        if st["mean"] > 0:
                            s1, r1, _ = trades(df, sig, ex, H, cost, fin, 1)
                            d1 = r1.mean() if len(r1) > 5 else np.nan
                        rows.append(dict(instr=name, family=family, logic=logic, p=p,
                                         exit=ex, H=H, delay1=d1, **st))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    fam = sys.argv[1]; instr = sys.argv[2].split(",")
    R = run(fam, instr)
    R.to_csv(D / f"{fam}_{instr[0]}_grid.csv", index=False)
    cols = ["instr", "logic", "p", "exit", "H", "n", "mean", "t", "delay1", "mL", "mS", "yrs_pos", "yrs_tot"]
    print(f"=== {fam} {instr} : N={len(R)} ===")
    print(f"net>0: {(R['mean']>0).sum()}  two-sided&net>0: {((R['mean']>0)&R.two_sided).sum()}"
          f"  &delay1>0: {((R['mean']>0)&R.two_sided&(R.delay1>0)).sum()}")
    ts = R[(R['mean']>0)&R.two_sided].sort_values('t', ascending=False)
    print("Two-sided positive:", len(ts))
    if len(ts): print(ts[cols].head(10).to_string(index=False))
    print("\nTop 6 net-positive by t:")
    print(R[R['mean']>0].sort_values('t', ascending=False)[cols].head(6).to_string(index=False))
