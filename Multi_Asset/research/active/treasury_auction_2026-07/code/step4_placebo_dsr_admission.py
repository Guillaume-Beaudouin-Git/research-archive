"""K2 matched-calendar placebo (L49), K9 DSR with measured std_sr_trials,
K8 marginal admission vs the B1-on-ZN book, and the personal-account economics."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
from scipy import stats

import lib

sys.path.insert(0, str(lib.REPO))
from Portfolio.admission import marginal  # noqa: E402

K, M = 3, 2
N_TRIALS = 16
ACCOUNT_EUR = 13_000.0
EURUSD = 1.08
ZN_POINT_USD = 1_000.0   # 1 price point = $1,000 (100k face)


# ───────────────────────────────────────────── K2 : matched calendar placebo
def matched_placebo(px: pd.DataFrame, ev_dates: pd.Series, blackout: pd.Series,
                    k: int, m: int, n_draws: int = 2000, seed: int = 0) -> dict:
    """For each real event, build a pool of same-weekday / same-day-of-month(+-3) /
    different-year trading days that are >3 trading days from ANY long-end coupon
    auction, then draw complete placebo calendars."""
    idx = px.index
    c = px["close"].to_numpy()
    dow = idx.dayofweek.to_numpy()
    dom = idx.day.to_numpy()
    yr = idx.year.to_numpy()
    ok = blackout.to_numpy()          # True = usable (outside blackout)
    valid = np.zeros(len(idx), dtype=bool)
    valid[k: len(idx) - m - 1] = True
    base = ok & valid

    pools = []
    for d in ev_dates:
        pos = idx.searchsorted(d, side="left")
        if pos >= len(idx) or idx[pos] != d:
            continue
        sel = base & (dow == dow[pos]) & (np.abs(dom - dom[pos]) <= 3) & (yr != yr[pos])
        p = np.flatnonzero(sel)
        if len(p) >= 5:
            pools.append(p)

    rng = np.random.default_rng(seed)
    means = np.empty(n_draws)
    for b in range(n_draws):
        vals = np.empty(len(pools))
        for j, p in enumerate(pools):
            t = p[rng.integers(len(p))]
            pre = -(np.log(c[t - 1]) - np.log(c[t - k])) * 1e4
            post = +(np.log(c[t + m]) - np.log(c[t - 1])) * 1e4
            vals[j] = pre + post
        means[b] = vals.mean()
    return {"n_pools": len(pools), "pool_med": int(np.median([len(p) for p in pools])),
            "means": means}


def blackout_mask(px: pd.DataFrame, auc: pd.DataFrame, terms: list[int],
                  pad: int = 3) -> pd.Series:
    idx = px.index
    bad = np.zeros(len(idx), dtype=bool)
    for d in auc[auc.term.isin(terms)].auctionDate:
        pos = idx.searchsorted(d, side="left")
        lo, hi = max(0, pos - pad), min(len(idx), pos + pad + 1)
        bad[lo:hi] = True
    return pd.Series(~bad, index=idx)


def report_placebo(name: str, real: float, res: dict) -> bool:
    mu = res["means"]
    med, p95, p99 = np.median(mu), np.quantile(mu, .95), np.quantile(mu, .99)
    pct = float((mu >= real).mean())
    verdict = "PASS" if real > p95 else "FAIL (K2)"
    print(f"{name:28s} real {real:+7.2f} | placebo med {med:+6.2f} p95 {p95:+6.2f} "
          f"p99 {p99:+6.2f} | P(placebo>=real) {pct:.3f} | pools {res['n_pools']} "
          f"(median size {res['pool_med']}) -> {verdict}")
    return real > p95


def main() -> None:
    px = lib.load_px("ZN")
    auc = lib.load_auctions()
    a10 = auc[auc.term == 10].sort_values("auctionDate")
    ev, P = lib.event_positions(px.index, a10.auctionDate.reset_index(drop=True), K, M,
                                require_announced=a10.announcementDate.reset_index(drop=True))
    er = lib.event_returns(px, ev, K, M).reset_index(drop=True)
    real = float(er.v_bps.mean())

    print("=" * 100)
    print("K2 — MATCHED CALENDAR PLACEBO (L49): same weekday, day-of-month +-3, different year,")
    print("     >3 trading days from any long-end coupon auction. 2000 full placebo calendars.")
    print("=" * 100)
    bl = blackout_mask(px, auc, [10, 20, 30], pad=3)
    r10 = matched_placebo(px, er.auction_date, bl, K, M)
    k2_primary = report_placebo("10y/ZN PRIMARY", real, r10)

    # the two cells that DID look significant in step3 (both month-end / B1-overlapping)
    for term, sym in [(7, "ZN"), (5, "ZF")]:
        p2 = lib.load_px(sym)
        a2 = auc[auc.term == term].sort_values("auctionDate")
        e2, _ = lib.event_positions(p2.index, a2.auctionDate.reset_index(drop=True), K, M,
                                    require_announced=a2.announcementDate.reset_index(drop=True))
        r2 = lib.event_returns(p2, e2, K, M)
        bl2 = blackout_mask(p2, auc, [2, 5, 7], pad=3)
        res = matched_placebo(p2, r2.auction_date, bl2, K, M)
        report_placebo(f"{term}y/{sym} (month-end)", float(r2.v_bps.mean()), res)

    # ---------------------------------------------------------------- K9 DSR
    print()
    print("=" * 100)
    print("K9 — DEFLATED SHARPE RATIO, std_sr_trials MEASURED (not assumed)")
    print("=" * 100)
    grid = pd.read_pickle(lib.ROOT / "data" / "grid_sr.pkl")
    sr_trials = grid.to_numpy()
    std_trials = float(np.std(sr_trials, ddof=1))
    sr_best = float(np.nanmax(sr_trials))
    sr_primary = lib.ann_sharpe_per_event(er.v_bps.to_numpy(), 12.0)
    n_obs = len(er)
    g = 0.5772156649
    e_max = std_trials * ((1 - g) * stats.norm.ppf(1 - 1 / N_TRIALS)
                          + g * stats.norm.ppf(1 - 1 / (N_TRIALS * np.e)))
    x = er.v_bps.to_numpy()
    sk, ku = float(stats.skew(x)), float(stats.kurtosis(x, fisher=False))
    for label, sr in [("primary (k=3,m=2)", sr_primary), ("best of grid", sr_best)]:
        num = (sr - e_max) * np.sqrt(n_obs - 1)
        den = np.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2)
        print(f"  {label:20s} SR_ann {sr:+.3f}  SR0(E[max]) {e_max:+.3f}  "
              f"DSR {stats.norm.cdf(num/den):.3f}  -> "
              f"{'PASS' if stats.norm.cdf(num/den) >= 0.95 else 'FAIL (K9)'}")
    print(f"  n_trials = {N_TRIALS} (declared) | std_sr_trials = {std_trials:.4f} MEASURED "
          f"across the {len(sr_trials)} grid cells | skew {sk:+.2f} kurt {ku:.2f} | n_events {n_obs}")

    # ---------------------------------------------------------------- K8 admission
    print()
    print("=" * 100)
    print("K8 — MARGINAL ADMISSION vs the existing book (B1 implemented on ZN)")
    print("=" * 100)
    b1 = lib.b1_daily_series(px, 3)
    cand = (P["net"] * px["ret"]).rename("AUCTION").reindex(px.index).fillna(0.0)
    both = pd.concat([b1, cand], axis=1).dropna()
    both = both.loc["2000-09-22":]
    res = marginal.admit(both[["B1"]], both["AUCTION"], scheme="erc",
                         periods_per_year=252.0, n_trials=N_TRIALS,
                         n_boot=4000, mean_block=10.0, seed=7)
    print(res)

    # net-of-cost candidate: charge the S_V cost on the exit day of each event
    for tag, cbps in [("central 3.3bps", lib.COST_CENTRAL_BPS),
                      ("stress  6.1bps", lib.COST_STRESS_BPS)]:
        c_net = cand.copy()
        for t in ev[ev.announced_ok].i_t.astype(int):
            if t + M < len(c_net):
                c_net.iloc[t + M] -= cbps / 1e4
        r2 = marginal.admit(both[["B1"]], c_net.reindex(both.index).fillna(0.0).rename("AUCTION"),
                            scheme="erc", periods_per_year=252.0, n_trials=N_TRIALS,
                            n_boot=4000, mean_block=10.0, seed=7)
        print(f"\n  NET {tag}: verdict {r2.verdict} | dSR {r2.delta_sharpe:+.4f} "
              f"| SR_cand {r2.candidate_sharpe:+.3f} | rho {r2.rho:+.3f} "
              f"| CI [{r2.ci[0]:+.3f},{r2.ci[1]:+.3f}] | min detectable dSR {r2.detectable_delta_sharpe:.3f}")

    # ---------------------------------------------------------------- economics
    print()
    print("=" * 100)
    print("ECONOMICS on a EUR 13k IBKR account, 1 ZN contract (no barrier, no clock)")
    print("=" * 100)
    notional = float(px["close"].iloc[-1]) / 100.0 * 100_000.0
    acct_usd = ACCOUNT_EUR * EURUSD
    for tag, cbps in [("gross", 0.0), ("net central", lib.COST_CENTRAL_BPS),
                      ("net stress", lib.COST_STRESS_BPS)]:
        pnl = (er.v_bps.to_numpy() - cbps) / 1e4 * notional
        mu, sd = pnl.mean(), pnl.std(ddof=1)
        sr = mu / sd * np.sqrt(12.0)
        cum = np.cumsum(pnl)
        dd = lib.max_dd(cum)
        yr_usd = mu * 12.0
        print(f"  {tag:12s} $/event {mu:+7.2f} (sd {sd:7.2f})  SR_ann {sr:+.3f}  "
              f"$/yr {yr_usd:+8.2f} = {yr_usd/acct_usd*100:+.2f}%/yr acct  "
              f"maxDD ${dd:,.0f} = {dd/acct_usd*100:.1f}% acct")
    print(f"  ZN notional ${notional:,.0f} | account ${acct_usd:,.0f} -> "
          f"1 contract = {notional/acct_usd:.1f}x notional leverage (margin ~$1,800 = "
          f"{1800/acct_usd*100:.0f}% of account)")

    # Kelly on the per-event distribution (fractional)
    mu_g = er.v_bps.mean() / 1e4
    sd_g = er.v_bps.std(ddof=1) / 1e4
    f_full = mu_g / sd_g ** 2
    print(f"  full-Kelly notional exposure = mu/sigma^2 = {f_full:.2f}x account "
          f"-> 1/4 Kelly {f_full/4:.2f}x, 1/2 Kelly {f_full/2:.2f}x")
    print(f"  1 contract = {notional/acct_usd:.1f}x  -> "
          f"{'ABOVE full Kelly' if notional/acct_usd > f_full else 'below full Kelly'} "
          f"(granularity, not margin, is the binding constraint)")


if __name__ == "__main__":
    main()
