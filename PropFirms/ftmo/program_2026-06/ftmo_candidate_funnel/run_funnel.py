"""
run_funnel.py — FTMO 10k 2-step candidate funnel: build configs, backtest causally with real
costs, hold out 2025-26 OOS, deflate Sharpe at the TRUE trial count N, keep DSR>0.5 survivors,
then pick <=5 most mutually-decorrelated.

Every distinct net-daily-return series computed here is one honest trial -> N = len(TRIALS).
DSR is evaluated on the untouched OOS slice only, deflated at N with the empirical OOS
trial-Sharpe dispersion (mean 0 null). p_funded is reported as color, not the gate.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import funnel_lib as F

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)

TRIALS: list[dict] = []          # every backtested net-return series (the honest N)
SERIES: dict[str, pd.Series] = {}

def add(cid, mech, instruments, series, mode="cc", note=""):
    """Register one backtested config as a trial."""
    series = series.dropna()
    SERIES[cid] = series
    isr, oos = F.split_is_oos(series)
    st_full, st_is, st_oos = F.stats(series), F.stats(isr), F.stats(oos)
    TRIALS.append(dict(id=cid, mech=mech, instr=instruments, mode=mode, note=note,
                       sharpe_full=st_full["sharpe"], sharpe_is=st_is["sharpe"],
                       sharpe_oos=st_oos["sharpe"], n_oos=st_oos["n"], n_full=st_full["n"],
                       exkurt_oos=st_oos["exkurt"], skew_oos=st_oos["skew"],
                       exkurt_full=st_full["exkurt"], hit_full=st_full["hit"],
                       years_pos=st_full["years_pos"], years_tot=st_full["years_tot"],
                       by_year=st_full["by_year"], maxdd_full=st_full["maxdd"],
                       ann_vol_full=st_full["ann_vol"]))
    return series

def leg_bt(sym, sig, mode="cc"):
    return F.backtest(sym, sig, mode=mode)

# ════════════════════════════════════════════════════════════════════════════
# ROSTER  (each add(...) = one honest trial)
# ════════════════════════════════════════════════════════════════════════════
def build_all():
    FX, IDX, JPY = F.FX, F.INDEX, F.JPY

    # ── (A) DAILY MEAN-REVERSION (price) ─────────────────────────────────────
    # A1 z-fade on each FX pair + inverse-vol sleeve; param variants k in {5,10,20}
    for k in (5, 10, 20):
        legs = {}
        for s in FX:
            ser = leg_bt(s, F.sig_zfade(F.load_daily(s), k, 2.0))
            legs[s] = ser
            if k == 10:
                add(f"A1.zfade{k}.{s}", "MR/z-fade", [s], ser)   # per-pair only for the headline k
        add(f"A1.zfadeFX.k{k}", "MR/z-fade FX sleeve", FX, F.combine_inv_vol(legs), note=f"k={k}")
    # A2 z-fade on indices + sleeve
    legs = {}
    for s in IDX:
        ser = leg_bt(s, F.sig_zfade(F.load_daily(s), 10, 2.0)); legs[s] = ser
        add(f"A2.zfade.{s}", "MR/z-fade idx", [s], ser)
    add("A2.zfadeIDX", "MR/z-fade idx sleeve", IDX, F.combine_inv_vol(legs))
    # A3 RSI2 (Connors) on indices + sleeve
    legs = {}
    for s in IDX:
        ser = leg_bt(s, F.sig_rsi2(F.load_daily(s))); legs[s] = ser
        add(f"A3.rsi2.{s}", "MR/RSI2 idx", [s], ser)
    add("A3.rsi2IDX", "MR/RSI2 idx sleeve", IDX, F.combine_inv_vol(legs))
    # A4 RSI2 / z-fade on XAU & BTC
    add("A4.rsi2.XAU", "MR/RSI2 xau", ["XAUUSD"], leg_bt("XAUUSD", F.sig_rsi2(F.load_daily("XAUUSD"))))
    add("A4.zfade.XAU", "MR/z-fade xau", ["XAUUSD"], leg_bt("XAUUSD", F.sig_zfade(F.load_daily("XAUUSD"), 10, 2.0)))
    add("A4.zfade.BTC", "MR/z-fade btc", ["BTCUSD"], leg_bt("BTCUSD", F.sig_zfade(F.load_daily("BTCUSD"), 10, 2.0)))
    add("A4.rsi2.BTC", "MR/RSI2 btc", ["BTCUSD"], leg_bt("BTCUSD", F.sig_rsi2(F.load_daily("BTCUSD"))))
    # A5 overnight gap-fade (open->close) on indices + sleeve, and XAU
    legs = {}
    for s in IDX:
        ser = leg_bt(s, F.sig_gap_fade(F.load_daily(s)), mode="oc"); legs[s] = ser
        add(f"A5.gapfade.{s}", "MR/gap-fade idx", [s], ser, mode="oc")
    add("A5.gapfadeIDX", "MR/gap-fade idx sleeve", IDX, F.combine_inv_vol(legs), mode="oc")
    add("A5.gapfade.XAU", "MR/gap-fade xau", ["XAUUSD"], leg_bt("XAUUSD", F.sig_gap_fade(F.load_daily("XAUUSD")), mode="oc"), mode="oc")

    # ── (B) TREND / MOMENTUM ─────────────────────────────────────────────────
    basket = ["US500", "US100", "GER40", "XAUUSD", "BTCUSD"]   # decorrelated multi-asset
    for k in (50, 100, 200):
        legs = {s: leg_bt(s, F.sig_tsmom(F.load_daily(s), k)) for s in basket}
        add(f"B1.tsmom.k{k}", "Trend/TSMOM basket", basket, F.combine_inv_vol(legs), note=f"K={k}")
    for s in ["US100", "XAUUSD", "BTCUSD"]:
        add(f"B2.tsmom100.{s}", "Trend/TSMOM single", [s], leg_bt(s, F.sig_tsmom(F.load_daily(s), 100)))
    # B3 Donchian breakout sleeves
    legs = {s: leg_bt(s, F.sig_donchian(F.load_daily(s), 20)) for s in IDX}
    add("B3.donchIDX", "Trend/Donchian idx sleeve", IDX, F.combine_inv_vol(legs))
    legs = {s: leg_bt(s, F.sig_donchian(F.load_daily(s), 20)) for s in FX}
    add("B3.donchFX", "Trend/Donchian fx sleeve", FX, F.combine_inv_vol(legs))
    # B4 long-only trend filter (beta baseline)
    legs = {s: leg_bt(s, F.sig_above_ma(F.load_daily(s), 200)) for s in IDX}
    add("B4.maLongIDX", "Trend/long-only MA200 idx", IDX, F.combine_inv_vol(legs), note="beta baseline")

    # ── (C) CROSS-SECTIONAL FX ───────────────────────────────────────────────
    add("C1.xsRevFX", "X-sec/1d reversal FX", FX, xs_fx(reversal=True), note="market-neutral")
    add("C2.xsMomFX", "X-sec/momentum FX", FX, xs_fx(reversal=False, k=60), note="registry-dead family")

    # ── (D) SEASONALITY / CALENDAR ───────────────────────────────────────────
    legs = {}
    for s in IDX:
        ser = leg_bt(s, F.sig_turn_of_month(F.load_daily(s), 1, 3)); legs[s] = ser
        add(f"D1.tom.{s}", "Seasonality/turn-of-month idx", [s], ser)
    add("D1.tomIDX", "Seasonality/turn-of-month idx sleeve", IDX, F.combine_ew(legs))
    add("D1.tom.XAU", "Seasonality/turn-of-month xau", ["XAUUSD"], leg_bt("XAUUSD", F.sig_turn_of_month(F.load_daily("XAUUSD"), 1, 3)))
    # D2 'best six months' Nov-Apr long indices
    legs = {s: leg_bt(s, F.sig_months(F.load_daily(s), {11, 12, 1, 2, 3, 4})) for s in IDX}
    add("D2.sixmonthIDX", "Seasonality/Nov-Apr idx", IDX, F.combine_ew(legs), note="long-only halloween")
    # D3 day-of-week (long Tuesday, short Monday) indices
    legs = {s: leg_bt(s, F.sig_weekday(F.load_daily(s), 1) - F.sig_weekday(F.load_daily(s), 0)) for s in IDX}
    add("D3.dowIDX", "Seasonality/day-of-week idx", IDX, F.combine_ew(legs))

    # ── (E) EVENT-CONDITIONED (calendar 2018+) ───────────────────────────────
    ev = F.load_events()
    legs = {}
    for s in IDX:
        ser = leg_bt(s, F.sig_pre_event(F.load_daily(s), ev["FOMC"], offset=1, hold=1)); legs[s] = ser
        add(f"E1.preFOMC.{s}", "Event/pre-FOMC idx", [s], ser, note="2018+")
    add("E1.preFOMC_IDX", "Event/pre-FOMC idx sleeve", IDX, F.combine_ew(legs), note="2018+")
    add("E1.preFOMC_XAU", "Event/pre-FOMC xau", ["XAUUSD"], leg_bt("XAUUSD", F.sig_pre_event(F.load_daily("XAUUSD"), ev["FOMC"], 1, 1)), note="2018+")
    add("E1.preFOMC_2d_IDX", "Event/pre-FOMC 2d idx", IDX,
        F.combine_ew({s: leg_bt(s, F.sig_pre_event(F.load_daily(s), ev["FOMC"], 1, 2)) for s in IDX}), note="hold=2,2018+")
    add("E2.preNFP_IDX", "Event/pre-NFP idx", IDX,
        F.combine_ew({s: leg_bt(s, F.sig_pre_event(F.load_daily(s), ev["NFP"], 1, 1)) for s in IDX}), note="2018+")
    add("E3.preCPI_IDX", "Event/pre-CPI idx", IDX,
        F.combine_ew({s: leg_bt(s, F.sig_pre_event(F.load_daily(s), ev["CPI"], 1, 1)) for s in IDX}), note="2018+")
    add("E4.postFOMC_IDX", "Event/post-FOMC drift idx", IDX,
        F.combine_ew({s: leg_bt(s, F.sig_post_event(F.load_daily(s), ev["FOMC"], 1, 1)) for s in IDX}), note="2018+")
    add("E5.preECB_GER", "Event/pre-ECB GER40", ["GER40"],
        leg_bt("GER40", F.sig_pre_event(F.load_daily("GER40"), ev["ECB"], 1, 1)), note="2018+")
    add("E1.preFOMC_EUR", "Event/pre-FOMC EURUSD", ["EURUSD"],
        leg_bt("EURUSD", F.sig_pre_event(F.load_daily("EURUSD"), ev["FOMC"], 1, 1, direction=-1.0)), note="USD-down pre-FOMC")

    # ── (F) VOL / REGIME ─────────────────────────────────────────────────────
    add("F1.lowvolLong_IDX", "Vol/low-vol drift idx", IDX,
        F.combine_inv_vol({s: leg_bt(s, vol_regime_long(F.load_daily(s))) for s in IDX}), note="long when calm")
    add("F2.volBreakout_IDX", "Vol/high-vol trend idx", IDX,
        F.combine_inv_vol({s: leg_bt(s, vol_regime_trend(F.load_daily(s))) for s in IDX}), note="trend when stormy")


# ── special builders ─────────────────────────────────────────────────────────
def xs_fx(reversal=True, k=1):
    """Cross-sectional FX: market-neutral rank by trailing return (reversal: long losers)."""
    R = F.ret_panel(F.FX).dropna(how="all")
    if k == 1:
        feat = R.shift(1)
    else:
        C = F.close_panel(F.FX)
        feat = (C / C.shift(k) - 1.0).shift(1)
    z = feat.sub(feat.mean(axis=1), axis=0).div(feat.std(axis=1).replace(0, np.nan), axis=0)
    pos = (-z if reversal else z).clip(-1, 1)
    pos = pos.sub(pos.mean(axis=1), axis=0)              # market-neutral
    # per-pair net with cost
    legs = {}
    for s in F.FX:
        d = F.load_daily(s)
        p = pos[s].reindex(d.index).fillna(0.0)
        gross = p * d["ret"]
        cost = 0.5 * d["rt_cost"] * p.diff().fillna(p).abs()
        legs[s] = (gross - cost).fillna(0.0)
    return pd.DataFrame(legs).sum(axis=1)

def vol_regime_long(df, k=20):
    """Long when trailing realised vol is below its 1y median (calm-drift)."""
    rv = df["ret"].rolling(k).std()
    med = rv.rolling(252, min_periods=60).median()
    return (rv < med).astype(float).shift(1)

def vol_regime_trend(df, k=20, kk=100):
    """Trade trend only when trailing vol is above its 1y median (stormy-trend)."""
    rv = df["ret"].rolling(k).std()
    med = rv.rolling(252, min_periods=60).median()
    mom = np.sign(df["close"] / df["close"].shift(kk) - 1.0)
    return (mom.where(rv > med, 0.0)).shift(1)


# ════════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
def analyse():
    df = pd.DataFrame(TRIALS)
    N = len(df)
    sig_oos = float(df["sharpe_oos"].std(ddof=1))         # OOS trial-Sharpe dispersion (selection)
    sig_full = float(df["sharpe_full"].std(ddof=1))
    print(f"\nN trials (true count) = {N} | OOS Sharpe dispersion sigma_SR = {sig_oos:.3f} | "
          f"full-sample sigma_SR = {sig_full:.3f}")

    # DSR on OOS, deflated at the true N. Three deflations bracket the std_sr_trials choice:
    #   primary  = OOS trial-Sharpe dispersion (consistent-sample, data-driven)  -> bar ~1.74
    #   strictest= repo dsr.py default std=1.0 (ultra-conservative)              -> bar ~2.38
    #   lenient  = full-sample trial-Sharpe dispersion (optimistic skill-spread) -> bar ~0.83
    dsr_p, dsr_strict, dsr_len, srbench = [], [], [], []
    for cid in df["id"]:
        _, oos = F.split_is_oos(SERIES[cid])
        d1 = F.dsr_oos(oos, n_trials=N, std_sr_trials=sig_oos)
        d0 = F.dsr_oos(oos, n_trials=N, std_sr_trials=1.0)
        d2 = F.dsr_oos(oos, n_trials=N, std_sr_trials=sig_full)
        dsr_p.append(d1["dsr"]); dsr_strict.append(d0["dsr"]); dsr_len.append(d2["dsr"])
        srbench.append(d1["sr_benchmark"])
    df["dsr_oos"] = dsr_p                          # PRIMARY gate
    df["dsr_oos_sig1"] = dsr_strict                # ultra-conservative
    df["dsr_oos_fullsig"] = dsr_len                # lenient sensitivity
    df["sr_benchmark"] = srbench

    # p_funded (color) for promising trials
    pf = {}
    for _, r in df.iterrows():
        if r["sharpe_full"] > 0.3 or r["sharpe_oos"] > 0.3:
            pf[r["id"]] = F.p_funded(SERIES[r["id"]], sigma_d=0.01)["p_combined"]
    df["p_funded_1pct"] = df["id"].map(pf).fillna(np.nan)

    df = df.sort_values("dsr_oos", ascending=False).reset_index(drop=True)
    df.to_json(RESULTS / "all_trials.json", orient="records", indent=2)
    cols = ["id", "mech", "sharpe_is", "sharpe_oos", "n_oos", "exkurt_oos", "skew_oos",
            "years_pos", "years_tot", "sr_benchmark", "dsr_oos", "dsr_oos_sig1",
            "dsr_oos_fullsig", "p_funded_1pct", "ann_vol_full", "maxdd_full", "note"]
    df[cols].to_csv(RESULTS / "all_trials.csv", index=False)

    survivors = df[df["dsr_oos"] > 0.5].copy()              # PRIMARY gate
    watch = df[df["dsr_oos_fullsig"] > 0.5].copy()          # conditional (lenient) watchlist
    print(f"\nCERTIFIED survivors DSR_oos>0.5 (primary)       : {len(survivors)}")
    print(f"CONDITIONAL watchlist DSR_oos_fullsig>0.5 (lenient): {len(watch)} -> {watch['id'].tolist()}")
    print(df[cols].head(18).to_string(index=False))

    # decorrelation analysis on whichever set is non-empty (certified first, else watchlist)
    sel = survivors if len(survivors) else watch
    chosen = []
    if len(sel):
        rp = pd.DataFrame({cid: SERIES[cid] for cid in sel["id"]}).sort_index()
        rp = rp[rp.index.dayofweek < 5].fillna(0.0)
        corr = rp.corr()
        ew = rp.mean(axis=1)
        stress = ew < ew.quantile(0.10)
        tcorr = rp[stress].corr() if stress.sum() > 10 else corr
        corr.round(3).to_csv(RESULTS / "watchlist_corr.csv")
        tcorr.round(3).to_csv(RESULTS / "watchlist_tailcorr.csv")
        chosen = greedy_decorrelate(sel, corr, tcorr, k=5)
        # sizing sweep p_funded for the chosen set
        sweep = {}
        for cid in chosen:
            sweep[cid] = {f"{sd:.3f}": round(F.p_funded(SERIES[cid], sigma_d=sd)["p_combined"], 3)
                          for sd in (0.006, 0.010, 0.015)}
        (RESULTS / "chosen_pfunded_sweep.json").write_text(json.dumps(sweep, indent=2))
        print("\nDecorrelated <=5 (from", "CERTIFIED" if len(survivors) else "CONDITIONAL", "set):", chosen)
        print(corr.loc[chosen, chosen].round(2).to_string())

    summary = dict(N_trials=N, sigma_SR_oos=sig_oos, sigma_SR_full=sig_full,
                   sr_benchmark_primary=float(df["sr_benchmark"].iloc[0]),
                   n_certified=int(len(survivors)), certified=survivors["id"].tolist(),
                   n_conditional=int(len(watch)), conditional=watch["id"].tolist(),
                   chosen=chosen, chosen_from=("certified" if len(survivors) else "conditional"),
                   oos_start=str(F.OOS_START.date()), markup=F.MARKUP,
                   artifacts_nulled=F._ARTIFACTS)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    return df, survivors, watch, chosen


def greedy_decorrelate(surv, corr, tcorr, k=5):
    order = surv.sort_values("dsr_oos", ascending=False)["id"].tolist()
    chosen = [order[0]]
    while len(chosen) < min(k, len(order)):
        best, best_score = None, 1e9
        for cid in order:
            if cid in chosen:
                continue
            score = max(max(abs(corr.loc[cid, c]), abs(tcorr.loc[cid, c])) for c in chosen)
            if score < best_score:
                best, best_score = cid, score
        if best is None:
            break
        chosen.append(best)
    return chosen


if __name__ == "__main__":
    build_all()
    analyse()
    print("\nDONE ->", RESULTS)
