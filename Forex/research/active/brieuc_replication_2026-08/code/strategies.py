"""
strategies.py — générateurs de trades pour les 5 EA (naïf + corrigé), tel que
spécifié dans SPECS.md. Chaque fonction retourne une liste de dicts prêts à
devenir des lignes `resultats.csv` après agrégation dans run_all.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import lib

PIP = lambda instr, version: lib.POINT_TABLE[instr][f"pip_{version}"]


def _sl_dist(instr, version, pips):
    return pips * PIP(instr, version)


# ---------------------------------------------------------------------------
# 1. LondonBreakout
# ---------------------------------------------------------------------------
def london_breakout(instr, version, m1, start, end, sl_pips=20, tp_pips=40):
    h1 = lib.resample_ohlc(m1, "1h")
    sl_d = _sl_dist(instr, version, sl_pips)
    tp_d = _sl_dist(instr, version, tp_pips)
    trades = []
    dates = pd.date_range(start, end, freq="D", tz="UTC")
    for d in dates:
        if d.weekday() >= 5:
            continue
        if version == "corrected":
            t_open = pd.Timestamp(d.year, d.month, d.day, 8, 0, tz=lib.LONDON_TZ).tz_convert("UTC")
            t_close = pd.Timestamp(d.year, d.month, d.day, 16, 30, tz=lib.LONDON_TZ).tz_convert("UTC")
        else:
            t_open = pd.Timestamp(d.year, d.month, d.day, 9, 0, tz="UTC")
            t_close = pd.Timestamp(d.year, d.month, d.day, 18, 0, tz="UTC")
        pos = h1.index.searchsorted(t_open, side="left")
        if pos < 10:
            continue
        window10 = h1.iloc[pos - 10:pos]
        if len(window10) < 10:
            continue
        asian_high = window10["high"].max()
        asian_low = window10["low"].min()
        for side, order_type, trig, sl0, tp0 in (
            ("long", "buy_stop", asian_high, asian_high - sl_d, asian_high + tp_d),
            ("short", "sell_stop", asian_low, asian_low + sl_d, asian_low - tp_d),
        ):
            ft, fp, gap_e = lib.scan_pending_fill(m1, t_open, t_close, trig, order_type)
            if ft is None:
                continue
            et, ep, reason, amb, gap_x = lib.scan_fixed_exit(
                m1, ft, side, sl0, tp0, pd.Timedelta(days=90))
            trades.append(dict(instrument=instr, strategy="LondonBreakout", version=version,
                                variant="", side=side, signal_time=t_open, entry_time=ft,
                                entry_fill=fp, sl0=sl0, tp0=tp0, exit_time=et, exit_price=ep,
                                exit_reason=reason, ambiguous_bar=amb, gap_entry=gap_e, gap_exit=gap_x))
    return trades


# ---------------------------------------------------------------------------
# 2. DailyBreakout
# ---------------------------------------------------------------------------
def daily_breakout(instr, version, m1, start, end):
    d1 = lib.resample_ohlc(m1, "1D")
    d1 = d1[(d1.index >= start) & (d1.index < end)]
    trades = []
    busy_until = None
    for i in range(1, len(d1)):
        day_start = d1.index[i]
        day_end = day_start + pd.Timedelta(days=1)
        if busy_until is not None and busy_until > day_start:
            continue
        prev_high = d1["high"].iloc[i - 1]
        prev_low = d1["low"].iloc[i - 1]
        today_open = d1["open"].iloc[i]
        if not (today_open < prev_high and today_open > prev_low):
            continue
        max_exit = None
        for side, order_type, trig, sl0 in (
            ("long", "buy_stop", prev_high, prev_low),
            ("short", "sell_stop", prev_low, prev_high),
        ):
            ft, fp, gap_e = lib.scan_pending_fill(m1, day_start, day_end, trig, order_type)
            if ft is None:
                continue
            et, ep, reason, gap_x = lib.scan_trailing_exit(
                m1, ft, side, sl0, fp, pd.Timedelta(days=365))
            trades.append(dict(instrument=instr, strategy="DailyBreakout", version=version,
                                variant="", side=side, signal_time=day_start, entry_time=ft,
                                entry_fill=fp, sl0=sl0, tp0=None, exit_time=et, exit_price=ep,
                                exit_reason=reason, ambiguous_bar=False, gap_entry=gap_e, gap_exit=gap_x))
            if et is not None:
                max_exit = et if max_exit is None else max(max_exit, et)
        busy_until = max_exit
    return trades


# ---------------------------------------------------------------------------
# 3. BollingerBands
# ---------------------------------------------------------------------------
def bollinger_bands(instr, version, m1, start, end, bb_period=20, bb_std=2.0,
                     ma_period=200, sl_pips=200, tp_pips=200):
    h4 = lib.resample_ohlc(m1, "4h")
    c = h4["close"].values
    n = len(c)
    cs = np.insert(np.cumsum(c), 0, 0.0)
    css = np.insert(np.cumsum(c ** 2), 0, 0.0)
    ma_full = h4["close"].rolling(ma_period).mean().values
    mean_full = h4["close"].rolling(bb_period).mean().values
    std_full = h4["close"].rolling(bb_period).std(ddof=0).values
    upper_full = mean_full + bb_std * std_full
    lower_full = mean_full - bb_std * std_full

    sl_d = _sl_dist(instr, version, sl_pips)
    tp_d = _sl_dist(instr, version, tp_pips)
    trades = []
    i0 = ma_period  # need MA200 available
    busy_until = None

    if version == "corrected":
        for i in range(i0, n - 1):
            t_signal = h4.index[i]
            if t_signal < start or t_signal >= end:
                continue
            if busy_until is not None and busy_until > t_signal:
                continue
            close_i = c[i]
            if np.isnan(upper_full[i]) or np.isnan(ma_full[i]):
                continue
            side = None
            if close_i > upper_full[i] and close_i < ma_full[i]:
                side = "short"
            elif close_i < lower_full[i] and close_i > ma_full[i]:
                side = "long"
            if side is None:
                continue
            entry_time_target = h4.index[i + 1]
            pos = m1.index.searchsorted(entry_time_target, side="left")
            if pos >= len(m1):
                continue
            entry_price = float(m1["open"].values[pos])
            if side == "long":
                sl0, tp0 = entry_price - sl_d, entry_price + tp_d
            else:
                sl0, tp0 = entry_price + sl_d, entry_price - tp_d
            et, ep, reason, amb, gap_x = lib.scan_fixed_exit(
                m1, m1.index[pos], side, sl0, tp0, pd.Timedelta(days=270))
            trades.append(dict(instrument=instr, strategy="BollingerBands", version=version,
                                variant="", side=side, signal_time=t_signal, entry_time=m1.index[pos],
                                entry_fill=entry_price, sl0=sl0, tp0=tp0, exit_time=et, exit_price=ep,
                                exit_reason=reason, ambiguous_bar=amb, gap_entry=False, gap_exit=gap_x))
            busy_until = et
    else:
        # naive: forming-bar band/MA vs FIXED last-closed close (reproduces
        # iClose(...,1) vs bbUpper[0]/ma[0] desync), scanned at M1 resolution
        # within each forming H4 period via the O(1) partial-window trick.
        for i in range(i0, n - 1):
            period_start = h4.index[i]
            period_end = period_start + pd.Timedelta(hours=4)
            if period_start < start or period_start >= end:
                continue
            if busy_until is not None and busy_until > period_start:
                continue
            if i < bb_period or i < ma_period:
                continue
            s19 = cs[i] - cs[i - bb_period + 1]     # sum of PRIOR (bb_period-1) closes
            ss19 = css[i] - css[i - bb_period + 1]
            s_ma = cs[i] - cs[i - ma_period + 1]    # sum of PRIOR (ma_period-1) closes
            last_closed = c[i - 1]  # iClose(...,1): stable throughout period i

            p0 = m1.index.searchsorted(period_start, side="left")
            p1 = m1.index.searchsorted(min(period_end, end), side="left")
            if p0 >= p1:
                continue
            mc = m1["close"].values[p0:p1]
            n_form = np.arange(1, len(mc) + 1)
            f_mean = (s19 + mc) / bb_period
            f_var = (ss19 + mc ** 2) / bb_period - f_mean ** 2
            f_std = np.sqrt(np.clip(f_var, 0, None))
            f_upper = f_mean + bb_std * f_std
            f_lower = f_mean - bb_std * f_std
            f_ma200 = (s_ma + mc) / ma_period

            sell_cond = (last_closed > f_upper) & (mc < f_ma200)
            buy_cond = (last_closed < f_lower) & (mc > f_ma200)
            any_cond = sell_cond | buy_cond
            if not any_cond.any():
                continue
            k = int(np.argmax(any_cond))
            side = "short" if sell_cond[k] else "long"
            entry_time = m1.index[p0 + k]
            entry_price = float(mc[k])
            if side == "long":
                sl0, tp0 = entry_price - sl_d, entry_price + tp_d
            else:
                sl0, tp0 = entry_price + sl_d, entry_price - tp_d
            et, ep, reason, amb, gap_x = lib.scan_fixed_exit(
                m1, entry_time, side, sl0, tp0, pd.Timedelta(days=270))
            trades.append(dict(instrument=instr, strategy="BollingerBands", version=version,
                                variant="", side=side, signal_time=period_start, entry_time=entry_time,
                                entry_fill=entry_price, sl0=sl0, tp0=tp0, exit_time=et, exit_price=ep,
                                exit_reason=reason, ambiguous_bar=amb, gap_entry=False, gap_exit=gap_x))
            busy_until = et
    return trades


# ---------------------------------------------------------------------------
# 4. FVG
# ---------------------------------------------------------------------------
def fvg(instr, version, m1, start, end, sl_pips=5, tp_pips=40):
    sl_d = _sl_dist(instr, version, sl_pips)
    tp_d = _sl_dist(instr, version, tp_pips)
    o = m1["open"].values
    h = m1["high"].values
    l = m1["low"].values
    n = len(m1)

    h1s, l1s = np.roll(h, 1), np.roll(l, 1)      # shift(1): bar t-1
    h2s, l2s = np.roll(h, 2), np.roll(l, 2)      # shift(2): bar t-2
    h3s, l3s = np.roll(h, 3), np.roll(l, 3)      # shift(3): bar t-3

    if version == "corrected":
        bull = l1s > h3s
        bear = h1s < l3s
        mid = l2s + (h2s - l2s) / 2.0
    else:
        # naive: bar 0 = forming, approximated by its OPEN only (open=high=low,
        # earliest-tick proxy — see SPECS.md addendum); bar i-1 -> shift1, i-2 -> shift2
        bull = o > h2s
        bear = o < l2s
        mid = l1s + (h1s - l1s) / 2.0

    bull[:4] = False
    bear[:4] = False
    cond = bull | bear
    idx_start = m1.index.searchsorted(start, side="left")
    idx_end = m1.index.searchsorted(end, side="left")
    cand_idx = np.nonzero(cond[idx_start:idx_end])[0] + idx_start

    trades = []
    busy_until_idx = -1
    for t in cand_idx:
        if t <= busy_until_idx:
            continue
        entry_time = m1.index[t]
        day_end = pd.Timestamp(entry_time.date(), tz="UTC") + pd.Timedelta(days=1)
        side = "long" if bull[t] else "short"
        trig = float(mid[t])
        order_type = "buy_limit" if side == "long" else "sell_limit"
        ft, fp, gap_e = lib.scan_pending_fill(m1, entry_time, day_end, trig, order_type)
        if ft is None:
            busy_until_idx = m1.index.searchsorted(day_end, side="left") - 1
            continue
        sl0 = fp - sl_d if side == "long" else fp + sl_d
        tp0 = fp + tp_d if side == "long" else fp - tp_d
        et, ep, reason, amb, gap_x = lib.scan_fixed_exit(m1, ft, side, sl0, tp0, pd.Timedelta(days=90))
        trades.append(dict(instrument=instr, strategy="FVG", version=version, variant="",
                            side=side, signal_time=entry_time, entry_time=ft, entry_fill=fp,
                            sl0=sl0, tp0=tp0, exit_time=et, exit_price=ep, exit_reason=reason,
                            ambiguous_bar=amb, gap_entry=gap_e, gap_exit=gap_x))
        busy_until_idx = m1.index.searchsorted(et, side="left") if et is not None else \
            m1.index.searchsorted(day_end, side="left") - 1
    return trades


# ---------------------------------------------------------------------------
# 5. MAcroisement
# ---------------------------------------------------------------------------
def ma_croisement(instr, version, m1, start, end, ema_fast=21, ema_slow=55,
                   sl_pips=20, tp_pips=40, variant=""):
    h1 = lib.resample_ohlc(m1, "1h")
    c = h1["close"]
    ema21 = c.ewm(span=ema_fast, adjust=False).mean().values
    ema55 = c.ewm(span=ema_slow, adjust=False).mean().values
    n = len(h1)
    sl_d = _sl_dist(instr, version, sl_pips)
    tp_d = _sl_dist(instr, version, tp_pips)
    alpha21 = 2.0 / (ema_fast + 1)
    alpha55 = 2.0 / (ema_slow + 1)

    trades = []
    busy_until = None

    def make_trade(side, entry_time, entry_price, t_signal):
        if side == "long":
            sl0, tp0 = entry_price - sl_d, entry_price + tp_d
        else:
            sl0, tp0 = entry_price + sl_d, entry_price - tp_d
        et, ep, reason, amb, gap_x = lib.scan_fixed_exit(
            m1, entry_time, side, sl0, tp0, pd.Timedelta(days=90))
        trades.append(dict(instrument=instr, strategy="MAcroisement", version=version,
                            variant=variant, side=side, signal_time=t_signal, entry_time=entry_time,
                            entry_fill=entry_price, sl0=sl0, tp0=tp0, exit_time=et, exit_price=ep,
                            exit_reason=reason, ambiguous_bar=amb, gap_entry=False, gap_exit=gap_x))
        return et

    if version == "corrected":
        for i in range(1, n - 1):
            t_signal = h1.index[i]
            if t_signal < start or t_signal >= end:
                continue
            if busy_until is not None and busy_until > t_signal:
                continue
            side = None
            # CopyBuffer(handle,0,0,2,arr) sans ArraySetAsSeries -> arr NON-series ->
            # copie en ordre CHRONOLOGIQUE : arr[0]=plus ancienne des 2 barres demandees
            # (= la barre CLOSE precedente), arr[1]=plus recente (= la barre EN FORMATION
            # au moment de l'appel). Condition source relue avec la bonne indexation =
            # croisement HAUSSIER (golden cross) declenche BUY, croisement BAISSIER (death
            # cross) declenche SELL -- PAS inverse (correction du 2026-08-28, cf. SPECS.md).
            if ema21[i] > ema55[i] and ema21[i - 1] < ema55[i - 1]:
                side = "long"
            elif ema21[i] < ema55[i] and ema21[i - 1] > ema55[i - 1]:
                side = "short"
            if side is None:
                continue
            entry_time_target = h1.index[i + 1]
            pos = m1.index.searchsorted(entry_time_target, side="left")
            if pos >= len(m1):
                continue
            entry_price = float(m1["open"].values[pos])
            busy_until = make_trade(side, m1.index[pos], entry_price, t_signal)
    else:
        for i in range(1, n - 1):
            period_start = h1.index[i]
            if period_start < start or period_start >= end:
                continue
            period_end = period_start + pd.Timedelta(hours=1)
            if busy_until is not None and busy_until > period_start:
                continue
            e21_prev, e55_prev = ema21[i - 1], ema55[i - 1]
            p0 = m1.index.searchsorted(period_start, side="left")
            p1 = m1.index.searchsorted(period_end, side="left")
            if p0 >= p1:
                continue
            mc = m1["close"].values[p0:p1]
            f21 = alpha21 * mc + (1 - alpha21) * e21_prev
            f55 = alpha55 * mc + (1 - alpha55) * e55_prev
            buy_cond = (f21 > f55) & (e21_prev < e55_prev)
            sell_cond = (f21 < f55) & (e21_prev > e55_prev)
            any_cond = buy_cond | sell_cond
            if not any_cond.any():
                continue
            k = int(np.argmax(any_cond))
            side = "long" if buy_cond[k] else "short"
            entry_time = m1.index[p0 + k]
            entry_price = float(mc[k])
            busy_until = make_trade(side, entry_time, entry_price, period_start)
    return trades
