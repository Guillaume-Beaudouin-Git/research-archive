"""
Phase-1 arbiter: beta-regression + regime split (up/chop/down) for S1.

Inputs:
  results/s1_trades.parquet      — trade-level S1 results (pnl_R per session)
  results/nq_daily_rth_2010_2026.parquet — daily NQ RTH OHLC

Outputs:
  results/s1_beta_regression.json
  results/s1_regime_tagged.parquet
  results/s1_regime_table.csv
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path("<HOME>/Desktop/Algo_claude")
RES = ROOT / "Futures/research/active/ftmo_3strats_audit_2026-06/results"


def hac_regress(y: pd.Series, x: pd.Series, lags: int = 6) -> dict:
    """OLS y = alpha + beta * x, Newey-West HAC standard errors lag=lags."""
    df = pd.concat([y, x], axis=1).dropna()
    df.columns = ["y", "x"]
    if len(df) < 50:
        return {"n": len(df), "alpha": None, "beta": None}
    X = sm.add_constant(df["x"].values)
    model = sm.OLS(df["y"].values, X)
    res = model.fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    alpha, beta = float(res.params[0]), float(res.params[1])
    se_alpha, se_beta = float(res.bse[0]), float(res.bse[1])
    t_alpha, t_beta = float(res.tvalues[0]), float(res.tvalues[1])
    r2 = float(res.rsquared)
    return {
        "n": int(len(df)),
        "alpha": alpha,
        "beta": beta,
        "se_alpha_hac": se_alpha,
        "se_beta_hac": se_beta,
        "t_alpha_hac": t_alpha,
        "t_beta_hac": t_beta,
        "r2": r2,
        "alpha_annualized_R": alpha * 252,
    }


def main() -> None:
    tr = pd.read_parquet(RES / "s1_trades.parquet")
    d = pd.read_parquet(RES / "nq_daily_rth_2010_2026.parquet")
    d.index = pd.to_datetime(d.index)

    # NQ RTH daily return (close-to-close)
    d["ret_nq"] = d["close"].pct_change()

    # Build aligned daily S1 R series + NQ ret
    s1 = tr["pnl_R"].copy()
    s1.index = pd.to_datetime(s1.index)
    joined = pd.DataFrame({"s1_R": s1, "nq_ret": d["ret_nq"]}).dropna()

    # ---- Full-sample beta regression ----
    full = hac_regress(joined["s1_R"], joined["nq_ret"], lags=6)
    print("[full-sample beta]", json.dumps(full, indent=2), flush=True)

    # ---- Long-leg vs Short-leg regressions ----
    dir_ = tr["direction"].reindex(joined.index)
    long_R = joined["s1_R"].where(dir_ == 1, 0.0)
    short_R = joined["s1_R"].where(dir_ == -1, 0.0)
    long_reg = hac_regress(long_R, joined["nq_ret"], lags=6)
    short_reg = hac_regress(short_R, joined["nq_ret"], lags=6)
    print("[long-only regression]", json.dumps(long_reg, indent=2), flush=True)
    print("[short-only regression]", json.dumps(short_reg, indent=2), flush=True)

    # ---- Tag each session by 60-day rolling NQ return regime ----
    d["roll60_ret"] = d["close"].pct_change(60)
    d["regime"] = np.where(
        d["roll60_ret"] > 0.05, "up",
        np.where(d["roll60_ret"] < -0.05, "down", "chop"),
    )
    # Avoid look-ahead: regime tag valid at day t based on close at t-1
    d["regime_lag"] = d["regime"].shift(1)

    # ---- Sub-period splits with regime breakdown ----
    splits = {
        "full_2010_2026": ("2010-06-06", "2026-05-31"),
        "pre_2015": ("2010-06-06", "2014-12-31"),
        "2015_2019": ("2015-01-01", "2019-12-31"),
        "2020_2022": ("2020-01-01", "2022-12-31"),
        "2023_2026": ("2023-01-01", "2026-05-31"),
    }

    regime_tbl_rows = []
    for label, (a, b) in splits.items():
        sub_tr = tr.loc[a:b].copy()
        sub_tr["regime"] = d["regime_lag"].reindex(sub_tr.index)
        # By regime
        for reg_label in ["up", "chop", "down", "all"]:
            if reg_label == "all":
                grp = sub_tr
            else:
                grp = sub_tr.loc[sub_tr["regime"] == reg_label]
            if len(grp) == 0:
                continue
            mean_R = float(grp["pnl_R"].mean())
            std_R = float(grp["pnl_R"].std(ddof=0))
            n = int(len(grp))
            traded = grp[grp["direction"] != 0]
            n_long = int((traded["direction"] == 1).sum())
            n_short = int((traded["direction"] == -1).sum())
            sum_long = float(traded.loc[traded["direction"] == 1, "pnl_R"].sum())
            sum_short = float(traded.loc[traded["direction"] == -1, "pnl_R"].sum())
            sh = mean_R / std_R * np.sqrt(252) if std_R > 0 else np.nan
            regime_tbl_rows.append(
                {
                    "period": label,
                    "regime": reg_label,
                    "n_sessions": n,
                    "n_trades": int(len(traded)),
                    "n_long": n_long,
                    "n_short": n_short,
                    "sum_R": float(grp["pnl_R"].sum()),
                    "sum_R_long": sum_long,
                    "sum_R_short": sum_short,
                    "mean_R_day": mean_R,
                    "sharpe_R": sh,
                }
            )

    tbl = pd.DataFrame(regime_tbl_rows)
    tbl.to_csv(RES / "s1_regime_table.csv", index=False)
    print(f"[save] s1_regime_table.csv  rows={len(tbl)}", flush=True)
    print(tbl.to_string(index=False), flush=True)

    # Save tagged trades
    out = tr.copy()
    out["regime"] = d["regime_lag"].reindex(out.index)
    out.to_parquet(RES / "s1_regime_tagged.parquet")
    print(f"[save] s1_regime_tagged.parquet  rows={len(out)}", flush=True)

    # Save beta-regression JSON
    out_json = {
        "full_sample": full,
        "long_leg": long_reg,
        "short_leg": short_reg,
    }
    (RES / "s1_beta_regression.json").write_text(json.dumps(out_json, indent=2))
    print(f"[save] s1_beta_regression.json", flush=True)


if __name__ == "__main__":
    main()
