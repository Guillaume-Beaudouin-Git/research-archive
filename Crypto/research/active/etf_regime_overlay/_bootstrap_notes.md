# Bootstrap Notes — ETF Flows + Stablecoin Regime Overlay
*Date: 2026-05-23 | Mission: Strategy A enhancement via macro liquidity regime filter*
*Phase 0 only — GATE 0 STOP below. Budget: n_tests 156 → 159 (+3 max).*

---

## 1. Mission Framing

This is **not** a standalone alpha research mission. The deliverable is a **multiplicative overlay** on Strategy A (TSMOM v3) that turns the long-only position ON or OFF based on a macro crypto liquidity regime score. 

Success criterion: `Sharpe(A_filtered) / Sharpe(A_unfiltered) > 1.10` on OOS walk-forward, post-ETF era (Jan 2024+) only.

The overlay cannot improve gross returns when active — it can only remove unfavorable periods. If it works, it does so by suppressing whipsaws during low-liquidity regimes (net ETF outflows + stablecoin supply stagnation), when TSMOM momentum signals are more likely to be false positives.

---

## 2. Data Architecture

### 2a. Farside BTC ETF Flows

**Source**: `https://farside.co.uk/bitcoin-etf-flow-all-data/`  
**Access method**: `requests.get()` with browser-mimicking User-Agent + BeautifulSoup HTML table parse  
**Cloudflare status**: Site returns 403 without headers. Required header:
```python
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://farside.co.uk/",
}
```
If 403 persists with correct headers → trigger STOP condition, archive with note "data source fragile: Farside Cloudflare blocks automated scraping".

**Table structure** (from Farside X posts and confirmed column list):
- Date column: `YYYY-MM-DD` format (first column)
- ETF columns (12 as of 2026): `IBIT`, `FBTC`, `BITB`, `ARKB`, `BTCO`, `EZBC`, `BRRR`, `HODL`, `BTCW`, `GBTC`, `BTC` (Grayscale Mini), `MSBT` (added ~Jan 2025)
- `Total` column: last column, sum of all ETF flows
- Units: US$ millions, float
- Zero flow day: `0` (market open, no flow)
- Missing/weekend/holiday: `"-"` or empty string → parse as `NaN`, then `dropna` for weekends
- Data range: **2024-01-11** (first ETF trading day) → present

**Parse notes**:
- Numbers may have commas as thousands separators (e.g., `"1,234.5"`) → `str.replace(",", "").strip()`
- Dash characters: `"-"` → `NaN`; note en-dash `"–"` may also appear
- `MSBT` column absent before its launch date → handle with `pd.DataFrame.reindex(columns=...)` defaulting to NaN

**GBTC note**: GBTC had anomalously large outflows in Jan–Feb 2024 (conversion from trust format), dominating the early total net flow. Use both `net_flow_all` and `net_flow_ex_gbtc` (sum excluding GBTC) as candidate inputs; document in PHASE 2 which is more predictive.

**Cache**: `data/etf_flows_raw.parquet` — columns: Date (index), one per ETF ticker, `net_flow_all` (sum), `net_flow_ex_gbtc`

```python
# Scraping skeleton
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

URL = "https://farside.co.uk/bitcoin-etf-flow-all-data/"
ETF_COLS = ["IBIT", "FBTC", "BITB", "ARKB", "BTCO", "EZBC", "BRRR", "HODL", "BTCW", "GBTC", "BTC", "MSBT", "Total"]

def fetch_farside_etf_flows() -> pd.DataFrame:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()  # raises on 403/4xx/5xx
    soup = BeautifulSoup(resp.content, "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError("No table found in Farside page — HTML structure may have changed")
    rows = table.find_all("tr")
    ...  # parse header row, then data rows
```

---

### 2b. DeFiLlama Stablecoin Supply

**Base URL**: `https://stablecoins.llama.fi`  (note: NOT `api.llama.fi`)  
**Free API, no authentication required**

**Endpoint 1 — Total aggregate stablecoin supply (preferred)**:
```
GET https://stablecoins.llama.fi/stablecoincharts/all
```
Returns: `[{"date": unix_timestamp, "totalCirculating": {"peggedUSD": float}, ...}, ...]`  
Date range: Nov 2017 → present (daily)  
Use: `df["supply"] = df["totalCirculating"].apply(lambda x: x["peggedUSD"])`

USDT+USDC ≈ 85% of total stablecoin market cap → `totalCirculating` is a valid proxy for USDT+USDC supply.

**Endpoint 2 — USDT-specific** (if USDT+USDC isolation required):
```
GET https://stablecoins.llama.fi/stablecoin/1   # USDT (ID confirmed = 1)
GET https://stablecoins.llama.fi/stablecoin/2   # USDC (ID confirmed = 2)
```
Warning: response >10MB (per-chain daily breakdown) — use streaming + filter to global circulating only:
```python
r = requests.get(url, stream=True, timeout=60)
data = r.json()  # parse in full — or use ijson for streaming
df = pd.DataFrame(data["tokens"])  # or relevant key — verify structure in PHASE 2
```
Fallback: if individual stablecoin endpoint is too slow, use `stablecoincharts/all` exclusively.

**Cache**: `data/stablecoin_supply_raw.parquet` — columns: Date (index), `total_supply_usd`, and optionally `usdt_supply`, `usdc_supply`

**Rate limit**: DeFiLlama public API documented as "billions of requests per month" — no key required, no rate limit for research-scale usage. Add `time.sleep(0.5)` between calls as courtesy.

---

## 3. Regime Score Hypothesis

### Formulation

Let `t` be a calendar day. All signals are computed strictly from T-1 data (available at open of T).

```
# Step 1 — ETF flow signal
flow_7d(t)  = Σ_{k=0}^{6} net_flow_all(t-k)       # 7-day rolling sum, US$M
flow_z(t)   = z_score(flow_7d, window=30d)          # 30d rolling mean/std normalization

# Step 2 — Stablecoin supply signal
Δstable_7d(t) = (supply(t) - supply(t-7)) / supply(t-7)   # 7-day growth rate
stable_z(t)   = z_score(Δstable_7d, window=30d)

# Step 3 — Composite regime score
regime_score(t) = 0.5 × flow_z(t) + 0.5 × stable_z(t)
```

**Rolling window choice (30d)**: longer than the 7d signal smoothing to capture medium-term regime; shorter than typical bull/bear cycle length (3-12 months) to remain responsive. This partially addresses L12b autocorrelation risk — the z-score normalizes against local history rather than computing a global IC across the full sample. HAC lag-6 mandatory for all statistical tests.

**Equal weighting (0.5/0.5)**: no optimization, justified by equal prior plausibility of both signals as liquidity proxies. Do not tune weights — this is a fixed ex-ante design decision.

### Rationale

Post-ETF (Jan 2024+), BTC price and TSMOM signal are correlated with institutional flows and stablecoin liquidity. In low-liquidity regimes (net outflows from ETFs, stagnant/declining stablecoin supply), TSMOM signals based on 28-day momentum are more likely to trigger on noise rather than real regime momentum:
- Net ETF outflows → institutional de-risking signal → trend likely exhausted or reversing
- Stablecoin supply flat/declining → less fresh capital entering crypto → fewer buyers to sustain momentum

The overlay does not predict the direction of BTC returns — it only decides whether the macro environment is consistent with TSMOM being in a reliable regime.

---

## 4. Overlay Architecture

### Pattern

```python
# Crypto/research/active/etf_regime_overlay/engine.py

from strategies.tsmom_v2_propfirm.signal import compute_signal, apply_weekly_rebalance
from strategies.tsmom_v2_propfirm.sizing import compute_vol_scalars, compute_positions
from strategies.tsmom_v2_propfirm.config import LOOKBACK_DAYS, VOL_LOOKBACK_DAYS, REBALANCE_WEEKDAY

def compute_regime_score(
    etf_flows: pd.Series,      # daily net ETF flow (US$M), index=Date
    stable_supply: pd.Series,  # daily total stablecoin supply (USD), index=Date
    flow_smooth: int = 7,
    stable_smooth: int = 7,
    z_window: int = 30,
) -> pd.Series:
    """
    Compute composite regime score from ETF flows and stablecoin supply.
    All inputs at T; output at T (apply .shift(1) in backtest to ensure T-1 use).
    """
    flow_7d   = etf_flows.rolling(flow_smooth).sum()
    flow_z    = (flow_7d - flow_7d.rolling(z_window).mean()) / flow_7d.rolling(z_window).std()
    delta_7d  = stable_supply.pct_change(stable_smooth)
    stable_z  = (delta_7d - delta_7d.rolling(z_window).mean()) / delta_7d.rolling(z_window).std()
    return 0.5 * flow_z + 0.5 * stable_z


def apply_regime_overlay(
    prices_df: pd.DataFrame,
    regime_score: pd.Series,
    threshold: float,
    vol_target: float = 0.18,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (signal_filtered, signal_unfiltered) for direct comparison.
    """
    # Strategy A signal — unchanged logic
    signal_A = compute_signal(prices_df, lookback=LOOKBACK_DAYS)
    weekly_A = apply_weekly_rebalance(signal_A, rebalance_weekday=REBALANCE_WEEKDAY)

    # Regime filter — T-1 basis (shift already applied to regime_score before calling)
    regime_active = (regime_score > threshold).reindex(weekly_A.index).fillna(False).astype(float)
    signal_filtered = weekly_A.multiply(regime_active, axis=0)

    return signal_filtered, weekly_A
```

**Key design constraints**:
- `strategies/tsmom_v2_propfirm/` is imported as a module, NEVER modified
- Regime score uses `.shift(1)` at the call site in backtest.py (not inside engine.py) for explicitness
- `regime_active` is a scalar multiplier per date — the same filter applies to all 14 Strategy A assets simultaneously (it's a market-level regime, not asset-level)
- Weekly rebalance Monday: regime filter evaluated from Friday close (T-1 relative to Monday open)

---

## 5. Ex-Ante Thresholds

Three thresholds, fixed before any data analysis. These are the 3 test budget items (n_tests 156→159):

| Threshold τ | Label | Expected time-in-market (if Gaussian regime_score) | Interpretation |
|------------|-------|-----------------------------------------------------|----------------|
| 0.0 | `BASELINE` | ~50% | Active when composite score above local 30d average |
| +0.5 | `MODERATE` | ~31% | Active in clearly positive liquidity regimes |
| +1.0 | `SELECTIVE` | ~16% | Active only in strongly positive regimes |

**Only ONE threshold will be selected for PHASE 3 WF** (to be justified in HYPOTHESIS.md based on PHASE 2 conditional analysis). The other two form sensitivity bounds in PHASE 4 (±0.25σ from selected).

**No additional thresholds will be tested** — doing so would exceed the 3-test budget and violate the max-3-modifications rule.

---

## 6. Walk-Forward Design (PHASE 3)

- **Post-ETF window only**: 2024-01-11 → 2026-05-23 = **~28 months**
- **WF params**: 12m train / 6m test / 3m step
- **Folds**:
  | Fold | Train start | Train end | Test start | Test end | Train months |
  |------|-------------|-----------|------------|----------|--------------|
  | 1 | 2024-01-11 | 2024-12-31 | 2025-01-01 | 2025-06-30 | 12m |
  | 2 | 2024-01-11 | 2025-03-31 | 2025-04-01 | 2025-09-30 | 15m |
  | 3 | 2024-01-11 | 2025-06-30 | 2025-07-01 | 2025-12-31 | 18m |
  | 4 | 2024-01-11 | 2025-09-30 | 2026-01-01 | 2026-05-23 | 21m (partial) |
- **Result**: 4 folds (≥ minimum 2). Fold 4 test is only ~5 months — acceptable.
- **Warm-up**: Strategy A requires 28 days; regime score z-score requires 30+7 = 37 days. Train period starts 37 days before the first test date for proper initialization.
- **No parameter fitting in train**: threshold is pre-specified. Train period provides signal warm-up only.

---

## 7. Cost Model

The overlay does not add transactions beyond what Strategy A already does. The delta-turnover arises only when:
- Regime switches from active→inactive at a Monday rebalance: Strategy A would normally hold or enter a position, but overlay prevents it → saves a trade cost (positive)
- Regime switches from inactive→active at a Monday rebalance: Strategy A enters a position it would have missed → adds a trade cost, but also earns the return

Expected regime state transitions: regime is autocorrelated (medium-term trend), so switching frequency is likely 2-6 regime changes per year. At 0.17% RT × ~4 extra/fewer trades per year = ≤1% additional annual cost. This is within noise relative to Strategy A's ~Sharpe 1.33 performance.

**Model explicitly**: in PHASE 3 backtest, track `n_turns_filtered` vs `n_turns_unfiltered` per WF fold and report `delta_cost_annual_pct`.

---

## 8. Known Risks & Pre-Filed Stop Conditions

| Risk | Probability | Mitigation / Stop |
|------|-------------|-------------------|
| Farside 403 Cloudflare block | Medium | Try headers → if still blocked, STOP "data source fragile" |
| Farside HTML schema change | Low | Validate expected column names, raise if `IBIT` not found |
| DeFiLlama stablecoincharts/all endpoint URL change | Low | Version-check the base URL at init; try `stablecoins.llama.fi/v2/stablecoincharts/all` as fallback |
| ETF data only 28 months → insufficient WF power | Medium | Already accepted — 4 folds is the best available; flag explicitly in results |
| GBTC distortion Jan-Feb 2024 (conversion outflows) | High | Compute both `net_flow_all` and `net_flow_ex_gbtc`; report in PHASE 2 which correlates better with A returns |
| L12b: ETF flow autocorrelation deflating IC | Medium | HAC lag-6 mandatory for all IC tests; report HAC t exclusively |
| Conditional improvement < 0.05%/day in PHASE 2 | Medium | STOP cleanly, archive, do not proceed to PHASE 3 |
| Overlay has opposite effect (σ decreases without ↑ Sharpe) | Low | Report Sharpe ratio AND time-in-market together — lower vol without lower returns is a win |

---

## 9. Confirmation: Overlay, Not Standalone Alpha

- The overlay has **no independent alpha claim**: it is a regime filter
- `regime_score > τ` is binary (ON/OFF), not a sizing modifier
- The overlay cannot be deployed without Strategy A
- Results are always reported as `Sharpe_ratio = Sharpe(A+overlay) / Sharpe(A_unfiltered)`, never as standalone Sharpe
- If Sharpe_ratio < 1.10 but time-in-market < 60% → **not a pass** (must actually improve risk-adjusted performance, not just reduce exposure)

---

## 10. N_tests Budget

| Phase | Tests consumed | n_tests after |
|-------|---------------|--------------|
| Current | 0 (bootstrap) | 156 |
| PHASE 2 IC analysis | 0 (exploratory, no new hypothesis) | 156 |
| PHASE 3 WF × 3 thresholds | +3 | 159 |
| PHASE 4 bootstrap/DSR | 0 (validation of selected threshold) | 159 |
| **Max budget** | **+3** | **159** |

---

## GATE 0 — HARD STOP

Inventory complete. Awaiting explicit "GO PHASE 1" before writing HYPOTHESIS.md or any code.

**Pre-PHASE 1 decision required**: confirm the threshold selection rule. The current plan selects 1 of the 3 thresholds in PHASE 2 based on conditional analysis. If user prefers to test all 3 in PHASE 3 independently (spending 3 tests), confirm.
