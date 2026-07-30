"""Final checks: year-by-year consistency, intraday 13:00 ET split (descriptive,
zero power by construction), and an exploratory dose-response falsifier."""
from __future__ import annotations

import numpy as np
import pandas as pd

import lib

K, M = 3, 2


def main() -> None:
    px = lib.load_px("ZN")
    auc = lib.load_auctions()
    a10 = auc[auc.term == 10].sort_values("auctionDate").reset_index(drop=True)
    ev, _ = lib.event_positions(px.index, a10.auctionDate, K, M,
                                require_announced=a10.announcementDate)
    er = lib.event_returns(px, ev, K, M).reset_index(drop=True)

    print("=" * 92)
    print("G — YEAR-BY-YEAR CONSISTENCY  (B1 reference: 23/23 positive years)")
    print("=" * 92)
    yr = er.groupby(er.auction_date.dt.year)["v_bps"].agg(["mean", "count"])
    pos = int((yr["mean"] > 0).sum())
    print(f"  positive years: {pos} / {len(yr)}  ({100*pos/len(yr):.0f}%)")
    s = "  " + "  ".join(f"{y}:{v:+.0f}" for y, v in yr["mean"].items())
    for i in range(0, len(s), 92):
        print(s[i:i + 92])
    prepost = er.groupby(er.auction_date.dt.year)[["pre_bps", "post_bps"]].mean()
    print(f"  PRE  leg positive years: {int((prepost.pre_bps>0).sum())} / {len(prepost)}")
    print(f"  POST leg positive years: {int((prepost.post_bps>0).sum())} / {len(prepost)}")

    print()
    print("=" * 92)
    print("H — INTRADAY 13:00 ET SPLIT (DESCRIPTIVE ONLY — hourly cache covers ~2 years)")
    print("=" * 92)
    h = pd.read_parquet(lib.REPO / "data/raw/ZN_1h_cache.parquet")
    h.index = pd.DatetimeIndex(h.index)
    print(f"  hourly cache: {h.index[0]} -> {h.index[-1]}  n={len(h)} (tz {h.index.tz})")
    hh = h["close"]
    day = hh.index.normalize()
    rows = []
    for d in er.auction_date:
        dd = pd.Timestamp(d).tz_localize(hh.index.tz)
        sel = hh[day == dd]
        if len(sel) < 10:
            continue
        try:
            p_open = sel[sel.index.hour <= 8].iloc[-1]     # ~08:00 ET
            p_pre = sel[sel.index.hour <= 12].iloc[-1]     # last bar before 13:00 ET
            p_post = sel[sel.index.hour <= 14].iloc[-1]    # ~14:00 ET, after the result
            p_stl = sel[sel.index.hour <= 15].iloc[-1]     # ~15:00 ET settlement
        except IndexError:
            continue
        rows.append({"d": d,
                     "morning_bps": np.log(p_pre / p_open) * 1e4,
                     "result_bps": np.log(p_post / p_pre) * 1e4,
                     "tail_bps": np.log(p_stl / p_post) * 1e4})
    ih = pd.DataFrame(rows)
    if len(ih) >= 5:
        print(f"  n events with hourly coverage = {len(ih)}  "
              f"({ih.d.min().date()} -> {ih.d.max().date()})")
        for c, lab in [("morning_bps", "08:00 -> 13:00 ET (concession window)"),
                       ("result_bps", "13:00 -> 14:00 ET (auction result)"),
                       ("tail_bps", "14:00 -> 15:00 ET (settlement tail)")]:
            m, t = lib.hac_t(ih[c].to_numpy())
            print(f"    {lab:42s} mean {m:+7.2f} bps  t {t:+5.2f}")
        print("  -> N is far below any decision threshold; reported for completeness only.")
    else:
        print("  insufficient hourly coverage overlapping the event set.")

    print()
    print("=" * 92)
    print("I — DOSE-RESPONSE FALSIFIER (EXPLORATORY, not in the preregistered ledger)")
    print("=" * 92)
    print("  If the concession is dealer balance-sheet pressure, a BIGGER auction relative to")
    print("  its own history must produce a BIGGER effect. Flat dose-response falsifies the")
    print("  mechanism even when the pooled mean is positive (same logic as L49).")
    a = a10.copy()
    a["size_z"] = (a.offeringAmount.rolling(24, min_periods=8).apply(
        lambda s: (s.iloc[-1] - s.iloc[:-1].mean()) / (s.iloc[:-1].std() + 1e-9), raw=False))
    merged = er.merge(a[["auctionDate", "size_z", "bidToCoverRatio"]],
                      left_on="auction_date", right_on="auctionDate", how="left")
    for var, lab in [("size_z", "auction size z-score (trailing 24)"),
                     ("bidToCoverRatio", "bid-to-cover ratio")]:
        sub = merged.dropna(subset=[var])
        if len(sub) < 40:
            continue
        q = pd.qcut(sub[var], 4, labels=False, duplicates="drop")
        print(f"\n  {lab}  (n={len(sub)})")
        print(f"    {'quartile':10s} {'n':>4s} {'V_bps':>8s} {'PRE_bps':>9s} {'POST_bps':>9s}")
        for qq in sorted(pd.Series(q).dropna().unique()):
            s2 = sub[q == qq]
            print(f"    Q{int(qq)+1:<9d} {len(s2):4d} {s2.v_bps.mean():8.2f} "
                  f"{s2.pre_bps.mean():9.2f} {s2.post_bps.mean():9.2f}")
        r = np.corrcoef(sub[var], sub.pre_bps)[0, 1]
        print(f"    corr({var}, PRE leg) = {r:+.3f}  "
              f"[mechanism predicts POSITIVE: bigger auction -> bigger concession]")

    print()
    print("=" * 92)
    print("J — SENSITIVITY: does the announcement-lag (T-1) filter change the answer?")
    print("=" * 92)
    ev_all, _ = lib.event_positions(px.index, a10.auctionDate, K, M,
                                    require_announced=None, entry_lag_check=False)
    er_all = lib.event_returns(px, ev_all, K, M)
    m1, t1 = lib.hac_t(er.v_bps.to_numpy())
    m2, t2 = lib.hac_t(er_all.v_bps.to_numpy())
    print(f"  announced-at-entry only (PRIMARY) : n={len(er):4d} mean {m1:+6.2f} t {t1:+5.2f}")
    print(f"  all auctions (look-ahead allowed) : n={len(er_all):4d} mean {m2:+6.2f} t {t2:+5.2f}")
    print(f"  -> the T-1 filter drops {len(er_all)-len(er)} events and is NOT what kills the result.")


if __name__ == "__main__":
    main()
