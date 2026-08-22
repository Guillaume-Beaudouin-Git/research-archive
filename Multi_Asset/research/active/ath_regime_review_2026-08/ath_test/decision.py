"""STEP 5 — decision translation at the CONFIRMED PHASE-2 geometry.

Account state confirmed by the risk-bearer: PHASE 2, EUR 10,000 fresh equity, target +5%
(10,500), static floor 90% of initial (9,000), daily budget 5% (500) anchored 00:00 CET.
Every p(pass) and duration below is therefore a **PHASE-2 (+5%)** figure. No P1 number and
no P1->P2 funnel number is quoted as a headline.

The min-trading-days backstop is modelled explicitly (`flat_after_target`), because a P2
account can reach +5% before it has 4 open days — the exact failure the Step-0 audit found
in the inherited config literal.

Decision rule, pre-registered: a conditional exposure variant must beat its
VOLATILITY-MATCHED CONSTANT DE-LEVER on Delta p(pass). A variant that cannot is a sizing
parameter in disguise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
OVERLAY = REPO / "Multi_Asset/research/active/regime_overlay_ftmo_2026-07"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "outputs"

sys.path.insert(0, str(OVERLAY))
sys.path.insert(0, str(REPO))
import build_book as B  # noqa: E402
from Portfolio.admission.barrier import BarrierConfig  # noqa: E402
from Portfolio.admission.marginal import stationary_bootstrap_indices  # noqa: E402

PASS, FLOOR, DAILY, TIMEOUT = 0, 1, 2, 3
N_PATHS = 20_000
MEAN_BLOCK = 10.0
CUT = 0.30                    # exposure in the cut state (same shape as the 2026-07 study)


def draw(n_obs: int, n_paths: int, horizon: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    reps = int(np.ceil(horizon / n_obs)) + 1
    out = np.empty((n_paths, horizon), dtype=np.int32)
    for p in range(n_paths):
        out[p] = np.concatenate(
            [stationary_bootstrap_indices(n_obs, MEAN_BLOCK, rng) for _ in range(reps)]
        )[:horizon]
    return out


def run_p2(ret: np.ndarray, act: np.ndarray, idx: np.ndarray, cfg: BarrierConfig,
           flat_after_target: bool) -> dict:
    """Single PHASE-2 (+5%) run, vectorised over bootstrap paths.

    flat_after_target=True models the rational trader who, once above target with fewer
    than min_days open days, stops posting size and ticks the counter with a token trade.
    False reproduces the inherited behaviour of forcing full-size risk until the counter
    fills — the behaviour the Step-0 audit showed converts winners into deaths.
    """
    R, A = ret[idx], act[idx]
    P, H = R.shape
    bal = np.ones(P)
    traded = np.zeros(P, dtype=np.int32)
    out = np.full(P, -1, dtype=np.int8)
    end = np.zeros(P, dtype=np.int32)
    floor = 1.0 - cfg.static_floor
    goal = 1.0 + cfg.target_p2
    live = np.ones(P, dtype=bool)
    above = np.zeros(P, dtype=bool)

    for k in range(cfg.horizon_days):
        if not live.any():
            break
        i = np.where(live)[0]
        r = R[i, k].copy()
        a = A[i, k]
        if flat_after_target:
            r = np.where(above[i], 0.0, r)          # token trade: no market risk
        day_open = bal[i]
        nb = day_open * (1.0 + r)
        bal[i] = nb
        traded[i] += a

        hit_daily = nb <= day_open * (1.0 - cfg.daily_stop)
        hit_floor = (~hit_daily) & (nb <= floor)
        ok = (~hit_daily) & (~hit_floor) & (nb >= goal)
        hit_pass = ok & (traded[i] >= cfg.min_days_p2)
        above[i] = np.where(ok & ~hit_pass, True, above[i])

        for mask, code in ((hit_daily, DAILY), (hit_floor, FLOOR), (hit_pass, PASS)):
            if mask.any():
                sel = i[mask]
                out[sel] = code
                end[sel] = k + 1
                live[sel] = False

    still = np.where(live)[0]
    out[still] = TIMEOUT
    end[still] = cfg.horizon_days
    days = np.where(out == PASS, end, np.nan).astype(float)
    return {"out": out, "days": days, "above_at_end": above}


def summarize(res: dict) -> dict:
    out, days = res["out"], res["days"]
    fd = days[~np.isnan(days)]
    dead = out != PASS
    return dict(
        p_pass=float((out == PASS).mean()),
        p_fail_daily=float((out == DAILY).mean()),
        p_fail_floor=float((out == FLOOR).mean()),
        p_timeout=float((out == TIMEOUT).mean()),
        share_dead_above_target=float(res["above_at_end"][dead].mean()) if dead.any() else 0.0,
        median_days=float(np.median(fd)) if fd.size else np.nan,
        p90_days=float(np.percentile(fd, 90)) if fd.size else np.nan,
    )


def paired_ci(a: np.ndarray, b: np.ndarray, n_boot: int = 4000, seed: int = 7):
    d = (b == PASS).astype(float) - (a == PASS).astype(float)
    rng = np.random.default_rng(seed)
    bt = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(n_boot)])
    return float(d.mean()), float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))


def series_for(M, WT, ON, expo: np.ndarray | None):
    bk = B.run_book(M, WT, ON, B.CFG_MONO, vm_series=expo)
    return bk["ret"].to_numpy(), (bk["ret"].to_numpy() != 0.0).astype(np.int32)


def match_vol(M, WT, ON, target_sd: float, n: int) -> tuple[float, np.ndarray]:
    """Constant multiplier carrying the same realised daily vol as the variant."""
    lo, hi = 0.05, 1.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        sd = B.run_book(M, WT, ON, B.CFG_MONO, vm_series=np.full(n, mid))["ret"].std(ddof=1)
        if sd > target_sd:
            hi = mid
        else:
            lo = mid
    return mid, np.full(n, mid)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    M = B.build_market()
    dates = pd.DatetimeIndex(M["dates"])
    WT, ON = B.mono_signals(dates)
    n = M["n"]
    cond = pd.read_parquet(CACHE / "conditioners.parquet")

    variants = {"baseline": None}
    for cc in ("C1", "C2"):
        b0 = (cond[f"{cc}_US100"] <= 0.01).fillna(False).to_numpy()
        variants[f"Vplus_{cc}"] = np.where(b0, CUT, 1.0)      # cut AT the high
        variants[f"Vminus_{cc}"] = np.where(b0, 1.0, CUT)     # cut AWAY from the high

    ser = {k: series_for(M, WT, ON, v) for k, v in variants.items()}

    # vol-matched constant de-lever for every conditional variant
    for k in [k for k in list(ser) if k != "baseline"]:
        sd = ser[k][0].std(ddof=1)
        c, vec = match_vol(M, WT, ON, sd, n)
        ser[f"delever_for_{k}"] = series_for(M, WT, ON, vec)
        variants[f"delever_for_{k}"] = vec
        print(f"vol-matched de-lever for {k}: c = {c:.4f}")

    cfg = BarrierConfig()
    idx = draw(n, N_PATHS, cfg.horizon_days + 5, seed=0)

    rows, outs = {}, {}
    for mode, flat in (("CORRECTED(flat_after_target)", True), ("INHERITED(no backstop)", False)):
        for k, (r, a) in ser.items():
            res = run_p2(r, a, idx, cfg, flat_after_target=flat)
            rows[(mode, k)] = summarize(res)
            rows[(mode, k)]["ann_vol"] = float(r.std(ddof=1) * np.sqrt(252.0))
            outs[(mode, k)] = res["out"]

    tab = pd.DataFrame(rows).T
    base = {m: outs[(m, "baseline")] for m in {k[0] for k in outs}}
    dp, lo, hi = [], [], []
    for (m, k) in tab.index:
        d, l, h = paired_ci(base[m], outs[(m, k)])
        dp.append(d); lo.append(l); hi.append(h)
    tab["dp_vs_base"], tab["ci_lo"], tab["ci_hi"] = dp, lo, hi
    tab.to_csv(OUT / "decision_p2.csv")

    print("\n=== PHASE-2 (+5%) CAMPAIGN — target 10,500 / floor 9,000 / daily 500 ===")
    print(tab.to_string(float_format=lambda x: f"{x:.4f}"))

    print("\n=== THE CONTROL THAT KILLS: variant vs its vol-matched constant de-lever ===")
    ver = {}
    for m in ("CORRECTED(flat_after_target)", "INHERITED(no backstop)"):
        for k in [x for x in ser if x.startswith(("Vplus", "Vminus"))]:
            v = tab.loc[(m, k)]
            d = tab.loc[(m, f"delever_for_{k}")]
            beats = bool(v["p_pass"] > d["p_pass"])
            ver[f"{m}|{k}"] = dict(variant_p=float(v["p_pass"]), delever_p=float(d["p_pass"]),
                                   gap_pt=float((v["p_pass"] - d["p_pass"]) * 100),
                                   beats_delever=beats,
                                   variant_median_days=float(v["median_days"]),
                                   delever_median_days=float(d["median_days"]))
            print(f"{m:30s} {k:12s} variant {v['p_pass']:.4f} vs de-lever {d['p_pass']:.4f} "
                  f"-> gap {(v['p_pass'] - d['p_pass']) * 100:+.2f}pt  "
                  f"{'BEATS' if beats else 'FAILS'}")
    (OUT / "decision_verdict.json").write_text(json.dumps(ver, indent=2, default=float))


if __name__ == "__main__":
    main()
