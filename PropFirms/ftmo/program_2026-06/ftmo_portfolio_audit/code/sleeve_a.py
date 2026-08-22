"""
sleeve_a.py — INDEPENDENT regeneration of Sleeve A (REPORT.md §4).

Spec (verbatim from the report, NOT the long-only S072 code):
  Universe (11): EURUSD GBPUSD AUDUSD NZDUSD USDCHF USDJPY US500 US100 US30 GER40 XAUUSD
  Signal (causal): RSI(2) on daily close, shifted 1. Enter at next OPEN when
                   RSI2<10 (long) / >90 (short); exit at OPEN on revert-to-50 or 8-day max hold.
  Sizing: per-instrument inverse-volatility risk parity (90-day trailing).
  Costs: real MT5 spread (×markup) + FX commission + swap on held nights.
Daily boundary: EET (FTMO broker server day — Gate 1) primary; UTC as sensitivity.
Trade MTM: day e open->close, full days close->close, exit day close->open (exit at open).

Outputs: results/sleeve_A_daily.csv (net daily series), results/sleeve_A_metrics.json
"""
from __future__ import annotations
import json, sys
import numpy as np
import pandas as pd
from audit_common import (load_daily, rsi, point_size, metrics, vol_target,
                          per_year_sharpe, FX, ROOT)

UNIVERSE = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCHF", "USDJPY",
            "US500", "US100", "US30", "GER40", "XAUUSD"]
THR_LO, THR_HI, EXIT_LVL, MAX_HOLD = 10.0, 90.0, 50.0, 8
FX_COMM_RT = 5.0 / 100_000          # 2.5 USD/lot/side -> 5 USD/lot RT on 100k notional (~0.5bps)


def sim_instrument(df: pd.DataFrame, sym: str, markup: float = 2.0,
                   swap_bps_night: float = 0.5) -> pd.DataFrame:
    """Return DataFrame(date-indexed) with gross, cost, net daily return for the RSI2 trades."""
    o = df["open"].values.astype(float)
    c = df["close"].values.astype(float)
    sp = np.maximum(df["spread_open"].values, df["spread_mean"].values).astype(float)
    sp = np.where(np.isfinite(sp) & (sp > 0), sp, np.nan)
    R = rsi(pd.Series(c, index=df.index), 2).values
    n = len(df)
    pt = point_size(sym)
    comm_side = (FX_COMM_RT / 2.0) if sym in FX else 0.0
    gross = np.zeros(n)
    cost = np.zeros(n)

    def rt_spread(k):
        s = sp[k]
        if not np.isfinite(s):
            s = np.nanmedian(sp)               # fallback for rare missing-spread bars
        return s * pt * markup / c[k]

    i = 5
    while i < n - 1:
        sig = 1 if R[i] < THR_LO else (-1 if R[i] > THR_HI else 0)
        if sig == 0:
            i += 1
            continue
        e = i + 1
        if e > n - 1:
            break
        gross[e] += sig * (c[e] / o[e] - 1.0)                 # entry day open->close
        cost[e] += 0.5 * rt_spread(e) + comm_side
        last_j = e
        for j in range(e, n):
            hold_days = j - e + 1
            revert = (sig == 1 and R[j] >= EXIT_LVL) or (sig == -1 and R[j] <= EXIT_LVL)
            if revert or hold_days >= MAX_HOLD or j >= n - 2:
                xe = min(j + 1, n - 1)
                gross[xe] += sig * (o[xe] / c[j] - 1.0)        # exit day close->open
                cost[xe] += 0.5 * rt_spread(xe) + comm_side
                cost[xe] += (xe - e) * swap_bps_night / 1e4    # swap per overnight held
                last_j = j
                break
            else:
                gross[j + 1] += sig * (c[j + 1] / c[j] - 1.0)  # carried full day close->close
        i = last_j + 1

    out = pd.DataFrame({"gross": gross, "cost": cost}, index=df.index)
    out["net"] = out["gross"] - out["cost"]
    return out


def build_sleeve_a(tz: str = "EET", markup: float = 2.0, swap_bps_night: float = 0.5,
                   invvol_lb: int = 90, start: str = "2021-06-01",
                   end: str = "2026-06-05") -> dict:
    per_instr_net = {}
    diag = {}
    for sym in UNIVERSE:
        df = load_daily(sym, tz).loc[:end]
        sim = sim_instrument(df, sym, markup, swap_bps_night)
        per_instr_net[sym] = sim["net"]
        m = metrics(sim["net"].loc[start:end])
        diag[sym] = {"ann_sharpe": round(m.get("ann_sharpe", 0), 3),
                     "n_days": m.get("n_days", 0),
                     "ann_ret": round(m.get("ann_return", 0), 4)}
    N = pd.DataFrame(per_instr_net).sort_index()
    N = N.loc[N.index >= pd.Timestamp("2007-01-01")]
    # inverse-vol risk parity weights (90d trailing std, lagged, renormalized over available)
    vol = N.rolling(invvol_lb).std().shift(1)
    inv = 1.0 / vol.replace(0, np.nan)
    w = inv.div(inv.sum(axis=1), axis=0)                      # row-normalized
    sleeve_gross = (w * N).sum(axis=1)                        # inverse-vol combined daily
    sleeve_gross = sleeve_gross.loc[start:end]
    sleeve_net = vol_target(sleeve_gross, sigma_target=0.01, lookback=63, cap=4.0)
    sleeve_net = sleeve_net.loc[start:end].dropna()
    return {"per_instr_net": N, "weights": w, "sleeve_gross": sleeve_gross,
            "sleeve_net": sleeve_net, "instr_diag": diag}


def main():
    res = build_sleeve_a()
    full = res["sleeve_net"].loc["2022-01-01":"2026-06-05"]
    oos = res["sleeve_net"].loc["2025-01-01":"2026-06-05"]
    m_full = metrics(full)
    m_oos = metrics(oos)
    out = {
        "spec": "two-sided RSI2 daily, 11 instruments, inverse-vol(90d), EET, markup2, swap0.5bp/night",
        "report_claim": {"daily_sharpe": 0.97, "excess_kurtosis": 14, "positive_every_year": True},
        "full_2022_2026": m_full,
        "oos_2025_2026": m_oos,
        "per_year_sharpe_full": per_year_sharpe(full),
        "instr_diag": res["instr_diag"],
    }
    res["sleeve_net"].rename("net").to_csv(ROOT / "research/ftmo_portfolio_audit/results/sleeve_A_daily.csv")
    (ROOT / "research/ftmo_portfolio_audit/results/sleeve_A_metrics.json").write_text(
        json.dumps(out, indent=2, default=str))
    print("=== Sleeve A (independent) ===")
    print(f" full 2022-26: daily_sharpe={m_full['daily_sharpe']:.3f} ann_sharpe={m_full['ann_sharpe']:.2f} "
          f"kurt={m_full['excess_kurtosis']:.1f} maxDD={m_full['max_dd']*100:.1f}% worst={m_full['worst_day']*100:.2f}%")
    print(f" oos  2025-26: daily_sharpe={m_oos['daily_sharpe']:.3f} ann_sharpe={m_oos['ann_sharpe']:.2f} "
          f"kurt={m_oos['excess_kurtosis']:.1f}")
    print(" per-year Sharpe:", {k: round(v, 2) for k, v in out["per_year_sharpe_full"].items()})
    print(" REPORT claim: daily_sharpe 0.97, kurt 14, positive every year")
    print(" per-instrument ann_sharpe:", {k: v["ann_sharpe"] for k, v in res["instr_diag"].items()})

    # cost/tz sensitivity
    print("\n--- sensitivity (full 2022-26 daily_sharpe) ---")
    for tz in ["EET", "UTC"]:
        for mk in [1.0, 2.0, 3.0]:
            for sw in [0.0, 0.5, 1.0]:
                r = build_sleeve_a(tz=tz, markup=mk, swap_bps_night=sw)
                mm = metrics(r["sleeve_net"].loc["2022-01-01":"2026-06-05"])
                print(f"  tz={tz} markup={mk} swap={sw}bp -> daily_sharpe={mm['daily_sharpe']:.3f} "
                      f"ann={mm['ann_sharpe']:.2f} kurt={mm['excess_kurtosis']:.1f}")


if __name__ == "__main__":
    main()
