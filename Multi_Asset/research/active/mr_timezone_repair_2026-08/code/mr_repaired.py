"""Phase 2 — the MR grid of `mr_deepdive.py`, re-run on the window it never tested.

The original consumed `data/panels/m5_indices/*` whose `timestamp_utc` column is
EET/EEST and did `tz_localize("UTC")` -> 7 h off.  43.9 % of its "RTH" was pre-market
and 38.7 % of the real RTH, including the whole close, was never visited.

This re-run:
  - reads `data/deep_history_utc/` (true UTC, verified) via the scratchpad cache;
  - uses the EXCHANGE clock with its own DST (L56);
  - gates at GROSS, cost_rt = 0;
  - two-sided with DISJOINT legs (L25) — no leg is ever the negation of the other;
  - delay+1 on ENTRY *and* on EXIT (L59): enter at OPEN of bar j+1, exit at OPEN of
    bar k+1.  There is no stop and no bracket, so no barrier is ever filled;
  - compares every leg to the UNCONDITIONAL expectation of the same trade form at
    the same holding length on the same bars (L58);
  - block bootstrap (L=5 trades), HAC(6) t.

Two window scopes are reported:
  FULL   = the whole true cash session
  CLOSE  = the last 90 minutes only — the zone the buggy study could never reach.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(sys.argv[1])
RNG = np.random.default_rng(20260801)

SPEC = {  # instrument -> (tz, open_mod, close_mod)
    "US500": ("America/New_York", 9 * 60 + 30, 16 * 60),
    "US100": ("America/New_York", 9 * 60 + 30, 16 * 60),
    "US30":  ("America/New_York", 9 * 60 + 30, 16 * 60),
    "GER40": ("Europe/Berlin",    9 * 60,      17 * 60 + 30),
}
TF_MIN = {"5m": 5, "15m": 15, "30m": 30}
THETAS = {"sma20_z": (1.5, 2.5), "ema20_z": (1.5, 2.5), "vwap_z": (1.5, 2.5),
          "rsi14": (20, 25), "range_fade": (0.8, 0.92)}


def rth_bars(name: str, tf: str, scope: str) -> pd.DataFrame:
    tz, om, cl = SPEC[name]
    df = pd.read_parquet(CACHE / f"{name}_M1.parquet")
    idx = df.index.tz_convert(tz)
    mod = idx.hour * 60 + idx.minute
    lo = cl - 90 if scope == "CLOSE" else om
    m = (mod >= lo) & (mod < cl) & (idx.dayofweek < 5)
    d = pd.DataFrame({"open": df["open"].values[m], "close": df["close"].values[m]},
                     index=idx[m])
    step = TF_MIN[tf]
    # session-anchored resample: bucket = minutes since session open
    day = d.index.normalize()
    k = ((d.index.hour * 60 + d.index.minute) - lo) // step
    grp = [pd.Series(day, index=d.index, name="day"),
           pd.Series(np.asarray(k), index=d.index, name="k")]
    out = pd.DataFrame({
        "open": d["open"].groupby(grp).first(),
        "px": d["close"].groupby(grp).last(),
    }).reset_index()
    out = out[out["k"] >= 0]
    return out


def compute_dev(df: pd.DataFrame, logic: str) -> np.ndarray:
    px, sess = df["px"], df["day"]
    g = px.groupby(sess)
    if logic in ("sma20_z", "ema20_z", "vwap_z"):
        if logic == "sma20_z":
            anc = g.transform(lambda x: x.rolling(20, min_periods=20).mean())
        elif logic == "ema20_z":
            anc = g.transform(lambda x: x.ewm(span=20, min_periods=20).mean())
        else:  # no volume on CFD series -> session-cumulative mean proxy (flagged)
            anc = px.groupby(sess).expanding().mean().reset_index(level=0, drop=True)
        sd = g.transform(lambda x: x.rolling(20, min_periods=20).std())
        return ((px - anc) / sd).values
    if logic == "rsi14":
        d = px.groupby(sess).diff()
        up, dn = d.clip(lower=0), (-d).clip(lower=0)
        ru = up.groupby(sess).transform(lambda x: x.ewm(alpha=1 / 14, min_periods=14).mean())
        rd = dn.groupby(sess).transform(lambda x: x.ewm(alpha=1 / 14, min_periods=14).mean())
        return (100 - 100 / (1 + ru / rd.replace(0, np.nan)) - 50).values
    if logic == "range_fade":
        hi, lo = px.groupby(sess).cummax(), px.groupby(sess).cummin()
        return (((px - lo) / (hi - lo) - 0.5) * 2).values
    raise ValueError(logic)


def build_trades(op, px, dev, sess, theta, exit_type, H, eligible=None):
    """Non-overlapping fade trades, delay+1 on ENTRY and EXIT (both are bar OPENs).

    `eligible` optionally restricts which bars may *signal* (used to isolate the
    close zone while keeping the anchor estimated on the whole session).
    """
    n = len(px)
    i = 0
    side, ret, dur, ent = [], [], [], []
    while i < n - 2:
        di = dev[i]
        if not (np.isfinite(di) and abs(di) > theta) or (eligible is not None and not eligible[i]):
            i += 1
            continue
        j = i + 1                                    # entry bar (delay+1)
        if sess[j] != sess[i]:
            i += 1
            continue
        s = -1.0 if di > 0 else 1.0
        if exit_type == "ts":
            k = j + H
        else:                                        # mean-touch on the dev series
            k = j
            while k + 1 < n and sess[k + 1] == sess[j]:
                if not np.isfinite(dev[k]) or s * dev[k] >= 0:
                    break
                k += 1
        k = min(k, n - 2)
        while k > j and sess[k + 1] != sess[j]:      # exit bar must stay in session
            k -= 1
        if k <= j:
            i += 1
            continue
        side.append(s)
        ret.append(s * (op[k + 1] / op[j] - 1.0) * 1e4)   # exit = OPEN of bar k+1
        dur.append(k + 1 - j)
        ent.append(j)
        i = max(k, i + 1)
    return (np.array(side), np.array(ret, float),
            np.array(dur, int), np.array(ent, int))


def uncond_by_dur(op, sess, durs):
    """L58 baseline: unconditional mean of the SAME trade form (long, same holding),
    over every bar of the sample, averaged over the realised duration mix."""
    n = len(op)
    out = {}
    for d in np.unique(durs):
        a = np.arange(0, n - d)
        ok = sess[a] == sess[a + d]
        if ok.sum() < 50:
            out[d] = np.nan
            continue
        out[d] = np.mean((op[a + d][ok] / op[a][ok] - 1.0) * 1e4)
    return float(np.nanmean([out[d] for d in durs]))


def hac_t(x, lags=6):
    x = np.asarray(x, float)
    n = len(x)
    if n < 30:
        return np.nan
    e = x - x.mean()
    s = (e @ e) / n
    for l in range(1, lags + 1):
        s += 2 * (1 - l / (lags + 1)) * ((e[l:] @ e[:-l]) / n)
    return x.mean() / np.sqrt(s / n) if s > 0 else np.nan


def boot_p(x, nboot=1000, L=5):
    x = np.asarray(x, float)
    n = len(x)
    if n < 30:
        return np.nan
    nb = int(np.ceil(n / L))
    st = RNG.integers(0, n, size=(nboot, nb))
    idx = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(nboot, -1)[:, :n] % n
    m = x[idx].mean(axis=1)
    return min(2 * min((m <= 0).mean(), (m >= 0).mean()), 1.0)


if __name__ == "__main__":
    pd.set_option("display.width", 260, "display.max_columns", 40, "display.max_rows", 400)
    rows = []
    for scope in ("FULL", "CLOSE", "CLOSE_ENTRY"):
        for name in SPEC:
            for tf in TF_MIN:
                df = rth_bars(name, tf, "CLOSE" if scope == "CLOSE" else "FULL")
                op = df["open"].values.astype(float)
                px = df["px"].values.astype(float)
                sess = df["day"].values
                H = {"5m": 6, "15m": 4, "30m": 2}[tf]
                elig = None
                if scope == "CLOSE_ENTRY":
                    # signal bar must sit in the last 90 min of the true cash session
                    nb = 90 // TF_MIN[tf]
                    kmax = df.groupby("day")["k"].transform("max")
                    elig = (df["k"] > kmax - nb).values
                for logic in THETAS:
                    dev = compute_dev(df, logic)
                    for th in THETAS[logic]:
                        for ex in ("ts", "mt"):
                            s, r, d, e = build_trades(op, px, dev, sess, th, ex, H, elig)
                            if len(r) < 60:
                                continue
                            L, S = r[s > 0], r[s < 0]
                            if len(L) < 30 or len(S) < 30:
                                continue
                            u = uncond_by_dur(op, sess, d)
                            uL = uncond_by_dur(op, sess, d[s > 0])
                            uS = uncond_by_dur(op, sess, d[s < 0])
                            rows.append(dict(
                                scope=scope, instr=name, tf=tf, logic=logic, theta=th,
                                exit=ex, H=H, n=len(r),
                                nL=len(L), mL=L.mean(), tL=hac_t(L), exL=L.mean() - uL,
                                nS=len(S), mS=S.mean(), tS=hac_t(S), exS=S.mean() + uS,
                                m=r.mean(), t=hac_t(r), p=boot_p(r), uncond=u,
                                med_dur=float(np.median(d))))
    R = pd.DataFrame(rows)
    R.to_csv(CACHE / "mr_repaired_cells.csv", index=False)
    print("cells tested: %d  %s\n" % (len(R), R.scope.value_counts().to_dict()))
    for scope in ("FULL", "CLOSE", "CLOSE_ENTRY"):
        Z = R[R.scope == scope]
        print(f"===== {scope} — two-sided GROSS summary (cost = 0) =====")
        print(f"  cells: {len(Z)} | mean two-sided m = {Z.m.mean():.3f} bps | "
              f"cells with m>0: {(Z.m>0).sum()} | with t>2.5: {(Z.t>2.5).sum()} | "
              f"with t<-2.5: {(Z.t<-2.5).sum()}")
        # L25: BOTH legs must be positive, and both must beat their unconditional
        surv = Z[(Z.mL > 0) & (Z.mS > 0) & (Z.exL > 0) & (Z.exS > 0) & (Z.t > 2.0)]
        print(f"  L25+L58 survivors (both legs >0, both beat unconditional, t>2.0): {len(surv)}")
        if len(surv):
            print(surv[["instr", "tf", "logic", "theta", "exit", "n", "nL", "mL", "tL",
                        "exL", "nS", "mS", "tS", "exS", "m", "t", "p", "uncond"]]
                  .round(3).to_string(index=False))
        print("  best 6 cells by two-sided mean:")
        print(Z.nlargest(6, "m")[["instr", "tf", "logic", "theta", "exit", "n",
                                  "mL", "tL", "mS", "tS", "m", "t", "p", "uncond"]]
              .round(3).to_string(index=False))
        print()
