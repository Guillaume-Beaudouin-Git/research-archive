"""
live_trader.py

Daily cron entry point. Loads model, fetches data, computes signal,
reconciles with exchange, executes trade.

Usage (dry-run, safe default):
    python live_trader.py --symbol BTC-USD --capital 1000

Live (testnet):
    python live_trader.py --symbol BTC-USD --capital 1000 --live \
        --private-key $HYPERLIQUID_TESTNET_KEY
"""
import argparse
import json
import logging
import os
import pickle
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

import notifier

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SELL, HOLD, BUY = 0, 1, 2
SIGNAL_NAMES = {SELL: "SELL", HOLD: "HOLD", BUY: "BUY"}


def load_model(symbol: str, model_dir: str = "model_store"):
    import torch
    from config import Config
    from model import TradingMLP

    symbol_clean = symbol.replace("-", "_")
    base = Path(model_dir)
    model_path = base / f"{symbol_clean}_model.pt"
    scaler_path = base / f"{symbol_clean}_scaler.pkl"
    meta_path = base / f"{symbol_clean}_meta.json"

    if not model_path.exists():
        raise FileNotFoundError(
            f"No model at {model_path}. Run: python train_and_save.py --symbol {symbol}"
        )

    with open(meta_path) as f:
        meta = json.load(f)
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    cfg = Config()
    model = TradingMLP(
        input_dim=meta["input_dim"],
        hidden_dims=meta["hidden_dims"],
        dropout=meta["dropout"],
    )
    model.load_state_dict(torch.load(model_path, map_location=cfg.device))
    model.to(cfg.device)
    model.eval()

    logger.info(f"Model loaded (trained until {meta['trained_until']})")
    return model, scaler, meta, cfg


def get_latest_bars(symbol: str):
    df = yf.download(symbol, period="6mo", interval="1d",
                     auto_adjust=True, progress=False)
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    # Drop today's partial bar — crypto trades 24/7, so yfinance returns
    # an incomplete bar for the current UTC date starting at 00:00.
    from datetime import datetime, timezone
    today_utc = datetime.now(timezone.utc).date()
    df = df[df.index.date < today_utc]
    logger.info(f"Fetched {len(df)} bars | latest: {df.index[-1].date()} "
                f"close={df['Close'].iloc[-1]:.2f}")
    return df


def get_signal(model, scaler, df, cfg) -> tuple[int, float]:
    import torch
    from features import extract_features

    feat = extract_features(df)
    last = feat.iloc[[-1]].dropna()
    if len(last) == 0:
        raise ValueError("Latest bar has NaN features — need more history")

    X = scaler.transform(last.values.astype("float32"))
    X_t = torch.tensor(X, device=cfg.device)

    # MC Dropout via model.predict_proba():
    # BatchNorm stays in eval mode (frozen running stats) so batch_size=1
    # is safe; only Dropout layers are set to train for stochastic sampling.
    probs = model.predict_proba(X_t, n_samples=cfg.mc_samples)

    signal = int(probs.argmax().item())
    confidence = float(probs[0, signal].item())
    return signal, confidence


def load_state(symbol: str) -> dict:
    path = Path(f"state_{symbol.replace('-', '_')}.json")
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"position": "flat", "entry_price": 0.0, "entry_time": None}


def save_state(symbol: str, state: dict) -> None:
    path = Path(f"state_{symbol.replace('-', '_')}.json")
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def log_trade(symbol: str, action: str, price: float, signal: int,
              confidence: float, capital: float) -> None:
    Path("logs").mkdir(exist_ok=True)
    line = (f"{datetime.now(timezone.utc).isoformat()},{symbol},{action},"
            f"{price:.4f},{SIGNAL_NAMES[signal]},{confidence:.4f},{capital}\n")
    with open("logs/trades.csv", "a") as f:
        f.write(line)


def _send_telegram_alert(message: str, level: str = "warning") -> None:
    """
    Internal helper — thin wrapper around notifier.send().

    All existing callers (check_kill_switch, check_data_freshness,
    reconcile_position) route through here so alert behaviour is
    centralised.  Call notifier.send() directly for new code that knows
    its own severity level.
    """
    notifier.send(message, level=level)


def check_data_freshness(df: pd.DataFrame, symbol: str) -> None:
    """
    Verify the latest bar in df is yesterday's UTC date.

    Daily crypto bars close at 00:00 UTC, so when the cron runs each day
    the freshest available bar should be yesterday.  If the latest bar is
    older than that, yfinance served stale or cached data and the signal
    would be computed on out-of-date prices — do not trade.

    Args:
        df:     OHLCV DataFrame with DatetimeIndex (tz-aware or tz-naive).
        symbol: Ticker string used in log / alert messages.

    Raises:
        SystemExit(1): if the data is stale (too old) or future-dated
                       (clock skew / yfinance bug).
    """
    # NOTE: Assumes 24/7 market (crypto). For equities/FX, replace
    # `yesterday_utc` with last_trading_day_before(today_utc, asset_class).
    today_utc     = datetime.now(timezone.utc).date()
    max_staleness = 2  # yfinance free crypto data can lag up to ~24h

    # yfinance can return a tz-aware or tz-naive DatetimeIndex — normalise both.
    latest_ts = df.index[-1]
    if hasattr(latest_ts, "tzinfo") and latest_ts.tzinfo is not None:
        latest_date = latest_ts.astimezone(timezone.utc).date()
    else:
        latest_date = latest_ts.date()

    lag = (today_utc - latest_date).days

    if lag < 1:
        # latest_date == today — should not happen after partial-bar drop
        msg = (
            f"SUSPICIOUS DATA | {symbol}: latest bar {latest_date} is today "
            f"{today_utc}. Clock skew or partial bar not dropped. NOT TRADING."
        )
        logger.error(msg)
        _send_telegram_alert(msg)
        sys.exit(1)

    if lag <= max_staleness:
        logger.info(
            f"Data freshness OK | {symbol}: latest bar {latest_date} "
            f"({lag} day{'s' if lag != 1 else ''} behind today {today_utc})"
        )
        return

    # Too stale
    msg = (
        f"STALE DATA | {symbol}: latest bar is {latest_date} "
        f"({lag} days behind today {today_utc}, max allowed {max_staleness}). "
        f"yfinance may be serving cached or delayed data. NOT TRADING."
    )
    logger.error(msg)
    _send_telegram_alert(msg)
    sys.exit(1)


def check_kill_switch() -> None:
    """
    Halt the trader cleanly if a STOP file exists in the working directory.

    The STOP file acts as an out-of-band pause mechanism: create it over SSH
    to stop the bot without touching cron, delete it to resume.

    If the file contains text it is treated as a human-readable reason and
    included in the log message and Telegram alert.  mtime is reported so
    the operator knows how long the halt has been in effect.

    Exits with sys.exit(0) — intentional halt, not an error.

    Usage:
        touch STOP                     # halt immediately on next run
        echo "drawdown limit hit" > STOP   # halt with reason
        rm STOP                        # resume
    Or use the convenience scripts: touch_stop.sh / remove_stop.sh
    """
    stop_path = Path("STOP")
    if not stop_path.exists():
        return

    stat        = stop_path.stat()
    mtime_utc   = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    halted_since = mtime_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    reason_raw = stop_path.read_text().strip()
    reason_str = f" — reason: {reason_raw}" if reason_raw else ""

    msg = f"HALTED by kill switch (file created {halted_since}){reason_str}"
    logger.warning(msg)
    _send_telegram_alert(f"[KILL SWITCH] {msg}")
    sys.exit(0)


def check_model_freshness(meta: dict, max_age_days: int) -> None:
    """
    Verify the saved model is not stale relative to today's UTC date.

    Age is measured from meta["trained_until"] (the last date of training
    data, format "YYYY-MM-DD") to today's UTC date.  Two thresholds apply:

    - age > max_age_days  → model is too old to trust; log ERROR, send
                            Telegram alert (level="error"), sys.exit(1).
    - 30 <= age <= max_age_days → model is getting stale; log WARNING,
                            send Telegram alert (level="warning"), continue.
    - age < 30            → model is fresh; log INFO, continue.

    Args:
        meta:         Dict loaded from {symbol}_meta.json, must contain
                      "trained_until" in "YYYY-MM-DD" format.
        max_age_days: Hard expiry threshold in days (default 45 in run()).
    """
    trained_until = datetime.strptime(meta["trained_until"], "%Y-%m-%d").date()
    today_utc     = datetime.now(timezone.utc).date()
    age_days      = (today_utc - trained_until).days

    symbol = meta.get("symbol", "unknown")

    if age_days > max_age_days:
        msg = (
            f"MODEL EXPIRED | {symbol}: trained_until={trained_until} "
            f"is {age_days} days old (limit={max_age_days}). "
            f"Re-run train_and_save.py to refresh. NOT TRADING."
        )
        logger.error(msg)
        notifier.send(msg, level="error")
        sys.exit(1)

    if age_days >= 30:
        msg = (
            f"MODEL STALE WARNING | {symbol}: trained_until={trained_until} "
            f"is {age_days} days old — consider retraining "
            f"(hard limit={max_age_days} days)."
        )
        logger.warning(msg)
        notifier.send(msg, level="warning")
        return

    logger.info(
        f"Model freshness OK | {symbol}: trained_until={trained_until} "
        f"({age_days} day{'s' if age_days != 1 else ''} old)"
    )


def reconcile_position(
    symbol: str,
    state: dict,
    private_key: str,
    testnet: bool = True,
) -> dict:
    """
    Query the live exchange position and reconcile with local state.json.

    The exchange is the authoritative source of truth.  If the stored
    position disagrees with what the exchange reports, the discrepancy is
    logged, a Telegram alert is sent, state.json is overwritten with the
    exchange value, and the corrected state is returned so the rest of
    run() makes its action decision on accurate data.

    Skips silently (returning state unchanged) if:
      - The Hyperliquid SDK is not installed (ImportError inside __init__).
      - The exchange query raises any exception (logged as ERROR; we do not
        halt trading on a reconciliation failure — the risk of double-open
        is smaller than the risk of refusing to close a losing position).

    Args:
        symbol:      Yahoo Finance ticker, e.g. "BTC-USD".
        state:       Dict loaded from state.json with keys 'position',
                     'entry_price', 'entry_time'.
        private_key: Hex private key for the Hyperliquid wallet.
        testnet:     True = testnet (default), False = mainnet.

    Returns:
        Reconciled state dict (may be the original or the exchange value).
    """
    # TODO (Phase 2 / mainnet): on query failure we currently proceed with
    # stored state, accepting a small double-open risk if a previous run
    # crashed mid-trade.  For mainnet, revisit: allow CLOSE actions but
    # block OPEN actions when reconciliation fails, so the worst case is
    # a missed entry rather than an unintended second position.
    try:
        from hyperliquid_client import HyperliquidClient
        client = HyperliquidClient(private_key=private_key, testnet=testnet)
        exchange_pos = client.get_position(symbol)
    except ImportError:
        logger.warning(
            "Hyperliquid SDK not installed — position reconciliation skipped. "
            "Install hyperliquid-python-sdk and eth_account for live use."
        )
        return state
    except Exception as exc:
        logger.error(
            f"Reconciliation query failed for {symbol}: {exc}. "
            f"Proceeding with stored state (position={state['position']})."
        )
        _send_telegram_alert(
            f"[RECONCILE ERROR] {symbol}: could not query exchange position — {exc}"
        )
        return state

    exchange_side = exchange_pos["side"]   # "long" | "short" | "flat"
    stored_side   = state["position"]      # "long" | "short" | "flat"

    if exchange_side == stored_side:
        logger.info(
            f"Reconciliation OK | {symbol}: exchange={exchange_side} "
            f"matches state.json={stored_side}"
        )
        return state

    # ── Discrepancy detected ───────────────────────────────────────────────
    msg = (
        f"POSITION MISMATCH | {symbol}: "
        f"exchange={exchange_side} "
        f"(size={exchange_pos['size']}, entry={exchange_pos['entry_price']:.4f}) "
        f"vs state.json={stored_side} "
        f"(entry={state['entry_price']:.4f}). "
        f"Trusting exchange and overwriting state.json."
    )
    logger.error(msg)
    _send_telegram_alert(f"[POSITION MISMATCH] {msg}")

    # Build corrected state from exchange data.
    # entry_time is not available from the exchange API; record the
    # reconciliation timestamp so the audit trail is not blank.
    corrected_state: dict = {
        "position":    exchange_side,
        "entry_price": exchange_pos["entry_price"],
        "entry_time":  datetime.now(timezone.utc).isoformat() + " (reconciled)",
    }
    save_state(symbol, corrected_state)
    logger.info(f"State overwritten from exchange: {corrected_state}")
    return corrected_state


def run(symbol: str, capital: float, dry_run: bool = True,
        private_key: str | None = None,
        max_model_age_days: int = 45) -> None:
    check_kill_switch()   # must be first — halts before any I/O if STOP exists

    logger.info(f"=== LIVE TRADER | {symbol} | capital=${capital} | "
                f"dry_run={dry_run} ===")

    # ── Main logic wrapped in try/except so every unhandled exception ──────
    # fires a Telegram alert before propagating.
    signal: int = HOLD
    confidence: float = 0.0
    state: dict = {"position": "flat", "entry_price": 0.0, "entry_time": None}
    try:
        model, scaler, meta, cfg = load_model(symbol)
        check_model_freshness(meta, max_model_age_days)
        df = get_latest_bars(symbol)
        check_data_freshness(df, symbol)
        signal, confidence = get_signal(model, scaler, df, cfg)
        current_price = float(df["Close"].iloc[-1])

        logger.info(f"Signal: {SIGNAL_NAMES[signal]} (conf={confidence:.2%})")

        state = load_state(symbol)
        logger.info(f"Stored position: {state['position']} "
                    f"(entry {state['entry_price']:.2f})")

        # ── Reconcile against exchange before deciding action ──────────────
        # Skipped in dry-run without a key: no wallet to query, no risk of
        # double-open either (dry-run never places orders).
        if private_key:
            state = reconcile_position(symbol, state, private_key=private_key)
        else:
            logger.warning(
                "Position reconciliation skipped — no --private-key provided. "
                "Pass --private-key even in dry-run to enable reconciliation."
            )

        action = "HOLD"
        if state["position"] == "flat":
            if signal == BUY:
                action = "OPEN_LONG"
            elif signal == SELL and getattr(cfg, "allow_short", False):
                action = "OPEN_SHORT"
        elif state["position"] == "long":
            if signal == SELL:
                action = "CLOSE_LONG"
            elif state["entry_price"] > 0:
                pnl = (current_price - state["entry_price"]) / state["entry_price"]
                if pnl <= -cfg.stop_loss:
                    logger.warning(f"STOP LOSS: {pnl:.2%}")
                    action = "STOP_LOSS_CLOSE"
        elif state["position"] == "short":
            if signal == BUY:
                action = "CLOSE_SHORT"
            elif state["entry_price"] > 0:
                pnl = (state["entry_price"] - current_price) / state["entry_price"]
                if pnl <= -cfg.stop_loss:
                    logger.warning(f"STOP LOSS: {pnl:.2%}")
                    action = "STOP_LOSS_CLOSE"

        logger.info(f"Action: {action}")

        if dry_run:
            logger.info("DRY RUN — no order placed")
        elif action != "HOLD":
            if not private_key:
                logger.error("--private-key required for --live")
                sys.exit(1)

            from hyperliquid_client import HyperliquidClient
            client = HyperliquidClient(private_key=private_key, testnet=True)
            deploy_usd = capital * cfg.position_size

            if action == "OPEN_LONG":
                client.open_long(symbol, deploy_usd)
                state = {"position": "long", "entry_price": current_price,
                         "entry_time": datetime.now(timezone.utc).isoformat()}
                notifier.send(
                    f"TRADE EXECUTED | {symbol} | OPEN_LONG | "
                    f"size=${deploy_usd:.0f} | price={current_price:.2f} | "
                    f"conf={confidence:.1%}",
                    level="info",
                )
            elif action == "OPEN_SHORT":
                client.open_short(symbol, deploy_usd)
                state = {"position": "short", "entry_price": current_price,
                         "entry_time": datetime.now(timezone.utc).isoformat()}
                notifier.send(
                    f"TRADE EXECUTED | {symbol} | OPEN_SHORT | "
                    f"size=${deploy_usd:.0f} | price={current_price:.2f} | "
                    f"conf={confidence:.1%}",
                    level="info",
                )
            elif action in ("CLOSE_LONG", "CLOSE_SHORT", "STOP_LOSS_CLOSE"):
                client.close_position(symbol, side=state["position"])
                entry = state.get("entry_price", 0.0)
                pnl_pct = (
                    (current_price - entry) / entry * 100
                    if state["position"] == "long" and entry > 0
                    else (entry - current_price) / entry * 100
                    if state["position"] == "short" and entry > 0
                    else 0.0
                )
                state = {"position": "flat", "entry_price": 0.0, "entry_time": None}
                notifier.send(
                    f"TRADE EXECUTED | {symbol} | {action} | "
                    f"price={current_price:.2f} | P&L≈{pnl_pct:+.2f}%",
                    level="info",
                )

        save_state(symbol, state)
        log_trade(symbol, action, current_price, signal, confidence, capital)
        logger.info(f"Done. State: {state}")

        # TODO (architecture): HyperliquidClient is instantiated 2-3x per run
        # (reconcile, trade, funding). Refactor to a single client created at
        # the start of run() and passed to each block.

        # ── Funding rate log (live only — requires a wallet) ──────────────
        if not dry_run and private_key:
            try:
                from hyperliquid_client import HyperliquidClient
                from datetime import timedelta
                _funding_client = HyperliquidClient(private_key=private_key, testnet=True)
                _since = datetime.now(timezone.utc) - timedelta(hours=24)
                _funding_client.get_funding_paid(symbol, since=_since)
            except Exception as _fe:
                logger.warning(f"Funding log failed (non-fatal): {_fe}")

        # ── Daily heartbeat ────────────────────────────────────────────────
        notifier.send(
            f"Heartbeat | {symbol} | position={state['position']} | "
            f"signal={SIGNAL_NAMES[signal]} (conf={confidence:.1%}) | "
            f"action={action} | {'dry_run' if dry_run else 'live'}",
            level="info",
        )

    except SystemExit:
        raise   # propagate intentional exits (kill switch, stale data) unchanged

    except Exception as exc:
        logger.error(f"Unhandled exception in run({symbol}): {exc}", exc_info=True)
        notifier.send(
            f"EXCEPTION | {symbol} | {type(exc).__name__}: {exc}",
            level="error",
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC-USD")
    parser.add_argument("--capital", type=float, default=1000.0)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--private-key", default=None)
    parser.add_argument("--max-model-age-days", type=int, default=45,
                        help="Days since trained_until before refusing to trade (default: 45)")
    args = parser.parse_args()

    run(symbol=args.symbol, capital=args.capital,
        dry_run=not args.live, private_key=args.private_key,
        max_model_age_days=args.max_model_age_days)
