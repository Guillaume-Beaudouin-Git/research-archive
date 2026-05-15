"""
Strategy C — Feasibility comparison runner.
Runs Test A (macro cross-asset) and Test B (4h intraday) in sequence,
then prints the comparison table and decision.

Usage:
    /usr/bin/python3 -m strategies.strategy_c_search
"""

from __future__ import annotations

import numpy as np
from strategies.strategy_c_search.macro_signal_feasibility    import main as run_macro
from strategies.strategy_c_search.intraday_pattern_feasibility import main as run_intraday


def _fmt(val: float | None, decimals: int = 4) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    if decimals == 4:
        return f"{val:+.4f}"
    return f"{val:+.3f}"


def print_comparison(a: dict, b: dict) -> None:
    W, C = 31, 14

    hdr   = f"┌{'─'*W}┬{'─'*C}┬{'─'*C}┐"
    title = f"│ {'Metric':<{W-2}} │ {'Test A Macro':^{C-2}} │ {'Test B 4h':^{C-2}} │"
    div   = f"├{'─'*W}┼{'─'*C}┼{'─'*C}┤"
    bot   = f"└{'─'*W}┴{'─'*C}┴{'─'*C}┘"

    def row(label: str, va: str, vb: str) -> str:
        return f"│ {label:<{W-2}} │ {va:^{C-2}} │ {vb:^{C-2}} │"

    rows = [
        ("IC (full period)",          _fmt(a.get("ic_full")),    _fmt(b.get("ic_full"))),
        ("IC t-stat",                  _fmt(a.get("t_stat"),3),   _fmt(b.get("t_stat"),3)),
        ("ICIR",                       _fmt(a.get("icir"),3),     _fmt(b.get("icir"),3)),
        ("IC (2023–2026 sub-period)", _fmt(a.get("ic_sub")),     _fmt(b.get("ic_sub"))),
        ("Corr with TSMOM signal",    _fmt(a.get("tsmom_corr"),3),_fmt(b.get("tsmom_corr"),3)),
        ("Verdict",                    a.get("verdict","?"),       b.get("verdict","?")),
    ]

    print(f"\n{'═'*65}")
    print("STRATEGY C FEASIBILITY — COMPARISON TABLE")
    print(f"{'═'*65}")
    print(hdr)
    print(title)
    print(div)
    for label, va, vb in rows:
        print(row(label, va, vb))
    print(bot)

    # Thresholds reminder
    print(f"\n  Pass thresholds:  IC t-stat > 1.5  AND  |corr TSMOM| < 0.30")

    # Additional context
    if b.get("best_signal") and b["best_signal"] != "N/A":
        print(f"  Test B best signal: {b['best_signal']}  "
              f"(data source: {b.get('data_source','?')})")

    # Decision logic
    a_pass = a.get("verdict") == "PASS"
    b_pass = b.get("verdict") == "PASS"

    print(f"\n{'─'*65}")
    print("DECISION")
    print(f"{'─'*65}")
    if a_pass and b_pass:
        ca = abs(a.get("tsmom_corr") or 1.0)
        cb = abs(b.get("tsmom_corr") or 1.0)
        winner = "A" if ca <= cb else "B"
        loser  = "B" if winner == "A" else "A"
        print(f"  Both PASS — backtest both; lead with Test {winner} "
              f"(lower TSMOM corr = {min(ca,cb):.3f})")
        print(f"  If Test {winner} survives backtest: combine with {loser} as 20-30% overlay")
    elif a_pass:
        print("  Only A passes — full backtest macro score as position scaler on TSMOM v3")
        print("  (scale position by clip(macro_score / macro_score.std(), 0, 2))")
    elif b_pass:
        sig = b.get("best_signal","body_score")
        print(f"  Only B passes — full backtest {sig} as standalone signal")
        print("  (run OOS backtest with weekly rebalance, same cost model as TSMOM v3)")
    else:
        print("  Both FAIL — document as SKIP")
        print("  Next candidate: on-chain USDT flows (Chi 2025) — needs CryptoQuant API key")
        print("  Fallback: different asset class overlay (gold/oil futures)")


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("STRATEGY C SEARCH — RUNNING BOTH FEASIBILITY TESTS")
    print("=" * 65)

    print("\n[STEP 1/2] Running Test A — Macro Cross-Asset Signal")
    a = run_macro()

    print("\n[STEP 2/2] Running Test B — 4h Intraday Pattern")
    b = run_intraday()

    print_comparison(a, b)
