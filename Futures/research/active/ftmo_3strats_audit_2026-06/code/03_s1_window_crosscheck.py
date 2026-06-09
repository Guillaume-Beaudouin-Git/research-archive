"""
Cross-check: reproduce the report's window 2021-01-01 → 2026-05-31 for S1.

Also produce:
  - sub-yearly breakdown matching the report's table (2021 / 2022 / 2023 / 2024-26)
  - dollar Sharpe equivalents (R-multiple Sharpe is comparable since the report
    cites Sharpe recalculated independently as 0.728)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
RES = ROOT / "Futures/research/active/ftmo_3strats_audit_2026-06/results"


def stats(sub_tr: pd.DataFrame) -> dict:
    if len(sub_tr) == 0:
        return {}
    mean_R = float(sub_tr["pnl_R"].mean())
    std_R = float(sub_tr["pnl_R"].std(ddof=0))
    sh = mean_R / std_R * np.sqrt(252) if std_R > 0 else np.nan
    traded = sub_tr[sub_tr["direction"] != 0]
    n_long = int((traded["direction"] == 1).sum())
    n_short = int((traded["direction"] == -1).sum())
    sum_long = float(traded.loc[traded["direction"] == 1, "pnl_R"].sum())
    sum_short = float(traded.loc[traded["direction"] == -1, "pnl_R"].sum())
    eq = sub_tr["pnl_R"].cumsum()
    dd = eq - eq.cummax()
    return {
        "n_sessions": int(len(sub_tr)),
        "n_trades": int(len(traded)),
        "n_long": n_long,
        "n_short": n_short,
        "mean_R_day": mean_R,
        "std_R_day": std_R,
        "sharpe_R": sh,
        "sum_R": float(sub_tr["pnl_R"].sum()),
        "sum_R_long": sum_long,
        "sum_R_short": sum_short,
        "win_rate": float((traded["pnl_R"] > 0).mean()) if len(traded) else None,
        "max_dd_R": float(dd.min()),
    }


def main() -> None:
    tr = pd.read_parquet(RES / "s1_regime_tagged.parquet")

    splits = {
        "report_window_2021_2026": ("2021-01-01", "2026-05-31"),
        "2021_only": ("2021-01-01", "2021-12-31"),
        "2022_only": ("2022-01-01", "2022-12-31"),
        "2023_only": ("2023-01-01", "2023-12-31"),
        "2024_2026": ("2024-01-01", "2026-05-31"),
        "report_minus_recent_bull": ("2021-01-01", "2022-12-31"),
        "full_2010_2026": ("2010-06-06", "2026-05-31"),
        "pre_report_window": ("2010-06-06", "2020-12-31"),
    }

    out = {}
    for label, (a, b) in splits.items():
        sub = tr.loc[a:b]
        out[label] = stats(sub)

    print(json.dumps(out, indent=2, default=str))
    (RES / "s1_window_crosscheck.json").write_text(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
