"""AUDIT of the K2 placebo baseline.

The matched placebo returned a median of -5.9 bps where the unconditional S_V shape
(short 2 days, long 3 days) should average drift*(m+1-(k-1)) = +0.12 bps. A placebo
whose own baseline is biased cannot certify anything, so we decompose it here:
unconditional, by day-of-month, by weekday, and under each matching constraint
switched on one at a time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import lib

K, M = 3, 2


def sv_shape(px: pd.DataFrame) -> pd.Series:
    """S_V-shaped return anchored on every trading day t (short t-k..t-1, long t-1..t+m)."""
    c = np.log(px["close"].to_numpy())
    n = len(c)
    out = np.full(n, np.nan)
    for t in range(K, n - M):
        out[t] = (-(c[t - 1] - c[t - K]) + (c[t + M] - c[t - 1])) * 1e4
    return pd.Series(out, index=px.index, name="sv")


def main() -> None:
    px = lib.load_px("ZN")
    auc = lib.load_auctions()
    sv = sv_shape(px)
    d = px["ret"].mean() * 1e4

    print("=" * 96)
    print("A — UNCONDITIONAL BASELINE OF THE S_V SHAPE (every trading day as a pseudo-event)")
    print("=" * 96)
    m, t = lib.hac_t(sv.dropna().to_numpy())
    print(f"  all days            n={sv.notna().sum():5d}  mean {m:+7.3f} bps  t {t:+6.2f}")
    print(f"  drift-implied       = drift*(m+1) - drift*(k-1) = {d*(M+1) - d*(K-1):+7.3f} bps")

    print()
    print("=" * 96)
    print("B — S_V SHAPE BY DAY-OF-MONTH (this is what the +-3 dom matching selects on)")
    print("=" * 96)
    dom = pd.Series(px.index.day, index=px.index)
    tab = pd.DataFrame({"sv": sv, "dom": dom}).dropna()
    g = tab.groupby("dom")["sv"].agg(["mean", "count"])
    for lo, hi in [(1, 5), (6, 10), (11, 15), (16, 20), (21, 25), (26, 31)]:
        sub = tab[(tab.dom >= lo) & (tab.dom <= hi)]
        mm, tt = lib.hac_t(sub.sv.to_numpy())
        print(f"  dom {lo:2d}-{hi:2d}  n={len(sub):5d}  mean {mm:+7.2f}  t {tt:+6.2f}")

    print()
    print("=" * 96)
    print("C — S_V SHAPE BY WEEKDAY (the second matching key)")
    print("=" * 96)
    tab["dow"] = tab.index.day_name()
    for name, sub in tab.groupby("dow", sort=False):
        mm, tt = lib.hac_t(sub.sv.to_numpy())
        print(f"  {name:10s} n={len(sub):5d}  mean {mm:+7.2f}  t {tt:+6.2f}")

    print()
    print("=" * 96)
    print("D — EFFECT OF EACH PLACEBO CONSTRAINT, APPLIED ONE AT A TIME (10y event set)")
    print("=" * 96)
    a10 = auc[auc.term == 10].sort_values("auctionDate")
    ev, _ = lib.event_positions(px.index, a10.auctionDate.reset_index(drop=True), K, M,
                                require_announced=a10.announcementDate.reset_index(drop=True))
    er = lib.event_returns(px, ev, K, M)
    real = float(er.v_bps.mean())
    ev_pos = set(er.i_t.astype(int))

    idx = px.index
    pos_all = np.array([i for i in range(K, len(idx) - M - 1) if not np.isnan(sv.iloc[i])])
    dowa, doma = idx.dayofweek.to_numpy(), idx.day.to_numpy()

    # blackout around long-end coupon auctions
    bad = np.zeros(len(idx), dtype=bool)
    for dt in auc[auc.term.isin([10, 20, 30])].auctionDate:
        p = idx.searchsorted(dt, side="left")
        bad[max(0, p - 3): min(len(idx), p + 4)] = True

    ev_dow = dowa[er.i_t.astype(int)]
    ev_dom = doma[er.i_t.astype(int)]

    def pool_mean(mask_fn, label):
        vals = []
        for j in range(len(er)):
            sel = mask_fn(j)
            p = pos_all[sel[pos_all]]
            if len(p) >= 5:
                vals.append(sv.iloc[p].mean())
        mm = float(np.mean(vals)) if vals else np.nan
        print(f"  {label:52s} pool-avg {mm:+7.2f} bps   (real {real:+.2f})")

    base = np.ones(len(idx), dtype=bool)
    pool_mean(lambda j: base, "no constraint (all days)")
    pool_mean(lambda j: (dowa == ev_dow[j]), "weekday only")
    pool_mean(lambda j: (np.abs(doma - ev_dom[j]) <= 3), "day-of-month +-3 only")
    pool_mean(lambda j: ~bad, "auction blackout only")
    pool_mean(lambda j: (dowa == ev_dow[j]) & (np.abs(doma - ev_dom[j]) <= 3),
              "weekday + dom+-3 (NO blackout)")
    pool_mean(lambda j: (dowa == ev_dow[j]) & (np.abs(doma - ev_dom[j]) <= 3) & ~bad,
              "weekday + dom+-3 + blackout  [PREREGISTERED]")

    print()
    print("=" * 96)
    print("E — WHAT THE BLACKOUT ACTUALLY REMOVES")
    print("=" * 96)
    print(f"  trading days inside blackout : {int(bad.sum())} / {len(idx)} "
          f"({100*bad.mean():.1f}%)")
    mm, tt = lib.hac_t(sv[~bad].dropna().to_numpy())
    print(f"  S_V shape OUTSIDE blackout   : mean {mm:+7.2f}  t {tt:+6.2f}  n={int((~bad).sum())}")
    mm, tt = lib.hac_t(sv[bad].dropna().to_numpy())
    print(f"  S_V shape INSIDE  blackout   : mean {mm:+7.2f}  t {tt:+6.2f}  n={int(bad.sum())}")
    dom_in = pd.Series(doma[bad]).describe(percentiles=[.1, .5, .9])
    dom_out = pd.Series(doma[~bad]).describe(percentiles=[.1, .5, .9])
    print(f"  dom inside  blackout: median {dom_in['50%']:.0f} p10 {dom_in['10%']:.0f} p90 {dom_in['90%']:.0f}")
    print(f"  dom outside blackout: median {dom_out['50%']:.0f} p10 {dom_out['10%']:.0f} p90 {dom_out['90%']:.0f}")

    print()
    print("=" * 96)
    print("F — THE HONEST CONTRAST: auction days vs same-dom-window NON-auction days, no blackout")
    print("=" * 96)
    near = np.zeros(len(idx), dtype=bool)
    for j in range(len(er)):
        near |= (np.abs(doma - ev_dom[j]) <= 3) & (dowa == ev_dow[j])
    non_ev = near.copy()
    for i in ev_pos:
        non_ev[i] = False
    mm, tt = lib.hac_t(sv[non_ev].dropna().to_numpy())
    print(f"  matched NON-auction days : n={int(non_ev.sum()):5d} mean {mm:+7.2f} t {tt:+6.2f}")
    mm2, tt2 = lib.hac_t(er.v_bps.to_numpy())
    print(f"  auction days             : n={len(er):5d} mean {mm2:+7.2f} t {tt2:+6.2f}")
    print(f"  CONTRAST (auction - matched non-auction) = {mm2-mm:+7.2f} bps")

    # two-sample HAC-ish contrast via pooled regression with a dummy
    import statsmodels.api as sm
    yy = pd.concat([sv[non_ev].dropna(), pd.Series(er.v_bps.to_numpy())])
    xx = np.r_[np.zeros(int(sv[non_ev].notna().sum())), np.ones(len(er))]
    X = sm.add_constant(xx)
    r = sm.OLS(yy.to_numpy(), X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    print(f"  dummy regression: beta {r.params[1]:+.2f} bps  t_HAC {r.tvalues[1]:+.2f}  "
          f"p {r.pvalues[1]:.4f}")


if __name__ == "__main__":
    main()
