"""
log_trade.py — Strategy C paper trade logger
=============================================
Usage:
  python log_trade.py add --date 2026-05-22 --entry-time "09:31" --exit-time "10:45" \
      --direction long --entry 21450 --exit 21520 --exit-reason TP \
      --contracts 0.25 --gap 0.008 --filter A --notes "clean breakout"

  python log_trade.py summary    # print running P&L and stats

Strategy: NQ iter_05 A$400 + B1.2% gap filter
  - Entry: 09:30-09:31 ET on opening signal
  - Direction: long or short (opening momentum)
  - Contracts: 0.25 (paper, = 2-3 /MNQ)
  - Costs: $19 RT per contract (= $4.75 per 0.25c)
  - Signals: iter_05 A$400 stop, 1.2% gap filter
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path

LOG_CSV     = Path(__file__).parent / "paper_trade_log.csv"
POINT_VALUE = 20.0
COST_RT     = 19.0
CAPITAL     = 50_000.0

FIELDS = [
    "date", "entry_time_et", "exit_time_et", "direction",
    "entry_price", "exit_price", "exit_reason", "contracts",
    "pnl_points", "pnl_usd", "signal_gap_pct", "signal_or_filter", "notes",
]


def add_trade(args: argparse.Namespace) -> None:
    direction  = args.direction.lower()
    entry_px   = float(args.entry)
    exit_px    = float(args.exit)
    contracts  = float(args.contracts)
    gap_pct    = float(args.gap) if args.gap else float("nan")

    sign       = 1 if direction == "long" else -1
    pnl_points = sign * (exit_px - entry_px)
    pnl_usd    = pnl_points * contracts * POINT_VALUE - contracts * COST_RT

    row = {
        "date":             args.date,
        "entry_time_et":    args.entry_time,
        "exit_time_et":     args.exit_time,
        "direction":        direction,
        "entry_price":      entry_px,
        "exit_price":       exit_px,
        "exit_reason":      args.exit_reason,
        "contracts":        contracts,
        "pnl_points":       round(pnl_points, 2),
        "pnl_usd":          round(pnl_usd, 2),
        "signal_gap_pct":   round(gap_pct, 4) if not (gap_pct != gap_pct) else "",
        "signal_or_filter": args.filter or "",
        "notes":            args.notes or "",
    }

    write_header = not LOG_CSV.exists() or LOG_CSV.stat().st_size == 0
    with open(LOG_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        w.writerow(row)

    print(f"Logged: {row['date']} {direction.upper()}  "
          f"entry={entry_px:.0f} exit={exit_px:.0f}  "
          f"pts={pnl_points:+.1f}  P&L=${pnl_usd:+.2f}  "
          f"({args.exit_reason})")


def summary() -> None:
    if not LOG_CSV.exists():
        print("No trades logged yet.")
        return

    with open(LOG_CSV) as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No trades logged yet.")
        return

    n          = len(rows)
    pnl_list   = [float(r["pnl_usd"]) for r in rows if r["pnl_usd"]]
    total_pnl  = sum(pnl_list)
    wins       = [p for p in pnl_list if p > 0]
    losses     = [p for p in pnl_list if p < 0]
    wr         = len(wins) / n if n else 0
    avg_win    = sum(wins) / len(wins) if wins else 0
    avg_loss   = sum(losses) / len(losses) if losses else 0

    print(f"\n{'='*50}")
    print(f"Strategy C Paper Trade Log — {date.today()}")
    print(f"{'='*50}")
    print(f"  Total trades:    {n}")
    print(f"  Win rate:        {wr:.1%}  ({len(wins)}W / {len(losses)}L)")
    print(f"  Avg win:        ${avg_win:+.2f}")
    print(f"  Avg loss:       ${avg_loss:+.2f}")
    print(f"  Total P&L:      ${total_pnl:+.2f}  ({total_pnl/CAPITAL*100:+.2f}% of ${CAPITAL:,.0f})")
    if losses:
        pf = sum(wins) / (-sum(losses))
        print(f"  Profit factor:   {pf:.3f}")
    print()
    print(f"  Recent trades:")
    for r in rows[-5:]:
        print(f"    {r['date']} {r['direction'].upper():<6}  "
              f"P&L: ${float(r['pnl_usd']):+.2f}  ({r['exit_reason']})")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Strategy C paper trade logger")
    sub    = parser.add_subparsers(dest="cmd")

    # add subcommand
    add_p = sub.add_parser("add", help="Log a new trade")
    add_p.add_argument("--date",       required=True, help="YYYY-MM-DD")
    add_p.add_argument("--entry-time", required=True, help="HH:MM ET")
    add_p.add_argument("--exit-time",  required=True, help="HH:MM ET")
    add_p.add_argument("--direction",  required=True, choices=["long", "short"])
    add_p.add_argument("--entry",      required=True, type=float, help="Entry price (NQ points)")
    add_p.add_argument("--exit",       required=True, type=float, help="Exit price")
    add_p.add_argument("--exit-reason",required=True, choices=["TP", "SL", "TIME", "EOD", "MANUAL"])
    add_p.add_argument("--contracts",  default=0.25, type=float, help="Contract size (default 0.25)")
    add_p.add_argument("--gap",        default=None, help="Opening gap % (e.g. 0.013 = 1.3%%)")
    add_p.add_argument("--filter",     default=None, choices=["A", "B", "both"],
                       help="Which iter_05 filter triggered: A ($400 stop), B (1.2%% gap), both")
    add_p.add_argument("--notes",      default=None, help="Free text notes")

    # summary subcommand
    sub.add_parser("summary", help="Print running statistics")

    args = parser.parse_args()

    if args.cmd == "add":
        add_trade(args)
    elif args.cmd == "summary":
        summary()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
