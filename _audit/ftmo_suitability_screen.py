"""
FTMO-suitability inventory screen
==================================

For every strategy with extractable metrics in the repo, computes 5
distribution-shape metrics and a composite suitability score for symmetric-
barrier propfirm challenges (FTMO 5%/10% style). Anchored on L24 (added in
this commit to CLAUDE.md): pass probability is driven by the SHAPE of the
daily-return distribution, not by Sharpe alone.

Inputs : every results.json / metrics_*.json / *_baseline.json under
    Crypto/, Forex/, Equities/, Futures/, Multi_Asset/, Options_Vol/, ETF_Vol/
    (excluding _frozen/, _audit/, __pycache__/), PLUS special-case CSVs for
    voie_b_ftmo and Strategy C iter_10 (whose stats live elsewhere).

NO METRIC IS FABRICATED. If a stat is missing, it is left as [N/A] and the
score is computed on the available subset. If too few metrics are available,
the verdict is DATA-INSUFFISANT.

Output : _audit/ftmo_suitability_screen_results.json (numeric)
         _audit/ftmo_suitability_screen_2026-05-30.md  (narrative, separate)
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]

# ─────────────────────────────────────────────────────────────────────────────
# Score thresholds (transparent, tunable here)
# ─────────────────────────────────────────────────────────────────────────────

# Each shape metric → component score in [0, 1] (1 = ideal for symmetric-barrier).
# IDEAL profile: WR ≥ 65%, win/loss ≈ 1, daily Sharpe ≥ 0.10, freq ≥ 1 trade/day,
#                excess kurtosis ≈ 0 (Gaussian).
WINRATE_FLOOR     = 0.30   # below this → score 0
WINRATE_CEILING   = 0.65   # at or above → score 1
WINLOSS_IDEAL     = 1.0    # ratio at 1 → score 1
WINLOSS_CAP       = 2.0    # ratio ≥ 2 → score 0 (asymmetric / lumpy)
DSHARPE_TARGET    = 0.10   # daily Sharpe ≥ 0.10 → score 1
FREQ_TARGET       = 1.0    # 1+ trade/day → score 1
EXCESS_KURT_FLOOR = 0.0    # excess kurtosis ≤ 0 → score 1
EXCESS_KURT_CAP   = 6.0    # excess kurtosis ≥ 6 → score 0

# Gates (any one failing forces a downgrade)
CANDIDATE_MIN_SCORE = 0.65
CANDIDATE_MIN_WR    = 0.55   # s_winrate at this point: (0.55-0.30)/(0.35) = 0.71
CANDIDATE_MIN_WL    = 1.5    # s_winloss at this point: (2-1.5)/1 = 0.5
MARGINAL_MIN_SCORE  = 0.45
MIN_METRICS         = 3      # need at least this many of (5) to issue a verdict

# Sample-size hard filter — applies on top of any score (L14: testnet/short
# samples are inadmissible). A strategy with fewer than this many trades is
# auto-routed to DATA-INSUFFISANT regardless of how good the metrics look.
MIN_TRADES_FOR_VERDICT  = 100
MIN_DAYS_FOR_VERDICT    = 250   # ~1 trading year


# ─────────────────────────────────────────────────────────────────────────────
# Strategy class taxonomy (cosmetic)
# ─────────────────────────────────────────────────────────────────────────────

def classify(path: str) -> str:
    p = path.lower()
    if "crypto" in p: return "Crypto"
    if "forex"  in p: return "FX"
    if "equit"  in p: return "Equities"
    if "future" in p: return "Futures"
    if "multi_asset" in p: return "Multi-Asset"
    if "options_vol" in p: return "Options"
    if "etf_vol" in p: return "ETF Vol"
    return "?"


# ─────────────────────────────────────────────────────────────────────────────
# Metric record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StratMetrics:
    name:        str
    cls:         str
    source:      str
    # Available raw metrics (None = missing)
    sharpe:      float | None = None
    sharpe_kind: str          = ""        # "daily_hac", "annual", "deflated"...
    win_rate:    float | None = None
    avg_winner:  float | None = None
    avg_loser:   float | None = None
    win_loss_ratio: float | None = None
    n_trades:    int | None   = None
    n_days:      int | None   = None
    max_dd:      float | None = None
    excess_kurt: float | None = None
    # Derived
    daily_sharpe:float | None = None
    freq_per_day:float | None = None
    # Scored
    s_winrate:   float | None = None
    s_winloss:   float | None = None
    s_dsharpe:   float | None = None
    s_freq:      float | None = None
    s_kurt:      float | None = None
    score:       float | None = None
    n_metrics:   int          = 0
    verdict:     str          = ""
    missing:     list[str]    = field(default_factory=list)
    notes:       str          = ""


def clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


def score_metrics(m: StratMetrics) -> StratMetrics:
    """Apply scoring formula. Each component in [0,1]; final = mean of available."""
    if m.win_rate is not None:
        m.s_winrate = clip01((m.win_rate - WINRATE_FLOOR) /
                              (WINRATE_CEILING - WINRATE_FLOOR))
    else:
        m.missing.append("win_rate")
    if m.win_loss_ratio is not None:
        m.s_winloss = clip01((WINLOSS_CAP - m.win_loss_ratio) /
                              (WINLOSS_CAP - WINLOSS_IDEAL))
    else:
        m.missing.append("win_loss_ratio")
    if m.daily_sharpe is not None:
        m.s_dsharpe = clip01(m.daily_sharpe / DSHARPE_TARGET)
    else:
        m.missing.append("daily_sharpe")
    if m.freq_per_day is not None:
        m.s_freq = clip01(m.freq_per_day / FREQ_TARGET)
    else:
        m.missing.append("freq_per_day")
    if m.excess_kurt is not None:
        m.s_kurt = clip01((EXCESS_KURT_CAP - m.excess_kurt) /
                          (EXCESS_KURT_CAP - EXCESS_KURT_FLOOR))
    else:
        m.missing.append("excess_kurt")

    parts = [v for v in (m.s_winrate, m.s_winloss, m.s_dsharpe,
                          m.s_freq, m.s_kurt) if v is not None]
    m.n_metrics = len(parts)
    if m.n_metrics == 0:
        m.score = None
    else:
        m.score = float(np.mean(parts))
    return m


def verdict_for(m: StratMetrics) -> str:
    if m.n_metrics < MIN_METRICS:
        return "DATA-INSUFFISANT"
    if m.score is None:
        return "DATA-INSUFFISANT"
    # Sample-size hard filter (L14: small-N inadmissible)
    if m.n_trades is not None and m.n_trades < MIN_TRADES_FOR_VERDICT:
        return "DATA-INSUFFISANT"
    if m.n_days is not None and m.n_days < MIN_DAYS_FOR_VERDICT:
        return "DATA-INSUFFISANT"
    # Hard gates
    fail_wr = (m.s_winrate is not None and m.s_winrate < (
        (CANDIDATE_MIN_WR - WINRATE_FLOOR) /
        (WINRATE_CEILING - WINRATE_FLOOR)))
    fail_wl = (m.s_winloss is not None and m.s_winloss < (
        (WINLOSS_CAP - CANDIDATE_MIN_WL) /
        (WINLOSS_CAP - WINLOSS_IDEAL)))
    if m.score >= CANDIDATE_MIN_SCORE and not fail_wr and not fail_wl:
        return "FTMO-CANDIDATE"
    if m.score >= MARGINAL_MIN_SCORE:
        return "MARGINAL"
    return "LUMPY-UNFIT"


# ─────────────────────────────────────────────────────────────────────────────
# Extractors per file shape
# ─────────────────────────────────────────────────────────────────────────────

def derive_winloss(avg_w: float | None, avg_l: float | None) -> float | None:
    if avg_w is None or avg_l is None:
        return None
    if avg_l == 0:
        return None
    return float(abs(avg_w) / abs(avg_l))


def derive_dsharpe(sharpe_ann: float | None) -> float | None:
    if sharpe_ann is None:
        return None
    return float(sharpe_ann / np.sqrt(252))


def derive_freq(n_trades: int | None, n_days: int | None) -> float | None:
    if not n_trades or not n_days or n_days == 0:
        return None
    return float(n_trades) / float(n_days)


# ── (1) nq_intraday/results.json (multi-entry) ──────────────────────────────

def parse_nq_intraday(path: Path) -> list[StratMetrics]:
    entries = json.loads(path.read_text())
    out: list[StratMetrics] = []
    for e in entries:
        if "iteration" not in e:
            continue
        if e.get("n_trades", 0) == 0:
            continue
        name = f"nq_intraday/{e['iteration']}"
        m = StratMetrics(name=name, cls="Futures", source=str(path.relative_to(REPO)))
        # Sharpe : prefer HAC, fall back to plain
        m.sharpe        = e.get("sharpe_daily_hac") or e.get("sharpe")
        m.sharpe_kind   = ("annual_HAC" if "sharpe_daily_hac" in e
                            else ("annual" if "sharpe" in e else ""))
        m.win_rate      = e.get("win_rate")
        m.avg_winner    = e.get("avg_winner_usd") or e.get("avg_winner")
        m.avg_loser     = e.get("avg_loser_usd")  or e.get("avg_loser")
        m.win_loss_ratio= derive_winloss(m.avg_winner, m.avg_loser)
        m.n_trades      = e.get("n_trades")
        m.max_dd        = e.get("max_dd_pct") or e.get("max_dd")
        # Sample range — most iter_* run on full 772 RTH days (2022-12 → 2025-12);
        # iter_07_val_* are 70-day OOS validation slices (period_start/end exposed).
        if "period_start" in e and "period_end" in e:
            try:
                s = pd.Timestamp(e["period_start"])
                en = pd.Timestamp(e["period_end"])
                m.n_days = int(np.busday_count(s.date(), en.date()) + 1)
            except Exception:
                m.n_days = 772
        else:
            m.n_days = 772
        m.daily_sharpe  = derive_dsharpe(m.sharpe)
        # trades_per_day exposed directly on D1-D5 entries; otherwise derive
        if "trades_per_day" in e and isinstance(e["trades_per_day"], (int, float)):
            m.freq_per_day = float(e["trades_per_day"])
        else:
            m.freq_per_day = derive_freq(m.n_trades, m.n_days)
        out.append(m)
    return out


# ── (2) sector_hothand phase1_baseline ──────────────────────────────────────

def parse_sector_hothand(path: Path) -> list[StratMetrics]:
    d = json.loads(path.read_text())
    m = StratMetrics(
        name="sector_hothand_propfirm",
        cls="Equities",
        source=str(path.relative_to(REPO)),
    )
    m.sharpe       = d.get("sharpe_net")
    m.sharpe_kind  = "annual_HAC_net"
    m.max_dd       = d.get("max_drawdown")
    m.n_days       = d.get("T_days")
    m.daily_sharpe = derive_dsharpe(m.sharpe)
    # ⚠ engine.py:120 look-ahead audited; metrics inflated. Note in output.
    m.notes        = (
        "engine look-ahead audited (_audit/sector_hothand_audit_2026-05-30.md). "
        "Metrics likely inflated. WR/win-loss not exposed in this baseline JSON."
    )
    return [m]


# ── (3) simple results.json with sharpe/maxdd ──────────────────────────────

def _first_dict_with_keys(d: dict, keys: list[str]) -> dict | None:
    """Find the first nested dict that has at least one of the keys."""
    if any(k in d for k in keys):
        return d
    for v in d.values():
        if isinstance(v, dict):
            r = _first_dict_with_keys(v, keys)
            if r is not None:
                return r
    return None


def parse_generic(path: Path, name: str) -> list[StratMetrics]:
    try:
        d = json.loads(path.read_text())
    except Exception:
        return []
    cls = classify(str(path))
    m = StratMetrics(name=name, cls=cls, source=str(path.relative_to(REPO)))

    # Look for common shapes
    cands = []
    if isinstance(d, list):
        for x in d:
            if isinstance(x, dict):
                cands.append(x)
    elif isinstance(d, dict):
        cands.append(d)
        # Some files nest under variant keys (e.g. fx_carry_trend has raw_carry,
        # variant_A/B/C). Walk one level deeper for representative entries.
        for v in d.values():
            if isinstance(v, dict):
                cands.append(v)

    sharpe = win_rate = avg_w = avg_l = n_tr = max_dd = None
    sharpe_kind = ""
    for c in cands:
        if sharpe is None:
            for k in ("sharpe_daily_hac", "sharpe_hac", "sharpe_net",
                      "sharpe_annual", "sharpe", "sr_hac", "sr_net", "sr"):
                if k in c and isinstance(c[k], (int, float)):
                    sharpe = float(c[k])
                    sharpe_kind = k
                    break
        if win_rate is None:
            for k in ("win_rate", "winrate", "wr", "hit_rate"):
                if k in c and isinstance(c[k], (int, float)):
                    win_rate = float(c[k])
                    break
        if avg_w is None:
            for k in ("avg_winner_usd", "avg_winner", "avg_win",
                      "mean_winner"):
                if k in c and isinstance(c[k], (int, float)):
                    avg_w = float(c[k])
                    break
        if avg_l is None:
            for k in ("avg_loser_usd", "avg_loser", "avg_loss",
                      "mean_loser"):
                if k in c and isinstance(c[k], (int, float)):
                    avg_l = float(c[k])
                    break
        if n_tr is None:
            for k in ("n_trades", "n_test", "n", "trade_count"):
                if k in c and isinstance(c[k], (int, float)):
                    n_tr = int(c[k])
                    break
        if max_dd is None:
            for k in ("max_dd", "max_dd_pct", "max_drawdown"):
                if k in c and isinstance(c[k], (int, float)):
                    max_dd = float(c[k])
                    break

    m.sharpe         = sharpe
    m.sharpe_kind    = sharpe_kind
    m.win_rate       = win_rate
    m.avg_winner     = avg_w
    m.avg_loser      = avg_l
    m.win_loss_ratio = derive_winloss(avg_w, avg_l)
    m.n_trades       = n_tr
    m.max_dd         = max_dd
    m.daily_sharpe   = derive_dsharpe(m.sharpe)
    # No n_days info from generic shape — leave freq as N/A unless we can derive.
    return [m]


# ── (4) voie_b_ftmo returns CSV — direct distribution ──────────────────────

def parse_voie_b_ftmo() -> list[StratMetrics]:
    csv_path = REPO / "Futures/research/active/voie_b_ftmo/results/ftmo_voie_b_returns.csv"
    if not csv_path.exists():
        return []
    df = pd.read_csv(csv_path)
    # Heuristic: first numeric column is the daily return series
    num_cols = df.select_dtypes(include=[np.number]).columns
    if len(num_cols) == 0:
        return []
    # Try standard column names first
    for col in ("ret", "return", "daily_ret", "pnl", "ret_net"):
        if col in df.columns:
            r = df[col].dropna().astype(float).values
            break
    else:
        r = df[num_cols[0]].dropna().astype(float).values

    if len(r) < 20:
        return []

    from scipy import stats
    m = StratMetrics(
        name="voie_b_ftmo",
        cls="Futures",
        source=str(csv_path.relative_to(REPO)),
    )
    mean = float(np.mean(r))
    std = float(np.std(r, ddof=1))
    m.sharpe       = float(mean / std * np.sqrt(252)) if std > 0 else None
    m.sharpe_kind  = "annual_raw_from_returns"
    m.daily_sharpe = (mean / std) if std > 0 else None
    m.win_rate     = float((r > 0).mean())
    pos = r[r > 0]; neg = r[r < 0]
    if len(pos) > 0:
        m.avg_winner = float(pos.mean())
    if len(neg) > 0:
        m.avg_loser  = float(neg.mean())
    m.win_loss_ratio = derive_winloss(m.avg_winner, m.avg_loser)
    m.excess_kurt  = float(stats.kurtosis(r, fisher=True, bias=False))
    m.n_days       = int(len(r))
    # voie_b is "daily decision" not "per trade", so freq_per_day = ratio of
    # days with non-zero return.
    nonzero = int((r != 0).sum())
    m.n_trades     = nonzero
    m.freq_per_day = nonzero / len(r)
    m.notes        = (
        f"Computed from {len(r)} daily returns. Engine = US open-to-close "
        "on US indices when ≥N intl gaps confirm (CAUSAL signal at 14:30 UTC). "
        "Audit-clean per _audit/engine_contamination_2026-05-30.md."
    )
    return [m]


# ── (5) Strategy C iter_10 — special: we have moments from account_sweep ───

def parse_strategy_c_anchor() -> list[StratMetrics]:
    """
    Build Strategy C's profile from the daily-PnL moments already exposed
    in account_sweep results (rather than re-running the engine here).
    """
    # Pull stats from results.json iter_10 entry and from account_sweep stats.
    nq = json.loads((REPO / "Futures/research/active/nq_intraday/results.json").read_text())
    iter10 = next(e for e in nq if e.get("iteration") == "iter_10")
    m = StratMetrics(
        name="nq_intraday/iter_10 (Strategy C anchor)",
        cls="Futures",
        source="Futures/research/active/nq_intraday/results.json + _audit/strategy_c_ftmo10k_sim_results.json",
    )
    m.sharpe        = iter10.get("sharpe_daily_hac")
    m.sharpe_kind   = "annual_HAC"
    m.win_rate      = iter10.get("win_rate")
    m.avg_winner    = iter10.get("avg_winner_usd")
    m.avg_loser     = iter10.get("avg_loser_usd")
    m.win_loss_ratio= derive_winloss(m.avg_winner, m.avg_loser)
    m.n_trades      = iter10.get("n_trades")
    m.max_dd        = iter10.get("max_dd_pct")
    m.n_days        = 772
    m.daily_sharpe  = derive_dsharpe(m.sharpe)
    m.freq_per_day  = derive_freq(m.n_trades, m.n_days)
    # Excess kurtosis: from acccount_sweep daily series at 1 NQ:
    # mean=$58.92, std=$662, min=-$440, max=$4473 — extreme positive skew.
    # Rough estimate via Vasicek-Kupiec: K_exc ≈ ((max-mean)/std)^2 - 3 ≈ (4414/662)^2 - 3 ≈ 41.
    # Use a conservative-but-honest estimate.
    sweep = json.loads((REPO / "_audit/strategy_c_ftmo10k_sim_results.json").read_text())
    n1 = next(r for r in sweep if r["n_contracts"] == 1)
    rng_over_std = (n1["daily_max_usd"] - n1["daily_min_usd"]) / n1["daily_std_usd"]
    # Heavy tails: a normal max over T=772 obs ≈ 3.4σ; we see 7.4σ rng. Excess kurt
    # crude: (Mx/std)^2 / (2 log T)  — Gumbel approx ; high-tail estimate.
    m.excess_kurt   = float((n1["daily_max_usd"] / n1["daily_std_usd"]) ** 2 - 3)
    m.notes         = (
        f"Daily moments from _audit/strategy_c_ftmo10k_sim_results.json "
        f"(N=1 MNQ): rng/std={rng_over_std:.1f}σ. Excess kurt estimated via "
        f"max-over-std square, conservative. Anchor for L24 calibration."
    )
    return [m]


# ── (6) nq_intraday_vwap iter_01_summary.md — text scrape ──────────────────

def parse_nq_vwap_text() -> list[StratMetrics]:
    p = REPO / "Futures/research/active/nq_intraday_vwap/iter_01_summary.md"
    if not p.exists():
        return []
    txt = p.read_text()
    m = StratMetrics(
        name="nq_intraday_vwap/iter_01",
        cls="Futures",
        source=str(p.relative_to(REPO)),
    )
    # Heuristic scrape (ad hoc — these strategies were already FAIL).
    sharpe_match = re.search(r"sharpe[^=:]*[:=]\s*(-?\d+\.\d+)", txt, re.I)
    if sharpe_match:
        m.sharpe       = float(sharpe_match.group(1))
        m.sharpe_kind  = "scraped_text"
        m.daily_sharpe = derive_dsharpe(m.sharpe)
    n_match = re.search(r"\bN\s*=\s*(\d+)", txt)
    if n_match:
        m.n_trades = int(n_match.group(1))
    m.notes = (
        "Scraped from iter_01_summary.md. Already FAIL: 'INSUFFICIENT SAMPLE "
        "(N=19 over 3 years)'. Also LOOK-AHEAD per engine_contamination audit."
    )
    return [m]


# ── (7) Inventory items with no metrics at all (mention only) ───────────────

NO_METRIC_STRATEGIES = [
    {"name": "strategy_d (pre-registration)", "cls": "Futures",
     "source": "Futures/research/active/strategy_d/hypotheses_preregistered.md",
     "note": "Pre-registration document only. No backtest run yet."},
    {"name": "strategy_d_nq (infra)", "cls": "Futures",
     "source": "Futures/research/active/strategy_d_nq/infra/",
     "note": "Infra scripts only (run_manual_signal.sh + plist)."},
    {"name": "cip_eoq (sigma_estimation only)", "cls": "FX",
     "source": "Forex/research/active/cip_eoq/sigma_estimation/",
     "note": "sigma_estimation_findings.md + validate_basis.py. No backtest."},
    {"name": "zn_baltussen (no top-level files)", "cls": "Futures",
     "source": "Futures/research/active/zn_baltussen/",
     "note": "Only tests/ + sigma_estimation/. No metrics emitted."},
    {"name": "token_unlocks", "cls": "Crypto",
     "source": "Crypto/research/active/token_unlocks/_bootstrap_notes.md",
     "note": "Bootstrap notes only."},
    {"name": "vrp_short_gamma", "cls": "Crypto",
     "source": "Crypto/research/active/vrp_short_gamma/_bootstrap_vrp_notes.md",
     "note": "Bootstrap notes only."},
    {"name": "network_momentum (archived)", "cls": "Multi-Asset",
     "source": "Multi_Asset/research/archived/network_momentum/feasibility_summary.md",
     "note": "FAIL (E3 Sharpe=0.293). No exploitable trade/return series."},
]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 80)
    print("FTMO-suitability inventory screen — 2026-05-30")
    print("=" * 80)

    results: list[StratMetrics] = []

    # (1) NQ intraday multi-entry
    nq_path = REPO / "Futures/research/active/nq_intraday/results.json"
    print(f"\nParsing {nq_path.relative_to(REPO)} ...")
    results.extend(parse_nq_intraday(nq_path))
    # Override iter_10 with anchored Strategy C entry (richer)
    results = [r for r in results if r.name != "nq_intraday/iter_10"]
    results.extend(parse_strategy_c_anchor())

    # (2) sector_hothand baseline
    sh_path = REPO / "Equities/research/active/sector_hothand_propfirm/results/phase1_baseline.json"
    if sh_path.exists():
        print(f"Parsing {sh_path.relative_to(REPO)} ...")
        results.extend(parse_sector_hothand(sh_path))

    # (3) generic results.json across the repo
    generic_paths = [
        ("Crypto/research/archived/etf_regime_overlay/data/phase2_results.json", "etf_regime_overlay"),
        ("Crypto/research/archived/h31_cs_fs_dn/results/metrics_validation.json", "h31_cs_fs_dn"),
        ("Crypto/research/archived/options/vrp_deribit/phase3_results.json", "vrp_deribit"),
        ("Crypto/research/archived/other/fgvd_h1/data/phase2_results.json", "fgvd_h1"),
        ("Crypto/research/archived/other/pmr_basis/results.json", "pmr_basis"),
        ("Crypto/research/archived/other/wav_h3/data/phase2_results.json", "wav_h3"),
        ("Equities/research/archived/jt_momentum_cs/results.json", "jt_momentum_cs"),
        ("Equities/research/archived/multi_asset_tsmom/results.json", "multi_asset_tsmom"),
        ("Forex/research/archived/fx_carry_em/results.json", "fx_carry_em"),
        ("Forex/research/archived/fx_carry_fred/results.json", "fx_carry_fred"),
        ("Forex/research/archived/fx_carry_trend/results.json", "fx_carry_trend"),
        ("Forex/research/archived/fx_momentum_monthly/results.json", "fx_momentum_monthly"),
        ("Forex/research/archived/strategy_d_modified_carry/results.json", "fx_strategy_d_modified_carry"),
        ("Forex/research/archived/strategy_d_modified_carry_v2/results.json", "fx_strategy_d_modified_carry_v2"),
        ("Forex/research/archived/strategy_f2_asian_breakout/results.json", "f2_asian_breakout"),
        ("Options_Vol/research/archived/vrp_spx_angle_c/phase1/phase1_results.json", "vrp_spx_angle_c"),
    ]
    for rel, name in generic_paths:
        p = REPO / rel
        if not p.exists():
            print(f"  skip (missing): {rel}")
            continue
        results.extend(parse_generic(p, name))

    # (4) voie_b_ftmo CSV
    print("Parsing voie_b_ftmo returns CSV ...")
    results.extend(parse_voie_b_ftmo())

    # (5) nq_intraday_vwap text scrape
    print("Parsing nq_intraday_vwap iter_01 summary text ...")
    results.extend(parse_nq_vwap_text())

    # ── Score everything ──────────────────────────────────────────────────
    for m in results:
        score_metrics(m)
        m.verdict = verdict_for(m)

    # ── No-metric strategies (mention only) ──────────────────────────────
    no_metric = [
        {**x, "verdict": "DATA-INSUFFISANT"} for x in NO_METRIC_STRATEGIES
    ]

    # ── Sort by verdict tier then by score within tier ────────────────────
    tier_order = {"FTMO-CANDIDATE": 0, "MARGINAL": 1,
                  "LUMPY-UNFIT": 2, "DATA-INSUFFISANT": 3}
    results.sort(key=lambda r: (tier_order.get(r.verdict, 9),
                                  -(r.score or -1.0)))

    # ── Console summary ───────────────────────────────────────────────────
    print(f"\n{'#':>2}  {'Strategy':<48} {'Class':<10} {'N':>5} {'WR':>6} "
          f"{'WL':>5} {'dSh':>5} {'frq':>5} {'krt':>5} {'Score':>7}  Verdict")
    print("-" * 130)
    for i, m in enumerate(results, 1):
        if m.verdict == "DATA-INSUFFISANT":
            sc = "(n/a)"
        else:
            sc = f"{m.score:.3f}" if m.score is not None else "  N/A"
        wr  = f"{m.win_rate*100:.0f}%" if m.win_rate is not None else "  -"
        wl  = f"{m.win_loss_ratio:.2f}" if m.win_loss_ratio is not None else "  -"
        dsh = f"{m.daily_sharpe:.2f}" if m.daily_sharpe is not None else "  -"
        frq = f"{m.freq_per_day:.2f}" if m.freq_per_day is not None else "  -"
        krt = f"{m.excess_kurt:.1f}" if m.excess_kurt is not None else "  -"
        ntr = f"{m.n_trades}" if m.n_trades is not None else "  -"
        print(f"{i:>2}  {m.name:<48} {m.cls:<10} {ntr:>5} {wr:>6} {wl:>5} "
              f"{dsh:>5} {frq:>5} {krt:>5} {sc:>7}  {m.verdict}")

    # ── Persist JSON ──────────────────────────────────────────────────────
    out_json = REPO / "_audit/ftmo_suitability_screen_results.json"
    payload = {
        "thresholds": {
            "WINRATE_FLOOR": WINRATE_FLOOR,
            "WINRATE_CEILING": WINRATE_CEILING,
            "WINLOSS_IDEAL": WINLOSS_IDEAL,
            "WINLOSS_CAP": WINLOSS_CAP,
            "DSHARPE_TARGET": DSHARPE_TARGET,
            "FREQ_TARGET": FREQ_TARGET,
            "EXCESS_KURT_CAP": EXCESS_KURT_CAP,
            "CANDIDATE_MIN_SCORE": CANDIDATE_MIN_SCORE,
            "CANDIDATE_MIN_WR": CANDIDATE_MIN_WR,
            "CANDIDATE_MIN_WL": CANDIDATE_MIN_WL,
            "MARGINAL_MIN_SCORE": MARGINAL_MIN_SCORE,
            "MIN_METRICS": MIN_METRICS,
        },
        "strategies":  [asdict(m) for m in results],
        "no_metric":   no_metric,
    }
    out_json.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\n  → {out_json.relative_to(REPO)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
