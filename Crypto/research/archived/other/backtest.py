"""
Event-driven backtester — revised.

Key fixes vs original:
    1. FRACTIONAL POSITION SIZING (position_size = 0.30)
       Each trade uses only 30% of capital, not 100%.
       A trade that makes 10% adds only 3% to the portfolio.
       This kills astronomical compounding while preserving signal.

    2. SLIPPAGE (slippage = 0.001)
       0.1% market impact added on top of fees for each entry and exit.
       Realistic for crypto with moderate order sizes.

    3. NO AUTO-FLIP (auto_flip = False)
       OLD: exiting a long on Sell immediately opens a short.
            Portfolio was ALWAYS in position → compounding every move.
       NEW: exiting goes FLAT. Next explicit signal opens a new position.
            Allows genuine flat periods between trades.

    4. MAX HOLD BARS (max_hold_bars = 30)
       Force-exit any position held longer than 30 bars.
       Prevents holding indefinitely through adverse moves.

    5. CORRECT EXECUTION TIMING (deferred by 1 bar)
       Features at bar i include close[i], which is not available at
       open[i].  The signal from bar i therefore executes at open[i+1].
       Previously entering at open[i] created a fatal look-ahead bias:
       100% of BUY bars had Close > Open, inflating win rate to 91% and
       Sharpe to 3.5+.  After the fix, Sharpe reflects true OOS skill.

       Mechanical exits (stop-loss at close[i], max-hold at open[i]) are
       NOT deferred — they are price-triggered, not signal-triggered.

Performance metrics unchanged: Sharpe, Calmar, MDD, Win Rate, Profit Factor.

# TODO (Task 6): add Backtester.apply_hyperliquid_costs(equity_df, trades_df,
#     taker_fee=0.00035, maker_fee=0.0001, funding_df=None) → (equity_df, trades_df)
#
# All market orders on Hyperliquid are taker (0.035%).  Limit orders that rest
# qualify for maker (0.010%).  Current backtest uses cfg.fee=0.002 (0.2%) per
# side which is more conservative, but the fee *structure* differs: Hyperliquid
# charges a flat notional fee, not position-size-scaled.  Funding accrues every
# 8 hours to longs/shorts and must be netted against trade P&L.
#
# When live fills start populating logs/fills.csv and logs/funding.csv (Task 6),
# this method should replay the backtest trade log with exact fill prices,
# Hyperliquid fee tiers, and realized funding so we can compare simulated vs
# live performance on the same basis.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config import Config

SELL, HOLD, BUY = 0, 1, 2


class Backtester:
    def __init__(self, config: Config):
        self.cfg = config

    def run(
        self,
        prices: pd.DataFrame,
        predictions: np.ndarray,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Simulate trading on the test period.

        Args:
            prices:      DataFrame with 'Open' and 'Close' columns.
            predictions: integer array {0: Sell, 1: Hold, 2: Buy}.

        Returns:
            equity_df:  DataFrame with columns ['equity', 'returns'].
            trade_log:  DataFrame of individual completed trades.

        Execution model:
            Signal from predictions[i] is computed from features that
            include close[i].  Since close[i] is unknown at open[i],
            the signal is deferred: it executes at open[i+1].

            Mechanical exits are NOT deferred:
              - Stop-loss: checked at close[i], exits at close[i].
              - Max-hold:  checked at bar start, exits at open[i].
        """
        cfg         = self.cfg
        n           = len(prices)
        capital     = cfg.initial_capital
        fee         = cfg.fee
        slippage    = cfg.slippage
        stop_pct    = cfg.stop_loss
        pos_size    = cfg.position_size   # fraction of capital per trade
        allow_short = cfg.allow_short
        auto_flip   = cfg.auto_flip
        max_hold    = cfg.max_hold_bars

        equity     = np.full(n, np.nan)
        equity[0]  = capital

        position    = 0      # 0: flat | 1: long | -1: short
        entry_price = 0.0
        bars_held   = 0
        trade_log: List[dict] = []
        position_arr = np.zeros(n, dtype=np.int8)   # records position held at end of each bar

        pending_sig: Optional[int] = None   # queued signal to execute at THIS bar's open

        for i in range(n):
            sig     = int(predictions[i])
            open_p  = float(prices["Open"].iloc[i])
            close_p = float(prices["Close"].iloc[i])

            # was_in_position: True if we held a position at bar START (before
            # any execution this bar).  Used to avoid double-counting bars_held
            # when a pending entry fires on this bar.
            was_in_position = position != 0

            # ── Execute signal queued from PREVIOUS bar ────────────────
            # predictions[i-1] was computed from features(close[i-1]).
            # Earliest realistic fill is open[i] — executed here.
            if pending_sig is not None:
                if position == 0:
                    if pending_sig == BUY:
                        position    = 1
                        entry_price = open_p * (1 + fee + slippage)
                        bars_held   = 0
                    elif pending_sig == SELL and allow_short:
                        position    = -1
                        entry_price = open_p * (1 - fee - slippage)
                        bars_held   = 0
                elif position == 1 and pending_sig == SELL:
                    # Exit long
                    capital, log = self._exit(
                        capital, position, entry_price, pos_size,
                        exit_price=open_p, fee=fee, slippage=slippage,
                        reason="signal", step=i,
                    )
                    trade_log.append(log)
                    position  = 0
                    bars_held = 0
                    if auto_flip and allow_short:
                        position    = -1
                        entry_price = open_p * (1 - fee - slippage)
                        bars_held   = 0
                elif position == -1 and pending_sig == BUY:
                    # Cover short
                    capital, log = self._exit(
                        capital, position, entry_price, pos_size,
                        exit_price=open_p, fee=fee, slippage=slippage,
                        reason="signal", step=i,
                    )
                    trade_log.append(log)
                    position  = 0
                    bars_held = 0
                    if auto_flip:
                        position    = 1
                        entry_price = open_p * (1 + fee + slippage)
                        bars_held   = 0
                pending_sig = None

            # ── Max hold bars: force exit ──────────────────────────────
            # Only runs for positions that were open at bar START (not
            # for positions just entered via pending_sig above).
            if was_in_position and position != 0:
                bars_held += 1
                if bars_held >= max_hold:
                    capital, log = self._exit(
                        capital, position, entry_price, pos_size,
                        exit_price=open_p, fee=fee, slippage=slippage,
                        reason="max_hold", step=i,
                    )
                    trade_log.append(log)
                    position  = 0
                    bars_held = 0

            # ── Stop-loss check at close ───────────────────────────────
            if position != 0:
                unreal = position * (close_p - entry_price) / (entry_price + 1e-9)
                if unreal <= -stop_pct:
                    capital, log = self._exit(
                        capital, position, entry_price, pos_size,
                        exit_price=close_p, fee=fee, slippage=slippage,
                        reason="stop_loss", step=i,
                    )
                    trade_log.append(log)
                    position  = 0
                    bars_held = 0

            # ── Queue signal for execution at NEXT bar's open ──────────
            # HOLD signals are not queued — no action needed.
            if sig != HOLD:
                pending_sig = sig

            equity[i] = capital
            position_arr[i] = position   # record end-of-bar position

        # ── Force close at end of period ───────────────────────────────
        # pending_sig (if any) is silently dropped — no next bar to fill.
        if position != 0:
            final = float(prices["Close"].iloc[-1])
            capital, log = self._exit(
                capital, position, entry_price, pos_size,
                exit_price=final, fee=fee, slippage=slippage,
                reason="end_of_period", step=n - 1,
            )
            trade_log.append(log)
            equity[-1] = capital

        equity_df = pd.DataFrame(
            {
                "equity":   equity,
                "returns":  pd.Series(equity).pct_change().fillna(0).values,
                "position": position_arr,   # +1 long / -1 short / 0 flat at bar close
            },
            index=prices.index,
        )
        return equity_df, pd.DataFrame(trade_log)

    @staticmethod
    def _exit(
        capital: float,
        position: int,
        entry_price: float,
        pos_size: float,
        exit_price: float,
        fee: float,
        slippage: float,
        reason: str,
        step: int,
    ) -> Tuple[float, dict]:
        """
        Apply fractional P&L to capital.

        P&L is scaled by pos_size: a 10% trade gain only adds
        pos_size * 10% = 3% to the portfolio (if pos_size = 0.30).
        """
        if position == 1:   # long
            net_exit  = exit_price * (1 - fee - slippage)
            trade_pnl = (net_exit - entry_price) / (entry_price + 1e-9)
        else:               # short
            net_exit  = exit_price * (1 + fee + slippage)
            trade_pnl = (entry_price - net_exit) / (entry_price + 1e-9)

        # FIX: portfolio impact is scaled by position size
        portfolio_pnl = pos_size * trade_pnl
        capital      *= (1 + portfolio_pnl)

        log = {
            "step":          step,
            "position":      "long" if position == 1 else "short",
            "entry":         entry_price,
            "exit":          net_exit,
            "trade_pnl_pct": trade_pnl * 100,        # trade-level P&L
            "port_pnl_pct":  portfolio_pnl * 100,     # portfolio-level P&L
            "reason":        reason,
        }
        return capital, log

    def compute_metrics(
        self,
        equity_df: pd.DataFrame,
        trade_df: Optional[pd.DataFrame] = None,
        freq: str = "1d",
        n_trials: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Compute backtest performance metrics.

        Args:
            equity_df: DataFrame with 'equity' and 'returns' columns.
            trade_df:  Optional trade log DataFrame.
            freq:      Bar frequency — '1d', '4h', or '1h'.
            n_trials:  If provided, also compute and store the Deflated Sharpe
                       Ratio (DSR) by treating this as the number of strategy
                       variants tested.  Prints a warning if DSR < 1.0
                       (i.e., the result does not survive selection-bias correction).
        """
        _ppy = {"1h": 8760, "4h": 2190, "1d": 365}
        ppy  = _ppy.get(freq, 365)

        ret    = equity_df["returns"].values
        equity = equity_df["equity"].values

        rf_per_period = 0.02 / ppy
        excess        = ret - rf_per_period

        sharpe  = (excess.mean() / (excess.std() + 1e-9)) * np.sqrt(ppy)
        sortino = (excess.mean() / (excess[excess < 0].std() + 1e-9)) * np.sqrt(ppy)

        total_ret = equity[-1] / equity[0] - 1
        ann_ret   = (1 + total_ret) ** (ppy / max(len(ret), 1)) - 1

        cummax = np.maximum.accumulate(equity)
        dd     = (equity - cummax) / (cummax + 1e-9)
        max_dd = float(dd.min())
        calmar = ann_ret / (abs(max_dd) + 1e-9)

        metrics = {
            "total_return": total_ret,
            "ann_return":   ann_ret,
            "sharpe":       sharpe,
            "sortino":      sortino,
            "max_drawdown": max_dd,
            "calmar":       calmar,
            "final_capital": float(equity[-1]),
        }

        if trade_df is not None and len(trade_df) > 0:
            # Use trade-level P&L for win rate / profit factor
            pnls    = trade_df["trade_pnl_pct"].values
            winners = pnls[pnls > 0]
            losers  = pnls[pnls < 0]
            metrics["n_trades"]      = len(pnls)
            metrics["win_rate"]      = float((pnls > 0).mean())
            metrics["profit_factor"] = (
                winners.sum() / (-losers.sum() + 1e-9) if len(losers) else float("inf")
            )
            metrics["avg_win_pct"]   = float(winners.mean()) if len(winners) else 0.0
            metrics["avg_loss_pct"]  = float(losers.mean())  if len(losers)  else 0.0

        # ── Market exposure, avg holding, t-statistic ─────────────────────
        n_bars   = len(ret)
        n_years  = n_bars / ppy
        in_pos   = int((equity_df["position"].values != 0).sum()) if "position" in equity_df.columns else None
        metrics["market_exposure_pct"] = (in_pos / n_bars) if in_pos is not None else float("nan")
        metrics["t_statistic"]         = sharpe * np.sqrt(max(n_years, 1e-9))

        if trade_df is not None and len(trade_df) > 0:
            metrics["avg_holding_days"] = metrics["market_exposure_pct"] * n_bars / max(metrics["n_trades"], 1)
        else:
            metrics["avg_holding_days"] = float("nan")

        if n_trials is not None:
            from dsr import deflated_sharpe_ratio
            import logging as _logging
            _dsr_log = _logging.getLogger(__name__)

            if trade_df is not None and len(trade_df) > 0:
                # Canonical DSR input: trade-level P&L with correct annualisation.
                # Using all-days equity returns inflates n_obs with structural zeros,
                # corrupting the higher-moment correction (skew/kurtosis) in PSR.
                trade_pnl     = trade_df["trade_pnl_pct"].values / 100.0
                trades_per_yr = max(len(trade_pnl) / max(n_years, 1e-9), 1.0)
                dsr_result    = deflated_sharpe_ratio(
                    trade_pnl, n_trials=n_trials,
                    periods_per_year=int(round(trades_per_yr)),
                )
                metrics["dsr_input"] = "trade_pnl"
            else:
                # Fall back to equity returns when no trade log is available
                dsr_result = deflated_sharpe_ratio(
                    ret, n_trials=n_trials, periods_per_year=ppy
                )
                metrics["dsr_input"] = "equity_returns"

            metrics["dsr"]          = dsr_result["dsr"]
            metrics["sr_benchmark"] = dsr_result["sr_benchmark"]
            metrics["dsr_skewness"] = dsr_result["skewness"]
            metrics["dsr_kurtosis"] = dsr_result["excess_kurtosis"]
            if dsr_result["dsr"] < 0.95:
                _dsr_log.warning(
                    f"DSR={dsr_result['dsr']:.4f} < 0.95 — Sharpe={sharpe:.3f} does NOT "
                    f"survive selection-bias correction for {n_trials} trials "
                    f"(benchmark SR={dsr_result['sr_benchmark']:.3f}, "
                    f"input='{metrics['dsr_input']}')"
                )

        return metrics

    @staticmethod
    def buy_and_hold(prices: pd.DataFrame, initial_capital: float) -> pd.Series:
        return initial_capital * prices["Close"] / prices["Close"].iloc[0]


if __name__ == "__main__":
    """
    CLI: run a quick single-symbol backtest and print Sharpe + DSR.

    Usage:
        python backtest.py --symbol BTC-USD --n-trials 50
    """
    import argparse
    import logging
    import yfinance as yf
    from config import Config
    from features import extract_features
    from labeler import compute_labels
    from trainer import SingleSplitTrainer

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    _log = logging.getLogger("backtest_cli")

    parser = argparse.ArgumentParser(
        description="Run backtest and optionally compute Deflated Sharpe Ratio."
    )
    parser.add_argument("--symbol", default="BTC-USD",
                        help="Yahoo Finance ticker (default: BTC-USD)")
    parser.add_argument("--n-trials", type=int, default=None,
                        help="Number of strategy variants tested. If supplied, "
                             "DSR is computed and a warning is printed if DSR < 0.95.")
    args = parser.parse_args()

    cfg = Config()

    _log.info(f"Downloading {args.symbol}...")
    _df = yf.download(args.symbol, period=cfg.period, interval=cfg.interval,
                      auto_adjust=True, progress=False)
    if hasattr(_df.columns, "get_level_values"):
        _df.columns = _df.columns.get_level_values(0)
    _df = _df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    from features import extract_features
    from labeler import compute_labels, label_distribution

    _feat   = extract_features(_df)
    _labels = compute_labels(_df, cfg)
    _valid  = _feat.dropna().index.intersection(_labels.index)
    _X      = _feat.loc[_valid].values.astype("float32")
    _y      = _labels.loc[_valid].values.astype("int64")
    _prices = _df.loc[_valid, ["Open", "Close"]]

    _trainer = SingleSplitTrainer(cfg)
    _trainer.fit(_X, _y)
    _X_test, _y_test = _trainer.get_test_split(_X, _y)
    _prices_test     = _prices.iloc[-len(_X_test):]
    _preds           = _trainer.predict(_X_test)

    _bt = Backtester(cfg)
    _equity, _trades = _bt.run(_prices_test, _preds)
    _metrics = _bt.compute_metrics(_equity, _trades, freq=cfg.interval,
                                   n_trials=args.n_trials)

    sep = "─" * 45
    print(f"\n{sep}")
    print(f"  Backtest — {args.symbol}")
    print(sep)
    print(f"  Sharpe Ratio     : {_metrics['sharpe']:>8.3f}")
    print(f"  Sortino Ratio    : {_metrics['sortino']:>8.3f}")
    print(f"  Total Return     : {_metrics['total_return']:>+8.2%}")
    print(f"  Ann. Return      : {_metrics['ann_return']:>+8.2%}")
    print(f"  Max Drawdown     : {_metrics['max_drawdown']:>8.2%}")
    print(f"  Calmar Ratio     : {_metrics['calmar']:>8.3f}")
    if "n_trades" in _metrics:
        print(f"  # Trades         : {_metrics['n_trades']}")
        print(f"  Win Rate         : {_metrics['win_rate']:>8.2%}")
        print(f"  Avg Hold (days)  : {_metrics.get('avg_holding_days', float('nan')):>8.1f}")
    print(f"  Mkt Exposure     : {_metrics.get('market_exposure_pct', float('nan')):>8.1%}")
    print(f"  t-statistic      : {_metrics.get('t_statistic', float('nan')):>8.3f}")

    if args.n_trials is not None and "dsr" in _metrics:
        print(f"\n  --- Deflated Sharpe Ratio (n_trials={args.n_trials}, "
              f"input={_metrics.get('dsr_input','?')}) ---")
        print(f"  Observed Sharpe  : {_metrics['sharpe']:>8.3f}")
        print(f"  E[max SR] bench  : {_metrics['sr_benchmark']:>8.3f}")
        print(f"  DSR (PSR)        : {_metrics['dsr']:>8.4f}")
        print(f"  Skewness         : {_metrics.get('dsr_skewness', float('nan')):>8.3f}")
        print(f"  Excess Kurtosis  : {_metrics.get('dsr_kurtosis', float('nan')):>8.3f}")
        if _metrics["dsr"] < 0.95:
            print(f"\n  WARNING: DSR={_metrics['dsr']:.4f} < 0.95")
            print(f"     Sharpe does NOT survive selection-bias correction.")
            print(f"     Benchmark SR*={_metrics['sr_benchmark']:.3f} for {args.n_trials} trials.")
        else:
            print(f"\n  DSR >= 0.95 — result survives selection-bias correction.")
    print(sep)