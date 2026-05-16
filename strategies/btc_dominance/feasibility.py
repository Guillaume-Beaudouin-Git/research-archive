"""
BTC Dominance Relative Momentum — Feasibility Study
=====================================================
Economic mechanism: crypto alternates between BTC season (institutions
rotate into BTC) and alt season (risk-on flows into alts). Rotation is
systematic. Portfolio is market-neutral by construction: long the
outperforming side, short the underperforming side.

Signal: 14-day relative return BTC vs equal-weighted ALT basket.
  dominance[T] = btc_ret_14d[T] − alt_ret_14d[T]
  +ve → BTC season → long BTC / short ALT
  −ve → alt season → long ALT / short BTC

Steps:
  1. IC test: does signal predict next-week relative return?
  2. Equity curve: full + by leg + sub-period Sharpe
  3. Lookback sensitivity: [7, 14, 21, 28] days

Verdict thresholds:
  STRONG:    Sharpe > 1.5, short leg Sharpe > 0, 3+/4 sub-periods positive
  PROMISING: Sharpe 0.8–1.5, or short leg slightly negative
  WEAK:      Sharpe < 0.8, or short leg consistently negative
  SKIP:      Sharpe < 0,   or IC t-stat < 1.0
"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Parameters ────────────────────────────────────────────────────────────────
START      = "2020-01-01"
END        = "2026-05-14"
BTC        = "BTC-USD"
ALTS       = ["ETH-USD", "SOL-USD", "BNB-USD", "ADA-USD", "AVAX-USD"]
BASE_LB    = 14          # base lookback (days)
VOL_WIN    = 20          # realized vol window
VOL_TGT    = 0.15        # annualized vol target per leg
GROSS_CAP  = 0.90        # max gross exposure
COST_RT    = 0.0017      # 0.17% RT, charged at Monday open
LOOKBACKS  = [7, 14, 21, 28]

# sub-period boundaries
SUBS = [
    ("2020–2022", "2020-01-01", "2021-12-31"),
    ("2022–2023", "2022-01-01", "2023-12-31"),
    ("2024–2026", "2024-01-01", "2026-05-14"),
]

OUT_DIR = Path(__file__).resolve().parent
OUT_PNG = OUT_DIR / "feasibility_results.png"


# ══════════════════════════════════════════════════════════════════════════════
# 1. DATA
# ══════════════════════════════════════════════════════════════════════════════

def load_data() -> tuple[pd.Series, pd.DataFrame]:
    """
    Download BTC + ALT daily closes via yfinance.
    Returns (btc_log_ret, alts_log_ret) — daily, tz-naive.
    alts_log_ret columns = ['ETH-USD', 'SOL-USD', 'BNB-USD', 'ADA-USD', 'AVAX-USD']
    """
    tickers = [BTC] + ALTS
    raw = yf.download(tickers, start=START, end=END,
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        px = raw["Close"]
    else:
        px = raw[["Close"]]

    px.index = pd.to_datetime(px.index).tz_localize(None)
    px = px.dropna(how="all")

    log_ret = np.log(px / px.shift(1)).dropna(how="all")
    btc_ret  = log_ret[BTC].dropna()
    alts_ret = log_ret[ALTS].dropna(how="all")

    print(f"  [data] {len(btc_ret)} daily obs: "
          f"{btc_ret.index[0].date()} → {btc_ret.index[-1].date()}")
    print(f"  [data] ALT basket: {len(ALTS)} assets "
          f"({', '.join(a.replace('-USD','') for a in ALTS)})")
    return btc_ret, alts_ret


# ══════════════════════════════════════════════════════════════════════════════
# 2. SIGNAL CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════

def build_signal(btc_ret: pd.Series,
                 alts_ret: pd.DataFrame,
                 lookback: int = BASE_LB) -> pd.Series:
    """
    dominance_signal[T] = btc_cum_lb[T−1] − alt_mean_cum_lb[T−1]  (no look-ahead)
    Weekly (Friday rebalance). Shift(1) so signal at T uses data ≤ T−1.
    """
    btc_cum  = btc_ret.rolling(lookback, min_periods=lookback // 2).sum().shift(1)
    alt_cum  = alts_ret.rolling(lookback, min_periods=lookback // 2).sum().shift(1)
    alt_mean = alt_cum.mean(axis=1)
    sig_daily = btc_cum - alt_mean
    sig_weekly = sig_daily.resample("W-FRI").last()
    return sig_weekly.dropna()


def build_vol_scalars(btc_ret: pd.Series,
                      alts_ret: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """
    Annualized realized vol per asset, 20d window, shifted 1.
    Returns (btc_vol, alts_vol) — both shifted 1, resampled to weekly.
    """
    btc_rvol  = (btc_ret.rolling(VOL_WIN, min_periods=10).std() * np.sqrt(365)).shift(1)
    alts_rvol = (alts_ret.rolling(VOL_WIN, min_periods=10).std() * np.sqrt(365)).shift(1)
    return (btc_rvol.resample("W-FRI").last(),
            alts_rvol.resample("W-FRI").last())


# ══════════════════════════════════════════════════════════════════════════════
# 3. STEP 1 — IC TEST
# ══════════════════════════════════════════════════════════════════════════════

def ic_test(signal: pd.Series,
            btc_ret: pd.Series,
            alts_ret: pd.DataFrame) -> dict:
    """
    Predicted  = dominance_signal[T]  (BTC outperformance over ALT, lookback)
    Realized   = btc_next5 − alt_next5  (next-week BTC vs ALT relative return)
    IC = rank_corr(predicted, realized)
    """
    btc_w5  = btc_ret.resample("W-FRI").sum().shift(-1)   # next week BTC return
    alt_w5  = alts_ret.mean(axis=1).resample("W-FRI").sum().shift(-1)
    realized = (btc_w5 - alt_w5).dropna()

    df = pd.DataFrame({"sig": signal, "real": realized}).dropna()
    n  = len(df)
    if n < 10:
        return dict(ic=np.nan, t_stat=np.nan, n=n, sig=df["sig"], real=df["real"])

    ic = df["sig"].rank(pct=True).corr(df["real"].rank(pct=True))
    t  = ic * np.sqrt(max(n - 2, 0)) / np.sqrt(max(1 - ic**2, 1e-12))
    return dict(ic=ic, t_stat=t, n=n, sig=df["sig"], real=df["real"])


# ══════════════════════════════════════════════════════════════════════════════
# 4. STEP 2 — EQUITY CURVE
# ══════════════════════════════════════════════════════════════════════════════

def run_backtest(btc_ret:   pd.Series,
                 alts_ret:  pd.DataFrame,
                 lookback:  int = BASE_LB) -> dict:
    """
    Full strategy 2020–2026.
    Position sizing:
      btc_scalar  = clip(VOL_TGT / btc_rvol, 0.1, 2.0)
      alt_scalar  = clip(VOL_TGT / alt_rvol_mean, 0.1, 2.0)   ← use portfolio-level vol
      gross = btc_scalar + alt_scalar → scale down to GROSS_CAP if > GROSS_CAP

    Long leg = long {BTC | ALT basket}, short leg = short {ALT basket | BTC}.
    Returns dict: sharpe, sortino, maxdd, pf, win_rate, pnl_long, pnl_short, daily_pnl
    """
    signal   = build_signal(btc_ret, alts_ret, lookback)
    btc_rvol, alts_rvol = build_vol_scalars(btc_ret, alts_ret)

    # Mean ALT basket rvol
    alt_rvol_mean = alts_rvol.mean(axis=1)

    # Reindex to weekly signal dates (Friday)
    btc_rv_w  = btc_rvol.reindex(signal.index, method="ffill")
    alt_rv_w  = alt_rvol_mean.reindex(signal.index, method="ffill")

    # Vol scalars per leg
    btc_sc = (VOL_TGT / btc_rv_w.replace(0, np.nan)).clip(0.1, 2.0).fillna(1.0)
    alt_sc = (VOL_TGT / alt_rv_w.replace(0, np.nan)).clip(0.1, 2.0).fillna(1.0)

    # Normalize to GROSS_CAP
    gross = btc_sc + alt_sc
    scale = (GROSS_CAP / gross.where(gross > GROSS_CAP, GROSS_CAP)).fillna(1.0)
    btc_sc = btc_sc * scale
    alt_sc = alt_sc * scale

    # Build daily weights from weekly signal (Monday open to Friday close)
    # Positions are set Monday, held until next Monday → forward-fill within week
    direction = np.sign(signal)  # +1 = BTC season, −1 = alt season

    # Expand to daily (position set at Monday following Friday signal)
    all_days = pd.date_range(start=btc_ret.index[0], end=btc_ret.index[-1], freq="D")
    sig_daily = direction.reindex(all_days).shift(3)   # Friday → Monday (+3 cal days)
    sig_daily = sig_daily.ffill()

    btc_sc_d  = btc_sc.reindex(all_days).shift(3).ffill()
    alt_sc_d  = alt_sc.reindex(all_days).shift(3).ffill()

    # Keep only actual trading days
    trade_days = btc_ret.index
    sig_d  = sig_daily.reindex(trade_days).ffill()
    bsc_d  = btc_sc_d.reindex(trade_days).ffill()
    asc_d  = alt_sc_d.reindex(trade_days).ffill()
    b_ret  = btc_ret.reindex(trade_days).fillna(0.0)
    a_ret  = alts_ret.reindex(trade_days).fillna(0.0).mean(axis=1)

    # P&L per day
    # BTC season (+1): long BTC * bsc, short ALT * asc → pnl = bsc*btc_ret − asc*alt_ret
    # Alt season (−1): long ALT * asc, short BTC * bsc → pnl = asc*alt_ret − bsc*btc_ret
    pnl_long_btc  = bsc_d * b_ret * (sig_d == +1).astype(float)
    pnl_long_alt  = asc_d * a_ret * (sig_d == -1).astype(float)
    pnl_short_alt = -asc_d * a_ret * (sig_d == +1).astype(float)
    pnl_short_btc = -bsc_d * b_ret * (sig_d == -1).astype(float)

    pnl_long  = pnl_long_btc + pnl_long_alt
    pnl_short = pnl_short_alt + pnl_short_btc
    pnl_total = pnl_long + pnl_short

    # Transaction costs: charged once per week on Monday rebalance
    # Detect position flips (Monday = day after Friday signal change)
    rebal_days = trade_days[trade_days.dayofweek == 0]   # Mondays
    cost_series = pd.Series(0.0, index=trade_days)
    cost_series.loc[cost_series.index.isin(rebal_days)] = COST_RT * 2  # 2 legs

    pnl_net = pnl_total - cost_series

    def _metrics(pnl: pd.Series, label: str = "") -> dict:
        ann = pnl.mean() * 365
        vol = pnl.std() * np.sqrt(365)
        sr  = ann / (vol + 1e-12)
        downside = pnl[pnl < 0].std() * np.sqrt(365)
        sortino  = ann / (downside + 1e-12)
        cum  = (1 + pnl).cumprod()
        roll = cum.cummax()
        mdd  = float(((cum - roll) / roll).min())
        wins = (pnl > 0).sum()
        pf_n = pnl[pnl > 0].sum()
        pf_d = abs(pnl[pnl < 0].sum())
        pf   = pf_n / (pf_d + 1e-12)
        return dict(sharpe=sr, sortino=sortino, maxdd=mdd,
                    profit_factor=pf, win_rate=wins / len(pnl),
                    annual_ret=ann, cum=cum)

    full = _metrics(pnl_net)
    long_m  = _metrics(pnl_long.reindex(trade_days).fillna(0))
    short_m = _metrics(pnl_short.reindex(trade_days).fillna(0))

    # Sub-period Sharpe
    sub_sharpes = {}
    for label, s, e in SUBS:
        pnl_sub = pnl_net.loc[s:e]
        if len(pnl_sub) > 30:
            ann = pnl_sub.mean() * 365
            vol = pnl_sub.std() * np.sqrt(365)
            sub_sharpes[label] = ann / (vol + 1e-12)
        else:
            sub_sharpes[label] = np.nan

    # BTC season fraction
    btc_season_frac = float((sig_d == 1).sum() / len(sig_d))

    return dict(
        sharpe       = full["sharpe"],
        sortino      = full["sortino"],
        maxdd        = full["maxdd"],
        profit_factor= full["profit_factor"],
        win_rate     = full["win_rate"],
        annual_ret   = full["annual_ret"],
        cum          = full["cum"],
        long_sharpe  = long_m["sharpe"],
        short_sharpe = short_m["sharpe"],
        pnl_long     = pnl_long.reindex(trade_days).fillna(0),
        pnl_short    = pnl_short.reindex(trade_days).fillna(0),
        pnl_net      = pnl_net,
        sub_sharpes  = sub_sharpes,
        btc_season_frac = btc_season_frac,
        sig_daily    = sig_d,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 5. STEP 3 — LOOKBACK SENSITIVITY
# ══════════════════════════════════════════════════════════════════════════════

def lookback_sensitivity(btc_ret: pd.Series,
                         alts_ret: pd.DataFrame) -> dict[int, float]:
    """Sharpe for each lookback in LOOKBACKS."""
    results = {}
    for lb in LOOKBACKS:
        res = run_backtest(btc_ret, alts_ret, lookback=lb)
        results[lb] = res["sharpe"]
    return results


# ══════════════════════════════════════════════════════════════════════════════
# 6. PLOTS
# ══════════════════════════════════════════════════════════════════════════════

def make_plots(res: dict,
               sig: pd.Series,
               ic_data: dict,
               lb_sens: dict[int, float],
               res_monthly: dict | None = None) -> None:
    ncols = 3 if res_monthly else 2
    fig, axes_raw = plt.subplots(2, ncols, figsize=(7 * ncols, 10))
    axes = axes_raw  # keep 2-D indexing
    fig.suptitle("BTC Dominance Relative Momentum — Feasibility",
                 fontsize=14, fontweight="bold")

    pnl_net   = res["pnl_net"]
    pnl_long  = res["pnl_long"]
    pnl_short = res["pnl_short"]

    # Subplot 1: Equity curves
    ax = axes[0, 0]
    cum_net   = (1 + pnl_net).cumprod()
    cum_long  = (1 + pnl_long).cumprod()
    cum_short = (1 + pnl_short).cumprod()
    ax.plot(cum_net.index,   cum_net.values,   color="steelblue", linewidth=1.8,
            label=f"Net  (SR={res['sharpe']:+.2f})")
    ax.plot(cum_long.index,  cum_long.values,  color="green",     linewidth=1.0,
            alpha=0.7, linestyle="--",
            label=f"Long leg (SR={res['long_sharpe']:+.2f})")
    ax.plot(cum_short.index, cum_short.values, color="red",       linewidth=1.0,
            alpha=0.7, linestyle=":",
            label=f"Short leg (SR={res['short_sharpe']:+.2f})")
    ax.axhline(1.0, color="black", linewidth=0.6, linestyle="--")
    ax.set_title("Equity Curve (log-return compound)")
    ax.set_ylabel("NAV (start=1)")
    ax.legend(fontsize=8)
    ax.tick_params(labelsize=8)

    # Subplot 2: Dominance signal + BTC/alt shading
    ax = axes[0, 1]
    sig_plot = res["sig_daily"].resample("W-FRI").last().dropna()
    ax.bar(sig_plot.index, sig_plot.values,
           color=["#1565C0" if v > 0 else "#E53935" for v in sig_plot.values],
           alpha=0.7, width=5)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Dominance Signal  (blue=BTC season, red=alt season)")
    ax.set_ylabel("BTC − ALT 14d cum return")
    ax.tick_params(labelsize=8)
    btc_patch = mpatches.Patch(color="#1565C0", alpha=0.7, label="BTC season")
    alt_patch = mpatches.Patch(color="#E53935", alpha=0.7, label="Alt season")
    ax.legend(handles=[btc_patch, alt_patch], fontsize=8)

    # Subplot 3: Rolling 6-month Sharpe
    ax = axes[1, 0]
    roll_sr = (pnl_net.rolling(126, min_periods=30).mean() * 365 /
               (pnl_net.rolling(126, min_periods=30).std() * np.sqrt(365) + 1e-12))
    ax.plot(roll_sr.index, roll_sr.values, color="steelblue", linewidth=1.2)
    ax.axhline(0,   color="black",  linewidth=0.8, linestyle="--")
    ax.axhline(1.0, color="green",  linewidth=0.8, linestyle=":", alpha=0.8, label="SR=1.0")
    ax.axhline(-1.0,color="red",    linewidth=0.8, linestyle=":", alpha=0.8, label="SR=−1.0")
    ax.fill_between(roll_sr.index, 0, roll_sr.values,
                    where=roll_sr.values > 0, alpha=0.15, color="green")
    ax.fill_between(roll_sr.index, 0, roll_sr.values,
                    where=roll_sr.values < 0, alpha=0.15, color="red")
    ax.set_title("Rolling 6-Month Sharpe")
    ax.set_ylabel("Sharpe"); ax.legend(fontsize=8); ax.tick_params(labelsize=8)

    # Subplot 4: Lookback sensitivity
    ax = axes[1, 1]
    lbs = list(lb_sens.keys())
    srs = [lb_sens[k] for k in lbs]
    bar_colors = ["steelblue" if s > 0 else "tomato" for s in srs]
    bars = ax.bar([str(k) + "d" for k in lbs], srs, color=bar_colors, alpha=0.8, width=0.5)
    ax.axhline(0,   color="black",  linewidth=0.8)
    ax.axhline(1.5, color="green",  linewidth=0.8, linestyle="--", alpha=0.7, label="SR=1.5")
    ax.axhline(0.8, color="orange", linewidth=0.8, linestyle=":",  alpha=0.7, label="SR=0.8")
    for bar, v in zip(bars, srs):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.03 * np.sign(v),
                f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
    ax.set_title("Lookback Sensitivity (days)")
    ax.set_ylabel("Sharpe"); ax.legend(fontsize=8); ax.tick_params(labelsize=8)

    # Subplot 5: Monthly vs Weekly equity curve (only when monthly data provided)
    if res_monthly is not None:
        ax = axes[0, 2]
        cum_w = (1 + res["pnl_net"]).cumprod()
        cum_m = (1 + res_monthly["pnl_net"]).cumprod()
        ax.plot(cum_w.index, cum_w.values, color="steelblue", linewidth=1.2,
                linestyle="--", alpha=0.7,
                label=f"Weekly  (SR={res['sharpe']:+.2f})")
        ax.plot(cum_m.index, cum_m.values, color="darkorange", linewidth=1.8,
                label=f"Monthly (SR={res_monthly['sharpe']:+.2f})")
        ax.axhline(1.0, color="black", linewidth=0.6, linestyle="--")
        ax.set_title("Monthly vs Weekly Equity Curve")
        ax.set_ylabel("NAV (start=1)")
        ax.legend(fontsize=8); ax.tick_params(labelsize=8)

        ax = axes[1, 2]
        m_lbs = list(res_monthly.get("lb_sens", {}).keys())
        m_srs = [res_monthly["lb_sens"][k] for k in m_lbs]
        bar_colors = ["steelblue" if s > 0 else "tomato" for s in m_srs]
        bars = ax.bar([str(k) + "d" for k in m_lbs], m_srs,
                      color=bar_colors, alpha=0.8, width=0.5)
        ax.axhline(0,   color="black",  linewidth=0.8)
        ax.axhline(1.5, color="green",  linewidth=0.8, linestyle="--", alpha=0.7, label="SR=1.5")
        ax.axhline(0.8, color="orange", linewidth=0.8, linestyle=":",  alpha=0.7, label="SR=0.8")
        for bar, v in zip(bars, m_srs):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    v + 0.03 * (1 if v >= 0 else -1),
                    f"{v:.2f}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=9)
        ax.set_title("Monthly Lookback Sensitivity")
        ax.set_ylabel("Sharpe"); ax.legend(fontsize=8); ax.tick_params(labelsize=8)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [plot] Saved → {OUT_PNG.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 7. VERDICT
# ══════════════════════════════════════════════════════════════════════════════

def verdict(res: dict, ic: dict, lb_sens: dict) -> str:
    sr    = res["sharpe"]
    sl_sr = res["short_sharpe"]
    subs  = res["sub_sharpes"]
    t     = ic.get("t_stat", 0) or 0

    n_pos_subs = sum(1 for v in subs.values() if v is not None and v > 0)

    if sr < 0 or (not np.isnan(t) and abs(t) < 1.0):
        return "SKIP"
    elif sr > 1.5 and sl_sr > 0 and n_pos_subs >= 3:
        return "STRONG"
    elif sr >= 0.8:
        return "PROMISING"
    else:
        return "WEAK"


# ══════════════════════════════════════════════════════════════════════════════
# 8. MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 60)
    print("BTC DOMINANCE RELATIVE MOMENTUM — FEASIBILITY")
    print("=" * 60)

    # 1. Data
    print("\n[1] Loading data ...")
    btc_ret, alts_ret = load_data()

    # 2. Signal
    print("\n[2] Building base signal (14d lookback) ...")
    base_signal = build_signal(btc_ret, alts_ret, BASE_LB)

    # 3. IC test
    print("\n[3] IC test: signal vs realized relative return ...")
    ic = ic_test(base_signal, btc_ret, alts_ret)
    ic_str = f"{ic['ic']:+.4f}" if not np.isnan(ic.get("ic", np.nan) or np.nan) else "N/A"
    ts_str = f"{ic['t_stat']:+.3f}" if not np.isnan(ic.get("t_stat", np.nan) or np.nan) else "N/A"
    print(f"    IC={ic_str}  t={ts_str}  N={ic.get('n', 0)}")

    # 4. Backtest
    print("\n[4] Running backtest ...")
    res = run_backtest(btc_ret, alts_ret, BASE_LB)

    # 5. Lookback sensitivity
    print("\n[5] Lookback sensitivity ...")
    lb_sens = lookback_sensitivity(btc_ret, alts_ret)

    # 6. Print table
    def _pct(v) -> str:
        if v is None or np.isnan(v):
            return "    N/A"
        return f"{v*100:+.1f}%"

    def _f2(v, fmt="+.2f") -> str:
        if v is None or np.isnan(v):
            return "    N/A"
        return format(v, fmt)

    subs = res["sub_sharpes"]

    print(f"""
  ┌─────────────────────────────┬──────────┐
  │ Metric                      │  Value   │
  ├─────────────────────────────┼──────────┤
  │ IC (signal vs rel. return)  │{ic_str:>10}│
  │ IC t-stat                   │{ts_str:>10}│
  │ Full-period Sharpe          │{_f2(res['sharpe']):>10}│
  │ Sharpe 2020-2022            │{_f2(subs.get('2020–2022')):>10}│
  │ Sharpe 2022-2023            │{_f2(subs.get('2022–2023')):>10}│
  │ Sharpe 2024-2026            │{_f2(subs.get('2024–2026')):>10}│
  │ Max DD                      │{_pct(res['maxdd']):>10}│
  │ Profit factor               │{_f2(res['profit_factor'], '.2f'):>10}│
  │ Win rate                    │{_pct(res['win_rate']):>10}│
  │ Annual return               │{_pct(res['annual_ret']):>10}│
  │ Long leg Sharpe             │{_f2(res['long_sharpe']):>10}│
  │ Short leg Sharpe            │{_f2(res['short_sharpe']):>10}│
  │ % time BTC season           │{_pct(res['btc_season_frac']):>10}│
  └─────────────────────────────┴──────────┘""")

    print("\n  Lookback sensitivity:")
    for lb, sr in lb_sens.items():
        marker = "  ← base" if lb == BASE_LB else ""
        flag   = " **" if sr > 1.5 else (" *" if sr > 0.8 else "")
        print(f"    {lb:>3}d:  Sharpe {sr:+.2f}{flag}{marker}")

    # 7. Verdict
    v = verdict(res, ic, lb_sens)
    print(f"\n  VERDICT: {v}")
    if v == "STRONG":
        print("  → Proceed to walk-forward backtest with DSR correction.")
    elif v == "PROMISING":
        print("  → Investigate short leg drag. Consider long-only variant or tighter vol scaling.")
    elif v == "WEAK":
        print("  → Short leg consistently destroys value OR Sharpe < 0.8. "
              "Market-neutral assumption fails in crypto.")
    else:
        print("  → No reliable IC or negative Sharpe. Strategy does not have edge.")

    # Long vs short leg diagnostic
    print(f"\n  Long/Short leg diagnostic:")
    print(f"    Long leg  Sharpe : {_f2(res['long_sharpe'])}")
    print(f"    Short leg Sharpe : {_f2(res['short_sharpe'])}")
    if res['short_sharpe'] < -0.3:
        print("    ⚠  Short leg significantly negative — crypto losers mean-revert "
              "(consistent with 6.3 finding). Strategy value is in long leg only.")
    elif res['short_sharpe'] < 0:
        print("    Short leg slightly negative — market-neutral partially holds.")
    else:
        print("    Short leg positive — genuine market-neutral edge.")

    # 8. Monthly test
    res_m = run_monthly_section(btc_ret, alts_ret, res)

    # 9. Plots (with subplot 5 = monthly vs weekly equity)
    print("\n[7] Generating plots ...")
    make_plots(res, base_signal, ic, lb_sens, res_monthly=res_m)

    print("\n" + "=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
# MONTHLY REBALANCE TEST
# Same signal, same vol scaling — only frequency and cost model change.
# Rebalance: first Monday of each month (12×/year).
# Cost: 0.17% RT × 2 legs, charged on direction-flip months only.
# ══════════════════════════════════════════════════════════════════════════════

MONTHLY_LB  = 21                   # base lookback for monthly signal (≈1 month)
MONTHLY_LBS = [14, 21, 28, 42]     # lookback sensitivity sweep

WF_WINDOWS = [
    ("W1", "2020-01-01", "2021-12-31", "2022-01-01", "2022-12-31"),
    ("W2", "2020-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
    ("W3", "2020-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("W4", "2020-01-01", "2024-12-31", "2025-01-01", "2025-12-31"),
]


def _first_mondays(trade_days: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """First trading Monday of each calendar month."""
    s = pd.Series(trade_days, index=trade_days)
    mondays = s[s.index.dayofweek == 0]
    return mondays.groupby(mondays.index.to_period("M")).first().values


def build_monthly_signal(btc_ret: pd.Series,
                         alts_ret: pd.DataFrame,
                         lookback: int = MONTHLY_LB) -> pd.Series:
    """
    dominance[T] = btc_cum_lb[T-1] − alt_mean_cum_lb[T-1], shift(1).
    Sampled at first Monday of each month.
    """
    btc_cum   = btc_ret.rolling(lookback, min_periods=lookback // 2).sum().shift(1)
    alt_cum   = alts_ret.rolling(lookback, min_periods=lookback // 2).sum().shift(1)
    sig_daily = btc_cum - alt_cum.mean(axis=1)
    rebal     = _first_mondays(btc_ret.index)
    return sig_daily.reindex(rebal, method="ffill").dropna()


def ic_test_monthly(signal: pd.Series,
                    btc_ret: pd.Series,
                    alts_ret: pd.DataFrame,
                    lookback: int = MONTHLY_LB) -> dict:
    """
    predicted  = dominance_signal[T]
    realized   = btc_cum_21d[T+1:T+22] − alt_mean_cum_21d[T+1:T+22]
               = relative return over the next ~month (21 trading days)
    """
    btc_fwd  = btc_ret.rolling(lookback, min_periods=lookback // 2).sum().shift(-lookback)
    alt_fwd  = alts_ret.rolling(lookback, min_periods=lookback // 2).sum().shift(-lookback)
    rel_fwd  = (btc_fwd - alt_fwd.mean(axis=1))
    rebal    = _first_mondays(btc_ret.index)
    realized = rel_fwd.reindex(rebal, method="ffill").dropna()

    df = pd.DataFrame({"sig": signal, "real": realized}).dropna()
    n  = len(df)
    if n < 10:
        return dict(ic=np.nan, t_stat=np.nan, n=n)
    ic = df["sig"].rank(pct=True).corr(df["real"].rank(pct=True))
    t  = ic * np.sqrt(max(n - 2, 0)) / np.sqrt(max(1 - ic**2, 1e-12))
    return dict(ic=ic, t_stat=t, n=n)


def run_monthly_backtest(btc_ret: pd.Series,
                         alts_ret: pd.DataFrame,
                         lookback: int = MONTHLY_LB,
                         start: str = START,
                         end: str = END) -> dict:
    """
    Monthly rebalance backtest.
    Cost: COST_RT * 2 charged only on months where direction flips.
    Position held from rebal T to rebal T+1 (daily returns between two Mondays).
    """
    signal  = build_monthly_signal(btc_ret, alts_ret, lookback)
    signal  = signal.loc[start:end]
    if len(signal) < 6:
        nan_s = pd.Series(dtype=float)
        return dict(sharpe=np.nan, sortino=np.nan, maxdd=np.nan,
                    profit_factor=np.nan, win_rate=np.nan, annual_ret=np.nan,
                    long_sharpe=np.nan, short_sharpe=np.nan,
                    btc_season_frac=np.nan, pnl_net=nan_s,
                    pnl_long=nan_s, pnl_short=nan_s,
                    sub_sharpes={lbl: np.nan for lbl, *_ in SUBS},
                    cum=nan_s)

    direction = np.sign(signal)

    # Vol scalars at each monthly rebalance
    btc_rvol  = (btc_ret.rolling(VOL_WIN, min_periods=10).std() * np.sqrt(365)).shift(1)
    alt_rvol  = (alts_ret.rolling(VOL_WIN, min_periods=10).std() * np.sqrt(365)
                 ).mean(axis=1).shift(1)

    btc_rv_m = btc_rvol.reindex(signal.index, method="ffill")
    alt_rv_m = alt_rvol.reindex(signal.index, method="ffill")
    btc_sc   = (VOL_TGT / btc_rv_m.replace(0, np.nan)).clip(0.1, 2.0).fillna(1.0)
    alt_sc   = (VOL_TGT / alt_rv_m.replace(0, np.nan)).clip(0.1, 2.0).fillna(1.0)
    gross    = btc_sc + alt_sc
    scale    = (GROSS_CAP / gross.where(gross > GROSS_CAP, GROSS_CAP)).fillna(1.0)
    btc_sc   = btc_sc * scale
    alt_sc   = alt_sc * scale

    # Expand monthly positions to daily
    trade_days = btc_ret.loc[start:end].index
    all_days   = pd.date_range(trade_days[0], trade_days[-1], freq="D")

    dir_d  = direction.reindex(all_days).ffill()
    bsc_d  = btc_sc.reindex(all_days).ffill()
    asc_d  = alt_sc.reindex(all_days).ffill()

    dir_d  = dir_d.reindex(trade_days).ffill().fillna(0)
    bsc_d  = bsc_d.reindex(trade_days).ffill().fillna(1.0)
    asc_d  = asc_d.reindex(trade_days).ffill().fillna(1.0)
    b_ret  = btc_ret.reindex(trade_days).fillna(0.0)
    a_ret  = alts_ret.reindex(trade_days).fillna(0.0).mean(axis=1)

    # Daily P&L per leg (identical convention to weekly backtest)
    pnl_long  = (bsc_d * b_ret * (dir_d == +1).astype(float) +
                 asc_d * a_ret * (dir_d == -1).astype(float))
    pnl_short = (-asc_d * a_ret * (dir_d == +1).astype(float) +
                 -bsc_d * b_ret * (dir_d == -1).astype(float))
    pnl_total = pnl_long + pnl_short

    # Costs: charged only on direction-flip rebalance days
    cost_s = pd.Series(0.0, index=trade_days)
    rebal_in_period = signal.index[signal.index.isin(trade_days)]
    flips = direction.diff().abs().reindex(rebal_in_period).fillna(0)
    flip_days = flips[flips > 0].index
    cost_s.loc[cost_s.index.isin(flip_days)] = COST_RT * 2

    pnl_net = pnl_total - cost_s

    def _sr(pnl: pd.Series) -> float:
        ann = pnl.mean() * 365
        vol = pnl.std() * np.sqrt(365)
        return ann / (vol + 1e-12)

    def _metrics(pnl: pd.Series) -> dict:
        ann  = pnl.mean() * 365
        vol  = pnl.std() * np.sqrt(365)
        sr   = ann / (vol + 1e-12)
        ds   = pnl[pnl < 0].std() * np.sqrt(365)
        srt  = ann / (ds + 1e-12)
        cum  = (1 + pnl).cumprod()
        mdd  = float(((cum - cum.cummax()) / cum.cummax()).min())
        wins = (pnl > 0).sum()
        pf   = pnl[pnl > 0].sum() / (abs(pnl[pnl < 0].sum()) + 1e-12)
        return dict(sharpe=sr, sortino=srt, maxdd=mdd,
                    profit_factor=pf, win_rate=wins / max(len(pnl), 1),
                    annual_ret=ann, cum=cum)

    full   = _metrics(pnl_net)
    long_m = _metrics(pnl_long)
    short_m= _metrics(pnl_short)

    sub_sharpes = {}
    for label, s, e in SUBS:
        sub = pnl_net.loc[s:e]
        sub_sharpes[label] = _sr(sub) if len(sub) > 20 else np.nan

    btc_frac = float((dir_d == 1).sum() / max(len(dir_d), 1))
    n_flips  = int(flips.sum() / 2)   # /2 because diff changes by 2 on flip (+1→-1)
    est_cost = n_flips * COST_RT * 2 / ((len(trade_days) / 365)) * 100

    return dict(
        sharpe        = full["sharpe"],
        sortino       = full["sortino"],
        maxdd         = full["maxdd"],
        profit_factor = full["profit_factor"],
        win_rate      = full["win_rate"],
        annual_ret    = full["annual_ret"],
        cum           = full["cum"],
        long_sharpe   = long_m["sharpe"],
        short_sharpe  = short_m["sharpe"],
        pnl_net       = pnl_net,
        pnl_long      = pnl_long,
        pnl_short     = pnl_short,
        sub_sharpes   = sub_sharpes,
        btc_season_frac = btc_frac,
        n_flips       = n_flips,
        est_cost_pct  = est_cost,
    )


def monthly_lookback_sensitivity(btc_ret: pd.Series,
                                 alts_ret: pd.DataFrame) -> dict[int, float]:
    return {lb: run_monthly_backtest(btc_ret, alts_ret, lb)["sharpe"]
            for lb in MONTHLY_LBS}


def run_walkforward(btc_ret: pd.Series,
                    alts_ret: pd.DataFrame) -> list[dict]:
    """
    4-window expanding-train walk-forward on monthly backtest.
    Reports Sharpe + short_leg_sharpe per OOS window.
    """
    results = []
    for label, tr_s, tr_e, oos_s, oos_e in WF_WINDOWS:
        oos = run_monthly_backtest(btc_ret, alts_ret,
                                   lookback=MONTHLY_LB,
                                   start=oos_s, end=oos_e)
        results.append(dict(
            label        = label,
            oos_start    = oos_s,
            oos_end      = oos_e,
            sharpe       = oos["sharpe"],
            long_sharpe  = oos["long_sharpe"],
            short_sharpe = oos["short_sharpe"],
        ))
    return results


def verdict_monthly(res: dict) -> str:
    sr   = res["sharpe"]
    sl   = res["short_sharpe"]
    wf   = res.get("wf_results", [])
    n_pos = sum(1 for w in wf if not np.isnan(w["sharpe"]) and w["sharpe"] > 0.5)
    if np.isnan(sr) or sr < 0.3:
        return "SKIP"
    elif sr > 1.5 and sl > 0 and n_pos >= 3:
        return "STRONG"
    elif sr >= 0.8:
        return "PROMISING"
    else:
        return "WEAK"


def run_monthly_section(btc_ret: pd.Series,
                        alts_ret: pd.DataFrame,
                        res_weekly: dict) -> dict:
    """Run full monthly test and print comparison table + verdict."""
    print("\n" + "═" * 60)
    print("MONTHLY REBALANCE TEST (same signal, 12×/year)")
    print("═" * 60)

    print(f"\n[M1] Monthly IC test (21d lookback) ...")
    m_sig = build_monthly_signal(btc_ret, alts_ret, MONTHLY_LB)
    m_ic  = ic_test_monthly(m_sig, btc_ret, alts_ret, MONTHLY_LB)
    m_ic_s = f"{m_ic['ic']:+.4f}" if not np.isnan(m_ic.get("ic", np.nan) or np.nan) else "N/A"
    m_ts_s = f"{m_ic['t_stat']:+.3f}" if not np.isnan(m_ic.get("t_stat", np.nan) or np.nan) else "N/A"
    print(f"    IC={m_ic_s}  t={m_ts_s}  N={m_ic.get('n', 0)}")

    print(f"\n[M2] Monthly backtest (21d lookback) ...")
    res_m = run_monthly_backtest(btc_ret, alts_ret, MONTHLY_LB)

    print(f"\n[M3] Monthly lookback sensitivity ...")
    lb_m  = monthly_lookback_sensitivity(btc_ret, alts_ret)
    res_m["lb_sens"] = lb_m

    # Comparison table
    def _f2(v, fmt="+.2f") -> str:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "   N/A"
        return format(v, fmt)

    def _pct(v) -> str:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "   N/A"
        return f"{v*100:+.1f}%"

    w_subs = res_weekly["sub_sharpes"]
    m_subs = res_m["sub_sharpes"]
    w_cost = "  17.7%"   # fixed known value from analysis
    m_cost = f"{res_m['est_cost_pct']:+.1f}%" if not np.isnan(res_m["est_cost_pct"]) else "   N/A"

    print(f"""
  ┌─────────────────────────────┬──────────┬──────────┐
  │ Metric                      │  Weekly  │  Monthly │
  ├─────────────────────────────┼──────────┼──────────┤
  │ IC t-stat                   │   +3.571 │{m_ts_s:>10}│
  │ Full-period Sharpe          │{_f2(res_weekly['sharpe']):>10}│{_f2(res_m['sharpe']):>10}│
  │ Sharpe 2020–2022            │{_f2(w_subs.get('2020–2022')):>10}│{_f2(m_subs.get('2020–2022')):>10}│
  │ Sharpe 2022–2023            │{_f2(w_subs.get('2022–2023')):>10}│{_f2(m_subs.get('2022–2023')):>10}│
  │ Sharpe 2024–2026            │{_f2(w_subs.get('2024–2026')):>10}│{_f2(m_subs.get('2024–2026')):>10}│
  │ Max DD                      │{_pct(res_weekly['maxdd']):>10}│{_pct(res_m['maxdd']):>10}│
  │ Long leg Sharpe             │{_f2(res_weekly['long_sharpe']):>10}│{_f2(res_m['long_sharpe']):>10}│
  │ Short leg Sharpe            │{_f2(res_weekly['short_sharpe']):>10}│{_f2(res_m['short_sharpe']):>10}│
  │ Annual cost drag (est.)     │  {w_cost}│{m_cost:>10}│
  └─────────────────────────────┴──────────┴──────────┘""")

    print("\n  Monthly lookback sensitivity:")
    for lb, sr in lb_m.items():
        marker = "  ← base" if lb == MONTHLY_LB else ""
        flag   = " **" if sr > 1.5 else (" *" if sr > 0.8 else "")
        print(f"    {lb:>3}d:  Sharpe {sr:+.2f}{flag}{marker}")

    # Walk-forward (if Sharpe > 0.8)
    wf_results = []
    if not np.isnan(res_m["sharpe"]) and res_m["sharpe"] > 0.8:
        print(f"\n[M4] Walk-forward (Sharpe {res_m['sharpe']:+.2f} > 0.8) ...")
        wf_results = run_walkforward(btc_ret, alts_ret)
        print(f"\n  Walk-forward results:")
        print(f"  {'Window':<6} {'OOS period':<22} {'Sharpe':>8} {'Long SR':>8} {'Short SR':>9}")
        print(f"  {'─'*6} {'─'*22} {'─'*8} {'─'*8} {'─'*9}")
        for w in wf_results:
            pos = "✓" if w["sharpe"] > 0.5 else ("~" if w["sharpe"] > 0 else "✗")
            print(f"  {w['label']:<6} {w['oos_start']} → {w['oos_end']}  "
                  f"{_f2(w['sharpe']):>8}  "
                  f"{_f2(w['long_sharpe']):>8}  "
                  f"{_f2(w['short_sharpe']):>9}  {pos}")
        n_pos = sum(1 for w in wf_results if not np.isnan(w["sharpe"]) and w["sharpe"] > 0.5)
        print(f"\n  WF: {n_pos}/4 windows with Sharpe > 0.5")
    else:
        print(f"\n  [M4] WF skipped (Sharpe {res_m['sharpe']:+.2f} ≤ 0.8)")

    res_m["wf_results"] = wf_results

    # Verdict
    v = verdict_monthly(res_m)
    print(f"\n  VERDICT (monthly): {v}")
    if v == "STRONG":
        print("  → Proceed to live test. Monthly rebalance viable on HL perps.")
    elif v == "PROMISING":
        print("  → Signal survives cost reduction. "
              "Consider long-only variant (short leg drag) before live deployment.")
    elif v == "WEAK":
        print("  → Cost drag reduced but signal too weak. "
              "Monthly Sharpe < 0.8 — not viable.")
    else:
        print("  → Monthly Sharpe < 0.3 — cost reduction insufficient. "
              "Signal does not survive even monthly frequency. Close search.")

    return res_m


if __name__ == "__main__":
    main()
