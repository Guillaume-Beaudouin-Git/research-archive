"""Alertes supervisor (conditions de la mission) + rapports non-crash."""
import os
from datetime import timezone

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


def test_disarm_notice_not_reject_when_armed(files_dir, runtime_isolated):
    """MISSION 1 — last_error porte la notice de désarmement PÉRIMÉE mais kill==0
    (EA réarmé : l'EA ne vide pas g_last_error au réarmement). Pas de faux 'reject'
    toutes les ~60 min, et pas d'alerte 'kill' non plus (kill==0)."""
    _write_state(files_dir, _state(kill=0, last_error="kill-file FLAT — EA désarmé"))
    _brain_ok(runtime_isolated)
    fired = supervisor.evaluate_alerts(files_dir)
    assert "reject" not in fired
    assert "kill" not in fired


def test_disarm_notice_alerts_when_disarmed(files_dir, runtime_isolated):
    """kill==1 (réellement désarmé MAINTENANT) : l'alerte de désarmement (kill) tire."""
    _write_state(files_dir, _state(kill=1, last_error="kill-file FLAT — EA désarmé"))
    _brain_ok(runtime_isolated)
    fired = supervisor.evaluate_alerts(files_dir)
    assert "kill" in fired


def test_real_reject_not_masked_when_armed(files_dir, runtime_isolated):
    """Un vrai reject d'ordre (kill==0) ne doit JAMAIS être masqué par le garde."""
    _write_state(files_dir, _state(kill=0, last_error="OrderSend XAUUSD ret=10006 rejected"))
    _brain_ok(runtime_isolated)
    assert "reject" in supervisor.evaluate_alerts(files_dir)


def test_heartbeat_lost(files_dir, runtime_isolated, monkeypatch):
    """Heartbeat gelé en session ET lien broker rompu (terminal64 mort/socket absent)
    → alerte (vraie panne)."""
    monkeypatch.setattr(supervisor, "_mt5_connected", lambda *a, **k: False)
    _write_state(files_dir, _state(ts_paris="2026.06.11 10:00:00"))
    _brain_ok(runtime_isolated)
    now = statefiles.parse_ts("2026.06.11 10:05:00")
    assert "heartbeat" in supervisor.evaluate_alerts(files_dir, now=now)


def test_heartbeat_suppressed_when_connected(files_dir, runtime_isolated, monkeypatch):
    """JUMEAU du fix watchdog M1 — heartbeat gelé en session MAIS MT5 connecté au broker
    (gel de ticks au rollover serveur) → PAS d'alerte (élimine le faux « heartbeat perdu »
    chaque soir). La connectivité (socket courtier :443) tranche, pas l'âge seul."""
    monkeypatch.setattr(supervisor, "_mt5_connected", lambda *a, **k: True)
    _write_state(files_dir, _state(ts_paris="2026.06.11 10:00:00"))
    _brain_ok(runtime_isolated)
    now = statefiles.parse_ts("2026.06.11 10:05:00")
    assert "heartbeat" not in supervisor.evaluate_alerts(files_dir, now=now)


def test_heartbeat_dormant_market_closed(files_dir, runtime_isolated):
    """State figé à la clôture vendredi, évalué samedi : silence structurel —
    pas d'alerte heartbeat hors session (et contenu évalué une seule fois)."""
    _write_state(files_dir, _state(ts_paris="2026.06.12 22:54:59"))
    statefiles.atomic_write_json(runtime_isolated / "brain_status.json",
                                 dict(status="OK", ts_paris="2026.06.13 09:00:00"))
    now = statefiles.parse_ts("2026.06.13 10:00:00")   # samedi 10:00 Paris
    fired = supervisor.evaluate_alerts(files_dir, now=now)
    assert "heartbeat" not in fired


def test_heartbeat_not_masked_by_mtime_gate(files_dir, runtime_isolated, monkeypatch):
    """MISSION 4 — reproduit le week-end : EA mort, state.json FIGÉ (mtime n'avance
    plus) ET lien broker rompu. Le mtime-gate (anti-spam contenu) ne doit JAMAIS masquer
    l'alerte heartbeat en session ouverte. Heartbeat est évalué AVANT le gate."""
    monkeypatch.setattr(supervisor, "_mt5_connected", lambda *a, **k: False)
    _write_state(files_dir, _state(ts_paris="2026.06.11 09:50:00"))   # jeudi, gelé
    _brain_ok(runtime_isolated)
    now1 = statefiles.parse_ts("2026.06.11 10:00:00")                 # session ouverte
    assert "heartbeat" in supervisor.evaluate_alerts(files_dir, now=now1)
    # 2e passage SANS réécrire le state → mtime inchangé → gate contenu fermé.
    now2 = statefiles.parse_ts("2026.06.11 10:20:00")
    f2 = supervisor.evaluate_alerts(files_dir, now=now2)
    assert "heartbeat" in f2, "RÉGRESSION Mission 4 : heartbeat masqué par le mtime-gate"


def _set_watchdog(monkeypatch, path, age_s, now_paris):
    """Pose un fichier watchdog_alive d'âge `age_s` (relatif à now_paris) ou absent."""
    if age_s is None:
        monkeypatch.setattr(supervisor, "WATCHDOG_ALIVE", path)   # n'existe pas
        return
    path.write_text("beat")
    epoch = now_paris.replace(tzinfo=statefiles.PARIS).astimezone(timezone.utc).timestamp()
    os.utime(path, (epoch - age_s, epoch - age_s))
    monkeypatch.setattr(supervisor, "WATCHDOG_ALIVE", path)


def test_watchdog_dead_stale_in_session(files_dir, runtime_isolated, monkeypatch, tmp_path):
    """Méta-surveillance : heartbeat watchdog périmé (20 min) en session → alerte."""
    now = statefiles.parse_ts("2026.06.11 10:00:00")                  # jeudi, ouvert
    _write_state(files_dir, _state(ts_paris="2026.06.11 09:59:30"))   # EA frais
    _brain_ok(runtime_isolated)
    _set_watchdog(monkeypatch, tmp_path / "wa", 1200, now)
    assert "watchdog_dead" in supervisor.evaluate_alerts(files_dir, now=now)


def test_watchdog_dead_missing_in_session(files_dir, runtime_isolated, monkeypatch, tmp_path):
    """watchdog_alive absent = watchdog jamais lancé / cron muet → alerte en session."""
    now = statefiles.parse_ts("2026.06.11 10:00:00")
    _write_state(files_dir, _state(ts_paris="2026.06.11 09:59:30"))
    _brain_ok(runtime_isolated)
    _set_watchdog(monkeypatch, tmp_path / "absent_wa", None, now)
    assert "watchdog_dead" in supervisor.evaluate_alerts(files_dir, now=now)


def test_watchdog_alive_fresh_no_alert(files_dir, runtime_isolated, monkeypatch, tmp_path):
    now = statefiles.parse_ts("2026.06.11 10:00:00")
    _write_state(files_dir, _state(ts_paris="2026.06.11 09:59:30"))
    _brain_ok(runtime_isolated)
    _set_watchdog(monkeypatch, tmp_path / "wa", 60, now)              # 1 min : frais
    assert "watchdog_dead" not in supervisor.evaluate_alerts(files_dir, now=now)


def test_watchdog_dead_silent_out_of_session(files_dir, runtime_isolated, monkeypatch, tmp_path):
    """Hors session : même watchdog absent ne déclenche pas (no-op marché fermé)."""
    now = statefiles.parse_ts("2026.06.13 10:00:00")                  # samedi : fermé
    _write_state(files_dir, _state(ts_paris="2026.06.12 22:54:59"))
    _set_watchdog(monkeypatch, tmp_path / "absent_wa", None, now)
    assert "watchdog_dead" not in supervisor.evaluate_alerts(files_dir, now=now)


def test_flat_latched_alerts_when_armed(files_dir, runtime_isolated):
    """INCIDENT 2026-06-16 — FLAT retiré (kill=0) mais flat_today resté COLLÉ (verrou
    g_flat_today purgé seulement au rollover 00:00 Paris) → tous les créneaux du jour
    sautés en silence. Doit alerter en session."""
    now = statefiles.parse_ts("2026.06.11 10:00:00")                  # jeudi : ouvert
    _write_state(files_dir, _state(kill=0, flat_today=1, opened_today=0,
                                   breaker_fired_today=0, ts_paris="2026.06.11 09:59:30"))
    _brain_ok(runtime_isolated)
    assert "flat_latched" in supervisor.evaluate_alerts(files_dir, now=now)


def test_flat_latched_silent_when_opened(files_dir, runtime_isolated):
    """flat_today=1 APRÈS un trade (target-lock/EOD légitime, opened_today=1) : pas
    d'alerte verrou — ce n'est pas le bug du kill-flat collé."""
    now = statefiles.parse_ts("2026.06.11 10:00:00")
    _write_state(files_dir, _state(kill=0, flat_today=1, opened_today=1,
                                   ts_paris="2026.06.11 09:59:30"))
    _brain_ok(runtime_isolated)
    assert "flat_latched" not in supervisor.evaluate_alerts(files_dir, now=now)


def test_flat_latched_silent_when_killed(files_dir, runtime_isolated):
    """kill=1 (FLAT présent) : l'alerte 'kill' couvre déjà — pas de double 'flat_latched'."""
    now = statefiles.parse_ts("2026.06.11 10:00:00")
    _write_state(files_dir, _state(kill=1, flat_today=1, opened_today=0,
                                   ts_paris="2026.06.11 09:59:30"))
    _brain_ok(runtime_isolated)
    fired = supervisor.evaluate_alerts(files_dir, now=now)
    assert "flat_latched" not in fired
    assert "kill" in fired


def test_flat_latched_silent_out_of_session(files_dir, runtime_isolated):
    """Hors session : aucun créneau ne tirerait → silence (no-op marché fermé)."""
    now = statefiles.parse_ts("2026.06.13 10:00:00")                  # samedi : fermé
    _write_state(files_dir, _state(kill=0, flat_today=1, opened_today=0,
                                   ts_paris="2026.06.12 22:54:59"))
    assert "flat_latched" not in supervisor.evaluate_alerts(files_dir, now=now)


def test_flat_latched_not_masked_by_mtime_gate(files_dir, runtime_isolated):
    """Évalué AVANT le mtime-gate (comme heartbeat) : un state latché FIGÉ (mtime
    inchangé) re-tire au 2e passage — jamais masqué par l'anti-spam de contenu."""
    _write_state(files_dir, _state(kill=0, flat_today=1, opened_today=0,
                                   ts_paris="2026.06.11 09:59:30"))
    _brain_ok(runtime_isolated)
    now1 = statefiles.parse_ts("2026.06.11 10:00:00")
    assert "flat_latched" in supervisor.evaluate_alerts(files_dir, now=now1)
    now2 = statefiles.parse_ts("2026.06.11 10:20:00")                 # state non réécrit
    assert "flat_latched" in supervisor.evaluate_alerts(files_dir, now=now2), \
        "RÉGRESSION : flat_latched masqué par le mtime-gate"


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


# ---------------------------------------------------------------- livre MONO
def _targets(files_dir, date, w_xau, w_jpy, on_day=0):
    statefiles.atomic_write_json(
        files_dir / "targets.json",
        dict(ea_valid_for_date=date, ea_w_xauusd=w_xau, ea_w_usdjpy=w_jpy,
             ea_on_day=on_day))
    return files_dir


def test_book_engine_streak_counts_through_on_days(tmp_path, monkeypatch):
    """Le compteur MONO doit monter MALGRÉ les jours ON.

    Régression du trou d'observabilité 2026-07-24 : `ea_on_day` est CALENDAIRE
    (lun+mar). Le compter comme « du risque » remettrait la série à zéro chaque
    lundi et l'alerte ne partirait JAMAIS — c'est exactement ce qui a laissé
    ~38-60 séances de moteurs coupés passer inaperçues.
    """
    monkeypatch.setattr(supervisor, "BOOK_STATE", tmp_path / "book_state.json")
    for i, (d, on) in enumerate([("2026-07-20", 1), ("2026-07-21", 1),
                                 ("2026-07-22", 0)], start=1):
        r = supervisor.book_engine_streak(_targets(tmp_path, d, 0.0, 0.0, on))
        assert r["engines_on"] is False
        assert r["streak"] == i


def test_book_engine_streak_idempotent_and_resets(tmp_path, monkeypatch):
    monkeypatch.setattr(supervisor, "BOOK_STATE", tmp_path / "book_state.json")
    a = supervisor.book_engine_streak(_targets(tmp_path, "2026-07-22", 0.0, 0.0))
    b = supervisor.book_engine_streak(_targets(tmp_path, "2026-07-22", 0.0, 0.0))
    assert a["streak"] == b["streak"] == 1          # une seule fois par jour-brain
    c = supervisor.book_engine_streak(_targets(tmp_path, "2026-07-23", 1.5, 0.0))
    assert c["engines_on"] is True and c["streak"] == 0
    # J1 seul suffit à réarmer le livre
    d = supervisor.book_engine_streak(_targets(tmp_path, "2026-07-24", 0.0, -1.5))
    assert d["engines_on"] is True and d["streak"] == 0


def test_book_engine_line_and_missing_targets(tmp_path, monkeypatch):
    monkeypatch.setattr(supervisor, "BOOK_STATE", tmp_path / "book_state.json")
    line = supervisor._book_engine_line(_targets(tmp_path, "2026-07-22", 0.0, 0.0))
    assert "MONO" in line
    line = supervisor._book_engine_line(_targets(tmp_path, "2026-07-23", 1.5, 0.0))
    assert "ACTIF" in line
    (tmp_path / "targets.json").unlink()
    assert "illisibles" in supervisor._book_engine_line(tmp_path)   # jamais de crash


# ------------------------------------------------- escalade de l'alerte MONO
def test_book_idle_milestone_fires_only_at_thresholds():
    """L'alerte MONO ne doit partir qu'aux PALIERS.

    Régression du 2026-08-19 : l'ancienne condition `streak >= 5` a émis 19 alertes
    quotidiennes IDENTIQUES, toutes reçues, sans rien changer. Un message quotidien
    qui se répète cesse d'être lu ; la visibilité quotidienne appartient à la ligne
    passive du rapport, pas à une alerte.
    """
    f = supervisor._book_idle_milestone
    for n in supervisor.BOOK_IDLE_MILESTONES:            # paliers exacts
        assert f(n) == n
    for n in (1, 4, 6, 19, 21, 59, 61, 119, 121):        # entre les paliers: silence
        assert f(n) is None
    last = supervisor.BOOK_IDLE_MILESTONES[-1]
    assert f(last + supervisor.BOOK_IDLE_RECUR) == last + supervisor.BOOK_IDLE_RECUR
    assert f(last + supervisor.BOOK_IDLE_RECUR - 1) is None


def test_book_idle_milestone_never_skipped_by_monotonic_streak():
    """Le streak avance de +1 par jour-brain (supervisor.py:191) : aucun palier sautable.

    C'est ce qui rend l'escalade sûre — sinon un palier manqué serait manqué POUR
    TOUJOURS, ce qui serait pire que l'alerte quotidienne qu'elle remplace.
    """
    hits = [n for n in range(1, 301) if supervisor._book_idle_milestone(n) is not None]
    assert hits[:4] == list(supervisor.BOOK_IDLE_MILESTONES)
    assert 180 in hits and 240 in hits and 300 in hits    # rappels tous les 60


def test_book_idle_text_never_raises_on_broken_targets(tmp_path):
    """Une alerte ne doit JAMAIS casser la boucle qui l'émet.

    `_alert` est appelé depuis `evaluate_alerts` sans try/except : une exception ici
    tuerait toutes les alertes évaluées APRÈS elle. On teste donc des targets.json
    absents, vides, et à champs malformés — le message doit sortir dégradé, pas lever.
    """
    bk = dict(streak=42, engines_on=False, w_xau=0.0, w_jpy=0.0, on_day=False)
    # 1. fichier absent
    assert "LIVRE MONO depuis 42" in supervisor._book_idle_text(tmp_path, bk)
    # 2. audit vide
    statefiles.atomic_write_json(tmp_path / "targets.json", {"audit": {}})
    assert "LIVRE MONO" in supervisor._book_idle_text(tmp_path, bk)
    # 3. champs présents mais NON numériques (le cas qui lèverait ValueError)
    statefiles.atomic_write_json(tmp_path / "targets.json", {"audit": {
        "j1_gate": {"suspend": True, "reason": "in_zone", "level": "n/a",
                    "t_on": None, "n_resume": 10},
        "signals": {"j1_mom_12_1": "oops"}}})
    out = supervisor._book_idle_text(tmp_path, bk)
    assert "LIVRE MONO" in out and "J1" in out


def test_book_idle_text_carries_the_cause_when_data_is_there(tmp_path):
    """Le message doit dire POURQUOI et CE QUI RALLUMERAIT — sinon il n'appelle rien."""
    statefiles.atomic_write_json(tmp_path / "targets.json", {"audit": {
        "j1_gate": {"suspend": True, "reason": "in_zone", "level": 159.461,
                    "t_on": 155.0, "n_resume": 10},
        "signals": {"j1_mom_12_1": 0.10198}}})
    out = supervisor._book_idle_text(
        tmp_path, dict(streak=20, engines_on=False, w_xau=0.0, w_jpy=0.0, on_day=False))
    assert "159.46" in out and "155" in out and "+4.46" in out   # écart au seuil
    assert "LONG" in out                      # le signal veut être long: seul le gate tue
    assert "θ=0.34" in out and "sig" in out   # or: cause + aveu d'absence de diagnostic
