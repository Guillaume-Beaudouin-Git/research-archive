"""Volet 1 — anatomy of funded busts (baseline gate ON, low-check). Reads busts_baseline.csv.
Daily/max split, by sleeve, event-type (gap/flash/drift), regime concentration, timing, unique days."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parent
TAB = HERE / "tables"
LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]
CACHE = MAIN / "data/ftmo_portfolio/cache"

ev = pd.read_csv(TAB / "busts_baseline.csv", parse_dates=["date"])
runs = pd.read_csv(TAB / "runs_baseline.csv")
n_runs = len(runs)
print(f"=== FUNDED BUST ANATOMY (baseline gate ON, low-check) — {n_runs} runs, "
      f"{len(ev)} bust events, {ev.date.nunique()} UNIQUE bust days ===\n")

# --- 1. daily vs max-loss (which FTMO rule closes the account) ---
print("1. DAILY (−5%) vs MAX-LOSS (−10%):")
kc = ev.kind.value_counts()
for k in ["daily", "max_loss"]:
    c = int(kc.get(k, 0))
    print(f"   {k:9s}: {c:4d} events ({100*c/len(ev):4.1f}%)  "
          f"median day-loss ${ev[ev.kind==k].daily_loss.median():,.0f}" if c else f"   {k}: 0")
print(f"   -> {'DAILY dominates (fresh-day shocks)' if kc.get('daily',0)>kc.get('max_loss',0) else 'MAX-LOSS dominates (drift)'}")

# --- 2. by sleeve (dominant adverse leg) ---
print("\n2. BY SLEEVE (dominant adverse leg):")
for leg, c in ev.dom_leg.value_counts().items():
    onuniq = ev[ev.dom_leg == leg].date.nunique()
    print(f"   {leg:7s}: {c:4d} events ({100*c/len(ev):4.1f}%), {onuniq} unique days")

# --- 3. event type: gap/open vs intraday flash vs drift proxy ---
print("\n3. EVENT TYPE:")
at_open = ev.at_open.mean()
gap = ev.gap_day.mean()
print(f"   at-open (s0b0, overnight gap): {100*at_open:.1f}%   intraday: {100*(1-at_open):.1f}%")
print(f"   on a weekend/gap day: {100*gap:.1f}%")
# drift proxy: max_loss busts (bal_start<9500) = account already drawn down; daily (fresh) = shock
drift = (ev.kind == "max_loss").mean()
print(f"   drift-proxy (max_loss, account pre-drawn <9500): {100*drift:.1f}%  vs "
      f"fresh-shock (daily): {100*(1-drift):.1f}%")

# --- 4. regime concentration (vol at bust) ---
rets = pd.read_parquet(CACHE / "panel_rets.parquet")


def volpct(sym, dates):
    rv = rets[sym].rolling(20).std()
    pr = rv.rolling(504, min_periods=120).apply(lambda x: (x[-1] > x).mean(), raw=True).shift(1)
    return pr.reindex(pd.to_datetime(dates)).values


print("\n4. REGIME (dom-leg 20d realized-vol percentile at bust, causal):")
ev["volpct_dom"] = np.nan
for leg in LEGS:
    m = ev.dom_leg == leg
    if m.any():
        ev.loc[m, "volpct_dom"] = volpct(leg, ev.loc[m, "date"])
vp = ev["volpct_dom"].dropna()
print(f"   median vol-pct at bust: {vp.median():.2f} (0.50=typical)  "
      f">p80: {100*(vp>0.80).mean():.0f}%  >p90: {100*(vp>0.90).mean():.0f}%  <p50: {100*(vp<0.50).mean():.0f}%")
print(f"   -> {'CONCENTRATED in high vol' if (vp>0.80).mean()>0.4 else 'DIFFUSE across vol regimes'}")

# --- 5. timing + banked payouts ---
print("\n5. TIMING & BANKED PAYOUTS at bust:")
print(f"   life (trading-days to bust): median {ev.life.median():.0f}  "
      f"q25 {ev.life.quantile(.25):.0f}  q75 {ev.life.quantile(.75):.0f}  min {ev.life.min():.0f}")
print(f"   payouts banked at bust: median {ev.n_pay.median():.0f}  "
      f"frac with >=1 payout {100*(ev.n_pay>0).mean():.0f}%  median $ banked ${ev.wd_banked.median():,.0f}")

# --- 6. unique bust DAYS (the real dangerous events, de-duplicated) ---
uniq = ev.sort_values("life").drop_duplicates("date")
print(f"\n6. UNIQUE BUST DAYS ({len(uniq)}): the dangerous historical days")
uniq_by_leg = uniq.dom_leg.value_counts()
print("   by dom sleeve:", uniq_by_leg.to_dict())
print("   by year:", uniq.date.dt.year.value_counts().sort_index().to_dict())
top = uniq.assign(ym=uniq.date.dt.to_period("M")).ym.value_counts().head(8)
print("   worst months (most starts busted):", {str(k): int(v) for k, v in top.items()})
uniq[["date", "kind", "dom_leg", "daily_loss", "at_open", "gap_day", "volpct_dom"]].to_csv(
    TAB / "unique_bust_days.csv", index=False)
print("\n   saved unique_bust_days.csv")
