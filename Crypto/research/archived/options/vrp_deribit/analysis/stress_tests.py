"""
stress_tests.py — VRP Phase 3 stress test analysis

Tests:
  1. LUNA  (May 5-15, 2022):   BTC −28% over 10 days, IV spike
  2. FTX   (Nov 6-14, 2022):   BTC −26% over 8 days, IV spike
  3. Synthetic COVID scenario:  BTC −50% in 24h, IV_ATM ×3

For real events (LUNA, FTX): identifies active straddle cycles during the
event window and reports their realized P&L (already captured in backtest).

For synthetic COVID: applies a hypothetical shock to an open straddle
position using full Black-Scholes repricing to compute mark-to-market loss.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

PARENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PARENT))

CYCLES_PATH = PARENT / "phase3_cycles.csv"
CACHE_DIR   = PARENT.parents[3] / "data" / "vrp" / "cache"

N_PRIME_0 = 0.39894228  # N'(0)


# ── Black-Scholes helpers ──────────────────────────────────────────────────────

def bs_straddle_price(S: float, K: float, sigma: float, T: float) -> float:
    """
    ATM straddle price (call + put) via Black-Scholes.
    Assumes r = 0, q = 0 (crypto: no dividend, carry via funding handled separately).
    Returns price as fraction of S.
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        return abs(S - K) / S  # intrinsic value only
    d1 = (np.log(S / K) + 0.5 * sigma ** 2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call = S * norm.cdf(d1) - K * norm.cdf(d2)
    put  = K * norm.cdf(-d2) - S * norm.cdf(-d1)
    return (call + put) / S


# ── Historical event analysis ──────────────────────────────────────────────────

def analyze_historical_event(
    cycles:  pd.DataFrame,
    name:    str,
    ev_start: str,
    ev_end:   str,
) -> dict:
    """
    Find cycles that overlapped with [ev_start, ev_end] and report their P&L.
    A cycle "overlapped" if start_date <= ev_end AND end_date >= ev_start.
    """
    es = pd.Timestamp(ev_start, tz="UTC")
    ee = pd.Timestamp(ev_end,   tz="UTC")

    overlap = cycles[
        (cycles["start_date"] <= ee) & (cycles["end_date"] >= es)
    ].copy()

    result = {
        "event":       name,
        "window":      f"{ev_start} → {ev_end}",
        "n_cycles_affected": int(len(overlap)),
    }
    if len(overlap) == 0:
        result["note"] = "No active cycles during event window."
        return result

    result["cycles"] = []
    for _, row in overlap.iterrows():
        result["cycles"].append({
            "start_date":   str(row["start_date"].date()),
            "end_date":     str(row["end_date"].date()),
            "hold_days":    int(row["hold_days"]),
            "dvol_entry":   round(float(row["dvol_entry"]) * 100, 2),
            "rv_realized":  round(float(row["rv_realized"]) * 100, 2),
            "gross_pnl_pct":round(float(row["gross_pnl"])   * 100, 4),
            "net_pnl_pct":  round(float(row["net_pnl"])     * 100, 4),
            "early_unwind": bool(row["early_unwind"]),
        })

    net_pnl_sum = overlap["net_pnl"].sum()
    result["total_net_pnl_pct_notional"] = round(float(net_pnl_sum) * 100, 4)
    result["avg_net_pnl_pct_per_cycle"]  = round(float(overlap["net_pnl"].mean()) * 100, 4)
    return result


# ── Synthetic COVID scenario ───────────────────────────────────────────────────

def synthetic_covid_loss(
    dvol_entry:   float,     # implied vol at straddle entry (decimal)
    dte_at_entry: int = 30,  # DTE when straddle was opened (typically 30)
    dte_remaining:int = 22,  # DTE at time of shock (mid-way through cycle: 30-8=22)
    btc_drop:     float = -0.50,  # spot shock (-50% = -0.50)
    vol_mult:     float = 3.0,    # IV multiplier (×3)
) -> dict:
    """
    Compute P&L of a short ATM straddle position under a COVID-like shock.

    Method: full B-S repricing before and after the shock.
    - At entry: straddle sold at premium = bs_straddle_price(S, S, dvol_entry, dte_at_entry/365)
    - Post-shock: straddle mark = bs_straddle_price(S_post, S, σ_post, dte_remaining/365)
    - Loss = mark_post - premium_received (as % of original S = notional)

    Note: delta-hedge partially offsets the spot move loss. We apply a
    simplified delta-hedge adjustment: hedged position gains ≈ delta_atm × |btc_drop|
    on the perp short (since ATM put delta ≈ -0.5, call delta ≈ +0.5, straddle delta ≈ 0,
    but after the move delta shifts significantly).
    """
    S_entry    = 1.0    # normalized to 1
    K          = 1.0    # ATM strike = entry spot
    sigma_orig = dvol_entry
    T_entry    = dte_at_entry  / 365.0
    T_rem      = dte_remaining / 365.0

    # Premium received (% of notional)
    premium = bs_straddle_price(S_entry, K, sigma_orig, T_entry)

    # Post-shock: new spot, new vol, remaining DTE
    S_post     = S_entry * (1 + btc_drop)
    sigma_post = sigma_orig * vol_mult

    # Straddle mark post-shock
    mark_post = bs_straddle_price(S_post, K, sigma_post, T_rem) * S_post / S_entry

    # Delta-hedge P&L offset:
    # Before shock, straddle delta ≈ 0 (short call + short put, ATM)
    # We assume the last delta-hedge was at S_entry with delta_hedge_size ≈ 0
    # (so minimal hedge offset on the large spot move — conservative estimate)
    # A partial hedge correction: after spot move, call goes deep OTM, put deep ITM
    # Hedge is approximately: cumulative delta adjustment = some fraction
    # Conservative approach: zero delta-hedge offset (worst case)
    delta_hedge_offset = 0.0

    # Short straddle P&L (negative = loss to straddle seller)
    pnl_unhedged = premium - mark_post + delta_hedge_offset

    return {
        "scenario":        "Synthetic COVID-like",
        "parameters": {
            "dvol_entry":       round(dvol_entry * 100, 1),
            "dte_at_entry":     dte_at_entry,
            "dte_remaining":    dte_remaining,
            "btc_drop_pct":     round(btc_drop * 100, 1),
            "vol_multiplier":   vol_mult,
        },
        "premium_received_pct":   round(premium * 100, 3),
        "mark_post_shock_pct":    round(mark_post * 100, 3),
        "straddle_pnl_pct":       round(pnl_unhedged * 100, 3),
        "s_entry":                1.0,
        "s_post":                 round(S_post, 3),
        "sigma_post":             round(sigma_post * 100, 1),
        "note": (
            "Unhedged worst-case estimate. Delta-hedge provides partial offset "
            "proportional to last-hedge-to-shock gap. Actual loss may be 20-40% lower "
            "with continuous hedging."
        ),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n══════════════════════════════════════════════════════════════════════")
    print(" VRP PHASE 3 — STRESS TEST ANALYSIS")
    print("══════════════════════════════════════════════════════════════════════\n")

    if not CYCLES_PATH.exists():
        print(f"  ERROR: {CYCLES_PATH} not found. Run backtest.py first.")
        return

    cycles = pd.read_csv(CYCLES_PATH, parse_dates=["start_date", "end_date"])

    # ── 1. Historical events ──────────────────────────────────────────────
    events = [
        ("LUNA collapse",      "2022-05-05", "2022-05-15"),
        ("FTX collapse",       "2022-11-06", "2022-11-14"),
    ]

    print("── HISTORICAL EVENT STRESS TESTS ──────────────────────────────────")
    for name, start, end in events:
        r = analyze_historical_event(cycles, name, start, end)
        print(f"\n  Event: {r['event']}  ({r['window']})")
        print(f"  Active cycles affected: {r['n_cycles_affected']}")
        if r["n_cycles_affected"] > 0:
            for c in r["cycles"]:
                eu = " [EARLY UNWIND]" if c["early_unwind"] else ""
                print(f"    Cycle {c['start_date']} → {c['end_date']}  "
                      f"DVOL={c['dvol_entry']:.0f}%  RV={c['rv_realized']:.0f}%  "
                      f"NetPnL={c['net_pnl_pct']:+.3f}%{eu}")
            print(f"  → Total net P&L (% notional): "
                  f"{r['total_net_pnl_pct_notional']:+.3f}%")
            print(f"  → Avg per affected cycle:      "
                  f"{r['avg_net_pnl_pct_per_cycle']:+.3f}%")

    # ── 2. Synthetic COVID ────────────────────────────────────────────────
    print("\n── SYNTHETIC COVID SCENARIO ────────────────────────────────────────")
    dvol_scenarios = [0.50, 0.60, 0.80]  # DVOL at entry
    covid_params   = {
        "btc_drop":      -0.50,   # −50% in 24h
        "vol_mult":       3.0,    # IV ×3
        "dte_remaining":  22,     # mid-cycle: 8 days elapsed, 22 DTE remaining
    }

    print(f"\n  Shock: BTC {covid_params['btc_drop']:.0%}/24h, "
          f"IV ×{covid_params['vol_mult']}, "
          f"at {covid_params['dte_remaining']} DTE remaining\n")
    print(f"  {'DVOL Entry':<12}  {'Premium rcvd':<14}  {'Mark post-shock':<16}  {'P&L %notional':<14}")
    print(f"  {'-'*12}  {'-'*14}  {'-'*16}  {'-'*14}")

    for dvol_entry in dvol_scenarios:
        res = synthetic_covid_loss(
            dvol_entry    = dvol_entry,
            dte_at_entry  = 30,
            dte_remaining = covid_params["dte_remaining"],
            btc_drop      = covid_params["btc_drop"],
            vol_mult      = covid_params["vol_mult"],
        )
        premium  = res["premium_received_pct"]
        mark     = res["mark_post_shock_pct"]
        pnl      = res["straddle_pnl_pct"]
        print(f"  {dvol_entry*100:.0f}%         "
              f"  {premium:>8.2f}%       "
              f"  {mark:>10.2f}%         "
              f"  {pnl:>8.2f}%")

    print(f"\n  Note: {res['note']}")

    # Portfolio-level stress impact
    print(f"\n  Portfolio loss estimate (sizing: 1% × 2 concurrent = 2% underlying):")
    mid_dvol = 0.60
    mid_res  = synthetic_covid_loss(mid_dvol, 30, 22, -0.50, 3.0)
    straddle_loss_pct = mid_res["straddle_pnl_pct"]
    portfolio_loss    = straddle_loss_pct / 100 * 2  # 2% underlying notional
    print(f"  Straddle loss at DVOL=60%: {straddle_loss_pct:.2f}% of notional")
    print(f"  Portfolio loss (2% sizing): {portfolio_loss:.3%}")

    threshold = -0.15
    if portfolio_loss < threshold:
        print(f"  ⚠  HARD STOP gate: loss {portfolio_loss:.2%} exceeds {threshold:.0%} threshold.")
        print(f"     Phase 4 requires stress mitigation before deployment.")
    else:
        print(f"  ✓  Within stress limit ({threshold:.0%} threshold).")

    print()


if __name__ == "__main__":
    main()
