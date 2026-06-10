"""
Re-do integrity + S2/S3 reproduction with corrected MT5 timezone.

MT5 timestamps in this dataset are mislabeled `utc` but are actually GMT+3 server-time.
Real UTC = MT5_timestamp - 3h. Real ET = MT5 - 8h (winter) or MT5 - 7h (summer DST).

Path:
  1) Re-build MT5 corrected ET index for all 5 indices.
  2) Re-check spread by 30-min ET RTH bucket (real cash session).
  3) Verify MT5 NQ ↔ databento NQ correlation now ≈ 0.95+ on signal-ret bar.
  4) Reproduce S2 (cross-sec reversion 09:30→10:30) and S3 (long PM 12:30→16:00).
"""
import json
from datetime import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
MT5DIR = ROOT / "data/ftmo_universe/intraday_m1/indices"
DBN = ROOT / "Futures/research/active/ftmo_3strats_audit_2026-06/results/nq_1m_rth_2010_2026.parquet"
RES = ROOT / "Futures/research/active/ftmo_3strats_audit_2026-06/results"

INDICES = ["US500", "US100", "US30", "US2000"]
TICK_VALUE_GUESS = 0.01  # 1 MT5 point = 0.01 USD (FTMO indices typical)
WINDOW_START = "2021-01-01"
WINDOW_END = "2026-05-31"


def load_mt5_corrected(symbol: str) -> pd.DataFrame:
    """Load MT5 M1 with GMT+3 → real UTC correction, then to ET."""
    p = MT5DIR / f"{symbol}_M1.csv"
    df = pd.read_csv(p, parse_dates=["timestamp_utc"],
                     date_format="%Y.%m.%d %H:%M:%S")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df = df.set_index("timestamp_utc").sort_index()
    # Strip mislabeled tz, shift -3h to get true UTC, then re-localize and convert to ET
    df.index = df.index.tz_localize(None) - pd.Timedelta(hours=3)
    df.index = df.index.tz_localize("UTC").tz_convert("America/New_York")
    df["t_et"] = df.index.time
    df["date_et"] = df.index.normalize().date
    return df


def session_keys(df: pd.DataFrame, label: str = "") -> pd.DataFrame:
    """For each ET date: open(09:30), open(10:30), open(11:00), open(12:30),
       close(16:00), high/low intraday post-09:30."""
    g_open = df.groupby("date_et")
    o930 = df[df["t_et"] == time(9, 30)].groupby("date_et")["open"].first()
    o1030 = df[df["t_et"] == time(10, 30)].groupby("date_et")["open"].first()
    o1100 = df[df["t_et"] == time(11, 0)].groupby("date_et")["open"].first()
    o1230 = df[df["t_et"] == time(12, 30)].groupby("date_et")["open"].first()
    rth_mask = (df["t_et"] >= time(9, 30)) & (df["t_et"] <= time(16, 0))
    rth = df.loc[rth_mask]
    close16 = rth.groupby("date_et")["close"].last()
    out = pd.DataFrame(
        {
            "o930": o930,
            "o1030": o1030,
            "o1100": o1100,
            "o1230": o1230,
            "close16": close16,
        }
    )
    return out


def main() -> None:
    print("=== STEP 1: Load MT5 corrected timestamps for all 5 indices ===", flush=True)
    panels = {}
    for sym in INDICES + ["GER40"]:
        try:
            print(f"[load] {sym}", flush=True)
            df = load_mt5_corrected(sym)
            df = df.loc[WINDOW_START:WINDOW_END]
            panels[sym] = df
            print(f"  rows={len(df):,}  span={df.index.min()} → {df.index.max()}", flush=True)
        except FileNotFoundError as e:
            print(f"  missing: {e}", flush=True)

    print("\n=== STEP 2: Spread by ET RTH bucket (TRUE cash session) — US100 ===", flush=True)
    us100 = panels["US100"]
    rth_mask = (us100["t_et"] >= time(9, 30)) & (us100["t_et"] < time(16, 0))
    sub = us100.loc[rth_mask].copy()
    sub["bucket"] = (
        pd.Series(sub.index.hour.astype(str).str.zfill(2), index=sub.index)
        + ":"
        + (pd.Series(sub.index.minute // 30 * 30, index=sub.index).astype(str).str.zfill(2))
    )
    spr_h = sub.groupby("bucket")["spread"].agg(["median", "mean",
                                                   lambda x: x.quantile(0.95)])
    spr_h.columns = ["median_pts", "mean_pts", "p95_pts"]
    px_med = float(us100["close"].median())
    spr_h["median_bps_RT"] = spr_h["median_pts"] * TICK_VALUE_GUESS / px_med * 1e4 * 2
    print(spr_h.to_string(), flush=True)
    spr_h.to_csv(RES / "mt5_us100_spread_corrected_et_bucket.csv")

    print("\n=== STEP 3: Re-do MT5 US100 vs databento NQ correlation (post-fix) ===", flush=True)
    dbn = pd.read_parquet(DBN)
    dbn.index = pd.to_datetime(dbn.index).tz_localize("America/New_York")
    dbn["t_et"] = dbn.index.time
    dbn["date_et"] = dbn.index.normalize().date
    dbn_w = dbn.loc[WINDOW_START:WINDOW_END]

    mt5_k = session_keys(us100)
    dbn_k = session_keys(dbn_w)
    merged = mt5_k.join(dbn_k, lsuffix="_mt5", rsuffix="_dbn", how="inner")
    merged["mt5_ret_signal"] = merged["o1100_mt5"] / merged["o930_mt5"] - 1
    merged["dbn_ret_signal"] = merged["o1100_dbn"] / merged["o930_dbn"] - 1
    merged["mt5_ret_session"] = merged["close16_mt5"] / merged["o930_mt5"] - 1
    merged["dbn_ret_session"] = merged["close16_dbn"] / merged["o930_dbn"] - 1
    merged.index = pd.to_datetime(merged.index)
    merged["year"] = merged.index.year
    rows = []
    for y, g in merged.groupby("year"):
        if len(g) < 50: continue
        rows.append({
            "year": int(y),
            "n": int(len(g)),
            "corr_signal": float(g[["mt5_ret_signal","dbn_ret_signal"]].corr().iloc[0,1]),
            "corr_session": float(g[["mt5_ret_session","dbn_ret_session"]].corr().iloc[0,1]),
        })
    cdf = pd.DataFrame(rows)
    print(cdf.to_string(index=False), flush=True)
    cdf.to_csv(RES / "mt5_vs_databento_corr_by_year_corrected.csv", index=False)

    print("\n=== STEP 4: Reproduce S2 (cross-sec reversion 09:30→10:30, hold to 16:00) ===", flush=True)
    keys = {sym: session_keys(panels[sym]) for sym in INDICES if sym in panels}
    s2_dates = sorted(set.intersection(*[set(k.index) for k in keys.values()]))
    print(f"[s2] common ET sessions across {len(INDICES)} indices = {len(s2_dates)}", flush=True)

    s2_rows = []
    for dt in s2_dates:
        rets_signal, rets_session = {}, {}
        valid = True
        for sym, k in keys.items():
            try:
                o930 = k.at[dt, "o930"]
                o1030 = k.at[dt, "o1030"]
                close16 = k.at[dt, "close16"]
            except KeyError:
                valid = False
                break
            if any(pd.isna([o930, o1030, close16])):
                valid = False
                break
            rets_signal[sym] = o1030 / o930 - 1
            rets_session[sym] = close16 / o1030 - 1
        if not valid:
            continue

        rs = pd.Series(rets_signal)
        rsess = pd.Series(rets_session)
        # Cross-sectional z-score
        z = (rs - rs.mean()) / rs.std(ddof=0) if rs.std(ddof=0) > 0 else rs * 0
        w = -z  # long laggards, short leaders
        # Dollar-neutral normalization Σ|w| = 1
        denom = np.abs(w).sum()
        if denom == 0:
            continue
        w = w / denom
        # Net daily return = w @ rsess
        ret_d = float((w * rsess).sum())
        s2_rows.append({"date": dt, **{f"w_{s}": w[s] for s in INDICES},
                        **{f"hold_ret_{s}": rsess[s] for s in INDICES},
                        "s2_ret": ret_d})

    s2 = pd.DataFrame(s2_rows).set_index("date").sort_index()
    s2.index = pd.to_datetime(s2.index)
    print(f"[s2] effective sessions={len(s2)}", flush=True)

    # Cost model: per-trade per-side cost in bps RT applied to gross|w|.
    # Notional turnover per day = sum(|w_entry|) + sum(|w_exit|) = 2 * sum(|w|) = 2.
    # Cost = spread/2 (per side) × turnover. For 4 indices at median 0.4-1.0 bp RT each,
    # take a conservative scenario.
    # Simpler: cost per day = 2 × mean_per_side_bps × sum_|w|.
    # Σ|w|=1, so cost = 2 * mean_per_side. Convert to fraction.
    # We'll apply 1× / 2× / 3× of 1.0 bp RT (= 0.5 bp per side average across 4 indices).
    for mult in [1, 2, 3]:
        cost_per_day = mult * 1e-4  # 1 bp = 1e-4 in fraction units
        s2[f"s2_net_x{mult}"] = s2["s2_ret"] - cost_per_day
    # Annualized stats
    print("\n[S2 gross + cost sensitivity]")
    for col in ["s2_ret", "s2_net_x1", "s2_net_x2", "s2_net_x3"]:
        mu = s2[col].mean()
        sd = s2[col].std(ddof=0)
        sh = mu / sd * np.sqrt(252) if sd > 0 else float("nan")
        print(f"  {col:15s}  mu={mu:.6f}  sd={sd:.6f}  Sharpe={sh:+.3f}  sumR={s2[col].sum()*100:+.2f}%")
    s2.to_parquet(RES / "s2_reproduction.parquet")

    print("\n=== STEP 5: Reproduce S3 (long US500+US100+US30 PM 12:30→16:00, equal weight) ===", flush=True)
    s3_dates = sorted(set.intersection(*[set(keys[s].index) for s in ["US500","US100","US30"]]))
    s3_rows = []
    for dt in s3_dates:
        try:
            r500 = keys["US500"].at[dt, "close16"] / keys["US500"].at[dt, "o1230"] - 1
            r100 = keys["US100"].at[dt, "close16"] / keys["US100"].at[dt, "o1230"] - 1
            r30  = keys["US30"].at[dt,  "close16"] / keys["US30"].at[dt,  "o1230"] - 1
        except KeyError:
            continue
        if any(pd.isna([r500, r100, r30])):
            continue
        s3_rows.append({"date": dt, "r500": r500, "r100": r100, "r30": r30,
                        "s3_ret": (r500 + r100 + r30) / 3.0})
    s3 = pd.DataFrame(s3_rows).set_index("date").sort_index()
    s3.index = pd.to_datetime(s3.index)
    print(f"[s3] effective sessions={len(s3)}", flush=True)

    # Cost: long-only 3 indices, each ~0.4 bp RT for tight ones, ~1 bp for US100
    # Simple model: 1 bp RT average, equal-weight 3 = 1 bp on total notional.
    for mult in [1, 2, 3]:
        cost = mult * 1e-4
        s3[f"s3_net_x{mult}"] = s3["s3_ret"] - cost
    print("\n[S3 gross + cost sensitivity]")
    for col in ["s3_ret", "s3_net_x1", "s3_net_x2", "s3_net_x3"]:
        mu = s3[col].mean()
        sd = s3[col].std(ddof=0)
        sh = mu / sd * np.sqrt(252) if sd > 0 else float("nan")
        print(f"  {col:15s}  mu={mu:.6f}  sd={sd:.6f}  Sharpe={sh:+.3f}  sumR={s3[col].sum()*100:+.2f}%")

    # Beta of S3 vs equal-weight long basket = trivial (β=1 by construction), but
    # let's still regress on full-session market return to confirm.
    # Use US500 09:30→16:00 as benchmark — align by date keys safely.
    us500_k = keys["US500"]
    bench_vals = []
    bench_idx = []
    for dt in s3.index:
        try:
            o = us500_k.at[dt, "o930"]
            c = us500_k.at[dt, "close16"]
        except KeyError:
            continue
        if pd.isna(o) or pd.isna(c):
            continue
        bench_vals.append(c / o - 1)
        bench_idx.append(dt)
    bench = pd.Series(bench_vals, index=pd.to_datetime(bench_idx), name="bench")
    df_reg = pd.DataFrame({"y": s3["s3_ret"], "x": bench}).dropna()
    if len(df_reg) > 30:
        cov = df_reg[["y","x"]].cov().iloc[0,1]
        var_x = df_reg["x"].var(ddof=0)
        beta = cov / var_x if var_x > 0 else float("nan")
        alpha = df_reg["y"].mean() - beta * df_reg["x"].mean()
        # rough t(alpha)
        n = len(df_reg)
        resid = df_reg["y"] - alpha - beta * df_reg["x"]
        se_alpha = resid.std(ddof=1) / np.sqrt(n)
        t_alpha = alpha / se_alpha if se_alpha > 0 else float("nan")
        print(f"\n[S3 vs US500 full-session]  β={beta:.3f}  α_daily={alpha:.6f}  t(α)≈{t_alpha:.2f}")

    s3.to_parquet(RES / "s3_reproduction.parquet")

    # Save concise JSON summary
    summary = {
        "mt5_timezone": "GMT+3 server-time (label `utc` misleading); corrected by -3h to true UTC",
        "spread_us100_at_11ET_median_pts": float(spr_h.loc["11:00", "median_pts"]) if "11:00" in spr_h.index else None,
        "spread_us100_at_11ET_median_bps_RT": float(spr_h.loc["11:00", "median_bps_RT"]) if "11:00" in spr_h.index else None,
        "mt5_vs_databento_corr_signal_year_by_year": cdf.to_dict(orient="records"),
        "s2_sharpe_x1_x2_x3": {
            "gross": float(s2["s2_ret"].mean() / s2["s2_ret"].std(ddof=0) * np.sqrt(252)),
            "x1": float(s2["s2_net_x1"].mean() / s2["s2_net_x1"].std(ddof=0) * np.sqrt(252)),
            "x2": float(s2["s2_net_x2"].mean() / s2["s2_net_x2"].std(ddof=0) * np.sqrt(252)),
            "x3": float(s2["s2_net_x3"].mean() / s2["s2_net_x3"].std(ddof=0) * np.sqrt(252)),
        },
        "s3_sharpe_x1_x2_x3": {
            "gross": float(s3["s3_ret"].mean() / s3["s3_ret"].std(ddof=0) * np.sqrt(252)),
            "x1": float(s3["s3_net_x1"].mean() / s3["s3_net_x1"].std(ddof=0) * np.sqrt(252)),
            "x2": float(s3["s3_net_x2"].mean() / s3["s3_net_x2"].std(ddof=0) * np.sqrt(252)),
            "x3": float(s3["s3_net_x3"].mean() / s3["s3_net_x3"].std(ddof=0) * np.sqrt(252)),
        },
    }
    if 't_alpha' in dir() and not np.isnan(t_alpha):
        summary["s3_vs_us500_full_session"] = {
            "beta": float(beta), "alpha_daily": float(alpha), "t_alpha": float(t_alpha),
            "alpha_annualized_pct": float(alpha * 252 * 100),
        }
    (RES / "s2_s3_reproduction.json").write_text(json.dumps(summary, indent=2))
    print(f"\n[save] {RES / 's2_s3_reproduction.json'}")


if __name__ == "__main__":
    main()
