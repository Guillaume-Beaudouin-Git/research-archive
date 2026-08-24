"""
K3 / Book-slot — marginal contribution of the sleeve to the A+B book (PREREG 1-2).
Reconstruct A (crypto TSMOM long-only) and B (delta-neutral carry) daily returns,
measure monthly corr(sleeve, A) and (sleeve, B), and compute the book Sharpe with
the sleeve added under (i) the project's equal-risk methodology that yields the
canonical A+B SR=2.31 and (ii) optimal tangency. Book-slot gate: marginal uplift
> 0 AND monthly corr(sleeve, A) < 0.4. D-gate (2.54) reported for context.
"""
from __future__ import annotations
import sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from engine import Params, load_universe, simulate, build_costs, load_specs
import metrics as M

ROOT = Path("<HOME>/Desktop/Algo_claude")
CORE = ["NQ", "ES", "GC", "CL", "6E", "6A", "6B"]
specs = load_specs(); PER, ROLL, MULT = build_costs(specs); DATA = load_universe(CORE)
others = tuple(s for s in CORE if s != "CL")

# documented book params (CLAUDE.md / _audit/portfolio_recalc_2026-06-10.md)
SR_A, SR_B, RHO_AB = 1.33, 2.0, 0.039


def reconstruct_A():
    import yfinance as yf
    px = {}
    for t, s in [("BTC-USD", "BTC"), ("ETH-USD", "ETH"), ("SOL-USD", "SOL")]:
        d = yf.download(t, start="2020-01-01", auto_adjust=True, progress=False)
        px[s] = d["Close"][t] if isinstance(d["Close"], pd.DataFrame) else d["Close"]
    P = pd.DataFrame(px).dropna(how="all")
    lr = np.log(P).diff()
    cum = lr.rolling(28).sum(); vol = lr.rolling(28).std()
    sig = np.tanh(cum / (vol * np.sqrt(28))).clip(lower=0)
    pos = sig.shift(1)
    raw = (pos * lr).mean(axis=1)
    rv = raw.rolling(63).std() * np.sqrt(365)
    A = (raw * (0.18 / rv).shift(1).clip(upper=3)).dropna()
    A.index = pd.to_datetime(A.index).tz_localize(None)
    return A


def reconstruct_B():
    f = ROOT / "data/metadata/delta_neutral_backtest.csv"
    df = pd.read_csv(f)
    ts = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    daily = df.assign(date=ts.dt.normalize()).groupby("date")["net_pnl"].sum() / 500.0
    return daily


def book_sharpe_eqrisk(SRs, R):
    w = np.ones(len(SRs)) / len(SRs)
    return float((w @ np.array(SRs)) / np.sqrt(w @ R @ w))


def tangency_sharpe(SRs, R):
    SRs = np.array(SRs)
    return float(np.sqrt(SRs @ np.linalg.inv(R) @ SRs))


def main():
    A = reconstruct_A(); B = reconstruct_B()
    Am = (1 + A).resample("ME").prod() - 1
    Bm = (1 + B).resample("ME").prod() - 1
    print(f"reconstructed A: {A.index[0].date()}..{A.index[-1].date()} ann.Sharpe={A.mean()/A.std()*np.sqrt(365):.2f}")
    print(f"reconstructed B: {B.index[0].date()}..{B.index[-1].date()} n={len(B)} (sparse)")
    print(f"  check: 2-asset equal-risk book Sharpe = {book_sharpe_eqrisk([SR_A,SR_B], np.array([[1,RHO_AB],[RHO_AB,1]])):.3f} (canonical 2.31)\n")

    cands = {"two_sided": Params(), "long_only": Params(long_only=True), "H1b_shortCL": Params(long_only_syms=others)}
    print(f"{'sleeve':12s} {'SR':>5s} {'rho_A(mo)':>9s} {'rho_B(mo)':>9s} {'ERC_book':>8s} {'tangency':>8s} {'K3':>14s}")
    rows = []
    for name, p in cands.items():
        res = simulate(DATA, p, 100_000, {s: PER[s] for s in CORE}, {s: ROLL[s] for s in CORE}, MULT,
                       start="2014-01-01", end="2026-06-12")
        sm = res["equity"]["equity"].resample("ME").last().pct_change()
        SR_S = M.equity_metrics(res["equity"])["sharpe"]
        jA = pd.concat([sm.rename("s"), Am.rename("a")], axis=1, sort=True).dropna()
        jB = pd.concat([sm.rename("s"), Bm.rename("b")], axis=1, sort=True).dropna()
        rA = float(jA["s"].corr(jA["a"])); rB = float(jB["s"].corr(jB["b"])) if len(jB) > 6 else 0.0
        R3 = np.array([[1, RHO_AB, rA], [RHO_AB, 1, rB], [rA, rB, 1]])
        erc3 = book_sharpe_eqrisk([SR_A, SR_B, SR_S], R3)
        tan2 = tangency_sharpe([SR_A, SR_B], np.array([[1, RHO_AB], [RHO_AB, 1]]))
        tan3 = tangency_sharpe([SR_A, SR_B, SR_S], R3)
        erc_marg = erc3 - 2.31; tan_marg = tan3 - tan2
        k3 = "SLOT" if (erc_marg > 0 and rA < 0.4) else "NO SLOT"
        rows.append((name, SR_S, rA, rB, erc3, erc_marg, tan3, tan_marg, k3))
        print(f"{name:12s} {SR_S:5.2f} {rA:9.2f} {rB:9.2f} {erc3:8.3f} {tan3:8.3f} {k3:>14s}")

    print("\n=== marginal detail (ERC = project methodology; tangency = optimal weight) ===")
    for name, SR_S, rA, rB, erc3, ercm, tan3, tanm, k3 in rows:
        print(f"  {name:12s} ERC: 2.310 -> {erc3:.3f} ({ercm:+.3f})   tangency: {tangency_sharpe([SR_A,SR_B],np.array([[1,RHO_AB],[RHO_AB,1]])):.3f} -> {tan3:.3f} ({tanm:+.3f})   "
              f"D-gate 2.54: {'PASS' if erc3>2.54 else 'FAIL'}")

    # sensitivity: SR_B proxy down to 1.5, sleeve at regime-OOS (2020-26) Sharpe
    print("\n=== sensitivity (SR_B in {2.0,1.5}; two_sided sleeve) ===")
    for srb in (2.0, 1.5):
        base2 = book_sharpe_eqrisk([SR_A, srb], np.array([[1, RHO_AB], [RHO_AB, 1]]))
        name, SR_S, rA, rB = rows[0][0], rows[0][1], rows[0][2], rows[0][3]
        R3 = np.array([[1, RHO_AB, rA], [RHO_AB, 1, rB], [rA, rB, 1]])
        erc3 = book_sharpe_eqrisk([SR_A, srb, SR_S], R3)
        print(f"  SR_B={srb}: A+B ERC={base2:.3f} -> A+B+sleeve ERC={erc3:.3f} ({erc3-base2:+.3f})")


if __name__ == "__main__":
    main()
