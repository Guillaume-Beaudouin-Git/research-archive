"""Protocole fichiers (schéma targets, atomicité, parse plat type-EA) + garde
anti-token-compromis de tg.py."""
import hashlib
import json
import re

import pandas as pd
import pytest

import tg
from lib import statefiles


def _mode_params():
    return dict(vm=14.0, on_w=0.6, orb_risk=0.0, micro_orb=True, breaker=0.30,
                taper=0.02, glide=0.5, pace=1, margin_cap=0.60)


def _targets():
    return statefiles.build_targets(
        spec_sha="a" * 64, valid_for=pd.Timestamp("2026-06-11"), phase_hint="P1",
        weights={"XAUUSD": 0.31234567, "USDJPY": 1.30123456}, on_day=False,
        mode_params=_mode_params(), audit={"nested": {"ea_decoy": 999}})


def test_targets_schema_flat_ea_keys():
    t = _targets()
    for k in ("ea_spec_sha256", "ea_generated_at_paris", "ea_valid_for_date",
              "ea_w_xauusd", "ea_w_usdjpy", "ea_on_day", "ea_vm", "ea_on_w",
              "ea_micro_orb", "ea_breaker", "ea_taper", "ea_glide",
              "ea_margin_cap", "ea_phase_hint"):
        assert k in t
        assert not isinstance(t[k], (dict, list))


def _ea_jkey(txt: str, key: str) -> str:
    """Mimique exacte de JKey() du .mq5 (recherche plate, coupe à , ou \\n)."""
    i = txt.find(f'"{key}"')
    if i < 0:
        return ""
    c = txt.find(":", i)
    e1, e2 = txt.find(",", c), txt.find("\n", c)
    e = e2 if e1 < 0 else (e1 if e2 < 0 else min(e1, e2))
    if e < 0:
        e = len(txt)
    return txt[c + 1:e].strip().replace('"', "")


def test_ea_flat_parser_compatibility(tmp_path):
    """Le parseur MQL5 (mimique) doit extraire les bons scalaires du JSON émis,
    y compris avec un blob audit imbriqué APRÈS les clés ea_*."""
    p = tmp_path / "targets.json"
    statefiles.atomic_write_json(p, _targets())
    txt = p.read_text()
    assert _ea_jkey(txt, "ea_spec_sha256") == "a" * 64
    assert float(_ea_jkey(txt, "ea_w_xauusd")) == pytest.approx(0.31234567)
    assert float(_ea_jkey(txt, "ea_w_usdjpy")) == pytest.approx(1.30123456)
    assert int(_ea_jkey(txt, "ea_on_day")) == 0
    assert float(_ea_jkey(txt, "ea_vm")) == 14.0
    assert int(_ea_jkey(txt, "ea_micro_orb")) == 1
    assert txt.index('"audit"') > txt.index('"ea_margin_cap"')   # ordre garanti


def test_atomic_write_and_age(tmp_path):
    p = tmp_path / "targets.json"
    statefiles.atomic_write_json(p, _targets())
    t = statefiles.read_json(p)
    assert t["schema"] == statefiles.TARGETS_SCHEMA
    age = statefiles.targets_age_h(t)
    assert 0 <= age < 0.1
    assert not list(tmp_path.glob(".tmp_*"))     # pas de résidu tmp


def test_csv_roundtrip(tmp_path):
    p = tmp_path / "fills.csv"
    row = dict(ts_server="x", ts_paris="2026.06.11 22:05:11", phase=1,
               reason="rebalance", symbol="XAUUSD", side="BUY", lots=0.13,
               req_price=3301.2, fill_price=3301.5, slip_bps=0.9,
               latency_ms=4000, magic=220500)
    statefiles.append_csv(p, statefiles.FILLS_COLUMNS, row)
    statefiles.append_csv(p, statefiles.FILLS_COLUMNS, row)
    df = pd.read_csv(p)
    assert len(df) == 2 and df["slip_bps"].iloc[0] == 0.9


def test_state_age(files_dir):
    st = dict(ts_paris="2026.06.11 10:00:00")
    assert statefiles.state_age_s(
        st, now=statefiles.parse_ts("2026.06.11 10:02:30")) == 150.0


# ---------------------------------------------------------------- tg guard
def test_tg_blocklist_refuses_compromised():
    dummy = "123456789:ABCDEFghijklmnopqrstuvwxyz01234567890"
    assert hashlib.sha256(dummy.encode()).hexdigest() in tg._blocklist()
    with pytest.raises(tg.TokenBlockedError):
        tg.check_token(dummy)


def test_tg_ok_token_passes():
    tg.check_token("999999999:fresh_token_not_blocklisted_123456")


def test_tg_disabled_prints(monkeypatch, capsys):
    monkeypatch.setenv("FTMO_LIVE_TG_DISABLED", "1")
    assert tg.send("hello") is True
    assert "hello" in capsys.readouterr().out
