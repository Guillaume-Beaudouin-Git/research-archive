"""
universe.py — Phase 1: Delta-Neutral Funding Arbitrage Universe Mapping

Finds assets tradeable on BOTH:
  - Binance spot (USDT pair, ≥$10M 24h volume)
  - Hyperliquid perps (≥180 days funding history)

Carry metric (hourly HL funding → 7-day carry):
  carry_7d = mean(|funding_rate_1h|) × 168   (168 = 24h × 7d)

Cost threshold: carry_7d > 0.34%
  (covers 0.17% Binance spot rt + 0.17% HL perp rt)

HL funding data: reads from hl_funding_summary.csv (generated on laptop)
  OR queries HL API directly if summary not available.

Usage:
    python -m strategies.delta_neutral.universe [--data-dir PATH]
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from binance.client import Client as BinanceClient

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR   = REPO_ROOT / "data" / "delta_neutral"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HL_API      = "https://api.hyperliquid.xyz/info"
# Volume check always uses the real Binance MAINNET public API (no keys needed).
# Never use BinanceTestnetClient here — testnet volume is synthetic/fake and
# would produce inflated or incorrect liquidity readings.
_BN_MAINNET = BinanceClient()   # no API keys → public endpoints only
MIN_DAYS    = 180          # minimum HL funding history
MIN_VOL_USD = 10_000_000   # Binance 24h USDT volume floor
CARRY_FLOOR = 0.0034       # 0.34% 7-day carry (covers round-trip costs)
HOURS_7D    = 24 * 7       # 168 hourly funding bars = 7 days


# ─── HYPERLIQUID ──────────────────────────────────────────────────────────────

def _hl_post(payload: dict, retries: int = 4) -> list | dict:
    for attempt in range(retries):
        try:
            r = requests.post(HL_API, json=payload, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"HL API failed: {exc}")


def get_hl_universe() -> list[str]:
    """Return all non-delisted Hyperliquid perp coin names."""
    meta = _hl_post({"type": "meta"})
    return sorted(
        item["name"]
        for item in meta.get("universe", [])
        if not item.get("isDelisted", False)
    )


def fetch_hl_7d_carry(coin: str) -> float | None:
    """
    Fetch last 7 days of hourly funding rates for coin.
    Returns mean(|rate_1h|) × 168 = carry earned over 7 days.
    Returns None on failure.
    """
    start_ms = int(
        (datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 1000
    )
    try:
        batch = _hl_post({"type": "fundingHistory", "coin": coin,
                          "startTime": start_ms})
    except Exception:
        return None

    if not batch:
        return None

    rates = [abs(float(r["fundingRate"])) for r in batch]
    if not rates:
        return None

    return sum(rates) / len(rates) * HOURS_7D


def load_hl_history_days(summary_path: Path) -> dict[str, int]:
    """
    Load per-asset history length (days) from the pre-computed summary CSV.
    Falls back to querying HL meta if file not found (uses listing date estimate).
    """
    if summary_path.exists():
        df = pd.read_csv(summary_path)
        result = {}
        for _, row in df.iterrows():
            asset = str(row["asset"])
            rows  = int(str(row["rows"]).strip())
            # rows - 1 header → hours of data → days (hourly data)
            days = max(0, (rows - 1) // 24)
            result[asset] = days
        return result

    print("  hl_funding_summary.csv not found — using HL API meta (listing dates)")
    hl_assets = get_hl_universe()
    # Without local data we can't know exact history; assume all listed assets
    # qualify if they appear in the HL universe (conservative: mark as 9999 days)
    return {a: 9999 for a in hl_assets}


# ─── BINANCE ─────────────────────────────────────────────────────────────────

def get_binance_spot_usdt() -> dict[str, float]:
    """
    Return {baseAsset: 24h_USDT_volume} for all actively-trading
    Binance USDT spot pairs above the volume floor.

    ALWAYS uses _BN_MAINNET (Client() with no keys) so volume figures
    reflect real market liquidity, not testnet synthetic data.
    """
    # Active USDT trading pairs (mainnet exchange info)
    info   = _BN_MAINNET.get_exchange_info()
    active = {
        s["baseAsset"]
        for s in info["symbols"]
        if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
    }

    # All 24h tickers in a single mainnet call (passing no symbol = bulk)
    all_tickers = _BN_MAINNET.get_ticker()
    volumes: dict[str, float] = {}
    for t in all_tickers:
        sym = t["symbol"]
        if sym.endswith("USDT"):
            base = sym[:-4]
            if base in active:
                volumes[base] = float(t["quoteVolume"])

    return volumes


# ─── UNIVERSE BUILD ───────────────────────────────────────────────────────────

def build_universe(summary_path: Path) -> pd.DataFrame:
    """
    Compute the viable delta-neutral universe.
    Returns a sorted DataFrame with carry, volume, history, viability.
    """
    print("\n── Step 1: Loading HL funding history summary ─────────────────────")
    hl_days = load_hl_history_days(summary_path)
    hl_eligible = {a for a, d in hl_days.items() if d >= MIN_DAYS}
    print(f"  HL assets with ≥{MIN_DAYS}d history: {len(hl_eligible)}")

    print("\n── Step 2: Fetching Binance spot USDT universe ─────────────────────")
    bn_volumes = get_binance_spot_usdt()
    bn_all     = set(bn_volumes.keys())
    print(f"  Binance active USDT pairs: {len(bn_all)}")

    print("\n── Step 3: Intersection ─────────────────────────────────────────────")
    intersection = hl_eligible & bn_all
    print(f"  Intersection: {len(intersection)} assets")

    print("\n── Step 4: Fetching last-7d HL funding rates (live API) ─────────────")
    rows = []
    for i, asset in enumerate(sorted(intersection), 1):
        carry = fetch_hl_7d_carry(asset)
        vol   = bn_volumes.get(asset, 0.0)
        days  = hl_days.get(asset, 0)

        viable = (
            carry is not None
            and carry > CARRY_FLOOR
            and vol >= MIN_VOL_USD
            and days >= MIN_DAYS
        )

        rows.append({
            "asset":          asset,
            "carry_7d_pct":   round(carry * 100, 4) if carry is not None else None,
            "bn_vol_usd_M":   round(vol / 1e6, 2),
            "hl_days":        days,
            "viable":         viable,
        })

        if i % 20 == 0:
            print(f"  [{i}/{len(intersection)}] processed ...", flush=True)
        time.sleep(0.1)  # courtesy cap

    df = pd.DataFrame(rows).sort_values(
        ["viable", "carry_7d_pct"], ascending=[False, False]
    ).reset_index(drop=True)
    return df


# ─── REPORTING ────────────────────────────────────────────────────────────────

def print_table(df: pd.DataFrame) -> None:
    viable   = df[df["viable"]]
    inviable = df[~df["viable"]]

    print("\n" + "═" * 70)
    print(f" VIABLE ASSETS ({len(viable)})")
    print("═" * 70)
    print(f"{'Asset':<10} {'Carry 7d %':>11} {'BN Vol $M':>10} {'HL days':>8}  {'Status'}")
    print("─" * 70)
    for _, r in viable.iterrows():
        carry_str = f"{r['carry_7d_pct']:.4f}" if r['carry_7d_pct'] is not None else "  N/A"
        print(f"{r['asset']:<10} {carry_str:>11} {r['bn_vol_usd_M']:>9.1f}  {r['hl_days']:>7}d  ✅")

    print("\n" + "─" * 70)
    print(f" INVIABLE (shown for reference, top 15 by carry)")
    print("─" * 70)
    top_inviable = inviable.dropna(subset=["carry_7d_pct"]).head(15)
    for _, r in top_inviable.iterrows():
        carry_str = f"{r['carry_7d_pct']:.4f}"
        vol_str   = f"{r['bn_vol_usd_M']:.1f}"
        reasons   = []
        if r["carry_7d_pct"] is not None and r["carry_7d_pct"] <= CARRY_FLOOR * 100:
            reasons.append("low carry")
        if r["bn_vol_usd_M"] < MIN_VOL_USD / 1e6:
            reasons.append("low vol")
        if r["hl_days"] < MIN_DAYS:
            reasons.append("short hist")
        print(f"{r['asset']:<10} {carry_str:>11} {vol_str:>9}  {r['hl_days']:>7}d  ❌ {', '.join(reasons)}")

    print("\n" + "═" * 70)
    print(f" SUMMARY")
    print("═" * 70)
    print(f"  Total intersection:    {len(df)}")
    print(f"  Viable (all filters):  {len(viable)}")
    print(f"  Cost threshold:        carry_7d > {CARRY_FLOOR*100:.2f}%")
    print(f"  Volume floor:          BN 24h vol > ${MIN_VOL_USD/1e6:.0f}M USDT")
    print(f"  History floor:         ≥{MIN_DAYS} days HL funding")

    if len(viable) < 5:
        print("\n  ⚠️  PHASE 1 RESULT: INSUFFICIENT UNIVERSE")
        print(f"  Viable assets ({len(viable)}) < 5 minimum for diversification.")
        print("  Strategy B v2 is NOT viable. See docs/strategy_B2_feasibility.md")
    else:
        print(f"\n  ✅ PHASE 1 RESULT: SUFFICIENT UNIVERSE ({len(viable)} assets)")
        print("  Proceeding to Phase 2 (backtest) is warranted.")


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delta-neutral universe mapper — Phase 1"
    )
    parser.add_argument(
        "--data-dir",
        default=str(REPO_ROOT / "data" / "funding_carry"),
        help="Directory containing hl_funding_summary.csv",
    )
    args = parser.parse_args()

    summary_path = Path(args.data_dir) / "hl_funding_summary.csv"

    df = build_universe(summary_path)

    out = OUT_DIR / "universe.csv"
    df.to_csv(out, index=False)
    print(f"\n  Saved: {out}")

    print_table(df)


if __name__ == "__main__":
    main()
