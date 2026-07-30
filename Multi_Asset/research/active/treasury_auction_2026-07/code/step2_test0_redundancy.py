"""TEST 0 (PREREGISTRATION section 2) — redundancy with B1, run BEFORE anything else.

T0.a calendar overlap of each auction cluster with the B1 window
T0.b return correlation of the two sleeves
T0.c auction effect with B1-overlapping events REMOVED
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import lib

K, M = 3, 2

CLUSTERS = {
    "10y (PRIMARY)": [10],
    "month-end 2/5/7": [2, 5, 7],
    "mid-month 3/10/30": [3, 10, 30],
    "20y": [20],
    "ALL coupon": [2, 3, 5, 7, 10, 20, 30],
}


def main() -> None:
    px = lib.load_px("ZN")
    auc = lib.load_auctions()
    b1_act = lib.b1_active_days(px.index, 3)
    b1 = lib.b1_daily_series(px, 3)

    print("=" * 78)
    print("T0.a — CALENDAR OVERLAP WITH THE B1 WINDOW (last 3 trading days of month)")
    print("=" * 78)
    print(f"{'cluster':22s} {'n_auc':>6s} {'n_used':>7s} {'ann_drop':>9s} "
          f"{'%evt touching B1':>17s} {'%pos-days in B1':>16s}")

    ev_store = {}
    for name, terms in CLUSTERS.items():
        a = auc[auc.term.isin(terms)].sort_values("auctionDate")
        ev, P = lib.event_positions(px.index, a.auctionDate.reset_index(drop=True),
                                    k=K, m=M,
                                    require_announced=a.announcementDate.reset_index(drop=True))
        used = ev[ev.announced_ok]
        b1arr = b1_act.to_numpy()
        touch, days_tot, days_b1 = [], 0, 0
        for t in used.i_t.astype(int):
            w = np.arange(t - K + 1, t + M + 1)
            w = w[(w >= 0) & (w < len(b1arr))]
            n_b1 = int(b1arr[w].sum())
            touch.append(n_b1 > 0)
            days_tot += len(w)
            days_b1 += n_b1
        pct_evt = 100.0 * np.mean(touch) if touch else np.nan
        pct_day = 100.0 * days_b1 / days_tot if days_tot else np.nan
        print(f"{name:22s} {len(a):6d} {len(used):7d} {len(ev)-len(used):9d} "
              f"{pct_evt:16.1f}% {pct_day:15.1f}%")
        ev_store[name] = (a, ev, P, np.array(touch))

    print()
    print("=" * 78)
    print("T0.b — RETURN CORRELATION, auction sleeve vs B1 (daily, ZN)")
    print("=" * 78)
    print(f"{'cluster':22s} {'rho_full':>9s} {'rho_active_union':>17s} {'n_full':>7s} {'n_union':>8s}")
    for name, (a, ev, P, touch) in ev_store.items():
        s = (P["net"] * px["ret"]).rename("AUC")
        d = pd.concat([b1, s], axis=1).dropna()
        rho_full = float(d["B1"].corr(d["AUC"]))
        active = (b1_act.reindex(d.index).fillna(False)) | (P["net"].reindex(d.index).fillna(0) != 0)
        du = d[active]
        rho_u = float(du["B1"].corr(du["AUC"]))
        print(f"{name:22s} {rho_full:9.3f} {rho_u:17.3f} {len(d):7d} {len(du):8d}")

    print()
    print("=" * 78)
    print("T0.c — AUCTION EFFECT, RAW vs B1-OVERLAP REMOVED  (ZN, S_V = short PRE + long POST)")
    print("=" * 78)
    print(f"{'cluster':22s} {'set':8s} {'n':>5s} {'mean_bps':>9s} {'t_HAC':>7s} "
          f"{'p_block':>8s} {'pre_bps':>8s} {'t_pre':>6s} {'post_bps':>9s} {'t_post':>7s}")
    for name, (a, ev, P, touch) in ev_store.items():
        er = lib.event_returns(px, ev, k=K, m=M)
        if er.empty:
            continue
        er = er.reset_index(drop=True)
        er["touch_b1"] = touch
        for label, sub in [("raw", er), ("ex-B1", er[~er.touch_b1])]:
            if len(sub) < 10:
                continue
            mv, tv = lib.hac_t(sub.v_bps.to_numpy())
            pv, _ = lib.block_bootstrap_p(sub.v_bps.to_numpy())
            mp, tp = lib.hac_t(sub.pre_bps.to_numpy())
            mo, to = lib.hac_t(sub.post_bps.to_numpy())
            print(f"{name:22s} {label:8s} {len(sub):5d} {mv:9.2f} {tv:7.2f} "
                  f"{pv:8.4f} {mp:8.2f} {tp:6.2f} {mo:9.2f} {to:7.2f}")

    a, ev, P, touch = ev_store["10y (PRIMARY)"]
    er = lib.event_returns(px, ev, k=K, m=M).reset_index(drop=True)
    er["touch_b1"] = touch
    er.to_parquet(lib.ROOT / "data" / "events_10y_ZN.parquet")
    print(f"\nsaved primary event table n={len(er)}")


if __name__ == "__main__":
    main()
