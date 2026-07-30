"""Step (a): panel quality audit — holes, holidays, cross-class calendar mismatch,
measured spread level vs the frozen live anchors."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import costs as C
from . import panel as P

OUT = Path(__file__).resolve().parent.parent / "results"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pan, rep = P.build()
    sub = pan.loc[P.START:]
    sp_med = C.spread_bps(sub, "spread_med")
    sp_p95 = C.spread_bps(sub, "spread_p95")
    tr = P.traded(sub)

    rep = rep.set_index("symbol")
    rep["spread_med_bps"] = sp_med.where(tr > 0).median().round(3)
    rep["spread_p95_bps"] = sp_p95.where(tr > 0).median().round(3)
    rep["spread_med_bps_2020+"] = sp_med.loc["2020":].where(tr.loc["2020":] > 0).median().round(3)
    rep = rep.drop(columns=["spread_med_bps_2013_26"])

    # live anchors: rt_bps_legs (spread+slippage RT, measured on the live account)
    anchors = {"XAUUSD": 1.84, "USDJPY": 1.36, "US100": 2.20, "GER40": 2.20}
    rows = []
    for s, a in anchors.items():
        modeled_rt = float(rep.loc[s, "spread_med_bps_2020+"]) + C.COMM_RT_BPS[C.CLASS[s]]
        rows.append({"symbol": s, "live_rt_anchor_bps": a,
                     "panel_rt_bps_2020+": round(modeled_rt, 3),
                     "ratio_live_over_panel": round(a / modeled_rt, 2)})
    anchor_chk = pd.DataFrame(rows)

    # calendar mismatch across classes
    cls = pd.Series({s: C.CLASS[s] for s in P.UNIVERSE})
    mism = {}
    for c in ["fx", "index", "metal", "commodity"]:
        cols = [s for s in P.UNIVERSE if cls[s] == c]
        mism[c] = round(100 * (1 - tr[cols].mean(axis=1)).mean(), 2)
    n_days = len(sub)
    all_open = float((tr.min(axis=1) > 0).mean() * 100)

    print(rep.to_string())
    print("\n-- live-anchor vs panel-measured round-trip cost --")
    print(anchor_chk.to_string(index=False))
    print(f"\nmaster calendar sessions {P.START}..{P.END}: {n_days}")
    print(f"all 17 instruments simultaneously open: {all_open:.1f}% of sessions")
    print("mean % of sessions closed, by class:", mism)

    rep.to_csv(OUT / "panel_quality.csv")
    anchor_chk.to_csv(OUT / "spread_anchor_check.csv", index=False)
    (OUT / "panel_quality.json").write_text(json.dumps({
        "sessions": int(n_days), "all_open_pct": all_open,
        "closed_pct_by_class": mism,
        "start": P.START, "end": P.END,
    }, indent=2))


if __name__ == "__main__":
    main()
