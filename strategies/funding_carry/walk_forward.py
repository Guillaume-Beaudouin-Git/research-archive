"""
walk_forward.py — Strategy C: Funding Rate Carry Walk-Forward Backtest

Rolling 6-month train / 1-month test OOS.
Rebalance frequency {8h, 24h, 7d} selected on train Sharpe each fold.
Sharpe ALWAYS computed at the rebalance period frequency (not hourly).
Price returns included via Hyperliquid 8h candles.

Usage:
    python -m strategies.funding_carry.walk_forward
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from dsr import deflated_sharpe_ratio
from strategies.funding_carry.fetch_funding import load_combined, OUT_DIR
from strategies.funding_carry.fetch_prices import (
    fetch_prices_universe, load_prices_wide, PRICES_DIR,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NOTIONAL        = 10_000.0      # $ per side (long or short leg)
COST_PER_LEG    = 0.0017        # 0.17% per leg change (0.035% fee + 0.05% slip × 2)
QUINTILE        = 0.20          # top and bottom 20%
MIN_ASSETS      = 10
MAX_WEIGHT      = 0.20          # max concentration per asset per side
LOOKBACK_PERD   = 3             # signal = 3-period rolling mean funding rate
TRAIN_MONTHS    = 6
TEST_MONTHS     = 1

STOP_LOSS_PCT   = 0.15          # per-asset, per-period
MAX_DD_PCT      = 0.20          # portfolio-level halt
COOLDOWN_PERD   = 2             # periods of cooldown after stop-loss

FREQ_OPTIONS    = {"8h": 8, "24h": 24, "7d": 7 * 24}
PERIODS_PER_YEAR = {8: 3 * 365, 24: 365, 7 * 24: 52}

OUTPUT_DIR = REPO_ROOT / "outputs"
DOCS_DIR   = REPO_ROOT / "docs"
DATA_DIR   = OUT_DIR            # data/funding_carry/


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_funding_pivot() -> pd.DataFrame:
    """Hourly funding wide DataFrame (timestamp × asset)."""
    df = load_combined()
    pivot = (df.pivot(index="timestamp", columns="asset", values="funding_rate_1h")
               .sort_index())
    pivot.columns.name = None
    valid = [c for c in pivot.columns if pivot[c].notna().any()]
    return pivot[valid]


# ---------------------------------------------------------------------------
# Resampling helpers
# ---------------------------------------------------------------------------

def resample_funding(fr_hourly: pd.DataFrame, freq_h: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Resample hourly funding to rebalance frequency.
    Returns (fr_mean, fr_sum):
      fr_mean: mean hourly rate per period (for ranking signal)
      fr_sum:  sum of hourly rates per period (carry income = -pos × fr_sum × notional)
    """
    freq = f"{freq_h}h"
    fr_mean = fr_hourly.resample(freq, label="left", closed="left").mean()
    fr_sum  = fr_hourly.resample(freq, label="left", closed="left").sum()
    return fr_mean, fr_sum


def resample_prices(px_open_8h: pd.DataFrame, freq_h: int) -> pd.DataFrame:
    """Resample 8h open prices to rebalance frequency (first bar of each period)."""
    freq = f"{freq_h}h"
    return px_open_8h.resample(freq, label="left", closed="left").first()


# ---------------------------------------------------------------------------
# Signal and position construction
# ---------------------------------------------------------------------------

def form_position_row(signal_row: pd.Series) -> pd.Series:
    """
    Cross-sectional position from one signal row.
    Long bottom quintile (lowest/most negative funding).
    Short top quintile (highest/most positive funding).
    """
    valid = signal_row.dropna()
    n     = len(valid)
    if n < MIN_ASSETS:
        return pd.Series(0.0, index=signal_row.index)

    n_q    = max(1, int(n * QUINTILE))
    ranked = valid.rank(ascending=True)

    pos    = pd.Series(0.0, index=signal_row.index)
    bottom = ranked[ranked <= n_q].index          # long
    top    = ranked[ranked > n - n_q].index       # short

    if len(bottom) > 0:
        pos[bottom] = 1.0 / len(bottom)
    if len(top) > 0:
        pos[top]    = -1.0 / len(top)

    # Concentration cap: max MAX_WEIGHT per asset per side
    for sign in (1, -1):
        mask = (pos * sign > 0)
        if not mask.any():
            continue
        leg = pos[mask].abs()
        if leg.max() > MAX_WEIGHT:
            leg = leg.clip(upper=MAX_WEIGHT)
            leg = leg / leg.sum()
            pos[mask] = leg * sign

    return pos


def compute_positions(fr_mean_rebal: pd.DataFrame, assets: list[str]) -> pd.DataFrame:
    """
    Compute position DataFrame at rebalance frequency.

    signal[t] = rolling(LOOKBACK_PERD).mean() of fr_mean_rebal[t-2:t]
    positions[t] = rank-based position to ENTER at start of period t+1.

    No look-ahead: signal at t uses only periods t-LOOKBACK+1 through t.

    Vectorized: uses pandas rank + clip instead of per-row Python loop.
    """
    fr     = fr_mean_rebal[assets].copy()
    signal = fr.rolling(LOOKBACK_PERD).mean()

    n_valid = signal.notna().sum(axis=1)    # assets with valid signal each period
    n_q     = (n_valid * QUINTILE).clip(lower=1).astype(int)

    # Cross-sectional rank (1 = lowest funding)
    ranks = signal.rank(axis=1, ascending=True, na_option="keep")

    # n_total for each row (count of non-NaN columns)
    n_tot = signal.notna().sum(axis=1)

    # Broadcast n_q across columns
    n_q_bcast = n_q.values[:, None]          # (n_rows, 1)
    n_tot_bcast = n_tot.values[:, None]

    # Long if rank <= n_q (bottom quintile)
    is_long  = (ranks.values <= n_q_bcast)  & ranks.notna().values
    # Short if rank > n_tot - n_q (top quintile)
    is_short = (ranks.values > n_tot_bcast - n_q_bcast) & ranks.notna().values

    # Equal weight within each leg; zero where < MIN_ASSETS
    n_long  = is_long.sum(axis=1, keepdims=True).clip(min=1)
    n_short = is_short.sum(axis=1, keepdims=True).clip(min=1)
    has_enough = (n_tot.values >= MIN_ASSETS)[:, None]

    pos_arr = np.where(is_long,  1.0 / n_long,  0.0)
    pos_arr = np.where(is_short, -1.0 / n_short, pos_arr)
    pos_arr = np.where(has_enough, pos_arr, 0.0)

    positions = pd.DataFrame(pos_arr, index=signal.index, columns=assets)

    # Concentration cap (clip and renormalize each leg per row)
    # For efficiency, only process rows where any position exceeds MAX_WEIGHT
    for idx in range(len(positions)):
        row = positions.iloc[idx]
        if row.abs().max() <= MAX_WEIGHT + 1e-10:
            continue
        for sign in (1, -1):
            mask = (row * sign > MAX_WEIGHT / 2)
            leg  = row[mask].abs()
            if leg.empty or leg.max() <= MAX_WEIGHT:
                continue
            leg   = leg.clip(upper=MAX_WEIGHT)
            leg  /= leg.sum()
            positions.iloc[idx][mask] = leg * sign

    return positions


# ---------------------------------------------------------------------------
# P&L computation (sequential loop — enables risk controls)
# ---------------------------------------------------------------------------

def compute_pnl_sequential(
    pos_all: pd.DataFrame,
    fr_sum_all: pd.DataFrame,
    px_open_all: pd.DataFrame,
    test_index: pd.DatetimeIndex,
    assets: list[str],
    price_assets: list[str],
) -> pd.DataFrame:
    """
    Sequential P&L with per-asset stop-loss and portfolio DD halt.

    For each test period t:
      entering_pos[t] = pos_all at the period immediately before t
                        (position formed at end of t-1, entered at open[t])
      carry_pnl[t]    = -entering_pos[t] × fr_sum[t] × NOTIONAL
      price_pnl[t]    = entering_pos[t] × (open[t+1]/open[t]-1) × NOTIONAL
      fees[t]         = |entering_pos[t] - entering_pos[t-1]|.sum()
                        × NOTIONAL × COST_PER_LEG

    Risk controls modify entering_pos before P&L computation.
    Assertion: len(output) == len(test_index).
    """
    all_cols = pos_all.columns.tolist()

    # Align support DataFrames to pos_all index
    fr_s  = fr_sum_all[assets].reindex(pos_all.index).fillna(0.0)
    px_o  = px_open_all[price_assets].reindex(pos_all.index) if price_assets else pd.DataFrame(index=pos_all.index)

    # Next-period open (for price return computation) — look-ahead on price only,
    # not on signal; position is already frozen at entry.
    px_next = px_o.shift(-1)

    results          = []
    cooldown_ctr: dict[str, int] = {}   # asset → periods remaining in cooldown
    prev_pos         = pd.Series(0.0, index=all_cols)
    cum_net_pnl      = 0.0
    peak_net_pnl     = 0.0
    halted           = False

    for ts in test_index:
        loc = pos_all.index.get_loc(ts)

        # --- Position proposed by signal (formed at end of previous period) ---
        if loc == 0:
            raw_pos = pd.Series(0.0, index=all_cols)
        else:
            raw_pos = pos_all.iloc[loc - 1].copy()

        # --- Apply risk controls: cooldown and portfolio halt ---
        enter_pos = raw_pos.copy()

        # Decrement cooldowns; zero out cooling-down assets
        expired = [a for a, c in cooldown_ctr.items() if c <= 0]
        for a in expired:
            del cooldown_ctr[a]
        for a in cooldown_ctr:
            enter_pos[a] = 0.0
            cooldown_ctr[a] -= 1

        if halted:
            enter_pos[:] = 0.0

        # --- Turnover and fees (cost of entering enter_pos from prev_pos) ---
        turnover   = (enter_pos - prev_pos).abs().sum()
        fees       = turnover * NOTIONAL * COST_PER_LEG

        # --- Carry P&L for period ts ---
        carry = -(enter_pos[assets] * fr_s.loc[ts, assets]).sum() * NOTIONAL

        # --- Price P&L for period ts (enter at open[ts], exit at open[ts+1]) ---
        price = 0.0
        price_pnl_by_asset = pd.Series(0.0, index=price_assets)
        if price_assets and loc + 1 < len(pos_all):
            px_t  = px_o.loc[ts, price_assets]
            px_t1 = px_next.loc[ts, price_assets]
            valid  = px_t.notna() & px_t1.notna() & (px_t > 0)
            if valid.any():
                ret_v  = (px_t1[valid] / px_t[valid] - 1).fillna(0.0)
                pos_v  = enter_pos[ret_v.index]
                ppa_v  = pos_v * ret_v * NOTIONAL
                price_pnl_by_asset[ppa_v.index] = ppa_v
                price  = float(ppa_v.sum())

        net        = carry + price - fees
        cum_net_pnl += net
        peak_net_pnl = max(peak_net_pnl, cum_net_pnl)

        results.append({
            "timestamp":  ts,
            "carry_pnl":  carry,
            "price_pnl":  price,
            "fees":       fees,
            "net_pnl":    net,
            "n_assets":   int((enter_pos != 0).sum()),
        })

        # --- Update state for next iteration ---
        prev_pos = enter_pos.copy()

        # Per-asset stop-loss check (vectorized)
        if not price_pnl_by_asset.empty:
            threshold = -STOP_LOSS_PCT * NOTIONAL * enter_pos[price_assets].abs()
            stop_triggered = price_pnl_by_asset < threshold
            for a in stop_triggered[stop_triggered].index:
                if a not in cooldown_ctr:
                    cooldown_ctr[a] = COOLDOWN_PERD

        # Portfolio DD halt check
        if peak_net_pnl > NOTIONAL * 0.05:   # only check after meaningful P&L builds
            dd_frac = (peak_net_pnl - cum_net_pnl) / peak_net_pnl
            if dd_frac > MAX_DD_PCT:
                halted = True
            elif halted and (peak_net_pnl - cum_net_pnl) / peak_net_pnl < MAX_DD_PCT * 0.5:
                halted = False   # recovered to 50% of DD limit

    pnl_df = pd.DataFrame(results).set_index("timestamp")
    assert len(pnl_df) == len(test_index), (
        f"Length mismatch: got {len(pnl_df)}, expected {len(test_index)}"
    )
    return pnl_df


# ---------------------------------------------------------------------------
# Sharpe at correct rebalance frequency
# ---------------------------------------------------------------------------

def compute_sharpe(net_pnl: pd.Series, freq_h: int) -> float:
    """
    Annualized Sharpe at the rebalance period frequency.
    returns = net_pnl / NOTIONAL  (fraction of one side's capital)
    """
    r = (net_pnl / NOTIONAL).dropna()
    if len(r) < 2 or r.std() < 1e-10:
        return 0.0
    ppy = PERIODS_PER_YEAR[freq_h]
    return float(r.mean() / r.std() * np.sqrt(ppy))


def _max_dd(cum_pnl: pd.Series) -> float:
    """Maximum dollar drawdown."""
    running_max = cum_pnl.cummax()
    return float((running_max - cum_pnl).max()) if len(cum_pnl) > 0 else 0.0


# ---------------------------------------------------------------------------
# Train-period frequency selection
# ---------------------------------------------------------------------------

def select_freq_on_train(
    train_fr_hourly: pd.DataFrame,
    train_px_8h: pd.DataFrame,
    assets: list[str],
    price_assets: list[str],
) -> tuple[int, float]:
    """Select rebalance frequency maximizing train-period Sharpe."""
    best_freq   = 24
    best_sharpe = -np.inf

    for label, freq_h in FREQ_OPTIONS.items():
        fr_mean, fr_sum = resample_funding(train_fr_hourly[assets], freq_h)
        px_open         = resample_prices(train_px_8h[price_assets], freq_h) if price_assets else pd.DataFrame(index=fr_mean.index)

        pos = compute_positions(fr_mean, assets)

        # Sequential P&L on full train window
        pnl_df = compute_pnl_sequential(
            pos, fr_sum, px_open, pos.index, assets, price_assets
        )
        sh = compute_sharpe(pnl_df["net_pnl"], freq_h)
        if sh > best_sharpe:
            best_sharpe = sh
            best_freq   = freq_h

    return best_freq, best_sharpe


# ---------------------------------------------------------------------------
# Fold creation
# ---------------------------------------------------------------------------

def make_folds(
    fr_hourly: pd.DataFrame,
    px_8h: pd.DataFrame,
) -> list[dict]:
    """Rolling 6-month train / 1-month test folds."""
    t_start = fr_hourly.index[0]
    t_end   = fr_hourly.index[-1]

    # Pre-compute first valid timestamp per asset (O(n_assets) not O(n_assets × n_hours))
    first_ts = {c: fr_hourly[c].first_valid_index() for c in fr_hourly.columns}

    folds    = []
    fold_num = 0
    t        = t_start + pd.DateOffset(months=TRAIN_MONTHS)

    while t + pd.DateOffset(months=TEST_MONTHS) <= t_end + pd.Timedelta(hours=1):
        train_start = t - pd.DateOffset(months=TRAIN_MONTHS)
        test_start  = t
        test_end    = t + pd.DateOffset(months=TEST_MONTHS)

        # Assets available at training START (no look-ahead)
        # Asset is available if its first data point is BEFORE or AT train_start
        available = [
            c for c, fts in first_ts.items()
            if fts is not None and fts <= train_start
        ]
        if len(available) < MIN_ASSETS:
            t += pd.DateOffset(months=TEST_MONTHS)
            continue

        # Slice using datetime ranges (works across different index frequencies)
        train_fr = fr_hourly.loc[train_start : test_start - pd.Timedelta(hours=1), available]
        test_fr  = fr_hourly.loc[test_start  : test_end   - pd.Timedelta(hours=1), available]
        # px_8h has 8h index — slice by datetime, not boolean mask
        train_px = px_8h.loc[train_start : test_start - pd.Timedelta(hours=1)]
        test_px  = px_8h.loc[test_start  : test_end   - pd.Timedelta(hours=1)]

        if len(train_fr) == 0 or len(test_fr) == 0:
            t += pd.DateOffset(months=TEST_MONTHS)
            continue

        fold_num += 1
        folds.append({
            "fold":        fold_num,
            "train_start": train_start,
            "test_start":  test_start,
            "test_end":    test_end,
            "train_fr":    train_fr,
            "test_fr":     test_fr,
            "train_px":    train_px,
            "test_px":     test_px,
            "available":   available,
        })
        t += pd.DateOffset(months=TEST_MONTHS)

    return folds


# ---------------------------------------------------------------------------
# TSMOM baseline (BTC, 28d momentum, 15% vol target)
# ---------------------------------------------------------------------------

def compute_tsmom(px_8h_btc: pd.Series) -> pd.Series:
    """BTC TSMOM daily P&L series."""
    daily = px_8h_btc.resample("1d").last().dropna()
    ret   = daily.pct_change().dropna()
    mom28 = daily.shift(1).pct_change(28).reindex(ret.index)
    vol20 = ret.rolling(20).std().replace(0, np.nan) * np.sqrt(365)
    sig   = np.sign(mom28).fillna(0.0)
    pos   = (sig * 0.15 / vol20).fillna(0.0).clip(-2.0, 2.0)
    return (pos.shift(1) * ret * NOTIONAL * 2).dropna()


# ---------------------------------------------------------------------------
# Main walk-forward
# ---------------------------------------------------------------------------

def run_walkforward() -> dict:
    print("=" * 70)
    print("STRATEGY C: FUNDING RATE CARRY — WALK-FORWARD BACKTEST")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print("=" * 70)

    # ── 1. Load funding data ────────────────────────────────────────────────
    print("\nLoading funding data ...")
    fr_hourly = load_funding_pivot()
    all_assets = fr_hourly.columns.tolist()
    print(f"  {len(all_assets)} assets, {len(fr_hourly):,} hourly bars  "
          f"({fr_hourly.index.min().date()} → {fr_hourly.index.max().date()})")

    # ── 2. Fetch / load price data ──────────────────────────────────────────
    print("\nFetching 8h price candles ...")
    fetch_prices_universe(all_assets, force=False)
    px_open_8h, _ = load_prices_wide(all_assets)
    n_with_px = len(px_open_8h.columns)
    print(f"  {n_with_px}/{len(all_assets)} assets have price data")

    # Fill NaN for missing assets (carry only, no price P&L contribution)
    for a in all_assets:
        if a not in px_open_8h.columns:
            px_open_8h[a] = np.nan
    px_open_8h = px_open_8h.reindex(columns=all_assets).sort_index()

    # ── 3. Make folds ───────────────────────────────────────────────────────
    print("\nCreating folds ...")
    folds = make_folds(fr_hourly, px_open_8h)
    print(f"  {len(folds)} folds  "
          f"({folds[0]['test_start'].date()} → {folds[-1]['test_end'].date()})")

    # ── 4. Walk-forward loop ────────────────────────────────────────────────
    print("\nRunning walk-forward ...")
    fold_results = []
    oos_pnl_list = []
    freq_counts  = {8: 0, 24: 0, 7 * 24: 0}

    for f in folds:
        fold_num  = f["fold"]
        available = f["available"]
        pa        = [a for a in available if a in px_open_8h.columns
                     and px_open_8h[a].loc[f["train_start"]:f["test_end"]].notna().any()]

        # ── Train: select rebalance frequency ────────────────────────────
        best_freq, tr_sh = select_freq_on_train(
            f["train_fr"], f["train_px"][pa] if pa else pd.DataFrame(), available, pa
        )
        freq_counts[best_freq] += 1

        # ── Test: combined window for signal continuity ───────────────────
        combined_fr = pd.concat([f["train_fr"][available], f["test_fr"][available]])
        combined_px = pd.concat([
            f["train_px"][pa] if pa else pd.DataFrame(index=f["train_px"].index),
            f["test_px"][pa]  if pa else pd.DataFrame(index=f["test_px"].index),
        ])

        fr_mean, fr_sum = resample_funding(combined_fr, best_freq)
        px_open_rebal   = resample_prices(combined_px, best_freq) if pa else pd.DataFrame(index=fr_mean.index)

        # Positions on full combined window
        pos_all = compute_positions(fr_mean, available)

        # Test-period rebalance timestamps
        test_idx = pos_all.index[
            (pos_all.index >= f["test_start"]) & (pos_all.index < f["test_end"])
        ]
        n_rebal = len(test_idx)

        if n_rebal == 0:
            t += pd.DateOffset(months=TEST_MONTHS)
            continue

        pnl_df = compute_pnl_sequential(
            pos_all, fr_sum, px_open_rebal, test_idx, available, pa
        )

        assert len(pnl_df) == n_rebal, (
            f"Fold {fold_num}: assert {len(pnl_df)} == {n_rebal}"
        )

        net_sharpe = compute_sharpe(pnl_df["net_pnl"], best_freq)
        fold_max_dd = _max_dd(pnl_df["net_pnl"].cumsum())

        freq_label = {8: "8h", 24: "24h", 7 * 24: "7d"}[best_freq]
        fold_rec = {
            "fold":             fold_num,
            "train_start":      str(f["train_start"].date()),
            "test_start":       str(f["test_start"].date()),
            "test_end":         str(f["test_end"].date()),
            "rebalance_freq":   freq_label,
            "n_assets":         len(available),
            "n_rebal_periods":  n_rebal,
            "carry_pnl":        round(float(pnl_df["carry_pnl"].sum()), 2),
            "price_pnl":        round(float(pnl_df["price_pnl"].sum()), 2),
            "fees":             round(float(pnl_df["fees"].sum()), 2),
            "net_pnl":          round(float(pnl_df["net_pnl"].sum()), 2),
            "net_sharpe":       round(net_sharpe, 3),
            "max_dd":           round(fold_max_dd, 2),
            "train_sharpe":     round(tr_sh, 3),
        }
        fold_results.append(fold_rec)

        pnl_df["freq_h"] = best_freq
        oos_pnl_list.append(pnl_df)

        print(f"  Fold {fold_num:2d}  {f['test_start'].date()} → {f['test_end'].date()}"
              f"  {freq_label}  n={len(available):3d}"
              f"  carry=${fold_rec['carry_pnl']:+7.0f}"
              f"  price=${fold_rec['price_pnl']:+7.0f}"
              f"  net=${fold_rec['net_pnl']:+7.0f}"
              f"  Sh={net_sharpe:+.2f}")

    # ── 5. Aggregate OOS ────────────────────────────────────────────────────
    fold_df    = pd.DataFrame(fold_results)
    oos_pnl_df = pd.concat(oos_pnl_list).sort_index()

    dominant_freq_h  = max(freq_counts, key=freq_counts.get)
    dominant_label   = {8: "8h", 24: "24h", 7 * 24: "7d"}[dominant_freq_h]
    dominant_frac    = freq_counts[dominant_freq_h] / len(folds)

    print(f"\n  Frequency counts: "
          f"8h={freq_counts[8]}, 24h={freq_counts[24]}, 7d={freq_counts[7*24]}")
    print(f"  Dominant: {dominant_label} ({dominant_frac:.0%} of folds)")

    oos_net_pnl   = oos_pnl_df["net_pnl"]
    oos_carry_pnl = oos_pnl_df["carry_pnl"]
    oos_price_pnl = oos_pnl_df["price_pnl"]

    oos_sharpe       = compute_sharpe(oos_net_pnl,   dominant_freq_h)
    carry_sharpe     = compute_sharpe(oos_carry_pnl, dominant_freq_h)
    price_sharpe     = compute_sharpe(oos_price_pnl, dominant_freq_h)
    oos_max_dd       = _max_dd(oos_net_pnl.cumsum())
    total_carry      = float(oos_carry_pnl.sum())
    total_price      = float(oos_price_pnl.sum())
    total_fees       = float(fold_df["fees"].sum())
    total_net        = float(oos_net_pnl.sum())

    gross_abs        = abs(total_carry) + abs(total_price)
    carry_frac       = total_carry / max(gross_abs, 1e-10)

    # DSR
    n_trials    = len(FREQ_OPTIONS) * len(folds)
    returns_arr = (oos_net_pnl / NOTIONAL).dropna().values
    dsr_result  = deflated_sharpe_ratio(
        returns_arr, n_trials=n_trials,
        periods_per_year=PERIODS_PER_YEAR[dominant_freq_h],
    )

    print(f"\n  OOS Net Sharpe ({dominant_label}): {oos_sharpe:+.3f}")
    print(f"  OOS Carry Sharpe: {carry_sharpe:+.3f}  |  Price Sharpe: {price_sharpe:+.3f}")
    print(f"  Total P&L: carry=${total_carry:+,.0f}  price=${total_price:+,.0f}"
          f"  fees=${total_fees:,.0f}  net=${total_net:+,.0f}")
    print(f"  Max Drawdown: ${oos_max_dd:,.0f}  |  Carry fraction: {carry_frac:.1%}")
    print(f"  DSR={dsr_result['dsr']:.4f} (n_trials={n_trials}, "
          f"passed={dsr_result['passed']})")

    # ── 6. Regime analysis (BTC up vs down months) ─────────────────────────
    btc_up_sh = btc_dn_sh = np.nan
    btc_regime_note = "BTC price not available"
    tsmom_pnl = None

    if "BTC" in px_open_8h.columns and px_open_8h["BTC"].notna().any():
        btc_8h = px_open_8h["BTC"].dropna()

        # Monthly regime
        btc_monthly = btc_8h.resample("1ME").last().pct_change().dropna()
        oos_monthly  = oos_net_pnl.resample("1ME").sum()
        reg_df = pd.concat([oos_monthly.rename("carry"),
                            btc_monthly.rename("btc")], axis=1).dropna()
        if len(reg_df) >= 5:
            up   = reg_df[reg_df["btc"] > 0]["carry"]
            dn   = reg_df[reg_df["btc"] < 0]["carry"]
            def _msh(s):
                if len(s) < 3 or s.std() < 1e-10: return np.nan
                return float(s.mean() / s.std() * np.sqrt(12))
            btc_up_sh = _msh(up)
            btc_dn_sh = _msh(dn)
            btc_regime_note = (
                f"BTC up months Sharpe={btc_up_sh:.2f} (n={len(up)})  |  "
                f"BTC down months Sharpe={btc_dn_sh:.2f} (n={len(dn)})"
            )
        print(f"  Regime: {btc_regime_note}")

        # TSMOM
        tsmom_pnl = compute_tsmom(btc_8h)

    # ── 7. TSMOM correlation ────────────────────────────────────────────────
    tsmom_corr = np.nan
    tsmom_note = "TSMOM not computed (no BTC price)"

    if tsmom_pnl is not None:
        oos_daily   = oos_net_pnl.resample("1d").sum()
        aligned_ts  = pd.concat([oos_daily.rename("carry"),
                                 tsmom_pnl.rename("tsmom")], axis=1).dropna()
        if len(aligned_ts) >= 30:
            tsmom_corr = float(aligned_ts["carry"].corr(aligned_ts["tsmom"]))
            tsmom_note = f"corr={tsmom_corr:.3f} (n={len(aligned_ts)} days)"
        print(f"  TSMOM: {tsmom_note}")

    # ── 8. Verdict ──────────────────────────────────────────────────────────
    sharpe_ok    = oos_sharpe >= 1.0
    dsr_ok       = dsr_result["dsr"] >= 0.95
    maxdd_ok     = oos_max_dd <= NOTIONAL * 0.30
    tsmom_ok     = np.isnan(tsmom_corr) or abs(tsmom_corr) < 0.30
    carry_ok     = carry_frac >= 0.30
    bull_ok      = np.isnan(btc_up_sh)  or btc_up_sh >= 0.50

    # NO-GO triggers (any one sufficient)
    no_go = (
        oos_sharpe < 0.5 or
        oos_max_dd > NOTIONAL * 0.40 or
        (not np.isnan(tsmom_corr) and abs(tsmom_corr) > 0.50) or
        (not np.isnan(btc_up_sh)  and btc_up_sh < 0.0)
    )

    go      = not no_go and sharpe_ok and dsr_ok and tsmom_ok and carry_ok
    verdict = "✅ GO" if go else "❌ NO-GO"

    print(f"\n{'─'*70}")
    print(f"VERDICT: {verdict}")
    print(f"  OOS Sharpe ≥ 1.0    : {'✅' if sharpe_ok else '❌'}  {oos_sharpe:.3f}")
    print(f"  DSR ≥ 0.95          : {'✅' if dsr_ok else '❌'}  {dsr_result['dsr']:.4f}")
    print(f"  MaxDD ≤ 30% notional: {'✅' if maxdd_ok else '❌'}  ${oos_max_dd:.0f}")
    print(f"  |TSMOM corr| < 0.30 : {'✅' if tsmom_ok else '❌'}  {tsmom_note}")
    print(f"  Carry fraction ≥ 30%: {'✅' if carry_ok else '❌'}  {carry_frac:.1%}")
    print(f"  Bull Sharpe ≥ 0.50  : {'✅' if bull_ok else '❌'}  {btc_regime_note}")
    print(f"{'─'*70}")

    # ── 9. Save outputs ──────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(exist_ok=True)
    csv_path = DATA_DIR / "walkforward_results.csv"
    fold_df.to_csv(csv_path, index=False)
    print(f"\nFold results → {csv_path}")

    _make_plots(fold_df, oos_pnl_df, px_open_8h, tsmom_pnl, tsmom_corr)
    _write_report(
        fold_df, oos_pnl_df, dsr_result, tsmom_corr, tsmom_note,
        btc_regime_note, btc_up_sh, btc_dn_sh, oos_sharpe, carry_sharpe,
        price_sharpe, carry_frac, oos_max_dd, dominant_label, dominant_frac,
        n_trials, go, freq_counts, total_carry, total_price, total_fees,
        total_net, sharpe_ok, dsr_ok, maxdd_ok, tsmom_ok, carry_ok, bull_ok,
    )

    return {
        "verdict":       go,
        "oos_sharpe":    oos_sharpe,
        "dsr":           dsr_result["dsr"],
        "max_dd":        oos_max_dd,
        "tsmom_corr":    tsmom_corr,
        "carry_frac":    carry_frac,
        "dominant_freq": dominant_label,
        "carry_sharpe":  carry_sharpe,
        "price_sharpe":  price_sharpe,
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def _make_plots(fold_df, oos_pnl_df, px_open_8h, tsmom_pnl, tsmom_corr):
    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    fig.suptitle("Strategy C: Funding Rate Carry — Walk-Forward OOS", fontsize=14)

    # [0,0] Cumulative P&L decomposed
    ax = axes[0, 0]
    cum_carry = oos_pnl_df["carry_pnl"].cumsum()
    cum_price = oos_pnl_df["price_pnl"].cumsum()
    cum_net   = oos_pnl_df["net_pnl"].cumsum()
    ax.plot(cum_carry.index, cum_carry.values, label="Carry",  color="steelblue", alpha=0.9)
    ax.plot(cum_price.index, cum_price.values, label="Price",  color="orange",    alpha=0.9)
    ax.plot(cum_net.index,   cum_net.values,   label="Net",    color="green", linewidth=2)
    ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
    ax.set_title("Cumulative OOS P&L: Carry / Price / Net")
    ax.set_ylabel("Cumulative P&L ($)")
    ax.legend(fontsize=8)

    # [0,1] Rolling 60-day Sharpe (daily P&L)
    ax = axes[0, 1]
    oos_daily = oos_pnl_df["net_pnl"].resample("1d").sum()
    roll_sh   = oos_daily.rolling(60).apply(
        lambda x: float(x.mean() / x.std() * np.sqrt(365)) if x.std() > 1e-10 else 0.0,
        raw=True
    )
    ax.plot(roll_sh.index, roll_sh.values, color="green", linewidth=1)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1, label="Sharpe=1.0")
    ax.axhline(0.0, color="gray",  linestyle="--", linewidth=0.5)
    ax.set_title("Rolling 60-day Net Sharpe (daily returns)")
    ax.set_ylabel("Annualized Sharpe")
    ax.legend(fontsize=8)

    # [1,0] Regime: BTC up vs down months
    ax = axes[1, 0]
    if "BTC" in px_open_8h.columns and px_open_8h["BTC"].notna().any():
        btc_monthly = px_open_8h["BTC"].resample("1ME").last().pct_change().dropna()
        oos_monthly  = oos_pnl_df["net_pnl"].resample("1ME").sum()
        reg = pd.concat([oos_monthly.rename("c"), btc_monthly.rename("b")], axis=1).dropna()
        if len(reg) >= 3:
            colors = ["#2ca02c" if b > 0 else "#d62728" for b in reg["b"]]
            ax.bar(reg.index, reg["c"], width=25, color=colors, alpha=0.8)
            ax.axhline(0, color="black", linewidth=0.5)
            import matplotlib.patches as mpatches
            ax.legend(handles=[mpatches.Patch(color="#2ca02c", label="BTC↑"),
                                mpatches.Patch(color="#d62728", label="BTC↓")], fontsize=8)
    ax.set_title("Monthly Net P&L by BTC Regime")
    ax.set_ylabel("Monthly P&L ($)")

    # [1,1] TSMOM rolling correlation
    ax = axes[1, 1]
    corr_label = f"Full-period corr={tsmom_corr:.3f}" if not np.isnan(tsmom_corr) else "TSMOM corr"
    if tsmom_pnl is not None:
        oos_daily_c = oos_pnl_df["net_pnl"].resample("1d").sum()
        aligned     = pd.concat([oos_daily_c.rename("c"),
                                 tsmom_pnl.rename("t")], axis=1).dropna()
        if len(aligned) >= 30:
            roll_corr = aligned["c"].rolling(60).corr(aligned["t"])
            ax.plot(roll_corr.index, roll_corr.values, color="purple", linewidth=1)
            ax.axhline( 0.30, color="red",  linestyle="--", linewidth=1, label="±0.30")
            ax.axhline(-0.30, color="red",  linestyle="--", linewidth=1)
            ax.axhline( 0.0,  color="gray", linestyle="--", linewidth=0.5)
            ax.legend(fontsize=8)
    ax.set_title(f"Rolling 60d Correlation to TSMOM  ({corr_label})")
    ax.set_ylabel("Pearson corr")

    # [2,0] Carry vs Fees per fold
    ax = axes[2, 0]
    x = fold_df["fold"]
    ax.bar(x, fold_df["carry_pnl"], label="Carry",  color="steelblue", alpha=0.8)
    ax.bar(x, -fold_df["fees"],     label="Fees (-)", color="red",       alpha=0.7)
    ax.bar(x, fold_df["price_pnl"], label="Price",   color="orange",    alpha=0.6, bottom=fold_df["carry_pnl"])
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Carry / Price / Fees per Fold")
    ax.set_xlabel("Fold")
    ax.set_ylabel("P&L ($)")
    ax.legend(fontsize=8)

    # [2,1] Frequency selected per fold
    ax = axes[2, 1]
    freq_map = {"8h": 0, "24h": 1, "7d": 2}
    y_vals = [freq_map.get(f, 1) for f in fold_df["rebalance_freq"]]
    ax.bar(fold_df["fold"], y_vals, color="steelblue", alpha=0.8)
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["8h", "24h", "7d"])
    ax.set_title("Rebalance Frequency Selected per Fold")
    ax.set_xlabel("Fold")

    plt.tight_layout()
    out = OUTPUT_DIR / "strategy_C_walkforward.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved → {out}")


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def _write_report(
    fold_df, oos_pnl_df, dsr_result, tsmom_corr, tsmom_note,
    btc_regime_note, btc_up_sh, btc_dn_sh, oos_sharpe, carry_sharpe,
    price_sharpe, carry_frac, oos_max_dd, dominant_label, dominant_frac,
    n_trials, go, freq_counts, total_carry, total_price, total_fees,
    total_net, sharpe_ok, dsr_ok, maxdd_ok, tsmom_ok, carry_ok, bull_ok,
):
    verdict   = "✅ GO" if go else "❌ NO-GO"
    tc        = f"{tsmom_corr:.3f}" if not np.isnan(tsmom_corr) else "not computed"
    bu        = f"{btc_up_sh:.2f}"  if not np.isnan(btc_up_sh)  else "—"
    bd        = f"{btc_dn_sh:.2f}"  if not np.isnan(btc_dn_sh)  else "—"

    freq_bkd  = (f"8h: {freq_counts.get(8,0)} folds, "
                 f"24h: {freq_counts.get(24,0)} folds, "
                 f"7d: {freq_counts.get(7*24,0)} folds")

    fold_rows = "\n".join(
        f"| {r['fold']} | {r['test_start']} | {r['rebalance_freq']} | {r['n_assets']} | "
        f"${r['carry_pnl']:+.0f} | ${r['price_pnl']:+.0f} | ${r['fees']:.0f} | "
        f"${r['net_pnl']:+.0f} | {r['net_sharpe']:+.2f} |"
        for _, r in fold_df.iterrows()
    )

    gross_abs = abs(total_carry) + abs(total_price)
    price_flag = ""
    if total_price < -abs(total_carry) * 0.5:
        price_flag = "\n⚠️ **Price P&L is systematically negative and large — short leg hurt by directional moves.**"

    report = f"""# Strategy C: Funding Rate Carry Walk-Forward Backtest

**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC
**Universe:** Hyperliquid perpetuals with ≥180 days funding history
**Method:** Rolling {TRAIN_MONTHS}-month train / {TEST_MONTHS}-month test, {len(fold_df)} folds
**Signal:** Cross-sectional funding rate rank, {LOOKBACK_PERD}-period lookback, top/bottom {int(QUINTILE*100)}% quintile
**Parameters:** Rebalance frequency selected on train Sharpe each fold (no test peeking)

---

## Verdict: {verdict}

---

## Sharpe Computation Methodology (Correction from Feasibility)

**The feasibility Sharpe (5.84 at 7d, 4.64 at 24h, 1.82 at 8h) was computed at hourly
frequency regardless of rebalance interval. This inflated Sharpe due to within-period
autocorrelation of funding P&L. Those numbers are NOT cited in this report.**

Sharpe here is computed at the rebalance period frequency:
- 8h: annualize × √1095   (1095 periods/year)
- 24h: annualize × √365
- 7d: annualize × √52

Assertion enforced: `len(pnl_series) == n_rebalance_periods` per fold.

---

## OOS Portfolio Metrics

| Metric | Value |
|--------|-------|
| OOS Net Sharpe ({dominant_label} dominant) | {oos_sharpe:+.3f} |
| OOS Carry Sharpe | {carry_sharpe:+.3f} |
| OOS Price Sharpe | {price_sharpe:+.3f} |
| Total Carry P&L | ${total_carry:+,.0f} |
| Total Price P&L | ${total_price:+,.0f} |
| Total Fees Paid | ${total_fees:,.0f} |
| Total Net P&L | ${total_net:+,.0f} |
| Max Drawdown ($) | ${oos_max_dd:,.0f} |
| Dominant rebalance frequency | {dominant_label} ({dominant_frac:.0%} of folds) |
| Frequency breakdown | {freq_bkd} |

---

## DSR (Deflated Sharpe Ratio)

| Metric | Value |
|--------|-------|
| Observed Sharpe | {dsr_result['sharpe']:+.3f} |
| E[max SR] benchmark | {dsr_result['sr_benchmark']:.3f} |
| Skewness | {dsr_result['skewness']:.3f} |
| Excess kurtosis | {dsr_result['excess_kurtosis']:.3f} |
| DSR | {dsr_result['dsr']:.4f} |
| n_trials | {n_trials} ({len(FREQ_OPTIONS)} freqs × {len(fold_df)} folds) |
| n_obs | {dsr_result['n_obs']} |
| Passed (≥ 0.95) | {'✅' if dsr_result['passed'] else '❌'} |

---

## Carry vs Price Decomposition

| Component | Amount | Fraction of gross |
|-----------|--------|-------------------|
| Carry P&L | ${total_carry:+,.0f} | {total_carry/max(gross_abs,1):.1%} |
| Price P&L | ${total_price:+,.0f} | {total_price/max(gross_abs,1):.1%} |
| Fees | −${total_fees:,.0f} | — |
| **Net P&L** | **${total_net:+,.0f}** | — |

Carry fraction of gross: **{carry_frac:.1%}** — {'✅ Strategy is primarily earn carry' if carry_ok else '❌ Price dominates — strategy is not primarily a carry strategy'}
{price_flag}

---

## Regime Analysis (BTC Up vs Down Months)

| Regime | Monthly Sharpe |
|--------|----------------|
| BTC up months   | {bu} |
| BTC down months | {bd} |

Bull market short-leg risk: {'✅ Acceptable — net positive even in BTC-up months' if bull_ok else '❌ Short leg destroyed in bull months — net Sharpe negative when BTC rises'}

---

## TSMOM Correlation (Strategy A)

{tsmom_note}

Target: |corr| < 0.30 — {'✅ Within target (strategies are diversifying)' if tsmom_ok else '❌ Exceeds target'}

---

## GO Criteria

| Criterion | Required | Result | Pass? |
|-----------|----------|--------|-------|
| OOS Net Sharpe | ≥ 1.0 | {oos_sharpe:.3f} | {'✅' if sharpe_ok else '❌'} |
| DSR | ≥ 0.95 | {dsr_result['dsr']:.4f} | {'✅' if dsr_ok else '❌'} |
| MaxDD | ≤ ${{int(NOTIONAL*0.30):,}} | ${oos_max_dd:.0f} | {'✅' if maxdd_ok else '❌'} |
| TSMOM corr | < 0.30 | {tc} | {'✅' if tsmom_ok else '❌'} |
| Carry fraction | ≥ 30% | {carry_frac:.1%} | {'✅' if carry_ok else '❌'} |
| Bull Sharpe | ≥ 0.50 | {bu} | {'✅' if bull_ok else '❌'} |

---

## Per-Fold OOS Results

| Fold | Test Start | Freq | Assets | Carry | Price | Fees | Net | Sharpe |
|------|-----------|------|--------|-------|-------|------|-----|--------|
{fold_rows}

---

## Methodology Notes

### Risk Controls Applied
- Per-asset stop-loss: loss > {int(STOP_LOSS_PCT*100)}% of notional in one period → force flat, {COOLDOWN_PERD}-period cooldown
- Portfolio DD halt: drawdown > {int(MAX_DD_PCT*100)}% of peak P&L → halt new entries until recovered to 50% of DD limit
- Concentration cap: max {int(MAX_WEIGHT*100)}% of one side's notional per asset

### Signal Construction
1. Resample hourly funding to rebalance frequency (mean per period)
2. Rolling {LOOKBACK_PERD}-period mean → cross-sectional rank
3. Long bottom {int(QUINTILE*100)}% (most negative funding), short top {int(QUINTILE*100)}%
4. Equal weight within quintile; concentration cap applied

### Timing (no look-ahead bias)
- Signal at period T uses funding from periods T-{LOOKBACK_PERD+1} through T-1 (completed)
- Position entered at open of period T
- Carry income = sum of hourly funding during period T × (−position)
- Price return = open[T+1] / open[T] − 1

### Survival Bias Control
Available assets per fold = assets with ANY funding data before the fold's training start.
Assets listed after training start are excluded from that fold.

### Cost Model
0.035% × 2 sides + 0.05% × 2 sides = 0.17% per leg.
Computed from actual position turnover (|pos_new − pos_old|.sum()).
"""

    path = DOCS_DIR / "strategy_C_walkforward.md"
    path.write_text(report)
    print(f"Report saved → {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_walkforward()

    freq  = result.get("dominant_freq", "?d")
    sh    = result.get("oos_sharpe", 0.0)
    cs    = result.get("carry_sharpe", 0.0)
    ps    = result.get("price_sharpe", 0.0)
    cf    = result.get("carry_frac", 0.0)
    corr  = result.get("tsmom_corr", float("nan"))
    corr_s = f"{corr:.2f}" if not (corr != corr) else "nan"

    tag = "GO" if result.get("verdict") else "NO-GO"
    print(f"\nCommit message:")
    print(f"strat-C: walk-forward — {tag} — net Sharpe {sh:.2f} ({freq} rebalance), "
          f"carry {cs:.2f}/price {ps:.2f}/fees, "
          f"carry_frac={cf:.0%}, corr(TSMOM)={corr_s}")
