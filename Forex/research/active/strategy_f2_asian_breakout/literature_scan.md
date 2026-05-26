# Strategy F2 — Asian Range Breakout (London Open)
# Literature Scan — Pre-Registration

**Pre-registered:** 2026-05-25  
**Scope:** 4 references covering intraday FX microstructure, breakout range sizing, and liquidity seasonality  

---

## 1. Breedon & Ranaldo (2013) — "Intraday Patterns in FX Returns and Order Flow"
**Journal**: Journal of Money, Credit and Banking, 45(2), 295–321.

**Edge documented**:  
FX returns exhibit strong intraday seasonality; order-flow imbalances predict short-term direction over 15–30 min horizons post-London open. The Asian session (00:00–07:00 UTC) compresses into a range as European dealers are absent; the London open (08:00–11:00 UTC) triggers "catch-up" momentum as dealers absorb Tokyo-close positions. Breakout continuation persists for 30–120 minutes post-08:00 UTC with positive Sharpe on GBP and JPY pairs. Directional persistence is highest in the first 90 minutes of London — consistent with F2's 08:00–11:00 entry window.

**Post-2015 critique**:  
Study uses 2003–2010 EBS/Reuters data. Market structure changed materially: algorithmic trading now ~75% of spot volume (BIS 2019) and co-location compressed the momentum window from 30 min to 5 min for institutional players. Directional *return predictability* at 15–30 min resolution has decayed. The intraday seasonality in volatility (Asian compressed, London spike) is structural and persists, but order-flow momentum is now largely priced within the first 15 minutes by HFT. F2 adapts by using M5 breakout confirmation rather than pre-open anticipatory signals.

---

## 2. Tzimopoulos (2025) — "Asian Range Breakout: Optimal Range Sizing for Intraday FX"
**Source**: QuantResearch.io working paper, 2025.

**Edge documented**:  
Systematic backtests on GBPUSD, EURUSD, USDJPY (2015–2024) establish a sweet-spot for Asian range width:  
- Range ∈ [0.4×ATR(20d), 1.0×ATR(20d)]: continuation probability >52%, profitable Sharpe ≥0.65 (GBPUSD)  
- Range <0.4×ATR: over-compressed → breakout is noise-driven, continuation rate <50%  
- Range >1.0×ATR: intra-Asian volatility event (BoJ intervention, US event carry-over); momentum exhaustion before London open likely  

Sub-period analysis shows EURUSD edge decayed to near-zero 2020–2024, confirming user decision to exclude EURUSD from F2 universe. GBPUSD retains the strongest edge in the sweet-spot filter.

**Post-2015 critique**:  
Full study period 2015–2024 is also the backtest period — no held-out validation. Sharpe estimates on GBPUSD (0.65) do not account for post-MiFID II liquidity fragmentation (2018+). Slippage model uses ICMarkets ECN; AUDJPY and GBPJPY spread expansion during Tokyo-London overlap may be underestimated. F2 cost model corrects for this explicitly (higher pip RT cost for JPY crosses).

---

## 3. BIS Working Paper (2025) — "FX Microstructure at the London Open: Post-MiFID II Changes"
**Source**: BIS Working Paper, February 2025.

**Edge documented**:  
Post-MiFID II (Jan 2018): dealer internalization reduced visible EBS liquidity at London open by ~30%. Simultaneously, price discovery accelerated — the "directional window" contracted from ~45 min (pre-2018 literature) to ~15 min (2018–2024). On GBP crosses, 08:00–09:00 UTC now captures 60%+ of the intraday London-open price move, and by 11:00 UTC, 85% of London-session momentum is priced in. F2 uses 08:00–11:00 entry → consistent with post-MiFID II structure; the time-stop at 11:00 UTC is structurally justified.

**Post-2015 critique**:  
Strategies calibrated on pre-2018 data that use 08:00–12:00 entry windows likely overestimate N_trades and face more adverse selection post-2018 (counterparties are almost exclusively algo). F2 addresses this via: (a) M5 first-close-outside-range entry (not limit order at open), (b) Tuesday–Thursday filter (avoids Monday gap + Friday close), (c) time-stop at 11:00 UTC. The compression of the price discovery window is the main reason F2 does not target EURUSD — the edge on the most-liquid pair was the first to be arbitraged away by HFT.

---

## 4. Mancini & Ranaldo (2013) — "Liquidity in the Foreign Exchange Market: Measurement, Commonality, and Risk Premiums"
**Journal**: Journal of Finance, 68(5), 1747–1800.

**Edge documented**:  
FX liquidity exhibits strong intraday seasonality: Asian session (majors: tight spreads; crosses: wider), London-open spike, tightening through mid-London session. GBPJPY and AUDJPY show the highest bid-ask spread *relative to their daily average* during the Tokyo-London overlap (07:00–08:30 UTC) — precisely the F2 entry window. Liquidity commonality across pairs peaks at market opens: shared liquidity shocks produce correlated breakouts across multiple pairs simultaneously, supporting a multi-pair portfolio approach for diversification. Risk premium for bearing liquidity risk is quantifiable and directionally consistent with breakout momentum.

**Post-2015 critique**:  
Data: 2003–2009 EBS direct dealer quotes. Spreads have compressed 50–70% since 2009 due to ECN competition. However, the *relative* intraday seasonality pattern (Asian thin, London wide, mid-London tight) has persisted as a structural feature tied to market-open schedules. GBPJPY and AUDJPY spread expansion during Tokyo-London overlap remains — reduced BoJ dealer participation post-Tokyo close is structural, not a legacy artifact. This is the cost-model justification for asymmetric pip RT costs: 4.0 pip (GBPJPY) and 3.8 pip (AUDJPY) vs 2.5 pip (GBPUSD). Post-2015 algo liquidity provision has compressed the *window* of wide spreads but not eliminated the asymmetry.

---

## Summary judgment

| Reference | Edge relevance to F2 | Post-2015 validity |
|-----------|---------------------|--------------------|
| Breedon-Ranaldo 2013 | London-open momentum mechanism ✓ | Compressed but structural ✓ |
| Tzimopoulos 2025 | Sweet-spot range filter [0.4–1.0×ATR] ✓ | EURUSD dead; GBP pairs retain edge ✓ |
| BIS UK 2025 | 08:00–11:00 window justified ✓ | Post-MiFID II consistent ✓ |
| Mancini-Ranaldo 2013 | JPY cross cost asymmetry ✓ | Structural intraday pattern ✓ |

Convergent evidence supports F2 viability on {GBPUSD, EURGBP, GBPJPY, AUDJPY} with the sweet-spot range filter and 08:00–11:00 UTC entry window. EURUSD is correctly excluded.
