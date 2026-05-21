"""
data/ — local data cache layer

Exposes a thin cache API so research scripts avoid re-parsing large CSVs
or re-fetching yfinance data on every run.

Usage:
    from data.cache import load_nq_1min, get_cached_or_fetch
"""
