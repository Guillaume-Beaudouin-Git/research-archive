"""v2.2 FROZEN SPEC — single change vs v2.1: ORB challenge-OFF + MICRO-ORB day-counter.

CHALLENGE (P1/P2):
  - ORB removed as P&L sleeve (orb_risk = 0).
  - MICRO-ORB: 0.01 lot US100 ORB trade, canonical entry 16:05-16:10 Paris (ledger
    timing), normal V2+E7 exit rules, taken on any day with no other trade opened by
    21:30 CET (in-engine: days without the 17:35 GER40 overnight entry, i.e. ON=0).
    P&L IS modeled: risk$ = 0.01 lot x or_range pts x $1/pt/lot ~ $0.2-2.0/trade;
    P&L = risk$ x R_era (same era-costed per-trade R as the full sleeve, cost scales
    proportionally with size). Posted at the 22:05 segment (exits close <= 22:00).
    Counts as the day's opened trade (min-4-days). Engine backstop (v2.1 deadlock
    patch, $1 token trade) stays armed for no-signal days; firings are counted and
    reported.
FUNDED: unchanged from v2.1 (ORB ON, risk 0.25% tapered, vm 1.0). Switch at funding.
ORB funded cost: PARAMETERIZED via ORB_RT_BPS ("era" = era-cost curve, or a float
  flat RT bps) so the demo N=60 measurement is a one-line change + rerun of the
  funded step only.
OUT OF SCOPE (unchanged, reserved v2.3+): J1 sizing, all other parameters.
"""

# --- the one switch ---
ORB_RT_BPS = "era"          # funded ORB cost: "era" or float RT bps all-in

# --- challenge config (frozen) ---
CFG_CHALLENGE = dict(
    vm=14.0, p2_mult=1.2, on_w=0.6,
    orb_risk=0.0,            # v2.2: ORB OFF in challenge
    micro_orb=True,          # v2.2: micro-ORB day-counter (P&L modeled)
    breaker=0.30, taper=0.02, glide=0.5, pace=1, pace_k=1.0,
    ab_buf=0.02, ab_days=5, margin_cap=0.60, quantize=True,
    fix_deadlock=True,       # v2.1 corrected-stack backstop (counted)
)

# --- funded config (unchanged v2.1) ---
CFG_FUNDED = dict(
    vm=1.0, on_w=0.35, orb_risk=0.0025, micro_orb=False,
    breaker=0.30, taper=0.02, glide=1.0, pace=0,
    margin_cap=0.60, quantize=True, target=10.0,
)

FEE = 96.0                   # challenge fee $96 (refunded at first payout)
WALL = 91                    # 3-month mission wall (calendar days)
WINDOWS = (("IS", "2013-10-01", "2019-12-31"), ("OOS", "2020-01-02", "2026-02-25"))
COHORT_STEP = 7
FUNDED_WINDOWS = (("IS", "2013-10-01", "2017-12-31"), ("OOS", "2020-01-02", "2024-06-30"))
FUNDED_STEP = 12
FUNDED_WD_EVERY = 14         # trading days (conservative vs official bi-weekly)
FUNDED_HORIZON = 504
