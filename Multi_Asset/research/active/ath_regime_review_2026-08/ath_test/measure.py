"""STEP 3-4 — conditional EV of the deployed overnight sleeve by distance to the ATH.

Objects: the two raw legs (US100, GER40) gross and net, and the reconstructed MONO book at
deployed leverage. Conditioners: C1 (expanding ATH drawdown) and C2 (52-week-high ratio).

Controls, all mandatory: matched circular-rotation placebo, unconditional-baseline check
(L58), stationary block bootstrap (never iid), sub-period stability.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

REPO = Path("<HOME>/Desktop/Algo_claude")
OVERLAY = REPO / "Multi_Asset/research/active/regime_overlay_ftmo_2026-07"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "outputs"

sys.path.insert(0, str(OVERLAY))
sys.path.insert(0, str(REPO))
import build_book as B  # noqa: E402
from Portfolio.admission.marginal import stationary_bootstrap_indices  # noqa: E402

import conditioner as C  # noqa: E402

N_PLACEBO = 999
N_BOOT = 10_000
MEAN_BLOCK = 10.0
SUBPERIODS = [
    ("2013-10..2016", "2013-10-01", "2016-12-31"),
    ("2017..2019", "2017-01-01", "2019-12-31"),
    ("2020..2021", "2020-01-01", "2021-12-31"),
    ("2022..2026-06", "2022-01-01", "2026-06-05"),
]


def hac_t(y: np.ndarray, x: np.ndarray | None = None, lags: int = 6):
    """HAC Newey-West t on a mean (x=None) or on a dummy slope."""
    X = np.ones((len(y), 1)) if x is None else sm.add_constant(x.astype(float))
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    i = 0 if x is None else 1
    return float(res.params[i]), float(res.tvalues[i])


def desc(y: np.ndarray, scale: float = 1.0) -> dict:
    y = np.asarray(y, float)
    m, t = hac_t(y)
    return dict(
        n=int(len(y)), mean=float(y.mean()) * scale, t_HAC=t,
        median=float(np.median(y)) * scale,
        skew=float(pd.Series(y).skew()), exkurt=float(pd.Series(y).kurtosis()),
        p1=float(np.percentile(y, 1)) * scale, p5=float(np.percentile(y, 5)) * scale,
        vol_ann=float(y.std(ddof=1)) * scale * np.sqrt(252.0),
    )


def contrast(y: np.ndarray, flag: np.ndarray, seed: int = 5) -> dict:
    """B0-vs-rest mean contrast with HAC t, block-bootstrap CI, matched placebo."""
    y = np.asarray(y, float)
    f = np.asarray(flag, bool)
    diff, t = hac_t(y, f.astype(float))
    n = len(y)

    rng = np.random.default_rng(seed)
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        idx = stationary_bootstrap_indices(n, MEAN_BLOCK, rng)
        yy, ff = y[idx], f[idx]
        boot[i] = (yy[ff].mean() - yy[~ff].mean()) if 0 < ff.sum() < n else np.nan
    boot = boot[np.isfinite(boot)]

    # matched placebo: circular rotations preserve duty cycle AND run-length structure
    shifts = np.random.default_rng(seed + 1).choice(
        np.arange(20, n - 20), size=min(N_PLACEBO, max(n - 40, 1)), replace=False)
    pl, pl_grp = np.empty(len(shifts)), np.empty(len(shifts))
    for j, s in enumerate(shifts):
        ff = np.roll(f, int(s))
        pl[j] = y[ff].mean() - y[~ff].mean()
        pl_grp[j] = y[ff].mean()

    uncond = float(y.mean())
    se_pool = float(y.std(ddof=1) / np.sqrt(f.sum()))
    return dict(
        diff=diff, t_HAC=t,
        boot_lo=float(np.percentile(boot, 2.5)), boot_hi=float(np.percentile(boot, 97.5)),
        boot_p_gt0=float((boot > 0).mean()),
        placebo_p50=float(np.percentile(pl, 50)), placebo_p95=float(np.percentile(pl, 95)),
        placebo_p05=float(np.percentile(pl, 5)),
        placebo_pctile=float((pl < diff).mean()),
        uncond_mean=uncond, placebo_pool_mean=float(pl_grp.mean()),
        baseline_bias_in_SE=float(abs(pl_grp.mean() - uncond) / se_pool) if se_pool > 0 else np.nan,
    )


def bucket_table(y: pd.Series, dd: pd.Series, scale: float = 1.0) -> pd.DataFrame:
    b = C.bucketize(dd)
    rows = {}
    for name in C.BUCKET_NAMES:
        m = (b == name).to_numpy()
        if m.sum() >= 20:
            rows[name] = desc(y[m].to_numpy(), scale)
    rows["ALL"] = desc(y.to_numpy(), scale)
    return pd.DataFrame(rows).T


def decile_table(y: pd.Series, dd: pd.Series, scale: float = 1.0) -> pd.DataFrame:
    q = pd.qcut(dd, 10, labels=False, duplicates="drop")
    rows = {}
    for d in sorted(pd.Series(q).dropna().unique()):
        m = (q == d).to_numpy()
        r = desc(y[m].to_numpy(), scale)
        r["dd_mid"] = float(dd[m].median())
        rows[f"D{int(d) + 1}"] = r
    return pd.DataFrame(rows).T


def analyse(tag: str, y: pd.Series, dd: pd.Series, scale: float, res: dict) -> None:
    """One object x one conditioner: buckets, deciles, contrast, sub-periods."""
    j = pd.concat([y.rename("y"), dd.rename("dd")], axis=1).dropna()
    if len(j) < 100:
        return
    yy, dds = j["y"], j["dd"]
    flag = (dds <= 0.01).to_numpy()

    res[tag] = {
        "buckets": bucket_table(yy, dds, scale).to_dict(orient="index"),
        "deciles": decile_table(yy, dds, scale).to_dict(orient="index"),
        "contrast": {k: (v * scale if k in ("diff", "boot_lo", "boot_hi", "placebo_p50",
                                            "placebo_p95", "placebo_p05", "uncond_mean",
                                            "placebo_pool_mean") else v)
                     for k, v in contrast(yy.to_numpy(), flag).items()},
        "duty_cycle": float(flag.mean()),
        "n": int(len(j)),
    }
    sub = {}
    for name, lo, hi in SUBPERIODS:
        m = (j.index >= lo) & (j.index <= hi)
        if m.sum() < 60 or not (0 < flag[m].sum() < m.sum()):
            continue
        d, t = hac_t(yy[m].to_numpy(), flag[m].astype(float))
        sub[name] = dict(n=int(m.sum()), n_B0=int(flag[m].sum()),
                         mean_B0=float(yy[m][flag[m]].mean()) * scale,
                         mean_rest=float(yy[m][~flag[m]].mean()) * scale,
                         diff=d * scale, t_HAC=t)
    res[tag]["subperiods"] = sub


def main() -> None:
    OUT.mkdir(exist_ok=True)
    M = B.build_market()
    dates = pd.DatetimeIndex(M["dates"])
    WT, ON = B.mono_signals(dates)

    cond = pd.read_parquet(CACHE / "conditioners.parquet")
    legs = pd.read_parquet(CACHE / "leg_returns.parquet").reindex(dates)
    book = B.run_book(M, WT, ON, B.CFG_MONO)

    on = pd.Series(np.isin(dates.dayofweek, [0, 1]), index=dates)
    res: dict = {}

    # ---- objects (a): raw legs, gross and net, on ON days, own-index conditioner
    for sym in ("US100", "GER40"):
        for kind in ("gross", "net"):
            y = legs[f"{sym}_{kind}_bps"][on.to_numpy()]
            for cc in ("C1", "C2"):
                analyse(f"leg_{sym}_{kind}_{cc}", y, cond[f"{cc}_{sym}"], 1.0, res)

    # ---- object (b): the deployed MONO book, conditioned on US100 (primary)
    r = book["ret"]
    act = r != 0.0
    for cc in ("C1", "C2"):
        analyse(f"book_active_{cc}_US100", r[act], cond[f"{cc}_US100"], 1e4, res)
        analyse(f"book_alldays_{cc}_US100", r, cond[f"{cc}_US100"], 1e4, res)
    # secondary book conditioners (diagnostic colour, not headlines)
    analyse("book_active_C1_GER40", r[act], cond["C1_GER40"], 1e4, res)
    mn = cond[["C1_US100", "C1_GER40"]].min(axis=1)
    analyse("book_active_C1_minboth", r[act], mn, 1e4, res)

    # ---- barrier-relevant tail of the book by bucket (P(day < -5%))
    tail = {}
    for cc in ("C1", "C2"):
        b = C.bucketize(cond[f"{cc}_US100"])
        for name in C.BUCKET_NAMES:
            m = ((b == name) & act).to_numpy()
            if m.sum() >= 20:
                tail[f"{cc}_{name}"] = dict(
                    n=int(m.sum()),
                    p_day_lt_m5pct=float((r[m] < -0.05).mean()),
                    p_day_lt_m10pct=float((r[m] < -0.10).mean()),
                    worst=float(r[m].min()) * 100.0)
    res["book_tail_by_bucket"] = tail

    (OUT / "measure.json").write_text(json.dumps(res, indent=2, default=float))

    # ---- console report
    print("=== BUCKET TABLES (mean in bps; legs = per night, book = per active day) ===")
    for tag in ("leg_US100_net_C1", "leg_GER40_net_C1",
                "book_active_C1_US100", "book_active_C2_US100"):
        if tag not in res:
            continue
        print(f"\n--- {tag}  (duty cycle B0 = {res[tag]['duty_cycle']:.3f}, N={res[tag]['n']})")
        print(pd.DataFrame(res[tag]["buckets"]).T[
            ["n", "mean", "t_HAC", "median", "skew", "exkurt", "p1", "p5", "vol_ann"]
        ].to_string(float_format=lambda x: f"{x:.3f}"))

    print("\n=== HEADLINE CONTRAST  B0 (at the high) minus REST ===")
    rows = {}
    for tag, v in res.items():
        if tag == "book_tail_by_bucket" or "contrast" not in v:
            continue
        c = v["contrast"]
        rows[tag] = dict(n=v["n"], duty=v["duty_cycle"], diff=c["diff"], t_HAC=c["t_HAC"],
                         boot_lo=c["boot_lo"], boot_hi=c["boot_hi"],
                         plac_p50=c["placebo_p50"], plac_p95=c["placebo_p95"],
                         plac_pctile=c["placebo_pctile"],
                         baseline_bias_SE=c["baseline_bias_in_SE"])
    tab = pd.DataFrame(rows).T
    tab.to_csv(OUT / "contrast_table.csv")
    print(tab.to_string(float_format=lambda x: f"{x:.3f}"))

    print("\n=== BOOK TAIL BY BUCKET (barrier-relevant) ===")
    print(pd.DataFrame(tail).T.to_string(float_format=lambda x: f"{x:.4f}"))

    print("\n=== SUB-PERIOD STABILITY (book, C1 US100, active days) ===")
    print(pd.DataFrame(res["book_active_C1_US100"]["subperiods"]).T.to_string(
        float_format=lambda x: f"{x:.3f}"))

    print("\n=== DECILE MONOTONICITY (book, C1 US100, active days) ===")
    print(pd.DataFrame(res["book_active_C1_US100"]["deciles"]).T[
        ["n", "dd_mid", "mean", "t_HAC", "vol_ann"]].to_string(
        float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
