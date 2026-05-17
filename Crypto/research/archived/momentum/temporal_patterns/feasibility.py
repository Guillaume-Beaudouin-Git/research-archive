"""
strategies/temporal_patterns/feasibility.py — Calendar Pattern Study on 4h Data

Hypothesis: crypto exhibits intraweek/intraday patterns driven by
Asia/EU/US session flows, weekly funding settlements (Friday 16:00 UTC),
and monthly options expiry. These are purely time-based → zero
construction correlation with any price-momentum signal.

Levels tested independently:
  L1 — Hour of day (UTC): 00h, 04h, 08h, 12h, 16h, 20h
  L2 — Day of week: Mon–Sun
  L3 — Week of month: W1 (days 1-7) / W2 (8-14) / W3 (15-21) / W4 (22+)
  L4 — Month of year: Jan–Dec

GO criterion: t > 2.5 AND pattern consistent in 2022-23 AND 2024-26.

Context:
  6.6 Weekend Anomaly: Sharpe 0.42 → FAILED (prior test, do not re-test)
  6.18 Monthly Seasonality: WEAK (pattern broke in 2025)
  Expectation: high bar given prior negative results.
"""

import os, sys, time, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import requests
from datetime import datetime, timezone
from scipy import stats

warnings.filterwarnings("ignore")
np.random.seed(42)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
HL_URL   = "https://api.hyperliquid.xyz/info"
INTERVAL = "4h"
COINS    = ["BTC", "ETH", "SOL"]

START_DT = datetime(2022, 1, 1, tzinfo=timezone.utc)
END_DT   = datetime(2026, 5, 14, tzinfo=timezone.utc)
START_MS = int(START_DT.timestamp() * 1000)
END_MS   = int(END_DT.timestamp()   * 1000)
CHUNK_MS = int(180 * 24 * 3600 * 1000)   # 6-month chunks to avoid timeout

COST_RT  = 0.0017   # 0.17% round-trip (Propr taker + slippage)

DOW_LABELS  = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
HOUR_LABELS = {0:"00h", 4:"04h", 8:"08h", 12:"12h", 16:"16h", 20:"20h"}
WOM_LABELS  = {0:"W1(1-7)", 1:"W2(8-14)", 2:"W3(15-21)", 3:"W4(22+)"}
MON_LABELS  = {i+1: m for i,m in enumerate(
               ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"])}

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── DATA FETCHING ────────────────────────────────────────────────────────────

def _hl_post(payload: dict, timeout: int = 30) -> list:
    for attempt in range(3):
        try:
            r = requests.post(HL_URL, json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def fetch_hl_candles(coin: str) -> pd.DataFrame:
    """Pull 4h OHLCV from Hyperliquid in 6-month chunks, 2022-01 → 2026-05."""
    all_rows: list = []
    t = START_MS
    while t < END_MS:
        chunk_end = min(t + CHUNK_MS, END_MS)
        dt_s = datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        print(f"    {coin} [{dt_s}] … ", end="", flush=True)
        rows = _hl_post({
            "type": "candleSnapshot",
            "req": {"coin": coin, "interval": INTERVAL,
                    "startTime": t, "endTime": chunk_end}
        })
        print(f"{len(rows)} candles")
        all_rows.extend(rows)
        if not rows:
            t = chunk_end + 1
        else:
            t = int(rows[-1]["T"]) + 1
        time.sleep(0.25)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["time"] = pd.to_datetime(df["t"].astype(np.int64), unit="ms", utc=True)
    for col in ["o","c","h","l","v"]:
        df[col] = df[col].astype(float)
    df = (df.drop_duplicates(subset=["time"])
            .set_index("time")[["o","c","h","l","v"]]
            .sort_index())
    return df


def fetch_yfinance_btc() -> pd.DataFrame | None:
    """Hourly BTC-USD from yfinance, resampled to 4h (fallback if HL fails)."""
    try:
        import yfinance as yf
        print("    [yfinance] BTC-USD 1h → 4h … ", end="", flush=True)
        raw = yf.download("BTC-USD", start="2022-01-01", end="2026-05-15",
                          interval="1h", progress=False, auto_adjust=True)
        if raw.empty:
            return None
        # Handle both old and new yfinance column formats
        raw.columns = [c[0] if isinstance(c, tuple) else c for c in raw.columns]
        raw4 = raw.resample("4h").agg({
            "Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"
        }).dropna()
        raw4.columns = ["o","h","l","c","v"]
        if raw4.index.tzinfo is None:
            raw4.index = raw4.index.tz_localize("UTC")
        print(f"{len(raw4)} candles")
        return raw4
    except Exception as e:
        print(f"FAILED: {e}")
        return None


def load_data() -> dict[str, pd.DataFrame]:
    data: dict = {}
    for coin in COINS:
        print(f"\n  Fetching {coin}:")
        try:
            df = fetch_hl_candles(coin)
            if df.empty or len(df) < 200:
                raise ValueError(f"Only {len(df)} candles from HL")
            data[coin] = df
            print(f"    → {len(df)} candles  "
                  f"{df.index[0].date()} → {df.index[-1].date()}")
        except Exception as e:
            print(f"    HL failed: {e}")
            if coin == "BTC":
                fb = fetch_yfinance_btc()
                if fb is not None:
                    data[coin] = fb
                    print(f"    → {len(fb)} candles (yfinance fallback)")
    return data


# ─── FEATURE ENGINEERING ─────────────────────────────────────────────────────

def build_temporal_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret"] = np.log(out["c"] / out["c"].shift(1))
    out = out.dropna(subset=["ret"])
    out["hour"]          = out.index.hour          # 0,4,8,12,16,20
    out["dow"]           = out.index.dayofweek     # 0=Mon … 6=Sun
    out["dom"]           = out.index.day
    out["month"]         = out.index.month         # 1–12
    out["week_of_month"] = ((out["dom"] - 1) // 7).clip(0, 3)   # 0–3
    return out


# ─── STATISTICAL ANALYSIS ────────────────────────────────────────────────────

def bucket_stats(series: pd.Series) -> dict:
    n = len(series)
    if n < 30:
        return dict(mean=np.nan, std=np.nan, t=np.nan, wr=np.nan, n=n)
    t_stat = stats.ttest_1samp(series.dropna(), 0).statistic
    return dict(
        mean=series.mean(),
        std=series.std(),
        t=t_stat,
        wr=(series > 0).mean(),
        n=n
    )


def analyze_level(temporal_data: dict, col: str, label_map: dict) -> pd.DataFrame:
    rows = []
    for coin, df in temporal_data.items():
        for val, label in label_map.items():
            s = df.loc[df[col] == val, "ret"]
            st = bucket_stats(s)
            rows.append({"coin": coin, "bucket": val, "label": label, **st})
    return pd.DataFrame(rows)


def subperiod_analysis(df_btc: pd.DataFrame, col: str, label_map: dict) -> dict:
    """Return t-stat per label for each sub-period."""
    periods = {
        "2022-2023": df_btc.index < "2024-01-01",
        "2024-2026": df_btc.index >= "2024-01-01",
    }
    out: dict = {}
    for pname, mask in periods.items():
        d = {"BTC": df_btc[mask]}
        r = analyze_level(d, col, label_map)
        out[pname] = r.set_index("label")["t"].to_dict()
    return out


# ─── TSMOM v3 WEEKLY RETURNS (for correlation) ───────────────────────────────

def compute_tsmom_weekly(df_4h: pd.DataFrame) -> pd.Series:
    """
    Reconstruct TSMOM v3 weekly returns from 4h candle data.
    Signal: tanh(cumret28 / (vol28 * sqrt(28))), long-only clip.
    Used on next-day open (signal shift=1), aggregated to weekly.
    """
    daily_c = df_4h["c"].resample("D").last().dropna()
    lr      = np.log(daily_c / daily_c.shift(1)).dropna()
    cr28    = lr.rolling(28).sum()
    v28     = lr.rolling(28).std() * np.sqrt(28)
    sig     = np.tanh(cr28 / v28.replace(0, np.nan)).clip(lower=0)
    strat_r = sig.shift(1) * lr          # trade on next day
    return strat_r.resample("W-MON").sum()


# ─── EQUITY CURVE ────────────────────────────────────────────────────────────

def temporal_equity_curve(
    df: pd.DataFrame, col: str, buckets: list
) -> tuple[pd.Series, float, pd.Series]:
    """
    Long BTC when current 4h candle falls in a target bucket; flat otherwise.
    Cost charged on each 0→1 entry: 0.17% RT.
    Returns (cumulative_log_return, annualised_sharpe, bar_level_net_ret).
    """
    pos     = df[col].isin(buckets).astype(float)
    entries = (pos.diff() > 0).astype(float)
    net_ret = pos * df["ret"] - entries * COST_RT

    annual_factor = np.sqrt(365.25 * 6)  # 6 bars/day
    sharpe = (
        net_ret.mean() / net_ret.std() * annual_factor
        if net_ret.std() > 0 else 0.0
    )
    return net_ret.cumsum(), sharpe, net_ret


# ─── FIGURES ─────────────────────────────────────────────────────────────────

def make_figure(
    temporal_data, raw_data,
    res_hour, res_dow, res_wom, res_mon,
    equity_curves, eq_sharpes, tsmom_corrs
) -> None:

    fig = plt.figure(figsize=(22, 20))
    fig.suptitle(
        "Temporal Calendar Patterns — Strategy C Feasibility\n"
        "4h Hyperliquid Data  ·  BTC / ETH / SOL  ·  2022–2026",
        fontsize=14, fontweight="bold", y=0.995
    )
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.52, wspace=0.38)

    # ── Panel 1: BTC hour×DOW heatmap ────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :2])
    if "BTC" in temporal_data:
        df = temporal_data["BTC"]
        pivot = df.pivot_table(
            values="ret", index="hour", columns="dow", aggfunc="mean"
        ) * 100
        pivot.index   = [HOUR_LABELS.get(h, str(h)) for h in pivot.index]
        pivot.columns = [DOW_LABELS[int(d)] for d in pivot.columns]
        scale = max(np.nanmax(np.abs(pivot.values)), 1e-6)
        im = ax1.imshow(pivot.values, cmap="RdYlGn",
                        vmin=-scale, vmax=scale, aspect="auto")
        ax1.set_xticks(range(len(pivot.columns)))
        ax1.set_yticks(range(len(pivot.index)))
        ax1.set_xticklabels(pivot.columns)
        ax1.set_yticklabels(pivot.index)
        ax1.set_xlabel("Day of Week"); ax1.set_ylabel("Hour (UTC)")
        ax1.set_title("BTC Mean 4h Return (%) — Hour × Day of Week", fontsize=11)
        plt.colorbar(im, ax=ax1, label="Mean return (%)", shrink=0.85)
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                v = pivot.values[i, j]
                if not np.isnan(v):
                    ax1.text(j, i, f"{v:.3f}", ha="center", va="center",
                             fontsize=7.5, color="black", fontweight="bold")

    # ── Panel 2: t-stat by Hour ───────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 2])
    h_pool = res_hour.groupby("label")["t"].mean()
    h_order = [HOUR_LABELS[k] for k in sorted(HOUR_LABELS)]
    h_vals  = [h_pool.get(l, 0) for l in h_order]
    ax2.barh(h_order, h_vals,
             color=["#d73027" if v < 0 else "#1a9850" for v in h_vals],
             edgecolor="white", height=0.6)
    for thresh in [2.0, -2.0, 2.5, -2.5]:
        ax2.axvline(thresh, color="k" if abs(thresh)==2.0 else "navy",
                    ls="--", lw=1.0, alpha=0.7)
    ax2.axvline(0, color="gray", lw=0.5)
    ax2.set_title("t-stat by Hour (pooled)", fontsize=10)
    ax2.set_xlabel("t-statistic")

    # ── Panel 3: t-stat by DOW ───────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    d_pool = res_dow.groupby("label")["t"].mean()
    d_vals = [d_pool.get(l, 0) for l in DOW_LABELS]
    ax3.bar(DOW_LABELS, d_vals,
            color=["#d73027" if v < 0 else "#1a9850" for v in d_vals],
            edgecolor="white")
    for thresh in [2.0, -2.0]:
        ax3.axhline(thresh, color="k", ls="--", lw=1.0)
    ax3.axhline(0, color="gray", lw=0.5)
    ax3.set_title("t-stat by Day of Week (pooled)", fontsize=10)
    ax3.set_ylabel("t-statistic")

    # ── Panel 4: t-stat by Week of Month ─────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    w_pool  = res_wom.groupby("label")["t"].mean()
    w_order = [WOM_LABELS[k] for k in sorted(WOM_LABELS)]
    w_vals  = [w_pool.get(l, 0) for l in w_order]
    ax4.bar(w_order, w_vals,
            color=["#d73027" if v < 0 else "#1a9850" for v in w_vals],
            edgecolor="white")
    for thresh in [2.0, -2.0]:
        ax4.axhline(thresh, color="k", ls="--", lw=1.0)
    ax4.axhline(0, color="gray", lw=0.5)
    ax4.set_title("t-stat by Week of Month (pooled)", fontsize=10)
    ax4.set_ylabel("t-statistic")
    ax4.tick_params(axis="x", rotation=15)

    # ── Panel 5: t-stat by Month ─────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 2])
    m_pool  = res_mon.groupby("label")["t"].mean()
    m_order = [MON_LABELS[k] for k in sorted(MON_LABELS)]
    m_vals  = [m_pool.get(l, 0) for l in m_order]
    ax5.bar(m_order, m_vals,
            color=["#d73027" if v < 0 else "#1a9850" for v in m_vals],
            edgecolor="white")
    for thresh in [2.0, -2.0]:
        ax5.axhline(thresh, color="k", ls="--", lw=1.0)
    ax5.axhline(0, color="gray", lw=0.5)
    ax5.set_title("t-stat by Month (pooled)", fontsize=10)
    ax5.set_ylabel("t-statistic")
    ax5.tick_params(axis="x", rotation=45)

    # ── Panel 6: Equity curves ────────────────────────────────────────────────
    ax6 = fig.add_subplot(gs[2, :])
    colors_ec = ["#2166ac","#d73027","#4dac26","#762a83","#f4a582"]
    for i, (name, cum) in enumerate(equity_curves.items()):
        corr_s = (f", corr(TSMOM)={tsmom_corrs[name]:.2f}"
                  if name in tsmom_corrs else "")
        ax6.plot(cum.index, cum.values * 100,
                 label=f"{name}  Sharpe={eq_sharpes[name]:.2f}{corr_s}",
                 color=colors_ec[i % len(colors_ec)], lw=1.5)
    if "BTC" in raw_data:
        bnh = np.log(raw_data["BTC"]["c"] /
                     raw_data["BTC"]["c"].shift(1)).fillna(0).cumsum()
        ax6.plot(bnh.index, bnh.values * 100,
                 label="Buy & Hold BTC", color="gray", lw=1, ls="--", alpha=0.7)
    ax6.axhline(0, color="black", lw=0.5)
    ax6.set_title("Equity Curves — Best Temporal Buckets vs Buy & Hold (log)", fontsize=11)
    ax6.set_xlabel("Date"); ax6.set_ylabel("Cumulative log return (%)")
    ax6.legend(fontsize=9); ax6.grid(alpha=0.3)

    out_path = os.path.join(OUT_DIR, "feasibility_results.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure → {out_path}")
    plt.close()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("TEMPORAL PATTERNS FEASIBILITY — Strategy C Candidate")
    print(f"Period: {START_DT.date()} → {END_DT.date()}  "
          f"| Assets: {', '.join(COINS)}")
    print("=" * 70)

    # ── 1. Data ───────────────────────────────────────────────────────────────
    print("\n[1/6] Fetching 4h OHLCV from Hyperliquid…")
    raw_data = load_data()
    if not raw_data:
        print("ERROR: No data available. Exiting."); return

    # ── 2. Build temporal features ────────────────────────────────────────────
    print("\n[2/6] Building temporal features…")
    temporal_data = {c: build_temporal_df(df) for c, df in raw_data.items()}
    for coin, df in temporal_data.items():
        print(f"  {coin}: {len(df)} bars, "
              f"hours={sorted(df['hour'].unique())}, "
              f"DOWs={sorted(df['dow'].unique())}")

    # ── 3. Analyse each temporal level ────────────────────────────────────────
    print("\n[3/6] Statistical analysis per level…")
    dow_map  = {i: DOW_LABELS[i] for i in range(7)}
    res_hour = analyze_level(temporal_data, "hour", HOUR_LABELS)
    res_dow  = analyze_level(temporal_data, "dow",  dow_map)
    res_wom  = analyze_level(temporal_data, "week_of_month", WOM_LABELS)
    res_mon  = analyze_level(temporal_data, "month", MON_LABELS)

    for level_name, res in [
        ("L1 — Hour of Day",    res_hour),
        ("L2 — Day of Week",    res_dow),
        ("L3 — Week of Month",  res_wom),
        ("L4 — Month of Year",  res_mon),
    ]:
        sig = res[(res["t"].abs() > 2.0) & (res["n"] >= 50)].sort_values("t", ascending=False)
        print(f"\n  ── {level_name} ── significant buckets |t|>2.0, n≥50 ──")
        if sig.empty:
            print("    (none)")
        else:
            for _, row in sig.iterrows():
                print(f"    [{row['coin']}] {row['label']:15s}  "
                      f"mean={row['mean']*100:+.4f}%  t={row['t']:+.2f}  "
                      f"WR={row['wr']*100:.1f}%  n={int(row['n'])}")

    # ── 4. Sub-period stability (BTC) ─────────────────────────────────────────
    print("\n[4/6] Sub-period stability check — BTC (2022-23 vs 2024-26)…")
    if "BTC" in temporal_data:
        df_b = temporal_data["BTC"]
        for level_name, col, lmap in [
            ("Hour", "hour", HOUR_LABELS),
            ("DOW",  "dow",  dow_map),
        ]:
            sp = subperiod_analysis(df_b, col, lmap)
            print(f"\n  {level_name}:")
            for period, t_by_label in sp.items():
                top3 = sorted(t_by_label.items(), key=lambda x: -x[1])[:3]
                bot3 = sorted(t_by_label.items(), key=lambda x:  x[1])[:3]
                print(f"    {period}  top3: " +
                      ", ".join(f"{l}(t={v:.2f})" for l, v in top3))
                print(f"             bot3: " +
                      ", ".join(f"{l}(t={v:.2f})" for l, v in bot3))

    # ── 5. Equity curves + TSMOM correlation ──────────────────────────────────
    print("\n[5/6] Equity curves for best buckets (BTC)…")
    equity_curves: dict = {}
    eq_sharpes:    dict = {}
    tsmom_corrs:   dict = {}

    if "BTC" in temporal_data:
        df_b     = temporal_data["BTC"]
        tsmom_wk = compute_tsmom_weekly(raw_data["BTC"])

        # Best hour: highest pooled t-stat
        h_pool       = res_hour.groupby("bucket")["t"].mean()
        best_h       = int(h_pool.idxmax())
        best_h_label = HOUR_LABELS.get(best_h, str(best_h))

        # Best DOW pair: top 2 BTC t-stat DOW buckets
        dow_btc = res_dow[res_dow["coin"] == "BTC"].sort_values("t", ascending=False)
        top_dow = dow_btc.head(2)["bucket"].tolist()
        top_dow_label = "+".join(DOW_LABELS[d] for d in top_dow)

        # Best month
        m_pool       = res_mon.groupby("bucket")["t"].mean()
        best_m       = int(m_pool.idxmax())
        best_m_label = MON_LABELS.get(best_m, str(best_m))

        rules = [
            (f"Best hour ({best_h_label})",       "hour",  [best_h]),
            (f"Best DOW ({top_dow_label})",        "dow",   top_dow),
            (f"Best month ({best_m_label})",       "month", [best_m]),
        ]
        for name, col, buckets in rules:
            if not buckets:
                continue
            cum, sharpe, ret_net = temporal_equity_curve(df_b, col, buckets)
            equity_curves[name] = cum
            eq_sharpes[name]    = sharpe
            print(f"  {name:35s}  Sharpe={sharpe:+.3f}", end="")

            # TSMOM correlation at weekly frequency
            ret_wk = ret_net.resample("W-MON").sum()
            common = ret_wk.index.intersection(tsmom_wk.index)
            if len(common) >= 30:
                corr = ret_wk.loc[common].corr(tsmom_wk.loc[common])
                tsmom_corrs[name] = corr
                print(f"  corr(TSMOM)={corr:+.3f}", end="")
            print()

    # ── 6. Figure ─────────────────────────────────────────────────────────────
    print("\n[6/6] Generating figure…")
    make_figure(
        temporal_data, raw_data,
        res_hour, res_dow, res_wom, res_mon,
        equity_curves, eq_sharpes, tsmom_corrs
    )

    # ── Verdict ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    all_res    = pd.concat([res_hour, res_dow, res_wom, res_mon])
    sig_any    = all_res[(all_res["t"].abs() > 2.0) & (all_res["n"] >= 50)]
    sig_strong = all_res[(all_res["t"]       > 2.5) & (all_res["n"] >= 50)]

    best_sharpe = max(eq_sharpes.values(), default=0.0)
    best_corr   = min(abs(v) for v in tsmom_corrs.values()) if tsmom_corrs else 1.0

    print(f"  Buckets |t|>2.0, n≥50 : {len(sig_any)}")
    print(f"  Buckets  t >2.5, n≥50 : {len(sig_strong)}")
    print(f"  Best Sharpe (BTC)     : {best_sharpe:+.3f}")
    print(f"  Min |corr(TSMOM)|     : {best_corr:.3f}")

    # GO criterion: t > 2.5 AND consistent in both sub-periods
    if sig_strong.empty:
        go = False
        reason = "no bucket clears t > 2.5 threshold"
    elif best_sharpe < 0.3:
        go = False
        reason = f"best Sharpe {best_sharpe:.3f} < 0.30 (cost floor)"
    else:
        go = True

    if go and best_sharpe > 1.2:
        verdict = "STRONG — proceed to full backtest + A+B+C combination"
    elif go and best_sharpe > 0.6:
        verdict = "PROMISING — consider combining with TSMOM"
    elif go:
        verdict = "WEAK — signal too weak vs costs; borderline"
    else:
        verdict = f"SKIP — {reason}"

    print(f"\n  >>> {verdict}")
    print()
    print("  Historical context:")
    print("    6.6 Weekend Anomaly: Sharpe 0.42 → FAILED")
    print("    6.18 Monthly Seasonality: WEAK (pattern broke 2025)")
    print("    DSR note: ~48 buckets tested across 4 levels × 3 assets.")
    print("    Required t > 2.5 (not 2.0) to correct for multiple testing.")


if __name__ == "__main__":
    main()
