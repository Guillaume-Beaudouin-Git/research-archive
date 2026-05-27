# Engine Audit — Phase 1.2

**Run date:** 2026-05-28

## Leverage distribution (active days only)

| Metric | Value |
|--------|-------|
| Mean | 0.922 |
| Median | 0.890 |
| P10 | 0.452 |
| P25 | 0.656 |
| P75 | 1.143 |
| P90 | 1.438 |
| Max | 2.346 |
| Days in cash | 7.6% |

**Interpretation:** leverage is below 1.0 most of the time
(median 0.89×). Vol-target 15% ann / asset vol typically > 15%
for equity ETFs → lever < 1. Vol spikes in crises compress leverage further.

## Cushion-ratchet from LLM report

**Report spec:** `lev = clip(base_lev + ratchet_coeff × (equity − 1), 0, cap)`
  where base_lev=2.5×, ratchet_coeff=25, cap=0.045/daily_stop

**engine.py (actual):**
```python
lever = min(vol_target / sig_vol, vol_cap)   # line ~74
# sig_vol = trailing 40-day realized vol of the SELECTED ASSET
# vol_target = 0.15 ann, vol_cap = 3.0
```

| Check | Result |
|-------|--------|
| Ratchet term `ratchet_coeff × (equity − 1)` present? | **NO** |
| Base leverage 2.5× hardcoded? | **NO** (vol-derived, median 0.89) |
| Cap as function of daily stop? | **NO** (cap = vol_cap = 3.0) |
| Leverage equity-conditional? | **NO** — f(asset vol), not f(equity path) |

**Conclusion:** Cushion-ratchet is **ABSENT** from the current engine.
The LLM report's ratchet amplifies leverage as equity rises (trend-following on PnL),
which would increase FTMO pass probability by hitting targets faster when ahead.
This is to be tested in **Phase 2 by ablation (L19)** against the rescaled baseline.

## FTMO daily loss barrier check

Engine daily stop: 1.2% on non-levered return, max leverage 3.0×.
Max strategy daily loss (leveraged) = 3.6% < FTMO 5% limit.
→ FTMO daily loss barrier is structurally unreachable under the current engine constraints.
Expected simulation fail_daily ≈ 0%.