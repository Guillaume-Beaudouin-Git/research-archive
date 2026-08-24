"""Block-bootstrap 90% CI on headline standalone p_funded (pre-registered for headlines)."""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asia_inject as AI
import asia_series as ASER
import asia_fp as FP
V, C22 = AI.V, AI.C22

M = AI.load_asia_stack(spread_bps=1.5)
dates = M["dates_idx"]
a = ASER.build(1.5)
net = ASER.align_to_book(a["net_simple"], dates)
low = ASER.align_to_book(a["low_frac"], dates)
traded = (net != 0)
starts = np.concatenate([V.starts(M, lo, hi, C22.COHORT_STEP) for _, lo, hi in C22.WINDOWS])


def block_ci(funded, block=12, nboot=2000, seed=0):
    rng = np.random.default_rng(seed)
    n = len(funded)
    nb = int(np.ceil(n / block))
    means = np.empty(nboot)
    for b in range(nboot):
        st = rng.integers(0, n, size=nb)
        idx = np.concatenate([np.arange(s, s + block) % n for s in st])[:n]
        means[b] = funded[idx].mean()
    return float(np.percentile(means, 5)), float(np.percentile(means, 95))


res = {}
for tag, K in [("V0_K3", 3.0), ("V0_K4", 4.0)]:
    r = FP.cohort_run(net * K, low * K, traded, dates, starts)
    lo, hi = block_ci(r["funded_arr"].astype(float))
    res[tag] = dict(p_funded=round(r["p_funded"], 4), ci90=[round(lo, 4), round(hi, 4)],
                    p_bust=round(r["p_bust_per_attempt"], 4))
    print(f"{tag}: p_funded {r['p_funded']*100:.1f}%  CI90 [{lo*100:.1f}, {hi*100:.1f}]  "
          f"bust {r['p_bust_per_attempt']*100:.1f}%")
(HERE.parent / "results" / "q2_ci.json").write_text(json.dumps(res, indent=2))
