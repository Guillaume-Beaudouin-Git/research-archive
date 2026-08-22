"""
Seykota-style trend-following engine (daily bars, multi-asset, single account).

Rules replicated from the video "I Tested Ed Seykota's Famous Trading Strategy"
(Unbiased Trading):

  1. Trend filter ..... EMA(100) on close. Long bias above, short bias below.
  2. Entry ............ close makes a new 20-day high (long) / low (short),
                        in the direction of the trend filter.
  3. Pyramiding ....... up to 3 add-ons; add one unit each time price moves
                        0.5 x ATR beyond the last fill price.
  4. Exit ............. ATR trailing stop (K x ATR, chandelier on best close),
                        ratcheting, never loosened. Whole position exits.
  5. Sizing ........... fixed fractional: each unit risks RISK_FRAC of current
                        portfolio equity; unit size = risk$ / (K x ATR).

Execution model (no look-ahead):
  - Signals are computed on the close of bar t; market orders fill at the
    open of bar t+1 (per asset calendar).
  - The trailing stop active during bar t+1 is the level computed at the
    close of bar t. Stops are monitored intrabar: a long exits at
    min(open, stop) if low <= stop (gap-through fills at the open, i.e.
    worse than the stop -- conservative).
  - If the stop fires on a bar, any pending pyramid order on that bar is
    cancelled. Position sizing uses portfolio equity marked at the signal
    close (last known equity), never same-bar information.

Costs: proportional per-side rate per asset (spread + slippage), applied to
fill notional.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

DAILY = Path(__file__).resolve().parent / "daily"

# ---------------------------------------------------------------- parameters


@dataclass(frozen=True)
class Params:
    ema_len: int = 100        # trend filter
    breakout: int = 20        # rolling close-high/low window
    atr_len: int = 14         # Wilder ATR
    atr_stop_mult: float = 3.0    # trailing stop distance (K)
    pyramid_step_atr: float = 0.5  # add-on trigger distance
    max_adds: int = 3         # add-ons beyond the initial unit
    risk_frac: float = 0.01   # equity risked per unit
    warmup: int = 100         # bars skipped before signals are allowed
    max_gross: float = float("inf")  # gross exposure cap (1.0 = cash account)
    long_only: bool = False
    trend_filter: bool = True  # False -> pure 20-day breakout, no EMA gate


# per-side proportional cost (spread + slippage), by asset
COSTS = {
    "US500": 0.0002, "US100": 0.0002,
    "XAUUSD": 0.0002, "USOIL": 0.0005,
    "BTC": 0.0010, "ETH": 0.0010,
}

# ---------------------------------------------------------------- indicators


def wilder_atr(df: pd.DataFrame, n: int) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def prepare_asset(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    out = df.copy()
    out["ema"] = out["close"].ewm(span=p.ema_len, adjust=False).mean()
    out["hh"] = out["close"].shift(1).rolling(p.breakout).max()
    out["ll"] = out["close"].shift(1).rolling(p.breakout).min()
    out["atr"] = wilder_atr(out, p.atr_len)
    out["bar_no"] = np.arange(len(out))
    return out


# ---------------------------------------------------------------- containers


@dataclass
class Unit:
    entry_date: pd.Timestamp
    entry_px: float
    size: float            # signed
    equity_at_entry: float
    risk_dollar: float


@dataclass
class AssetState:
    direction: int = 0                 # +1 long, -1 short, 0 flat
    units: list = field(default_factory=list)
    adds_done: int = 0
    best_close: float = np.nan         # highest (long) / lowest (short) close
    stop: float = np.nan               # active trailing stop
    last_fill_px: float = np.nan
    pending: dict | None = None        # order built at previous close


# ---------------------------------------------------------------- simulator


def simulate(
    data: dict[str, pd.DataFrame],
    p: Params = Params(),
    initial_equity: float = 100_000.0,
    costs: dict[str, float] | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """Event-driven daily simulation over a dict of prepared OHLC frames."""
    costs = costs or COSTS
    frames = {}
    for sym, df in data.items():
        d = prepare_asset(df, p)
        if start:
            d = d[d.index >= pd.Timestamp(start)]
        if end:
            d = d[d.index <= pd.Timestamp(end)]
        frames[sym] = d

    calendar = sorted(set().union(*[set(d.index) for d in frames.values()]))
    cols = ["open", "high", "low", "close", "atr", "ema", "hh", "ll", "bar_no"]
    arr = {s: {c: d[c].to_numpy() for c in cols} for s, d in frames.items()}
    idx_map = {s: {ts: i for i, ts in enumerate(d.index)} for s, d in frames.items()}

    cash = initial_equity
    pos = {s: 0.0 for s in frames}          # signed size
    last_close = {s: np.nan for s in frames}
    state = {s: AssetState() for s in frames}
    equity_curve, trades = [], []
    gross_exposure = []
    equity = initial_equity

    def fill_cost(sym, px, size):
        return abs(size) * px * costs[sym]

    for ts in calendar:
        # ---------------- phase 1: stops & pending orders at this bar ------
        for sym in frames:
            i = idx_map[sym].get(ts)
            if i is None:
                continue
            A = arr[sym]
            st = state[sym]
            o, h, l, c = A["open"][i], A["high"][i], A["low"][i], A["close"][i]

            stop_fired = False
            if st.direction != 0 and np.isfinite(st.stop):
                if st.direction > 0 and l <= st.stop:
                    px = min(o, st.stop)
                    stop_fired = True
                elif st.direction < 0 and h >= st.stop:
                    px = max(o, st.stop)
                    stop_fired = True
                if stop_fired:
                    for u in st.units:
                        gross = (px - u.entry_px) * u.size
                        cost = fill_cost(sym, u.entry_px, u.size) + fill_cost(sym, px, u.size)
                        trades.append(dict(
                            symbol=sym, direction=st.direction,
                            entry_date=u.entry_date, entry_px=u.entry_px,
                            exit_date=ts, exit_px=px, size=abs(u.size),
                            pnl_gross=gross, costs=cost, pnl_net=gross - cost,
                            r_multiple=(gross - cost) / u.risk_dollar,
                            holding_days=(ts - u.entry_date).days,
                            exit_reason="trail_stop",
                        ))
                        cash += u.size * px - fill_cost(sym, px, u.size)
                        pos[sym] -= u.size
                    state[sym] = AssetState()          # flat, clears pending
                    st = state[sym]

            # pending market order placed at previous close
            if st.pending is not None and not stop_fired:
                od = st.pending
                st.pending = None
                px = o
                size = od["size"] * (1 if od["dir"] > 0 else -1)
                cash -= size * px + fill_cost(sym, px, size)
                pos[sym] += size
                st.units.append(Unit(ts, px, size, od["equity"], od["risk_dollar"]))
                st.direction = od["dir"]
                st.last_fill_px = px
                if od["kind"] == "add":
                    st.adds_done += 1
                if not np.isfinite(st.best_close):
                    st.best_close = c
            elif st.pending is not None and stop_fired:
                st.pending = None                       # cancelled by stop

        # ---------------- phase 2: close marks, stop ratchet, new signals --
        for sym in frames:
            i = idx_map[sym].get(ts)
            if i is not None:
                last_close[sym] = arr[sym]["close"][i]

        equity = cash + sum(
            pos[s] * last_close[s] for s in frames if np.isfinite(last_close[s])
        )

        for sym in frames:
            i = idx_map[sym].get(ts)
            if i is None:
                continue
            A = arr[sym]
            st = state[sym]
            c, atr, ema, hh, ll = A["close"][i], A["atr"][i], A["ema"][i], A["hh"][i], A["ll"][i]
            if A["bar_no"][i] < p.warmup or not np.isfinite(atr):
                continue

            if st.direction != 0:
                # ratchet trailing stop on best close
                if st.direction > 0:
                    st.best_close = max(st.best_close, c)
                    new_stop = st.best_close - p.atr_stop_mult * atr
                    st.stop = new_stop if not np.isfinite(st.stop) else max(st.stop, new_stop)
                else:
                    st.best_close = min(st.best_close, c)
                    new_stop = st.best_close + p.atr_stop_mult * atr
                    st.stop = new_stop if not np.isfinite(st.stop) else min(st.stop, new_stop)
                # pyramid signal
                if st.adds_done < p.max_adds:
                    trig = (
                        st.direction > 0 and c >= st.last_fill_px + p.pyramid_step_atr * atr
                    ) or (
                        st.direction < 0 and c <= st.last_fill_px - p.pyramid_step_atr * atr
                    )
                    if trig:
                        risk_d = p.risk_frac * equity
                        size = risk_d / (p.atr_stop_mult * atr)
                        cur_gross = sum(
                            abs(pos[s]) * last_close[s]
                            for s in frames if np.isfinite(last_close[s])
                        ) / equity
                        if cur_gross + size * c / equity <= p.max_gross:
                            st.pending = dict(
                                kind="add", dir=st.direction, size=size,
                                equity=equity, risk_dollar=risk_d,
                            )
            else:
                long_sig = (c > ema or not p.trend_filter) and c > hh
                short_sig = (not p.long_only) and (c < ema or not p.trend_filter) and c < ll
                if long_sig or short_sig:
                    d = 1 if long_sig else -1
                    risk_d = p.risk_frac * equity
                    size = risk_d / (p.atr_stop_mult * atr)
                    cur_gross = sum(
                        abs(pos[s]) * last_close[s]
                        for s in frames if np.isfinite(last_close[s])
                    ) / equity
                    if cur_gross + size * c / equity <= p.max_gross:
                        st.pending = dict(
                            kind="entry", dir=d, size=size,
                            equity=equity, risk_dollar=risk_d,
                        )

        gross_exposure.append(
            sum(abs(pos[s]) * last_close[s] for s in frames if np.isfinite(last_close[s]))
            / equity
        )
        equity_curve.append((ts, equity, cash))

    # liquidate residual open positions at the final close (clean accounting)
    final_ts = calendar[-1]
    for sym in frames:
        st = state[sym]
        if st.direction != 0 and np.isfinite(last_close[sym]):
            px = last_close[sym]
            for u in st.units:
                gross = (px - u.entry_px) * u.size
                cost = fill_cost(sym, u.entry_px, u.size) + fill_cost(sym, px, u.size)
                trades.append(dict(
                    symbol=sym, direction=st.direction,
                    entry_date=u.entry_date, entry_px=u.entry_px,
                    exit_date=final_ts, exit_px=px, size=abs(u.size),
                    pnl_gross=gross, costs=cost, pnl_net=gross - cost,
                    r_multiple=(gross - cost) / u.risk_dollar,
                    holding_days=(final_ts - u.entry_date).days,
                    exit_reason="end_of_test",
                ))
                cash += u.size * px - fill_cost(sym, px, u.size)
                pos[sym] -= u.size
    equity_curve[-1] = (final_ts, cash + sum(
        pos[s] * last_close[s] for s in frames if np.isfinite(last_close[s])
    ), cash)

    ec = pd.DataFrame(equity_curve, columns=["date", "equity", "cash"]).set_index("date")
    ec["gross_exposure"] = gross_exposure
    tr = pd.DataFrame(trades)
    if not tr.empty:
        tr = tr.sort_values("exit_date").reset_index(drop=True)
    return {"equity": ec, "trades": tr, "params": p}


def load_universe(symbols: list[str]) -> dict[str, pd.DataFrame]:
    return {s: pd.read_parquet(DAILY / f"{s}.parquet") for s in symbols}
