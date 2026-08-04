"""Q4 — tail modelability of J1.

The cleanroom simulator sees `sim_m5_repaired.parquet` = M5 **CLOSE ONLY** (one float
per bar, no OHLC). So by construction it cannot see any excursion that lives inside an
M5 bar. This script quantifies that blind spot against true M1 OHLC
(`data/deep_history_utc/USDJPY_M1.csv`, true UTC), on the day grid the account uses
(Europe/Prague, FTMO's 00:00 daily reset).

Also: L60 zero-range audit of the M1 series, daily skew/kurtosis of the sleeve at
deployed leverage, and the deterministic move-to-breach at the 12x leg cap.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from j1_lib import load_panels, sleeve_returns, sharpe, RT_BPS_USDJPY_ALLIN, VM_DEPLOYED

SCRATCH = Path("<SCRATCH>"
               "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/j1cache")
M1 = "<HOME>/Desktop/Algo_claude/data/deep_history_utc/USDJPY_M1.csv"
DAILY_CACHE = SCRATCH / "usdjpy_daily_prague.parquet"


def build_daily():
    if DAILY_CACHE.exists():
        return pd.read_parquet(DAILY_CACHE)
    parts, zr = [], []
    it = pd.read_csv(M1, usecols=["timestamp_utc", "open", "high", "low", "close"],
                     chunksize=1_000_000)
    for c in it:
        c["timestamp_utc"] = pd.to_datetime(c["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
        c = c[c.timestamp_utc >= pd.Timestamp("2013-09-01")]
        if not len(c):
            continue
        c = c.set_index("timestamp_utc").tz_localize("UTC").tz_convert("Europe/Prague")
        zr.append(pd.DataFrame({"y": c.index.year, "zero": (c.high == c.low).astype(int),
                                "hlc": ((c.high == c.low) & (c.low == c.close)).astype(int)}))
        d = c.index.normalize()
        g = c.groupby(d)
        m5c = c["close"].resample("5min").last().dropna()
        g5 = m5c.groupby(m5c.index.normalize())
        part = pd.DataFrame({
            "open": g["open"].first(), "close": g["close"].last(),
            "low": g["low"].min(), "high": g["high"].max(),
            "m5_lo": g5.min(), "m5_hi": g5.max(),
            "n_m1": g.size(),
        })
        parts.append(part)
    df = pd.concat(parts)
    df = df.groupby(level=0).agg({"open": "first", "close": "last", "low": "min",
                                  "high": "max", "m5_lo": "min", "m5_hi": "max",
                                  "n_m1": "sum"})
    z = pd.concat(zr)
    print("### L60 zero-range audit, USDJPY M1 (Dukascopy deep_history_utc)")
    print(z.groupby("y")[["zero", "hlc"]].mean().mul(100).round(2).tail(14).to_string())
    print(f"  pooled: high==low {z.zero.mean()*100:.2f} % | high==low==close "
          f"{z.hlc.mean()*100:.2f} %  (N={len(z):,})")
    df.index = df.index.tz_localize(None)
    df.to_parquet(DAILY_CACHE)
    return df


d = build_daily()
d = d.loc["2013-10-01":]
d = d[d.n_m1 > 200]

# ------------------------------------------------ sim-visible vs true excursion
# long position, adverse = downside from the day's opening price
true_mae = d["low"] / d["open"] - 1.0            # M1 low  (reality)
sim_mae = d["m5_lo"] / d["open"] - 1.0           # M5 close only (simulator's view)
gap = sim_mae - true_mae                          # >=0, the invisible part

print("\n" + "=" * 78)
print("### Q4a — WHAT THE SIMULATOR CANNOT SEE (M5-close vs M1-low, long side)")
print("=" * 78)
print(f"N days = {len(d)}   {d.index[0].date()} -> {d.index[-1].date()}")
q = [50, 90, 99, 99.5, 99.9, 100]
tab = pd.DataFrame({
    "M1 low (true) %": [np.percentile(true_mae, 100 - x) * 100 for x in q],
    "M5 close (sim) %": [np.percentile(sim_mae, 100 - x) * 100 for x in q],
}, index=[f"p{x}" for x in q])
tab["understated by"] = (tab["M5 close (sim) %"] / tab["M1 low (true) %"] - 1) * 100
print(tab.round(3).to_string())
print(f"\n  mean invisible depth       : {gap.mean()*1e4:.2f} bps")
print(f"  p99 invisible depth        : {np.percentile(gap, 99)*1e4:.2f} bps")
print(f"  max invisible depth        : {gap.max()*1e4:.2f} bps "
      f"({d.index[gap.argmax()].date()})")
print(f"  worst true day             : {true_mae.min()*100:.3f} % "
      f"({d.index[true_mae.argmin()].date()})")

# ------------------------------------------------ breach frontier at the leg cap
print("\n" + "=" * 78)
print("### Q4b — MOVE-TO-BREACH vs THE 12x LEG CAP (daily -5% on a $10k account)")
print("=" * 78)
for lev, tag in [(18.05, "margin cap 60% / 3.333% rate (pre-v2.8)"),
                 (16.80, "REALISED at the 2026-07-02 breach"),
                 (12.00, "v2.8 leg_lev_cap")]:
    need = 0.05 / lev
    n_true = int((true_mae <= -need).sum())
    n_sim = int((sim_mae <= -need).sum())
    print(f"  {lev:>5.2f}x  ({tag})")
    print(f"          breach needs USDJPY {-need*100:.3f} %  |  days breached: "
          f"TRUE(M1) {n_true} ({n_true/len(d)*252:.1f}/yr)  "
          f"SIM(M5 close) {n_sim} ({n_sim/len(d)*252:.1f}/yr)  "
          f"-> sim misses {100*(1-n_sim/max(n_true,1)):.0f} %")

# restrict to days the sleeve is actually long
px, rets, sL, sS, mu, rt = load_panels()
g, n_, w = sleeve_returns(px, rets, sL, sS, mu, "long", RT_BPS_USDJPY_ALLIN)
onmask = (w.reindex(d.index) > 0).fillna(False)
print(f"\n  restricted to the {int(onmask.sum())} days the sleeve is ACTUALLY LONG:")
for lev in (16.80, 12.00):
    need = 0.05 / lev
    nt = int((true_mae[onmask] <= -need).sum())
    ns = int((sim_mae[onmask] <= -need).sum())
    print(f"    {lev:>5.2f}x -> TRUE {nt} days ({nt/onmask.sum()*252:.1f}/yr)  "
          f"SIM {ns} days ({ns/onmask.sum()*252:.1f}/yr)")

# ------------------------------------------------ sleeve daily moments
print("\n" + "=" * 78)
print("### Q4c — DAILY MOMENTS OF THE SLEEVE (L39: report daily AND monthly)")
print("=" * 78)
r = n_.loc["2013-10-01":].dropna()
for tag, s in [("research scale (w as built)", r),
               (f"deployed scale (x vm {VM_DEPLOYED:.0f})", r * VM_DEPLOYED)]:
    eq = (1 + s.clip(lower=-0.999)).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    print(f"  {tag}")
    print(f"    daily  vol {s.std()*np.sqrt(252)*100:6.2f}%/yr  skew {s.skew():+.3f}  "
          f"exkurt {s.kurtosis():.2f}  SR {sharpe(s):+.3f}  MaxDD {dd*100:.1f}%")
    m = s.resample("ME").sum()
    print(f"    monthly skew {m.skew():+.3f}  exkurt {m.kurtosis():.2f}")
    print(f"    worst 5 sessions: {', '.join(f'{v*100:.2f}%' for v in s.nsmallest(5))}")
    print(f"    p(daily <= -5%) = {(s <= -0.05).mean()*100:.2f} %  "
          f"({int((s<=-0.05).sum())} days)")

# gaussian vs empirical tail at deployed scale
s = r * VM_DEPLOYED
z = (s - s.mean()) / s.std()
print(f"\n  tail-fatness check at vm14: empirical p(z<-3) = {(z<-3).mean()*100:.3f} % "
      f"vs gaussian 0.135 %  -> x{(z<-3).mean()/0.00135:.1f}")
print(f"                              empirical p(z<-4) = {(z<-4).mean()*100:.3f} % "
      f"vs gaussian 0.003 %  -> x{max((z<-4).mean(),1e-9)/0.0000317:.1f}")

# the 2026-07-02 style event: worst intraday gap-downs on long days
print("\n  10 deepest TRUE intraday adverse excursions on sleeve-long days:")
sub = pd.DataFrame({"true": true_mae[onmask], "sim": sim_mae[onmask]}).nsmallest(10, "true")
sub["equity@12x %"] = sub["true"] * 12 * 100
sub["equity@16.8x %"] = sub["true"] * 16.8 * 100
sub["sim sees %"] = sub["sim"] * 100
print((sub[["true", "sim", "equity@12x %", "equity@16.8x %"]] * [100, 100, 1, 1]
       ).round(3).to_string())
