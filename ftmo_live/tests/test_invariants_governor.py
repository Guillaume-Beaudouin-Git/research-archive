"""Miroir des invariants EA == oracle sim (E._target_for_segment / E._quantize).

Le .mq5 porte lib/invariants.py 1:1 ; ces goldens prouvent miroir == moteur des
462 cohortes sur une grille d'états. Toute divergence = STOP (politique forkée).
"""
import numpy as np
import pandas as pd
import pytest

import engine as E
from lib import governor
from lib import invariants as inv

PX = np.array([3300.0, 145.0, 21500.0, 24000.0])
START = pd.Timestamp("2026-06-01")


@pytest.mark.parametrize("eq", [9050.0, 9500.0, 10000.0, 10400.0, 10900.0, 11500.0])
@pytest.mark.parametrize("days", [0, 7, 45, 90])
@pytest.mark.parametrize("phase", ["P1", "P2"])
def test_governor_scale_mirror_equals_sim_probe(eq, days, phase):
    cfg = governor.phase_cfg(phase)
    pos, avg = np.zeros(4), np.full(4, np.nan)
    today = START + pd.Timedelta(days=days)
    tgt, _ = governor._call(4, cfg, (1.0, 0.0), 0.0, eq, pos, avg, PX,
                            START, today, quantize=False, margin_cap=None)
    probe = tgt[0] / eq
    mirror = inv.governor_scale(
        eq, cfg["vm"], cfg["taper"], cfg["glide"], bool(cfg.get("pace")),
        days, cfg.get("max_cal"), cfg["target"], cfg.get("pace_k", 1.0))
    assert abs(probe - mirror) < 1e-12


def test_governor_funded_no_pace_no_glide():
    cfg = governor.phase_cfg("FUNDED")
    pos, avg = np.zeros(4), np.full(4, np.nan)
    eq = 10900.0  # prog>0.8 serait vrai en challenge
    tgt, _ = governor._call(4, cfg, (1.0, 0.0), 0.0, eq, pos, avg, PX,
                            START, START + pd.Timedelta(days=60),
                            quantize=False, margin_cap=None)
    assert abs(tgt[0] / eq - cfg["vm"] * inv.governor_taper(eq, cfg["taper"])) < 1e-12


@pytest.mark.parametrize("w", [(0.5, 1.4), (1.5, 1.5), (-1.0, 0.8)])
def test_margin_cap_proportional_mirror(w):
    cfg = governor.phase_cfg("P1")
    pos, avg = np.zeros(4), np.full(4, np.nan)
    eq = 10000.0
    raw, _ = governor._call(4, cfg, w, 1.0, eq, pos, avg, PX,
                            START, START, quantize=False, margin_cap=None)
    capped, _ = governor._call(4, cfg, w, 1.0, eq, pos, avg, PX,
                               START, START, quantize=False,
                               margin_cap=cfg["margin_cap"])
    # mrate explicite : depuis l'audit desk 2026-07-24, phase_cfg injecte le taux
    # SWING live (le compte réel) ; le miroir doit être interrogé au MÊME taux,
    # sinon on compare un cap Swing à un cap Standard (c'est ce décalage qui a
    # laissé le brain dimensionner 2x trop large sans qu'aucun test ne le voie).
    f = inv.margin_scale(raw, eq, cfg["margin_cap"], mrate=cfg["mrate"])
    assert np.allclose(np.asarray(capped), np.asarray(raw) * f, atol=1e-9)


CAPS_J1_12 = [None, 12.0, None, None]


@pytest.mark.parametrize("w", [(0.5, 1.4), (1.5, 1.5), (-1.0, 0.8)])
def test_leg_leverage_clip_mirror(w):
    """Miroir == oracle sim, ET dans le bon ORDRE (clip AVANT le cap marge).

    Si l'EA clippait après le cap marge et le sim avant, le reconcile produirait
    un Δ inexpliqué chaque nuit où le cap mord -> gate STOP 3j à tort.
    """
    cfg = dict(governor.phase_cfg("P1"), leg_lev_cap=CAPS_J1_12)
    pos, avg = np.zeros(4), np.full(4, np.nan)
    eq = 10000.0
    raw, _ = governor._call(4, dict(cfg, leg_lev_cap=None), w, 1.0, eq, pos, avg,
                            PX, START, START, quantize=False, margin_cap=None)
    capped, _ = governor._call(4, cfg, w, 1.0, eq, pos, avg, PX, START, START,
                               quantize=False, margin_cap=cfg["margin_cap"])
    clipped = inv.leg_leverage_clip(raw, eq, CAPS_J1_12)
    f = inv.margin_scale(clipped, eq, cfg["margin_cap"], mrate=cfg["mrate"])
    assert np.allclose(np.asarray(capped), np.asarray(clipped) * f, atol=1e-9)


def test_leg_leverage_clip_actually_bites():
    """Garde-fou : sans ceci les tests miroir passeraient sur un clip inopérant."""
    cfg = dict(governor.phase_cfg("P1"), leg_lev_cap=None)
    pos, avg = np.zeros(4), np.full(4, np.nan)
    eq = 10000.0
    raw, _ = governor._call(4, cfg, (1.5, 1.5), 1.0, eq, pos, avg, PX,
                            START, START, quantize=False, margin_cap=None)
    assert abs(raw[1]) > 12.0 * eq, "cas de test trop faible : le cap ne mord pas"
    clipped = inv.leg_leverage_clip(raw, eq, CAPS_J1_12)
    assert abs(clipped[1]) == pytest.approx(12.0 * eq, abs=1e-9)
    assert np.allclose(clipped[[0, 2, 3]], np.asarray(raw)[[0, 2, 3]])


@pytest.mark.parametrize("w", [(0.5, 1.4), (1.5, 1.5), (-1.0, 0.8)])
def test_leg_cap_noop_when_disabled(w):
    """Clé absente == leg_lev_cap None == chiffres pinnés v2.2, strictement.

    Écrit sans supposer ce que porte le yaml courant : c'est la NON-RÉGRESSION
    des 462 cohortes qui est testée, pas la valeur du cap du jour.
    """
    base = dict(governor.phase_cfg("P1"))
    without = {k: v for k, v in base.items() if k != "leg_lev_cap"}
    pos, avg = np.zeros(4), np.full(4, np.nan)
    eq = 10000.0
    args = dict(quantize=False, margin_cap=base["margin_cap"])
    t_absent, _ = governor._call(4, without, w, 1.0, eq, pos, avg, PX,
                                 START, START, **args)
    t_none, _ = governor._call(4, dict(base, leg_lev_cap=None), w, 1.0, eq, pos,
                               avg, PX, START, START, **args)
    assert np.allclose(np.asarray(t_absent), np.asarray(t_none), atol=0.0)


def test_leg_leverage_clip_edge_cases():
    caps = CAPS_J1_12
    assert np.allclose(inv.leg_leverage_clip([1.0, 9e9, 2.0, 3.0], 0.0, caps),
                       [1.0, 9e9, 2.0, 3.0]), "eq<=0 doit être un no-op fail-safe"
    assert np.allclose(inv.leg_leverage_clip([1.0, 9e9, 2.0, 3.0], 100.0, None),
                       [1.0, 9e9, 2.0, 3.0]), "caps None doit être un no-op"
    # symétrie : le cap borne la VALEUR ABSOLUE, short compris
    assert inv.leg_leverage_clip([0, -9e9, 0, 0], 1000.0, caps)[1] == -12000.0


@pytest.mark.parametrize("leg,price", [("XAUUSD", 3312.55), ("USDJPY", 144.831),
                                       ("US100", 21577.2), ("GER40", 24011.8)])
@pytest.mark.parametrize("notional", [-150000.0, -42137.5, 0.0, 137.0, 5000.0,
                                      42137.5, 151234.9])
def test_quantize_mirror_equals_sim(leg, price, notional):
    k = ["XAUUSD", "USDJPY", "US100", "GER40"].index(leg)
    t = np.zeros(4)
    t[k] = notional
    sim = E._quantize(t, np.full(4, price))[k]
    assert inv.quantize_sim_usd(notional, leg, price) == pytest.approx(sim, abs=1e-9)


def test_floors_and_breaker():
    assert inv.daily_floor(10000.0) == 9500.0
    assert inv.daily_floor(10400.0) == 9900.0
    assert inv.static_floor() == 9000.0
    assert inv.lim_eff(9300.0) == 9000.0          # daily 8800 < floor statique
    assert inv.breaker_line(10000.0, 0.30) == 9650.0
    assert inv.target_equity(0.10) == pytest.approx(11000.0 * (1 + E.EPS_T))


def test_breaker_is_daily_only_v24_remedy_A():
    """v2.4 (A) : le breaker suit le SEUL daily et se réarme chaque matin.

    Régression du cliquet : sous balance $9,500 l'ancienne formule
    max(daily, static) + 150 figeait la ligne à $9,150 quelle que soit l'ancre,
    et la room ne repoussait plus jamais (état absorbant, compte <ACCOUNT_ID>)."""
    # au-dessus de la bascule : daily contraignant, comportement inchangé
    assert inv.breaker_line(10000.0, 0.30) == 9650.0
    # sous la bascule : la ligne SUIT l'ancre au lieu de se figer à 9150
    assert inv.breaker_line(9239.84, 0.30) == pytest.approx(8889.84)
    assert inv.breaker_line(9100.0, 0.30) == pytest.approx(8750.0)
    # la ligne est strictement monotone en l'ancre — plus aucun palier
    lines = [inv.breaker_line(b, 0.30) for b in (9700, 9500, 9300, 9100, 9000)]
    assert all(a > b for a, b in zip(lines, lines[1:]))
    # et elle se réarme : room au breaker constante = 30% du budget, toujours
    for bal in (10000.0, 9500.0, 9239.84, 9050.0):
        assert bal - inv.breaker_line(bal, 0.30) == pytest.approx(350.0)


def test_breaker_corrupt_anchor_falls_back_to_static():
    """Ancre <= 0 (ea_state.json illisible) : sans garde la ligne serait à -350,
    donc le breaker DÉSARMÉ. On retombe sur le filet statique de l'ancienne
    formule au lieu de perdre la protection intraday."""
    assert inv.breaker_line(0.0, 0.30) == 9150.0
    assert inv.breaker_line(-1.0, 0.30) == 9150.0


def test_terminal_regime_detection_v24_remedy_C():
    """v2.4 (C) : détection seule, sans bande aveugle."""
    assert not inv.terminal_regime(10000.0)
    assert not inv.terminal_regime(9500.01)
    # à exactement static+budget, daily_floor == static_floor : les deux formules
    # de breaker coïncident, le cliquet n'a pas encore commencé -> pas terminal
    assert not inv.terminal_regime(9500.0)
    assert inv.breaker_line(9500.0, 0.30) == 9150.0     # = l'ancienne valeur
    assert inv.terminal_regime(9499.99)                 # premier pas sous la bascule
    # la bande aveugle de l'ancien seuil ($9,500 -> $9,200) est couverte :
    # <ACCOUNT_ID> à 9239.84 était terminal et non détecté
    assert inv.terminal_regime(9239.84)
    assert inv.terminal_regime(9050.0)


def test_tapers_two_bases():
    # gouverneur = base equity ; orb = base balance début de jour
    assert inv.governor_taper(9000.0, 0.02) == 0.0
    assert inv.governor_taper(9200.0, 0.02) == 1.0
    assert inv.governor_taper(9100.0, 0.02) == 0.5
    assert inv.orb_taper0(9000.0, 0.02) == 0.0
    assert inv.orb_taper0(9200.0, 0.02) == 1.0


def test_lots_helpers():
    one = inv.usd_per_lot(21500.0, 0.01, 0.01)     # US100: $1/pt/lot
    assert one == 21500.0
    assert inv.lots_from_usd(84000.0, one) == pytest.approx(3.91)
    assert inv.lots_from_usd(50.0, one) == 0.0
    assert inv.funded_orb_lots(25.0, 50.0, 1.0) == pytest.approx(0.5)
    assert inv.funded_orb_lots(25.0, 5000.0, 1.0) == 0.0   # < 1 step -> 0
    cap = inv.leg_lot_cap(10000.0, 14.0, 1.5, one)
    assert cap == pytest.approx(1.5 * 14.0 * 2.0 * 10000.0 / 21500.0)


def test_micro_arming_and_backstop_rules():
    assert inv.micro_armed(on_day=False, micro_enabled=True, opened_today=False)
    assert not inv.micro_armed(True, True, False)    # jour ON: jamais (605f4a4)
    assert not inv.micro_armed(False, True, True)
    assert not inv.micro_armed(False, False, False)
    t = inv.target_equity(0.10)
    assert inv.backstop_due(False, 2, 4, t + 1, t, False)
    assert not inv.backstop_due(True, 2, 4, t + 1, t, False)
    assert not inv.backstop_due(False, 4, 4, t + 1, t, False)
    assert not inv.backstop_due(False, 2, 4, t - 1, t, False)
    assert not inv.backstop_due(False, 2, 4, t + 1, t, True)


def test_targets_staleness_26h():
    gen = pd.Timestamp("2026-06-10 21:50:00")
    assert not inv.targets_stale(gen, gen + pd.Timedelta(hours=25.9))
    assert inv.targets_stale(gen, gen + pd.Timedelta(hours=26.1))


# ------------------------------------------------- LOT B : télémétrie live_truth
def test_governor_declares_mrate_source():
    """Le module qui CHOISIT la source doit la déclarer.

    Sans ça, le repli `getattr(E,"MRATE_SWING", littéral)` est indétectable en aval :
    un cleanroom VPS en retard ferait diverger le modèle SANS aucun signal
    (audit desk 2026-07-24 — « un fallback silencieux ne s'observe pas »).
    """
    cfg = governor.phase_cfg("P1")
    assert cfg["mrate_source"] == "engine.MRATE_SWING"
    assert len(cfg["mrate"]) == 4
    assert governor.phase_cfg("FUNDED")["mrate_source"] == "engine.MRATE_SWING"


def test_mrate_divergence_detects_leverage_change():
    """Confrontation modèle <-> broker : les deux moitiés existaient, personne ne
    les multipliait. Le scénario à attraper = FTMO change le levier de l'or."""
    import brain
    real = {"XAUUSD": {"margin_rate": 0.066667}, "USDJPY": {"margin_rate": 0.033335},
            "US100": {"margin_rate": 0.066667}, "GER40": {"margin_rate": 0.066670}}
    ok = brain._live_truth_audit("P1", real)
    assert ok["mrate_divergence_breach"] is False      # notre valeur est exacte
    assert ok["mrate_worst_rel_diff"] < 1e-3

    changed = dict(real, XAUUSD={"margin_rate": 0.111111})   # or 1:15 -> 1:9
    bad = brain._live_truth_audit("P1", changed)
    assert bad["mrate_divergence_breach"] is True
    assert abs(bad["mrate_worst_rel_diff"]) > 0.3


def test_mrate_audit_degrades_without_live_specs():
    """Dry-run / specs partielles : jamais de crash, jamais de faux breach."""
    import brain
    none = brain._live_truth_audit("P1", None)
    assert none["mrate_vs_live"] == "indisponible"
    assert none["mrate_divergence_breach"] is False
    partial = brain._live_truth_audit("P1", {"XAUUSD": {"margin_rate": None}})
    assert partial["mrate_vs_live"]["XAUUSD"] is None
    assert partial["mrate_divergence_breach"] is False


def test_legs_order_identical_across_modules():
    """L'appariement mr[i] <-> LEGS[i] n'est garanti que si les deux LEGS coïncident.

    Sans ça, une divergence de marge serait comparée à la mauvaise jambe EN SILENCE.
    L'audit a montré que le test de divergence ne le prouve PAS (les 3 jambes
    non-JPY partagent 0.066667, donc un échange XAUUSD<->US100 passe inaperçu) :
    c'est CE test qui porte la garantie.
    """
    import lib
    assert list(lib.LEGS) == list(E.LEGS) == ["XAUUSD", "USDJPY", "US100", "GER40"]
    assert len(E.MRATE_SWING) == len(E.LEGS)


def test_mrate_divergence_catches_non_jpy_leg():
    """Divergence sur US100 SEUL — le cas que le test précédent ne discriminait pas."""
    import brain
    real = {"XAUUSD": {"margin_rate": 0.066667}, "USDJPY": {"margin_rate": 0.033334},
            "US100": {"margin_rate": 0.066667}, "GER40": {"margin_rate": 0.066667}}
    bad = brain._live_truth_audit("P1", dict(real, US100={"margin_rate": 0.10}))
    assert bad["mrate_divergence_breach"] is True
    assert bad["mrate_vs_live"]["US100"]["rel_diff"] < -0.3
    assert bad["mrate_vs_live"]["XAUUSD"]["rel_diff"] == 0.0      # les autres intacts


def test_mrate_fallback_branch_declares_repli(monkeypatch):
    """Branche REPLI : c'est elle qui arme l'alerte `mrate_fallback`, elle doit être testée."""
    monkeypatch.delattr(E, "MRATE_SWING", raising=False)
    cfg = governor.phase_cfg("P1")
    assert cfg["mrate_source"].startswith("REPLI")
    assert cfg["mrate"] == [0.066667, 0.033334, 0.066667, 0.066667]   # valeur préservée


def test_worst_rel_diff_absent_does_not_crash_supervisor_format():
    """Specs broker indisponibles -> la clé est ABSENTE puis écrite `null` en aval.
    `get(k, 0)` ne protège PAS (la clé existe) : seul `or 0` évite le TypeError."""
    import brain
    out = brain._live_truth_audit("P1", None)
    assert "mrate_worst_rel_diff" not in out
    bs_lt = dict(mrate_worst_rel_diff=out.get("mrate_worst_rel_diff"))   # -> None
    assert float(bs_lt.get("mrate_worst_rel_diff") or 0) == 0.0
