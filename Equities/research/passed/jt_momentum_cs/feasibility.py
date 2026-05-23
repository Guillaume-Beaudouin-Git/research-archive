"""
jt_momentum_cs/feasibility.py
==============================
Cross-sectional equity momentum — Jegadeesh & Titman (1993) on a
static large-cap US universe.

Literature
----------
- Jegadeesh & Titman (1993) "Returns to Buying Winners and Selling Losers" — JF
  Original: 12M-1M signal on NYSE/AMEX, monthly, Sharpe ~0.5-1.0
- Asness, Moskowitz & Pedersen (2013) "Value and Momentum Everywhere" — JF
  Confirmed across 40 markets; IC ~0.05-0.10/month on equity CS
- Daniel & Moskowitz (2016) "Momentum Crashes" — JFE
  Documents the crash dynamic: GFC 2009, COVID 2020 — vol-scaling mitigates

Key differences from FX runs
-----------------------------
- Short leg WORKS in equities (lesson from crypto: short only failed in crypto).
  Jegadeesh & Titman document symmetric L/S edge.
- 70-stock cross-section → IC std ~1/sqrt(69) ≈ 0.12 (3× smaller than 8-pair FX)
- Monthly frequency: documented holding period, not extrapolated from daily
- Vol scaling (tanh / vol normalisation): mitigates momentum crash events

Universe
--------
Static list of ~70 large-cap S&P 500 constituents that were trading continuously
since 2005. Selection criterion: well-known blue-chip stocks present in SPX as of
2010. No current-composition look-ahead bias — list frozen at 2010 membership.
Tickers excluded: spinoffs that started trading after 2005 (PSX, GM post-2010, etc.)
and near-bankruptcies with data gaps (AIG excluded).

Notes on corporate actions baked into yfinance adjusted prices:
- HPQ split 2015 (HP Inc + HPE): old HPQ data is the combined company, adjusted.
- DD DowDupont merger/split 2017-2019: yfinance adjustments applied.
- BAC, C: near-bankruptcy 2008-2009, data continuous (useful variation for IC test).

Methodology
-----------
Signal A (CS momentum, Jegadeesh & Titman):
    mom[i,t] = cumret[i, t-12M : t-1M] / (vol_12M[i,t] * sqrt(11))
    - Vol-normalised to make signals comparable across stocks
    - Skip last month (documented 1M reversal in equities, Jegadeesh 1990)
    - Cross-sectional L/S quintile (top 20% long, bottom 20% short)

Signal B (TSMOM tanh, Moskowitz-style):
    tsmom[i,t] = tanh( cumret_12M[i,t] / (vol_12M[i,t] * sqrt(12)) )
    - Same family as crypto Strategy A — tests transfer to equity universe
    - No clipping at 0 (short leg allowed)

Shift convention: signals computed at T-1, positions entered at T.
Returns: M-end to M-end adjusted close log-returns.
Costs: 8 bps RT (institutional equity: 3-5 bps commission + 3-5 bps spread).
Annualisation: 12 months.

Hard gate
---------
PASS: IC t-stat > 2.5 AND COVID 2020 MaxDD > -25%
WEAK: IC t-stat 1.5-2.5 OR COVID MaxDD -25% to -35%
SKIP: IC t-stat < 1.5
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
START          = "2005-01-01"
END            = pd.Timestamp.today().strftime("%Y-%m-%d")
COST_RT        = 0.0008      # 8 bps round-trip
LB_MONTHS      = 12          # lookback window
SKIP_MONTHS    = 1           # skip most-recent month (reversal filter)
ANN            = 12          # annualisation factor
RESULTS_PATH   = Path(__file__).parent / "results.json"

# Static large-cap universe — S&P 500 constituents circa 2010
# All tickers have continuous yfinance data back to at least 2005
UNIVERSE = [
    # Technology
    'AAPL', 'MSFT', 'INTC', 'IBM', 'TXN', 'CSCO', 'ORCL', 'QCOM', 'HPQ', 'ADI',
    # Financials
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'AXP', 'USB', 'PNC', 'MET',
    # Healthcare
    'JNJ', 'PFE', 'ABT', 'MRK', 'LLY', 'BMY', 'AMGN', 'UNH', 'MDT', 'BDX',
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'HAL', 'VLO', 'OXY',
    # Consumer Staples
    'WMT', 'PG', 'KO', 'PEP', 'MO', 'CL', 'KMB', 'GIS',
    # Consumer Discretionary
    'HD', 'MCD', 'NKE', 'LOW', 'TGT', 'DIS', 'F',
    # Industrials
    'BA', 'CAT', 'GE', 'MMM', 'HON', 'EMR', 'ITW', 'UPS', 'FDX',
    # Materials
    'NEM', 'FCX', 'PPG', 'SHW', 'DD',
    # Utilities
    'SO', 'DUK', 'D', 'AEP', 'EXC',
    # Communication / Telecom
    'VZ', 'T',
]

CRASH_PERIODS = {
    'GFC_2008':   ('2008-07-01', '2009-06-30'),
    'COVID_2020': ('2020-02-01', '2020-06-30'),
}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def fetch_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """
    Download adjusted monthly close for all tickers.
    Downloads in one yfinance call, resamples to M-end, drops tickers
    with >20% missing months.
    """
    log.info(f"Downloading {len(tickers)} tickers from yfinance …")
    raw = yf.download(
        tickers, start=start, end=end,
        auto_adjust=True, progress=False
    )
    # yfinance multi-ticker: columns are MultiIndex (price_type, ticker)
    if isinstance(raw.columns, pd.MultiIndex):
        px = raw['Close']
    else:
        px = raw[['Close']] if 'Close' in raw.columns else raw

    px.index = pd.to_datetime(px.index)
    px_m = px.resample('ME').last()           # month-end close

    # Drop tickers with too much missing data
    min_obs = int(0.8 * len(px_m))
    ok = px_m.columns[px_m.notna().sum() >= min_obs]
    dropped = set(px_m.columns) - set(ok)
    if dropped:
        log.warning(f"Dropped {len(dropped)} tickers (>20% missing): {sorted(dropped)}")
    px_m = px_m[ok].ffill(limit=2)           # forward-fill at most 2 months
    log.info(f"Final universe: {px_m.shape[1]} stocks, "
             f"{px_m.index[0].date()} → {px_m.index[-1].date()}")
    return px_m


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------
def cs_momentum_signal(px_m: pd.DataFrame,
                        lb: int = LB_MONTHS,
                        skip: int = SKIP_MONTHS) -> pd.DataFrame:
    """
    Vol-normalised CS momentum: cumret[t-lb : t-skip] / (vol_lb * sqrt(lb-skip)).
    All computations on log-returns for additive composition.
    """
    logret = np.log(px_m / px_m.shift(1))
    # sum of (lb-skip) monthly log-returns, ending at t-skip
    cumret = logret.rolling(lb - skip).sum().shift(skip)
    vol    = logret.rolling(lb).std()
    denom  = vol * np.sqrt(lb - skip)
    return (cumret / denom).replace([np.inf, -np.inf], np.nan)


def tsmom_tanh_signal(px_m: pd.DataFrame,
                       lb: int = LB_MONTHS) -> pd.DataFrame:
    """
    tanh( cumret_12M / (vol_12M * sqrt(12)) ) — same family as crypto Strategy A.
    """
    logret = np.log(px_m / px_m.shift(1))
    cumret = logret.rolling(lb).sum()
    vol    = logret.rolling(lb).std()
    denom  = vol * np.sqrt(lb)
    return np.tanh((cumret / denom).replace([np.inf, -np.inf], np.nan))


# ---------------------------------------------------------------------------
# IC test
# ---------------------------------------------------------------------------
def cross_sectional_ic(signal: pd.DataFrame,
                        fwd_ret: pd.DataFrame) -> pd.Series:
    """Per-row Spearman rank correlation between signal and forward return."""
    common = signal.columns.intersection(fwd_ret.columns)
    sig, ret = signal[common], fwd_ret[common]
    idx = sig.index.intersection(ret.index)
    out = {}
    for t in idx:
        s = sig.loc[t].astype(float)
        r = ret.loc[t].astype(float)
        m = s.notna() & r.notna()
        if m.sum() < 10:            # need at least 10 stocks for meaningful rank corr
            continue
        rho, _ = stats.spearmanr(s[m].values, r[m].values)
        if np.isfinite(rho):
            out[t] = rho
    return pd.Series(out).sort_index()


def ic_summary(ic: pd.Series) -> dict:
    n        = len(ic)
    mean, sd = ic.mean(), ic.std(ddof=1)
    t        = mean / (sd / np.sqrt(n)) if sd > 0 and n > 1 else np.nan
    pct_pos  = float((ic > 0).mean())
    return {'ic_mean': float(mean), 'ic_std': float(sd),
            'ic_tstat': float(t), 'ic_n': int(n),
            'ic_pct_positive': pct_pos}


# ---------------------------------------------------------------------------
# Backtests
# ---------------------------------------------------------------------------
def bt_ls_quintile(signal: pd.DataFrame,
                    fwd_ret: pd.DataFrame,
                    cost_rt: float = COST_RT,
                    ann: int = ANN) -> tuple[pd.Series, dict]:
    """L/S quintile (top 20% long, bottom 20% short), equal-weight, monthly."""
    common = signal.columns.intersection(fwd_ret.columns)
    sig    = signal[common].dropna(how='all')
    ret    = fwd_ret[common]
    idx    = sig.index.intersection(ret.index)
    sig, ret = sig.loc[idx], ret.loc[idx]
    n_stocks = sig.shape[1]
    k = max(1, n_stocks // 5)          # quintile bucket size

    w = pd.DataFrame(0.0, index=sig.index, columns=sig.columns)
    for t in sig.index:
        s = sig.loc[t].dropna()
        if len(s) < 2 * k:
            continue
        ranked = s.rank(pct=True)      # percentile rank 0-1
        w.loc[t, ranked[ranked >= 0.8].index] = +1.0 / k   # top quintile: long
        w.loc[t, ranked[ranked <= 0.2].index] = -1.0 / k   # bot quintile: short

    gross    = (w * ret).sum(axis=1)
    turnover = (w - w.shift(1).fillna(0)).abs().sum(axis=1)
    net      = gross - turnover * (cost_rt / 2.0)

    sharpe  = float(net.mean() / net.std(ddof=1) * np.sqrt(ann)) if net.std(ddof=1) > 0 else np.nan
    equity  = (1 + net).cumprod()
    max_dd  = float((equity / equity.cummax() - 1.0).min())
    ann_ret = float(net.mean() * ann)
    return net, {
        'sharpe': sharpe, 'max_dd': max_dd, 'ann_ret': ann_ret,
        'n_stocks': int(n_stocks), 'quintile_k': int(k),
        'avg_turnover': float(turnover.mean()),
    }


def bt_tsmom_scaled(signal: pd.DataFrame,
                     fwd_ret: pd.DataFrame,
                     cost_rt: float = COST_RT,
                     ann: int = ANN) -> tuple[pd.Series, dict]:
    """TSMOM: each stock sized proportional to tanh signal, cross-stock average."""
    common = signal.columns.intersection(fwd_ret.columns)
    sig    = signal[common].dropna(how='all')
    ret    = fwd_ret[common]
    idx    = sig.index.intersection(ret.index)
    sig, ret = sig.loc[idx], ret.loc[idx]
    n_stocks = sig.shape[1]

    w = sig.fillna(0.0) / n_stocks          # avg leverage = tanh(x) / n ≤ 1/n per stock
    gross    = (w * ret).sum(axis=1)
    turnover = (w - w.shift(1).fillna(0)).abs().sum(axis=1)
    net      = gross - turnover * (cost_rt / 2.0)

    sharpe  = float(net.mean() / net.std(ddof=1) * np.sqrt(ann)) if net.std(ddof=1) > 0 else np.nan
    equity  = (1 + net).cumprod()
    max_dd  = float((equity / equity.cummax() - 1.0).min())
    ann_ret = float(net.mean() * ann)
    return net, {
        'sharpe': sharpe, 'max_dd': max_dd, 'ann_ret': ann_ret,
        'n_stocks': int(n_stocks), 'avg_turnover': float(turnover.mean()),
    }


def crash_stats(net: pd.Series,
                periods: dict,
                ann: int = ANN) -> dict:
    out = {}
    for name, (s, e) in periods.items():
        sub = net.loc[s:e]
        if len(sub) < 3:
            out[name] = {'note': 'insufficient data'}
            continue
        equity = (1 + sub).cumprod()
        dd     = float((equity / equity.cummax() - 1.0).min())
        sharpe = float(sub.mean() / sub.std(ddof=1) * np.sqrt(ann)) if sub.std(ddof=1) > 0 else np.nan
        cumret = float(equity.iloc[-1] - 1.0)
        out[name] = {'period': f'{s} → {e}', 'sharpe': round(sharpe, 3),
                     'max_dd': round(dd, 4), 'cum_ret': round(cumret, 4),
                     'n_obs': int(len(sub))}
    return out


def _gate(ic_t: float, covid_dd: float) -> str:
    ic_ok    = ic_t > 2.5
    crash_ok = covid_dd > -0.25
    if ic_ok and crash_ok:
        return 'PASS'
    elif ic_t > 1.5:
        return 'WEAK'
    return 'SKIP'


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> dict:
    log.info('=== JT Cross-Sectional Equity Momentum Feasibility ===')
    log.info(f'Universe: {len(UNIVERSE)} tickers | Period: {START} → {END}')

    px_m = fetch_prices(UNIVERSE, START, END)

    # Monthly log-returns
    ret_m   = np.log(px_m / px_m.shift(1)).dropna(how='all')

    # JT convention: signal at T predicts return at T+1.
    # Signal functions already apply the 1-month skip internally
    # (rolling(11).sum().shift(1)) — no additional external shift needed.
    # Forward return: shift ret_m back by 1 so fwd_ret_m[T] = ret_m[T+1].
    sig_cs    = cs_momentum_signal(px_m)
    sig_ts    = tsmom_tanh_signal(px_m)
    fwd_ret_m = ret_m.shift(-1)                 # T+1 return aligned to signal at T

    idx = ret_m.index
    sig_cs    = sig_cs.reindex(idx)
    sig_ts    = sig_ts.reindex(idx)
    fwd_ret_m = fwd_ret_m.reindex(idx)

    # IC
    log.info('Computing cross-sectional IC …')
    ic_cs = cross_sectional_ic(sig_cs, fwd_ret_m)
    ic_ts = cross_sectional_ic(sig_ts, fwd_ret_m)

    # Backtests
    log.info('Running backtests …')
    net_cs, bt_cs = bt_ls_quintile(sig_cs, fwd_ret_m)
    net_ts, bt_ts = bt_tsmom_scaled(sig_ts, fwd_ret_m)

    # Crash period analysis
    crash_cs = crash_stats(net_cs, CRASH_PERIODS)
    crash_ts = crash_stats(net_ts, CRASH_PERIODS)

    covid_dd_cs = crash_cs.get('COVID_2020', {}).get('max_dd', 0.0) or 0.0
    covid_dd_ts = crash_ts.get('COVID_2020', {}).get('max_dd', 0.0) or 0.0

    cs_stats = {'signal': 'jt_momentum_cs_monthly', 'universe': 'SPX large-cap ~70 stocks',
                'freq': 'monthly', 'cost_rt': COST_RT,
                'period_start': str(idx.min().date()), 'period_end': str(idx.max().date()),
                **ic_summary(ic_cs), **bt_cs, 'crashes': crash_cs}
    cs_stats['gate'] = _gate(cs_stats['ic_tstat'], covid_dd_cs)

    ts_stats = {'signal': 'tsmom_tanh_monthly', 'universe': 'SPX large-cap ~70 stocks',
                'freq': 'monthly', 'cost_rt': COST_RT,
                'period_start': str(idx.min().date()), 'period_end': str(idx.max().date()),
                **ic_summary(ic_ts), **bt_ts, 'crashes': crash_ts}
    ts_stats['gate'] = _gate(ts_stats['ic_tstat'], covid_dd_ts)

    results = {'momentum_cs': cs_stats, 'tsmom': ts_stats}
    RESULTS_PATH.write_text(json.dumps(results, indent=2))

    # ── Pretty print ────────────────────────────────────────────────────────
    for label, r in (('CS MOMENTUM 12M-1M (Jegadeesh-Titman L/S quintile)', cs_stats),
                     ('TSMOM TANH 12M (Moskowitz-style, full L/S)',          ts_stats)):
        print('\n' + '=' * 72)
        print(label)
        print('=' * 72)
        for k, v in r.items():
            if k == 'crashes':
                print(f'  {"crashes":<22}')
                for cn, cv in v.items():
                    if 'max_dd' in cv:
                        print(f'    {cn:<16} MaxDD={cv["max_dd"]:+.3f}  '
                              f'CumRet={cv["cum_ret"]:+.3f}  Sharpe={cv["sharpe"]:+.2f}')
                    else:
                        print(f'    {cn:<16} {cv.get("note", "")}')
            else:
                print(f'  {k:<22} {v}')
    print('=' * 72)

    return results


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log.exception('feasibility run failed')
        sys.exit(1)
