"""
monitor.py — Daily P&L attribution dashboard (TSMOM + Delta-Neutral).

Reads from existing log files only. No exchange calls. No new dependencies.
Sends one Telegram message at 00:30 UTC, after both strategy crons have run.

Log sources:
  ~/logs/tsmom.log                        (TSMOM cron stdout)
  ~/projects/Algo_claude/logs/tsmom_trades.csv
  ~/projects/Algo_claude/logs/fills.csv   (actual HL fill prices)
  ~/projects/Algo_claude/logs/delta_neutral_carry.csv
  ~/logs/delta_neutral.log                (DN cron stdout)

P&L note:
  TSMOM P&L is computed from consecutive price diffs in tsmom_trades.csv.
  The price column is the yfinance close used for signal computation (T-2
  due to yfinance free-tier lag), so daily P&L is an approximation.
  Actual entry prices come from fills.csv when available.

Cron:
  30 0 * * * /home/algo/run_monitor.sh >> /home/algo/logs/monitor.log 2>&1
"""
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
LOG_HOME  = Path.home() / "logs"
PROJ_LOGS = REPO_ROOT / "logs"
sys.path.insert(0, str(REPO_ROOT))

import notifier

TSMOM_LOG    = LOG_HOME  / "tsmom.log"
TSMOM_TRADES = PROJ_LOGS / "tsmom_trades.csv"
FILLS_CSV    = PROJ_LOGS / "fills.csv"
DN_CARRY_CSV = PROJ_LOGS / "delta_neutral_carry.csv"
DN_LOG       = LOG_HOME  / "delta_neutral.log"

TSMOM_ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]
CORR_MIN_DAYS = 10   # minimum shared daily P&L points before reporting correlation


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s).astimezone(timezone.utc)

def _fmt(v: float, prefix: str = "$") -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{prefix}{v:.2f}" if prefix else f"{sign}{v:.2f}"

def _pct(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


# ─── TSMOM DATA ───────────────────────────────────────────────────────────────

def _tsmom_dir(action: str, prev: int) -> int:
    return {"OPEN_LONG": 1, "FLIP_TO_LONG": 1,
            "OPEN_SHORT": -1, "FLIP_TO_SHORT": -1,
            "CLOSE": 0, "HOLD": prev}.get(action, prev)


def load_tsmom_trades() -> dict[str, list[dict]]:
    """
    Return {symbol: [row, ...]} filtered to the cron window (hour 0 UTC).
    Each row has an added '_ts' key (datetime) and '_dir' key (position direction).
    Rows within one minute of each other on the same date are de-duplicated
    by keeping the EARLIEST (first actual cron execution, not reruns).
    """
    if not TSMOM_TRADES.exists():
        return {}

    raw: dict[str, list[dict]] = defaultdict(list)
    with open(TSMOM_TRADES) as f:
        for row in csv.DictReader(f):
            ts = _ts(row["timestamp"])
            if ts.hour != 0:   # ignore test/dev runs at other hours
                continue
            row["_ts"] = ts
            raw[row["symbol"]].append(row)

    # De-duplicate: keep one row per (symbol, date) — earliest in window
    result: dict[str, list[dict]] = {}
    for sym, rows in raw.items():
        seen: dict[date, dict] = {}
        for r in sorted(rows, key=lambda x: x["_ts"]):
            d = r["_ts"].date()
            if d not in seen:
                seen[d] = r
        ordered = sorted(seen.values(), key=lambda x: x["_ts"])
        # Reconstruct position direction
        direction = 0
        for r in ordered:
            direction = _tsmom_dir(r["action"], direction)
            r["_dir"] = direction
        result[sym] = ordered
    return result


def compute_tsmom_pnl(by_sym: dict[str, list[dict]]) -> dict:
    """
    Build per-symbol state and a daily P&L series (date → portfolio USD P&L).

    P&L for date D = sum over symbols of:
        prev_direction × prev_deploy_usd × (price_D − price_{D-1}) / price_{D-1}

    where price_D is the signal-computation price recorded at D's cron row.
    This is an approximation (yfinance T-2 lag), sufficient for daily monitoring.
    """
    now_utc = datetime.now(timezone.utc)
    today   = now_utc.date()
    month_start = today.replace(day=1)

    daily_pnl: dict[date, float] = defaultdict(float)
    fees_today = 0.0
    fees_mtd   = 0.0
    symbols: dict[str, dict] = {}

    for sym, rows in by_sym.items():
        for i in range(1, len(rows)):
            r_prev, r_curr = rows[i - 1], rows[i]
            d  = r_curr["_ts"].date()
            p0 = float(r_prev["price"])
            p1 = float(r_curr["price"])
            direction = r_prev["_dir"]
            deploy    = float(r_prev["deploy_usd"])
            if direction != 0 and p0 > 0:
                daily_pnl[d] += direction * deploy * (p1 - p0) / p0

        # Fees
        for r in rows:
            fee = float(r.get("fee_est", 0.0))
            d   = r["_ts"].date()
            if d == today:
                fees_today += fee
            if d >= month_start:
                fees_mtd += fee

        if rows:
            curr = rows[-1]
            prev = rows[-2] if len(rows) >= 2 else None
            symbols[sym] = {
                "price":           float(curr["price"]),
                "vol_scalar":      float(curr["vol_scalar"]),
                "prev_vol_scalar": float(prev["vol_scalar"]) if prev else None,
                "direction":       curr["_dir"],
                "deploy_usd":      float(curr["deploy_usd"]),
                "action":          curr["action"],
            }

    daily_total = daily_pnl.get(today, 0.0)
    mtd_total   = sum(v for d, v in daily_pnl.items() if d >= month_start)
    cum_total   = sum(daily_pnl.values())

    return {
        "symbols":    symbols,
        "daily_pnl":  dict(daily_pnl),   # date → float, used for correlation
        "daily_total": daily_total,
        "mtd_total":   mtd_total,
        "cum_total":   cum_total,
        "fees_today":  fees_today,
        "fees_mtd":    fees_mtd,
        "n_days":      len(daily_pnl),
    }


def load_fills() -> dict[str, dict]:
    """
    Return {symbol: latest_fill_row} with actual entry prices from fills.csv.
    Only considers BUY fills (position entries) from the current live session.
    """
    if not FILLS_CSV.exists():
        return {}
    entries: dict[str, dict] = {}
    with open(FILLS_CSV) as f:
        for row in csv.DictReader(f):
            if row.get("side") == "buy":
                entries[row["symbol"]] = row   # last buy per symbol
    return entries


# ─── DELTA NEUTRAL DATA ───────────────────────────────────────────────────────

def load_dn_carry() -> dict:
    """
    Parse delta_neutral_carry.csv (may not exist if no live DN positions yet).
    Returns carry totals for today and MTD.
    """
    if not DN_CARRY_CSV.exists():
        return {"today": 0.0, "mtd": 0.0, "by_asset": {}, "n_periods": 0,
                "daily_pnl": {}}

    now_utc = datetime.now(timezone.utc)
    today   = now_utc.date()
    month_start = today.replace(day=1)

    carry_today = 0.0
    carry_mtd   = 0.0
    n_periods   = 0
    by_asset: dict[str, float] = defaultdict(float)
    daily_pnl: dict[date, float] = defaultdict(float)

    with open(DN_CARRY_CSV) as f:
        for row in csv.DictReader(f):
            ts  = _ts(row["timestamp"])
            amt = float(row.get("carry_usd", 0.0))
            d   = ts.date()
            asset = row.get("asset", "?")
            by_asset[asset] += amt
            daily_pnl[d]    += amt
            if d == today:
                carry_today += amt
                n_periods   += 1
            if d >= month_start:
                carry_mtd   += amt

    return {
        "today":     carry_today,
        "mtd":       carry_mtd,
        "by_asset":  dict(by_asset),
        "n_periods": n_periods,
        "daily_pnl": dict(daily_pnl),
    }


def parse_dn_log() -> dict:
    """
    Parse the most recent run block from ~/logs/delta_neutral.log.
    Extracts: active_assets, mode, basis dict.
    Handles both old ("Active (carry > floor)") and new ("Active (vol + carry filters)") formats.
    """
    if not DN_LOG.exists():
        return {"active_assets": [], "mode": "UNKNOWN", "basis": {}}

    text = DN_LOG.read_text()

    # Find the last run header
    parts = re.split(r"={3} DELTA NEUTRAL \|", text)
    if len(parts) < 2:
        return {"active_assets": [], "mode": "UNKNOWN", "basis": {}}

    block = parts[-1]

    # Mode
    mode_m = re.match(r"\s*(\S[\S ]*?)\s*\|", block)
    mode = mode_m.group(1).strip() if mode_m else "UNKNOWN"

    # Active assets — handle both log formats
    active_m = re.search(
        r"Active \([^)]+\):\s*\[([^\]]*)\]", block
    )
    if active_m:
        raw = active_m.group(1)
        active_assets = [a.strip().strip("'\"") for a in raw.split(",") if a.strip()]
    else:
        active_assets = []

    # Basis per asset (live mode only, from "basis=X.XXX%" in log)
    basis: dict[str, float] = {}
    for m in re.finditer(r"\[(\w+)\].*?basis=([\d.]+)%", block):
        basis[m.group(1)] = float(m.group(2))

    return {"active_assets": active_assets, "mode": mode, "basis": basis}


# ─── CORRELATION ──────────────────────────────────────────────────────────────

def rolling_corr(
    tsmom_daily: dict[date, float],
    dn_daily:    dict[date, float],
    window: int = 30,
) -> float | None:
    """
    Compute rolling window correlation between TSMOM and DN daily P&L series.
    Returns None if there are fewer than CORR_MIN_DAYS shared observations.
    """
    shared = sorted(set(tsmom_daily) & set(dn_daily))
    if len(shared) < CORR_MIN_DAYS:
        return None

    shared = shared[-window:]   # last `window` common dates
    a = [tsmom_daily[d] for d in shared]
    b = [dn_daily[d]    for d in shared]

    n   = len(a)
    ma  = sum(a) / n
    mb  = sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b)) / n
    sa  = (sum((x - ma) ** 2 for x in a) / n) ** 0.5
    sb  = (sum((y - mb) ** 2 for y in b) / n) ** 0.5
    if sa == 0 or sb == 0:
        return None
    return cov / (sa * sb)


# ─── MESSAGE BUILDING ─────────────────────────────────────────────────────────

_DIRS = {1: "LONG", -1: "SHORT", 0: "FLAT"}
_SYM  = {"BTC-USD": "BTC", "ETH-USD": "ETH", "SOL-USD": "SOL"}


def _position_line(sym: str, info: dict, fills: dict[str, dict]) -> str:
    """Format one position line for the TSMOM block."""
    direction = _DIRS.get(info["direction"], "?")
    deploy    = info["deploy_usd"]
    ticker    = _SYM.get(sym, sym)
    fill      = fills.get(sym)
    if fill and info["direction"] != 0:
        actual_px = float(fill["actual_price"])
        signal_px = info["price"]
        slip_bps  = float(fill.get("slippage_bps", 0))
        return (f"  {ticker} {direction} ${deploy:.0f} "
                f"(entry {actual_px:.0f}, signal {signal_px:.0f}, slip {slip_bps:+.0f}bps)")
    if info["direction"] != 0:
        return f"  {ticker} {direction} ${deploy:.0f}"
    return f"  {ticker} FLAT"


def _vol_drift_line(by_sym: dict[str, dict]) -> str:
    """Format vol scalar drift summary."""
    parts = []
    for sym, info in by_sym.items():
        curr = info["vol_scalar"]
        prev = info["prev_vol_scalar"]
        ticker = _SYM.get(sym, sym)
        if prev is None:
            parts.append(f"{ticker} {curr:.2f} (no prior)")
        else:
            drift_pct = abs(curr - prev) / prev * 100 if prev else 0
            flag = " ⚠" if drift_pct > 10 else ""
            parts.append(f"{ticker} {prev:.2f}→{curr:.2f}{flag}")
    return "  Vol scalar: " + " | ".join(parts) if parts else ""


def build_message(
    report_date: date,
    tsmom:  dict,
    fills:  dict[str, dict],
    dn_carry: dict,
    dn_log:   dict,
) -> str:
    now_utc = datetime.now(timezone.utc)
    lines: list[str] = []
    lines.append(f"PORTFOLIO DAILY SUMMARY | {report_date}")
    lines.append("")

    # ── TSMOM ────────────────────────────────────────────────────────────────
    lines.append("TSMOM (Strategy A):")
    by_sym = tsmom["symbols"]
    if not by_sym:
        lines.append("  No data yet.")
    else:
        n_days = tsmom["n_days"]
        if n_days >= 1:
            daily_pct = (tsmom["daily_total"] / 499.0 * 100)
            lines.append(f"  Today approx: {_fmt(tsmom['daily_total'])} ({_pct(daily_pct)}) "
                         f"[{n_days}d data, yfinance T-2 lag]")
        else:
            lines.append("  Today: N/A (insufficient history)")
        lines.append(f"  MTD: {_fmt(tsmom['mtd_total'])} | "
                     f"Cumulative: {_fmt(tsmom['cum_total'])}")
        lines.append("  Positions:")
        for sym in TSMOM_ASSETS:
            if sym in by_sym:
                lines.append(_position_line(sym, by_sym[sym], fills))
        drift = _vol_drift_line(by_sym)
        if drift:
            lines.append(drift)

    lines.append("")

    # ── DELTA NEUTRAL ─────────────────────────────────────────────────────────
    lines.append("DELTA NEUTRAL (Strategy B):")
    mode = dn_log.get("mode", "UNKNOWN")
    active = dn_log.get("active_assets", [])
    basis  = dn_log.get("basis", {})

    if mode != "LIVE (TESTNET)" and mode != "LIVE":
        lines.append(f"  Mode: {mode} — no live positions")
    else:
        n_per = dn_carry["n_periods"]
        avg   = dn_carry["today"] / n_per if n_per else 0.0
        lines.append(f"  Carry earned today: {_fmt(dn_carry['today'])} "
                     f"({n_per} periods × avg {_fmt(avg)} per period)")
        lines.append(f"  Price P&L: approx $0.00 (delta-neutral)")

    if active:
        lines.append(f"  Active pairs: {' | '.join(active)}")
        if basis:
            basis_str = " | ".join(f"{a} {v:.2f}%" for a, v in basis.items())
            lines.append(f"  Basis: {basis_str}")
        else:
            lines.append("  Basis: n/a (dry-run)")
    else:
        lines.append("  Active pairs: none")

    lines.append("")

    # ── PORTFOLIO ─────────────────────────────────────────────────────────────
    lines.append("PORTFOLIO:")
    combined_today = tsmom["daily_total"] + dn_carry["today"]
    combined_mtd   = tsmom["mtd_total"]   + dn_carry["mtd"]
    total_fees_mtd = tsmom["fees_mtd"]

    lines.append(f"  Combined P&L today: {_fmt(combined_today)}")
    lines.append(f"  Combined MTD: {_fmt(combined_mtd)}")

    corr = rolling_corr(tsmom["daily_pnl"], dn_carry["daily_pnl"])
    if corr is None:
        lines.append(f"  Rolling 30d corr(A,B): N/A (<{CORR_MIN_DAYS} shared days)")
    else:
        flag = " ✓" if abs(corr) < 0.3 else " ⚠ (>0.3)"
        lines.append(f"  Rolling 30d corr(A,B): {corr:.2f}{flag}")

    lines.append(f"  Total fees paid MTD: {_fmt(total_fees_mtd)}")

    return "\n".join(lines)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main() -> None:
    now_utc     = datetime.now(timezone.utc)
    report_date = now_utc.date()

    by_sym   = load_tsmom_trades()
    tsmom    = compute_tsmom_pnl(by_sym)
    fills    = load_fills()
    dn_carry = load_dn_carry()
    dn_log   = parse_dn_log()

    msg = build_message(report_date, tsmom, fills, dn_carry, dn_log)
    print(msg)   # always print to stdout (for log file)
    notifier.send(msg, level="info")


if __name__ == "__main__":
    main()
