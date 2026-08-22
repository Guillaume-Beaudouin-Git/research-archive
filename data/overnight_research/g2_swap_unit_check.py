"""G2 — Swap unit make-or-break.

Question: is the report's claim "swap_long = −662.4 points → −3.08 bps/night"
actually correct, or did it assume the wrong point→price unit?

Strategy:
  1. Use the FTMO specs CSV (data/ftmo_research/ftmo_specs_full.csv).
  2. Apply MT5 standard formula: swap_money = swap_points × point_size_in_price × contract_size.
  3. Cross-validate against TWO independent symbols (EURUSD and XAUUSD) where
     the resulting bps/night is known industry-wide.
  4. Sensitivity grid: what if point_size = 0.001, 0.01, 0.1, 1.0?
  5. Compute swap_3x_day convention impact (A: Fri-night Fri→Mon 3x; B: Thu-night→Fri 3x).
  6. Net per weekday-open for both conventions.
"""
import numpy as np
import pandas as pd

SPECS_PATH = "<HOME>/Desktop/Algo_claude/data/ftmo_research/ftmo_specs_full.csv"

# Reference live prices (approx, only the order of magnitude matters)
PX = {"US100.cash": 21500, "EURUSD": 1.10, "XAUUSD": 3000, "GBPJPY": 200, "USDJPY": 150}

# Read & focus
specs = pd.read_csv(SPECS_PATH)
print("Specs columns:", specs.columns.tolist())
print(specs[["ticker", "digits", "contract_size", "swap_long", "swap_short", "swap_type", "swap_3x_day"]].to_string(index=False))

us100 = specs[specs.ticker == "US100.cash"].iloc[0]
print(f"\nUS100.cash row:\n{us100}\n")


def swap_bps_per_night(swap_points, digits, contract_size, ref_price, point_size_override=None):
    """Convert MT5 swap_points → bps/night under the standard MT5 mode=POINTS formula.

    swap_money (USD per lot per night) = swap_points × point_in_price × contract_size
    bps/night = swap_money / (contract_size × ref_price) × 1e4
              = swap_points × point_in_price / ref_price × 1e4
    """
    if point_size_override is not None:
        ps = point_size_override
    else:
        ps = 10 ** (-int(digits))
    money_per_lot = swap_points * ps * float(contract_size)
    notional_per_lot = float(contract_size) * ref_price
    return money_per_lot / notional_per_lot * 1e4, money_per_lot, ps


# ===== Canonical (digits-implied) calculation =====
print("=" * 78)
print("CANONICAL — point_size derived from digits (MT5 standard)")
print("=" * 78)
for tk in ["US100.cash", "EURUSD", "XAUUSD", "USDJPY", "GBPJPY"]:
    row = specs[specs.ticker == tk].iloc[0]
    cs = float(str(row.contract_size).split()[0])
    bps, money, ps = swap_bps_per_night(row.swap_long, int(row.digits), cs, PX[tk])
    print(f"{tk:12s}  swap_long={row.swap_long:>8} pts  digits={int(row.digits)}  cs={cs:>9.0f}  point_size={ps}  "
          f"swap_money={money:>+10.3f} USD/lot/night  swap_bps={bps:>+7.3f} bps/night  (ref px {PX[tk]})")

print("\nIndustry-reference cross-checks:")
print("  EURUSD swap_long  bps/night — industry sees ~ −1 to −2 bps (carry: USD>EUR)  → our number should be within that band.")
print("  XAUUSD swap_long  bps/night — industry sees ~ −2 to −5 bps   (gold financing)  → our number should be within that band.")

# ===== Sensitivity grid on the US100.cash point_size =====
print("\n" + "=" * 78)
print("SENSITIVITY GRID — US100.cash point_size assumed value")
print("=" * 78)
print(f"{'point_size':>12s}  {'swap_money $/lot/night':>22s}  {'bps/night (1x)':>15s}")
for ps in [0.001, 0.01, 0.1, 1.0]:
    bps, money, _ = swap_bps_per_night(us100.swap_long, int(us100.digits), float(us100.contract_size), PX["US100.cash"], point_size_override=ps)
    print(f"{ps:>12.4f}  {money:>+22.3f}  {bps:>+15.3f}")
print(f"\nDigits-implied point_size for US100.cash: 10^-{int(us100.digits)} = {10**-int(us100.digits)}")
print("→ At digits=2, MT5 *forces* point_size = 0.01. Other values would contradict the symbol spec.")

# ===== Swap_3x_day — convention impact =====
print("\n" + "=" * 78)
print("SWAP_3X_DAY = Friday — TWO possible conventions impact on per-weekday net")
print("=" * 78)
print(f"  Convention A (industry-common for CFD indices):")
print(f"    Friday rollover charge covers Sat+Sun → night Fri→Mon (open-day Mon) is 3x")
print(f"  Convention B (literal MT5 reading 'day when calculated', used by the report):")
print(f"    Friday open-day shows the 3x charge → night Thu→Fri (open-day Fri) is 3x")
print(f"  Both yield identical WEEKLY total swap (4×1x + 1×3x = 7x per Mon-Fri week).")
print(f"  Midweek-only (Tue+Wed open-days) is INVARIANT to A/B: always 1x in both.\n")

# Gross per-weekday (from G1)
GROSS_BPS = {0: 3.178, 1: 7.441, 2: 8.690, 3: 2.936, 4: 2.156}  # Mon..Fri (NQ canonical)
SWAP_1X = abs(swap_bps_per_night(us100.swap_long, 2, 1.0, PX["US100.cash"])[0])  # |bps| absorbed
print(f"  swap_1x = {SWAP_1X:.3f} bps/night ;  swap_3x = {3*SWAP_1X:.3f} bps/night")

def net_table(conv_A=True):
    rows = []
    for wd, gross in GROSS_BPS.items():
        if conv_A:
            mult = 3 if wd == 0 else 1   # Mon-open = Fri-night = 3x in Conv A
        else:
            mult = 3 if wd == 4 else 1   # Fri-open = Thu-night = 3x in Conv B
        swap_charge = SWAP_1X * mult
        net = gross - swap_charge
        rows.append({"weekday": ["Mon","Tue","Wed","Thu","Fri"][wd],
                     "swap_x": mult,
                     "gross_bps": gross,
                     "swap_charge_bps": swap_charge,
                     "net_bps": net})
    return pd.DataFrame(rows)

print("\n  Convention A — Mon-open = 3x swap:")
print(net_table(conv_A=True).to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
print("\n  Convention B — Fri-open = 3x swap (dossier):")
print(net_table(conv_A=False).to_string(index=False, float_format=lambda v: f"{v:+.3f}"))

# Toutes-nuits aggregate (weighted by ~equal weekdays)
wA = net_table(True)
wB = net_table(False)
print(f"\n  ALL-nights mean (1/5 weighting):")
print(f"    Conv A: gross {wA.gross_bps.mean():+.3f}  swap {wA.swap_charge_bps.mean():+.3f}  net {wA.net_bps.mean():+.3f} bps/night")
print(f"    Conv B: gross {wB.gross_bps.mean():+.3f}  swap {wB.swap_charge_bps.mean():+.3f}  net {wB.net_bps.mean():+.3f} bps/night")

print("\n  MIDWEEK (Tue+Wed open) — INVARIANT to A/B:")
mid = wA[wA.weekday.isin(["Tue", "Wed"])]
print(mid.to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
print(f"    mean midweek net = {mid.net_bps.mean():+.3f} bps/night")

# Save
summary = {
    "swap_long_points": float(us100.swap_long),
    "swap_short_points": float(us100.swap_short),
    "digits": int(us100.digits),
    "contract_size": float(us100.contract_size),
    "point_size_implied": 10 ** -int(us100.digits),
    "ref_price_used": PX["US100.cash"],
    "swap_long_bps_1x": -SWAP_1X,
    "swap_long_bps_3x": -3 * SWAP_1X,
    "swap_3x_day": us100.swap_3x_day,
    "convention_A_assumption": "Fri-night→Mon-open is 3x (CFD industry-standard)",
    "convention_B_assumption": "Thu-night→Fri-open is 3x (dossier interpretation)",
    "midweek_net_bps_mean": float(mid.net_bps.mean()),
    "all_nights_net_bps_convA": float(wA.net_bps.mean()),
    "all_nights_net_bps_convB": float(wB.net_bps.mean()),
}
pd.Series(summary).to_csv("<HOME>/Desktop/Algo_claude/data/overnight_research/g2_swap_summary.csv", header=["value"])
print("\nSaved: data/overnight_research/g2_swap_summary.csv")
