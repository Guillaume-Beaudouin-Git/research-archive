"""Faithful copy of top10_test/batch_strategies.py with the 6 defect switches.

Every handler is line-for-line the funnel's logic; only three things are hooked:
  * which CLOCK the bar index carries          (defect 2)
  * which cost table is charged                (defects 3, 6)
  * which swap table is charged, side-aware    (defect 5)
Nothing in top10_test/ is modified — this file is a COPY (pre-registration §3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from costs import rt_cost, swap_night
from data_layer import get_m1, get_daily, get_events

M1_INSTRUMENTS = {"US500", "US100", "US30", "GER40", "AUDJPY", "AUDUSD", "EURGBP",
                  "EURJPY", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF",
                  "USDJPY", "XAUUSD", "BTCUSD"}


@dataclass
class Cfg:
    clock: str = "eet"          # 'eet' (funnel) | 'utc' (defect 2 repaired)
    costs: bool = False         # defect 3
    swaps: bool = False         # defect 5
    typed_order: bool = False   # defect 6
    p95_cost: bool = False


def trades_to_daily_pnl(trades: pd.DataFrame, all_dates: pd.DatetimeIndex) -> pd.Series:
    if trades.empty:
        return pd.Series(0.0, index=all_dates)
    t = trades.copy()
    ed = pd.to_datetime(t["exit_date"])
    if hasattr(ed.dt, "tz") and ed.dt.tz is not None:
        ed = ed.dt.tz_localize(None)
    t["exit_date"] = ed.dt.normalize()
    pnl_by_date = t.groupby("exit_date")["net_bps"].sum() / 10000.0
    base_idx = pd.DatetimeIndex(all_dates)
    if base_idx.tz is not None:
        base_idx = base_idx.tz_localize(None)
    full_idx = pnl_by_date.index.union(base_idx).sort_values()
    out = pd.Series(0.0, index=full_idx)
    out.loc[pnl_by_date.index] = pnl_by_date.values
    return out


@dataclass
class StratSpec:
    id: str
    name: str
    family: str
    asset_class: str
    order_type: str = "scheduled_market"
    params: dict = field(default_factory=dict)


def _intraday(instrument: str, cfg: Cfg) -> pd.DataFrame:
    return get_m1(instrument, cfg.clock)


def _bar_at_time_or_close(intraday_df, event_dt, max_lag_hours: float = 4):
    """Identical semantics to framework's version; searchsorted instead of a
    full boolean mask (same result, ~1000x faster on a 2.7M-row index)."""
    if intraday_df is None or len(intraday_df) == 0:
        return None
    i = intraday_df.index.searchsorted(event_dt, side="left")
    if i >= len(intraday_df):
        return None
    if (intraday_df.index[i] - event_dt) > pd.Timedelta(hours=max_lag_hours):
        return None
    return float(intraday_df["open"].iat[i])


# ---------------------------------------------------------------- families ---

def family_event_drift(params, cfg: Cfg):
    et, inst = params["event_type"], params["instrument"]
    side, cls = params["side"], params["asset_class"]
    events = get_events(et)
    if events.empty:
        return pd.DataFrame()
    daily = get_daily(inst, cfg.clock)
    if daily.empty:
        return pd.DataFrame()
    intraday = _intraday(inst, cfg)
    cost = rt_cost(cls, cfg.costs, "scheduled_market", cfg.typed_order, cfg.p95_cost)
    sw = swap_night(cls, inst, side, cfg.swaps)
    trades = []
    for _, ev in events.iterrows():
        ev_date = ev["date"]
        prev = daily.index[daily.index < ev_date]
        if len(prev) == 0:
            continue
        entry_px = daily.loc[prev[-1], "close"]
        ts = ev["time_utc"] if pd.notna(ev["time_utc"]) else "13:30"
        try:
            hh, mm = ts.split(":")
        except (ValueError, AttributeError):
            hh, mm = "13", "30"
        rel = pd.Timestamp(ev_date) + pd.Timedelta(hours=int(hh), minutes=int(mm))
        exit_px = _bar_at_time_or_close(intraday, rel)
        if exit_px is None or pd.isna(entry_px) or entry_px <= 0:
            continue
        g = side * (exit_px - entry_px) / entry_px * 10000.0
        trades.append({"exit_date": pd.Timestamp(ev_date), "asset": inst, "side": side,
                       "gross_bps": g, "cost_bps": cost, "swap_bps": sw,
                       "net_bps": g - cost + sw, "n_nights": 1})
    return pd.DataFrame(trades)


def family_post_event_rev(params, cfg: Cfg):
    et, inst = params["event_type"], params["instrument"]
    hold = params.get("hold_hours", 2)
    cls = params["asset_class"]
    events = get_events(et)
    if events.empty:
        return pd.DataFrame()
    intraday = _intraday(inst, cfg)
    if intraday.empty:
        return pd.DataFrame()
    cost = rt_cost(cls, cfg.costs, "scheduled_market", cfg.typed_order, cfg.p95_cost)
    trades = []
    for _, ev in events.iterrows():
        ev_date = ev["date"]
        ts = ev["time_utc"] if pd.notna(ev["time_utc"]) else "13:30"
        try:
            hh, mm = ts.split(":")
        except (ValueError, AttributeError):
            hh, mm = "13", "30"
        rel = pd.Timestamp(ev_date) + pd.Timedelta(hours=int(hh), minutes=int(mm))
        entry_px = _bar_at_time_or_close(intraday, rel + pd.Timedelta(minutes=1))
        peek_px = _bar_at_time_or_close(intraday, rel + pd.Timedelta(minutes=15))
        exit_px = _bar_at_time_or_close(intraday, rel + pd.Timedelta(hours=hold))
        if any(x is None or pd.isna(x) for x in [entry_px, peek_px, exit_px]):
            continue
        direction = np.sign(peek_px - entry_px)
        if direction == 0:
            continue
        side = -int(direction)
        g = side * (exit_px - peek_px) / peek_px * 10000.0
        trades.append({"exit_date": pd.Timestamp(ev_date), "asset": inst, "side": side,
                       "gross_bps": g, "cost_bps": cost, "swap_bps": 0.0,
                       "net_bps": g - cost, "n_nights": 0})
    return pd.DataFrame(trades)


def family_intraday_mom(params, cfg: Cfg):
    inst = params["instrument"]
    ss, se, te = params["sig_start"], params["sig_end"], params["trade_end"]
    thr, sd, cls = params["threshold"], params["side_dir"], params["asset_class"]
    df = _intraday(inst, cfg)
    if df.empty:
        return pd.DataFrame()
    cost = rt_cost(cls, cfg.costs, "scheduled_market", cfg.typed_order, cfg.p95_cost)
    h, m = df.index.hour, df.index.minute

    def _per_date_open(mask):
        sub = df[mask]
        if sub.empty:
            return pd.Series(dtype=float)
        return sub.groupby(sub.index.normalize())["open"].first()

    a = _per_date_open((h == ss[0]) & (m == ss[1]))
    b = _per_date_open((h == se[0]) & (m == se[1]))
    c = _per_date_open((h == te[0]) & (m == te[1]))
    trades = []
    for date in a.index:
        e1, en, ex = a.get(date), b.get(date), c.get(date)
        if any(pd.isna(x) for x in [e1, en, ex]):
            continue
        mom = (en - e1) / e1
        if abs(mom) < thr:
            continue
        sgn = int(np.sign(mom))
        side = sgn if sd == "mom" else -sgn
        g = side * (ex - en) / en * 10000.0
        trades.append({"exit_date": date, "asset": inst, "side": side,
                       "gross_bps": g, "cost_bps": cost, "swap_bps": 0.0,
                       "net_bps": g - cost, "n_nights": 0})
    return pd.DataFrame(trades)


def family_pair_mr(params, cfg: Cfg):
    a, b = params["asset_a"], params["asset_b"]
    lr, lz = params["lookback_ret"], params["lookback_z"]
    zt, hold = params["z_threshold"], params["holding_days"]
    ca, cb = params["asset_class_a"], params["asset_class_b"]
    da, db = get_daily(a, cfg.clock), get_daily(b, cfg.clock)
    if da.empty or db.empty:
        return pd.DataFrame()
    common = da.index.intersection(db.index)
    if len(common) < lz + 30:
        return pd.DataFrame()
    da, db = da.loc[common], db.loc[common]
    ra = da["close"] / da["close"].shift(lr) - 1.0
    rb = db["close"] / db["close"].shift(lr) - 1.0
    div = ra - rb
    z = ((div - div.rolling(lz, min_periods=20).mean())
         / div.rolling(lz, min_periods=20).std()).shift(1)
    cost = (rt_cost(ca, cfg.costs, "scheduled_market", cfg.typed_order, cfg.p95_cost)
            + rt_cost(cb, cfg.costs, "scheduled_market", cfg.typed_order, cfg.p95_cost))
    trades = []
    for i, date in enumerate(common):
        zi = z.get(date)
        if pd.isna(zi) or abs(zi) < zt:
            continue
        if i + hold >= len(common):
            break
        ex_date = common[i + hold]
        a_side = -1 if zi > 0 else 1
        b_side = +1 if zi > 0 else -1
        ae, ax = da.loc[date, "open"], da.loc[ex_date, "close"]
        be, bx = db.loc[date, "open"], db.loc[ex_date, "close"]
        g = (a_side * (ax - ae) / ae * 10000.0 + b_side * (bx - be) / be * 10000.0) / 2.0
        sw = hold * (swap_night(ca, a, a_side, cfg.swaps)
                     + swap_night(cb, b, b_side, cfg.swaps))
        trades.append({"exit_date": ex_date, "asset": f"{a}-{b}", "side": a_side,
                       "gross_bps": g, "cost_bps": cost, "swap_bps": sw,
                       "net_bps": g - cost + sw, "n_nights": hold * 2})
    return pd.DataFrame(trades)


def family_gap_variant(params, cfg: Cfg):
    inst, thr_s = params["instrument"], params["gap_threshold_sigma"]
    sd, em, cls = params["side_dir"], params["exit_mode"], params["asset_class"]
    d = get_daily(inst, cfg.clock)
    if d.empty:
        return pd.DataFrame()
    d = d.copy()
    d["close_prev"] = d["close"].shift(1)
    d["gap"] = (d["open"] - d["close_prev"]) / d["close_prev"]
    d["abs_gap_std30"] = d["gap"].abs().rolling(30, min_periods=10).std()
    otype = "resting_stop" if em == "fill" else "scheduled_market"
    cost = rt_cost(cls, cfg.costs, otype, cfg.typed_order, cfg.p95_cost)
    trades = []
    for date, row in d.iterrows():
        if pd.isna(row["close_prev"]) or pd.isna(row["abs_gap_std30"]):
            continue
        if abs(row["gap"]) < thr_s * row["abs_gap_std30"]:
            continue
        sg = 1 if row["gap"] > 0 else -1
        side = sg if sd == "cont" else -sg
        entry = row["open"]
        if em == "fill":
            target = row["close_prev"]
            if side == -1:
                th, stop = row["low"] <= target, entry + abs(row["gap"]) * entry
                sh = row["high"] >= stop
            else:
                th, stop = row["high"] >= target, entry - abs(row["gap"]) * entry
                sh = row["low"] <= stop
            exit_px = stop if (th and sh) else (target if th else (stop if sh else row["close"]))
        else:
            exit_px = row["close"]
        g = side * (exit_px - entry) / entry * 10000.0
        trades.append({"exit_date": date, "asset": inst, "side": side,
                       "gross_bps": g, "cost_bps": cost, "swap_bps": 0.0,
                       "net_bps": g - cost, "n_nights": 0})
    return pd.DataFrame(trades)


def family_calendar(params, cfg: Cfg):
    inst, kind = params["instrument"], params["kind"]
    side, cls = params["side"], params["asset_class"]
    d = get_daily(inst, cfg.clock)
    if d.empty:
        return pd.DataFrame()
    d = d.copy()
    dom, dow = d.index.day, d.index.dayofweek
    if kind == "tom":
        act = (dom >= 27) | (dom <= 3)
    elif kind == "eom":
        act = dom >= 28
    elif kind == "dow_mon":
        act = dow == 0
    elif kind == "dow_fri":
        act = dow == 4
    elif kind == "dow_tue":
        act = dow == 1
    else:
        return pd.DataFrame()
    d["next_close"] = d["close"].shift(-1)
    cost = rt_cost(cls, cfg.costs, "scheduled_market", cfg.typed_order, cfg.p95_cost)
    sw = swap_night(cls, inst, side, cfg.swaps)
    trades = []
    for date, row in d[act].iterrows():
        if pd.isna(row["next_close"]):
            continue
        g = side * (row["next_close"] - row["open"]) / row["open"] * 10000.0
        try:
            idx = d.index.get_loc(date)
            if idx + 1 >= len(d):
                continue
            ex_date = d.index[idx + 1]
        except (KeyError, IndexError):
            continue
        trades.append({"exit_date": ex_date, "asset": inst, "side": side,
                       "gross_bps": g, "cost_bps": cost, "swap_bps": sw,
                       "net_bps": g - cost + sw, "n_nights": 1})
    return pd.DataFrame(trades)


def family_multi_event(params, cfg: Cfg):
    types, inst = params["event_types"], params["instrument"]
    side, cls = params["side"], params["asset_class"]
    evs = [get_events(t) for t in types]
    evs = [e for e in evs if not e.empty]
    if not evs:
        return pd.DataFrame()
    events = pd.concat(evs).drop_duplicates(subset=["date"]).sort_values("date")
    daily = get_daily(inst, cfg.clock)
    if daily.empty:
        return pd.DataFrame()
    intraday = _intraday(inst, cfg)
    cost = rt_cost(cls, cfg.costs, "scheduled_market", cfg.typed_order, cfg.p95_cost)
    sw = swap_night(cls, inst, side, cfg.swaps)
    trades = []
    for _, ev in events.iterrows():
        ev_date = ev["date"]
        prev = daily.index[daily.index < ev_date]
        if len(prev) == 0:
            continue
        entry_px = daily.loc[prev[-1], "close"]
        ts = ev["time_utc"] if pd.notna(ev["time_utc"]) else "13:30"
        try:
            hh, mm = ts.split(":")
        except (ValueError, AttributeError):
            hh, mm = "13", "30"
        rel = pd.Timestamp(ev_date) + pd.Timedelta(hours=int(hh), minutes=int(mm))
        exit_px = _bar_at_time_or_close(intraday, rel)
        if exit_px is None or pd.isna(entry_px) or entry_px <= 0:
            continue
        g = side * (exit_px - entry_px) / entry_px * 10000.0
        trades.append({"exit_date": pd.Timestamp(ev_date), "asset": inst, "side": side,
                       "gross_bps": g, "cost_bps": cost, "swap_bps": sw,
                       "net_bps": g - cost + sw, "n_nights": 1})
    return pd.DataFrame(trades)


FAMILY_HANDLERS = {
    "event_drift": family_event_drift,
    "post_event_rev": family_post_event_rev,
    "intraday_mom": family_intraday_mom,
    "pair_mr": family_pair_mr,
    "gap_variant": family_gap_variant,
    "calendar": family_calendar,
    "multi_event": family_multi_event,
}


def build_specs():
    specs = []
    event_inst_map = [
        ("FOMC", "US500", "Index_CFD_major", 1), ("FOMC", "US100", "Index_CFD_major", 1),
        ("FOMC", "US30", "Index_CFD_major", 1), ("FOMC", "EURUSD", "FX_major", 1),
        ("FOMC", "USDJPY", "FX_major", -1), ("FOMC", "XAUUSD", "Metals_CFD_gold", 1),
        ("FOMC", "GBPUSD", "FX_major", 1), ("FOMC", "GER40", "Index_CFD_major", 1),
        ("NFP_US", "US500", "Index_CFD_major", 1), ("NFP_US", "EURUSD", "FX_major", -1),
        ("NFP_US", "USDJPY", "FX_major", 1), ("NFP_US", "GBPUSD", "FX_major", -1),
        ("NFP_US", "XAUUSD", "Metals_CFD_gold", -1),
        ("CPI_US", "US500", "Index_CFD_major", 1), ("CPI_US", "EURUSD", "FX_major", 1),
        ("CPI_US", "USDJPY", "FX_major", -1), ("CPI_US", "XAUUSD", "Metals_CFD_gold", 1),
        ("ECB_RATE", "EURUSD", "FX_major", 1), ("ECB_RATE", "EURGBP", "FX_cross", 1),
        ("ECB_RATE", "EURJPY", "FX_cross", 1), ("BOE_RATE", "GBPUSD", "FX_major", 1),
        ("BOE_RATE", "EURGBP", "FX_cross", -1), ("BOJ_RATE", "USDJPY", "FX_major", 1),
        ("BOJ_RATE", "EURJPY", "FX_cross", 1),
    ]
    for et, inst, cls, sl in event_inst_map:
        for tag, s in (("LO", sl), ("SS", -sl)):
            specs.append(StratSpec(id=f"ed_{et.lower()}_{inst}_{tag}",
                                   name=f"Pre-{et} {inst} {tag}", family="event_drift",
                                   asset_class=cls,
                                   params=dict(event_type=et, instrument=inst, side=s,
                                               asset_class=cls)))
    post_event_set = [
        ("FOMC", "US500", "Index_CFD_major"), ("FOMC", "EURUSD", "FX_major"),
        ("FOMC", "USDJPY", "FX_major"), ("FOMC", "XAUUSD", "Metals_CFD_gold"),
        ("NFP_US", "EURUSD", "FX_major"), ("NFP_US", "USDJPY", "FX_major"),
        ("NFP_US", "US500", "Index_CFD_major"), ("CPI_US", "US500", "Index_CFD_major"),
        ("CPI_US", "EURUSD", "FX_major"), ("ECB_RATE", "EURUSD", "FX_major"),
        ("BOE_RATE", "GBPUSD", "FX_major"), ("BOJ_RATE", "USDJPY", "FX_major"),
    ]
    for et, inst, cls in post_event_set:
        for hh in [1, 2, 4]:
            specs.append(StratSpec(id=f"per_{et.lower()}_{inst}_{hh}h",
                                   name=f"Post-{et} {inst} fade {hh}h",
                                   family="post_event_rev", asset_class=cls,
                                   params=dict(event_type=et, instrument=inst,
                                               hold_hours=hh, asset_class=cls)))
    intraday_set = [
        ("US500", (14, 30), (15, 30), (16, 30), 0.003, "mom", "Index_CFD_major"),
        ("US500", (14, 30), (15, 30), (16, 30), 0.003, "fade", "Index_CFD_major"),
        ("US500", (15, 0), (16, 30), (18, 0), 0.003, "mom", "Index_CFD_major"),
        ("US500", (15, 0), (16, 30), (18, 0), 0.003, "fade", "Index_CFD_major"),
        ("US500", (16, 30), (18, 0), (19, 30), 0.003, "fade", "Index_CFD_major"),
        ("US100", (14, 30), (15, 30), (16, 30), 0.004, "mom", "Index_CFD_major"),
        ("US100", (14, 30), (15, 30), (16, 30), 0.004, "fade", "Index_CFD_major"),
        ("US100", (15, 0), (16, 30), (18, 0), 0.004, "mom", "Index_CFD_major"),
        ("US100", (15, 0), (16, 30), (18, 0), 0.004, "fade", "Index_CFD_major"),
        ("GER40", (14, 30), (15, 30), (16, 30), 0.005, "mom", "Index_CFD_major"),
        ("GER40", (14, 30), (15, 30), (16, 30), 0.005, "fade", "Index_CFD_major"),
        ("EURUSD", (13, 0), (14, 0), (15, 0), 0.002, "mom", "FX_major"),
        ("EURUSD", (13, 0), (14, 0), (15, 0), 0.002, "fade", "FX_major"),
        ("USDJPY", (1, 0), (2, 0), (3, 0), 0.002, "mom", "FX_major"),
        ("XAUUSD", (14, 30), (15, 30), (16, 30), 0.003, "mom", "Metals_CFD_gold"),
        ("XAUUSD", (14, 30), (15, 30), (16, 30), 0.003, "fade", "Metals_CFD_gold"),
    ]
    for asset, ss, se, te, thr, sd, cls in intraday_set:
        specs.append(StratSpec(
            id=f"im_{asset}_{ss[0]:02d}{ss[1]:02d}_{se[0]:02d}{se[1]:02d}_{sd}",
            name=f"{asset} intraday {sd} {ss[0]:02d}:{ss[1]:02d}-{se[0]:02d}:{se[1]:02d}",
            family="intraday_mom", asset_class=cls,
            params=dict(instrument=asset, sig_start=ss, sig_end=se, trade_end=te,
                        threshold=thr, side_dir=sd, asset_class=cls)))
    pair_set = [
        ("US100", "US500", 5, 60, 1.5, 3, "Index_CFD_major", "Index_CFD_major"),
        ("US500", "GER40", 5, 60, 1.5, 3, "Index_CFD_major", "Index_CFD_major"),
        ("US100", "GER40", 5, 60, 1.5, 3, "Index_CFD_major", "Index_CFD_major"),
        ("EURUSD", "USDJPY", 5, 60, 1.5, 3, "FX_major", "FX_major"),
        ("EURUSD", "GBPUSD", 5, 60, 2.0, 3, "FX_major", "FX_major"),
        ("GBPUSD", "USDJPY", 5, 60, 1.5, 3, "FX_major", "FX_major"),
        ("AUDUSD", "NZDUSD", 5, 60, 1.5, 3, "FX_major", "FX_major"),
        ("USDCAD", "USDCHF", 5, 60, 1.5, 3, "FX_major", "FX_major"),
        ("XAUUSD", "XAGUSD", 5, 60, 1.5, 5, "Metals_CFD_gold", "Metals_CFD_gold"),
        ("USOIL", "UKOIL", 3, 60, 1.5, 3, "Commodity_CFD", "Commodity_CFD"),
        ("EURJPY", "GBPJPY", 5, 60, 1.5, 3, "FX_cross", "FX_cross"),
        ("EURUSD", "EURGBP", 5, 60, 1.5, 3, "FX_major", "FX_cross"),
    ]
    for a, b, lr, lz, zt, hd, ca, cb in pair_set:
        specs.append(StratSpec(id=f"pr_{a}_{b}_z{zt}_h{hd}",
                               name=f"Pair MR {a}-{b} z>{zt} hold={hd}d",
                               family="pair_mr", asset_class=ca,
                               params=dict(asset_a=a, asset_b=b, lookback_ret=lr,
                                           lookback_z=lz, z_threshold=zt,
                                           holding_days=hd, asset_class_a=ca,
                                           asset_class_b=cb)))
    gap_set = [
        ("US500", 1.5, "fade", "close", "Index_CFD_major"),
        ("US500", 1.5, "cont", "close", "Index_CFD_major"),
        ("US500", 2.0, "fade", "close", "Index_CFD_major"),
        ("US500", 2.0, "cont", "close", "Index_CFD_major"),
        ("US100", 1.5, "fade", "close", "Index_CFD_major"),
        ("US100", 1.5, "cont", "close", "Index_CFD_major"),
        ("US100", 2.0, "cont", "close", "Index_CFD_major"),
        ("GER40", 1.5, "cont", "close", "Index_CFD_major"),
        ("GER40", 2.0, "cont", "close", "Index_CFD_major"),
        ("XAUUSD", 1.5, "cont", "close", "Metals_CFD_gold"),
        ("XAUUSD", 1.5, "fade", "close", "Metals_CFD_gold"),
        ("USDJPY", 1.5, "cont", "close", "FX_major"),
    ]
    for inst, thr, sd, em, cls in gap_set:
        specs.append(StratSpec(id=f"gv_{inst}_t{thr}_{sd}", name=f"Gap {sd} {inst} {thr}s",
                               family="gap_variant", asset_class=cls,
                               order_type=("resting_stop" if em == "fill" else "scheduled_market"),
                               params=dict(instrument=inst, gap_threshold_sigma=thr,
                                           side_dir=sd, exit_mode=em, asset_class=cls)))
    cal_set = [
        ("US500", "tom", 1, "Index_CFD_major"), ("US500", "eom", 1, "Index_CFD_major"),
        ("US500", "dow_mon", -1, "Index_CFD_major"), ("US500", "dow_fri", 1, "Index_CFD_major"),
        ("US500", "dow_tue", 1, "Index_CFD_major"), ("EURUSD", "eom", -1, "FX_major"),
        ("EURUSD", "tom", 1, "FX_major"), ("XAUUSD", "tom", 1, "Metals_CFD_gold"),
        ("US100", "tom", 1, "Index_CFD_major"), ("GER40", "tom", 1, "Index_CFD_major"),
    ]
    for inst, kind, side, cls in cal_set:
        specs.append(StratSpec(id=f"cal_{inst}_{kind}_{side:+d}",
                               name=f"Calendar {kind} {inst} side={side}",
                               family="calendar", asset_class=cls,
                               params=dict(instrument=inst, kind=kind, side=side,
                                           asset_class=cls)))
    multi_set = [
        (["FOMC", "NFP_US", "CPI_US"], "US500", 1, "Index_CFD_major"),
        (["FOMC", "NFP_US", "CPI_US"], "US100", 1, "Index_CFD_major"),
        (["FOMC", "NFP_US", "CPI_US"], "XAUUSD", 1, "Metals_CFD_gold"),
        (["FOMC", "NFP_US", "CPI_US"], "EURUSD", 1, "FX_major"),
        (["FOMC", "NFP_US", "CPI_US"], "EURUSD", -1, "FX_major"),
        (["FOMC", "ECB_RATE"], "EURUSD", 1, "FX_major"),
        (["FOMC", "BOE_RATE"], "GBPUSD", 1, "FX_major"),
        (["FOMC", "BOJ_RATE"], "USDJPY", 1, "FX_major"),
    ]
    for ets, inst, side, cls in multi_set:
        tag = "_".join(e.replace("_US", "").replace("_RATE", "")[:3].lower() for e in ets)
        specs.append(StratSpec(id=f"me_{tag}_{inst}_{side:+d}",
                               name=f"Multi-event {'+'.join(ets)} {inst} side={side}",
                               family="multi_event", asset_class=cls,
                               params=dict(event_types=ets, instrument=inst, side=side,
                                           asset_class=cls)))
    return specs
