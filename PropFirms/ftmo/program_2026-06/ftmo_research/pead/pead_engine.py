#!/usr/bin/env python3
"""PEAD — post-earnings-announcement drift. Event study (existence) + deployable
long-only basket + FTMO first-passage. Causal: enter the trading day AFTER the
announcement (surprise is public), hold H days. Market-adjusted CAR vs SPY."""
import numpy as np, pandas as pd

D = "/sessions/affectionate-epic-faraday/mnt/data"


def load():
    px = pd.read_csv(f"{D}/panels/single_stocks.csv", index_col=0, parse_dates=True).sort_index()
    spy = pd.read_csv(f"{D}/panels/equity_close2.csv", index_col=0, parse_dates=True)["SPY"].sort_index()
    earn = pd.read_csv(f"{D}/panels/earnings_dates.csv")
    earn["date"] = pd.to_datetime(earn["date"], errors="coerce")
    earn["surprise_pct"] = pd.to_numeric(earn["surprise_pct"], errors="coerce")
    earn = earn.dropna(subset=["date"])
    return px, spy, earn


def event_study(px, spy, earn, H=40):
    """Per event: forward H-day market-adjusted CAR, entering the day AFTER announcement."""
    spy = spy.reindex(px.index).ffill()
    rows = []
    for tk, g in earn.groupby("ticker"):
        if tk not in px.columns:
            continue
        s = px[tk].dropna()
        idx = s.index
        for _, r in g.iterrows():
            ed, sp = r["date"], r["surprise_pct"]
            a = idx.searchsorted(ed, side="right")   # first trading day strictly AFTER announcement
            if a < 2 or a + H >= len(idx):
                continue
            d0, dH = idx[a], idx[a + H]
            stock = s.iloc[a + H] / s.iloc[a] - 1.0
            mkt = spy.asof(dH) / spy.asof(d0) - 1.0
            react = s.iloc[a] / s.iloc[a - 1] - 1.0       # announcement reaction (gap)
            rows.append((tk, d0, sp, react, float(stock - mkt)))
    return pd.DataFrame(rows, columns=["tk", "date", "surprise", "react", "CAR"])


def summ(c, lab):
    c = c[~np.isnan(c)]
    if len(c) < 5: return f"{lab}: n<5"
    t = c.mean() / c.std(ddof=1) * np.sqrt(len(c))
    return f"{lab}: n={len(c):5d}  meanCAR {c.mean()*100:+.2f}%  t {t:+.2f}  win {(c>0).mean()*100:.0f}%"


def main():
    px, spy, earn = load()
    print(f"universe {px.shape[1]} stocks {px.index[0].date()}..{px.index[-1].date()} | events {len(earn)}")
    for H in (20, 40, 60):
        ev = event_study(px, spy, earn, H=H)
        ev = ev.dropna(subset=["CAR"])
        pos = ev[ev["surprise"] > 0]["CAR"]; neg = ev[ev["surprise"] < 0]["CAR"]
        spr = pos.mean() - neg.mean()
        ts = (pos.mean()-neg.mean())/np.sqrt(pos.var(ddof=1)/len(pos)+neg.var(ddof=1)/len(neg))
        print(f"\n=== H={H} days, market-adjusted CAR ===")
        print("  " + summ(pos.values, "surprise>0"))
        print("  " + summ(neg.values, "surprise<0"))
        print(f"  LONG-SHORT spread (pos-neg): {spr*100:+.2f}%  t {ts:+.2f}")
        # by surprise quintile (monotonic drift?)
        evs = ev.dropna(subset=["surprise"]).copy()
        evs["q"] = pd.qcut(evs["surprise"], 5, labels=False, duplicates="drop")
        qm = evs.groupby("q")["CAR"].mean() * 100
        print("  CAR by surprise quintile (low->high):", [f"{v:+.2f}" for v in qm.values])
        # alternative signal: announcement-reaction sign
        rp = ev[ev["react"] > 0]["CAR"]; rn = ev[ev["react"] < 0]["CAR"]
        print(f"  by REACTION sign: react>0 meanCAR {rp.mean()*100:+.2f}% (n{len(rp)}) | react<0 {rn.mean()*100:+.2f}% (n{len(rn)})")


if __name__ == "__main__":
    main()
