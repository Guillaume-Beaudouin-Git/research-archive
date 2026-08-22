"""Diagnostic-only: cross-check vs AQR using SINGLE-horizon 12m signal.

Purpose: validate that build mechanics match AQR original paper, separating
the multi-horizon vs single-horizon difference from any code bug.

This does NOT alter the spec (which remains multi-horizon {21,63,252}).
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("a1", str(ROOT / "code/mtf/a1_tsmom_multihorizon.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

# Single-horizon 12m signal
def signal_12m(panel):
    return np.sign(panel.pct_change(252))


panel, _ = mod.load_panel()
rets = mod.daily_returns(panel)
sigma = mod.vol_ex_ante_daily(rets)
S12 = signal_12m(panel)
eff = mod.compute_effective_start(panel, rets, sigma, S12)
print("effective_start (12m signal):", eff.date())

res = mod.run_portfolio(panel, rets, sigma, S12, effective_start=eff)
m_12m = res["monthly_net"]
print(f"Single-horizon 12m TSMOM Sharpe (full): {mod.sharpe_ann(m_12m, ppy=12):.3f}")

# AQR cross-check
aqr_csv = ROOT / "data/mtf_survey/raw/aqr_tsmom_sheet_TSMOM_factors.csv"
aqr_df = pd.read_csv(aqr_csv, skiprows=11)
aqr_df["DATE"] = pd.to_datetime(aqr_df["DATE"])
aqr_df = aqr_df.set_index("DATE").sort_index()
aqr_factors = aqr_df[["TSMOM", "TSMOM^EQ", "TSMOM^FX", "TSMOM^FI", "TSMOM^CM"]].astype(float)
aqr_factors.index = aqr_factors.index + pd.offsets.MonthEnd(0)

m_12m_eom = m_12m.copy()
m_12m_eom.index = m_12m_eom.index + pd.offsets.MonthEnd(0)
joined = pd.concat([m_12m_eom.rename("us12"), aqr_factors], axis=1).dropna()

print(f"\nOverlap: {joined.index.min().date()} → {joined.index.max().date()} (n={joined.shape[0]})")
print("Correlation us(12m, aggregate) vs AQR aggregate TSMOM:",
      f"{joined['us12'].corr(joined['TSMOM']):.4f}")
print("\nCorrelation us(12m, aggregate) vs each AQR sleeve:")
for sleeve in ["TSMOM^EQ", "TSMOM^FX", "TSMOM^FI", "TSMOM^CM"]:
    print(f"  {sleeve}: {joined['us12'].corr(joined[sleeve]):.4f}")

# Now: per-sleeve replication
classes = {
    "equity": ["ES=F", "NQ=F", "YM=F", "RTY=F"],
    "fx":     ["6E=F", "6J=F", "6B=F", "6A=F", "6C=F", "6S=F"],
    "fi":     ["ZT=F", "ZF=F", "ZN=F", "ZB=F"],
    "commod": ["CL=F", "NG=F", "GC=F", "SI=F", "HG=F", "ZC=F", "ZW=F", "ZS=F", "KC=F", "SB=F"],
}
sleeve_map = {"equity": "TSMOM^EQ", "fx": "TSMOM^FX", "fi": "TSMOM^FI", "commod": "TSMOM^CM"}

print("\nPer-sleeve replication using 12m signal:")
for sleeve_name, tickers in classes.items():
    tickers_in = [t for t in tickers if t in panel.columns]
    sub_panel = panel[tickers_in].copy()
    sub_rets = sub_panel.pct_change()
    sub_sigma = mod.vol_ex_ante_daily(sub_rets)
    sub_S = np.sign(sub_panel.pct_change(252))
    sub_eff = mod.compute_effective_start(sub_panel, sub_rets, sub_sigma, sub_S)
    sub_res = mod.run_portfolio(sub_panel, sub_rets, sub_sigma, sub_S, effective_start=sub_eff)
    sub_m = sub_res["monthly_net"]
    sub_m_eom = sub_m.copy()
    sub_m_eom.index = sub_m_eom.index + pd.offsets.MonthEnd(0)
    sleeve_aqr_col = sleeve_map[sleeve_name]
    j = pd.concat([sub_m_eom.rename("us"), aqr_factors[sleeve_aqr_col]], axis=1).dropna()
    if j.empty:
        print(f"  {sleeve_name} ({sleeve_aqr_col}): NO OVERLAP")
        continue
    corr = j["us"].corr(j[sleeve_aqr_col])
    us_sr = mod.sharpe_ann(j["us"], ppy=12)
    aqr_sr = mod.sharpe_ann(j[sleeve_aqr_col], ppy=12)
    print(f"  {sleeve_name:7s} ({sleeve_aqr_col}, n_inst={len(tickers_in)}): "
          f"corr={corr:.3f} | us_SR={us_sr:.2f} | aqr_SR={aqr_sr:.2f} | n={j.shape[0]}")

print("\n=== DONE ===")
