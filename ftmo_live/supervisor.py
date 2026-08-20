#!/usr/bin/env python3
"""supervisor.py — heartbeat 60 s sur state.json + alertes + 2 rapports quotidiens.

Alertes temps réel (cooldown persisté runtime/alerts_state.json) :
  breaker déclenché | room daily < 1.5% init | marge > 50% | reject/ordre non
  confirmé | heartbeat > 3 min | écart swap facturé/modèle > 20% | kill-file |
  targets KO à 22:00+ | mode mismatch EA/spec | zombie >= 5 j | brain ERROR/stale.

Market-aware (2026-06-13) : le heartbeat EA est tick-dépendant (WriteState
throttle M1 sur TimeCurrent, mq5:1291) — il se tait STRUCTURELLEMENT marché
fermé. L'alerte heartbeat n'est évaluée qu'en session (lib/market_hours) ; les
alertes de CONTENU ne sont ré-évaluées que si state.json a un mtime postérieur
à la dernière évaluation (un state figé ne re-tire jamais en boucle).

Rapports (cron, --report) :
  08:30 Paris : jour J/phase/jours tradés, equity + % cible, rooms, PnL nuit +
    swaps facturés vs modèle, positions + marge/cap, breaker/pacing/taper,
    programme du jour (rebalance, micro-ORB armé, triple-day, jour ON).
  22:20 Paris : PnL jour, fills + slip, deltas de rebalance, coûts + swaps dus,
    % cible + compteur jours, Δ réconciliation x/3, fees campagne + budget.

Usage: supervisor.py --daemon | --report morning|evening | --add-fee N LABEL | --test-alert
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tg  # noqa: E402
from lib import LEGS, RUNTIME  # noqa: E402
from lib import invariants as inv  # noqa: E402
from lib import market_hours, spec, statefiles, swaps  # noqa: E402

HEARTBEAT_MAX_S = 180
# Méta-surveillance du watchdog MT5 : il réécrit ~/logs/watchdog_alive à chaque run
# (cron */3). Périmé > 10 min EN SESSION = garde inopérant → alerte (le superviseur
# surveille le gardien). Chemin partagé via env FTMO_WATCHDOG_ALIVE (idem watchdog).
WATCHDOG_ALIVE = Path(os.environ.get("FTMO_WATCHDOG_ALIVE",
                                     "/home/algo/logs/watchdog_alive"))
WATCHDOG_ALIVE_MAX_S = 600
ROOM_DAILY_ALERT_FRAC = 0.015
MARGIN_ALERT_PCT = 50.0
BRAIN_STALE_H = 25.0
CAMPAIGN_BUDGET_USD = 400.0   # yaml live_gates: « budget 4+ fees (~$400) »

BOOK_IDLE_MILESTONES = (5, 20, 60, 120)   # paliers d'alerte, en jours-brain
BOOK_IDLE_RECUR = 60                      # au-delà du dernier palier: rappel tous les 60

ALERTS_STATE = RUNTIME / "alerts_state.json"
BOOK_STATE = RUNTIME / "book_state.json"
SOD_DIR = RUNTIME / "sod"
SNAP_PATH = RUNTIME / "snapshots.json"
CAMPAIGN = RUNTIME / "campaign.json"


def _leg_of(symbol: str) -> Optional[str]:
    for l in LEGS:
        if str(symbol).startswith(l):
            return l
    return None


def _load(path: Path, default):
    out = statefiles.read_json(path)
    return out if out is not None else default


def _initial() -> float:
    return spec.account_size()


def _now_utc(now_paris_naive: datetime) -> datetime:
    return now_paris_naive.replace(tzinfo=statefiles.PARIS).astimezone(timezone.utc)


def _watchdog_stale(now: datetime) -> bool:
    """True si le heartbeat du watchdog MT5 (watchdog_alive) est absent ou périmé.

    `now` est Paris-naïf ; comparé au mtime (epoch UTC) du fichier réécrit à chaque
    run du cron */3. Absent = watchdog jamais lancé / cron muet → True.
    """
    try:
        mtime = WATCHDOG_ALIVE.stat().st_mtime
    except OSError:
        return True
    return (_now_utc(now).timestamp() - mtime) > WATCHDOG_ALIVE_MAX_S


def _state_freshness(state: dict, now: datetime) -> str:
    """Âge du state + contexte session (le heartbeat EA est tick-dépendant)."""
    age_s = statefiles.state_age_s(state, now)
    if not market_hours.fx_session_open(_now_utc(now)):
        return (f"State: vieux de {age_s / 3600.0:.1f} h — marché fermé "
                "(heartbeat dormant)")
    return f"State: âge {age_s:.0f} s"


def _mt5_connected(timeout: float = 5.0) -> bool:
    """True si MT5 est connecté au broker : process terminal64 vivant ET socket courtier
    :443 ÉTABLI. Mirror Python du watchdog M1 (watchdog_mt5.sh broker_socket_up/link_state).

    Gate l'alerte heartbeat : le gel de ticks au rollover serveur (~22:54→23:05 Paris) fige
    le heartbeat > HEARTBEAT_MAX_S ALORS QUE le socket courtier est vivant → ce N'EST PAS une
    panne → pas d'alerte (sinon faux « heartbeat perdu » chaque soir). Une vraie panne
    (terminal64 mort OU socket :443 absent) laisse passer l'alerte.

    Fail-safe : pgrep/ss indéterminés → False → l'alerte PASSE (jamais masquer une panne
    potentielle sur un doute d'outillage). Le motif '[t]erminal64' est immunisé (ne matche
    jamais pgrep lui-même ni le daemon supervisor).
    """
    try:
        pids = subprocess.run(["pgrep", "-f", "[t]erminal64"], capture_output=True,
                              text=True, timeout=timeout).stdout.split()
    except Exception:
        return False
    if not pids:
        return False                                  # terminal64 absent = panne
    try:
        ss = subprocess.run(["ss", "-tnp"], capture_output=True, text=True,
                            timeout=timeout).stdout
    except Exception:
        return False
    pidpat = re.compile(r"pid=(?:%s)[,)]" % "|".join(re.escape(p) for p in pids))
    for line in ss.splitlines():
        if not line.startswith("ESTAB") or not pidpat.search(line):
            continue
        cols = line.split()
        if len(cols) >= 5:
            peer = cols[4]
            if peer.endswith(":443") and not peer.startswith("127.") \
                    and not peer.startswith("[::1]"):
                return True
    return False


# ------------------------------------------------------------------ alertes
def _cooldown_ok(key: str, minutes: float, now: datetime) -> bool:
    st = _load(ALERTS_STATE, {})
    last = st.get(key)
    if last and (now - statefiles.parse_ts(last)).total_seconds() < minutes * 60:
        return False
    st[key] = statefiles.fmt_ts(now)
    statefiles.atomic_write_json(ALERTS_STATE, st)
    return True


def _alert(key: str, minutes: float, text: str, now: datetime) -> None:
    if _cooldown_ok(key, minutes, now):
        tg.send(f"🚨 FTMO live — {text}")


def book_engine_streak(files_dir: Path) -> Optional[dict]:
    """Les MOTEURS pilotés par signal (gold, J1) portent-ils du risque — et sinon, depuis
    combien de jours-brain ?

    Trou d'observabilité constaté le 2026-07-24 : w_xau = 0 pendant ~38-60 séances
    consécutives (or flat, vote 2-1 des lookbacks à |sig| 0.3333 vs seuil 0.34) ET J1
    suspendu par le gate depuis le 06/07 -> le livre DÉPLOYÉ était MONO (jambes ON
    lun/mar + micro-ORB compteur) alors que tous les p(pass) cités décrivent le livre
    COMPLET. Personne ne l'a vu : aucune alerte ni ligne de rapport ne posait la
    question « le livre porte-t-il du risque aujourd'hui ? ». Écart mesuré :
    p(campagne 91j) 82.5 % (complet) vs 53.7 % (MONO).

    On ne regarde QUE les poids data (gold/J1) : `ea_on_day` est CALENDAIRE (lun+mar),
    il remettrait la série à zéro chaque lundi et l'alerte ne partirait jamais.

    Compteur idempotent par JOUR-BRAIN (clé `ea_valid_for_date`) : le superviseur tourne
    plusieurs fois par jour, on ne compte qu'une fois par génération de targets.
    """
    t = statefiles.read_json(files_dir / "targets.json")
    if not t:
        return None
    day = str(t.get("ea_valid_for_date", "") or "")
    if not day:
        return None
    try:
        engines_on = (abs(float(t.get("ea_w_xauusd", 0.0))) > 0.0
                      or abs(float(t.get("ea_w_usdjpy", 0.0))) > 0.0)
    except (TypeError, ValueError):
        return None
    st = statefiles.read_json(BOOK_STATE) or {}
    if str(st.get("date", "")) != day:                     # nouveau jour-brain
        st = dict(date=day,
                  streak=0 if engines_on else int(st.get("streak", 0)) + 1)
        statefiles.atomic_write_json(BOOK_STATE, st)
    return dict(date=day, engines_on=engines_on, streak=int(st.get("streak", 0)),
                w_xau=float(t.get("ea_w_xauusd", 0.0)),
                w_jpy=float(t.get("ea_w_usdjpy", 0.0)),
                on_day=int(t.get("ea_on_day", 0)) == 1)


def _book_engine_line(files_dir: Path) -> str:
    """Ligne de rapport « le livre porte-t-il du risque ? » — visibilité PASSIVE.

    L'alerte (paliers BOOK_IDLE_MILESTONES) ne suffit pas : c'est de voir cette ligne
    chaque jour qui aurait fait remarquer les ~38-60 séances de moteurs coupés.
    """
    bk = book_engine_streak(files_dir)
    if bk is None:
        return "Moteurs: targets illisibles ⚠"
    onl = " + jambes ON (lun/mar)" if bk["on_day"] else ""
    if bk["engines_on"]:
        return (f"Moteurs: gold {bk['w_xau']:+.2f} | J1 {bk['w_jpy']:+.2f} ✓ "
                f"livre ACTIF{onl}")
    return (f"Moteurs: gold {bk['w_xau']:+.2f} | J1 {bk['w_jpy']:+.2f} — "
            f"⚠ LIVRE MONO depuis {bk['streak']} j{onl}")


def _book_idle_milestone(streak: int) -> Optional[int]:
    """Palier atteint EXACTEMENT à ce streak, sinon None.

    Constaté le 2026-08-19 : l'alerte `book_idle` avait été émise **19 jours de suite**
    (19 clés dans alerts_state.json), reçue chaque jour par l'opérateur, sans rien
    changer — les sleeves étaient éteintes depuis 88 et 101 séances et le livre a été
    diagnostiqué MONO par un audit, pas par l'alerte. Un message quotidien identique
    n'est plus une alerte, c'est du papier peint.

    On n'alerte donc qu'aux PALIERS (5, 20, 60, 120, puis tous les 60). La visibilité
    QUOTIDIENNE reste assurée par `_book_engine_line()` dans les deux rapports : c'est
    le bon endroit pour une répétition, parce qu'elle y est passive et contextualisée.
    """
    if streak in BOOK_IDLE_MILESTONES:
        return streak
    last = BOOK_IDLE_MILESTONES[-1]
    if streak > last and (streak - last) % BOOK_IDLE_RECUR == 0:
        return streak
    return None


def _num(v) -> Optional[float]:
    """float(v) ou None — JAMAIS d'exception.

    `_alert` est appelé depuis `evaluate_alerts` SANS try/except : une ValueError dans
    la construction d'un message tuerait toutes les alertes évaluées ensuite. Un champ
    d'audit malformé doit dégrader le texte, pas désarmer la surveillance.
    """
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _book_idle_text(files_dir: Path, bk: dict) -> str:
    """Message d'alerte ACTIONNABLE : pour chaque sleeve, la cause et ce qui la rallume.

    L'ancien texte citait p(campagne) et « le challenge en cours » — périmé depuis le
    passage en funded (2026-08-17). Et il ne disait pas POURQUOI chaque moteur est à
    zéro, donc il n'appelait aucune action.
    """
    t = statefiles.read_json(files_dir / "targets.json") or {}
    a = t.get("audit", {}) or {}
    g = a.get("j1_gate", {}) or {}
    s = a.get("signals", {}) or {}
    out = [f"LIVRE MONO depuis {bk['streak']} jours-brain — gold ET J1 à 0. Le livre ne "
           f"porte que les jambes ON (lun/mar) + l'ORB."]

    if g.get("suspend"):
        lvl, t_on, mom = _num(g.get("level")), _num(g.get("t_on")), _num(s.get("j1_mom_12_1"))
        msg = f"J1: gate '{g.get('reason', '?')}'"
        if lvl is not None and t_on is not None:
            msg += (f" à {lvl:.2f} — rouvre après {g.get('n_resume', '?')} clôtures "
                    f"≤ {t_on:.0f} (écart {lvl - t_on:+.2f})")
        if mom is not None:
            msg += (f". ⚠ momentum 12-1 = {mom:+.1%} : le SIGNAL est "
                    f"{'LONG' if mom > 0 else 'nul'}, seul le gate l'éteint")
        out.append(msg + ".")

    # Or : le deadband est la cause connue, mais aucune valeur de sig n'est publiée.
    out.append("Gold: deadband θ=0.34 sur la moyenne des signes {60,120,250} — comme "
               "|±1/3| = 0.333 < 0.34, l'UNANIMITÉ des 3 lookbacks est requise. ⚠ Aucun "
               "sig n'est exposé dans targets.json : cause non vérifiable depuis ici.")
    out.append("Conséquence: la diversification que suppose le sizing n'existe pas.")
    return " ".join(out)


def evaluate_alerts(files_dir: Path, now: Optional[datetime] = None) -> list:
    """Évalue toutes les conditions ; envoie (cooldown) ; retourne les clefs actives.

    Heartbeat : évalué seulement si la session forex est ouverte (hors session le
    silence est structurel — WriteState throttlé sur l'horloge des ticks).
    Alertes de contenu (tout ce qui relit state.json + brain + swaps) : évaluées
    seulement si state.json a un mtime postérieur à la dernière évaluation
    (_last_state_mtime dans alerts_state.json) — skip silencieux sinon.
    """
    now = now or statefiles.now_paris().replace(tzinfo=None)
    session_open = market_hours.fx_session_open(_now_utc(now))
    day = str(now.date())
    init = _initial()
    fired = []

    state = statefiles.read_state(files_dir)
    if state is None:
        fired.append("state_missing")
        _alert("state_missing", 15, "state.json ABSENT — EA down ?", now)
        return fired

    age = statefiles.state_age_s(state, now)
    # Connectivity-aware (jumeau du fix watchdog M1, MÊME cause racine) : un heartbeat gelé
    # en session N'est une panne QUE si le lien broker est rompu. Le gel de ticks au rollover
    # serveur (~22:54→23:05 Paris) fige le heartbeat > 180s ALORS QUE le socket courtier est
    # vivant → PAS d'alerte (élimine le faux « heartbeat perdu » chaque soir). `and` court-
    # circuité : _mt5_connected (subprocess) n'est appelé QUE si le heartbeat est déjà périmé.
    if session_open and age > HEARTBEAT_MAX_S and not _mt5_connected():
        fired.append("heartbeat")
        _alert("heartbeat", 15,
               f"heartbeat perdu {age:.0f}s > {HEARTBEAT_MAX_S}s ET lien broker rompu "
               "(terminal64 mort ou socket :443 absent) — MT5 down ?", now)

    # Méta-surveillance du gardien : évaluée AVANT le mtime-gate (comme heartbeat),
    # donc jamais masquée par un state figé. EA mort + watchdog mort = double panne.
    if session_open and _watchdog_stale(now):
        fired.append("watchdog_dead")
        _alert("watchdog_dead", 15,
               "WATCHDOG MT5 INOPÉRANT — heartbeat watchdog absent/périmé "
               f"(> {WATCHDOG_ALIVE_MAX_S}s) en session : MT5 sans filet de relance "
               "— vérifier le cron */3 (ftmo_watchdog) et run_with_env", now)

    # Armé-mais-flat-verrouillé : kill==0 (FLAT retiré) mais g_flat_today resté COLLÉ.
    # Le verrou n'est purgé QUE par DayRollover à 00:00 Paris (mq5:1107) ; retirer FLAT en
    # cours de journée ne le purge pas → tous les créneaux du jour court-circuitent en
    # silence (Do1735 `||g_flat_today`, Do2205 `if(g_flat_today)return`, mq5:992/1055).
    # opened_today==0 exclut le target-lock/EOD légitime (qui ouvre d'abord) ; breaker a son
    # alerte dédiée. Évalué AVANT le mtime-gate (comme heartbeat) : un state latché FIGÉ
    # alerte toujours. Trou d'observabilité du non-trade du 2026-06-16 (FLAT ré-apparu 02:09
    # Paris → verrou collé toute la journée armée). Voir RUNBOOK §Armement propre.
    if session_open and not int(state.get("kill", 0)) \
            and int(state.get("flat_today", 0)) \
            and not int(state.get("opened_today", 0)) \
            and not int(state.get("breaker_fired_today", 0)):
        fired.append("flat_latched")
        _alert("flat_latched", 60,
               "EA ARMÉ (kill=0) mais flat_today=1 COLLÉ — les créneaux du jour seront "
               "SAUTÉS (verrou g_flat_today non purgé jusqu'au rollover 00:00 Paris). "
               "Ré-armer proprement : voir RUNBOOK §Armement propre", now)

    try:
        mtime = (files_dir / "state.json").stat().st_mtime
    except OSError:
        return fired
    if mtime <= float(_load(ALERTS_STATE, {}).get("_last_state_mtime", 0.0)):
        return fired   # state inchangé (marché fermé / EA figé) : skip silencieux

    if int(state.get("breaker_fired_today", 0)):
        fired.append("breaker")
        _alert(f"breaker_{day}", 24 * 60,
               f"BREAKER déclenché — flatten M5, room daily épuisée "
               f"(equity ${state.get('equity', 0):,.0f})", now)
    room = float(state.get("room_daily_usd", 1e9))
    if room < ROOM_DAILY_ALERT_FRAC * init:
        fired.append("room_daily")
        _alert("room_daily", 30,
               f"room daily ${room:,.0f} < {ROOM_DAILY_ALERT_FRAC:.1%} init — "
               f"breaker à ${float(state.get('breaker_line', 0)):,.0f}", now)
    margin = float(state.get("margin_used_pct_equity", 0))
    if margin > MARGIN_ALERT_PCT:
        fired.append("margin")
        _alert("margin", 30, f"marge {margin:.0f}% > {MARGIN_ALERT_PCT:.0f}% equity", now)
    err = str(state.get("last_error", "") or "")
    # « kill-file FLAT — EA désarmé » (book_executor.mq5:1481) est une NOTICE de
    # désarmement, pas un reject d'ordre : l'EA ne vide PAS g_last_error au réarmement
    # (mq5:1487 remet g_killed=false sans toucher g_last_error) → champ « dernière erreur
    # connue », pas « erreur courante ». Réarmé (kill==0), cette notice est PÉRIMÉE : ne
    # pas la crier, sinon faux positif toutes les ~60 min. L'état désarmé COURANT est déjà
    # signalé par l'alerte `kill` (kill==1). Les vrais rejects (OrderSend/stop/fill/BREAKER
    # /pendings…) ne contiennent pas « kill-file FLAT » → passent toujours, kill==0 ou non.
    disarm_notice = "kill-file FLAT" in err
    if err and not (disarm_notice and not int(state.get("kill", 0))):
        fired.append("reject")
        # hashlib et non hash() : `hash()` de str est randomisé par PYTHONHASHSEED,
        # donc une clé neuve à chaque redémarrage du daemon -> le cooldown ne tenait
        # pas et alerts_state.json accumulait des clés orphelines (15/67 mesurées).
        _alert("reject_" + hashlib.sha1(err.encode()).hexdigest()[:8], 60,
               f"EA erreur/reject: {err}", now)
    if int(state.get("pending_unconfirmed", 0)) > 0:
        fired.append("pending")
        _alert("pending", 15,
               f"{state['pending_unconfirmed']} ordre(s) non confirmé(s) "
               f"(latence serveur 2-19 s dépassée)", now)
    if int(state.get("kill", 0)):
        fired.append("kill")
        _alert(f"kill_{day}", 12 * 60, "kill-file FLAT actif — EA désarmé", now)
    if int(state.get("mode_mismatch", 0)):
        fired.append("mode_mismatch")
        _alert("mode_mismatch", 60,
               "MODE MISMATCH targets.json vs spec_v22.mqh/InpPhase — vérifier", now)
    if now.hour >= 22 and str(state.get("targets_status", "OK")) != "OK":
        fired.append("targets")
        _alert(f"targets_{day}", 60,
               f"targets.json {state.get('targets_status')} au rebalance — "
               "gestion seule, aucun risque nouveau", now)
    if int(state.get("abandon_zombie_days", 0)) >= 5:
        fired.append("abandon")
        _alert(f"abandon_{day}", 24 * 60,
               "ABANDON sim atteint (5 j EOD < floor+2%) — décision humaine: "
               "relancer la tentative (règle v2.2)", now)
    wd = float(state.get("wd_due_usd", 0))
    if wd > 0:
        fired.append("wd_due")
        _alert(f"wd_{day}", 24 * 60,
               f"FUNDED: retrait dû ${wd:,.0f} (wd14) — demander le payout", now)
    if int(state.get("spec_bounds_breach", 0)):
        fired.append("spec_bounds")
        # Clé de cooldown = hash de la SIGNATURE du breach (quelles jambes, quelle
        # nature), PAS des valeurs. Deux pièges, tous deux mesurés :
        #  - `hash()` de Python n'est pas stable entre processus (PYTHONHASHSEED) ->
        #    hashlib, sinon une clé neuve à chaque redémarrage du daemon.
        #  - le détail embarque les swaps live à 2 décimales : 17 chaînes distinctes
        #    en 25 jours alors que l'ENSEMBLE des breaches est stable. Hasher le détail
        #    brut contournerait le cooldown par construction = 1 alerte par jour ouvré
        #    À VIE sur une condition permanente et connue (marge XAU 6.667% hors des
        #    ±25% de deux ancres yaml périmées). Ce serait AGGRAVER la fatigue d'alerte
        #    — celle-là même qui a coûté 38-60 séances de « LIVRE MONO » non vues.
        # On neutralise donc les nombres : seule l'apparition d'une jambe ou d'une
        # nature INÉDITE re-alerte.
        detail = str(state.get("spec_bounds_detail", ""))
        sig = re.sub(r"[-+0-9.]+", "#", detail)
        _alert("spec_bounds_" + hashlib.sha1(sig.encode()).hexdigest()[:8], 12 * 60,
               "SPECS LIVE HORS BORNES datées (swap/triple/marge) — dérive "
               f"dealer ou écart Standard/Swing: {detail}", now)

    bs = statefiles.read_brain_status()
    if bs is None or bs.get("status") != "OK" or \
            (now - statefiles.parse_ts(bs["ts_paris"])).total_seconds() > BRAIN_STALE_H * 3600:
        detail = "absent" if bs is None else \
            (bs.get("status") if bs.get("status") != "OK" else "stale >25h")
        fired.append("brain")
        _alert("brain", 60, f"brain_status {detail} — targets non régénérés "
                            f"({(bs or {}).get('error', '')})", now)

    bk = book_engine_streak(files_dir)
    if bk and not bk["engines_on"]:
        ms = _book_idle_milestone(bk["streak"])
        if ms is not None:                         # clé par PALIER, pas par jour
            fired.append("book_idle")
            _alert(f"book_idle_at_{ms}", 7 * 24 * 60,
                   _book_idle_text(files_dir, bk), now)

    # Divergence marge MODÈLE <-> BROKER (LOT B). L'EA enforce au taux serveur
    # (OrderCalcMargin) : c'est le MODÈLE qui mentirait, pas l'exécution — ni le sizing
    # live ni le risque ne bougent, mais tout p(pass)/EV cité deviendrait faux.
    # Placé APRÈS l'alerte `brain` à dessein : une régression de cette télémétrie
    # (neuve, donc la moins éprouvée) ne doit jamais pouvoir éteindre la surveillance
    # de santé en aval — `daemon()` avale les exceptions, une erreur ici tuerait
    # silencieusement brain/book_idle/swap_drift à chaque boucle.
    # `or 0` et pas `get(..., 0)` : la clé EXISTE avec la valeur null quand les specs
    # broker sont indisponibles -> le défaut ne s'appliquerait pas -> TypeError.
    bs_lt = (bs or {}).get("live_truth") or {}
    if bs_lt.get("mrate_divergence_breach"):
        fired.append("mrate_divergence")
        _alert("mrate_divergence", 12 * 60,
               f"MARGE MODÈLE ≠ BROKER — écart max "
               f"{100 * float(bs_lt.get('mrate_worst_rel_diff') or 0):+.1f}% "
               f"(source modèle: {bs_lt.get('mrate_source')}). Le sizing LIVE reste "
               f"sûr (l'EA enforce au taux serveur) mais les p(pass)/EV cités sont "
               f"à recalculer.", now)
    if str(bs_lt.get("mrate_source") or "").startswith("REPLI"):
        fired.append("mrate_fallback")
        _alert("mrate_fallback", 24 * 60,
               "MARGE modèle en REPLI littéral — le cleanroom du VPS est en retard "
               "sur main (governor._live_truth n'a pas trouvé engine.MRATE_SWING). "
               "Resynchroniser le dépôt VPS.", now)

    drift = swap_drift_last_night(files_dir, now)
    if drift and drift.get("gate_breach"):
        fired.append("swap_drift")
        _alert(f"swap_{day}", 24 * 60,
               f"SWAP DRIFT {drift['total_drift_pct']:+.0f}% > ±20% "
               f"(facturé ${drift['total_billed']:+.2f} vs modèle "
               f"${drift['total_model']:+.2f}) — gate live yaml: STOP si confirmé", now)

    st = _load(ALERTS_STATE, {})
    st["_last_state_mtime"] = mtime
    statefiles.atomic_write_json(ALERTS_STATE, st)
    return fired


def swap_drift_last_night(files_dir: Path, now: datetime) -> Optional[dict]:
    """billed_vs_model sur la dernière nuit présente dans swaps_billed.csv."""
    df = statefiles.read_swaps_billed(files_dir)
    if not len(df):
        return None
    last = sorted(df["date_paris"].astype(str).unique())[-1]
    rows = df[df["date_paris"].astype(str) == last]
    billed, modeled = {}, {}
    for _, r in rows.iterrows():
        leg = _leg_of(r["symbol"])
        if leg is None:
            continue
        billed[leg] = billed.get(leg, 0.0) + float(r["swap_usd"])
        bps, _ = swaps.anchor_bps(leg, "long" if float(r.get("notional_usd", 0)) >= 0
                                  else "short")
        if bps is not None:
            mult = swaps.night_multiplier(leg, pd.Timestamp(last))
            modeled[leg] = modeled.get(leg, 0.0) + abs(
                float(r.get("notional_usd", 0))) * bps / 1e4 * mult
    if not billed:
        return None
    out = swaps.billed_vs_model(billed, modeled)
    out["night"] = last
    return out


# ------------------------------------------------------------------ rapports
def _fmt_positions(state: dict) -> str:
    rows = []
    for p in (state or {}).get("positions", []):
        side = "+" if int(p.get("dir", 1)) > 0 else "−"
        rows.append(f"{p.get('leg', p.get('symbol'))} {side}{abs(float(p['lots'])):g} "
                    f"lots (${abs(float(p['notional_usd'])) / 1e3:,.1f}k)")
    return " | ".join(rows) if rows else "flat"


def _campaign() -> dict:
    return _load(CAMPAIGN, dict(fees=[], total=0.0))


def build_morning(state: dict, files_dir: Path, now: datetime) -> str:
    init = _initial()
    sp = spec.load()
    wall = spec.wall_days(sp)
    eq = float(state.get("equity", 0))
    target_eq = float(state.get("target_equity", 0))
    att = state.get("attempt_start", "?")
    day_n = (now.date() - pd.Timestamp(att).date()).days + 1 if att != "?" else "?"
    prog = (eq / init - 1) / max(target_eq / init - 1, 1e-9) * 100 if target_eq else 0.0
    snaps = _load(SNAP_PATH, {})
    ev = snaps.get("evening", {})
    pnl_night = eq - float(ev["equity"]) if ev.get("equity") else None
    drift = swap_drift_last_night(files_dir, now)
    gov = state.get("governor", {})
    on_day = now.weekday() in (0, 1)
    trip = [l for l in LEGS if swaps.night_multiplier(l, pd.Timestamp(now.date())) == 3]
    micro_armed = inv.micro_armed(on_day, bool(int(state.get("micro_enabled", 1))),
                                  False)
    lines = [
        f"🌅 FTMO {state.get('phase', '?')} — J{day_n}/{wall} — {now.date()}",
        f"Jours tradés {state.get('open_days', '?')}/{state.get('min_days', 4)} | "
        f"tentative {att}",
        f"Equity ${eq:,.0f} ({(eq / init - 1) * 100:+.2f}% init) — cible "
        f"${target_eq:,.0f} ({prog:.0f}%)",
        f"Rooms: daily ${float(state.get('room_daily_usd', 0)):,.0f} | "
        f"floor ${eq - inv.static_floor(init):,.0f} | "
        f"breaker ${float(state.get('breaker_line', 0)):,.0f}",
    ]
    if pnl_night is not None:
        lines.append(f"Nuit: PnL ${pnl_night:+,.0f}")
    if drift:
        lines.append(f"Swaps {drift['night']}: facturé ${drift['total_billed']:+.2f} "
                     f"vs modèle ${drift['total_model']:+.2f} "
                     f"({drift['total_drift_pct'] if drift['total_drift_pct'] is not None else '?'}%)"
                     + (" ⚠ GATE ±20%" if drift.get("gate_breach") else ""))
    lines += [
        f"Positions: {_fmt_positions(state)} | marge "
        f"{float(state.get('margin_used_pct_equity', 0)):.0f}%/60%",
        f"Gouverneur: taper {gov.get('taper', '?')} glide {gov.get('glide', '?')} "
        f"pace {gov.get('pace', '?')} | breaker armé | "
        f"zombie {state.get('abandon_zombie_days', 0)}/5",
        _book_engine_line(files_dir),
        "Programme: rebalance 22:05"
        + (" | GER40 17:35 + US100 22:05 (jour ON)" if on_day else "")
        + (" | micro-ORB armable 16:00" if micro_armed else " | micro-ORB OFF (jour ON)"
           if int(state.get("micro_enabled", 1)) else "")
        + (f" | triple-swap ce soir: {','.join(trip)}" if trip else "")
        + (" | weekend tenu dès ce soir" if now.weekday() == 4 else ""),
        _state_freshness(state, now),
    ]
    if int(state.get("kill", 0)):
        lines.append("⛔ KILL-FILE ACTIF")
    return "\n".join(lines)


def build_evening(state: dict, files_dir: Path, now: datetime) -> str:
    init = _initial()
    day = str(now.date())
    eq = float(state.get("equity", 0))
    anchor = float(state.get("anchor_balance", init))
    pnl_day = eq - anchor
    fills = statefiles.read_fills(files_dir, day)
    targets = statefiles.read_json(files_dir / "targets.json") or {}
    target_eq = float(state.get("target_equity", 0))
    prog = (eq / init - 1) / max(target_eq / init - 1, 1e-9) * 100 if target_eq else 0.0
    slip = pd.to_numeric(fills["slip_bps"], errors="coerce").dropna() if len(fills) else []
    reb = fills[fills["reason"] == "rebalance"] if len(fills) else fills
    deltas = []
    for _, r in (reb.iterrows() if len(reb) else []):
        sgn = "+" if str(r["side"]).upper() == "BUY" else "−"
        deltas.append(f"{_leg_of(r['symbol']) or r['symbol']} {sgn}{float(r['lots']):g}")
    cost_est = None
    if len(fills):
        f2 = fills.dropna(subset=["slip_bps"])
        if len(f2):
            cost_est = float((pd.to_numeric(f2["slip_bps"]) / 1e4 *
                              pd.to_numeric(f2["lots"], errors="coerce").fillna(0) *
                              pd.to_numeric(f2["fill_price"], errors="coerce").fillna(0)
                              ).abs().sum())
    pos_now = {p["leg"]: float(p["notional_usd"]) * (1 if int(p["dir"]) > 0 else -1)
               for p in state.get("positions", []) if p.get("leg") in LEGS}
    swdue = swaps.forecast_night(pos_now, pd.Timestamp(day))
    rec = _last_reconcile()
    camp = _campaign()
    lines = [
        f"🌙 FTMO {state.get('phase', '?')} — {day} 22:20",
        f"PnL jour ${pnl_day:+,.0f} ({pnl_day / init * 100:+.2f}%) | equity ${eq:,.0f} "
        f"— {prog:.0f}% cible | jours {state.get('open_days', '?')}/"
        f"{state.get('min_days', 4)}",
        f"Trades: {len(fills)} fills"
        + (f" | slip méd {float(pd.Series(slip).median()):+.1f} bps" if len(slip) else "")
        + (f" | rejets: {state.get('last_error')}" if state.get("last_error") else ""),
        "Rebalance Δ: " + (" | ".join(deltas) if deltas else "aucun"),
        (f"Coûts jour est. ${cost_est:,.2f} | " if cost_est is not None else "")
        + f"swaps dus cette nuit ${swdue['total_usd']:+,.2f}",
        f"Réconciliation: Δ inexpliqué {rec.get('consec', 0)}/3"
        + (f" | dernier ${rec.get('residual', 0):+,.2f} ({rec.get('date')})"
           if rec.get("date") else " | pas encore de run"),
        f"Campagne: fees ${camp['total']:,.0f} / budget ${CAMPAIGN_BUDGET_USD:,.0f} "
        f"(reste ${CAMPAIGN_BUDGET_USD - camp['total']:,.0f})",
        _state_freshness(state, now),
    ]
    if str(state.get("targets_status", "OK")) != "OK":
        lines.append(f"⚠ targets.json: {state.get('targets_status')}")
    if not targets:
        lines.append("⚠ targets.json absent")
    return "\n".join(lines)


def _last_reconcile() -> dict:
    p = RUNTIME / "reconcile_log.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    if not len(df):
        return {}
    r = df.iloc[-1]
    return dict(date=str(r.get("date")), residual=float(r.get("residual_usd", 0)),
                consec=int(r.get("consec_unexplained", 0)))


def _snapshot(kind: str, state: dict, now: datetime) -> None:
    snaps = _load(SNAP_PATH, {})
    snaps[kind] = dict(ts=statefiles.fmt_ts(now), equity=float(state.get("equity", 0)),
                       balance=float(state.get("balance", 0)))
    statefiles.atomic_write_json(SNAP_PATH, snaps)


def _archive_sod(state: dict, now: datetime) -> None:
    SOD_DIR.mkdir(parents=True, exist_ok=True)
    p = SOD_DIR / f"state_{now.date()}.json"
    if not p.exists():
        statefiles.atomic_write_json(p, state)


def daemon() -> None:
    files_dir = statefiles.mt5_files_dir()
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if os.environ.get("FTMO_LIVE_TG_DISABLED") != "1":
        tg.check_token(tok)
    print(f"supervisor démarré — files={files_dir}")
    while True:
        try:
            now = statefiles.now_paris().replace(tzinfo=None)
            state = statefiles.read_state(files_dir)
            if state is not None:
                _archive_sod(state, now)
            evaluate_alerts(files_dir, now)
        except Exception as e:
            print(f"[supervisor] {e!r}", flush=True)
        time.sleep(60)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--report", choices=["morning", "evening"])
    ap.add_argument("--add-fee", nargs=2, metavar=("USD", "LABEL"))
    ap.add_argument("--test-alert", action="store_true")
    a = ap.parse_args(argv)
    if a.add_fee:
        camp = _campaign()
        camp["fees"].append(dict(usd=float(a.add_fee[0]), label=a.add_fee[1],
                                 ts=statefiles.fmt_ts(statefiles.now_paris()
                                                      .replace(tzinfo=None))))
        camp["total"] = sum(f["usd"] for f in camp["fees"])
        statefiles.atomic_write_json(CAMPAIGN, camp)
        print(f"fee ajouté — total ${camp['total']:,.0f}")
        return 0
    if a.test_alert:
        tg.send("✅ FTMO live — test alerte supervisor")
        return 0
    if a.report:
        files_dir = statefiles.mt5_files_dir()
        now = statefiles.now_paris().replace(tzinfo=None)
        state = statefiles.read_state(files_dir)
        if state is None:
            tg.send(f"🚨 FTMO live — rapport {a.report}: state.json ABSENT")
            return 1
        txt = build_morning(state, files_dir, now) if a.report == "morning" \
            else build_evening(state, files_dir, now)
        tg.send(txt)
        _snapshot(a.report, state, now)
        return 0
    if a.daemon:
        daemon()
    return 0


if __name__ == "__main__":
    sys.exit(main())
