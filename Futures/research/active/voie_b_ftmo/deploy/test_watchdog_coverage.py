"""
test_watchdog_coverage.py — Verify */15 12-23 UTC covers all critical trading events.

Run: /usr/bin/python3 deploy/test_watchdog_coverage.py

No MT5 / VPS needed — pure arithmetic on cron schedule.
Pass iff every event shows gap < INTERVAL (15 min).
"""
from __future__ import annotations

INTERVAL     = 15   # cron interval in minutes
WINDOW_START = 12   # first fire: 12:00 UTC
WINDOW_END   = 23   # last fire:  23:45 UTC (*/15 at hour 23)

# (label, hour_utc, minute_utc, note)
EVENTS = [
    ("EDT entry",  13, 31, "09:31 ET summer  → fix DST confirmed"),
    ("EST entry",  14, 31, "09:31 ET winter"),
    ("EDT exit",   19, 58, "15:58 ET summer"),
    ("EST exit",   20, 58, "15:58 ET winter"),
    ("Forced EOD", 23,  0, "hard-coded 23:00 UTC reset"),
]


def gap_to_prev_fire(h: int, m: int) -> int | None:
    """
    Minutes since the last */INTERVAL fire at time h:m UTC within the cron window.
    Returns None if h:m falls outside [WINDOW_START, WINDOW_END].
    """
    if h < WINDOW_START or h > WINDOW_END:
        return None
    last_fire_m = (m // INTERVAL) * INTERVAL  # floor to :00, :15, :30, or :45
    return m - last_fire_m


def main() -> int:
    print("=" * 65)
    print(f"WATCHDOG COVERAGE  */15 {WINDOW_START}-{WINDOW_END} * * 1-5")
    print("=" * 65)

    all_pass = True
    for label, h, m, note in EVENTS:
        gap = gap_to_prev_fire(h, m)
        if gap is None:
            verdict = f"❌  OUTSIDE WINDOW [{WINDOW_START}:00-{WINDOW_END}:59 UTC]"
            all_pass = False
        elif gap < INTERVAL:
            verdict = f"✅  gap = {gap:2d} min  (prev fire {h:02d}:{(m//INTERVAL)*INTERVAL:02d} UTC)"
        else:
            # Should never happen with */15 — gap is always 0..14
            verdict = f"❌  gap = {gap:2d} min  (≥ {INTERVAL} min — BUG)"
            all_pass = False
        print(f"  {label:14s}  {h:02d}:{m:02d} UTC  {verdict}")
        print(f"  {'':14s}  {'':9s}  {note}")
        print()

    print("-" * 65)
    print("All fire times per weekday (first and last few):")
    fires = [f"{h:02d}:{m:02d}" for h in range(WINDOW_START, WINDOW_END + 1)
             for m in range(0, 60, INTERVAL)]
    for t in fires[:4]:
        print(f"  {t} UTC")
    print("  ...")
    for t in fires[-4:]:
        print(f"  {t} UTC")
    print(f"  Total: {len(fires)} fires/weekday × 5 days/week")
    print()
    result = "✅  ALL EVENTS COVERED — window 12:00-23:59 UTC is sufficient" if all_pass \
             else "❌  COVERAGE GAP — extend WINDOW_START or WINDOW_END"
    print(f"RESULT: {result}")
    print("=" * 65)

    # Instructions for the 48h dry-run on the VPS
    print("""
48h DRY-RUN SETUP (on the MT5 VPS, as mt5user):
  1. Copy watchdog.sh to ~/watchdog.sh
  2. crontab -e  →  add:
       */15 12-23 * * 1-5 ~/watchdog.sh --dry-run
  3. Wait 48h (covers Mon+Tue or any two trading days)
  4. Verify log contains DOWN entries near each critical time:
       grep "DOWN\\|UP" ~/watchdog.log | head -40
  5. Remove the dry-run crontab entry before adding the real one.
""")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
