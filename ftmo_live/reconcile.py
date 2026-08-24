#!/usr/bin/env python3
"""reconcile.py — cron 23:00 Paris : rejoue la journée dans le moteur sim
(atomes E, lib/replay) avec les fills réels ; Δ décomposé signal/coût/timing/
micro/swap ; 3 jours consécutifs d'écart inexpliqué -> recommandation STOP +
alerte (gate de production du RAPPORT).

Fenêtre du jour = [balance@00:00 (ancre, post-swap de la veille), snapshot EOD
22:58 de l'EA] — les swaps de CETTE nuit (postés ~23:00 Paris = minuit serveur)
sont hors fenêtre et réconciliés séparément (gate ±20%, supervisor).

Décomposition (USD) :
  Δ_total   = equity réelle EOD − equity modèle (les deux markées M5 22:55)
  Δ_signal  = Σ jambes (lots EA − lots modèle au même prix) x px  [conformance]
  Δ_cost    = Σ fills (fill−req)·dir·notional/req + modèle half-RT (ancres yaml)
  Δ_timing  = Σ jambes rebalance (req − px_M5_2205)·dir·units
  Δ_micro   = micro réel (fills) − micro modèle (miroir V2+E7, gross)
  residual  = Δ_total − (Δ_signal + Δ_cost + Δ_timing + Δ_micro)
Inexpliqué si |residual| > TOL = 5$ + 1bp x turnover + 0.5bp x book brut.

Usage: reconcile.py [--date YYYY-MM-DD] [--no-alert]
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tg  # noqa: E402
from lib import LEGS, RUNTIME  # noqa: E402
from lib import replay, statefiles  # noqa: E402

LOG = RUNTIME / "reconcile_log.csv"
EOD_DIR = RUNTIME / "eod"
LOG_COLUMNS = ["date", "pnl_real", "pnl_model", "delta_total", "d_signal", "d_cost",
               "d_timing", "d_micro", "residual_usd", "tol_usd", "unexplained",
               "consec_unexplained", "stop_recommended", "n_fills", "detail_path"]


def _leg_of(symbol: str):
    for l in LEGS:
        if str(symbol).startswith(l):
            return l
    return None


def _pos_vec(positions: list):
    pos, avg = np.zeros(4), np.full(4, np.nan)
    for p in positions or []:
        leg = p.get("leg") or _leg_of(p.get("symbol", ""))
        if leg in LEGS:
            k = LEGS.index(leg)
            pos[k] = float(p["notional_usd"]) * (1 if int(p["dir"]) > 0 else -1)
            avg[k] = float(p["avg"])
    return pos, avg


def _sod(files_dir: Path, day: str) -> dict:
    p = RUNTIME / "sod" / f"state_{day}.json"
    st = statefiles.read_json(p)
    if st is not None:
        return st
    prev = sorted(EOD_DIR.glob("eod_*.json"))
    if prev:
        e = statefiles.read_json(prev[-1])
        if e:
            return dict(balance=e["balance"], positions=e.get("positions", []),
                        anchor_balance=e["balance"], _fallback="eod_prev")
    raise RuntimeError(f"pas de state start-of-day pour {day} "
                       "(supervisor --daemon doit tourner)")


def _degraded_reconcile(state: dict, files_dir: Path, day: str, eod: dict,
                        alert: bool) -> dict:
    """Réconciliation DÉGRADÉE quand l'EOD 22:58 manque par GEL DE CLÔTURE — voir run().

    QUOTIDIEN, pas seulement le vendredi : le gel de ticks de fin de journée (rollover
    serveur 00:00 EEST = 21:00 UTC en semaine ; clôture forex ~22:54 le vendredi) fige
    TimeCurrent() vers ~22:54 Paris → la grille EA (book_executor.mq5:1517, hm>=2258)
    n'atteint jamais 22:58 → Do2258EOD ne s'exécute pas → ni state.eod NI m5_today.json
    (co-écrits, mq5:1228-1229).

    Sans m5_today, le modèle (replay) n'a pas de chemin de prix → la décomposition Δ
    signal/coût/timing/micro est IMPOSSIBLE. On enregistre le PnL réel de clôture (equity
    broker @~22:54, PRÉ-swap, déjà markée) pour la piste d'audit ; le gate « 3 jours
    inexpliqués » n'est PAS évalué (consec PRÉSERVÉ : un jour sans information ne casse ni
    n'étend une série inexpliquée).

    Pourquoi ne PAS attendre l'EOD tardif : l'EA re-déclenche bien Do2258EOD ~21:02 UTC (1er
    tick post-reconnexion, hm=2302, g_done_2258 encore false) — mais APRÈS le swap posté à
    21:00 UTC (minuit serveur) → ce bloc eod tardif est POST-swap, contaminé pour la fenêtre
    du jour. L'equity figée @~22:54 (lue par le cron 21:00 UTC) est PRÉ-swap, correcte.

    Garde anti-masquage : on ne dégrade QUE si le gel de CLÔTURE est avéré — l'EA a battu le
    jour J jusqu'à près de la clôture (ts_paris du jour J ET >= 22:30 Paris). Distinction par
    l'HEURE du dernier battement : un crash en milieu de séance laisse ts_paris tôt → vraie
    absence d'EOD → on relève le RuntimeError (pas de masquage), tous jours confondus.

    Swap : la fenêtre du jour exclut le swap de CETTE nuit (posté ~minuit serveur, APRÈS la
    clôture) ; sa vérification (×3 indices certains soirs) reste au superviseur
    (swap_drift_last_night, hors fenêtre) — le fallback 22:54 vs 22:58 est swap-neutre.
    """
    absent = RuntimeError(f"snapshot EOD 22:58 absent pour {day} "
                          f"(eod.date={eod.get('date')}) — EA down avant 22:58 ?")
    try:
        ts = statefiles.parse_ts(state["ts_paris"])
    except (KeyError, ValueError, TypeError):
        raise absent
    if str(ts.date()) != day or (ts.hour, ts.minute) < (22, 30):
        raise absent
    eq_close = state.get("equity")
    if eq_close is None:
        raise absent

    sod = _sod(files_dir, day)
    anchor = float(sod.get("anchor_balance", sod.get("balance")))
    pnl_real = float(eq_close) - anchor
    fills = statefiles.read_fills(files_dir, day)
    jours = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
    wd = jours[pd.Timestamp(day).dayofweek]
    msg = (f"reconcile {day} ({wd}) DÉGRADÉ : snapshot EOD 22:58 absent (gel de clôture "
           f"~22:54, Do2258EOD non atteint) — fallback sur état de clôture "
           f"({state['ts_paris']}, equity ${float(eq_close):,.2f}, pré-swap). Modèle/Δ non "
           f"rejoués (m5_today absent) ; PnL réel ${pnl_real:+.2f} enregistré, gate STOP non "
           f"évalué ce jour.")
    print(msg)

    prev = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame(columns=LOG_COLUMNS)
    consec = (int(prev.iloc[-1]["consec_unexplained"])
              if len(prev) and str(prev.iloc[-1]["date"]) != day else 0)
    row = dict(date=day, pnl_real=round(pnl_real, 2), pnl_model="", delta_total="",
               d_signal="", d_cost="", d_timing="", d_micro="", residual_usd=0.0,
               tol_usd="", unexplained=0, consec_unexplained=consec, stop_recommended=0,
               n_fills=int(len(fills)), detail_path="degraded")
    statefiles.append_csv(LOG, LOG_COLUMNS, row)
    if alert:
        tg.send(f"🟦 FTMO live — {msg} Swap nuit vérifié séparément par le superviseur.")
    _save_preswap_snapshot(state, files_dir, day, anchor)   # Option A — stage 1 capture
    return row


def _save_preswap_snapshot(state: dict, files_dir: Path, day: str, anchor: float) -> None:
    """Option A (stage 1, ~21:00 UTC) : fige la clôture PRÉ-swap (equity/balance/positions
    lues de l'état figé 22:54) + le contexte (poids, on_day, phase) pour que l'upgrade
    (stage 2, ~21:10) reconstruise la vraie décomposition Δ avec le m5_today tardif. Écrit
    une seule fois par jour (l'état figé ne bouge pas pendant le gel)."""
    targets = statefiles.read_json(files_dir / "targets.json") or {}
    weights = {"XAUUSD": float(targets.get("ea_w_xauusd", 0.0)),
               "USDJPY": float(targets.get("ea_w_usdjpy", 0.0))}
    on_day = bool(int(targets.get("ea_on_day", pd.Timestamp(day).dayofweek in (0, 1))))
    EOD_DIR.mkdir(parents=True, exist_ok=True)
    statefiles.atomic_write_json(EOD_DIR / f"preswap_{day}.json", dict(
        day=day, ts_paris=state.get("ts_paris"),
        balance=float(state.get("balance", state.get("equity", anchor))),
        equity=float(state.get("equity", anchor)),
        positions=state.get("positions", []), anchor=anchor,
        weights=weights, on_day=on_day, phase=state.get("phase", "P1"),
        attempt_start=str(state.get("attempt_start", day)),
        last_rebalance=state.get("last_rebalance"),
        symbol_specs=state.get("symbol_specs", {})))


def _decompose(day: str, *, anchor: float, pos0, avg0, eod_balance: float, eod_positions: list,
               weights, on_day: bool, phase: str, att, last_rebalance, symbol_specs: dict,
               m5_legs: dict, fills) -> dict:
    """Coeur partagé de la décomposition Δ (réel − modèle) en signal/coût/timing/micro.
    Utilisé par le chemin EOD on-time (run) ET l'upgrade Option A (m5 tardif + clôture
    pré-swap). real_eq = eod_balance + mark(eod_positions @ px modèle 22:55)."""
    mod = replay.replay_day(pd.Timestamp(day), phase, att, anchor, pos0, avg0,
                            weights, on_day, m5_legs)
    eod_px = mod["eod_px"]
    pos_r, avg_r = _pos_vec(eod_positions)
    mtm_r = sum(pos_r[k] * (eod_px[l] / avg_r[k] - 1.0)
                for k, l in enumerate(LEGS)
                if pos_r[k] != 0.0 and np.isfinite(avg_r[k]) and np.isfinite(eod_px[l]))
    real_eq = float(eod_balance) + float(mtm_r)
    pnl_real = real_eq - anchor
    pnl_model = float(mod["model_equity"]) - anchor
    d_total = pnl_real - pnl_model

    # Conformance (Δ_signal) : cibles $ de l'EA (last_rebalance) vs cibles modèle —
    # rapportée/alertée, PAS soustraite du résiduel (une vraie divergence DOIT rester
    # inexpliquée pour déclencher le gate).
    d_signal = 0.0
    lr = last_rebalance or {}
    mod_t4 = next((t for t in mod["trades"] if t["seg"] == 4), None)
    if lr and mod_t4:
        d_signal = sum(abs(float((lr.get("targets_usd") or {}).get(l, 0.0))
                           - float(mod_t4["tgt"].get(l, 0.0))) for l in LEGS)

    d_exec, d_timing, turnover = 0.0, 0.0, 0.0
    for _, f in fills.iterrows():
        leg = _leg_of(f["symbol"])
        try:
            req, fill, lots = float(f["req_price"]), float(f["fill_price"]), float(f["lots"])
        except (TypeError, ValueError):
            continue
        if not (np.isfinite(req) and np.isfinite(fill) and req > 0 and lots != 0):
            continue
        side = 1.0 if str(f["side"]).upper() == "BUY" else -1.0
        upu = _usd_per_unit(symbol_specs, f["symbol"])
        units = abs(lots) * upu
        turnover += abs(lots) * req * upu
        d_exec += (req - fill) * side * units
        if str(f["reason"]) == "rebalance" and leg and mod_t4:
            px_mod = mod_t4["px"].get(leg)
            if px_mod and np.isfinite(px_mod):
                d_timing += (px_mod - req) * side * units
    d_costmb = sum(float(t.get("cost_model_usd", 0.0)) for t in mod["trades"])
    d_cost = d_exec + d_costmb

    # micro (challenge, magic MAGIC_MICRO) et funded ORB (funded, magic MAGIC_FORB)
    # partagent le même symbole/mécanique V2+E7 et sont mutuellement exclusifs par
    # phase (mq5:170-171) -> même pairing entrée/sortie, comparé à mod["micro"] +
    # mod["funded_orb"] (avant ce correctif, funded_orb n'existait pas et son PnL
    # réel finissait entièrement dans le résiduel inexpliqué, cf. 2026-08-21).
    micro_real = 0.0
    mf = fills[fills["reason"].astype(str).str.startswith(("micro", "funded_orb"))] \
        if len(fills) else fills
    if len(mf):
        ent = mf[mf["reason"].isin(["micro_entry", "funded_orb_entry"])]
        ext = mf[mf["reason"].isin(["micro_stop", "micro_be", "micro_time", "funded_orb_exit"])]
        if len(ent) and len(ext):
            e0, x0 = ent.iloc[0], ext.iloc[-1]
            side = 1.0 if str(e0["side"]).upper() == "BUY" else -1.0
            micro_real = (float(x0["fill_price"]) - float(e0["fill_price"])) * side \
                * float(e0["lots"]) * replay.US100_USD_PER_PT_PER_LOT
    mod_micro_pnl = float(mod["micro"]["pnl_usd"]) \
        + float(mod.get("funded_orb", {}).get("pnl_usd", 0.0))
    d_micro = micro_real - mod_micro_pnl

    gross_book = float(np.abs(pos0).sum())
    tol = 5.0 + 1e-4 * turnover + 0.5e-4 * gross_book
    residual = d_total - (d_cost + d_timing + d_micro)
    unexplained = bool(abs(residual) > tol)
    return dict(mod=mod, pnl_real=pnl_real, pnl_model=pnl_model, d_total=d_total,
                d_signal=d_signal, d_cost=d_cost, d_timing=d_timing, d_micro=d_micro,
                residual=residual, tol=tol, unexplained=unexplained)


def run(day: str = None, alert: bool = True) -> dict:
    files_dir = statefiles.mt5_files_dir()
    now = statefiles.now_paris().replace(tzinfo=None)
    day = day or str(now.date())

    state = statefiles.read_state(files_dir) or {}
    eod = state.get("eod") or {}
    if str(eod.get("date")) != day:
        # Snapshot EOD 22:58 absent. C'est STRUCTUREL et QUOTIDIEN : le gel de ticks de fin
        # de journée (rollover serveur 00:00 EEST = 21:00 UTC en semaine ; clôture forex
        # ~22:54 le vendredi) fige TimeCurrent() vers ~22:54 → la grille EA
        # (book_executor.mq5:1517, hm>=2258) n'atteint jamais 22:58 → Do2258EOD ne s'exécute
        # PAS → ni le bloc state.eod NI m5_today.json (mq5:1228-1229). Réconciliation
        # dégradée (PnL réel pré-swap seul) SI le gel de clôture est avéré (ts du jour
        # >= 22:30 Paris) ; sinon (mort en journée, ts tôt) → vraie absence, on lève.
        return _degraded_reconcile(state, files_dir, day, eod, alert)
    m5 = statefiles.read_json(files_dir / "m5_today.json") or {}
    if str(m5.get("date")) != day:
        raise RuntimeError(f"m5_today.json absent/périmé pour {day}")
    targets = statefiles.read_json(files_dir / "targets.json") or {}
    fills = statefiles.read_fills(files_dir, day)
    sod = _sod(files_dir, day)

    phase = state.get("phase", targets.get("ea_phase_hint", "P1"))
    att = pd.Timestamp(state.get("attempt_start", day))
    anchor = float(sod.get("anchor_balance", sod.get("balance")))
    pos0, avg0 = _pos_vec(sod.get("positions", []))
    weights = (float(targets.get("ea_w_xauusd", 0.0)),
               float(targets.get("ea_w_usdjpy", 0.0)))
    on_day = bool(int(targets.get("ea_on_day", pd.Timestamp(day).dayofweek in (0, 1))))

    d = _decompose(day, anchor=anchor, pos0=pos0, avg0=avg0,
                   eod_balance=float(eod["balance"]), eod_positions=eod.get("positions", []),
                   weights=weights, on_day=on_day, phase=phase, att=att,
                   last_rebalance=state.get("last_rebalance"),
                   symbol_specs=state.get("symbol_specs", {}),
                   m5_legs=m5.get("legs", {}), fills=fills)
    mod, pnl_real, pnl_model, d_total = d["mod"], d["pnl_real"], d["pnl_model"], d["d_total"]
    d_signal, d_cost, d_timing, d_micro = d["d_signal"], d["d_cost"], d["d_timing"], d["d_micro"]
    residual, tol, unexplained = d["residual"], d["tol"], d["unexplained"]

    prev = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame(columns=LOG_COLUMNS)
    consec = (int(prev.iloc[-1]["consec_unexplained"])
              if len(prev) and str(prev.iloc[-1]["date"]) != day else 0)
    consec = consec + 1 if unexplained else 0
    stop = consec >= 3

    EOD_DIR.mkdir(parents=True, exist_ok=True)
    detail_path = EOD_DIR / f"reconcile_{day}.json"
    statefiles.atomic_write_json(EOD_DIR / f"eod_{day}.json", eod)
    statefiles.atomic_write_json(detail_path, dict(
        date=day, pnl_real=pnl_real, pnl_model=pnl_model, model=mod,
        d_signal=d_signal, d_cost=d_cost, d_timing=d_timing, d_micro=d_micro,
        residual=residual, tol=tol, weights=weights, on_day=on_day,
        n_fills=int(len(fills)), sod_fallback=sod.get("_fallback")))
    row = dict(date=day, pnl_real=round(pnl_real, 2), pnl_model=round(pnl_model, 2),
               delta_total=round(d_total, 2), d_signal=round(d_signal, 2),
               d_cost=round(d_cost, 2), d_timing=round(d_timing, 2),
               d_micro=round(d_micro, 2), residual_usd=round(residual, 2),
               tol_usd=round(tol, 2), unexplained=int(unexplained),
               consec_unexplained=consec, stop_recommended=int(stop),
               n_fills=int(len(fills)), detail_path=str(detail_path))
    statefiles.append_csv(LOG, LOG_COLUMNS, row)

    msg = (f"reconcile {day}: PnL réel ${pnl_real:+.2f} vs modèle ${pnl_model:+.2f} "
           f"| Δcost ${d_cost:+.2f} Δtiming ${d_timing:+.2f} Δmicro ${d_micro:+.2f} "
           f"| résiduel ${residual:+.2f} (tol ${tol:.2f}) "
           f"{'INEXPLIQUÉ' if unexplained else 'OK'} {consec}/3")
    print(msg)
    if alert and unexplained:
        tg.send(f"⚠️ FTMO live — {msg}")
    if alert and stop:
        tg.send(f"🛑 FTMO live — 3 jours d'écart inexpliqué consécutifs "
                f"({day}) : RECOMMANDATION STOP — gate de production du rapport. "
                f"Détails: {detail_path.name}")
    return row


def _usd_per_unit(symbol_specs: dict, symbol: str) -> float:
    """$ par unité de prix par lot (tick_value/tick_size exporté par l'EA)."""
    specs = (symbol_specs or {})
    s = specs.get(symbol) or specs.get(_leg_of(symbol) or "", {})
    tv, ts = float(s.get("tick_value", 0)), float(s.get("tick_size", 0))
    if tv > 0 and ts > 0:
        return tv / ts
    leg = _leg_of(symbol)
    return {"XAUUSD": 100.0, "USDJPY": 100000.0 / max(float(s.get("price", 145.0)), 1e-9),
            "US100": 1.0, "GER40": 1.0}.get(leg, 1.0)


def _replace_day_row(day: str, row: dict) -> None:
    """Remplace la ligne du jour dans reconcile_log.csv (dégradé de stage 1 → Δ complet)."""
    df = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame(columns=LOG_COLUMNS)
    df = df[df["date"].astype(str) != day]
    df = pd.concat([df, pd.DataFrame([row], columns=LOG_COLUMNS)], ignore_index=True)
    df.to_csv(LOG, index=False)


def upgrade(day: str = None, alert: bool = True, dry_run: bool = False) -> Optional[dict]:
    """Option A — stage 2 (~21:10 UTC). Si le m5_today TARDIF du jour est arrivé (~21:05,
    après le gel de clôture), reconstruit la VRAIE décomposition Δ avec le chemin de prix M5
    + la clôture PRÉ-swap figée par stage 1, et REMPLACE la ligne dégradée. Sinon no-op (la
    ligne dégradée reste — jamais de trou). Ne touche jamais l'EA/FLAT/targets."""
    files_dir = statefiles.mt5_files_dir()
    now = statefiles.now_paris().replace(tzinfo=None)
    day = day or str(now.date())
    snap = statefiles.read_json(EOD_DIR / f"preswap_{day}.json")
    if not snap:
        print(f"upgrade {day}: pas de snapshot pré-swap (stage 1 non exécuté / EOD on-time) — skip")
        return None
    m5 = statefiles.read_json(files_dir / "m5_today.json") or {}
    if str(m5.get("date")) != day:
        print(f"upgrade {day}: m5_today tardif absent (date={m5.get('date')}) — reste dégradé")
        return None
    sod = _sod(files_dir, day)
    anchor = float(snap.get("anchor", sod.get("anchor_balance", sod.get("balance"))))
    pos0, avg0 = _pos_vec(sod.get("positions", []))
    w = snap.get("weights", {})
    weights = (float(w.get("XAUUSD", 0.0)), float(w.get("USDJPY", 0.0)))
    fills = statefiles.read_fills(files_dir, day)
    d = _decompose(day, anchor=anchor, pos0=pos0, avg0=avg0,
                   eod_balance=float(snap["balance"]), eod_positions=snap.get("positions", []),
                   weights=weights, on_day=bool(snap.get("on_day")),
                   phase=snap.get("phase", "P1"), att=pd.Timestamp(snap.get("attempt_start", day)),
                   last_rebalance=snap.get("last_rebalance"),
                   symbol_specs=snap.get("symbol_specs", {}), m5_legs=m5.get("legs", {}), fills=fills)

    prev = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame(columns=LOG_COLUMNS)
    before = prev[prev["date"].astype(str) != day]
    consec_prev = int(before.iloc[-1]["consec_unexplained"]) if len(before) else 0
    consec = consec_prev + 1 if d["unexplained"] else 0
    stop = consec >= 3
    msg = (f"reconcile {day} Δ COMPLET (m5 tardif): PnL réel ${d['pnl_real']:+.2f} vs modèle "
           f"${d['pnl_model']:+.2f} | Δsignal ${d['d_signal']:+.2f} Δcost ${d['d_cost']:+.2f} "
           f"Δtiming ${d['d_timing']:+.2f} Δmicro ${d['d_micro']:+.2f} | résiduel ${d['residual']:+.2f} "
           f"(tol ${d['tol']:.2f}) {'INEXPLIQUÉ' if d['unexplained'] else 'OK'} {consec}/3")
    print(msg)
    if dry_run:
        return dict(day=day, consec=consec, stop=stop, **{k: d[k] for k in (
            "pnl_real", "pnl_model", "d_total", "d_signal", "d_cost", "d_timing",
            "d_micro", "residual", "tol", "unexplained")})
    EOD_DIR.mkdir(parents=True, exist_ok=True)
    detail_path = EOD_DIR / f"reconcile_{day}.json"
    statefiles.atomic_write_json(detail_path, dict(
        date=day, source="optA_late_m5", pnl_real=d["pnl_real"], pnl_model=d["pnl_model"],
        model=d["mod"], d_signal=d["d_signal"], d_cost=d["d_cost"], d_timing=d["d_timing"],
        d_micro=d["d_micro"], residual=d["residual"], tol=d["tol"], weights=list(weights),
        on_day=bool(snap.get("on_day")), n_fills=int(len(fills))))
    row = dict(date=day, pnl_real=round(d["pnl_real"], 2), pnl_model=round(d["pnl_model"], 2),
               delta_total=round(d["d_total"], 2), d_signal=round(d["d_signal"], 2),
               d_cost=round(d["d_cost"], 2), d_timing=round(d["d_timing"], 2),
               d_micro=round(d["d_micro"], 2), residual_usd=round(d["residual"], 2),
               tol_usd=round(d["tol"], 2), unexplained=int(d["unexplained"]),
               consec_unexplained=consec, stop_recommended=int(stop),
               n_fills=int(len(fills)), detail_path=str(detail_path))
    _replace_day_row(day, row)
    if alert and d["unexplained"]:
        tg.send(f"⚠️ FTMO live — {msg}")
    if alert and stop:
        tg.send(f"🛑 FTMO live — 3 jours d'écart inexpliqué consécutifs ({day}) : "
                f"RECOMMANDATION STOP — gate de production. Détails: {detail_path.name}")
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--no-alert", action="store_true")
    ap.add_argument("--upgrade", action="store_true",
                    help="Option A stage 2 (~21:10 UTC) : upgrade le jour en Δ COMPLET via le m5_today tardif")
    ap.add_argument("--dry-run", action="store_true",
                    help="avec --upgrade : calcule et imprime la décomposition SANS écrire")
    a = ap.parse_args(argv)
    try:
        if a.upgrade:
            upgrade(a.date, alert=not a.no_alert, dry_run=a.dry_run)
        else:
            run(a.date, alert=not a.no_alert)
        return 0
    except Exception as e:
        print(f"reconcile ERROR: {e!r}")
        if not a.no_alert:
            try:
                tg.send(f"🚨 FTMO live — reconcile ÉCHEC: {e!r}")
            except Exception:
                pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
