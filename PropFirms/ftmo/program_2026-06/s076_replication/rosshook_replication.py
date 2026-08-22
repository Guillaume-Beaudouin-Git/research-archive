"""
rosshook_replication.py — INDEPENDENT re-implementation of S076 "Ross Hook" (proxy) from
SPEC_S076 §5 pseudocode. Does NOT import/call ftmo_lab or code/rosshook.py.

FROZEN params (NO optimization): Min_Setup=10, Max_Hook=20, Time=10, ATR_Length=20,
ATR_Stop=6, RISK_FRAC=0.5%, depth_ratio=None.
Fill: realistic = O[e_bar+1+delay] (PRIMARY); optimistic = max(O[e_bar],H*) (gate ref).
Returns: MARK-TO-MARKET daily close-to-close of every open position (NOT R-over-holding).

Outputs CSVs to research/s076_replication/results/. READ-ONLY on source data.
"""
from __future__ import annotations
import json
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path("<HOME>/Desktop/Algo_claude")
DAILY = ROOT / "research/s076_replication/daily"
RES = ROOT / "research/s076_replication/results"; RES.mkdir(parents=True, exist_ok=True)

MIN_SETUP, MAX_HOOK, TIME_I, ATR_LEN, ATR_STOP, RISK_FRAC = 10, 20, 10, 20, 6, 0.005
CLASS = {"US500": "index", "US100": "index", "US30": "index", "GER40": "index", "US2000": "index",
         "XAUUSD": "commodity", "BTCUSD": "crypto",
         **{s: "fx" for s in ["EURUSD", "GBPUSD", "EURGBP", "NZDUSD", "USDCHF", "AUDJPY",
                              "EURJPY", "AUDUSD", "USDCAD", "USDJPY"]}}
DEPLOYABLE = [s for s, c in CLASS.items() if c != "fx"]
FX = [s for s, c in CLASS.items() if c == "fx"]
POINT = {**{s: 1e-5 for s in ["EURUSD", "GBPUSD", "EURGBP", "NZDUSD", "USDCHF", "AUDUSD", "USDCAD"]},
         **{s: 1e-3 for s in ["USDJPY", "EURJPY", "AUDJPY"]},
         **{s: 1e-2 for s in ["XAUUSD", "US500", "US100", "US30", "GER40", "US2000", "BTCUSD"]}}
FLAT_RT_BPS = {"fx": 1.5, "index": 2.0, "commodity": 4.0, "crypto": 8.0}   # report's per-class
COMM_BPS = {"fx": 0.2, "index": 0.5, "commodity": 1.0, "crypto": 2.0}      # primary commission est.
ANN = 252


def atr(d: pd.DataFrame, n: int = ATR_LEN) -> np.ndarray:
    pc = d["close"].shift(1)
    tr = pd.concat([d["high"] - d["low"], (d["high"] - pc).abs(), (d["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().values   # "True Range moyen" = simple MA (per spec)


def load_daily(sym: str, boundary: str = "EET") -> pd.DataFrame:
    d = pd.read_parquet(DAILY / f"{sym}_{boundary}.parquet").sort_index()
    d = d[d["close"] > 0].copy()
    return d


def simulate(d: pd.DataFrame, sym: str, *, delay: int = 1, fill: str = "realistic",
             placebo: bool = False, cost_mode: str = "real", extra_bps: float = 0.0,
             truncate=None) -> pd.DataFrame:
    """Return trades DataFrame. delay applied on realistic fill (O[e_bar+1+delay])."""
    if truncate is not None:
        d = d[d.index < pd.Timestamp(truncate)]
    H, L, O, C = (d[c].values for c in ("high", "low", "open", "close"))
    A = atr(d)
    so = d["spread_open"].values
    dates = d.index
    n = len(H)
    HH = pd.Series(H).rolling(MIN_SETUP).max().values   # inclusive of bar i
    LL = pd.Series(L).rolling(MIN_SETUP).min().values
    pt = POINT[sym]; cls = CLASS[sym]
    trades = []
    i = MIN_SETUP + 1
    while i < n - 1:
        d_dir = 0; e_detect = e_bar = -1; quick = np.nan
        okA = np.isfinite(A[i]) and A[i] > 0
        # ---- LONG candidate: new Min_Setup high ----
        if okA and H[i] >= HH[i] and H[i] > H[i - 1]:
            Hstar = H[i]
            if placebo:
                d_dir, e_detect, e_bar, quick = 1, i, i, -np.inf
            else:
                pulled, hooklow = False, np.inf
                for j in range(i + 1, min(i + MAX_HOOK, n - 1) + 1):
                    if H[j] < Hstar:
                        pulled = True; hooklow = min(hooklow, L[j])
                    if pulled and H[j] >= Hstar:
                        d_dir, e_detect, e_bar, quick = 1, i, j, hooklow; break
        # ---- SHORT candidate (mirror) if no long ----
        if d_dir == 0 and okA and L[i] <= LL[i] and L[i] < L[i - 1]:
            Lstar = L[i]
            if placebo:
                d_dir, e_detect, e_bar, quick = -1, i, i, np.inf
            else:
                pulled, hookhigh = False, -np.inf
                for j in range(i + 1, min(i + MAX_HOOK, n - 1) + 1):
                    if L[j] > Lstar:
                        pulled = True; hookhigh = max(hookhigh, H[j])
                    if pulled and L[j] <= Lstar:
                        d_dir, e_detect, e_bar, quick = -1, i, j, hookhigh; break
        if d_dir == 0:
            i += 1; continue
        # ---- execution ----
        if fill == "optimistic" and not placebo:
            entry_bar = e_bar
            entry = max(O[e_bar], H[e_detect]) if d_dir > 0 else min(O[e_bar], L[e_detect])
        else:  # realistic: next day's open (+delay)
            entry_bar = e_bar + 1 + delay
            if entry_bar >= n:
                break
            entry = O[entry_bar]
        risk0 = A[e_detect] * ATR_STOP
        astop = entry - d_dir * risk0
        kmax = min(entry_bar + TIME_I, n - 1)
        exit_price = exit_bar = reason = None
        for k in range(entry_bar, kmax + 1):
            if d_dir > 0:
                if L[k] <= quick:
                    exit_price, exit_bar, reason = quick, k, "quick"; break
                if L[k] <= astop:
                    exit_price, exit_bar, reason = astop, k, "astop"; break
            else:
                if H[k] >= quick:
                    exit_price, exit_bar, reason = quick, k, "quick"; break
                if H[k] >= astop:
                    exit_price, exit_bar, reason = astop, k, "astop"; break
            if k == kmax:
                exit_price, exit_bar, reason = C[k], k, "time"
        gross_R = d_dir * (exit_price - entry) / risk0
        # ---- costs (in R units) ----
        if cost_mode == "real":
            spread_px = 0.5 * (so[entry_bar] + so[exit_bar]) * pt          # full round-turn spread
            slip_px = 2 * pt                                                # 1 tick / side
            comm_px = COMM_BPS[cls] / 1e4 * entry
            cost_px = spread_px + slip_px + comm_px
        else:  # flat per-class bps
            cost_px = FLAT_RT_BPS[cls] / 1e4 * entry
        cost_px += extra_bps / 1e4 * entry                                  # stress
        cost_R = cost_px / risk0
        net_R = gross_R - cost_R
        trades.append(dict(sym=sym, cls=cls, dir=d_dir, entry_bar=entry_bar, exit_bar=exit_bar,
                           entry_date=dates[entry_bar], exit_date=dates[exit_bar],
                           entry=entry, exit=exit_price, risk0=risk0, grossR=gross_R,
                           costR=cost_R, netR=net_R, reason=reason))
        i = exit_bar + 1
    return pd.DataFrame(trades)


def mtm_daily(trades: pd.DataFrame, d: pd.DataFrame) -> pd.Series:
    """Mark-to-market daily return series (RISK_FRAC per trade) over the instrument's full calendar."""
    ret = pd.Series(0.0, index=d.index)
    C = d["close"]; pos = {t: i for i, t in enumerate(d.index)}
    for _, tr in trades.iterrows():
        eb, xb, dirn, r0, entry, xprice = int(tr.entry_bar), int(tr.exit_bar), tr.dir, tr.risk0, tr.entry, tr.exit
        for k in range(eb, xb + 1):
            prev = entry if k == eb else C.iloc[k - 1]
            cur = xprice if k == xb else C.iloc[k]
            ret.iloc[k] += RISK_FRAC * dirn * (cur - prev) / r0
        ret.iloc[eb] -= RISK_FRAC * tr.costR   # book cost on entry day
    return ret


def sharpe(x: pd.Series, ann: int = ANN) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * np.sqrt(ann)) if len(x) > 2 and x.std() > 0 else np.nan


def trade_stats(tr: pd.DataFrame, years: float) -> dict:
    if len(tr) == 0:
        return dict(n=0, win=np.nan, expR=np.nan, pf=np.nan, sharpe_trade=np.nan)
    r = tr["netR"]
    gp, gl = r[r > 0].sum(), -r[r < 0].sum()
    tpy = len(tr) / years if years > 0 else np.nan
    return dict(n=len(tr), win=float((r > 0).mean()), expR=float(r.mean()),
                pf=float(gp / gl) if gl > 0 else np.inf,
                sharpe_trade=float(r.mean() / r.std() * np.sqrt(tpy)) if r.std() > 0 and tpy == tpy else np.nan)


def boot_ci(vals: np.ndarray, n_boot: int = 2000, seed: int = 7) -> tuple:
    if len(vals) < 5:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = [rng.choice(vals, len(vals), replace=True).mean() for _ in range(n_boot)]
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def nw_alpha(y: pd.Series, X: pd.DataFrame, lags: int = 6) -> dict:
    """OLS y ~ const + X with Newey-West HAC SE. Returns alpha (ann), t, betas."""
    df = pd.concat([y.rename("y"), X], axis=1).dropna()
    if len(df) < 60:
        return dict(alpha_ann=np.nan, alpha_t=np.nan, betas={}, n=len(df))
    try:
        import statsmodels.api as sm
        Xc = sm.add_constant(df[X.columns])
        m = sm.OLS(df["y"], Xc).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
        return dict(alpha_ann=float(m.params["const"] * ANN), alpha_t=float(m.tvalues["const"]),
                    betas={c: round(float(m.params[c]), 4) for c in X.columns}, n=int(len(df)))
    except Exception:  # manual Newey-West fallback
        Xm = np.column_stack([np.ones(len(df))] + [df[c].values for c in X.columns])
        yv = df["y"].values
        XtX_inv = np.linalg.inv(Xm.T @ Xm)
        beta = XtX_inv @ Xm.T @ yv
        resid = yv - Xm @ beta
        S = (Xm * resid[:, None]).T @ (Xm * resid[:, None])
        for L in range(1, lags + 1):
            w = 1 - L / (lags + 1)
            G = (Xm[L:] * resid[L:, None]).T @ (Xm[:-L] * resid[:-L, None])
            S += w * (G + G.T)
        cov = XtX_inv @ S @ XtX_inv
        return dict(alpha_ann=float(beta[0] * ANN), alpha_t=float(beta[0] / np.sqrt(cov[0, 0])),
                    betas={c: round(float(beta[k + 1]), 4) for k, c in enumerate(X.columns)}, n=int(len(df)))


if __name__ == "__main__":
    print("module loaded; run rosshook_run.py for the full study")
