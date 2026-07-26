"""Modèle de swap v2.2.1 = points MESURÉS datés (yaml measured_specs) x calendrier
triple PAR SYMBOLE, conversion prix-aware ; bornes de sanité live.

bps/nuit = pts x 10^-digits / prix x 1e4 (fx-free, validé 4/4 au centime nuit
10->11/06). $-modèle live = pts x tick_value x lots x mult (export EA, fx inclus).
Gate live (yaml live_gates): facturé vs modèle ±20% sinon STOP.
check_live_bounds(): specs live (pts, rollover3days, marge) vs ancres datées —
hors borne -> alerte (immunisation dérive dealer + écart Standard/Swing).
"""
from typing import Dict, List, Optional, Tuple

import pandas as pd

from . import LEGS
from . import spec as S

SWAP_DRIFT_STOP = 0.20
ABS_PTS_FLOOR = 2.0          # plancher du dénominateur relatif (petites ancres, ex JPY 0.96)


def _ms() -> dict:
    return S.measured_specs()


def night_multiplier(leg: str, date: pd.Timestamp) -> int:
    """x3 le triple_dow PAR SYMBOLE (XAU/JPY mercredi, indices vendredi)."""
    trip = int(_ms()["symbols"][leg]["triple_dow"])
    return 3 if pd.Timestamp(date).dayofweek == trip else 1


def swap_bps(leg: str, side: str, px: Optional[float] = None) -> float:
    """bps/nuit du notionnel aux prix courants (défaut: ref_px daté du yaml)."""
    m = _ms()["symbols"][leg]
    px = float(_ms()["ref_px"][leg]) if px is None else float(px)
    pts = float(m["swap_long_pts"] if side == "long" else m["swap_short_pts"])
    return pts * 10.0 ** (-int(m["digits"])) / px * 1e4


def anchor_bps(leg: str, side: str, px: Optional[float] = None) -> Tuple[float, bool]:
    """(bps/nuit, mesuré=True) — toutes jambes/sides mesurés depuis v2.2.1."""
    return swap_bps(leg, side, px), True


def forecast_night(positions_usd: Dict[str, float], date: pd.Timestamp,
                   px_map: Optional[Dict[str, float]] = None) -> dict:
    """{leg: {usd, bps, mult, measured}} + total — positions signées tenues la
    nuit de `date`. px_map (prix live state/export) affine la conversion bps."""
    out, total = {}, 0.0
    for leg in LEGS:
        pos = float(positions_usd.get(leg, 0.0))
        if pos == 0.0:
            continue
        side = "long" if pos > 0 else "short"
        px = (px_map or {}).get(leg)
        bps = swap_bps(leg, side, px)
        mult = night_multiplier(leg, date)
        usd = abs(pos) * bps / 1e4 * mult
        out[leg] = dict(usd=round(usd, 2), bps=round(bps, 4), mult=mult, measured=True)
        total += usd
    return dict(per_leg=out, total_usd=round(total, 2),
                date=str(pd.Timestamp(date).date()))


def billed_vs_model(billed_usd: Dict[str, float], modeled_usd: Dict[str, float]) -> dict:
    """Écarts par jambe + verdict gate ±20% (total, jambes modélisées)."""
    rows, tb, tm = {}, 0.0, 0.0
    for leg in sorted(set(billed_usd) | set(modeled_usd)):
        b = billed_usd.get(leg)
        m = modeled_usd.get(leg)
        drift = None
        if b is not None and m not in (None, 0.0):
            drift = b / m - 1.0
            tb += b
            tm += m
        rows[leg] = dict(billed=b, model=m,
                         drift_pct=None if drift is None else round(drift * 100, 1))
    tot = None if tm == 0.0 else tb / tm - 1.0
    return dict(per_leg=rows, total_billed=round(tb, 2), total_model=round(tm, 2),
                total_drift_pct=None if tot is None else round(tot * 100, 1),
                gate_breach=bool(tot is not None and abs(tot) > SWAP_DRIFT_STOP))


def check_live_bounds(live: Dict[str, dict]) -> List[str]:
    """Specs live vs ancres datées. live[leg] = {swap_long_pts, swap_short_pts,
    rollover3days_dow_py?, margin_rate?}. Retourne la liste des breaches.

    swap: |live-ancre|/max(|ancre|, ABS_PTS_FLOOR) > bounds_rel.swap
    triple: dow différent de l'ancre
    marge: hors ±bounds_rel.margin des ancres {standard_measured, swing_measured}
           — une seule dans la borne suffit. swing_official est VOLONTAIREMENT exclu
           (ses bornes se soudent à celles de la mesure : l'or à 1:9 passerait en
           silence) ; il reste le fallback conservateur de MarginRateEff côté EA.
    """
    ms = _ms()
    rel_sw = float(ms["bounds_rel"]["swap"])
    rel_mg = float(ms["bounds_rel"]["margin"])
    std = ms["margin_rates"]["standard_measured"]
    # v2.8 : 3e ancre = marge Swing MESURÉE sur le compte armé. Miroir exact du
    # test EA (book_executor.mq5::CheckLiveSpecBounds). Sans elle, la marge réelle
    # tombe hors des DEUX autres par construction (6.667% est exactement entre
    # Std 3.333% et Swing officiel 11.111%) -> breach permanent dans
    # audit["live_spec_bounds"] de chaque targets.json -> une vraie dérive de marge
    # y serait indiscernable du faux positif. `.get` : une spec antérieure à
    # v2.2.2 n'a pas le bloc. (Audit indépendant 2026-07-26.)
    meas = ms["margin_rates"].get("swing_measured") or {}
    # 2e audit 2026-07-26 : swing_official est RETIRÉ des ancres de sanité. À ±25%,
    # [swing_official] et [swing_measured] se SOUDENT pour XAUUSD
    # ([0.0500,0.0833] ∪ [0.0833,0.1389]) -> l'or passant à 1:9 (0.111111) serait
    # accepté EN SILENCE. Or c'est exactement le `headline_margin_swing` du yaml
    # (« LE TERME MATÉRIEL », Δp(pass) -15.6 pt, décision comité) : le seul
    # événement que ce canal doit attraper. swing_official GARDE son autre rôle,
    # distinct : fallback conservateur d'enforcement dans MarginRateEff (EA).
    refs = (std, meas)
    breaches = []
    for leg, lv in live.items():
        if leg not in ms["symbols"]:
            continue
        a = ms["symbols"][leg]
        for side, key in (("long", "swap_long_pts"), ("short", "swap_short_pts")):
            if key not in lv or lv[key] is None:
                continue
            anc, cur = float(a[key]), float(lv[key])
            rel = abs(cur - anc) / max(abs(anc), ABS_PTS_FLOOR)
            if rel > rel_sw:
                breaches.append(f"{leg} swap_{side} {cur:+.2f} pts vs ancre "
                                f"{anc:+.2f} ({rel:+.0%} > ±{rel_sw:.0%})")
        if lv.get("rollover3days_dow_py") is not None:
            if int(lv["rollover3days_dow_py"]) != int(a["triple_dow"]):
                breaches.append(f"{leg} triple dow {lv['rollover3days_dow_py']} "
                                f"vs ancre {a['triple_dow']}")
        mr = lv.get("margin_rate")
        if mr is not None and float(mr) > 0:
            mr = float(mr)
            ok = any(leg in ref and float(ref[leg]) > 0
                     and abs(mr - float(ref[leg])) / float(ref[leg]) <= rel_mg
                     for ref in refs)
            if not ok:
                breaches.append(f"{leg} marge {mr:.4f} hors bornes Standard "
                                f"{float(std[leg]):.4f}"
                                + (f"/Mesure {float(meas[leg]):.4f}"
                                   if leg in meas else "")
                                + f" ±{rel_mg:.0%}")
    return breaches
