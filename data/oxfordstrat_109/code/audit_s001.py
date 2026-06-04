"""
AUDIT — Strategy 1/109 Crabel 2-Bar NR + ORB.

Critical re-test of the Cowork report's KEEP verdict against constitutional gates:
- Gate 1 (L26 délai+1): re-run with entry shifted by 1 bar OR fill at close → if edge
  collapses, it was an intrabar-fill artefact.
- Gate 2 (L25 two-sided): split longs vs shorts. Long-biased on indices = disguised beta.
- Gate 3 (L33 cost stress): ×1.5 / ×2 cost. At which multiplier does edge die?
- Gate 4 (DSR Bailey-Lopez de Prado): N_trials = 42 grid cells. Is +0.0068R nonzero after
  deflation?
- Gate 5 (L31 OOS): train 2000-2015 / test 2016-2026.
- Gate 6 (bootstrap): block bootstrap 95% CI on pooled expectancy.

Reuses ftmo_lab.* for load_universe, round_turn_cost_bps, atr, trade_metrics.
Adds variant simulators in this file (NOT modifying ftmo_lab.py) to test the gates.
"""
from __future__ import annotations
import os
import sys
import math

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ftmo_lab as lab
from strat_s001_crabel_nr_orb import crabel_signals, LOOK_BACK, STRETCH_LEN, STRETCH_MULT, ATR_LEN, ATR_STOP


# ============================================================================
# Variant simulators (do NOT touch ftmo_lab.simulate_bracket).
# ============================================================================

def _sim_core(df, setup, stretch, *, target_index, time_index,
              atr_len=ATR_LEN, atr_stop=ATR_STOP, cost_bps=2.0,
              allow_long=True, allow_short=True, entry_mode="stop",
              entry_delay_days=0, record_dir=True):
    """Generalised event-driven sim with audit knobs.

    entry_mode:
      - "stop"  : original behaviour, fill at the stop level on bar e (the day after setup)
      - "close" : if the stop is touched on bar e, fill at the CLOSE of bar e instead
                  (eats the intrabar fill assumption)

    entry_delay_days:
      - 0 : original (signal i-1 → entry bar i, intrabar at stop)
      - 1 : skip bar i entirely; if the stop was touched on bar i, enter at OPEN of bar i+1
            (eats the intrabar-action assumption — pure next-bar execution)

    record_dir: also store direction d (1 long, -1 short) and trade type tag.
    """
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    A = lab.atr(df, atr_len).values
    su = setup.values.astype(bool)
    st = stretch.values
    n = len(df)
    idx = df.index
    trades = []
    i = 1
    while i < n - 1:
        if not (su[i-1] and np.isfinite(st[i-1]) and st[i-1] > 0 and np.isfinite(A[i])):
            i += 1
            continue
        e = i
        buy, sell = o[e] + st[i-1], o[e] - st[i-1]
        long_hit = (h[e] >= buy) and allow_long
        short_hit = (l[e] <= sell) and allow_short
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1
            continue
        cost_R = (cost_bps / 1e4) * c[e] / risk0

        if long_hit and short_hit:
            # both stops touched -> conservative loss (matches original engine)
            t = _trade_rec(idx[e], idx[e], "both", -2 * st[i-1] / risk0 - cost_R, 0,
                           direction=0)
            trades.append(t)
            i = e + 1
            continue
        if not (long_hit or short_hit):
            i += 1
            continue

        if long_hit:
            d = 1
        else:
            d = -1

        # ---- choose entry price and entry bar according to audit modes ----
        if entry_delay_days == 0:
            entry_bar = e
            if entry_mode == "stop":
                entry = max(o[e], buy) if d == 1 else min(o[e], sell)
            elif entry_mode == "close":
                entry = c[e]
            else:
                raise ValueError(entry_mode)
        elif entry_delay_days == 1:
            # signal observed on bar e (intrabar), but trade only on bar e+1 open
            if e + 1 >= n:
                i = e + 1
                continue
            entry_bar = e + 1
            entry = o[entry_bar]
        else:
            raise ValueError(entry_delay_days)

        stop = entry - d * risk0
        tgt = entry + d * target_index * risk0

        # ---- exit scan from entry_bar to entry_bar + time_index ----
        exit_p, exit_j, reason = None, None, None
        for j in range(entry_bar, min(entry_bar + time_index, n - 1) + 1):
            if d == 1:
                if l[j] <= stop:
                    exit_p, reason, exit_j = stop, "stop", j; break
                if h[j] >= tgt:
                    exit_p, reason, exit_j = tgt, "target", j; break
            else:
                if h[j] >= stop:
                    exit_p, reason, exit_j = stop, "stop", j; break
                if l[j] <= tgt:
                    exit_p, reason, exit_j = tgt, "target", j; break
            if j == entry_bar + time_index:
                exit_p, reason, exit_j = c[j], "time", j; break
        if exit_p is None:
            exit_p = c[min(entry_bar + time_index, n - 1)]
            reason, exit_j = "eod", min(entry_bar + time_index, n - 1)

        grossR = d * (exit_p - entry) / risk0
        trades.append(_trade_rec(idx[entry_bar], idx[exit_j], reason,
                                 grossR - cost_R, exit_j - entry_bar, direction=d))
        i = exit_j + 1
    return pd.DataFrame(trades)


def _trade_rec(t_in, t_out, reason, netR, hold, direction=0):
    return dict(entry=t_in, exit=t_out, reason=reason, netR=netR, hold=hold, dir=direction)


def run_variant(uni, costs, *, target_index=3.0, time_index=10,
                allow_long=True, allow_short=True, entry_mode="stop",
                entry_delay_days=0, cost_mult=1.0):
    all_tr = []
    for t, df in uni.items():
        setup, stretch = crabel_signals(df)
        tr = _sim_core(df, setup, stretch, target_index=target_index, time_index=time_index,
                       atr_len=ATR_LEN, atr_stop=ATR_STOP, cost_bps=costs[t] * cost_mult,
                       allow_long=allow_long, allow_short=allow_short,
                       entry_mode=entry_mode, entry_delay_days=entry_delay_days)
        if len(tr):
            tr["instr"] = t
            all_tr.append(tr)
    return pd.concat(all_tr, ignore_index=True) if all_tr else pd.DataFrame()


# ============================================================================
# Stats helpers
# ============================================================================

def pooled(tr):
    if tr is None or len(tr) == 0:
        return dict(trades=0, expR=np.nan, pf=np.nan, win=np.nan, sharpe=np.nan)
    r = tr["netR"].values
    pf = r[r > 0].sum() / abs(r[r < 0].sum()) if (r < 0).any() else np.inf
    eq = (1 + lab.RISK_FRAC * pd.Series(r, index=pd.to_datetime(tr["exit"]))).cumprod()
    eq = eq.groupby(eq.index).last()
    days = max((eq.index[-1] - eq.index[0]).days, 1)
    tpy = len(r) / (days / 365.0)
    sh = (r.mean() / r.std() * math.sqrt(tpy)) if r.std() > 0 else np.nan
    return dict(trades=int(len(r)), expR=float(r.mean()), pf=float(pf),
                win=float((r > 0).mean()), sharpe=float(sh))


def block_bootstrap_expR(tr, n_boot=5000, block=5, seed=42):
    r = tr["netR"].values
    n = len(r)
    rng = np.random.default_rng(seed)
    expRs = np.empty(n_boot)
    n_blocks = n // block + 1
    for b in range(n_boot):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        boot = np.concatenate([r[s:s+block] for s in starts])[:n]
        expRs[b] = boot.mean()
    return float(expRs.mean()), float(np.percentile(expRs, 2.5)), float(np.percentile(expRs, 97.5))


def dsr_bailey(sharpe_obs, n_obs, n_trials, skew, kurt):
    """Bailey-Lopez de Prado Deflated Sharpe Ratio.
    Returns DSR (z-score) and the implied probability that observed SR > 0 under
    the null of N_trials random trials.
    """
    from math import log, sqrt
    emc = 0.5772156649
    sr_threshold = sqrt(2.0 * log(max(2, n_trials))) * (1.0 - emc / sqrt(2.0 * log(max(2, n_trials))))
    sigma_sr = math.sqrt((1 - skew * sharpe_obs + (kurt - 1) / 4.0 * sharpe_obs * sharpe_obs) / max(n_obs - 1, 1))
    if sigma_sr <= 0:
        return float("nan"), float("nan"), sr_threshold
    dsr = (sharpe_obs - sr_threshold) / sigma_sr
    from math import erf
    p = 0.5 * (1.0 + erf(dsr / math.sqrt(2)))
    return float(dsr), float(p), float(sr_threshold)


# ============================================================================
# MAIN — run all 6 gates
# ============================================================================

def main():
    uni = lab.load_universe()
    costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
    print(f"Universe: {len(uni)} instruments | cost(bps) min={min(costs.values()):.1f} "
          f"med={np.median(list(costs.values())):.1f} max={max(costs.values()):.1f}\n")

    TI_REP, TM_REP = 3.0, 10

    # ----- 0. Reference baseline (must match REPORT_S001) -----
    base = run_variant(uni, costs, target_index=TI_REP, time_index=TM_REP)
    p_base = pooled(base)
    print("=== 0. REFERENCE (3R / 10d) ===")
    print(f"  trades={p_base['trades']}  win={p_base['win']*100:.1f}%  "
          f"expR={p_base['expR']:+.4f}  PF={p_base['pf']:.3f}  Sharpe={p_base['sharpe']:.2f}")
    print(f"  Expected REPORT: 3841 / 45.1% / +0.0068 / 1.050 / 0.22")
    matches_ref = (p_base['trades'] == 3841 and abs(p_base['expR'] - 0.0068) < 1e-4)
    print(f"  Repro match: {'YES' if matches_ref else 'NO — RED FLAG'}\n")

    results = {"reference": p_base}

    # ----- Gate 1 — délai+1 -----
    print("=" * 70)
    print("GATE 1 — DÉLAI+1 (L26) — most decisive intrabar-fill test")
    print("=" * 70)
    tr_g1a = run_variant(uni, costs, target_index=TI_REP, time_index=TM_REP,
                          entry_delay_days=1)
    p_g1a = pooled(tr_g1a)
    print(f"  V1a [entry at OPEN of i+2 instead of stop on i+1]:")
    print(f"    trades={p_g1a['trades']}  win={p_g1a['win']*100:.1f}%  "
          f"expR={p_g1a['expR']:+.4f}  PF={p_g1a['pf']:.3f}  Sharpe={p_g1a['sharpe']:.2f}")
    drop_v1a = (p_base["expR"] - p_g1a["expR"]) / max(abs(p_base["expR"]), 1e-9)
    print(f"    Δ expR vs ref: {drop_v1a*100:+.0f}%  ({'COLLAPSE' if p_g1a['expR']<=0 else 'survives'})")

    tr_g1b = run_variant(uni, costs, target_index=TI_REP, time_index=TM_REP,
                          entry_mode="close")
    p_g1b = pooled(tr_g1b)
    print(f"  V1b [fill at CLOSE of entry bar instead of stop level]:")
    print(f"    trades={p_g1b['trades']}  win={p_g1b['win']*100:.1f}%  "
          f"expR={p_g1b['expR']:+.4f}  PF={p_g1b['pf']:.3f}  Sharpe={p_g1b['sharpe']:.2f}")
    drop_v1b = (p_base["expR"] - p_g1b["expR"]) / max(abs(p_base["expR"]), 1e-9)
    print(f"    Δ expR vs ref: {drop_v1b*100:+.0f}%  ({'COLLAPSE' if p_g1b['expR']<=0 else 'survives'})")

    gate1_kill = (p_g1a["expR"] <= 0) or (p_g1b["expR"] <= 0)
    print(f"  → GATE 1 verdict: {'FAIL (intrabar artefact)' if gate1_kill else 'PASS'}\n")
    results["gate1_v1a"] = p_g1a
    results["gate1_v1b"] = p_g1b

    # ----- Gate 2 — two-sided -----
    print("=" * 70)
    print("GATE 2 — TWO-SIDED SPLIT (L25)")
    print("=" * 70)
    # Need to know direction per trade.
    # base has 'dir' column. Split.
    longs = base[base["dir"] == 1]
    shorts = base[base["dir"] == -1]
    boths = base[base["dir"] == 0]
    p_long = pooled(longs)
    p_short = pooled(shorts)
    print(f"  Longs  : trades={p_long['trades']}  win={p_long['win']*100:.1f}%  "
          f"expR={p_long['expR']:+.4f}  PF={p_long['pf']:.3f}  Sharpe={p_long['sharpe']:.2f}")
    print(f"  Shorts : trades={p_short['trades']}  win={p_short['win']*100:.1f}%  "
          f"expR={p_short['expR']:+.4f}  PF={p_short['pf']:.3f}  Sharpe={p_short['sharpe']:.2f}")
    print(f"  Both-hit (loss): trades={len(boths)}")
    # Long-bias check
    if p_long["expR"] > 0 and p_short["expR"] <= 0:
        verdict_g2 = "FAIL (long-bias / disguised beta on rising universe)"
    elif p_long["expR"] > 0 and p_short["expR"] > 0:
        verdict_g2 = "PASS (both sides positive)"
    else:
        verdict_g2 = "AMBIGUOUS (longs not driving)"
    print(f"  → GATE 2 verdict: {verdict_g2}\n")
    results["gate2_long"] = p_long
    results["gate2_short"] = p_short

    # Long-bias quantification: % of pooled expR from longs only
    if p_base["trades"] > 0:
        long_contrib = (longs["netR"].sum() / base["netR"].sum() * 100) if base["netR"].sum() != 0 else float('nan')
        print(f"  Long contribution to net R: {long_contrib:.1f}%  "
              f"(beta-equiv: longs on indices in 2000-2026 ~= drift cap)")

    # ----- Gate 3 — cost stress -----
    print("\n" + "=" * 70)
    print("GATE 3 — COST STRESS ×1.5, ×2.0 (L33)")
    print("=" * 70)
    p_x15 = pooled(run_variant(uni, costs, target_index=TI_REP, time_index=TM_REP, cost_mult=1.5))
    p_x20 = pooled(run_variant(uni, costs, target_index=TI_REP, time_index=TM_REP, cost_mult=2.0))
    print(f"  ×1.0 (ref): expR={p_base['expR']:+.4f}  PF={p_base['pf']:.3f}")
    print(f"  ×1.5      : expR={p_x15['expR']:+.4f}  PF={p_x15['pf']:.3f}")
    print(f"  ×2.0      : expR={p_x20['expR']:+.4f}  PF={p_x20['pf']:.3f}")
    if p_x15["expR"] <= 0:
        verdict_g3 = "FAIL (dies at ×1.5 — too fragile)"
    elif p_x20["expR"] <= 0:
        verdict_g3 = "BORDERLINE (survives ×1.5 but dies at ×2.0)"
    else:
        verdict_g3 = "PASS (survives ×2.0)"
    print(f"  → GATE 3 verdict: {verdict_g3}\n")
    results["gate3_x15"] = p_x15
    results["gate3_x20"] = p_x20

    # ----- Gate 4 — DSR with N_trials=42 -----
    print("=" * 70)
    print("GATE 4 — DSR Bailey-Lopez de Prado (N_trials = 42 grid cells)")
    print("=" * 70)
    r = base["netR"].values
    sr_obs = p_base["sharpe"]
    skew = float(pd.Series(r).skew())
    kurt = float(pd.Series(r).kurtosis() + 3)
    dsr_z, p_val, sr_thresh = dsr_bailey(sr_obs, len(r), n_trials=42, skew=skew, kurt=kurt)
    print(f"  Observed SR (per-trade-ann): {sr_obs:.3f}")
    print(f"  SR_threshold (E[max] under N=42 nulls): {sr_thresh:.3f}")
    print(f"  Skew={skew:.2f}  Kurt={kurt:.2f}")
    print(f"  DSR z-score: {dsr_z:.2f}  (passes if > +0.95 ~ p<0.17)")
    print(f"  Implied p(SR > 0 | data): {p_val:.4f}")
    if dsr_z > 0.95:
        verdict_g4 = "PASS (DSR > 0.95)"
    elif dsr_z > 0:
        verdict_g4 = "BORDERLINE (DSR positive but below 0.95)"
    else:
        verdict_g4 = "FAIL (DSR < 0 — observed SR below threshold)"
    print(f"  → GATE 4 verdict: {verdict_g4}\n")
    results["gate4_dsr"] = dict(dsr_z=dsr_z, sr_obs=sr_obs, sr_threshold=sr_thresh,
                                 skew=skew, kurt=kurt)

    # ----- Gate 5 — OOS split -----
    print("=" * 70)
    print("GATE 5 — OOS SPLIT (train 2000-2015, test 2016-2026)")
    print("=" * 70)
    base["entry_dt"] = pd.to_datetime(base["entry"])
    train = base[base["entry_dt"] <= "2015-12-31"]
    test = base[base["entry_dt"] >= "2016-01-01"]
    p_tr = pooled(train); p_te = pooled(test)
    print(f"  Train 2000-2015: trades={p_tr['trades']}  expR={p_tr['expR']:+.4f}  "
          f"PF={p_tr['pf']:.3f}  Sharpe={p_tr['sharpe']:.2f}")
    print(f"  Test  2016-2026: trades={p_te['trades']}  expR={p_te['expR']:+.4f}  "
          f"PF={p_te['pf']:.3f}  Sharpe={p_te['sharpe']:.2f}")
    sign_flip = (p_tr["expR"] > 0) and (p_te["expR"] <= 0)
    if sign_flip:
        verdict_g5 = "FAIL (edge in train flips to negative OOS)"
    elif p_te["expR"] <= 0:
        verdict_g5 = "FAIL (OOS edge non-positive)"
    elif p_te["expR"] < 0.5 * p_tr["expR"]:
        verdict_g5 = "BORDERLINE (OOS edge < 50% of train)"
    else:
        verdict_g5 = "PASS (OOS edge >= 50% of train)"
    print(f"  → GATE 5 verdict: {verdict_g5}\n")
    results["gate5_train"] = p_tr
    results["gate5_test"] = p_te

    # ----- Gate 6 — Block bootstrap CI -----
    print("=" * 70)
    print("GATE 6 — Block bootstrap 95% CI on pooled expectancy (block=5)")
    print("=" * 70)
    boot_mean, lo, hi = block_bootstrap_expR(base, n_boot=5000, block=5)
    print(f"  Bootstrap mean expR: {boot_mean:+.4f}")
    print(f"  95% CI: [{lo:+.4f}, {hi:+.4f}]")
    if lo > 0:
        verdict_g6 = "PASS (CI excludes 0)"
    elif hi < 0:
        verdict_g6 = "FAIL (CI excludes 0 in negative side)"
    else:
        verdict_g6 = "FAIL (CI straddles 0 — not distinguishable from null)"
    print(f"  → GATE 6 verdict: {verdict_g6}\n")
    results["gate6_boot"] = dict(mean=boot_mean, lo=lo, hi=hi)

    # ----- FINAL SYNTHESIS -----
    print("=" * 70)
    print("FINAL AUDIT VERDICT")
    print("=" * 70)
    summary_rows = []
    for g, (name, verdict) in enumerate([
        ("1 — Délai+1 / fill close", "FAIL" if gate1_kill else "PASS"),
        ("2 — Two-sided split", verdict_g2),
        ("3 — Cost stress ×1.5/×2", verdict_g3),
        ("4 — DSR (N_trials=42)", verdict_g4),
        ("5 — OOS 2016-2026", verdict_g5),
        ("6 — Bootstrap CI", verdict_g6),
    ]):
        summary_rows.append({"gate": name, "verdict": verdict})
    sdf = pd.DataFrame(summary_rows)
    print(sdf.to_string(index=False))
    fails = sdf["verdict"].str.startswith("FAIL").sum()
    borderline = sdf["verdict"].str.startswith("BORDERLINE").sum()
    print(f"\n  FAILS: {fails}/6   BORDERLINES: {borderline}/6")
    if fails >= 2 or (fails >= 1 and borderline >= 2):
        final = "DOWNGRADE Cowork KEEP → DISCARD"
    elif fails == 1 or borderline >= 2:
        final = "DOWNGRADE Cowork KEEP → BORDERLINE-AT-MOST"
    else:
        final = "HOLD Cowork KEEP verdict"
    print(f"\n  FINAL: {final}")

    # ----- Save audit artefacts -----
    out_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(out_dir, exist_ok=True)
    sdf.to_csv(os.path.join(out_dir, "audit_s001_gates.csv"), index=False)
    pd.DataFrame({k: [v.get("expR"), v.get("sharpe"), v.get("trades")] if isinstance(v, dict) else [v, None, None]
                  for k, v in results.items() if isinstance(v, dict) and "expR" in v}).T.to_csv(
        os.path.join(out_dir, "audit_s001_pooled_by_variant.csv"))
    print(f"\nSaved: {out_dir}/audit_s001_*.csv")
    return results, summary_rows, fails, borderline, final


if __name__ == "__main__":
    main()
