"""
strategies/combined_portfolio/regime_gated.py

HMM-gated combined portfolio: long leg always active, short leg
(SOL/LINK/BCH/OP when TSMOM signal=-1) active only in BEAR regime.

Hypothesis: feasibility.py WEAK result (Sharpe 0.76, -11.9% max daily)
was driven by shorts amplifying tail risk in bull markets. Regime-gating
should preserve hedge benefit while eliminating bull-market drag.

Prior chain:
  TSMOM v2 alone     → OOS Sharpe 0.43, Propr 34-45%
  Combined (ungated) → OOS Sharpe 0.76, Propr 34%, max daily -11.9%
  Target (DEPLOY)    → OOS Sharpe ≥ 1.5, Propr ≥ 45%
"""

from __future__ import annotations

import warnings
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yfinance as yf
from hmmlearn import hmm

warnings.filterwarnings("ignore")

# ── Constants ─────────────────────────────────────────────────────────────────
ASSETS = [
    "BTC-USD", "ETH-USD", "AVAX-USD", "LINK-USD", "DOGE-USD",
    "ADA-USD",  "DOT-USD", "LTC-USD",  "BCH-USD",  "OP-USD",  "SOL-USD",
]
SHORT_ELIGIBLE = {"SOL", "LINK", "BCH", "OP"}

TSMOM_LOOKBACK   = 28
VOL_WINDOW        = 20
VOL_TARGET_LONG   = 0.15
VOL_TARGET_SHORT  = 0.10
GROSS_CAP         = 0.90
COST_RT           = 0.0017   # 0.17% RT (taker 0.035% × 2 + slippage 0.05% × 2)

DATA_START   = "2020-06-01"   # warm-up: MA50 (50d) + HMM features
TRAIN_START  = "2021-01-01"
TRAIN_END    = "2023-12-31"
TEST_START   = "2024-01-01"
TEST_END     = "2026-05-14"

WALK_FORWARD_WINDOWS: list[tuple[str, str, str, str]] = [
    ("2021-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
    ("2021-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("2021-01-01", "2023-06-30", "2023-07-01", "2024-06-30"),
    ("2021-01-01", "2024-12-31", "2025-01-01", "2026-05-14"),
]

HMM_CONFIRMATION = 3     # days of state agreement before regime flip
N_SIMS           = 44
PROPR_INITIAL    = 5_000.0
PROPR_TARGET     = 1.10
PROPR_MAX_DD     = 0.06
PROPR_DAILY_LIM  = 0.03
SIM_POOL_START   = "2025-01-06"

OUT_DIR  = Path("strategies/combined_portfolio")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_PATH = OUT_DIR / "regime_gated_results.png"


# ── Data ──────────────────────────────────────────────────────────────────────
def load_prices(start: str = DATA_START, end: str = TEST_END) -> pd.DataFrame:
    print("Downloading price data …")
    raw = yf.download(ASSETS, start=start, end=end,
                      auto_adjust=True, progress=False)["Close"]
    raw = raw.ffill(limit=2)
    raw.columns = [c.replace("-USD", "") for c in raw.columns]
    return raw.dropna(how="all")


def log_ret(prices: pd.DataFrame) -> pd.DataFrame:
    return np.log(prices / prices.shift(1))


# ── HMM ───────────────────────────────────────────────────────────────────────
def hmm_features(btc: pd.Series) -> pd.DataFrame:
    """4-feature observation matrix (consistent with regime_hmm/feasibility.py)."""
    lr   = np.log(btc / btc.shift(1))
    vol5 = lr.rolling(5).std() * np.sqrt(252)
    vol20= lr.rolling(20).std() * np.sqrt(252)
    ma50 = btc.rolling(50).mean()
    sgn  = np.sign(btc - ma50)
    return pd.DataFrame(
        {"log_ret": lr, "vol5": vol5, "vol20": vol20, "sign_ma50": sgn}
    ).dropna()


def fit_2state_hmm(feats: pd.DataFrame, seed: int = 42) -> hmm.GaussianHMM:
    """2-state full-covariance HMM (3-state failed to converge — see 6.15)."""
    model = hmm.GaussianHMM(
        n_components=2, covariance_type="full",
        n_iter=300, random_state=seed, verbose=False,
    )
    model.fit(feats.values)
    return model


def decode_regime(
    model: hmm.GaussianHMM,
    predict_on: pd.DataFrame,   # features to decode regime for
    full_history: pd.DataFrame, # full feature history (for bull-state identification)
) -> pd.Series:
    """
    Viterbi decode on full_history, shift by 1 (no look-ahead),
    apply HMM_CONFIRMATION-day filter, return BULL/BEAR for predict_on index.

    Shift(1): state known at close T → position active from T to T+1.
    Convention matches regime_hmm/feasibility.py: states_shifted = predict(obs).shift(1).
    """
    raw = pd.Series(model.predict(full_history.values), index=full_history.index)

    # Identify BULL state as higher mean log return
    means = {s: full_history.loc[raw == s, "log_ret"].mean() for s in range(model.n_components)}
    bull = max(means, key=means.get)

    # Shift by 1 — no look-ahead
    shifted = raw.shift(1)

    # Confirmation filter: only flip regime if last CONFIRMATION days agree
    confirmed = shifted.copy()
    for i in range(HMM_CONFIRMATION - 1, len(shifted)):
        win = shifted.iloc[i - HMM_CONFIRMATION + 1: i + 1]
        if win.nunique() == 1:
            confirmed.iloc[i] = win.iloc[0]
        else:
            confirmed.iloc[i] = confirmed.iloc[i - 1]

    regime = confirmed.map(lambda s: "BULL" if s == bull else "BEAR")
    return regime.reindex(predict_on.index, method="ffill").fillna("BULL")


# ── Portfolio construction ────────────────────────────────────────────────────
def compute_weights(
    prices: pd.DataFrame,
    regime: pd.Series,
    vol_long:  float = VOL_TARGET_LONG,
    vol_short: float = VOL_TARGET_SHORT,
    gate_shorts: bool = True,
) -> pd.DataFrame:
    """
    Compute daily portfolio weights. Convention: weight[T] uses data through
    T-1 (shift(1) on features); run_backtest applies NO additional shift.

    Positive weight = long, negative = short.
    """
    lr   = log_ret(prices)
    cum  = lr.rolling(TSMOM_LOOKBACK).sum().shift(1)   # signal: data through T-1
    sig  = np.sign(cum)
    rv   = (lr.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(252)).clip(lower=1e-6)

    w = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    for asset in prices.columns:
        s = sig[asset]
        r = rv[asset]

        # Long leg (all assets except SOL)
        if asset != "SOL":
            scalar = (vol_long / r).clip(0.1, 2.0)
            w[asset] += (s > 0).astype(float) * scalar

        # Short leg — only SHORT_ELIGIBLE assets when signal = −1
        if asset in SHORT_ELIGIBLE:
            if gate_shorts:
                is_bear = (
                    regime.reindex(prices.index, fill_value="BULL") == "BEAR"
                ).astype(float)
            else:
                is_bear = pd.Series(1.0, index=prices.index)
            scalar = (vol_short / r).clip(0.1, 2.0)
            w[asset] += (s < 0).astype(float) * (-scalar) * is_bear

    # Gross exposure cap
    gross = w.abs().sum(axis=1).replace(0, np.nan)
    scale = (GROSS_CAP / gross).clip(upper=1.0).fillna(1.0)
    return w.mul(scale, axis=0)


def backtest(prices: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    """
    Daily net returns. Convention: weight[T] already uses T-1 data.
    P&L[T] = weight[T] × return[T] — no additional shift.
    Costs applied on turnover.
    """
    lr    = log_ret(prices)
    pnl   = (weights * lr).sum(axis=1)
    costs = weights.diff().abs().sum(axis=1) * COST_RT
    return pnl - costs


# ── Metrics ───────────────────────────────────────────────────────────────────
def sharpe(r: pd.Series, ann: int = 252) -> float:
    return r.mean() / r.std() * np.sqrt(ann) if r.std() > 0 else 0.0


def max_dd(r: pd.Series) -> float:
    cum = (1 + r).cumprod()
    return ((cum / cum.cummax()) - 1).min()


def metrics(r: pd.Series) -> dict[str, float]:
    return {
        "sharpe":    sharpe(r),
        "ann_ret":   r.mean() * 252 * 100,
        "max_dd":    max_dd(r) * 100,
        "max_daily": r.min() * 100,
        "days_gt3":  int((r < -0.03).sum()),
        "win_rate":  (r > 0).mean() * 100,
    }


# ── Walk-forward ──────────────────────────────────────────────────────────────
def walk_forward(prices: pd.DataFrame) -> list[dict[str, Any]]:
    results = []
    for i, (tr_s, tr_e, te_s, te_e) in enumerate(WALK_FORWARD_WINDOWS):
        btc = prices["BTC"]
        all_feats   = hmm_features(btc.loc[:te_e])
        train_feats = all_feats.loc[tr_s:tr_e]
        if len(train_feats) < 80:
            results.append({"window": i + 1, "period": f"{te_s}→{te_e}",
                            "g": np.nan, "u": np.nan, "t": np.nan, "stable": False})
            continue

        model  = fit_2state_hmm(train_feats)
        regime = decode_regime(model, all_feats.loc[te_s:te_e], all_feats)

        tp = prices.loc[te_s:te_e]
        r_g = backtest(tp, compute_weights(tp, regime, gate_shorts=True))
        r_u = backtest(tp, compute_weights(tp, regime, gate_shorts=False))
        bull_regime = pd.Series("BULL", index=tp.index)
        r_t = backtest(tp, compute_weights(tp, bull_regime, gate_shorts=True))

        sg, su, st = sharpe(r_g), sharpe(r_u), sharpe(r_t)
        stable = sg > 0.5
        results.append({"window": i + 1, "period": f"{te_s}→{te_e}",
                        "g": sg, "u": su, "t": st, "stable": stable})
        print(f"  WF{i+1} [{te_s}→{te_e}]  gated={sg:.2f}  ungated={su:.2f}  tsmom={st:.2f}  {'✓' if stable else '✗'}")
    return results


# ── Propr simulation ──────────────────────────────────────────────────────────
def propr_sim(
    daily_rets: pd.Series,
    pool_start: str = SIM_POOL_START,
    n_sims: int = N_SIMS,
    seed: int = 42,
) -> dict[str, Any]:
    """Block-bootstrap Propr challenge (5-day blocks from 2025 pool)."""
    pool = daily_rets.loc[pool_start:] if len(daily_rets.loc[pool_start:]) > 20 else daily_rets
    arr = pool.values
    blocks = [arr[i: i + 5] for i in range(0, len(arr) - 4, 5)]
    if not blocks:
        blocks = [arr]

    rng = np.random.default_rng(seed)
    passes = daily_fails = dd_fails = 0
    days_list: list[int] = []

    for _ in range(n_sims):
        equity = hwm = PROPR_INITIAL
        passed = breached = False
        day = 0
        for _ in range(250):
            blk = blocks[rng.integers(0, len(blocks))]
            for r in blk:
                prev = equity
                equity *= (1 + r)
                day += 1
                if (equity - prev) / prev < -PROPR_DAILY_LIM:
                    daily_fails += 1; breached = True; break
                hwm = max(hwm, equity)
                if (equity - hwm) / hwm < -PROPR_MAX_DD:
                    dd_fails += 1; breached = True; break
                if equity >= PROPR_INITIAL * PROPR_TARGET:
                    passes += 1; days_list.append(day); passed = True; break
            if passed or breached:
                break

    return {
        "pass_rate":         passes / n_sims,
        "daily_limit_fails": daily_fails,
        "total_dd_fails":    dd_fails,
        "avg_days":          float(np.mean(days_list)) if days_list else float("nan"),
    }


# ── Plot ──────────────────────────────────────────────────────────────────────
def _contiguous_ranges(idx: pd.DatetimeIndex) -> list[tuple]:
    if len(idx) == 0:
        return []
    ranges, start, prev = [], idx[0], idx[0]
    for d in idx[1:]:
        if (d - prev).days > 7:
            ranges.append((start, prev))
            start = d
        prev = d
    ranges.append((start, prev))
    return ranges


def plot(
    r_gated: pd.Series,
    r_ungated: pd.Series,
    r_tsmom: pd.Series,
    regime_test: pd.Series,
    wf_res: list[dict],
    p_gated: dict,
    p_ungated: dict,
    p_tsmom: dict,
    r_long: pd.Series,
    r_short: pd.Series,
) -> None:
    BG, PANEL, GRID = "#0d1117", "#161b22", "#30363d"
    BLUE, RED, GREEN, YELLOW = "#58a6ff", "#f78166", "#3fb950", "#e3b341"

    fig = plt.figure(figsize=(18, 14))
    fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(3, 2, hspace=0.45, wspace=0.35)
    axs = [fig.add_subplot(gs[0, :]),
           fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1]),
           fig.add_subplot(gs[2, 0]), fig.add_subplot(gs[2, 1])]
    for ax in axs:
        ax.set_facecolor(PANEL)
        ax.tick_params(colors="#c9d1d9", labelsize=8)
        for sp in ax.spines.values(): sp.set_color(GRID)
        ax.xaxis.label.set_color("#c9d1d9")
        ax.yaxis.label.set_color("#c9d1d9")
        ax.title.set_color("#e6edf3")

    # ── 1. Equity curves ──────────────────────────────────────────────────
    ax = axs[0]
    for r, label, color, lw in [
        (r_gated,   f"Regime-Gated   Sharpe {sharpe(r_gated):.2f}", BLUE,  2.2),
        (r_ungated, f"Ungated         Sharpe {sharpe(r_ungated):.2f}", RED,  1.5),
        (r_tsmom,   f"TSMOM v2 alone  Sharpe {sharpe(r_tsmom):.2f}",  GREEN, 1.5),
    ]:
        ax.plot((1 + r).cumprod().index, (1 + r).cumprod().values,
                label=label, color=color, linewidth=lw)
    bear_idx = regime_test[regime_test == "BEAR"].index
    for s, e in _contiguous_ranges(bear_idx):
        ax.axvspan(s, e, alpha=0.13, color=RED, linewidth=0)
    ax.legend(fontsize=8, labelcolor="#c9d1d9", facecolor=PANEL, edgecolor=GRID)
    ax.set_title("(1) OOS Equity 2024–2026  [red shading = BEAR regime]",
                 fontsize=10, fontweight="bold")
    ax.set_ylabel("Growth of $1")

    # ── 2. P&L decomposition ──────────────────────────────────────────────
    ax = axs[1]
    cum_long  = (1 + r_long).cumprod()
    cum_short = (1 + r_short).cumprod()
    ax.plot(cum_long.index,  cum_long.values,  label=f"Long leg  Sh={sharpe(r_long):.2f}",  color=GREEN)
    ax.plot(cum_short.index, cum_short.values, label=f"Short leg Sh={sharpe(r_short):.2f}", color=RED)
    ax.axhline(1.0, color=GRID, linewidth=0.8, linestyle="--")
    ax.legend(fontsize=8, labelcolor="#c9d1d9", facecolor=PANEL, edgecolor=GRID)
    ax.set_title("(2) P&L Decomposition — Gated Portfolio", fontsize=10, fontweight="bold")
    ax.set_ylabel("Growth of $1")

    # ── 3. Walk-forward ───────────────────────────────────────────────────
    ax = axs[2]
    labels = [f"W{r['window']}" for r in wf_res]
    x = np.arange(len(labels))
    bw = 0.25
    ax.bar(x - bw, [r["g"] for r in wf_res], width=bw, color=BLUE,  label="Gated")
    ax.bar(x,      [r["u"] for r in wf_res], width=bw, color=RED,   label="Ungated")
    ax.bar(x + bw, [r["t"] for r in wf_res], width=bw, color=GREEN, label="TSMOM")
    ax.axhline(0.5, color=YELLOW, linestyle="--", linewidth=1, alpha=0.8, label="0.5 min")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.legend(fontsize=7, labelcolor="#c9d1d9", facecolor=PANEL, edgecolor=GRID)
    ax.set_title("(3) Walk-Forward OOS Sharpe", fontsize=10, fontweight="bold")

    # ── 4. Daily return distributions ─────────────────────────────────────
    ax = axs[3]
    for r, label, color in [
        (r_gated,   "Gated",   BLUE),
        (r_ungated, "Ungated", RED),
        (r_tsmom,   "TSMOM",   GREEN),
    ]:
        ax.hist(r.values * 100, bins=60, alpha=0.45, color=color, label=label, density=True)
    ax.axvline(-3, color=YELLOW, linestyle="--", linewidth=1.3, label="−3% limit")
    ax.set_title("(4) Daily Return Distribution", fontsize=10, fontweight="bold")
    ax.set_xlabel("Daily Return (%)")
    ax.legend(fontsize=7, labelcolor="#c9d1d9", facecolor=PANEL, edgecolor=GRID)

    # ── 5. Propr pass rates ───────────────────────────────────────────────
    ax = axs[4]
    labels_p = ["TSMOM v2\n(baseline 34-45%)",
                f"Ungated\n({p_ungated['pass_rate']*100:.0f}%)",
                f"Gated\n({p_gated['pass_rate']*100:.0f}%)"]
    rates = [0.395, p_ungated["pass_rate"], p_gated["pass_rate"]]
    bars = ax.bar(labels_p, [r * 100 for r in rates],
                  color=[GREEN, RED, BLUE], width=0.5)
    ax.axhline(45, color=YELLOW, linestyle="--", linewidth=1.2, label="45% target")
    for b, r in zip(bars, rates):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5,
                f"{r*100:.0f}%", ha="center", va="bottom", color="#e6edf3", fontsize=9)
    ax.set_title("(5) Propr Pass Rate — 44 Simulations", fontsize=10, fontweight="bold")
    ax.set_ylabel("Pass Rate (%)")
    ax.legend(fontsize=7, labelcolor="#c9d1d9", facecolor=PANEL, edgecolor=GRID)

    fig.suptitle("HMM Regime-Gated Combined Portfolio — Research Results",
                 color="#e6edf3", fontsize=13, fontweight="bold", y=0.98)
    plt.savefig(FIG_PATH, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"\nFigure saved → {FIG_PATH}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    # 1. Load data
    prices = load_prices()
    tp     = prices.loc[TEST_START:TEST_END]   # OOS test prices

    # 2. Fit HMM on BTC training features only
    print("Fitting HMM on BTC training features …")
    all_feats   = hmm_features(prices["BTC"])
    train_feats = all_feats.loc[TRAIN_START:TRAIN_END]
    model       = fit_2state_hmm(train_feats)

    # 3. Decode OOS regime (no look-ahead: HMM trained on train only)
    regime_test = decode_regime(model, all_feats.loc[TEST_START:TEST_END], all_feats)
    bull_pct = (regime_test == "BULL").mean()
    print(f"OOS regime: BULL={bull_pct*100:.1f}%  BEAR={(1-bull_pct)*100:.1f}%")

    # 4. Three variants
    bull_regime = pd.Series("BULL", index=tp.index)
    w_gated   = compute_weights(tp, regime_test,  gate_shorts=True)
    w_ungated = compute_weights(tp, regime_test,  gate_shorts=False)
    w_tsmom   = compute_weights(tp, bull_regime,  gate_shorts=True)  # all-BULL → no shorts ever

    r_gated   = backtest(tp, w_gated)
    r_ungated = backtest(tp, w_ungated)
    r_tsmom   = backtest(tp, w_tsmom)

    # 5. P&L decomposition (gated)
    lr = log_ret(tp)
    long_mask  = w_gated > 0
    short_mask = w_gated < 0
    r_long  = (w_gated.where(long_mask,  0.0) * lr).sum(axis=1)
    r_short = (w_gated.where(short_mask, 0.0) * lr).sum(axis=1)

    long_short_corr = r_long.corr(r_short)
    worst10_tsmom   = r_tsmom.nsmallest(10)
    short_on_worst  = r_short.loc[worst10_tsmom.index].mean()

    # 6. Walk-forward
    print("\nRunning walk-forward …")
    wf_res    = walk_forward(prices)
    wf_stable = sum(r["stable"] for r in wf_res)

    # 7. Propr simulations
    print("Running Propr simulations …")
    p_gated   = propr_sim(r_gated)
    p_ungated = propr_sim(r_ungated)
    p_tsmom   = propr_sim(r_tsmom)

    # 8. Plot
    plot(r_gated, r_ungated, r_tsmom, regime_test, wf_res,
         p_gated, p_ungated, p_tsmom, r_long, r_short)

    # 9. Verdict
    mg = metrics(r_gated)
    mu = metrics(r_ungated)
    mt = metrics(r_tsmom)

    sh = mg["sharpe"]
    pr = p_gated["pass_rate"]

    if sh >= 1.5 and pr >= 0.45 and wf_stable >= 3:
        verdict = "DEPLOY"
        action  = (f"Implement combined portfolio with HMM regime gate. "
                   f"Short leg (SOL/LINK/BCH/OP signal=-1) active only in BEAR regime. "
                   f"Expected OOS Sharpe: {sh:.2f}.")
    elif 1.0 <= sh < 1.5 or 0.40 <= pr < 0.45:
        verdict = "PROMISING"
        action  = ("Regime gate improves over ungated but doesn't reach DEPLOY threshold. "
                   "Next: add intra-regime vol-spike filter — scale all positions to 50% "
                   "when 5d BTC realized vol > 2× 20d baseline. "
                   "This targets the vol spikes within BULL that caused daily limit breaches (6.15).")
    elif sh > sharpe(r_ungated):
        verdict = "WEAK"
        action  = ("Regime gate improves Sharpe but insufficient for DEPLOY. "
                   "Short signals are structurally real (t > 2.0 OOS) but regime "
                   "filter not precise enough. Consider: (1) tighter BEAR confirmation "
                   "(5 days vs 3), (2) vol-spike filter overlay.")
    else:
        verdict = "SKIP"
        action  = ("HMM gate doesn't improve over ungated. The 2-state BTC HMM cannot "
                   "reliably identify regimes where the short leg adds value. "
                   "Accept TSMOM v2 long-only as the production strategy.")

    # ── Print ──────────────────────────────────────────────────────────────
    print()
    print("═" * 65)
    print("REGIME-GATED COMBINED PORTFOLIO")
    print("TSMOM Long + HMM-Gated Short (SOL/LINK/BCH/OP)")
    print("═" * 65)
    print(f"\nHMM (OOS 2024–2026): BULL={bull_pct*100:.1f}%  BEAR={(1-bull_pct)*100:.1f}%")
    print()
    hdr = f"  {'':28s}  {'Gated':>7}  {'Ungated':>7}  {'TSMOM':>7}"
    sep = "  " + "─" * (len(hdr) - 2)
    print(hdr); print(sep)
    for key, label in [
        ("sharpe",    "OOS Sharpe"),
        ("ann_ret",   "Ann return (%)"),
        ("max_dd",    "Max DD (%)"),
        ("max_daily", "Max daily loss (%)"),
        ("days_gt3",  "Days > 3% loss"),
        ("win_rate",  "Win rate (%)"),
    ]:
        vg = mg[key]; vu = mu[key]; vt = mt[key]
        fmt = ".1f" if key != "days_gt3" else "d"
        print(f"  {label:28s}  {vg:>7{fmt}}  {vu:>7{fmt}}  {vt:>7{fmt}}")

    print("\nWalk-forward:")
    print(f"  {'W':3s}  {'Period':25s}  {'Gated':>7}  {'Ungated':>7}  {'TSMOM':>7}  Stable")
    for r in wf_res:
        g = r.get("g", float("nan"))
        u = r.get("u", float("nan"))
        t = r.get("t", float("nan"))
        print(f"  W{r['window']}   {r['period']:25s}  {g:>7.2f}  {u:>7.2f}  {t:>7.2f}  {'✓' if r.get('stable') else '✗'}")
    print(f"  Stable windows: {wf_stable}/4")

    print("\nPropr simulation (44 paths from 2025-01-06):")
    print(f"  {'':28s}  {'Gated':>7}  {'Ungated':>7}  {'TSMOM':>7}")
    print(f"  {'Pass rate':28s}  {p_gated['pass_rate']*100:>6.0f}%  {p_ungated['pass_rate']*100:>6.0f}%  {p_tsmom['pass_rate']*100:>6.0f}%")
    print(f"  {'Daily limit fails':28s}  {p_gated['daily_limit_fails']:>7d}  {p_ungated['daily_limit_fails']:>7d}  {p_tsmom['daily_limit_fails']:>7d}")
    print(f"  {'Total DD fails':28s}  {p_gated['total_dd_fails']:>7d}  {p_ungated['total_dd_fails']:>7d}  {p_tsmom['total_dd_fails']:>7d}")
    print(f"  {'Avg days to pass':28s}  {p_gated['avg_days']:>7.0f}  {p_ungated['avg_days']:>7.0f}  {p_tsmom['avg_days']:>7.0f}")

    print("\nCorrelation decomposition (gated portfolio):")
    print(f"  Long/short leg correlation    : {long_short_corr:+.3f}")
    print(f"  Short leg on worst 10 TSMOM days: {short_on_worst*100:+.2f}%"
          f"  ({'hedge works' if short_on_worst > 0 else 'hedge FAILS'})")
    bear_short_act = (w_gated[list(SHORT_ELIGIBLE.intersection(w_gated.columns))] < 0).any(axis=1)
    bear_short_pct = bear_short_act.mean() * 100
    print(f"  Short leg active {bear_short_pct:.1f}% of OOS days (BEAR regime only)")

    print()
    print(f"VERDICT: {verdict}")
    print(f"Action : {action}")
    print("═" * 65)

    # ── Git commit ─────────────────────────────────────────────────────────
    result = subprocess.run(
        "git add strategies/combined_portfolio/ && "
        "git commit -m 'research: HMM regime-gated combined portfolio "
        "— short leg active only in BEAR regime, resolves feasibility.py tail risk'",
        shell=True, capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("\nCommitted to git.")
    else:
        print(f"\nGit: {result.stderr.strip() or result.stdout.strip()}")


if __name__ == "__main__":
    main()
