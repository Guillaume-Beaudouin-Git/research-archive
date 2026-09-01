"""
Orchestrateur : charge trades_<PAIR>[.csv|_placebo.csv], calcule toutes les statistiques
prescrites par PREREGISTRATION.md, ecrit resultats.csv (une ligne par scenario/metrique) et
imprime un resume texte utilise pour rediger RAPPORT.md.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as M  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
WINDOW_PRIMARY = ("2018-01-05", "2024-07-29")
COST_SCENARIOS = {"gross_0bps": 0.0, "eightcap_0.75bps": 0.75, "ftmo_2.48bps": 2.48}
SWAP_HAIRCUTS = {"swap_brut": 1.0, "swap_realiste_0.85": 0.85}

rows = []


def summarize(tag: str, df: pd.DataFrame, pnl_col: str, periods_per_year: float):
    r = df[pnl_col].values
    n = len(r)
    sharpe_correct = M.sharpe_annualized(r, periods_per_year)
    sharpe_wrong_252 = M.sharpe_annualized(r, 252)
    mean_r, hac_t, n_hac = M.hac_tstat(r)
    skew = float(pd.Series(r).skew()) if n > 2 else np.nan
    kurt = float(pd.Series(r).kurt()) + 3.0 if n > 2 else np.nan
    sr_per = r.mean() / r.std(ddof=1) if n > 1 and r.std(ddof=1) > 0 else np.nan
    dsr_out = M.deflated_sharpe(sr_per, n, skew, kurt, n_trials=2) if np.isfinite(sr_per) else {}
    rows.append(dict(
        scenario=tag, n_trades=n, trades_per_year=periods_per_year,
        sharpe_correct_sqrt_tpy=sharpe_correct, sharpe_wrong_sqrt252=sharpe_wrong_252,
        inflation_factor=(sharpe_wrong_252 / sharpe_correct) if sharpe_correct not in (0, np.nan)
        and np.isfinite(sharpe_correct) else np.nan,
        mean_pnl_per_trade=mean_r, hac_t=hac_t, skew=skew, kurtosis=kurt,
        psr=dsr_out.get("psr"), dsr_n2=dsr_out.get("dsr"),
        cum_pnl=float(r.sum()), win_rate=float((r > 0).mean()),
    ))


def years_span(df):
    return max((df["exit_time"].max() - df["exit_time"].min()).days / 365.25, 0.01)


def main():
    rf = M.load_rf()
    trades_all = M.load_all_trades()
    trades_placebo = pd.concat(
        [pd.read_csv(BASE / f"trades_{p}_placebo.csv", parse_dates=["entry_time", "exit_time"])
         for p in M.PAIRS], ignore_index=True).sort_values("exit_time").reset_index(drop=True)

    for window_name, (lo, hi) in [("primary_2018-2024", WINDOW_PRIMARY),
                                   ("extended_full_history", (None, None))]:
        d = trades_all
        if lo is not None:
            d = d[(d["entry_time"] >= lo) & (d["exit_time"] <= hi)]
        if len(d) < 10:
            continue
        tpy = len(d) / years_span(d)

        for cost_name, cost_bps in COST_SCENARIOS.items():
            for swap_name, haircut in SWAP_HAIRCUTS.items():
                dd = M.add_pnl(d, rf, cost_bps, haircut)
                summarize(f"{window_name}|{cost_name}|{swap_name}|GROSS", dd, "pnl_gross", tpy)
                summarize(f"{window_name}|{cost_name}|{swap_name}|NET", dd, "pnl_net", tpy)
                summarize(f"{window_name}|{cost_name}|{swap_name}|NET_SWAP", dd, "pnl_net_swap", tpy)
                summarize(f"{window_name}|{cost_name}|{swap_name}|NET_SWAP_EXCESS_RF", dd,
                          "pnl_net_swap_excess", tpy)

        # two-sided, main scenario (FTMO cost, realistic swap)
        dd_main = M.add_pnl(d, rf, COST_SCENARIOS["ftmo_2.48bps"],
                             SWAP_HAIRCUTS["swap_realiste_0.85"])
        ts = M.two_sided(dd_main, "pnl_net_swap_excess", tpy)
        ts.to_csv(BASE / f"two_sided_{window_name}.csv", index=False)

        # regime split
        rs = M.regime_split(dd_main, "pnl_net_swap_excess")
        rs.to_csv(BASE / f"regime_split_{window_name}.csv", index=False)

        # walk-forward 5 folds
        wf = M.walk_forward_folds(dd_main, "pnl_net_swap_excess", n_folds=5)
        wf.to_csv(BASE / f"walkforward_{window_name}.csv", index=False)

        # block bootstrap CI on main scenario, block size ~ mean hold days worth of trades
        block = max(int(dd_main["hold_days"].mean() / (365.25 / tpy)), 5) if tpy > 0 else 10
        lo_b, hi_b, _ = M.block_bootstrap_sharpe(dd_main["pnl_net_swap_excess"].values, tpy,
                                                  block_size=min(block, len(dd_main) // 4 or 1))
        rows.append(dict(scenario=f"{window_name}|bootstrap_CI95_sharpe", n_trades=len(dd_main),
                          trades_per_year=tpy, sharpe_correct_sqrt_tpy=np.nan,
                          sharpe_wrong_sqrt252=np.nan, inflation_factor=np.nan,
                          mean_pnl_per_trade=np.nan, hac_t=np.nan, skew=np.nan, kurtosis=np.nan,
                          psr=lo_b, dsr_n2=hi_b, cum_pnl=np.nan, win_rate=np.nan))

        # placebo comparison, same window
        dp = trades_placebo
        if lo is not None:
            dp = dp[(dp["entry_time"] >= lo) & (dp["exit_time"] <= hi)]
        if len(dp) >= 10:
            tpy_p = len(dp) / years_span(dp)
            dp_main = M.add_pnl(dp, rf, COST_SCENARIOS["ftmo_2.48bps"],
                                 SWAP_HAIRCUTS["swap_realiste_0.85"])
            summarize(f"{window_name}|PLACEBO_random_direction|ftmo_2.48bps|swap_realiste_0.85",
                      dp_main, "pnl_net_swap_excess", tpy_p)

        # decomposition: sum of gross price pnl vs sum of swap pnl vs cost, main scenario
        rows.append(dict(
            scenario=f"{window_name}|DECOMPOSITION_sums", n_trades=len(dd_main),
            trades_per_year=tpy, sharpe_correct_sqrt_tpy=np.nan, sharpe_wrong_sqrt252=np.nan,
            inflation_factor=np.nan,
            mean_pnl_per_trade=dd_main["pnl_gross"].sum(), hac_t=dd_main["pnl_swap_only"].sum(),
            skew=dd_main["pnl_cost_only"].sum(), kurtosis=dd_main["rf_drag"].sum(),
            psr=np.nan, dsr_n2=np.nan, cum_pnl=dd_main["pnl_net_swap_excess"].sum(),
            win_rate=np.nan,
        ))

    out = pd.DataFrame(rows)
    out.to_csv(BASE / "resultats.csv", index=False)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    print(out.to_string())


if __name__ == "__main__":
    main()
