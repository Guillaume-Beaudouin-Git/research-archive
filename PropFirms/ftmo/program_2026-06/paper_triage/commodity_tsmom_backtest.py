"""
commodity_tsmom_backtest.py — Bucket-B idea #1: commodity TSMOM on the NEW FTMO-executable
commodity universe, with the measured L37 positive long-carry. ONE idea, reported in full.

ORTHOGONALITY (why this is not the closed box):
  * NEW universe: the FTMO-16 trials never traded commodities except gold. PROGRAM_DECISION_MEMO
    §2 lists "energy / silver ... excluded, not tested". These 6 are FTMO-executable & on disk.
  * L37 carry INVERTS the program's #1 killer (overnight swap on held LONG momentum). Measured from
    ftmo_specs_full.csv: USOIL long swap +36.55 pts/night (~+14%/yr at $65), UKOIL +27.62 (~+9%/yr).
    BUT shorts pay brutally (USOIL short -168 pts ~ -65%/yr) -> L37 helps the LONG leg only.
    -> test SYMMETRIC L/S TSMOM (neutral) AND LONG-ONLY TSMOM (the L37-favorable config).

REUSE VERBATIM: funnel_lib -> combined_pass_prob_empirical (ftmo_first_passage), deflated_sharpe_ratio
(dsr). Frozen pre-registered noise floor SE0=0.845 (gate0_noise_floor). DSR std_sr_trials=SE0.

TWO POINT SIZES (verified): SPREAD is Dukascopy `spread` col in 1/decimalFactor units (df=1000 -> 0.001
for all 6). SWAP is ftmo_specs points in 10^-FTMO_digits units. They DIFFER for COCOA/COFFEE/SOYBEAN.

HONEST CAVEATS (reported): ECN spreads UNCALIBRATED -> headline at markup 3.0 x +50% stress. The FTMO
swap is a CURRENT (2026) snapshot; historical backwardation was regime-dependent (2020 oil severe
contango -> long carry NEGATIVE). No historical swap series on disk -> sweep energy carry contango..current.

Causal (signal<=t-1, shift 1); real costs incl. swap; OOS 2025-01-01.. untouched. Writes only under
research/paper_triage/.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(REPO / "research/ftmo_candidate_funnel"))   # funnel_lib + engine reuse
import funnel_lib as F                                             # noqa: E402

CACHE = REPO / "research/paper_triage/cache"
OUT = REPO / "research/paper_triage"
PPY = 252
OOS_START = pd.Timestamp("2025-01-01")
MARKUP = 3.0          # program-standard conservative retail markup (funnel_lib MARKUP, L23b)
ADD_BPS_RT = 1.0      # fixed slippage add-on, RT bps (L19 conservative)
WEEKEND_MULT = 1.45   # nights per trading-day (weekend x3 amortized), from tsmom_regen
SE0 = 0.845           # FROZEN pre-registered noise SE (gate0_noise_floor.json)

# digits = FTMO swap point (10^-digits); df = Dukascopy spread point (1/df); swap (long,short) pts/night
SPEC = {
    "USOIL":   {"digits": 3, "df": 1000, "swap": (+36.55, -168.14), "class": "energy"},
    "UKOIL":   {"digits": 3, "df": 1000, "swap": (+27.62, -129.90), "class": "energy"},
    "XAGUSD":  {"digits": 3, "df": 1000, "swap": (-20.65,   +0.70), "class": "metal"},
    "COCOA":   {"digits": 1, "df": 1000, "swap": (-15.52,   +2.58), "class": "soft"},
    "COFFEE":  {"digits": 2, "df": 1000, "swap": (+1.70,   -10.32), "class": "soft"},
    "SOYBEAN": {"digits": 2, "df": 1000, "swap": (-39.12,   +6.10), "class": "soft"},
}
EXEC = list(SPEC)
RET_CAP = 0.40
_CACHE: dict[str, pd.DataFrame] = {}


def load_daily(sym: str) -> pd.DataFrame:
    if sym in _CACHE:
        return _CACHE[sym]
    df = pd.read_parquet(CACHE / f"{sym}_daily.parquet").set_index("date").sort_index()
    df = df[(df["close"] > 0)]
    df = df[(df.index.dayofweek < 5) & (df["n_bars"].fillna(0) >= 30)].copy()
    df["ret"] = df["close"].pct_change()
    df.loc[df["ret"].abs() > RET_CAP, "ret"] = 0.0
    pt_spread = 1.0 / SPEC[sym]["df"]            # Dukascopy spread point
    pt_swap = 10.0 ** (-SPEC[sym]["digits"])     # FTMO swap point
    sp = df["spread_med"].fillna(df["spread_med"].median()).to_numpy()
    df["rt_cost"] = sp * pt_spread * MARKUP / df["close"].to_numpy() + ADD_BPS_RT * 1e-4
    df["sl_frac"] = SPEC[sym]["swap"][0] * pt_swap / df["close"]   # long swap frac/night (signed)
    df["ss_frac"] = SPEC[sym]["swap"][1] * pt_swap / df["close"]   # short swap frac/night (signed)
    _CACHE[sym] = df
    return df


def tsmom_signal(close: pd.Series, lookbacks, theta: float = 0.34, long_only: bool = False) -> pd.Series:
    raw = sum(np.sign(close / close.shift(k) - 1.0) for k in lookbacks) / len(lookbacks)
    gated = raw.where(raw.abs() >= theta, 0.0)
    if long_only:
        gated = gated.clip(lower=0.0)
    return gated.shift(1)


def leg_net(sym, lookbacks, swap_scen="base", spread_stress=1.5, long_only=False, vol_tgt=0.10):
    df = load_daily(sym)
    sig = tsmom_signal(df["close"], lookbacks, long_only=long_only).reindex(df.index).fillna(0.0)
    rv = df["ret"].rolling(60).std().replace(0, np.nan)
    lev = (vol_tgt / np.sqrt(252) / rv).clip(upper=5.0).shift(1).fillna(0.0)
    pos = sig * lev
    gross = pos * df["ret"]
    dpos = pos.diff().fillna(pos)
    cost = 0.5 * (df["rt_cost"] * spread_stress) * dpos.abs()
    sl, ss = df["sl_frac"].copy(), df["ss_frac"].copy()
    if swap_scen == "free":
        sl[:] = 0.0; ss[:] = 0.0
    elif swap_scen == "contango":               # stress: energy long-carry flips negative
        if SPEC[sym]["class"] == "energy":
            sl = -sl
    elif swap_scen == "double":
        sl, ss = sl * 2, ss * 2
    long_n = pos.clip(lower=0.0); short_n = (-pos).clip(lower=0.0)
    swap = (long_n * sl + short_n * ss) * WEEKEND_MULT
    return (gross - cost + swap).fillna(0.0)


def book(universe, lookbacks, swap_scen="base", spread_stress=1.5, long_only=False, start=None):
    legs = {s: leg_net(s, lookbacks, swap_scen, spread_stress, long_only) for s in universe}
    R = pd.DataFrame(legs).sort_index()
    R = R[R.index.dayofweek < 5]
    if start is not None:
        R = R[R.index >= pd.Timestamp(start)]
    return R.mean(axis=1).dropna(), R


def ann_sharpe(r):
    r = r.dropna(); sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(PPY)) if sd > 1e-12 and len(r) > 5 else 0.0


def block_boot_ci(r, n=2000, block=10, seed=7):
    r = r.dropna().to_numpy(); T = len(r)
    if T < 30:
        return [0.0, 0.0]
    rng = np.random.default_rng(seed); out = []; nb = int(np.ceil(T / block))
    for _ in range(n):
        idx = (rng.integers(0, T, size=nb)[:, None] + np.arange(block)[None, :]).ravel()[:T] % T
        x = r[idx]; sd = x.std(ddof=1)
        if sd > 1e-12:
            out.append(x.mean() / sd * np.sqrt(PPY))
    return [round(float(np.percentile(out, 5)), 2), round(float(np.percentile(out, 95)), 2)]


def per_year(r):
    return {int(y): round(ann_sharpe(s), 2) for y, s in r.groupby(r.index.year)}


def wf_folds(r, k=6):
    r = r.dropna(); b = np.linspace(0, len(r), k + 1).astype(int)
    sh = [round(ann_sharpe(r.iloc[b[i]:b[i + 1]]), 2) for i in range(k)]
    return sh, int(sum(x > 0 for x in sh))


def exkurt(r):
    r = r.dropna(); z = (r - r.mean()) / r.std(ddof=1)
    return float((z ** 4).mean() - 3.0)


def p_pass(r, p1_tgt=0.10, p2_tgt=0.05, sigma_d=0.01, n_paths=6000):
    r = r.dropna(); sd = r.std(ddof=1)
    if sd < 1e-12:
        return {"p": 0.0, "ci": [0, 0]}
    o = F.combined_pass_prob_empirical((r * (sigma_d / sd)).to_numpy(), n_paths=n_paths,
                                       max_days=400, seed=7, p1_tgt=p1_tgt, p2_tgt=p2_tgt)
    return {"p": round(float(o["p_combined"]), 3),
            "ci": [round(float(o["p_combined_ci95"][0]), 3), round(float(o["p_combined_ci95"][1]), 3)],
            "median_sessions": o.get("median_sessions_to_pass")}


def evaluate(name, r, n_trials, label=""):
    full = r.dropna(); is_, oos = full[full.index < OOS_START], full[full.index >= OOS_START]
    d_o = F.deflated_sharpe_ratio(oos.to_numpy(), n_trials=n_trials, periods_per_year=252, std_sr_trials=SE0)
    d_f = F.deflated_sharpe_ratio(full.to_numpy(), n_trials=n_trials, periods_per_year=252, std_sr_trials=SE0)
    wf, wfpos = wf_folds(full)
    return {"name": name, "label": label, "n_days": len(full),
            "start": str(full.index.min().date()), "end": str(full.index.max().date()),
            "sharpe_full": round(ann_sharpe(full), 3), "ci_full": block_boot_ci(full),
            "sharpe_is": round(ann_sharpe(is_), 3),
            "sharpe_oos": round(ann_sharpe(oos), 3), "ci_oos": block_boot_ci(oos),
            "exkurt": round(exkurt(full), 1), "wf_folds": wf, "wf_pos": f"{wfpos}/6",
            "per_year": per_year(full), "dsr_oos": round(d_o["dsr"], 3), "dsr_full": round(d_f["dsr"], 3),
            "dsr_benchmark_sharpe": round(d_o["sr_benchmark"], 2), "n_trials": n_trials}


def main():
    LB = (60, 120, 250); N_BASE = 103
    # 5 signal configs honestly tested -> cumulative N
    CONFIGS = [("sym_blend", LB, False), ("long_blend", LB, True),
               ("sym_L60", (60,), False), ("sym_L120", (120,), False), ("sym_L250", (250,), False)]
    N_CUM = N_BASE + len(CONFIGS)
    print(f"=== Commodity TSMOM | universe={EXEC} | cumulative N={N_CUM} ===\n")
    starts = {s: load_daily(s).index.min() for s in EXEC}
    common = max(starts.values())
    print("starts:", {s: str(d.date()) for s, d in starts.items()}, "-> common", common.date(), "\n")

    rep = {"meta": {"universe_FTMO_executable": EXEC, "lookbacks_blend": LB, "cumulative_N": N_CUM,
                    "SE0_frozen": SE0, "markup": MARKUP, "spread_stress_headline": 1.5,
                    "noise_floor_oos_sharpe_to_beat": {"N100": 2.139, "N110": 2.168, "N120": 2.193},
                    "swap_ann_pct_long_at_median_px": {
                        s: round(SPEC[s]["swap"][0] * 10**(-SPEC[s]["digits"]) /
                                 load_daily(s)["close"].median() * 252 * 100, 1) for s in EXEC}}}

    print("--- (1) signal configs (EW-6, swap=base, spread x1.5, from common start) ---")
    cfg = []
    for cname, lb, lo in CONFIGS:
        bk, _ = book(EXEC, lb, "base", 1.5, long_only=lo, start=common)
        e = evaluate(cname, bk, N_CUM, f"lb={lb} long_only={lo}")
        cfg.append(e)
        print(f"  {cname:11s} full={e['sharpe_full']:+.2f}{e['ci_full']} IS={e['sharpe_is']:+.2f} "
              f"OOS={e['sharpe_oos']:+.2f}{e['ci_oos']} WF {e['wf_pos']} DSRoos={e['dsr_oos']:.2f} "
              f"DSRfull={e['dsr_full']:.2f} exk={e['exkurt']}")
    rep["signal_configs"] = cfg

    # headlines: symmetric (neutral) and long-only (L37-favorable)
    for tag, lo in [("HEADLINE_sym", False), ("HEADLINE_long", True)]:
        bk, _ = book(EXEC, LB, "base", 1.5, long_only=lo, start=common)
        h = evaluate(tag, bk, N_CUM, f"EW6 blend swap=base spread1.5 long_only={lo}")
        h["p_pass_FTMO_10_5"] = p_pass(bk, 0.10, 0.05)
        h["p_pass_FundedNext_8_5"] = p_pass(bk, 0.08, 0.05)
        rep[tag] = h
        print(f"\n  {tag}: per-year={h['per_year']}")
        print(f"    p(pass) FTMO={h['p_pass_FTMO_10_5']} FundedNext={h['p_pass_FundedNext_8_5']}")

    print("\n--- (2) swap robustness (EW-6, spread x1.5) [sym | long_only] ---")
    sw = {}
    for sc in ["free", "base", "contango", "double"]:
        bs, _ = book(EXEC, LB, sc, 1.5, long_only=False, start=common)
        bl, _ = book(EXEC, LB, sc, 1.5, long_only=True, start=common)
        sw[sc] = {"sym_full": round(ann_sharpe(bs), 2), "sym_oos": round(ann_sharpe(bs[bs.index >= OOS_START]), 2),
                  "long_full": round(ann_sharpe(bl), 2), "long_oos": round(ann_sharpe(bl[bl.index >= OOS_START]), 2)}
        print(f"  swap={sc:9s} sym full={sw[sc]['sym_full']:+.2f} oos={sw[sc]['sym_oos']:+.2f} | "
              f"long full={sw[sc]['long_full']:+.2f} oos={sw[sc]['long_oos']:+.2f}")
    rep["swap_robustness"] = sw

    print("\n--- (3) spread-stress robustness (EW-6, swap=base) [sym | long_only] ---")
    sp = {}
    for ss in [1.0, 1.5, 2.0]:
        bs, _ = book(EXEC, LB, "base", ss, long_only=False, start=common)
        bl, _ = book(EXEC, LB, "base", ss, long_only=True, start=common)
        sp[f"x{ss}"] = {"sym": round(ann_sharpe(bs), 2), "long": round(ann_sharpe(bl), 2)}
        print(f"  spread x{ss}: sym={sp[f'x{ss}']['sym']:+.2f} long={sp[f'x{ss}']['long']:+.2f}")
    rep["spread_robustness"] = sp

    print("\n--- (4) universe robustness (blend, swap=base, spread x1.5) [long_only=L37 core] ---")
    uni = {}
    for un, u, st, lo in [("energy2_long", ["USOIL", "UKOIL"], None, True),
                          ("energy_silver3_long", ["USOIL", "UKOIL", "XAGUSD"], None, True),
                          ("exec6_long", EXEC, common, True),
                          ("exec6_sym", EXEC, common, False)]:
        bk, _ = book(u, LB, "base", 1.5, long_only=lo, start=st)
        e = evaluate(un, bk, N_CUM, f"{u} long_only={lo}")
        e["p_pass_FTMO"] = p_pass(bk, 0.10, 0.05)["p"]
        uni[un] = e
        print(f"  {un:20s} ({len(u)}leg {e['start']}->) full={e['sharpe_full']:+.2f}{e['ci_full']} "
              f"OOS={e['sharpe_oos']:+.2f} WF {e['wf_pos']} DSRoos={e['dsr_oos']:.2f} pFTMO={e['p_pass_FTMO']}")
    rep["universe_robustness"] = uni

    print("\n--- (5) per-leg standalone (blend sym, swap=base, spread x1.5) ---")
    leg = {}
    for s in EXEC:
        ln = leg_net(s, LB, "base", 1.5).dropna()
        leg[s] = {"full": round(ann_sharpe(ln), 2), "oos": round(ann_sharpe(ln[ln.index >= OOS_START]), 2)}
        print(f"  {s:8s} full={leg[s]['full']:+.2f} oos={leg[s]['oos']:+.2f}")
    rep["per_leg"] = leg

    (OUT / "commodity_tsmom_results.json").write_text(json.dumps(rep, indent=2, default=str))
    print(f"\nwrote {OUT/'commodity_tsmom_results.json'}")
    floor = rep["meta"]["noise_floor_oos_sharpe_to_beat"]["N110"]
    print("\n=== VERDICT INPUTS (headlines) ===")
    for tag in ["HEADLINE_sym", "HEADLINE_long"]:
        h = rep[tag]
        print(f"  {tag}: full {h['sharpe_full']}{h['ci_full']} OOS {h['sharpe_oos']}{h['ci_oos']} "
              f"(beat floor {floor}? {h['sharpe_oos']>floor}) DSRoos {h['dsr_oos']} DSRfull {h['dsr_full']} "
              f"WF {h['wf_pos']} pFTMO {h['p_pass_FTMO_10_5']['p']} pFN {h['p_pass_FundedNext_8_5']['p']}")
    print(f"  swap_ann_long_%@median: {rep['meta']['swap_ann_pct_long_at_median_px']}")


if __name__ == "__main__":
    main()
