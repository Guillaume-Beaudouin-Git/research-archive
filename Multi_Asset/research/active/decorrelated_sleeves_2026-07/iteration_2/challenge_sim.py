"""FTMO 2-step challenge Monte-Carlo (post-2024 rules: NO time limit; +10% / +5% targets;
5% daily loss & 10% max loss, equity-based incl. intraday excursion & swaps; min 4 trading days).
Block-bootstrap of a strategy's daily returns; sweep leverage L and intraday-excursion multiplier m.

Usage: python3 challenge_sim.py <daily_returns.csv> [label]
The CSV has a 'ret' column of daily strategy returns (fraction), one sizing unit (L=1)."""
from __future__ import annotations
import sys, json
import numpy as np, pandas as pd

INITIAL = 1.0
DAILY_LIM, TOTAL_LIM = 0.05, 0.10          # of initial
T1, T2 = 0.10, 0.05                        # phase targets
MAX_DAYS = 600                             # patience cap per phase (no real FTMO limit)
BLOCK = 10


def boot_path(pool, n, rng):
    out = np.empty(n); i = 0
    while i < n:
        s = rng.integers(0, len(pool) - BLOCK)
        k = min(BLOCK, n - i); out[i:i + k] = pool[s:s + k]; i += k
    return out


def run_phase(pool, target, L, m, rng):
    path = boot_path(pool, MAX_DAYS, rng) * L
    eq = INITIAL; day_start = INITIAL; tdays = 0
    for d in range(MAX_DAYS):
        r = path[d]
        if r != 0: tdays += 1
        intraday_low = eq * (1 + m * min(r, 0.0))            # conservative intraday excursion
        if intraday_low <= INITIAL - TOTAL_LIM: return "breach_total", d
        if intraday_low <= day_start - DAILY_LIM: return "breach_daily", d
        eq *= (1 + r)
        if eq >= INITIAL + target and tdays >= 4: return "pass", d
        day_start = eq
    return "timeout", MAX_DAYS


def simulate(pool, L, m, n=4000, seed=11):
    rng = np.random.default_rng(seed)
    p1 = [run_phase(pool, T1, L, m, rng) for _ in range(n)]
    pass1 = np.mean([r[0] == "pass" for r in p1])
    days1 = np.median([r[1] for r in p1 if r[0] == "pass"]) if pass1 > 0 else np.nan
    # phase 2 conditional on phase-1 pass (fresh account)
    p2 = [run_phase(pool, T2, L, m, rng) for _ in range(n)]
    pass2 = np.mean([r[0] == "pass" for r in p2])
    breach1 = np.mean([r[0].startswith("breach") for r in p1])
    return dict(L=L, m=m, p_pass1=round(float(pass1), 3), p_pass2=round(float(pass2), 3),
                p_pass_both=round(float(pass1 * pass2), 3), p_breach_phase1=round(float(breach1), 3),
                median_days_pass1=None if np.isnan(days1) else int(days1))


def main():
    path = sys.argv[1]; label = sys.argv[2] if len(sys.argv) > 2 else path
    r = pd.read_csv(path)["ret"].dropna().values
    print(f"# FTMO 2-step challenge MC — {label}  (n_days={len(r)}, ann_vol={r.std()*np.sqrt(252):.1%}, "
          f"worst_day={r.min():.1%})")
    rows = []
    for L in [1.0, 1.25, 1.5, 2.0]:
        for m in [1.0, 1.4]:
            rows.append(simulate(r, L, m))
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    out = path.rsplit("/", 1)[0] + "/challenge_mc.json"
    json.dump(df.to_dict("records"), open(out, "w"), indent=2)
    best = df.loc[df.p_pass_both.idxmax()]
    print(f"\nBEST: L={best.L} m={best.m} -> P(pass both)={best.p_pass_both}, "
          f"P(breach phase1)={best.p_breach_phase1}, median days phase1={best.median_days_pass1}")


if __name__ == "__main__":
    main()
