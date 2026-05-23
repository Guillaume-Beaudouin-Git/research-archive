"""
Pairs universe for cointegration feasibility study.

4 categories, 19 pairs total:
  C1: Same-underlying ETF pairs (highest cointegration, lowest edge expected)
  C2: Sector ETF pairs
  C3: Commodity-linked stock pairs
  C4: Equity peer pairs (industry cointegration)
"""

CATEGORIES: dict[str, list[tuple[str, str, str]]] = {
    "C1": [
        ("GLD",  "IAU",  "Gold ETFs (SPDR vs iShares)"),
        ("SLV",  "SIVR", "Silver ETFs (iShares vs Aberdeen)"),
        ("VOO",  "IVV",  "S&P500 ETFs (Vanguard vs iShares)"),
        ("VOO",  "SPY",  "S&P500 ETFs (Vanguard vs SPDR)"),
        ("IVV",  "SPY",  "S&P500 ETFs (iShares vs SPDR)"),
        ("QQQ",  "QQQM", "Nasdaq ETFs (QQQ vs QQQM)"),
    ],
    "C2": [
        ("XLE",  "XOP",  "Energy: integrated vs E&P"),
        ("XLF",  "KBE",  "Financials: broad vs banks"),
        ("XLK",  "SOXX", "Tech: broad vs semis"),
        ("IWM",  "IWO",  "SmallCap: blend vs growth"),
    ],
    "C3": [
        ("GLD",  "GDX",  "Gold metal vs gold miners"),
        ("USO",  "XLE",  "Oil vs energy stocks"),
        ("USO",  "CVX",  "Oil vs Chevron"),
        ("GLD",  "NEM",  "Gold vs Newmont"),
    ],
    "C4": [
        ("KO",   "PEP",  "Beverages (Coke vs Pepsi)"),
        ("HD",   "LOW",  "Home improvement (HD vs Lowe's)"),
        ("WMT",  "TGT",  "Mass retail (Walmart vs Target)"),
        ("V",    "MA",   "Payments (Visa vs Mastercard)"),
        ("GS",   "MS",   "Investment banks (Goldman vs Morgan)"),
    ],
}

ALL_PAIRS: list[tuple[str, str, str, str]] = [
    (cat, y, x, desc)
    for cat, pairs in CATEGORIES.items()
    for (y, x, desc) in pairs
]

ALL_TICKERS: list[str] = sorted(set(
    t
    for pairs in CATEGORIES.values()
    for (y, x, _) in pairs
    for t in (y, x)
))
