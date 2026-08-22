#!/usr/bin/env python3
"""crypto_intraday GATE-0 + AXIS #1 — same fil as ORB: does the SPREAD sweep the MOVE?
Data: BTCUSD_M1 (1-min, 2018-11..2026-05) with MT5 FLOATING spread column (pt=0.01,
flagged FTMO-LP-class proxy). Gate ratio = move-points / spread-points (POINT-SIZE-ROBUST).
Cost = measured floating spread at entry minute + commission 6.5 bps RT. Intraday-FLAT (no swap).
#1 FOMC/CPI reaction at delay-1 (L26); two-sided by spike sign; OOS pre/post-2023 (L12 low-N)."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"; OUT = f"{D}/crypto_intraday"
PT = 0.01            # BTCUSD MT5 point (digits=2). Gate uses ratio -> robust to this.
COMM_RT = 6.5        # commission bps round-trip


def load_min():
    df = pd.read_csv(f"{D}/panels/m5_indices/BTCUSD_M1.csv",
                     usecols=["timestamp_utc", "high", "low", "close", "spread"])
    df["dt"] = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns="timestamp_utc").set_index("dt").sort_index()
    df["spr_bps"] = df["spread"] * PT / df["close"] * 1e4     # spread in bps (pt-flagged)
    df["ret"] = df["close"].pct_change()
    return df


def gate0_spread_wall(df):
    s = df.loc[df["spread"] > 0, "spr_bps"]
    print("=== GATE-0 SPREAD WALL (bps, MT5 floating spread, FTMO-LP-class proxy) ===")
    print(f"  ALL minutes      : median {s.median():.1f}  p90 {s.quantile(.9):.1f}  p99 {s.quantile(.99):.1f}  p99.9 {s.quantile(.999):.1f}")
    # by year (regime)
    by = df[df.spread > 0].groupby(df[df.spread > 0].index.year)["spr_bps"].median()
    print("  median by year   :", {int(y): round(v, 1) for y, v in by.items()})
    # liquidation-cascade proxy = top-1% |ret| minutes (the L33 blowout that decides #2)
    hv = df[df["ret"].abs() > df["ret"].abs().quantile(.99)]
    print(f"  CASCADE proxy (top-1% |ret| min): spread median {hv['spr_bps'].median():.1f}  p90 {hv['spr_bps'].quantile(.9):.1f}  "
          f"| move/min median {hv['ret'].abs().median()*1e4:.0f}bps  -> move/spread ratio {hv['ret'].abs().median()*1e4/hv['spr_bps'].median():.1f}")
    return s.median()


def load_events():
    cal = pd.read_csv(f"{D}/panels/economic_calendar.csv")
    cal = cal[cal["event"].isin(["FOMC", "CPI"])].copy()
    cal["t0"] = pd.to_datetime(cal["datetime_utc"])
    return cal


def axis1_event_reaction(df, cal):
    """For each FOMC/CPI: instant spike (t0-1->t0+1, NOT capturable) vs post-delay-1
    continuation/reversion (t0+1->exit, capturable), net of spread@entry + commission."""
    idx = df.index
    rows = []
    for _, e in cal.iterrows():
        t0 = e["t0"]
        i = idx.searchsorted(t0)                       # first bar >= event time
        if i < 2 or i + 130 >= len(df):
            continue
        # require the bar to be within 3 min of the event (alignment sanity)
        if abs((idx[i] - t0).total_seconds()) > 180:
            continue
        c = df["close"].values
        pre = c[i - 1]                                  # price just before event
        spk1 = c[i + 1] / pre - 1                       # instant spike over event bar (NOT capturable)
        sgn = np.sign(spk1)
        if sgn == 0:
            continue
        entry = c[i + 1]                                # delay-1 entry (one bar after event bar, L26)
        spr_entry = df["spr_bps"].values[i + 1]
        out = {"event": e["event"], "year": t0.year, "spike_bps": spk1 * 1e4,
               "spr_entry_bps": spr_entry, "sgn": sgn}
        for h, lbl in [(30, "30m"), (60, "60m"), (120, "120m")]:
            fwd = c[i + 1 + h] / entry - 1
            cont = sgn * fwd * 1e4                       # continuation (trade in spike direction)
            net = cont - spr_entry - COMM_RT             # net of spread@entry + commission RT
            out[f"cont_{lbl}_gross"] = cont
            out[f"cont_{lbl}_net"] = net
        rows.append(out)
    return pd.DataFrame(rows)


def summ(ev, col_net, col_gross, lbl):
    n = len(ev)
    g = ev[col_gross]; net = ev[col_net]
    hit = (net > 0).mean()
    print(f"  {lbl:6s}: N={n}  gross {g.mean():+6.0f}bps  net {net.mean():+6.0f}bps (med {net.median():+5.0f})  "
          f"hit {hit*100:3.0f}%  | up-spike net {ev[ev.sgn>0][col_net].mean():+6.0f} (n{(ev.sgn>0).sum()})  "
          f"dn-spike net {ev[ev.sgn<0][col_net].mean():+6.0f} (n{(ev.sgn<0).sum()})")


def main():
    import os; os.makedirs(OUT, exist_ok=True)
    df = load_min()
    print(f"BTCUSD 1-min {df.index.min()} .. {df.index.max()}  n={len(df):,}\n")
    med_spread = gate0_spread_wall(df)

    cal = load_events()
    ev = axis1_event_reaction(df, cal)
    print(f"\n=== AXIS #1 — FOMC/CPI reaction, DELAY-1 entry, net of measured spread+comm ===")
    print(f"  events matched: {len(ev)}  (FOMC {sum(ev.event=='FOMC')}, CPI {sum(ev.event=='CPI')})")
    print(f"  spread @ entry minute (t0+1): median {ev.spr_entry_bps.median():.1f}bps  p90 {ev.spr_entry_bps.quantile(.9):.1f}bps")
    print(f"  instant spike (t0-1->t0+1, NOT capturable at delay-1): median |{ev.spike_bps.abs().median():.0f}|bps")
    print("  -- CONTINUATION (trade in spike direction), capturable from delay-1:")
    for h in ["30m", "60m", "120m"]:
        summ(ev, f"cont_{h}_net", f"cont_{h}_gross", h)
    # OOS decay
    print("  -- OOS decay (60m continuation net):")
    for lab, mask in [("pre-2023", ev.year < 2023), ("post-2023", ev.year >= 2023)]:
        sub = ev[mask]
        print(f"      {lab}: N={len(sub)}  net {sub['cont_60m_net'].mean():+.0f}bps  hit {(sub['cont_60m_net']>0).mean()*100:.0f}%")
    # gate ratio (point-size robust): median |spike| vs median entry spread
    ratio = ev.spike_bps.abs().median() / ev.spr_entry_bps.median()
    print(f"\n  GATE RATIO (instant spike / entry-spread) = {ratio:.1f}x  "
          f"| capturable 60m-continuation / spread = {ev.cont_60m_gross.median()/ev.spr_entry_bps.median():.1f}x")
    ev.to_csv(f"{OUT}/axis1_events.csv", index=False)

    # #3 US-open flow prior: BTC move & spread by UTC hour
    print("\n=== #3 prior — BTC by UTC hour (US cash open ~13:30 UTC): |move|/min & spread ===")
    h = df.copy(); h["hr"] = h.index.hour
    g = h.groupby("hr").agg(mv=("ret", lambda x: x.abs().median() * 1e4), spr=("spr_bps", "median"))
    for hr in [0, 8, 12, 13, 14, 15, 20]:
        if hr in g.index:
            print(f"   {hr:02d}:00 UTC: |move|/min {g.loc[hr,'mv']:.0f}bps  spread {g.loc[hr,'spr']:.1f}bps  ratio {g.loc[hr,'mv']/g.loc[hr,'spr']:.1f}")


if __name__ == "__main__":
    main()
