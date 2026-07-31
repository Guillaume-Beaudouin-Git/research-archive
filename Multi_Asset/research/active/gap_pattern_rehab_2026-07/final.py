"""
final.py — consolidated ladder: published headline -> honest headline.

Each rung removes one documented defect. Nothing here changes a parameter of the
strategy; every rung is a re-pricing or a data-hygiene exclusion.

  0. as published                      (audit numbers)
  1. + realistic EXIT fill             (open-gap fill, L26 applied to the exit)
  2. + measured FTMO overnight carry   (L36, phase0_swap_model.csv)
  3. + drop degenerate-range series    (XPTUSD/XPDUSD median daily range = 0)
  4. + recent regime only              (L31)
"""
from __future__ import annotations
import os, sys, json
import numpy as np, pandas as pd

ROOT = "<HOME>/Desktop/Algo_claude"
AUDIT = f"{ROOT}/Multi_Asset/research/archived/oxfordstrat_109_audit"
sys.path.insert(0, os.path.join(AUDIT, "code"))
os.environ.setdefault("OHLC_DIR", os.path.join(AUDIT, "ohlc"))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ftmo_lab as lab                       # noqa: E402
import mechanism as M                        # noqa: E402
import mechanism2 as M2                      # noqa: E402
from exitfill import pooled                  # noqa: E402
M.PROXY["GER40"] = "US500"

DEGENERATE = ["XPTUSD", "XPDUSD"]            # median daily range == 0
THIN = DEGENERATE + ["XAGUSD"]               # + 22.7% zero-range bars


def line(tr, label, col="netR"):
    x = tr.assign(netR=tr[col])
    m = lab.trade_metrics(x)
    bb = M2.block_bootstrap(x, "netR", n_boot=1500)
    return dict(rung=label, n=len(tr), expR=float(tr[col].mean()),
                sharpe=float(m["sharpe"]), maxdd=float(m["maxdd"]),
                long=float(tr.loc[tr["dir"] == 1, col].mean()),
                short=float(tr.loc[tr["dir"] == -1, col].mean()),
                boot_lo=bb["p2_5"], boot_hi=bb["p97_5"], boot_p_le_0=bb["p_le_0"])


if __name__ == "__main__":
    OUT = {}
    for variant, tag in (("A", "s035"), ("B", "s036")):
        a = pooled(variant, "stop_exact")
        b = pooled(variant, "open_gap")
        aw, bw = M.add_swap(a), M.add_swap(b)
        rows = [line(a, "0. as published"),
                line(b, "1. + realistic exit fill"),
                line(bw, "2. + measured FTMO swap", "netR_swap"),
                line(bw[~bw["instr"].isin(DEGENERATE)], "3. - zero-range XPT/XPD", "netR_swap"),
                line(bw[~bw["instr"].isin(THIN)], "3b. - XPT/XPD/XAG", "netR_swap")]
        r4 = bw[(~bw["instr"].isin(DEGENERATE)) &
                (pd.to_datetime(bw["entry"]) > pd.Timestamp("2018-12-31"))]
        rows.append(line(r4, "4. + recent regime 2019+", "netR_swap"))
        df = pd.DataFrame(rows)
        df.to_csv(os.path.join(HERE, f"{tag}_ladder.csv"), index=False)
        OUT[tag] = json.loads(df.to_json(orient="records"))
        print("=" * 100); print(tag)
        pd.set_option("display.width", 250)
        print(df.round(5).to_string(index=False))

        # P&L share of the degenerate series, as published
        s = a.groupby("instr")["netR"].sum()
        tot = s.sum()
        print(f"  P&L share XPT+XPD (median daily range = 0): "
              f"{s.reindex(DEGENERATE).sum()/tot*100:.1f}%   "
              f"+XAG: {s.reindex(THIN).sum()/tot*100:.1f}%   (total netR {tot:.1f} R)")
        OUT[tag + "_degenerate_pnl_share_pct"] = float(s.reindex(DEGENERATE).sum() / tot * 100)
        OUT[tag + "_thin_pnl_share_pct"] = float(s.reindex(THIN).sum() / tot * 100)

    with open(os.path.join(HERE, "final_ladder.json"), "w") as f:
        json.dump(OUT, f, indent=1)
