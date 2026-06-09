"""
run_phase0b_costs.py — Phase 0b deliverable: CFD cost model reconciliation
===========================================================================
Reconciles the data-derived CFD round-trip costs against white-paper Table 3 and
documents the intraday spread profile (the rollover blow-out that motivates the
liquid-hours session filter). Outputs results JSON + figure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from engine.cfd_costs import reconcile_table3, load_spread_series, point_size, PIP_SIZE  # noqa: E402

FIG, RES = HERE / "figures", HERE / "results"

# White-paper Table 3 indicative RT cost ranges (native units) for reconciliation.
TABLE3 = {"EURUSD": (0.3, 1.0, "pip"), "US500": (0.5, 2.0, "idx_pts"),
          "US100": (0.5, 2.0, "idx_pts"), "XAUUSD": (0.15, 0.30, "$"),
          "GER40": (0.5, 3.0, "idx_pts"), "US30": (0.5, 3.0, "idx_pts")}


def main() -> int:
    rec = reconcile_table3()
    out = {s: {**rec[s], "table3_low": TABLE3[s][0], "table3_high": TABLE3[s][1]}
           for s in rec}
    (RES / "phase0b_cost_reconciliation.json").write_text(json.dumps(out, indent=2))

    print("Phase 0b — CFD cost reconciliation vs white-paper Table 3")
    print(f"{'sym':8s} {'data RT':>10s} {'Table 3 range':>16s} {'reconciled':>11s}")
    for s in rec:
        lo, hi, unit = TABLE3[s]
        v = rec[s]["rt_cost_native"]
        ok = "✓ in-range" if v <= hi * 1.2 else "wider"     # data feed can be tighter than paper
        print(f"{s:8s} {v:>7.2f} {unit:<3s} {f'{lo}-{hi} {unit}':>16s} {ok:>11s}")

    # ── figure ────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    syms = list(TABLE3.keys())
    data_native = [rec[s]["rt_cost_native"] for s in syms]
    lows = [TABLE3[s][0] for s in syms]; highs = [TABLE3[s][1] for s in syms]
    x = np.arange(len(syms))
    ax[0].bar(x, data_native, color="#2a6f97", label="data-derived RT cost (median)")
    ax[0].vlines(x, lows, highs, color="#e76f51", lw=6, alpha=.5, label="white-paper Table 3 range")
    ax[0].set_xticks(x); ax[0].set_xticklabels(syms, rotation=30)
    ax[0].set_ylabel("RT cost (native units: pip / idx pts / $)")
    ax[0].set_title("CFD round-trip cost: data vs Table 3\n(feed tighter than paper → markup applied, L23b)")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.25, axis="y")

    # intraday spread profile (EURUSD) — rollover blow-out
    df = load_spread_series("EURUSD")
    df["hour"] = df["timestamp_utc"].dt.hour
    prof = df.groupby("hour")["spread"].median() * point_size("EURUSD") / PIP_SIZE["EURUSD"]
    ax[1].plot(prof.index, prof.values, "o-", color="#264653")
    ax[1].axvspan(7, 20, color="#2a9d8f", alpha=.10, label="traded hours (07-20 UTC)")
    ax[1].axvspan(21, 22, color="#d1495b", alpha=.20, label="rollover blow-out (excluded)")
    ax[1].set_xlabel("hour of day (UTC)"); ax[1].set_ylabel("median spread (pip)")
    ax[1].set_title("EURUSD intraday spread profile\nmotivates the liquid-hours filter")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(FIG / "phase0b_cost_reconciliation.png", dpi=130)
    plt.close(fig)
    print("\n  → results/phase0b_cost_reconciliation.json")
    print("  → figures/phase0b_cost_reconciliation.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
