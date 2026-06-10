# REPORT — H3: Day-of-week × session directional seasonal (FX majors)

**Status:** CLOSED. **Verdict: DEAD — no cost-beating intraday-flat seasonal.** The WF day-of-week sleeve is
net −4.27 Sharpe; the single net-positive standout (EURUSD-London-Friday) is a **decayed pre-2015 regime
artifact** (F6 trap), at the chance-expected-max-t of a 100-cell scan. **Cumulative N after H3: 240**
(140 + 100 scan cells; see `N_ledger.md`).

---

## 1. Hypothesis (frozen — PRE_REGISTRATION.md ADDENDUM 2)

Decisive falsification: is there ANY intraday-flat, swap-free day-of-week × session directional seasonal in
FX majors that survives real cost + DSR deflation at cumulative N? 100 cells = 10 FX × 5 weekdays × 2
sessions (London 07→16, NY 13→20 UTC). Each cell counted toward N (→ N=240).

## 2. Scan result — `results/h3_phase1_scan.json`

| metric | value | gate | verdict |
|---|---:|---|---|
| WF day-of-week sleeve net Sharpe | **−4.27** | > floor 0.631 | ❌ cost-killed |
| sleeve DSR(P) @ N=240 | 0.00 | > 0.5 | ❌ |
| sleeve p(pass) FTMO | 0.0002 | — | ❌ dead |
| cells with \|gross-t\|>2.5 | **2 of 100** | — | ≈ chance (E[max-t₁₀₀]=2.53) |
| cells net-positive after cost | 3 of 100 | — | selection noise |
| best gross cell | EURUSD-London-Fri, t=−2.53 | — | **exactly at the luck ceiling** |

- The WF sleeve trades every session (~500 RT/yr) → cost dominates → −4.27 Sharpe. As a tradeable *system*,
  the seasonal is dead.
- Only **2/100** cells reach |t|>2.5 (chance among 100 ≈ 1.2); the best (|t|=2.53) equals the chance-expected
  maximum-t for 100 cells (2.53) → indistinguishable from selection. The other (EURJPY-NY-Wed, t=+3.28) is
  **net −0.02 bps** (cost ate the 3.7-bps gross).

## 3. The one net-positive standout — characterized, not chased

EURUSD London-session on **Fridays** is systematically down (gross −3.5 bps, t −2.53; shorting nets +1.94
bps/trade, ~50/yr; GBPUSD echoes it at −3.3 bps → a generic EUR/GBP USD-strength-into-the-weekend pattern).
**But it is a decayed regime artifact** (the TSMOM-K200 / F6 trap):

| sub-period | Friday London gross | NW-t |
|---|---:|---:|
| 2007–2009 | **−8.21 bps** | −1.78 |
| 2010–2015 | −4.83 bps | −1.76 |
| 2016–2020 | −2.95 bps | −1.38 |
| 2021–2026 | **−0.05 bps** | **−0.02** |

- **Monotonic decay to zero.** Full-history short-Friday net Sharpe 0.668 ≈ noise floor 0.631 (at the floor →
  deflated nothing); **recent (≥2016) net Sharpe = −0.011** (dead). Consistent with L23 (microstructure
  edges erased by algoization/reform). **Not a forward edge — not promotable.**

## 4. Verdict

**H3 = DEAD.** No intraday-flat FX seasonal beats cost + deflation; the only net-positive cell is a decayed
pre-2015 artifact at the 100-cell luck ceiling. The decisive falsification fires: **the retail FX
intraday-flat space is now burned across all three orthogonal angles** (H1 reversal / H2 news-drift / H3
seasonality). See `SYNTHESIS.md`.

### What's burned now
- **H3 intraday-flat day-of-week × session FX seasonal** — no cost-beating cell; best is a decayed artifact.
  Do not re-test as a retail strategy. The EURUSD/GBPUSD Friday USD-into-weekend bias is **real-historical but
  decayed to zero post-2015** (documented, dead forward).
