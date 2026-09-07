"""Part A: pricing map. For each (family, currency), measure how long price
takes to stabilize after the announcement:
  (1) realized-activity (vol) decay profile, event vs vol-matched placebo,
      half-life = time for excess activity to decay to 50% of its peak.
  (2) directional continuation of cumulative return (impact-kernel style):
      sign the move using the first `dir_window` minutes, then track the
      average signed cumulative return out to T+72h -- if it's an Evans-Lyon
      style gradual impact kernel, the curve keeps climbing after T+dir_window;
      if pricing is instantaneous, it flattens immediately.
"""
import numpy as np
import pandas as pd
import os
import json
from lib import (CCY_PAIRS, load_pair, extract_event_matrix, bucket_realized_activity,
                  BUCKET_EDGES_MIN, build_placebo_times, hac_tstat)

EVENTS_DIR = os.path.join(os.path.dirname(__file__), "events")
OUT_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT_DIR, exist_ok=True)

FAMILY_DIR_WINDOW = {  # minutes used to sign the initial move
    "rate_decision": 5,
    "cpi": 15,
    "nfp": 15,
    "gdp": 15,
    "pmi": 15,
}

CONT_OFFSETS = [-60, -30, -15, -5, -1, 0, 1, 5, 15, 30, 60, 120, 240, 480,
                720, 1440, 2160, 2880, 3600, 4320]

N_PLACEBO = 5


def half_life_from_excess(edges_min, excess):
    """edges_min: bucket right-edges (post-event only, all >=0). excess: same
    length, the excess activity curve (already peak-anchored at index of max).
    Returns (peak_h, half_life_h) via linear interpolation, or (nan, nan) if
    it never decays to half."""
    peak_idx = int(np.nanargmax(excess))
    peak_val = excess[peak_idx]
    peak_h = edges_min[peak_idx]
    if peak_val <= 0:
        return peak_h, np.nan
    target = peak_val / 2.0
    for j in range(peak_idx, len(excess) - 1):
        if excess[j] >= target and excess[j + 1] < target:
            # linear interpolate between edges_min[j] and edges_min[j+1]
            x0, x1 = edges_min[j], edges_min[j + 1]
            y0, y1 = excess[j], excess[j + 1]
            if y1 == y0:
                return peak_h, x1
            frac = (target - y0) / (y1 - y0)
            return peak_h, x0 + frac * (x1 - x0)
    return peak_h, np.nan


def currency_proxy_matrix(pairs, event_times, offsets):
    """Average (across pairs, sign-adjusted) cumulative log-return in bps
    relative to offset=0, shape (n_events, n_offsets)."""
    acc = None
    n_pairs = 0
    for pair, sign in pairs:
        mat = extract_event_matrix(pair, event_times, offsets)
        logp = np.log(mat)
        anchor_col = offsets.index(0)
        cum = (logp - logp[:, [anchor_col]]) * sign * 10000.0
        acc = cum if acc is None else acc + cum
        n_pairs += 1
    return acc / n_pairs


def currency_proxy_activity(pairs, event_times, edges=BUCKET_EDGES_MIN):
    acc = None
    for pair, sign in pairs:
        act = bucket_realized_activity(pair, event_times, edges)
        acc = act if acc is None else acc + act
    return acc / len(pairs)


def run_one(family, ccy):
    ev_path = f"{EVENTS_DIR}/{family}_{ccy}.csv"
    ev = pd.read_csv(ev_path, parse_dates=["datetime_utc"])
    if len(ev) < 15:
        return None
    event_times = pd.DatetimeIndex(pd.to_datetime(ev["datetime_utc"], utc=True))
    pairs = CCY_PAIRS[ccy]

    # --- activity / vol decay ---
    act_event = currency_proxy_activity(pairs, event_times)
    placebo_times, src_idx = build_placebo_times(event_times, ccy, event_times, n_placebo=N_PLACEBO)
    act_placebo = currency_proxy_activity(pairs, placebo_times)

    edges = BUCKET_EDGES_MIN
    widths = np.array([edges[i + 1] - edges[i] for i in range(len(edges) - 1)], dtype=float)
    post_mask = np.array(edges[1:]) > 0  # buckets fully post-event (right edge>0); include the [-5,0) as t=0- baseline anchor? use only post
    post_edges = [edges[i + 1] for i in range(len(edges) - 1) if post_mask[i]]
    # normalize by sqrt(bucket width) so buckets of different width are comparable
    # (raw realized-activity scales ~sqrt(time) under a random walk with constant vol rate)
    rate_event = act_event / np.sqrt(widths)[None, :]
    rate_placebo = act_placebo / np.sqrt(widths)[None, :]
    mean_event = np.nanmean(rate_event, axis=0)
    mean_placebo = np.nanmean(rate_placebo, axis=0)
    excess = mean_event - mean_placebo
    excess_post = excess[post_mask]
    peak_h, hl = half_life_from_excess(post_edges, excess_post)

    # HAC t-stat on excess for the peak bucket (event vs placebo distribution)
    peak_bucket_idx = np.where(post_mask)[0][int(np.nanargmax(excess_post))]
    ev_peak = rate_event[:, peak_bucket_idx]
    pb_peak_by_event = np.full(len(event_times), np.nan)
    for i in range(len(event_times)):
        vals = rate_placebo[src_idx == i, peak_bucket_idx]
        if len(vals):
            pb_peak_by_event[i] = np.nanmean(vals)
    diff = ev_peak - pb_peak_by_event
    _, t_peak, n_peak = hac_tstat(diff)

    # --- directional continuation (event AND vol-matched placebo, same method) ---
    dir_w = FAMILY_DIR_WINDOW[family]
    offsets = sorted(set(CONT_OFFSETS + [0, dir_w]))

    def signed_continuation(times):
        cum = currency_proxy_matrix(pairs, times, offsets)
        dir_col = offsets.index(dir_w)
        r0 = cum[:, dir_col]
        sign0 = np.sign(r0)
        sign0[sign0 == 0] = np.nan
        return np.nanmean(cum * sign0[:, None], axis=0)

    cont_curve = signed_continuation(event_times)
    cont_curve_placebo = signed_continuation(placebo_times)
    cont_excess = cont_curve - cont_curve_placebo

    # plateau = mean of last 3 offsets (48h-72h region); half-life to 50% of plateau,
    # measured on the EXCESS (event minus placebo) curve so generic FX momentum in
    # the placebo pool doesn't get counted as an event effect
    plateau = np.nanmean(cont_excess[-3:])
    initial = cont_excess[offsets.index(dir_w)]
    hl_cont = np.nan
    if plateau > 0:
        target = plateau / 2.0
        post_offsets_idx = [k for k, o in enumerate(offsets) if o >= dir_w]
        for j in range(len(post_offsets_idx) - 1):
            a, b = post_offsets_idx[j], post_offsets_idx[j + 1]
            if cont_excess[a] < target <= cont_excess[b] or cont_excess[a] <= target < cont_excess[b]:
                x0, x1 = offsets[a], offsets[b]
                y0, y1 = cont_excess[a], cont_excess[b]
                if y1 != y0:
                    frac = (target - y0) / (y1 - y0)
                    hl_cont = x0 + frac * (x1 - x0)
                break

    result = {
        "family": family, "currency": ccy, "n_events": len(event_times),
        "n_pairs": len(pairs), "pairs": ",".join(p for p, _ in pairs),
        "peak_bucket_h_min": float(peak_h), "vol_half_life_min": float(hl),
        "t_peak_excess": float(t_peak), "n_peak": int(n_peak),
        "dir_window_min": dir_w, "cont_initial_excess_bps": float(initial),
        "cont_plateau_excess_bps": float(plateau), "cont_half_life_min": float(hl_cont),
        "cont_curve_event_final_bps": float(cont_curve[-1]), "cont_curve_placebo_final_bps": float(cont_curve_placebo[-1]),
    }

    detail = {
        "edges_min": edges, "mean_event_activity_rate_bps_sqrtmin": mean_event.tolist(),
        "mean_placebo_activity_rate_bps_sqrtmin": mean_placebo.tolist(),
        "offsets_min": offsets, "cont_curve_event_bps": cont_curve.tolist(),
        "cont_curve_placebo_bps": cont_curve_placebo.tolist(), "cont_excess_bps": cont_excess.tolist(),
    }
    with open(f"{OUT_DIR}/decay_{family}_{ccy}.json", "w") as f:
        json.dump(detail, f, indent=1)
    return result


def main():
    summary = pd.read_csv(f"{EVENTS_DIR}/_summary.csv")
    rows = []
    for _, r in summary.iterrows():
        fam, ccy = r["family"], r["currency"]
        try:
            res = run_one(fam, ccy)
            if res:
                rows.append(res)
                print(f"{fam:15s} {ccy}  peak={res['peak_bucket_h_min']:>6.0f}min "
                      f"vol_hl={res['vol_half_life_min']:>8.1f}min "
                      f"t_peak={res['t_peak_excess']:>5.2f} "
                      f"cont_hl={res['cont_half_life_min']}")
        except Exception as e:
            print(f"FAILED {fam} {ccy}: {e}")
    out = pd.DataFrame(rows)
    out.to_csv(f"{OUT_DIR}/decay_summary.csv", index=False)
    print("\nSaved", f"{OUT_DIR}/decay_summary.csv")


if __name__ == "__main__":
    main()
