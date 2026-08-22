#!/usr/bin/env python3
"""session_C_combos — combinations vs their best NAKED brick (the decisive test;
prior: 0/5 combos beat naked → layering degrades). #1 regime-switch: VERIFY the
detector separates trend/MR BEFORE building. #3: two-sided FIRST (long-beta trap).
#5: check skew. GATE-0 FTMO-tradeable basket, daily (OOM-safe)."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"; OUT = f"{D}/skew_research/session_C_combos"


def load():
    px = {}
    fc = pd.read_csv(f"{D}/panels/ftmo_close.csv", index_col=0, parse_dates=True)
    for s in ["US500", "US100", "GER40"]: px[s] = fc[s]
    cp = pd.read_csv(f"{D}/panels/commodity_panel.csv", index_col=0, parse_dates=True)
    mac = pd.read_csv(f"{D}/panels/macro_etf_panel.csv", index_col=0, parse_dates=True)
    px["XAU"], px["XAG"] = mac["GLD"], cp["SLV"]
    px["BTC"] = pd.read_csv(f"{D}/panels/btc_full.csv", index_col=0, parse_dates=True)["BTC-USD"]
    px["ETH"] = pd.read_csv(f"{D}/panels/crypto_panel.csv", index_col=0, parse_dates=True)["ETHUSD"]
    df = pd.DataFrame(px); df.index = pd.to_datetime(df.index); return df.sort_index()


def agg(sig, rets):                       # equal-weight aggregate daily strat return
    return (sig.shift(1) * rets).mean(axis=1)


def rsi(p, n=14):
    d = p.diff(); up = d.clip(lower=0).rolling(n).mean(); dn = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100/(1 + up/dn.replace(0, np.nan))


def stt(x):
    x = np.asarray(x); x = x[x == x]; nz = x[x != 0]; s = nz.std(ddof=1)
    return (round(x.mean()/s*np.sqrt(252), 2), round(float(((x-x.mean())**3).mean()/x.std()**3), 2))  # (Sharpe, skew)


def main():
    df = load(); rets = df.pct_change().clip(-0.5, 0.5)
    trend = np.sign(sum(np.sign(df.pct_change(L)) for L in (60, 120, 250)))      # naked trend sign
    z = (np.log(df) - np.log(df).rolling(20).mean())/np.log(df).rolling(20).std()
    mr = -np.sign(z.where(z.abs() > 1, 0.0))                                      # naked MR fade
    tr_naked, mr_naked = agg(trend, rets), agg(mr, rets)
    print(f"NAKED bricks: trend Sharpe/skew {stt(tr_naked.values)} | MR {stt(mr_naked.values)}")

    # === #1 regime detector SEPARATION test (verify BEFORE building) ===
    ac = rets.rolling(60).apply(lambda s: pd.Series(s).autocorr(1), raw=False)    # lag-1 autocorr (>0 trending)
    lab_tr = (ac > 0).shift(1); lab_mr = (ac < 0).shift(1)
    # conditional mean daily return of each naked strat by regime label (pooled)
    tstrat = trend.shift(1)*rets; mstrat = mr.shift(1)*rets
    def cm(strat, lab): return round(float(strat.where(lab).stack().mean()*1e4), 2)
    print("\n#1 DETECTOR SEPARATION (lag-1 autocorr): does trend win in trend-regime & MR in MR-regime?")
    print(f"   trend-strat: in TREND-regime {cm(tstrat,lab_tr):+.2f}bps  vs MR-regime {cm(tstrat,lab_mr):+.2f}bps")
    print(f"   MR-strat   : in MR-regime   {cm(mstrat,lab_mr):+.2f}bps  vs TREND-regime {cm(mstrat,lab_tr):+.2f}bps")
    sep = (cm(tstrat,lab_tr) > cm(tstrat,lab_mr)) and (cm(mstrat,lab_mr) > cm(mstrat,lab_tr))
    print(f"   => detector {'SEPARATES — build switch' if sep else 'does NOT separate cleanly → switch not worth building'}")
    sw = trend.where(lab_tr, 0).fillna(0) + mr.where(lab_mr, 0).fillna(0)
    sw_ret = agg(sw, rets)
    print(f"   regime-switched combo Sharpe/skew {stt(sw_ret.values)}  | best naked = {max(stt(tr_naked.values)[0], stt(mr_naked.values)[0])}  -> {'BEATS' if stt(sw_ret.values)[0]>max(stt(tr_naked.values)[0],stt(mr_naked.values)[0]) else 'does NOT beat best naked'}")

    # === #2 double-timeframe alignment ===
    wk = np.sign(df.pct_change(25))                       # ~weekly trend
    combo2 = trend.where(np.sign(trend) == wk, 0)
    c2 = agg(combo2, rets)
    print(f"\n#2 daily+weekly aligned: combo {stt(c2.values)} | naked trend {stt(tr_naked.values)} -> {'BEATS' if stt(c2.values)[0]>stt(tr_naked.values)[0] else 'does NOT beat naked'}")

    # === #3 RSI-dip in uptrend — TWO-SIDED FIRST (beta trap) ===
    r = rsi(df); ma200 = df.rolling(200).mean()
    long_sig = ((r < 30) & (df > ma200)).astype(float)                 # buy dip in uptrend
    short_sig = -((r > 70) & (df < ma200)).astype(float)               # sell rip in downtrend
    lr, sr = agg(long_sig, rets), agg(short_sig, rets)
    print(f"\n#3 RSI-dip TWO-SIDED: LONG-in-uptrend {stt(lr.values)} | SHORT-in-downtrend {stt(sr.values)}")
    print(f"   => {'symmetric' if stt(sr.values)[0] > 0.3 else 'ASYMMETRIC — short side weak => LONG BETA in disguise, KILL'}")

    # === #4 trend + relative-strength confirmation ===
    rs = df.pct_change(60); rs_rank = rs.rank(axis=1)
    n = df.notna().sum(1); strong = rs_rank.ge((n.values[:, None]+1)/2, axis=0)   # above cross-sec median
    combo4 = trend.where((np.sign(trend) > 0) & strong | (np.sign(trend) < 0) & ~strong, 0)
    c4 = agg(combo4, rets)
    print(f"\n#4 trend + relative-strength: combo {stt(c4.values)} | naked trend {stt(tr_naked.values)} -> {'BEATS' if stt(c4.values)[0]>stt(tr_naked.values)[0] else 'does NOT beat naked'}")

    # === #5 Bollinger reversion + directional filter (skew check) ===
    m20, s20 = df.rolling(20).mean(), df.rolling(20).std()
    bb_rev = np.where(df < m20 - 2*s20, 1.0, np.where(df > m20 + 2*s20, -1.0, 0.0))
    bb_rev = pd.DataFrame(bb_rev, index=df.index, columns=df.columns)
    bb_naked = agg(bb_rev, rets)
    bb_filt = bb_rev.where(np.sign(bb_rev) == np.sign(trend), 0)        # only in trend direction
    bb_f = agg(bb_filt, rets)
    print(f"\n#5 Bollinger rev: naked {stt(bb_naked.values)} | +trend-filter {stt(bb_f.values)} (CHECK SKEW sign)")


if __name__ == "__main__":
    main()
