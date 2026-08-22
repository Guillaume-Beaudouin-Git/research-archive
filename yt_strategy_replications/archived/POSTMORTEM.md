# Archived strategies — DO NOT re-propose without strong new evidence

One-line kill reasons. Full evidence in `../reports/`. Code retained in each module folder for reference.

## Module 1 — crypto 5-minute "scalping" (5 strategies) — ALL FAIL
Tested on 18 liquid USDT pairs, 2021–2026, 0.17% round-trip.
- **S1 Momentum breakout + vol filter** — no edge even gross (Sharpe −0.18); net −6.2. 0/18 pairs +.
- **S2 SMA 50/100 cross** — no edge gross (−0.24); net −10.9; over-trades (4,171/pair/yr).
- **S3 EMA/SMA + z-score** — gross edge +0.7 bp/trade; break-even cost 0.74 bp ≪ 17 bp reality.
- **S4 Body-fraction breakout** — no edge gross (−0.37); net −7.0.
- **S5 VWMA buy-the-dip ("+5,381%")** — gross +0.8 bp/trade; break-even 0.84 bp; net −4.6.
- **Root cause:** simple MA/breakout rules have ≤1 bp/trade gross edge, crushed by costs; the advertised returns are cost-free, single-instrument, 50k-search selection bias.

## Module 2 — pin-bar / rejection candle + EMA trend filter (gold H1) — FAIL
- Faithful replication; trend filter genuinely halves drawdown, but the underlying edge is **insignificant even gross** (HAC t +0.5 over 19y, +0.9 over 6y), **dies above ~2 bp**, and is **net-negative on 0/8 instruments** (significantly negative on FX).
- **Root cause:** a single-candle pattern is not a standalone alpha. The base idea is replaced — see `../gold_research/`.

## Module 4 — pairs trading BRK-B / MSFT (daily) — FAIL
- "0.97 correlation" was spurious **price-level** correlation (true return corr 0.49); cointegration "passes" full-sample but holds in **1 of 16** individual years (look-ahead selection); all three OOS variants net-negative (−0.11 to −0.15 Sharpe).
- **Root cause:** two unrelated equities have no structural convergence force (lesson L27, beta trap). Consistent with repo prior "pairs 0/19 qualify".

## Module 5 — partial archives
- **Blind Opening-Range Breakout (NQ, 1:1, no filter)** — net Sharpe −0.57; the directional skew is +5% long / −5% short, below the cost line. (The *filtered* version lives on as repo Strategy C, marginal.)
- **Congressional copy-trading** — historical-only, eroded by the 45-day disclosure lag, and the pitch is ex-post selected (Pelosi named because she won). Low conviction; data-gated.
