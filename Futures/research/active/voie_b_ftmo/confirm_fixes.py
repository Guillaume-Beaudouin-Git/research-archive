"""
confirm_fixes.py — Python mirror of Voie_B_EA_fixed.mq5 critical logic.

Tests:
  A. DST core          — summer / winter session bounds
  B. DST transitions   — 2026-03-08 and 2026-11-01 (off-by-one edge cases)
  C. Kill-switch       — levered threshold computation
  D. Entry/exit timing — firing conditions mirroring OnTimer()
  E. Gap isolation     — frozen secondary instruments (tester artefact)
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta


# ─── Shared helpers (exact Python mirror of MQL5) ─────────────────────────────

def nth_sunday_mql5(year: int, month: int, n: int) -> int:
    """Mirror of MQL5 NthSunday(). Returns day-of-month of nth Sunday."""
    python_dow = datetime(year, month, 1).weekday()  # 0=Mon … 6=Sun
    mql_dow    = (python_dow + 1) % 7                # 0=Sun … 6=Sat
    first_sun  = 1 if mql_dow == 0 else 8 - mql_dow
    return first_sun + (n - 1) * 7


def get_et_offset_hours(utc_dt: datetime) -> int:
    """Mirror of MQL5 GetETOffsetHours(). Returns 4 (EDT) or 5 (EST)."""
    y = utc_dt.year
    edt_start = datetime(y, 3,  nth_sunday_mql5(y, 3, 2),  7, 0, tzinfo=timezone.utc)
    edt_end   = datetime(y, 11, nth_sunday_mql5(y, 11, 1), 6, 0, tzinfo=timezone.utc)
    aware = utc_dt if utc_dt.tzinfo else utc_dt.replace(tzinfo=timezone.utc)
    return 4 if edt_start <= aware < edt_end else 5


def get_session_bounds(utc_dt: datetime) -> tuple[int, int, int, int, int]:
    """Mirror of GetSessionBoundsUTC(). Returns (entry_h, entry_m, exit_h, exit_m, eod_h)."""
    off = get_et_offset_hours(utc_dt)
    return 9 + off, 31, 15 + off, 58, 16 + off


def entry_should_fire(utc_dt: datetime, entered: bool) -> bool:
    """Mirror of OnTimer() entry condition (block 2)."""
    if entered:
        return False
    eh, em, *_ = get_session_bounds(utc_dt)
    return utc_dt.hour == eh and utc_dt.minute >= em


def exit_should_fire(utc_dt: datetime, entered: bool) -> bool:
    """Mirror of OnTimer() exit condition (block 4)."""
    if not entered:
        return False
    _, _, xh, xm, _ = get_session_bounds(utc_dt)
    return utc_dt.hour == xh and utc_dt.minute >= xm


def kill_threshold(equity_at_entry: float, lev: float,
                   ks_unlev: float = -0.012) -> float:
    """Mirror of: g_levered_kill_threshold = equity*(1 + KillSwitchUnlev*lev)."""
    return equity_at_entry * (1.0 + ks_unlev * lev)


# ─── A. DST core ──────────────────────────────────────────────────────────────

def test_dst_core() -> bool:
    print("=" * 60)
    print("A. DST CORE — GetSessionBoundsUTC")
    print("=" * 60)
    cases = [
        ("ÉTÉ  2026-05-15 12:00 UTC (EDT)", datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
         4, (13, 31), (19, 58)),
        ("HIVER 2026-01-15 12:00 UTC (EST)", datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
         5, (14, 31), (20, 58)),
    ]
    ok = _run_session_cases(cases)
    print()
    return ok


# ─── B. DST transitions (off-by-one edge cases) ───────────────────────────────

def test_dst_transitions() -> bool:
    """
    2026-03-08: NthSunday(2026,3,2) must return 8 (not 15 — month starts on Sunday).
    2026-11-01: NthSunday(2026,11,1) must return 1 (not 8 — same edge).
    Test the boundary minute immediately before and after each switchover.
    """
    print("=" * 60)
    print("B. DST TRANSITIONS — 2026-03-08 and 2026-11-01 (off-by-one risk)")
    print("=" * 60)

    # Verify NthSunday values first
    mar8  = nth_sunday_mql5(2026, 3, 2)
    nov1  = nth_sunday_mql5(2026, 11, 1)
    edt_start = datetime(2026, 3,  mar8, 7, 0, tzinfo=timezone.utc)
    edt_end   = datetime(2026, 11, nov1, 6, 0, tzinfo=timezone.utc)

    ok_mar  = mar8 == 8
    ok_nov  = nov1 == 1
    print(f"  NthSunday(2026,3,2)  = {mar8}  (expected 8)  {'✅' if ok_mar else '❌'}")
    print(f"  NthSunday(2026,11,1) = {nov1}  (expected 1)  {'✅' if ok_nov else '❌'}")
    print(f"  EDT window: {edt_start.strftime('%Y-%m-%d %H:%M')} UTC"
          f" → {edt_end.strftime('%Y-%m-%d %H:%M')} UTC")
    print()

    # EDT switchover: 2026-03-08 07:00 UTC
    # one second before → EST ; at/after → EDT
    cases_mar = [
        ("2026-03-08 06:59 UTC (last EST minute)",
         datetime(2026, 3, 8, 6, 59, tzinfo=timezone.utc), 5, (14, 31), (20, 58)),
        ("2026-03-08 07:00 UTC (first EDT minute)",
         datetime(2026, 3, 8, 7,  0, tzinfo=timezone.utc), 4, (13, 31), (19, 58)),
        ("2026-03-08 08:00 UTC (solidly EDT)",
         datetime(2026, 3, 8, 8,  0, tzinfo=timezone.utc), 4, (13, 31), (19, 58)),
    ]
    # EDT→EST switchover: 2026-11-01 06:00 UTC
    cases_nov = [
        ("2026-11-01 05:59 UTC (last EDT minute)",
         datetime(2026, 11, 1, 5, 59, tzinfo=timezone.utc), 4, (13, 31), (19, 58)),
        ("2026-11-01 06:00 UTC (first EST minute)",
         datetime(2026, 11, 1, 6,  0, tzinfo=timezone.utc), 5, (14, 31), (20, 58)),
        ("2026-11-01 07:00 UTC (solidly EST)",
         datetime(2026, 11, 1, 7,  0, tzinfo=timezone.utc), 5, (14, 31), (20, 58)),
    ]

    ok_all  = ok_mar and ok_nov
    ok_all &= _run_session_cases(cases_mar)
    print()
    ok_all &= _run_session_cases(cases_nov)
    print()
    return ok_all


def _run_session_cases(cases) -> bool:
    all_ok = True
    for label, utc_dt, exp_off, exp_entry, exp_exit in cases:
        off = get_et_offset_hours(utc_dt)
        eh, em, xh, xm, _ = get_session_bounds(utc_dt)
        ok_off   = off == exp_off
        ok_entry = (eh, em) == exp_entry
        ok_exit  = (xh, xm) == exp_exit
        passed   = ok_off and ok_entry and ok_exit
        all_ok  &= passed
        mark = "✅" if passed else "❌"
        print(f"  {mark} {label}")
        if not passed:
            if not ok_off:   print(f"      offset : got {off}, expected {exp_off}")
            if not ok_entry: print(f"      entry  : got {eh:02d}:{em:02d}, expected {exp_entry[0]:02d}:{exp_entry[1]:02d}")
            if not ok_exit:  print(f"      exit   : got {xh:02d}:{xm:02d}, expected {exp_exit[0]:02d}:{exp_exit[1]:02d}")
    return all_ok


# ─── C. Kill-switch ───────────────────────────────────────────────────────────

def test_kill_switch() -> bool:
    """
    EA: g_levered_kill_threshold = equity_at_entry * (1 + KillSwitchUnlev * lev)
    KillSwitchUnlev = -0.012  (-1.2% unlevered = max allowed intraday unlevered loss)
    """
    print("=" * 60)
    print("C. KILL-SWITCH — levered threshold & firing logic")
    print("=" * 60)
    print("  EA code: g_levered_kill_threshold = equity*(1 + KillSwitchUnlev*lev)")
    print("           fires when: AccountInfoDouble(ACCOUNT_EQUITY) <= threshold")
    print()

    START = 100_000.0
    KS = -0.012

    threshold_cases = [
        # (label, lev, expected_threshold, expected_max_loss_usd, expected_max_loss_pct)
        ("lev=2.5 (BaseLev default)", 2.5, START * (1 + KS * 2.5)),
        ("lev=5.0 (MaxLev)",          5.0, START * (1 + KS * 5.0)),
    ]
    all_ok = True
    for label, lev, expected_thr in threshold_cases:
        got = kill_threshold(START, lev, KS)
        loss_pct = (got / START - 1) * 100
        passed = abs(got - expected_thr) < 0.01
        all_ok &= passed
        mark = "✅" if passed else "❌"
        print(f"  {mark} {label}")
        print(f"      threshold : {got:,.0f}  (expected {expected_thr:,.0f})")
        print(f"      max loss  : {loss_pct:.1f}%  ({got - START:,.0f} USD)")

    print()
    print("  Firing logic (lev=2.5, threshold=97 000):")
    thr = kill_threshold(START, 2.5, KS)
    fire_cases = [
        (97_001, False, "equity > threshold → no kill"),
        (97_000, True,  "equity = threshold → fires"),
        (96_500, True,  "equity < threshold → fires"),
    ]
    for eq, exp_fire, label in fire_cases:
        fires = eq <= thr
        ok = fires == exp_fire
        all_ok &= ok
        mark = "✅" if ok else "❌"
        print(f"    {mark} equity={eq:,}  kill_fires={fires}  ← {label}")
    print()
    return all_ok


# ─── D. Entry / exit firing ───────────────────────────────────────────────────

def test_entry_exit_timing() -> bool:
    """
    EA block 2: entry fires when dt.hour == eh AND dt.min >= em (09:31 ET)
    EA block 4: exit  fires when dt.hour == xh AND dt.min >= xm (15:58 ET)
    """
    print("=" * 60)
    print("D. ENTRY / EXIT TIMING — OnTimer() firing conditions")
    print("=" * 60)
    UTC = timezone.utc
    all_ok = True

    edt_cases = [
        # (label, utc_dt, already_entered, exp_entry_fire, exp_exit_fire)
        ("EDT 13:30 UTC — too early, not entered",
         datetime(2026, 5, 15, 13, 30, tzinfo=UTC), False, False, False),
        ("EDT 13:31 UTC — entry fires",
         datetime(2026, 5, 15, 13, 31, tzinfo=UTC), False, True,  False),
        ("EDT 13:45 UTC — already entered, no re-entry",
         datetime(2026, 5, 15, 13, 45, tzinfo=UTC), True,  False, False),
        ("EDT 19:57 UTC — too early for exit",
         datetime(2026, 5, 15, 19, 57, tzinfo=UTC), True,  False, False),
        ("EDT 19:58 UTC — exit fires",
         datetime(2026, 5, 15, 19, 58, tzinfo=UTC), True,  False, True),
        ("EST 14:30 UTC — too early, not entered",
         datetime(2026, 1, 15, 14, 30, tzinfo=UTC), False, False, False),
        ("EST 14:31 UTC — entry fires",
         datetime(2026, 1, 15, 14, 31, tzinfo=UTC), False, True,  False),
        ("EST 20:57 UTC — too early for exit",
         datetime(2026, 1, 15, 20, 57, tzinfo=UTC), True,  False, False),
        ("EST 20:58 UTC — exit fires",
         datetime(2026, 1, 15, 20, 58, tzinfo=UTC), True,  False, True),
    ]
    for label, utc_dt, entered, exp_entry, exp_exit in edt_cases:
        got_entry = entry_should_fire(utc_dt, entered)
        got_exit  = exit_should_fire(utc_dt, entered)
        ok = got_entry == exp_entry and got_exit == exp_exit
        all_ok &= ok
        mark = "✅" if ok else "❌"
        print(f"  {mark} {label}")
        if not ok:
            print(f"      entry: got {got_entry}, expected {exp_entry}")
            print(f"      exit:  got {got_exit},  expected {exp_exit}")
    print()
    return all_ok


# ─── E. Gap isolation (frozen secondaries) ────────────────────────────────────

def test_gap_isolation() -> bool:
    """
    In MT5 Strategy Tester, secondary symbols (US100/US30/US2000) may have
    no tick data → BID=0 → gaps[i]=0 → excluded from n_up/n_dn count.
    EA handles gracefully: if(prev<=0||cur<=0){gaps[i]=0;continue;}

    This test verifies that mono-symbol tester mode still fires correctly
    when only US500 (symbol 0) has valid data.
    """
    print("=" * 60)
    print("E. GAP ISOLATION — frozen secondaries in tester")
    print("=" * 60)
    print("  EA: if(prev<=0 || cur<=0) { gaps[i]=0; continue; }")
    print("  → frozen instruments contribute 0 to n_up/n_dn count")
    print()

    GAP_THR   = 15 / 10_000   # GapThresholdBps=15
    MIN_CONF  = 2              # MinConfirmation=2

    def determine_direction(prev_closes, cur_bids):
        gaps = []
        n_up = n_dn = 0
        for prev, cur in zip(prev_closes, cur_bids):
            if prev <= 0 or cur <= 0:
                gaps.append(0.0)
                continue
            g = (cur - prev) / prev
            gaps.append(g)
            if g >  GAP_THR: n_up += 1
            if g < -GAP_THR: n_dn += 1
        if n_up >= MIN_CONF: return +1, gaps
        if n_dn >= MIN_CONF: return -1, gaps
        return 0, gaps

    # Prices chosen so gap = +20bp on all valid instruments (> 15bp threshold)
    # US500≈5000, US100≈20000, US30≈40000, US2000≈2200; +20bp = ×1.0020

    # Scenario 1: all 4 valid, all gap +20bp → n_up=4 ≥ MinConf=2 → dir=+1
    prev  = [5000.0, 20000.0, 40000.0, 2200.0]
    cur   = [5010.0, 20040.0, 40080.0, 2204.4]  # each +20bp
    dir1, gaps1 = determine_direction(prev, cur)
    ok1 = dir1 == +1
    print(f"  {'✅' if ok1 else '❌'} 4/4 valid, all +20bp → dir={dir1} (expected +1)")
    print(f"      gaps(bp): {[round(g*1e4,1) for g in gaps1]}")

    # Scenario 2: US100/US30/US2000 frozen (BID=0), US500 alone gaps up
    # MinConfirmation=2 → dir=0 (only 1 valid instrument, n_up=1 < 2)
    prev2 = [5000.0, 0, 0, 0]
    cur2  = [5010.0, 0, 0, 0]
    dir2, gaps2 = determine_direction(prev2, cur2)
    ok2 = dir2 == 0
    print(f"  {'✅' if ok2 else '❌'} 1/4 valid (US500 only) → dir={dir2} (expected 0, need ≥{MIN_CONF} confirms)")
    print(f"      gaps(bp): {[round(g*1e4,1) for g in gaps2]}")

    # Scenario 3: US100/US30/US2000 frozen, US500 gaps down — same result
    prev3 = [5000.0, 0, 0, 0]
    cur3  = [4990.0, 0, 0, 0]   # -20bp
    dir3, gaps3 = determine_direction(prev3, cur3)
    ok3 = dir3 == 0
    print(f"  {'✅' if ok3 else '❌'} 1/4 valid (US500 -20bp) → dir={dir3} (expected 0)")

    # Scenario 4: exactly MinConfirmation=2 valid, both +20bp → n_up=2 ≥ 2 → dir=+1
    prev4 = [5000.0, 20000.0, 0, 0]
    cur4  = [5010.0, 20040.0, 0, 0]
    dir4, gaps4 = determine_direction(prev4, cur4)
    ok4 = dir4 == +1
    print(f"  {'✅' if ok4 else '❌'} 2/4 valid, both +20bp → dir={dir4} (expected +1)")

    print()
    print("  TESTER NOTE: si les 3 secondaires sont figés (gaps=0),")
    print("  MinConfirmation=2 bloque le signal. Le tester ne peut pas")
    print("  valider la logique multi-instruments — vérifiable uniquement")
    print("  en live (démo) où tous les flux de prix sont présents.")
    print()
    return ok1 and ok2 and ok3 and ok4


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    results = {
        "A — DST core":         test_dst_core(),
        "B — DST transitions":  test_dst_transitions(),
        "C — Kill-switch":      test_kill_switch(),
        "D — Entry/exit timing":test_entry_exit_timing(),
        "E — Gap isolation":    test_gap_isolation(),
    }

    print("=" * 60)
    print("RÉSULTAT GLOBAL")
    print("=" * 60)
    all_pass = True
    for label, passed in results.items():
        all_pass &= passed
        print(f"  {'✅' if passed else '❌'} {label}")
    print()
    if all_pass:
        print("✅ Tous les tests passent — mécanique EA confirmée.")
        print()
        print("PROCHAINES ÉTAPES:")
        print("  1. Déployer Voie_B_EA_fixed.mq5 sur VPS (Wine/MT5, compte démo FTMO)")
        print("     → voir vps_deploy.md pour les instructions")
        print("  2. Activer VerboseLog=true + log CSV activé dès J1")
        print("  3. Après 4-6 semaines de démo, lancer :")
        print("     python parity_check.py --mt5_csv <VoieB_decisions.csv>")
        print("     Gate : ≥95% direction, ≥90% sizing")
    else:
        print("❌ Des tests échouent — revoir l'EA avant déploiement.")


if __name__ == "__main__":
    main()
