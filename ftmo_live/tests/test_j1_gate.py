"""Tests du gate de suspension J1 (lib/j1_gate.py) — hystérésis, causalité, fail-safe."""
import json

import numpy as np
import pandas as pd

from lib import j1_gate as JG


def _series(vals):
    return pd.Series(vals, index=pd.date_range("2024-01-01", periods=len(vals), freq="D"),
                     dtype=float)


def test_off_state_latch_and_resume():
    # latch at 161 (idx2); a 156 at idx12 resets the <=155 streak; resume after 10 consec <=155
    vals = [150, 159, 161, 162, 159, 157, 156, 155, 155, 155, 155, 155, 156,
            155, 155, 155, 155, 155, 155, 155, 155, 155, 154, 153, 150]
    off = JG._off_state(_series(vals), 160.0, 155.0, 10).astype(int).tolist()
    assert off[0] == 0 and off[1] == 0
    assert off[2] == 1                       # latch at 161
    assert all(o == 1 for o in off[2:22])    # stays OFF (156 at idx12 resets the counter)
    assert off[22] == 0                       # resume on the 10th consecutive <=155 (idx13..22)
    assert off[-1] == 0


def test_single_break_prevents_resume():
    # 9 closes <=155, then one 156, then 9 more -> never 10 consecutive -> stays OFF forever
    vals = [161] + [155] * 9 + [156] + [155] * 9
    off = JG._off_state(_series(vals), 160.0, 155.0, 10).astype(int).tolist()
    assert all(o == 1 for o in off)


def test_evaluate_in_zone(tmp_path):
    px = _series([150.0] * 250 + [161.0])
    pd.DataFrame({"USDJPY": px, "XAUUSD": px}).to_parquet(tmp_path / "panel_px.parquet")
    g = JG.evaluate(tmp_path)
    assert g["suspend"] is True and g["reason"] == "in_zone"
    assert g["level"] == 161.0 and g["source"] == "config"
    assert g["last_close_date"] == str(px.index[-1].date())   # causal: last available close


def test_evaluate_out_of_zone(tmp_path):
    px = _series([150.0] * 250)
    pd.DataFrame({"USDJPY": px}).to_parquet(tmp_path / "panel_px.parquet")
    g = JG.evaluate(tmp_path)
    assert g["suspend"] is False and g["reason"] == "out_of_zone"


def test_failsafe_config_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(JG, "CONFIG_PATH", tmp_path / "nope.json")
    cfg, src = JG._load_config()
    assert src == "default_failsafe" and cfg == JG.DEFAULTS


def test_failsafe_config_corrupt(monkeypatch, tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ not valid json")
    monkeypatch.setattr(JG, "CONFIG_PATH", p)
    _, src = JG._load_config()
    assert src == "default_failsafe"


def test_failsafe_bad_values(monkeypatch, tmp_path):
    # t_on >= t_off is invalid -> defaults (protection intact)
    p = tmp_path / "j.json"
    p.write_text(json.dumps({"enabled": True, "t_off": 155.0, "t_on": 160.0, "n_resume": 10}))
    monkeypatch.setattr(JG, "CONFIG_PATH", p)
    cfg, src = JG._load_config()
    assert src == "default_failsafe_bad_values" and cfg == JG.DEFAULTS


def test_disabled_opts_out(monkeypatch, tmp_path):
    p = tmp_path / "j.json"
    p.write_text(json.dumps({"enabled": False, "t_off": 160.0, "t_on": 155.0, "n_resume": 10}))
    monkeypatch.setattr(JG, "CONFIG_PATH", p)
    px = _series([150.0] * 250 + [161.0])
    pd.DataFrame({"USDJPY": px}).to_parquet(tmp_path / "panel_px.parquet")
    g = JG.evaluate(tmp_path)
    assert g["suspend"] is False and g["reason"] == "disabled"


def test_failclosed_no_data(tmp_path):
    # empty cache dir -> no panel_px -> fail CLOSED (suspend) so we never trade J1 blind
    g = JG.evaluate(tmp_path)
    assert g["suspend"] is True and g["reason"] == "failclosed_no_usdjpy_data"


def test_nan_close_ignored(tmp_path):
    px = _series([150.0] * 250 + [161.0, np.nan])   # last real close 161 (NaN dropped)
    pd.DataFrame({"USDJPY": px}).to_parquet(tmp_path / "panel_px.parquet")
    g = JG.evaluate(tmp_path)
    assert g["suspend"] is True and g["level"] == 161.0


def test_evaluate_never_raises_failclosed(tmp_path):
    # panel_px with a NON-datetime index -> the .date() call in _evaluate raises;
    # the public evaluate() must NOT propagate it and must fail CLOSED (audit B9 hardening).
    px = pd.Series([150.0] * 250 + [161.0], index=[f"r{i}" for i in range(251)])
    pd.DataFrame({"USDJPY": px}).to_parquet(tmp_path / "panel_px.parquet")
    g = JG.evaluate(tmp_path)                        # must not raise
    assert g["suspend"] is True and g["reason"] == "failclosed_exception"
