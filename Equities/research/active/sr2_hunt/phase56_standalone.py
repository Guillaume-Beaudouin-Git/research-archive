"""Phase 5 (volume microstructure) + Phase 6 (ML) — standalone, no external imports."""
from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import yfinance as yf
import statsmodels.api as sm
import json, os

# ── constants ──────────────────────────────────────────────────────────────
IS_START, IS_END     = "2015-01-01", "2021-12-31"
OOS_START, OOS_END   = "2022-01-01", "2024-12-31"
HOLD_START, HOLD_END = "2025-01-01", "2026-05-26"
COST = 7 / 10_000   # 7 bps RT (5 bp commission + 2 bp slip)
N_PREV = 727

def fetch_rf() -> pd.Series:
    try:
        import pandas_datareader as pdr
        rf = pdr.get_data_fred("DTB3", start="2014-01-01", end=HOLD_END)["DTB3"]
        return (rf / 100 / 252).dropna()
    except Exception:
        return pd.Series(0.0, index=pd.date_range("2014-01-01", HOLD_END, freq="B"))

def sharpe(ret: pd.Series, ann: float = 252) -> float:
    if ret.empty or ret.std() == 0: return 0.0
    return float(ret.mean() / ret.std() * np.sqrt(ann))

def mdd(ret: pd.Series) -> float:
    c = (1 + ret).cumprod()
    return float((c / c.cummax() - 1).min())

def exc(ret: pd.Series, rf: pd.Series) -> pd.Series:
    return ret - rf.reindex(ret.index, method="ffill").fillna(0)

def metrics(r: pd.Series, rf: pd.Series):
    if r.empty or r.std() == 0: return 0.0, 0.0
    return sharpe(exc(r, rf)), mdd(r)

def fetch_ohlcv(ticker: str) -> pd.DataFrame:
    df = yf.download(ticker, start="2013-01-01", end=HOLD_END,
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df[["Open","High","Low","Close","Volume"]].dropna()

print("=== PHASE 5+6 (standalone) ===\n")
rf = fetch_rf()

print("Fetching data...")
spy = fetch_ohlcv("SPY");  qqq = fetch_ohlcv("QQQ")
vix_raw = yf.download("^VIX", start="2013-01-01", end=HOLD_END, auto_adjust=True, progress=False)
if isinstance(vix_raw.columns, pd.MultiIndex): vix_raw.columns = vix_raw.columns.get_level_values(0)
vix = vix_raw["Close"].dropna()
if isinstance(vix, pd.DataFrame): vix = vix.iloc[:,0]
print(f"  SPY={len(spy)}, QQQ={len(qqq)}, VIX={len(vix)}")

N_TESTS = N_PREV
candidates: list[dict] = []

def backtest(ohlcv, signal, cost=COST):
    ret = ohlcv["Close"].pct_change().dropna()
    pos = signal.shift(1).reindex(ret.index).fillna(0)
    return pos * ret - cost * pos.diff().abs().fillna(0)

def eval_and_log(strat_ret, sid, desc, phase, params):
    sr_is, mdd_is     = metrics(strat_ret.loc[IS_START:IS_END], rf)
    sr_oos, mdd_oos   = metrics(strat_ret.loc[OOS_START:OOS_END], rf)
    sr_hold, mdd_hold = metrics(strat_ret.loc[HOLD_START:HOLD_END], rf)
    print(f"  [{sid}] IS={sr_is:+.2f} OOS={sr_oos:+.2f} HOLD={sr_hold:+.2f} | MDD_IS={mdd_is:.1%}")
    return dict(id=sid, phase=phase, description=desc, params=params,
                sr_is=sr_is, mdd_is=mdd_is, sr_oos=sr_oos, mdd_oos=mdd_oos,
                sr_hold=sr_hold, mdd_hold=mdd_hold)

# ══════════════════════════════════════════════════════════════════════════
# PHASE 5 — Volume microstructure proxies
# ══════════════════════════════════════════════════════════════════════════
print("\n--- Phase 5: Volume Signals ---")

for ticker, ohlcv in [("SPY", spy), ("QQQ", qqq)]:
    p = ohlcv["Close"]; vol = ohlcv["Volume"]
    ret = p.pct_change().dropna()
    rvol = vol / vol.rolling(20).mean()

    # 5.1 RVol + direction (follow / fade high-vol days)
    for rv_th in [1.5, 2.0, 2.5]:
        for fade in [False, True]:
            N_TESTS += 1
            hv = rvol > rv_th
            direction = pd.Series(np.sign(ret.reindex(hv.index).fillna(0)), index=hv.index)
            sig = pd.Series(0.0, index=p.index)
            sig[hv] = direction[hv] * (-1 if fade else 1)
            sr = sharpe(exc(backtest(ohlcv, sig).loc[IS_START:IS_END], rf))
            tag = "fade" if fade else "follow"
            key = f"P5.1_{ticker}_RVol{int(rv_th*10)}_{tag}"
            if sr >= 1.0:
                result = eval_and_log(backtest(ohlcv, sig), key,
                    f"{ticker} RVol{rv_th} {tag}", "5.1", {"rv_th": rv_th, "fade": fade})
                candidates.append(result)
            else:
                print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # 5.2 OBV trend
    for obv_s in [10, 20]:
        N_TESTS += 1
        obv = (pd.Series(np.sign(ret.reindex(vol.index).fillna(0)), index=vol.index) * vol).fillna(0).cumsum()
        sig = (obv > obv.rolling(obv_s).mean()).astype(float)
        sr = sharpe(exc(backtest(ohlcv, sig).loc[IS_START:IS_END], rf))
        key = f"P5.2_{ticker}_OBV{obv_s}"
        if sr >= 1.0:
            result = eval_and_log(backtest(ohlcv, sig), key, f"{ticker} OBV{obv_s}", "5.2", {})
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # 5.3 Vol-weighted momentum
    for lb in [5, 10, 20]:
        N_TESTS += 1
        vwm = (ret * rvol.reindex(ret.index).fillna(1)).rolling(lb).mean()
        sig = pd.Series(np.sign(vwm), index=p.index)
        sr = sharpe(exc(backtest(ohlcv, sig).loc[IS_START:IS_END], rf))
        key = f"P5.3_{ticker}_VWM{lb}"
        if sr >= 1.0:
            result = eval_and_log(backtest(ohlcv, sig), key, f"{ticker} VolWgtMom{lb}", "5.3", {})
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # 5.4 Price-volume divergence
    for lb in [5, 10]:
        N_TESTS += 1
        pm = p.pct_change(lb); vm = vol.pct_change(lb)
        sig = pd.Series(0.0, index=p.index)
        sig[(pm > 0) & (vm < 0)] = -1.0   # price up, vol down → fade
        sig[(pm < 0) & (vm > 0)] = 1.0    # price down, vol up → fade
        sig = sig.shift(1).fillna(0)
        strat = sig.reindex(ret.index).fillna(0) * ret - COST * sig.reindex(ret.index).fillna(0).diff().abs().fillna(0)
        sr = sharpe(exc(strat.loc[IS_START:IS_END], rf))
        key = f"P5.4_{ticker}_PVdiv{lb}"
        if sr >= 1.0:
            result = eval_and_log(strat, key, f"{ticker} PVdiv{lb}", "5.4", {})
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

p5_count = N_TESTS - N_PREV
print(f"\nPhase 5: {p5_count} tests, {len(candidates)} IS passes")

# ══════════════════════════════════════════════════════════════════════════
# PHASE 6 — ML with XGBoost / GBM
# ══════════════════════════════════════════════════════════════════════════
print("\n--- Phase 6: ML ---")

try:
    from xgboost import XGBRegressor as GBM
    GBM_KWARGS = {"verbosity": 0, "n_jobs": 1}
    print("  Using XGBoost")
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor as GBM
    GBM_KWARGS = {}
    print("  Using sklearn GBM")

from sklearn.ensemble import RandomForestRegressor as RF

def build_features(ohlcv: pd.DataFrame, vix_s: pd.Series) -> pd.DataFrame:
    p = ohlcv["Close"]; vol = ohlcv["Volume"]; ret = p.pct_change()
    df = pd.DataFrame(index=p.index)
    for lb in [5, 10, 21, 63]: df[f"mom_{lb}"] = p.pct_change(lb)
    df["trend_200"] = p / p.rolling(200).mean() - 1
    df["vol_20"]    = ret.rolling(20).std() * np.sqrt(252)
    df["vix"]       = vix_s.reindex(p.index, method="ffill")
    df["vix_chg5"]  = df["vix"].pct_change(5)
    df["rvol"]      = vol / vol.rolling(20).mean()
    df["month"]     = p.index.month
    df["target"]    = ret.shift(-1)
    return df.dropna()

FEATS = ["mom_5","mom_10","mom_21","mom_63","trend_200","vol_20","vix","vix_chg5","rvol","month"]

def ml_bt(ohlcv, feats_df, model_cls, model_kw, sid, ticker):
    X = feats_df[FEATS]; y = feats_df["target"]
    ret = ohlcv["Close"].pct_change().dropna()
    X_is = X.loc[IS_START:IS_END]; y_is = y.loc[IS_START:IS_END]
    mdl = model_cls(**model_kw); mdl.fit(X_is, y_is)
    preds = pd.Series(mdl.predict(X), index=X.index)
    sig = pd.Series(np.sign(preds), index=X.index)
    pos = sig.shift(1).reindex(ret.index).fillna(0)
    strat = pos * ret - COST * pos.diff().abs().fillna(0)
    sr_is, mdd_is     = metrics(strat.loc[IS_START:IS_END], rf)
    sr_oos, mdd_oos   = metrics(strat.loc[OOS_START:OOS_END], rf)
    sr_hold, mdd_hold = metrics(strat.loc[HOLD_START:HOLD_END], rf)
    print(f"  [{sid}] {ticker} | IS={sr_is:+.2f} OOS={sr_oos:+.2f} HOLD={sr_hold:+.2f}")
    return dict(id=sid, phase="6", description=f"ML {sid} {ticker}", params=model_kw,
                sr_is=sr_is, mdd_is=mdd_is, sr_oos=sr_oos, mdd_oos=mdd_oos,
                sr_hold=sr_hold, mdd_hold=mdd_hold)

# Purged K-Fold IC check
def purged_ic(X_is, y_is, model_cls, kw, n_folds=5, embargo=21):
    from scipy.stats import spearmanr
    n = len(X_is); fs = n // n_folds; ics = []
    for f in range(n_folds - 1):
        te = fs * (f + 1); vs = te + embargo; ve = min(te + fs + embargo, n)
        if vs >= ve: continue
        m = model_cls(**kw); m.fit(X_is.iloc[:te], y_is.iloc[:te])
        ic, _ = spearmanr(m.predict(X_is.iloc[vs:ve]), y_is.iloc[vs:ve])
        ics.append(ic)
    return ics

configs_gbm = [
    {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.05, **GBM_KWARGS},
    {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.02, **GBM_KWARGS},
    {"n_estimators": 100, "max_depth": 4, "learning_rate": 0.05, **GBM_KWARGS},
]
configs_rf = [
    {"n_estimators": 100, "max_depth": 4, "n_jobs": -1},
    {"n_estimators": 200, "max_depth": 3, "n_jobs": -1},
]

print("\n  GBM models:")
for ticker, ohlcv in [("SPY", spy), ("QQQ", qqq)]:
    feats = build_features(ohlcv, vix)
    for cfg in configs_gbm:
        N_TESTS += 1
        sid = f"P6_GBM_{ticker}_d{cfg['max_depth']}_lr{int(cfg['learning_rate']*100)}"
        r = ml_bt(ohlcv, feats, GBM, cfg, sid, ticker)
        if r["sr_is"] >= 1.0: candidates.append(r)

print("\n  RF models:")
for ticker, ohlcv in [("SPY", spy), ("QQQ", qqq)]:
    feats = build_features(ohlcv, vix)
    for cfg in configs_rf:
        N_TESTS += 1
        sid = f"P6_RF_{ticker}_d{cfg['max_depth']}_n{cfg['n_estimators']}"
        r = ml_bt(ohlcv, feats, RF, cfg, sid, ticker)
        if r["sr_is"] >= 1.0: candidates.append(r)

# Purged CV IC on best GBM (SPY)
feats_spy = build_features(spy, vix)
X_is = feats_spy.loc[IS_START:IS_END][FEATS]
y_is = feats_spy.loc[IS_START:IS_END]["target"]
best_kw = {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.02, **GBM_KWARGS}
ics = purged_ic(X_is, y_is, GBM, best_kw)
print(f"\n  Purged K-Fold ICs (SPY GBM200/d3): {[f'{s:.3f}' for s in ics]}")
print(f"  Mean IC={np.mean(ics):.3f}, Positive={sum(s>0 for s in ics)}/{len(ics)} folds")

p6_count = N_TESTS - N_PREV - p5_count

# ══════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*65}")
print("FINAL SUMMARY — ALL PHASES")
print(f"{'='*65}")
print(f"Phase 5 tests: {p5_count}")
print(f"Phase 6 tests: {p6_count}")
print(f"Total session tests: {N_TESTS - 322}  |  Global n_tests: {N_TESTS}")
print(f"\nIS passes (valid, SR≥1.0): {len(candidates)}")
for c in candidates:
    print(f"  {c['id']}: IS={c['sr_is']:.2f} OOS={c['sr_oos']:.2f} HOLD={c['sr_hold']:.2f}")

oos_pass  = [c for c in candidates if c.get("sr_oos", 0) >= 1.5]
hold_pass = [c for c in candidates if c.get("sr_hold", 0) >= 2.0]
print(f"\nOOS≥1.5: {len(oos_pass)}")
print(f"HOLDOUT≥2.0: {len(hold_pass)}")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "final_results.json"), "w") as f:
    json.dump({"n_tests": N_TESTS, "candidates": candidates,
               "oos_passes": oos_pass, "hold_passes": hold_pass}, f, indent=2, default=str)
print("Results saved: final_results.json")
