"""MERGE — combine skew+ Cowork sleeves with existing assets, common window.

Sleeves to merge:
  - Long-vol VXX (session_cowork): tail-hedge, neg carry
  - VIX-term timé (session_vol_tail): reconstruct from VIX/VIX3M + VIXY-proxy via -VIX_change
  - MR reversal 1j (session_vol_tail): reconstruct from SP500 daily
  - Pré-FOMC (session_3): reconstruct from NQ daily + FOMC calendar
Existing:
  - TSMOM (proxy): reconstruct sign(SP500_R_60d) × SP500_R, vol-targeted
  - Long-US500 (proxy long-equity benchmark)

Common window: intersection of all series. Reported in deliverable.
NO weight optimization. Equal-risk-contrib (ERC) + inverse-vol weights.
Skew measured at HOLDING horizon per sleeve (not all daily).
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import skew as skw

VXX_PATH = "<HOME>/Desktop/Algo_claude/data/skew_research/session_cowork/series_Long-vol_VXX.csv"
US500_PATH = "<HOME>/Desktop/Algo_claude/data/skew_research/session_cowork/series_Long-US500.csv"
VIX_TS_PATH = "<HOME>/Desktop/Algo_claude/data/panels/vix_term_structure.csv"
NQ_DAILY = "<HOME>/Desktop/Algo_claude/data/overnight_research/nq_rth_daily.parquet"
NQ_PARQUET = "<HOME>/Desktop/Algo_claude/data/raw/NQ_1min_databento_2010-2026.parquet"
CAL_PATH = "<HOME>/Desktop/Algo_claude/data/panels/economic_calendar.csv"

# ============================================================
# 1. LOAD SLEEVES
# ============================================================
print("=" * 80)
print("LOADING SLEEVES")
print("=" * 80)

# --- Long-vol VXX (from session_cowork)
vxx = pd.read_csv(VXX_PATH)
vxx["Date"] = pd.to_datetime(vxx["Date"])
vxx = vxx.set_index("Date")["VXX"].rename("LONGVOL_VXX").sort_index()
print(f"LONGVOL_VXX:  n={len(vxx)}  {vxx.index.min().date()} → {vxx.index.max().date()}  "
      f"mean={vxx.mean()*1e4:+.1f}bp std={vxx.std()*1e4:.0f}bp skew={skw(vxx):+.2f}")

# --- Long-US500 (proxy long-equity)
us500 = pd.read_csv(US500_PATH)
us500["Date"] = pd.to_datetime(us500["Date"])
us500 = us500.set_index("Date")["US500"].rename("LONG_US500").sort_index()
print(f"LONG_US500:   n={len(us500)}  {us500.index.min().date()} → {us500.index.max().date()}")

# --- VIX-term timé (reconstruct from VIX/VIX3M + proxy VIXY return)
vts = pd.read_csv(VIX_TS_PATH)
vts["Date"] = pd.to_datetime(vts["Date"])
vts = vts.dropna(subset=["^VIX", "^VIX3M"]).set_index("Date").sort_index()
vts["ratio"] = vts["^VIX"] / vts["^VIX3M"]    # <1 contango, >1 backwardation
vts["vix_chg"] = vts["^VIX"].diff() / vts["^VIX"].shift(1)
# Signal at t-1 (lagged 1 day), trade at t close. Contango (<1) → short-vol = -vix_chg
# Backwardation (≥1) → long-vol = +vix_chg
vts["signal"] = np.where(vts["ratio"].shift(1) < 1, -1, +1)
vts["VIXTERM"] = vts["signal"] * vts["vix_chg"]
vixterm = vts["VIXTERM"].dropna().rename("VIXTERM")
print(f"VIXTERM:      n={len(vixterm)}  {vixterm.index.min().date()} → {vixterm.index.max().date()}  "
      f"mean={vixterm.mean()*1e4:+.1f}bp std={vixterm.std()*1e4:.0f}bp skew={skw(vixterm):+.2f}")

# --- MR reversal SPX (signal = -sign(R_{t-1}) × R_t)
mr_signal = -np.sign(us500.shift(1))
mr = (mr_signal * us500).dropna().rename("MR_REVERSAL")
print(f"MR_REVERSAL:  n={len(mr)}  {mr.index.min().date()} → {mr.index.max().date()}  "
      f"mean={mr.mean()*1e4:+.2f}bp std={mr.std()*1e4:.0f}bp skew={skw(mr):+.2f}  ⚠ artefact délai+1")

# --- Pré-FOMC (simplified: full RTH day return on FOMC days, from nq_rth_daily)
print("Building Pré-FOMC sleeve (full-day proxy from nq_rth_daily)...", flush=True)
nq_daily = pd.read_parquet(NQ_DAILY).reset_index()
nq_daily.columns = ["date", "o", "c", "pc", "ov_bps", "in_bps", "wd", "yr"]
nq_daily["date"] = pd.to_datetime(nq_daily["date"]).dt.normalize()
nq_daily = nq_daily.set_index("date").sort_index()
nq_daily["dret"] = nq_daily["c"] / nq_daily["pc"] - 1   # full-day return (close to close)
# FOMC calendar
cal = pd.read_csv(CAL_PATH)
fomc_dates = pd.to_datetime(cal[cal.event == "FOMC"]["date"]).dt.normalize()
print(f"  FOMC events available (2020+): {len(fomc_dates)}", flush=True)
# Build sleeve series: full-day NQ return on FOMC days, 0 elsewhere
prefomc_sleeve = pd.Series(0.0, index=nq_daily.index)
fomc_mask = nq_daily.index.isin(set(fomc_dates))
prefomc_sleeve.loc[fomc_mask] = nq_daily.loc[fomc_mask, "dret"]
prefomc_sleeve = prefomc_sleeve.dropna()
prefomc_sleeve.name = "PREFOMC"
n_events = (prefomc_sleeve != 0).sum()
print(f"PREFOMC:      n={len(prefomc_sleeve)}  events={n_events}  "
      f"{prefomc_sleeve.index.min().date()} → {prefomc_sleeve.index.max().date()}", flush=True)
event_only = prefomc_sleeve[prefomc_sleeve != 0]
print(f"  event-only:   mean={event_only.mean()*1e4:+.1f}bp/event  skew={skw(event_only):+.2f}  hit={(event_only>0).mean():.2%}", flush=True)
print(f"  full-series (with zeros): mean={prefomc_sleeve.mean()*1e4:+.2f}bp/day  std={prefomc_sleeve.std()*1e4:.0f}bp", flush=True)
print(f"  Note: 'full-day RTH NQ on FOMC' proxy (vs 'prior_close→14:00 ET' in session_3 — proxy more conservative)", flush=True)

# --- TSMOM (proxy = sign(SP500_R_60d) × SP500_R, vol-targeted)
us500_r = us500.copy()
us500_idx = (1 + us500_r).cumprod()
r60 = us500_idx.pct_change(60)
tsmom_signal = np.sign(r60)
vol30 = us500_r.rolling(30).std() * np.sqrt(252)
vol_target = 0.10  # 10% annualized
vol_scalar = (vol_target / vol30).clip(0, 2)
tsmom = (tsmom_signal.shift(1) * us500_r * vol_scalar.shift(1)).dropna().rename("TSMOM_PROXY")
print(f"TSMOM_PROXY:  n={len(tsmom)}  {tsmom.index.min().date()} → {tsmom.index.max().date()}  "
      f"mean={tsmom.mean()*1e4:+.2f}bp/day  std={tsmom.std()*1e4:.0f}bp  skew={skw(tsmom):+.2f}")

# ============================================================
# 2. ALIGN ON COMMON WINDOW
# ============================================================
print("\n" + "=" * 80)
print("ALIGNING ON COMMON WINDOW")
print("=" * 80)
all_s = pd.concat([vxx, vixterm, mr, prefomc_sleeve, tsmom, us500], axis=1)
all_s.columns = ["LONGVOL_VXX", "VIXTERM", "MR_REVERSAL", "PREFOMC", "TSMOM_PROXY", "LONG_US500"]
print(f"Pre-join coverage by series:")
for c in all_s.columns:
    s = all_s[c].dropna()
    print(f"  {c:18s}  n={len(s):>5d}  {s.index.min().date()} → {s.index.max().date()}")

# Common window = intersection where ALL series have data
common = all_s.dropna()
print(f"\n*** COMMON WINDOW: n={len(common)} days  {common.index.min().date()} → {common.index.max().date()}  "
      f"({(common.index.max() - common.index.min()).days/365.25:.1f} years) ***")

# ============================================================
# 3. CORRELATION MATRIX + SKEW AT HOLDING HORIZON
# ============================================================
print("\n" + "=" * 80)
print("CORRELATION MATRIX (common window)")
print("=" * 80)
corr = common.corr()
print(corr.round(3).to_string())

print("\nDaily skew per sleeve (common window):")
for c in common.columns:
    s = common[c]
    print(f"  {c:18s}  skew_daily = {skw(s):+.3f}  std_daily = {s.std()*1e4:>5.0f} bp  mean_daily = {s.mean()*1e4:>+5.2f} bp")

# Skew at holding horizon
print("\nSkew at HOLDING HORIZON (event/trade-level for event sleeves; weekly for daily continuous):")
print("  LONGVOL_VXX  — daily holding, daily skew already correct")
print("  VIXTERM      — daily rebalance, daily skew correct")
print("  MR_REVERSAL  — daily (1-day), daily correct ⚠ artefact délai+1")
print("  PREFOMC      — per-event (~7 events/yr): skew on event-only series:")
po_events = common["PREFOMC"][common["PREFOMC"] != 0]
print(f"    n={len(po_events)}  skew_per_event = {skw(po_events):+.3f}  mean_per_event = {po_events.mean()*1e4:+.1f} bp")
print("  TSMOM_PROXY  — held positions ~1-3 months; resample to monthly:")
tsmom_m = common["TSMOM_PROXY"].resample("ME").apply(lambda x: (1+x).prod() - 1).dropna()
print(f"    n_months={len(tsmom_m)}  skew_monthly = {skw(tsmom_m):+.3f}")

# ============================================================
# 4. PORTFOLIO CONSTRUCTION (simple weights, NO optimization)
# ============================================================
print("\n" + "=" * 80)
print("CANDIDATE PORTFOLIOS — simple weights only (ERC + inverse-vol)")
print("=" * 80)

# Inverse-vol weights (annualized)
def inv_vol_weights(df, cols):
    sub = df[cols]
    vols = sub.std() * np.sqrt(252)
    w = (1 / vols) / (1 / vols).sum()
    return w


def portfolio_metrics(df, weights, label, target_vol_ann=None):
    """Weighted sum, optionally vol-target."""
    p = (df[list(weights.index)] * weights.values).sum(axis=1)
    if target_vol_ann is not None:
        scale = target_vol_ann / (p.std() * np.sqrt(252))
        p = p * scale
    ann_ret = p.mean() * 252
    ann_vol = p.std() * np.sqrt(252)
    sr = ann_ret / ann_vol if ann_vol > 0 else np.nan
    cum = (1 + p).cumprod()
    dd = (cum / cum.cummax() - 1).min()
    worst_day = p.min()
    monthly = p.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    worst_month = monthly.min()
    return {
        "label": label,
        "ann_ret": ann_ret,
        "ann_vol": ann_vol,
        "sr": sr,
        "max_dd": dd,
        "worst_day": worst_day,
        "worst_month": worst_month,
        "skew_daily": skw(p),
        "skew_monthly": skw(monthly),
        "weights": weights.to_dict(),
        "returns": p,
    }

# Portfolios:
# P1: TSMOM only (the engine alone, benchmark)
# P2: TSMOM + PREFOMC (moteur + décorrélation)
# P3: TSMOM + LONGVOL_VXX (moteur + tail-hedge)
# P4: TSMOM + PREFOMC + LONGVOL_VXX (triple)
# P5: TSMOM + VIXTERM (alt for comparison; vixterm corr trend per cowork)

# Note: MR_REVERSAL EXCLU des recos déployables (artefact délai+1) — calculé pour info corr seulement.

portfolios = {}

# P1 baseline
w1 = pd.Series({"TSMOM_PROXY": 1.0})
portfolios["P1_TSMOM_only"] = portfolio_metrics(common, w1, "P1_TSMOM_only")

# P2 ERC TSMOM + PREFOMC (inverse-vol)
w2 = inv_vol_weights(common, ["TSMOM_PROXY", "PREFOMC"])
portfolios["P2_TSMOM+FOMC"] = portfolio_metrics(common, w2, "P2_TSMOM+FOMC")

# P3 ERC TSMOM + LONGVOL_VXX (inverse-vol)
w3 = inv_vol_weights(common, ["TSMOM_PROXY", "LONGVOL_VXX"])
portfolios["P3_TSMOM+VXX_invol"] = portfolio_metrics(common, w3, "P3_TSMOM+VXX_invol")

# P3b: TSMOM 90% + VXX 10% (small tail-hedge overlay as Cowork suggested)
w3b = pd.Series({"TSMOM_PROXY": 0.90, "LONGVOL_VXX": 0.10})
portfolios["P3b_TSMOM+VXX_10pct"] = portfolio_metrics(common, w3b, "P3b_TSMOM+VXX_10pct")

# P4 ERC triple
w4 = inv_vol_weights(common, ["TSMOM_PROXY", "PREFOMC", "LONGVOL_VXX"])
portfolios["P4_triple_invol"] = portfolio_metrics(common, w4, "P4_triple_invol")

# P4b: 80% TSMOM + 10% FOMC + 10% VXX
w4b = pd.Series({"TSMOM_PROXY": 0.80, "PREFOMC": 0.10, "LONGVOL_VXX": 0.10})
portfolios["P4b_TSMOM+FOMC+VXX_80_10_10"] = portfolio_metrics(common, w4b, "P4b_TSMOM+FOMC+VXX_80_10_10")

print(f"\n{'Portfolio':32s}{'AnnRet':>9s}{'AnnVol':>9s}{'Sharpe':>9s}{'MaxDD':>9s}{'WorstDay':>11s}{'WorstMon':>11s}{'Skew_d':>9s}{'Skew_m':>9s}")
for label, m in portfolios.items():
    print(f"{label:32s}{m['ann_ret']*100:>+8.2f}%{m['ann_vol']*100:>+8.2f}%{m['sr']:>9.2f}"
          f"{m['max_dd']*100:>+8.2f}%{m['worst_day']*100:>+10.2f}%{m['worst_month']*100:>+10.2f}%"
          f"{m['skew_daily']:>+9.2f}{m['skew_monthly']:>+9.2f}")
    print(f"  weights: {m['weights']}")

# ============================================================
# 5. TAIL-HEDGE DECISIVE TEST: DD evité × P(krach) vs portage payé
# ============================================================
print("\n" + "=" * 80)
print("TAIL-HEDGE DECISIVE TEST — long-vol VXX")
print("=" * 80)

# Define "crash days" as days where LONG_US500 ≤ p5 of its distribution
crash_threshold = common["LONG_US500"].quantile(0.05)
crash_days = common["LONG_US500"] <= crash_threshold
print(f"\n  Définition 'krach' : LONG_US500 ≤ p5 = {crash_threshold*100:.2f}% (n={crash_days.sum()} days, {crash_days.mean()*100:.1f}%)")

# What VXX returns on crash days vs non-crash
vxx_on_crash = common.loc[crash_days, "LONGVOL_VXX"].mean()
vxx_on_normal = common.loc[~crash_days, "LONGVOL_VXX"].mean()
vxx_total = common["LONGVOL_VXX"].mean()
print(f"  VXX mean return:")
print(f"    on crash days:   {vxx_on_crash*100:+.3f}%/day  ({crash_days.sum()} days)")
print(f"    on normal days:  {vxx_on_normal*100:+.3f}%/day  ({(~crash_days).sum()} days)")
print(f"    overall:         {vxx_total*100:+.3f}%/day  (the theta bleed)")

# TSMOM behavior on crash vs normal
tsmom_on_crash = common.loc[crash_days, "TSMOM_PROXY"].mean()
tsmom_on_normal = common.loc[~crash_days, "TSMOM_PROXY"].mean()
print(f"\n  TSMOM_PROXY mean return:")
print(f"    on crash days:   {tsmom_on_crash*100:+.3f}%/day")
print(f"    on normal days:  {tsmom_on_normal*100:+.3f}%/day")

# Cost-benefit of small 10% VXX overlay
total_days = len(common)
n_crash = crash_days.sum()
n_normal = total_days - n_crash
years = (common.index.max() - common.index.min()).days / 365.25

# Cost: 10% allocation × overall VXX return × all days
# Benefit: 10% × VXX_crash_return × n_crash, offsetting TSMOM crash loss
cost_annual = 0.10 * vxx_total * 252       # annual cost of holding 10% VXX
benefit_crash = 0.10 * vxx_on_crash * (n_crash / years)   # annual benefit on crash days
net_annual = 0.10 * vxx_total * 252       # this IS the total = cost + benefit, since benefit is "above zero" return

# Cleaner: compute the IMPACT of adding 10% VXX
ret_p1 = common["TSMOM_PROXY"]
ret_p3b = 0.9 * common["TSMOM_PROXY"] + 0.1 * common["LONGVOL_VXX"]
delta = ret_p3b - ret_p1
annual_drag = delta.mean() * 252
print(f"\n  IMPACT of adding 10% VXX to TSMOM:")
print(f"    Annual return drag/lift: {annual_drag*100:+.2f}%/year   (negative = pure cost)")
print(f"    Contribution to total over {years:.1f} years: {delta.sum()*100:+.2f}%")

# DD comparison
cum_p1 = (1 + ret_p1).cumprod(); dd_p1 = (cum_p1 / cum_p1.cummax() - 1).min()
cum_p3b = (1 + ret_p3b).cumprod(); dd_p3b = (cum_p3b / cum_p3b.cummax() - 1).min()
print(f"    MaxDD TSMOM only: {dd_p1*100:+.2f}%  →  MaxDD TSMOM+10%VXX: {dd_p3b*100:+.2f}%   (DD réduit de {abs(dd_p1-dd_p3b)*100:.2f}pp)")

# Worst-day reduction
print(f"    Worst day TSMOM only: {ret_p1.min()*100:+.2f}%  →  Worst day TSMOM+10%VXX: {ret_p3b.min()*100:+.2f}%")

# Tail-hedge breakeven: cost = benefit at crash frequency p_crash needed
# annual_cost_perc = 0.10 * (-vxx_total) * 252 (theta paid all year)
# annual_benefit_perc = 0.10 * (vxx_on_crash - vxx_normal) * n_crash/years  (excess return on crash)
annual_cost_pct = -0.10 * vxx_total * 252  # cost paid (positive if VXX bleeds)
annual_benefit_pct = 0.10 * (vxx_on_crash - vxx_on_normal) * (n_crash / years)
print(f"\n  Décomposition cost/benefit (10% VXX overlay):")
print(f"    Annual theta cost (full year):                   {annual_cost_pct*100:+.2f}%/year")
print(f"    Annual benefit on crash days (excess over norm): {annual_benefit_pct*100:+.2f}%/year")
print(f"    Net = benefit − cost:                            {(annual_benefit_pct - annual_cost_pct)*100:+.2f}%/year")
print(f"    → if net ≤ 0: tail-hedge plombe le portefeuille (assurance trop chère)")
print(f"    → if net > 0: tail-hedge rentable même hors-stress")

# ============================================================
# 6. FTMO 2-step MC: portfolio vs TSMOM only
# ============================================================
print("\n" + "=" * 80)
print("FTMO 2-step MC — portfolio vs TSMOM only")
print("=" * 80)

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


def generate_bootstrap(samples, n_paths, max_steps, block_size, rng):
    L = len(samples)
    n_blocks = (max_steps + block_size - 1) // block_size
    starts = rng.integers(0, max(1, L - block_size + 1), size=(n_paths, n_blocks))
    out = np.empty((n_paths, n_blocks * block_size), dtype=np.float64)
    for k in range(block_size):
        idx = np.clip(starts + k, 0, L - 1)
        out[:, k::block_size] = samples[idx]
    return out[:, :max_steps]


def simulate_phase(boot, sizing_pct, target_pct, account_init=ACCOUNT_INIT,
                   dll_pct=DLL_PCT, max_total_pct=MAX_TOTAL_PCT, min_trades=MIN_TRADES_PHASE):
    n_paths, max_steps = boot.shape
    # Here we interpret 'sizing' as the leverage applied to the daily portfolio return.
    pnl_pct = boot * sizing_pct  # leveraged daily return
    eq = 1.0 + np.cumsum(pnl_pct, axis=1)  # equity scaled to 1
    midnight = np.concatenate([np.ones((n_paths, 1)), eq[:, :-1]], axis=1)
    daily_dollar_pnl_norm = pnl_pct  # already normalized to account=1
    dll_breach = daily_dollar_pnl_norm <= -dll_pct * midnight
    floor = 1.0 - max_total_pct
    target = 1.0 + target_pct
    floor_breach = eq <= floor
    target_hit = eq >= target
    target_hit[:, :min_trades - 1] = False
    bust_step = np.where(dll_breach | floor_breach, np.arange(max_steps), max_steps + 1)
    bust_first = bust_step.min(axis=1)
    pass_step = np.where(target_hit, np.arange(max_steps), max_steps + 1)
    pass_first = pass_step.min(axis=1)
    passed = pass_first < bust_first
    return passed, pass_first + 1


def p_funded_mc(returns, leverage, seed_offset, block=BLOCK_SIZE):
    samples = returns.values
    rng = np.random.default_rng(RNG_SEED + seed_offset)
    boot1 = generate_bootstrap(samples, N_PATHS, MAX_STEPS, block, rng)
    p1_pass, p1_pass_step = simulate_phase(boot1, leverage, TARGET_P1)
    n_p1_pass = int(p1_pass.sum())
    if n_p1_pass == 0:
        return 0.0, 0.0
    boot2 = generate_bootstrap(samples, n_p1_pass, MAX_STEPS, block, rng)
    p2_pass, _ = simulate_phase(boot2, leverage, TARGET_P2)
    p_funded = (n_p1_pass / N_PATHS) * (p2_pass.mean())
    return p_funded, p1_pass.mean()


# Sizing here is leverage on daily portfolio % return. Choose levers that make the
# portfolio risk comparable to ORB-style sizings (1-2-3-5x leverage on the volatility).
print(f"\n{'Portfolio':32s}{'lev':>5s}{'p_funded':>11s}{'p1_pass':>11s}")
print("-" * 65)
ppass_rows = []
for label, m in portfolios.items():
    r = m["returns"]
    for lev in [1.0, 2.0, 3.0, 5.0]:
        pf, p1p = p_funded_mc(r, lev, seed_offset=int(lev * 100) + hash(label) % 10000)
        print(f"{label:32s}{lev:>5.1f}{pf*100:>10.1f}%{p1p*100:>10.1f}%")
        ppass_rows.append({"portfolio": label, "leverage": lev, "p_funded": pf, "p1_pass": p1p,
                           "ann_ret": m["ann_ret"], "ann_vol": m["ann_vol"], "sr": m["sr"],
                           "max_dd": m["max_dd"]})
    print()

pd.DataFrame(ppass_rows).to_csv("<HOME>/Desktop/Algo_claude/data/skew_research/MERGE_ppass.csv", index=False)
pd.DataFrame({k: v["returns"] for k, v in portfolios.items()}).to_csv(
    "<HOME>/Desktop/Algo_claude/data/skew_research/MERGE_portfolio_returns.csv")
corr.to_csv("<HOME>/Desktop/Algo_claude/data/skew_research/MERGE_correlations.csv")

print("\nSaved → MERGE_ppass.csv + MERGE_portfolio_returns.csv + MERGE_correlations.csv")

# Pré-FOMC since 2023 — recent decay check
print("\n" + "=" * 80)
print("PRÉ-FOMC — corrélations sur full window vs 2023-2026 (test décay)")
print("=" * 80)
recent = common[common.index >= "2023-01-01"]
print(f"  Full common: PRÉ-FOMC corrs vs others:")
print(common.corr()["PREFOMC"].round(3).to_string())
print(f"  2023+ ({len(recent)} days): PRÉ-FOMC corrs vs others:")
print(recent.corr()["PREFOMC"].round(3).to_string())
event_full = common["PREFOMC"][common["PREFOMC"] != 0]
event_recent = recent["PREFOMC"][recent["PREFOMC"] != 0]
print(f"\n  PRÉ-FOMC event-only mean (bp/event):")
print(f"    Full: n={len(event_full)}  mean={event_full.mean()*1e4:+.1f} bp")
print(f"    2023+: n={len(event_recent)}  mean={event_recent.mean()*1e4:+.1f} bp")
