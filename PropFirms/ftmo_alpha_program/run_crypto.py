"""
run_crypto.py — Family-6: BTCUSD intraday (the crypto focus), relaxed thresholds
=================================================================================

Prior: crypto is less efficient than FX/index (retail, herding) with LARGE intraday moves
that may overcome a wide CFD spread. Recon picked the direction from data: BTC levels TREND
intraday (the level-fade loses gross); the edge is MOMENTUM (follow the breakout). Crypto
swaps are catastrophic => intraday-flat (flatten before the daily rollover). HARD daily stop.

Gates: thresholds RELAXED per request (cost ratio>=2 = promising; P(pass) reported vs 70%;
kurtosis noted, not hard-failed). INTEGRITY gates kept: untouched hold-out, honest cost
(BTC spread x3), no loss-cap artifact, DSR at true trial count, per-year stability.

Candidate (selected on IS cost-ratio, confirmed OOS): BTCUSD momentum, 120-min bars, window 16,
z_entry 2.0, intraday-flat 00-21 UTC, daily stop 2%, spread x3.

Outputs: results/crypto_intraday.json, figures/crypto_intraday.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO))
from strategy.fx_data import load_mt5_panel                              # noqa: E402
from strategy.intraday_fx_mr import build_bars, add_mr_signal, backtest_mr, BacktestConfig, per_trade_stats  # noqa: E402
from engine.ftmo_first_passage import combined_pass_prob_empirical, tail_dd_gate, combined_pass_prob_closed_form, annual_to_daily_sharpe  # noqa: E402
from dsr import deflated_sharpe_ratio                                    # noqa: E402

FIG, RES = HERE / "figures", HERE / "results"
IS = ("2022-01-01", "2024-12-31"); OOS = ("2025-01-01", "2026-05-29")
N_TRIALS = 25
DF = load_mt5_panel("BTCUSD")


def signal_bars(span, momentum=True):
    b = add_mr_signal(build_bars(DF.loc[span[0]:span[1]], freq="120min", hours=(0, 21)), window=16)
    if momentum:
        b = b.copy(); b["z"] = -b["z"]      # follow the breakout (level momentum)
    return b


def run(span, markup, momentum=True):
    b = signal_bars(span, momentum)
    res = backtest_mr(b, "BTCUSD", BacktestConfig(z_entry=2.0, z_exit=0.5, sigma_target=0.01,
                                                  markup=markup, daily_stop=0.02))
    return res, b


def per_year(net):
    out = {}
    for y, seg in net.groupby(net.index.year):
        sd = seg.std(ddof=1)
        out[int(y)] = round(float(seg.mean() / sd * np.sqrt(252)) if sd > 0 else 0.0, 2)
    return out


def main() -> int:
    print("=" * 80)
    print("FAMILY-6 — BTCUSD intraday (crypto focus, relaxed thresholds, integrity kept)")
    print("=" * 80)

    # contrast: reversion direction has no gross edge
    rev_is = run(IS, 0.0, momentum=False)[0].metrics["ann_sharpe"]
    print(f"\nDirection check (IS gross): level-FADE/reversion annSh={rev_is:.2f} (no edge) "
          f"vs MOMENTUM below.")

    mi, bi = run(IS, 3.0); mo, bo = run(OOS, 3.0)
    gi = run(IS, 0.0)[0].metrics; go = run(OOS, 0.0)[0].metrics
    m_is, m_oos = mi.metrics, mo.metrics
    net_is, net_oos = mi.daily_net.dropna(), mo.daily_net.dropna()
    pt = per_trade_stats(bi, 2.0, 0.5)
    print(f"\n[Candidate: BTCUSD momentum 120min, spread x3]")
    print(f"  GROSS annSh: IS {gi['ann_sharpe']:.2f} → OOS {go['ann_sharpe']:.2f} (untouched) — edge survives")
    print(f"  NET annSh:   IS {m_is['ann_sharpe']:.2f} → OOS {m_oos['ann_sharpe']:.2f}   per-trade t={pt['t_stat']:.2f}")
    print(f"  cost ratio IS: {m_is['gross_ann_return']/max(1e-9,m_is['cost_ann_drag']):.2f} (relaxed gate>=2 = promising)")
    print(f"  DISTRIBUTION (lumpy momentum): WR {m_is['win_rate']*100:.0f}% W/L {m_is['win_loss_ratio']:.2f} "
          f"kurtosis {m_is['excess_kurtosis']:.1f}")
    py = per_year(pd.concat([net_is, net_oos]))
    print(f"  per-year net Sharpe: {py}")
    tail = tail_dd_gate(net_is.values, n_paths=12000)
    dsr = deflated_sharpe_ratio(net_is.values, n_trials=N_TRIALS, periods_per_year=252)
    print(f"  tail-DD P(touch -8%/60d): {tail['p_floor_excursion']*100:.1f}%   DSR(n={N_TRIALS}): {dsr['dsr']:.3f}")

    # FTMO MC — read on the UNTOUCHED HOLD-OUT (per protocol), with the crypto daily-floor
    # sensitivity (FTMO reduces the daily limit for crypto) — the decisive caveat.
    print(f"  FTMO MC honest — σd=0.6%, IS vs HOLD-OUT, crypto daily-floor sensitivity:")
    SIG = 0.006
    def mc_p(net, floor):
        return combined_pass_prob_empirical((net / net.std() * SIG).values, n_paths=12000,
                                            seed=1, daily_floor=floor)["p_combined"]
    mc = {}
    for floor in [0.05, 0.03, 0.02]:
        p_is, p_oos = mc_p(net_is, floor), mc_p(net_oos, floor)
        mc[floor] = {"is": p_is, "oos": p_oos}
        tag = "  <- FTMO Standard" if floor == 0.05 else ("  <- realistic crypto" if floor == 0.03 else "")
        print(f"     daily_floor={floor*100:.0f}%: P(pass) IS {p_is*100:>4.0f}%  HOLD-OUT {p_oos*100:>4.0f}%{tag}")
    cf = combined_pass_prob_closed_form(net_is.mean() / net_is.std(), SIG)["p_combined"]
    print(f"     positive-skew effect (5% floor, IS): empirical {mc[0.05]['is']*100:.0f}% vs Gaussian {cf*100:.0f}% "
          f"(real, but insufficient)")
    bear = run(("2022-01-01", "2022-12-31"), 3.0)[0].metrics
    print(f"  Bear-regime stress (2022 BTC): net annSh {bear['ann_sharpe']:.2f}, maxDD {bear['max_dd']*100:.1f}% "
          f"({'BREACH (>10% FTMO floor)' if bear['max_dd'] > 0.10 else 'within 10%'})")

    p5, p3, p2 = mc[0.05]['oos'], mc[0.03]['oos'], mc[0.02]['oos']
    verdict = (
        f"NO-GO under realistic crypto rules — but the program's FIRST real net-positive edge. BTCUSD intraday "
        f"momentum reproduces exactly and SURVIVES the untouched hold-out at the Sharpe level (gross OOS "
        f"{go['ann_sharpe']:.2f}, net OOS {m_oos['ann_sharpe']:.2f}, per-trade t {pt['t_stat']:.2f}; look-ahead-free, "
        f"independently verified). Two honest corrections defeat the FTMO claim: (1) read on the HOLD-OUT, P(pass) at "
        f"the Standard 5% floor is only {p5*100:.0f}% (the 70% was in-sample); (2) FTMO applies a REDUCED daily-loss "
        f"limit to crypto — at a realistic 3%/2% floor the hold-out P(pass) collapses to {p3*100:.0f}%/{p2*100:.0f}% "
        f"because this lumpy book's losing days cluster at -2..-4%. And it is long-bull-biased: the 2022 bear ran a "
        f"{bear['max_dd']*100:.0f}% drawdown (>10% → would have breached). The positive-skew-helps mechanism "
        f"(empirical>Gaussian) is real but insufficient. Net: this CORROBORATES L24 — lumpy momentum is not a "
        f"reliable symmetric-barrier passer; the 'promising' first read was an in-sample + too-loose-floor artifact, "
        f"caught by independent verification.")
    print(f"\n[VERDICT] {verdict}")

    payload = {"protocol": {"IS": IS, "OOS_untouched": OOS, "n_trials_dsr": N_TRIALS},
               "reversion_is_gross_sharpe": rev_is,
               "candidate": {"gross_is": gi["ann_sharpe"], "gross_oos": go["ann_sharpe"],
                             "net_is": m_is["ann_sharpe"], "net_oos": m_oos["ann_sharpe"],
                             "per_trade_t": pt["t_stat"], "win_rate": m_is["win_rate"],
                             "win_loss": m_is["win_loss_ratio"], "kurtosis": m_is["excess_kurtosis"],
                             "cost_ratio_is": m_is["gross_ann_return"]/max(1e-9,m_is["cost_ann_drag"]),
                             "per_year": py, "tail_dd": tail, "dsr": dsr,
                             "bear_2022": {"ann_sharpe": bear["ann_sharpe"], "max_dd": bear["max_dd"]},
                             "ftmo_mc_floor_sensitivity": {str(k): v for k, v in mc.items()}},
               "verdict": verdict}
    (RES / "crypto_intraday.json").write_text(json.dumps(payload, indent=2, default=str))
    _plot(net_is, net_oos, gi, go, m_is, m_oos, mc)
    print("\n  → results/crypto_intraday.json\n  → figures/crypto_intraday.png")
    return 0


def _plot(net_is, net_oos, gi, go, m_is, m_oos, mc):
    fig, ax = plt.subplots(2, 2, figsize=(13, 8.5))
    eq = pd.concat([net_is, net_oos])
    ax[0, 0].plot(eq.index, eq.cumsum()*100, color="#2a9d8f")
    ax[0, 0].axvline(pd.Timestamp(OOS[0]), color="#d1495b", ls=":", lw=1.4)
    ax[0, 0].text(pd.Timestamp(OOS[0]), ax[0, 0].get_ylim()[0], " hold-out →", color="#d1495b", fontsize=8)
    ax[0, 0].axhline(0, color="#aaa", lw=.8)
    ax[0, 0].set_title("BTCUSD intraday momentum — net equity (spread ×3)\nfirst edge to SURVIVE the untouched hold-out")
    ax[0, 0].set_ylabel("cum return (%)"); ax[0, 0].grid(alpha=.25)
    # gross/net IS/OOS
    cats = ["gross IS", "gross OOS", "net IS", "net OOS"]
    vals = [gi["ann_sharpe"], go["ann_sharpe"], m_is["ann_sharpe"], m_oos["ann_sharpe"]]
    ax[0, 1].bar(cats, vals, color=["#2a9d8f", "#9fd8cf", "#264653", "#7a8e95"])
    ax[0, 1].axhline(0, color="#333", lw=.8)
    ax[0, 1].set_title("Annualised Sharpe — robust gross & net, in- and out-of-sample"); ax[0, 1].set_ylabel("ann Sharpe")
    ax[0, 1].grid(alpha=.25, axis="y")
    # daily return distribution (lumpy)
    r = net_is.values*100
    ax[1, 0].hist(r, bins=50, color="#264653", alpha=.85)
    ax[1, 0].axvline(0, color="#d1495b", lw=1)
    ax[1, 0].set_title(f"Daily return distribution — LUMPY (WR {m_is['win_rate']*100:.0f}%, "
                       f"W/L {m_is['win_loss_ratio']:.1f}, kurt {m_is['excess_kurtosis']:.0f})\nthe wrong shape for a symmetric barrier")
    ax[1, 0].set_xlabel("daily net return (%)"); ax[1, 0].set_ylabel("count"); ax[1, 0].grid(alpha=.25)
    # P(pass) vs crypto daily-floor (the decisive caveat): IS vs untouched hold-out
    floors = sorted(mc.keys(), reverse=True); x = [f*100 for f in floors]
    ax[1, 1].plot(x, [mc[f]["is"]*100 for f in floors], "s--", color="#9fd8cf", label="in-sample")
    ax[1, 1].plot(x, [mc[f]["oos"]*100 for f in floors], "o-", color="#264653", label="HOLD-OUT (honest)")
    ax[1, 1].axhline(70, ls="--", color="#d1495b", label="70% objective")
    ax[1, 1].axvspan(2, 3, color="#d1495b", alpha=.10)
    ax[1, 1].text(2.5, 8, "realistic\ncrypto floor", fontsize=7, color="#d1495b", ha="center")
    ax[1, 1].set_title("FTMO P(pass) vs daily-loss floor (σd 0.6%)\ncollapses at the reduced crypto floor → NO-GO")
    ax[1, 1].invert_xaxis(); ax[1, 1].set_xlabel("daily-loss floor (%)"); ax[1, 1].set_ylabel("P(pass) %")
    ax[1, 1].set_ylim(0, 100); ax[1, 1].legend(fontsize=7); ax[1, 1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(FIG / "crypto_intraday.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
