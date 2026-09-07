"""Part D: cost gate. Three venues, per L43 (gross_per_trade / cost_p95 >= 1.5,
best ever observed in this repo = 0.36-0.38).

FTMO: measured per-pair RT bps from data/ftmo_portfolio/outputs/phase0_rt_cost_bps.csv
  (repo-canonical measured figure; the CLAUDE.md 2.48bps figure is the portfolio-
  blended average, not a per-pair number -- use the per-pair series here).
Eightcap Raw: NOT reliably measured. Forex/research/active/dedale_broker_2026-08/
  RAPPORT_BROKER.md puts it at ~0.66-1.18 bps RT ESTIMATION, flagging that the real
  cost is "probablement 2-8x plus haut" per a measured EURUSD comparable. We use
  the prompt's 0.75 bps as a best-case number and separately show the 2-8x stress.
IBKR: ~0.4-0.5 bps RT execution, but commission has a $2/order floor (L57) that
  dominates on small notional -- reported net of a notional assumption.
"""
import pandas as pd
import os

RT_COST_FTMO_PATH = "<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/outputs/phase0_rt_cost_bps.csv"

EIGHTCAP_BEST_CASE_BPS = 0.75
EIGHTCAP_STRESS_MULT = (2.0, 8.0)  # per dedale_broker_2026-08 measured-comparable caveat
IBKR_EXEC_BPS = 0.45


def ftmo_cost_table():
    df = pd.read_csv(RT_COST_FTMO_PATH, index_col=0, header=None, names=["pair", "rt_bps"])
    return df["rt_bps"].to_dict()


def ibkr_effective_bps(notional_usd, commission_per_order_usd=2.0):
    """IBKR FX commission ~0.2bps of notional with a $2/order floor, round trip
    = 2 orders. Effective bps = exec spread bps + commission bps."""
    commission_bps_leg = max(commission_per_order_usd, 0.00002 * notional_usd) / notional_usd * 10000
    return IBKR_EXEC_BPS + 2 * commission_bps_leg  # RT = 2 legs


def gate_report(pair, gross_bps):
    ftmo = ftmo_cost_table()
    ftmo_bps = ftmo.get(pair, float("nan"))
    rows = []
    rows.append({"venue": "FTMO (measured, phase0_rt_cost_bps.csv)", "cost_bps": ftmo_bps,
                 "ratio": gross_bps / ftmo_bps if ftmo_bps else float("nan")})
    rows.append({"venue": "Eightcap Raw (best-case, UNVERIFIED)", "cost_bps": EIGHTCAP_BEST_CASE_BPS,
                 "ratio": gross_bps / EIGHTCAP_BEST_CASE_BPS})
    for mult in EIGHTCAP_STRESS_MULT:
        c = EIGHTCAP_BEST_CASE_BPS * mult
        rows.append({"venue": f"Eightcap Raw (stress x{mult:.0f}, per measured-comparable caveat)",
                     "cost_bps": c, "ratio": gross_bps / c})
    for notional in (10_000, 50_000):
        c = ibkr_effective_bps(notional)
        rows.append({"venue": f"IBKR (${notional:,} notional, $2/order floor)", "cost_bps": c,
                     "ratio": gross_bps / c})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    pair = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    gross = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    print(gate_report(pair, gross).to_string(index=False))
