"""
hl_perp_client.py — HyperliquidClient subclass for delta-neutral assets.

HyperliquidClient maps Yahoo Finance tickers ("BTC-USD") to HL coin names.
Delta-neutral assets use raw coin names ("WLD", "STX", "TST", etc.).
This subclass skips the SYMBOL_MAP lookup so raw coin names pass through.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from hyperliquid_client import HyperliquidClient


class HLPerpClient(HyperliquidClient):
    """
    HyperliquidClient variant for delta-neutral spot/perp pairs.
    Asset names ("WLD", "STX", "HMSTR") are passed directly as HL coin names.
    All other behaviour (order placement, fill logging, position query) is unchanged.
    """

    def _coin(self, symbol: str) -> str:
        """Pass coin name through directly — no Yahoo ticker mapping."""
        return symbol
