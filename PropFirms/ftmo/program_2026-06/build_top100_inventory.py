"""
Build the FTMO top-100 strategy candidate inventory.

Methodology:
- 50 literature-derived hypotheses + 50 untested angles in my domain.
- Each scored on six L24 propfirm-fit dimensions for FTMO 2-step
  (5% DLL / 10% MLL, unlimited time P1/P2, no CME, news/weekend allowed in challenges).
- L24 reference: CLAUDE.md "FTMO-SUITABLE profile = high DAILY Sharpe + WR>55%
  + win/loss ratio ~1 + low kurtosis + high trade frequency"
- L21 reality check: any cited paper Sharpe is downgraded to live-net category cap
  (CS academic daily 0.3-1.2; intraday single-instr 0.8-2.0; carry/MR 1.0-2.5).
- L11/L12 cost gate: gross_per_trade / cost_per_trade >= 3.0.

FTMO costs (per PropFirms/ftmo/rules.md, last_verified 2026-06-01):
- FX major: ~1.5 bps RT (MT5 spread + ~$3 commission/lot on $10K notional ≈ 0.6 bps)
- FX cross: ~4 bps RT
- Indices: zero commission, spread only — US500/US100/GER40 ~1.5 bps, minor indices ~2.5 bps
- Crypto: 0.0325% per side commission = 6.5 bps RT + ~5 bps spread = ~12 bps total
- Metals XAUUSD: ~3.5 bps; XAGUSD ~5 bps
- Commodity CL/NG: ~8 bps RT
- Stocks: ~8 bps RT
- Overnight swap: -3 bps/night (any held position)

CSV output: top100_strategy_candidates_2026-06-04.csv
"""

import csv
import math
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

OUT_PATH = "<HOME>/Desktop/Algo_claude/PropFirms/ftmo/top100_strategy_candidates_2026-06-04.csv"

# ===========================================================================
# FTMO cost & compatibility tables
# ===========================================================================

FTMO_COST_BPS = {
    "FX_major":            1.5,
    "FX_minor":            3.0,
    "FX_cross":            4.0,
    "Index_CFD_major":     1.5,
    "Index_CFD_minor":     2.5,
    "Crypto_CFD":          12.0,
    "Metals_CFD_gold":     3.5,
    "Metals_CFD_silver":   5.0,
    "Commodity_CFD":       8.0,
    "Stocks_CFD":          8.0,
    "Multi_Asset":         3.0,
    "NOT_FTMO":            999.0,  # gate-0 fail
}

FTMO_COMPAT_SCORE = {
    "FX_major":            10,
    "FX_minor":            8,
    "FX_cross":            8,
    "Index_CFD_major":     10,
    "Index_CFD_minor":     8,
    "Crypto_CFD":          6,   # Swing-only weekend; commission heavier than CEX
    "Metals_CFD_gold":     8,
    "Metals_CFD_silver":   6,
    "Commodity_CFD":       5,   # leverage 1:10 cap, thin universe
    "Stocks_CFD":          5,   # ~150 stocks only, blocks XS strategies
    "Multi_Asset":         7,
    "NOT_FTMO":            0,
}

# ===========================================================================
# Scoring
# ===========================================================================

def score_strategy(s: dict) -> dict:
    """Compute L24 sub-scores and total. Returns dict of new fields."""
    # 1) Daily Sharpe proxy (max 25): live-realistic SR / sqrt(252)
    daily_sr = s["sr_annual_rc"] / math.sqrt(252)
    sub_daily = min(25.0, max(0.0, daily_sr * 250.0))

    # 2) Win rate (max 20): peaks at 65%, fails below 45%
    wr = s["win_rate"]
    if wr >= 0.65:
        sub_wr = 20.0
    elif wr >= 0.55:
        sub_wr = 10.0 + (wr - 0.55) * 100.0
    elif wr >= 0.45:
        sub_wr = (wr - 0.45) * 100.0
    else:
        sub_wr = 0.0

    # 3) Win/loss ratio (max 20): L24 wants ~1.0, penalises lumpy (>1.5) and weak (<0.7)
    wl = s["wl_ratio"]
    abs_dev = abs(wl - 1.0)
    if abs_dev <= 0.2:
        sub_wl = 20.0
    elif abs_dev <= 0.5:
        sub_wl = 15.0
    elif abs_dev <= 1.0:
        sub_wl = 10.0
    elif abs_dev <= 2.0:
        sub_wl = 5.0
    else:
        sub_wl = 0.0

    # 4) Trade frequency (max 15): edge must materialise inside reasonable horizon
    # FTMO P1/P2 unlimited time, but min 4 trading days and equity barrier sensitive to time
    t = s["trades_per_year"]
    if t >= 100:
        sub_freq = 15.0
    elif t >= 50:
        sub_freq = 10.0 + (t - 50) / 10.0
    elif t >= 20:
        sub_freq = 5.0 + (t - 20) / 6.0
    elif t >= 10:
        sub_freq = 2.0 + (t - 10) / 3.3
    else:
        sub_freq = max(0.0, t / 5.0)

    # 5) Cost gate (max 10): gross/cost ratio per L11
    cost = FTMO_COST_BPS.get(s["asset_class_key"], 10.0)
    gross_t = s["gross_bps_per_trade"]
    ratio = gross_t / cost if cost > 0 else 0.0
    if ratio >= 3.0:
        sub_cost = 10.0
    elif ratio >= 2.0:
        sub_cost = 7.0
    elif ratio >= 1.5:
        sub_cost = 5.0
    elif ratio >= 1.0:
        sub_cost = 2.0
    else:
        sub_cost = 0.0

    # 6) FTMO asset compatibility (max 10)
    sub_compat = FTMO_COMPAT_SCORE.get(s["asset_class_key"], 4)

    total = sub_daily + sub_wr + sub_wl + sub_freq + sub_cost + sub_compat

    if total >= 80:
        cls = "Excellent"
    elif total >= 60:
        cls = "Good"
    elif total >= 40:
        cls = "Borderline"
    else:
        cls = "Poor"

    return {
        "daily_sr_proxy":    round(daily_sr, 4),
        "ftmo_cost_bps_rt":  cost,
        "net_bps_per_trade": round(gross_t - cost, 2),
        "cost_gate_ratio":   round(ratio, 2),
        "sub_daily_sr":      round(sub_daily, 1),
        "sub_wr":            round(sub_wr, 1),
        "sub_wl":            round(sub_wl, 1),
        "sub_freq":          round(sub_freq, 1),
        "sub_cost":          round(sub_cost, 1),
        "sub_compat":        round(sub_compat, 1),
        "l24_score":         round(total, 1),
        "l24_class":         cls,
    }

# ===========================================================================
# Strategy data
# ===========================================================================

# Compact constructor — single line per strategy where possible.
# Fields: id, name, asset_class_key, ftmo_instrument, signal_family, direction,
#         holding_period, trades_per_year, win_rate, wl_ratio,
#         sr_annual_paper, sr_annual_rc, gross_bps_per_trade,
#         source, source_year, status_in_ledger, red_flags, next_action

def S(id, name, ak, instr, fam, dir, hold, t, wr, wl, srp, src_rc, gross, src, yr,
      status, flags, next_act):
    return dict(
        id=id, name=name, asset_class_key=ak, ftmo_instrument=instr,
        signal_family=fam, direction=dir, holding_period=hold,
        trades_per_year=t, win_rate=wr, wl_ratio=wl,
        sr_annual_paper=srp, sr_annual_rc=src_rc, gross_bps_per_trade=gross,
        source=src, source_year=yr, status_in_ledger=status,
        red_flags=flags, next_action=next_act,
    )


# ---------- LITERATURE (50) ----------

literature = [
    # --- FX literature (12) ---
    S("lit_001","Currency Value (PPP/REER) — Asness-Moskowitz-Pedersen",
      "FX_cross","G10 crosses basket","Value (CS)","LS","1-3 months",
      12, 0.55, 1.10, 1.00, 0.50, 80,
      "Asness Moskowitz Pedersen 2013 JF", 2013, "UNTESTED",
      "Needs N>=8 crosses, slow rebal; FTMO Swing leverage 1:30",
      "Preflight gross_alpha vs FTMO cross spreads; check post-2013 attenuation"),

    S("lit_002","Currency Carry G10 — Lustig-Roussanov-Verdelhan",
      "FX_cross","G10 basket high-low IRD","Carry (CS)","LS","1 month",
      12, 0.50, 0.80, 0.80, 0.05, 25,
      "Lustig Roussanov Verdelhan 2011 RFS", 2011, "ARCHIVED",
      "DEAD post-GFC per CLAUDE.md FX-1..FX-4; IC=-0.028 on 2013-2023",
      "DO NOT re-propose — L23/L23b regulatory + central-bank-anchoring kill"),

    S("lit_003","Currency Momentum 1-12m — Menkhoff-Sarno-Schmeling-Schrimpf",
      "FX_cross","G10 basket","Momentum (CS)","LS","1 month",
      12, 0.48, 0.85, 0.70, 0.03, 12,
      "Menkhoff et al 2012 JF", 2012, "ARCHIVED",
      "DEAD post-Menkhoff per CLAUDE.md; central-bank-anchoring kill",
      "DO NOT re-propose"),

    S("lit_004","Currency Reversal 1-month — Asness-Liew-Pedersen",
      "FX_cross","G10 crosses","Reversal (CS)","LS","1 month",
      60, 0.53, 0.95, 0.60, 0.30, 12,
      "Asness Liew Pedersen 2018 JFE", 2018, "UNTESTED",
      "Short-horizon — sensitive to FX cross spreads",
      "Check FTMO spread on EURNOK / EURSEK / NOKSEK on MT5"),

    S("lit_005","Currency Low-Volatility — Cooper-Mello-Gulen",
      "FX_cross","G10 sorted realised vol","Low-Vol (CS)","LS","1 month",
      24, 0.56, 1.05, 0.70, 0.40, 35,
      "Cooper Mello Gulen 2014 JFQA", 2014, "UNTESTED",
      "Correlated to carry — check residual after stripping carry beta",
      "Carry-orthogonal residual test"),

    S("lit_006","FX Dollar Factor — Verdelhan",
      "FX_major","DXY basket USDxxx","Macro (TS)","LS","1 month",
      12, 0.52, 1.00, 0.50, 0.30, 25,
      "Verdelhan 2018 JF", 2018, "UNTESTED",
      "Dollar pricing factor — high correlation to risk-on/off",
      "Decorrelation test vs Strategy A and personal book"),

    S("lit_007","FX Skewness Premium — Brunnermeier-Nagel-Pedersen",
      "FX_cross","G10 risk-reversal sort","Skew (CS)","LS","1 month",
      12, 0.54, 1.00, 0.80, 0.40, 55,
      "Brunnermeier Nagel Pedersen 2008 NBER ASR", 2008, "UNTESTED",
      "Needs options data for skew sort (risk-reversal vol)",
      "Source IV risk-reversals — Bloomberg or OptionMetrics"),

    S("lit_008","FX Variance Risk Premium — Della Corte-Sarno-Tsiakas",
      "FX_cross","G10 implied vs realised","Vol-Premium (CS)","LS","1 month",
      12, 0.56, 1.00, 1.00, 0.50, 60,
      "Della Corte Sarno Tsiakas 2016 RFS", 2016, "UNTESTED",
      "Needs FX option implied vol data",
      "Lit replication on Deribit FX vol or Reuters IVS"),

    S("lit_009","FX Term Structure of IV — Della Corte-Tsiakas",
      "FX_cross","G10 1M vs 12M IV slope","Vol-Slope (CS)","LS","1 month",
      12, 0.53, 1.00, 0.70, 0.35, 40,
      "Della Corte Tsiakas 2008 RFS", 2008, "UNTESTED",
      "Same data constraint as FX VRP",
      "Bundle data fetch with lit_008"),

    S("lit_010","CIP-EOQ basis — Du-Tepper-Verdelhan",
      "FX_major","EURUSD/USDJPY/GBPUSD EOQ","Basis (TS)","LS","2-5 days",
      4, 0.70, 1.20, 1.50, 0.70, 200,
      "Du Tepper Verdelhan 2018 JF", 2018, "ACTIVE",
      "Active research Forex/research/active/cip_eoq/",
      "Continue current sigma_estimation work"),

    S("lit_011","NFP-day FX overshooting fade — Andersen",
      "FX_major","EURUSD/USDJPY/GBPUSD","Event (TS)","two-sided","intraday 60-120min",
      12, 0.60, 1.00, 1.20, 0.50, 35,
      "Andersen Bollerslev Diebold Vega 2003", 2003, "UNTESTED",
      "P1/P2 news trading allowed; funded standard 2-min news block",
      "Backtest EURUSD/USDJPY post-NFP 30/60/120min fade on Dukascopy"),

    S("lit_012","Pre-NFP USD drift — Brusa",
      "FX_major","DXY components T-1 to NFP","Event (TS)","two-sided","18-24h",
      12, 0.62, 1.10, 0.90, 0.55, 25,
      "Brusa Savor Wilson 2019", 2019, "UNTESTED",
      "Possibly correlated with pre-FOMC mechanism (Lucca-Moench)",
      "Joint regression with lit_013"),

    # --- Indices CFD literature (12) ---
    S("lit_013","Pre-FOMC equity drift — Lucca-Moench",
      "Index_CFD_major","US500 / US100","Event (TS)","LO","24h FOMC-eve",
      8, 0.65, 1.40, 1.00, 0.70, 50,
      "Lucca Moench 2015 JF", 2015, "VALIDATED",
      "Personal book brique (pre-FOMC); Cieslak 2019 post-2014 attenuation",
      "Already in personal book; FTMO instance = backtest US500 CFD only"),

    S("lit_014","Overnight S&P drift — Branch-Ma / Lou-Polk-Skouras",
      "Index_CFD_major","US500 / US100","Calendar (TS)","LO","Overnight",
      252, 0.55, 1.00, 0.80, 0.55, 5,
      "Branch Ma 2012; Lou Polk Skouras 2019 JF", 2012, "VALIDATED",
      "Memory G0/G1 verified L36 candidate; swap -3 bps/night",
      "Already verified; FTMO instance needs swap-adjusted PnL"),

    S("lit_015","Turn-of-Month effect — Ariel / Lakonishok-Smidt",
      "Index_CFD_major","US500","Calendar (TS)","LO","4 trading days",
      12, 0.58, 1.20, 0.70, 0.45, 50,
      "Ariel 1987 JF; Lakonishok Smidt 1988 RFS", 1987, "UNTESTED",
      "Well-known seasonal — possibly partially decayed",
      "Check on FTMO US500 2010-2026 with day-by-day decomposition"),

    S("lit_016","Pre-CPI equity drift — Pflueger-Rinaldi",
      "Index_CFD_major","US500 / US100","Event (TS)","two-sided","6-24h",
      12, 0.60, 1.20, 0.80, 0.45, 30,
      "Pflueger Rinaldi 2020", 2020, "UNTESTED",
      "Stack with pre-FOMC/pre-NFP for higher freq (~36 evts/yr)",
      "Joint event-stack model with lit_013 + lit_012"),

    S("lit_017","Pre-NFP equity drift — Brusa-Savor-Wilson",
      "Index_CFD_major","US500 / US100","Event (TS)","LO","18-24h",
      12, 0.58, 1.10, 0.70, 0.40, 25,
      "Brusa Savor Wilson 2019", 2019, "UNTESTED",
      "Possible overlap with pre-FOMC factor",
      "Backtest on US500 CFD; joint regression with lit_013"),

    S("lit_018","Sell-in-May/Halloween — Bouman-Jacobsen",
      "Index_CFD_major","US500 / GER40","Seasonal (TS)","LO","6 months",
      2, 0.60, 1.50, 0.50, 0.20, 400,
      "Bouman Jacobsen 2002 AER", 2002, "UNTESTED",
      "Slow — 2 trades/yr fails L24 frequency badly",
      "Tag for personal book overlay, not standalone FTMO"),

    S("lit_019","Day-of-Week — French / Gibbons-Hess",
      "Index_CFD_major","US500","Calendar (TS)","LO","intraday",
      250, 0.50, 1.00, 0.20, 0.05, 1,
      "French 1980 JFE; Gibbons Hess 1981", 1980, "ARCHIVED",
      "Dead post-1990 — included for completeness",
      "Skip; baseline only"),

    S("lit_020","Intraday momentum US500 — Heston-Korajczyk-Sadka",
      "Index_CFD_major","US500","Momentum (TS)","two-sided","intraday 30-60min",
      250, 0.53, 1.00, 0.60, 0.30, 6,
      "Heston Korajczyk Sadka 2010 JF", 2010, "UNTESTED",
      "U-shape volume; some decay post-HFT 2010s",
      "Replicate on US500 CFD M5 2015-2026"),

    S("lit_021","Index opening-gap fade — Berkman-Eleswarapu-Tang",
      "Index_CFD_major","US500 / GER40","Microstructure (TS)","two-sided","30-90min",
      100, 0.60, 1.00, 0.70, 0.40, 12,
      "Berkman Eleswarapu Tang 2012", 2012, "UNTESTED",
      "Gap definition matters; daylight saving cross-check",
      "Backtest on Dukascopy/FTMO indices M5"),

    S("lit_022","VIX term carry — Johnson",
      "NOT_FTMO","VIX/VIX3M (NOT offered on FTMO)","Vol-Carry (TS)","LS","weekly",
      12, 0.50, 1.00, 1.50, 0.20, 80,
      "Johnson 2017 RFS", 2017, "ARCHIVED",
      "Gate-0 fail — FTMO has no VIX/VXX/VIX3M CFD",
      "DROP for FTMO; viable for personal book only"),

    S("lit_023","VIX-conditioned US500 intraday fade — Whaley extension",
      "Index_CFD_major","US500 conditioned VIX>20","Volatility (TS)","two-sided","60-180min",
      30, 0.60, 1.00, 0.60, 0.30, 30,
      "Whaley 1993 JF + Conrad-Wahal 2020 extension", 1993, "UNTESTED",
      "Regime filter VIX>20 reduces sample",
      "Backtest US500 M15 2015-2026 with VIX overlay"),

    S("lit_024","End-of-Quarter window dressing — Lakonishok-Shleifer-Vishny",
      "Index_CFD_major","US500 / sector ETFs","Calendar (TS)","LO","2 days",
      4, 0.65, 1.30, 0.50, 0.25, 100,
      "Lakonishok Shleifer Vishny 1991 RES", 1991, "UNTESTED",
      "4 evts/yr fails L24 frequency",
      "Tag for personal book overlay only"),

    # --- Crypto CFD literature (5) ---
    S("lit_025","BTC overnight drift Asia-EU-NY — Aleti",
      "Crypto_CFD","BTCUSD","Calendar (TS)","LO","8h block",
      365, 0.53, 1.00, 0.60, 0.20, 5,
      "Aleti 2021", 2021, "UNTESTED",
      "Crypto trades 24/7; FTMO weekend allowed on Swing",
      "Backtest BTC CFD with FTMO 6.5 bps + spread"),

    S("lit_026","ETH-BTC ratio mean reversion — Liu-Tsyvinski",
      "Crypto_CFD","ETHBTC pair CFD","StatArb (TS)","two-sided","2-10 days",
      50, 0.60, 1.00, 0.80, 0.45, 35,
      "Liu Tsyvinski 2021 RFS", 2021, "UNTESTED",
      "Needs ETHBTC quote — FTMO offers ETH but not ETHBTC pair",
      "Synthesize via ETHUSD/BTCUSD on FTMO MT5"),

    S("lit_027","Stablecoin issuance surprise — Lyons-Viswanath-Natraj",
      "Crypto_CFD","BTCUSD/ETHUSD","Flow (TS)","LO","1-3 days",
      40, 0.58, 1.10, 0.70, 0.35, 40,
      "Lyons Viswanath Natraj 2023", 2023, "UNTESTED",
      "Requires Glassnode/Nansen API for free signal; may need paid data",
      "Free-tier feasibility check on Coingecko USDT supply"),

    S("lit_028","Spot-perp basis as CFD proxy — Hyperliquid 2024",
      "Crypto_CFD","BTCUSD/ETHUSD","Basis (TS)","LO","8h-1 day",
      200, 0.62, 1.00, 1.20, 0.60, 12,
      "Hyperliquid funding rate data", 2024, "ACTIVE",
      "Strategy B-related; FTMO swap cost vs HL funding differential",
      "Bridge analysis: FTMO BTCUSD swap vs HL perp funding"),

    S("lit_029","Network momentum crypto — Yang-Zhang",
      "Crypto_CFD","BTC/ETH/SOL basket","Network (CS)","LS","1 week",
      52, 0.50, 1.10, 0.70, 0.10, 8,
      "Yang Zhang 2017 (Multi_Asset)", 2017, "ARCHIVED",
      "Universe too small post-quality-filter per CLAUDE.md archive",
      "DO NOT re-propose for crypto"),

    # --- Metals CFD literature (6) ---
    S("lit_030","Gold-Silver Ratio mean reversion — Hammoudeh-Yuan",
      "Metals_CFD_silver","XAUUSD-XAGUSD pair","StatArb (TS)","two-sided","5-20 days",
      24, 0.62, 1.10, 0.80, 0.45, 60,
      "Hammoudeh Yuan 2008", 2008, "UNTESTED",
      "Lower compat (XAG metals minor); spread cost ~5 bps RT",
      "Backtest GSR z>2 entry on XAU/XAG CFD 2010-2026"),

    S("lit_031","Gold seasonality Sep-Jan — Lucey-Pham",
      "Metals_CFD_gold","XAUUSD","Seasonal (TS)","LO","2-4 weeks",
      4, 0.65, 1.30, 0.50, 0.30, 200,
      "Lucey Pham 2017", 2017, "UNTESTED",
      "4 evts/yr — frequency cap; could combine with FOMC drift",
      "Personal book brique candidate; not FTMO standalone"),

    S("lit_032","Gold real-yield cointegration — Erb-Harvey",
      "Metals_CFD_gold","XAUUSD vs 10Y TIPS yield","Macro (TS)","LO","weeks",
      20, 0.58, 1.10, 0.60, 0.35, 50,
      "Erb Harvey 2013 FAJ", 2013, "UNTESTED",
      "Needs FRED TIPS daily; FTMO has no TIPS instrument (signal-only)",
      "Backtest signal from FRED, trade only XAUUSD CFD"),

    S("lit_033","XAU-DXY divergence fade — Reboredo",
      "Metals_CFD_gold","XAUUSD vs DXY","StatArb (TS)","two-sided","3-10 days",
      40, 0.60, 1.00, 0.70, 0.40, 30,
      "Reboredo 2013", 2013, "UNTESTED",
      "DXY via DX-USD CFD if FTMO offers, else basket synthesis",
      "Backtest XAU CFD with DXY divergence z-score signal"),

    S("lit_034","Pre-FOMC gold drift — Lucca-Moench extension to gold",
      "Metals_CFD_gold","XAUUSD","Event (TS)","LO","24h",
      8, 0.62, 1.30, 0.60, 0.35, 40,
      "Extension of Lucca-Moench 2015 to gold (Bauer 2014)", 2015, "UNTESTED",
      "Gold reacts to real-yield shocks on FOMC day",
      "Backtest XAU CFD T-1 to FOMC release on 2010-2026"),

    S("lit_035","XAU-BTC correlation regime — Bouri-Roubaud-Shahzad",
      "Metals_CFD_gold","XAUUSD conditioned BTC corr","Regime (TS)","two-sided","1-2 weeks",
      20, 0.55, 1.00, 0.50, 0.25, 30,
      "Bouri Roubaud Shahzad 2020", 2020, "UNTESTED",
      "Two-asset regime — fragile when corr=0",
      "Joint analysis with personal book TSMOM crypto signal"),

    # --- Commodity CFD literature (4) ---
    S("lit_036","CL pre-EIA Wednesday inventory drift — Symes",
      "Commodity_CFD","USOIL (WTI)","Event (TS)","two-sided","2-4h",
      52, 0.58, 1.10, 0.70, 0.40, 22,
      "Symes 2018", 2018, "UNTESTED",
      "Weekly EIA Wed 10:30 ET; FTMO leverage 1:10 cap",
      "Backtest USOIL CFD around EIA print 2015-2026"),

    S("lit_037","Brent-WTI spread mean reversion — Buyuksahin-Lee-Moser-Robe",
      "Commodity_CFD","UKOIL-USOIL spread","StatArb (TS)","two-sided","5-20 days",
      20, 0.62, 1.10, 0.80, 0.45, 70,
      "Buyuksahin Lee Moser Robe 2013 JF", 2013, "UNTESTED",
      "Both legs CFDs — combined cost ~16 bps per RT pair",
      "Pair cost-gate check; needs both UKOIL+USOIL on FTMO"),

    S("lit_038","NATGAS Thursday EIA storage drift — Linn-Zhu",
      "Commodity_CFD","NGAS (NATGAS)","Event (TS)","two-sided","1-3h",
      52, 0.56, 1.10, 0.60, 0.35, 30,
      "Linn Zhu 2020", 2020, "UNTESTED",
      "Storage report Thu 10:30 ET; NATGAS very volatile",
      "Backtest NGAS CFD around EIA print"),

    S("lit_039","Crude Friday weekly auction effect — Kawaller-Koch-Peterson",
      "Commodity_CFD","USOIL","Calendar (TS)","two-sided","intraday Fri",
      52, 0.55, 1.00, 0.40, 0.20, 12,
      "Kawaller Koch Peterson 1990 (FX/FUT)", 1990, "UNTESTED",
      "Microstructure Friday close — weak signal",
      "Cheap preflight on USOIL CFD; deprioritise"),

    # --- Stocks CFD literature (8) ---
    S("lit_040","PEAD Post-Earnings Drift — Bernard-Thomas",
      "Stocks_CFD","FTMO ~150 US stocks universe","Event (CS)","LS","5-60 days",
      150, 0.58, 1.30, 1.20, 0.55, 80,
      "Bernard Thomas 1989 JAR", 1989, "UNTESTED",
      "Universe = FTMO stocks list; SUE signal needs Estimize/Refinitiv",
      "Pull FTMO stocks list; check feasibility on free earnings data"),

    S("lit_041","52-week high momentum — George-Hwang",
      "Stocks_CFD","FTMO stocks universe","Momentum (CS)","LS","1-3 months",
      40, 0.55, 1.30, 0.80, 0.40, 90,
      "George Hwang 2004 JF", 2004, "UNTESTED",
      "Long-short on FTMO stocks — universe might be too small for XS",
      "Check if FTMO offers shorts on stocks"),

    S("lit_042","Short-term reversal — Lehmann",
      "Stocks_CFD","FTMO stocks","Reversal (CS)","LS","1 week",
      250, 0.54, 0.95, 0.60, 0.30, 20,
      "Lehmann 1990 QJE", 1990, "UNTESTED",
      "Largely from microstructure; FTMO spreads kill on small caps",
      "Filter to top-50 most liquid FTMO stocks"),

    S("lit_043","Industry momentum — Moskowitz-Grinblatt",
      "Stocks_CFD","FTMO sector groupings","Momentum (CS)","LS","1-6 months",
      24, 0.55, 1.20, 0.80, 0.45, 80,
      "Moskowitz Grinblatt 1999 JF", 1999, "UNTESTED",
      "Needs N>=10 industries within FTMO ~150 stock universe",
      "Group FTMO stocks by GICS sector"),

    S("lit_044","Insider buying signal — Cohen-Malloy-Pomorski",
      "Stocks_CFD","FTMO stocks","Insider (CS)","LO","20-60 days",
      80, 0.58, 1.30, 0.90, 0.40, 50,
      "Cohen Malloy Pomorski 2012 JF", 2012, "UNTESTED",
      "Needs SEC Form 4 data; free via EDGAR",
      "Build EDGAR scraper for FTMO universe"),

    S("lit_045","News sentiment short-term reversal — Tetlock",
      "Stocks_CFD","FTMO stocks","Event (CS)","LS","1-5 days",
      150, 0.55, 1.00, 0.70, 0.30, 20,
      "Tetlock 2007 JF", 2007, "UNTESTED",
      "Needs WSJ/NewsAPI sentiment; LLM-based scoring possible",
      "Feasibility check on NewsAPI free tier"),

    S("lit_046","Quality-minus-Junk — Asness-Frazzini-Pedersen",
      "Stocks_CFD","FTMO stocks","Quality (CS)","LS","6-12 months",
      4, 0.55, 1.20, 0.60, 0.35, 200,
      "Asness Frazzini Pedersen 2013/2018", 2018, "UNTESTED",
      "Slow rebal — 4/yr — challenge to materialise in <2 months",
      "Personal book brique candidate only"),

    S("lit_047","Low-volatility anomaly — Ang-Hodrick-Xing-Zhang",
      "Stocks_CFD","FTMO stocks ranked beta","Low-Vol (CS)","LS","1-3 months",
      12, 0.55, 1.10, 0.55, 0.30, 60,
      "Ang Hodrick Xing Zhang 2006/2009", 2006, "UNTESTED",
      "Needs beta estimation — survivorship-prone",
      "Use FTMO universe with rolling beta vs S&P"),

    # --- FX microstructure / round-number (3) ---
    S("lit_048","Round-number bounce intraday — Osler",
      "FX_major","EURUSD/USDJPY 00 / 50 levels","Microstructure (TS)","two-sided","30-90min",
      150, 0.58, 1.00, 0.70, 0.30, 6,
      "Osler 2003 RFS", 2003, "UNTESTED",
      "Possibly attenuated since 2010s algos; check post-2015 sample",
      "Backtest EURUSD M5 with 50-pip and 100-pip levels"),

    S("lit_049","Order Flow Imbalance — Cont-Kukanov-Stoikov",
      "FX_major","EURUSD top-of-book","Microstructure (TS)","two-sided","intraday seconds-min",
      2000, 0.55, 0.95, 1.50, 0.20, 1,
      "Cont Kukanov Stoikov 2014 JFM", 2014, "UNTESTED",
      "L23b HFT-mediated; retail FTMO spread tier cannot capture",
      "Likely cost-gate fail — skip standalone, consider OFI as filter"),

    S("lit_050","Triangular cointegration residual — Aiba-Hatano",
      "FX_major","EUR/USD/GBP triangular basket","StatArb (TS)","LS","intraday minutes",
      2000, 0.52, 0.95, 1.00, 0.10, 1,
      "Aiba Hatano 2002", 2002, "UNTESTED",
      "L23b HFT-only — execution speed kills retail at any FTMO spread",
      "Skip standalone"),
]


# ---------- UNTESTED ANGLES (50) ----------

untested = [
    # --- FX intraday angles (15) ---
    S("ang_001","EURUSD London-NY overlap range break (13:00-16:00 GMT)",
      "FX_major","EURUSD M5/M15","Breakout (TS)","two-sided","intraday 1-3h",
      150, 0.45, 1.50, None, 0.40, 12,
      "Untested angle — overlap session volume peak", 2026, "UNTESTED",
      "Breakout = lumpy; L11b binary-TP/SL gate must hold",
      "Pre-flight IJR + alt binary gate; Dukascopy EURUSD M5 2018-2026"),

    S("ang_002","GBPUSD pre-BoE 1h drift (T-60 to 12:00 GMT)",
      "FX_major","GBPUSD","Event (TS)","LO/SS","60min",
      8, 0.62, 1.10, None, 0.50, 35,
      "Untested angle — central bank announcement pre-drift", 2026, "UNTESTED",
      "Only 8 evts/yr; stack with other CB pre-drifts for freq",
      "Backtest GBPUSD M5 pre-BoE 2010-2026"),

    S("ang_003","USDJPY post-BoJ statement fade (60min)",
      "FX_major","USDJPY","Event (TS)","two-sided","60min",
      8, 0.58, 1.00, None, 0.40, 30,
      "Untested angle — BoJ press conf overreaction", 2026, "UNTESTED",
      "BoJ rare moves; 8 evts/yr",
      "Backtest USDJPY M5 BoJ days 2015-2026"),

    S("ang_004","AUDUSD-NZDUSD pair MR (RBA-RBNZ rate diff conditioned)",
      "FX_major","AUDUSD-NZDUSD spread","StatArb (TS)","two-sided","2-10 days",
      30, 0.60, 1.10, None, 0.40, 50,
      "Untested angle — Antipodean rate-diff pair", 2026, "UNTESTED",
      "Both legs CFDs — combined cost ~3 bps per RT pair",
      "Backtest spread z-score with rate-diff overlay"),

    S("ang_005","USDCAD oil-correlation regime conditional MR",
      "FX_major","USDCAD conditioned oil corr","Regime (TS)","two-sided","3-10 days",
      30, 0.58, 1.05, None, 0.35, 40,
      "Untested angle — CAD as oil proxy", 2026, "UNTESTED",
      "Regime filter shrinks sample",
      "Backtest with rolling 30d correlation as regime filter"),

    S("ang_006","EURUSD pre-FOMC drift (mirror of Lucca-Moench)",
      "FX_major","EURUSD","Event (TS)","LO/SS","24h",
      8, 0.62, 1.20, None, 0.55, 40,
      "Untested angle — pre-FOMC anomaly extended to FX", 2026, "UNTESTED",
      "Pre-FOMC effect documented on equities; FX direction unclear",
      "Backtest EURUSD T-1 to FOMC release 2010-2026"),

    S("ang_007","EURGBP intraday Brexit-vol regime fade",
      "FX_cross","EURGBP","Regime (TS)","two-sided","intraday 1-2h",
      80, 0.57, 1.00, None, 0.30, 18,
      "Untested angle — cross fade in post-Brexit vol regime", 2026, "UNTESTED",
      "Cross with FX spread cost 4 bps RT — tighter gate",
      "Backtest EURGBP M15 2017-2026 with vol regime"),

    S("ang_008","USDCHF SNB-day post-statement fade",
      "FX_major","USDCHF","Event (TS)","two-sided","60min",
      4, 0.58, 1.05, None, 0.30, 35,
      "Untested angle — SNB rate decisions ~quarterly", 2026, "UNTESTED",
      "Only 4/yr; SNB very rate-decision-quiet recently",
      "Stack with other CB days"),

    S("ang_009","EURNOK liquidity-condition contrarian",
      "FX_cross","EURNOK","Microstructure (TS)","two-sided","1-3 days",
      40, 0.55, 1.00, None, 0.25, 25,
      "Untested angle — NOK low-vol cross MR", 2026, "UNTESTED",
      "Cross spread ~4 bps; weak edge expectation",
      "Check FTMO EURNOK availability and live spreads"),

    S("ang_010","USDMXN macro-surprise fade",
      "FX_minor","USDMXN","Event (TS)","two-sided","2-8h",
      24, 0.55, 1.05, None, 0.25, 25,
      "Untested angle — EM FX overshoot fade post-macro", 2026, "UNTESTED",
      "Minor FX higher spread + funding cost",
      "Check FTMO USDMXN availability"),

    S("ang_011","NFP-release minute reversal (09:00-10:00 ET)",
      "FX_major","EURUSD post-NFP","Event (TS)","two-sided","30-60min",
      12, 0.60, 1.00, None, 0.45, 28,
      "Untested angle — NFP impulse fade vs Andersen lit", 2026, "UNTESTED",
      "P1/P2 news allowed; funded standard 2-min block",
      "Backtest M1 reversal at NFP release"),

    S("ang_012","CPI release first-30min fade",
      "FX_major","EURUSD/USDJPY post-CPI","Event (TS)","two-sided","30min",
      12, 0.58, 1.00, None, 0.40, 22,
      "Untested angle — CPI overshoot fade", 2026, "UNTESTED",
      "Stack with NFP/FOMC for freq",
      "Joint event-fade backtest on EURUSD M1"),

    S("ang_013","EURUSD intraday momentum (Heston-Korajczyk applied to FX)",
      "FX_major","EURUSD M15-H1","Momentum (TS)","two-sided","intraday 1-3h",
      400, 0.53, 1.00, None, 0.25, 4,
      "Untested angle — intraday TS momentum extended to FX", 2026, "UNTESTED",
      "Per-trade gross small; needs careful cost gate",
      "Lit replication on EURUSD M15 with H1 bucketing"),

    S("ang_014","FX cross spread arb residual (EURGBP - EURUSD/GBPUSD)",
      "FX_cross","Three-pair triangular residual","StatArb (TS)","two-sided","intraday minutes",
      500, 0.55, 0.95, None, 0.20, 2,
      "Untested angle — cross-rate residual fade (retail-tier)", 2026, "UNTESTED",
      "L23b HFT competition; expect cost-gate fail",
      "Quick preflight; expect skip"),

    S("ang_015","USDJPY VIX-conditioned MR",
      "FX_major","USDJPY conditioned VIX>20","Regime (TS)","two-sided","1-3 days",
      40, 0.58, 1.00, None, 0.30, 25,
      "Untested angle — JPY safe-haven regime MR", 2026, "UNTESTED",
      "VIX as conditioning, traded via USDJPY CFD",
      "Backtest USDJPY D1 2010-2026 with VIX overlay"),

    # --- Indices CFD intraday angles (10) ---
    S("ang_016","US100 first 15-min opening drift (post 09:30 ET)",
      "Index_CFD_major","US100","Microstructure (TS)","two-sided","15-30min",
      250, 0.55, 1.00, None, 0.35, 8,
      "Untested angle — Nasdaq open momentum filter", 2026, "UNTESTED",
      "ORB-like structure; lessons from V2+E7 placebo apply",
      "Decouple from K5 placebo: signal must be edge not no-bust math"),

    S("ang_017","US500 lunch fade 11:30-13:30 ET",
      "Index_CFD_major","US500","Microstructure (TS)","two-sided","60-120min",
      200, 0.57, 1.00, None, 0.30, 10,
      "Untested angle — lunch-hour mean reversion", 2026, "UNTESTED",
      "U-shape volume implies fade in low-volume window",
      "Backtest US500 M15 2015-2026 lunch hour"),

    S("ang_018","GER40 post-US-open lag fade (15:30-17:00 CET)",
      "Index_CFD_major","GER40","Lag (TS)","two-sided","60-90min",
      200, 0.56, 1.00, None, 0.30, 12,
      "Untested angle — DAX overreaction to US open", 2026, "UNTESTED",
      "Check Dukascopy DAX or FTMO MT5 for data",
      "Backtest GER40 M5 2015-2026"),

    S("ang_019","UK100 morning gap close probability",
      "Index_CFD_major","UK100","Gap (TS)","two-sided","intraday",
      150, 0.62, 1.00, None, 0.40, 12,
      "Untested angle — FTSE gap fill", 2026, "UNTESTED",
      "Gap fills well documented on indices",
      "Backtest UK100 D1 gaps with intraday fill probability"),

    S("ang_020","US100-US500 ratio MR (NDX/SPX > 2σ)",
      "Index_CFD_major","US100-US500 pair","StatArb (TS)","two-sided","2-10 days",
      30, 0.60, 1.10, None, 0.40, 50,
      "Untested angle — tech-vs-broad spread fade", 2026, "UNTESTED",
      "2010-2024 secular Nasdaq outperformance breaks stationarity",
      "Test rolling cointegration; signal valid only when stationary"),

    S("ang_021","JPN225-USDJPY hedged carry",
      "Index_CFD_minor","JPN225 + USDJPY hedge","Carry (TS)","LO","weeks",
      20, 0.58, 1.20, None, 0.40, 80,
      "Untested angle — Nikkei + FX hedge for USD-investors", 2026, "UNTESTED",
      "Two-leg CFD costs add up; check FTMO JPN225 spread",
      "Backtest JPN225 + USDJPY hedged on FTMO instruments"),

    S("ang_022","VIX>20 US500 intraday range fade",
      "Index_CFD_major","US500 conditioned VIX>20","Volatility (TS)","two-sided","60-180min",
      40, 0.60, 1.00, None, 0.35, 28,
      "Untested angle — high-vol regime MR", 2026, "UNTESTED",
      "Regime filter shrinks sample but lifts edge per L15 caveat",
      "Backtest US500 M15 with VIX>20 conditioning"),

    S("ang_023","US500 close auction skew 15:55-16:00 ET",
      "Index_CFD_major","US500","Microstructure (TS)","two-sided","5-15min",
      252, 0.57, 1.00, None, 0.25, 4,
      "Untested angle — close auction MOC imbalance fade", 2026, "UNTESTED",
      "Very short — requires precise execution; FTMO CFD close differs from cash",
      "Confirm FTMO US500 closing time matches NYSE close"),

    S("ang_024","US500 2-day momentum continuation low-vol only",
      "Index_CFD_major","US500 conditioned VIX<15","Momentum (TS)","LO","2 days",
      80, 0.58, 1.20, None, 0.35, 20,
      "Untested angle — short-momentum in calm regime", 2026, "UNTESTED",
      "L15 lift expected modest on high-SR base",
      "Backtest US500 D1 with VIX<15 conditioning"),

    S("ang_025","Index overnight gap fill (within 24h)",
      "Index_CFD_major","US500/GER40 overnight gap","Gap (TS)","two-sided","intraday",
      120, 0.65, 1.10, None, 0.45, 18,
      "Untested angle — gap-fill probability classical", 2026, "UNTESTED",
      "Multi-instrument can add freq",
      "Backtest US500+GER40+UK100 gap fill on FTMO M15"),

    # --- Crypto CFD angles (4) ---
    S("ang_026","BTC weekend gap close probability",
      "Crypto_CFD","BTCUSD","Gap (TS)","two-sided","intraday Mon",
      52, 0.62, 1.10, None, 0.35, 40,
      "Untested angle — crypto weekend gap fill", 2026, "UNTESTED",
      "FTMO crypto Swing-only for weekend hold",
      "Backtest BTCUSD CFD weekend gap fill probability"),

    S("ang_027","ETH-BTC ratio CFD MR (NOT TSMOM)",
      "Crypto_CFD","ETHUSD/BTCUSD synthetic","StatArb (TS)","two-sided","3-15 days",
      40, 0.58, 1.05, None, 0.40, 35,
      "Untested angle — synth ratio via two FTMO crypto pairs", 2026, "UNTESTED",
      "Double the CFD cost = ~24 bps RT — tight gate",
      "Backtest synth ratio with z>2 entries"),

    S("ang_028","Crypto Asia-open (00:00 UTC) 15min range fade",
      "Crypto_CFD","BTCUSD/ETHUSD","Microstructure (TS)","two-sided","15-45min",
      365, 0.55, 1.00, None, 0.25, 8,
      "Untested angle — Asia open fade analogous to FX London", 2026, "UNTESTED",
      "Crypto already 24/7 — no clear 'open' but Asia institutional flow",
      "Backtest BTC CFD M5 00:00 UTC window 2020-2026"),

    S("ang_029","BTC swap-carry harvesting (FTMO swap gradient)",
      "Crypto_CFD","BTCUSD vs FTMO swap","Basis (TS)","LO/SS","1-5 days",
      80, 0.60, 1.00, None, 0.35, 25,
      "Untested angle — exploit FTMO BTC swap rate vs spot drift", 2026, "UNTESTED",
      "Critical unknown: FTMO BTC swap rate (need MT5 SPEC verification)",
      "PRECOND: extract swap_long/swap_short via mq5 ExportSpecs script"),

    # --- Metals CFD angles (4) ---
    S("ang_030","XAUUSD Asia drift after US close (22:00-08:00 GMT)",
      "Metals_CFD_gold","XAUUSD","Calendar (TS)","two-sided","8h block",
      252, 0.55, 1.00, None, 0.30, 8,
      "Untested angle — gold Asia session overnight drift", 2026, "UNTESTED",
      "Swap cost -3 bps/night may dominate edge",
      "Backtest XAU CFD with swap-adjusted PnL"),

    S("ang_031","XAUUSD-XAGUSD ratio MR refined",
      "Metals_CFD_silver","Gold-Silver Ratio CFD pair","StatArb (TS)","two-sided","5-30 days",
      24, 0.62, 1.10, None, 0.45, 65,
      "Untested angle — refined GSR signal (LCB regime)", 2026, "UNTESTED",
      "Both metals CFDs; combined cost ~8.5 bps RT pair",
      "Backtest XAU/XAG 2010-2026 with regime conditioning"),

    S("ang_032","XAUUSD pre-NFP drift (mirror of equities)",
      "Metals_CFD_gold","XAUUSD","Event (TS)","two-sided","24h",
      12, 0.58, 1.15, None, 0.40, 30,
      "Untested angle — gold pre-NFP", 2026, "UNTESTED",
      "Joint with lit_017 pre-NFP equities for cross-asset signal",
      "Backtest XAU CFD T-1 to NFP 2010-2026"),

    S("ang_033","XAUUSD real-yield divergence fade intraday",
      "Metals_CFD_gold","XAU vs 10Y TIPS","Macro (TS)","two-sided","2-8h",
      80, 0.58, 1.00, None, 0.35, 20,
      "Untested angle — intraday gold-yield gap", 2026, "UNTESTED",
      "Needs FRED TIPS daily; intraday TIPS via Bloomberg",
      "Daily TIPS signal applied to intraday gold MR"),

    # --- Commodity CFD angles (3) ---
    S("ang_034","USOIL EIA Wed pre-release drift (refined hour bucket)",
      "Commodity_CFD","USOIL","Event (TS)","two-sided","60-120min",
      52, 0.60, 1.10, None, 0.45, 28,
      "Untested angle — refinement of lit_036 with hour bucketing", 2026, "UNTESTED",
      "Leverage 1:10 cap limits sizing",
      "Backtest USOIL M5 T-90 to EIA print 2018-2026"),

    S("ang_035","NATGAS Thursday EIA storage drift (refined)",
      "Commodity_CFD","NGAS","Event (TS)","two-sided","60-120min",
      52, 0.57, 1.05, None, 0.35, 25,
      "Untested angle — refinement of lit_038", 2026, "UNTESTED",
      "NATGAS very volatile; tight stop logic critical",
      "Backtest NGAS M5 T-60 to EIA print"),

    S("ang_036","UKOIL-USOIL Brent-WTI spread MR",
      "Commodity_CFD","UKOIL-USOIL pair","StatArb (TS)","two-sided","3-15 days",
      30, 0.62, 1.10, None, 0.40, 55,
      "Untested angle — refinement of lit_037 with regime gating", 2026, "UNTESTED",
      "Geopolitical regime fragility (Russia/Iran)",
      "Backtest spread with VIX-or-DXY regime overlay"),

    # --- Single-name stocks CFD angles (6) ---
    S("ang_037","PEAD on FTMO 150-stock universe",
      "Stocks_CFD","FTMO US stocks","Event (CS)","LS","5-60 days",
      150, 0.58, 1.30, None, 0.45, 70,
      "Untested angle — application of lit_040 to FTMO universe", 2026, "UNTESTED",
      "Universe small but high-quality (mega/large cap)",
      "Pull FTMO stocks list; bind with Yahoo earnings calendar"),

    S("ang_038","52-week-high breakout on FTMO universe",
      "Stocks_CFD","FTMO US stocks","Momentum (CS)","LO","1-3 months",
      40, 0.55, 1.30, None, 0.35, 75,
      "Untested angle — application of lit_041", 2026, "UNTESTED",
      "Need FTMO long-only constraint check (no short on some stocks?)",
      "Verify FTMO stock short availability"),

    S("ang_039","Mega-cap pre-earnings drift (FTMO stocks)",
      "Stocks_CFD","FTMO megacap (AAPL/MSFT/NVDA/etc)","Event (CS)","LO","5-10 days",
      40, 0.60, 1.30, None, 0.40, 80,
      "Untested angle — pre-earnings IV crush avoidance", 2026, "UNTESTED",
      "Top mega-cap quarterly earnings drift documented",
      "Filter FTMO universe to top 30 by market cap"),

    S("ang_040","Tech sector pair MR (single names)",
      "Stocks_CFD","FTMO tech pairs (AAPL/MSFT, NVDA/AMD)","StatArb (CS)","LS","3-10 days",
      80, 0.58, 1.00, None, 0.35, 50,
      "Untested angle — pairs trading in FTMO single names", 2026, "UNTESTED",
      "Limited universe — only a few viable pairs",
      "Cointegration test on top-30 FTMO stocks; survive 2020-2026"),

    S("ang_041","Stock 1-day reversal (Lehmann variant on FTMO)",
      "Stocks_CFD","FTMO US stocks","Reversal (CS)","LS","1 day",
      250, 0.54, 0.95, None, 0.25, 15,
      "Untested angle — Lehmann applied to FTMO universe", 2026, "UNTESTED",
      "Microstructure-driven; FTMO spreads kill",
      "Filter to top-30 most liquid; test net of FTMO spreads"),

    S("ang_042","Pre-FOMC mega-cap drift differential",
      "Stocks_CFD","FTMO mega-caps","Event (CS)","LS","24h",
      8, 0.62, 1.20, None, 0.45, 60,
      "Untested angle — Lucca-Moench applied at single-name level", 2026, "UNTESTED",
      "Trade FTMO mega-caps long vs equal-weight short",
      "Backtest single-name pre-FOMC on FTMO stocks"),

    # --- Event-driven cross-asset (4) ---
    S("ang_043","Pre-NFP USD basket drift",
      "FX_major","DXY-like basket via FTMO majors","Event (TS)","two-sided","18-24h",
      12, 0.60, 1.10, None, 0.50, 30,
      "Untested angle — multi-FX basket pre-NFP", 2026, "UNTESTED",
      "Equal-weight basket reduces single-pair noise",
      "Combine lit_012 + ang_011 into basket"),

    S("ang_044","Post-CPI 1h reversal cross-asset",
      "Multi_Asset","EURUSD + US500 + XAU","Event (TS)","two-sided","60min",
      36, 0.58, 1.00, None, 0.35, 25,
      "Untested angle — cross-asset CPI overshoot basket", 2026, "UNTESTED",
      "Aggregate signal across asset classes",
      "Joint backtest M1 reversal on 3 instruments at CPI release"),

    S("ang_045","Post-ECB EUR cross fade (60min)",
      "FX_cross","EURGBP / EURCHF / EURJPY","Event (TS)","two-sided","60min",
      8, 0.58, 1.00, None, 0.30, 30,
      "Untested angle — ECB overreaction across EUR crosses", 2026, "UNTESTED",
      "Cross spread cost 4 bps RT each leg",
      "Multi-cross backtest at ECB rate decisions"),

    S("ang_046","Pre-BoJ JPY basket fade",
      "FX_major","USDJPY/EURJPY/AUDJPY","Event (TS)","two-sided","24h",
      8, 0.55, 1.00, None, 0.25, 25,
      "Untested angle — JPY basket pre-BoJ", 2026, "UNTESTED",
      "BoJ very predictable recently — low edge expectation",
      "Quick preflight; deprioritise"),

    # --- Composite / multi-asset (4) ---
    S("ang_047","EURUSD-GBPUSD divergence fade",
      "FX_major","EUR-GBP residual","StatArb (TS)","two-sided","1-5 days",
      80, 0.58, 1.00, None, 0.35, 28,
      "Untested angle — major-major divergence", 2026, "UNTESTED",
      "Cointegration test with rolling window",
      "Backtest EURUSD-GBPUSD residual z>1.5 2015-2026"),

    S("ang_048","US100-US500 ratio + VIX-conditioned MR",
      "Index_CFD_major","NDX/SPX with VIX overlay","Regime (TS)","two-sided","2-10 days",
      50, 0.60, 1.10, None, 0.40, 50,
      "Untested angle — combination ang_020 + VIX regime", 2026, "UNTESTED",
      "Best variant of NDX-SPX pair with explicit regime filter",
      "Backtest with VIX>18 conditioning for stationarity"),

    S("ang_049","Multi-FX volatility-targeted basket (low-vol cross MR)",
      "FX_cross","Top-3 lowest-vol G10 crosses","Low-Vol (CS)","LS","1-2 weeks",
      52, 0.56, 1.05, None, 0.40, 35,
      "Untested angle — vol-targeted basket MR", 2026, "UNTESTED",
      "Cross cost 4 bps RT — multi-leg eats edge",
      "Backtest top-3 lowest-vol crosses with weekly rebal"),

    S("ang_050","Cross-asset risk-off rotation (JPY+gold+US500-)",
      "Multi_Asset","USDJPY-/XAU+/US500-","Regime (TS)","LS","1-3 weeks",
      30, 0.58, 1.10, None, 0.45, 60,
      "Untested angle — RoRo basket conditional VIX/CDS", 2026, "UNTESTED",
      "Multi-asset L24 fit; complex but high diversification",
      "Build composite RoRo signal; backtest on FTMO instruments"),
]


# ===========================================================================
# Build CSV
# ===========================================================================

def build_csv():
    all_strats = literature + untested
    assert len(all_strats) == 100, f"Got {len(all_strats)} strategies, expected 100"

    rows = []
    for s in all_strats:
        scored = score_strategy(s)
        row = {**s, **scored}
        rows.append(row)

    rows.sort(key=lambda r: -r["l24_score"])
    for i, r in enumerate(rows):
        r["rank"] = i + 1

    cols = [
        "rank", "id", "name",
        "asset_class_key", "ftmo_instrument",
        "signal_family", "direction", "holding_period",
        "trades_per_year", "win_rate", "wl_ratio",
        "sr_annual_paper", "sr_annual_rc", "daily_sr_proxy",
        "gross_bps_per_trade", "ftmo_cost_bps_rt", "net_bps_per_trade",
        "cost_gate_ratio",
        "sub_daily_sr", "sub_wr", "sub_wl", "sub_freq", "sub_cost", "sub_compat",
        "l24_score", "l24_class",
        "status_in_ledger", "red_flags",
        "source", "source_year", "next_action",
    ]

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote {len(rows)} strategies to {OUT_PATH}")

    # Summary stats
    excellent = sum(1 for r in rows if r["l24_class"] == "Excellent")
    good = sum(1 for r in rows if r["l24_class"] == "Good")
    borderline = sum(1 for r in rows if r["l24_class"] == "Borderline")
    poor = sum(1 for r in rows if r["l24_class"] == "Poor")
    print(f"  Excellent (>=80): {excellent}")
    print(f"  Good (60-79):     {good}")
    print(f"  Borderline (40-59): {borderline}")
    print(f"  Poor (<40):       {poor}")

    untested_count = sum(1 for r in rows if r["status_in_ledger"] == "UNTESTED")
    archived_count = sum(1 for r in rows if r["status_in_ledger"] == "ARCHIVED")
    active_count = sum(1 for r in rows if r["status_in_ledger"] == "ACTIVE")
    validated_count = sum(1 for r in rows if r["status_in_ledger"] == "VALIDATED")
    print(f"  Status: UNTESTED={untested_count}  ARCHIVED={archived_count}  ACTIVE={active_count}  VALIDATED={validated_count}")

    top10 = rows[:10]
    print("\nTop 10 by L24 score:")
    for r in top10:
        print(f"  #{r['rank']:>2}  {r['l24_score']:>5.1f} [{r['l24_class']:<10}]  {r['id']}  {r['name'][:65]}")


if __name__ == "__main__":
    build_csv()
