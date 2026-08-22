"""
sleeve_bc.py — INDEPENDENT regeneration of the intraday banded-z sleeves (REPORT §4).

Sleeve B — BTCUSD 120-min MOMENTUM: long z>+2 / short z<-2, exit |z|<0.5; window 00-21 UTC;
           intraday-flat; 2% daily-stop; cost = MT5 spread×markup + 0.065% RT commission.
Sleeve C — US30 60-min MEAN-REVERSION (fade): long z<-2 / short z>+2, exit |z|<0.5; US cash
           13-20 UTC; intraday-flat; 2% daily-stop; cost = real spread×markup (survives 4×).
z = (logP - SMA_16(logP)) / rolling_std_16 (causal). Decide at t, trade at t+1 (L1).
Each sleeve causally vol-targeted to ~1%/day (63d trailing, cap 4x).

Data tz (Gate 1): US30 from deep_history_utc = TRUE UTC; BTC from MT5 panel = EET -> converted
to true UTC (binance true-UTC variant also built for cross-check / Sleeve-B robustness).

Outputs: results/sleeve_{B,C}_daily.csv + results/sleeve_bc_metrics.json
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from audit_common import load_m1, point_size, metrics, vol_target, per_year_sharpe, ROOT


def build_bars(m1: pd.DataFrame, freq: str, h0: int, h1: int, drop_weekend: bool) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "spread": "mean"}
    bars = m1.resample(freq, label="right", closed="right").agg(agg).dropna(subset=["close"])
    h = bars.index.hour
    mask = (h >= h0) & (h < h1)
    if drop_weekend:
        mask &= bars.index.dayofweek < 5
    bars = bars[mask].copy()
    bars["logret"] = np.log(bars["close"]).diff()
    new_day = bars.index.normalize() != pd.Series(bars.index.normalize()).shift(1).values
    bars.loc[new_day, "logret"] = np.nan
    return bars


def banded_position(z: pd.Series, day_id, z_entry, z_exit, mode) -> pd.Series:
    raw = pd.Series(np.nan, index=z.index)
    if mode == "mr":           # fade: buy when too low
        raw[z < -z_entry] = 1.0
        raw[z > z_entry] = -1.0
    else:                      # momentum: buy when breaking up
        raw[z > z_entry] = 1.0
        raw[z < -z_entry] = -1.0
    raw[z.abs() < z_exit] = 0.0
    return raw.groupby(day_id).ffill().fillna(0.0)


def backtest(bars: pd.DataFrame, sym: str, mode: str, window: int = 16,
             z_entry=2.0, z_exit=0.5, daily_stop=0.02, markup=2.0, commission_rt=0.0,
             sigma_target=0.01, vol_lb=63, cap=4.0, exec_lag=0) -> dict:
    b = bars.copy()
    logp = np.log(b["close"])
    mean = logp.rolling(window).mean()
    sd = logp.rolling(window).std(ddof=0)
    b["z"] = (logp - mean) / sd.replace(0, np.nan)
    day_id = b.index.normalize().values
    pos_state = banded_position(b["z"], day_id, z_entry, z_exit, mode)
    last_of_day = pd.Series(b.index.normalize()).shift(-1).values != b.index.normalize()
    pos_state[last_of_day] = 0.0
    pos = pos_state.shift(1 + exec_lag).fillna(0.0)        # +1 causal; exec_lag adds execution delay
    ret = b["logret"].fillna(0.0)

    # intraday daily-stop: cumulative same-day unit PnL <= -daily_stop -> flat rest of day
    prov = pos * ret
    cum = prov.groupby(day_id).cumsum()
    breached = (cum <= -daily_stop)
    flat_after = (breached.groupby(day_id).cumsum().groupby(day_id).shift(1).fillna(0.0) >= 1)
    pos = pos.where(~flat_after, 0.0)

    gross_bar = pos * ret
    pt = point_size(sym)
    rt_cost = b["spread"].fillna(b["spread"].median()) * pt * markup / b["close"] + commission_rt
    turnover = (pos - pos.shift(1).fillna(0.0)).abs()
    cost_bar = turnover * 0.5 * rt_cost

    g_daily = gross_bar.groupby(day_id).sum()
    c_daily = cost_bar.groupby(day_id).sum().reindex(g_daily.index).fillna(0.0)
    g_daily.index = pd.to_datetime(g_daily.index)
    c_daily.index = pd.to_datetime(c_daily.index)
    trail = g_daily.rolling(vol_lb).std().shift(1)
    scale = (sigma_target / trail).clip(upper=cap).fillna(0.0)
    net = ((g_daily - c_daily) * scale).dropna()
    return {"net": net, "gross_daily": g_daily, "turnover_per_day": float(turnover.groupby(day_id).sum().mean())}


def window_metrics(net, lo, hi):
    s = net.loc[lo:hi]
    return metrics(s), per_year_sharpe(s)


def main():
    out = {}
    R = ROOT / "research/ftmo_portfolio_audit/results"

    # ---- Sleeve C: US30 60-min MR, deep (true UTC), cash 13-20 UTC ----
    print("[C] loading US30 deep M1 (true UTC) ...", flush=True)
    us30 = load_m1("US30", "deep")
    barsC = build_bars(us30, "60min", 13, 20, drop_weekend=True)
    print(f"    bars={len(barsC)}  {barsC.index.min()} -> {barsC.index.max()}", flush=True)
    resC = backtest(barsC, "US30", "mr", markup=2.0, commission_rt=0.0)
    netC = resC["net"]
    netC.rename("net").to_csv(R / "sleeve_C_daily.csv")
    mC, yC = window_metrics(netC, "2022-01-01", "2026-06-05")
    mC_o, _ = window_metrics(netC, "2025-01-01", "2026-06-05")
    # 4x spread stress
    resC4 = backtest(barsC, "US30", "mr", markup=4.0)
    mC4, _ = window_metrics(resC4["net"], "2022-01-01", "2026-06-05")
    out["C_us30_mr"] = {"report_claim": {"IS": 0.76, "OOS": 1.00, "4x_IS": 0.58, "4x_OOS": 0.86, "pos_every_yr": True},
                        "full_2022_26": mC, "oos_2025_26": mC_o, "per_year": yC,
                        "markup4x_full": {"ann_sharpe": mC4.get("ann_sharpe")},
                        "turnover_per_day": resC["turnover_per_day"]}
    print(f"    C full ann_sharpe={mC['ann_sharpe']:.2f} OOS={mC_o['ann_sharpe']:.2f} kurt={mC['excess_kurtosis']:.1f} "
          f"4x_full={mC4['ann_sharpe']:.2f}  per-year={ {k:round(v,2) for k,v in yC.items()} }")

    # ---- Sleeve B: BTC 120-min momentum ----
    for src in ["panel", "binance"]:
        print(f"[B] loading BTC {src} ...", flush=True)
        btc = load_m1("BTCUSD", src)
        # binance has spread=0; give it a nominal MT5-like spread proxy for cost when needed
        barsB = build_bars(btc, "120min", 0, 21, drop_weekend=False)
        print(f"    bars={len(barsB)}  {barsB.index.min()} -> {barsB.index.max()}", flush=True)
        # cost: panel = real MT5 spread x2 + 0.065% RT commission. binance(spread=0) -> model
        # total BTC RT cost (~6-7bps spread + 6.5bps commission ~ 13bps) via commission_rt proxy.
        if src == "binance":
            resB = backtest(barsB, "BTCUSD", "mom", markup=0.0, commission_rt=0.0013)
        else:
            resB = backtest(barsB, "BTCUSD", "mom", markup=2.0, commission_rt=0.00065)
        netB = resB["net"]
        mB, yB = window_metrics(netB, "2022-01-01", "2026-06-05")
        mB_o, _ = window_metrics(netB, "2025-01-01", "2026-06-05")
        out[f"B_btc_mom_{src}"] = {"report_claim_netOOS": 0.51, "full_2022_26": mB, "oos_2025_26": mB_o,
                                   "per_year": yB, "turnover_per_day": resB["turnover_per_day"]}
        print(f"    B({src}) full ann_sharpe={mB['ann_sharpe']:.2f} OOS={mB_o['ann_sharpe']:.2f} "
              f"kurt={mB['excess_kurtosis']:.1f} per-year={ {k:round(v,2) for k,v in yB.items()} }")
        if src == "panel":
            netB.rename("net").to_csv(R / "sleeve_B_daily.csv")            # panel = MT5 cost-faithful (primary)
        else:
            netB.rename("net").to_csv(R / "sleeve_B_binance_daily.csv")

    (R / "sleeve_bc_metrics.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nReport: B net OOS Sharpe ~0.51 ; C IS+0.76/OOS+1.00, 4x IS+0.58/OOS+0.86, positive every year")


if __name__ == "__main__":
    main()
