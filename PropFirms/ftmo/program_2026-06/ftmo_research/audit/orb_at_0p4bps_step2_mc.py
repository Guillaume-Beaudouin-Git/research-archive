"""ORB V2+E7 @ 0.4 bps — Step 2: FTMO 2-step block-bootstrap MC.

Rules (SETTLED, post-July-2023 FTMO):
  Phase 1: +10% target, 5% daily, 10% max-total (floor STATIC = $9k on $10k), NO time limit.
  Phase 2: +5% target, 5% daily, 10% max-total, NO time limit.
Trade frequency: ORB ≈ 1 trade/day after V2 filter (4013 trades / ~4032 trading days).
Block bootstrap: 21-trade blocks (preserves regime clustering); 12000 paths per phase.

Sizing convention: risk_$ = sizing% × initial_account (fixed dollar risk, FTMO standard).
"""
import numpy as np
import pandas as pd

INPUT = "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_v2e7_0p4bps_per_trade.parquet"
ACCOUNT_INIT = 10000.0
DLL_PCT = 0.05
MAX_TOTAL_PCT = 0.10
TARGET_P1 = 0.10
TARGET_P2 = 0.05
BLOCK_SIZE = 21
N_PATHS = 12000
MAX_STEPS = 252 * 5  # 5 years per phase max (no time limit, practical cap)
RNG_SEED = 17

# --- Load
df = pd.read_parquet(INPUT)
R = df["r_v2e7_0p4"].values.astype(np.float64)
print(f"Trade R-distribution: n={len(R)}  mean={R.mean():+.4f}  std={R.std():.4f}  "
      f"skew={pd.Series(R).skew():+.4f}  kurt={pd.Series(R).kurt():+.2f}  "
      f"min={R.min():+.3f}  max={R.max():+.3f}")
print(f"  p1={np.percentile(R,1):+.3f}  p5={np.percentile(R,5):+.3f}  "
      f"p50={np.percentile(R,50):+.3f}  p95={np.percentile(R,95):+.3f}")


def generate_bootstrap(samples, n_paths, max_steps, block_size, rng):
    """Vectorized block bootstrap: (n_paths × max_steps) of R-values."""
    L = len(samples)
    n_blocks = (max_steps + block_size - 1) // block_size
    starts = rng.integers(0, L - block_size + 1, size=(n_paths, n_blocks))
    out = np.empty((n_paths, n_blocks * block_size), dtype=np.float64)
    # Build column-wise per offset
    for k in range(block_size):
        # samples at index starts + k for each block
        out[:, k::block_size] = samples[starts + k]
    return out[:, :max_steps]


def simulate_phase(boot, sizing_pct, target_pct, dll_pct=DLL_PCT,
                   max_total_pct=MAX_TOTAL_PCT, account_init=ACCOUNT_INIT):
    """Vectorized phase simulation. boot[i, t] is path i's trade t R-value."""
    n_paths, max_steps = boot.shape
    risk_dollar = account_init * sizing_pct  # constant $ risk per trade
    pnl = boot * risk_dollar
    eq = account_init + np.cumsum(pnl, axis=1)  # equity time series
    # DLL check: each trade pnl vs midnight balance (= eq just before trade = eq[:, t-1] or init at t=0)
    midnight = np.concatenate([np.full((n_paths, 1), account_init), eq[:, :-1]], axis=1)
    dll_breach = pnl <= -dll_pct * midnight
    # Floor check
    floor = account_init * (1 - max_total_pct)
    floor_breach = eq <= floor
    # Target check
    target = account_init * (1 + target_pct)
    target_hit = eq >= target
    # First event per path
    bust_step = np.where(dll_breach | floor_breach, np.arange(max_steps), max_steps + 1)
    bust_first = bust_step.min(axis=1)
    pass_step = np.where(target_hit, np.arange(max_steps), max_steps + 1)
    pass_first = pass_step.min(axis=1)
    passed = pass_first < bust_first
    busted = (bust_first <= max_steps) & ~passed
    days_to_pass = np.where(passed, pass_first + 1, np.nan)
    return {"passed": passed, "busted": busted, "days_to_pass": days_to_pass}


def run_mc(samples, label, sizings):
    print("\n" + "=" * 78); print(f"FTMO 2-step MC — {label}"); print("=" * 78)
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    for sz in sizings:
        boot1 = generate_bootstrap(samples, N_PATHS, MAX_STEPS, BLOCK_SIZE, rng)
        p1 = simulate_phase(boot1, sz, TARGET_P1)
        p1_pass = p1["passed"]; p1_med = np.nanmedian(p1["days_to_pass"][p1_pass])
        # Among phase-1 passers, run phase 2
        n_p1_pass = int(p1_pass.sum())
        if n_p1_pass > 0:
            boot2 = generate_bootstrap(samples, n_p1_pass, MAX_STEPS, BLOCK_SIZE, rng)
            p2 = simulate_phase(boot2, sz, TARGET_P2)
            p_funded = (p1_pass.sum() * p2["passed"].sum()) / (N_PATHS * n_p1_pass)
            p_bust2 = p2["busted"].mean()
            p2_med = np.nanmedian(p2["days_to_pass"][p2["passed"]]) if p2["passed"].any() else np.nan
            total_med = p1_med + p2_med if (not np.isnan(p1_med) and not np.isnan(p2_med)) else np.nan
        else:
            p_funded = 0.0; p_bust2 = np.nan; p2_med = np.nan; total_med = np.nan
        p_bust1 = p1["busted"].mean()
        # Overall bust = phase1 bust + phase2 bust given passed
        overall_bust = p_bust1 + (1 - p_bust1) * (p_bust2 if not np.isnan(p_bust2) else 0)
        rows.append({"label": label, "sizing_pct": sz, "p_pass_P1": p1_pass.mean(),
                     "p_bust_P1": p_bust1, "p_funded": p_funded,
                     "p_bust_total": overall_bust,
                     "med_days_P1_if_pass": p1_med, "med_days_P2_if_pass": p2_med,
                     "med_days_total_if_funded": total_med})
        print(f"  sizing={sz:.1%}  P1 pass={p1_pass.mean():.1%}  P1 bust={p_bust1:.1%}  "
              f"funded={p_funded:.1%}  overall_bust={overall_bust:.1%}  "
              f"med_days_P1={p1_med:>5.0f}  med_days_total={total_med if not np.isnan(total_med) else 'n/a':>5}")
    return rows


SIZINGS = [0.010, 0.015, 0.025]

# ===== Real ORB =====
real_rows = run_mc(R, "ORB V2+E7 @ 0.4 bps (real)", SIZINGS)

# ===== Placebo A: zero-mean Gaussian (no edge, std matched) =====
rng = np.random.default_rng(RNG_SEED + 1)
placeboA = rng.normal(loc=0.0, scale=R.std(), size=len(R))
print(f"\nPlacebo A (Gauss zero-mean, std={R.std():.4f}): mean={placeboA.mean():+.4f}")
placeboA_rows = run_mc(placeboA, "Placebo A — Gaussian zero-mean", SIZINGS)

# ===== Placebo B: mean+std-matched Gaussian (no skew, no clustering) =====
rng = np.random.default_rng(RNG_SEED + 2)
placeboB = rng.normal(loc=R.mean(), scale=R.std(), size=len(R))
print(f"\nPlacebo B (Gauss mean={R.mean():.4f}, std={R.std():.4f}): mean={placeboB.mean():+.4f}")
placeboB_rows = run_mc(placeboB, "Placebo B — Gaussian mean+std matched", SIZINGS)

# ===== Placebo C: mean+std+skew-matched (skewed-Normal) =====
from scipy.stats import skewnorm
rng = np.random.default_rng(RNG_SEED + 3)
# fit skew-normal to R
sk = pd.Series(R).skew()
# skewnorm with shape alpha → skew. Solve approximately.
# Use scipy fit:
try:
    a_fit, loc_fit, scale_fit = skewnorm.fit(R, method="MLE")
    placeboC = skewnorm.rvs(a_fit, loc=loc_fit, scale=scale_fit, size=len(R), random_state=rng)
    print(f"\nPlacebo C (Skew-normal fit, α={a_fit:.2f}): mean={placeboC.mean():+.4f}  std={placeboC.std():.4f}  skew={pd.Series(placeboC).skew():+.4f}")
    placeboC_rows = run_mc(placeboC, "Placebo C — Skew-normal mean+vol+skew matched", SIZINGS)
except Exception as e:
    print(f"Placebo C failed: {e}")
    placeboC_rows = []

# Save all
all_rows = real_rows + placeboA_rows + placeboB_rows + placeboC_rows
df_out = pd.DataFrame(all_rows)
df_out.to_csv("<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_at_0p4bps_mc.csv", index=False)
print("\nSaved -> orb_at_0p4bps_mc.csv")

# ===== Decomposition summary =====
print("\n" + "=" * 78)
print("DECOMPOSITION — signal contribution vs container math")
print("=" * 78)
print(f"\n{'Sizing':>8s}{'Real ORB':>12s}{'Placebo B (μ-matched)':>25s}{'Placebo A (zero-μ)':>22s}{'Real − PlcB (signal)':>22s}{'PlcB − PlcA (mean-drift)':>26s}")
for sz in SIZINGS:
    real = next(r["p_funded"] for r in real_rows if r["sizing_pct"] == sz)
    plcA = next(r["p_funded"] for r in placeboA_rows if r["sizing_pct"] == sz)
    plcB = next(r["p_funded"] for r in placeboB_rows if r["sizing_pct"] == sz)
    print(f"{sz:>7.1%}{real:>12.1%}{plcB:>25.1%}{plcA:>22.1%}{real-plcB:>+22.1%}{plcB-plcA:>+26.1%}")
print("\n  Interpretation:")
print("  • Real − PlcB (μ-matched)  = lift from non-Gaussian features (skew, fat tails, regime clustering)")
print("  • PlcB − PlcA (zero-μ)     = lift from positive mean drift (the 'edge' if normally distributed)")
print("  • PlcA itself              = pure container math (no edge, just unlimited-time no-bust)")
