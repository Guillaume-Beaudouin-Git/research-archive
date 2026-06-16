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


def _friday_degraded_reconcile(state: dict, files_dir: Path, day: str, eod: dict,
                               alert: bool) -> dict:
    """Réconciliation DÉGRADÉE du vendredi — voir le branchement dans run().

    Sans m5_today (co-gé par Do2258EOD, donc absent le vendredi), le modèle (replay) n'a
    pas de chemin de prix → la décomposition Δ signal/coût/timing/micro est IMPOSSIBLE. On
    enregistre seulement le PnL réel de clôture (equity broker @22:54, déjà markée) pour la
    piste d'audit ; le gate « 3 jours inexpliqués » n'est PAS évalué (consec PRÉSERVÉ : un
    jour sans information ne casse ni n'étend une série inexpliquée).

    Garde anti-masquage : on ne dégrade QUE si (a) c'est un vendredi ET (b) la clôture a été
    réellement atteinte — state figé le jour J, après le rebalance 22:05 (ts >= 22:30 Paris,
    proche du gel ~22:54). Lun-jeu, ou EA mort tôt un vendredi → vraie absence d'EOD → on
    relève le RuntimeError d'origine (comportement inchangé, pas de masquage).

    Swap : la fenêtre du jour exclut le swap de CETTE nuit (posté ~23:00 = minuit serveur,
    APRÈS 22:54 comme après 22:58) ; sa vérification (×3 indices le vendredi) reste au
    superviseur (swap_drift_last_night, hors fenêtre) — le fallback 22:54 vs 22:58 ne
    déplace pas la frontière swap, il est swap-neutre.
    """
    absent = RuntimeError(f"snapshot EOD 22:58 absent pour {day} "
                          f"(eod.date={eod.get('date')}) — EA down avant 22:58 ?")
    if pd.Timestamp(day).dayofweek != 4:            # 4 = vendredi
        raise absent
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
    msg = (f"reconcile {day} (vendredi) DÉGRADÉ : snapshot EOD 22:58 absent par "
           f"construction (clôture forex 22:54, Do2258EOD non atteint) — fallback sur état "
           f"de clôture ({state['ts_paris']}, equity ${float(eq_close):,.2f}). Modèle/Δ non "
           f"rejoués (m5_today absent) ; PnL réel ${pnl_real:+.2f} enregistré, gate STOP non "
           f"évalué ce jour.")
    print(msg)

    prev = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame(columns=LOG_COLUMNS)
    consec = (int(prev.iloc[-1]["consec_unexplained"])
              if len(prev) and str(prev.iloc[-1]["date"]) != day else 0)
    row = dict(date=day, pnl_real=round(pnl_real, 2), pnl_model="", delta_total="",
               d_signal="", d_cost="", d_timing="", d_micro="", residual_usd=0.0,
               tol_usd="", unexplained=0, consec_unexplained=consec, stop_recommended=0,
               n_fills=int(len(fills)), detail_path="friday_degraded")
    statefiles.append_csv(LOG, LOG_COLUMNS, row)
    if alert:
        tg.send(f"🟦 FTMO live — {msg} Swap nuit (×3 indices) vérifié séparément par le "
                f"superviseur. Reprise lundi.")
    return row


def run(day: str = None, alert: bool = True) -> dict:
    files_dir = statefiles.mt5_files_dir()
    now = statefiles.now_paris().replace(tzinfo=None)
    day = day or str(now.date())

    state = statefiles.read_state(files_dir) or {}
    eod = state.get("eod") or {}
    if str(eod.get("date")) != day:
        # Snapshot EOD 22:58 absent. Le VENDREDI c'est STRUCTUREL : le forex ferme
        # ~22:54:59 Paris → plus de ticks → TimeCurrent() gèle → la grille EA
        # (book_executor.mq5:1517, hm>=2258) n'atteint jamais 22:58 → Do2258EOD ne
        # s'exécute PAS → ni le bloc state.eod NI m5_today.json (tous deux écrits par
        # Do2258EOD, mq5:1228-1229). Réconciliation dégradée (PnL réel seul) ; lun-jeu ou
        # vendredi sans clôture atteinte → vraie absence, on lève. Voir le helper.
        return _friday_degraded_reconcile(state, files_dir, day, eod, alert)
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

    mod = replay.replay_day(pd.Timestamp(day), phase, att, anchor, pos0, avg0,
                            weights, on_day, m5.get("legs", {}))

    eod_px = mod["eod_px"]
    pos_r, avg_r = _pos_vec(eod.get("positions", []))
    mtm_r = sum(pos_r[k] * (eod_px[l] / avg_r[k] - 1.0)
                for k, l in enumerate(LEGS)
                if pos_r[k] != 0.0 and np.isfinite(avg_r[k]) and np.isfinite(eod_px[l]))
    real_eq = float(eod["balance"]) + float(mtm_r)
    pnl_real = real_eq - anchor
    pnl_model = float(mod["model_equity"]) - anchor
    d_total = pnl_real - pnl_model

    # Conformance (Δ_signal) : cibles $ de l'EA (state.last_rebalance) vs cibles
    # modèle — métrique rapportée/alertée, PAS soustraite du résiduel (une vraie
    # divergence de politique DOIT rester inexpliquée pour déclencher le gate).
    d_signal = 0.0
    lr = state.get("last_rebalance") or {}
    mod_t4 = next((t for t in mod["trades"] if t["seg"] == 4), None)
    if lr and mod_t4:
        d_signal = sum(abs(float((lr.get("targets_usd") or {}).get(l, 0.0))
                           - float(mod_t4["tgt"].get(l, 0.0))) for l in LEGS)

    # Contributions réel−modèle :
    #   d_exec   = (req − fill)·dir·units      (slippage vs prix demandé)
    #   d_timing = (px_M5_seg − req)·dir·units (latence de décision, rebalance)
    #   d_costmb = +Σ coûts half-RT du modèle  (le modèle les a déduits ; côté
    #              réel ils vivent dans d_exec/d_timing vs le prix M5)
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
        upu = _usd_per_unit(state, f["symbol"])
        units = abs(lots) * upu
        turnover += abs(lots) * req * upu
        d_exec += (req - fill) * side * units
        if str(f["reason"]) == "rebalance" and leg and mod_t4:
            px_mod = mod_t4["px"].get(leg)
            if px_mod and np.isfinite(px_mod):
                d_timing += (px_mod - req) * side * units
    d_costmb = sum(float(t.get("cost_model_usd", 0.0)) for t in mod["trades"])
    d_cost = d_exec + d_costmb

    micro_real = 0.0
    mf = fills[fills["reason"].astype(str).str.startswith("micro")] if len(fills) else fills
    if len(mf):
        ent = mf[mf["reason"] == "micro_entry"]
        ext = mf[mf["reason"].isin(["micro_stop", "micro_be", "micro_time"])]
        if len(ent) and len(ext):
            e0, x0 = ent.iloc[0], ext.iloc[-1]
            side = 1.0 if str(e0["side"]).upper() == "BUY" else -1.0
            micro_real = (float(x0["fill_price"]) - float(e0["fill_price"])) * side \
                * float(e0["lots"]) * replay.US100_USD_PER_PT_PER_LOT
    d_micro = micro_real - float(mod["micro"]["pnl_usd"])

    gross_book = float(np.abs(pos0).sum())
    tol = 5.0 + 1e-4 * turnover + 0.5e-4 * gross_book
    residual = d_total - (d_cost + d_timing + d_micro)
    unexplained = bool(abs(residual) > tol)

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


def _usd_per_unit(state: dict, symbol: str) -> float:
    """$ par unité de prix par lot (tick_value/tick_size exporté par l'EA)."""
    specs = (state.get("symbol_specs") or {})
    s = specs.get(symbol) or specs.get(_leg_of(symbol) or "", {})
    tv, ts = float(s.get("tick_value", 0)), float(s.get("tick_size", 0))
    if tv > 0 and ts > 0:
        return tv / ts
    leg = _leg_of(symbol)
    return {"XAUUSD": 100.0, "USDJPY": 100000.0 / max(float(s.get("price", 145.0)), 1e-9),
            "US100": 1.0, "GER40": 1.0}.get(leg, 1.0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--no-alert", action="store_true")
    a = ap.parse_args(argv)
    try:
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
