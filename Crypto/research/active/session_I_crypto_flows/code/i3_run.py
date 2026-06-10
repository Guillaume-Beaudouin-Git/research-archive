"""Trial I-3: funding-extremes two-sided IC study (gates I-4).

Spec frozen in ../preregistration.md. Settled rates are normalized to 8h-equivalent
(rate x 8h/actual interval, interval inferred from settlement spacing) so that
symbols whose funding interval switched (Binance 8h->4h on some alts) rank on a
homogeneous scale; percentile = causal trailing-365d rank (min 180d warmup).
Events de-clustered: same side within 24h keeps the first. Forward returns from
the next 1h open (delay-1, L26); missing bars fail loud (event skipped + counted).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lib_data as ld

HORIZONS = {"8h": 8, "24h": 24, "72h": 72}
HAC_LAGS = {"8h": 6, "24h": 12, "72h": 24}
REGIMES = {"2020-21": ("2020-01-01", "2021-12-31"), "2022": ("2022-01-01", "2022-12-31"),
           "2023": ("2023-01-01", "2023-12-31"), "2024-26": ("2024-01-01", "2026-05-31")}
HI, LO = 0.975, 0.025


def hac_t(x: np.ndarray, lags: int) -> tuple[float, float]:
    x = np.asarray(x, float)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan")
    e = x - x.mean()
    s = (e @ e) / n
    for l in range(1, min(lags, n - 1) + 1):
        s += 2 * (1 - l / (lags + 1)) * (e[:-l] @ e[l:]) / n
    return x.mean(), x.mean() / np.sqrt(max(s, 1e-18) / n)


def load_1h(sym: str) -> pd.Series:
    months = pd.period_range("2019-12", "2026-05", freq="M").strftime("%Y-%m")
    frames = [df for m in months if (df := ld.monthly_klines(sym, "1h", m)) is not None]
    px = pd.concat(frames)["open"].astype(float)
    return px[~px.index.duplicated()].sort_index()


def symbol_events(sym: str) -> pd.DataFrame:
    f = ld.funding_history(sym).copy()
    dt_h = f.index.to_series().diff().dt.total_seconds().div(3600).bfill().clip(0.5, 12)
    f["r8"] = f["rate"] * (8.0 / dt_h)
    r = f["r8"]
    pct = np.full(len(r), np.nan)
    vals = r.values
    ts = r.index
    for i in range(len(r)):
        lo_t = ts[i] - pd.Timedelta(days=365)
        j0 = ts.searchsorted(lo_t)
        win = vals[j0:i]
        if len(win) >= 180 * 3:
            pct[i] = (win <= vals[i]).mean()
    f["pct"] = pct
    f["side"] = np.where(f["pct"] > HI, "high", np.where(f["pct"] < LO, "low", ""))
    ev = f[f["side"] != ""].copy()
    keep, last = [], {}
    for t, row in ev.iterrows():
        if row["side"] in last and (t - last[row["side"]]) < pd.Timedelta(hours=24):
            continue
        last[row["side"]] = t
        keep.append(t)
    ev = ev.loc[keep]
    px = load_1h(sym)
    rows, skipped = [], 0
    for t, row in ev.iterrows():
        i = px.index.searchsorted(t, side="right")
        if i >= len(px):
            skipped += 1
            continue
        t_in = px.index[i]
        if (t_in - t) > pd.Timedelta(hours=2):
            skipped += 1
            continue
        rec = {"symbol": sym, "ts": t, "side": row["side"], "pct": row["pct"], "r8": row["r8"]}
        ok = True
        for hname, h in HORIZONS.items():
            t_out = t_in + pd.Timedelta(hours=h)
            if t_out not in px.index:
                ok = False
                break
            rec[f"fwd_{hname}"] = float(np.log(px.loc[t_out] / px.loc[t_in]) * 1e4)
        if ok:
            rows.append(rec)
        else:
            skipped += 1
    print(f"{sym}: {len(rows)} events ({skipped} skipped on gaps)")
    return pd.DataFrame(rows)


def main() -> None:
    uni = json.load(open(ld.CACHE / "i3_universe.json"))["universe"]
    ev = pd.concat([symbol_events(s) for s in uni], ignore_index=True)
    ev.to_parquet(ld.CACHE / "i3_events.parquet")

    out: dict = {"universe": uni, "n_events": {s: int((ev["symbol"] == s).sum()) for s in uni}}
    res = {}
    for hname in HORIZONS:
        res[hname] = {}
        for side, want in (("high", -1), ("low", +1)):
            sub = ev[ev["side"] == side].sort_values("ts")
            m, t = hac_t(sub[f"fwd_{hname}"].values, HAC_LAGS[hname])
            leg = {"n": int(len(sub)), "mean_bps": m, "hac_t": t,
                   "contrarian_ok": bool(np.sign(m) == want and abs(t) >= 2.0)}
            for rname, (a, b) in REGIMES.items():
                rs = sub[(sub["ts"] >= pd.Timestamp(a, tz="UTC")) & (sub["ts"] <= pd.Timestamp(b, tz="UTC"))]
                rm, rt = hac_t(rs[f"fwd_{hname}"].values, HAC_LAGS[hname])
                leg[f"regime_{rname}"] = {"n": int(len(rs)), "mean_bps": rm, "hac_t": rt}
            res[hname][side] = leg
    out["legs"] = res

    passes = {}
    for hname in HORIZONS:
        hi_leg, lo_leg = res[hname]["high"], res[hname]["low"]
        both = hi_leg["contrarian_ok"] and lo_leg["contrarian_ok"]
        stable = True
        for leg, want in ((hi_leg, -1), (lo_leg, +1)):
            for rname in REGIMES:
                cell = leg[f"regime_{rname}"]
                if cell["n"] > 0 and np.isfinite(cell["mean_bps"]) and np.sign(cell["mean_bps"]) != want:
                    stable = False
        passes[hname] = {"both_sides_significant_contrarian": bool(both),
                         "sign_stable_all_regimes": bool(stable), "PASS": bool(both and stable)}
    out["pass_table"] = passes
    out["I3_PASS"] = bool(any(p["PASS"] for p in passes.values()))

    per_sym = ev.groupby(["symbol", "side"])["fwd_24h"].agg(["mean", "count"]).reset_index()
    out["per_symbol_24h"] = per_sym.to_dict("records")

    json.dump(out, open(ld.ROOT / "i3_results.json", "w"), indent=1, default=float)
    print(json.dumps(passes, indent=1))
    print("I3_PASS:", out["I3_PASS"])


if __name__ == "__main__":
    main()
