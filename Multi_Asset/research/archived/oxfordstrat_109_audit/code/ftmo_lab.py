"""
ftmo_lab.py — Reusable backtest engine + FTMO cost model + metrics.
Used to filter the 109 oxfordstrat strategies across the FTMO universe.

Design notes
------------
- Daily OHLC store built in outputs/ohlc/{INSTR}.parquet (see _coverage.csv).
- Strategies of the "stop-entry + bracket-exit" family (breakouts, Crabel ORB,
  gap/NR patterns...) are simulated event-driven with explicit, *conservative*
  intrabar assumptions (stop assumed to fill before target when both are inside
  a daily bar).
- Performance is risk-normalised: every trade risks a fixed fraction of equity
  at its initial stop distance, so instruments with very different price levels
  and volatilities are directly comparable and aggregatable.
- Costs (spread + commission + slippage) are charged per round turn, in bps of
  notional, with conservative per-class floors so the "edge after costs" test is
  honest rather than flattered by ultra-tight raw spreads.
"""
from __future__ import annotations
import numpy as np, pandas as pd, glob, os
from statistics import NormalDist

PIPELINE_VERSION = "v2-gates"   # constitutional gates are MANDATORY before any KEEP
_NORM = NormalDist()

def _find_ohlc_dir():
    """Resolve the OHLC store: $OHLC_DIR, else first existing of ./ohlc,
    ../ohlc (when this file lives in code/), or cwd/ohlc."""
    if os.environ.get("OHLC_DIR"):
        return os.environ["OHLC_DIR"]
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "ohlc"),
                 os.path.join(here, "..", "ohlc"),
                 os.path.join(os.getcwd(), "ohlc")):
        if os.path.isdir(cand):
            return os.path.abspath(cand)
    return os.path.join(here, "ohlc")

OHLC_DIR = _find_ohlc_dir()

CLASS = {  # instrument -> asset class
 **{t:'indices' for t in "US500 US100 US30 US2000 GER40 UK100 EU50 AUS200 JP225 HK50".split()},
 **{t:'forex'   for t in "EURUSD GBPUSD USDJPY USDCHF USDCAD AUDUSD NZDUSD EURGBP AUDJPY GBPJPY".split()},
 **{t:'crypto'  for t in "BTCUSD ETHUSD LTCUSD XRPUSD XMRUSD NEOUSD ADAUSD DASHUSD DOTUSD DOGEUSD".split()},
 **{t:'commodities' for t in "XAUUSD XAGUSD XPTUSD XPDUSD USOIL UKOIL WHEAT SOYBEAN COFFEE COCOA".split()},
}

# Conservative round-turn cost FLOORS (bps of notional) per class, FTMO-style.
COST_FLOOR_BPS = {'forex':1.5, 'indices':2.0, 'commodities':4.0, 'crypto':8.0}
# Commission per ROUND TURN (bps of notional), from ftmo_specs.
COMMISSION_RT_BPS = {'forex':0.5, 'indices':0.0, 'commodities':0.3, 'crypto':2.0}
SLIPPAGE_BPS = 2.0       # conservative daily stop-entry slippage, round turn
RISK_FRAC    = 0.005     # 0.5% equity risked per trade (fixed-fractional)

# ---------------------------------------------------------------- data
def load_universe(instruments=None):
    out = {}
    for f in sorted(glob.glob(os.path.join(OHLC_DIR, "*.parquet"))):
        t = os.path.basename(f)[:-8]
        if instruments and t not in instruments:
            continue
        df = pd.read_parquet(f)
        df.index = pd.to_datetime(df.index)
        out[t] = df.sort_index()
    return out

def round_turn_cost_bps(instr, df):
    """Round-turn cost in bps: measured spread (if present) + commission + slippage,
    floored at a conservative per-class level."""
    cls = CLASS.get(instr, 'indices')
    spread_bps = 0.0
    if 'spread' in df.columns:
        # spread column is in broker 'points'; 1 point = 10**-digits of price.
        # Convert median spread to bps of price using the median close.
        digits = _infer_digits(instr)
        pt = 10.0 ** (-digits)
        spread_bps = float((df['spread'].median() * pt / df['close'].median()) * 1e4)
    base = spread_bps + COMMISSION_RT_BPS.get(cls, 1.0) + SLIPPAGE_BPS
    return max(base, COST_FLOOR_BPS.get(cls, 3.0))

def _infer_digits(instr):
    return {'USDJPY':3,'AUDJPY':3,'GBPJPY':3}.get(instr, 5) if CLASS.get(instr)=='forex' else 2

# ---------------------------------------------------------------- indicators
def atr(df, n=20):
    h,l,c = df['high'], df['low'], df['close']
    pc = c.shift(1)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()

# ---------------------------------------------------------------- bracket simulator
def simulate_bracket(df, setup, stretch, *, target_index, time_index,
                     atr_len=20, atr_stop=6.0, cost_bps=2.0, allow_short=True,
                     fill='stop'):
    """Event-driven sim for ORB / breakout-type strategies.
    `setup[i]` True  -> NR/pattern formed using info up to & incl. bar i.
    `stretch[i]`     -> ORB offset to use for entry on bar i+1.
    `fill`           -> entry execution price assumption (the L26 lever):
        'stop'      : OPTIMISTIC — fill at the breakout stop level intra-bar (default,
                      reproduces the original S001 numbers).
        'close'     : fill at the CLOSE of the breakout bar (realistic, same bar).
        'next_open' : fill at the OPEN of the bar AFTER the breakout (realistic delay+1).
      'close'/'next_open' are the adversarial fills consumed by gate_delay1().
    Each trade carries `dir` (+1 long, -1 short, 0 = both-stops-hit loss).
    Returns a DataFrame of trades with net R-multiples (costs included)."""
    o,h,l,c = (df[x].values for x in ('open','high','low','close'))
    A = atr(df, atr_len).values
    su = setup.values.astype(bool); st = stretch.values
    n = len(df); idx = df.index
    trades = []
    i = 1
    while i < n - 1:
        if not (su[i-1] and np.isfinite(st[i-1]) and st[i-1] > 0 and np.isfinite(A[i])):
            i += 1; continue
        e = i                                    # breakout bar (day after setup)
        buy, sell = o[e] + st[i-1], o[e] - st[i-1]
        long_hit  = h[e] >= buy
        short_hit = (l[e] <= sell) and allow_short
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps/1e4) * c[e] / risk0    # round-turn cost in R units

        if long_hit and short_hit:                # both sides -> assume loser (spec)
            trades.append(_trade(idx[e], idx[e], 'both', 0, -2*st[i-1]/risk0 - cost_R, 0))
            i = e + 1; continue
        if not (long_hit or short_hit):
            i += 1; continue
        d = 1 if long_hit else -1

        # ---- entry fill (the L26 lever) -----------------------------------
        if fill == 'stop':
            entry = max(o[e], buy) if d == 1 else min(o[e], sell)
            start_j = e
        elif fill == 'close':
            entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1:
                i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(f"unknown fill mode: {fill}")
        stop = entry - d * risk0
        tgt  = entry + d * target_index * risk0

        last = min(e + time_index, n - 1)          # holding horizon anchored on breakout bar
        exit_p, exit_j, reason = None, None, None
        for j in range(start_j, last + 1):
            if d == 1:
                if l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
                if h[j] >= tgt:   exit_p, reason, exit_j = tgt,  'target', j; break
            else:
                if h[j] >= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
                if l[j] <= tgt:   exit_p, reason, exit_j = tgt,  'target', j; break
            if j == last:                          # time exit at close
                exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None:                          # ran out of data
            exit_j = last; exit_p, reason = c[last], 'eod'

        grossR = d * (exit_p - entry) / risk0
        trades.append(_trade(idx[e], idx[exit_j], reason, d, grossR - cost_R, exit_j - e))
        i = exit_j + 1                              # no overlapping positions
    return pd.DataFrame(trades)

def _trade(t_in, t_out, reason, d, netR, hold):
    return {'entry':t_in, 'exit':t_out, 'reason':reason, 'dir':d, 'netR':netR, 'hold':hold}

# ---------------------------------------------------------------- metrics
def trade_metrics(tr, risk_frac=RISK_FRAC):
    if tr is None or len(tr) == 0:
        return dict(trades=0, win=np.nan, expR=np.nan, pf=np.nan, sharpe=np.nan,
                    cagr=np.nan, maxdd=np.nan, netR_sum=np.nan)
    r = tr['netR'].values
    wins, losses = r[r > 0], r[r < 0]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else np.inf
    # equity curve in fraction of capital, compounded per trade on exit date
    eq = (1 + risk_frac * pd.Series(r, index=pd.to_datetime(tr['exit']))).cumprod()
    eq = eq.groupby(eq.index).last()
    days = max((eq.index[-1] - eq.index[0]).days, 1)
    cagr = eq.iloc[-1] ** (365.0/days) - 1
    dd = (eq / eq.cummax() - 1).min()
    # Sharpe from per-trade returns, annualised by trades/yr
    tpy = len(r) / (days/365.0)
    sh = (np.mean(r)/np.std(r) * np.sqrt(tpy)) if np.std(r) > 0 else np.nan
    return dict(trades=len(r), win=float((r>0).mean()), expR=float(np.mean(r)),
                pf=float(pf), sharpe=float(sh), cagr=float(cagr), maxdd=float(dd),
                netR_sum=float(r.sum()))

# ============================================================================
# CONSTITUTIONAL GATES (v2) — mandatory before any KEEP verdict.
# A strategy provides a `run(fill=...) -> trades_df` callable (params baked in)
# and the array of per-cell Sharpes from its parameter sweep. The gates are
# strategy-agnostic and reused unchanged for S002...S109.
# ============================================================================

def gate_delay1(run, fill_realistic='next_open'):
    """GATE 1 (L26) — the most decisive. Re-price the edge with a realistic fill
    instead of the intra-bar stop level. If the positive edge collapses/inverts
    -> DISCARD (intra-bar fill artefact). `run(fill=...)` returns pooled trades."""
    opt = trade_metrics(run(fill='stop'))
    rea = trade_metrics(run(fill=fill_realistic))
    survives = bool(np.isfinite(rea['expR']) and rea['expR'] > 0 and rea['sharpe'] > 0)
    return {'gate': 'delay1 (L26)', 'pass': survives, 'fill': fill_realistic,
            'opt_expR': opt['expR'], 'opt_sharpe': opt['sharpe'], 'opt_win': opt['win'],
            'real_expR': rea['expR'], 'real_sharpe': rea['sharpe'], 'real_win': rea['win'],
            'tag': None if survives else 'artefact de fill intrabar'}

def gate_twosided(trades, dom_thresh=0.70):
    """GATE 2 (L25) — split by direction. If one side carries essentially all the
    net profit (> dom_thresh of positive directional PnL) while the other side has
    expectancy <= 0, the 'breakout' is disguised directional beta, not a symmetric
    edge -> no KEEP. Requires a `dir` column (+1/-1/0)."""
    r = trades['netR'].values; d = trades['dir'].values
    lr, sr = r[d == 1], r[d == -1]
    sl, ss = float(lr.sum()), float(sr.sum())
    exp_long  = float(lr.mean()) if len(lr) else np.nan
    exp_short = float(sr.mean()) if len(sr) else np.nan
    tot = float(r.sum())
    pos = max(sl, 0) + max(ss, 0)
    dom_share = (max(max(sl, 0), max(ss, 0)) / pos) if pos > 0 else 1.0
    dominant = 'long' if sl >= ss else 'short'
    minor_exp = exp_short if dominant == 'long' else exp_long
    disguised = bool(dom_share > dom_thresh and (not np.isfinite(minor_exp) or minor_exp <= 0))
    return {'gate': 'twosided (L25)', 'pass': not disguised,
            'n_long': int(len(lr)), 'n_short': int(len(sr)),
            'exp_long': exp_long, 'exp_short': exp_short,
            'contrib_long_pct': (sl / tot * 100) if tot else np.nan,
            'contrib_short_pct': (ss / tot * 100) if tot else np.nan,
            'dominant': dominant, 'dom_share_pos_pct': dom_share * 100,
            'tag': None if not disguised else f'beta déguisé ({dominant}-dominé) — re-tester vs buy&hold timé'}

def gate_dsr(grid_sharpes, sr_obs, pooled_netR):
    """GATE 3 — Deflated Sharpe Ratio (Bailey & López de Prado, 2014) over the
    N swept cells. Compares the selected Sharpe to the expected MAX of N noise
    trials. If SR_obs < E[max] -> the 'positive grid' is multiple-testing noise.
    Uses the standardised E[max] approximation (conservative; assumes ~independent
    trials), consistent with the AUDIT_S001 formulation."""
    sr = np.asarray([s for s in np.ravel(grid_sharpes) if np.isfinite(s)], float)
    N = max(len(sr), 2)
    g = 0.5772156649                                  # Euler-Mascheroni
    root = np.sqrt(2.0 * np.log(N))
    e_max = root * (1.0 - g / root)                   # E[max] of N standard-normal trials
    r = np.asarray(pooled_netR, float); nobs = len(r)
    sd = r.std(ddof=1) if nobs > 1 else 0.0
    skew = float(((r - r.mean()) ** 3).mean() / sd ** 3) if sd > 0 else 0.0
    kurt = float(((r - r.mean()) ** 4).mean() / sd ** 4) if sd > 0 else 3.0
    var = max(1.0 - skew * sr_obs + (kurt - 1.0) / 4.0 * sr_obs ** 2, 1e-9)
    sigma_sr = np.sqrt(var / max(nobs - 1, 1))
    z = (sr_obs - e_max) / sigma_sr if sigma_sr > 0 else np.nan
    dsr_prob = _NORM.cdf(z) if np.isfinite(z) else np.nan
    passed = bool(np.isfinite(z) and sr_obs > e_max)  # DSR z > 0
    return {'gate': 'dsr', 'pass': passed, 'N_trials': int(len(sr)),
            'SR_obs': float(sr_obs), 'E_max_SR': float(e_max), 'DSR_z': float(z),
            'DSR_prob': float(dsr_prob), 'skew': skew, 'kurt': kurt,
            'tag': None if passed else 'grille = bruit (multiple testing, DSR<0)'}

def gate_oos(trades, split='2015-12-31'):
    """GATE 4 (L31) — train/test split on the trade ENTRY date. If the edge flips
    sign or disappears out-of-sample -> regime-dependent / decayed, no KEEP.
    Operates post-hoc on the full-sample (fill='stop') trades."""
    sd = pd.Timestamp(split)
    ent = pd.to_datetime(trades['entry'])
    tr, te = trades[ent <= sd], trades[ent > sd]
    mtr, mte = trade_metrics(tr), trade_metrics(te)
    flip = (np.sign(mtr['expR']) != np.sign(mte['expR']))
    survives = bool(np.isfinite(mte['expR']) and mte['expR'] > 0 and not flip)
    return {'gate': 'oos (L31)', 'pass': survives, 'split': split,
            'n_train': mtr['trades'], 'train_expR': mtr['expR'], 'train_sharpe': mtr['sharpe'],
            'n_test': mte['trades'], 'test_expR': mte['expR'], 'test_sharpe': mte['sharpe'],
            'tag': None if survives else 'régime-dépendant / décayé (flip OOS)'}

def run_gates(run, grid_sharpes, split='2015-12-31', weak_sharpe=0.5):
    """Orchestrate the 4 mandatory gates. KEEP is allowed ONLY if there is a
    positive edge after costs AND all gates pass. Otherwise DISCARD (or BORDERLINE
    if all gates pass but the Sharpe is weak). Returns a structured verdict dict."""
    base_trades = run(fill='stop')
    base = trade_metrics(base_trades)
    edge_pos = bool(np.isfinite(base['expR']) and base['expR'] > 0 and base['pf'] > 1.0)
    sr_obs = float(np.nanmax(grid_sharpes)) if np.isfinite(np.nanmax(grid_sharpes)) else base['sharpe']
    gates = [gate_delay1(run), gate_twosided(base_trades),
             gate_dsr(grid_sharpes, sr_obs, base_trades['netR'].values),
             gate_oos(base_trades, split)]
    all_pass = all(g['pass'] for g in gates)
    if not edge_pos:
        verdict, reason = 'DISCARD', "pas d'edge positif après coûts"
    elif all_pass:
        verdict = 'KEEP' if base['sharpe'] >= weak_sharpe else 'BORDERLINE'
        reason = 'edge positif ET 4 gates OK' + ('' if verdict == 'KEEP' else f' (Sharpe {base["sharpe"]:.2f} < {weak_sharpe})')
    else:
        verdict = 'DISCARD'
        reason = ' | '.join(g['tag'] for g in gates if not g['pass'])
    return {'base': base, 'edge_positive': edge_pos, 'gates': gates,
            'n_fail': int(sum(not g['pass'] for g in gates)), 'verdict': verdict, 'reason': reason}
