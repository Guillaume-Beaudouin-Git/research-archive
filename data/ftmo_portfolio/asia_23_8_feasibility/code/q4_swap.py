"""Q4 — rollover/swap risk on the FTMO infra specifically.

Server TZ confirmed read-only from ftmo_live/lib/market_hours.py:
  summer EEST = UTC+3 (until 2026-10-25), winter EET = UTC+2.
Swap rollover = 00:00 server = 21:00 UTC (summer) / 22:00 UTC (winter).
ASIA holds 23:00 UTC (entry) -> 07:00 UTC next day (exit). Question: does the holding
interval contain a rollover instant? And what does the avoided swap cost (counterfactual)?
"""
import json, sys
from pathlib import Path
import numpy as np

YT = Path("<HOME>/Desktop/Algo_claude/yt_strategy_replications")
sys.path.insert(0, str(HERE := Path(__file__).resolve().parent))
import asia_series as ASER
sys.path.insert(0, str(Path("<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/v22")))
import config_v22 as C22
OUT = HERE.parent / "results"
ENTRY_UTC, EXIT_UTC = 23, 7 + 24      # 07:00 next day on a 0..47h axis


def contains_rollover(roll_utc):
    """Is the rollover hour (UTC) inside the half-open holding interval [23:00, 31:00)?"""
    return ENTRY_UTC <= roll_utc < EXIT_UTC      # roll on the SAME civil day as entry


def main():
    res = {}
    # rollover instants (UTC) for the two seasons; civil-day rollover happens daily at these hours
    seasons = {"summer_EEST_utc+3": 21, "winter_EET_utc+2": 22}
    # the rollover relevant to the holding interval is the NEXT one after 23:00 entry:
    # next rollover is on day D+1 at 21:00/22:00 UTC = hour 45/46 on the 0..47h axis -> AFTER exit (31).
    # the previous rollover (day D, 21:00/22:00 UTC) is BEFORE entry (23:00). So none inside.
    roll_check = {}
    for s, h in seasons.items():
        prev_roll = h                 # 21 or 22 (before 23 entry)
        next_roll = h + 24            # 45 or 46 (after 31 exit)
        inside = (ENTRY_UTC <= prev_roll < EXIT_UTC) or (ENTRY_UTC <= next_roll < EXIT_UTC)
        roll_check[s] = dict(rollover_utc=h, prev_roll_axis=prev_roll, next_roll_axis=next_roll,
                             entry_axis=ENTRY_UTC, exit_axis=EXIT_UTC,
                             rollover_inside_holding=bool(inside),
                             gap_entry_to_prev_roll_h=ENTRY_UTC - prev_roll)
    res["server_rollover"] = roll_check
    n_nights = 0      # swap nights charged = number of rollovers strictly inside holding
    res["swap_nights_charged"] = n_nights
    res["swap_free_confirmed"] = (n_nights == 0
                                  and all(not v["rollover_inside_holding"] for v in roll_check.values()))
    xau = C22.MEASURED_SPECS["XAUUSD"]
    res["xau_swap_spec"] = dict(swap_long_pts=xau["swap_long_pts"],
                                swap_long_bps_per_night=round(C22.swap_bps("XAUUSD", "long"), 3),
                                triple_dow=xau["triple_dow"], triple_dow_name="Wednesday(=2)",
                                note="triple charged Wed; N/A while swap-free (window never crosses rollover)")

    # counterfactual: if the long swap WERE charged each night (entry slipped before rollover)
    a0 = ASER.build(1.5)
    base = a0.copy()
    sw_bp = abs(C22.swap_bps("XAUUSD", "long"))     # 1.518 bp/night
    import importlib.util
    spec = importlib.util.spec_from_file_location("yt_stats", YT / "engine" / "stats.py")
    S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
    pos = base["pos"]; onr = base["raw_log"]
    for tag, swday in {"swap_free": 0.0, "swap_1x_everyday": sw_bp,
                       "swap_avg_with_wed_triple": sw_bp * (4 + 1) / 4}.items():
        net = (pos * (np.exp(onr) - 1.0) - pos.abs() * (1.5 + swday) * 1e-4).to_numpy()
        res.setdefault("counterfactual_sharpe", {})[tag] = round(S.sharpe_ratio(net, 252), 3)
    print("=== Q4 swap/rollover ===")
    print(f"  swap-free confirmed: {res['swap_free_confirmed']}  (nights charged: {n_nights})")
    for s, v in roll_check.items():
        print(f"  {s}: rollover {v['rollover_utc']}:00 UTC, inside holding [23:00,07:00+1d)? "
              f"{v['rollover_inside_holding']}  (entry is {v['gap_entry_to_prev_roll_h']}h after prev rollover)")
    print(f"  XAU long swap: {res['xau_swap_spec']['swap_long_bps_per_night']} bp/night, triple Wed")
    print(f"  counterfactual Sharpe: {res['counterfactual_sharpe']}")
    (OUT / "q4_swap.json").write_text(json.dumps(res, indent=2, default=str))
    print("written q4_swap.json")


if __name__ == "__main__":
    main()
