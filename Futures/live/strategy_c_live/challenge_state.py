"""
challenge_state.py — Propfirm challenge state tracker (Tradeify Select Flex $50K)
==================================================================================
Persists state across daily runs. Survives machine restarts.

Phases:
  eval      — Evaluation, 3 MNQ, target +$3,000
  pre_lock  — Funded, 4 MNQ, until lock trigger
  post_lock — Floor locked at $50,100, 5 MNQ, indefinite

Lock trigger: EOD balance ≥ $52,100 AND first payout requested.
  check_lock_trigger() — call after market close each day
  mark_payout_requested() — call manually when submitting first payout

CLI:
  python3 -m Futures.live.strategy_c_live.challenge_state init
  python3 -m Futures.live.strategy_c_live.challenge_state mark-funded
  python3 -m Futures.live.strategy_c_live.challenge_state mark-payout-requested
  python3 -m Futures.live.strategy_c_live.challenge_state status
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

from Futures.live.strategy_c_live.config import (
    CHALLENGE_STATE_PATH, HALT_SENTINEL_PATH,
    PHASE_CONTRACTS,
    TRADEIFY_LOCK_BALANCE, TRADEIFY_LOCKED_FLOOR,
)


class ChallengeState:
    """
    Tracks Tradeify propfirm metrics across daily runs.
    Persisted as JSON.

    Key metrics (Tradeify):
      trailing_dd_usd = peak_balance - current_balance  (pre-lock)
      post-lock: current_balance must stay >= locked_floor ($50,100)
    """

    def __init__(
        self,
        initial_balance:         float,
        peak_balance:            float,
        challenge_start_date:    str,
        balance_at_day_open:     Optional[float] = None,
        trades_since_start:      int = 0,
        is_funded:               bool = False,
        lock_triggered:          bool = False,
        lock_trigger_date:       Optional[str] = None,
        lock_floor:              float = TRADEIFY_LOCKED_FLOOR,
        first_payout_requested:  bool = False,
        cumulative_payouts:      float = 0.0,
    ) -> None:
        self.initial_balance        = initial_balance
        self.peak_balance           = peak_balance
        self.challenge_start_date   = challenge_start_date
        self.balance_at_day_open    = (balance_at_day_open
                                       if balance_at_day_open is not None
                                       else initial_balance)
        self.trades_since_start     = trades_since_start
        self.is_funded              = is_funded
        self.lock_triggered         = lock_triggered
        self.lock_trigger_date      = lock_trigger_date
        self.lock_floor             = lock_floor
        self.first_payout_requested = first_payout_requested
        self.cumulative_payouts     = cumulative_payouts

    # ── Persistence ──────────────────────────────────────────────────────────

    def _save(self) -> None:
        CHALLENGE_STATE_PATH.write_text(json.dumps({
            "initial_balance":        self.initial_balance,
            "peak_balance":           self.peak_balance,
            "challenge_start_date":   self.challenge_start_date,
            "balance_at_day_open":    self.balance_at_day_open,
            "trades_since_start":     self.trades_since_start,
            "is_funded":              self.is_funded,
            "lock_triggered":         self.lock_triggered,
            "lock_trigger_date":      self.lock_trigger_date,
            "lock_floor":             self.lock_floor,
            "first_payout_requested": self.first_payout_requested,
            "cumulative_payouts":     self.cumulative_payouts,
        }, indent=2))
        log.debug("Challenge state saved to %s", CHALLENGE_STATE_PATH)

    @classmethod
    def initialize(cls, client) -> "ChallengeState":
        """
        Read current account balance and write as initial challenge state.
        Call ONCE at challenge start. Refuses to reinitialize if state already exists.
        """
        if HALT_SENTINEL_PATH.exists():
            raise RuntimeError(
                f"HALTED sentinel active. Delete {HALT_SENTINEL_PATH} before initializing."
            )
        if CHALLENGE_STATE_PATH.exists():
            existing = json.loads(CHALLENGE_STATE_PATH.read_text())
            raise RuntimeError(
                f"Challenge already initialized (start={existing['challenge_start_date']}, "
                f"initial=${existing['initial_balance']:,.2f}). "
                f"Delete {CHALLENGE_STATE_PATH} manually to reinitialize."
            )

        balance = client.get_account_value()
        today   = date.today().isoformat()

        instance = cls(
            initial_balance      = balance,
            peak_balance         = balance,
            challenge_start_date = today,
            balance_at_day_open  = balance,
            trades_since_start   = 0,
        )
        instance._save()
        log.info(
            "Challenge initialized. Initial balance: $%,.2f. Start: %s",
            balance, today,
        )
        return instance

    @classmethod
    def load(cls) -> "ChallengeState":
        """Load state from JSON. Raises FileNotFoundError if not initialized."""
        if not CHALLENGE_STATE_PATH.exists():
            raise FileNotFoundError(
                f"Challenge state not found: {CHALLENGE_STATE_PATH}\n"
                f"Run: python3 -m Futures.live.strategy_c_live.challenge_state init"
            )
        d = json.loads(CHALLENGE_STATE_PATH.read_text())
        return cls(
            initial_balance        = float(d["initial_balance"]),
            peak_balance           = float(d["peak_balance"]),
            challenge_start_date   = d["challenge_start_date"],
            balance_at_day_open    = float(d.get("balance_at_day_open", d["initial_balance"])),
            trades_since_start     = int(d.get("trades_since_start", 0)),
            is_funded              = bool(d.get("is_funded", False)),
            lock_triggered         = bool(d.get("lock_triggered", False)),
            lock_trigger_date      = d.get("lock_trigger_date"),
            lock_floor             = float(d.get("lock_floor", TRADEIFY_LOCKED_FLOOR)),
            first_payout_requested = bool(d.get("first_payout_requested", False)),
            cumulative_payouts     = float(d.get("cumulative_payouts", 0.0)),
        )

    # ── Phase management ─────────────────────────────────────────────────────

    def get_phase(self) -> str:
        """Returns 'eval', 'pre_lock', or 'post_lock'."""
        if self.lock_triggered:
            return 'post_lock'
        if not self.is_funded:
            return 'eval'
        return 'pre_lock'

    def get_n_contracts(self) -> int:
        """Staged sizing based on current phase."""
        return PHASE_CONTRACTS[self.get_phase()]

    def check_lock_trigger(self, current_balance: float) -> bool:
        """
        Check EOD lock condition. Call after market close each day.
        Lock requires BOTH: EOD balance >= $52,100 AND first payout requested.
        Returns True if lock was just activated (caller should send Telegram alert).
        """
        if self.lock_triggered:
            return False
        if current_balance >= TRADEIFY_LOCK_BALANCE and self.first_payout_requested:
            self.lock_triggered     = True
            self.lock_trigger_date  = date.today().isoformat()
            self._save()
            log.info(
                "Lock triggered! Balance=$%.2f >= $%,.0f + payout requested. Floor=$%.0f",
                current_balance, TRADEIFY_LOCK_BALANCE, self.lock_floor,
            )
            return True
        return False

    def mark_payout_requested(self) -> None:
        """
        Call manually via CLI when submitting first payout on Tradeify dashboard.
        Sets first_payout_requested=True and checks lock condition immediately.
        """
        if self.first_payout_requested:
            log.warning("Payout already marked as requested.")
            return
        self.first_payout_requested = True
        self.lock_triggered         = True   # payout request always triggers lock immediately
        self.lock_trigger_date      = date.today().isoformat()
        self._save()
        log.info("Payout requested — lock triggered. Floor locked at $%.0f.", self.lock_floor)

    def mark_funded(self) -> None:
        """CLI: transition from eval → pre_lock after eval validation."""
        if self.is_funded:
            log.warning("Already funded.")
            return
        self.is_funded = True
        self._save()
        log.info("Marked funded. Phase: eval → pre_lock. Sizing: 3 MNQ → 4 MNQ.")

    # ── Balance updates ──────────────────────────────────────────────────────

    def update_balance(self, current_balance: float) -> None:
        """Update peak if current > peak. Persist."""
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        self._save()

    def record_day_open(self, current_balance: float) -> None:
        """Store today's opening balance for intraday self-imposed DD."""
        self.balance_at_day_open = current_balance
        self._save()

    def increment_trade_count(self) -> None:
        self.trades_since_start += 1
        self._save()

    # ── Metrics ──────────────────────────────────────────────────────────────

    def trailing_dd_usd(self, current_balance: float) -> float:
        """Trailing DD in USD from equity peak (pre-lock Tradeify rule)."""
        return max(0.0, self.peak_balance - current_balance)

    def is_below_locked_floor(self, current_balance: float) -> bool:
        """Post-lock: is balance below the permanent floor?"""
        return self.lock_triggered and current_balance < self.lock_floor

    def daily_pnl(self, current_balance: float) -> float:
        """P&L since day open. Positive = gain."""
        return current_balance - self.balance_at_day_open

    def progress_pct(self, current_balance: float) -> float:
        """Progress toward eval target (6%). Positive = gain from initial."""
        return (current_balance - self.initial_balance) / self.initial_balance

    # Legacy metrics (kept for backward compatibility with validate_mt5.py tests)
    def fixed_dd_pct(self, current_balance: float) -> float:
        return (self.initial_balance - current_balance) / self.initial_balance

    def trailing_dd_pct(self, current_balance: float) -> float:
        return (self.peak_balance - current_balance) / self.initial_balance

    def daily_floor(self) -> float:
        """Legacy FTMO floor — returns balance_at_day_open for Tradeify (no DLL)."""
        return self.balance_at_day_open


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _cli_init() -> None:
    from Futures.live.strategy_c_live.config import BROKER

    if BROKER == 'tradovate':
        from Futures.live.strategy_c_live.tradovate_client import TradovateClient
        print("Connecting to Tradovate to read initial balance...")
        client = TradovateClient()
    elif BROKER == 'mt5':
        from Futures.live.strategy_c_live.mt5_client import MT5Client
        print("Connecting to MT5 to read initial balance...")
        client = MT5Client()
    else:
        from Futures.live.strategy_c_live.ibkr_client import IBKRClient
        from Futures.live.strategy_c_live.config import IBKR_HOST, IBKR_PORT, IBKR_CLIENT
        print("Connecting to IBKR to read initial balance...")
        client = IBKRClient(host=IBKR_HOST, port=IBKR_PORT, client_id=IBKR_CLIENT)

    try:
        client.connect()
        state = ChallengeState.initialize(client)
        print(f"\nChallenge initialized.")
        print(f"  Initial balance:      ${state.initial_balance:,.2f}")
        print(f"  Challenge start date: {state.challenge_start_date}")
        print(f"  Phase:                {state.get_phase()} ({state.get_n_contracts()} MNQ)")
        print(f"  State file:           {CHALLENGE_STATE_PATH}")
        print()
        print("NOTE: Verify initial_balance matches your funded account balance.")
        print("      Edit challenge_state.json manually if needed.")
        print("      Run 'mark-funded' once eval passes.")
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR (unexpected): {e}")
        sys.exit(1)
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


def _cli_status() -> None:
    try:
        state = ChallengeState.load()
        phase = state.get_phase()
        n     = state.get_n_contracts()
        print(f"Challenge state: {CHALLENGE_STATE_PATH}")
        print(f"  Start date:           {state.challenge_start_date}")
        print(f"  Phase:                {phase} ({n} MNQ)")
        print(f"  Initial balance:      ${state.initial_balance:,.2f}")
        print(f"  Peak balance:         ${state.peak_balance:,.2f}")
        print(f"  Day open balance:     ${state.balance_at_day_open:,.2f}")
        print(f"  Trades since start:   {state.trades_since_start}")
        print(f"  Is funded:            {state.is_funded}")
        print(f"  Lock triggered:       {state.lock_triggered}"
              + (f" (date: {state.lock_trigger_date})" if state.lock_trigger_date else ""))
        print(f"  Lock floor:           ${state.lock_floor:,.0f}")
        print(f"  First payout req:     {state.first_payout_requested}")
        print(f"  Cumulative payouts:   ${state.cumulative_payouts:,.0f}")
        if HALT_SENTINEL_PATH.exists():
            print(f"\n  HALTED sentinel active: {HALT_SENTINEL_PATH}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "init":
        _cli_init()
    elif cmd == "status":
        _cli_status()
    elif cmd == "mark-funded":
        try:
            state = ChallengeState.load()
            state.mark_funded()
            print(f"Funded. Phase: {state.get_phase()}, sizing: {state.get_n_contracts()} MNQ.")
        except Exception as e:
            print(f"ERROR: {e}"); sys.exit(1)
    elif cmd == "mark-payout-requested":
        try:
            state = ChallengeState.load()
            state.mark_payout_requested()
            print(f"Payout marked. Lock triggered. Floor: ${state.lock_floor:,.0f}.")
        except Exception as e:
            print(f"ERROR: {e}"); sys.exit(1)
    else:
        print("Usage:")
        print("  python3 -m Futures.live.strategy_c_live.challenge_state init")
        print("  python3 -m Futures.live.strategy_c_live.challenge_state mark-funded")
        print("  python3 -m Futures.live.strategy_c_live.challenge_state mark-payout-requested")
        print("  python3 -m Futures.live.strategy_c_live.challenge_state status")
        sys.exit(1)
