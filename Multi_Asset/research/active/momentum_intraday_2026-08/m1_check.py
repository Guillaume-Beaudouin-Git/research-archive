"""
M1 tie-break resolution for the grid's bracket-exit survivors (gross |t|>2, X2/X4 exits) --
per PREREGISTRATION.md gate 5 / L62. Imports `audit_moteur_bracket_2026-08/m1_resolver.py`
read-only (not rewritten); its `DEEP` constant is monkey-patched to the absolute main-dir path
since this worktree lacks the gitignored `data/deep_history_utc/` cache. Trades are first
session-capped (this study's own construction-B fix) so the tie-break check doesn't inherit
the cross-day-bleed bug, then M1-resolved exactly as the bracket audit does.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(HERE.parents[0] / "mr_intraday_grille_2026-08"))
import engine_lib as EL
from engine import backtest as BT
from engine import stats as S
sys.path.insert(0, str(HERE))
import dataload as DL
import signals as SG

sys.path.insert(0, str(HERE.parents[0] / "audit_moteur_bracket_2026-08"))
import m1_resolver as M1R
M1R.DEEP = MAIN / "data" / "deep_history_utc"  # monkey-patch: worktree has no local cache


def session_cap(df, sig, sl, tp, engine_max_hold, sl_first_on_tie):
    tr = BT.run_backtest_vectorized(df, sig, sl_dist=sl, tp_dist=tp, cost_rt=0.0,
                                    max_hold=engine_max_hold, sl_first_on_tie=sl_first_on_tie)
    if tr.empty:
        return tr
    sess = df["session_date"]
    entry_sess = sess.reindex(tr["entry_time"]).to_numpy()
    exit_sess = sess.reindex(tr["exit_time"]).to_numpy()
    bleed = exit_sess != entry_sess
    if bleed.any():
        last_close = df.groupby("session_date")["close"].last()
        last_time = df.groupby("session_date").apply(lambda g: g.index[-1])
        tr = tr.copy()
        idx = np.where(bleed)[0]
        sdates = entry_sess[idx]
        tr.loc[tr.index[idx], "exit_px"] = last_close.reindex(sdates).to_numpy()
        tr.loc[tr.index[idx], "exit_time"] = last_time.reindex(sdates).to_numpy()
        tr.loc[tr.index[idx], "reason"] = "session_end"
        direction = tr["direction"].to_numpy(float)
        entry_px = tr["entry_px"].to_numpy(float)
        exit_px = tr["exit_px"].to_numpy(float)
        tr["ret_gross"] = direction * (exit_px / entry_px - 1.0)
    return tr


def check_cell(symbol, construction_fn, kwargs, label, bar_minutes=15):
    print(f"=== {label} ({symbol}) ===", flush=True)
    df = DL.load(symbol)
    res = construction_fn(df, bars_per_day=DL.BARS_PER_DAY, symbol=symbol, **kwargs)
    sig, sl, tp, mh = res[0], res[1], res[2], res[3]
    tr_p = session_cap(df, sig, sl, tp, mh, True)
    tr_o = session_cap(df, sig, sl, tp, mh, False)
    n = min(len(tr_p), len(tr_o))
    tr_p, tr_o = tr_p.iloc[:n].reset_index(drop=True), tr_o.iloc[:n].reset_index(drop=True)
    assert np.array_equal(tr_p["entry_time"].to_numpy(), tr_o["entry_time"].to_numpy())
    is_tie = (tr_p["reason"].to_numpy() != tr_o["reason"].to_numpy()) & \
             (tr_p["reason"].to_numpy() != "session_end") & (tr_o["reason"].to_numpy() != "session_end")

    m1_raw = pd.read_csv(M1R.DEEP / f"{symbol}_M1.csv",
                         usecols=["timestamp_utc", "open", "high", "low", "close"],
                         dtype={"open": "float64", "high": "float64", "low": "float64", "close": "float64"})
    m1_raw.index = pd.to_datetime(m1_raw["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    m1_raw = m1_raw.drop(columns=["timestamp_utc"]).sort_index()

    ret_m1, frac_ambig, n_ties, n_lookup = M1R.apply_m1_resolution(tr_p, tr_o, is_tie, m1_raw, bar_minutes)
    ret_p = tr_p["ret_gross"].to_numpy(float)
    unbiased = ret_p.copy()
    tie_idx = np.where(is_tie)[0]
    unbiased[tie_idx] = 0.5 * (tr_p["ret_gross"].to_numpy(float)[tie_idx] + tr_o["ret_gross"].to_numpy(float)[tie_idx])
    _, t_p = S.hac_tstat(ret_p, lags=6)
    _, t_m1 = S.hac_tstat(ret_m1, lags=6)
    _, t_u = S.hac_tstat(unbiased, lags=6)
    row = dict(label=label, symbol=symbol, n_trades=n, n_ties=int(is_tie.sum()),
              frac_tie=float(is_tie.mean()),
              frac_m1_still_ambiguous=(frac_ambig if n_lookup else float("nan")),
              t_pessimistic=t_p, t_m1_resolved=t_m1, t_unbiased_reference=t_u,
              bps_pessimistic=float(ret_p.mean() * 1e4), bps_m1_resolved=float(ret_m1.mean() * 1e4))
    print(f"  n_trades={n} n_ties={row['n_ties']} frac_tie={row['frac_tie']:.4f} "
          f"frac_m1_still_ambiguous={row['frac_m1_still_ambiguous']}")
    print(f"  t_pessimistic={t_p:+.3f}  t_m1_resolved={t_m1:+.3f}  t_unbiased_ref={t_u:+.3f}", flush=True)
    return row


if __name__ == "__main__":
    t0 = time.time()
    rows = []
    for sym in ["USDJPY", "GBPUSD", "EURJPY", "EURGBP"]:
        rows.append(check_cell(sym, SG.construction_b, dict(K=2, exit_type="X4"),
                               f"B_orb_K2_X4_{sym}"))
    rows.append(check_cell("XAGUSD", SG.construction_a,
                           dict(K=2, H="8bars", exit_type="X2"), "A_gao_K2_H8_X2_XAGUSD"))
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "m1_check_results.csv", index=False)
    print(f"\nWrote {len(out)} rows -> m1_check_results.csv ({time.time()-t0:.1f}s total)")
