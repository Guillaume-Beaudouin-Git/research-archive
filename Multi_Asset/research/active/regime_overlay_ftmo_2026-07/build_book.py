"""Reconstruct the DEPLOYED (mono) FTMO book as a constant-risk daily return series.

Read-only reuse of the audited cleanroom engine
(``data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py``): its accounting
primitives are imported and never modified. The FTMO barriers are NOT applied here —
they are applied downstream by ``Portfolio/admission/barrier.py``.

Deployed book = MONO: gold weight 0, J1 off, ORB challenge-off, so only the overnight
sleeve trades (US100 22:05->15:30, GER40 17:35->09:00, Monday/Tuesday only).

Equity is renormalised to INIT at every day's close, which pins taper=glide=pace=1 and
yields the book's return stream at constant deployed gross leverage.

An arbitrary per-day exposure multiplier (the regime overlay) can be injected through
``vm_series``: it multiplies ``vm`` inside the engine's own sizing function, i.e. exactly
the live semantics of "trade smaller today".
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
ENGINE_PATH = REPO / "data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def load_engine():
    spec = importlib.util.spec_from_file_location("cleanroom_engine", ENGINE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cleanroom_engine"] = mod
    spec.loader.exec_module(mod)
    return mod


E = load_engine()

# Live Swing account config, MONO book. Mirrors cleanroom CFG_V2 with the sleeves that
# are actually switched off in production set to zero.
CFG_MONO = dict(
    vm=14.0,
    on_w=0.6,
    target=0.10,           # only feeds the glide test; equity is pinned at INIT so glide=1
    orb_risk=0.0,          # ORB is challenge-OFF and is a day-counter, not P&L
    breaker=0.30,
    taper=0.02,
    glide=0.5,
    ab_buf=0.02,
    ab_days=5,
    margin_cap=0.60,
    mrate=E.MRATE_SWING,   # live Swing margin rates (1:15 / USDJPY 1:30)
    quantize=True,
    brk_mode="daily",      # EA v2.4 deployed 2026-07-20
    brk_needs_pos=True,
    # no "pace"/"max_cal" keys -> pace multiplier is identically 1
)


def build_market():
    return E.load_market()


def mono_signals(dates: pd.DatetimeIndex):
    """WT identically zero (gold + J1 off); ON = Monday/Tuesday."""
    WT = np.zeros((len(dates), 2), dtype=float)
    ON = np.zeros(len(dates), dtype=float)
    ON[np.isin(dates.dayofweek, [0, 1])] = 1.0
    return WT, ON


def run_book(M, WT, ON, cfg, vm_series=None) -> pd.DataFrame:
    """Constant-risk daily return series of the book. No barriers.

    Args:
        vm_series: per-day multiplier on ``vm`` (the regime overlay). None = 1.0.

    Returns:
        DataFrame indexed by engine date with columns ``ret`` (daily return on a
        constant 10k equity), ``traded`` (any position opened that day), ``expo``
        (the applied exposure multiplier).
    """
    n = M["n"]
    mult = np.ones(n) if vm_series is None else np.asarray(vm_series, dtype=float)
    if mult.shape != (n,):
        raise ValueError("vm_series must have one entry per engine day")

    bal = E.INIT
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    rets = np.zeros(n)
    traded = np.zeros(n, dtype=bool)

    for i in range(n):
        px_day, bounds = M["days"][i]
        T = len(px_day)
        cuts = [0] + list(bounds) + [T]
        opened = False
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            seg = px_day[a:b]
            if len(seg) == 0:
                continue
            tgt, did_open = E._target_for_segment(
                s, i, M, WT, ON, cfg, bal, pos, avg, seg[0], 0, cfg["vm"]
            )
            if tgt is not None:
                # Regime overlay: multiplier on the NEWLY POSTED risk, applied AFTER the
                # 60% margin cap so the realised notional really is e_t x baseline (a
                # pre-cap multiplier would be partly absorbed by the cap, which binds at
                # full size). Legs already held are untouched: segments 1 and 2 are pure
                # closes, and re-scaling a held leg would be a liquidation the live EA
                # does not perform.
                if mult[i] != 1.0 and s in (3, 4) and ON[i] > 0:
                    leg = 3 if s == 3 else 2
                    tgt = tgt.copy()
                    tgt[leg] *= mult[i]
                    if cfg.get("quantize", True):
                        step = E.LOT_UNITS[leg] * seg[0][leg] * E.VSTEP
                        if np.isfinite(step) and step > 0:
                            tgt[leg] = np.round(tgt[leg] / step) * step
                bal = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
                opened = opened or did_open
        # end of day: swaps on held notional (measured asymmetric FTMO panels)
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        eq_close = bal + E._mtm(pos, avg, px_day[-1])
        rets[i] = eq_close / E.INIT - 1.0
        traded[i] = opened
        # renormalise to constant risk: scale balance and positions, keep avg entry
        f = E.INIT / eq_close
        bal = E.INIT
        pos = pos * f

    return pd.DataFrame(
        {"ret": rets, "traded": traded, "expo": mult}, index=pd.DatetimeIndex(M["dates"])
    )


def max_drawdown(r: pd.Series) -> float:
    eq = (1.0 + r).cumprod()
    return float((eq / eq.cummax() - 1.0).min())


def summarize(r: pd.Series) -> dict:
    ann = np.sqrt(252.0)
    mu = float(r.mean()) * 252.0
    sd = float(r.std(ddof=1)) * ann
    nz = r[r != 0.0]
    return {
        "n_days": int(len(r)),
        "active_pct": float((r != 0.0).mean()),
        "ann_ret": mu,
        "ann_vol": sd,
        "sharpe": mu / sd if sd > 0 else np.nan,
        "maxDD": max_drawdown(r),
        "worst_day": float(r.min()),
        "best_day": float(r.max()),
        "daily_skew": float(nz.skew()),
        "daily_exkurt": float(nz.kurtosis()),
    }


if __name__ == "__main__":
    CACHE.mkdir(exist_ok=True)
    M = build_market()
    dates = pd.DatetimeIndex(M["dates"])
    WT, ON = mono_signals(dates)
    book = run_book(M, WT, ON, CFG_MONO)
    book.to_parquet(CACHE / "book_mono.parquet")

    r = book["ret"]
    s = summarize(r)
    print("=== DEPLOYED MONO BOOK (constant risk, no barriers) ===")
    print(f"period      : {dates.min().date()} -> {dates.max().date()}")
    for k, v in s.items():
        print(f"{k:12s}: {v:.4f}" if isinstance(v, float) else f"{k:12s}: {v}")

    # sanity: ON days must be Monday/Tuesday only
    active = book.index[book["ret"] != 0.0]
    dow = pd.Series(active.dayofweek).value_counts().sort_index()
    print("\nactive-day weekday histogram (0=Mon):")
    print(dow.to_string())

    # cross-check vs the audited unit-vol sleeve
    sl = pd.read_parquet(REPO / "data/ftmo_portfolio/cache/phase1c_sleeves.parquet")["overnight"]
    j = pd.concat([r.rename("book"), sl.rename("sleeve")], axis=1).dropna()
    j = j[(j["book"] != 0) | (j["sleeve"] != 0)]
    print(f"\ncorr(book, audited overnight sleeve) = {j['book'].corr(j['sleeve']):.4f}  (N={len(j)})")
    print(f"implied leverage vs sleeve           = {j['book'].std() / j['sleeve'].std():.2f}x")
