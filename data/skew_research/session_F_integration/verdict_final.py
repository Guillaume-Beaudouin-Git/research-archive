#!/usr/bin/env python3
"""session_F_integration — FINAL VERDICT with the MEASURED crypto swap.
Gate collapsed from low/mid/high to ONE point: BTCUSD demo FTMO interest %/yr mode,
long -30 AND short -30 => ~-30%/yr ~= 8.3 bps/night, SYMMETRIC, Friday x3 (=>~58 bps/wk
held, NOT 7x8.3 naive), commission 6.5 bps RT. Swap charged on HELD NOTIONAL per leg
(L33), day-multiplier-weighted, both-directions. Circuit-breaker -3% KEEP (+5pp).
Phase 2 (if NO-GO): crypto ablation, two-sided per class (L25), matched-leverage (L19)."""
import numpy as np, pandas as pd, warnings, sys
warnings.filterwarnings("ignore")
sys.path.insert(0, "/sessions/affectionate-epic-faraday/mnt/data/ftmo_research/tsmom")
from tsmom_engine import load_basket
D = "/sessions/affectionate-epic-faraday/mnt/data"; OUT = f"{D}/skew_research/session_F_integration"
INIT, P1, P2, FLOOR, DCAP = 1e4, 1.10, 1.05, 9e3, 0.05
INST = ["US500", "GLD", "SLV", "USO", "BTC", "ETH"]

# --- MEASURED per-leg swap rates (bps of notional / NIGHT, both-directions) ---
# crypto BTC measured -30%/yr ~ 8.3; ETH default -30% (8.3), sensitivity -45% (12.3, non-BTC heavier)
# non-crypto from session_E model: indices 2.5 / metals 3.5 / oil 4.0
RATE = dict(US500=2.5, GLD=3.5, SLV=3.5, USO=4.0, BTC=8.3, ETH=8.3)
CRYPTO = {"BTC", "ETH"}
COMM_RT = 6.5            # commission bps round-trip -> 3.25/side on one-way turnover


def day_mult(idx, crypto_leg):
    """Triple-swap day multiplier on a TRADING-day series (accounts for weekend via the
    triple day; weekly = 4x1 + 1x3 = 7x rate ~ 58bps for crypto, NOT 7x8.3 phantom rows).
    Crypto triple = Friday (measured); non-crypto triple = Wednesday (MT5 standard)."""
    wd = idx.weekday  # Series of weekday ints
    triple = 4 if crypto_leg else 2
    return np.where(wd == triple, 3.0, 1.0)


def engine_net(px, inst, eth_rate=8.3, comm_rt=COMM_RT, lookbacks=(60, 120, 250), theta=0.34, port_vol=0.10):
    """TSMOM net of MEASURED day-weighted per-leg swap on held notional + commission.
    Returns (net_series, diag dict)."""
    rate = dict(RATE); rate["ETH"] = eth_rate
    px = px[inst].dropna(how="all"); rets = px.pct_change().clip(-0.5, 0.5)
    rv = rets.rolling(60).std() * np.sqrt(252)
    sig = sum(np.sign(px.pct_change(L)) for L in lookbacks) / len(lookbacks)
    sig = sig.where(sig.abs() >= theta, 0.0)
    pos = (sig * (0.10 / rv).clip(upper=5.0)).shift(1)               # per-inst vol-targeted weight
    gross = (pos * rets).sum(1)
    scale = (port_vol / (gross.rolling(60).std() * np.sqrt(252))).clip(upper=3.0).shift(1)
    port = (gross * scale).fillna(0.0) - pos.diff().abs().sum(1) * (comm_rt / 2) * 1e-4   # commission (RT/2 per side)
    mult_vd = (port_vol / (port.rolling(20).std() * np.sqrt(252))).clip(upper=1.0).shift(1).fillna(1.0)
    port = port * mult_vd
    eqc = (1 + port).cumprod(); g = (eqc > eqc.rolling(100).mean()).astype(float).shift(1).fillna(1.0)
    mult_eg = 0.4 + 0.6 * g
    port = port * mult_eg
    Stot = (scale.fillna(0.0) * mult_vd * mult_eg)                   # total book scaling at L=1
    # --- day-weighted per-leg swap on held notional ---
    swap = pd.Series(0.0, index=px.index); legdrag = {}
    wd = pd.Series(px.index.weekday, index=px.index)
    for c in inst:
        notion = pos[c].abs() * Stot                                # |notional| of leg c at L=1
        mult = np.where(wd == (4 if c in CRYPTO else 2), 3.0, 1.0)   # triple day
        leg_swap = notion * (rate[c] * 1e-4) * mult
        swap += leg_swap
        legdrag[c] = float(leg_swap.dropna().mean() * 252 * 100)     # ann drag % of this leg
    net = (port - swap).dropna()
    nz = net[net != 0]
    diag = dict(sharpe=round(net.mean() / nz.std() * np.sqrt(252), 2),
                ann=round(net.mean() * 252 * 100, 1),
                swap_drag_yr=round(swap.dropna().mean() * 252 * 100, 2),
                maxdd=round((( (1+net).cumprod() / (1+net).cumprod().cummax()) - 1).min() * 100, 1),
                legdrag={k: round(v, 2) for k, v in legdrag.items()},
                wk_crypto_bps=round((RATE["BTC"] * 7), 1))           # sanity: 7x rate = weekly
    return net, diag


def vol_scale(s, tgt=0.10):
    return s * (tgt / (s[s != 0].std() * np.sqrt(252)))


def build_book(net_ts, macd_swap=3.5, seas_swap=3.5):
    """equal-risk book: net-TSMOM(measured swap) + MACD + seasonal. MACD/seasonal charged a
    CONSERVATIVE FLAGGED non-crypto overnight haircut (bps/trading-day on vol-scaled notional)."""
    macd = pd.read_csv(f"{D}/skew_research/session_basic_trend/setup_daily_series.csv", index_col=0, parse_dates=True)["MACD cross"]
    seas = pd.read_csv(f"{D}/skew_research/session_basic_trend/commodity_seasonality_oos.csv", index_col=0, parse_dates=True).iloc[:, 0]
    sleeves = [vol_scale(net_ts),
               (vol_scale(macd) - macd_swap * 1e-4),
               (vol_scale(seas) - seas_swap * 1e-4)]
    M = pd.concat(sleeves, axis=1).dropna()
    return M.mean(axis=1).dropna()


def fp_decomp(sr, L, cap=1260, step=3, daily_cb=None):
    N = len(sr); st = np.arange(0, N - 5, step)
    pas = bd = bt = run = 0; ttf = []
    for a in st:
        eq, i, end, res = INIT, a, min(a + cap, N), None
        while i < end:
            c = L * sr[i]
            if daily_cb is not None and c < -daily_cb: c = -daily_cb
            if c <= -DCAP: res = "bd"; break
            eq *= 1 + c
            if eq < FLOOR: res = "bt"; break
            if eq >= INIT * P1: res = "p1"; break
            i += 1
        if res == "bd": bd += 1; continue
        if res == "bt": bt += 1; continue
        if res != "p1": run += 1; continue
        d1 = i - a; eq = INIT; i += 1
        while i < end:
            c = L * sr[i]
            if daily_cb is not None and c < -daily_cb: c = -daily_cb
            if c <= -DCAP: bd += 1; res = "x"; break
            eq *= 1 + c
            if eq < FLOOR: bt += 1; res = "x"; break
            if eq >= INIT * P2: pas += 1; ttf.append(i - a); res = "x"; break
            i += 1
        if res != "x": run += 1
    n = len(st)
    return dict(p_pass=round(pas/n, 3), bust_daily=round(bd/n, 3), bust_total=round(bt/n, 3),
                run=round(run/n, 3), med_mo=round(float(np.median(ttf))/21, 1) if ttf else None)


def two_sided_by_class(px, classes, lookbacks=(60, 120, 250), theta=0.34):
    """L25: per class, is the LONG-leg and SHORT-leg each positive? (no disguised beta)."""
    out = {}
    for cls, inst in classes.items():
        sub = px[inst].dropna(how="all"); rets = sub.pct_change().clip(-0.5, 0.5)
        rv = rets.rolling(60).std() * np.sqrt(252)
        sig = sum(np.sign(sub.pct_change(L)) for L in lookbacks) / len(lookbacks)
        sig = sig.where(sig.abs() >= theta, 0.0)
        pos = (sig * (0.10 / rv).clip(upper=5.0)).shift(1)
        long_r = (pos.clip(lower=0) * rets).sum(1); short_r = (pos.clip(upper=0) * rets).sum(1)
        sl = lambda x: round(x[x != 0].mean() / x[x != 0].std() * np.sqrt(252), 2) if (x != 0).any() else None
        out[cls] = (sl(long_r), sl(short_r))
    return out


def crash_short(px, net_pos_inst):
    """short-the-crash property: in the worst equity days, is the engine SHORT equity?"""
    pass  # characterized inline in main


def main():
    import os; os.makedirs(OUT, exist_ok=True)
    px = load_basket()
    print("=" * 78)
    print("FINAL VERDICT — MEASURED crypto swap (BTC -30%/yr=8.3bps/night, Fri x3, both-dir, comm 6.5 RT)")
    print(f"sanity: weekly crypto swap = 7 x 8.3 = {7*8.3:.1f} bps/wk held  (matches measured ~58)")
    print("=" * 78)

    # ===== ENGINE net of measured swap =====
    net_full, dfull = engine_net(px, INST, eth_rate=8.3)
    print(f"\nTSMOM FULL (6 legs) net of measured swap: Sharpe {dfull['sharpe']}  ann {dfull['ann']}%  "
          f"swap-drag {dfull['swap_drag_yr']}%/yr  maxDD {dfull['maxdd']}%")
    print(f"  per-leg ann swap drag %: {dfull['legdrag']}")

    # ===== PHASE 1: book WITH crypto, measured swap, CB-3% =====
    book = build_book(net_full)
    print(f"\nBOOK (TSMOM+MACD+seasonal) common window {book.index.min().date()}..{book.index.max().date()} n={len(book)}")
    print("\n=== PHASE 1 — point verdict, L2, circuit-breaker -3% (KEEP) ===")
    r_noCB = fp_decomp(book.values, 2.0)
    r_CB = fp_decomp(book.values, 2.0, daily_cb=0.03)
    print(f"  no CB : p(pass) {r_noCB['p_pass']*100:4.0f}%  bust-daily {r_noCB['bust_daily']*100:3.0f}%  bust-total {r_noCB['bust_total']*100:3.0f}%  med {r_noCB['med_mo']}mo")
    print(f"  CB-3% : p(pass) {r_CB['p_pass']*100:4.0f}%  bust-daily {r_CB['bust_daily']*100:3.0f}%  bust-total {r_CB['bust_total']*100:3.0f}%  med {r_CB['med_mo']}mo  <-- VERDICT METRIC")
    print("  -- leverage frontier (CB-3%):")
    for L in (1.5, 2.0, 3.0, 4.0):
        r = fp_decomp(book.values, L, daily_cb=0.03)
        print(f"     L={L}x: p(pass) {r['p_pass']*100:4.0f}%  bust-daily {r['bust_daily']*100:3.0f}%  bust-total {r['bust_total']*100:3.0f}%  med {r['med_mo']}mo")

    # ETH sensitivity (-45%)
    net_eth45, deth = engine_net(px, INST, eth_rate=12.3)
    book_eth45 = build_book(net_eth45)
    r_eth45 = fp_decomp(book_eth45.values, 2.0, daily_cb=0.03)
    print(f"  -- ETH sensitivity -45% (12.3 bps): TSMOM Sharpe {deth['sharpe']} -> book p(pass) {r_eth45['p_pass']*100:.0f}% (CB-3%, L2)")

    verdict_p = r_CB['p_pass']
    go = verdict_p > 0.40
    print(f"\n  >>> PHASE-1 VERDICT: p(pass)={verdict_p*100:.0f}%  -> {'GO (>40%) — STOP' if go else 'NO-GO (<=33%) — proceed to PHASE 2'}")

    book.to_csv(f"{OUT}/book_measured_swap.csv")
    if go:
        return

    # ===== PHASE 2: crypto ablation =====
    print("\n" + "=" * 78)
    print("=== PHASE 2 — crypto ABLATION (isolate the bleeder) ===")
    NC = ["US500", "GLD", "SLV", "USO"]
    net_nc, dnc = engine_net(px, NC)
    print(f"\nTSMOM NO-CRYPTO (4 legs) net of measured swap: Sharpe {dnc['sharpe']}  ann {dnc['ann']}%  "
          f"swap-drag {dnc['swap_drag_yr']}%/yr  maxDD {dnc['maxdd']}%")
    print(f"  per-leg ann swap drag %: {dnc['legdrag']}")

    # (a) residual net-SR>0 ? + short-the-crash (does engine short equity in worst US500 days?)
    rets = px.pct_change()
    rv = rets[NC].rolling(60).std() * np.sqrt(252)
    sig = sum(np.sign(px[NC].pct_change(L)) for L in (60, 120, 250)) / 3
    sig = sig.where(sig.abs() >= 0.34, 0.0)
    pos = (sig * (0.10 / rv).clip(upper=5.0)).shift(1)
    worst = rets["US500"].nsmallest(40).index                     # 40 worst equity days
    eq_pos_in_crash = float(np.sign(pos.loc[worst, "US500"]).mean())   # <0 means short during crashes
    print(f"  (a) residual net-SR = {dnc['sharpe']} ({'>0 OK' if dnc['sharpe']>0 else '<=0 DEAD'}); "
          f"short-the-crash: mean US500 sign on 40 worst eq-days = {eq_pos_in_crash:+.2f} ({'shorts crashes OK' if eq_pos_in_crash<0 else 'NOT short in crashes'})")

    # (b) two-sided per class (L25)
    classes = {"index(US500)": ["US500"], "metals(GLD,SLV)": ["GLD", "SLV"], "oil(USO)": ["USO"]}
    ts = two_sided_by_class(px, classes)
    print("  (b) two-sided per class (long-SR, short-SR):")
    for cls, (l, s) in ts.items():
        print(f"      {cls:18s}: long {l}  short {s}")

    # (c) compare full vs no-crypto at MATCHED leverage (L19) — both via fp at same L
    print("  (c) matched-leverage compare (L19, CB-3%, L2):")
    book_nc = build_book(net_nc)
    r_full = fp_decomp(book.values, 2.0, daily_cb=0.03)
    r_nc = fp_decomp(book_nc.values, 2.0, daily_cb=0.03)
    print(f"      book WITH crypto   : p(pass) {r_full['p_pass']*100:4.0f}%  bust-daily {r_full['bust_daily']*100:3.0f}%  bust-total {r_full['bust_total']*100:3.0f}%")
    print(f"      book NO-crypto     : p(pass) {r_nc['p_pass']*100:4.0f}%  bust-daily {r_nc['bust_daily']*100:3.0f}%  bust-total {r_nc['bust_total']*100:3.0f}%")
    print("  -- NO-crypto leverage frontier (CB-3%):")
    for L in (1.5, 2.0, 3.0, 4.0):
        r = fp_decomp(book_nc.values, L, daily_cb=0.03)
        print(f"     L={L}x: p(pass) {r['p_pass']*100:4.0f}%  bust-daily {r['bust_daily']*100:3.0f}%  bust-total {r['bust_total']*100:3.0f}%  med {r['med_mo']}mo")
    book_nc.to_csv(f"{OUT}/book_nocrypto_measured_swap.csv")

    print("\n  >>> PHASE-2 VERDICT:")
    if dnc['sharpe'] > 0 and r_nc['p_pass'] > r_full['p_pass'] + 0.05:
        print("      crypto = MARGINAL BLEEDER that tipped the engine net-zero -> NO-CRYPTO book is the viable FTMO engine")
    elif dnc['sharpe'] <= 0.2:
        print("      multi-asset TSMOM is WEAK INDEPENDENTLY (no-crypto net-SR ~0) -> FTMO branch has NO validated engine")
    else:
        print("      mixed: no-crypto improves but stays below the wall -> engine marginal either way")


if __name__ == "__main__":
    main()
