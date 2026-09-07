"""
Keyword-rule categorization of ForexFactory event names into 5 macro categories
(Confidence, Growth, Inflation, Rates, Employment), matching the taxonomy described
in the Dedale video transcript. Declared BEFORE any score is computed (pre-registration).

Speeches / press conferences / auctions are explicitly excluded: they carry no
Actual/Forecast numeric pair, so no surprise can be computed from them.
"""
import re

EXCLUDE_PATTERNS = [
    r"speaks", r"press conference", r"testimony", r"bond auction", r"holiday",
    r"summit", r"g7|g20", r"election", r"referendum", r"strikes", r"vote\b",
]

CATEGORY_RULES = {
    "Employment": [
        r"unemployment rate", r"unemployment claims", r"employment change",
        r"non-farm", r"nonfarm", r"payroll", r"jobless", r"claimant count",
        r"average hourly earnings", r"average earnings index", r"participation rate",
        r"employment cost index", r"job", r"hiring",
    ],
    "Inflation": [
        r"\bcpi\b", r"\bppi\b", r"pce price index", r"price index", r"\brmpi\b",
        r"inflation", r"import prices", r"export prices", r"\brpi\b",
    ],
    "Growth": [
        r"\bgdp\b", r"retail sales", r"industrial production", r"manufacturing production",
        r"\bpmi\b", r"\bism\b", r"durable goods", r"trade balance", r"current account",
        r"housing starts", r"building permits", r"new home sales", r"existing home sales",
        r"pending home sales", r"chicago pmi", r"empire state", r"philly fed",
        r"ivey pmi", r"manufacturing sales", r"construction pmi", r"factory orders",
        r"business inventories", r"capacity utilization", r"wholesale", r"leading index",
        r"housing price index", r"construction spending", r"vehicle sales", r"gdp\b",
        r"mining production", r"personal spending", r"building approvals", r"\bhpi\b",
        r"home loans", r"net lending", r"public sector net borrowing",
        r"foreign securities purchases", r"personal income",
    ],
    "Confidence": [
        r"consumer confidence", r"consumer sentiment", r"\bifo\b", r"\bzew\b",
        r"business confidence", r"economic sentiment", r"\bkof\b", r"business climate",
        r"nab business confidence", r"anz business confidence", r"westpac consumer",
        r"gfk consumer", r"tankan", r"business nz", r"melbourne institute",
    ],
    "Rates": [
        r"cash rate", r"official bank rate", r"federal funds rate", r"overnight rate",
        r"main refinancing rate", r"monetary policy statement",
        r"monetary policy meeting minutes", r"rate statement", r"mpc official bank rate votes",
        r"deposit facility rate", r"repo rate", r"ocr\b", r"fomc statement",
        r"fomc meeting minutes", r"\bm3 money supply\b",
    ],
}


def categorize(event_name):
    e = event_name.lower()
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, e):
            return None
    for cat, pats in CATEGORY_RULES.items():
        for pat in pats:
            if re.search(pat, e):
                return cat
    return None


if __name__ == "__main__":
    import pandas as pd
    CACHE = "<SCRATCH>"
    df = pd.read_csv(f"{CACHE}/forex_factory_calendar_2007_2025.csv", low_memory=False)
    econ = df[df["Impact"].isin(["High Impact Expected", "Medium Impact Expected"])]
    econ = econ[econ["Currency"].isin(["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"])]
    econ = econ.copy()
    econ["category"] = econ["Event"].apply(categorize)
    total = len(econ)
    categorized = econ["category"].notna().sum()
    print(f"Total High/Medium events (8 currencies): {total}")
    print(f"Categorized: {categorized} ({categorized/total:.1%})")
    print(econ["category"].value_counts(dropna=False))
    print()
    print("--- top 30 UNCATEGORIZED event names by frequency (for audit) ---")
    uncat = econ[econ["category"].isna()]
    print(uncat["Event"].value_counts().head(30))
