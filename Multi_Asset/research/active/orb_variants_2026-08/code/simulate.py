"""
Moteur de simulation ORB, une variante a la fois, depuis les structures de
build_sessions.py. Un "engine run" fixe (open_type, dur, breakout_def,
overshoot_mult, confirm, exit_rule) et produit une ligne de trade par jour
RTH ou aucune (si pas de cassure / pas de confirmation / pas de retest).

Cout : converti PAR TRADE via entry/|entry-stop| (jamais un levier fixe).
Stop par defaut = cote oppose de l'OR (spec deployee). exit_rule='stop_half_OR'
et exit_rule='trailing_ATR' changent la distance/regle de stop.
"""
import numpy as np
import pandas as pd
import pickle

COST_BPS = 0.962e-4  # 0.962 bps RT

SESS_PATH = "<HOME>/Desktop/Algo_claude_orbvar/Multi_Asset/research/active/orb_variants_2026-08/code/sessions.pkl"


def load_sessions():
    with open(SESS_PATH, "rb") as f:
        return pickle.load(f)


def _time_stop_bar_idx(T_row, m, cutoff_hour, cutoff_minute):
    """Index (0-based, within T_row[:m]) of the last 5min bar strictly before
    cutoff time. Returns m-1 (full session) if cutoff_hour is None."""
    if cutoff_hour is None:
        return m - 1
    cutoff_min_of_day = cutoff_hour * 60 + cutoff_minute
    last_ok = -1
    for k in range(m):
        t = T_row[k]
        if t is None:
            break
        mod = t.hour * 60 + t.minute
        if mod < cutoff_min_of_day:
            last_ok = k
        else:
            break
    return last_ok


EXIT_RULES = {
    # name -> dict(time_stop=(hour,min) or None, tp_R=None or float,
    #              stop_mode='opposite_or'|'half_or', trailing=False)
    "close_RTH": dict(time_stop=None, tp_R=None, stop_mode="opposite_or", trailing=False),
    "time_stop_12": dict(time_stop=(12, 0), tp_R=None, stop_mode="opposite_or", trailing=False),
    "time_stop_11": dict(time_stop=(11, 0), tp_R=None, stop_mode="opposite_or", trailing=False),
    "TP_1R": dict(time_stop=None, tp_R=1.0, stop_mode="opposite_or", trailing=False),
    "TP_1.5R": dict(time_stop=None, tp_R=1.5, stop_mode="opposite_or", trailing=False),
    "TP_2R": dict(time_stop=None, tp_R=2.0, stop_mode="opposite_or", trailing=False),
    "stop_half_OR": dict(time_stop=None, tp_R=None, stop_mode="half_or", trailing=False),
    "trailing_ATR": dict(time_stop=None, tp_R=None, stop_mode="opposite_or", trailing=True),
}


def simulate_engine(sess, open_type, dur, breakout_def, overshoot_mult, confirm, exit_rule_name):
    rule = EXIT_RULES[exit_rule_name]
    rth_dates = sess["rth_dates"]
    daily = sess["daily"]
    H, L, C, O, T = sess["H"], sess["L"], sess["C"], sess["O"], sess["T"]
    or_df = (sess["or_rth"] if open_type == "RTH" else sess["or_globex"])[dur]
    start_bar = sess["path_start_idx"][(open_type, dur)]
    n, max_bars = H.shape

    atr_by_date = daily["atr14_t1"].reindex(pd.to_datetime(rth_dates)).to_numpy()
    or_hi_all = or_df["or_hi"].reindex(rth_dates).to_numpy()
    or_lo_all = or_df["or_lo"].reindex(rth_dates).to_numpy()

    rows = []
    for i in range(n):
        or_hi, or_lo = or_hi_all[i], or_lo_all[i]
        if not (np.isfinite(or_hi) and np.isfinite(or_lo)) or or_hi <= or_lo:
            continue
        or_range = or_hi - or_lo
        atr = atr_by_date[i]
        overshoot = overshoot_mult * atr if (overshoot_mult > 0 and np.isfinite(atr)) else 0.0
        level_long = or_hi + overshoot
        level_short = or_lo - overshoot

        h_row, l_row, c_row, o_row, t_row = H[i], L[i], C[i], O[i], T[i]
        # trim to valid bars from start_bar onward
        valid = ~np.isnan(h_row)
        m_full = int(valid.sum())
        if m_full <= start_bar:
            continue
        hb = h_row[start_bar:m_full]
        lb = l_row[start_bar:m_full]
        cb = c_row[start_bar:m_full]
        ob = o_row[start_bar:m_full]
        tb = t_row[start_bar:m_full]
        m = len(hb)
        if m < 2:
            continue

        cutoff_idx = _time_stop_bar_idx(tb, m, *(rule["time_stop"] or (None, None)))
        if cutoff_idx < 0:
            continue

        # ---- step 1: find trigger bar/direction per breakout_def ----
        if breakout_def == "touch":
            long_trig = hb >= level_long
            short_trig = lb <= level_short
        else:  # close
            long_trig = cb >= level_long
            short_trig = cb <= level_short
        both = long_trig & short_trig

        t0 = None
        dirn = 0
        for k in range(0, cutoff_idx + 1):
            lt, st = long_trig[k], short_trig[k]
            if lt and st:
                # tie-break: close>open in that bar => assume high hit first (long)
                dirn = 1 if cb[k] >= ob[k] else -1
                t0 = k
                break
            elif lt:
                dirn = 1
                t0 = k
                break
            elif st:
                dirn = -1
                t0 = k
                break
        if t0 is None:
            continue

        entry_bar = None
        entry_price = None
        level = level_long if dirn == 1 else level_short

        if confirm == "immediate":
            entry_bar = t0
            entry_price = level if breakout_def == "touch" else cb[t0]
        elif confirm == "bar_close":
            if t0 + 1 > cutoff_idx:
                continue
            entry_bar = t0 + 1
            entry_price = ob[t0 + 1]
        elif confirm == "2bar":
            # scan forward for 2 consecutive closes beyond the SAME level/direction
            found = None
            k = t0
            while k + 1 <= cutoff_idx:
                c1_ok = (cb[k] >= level_long) if dirn == 1 else (cb[k] <= level_short)
                c2_ok = (cb[k + 1] >= level_long) if dirn == 1 else (cb[k + 1] <= level_short)
                if c1_ok and c2_ok:
                    found = k + 1
                    break
                k += 1
            if found is None or found + 1 > cutoff_idx:
                continue
            entry_bar = found + 1
            entry_price = ob[found + 1]
        elif confirm == "retest":
            found = None
            for k in range(t0 + 1, cutoff_idx + 1):
                if dirn == 1 and lb[k] <= level_long:
                    found = k
                    break
                if dirn == -1 and hb[k] >= level_short:
                    found = k
                    break
            if found is None:
                continue
            entry_bar = found
            entry_price = level
        else:
            raise ValueError(confirm)

        if entry_bar is None or entry_bar > cutoff_idx:
            continue

        # ---- stop ----
        if rule["stop_mode"] == "opposite_or":
            stop_price = or_lo if dirn == 1 else or_hi
        elif rule["stop_mode"] == "half_or":
            stop_price = entry_price - dirn * (or_range / 2.0)
        else:
            raise ValueError(rule["stop_mode"])
        R_unit = abs(entry_price - stop_price)
        if R_unit <= 0 or not np.isfinite(R_unit):
            continue

        tp_price = None
        if rule["tp_R"] is not None:
            tp_price = entry_price + dirn * rule["tp_R"] * R_unit

        # ---- walk forward for exit ----
        exit_price = None
        outcome = None
        running_extreme = entry_price
        trail_stop = stop_price
        for k in range(entry_bar, cutoff_idx + 1):
            hk, lk = hb[k], lb[k]
            if rule["trailing"] and np.isfinite(atr):
                if dirn == 1:
                    running_extreme = max(running_extreme, hk)
                    trail_stop = max(trail_stop, running_extreme - atr)
                else:
                    running_extreme = min(running_extreme, lk)
                    trail_stop = min(trail_stop, running_extreme + atr)
            eff_stop = trail_stop if rule["trailing"] else stop_price
            if dirn == 1:
                stop_hit = lk <= eff_stop
                tp_hit = (tp_price is not None) and (hk >= tp_price)
            else:
                stop_hit = hk >= eff_stop
                tp_hit = (tp_price is not None) and (lk <= tp_price)
            if stop_hit and tp_hit:
                # conservative: assume the adverse outcome fires first intrabar
                exit_price = eff_stop
                outcome = "STOP" if not rule["trailing"] else "TRAIL"
                break
            if stop_hit:
                exit_price = eff_stop
                outcome = "STOP" if not rule["trailing"] else "TRAIL"
                break
            if tp_hit:
                exit_price = tp_price
                outcome = "TP"
                break
        if exit_price is None:
            exit_price = cb[cutoff_idx]
            outcome = "TIME_STOP"

        r_gross = dirn * (exit_price - entry_price) / R_unit
        cost_R = entry_price * COST_BPS / R_unit
        r_net = r_gross - cost_R

        rows.append((
            rth_dates[i], dirn, entry_price, stop_price, exit_price, outcome,
            r_gross, r_net, or_range, atr, cost_R,
        ))

    df = pd.DataFrame(rows, columns=[
        "date", "dir", "entry", "stop", "exit", "outcome",
        "r_gross", "r_net", "or_range", "atr14_t1", "cost_R",
    ])
    return df
