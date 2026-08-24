# J1 leverage-cap study — VERDICT

**Backtest verdict: ADOPT LCAP8 as a systematic rule** (cap `|notional_J1|/eq ≤ 8×`).
**Live decision (Q4): the cap does NOT make this weekend's position safe — suspend the J1 leg
while USDJPY is in the defended zone IN ADDITION to coding the cap.** Both are true.

Baseline EQUIV PASS (462/462, pooled 87.01 — anchor-exact; the cap hook is inert at `j1_lev_cap=0`).
Independent author≠auditor pass: CONFIRM-WITH-CAVEATS (6/6 numeric checks PASS).

> **Decision artifact note:** the verdict here follows the FROZEN asymmetric rule in
> `PREREGISTRATION.md`, evaluated in **`decision_prereg.json` (ADOPT=LCAP8)**. The file
> `tables/decision.json` is produced by the inherited v2.3 `aggregate.py`, whose gate requires a
> CI-significant POSITIVE p/EV improvement (says "NULL") — that is NOT this study's pre-registered
> rule and is superseded by `decision_prereg.json`.

## Q1 — procyclical regime (measured, pre-reg)
`notional_J1 = w_jpy·scale·eq`, `w_jpy∈[0,1.5]` saturates at 1.5 when `rvj ≤ 6.67%`, `scale≈vm(14)`.
Realized J1 leverage by rvj percentile: **P0-20 (compression) median 21.1× (max 29.1×)** vs
**P80-100 (high vol) 11.7× (max 16.0×)** — monotone procyclicality confirmed. 65% of active J1
days >15×, 30% >20×. **Caveat:** worst in-sample gaps were NOT in compression (Grexit −$2,822 @
rvpct 0.38; NK-missile −$871 @ 0.41; SVB −$633 @ 0.95) → a regime-agnostic hard cap is expected
to dominate a compression-only cap. Latest observable regime (2026-06-05): rvj 43rd pct (moderate).

## Q2-Q3 — caps backtested (paired vs baseline, 90% circular block-bootstrap, N_eff 174)

| arm | p_pooled | Δp (90% CI) | EV | ΔEV (90% CI) | worst gap | worst J1 day | gap busts | lev med/max | risk_jpy |
|---|---|---|---|---|---|---|---|---|---|
| **baseline** | 87.0 | — | $926 | — | **−$2,822** | −$2,824 | 34 | 16.8/30.3× | 0.288 |
| **LCAP8** | 85.5 | −1.5 [−6.3;+2.8] | $927 | **+$1.3 [−75;+76]** | **−$1,129** | −$1,449 | 29 | 8.0/10.0× | 0.135 |
| LCAP10 | 84.9 | −2.2 [−7.4;+2.8] | $910 | −$16 [−106;+71] | −$1,411 | −$1,449 | 26 | 10.0/12.5× | 0.170 |
| LCAP12 | 82.2 | −4.8 [−10.2;+0.7] | $861 | −$65 [−157;+25] | −$1,792 | −$1,793 | **18** | 12.0/15.8× | 0.214 |
| COMPRESS | 85.7 | −1.3 [−3.5;+0.4] | $915 | −$11 [−48;+22] | **−$2,822** | −$2,824 | 26 | 13.3/30.3× | 0.252 |

**Decision rule (frozen) applied:**
1. *Tail improves materially* — hard caps cut the worst weekend gap by **37-60%** (LCAP8 −60%,
   LCAP12 −37%) and hard-cap leverage (p95/max collapse to the cap); LCAP12 halves gap busts
   (34→18). ✓ for LCAP8/10/12.
   **COMPRESS FAILS the tail test** — worst gap/day unchanged (−$2,822/−$2,824), max lev still
   30.3× — because the catastrophic gaps were NOT in compression (Q1 confirmed). Rejected.
2. *p/EV not CI-significantly destroyed* — all hard caps' Δp/ΔEV 90% CIs include 0 (none below the
   −2.0pt / −$40 guards). ✓ Point estimates lean negative (Δp −1.5 to −4.8) but are within noise
   at N_eff 174; LCAP12-worse-than-LCAP8 is non-monotone = sampling noise, not signal.
3. *Lowest cap passing the guard* → **LCAP8**.

**Why LCAP8 wins**: near-zero campaign cost (Δp −1.5 ns, **ΔEV +$1.3 ≈ 0**) — the bust/attempt
reduction offsets the slightly lower funded rate — while cutting the worst gap **−60%** and
halving J1's risk share (0.288→0.135) WITH the decorrelation preserved (corr J1-vs-rest 0.020).
It beats a uniform J1×0.5 (v2.3 A_raw) because it cuts ONLY the procyclical high-leverage days,
leaving normal-vol days untouched. The cap separates the tail from the diversification — better
than Q1 feared.

**Honest limits (retrospective):** Δp point estimates are all negative; "ns" = can't distinguish
from 0, not "proven free". The book's single worst DAY (−$7,078) is the OVERNIGHT sleeve, untouched
by any J1 cap — J1 caps address the J1 gap tail, not the book's worst-case day.

## Q4 — does the cap make THIS weekend's position acceptable? **NO.**
Live: 1.8 lots ≈ $180k = 18× on $10k. FTMO limits: daily $500, total floor $1,000. Per-yen ≈ $1,113.

| config | notional | $/yen | 3-yen gap | 5-yen gap | verdict |
|---|---|---|---|---|---|
| LIVE 18× | $180k | $1,112 | −$3,337 | −$5,562 | BUST / BUST |
| LCAP10 | $100k | $618 | −$1,854 | −$3,090 | BUST / BUST |
| **LCAP8** | **$80k** | **$494** | **−$1,483** | **−$2,472** | **BUST / BUST** |

To survive a 3-yen gap within the floor you need **≤5.4×**; a 5-yen gap **≤3.2×**; within the daily
limit **≤2.7× / ≤1.6×**. **The 8× cap reduces the loss ~55% but still BUSTS on a 3-yen intervention**
— the $1,000 floor is simply too tight for any leverage above ~5× against a multi-yen gap.

**Prospective judgment (NOT from the backtest):** the engine's worst gap (~2.5 yen) UNDERSTATES a
coordinated BoJ-MoF-US intervention (3-5+ yen, unprecedented since 2011). The cap is the correct
structural FOND rule, but for the acute event this weekend it is insufficient. → **Code LCAP8 AND
suspend/flatten the J1 leg while USDJPY sits under the defended 161.95** (a documented risk
exception; campaign cost of skipping entries ≈ 0 per the v2.3 ablation — diversification is an
aggregate-of-attempts property, not a single-entry one).

Trial accounting: +5 arms (equiv+baseline+LCAP8/10/12+COMPRESS) to the v2-program ledger; 1 frozen
rule, 0 post-hoc arms. NOT deployed; live book untouched (read-only).
