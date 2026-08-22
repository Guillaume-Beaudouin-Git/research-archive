"""
ftmo_sim.py — FTMO Challenge as a first-passage / barrier-option problem.

FTMO $10k Challenge rules modelled (verified against ftmo.com, 2026):
    start            = $10,000
    profit target    = +10%  -> equity >= $11,000   (and >= 4 trading days)
    max daily loss   = 5% of initial = $500, measured from each day's
                       starting balance (floor_day = day_start - 500)
    max overall loss = 10% of initial -> static equity floor $9,000
    min trading days = 4
    time             = no hard limit; we cap at 40 trading days (~2 months)

Because the underlying per-trade expectancy is ~0 (slightly negative) after
costs, passing is NOT an alpha problem. It is the probability that a (near-)
driftless equity process hits the +$1,000 barrier before the -$1,000 / -$500
barriers within the time cap. Bet size is the key control variable:
    too small -> can't reach +10% in time (timeout)
    too large -> breach the 5% daily limit
There is an interior optimum (~0.75% risk/trade for this trade distribution).
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def simulate(
    r_pool: np.ndarray,
    risk_per_trade: float,
    n_paths: int = 30_000,
    trades_per_day: int = 5,
    max_days: int = 40,
    start: float = 10_000.0,
    target: float = 11_000.0,
    total_floor: float = 9_000.0,
    daily_loss: float = 500.0,
    min_trading_days: int = 4,
    seed: int = 42,
) -> dict:
    """
    Monte-Carlo the challenge by bootstrapping trade R-multiples.

    Each trade risks `risk_per_trade` of *current* equity; its P&L is
    risk_per_trade * equity * R, with R drawn iid from `r_pool` (preserving the
    empirical skew). Barriers are checked after every trade.

    NOTE (conservative caveat): FTMO checks *floating* equity continuously; we
    check only at trade close, so the true daily-breach rate is >= ours and the
    true pass rate is <= ours.
    """
    rng = np.random.default_rng(seed)
    eq = np.full(n_paths, start)
    status = np.zeros(n_paths, dtype=int)     # 0 live, 1 pass, 2 fail-daily, 3 fail-total
    tdays = np.zeros(n_paths, dtype=int)
    days_to_pass = np.zeros(n_paths, dtype=int)

    for d in range(max_days):
        day_start = eq.copy()
        traded = np.zeros(n_paths, dtype=bool)
        for _ in range(trades_per_day):
            live = status == 0
            if not live.any():
                break
            r = r_pool[rng.integers(0, len(r_pool), n_paths)]
            eq = np.where(live, eq + risk_per_trade * eq * r, eq)
            traded |= live
            total_breach = live & (eq < total_floor)
            daily_breach = live & (eq < day_start - daily_loss)
            status = np.where(total_breach, 3, status)
            status = np.where(daily_breach & (status == 0), 2, status)
        tdays += traded.astype(int)
        passed = (status == 0) & (eq >= target) & (tdays >= min_trading_days)
        days_to_pass = np.where(passed & (days_to_pass == 0), d + 1, days_to_pass)
        status = np.where(passed, 1, status)
        if (status == 0).sum() == 0:
            break

    return {
        "risk": risk_per_trade,
        "pass_rate": float((status == 1).mean()),
        "fail_daily": float((status == 2).mean()),
        "fail_total": float((status == 3).mean()),
        "timeout": float((status == 0).mean()),
        "median_days_to_pass": int(np.median(days_to_pass[status == 1]))
        if (status == 1).any() else None,
    }


def optimise_risk(r_pool: np.ndarray, grid=None, **kw) -> pd.DataFrame:
    """Sweep risk-per-trade and return the outcome table (find the optimum)."""
    if grid is None:
        grid = [0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02, 0.03, 0.05]
    return pd.DataFrame([simulate(r_pool, r, **kw) for r in grid])


def reattempt_table(p: float, n=(1, 2, 3, 5, 10)) -> pd.DataFrame:
    """Cumulative pass probability given the cheap re-attempt option."""
    return pd.DataFrame({"attempts": n,
                         "P(pass by n)": [1 - (1 - p) ** k for k in n]})


if __name__ == "__main__":
    from strategy import r_multiples
    R = r_multiples().values
    print(f"Pooled R: mean={R.mean():+.3f}  skew={pd.Series(R).skew():.2f}  "
          f"win%={100*(R>0).mean():.0f}")
    tbl = optimise_risk(R)
    print(tbl.to_string(index=False))
    p = tbl["pass_rate"].max()
    print(f"\nOptimal per-attempt pass ~ {p*100:.1f}%")
    print(reattempt_table(p).to_string(index=False))
