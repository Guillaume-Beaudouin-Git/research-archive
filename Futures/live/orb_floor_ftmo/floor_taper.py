"""
floor_taper.py — Live sizing module: floor-proximity taper + post-target de-risk.

This is NOT an alpha. The ORB has zero per-trade edge (DSR_p 0.08, placebo random+floor
= 97.7% p_funded). What floor_taper does:
  - Path management: reduce size when equity is close to a fail floor (daily or total)
  - Post-target lock: when P1 target met, drop size to minimum / stop trading
  - Net effect: lengthens grind but reduces bust probability

L19 note: the effective leverage of floor_taper depends on the equity trajectory.
We document the mean effective leverage AS A REPORTING NUMBER, not as an edge claim.

Logic:
  - λ_floor = min(λ_floor_daily, λ_floor_total)
  - λ_floor_daily = max(0.25, distance_to_daily_floor / cushion_daily)
  - λ_floor_total = max(0.25, distance_to_total_floor / cushion_total)
    where cushion_X is the "soft" threshold (configurable)
  - λ_post_p1 = 0.10 if equity ≥ P1 target (verrouille acquis), else 1.0
  - Total live size = base_risk × min(λ_floor, λ_post_p1)
"""
from __future__ import annotations
from dataclasses import dataclass
from .ftmo_rules import FTMORules


@dataclass
class FloorTaperParams:
    """Sizing taper parameters.

    cushion_daily_pct: when equity is within this % of daily floor, taper kicks in.
                       e.g. 0.02 = 2% → if day_start = $50K and daily_floor = -5% = $47.5K,
                       cushion of 2% = $1000, so taper from $48.5K down (when DD > 3% on day).
    cushion_total_pct: same for total floor.
    taper_min_factor: floor of the taper (e.g. 0.25 = down-size to 25% near floor).
    post_target_factor: factor applied AFTER P1 target reached. 0.10 = 10% size to lock.
    post_target_stop_trading: if True, stop trading entirely after P1 target.
    """
    cushion_daily_pct: float = 0.02      # 2% cushion from daily floor
    cushion_total_pct: float = 0.04      # 4% cushion from total floor
    taper_min_factor: float = 0.25       # floor of taper
    post_target_factor: float = 0.10     # after P1 target: 10% size
    post_target_stop_trading: bool = False  # safer: actually stop


def floor_taper_factor(equity_now: float,
                        day_start_balance: float,
                        hwm: float,
                        rules: FTMORules,
                        params: FloorTaperParams) -> dict:
    """
    Compute the sizing factor at the current moment.

    Returns dict with:
      - lambda_daily : taper based on daily floor proximity
      - lambda_total : taper based on total floor proximity
      - lambda_target: post-target de-risk factor
      - lambda_combined: min(daily, total, target)
      - distance_daily_pct: how far above daily floor (% of day_start)
      - distance_total_pct: how far above total floor (% of initial)
      - phase: "p1_grind" / "p1_passed" / "near_daily_floor" / "near_total_floor"
    """
    # Daily floor
    daily_floor = rules.daily_floor_usd_from_balance(day_start_balance)
    daily_distance = equity_now - daily_floor
    daily_cushion = day_start_balance * params.cushion_daily_pct
    if daily_distance <= 0:
        lambda_daily = 0.0  # already in breach territory
    elif daily_distance >= daily_cushion:
        lambda_daily = 1.0  # well clear
    else:
        # Linear taper from 1.0 (at cushion) to taper_min_factor (at floor)
        frac = daily_distance / daily_cushion
        lambda_daily = params.taper_min_factor + (1 - params.taper_min_factor) * frac

    # Total floor (static or trailing per rules)
    total_floor = rules.floor_total_usd(hwm)
    total_distance = equity_now - total_floor
    total_cushion = rules.initial_balance_usd * params.cushion_total_pct
    if total_distance <= 0:
        lambda_total = 0.0
    elif total_distance >= total_cushion:
        lambda_total = 1.0
    else:
        frac = total_distance / total_cushion
        lambda_total = params.taper_min_factor + (1 - params.taper_min_factor) * frac

    # Post-target
    p1_target_usd = rules.initial_balance_usd * (1 + rules.p1_profit_target_pct)
    if equity_now >= p1_target_usd:
        if params.post_target_stop_trading:
            lambda_target = 0.0
        else:
            lambda_target = params.post_target_factor
        phase = "p1_passed"
    else:
        lambda_target = 1.0
        phase = "p1_grind"

    # Override phase if near floor
    if lambda_daily < 1.0 or lambda_total < 1.0:
        if lambda_daily <= lambda_total:
            phase = "near_daily_floor"
        else:
            phase = "near_total_floor"

    lambda_combined = min(lambda_daily, lambda_total, lambda_target)
    return {
        "lambda_daily": lambda_daily,
        "lambda_total": lambda_total,
        "lambda_target": lambda_target,
        "lambda_combined": lambda_combined,
        "distance_daily_pct": daily_distance / day_start_balance,
        "distance_total_pct": total_distance / rules.initial_balance_usd,
        "phase": phase,
    }


def position_size_usd(equity_now: float, day_start_balance: float, hwm: float,
                       base_risk_pct: float, sl_distance_pct: float,
                       rules: FTMORules, params: FloorTaperParams) -> dict:
    """
    Compute the position size in $ for the next trade.

    base_risk_pct: % of equity to risk per trade if not tapered (e.g. 0.005 = 0.5%)
    sl_distance_pct: distance from entry to stop (% of price)
    """
    taper = floor_taper_factor(equity_now, day_start_balance, hwm, rules, params)
    risk_usd = equity_now * base_risk_pct * taper["lambda_combined"]
    # Position notional ≈ risk_usd / sl_distance_pct
    notional = risk_usd / sl_distance_pct if sl_distance_pct > 0 else 0.0
    return {
        "risk_usd": risk_usd,
        "notional_usd": notional,
        **taper,
    }


if __name__ == "__main__":
    from .ftmo_rules import FTMO_50K_STATIC, FTMO_50K_TRAILING

    print("=" * 90)
    print("FLOOR TAPER SANITY — $50K account, static max DD")
    print("=" * 90)
    rules = FTMO_50K_STATIC
    params = FloorTaperParams()
    # Test at various equity levels
    print(f"\n{'Equity':>10} {'DayStart':>10} {'HWM':>10} {'λ_daily':>8} {'λ_total':>8} "
          f"{'λ_target':>9} {'λ_comb':>8} {'phase':>20}")
    test_cases = [
        # (equity, day_start, hwm, label)
        (50000, 50000, 50000, "Start fresh"),
        (49500, 50000, 50000, "Day -1% loss"),
        (48500, 50000, 50000, "Day -3% loss (3% from daily floor)"),
        (48000, 50000, 50000, "Day -4% loss (1% from daily floor)"),
        (47600, 50000, 50000, "Day -4.8% loss (0.2% from daily floor)"),
        (46000, 50000, 50000, "Total -8% (2% from total floor)"),
        (45500, 50000, 50000, "Total -9% (1% from total floor)"),
        (55000, 55000, 55000, "+10% achieved, P1 done"),
        (53000, 55000, 55000, "Post-P1 some retracement"),
    ]
    for eq, ds, hwm, label in test_cases:
        r = position_size_usd(eq, ds, hwm, 0.005, 0.005, rules, params)
        print(f"  {eq:>10,} {ds:>10,} {hwm:>10,} {r['lambda_daily']:>8.2f} "
              f"{r['lambda_total']:>8.2f} {r['lambda_target']:>9.2f} "
              f"{r['lambda_combined']:>8.2f} {r['phase']:>20s}   {label}")

    print()
    print("=" * 90)
    print("Same scenarios under TRAILING max DD")
    print("=" * 90)
    rules_t = FTMO_50K_TRAILING
    print(f"\n{'Equity':>10} {'DayStart':>10} {'HWM':>10} {'λ_daily':>8} {'λ_total':>8} "
          f"{'λ_target':>9} {'λ_comb':>8} {'phase':>20}")
    for eq, ds, hwm, label in test_cases:
        r = position_size_usd(eq, ds, hwm, 0.005, 0.005, rules_t, params)
        print(f"  {eq:>10,} {ds:>10,} {hwm:>10,} {r['lambda_daily']:>8.2f} "
              f"{r['lambda_total']:>8.2f} {r['lambda_target']:>9.2f} "
              f"{r['lambda_combined']:>8.2f} {r['phase']:>20s}   {label}")
