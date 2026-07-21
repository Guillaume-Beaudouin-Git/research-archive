"""Miroir Python des invariants de book_executor.mq5 — UNE fonction par règle.

Rôle : (a) golden tests vs l'oracle sim (E._target_for_segment / E._quantize /
ledger V2+E7) prouvent miroir == sim ; (b) l'EA MQL5 porte ces fonctions 1:1
(revue ligne à ligne, burn-in réconcilié) ; (c) reconcile.py prédit avec elles.

Constantes de règles importées du cleanroom (E.INIT/FLOOR/DAILY_BUDGET/
MIN_OPEN_DAYS/EPS_T) et de la spec yaml — rien de local sauf V2_MIN_WIDTH_BPS,
spec-par-référence (yaml: « breakout ORB V2 canonique » → FTMO_CANONICAL_STATE.md
§1 : « filtre V2 = OR >= 10 bps », base = close de fin d'OR, sémantique vérifiée
sur le ledger nq_v2_trades 4013 trades).
"""
from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

import engine as E  # cleanroom

V2_MIN_WIDTH_BPS = 10.0
TARGETS_STALE_H = 26.0
PACE_MAX = 2.0

LOT_STEP = 0.01
_LEG_IDX = {"XAUUSD": 0, "USDJPY": 1, "US100": 2, "GER40": 3}


# ---------------------------------------------------------------- floors
def daily_floor(anchor_balance: float, initial: float = E.INIT) -> float:
    """equity >= balance@00:00 CE(S)T - 5% du capital initial (check M5)."""
    return anchor_balance - E.DAILY_BUDGET / E.INIT * initial


def static_floor(initial: float = E.INIT) -> float:
    return E.FLOOR / E.INIT * initial


def lim_eff(anchor_balance: float, initial: float = E.INIT) -> float:
    """Limite dure EFFECTIVE (condition de bust FTMO) : on breache si l'equity
    passe sous le daily OU sous le statique. Inchangé par v2.4 (A)."""
    return max(daily_floor(anchor_balance, initial), static_floor(initial))


def breaker_line(anchor_balance: float, breaker_frac: float,
                 initial: float = E.INIT) -> float:
    """Flatten M5 si equity < daily_floor + frac x budget daily (room < 30%).

    v2.4 remède (A) — le breaker protège le SEUL daily, plus le floor statique.
    Avant : lim_eff() = max(daily, statique). Sous balance = static + budget
    (10k : $9,500) le max() basculait sur le statique et la ligne se FIGEAIT
    ($9,150), alors que le buffer (0.30 x budget QUOTIDIEN) est dimensionné pour
    une barrière qui se réarme chaque matin. Cliquet unidirectionnel : la room ne
    repoussait jamais, le compte ne pouvait plus ni passer ni mourir (état
    absorbant, cf. AUDIT.md F5(b) « breaker-deadlock près du floor »).
    Le daily se réancre au rollover, donc la ligne se réarme toujours : le
    drawdown maximum redevient la mort naturelle qu'on laisse advenir.

    Garde état corrompu : une ancre <= 0 (ea_state.json illisible) donnerait une
    ligne négative = breaker DÉSARMÉ. L'ancien max() retombait implicitement sur
    le statique ; on restaure ce filet explicitement."""
    budget = E.DAILY_BUDGET / E.INIT * initial
    if anchor_balance <= 0.0:
        return static_floor(initial) + breaker_frac * budget
    return daily_floor(anchor_balance, initial) + breaker_frac * budget


def terminal_regime(anchor_balance: float, initial: float = E.INIT) -> bool:
    """v2.4 remède (C) — DÉTECTION SEULE, ne modifie aucun comportement.

    Vrai quand le floor statique est plus proche que le budget quotidien, i.e.
    anchor < static + budget (10k : $9,500) : le compte breachera le max loss
    AVANT de pouvoir breacher le daily. C'est le régime où la tentative est
    structurellement compromise (p(pass) mesurée 21% vs 47% à neuf).

    Remplace le déclencheur historique `eq < static + 2% x initial` ($9,200),
    qui laissait une bande aveugle de $300 : le compte <ACCOUNT_ID> est resté 14
    jours en régime terminal avec le compteur zombie à 0/5 et aucune alerte.

    JAMAIS de désarmement automatique : couper le trading ici détruirait
    l'option de résorption, qui est précisément ce que (A) rouvre."""
    return anchor_balance < static_floor(initial) + E.DAILY_BUDGET / E.INIT * initial


def target_equity(phase_target: float, initial: float = E.INIT) -> float:
    """Seuil de lock du pass intraday (sim: target x (1 + EPS_T))."""
    return initial * (1.0 + phase_target) * (1.0 + E.EPS_T)


# ---------------------------------------------------------------- governor
def governor_taper(eq: float, taper_frac: float, initial: float = E.INIT) -> float:
    """Taper du gouverneur (sizing 17:35/22:05) — base EQUITY (sim l.345-346)."""
    room = (eq - static_floor(initial)) / initial
    return float(np.clip(room / taper_frac, 0.0, 1.0))


def orb_taper0(bal: float, taper_frac: float, initial: float = E.INIT) -> float:
    """Taper du risk ORB/micro — base BALANCE début de jour (sim l.92)."""
    return float(np.clip((bal - static_floor(initial)) / initial / taper_frac, 0.0, 1.0))


def glide(eq: float, phase_target: float, glide_frac: float,
          initial: float = E.INIT) -> float:
    prog = (eq / initial - 1.0) / phase_target
    return glide_frac if prog > 0.8 else 1.0


def pace(days_elapsed: int, max_cal: int, eq: float, phase_target: float,
         pace_k: float, initial: float = E.INIT) -> float:
    frac_t = days_elapsed / max_cal
    prog = (eq / initial - 1.0) / phase_target
    return float(np.clip(1.0 + pace_k * (frac_t - max(prog, 0.0)), 0.8, PACE_MAX))


def governor_scale(eq: float, vm: float, taper_frac: float, glide_frac: float,
                   pace_on: bool, days_elapsed: int, max_cal: Optional[int],
                   phase_target: float, pace_k: float = 1.0,
                   initial: float = E.INIT) -> float:
    s = vm * governor_taper(eq, taper_frac, initial) \
        * glide(eq, phase_target, glide_frac, initial)
    if pace_on and max_cal:
        s *= pace(days_elapsed, max_cal, eq, phase_target, pace_k, initial)
    return s


def margin_scale(tgt_usd: Sequence[float], eq: float, cap: float,
                 mrate: Sequence[float] = E.MRATE) -> float:
    """Facteur de scaling proportionnel toutes jambes si besoin > cap x equity."""
    need = float(np.abs(np.asarray(tgt_usd)) @ np.asarray(mrate))
    if eq <= 0 or need <= cap * eq:
        return 1.0
    return cap * eq / need


# ---------------------------------------------------------------- lots
def quantize_sim_usd(tgt_usd: float, leg: str, price: float) -> float:
    """Grille du sim (E._quantize) : notional USD arrondi au pas 0.01 lot.
    USDJPY: pas = $1000 (base USD) ; autres: LOT_UNITS x prix x 0.01."""
    k = _LEG_IDX[leg]
    t = np.zeros(4)
    t[k] = tgt_usd
    px = np.full(4, price)
    return float(E._quantize(t, px)[k])


def usd_per_lot(price: float, tick_value: float, tick_size: float) -> float:
    """Valeur notionnelle USD d'1.0 lot, conversion devise incluse
    (= price x tick_value/tick_size ; GER40 EUR->USD automatique)."""
    return price * tick_value / tick_size


def lots_from_usd(notional_usd: float, one_lot_usd: float,
                  lot_step: float = LOT_STEP) -> float:
    if one_lot_usd <= 0:
        return 0.0
    return float(np.round(notional_usd / one_lot_usd / lot_step) * lot_step)


def leg_lot_cap(eq: float, vm: float, leg_cap_pre_vm: float,
                one_lot_usd: float) -> float:
    """Cap sanity |lots| par jambe = leg_cap_pre_vm x vm x pace_max x eq / $lot."""
    if one_lot_usd <= 0:
        return 0.0
    return leg_cap_pre_vm * vm * PACE_MAX * eq / one_lot_usd


# ---------------------------------------------------------------- micro-ORB (V2+E7)
def or_levels(highs: Sequence[float], lows: Sequence[float]) -> Tuple[float, float]:
    """(or_hi, or_lo) des barres M5 15:30-16:00 CET (6 barres)."""
    return float(np.max(highs)), float(np.min(lows))


def v2_width_ok(or_hi: float, or_lo: float, or_end_close: float,
                min_bps: float = V2_MIN_WIDTH_BPS) -> bool:
    """Filtre V2 : largeur OR >= min_bps, base close fin d'OR (sémantique ledger)."""
    if or_end_close <= 0 or or_hi <= or_lo:
        return False
    return (or_hi - or_lo) / or_end_close * 1e4 >= min_bps


def orb_break(highs: Sequence[float], lows: Sequence[float],
              or_hi: float, or_lo: float) -> Optional[dict]:
    """Premier bar post-OR cassant un niveau. Priorité LONG à barre ambiguë
    (sémantique builder: high testé avant low). None si aucun break."""
    for i in range(len(highs)):
        if highs[i] >= or_hi:
            return dict(direction=1, level=or_hi, stop=or_lo, bar=i)
        if lows[i] <= or_lo:
            return dict(direction=-1, level=or_lo, stop=or_hi, bar=i)
    return None


def e7_exit(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float],
            entry: float, stop: float, direction: int) -> dict:
    """Sorties V2+E7 sur le chemin post-entrée (barres M5, stop testé avant
    arming — ordre conservateur du builder) :
      stop = côté opposé OR (1R) ; trail-to-BE après +1R ; time-stop = close
      de la dernière barre (22:00 CET).
    Retourne exit_px, reason in {stop, be, time_stop}, be_armed."""
    R = abs(entry - stop)
    be_armed = False
    for j in range(len(highs)):
        cur_stop = entry if be_armed else stop
        if direction == 1:
            if lows[j] <= cur_stop:
                return dict(exit_px=cur_stop, reason="be" if be_armed else "stop",
                            be_armed=be_armed)
            if not be_armed and highs[j] >= entry + R:
                be_armed = True
        else:
            if highs[j] >= cur_stop:
                return dict(exit_px=cur_stop, reason="be" if be_armed else "stop",
                            be_armed=be_armed)
            if not be_armed and lows[j] <= entry - R:
                be_armed = True
    return dict(exit_px=float(closes[-1]), reason="time_stop", be_armed=be_armed)


def micro_risk_usd(or_range_pts: float, usd_per_point_per_lot: float,
                   lots: float) -> float:
    """risk$ du micro-ORB = lots x OR range pts x $/pt/lot (~$0.2-2.0)."""
    return lots * or_range_pts * usd_per_point_per_lot


def funded_orb_lots(risk_usd: float, or_range_pts: float,
                    usd_per_point_per_lot: float,
                    lot_step: float = LOT_STEP) -> float:
    """Lots funded = risk$ / (range x $/pt/lot), quantisés (0 si < 1 step)."""
    if or_range_pts <= 0 or usd_per_point_per_lot <= 0:
        return 0.0
    return float(np.floor(risk_usd / (or_range_pts * usd_per_point_per_lot)
                          / lot_step) * lot_step)


# ---------------------------------------------------------------- divers
def targets_stale(generated_at: pd.Timestamp, now: pd.Timestamp,
                  max_h: float = TARGETS_STALE_H) -> bool:
    return (pd.Timestamp(now) - pd.Timestamp(generated_at)).total_seconds() > max_h * 3600

def micro_armed(on_day: bool, micro_enabled: bool, opened_today: bool) -> bool:
    """Compteur de jours v2.2 : armé ssi micro ON, pas un jour ON (lun/mar — le
    GER40 17:35 marquera `opened`, sémantique 605f4a4) et rien d'ouvert ce jour."""
    return micro_enabled and not on_day and not opened_today


def backstop_due(opened_today: bool, open_days: int, min_days: int,
                 balance: float, target_eq: float, any_position: bool) -> bool:
    """Token open/close 0.01 lot — fallback RARE du yaml (50/13068 jours sim) :
    aucun trade ouvert ce jour ET min-days non atteint ET balance >= cible ET flat."""
    return (not opened_today and open_days < min_days
            and balance >= target_eq and not any_position)
