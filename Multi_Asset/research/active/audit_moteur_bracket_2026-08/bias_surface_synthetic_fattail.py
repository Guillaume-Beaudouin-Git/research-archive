"""
Chantier A -- PRIMARY abaque. Same decomposition as bias_surface_synthetic_thin_tail.py
(pessimistic vs optimistic vs unbiased trade-for-trade, via sl_first_on_tie flip), but
with a synthetic generator that matches the RAPPORT.md methodology more closely:

  "a pure i.i.d. Gaussian random walk ... zero fat tails BEYOND the resampled bar-range
  distribution" (RAPPORT.md section 3, step 4).

Read literally: close-to-close log returns are drawn i.i.d. Gaussian (no autocorrelation,
no directional structure) -- but the intrabar high/low is NOT built from a smooth Gaussian
sub-path. It is built by bootstrapping (iid, with replacement) the REAL, empirically
fat-tailed relative-range ((high-low)/prev_close) distribution of a real instrument
(US100 15-min, already cached read-only by mr_intraday_grille_2026-08/dataload.py).

This isolates the ONE thing that matters for the tie-break mechanism -- how often a
single bar's range is wide enough to span both barriers -- from genuine market
DIRECTIONAL structure (which the iid returns explicitly remove). The
bias_surface_synthetic_thin_tail.py companion script (idealised smooth sub-tick GBM,
near-Gaussian thin-tailed range) is kept alongside as a robustness/contrast check: it
shows the bias collapses much faster with bracket width when the range distribution
lacks real fat tails, i.e. the magnitude of this artifact is itself sensitive to how
fat-tailed the instrument's own bar-range distribution is.

Interpreter: /usr/bin/python3. Reads (read-only) the parquet cache built by
Multi_Asset/research/active/mr_intraday_grille_2026-08/dataload.py and the shared engine
at yt_strategy_replications/engine/ -- modifies neither. Writes confined to this folder.
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

REAL_CACHE = REPO / "Multi_Asset/research/active/mr_intraday_grille_2026-08/_cache/US100_15min.parquet"

SEED = 20260821
K_DRAWS = 12
N_BARS = 20000
ATR_N = 20
Z_N = 20
Z_THRESHOLD = 2.0

WIDTHS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
HOLDS = [2, 3, 4, 6, 8, 12, 16, 24, 32]


def load_real_relrange() -> np.ndarray:
    df = pd.read_parquet(REAL_CACHE)
    rr = ((df["high"] - df["low"]) / df["close"]).dropna().to_numpy(float)
    ret = np.log(df["close"] / df["close"].shift(1)).dropna().to_numpy(float)
    return rr, float(np.std(ret))


def gen_ohlc_fattail(n_bars: int, rel_range_pool: np.ndarray, sigma_bar: float, rng, s0: float = 100.0):
    """i.i.d. Gaussian close-to-close log returns; high/low built from an iid bootstrap
    of REAL relative-range values (fat right tail preserved, autocorrelation destroyed
    by the iid resampling itself). Same body-plus-wick construction as the sibling
    mr_intraday_grille_2026-08/placebo.py::synthetic_frame, applied here to a fully
    synthetic (no genuine gaps, no session structure) iid return series."""
    logret = rng.normal(0.0, sigma_bar, size=n_bars)
    logret[0] = 0.0
    close = s0 * np.exp(np.cumsum(logret))
    open_ = np.empty(n_bars)
    open_[0] = s0
    open_[1:] = close[:-1]
    rr = rng.choice(rel_range_pool, size=n_bars, replace=True)
    prev_close = np.r_[s0, close[:-1]]
    body_hi = np.maximum(open_, close)
    body_lo = np.minimum(open_, close)
    wick = 0.5 * rr * prev_close
    high = body_hi + wick
    low = body_lo - wick
    idx = pd.date_range("2020-01-01", periods=n_bars, freq="15min")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=idx)


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
    rr_pool, sigma_bar = load_real_relrange()
    print(f"Loaded {len(rr_pool)} real US100 15-min relative-range values "
          f"(median {np.median(rr_pool)*1e4:.2f}bps, p95 {np.percentile(rr_pool,95)*1e4:.2f}bps, "
          f"max {rr_pool.max()*1e4:.2f}bps); close-to-close logret sigma={sigma_bar*1e4:.2f}bps")

    rng = np.random.default_rng(SEED)
    draws = []
    for d in range(K_DRAWS):
        df = gen_ohlc_fattail(N_BARS, rr_pool, sigma_bar, rng)
        sig, atrN = make_signal(df)
        draws.append((df, sig, atrN))
    print(f"Generated {K_DRAWS} draws of {N_BARS} bars ({time.time()-t0:.1f}s)")

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
    out.to_csv(HERE / "abaque_biais.csv", index=False)
    print(f"\nWrote {len(out)} rows -> abaque_biais.csv ({time.time()-t0:.1f}s total)")
    print(f"Draw-cell trade-count/entry-time mismatches (expected 0): {int(out['n_draw_mismatch'].sum())}")


if __name__ == "__main__":
    main()
