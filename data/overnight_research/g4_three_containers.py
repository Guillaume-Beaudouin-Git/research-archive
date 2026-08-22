"""G4 — Three honest containers: sprint, funded-book sleeve, personal book.

We refuse to conflate "real edge" with "FTMO challenge vehicle".
The midweek overnight has SR_net ≈ 0.68 at the leverage that survives the 10%
Max Total Loss historically (L=0.5×).  But what's the *challenge pass probability*?

Containers:
  (a) FTMO 2-step SPRINT <2mo (self-imposed, since 2023 FTMO removed time limit):
      Phase 1 needs +10% in 42 trading days, no 5% daily, no 10% total.
      Phase 2 needs +5% in another 42 trading days.
      Monte-Carlo with block bootstrap of the midweek net distribution.
  (b) FTMO 2-step UNLIMITED-TIME (the post-2023 reality):
      Same barriers, but NO time limit. p(eventual funded).
  (c) Personal book sleeve, no propfirm barrier, sized to L=0.5×:
      SR, MaxDD, worst-month, return profile.

Method: stationary block bootstrap (block ~5 events, Politis-Romano-ish).
"""
import numpy as np
import pandas as pd

DAILY = "<HOME>/Desktop/Algo_claude/data/overnight_research/nq_rth_daily.parquet"
SWAP_1X = 3.081 / 1e4
SWAP_3X = 9.243 / 1e4

d = pd.read_parquet(DAILY).copy()
# Conv A swap charge (conservative: Mon-open = 3x)
d["swap_charge"] = d.wd.apply(lambda w: SWAP_3X if w == 0 else SWAP_1X)
d["net_ret"] = d["ov_bps"] / 1e4 - d["swap_charge"]

# Midweek-only series (held days): Tue+Wed open
mid = d.loc[d.wd.isin([1, 2]), "net_ret"].dropna().values
print(f"Midweek nights (sample): n={len(mid)}  mean={mid.mean()*1e4:+.2f} bps  std={mid.std()*1e4:.0f} bps")
print(f"   worst={mid.min()*100:+.2f}%  p1={np.percentile(mid,1)*100:+.2f}%  p5={np.percentile(mid,5)*100:+.2f}%  p95={np.percentile(mid,95)*100:+.2f}%")

# Build the full daily calendar with zeros on off-days (for FTMO daily DLL accounting)
zero_aug = pd.DataFrame(index=d.index, data={"r": 0.0})
zero_aug.loc[d.wd.isin([1, 2]), "r"] = mid
calendar = zero_aug["r"].values  # daily series, 0 on non-mid days, leveraged 1×

# ===== Block bootstrap =====
RNG = np.random.default_rng(7)


def stationary_bootstrap(arr, n_steps, mean_block=5, rng=RNG):
    """Generate a sample of length n_steps from arr using stationary block bootstrap."""
    L = len(arr)
    out = np.empty(n_steps)
    i = 0
    while i < n_steps:
        start = rng.integers(0, L)
        block_len = rng.geometric(1 / mean_block)
        block_len = min(block_len, n_steps - i, L)
        end = min(start + block_len, L)
        chunk = arr[start:end]
        out[i:i + len(chunk)] = chunk
        i += len(chunk)
        if end == L and i < n_steps:
            # wrap around
            continue
    return out[:n_steps]


def ftmo_2step_sim(daily_ret_sample, lev, p1_target=0.10, p2_target=0.05,
                   dll=0.05, max_total=0.10, max_days_per_phase=None, n_paths=20000,
                   rng=RNG):
    """Path-by-path FTMO 2-step pass simulator on a daily-return SAMPLE (already leveraged)."""
    passed = np.zeros(n_paths, dtype=bool)
    busted = np.zeros(n_paths, dtype=bool)
    days_p1 = np.full(n_paths, np.nan)
    days_p2 = np.full(n_paths, np.nan)
    days_total = np.full(n_paths, np.nan)

    horizon_p1 = max_days_per_phase or len(daily_ret_sample) // 2
    horizon_p2 = max_days_per_phase or len(daily_ret_sample) // 2

    for k in range(n_paths):
        # Phase 1
        path = stationary_bootstrap(daily_ret_sample * lev, horizon_p1, rng=rng)
        eq = 1.0
        hwm = 1.0
        d_at_p1_open = 1.0  # balance at 00:00 of current day
        bust = False
        passed_p1 = False
        p1_day = np.nan
        for j, r in enumerate(path):
            # Daily-DLL: r is daily return on current balance which equals d_at_p1_open (compounded)
            # Wait — FTMO DLL anchors at midnight balance. We approximate it: balance at start of day.
            if r <= -dll:
                bust = True
                break
            eq *= (1 + r)
            hwm = max(hwm, eq)
            if eq <= 1.0 - max_total:
                bust = True
                break
            if eq - 1.0 >= p1_target:
                passed_p1 = True
                p1_day = j + 1
                break
            d_at_p1_open = eq  # next day's anchor
        if bust:
            busted[k] = True
            continue
        if not passed_p1:
            # time-out
            continue

        # Phase 2 — re-anchor (FTMO funds reset, but same barriers apply to phase 2)
        path = stationary_bootstrap(daily_ret_sample * lev, horizon_p2, rng=rng)
        eq = 1.0
        hwm = 1.0
        passed_p2 = False
        p2_day = np.nan
        for j, r in enumerate(path):
            if r <= -dll:
                bust = True
                break
            eq *= (1 + r)
            hwm = max(hwm, eq)
            if eq <= 1.0 - max_total:
                bust = True
                break
            if eq - 1.0 >= p2_target:
                passed_p2 = True
                p2_day = j + 1
                break
        if bust:
            busted[k] = True
            continue
        if passed_p2:
            passed[k] = True
            days_p1[k] = p1_day
            days_p2[k] = p2_day
            days_total[k] = p1_day + p2_day
    return {"p_pass": passed.mean(), "p_bust": busted.mean(),
            "passed": passed, "days_total": days_total,
            "median_days": np.nanmedian(days_total[passed]) if passed.any() else np.nan}


# ===== Container (a): SPRINT <2mo =====
print("\n" + "=" * 78)
print("CONTAINER (a) — FTMO 2-step SPRINT <2 months/phase (=42 trading days)")
print("=" * 78)
print(f"{'Lev':>5s}{'P(pass)':>10s}{'P(bust)':>10s}{'medDays':>10s}")
for L in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
    r = ftmo_2step_sim(calendar, L, max_days_per_phase=42, n_paths=10000)
    print(f"{L:>5.2f}{r['p_pass']:>10.3%}{r['p_bust']:>10.3%}{r['median_days']:>10.0f}" if not np.isnan(r['median_days']) else
          f"{L:>5.2f}{r['p_pass']:>10.3%}{r['p_bust']:>10.3%}{'n/a':>10s}")

# ===== Container (b): UNLIMITED-TIME (post-2023 FTMO) =====
print("\n" + "=" * 78)
print("CONTAINER (b) — FTMO 2-step UNLIMITED time (post-2023 reality)")
print("=" * 78)
print(f"{'Lev':>5s}{'P(pass)':>10s}{'P(bust)':>10s}{'medDays':>10s}{'medMonths':>11s}")
for L in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
    # cap horizon at 5 years per phase
    r = ftmo_2step_sim(calendar, L, max_days_per_phase=252 * 5, n_paths=10000)
    mm = r['median_days'] / 21 if not np.isnan(r['median_days']) else np.nan
    print(f"{L:>5.2f}{r['p_pass']:>10.3%}{r['p_bust']:>10.3%}"
          f"{r['median_days']:>10.0f}" if not np.isnan(r['median_days']) else f"{L:>5.2f}{r['p_pass']:>10.3%}{r['p_bust']:>10.3%}{'n/a':>10s}",
          f"{mm:>11.1f}" if not np.isnan(mm) else f"{'n/a':>11s}")

# ===== Container (c): personal book =====
print("\n" + "=" * 78)
print("CONTAINER (c) — PERSONAL BOOK sleeve (no propfirm barrier)")
print("=" * 78)
ann_factor = np.sqrt(252)
print(f"{'Lev':>5s}{'AnnRet':>9s}{'AnnVol':>9s}{'SR':>7s}{'MaxDD':>9s}{'WorstMo':>10s}{'WorstNight':>12s}")
for L in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
    lev_r = calendar * L
    eq = (1 + lev_r).cumprod()
    hwm = np.maximum.accumulate(eq)
    dd = eq / hwm - 1
    mean_d = lev_r.mean()
    std_d = lev_r.std()
    sr = (mean_d / std_d) * ann_factor if std_d > 0 else np.nan
    ann_ret = (eq[-1]) ** (252 / len(eq)) - 1
    monthly = pd.Series(lev_r, index=d.index).resample("ME").apply(lambda x: (1 + x).prod() - 1)
    worst_mo = monthly.min()
    worst_night = lev_r.min()
    print(f"{L:>5.2f}{ann_ret:>9.2%}{std_d*ann_factor:>9.2%}{sr:>7.2f}{dd.min():>9.2%}{worst_mo:>10.2%}{worst_night:>12.2%}")

# ===== Save =====
out_rows = []
for L in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
    sprint = ftmo_2step_sim(calendar, L, max_days_per_phase=42, n_paths=5000)
    unlim = ftmo_2step_sim(calendar, L, max_days_per_phase=252 * 5, n_paths=5000)
    lev_r = calendar * L
    sr = (lev_r.mean() / lev_r.std()) * ann_factor if lev_r.std() > 0 else np.nan
    eq = (1 + lev_r).cumprod()
    out_rows.append({
        "lev": L,
        "sprint_p_pass": sprint["p_pass"], "sprint_p_bust": sprint["p_bust"],
        "unlim_p_pass": unlim["p_pass"], "unlim_p_bust": unlim["p_bust"],
        "ann_sr": sr,
        "max_dd": float(np.min(eq / np.maximum.accumulate(eq) - 1)),
    })
pd.DataFrame(out_rows).to_csv(
    "<HOME>/Desktop/Algo_claude/data/overnight_research/g4_containers.csv", index=False)
print("\nSaved: data/overnight_research/g4_containers.csv")
