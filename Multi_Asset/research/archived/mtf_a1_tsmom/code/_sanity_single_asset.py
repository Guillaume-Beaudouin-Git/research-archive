"""Sanity-test single-asset, single-horizon TSMOM on gold (GC=F).

If mechanics are right:
- Sharpe of sign(12m_cumret) TSMOM on GC=F over 2001-2025 should be in range
  [0.3, 0.7] (literature).
- Sharpe of BH (long-only same vol-target) on GC=F should be ~0.4-0.6 (gold ran 2000-2011).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "mtf_survey" / "raw"

# Load
df = pd.read_parquet(RAW / "prices_GC_F.parquet")
close = df["Close"].astype(float)
close.index = pd.to_datetime(close.index).tz_localize(None)
close = close.sort_index()
bd = pd.bdate_range(close.index.min(), close.index.max())
close = close.reindex(bd)

# Daily returns
ret = close.pct_change()

# 63d sigma annualized, lagged 1 day
sigma = ret.rolling(63).std() * np.sqrt(252)
sigma = sigma.shift(1)

# Signal: sign(252d cumret)
cumret_252 = close.pct_change(252)
S_daily = np.sign(cumret_252)

# Sample at month-end (BME)
S_eom = S_daily.resample("BME").last()
sigma_eom = sigma.resample("BME").last()

# Position: per-asset vol target 0.10, position = S × 0.10/σ
TGT = 0.10
pos_eom = S_eom * (TGT / sigma_eom)
pos_bh_eom = (TGT / sigma_eom)  # buy-hold version (always +1)

# Re-index forward by 1 BDay to apply next month
pos_eom_fwd = pos_eom.copy()
pos_eom_fwd.index = pos_eom_fwd.index + pd.offsets.BDay(1)
pos_bh_fwd = pos_bh_eom.copy()
pos_bh_fwd.index = pos_bh_fwd.index + pd.offsets.BDay(1)

pos_daily = pos_eom_fwd.reindex(bd, method="ffill").fillna(0)
pos_bh_daily = pos_bh_fwd.reindex(bd, method="ffill").fillna(0)

# Daily PnL
pnl_tsmom_d = pos_daily * ret
pnl_bh_d = pos_bh_daily * ret

# Monthly
pnl_tsmom_m = (1 + pnl_tsmom_d.fillna(0)).resample("ME").prod() - 1
pnl_bh_m = (1 + pnl_bh_d.fillna(0)).resample("ME").prod() - 1


def sharpe(x, ppy):
    x = x.dropna()
    if len(x) < 2 or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(ppy))


print("=== GC=F single-asset sanity (no costs) ===")
print(f"Sample: {pnl_tsmom_m.index.min().date()} → {pnl_tsmom_m.index.max().date()}, "
      f"N_months={pnl_tsmom_m.dropna().shape[0]}")
print(f"TSMOM 12m  Sharpe ann: {sharpe(pnl_tsmom_m, 12):.3f}")
print(f"BuyHold    Sharpe ann: {sharpe(pnl_bh_m, 12):.3f}")
print(f"TSMOM cumret final  : {pnl_tsmom_m.add(1).prod() - 1:.3f}")
print(f"BH    cumret final  : {pnl_bh_m.add(1).prod() - 1:.3f}")

# Check sign of recent few months
print("\nLast 6 months of S_eom + pos_eom + monthly pnl:")
combined = pd.DataFrame({
    "S_eom": S_eom,
    "sigma_eom": sigma_eom,
    "pos_eom": pos_eom,
    "pos_bh_eom": pos_bh_eom,
}).tail(6)
print(combined)
print("\nLast 6 months of pnl:")
print(pd.DataFrame({"tsmom": pnl_tsmom_m, "bh": pnl_bh_m}).tail(6))

# Sharpe over MOP overlap window 2000-2009
mask = (pnl_tsmom_m.index >= "2000-01-01") & (pnl_tsmom_m.index <= "2009-12-31")
print(f"\nOverlap 2001-2009 (signal valid):")
print(f"TSMOM Sharpe: {sharpe(pnl_tsmom_m[mask], 12):.3f}")
print(f"BH    Sharpe: {sharpe(pnl_bh_m[mask], 12):.3f}")
