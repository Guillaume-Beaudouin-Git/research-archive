#!/usr/bin/env python3
"""Phase 1 — dated mechanical flows. Testable on data: NFP/CPI pre-event drift
(+ pre-FOMC comparison/overlap) and month-end equity rebalancing (perf-conditioned).
Treasury-auction / futures-roll / expiry-pinning: characterized/cited (no calendar/OI data).
Daily only (OOM-safe). Pre-event = run-up exiting the close BEFORE the event (flat overnight)."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"


def stt(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; s = x.std(ddof=1)
    return dict(n=int(len(x)), mean_bps=round(float(x.mean()*1e4), 1),
                t=round(float(x.mean()/s*np.sqrt(len(x))), 2) if s > 0 and len(x) > 2 else 0,
                skew=round(float(((x-x.mean())**3).mean()/s**3), 2) if s > 0 and len(x) > 2 else 0,
                hit=round(float((x > 0).mean()), 2))


def load():
    spx = pd.read_csv(f"{D}/panels/ftmo_close.csv", index_col=0, parse_dates=True)["US500"].dropna()
    cal = pd.read_csv(f"{D}/panels/economic_calendar.csv"); cal["date"] = pd.to_datetime(cal["date"])
    return spx, cal


def pre_event_drift(spx, dates, W):
    """run-up return over the W trading days ending the close BEFORE the event (flat overnight)."""
    idx = spx.index; out = []
    for d in dates:
        pos = idx.searchsorted(pd.Timestamp(d))
        if pos - 1 - W < 0 or pos - 1 >= len(idx): continue
        out.append(spx.iloc[pos-1]/spx.iloc[pos-1-W] - 1)
    return np.array(out)


def main():
    spx, cal = load()
    print(f"US500 {spx.index.min().date()}..{spx.index.max().date()} | calendar {cal['date'].min().date()}..{cal['date'].max().date()}")
    ev = {e: cal[cal["event"] == e]["date"].tolist() for e in ["FOMC", "NFP", "CPI"]}
    print({e: len(v) for e, v in ev.items()}, "events")

    print("\n=== #1 NFP/CPI drift (pre-FOMC twins) — pre-event run-up, long, flat overnight ===")
    for W in (1, 3):
        print(f"  -- {W}-day run-up before event --")
        for e in ["FOMC", "NFP", "CPI"]:
            print(f"     {e:5s}:", stt(pre_event_drift(spx, ev[e], W)))
    # overlap: are NFP/CPI just pre-FOMC? (events within +-2 trading days of an FOMC)
    idx = spx.index; fomc_pos = set(idx.searchsorted(pd.Timestamp(d)) for d in ev["FOMC"])
    for e in ["NFP", "CPI"]:
        pos = [idx.searchsorted(pd.Timestamp(d)) for d in ev[e]]
        near = sum(any(abs(p-f) <= 2 for f in fomc_pos) for p in pos)
        print(f"  overlap: {near}/{len(pos)} {e} events within +-2 trading days of an FOMC (distinct signal if low)")

    print("\n=== #5 Month-end equity rebalancing (perf-conditioned, last 3 trading days) ===")
    r = spx.pct_change(); ym = spx.index.to_period("M")
    df = pd.DataFrame({"r": r, "ym": ym}); df["tdom"] = df.groupby("ym").cumcount()+1
    nmax = df.groupby("ym")["tdom"].transform("max"); df["rtdom"] = nmax - df["tdom"] + 1
    last3 = df["rtdom"] <= 3
    # month-to-date return through day -4 (causal, excludes the last-3 window)
    mtd = df["r"].where(df["rtdom"] > 3).groupby(df["ym"]).transform(lambda x: (1+x.fillna(0)).cumprod()-1)
    sig = -np.sign(mtd)                      # rebalance TOWARD the underperformer = fade the month
    plain = df["r"].where(last3)             # plain long last-3 (TOM-equity, archived dead)
    cond = (sig*df["r"]).where(last3)        # perf-conditioned fade
    print("  plain long last-3-days (archived TOM-equity):", stt(plain.dropna().values))
    print("  perf-conditioned FADE last-3-days (new angle):", stt(cond.dropna().values))

    print("\n=== #2/#3/#4 — characterized/cited (no clean data) ===")
    print("  #2 Treasury auction cycle: TLT/IEF available BUT no auction calendar in data -> cannot test;")
    print("     + bond tradeability on FTMO (same flag as month-end-bond). CHARACTERIZE only.")
    print("  #3 Futures roll: mechanically a COST you pay (front->next), captured by liquidity providers, not retail -> not an edge. CITE.")
    print("  #4 Expiry/pinning: needs options open-interest (not in data); archive quad-witching = NEGATIVE (paquet 4) -> mitigated prior. CITE.")


if __name__ == "__main__":
    main()
