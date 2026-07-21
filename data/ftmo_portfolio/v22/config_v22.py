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

# --- v2.4 : sémantique de l'EA RÉELLEMENT DÉPLOYÉ (2026-07-20, ex5 678e303e) ---
# Deux écarts sim/EA corrigés ici. Les configs v2.2 ci-dessus restent gelées : tout
# résultat pinné se reproduit à l'identique (leurs défauts sont la sémantique v2.2).
#   brk_mode="daily"     -> remède (A) : breaker sur le daily seul, il se réarme
#                           chaque matin au lieu de se figer à $9,150 sous $9,500.
#   brk_needs_pos=True   -> l'EA conditionne le breaker à OurPositionsExist() ; sans
#                           position il ne latche pas flat_today et rouvre au
#                           rebalance suivant. Le sim v2.2 latchait à plat, d'où un
#                           "zombie inerte à $0/j" qui n'existe PAS en live (l'EA réel
#                           churn et meurt en ~35 j).
# ATTENTION : l'EA n'ABANDONNE pas tout seul (ab_days = alerte Telegram, décision
# humaine). Pour un p(funded) réaliste sans discipline de relance, mettre ab_days
# très grand — l'écart mesuré est -43.5 pt.
CFG_CHALLENGE_V24 = dict(CFG_CHALLENGE, brk_mode="daily", brk_needs_pos=True)
CFG_FUNDED_V24 = dict(CFG_FUNDED, brk_mode="daily", brk_needs_pos=True)

FEE = 96.0                   # challenge fee $96 (refunded at first payout)
WALL = 91                    # 3-month mission wall (calendar days)
WINDOWS = (("IS", "2013-10-01", "2019-12-31"), ("OOS", "2020-01-02", "2026-02-25"))
COHORT_STEP = 7
FUNDED_WINDOWS = (("IS", "2013-10-01", "2017-12-31"), ("OOS", "2020-01-02", "2024-06-30"))
FUNDED_STEP = 12
FUNDED_WD_EVERY = 14         # trading days (conservative vs official bi-weekly)
FUNDED_HORIZON = 504

# ===================== v2.2.1 RE-COST — ancres MESURÉES (data-only) =========
# Specs MT5 FTMO lues le 2026-06-10 (compte démo STANDARD, type swap = points).
# Mécanique validée empiriquement nuit 10->11/06 (mercredi x3) : 4/4 au centime
# (XAU 0.01=-$1.97 ; JPY 0.1=+$0.18 ; US100 0.1=-$0.64 ; GER40 0.1=-€0.394=-$0.45
# en USD compte @EURUSD 1.152). AUCUN paramètre de policy modifié (signal, vm,
# budgets, caps, margin_cap du moteur inchangés) — pré-enregistrement v2.2.1.
SPECS_READ_DATE = "2026-06-10"
SPECS_SOURCE = "FTMO-Demo Standard"
MEASURED_SPECS = {
    "XAUUSD": dict(swap_long_pts=-65.68, swap_short_pts=-14.53, triple_dow=2,
                   contract=100, digits=2, comm_side_frac=0.0000070,
                   comm_side_usd_lot=0.0),
    "USDJPY": dict(swap_long_pts=0.96, swap_short_pts=-20.30, triple_dow=2,
                   contract=100000, digits=3, comm_side_frac=0.0,
                   comm_side_usd_lot=2.5),
    "US100": dict(swap_long_pts=-637.16, swap_short_pts=27.49, triple_dow=4,
                  contract=1, digits=2, comm_side_frac=0.0, comm_side_usd_lot=0.0),
    "GER40": dict(swap_long_pts=-393.88, swap_short_pts=-48.68, triple_dow=4,
                  contract=1, digits=2, comm_side_frac=0.0, comm_side_usd_lot=0.0),
}
GER40_NOTE = "quote EUR — profit/swap convertis EUR->USD au taux marché (pas de commission)"
REF_PX_DATE = "2026-06-05"   # derniers closes panel (conversion pts->bps)
REF_PX = {"XAUUSD": 4326.70, "USDJPY": 160.28, "US100": 29973.57,
          "GER40": 25184.89, "EURUSD": 1.152}
# Marge par classe : policy v2.2 (moteur, INCHANGÉE) vs mesurée Standard vs Swing
MARGIN_RATES_POLICY = {"XAUUSD": 0.02, "USDJPY": 0.01, "US100": 0.02, "GER40": 0.02}
MARGIN_RATES_STANDARD = {"XAUUSD": 1 / 30, "USDJPY": 1 / 100,
                         "US100": 1 / 50, "GER40": 1 / 50}
MARGIN_RATES_SWING = {"XAUUSD": 1 / 9, "USDJPY": 1 / 30,
                      "US100": 1 / 15, "GER40": 1 / 15}
SWING_MARGIN_STATUS = ("levier Swing officiel FTMO (forex 1:30, indices 1:15, "
                       "métaux 1:9) — À CONFIRMER sur specs serveur Swing au déploiement")
SANITY_BOUND_SWAP_REL = 0.25   # |pts live - ancre|/|ancre| max avant alerte
SANITY_BOUND_MARGIN_REL = 0.25


def point_value_quote(sym):
    """Valeur d'un point en devise de cote, par lot = contract x 10^-digits."""
    s = MEASURED_SPECS[sym]
    return s["contract"] * 10.0 ** (-s["digits"])


def swap_bps(sym, side, px=None):
    """bps/nuit du notionnel (fx-free): pts x 10^-digits / prix x 1e4."""
    s = MEASURED_SPECS[sym]
    px = REF_PX[sym] if px is None else px
    pts = s["swap_long_pts"] if side == "long" else s["swap_short_pts"]
    return pts * 10.0 ** (-s["digits"]) / px * 1e4


def comm_rt_bps(sym):
    """Commission aller-retour en bps du notionnel (constante par construction:
    % du notionnel pour XAU, $/lot sur notionnel base-USD fixe pour USDJPY)."""
    s = MEASURED_SPECS[sym]
    rt = 2.0 * s["comm_side_frac"] * 1e4
    if s["comm_side_usd_lot"] > 0.0:           # USDJPY: $/lot sur 100k$ base
        rt += 2.0 * s["comm_side_usd_lot"] / s["contract"] * 1e4
    return rt
