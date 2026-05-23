"""
FX Carry + Momentum Feasibility (G10 FX)
=========================================
Signals FX-1 (Carry), FX-2 (Momentum), FX-3 (Combo)
DSR: n_tests_so_far = 53 (crypto journal)
     this script adds: +3 (carry, momentum, combo)

Literature:
  Carry: Lustig & Verdelhan (2007) "The Cross-Section of Foreign Currency
         Risk Premia and Consumption Growth Risk" — JF
         Koijen et al. (2018) "Carry" — JFE
         Expected IC ~0.08-0.15 weekly; Sharpe ~0.4-0.8 standalone
  Mom:   Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum" — JFE
         Menkhoff et al. (2012) "Currency Momentum Strategies" — JFE
         Expected IC ~0.04-0.10 weekly; Sharpe ~0.4-0.7 standalone
  Combo: Koijen et al. (2018) combined carry+momentum ~0.8-1.2 Sharpe

Universe: G10 FX — EUR GBP AUD NZD CAD JPY CHF NOK SEK (9 non-USD)
Data:     yfinance weekly Close, 2010-01 → 2026-05
Cost:     0.01% RT (major FX: ~0.5-1 pip on 1.20 = 0.004-0.008%)
          52 trades/yr × 0.01% = 0.52%/yr → NOT binding

Feasibility gate:
  IC t-stat > 2.0 → PASS  (proceed to full walk-forward backtest)
  IC t-stat 1.5–2.0 → WEAK (proceed with caution, need better proxy)
  IC t-stat < 1.5 → SKIP

Carry proxy approach:
  carry_t = foreign_policy_rate_t - USD_policy_rate_t
  Using annual-average central bank policy rates (well-documented).
  This is a blunt proxy vs. actual 3M forward premium, but sufficient
  for IC feasibility. If IC passes, full backtest will use better rate data.
"""

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════
START = "2010-01-01"
END   = "2026-05-01"

# All prices standardised to "USD per 1 unit of foreign currency"
# EURUSD=X → 1 EUR = X USD → already correct
# USDCAD=X → 1 USD = X CAD → invert to get USD per CAD
PAIR_MAP = {
    'EUR': ('EURUSD=X', False),
    'GBP': ('GBPUSD=X', False),
    'AUD': ('AUDUSD=X', False),
    'NZD': ('NZDUSD=X', False),
    'CAD': ('USDCAD=X', True),   # invert
    'JPY': ('USDJPY=X', True),   # invert
    'CHF': ('USDCHF=X', True),   # invert
    'NOK': ('USDNOK=X', True),   # invert
    'SEK': ('USDSEK=X', True),   # invert
}

# Approximate annual-average central bank policy rates (%)
# Sources: Fed (FOMC), ECB, BOE, RBA, RBNZ, BOC, BOJ, SNB, Norges Bank, Riksbank
# Precision sufficient for cross-sectional ranking (relative ordering matters)
RATES_PCT = {
    'USD': {2010: 0.25, 2011: 0.25, 2012: 0.25, 2013: 0.25, 2014: 0.25,
            2015: 0.38, 2016: 0.63, 2017: 1.25, 2018: 2.38, 2019: 1.88,
            2020: 0.25, 2021: 0.25, 2022: 3.13, 2023: 5.38, 2024: 5.38,
            2025: 4.50, 2026: 4.50},
    'EUR': {2010: 1.00, 2011: 1.25, 2012: 0.75, 2013: 0.25, 2014: 0.05,
            2015: 0.05, 2016: 0.00, 2017: 0.00, 2018: 0.00, 2019: 0.00,
            2020: 0.00, 2021: 0.00, 2022: 0.50, 2023: 4.00, 2024: 3.50,
            2025: 2.50, 2026: 2.00},
    'GBP': {2010: 0.50, 2011: 0.50, 2012: 0.50, 2013: 0.50, 2014: 0.50,
            2015: 0.50, 2016: 0.25, 2017: 0.50, 2018: 0.75, 2019: 0.75,
            2020: 0.10, 2021: 0.10, 2022: 2.25, 2023: 5.25, 2024: 5.00,
            2025: 4.50, 2026: 4.25},
    'AUD': {2010: 4.50, 2011: 4.75, 2012: 3.25, 2013: 2.50, 2014: 2.50,
            2015: 2.00, 2016: 1.50, 2017: 1.50, 2018: 1.50, 2019: 1.00,
            2020: 0.25, 2021: 0.10, 2022: 2.35, 2023: 4.35, 2024: 4.35,
            2025: 4.10, 2026: 3.85},
    'NZD': {2010: 3.00, 2011: 2.50, 2012: 2.50, 2013: 2.50, 2014: 3.50,
            2015: 2.75, 2016: 1.75, 2017: 1.75, 2018: 1.75, 2019: 1.00,
            2020: 0.25, 2021: 0.25, 2022: 3.50, 2023: 5.50, 2024: 5.25,
            2025: 3.75, 2026: 3.25},
    'CAD': {2010: 1.00, 2011: 1.00, 2012: 1.00, 2013: 1.00, 2014: 1.00,
            2015: 0.50, 2016: 0.50, 2017: 1.00, 2018: 1.75, 2019: 1.75,
            2020: 0.25, 2021: 0.25, 2022: 3.75, 2023: 5.00, 2024: 4.50,
            2025: 3.00, 2026: 2.75},
    'JPY': {2010: 0.10, 2011: 0.10, 2012: 0.10, 2013: 0.10, 2014: 0.10,
            2015: 0.10, 2016:-0.10, 2017:-0.10, 2018:-0.10, 2019:-0.10,
            2020:-0.10, 2021:-0.10, 2022:-0.10, 2023:-0.10, 2024: 0.10,
            2025: 0.50, 2026: 0.75},
    'CHF': {2010: 0.25, 2011: 0.00, 2012: 0.00, 2013: 0.00, 2014:-0.25,
            2015:-0.75, 2016:-0.75, 2017:-0.75, 2018:-0.75, 2019:-0.75,
            2020:-0.75, 2021:-0.75, 2022:-0.25, 2023: 1.75, 2024: 1.25,
            2025: 0.50, 2026: 0.25},
    'NOK': {2010: 2.00, 2011: 2.25, 2012: 1.50, 2013: 1.50, 2014: 1.50,
            2015: 0.75, 2016: 0.50, 2017: 0.50, 2018: 1.00, 2019: 1.50,
            2020: 0.00, 2021: 0.25, 2022: 2.75, 2023: 4.50, 2024: 4.50,
            2025: 4.25, 2026: 3.75},
    'SEK': {2010: 1.25, 2011: 2.00, 2012: 1.00, 2013: 0.75, 2014: 0.00,
            2015:-0.10, 2016:-0.50, 2017:-0.50, 2018:-0.25, 2019: 0.00,
            2020: 0.00, 2021: 0.00, 2022: 2.50, 2023: 4.00, 2024: 3.50,
            2025: 2.50, 2026: 2.00},
}

MOM_WEEKS_LONG  = 52   # 12M lookback (avoid-short-reversal version)
MOM_WEEKS_SKIP  = 4    # skip most recent 1M (reduces reversal noise)

OUT_IC_PNG = "Forex/research/fx_carry_momentum_ic.png"


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def cross_sectional_ic(signal_df: pd.DataFrame,
                        fwd_ret_df: pd.DataFrame) -> pd.Series:
    """
    Weekly cross-sectional IC (Spearman).
    signal_df : (weeks × currencies) — computed at end of week T
    fwd_ret_df: (weeks × currencies) — return of week T+1
    Both indexed identically. Returns Series of ICs indexed by date.
    """
    dates = signal_df.index.intersection(fwd_ret_df.index)
    ics, idx = [], []
    for d in dates:
        sig = signal_df.loc[d].dropna()
        ret = fwd_ret_df.loc[d].dropna()
        common = sig.index.intersection(ret.index)
        if len(common) < 4:
            continue
        rho, _ = stats.spearmanr(sig[common].values, ret[common].values)
        ics.append(rho)
        idx.append(d)
    return pd.Series(ics, index=idx)


def ic_summary(ic_series: pd.Series) -> dict:
    ic = ic_series.dropna()
    mean, std, n = ic.mean(), ic.std(), len(ic)
    t = mean / (std / np.sqrt(n)) if std > 0 and n > 0 else 0.0
    ir = mean / std if std > 0 else 0.0
    gate = 'PASS' if t > 2.0 else ('WEAK' if t > 1.5 else 'SKIP')
    return {'IC_mean': mean, 'IC_std': std, 'IC_IR': ir,
            't_stat': t, 'n_weeks': n, 'gate': gate}


def zscore_xsection(df: pd.DataFrame) -> pd.DataFrame:
    """Row-wise z-score (cross-sectional normalisation)."""
    mu  = df.mean(axis=1)
    sig = df.std(axis=1)
    return df.sub(mu, axis=0).div(sig.replace(0, np.nan), axis=0)


# ══════════════════════════════════════════════════════════════════════
# 1. DOWNLOAD & CLEAN FX DATA
# ══════════════════════════════════════════════════════════════════════
print("=" * 62)
print("FX Carry + Momentum Feasibility — G10 FX, weekly 2010-2026")
print("=" * 62)
print("\n[1] Downloading G10 FX data from yfinance …")

tickers = [v[0] for v in PAIR_MAP.values()]
raw = yf.download(tickers, start=START, end=END, interval='1wk',
                  auto_adjust=True, progress=False)

# Handle yfinance column structure (MultiIndex or flat)
if isinstance(raw.columns, pd.MultiIndex):
    close_raw = raw['Close']
else:
    close_raw = raw  # single ticker fallback (shouldn't happen here)

# Build standardised USD-per-foreign price matrix
spot = {}
for ccy, (ticker, invert) in PAIR_MAP.items():
    if ticker not in close_raw.columns:
        print(f"  WARNING: {ticker} not found, skipping {ccy}")
        continue
    px = close_raw[ticker].dropna()
    spot[ccy] = 1.0 / px if invert else px

spot_df = pd.DataFrame(spot)
spot_df.index = pd.to_datetime(spot_df.index)
spot_df = spot_df.resample('W-FRI').last().dropna(how='all')

# Forward 1-week log return: computed at week T, reflects week T+1 return
# shift(-1) pushes next-week return to align with current-week signal date
log_spot = np.log(spot_df)
ret_1w   = log_spot.diff(1).shift(-1)   # next-week return, aligned to signal date

print(f"  Period: {spot_df.index[0].date()} → {spot_df.index[-1].date()}")
print(f"  Weeks:  {len(spot_df)} | Currencies: {spot_df.shape[1]}")
print(f"  Pairs:  {list(spot_df.columns)}")


# ══════════════════════════════════════════════════════════════════════
# 2. CARRY SIGNAL (FX-1)
#    carry(ccy, t) = policy_rate(ccy, year(t)) - policy_rate(USD, year(t))
#    Rationale: UIP empirically fails (forward premium puzzle). High-yield
#    currencies do NOT depreciate as UIP predicts → carry is collectible.
# ══════════════════════════════════════════════════════════════════════
print("\n[2] Computing carry signal (FX-1) …")

carry_rows = []
for dt in spot_df.index:
    yr  = dt.year
    usd = RATES_PCT['USD'].get(yr, np.nan)
    row = {}
    for ccy in spot_df.columns:
        foreign = RATES_PCT.get(ccy, {}).get(yr, np.nan)
        row[ccy] = foreign - usd if not (np.isnan(foreign) or np.isnan(usd)) else np.nan
    carry_rows.append(row)

carry_df = pd.DataFrame(carry_rows, index=spot_df.index)

carry_ic  = cross_sectional_ic(carry_df, ret_1w)
carry_stats = ic_summary(carry_ic)

print(f"  IC={carry_stats['IC_mean']:+.4f}  std={carry_stats['IC_std']:.4f}  "
      f"t={carry_stats['t_stat']:+.2f}  n={carry_stats['n_weeks']}  "
      f"→ {carry_stats['gate']}")


# ══════════════════════════════════════════════════════════════════════
# 3. MOMENTUM SIGNAL (FX-2)
#    Cross-sectional version: rank(ret_12M - ret_1M) vs forward 1-week
#    Time-series version:     sign(ret_12M - ret_1M) = TSMOM direction
#    Rationale: Moskowitz (2012) documented on 58 futures including FX.
#    Menkhoff (2012) documented on 48 currencies.
#    12M-1M avoids 1M reversal; standard in literature.
# ══════════════════════════════════════════════════════════════════════
print("\n[3] Computing momentum signal (FX-2) …")

# 12M-1M lookback (annualised at weekly frequency)
mom_signal = (log_spot.shift(MOM_WEEKS_SKIP)
              - log_spot.shift(MOM_WEEKS_LONG))

# Cross-sectional: rank of momentum signal across currencies
cs_mom_ic     = cross_sectional_ic(mom_signal, ret_1w)
cs_mom_stats  = ic_summary(cs_mom_ic)

# Time-series: sign of momentum (binary long/short per currency)
ts_mom_signal = np.sign(mom_signal)
ts_mom_ic     = cross_sectional_ic(ts_mom_signal, ret_1w)
ts_mom_stats  = ic_summary(ts_mom_ic)

print(f"  CS-Momentum: IC={cs_mom_stats['IC_mean']:+.4f}  "
      f"t={cs_mom_stats['t_stat']:+.2f}  → {cs_mom_stats['gate']}")
print(f"  TS-Momentum: IC={ts_mom_stats['IC_mean']:+.4f}  "
      f"t={ts_mom_stats['t_stat']:+.2f}  → {ts_mom_stats['gate']}")


# ══════════════════════════════════════════════════════════════════════
# 4. CARRY + MOMENTUM COMBO (FX-3)
#    Z-score normalise both, equal weight.
#    Literature: combination dominates standalone (Koijen et al. 2018,
#    Table 5). Low carry-momentum correlation in FX (~0.1-0.2).
# ══════════════════════════════════════════════════════════════════════
print("\n[4] Computing carry + momentum combo (FX-3) …")

# Align to common index
common_idx = carry_df.index.intersection(mom_signal.index)
carry_z  = zscore_xsection(carry_df.loc[common_idx])
mom_z    = zscore_xsection(mom_signal.loc[common_idx])
combo_df = carry_z.add(mom_z, fill_value=0)

combo_ic    = cross_sectional_ic(combo_df, ret_1w)
combo_stats = ic_summary(combo_ic)

print(f"  Carry+Mom: IC={combo_stats['IC_mean']:+.4f}  "
      f"t={combo_stats['t_stat']:+.2f}  → {combo_stats['gate']}")

# Carry-momentum signal correlation (want low to confirm diversification)
carry_flat = carry_df.loc[common_idx].values.flatten()
mom_flat   = mom_signal.loc[common_idx].values.flatten()
mask       = ~(np.isnan(carry_flat) | np.isnan(mom_flat))
corr_cm    = np.corrcoef(carry_flat[mask], mom_flat[mask])[0, 1]
print(f"  Carry vs Momentum cross-signal correlation: {corr_cm:+.3f}")


# ══════════════════════════════════════════════════════════════════════
# 5. ROLLING IC STABILITY CHART
# ══════════════════════════════════════════════════════════════════════
print("\n[5] Generating rolling IC chart …")

fig, axes = plt.subplots(3, 1, figsize=(14, 11))
fig.suptitle("G10 FX — Carry & Momentum Feasibility\n"
             "Cross-sectional Spearman IC vs 1-week forward return",
             fontsize=13, fontweight='bold')

panels = [
    ('Carry (policy rate differential)',    carry_ic,   carry_stats,   'steelblue'),
    ('Momentum (12M–1M, CS rank)',          cs_mom_ic,  cs_mom_stats,  'darkorange'),
    ('Combo (carry + momentum, Z-score)',   combo_ic,   combo_stats,   'seagreen'),
]

for ax, (name, ic_s, s, color) in zip(axes, panels):
    rolling = ic_s.rolling(52, min_periods=26).mean()
    ax.axhline(0, color='black', lw=0.8, zorder=3)
    ax.fill_between(ic_s.index, ic_s, 0,
                    where=ic_s > 0, alpha=0.12, color='green')
    ax.fill_between(ic_s.index, ic_s, 0,
                    where=ic_s < 0, alpha=0.12, color='red')
    ax.plot(ic_s,    color='lightgray', lw=0.7, label='Weekly IC', zorder=2)
    ax.plot(rolling, color=color, lw=2.0, label='52-wk rolling IC', zorder=4)
    gate_color = {'PASS': 'darkgreen', 'WEAK': 'darkorange', 'SKIP': 'red'}[s['gate']]
    ax.set_title(f"{name}  |  IC={s['IC_mean']:+.4f}  "
                 f"t={s['t_stat']:+.2f}  n={s['n_weeks']}wks  "
                 f"→ [{s['gate']}]",
                 fontsize=10,
                 color=gate_color,
                 fontweight='bold')
    ax.legend(loc='upper right', fontsize=8)
    ax.set_ylabel('Spearman IC')
    ax.grid(True, alpha=0.25)
    ax.set_xlim(ic_s.index[0], ic_s.index[-1])

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(OUT_IC_PNG, dpi=130, bbox_inches='tight')
plt.close()
print(f"  Saved: {OUT_IC_PNG}")


# ══════════════════════════════════════════════════════════════════════
# 6. SUMMARY TABLE
# ══════════════════════════════════════════════════════════════════════
print("\n" + "═" * 68)
print("FEASIBILITY SUMMARY — G10 FX, weekly, 2010-2026")
print("═" * 68)
print(f"  {'Signal':<30} {'IC_mean':>8} {'IC_std':>8} {'t_stat':>8} {'n_wks':>6}  GATE")
print("  " + "─" * 64)
for label, s in [
    ("FX-1  Carry (CS)",              carry_stats),
    ("FX-2a Momentum CS rank",        cs_mom_stats),
    ("FX-2b Momentum TS sign",        ts_mom_stats),
    ("FX-3  Carry + Momentum combo",  combo_stats),
]:
    gate_str = {'PASS': '✓ PASS', 'WEAK': '~ WEAK', 'SKIP': '✗ SKIP'}[s['gate']]
    print(f"  {label:<30} {s['IC_mean']:>+8.4f} {s['IC_std']:>8.4f} "
          f"{s['t_stat']:>8.2f} {s['n_weeks']:>6}  {gate_str}")

print()
print("Cost floor:")
print("  FX major pairs: ~0.5–1 pip spread ≈ 0.004–0.008% one-way")
print("  Conservative: 0.01% RT → 52 trades/yr × 0.01% = 0.52%/yr")
print("  vs. expected gross Sharpe ~0.4–1.2 → cost is NOT binding")
print()
print("Carry-Momentum cross-signal correlation: "
      f"{corr_cm:+.3f} (low = good diversification)")
print()
print("DSR note:")
print(f"  Crypto signals: 53  |  This script: +4  |  Running total: 57")
print("  DSR adjustment will be applied in full backtest if carry/mom pass.")
print("═" * 68)
