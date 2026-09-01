"""
Moteur de reproduction "Dedale" (DedaleFormation.mq5) - config A (defaut de code, 0 filtre TDI).
Voir SPEC_DEDALE.md et PREREGISTRATION.md pour la specification et les hypotheses figees.

Usage (par paire, ecriture incrementale) :
    /usr/bin/python3 dedale_engine.py EURUSD
    /usr/bin/python3 dedale_engine.py ALL     # boucle sequentielle sur les 7 paires

Sortie : trades_<PAIR>.csv dans le dossier parent (une ligne par trade ferme), colonnes brutes
(prix, dates, R-multiple, notional, cout, swap) -- la couche metrics.py fait les agregations.
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

CACHE_DIR = Path("<SCRATCH>"
                  "9fd32b98-b3ee-47bf-93c1-b7c5a1ac70a6/scratchpad/m1_cache")
RATES_CSV = Path("<HOME>/Desktop/Algo_claude/data/panels/fx_rates_3m.csv")
OUT_DIR = Path(__file__).resolve().parent.parent

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]

# base/quote currency for each pair, to compute rate differential base-quote
PAIR_CCY = {
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "AUDUSD": ("AUD", "USD"),
    "USDCAD": ("USD", "CAD"),
    "USDCHF": ("USD", "CHF"),
    "NZDUSD": ("NZD", "USD"),
}

PIVOT_NUMBER = 2
TARGET_PROBABILITY = 50.0
SL_DISTANCE_MIN_PIPS = 10.0
TP_DISTANCE_MIN_PIPS = 10.0
RISK_PCT = 1.0
SWAP_TRIPLE_DOW = 2  # Wednesday=2 (Mon=0) -> tripled to cover the weekend, standard FX convention
SWAP_HAIRCUT_REALISTIC = 0.85


def pip_size(pair: str) -> float:
    return 0.01 if pair.endswith("JPY") else 0.0001


def load_h1(pair: str) -> pd.DataFrame:
    df = pd.read_parquet(CACHE_DIR / f"{pair}_M1.parquet")
    h1 = df.resample("1h").agg(open=("open", "first"), high=("high", "max"),
                                low=("low", "min"), close=("close", "last")).dropna()
    return h1


def load_weekly_pivots(pair: str) -> pd.DataFrame:
    df = pd.read_parquet(CACHE_DIR / f"{pair}_M1.parquet")
    w = df.resample("W-SUN", label="left", closed="left").agg(
        high=("high", "max"), low=("low", "min"), close=("close", "last")).dropna()
    # week starting at label (Monday 00:00 UTC). Pivots for week N use week N-1's H/L/C.
    p0 = (w["high"] + w["low"] + w["close"]) / 3.0
    r1 = 2 * p0 - w["low"]
    s1 = 2 * p0 - w["high"]
    r2 = p0 + (w["high"] - w["low"])
    s2 = p0 - (w["high"] - w["low"])
    piv = pd.DataFrame({"S1": s1, "S2": s2, "R1": r1, "R2": r2})
    piv.index = piv.index + pd.Timedelta(days=7)  # shift: applies to the FOLLOWING week
    return piv


def load_rate_diff(base: str, quote: str) -> pd.Series:
    rates = pd.read_csv(RATES_CSV, parse_dates=["Date"]).set_index("Date")
    diff_pct = rates[base] - rates[quote]  # % per annum
    diff_pct = diff_pct.resample("D").ffill(limit=45)
    diff_pct.index = diff_pct.index.tz_localize("UTC")
    return diff_pct


def get_trade_info(direction: int, bid: float, ask: float, S1, S2, R1, R2):
    """Faithful replica of GetTradeInfo() in DedaleFormation.mq5.
    direction: 0=buy, 1=sell. Returns (sl, tp)."""
    S = [S1, S2]
    R = [R1, R2]
    if direction == 0:
        sl_size = [abs(S[i] - bid) for i in range(PIVOT_NUMBER)]
        tp_size = [abs(R[i] - ask) for i in range(PIVOT_NUMBER)]
    else:
        sl_size = [abs(R[i] - ask) for i in range(PIVOT_NUMBER)]
        tp_size = [abs(S[i] - bid) for i in range(PIVOT_NUMBER)]

    best_diff = None
    best_sl, best_tp = None, None
    for i in range(PIVOT_NUMBER):
        for j in range(PIVOT_NUMBER):
            if direction == 0:
                valid = (bid > S[j]) and (ask < R[i])
            else:
                valid = (bid > S[i]) and (ask < R[j])
            if valid:
                prob = tp_size[i] / (tp_size[i] + sl_size[j]) * 100.0
            else:
                prob = 151.0
            diff = abs(prob - TARGET_PROBABILITY)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                if direction == 0:
                    best_sl, best_tp = S[j], R[i]
                else:
                    best_sl, best_tp = R[j], S[i]
    return best_sl, best_tp


def run_pair(pair: str, cost_bps_list, swap_haircuts, verbose=True,
             direction_mode: str = "swap", seed: int = 123) -> pd.DataFrame:
    t0 = time.time()
    rng = np.random.default_rng(seed)
    base, quote = PAIR_CCY[pair]
    h1 = load_h1(pair)
    piv = load_weekly_pivots(pair)
    rate_diff = load_rate_diff(base, quote)  # base - quote, % p.a.
    pip = pip_size(pair)
    sl_min = SL_DISTANCE_MIN_PIPS * pip
    tp_min = TP_DISTANCE_MIN_PIPS * pip

    # align pivots and rate_diff to h1 index (backward asof, no lookahead)
    piv_al = piv.reindex(h1.index, method="ffill")
    rd_al = rate_diff.reindex(h1.index, method="ffill")

    idx = h1.index
    o = h1["open"].values
    hi = h1["high"].values
    lo = h1["low"].values
    cl = h1["close"].values
    S1 = piv_al["S1"].values
    S2 = piv_al["S2"].values
    R1 = piv_al["R1"].values
    R2 = piv_al["R2"].values
    rd = rd_al.values  # % p.a., base - quote

    n = len(h1)
    trades = []
    position = None  # dict when open

    for t in range(1, n - 1):
        if position is None:
            # evaluate signal at bar t (close of bar t), using rate diff known at t (no lookahead:
            # it's a policy-rate series ffilled, available well before bar t in practice)
            if np.isnan(S1[t]) or np.isnan(rd[t]):
                continue
            diff = rd[t]  # base minus quote, % p.a.
            if diff == 0:
                continue
            if direction_mode == "swap":
                direction = 0 if diff > 0 else 1  # long base = buy pair, swap_long positive
            elif direction_mode == "random":
                direction = int(rng.integers(0, 2))  # placebo: fair coin, same cadence/mechanics
            else:
                raise ValueError(direction_mode)
            mid = cl[t]
            sl, tp = get_trade_info(direction, mid, mid, S1[t], S2[t], R1[t], R2[t])
            if direction == 0:
                dist_sl = mid - sl
                dist_tp = tp - mid
            else:
                dist_sl = sl - mid
                dist_tp = mid - tp
            if dist_sl < sl_min or dist_tp < tp_min or dist_sl <= 0 or dist_tp <= 0:
                continue
            # enter at next bar's open (delay-1)
            entry_time = idx[t + 1]
            entry_price = o[t + 1]
            position = dict(direction=direction, entry_idx=t + 1, entry_time=entry_time,
                             entry_price=entry_price, sl=sl, tp=tp,
                             sl_dist=dist_sl, tp_dist=dist_tp, rate_diff_entry=diff)
        else:
            d = position["direction"]
            exit_price = None
            reason = None
            if d == 0:
                if lo[t] <= position["sl"]:
                    exit_price, reason = position["sl"], "SL"
                elif hi[t] >= position["tp"]:
                    exit_price, reason = position["tp"], "TP"
            else:
                if hi[t] >= position["sl"]:
                    exit_price, reason = position["sl"], "SL"
                elif lo[t] <= position["tp"]:
                    exit_price, reason = position["tp"], "TP"
            if exit_price is not None:
                entry_price = position["entry_price"]
                if d == 0:
                    r_multiple = (exit_price - entry_price) / position["sl_dist"]
                else:
                    r_multiple = (entry_price - exit_price) / position["sl_dist"]
                entry_time = position["entry_time"]
                exit_time = idx[t]
                hold_days = (exit_time - entry_time).total_seconds() / 86400.0
                # nights held: count midnight UTC crossings, x3 on Wednesday
                nights = 0.0
                day = entry_time.normalize()
                end_day = exit_time.normalize()
                while day < end_day:
                    mult = 3 if day.dayofweek == SWAP_TRIPLE_DOW else 1
                    nights += mult
                    day = day + pd.Timedelta(days=1)
                sign = 1 if d == 0 else -1
                swap_bps_annual = sign * position["rate_diff_entry"]  # >0 by construction
                # notional s.t. loss at SL = risk_pct * balance (balance tracked outside, use 1.0 unit here)
                frac_to_sl = position["sl_dist"] / entry_price
                notional_per_risk_unit = 1.0 / frac_to_sl if frac_to_sl > 0 else np.nan

                trades.append(dict(
                    pair=pair, direction="buy" if d == 0 else "sell",
                    entry_time=entry_time, exit_time=exit_time, exit_reason=reason,
                    entry_price=entry_price, exit_price=exit_price,
                    sl=position["sl"], tp=position["tp"],
                    r_multiple=r_multiple, hold_days=hold_days, nights=nights,
                    notional_per_risk_unit=notional_per_risk_unit,
                    swap_bps_annual=swap_bps_annual,
                ))
                position = None

    df = pd.DataFrame(trades)
    if verbose:
        print(f"[{pair}] {len(df)} trades, {time.time()-t0:.1f}s", flush=True)
    return df


def add_pnl_columns(df: pd.DataFrame, risk_pct=RISK_PCT, cost_bps=0.0, swap_haircut=1.0):
    """Given raw trade rows (r_multiple, notional_per_risk_unit, swap_bps_annual, nights),
    compute $ P&L per trade assuming risk_amount = risk_pct% of a NON-compounding $1 unit
    (per-trade fractional return on a fixed reference balance; compounding handled downstream
    in metrics.py on the resulting return series if desired)."""
    risk_amount = risk_pct / 100.0
    gross = df["r_multiple"] * risk_amount
    notional = risk_amount * df["notional_per_risk_unit"]
    cost = cost_bps * 1e-4 * notional  # round-trip, charged once at notional
    swap = (df["swap_bps_annual"] * swap_haircut / 100.0 / 365.0) * df["nights"] * notional
    out = df.copy()
    out["pnl_gross"] = gross
    out["pnl_cost"] = -cost
    out["pnl_swap"] = swap
    out["pnl_net_nocost"] = gross + swap
    out["pnl_net_full"] = gross - cost + swap
    return out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    mode = sys.argv[2] if len(sys.argv) > 2 else "swap"  # "swap" or "random" (placebo)
    targets = PAIRS if which == "ALL" else [which]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "" if mode == "swap" else "_placebo"
    for p in targets:
        df = run_pair(p, None, None, direction_mode=mode)
        df.to_csv(OUT_DIR / f"trades_{p}{suffix}.csv", index=False)
        print(f"wrote trades_{p}{suffix}.csv ({len(df)} rows)", flush=True)
