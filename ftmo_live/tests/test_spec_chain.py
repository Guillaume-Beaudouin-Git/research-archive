"""Chaîne de gel (ancres #19/#20) : pins yaml/mqh, rejet d'un yaml altéré,
round-trip byte-identique du générateur mqh."""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lib import EA_DIR, V22, PIN_MQH_SHA256
from lib import spec


def test_yaml_pin():
    sha = hashlib.sha256((V22 / "spec_v22.yaml").read_bytes()).hexdigest()
    assert sha == spec.loader().PIN_SHA256


def test_mqh_pin():
    spec.verify_mqh_pin()
    sha = hashlib.sha256((EA_DIR / "spec_v22.mqh").read_bytes()).hexdigest()
    assert sha == PIN_MQH_SHA256


def test_load_passes_and_drift_checked():
    s = spec.load()
    assert s["meta"]["version"] == "v2.2.2"               # v2.8: overlay leg_leverage_cap
    assert "v2.2" in s["meta"]["policy_version"]
    assert s["challenge"]["config"]["orb_risk"] == 0.0
    assert s["challenge"]["config"]["micro_orb"] is True
    assert s["funded"]["ORB_RT_BPS"]["value"] == "era"
    ms = s["measured_specs"]
    assert ms["read_date"] == "2026-06-10"
    assert ms["symbols"]["USDJPY"]["comm_side_usd_lot"] == 2.5
    assert ms["margin_rates"]["swing_official"]["XAUUSD"] == pytest.approx(1 / 9)
    # v2.8 : 3e ancre = marge Swing MESURÉE sur le compte armé. swing_official
    # (1:9) est conservé DOCUMENTAIRE + fallback conservateur d'enforcement ;
    # c'est celle-ci qui décrit le serveur réel (1:15 pour l'or).
    assert ms["margin_rates"]["swing_measured"]["XAUUSD"] == pytest.approx(0.066667)
    assert ms["margin_rates"]["swing_measured"]["read_date"] == "2026-07-24"


def test_leg_leverage_cap_overlay_frozen():
    """L'overlay est POLICY : il doit vivre dans le yaml gelé, hors challenge.config.

    Hors challenge.config est vital : le drift-check exige
    challenge.config == dict(C22.CFG_CHALLENGE) ; l'y placer casserait le gel v2.2.
    """
    s = spec.load()
    assert "leg_lev_cap" not in s["challenge"]["config"]
    ro = s["risk_overlays"]["leg_leverage_cap"]
    assert ro["enabled"] is True
    assert ro["order"] == "before_margin_cap"
    assert ro["caps"]["USDJPY"] == pytest.approx(12.0)
    assert ro["caps"]["XAUUSD"] is None
    assert spec.leg_lev_cap_vector(s, "challenge") == [None, 12.0, None, None]
    assert spec.leg_lev_cap_vector(s, "funded") == [None, 12.0, None, None]
    assert spec.leg_lev_cap_vector(s, "inexistant") is None


def test_altered_yaml_rejected(tmp_path):
    alt = tmp_path / "spec_v22.yaml"
    txt = (V22 / "spec_v22.yaml").read_text()
    alt.write_text(txt.replace("vm: 14.0", "vm: 13.0", 1))
    loader = spec.loader()
    with pytest.raises(loader.SpecError):
        loader.load(alt)


def test_truncated_yaml_rejected(tmp_path):
    alt = tmp_path / "spec_v22.yaml"
    alt.write_text((V22 / "spec_v22.yaml").read_text()[:-50])
    loader = spec.loader()
    with pytest.raises(loader.SpecError):
        loader.load(alt)


def test_mqh_generator_roundtrip(tmp_path):
    """make_spec_mqh.py régénéré dans une copie isolée -> mqh byte-identique."""
    work = tmp_path / "v22"
    (work / "ea").mkdir(parents=True)
    for f in ("spec_v22.yaml", "config_v22.py"):
        shutil.copy(V22 / f, work / f)
    for f in ("brain.py", "make_spec_mqh.py"):
        shutil.copy(EA_DIR / f, work / "ea" / f)
    r = subprocess.run([sys.executable, str(work / "ea" / "make_spec_mqh.py")],
                       capture_output=True, text=True, cwd=str(work / "ea"))
    assert r.returncode == 0, r.stderr
    sha = hashlib.sha256((work / "ea" / "spec_v22.mqh").read_bytes()).hexdigest()
    assert sha == PIN_MQH_SHA256, "générateur non byte-identique (ancre #20)"
    pin = (work / "ea" / "spec_v22.sha256").read_text().strip()
    assert pin == spec.loader().PIN_SHA256
