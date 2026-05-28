"""
corr_c_b.py — Correlation between Strategy C (iter_10 NQ ORB) and Voie B.

Strategy C returns: generated from NQ 1-min data via iter_10 engine.
Voie B returns:     results/ftmo_voie_b_returns.csv (pre-computed).

Output: results/corr_c_b.md
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)

VOIE_B_CSV  = RESULTS / "ftmo_voie_b_returns.csv"
NQ_CSV_PATH = REPO / "Dataset_NQ_1min_2022_2025.csv"


# ─── Strategy C (iter_10) engine — minimal self-contained reproduction ────────
# Source: Futures/research/active/nq_intraday/analysis/iter_10_refined.py
# Signal: 09:30-09:45 ET opening range, entry 09:46 ET
# Filters: VWAP confirm, gap < 1.2%, range ≥ 30pts, SL cap $400 (MNQ: 0.5R/20pt floor)
# TP: 1.5R, SL: min(0.5R, 20pts), time stop 12:30 ET

def build_strategy_c_returns(nq_path: Path) -> pd.Series:
    """
    Reproduce iter_10 daily returns from NQ 1-min CSV.

    Signal logic mirrors iter_05.py build_opening_features + signals_from_features
    with iter_10 parameters (STRATEGY_GAP=0.012, STRATEGY_STOP=400, RNG_MIN=30).

    direction = sign(orb_close_9:45 - orb_open_9:30)   [NOT breakout of high/low]
    rng       = abs(orb_close - orb_open)               [NOT high-low range]
    VWAP check at 09:45 bar close vs vwap_rth            [NOT at entry bar]
    Gap: RTH daily close-to-open                         [NOT raw prev_close]
    """
    import datetime as dt
    from data.cache import load_nq_1min
    nq = load_nq_1min(str(nq_path))

    # ── parameters (iter_10 final, matching iter_05 engine) ──────────────
    T_ORB_START = dt.time(9, 30)
    T_ORB_END   = dt.time(9, 45)
    T_EXIT      = dt.time(12, 30)
    T_RTH_END   = dt.time(15, 59)
    GAP_MAX     = 0.012        # 1.2% RTH gap threshold
    RANGE_MIN   = 30.0         # pts close-to-open momentum, RNG_MIN in iter_10
    TP_MULT     = 1.5          # BASE_TP_MULT
    SL_MULT     = 0.5          # BASE_SL_MULT
    # NQ engine: POINT_VALUE=20, COST_RT=19 → cap ≈ 21pts
    SL_CAP_PTS  = (400.0 + 19.0) / 20.0
    SLIP_PT     = 1.0          # 4 ticks RT = 1 NQ pt total

    # ── RTH daily open/close for gap computation (iter_05 approach) ───────
    rth = nq[(nq.index.time >= T_ORB_START) & (nq.index.time <= T_RTH_END)]
    daily_rth_open  = rth["open"].resample("B").first().dropna()
    daily_rth_close = rth["close"].resample("B").last().dropna()

    dates   = sorted(nq.index.normalize().unique())
    records = []

    for i, date in enumerate(dates):
        day      = nq[nq.index.normalize() == date]
        prev_date = dates[i - 1] if i > 0 else None

        # ── ORB 09:30-09:45 ───────────────────────────────────────────────
        opening = day.between_time("09:30", "09:45")
        if len(opening) < 2:
            continue

        orb_open  = float(opening.iloc[0]["open"])
        orb_close = float(opening.iloc[-1]["close"])
        rng = abs(orb_close - orb_open)

        # ── range filter (close-to-open momentum, NOT high-low) ───────────
        if rng < RANGE_MIN:
            continue

        direction = 1 if orb_close > orb_open else -1

        # ── VWAP check at 09:45 bar (iter_05 vwap_ok logic) ──────────────
        vwap_at_sig = float(opening.iloc[-1]["vwap_rth"])
        if vwap_at_sig == 0 or pd.isna(vwap_at_sig):
            vwap_at_sig = orb_open
        vwap_ok = (direction == 1 and orb_close > vwap_at_sig) or \
                  (direction == -1 and orb_close < vwap_at_sig)
        if not vwap_ok:
            continue

        # ── gap filter (RTH close-to-open, iter_05 approach) ─────────────
        today_open_rth = float(daily_rth_open.get(date, np.nan))
        prev_close_rth = float(daily_rth_close.get(prev_date, np.nan)) if prev_date else np.nan
        if not (np.isfinite(today_open_rth) and np.isfinite(prev_close_rth)
                and prev_close_rth > 0):
            continue
        gap = abs(today_open_rth - prev_close_rth) / prev_close_rth
        if gap > GAP_MAX:
            continue

        # ── entry: first bar after 09:45 end (09:46 open) ────────────────
        post_orb = day[day.index > opening.index[-1]]
        post_orb_to_exit = post_orb[post_orb.index.time <= T_EXIT]
        if post_orb_to_exit.empty:
            continue
        entry_price = float(post_orb_to_exit.iloc[0]["open"])

        # ── SL / TP (matching iter_05 signals_from_features) ─────────────
        sl_pts = min(rng * SL_MULT, SL_CAP_PTS)
        tp_pts = rng * TP_MULT

        sl_price = entry_price - direction * sl_pts
        tp_price = entry_price + direction * tp_pts

        # ── simulate bars 09:47 → 12:30 ──────────────────────────────────
        exit_price = None
        for _, bar in post_orb_to_exit.iloc[1:].iterrows():
            if direction == 1:
                if bar["low"] <= sl_price:
                    exit_price = sl_price; break
                if bar["high"] >= tp_price:
                    exit_price = tp_price; break
            else:
                if bar["high"] >= sl_price:
                    exit_price = sl_price; break
                if bar["low"] <= tp_price:
                    exit_price = tp_price; break

        if exit_price is None:
            stop_bars = day.between_time("12:30", "12:30")
            exit_price = float(stop_bars.iloc[0]["close"]) if len(stop_bars) > 0 else entry_price

        # ── P&L (fractional price return, net of slippage) ───────────────
        raw_pts = direction * (exit_price - entry_price)
        net_pts = raw_pts - SLIP_PT
        ret     = net_pts / entry_price

        records.append({"date": date.date(), "ret_c": ret, "direction": direction})

    if not records:
        raise ValueError("No iter_10 trades generated — check filters or data range")

    df_c = pd.DataFrame(records).set_index("date")
    df_c.index = pd.to_datetime(df_c.index)
    return df_c["ret_c"]


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Loading Voie B returns...")
    voie_b = pd.read_csv(VOIE_B_CSV, parse_dates=["Date"]).set_index("Date")
    voie_b.columns = ["ret_b"]
    print(f"  Voie B: {voie_b.index[0].date()} → {voie_b.index[-1].date()}, {len(voie_b)} days")

    print("Building Strategy C returns from NQ 1-min...")
    if not NQ_CSV_PATH.exists():
        print(f"  NQ 1-min CSV not found at {NQ_CSV_PATH}")
        print("  Cannot compute corr(C, B) — NQ data required.")
        # write placeholder
        md = ["# corr(C, B)", "", "**BLOCKED:** NQ 1-min dataset not found.",
              f"Expected: `{NQ_CSV_PATH.name}`"]
        (RESULTS / "corr_c_b.md").write_text("\n".join(md))
        return

    ret_c = build_strategy_c_returns(NQ_CSV_PATH)
    print(f"  Strategy C: {ret_c.index[0].date()} → {ret_c.index[-1].date()}, "
          f"{len(ret_c)} trading days ({(ret_c != 0).sum()} active)")

    # ── align on common dates ──────────────────────────────────────────────
    common = voie_b.index.intersection(ret_c.index)
    if len(common) < 30:
        print(f"  Insufficient overlap ({len(common)} days). Check data range.")
        return

    b = voie_b.loc[common, "ret_b"]
    c = ret_c.loc[common].rename("ret_c")
    df = pd.concat([c, b], axis=1).dropna()
    print(f"  Overlap: {common[0].date()} → {common[-1].date()}, {len(df)} days")

    corr      = float(df["ret_c"].corr(df["ret_b"]))
    corr_spear = float(df["ret_c"].rank().corr(df["ret_b"].rank()))
    # only days where both are active
    active_both = df[(df["ret_c"] != 0) & (df["ret_b"] != 0)]
    corr_active = float(active_both["ret_c"].corr(active_both["ret_b"])) if len(active_both) > 10 else float("nan")
    n_active = len(active_both)

    # ── Sharpe for context ─────────────────────────────────────────────────
    sr_c = float(df["ret_c"].mean() / df["ret_c"].std() * np.sqrt(252)) if df["ret_c"].std() > 0 else 0.0
    sr_b = float(df["ret_b"].mean() / df["ret_b"].std() * np.sqrt(252)) if df["ret_b"].std() > 0 else 0.0

    print(f"  corr(C, B) = {corr:.4f}  Spearman={corr_spear:.4f}  active-only={corr_active:.4f}")
    print(f"  SR_C={sr_c:.3f}  SR_B={sr_b:.3f}  overlap={len(df)}d")

    # ── markdown report ────────────────────────────────────────────────────
    md = [
        "# Corrélation Strategy C ↔ Voie B",
        "",
        f"**Run date:** {date.today()}  ",
        f"**Overlap:** {common[0].date()} → {common[-1].date()}  ",
        f"**N jours :** {len(df)} (dont {n_active} actifs simultanément)",
        "",
        "| Métrique | Valeur |",
        "|----------|--------|",
        f"| corr(C, B) Pearson | **{corr:.4f}** |",
        f"| corr(C, B) Spearman | {corr_spear:.4f} |",
        f"| corr(C, B) jours actifs-simultanés | {corr_active:.4f} |",
        f"| Sharpe C (sur overlap) | {sr_c:.3f} |",
        f"| Sharpe B (sur overlap) | {sr_b:.3f} |",
        "",
        "## Interprétation",
        "",
    ]

    if abs(corr) < 0.20:
        interp = (
            f"Corrélation faible ({corr:.2f}) — C et B sont **quasi-décorrelés** "
            f"sur la période commune. Diversification porteur efficace. "
            f"Les deux stratégies opèrent sur des mécanismes indépendants "
            f"(ORB momentum NQ 09:46-12:30 vs gap continuation US indices 14:30-21:00)."
        )
    elif abs(corr) < 0.40:
        interp = (
            f"Corrélation modérée ({corr:.2f}) — C et B partagent une exposition "
            f"beta US indices. Diversification partielle."
        )
    else:
        interp = (
            f"Corrélation élevée ({corr:.2f}) — C et B sont corrélés. "
            f"Diversification limitée — revoir l'allocation."
        )
    md += [interp, ""]

    # portfolio portfolio combined SR (ERC weights 50/50 approx)
    if len(df) > 50:
        port = 0.5 * df["ret_c"] + 0.5 * df["ret_b"]
        sr_port = float(port.mean() / port.std() * np.sqrt(252)) if port.std() > 0 else 0.0
        md += [
            f"**SR portefeuille 50/50 (sur overlap) :** {sr_port:.3f}",
            "",
            f"Diversification lift : {sr_port:.3f} vs max(SR_C={sr_c:.2f}, SR_B={sr_b:.2f})",
            "",
        ]

    md += [
        "## Note de portée",
        "",
        "L'overlap est limité au dataset NQ 1-min disponible (fin 2022 → 2025).",
        "Voie B couvre 2010-2026 mais Strategy C seulement 2022-2025.",
        "Corrélation estimée sur ~3 ans — à ré-estimer quand NQ dataset étendu.",
    ]

    out_path = RESULTS / "corr_c_b.md"
    out_path.write_text("\n".join(md))
    print(f"  Report → {out_path.relative_to(Path(__file__).parents[4])}")


if __name__ == "__main__":
    main()
