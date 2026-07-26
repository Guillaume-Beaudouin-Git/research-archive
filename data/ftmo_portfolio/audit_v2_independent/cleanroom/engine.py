"""CLEAN-ROOM FTMO 2-step funnel simulator — independent audit implementation.

Written from the v2 report spec (sections 2.2 / 2.3 / 5.3) + official-rule notes
(logs/phase0_rules.md) + audited data caches ONLY. Author engine read as
reference but no code imported/copied; accounting derived from first principles.

Rules implemented:
  daily loss: equity >= balance@00:00 CET - 5% * initial (checked on M5 grid)
  max loss:   equity >= 90% * initial (static floor)
  targets:    P1 +10% / P2 +5% on BALANCE with all positions closed
  min 4 trading days (>=1 position opened) per phase
  schedule:   09:00 GER40 off / 15:30 US100 off / 17:35 GER40 on (Mon,Tue)
              22:05 trend rebalance + US100 on (Mon,Tue)
  governor:   scale = vm * taper(2% to floor) * glide(0.5 past 80% progress)
              * pace(clip(1+behind,0.8,2.0)) ; per-leg pre-vm cap 1.5x equity
  margin cap: sum(|notional|*rate) <= 60% equity, rates XAU/US100/GER40 2%, FX 1%
  breaker:    flatten at M5 bar where equity < limit + 30% * daily budget
  abandon:    5 consecutive EOD with equity < floor + 2% -> abandon (retryable)
  funnel:     P1 -> 3 business days gap -> P2 (vm x1.2); bust/abandon -> retry
              after 2 business days; wall clock 91 calendar days
  ORB:        synthetic sleeve, risk 0.25% * initial * taper0; R posted at 22:05;
              constant adverse dip 1.31R held against rules 15:30->22:05
  accounting: balance vs equity; signed $ notional; avg price (harmonic on adds);
              realized P&L on reductions; half-RT bps cost on |delta notional|;
              swaps posted nightly EOD (panel bps/night x triple-day multiplier);
              lot quantization 0.01 against current price.
"""
from pathlib import Path
import numpy as np
import pandas as pd

PKG = Path(__file__).resolve().parents[2]      # data/ftmo_portfolio
CACHE = PKG / "cache"
AOUT = PKG / "outputs"

INIT = 10_000.0
DAILY_BUDGET = 0.05 * INIT
FLOOR = 0.90 * INIT
TARGET1, TARGET2 = 0.10, 0.05


def breaker_line(bal, cfg, initial=None):
    """Miroir de book_executor.mq5 BreakerLine(). Deux sémantiques d'EA :

      brk_mode "static" (DÉFAUT, EA v2.2 gelé) : max(daily, statique) + frac x budget.
        Sous balance = statique + budget ($9,500 sur 10k) le max() bascule sur le
        statique et la ligne SE FIGE ($9,150) : cliquet unidirectionnel, la room ne
        repousse jamais -> état absorbant (AUDIT.md F5(b)).

      brk_mode "daily" (EA v2.4 déployé 2026-07-20) : daily seul, la ligne se réancre
        chaque matin avec l'ancre, donc se réarme toujours ; le max drawdown redevient
        la mort naturelle qu'on laisse advenir.

    Le DÉFAUT reste "static" pour que tout résultat v2.2 pinné se reproduise à
    l'identique. La limite dure de BUST, elle, reste max(daily, statique) dans les
    deux modes — on breache sous l'une OU l'autre barrière (sémantique FTMO)."""
    init = INIT if initial is None else initial
    budget = DAILY_BUDGET / INIT * init
    limit = bal - budget
    if cfg.get("brk_mode") == "daily":
        if bal <= 0.0:                      # garde ancre corrompue (miroir EA)
            return FLOOR / INIT * init + cfg["breaker"] * budget
        return limit + cfg["breaker"] * budget
    return max(limit, FLOOR / INIT * init) + cfg["breaker"] * budget
MIN_OPEN_DAYS = 4
LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]
MRATE = np.array([0.02, 0.01, 0.02, 0.02])          # Standard-account (1:50) — DÉFAUT historique
# Taux de marge réels du compte SWING FTMO (1:15 / USDJPY 1:30), lus serveur 2026-07 (essai4
# live_specs). Le sim historique supposait Standard (2%) → cap 60% mordait ~2× moins qu'en live,
# donc le sim SUR-dimensionnait les jambes ON. Passé via cfg["mrate"] (défaut = MRATE Standard →
# non-régression préservée). Recalibration mesurée : p single 30→27%, campagne 93→83%.
MRATE_SWING = [0.066667, 0.033334, 0.066667, 0.066667]
LOT_UNITS = np.array([100.0, 100_000.0, 1.0, 1.0])   # contract size per 1.0 lot
VSTEP = 0.01
SCHED_MIN = [9 * 60, 15 * 60 + 30, 17 * 60 + 35, 22 * 60 + 5]
EPS_T = 2e-4


# ---------------------------------------------------------------- data layer
def load_market(swap_mul=1.0, spread_mul=1.0, start="2013-10-01"):
    """Audited stack, rebuilt independently: repaired M5 + GER40 hole mask +
    swap panels + RT costs + era-costed ORB ledger."""
    m5 = pd.read_parquet(CACHE / "sim_m5_repaired.parquet").loc[start:]
    m5 = m5.ffill()
    # GER40 hole mask from RAW (pre-repair) file, rule: <50 bars/day, 2018-2021
    raw_g = pd.read_parquet(CACHE / "sim_m5.parquet")["GER40"]
    w = raw_g.loc["2018":"2021"].dropna()
    per_day = w.groupby(w.index.date).size()
    holes = {d.date() for d in pd.bdate_range("2018-01-01", "2021-12-31")
             if per_day.get(d.date(), 0) < 50}
    day_of = pd.Series(m5.index.date, index=m5.index)
    m5.loc[day_of.isin(holes).values, "GER40"] = np.nan

    sL = pd.read_parquet(CACHE / "panel_swapL.parquet")[LEGS] * swap_mul
    sS = pd.read_parquet(CACHE / "panel_swapS.parquet")[LEGS] * swap_mul
    mu = pd.read_parquet(CACHE / "panel_mult.parquet")[LEGS]
    rt = pd.read_csv(AOUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]
    rt = rt.reindex(LEGS).to_numpy(float) * spread_mul

    days, dates = [], []
    minutes = m5.index.hour * 60 + m5.index.minute
    for d, g in m5.groupby(m5.index.date):
        if len(g) < 30:
            continue
        px = g.to_numpy(float)
        mins = (g.index.hour * 60 + g.index.minute).to_numpy()
        bounds = [int(np.searchsorted(mins, t, side="left")) for t in SCHED_MIN]
        days.append((px, bounds))
        dates.append(pd.Timestamp(d))
    dates = pd.DatetimeIndex(dates)
    swL = sL.reindex(dates).fillna(0.0).to_numpy(float)
    swS = sS.reindex(dates).fillna(0.0).to_numpy(float)
    mlt = mu.reindex(dates).fillna(1.0).to_numpy(float)
    orb = pd.read_parquet(CACHE / "orb_e7_Rera.parquet")["R"]
    orb_R = orb.reindex(dates).fillna(0.0).to_numpy(float)
    return dict(days=days, dates=dates, swL=swL, swS=swS, mult=mlt, rt=rt,
                orb_R=orb_R, n=len(dates))


# ------------------------------------------------------------- signal layer
def _rv(ret, window=60):
    return ret.rolling(window, min_periods=max(20, window // 3)).std() * np.sqrt(252)


def build_signals(carry_adj=True, theta=0.34, lookbacks=(60, 120, 250)):
    """Rebuild WT (gold blend + J1) and ON from panel data — own implementation."""
    px = pd.read_parquet(CACHE / "panel_px.parquet")
    rets = pd.read_parquet(CACHE / "panel_rets.parquet")
    sL = pd.read_parquet(CACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(CACHE / "panel_swapS.parquet")
    mu = pd.read_parquet(CACHE / "panel_mult.parquet")
    rt = pd.read_csv(AOUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]

    # --- gold: blended sign TSMOM on carry-adjusted total return
    p = px["XAUUSD"].dropna()
    if carry_adj:
        tr = np.log(p).diff() + sL["XAUUSD"].reindex(p.index).fillna(0) / 1e4
        base = np.exp(tr.cumsum())
    else:
        base = p
    sig = sum(np.sign(base / base.shift(L) - 1.0) for L in lookbacks) / len(lookbacks)
    sig = sig.where(sig.abs() >= theta, 0.0).reindex(rets.index)
    rv = _rv(rets["XAUUSD"]).clip(lower=1e-4)
    w = (sig * (0.10 / rv).clip(upper=5.0)).shift(1)
    # NaN day -> 0 book return (author pipeline's de-facto semantics via
    # DataFrame.sum; audit finding: holidays enter vol windows as zeros)
    raw = (w * rets["XAUUSD"]).fillna(0.0)
    bvol = raw.rolling(60).std().shift(1) * np.sqrt(252)
    scale = (0.10 / bvol.clip(lower=1e-4)).clip(upper=10.0)
    v20 = raw.rolling(20).std().shift(1) * np.sqrt(252)
    scale = scale * np.minimum(1.0, 0.10 / v20.clip(lower=1e-4))
    pos = w * scale
    # equity-curve gate (author pipeline component; flagged in audit as
    # undocumented in the report spec) - replicate to test computation
    net = (pos * rets["XAUUSD"]).fillna(0.0)
    net = net - (pos.diff().abs() * (rt["XAUUSD"] / 2.0 / 1e4)).fillna(0.0)
    bps = np.where(pos > 0, sL["XAUUSD"], np.where(pos < 0, sS["XAUUSD"], 0.0))
    net = net + (pos.abs() * bps / 1e4 * mu["XAUUSD"]).fillna(0.0)
    eq = (1 + net.fillna(0)).cumprod()
    gate = (eq > eq.rolling(100).mean()).astype(float).replace(0.0, 0.4).shift(1)
    w_gold = (pos * gate.fillna(1.0)).clip(-1.5, 1.5)

    # --- J1: USDJPY 12-1 long-only
    pj = px["USDJPY"].dropna()
    mom = pj.shift(21) / pj.shift(252) - 1.0
    sj = (mom > 0).astype(float)
    rvj = _rv(rets["USDJPY"]).clip(lower=1e-4)
    w_jpy = (sj * (0.10 / rvj).clip(upper=5.0)).shift(1).clip(-1.5, 1.5)

    WT = pd.DataFrame({"XAUUSD": w_gold, "USDJPY": w_jpy}).fillna(0.0)
    ON = pd.Series(0.0, index=WT.index)
    ON[WT.index.dayofweek.isin([0, 1])] = 1.0
    return WT, ON


def align_signals(M, WT, ON):
    WTa = WT.reindex(M["dates"]).fillna(0.0).to_numpy(float)
    ONa = ON.reindex(M["dates"]).fillna(0.0).to_numpy(float)
    return WTa, ONa


# ------------------------------------------------------------ account layer
def _quantize(target, prices):
    out = np.zeros(4)
    for k in range(4):
        step = (LOT_UNITS[k] if LEGS[k] == "USDJPY" else LOT_UNITS[k] * prices[k]) * VSTEP
        if np.isfinite(step) and step > 0:
            out[k] = np.round(target[k] / step) * step
    return out


def _mtm(pos, avg, prices):
    tot = 0.0
    for k in range(4):
        if pos[k] != 0.0 and np.isfinite(avg[k]) and np.isfinite(prices[k]):
            tot += pos[k] * (prices[k] / avg[k] - 1.0)
    return tot


def _trade_to(pos, avg, bal, target, prices, rt):
    """Move position vector to target at given prices. Returns new balance.
    Cost: half-RT bps on |delta|. Realize P&L on reductions/flips. Average
    entry price updated harmonically on adds (return-space accounting)."""
    for k in range(4):
        t, o, p = target[k], pos[k], prices[k]
        if abs(t - o) < 1e-9:
            continue
        if not np.isfinite(p):
            continue
        bal -= abs(t - o) * (rt[k] / 2.0) / 1e4
        if o != 0.0:
            if t == 0.0 or t * o < 0:
                bal += o * (p / avg[k] - 1.0)            # close everything
            elif abs(t) < abs(o):
                bal += (o - t) * (p / avg[k] - 1.0)      # partial reduce
        if t == 0.0:
            avg[k] = np.nan
        elif o == 0.0 or t * o < 0:
            avg[k] = p
        elif abs(t) > abs(o):
            inv = (abs(o) / abs(t)) / avg[k] + (1 - abs(o) / abs(t)) / p
            avg[k] = 1.0 / inv
        pos[k] = t
    return bal


def _flat(pos, avg, bal, prices, rt):
    return _trade_to(pos, avg, bal, np.zeros(4), prices, rt)


# --------------------------------------------------------------- one phase
def run_phase(M, i0, WT, ON, cfg, diag=None):
    """One evaluation phase from a fresh account at day i0."""
    bal = INIT
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    target = INIT * (1 + cfg["target"])
    open_days = 0
    zombie = 0
    vm = cfg["vm"]
    gap_k = cfg.get("gap_stress", 1.0)
    i = i0
    while i < M["n"]:
        di = i - i0
        if cfg.get("max_cal") and (M["dates"][i] - M["dates"][i0]).days > cfg["max_cal"]:
            px_last = M["days"][i - 1][0][-1]
            return dict(out="timeout", end=bal + _mtm(pos, avg, px_last),
                        last=i, used=di)
        limit = bal - DAILY_BUDGET
        lim_eff = max(limit, FLOOR)          # limite dure de BUST (inchangée)
        brk_line = breaker_line(bal, cfg)    # v2.4 (A) : dépend de cfg["brk_mode"]
        px_day, bounds = M["days"][i]
        T = len(px_day)
        cuts = [0] + bounds + [T]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        flat_today = False
        opened = False
        day_min_eq = np.inf
        # gap stress (rule-check only): amplified day-open jump on held legs
        gap_extra = 0.0
        if gap_k != 1.0 and i > i0 and np.any(pos):
            prev_close = M["days"][i - 1][0][-1]
            op = px_day[0]
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(prev_close[k]) and np.isfinite(op[k]):
                    gap_extra += (gap_k - 1.0) * pos[k] * (op[k] / prev_close[k] - 1.0)
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b:
                # segment empty; still apply scheduled actions at next segment
                pass
            seg = px_day[a:b]
            if s == 4 and orb_live:
                bal += orb_risk * M["orb_R"][i]
                opened = True
                orb_live = False
            dip = 1.31 * orb_risk if (orb_live and s in (2, 3)) else 0.0
            if not flat_today and len(seg) > 0:
                tgt, did_open = _target_for_segment(s, i, M, WT, ON, cfg, bal,
                                                    pos, avg, seg[0], i0, vm)
                if tgt is not None:
                    bal = _trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
                    opened = opened or did_open
            if len(seg) == 0:
                continue
            # vectorized equity path
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    ok = np.isfinite(col)
                    contrib = np.where(ok, (col / avg[k] - 1.0) * pos[k], 0.0)
                    pl += contrib
            eq = bal + pl - dip
            eq_chk = eq + gap_extra
            hit_bust = eq_chk < lim_eff
            # v2.4 : l'EA conditionne le breaker à OurPositionsExist() — sans
            # position il ne flatte pas et ne latche donc PAS flat_today, il
            # rouvre au rebalance suivant. Le défaut (False) garde la sémantique
            # v2.2 du sim, qui latchait à plat et figeait le compte en zombie inerte.
            hit_brk = (eq_chk < brk_line)
            if cfg.get("brk_needs_pos") and not np.any(pos):
                hit_brk = hit_brk & False
            hit_tgt = eq >= target * (1 + EPS_T)
            tb = int(np.argmax(hit_bust)) if hit_bust.any() else len(seg)
            tk = int(np.argmax(hit_brk)) if hit_brk.any() else len(seg)
            th = int(np.argmax(hit_tgt)) if hit_tgt.any() else len(seg)
            first = min(tb, tk, th)
            day_min_eq = min(day_min_eq, float(eq[:min(first + 1, len(seg))].min()))
            if first < len(seg):
                if tb <= min(tk, th):
                    e = eq_chk[tb]
                    if diag is not None:
                        diag.append(dict(date=M["dates"][i], seg=s, bar=tb,
                                         kind="bust", day_first_bar=(s == 0 and tb == 0),
                                         eq=e))
                    return dict(out="bust_daily" if e >= FLOOR else "bust_floor",
                                end=e, last=i, used=di + 1)
                if th <= tk:
                    bal = _flat(pos, avg, bal, seg[th], M["rt"])
                    if bal >= target and open_days + (1 if opened else 0) >= MIN_OPEN_DAYS:
                        return dict(out="pass", end=bal, last=i, used=di + 1)
                    flat_today = True
                else:
                    fill = seg[tk].copy()
                    kslip = cfg.get("brk_slip", 0.0)
                    if kslip > 0.0 and tk > 0:
                        rng = np.abs(seg[tk] - seg[tk - 1])
                        fill = fill - np.sign(pos) * kslip * rng
                    bal = _flat(pos, avg, bal, fill, M["rt"])
                    if diag is not None:
                        diag.append(dict(date=M["dates"][i], seg=s, bar=tk,
                                         kind="breaker", day_first_bar=(s == 0 and tk == 0),
                                         eq=eq_chk[tk]))
                    flat_today = True
                    if bal < FLOOR:
                        return dict(out="bust_floor", end=bal, last=i, used=di + 1)
                    if bal < limit:
                        return dict(out="bust_daily", end=bal, last=i, used=di + 1)
        if cfg.get("day_log") and np.isfinite(day_min_eq):
            DAY_LOG.append(dict(date=M["dates"][i],
                                worst_dpl=day_min_eq - (limit + DAILY_BUDGET),
                                headroom=day_min_eq - lim_eff))
        # end of day: swaps on held notional
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        if opened:
            open_days += 1
        if not np.any(pos) and bal >= target and open_days >= MIN_OPEN_DAYS:
            return dict(out="pass", end=bal, last=i, used=di + 1)
        eq_eod = bal + _mtm(pos, avg, px_day[-1])
        zombie = zombie + 1 if eq_eod < FLOOR + cfg.get("ab_buf", 0.0) * INIT else 0
        if zombie >= cfg.get("ab_days", 10 ** 9):
            return dict(out="abandon", end=eq_eod, last=i, used=di + 1)
        # audit fix option: a rational trader above target with <4 open days
        # just opens a token 0.01-lot trade to tick the day counter
        # (escapes the flatten-deadlock artifact; ~$1 nominal cost)
        if (cfg.get("fix_deadlock") and flat_today and not np.any(pos)
                and bal >= target and open_days < MIN_OPEN_DAYS and not opened):
            open_days += 1
            bal -= 1.0
            if bal >= target and open_days >= MIN_OPEN_DAYS:
                return dict(out="pass", end=bal, last=i, used=di + 1)
        i += 1
    px_last = M["days"][M["n"] - 1][0][-1]
    return dict(out="timeout", end=bal + _mtm(pos, avg, px_last),
                last=M["n"] - 1, used=M["n"] - i0)


MARGIN_LOG = []          # (need/eq pre-cap) when cfg["margin_log"] set
DAY_LOG = []             # per-day dicts when cfg["day_log"] set


def _target_for_segment(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm):
    eq = bal + _mtm(pos, avg, px0)
    room = (eq - FLOOR) / INIT
    taper = float(np.clip(room / cfg["taper"], 0.0, 1.0))
    prog = (eq / INIT - 1.0) / cfg["target"]
    glide = cfg.get("glide", 1.0) if prog > 0.8 else 1.0
    pace = 1.0
    if cfg.get("pace") and cfg.get("max_cal"):
        frac_t = (M["dates"][i] - M["dates"][i0]).days / cfg["max_cal"]
        pace = float(np.clip(1.0 + cfg.get("pace_k", 1.0) * (frac_t - max(prog, 0.0)),
                             0.8, 2.0))
    scale = vm * taper * glide * pace
    tgt = None
    opened = False
    if s == 1 and pos[3] != 0.0:                      # 09:00 GER40 off
        tgt = pos.copy(); tgt[3] = 0.0
    elif s == 2 and pos[2] != 0.0:                    # 15:30 US100 off
        tgt = pos.copy(); tgt[2] = 0.0
    elif s == 3 and ON[i] > 0:                        # 17:35 GER40 on
        tgt = pos.copy()
        tgt[3] = cfg["on_w"] * scale * eq
        opened = True
    elif s == 4:                                      # 22:05 rebalance
        tgt = pos.copy()
        tgt[0] = WT[i, 0] * scale * eq
        tgt[1] = WT[i, 1] * scale * eq
        tgt[2] = cfg["on_w"] * scale * eq if ON[i] > 0 else 0.0
        opened = bool(abs(tgt[0]) > 0 or abs(tgt[1]) > 0 or tgt[2] > 0)
    if tgt is None:
        return None, False
    # --- overlay risque v2.8 : cap de NOTIONNEL par jambe, AVANT le cap marge ---
    # Le cap marge est libellé en MARGE : 0.60/0.03333 = 18.05x pour USDJPY contre
    # 9.0x pour les jambes à 6.667% -> la jambe au pire skew reçoit 2x l'allocation.
    # Unité = notionnel/equity, donc INVARIANTE EN vm (ne pas confondre avec
    # LEG_CAP_PRE_VM côté EA, garde-fou anti-lot-aberrant qui, lui, suit vm).
    # Appliqué AVANT le cap marge : écrêter J1 libère de la marge pour les autres
    # jambes au lieu de les raboter proportionnellement.
    # Défaut None => NO-OP STRICT : aucun chiffre pinné v2.2 ne bouge.
    # s in (3, 4) UNIQUEMENT — les segments qui POSENT du risque et qui, côté EA,
    # passent par CapQuantizeTrade (Do1735, Do2205Rebalance). s=1 (09:00 GER40 off)
    # et s=2 (15:30 US100 off) sont des FERMETURES mono-jambe : l'EA y appelle
    # TradeLegTo directement, et lib/replay.py construit la cible en ligne — aucun
    # des deux ne clippe. Clipper ici écrêterait la position J1 DÉTENUE dans le
    # seul sim : le modèle couperait un levier que le live garderait, précisément
    # dans l'état de drawdown que le cap doit couvrir, et replay.py reproduisant
    # l'EA, le reconcile ne le verrait JAMAIS. (Audit indépendant 2026-07-26.)
    llc = cfg.get("leg_lev_cap")
    if llc is not None and eq > 0 and s in (3, 4):
        # `llc[k] and llc[k] > 0` = miroir EXACT du garde `lc>0` de l'EA. Couvre
        # None, 0 (l'EA et make_spec_mqh encodent "pas de cap" par 0 : les #define
        # MQL5 n'ont pas de None), les NÉGATIFS (une coquille yaml -12.0
        # inverserait le signe de la cible ici alors que l'EA l'ignorerait) et NaN.
        for k in range(4):
            if llc[k] and llc[k] > 0 and abs(tgt[k]) > llc[k] * eq:
                tgt[k] = llc[k] * eq if tgt[k] > 0 else -llc[k] * eq
    mcap = cfg.get("margin_cap")
    if mcap is not None and eq > 0:
        need = float(np.abs(tgt) @ cfg.get("mrate", MRATE))   # cfg["mrate"]=MRATE_SWING pour le live-fidèle
        if cfg.get("margin_log") and (abs(tgt).sum() > 0):
            MARGIN_LOG.append(need / eq)
        if need > mcap * eq:
            tgt = tgt * (mcap * eq / need)
    tgt = _quantize(tgt, px0) if cfg.get("quantize", True) else tgt
    return tgt, opened


# ------------------------------------------------------------------ funnel
def run_funnel(M, i0, WT, ON, cfg, wall=91, gap_bd=3, retry_bd=2, diag=None):
    start = M["dates"][i0]
    i = i0
    attempts = 0
    while True:
        if (M["dates"][min(i, M["n"] - 1)] - start).days > wall or i >= M["n"] - 5:
            return dict(funded=False, attempts=attempts, t=np.nan)
        attempts += 1
        c1 = dict(cfg, target=TARGET1, max_cal=wall)
        r1 = run_phase(M, i, WT, ON, c1, diag=diag)
        if r1["out"] == "pass":
            j = min(r1["last"] + gap_bd, M["n"] - 1)
            if (M["dates"][j] - start).days > wall:
                return dict(funded=False, attempts=attempts, t=np.nan)
            c2 = dict(cfg, target=TARGET2, max_cal=wall,
                      vm=cfg["vm"] * cfg.get("p2_mult", 1.0))
            r2 = run_phase(M, j, WT, ON, c2, diag=diag)
            if r2["out"] == "pass":
                t = (M["dates"][r2["last"]] - start).days
                if t <= wall:
                    return dict(funded=True, attempts=attempts, t=t)
                return dict(funded=False, attempts=attempts, t=np.nan)
            if r2["out"] == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan)
            i = min(r2["last"] + retry_bd, M["n"] - 1)
        else:
            if r1["out"] == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan)
            i = min(r1["last"] + retry_bd, M["n"] - 1)


CFG_V2 = dict(vm=14.0, p2_mult=1.2, on_w=0.6, orb_risk=0.0025,
              breaker=0.30, taper=0.02, glide=0.5, pace=1, pace_k=1.0,
              ab_buf=0.02, ab_days=5, margin_cap=0.60, quantize=True)


def cohort_starts(M, lo, hi, step=7):
    idx = M["dates"]
    sel = np.where((idx >= lo) & (idx <= hi))[0]
    return sel[::step]
