"""
tsmom_live.py

Daily TSMOM live trader for Hyperliquid testnet.
Assets: BTC-USD, ETH-USD, SOL-USD
Rebalance: daily at 00:05 UTC — signal from T-1 close, order at T open.

Timing guarantee (matches backtest):
  signal(T) = sign( sum of log_returns[T-LOOKBACK : T-1] )
  vol_scalar(T) = clip( VOL_TARGET / realized_vol[T-VOL_LOOKBACK : T-1], 0.1, 2.0 )
  Both use only T-1 data — zero look-ahead bias.

Trade logic:
  Only trade when signal DIRECTION changes (flat/long/short).
  This yields ~12–17 trades/year per asset, matching the backtest cost model.

Usage:
    python tsmom_live.py --dry-run
    python tsmom_live.py --live --private-key $HYPERLIQUID_TESTNET_KEY
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

import notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── VALIDATED STRATEGY PARAMETERS (do not change) ───────────────────────────
ASSETS            = ["BTC-USD", "ETH-USD", "SOL-USD"]
CAPITAL_PER_ASSET = 150.0   # max USD notional per asset ($150 × 3 = $450 of $499)
LOOKBACK          = 28      # momentum signal window (days)
VOL_TARGET        = 0.15    # annualized vol target (15%)
VOL_LOOKBACK      = 30      # realized vol estimation window (days)
TRADING_DAYS      = 365     # crypto trades 365 days/year (24/7)
FEE_RATE          = 0.00035 # taker fee (0.035%)
SLIPPAGE          = 0.0005  # estimated one-way slippage (0.05%)
MAX_DATA_LAG_DAYS = 2       # yfinance free tier can lag ~24 h

STOP_PATH = Path("STOP")


# ─── STATE ────────────────────────────────────────────────────────────────────

def _state_path(symbol: str) -> Path:
    """State file path for this asset (separate from the ML trader's state files)."""
    return Path(f"tsmom_state_{symbol.replace('-', '_')}.json")


def load_state(symbol: str) -> dict:
    p = _state_path(symbol)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {"position": "flat", "entry_price": 0.0, "entry_time": None}


def save_state(symbol: str, state: dict) -> None:
    with open(_state_path(symbol), "w") as f:
        json.dump(state, f, indent=2)


# ─── KILL SWITCH ─────────────────────────────────────────────────────────────

def check_kill_switch() -> None:
    """Halt immediately if STOP file exists. Exit 0 (intentional halt)."""
    if not STOP_PATH.exists():
        return
    stat       = STOP_PATH.stat()
    mtime_utc  = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    reason_raw = STOP_PATH.read_text().strip()
    reason_str = f" — reason: {reason_raw}" if reason_raw else ""
    msg = (f"HALTED by kill switch "
           f"(created {mtime_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}){reason_str}")
    logger.warning(msg)
    notifier.send(f"[KILL SWITCH] {msg}")
    sys.exit(0)


# ─── DATA ─────────────────────────────────────────────────────────────────────

def fetch_ohlcv(symbol: str) -> pd.DataFrame:
    """
    Fetch 6 months of daily OHLCV. Drop today's partial bar (24/7 crypto).
    """
    df = yf.download(symbol, period="6mo", interval="1d",
                     auto_adjust=True, progress=False)
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    today_utc = datetime.now(timezone.utc).date()
    df = df[df.index.date < today_utc]
    logger.info(f"[{symbol}] {len(df)} bars | latest: {df.index[-1].date()} "
                f"close={df['Close'].iloc[-1]:.2f}")
    return df


def check_data_freshness(df: pd.DataFrame, symbol: str) -> None:
    """
    Verify latest bar is T-1 (or T-2 at most, for yfinance lag).
    Exits with sys.exit(1) if data is too stale or suspiciously future-dated.
    """
    today_utc  = datetime.now(timezone.utc).date()
    latest_ts  = df.index[-1]
    if hasattr(latest_ts, "tzinfo") and latest_ts.tzinfo is not None:
        latest_date = latest_ts.astimezone(timezone.utc).date()
    else:
        latest_date = latest_ts.date()

    lag = (today_utc - latest_date).days

    if lag < 1:
        msg = (f"SUSPICIOUS DATA | {symbol}: latest bar is today {latest_date}. "
               f"Partial bar may not have been dropped. NOT TRADING.")
        logger.error(msg)
        notifier.send(msg, level="warning")
        sys.exit(1)

    if lag <= MAX_DATA_LAG_DAYS:
        logger.info(f"Data freshness OK | {symbol}: latest={latest_date} "
                    f"({lag}d behind today {today_utc})")
        return

    msg = (f"STALE DATA | {symbol}: latest bar {latest_date} is {lag}d old "
           f"(max allowed {MAX_DATA_LAG_DAYS}). NOT TRADING.")
    logger.error(msg)
    notifier.send(msg, level="warning")
    sys.exit(1)


# ─── SIGNAL ───────────────────────────────────────────────────────────────────

def compute_live_signal(close: pd.Series) -> tuple[int, float]:
    """
    Compute TSMOM signal and vol_scalar from a close price series.

    signal    = sign( sum of log_returns over last LOOKBACK bars )
    vol_scalar = clip( VOL_TARGET / realized_vol, 0.1, 2.0 )

    Both use only data through the last closed bar (T-1). No lookahead.

    Returns:
        signal:     +1 (long), -1 (short), 0 (flat / indeterminate)
        vol_scalar: position size multiplier ∈ [0.1, 2.0]
    """
    log_ret = np.log(close / close.shift(1)).dropna()

    min_bars = max(LOOKBACK, VOL_LOOKBACK)
    if len(log_ret) < min_bars:
        raise ValueError(
            f"Not enough data: {len(log_ret)} bars, need {min_bars}"
        )

    cum_ret      = log_ret.iloc[-LOOKBACK:].sum()
    signal       = int(np.sign(cum_ret))

    realized_vol = log_ret.iloc[-VOL_LOOKBACK:].std() * np.sqrt(TRADING_DAYS)
    if realized_vol <= 0:
        raise ValueError(f"Realized vol is zero or negative: {realized_vol}")

    vol_scalar = float(np.clip(VOL_TARGET / realized_vol, 0.1, 2.0))
    return signal, vol_scalar


# ─── RECONCILIATION ───────────────────────────────────────────────────────────

def reconcile_position(symbol: str, state: dict, client) -> dict:
    """
    Query live exchange position and sync with local state.
    Exchange is authoritative — overwrites state on mismatch.
    Non-fatal: logs + alerts on query failure but continues with stored state.
    """
    try:
        exchange_pos = client.get_position(symbol)
    except Exception as exc:
        logger.error(f"[{symbol}] Reconciliation query failed: {exc}. "
                     f"Continuing with stored state.")
        notifier.send(f"[RECONCILE ERROR] {symbol}: {exc}", level="warning")
        return state

    exchange_side = exchange_pos["side"]   # "long" | "short" | "flat"
    stored_side   = state["position"]

    if exchange_side == stored_side:
        logger.info(f"[{symbol}] Reconciliation OK: "
                    f"exchange={exchange_side} == state={stored_side}")
        return state

    msg = (f"POSITION MISMATCH | {symbol}: "
           f"exchange={exchange_side} "
           f"(size={exchange_pos['size']:.4f}, "
           f"entry={exchange_pos['entry_price']:.4f}) "
           f"vs state={stored_side}. Trusting exchange.")
    logger.error(msg)
    notifier.send(f"[MISMATCH] {msg}", level="warning")

    corrected = {
        "position":    exchange_side,
        "entry_price": exchange_pos["entry_price"],
        "entry_time":  datetime.now(timezone.utc).isoformat() + " (reconciled)",
    }
    save_state(symbol, corrected)
    return corrected


# ─── TRADE LOGIC ──────────────────────────────────────────────────────────────

def _direction_str(sig: int) -> str:
    return {1: "long", -1: "short", 0: "flat"}[sig]


def decide_action(current_position: str, target_signal: int) -> str:
    """
    Determine what order to place based on current position and TSMOM signal.

    Returns one of:
      HOLD         — signal direction unchanged, no trade needed
      OPEN_LONG    — from flat, signal = +1
      OPEN_SHORT   — from flat, signal = -1
      FLIP_TO_LONG — currently short, signal flipped to +1 (close + open)
      FLIP_TO_SHORT— currently long, signal flipped to -1 (close + open)
      CLOSE        — signal = 0, close any open position
    """
    target_dir = _direction_str(target_signal)

    if current_position == target_dir:
        return "HOLD"

    if target_signal == 0:
        return "CLOSE" if current_position != "flat" else "HOLD"

    if current_position == "flat":
        return "OPEN_LONG" if target_signal == 1 else "OPEN_SHORT"

    return "FLIP_TO_LONG" if target_signal == 1 else "FLIP_TO_SHORT"


# ─── LOGGING ──────────────────────────────────────────────────────────────────

def log_trade_csv(symbol: str, action: str, price: float,
                  signal: int, vol_scalar: float,
                  deploy_usd: float, fee_est: float) -> None:
    """Append one row to logs/tsmom_trades.csv."""
    Path("logs").mkdir(exist_ok=True)
    csv_path = Path("logs/tsmom_trades.csv")
    header_needed = not csv_path.exists()
    with open(csv_path, "a") as f:
        if header_needed:
            f.write("timestamp,symbol,action,price,signal,"
                    "vol_scalar,deploy_usd,fee_est\n")
        f.write(
            f"{datetime.now(timezone.utc).isoformat()},{symbol},{action},"
            f"{price:.4f},{signal},{vol_scalar:.4f},"
            f"{deploy_usd:.2f},{fee_est:.4f}\n"
        )


# ─── SINGLE ASSET RUN ─────────────────────────────────────────────────────────

def run_asset(symbol: str, dry_run: bool, client) -> dict:
    """
    Execute TSMOM logic for one asset.
    Returns a summary dict for the Telegram alert.
    """
    df                 = fetch_ohlcv(symbol)
    check_data_freshness(df, symbol)
    signal, vol_scalar = compute_live_signal(df["Close"])
    current_price      = float(df["Close"].iloc[-1])
    deploy_usd         = round(CAPITAL_PER_ASSET * vol_scalar, 2)
    state              = load_state(symbol)

    logger.info(f"[{symbol}] signal={signal:+d} vol_scalar={vol_scalar:.3f} "
                f"deploy_usd=${deploy_usd:.2f} state={state['position']}")

    if client is not None:
        state = reconcile_position(symbol, state, client)

    action  = decide_action(state["position"], signal)
    fee_est = 0.0

    logger.info(f"[{symbol}] action={action}")

    if dry_run:
        logger.info(f"[{symbol}] DRY RUN — no order placed")

    elif action != "HOLD":
        fee_est = deploy_usd * (FEE_RATE + SLIPPAGE)

        if action in ("FLIP_TO_LONG", "FLIP_TO_SHORT"):
            # Close the existing position first
            client.close_position(symbol, side=state["position"])
            logger.info(f"[{symbol}] Closed {state['position']}")
            fee_est *= 2  # two legs: close + open

        if action in ("OPEN_LONG", "FLIP_TO_LONG"):
            client.open_long(symbol, deploy_usd)
            state = {
                "position":   "long",
                "entry_price": current_price,
                "entry_time":  datetime.now(timezone.utc).isoformat(),
            }

        elif action in ("OPEN_SHORT", "FLIP_TO_SHORT"):
            client.open_short(symbol, deploy_usd)
            state = {
                "position":   "short",
                "entry_price": current_price,
                "entry_time":  datetime.now(timezone.utc).isoformat(),
            }

        elif action == "CLOSE":
            client.close_position(symbol, side=state["position"])
            state = {"position": "flat", "entry_price": 0.0, "entry_time": None}

        save_state(symbol, state)

    log_trade_csv(symbol, action, current_price, signal, vol_scalar,
                  deploy_usd, fee_est)

    # Log funding (live only)
    if not dry_run and client is not None:
        try:
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            client.get_funding_paid(symbol, since=since)
        except Exception as fe:
            logger.warning(f"[{symbol}] Funding log failed (non-fatal): {fe}")

    return {
        "symbol":     symbol,
        "signal":     signal,
        "vol_scalar": vol_scalar,
        "deploy_usd": deploy_usd,
        "price":      current_price,
        "position":   state["position"],
        "action":     action,
        "fee_est":    fee_est,
    }


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run(dry_run: bool = True, private_key: str | None = None) -> None:
    check_kill_switch()

    mode = "DRY-RUN" if dry_run else "LIVE (TESTNET)"
    logger.info(f"=== TSMOM LIVE | {mode} | {ASSETS} ===")

    client = None
    if not dry_run:
        if not private_key:
            logger.error("--private-key required for --live")
            sys.exit(1)
        from hyperliquid_client import HyperliquidClient
        client = HyperliquidClient(private_key=private_key, testnet=True)

    results: list[dict] = []
    errors:  list[str]  = []

    for symbol in ASSETS:
        try:
            results.append(run_asset(symbol, dry_run, client))
        except SystemExit:
            raise
        except Exception as exc:
            logger.error(f"[{symbol}] Unhandled exception: {exc}", exc_info=True)
            errors.append(f"{symbol}: {type(exc).__name__}: {exc}")
            notifier.send(f"[TSMOM ERROR] {symbol}: {exc}", level="error")

    # ── Telegram summary alert ────────────────────────────────────────────
    sig_name = {1: "LONG", -1: "SHORT", 0: "FLAT"}
    lines = [
        f"TSMOM | {mode} | "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    ]
    for r in results:
        fee_str = f"fee≈${r['fee_est']:.2f}" if r["fee_est"] > 0 else "no fee"
        lines.append(
            f"  {r['symbol']}: {sig_name[r['signal']]} | "
            f"pos={r['position']} | action={r['action']} | "
            f"size=${r['deploy_usd']:.0f} | {fee_str}"
        )
    if errors:
        lines.append(f"  ERRORS: {'; '.join(errors)}")

    notifier.send("\n".join(lines), level="error" if errors else "info")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TSMOM daily live trader — Hyperliquid testnet"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", dest="dry_run", action="store_true",
                       default=True, help="Simulate only, no orders (default)")
    group.add_argument("--live", dest="dry_run", action="store_false",
                       help="Place real orders on testnet")
    parser.add_argument("--private-key", default=None,
                        help="Hex private key for Hyperliquid testnet wallet")
    args = parser.parse_args()

    run(dry_run=args.dry_run, private_key=args.private_key)
