"""
step2_validation.py — powered validation of the funnel's surviving leads.

Fixes the three caveats the 17-month OOS couldn't resolve:
  1. POWER  : expanding-window walk-forward, 6 folds (per-fold Sharpe + sign), + full-history DSR
              deflated at the honest cumulative N (66 funnel trials + new step-2 variants).
  2. FLOORS : intraday-aware FTMO first-passage. The funnel fed CLOSE-TO-CLOSE returns to the engine,
              so it never saw intraday -5% daily / -10% static breaches. Here each day carries its
              intraday Maximum Adverse Excursion (MAE) from daily High/Low, and the daily/static
              floors are checked against that intraday low -> honest (no longer optimistic).
  3. BETA   : the cleanest-shape lead (F1 low-vol-drift) is regressed on equity to test whether its
              edge is alpha or just timed beta; compared to always-long benchmarks.
Plus 2x cost stress on every finalist.

Pre-registered candidates only (no new search beyond the listed variants). Causal, real costs.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import funnel_lib as F
from ftmo_first_passage import _stationary_block_matrix, FTMO_MAX_DD_PCT, FTMO_DAILY_PCT, \
    FTMO_P1_TGT_PCT, FTMO_P2_TGT_PCT
import statsmodels.api as sm

RESULTS = Path(__file__).parent / "results"
N_FUNNEL = 66                      # honest trial count from the funnel search

# ── leg backtest carrying intraday MAE (from daily High/Low) ──────────────────
def leg_mae(sym: str, sig: pd.Series, mode: str = "cc", stress: float = 1.0) -> pd.DataFrame:
    """Net daily return + intraday MAE (most-adverse intraday P&L of the held position)."""
    d = F.load_daily(sym, stress=stress)
    pos = sig.reindex(d.index).fillna(0.0)
    if mode == "oc":
        entry = d["open"]; ret_gross = pos * (d["close"] / d["open"] - 1.0)
    else:
        entry = d["close"].shift(1); ret_gross = pos * d["ret"]
    dpos = pos.diff().fillna(pos)
    cost = 0.5 * d["rt_cost"] * dpos.abs()
    ret_net = (ret_gross - cost).fillna(0.0)
    # intraday adverse extreme: long -> low, short -> high
    adverse = np.where(pos > 0, d["low"], np.where(pos < 0, d["high"], entry))
    mae_gross = pos * (pd.Series(adverse, index=d.index) / entry - 1.0)
    mae = (mae_gross.fillna(0.0) - cost).clip(upper=ret_net)   # worst point <= close point
    mae = mae.fillna(0.0)
    return pd.DataFrame({"ret": ret_net, "mae": mae})

def voltarget_pos(d: pd.DataFrame, sig: pd.Series, target=0.01, lk=60) -> pd.Series:
    """Scale a signal to a fixed per-instrument daily vol (Moskowitz vol-target; causal)."""
    rv = d["ret"].rolling(lk).std().shift(1)
    return (sig * (target / rv.replace(0, np.nan))).clip(-3, 3).fillna(0.0)

def sleeve_mae(legs: dict[str, pd.DataFrame], mode="invvol", lookback=60):
    """Combine legs (ret & mae) on a common business-day calendar. Weights from ret legs;
    same weights applied to mae (conservative: sleeve MAE = weighted sum of leg MAEs)."""
    Rret = pd.DataFrame({k: v["ret"] for k, v in legs.items()}).sort_index()
    Rmae = pd.DataFrame({k: v["mae"] for k, v in legs.items()}).sort_index()
    bd = Rret.index.dayofweek < 5
    Rret, Rmae = Rret[bd], Rmae[bd]
    if mode == "invvol":
        vol = Rret.rolling(lookback, min_periods=20).std(ddof=0).shift(1)
        w = (1.0 / vol).replace([np.inf, -np.inf], np.nan)
        w = w.div(w.sum(axis=1), axis=0).fillna(0.0)
    else:
        w = pd.DataFrame(1.0 / Rret.shape[1], index=Rret.index, columns=Rret.columns)
    ret = (Rret.fillna(0.0) * w).sum(axis=1)
    mae = (Rmae.fillna(0.0) * w).sum(axis=1)
    return pd.DataFrame({"ret": ret, "mae": mae})

# ── intraday-aware FTMO first-passage ─────────────────────────────────────────
def sim_phase_intraday(ret, mae, target, max_dd=FTMO_MAX_DD_PCT, daily_floor=FTMO_DAILY_PCT,
                       n_paths=8000, max_days=400, seed=42, batch=4000) -> float:
    ret = np.asarray(ret, float); mae = np.asarray(mae, float)
    T = len(ret); block = max(1.0, round(np.sqrt(T)))
    horizon = min(max_days, 1000); rng = np.random.default_rng(seed)
    passed = 0
    for s0 in range(0, n_paths, batch):
        bs = min(batch, n_paths - s0)
        idx = _stationary_block_matrix(T, bs, horizon, block, rng)
        R = ret[idx]; M = mae[idx]
        eq = np.cumsum(R, axis=1)
        eq_prev = np.concatenate([np.zeros((bs, 1)), eq[:, :-1]], axis=1)
        intraday_low = eq_prev + M                      # worst equity within each day
        daily_hit = M <= -daily_floor                   # intraday daily-floor breach
        dd_hit = intraday_low <= -max_dd                # intraday static-DD breach
        pass_hit = eq >= target                         # target on close
        t_daily = np.where(daily_hit.any(1), daily_hit.argmax(1), 10**9)
        t_dd = np.where(dd_hit.any(1), dd_hit.argmax(1), 10**9)
        t_pass = np.where(pass_hit.any(1), pass_hit.argmax(1), 10**9)
        t_breach = np.minimum(t_daily, t_dd)
        passed += int((t_pass < t_breach).sum())
    return passed / n_paths

def p_funded_intraday(df_rm: pd.DataFrame, sigma_d=0.01, n_paths=8000):
    r = df_rm["ret"].dropna(); m = df_rm.loc[r.index, "mae"]
    sd = r.std(ddof=1)
    if sd < 1e-12: return {"p_combined": 0.0}
    lev = sigma_d / sd
    rr, mm = (r * lev).to_numpy(), (m * lev).to_numpy()
    p1 = sim_phase_intraday(rr, mm, FTMO_P1_TGT_PCT, n_paths=n_paths, seed=1)
    p2 = sim_phase_intraday(rr, mm, FTMO_P2_TGT_PCT, n_paths=n_paths, seed=2)
    return {"p_combined": p1 * p2, "p1": p1, "p2": p2, "lev": lev}

# ── walk-forward (expanding-window evaluation, fixed pre-registered params) ────
def walk_forward(ret: pd.Series, n_folds=6) -> dict:
    r = ret.dropna()
    folds = np.array_split(np.arange(len(r)), n_folds)
    sh = [F.ann_sharpe(r.iloc[f]) for f in folds]
    yrs = [(str(r.index[f[0]].date()), str(r.index[f[-1]].date())) for f in folds]
    return {"fold_sharpe": [round(x, 2) for x in sh],
            "fold_spans": yrs, "pct_folds_pos": float(np.mean(np.array(sh) > 0)),
            "worst_fold": round(min(sh), 2)}

# ── candidate roster for step 2 (carried + NEW variants; NEW add to N) ─────────
def build():
    IDX = F.INDEX
    basket = ["US500", "US100", "GER40", "XAUUSD", "BTCUSD"]
    cands, new = {}, []

    # carried from funnel (already in N_FUNNEL)
    cands["TSMOM_K200"] = sleeve_mae({s: leg_mae(s, F.sig_tsmom(F.load_daily(s), 200)) for s in basket})
    cands["TSMOM_K100"] = sleeve_mae({s: leg_mae(s, F.sig_tsmom(F.load_daily(s), 100)) for s in basket})
    cands["F1_lowvol_IDX"] = sleeve_mae({s: leg_mae(s, F.vol_regime_long_sig(F.load_daily(s))) for s in IDX})
    cands["TSMOM_XAU"] = leg_mae("XAUUSD", F.sig_tsmom(F.load_daily("XAUUSD"), 100))

    # NEW variants (each adds to honest N)
    # v1: vol-targeted TSMOM (per-instrument vol target -> lower kurtosis)
    cands["TSMOM_K200_voltgt"] = sleeve_mae(
        {s: leg_mae(s, voltarget_pos(F.load_daily(s), F.sig_tsmom(F.load_daily(s), 200))) for s in basket}); new.append("TSMOM_K200_voltgt")
    # v2: low-vol drift broadened to indices+XAU
    cands["F1_lowvol_broad"] = sleeve_mae(
        {s: leg_mae(s, F.vol_regime_long_sig(F.load_daily(s))) for s in IDX + ["XAUUSD"]}); new.append("F1_lowvol_broad")
    # v3: TSMOM + low-vol combined (decorrelation play), equal-risk of the two sleeve returns
    combo_legs = {"tsmom": cands["TSMOM_K200"], "lowvol": cands["F1_lowvol_IDX"]}
    cands["COMBO_tsmom_lowvol"] = sleeve_mae(combo_legs); new.append("COMBO_tsmom_lowvol")
    # v4: TSMOM K200 with a slower vol-target (target 0.6%/day) — robustness of v1
    cands["TSMOM_K200_voltgt06"] = sleeve_mae(
        {s: leg_mae(s, voltarget_pos(F.load_daily(s), F.sig_tsmom(F.load_daily(s), 200), target=0.006)) for s in basket}); new.append("TSMOM_K200_voltgt06")

    return cands, new

# ── F1 beta diagnostic ────────────────────────────────────────────────────────
def beta_diag(f1_ret: pd.Series) -> dict:
    bench = F.load_daily("US500")["ret"].reindex(f1_ret.index).fillna(0.0)
    y = f1_ret.reindex(bench.index).fillna(0.0)
    X = sm.add_constant(bench.values)
    m = sm.OLS(y.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    alpha_d, beta = m.params; t_alpha = m.tvalues[0]
    bh = F.ann_sharpe(bench)              # buy-and-hold US500 Sharpe over same window
    return {"alpha_ann": float(alpha_d * 252), "t_alpha_HAC": float(t_alpha),
            "beta": float(beta), "buyhold_sharpe": round(bh, 2),
            "f1_sharpe": round(F.ann_sharpe(f1_ret), 2)}


def main():
    cands, new = build()
    N = N_FUNNEL + len(new)
    # global sigma_SR for DSR deflation: reuse the funnel's dispersions (selection distribution)
    summ = json.loads((RESULTS / "summary.json").read_text())
    sig_oos = float(summ["sigma_SR_oos"]); sig_full = float(summ["sigma_SR_full"])
    print(f"Step-2 honest N = {N} (funnel {N_FUNNEL} + {len(new)} new) | sigma_SR oos={sig_oos:.3f} full={sig_full:.3f}\n")

    rows = []
    for name, rm in cands.items():
        r = rm["ret"].dropna()
        wf = walk_forward(r)
        st_full = F.stats(r)
        # full-history DSR (powered), deflated at N — primary (OOS sigma) + lenient (full sigma)
        dfull_p = F.deflated_sharpe_ratio(r.to_numpy(), n_trials=N, periods_per_year=252, std_sr_trials=sig_oos)
        dfull_l = F.deflated_sharpe_ratio(r.to_numpy(), n_trials=N, periods_per_year=252, std_sr_trials=sig_full)
        # OOS-only DSR (2025-26) for continuity with funnel
        _, oos = F.split_is_oos(r)
        doos = F.dsr_oos(oos, n_trials=N, std_sr_trials=sig_oos)
        # intraday-aware p_funded (1x and 2x cost)
        pf = p_funded_intraday(rm)
        rm2 = rebuild_2x(name, cands)            # recompute at 2x cost
        pf2 = p_funded_intraday(rm2) if rm2 is not None else {"p_combined": np.nan}
        rows.append(dict(
            name=name, sharpe_full=round(st_full["sharpe"], 2), sharpe_oos=round(F.ann_sharpe(oos), 2),
            exkurt_full=round(st_full["exkurt"], 1), skew_full=round(st_full["skew"], 2),
            maxdd=round(st_full["maxdd"], 3), years_pos=f"{st_full['years_pos']}/{st_full['years_tot']}",
            wf_pct_pos=wf["pct_folds_pos"], wf_worst=wf["worst_fold"], wf_folds=wf["fold_sharpe"],
            dsr_full_primary=round(dfull_p["dsr"], 3), dsr_full_lenient=round(dfull_l["dsr"], 3),
            dsr_oos_primary=round(doos["dsr"], 3),
            p_funded_intraday=round(pf["p_combined"], 3), p_funded_intraday_2x=round(pf2["p_combined"], 3),
            is_new=name in new))
    res = pd.DataFrame(rows).sort_values("dsr_full_primary", ascending=False)
    print(res.to_string(index=False))

    # F1 beta diagnostic
    bd = beta_diag(cands["F1_lowvol_IDX"]["ret"])
    bd_broad = beta_diag(cands["F1_lowvol_broad"]["ret"])
    print("\nF1 beta diagnostic (vs US500):", {k: round(v, 3) if isinstance(v, float) else v for k, v in bd.items()})
    print("F1_broad beta diagnostic     :", {k: round(v, 3) if isinstance(v, float) else v for k, v in bd_broad.items()})

    # decorrelation of the genuine finalists (full-sample daily ret)
    fin = res["name"].tolist()
    rp = pd.DataFrame({n: cands[n]["ret"] for n in fin}).sort_index()
    rp = rp[rp.index.dayofweek < 5].fillna(0.0)
    corr = rp.corr().round(2)
    corr.to_csv(RESULTS / "step2_corr.csv")
    print("\nFinalist correlation matrix:\n", corr.to_string())

    out = dict(N=N, new_variants=new, sigma_SR_oos=sig_oos,
               table=rows, f1_beta=bd, f1_broad_beta=bd_broad)
    (RESULTS / "step2_validation.json").write_text(json.dumps(out, indent=2, default=float))
    res.to_csv(RESULTS / "step2_validation.csv", index=False)
    print("\nDONE -> results/step2_validation.{json,csv}")


_CACHE2 = {}
def rebuild_2x(name, cands):
    """Rebuild a candidate's (ret,mae) at 2x cost for stress (only the ones we report)."""
    IDX = F.INDEX; basket = ["US500", "US100", "GER40", "XAUUSD", "BTCUSD"]
    g = lambda s: F.load_daily(s, stress=2.0)
    try:
        if name == "TSMOM_K200":
            return sleeve_mae({s: leg_mae(s, F.sig_tsmom(g(s), 200), stress=2.0) for s in basket})
        if name == "TSMOM_K100":
            return sleeve_mae({s: leg_mae(s, F.sig_tsmom(g(s), 100), stress=2.0) for s in basket})
        if name == "F1_lowvol_IDX":
            return sleeve_mae({s: leg_mae(s, F.vol_regime_long_sig(g(s)), stress=2.0) for s in IDX})
        if name == "TSMOM_XAU":
            return leg_mae("XAUUSD", F.sig_tsmom(g("XAUUSD"), 100), stress=2.0)
        if name == "TSMOM_K200_voltgt":
            return sleeve_mae({s: leg_mae(s, voltarget_pos(g(s), F.sig_tsmom(g(s), 200)), stress=2.0) for s in basket})
        if name == "TSMOM_K200_voltgt06":
            return sleeve_mae({s: leg_mae(s, voltarget_pos(g(s), F.sig_tsmom(g(s), 200), target=0.006), stress=2.0) for s in basket})
        if name == "F1_lowvol_broad":
            return sleeve_mae({s: leg_mae(s, F.vol_regime_long_sig(g(s)), stress=2.0) for s in IDX + ["XAUUSD"]})
        if name == "COMBO_tsmom_lowvol":
            t = sleeve_mae({s: leg_mae(s, F.sig_tsmom(g(s), 200), stress=2.0) for s in basket})
            l = sleeve_mae({s: leg_mae(s, F.vol_regime_long_sig(g(s)), stress=2.0) for s in IDX})
            return sleeve_mae({"tsmom": t, "lowvol": l})
    except Exception:
        return None
    return None


if __name__ == "__main__":
    main()
