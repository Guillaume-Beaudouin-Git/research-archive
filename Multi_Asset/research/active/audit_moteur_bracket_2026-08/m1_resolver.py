"""
Chantier B -- the RESOLVER. The engine's pessimistic same-bar tie-break (chantier A) is a
15-min-bar-resolution artifact, not a law of nature: the repo has true-UTC M1 data
(`data/deep_history_utc/*_M1.csv`) for every instrument the 15-min studies use. An
ambiguous 15-min bar (both stop and target reachable within it) can be re-examined at M1
resolution: whichever level the price touches FIRST, minute by minute, wins. Falls back
to the pessimistic default only when the M1 bar itself is STILL ambiguous (both levels
touched inside the very same minute) -- a residual, reported separately, never assumed
away.

Two experiments:
  B1 -- synthetic M1-level noise (zero content at ANY horizon: M1 returns i.i.d. Gaussian,
        M1 ranges bootstrapped from real M1 data so the fat tail is realistic, aggregated
        up to 15-min for the outer z-score/ATR-bracket cell). Tests whether M1 resolution
        actually collapses the bias on pure noise, and what residual remains.
  B2 -- real data (US100 index, XAUUSD metal -- one per instrument class already measured
        in chantier A) at the canonical cell (SMA20+z-score(2.0), CROSS, 1.0xATR
        symmetric bracket, H=8). Reports the before/after swing on the real series.

Zone check (mandate's explicit ask, L52/L56): `data/deep_history_utc` timestamps are
verified true UTC by an independent DST-shift test in this session (US100 peak-volume
hour shifts 15->14 UTC between January and July, exactly the 1-hour shift expected from a
fixed 9:30 ET cash-equity open under EST->EDT -- a mislabeled fixed-local-time series
would show NO such shift). Confirms the MANIFEST.md claim and the prior tick-verification
already logged by mr_timezone_repair_2026-08 / gross_surface_map_2026-08.

Interpreter: /usr/bin/python3. Reads yt_strategy_replications/engine and
data/deep_history_utc (read-only). Writes confined to this folder.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "yt_strategy_replications"))
sys.path.insert(0, str(HERE.parents[0] / "mr_intraday_grille_2026-08"))
from engine import backtest as BT
from engine import indicators as ind
from engine import stats as S
import dataload as DL

DEEP = REPO / "data" / "deep_history_utc"
ATR_N = 20
Z_N = 20
Z_THRESHOLD = 2.0
WIDTH = 1.0
HOLD = 8


# ------------------------------------------------------------------ M1 tie resolution

def m1_tie_resolve(m1_sub: pd.DataFrame, direction: int, sl_px: float, tp_px: float):
    """m1_sub: the M1 OHLC rows composing ONE ambiguous 15-min bar, chronological order.
    Returns (resolved_exit_px, reason, m1_still_ambiguous: bool)."""
    hi = m1_sub["high"].to_numpy(float)
    lo = m1_sub["low"].to_numpy(float)
    if direction > 0:
        hit_sl, hit_tp = lo <= sl_px, hi >= tp_px
    else:
        hit_sl, hit_tp = hi >= sl_px, lo <= tp_px
    sidx = int(np.argmax(hit_sl)) if hit_sl.any() else None
    tidx = int(np.argmax(hit_tp)) if hit_tp.any() else None
    if sidx is None and tidx is None:
        return None, "m1_no_touch", False  # should not happen (15min hi/lo = max/min of M1)
    if sidx is None:
        return tp_px, "tp", False
    if tidx is None:
        return sl_px, "sl", False
    if sidx < tidx:
        return sl_px, "sl", False
    if tidx < sidx:
        return tp_px, "tp", False
    return sl_px, "sl", True  # same M1 minute hits both -- genuinely irreducible, pessimistic fallback


def find_ties(df15: pd.DataFrame, sig: np.ndarray, sl_arr: np.ndarray, tp_arr: np.ndarray, max_hold: int):
    """Run the engine twice (pessimistic/optimistic) and return the trade-aligned pair
    plus a boolean tie mask, exactly as in chantier A's decomposition."""
    tr_p = BT.run_backtest_vectorized(df15, sig, sl_dist=sl_arr, tp_dist=tp_arr, cost_rt=0.0,
                                      max_hold=max_hold, sl_first_on_tie=True)
    tr_o = BT.run_backtest_vectorized(df15, sig, sl_dist=sl_arr, tp_dist=tp_arr, cost_rt=0.0,
                                      max_hold=max_hold, sl_first_on_tie=False)
    n = min(len(tr_p), len(tr_o))
    tr_p, tr_o = tr_p.iloc[:n].reset_index(drop=True), tr_o.iloc[:n].reset_index(drop=True)
    assert np.array_equal(tr_p["entry_time"].to_numpy(), tr_o["entry_time"].to_numpy())
    is_tie = (tr_p["reason"].to_numpy() != tr_o["reason"].to_numpy())
    return tr_p, tr_o, is_tie


def apply_m1_resolution(tr_p: pd.DataFrame, tr_o: pd.DataFrame, is_tie: np.ndarray,
                        m1_df: pd.DataFrame, bar_minutes: int = 15):
    """For every tie trade, slice the M1 sub-bars composing the ambiguous 15-min exit bar
    and resolve at M1 resolution. Returns (ret_m1_resolved, frac_m1_still_ambiguous,
    n_ties, n_m1_lookup_ok)."""
    ret_p = tr_p["ret_gross"].to_numpy(float).copy()
    entry_px = tr_p["entry_px"].to_numpy(float)
    direction = tr_p["direction"].to_numpy(int)
    exit_time = tr_p["exit_time"]
    ret_out = ret_p.copy()
    n_m1_ambig = 0
    n_lookup_ok = 0
    tie_idx = np.where(is_tie)[0]
    for i in tie_idx:
        sl_px = tr_p["exit_px"].iat[i]   # pessimistic run always picks sl on a tie
        tp_px = tr_o["exit_px"].iat[i]   # optimistic run always picks tp on the same tie
        bar_start = exit_time.iat[i]
        bar_end = bar_start + pd.Timedelta(minutes=bar_minutes)
        sub = m1_df.loc[(m1_df.index >= bar_start) & (m1_df.index < bar_end)]
        if sub.empty:
            continue  # no M1 coverage for this bar -- leave pessimistic (flagged in report)
        n_lookup_ok += 1
        xp, reason, ambiguous = m1_tie_resolve(sub, direction[i], sl_px, tp_px)
        if xp is None:
            continue
        if ambiguous:
            n_m1_ambig += 1
        ret_out[i] = direction[i] * (xp / entry_px[i] - 1.0)
    n_ties = int(is_tie.sum())
    frac_ambig = (n_m1_ambig / n_lookup_ok) if n_lookup_ok else float("nan")
    return ret_out, frac_ambig, n_ties, n_lookup_ok


# ------------------------------------------------------------------ B1: synthetic M1 noise

def load_real_m1_relrange(symbol: str, n_sample: int = 500_000) -> tuple[np.ndarray, float]:
    df = pd.read_csv(DEEP / f"{symbol}_M1.csv", usecols=["open", "high", "low", "close"], nrows=n_sample)
    rr = ((df["high"] - df["low"]) / df["close"]).replace(0, np.nan).dropna().to_numpy(float)
    ret = np.log(df["close"] / df["close"].shift(1)).dropna()
    ret = ret[ret != 0].to_numpy(float)
    return rr, float(np.std(ret))


def gen_m1_noise(n_bars_15: int, rr_pool: np.ndarray, sigma_m1: float, rng, bar_minutes: int = 15,
                 s0: float = 100.0) -> pd.DataFrame:
    """Generate i.i.d.-return M1 bars (real bootstrapped M1 range, zero autocorrelation,
    zero genuine structure at any horizon) then aggregate to 15-min for the outer signal."""
    n_m1 = n_bars_15 * bar_minutes
    logret = rng.normal(0.0, sigma_m1, size=n_m1)
    logret[0] = 0.0
    close = s0 * np.exp(np.cumsum(logret))
    open_ = np.empty(n_m1); open_[0] = s0; open_[1:] = close[:-1]
    rr = rng.choice(rr_pool, size=n_m1, replace=True)
    prev_close = np.r_[s0, close[:-1]]
    body_hi = np.maximum(open_, close); body_lo = np.minimum(open_, close)
    wick = 0.5 * rr * prev_close
    high = body_hi + wick
    low = body_lo - wick
    idx = pd.date_range("2020-01-01", periods=n_m1, freq="1min")
    m1 = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=idx)
    df15 = (m1.resample(f"{bar_minutes}min")
             .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
             .dropna())
    return m1, df15


def canonical_signal(df15: pd.DataFrame):
    z = ind.zscore(df15["close"], Z_N)
    zz = np.nan_to_num(z.to_numpy(float), nan=0.0)
    sig = np.where(zz <= -Z_THRESHOLD, 1.0, np.where(zz >= Z_THRESHOLD, -1.0, 0.0))
    atrN = ind.atr(df15["high"], df15["low"], df15["close"], n=ATR_N)
    sl = (WIDTH * atrN).to_numpy(float)
    tp = (WIDTH * atrN).to_numpy(float)
    return sig, sl, tp


def experiment_b1():
    print("=== B1: synthetic M1-level noise, canonical cell (1.0xATR, H=8) ===")
    rr_pool, sigma_m1 = load_real_m1_relrange("US100", n_sample=500_000)
    print(f"  bootstrapped {len(rr_pool)} real US100 M1 relative-range values "
          f"(median {np.median(rr_pool)*1e4:.3f}bps), M1 logret sigma={sigma_m1*1e4:.3f}bps")
    rng = np.random.default_rng(20260821)
    K = 10
    all_p, all_o, all_tie, all_m1res = [], [], [], []
    total_ambig, total_lookup = 0, 0
    for d in range(K):
        m1, df15 = gen_m1_noise(20000, rr_pool, sigma_m1, rng)
        sig, sl, tp = canonical_signal(df15)
        tr_p, tr_o, is_tie = find_ties(df15, sig, sl, tp, HOLD)
        ret_m1, frac_ambig, n_ties, n_lookup = apply_m1_resolution(tr_p, tr_o, is_tie, m1)
        all_p.append(tr_p["ret_gross"].to_numpy(float))
        all_o.append(tr_o["ret_gross"].to_numpy(float))
        all_tie.append(is_tie)
        all_m1res.append(ret_m1)
        total_ambig += int(round(frac_ambig * n_lookup)) if n_lookup else 0
        total_lookup += n_lookup
    ret_p = np.concatenate(all_p); ret_o = np.concatenate(all_o)
    is_tie = np.concatenate(all_tie); ret_m1 = np.concatenate(all_m1res)
    unbiased = np.where(is_tie, 0.5 * (ret_p + ret_o), ret_p)
    _, t_p = S.hac_tstat(ret_p, lags=6)
    _, t_m1 = S.hac_tstat(ret_m1, lags=6)
    _, t_u = S.hac_tstat(unbiased, lags=6)
    row = dict(experiment="B1_synthetic_noise", n_trades=len(ret_p), n_ties=int(is_tie.sum()),
              frac_tie=float(is_tie.mean()),
              frac_m1_still_ambiguous=(total_ambig / total_lookup) if total_lookup else float("nan"),
              t_pessimistic=t_p, t_m1_resolved=t_m1, t_unbiased_reference=t_u,
              bps_pessimistic=float(ret_p.mean() * 1e4), bps_m1_resolved=float(ret_m1.mean() * 1e4),
              bps_unbiased_reference=float(unbiased.mean() * 1e4),
              bias_before_bps=float((ret_p.mean() - unbiased.mean()) * 1e4),
              bias_after_m1_bps=float((ret_m1.mean() - unbiased.mean()) * 1e4))
    print(f"  n_trades={row['n_trades']} n_ties={row['n_ties']} frac_tie={row['frac_tie']:.4f} "
          f"frac_m1_still_ambiguous={row['frac_m1_still_ambiguous']:.4f}")
    print(f"  t_pessimistic={t_p:+.3f}  t_m1_resolved={t_m1:+.3f}  t_unbiased_ref={t_u:+.3f}")
    print(f"  bias BEFORE m1 (bps)={row['bias_before_bps']:+.4f}  bias AFTER m1 (bps)={row['bias_after_m1_bps']:+.4f}")
    return row


# ------------------------------------------------------------------ B2: real data

def experiment_b2(symbol: str):
    print(f"=== B2: real data, {symbol}, canonical cell (1.0xATR, H=8) ===")
    df15 = DL.load(symbol, bar="15min")
    sig, sl, tp = canonical_signal(df15)
    tr_p, tr_o, is_tie = find_ties(df15, sig, sl, tp, HOLD)
    print(f"  loading real M1 for {symbol} (full file, read-only)...")
    t0 = time.time()
    m1_raw = pd.read_csv(DEEP / f"{symbol}_M1.csv", usecols=["timestamp_utc", "open", "high", "low", "close"],
                         dtype={"open": "float64", "high": "float64", "low": "float64", "close": "float64"})
    m1_raw.index = pd.to_datetime(m1_raw["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    m1_raw = m1_raw.drop(columns=["timestamp_utc"]).sort_index()
    print(f"  loaded {len(m1_raw)} M1 rows ({time.time()-t0:.1f}s)")
    ret_m1, frac_ambig, n_ties, n_lookup = apply_m1_resolution(tr_p, tr_o, is_tie, m1_raw)
    ret_p = tr_p["ret_gross"].to_numpy(float); ret_o = tr_o["ret_gross"].to_numpy(float)
    unbiased = np.where(is_tie, 0.5 * (ret_p + ret_o), ret_p)
    _, t_p = S.hac_tstat(ret_p, lags=6)
    _, t_m1 = S.hac_tstat(ret_m1, lags=6)
    _, t_u = S.hac_tstat(unbiased, lags=6)
    row = dict(experiment=f"B2_real_{symbol}", n_trades=len(ret_p), n_ties=n_ties,
              frac_tie=float(is_tie.mean()),
              frac_m1_still_ambiguous=(frac_ambig if n_lookup else float("nan")),
              n_m1_lookup_ok=n_lookup,
              t_pessimistic=t_p, t_m1_resolved=t_m1, t_unbiased_reference=t_u,
              bps_pessimistic=float(ret_p.mean() * 1e4), bps_m1_resolved=float(ret_m1.mean() * 1e4),
              bps_unbiased_reference=float(unbiased.mean() * 1e4),
              bias_before_bps=float((ret_p.mean() - unbiased.mean()) * 1e4),
              bias_after_m1_bps=float((ret_m1.mean() - unbiased.mean()) * 1e4))
    print(f"  n_trades={row['n_trades']} n_ties={n_ties} frac_tie={row['frac_tie']:.4f} "
          f"m1_lookup_ok={n_lookup}/{n_ties} frac_m1_still_ambiguous={row['frac_m1_still_ambiguous']:.4f}")
    print(f"  t_pessimistic={t_p:+.3f}  t_m1_resolved={t_m1:+.3f}  t_unbiased_ref={t_u:+.3f}")
    print(f"  bias BEFORE m1 (bps)={row['bias_before_bps']:+.4f}  bias AFTER m1 (bps)={row['bias_after_m1_bps']:+.4f}")
    return row


def main():
    t0 = time.time()
    rows = [experiment_b1()]
    for sym in ["US100", "XAUUSD"]:
        rows.append(experiment_b2(sym))
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "m1_resolver_results.csv", index=False)
    print(f"\nWrote {len(out)} rows -> m1_resolver_results.csv ({time.time()-t0:.1f}s total)")


if __name__ == "__main__":
    main()
