"""Step 5 — can a futures-propfirm account actually MONETISE the month-end sleeve?

Portfolio/admission/barrier.py is not reusable here: it hard-codes an FTMO 2-phase
%-of-balance contract with a mandatory daily stop (``daily_stop`` must be > 0),
whereas futures firms run a 1-phase, dollar-denominated, no-daily-loss-limit
contract. So this is a bespoke first-passage engine with the same philosophy:
paths, not moments; block-bootstrapped from the real event distribution.

The sleeve fires ~12x/year, 3 trading days each. Between events the account is
flat, so calendar burns without approaching the target -- exactly the regime
where a monthly subscription bites.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / "data"
BPS = 1e4


def event_daily_matrix(tk: str, k: int = 3) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(n_events, k) matrices of daily log returns: continuous-hold and daily-flat,
    plus the per-event average settle price."""
    df = pd.read_parquet(DATA / f"daily_{tk}.parquet")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df.sort_index()
    lc, lo = np.log(df["Close"]), np.log(df["Open"])
    de = pd.Series(0, index=df.index).groupby(df.index.to_period("M")).cumcount(ascending=False) + 1
    t = pd.DataFrame(dict(cc=lc.diff(), held=lc - lo, px=df["Close"],
                          per=df.index.to_period("M")))[(de <= k).values]
    cont, flat, px = [], [], []
    for p, g in t.groupby("per"):
        if len(g) != k or g[["cc", "held"]].isna().any().any():
            continue
        cont.append(g["cc"].values)
        flat.append(g["held"].values)
        px.append(g["px"].mean())
    return np.array(cont), np.array(flat), np.array(px)


@dataclass(frozen=True)
class Firm:
    name: str
    account: float
    target: float
    dd: float
    dd_type: str          # "static" | "eod_trail"
    max_contracts: int
    monthly_fee: float
    allows_overnight: bool
    n_roundtrips: int     # per 3-day event
    split: float


def simulate(returns: np.ndarray, px: np.ndarray, firm: Firm, n_ctr: int,
             dollars_per_bp: float, rt_cost: float, n_paths: int = 40000,
             max_months: int = 36, block: int = 3, seed: int = 3) -> dict:
    """First-passage MC. Equity marked at each of the 3 event EODs."""
    rng = np.random.default_rng(seed)
    n_ev = len(returns)
    nb = int(np.ceil(max_months / block))
    st = rng.integers(0, n_ev, size=(n_paths, nb))
    idx = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(n_paths, -1)[:, :max_months] % n_ev

    # dollar P&L per contract per event-day, using the sample's own price level
    pnl = returns[idx] * BPS * dollars_per_bp * n_ctr           # (paths, months, 3)
    cost = firm.n_roundtrips * rt_cost * n_ctr

    eq = np.full(n_paths, firm.account)
    peak = eq.copy()
    alive = np.ones(n_paths, bool)
    passed = np.zeros(n_paths, bool)
    months = np.full(n_paths, max_months, int)

    for m in range(max_months):
        step = pnl[:, m, :].copy()
        step[:, 0] -= cost                       # charge the round trip up front
        for d in range(3):
            eq = np.where(alive, eq + step[:, d], eq)
            floor = (firm.account - firm.dd) if firm.dd_type == "static" else (peak - firm.dd)
            bust = alive & (eq <= floor)
            alive &= ~bust
            months = np.where(bust & (months == max_months), m + 1, months)
            if firm.dd_type == "eod_trail":
                peak = np.where(alive, np.maximum(peak, eq), peak)
                # most futures firms stop trailing once the floor reaches start+buffer
                peak = np.minimum(peak, firm.account + firm.dd + 100)
        win = alive & ~passed & (eq >= firm.account + firm.target)
        months = np.where(win, m + 1, months)
        passed |= win
        alive &= ~win
        if not alive.any():
            break

    p_pass = passed.mean()
    mm = months[passed]
    fee = months * firm.monthly_fee
    return dict(n_ctr=n_ctr, p_pass=float(p_pass),
                p_bust=float((~passed & ~alive).mean()),
                p_timeout=float(alive.mean()),
                med_months_pass=float(np.median(mm)) if len(mm) else np.nan,
                mean_fee=float(fee.mean()),
                ev_eval=float(p_pass * firm.target * 0 - fee.mean()))  # eval itself pays nothing


if __name__ == "__main__":
    cont, flat, px = event_daily_matrix("ZNF")
    print(f"ZN events: n={len(cont)}  mean total={cont.sum(1).mean()*BPS:+.2f}bps  "
          f"mean held={flat.sum(1).mean()*BPS:+.2f}bps")
    px_mean = px.mean()
    dpb_zn = px_mean / 100 * 100_000 * 1e-4       # $ per bp of price return, 1 ZN
    dpb_micro = 10.0 / 6.4                         # 10Y micro yield future, DV01-converted
    print(f"  $ per bp per contract: ZN ${dpb_zn:.2f} | 10Y micro yield ${dpb_micro:.2f}")

    firms = [
        Firm("MFFU Builder 50k (EOD trail $2,000, overnight OK)", 50_000, 3_000, 2_000,
             "eod_trail", 4, 99, True, 1, 0.80),
        Firm("MFFU Flex 50k  (EOD STATIC $2,000, overnight OK)", 50_000, 3_000, 2_000,
             "static", 10, 49, True, 1, 0.80),
        Firm("MFFU Flex 25k  (EOD STATIC $1,000, overnight OK)", 25_000, 1_500, 1_000,
             "static", 5, 39, True, 1, 0.80),
        Firm("Apex 4.0 100k  (EOD trail $3,000, daily-flat)", 100_000, 6_000, 3_000,
             "eod_trail", 20, 85, False, 3, 0.90),
        Firm("Topstep 150k   (EOD trail $4,500, daily-flat)", 150_000, 9_000, 4_500,
             "eod_trail", 15, 375, False, 3, 0.90),
    ]

    for firm in firms:
        rets = cont if firm.allows_overnight else flat
        print("\n" + "=" * 78)
        print(f"{firm.name}   target ${firm.target:,.0f} | DD ${firm.dd:,.0f} {firm.dd_type} "
              f"| max {firm.max_contracts} ctr | ${firm.monthly_fee}/mo")
        print("=" * 78)
        for instr, dpb, rt, cap in (("ZN", dpb_zn, 19.0, firm.max_contracts),
                                     ("10Y micro", dpb_micro, 6.6, firm.max_contracts * 10)):
            rows = []
            sizes = sorted({max(1, int(round(s))) for s in
                            np.unique(np.geomspace(1, cap, 7))})
            for n in sizes:
                r = simulate(rets, px, firm, n, dpb, rt)
                sd = rets.sum(1).std(ddof=1) * BPS * dpb * n
                worst = rets.sum(1).min() * BPS * dpb * n
                r.update(sd_evt=sd, worst_evt=worst,
                         mean_evt=rets.sum(1).mean() * BPS * dpb * n - firm.n_roundtrips * rt * n)
                rows.append(r)
            out = pd.DataFrame(rows)[["n_ctr", "mean_evt", "sd_evt", "worst_evt",
                                      "p_pass", "p_bust", "p_timeout",
                                      "med_months_pass", "mean_fee"]]
            print(f"\n  -- {instr} --")
            print(out.to_string(index=False, float_format=lambda v: f"{v:9.2f}"))
