"""
Chantier A -- confirmation grid on the matched-autocorrelation placebo (not just the
from-scratch synthetic generator in bias_surface_synthetic_fattail.py). Reuses, read-only,
the existing block-shuffle machinery already built and validated in
Multi_Asset/research/active/mr_intraday_grille_2026-08/placebo.py (stationary_block_shuffle,
synthetic_frame) and dataload/run_grid/engine_lib from that same folder -- no engine or
prior-study code is modified, only imported.

Smaller grid than the from-scratch surface (3 widths x 3 holds x 9 instruments x 8 draws
= 648 cell-draws) because each draw here re-runs the FULL real-session-filtered pipeline
(session mask, vol targeting, HAC/DSR) per instrument, which is much more expensive than
the pure-synthetic loop. Purpose: confirm the from-scratch abaque's shape (bias shrinks
monotonically with bracket width, saturates with hold) survives when the range/return
co-dependence of REAL market microstructure (not just a bootstrapped marginal) is used.

Interpreter: /usr/bin/python3. Writes confined to this folder.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
GRILLE_DIR = HERE.parents[0] / "mr_intraday_grille_2026-08"
sys.path.insert(0, str(GRILLE_DIR))
sys.path.insert(0, str(HERE.parents[3] / "yt_strategy_replications"))
import dataload as DL
import engine_lib as E
import run_grid as RG
import placebo as PL
from engine import indicators as ind
from engine import backtest as BT
from engine import stats as S

WIDTHS = [0.75, 1.0, 1.5]
HOLDS = [4, 8, 16]
N_DRAWS = 8
MEAN_BLOCK = 100  # >> the 20-bar signal window, per RAPPORT.md's own step-2 finding


def cell_pair_t(df: pd.DataFrame, width: float, hold: int):
    close = df["close"]
    atr20 = ind.atr(df["high"], df["low"], df["close"], n=20)
    dist = E.dist_zscore(close, 20)
    d = np.nan_to_num(dist.to_numpy(float), nan=1e9)
    long_m, short_m = E.entry_cross(d, 2.0, "signed")
    ne = (E.bars_to_session_end(df) <= hold)
    sig = E.signal_from_masks(long_m, short_m, ne)
    sl = (width * atr20).to_numpy(float)
    tp = (width * atr20).to_numpy(float)
    tr_p = BT.run_backtest_vectorized(df, sig, sl_dist=sl, tp_dist=tp, cost_rt=0.0,
                                      max_hold=hold, sl_first_on_tie=True)
    tr_o = BT.run_backtest_vectorized(df, sig, sl_dist=sl, tp_dist=tp, cost_rt=0.0,
                                      max_hold=hold, sl_first_on_tie=False)
    return tr_p, tr_o


def main():
    t0 = time.time()
    rows = []
    for width in WIDTHS:
        for hold in HOLDS:
            pess_all, opt_all = [], []
            for sym in DL.ALL:
                df, bpy, scale, cost, ne_cache = RG.base_frame(sym, "15min")
                for d in range(N_DRAWS):
                    sym_seed = sum(ord(c) for c in sym) * 1000
                    rng = np.random.default_rng(sym_seed + d + MEAN_BLOCK * 7919 + 31 * int(width * 100) + hold)
                    synth = PL.synthetic_frame(df, rng, mean_block=MEAN_BLOCK)
                    tr_p, tr_o = cell_pair_t(synth, width, hold)
                    n = min(len(tr_p), len(tr_o))
                    if n == 0:
                        continue
                    if not np.array_equal(tr_p["entry_time"].to_numpy()[:n], tr_o["entry_time"].to_numpy()[:n]):
                        continue  # skip the (rare) mismatched draw rather than silently misalign
                    pess_all.append(tr_p.iloc[:n]); opt_all.append(tr_o.iloc[:n])
            if not pess_all:
                continue
            pess = pd.concat(pess_all, ignore_index=True)
            opt = pd.concat(opt_all, ignore_index=True)
            ret_p = pess["ret_gross"].to_numpy(float)
            ret_o = opt["ret_gross"].to_numpy(float)
            is_tie = (pess["reason"].to_numpy() != opt["reason"].to_numpy())
            unbiased = np.where(is_tie, 0.5 * (ret_p + ret_o), ret_p)
            _, t_p = S.hac_tstat(ret_p, lags=6)
            _, t_u = S.hac_tstat(unbiased, lags=6)
            row = dict(width_atr=width, max_hold=hold, n_trades=int(len(pess)),
                      frac_tie=float(is_tie.mean()), t_pessimistic=t_p, t_unbiased=t_u,
                      bias_t=t_p - t_u, bps_pessimistic=float(ret_p.mean() * 1e4),
                      bps_unbiased=float(unbiased.mean() * 1e4),
                      bias_bps=float((ret_p.mean() - unbiased.mean()) * 1e4))
            rows.append(row)
            print(f"  width={width} hold={hold}  n={row['n_trades']}  frac_tie={row['frac_tie']:.3f}  "
                  f"t_pess={t_p:+.2f}  t_unbiased={t_u:+.2f}  bias_t={row['bias_t']:+.2f}  "
                  f"bias_bps={row['bias_bps']:+.3f}", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(HERE / "abaque_biais_placebo_confirm.csv", index=False)
    print(f"\nWrote {len(out)} rows -> abaque_biais_placebo_confirm.csv ({time.time()-t0:.1f}s total)")


if __name__ == "__main__":
    main()
