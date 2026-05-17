"""
CS Stat Arb Feasibility — Combined Carry + Momentum (Long-Only Cross-Sectional)
=================================================================================
Signal: equal-weight (carry_z + momentum_z), cross-sectional ranking, long top-5.

Economic mechanism: assets with BOTH positive funding trend AND price momentum
are structurally bid. Combined signal is RELATIVE across assets → low correlation
with time-series TSMOM which is absolute (per-asset).

Data:
  Funding: data/funding_carry/{ASSET}_funding.csv (174 assets, 8h intervals)
  Prices:  HL candleSnapshot 1d API → cached to strategies/cs_stat_arb/data/

Verdict:
  GO:   t > 2.0, combo beats components, corr_TSMOM < 0.40, IC > 0 in bear
  WEAK: t 1.5–2.0 OR combo <= max(components)
  SKIP: t < 1.5 OR corr_TSMOM > 0.60 OR IC < 0 in bear (just beta)
"""
from __future__ import annotations

import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parents[2]
FUNDING_DIR = REPO_ROOT / "data" / "funding_carry"
CACHE_DIR   = Path(__file__).resolve().parent / "data"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Parameters ────────────────────────────────────────────────────────────────
START        = "2022-01-01"
END          = "2026-05-14"
BEAR_END     = "2023-12-31"
BULL_START   = "2024-01-01"
MIN_DAYS     = 365
MIN_VOL_USD  = 500_000       # mean daily USD volume (HL notional)
TOP_N        = 5
CARRY_WIN    = 14            # calendar days for carry lookback
MOM_WIN      = 14            # calendar days for momentum lookback
VOL_WIN      = 20            # days for realized vol (position sizing, not used in IC)
VOL_TGT      = 0.15          # annualized vol target (for pos sizing reference)
IC_GO        = 2.0
IC_WEAK      = 1.5
CORR_SKIP    = 0.60
CORR_WARN    = 0.40
HL_URL       = "https://api.hyperliquid.xyz/info"
EPOCH_MS     = 1_640_000_000_000   # ~2022-01-01 UTC


# ══════════════════════════════════════════════════════════════════════════════
# 1. FUNDING DATA
# ══════════════════════════════════════════════════════════════════════════════

def load_funding_daily() -> pd.DataFrame:
    """
    Load all {ASSET}_funding.csv from FUNDING_DIR.
    Format: timestamp, asset, funding_rate_1h (actually 8h rate at 0h/8h/16h UTC).
    Returns wide DataFrame: daily mean 8h funding rate × asset (tz-naive).
    """
    files = sorted(FUNDING_DIR.glob("*_funding.csv"))
    series: dict[str, pd.Series] = {}
    for f in files:
        asset = f.stem.replace("_funding", "")
        if asset == "funding_rates_combined":
            continue
        try:
            df = pd.read_csv(f, parse_dates=["timestamp"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)
            df = df.set_index("timestamp").sort_index()
            # 3 records/day (0h,8h,16h) → daily mean = mean 8h funding rate per day
            daily = df["funding_rate_1h"].resample("D").mean()
            series[asset] = daily
        except Exception as e:
            print(f"  [funding] {asset}: skip ({e})")

    wide = pd.DataFrame(series)
    wide = wide[(wide.index >= START) & (wide.index <= END)]
    print(f"  [funding] {len(wide.columns)} assets, "
          f"{wide.index[0].date()} → {wide.index[-1].date()}")
    return wide


# ══════════════════════════════════════════════════════════════════════════════
# 2. PRICE DATA (HL daily candles)
# ══════════════════════════════════════════════════════════════════════════════

def _post_hl(payload: dict, retries: int = 2) -> list:
    for attempt in range(retries):
        try:
            r = requests.post(HL_URL, json=payload, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return []
    return []


def fetch_price_daily(coin: str) -> pd.DataFrame:
    """
    Fetch 1d OHLCV from HL candleSnapshot. Cached to CACHE_DIR/{coin}_1d.csv.
    Returns DataFrame indexed by tz-naive date, columns: close, volume_usd.
    Volume: HL returns USD notional for perp candles.
    """
    cache = CACHE_DIR / f"{coin}_1d.csv"
    if cache.exists():
        df = pd.read_csv(cache, parse_dates=["date"])
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
        return df.set_index("date")

    end_ms = int(pd.Timestamp("2026-05-15", tz="UTC").timestamp() * 1000)
    raw = _post_hl({
        "type": "candleSnapshot",
        "req": {
            "coin":      coin,
            "interval":  "1d",
            "startTime": EPOCH_MS,
            "endTime":   end_ms,
        }
    })
    if not raw:
        return pd.DataFrame()

    rows = []
    for c in raw:
        try:
            rows.append({
                "date":       pd.Timestamp(int(c["t"]), unit="ms", tz="UTC").normalize(),
                "close":      float(c["c"]),
                "volume_usd": float(c["v"]),
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = (pd.DataFrame(rows)
          .drop_duplicates("date")
          .sort_values("date")
          .set_index("date"))
    df.index = df.index.tz_localize(None)
    df.to_csv(cache)
    return df


def load_prices(assets: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load/fetch daily close and volume for all assets.
    Returns (close_wide, vol_wide): date × asset, tz-naive.
    """
    closes: dict[str, pd.Series] = {}
    vols:   dict[str, pd.Series] = {}
    failed = []

    for coin in assets:
        df = fetch_price_daily(coin)
        if df.empty or len(df) < MIN_DAYS:
            failed.append(coin)
            continue
        closes[coin] = df["close"]
        vols[coin]   = df["volume_usd"]
        time.sleep(0.10)

    if failed:
        print(f"  [prices] {len(failed)} failed/short: "
              f"{', '.join(failed[:10])}{'...' if len(failed) > 10 else ''}")

    close_wide = pd.DataFrame(closes)
    vol_wide   = pd.DataFrame(vols)
    close_wide = close_wide[(close_wide.index >= START) & (close_wide.index <= END)]
    vol_wide   = vol_wide[(vol_wide.index >= START) & (vol_wide.index <= END)]
    return close_wide, vol_wide


# ══════════════════════════════════════════════════════════════════════════════
# 3. UNIVERSE FILTER
# ══════════════════════════════════════════════════════════════════════════════

def build_universe(
    funding_wide: pd.DataFrame,
    close_wide:   pd.DataFrame,
    vol_wide:     pd.DataFrame,
) -> list[str]:
    """Apply ≥365d funding, ≥365d price, mean daily vol > $500K."""
    candidates = sorted(set(funding_wide.columns) & set(close_wide.columns))
    universe = []
    relaxed  = []  # fallback if vol filter is too strict

    for asset in candidates:
        f_days   = funding_wide[asset].notna().sum()
        p_days   = close_wide[asset].notna().sum()
        mean_vol = vol_wide[asset].mean() if asset in vol_wide.columns else 0.0
        passes_base = f_days >= MIN_DAYS and p_days >= MIN_DAYS
        if passes_base:
            relaxed.append(asset)
        if passes_base and mean_vol >= MIN_VOL_USD:
            universe.append(asset)

    # Fallback: if vol filter too strict, relax it
    if len(universe) < 10:
        print(f"  [universe] vol filter too strict ({len(universe)} assets) — relaxing to any vol>0")
        universe = [a for a in relaxed
                    if a in vol_wide.columns and vol_wide[a].mean() > 0]

    print(f"  Universe: {len(universe)} assets after filters")
    return universe


# ══════════════════════════════════════════════════════════════════════════════
# 4. WEEKLY SIGNALS
# ══════════════════════════════════════════════════════════════════════════════

def _cs_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score each row (no look-ahead, uses only that row's assets)."""
    mu = df.mean(axis=1)
    sd = df.std(axis=1)
    return df.sub(mu, axis=0).div(sd + 1e-12, axis=0)


def build_weekly_signals(
    funding_daily: pd.DataFrame,
    close_daily:   pd.DataFrame,
    assets:        list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    carry_score[i,T]    = mean(funding[i, T-14:T-1]) — 14d rolling mean, shift(1)
    momentum_score[i,T] = sum(log_ret[i, T-14:T-1]) — 14d log return, shift(1)
    Both shifted 1 day so signal at Friday T uses only data ≤ Thursday T-1.
    Returns (carry_z, mom_z, combo) — weekly W-FRI, cross-sectionally z-scored.
    """
    fd = funding_daily[assets].copy()
    cd = close_daily[assets].copy()

    # Carry: 14-day rolling mean of daily funding, shifted 1
    carry_raw = fd.shift(1).rolling(CARRY_WIN, min_periods=7).mean()

    # Momentum: 14-day cumulative log return, shifted 1
    log_ret   = np.log(cd / cd.shift(1))
    mom_raw   = log_ret.shift(1).rolling(MOM_WIN, min_periods=7).sum()

    # Resample to Friday weekly
    carry_w   = carry_raw.resample("W-FRI").last()
    mom_w     = mom_raw.resample("W-FRI").last()

    carry_z   = _cs_zscore(carry_w)
    mom_z     = _cs_zscore(mom_w)
    combo     = 0.5 * carry_z + 0.5 * mom_z   # equal weight per spec

    return carry_z, mom_z, combo


# ══════════════════════════════════════════════════════════════════════════════
# 5. TSMOM v3 SIGNAL (cross-sectional benchmark)
# ══════════════════════════════════════════════════════════════════════════════

def build_tsmom_signal(close_daily: pd.DataFrame, assets: list[str]) -> pd.DataFrame:
    """
    TSMOM v3: tanh(cumret_28d / (vol_28d × sqrt(28))), shift(1), weekly.
    Computes independently per asset (time-series signal, not cross-sectional).
    """
    cd      = close_daily[assets].copy()
    log_ret = np.log(cd / cd.shift(1))
    cum28   = log_ret.rolling(28, min_periods=14).sum()
    vol28   = log_ret.rolling(28, min_periods=14).std() * np.sqrt(28)
    signal  = np.tanh(cum28 / (vol28 + 1e-12))
    return signal.shift(1).resample("W-FRI").last()


# ══════════════════════════════════════════════════════════════════════════════
# 6. OUTCOME
# ══════════════════════════════════════════════════════════════════════════════

def build_outcome(close_daily: pd.DataFrame, assets: list[str]) -> pd.DataFrame:
    """
    Next-week log return: outcome[i,T] = log(close[T+5] / close[T]).
    Implemented as weekly close-to-close log return shifted -1 (next period).
    """
    cd  = close_daily[assets].copy()
    ret = np.log(cd / cd.shift(1))
    w   = ret.resample("W-FRI").sum()
    return w.shift(-1)


# ══════════════════════════════════════════════════════════════════════════════
# 7. IC METRICS
# ══════════════════════════════════════════════════════════════════════════════

def _rank_corr(a: pd.Series, b: pd.Series) -> float:
    return a.rank(pct=True).corr(b.rank(pct=True))


def pooled_ic(signal: pd.DataFrame, outcome: pd.DataFrame) -> dict:
    """
    Pooled rank IC across all (asset, week) pairs.
    Also returns weekly IC time series for ICIR and rolling plots.
    """
    sig, out = signal.align(outcome, join="inner")

    # Per-week IC time series
    weekly_ic_vals = {}
    for dt in sig.index:
        s_row = sig.loc[dt].dropna()
        o_row = out.loc[dt].dropna()
        common = s_row.index.intersection(o_row.index)
        if len(common) < 5:
            continue
        weekly_ic_vals[dt] = _rank_corr(s_row[common], o_row[common])

    weekly_ic = pd.Series(weekly_ic_vals).dropna()

    if len(weekly_ic) < 10:
        return dict(ic=np.nan, t_stat=np.nan, icir=np.nan, n=0, weekly_ic=weekly_ic)

    # Pooled IC (flatten all (i,T) pairs)
    all_s, all_o = [], []
    for dt in sig.index:
        s_row = sig.loc[dt].dropna()
        o_row = out.loc[dt].dropna()
        common = s_row.index.intersection(o_row.index)
        all_s.extend(s_row[common].tolist())
        all_o.extend(o_row[common].tolist())

    ps, po = pd.Series(all_s), pd.Series(all_o)
    ic     = _rank_corr(ps, po)
    n      = len(ps)
    t_stat = ic * np.sqrt(max(n - 2, 0)) / np.sqrt(max(1 - ic**2, 1e-12))
    icir   = float(weekly_ic.mean() / (weekly_ic.std() + 1e-12))

    return dict(ic=ic, t_stat=t_stat, icir=icir, n=n, weekly_ic=weekly_ic)


# ══════════════════════════════════════════════════════════════════════════════
# 8. CONCENTRATION / TURNOVER
# ══════════════════════════════════════════════════════════════════════════════

def portfolio_turnover(combo: pd.DataFrame) -> float:
    """Mean weekly turnover: fraction of long assets replaced."""
    prev: set = set()
    turns = []
    for dt in combo.index:
        row = combo.loc[dt].dropna()
        if len(row) < TOP_N:
            continue
        cur = set(row.nlargest(TOP_N).index)
        if prev:
            turns.append(1.0 - len(cur & prev) / TOP_N)
        prev = cur
    return float(np.mean(turns)) if turns else np.nan


# ══════════════════════════════════════════════════════════════════════════════
# 9. PLOTS
# ══════════════════════════════════════════════════════════════════════════════

def make_plots(
    carry_ic:            dict,
    mom_ic:              dict,
    combo_ic:            dict,
    tsmom_corr_by_asset: pd.Series,
    valid_mask:          pd.DataFrame,
    out_path:            Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("CS Stat Arb — Carry+Momentum Feasibility (Long-Only)",
                 fontsize=14, fontweight="bold")

    # 1: Rolling 52w IC — combo
    ax = axes[0, 0]
    wic = combo_ic.get("weekly_ic", pd.Series(dtype=float))
    if len(wic) > 10:
        roll = wic.rolling(52, min_periods=10).mean()
        ax.plot(roll.index, roll.values, color="steelblue", linewidth=1.5, label="52w rolling IC")
        ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
        ax.axhline(0.05,  color="green",  linewidth=0.8, linestyle=":", alpha=0.8, label="IC=+0.05")
        ax.axhline(-0.05, color="red",    linewidth=0.8, linestyle=":", alpha=0.8, label="IC=−0.05")
        ax.fill_between(roll.index, 0, roll.values,
                        where=roll.values > 0, alpha=0.15, color="green")
        ax.fill_between(roll.index, 0, roll.values,
                        where=roll.values < 0, alpha=0.15, color="red")
    ax.set_title("Rolling 52w IC — Combined Signal")
    ax.set_ylabel("IC"); ax.legend(fontsize=8); ax.tick_params(labelsize=8)

    # 2: Component IC bar chart
    ax = axes[0, 1]
    labels  = ["Carry z-score", "Momentum z-score", "Combined"]
    ic_vals = [carry_ic.get("ic") or 0, mom_ic.get("ic") or 0, combo_ic.get("ic") or 0]
    ts_vals = [carry_ic.get("t_stat") or 0, mom_ic.get("t_stat") or 0,
               combo_ic.get("t_stat") or 0]
    colors  = ["#2196F3", "#FF9800", "#4CAF50"]
    x, w    = np.arange(3), 0.35
    ax.bar(x - w/2, ic_vals, w, label="IC", color=colors, alpha=0.75)
    ax2 = ax.twinx()
    ax2.bar(x + w/2, ts_vals, w, label="t-stat", color=colors, alpha=0.40, hatch="//")
    ax2.axhline(IC_GO,   color="green",  linewidth=1.2, linestyle="--", label=f"t={IC_GO}")
    ax2.axhline(IC_WEAK, color="orange", linewidth=1.0, linestyle=":", label=f"t={IC_WEAK}")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("IC"); ax2.set_ylabel("t-statistic")
    ax.set_title("Component IC Attribution"); ax.tick_params(labelsize=8)
    ax2.legend(fontsize=7, loc="upper right"); ax2.tick_params(labelsize=8)

    # 3: Universe size over time
    ax = axes[1, 0]
    if not valid_mask.empty:
        monthly = valid_mask.resample("ME").last().notna().sum(axis=1)
        ax.fill_between(monthly.index, monthly.values,
                        alpha=0.5, color="steelblue", step="post")
        ax.set_title("Universe Size Over Time (assets with valid signal)")
        ax.set_ylabel("# Assets"); ax.tick_params(labelsize=8)
    else:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_title("Universe Size")

    # 4: Per-asset combo vs TSMOM correlation
    ax = axes[1, 1]
    if not tsmom_corr_by_asset.empty:
        sc = tsmom_corr_by_asset.sort_values()
        bar_colors = [
            "red"       if v > CORR_SKIP else
            "orange"    if v > CORR_WARN else
            "steelblue" for v in sc.values
        ]
        ax.barh(range(len(sc)), sc.values, color=bar_colors, alpha=0.8)
        ax.set_yticks(range(len(sc)))
        ax.set_yticklabels(sc.index, fontsize=6)
        ax.axvline(CORR_WARN, color="orange", linewidth=1, linestyle="--",
                   label=f"r={CORR_WARN} warn")
        ax.axvline(CORR_SKIP, color="red",    linewidth=1, linestyle="--",
                   label=f"r={CORR_SKIP} skip")
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title("Combo vs TSMOM Corr (by Asset)")
        ax.set_xlabel("Rank Correlation"); ax.legend(fontsize=7)
        ax.tick_params(labelsize=7)
    else:
        ax.text(0.5, 0.5, "N/A", ha="center", va="center")
        ax.set_title("Combo vs TSMOM Corr")

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [plot] Saved → {out_path.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 10. MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 65)
    print("CS STAT ARB FEASIBILITY — CARRY + MOMENTUM (LONG-ONLY)")
    print("=" * 65)

    # 1. Funding
    print("\n[1] Loading funding rates ...")
    funding_daily = load_funding_daily()

    # 2. Prices
    print(f"\n[2] Fetching daily prices ({len(funding_daily.columns)} assets) ...")
    close_daily, vol_daily = load_prices(sorted(funding_daily.columns))
    print(f"      Price data: {len(close_daily.columns)} assets loaded")

    # 3. Universe
    print("\n[3] Applying universe filters ...")
    universe = build_universe(funding_daily, close_daily, vol_daily)

    if len(universe) < 8:
        print(f"\n  ABORT: only {len(universe)} assets — insufficient for CS test")
        return

    fd_u  = funding_daily[universe]
    cd_u  = close_daily[universe]

    # 4. Signals
    print("\n[4] Building weekly carry+momentum signals ...")
    carry_z, mom_z, combo = build_weekly_signals(fd_u, cd_u, universe)

    # 5. Outcome
    outcome = build_outcome(cd_u, universe)

    # 6. TSMOM benchmark
    print("[5] Computing TSMOM v3 benchmark ...")
    tsmom = build_tsmom_signal(cd_u, universe)

    # 7. IC tests
    print("[6] Running IC tests ...")
    carry_ic = pooled_ic(carry_z, outcome)
    mom_ic   = pooled_ic(mom_z,   outcome)
    combo_ic = pooled_ic(combo,   outcome)

    # 8. TSMOM correlation (per-asset pooled rank-corr of combo vs tsmom)
    corr_vals: dict[str, float] = {}
    common_idx = combo.index.intersection(tsmom.index)
    for asset in universe:
        if asset not in combo.columns or asset not in tsmom.columns:
            continue
        s = combo.loc[common_idx, asset].dropna()
        t = tsmom.loc[common_idx, asset].dropna()
        idx = s.index.intersection(t.index)
        if len(idx) < 20:
            continue
        corr_vals[asset] = _rank_corr(s[idx], t[idx])

    tsmom_corr_by_asset = pd.Series(corr_vals)
    tsmom_corr_mean = float(tsmom_corr_by_asset.mean()) if len(tsmom_corr_by_asset) > 0 else np.nan

    # 9. Sub-period IC
    def sub_ic(sig: pd.DataFrame, out: pd.DataFrame, s: str, e: str) -> dict:
        return pooled_ic(sig.loc[s:e], out.loc[s:e])

    ic_bear = sub_ic(combo, outcome, START, BEAR_END)
    ic_bull = sub_ic(combo, outcome, BULL_START, END)

    # 10. Concentration / turnover
    turnover = portfolio_turnover(combo)

    # 11. Print table
    def _f(d: dict, key: str, fmt: str = "+.4f") -> str:
        v = d.get(key)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "   N/A"
        return format(v, fmt)

    print(f"\n  Universe : {len(universe)} assets")
    print(f"  Weeks    : {len(combo.index)}")
    print(f"  Pooled N : {combo_ic['n']:,} (asset,week) pairs\n")

    rows = [
        ("Carry z-score alone",        carry_ic, "+.4f", "+.3f", "+.3f"),
        ("Momentum z-score alone",     mom_ic,   "+.4f", "+.3f", "+.3f"),
        ("Combined (0.5/0.5)",         combo_ic, "+.4f", "+.3f", "+.3f"),
    ]

    print("  ┌─────────────────────────────┬────────┬────────┬──────────────┐")
    print("  │ Signal                      │   IC   │ t-stat │    ICIR      │")
    print("  ├─────────────────────────────┼────────┼────────┼──────────────┤")
    for label, d, fi, ft, fr in rows:
        ic_s   = _f(d, "ic",     fi)
        ts_s   = _f(d, "t_stat", ft)
        icir_s = _f(d, "icir",   fr)
        print(f"  │ {label:<27} │{ic_s:>8}│{ts_s:>8}│{icir_s:>14}│")
    print("  ├─────────────────────────────┼────────┼────────┼──────────────┤")

    tc = format(tsmom_corr_mean, "+.3f") if not np.isnan(tsmom_corr_mean) else "   N/A"
    bi = _f(ic_bear, "ic"); bt = _f(ic_bear, "t_stat", "+.3f"); bir = _f(ic_bear, "icir", "+.3f")
    ui = _f(ic_bull, "ic"); ut = _f(ic_bull, "t_stat", "+.3f"); uir = _f(ic_bull, "icir", "+.3f")
    tv = f"{turnover*100:.1f}%" if not np.isnan(turnover) else "   N/A"

    print(f"  │ {'Corr with TSMOM v3':<27} │{tc:>8}│{'  —':>8}│{'  —':>14}│")
    print(f"  │ {'IC bear sub-period (≤2023)':<27} │{bi:>8}│{bt:>8}│{bir:>14}│")
    print(f"  │ {'IC bull sub-period (2024+)':<27} │{ui:>8}│{ut:>8}│{uir:>14}│")
    print(f"  │ {'Mean weekly portfolio turn':<27} │{tv:>8}│{'  —':>8}│{'  —':>14}│")
    print("  └─────────────────────────────┴────────┴────────┴──────────────┘")

    # 12. Verdict
    t_val  = combo_ic.get("t_stat")
    ic_val = combo_ic.get("ic") or 0.0
    comp_max = max(
        carry_ic.get("ic") or -np.inf,
        mom_ic.get("ic")   or -np.inf,
    )
    combo_wins = ic_val > comp_max
    bear_pos   = (ic_bear.get("ic") or -1.0) > 0
    t_ok       = t_val is not None and not np.isnan(t_val)

    print()
    if not t_ok:
        verdict = "SKIP"
        reason  = "IC computation failed — insufficient data"
    elif tsmom_corr_mean > CORR_SKIP:
        verdict = "SKIP"
        reason  = (f"corr_TSMOM={tsmom_corr_mean:.2f} > {CORR_SKIP} "
                   "— combined signal is a TSMOM proxy")
    elif not bear_pos:
        verdict = "SKIP"
        reason  = "IC < 0 in bear sub-period (≤2023) — pure beta exposure, not alpha"
    elif abs(t_val) < IC_WEAK:
        verdict = "SKIP"
        reason  = f"t-stat={t_val:+.2f} < {IC_WEAK} — no reliable IC"
    elif abs(t_val) >= IC_GO and combo_wins and tsmom_corr_mean < CORR_WARN:
        verdict = "GO"
        reason  = (f"t={t_val:+.2f} > {IC_GO}, combo beats components, "
                   f"corr_TSMOM={tsmom_corr_mean:.2f} < {CORR_WARN}, IC>0 in bear")
    else:
        verdict = "WEAK"
        if not combo_wins:
            dom = "carry" if (carry_ic.get("ic") or 0) > (mom_ic.get("ic") or 0) else "momentum"
            reason = f"t={t_val:+.2f} but {dom} dominates — test {dom}-only variant"
        elif tsmom_corr_mean >= CORR_WARN:
            reason = (f"t={t_val:+.2f} but corr_TSMOM={tsmom_corr_mean:.2f} "
                      f"in [{CORR_WARN},{CORR_SKIP}] — partial TSMOM overlap")
        else:
            reason = f"t={t_val:+.2f} in [{IC_WEAK},{IC_GO}) — marginal signal"

    print(f"  VERDICT : {verdict}")
    print(f"  Reason  : {reason}")

    if verdict == "GO":
        n_trades = int(52 * TOP_N * turnover) if not np.isnan(turnover) else "?"
        print(f"\n  → Proceed to backtest.")
        print(f"    Expected annual trades: ~{n_trades}  (52 × {TOP_N} × {turnover*100:.0f}% turnover)")
    elif verdict == "WEAK":
        dom = "carry" if (carry_ic.get("ic") or 0) > (mom_ic.get("ic") or 0) else "momentum"
        print(f"\n  → Test {dom}-only signal. Drop weaker component.")
    else:
        print(f"\n  → Combined signal has no IC or is a TSMOM proxy.")
        print(f"    Close Strategy C search or pivot to intraday/cost-efficiency improvements.")

    # 13. Plots
    print("\n[7] Generating plots ...")
    out_path = Path(__file__).resolve().parent / "feasibility_results.png"
    make_plots(
        carry_ic, mom_ic, combo_ic,
        tsmom_corr_by_asset,
        combo.notna().astype(float),
        out_path,
    )

    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
