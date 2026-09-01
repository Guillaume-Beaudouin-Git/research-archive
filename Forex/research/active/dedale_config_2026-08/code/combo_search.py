"""Exhaustive 2-filter (and a few hand-picked 3-filter) combos, ranked by distance to the
author's declared metadata (see search_engine.TARGET / distance()). Writes incrementally."""
import itertools
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import search_engine as se  # noqa: E402
import dedale_engine as de  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "combo_search_results.csv"

FILTERS = [(tf, k) for tf in range(5) for k in ["CROSS", "TREND", "ANGLE"]]


def name_of(fset):
    return "+".join(f"TDI_TIMEFRAME{tf}_{k}" for tf, k in sorted(fset))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "pairs"
    tf_cache = {}
    # warm the tf_cache once for all 7 pairs up front (shared across all combos)
    for p in de.PAIRS:
        m1 = se.load_m1_close(p)
        h1 = de.load_h1(p)
        import tdi
        tf_cache[p] = tdi.build_all_tf_conditions(m1, h1.index)
        print(f"tf_cache warmed: {p}", flush=True)

    rows = []
    if which == "pairs":
        combos = list(itertools.combinations(FILTERS, 2))
    elif which == "triples_top":
        # anchored on the best-distance filters observed in the single + pairwise sweeps
        # (D1/H4/H1 CROSS, D1 ANGLE/TREND, M30 TREND+CROSS, M15 CROSS)
        anchors = [(4, "CROSS"), (4, "ANGLE"), (4, "TREND"), (3, "CROSS"), (2, "CROSS"),
                   (1, "CROSS"), (1, "TREND"), (0, "CROSS")]
        combos = list(itertools.combinations(anchors, 3))
    else:
        raise ValueError(which)

    for i, combo in enumerate(combos):
        fset = set(combo)
        summ, _ = se.run_config(fset, tf_cache=tf_cache, verbose=False)
        summ["config"] = name_of(fset)
        rows.append(summ)
        if i % 10 == 0 or i == len(combos) - 1:
            pd.DataFrame(rows).to_csv(OUT, index=False)
            print(f"[{i+1}/{len(combos)}] {name_of(fset)} n={summ['n']} "
                  f"tpy={summ['trades_per_pair_year']:.2f} wr={summ['win_rate']:.1f} "
                  f"hold={summ['hold_days']:.1f} dist={summ['dist']:.2f}", flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print("done", flush=True)
