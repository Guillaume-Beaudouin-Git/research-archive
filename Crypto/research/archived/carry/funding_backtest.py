"""
funding_backtest.py

Event-driven backtester for the funding rate mean reversion strategy.

TIMING (critical — no look-ahead):
    Signal computed at bar t  →  trade executes at mark_price of bar t+1.
    This applies to BOTH entries and exits.

FUNDING P&L MECHANICS:
    Every hour while in position, we accumulate the actual funding payment:
        SHORT : received_funding = +funding_rate × position_usd
                (positive rate → you receive; negative rate → you pay)
        LONG  : received_funding = -funding_rate × position_usd
                (positive rate → you pay; negative rate → you receive)

COSTS (per side):
    Taker fee : 0.035 %
    Slippage  : 0.020 %
    Total     : 0.055 % per side  →  0.110 % round-trip

Run: python funding_backtest.py
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

# ── Local import ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from funding_strategy import FundingStrategy

# ── Constants ─────────────────────────────────────────────────────────────────
TAKER_FEE       = 0.00035   # 0.035 % per side
SLIPPAGE        = 0.00020   # 0.020 % per side
COST_PER_SIDE   = TAKER_FEE + SLIPPAGE          # 0.055 % per side
INITIAL_CAPITAL = 100_000.0                      # USD

SYMBOLS    = ["BTC", "ETH", "SOL"]
DATA_FILE  = "data/funding_rates.csv"
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 1 — Single-symbol event-driven backtester
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(
    df_sym: pd.DataFrame,
    strategy: FundingStrategy,
    initial_capital: float = INITIAL_CAPITAL,
) -> tuple:
    """
    Bar-by-bar backtester for one symbol.

    Parameters
    ----------
    df_sym : DataFrame for ONE symbol, sorted by timestamp.
             Required columns: timestamp, funding_rate, mark_price, z_score, signal.
             mark_price NaN rows are still included (funding accrues; no price-checks).
    strategy : FundingStrategy instance
    initial_capital : starting USD balance

    Returns
    -------
    equity_df : pd.DataFrame
        Hourly mark-to-market equity curve.
        Columns: timestamp, equity, in_position
    trades_df : pd.DataFrame
        Completed trade log with P&L decomposition.
    """
    p             = strategy.get_params()
    z_exit        = p["z_exit"]
    stop_loss     = p["stop_loss"]
    max_hold      = p["max_hold_hours"]
    pos_frac      = p["position_size"]

    n = len(df_sym)
    if n < 2:
        return pd.DataFrame(), pd.DataFrame()

    # Convert to numpy for speed
    prices     = df_sym["mark_price"].values.astype(float)
    fr_arr     = df_sym["funding_rate"].values.astype(float)
    z_arr      = df_sym["z_score"].values.astype(float)
    sig_arr    = df_sym["signal"].values.astype(int)
    ts_arr     = df_sym["timestamp"].values        # numpy datetime64
    sym_name   = df_sym["symbol"].iloc[0]

    # ── State variables ───────────────────────────────────────────────────────
    realized_capital  = initial_capital
    in_position       = False
    pos_dir           = 0          # +1 short, -1 long
    entry_bar_idx     = -1
    signal_bar_idx    = -1         # bar where entry signal fired (for t+1 check)
    entry_price       = np.nan
    pos_size_usd      = 0.0
    entry_fee_paid    = 0.0
    accum_funding     = 0.0
    pending_entry_dir = 0          # queued entry direction (executes next bar)
    pending_entry_sig_bar = -1     # bar where the pending entry signal fired
    pending_exit      = False
    pending_exit_rsn  = ""

    equity_records = []
    trades         = []

    # ── Helper: close trade ───────────────────────────────────────────────────
    def _close_trade(exit_idx, exit_px, reason):
        nonlocal realized_capital, in_position, pos_dir
        nonlocal entry_bar_idx, signal_bar_idx, entry_price
        nonlocal pos_size_usd, entry_fee_paid, accum_funding

        if pos_dir == 1:    # short: profit when price falls
            price_pnl = pos_size_usd * (entry_price - exit_px) / entry_price
        else:               # long: profit when price rises
            price_pnl = pos_size_usd * (exit_px - entry_price) / entry_price

        exit_fee  = pos_size_usd * COST_PER_SIDE
        total_pnl = price_pnl + accum_funding - entry_fee_paid - exit_fee
        realized_capital += total_pnl

        safe_idx = min(exit_idx, n - 1)
        trades.append({
            "symbol":         sym_name,
            "signal_ts":      pd.Timestamp(ts_arr[signal_bar_idx]),
            "entry_ts":       pd.Timestamp(ts_arr[entry_bar_idx]),
            "exit_ts":        pd.Timestamp(ts_arr[safe_idx]),
            "direction":      "short" if pos_dir == 1 else "long",
            "entry_price":    entry_price,
            "exit_price":     exit_px,
            "hours_held":     safe_idx - entry_bar_idx,
            "pos_size_usd":   pos_size_usd,
            "price_pnl":      price_pnl,
            "funding_pnl":    accum_funding,
            "entry_fee":      entry_fee_paid,
            "exit_fee":       exit_fee,
            "total_pnl":      total_pnl,
            "exit_reason":    reason,
        })

        in_position    = False
        pos_dir        = 0
        entry_bar_idx  = -1
        signal_bar_idx = -1
        entry_price    = np.nan
        pos_size_usd   = 0.0
        entry_fee_paid = 0.0
        accum_funding  = 0.0

    # ── Main loop ─────────────────────────────────────────────────────────────
    for i in range(n):
        px      = prices[i]
        fr      = fr_arr[i]
        z       = z_arr[i]
        sig     = sig_arr[i]
        has_px  = not np.isnan(px)

        # ── Step 1: Execute pending exit at this bar's price ──────────────────
        #    Exit was triggered at bar i-1, executes at bar i (t+1 rule)
        if pending_exit and in_position:
            if has_px:
                _close_trade(i, px, pending_exit_rsn)
                pending_exit = False
            # If no price available: hold pending_exit, retry next bar

        # ── Step 2: Execute pending entry at this bar's price ─────────────────
        #    Signal fired at bar i-1, enters at bar i (t+1 rule)
        if pending_entry_dir != 0 and not in_position:
            if has_px:
                in_position     = True
                pos_dir         = pending_entry_dir
                entry_bar_idx   = i
                signal_bar_idx  = pending_entry_sig_bar
                entry_price     = px
                pos_size_usd    = realized_capital * pos_frac
                entry_fee_paid  = pos_size_usd * COST_PER_SIDE
                accum_funding   = 0.0
            pending_entry_dir = 0

        # ── Step 3: Process open position ─────────────────────────────────────
        if in_position:
            # Funding accrues this hour while position is open
            if pos_dir == 1:     # short: receive positive funding
                accum_funding += pos_size_usd * fr
            else:                # long: pay positive funding
                accum_funding -= pos_size_usd * fr

            hours_held  = i - entry_bar_idx + 1
            exit_reason = None

            # Priority 1 (lowest): z-score crosses back through mean
            if not np.isnan(z):
                if pos_dir == 1 and z <= z_exit:
                    exit_reason = "z_cross"
                elif pos_dir == -1 and z >= z_exit:
                    exit_reason = "z_cross"

            # Priority 2: max hold period expired
            if hours_held >= max_hold:
                exit_reason = "max_hold"

            # Priority 3 (highest): stop-loss hit
            if has_px:
                if pos_dir == 1 and px >= entry_price * (1.0 + stop_loss):
                    exit_reason = "stop_loss"
                elif pos_dir == -1 and px <= entry_price * (1.0 - stop_loss):
                    exit_reason = "stop_loss"

            if exit_reason and not pending_exit:
                pending_exit     = True
                pending_exit_rsn = exit_reason

        # ── Step 4: New entry signal ──────────────────────────────────────────
        #    Only when flat and nothing else queued.  Executes next bar (t+1).
        if (not in_position
                and not pending_exit
                and pending_entry_dir == 0
                and sig != 0
                and not np.isnan(z)):
            pending_entry_dir     = int(sig)
            pending_entry_sig_bar = i

        # ── Step 5: Mark-to-market equity ─────────────────────────────────────
        if in_position and has_px:
            if pos_dir == 1:
                unrealized = pos_size_usd * (entry_price - px) / entry_price
            else:
                unrealized = pos_size_usd * (px - entry_price) / entry_price
            current_eq = realized_capital + unrealized + accum_funding - entry_fee_paid
        else:
            current_eq = realized_capital

        equity_records.append({
            "timestamp":   pd.Timestamp(ts_arr[i]),
            "equity":      current_eq,
            "in_position": in_position,
        })

    # ── Force-close any open position at end of data ──────────────────────────
    if in_position:
        last_valid = n - 1
        while last_valid >= 0 and np.isnan(prices[last_valid]):
            last_valid -= 1
        if last_valid >= 0:
            _close_trade(last_valid, prices[last_valid], "end_of_data")

    equity_df = pd.DataFrame(equity_records)
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    return equity_df, trades_df


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2 — Performance metrics
# ═══════════════════════════════════════════════════════════════════════════════

def compute_metrics(
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    initial_capital: float = INITIAL_CAPITAL,
) -> dict:
    """
    Compute all performance metrics from equity curve and trade log.

    Sharpe / Sortino use hourly returns × sqrt(8760) for annualisation.
    """
    if equity_df.empty:
        return {}

    equity = equity_df["equity"].values.astype(float)

    # ── Return series ─────────────────────────────────────────────────────────
    hourly_ret = np.diff(equity) / equity[:-1]
    hourly_ret = hourly_ret[np.isfinite(hourly_ret)]

    mean_ret = hourly_ret.mean()
    std_ret  = hourly_ret.std(ddof=1)

    # Sharpe (annualised, hourly × √8760)
    sharpe = mean_ret / std_ret * np.sqrt(8760) if std_ret > 0 else np.nan

    # Sortino (downside deviation: RMS of negative returns)
    neg = hourly_ret[hourly_ret < 0]
    downside_std = np.sqrt(np.mean(neg**2)) if len(neg) > 0 else 0.0
    sortino = mean_ret / downside_std * np.sqrt(8760) if downside_std > 0 else np.nan

    # ── Drawdown ──────────────────────────────────────────────────────────────
    roll_max = np.maximum.accumulate(equity)
    dd = (equity - roll_max) / roll_max
    max_dd = dd.min()

    # ── Return ────────────────────────────────────────────────────────────────
    total_return = (equity[-1] - initial_capital) / initial_capital

    # ── Trade metrics ─────────────────────────────────────────────────────────
    if trades_df.empty:
        return {
            "sharpe": sharpe, "sortino": sortino,
            "total_return_pct": total_return * 100,
            "max_drawdown_pct": max_dd * 100,
            "n_trades": 0,
        }

    n_trades      = len(trades_df)
    winners       = trades_df[trades_df["total_pnl"] > 0]
    losers        = trades_df[trades_df["total_pnl"] <= 0]
    win_rate      = len(winners) / n_trades if n_trades else 0.0
    avg_dur       = trades_df["hours_held"].mean()

    # ── Funding metrics ───────────────────────────────────────────────────────
    total_funding = trades_df["funding_pnl"].sum()
    total_pnl_usd = trades_df["total_pnl"].sum()
    fund_pct_pnl  = (total_funding / total_pnl_usd * 100
                     if abs(total_pnl_usd) > 1e-6 else np.nan)

    # ── P&L decomposition ─────────────────────────────────────────────────────
    total_price   = trades_df["price_pnl"].sum()
    total_fees    = (trades_df["entry_fee"] + trades_df["exit_fee"]).sum()

    # ── Profit factor ─────────────────────────────────────────────────────────
    gross_profit = winners["total_pnl"].sum()
    gross_loss   = abs(losers["total_pnl"].sum())
    pf           = gross_profit / gross_loss if gross_loss > 1e-6 else np.inf

    # ── Exit reason breakdown ─────────────────────────────────────────────────
    reason_counts = trades_df["exit_reason"].value_counts().to_dict()

    return {
        # Risk-adjusted returns
        "sharpe":              sharpe,
        "sortino":             sortino,
        # Absolute returns
        "total_return_pct":    total_return * 100,
        "final_equity":        equity[-1],
        "max_drawdown_pct":    max_dd * 100,
        # Trade statistics
        "n_trades":            n_trades,
        "win_rate_pct":        win_rate * 100,
        "avg_duration_hours":  avg_dur,
        # Funding
        "total_funding_usd":   total_funding,
        "total_funding_pct":   total_funding / initial_capital * 100,
        "funding_pct_of_pnl":  fund_pct_pnl,
        # P&L decomposition
        "price_pnl_usd":       total_price,
        "funding_pnl_usd":     total_funding,
        "fees_usd":            total_fees,
        "total_pnl_usd":       total_pnl_usd,
        # Profit factor
        "profit_factor":       pf,
        # Exit breakdown (for reference)
        "exits_z_cross":       reason_counts.get("z_cross", 0),
        "exits_max_hold":      reason_counts.get("max_hold", 0),
        "exits_stop_loss":     reason_counts.get("stop_loss", 0),
        "exits_eod":           reason_counts.get("end_of_data", 0),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PART 3 — Walk-forward analysis (6-month folds)
# ═══════════════════════════════════════════════════════════════════════════════

def run_walk_forward(
    df_sym: pd.DataFrame,
    strategy: FundingStrategy,
    fold_months: int = 6,
    initial_capital: float = INITIAL_CAPITAL,
) -> list:
    """
    Split price-available data into consecutive 6-month test folds.

    For a rule-based rolling z-score strategy there is no trainable parameter;
    the "expanding window" simply means that by the start of each fold the
    168-hour rolling window has many months of warm-up history already baked in
    (pre-computed in df_sym["z_score"] on the full funding history).

    Each fold is backtested independently (fresh capital) so Sharpe values are
    directly comparable across periods.

    Returns
    -------
    list of dicts, one per fold, with keys:
        fold, start, end, sharpe, total_return_pct, n_trades
    """
    fold_results = []

    ts        = df_sym["timestamp"]
    fold_start = ts.min()
    end_ts    = ts.max()
    fold_idx  = 1

    while fold_start < end_ts:
        fold_end = fold_start + pd.DateOffset(months=fold_months)
        if fold_end > end_ts:
            fold_end = end_ts

        mask = (ts >= fold_start) & (ts < fold_end)
        fold_df = df_sym[mask].copy().reset_index(drop=True)

        if len(fold_df) < 200:
            break

        eq_df, tr_df = run_backtest(fold_df, strategy, initial_capital)

        if not eq_df.empty:
            m = compute_metrics(eq_df, tr_df, initial_capital)
            fold_results.append({
                "fold":             fold_idx,
                "start":            fold_start.strftime("%Y-%m"),
                "end":              fold_end.strftime("%Y-%m"),
                "sharpe":           m.get("sharpe", np.nan),
                "total_return_pct": m.get("total_return_pct", np.nan),
                "n_trades":         m.get("n_trades", 0),
                "max_drawdown_pct": m.get("max_drawdown_pct", np.nan),
            })

        fold_start = fold_end
        fold_idx  += 1

    return fold_results


# ═══════════════════════════════════════════════════════════════════════════════
# PART 4 — Output helpers
# ═══════════════════════════════════════════════════════════════════════════════

def print_results_table(
    results: dict,
    decomp: dict,
    wf: dict,
) -> None:
    """Pretty-print per-symbol results, P&L decomposition, and walk-forward."""
    BAR = "═" * 78

    # ── A: Per-symbol metrics ─────────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART A — PER-SYMBOL PERFORMANCE METRICS")
    print(BAR)

    col_w = 20
    syms  = list(results.keys())
    hdr   = f"{'Metric':<32}" + "".join(f"{s:>{col_w}}" for s in syms)
    print(hdr)
    print("-" * len(hdr))

    def _row(label, key, fmt):
        vals = []
        for s in syms:
            v = results[s].get(key, np.nan)
            try:
                vals.append(fmt.format(v))
            except Exception:
                vals.append(f"{'—':>{col_w}}")
        print(f"{label:<32}" + "".join(f"{v:>{col_w}}" for v in vals))

    _row("Sharpe Ratio (annualised)",  "sharpe",              "{:+.3f}")
    _row("Sortino Ratio",              "sortino",             "{:+.3f}")
    _row("Total Return (%)",           "total_return_pct",    "{:+.2f}%")
    _row("Max Drawdown (%)",           "max_drawdown_pct",    "{:.2f}%")
    _row("Number of Trades",           "n_trades",            "{:,}")
    _row("Win Rate (%)",               "win_rate_pct",        "{:.1f}%")
    _row("Avg Trade Duration (hours)", "avg_duration_hours",  "{:.1f}h")
    _row("Profit Factor",              "profit_factor",       "{:.2f}")
    print()
    _row("Total Funding Collected ($)", "total_funding_usd",  "${:,.2f}")
    _row("Funding as % of Capital",    "total_funding_pct",   "{:.2f}%")
    _row("Funding % of Total P&L",     "funding_pct_of_pnl",  "{:.1f}%")
    print()
    _row("Exits: z-cross",             "exits_z_cross",       "{:,}")
    _row("Exits: max-hold",            "exits_max_hold",      "{:,}")
    _row("Exits: stop-loss",           "exits_stop_loss",     "{:,}")

    # ── B: P&L Decomposition ──────────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART B — P&L DECOMPOSITION  (Price vs Funding vs Fees)")
    print(BAR)

    for sym in syms:
        m = results[sym]
        price_pnl   = m.get("price_pnl_usd",   0.0)
        fund_pnl    = m.get("funding_pnl_usd",  0.0)
        fees        = m.get("fees_usd",         0.0)
        total       = m.get("total_pnl_usd",    0.0)
        total_ret   = m.get("total_return_pct", np.nan)

        print(f"\n  {sym}")
        print(f"    Price P&L       : ${price_pnl:>+10,.2f}  ({price_pnl / INITIAL_CAPITAL * 100:>+6.2f}%)")
        print(f"    Funding P&L     : ${fund_pnl:>+10,.2f}  ({fund_pnl  / INITIAL_CAPITAL * 100:>+6.2f}%)")
        print(f"    Fees + Slippage : ${-fees:>+10,.2f}  ({-fees / INITIAL_CAPITAL * 100:>+6.2f}%)")
        print(f"    ─────────────────────────────────────────")
        print(f"    Net P&L         : ${total:>+10,.2f}  ({total_ret:>+6.2f}%)")

        if abs(total) > 1e-6:
            print(f"    Edge source     : "
                  f"{'Price' if abs(price_pnl) > abs(fund_pnl) else 'Funding'} dominant  "
                  f"(price={price_pnl/total*100:.0f}%  "
                  f"funding={fund_pnl/total*100:.0f}%  "
                  f"fees={-fees/total*100:.0f}%)")

    # ── C: Walk-forward ───────────────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART C — WALK-FORWARD SHARPE (6-month folds, expanding window)")
    print(BAR)

    wf_hdr = f"  {'Fold':<6} {'Period':<18} {'Sharpe':>10} {'Return':>10} {'N Trades':>10} {'MaxDD':>10}"
    print(wf_hdr)
    print("  " + "-" * (len(wf_hdr) - 2))

    for sym in syms:
        print(f"\n  {sym}")
        folds = wf.get(sym, [])
        if not folds:
            print("    (no data)")
            continue
        for f in folds:
            sharpe_str = f"{f['sharpe']:>+.3f}" if np.isfinite(f.get("sharpe", np.nan)) else "   n/a"
            ret_str    = f"{f['total_return_pct']:>+.2f}%" if np.isfinite(f.get("total_return_pct", np.nan)) else "   n/a"
            dd_str     = f"{f['max_drawdown_pct']:.2f}%" if np.isfinite(f.get("max_drawdown_pct", np.nan)) else "   n/a"
            print(f"    {f['fold']:<6} {f['start']}→{f['end']:<8} "
                  f"{sharpe_str:>10} {ret_str:>10} {f['n_trades']:>10,} {dd_str:>10}")


def _verify_timing(trades_df: pd.DataFrame, symbol: str) -> None:
    """Print first 3 trades showing signal_ts vs entry_ts to confirm t+1 execution."""
    if trades_df.empty:
        print(f"  {symbol}: no trades to verify.")
        return
    print(f"\n  {symbol} — first 3 trades (signal_ts → entry_ts gap confirms t+1):")
    for _, t in trades_df.head(3).iterrows():
        gap = (t["entry_ts"] - t["signal_ts"]).total_seconds() / 3600
        print(f"    signal={t['signal_ts'].strftime('%Y-%m-%d %H:%M')}  "
              f"entry={t['entry_ts'].strftime('%Y-%m-%d %H:%M')}  "
              f"gap={gap:.0f}h  dir={t['direction']:5s}  "
              f"entry_px={t['entry_price']:.2f}  "
              f"pnl=${t['total_pnl']:>+.2f}")


def save_equity_plot(equity_by_symbol: dict, path: str) -> None:
    """Save 3-panel equity curve plot."""
    fig, axes = plt.subplots(len(equity_by_symbol), 1,
                             figsize=(14, 4 * len(equity_by_symbol)),
                             sharex=False)
    if len(equity_by_symbol) == 1:
        axes = [axes]

    colors = {"BTC": "steelblue", "ETH": "darkorange", "SOL": "mediumseagreen"}

    for ax, (sym, eq_df) in zip(axes, equity_by_symbol.items()):
        if eq_df.empty:
            ax.set_title(f"{sym} — no data")
            continue
        ts  = eq_df["timestamp"]
        eq  = eq_df["equity"]
        ret = (eq.iloc[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

        ax.plot(ts, eq, lw=1.2, color=colors.get(sym, "navy"),
                label=f"{sym}  ({ret:+.2f}%)")
        ax.axhline(INITIAL_CAPITAL, color="gray", lw=0.7, ls="--", alpha=0.6,
                   label=f"Initial ${INITIAL_CAPITAL/1e3:.0f}k")
        ax.fill_between(ts, INITIAL_CAPITAL, eq,
                        where=eq >= INITIAL_CAPITAL,
                        alpha=0.15, color="green")
        ax.fill_between(ts, INITIAL_CAPITAL, eq,
                        where=eq < INITIAL_CAPITAL,
                        alpha=0.15, color="red")
        ax.set_ylabel("Equity (USD)")
        ax.set_title(f"{sym}  —  Funding Mean Reversion  |  "
                     f"Total Return {ret:+.2f}%")
        ax.legend(fontsize=9, loc="upper left")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.grid(True, alpha=0.2)

    fig.suptitle(
        "Funding Rate Mean Reversion — Equity Curves\n"
        f"Initial capital ${INITIAL_CAPITAL/1e3:.0f}k | "
        f"Costs: {TAKER_FEE*100:.3f}% taker + {SLIPPAGE*100:.3f}% slippage each side",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Equity curve saved: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 5 — Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    BAR = "═" * 78

    print(BAR)
    print("FUNDING RATE MEAN REVERSION STRATEGY — BACKTEST")
    print(BAR)

    # ── Load data ─────────────────────────────────────────────────────────────
    print("\nLoading data ...")
    df = pd.read_csv(DATA_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    print(f"  {len(df):,} rows | {df['symbol'].nunique()} symbols")

    # ── Strategy ──────────────────────────────────────────────────────────────
    strategy = FundingStrategy()
    p = strategy.get_params()
    print(f"\nStrategy parameters:")
    for k, v in p.items():
        print(f"  {k:<20}: {v}")

    print(f"\nCosts per side  : taker={TAKER_FEE*100:.3f}%  slippage={SLIPPAGE*100:.3f}%  "
          f"total={COST_PER_SIDE*100:.3f}%")
    print(f"Round-trip cost : {COST_PER_SIDE*2*100:.3f}%")

    # ── Per-symbol processing ─────────────────────────────────────────────────
    results_by_sym = {}
    equity_by_sym  = {}
    trades_by_sym  = {}
    wf_by_sym      = {}

    print(f"\n{BAR}")
    print("TIMING VERIFICATION  (signal at t → execution at t+1)")
    print(BAR)

    for sym in SYMBOLS:
        df_sym = df[df["symbol"] == sym].copy().reset_index(drop=True)

        # Compute signals on FULL history (warms rolling window before price era)
        df_sym = strategy.compute_signals(df_sym)

        # Restrict to price-available bars for backtesting
        df_price = df_sym.dropna(subset=["mark_price"]).copy().reset_index(drop=True)

        n_bars = len(df_price)
        t_start = df_price["timestamp"].min()
        t_end   = df_price["timestamp"].max()
        n_signals = (df_price["signal"] != 0).sum()

        print(f"\n  {sym}: {n_bars:,} bars  "
              f"({t_start.strftime('%Y-%m-%d')} → {t_end.strftime('%Y-%m-%d')})  "
              f"signals={n_signals:,}")

        # Full backtest
        eq_df, tr_df = run_backtest(df_price, strategy, INITIAL_CAPITAL)
        metrics      = compute_metrics(eq_df, tr_df, INITIAL_CAPITAL)

        results_by_sym[sym] = metrics
        equity_by_sym[sym]  = eq_df
        trades_by_sym[sym]  = tr_df

        # Timing verification — first 3 trades
        _verify_timing(tr_df, sym)

        # Walk-forward
        wf_by_sym[sym] = run_walk_forward(df_price, strategy, fold_months=6)

    # ── Print full results ────────────────────────────────────────────────────
    print_results_table(results_by_sym, results_by_sym, wf_by_sym)

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART D — DOES THE STRATEGY WORK AFTER COSTS?")
    print(BAR)

    for sym in SYMBOLS:
        m  = results_by_sym[sym]
        sh = m.get("sharpe", np.nan)
        rt = m.get("total_return_pct", np.nan)
        pf = m.get("profit_factor", np.nan)
        nt = m.get("n_trades", 0)
        fn = m.get("funding_pct_of_pnl", np.nan)
        dd = m.get("max_drawdown_pct", np.nan)

        works = (np.isfinite(sh) and sh > 0.5
                 and np.isfinite(rt) and rt > 0
                 and np.isfinite(pf) and pf > 1.0)

        verdict = "YES" if works else ("MARGINAL" if (np.isfinite(rt) and rt > 0) else "NO")

        print(f"\n  {sym}  →  {verdict}")
        print(f"    Sharpe={sh:+.3f}  Return={rt:+.2f}%  PF={pf:.2f}  "
              f"MaxDD={dd:.2f}%  N={nt}")
        if np.isfinite(fn):
            src = "FUNDING-driven" if fn > 50 else ("PRICE-driven" if fn < 0 else "MIXED")
            print(f"    Edge source: {src}  (funding={fn:.1f}% of P&L)")
        print(f"    Costs paid: ${m.get('fees_usd', 0):,.2f}  "
              f"({m.get('fees_usd', 0) / INITIAL_CAPITAL * 100:.2f}% of capital)")

    # ── Save outputs ──────────────────────────────────────────────────────────
    # Equity curve plot
    plot_path = os.path.join(OUTPUT_DIR, "funding_equity_curve.png")
    save_equity_plot(equity_by_sym, plot_path)

    # Trade log (all symbols combined)
    all_trades = [tr for tr in trades_by_sym.values() if not tr.empty]
    if all_trades:
        combined = pd.concat(all_trades, ignore_index=True)
        combined = combined.sort_values(["symbol", "entry_ts"]).reset_index(drop=True)
        trade_path = os.path.join(OUTPUT_DIR, "funding_trades.csv")
        combined.to_csv(trade_path, index=False)
        print(f"  Trade log saved : {trade_path}  ({len(combined):,} trades)")

    print(f"\n{BAR}")
    print("Done.")
    print(BAR)


if __name__ == "__main__":
    main()
