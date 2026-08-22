"""Debug the 2nd-stage vol-target scale on the multi-asset engine."""
from __future__ import annotations
import sys
sys.path.insert(0, str((__file__.rsplit("/", 1)[0])))
import importlib.util
spec = importlib.util.spec_from_file_location("a1", __file__.rsplit("/", 1)[0] + "/a1_tsmom_multihorizon.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

import numpy as np
import pandas as pd

panel, meta = mod.load_panel()
rets = mod.daily_returns(panel)
sigma = mod.vol_ex_ante_daily(rets)
S = mod.signal_tsmom_daily(panel)

pos_eom = mod.build_monthly_positions(panel, rets, sigma, S)
print("pos_eom shape:", pos_eom.shape)
print("First valid pos_eom rows:")
print(pos_eom.dropna(how="all").head(3).round(3))

pos_daily_pre = mod.daily_position_from_monthly(pos_eom, panel.index)
print("\nDaily total |pos| at a few dates:")
abspos = pos_daily_pre.abs().sum(axis=1)
print(abspos.dropna().head(10))
print(abspos.dropna().tail(5))

sd_eom = mod.realized_port_vol_monthly(pos_daily_pre, rets)
print("\nrealized monthly vol (ann.):")
print(sd_eom.dropna().head(10))
print(sd_eom.dropna().describe())

scale_eom = mod.vol_target_scale_monthly(sd_eom)
print("\nscale:")
print(scale_eom.dropna().head(10))
print(scale_eom.dropna().describe())

# Check gross daily series after scale applied
scale_eom_applied = scale_eom.copy()
scale_eom_applied.index = scale_eom_applied.index + pd.offsets.BDay(1)
scale_daily = scale_eom_applied.reindex(panel.index, method="ffill").fillna(0)
scaled_pos = pos_daily_pre.mul(scale_daily, axis=0)
gross_daily = (scaled_pos * rets).sum(axis=1)
gross_monthly = (1 + gross_daily.fillna(0)).resample("ME").prod() - 1

print("\ngross monthly first 12 valid:")
gm_v = gross_monthly[gross_monthly != 0]
print(gm_v.head(12))
print(f"\ngross Sharpe ann (all): {gm_v.mean()/gm_v.std()*np.sqrt(12):.3f}")
print(f"gross Sharpe ann post-2002: "
      f"{gm_v[gm_v.index>='2002-01-01'].mean()/gm_v[gm_v.index>='2002-01-01'].std()*np.sqrt(12):.3f}")
print(f"gross Sharpe ann 2002-2009 (AQR overlap): "
      f"{gm_v[(gm_v.index>='2002-01-01')&(gm_v.index<='2009-12-31')].mean()/gm_v[(gm_v.index>='2002-01-01')&(gm_v.index<='2009-12-31')].std()*np.sqrt(12):.3f}")
