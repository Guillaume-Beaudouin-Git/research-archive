"""TEST 1 — DSR du survivant. HAC lag-sweep, skew/kurt, trial-SR dispersion,
Bailey-Lopez de Prado DSR, bootstrap CI. Per-trade basis (comme la formule du brief)."""
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy.stats import norm, skew, kurtosis
from pathlib import Path

ROOT = Path("<HOME>/Desktop/Algo_claude")
s = pd.read_parquet(ROOT / "outputs/audit_month_end/data/survivor_trades.parquet")
net = s["net"].values
N = len(net)
mean, sd = net.mean(), net.std(ddof=1)
SR = mean / sd
print(f"N={N}  mean_net={mean*100:+.3f}%  sd={sd*100:.3f}%  SR/trade={SR:.4f}")

# --- HAC lag sweep (finding: reported 2.55 == plain t, real HAC(6) < 2.5) ---
print("\n[HAC lag sweep on net]")
for L in [0, 1, 2, 3, 4, 6, 8]:
    res = sm.OLS(net, np.ones((N, 1))).fit(cov_type="HAC", cov_kwds={"maxlags": L})
    tag = " (=plain)" if L == 0 else ""
    print(f"  lag {L}: t = {res.tvalues[0]:.3f}{tag}")

g3 = float(skew(net, bias=False))
g4 = float(kurtosis(net, fisher=False, bias=False))  # normal->3
print(f"\nskew={g3:+.3f}  kurtosis(normal=3)={g4:.3f}")

# --- Trial SR list (per-trade, from report t/sqrt(N)); ABSENT N_ledger -> reconstructed ---
# (spec, N, t, note). SR_trade = t/sqrt(N). Estimates flagged.
trials = [
    ("F1a ORB 00:00", 2652, -9.63, "given"),
    ("F1b ORB 13:30", 2366, -10.04, "given"),
    ("F2 US-session", 3073, -5.86, "given"),
    ("F3 pre-event", 168, -0.67, "given"),
    ("TSM intraday uncond", 2500, -6.0, "est (~breakout family, -19bps)"),
    ("TSM vol-conditional", 250, 1.9, "est N; t<=1.9 given"),
    ("RSI2 oversold", 400, 0.05, "est ~0 (gross +0.34bps)"),
    ("IBS oversold", 400, 0.05, "est ~0"),
    ("VWAP oversold", 400, 0.05, "est ~0"),
    ("Options expiry daily", 300, 0.3, "est ~0 (momentum, falsified)"),
    ("Options expiry weekly", 150, 0.3, "est ~0"),
    ("Options expiry monthly", 28, 2.5, "= survivor origin (given t~2.5)"),
    ("Hour-of-day", 2900, 0.2, "est ~0 (artifact only)"),
    ("Overnight 21-23", 2900, 3.64, "given t; N=daily"),
    ("Turn-of-candle", 3000, 0.1, "est ~0 (~cost)"),
    ("Cross-asset lead-lag", 1000, 0.2, "est ~0 (HFT)"),
    ("Funding-window", 1000, 0.1, "est ~0 (killed)"),
    ("Cross pooling monthly (DOGE)", 28, 3.18, "given; correlated w/ survivor"),
    ("Alpha-vs-beta placebo ord.", 594, -2.98, "given (placebo)"),
]
sr_trials = np.array([t / np.sqrt(n) for (_, n, t, _) in trials])
print("\n[trial per-trade SR]")
for (nm, n, t, note), sr in zip(trials, sr_trials):
    print(f"  {nm:32s} N={n:5d} t={t:+.2f} -> SR={sr:+.4f}   {note}")
sd_all = sr_trials.std(ddof=1)
# variant excluding the 2 survivor-correlated positives (monthly expiry, DOGE)
mask = np.array([nm not in ("Options expiry monthly", "Cross pooling monthly (DOGE)")
                 for (nm, _, _, _) in trials])
sd_excl = sr_trials[mask].std(ddof=1)
print(f"\nsd(SR_trials) all19 = {sd_all:.4f}   |   excl 2 survivor-dupes = {sd_excl:.4f}")


def dsr(SR_obs, sd_trials, Ntrials, T, g3, g4):
    gamma = 0.5772156649
    z1 = norm.ppf(1 - 1.0 / Ntrials)
    z2 = norm.ppf(1 - 1.0 / (Ntrials * np.e))
    SR0 = sd_trials * ((1 - gamma) * z1 + gamma * z2)
    denom = np.sqrt(1 - g3 * SR_obs + (g4 - 1) / 4.0 * SR_obs**2)
    z = (SR_obs - SR0) * np.sqrt(T - 1) / denom
    return norm.cdf(z), SR0

print("\n[DSR — Bailey/Lopez de Prado, per-trade]")
for label, sdv in [("sd_all19", sd_all), ("sd_excl_dupes", sd_excl)]:
    for Nt in [19, 24, 40]:
        d, sr0 = dsr(SR, sdv, Nt, N, g3, g4)
        print(f"  {label:14s} N_trials={Nt:2d}: SR0={sr0:.4f}  DSR={d:.4f}")

# --- Bootstrap CI on mean net (iid, 10k) ---
rng = np.random.default_rng(42)
boot = rng.choice(net, size=(10000, N), replace=True).mean(axis=1)
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"\n[bootstrap 10k] mean_net 95% CI = [{lo*100:+.3f}%, {hi*100:+.3f}%]  P(mean>0)={(boot>0).mean():.3f}")
print(f"  (point mean_net = {mean*100:+.3f}%)")
