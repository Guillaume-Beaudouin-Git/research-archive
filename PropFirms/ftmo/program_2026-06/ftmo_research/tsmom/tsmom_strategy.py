#!/usr/bin/env python3
"""
tsmom_strategy.py — Diversified multi-asset trend-following for the FTMO 2-step.
Reference implementation: the first strategy in the research program to beat the
FTMO barrier (p(funded) ~54% @2x / ~71% @1.5x, OOS-validated, compliant).

STRATEGY (one paragraph)
------------------------
On a decorrelated multi-asset basket (1 equity index + gold + silver + oil + BTC +
ETH), take a TWO-SIDED time-series-momentum position in each instrument: long if the
blended trailing momentum is up, short if down. Size each position inversely to its
volatility (vol-targeting), scale the portfolio to a target vol, and apply two risk
overlays: an equity-curve gate (de-risk when the strategy's own equity is below its
100-day MA) and a portfolio vol de-risk. Hold with ~1.5-2x leverage, no time limit.

WHY IT PASSES THE FTMO BARRIER (where long-only betas failed)
-------------------------------------------------------------
It is TWO-SIDED: it SHORTS down-trends, so it makes money in 2008/2020/2022 instead of
bleeding long beta into the -10% floor. Diversification + vol-targeting + drawdown
control keep maxDD ~-14% (vs -50% for the betas). Single directional position per
instrument on decorrelated assets => FTMO-compliant (no opposing-correlated hedging).

COMPLIANCE
----------
One directional position per instrument; decorrelated basket (single equity) => never
holds opposing positions on highly correlated instruments => not the FTMO "hedging".
Low turnover (trend-following) => cost-robust.

DATA INPUTS (daily close, adjusted; FTMO-tradeable as CFDs)
-----------------------------------------------------------
  US500 (or NQ/US100)  -> ftmo_close.csv         (validated vs NQ databento, corr 0.997)
  GLD, SLV, USO        -> macro_etf_panel / commodity_panel  (ETF adjusted proxies)
  BTC-USD, ETHUSD      -> btc_full.csv / crypto_panel.csv    (2014+)
Deploy on FTMO as: US500, XAUUSD, XAGUSD, USOIL, BTCUSD, ETHUSD CFDs.

NO LOOK-AHEAD: every signal/overlay uses only trailing data and is .shift(1)-ed before
the return is earned.

Run:  python3 tsmom_strategy.py --data-dir /path/to/panels --out ./out
"""
from __future__ import annotations
import argparse, json, os
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")

# ----------------------------- frozen config ------------------------------- #
INSTRUMENTS = ["US500", "GLD", "SLV", "USO", "BTC", "ETH"]   # decorrelated, compliance-clean
LOOKBACKS   = (60, 120, 250)     # multi-lookback TSMOM (trading days)
THETA       = 0.34               # trend-strength filter on blended signal
VOL_PER_INST = 0.10              # per-instrument vol target
PORT_VOL    = 0.10               # portfolio vol target
COST_BPS    = 2.0                # round-trip cost per unit turnover (stress to 10-20)
EQ_GATE     = True               # de-risk below equity 100d MA
VOL_DERISK  = True               # de-risk on portfolio vol spikes
# FTMO 2-step
INIT, P1, P2, FLOOR, DAILY = 10_000., 1.10, 1.05, 9_000., 0.05


# ------------------------------- data -------------------------------------- #
def load_prices(data_dir: str) -> pd.DataFrame:
    px = {}
    fc = pd.read_csv(f"{data_dir}/ftmo_close.csv", index_col=0, parse_dates=True)
    px["US500"] = fc["US500"]
    cp = pd.read_csv(f"{data_dir}/commodity_panel.csv", index_col=0, parse_dates=True)
    mac = pd.read_csv(f"{data_dir}/macro_etf_panel.csv", index_col=0, parse_dates=True)
    px["GLD"], px["SLV"], px["USO"] = mac["GLD"], cp["SLV"], cp["USO"]
    px["BTC"] = pd.read_csv(f"{data_dir}/btc_full.csv", index_col=0, parse_dates=True)["BTC-USD"]
    px["ETH"] = pd.read_csv(f"{data_dir}/crypto_panel.csv", index_col=0, parse_dates=True)["ETHUSD"]
    df = pd.DataFrame(px); df.index = pd.to_datetime(df.index)
    return df.sort_index()


# ------------------------------- strategy ---------------------------------- #
def strategy_returns(px: pd.DataFrame, inst=INSTRUMENTS, lookbacks=LOOKBACKS, theta=THETA,
                     port_vol=PORT_VOL, cost_bps=COST_BPS, eq_gate=EQ_GATE, vol_derisk=VOL_DERISK):
    px = px[inst].dropna(how="all")
    rets = px.pct_change().clip(-0.5, 0.5)
    rv = rets.rolling(60).std() * np.sqrt(252)                       # trailing realized vol
    sig = sum(np.sign(px.pct_change(L)) for L in lookbacks) / len(lookbacks)   # blended TSMOM
    sig = sig.where(sig.abs() >= theta, 0.0)                          # trend-strength filter
    pos = (sig * (VOL_PER_INST / rv).clip(upper=5.0)).shift(1)        # vol-targeted, causal
    gross = (pos * rets).sum(axis=1)
    pv = gross.rolling(60).std() * np.sqrt(252)
    port = (gross * (port_vol / pv).clip(upper=3.0).shift(1)).fillna(0.0)
    port -= pos.diff().abs().sum(axis=1) * cost_bps * 1e-4            # turnover cost
    if vol_derisk:
        rvol = port.rolling(20).std() * np.sqrt(252)
        port *= (port_vol / rvol).clip(upper=1.0).shift(1).fillna(1.0)
    if eq_gate:
        eq = (1 + port).cumprod()
        g = (eq > eq.rolling(100).mean()).astype(float).shift(1).fillna(1.0)
        port *= (0.4 + 0.6 * g)                                       # 40% below MA, 100% above
    return port.dropna()


# --------------------------- FTMO first-passage ---------------------------- #
def first_passage(sr: np.ndarray, L: float, cap=1260, step=4):
    """Contiguous real-path 2-step first-passage. cap = max horizon (trading days)."""
    N = len(sr); starts = np.arange(0, N - 5, step)
    funded = bust = 0; ttf = []
    for a in starts:
        eq, i, end, ok = INIT, a, min(a + cap, N), None
        while i < end:
            c = L * sr[i]
            if c <= -DAILY or eq * (1 + c) < FLOOR: bust += 1; ok = False; break
            eq *= 1 + c
            if eq >= INIT * P1: ok = True; break
            i += 1
        if ok is not True: continue
        d1 = i - a; eq = INIT; i += 1
        while i < end:
            c = L * sr[i]
            if c <= -DAILY or eq * (1 + c) < FLOOR: bust += 1; break
            eq *= 1 + c
            if eq >= INIT * P2: funded += 1; ttf.append(d1 + (i - a - d1)); break
            i += 1
    n = len(starts)
    return dict(L=L, p_funded=round(funded/n, 3), pct_bust=round(bust/n, 3),
                median_months=round(float(np.median(ttf))/21, 1) if ttf else None)


def p_pass_table(sr, levs=(1.5, 2, 3, 4, 6), months=(3, 6, 9, 12, 18, 24, 36), cap=1260, step=8):
    N = len(sr); starts = np.arange(0, N - 5, step); rows = {}
    for L in levs:
        ttf = []; bust = 0
        for a in starts:
            eq, i, end, ok = INIT, a, min(a+cap, N), None
            while i < end:
                c = L*sr[i]
                if c <= -DAILY or eq*(1+c) < FLOOR: bust += 1; ok = False; break
                eq *= 1+c
                if eq >= INIT*P1: ok = True; break
                i += 1
            if ok is not True: continue
            d1 = i-a; eq = INIT; i += 1
            while i < end:
                c = L*sr[i]
                if c <= -DAILY or eq*(1+c) < FLOOR: bust += 1; break
                eq *= 1+c
                if eq >= INIT*P2: ttf.append(i-a); break
                i += 1
        ttf = np.array(ttf); n = len(starts)
        rows[L] = {f"{m}mo": round(float((ttf <= m*21).sum())/n, 3) for m in months}
        rows[L]["terminal"] = round(len(ttf)/n, 3); rows[L]["bust"] = round(bust/n, 3)
    return rows


def metrics(sr):
    x = np.asarray(sr); nz = x[x != 0]; s = nz.std(ddof=1)
    eq = np.cumprod(1 + x); dd = (eq/np.maximum.accumulate(eq) - 1).min()
    return dict(ann_ret_pct=round(x.mean()*252*100, 1), sharpe=round(x.mean()/s*np.sqrt(252), 2),
                skew=round(float(((x-x.mean())**3).mean()/s**3), 2), maxdd_pct=round(dd*100, 1),
                t_stat=round(x.mean()/s*np.sqrt(len(nz)), 2),
                worst_day_pct=round(x.min()*100, 2), best_day_pct=round(x.max()*100, 2))


def stress_suite(px):
    base = strategy_returns(px)
    out = {"baseline": dict(metrics=metrics(base.values),
                            fp_1_5=first_passage(base.values, 1.5, step=8),
                            fp_2=first_passage(base.values, 2.0, step=8))}
    variants = {"cost_10bps": dict(cost_bps=10), "cost_20bps": dict(cost_bps=20),
                "no_crypto": dict(inst=["US500", "GLD", "SLV", "USO"]),
                "lookbacks_50_100_200": dict(lookbacks=(50, 100, 200)),
                "no_trend_filter": dict(theta=0.0)}
    for name, kw in variants.items():
        r = strategy_returns(px, **kw)
        out[name] = dict(metrics=metrics(r.values), fp_1_5=first_passage(r.values, 1.5, step=10))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/sessions/affectionate-epic-faraday/mnt/data/panels")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--full", action="store_true", help="also run p_pass table + stress suite")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    px = load_prices(a.data_dir)
    port = strategy_returns(px); port.to_csv(f"{a.out}/strategy_returns.csv")
    res = dict(period=f"{port.index.min().date()}..{port.index.max().date()}",
               n_days=len(port), metrics=metrics(port.values),
               fp={f"{L}x": first_passage(port.values, L, step=6) for L in (1.5, 2, 3)})
    by = port.groupby(port.index.year).apply(lambda x: round((np.prod(1+x.values)-1)*100, 1))
    res["by_year"] = {int(y): float(v) for y, v in by.items()}
    if a.full:
        res["p_pass_table"] = p_pass_table(port.values)
        res["stress"] = stress_suite(px)
    json.dump(res, open(f"{a.out}/results.json", "w"), indent=2, default=str)
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
