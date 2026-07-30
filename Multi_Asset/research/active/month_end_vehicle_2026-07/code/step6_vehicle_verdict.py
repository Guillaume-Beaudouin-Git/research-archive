"""Step 6 — vehicle verdict: propfirm funded EV vs a direct personal futures account.

Passing a challenge is not the objective; monetising the sleeve is. This step
prices both ends: the funded phase after a pass, and the counterfactual of simply
trading ZN in the personal IBKR account the book already has.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from step5_propfirm_sim import Firm, event_daily_matrix, simulate

BASE = pathlib.Path(__file__).resolve().parent.parent
BPS = 1e4


def funded_phase(rets: np.ndarray, n_ctr: int, dpb: float, rt: float, n_rt: int,
                 dd: float, dd_type: str, account: float, n_paths: int = 40000,
                 months: int = 24, block: int = 3, seed: int = 5) -> dict:
    """Expected gross P&L over `months` of funded trading, stopping at a bust."""
    rng = np.random.default_rng(seed)
    n_ev = len(rets)
    nb = int(np.ceil(months / block))
    st = rng.integers(0, n_ev, size=(n_paths, nb))
    idx = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(n_paths, -1)[:, :months] % n_ev
    pnl = rets[idx] * BPS * dpb * n_ctr
    cost = n_rt * rt * n_ctr

    eq = np.full(n_paths, account)
    peak = eq.copy()
    alive = np.ones(n_paths, bool)
    banked = np.zeros(n_paths)
    for m in range(months):
        step = pnl[:, m, :].copy()
        step[:, 0] -= cost
        for d in range(3):
            eq = np.where(alive, eq + step[:, d], eq)
            floor = (account - dd) if dd_type == "static" else (peak - dd)
            bust = alive & (eq <= floor)
            alive &= ~bust
            if dd_type == "eod_trail":
                peak = np.where(alive, np.maximum(peak, eq), np.minimum(peak, account + dd + 100))
                peak = np.minimum(peak, account + dd + 100)
        banked = np.where(alive, eq - account, banked)
    return dict(p_alive_24m=float(alive.mean()), mean_profit_24m=float(banked.mean()),
                med_profit_24m=float(np.median(banked)))


if __name__ == "__main__":
    cont, flat, px = event_daily_matrix("ZNF")
    dpb = px.mean() / 100 * 100_000 * 1e-4
    rt = 19.0
    tot = cont.sum(1) * BPS          # bps per event, continuous hold

    print("=" * 78)
    print("6a — the sleeve as a standalone series (per ZN contract, no leverage games)")
    print("=" * 78)
    gross = tot.mean() * dpb
    net = gross - rt
    sd = tot.std(ddof=1) * dpb
    # 12 events/yr -> annualise by sqrt(12), NOT sqrt(252) (L47)
    print(f"  per event : gross ${gross:6.2f}  cost ${rt:5.2f}  net ${net:6.2f}  sd ${sd:7.2f}")
    print(f"  per year  : net ${net*12:8.2f}  sd ${sd*np.sqrt(12):8.2f}  "
          f"Sharpe(net, sqrt(12)) = {net*12/(sd*np.sqrt(12)):.3f}")
    print(f"  worst event ${tot.min()*dpb:,.0f} | 5th pct ${np.percentile(tot,5)*dpb:,.0f} "
          f"| hit {(tot>0).mean():.1%}")
    print(f"  cost drag = {rt/gross:.1%} of gross  (edge is 11x the round trip)")

    print("\n" + "=" * 78)
    print("6b — funded phase, 24 months, best size from step 5")
    print("=" * 78)
    rows = []
    for lab, acct, dd, ddt, n, rets, nrt, split in [
        ("MFFU Flex 50k  1 ZN (static $2,000)", 50_000, 2_000, "static", 1, cont, 1, 0.80),
        ("MFFU Flex 50k  2 ZN (static $2,000)", 50_000, 2_000, "static", 2, cont, 1, 0.80),
        ("MFFU Builder 50k 1 ZN (trail $2,000)", 50_000, 2_000, "eod_trail", 1, cont, 1, 0.80),
        ("Apex 4.0 100k  2 ZN (trail $3,000, flat)", 100_000, 3_000, "eod_trail", 2, flat, 3, 0.90),
    ]:
        r = funded_phase(rets, n, dpb, rt, nrt, dd, ddt, acct)
        r.update(vehicle=lab, split_profit_24m=r["mean_profit_24m"] * split)
        rows.append(r)
    print(pd.DataFrame(rows)[["vehicle", "p_alive_24m", "mean_profit_24m",
                              "med_profit_24m", "split_profit_24m"]]
          .to_string(index=False, float_format=lambda v: f"{v:10.1f}"))

    print("\n" + "=" * 78)
    print("6c — counterfactual: the SAME trade in the personal futures account")
    print("=" * 78)
    for cap_eur, n in ((12_000, 1), (12_000, 2), (50_000, 4)):
        cap = cap_eur * 1.08     # EUR -> USD, rough
        ann = net * 12 * n
        annsd = sd * np.sqrt(12) * n
        worst = tot.min() * dpb * n
        print(f"  capital ${cap:>8,.0f}  {n} ZN | margin ~${1800*n:,} ({1800*n/cap:.0%} of capital) "
              f"| exp ${ann:7,.0f}/yr ({ann/cap:+5.1%}) | sd ${annsd:6,.0f} "
              f"| worst event ${worst:7,.0f} ({worst/cap:+5.1%}) | 100% of P&L")

    print("\n  propfirm equivalent, best cell (MFFU Flex 50k, 1 ZN):")
    print("    cost to pass  ~$639 in subscriptions, median 11 months of waiting")
    print("    then 80% of the same 1-contract P&L, under a $2,000 kill barrier")
    print("    -> the propfirm sells LEVERAGE; 1 ZN needs ~$1,800 of margin, which the")
    print("       personal account already has. Nothing is being bought.")
