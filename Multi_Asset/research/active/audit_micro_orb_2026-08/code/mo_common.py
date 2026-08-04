"""Chargement du stack v2.2 depuis un worktree (caches gitignorés -> repo principal).

READ-ONLY sur tout ce qui vient du repo principal. Aucune modification de
data/ftmo_portfolio/** ni de ftmo_live/**.
"""
import sys
from pathlib import Path

MAIN = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve()
WT_ROOT = HERE.parents[5]                       # racine du worktree
V22 = WT_ROOT / "data" / "ftmo_portfolio" / "v22"
CLEAN = WT_ROOT / "data" / "ftmo_portfolio" / "audit_v2_independent" / "cleanroom"
for p in (str(V22), str(CLEAN)):
    if p not in sys.path:
        sys.path.insert(0, p)

import engine as E                              # noqa: E402  cleanroom
E.CACHE = MAIN / "data" / "ftmo_portfolio" / "cache"     # gitignoré -> principal
E.AOUT = MAIN / "data" / "ftmo_portfolio" / "outputs"

import engine_v22 as V                          # noqa: E402
import config_v22 as C22                        # noqa: E402

OUT = HERE.parents[1] / "out"
OUT.mkdir(exist_ok=True)


def load():
    M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    WT_df, ON_df = E.build_signals()
    WT, ON = V.align(M, WT_df, ON_df)
    return M, WT, ON


def dates():
    """Index de dates du stack (pour aligner une série re-pricée)."""
    import engine as _E
    M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    return M["dates_idx"]
