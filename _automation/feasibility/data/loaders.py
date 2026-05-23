"""
Unified data loaders for the feasibility pipeline.
Wraps cached parquet (crypto 8h OHLCV + funding), Binance klines, and NQ 1-min CSV
via the project's existing data/cache.py infrastructure.
"""
