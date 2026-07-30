"""Primary diagnostics: drift/demean (L25-K6), regimes (L31-K3), window grid,
contract-roll artefact (K7), maturity transfer (ZB/ZF), cost gate (K4)."""
from __future__ import annotations

import numpy as np
import pandas as pd

import lib

K, M = 3, 2


def drift_baseline(px: pd.DataFrame, lo: str, hi: str) -> float:
    r = px.loc[lo:hi, "ret"].dropna()
    return float(r.mean() * 1e4)


def demeaned(er: pd.DataFrame, px: pd.DataFrame, k: int, m: int,
             regime_bounds: tuple[str, str] | None = None) -> pd.DataFrame:
    """Subtract the unconditional ZN drift * n_days from each leg, within regime."""
    out = er.copy()
    if regime_bounds is None:
        d = drift_baseline(px, str(px.index[0].date()), str(px.index[-1].date()))
        out["pre_dm"] = out.pre_bps + d * (k - 1)     # short leg: drift is a headwind
        out["post_dm"] = out.post_bps - d * (m + 1)
    else:
        d = drift_baseline(px, *regime_bounds)
        out["pre_dm"] = out.pre_bps + d * (k - 1)
        out["post_dm"] = out.post_bps - d * (m + 1)
    out["v_dm"] = out.pre_dm + out.post_dm
    return out


def line(label: str, x: np.ndarray, epy: float = 12.0) -> str:
    m, t = lib.hac_t(x)
    p, ci = lib.block_bootstrap_p(x)
    sr = lib.ann_sharpe_per_event(x, epy)
    hit = float((x > 0).mean() * 100)
    return (f"{label:34s} {len(x):5d} {m:9.2f} {t:7.2f} {p:8.4f} "
            f"[{ci[0]:7.2f},{ci[1]:7.2f}] {sr:7.2f} {hit:6.1f}%")


HDR = (f"{'cell':34s} {'n':>5s} {'mean_bps':>9s} {'t_HAC':>7s} {'p_blk':>8s} "
       f"{'95% CI bps':>18s} {'SR_ann':>7s} {'hit':>7s}")


def main() -> None:
    px = lib.load_px("ZN")
    auc = lib.load_auctions()
    a10 = auc[auc.term == 10].sort_values("auctionDate")

    ev, P = lib.event_positions(px.index, a10.auctionDate.reset_index(drop=True), K, M,
                                require_announced=a10.announcementDate.reset_index(drop=True))
    er = lib.event_returns(px, ev, K, M).reset_index(drop=True)

    d_all = drift_baseline(px, "2000-01-01", "2026-12-31")
    print(f"ZN unconditional drift 2000-2026 : {d_all:+.3f} bps/day "
          f"({d_all*252/100:+.2f} %/yr)   n_days={len(px)}")
    print(f"ZN daily vol                      : {px['ret'].std()*1e4:.1f} bps")
    print()

    # ---------------------------------------------------------------- K6 / L25
    print("=" * 108)
    print("CELLS 1-3 — PRIMARY 10y/ZN, RAW vs DEMEANED (two-sided test, L25 / K6)")
    print("=" * 108)
    print(HDR)
    dm = demeaned(er, px, K, M)
    print(line("1  S_V  raw", er.v_bps.to_numpy()))
    print(line("2  PRE (short) raw", er.pre_bps.to_numpy()))
    print(line("3  POST (long) raw", er.post_bps.to_numpy()))
    print(line("   S_V  demeaned", dm.v_dm.to_numpy()))
    print(line("   PRE (short) demeaned", dm.pre_dm.to_numpy()))
    print(line("   POST (long) demeaned", dm.post_dm.to_numpy()))
    print()
    print(f"   drift-implied POST leg  = {d_all*(M+1):+.2f} bps   "
          f"(measured POST = {er.post_bps.mean():+.2f} bps)")
    print(f"   drift-implied PRE  leg  = {-d_all*(K-1):+.2f} bps   "
          f"(measured PRE  = {er.pre_bps.mean():+.2f} bps)")

    # ---------------------------------------------------------------- K3 / L31
    print()
    print("=" * 108)
    print("CELLS 8-10 — REGIME SPLIT (L31 / K3)")
    print("=" * 108)
    print(HDR)
    for name, (lo, hi) in lib.REGIMES.items():
        sub = er[(er.auction_date >= lo) & (er.auction_date <= hi)]
        if len(sub) < 10:
            continue
        subdm = demeaned(sub, px, K, M, (lo, hi))
        print(line(f"   {name} raw", sub.v_bps.to_numpy()))
        print(line(f"   {name} demeaned", subdm.v_dm.to_numpy()))
        print(f"{'':34s} {'':5s} drift {drift_baseline(px, lo, hi):+.3f} bps/d | "
              f"PRE {sub.pre_bps.mean():+6.2f} (t {lib.hac_t(sub.pre_bps.to_numpy())[1]:+.2f}) | "
              f"POST {sub.post_bps.mean():+6.2f} (t {lib.hac_t(sub.post_bps.to_numpy())[1]:+.2f})")

    # ---------------------------------------------------------------- K7 roll
    print()
    print("=" * 108)
    print("K7 — CONTRACT-ROLL ARTEFACT  (ZN rolls late Feb/May/Aug/Nov)")
    print("=" * 108)
    print(HDR)
    ad = er.auction_date
    roll_month = ad.dt.month.isin([2, 5, 8, 11])
    roll_win = roll_month & (ad.dt.day >= 18)
    print(line("   S_V excl. roll windows", er[~roll_win].v_bps.to_numpy()))
    print(line("   S_V inside roll windows", er[roll_win].v_bps.to_numpy()))
    print(f"   events inside roll windows: {int(roll_win.sum())} / {len(er)}")

    # ---------------------------------------------------------------- grid
    print()
    print("=" * 108)
    print("CELLS 11-16 — WINDOW ROBUSTNESS GRID (k = PRE entry offset, m = POST exit offset)")
    print("=" * 108)
    print(f"{'k':>3s} {'m':>3s} {'n':>5s} {'V_bps':>8s} {'t_V':>6s} "
          f"{'PRE_bps':>8s} {'t_PRE':>6s} {'POST_bps':>9s} {'t_POST':>7s}")
    grid_sr = {}
    for k in [2, 3, 4, 5]:
        for m in [1, 2, 3, 4]:
            e2, _ = lib.event_positions(px.index, a10.auctionDate.reset_index(drop=True), k, m,
                                        require_announced=a10.announcementDate.reset_index(drop=True))
            r2 = lib.event_returns(px, e2, k, m)
            if len(r2) < 30:
                continue
            mv, tv = lib.hac_t(r2.v_bps.to_numpy())
            mp, tp = lib.hac_t(r2.pre_bps.to_numpy())
            mo, to = lib.hac_t(r2.post_bps.to_numpy())
            star = " *" if (k, m) == (K, M) else ""
            print(f"{k:3d} {m:3d} {len(r2):5d} {mv:8.2f} {tv:6.2f} {mp:8.2f} {tp:6.2f} "
                  f"{mo:9.2f} {to:7.2f}{star}")
            grid_sr[(k, m)] = lib.ann_sharpe_per_event(r2.v_bps.to_numpy(), 12.0)
    pd.Series(grid_sr).to_pickle(lib.ROOT / "data" / "grid_sr.pkl")

    # ---------------------------------------------------------------- maturity
    print()
    print("=" * 108)
    print("CELLS 5-7 — MATURITY TRANSFER  (auctioned sector traded in its own contract)")
    print("=" * 108)
    print(HDR)
    for sym, terms, label in [("ZB", [30], "6  30y auctions on ZB"),
                              ("ZF", [3], "7  3y auctions on ZF"),
                              ("ZF", [5], "   5y auctions on ZF (exploratory)"),
                              ("ZN", [7], "   7y auctions on ZN (exploratory)")]:
        p2 = lib.load_px(sym)
        a2 = auc[auc.term.isin(terms)].sort_values("auctionDate")
        e2, _ = lib.event_positions(p2.index, a2.auctionDate.reset_index(drop=True), K, M,
                                    require_announced=a2.announcementDate.reset_index(drop=True))
        r2 = lib.event_returns(p2, e2, K, M)
        if len(r2) < 20:
            continue
        print(line(label, r2.v_bps.to_numpy()))
        print(f"{'':34s} {'':5s} PRE {r2.pre_bps.mean():+6.2f} "
              f"(t {lib.hac_t(r2.pre_bps.to_numpy())[1]:+.2f}) | "
              f"POST {r2.post_bps.mean():+6.2f} (t {lib.hac_t(r2.post_bps.to_numpy())[1]:+.2f})")

    # ---------------------------------------------------------------- K4 cost
    print()
    print("=" * 108)
    print("K4 — COST GATE")
    print("=" * 108)
    g = er.v_bps.mean()
    print(f"gross S_V           : {g:+.2f} bps/event")
    print(f"cost central        : {lib.COST_CENTRAL_BPS:.2f} bps/event  -> "
          f"net {g - lib.COST_CENTRAL_BPS:+.2f} bps   gate(3x)={3*lib.COST_CENTRAL_BPS:.1f} "
          f"-> {'PASS' if g >= 3*lib.COST_CENTRAL_BPS else 'FAIL'}")
    print(f"cost stress         : {lib.COST_STRESS_BPS:.2f} bps/event  -> "
          f"net {g - lib.COST_STRESS_BPS:+.2f} bps   gate(3x)={3*lib.COST_STRESS_BPS:.1f} "
          f"-> {'PASS' if g >= 3*lib.COST_STRESS_BPS else 'FAIL'}")

    er.to_parquet(lib.ROOT / "data" / "events_10y_ZN.parquet")


if __name__ == "__main__":
    main()
