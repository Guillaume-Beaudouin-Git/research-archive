"""Per-leg attribution: who is actually held, and who pays the swap bill (L36)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import costs as C
from . import panel as P
from . import strategy as St

OUT = Path(__file__).resolve().parent.parent / "results"


def main() -> None:
    pan, _ = P.build()
    r = St.run(pan, St.Config(name="V0"))
    w = r["weights"]
    dates = w.index
    syms = list(w.columns)
    swap_l = C.swap_bps_frame(syms, dates, "long")
    bill = (w.abs() * (-swap_l) / 1e4).sum()          # cost > 0
    grossw = w.abs().mean()
    hold = (w.abs() > 1e-9).mean()
    ret = P.closes(pan).pct_change().reindex(dates)
    pnl = (w * ret).sum()

    t = pd.DataFrame({
        "class": [C.CLASS[s] for s in syms],
        "pct_time_held": (hold * 100).round(1),
        "mean_notional_pct_equity": (grossw * 100).round(1),
        "gross_pnl_pct_equity": (pnl * 100).round(1),
        "swap_bill_pct_equity": (bill * 100).round(1),
        "net_pct_equity": ((pnl - bill) * 100).round(1),
    }, index=syms).sort_values("swap_bill_pct_equity", ascending=False)
    print(t.to_string())
    print("\nby class:")
    print(t.groupby("class")[["mean_notional_pct_equity", "gross_pnl_pct_equity",
                              "swap_bill_pct_equity", "net_pct_equity"]].sum().round(1).to_string())
    print(f"\ntotal gross {t.gross_pnl_pct_equity.sum():.1f}% | "
          f"swap {t.swap_bill_pct_equity.sum():.1f}% | over {len(dates)} sessions")
    t.to_csv(OUT / "leg_attribution.csv")


if __name__ == "__main__":
    main()
