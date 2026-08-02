"""What Delta p(pass) does a sleeve with NO edge produce?

Without this control the whole ranking is uninterpretable. The combined book is
re-levered to the incumbent's volatility (``normalize_vol=True``), so adding *any*
weakly-correlated series changes the SHAPE of the daily distribution even when it
adds no return: it thins the left tail, and the FTMO daily stop is a barrier on the
left tail of a single day. A zero-mean Gaussian sleeve therefore has a non-zero
expected Delta p(pass), and that number — not zero — is the bar every candidate has
to clear.

Three nulls, increasing in realism:

* ``gauss_zero``   iid normal, zero mean. Pure shape effect, no return, no clustering.
* ``gauss_block``  same but with the book's own block structure imposed, to check the
  bootstrap's mean block length is not doing the work.
* ``flat_filler``  zero-mean, active only on days the book is flat. This is the
  archetype the brief describes — it isolates the calendar-filling channel from the
  return channel.

Each is run over many seeds so the reported band is the null *distribution*, which is
what "minimum detectable effect" has to be measured against.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

WT = Path("<HOME>/Desktop/Algo_claude_marginal")
sys.path.insert(0, str(WT))
warnings.filterwarnings("ignore")

from Portfolio.admission import BarrierConfig, pass_probability_delta  # noqa: E402

HERE = Path(__file__).resolve().parent
CFG = BarrierConfig()
N_PATHS = 2000
N_REP = 20


def run() -> pd.DataFrame:
    d = pd.read_pickle(HERE / "cache" / "panel.pkl")
    book: pd.Series = d["book"]
    idx = book.index
    flat = (book == 0.0).to_numpy()
    rows = []
    for rep in range(N_REP):
        rng = np.random.default_rng(1000 + rep)
        variants = {
            "gauss_zero": rng.standard_normal(len(idx)) * 0.01,
            "gauss_block": np.repeat(rng.standard_normal(len(idx) // 10 + 1) * 0.01, 10)[: len(idx)],
        }
        ff = rng.standard_normal(len(idx)) * 0.01
        ff[~flat] = 0.0
        variants["flat_filler"] = ff
        for nm, arr in variants.items():
            arr = arr - arr.mean()          # enforce exactly zero mean: no edge at all
            cand = pd.Series(arr, index=idx, name=nm)
            out = pass_probability_delta(book.to_frame("book"), cand, cfg=CFG,
                                         scheme="erc", n_paths=N_PATHS, seed=rep,
                                         normalize_vol=True)
            rows.append(dict(variant=nm, rep=rep, d_p=out["delta_p_pass"],
                             d_days=out["delta_median_days"],
                             p_book=out["p_pass_book"]))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    r = run()
    r.to_csv(HERE / "null_control_raw.csv", index=False)
    g = r.groupby("variant").agg(
        d_p_mean=("d_p", "mean"), d_p_sd=("d_p", "std"),
        d_p_p50=("d_p", "median"), d_p_p95=("d_p", lambda x: np.percentile(x, 95)),
        d_days_mean=("d_days", "mean"), n=("d_p", "size"))
    g.to_csv(HERE / "null_control.csv")
    print(g.to_string())
    print("\nNull band (95th pct of the strongest null) is the bar a candidate must clear:")
    print(f"  {g['d_p_p95'].max():+.4f}")
