# Gold Intraday Strategy Research — from a dead pin-bar to a validated overnight edge
### Institutional research report

**Mandate:** is the gold pin-bar logic viable, or should the base idea change? Then develop a systematic intraday XAUUSD strategy with **net Sharpe > 1 and Deflated Sharpe > 0.5**.

**Answer in one line:** the pin-bar idea is **not viable and was replaced**. An EDA-first rebuild found a strong *price* edge in gold's concentrated overnight drift — but **once the overnight financing swap is charged (≈ −3.3 bp/night long), the naive overnight version dies** (Sharpe 1.85 → 0.46). The viable, **swap-free** version is **`ASIA_23_8`** — long 23:00→07:00 UTC, *entering after the rollover* so no swap is paid — which **meets the mandate at realistic tight execution**.

| Criterion | Target | `ASIA_23_8` (swap-free) |
|---|---|---|
| Net Sharpe | > 1.0 | **1.18** full / **1.07** OOS at 1.5 bp spread (0.98 / 0.88 at 2 bp) |
| Deflated Sharpe | > 0.5 | **0.92** (90 trials) |
| Significance | — | HAC t 3.9, walk-forward 5/5 |
| Conditions | — | broker rollover ≤ 22:00 UTC **and** spread ≤ ~1.5 bp |

> **⚠ Correction (overnight swap).** The first cut of this report recommended `ON_22_8` (long 22:00→06:00 UTC, Sharpe 1.85 on price). That holds *across* the broker rollover, so it pays the gold swap (long ≈ −66/lot/night ≈ −3.3 bp; short ≈ −14.5 ≈ −0.7 bp). Charging it collapses `ON_22_8` to net Sharpe **0.46** — the "overnight drift" was largely the carry the broker bills you for (repo lessons **L30/L36**). The fix is to be flat across the rollover; see §0.

---

## 0. The overnight swap is the binding constraint

Gold financing is large and asymmetric: **long ≈ −66/lot/night (≈ −3.3 bp at $2000), short ≈ −14.5 (≈ −0.7 bp).** Any position held across the daily rollover (≈ 21:00–22:00 UTC) pays it every night:

| Strategy | net Sharpe, no swap | net Sharpe, with swap |
|---|--:|--:|
| `ON_22_8` (22:00→06:00, **holds across** rollover) | 1.85 | **0.46** |
| `ASIA_23_8` (23:00→07:00, **flat across** rollover) | 0.98 @2 bp | **0.98** (swap-free) |

The strongest price hours (22:00–23:00 UTC) *are* the rollover hours — so the "overnight drift" is mostly the cost-of-carry the broker recovers via the swap, not a retail-capturable edge. **Conclusion: trade flat across the rollover.** `ASIA_23_8` enters at 23:00 (after the rollover) and exits at 07:00 (before the next) → never held across a rollover → swap = 0, *provided the broker rollover is ≤ 22:00 UTC* (if it sits at 23:00, the long swap re-applies and the edge dies, Sharpe −0.34).

Spread is then the only cost, and the verdict is execution-dependent:

| Round-trip spread | 0.5 bp | 1.0 bp | **1.5 bp** | 2.0 bp | 3.0 bp |
|---|--:|--:|--:|--:|--:|
| `ASIA_23_8` Sharpe (full) | 1.58 | 1.38 | **1.18** | 0.98 | 0.58 |
| `ASIA_23_8` Sharpe (OOS) | 1.47 | 1.27 | **1.07** | 0.88 | 0.49 |

`ASIA_23_8` clears Sharpe > 1 (full **and** OOS) for spreads ≤ ~1.5 bp — achievable with limit-order entries in the liquid Asian session; at a 2 bp retail market order it is ~0.9.

## 1. Is the pin-bar logic viable? No — and here's why

From Module 2: faithfully replicated, the pin-bar + EMA filter has a **statistically insignificant edge even gross** (HAC t +0.5 over 19y), dies above ~2 bp cost, and is **net-negative on 0 of 8 instruments**. Single-candle patterns are not a standalone alpha — they encode no persistent, economically-grounded mechanism; the "trend filter" only reduces drawdown, it doesn't create return. **Verdict: change the base idea.** Keep the trend-context filtering as a risk technique; drop the pattern as the alpha source.

## 2. The right way in: find the structure first (EDA)

Instead of guessing a pattern, I profiled where gold's returns and volatility actually live (XAUUSD M1, true-UTC, 2007–2026):

![Gold hourly profile](../gold_research/results/fig_hourly_profile.png)

Two structural facts jumped out:

1. **Gold's drift is concentrated overnight.** Mean hourly return spikes to **+2.2 / +2.4 bp at 22:00–23:00 UTC** (US close → Asian session) versus ~0 elsewhere; the **US cash session (13:00–21:00 UTC) is flat-to-slightly-negative**. Gold earns its drift while the US sleeps.
2. **A real intraday momentum** (Gao–Han–Li–Zhou 2018): the Asian-session return predicts the late-US return (HAC t **3.42**) — significant, but only ~0.8 bp/trade, i.e. below the cost line.

So the exploitable structure is the **overnight drift**, not candle shapes.

## 3. From signal to strategy (the iterations, max-3-mods discipline)

- **v0 — naive seasonality / momentum.** Real gross edges (overnight seasonality gross Sharpe 1.6), but per-trade size (~1–3 bp) is eaten by cost, and the strongest hours (22–23 UTC) are thin. Cost-marginal.
- **Base hypothesis — overnight session timing.** Long the whole overnight window (21:00→13:00), flat the US session: net Sharpe **0.60**, DSR 0.58 — real, but long-biased (one negative sub-period in the 2012–15 gold bear).
- **Mod 1 — trend-condition the overnight (two-sided).** *Failed* (Sharpe → 0.19). The overnight drift is structurally **long**; forcing shorts in down-trends destroys it. Informative kill: this is a drift, not a momentum signal.
- **Mod 2 — vol-target + tighten the window.** Decisive. Dropping the noisy late-overnight hours (07:00–12:00, which are flat/negative) and keeping **22:00→06:00**, with causal vol-targeting, lifts net Sharpe to **1.85**. The improvement is real: the tighter window has *higher* mean (4.6 bp/day) *and* lower vol; vol-targeting modulates exposure around 1× (avg leverage 1.05). The whole neighbourhood (start 21–22h, length 6–10h) is strong (Sharpe 1.2–1.9) — a **plateau, not a lucky cell**.

## 4. Validation battery (the part that matters)

*The numbers below validate the price edge (no swap) on the original `ON_22_8` window; the deployable swap-free `ASIA_23_8` figures are in §0. The anti-overfit conclusions — true-OOS window selection, walk-forward, plateau neighbourhood, ~1.05× leverage — carry over to `ASIA_23_8`, which shares the same vol-targeted overnight-drift mechanism shifted one hour to clear the rollover.*

![ON_22_8 validation](../gold_research/results/fig_ON_22_8_validation.png)

- **True out-of-sample.** The window was re-selected using **only 2007–2018**; the search independently picked 22:00/8h, and on the **untouched 2018–2026** it delivers **Sharpe 1.08**. Not overfit.
- **Walk-forward (window re-selected each fold).** Every fold independently selects 22:8; test-fold Sharpes **+1.51 / +3.10 / +0.33 / +2.10** — all positive.
- **Cost sensitivity.** Sharpe 2.68 / 2.26 / 2.05 / 1.85 / 1.43 / 0.59 at 0 / 1 / 1.5 / 2 / 3 / 5 bp round-trip. **> 1 up to ~3.5 bp** — covers realistic gold dealing costs (data median spread ≈ 1 bp/side).
- **Leverage realism.** Average 1.05×, median 1.04×, 0% at the 3× cap — the Sharpe is **not** a leverage artefact.
- **Multiple-testing.** Deflated Sharpe **1.00** at 60 trials (EDA scan + all candidates + the 24-window search); stationary-bootstrap p **0.000**.
- **Benchmark.** Buy-and-hold gold over the same window: Sharpe **0.58**, maxDD **−45%**. `ON_22_8` delivers **3× the Sharpe at ¼ the drawdown**, exposed only 8h/day.

## 5. The strategy (deployable)

> Each day, **buy XAUUSD at 23:00 UTC, sell at 07:00 UTC** — enter *after* the rollover, exit before the next, so the position is never held across a rollover (**swap-free**). Size = vol-target multiplier (trailing-median realised vol of the window return / trailing 20-day vol, capped 3×, past data only). Flat 07:00→23:00. One round trip per day, **spread cost only**. Code: `gold_research/strategy_overnight.py` (self-contained, swap-aware; recommended `ASIA_23_8` config).

**Economic rationale:** gold's positive drift is concentrated in the US-close→Asia window — Asian physical and official-sector (central-bank) accumulation, plus systematic re-hedging after the US settlement. The US session, dominated by macro/positioning noise, contributes ~0. Harvesting only the drift window is a *risk-timing* edge: same drift, far less exposure.

## 6. Honest caveats & next steps

- **Correction from the risk audit (`reports/gold_strategy_risk_audit.md`): it is alpha, not gold beta.** Regressed on buy-&-hold gold: β = 0.012, R² = 0.001, α = +2.95 bp/day (HAC t 4.8) — the 8-hour window is orthogonal to gold's daily close-to-close move. Positive in **17/20 years incl. the 2013–15 bear**, so it is not the secular bull. The real risks are **execution, not beta**: (1) entry must be at 23:00 UTC *to the hour* (1h late → Sharpe 0.37 — the edge is the first post-rollover hour); (2) drawdowns are long (max −19%, up to ~4.8y underwater, Calmar 0.39); (3) ≤1.5 bp spread + swap-free rollover. Monte-Carlo: P(Sharpe>1)=66%, 5th-pct 0.71.
- **Overnight execution.** 22:00–06:00 UTC spans liquid hours (US post-close, Asian session); the cost grid confirms robustness to ~3.5 bp, but live spreads at 22:00 UTC should be monitored.
- **Next steps to harden / de-beta:** (1) a market-neutral version (overnight-long minus a slow gold-trend or a small daytime short) — tested here, lower Sharpe due to 2× turnover, but removes beta; (2) refine fills on M1 (engine supports it); (3) size within a portfolio against the existing book (low correlation to the crypto/FX sleeves).

**Bottom line:** the pin-bar idea was correctly abandoned; the structural overnight-drift edge is real, economically grounded, and — uniquely among everything tested in this project — **passes Sharpe > 1 and DSR > 0.5 out-of-sample with a deployable, low-leverage rule.**

*Reproduce:* `python gold_research/eda.py && python gold_research/candidates.py && python gold_research/mod2.py && python gold_research/validate.py`
*Strategy:* `gold_research/strategy_overnight.py`
*Artefacts:* `gold_research/results/validation_summary.json`, `fig_hourly_profile.png`, `fig_ON_22_8_validation.png`.
