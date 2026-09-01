"""AUDIT VARIANT of intrabar_engine.py -- tests whether MT5/broker-server-time (EET/EEST, DST-aware)
anchoring of the H4/D1 TDI timeframes and the WEEKLY pivot bar changes the reproduction fidelity,
vs. the baseline's naive UTC-midnight-anchored pandas resample.

Empirical basis (this audit session, verified directly on the M1 cache): the weekly market-close/
reopen gap in EURUSD_M1 sits at Sunday 22:00 UTC in winter and Sunday 21:00 UTC in summer, and the
spring/autumn switch dates (2023: Mar 19 still 22:00, Mar 26 already 21:02; Oct 22 still 21:00, Oct
29 already 22:00) match the EU DST calendar (last Sunday of March/October), NOT the US calendar
(2nd Sun March / 1st Sun Nov). This is Monday 00:00 EET(winter, UTC+2)/EEST(summer, UTC+3) exactly
-- consistent with the project's own MT5-provenance finding (panels timestamped EET/EEST, -2h vs
true UTC). M15/M30/H1 bar boundaries are UNAFFECTED by this (a 2h or 3h offset is an exact multiple
of 15/30/60 min, so those timeframes' absolute bin edges coincide with naive UTC resampling); only
H4 (4h, not a divisor match for 2h/3h offsets) and D1 (daily) and the WEEKLY pivot bar are anchor-
sensitive. This file patches exactly those three.

Original docstring (unchanged mechanics otherwise):
Deux corrections par rapport au moteur H1 :
  1. NormalizeDouble(MathMean(tdi),1) du MQL5 -> arrondi au dixieme de chaque moyenne RSI.
  2. CalculateTdiAngle() code en dur shift=0, dont la fenetre inclut la BARRE EN FORMATION.
     A resolution M1, le RSI de la barre en formation se met a jour en recurrence de Wilder
     depuis la derniere barre FERMEE du timeframe, avec le cours M1 courant.
Cross et trend n'utilisent que des barres fermees (shift=TDI_SHIFT et TDI_SHIFT+1) : constants
a l'interieur d'une barre, donc simplement propages.
"""
import sys, time, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
ENG  = Path("<HOME>/Desktop/Algo_claude/Forex/research/active/dedale_strategy_2026-08/code")
CFG  = Path("<HOME>/Desktop/Algo_claude/Forex/research/active/dedale_config_2026-08/code")
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ENG)); sys.path.insert(0, str(CFG))
import tdi as T, dedale_engine as de

BROKER_TZ = "Europe/Bucharest"  # EET/EEST, EU DST rule -- verified against the M1 weekly gap above

CACHE = Path("<SCRATCH>"
             "9fd32b98-b3ee-47bf-93c1-b7c5a1ac70a6/scratchpad/m1_cache")
R1 = lambda a: np.round(a, 1)
P_RSI, P_F, P_S, P_M = T.RSI_PERIOD, T.TDI_FAST_PERIOD, T.TDI_SLOW_PERIOD, T.TDI_MIDDLE_PERIOD
AMIN, AMAX = T.TDI_ANGLE_MIN, T.TDI_ANGLE_MAX


def resample_broker_tz(s: pd.Series, rule: str, label="right", closed="left") -> pd.Series:
    """Resample a UTC-indexed series on BROKER-LOCAL wall-clock bins (DST-aware), return UTC-indexed."""
    loc = s.tz_convert(BROKER_TZ)
    out = loc.resample(rule, label=label, closed=closed).last().dropna()
    out.index = out.index.tz_convert("UTC")
    return out


def load_weekly_pivots_tzfix(pair: str) -> pd.DataFrame:
    """Weekly pivots anchored to Monday 00:00 broker-local time (EET/EEST, DST-aware), instead of
    the baseline's Sunday 00:00 UTC. Same +1 week forward-application as de.load_weekly_pivots."""
    df = pd.read_parquet(CACHE / f"{pair}_M1.parquet")
    loc = df.index.tz_convert(BROKER_TZ)
    w = df.set_axis(loc).resample("W-MON", label="left", closed="left").agg(
        high=("high", "max"), low=("low", "min"), close=("close", "last")).dropna()
    # W-MON label=left, closed=left -> bins [Mon 00:00 broker-local, next Mon 00:00) labelled by
    # the Monday start -- confirmed empirically with a controlled date_range (168h/bin, DST weeks
    # 121/145h). This is the MT5 PERIOD_W1 convention (week opens Monday, server time).
    p0 = (w["high"] + w["low"] + w["close"]) / 3.0
    r1 = 2 * p0 - w["low"]
    s1 = 2 * p0 - w["high"]
    r2 = p0 + (w["high"] - w["low"])
    s2 = p0 - (w["high"] - w["low"])
    piv = pd.DataFrame({"S1": s1, "S2": s2, "R1": r1, "R2": r2})
    piv.index = (piv.index + pd.Timedelta(days=7)).tz_convert("UTC")
    return piv.sort_index()


def wilder_state(close: pd.Series, p: int):
    """RSI de Wilder + etats avg_gain/avg_loss a chaque barre FERMEE."""
    d = close.diff()
    g = d.clip(lower=0.0); l = (-d).clip(lower=0.0)
    ag = g.ewm(alpha=1.0/p, adjust=False, min_periods=p).mean()
    al = l.ewm(alpha=1.0/p, adjust=False, min_periods=p).mean()
    rs = ag / al.replace(0.0, np.nan)
    rsi = (100.0 - 100.0/(1.0+rs)).fillna(50.0)
    return rsi, ag, al


def tf_intrabar(m1_close: pd.Series, tf_idx: int) -> pd.DataFrame:
    """Conditions TDI a resolution M1 pour un timeframe.
    tf_idx in {3 (H4), 4 (D1)}: broker-local (EET/EEST) wall-clock anchoring, DST-aware -- these
    two periods are NOT exact divisors of the 2h/3h UTC<->broker offset, unlike M15/M30/H1."""
    rule = T.TF_RULES[tf_idx]
    if tf_idx in (3, 4):
        c = resample_broker_tz(m1_close, rule, label="right", closed="left")
    else:
        c = m1_close.resample(rule, label="right", closed="left").last().dropna()
    rsi, ag, al = wilder_state(c, P_RSI)

    # moyennes sur barres FERMEES (shift=1) et leur decalage (shift=2)
    m_f1 = R1(rsi.rolling(P_F).mean()); m_s1 = R1(rsi.rolling(P_S).mean()); m_m1 = R1(rsi.rolling(P_M).mean())
    cross_up  = (m_f1.shift(1) < m_s1.shift(1)) & (m_f1 > m_s1)
    cross_dn  = (m_f1.shift(1) > m_s1.shift(1)) & (m_f1 < m_s1)
    trend_up  = m_m1.shift(1) < m_m1
    trend_dn  = m_m1.shift(1) > m_m1
    # sommes des p-1 dernieres valeurs FERMEES (pour la fenetre shift=0)
    sum_f = rsi.rolling(P_F-1).sum() if P_F > 1 else rsi*0.0
    sum_s = rsi.rolling(P_S-1).sum()

    closed = pd.DataFrame({"c":c, "ag":ag, "al":al, "sum_f":sum_f, "sum_s":sum_s,
                           "m_f1":m_f1, "m_s1":m_s1,
                           "cross_up":cross_up, "cross_dn":cross_dn,
                           "trend_up":trend_up, "trend_dn":trend_dn})
    # propager la DERNIERE barre fermee sur chaque minute
    al_m1 = closed.reindex(closed.index.union(m1_close.index)).sort_index().ffill().reindex(m1_close.index)

    # RSI de la barre EN FORMATION : recurrence de Wilder depuis la derniere cloture
    delta = m1_close.values - al_m1["c"].values
    a = 1.0/P_RSI
    agf = al_m1["ag"].values*(1-a) + np.maximum(delta, 0.0)*a
    alf = al_m1["al"].values*(1-a) + np.maximum(-delta, 0.0)*a
    with np.errstate(divide="ignore", invalid="ignore"):
        rsif = 100.0 - 100.0/(1.0 + agf/np.where(alf == 0, np.nan, alf))
    rsif = np.nan_to_num(rsif, nan=50.0)

    ma_f0 = R1((al_m1["sum_f"].values + rsif)/P_F)   # shift=0 : p-1 fermees + formation
    ma_s0 = R1((al_m1["sum_s"].values + rsif)/P_S)
    fa = np.degrees(np.arctan(ma_f0 - al_m1["m_f1"].values))
    sa = np.degrees(np.arctan(ma_s0 - al_m1["m_s1"].values))
    w = P_RSI/P_M
    ang = np.round((sa + fa*w)/(1.0+w), 1)

    return pd.DataFrame({
        "cross_up": al_m1["cross_up"].fillna(False).values.astype(bool),
        "cross_dn": al_m1["cross_dn"].fillna(False).values.astype(bool),
        "trend_up": al_m1["trend_up"].fillna(False).values.astype(bool),
        "trend_dn": al_m1["trend_dn"].fillna(False).values.astype(bool),
        "angle_buy": (ang >= AMIN) & (ang <= AMAX),
        "angle_sell": (ang <= -AMIN) & (ang >= -AMAX)}, index=m1_close.index)


def run_pair_intrabar(pair: str, active_filters: set, start=None, end=None, verbose=True):
    t0 = time.time()
    base, quote = de.PAIR_CCY[pair]
    m1 = pd.read_parquet(CACHE/f"{pair}_M1.parquet")
    if start is not None: m1 = m1[m1.index >= start]
    if end is not None:   m1 = m1[m1.index <= end]
    if len(m1) < 10000: return pd.DataFrame()
    m1c = m1["close"]

    piv = load_weekly_pivots_tzfix(pair).reindex(m1.index, method="ffill")
    rd  = de.load_rate_diff(base, quote).reindex(m1.index, method="ffill")
    pip = de.pip_size(pair)
    sl_min, tp_min = de.SL_DISTANCE_MIN_PIPS*pip, de.TP_DISTANCE_MIN_PIPS*pip

    n = len(m1)
    buy_ok = np.ones(n, bool); sell_ok = np.ones(n, bool)
    for tf_idx in sorted({t for t, _ in active_filters}):
        cd = tf_intrabar(m1c, tf_idx)
        for tfi, kind in active_filters:
            if tfi != tf_idx: continue
            if kind == "CROSS": buy_ok &= cd["cross_up"].values;   sell_ok &= cd["cross_dn"].values
            if kind == "TREND": buy_ok &= cd["trend_up"].values;   sell_ok &= cd["trend_dn"].values
            if kind == "ANGLE": buy_ok &= cd["angle_buy"].values;  sell_ok &= cd["angle_sell"].values
        del cd

    idx = m1.index
    o, hi, lo, cl = m1["open"].values, m1["high"].values, m1["low"].values, m1["close"].values
    S1, S2 = piv["S1"].values, piv["S2"].values
    R1v, R2v = piv["R1"].values, piv["R2"].values
    rdv = rd.values
    trades = []; pos = None
    for t in range(1, n-1):
        if pos is None:
            if not (buy_ok[t] or sell_ok[t]): continue
            if np.isnan(S1[t]) or np.isnan(rdv[t]) or rdv[t] == 0: continue
            direction = 0 if rdv[t] > 0 else 1
            if (direction == 0 and not buy_ok[t]) or (direction == 1 and not sell_ok[t]): continue
            mid = cl[t]
            sl, tp = de.get_trade_info(direction, mid, mid, S1[t], S2[t], R1v[t], R2v[t])
            if sl is None or tp is None: continue
            dsl = mid-sl if direction == 0 else sl-mid
            dtp = tp-mid if direction == 0 else mid-tp
            if dsl < sl_min or dtp < tp_min or dsl <= 0 or dtp <= 0: continue
            pos = dict(d=direction, i0=t+1, t0=idx[t+1], p0=o[t+1], sl=sl, tp=tp,
                       dsl=dsl, dtp=dtp, rd=rdv[t])
        else:
            d = pos["d"]; xp = None; why = None
            if d == 0:
                if lo[t] <= pos["sl"]: xp, why = pos["sl"], "SL"
                elif hi[t] >= pos["tp"]: xp, why = pos["tp"], "TP"
            else:
                if hi[t] >= pos["sl"]: xp, why = pos["sl"], "SL"
                elif lo[t] <= pos["tp"]: xp, why = pos["tp"], "TP"
            if xp is not None:
                r = (xp-pos["p0"])/pos["dsl"] if d == 0 else (pos["p0"]-xp)/pos["dsl"]
                hold = (idx[t]-pos["t0"]).total_seconds()/86400
                nights = len(pd.date_range(pos["t0"].normalize(), idx[t].normalize(), freq="D"))-1
                trades.append(dict(pair=pair, direction="buy" if d == 0 else "sell",
                    entry_time=pos["t0"], exit_time=idx[t], exit_reason=why,
                    entry_price=pos["p0"], exit_price=xp, sl=pos["sl"], tp=pos["tp"],
                    r_multiple=r, hold_days=hold, nights=max(nights, 0),
                    notional_per_risk_unit=pos["p0"]/pos["dsl"], swap_bps_annual=abs(pos["rd"])))
                pos = None
    df = pd.DataFrame(trades)
    if verbose: print(f"  [{pair}] {len(m1)} barres M1 -> {len(df)} trades  ({time.time()-t0:.0f}s)", flush=True)
    return df
