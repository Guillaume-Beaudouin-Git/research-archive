#!/usr/bin/env python3
"""Mechanism-justified selectivity — #1 trend-by-class, #2 crypto-only trend,
#4 day-of-week (mechanism-first), #5 commodity seasonality (the archive keeper,
train/OOS). Profile lens: skew + decorrelation + ADDITIONALITY to TSMOM. GATE-0
FTMO-tradeable. Daily only (OOM-safe). #3 session-forex handled separately."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"; OUT = f"{D}/skew_research/session_basic_trend"


def col(path, name):
    try:
        return pd.read_csv(f"{D}/panels/{path}", index_col=0, parse_dates=True)[name]
    except Exception:
        return None


def load():
    px = {}
    fc = pd.read_csv(f"{D}/panels/ftmo_close.csv", index_col=0, parse_dates=True)
    idx = {s: fc[s] for s in ["US500", "US100", "GER40"]}
    crypto = {"BTC": col("btc_full.csv", "BTC-USD"), "ETH": col("crypto_panel.csv", "ETHUSD")}
    # FTMO-tradeable commodities (CFDs): natgas, crude, brent, soybean, coffee, cocoa, metals
    cmd = {}
    for nm, p in [("NatGas", ("commodity_panel.csv","UNG")), ("CrudeWTI", ("commodity_panel.csv","USO")),
                  ("Brent", ("softs_metals.csv","UKOIL")), ("Soybean", ("softs_metals.csv","SOYBEAN")),
                  ("Coffee", ("softs_metals.csv","COFFEE")), ("Cocoa", ("softs_metals.csv","COCOA")),
                  ("Silver", ("commodity_panel.csv","SLV")), ("Gold", ("macro_etf_panel.csv","GLD")),
                  ("Platinum", ("softs_metals.csv","XPTUSD")), ("Palladium", ("commodity_panel.csv","PALL"))]:
        s = col(*p)
        if s is not None: cmd[nm] = s
    def mk(d): m = pd.DataFrame(d); m.index = pd.to_datetime(m.index); return m.sort_index()
    return mk(idx), mk(crypto), mk(cmd)


def trend_class(px):
    rets = px.pct_change().clip(-0.5, 0.5); rv = rets.rolling(60).std()*np.sqrt(252)
    sig = sum(np.sign(px.pct_change(L)) for L in (60, 120, 250))/3
    pos = (sig*(0.10/rv).clip(upper=5)).shift(1)
    g = (pos*rets).sum(1); k = px.shape[1]
    return (g/k).dropna()


def stt(x):
    x = np.asarray(x); x = x[x == x]; nz = x[x != 0]; s = nz.std(ddof=1)
    return dict(sharpe=round(x.mean()/s*np.sqrt(252), 2), skew=round(float(((x-x.mean())**3).mean()/x.std()**3), 2))


def main():
    idx, crypto, cmd = load()
    ts = pd.read_csv(f"{D}/ftmo_research/tsmom/chosen_returns.csv", index_col=0, parse_dates=True).iloc[:,0]
    eq = idx.pct_change().mean(1)
    def corr(a, b): j = pd.concat([a, b], axis=1).dropna(); return round(j.iloc[:,0].corr(j.iloc[:,1]), 2)

    print("=== #1/#2 TREND BY CLASS (where does trend work? + additionality to TSMOM) ===")
    for nm, p in [("Indices", idx), ("Commodities", cmd), ("Crypto (BTC/ETH only)", crypto)]:
        s = trend_class(p); st = stt(s.values)
        print(f"  {nm:22s}: Sharpe {st['sharpe']:+.2f}  daily-skew {st['skew']:+.2f}  corr->equity {corr(s,eq):+.2f}  corr->TSMOM {corr(s,ts):+.2f}")
    print("  (crypto/commodity trend is a SUBSET of TSMOM's universe -> high corr to TSMOM = redundant, not a new brick)")

    print("\n=== #5 COMMODITY SEASONALITY (archive keeper) — TRAIN 06-15 -> OOS 16-26 (no mining) ===")
    rets = cmd.pct_change().clip(-0.3, 0.3)
    tr = rets[rets.index.year <= 2015]; oos_idx = rets.index.year >= 2016
    seas = tr.groupby(tr.index.month).mean()              # train month-of-year mean per commodity
    sign = np.sign(seas)                                   # seasonal direction (mechanism: prod/demand cycle)
    pos = pd.DataFrame(index=rets.index, columns=rets.columns, dtype=float)
    for m in range(1, 13):
        pos.loc[pos.index.month == m] = sign.loc[m].values
    pos = pos.shift(1)
    daily_oos = (pos*rets)[oos_idx].mean(1).dropna()
    st = stt(daily_oos.values)
    print(f"  OOS 2016-26: Sharpe {st['sharpe']:+.2f}  daily-skew {st['skew']:+.2f}  corr->equity {corr(daily_oos,eq):+.2f}  corr->TSMOM {corr(daily_oos,ts):+.2f}")
    # train-period for reference
    daily_tr = (pos*rets)[~oos_idx].mean(1).dropna()
    print(f"  TRAIN 06-15: Sharpe {stt(daily_tr.values)['sharpe']:+.2f} (in-sample, for reference)")
    daily_oos.to_csv(f"{OUT}/commodity_seasonality_oos.csv")

    print("\n=== #4 DAY-OF-WEEK (mechanism-FIRST; very weak prior R2=0.14%) ===")
    allinst = pd.concat([idx, crypto, cmd], axis=1)
    r = allinst.pct_change()
    best = None
    for c in allinst.columns:
        x = r[c].dropna(); g = x.groupby(x.index.dayofweek)
        for dow, gg in g:
            t = gg.mean()/gg.std()*np.sqrt(len(gg))
            if best is None or abs(t) > abs(best[2]): best = (c, dow, t, gg.mean()*1e4)
    print(f"  strongest day-of-week effect across all instruments: {best[0]} day{best[1]} t={best[2]:+.2f} ({best[3]:+.1f}bps)")
    print("  (no pre-specified mechanism -> a posteriori cut = mining; weak prior confirmed -> not pursued)")


if __name__ == "__main__":
    main()
