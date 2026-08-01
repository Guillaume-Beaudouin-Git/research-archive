"""Falsification battery for the single B1 survivor candidate (GER40 close fade).

Nothing here is designed to confirm.  Each block is a way for the candidate to die:
  A. time-of-day placebo — is 17:30 special, or is this generic 10-min MR?
  B. auction decomposition — is the P&L inside the 17:30-17:35 closing auction,
     where the cash-index print is derived rather than traded?
  C. sub-period stability
  D. clock test (L56) — exchange clock vs fixed UTC
  E. concentration — does a handful of sessions carry it?
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(sys.argv[1])
RNG = np.random.default_rng(20260801)
TZ = "Europe/Berlin"
CLOSE = 17 * 60 + 30


def load(name="GER40", tz=TZ):
    df = pd.read_parquet(CACHE / f"{name}_M1.parquet")
    idx = df.index.tz_convert(tz)
    return pd.DataFrame({
        "day": idx.normalize().tz_localize(None),
        "mod": idx.hour * 60 + idx.minute,
        "open": df["open"].values, "close": df["close"].values,
        "high": df["high"].values, "low": df["low"].values,
    })


def wide(sub: pd.DataFrame, mods) -> dict:
    s = sub[np.isin(sub["mod"], list(mods))].drop_duplicates(["day", "mod"], keep="last")
    return {f: s.pivot(index="day", columns="mod", values=f) for f in ("open", "close", "high", "low")}


def hac_t(x, lags=6):
    x = np.asarray(x, float)
    n = len(x)
    if n < 20:
        return np.nan
    e = x - x.mean()
    s = (e @ e) / n
    for l in range(1, lags + 1):
        s += 2 * (1 - l / (lags + 1)) * ((e[l:] @ e[:-l]) / n)
    return x.mean() / np.sqrt(s / n) if s > 0 else np.nan


def boot_p(x, nboot=2000, L=5):
    x = np.asarray(x, float)
    n = len(x)
    if n < 20:
        return np.nan
    nb = int(np.ceil(n / L))
    st = RNG.integers(0, n, size=(nboot, nb))
    idx = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(nboot, -1)[:, :n] % n
    m = x[idx].mean(axis=1)
    return min(2 * min((m <= 0).mean(), (m >= 0).mean()), 1.0)


def cell(sig_bps: pd.Series, r_bps: pd.Series, theta: float, label: str) -> dict:
    d = pd.concat([sig_bps.rename("s"), r_bps.rename("r")], axis=1).dropna()
    if len(d) < 200:
        return dict(label=label, n=len(d))
    s = d["s"]
    z = ((s - s.shift(1).rolling(250, min_periods=100).mean())
         / s.shift(1).rolling(250, min_periods=100).std())
    m = z.notna()
    z, r = z[m].values, d["r"][m].values
    yr = d.index[m].year.values
    up, dn = z > theta, z < -theta
    if up.sum() < 25 or dn.sum() < 25:
        return dict(label=label, n=int(m.sum()))
    rL, rS = r[dn], -r[up]
    both = np.concatenate([rL, rS])
    ys = pd.Series(both).groupby(pd.Series(np.concatenate([yr[dn], yr[up]]))).mean()
    return dict(label=label, n=int(m.sum()), uncond=r.mean(), unc_t=hac_t(r),
                nL=int(dn.sum()), mL=rL.mean(), tL=hac_t(rL),
                nS=int(up.sum()), mS=rS.mean(), tS=hac_t(rS),
                m_both=both.mean(), t_both=hac_t(both), p_boot=boot_p(both),
                sd=both.std(), yrs_pos=int((ys > 0).sum()), yrs=len(ys))


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_columns", 40)
    sub = load()
    THE = 1.0
    print(f"### GER40 falsification battery — theta={THE}, sig=last 30 min, hold=10 min\n")

    # ------------------------------------------------------------------ A. placebo
    print("--- A. TIME-OF-DAY PLACEBO: identical trade form anchored every 30 min ---")
    anchors = list(range(8 * 60, 22 * 60 + 1, 30))
    mods = sorted({a + k for a in anchors for k in (-31, -1, 1, 11)})
    W = wide(sub, mods)
    rows = []
    for a in anchors:
        try:
            sig = (W["close"][a - 1] / W["close"][a - 31] - 1) * 1e4
            r = (W["open"][a + 11] / W["open"][a + 1] - 1) * 1e4
        except KeyError:
            continue
        st = cell(sig, r, THE, f"{a//60:02d}:{a%60:02d}")
        if "m_both" in st:
            rows.append(st)
    A = pd.DataFrame(rows)
    A["is_close"] = A["label"] == "17:30"
    print(A[["label", "n", "nL", "nS", "m_both", "t_both", "p_boot", "uncond", "is_close"]]
          .round(3).to_string(index=False))
    r_close = A.loc[A.is_close, "m_both"].iloc[0]
    print(f"\n  17:30 rank among {len(A)} anchors by m_both: "
          f"{int((A['m_both'] >= r_close).sum())} (1 = best); "
          f"pctile {100*(A['m_both'] < r_close).mean():.0f}")
    print(f"  anchors with t_both > 2.0: {(A.t_both > 2).sum()} / {len(A)}  "
          f"[expected by chance at 5% one-sided: {0.025*len(A):.1f}]")

    # ------------------------------------- B. auction decomposition / delayed entry
    print("\n--- B. AUCTION DECOMPOSITION (Xetra closing auction 17:30-17:35) ---")
    mods = sorted({CLOSE + k for k in (-31, -1, 0, 1, 6, 11, 16, 21, 31)})
    W = wide(sub, mods)
    sig = (W["close"][CLOSE - 1] / W["close"][CLOSE - 31] - 1) * 1e4
    segs = {
        "17:31->17:36  (auction leg)": (CLOSE + 1, CLOSE + 6),
        "17:36->17:41  (post-auction)": (CLOSE + 6, CLOSE + 11),
        "17:31->17:41  (full 10 min)": (CLOSE + 1, CLOSE + 11),
        "17:36->17:46  (entry AFTER auction)": (CLOSE + 6, CLOSE + 16),
        "17:41->17:51  (entry +10 min later)": (CLOSE + 11, CLOSE + 21),
    }
    rows = [cell(sig, (W["open"][b] / W["open"][a] - 1) * 1e4, THE, lab)
            for lab, (a, b) in segs.items()]
    B = pd.DataFrame(rows)
    print(B[["label", "n", "nL", "mL", "tL", "nS", "mS", "tS", "m_both", "t_both",
             "p_boot", "uncond", "unc_t"]].round(3).to_string(index=False))

    # ------------------------------------------------------- C. sub-period stability
    print("\n--- C. SUB-PERIOD STABILITY (full 10-min hold, theta 1.0 and 1.5) ---")
    r_full = (W["open"][CLOSE + 11] / W["open"][CLOSE + 1] - 1) * 1e4
    for th in (1.0, 1.5):
        for lo, hi in [(2014, 2019), (2020, 2026), (2014, 2026)]:
            m = (sig.index.year >= lo) & (sig.index.year <= hi)
            st = cell(sig[m], r_full[m], th, f"theta{th} {lo}-{hi}")
            print("  " + ", ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                                   for k, v in st.items()
                                   if k in ("label", "n", "nL", "mL", "nS", "mS",
                                            "m_both", "t_both", "p_boot", "yrs_pos", "yrs")))

    # --------------------------------------------------------------- D. clock test
    print("\n--- D. CLOCK TEST (L56): same wall-clock windows in FIXED UTC ---")
    subu = load(tz="UTC")
    for utc_close in (15 * 60 + 30, 16 * 60 + 30):
        Wu = wide(subu, sorted({utc_close + k for k in (-31, -1, 1, 11)}))
        sg = (Wu["close"][utc_close - 1] / Wu["close"][utc_close - 31] - 1) * 1e4
        rr = (Wu["open"][utc_close + 11] / Wu["open"][utc_close + 1] - 1) * 1e4
        st = cell(sg, rr, THE, f"UTC {utc_close//60:02d}:{utc_close%60:02d}")
        print("  " + ", ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                               for k, v in st.items()
                               if k in ("label", "n", "m_both", "t_both", "p_boot")))
    print("  (exchange clock 17:30 Berlin = 16:30 UTC in winter, 15:30 UTC in summer)")

    # ------------------------------------------------------------- E. concentration
    print("\n--- E. CONCENTRATION / TAIL ---")
    d = pd.concat([sig.rename("s"), r_full.rename("r")], axis=1).dropna()
    z = ((d.s - d.s.shift(1).rolling(250, min_periods=100).mean())
         / d.s.shift(1).rolling(250, min_periods=100).std())
    m = z.notna()
    z, r, dd = z[m].values, d.r[m].values, d.index[m]
    for th in (1.0, 1.5):
        up, dn = z > th, z < -th
        pnl = np.concatenate([r[dn], -r[up]])
        srt = np.sort(pnl)[::-1]
        tot = pnl.sum()
        print(f"  theta={th}: n={len(pnl)} mean={pnl.mean():.3f} sd={pnl.std():.2f} "
              f"skew={pd.Series(pnl).skew():.2f} "
              f"top1%_share={srt[:max(1,len(pnl)//100)].sum()/tot:.1%} "
              f"top5%_share={srt[:max(1,len(pnl)//20)].sum()/tot:.1%} "
              f"win_rate={(pnl>0).mean():.3f} "
              f"drop_top5%_mean={np.sort(pnl)[::-1][max(1,len(pnl)//20):].mean():.3f}")
        # per-trade Sharpe -> annualised with sqrt(trades/yr)  (L47)
        tpy = len(pnl) / ((dd.year.max() - dd.year.min()) + 1)
        print(f"           trades/yr={tpy:.1f}  gross SR_ann="
              f"{pnl.mean()/pnl.std()*np.sqrt(tpy):.3f}  "
              f"net@1.8bps SR_ann={(pnl.mean()-1.8)/pnl.std()*np.sqrt(tpy):.3f}  "
              f"gross bps/yr={pnl.mean()*tpy:.1f}  net bps/yr={(pnl.mean()-1.8)*tpy:.1f}")
