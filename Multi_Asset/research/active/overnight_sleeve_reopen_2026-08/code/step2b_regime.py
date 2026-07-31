"""Step 2b — MANDATORY regime split at the documented 2021 break (L31).

"The Disappearing Overnight Drift" (NY Fed, 2026-07) reports the ES/NQ/YM overnight
drift at ZERO since 2021, and attributes it to a measured compression in the dispersion
of signed closing volume (6.5% -> 2.9%). Our sleeve claims the SAME mechanism —
inventory compensation paid when liquidity returns after the halt. If the mechanism
closed in 2021, a full-sample t of 4.8 is an artefact of a dead regime and every
downstream p(pass) computed on the full sample is misleading.

Two things are measured here:
  (a) pre/post-2021 split on GOLD, SILVER, WTI: gross, net at both cost hypotheses,
      t_HAC(6), SR, N — raw (unwinsorised) series;
  (b) a free proxy for the closing-flow-dispersion mechanism: the annual cross-session
      dispersion of the signed PRE-HALT hour return (price impact is monotone in signed
      flow, so a finer-sliced close compresses this dispersion too), plus the annual
      dispersion of pre-halt tick volume.

(b) is a mechanism diagnostic, not a strategy test: no position is ever taken on it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common_reopen import (COST_MEAS_BPS, COST_OLD_BPS, MAIN, OUT, PRIOR, REOPEN_ET,
                           hac_t, obs_per_year, sharpe, us_dst)

H = np.int64(3_600_000_000_000)
SLEEVES = {                      # cfd, window hours, sample start (inherited verbatim)
    "GOLD": ("XAUUSD", 8, "2007-01-01"),
    "SILVER": ("XAGUSD", 8, "2014-01-01"),
    "WTI": ("USOIL", 8, "2013-01-01"),
}
BREAK = pd.Timestamp("2021-01-01")


def window_series(cfd: str, hours: int, start: str) -> pd.Series:
    m1 = pd.read_parquet(PRIOR / "code" / "_m1cache" / f"{cfd}_m1.parquet")
    m1 = m1[m1["ts"] >= pd.Timestamp(start)].sort_values("ts")
    ts = pd.DatetimeIndex(m1["ts"])
    et = ts - pd.to_timedelta(np.where(us_dst(ts), 4, 5), unit="h")
    keys, px = et.asi8, m1["close"].to_numpy(float)
    sess = pd.DatetimeIndex(np.unique(pd.DatetimeIndex(et).normalize()))
    base = (sess + pd.Timedelta(hours=REOPEN_ET)).asi8
    i0 = np.searchsorted(keys, base, "left")
    ok0 = (i0 < len(keys)) & (keys[np.clip(i0, 0, len(keys) - 1)] - base <= 20 * 60_000_000_000)
    i1 = np.searchsorted(keys, base + hours * H, "left") - 1
    ok1 = (i1 >= 0) & (base + hours * H - keys[np.clip(i1, 0, len(keys) - 1)] <= 30 * 60_000_000_000)
    m = ok0 & ok1 & (i1 > i0)
    s = pd.Series(np.log(px[i1[m]] / px[i0[m]]), index=sess[m])
    return s[np.isfinite(s.to_numpy())]


rows = []
for name, (cfd, hours, start) in SLEEVES.items():
    s = window_series(cfd, hours, start)
    for era, sub in (("full", s), ("pre-2021", s[s.index < BREAK]), ("post-2021", s[s.index >= BREAK])):
        if len(sub) < 100:
            continue
        ppy = obs_per_year(sub)
        r = dict(sleeve=name, era=era, N=len(sub),
                 span=f"{sub.index.min().date()}..{sub.index.max().date()}",
                 gross_bps=round(1e4 * sub.mean(), 2), t_hac_gross=round(hac_t(sub)[1], 2),
                 SR_gross=round(sharpe(sub), 3))
        for lab, c in (("meas1.84", COST_MEAS_BPS), ("old3.50", COST_OLD_BPS)):
            net = sub - c * 1e-4
            r[f"net_{lab}_bps"] = round(1e4 * net.mean(), 2)
            r[f"t_hac_{lab}"] = round(hac_t(net)[1], 2)
            r[f"SR_{lab}"] = round(sharpe(net), 3)
        rows.append(r)

reg = pd.DataFrame(rows)
reg.to_csv(OUT / "step2b_regime_split.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 40)
print("=== (a) regime split at 2021 (raw, unwinsorised) ===")
print(reg.to_string(index=False))

# ── (b) closing-flow-dispersion proxy ────────────────────────────────────────
print("\n=== (b) pre-halt (closing) flow-dispersion proxy, by year ===")
drows = []
for name, (cfd, hours, start) in SLEEVES.items():
    h1 = pd.read_parquet(MAIN / "yt_strategy_replications" / "data_cache" / "gold"
                         / f"{cfd}_1h.parquet")
    h1 = h1[h1.index >= pd.Timestamp(start)]
    et = h1.index - pd.to_timedelta(np.where(us_dst(h1.index), 4, 5), unit="h")
    h1 = h1.set_index(pd.DatetimeIndex(et))
    pre = h1[h1.index.hour == REOPEN_ET - 2]          # 16:00-17:00 ET, last full hour
    r = np.log(pre["close"] / pre["open"])
    amp = (pre["high"] - pre["low"]) / pre["close"]
    tv = pre["tick_volume"]
    for y, g in r.groupby(r.index.year):
        if len(g) < 100:
            continue
        a, v = amp.loc[g.index], tv.loc[g.index]
        drows.append(dict(sleeve=name, year=int(y), n=len(g),
                          disp_signed_ret_bps=round(1e4 * g.std(), 1),
                          mean_abs_ret_bps=round(1e4 * g.abs().mean(), 1),
                          amp_bps=round(1e4 * a.mean(), 1),
                          cv_tick_vol=round(float(v.std() / v.mean()), 3) if v.mean() > 0 else np.nan))
disp = pd.DataFrame(drows)
disp.to_csv(OUT / "step2b_flow_dispersion.csv", index=False)
for name in SLEEVES:
    d = disp[disp.sleeve == name]
    if d.empty:
        continue
    pre_e = d[d.year < 2021]
    post_e = d[d.year >= 2021]
    print(f"{name:7s} disp(signed pre-halt ret, bps): pre-2021 {pre_e.disp_signed_ret_bps.mean():6.1f}"
          f" -> post-2021 {post_e.disp_signed_ret_bps.mean():6.1f}"
          f"   ({100*(post_e.disp_signed_ret_bps.mean()/pre_e.disp_signed_ret_bps.mean()-1):+.0f}%)"
          f" | CV(tick vol): {pre_e.cv_tick_vol.mean():.2f} -> {post_e.cv_tick_vol.mean():.2f}")
print()
print(disp.pivot(index="year", columns="sleeve", values="disp_signed_ret_bps").to_string())
