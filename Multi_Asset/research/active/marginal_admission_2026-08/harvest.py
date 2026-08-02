"""Harvest every recoverable daily return series and the reference book.

The hard constraint of this study is stated once here: **no series, no marginal test**.
An edge with a t-stat in a report but no saved return stream cannot be joined to the
book calendar, so it cannot produce a rho, a Delta SR or a Delta p(pass). Counting
what is lost that way is part of the deliverable.

Everything is read from the MAIN working directory by absolute path, read-only: the
data caches are gitignored and therefore absent from a fresh worktree.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

# ── the reference book ───────────────────────────────────────────────────────
# The DEPLOYED book, not a theoretical one: gold weight 0, J1 off, ORB challenge-off,
# so only the overnight sleeve trades, at the live vm=14. Built by the L54 session's
# build_book.py on the audited cleanroom engine.
BOOK_PATH = MAIN / "Multi_Asset/research/active/regime_overlay_ftmo_2026-07/cache/book_mono.parquet"

# ── candidate manifest ───────────────────────────────────────────────────────
# (name, path, column, cost_status, family, note)
#   cost_status: "net" = costs and swap already deducted by the producing study
#                "gross" = costs NOT deducted -> the Delta is an upper bound
P = str  # readability


def _m(p: str) -> Path:
    return MAIN / p


MANIFEST: list[dict] = []


def add(name, path, col, cost, family, note=""):
    MANIFEST.append(dict(name=name, path=path, col=col, cost=cost, family=family, note=note))


# --- FTMO container sleeves (net of measured RT cost + asymmetric swap) -------
_p1c = "data/ftmo_portfolio/cache/phase1c_sleeves.parquet"
add("gold_trend_cfd", _p1c, "gold", "net", "trend", "XAUUSD TSMOM, carry-adj")
add("energy_LO_cfd", _p1c, "energy_LO", "net", "trend", "UKOIL+USOIL long-only trend")
add("J1_usdjpy_LO", _p1c, "J1", "net", "trend", "USDJPY 12-1 long-only, VT10%")
add("crypto_trend_cfd", _p1c, "crypto", "net", "trend", "BTC+ETH CFD trend")
add("metals_pair_cfd", _p1c, "metals_pair", "net", "trend", "XAU+XAG trend")

_p1 = "data/ftmo_portfolio/cache/phase1_sleeve_returns.parquet"
add("trend_replica", _p1, "trend_replica", "net", "trend", "")
add("trend_replica_carryadj", _p1, "trend_replica_carryadj", "net", "trend", "")
add("trend_full", _p1, "trend_full", "net", "trend", "")
add("trend_full_carryadj", _p1, "trend_full_carryadj", "net", "trend", "")

# --- overnight-drift family, REBUILT un-winsorised (E002/E003/E004/E005) ------
_ovn = "Multi_Asset/research/active/marginal_admission_2026-08/cache/overnight_raw_sleeves.parquet"
add("ovn_GOLD_fut", _ovn, "GOLD", "net", "overnight", "un-winsorised, 0.66 bps RT MGC")
add("ovn_SILVER_fut", _ovn, "SILVER", "net", "overnight", "un-winsorised, 1.15 bps RT SIL")
add("ovn_WTI_fut", _ovn, "WTI", "net", "overnight", "un-winsorised, 3.67 bps RT MCL")
add("ovn_SOYBEAN_fut", _ovn, "SOYBEAN", "net", "overnight", "un-winsorised, N=313 only")

# --- the same three, AS PUBLISHED (winsorised) -> the trap, kept for contrast --
_ovnw = "Multi_Asset/research/active/overnight_futures_2026-07/results/step3_sleeve_series.csv"
add("ovn_GOLD_winsorised", _ovnw, "GOLD", "gross", "overnight", "WINSORISED 0.5/99.5 in constructor")

# --- personal-book validated sleeves (growth_engine audit) --------------------
_ge = "Multi_Asset/research/active/growth_engine_2026-07/audit_growth_returns.parquet"
add("B1_month_end_bonds", _ge, "bonds", "net", "flow", "E001 dash-for-cash, the deployed IBKR sleeve")
add("growth_trend", _ge, "trend", "net", "trend", "personal-book trend leg")

# --- trend_research (J1/G1 verification session) ------------------------------
add("J1_trendres", "data/trend_research/g1_sleeves.csv", "J1", "net", "trend", "")
add("TSMOM_unfilt", "data/trend_research/g1_sleeves.csv", "TSMOM_unfilt", "net", "trend", "")
add("TSMOM_long_only", "data/trend_research/g1_sleeves.csv", "TSMOM_long_only", "net", "trend", "")
add("G1_gold_orig", "data/trend_research/g2_swap_grid.csv", "G1_baseline_orig", "net", "trend", "")
add("G1_credit_shorts", "data/trend_research/g2_swap_grid.csv", "G1_credit_shorts_mul1", "net", "trend", "")
add("book_10pct_vol", "data/trend_research/g3_book_book.csv", "book_10pct_vol", "net", "trend", "")
add("btc_proxy_A", "data/trend_research/g5_book_vs_A.csv", "btc_proxy_A", "net", "crypto", "Strategy A proxy")

# --- skew_research: basic trend setups + cowork sleeves -----------------------
_sbt = "data/skew_research/session_basic_trend/setup_daily_series.csv"
add("EMA_50_200", _sbt, "EMA 50/200", "net", "trend", "")
add("Donchian_55", _sbt, "Donchian 55", "net", "trend", "")
add("Momentum_MA200", _sbt, "Momentum MA200", "net", "trend", "")
add("MACD_cross", _sbt, "MACD cross", "net", "trend", "")
add("Pullback_uptrend", _sbt, "Pullback-in-uptrend", "net", "reversion", "")
add("commodity_seasonality", "data/skew_research/session_basic_trend/commodity_seasonality_oos.csv",
    "0", "net", "seasonal", "OOS commodity seasonality book")
_cw = "data/skew_research/session_cowork/phase1_series_all.csv"
add("Donchian_breakout", _cw, "Donchian-breakout", "net", "trend", "")
add("XS_momentum", _cw, "XS-momentum", "net", "momentum", "M049")
add("Long_vol_VXX", _cw, "Long-vol(VXX)", "net", "vol", "")

# --- merge/portfolio study (TSMOM + FOMC + VXX) ------------------------------
_mg = "data/skew_research/MERGE_portfolio_returns.csv"
add("P2_TSMOM_FOMC", _mg, "P2_TSMOM+FOMC", "net", "mixed", "")
add("P4_triple_invol", _mg, "P4_triple_invol", "net", "mixed", "")

# --- survivors book / ftmo_research TSMOM ------------------------------------
_sv = "PropFirms/ftmo/program_2026-06/ftmo_survivors_book/results/"
add("tsmom_swapfree_full", _sv + "tsmom_swapfree_full.csv", "ret", "gross", "trend", "swap NOT charged")
add("tsmom_swapnet_nocrypto", _sv + "tsmom_swapnet_nocrypto.csv", "ret", "net", "trend", "")
add("survivors_final_book", _sv + "final_book_daily.csv", "ret", "net", "mixed", "RH+TSMOM book")
add("tsmom_chosen", "PropFirms/ftmo/program_2026-06/ftmo_research/tsmom/chosen_returns.csv",
    "0", "gross", "trend", "swap-free variant")

# --- FTMO paper-edge replications (all net) ----------------------------------
_pe = "PropFirms/ftmo/program_2026-06/ftmo_paper_edges/results/"
add("paper_im_book", _pe + "im_book.parquet", "net", "net", "momentum", "intraday momentum book")
add("paper_rev_book", _pe + "rev_book.parquet", "net", "net", "reversion", "")
add("paper_fomc_long_even", _pe + "fomc_long-even.parquet", "net", "net", "event", "M002 family")
add("paper_overnight_fade", _pe + "overnight_fade_book.parquet", "net", "net", "reversion", "")

# --- top10 rigorous funnel: the 20 tests whose daily P&L was saved -----------
_t10 = "PropFirms/ftmo/program_2026-06/top10_test/results/"
for tid in ["ang_006", "ang_017", "ang_018", "ang_019", "ang_024", "ang_024_flip",
            "ang_025", "ang_025_flip", "ang_025_flip_mod2", "ang_025_flip_mod3",
            "ang_047", "ang_047_mod1", "ang_047_mod2", "ang_047_mod3", "ang_048",
            "lit_012", "lit_013", "lit_020", "lit_021", "lit_048"]:
    add(f"top10_{tid}", f"{_t10}daily_pnl_{tid}.csv", "pnl_frac", "net", "funnel",
        "164-test funnel; gold legs over-costed 1.9x (COST_AUDIT s3)")

# --- decorrelated-sleeves iteration 2 ----------------------------------------
_ds = "Multi_Asset/research/active/decorrelated_sleeves_2026-07/iteration_2/"
add("dec_H1_goldsilver", _ds + "piste_A/H1_goldsilver_returns.csv", "ret", "net", "statarb", "")
add("dec_H2_resid_port", _ds + "piste_A/H2_resid_portfolio_returns.csv", "ret", "net", "statarb", "")
add("dec_pisteC_best", _ds + "piste_C/best_daily_returns.csv", "ret", "net", "reversion", "M007")

# --- cs macro momentum (M001, closed 07-29) ----------------------------------
_cs = "yt_strategy_replications/cs_macro_momentum_ftmo/results/variant_series.parquet"
add("cs_macro_V1_panel", _cs, "V1_panel", "net", "momentum", "M001 best variant")
add("cs_macro_V0_anchor", _cs, "V0_anchor", "net", "momentum", "")

# --- misc single sleeves ------------------------------------------------------
add("voie_b_ftmo", "Futures/research/active/voie_b_ftmo/results/ftmo_voie_b_returns.csv",
    "ret", "net", "unknown", "underlying UNCONFIRMED per CLAUDE.md")
add("double7_cfd", "data/double7_connors/eq_cfd_sleeves.csv", "0", "net", "reversion", "Connors Double 7")
add("orb_e7_R15", "data/ftmo_portfolio/cache/orb_e7_R15.parquet", "R", "net", "orb",
    "R multiples; scale-invariant under ERC")
add("btc_sleeve_it2", "data/ftmo_portfolio/cache/btc_sleeve_it2.parquet", "r", "net", "crypto", "")
add("s060_oxford", "Multi_Asset/research/archived/oxfordstrat_109_audit/results/s060_deepdive_daily.csv",
    "strat", "net", "oxford", "S060 deep-dive")
add("s076_mtm_fx", "PropFirms/ftmo/program_2026-06/s076_replication/results/mtm_fx.csv",
    "ret", "net", "oxford", "S076 Ross Hook")
_3s = "PropFirms/ftmo/program_2026-06/ftmo_3strats_audit_2026-06/results/"
add("prodige_s1", _3s + "s1_daily.parquet", "pnl_R", "net", "orb", "")
add("prodige_s3_net", _3s + "s3_reproduction.parquet", "s3_net_x1", "net", "momentum", "")
# --- ledgers converted to daily by build_extra.py (E012 / E013 / E020) --------
_ex = "Multi_Asset/research/active/marginal_admission_2026-08/cache/extra_sleeves.parquet"
add("gapA_S035_point", _ex, "gapA_S035_point", "net", "gap", "E012, pre-registered spec, N=3438")
add("gapB_S036_point", _ex, "gapB_S036_point", "net", "gap", "E013")
add("gapA_S035_best", _ex, "gapA_S035_best", "net", "gap", "E012 best-of-grid, selection-biased")
add("auction_ZN_post", _ex, "auction_ZN_post", "net", "flow", "E020, never tested pre-2026-07")


# ── loading ──────────────────────────────────────────────────────────────────
def _read(path: str) -> pd.DataFrame:
    # Series rebuilt by this study live in the worktree; everything else is read
    # from the main working directory (its data caches are gitignored).
    f = _m(path)
    local = HERE.parent.parent.parent.parent / path
    if not f.exists() and local.exists():
        f = local
    d = pd.read_parquet(f) if f.suffix == ".parquet" else pd.read_csv(f, index_col=0)
    idx = pd.DatetimeIndex(pd.to_datetime(d.index))
    if idx.tz is not None:          # some studies persist tz-aware stamps
        idx = idx.tz_convert("UTC").tz_localize(None)
    d.index = idx.normalize()
    return d[~d.index.duplicated(keep="first")].sort_index()


def load_book() -> pd.Series:
    b = pd.read_parquet(BOOK_PATH)
    s = b["ret"].astype(float)
    s.index = pd.DatetimeIndex(s.index).normalize()
    return s.rename("book")


def _coerce_returns(s: pd.Series) -> tuple[pd.Series, str]:
    """Guard against an equity *level* being mistaken for a return stream.

    A level is strictly positive and far from zero; differencing it silently would
    be invisible in a Sharpe but catastrophic in a barrier simulation, which reads
    the numbers as daily percentage moves. Caught in this study on
    ``double7_connors/eq_cfd_sleeves.csv`` (an account balance in USD).
    """
    if float(s.min()) > 0.0 and float(s.mean()) > 0.5:
        return s.pct_change().dropna(), "level->pct_change"
    return s, ""


def load_candidates() -> tuple[dict[str, pd.Series], list[dict]]:
    series, meta = {}, []
    for m in MANIFEST:
        try:
            d = _read(m["path"])
            s = d[m["col"]].astype(float).dropna()
        except Exception as e:  # noqa: BLE001
            meta.append({**m, "status": f"LOAD_FAIL: {type(e).__name__}"})
            continue
        s, transform = _coerce_returns(s)
        if len(s) < 200:
            meta.append({**m, "status": f"TOO_SHORT n={len(s)}"})
            continue
        sr = float(s.mean() / s.std() * np.sqrt(252)) if s.std() > 0 else np.nan
        # L21: no daily sleeve in any legitimate category exceeds ~4 annualised.
        if not np.isfinite(sr) or abs(sr) > 6.0:
            meta.append({**m, "status": f"IMPLAUSIBLE_SR={sr:.1f}", "n_raw": len(s)})
            continue
        series[m["name"]] = s.rename(m["name"])
        meta.append({**m, "status": "OK", "n_raw": len(s), "sr_raw": sr,
                     "transform": transform,
                     "start": str(s.index.min().date()), "end": str(s.index.max().date())})
    return series, meta


# ── diagnostics ──────────────────────────────────────────────────────────────
def clipping_signature(s: pd.Series) -> dict:
    """Detect a winsorised series: clipping piles observations on the extremes.

    A continuous P&L stream has a unique min and a unique max. Repeated extreme
    values, or a max/sd ratio far below what the kurtosis implies, are the
    fingerprint of a clip applied inside the constructor.
    """
    x = s[s != 0.0]
    if len(x) < 50:
        return {"clip_flag": False, "n_at_max": 0, "n_at_min": 0, "tail_ratio": np.nan}
    n_max = int((x == x.max()).sum())
    n_min = int((x == x.min()).sum())
    sd = float(x.std(ddof=1))
    tail = float(max(abs(x.max()), abs(x.min())) / sd) if sd > 0 else np.nan
    return {"clip_flag": bool(n_max > 1 or n_min > 1), "n_at_max": n_max,
            "n_at_min": n_min, "tail_ratio": tail}


def beta_r2(cand: pd.Series, factors: pd.DataFrame) -> dict:
    """L38 orthogonality: R^2 of the candidate on vol-targeted buy-and-holds.

    Reported per factor rather than jointly, because the registry threshold
    ("R2 > 30% => not orthogonal") is stated against a single primary asset.
    """
    out = {}
    for c in factors.columns:
        j = pd.concat([cand.rename("y"), factors[c].rename("x")], axis=1).dropna()
        if len(j) < 100 or j["x"].std() == 0 or j["y"].std() == 0:
            out[f"r2_{c}"] = np.nan
            continue
        out[f"r2_{c}"] = float(np.corrcoef(j["y"], j["x"])[0, 1] ** 2)
    return out


def calendar_overlap(book: pd.Series, cand: pd.Series) -> dict:
    """Fraction of the candidate's ACTIVE days that land on days the book is FLAT.

    This is the variable the brief expects to explain Delta p(pass): a sleeve that
    trades when the book is idle buys calendar the book cannot buy for itself.
    """
    j = pd.concat([book.rename("b"), cand.rename("c")], axis=1).dropna()
    act = j[j["c"] != 0.0]
    if len(act) == 0:
        return {"cand_active_days": 0, "fill_rate": np.nan, "book_flat_frac": np.nan}
    return {
        "cand_active_days": int(len(act)),
        "fill_rate": float((act["b"] == 0.0).mean()),
        "book_flat_frac": float((j["b"] == 0.0).mean()),
    }


def build_factors() -> pd.DataFrame:
    """Vol-targeted long buy-and-holds used as the L38 beta yardsticks."""
    px = pd.read_parquet(_m("data/ftmo_portfolio/cache/panel_rets.parquet"))
    px.index = pd.DatetimeIndex(px.index).normalize()
    out = {}
    for c in ["US500", "XAUUSD", "USDJPY"]:
        r = px[c].dropna()
        rv = r.rolling(63).std().shift(1).clip(lower=1e-5)
        out[f"BH_{c}"] = (0.10 / np.sqrt(252) / rv * r).dropna()
    return pd.DataFrame(out)


if __name__ == "__main__":
    CACHE.mkdir(exist_ok=True)
    book = load_book()
    series, meta = load_candidates()
    print(f"book: n={len(book)} {book.index.min().date()} -> {book.index.max().date()} "
          f"flat={(book == 0).mean():.3f} "
          f"SR={book.mean() / book.std() * np.sqrt(252):.3f} "
          f"annvol={book.std() * np.sqrt(252):.3f}")
    md = pd.DataFrame(meta)
    print(md["status"].value_counts().to_string())
    ok = md[md.status == "OK"]
    print(f"\nloaded {len(ok)} candidate series")
    pd.to_pickle({"book": book, "series": series}, CACHE / "panel.pkl")
    md.to_csv(HERE / "harvest_manifest.csv", index=False)
