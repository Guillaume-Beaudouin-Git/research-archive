"""
ftmo_swaps.py — Real FTMO swap guardrail (the Dédale swap-sign rule).

Source: the trader's real FTMO platform specs (`ftmo_specs.csv`, swap_long/short in
points/night per symbol). This module is the reusable cost-discipline guardrail
distilled from the Dédale FX algo and confirmed across the research arc.

API
---
    swap_bps(symbol, side)               -> per-night swap in bps of notional, SIGNED
                                            (side=+1 long / -1 short; value<0 = you PAY)
    carry_side(symbol)                   -> +1 if long pays positive swap, -1 if short,
                                            0 if both sides are negative (no carry side)
    swap_allowed(symbol, side, allow_neg=False)
                                         -> Dédale rule: only hold the side whose swap
                                            is positive (never pay financing overnight)

Why it matters (research-confirmed)
-----------------------------------
- Holding the NEGATIVE-swap side overnight is the financing-killer. US100 long swap is
  -3.31 bps/night: it pushes the MA200 overnight-harvester net edge to ~0 and p_funded
  to ~31%. The overnight equity premium is LONG but the positive-swap side of an index
  is SHORT -> the two cannot be collected together -> harvester structurally dead.
- For FX multi-day holds, swap_allowed() shaves the expensive side's financing and keeps
  the cheaper leg. It is COST DISCIPLINE, not an alpha generator: it cannot create EV
  where the underlying edge has decayed (Dédale carry-trend, EURGBP swing-MR).

Use swap_allowed() as a HARD FILTER on any strategy that holds across the broker rollover.
"""
from __future__ import annotations
import csv
from pathlib import Path

_SPECS = Path(__file__).resolve().parents[1] / "ftmo_specs.csv"   # data/ftmo_research/ftmo_specs.csv

# Representative current (2026) price levels for points->bps conversion. Swap in bps of
# notional is ~price-invariant over time because the broker re-quotes points with price.
_PRICES = {
    "USDJPY": 150.0, "USDSEK": 10.5, "USDCNH": 7.2, "USDCHF": 0.88, "USDCAD": 1.37,
    "EURUSD": 1.08, "EURGBP": 0.85, "EURJPY": 162.0, "AUDJPY": 98.0, "GBPJPY": 190.0,
    "US100": 20000.0, "US100.cash": 20000.0,
}
# Instruments NOT in the specs file are "just negative both sides" (trader's note):
# no positive-carry side -> swap_allowed() returns False unless allow_neg=True.
_DEFAULT_NEG = (-0.7, -0.7)   # bps/night (long, short) conservative markup drag for FX


def _load() -> dict:
    out = {}
    if not _SPECS.exists():
        return out
    with open(_SPECS, newline="") as f:
        for r in csv.DictReader(f):
            tic = r["ticker"]
            try:
                digits = int(r["digits"])
                sl = float(r["swap_long"]); ss = float(r["swap_short"])
            except (ValueError, KeyError):
                continue
            px = _PRICES.get(tic) or _PRICES.get(tic.replace(".cash", "")) or None
            if px is None:
                continue
            f_ = 10 ** (-digits) / px * 1e4
            key = tic.replace(".cash", "")
            out[key] = (round(sl * f_, 3), round(ss * f_, 3))   # (long_bps, short_bps)
    return out


SWAP_BPS = _load()   # {symbol: (long_bps_per_night, short_bps_per_night)}


def swap_bps(symbol: str, side: int) -> float:
    """Per-night swap in bps of notional, signed (<0 = you pay). side=+1 long / -1 short."""
    lo, sh = SWAP_BPS.get(symbol, _DEFAULT_NEG)
    return lo if side > 0 else sh


def carry_side(symbol: str) -> int:
    """+1 long / -1 short if that side pays positive swap; 0 if neither (no carry side)."""
    lo, sh = SWAP_BPS.get(symbol, _DEFAULT_NEG)
    if lo > 0:
        return 1
    if sh > 0:
        return -1
    return 0


def swap_allowed(symbol: str, side: int, allow_neg: bool = False) -> bool:
    """Dédale rule: only hold the side whose overnight swap is positive."""
    if allow_neg:
        return True
    return swap_bps(symbol, side) > 0


if __name__ == "__main__":
    print("=== Real FTMO swap guardrail (bps/night, signed) ===")
    print(f"{'symbol':>8} {'long':>7} {'short':>7} {'carry_side':>10}")
    for s in sorted(SWAP_BPS):
        lo, sh = SWAP_BPS[s]
        cs = {1: "long", -1: "short", 0: "none"}[carry_side(s)]
        print(f"{s:>8} {lo:>+7.2f} {sh:>+7.2f} {cs:>10}")
    print("\nExamples:")
    print(f"  hold US100 long overnight? {swap_allowed('US100', +1)}  (swap {swap_bps('US100',+1):+.2f} bps/night)")
    print(f"  hold EURGBP short overnight? {swap_allowed('EURGBP', -1)}  (swap {swap_bps('EURGBP',-1):+.2f} bps/night)")
    print(f"  hold GBPUSD (not in specs) long? {swap_allowed('GBPUSD', +1)}  (default negative both sides)")
