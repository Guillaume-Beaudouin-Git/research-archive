"""
Event-driven preliminary (FROZEN pre-reg). Aligns 5-min bars to each US release,
tests: HEV-1 release-bar loads on surprise (control), HEV-2 tradable post-release
continuation (two-sided + regime split + net), HEV-4 release-bar excursion / gap-through-stop.
Reimplemented engine -> POSITIVE = candidate only; NEGATIVE = definitive.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE.parents[0]))  # reach the engine package
DEEP = REPO / "data" / "deep_history_utc"
CAL = DEEP / "calendar" / "economic_calendar_2018_2026_full.csv"
INSTR = ["US500", "US100", "XAUUSD"]
DIGITS = {"US500": 2, "US100": 2, "XAUUSD": 2}  # MT5 point = 10**-digits
EVENTS = {"CPI": "Inflation Rate MoM", "NFP": "Non Farm Payrolls", "FOMC": "Fed Interest Rate Decision"}
N_TRIALS = 110
BARS_PER_YEAR_EVENT = {"CPI": 12.0, "NFP": 12.0, "FOMC": 8.0}


def load5(sym):
    df = pd.read_csv(DEEP / f"{sym}_M1.csv",
                     usecols=["timestamp_utc", "open", "high", "low", "close", "spread"],
                     dtype={c: "float64" for c in ["open", "high", "low", "close", "spread"]})
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = (df.resample("5min").agg({"open": "first", "high": "max", "low": "min",
                                   "close": "last", "spread": "mean"})
            .dropna(subset=["open", "high", "low", "close"]))
    return df


def load_events():
    d = pd.read_csv(CAL)
    d["dt"] = pd.to_datetime(d["datetime_utc"]).dt.floor("5min")
    out = {}
    for k, name in EVENTS.items():
        m = d[(d["currency"] == "USD") & (d["event"] == name)].copy()
        m = m.dropna(subset=["actual"]).sort_values("dt")
        sraw = (m["actual"] - m["forecast"])
        m["s"] = (sraw / sraw.rolling(12, min_periods=6).std().shift(1))
        out[k] = m.dropna(subset=["forecast"])[["dt", "s", "actual", "forecast"]].reset_index(drop=True)
    return out


def hac_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 8 or x.std() == 0: return np.nan, np.nan
    r = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(r.params[0]), float(r.tvalues[0])


def slope_t(y, x):
    y = np.asarray(y, float); x = np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    if ok.sum() < 10: return np.nan, np.nan, np.nan
    X = sm.add_constant(x[ok])
    r = sm.OLS(y[ok], X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(r.params[1]), float(r.tvalues[1]), float(r.rsquared)


def align(df, ev, pt):
    """For each event return dict arrays: r0 (release bar), r_post (entry+5min->+60min),
    mae_atr (max adverse excursion of the continuation trade, ATR units), absr0_atr, entry_spread_bps."""
    idx = df.index.values.astype("datetime64[ns]")
    o, h, l, c = (df[k].values for k in ["open", "high", "low", "close"])
    spr = df["spread"].values
    # 5-min ATR(20)
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    atr = pd.Series(tr).rolling(20, min_periods=20).mean().values
    atr = np.concatenate([[np.nan], atr])
    rows = []
    for _, e in ev.iterrows():
        t0 = np.datetime64(e["dt"])
        p0 = np.searchsorted(idx, t0)
        if p0 >= len(idx) or abs((idx[p0] - t0) / np.timedelta64(1, "m")) > 6:  # release bar present
            continue
        pe = p0 + 1                       # entry bar (after release bar)
        px = p0 + 12                      # exit ~ +60min (12 x 5min)
        if px >= len(idx): continue
        if (idx[pe] - t0) / np.timedelta64(1, "m") > 11: continue
        a = atr[p0 - 1] if p0 - 1 >= 0 else np.nan
        if not (a and np.isfinite(a) and a > 0): continue
        r0 = c[p0] / o[p0] - 1.0
        entry = o[pe]; exit_ = c[px]
        rpost = exit_ / entry - 1.0
        seg_lo = l[pe:px + 1].min(); seg_hi = h[pe:px + 1].max()
        d = np.sign(r0) if r0 != 0 else 0.0
        mae = (entry - seg_lo) / entry if d > 0 else (seg_hi - entry) / entry  # adverse, positive=bad
        rows.append((e["dt"], e["s"], r0, rpost, d, abs(r0) / (a / c[p0]),
                     mae / (a / entry), spr[pe] * pt / entry * 1e4))
    return pd.DataFrame(rows, columns=["dt", "s", "r0", "rpost", "dir", "absr0_atr", "mae_atr", "spr_bps"])


def analyze(sym, evk, df, ev):
    t = align(df, ev, DIGITS[sym] and 10.0 ** (-DIGITS[sym]))
    if len(t) < 12:
        return None
    cont = (t["dir"] * t["rpost"]).values            # continuation return (two-sided by dir)
    med_cost = float(np.nanmedian(t["spr_bps"])) / 1e4
    m, tt = hac_t(cont)
    # two legs
    up = cont[t["dir"].values > 0]; dn = cont[t["dir"].values < 0]
    # regime split
    yr = pd.to_datetime(t["dt"]).dt.year.values
    h1 = cont[yr <= 2021]; h2 = cont[yr >= 2022]
    sl, slt, r2 = slope_t(t["r0"].values, t["s"].values)         # HEV-1
    net2 = cont - (med_cost if sym != "XAUUSD" else med_cost)    # measured
    netS = cont - (0.0002 if sym != "XAUUSD" else 0.0003)        # stress
    return dict(
        sym=sym, ev=evk, n=int(len(t)),
        hev1_slope_t=round(slt, 2), hev1_r2=round(r2, 3),
        absr0_atr_med=round(float(np.nanmedian(t["absr0_atr"])), 2),
        p_r0_gt_1atr=round(float((t["absr0_atr"] > 1).mean()), 2),
        mae_atr_med=round(float(np.nanmedian(t["mae_atr"])), 2),
        cont_bps=round(m * 1e4, 2), cont_t=round(tt, 2),
        leg_up_bps=round(float(np.nanmean(up)) * 1e4, 2) if len(up) else np.nan,
        leg_dn_bps=round(float(np.nanmean(dn)) * 1e4, 2) if len(dn) else np.nan,
        h1_bps=round(float(np.nanmean(h1)) * 1e4, 2) if len(h1) else np.nan,
        h2_bps=round(float(np.nanmean(h2)) * 1e4, 2) if len(h2) else np.nan,
        gross_per_trade_bps=round(float(np.nanmean(np.abs(cont))) * 1e4, 2),
        cost_bps=round(med_cost * 1e4, 2),
        net2_bps=round(float(np.nanmean(net2)) * 1e4, 2),
        netS_bps=round(float(np.nanmean(netS)) * 1e4, 2),
        _cont=cont, _yr=yr)


if __name__ == "__main__":
    ev = load_events()
    print("event counts (with surprise):", {k: len(v) for k, v in ev.items()})
    allrows = []
    pooled = {k: [] for k in EVENTS}
    for sym in INSTR:
        df = load5(sym)
        for evk in EVENTS:
            r = analyze(sym, evk, df, ev[evk])
            if r is None: continue
            allrows.append(r); pooled[evk].append(r["_cont"])
            print(f"\n[{sym} {evk}] n={r['n']}  HEV1 slope_t={r['hev1_slope_t']} R2={r['hev1_r2']}  "
                  f"|r0|/ATR med={r['absr0_atr_med']} P(>1ATR)={r['p_r0_gt_1atr']}  MAE/ATR={r['mae_atr_med']}")
            print(f"    HEV2 continuation: {r['cont_bps']:+} bps/ev  t={r['cont_t']:+}  "
                  f"legs up={r['leg_up_bps']:+}/dn={r['leg_dn_bps']:+}  regime 18-21={r['h1_bps']:+}/22-26={r['h2_bps']:+}")
            print(f"    gross/trade={r['gross_per_trade_bps']}bps cost={r['cost_bps']}bps "
                  f"net@meas={r['net2_bps']:+} net@stress={r['netS_bps']:+}  (3xcost gate={round(3*r['cost_bps'],1)})")
    # pooled per event across instruments
    from engine import stats as S
    print("\n" + "=" * 90)
    for evk in EVENTS:
        if not pooled[evk]: continue
        c = np.concatenate(pooled[evk])
        m, tt = hac_t(c)
        dsr = S.deflated_sharpe_ratio(c, n_trials=N_TRIALS, periods_per_year=BARS_PER_YEAR_EVENT[evk])
        print(f">>> POOLED {evk}: n={len(c)} cont={m*1e4:+.2f}bps/ev t_HAC={tt:+.2f} "
              f"DSR(N=110)={dsr.get('dsr',float('nan')):.3f}")
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in allrows]
    (HERE / "results_event.json").write_text(json.dumps(clean, indent=2, default=float))
    print("\nsaved results_event.json")
