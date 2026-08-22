"""ORB V2+E7 — Step 3: cost sensitivity sweep + worst-year stress.

The 0.4 bps assumption is a HIGH-CASE bound (calm-session measurement).
Real ORB entry is at the open (15:30 Paris) where spread is widest.
This script shows how p(funded) collapses as cost rises from 0.4 → 6 bps,
to make the verdict honest about what 0.4 bps means.

Also: stress under the worst regime (2015) — pre-register the risk.
"""
import numpy as np
import pandas as pd

LEDGER = "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/nq_v2_trades.parquet"
E7_LIFT_R = 0.015
ACCOUNT_INIT = 10000.0
DLL_PCT = 0.05
MAX_TOTAL_PCT = 0.10
TARGET_P1 = 0.10
TARGET_P2 = 0.05
BLOCK_SIZE = 21
N_PATHS = 12000
MAX_STEPS = 252 * 5
RNG_SEED = 17

df = pd.read_parquet(LEDGER).reset_index()
r_g  = df["r_gross"].astype(float).values
r_1  = df["r_1 bps RT (aggressive)"].astype(float).values
r_2  = df["r_2 bps RT (median)"].astype(float).values
cost_unit = r_1 - r_2  # per 1 bps R cost per trade

def r_at_cost(c_bps):
    """Per-trade r_realized at cost c bps with V2+E7 lift."""
    # r_c = r_2 + (2 - c) × cost_unit
    return r_2 + (2.0 - c_bps) * cost_unit + E7_LIFT_R


def generate_bootstrap(samples, n_paths, max_steps, block_size, rng):
    L = len(samples)
    n_blocks = (max_steps + block_size - 1) // block_size
    starts = rng.integers(0, L - block_size + 1, size=(n_paths, n_blocks))
    out = np.empty((n_paths, n_blocks * block_size), dtype=np.float64)
    for k in range(block_size):
        out[:, k::block_size] = samples[starts + k]
    return out[:, :max_steps]


def simulate_phase(boot, sizing_pct, target_pct):
    n_paths, max_steps = boot.shape
    risk_dollar = ACCOUNT_INIT * sizing_pct
    pnl = boot * risk_dollar
    eq = ACCOUNT_INIT + np.cumsum(pnl, axis=1)
    midnight = np.concatenate([np.full((n_paths, 1), ACCOUNT_INIT), eq[:, :-1]], axis=1)
    dll_breach = pnl <= -DLL_PCT * midnight
    floor = ACCOUNT_INIT * (1 - MAX_TOTAL_PCT)
    target = ACCOUNT_INIT * (1 + target_pct)
    floor_breach = eq <= floor
    target_hit = eq >= target
    bust_step = np.where(dll_breach | floor_breach, np.arange(max_steps), max_steps + 1)
    bust_first = bust_step.min(axis=1)
    pass_step = np.where(target_hit, np.arange(max_steps), max_steps + 1)
    pass_first = pass_step.min(axis=1)
    passed = pass_first < bust_first
    busted = (bust_first <= max_steps) & ~passed
    return passed, busted, np.where(passed, pass_first + 1, np.nan)


def p_funded_at_cost(samples, sizing_pct):
    rng = np.random.default_rng(RNG_SEED)
    boot1 = generate_bootstrap(samples, N_PATHS, MAX_STEPS, BLOCK_SIZE, rng)
    p1_pass, p1_bust, _ = simulate_phase(boot1, sizing_pct, TARGET_P1)
    if not p1_pass.any():
        return 0.0, p1_bust.mean(), 0.0
    boot2 = generate_bootstrap(samples, int(p1_pass.sum()), MAX_STEPS, BLOCK_SIZE, rng)
    p2_pass, _, _ = simulate_phase(boot2, sizing_pct, TARGET_P2)
    p_funded = (p1_pass.sum() / N_PATHS) * (p2_pass.sum() / p1_pass.sum())
    return p_funded, p1_bust.mean(), p1_pass.mean()


# ===== COST SWEEP =====
print("=" * 78); print("COST SENSITIVITY — V2+E7 mean_R and p(funded) across cost"); print("=" * 78)
print(f"\n{'cost_bps':>9s}{'mean_R':>9s}  {'sizing 1.0%':>20s}  {'sizing 1.5%':>20s}  {'sizing 2.5%':>20s}")
print(f"{'':9s}{'':9s}  {'p_fund   p_bust_P1':>20s}  {'p_fund   p_bust_P1':>20s}  {'p_fund   p_bust_P1':>20s}")
rows = []
for c in [0.4, 1.0, 2.0, 3.0, 4.0, 6.0]:
    r_c = r_at_cost(c)
    cols = []
    for sz in [0.010, 0.015, 0.025]:
        pf, pb1, p1p = p_funded_at_cost(r_c, sz)
        cols.append((pf, pb1, p1p))
        rows.append({"cost_bps": c, "mean_R": r_c.mean(), "sizing": sz, "p_funded": pf, "p_bust_P1": pb1})
    print(f"{c:>9.1f}{r_c.mean():>+9.4f}  "
          f"{cols[0][0]:>+7.1%}  {cols[0][1]:>+7.1%}      "
          f"{cols[1][0]:>+7.1%}  {cols[1][1]:>+7.1%}      "
          f"{cols[2][0]:>+7.1%}  {cols[2][1]:>+7.1%}")

# Also placebo zero-mean at corresponding std for each cost
print("\nReference placebo p(funded) — Gaussian zero-μ, std=1.20 (signal-free container math):")
rng = np.random.default_rng(RNG_SEED + 100)
placeboA = rng.normal(0.0, 1.20, size=4013)
for sz in [0.010, 0.015, 0.025]:
    pf, pb1, p1p = p_funded_at_cost(placeboA, sz)
    print(f"  sizing={sz:.1%}  p(funded)={pf:.1%}  p1_bust={pb1:.1%}  → 'free lunch' from container math alone")

pd.DataFrame(rows).to_csv(
    "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_at_0p4bps_cost_sweep.csv", index=False)

# ===== Year stress: 2015 isolated =====
print("\n" + "=" * 78); print("WORST-YEAR STRESS — 2015 alone (worst year @ 0.4 bps, mean_R = −0.0867)"); print("=" * 78)
df["year"] = pd.to_datetime(df["date"]).dt.year
r_2015 = (r_2 + (2.0 - 0.4) * cost_unit + E7_LIFT_R)[df.year.values == 2015]
print(f"  2015 sample: n={len(r_2015)}  mean={r_2015.mean():+.4f}  std={r_2015.std():.3f}")
# If we were unlucky enough to start during 2015:
rng = np.random.default_rng(RNG_SEED + 200)
boot_2015 = generate_bootstrap(r_2015, N_PATHS, MAX_STEPS, BLOCK_SIZE, rng)
for sz in [0.010, 0.015, 0.025]:
    p1_pass, p1_bust, _ = simulate_phase(boot_2015, sz, TARGET_P1)
    print(f"  sizing={sz:.1%}  P1 pass={p1_pass.mean():.1%}  P1 bust={p1_bust.mean():.1%}")
print("  → if a candidate starts during a regime like 2015, P1 pass collapses well below ceiling.")
