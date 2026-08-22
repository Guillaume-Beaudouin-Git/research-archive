"""
swap_sensitivity.py — SENSITIVITY ONLY. How much does the survivors-book NO-GO depend on the
TSMOM per-night CFD swap proxy? No rebuild, no re-search, no new strategy, engine read-only.

Reuses: tsmom_regen.strat (validated construction, corr 1.000 vs chosen_returns) + audit monotone
first-passage engine (firstpassage.cdf_sequential / outer_resample_ci). Book construction frozen:
RH(deployable) + TSMOM, each vol-targeted 1%/day (63d, cap4), equal-weight, L=2.0 fixed.

A. single-rate non-crypto swap sweep (no-crypto basket): rate 0..8 bps/night long (short = measured
   +0.13), TSMOM Sharpe (full/OOS) + book p(pass) 6mo/12mo OOS with 90% CI.
B. REAL per-leg directional swap from ftmo_specs (resolves residual i: single proxy for all legs).
C. crypto bound (resolves residual ii): re-include BTC/ETH at crypto swap {0,12,25} bps/night.
D. construction sanity: swap-free regen vs chosen_returns corr.
Write only under swap_sensitivity/. Plausible-range analysis — real demo swap is the true resolver.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "research/ftmo_portfolio_audit/code"))   # audit engine (read-only)
sys.path.insert(0, str(ROOT / "research/ftmo_survivors_book/code"))    # book code (read-only)
import firstpassage as fp                                              # noqa
from audit_common import vol_target                                    # noqa
import tsmom_regen as tr                                               # noqa

OUT = ROOT / "research/ftmo_survivors_book/swap_sensitivity"
OUT.mkdir(parents=True, exist_ok=True)
OOS0, OOS1 = "2025-01-01", "2026-06-05"
L_FIXED = 2.0
N_OUTER, N_PATHS = 60, 8000

# real per-leg SIGNED swap bps/night (neg=cost to holder), from ftmo_specs_full.csv at current prices:
#   pts * 10^-digits / CFD_price * 1e4. US500 uses US100.cash proxy (USD-index financing, price-indep).
PERLEG = {"US500": (-3.08, +0.13), "GLD": (-3.52, -0.14), "SLV": (-6.88, +0.23), "USO": (+4.87, -22.42)}

RH = pd.read_csv(ROOT / "research/s076_replication/results/mtm_deployable.csv",
                 parse_dates=["date"]).set_index("date")["ret"]
PX = tr.load_basket()


def annsh(s, lo=None, hi=None):
    s = s.loc[lo:hi].dropna() if (lo or hi) else s.dropna()
    v = s[s != 0]
    return float(s.mean() / s.std(ddof=1) * np.sqrt(252)) if s.std(ddof=1) > 0 else 0.0


def book_oos(ts):
    """Frozen book: RH+TSMOM, vt each to 1%/day, equal-weight, return OOS daily series."""
    vt = lambda s: vol_target(s.dropna(), 0.01, 63, 4.0)
    df = pd.concat({"RH": vt(RH), "TS": vt(ts)}, axis=1)
    start = max(df[c].first_valid_index() for c in df.columns)
    ew = df.loc[start:].fillna(0.0).mean(axis=1)
    return ew.loc[OOS0:OOS1]


def ppass_ci(series, H):
    o = fp.outer_resample_ci(series, L_FIXED, H, n_outer=N_OUTER, n_paths=N_PATHS)
    return round(o["mean"], 3), [round(o["ci90"][0], 3), round(o["ci90"][1], 3)]


def strat_perleg(px, inst, perleg, lookbacks=(60, 120, 250), theta=0.34, port_vol=0.10, cost_bps=2.0):
    """tsmom_regen.strat construction with SIGNED per-leg directional swap (cost added to port)."""
    px = px[inst].dropna(how="all")
    rets = px.pct_change(fill_method=None).clip(-0.5, 0.5)
    rv = rets.rolling(60).std() * np.sqrt(252)
    sig = sum(np.sign(px.pct_change(L, fill_method=None)) for L in lookbacks) / len(lookbacks)
    sig = sig.where(sig.abs() >= theta, 0.0)
    pos = (sig * (0.10 / rv).clip(upper=5.0)).shift(1)
    gross = (pos * rets).sum(1)
    scale = (port_vol / (gross.rolling(60).std() * np.sqrt(252))).clip(upper=3.0).shift(1)
    port = (gross * scale).fillna(0.0) - pos.diff().abs().sum(1) * cost_bps * 1e-4
    mult_vd = (port_vol / (port.rolling(20).std() * np.sqrt(252))).clip(upper=1.0).shift(1).fillna(1.0)
    port = port * mult_vd
    eqc = (1 + port).cumprod()
    g = (eqc > eqc.rolling(100).mean()).astype(float).shift(1).fillna(1.0)
    port = port * (0.4 + 0.6 * g)
    Stot = scale.fillna(0.0) * mult_vd * (0.4 + 0.6 * g)
    fin = pd.Series(0.0, index=px.index)
    for c in inst:
        notion = pos[c] * Stot
        long_n = notion.clip(lower=0.0); short_n = (-notion.clip(upper=0.0))
        sl, ss = perleg[c]
        fin += (long_n * sl + short_n * ss) * 1e-4 * tr.WEEKEND_MULT     # signed: neg bps -> cost
    return (port + fin).dropna()


def main():
    rep = {"meta": {"L_fixed": L_FIXED, "n_outer": N_OUTER, "n_paths": N_PATHS,
                    "note": "PLAUSIBLE-RANGE analysis; real measured demo swap is the true resolver",
                    "per_leg_signed_bps_long_short": PERLEG}}

    # D. sanity: swap-free regen vs chosen_returns
    sf = tr.strat(PX, tr.INST, apply_swap=False)
    chosen = pd.read_csv(ROOT / "data/ftmo_research/tsmom/chosen_returns.csv",
                         parse_dates=["Date"]).set_index("Date")["0"]
    al = pd.concat([sf.rename("a"), chosen.rename("b")], axis=1).dropna()
    rep["D_sanity_corr_regen_vs_input"] = round(float(al.a.corr(al.b)), 4)
    print(f"[D] swap-free regen vs chosen_returns corr = {rep['D_sanity_corr_regen_vs_input']}")

    # A. single-rate non-crypto sweep (no-crypto basket, the headline book)
    print("\n[A] non-crypto swap sweep (no-crypto basket, short=+0.13 measured):")
    sweep = []
    for r in [0.0, 1.0, 2.0, 2.15, 3.08, 4.0, 5.0, 6.0, 8.0]:
        tr.SWAP_LONG_NONCRYPTO = r                       # monkeypatch (module global, read by strat)
        tr.SWAP_SHORT_NONCRYPTO = 0.13
        ts = tr.strat(PX, tr.NONCRYPTO, apply_swap=True)
        p6, c6 = ppass_ci(book_oos(ts), 126)
        p12, c12 = ppass_ci(book_oos(ts), 252)
        row = {"rate_bps_night": r, "tsmom_Sh_2007+": round(annsh(ts, "2007-01-01", None), 2),
               "tsmom_Sh_OOS": round(annsh(ts, OOS0, OOS1), 2),
               "book_OOS_6mo": p6, "book_OOS_6mo_ci90": c6,
               "book_OOS_12mo": p12, "book_OOS_12mo_ci90": c12}
        sweep.append(row)
        tag = " <- -3.08 proxy" if r == 3.08 else (" <- real per-leg avg" if r == 2.15 else "")
        print(f"  {r:>4.2f}bps: TSMOM Sh full={row['tsmom_Sh_2007+']:+.2f} OOS={row['tsmom_Sh_OOS']:+.2f} | "
              f"book OOS 6mo={p6:.3f}{c6} 12mo={p12:.3f}{c12}{tag}")
    tr.SWAP_LONG_NONCRYPTO = 3.08                        # restore
    rep["A_noncrypto_sweep"] = sweep

    # B. REAL per-leg directional swap (no-crypto)
    print("\n[B] REAL per-leg directional swap (ftmo_specs):")
    ts_pl = strat_perleg(PX, tr.NONCRYPTO, PERLEG)
    # validate strat_perleg vs tr.strat under uniform rates
    tr.SWAP_LONG_NONCRYPTO = 3.08; tr.SWAP_SHORT_NONCRYPTO = 0.13
    ts_uni = tr.strat(PX, tr.NONCRYPTO, apply_swap=True)
    ts_pl_uni = strat_perleg(PX, tr.NONCRYPTO, {c: (-3.08, -0.13) for c in tr.NONCRYPTO})
    vcorr = pd.concat([ts_uni, ts_pl_uni], axis=1).dropna().corr().iloc[0, 1]
    p6, c6 = ppass_ci(book_oos(ts_pl), 126); p12, c12 = ppass_ci(book_oos(ts_pl), 252)
    rep["B_real_perleg"] = {"validate_perleg_vs_uniform_corr": round(float(vcorr), 4),
                            "tsmom_Sh_2007+": round(annsh(ts_pl, "2007-01-01", None), 2),
                            "tsmom_Sh_OOS": round(annsh(ts_pl, OOS0, OOS1), 2),
                            "book_OOS_6mo": p6, "book_OOS_6mo_ci90": c6,
                            "book_OOS_12mo": p12, "book_OOS_12mo_ci90": c12}
    print(f"  per-leg validate corr(uniform)={vcorr:.4f} | TSMOM Sh full={rep['B_real_perleg']['tsmom_Sh_2007+']:+.2f} "
          f"OOS={rep['B_real_perleg']['tsmom_Sh_OOS']:+.2f} | book OOS 6mo={p6:.3f}{c6} 12mo={p12:.3f}{c12}")

    # C. crypto bound (full basket, non-crypto proxy 3.08, crypto swept)
    print("\n[C] crypto-leg inclusion bound (full basket, non-crypto=3.08, crypto swept):")
    cb = {}
    for cs, lbl in [(0.0, "best(crypto=0)"), (12.0, "mid(crypto=12)"), (25.0, "worst(crypto=25)")]:
        ts = tr.strat(PX, tr.INST, crypto_swap=cs, apply_swap=True)
        p6, c6 = ppass_ci(book_oos(ts), 126); p12, c12 = ppass_ci(book_oos(ts), 252)
        cb[lbl] = {"tsmom_Sh_2007+": round(annsh(ts, "2007-01-01", None), 2),
                   "tsmom_Sh_OOS": round(annsh(ts, OOS0, OOS1), 2),
                   "book_OOS_6mo": p6, "book_OOS_6mo_ci90": c6,
                   "book_OOS_12mo": p12, "book_OOS_12mo_ci90": c12}
        print(f"  {lbl:18s}: TSMOM Sh OOS={cb[lbl]['tsmom_Sh_OOS']:+.2f} | book OOS 6mo={p6:.3f}{c6} 12mo={p12:.3f}{c12}")
    rep["C_crypto_bound"] = cb

    # Breakeven analysis (12mo OOS): point and CI-lower vs 0.50
    pts = [(r["rate_bps_night"], r["book_OOS_12mo"], r["book_OOS_12mo_ci90"][0]) for r in sweep]
    point_max = max(p for _, p, _ in pts); cilow_max = max(l for _, _, l in pts)
    rep["breakeven_12mo"] = {
        "max_point_over_sweep": round(point_max, 3),
        "max_ci_lower_over_sweep": round(cilow_max, 3),
        "point_clears_0.50_anywhere": bool(point_max >= 0.50),
        "ci_lower_clears_0.50_anywhere": bool(cilow_max >= 0.50),
        "verdict": ("NO swap rate in [0,8] (nor 0) lifts the 12mo OOS point estimate to 0.50; "
                    "CI lower bound stays far below 0.50 throughout -> NO-GO is SWAP-ROBUST.")
        if point_max < 0.50 else "a plausible swap rate clears 0.50 -> verdict hinges on the proxy"}
    print(f"\n[breakeven] max 12mo OOS point over sweep={point_max:.3f}, max CI-lower={cilow_max:.3f} "
          f"-> {'SWAP-ROBUST NO-GO' if point_max<0.50 else 'hinges on proxy'}")

    (OUT / "swap_sensitivity.json").write_text(json.dumps(rep, indent=2, default=str))
    pd.DataFrame(sweep).to_csv(OUT / "swap_sweep_table.csv", index=False)
    print(f"\nwrote {OUT/'swap_sensitivity.json'} + swap_sweep_table.csv")


if __name__ == "__main__":
    main()
