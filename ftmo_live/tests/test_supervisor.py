"""Alertes supervisor (conditions de la mission) + rapports non-crash."""
import pandas as pd
import pytest

import supervisor
from lib import statefiles


def _state(**kw):
    base = dict(schema="ftmo_live.state.v1",
                ts_paris=statefiles.fmt_ts(statefiles.now_paris().replace(tzinfo=None)),
                phase="P1", attempt_start="2026-06-08", equity=10000.0,
                balance=10000.0, anchor_balance=10000.0, daily_floor=9500.0,
                static_floor=9000.0, breaker_line=9650.0, room_daily_usd=500.0,
                target_equity=11002.2, breaker_fired_today=0, opened_today=1,
                flat_today=0, open_days=3, min_days=4, margin_used_pct_equity=22.0,
                micro_state=0, micro_enabled=1, micro_or_hi=0, micro_or_lo=0,
                micro_be=0, targets_age_h=1.0, targets_status="OK",
                mode_mismatch=0, kill=0, abandon_zombie_days=0,
                pending_unconfirmed=0, wd_due_usd=0, trading_days_since_wd=0,
                governor=dict(taper=1.0, glide=1.0, pace=1.05, scale=14.7, vm=14.0),
                symbol_specs={}, positions=[], last_error="")
    base.update(kw)
    return base


def _write_state(files_dir, st):
    statefiles.atomic_write_json(files_dir / "state.json", st)


def _brain_ok(runtime):
    statefiles.atomic_write_json(runtime / "brain_status.json", dict(
        status="OK", ts_paris=statefiles.fmt_ts(
            statefiles.now_paris().replace(tzinfo=None))))


def test_no_alerts_on_healthy_state(files_dir, runtime_isolated):
    _write_state(files_dir, _state())
    _brain_ok(runtime_isolated)
    fired = supervisor.evaluate_alerts(files_dir)
    assert fired == []


@pytest.mark.parametrize("mutation,expected", [
    (dict(breaker_fired_today=1), "breaker"),
    (dict(room_daily_usd=100.0), "room_daily"),
    (dict(margin_used_pct_equity=55.0), "margin"),
    (dict(last_error="OrderSend ret=10006"), "reject"),
    (dict(pending_unconfirmed=2), "pending"),
    (dict(kill=1), "kill"),
    (dict(mode_mismatch=1), "mode_mismatch"),
    (dict(abandon_zombie_days=5), "abandon"),
    (dict(wd_due_usd=350.0), "wd_due"),
])
def test_alert_conditions(files_dir, runtime_isolated, mutation, expected):
    _write_state(files_dir, _state(**mutation))
    _brain_ok(runtime_isolated)
    fired = supervisor.evaluate_alerts(files_dir)
    assert expected in fired


def test_heartbeat_lost(files_dir, runtime_isolated):
    _write_state(files_dir, _state(ts_paris="2026.06.11 10:00:00"))
    _brain_ok(runtime_isolated)
    now = statefiles.parse_ts("2026.06.11 10:05:00")
    assert "heartbeat" in supervisor.evaluate_alerts(files_dir, now=now)


def test_heartbeat_dormant_market_closed(files_dir, runtime_isolated):
    """State figé à la clôture vendredi, évalué samedi : silence structurel —
    pas d'alerte heartbeat hors session (et contenu évalué une seule fois)."""
    _write_state(files_dir, _state(ts_paris="2026.06.12 22:54:59"))
    statefiles.atomic_write_json(runtime_isolated / "brain_status.json",
                                 dict(status="OK", ts_paris="2026.06.13 09:00:00"))
    now = statefiles.parse_ts("2026.06.13 10:00:00")   # samedi 10:00 Paris
    fired = supervisor.evaluate_alerts(files_dir, now=now)
    assert "heartbeat" not in fired


def test_content_alerts_skip_on_stale_mtime(files_dir, runtime_isolated):
    """Contenu (kill, …) : tiré une fois sur state frais, skip silencieux tant
    que le mtime n'avance pas (même cooldown expiré), re-tiré après réécriture."""
    statefiles.atomic_write_json(runtime_isolated / "brain_status.json",
                                 dict(status="OK", ts_paris="2026.06.13 09:00:00"))
    _write_state(files_dir, _state(kill=1, ts_paris="2026.06.13 09:59:30"))
    t1 = statefiles.parse_ts("2026.06.13 10:00:00")    # samedi : session fermée
    assert "kill" in supervisor.evaluate_alerts(files_dir, now=t1)
    t2 = statefiles.parse_ts("2026.06.13 23:30:00")    # cooldown kill (12 h) expiré
    assert supervisor.evaluate_alerts(files_dir, now=t2) == []
    _write_state(files_dir, _state(kill=1, ts_paris="2026.06.13 09:59:30"))
    assert "kill" in supervisor.evaluate_alerts(files_dir, now=t2)


def test_brain_error_alert(files_dir, runtime_isolated):
    _write_state(files_dir, _state())
    statefiles.atomic_write_json(runtime_isolated / "brain_status.json", dict(
        status="ERROR", error="x", ts_paris=statefiles.fmt_ts(
            statefiles.now_paris().replace(tzinfo=None))))
    assert "brain" in supervisor.evaluate_alerts(files_dir)


def test_swap_drift_gate(files_dir, runtime_isolated):
    _write_state(files_dir, _state())
    _brain_ok(runtime_isolated)
    import csv
    with open(files_dir / "swaps_billed.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date_paris", "symbol", "lots_held", "notional_usd", "swap_usd"])
        # mercredi 2026-06-10, USDJPY long x3 : modèle = 100000*0.184e-4*3 = +5.52$
        w.writerow(["2026-06-10", "USDJPY", 1.0, 100000.0, 9.0])   # facturé +9 -> +63%
    fired = supervisor.evaluate_alerts(files_dir)
    assert "swap_drift" in fired
    d = supervisor.swap_drift_last_night(files_dir,
                                         statefiles.now_paris().replace(tzinfo=None))
    assert d["gate_breach"]


def test_reports_render(files_dir, runtime_isolated):
    st = _state(positions=[dict(leg="USDJPY", symbol="USDJPY", lots=1.41, dir=1,
                                avg=145.0, notional_usd=141000.0, swap_acc=0.55)])
    _write_state(files_dir, st)
    _brain_ok(runtime_isolated)
    now = statefiles.now_paris().replace(tzinfo=None)
    m = supervisor.build_morning(st, files_dir, now)
    e = supervisor.build_evening(st, files_dir, now)
    assert "FTMO P1" in m and "Rooms" in m and "Programme" in m
    assert "PnL jour" in e and "Campagne" in e and "Réconciliation" in e
    assert "State:" in m and "State:" in e   # âge du state (dormant si marché fermé)
