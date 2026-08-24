"""
Futures trend engine — port of the verified data/seykota_trend/engine.py
(V1-V7 pass) with FUTURES-correct adaptations (PREREG section 6, 11):

  * Costs: per-instrument per-side bp derived from each micro's tick / median
    notional + commission (build_costs), NOT CFD spreads.
  * Roll cost: cross the bid-ask once per roll per contract held — charged on
    `is_roll` days to the open position (NO overnight swap; carry is in the
    back-adjusted series). Kept as a separate equity drag so the accounting
    identity is final = init + Σ trade.pnl_net − total_roll_cost.
  * Integer-micro sizing mode for $100k lumpiness (round desired notional to an
    integer number of micro contracts via the $ multiplier).

The execution semantics are UNCHANGED from the verified engine: signal on close
of bar t, fill at open of t+1; trailing stop active during t+1 is the level set
at the close of t; gap-throughs fill at the open (worse than the stop, L26);
sizing uses equity marked at the signal close (no same-bar info, L1).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DAILY = HERE / "daily"


@dataclass(frozen=True)
class Params:
    ema_len: int = 100
    breakout: int = 20
    atr_len: int = 14
    atr_stop_mult: float = 3.0
    pyramid_step_atr: float = 0.5
    max_adds: int = 3
    risk_frac: float = 0.01
    warmup: int = 100
    max_gross: float = 1.0          # 1.0 = cash account (realistic); inf = literal leverage
    long_only: bool = False
    trend_filter: bool = True
    integer_contracts: bool = False  # True -> round to integer micro contracts ($100k lumpiness)
    long_only_syms: tuple = ()       # per-symbol short disable (H1b conditional shorts)
    short_risk_mult: float = 1.0     # risk multiplier on the short leg (H1d)
    short_only: bool = False         # crypto bear-convexity ablation


# ---------------------------------------------------------------- cost model
def build_costs(specs: dict, daily_dir: Path = DAILY) -> tuple[dict, dict, dict]:
    """Per-side cost bp and roll-cost bp per instrument, from tick/notional.

    per_side_$ = 1 tick slippage (tick*mult) + commission/side
    per_side_bp = per_side_$ / median_notional * 1e4
    roll_bp     = 1 tick / median_price * 1e4   (cross the spread once per roll)
    """
    per_side, roll_bp, mult = {}, {}, {}
    for sym, sp in specs.items():
        f = daily_dir / f"{sym}.parquet"
        if not f.exists():
            continue
        med_px = float(pd.read_parquet(f, columns=["close"])["close"].median())
        tick_val = sp["tick"] * sp["mult"]
        med_notional = med_px * sp["mult"]
        per_side[sym] = (tick_val + sp["comm_side"]) / med_notional      # fraction
        roll_bp[sym] = sp["tick"] / med_px                               # fraction
        mult[sym] = sp["mult"]
    return per_side, roll_bp, mult


def load_specs(daily_dir: Path = DAILY) -> dict:
    return json.loads((daily_dir / "specs.json").read_text())


# ---------------------------------------------------------------- indicators
def wilder_atr(df: pd.DataFrame, n: int) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def prepare_asset(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    out = df.copy()
    out["ema"] = out["close"].ewm(span=p.ema_len, adjust=False).mean()
    out["hh"] = out["close"].shift(1).rolling(p.breakout).max()
    out["ll"] = out["close"].shift(1).rolling(p.breakout).min()
    out["atr"] = wilder_atr(out, p.atr_len)
    out["bar_no"] = np.arange(len(out))
    if "is_roll" not in out.columns:
        out["is_roll"] = False
    return out


@dataclass
class Unit:
    entry_date: pd.Timestamp
    entry_px: float
    size: float
    equity_at_entry: float
    risk_dollar: float


@dataclass
class AssetState:
    direction: int = 0
    units: list = field(default_factory=list)
    adds_done: int = 0
    best_close: float = np.nan
    stop: float = np.nan
    last_fill_px: float = np.nan
    pending: dict | None = None


# ---------------------------------------------------------------- simulator
def simulate(data: dict[str, pd.DataFrame], p: Params, initial_equity: float,
             costs: dict, roll_bp: dict | None = None, multipliers: dict | None = None,
             start: str | None = None, end: str | None = None) -> dict:
    roll_bp = roll_bp or {}
    multipliers = multipliers or {}
    frames = {}
    for sym, df in data.items():
        d = prepare_asset(df, p)
        if start:
            d = d[d.index >= pd.Timestamp(start)]
        if end:
            d = d[d.index <= pd.Timestamp(end)]
        frames[sym] = d

    calendar = sorted(set().union(*[set(d.index) for d in frames.values()]))
    cols = ["open", "high", "low", "close", "atr", "ema", "hh", "ll", "bar_no", "is_roll"]
    arr = {s: {c: d[c].to_numpy() for c in cols} for s, d in frames.items()}
    idx_map = {s: {ts: i for i, ts in enumerate(d.index)} for s, d in frames.items()}

    cash = initial_equity
    pos = {s: 0.0 for s in frames}
    last_close = {s: np.nan for s in frames}
    state = {s: AssetState() for s in frames}
    equity_curve, trades, gross_exposure, position_rows = [], [], [], []
    total_roll_cost = 0.0
    equity = initial_equity

    def fill_cost(sym, px, size):
        return abs(size) * px * costs[sym]

    def to_contracts(size, sym):
        """Round desired index-unit size to an integer number of micro contracts."""
        if not p.integer_contracts or sym not in multipliers:
            return size
        m = multipliers[sym]
        n = round(size / m)
        return n * m

    for ts in calendar:
        # --------- phase 1: stops & pending fills ---------
        for sym in frames:
            i = idx_map[sym].get(ts)
            if i is None:
                continue
            A = arr[sym]; st = state[sym]
            o, h, l, c = A["open"][i], A["high"][i], A["low"][i], A["close"][i]
            stop_fired = False
            if st.direction != 0 and np.isfinite(st.stop):
                if st.direction > 0 and l <= st.stop:
                    px = min(o, st.stop); stop_fired = True
                elif st.direction < 0 and h >= st.stop:
                    px = max(o, st.stop); stop_fired = True
                if stop_fired:
                    for u in st.units:
                        gross = (px - u.entry_px) * u.size
                        cost = fill_cost(sym, u.entry_px, u.size) + fill_cost(sym, px, u.size)
                        trades.append(dict(symbol=sym, direction=st.direction, entry_date=u.entry_date,
                                           entry_px=u.entry_px, exit_date=ts, exit_px=px, size=abs(u.size),
                                           pnl_gross=gross, costs=cost, pnl_net=gross - cost,
                                           r_multiple=(gross - cost) / u.risk_dollar,
                                           holding_days=(ts - u.entry_date).days, exit_reason="trail_stop"))
                        cash += u.size * px - fill_cost(sym, px, u.size)
                        pos[sym] -= u.size
                    state[sym] = AssetState(); st = state[sym]
            if st.pending is not None and not stop_fired:
                od = st.pending; st.pending = None
                px = o; size = od["size"] * (1 if od["dir"] > 0 else -1)
                cash -= size * px + fill_cost(sym, px, size); pos[sym] += size
                st.units.append(Unit(ts, px, size, od["equity"], od["risk_dollar"]))
                st.direction = od["dir"]; st.last_fill_px = px
                if od["kind"] == "add":
                    st.adds_done += 1
                if not np.isfinite(st.best_close):
                    st.best_close = c
            elif st.pending is not None and stop_fired:
                st.pending = None

        # --------- phase 1b: roll cost on held positions ---------
        for sym in frames:
            i = idx_map[sym].get(ts)
            if i is None or pos[sym] == 0.0 or not arr[sym]["is_roll"][i]:
                continue
            rc = roll_bp.get(sym, 0.0) * abs(pos[sym]) * arr[sym]["close"][i]
            cash -= rc; total_roll_cost += rc

        # --------- phase 2: marks, ratchet, signals ---------
        for sym in frames:
            i = idx_map[sym].get(ts)
            if i is not None:
                last_close[sym] = arr[sym]["close"][i]
        equity = cash + sum(pos[s] * last_close[s] for s in frames if np.isfinite(last_close[s]))

        for sym in frames:
            i = idx_map[sym].get(ts)
            if i is None:
                continue
            A = arr[sym]; st = state[sym]
            c, atr, ema, hh, ll = A["close"][i], A["atr"][i], A["ema"][i], A["hh"][i], A["ll"][i]
            if A["bar_no"][i] < p.warmup or not np.isfinite(atr):
                continue
            if st.direction != 0:
                if st.direction > 0:
                    st.best_close = max(st.best_close, c)
                    new_stop = st.best_close - p.atr_stop_mult * atr
                    st.stop = new_stop if not np.isfinite(st.stop) else max(st.stop, new_stop)
                else:
                    st.best_close = min(st.best_close, c)
                    new_stop = st.best_close + p.atr_stop_mult * atr
                    st.stop = new_stop if not np.isfinite(st.stop) else min(st.stop, new_stop)
                if st.adds_done < p.max_adds:
                    trig = (st.direction > 0 and c >= st.last_fill_px + p.pyramid_step_atr * atr) or \
                           (st.direction < 0 and c <= st.last_fill_px - p.pyramid_step_atr * atr)
                    if trig:
                        rm = p.short_risk_mult if st.direction < 0 else 1.0
                        risk_d = p.risk_frac * equity * rm
                        size = to_contracts(risk_d / (p.atr_stop_mult * atr), sym)
                        if size > 0:
                            cur_gross = sum(abs(pos[s]) * last_close[s] for s in frames if np.isfinite(last_close[s])) / equity
                            if cur_gross + size * c / equity <= p.max_gross:
                                st.pending = dict(kind="add", dir=st.direction, size=size, equity=equity, risk_dollar=risk_d)
            else:
                long_sig = (not p.short_only) and (c > ema or not p.trend_filter) and c > hh
                short_sig = ((not p.long_only) and (sym not in p.long_only_syms)
                             and (c < ema or not p.trend_filter) and c < ll)
                if long_sig or short_sig:
                    d = 1 if long_sig else -1
                    rm = p.short_risk_mult if d < 0 else 1.0
                    risk_d = p.risk_frac * equity * rm
                    size = to_contracts(risk_d / (p.atr_stop_mult * atr), sym)
                    if size > 0:
                        cur_gross = sum(abs(pos[s]) * last_close[s] for s in frames if np.isfinite(last_close[s])) / equity
                        if cur_gross + size * c / equity <= p.max_gross:
                            st.pending = dict(kind="entry", dir=d, size=size, equity=equity, risk_dollar=risk_d)

        gross_exposure.append(sum(abs(pos[s]) * last_close[s] for s in frames if np.isfinite(last_close[s])) / equity)
        equity_curve.append((ts, equity, cash))
        position_rows.append({s: (pos[s] * last_close[s] if np.isfinite(last_close[s]) else 0.0) for s in frames})

    # liquidate residual positions at final close
    final_ts = calendar[-1]
    for sym in frames:
        st = state[sym]
        if st.direction != 0 and np.isfinite(last_close[sym]):
            px = last_close[sym]
            for u in st.units:
                gross = (px - u.entry_px) * u.size
                cost = fill_cost(sym, u.entry_px, u.size) + fill_cost(sym, px, u.size)
                trades.append(dict(symbol=sym, direction=st.direction, entry_date=u.entry_date,
                                   entry_px=u.entry_px, exit_date=final_ts, exit_px=px, size=abs(u.size),
                                   pnl_gross=gross, costs=cost, pnl_net=gross - cost,
                                   r_multiple=(gross - cost) / u.risk_dollar,
                                   holding_days=(final_ts - u.entry_date).days, exit_reason="end_of_test"))
                cash += u.size * px - fill_cost(sym, px, u.size); pos[sym] -= u.size
    equity_curve[-1] = (final_ts, cash + sum(pos[s] * last_close[s] for s in frames if np.isfinite(last_close[s])), cash)

    ec = pd.DataFrame(equity_curve, columns=["date", "equity", "cash"]).set_index("date")
    ec["gross_exposure"] = gross_exposure
    positions = pd.DataFrame(position_rows, index=ec.index)
    tr = pd.DataFrame(trades)
    if not tr.empty:
        tr = tr.sort_values("exit_date").reset_index(drop=True)
    return {"equity": ec, "trades": tr, "params": p, "total_roll_cost": total_roll_cost, "positions": positions}


def load_universe(symbols: list[str]) -> dict[str, pd.DataFrame]:
    return {s: pd.read_parquet(DAILY / f"{s}.parquet") for s in symbols}
