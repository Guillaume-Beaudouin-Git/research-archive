"""
container_eval.py — re-evaluate the EXISTING survivors book under the verified non-symmetric
barrier geometries (PROPFIRM_SCAN.md). NO new strategies/signals/params — same book, different barrier.

Reuses VERBATIM: the survivors combined book (research/ftmo_survivors_book/results/final_book_daily.csv),
the audit's monotone first-passage engine (geometry set by P1/P2 module constants), the survivors
tsmom_regen.strat() construction (for the weekend re-cost), measured per-leg swap.

Geometries (verified vs scan; all STATIC 10% DD + 5% daily — only the P1 target differs, except
weekend LEGALITY which gates whether the weekend-holding book is deployable):
  (a) FTMO Standard  : P1 10% / P2 5%  — weekend holds PROHIBITED (book is non-compliant as-is)
  (b) FundedNext Stellar 2-Step : P1 8% / P2 5% — weekend ALLOWED (daily granularity [UNVERIFIED])
  (c) FTMO Swing     : P1 10% / P2 5% — weekend ALLOWED (same barrier as Standard; legal holds)
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "research/ftmo_portfolio_audit/code"))   # firstpassage (engine)
sys.path.insert(0, str(ROOT / "research/ftmo_survivors_book/code"))     # tsmom_regen (construction)
import firstpassage as fp
import tsmom_regen as tg
OUT = Path(__file__).parent / "results"; OUT.mkdir(parents=True, exist_ok=True)
IS_END, OOS0, OOS1 = "2024-12-31", "2025-01-01", "2026-06-05"

GEOM = {  # (P1, P2, weekend_legal)
    "FTMO_Standard(10/5,no-wknd)": (0.10, 0.05, False),
    "FundedNext_Stellar2(8/5,wknd)": (0.08, 0.05, True),
    "FTMO_Swing(10/5,wknd)": (0.10, 0.05, True),
}
LGRID = [1.5, 2.0, 2.5, 3.0, 3.5]


def ann_sharpe(s):
    s = s.dropna(); s = s[s != 0]
    return float(s.mean() / s.std(ddof=1) * np.sqrt(252)) if len(s) > 5 and s.std(ddof=1) > 0 else 0.0


def set_geom(p1, p2):
    fp.P1, fp.P2 = p1, p2          # monkeypatch engine geometry (MAXDD/DAILY unchanged = 10%/5%)


def ppass(series, L, H, p1, p2):
    set_geom(p1, p2)
    return fp.cdf_sequential(series, L, [H], n_paths=15000)[H]


def ppass_ci(series, L, H, p1, p2, n_outer=60):
    set_geom(p1, p2)
    return fp.outer_resample_ci(series, L, H, n_outer=n_outer, n_paths=6000)


def fix_L_on_IS(series, p1, p2):
    iss = series.loc[:IS_END]
    return max(LGRID, key=lambda L: ppass(iss, L, 252, p1, p2))


# ── weekend re-cost: replicate tsmom_regen.strat with a weekend-FLAT toggle (construction verbatim) ──
def strat_wf(px, inst, weekend_flat=False, lookbacks=(60, 120, 250), theta=0.34,
             port_vol=0.10, cost_bps=2.0, crypto_swap=0.0, apply_swap=True):
    px = px[inst].dropna(how="all")
    rets = px.pct_change().clip(-0.5, 0.5)
    rv = rets.rolling(60).std() * np.sqrt(252)
    sig = sum(np.sign(px.pct_change(L)) for L in lookbacks) / len(lookbacks)
    sig = sig.where(sig.abs() >= theta, 0.0)
    pos = (sig * (0.10 / rv).clip(upper=5.0)).shift(1)
    if weekend_flat:                       # do NOT hold over the weekend: flat on Mondays (the bar that carries Fri->Mon)
        pos.loc[px.index.dayofweek == 0, :] = 0.0
    gross = (pos * rets).sum(1)
    scale = (port_vol / (gross.rolling(60).std() * np.sqrt(252))).clip(upper=3.0).shift(1)
    port = (gross * scale).fillna(0.0) - pos.diff().abs().sum(1) * cost_bps * 1e-4
    mult_vd = (port_vol / (port.rolling(20).std() * np.sqrt(252))).clip(upper=1.0).shift(1).fillna(1.0)
    port = port * mult_vd
    eqc = (1 + port).cumprod()
    g = (eqc > eqc.rolling(100).mean()).astype(float).shift(1).fillna(1.0)
    mult_eg = 0.4 + 0.6 * g
    port = port * mult_eg
    Stot = scale.fillna(0.0) * mult_vd * mult_eg
    wmult = 1.0 if weekend_flat else tg.WEEKEND_MULT     # no weekend hold -> no weekend swap amortization
    if apply_swap:
        swap = pd.Series(0.0, index=px.index)
        for c in inst:
            notion = pos[c] * Stot
            long_n = notion.clip(lower=0.0); short_n = -notion.clip(upper=0.0)
            rl, rs = (crypto_swap, crypto_swap) if c not in tg.NONCRYPTO else (tg.SWAP_LONG_NONCRYPTO, tg.SWAP_SHORT_NONCRYPTO)
            swap += (long_n * rl + short_n * rs) * 1e-4 * wmult
        port = port - swap
    return port.dropna()


def main():
    rep = {"geometries_verified_vs_scan": {
        "FundedNext_Stellar2": "P1 8%/P2 5%, 10% STATIC DD, 5% daily, wknd YES (daily bal-vs-eq granularity UNVERIFIED)",
        "FTMO_Swing": "P1 10%/P2 5%, 10% STATIC DD, 5% daily (equity intraday), wknd YES",
        "FTMO_Standard": "same 10/5 barrier but weekend holds PROHIBITED -> book (holds wknds) non-compliant as-is"}}

    book = pd.read_csv(ROOT / "research/ftmo_survivors_book/results/final_book_daily.csv",
                       index_col=0, parse_dates=True).iloc[:, 0]
    book.index = pd.to_datetime(book.index)
    print(f"book range {book.index.min().date()}..{book.index.max().date()} | full Sh {ann_sharpe(book):.2f} "
          f"IS {ann_sharpe(book.loc[:IS_END]):.2f} OOS {ann_sharpe(book.loc[OOS0:OOS1]):.2f}")

    # ---- p(pass) per geometry on the EXISTING (weekend-holding) book ----
    rep["geometry_ppass"] = {}
    for gname, (p1, p2, wknd_ok) in GEOM.items():
        L = fix_L_on_IS(book, p1, p2)
        iss, oos = book.loc[:IS_END], book.loc[OOS0:OOS1]
        tbl = {}
        for win, s in [("IS", iss), ("OOS", oos)]:
            for H, mo in [(126, "6mo"), (252, "12mo")]:
                ci = ppass_ci(s, L, H, p1, p2)
                tbl[f"{win}_{mo}"] = {"p": round(ci["mean"], 3), "ci90": [round(ci["ci90"][0], 3), round(ci["ci90"][1], 3)]}
        mono = {h: round(ppass(oos, L, h, p1, p2), 3) for h in [63, 126, 189, 252]}
        sweep = {L2: round(ppass(oos, L2, 252, p1, p2), 3) for L2 in LGRID}
        clears = any(tbl[k]["ci90"][0] > 0.50 for k in ["OOS_6mo", "OOS_12mo"])
        rep["geometry_ppass"][gname] = {"P1": p1, "P2": p2, "weekend_legal": wknd_ok, "Lstar_IS": L,
                                        "ppass": tbl, "monotone_OOS": mono, "L_sweep_OOS12mo": sweep,
                                        "OOS_CI_clears_0.50": clears,
                                        "deployable_as_is": wknd_ok}
        print(f"\n[{gname}] L*={L} wknd_legal={wknd_ok}")
        for k, v in tbl.items():
            print(f"   p(pass) {k:9s} {v['p']:.3f} CI{v['ci90']}")
        print(f"   monotone OOS {mono} | clears0.50={clears}")
        set_geom(0.10, 0.05)     # restore

    # ---- weekend re-cost (TSMOM sleeve; reuse tg.strat verbatim for HOLD, replicate FLAT) ----
    px = tg.load_basket()
    ts_hold_verbatim = tg.strat(px, tg.NONCRYPTO, apply_swap=True)            # the book's TSMOM, verbatim
    ts_hold_repl = strat_wf(px, tg.NONCRYPTO, weekend_flat=False, apply_swap=True)
    ts_flat = strat_wf(px, tg.NONCRYPTO, weekend_flat=True, apply_swap=True)
    al = pd.concat([ts_hold_verbatim.rename("v"), ts_hold_repl.rename("r")], axis=1).dropna()
    rep["weekend_recost"] = {
        "validate_replication_corr_vs_verbatim": round(float(al.v.corr(al.r)), 4),
        "TSMOM_weekend_HOLD_Sharpe_full": round(ann_sharpe(ts_hold_verbatim), 3),
        "TSMOM_weekend_HOLD_Sharpe_OOS": round(ann_sharpe(ts_hold_verbatim.loc[OOS0:OOS1]), 3),
        "TSMOM_weekend_FLAT_Sharpe_full": round(ann_sharpe(ts_flat), 3),
        "TSMOM_weekend_FLAT_Sharpe_OOS": round(ann_sharpe(ts_flat.loc[OOS0:OOS1]), 3),
        "delta_full(hold-flat)": round(ann_sharpe(ts_hold_verbatim) - ann_sharpe(ts_flat), 3),
        "note": ("survivors book TSMOM ALREADY holds weekends + charges WEEKEND_MULT=1.45 swap (verbatim). "
                 "FLAT = zero Monday holds + swap mult 1.0 (conservative: over-penalizes by missing all Monday, "
                 "not just the Fri->Mon-open gap). RH weekend dependence is an uncosted residual (fixed series).")}
    print(f"\n[weekend re-cost] replication corr {rep['weekend_recost']['validate_replication_corr_vs_verbatim']}")
    print(f"  TSMOM HOLD Sh full {rep['weekend_recost']['TSMOM_weekend_HOLD_Sharpe_full']} OOS {rep['weekend_recost']['TSMOM_weekend_HOLD_Sharpe_OOS']}")
    print(f"  TSMOM FLAT Sh full {rep['weekend_recost']['TSMOM_weekend_FLAT_Sharpe_full']} OOS {rep['weekend_recost']['TSMOM_weekend_FLAT_Sharpe_OOS']}")

    (OUT / "container_eval.json").write_text(json.dumps(rep, indent=2, default=str))
    set_geom(0.10, 0.05)
    print("\nDONE ->", OUT)


if __name__ == "__main__":
    main()
