"""
Strategy C Search — full feasibility runner.
Runs Tests A/B/C/D and prints consolidated IC table + decision tree.

Tests:
  A — Macro composite (VIX/DXY/SPY/GLD), no lag
  B — 4h Hyperliquid body score (US session weekly aggregate)
  C — Macro composite with lag correction + position scaler
  D — Google Trends 'bitcoin' attention z-score (Liu & Tsyvinski 2021)

Usage:
    /usr/bin/python3 -m strategies.strategy_c_search
"""

from __future__ import annotations

import numpy as np

from strategies.strategy_c_search.macro_signal_feasibility     import main as run_macro
from strategies.strategy_c_search.intraday_pattern_feasibility  import main as run_intraday
from strategies.strategy_c_search.macro_lagged_feasibility      import main as run_macro_lagged
from strategies.strategy_c_search.google_trends_feasibility     import main as run_trends


# ── Formatting helpers ────────────────────────────────────────────────────────

def _f(v, w: int = 7, d: int = 4) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A".center(w)
    return f"{v:+.{d}f}".center(w)

def _ft(v, w: int = 7) -> str:
    return _f(v, w, 3)

def _verdict(v, w: int = 7) -> str:
    return str(v or "?").center(w)


# ── Consolidated table ────────────────────────────────────────────────────────

def print_table(rows: list[tuple]) -> None:
    """
    rows: list of (label, ic_full, t_stat, icir, tsmom_corr, verdict)
    """
    W, C1, C2, C3, C4, C5 = 32, 9, 9, 8, 11, 9

    hdr = (f"┌{'─'*W}┬{'─'*C1}┬{'─'*C2}┬{'─'*C3}┬{'─'*C4}┬{'─'*C5}┐")
    div = (f"├{'─'*W}┼{'─'*C1}┼{'─'*C2}┼{'─'*C3}┼{'─'*C4}┼{'─'*C5}┤")
    bot = (f"└{'─'*W}┴{'─'*C1}┴{'─'*C2}┴{'─'*C3}┴{'─'*C4}┴{'─'*C5}┘")

    def row(label, ic, ts, icir, corr, verd):
        return (f"│ {label:<{W-2}} │{ic:^{C1}}│{ts:^{C2}}│{icir:^{C3}}│{corr:^{C4}}│{verd:^{C5}}│")

    print(f"\n{'═'*82}")
    print("STRATEGY C SEARCH — CONSOLIDATED IC TABLE")
    print(f"{'═'*82}")
    print(hdr)
    print(row("Signal", "IC full", "t-stat", "ICIR", "Corr TSMOM", "Verdict"))
    print(div)
    for label, ic, ts, icir, corr, verd in rows:
        print(row(label, _f(ic), _ft(ts), _ft(icir), _ft(corr), _verdict(verd)))
    print(bot)
    print(f"  Pass thresholds: |t-stat| > 1.5  AND  |corr TSMOM| < 0.30")


# ── Decision tree ─────────────────────────────────────────────────────────────

def print_decision(a, c, d, scaler) -> None:
    trends_pass   = d.get("verdict") == "PASS"
    trends_scaler = d.get("verdict") in ("PASS", "SCALER")
    comp_pass     = c.get("comp_pass", False)
    any_lag_pass  = c.get("any_lag_pass", False)
    sc            = c.get("scaler", {})
    scaler_helps  = sc.get("delta", -1) > 0
    scaler_strong = sc.get("sharpe_scaled", 0) > 1.40

    print(f"\n{'─'*82}")
    print("DECISION TREE")
    print(f"{'─'*82}")

    decided = False

    if trends_pass and abs(d.get("tsmom_corr", 1)) < 0.30:
        print("  [1] TRENDS PASS — GO")
        print(f"      Run full backtest: 'google_trends' as standalone signal")
        print(f"      Also test: combined with TSMOM v3 (hedge ratio based on corr)")
        print(f"      Direction: {d.get('direction','?')}")
        decided = True

    if not decided and trends_scaler and abs(d.get("tsmom_corr", 1)) < 0.30:
        print("  [1] TRENDS SCALER (t-stat 1.0–1.5) — position multiplier test")
        print(f"      t-stat={d.get('t_stat',np.nan):.3f} — below GO threshold but worth scaling")
        print(f"      Implement: scale TSMOM v3 position by 1.0 if z>0.5 else 0.6")
        decided = True

    if any_lag_pass:
        lag_key = [k for k in ("lag1","lag2") if c.get(k,{}).get("t_stat",0) > 1.5]
        print(f"  [2] MACRO LAG PASS — GO")
        print(f"      Lagged composite clears IC threshold (lag {', '.join(lag_key)}w)")
        print(f"      Rebuild composite using only predictive components")
        decided = True

    if comp_pass:
        print(f"  [2] MACRO COMPONENT PASS — GO")
        print(f"      Best component: {c.get('best_comp',{}).get('name','?')} — rebuild composite with this alone")
        decided = True

    if scaler_strong:
        print(f"  [3] MACRO SCALER IMPROVES SHARPE > 1.40 — IMPLEMENT")
        print(f"      BTC-only: C1={sc.get('sharpe_c1',np.nan):.3f} → scaled={sc.get('sharpe_scaled',np.nan):.3f}")
        print(f"      Add binary macro scale (100%/40%) to production rebalance.py")
        decided = True
    elif scaler_helps:
        print(f"  [3] MACRO SCALER HELPS (+{sc.get('delta',0):.3f} Sharpe) BUT <1.40 threshold")
        print(f"      C1={sc.get('sharpe_c1',np.nan):.3f} → scaled={sc.get('sharpe_scaled',np.nan):.3f} on BTC")
        print(f"      → NOT deploying (insufficient magnitude on single asset)")

    if not decided:
        print("  ALL TESTS FAIL — move to on-chain data")
        print()
        print("  Next candidates (free tier available):")
        print("  ┌─────────────────────────────────────────────────────────┐")
        print("  │ Glassnode free tier — sign up at glassnode.com (free)  │")
        print("  │   MVRV Z-score  : market value / realised value        │")
        print("  │   Active addrs  : daily unique active BTC addresses    │")
        print("  │   Exchange flow : net BTC inflow to exchanges          │")
        print("  │ Test endpoint:                                          │")
        print("  │   GET api.glassnode.com/v1/metrics/market/mvrv_z_score │")
        print("  │       ?a=BTC&i=24h&api_key=<free_tier_key>             │")
        print("  │ If user has key: test MVRV z-score as timing signal   │")
        print("  └─────────────────────────────────────────────────────────┘")
        print()
        print("  CryptoQuant USDT flows (Chi 2025): $49/month basic plan")
        print("  → Defer until Glassnode free-tier is exhausted")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 82)
    print("STRATEGY C SEARCH — ALL FEASIBILITY TESTS")
    print("=" * 82)

    # ── Test A: macro composite (no lag)
    print("\n[TEST A] Macro Cross-Asset Signal (no lag)")
    a = run_macro()

    # ── Test B: 4h intraday
    print("\n[TEST B] 4h Intraday Pattern")
    b = run_intraday()

    # ── Test C: macro lagged + scaler (reuse preloaded data if possible)
    print("\n[TEST C] Macro Lagged + Position Scaler")
    c = run_macro_lagged()

    # ── Test D: Google Trends attention
    print("\n[TEST D] Google Trends Attention Signal")
    d = run_trends()

    # ── Consolidated table
    #  Known from Test A: lag0 row uses a["ic_full"], a["t_stat"], etc.
    #  Test C provides lag1, lag2, best_comp.
    #  Test B best signal.
    #  Test D Google Trends.

    lag0 = {"ic": a.get("ic_full"), "t":  a.get("t_stat"),
            "icir": a.get("icir"),  "corr": a.get("tsmom_corr")}

    lag1 = c.get("lag1", {})
    lag2 = c.get("lag2", {})
    bc   = c.get("best_comp", {})
    scaler = c.get("scaler", {})

    table_rows = [
        ("Macro composite (no lag)",       lag0["ic"], lag0["t"], lag0["icir"], lag0["corr"], a.get("verdict")),
        ("Macro composite (lag 1w)",        lag1.get("ic"), lag1.get("t_stat"), lag1.get("icir"), lag1.get("tsmom_corr"), "—"),
        ("Macro composite (lag 2w)",        lag2.get("ic"), lag2.get("t_stat"), lag2.get("icir"), lag2.get("tsmom_corr"), "—"),
        (f"Best component ({bc.get('name','?')}) lag1", bc.get("ic"), bc.get("t_stat"), bc.get("icir"), bc.get("tsmom_corr"), "—"),
        ("Google Trends z-score",           d.get("ic_full"), d.get("t_stat"), d.get("icir"), d.get("tsmom_corr"), d.get("verdict")),
    ]

    print_table(table_rows)

    # Scaler summary row
    print(f"\n  Macro scaler (BTC-only): "
          f"C1={scaler.get('sharpe_c1', np.nan):.3f} → "
          f"scaled={scaler.get('sharpe_scaled', np.nan):.3f}  "
          f"Δ={scaler.get('delta', np.nan):+.3f}  "
          f"{'(threshold 1.40)' if scaler.get('sharpe_scaled', 0) > 1.40 else ''}")

    print_decision(a, c, d, scaler)
