"""Crosswalk: which of the 118 catalogued edges can the marginal test actually reach?

The binding constraint of this study is a *saved daily return stream*. An edge with a
t-stat in a report and no series cannot be joined to the book calendar, so it has no
rho, no Delta SR and no Delta p(pass) — it is unreachable regardless of how strong it
looks. Counting that population is a deliverable in itself: it says how much of the
repo is even *eligible* for a portfolio-level decision rule.

Mapping is manual and conservative: an inventory row is marked RECOVERED only when a
harvested series is the same construction, not merely the same family. Where a series
is a close but non-identical proxy it is marked PROXY and named.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parent

# id -> (status, series_name, note)
#   RECOVERED  : a daily series for this exact construction is in the panel
#   PROXY      : same edge, different but faithful implementation
#   NO_SERIES  : measured, but only summary stats / trade counts were persisted
#   NON_DAILY  : series exists but is monthly or event-level, unusable for a daily barrier
#   NEVER_MEASURED : no numbers were ever produced
MAP: dict[str, tuple[str, str, str]] = {
    "E001": ("RECOVERED", "B1_month_end_bonds", "growth_engine audit series"),
    "E002": ("PROXY", "ovn_GOLD_fut", "exchange-anchored futures rebuild (L56), not the 23:00-07:00 UTC CFD sleeve"),
    "E003": ("PROXY", "ovn_SILVER_fut", "idem"),
    "E004": ("PROXY", "ovn_WTI_fut", "idem"),
    "E005": ("PROXY", "ovn_SOYBEAN_fut", "N=313 only, CFD window never existed"),
    "E006": ("NO_SERIES", "", "January seasonality: event tables only"),
    "E007": ("NO_SERIES", "", "platinum, no CFD/futures series persisted"),
    "E008": ("NO_SERIES", "", ""),
    "E009": ("NO_SERIES", "", "combined precious-Q1 basket never written out"),
    "E010": ("NO_SERIES", "", "COFFEE July"),
    "E011": ("NO_SERIES", "", "WHEAT May"),
    "E012": ("RECOVERED", "gapA_S035_point", "rebuilt from the trade ledger by build_extra.py"),
    "E013": ("RECOVERED", "gapB_S036_point", "idem"),
    "E014": ("NO_SERIES", "", "S1 VRP QQQ: IC scans and PNGs only; net-futures 0.454 exists as a scalar"),
    "E015": ("NO_SERIES", "", "VIX-term carry timed"),
    "E016": ("NO_SERIES", "", "1-day SPX reversal: never written out"),
    "E017": ("NO_SERIES", "", "VIX expiry SOQ"),
    "E018": ("NO_SERIES", "", "lev-ETF EOD flow"),
    "E019": ("RECOVERED", "Long_vol_VXX", ""),
    "E020": ("RECOVERED", "auction_ZN_post", "event ledger from the 2026-07-30 session"),
    "M001": ("RECOVERED", "cs_macro_V1_panel", ""),
    "M002": ("PROXY", "paper_fomc_long_even", "FTMO paper-edge replication of the same window"),
    "M003": ("NO_SERIES", "", "overlay on the book, not a sleeve — out of scope by construction"),
    "M004": ("RECOVERED", "dec_H2_resid_port", ""),
    "M005": ("RECOVERED", "dec_H1_goldsilver", ""),
    "M006": ("NO_SERIES", "", "piste B: parameter grid only"),
    "M007": ("RECOVERED", "dec_pisteC_best", ""),
    "M008": ("NO_SERIES", "", "Strategy C iter_10: results.json, no daily stream"),
    "M009": ("RECOVERED", "orb_e7_R15", "R units; scale-invariant under ERC"),
    "M010": ("NO_SERIES", "", "look-ahead artefact, excluded on merit anyway"),
    "M011": ("RECOVERED", "s076_mtm_fx", "Ross Hook replication"),
    "M012": ("NO_SERIES", "", "oxfordstrat cohort: gates.csv only"),
    "M013": ("NO_SERIES", "", "idem"),
    "M014": ("NO_SERIES", "", "idem"),
    "M015": ("NO_SERIES", "", "ORB-stop cohort, ~8 strategies"),
    "M016": ("PROXY", "EMA_50_200/Donchian_55/Momentum_MA200", "~40-entry trend cohort, 4 representatives"),
    "M017": ("NO_SERIES", "", "candle-pattern cohort"),
    "M018": ("NO_SERIES", "", "RSI(2) Connors"),
    "M019": ("NO_SERIES", "", "Friday momentum"),
    "M020": ("NO_SERIES", "", "Gao time-of-day"),
    "M021": ("NO_SERIES", "", ""),
    "M022": ("NO_SERIES", "", "CPI/NFP gap continuation"),
    "M023": ("NO_SERIES", "", "pre-CPI"),
    "M024": ("NO_SERIES", "", "pre-NFP"),
    "M025": ("NO_SERIES", "", "pre-CB"),
    "M026": ("NO_SERIES", "", "post-limit-move"),
    "M027": ("PROXY", "paper_overnight_fade", "gap-fade family"),
    "M028": ("NON_DAILY", "swapkilled ME_*", "monthly, 125 obs"),
    "M029": ("NON_DAILY", "swapkilled ME_US", "monthly"),
    "M030": ("NON_DAILY", "", "monthly"),
    "M031": ("NO_SERIES", "", ""),
    "M032": ("NO_SERIES", "", ""),
    "M033": ("NO_SERIES", "", "overnight conditional"),
    "M034": ("NO_SERIES", "", "OPEX"),
    "M035": ("NO_SERIES", "", "copper lead-lag"),
    "M036": ("NO_SERIES", "", ""),
    "M037": ("NO_SERIES", "", ""),
    "M038": ("NO_SERIES", "", ""),
    "M039": ("NO_SERIES", "", ""),
    "M040": ("NO_SERIES", "", ""),
    "M041": ("NO_SERIES", "", ""),
    "M042": ("NO_SERIES", "", "regime filters, overlay not sleeve"),
    "M043": ("NO_SERIES", "", "signal filters on TSMOM, overlay"),
    "M044": ("NO_SERIES", "", "survival overlays"),
    "M045": ("NO_SERIES", "", ""),
    "M046": ("PROXY", "Pullback_uptrend", "5-day reversion cohort"),
    "M047": ("RECOVERED", "tsmom_chosen", "the FTMO TSMOM engine"),
    "M048": ("RECOVERED", "Donchian_breakout", ""),
    "M049": ("RECOVERED", "XS_momentum", ""),
    "M050": ("RECOVERED", "Pullback_uptrend", ""),
    "M051": ("RECOVERED", "MACD_cross", ""),
    "M052": ("RECOVERED", "commodity_seasonality", ""),
    "M053": ("NON_DAILY", "swapkilled spreads", "monthly"),
    "M054": ("RECOVERED", "growth_trend", ""),
    "M055": ("NO_SERIES", "", "long-convexity straddle"),
    "M056": ("NO_SERIES", "", "sizing overlays, create no edge by construction"),
    "M057": ("NO_SERIES", "", "PCA stat-arb"),
    "M058": ("NO_SERIES", "", "COT"),
    "M059": ("NON_DAILY", "swapkilled 13 sleeves", "monthly"),
    "M060": ("NO_SERIES", "", "month-end FX flow"),
    "M061": ("NO_SERIES", "", ""),
    "M062": ("NO_SERIES", "", ""),
    "M063": ("NO_SERIES", "", ""),
    "M064": ("NO_SERIES", "", ""),
    "R001": ("RECOVERED", "btc_proxy_A", "Strategy A crypto TSMOM proxy series"),
    "R002": ("NO_SERIES", "", "delta-neutral carry: walkforward table only"),
    "R003": ("RECOVERED", "crypto_trend_cfd", ""),
    "R004": ("NO_SERIES", "", "unlock cliff: event table"),
    "R005": ("NO_SERIES", "", "funding extremes: event table"),
    "R006": ("NO_SERIES", "", ""),
    "R007": ("NO_SERIES", "", ""),
    "R008": ("NO_SERIES", "", ""),
    "R009": ("NO_SERIES", "", "SPY iron condor"),
    "R010": ("NO_SERIES", "", ""),
    "R011": ("NO_SERIES", "", "PEAD"),
    "R012": ("NO_SERIES", "", ""),
    "R013": ("NO_SERIES", "", ""),
    "R014": ("NO_SERIES", "", ""),
    "R015": ("NO_SERIES", "", "WMR fix reversal"),
    "R016": ("NO_SERIES", "", "G10 carry"),
    "R017": ("NO_SERIES", "", ""),
    "R018": ("PROXY", "top10_lit_048", "round-number cascade, funnel line"),
    "R019": ("NO_SERIES", "", "CIP-EOQ"),
    "R020": ("NO_SERIES", "", ""),
    "R021": ("NO_SERIES", "", ""),
    "R022": ("NO_SERIES", "", ""),
    "R023": ("NO_SERIES", "", "Strategy D D3+D5"),
    "R024": ("NO_SERIES", "", ""),
    "R025": ("NO_SERIES", "", ""),
    "R026": ("NO_SERIES", "", ""),
    # D-series: killed on DATA availability, so by construction no series exists.
    "D001": ("NO_SERIES", "", "dispersion — needs component IV"),
    "D002": ("NO_SERIES", "", "dividend futures"),
    "D003": ("NO_SERIES", "", "index reconstitution flows"),
    "D004": ("NO_SERIES", "", "OPEX dealer gamma"),
    "D005": ("NO_SERIES", "", "ZN Baltussen — open chantier, nothing persisted"),
    "D006": ("NO_SERIES", "", "Glassnode"),
    "D007": ("NO_SERIES", "", "HLP vault / Uniswap / GitHub velocity"),
    "D008": ("NO_SERIES", "", "Commodities XS basis+TSMOM — phase A incomplete"),
}


if __name__ == "__main__":
    inv = pd.read_csv(MAIN / "Multi_Asset/research/active/edge_inventory_2026-07/INVENTORY.csv")
    inv["reach_status"] = inv["id"].map(lambda i: MAP.get(i, ("UNMAPPED", "", ""))[0])
    inv["reach_series"] = inv["id"].map(lambda i: MAP.get(i, ("", "", ""))[1])
    inv["reach_note"] = inv["id"].map(lambda i: MAP.get(i, ("", "", ""))[2])
    keep = inv[["id", "name", "t_stat", "kill_class", "reach_status", "reach_series", "reach_note"]]
    keep.to_csv(HERE / "crosswalk_inventory.csv", index=False)
    print(keep["reach_status"].value_counts().to_string())
    print()
    # concentration in the statistically strong tranche
    strong = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008",
              "E012", "E014", "E016", "M001", "M043", "M047", "R015"]
    sub = keep[keep.id.isin(strong)]
    print("t >= 3 tranche (inventory s4.2):")
    print(sub[["id", "reach_status", "reach_series"]].to_string(index=False))
