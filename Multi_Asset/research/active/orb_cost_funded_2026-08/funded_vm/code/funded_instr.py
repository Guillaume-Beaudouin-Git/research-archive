"""Clone INSTRUMENTÉ de engine_v22.run_funded — observation seule.

Aucune modification de la source : ce fichier RECOPIE la boucle de
`data/ftmo_portfolio/v22/engine_v22.py:run_funded` (lignes 257-320) et n'ajoute que
des compteurs. L'équivalence stricte avec l'original est prouvée par
`check_equiv()` sur toutes les cohortes des deux fenêtres funded (sortie
identique sur wd / payouts / life / busted / residual).

Ajouts (aucun effet sur la trajectoire) :
  bust_kind   "daily" si l'équité au bust reste >= FLOOR (barrière -5% du jour),
              "floor" sinon (max-loss statique $9,000)
  bust_date, bust_bal0 (balance d'ouverture du jour), bust_dayloss ($)
  n_brk       nombre de déclenchements du breaker
  periods     nombre de checkpoints de retrait atteints (life // wd_every)
"""
import sys
from pathlib import Path
import numpy as np

ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "data" / "ftmo_portfolio" / "v22"))
import engine_v22 as V          # noqa: E402
E = V.E
INIT, FLOOR, BUDGET = V.INIT, V.FLOOR, V.BUDGET


def run_funded_instr(M, i0, WT, ON, cfg, horizon=504, wd_every=14):
    bal = INIT
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    total_wd, n_pay, days = 0.0, 0, 0
    n_brk = 0
    i = i0
    while i < M["n"] and days < horizon:
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = E.breaker_line(bal, cfg)
        px_day, bounds = M["days"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        flat_today = False
        bal0 = bal                                     # instrumentation
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b:
                continue
            seg = px_day[a:b]
            if s == 4 and orb_live:
                bal += orb_risk * M["orb_R"][i]
                orb_live = False
            dip = 1.31 * orb_risk if (orb_live and s in (2, 3)) else 0.0
            if not flat_today:
                tgt, _ = E._target_for_segment(s, i, M, WT, ON, cfg, bal, pos,
                                               avg, seg[0], i0, cfg["vm"])
                if tgt is not None:
                    bal = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            bad = eq < lim_eff
            brk = eq < brk_line
            if cfg.get("brk_needs_pos") and not np.any(pos):
                brk = brk & False
            tb = int(np.argmax(bad)) if bad.any() else len(seg)
            tk = int(np.argmax(brk)) if brk.any() else len(seg)
            if min(tb, tk) < len(seg):
                if tb <= tk:
                    e = float(eq[tb])
                    return dict(wd=total_wd, payouts=n_pay, life=days,
                                busted=True, residual=0.0,
                                bust_kind="daily" if e >= FLOOR else "floor",
                                bust_date=M["dates"][i], bust_bal0=bal0,
                                bust_dayloss=bal0 - e, bust_eq=e,
                                n_brk=n_brk, periods=days // wd_every)
                bal = E._flat(pos, avg, bal, seg[tk], M["rt"])
                n_brk += 1
                flat_today = True
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        days += 1
        i += 1
        if days % wd_every == 0 and bal > INIT:
            total_wd += bal - INIT
            n_pay += 1
            bal = INIT
    px_last = M["days"][min(i, M["n"] - 1)][0][-1]
    res = max(bal + E._mtm(pos, avg, px_last) - INIT, 0.0)
    return dict(wd=total_wd, payouts=n_pay, life=days, busted=False, residual=res,
                bust_kind="", bust_date=None, bust_bal0=np.nan,
                bust_dayloss=np.nan, bust_eq=np.nan,
                n_brk=n_brk, periods=days // wd_every)


KEYS = ("wd", "payouts", "life", "busted", "residual")


def check_equiv(M, WT, ON, cfg, starts, horizon=504, wd_every=14):
    """Équivalence stricte clone vs source, cohorte par cohorte."""
    ok = bad = 0
    diffs = []
    for i0 in starts:
        a = V.run_funded(M, int(i0), WT, ON, cfg, horizon=horizon, wd_every=wd_every)
        b = run_funded_instr(M, int(i0), WT, ON, cfg, horizon=horizon, wd_every=wd_every)
        same = all(
            (abs(a[k] - b[k]) < 1e-9) if isinstance(a[k], float) else (a[k] == b[k])
            for k in KEYS)
        if same:
            ok += 1
        else:
            bad += 1
            diffs.append((int(i0), {k: (a[k], b[k]) for k in KEYS if a[k] != b[k]}))
    return ok, bad, diffs
