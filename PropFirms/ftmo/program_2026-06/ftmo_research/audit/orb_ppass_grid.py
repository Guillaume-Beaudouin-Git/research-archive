"""ORB V2+E7 — Grid p(funded) [coût × sizing × horizon] FTMO 2-step.

Spec FIGÉE V2+E7. Rules SETTLED: +10%/+5%, daily 5%, floor static $9k,
no time limit, min 4 trades/phase. Block bootstrap 21-trade blocks,
12000 paths/cell, seed fixed. Contiguous chunks (NOT IID).

For each (cost, sizing) cell:
  - p(funded) cumulative at horizons {1, 2, 4, 8, 12, 26 weeks, terminal}
  - p(P1 pass), p(bust), p10/median/p90 of trades to funded
  - placebo zero-μ matched std (signal-free container math)
For 2015 alone (worst regime year): P1 pass per sizing.
"""
import numpy as np
import pandas as pd
import json

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

COSTS_BPS = [0.2, 0.5, 1.0, 2.0]
SIZINGS = [0.010, 0.015, 0.025]
HORIZONS_WEEKS = [1, 2, 4, 8, 12, 26]
TRADES_PER_WEEK = 5  # ORB ≈ 1 trade/day RTH
TERMINAL_TRADES = MAX_STEPS * 2  # both phases summed

# -- Load + build cost grids
df = pd.read_parquet(LEDGER).reset_index()
r_2 = df["r_2 bps RT (median)"].astype(float).values
r_1 = df["r_1 bps RT (aggressive)"].astype(float).values
cost_unit = r_1 - r_2
year = pd.to_datetime(df["date"]).dt.year.values

def r_at_cost(c_bps):
    return r_2 + (2.0 - c_bps) * cost_unit + E7_LIFT_R

# -- MC engine
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
    """Returns: passed, busted, pass_step (1-indexed), bust_step (1-indexed)."""
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
    # Enforce min trading days: target_hit only valid from trade index min_trades-1
    target_hit[:, :min_trades - 1] = False
    bust_step = np.where(dll_breach | floor_breach, np.arange(max_steps), max_steps + 1)
    bust_first = bust_step.min(axis=1)
    pass_step = np.where(target_hit, np.arange(max_steps), max_steps + 1)
    pass_first = pass_step.min(axis=1)
    passed = pass_first < bust_first
    busted = (bust_first <= max_steps) & ~passed
    return passed, busted, pass_first + 1, bust_first + 1


def run_cell(samples, sizing_pct, seed_offset, n_paths=N_PATHS):
    """One MC cell. Returns dict with funded-time distribution + placebo-ready stats."""
    rng = np.random.default_rng(RNG_SEED + seed_offset)
    # Phase 1
    boot1 = generate_bootstrap(samples, n_paths, MAX_STEPS, BLOCK_SIZE, rng)
    p1_pass, p1_bust, p1_pass_step, _ = simulate_phase(boot1, sizing_pct, TARGET_P1)
    n_p1_pass = int(p1_pass.sum())
    # Phase 2 (only for P1-passing paths)
    if n_p1_pass > 0:
        boot2 = generate_bootstrap(samples, n_p1_pass, MAX_STEPS, BLOCK_SIZE, rng)
        p2_pass, p2_bust, p2_pass_step, _ = simulate_phase(boot2, sizing_pct, TARGET_P2)
        # Total trade index for funded paths
        p1_pass_step_for_passers = p1_pass_step[p1_pass]   # 1-indexed
        total_step_p2_pass = p1_pass_step_for_passers[p2_pass] + p2_pass_step[p2_pass]
    else:
        p2_pass = np.array([], dtype=bool)
        p2_bust = np.array([], dtype=bool)
        total_step_p2_pass = np.array([], dtype=np.int64)
    p_funded = (n_p1_pass / n_paths) * (p2_pass.mean() if n_p1_pass > 0 else 0.0)
    p_bust_p1 = p1_bust.mean()
    p_bust_p2 = p2_bust.mean() if n_p1_pass > 0 else 0.0
    p_bust_total = p_bust_p1 + (1 - p_bust_p1) * p_bust_p2  # joint
    return {
        "p_funded_terminal": p_funded,
        "p1_pass": p1_pass.mean(),
        "p1_bust": p_bust_p1,
        "p2_pass_among_p1": p2_pass.mean() if n_p1_pass > 0 else 0.0,
        "p_bust_total": p_bust_total,
        "total_step_funded": total_step_p2_pass,  # 1-indexed trade count to funded
        "n_funded": len(total_step_p2_pass),
        "n_p1_pass": n_p1_pass,
    }


def horizon_pcum(total_step_funded, horizon_trades, n_paths=N_PATHS):
    if len(total_step_funded) == 0:
        return 0.0
    return (total_step_funded <= horizon_trades).sum() / n_paths


# ===== MAIN GRID =====
print(f"Running grid: {len(COSTS_BPS)} costs × {len(SIZINGS)} sizings = {len(COSTS_BPS)*len(SIZINGS)} cells, "
      f"plus placebos. N_paths={N_PATHS}.")
print(f"Horizons (trades): {[w*TRADES_PER_WEEK for w in HORIZONS_WEEKS]}, terminal={TERMINAL_TRADES}")
print()

rows = []
for c in COSTS_BPS:
    r_c = r_at_cost(c)
    print(f"\n=== COST {c} bps RT  (mean_R = {r_c.mean():+.4f}) ===")
    # Real ORB
    for sz in SIZINGS:
        res = run_cell(r_c, sz, seed_offset=int(c * 100) + int(sz * 1000))
        row = {"variant": "real", "cost_bps": c, "sizing": sz, "mean_R": r_c.mean()}
        for hw in HORIZONS_WEEKS:
            row[f"pf_{hw}w"] = horizon_pcum(res["total_step_funded"], hw * TRADES_PER_WEEK)
        row["pf_terminal"] = res["p_funded_terminal"]
        row["p1_pass"] = res["p1_pass"]
        row["p1_bust"] = res["p1_bust"]
        row["p_bust_total"] = res["p_bust_total"]
        if res["n_funded"] > 0:
            row["med_trades"] = float(np.median(res["total_step_funded"]))
            row["p10_trades"] = float(np.percentile(res["total_step_funded"], 10))
            row["p90_trades"] = float(np.percentile(res["total_step_funded"], 90))
        else:
            row["med_trades"] = row["p10_trades"] = row["p90_trades"] = np.nan
        rows.append(row)
        print(f"  REAL sizing={sz:.1%}  p_funded@1w={row['pf_1w']:.1%} 4w={row['pf_4w']:.1%} "
              f"12w={row['pf_12w']:.1%} 26w={row['pf_26w']:.1%} terminal={row['pf_terminal']:.1%} "
              f"P1_pass={row['p1_pass']:.1%} med_trades={row['med_trades']:.0f}")

    # Placebo zero-μ Gaussian matched std at THIS cost
    rng_p = np.random.default_rng(RNG_SEED + int(c * 100) + 9999)
    placebo = rng_p.normal(0.0, r_c.std(), size=len(r_c))
    for sz in SIZINGS:
        res = run_cell(placebo, sz, seed_offset=int(c * 100) + int(sz * 1000) + 7777)
        row = {"variant": "placebo_zero_mu", "cost_bps": c, "sizing": sz, "mean_R": placebo.mean()}
        for hw in HORIZONS_WEEKS:
            row[f"pf_{hw}w"] = horizon_pcum(res["total_step_funded"], hw * TRADES_PER_WEEK)
        row["pf_terminal"] = res["p_funded_terminal"]
        row["p1_pass"] = res["p1_pass"]
        row["p1_bust"] = res["p1_bust"]
        row["p_bust_total"] = res["p_bust_total"]
        if res["n_funded"] > 0:
            row["med_trades"] = float(np.median(res["total_step_funded"]))
            row["p10_trades"] = float(np.percentile(res["total_step_funded"], 10))
            row["p90_trades"] = float(np.percentile(res["total_step_funded"], 90))
        else:
            row["med_trades"] = row["p10_trades"] = row["p90_trades"] = np.nan
        rows.append(row)
        print(f"  PLAC sizing={sz:.1%}  p_funded@terminal={row['pf_terminal']:.1%} (signal-free reference)")

# ===== 2015 STRESS — P1 pass per sizing (at each cost) =====
print("\n=== STRESS REGIME 2015 — P1 pass only, all costs ===")
mask_2015 = (year == 2015)
n_2015 = mask_2015.sum()
print(f"2015 sample: n={n_2015}")
stress_rows = []
for c in COSTS_BPS:
    r_c = r_at_cost(c)
    r_2015 = r_c[mask_2015]
    for sz in SIZINGS:
        rng_s = np.random.default_rng(RNG_SEED + 4242 + int(c * 100) + int(sz * 1000))
        boot = generate_bootstrap(r_2015, N_PATHS, MAX_STEPS, BLOCK_SIZE, rng_s)
        passed, busted, _, _ = simulate_phase(boot, sz, TARGET_P1)
        stress_rows.append({"cost_bps": c, "sizing": sz, "p1_pass_2015": passed.mean(),
                            "p1_bust_2015": busted.mean(), "mean_R_2015": r_2015.mean()})
        print(f"  cost={c} bps  sizing={sz:.1%}  P1_pass(2015)={passed.mean():.1%}  bust={busted.mean():.1%}  mean_R_2015={r_2015.mean():+.4f}")

# ===== Save =====
df_grid = pd.DataFrame(rows)
df_stress = pd.DataFrame(stress_rows)
df_grid.to_csv("<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_ppass_grid_main.csv", index=False)
df_stress.to_csv("<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_ppass_grid_stress2015.csv", index=False)
print("\nSaved -> orb_ppass_grid_main.csv + orb_ppass_grid_stress2015.csv")

# ===== Print summary table (markdown-ready) =====
print("\n" + "=" * 80)
print("SUMMARY p(funded) TERMINAL — Real vs Placebo zero-μ matched std")
print("=" * 80)
print(f"\n{'Cost':>6s}{'Sizing':>9s}{'Real_pf':>10s}{'Placebo_pf':>13s}{'SignalLift':>13s}{'P1_2015':>10s}")
for c in COSTS_BPS:
    for sz in SIZINGS:
        real = df_grid[(df_grid.variant=='real') & (df_grid.cost_bps==c) & (df_grid.sizing==sz)].iloc[0]
        plc = df_grid[(df_grid.variant=='placebo_zero_mu') & (df_grid.cost_bps==c) & (df_grid.sizing==sz)].iloc[0]
        st = df_stress[(df_stress.cost_bps==c) & (df_stress.sizing==sz)].iloc[0]
        lift = real.pf_terminal - plc.pf_terminal
        marker = " ←" if abs(lift) < 0.05 else ""
        print(f"{c:>6.1f}{sz:>9.1%}{real.pf_terminal:>10.1%}{plc.pf_terminal:>13.1%}{lift:>+13.1%}{st.p1_pass_2015:>10.1%}{marker}")
