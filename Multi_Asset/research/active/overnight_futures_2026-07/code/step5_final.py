"""Step 5 — headline table for the surviving sleeve, un-winsorised (conservative:
the source gold study did not winsorise), plus bootstrap CI and the soybean
futures-only finding that must be reported as an open, unmeasured window.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from common import (ACCOUNT_USD, CONTRACTS, NOTIONAL, OUT, REPO, cagr, hac_t, max_dd,
                    obs_per_year, sharpe, us_dst, vol_target)
from step1c_gap_decomposition import REOPEN_ET, WINDOW_HOURS, load_m1, price_at
from common import SLEEVES

sys.path.insert(0, str(REPO / "yt_strategy_replications"))
from engine import stats as S  # noqa: E402

H = np.int64(3_600_000_000_000)


def raw_window(name: str, winsor: bool) -> pd.Series:
    sp = SLEEVES[name]
    df = load_m1(sp["cfd"], sp["sample_start"])
    ts = pd.DatetimeIndex(df["ts"])
    et = ts - pd.to_timedelta(np.where(us_dst(ts), 4, 5), unit="h")
    keys, vals = et.asi8, df["close"].to_numpy()
    ro, hours = REOPEN_ET[name], WINDOW_HOURS[name]
    sess = pd.DatetimeIndex(np.unique(pd.DatetimeIndex(et).normalize()))
    base = (sess + pd.Timedelta(hours=ro)).asi8
    p0 = price_at(vals, keys, base, "first", 20)
    p1 = price_at(vals, keys, base + hours * H, "last", 30)
    s = pd.Series(np.log(p1 / p0), index=sess).dropna()
    s = s[np.isfinite(s.to_numpy())]
    if winsor:
        lo, hi = s.quantile([0.005, 0.995])
        s = s.clip(lo, hi)
    return s


def boot_sr_ci(x: pd.Series, n_boot=5000, mean_block=10, seed=11):
    a = np.asarray(x, float); n = len(a); ppy = obs_per_year(x)
    rng = np.random.default_rng(seed); p = 1.0 / mean_block
    out = np.empty(n_boot)
    for i in range(n_boot):
        idx = np.empty(n, int); j = 0
        while j < n:
            s0 = rng.integers(0, n); L = min(rng.geometric(p), n - j)
            idx[j:j + L] = (s0 + np.arange(L)) % n; j += L
        v = a[idx]; out[i] = v.mean() / v.std(ddof=1) * np.sqrt(ppy)
    return float(np.percentile(out, 5)), float(np.percentile(out, 95))


rows = []
for winsor in (False, True):
    w = raw_window("GOLD", winsor)
    pos = vol_target(w)
    for cost, tag in ((0.0, "gross"), (0.66, "net_MGC_base"), (0.91, "net_MGC_stress2tick"),
                      (1.5, "net_at_CFD_1.5bp")):
        net = (pos * w - pos.abs() * cost * 1e-4).dropna()
        net = net[net.index >= w.index[20]]
        for span, seg in (("2007-2026", net), ("2014-2026", net[net.index >= "2014"]),
                          ("2020-2026", net[net.index >= "2020"])):
            mu, t = hac_t(seg)
            ppy = obs_per_year(seg)
            d = S.deflated_sharpe_ratio(seg.to_numpy(), n_trials=95, periods_per_year=ppy)
            r = dict(winsorised=winsor, cost_case=tag, cost_bps=cost, span=span,
                     N=len(seg), obs_yr=round(ppy, 1),
                     mean_bps=round(1e4 * seg.mean(), 2), SR=round(sharpe(seg), 3),
                     t_hac=round(t, 2), DSR=round(float(d["dsr"]), 3),
                     vol_pct=round(100 * seg.std(ddof=1) * np.sqrt(ppy), 2),
                     CAGR_pct=round(100 * cagr(seg), 2),
                     maxDD_pct=round(100 * max_dd(seg), 1),
                     skew=round(float(pd.Series(seg).skew()), 2))
            if not winsor and tag == "net_MGC_base":
                lo, hi = boot_sr_ci(seg)
                r["SR_boot_ci90"] = f"[{lo:.2f}, {hi:.2f}]"
            rows.append(r)

res = pd.DataFrame(rows)
pd.set_option("display.width", 300, "display.max_columns", 40)
print("=== GOLD / MGC — headline, exchange-clock spec, halt gap excluded ===")
print(res.to_string(index=False))
res.to_csv(OUT / "step5_gold_headline.csv", index=False)

# ------------------------------------------------- account sizing, honest regime
w = raw_window("GOLD", False)
pos = vol_target(w)
print("\n=== account outcome at $15,000, un-winsorised, net 0.66 bps RT ===")
for span in ("2007-2026", "2014-2026", "2020-2026"):
    net = (pos * w - pos.abs() * 0.66e-4).dropna()
    if span != "2007-2026":
        net = net[net.index >= span[:4]]
    ppy = obs_per_year(net)
    sr, vol = sharpe(net), net.std(ddof=1) * np.sqrt(ppy)
    kelly = sr / vol
    print(f"\n {span}: sleeve SR={sr:.2f} vol={100*vol:.2f}%  full-Kelly leverage={kelly:.1f}x"
          f"  (= {kelly*ACCOUNT_USD/NOTIONAL['MGC']:.1f} MGC contracts)")
    for n in (1, 2, 3):
        lev = n * NOTIONAL["MGC"] / ACCOUNT_USD
        a = net * lev
        print(f"   {n} MGC lev={lev:4.2f}x ({lev/kelly:.2f} Kelly) margin="
              f"{100*n*CONTRACTS['MGC']['margin']/ACCOUNT_USD:5.1f}%  vol={100*a.std(ddof=1)*np.sqrt(ppy):5.1f}%"
              f"  CAGR={100*cagr(a):6.1f}%  maxDD={100*max_dd(a):6.1f}%")

# ------------------------------------------------------- soybean: the open window
fut = pd.read_csv(OUT / "step2_futures_daily.csv", index_col=0, parse_dates=True)
zs = fut[fut["sleeve"] == "SOYBEAN"]
print("\n=== SOYBEAN: the CBOT reopen window that the CFD cannot see ===")
for c in ("gap", "hour1_cap", "window_cap"):
    mu, t = hac_t(zs[c])
    print(f"  {c:12s} mean={1e4*zs[c].mean():6.2f} bps  t_HAC={t:5.2f}  N={len(zs)}")
print(f"  raw SR (2y, ZS=F, NOT a performance claim) = {sharpe(zs['window_cap']):.2f}")
print("  MZS round-trip cost = 3.89 bps base / 4.94 bps stress vs this 9.65 bps gross.")
