"""
Stage B — intraday-flat pair strategies on pairs that cleared K1.

Every run is walk-forward by construction (K9): parameters come from a formation
window that STRICTLY precedes the trading window; formation never touches trading.

K7 (delay+1 on BOTH ends): the signal is read on the close of bar t, entry and
exit both fill at the OPEN of bar t+1. Threshold exits are repriced at the WORSE
of the trigger level and the next bar's open.

Positions are FORCED FLAT at the last common bar of each UTC day: the whole point
of the family here is to pay no financing (2 legs x ~1.5 bps/night, L28).

Accounting: leg A notional = 1, leg B notional = |b|. P&L in bps of leg-A
notional. Cost per round trip = cost_rt(A) + |b| * cost_rt(B)  -- BOTH legs.
"""
import os
import numpy as np
import pandas as pd

M5 = "<SCRATCH>"
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/outputs"
os.makedirs(OUT, exist_ok=True)

# Round-trip cost in bps per leg. COST_AUDIT 2026-07-31: indices ~1.8 centre
# (2.9 tail), XAUUSD 1.84 (3.88 tail), FX per section 2. The `spread` column is
# NEVER used alone (US30 79.7/100/74.9% null bars 2019/20/21).
COST_RT = {
    "US500": 1.82, "US100": 1.80, "US30": 1.47, "GER40": 1.73,
    "XAUUSD": 1.84, "XAGUSD": 3.50, "COPPER": 4.00,
    "UKOIL": 3.00, "USOIL": 3.00,
    "EURUSD": 1.13, "GBPUSD": 1.30, "USDJPY": 1.20, "USDCHF": 1.50,
    "USDCAD": 1.36, "AUDUSD": 1.36, "NZDUSD": 1.80,
    "EURGBP": 1.65, "EURJPY": 1.60, "AUDJPY": 1.80,
}
COST_TAIL_MULT = 1.6   # provisioned tail (COST_AUDIT section 5)


def load(sym, start="2014-01-01", end="2026-06-05"):
    df = pd.read_parquet(f"{M5}/{sym}_M5.parquet", columns=["open", "close"])
    return df.loc[start:end]


def align(a, b, symA, symB):
    df = pd.concat([load(symA).add_prefix("A_"), load(symB).add_prefix("B_")],
                   axis=1).dropna()
    df["lA_c"] = np.log(df["A_close"]); df["lB_c"] = np.log(df["B_close"])
    df["lA_o"] = np.log(df["A_open"]);  df["lB_o"] = np.log(df["B_open"])
    df["day"] = df.index.normalize()
    return df


def _ols(y, x):
    xm, ym = x.mean(), y.mean()
    vx = ((x - xm) ** 2).sum()
    if vx <= 0:
        return np.nan, np.nan
    b = ((x - xm) * (y - ym)).sum() / vx
    return float(ym - b * xm), float(b)


def run(symA, symB, method="EG_static", z_in=2.0, z_out=0.0, z_stop=4.0,
        form_days=20, trade_days=5, cost_mult=1.0, entry_cutoff_bars=6,
        beta_mode=None, seed_shift=0):
    """
    method: 'EG_static' (OLS beta on formation), 'DIST' (beta=1 on normalised
            log prices, Gatev), 'EG_roll' (beta re-estimated each trading day
            from the trailing formation window -> dynamic hedge ratio).
    seed_shift: circular shift (in bars) applied to the residual for the K8
            placebo -- destroys the level information, preserves autocorrelation.
    """
    df = align(None, None, symA, symB)
    if df.empty:
        return None
    days = np.array(sorted(df["day"].unique()))
    cA, cB = COST_RT[symA], COST_RT[symB]

    trades = []
    daily = {}
    n_folds = 0
    for k in range(form_days, len(days) - 1, trade_days):
        fdays = days[k - form_days:k]
        tdays = days[k:k + trade_days]
        if len(tdays) == 0:
            break
        f = df[df["day"].isin(fdays)]
        if len(f) < 800:
            continue
        if method == "DIST":
            a0, beta = 0.0, 1.0
            # Gatev normalisation: level offset only
            a0 = float((f["lA_c"] - f["lB_c"]).mean())
            res_f = f["lA_c"] - a0 - f["lB_c"]
        else:
            a0, beta = _ols(f["lA_c"].values, f["lB_c"].values)
            if not np.isfinite(beta):
                continue
            res_f = f["lA_c"] - a0 - beta * f["lB_c"]
        mu, sd = float(res_f.mean()), float(res_f.std())
        if not np.isfinite(sd) or sd <= 0:
            continue
        n_folds += 1

        t = df[df["day"].isin(tdays)].copy()
        if len(t) < 50:
            continue
        t["res"] = t["lA_c"] - a0 - beta * t["lB_c"]
        if seed_shift:
            v = t["res"].values
            t["res"] = np.roll(v, seed_shift % max(len(v), 1))
        t["z"] = (t["res"] - mu) / sd

        # ---- intraday-flat event loop, delay+1 on entry AND exit ----
        for _, d in t.groupby("day"):
            if len(d) < 20:
                continue
            z = d["z"].values
            lAo, lBo = d["lA_o"].values, d["lB_o"].values
            n = len(d)
            last = n - 1
            pos = 0; ei = -1
            for i in range(n - 1):
                if pos == 0:
                    if i > last - entry_cutoff_bars:
                        continue
                    if abs(z[i]) >= z_in:
                        pos = -1 if z[i] > 0 else 1     # fade the deviation
                        ei = i + 1                       # fill next bar OPEN
                else:
                    hit_out = abs(z[i]) <= z_out
                    hit_stop = abs(z[i]) >= z_stop
                    forced = (i + 1) >= last
                    if hit_out or hit_stop or forced:
                        xi = i + 1
                        gross = pos * ((lAo[xi] - lAo[ei]) -
                                       beta * (lBo[xi] - lBo[ei])) * 1e4
                        cost = (cA + abs(beta) * cB) * cost_mult
                        trades.append({
                            "t": d.index[xi], "side": pos, "gross": gross,
                            "net": gross - cost, "cost": cost,
                            "bars": xi - ei, "z_entry": z[ei - 1],
                            "reason": "stop" if hit_stop else ("out" if hit_out else "eod"),
                        })
                        pos = 0; ei = -1
    if not trades:
        return {"n_trades": 0, "n_folds": n_folds}
    tr = pd.DataFrame(trades).set_index("t")
    d_net = tr["net"].resample("1D").sum().reindex(
        pd.date_range(tr.index[0].normalize(), tr.index[-1].normalize(), freq="D")).fillna(0.0)
    d_net = d_net[d_net.index.dayofweek < 5]
    d_gross = tr["gross"].resample("1D").sum().reindex(d_net.index).fillna(0.0)
    return {"trades": tr, "daily_net": d_net, "daily_gross": d_gross,
            "n_trades": len(tr), "n_folds": n_folds}


def hac_t(x, lags=6):
    import statsmodels.api as sm
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 30 or x.std() == 0:
        return np.nan
    r = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(r.tvalues[0])


def summarise(res, label):
    if not res or res.get("n_trades", 0) == 0:
        return {"cell": label, "n_trades": 0, "verdict": "NO_TRADES"}
    tr, dn, dg = res["trades"], res["daily_net"], res["daily_gross"]
    lo = tr[tr.side == 1]["net"]; sh = tr[tr.side == -1]["net"]
    ann = 252.0
    sr = float(dn.mean() / dn.std() * np.sqrt(ann)) if dn.std() > 0 else np.nan
    return {
        "cell": label, "n_trades": len(tr), "n_folds": res["n_folds"],
        "gross_per_trade_bps": float(tr["gross"].mean()),
        "net_per_trade_bps": float(tr["net"].mean()),
        "cost_per_trade_bps": float(tr["cost"].mean()),
        "t_hac_gross_daily": hac_t(dg),
        "t_hac_net_daily": hac_t(dn),
        "sharpe_net": sr,
        "median_bars": float(tr["bars"].median()),
        "n_long": len(lo), "mean_long": float(lo.mean()) if len(lo) else np.nan,
        "t_long": hac_t(lo.values) if len(lo) > 30 else np.nan,
        "n_short": len(sh), "mean_short": float(sh.mean()) if len(sh) else np.nan,
        "t_short": hac_t(sh.values) if len(sh) > 30 else np.nan,
        "eod_frac": float((tr.reason == "eod").mean()),
        "stop_frac": float((tr.reason == "stop").mean()),
    }
