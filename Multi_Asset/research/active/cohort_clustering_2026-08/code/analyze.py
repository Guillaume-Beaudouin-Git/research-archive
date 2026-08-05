"""Do the outcomes of successive challenge cohorts CLUSTER beyond what the
cohort overlap already guarantees?

Everything here is a comparison against the overlap-matched placebo. A statistic
that is "far from independence" proves nothing: overlapping cohorts are far from
independence BY CONSTRUCTION. Only real-vs-placebo carries information.

usage: analyze.py [vm] [H ...]
"""
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm as _norm

import cc_lib as C

sp_norm_ppf = _norm.ppf

VM = sys.argv[1] if len(sys.argv) > 1 else "10"
HS = [int(x) for x in sys.argv[2:]] or [28, 35, 42, 49, 56, 63, 70]
H_MAIN = 56
tag = f"vm{VM}"

real = pd.read_csv(C.OUT / f"real_{tag}.csv", parse_dates=["start_date"])
pl = np.load(C.OUT / f"placebo_{tag}.npz", allow_pickle=True)
PL_OUT, PL_CAL = pl["out"], pl["cal"]
NPL = len(PL_OUT)
sd = pd.DatetimeIndex(real["start_date"])
n = len(real)
print(f"{tag}: {n} cohorts {sd[0].date()}..{sd[-1].date()}  placebo reps {NPL}")


def collapse(out, cal, H):
    o = np.where(cal <= H, out, "not_reached")
    return np.where(o == "timeout", "not_reached", o)


def blockboot_var(y, block, n_boot=4000, seed=7):
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(len(y) / block))
    idx = ((np.arange(block)[None, :] +
            rng.integers(0, len(y), size=(n_boot, nb))[:, :, None]) % len(y)
           ).reshape(n_boot, -1)[:, :len(y)]
    return float(y[idx].mean(axis=1).var(ddof=1))


# ---------------------------------------------------------------- 1. timeline
tl = real[["start_date", "out", "cal_days", "td_used", "end_bal"]].copy()
for H in (49, 56, 63):
    tl[f"outcome_H{H}"] = collapse(real["out"].to_numpy(), real["cal_days"].to_numpy(), H)
tl.to_csv(C.TAB / f"cohort_timeline_{tag}.csv", index=False)

# --------------------------------------- 1b. how much do cohorts ACTUALLY overlap?
# The premise "neighbouring cohorts share >95 % of their trajectory" is true of the
# NOMINAL horizon and false of the DECISIVE window: an attempt stops the day it
# resolves, and everything after that day is irrelevant to its outcome.
ov = []
s_i = sd.to_numpy()
for H in HS:
    dur = np.minimum(real["cal_days"].to_numpy(), H)
    end = s_i + dur.astype("timedelta64[D]")
    for lag in (1, 2, 3):
        a0, a1 = s_i[:-lag], end[:-lag]
        b0, b1 = s_i[lag:], end[lag:]
        inter = (np.minimum(a1, b1) - np.maximum(a0, b0)) / np.timedelta64(1, "D")
        union = (np.maximum(a1, b1) - np.minimum(a0, b0)) / np.timedelta64(1, "D")
        jac = np.clip(inter, 0, None) / np.maximum(union, 1)
        nom = np.clip(H - lag * 10.0, 0, None) / (H + lag * 10.0)   # nominal-horizon
        ov.append(dict(H=H, lag=lag, jaccard_decisive_mean=float(jac.mean()),
                       jaccard_decisive_med=float(np.median(jac)),
                       share_zero_overlap=float((jac <= 0).mean()),
                       jaccard_if_full_horizon=float(nom),
                       med_dur_days=float(np.median(dur))))
odf = pd.DataFrame(ov)
odf.to_csv(C.TAB / f"overlap_{tag}.csv", index=False)
print("\n--- ACTUAL overlap of adjacent cohorts (decisive window vs nominal) ---")
print(odf[odf.lag == 1].round(3).to_string(index=False))

# ------------------------------------------------- 2. clustering vs placebo
rows = []
for H in HS:
    lab_r = collapse(real["out"].to_numpy(), real["cal_days"].to_numpy(), H)
    s_r = C.cluster_stats(lab_r)
    s_p = [C.cluster_stats(collapse(PL_OUT[k], PL_CAL[k], H)) for k in range(NPL)]
    dp = pd.DataFrame(s_p)
    keys = ["ac1", "ac2", "ac3", "ac4", "ac6", "ac8", "vr4", "vr8", "vr13",
            "mean_run", "max_run", "p_run_ge5", "n_runs"]
    r = dict(H=H, vm=float(VM), p_real=s_r["p_bar"], p_plac=float(dp.p_bar.mean()))
    for k in keys:
        v = s_r[k]
        pv = dp[k].to_numpy(float)
        r[f"{k}_real"] = v
        r[f"{k}_plac"] = float(np.nanmean(pv))
        r[f"{k}_plac_p5"] = float(np.nanpercentile(pv, 5))
        r[f"{k}_plac_p95"] = float(np.nanpercentile(pv, 95))
        # one-sided p: how often does the placebo cluster AT LEAST as much
        r[f"{k}_pval"] = float((pv >= v).mean())
    # base-rate control. Run lengths depend mechanically on p, and the placebo has
    # no drift so its p sits below the real one. Two controls:
    #  (a) the matched subset of placebo reps, when it is populated;
    #  (b) the placebo statistic REGRESSED on p_bar and evaluated at the real p,
    #      with a prediction interval from the residual spread.
    m = np.abs(dp.p_bar.to_numpy() - s_r["p_bar"]) < 0.05
    r["n_matched"] = int(m.sum())
    pb = dp.p_bar.to_numpy(float)
    for k in ("mean_run", "max_run", "vr4", "vr8", "vr13", "ac1", "p_run_ge5"):
        r[f"{k}_plac_matched"] = float(dp[k][m].mean()) if m.sum() >= 5 else np.nan
        r[f"{k}_pval_matched"] = (float((dp[k][m].to_numpy() >= s_r[k]).mean())
                                  if m.sum() >= 5 else np.nan)
        yy = dp[k].to_numpy(float)
        ok = np.isfinite(yy) & np.isfinite(pb)
        if ok.sum() >= 8 and pb[ok].std() > 1e-6:
            b, a = np.polyfit(pb[ok], yy[ok], 1)
            pred = a + b * s_r["p_bar"]
            resid = yy[ok] - (a + b * pb[ok])
            sdr = float(resid.std(ddof=2))
            r[f"{k}_plac_adj"] = float(pred)
            r[f"{k}_plac_adj_sd"] = sdr
            r[f"{k}_z_vs_adj"] = float((s_r[k] - pred) / sdr) if sdr > 0 else np.nan
            r[f"{k}_slope_p"] = float(b)
        else:
            for s_ in ("_plac_adj", "_plac_adj_sd", "_z_vs_adj", "_slope_p"):
                r[f"{k}{s_}"] = np.nan
    # n_eff: from block-bootstrap variance of p_hat, and from the tiling bound
    y = (lab_r == "pass").astype(float)
    blk = C.L.block_for_horizon(H)
    v = blockboot_var(y, blk)
    r["n_eff_boot"] = float(y.mean() * (1 - y.mean()) / v) if v > 0 else np.nan
    r["n_eff_tiling"] = C.n_eff(sd, H)
    r["n_eff_vr8"] = n / s_r["vr8"] if s_r["vr8"] > 0 else np.nan
    rows.append(r)

cl = pd.DataFrame(rows)
cl.to_csv(C.TAB / f"clustering_{tag}.csv", index=False)

# run-length DISTRIBUTION (the deliverable asks for the block-size distribution)
EDG = [1, 2, 3, 4, 5, 7, 10, 999]
def rl_hist(lab):
    for arr, nm in ((C.runs(lab), "outcome5"),
                    (C.runs((lab == "pass").astype(int).astype(str)), "passbin")):
        h = np.histogram(arr, bins=EDG)[0] / len(arr)
        yield nm, h, float(arr.mean()), int(arr.max())

hh = []
for H in (49, 56, 63):
    lab_r = collapse(real["out"].to_numpy(), real["cal_days"].to_numpy(), H)
    for nm, h, mu, mx in rl_hist(lab_r):
        hh.append(dict(H=H, series=nm, arm="real", mean_run=mu, max_run=mx,
                       **{f"share_len_{EDG[i]}": h[i] for i in range(len(h))}))
    acc = {nm: [] for nm in ("outcome5", "passbin")}
    for k in range(NPL):
        for nm, h, mu, mx in rl_hist(collapse(PL_OUT[k], PL_CAL[k], H)):
            acc[nm].append(np.concatenate([h, [mu, mx]]))
    for nm, v in acc.items():
        a = np.array(v).mean(axis=0)
        hh.append(dict(H=H, series=nm, arm="placebo", mean_run=a[-2], max_run=a[-1],
                       **{f"share_len_{EDG[i]}": a[i] for i in range(len(EDG) - 1)}))
rlh = pd.DataFrame(hh)
rlh.to_csv(C.TAB / f"runlength_hist_{tag}.csv", index=False)
print("\n--- run-length distribution, real vs placebo (share of runs) ---")
print(rlh[rlh.H == H_MAIN].round(3).to_string(index=False))
print("\n--- clustering real vs overlap-matched placebo (pass indicator) ---")
show = ["H", "p_real", "p_plac", "ac1_real", "ac1_plac", "ac1_pval",
        "vr8_real", "vr8_plac", "vr8_pval", "mean_run_real", "mean_run_plac",
        "max_run_real", "max_run_plac", "n_eff_boot", "n_eff_tiling"]
print(cl[show].round(3).to_string(index=False))

# ---------------------------------------------------- 3. seasonality, shift null
def shift_null(y, keys, n_shift=None):
    """Circular shift of the OUTCOME series against fixed calendar labels.
    Preserves the autocorrelation (hence the overlap) EXACTLY; destroys only the
    calendar alignment. Shift 0 = the real series, included as one draw."""
    n = len(y)
    ks = np.unique(keys)
    Kmat = np.array([(keys == k).astype(float) for k in ks])       # (ncell, n)
    cnt = Kmat.sum(axis=1)
    shifts = np.arange(n if n_shift is None else n_shift)
    means = np.array([(Kmat @ np.roll(y, s)) / cnt for s in shifts])  # (nshift, ncell)
    dev = means - y.mean()
    stat = np.abs(dev).max(axis=1)
    rng = np.abs(means.max(axis=1) - means.min(axis=1))
    return ks, means, dev, stat, rng


def seasonality(y, sd, label, cells, cellname):
    ks, means, dev, stat, rng = shift_null(y, cells)
    p_max = float((stat >= stat[0]).mean())
    p_rng = float((rng >= rng[0]).mean())
    out = []
    m = len(ks)
    # Sidak-adjusted two-sided critical z over m cells, + 0.84 for 80 % power
    z_crit = -sp_norm_ppf((1 - (1 - 0.05) ** (1.0 / m)) / 2)
    for j, k in enumerate(ks):
        d0 = dev[0, j]
        p2 = float((np.abs(dev[:, j]) >= abs(d0)).mean())
        sd_dev = float(dev[:, j].std(ddof=1))
        out.append(dict(scope=label, cell=f"{cellname}{k}", n=int((cells == k).sum()),
                        p_cell=means[0, j], dev=d0, p_shift=p2,
                        sd_dev_shift=sd_dev, mde80_pt=100 * (z_crit + 0.8416) * sd_dev))
    o = pd.DataFrame(out)
    o["p_sidak"] = 1 - (1 - o.p_shift.clip(1e-9, 1)) ** m
    o["p_omnibus_maxdev"] = p_max
    o["p_omnibus_range"] = p_rng
    return o


res_seas = []
for H in (49, 56, 63):
    lab = collapse(real["out"].to_numpy(), real["cal_days"].to_numpy(), H)
    y = (lab == "pass").astype(float)
    for scope, msk in (("full", np.ones(n, bool)),
                       ("post2021", np.asarray(sd >= pd.Timestamp("2021-01-01")))):
        ys, ss = y[msk], sd[msk]
        for cn, cells in (("Q", ss.quarter.to_numpy()), ("M", ss.month.to_numpy())):
            o = seasonality(ys, ss, f"{scope}_H{H}", cells, cn)
            o["H"] = H
            res_seas.append(o)
seas = pd.concat(res_seas, ignore_index=True)
seas.to_csv(C.TAB / f"seasonality_{tag}.csv", index=False)
print("\n--- seasonality, circular-shift null (full sample, H=56) ---")
print(seas[(seas.scope == f"full_H{H_MAIN}") & seas.cell.str.startswith("Q")]
      .round(4).to_string(index=False))
print("\n--- months (full, H=56) ---")
print(seas[(seas.scope == f"full_H{H_MAIN}") & seas.cell.str.startswith("M")]
      [["cell", "n", "p_cell", "dev", "p_shift", "p_sidak"]].round(4).to_string(index=False))

# -------------------------------------------------------------- 4. era split
era = []
for H in HS:
    lab = collapse(real["out"].to_numpy(), real["cal_days"].to_numpy(), H)
    for name, msk in (("full", np.ones(n, bool)),
                      ("pre2021", np.asarray(sd < pd.Timestamp("2021-01-01"))),
                      ("post2021", np.asarray(sd >= pd.Timestamp("2021-01-01")))):
        s = C.cluster_stats(lab[msk])
        y = (lab[msk] == "pass").astype(float)
        blk = C.L.block_for_horizon(H)
        v = blockboot_var(y, blk)
        pp = [float((collapse(PL_OUT[k], PL_CAL[k], H)[msk] == "pass").mean())
              for k in range(NPL)]
        era.append(dict(H=H, era=name, n=int(msk.sum()), p_pass=s["p_bar"],
                        p_placebo=float(np.mean(pp)),
                        edge=s["p_bar"] - float(np.mean(pp)),
                        pl_p5=float(np.percentile(pp, 5)),
                        pl_p95=float(np.percentile(pp, 95)),
                        ac1=s["ac1"], vr8=s["vr8"], mean_run=s["mean_run"],
                        max_run=s["max_run"],
                        n_eff=float(y.mean() * (1 - y.mean()) / v) if v > 0 else np.nan))
ed = pd.DataFrame(era)
ed.to_csv(C.TAB / f"era_{tag}.csv", index=False)
print("\n--- era split ---")
print(ed[ed.H.isin([49, 56, 63])].round(3).to_string(index=False))
