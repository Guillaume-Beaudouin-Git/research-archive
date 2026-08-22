"""
directional_deepdive.py — Breakout & intraday-momentum deep-dives for FTMO.

Same protocol as mr_deepdive: every cell under non-overlapping trades + per-trade
bps cost + 1-bar execution-delay column + the TWO-SIDED test up front (up-leg and
down-leg reported separately; one-sided long = beta = reject) + N_trials tracked
for DSR on the total space.

Reuses cached intraday panels from mr_deepdive (outputs/mr_dd/{name}_{tf}.parquet),
columns: px, vol, session.

Signal convention: sig[i] = +1 (long entry condition at bar i), -1 (short), 0 none.
Decision uses info up to close[i]; entry at i (+delay), no look-ahead.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

MR = Path("/sessions/blissful-upbeat-newton/mnt/outputs/mr_dd")
OUT = Path("/sessions/blissful-upbeat-newton/mnt/outputs/dir")
OUT.mkdir(parents=True, exist_ok=True)
COST = {"NQ": 1.5, "US500": 1.5, "US100": 1.5, "US30": 1.5, "GER40": 1.5, "EURUSD": 1.0}
TF_PER_SESSION = {"5m": 78, "15m": 26, "30m": 13}   # approx US RTH bars


def load(name, tf):
    df = pd.read_parquet(MR / f"{name}_{tf}.parquet")
    df["ret"] = df.groupby("session")["px"].pct_change()
    return df


def sess_roll(s, sess, win, fn):
    return getattr(s.groupby(sess), "transform")(lambda x: getattr(x.rolling(win, min_periods=win), fn)())


# ----------------------------- signal logics --------------------------------
def signal(df, family, logic, p):
    px = df["px"]; sess = df["session"]; g = px.groupby(sess)
    if family == "breakout":
        if logic == "donchian":                      # break prior-N high/low within session
            hi = g.transform(lambda x: x.rolling(p, min_periods=p).max().shift(1))
            lo = g.transform(lambda x: x.rolling(p, min_periods=p).min().shift(1))
            return np.where(px > hi, 1, np.where(px < lo, -1, 0))
        if logic == "atr_brk":                        # close beyond k*ATR of last bar move
            tr = px.groupby(sess).diff().abs()
            atr = tr.groupby(sess).transform(lambda x: x.rolling(14, min_periods=14).mean())
            mv = px.groupby(sess).diff()
            return np.where(mv > p * atr, 1, np.where(mv < -p * atr, -1, 0))
        if logic == "orb":                            # break of first-p-bars session range
            idxn = df.groupby("session").cumcount()
            orh = px.where(idxn < p).groupby(sess).transform("max")
            orl = px.where(idxn < p).groupby(sess).transform("min")
            sig = np.where((idxn >= p) & (px > orh), 1, np.where((idxn >= p) & (px < orl), -1, 0))
            return sig
    if family == "momentum":
        if logic == "tsmom":                          # sign of past-N-bar return, vol-scaled
            r = px / g.transform(lambda x: x.shift(p)) - 1
            sd = df["ret"].groupby(sess).transform(lambda x: x.rolling(20, min_periods=20).std())
            z = r / (sd * np.sqrt(p))
            return np.where(z > 1.0, 1, np.where(z < -1.0, -1, 0))
        if logic == "vwap_dist":                      # price vs session VWAP-proxy
            if df["vol"].notna().any():
                anc = (px * df["vol"]).groupby(sess).cumsum() / df["vol"].groupby(sess).cumsum()
            else:
                anc = px.groupby(sess).expanding().mean().reset_index(level=0, drop=True)
            sd = df["ret"].groupby(sess).transform(lambda x: x.rolling(20, min_periods=20).std())
            z = (px / anc - 1) / sd
            return np.where(z > p, 1, np.where(z < -p, -1, 0))
        if logic == "gao":                            # first-p-bars return -> trade rest of session
            idxn = df.groupby("session").cumcount()
            op = px.where(idxn == 0).groupby(sess).transform("max")
            ref = px.where(idxn == p - 1).groupby(sess).transform("max")
            early = ref / op - 1
            return np.where((idxn == p) & (early > 0), 1, np.where((idxn == p) & (early < 0), -1, 0))
    raise ValueError((family, logic))


def trades(df, sig, exit_type, H, cost, delay=0):
    px = df["px"].values; sess = df["session"].values.astype("datetime64[D]")
    yr = pd.DatetimeIndex(df.index).year.values
    n = len(px); i = 0; sd = []; rt = []; ty = []
    # last bar index per session for EOD exit
    while i < n - 1 - delay:
        s = sig[i]
        if s != 0 and np.isfinite(px[i]):
            j = i + delay
            if j >= n - 1 or sess[j] != sess[i]:
                i += 1; continue
            if exit_type == "eod":
                k = j
                while k + 1 < n and sess[k + 1] == sess[j]:
                    k += 1
            else:                                     # time-stop H bars (capped to session)
                k = j + H
                if k >= n or sess[k] != sess[j]:
                    k = j
                    while k + 1 < n and sess[k + 1] == sess[j]:
                        k += 1
            ret = s * (px[k] / px[j] - 1) * 1e4 - cost
            sd.append(s); rt.append(ret); ty.append(yr[i]); i = max(k, i + 1)
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
    return dict(n=n, mean=m, t=t, wr=(rt > 0).mean(), nL=len(L), nS=len(S),
                mL=L.mean() if len(L) else np.nan, mS=S.mean() if len(S) else np.nan,
                two_sided=bool((len(L) and L.mean() > 0) and (len(S) and S.mean() > 0)),
                yrs_pos=int((yrs > 0).sum()), yrs_tot=len(yrs))


GRID = {
    "breakout": {"donchian": (10, 20), "atr_brk": (1.0, 2.0), "orb": (3, 6)},
    "momentum": {"tsmom": (6, 12), "vwap_dist": (1.5, 2.5), "gao": (6, 12)},
}


def run(family, instruments, tfs=("5m", "15m", "30m"), exits=("eod", "ts"), H=8):
    rows = []
    for name in instruments:
        cost = COST[name]
        for tf in tfs:
            df = load(name, tf)
            for logic, params in GRID[family].items():
                for p in params:
                    sig = signal(df, family, logic, p)
                    for ex in exits:
                        sd, rt, ty = trades(df, sig, ex, H, cost, 0)
                        st = stats(sd, rt, ty)
                        if st is None:
                            continue
                        d1 = np.nan
                        if st["mean"] > 0:
                            s2, r2, _ = trades(df, sig, ex, H, cost, 1)
                            d1 = r2.mean() if len(r2) > 5 else np.nan
                        rows.append(dict(instr=name, tf=tf, family=family, logic=logic,
                                         p=p, exit=ex, delay1=d1, **st))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    fam = sys.argv[1] if len(sys.argv) > 1 else "breakout"
    instr = ["NQ", "US500", "US100", "US30", "GER40", "EURUSD"]
    R = run(fam, instr)
    R.to_csv(OUT / f"{fam}_grid.csv", index=False)
    print(f"=== {fam} grid: N_trials={len(R)} ===")
    print(f"net mean>0: {(R['mean']>0).sum()}   two-sided & net>0: {((R['mean']>0)&R.two_sided).sum()}"
          f"   & delay1>0: {((R['mean']>0)&R.two_sided&(R.delay1>0)).sum()}")
    bar = (2*np.log(len(R)))**0.5
    print(f"DSR bar (expected max|t|, N={len(R)}): ~{bar:.2f}")
    ts = R[(R['mean']>0)&R.two_sided].sort_values('t', ascending=False)
    cols = ["instr","tf","logic","p","exit","n","mean","t","delay1","mL","mS","yrs_pos","yrs_tot"]
    print(f"\nTwo-sided positive cells ({len(ts)}):")
    print(ts[cols].head(15).to_string(index=False) if len(ts) else "  NONE")
    print(f"\nTop 8 net-positive by t (any sidedness):")
    print(R[R['mean']>0].sort_values('t',ascending=False)[cols].head(8).to_string(index=False))
