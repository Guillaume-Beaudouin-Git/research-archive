"""
build_steelman.py — build the most generous reproducible sleeves ("steel-man") that
approximate the report's CLAIMED per-sleeve Sharpes, so the methodology gates (MC,
leverage, correlation) test the report's *intended* portfolio, not just the (failing)
literal spec.

  A* = long-only classic Connors (SMA200 + RSI2<10 + SMA5 exit) on indices-5, inverse-vol
       (the only config reaching ann~1.0 + positive-every-year on 2022-26).
  B* = BTC 120/60-min momentum, best reproducible config (~+0.5 OOS).
  C* = US30 MR, best reproducible config (~+1.0 OOS) within a US-session window.

Saves results/sleeve_{A,B,C}_steel.csv and prints faithful-vs-steelman-vs-report.
"""
from __future__ import annotations
import json
import numpy as np, pandas as pd
from audit_common import load_m1, metrics, per_year_sharpe, vol_target, ROOT
from sleeve_a_variants import build as build_a, IDX5
from sleeve_bc import build_bars, backtest

R = ROOT / "research/ftmo_portfolio_audit/results"
LO, HI, OLO = "2022-01-01", "2026-06-05", "2025-01-01"


def show(tag, net, claim):
    mf, mo = metrics(net.loc[LO:HI]), metrics(net.loc[OLO:HI])
    yr = per_year_sharpe(net.loc[LO:HI])
    print(f"  {tag:26s} full={mf['ann_sharpe']:+.2f} oos={mo['ann_sharpe']:+.2f} "
          f"kurt={mf['excess_kurtosis']:.1f} allyr+={all(v>0 for v in yr.values())}  "
          f"claim={claim}  yr={ {k:round(v,1) for k,v in yr.items()} }")
    return net


def main():
    print("Building steel-man sleeves ...", flush=True)
    # A*
    a = build_a(universe=IDX5, weight="invvol", side="long", regime="sma200",
                exit_mode="sma5", tz="EET", start=LO, end=HI)
    show("A* long-idx Connors", a, "report A ann~0.97 pos-every-yr")
    a.rename("net").to_csv(R / "sleeve_A_steel.csv")

    # B* — BTC momentum, search best cash-ish config
    btc = load_m1("BTCUSD", "panel")
    bestB = None
    for freq, w, ze, st in [("60min", 16, 2.5, 0.03), ("120min", 12, 2.5, 0.03),
                            ("60min", 16, 2.5, 0.02), ("60min", 24, 2.5, 0.03)]:
        bars = build_bars(btc, freq, 0, 21, drop_weekend=False)
        net = backtest(bars, "BTCUSD", "mom", window=w, z_entry=ze, daily_stop=st,
                       markup=2.0, commission_rt=0.00065)["net"]
        mo = metrics(net.loc[OLO:HI])["ann_sharpe"]
        if bestB is None or mo > bestB[0]:
            bestB = (mo, net, f"{freq} w{w} z{ze} st{st}")
    show(f"B* BTC mom [{bestB[2]}]", bestB[1], "report B net OOS~0.51")
    bestB[1].rename("net").to_csv(R / "sleeve_B_steel.csv")

    # C* — US30 MR, best within US session window (13-21)
    us30 = load_m1("US30", "deep")
    bestC = None
    for sess in [(13, 20), (13, 21), (14, 21)]:
        for freq, w, ze, st in [("60min", 16, 2.0, 0.02), ("60min", 24, 1.5, 0.02),
                                ("120min", 16, 1.5, 0.02), ("60min", 32, 1.5, 0.02)]:
            bars = build_bars(us30, freq, sess[0], sess[1], drop_weekend=True)
            net = backtest(bars, "US30", "mr", window=w, z_entry=ze, daily_stop=st, markup=2.0)["net"]
            mf = metrics(net.loc[LO:HI])["ann_sharpe"]
            mo = metrics(net.loc[OLO:HI])["ann_sharpe"]
            score = mf + mo                              # balance IS+OOS (report claims both positive)
            if bestC is None or score > bestC[0]:
                bestC = (score, net, f"sess{sess} {freq} w{w} z{ze} st{st}")
    show(f"C* US30 MR [{bestC[2]}]", bestC[1], "report C IS+0.76/OOS+1.00")
    bestC[1].rename("net").to_csv(R / "sleeve_C_steel.csv")

    # combined equal-weight (each already ~1%/day vol-targeted)
    A = pd.read_csv(R / "sleeve_A_steel.csv", index_col=0, parse_dates=True)["net"]
    B = bestB[1]; C = bestC[1]
    comb = pd.concat([A, B, C], axis=1, keys=["A", "B", "C"]).loc[LO:HI]
    print("\n  sleeve overlap (non-NaN days):", comb.dropna().shape[0],
          "| per-sleeve days:", {k: int(comb[k].notna().sum()) for k in comb})
    print("  pairwise corr (steel-man, full 2022-26):")
    print(comb.corr().round(3).to_string().replace("\n", "\n   "))
    ew = comb.fillna(0.0).mean(axis=1)
    mcomb = metrics(ew)
    print(f"\n  COMBINED equal-weight (L=1): ann_sharpe={mcomb['ann_sharpe']:.2f} "
          f"daily_sharpe={mcomb['daily_sharpe']:.3f} kurt={mcomb['excess_kurtosis']:.1f} "
          f"sigma_d={mcomb['sigma_daily']*100:.2f}%  (report: ann 1.39, kurt 6.3)")
    print("  per-year combined:", {k: round(v, 2) for k, v in per_year_sharpe(ew).items()})
    comb.to_csv(R / "sleeves_steel_combined.csv")
    json.dump({"B_cfg": bestB[2], "C_cfg": bestC[2], "combined": mcomb},
              open(R / "steelman_meta.json", "w"), indent=2, default=str)


if __name__ == "__main__":
    main()
