# Volet 0 — findings (interim, 2026-07-14)

## Part B (audited engine) — margin-cap-uncapping REFUTED at model weights
At eq=INIT, scale=14 (taper=glide=pace=1), over the engine's 13y real gold/J1 weight distribution:
- US100 22:05 notional = **$84,000 (8.4×) in ALL regimes** (full/diversified, mono-sleeve, and
  post-restamp US100+GER40). Reason: US100's own margin footprint = 8.4×·2% = **0.168·eq**, always
  far below the 0.60·eq cap → the cap never bridles US100 *by itself*.
- The 60% cap BINDS on only **17% of ON-nights** (need/eq median 0.43), driven by gold+J1 on high-
  weight days; even then US100 is scaled at most to ~5.2× (ratio mono/full ≤ **1.6×** on those 17%,
  **1.00× on the median night**).
- **The monday_restamp does NOT re-bridle US100** (US100+GER40 need = 0.336·eq < 0.60 → no cap).
⇒ The precise mechanical hypothesis "cap uncapping makes US100 bigger alone" is **not the dominant
driver** (M0b-mechanism ratio 1.00× median, ≤1.6× conditional — below the pre-registered 1.5× except
on the ~17% highest-gold/J1 nights). **Sub-mechanism (b2-i) rejected as dominant.**

## Part A (real fills) — data-integrity WALL: fills.csv is NOT a reliable position ledger
- `state.json` now: equity **$9,238.64**, **positions EMPTY** (flat), open_days 4, flat_today 1.
- Naive fill netting from 06/17 gives USDJPY accumulating to 3.53 lots "held" through the loss nights
  — but this is an **artifact**: the account was **RESET on 2026-06-24** (reconcile: −$1014.72,
  equity→$10,000.00), and there are **no USDJPY close fills logged** after 07/02 despite the account
  being flat now. ⇒ `fills.csv` misses closes / spans a reset → cannot reconstruct overnight
  composition from it. M0a/M0b-real are **not computable from fills alone**; need reconcile/deal
  history.

## Reconcile log — the RELIABLE live signal (and a degraded-ops discovery)
Real daily PnL (reconcile, fallback close-state; the −$402 of 07/14 not yet reconciled today):
- 07/06 **+$480.44** (US100 opened, day gain) → 07/07 **−$354.14** (overnight loss + breaker).
- 07/13 −$103.15 (daytime) → 07/14 loss pending.
- **07/07: real −$354.14 vs MODEL −$378.11** (residual +$24.82) → the loss magnitude is **model-
  consistent** (the sim also loses ~$378 that day) ⇒ preliminary support for **no gross
  implementation gap** (variance/size, not a bug). To be confirmed by K1b real-path replay.
- **Degraded ops (notable in its own right):** EVERY night "DÉGRADÉ — snapshot EOD 22:58 absent, EA
  freeze ~22:54"; large unexplained model residuals (Δsignal $80k–190k, INEXPLIQUÉ 5–6/3); reset
  06/24. The clean sim≡live assumption holds on the loss days but the nightly reconciliation is noisy.

## Where this leaves Hb2
- **(b2-i) cap uncapping → REJECTED as dominant** (Part B).
- **(b2-ii) diversification loss** (same US100 size, but no decorrelated legs to dampen book vol →
  breaker fires more) — **STILL OPEN**, testable via sim (M0c: force J1/gold=0 vs full, compare book
  vol/maxDD/p(pass)) without the broken fills.
- The book IS reduced post-gate (gold 0 fills all period, J1 gated) — qualitatively fewer legs — but
  the *harm* mechanism is diversification (b2-ii), not physical US100 up-sizing (b2-i).

## Pivot
Adjudicate via the RELIABLE audited-engine analysis: Volet 1 (nightly US100 distribution + K1a +
K1b real-size/real-path replay) + M0c (mono-sleeve vs diversified book vol/maxDD). Do NOT rely on
the fills reconstruction for composition; use reconcile daily PnL for the live anchor.
