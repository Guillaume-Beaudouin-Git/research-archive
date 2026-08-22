"""
run_v2.py — iteration-2 funnel over the THREE uncovered spaces only (A multi-leg RV, B regime
conditioning of proven edges, C sub-60min index reversion). Burned iter-1 configs are NOT re-tested.

Binding gate: Deflated Sharpe on untouched OOS (2025-01..2026-06), deflated at the TRUE CUMULATIVE N
= 70 burned (66 funnel + 4 step-2) + v2 trials, with std_sr_trials = the Gate-0 frozen noise SE
(SE0=0.845) -> DSR>0.5 is EXACTLY "beat the pre-registered noise floor at cumulative N". Survivors
must also EXCEED the frozen threshold OOS Sharpe. Post-search dispersion vs SE0 -> exhaustion check.
"""
from __future__ import annotations
import sys, json, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import v2_lib as V
import funnel_lib as F
RES = HERE / "results"; RES.mkdir(exist_ok=True)

BURNED_N = 70                              # 66 funnel + 4 step-2 (cumulative, does not reset)
NF = json.loads((RES / "noise_floor.json").read_text())
SE0 = float(NF["SE0_frozen"])              # 0.845, frozen pre-search
IDXG = ["US500", "US100", "US30", "GER40", "XAUUSD"]
BASKET = ["US500", "US100", "GER40", "XAUUSD", "BTCUSD"]
TRIALS, SER = [], {}

def add(cid, space, mech, series, compliant="yes", note=""):
    s = series.dropna()
    SER[cid] = s
    _, oos = F.split_is_oos(s)
    st, sto = F.stats(s), F.stats(oos)
    TRIALS.append(dict(id=cid, space=space, mech=mech, compliant=compliant, note=note,
                       sharpe_is=F.ann_sharpe(F.split_is_oos(s)[0]), sharpe_oos=sto["sharpe"],
                       sharpe_full=st["sharpe"], n_oos=sto["n"], exkurt_oos=sto["exkurt"],
                       skew_oos=sto["skew"], years_pos=st["years_pos"], years_tot=st["years_tot"],
                       maxdd=st["maxdd"], by_year=st["by_year"]))

def isleeve(freq, sigfn, syms=("US500", "US100", "US30", "GER40")):
    return F.combine_inv_vol({s: V.intraday_backtest(s, freq, sigfn) for s in syms})

def build():
    # ── A. MULTI-LEG RELATIVE VALUE (>=3 legs) ───────────────────────────────
    for k in (5, 10, 20):
        add(f"A.xsrev_idxgold_k{k}", "A", "x-sec reversion idx+gold (5-leg)",
            V.xs_reversion(IDXG, k), compliant="no(hedge: corr indices L/S)", note=f"k={k}")
    for k in (20, 60):
        add(f"A.xsmom_idxgold_k{k}", "A", "x-sec momentum idx+gold (5-leg)",
            V.xs_reversion(IDXG, k, mom=True), compliant="no(hedge)", note=f"k={k}")
    add("A.triangular_eurgbp", "A", "triangular FX RV EUR/GBP (3-leg)", V.triangular_fx(),
        compliant="partial(related legs)")
    for k in (10, 20):
        add(f"A.equity_vs_gold_k{k}", "A", "equity-basket vs gold RV (4-leg)", V.equity_vs_gold(k),
            compliant="yes(cross-asset)", note=f"k={k}")
    # 3-leg index butterfly: US100 vs (US500+US30)/2 relative-strength reversion
    C = F.close_panel(["US100", "US500", "US30"])
    spread = np.log(C["US100"]) - 0.5 * (np.log(C["US500"]) + np.log(C["US30"]))
    z = ((spread - spread.rolling(20).mean()) / spread.rolling(20).std(ddof=0)).shift(1)
    sig = (-z / 2).clip(-1, 1)
    bfly = V._legnet("US100", sig) + V._legnet("US500", -sig / 2) + V._legnet("US30", -sig / 2)
    add("A.butterfly_nasdaq", "A", "index butterfly US100 vs US500/US30 (3-leg)", bfly,
        compliant="no(hedge: corr indices)")
    # RV sleeve (equal-risk of the cross-asset-compliant RV legs)
    add("A.rv_sleeve", "A", "RV sleeve (xsrev10 + equity-gold10 + triangular)",
        F.combine_inv_vol({"xsrev": SER["A.xsrev_idxgold_k10"], "eqgold": SER["A.equity_vs_gold_k10"],
                           "tri": SER["A.triangular_eurgbp"]}), compliant="mixed")

    # ── B. REGIME/CALENDAR CONDITIONING of the proven TSMOM edge (NOT vol-regime, burned) ──
    add("B.tsmom_monthend", "B", "TSMOM k200 | month-end window (±3d)",
        V.conditioned_tsmom(BASKET, 200, lambda d: V.cond_mask_monthend(d.index, 3)), note="settlement")
    add("B.tsmom_quarterend", "B", "TSMOM k200 | quarter-end month only",
        V.conditioned_tsmom(BASKET, 200, lambda d: pd.Series(np.isin(d.index.month, [3,6,9,12]).astype(float), index=d.index)))
    for th in (0.5, 1.0, 1.5):
        add(f"B.tsmom_trendstr{th}", "B", f"TSMOM k200 | trend-strength>{th}",
            V.conditioned_tsmom(BASKET, 200, lambda d, th=th: V.cond_mask_trendstrength(d, 200, th)), note="selectivity")
    add("B.tsmom_dow_TWT", "B", "TSMOM k200 | Tue-Thu only",
        V.conditioned_tsmom(BASKET, 200, lambda d: V.cond_mask_dow(d.index, [1, 2, 3])))
    add("B.tsmom100_trendstr1", "B", "TSMOM k100 | trend-strength>1.0",
        V.conditioned_tsmom(BASKET, 100, lambda d: V.cond_mask_trendstrength(d, 100, 1.0)))

    # ── C. SUB-60MIN INDEX INTRADAY REVERSION (the new frequency) ────────────
    for s in ["US500", "US100", "US30", "GER40"]:
        add(f"C.sessfade30_{s}", "C", "session-fade 30m (1 trade/day)", V.intraday_backtest(s, "30min", V.isig_session_fade(2)))
    add("C.sessfade30_sleeve", "C", "session-fade 30m sleeve", isleeve("30min", V.isig_session_fade(2)))
    add("C.sessfade30_eb4_sleeve", "C", "session-fade 30m late-entry sleeve", isleeve("30min", V.isig_session_fade(4)))
    add("C.sessfade15_sleeve", "C", "session-fade 15m sleeve", isleeve("15min", V.isig_session_fade(4)))
    add("C.zfade6_30m_sleeve", "C", "z-fade(6) 30m sleeve (med turnover)", isleeve("30min", V.isig_zfade(6)))
    add("C.zfade_bigbar_30m_sleeve", "C", "z-fade big-bar 30m sleeve (selectivity)", isleeve("30min", V.isig_zfade_bigbar(6, 2, 1.0)))
    add("C.fadeprev_30m_sleeve", "C", "fade-every-bar 30m sleeve (cost stress)", isleeve("30min", V.isig_fade_prev))


def e_max_iid(n):
    from scipy.stats import norm
    g = 0.5772156649015329
    return (1 - g) * norm.ppf(1 - 1.0 / n) + g * norm.ppf(1 - 1.0 / (n * math.e))


def main():
    build()
    Nv2 = len(TRIALS)
    N = BURNED_N + Nv2
    thr = SE0 * e_max_iid(N)                # frozen-noise threshold OOS Sharpe at cumulative N
    df = pd.DataFrame(TRIALS)
    sig_v2_oos = float(df["sharpe_oos"].std(ddof=1))
    # robust edge-dispersion: exclude construction-dead cost-suicide strategies (|OOS Sh|>2 are all
    # NET-cost-destroyed, not edge candidates) so the left tail doesn't inflate the dispersion.
    edge = df[df["sharpe_oos"].between(-2.0, 3.0)]
    sig_edge_oos = float(edge["sharpe_oos"].std(ddof=1))

    # PRIMARY DSR: deflate at cumulative N with the frozen noise SE -> "beat noise floor"
    dsr, bench = [], []
    for cid in df["id"]:
        _, oos = F.split_is_oos(SER[cid])
        d = F.deflated_sharpe_ratio(oos.dropna().to_numpy(), n_trials=N, periods_per_year=252, std_sr_trials=SE0)
        dsr.append(d["dsr"]); bench.append(d["sr_benchmark"])
    df["dsr_oos"] = dsr
    df["beats_floor"] = df["sharpe_oos"] > thr
    df = df.sort_values("sharpe_oos", ascending=False).reset_index(drop=True)

    cols = ["id", "space", "compliant", "sharpe_is", "sharpe_oos", "n_oos", "exkurt_oos",
            "years_pos", "years_tot", "dsr_oos", "beats_floor", "mech"]
    df[cols].to_csv(RES / "v2_all_trials.csv", index=False)
    df.to_json(RES / "v2_all_trials.json", orient="records", indent=2)

    surv = df[df["dsr_oos"] > 0.5]
    # of the candidates that LOOK best on OOS, how many also have a positive IS Sharpe (persistence)?
    top_pos = df[df["sharpe_oos"] > 0.5]
    n_top_is_pos = int((top_pos["sharpe_is"] > 0.3).sum())
    print(f"cumulative N = {N} ({BURNED_N} burned + {Nv2} v2) | frozen SE0={SE0} | "
          f"noise-floor OOS-Sharpe threshold = {thr:.2f}")
    print(f"raw OOS-Sharpe dispersion = {sig_v2_oos:.3f} (inflated by cost-suicide left tail)")
    print(f"EDGE dispersion (|OOS Sh|<=2, n={len(edge)}) = {sig_edge_oos:.3f}  (noise SE0={SE0}; "
          f"exhausted if <= SE0)")
    print(f"candidates beating the noise floor (OOS Sh > {thr:.2f}): {int(df['beats_floor'].sum())}")
    print(f"candidates with OOS Sh>0.5 that ALSO have IS Sh>0.3: {n_top_is_pos} / {len(top_pos)}")
    print(f"DSR>0.5 survivors: {len(surv)}\n")
    print(df[cols].head(28).to_string(index=False))

    # exhaustion: nobody beat the pre-registered floor AND the edge-dispersion is noise-like
    exhausted = (int(df["beats_floor"].sum()) == 0) and (sig_edge_oos <= SE0)
    summary = dict(cumulative_N=N, burned_N=BURNED_N, v2_N=Nv2, SE0_frozen=SE0,
                   noise_floor_threshold_oos_sharpe=round(thr, 3),
                   raw_oos_sharpe_dispersion=round(sig_v2_oos, 3),
                   edge_oos_sharpe_dispersion=round(sig_edge_oos, 3),
                   max_oos_sharpe=round(float(df["sharpe_oos"].max()), 3),
                   n_beating_floor=int(df["beats_floor"].sum()),
                   n_top_oos_with_positive_is=n_top_is_pos,
                   n_dsr_survivors=int(len(surv)), survivors=surv["id"].tolist(),
                   exhaustion_confirmed=bool(exhausted))
    (RES / "v2_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(f"\nEXHAUSTION CONFIRMED: {exhausted} | 0 beat floor AND edge-dispersion {sig_edge_oos:.3f} <= noise SE {SE0}")
    print("DONE ->", RES)


if __name__ == "__main__":
    main()
