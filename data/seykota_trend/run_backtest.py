"""Run replication (video window) and extended (full history) backtests."""

from pathlib import Path

import pandas as pd

from engine import Params, load_universe, simulate
from metrics import equity_metrics, monthly_table, per_asset_table, trade_metrics

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

UNIVERSE = ["US500", "US100", "XAUUSD", "USOIL", "BTC", "ETH"]


def run(tag: str, start: str | None, end: str | None, params: Params = Params()) -> dict:
    data = load_universe(UNIVERSE)
    res = simulate(data, params, initial_equity=100_000, start=start, end=end)
    ec, tr = res["equity"], res["trades"]

    em = equity_metrics(ec)
    tm = trade_metrics(tr)
    ec.to_csv(OUT / f"equity_{tag}.csv")
    tr.to_csv(OUT / f"trades_{tag}.csv", index=False)
    per_asset_table(tr, ec).to_csv(OUT / f"per_asset_{tag}.csv", index=False)
    monthly_table(ec).to_csv(OUT / f"monthly_{tag}.csv")
    pd.Series({**em, **tm}).to_csv(OUT / f"metrics_{tag}.csv")

    print(f"\n========== {tag} ==========")
    for k, v in {**em, **tm}.items():
        print(f"{k:>22}: {v:,.4f}" if isinstance(v, float) else f"{k:>22}: {v}")
    print(per_asset_table(tr, ec).to_string(index=False))
    return res


RUNS = {
    # A. Literal reading of the rules (1% risk PER UNIT -> leveraged)
    "replication": dict(start="2020-06-01", end="2026-06-05", params=Params()),
    # B. Cash-account variant: gross exposure capped at 100% (no leverage),
    #    closest to a retail brokerage backtest like the video's
    "replication_capped": dict(
        start="2020-06-01", end="2026-06-05", params=Params(max_gross=1.0)
    ),
    # C/D. Extended sample 2014-2026, both variants
    "extended": dict(start="2014-09-17", end="2026-06-05", params=Params()),
    "extended_capped": dict(
        start="2014-09-17", end="2026-06-05", params=Params(max_gross=1.0)
    ),
}

if __name__ == "__main__":
    import sys

    tags = sys.argv[1:] or list(RUNS)
    for tag in tags:
        cfg = RUNS[tag]
        run(tag, cfg["start"], cfg["end"], cfg["params"])
