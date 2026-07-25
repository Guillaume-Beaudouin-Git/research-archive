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


def test_mt5_mqh_copy_identical():
    """La copie que l'EA #include DOIT être celle qui est pinnée.

    verify_mqh_pin() hache v22/ea/spec_v22.mqh, mais l'EA compile avec
    ftmo_live/mt5/spec_v22.mqh (copie manuelle non scriptée, étape S4). Depuis
    v2.8 le mqh porte une LIMITE DE RISQUE (LEG_LEV_CAP_*) : une copie mt5/
    divergente mais gardant le bon SPEC_SHA256 compilerait et passerait
    SpecHashOK avec un cap de levier faux. 3 lignes ferment la classe entière.
    """
    from lib import LIVE_ROOT
    a = hashlib.sha256((EA_DIR / "spec_v22.mqh").read_bytes()).hexdigest()
    b = hashlib.sha256((LIVE_ROOT / "mt5" / "spec_v22.mqh").read_bytes()).hexdigest()
    assert a == b == PIN_MQH_SHA256
    assert ((EA_DIR / "spec_v22.sha256").read_text().strip()
            == (LIVE_ROOT / "mt5" / "spec_v22.sha256").read_text().strip())


def test_ea_clip_before_margin_cap():
    """L'EA doit clipper AVANT le cap marge — vérification STATIQUE.

    Le MQL5 n'est pas exécutable en CI : sans ce test, l'ordre d'application
    côté EA (le risque n°1 de l'overlay) n'est garanti que par un commentaire.
    Si l'EA clippait APRÈS le scaling proportionnel du cap marge, les cibles
    différeraient du sim à chaque nuit où le cap mord -> Δ reconcile inexpliqué
    et gate STOP 3j déclenché à tort. (Audit indépendant 2026-07-26.)
    """
    from lib import LIVE_ROOT
    src = (LIVE_ROOT / "mt5" / "book_executor.mq5").read_text()
    body = src.split("void CapQuantizeTrade(")[1].split("\nvoid ")[0]
    i_clip = body.index("LegLevCap(")
    i_need = body.index("MarginRateEff(")
    assert i_clip < i_need, "le clip de levier doit précéder le calcul du cap marge"
    flat = body.replace(" ", "").replace("\n", "")
    # Mutation-testé (2e audit) : sans ces deux littéraux, un clip MORT (tgt[k]
    # jamais affecté), un `>` inversé en `<`, un garde `lc>0` inversé ou un mauvais
    # index de jambe passaient tous le test.
    assert "lc>0&&MathAbs(tgt[k])>lc*eq" in flat, \
        "condition de clip absente ou altérée (garde lc>0, sens de la comparaison)"
    assert "tgt[k]=(tgt[k]>0?lc*eq:-lc*eq);" in flat, \
        "affectation du clip absente ou altérée (clip mort, ou signe non symétrique)"
    assert "doublelc=LegLevCap(k);" in flat, \
        "le cap doit être lu pour la jambe k (pas un index figé)"
    assert "if(eq>0)" in flat, "garde eq>0 absente (division/cap sur equity nulle)"
    # la jambe écrêtée doit être retaillée, sinon le clip est un calcul mort
    clip_block = body[i_clip - 200:i_need]
    assert "trade_mask[k]=true" in clip_block.replace(" ", "")


def test_pin_commits_consistent_and_yaml_pin_is_real():
    """P2 n'est vérifié par AUCUN garde-fou runtime (cf. README_BUILD) — ici.

    Deux copies indépendantes de PIN_COMMITS existent (v22/ea/brain.py et
    ftmo_live/lib/__init__.py) : elles doivent coïncider. Et le commit pinné
    doit RÉELLEMENT contenir le yaml dont on pin le sha, sinon la traçabilité
    du mqh (SPEC_PIN_YAML) est fausse en silence.
    """
    import subprocess
    from lib import PIN_COMMITS, REPO
    loader = spec.loader()
    for k in ("v22_contract", "v22_residuals", "v22_spec_yaml"):
        assert loader.PIN_COMMITS[k] == PIN_COMMITS[k], f"pin divergent: {k}"
    sha_pin = loader.PIN_SHA256
    blob = subprocess.run(
        ["git", "show", f"{PIN_COMMITS['v22_spec_yaml']}:"
         "data/ftmo_portfolio/v22/spec_v22.yaml"],
        cwd=REPO, capture_output=True)
    if blob.returncode != 0:
        # PAS un skip silencieux : ce cas se produit précisément après un
        # SQUASH-merge (le commit de gel disparaît), c'est-à-dire quand la
        # traçabilité SPEC_PIN_YAML devient fausse — le moment où il faut
        # alerter, pas se taire. Échec bruyant, sauf clone superficiel avéré.
        shallow = (REPO / ".git" / "shallow").exists()
        assert shallow, (
            f"PIN_COMMITS['v22_spec_yaml']={PIN_COMMITS['v22_spec_yaml'][:8]} "
            "est introuvable dans le dépôt (squash-merge ?) — SPEC_PIN_YAML "
            "embarqué dans le mqh ne trace plus rien. Re-pinner sur le commit réel.")
        pytest.skip("clone superficiel : commit pinné hors profondeur")
    assert hashlib.sha256(blob.stdout).hexdigest() == sha_pin, \
        "PIN_COMMITS['v22_spec_yaml'] ne contient pas le yaml pinné"


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
