"""
ftmo_rules.py — FTMO 2-step Challenge rules (verified as of 2026-06).

⚠ HUMAN VERIFICATION REQUIRED ⚠
These rules are based on FTMO documentation visible mid-2025 / early-2026 + memory
from prior sessions. Re-confirm against https://ftmo.com/en/account-types/normal-2-step/
BEFORE depositing. The constants flagged HUMAN_VERIFY are critical to the floor_taper logic.

KEY OPEN QUESTIONS (the user must confirm before deploy):
  Q1 (CRITICAL): max overall loss — STATIC equity floor (- $X% of initial balance)
                  or TRAILING (- $X% from high water mark, EOD-tracked) ?
  → This changes the floor_taper math. We code BOTH variants below; user selects.

  Q2: minimum trading days — 4 days is standard but verify the definition (4 trades
                              or 4 days with ≥ 1 position?)

  Q3: inactivity rule — 30 days of no trading triggers fail. ORB trades ~daily so OK
                         but plan for market closures.

  Q4: consistency rule — 2-step has NO consistency cap (= no single-day-too-large limit)
                          per FTMO docs. CONFIRM still true 2026.

  Q5: news trading allowed (NFP/CPI/FOMC) ? Per 2025 update YES on 2-step. Confirm.

  Q6: stop-loss MANDATORY ? FTMO has 'no SL required' rule on 2-step. Confirm.

  Q7: max position size or leverage cap on US100 ?  E.g. some prop firms cap @ 1:20
                                                     on indices. Verify FTMO US100 spec.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class FTMORules:
    """FTMO 2-step Challenge — known + assumed parameters."""
    # Account size (we deploy on $50K; the user said budget $50K)
    initial_balance_usd: float = 50000.0

    # Phase 1 (Challenge) targets
    p1_profit_target_pct: float = 0.10   # +10% to pass P1
    p2_profit_target_pct: float = 0.05   # +5% to pass P2 (Verification)

    # Daily drawdown
    daily_loss_max_pct: float = 0.05     # max -5% from day-start balance (floating equity)
    # ⚠ HUMAN_VERIFY: "from day-start balance" or "from previous-day close" ?

    # Max overall loss
    max_overall_loss_pct: float = 0.10   # max -10% from initial balance OR HWM
    max_overall_loss_mode: str = "static"  # "static" or "trailing"
    # ⚠ HUMAN_VERIFY Q1: this is the critical setting

    # Time
    min_trading_days: int = 4
    time_limit_days: int | None = None  # 2026: NO time limit confirmed
    inactivity_days: int = 30            # fail if no trade for 30 calendar days

    # Other
    weekend_holding_allowed: bool = True   # 2-step yes; some "swing" plans differ
    news_trading_allowed: bool = True       # confirm 2025 update
    consistency_rule_2step: bool = False    # 2-step: NO consistency cap (verified mid-2025)
    eod_trailing_mode: str | None = None    # trailing only "static" mode on 2-step
    # ⚠ HUMAN_VERIFY all flags above before deploy

    @property
    def daily_floor_usd(self) -> float:
        return self.initial_balance_usd * self.daily_loss_max_pct

    @property
    def total_floor_usd_static(self) -> float:
        return self.initial_balance_usd * (1 - self.max_overall_loss_pct)

    def floor_total_usd(self, current_hwm: float) -> float:
        """Returns the effective total floor in USD (static or trailing)."""
        if self.max_overall_loss_mode == "static":
            return self.initial_balance_usd * (1 - self.max_overall_loss_pct)
        elif self.max_overall_loss_mode == "trailing":
            return current_hwm * (1 - self.max_overall_loss_pct)
        else:
            raise ValueError(f"Unknown mode: {self.max_overall_loss_mode}")

    def daily_floor_usd_from_balance(self, day_start_balance: float) -> float:
        return day_start_balance * (1 - self.daily_loss_max_pct)


# Default instance for $50K account, STATIC max DD (the LESS conservative case)
FTMO_50K_STATIC = FTMORules(
    initial_balance_usd=50000.0,
    p1_profit_target_pct=0.10,
    p2_profit_target_pct=0.05,
    daily_loss_max_pct=0.05,
    max_overall_loss_pct=0.10,
    max_overall_loss_mode="static",
)

# Conservative variant in case FTMO is trailing
FTMO_50K_TRAILING = FTMORules(
    initial_balance_usd=50000.0,
    max_overall_loss_mode="trailing",
)


def sanity_check_rules(r: FTMORules) -> list[str]:
    """Print + return any HUMAN_VERIFY warnings."""
    warnings = []
    warnings.append(f"⚠ HUMAN_VERIFY Q1: max DD is set to {r.max_overall_loss_mode.upper()} mode. "
                     "If FTMO uses the OTHER mode, floor_taper is mis-calibrated.")
    warnings.append(f"⚠ HUMAN_VERIFY Q2-Q7: re-confirm 2-step rules on ftmo.com BEFORE deploy.")
    warnings.append("⚠ The daily loss is measured against day-start balance — confirm.")
    return warnings


if __name__ == "__main__":
    print("FTMO 2-step Challenge rules — STATIC mode (default assumption):")
    r = FTMO_50K_STATIC
    print(f"  Initial: ${r.initial_balance_usd:,.0f}")
    print(f"  P1 target: +{r.p1_profit_target_pct*100:.0f}% = ${r.initial_balance_usd*(1+r.p1_profit_target_pct):,.0f}")
    print(f"  P2 target: +{r.p2_profit_target_pct*100:.0f}% (after P1)")
    print(f"  Daily floor: -{r.daily_loss_max_pct*100:.0f}% from day-start = -${r.daily_floor_usd:,.0f}")
    print(f"  Total floor: -{r.max_overall_loss_pct*100:.0f}% ({r.max_overall_loss_mode}) = ${r.total_floor_usd_static:,.0f}")
    print(f"  Min trading days: {r.min_trading_days}")
    print(f"  Time limit: {r.time_limit_days or 'NONE'}")
    print(f"  Inactivity: {r.inactivity_days} days")
    print()
    for w in sanity_check_rules(r):
        print(w)
