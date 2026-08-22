"""
Chantier A -- quantify the shared engine's pessimistic same-bar tie-break bias as a
function of its two free parameters: bracket width (in ATR multiples) and max holding
period (in bars). Zero market content (pure i.i.d. Gaussian random walk, no
autocorrelation, no drift, no gaps) so any nonzero mean return is 100% mechanical.

Method (clean decomposition, does not require guessing a "fair" resolution rule):
  For each (width, hold) cell, run the SAME synthetic price draws and the SAME entry
  signal through the shared engine (yt_strategy_replications/engine/backtest.py) TWICE,
  flipping only `sl_first_on_tie`:
    - True  (the engine's own default -- "pessimistic (stop first)", see
      yt_strategy_replications/engine/backtest.py:10, :51, :124, :179)
    - False (tp-first / "optimistic")
  Because the exit BAR index for an exact tie (sidx == tidx, both barriers first
  touched in the same subsequent bar) does not depend on sl_first_on_tie (see
  backtest.py:107-124), the two runs produce IDENTICAL trade sequences (same
  entry_time/exit_time for every trade) except that tie trades get a different
  exit_px/reason. This lets us build a third, unbiased reference series:
      unbiased_ret[i] = 0.5*(ret_pessimistic[i] + ret_optimistic[i])   if trade i is a tie
                      = ret_pessimistic[i]  (== ret_optimistic[i])      otherwise
  which is exactly what a "50/50 coin flip on true ambiguity" would produce in
  expectation. bias = pessimistic - unbiased, in both HAC-t and bps/trade.

Interpreter: /usr/bin/python3. Read-only reuse of yt_strategy_replications/engine
(no modification). Writes confined to this folder.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "yt_strategy_replications"))
from engine import backtest as BT
from engine import indicators as ind
from engine import stats as S

SEED = 20260821
K_DRAWS = 12
N_BARS = 20000          # ~625 trading days at 32 bars/day -- comparable order of magnitude
TICKS_PER_BAR = 20      # intrabar sub-steps used only to build internally consistent O/H/L/C
SIGMA_BAR = 0.0025      # 25 bps per-bar log-return std, calibrated to real US100 15-min
                        # (measured: US100 15min logret std = 24.70bps, ATR20 median = 20.83bps
                        # -- see Multi_Asset/research/active/mr_intraday_grille_2026-08/_cache)
ATR_N = 20
Z_N = 20
Z_THRESHOLD = 2.0

WIDTHS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]     # symmetric sl=tp=width*ATR20
HOLDS = [2, 3, 4, 6, 8, 12, 16, 24, 32]             # max_hold in bars


def gen_ohlc(n_bars: int, ticks_per_bar: int, sigma_bar: float, rng, s0: float = 100.0):
    """Vectorised i.i.d. Gaussian intrabar random walk -> internally-consistent OHLC.
    Zero drift, zero autocorrelation beyond the trivial continuity of price levels."""
    n_steps = n_bars * ticks_per_bar
    sigma_tick = sigma_bar / np.sqrt(ticks_per_bar)
    r = rng.normal(0.0, sigma_tick, size=n_steps)
    L = np.concatenate([[0.0], np.cumsum(r)])
    P = s0 * np.exp(L)
    idx0 = np.arange(n_bars) * ticks_per_bar
    opens = P[idx0]
    closes = P[idx0 + ticks_per_bar]
    windows = np.lib.stride_tricks.sliding_window_view(P, ticks_per_bar + 1)[idx0]
    highs = windows.max(axis=1)
    lows = windows.min(axis=1)
    idx = pd.date_range("2020-01-01", periods=n_bars, freq="15min")
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes}, index=idx)


def make_signal(df: pd.DataFrame):
    z = ind.zscore(df["close"], Z_N)
    zz = np.nan_to_num(z.to_numpy(float), nan=0.0)
    sig = np.where(zz <= -Z_THRESHOLD, 1.0, np.where(zz >= Z_THRESHOLD, -1.0, 0.0))
    atrN = ind.atr(df["high"], df["low"], df["close"], n=ATR_N)
    return sig, atrN


def run_pair(df, sig, atrN, width, hold):
    sl = (width * atrN).to_numpy(float)
    tp = (width * atrN).to_numpy(float)
    tr_pess = BT.run_backtest_vectorized(df, sig, sl_dist=sl, tp_dist=tp, cost_rt=0.0,
                                         max_hold=hold, sl_first_on_tie=True)
    tr_opt = BT.run_backtest_vectorized(df, sig, sl_dist=sl, tp_dist=tp, cost_rt=0.0,
                                        max_hold=hold, sl_first_on_tie=False)
    return tr_pess, tr_opt


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    draws = []
    for d in range(K_DRAWS):
        df = gen_ohlc(N_BARS, TICKS_PER_BAR, SIGMA_BAR, rng)
        sig, atrN = make_signal(df)
        draws.append((df, sig, atrN))
    print(f"Generated {K_DRAWS} draws of {N_BARS} synthetic bars ({time.time()-t0:.1f}s)")

    rows = []
    for width in WIDTHS:
        for hold in HOLDS:
            pess_all, opt_all = [], []
            mismatch = 0
            for df, sig, atrN in draws:
                tr_p, tr_o = run_pair(df, sig, atrN, width, hold)
                n = min(len(tr_p), len(tr_o))
                if len(tr_p) != len(tr_o):
                    mismatch += 1
                    n = min(len(tr_p), len(tr_o))
                if n == 0:
                    continue
                et_p = tr_p["entry_time"].to_numpy()[:n]
                et_o = tr_o["entry_time"].to_numpy()[:n]
                if not np.array_equal(et_p, et_o):
                    mismatch += 1
                pess_all.append(tr_p.iloc[:n])
                opt_all.append(tr_o.iloc[:n])
            if not pess_all:
                continue
            pess = pd.concat(pess_all, ignore_index=True)
            opt = pd.concat(opt_all, ignore_index=True)
            ret_p = pess["ret_gross"].to_numpy(float)
            ret_o = opt["ret_gross"].to_numpy(float)
            is_tie = (pess["reason"].to_numpy() != opt["reason"].to_numpy())
            unbiased = np.where(is_tie, 0.5 * (ret_p + ret_o), ret_p)

            _, t_p = S.hac_tstat(ret_p, lags=6)
            _, t_o = S.hac_tstat(ret_o, lags=6)
            _, t_u = S.hac_tstat(unbiased, lags=6)

            row = dict(
                width_atr=width, max_hold=hold, n_trades=int(len(pess)),
                n_draw_mismatch=int(mismatch), frac_tie=float(is_tie.mean()),
                avg_bars_held=float(pess["bars_held"].mean()),
                frac_sl_pess=float((pess["reason"] == "sl").mean()),
                frac_tp_pess=float((pess["reason"] == "tp").mean()),
                frac_time_pess=float((pess["reason"].isin(["time", "open_end"])).mean()),
                t_pessimistic=t_p, t_optimistic=t_o, t_unbiased=t_u,
                bias_t=t_p - t_u,
                bps_pessimistic=float(ret_p.mean() * 1e4),
                bps_optimistic=float(ret_o.mean() * 1e4),
                bps_unbiased=float(unbiased.mean() * 1e4),
                bias_bps=float((ret_p.mean() - unbiased.mean()) * 1e4),
            )
            rows.append(row)
            print(f"  width={width:>4} hold={hold:>3}  n={row['n_trades']:>6}  "
                  f"frac_tie={row['frac_tie']:.3f}  t_pess={t_p:+.2f}  t_unbiased={t_u:+.2f}  "
                  f"bias_t={row['bias_t']:+.2f}  bias_bps={row['bias_bps']:+.3f}", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(HERE / "abaque_biais_synthetic_thin_tail.csv", index=False)
    print(f"\nWrote {len(out)} rows -> abaque_biais_synthetic_thin_tail.csv ({time.time()-t0:.1f}s total)")
    print(f"Any entry_time mismatch across the {len(WIDTHS)*len(HOLDS)} cells: "
          f"{int(out['n_draw_mismatch'].sum())} draw-cells flagged (expected 0; nonzero would mean "
          f"the pessimistic/optimistic runs are NOT directly comparable trade-for-trade).")


if __name__ == "__main__":
    main()
