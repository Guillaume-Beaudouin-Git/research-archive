"""Targeted MC re-run: 0.4 bps RT, weekly resolution 1..10 weeks + terminal.
Reuses the engine from orb_ppass_grid_v2.py (functions verbatim, same seed,
same MC settings). Output: ONE table only.
"""
import numpy as np
import pandas as pd

# -- Same constants as orb_ppass_grid_v2.py
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
MIN_TRADES_PHASE = 4
RNG_SEED = 17
TRADES_PER_WEEK = 5

COST_BPS = 0.4
SIZINGS = [0.010, 0.015, 0.025]
WEEKS = list(range(1, 11))

df = pd.read_parquet(LEDGER).reset_index()
r_2 = df["r_2 bps RT (median)"].astype(float).values
r_1 = df["r_1 bps RT (aggressive)"].astype(float).values
cost_unit = r_1 - r_2

def r_at_cost(c_bps):
    return r_2 + (2.0 - c_bps) * cost_unit + E7_LIFT_R

def generate_bootstrap(samples, n_paths, max_steps, block_size, rng):
    L = len(samples)
    n_blocks = (max_steps + block_size - 1) // block_size
    starts = rng.integers(0, L - block_size + 1, size=(n_paths, n_blocks))
    out = np.empty((n_paths, n_blocks * block_size), dtype=np.float64)
    for k in range(block_size):
        out[:, k::block_size] = samples[starts + k]
    return out[:, :max_steps]

def simulate_phase(boot, sizing_pct, target_pct, account_init=ACCOUNT_INIT,
                   dll_pct=DLL_PCT, max_total_pct=MAX_TOTAL_PCT,
                   min_trades=MIN_TRADES_PHASE):
    n_paths, max_steps = boot.shape
    risk_dollar = account_init * sizing_pct
    pnl = boot * risk_dollar
    eq = account_init + np.cumsum(pnl, axis=1)
    midnight = np.concatenate([np.full((n_paths, 1), account_init), eq[:, :-1]], axis=1)
    dll_breach = pnl <= -dll_pct * midnight
    floor = account_init * (1 - max_total_pct)
    target = account_init * (1 + target_pct)
    floor_breach = eq <= floor
    target_hit = eq >= target
    target_hit[:, :min_trades - 1] = False
    bust_step = np.where(dll_breach | floor_breach, np.arange(max_steps), max_steps + 1)
    bust_first = bust_step.min(axis=1)
    pass_step = np.where(target_hit, np.arange(max_steps), max_steps + 1)
    pass_first = pass_step.min(axis=1)
    passed = pass_first < bust_first
    return passed, pass_first + 1

def run_cell(samples, sizing_pct, seed_offset, n_paths=N_PATHS):
    rng = np.random.default_rng(RNG_SEED + seed_offset)
    boot1 = generate_bootstrap(samples, n_paths, MAX_STEPS, BLOCK_SIZE, rng)
    p1_pass, p1_pass_step = simulate_phase(boot1, sizing_pct, TARGET_P1)
    n_p1_pass = int(p1_pass.sum())
    if n_p1_pass == 0:
        return np.array([], dtype=np.int64), 0.0
    boot2 = generate_bootstrap(samples, n_p1_pass, MAX_STEPS, BLOCK_SIZE, rng)
    p2_pass, p2_pass_step = simulate_phase(boot2, sizing_pct, TARGET_P2)
    total_step = p1_pass_step[p1_pass][p2_pass] + p2_pass_step[p2_pass]
    p_funded = (n_p1_pass / n_paths) * (p2_pass.mean() if n_p1_pass > 0 else 0.0)
    return total_step, p_funded

# Run
r_c = r_at_cost(COST_BPS)
results = {}
terminals = {}
for sz in SIZINGS:
    total_step, p_funded_term = run_cell(r_c, sz, seed_offset=int(COST_BPS * 100) + int(sz * 1000))
    terminals[sz] = p_funded_term
    weekly = {}
    for w in WEEKS:
        weekly[w] = (total_step <= w * TRADES_PER_WEEK).sum() / N_PATHS
    results[sz] = weekly

# Table
print("ORB V2+E7 — FTMO 2-step p(funded) cumulé — coût 0.4 bps RT — 12000 paths/cell, seed=17, blocs 21j")
print()
print(f"{'Semaine':>8s}  {'1.0%':>8s}  {'1.5%':>8s}  {'2.5%':>8s}")
print("-" * 40)
for w in WEEKS:
    print(f"{w:>8d}  {results[0.010][w]*100:>7.1f}%  {results[0.015][w]*100:>7.1f}%  {results[0.025][w]*100:>7.1f}%")
print("-" * 40)
print(f"{'TERMINAL':>8s}  {terminals[0.010]*100:>7.1f}%  {terminals[0.015]*100:>7.1f}%  {terminals[0.025]*100:>7.1f}%   (no time limit, max 5 ans/phase)")
