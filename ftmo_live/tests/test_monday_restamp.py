"""Tests monday_restamp — couvre _decide (toutes branches fail-safe) + _restamp.

Pur logique : _decide/_restamp prennent `now` en argument → pas de mock d'horloge.
Seul S.spec_sha256 est monkeypatché (sinon il chargerait le loader yaml/données).
Aucune écriture live. Voir MONDAY_RESTAMP_PREREG.md §10.

Amendement §0 : _restamp met AUSSI à zéro les 2 poids data-dépendants (ea_w_usdjpy fail-closed J1
2026-07-13 + ea_w_xauusd fail-closed or, option 2 2026-07-14). Les tests _restamp couvrent : les
deux zéros, la trace source_w_*/failclosed, l'idempotence quand les poids sont déjà 0, et la
préservation verbatim de ea_on_w (calendaire, levier du fix) + audit(.j1_gate).
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monday_restamp as MR  # noqa: E402

SHA = "56fbdde78a2e5c4365e8e0f5bbda06d3697a198beccbcbf2dd02deea0eb27928"
MON = datetime(2026, 6, 29, 13, 0, 0)   # lundi 13:00 Paris
TUE = datetime(2026, 6, 30, 13, 0, 0)   # mardi


def _targets(**over):
    t = {
        "schema": "ftmo_live.targets.v1",
        "ea_spec_sha256": SHA,
        "ea_generated_at_paris": "2026.06.26 21:50:03",   # vendredi
        "ea_valid_for_date": "2026-06-26",
        "ea_phase_hint": "P1",
        "ea_w_xauusd": 0.83,
        "ea_w_usdjpy": 1.5,
        "ea_on_day": 0,
        "ea_vm": 14.0,
        "ea_on_w": 0.6,
        # bloc audit réaliste : contient le sous-bloc j1_gate écrit par le brain (gate OFF vendredi)
        "audit": {"weights": {"XAUUSD": 0.83, "USDJPY": 1.5},
                  "j1_gate": {"suspend": False, "level": 158.42, "reason": "out_of_zone"}},
    }
    t.update(over)
    return t


@pytest.fixture(autouse=True)
def _patch_sha(monkeypatch):
    monkeypatch.setattr(MR.S, "spec_sha256", lambda: SHA)


# ---- happy path -------------------------------------------------------------
def test_happy_path_writes():
    do, reason = MR._decide(_targets(), MON, {"phase": "P1"})
    assert do is True
    assert "OK" in reason


# ---- garde-fous jour --------------------------------------------------------
def test_noop_not_monday():
    do, reason = MR._decide(_targets(), TUE, None)
    assert do is False and "pas lundi" in reason


# ---- garde-fous intégrité ---------------------------------------------------
def test_refuse_targets_absent():
    do, reason = MR._decide(None, MON, None)
    assert do is False and "absent" in reason


def test_refuse_bad_schema():
    do, reason = MR._decide(_targets(schema="autre.v9"), MON, None)
    assert do is False and "schema" in reason


def test_refuse_sha_mismatch():
    do, reason = MR._decide(_targets(ea_spec_sha256="deadbeef" * 8), MON, None)
    assert do is False and "spec_sha256" in reason


def test_refuse_phase_mismatch():
    do, reason = MR._decide(_targets(ea_phase_hint="P1"), MON, {"phase": "P2"})
    assert do is False and "phase" in reason


def test_phase_absent_in_state_ok():
    # state sans 'phase' → ne bloque pas (refus seulement sur mismatch explicite)
    do, _ = MR._decide(_targets(), MON, {"equity": 10000})
    assert do is True


# ---- garde-fous fraîcheur / source -----------------------------------------
def test_noop_already_fresh():
    do, reason = MR._decide(
        _targets(ea_generated_at_paris="2026.06.29 12:00:00"), MON, None)
    assert do is False and "fraîches" in reason


def test_refuse_source_too_old():
    do, reason = MR._decide(
        _targets(ea_valid_for_date="2026-06-19",
                 ea_generated_at_paris="2026.06.19 21:50:00"), MON, None)
    assert do is False and "valid_for_date" in reason


def test_refuse_source_future():
    do, reason = MR._decide(
        _targets(ea_valid_for_date="2026-06-30",
                 ea_generated_at_paris="2026.06.26 21:50:00"), MON, None)
    assert do is False and "valid_for_date" in reason


# ---- _restamp : ne touche que les champs §3 (3 + les 2 poids data) + bloc restamp -
def test_restamp_only_expected_fields_change():
    before = _targets()                       # or=0.83 ET J1=1.5 non nuls (gate vendredi OFF)
    after = MR._restamp(before, MON)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert changed == {"ea_generated_at_paris", "ea_valid_for_date", "ea_on_day",
                       "ea_w_usdjpy", "ea_w_xauusd", "restamp"}


def test_restamp_values():
    after = MR._restamp(_targets(), MON)
    assert after["ea_on_day"] == 1
    assert after["ea_valid_for_date"] == "2026-06-29"
    assert after["ea_generated_at_paris"] == "2026.06.29 13:00:00"
    assert after["restamp"]["source_generated_at"] == "2026.06.26 21:50:03"
    assert after["restamp"]["source_valid_for_date"] == "2026-06-26"
    assert after["restamp"]["restamp_ts"] == "2026.06.29 13:00:00"
    assert after["restamp"]["reason"] == MR.RESTAMP_REASON


# ---- _restamp : fail-closed data-poids (amendement §0 : J1 + or) ------------
def test_restamp_zeroes_both_data_weights_and_records_source():
    after = MR._restamp(_targets(ea_w_usdjpy=1.21, ea_w_xauusd=0.83), MON)
    assert after["ea_w_usdjpy"] == 0.0
    assert after["ea_w_xauusd"] == 0.0
    assert after["restamp"]["source_w_usdjpy"] == 1.21
    assert after["restamp"]["source_w_xauusd"] == 0.83
    assert after["restamp"]["failclosed"] is True


def test_restamp_preserves_onw_sha_mode_audit():
    # ea_on_w (poids calendaire US100/GER40, levier du fix) + sha/mode/audit copiés verbatim
    before = _targets()
    after = MR._restamp(before, MON)
    assert after["ea_on_w"] == 0.6                     # calendaire — JAMAIS touché (levier GER40)
    assert after["ea_spec_sha256"] == SHA
    assert after["ea_vm"] == 14.0
    assert after["schema"] == "ftmo_live.targets.v1"
    assert after["audit"] == before["audit"]           # bloc audit copié verbatim
    assert after["audit"]["j1_gate"]["suspend"] is False   # audit.j1_gate vendredi préservé


def test_restamp_data_weights_already_zero_idempotent():
    # brain gate/flat vendredi sur les deux (poids déjà 0) → les zéros ne créent pas de diff
    before = _targets(ea_w_usdjpy=0.0, ea_w_xauusd=0.0)
    after = MR._restamp(before, MON)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert changed == {"ea_generated_at_paris", "ea_valid_for_date", "ea_on_day", "restamp"}
    assert after["ea_w_usdjpy"] == 0.0 and after["ea_w_xauusd"] == 0.0
    assert after["restamp"]["source_w_usdjpy"] == 0.0
    assert after["restamp"]["source_w_xauusd"] == 0.0


def test_restamp_does_not_mutate_original():
    before = _targets()
    MR._restamp(before, MON)
    assert before["ea_on_day"] == 0
    assert before["ea_generated_at_paris"] == "2026.06.26 21:50:03"
    assert before["ea_w_usdjpy"] == 1.5               # zéro data-poids n'a pas muté l'original
    assert before["ea_w_xauusd"] == 0.83
    assert before["audit"]["weights"]["USDJPY"] == 1.5
    assert "restamp" not in before
