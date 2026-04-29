"""
momentum_backtest.py

Portfolio-level backtester for the cross-sectional momentum strategy.

EXECUTION TIMING (no look-ahead):
    Signal computed at Friday close using data through Thursday (skip day t).
    Trades execute at Monday open prices (3 calendar days later).

COSTS per side:
    Taker fee : 0.035 %
    Slippage  : 0.050 %  (wider for less-liquid alts)
    Total     : 0.085 %  →  0.170 % round-trip

PORTFOLIO ACCOUNTING:
    Allocated capital per position is fixed at entry (dollar amount).
    P&L = gross price return × allocated – fees.
    Both long and short legs use the same equity as base for sizing.
    Net exposure = long_exposure - short_exposure ≈ 0 (market neutral).

Run: python momentum_backtest.py
"""

import os
import sys
import warnings
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(__file__))
from momentum_strategy import MomentumStrategy

# ── Constants ─────────────────────────────────────────────────────────────────
TAKER_FEE       = 0.00035
SLIPPAGE        = 0.00050   # wider for alt perps
COST_PER_SIDE   = TAKER_FEE + SLIPPAGE      # 0.085 %
INITIAL_CAPITAL = 100_000.0

DATA_FILE  = "data/momentum_universe.csv"
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 1 — Position data class
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Position:
    symbol:        str
    side:          str           # 'long' or 'short'
    entry_date:    pd.Timestamp
    entry_price:   float
    allocated_usd: float         # fixed at entry
    stop_price:    float         # pre-computed stop level
    weeks_held:    int = 0
    entry_fee:     float = 0.0

    def unrealized_pnl(self, price: float) -> float:
        """Gross unrealized P&L (before exit fee)."""
        r = price / self.entry_price - 1
        return self.allocated_usd * (r if self.side == "long" else -r)

    def is_stop_hit(self, price: float) -> bool:
        if self.side == "long":
            return price <= self.stop_price
        return price >= self.stop_price

    def close_pnl(self, exit_price: float, exit_fee: float) -> float:
        """Net P&L including entry and exit fees."""
        r = exit_price / self.entry_price - 1
        gross = self.allocated_usd * (r if self.side == "long" else -r)
        return gross - self.entry_fee - exit_fee


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2 — Main backtester
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(
    df: pd.DataFrame,
    strategy: MomentumStrategy,
    initial_capital: float = INITIAL_CAPITAL,
) -> tuple:
    """
    Daily-resolution portfolio backtester.

    Parameters
    ----------
    df : long-format DataFrame (date, symbol, open, high, low, close, volume)
    strategy : MomentumStrategy instance
    initial_capital : starting USD capital

    Returns
    -------
    equity_df    : daily equity curve (includes long/short leg decomposition)
    trades_df    : completed trade log
    snapshots_df : weekly portfolio snapshots
    """
    p = strategy.get_params()
    n_long           = p["n_long"]
    n_short          = p["n_short"]
    long_pct         = p["long_pct"]
    short_pct        = p["short_pct"]
    stop_loss        = p["stop_loss"]
    max_hold_weeks   = p["max_hold_weeks"]
    max_pos_pct      = p["max_position_pct"]

    # ── Prepare data ──────────────────────────────────────────────────────────
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()

    close_wide = df.pivot_table(index="date", columns="symbol", values="close").sort_index()
    open_wide  = df.pivot_table(index="date", columns="symbol", values="open").sort_index()

    all_dates = close_wide.index

    # ── Pre-compute all weekly signals ────────────────────────────────────────
    signals = strategy.compute_weekly_signals(df)
    # Index by execution date so we can look up quickly in the loop
    exec_to_signal = {s["exec_date"]: s for s in signals}

    # ── State ─────────────────────────────────────────────────────────────────
    positions: dict[str, Position] = {}   # symbol → Position

    long_realized  = 0.0    # net P&L from closed long positions (fees included)
    short_realized = 0.0    # net P&L from closed short positions

    pending_stop_exits: list[str] = []    # symbols to exit at next open (stop hit)

    equity_records   = []
    trade_records    = []
    snapshot_records = []

    # ── Daily loop ────────────────────────────────────────────────────────────
    for date in all_dates:

        closes = close_wide.loc[date].dropna()
        opens  = open_wide.loc[date].dropna()

        # ── 1. Execute stop-loss exits at today's open ─────────────────────
        for sym in pending_stop_exits:
            if sym not in positions:
                continue
            pos     = positions.pop(sym)
            exit_px = opens.get(sym, pos.entry_price)   # fallback to entry if no open
            exit_fee = pos.allocated_usd * COST_PER_SIDE
            pnl     = pos.close_pnl(exit_px, exit_fee)

            if pos.side == "long":
                long_realized += pnl
            else:
                short_realized += pnl

            trade_records.append(_trade_record(
                pos, exit_px, exit_fee, pnl, date, "stop_loss"
            ))

        pending_stop_exits.clear()

        # ── 2. Execute weekly rebalance trades at today's open ─────────────
        if date in exec_to_signal:
            signal   = exec_to_signal[date]
            sig_date = signal["signal_date"]

            target_longs  = set(signal["longs"])
            target_shorts = set(signal["shorts"])
            target = {s: "long" for s in target_longs}
            target.update({s: "short" for s in target_shorts})

            current = {sym: pos.side for sym, pos in positions.items()}

            # Determine exits:
            #   - symbol no longer in target
            #   - symbol changed side
            #   - max hold weeks exceeded
            exits = set()
            for sym, side in current.items():
                if sym not in target:
                    exits.add(sym)
                elif target[sym] != side:
                    exits.add(sym)          # side flip
                elif positions[sym].weeks_held >= max_hold_weeks:
                    exits.add(sym)          # expire and optionally re-enter

            # Close exiting positions
            for sym in exits:
                pos = positions.pop(sym)
                if sym in opens:
                    exit_px = opens[sym]
                else:
                    exit_px = closes.get(sym, pos.entry_price)
                exit_fee = pos.allocated_usd * COST_PER_SIDE
                pnl = pos.close_pnl(exit_px, exit_fee)
                if pos.side == "long":
                    long_realized += pnl
                else:
                    short_realized += pnl
                trade_records.append(_trade_record(
                    pos, exit_px, exit_fee, pnl, date,
                    "max_hold" if positions.get(sym) is None and
                    sym in target and positions.get(sym, Position("","long",date,1,0,0,0,0)).weeks_held >= max_hold_weeks
                    else "rebalance"
                ))

            # Increment weeks_held for continuing positions
            for sym in set(current) - exits:
                if sym in positions:
                    positions[sym].weeks_held += 1

            # Compute current equity for sizing new entries
            equity_now = _compute_equity(
                initial_capital, long_realized, short_realized, positions, closes
            )

            # Determine new entries (target minus current, plus expired re-entries)
            new_syms = {s: side for s, side in target.items()
                        if s not in positions}

            for sym, side in new_syms.items():
                if sym not in opens:
                    continue
                entry_px = opens[sym]
                if not np.isfinite(entry_px) or entry_px <= 0:
                    continue

                n = n_long if side == "long" else n_short
                frac = long_pct / n if side == "long" else short_pct / n
                alloc = min(equity_now * frac, equity_now * max_pos_pct)
                if alloc <= 0:
                    continue

                entry_fee = alloc * COST_PER_SIDE
                stop_px   = (entry_px * (1.0 - stop_loss) if side == "long"
                             else entry_px * (1.0 + stop_loss))

                positions[sym] = Position(
                    symbol        = sym,
                    side          = side,
                    entry_date    = date,
                    entry_price   = entry_px,
                    allocated_usd = alloc,
                    stop_price    = stop_px,
                    weeks_held    = 0,
                    entry_fee     = entry_fee,
                )
                trade_records.append({
                    "date":         date,
                    "signal_date":  sig_date,
                    "symbol":       sym,
                    "action":       "open",
                    "side":         side,
                    "price":        entry_px,
                    "allocated":    alloc,
                    "fee":          entry_fee,
                    "pnl":          np.nan,
                    "exit_reason":  np.nan,
                })

            # Snapshot: weekly portfolio state
            snap_long  = {s: pos for s, pos in positions.items() if pos.side == "long"}
            snap_short = {s: pos for s, pos in positions.items() if pos.side == "short"}
            equity_snap = _compute_equity(
                initial_capital, long_realized, short_realized, positions, closes
            )
            snapshot_records.append({
                "date":            date,
                "signal_date":     sig_date,
                "n_long":          len(snap_long),
                "n_short":         len(snap_short),
                "long_symbols":    ",".join(sorted(snap_long.keys())),
                "short_symbols":   ",".join(sorted(snap_short.keys())),
                "equity":          equity_snap,
                "long_alloc":      sum(p.allocated_usd for p in snap_long.values()),
                "short_alloc":     sum(p.allocated_usd for p in snap_short.values()),
                "n_available":     signal["n_available"],
                "top_score":       max(signal["scores"].values(), default=np.nan),
                "bottom_score":    min(signal["scores"].values(), default=np.nan),
            })

        # ── 3. Update unrealized P&L and equity at close ───────────────────
        long_unreal  = 0.0
        short_unreal = 0.0
        long_open_fees  = 0.0
        short_open_fees = 0.0

        for sym, pos in positions.items():
            if sym in closes:
                pnl = pos.unrealized_pnl(closes[sym])
            else:
                pnl = 0.0   # price unavailable: mark at break-even
            if pos.side == "long":
                long_unreal  += pnl
                long_open_fees += pos.entry_fee
            else:
                short_unreal  += pnl
                short_open_fees += pos.entry_fee

        equity = (initial_capital
                  + long_realized + short_realized
                  + long_unreal   + short_unreal
                  - long_open_fees - short_open_fees)

        long_pnl_total  = long_realized  + long_unreal  - long_open_fees
        short_pnl_total = short_realized + short_unreal - short_open_fees

        long_alloc_now  = sum(p.allocated_usd for p in positions.values() if p.side == "long")
        short_alloc_now = sum(p.allocated_usd for p in positions.values() if p.side == "short")
        net_exp   = (long_alloc_now - short_alloc_now) / equity if equity > 0 else 0.0
        gross_exp = (long_alloc_now + short_alloc_now) / equity if equity > 0 else 0.0

        equity_records.append({
            "date":          date,
            "equity":        equity,
            "long_pnl":      long_pnl_total,
            "short_pnl":     short_pnl_total,
            "net_exposure":  net_exp,
            "gross_exposure": gross_exp,
            "n_positions":   len(positions),
        })

        # ── 4. Check stop-losses at close → execute at next open ───────────
        for sym, pos in positions.items():
            if sym in closes and pos.is_stop_hit(closes[sym]):
                pending_stop_exits.append(sym)

    # ── Force-close remaining positions at last date ──────────────────────────
    if positions:
        last_date   = all_dates[-1]
        last_closes = close_wide.loc[last_date].dropna()
        for sym in list(positions.keys()):
            pos = positions.pop(sym)
            exit_px  = last_closes.get(sym, pos.entry_price)
            exit_fee = pos.allocated_usd * COST_PER_SIDE
            pnl      = pos.close_pnl(exit_px, exit_fee)
            if pos.side == "long":
                long_realized += pnl
            else:
                short_realized += pnl
            trade_records.append(_trade_record(
                pos, exit_px, exit_fee, pnl, last_date, "end_of_data"
            ))

    equity_df    = pd.DataFrame(equity_records)
    trades_df    = pd.DataFrame(trade_records)
    snapshots_df = pd.DataFrame(snapshot_records)

    return equity_df, trades_df, snapshots_df


# ── Helpers ────────────────────────────────────────────────────────────────────

def _compute_equity(initial, long_real, short_real, positions, closes):
    long_unreal = short_unreal = long_fees = short_fees = 0.0
    for sym, pos in positions.items():
        px = closes.get(sym)
        if px is not None and np.isfinite(px):
            upnl = pos.unrealized_pnl(px)
        else:
            upnl = 0.0
        if pos.side == "long":
            long_unreal += upnl; long_fees += pos.entry_fee
        else:
            short_unreal += upnl; short_fees += pos.entry_fee
    return (initial + long_real + short_real
            + long_unreal + short_unreal - long_fees - short_fees)


def _trade_record(pos, exit_px, exit_fee, pnl, exit_date, reason):
    return {
        "date":        exit_date,
        "signal_date": np.nan,
        "symbol":      pos.symbol,
        "action":      "close",
        "side":        pos.side,
        "price":       exit_px,
        "allocated":   pos.allocated_usd,
        "fee":         exit_fee,
        "pnl":         pnl,
        "exit_reason": reason,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PART 3 — Performance metrics
# ═══════════════════════════════════════════════════════════════════════════════

def compute_metrics(
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    snapshots_df: pd.DataFrame,
    initial_capital: float = INITIAL_CAPITAL,
) -> dict:
    """Compute all performance metrics from daily equity curve and trade log."""
    if equity_df.empty:
        return {}

    eq   = equity_df.set_index("date")["equity"].sort_index()
    lp   = equity_df.set_index("date")["long_pnl"].sort_index()
    sp   = equity_df.set_index("date")["short_pnl"].sort_index()

    # ── Weekly returns (signal day = Friday) ─────────────────────────────────
    weekly_eq  = eq.resample("W-FRI").last().dropna()
    weekly_ret = weekly_eq.pct_change().dropna()
    n_weeks    = len(weekly_ret)

    mean_w  = weekly_ret.mean()
    std_w   = weekly_ret.std(ddof=1)

    sharpe  = mean_w / std_w * np.sqrt(52) if std_w > 0 else np.nan

    neg_w   = weekly_ret[weekly_ret < 0]
    ds_std  = np.sqrt(np.mean(neg_w**2)) if len(neg_w) > 0 else 0.0
    sortino = mean_w / ds_std * np.sqrt(52) if ds_std > 0 else np.nan

    # ── Annualised return ─────────────────────────────────────────────────────
    n_years  = (eq.index[-1] - eq.index[0]).days / 365.25
    total_ret = (eq.iloc[-1] - initial_capital) / initial_capital
    ann_ret   = (1 + total_ret) ** (1 / n_years) - 1 if n_years > 0 else np.nan

    # ── Drawdown ──────────────────────────────────────────────────────────────
    roll_max = eq.cummax()
    dd       = (eq - roll_max) / roll_max
    max_dd   = dd.min()
    calmar   = ann_ret / abs(max_dd) if max_dd != 0 and np.isfinite(max_dd) else np.nan

    # ── Turnover ─────────────────────────────────────────────────────────────
    opens_df = trades_df[trades_df["action"] == "open"] if not trades_df.empty else pd.DataFrame()
    closes_df = trades_df[trades_df["action"] == "close"] if not trades_df.empty else pd.DataFrame()

    n_rebalances = len(snapshots_df) if not snapshots_df.empty else 0

    if not opens_df.empty and not snapshots_df.empty:
        # Turnover: sum of newly opened allocated capital per rebalance / equity
        opened_per_rebal = opens_df.groupby("date")["allocated"].sum()
        avg_equity_rebal = snapshots_df.set_index("date")["equity"]
        turnover_pcts = []
        for d, alloc in opened_per_rebal.items():
            eq_val = avg_equity_rebal.get(d, initial_capital)
            turnover_pcts.append(alloc / eq_val * 100)
        avg_turnover = np.mean(turnover_pcts) if turnover_pcts else np.nan
    else:
        avg_turnover = np.nan

    # ── Win rate (per rebalance) ──────────────────────────────────────────────
    if not snapshots_df.empty and len(snapshots_df) > 1:
        snap_eq = snapshots_df.set_index("date")["equity"].sort_index()
        rebal_ret = snap_eq.pct_change().dropna()
        win_rate = (rebal_ret > 0).mean() * 100
        best_week  = weekly_ret.max() * 100
        worst_week = weekly_ret.min() * 100
    else:
        win_rate = best_week = worst_week = np.nan

    # ── Net / gross exposure ─────────────────────────────────────────────────
    avg_net_exp   = equity_df["net_exposure"].mean() * 100
    avg_gross_exp = equity_df["gross_exposure"].mean() * 100

    # ── Long / short leg ─────────────────────────────────────────────────────
    long_total  = lp.iloc[-1] if not lp.empty else 0.0
    short_total = sp.iloc[-1] if not sp.empty else 0.0

    # Hit rate per leg (weekly)
    long_weekly  = lp.resample("W-FRI").last().pct_change().dropna()
    short_weekly = sp.resample("W-FRI").last().pct_change().dropna()
    long_hit  = (long_weekly > 0).mean() * 100  if len(long_weekly) > 0 else np.nan
    short_hit = (short_weekly > 0).mean() * 100 if len(short_weekly) > 0 else np.nan

    # ── P&L decomposition ─────────────────────────────────────────────────────
    total_pnl = eq.iloc[-1] - initial_capital
    fees_paid = 0.0
    if not closes_df.empty:
        fees_paid = closes_df["fee"].sum()
    if not opens_df.empty:
        fees_paid += opens_df["fee"].sum()

    return {
        # Risk-adjusted
        "sharpe":            sharpe,
        "sortino":           sortino,
        "calmar":            calmar,
        # Returns
        "total_return_pct":  total_ret * 100,
        "ann_return_pct":    ann_ret * 100,
        "final_equity":      eq.iloc[-1],
        "max_drawdown_pct":  max_dd * 100,
        # Activity
        "n_rebalances":      n_rebalances,
        "avg_turnover_pct":  avg_turnover,
        "win_rate_pct":      win_rate,
        "best_week_pct":     best_week,
        "worst_week_pct":    worst_week,
        # Exposure
        "avg_net_exp_pct":   avg_net_exp,
        "avg_gross_exp_pct": avg_gross_exp,
        # Decomposition
        "long_pnl":          long_total,
        "short_pnl":         short_total,
        "total_pnl":         total_pnl,
        "fees_paid":         fees_paid,
        "long_hit_pct":      long_hit,
        "short_hit_pct":     short_hit,
        # Duration
        "backtest_years":    n_years,
        "n_weeks":           n_weeks,
    }


def per_year_sharpe(equity_df: pd.DataFrame) -> dict:
    """Compute Sharpe ratio for each calendar year (weekly returns)."""
    eq = equity_df.set_index("date")["equity"].sort_index()
    weekly_eq = eq.resample("W-FRI").last().dropna()
    weekly_ret = weekly_eq.pct_change().dropna()

    results = {}
    for year in range(2019, 2027):
        yr = weekly_ret[weekly_ret.index.year == year]
        if len(yr) < 4:
            continue
        m  = yr.mean()
        s  = yr.std(ddof=1)
        sh = m / s * np.sqrt(52) if s > 0 else np.nan
        results[year] = {
            "sharpe":     sh,
            "return_pct": ((1 + yr).prod() - 1) * 100,
            "n_weeks":    len(yr),
        }
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# PART 4 — Walk-forward (rolling 6-month Sharpe)
# ═══════════════════════════════════════════════════════════════════════════════

def rolling_6m_sharpe(equity_df: pd.DataFrame, window_months: int = 6) -> pd.DataFrame:
    """Return a DataFrame of rolling 6-month Sharpe values (based on weekly returns)."""
    eq = equity_df.set_index("date")["equity"].sort_index()
    weekly_eq  = eq.resample("W-FRI").last().dropna()
    weekly_ret = weekly_eq.pct_change().dropna()

    records = []
    dates   = weekly_ret.index

    for i in range(len(dates)):
        window_end   = dates[i]
        window_start = window_end - pd.DateOffset(months=window_months)
        window_data  = weekly_ret[(weekly_ret.index > window_start) & (weekly_ret.index <= window_end)]
        if len(window_data) < 8:
            continue
        m  = window_data.mean()
        s  = window_data.std(ddof=1)
        sh = m / s * np.sqrt(52) if s > 0 else np.nan
        records.append({"date": window_end, "rolling_sharpe": sh})

    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 5 — Output: plots + CSVs
# ═══════════════════════════════════════════════════════════════════════════════

def save_equity_plot(equity_df: pd.DataFrame, path: str) -> None:
    """Two-panel plot: total equity + long/short leg P&L decomposition."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    dates  = equity_df["date"]
    equity = equity_df["equity"]
    lp     = equity_df["long_pnl"]
    sp     = equity_df["short_pnl"]

    # Top: total equity
    ax1 = axes[0]
    ax1.plot(dates, equity, lw=1.5, color="steelblue", label="Portfolio equity")
    ax1.axhline(INITIAL_CAPITAL, color="gray", lw=0.7, ls="--", alpha=0.7,
                label=f"Initial ${INITIAL_CAPITAL/1e3:.0f}k")
    ax1.fill_between(dates, INITIAL_CAPITAL, equity,
                     where=equity >= INITIAL_CAPITAL, alpha=0.12, color="green")
    ax1.fill_between(dates, INITIAL_CAPITAL, equity,
                     where=equity < INITIAL_CAPITAL, alpha=0.12, color="red")
    ax1.set_ylabel("Equity (USD)")
    ret_pct = (equity.iloc[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    ax1.set_title(f"Cross-Sectional Momentum — Portfolio Equity  ({ret_pct:+.2f}%)")
    ax1.legend(fontsize=9); ax1.grid(True, alpha=0.2)

    # Bottom: long vs short leg P&L
    ax2 = axes[1]
    ax2.plot(dates, lp, lw=1.2, color="forestgreen",  alpha=0.85, label="Long leg P&L")
    ax2.plot(dates, sp, lw=1.2, color="firebrick",     alpha=0.85, label="Short leg P&L")
    ax2.plot(dates, lp + sp, lw=1.5, color="navy",    alpha=0.90, label="Combined P&L", ls="--")
    ax2.axhline(0, color="gray", lw=0.7, ls="-", alpha=0.5)
    ax2.set_ylabel("Cumulative P&L (USD)")
    ax2.set_title("Long Leg vs Short Leg Decomposition")
    ax2.legend(fontsize=9); ax2.grid(True, alpha=0.2)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

    fig.autofmt_xdate(rotation=30)
    fig.suptitle(
        f"Cross-Sectional Momentum  |  "
        f"Formation 14d, Top/Bottom 4, 40/40% L/S  |  "
        f"Costs {COST_PER_SIDE*2*100:.2f}% RT",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Equity curve saved  : {path}")


def save_monthly_heatmap(equity_df: pd.DataFrame, path: str) -> None:
    """Monthly returns heatmap (years × months)."""
    eq  = equity_df.set_index("date")["equity"].sort_index()
    mon = eq.resample("ME").last().pct_change().dropna()

    mon_df = pd.DataFrame({
        "year":   mon.index.year,
        "month":  mon.index.month,
        "ret":    mon.values,
    })
    pivot = mon_df.pivot(index="year", columns="month", values="ret")

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    years  = pivot.index.tolist()
    data   = pivot.reindex(columns=range(1, 13)).values

    fig, ax = plt.subplots(figsize=(14, max(4, len(years) * 0.55 + 1.5)))

    vals = data[~np.isnan(data)]
    if len(vals):
        vmax = max(abs(np.percentile(vals, 2)), abs(np.percentile(vals, 98)))
        norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    else:
        norm = None

    im = ax.imshow(data, aspect="auto", cmap="RdYlGn", norm=norm)
    plt.colorbar(im, ax=ax, label="Monthly Return")

    ax.set_xticks(range(12));  ax.set_xticklabels(months, fontsize=9)
    ax.set_yticks(range(len(years)));  ax.set_yticklabels(years, fontsize=9)

    for i in range(len(years)):
        for j in range(12):
            v = data[i, j]
            if not np.isnan(v):
                txt_col = "black" if abs(v) < 0.10 else "white"
                ax.text(j, i, f"{v*100:.1f}%", ha="center", va="center",
                        fontsize=7, color=txt_col, fontweight="bold")

    ax.set_title("Monthly Returns Heatmap — Cross-Sectional Momentum", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Monthly heatmap saved: {path}")


def save_rolling_sharpe_plot(rs_df: pd.DataFrame, path: str) -> None:
    """Plot rolling 6-month Sharpe."""
    if rs_df.empty:
        return
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(rs_df["date"], rs_df["rolling_sharpe"], lw=1.4, color="steelblue")
    ax.axhline(0, color="black", lw=0.8, ls="--", alpha=0.5)
    ax.axhline(1, color="green", lw=0.6, ls=":", alpha=0.6, label="Sharpe=1")
    ax.axhline(-1, color="red",  lw=0.6, ls=":", alpha=0.6, label="Sharpe=-1")
    ax.fill_between(rs_df["date"], 0, rs_df["rolling_sharpe"],
                    where=rs_df["rolling_sharpe"] >= 0, alpha=0.15, color="green")
    ax.fill_between(rs_df["date"], 0, rs_df["rolling_sharpe"],
                    where=rs_df["rolling_sharpe"] < 0, alpha=0.15, color="red")
    ax.set_ylabel("Sharpe Ratio"); ax.set_title("Rolling 6-Month Sharpe Ratio")
    ax.legend(fontsize=9); ax.grid(True, alpha=0.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Rolling Sharpe saved: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 6 — Print results
# ═══════════════════════════════════════════════════════════════════════════════

def print_full_results(
    metrics: dict,
    per_year: dict,
    rs_df: pd.DataFrame,
    first_signals: list,
) -> None:
    BAR = "═" * 72

    # ── A: Timing verification ─────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART E — TIMING VERIFICATION  (Friday close → Monday open)")
    print(BAR)
    for s in first_signals[:3]:
        gap = (s["exec_date"] - s["signal_date"]).days
        print(f"  Signal: {s['signal_date'].strftime('%Y-%m-%d %A')}  "
              f"→  Execute: {s['exec_date'].strftime('%Y-%m-%d %A')}  "
              f"(gap={gap} days)")
        print(f"    Longs : {s['longs']}")
        print(f"    Shorts: {s['shorts']}")

    # ── B: Full metrics table ──────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART B — FULL PERFORMANCE METRICS")
    print(BAR)

    def _p(label, key, fmt):
        v = metrics.get(key, np.nan)
        try:
            fv = float(v)
        except (TypeError, ValueError):
            fv = np.nan
        if np.isfinite(fv):
            print(f"  {label:<38}: {fmt.format(fv)}")
        else:
            print(f"  {label:<38}: n/a")

    _p("Sharpe Ratio (annualised, weekly)",     "sharpe",           "{:+.3f}")
    _p("Sortino Ratio",                         "sortino",          "{:+.3f}")
    _p("Calmar Ratio",                          "calmar",           "{:+.3f}")
    print()
    _p("Total Return",                          "total_return_pct", "{:+.2f}%")
    _p("Annualised Return",                     "ann_return_pct",   "{:+.2f}%")
    _p("Max Drawdown",                          "max_drawdown_pct", "{:.2f}%")
    print()
    _p("Number of Rebalances",                  "n_rebalances",     "{:,.0f}")
    _p("Avg Weekly Turnover",                   "avg_turnover_pct", "{:.1f}%")
    _p("Win Rate (per rebalance)",               "win_rate_pct",     "{:.1f}%")
    _p("Best Weekly Return",                    "best_week_pct",    "{:+.2f}%")
    _p("Worst Weekly Return",                   "worst_week_pct",   "{:+.2f}%")
    print()
    _p("Average Net Exposure (market neutral?)", "avg_net_exp_pct",  "{:+.1f}%")
    _p("Average Gross Exposure",                "avg_gross_exp_pct","{:.1f}%")
    print()
    _p("Backtest Length (years)",               "backtest_years",   "{:.1f}")
    _p("Total Weeks in Backtest",               "n_weeks",          "{:,.0f}")

    # ── C: P&L decomposition ───────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART C — P&L DECOMPOSITION  (Long leg vs Short leg)")
    print(BAR)

    total_pnl  = metrics.get("total_pnl",  np.nan)
    long_pnl   = metrics.get("long_pnl",   np.nan)
    short_pnl  = metrics.get("short_pnl",  np.nan)
    fees       = metrics.get("fees_paid",  np.nan)
    long_hit   = metrics.get("long_hit_pct", np.nan)
    short_hit  = metrics.get("short_hit_pct", np.nan)

    ic = INITIAL_CAPITAL
    print(f"\n  Long leg P&L     : ${long_pnl:>+10,.2f}  ({long_pnl/ic*100:>+6.2f}%)")
    print(f"  Short leg P&L    : ${short_pnl:>+10,.2f}  ({short_pnl/ic*100:>+6.2f}%)")
    print(f"  Fees + slippage  : ${-fees:>+10,.2f}  ({-fees/ic*100:>+6.2f}%)")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  Net P&L          : ${total_pnl:>+10,.2f}  ({total_pnl/ic*100:>+6.2f}%)")

    if np.isfinite(long_pnl) and np.isfinite(short_pnl):
        if long_pnl > 0 and short_pnl > 0:
            tag = "BOTH LEGS POSITIVE ← genuine alpha candidate"
        elif long_pnl > 0 > short_pnl:
            tag = "Long works, short hurts ← may be disguised beta"
        elif short_pnl > 0 > long_pnl:
            tag = "Short works, long hurts ← unusual (bear market edge?)"
        else:
            tag = "BOTH LEGS NEGATIVE ← no edge"
        print(f"\n  Assessment: {tag}")
        if np.isfinite(long_hit) and np.isfinite(short_hit):
            print(f"  Long leg weekly hit rate : {long_hit:.1f}%")
            print(f"  Short leg weekly hit rate: {short_hit:.1f}%")

    # ── D: Per-year Sharpe ─────────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART D — PER-YEAR SHARPE  (market-neutral check)")
    print(BAR)
    print(f"\n  {'Year':<6} {'Sharpe':>8} {'Return':>10} {'Weeks':>7}  Notes")
    print(f"  {'-'*6} {'-'*8} {'-'*10} {'-'*7}  {'-'*30}")

    all_sharpes = []
    for year in sorted(per_year.keys()):
        d    = per_year[year]
        sh   = d["sharpe"]
        ret  = d["return_pct"]
        nw   = d["n_weeks"]
        all_sharpes.append(sh)

        note = ""
        if year in (2021, 2023, 2024):
            note = "(bull market)"
        elif year == 2022:
            note = "(bear market)"

        sh_str  = f"{sh:>+8.3f}" if np.isfinite(sh) else "     n/a"
        ret_str = f"{ret:>+8.2f}%" if np.isfinite(ret) else "      n/a"
        print(f"  {year:<6} {sh_str} {ret_str} {nw:>7,}  {note}")

    # Market-neutral flag
    valid = [s for s in all_sharpes if np.isfinite(s)]
    if valid:
        pct_pos = sum(1 for s in valid if s > 0) / len(valid) * 100
        print(f"\n  Positive Sharpe years: {pct_pos:.0f}% ({sum(1 for s in valid if s > 0)}/{len(valid)})")

        bull_years = [y for y in [2021, 2023, 2024] if y in per_year and np.isfinite(per_year[y]["sharpe"])]
        bear_years = [y for y in [2022]              if y in per_year and np.isfinite(per_year[y]["sharpe"])]
        if bull_years and bear_years:
            bull_avg = np.mean([per_year[y]["sharpe"] for y in bull_years])
            bear_avg = np.mean([per_year[y]["sharpe"] for y in bear_years])
            print(f"  Avg Sharpe bull markets: {bull_avg:+.3f}")
            print(f"  Avg Sharpe bear markets: {bear_avg:+.3f}")
            if abs(bull_avg - bear_avg) > 1.0:
                print(f"  ⚠  Large bull/bear disparity → may be disguised beta")
            else:
                print(f"  ✓  Consistent across market regimes")

    # ── F: Net exposure ────────────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART F — MARKET NEUTRALITY CHECK")
    print(BAR)
    net = metrics.get("avg_net_exp_pct", np.nan)
    gross = metrics.get("avg_gross_exp_pct", np.nan)
    print(f"\n  Average net exposure   : {net:+.1f}%  "
          f"({'≈ market neutral ✓' if abs(net) < 5 else '⚠ NOT market neutral'})")
    print(f"  Average gross exposure : {gross:.1f}%  (target = 80%)")

    # ── G: Honest assessment ───────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART G — HONEST ASSESSMENT")
    print(BAR)
    sh   = metrics.get("sharpe",           np.nan)
    ret  = metrics.get("total_return_pct", np.nan)
    dd   = metrics.get("max_drawdown_pct", np.nan)
    lp_v = metrics.get("long_pnl",         np.nan)
    sp_v = metrics.get("short_pnl",        np.nan)

    if not np.isfinite(sh):
        print("\n  INSUFFICIENT DATA — cannot assess.")
        return

    works = sh > 0.5 and np.isfinite(ret) and ret > 0

    print(f"\n  Overall: {'POSITIVE EDGE (conditional — see notes)' if works else 'NO CLEAR EDGE'}")
    print(f"\n  Sharpe={sh:+.3f}  Return={ret:+.2f}%  MaxDD={dd:.2f}%")

    # Red flags
    if np.isfinite(lp_v) and np.isfinite(sp_v):
        if lp_v > 0 and sp_v < 0 and abs(sp_v) > lp_v * 0.5:
            print("\n  ⚠  RED FLAG: Short leg is a significant drag.")
            print("     In crypto bull markets, shorting losers = shorting assets with")
            print("     strong negative autocorrelation. The strategy may be capturing")
            print("     long beta, not a pure momentum factor.")
        if lp_v < 0:
            print("\n  ⚠  RED FLAG: Long leg (buying winners) is LOSING money.")
            print("     This contradicts the momentum hypothesis.")

    if per_year:
        valid_years = {y: d for y, d in per_year.items() if np.isfinite(d["sharpe"])}
        if 2022 in valid_years and valid_years[2022]["sharpe"] < -0.3:
            print("\n  ⚠  2022 (bear market): strategy struggled.")
            if any(valid_years.get(y, {}).get("sharpe", 0) > 0 for y in [2021, 2023, 2024]):
                print("     Strong in bulls, weak in bears → may be leveraged beta.")

    rt = (COST_PER_SIDE * 2 * 100)
    turns = metrics.get("avg_turnover_pct", np.nan)
    if np.isfinite(turns):
        ann_cost = turns * 52 * rt / 100
        print(f"\n  Annual fee drag estimate: {turns:.1f}% turnover/week × "
              f"{rt:.3f}% RT cost × 52 = {ann_cost:.1f}% p.a.")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 7 — Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    BAR = "═" * 72
    print(BAR)
    print("CROSS-SECTIONAL MOMENTUM STRATEGY — BACKTEST")
    print(BAR)

    # ── Load data ─────────────────────────────────────────────────────────
    print(f"\nLoading {DATA_FILE} ...")
    df = pd.read_csv(DATA_FILE)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    n_sym = df["symbol"].nunique()
    syms  = sorted(df["symbol"].unique())
    print(f"  {len(df):,} rows | {n_sym} symbols: {syms}")
    print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()}")

    # ── Strategy ──────────────────────────────────────────────────────────
    strategy = MomentumStrategy()
    p = strategy.get_params()
    print(f"\nStrategy parameters:")
    for k, v in p.items():
        print(f"  {k:<22}: {v}")
    print(f"\nCosts per side: taker={TAKER_FEE*100:.3f}%  slippage={SLIPPAGE*100:.3f}%  "
          f"total={COST_PER_SIDE*100:.3f}%")
    print(f"Round-trip    : {COST_PER_SIDE*2*100:.3f}%")

    # ── Universe summary ──────────────────────────────────────────────────
    print(f"\n{BAR}")
    print("PART A — UNIVERSE SUMMARY")
    print(BAR)
    print(f"\n  {n_sym} symbols pass the 365-day filter: {syms}")

    pivot = df.pivot_table(index="date", columns="symbol", values="close")
    overlap = pivot.dropna(how="any")
    if not overlap.empty:
        print(f"  Full-universe overlap: "
              f"{overlap.index.min().date()} → {overlap.index.max().date()} "
              f"({len(overlap):,} days)")
    else:
        print("  No single date where ALL symbols have simultaneous data.")

    # Earliest date with N_long + N_short symbols available
    avail_count = pivot.notna().sum(axis=1)
    min_needed  = p["n_long"] + p["n_short"]
    first_tradeable = avail_count[avail_count >= min_needed].index.min()
    print(f"  First date with ≥{min_needed} symbols: {first_tradeable.date()}")

    # ── Pre-compute signals and verify timing ─────────────────────────────
    print(f"\n  Pre-computing weekly signals ...", end=" ", flush=True)
    signals = strategy.compute_weekly_signals(df)
    print(f"{len(signals):,} signals ({signals[0]['signal_date'].date()} "
          f"→ {signals[-1]['signal_date'].date()})")

    # ── Run backtest ──────────────────────────────────────────────────────
    print(f"\n  Running backtest ...", end=" ", flush=True)
    equity_df, trades_df, snapshots_df = run_backtest(df, strategy, INITIAL_CAPITAL)
    print(f"done. {len(equity_df):,} bars | {len(trades_df):,} trades | "
          f"{len(snapshots_df):,} rebalances")

    # ── Metrics ───────────────────────────────────────────────────────────
    metrics   = compute_metrics(equity_df, trades_df, snapshots_df, INITIAL_CAPITAL)
    per_year  = per_year_sharpe(equity_df)
    rs_df     = rolling_6m_sharpe(equity_df)

    # ── Print results ─────────────────────────────────────────────────────
    print_full_results(metrics, per_year, rs_df, signals)

    # ── Save outputs ──────────────────────────────────────────────────────
    print(f"\n{BAR}")
    print("SAVING OUTPUTS")
    print(BAR)
    save_equity_plot(equity_df, os.path.join(OUTPUT_DIR, "momentum_equity_curve.png"))
    save_monthly_heatmap(equity_df, os.path.join(OUTPUT_DIR, "momentum_monthly.png"))
    save_rolling_sharpe_plot(rs_df, os.path.join(OUTPUT_DIR, "momentum_rolling_sharpe.png"))

    if not trades_df.empty:
        tp = os.path.join(OUTPUT_DIR, "momentum_trades.csv")
        trades_df.to_csv(tp, index=False)
        print(f"  Trade log saved      : {tp}  ({len(trades_df):,} rows)")

    if not snapshots_df.empty:
        sp = os.path.join(OUTPUT_DIR, "momentum_snapshots.csv")
        snapshots_df.to_csv(sp, index=False)
        print(f"  Snapshots saved      : {sp}  ({len(snapshots_df):,} rows)")

    print(f"\n{BAR}")
    print("Done.")
    print(BAR)


if __name__ == "__main__":
    main()
