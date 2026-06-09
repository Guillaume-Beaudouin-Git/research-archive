"""
breakoutprop_fit.py — Re-fit Strategy A to BreakoutProp Classic rules.

Strategy A spec (live, frozen Propr 2026-05-30):
  - 3-asset core: BTC, ETH, SOL
  - Signal: signal(t) = tanh(cumret_28d(t-1) / (vol_28d(t-1) × √28)).clip(lower=0)
  - Weekly rebalance Monday 00:05 UTC (positions held flat from Mon to next Mon)
  - Daily vol-target = VOL_TARGET_LIVE (0.18)
  - Cost RT = 0.17% (per CLAUDE.md L9)

Builds the OOS daily equity curve, then tests against BreakoutProp Classic rules
(documented inline — HUMAN_VERIFY required before deploy).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ["BTC", "ETH", "SOL"]
DAILY_DATA = Path("<HOME>/Desktop/Algo_claude/data/panels/m5_indices/binance")
COST_RT = 0.0017  # 0.17% round-trip per CLAUDE.md L9


# ── BreakoutProp Classic rules (HUMAN_VERIFY before deploy) ────────────────
# Best-known specs from public docs (mid-2025, to be confirmed):
BREAKOUTPROP_RULES = {
    "account_size_usd": 25000.0,        # we test on $25K (entry-level)
    "phase1_target_pct": 0.10,          # +10% to pass P1
    "phase2_target_pct": 0.05,          # +5% to pass P2
    "daily_dd_pct": 0.04,                # 4% daily DD (HUMAN_VERIFY)
    "total_dd_pct": 0.06,                # 6% total DD (HUMAN_VERIFY)
    "total_dd_mode": "static",          # static or trailing (HUMAN_VERIFY)
    "min_trading_days": 3,               # 3 days (typical crypto-prop, HUMAN_VERIFY)
    "time_limit_days": None,             # most plans no time limit (HUMAN_VERIFY)
}


def load_daily_close(asset: str) -> pd.Series:
    """Load daily close (last close of day in UTC) from M1 Binance data."""
    df = pd.read_csv(DAILY_DATA / f"{asset}USD_M1.csv",
                      parse_dates=["timestamp_utc"],
                      usecols=["timestamp_utc", "close"])
    df = df.set_index("timestamp_utc").sort_index()
    daily = df["close"].resample("D").last().dropna()
    return daily.rename(asset)


def build_prices_df() -> pd.DataFrame:
    """Build daily close DataFrame for BTC/ETH/SOL."""
    cols = []
    for a in ASSETS:
        s = load_daily_close(a)
        cols.append(s)
    df = pd.concat(cols, axis=1).dropna()
    return df


def compute_signal_v3(prices: pd.DataFrame, lookback: int = 28) -> pd.DataFrame:
    """
    C1 continuous signal long-only:
      cum_ret(t) = sum(log_ret[t-lookback : t-1])
      vol(t)     = std(log_ret[t-lookback : t-1]) × √365  (annualized)
      t_stat(t)  = cum_ret(t) / (vol(t)/√365 × √lookback + ε)
                = cum_ret(t) / (vol_daily(t) × √lookback)
      signal(t)  = tanh(t_stat(t)).clip(lower=0)
    Per signal.py the formula uses vol_daily × √lookback as denominator.
    """
    log_ret = np.log(prices / prices.shift(1))
    cum_ret = log_ret.rolling(lookback).sum().shift(1)
    vol_L = log_ret.rolling(lookback).std().shift(1) * np.sqrt(lookback)
    t_stat = cum_ret / (vol_L + 1e-8)
    sig = np.tanh(t_stat).clip(lower=0.0)
    sig[cum_ret.isna()] = np.nan
    return sig


def apply_weekly_rebalance(daily_sig: pd.DataFrame, weekday: int = 0) -> pd.DataFrame:
    """Hold from rebalance day to next; pandas weekday 0=Mon."""
    is_reb = pd.Series(daily_sig.index.dayofweek == weekday,
                       index=daily_sig.index, dtype=bool)
    pos = daily_sig.where(is_reb)
    return pos.ffill()


def vol_target_sizing(prices: pd.DataFrame, raw_pos: pd.DataFrame,
                       vol_target: float, vol_lookback: int = 20,
                       scalar_min: float = 0.1, scalar_max: float = 2.0) -> pd.DataFrame:
    """
    Scale positions to target portfolio annualized vol.
    Vol scalar = vol_target / portfolio_realized_vol_recent.
    Applied per-position-day, capped [scalar_min, scalar_max].
    """
    daily_ret = np.log(prices / prices.shift(1))
    # Portfolio vol estimate using current positions × daily ret
    port_ret = (raw_pos.shift(1) * daily_ret).sum(axis=1)
    port_vol = port_ret.rolling(vol_lookback).std() * np.sqrt(365)
    scalar = (vol_target / (port_vol + 1e-8)).clip(scalar_min, scalar_max)
    return raw_pos.mul(scalar, axis=0)


def backtest_strategy_A(prices: pd.DataFrame, vol_target: float = 0.18,
                         cost_rt: float = COST_RT) -> pd.DataFrame:
    """Run full backtest. Returns DataFrame with daily R, equity, DD."""
    sig = compute_signal_v3(prices, lookback=28)
    raw_pos = apply_weekly_rebalance(sig, weekday=0)  # Monday
    pos = vol_target_sizing(prices, raw_pos, vol_target=vol_target)
    pos = pos.fillna(0.0)
    daily_ret = np.log(prices / prices.shift(1))

    # Gross daily return: position[t-1] × ret[t]
    daily_pnl_gross = (pos.shift(1) * daily_ret).sum(axis=1).fillna(0.0)
    # Costs: pay on absolute position change. Only on rebalance days actually.
    pos_change = pos.diff().abs().sum(axis=1).fillna(0.0)
    costs = pos_change * cost_rt
    daily_pnl_net = daily_pnl_gross - costs

    eq = (1 + daily_pnl_net).cumprod()
    dd = eq / eq.cummax() - 1

    out = pd.DataFrame({
        "log_ret_gross": daily_pnl_gross,
        "cost": costs,
        "log_ret_net": daily_pnl_net,
        "equity": eq,
        "drawdown": dd,
        "btc_pos": pos["BTC"],
        "eth_pos": pos["ETH"],
        "sol_pos": pos["SOL"],
        "total_pos": pos.sum(axis=1),
    })
    return out


def dd_distribution(equity_df: pd.DataFrame):
    """Compute distribution of daily DD vs prior close (= daily P&L)."""
    daily_ret = equity_df["log_ret_net"].fillna(0.0)  # log returns
    daily_ret_pct = (np.exp(daily_ret) - 1) * 100  # in %
    max_dd_total = equity_df["drawdown"].min() * 100
    worst_day = daily_ret_pct.min()
    p99_loss = daily_ret_pct.quantile(0.01)
    p95_loss = daily_ret_pct.quantile(0.05)
    p90_loss = daily_ret_pct.quantile(0.10)
    return {
        "max_dd_total_pct": max_dd_total,
        "worst_day_pct": worst_day,
        "p99_loss_pct": p99_loss,
        "p95_loss_pct": p95_loss,
        "p90_loss_pct": p90_loss,
        "daily_ret_std_pct": daily_ret_pct.std(),
        "n_days": len(daily_ret_pct),
        "n_winning_days": (daily_ret_pct > 0).sum(),
        "win_rate_pct": (daily_ret_pct > 0).mean() * 100,
        "ann_ret_pct": daily_ret.mean() * 365 * 100,
        "ann_vol_pct": daily_ret.std() * np.sqrt(365) * 100,
        "sharpe_ann": (daily_ret.mean() / daily_ret.std() * np.sqrt(365))
                       if daily_ret.std() > 0 else 0,
    }


def count_daily_dd_breaches(equity_df: pd.DataFrame, threshold_pct: float):
    """How often does daily DD (from prior close) exceed threshold?"""
    daily_ret = equity_df["log_ret_net"].fillna(0.0)
    daily_ret_pct = (np.exp(daily_ret) - 1) * 100
    breaches = (daily_ret_pct < -threshold_pct).sum()
    return breaches, breaches / len(daily_ret_pct) * 100


def simulate_challenge_2phase(eq_returns: pd.Series, rules: dict,
                                n_paths: int = 5000,
                                block_size_days: int = 14,
                                max_attempt_days: int = 365 * 2,
                                seed: int = 42):
    """
    Block-bootstrap challenge simulation.
    eq_returns = daily log net returns of A.
    """
    rng = np.random.default_rng(seed)
    r = eq_returns.values
    n = len(r)
    # Random starting block; concat blocks to build a path of `max_attempt_days`
    p1_tgt = rules["phase1_target_pct"]
    p2_tgt = rules["phase2_target_pct"]
    daily_dd = rules["daily_dd_pct"]
    total_dd = rules["total_dd_pct"]
    static_mode = (rules.get("total_dd_mode", "static") == "static")
    min_days = rules.get("min_trading_days", 3)

    n_funded = n_phase1_pass = n_bust_daily = n_bust_total = n_timeout = 0
    p1_resolutions = []
    p2_resolutions = []
    for _ in range(n_paths):
        # Build a long path of returns via block-bootstrap
        path_len = max_attempt_days
        n_blocks = (path_len + block_size_days - 1) // block_size_days
        starts = rng.integers(0, max(1, n - block_size_days), size=n_blocks)
        path_rets = np.concatenate([r[s:s + block_size_days] for s in starts])[:path_len]

        # Simulate P1
        eq = 1.0
        hwm = 1.0
        day_start_eq = 1.0
        days_traded = 0
        p1_passed = False
        p1_failed = False
        bust_type = None
        for t in range(path_len):
            day_start_eq = eq  # for daily-DD check
            eq = eq * np.exp(path_rets[t])
            days_traded += 1
            hwm = max(hwm, eq)
            # Daily DD check
            day_return_pct = (eq - day_start_eq) / day_start_eq
            if day_return_pct < -daily_dd:
                bust_type = "daily"
                p1_failed = True
                p1_resolutions.append(("BUST_DAILY", t + 1))
                break
            # Total DD check
            floor = (1 - total_dd) if static_mode else hwm * (1 - total_dd)
            if eq < floor:
                bust_type = "total"
                p1_failed = True
                p1_resolutions.append(("BUST_TOTAL", t + 1))
                break
            # Target
            if eq >= (1 + p1_tgt) and days_traded >= min_days:
                p1_passed = True
                p1_resolutions.append(("PASS_P1", t + 1))
                break
        if not p1_passed and not p1_failed:
            p1_resolutions.append(("TIMEOUT_P1", path_len))
            n_timeout += 1
            continue
        if p1_failed:
            if bust_type == "daily":
                n_bust_daily += 1
            else:
                n_bust_total += 1
            continue

        n_phase1_pass += 1
        # Phase 2 — continue from p1_resolution
        p1_ttp = p1_resolutions[-1][1]
        # Reset HWM and equity for P2 starting at 1.0
        eq2 = 1.0
        hwm2 = 1.0
        days_traded2 = 0
        # Use the REMAINING bootstrapped returns (path_rets[p1_ttp:])
        p2_passed = False
        p2_failed = False
        bust2 = None
        for t in range(p1_ttp, path_len):
            day_start_eq2 = eq2
            eq2 = eq2 * np.exp(path_rets[t])
            days_traded2 += 1
            hwm2 = max(hwm2, eq2)
            day_return_pct = (eq2 - day_start_eq2) / day_start_eq2
            if day_return_pct < -daily_dd:
                bust2 = "daily"
                p2_failed = True
                break
            floor2 = (1 - total_dd) if static_mode else hwm2 * (1 - total_dd)
            if eq2 < floor2:
                bust2 = "total"
                p2_failed = True
                break
            if eq2 >= (1 + p2_tgt) and days_traded2 >= min_days:
                p2_passed = True
                break
        if p2_passed:
            n_funded += 1
            p2_resolutions.append(("FUNDED", t + 1 - p1_ttp))
        elif p2_failed:
            if bust2 == "daily":
                n_bust_daily += 1
            else:
                n_bust_total += 1
            p2_resolutions.append(("BUST_P2_" + bust2, t + 1 - p1_ttp))
        else:
            p2_resolutions.append(("TIMEOUT_P2", path_len - p1_ttp))

    return {
        "n_paths": n_paths,
        "n_funded": n_funded,
        "n_phase1_pass": n_phase1_pass,
        "n_bust_daily": n_bust_daily,
        "n_bust_total": n_bust_total,
        "n_timeout": n_timeout,
        "p_funded": n_funded / n_paths,
        "p_phase1_pass": n_phase1_pass / n_paths,
        "p_bust_daily": n_bust_daily / n_paths,
        "p_bust_total": n_bust_total / n_paths,
        "p_timeout": n_timeout / n_paths,
        "median_p1_ttp": np.median([r[1] for r in p1_resolutions if r[0] == "PASS_P1"])
                          if any(r[0] == "PASS_P1" for r in p1_resolutions) else float("nan"),
        "median_p2_ttp": np.median([r[1] for r in p2_resolutions if r[0] == "FUNDED"])
                          if any(r[0] == "FUNDED" for r in p2_resolutions) else float("nan"),
    }


if __name__ == "__main__":
    print("=" * 90)
    print("BREAKOUTPROP FIT — Strategy A (BTC/ETH/SOL TSMOM v3) vs BreakoutProp Classic")
    print("=" * 90)

    print("\nLoading BTC/ETH/SOL daily closes from Binance M1...")
    prices = build_prices_df()
    print(f"  {len(prices)} daily bars, {prices.index.min().date()} → {prices.index.max().date()}")

    # ---- A at default vol target 0.18 ----
    print("\n" + "=" * 90)
    print(f"ÉTAPE 1 — DD profile of A at vol_target = 0.18 (live spec)")
    print("=" * 90)
    eq_df = backtest_strategy_A(prices, vol_target=0.18, cost_rt=COST_RT)
    eq_df.to_csv(ROOT / "breakoutprop_fit_equity_v018.csv")
    stats = dd_distribution(eq_df)
    print(f"  n_days = {stats['n_days']}, win_rate = {stats['win_rate_pct']:.1f}%")
    print(f"  Annualized return: {stats['ann_ret_pct']:.2f}%, vol: {stats['ann_vol_pct']:.2f}%, Sharpe: {stats['sharpe_ann']:.2f}")
    print(f"  Max total DD (compounded): {stats['max_dd_total_pct']:+.2f}%")
    print(f"  Worst single day: {stats['worst_day_pct']:+.2f}%")
    print(f"  Daily P&L percentiles: p10={stats['p90_loss_pct']:+.2f}%, "
          f"p5={stats['p95_loss_pct']:+.2f}%, p1={stats['p99_loss_pct']:+.2f}%")
    print(f"  Daily P&L std: {stats['daily_ret_std_pct']:.2f}%")

    for thresh in [3, 4, 5]:
        n, pct = count_daily_dd_breaches(eq_df, thresh)
        print(f"  Daily moves worse than -{thresh}%: {n} ({pct:.2f}% of days)")

    # ---- Make-or-break test ----
    print("\n" + "=" * 90)
    print("MAKE-OR-BREAK: Daily DD profile of A vs BreakoutProp limits")
    print("=" * 90)
    rules = BREAKOUTPROP_RULES
    print(f"  BreakoutProp Classic (HUMAN_VERIFY):")
    print(f"    Daily DD limit: {rules['daily_dd_pct']*100:.1f}%")
    print(f"    Total DD limit: {rules['total_dd_pct']*100:.1f}% ({rules['total_dd_mode']})")
    print(f"  A's worst single day: {stats['worst_day_pct']:.2f}%")
    print(f"  A's max DD (compounded): {stats['max_dd_total_pct']:.2f}%")
    if stats['worst_day_pct'] < -rules['daily_dd_pct'] * 100:
        print(f"  ⚠ A's worst day BREACHES the daily DD limit ({stats['worst_day_pct']:.2f}% < -{rules['daily_dd_pct']*100:.1f}%)")
    else:
        print(f"  ✓ A's worst day stays within daily DD limit")
    if stats['max_dd_total_pct'] < -rules['total_dd_pct'] * 100:
        print(f"  ⚠ A's max DD BREACHES the total DD limit ({stats['max_dd_total_pct']:.2f}% < -{rules['total_dd_pct']*100:.1f}%)")
    else:
        print(f"  ✓ A's max DD stays within total DD limit")

    # ---- Étape 2 : block-bootstrap p(pass) at default vol ----
    print("\n" + "=" * 90)
    print("ÉTAPE 2 — Block-bootstrap p(pass) BreakoutProp Classic ($25K, 2-phase)")
    print("=" * 90)
    res = simulate_challenge_2phase(eq_df["log_ret_net"], rules, n_paths=5000, seed=42)
    print(f"  vol_target=0.18  → p(funded)={res['p_funded']*100:.1f}%  "
          f"p(P1)={res['p_phase1_pass']*100:.1f}%  "
          f"bust_daily={res['p_bust_daily']*100:.1f}%  "
          f"bust_total={res['p_bust_total']*100:.1f}%  "
          f"timeout={res['p_timeout']*100:.1f}%")
    print(f"  median P1 TTP: {res['median_p1_ttp']:.0f} days; median P2 TTP: {res['median_p2_ttp']:.0f}")

    # ---- Étape 3 : vol-target sweep (L19 de-leveraging) ----
    print("\n" + "=" * 90)
    print("ÉTAPE 3 — De-leveraging sweep (L19): vol_target sensitivity")
    print("=" * 90)
    sweep_rows = []
    for vt in [0.05, 0.08, 0.10, 0.13, 0.15, 0.18, 0.25, 0.35]:
        eq_swp = backtest_strategy_A(prices, vol_target=vt, cost_rt=COST_RT)
        st = dd_distribution(eq_swp)
        sim = simulate_challenge_2phase(eq_swp["log_ret_net"], rules, n_paths=3000, seed=42)
        sweep_rows.append({
            "vol_target": vt,
            "ann_ret_pct": st["ann_ret_pct"],
            "ann_vol_pct": st["ann_vol_pct"],
            "sharpe": st["sharpe_ann"],
            "max_dd_pct": st["max_dd_total_pct"],
            "worst_day_pct": st["worst_day_pct"],
            "p99_loss_pct": st["p99_loss_pct"],
            "p_funded_pct": sim["p_funded"] * 100,
            "p_p1_pct": sim["p_phase1_pass"] * 100,
            "p_bust_daily_pct": sim["p_bust_daily"] * 100,
            "p_bust_total_pct": sim["p_bust_total"] * 100,
            "p_timeout_pct": sim["p_timeout"] * 100,
            "med_p1_ttp_days": sim["median_p1_ttp"],
            "med_p2_ttp_days": sim["median_p2_ttp"],
        })
    sweep_df = pd.DataFrame(sweep_rows)
    sweep_df.to_csv(ROOT / "breakoutprop_fit_levier_sweep.csv", index=False)
    cols_show = ["vol_target", "ann_ret_pct", "max_dd_pct", "worst_day_pct",
                 "p99_loss_pct", "p_funded_pct", "p_bust_daily_pct",
                 "p_bust_total_pct", "med_p1_ttp_days", "med_p2_ttp_days"]
    print(sweep_df[cols_show].round(2).to_string(index=False))

    # ---- Sensitivity to daily DD limit (in case HUMAN_VERIFY shows different) ----
    print("\n" + "=" * 90)
    print("Sensitivity to actual BreakoutProp daily DD limit (vol_target=0.18)")
    print("=" * 90)
    for ddl in [0.03, 0.04, 0.05, 0.06, 0.08, 0.10]:
        rules_alt = dict(rules)
        rules_alt["daily_dd_pct"] = ddl
        sim = simulate_challenge_2phase(eq_df["log_ret_net"], rules_alt,
                                          n_paths=3000, seed=42)
        print(f"  daily_dd={ddl*100:4.1f}%  → p(funded)={sim['p_funded']*100:5.1f}%  "
              f"p_bust_daily={sim['p_bust_daily']*100:5.1f}%  "
              f"p_bust_total={sim['p_bust_total']*100:5.1f}%")
