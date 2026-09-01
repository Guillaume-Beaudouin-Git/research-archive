"""AUDIT VARIANT: replicates a literal-MQL5 bug in GetTradeInfo() (DedaleFormation.mq5 line ~530-560)
that our Python `get_trade_info` (dedale_engine.py) did NOT replicate.

The bug: `if(MathMin(proba_difference) == proba_difference[index])` is evaluated INSIDE the same
i,j double loop that FILLS `proba_difference[]` element by element. MQL5's ArrayResize()
zero-initializes new numeric elements, so at iteration index<3 (PIVOT_NUMBER=2 -> 4 combos, index
0..3), the array still has UNFILLED (zero) slots at index>current. MathMin() operates over the
array's full declared size regardless of "logical" fill progress, so at every index<3 the reported
minimum is contaminated by trailing zeros and (barring the extremely rare proba_difference==0
exactly) can NEVER equal the just-computed proba_difference[index<3]. Only at the LAST iteration
(i=j=PIVOT_NUMBER-1=1, index=3) is the comparison ever "fair" (array fully populated) -- so the
sl/tp assignment can ONLY EVER fire for the (S2,R2) [widest] pivot pair, and only when that pair's
|prob-50| happens to also be the true global minimum of the 4. In every other case sl=0, tp=0
(their declared initial values) are returned, which then makes IsTradeAllowed's distance check
(`ask > tp - tp_distance_min` i.e. `ask > -tp_distance_min`) trivially true -> trade blocked.
Net effect: the "search 4 pivot combos for closest-to-50%" is NOT what the EA does; it only ever
trades the widest (S2,R2) pair, and only in the (minority of) bars where that pair is itself the
argmin. Delta n_tests = 0 (audit of an existing reproduction, not a new hypothesis).

Original docstring (mechanics otherwise unchanged):
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

PIVOT_NUMBER = de.PIVOT_NUMBER
TARGET_PROBABILITY = de.TARGET_PROBABILITY


def get_trade_info_buggy(direction: int, bid: float, ask: float, S1, S2, R1, R2):
    """Literal-MQL5 replica INCLUDING the MathMin-on-partially-filled-array bug: can only ever
    return the (S2,R2)-pivot-pair combo (i=j=PIVOT_NUMBER-1), and only if it is the true argmin
    of |prob-50| among all 4 combos. Otherwise returns (None, None) -- equivalent to MQL5's sl=0/
    tp=0, which IsTradeAllowed always rejects downstream."""
    S = [S1, S2]; R = [R1, R2]
    if direction == 0:
        sl_size = [abs(S[i] - bid) for i in range(PIVOT_NUMBER)]
        tp_size = [abs(R[i] - ask) for i in range(PIVOT_NUMBER)]
    else:
        sl_size = [abs(R[i] - ask) for i in range(PIVOT_NUMBER)]
        tp_size = [abs(S[i] - bid) for i in range(PIVOT_NUMBER)]

    diffs = {}
    for i in range(PIVOT_NUMBER):
        for j in range(PIVOT_NUMBER):
            if direction == 0:
                valid = (bid > S[j]) and (ask < R[i])
            else:
                valid = (bid > S[i]) and (ask < R[j])
            prob = (tp_size[i] / (tp_size[i] + sl_size[j]) * 100.0) if valid else 151.0
            diffs[(i, j)] = abs(prob - TARGET_PROBABILITY)

    last = (PIVOT_NUMBER - 1, PIVOT_NUMBER - 1)
    if diffs[last] <= min(diffs.values()):
        i, j = last
        if direction == 0:
            return S[j], R[i]
        else:
            return R[j], S[i]
    return None, None

CACHE = Path("<SCRATCH>"
             "9fd32b98-b3ee-47bf-93c1-b7c5a1ac70a6/scratchpad/m1_cache")
R1 = lambda a: np.round(a, 1)
P_RSI, P_F, P_S, P_M = T.RSI_PERIOD, T.TDI_FAST_PERIOD, T.TDI_SLOW_PERIOD, T.TDI_MIDDLE_PERIOD
AMIN, AMAX = T.TDI_ANGLE_MIN, T.TDI_ANGLE_MAX


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
    """Conditions TDI a resolution M1 pour un timeframe."""
    rule = T.TF_RULES[tf_idx]
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

    piv = de.load_weekly_pivots(pair).reindex(m1.index, method="ffill")
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
            sl, tp = get_trade_info_buggy(direction, mid, mid, S1[t], S2[t], R1v[t], R2v[t])
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
