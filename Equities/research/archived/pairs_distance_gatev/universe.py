"""
SP100 proxy universe (~96 tickers, circa 2015).

Survivorship note: this is a static forward-looking list; stocks that delisted
between 2012 and 2024 are absent. This introduces survivorship bias vs CRSP.
For proof-of-concept this is acceptable; full replication requires CRSP/Compustat.
"""

SP100_2015 = [
    # Technology (13)
    "AAPL", "ACN", "ADBE", "CRM", "CSCO", "GOOGL", "IBM", "INTC", "MSFT", "NVDA",
    "ORCL", "QCOM", "TXN",
    # Healthcare (13)
    "ABBV", "ABT", "AMGN", "BAX", "BMY", "GILD", "JNJ", "LLY", "MDT", "MRK",
    "PFE", "TMO", "UNH",
    # Financials (14)
    "AIG", "ALL", "AXP", "BAC", "BK", "BLK", "C", "COF", "GS", "JPM",
    "MET", "MS", "USB", "WFC",
    # Consumer Discretionary (11)
    "AMZN", "BKNG", "F", "GM", "HD", "LOW", "MCD", "NKE", "SBUX", "TGT", "TJX",
    # Consumer Staples (9)
    "CL", "COST", "KO", "MDLZ", "MO", "PEP", "PG", "PM", "WMT",
    # Energy (6)
    "COP", "CVX", "HAL", "OXY", "SLB", "XOM",
    # Industrials (14)
    "BA", "CAT", "DE", "EMR", "FDX", "GD", "GE", "HON", "LMT", "MMM",
    "NOC", "RTX", "UNP", "UPS",
    # Utilities (5)
    "D", "DUK", "EXC", "NEE", "SO",
    # Communication Services (5)
    "CHTR", "CMCSA", "DIS", "T", "VZ",
    # Other large-caps (6)
    "AMT", "BRK-B", "CVS", "DHR", "MA", "V",
]
