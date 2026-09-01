"""Walk-forward (5 folds, expanding) pour les variantes qui declenchent le
kill-rule (retest) ou qui en approchent (cal_Fri_only), comme demande par
PREREGISTRATION.md §7 -- ne PAS gaspiller 5x37 folds sur des cellules mortes."""
import sys
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from simulate import simulate_engine, load_sessions
from stats_utils import hac_tstat_fast

OUTDIR = "<HOME>/Desktop/Algo_claude_orbvar/Multi_Asset/research/active/orb_variants_2026-08"


def wf_expanding(df, n_folds=5):
    df = df.sort_values("date").reset_index(drop=True)
    n = len(df)
    fold_size = n // n_folds
    out = []
    for f in range(n_folds):
        start = f * fold_size
        end = n if f == n_folds - 1 else (f + 1) * fold_size
        sub = df.iloc[start:end]
        m, t, nn = hac_tstat_fast(sub["r_net"].values)
        out.append(dict(fold=f + 1, n=nn, date_min=sub["date"].min(), date_max=sub["date"].max(),
                         mean=m, t=t, pct_positive_days=(sub["r_net"] > 0).mean()))
    return pd.DataFrame(out)


def main():
    sess = load_sessions()
    anchor_df = simulate_engine(sess, "RTH", 30, "touch", 0.0, "retest", "close_RTH")
    print("=== retest (confirm axis) : walk-forward 5 folds expanding ===")
    wf = wf_expanding(anchor_df)
    print(wf.to_string())
    wf.to_csv(f"{OUTDIR}/code/wf_retest.csv", index=False)

    base = simulate_engine(sess, "RTH", 30, "touch", 0.0, "immediate", "close_RTH")
    base["date_ts"] = pd.to_datetime(base["date"])
    base["weekday"] = base["date_ts"].dt.day_name()
    fri = base[base["weekday"] == "Friday"]
    print("\n=== cal_Fri_only (near-miss) : walk-forward 5 folds expanding ===")
    wf_fri = wf_expanding(fri)
    print(wf_fri.to_string())
    wf_fri.to_csv(f"{OUTDIR}/code/wf_fri.csv", index=False)


if __name__ == "__main__":
    main()
