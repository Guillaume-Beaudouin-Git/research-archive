"""Part B / B': FX equivalent of the pre-FOMC drift (L42). Test, for each
(family, currency), whether there is a systematic pre-event drift over
several lookback windows, ending exactly at the announcement (T-1 signal is
not applicable here -- the test is unconditional on any forecast, purely "is
there a mean move in the window preceding a KNOWN date"). No sign is chosen
post-hoc: we report the raw signed mean for every window, then flag the ones
whose |t| clears both the real-sample HAC gate AND the vol-matched placebo
percentile gate (L58).
"""
import numpy as np
import pandas as pd
import os
import json
from lib import CCY_PAIRS, extract_event_matrix, build_placebo_times, hac_tstat, block_bootstrap_mean, mde

EVENTS_DIR = os.path.join(os.path.dirname(__file__), "events")
OUT_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT_DIR, exist_ok=True)

PRE_WINDOWS_MIN = [-30, -60, -120, -240, -1440]  # 30min,1h,2h,4h,24h before
N_PLACEBO = 8
N_FOLDS = 5


def currency_proxy_ret(pairs, event_times, offsets):
    acc = None
    for pair, sign in pairs:
        mat = extract_event_matrix(pair, event_times, offsets)
        logp = np.log(mat)
        acc = (logp * sign) if acc is None else acc + logp * sign
    return acc / len(pairs)  # avg log price level (sign-adjusted) per pair, not meaningful alone; use diffs


def pre_drift(pairs, event_times, window_min):
    """Return per-event pre-window drift in bps: log(P(0)) - log(P(window_min))
    sign-adjusted per currency convention, averaged across pairs."""
    offsets = [window_min, 0]
    acc = np.zeros(len(event_times))
    for pair, sign in pairs:
        mat = extract_event_matrix(pair, event_times, offsets)
        d = (np.log(mat[:, 1]) - np.log(mat[:, 0])) * sign * 10000.0
        acc += d
    return acc / len(pairs)


def walk_forward_sign(vals, n_folds=N_FOLDS):
    vals = np.asarray(vals, dtype=float)
    vals = vals[~np.isnan(vals)]
    n = len(vals)
    if n < n_folds * 3:
        return np.nan, 0, n_folds
    full_sign = np.sign(np.nanmean(vals))
    edges = np.linspace(0, n, n_folds + 1).astype(int)
    same = 0
    for k in range(n_folds):
        seg = vals[edges[k]:edges[k + 1]]
        if len(seg) == 0:
            continue
        if np.sign(np.mean(seg)) == full_sign and full_sign != 0:
            same += 1
    return full_sign, same, n_folds


def run_one(family, ccy):
    ev_path = f"{EVENTS_DIR}/{family}_{ccy}.csv"
    ev = pd.read_csv(ev_path, parse_dates=["datetime_utc"])
    if len(ev) < 15:
        return []
    event_times = pd.DatetimeIndex(pd.to_datetime(ev["datetime_utc"], utc=True))
    pairs = CCY_PAIRS[ccy]
    placebo_times, src_idx = build_placebo_times(event_times, ccy, event_times, n_placebo=N_PLACEBO)

    rows = []
    for w in PRE_WINDOWS_MIN:
        real = pre_drift(pairs, event_times, w)
        placebo = pre_drift(pairs, placebo_times, w)

        mean_real, t_real, n_real = hac_tstat(real)
        mean_placebo_pool = np.nanmean(placebo)

        # percentile of real mean within a placebo sampling distribution
        # (draw same-size subsamples from the placebo pool with replacement)
        rng = np.random.default_rng(hash((family, ccy, w)) % (2**32))
        boot_means = np.array([np.nanmean(rng.choice(placebo[~np.isnan(placebo)], size=n_real, replace=True))
                                for _ in range(2000)]) if np.isfinite(placebo).sum() > 5 else np.array([np.nan])
        pct = float((boot_means < mean_real).mean()) if np.isfinite(boot_means).all() else np.nan

        bb = block_bootstrap_mean(real, n_boot=3000, block=5)
        ci_lo, ci_hi = np.nanpercentile(bb, [2.5, 97.5])

        sign_fold, same_folds, n_folds = walk_forward_sign(real)

        sigma = np.nanstd(real)
        mde_val = mde(sigma, n_real)

        rows.append({
            "family": family, "currency": ccy, "window_min": w, "n": n_real,
            "mean_bps": mean_real, "t_hac": t_real,
            "placebo_pool_mean_bps": float(mean_placebo_pool),
            "placebo_percentile": pct,
            "bb_ci_lo": float(ci_lo), "bb_ci_hi": float(ci_hi),
            "wf_same_sign_folds": same_folds, "wf_n_folds": n_folds,
            "mde_bps": mde_val, "effect_over_mde": abs(mean_real) / mde_val if mde_val and mde_val > 0 else np.nan,
        })
    return rows


def main():
    summary = pd.read_csv(f"{EVENTS_DIR}/_summary.csv")
    all_rows = []
    for _, r in summary.iterrows():
        fam, ccy = r["family"], r["currency"]
        try:
            rows = run_one(fam, ccy)
            all_rows.extend(rows)
            for row in rows:
                print(f"{fam:15s} {ccy} w={row['window_min']:>5d}min  mean={row['mean_bps']:>7.2f}bps "
                      f"t={row['t_hac']:>5.2f} pctl_vs_placebo={row['placebo_percentile']:.3f} "
                      f"wf={row['wf_same_sign_folds']}/{row['wf_n_folds']} eff/mde={row['effect_over_mde']:.2f}")
        except Exception as e:
            print(f"FAILED {fam} {ccy}: {e}")
    out = pd.DataFrame(all_rows)
    out.to_csv(f"{OUT_DIR}/drift_summary.csv", index=False)
    print("\nSaved", f"{OUT_DIR}/drift_summary.csv", "n_tests=", len(out))


if __name__ == "__main__":
    main()
