# FTMO — Rules

last_verified: 2026-06-01 (web fetches on ftmo.com FAQ + Trading Objectives page + third-party 2026 reviews)
sources:
- https://ftmo.com/en/trading-objectives/ (2-step targets/DLL/MLL)
- https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/
- https://ftmo.com/en/faq/what-are-the-account-specifications/ (Standard 1:100, Swing 1:30)
- https://ftmo.com/en/blog/ftmo-enhances-crypto-trading-new-instruments-and-better-spreads/
- https://ftmo.com/en/blog/zero-commissions-on-indices/
- https://ftmo.com/en/swing-account/ (Swing exemptions)
- https://academy.ftmo.com/lesson/maximum-daily-loss/ (DLL recalc time, 1-step 3%)
- WebSearch 2026 reviews for news-trading 2-min rule + funded-account weekend rule

> ✓ = fetched verbatim from a public FTMO/Academy URL on 2026-06-01.
> ◐ = derived from 2026 third-party reviews (FXEmpire, BrokerAnalysis, tradingfinder, etc.), cross-corroborated, but not a direct FTMO quote.
> ⚠️ = must be confirmed in MT5 Symbol Specification, or by FTMO support — cannot be obtained from public web.

---

## 2-Step Challenge — Trading Objectives (Normal + Swing identical)

| Objective | Phase 1 (Challenge) | Phase 2 (Verification) | Source |
|-----------|---------------------|------------------------|--------|
| Profit target | ✓ 10% of initial capital | ✓ 5% of initial capital | trading-objectives/ |
| Maximum Daily Loss | ✓ 5% of initial capital (recalculated daily at 00:00 CE(S)T) | ✓ 5% of initial capital | trading-objectives/ |
| Maximum Total Loss | ✓ 10% of initial capital — **STATIQUE, ancré au capital initial** (corrigé 2026-08-04) | ✓ idem, statique | trading-objectives/ |
| Min trading days | ✓ ≥4 trading days ⚠ **définition de « trading day » NON citée en source primaire** (voir ci-dessous) | ✓ ≥4 trading days | trading-objectives/ |
| Max trading period | ✓ none (unlimited) | ✓ none (unlimited) | trading-objectives/ |

## 1-Step Challenge — Trading Objectives

| Objective | Value | Source |
|-----------|-------|--------|
| Profit target | ◐ 10% | tradingfinder 2026 |
| Maximum Daily Loss | ◐ 3% (tighter than 2-step) | FTMO Academy DLL page |
| Maximum Total Loss | ◐ 6% (typical) | tradingfinder 2026 |
| Min trading days | ◐ ≥4 | tradingfinder 2026 |

> ⚠️ 1-Step values are 2026-review-corroborated but not all directly quoted from ftmo.com — re-verify before purchasing a 1-Step.

## ⚠ « Trading day » — DÉFINITION MANQUANTE EN SOURCE PRIMAIRE (relevé 2026-08-04)

Toutes les autres règles de ce fichier sont citées **verbatim**. Celle-ci ne l'est pas : on sait
qu'il faut **≥4 trading days**, on ne sait pas ce qui **compte** comme trading day.

**Pourquoi c'est important** : une pièce entière du livre déployé — le **micro-ORB compteur de
jours** (`micro_orb_day_counter`, US100.cash à 0.01 lot) — n'existe QUE pour satisfaire cette règle.
Son audit (`Multi_Asset/research/active/audit_micro_orb_2026-08/`) montre qu'elle fait son travail
(taux d'échec **0.00 %**, médiane **4 séances** = le minimum arithmétique), mais **on valide une
pièce contre une règle qu'on n'a jamais lue à la source**.

Questions ouvertes, toutes matérielles : une position **ouverte** suffit-elle, ou faut-il une
position **fermée** ? un volume minimum ? un jour où l'on est en position depuis la veille sans
nouvel ordre compte-t-il ? le jour est-il compté en heure de Prague (cohérent avec le reset 00:00
CE(S)T) ?

**À vérifier en source primaire avant tout travail sur le compteur.** Précédent : le « parc
multi-comptes » a été instruit puis annulé faute d'avoir lu les T&C d'abord.

## Daily Loss Limit — mechanism

> ✓ Quoted from FTMO Academy "Maximum Daily Loss":
> _"recalculated daily at 00:00 CE(S)T as the difference between the account balance recorded at 00:00 CE(S)T of the current day and the Maximum Daily Loss Amount, which is 3% or 5% of the Initial Simulated Capital."_

- Floor reset time: **00:00 Prague time** (CET=UTC+1, CEST=UTC+2). For backtesting, the relevant cutoff is 22:00 or 23:00 UTC depending on DST.
- The DLL is anchored on the **balance** at 00:00 CE(S)T, NOT high-water-mark.
- Open-PNL counts toward the DLL intraday (FTMO uses equity-based DLL enforcement, not balance-based).

## Maximum Loss — mechanism

> ⚠ **PORTÉE — À LIRE AVANT LA CITATION (précisé 2026-08-01).** La citation ci-dessous décrit le
> plancher **à cliquet**, qui ne s'applique **QU'AU CHALLENGE 1-STEP** — produit **écarté** par ce
> projet. Sur le **2-step** que nous exécutons, le plancher est **STATIQUE** : −10 % du capital
> initial, fixe, il ne monte jamais avec les gains ($10k → plancher dur $9 000).
>
> **Toutes les simulations du projet doivent utiliser le plancher STATIQUE.** Cette contradiction
> apparente a été signalée et tranchée deux fois (2026-07-20, 2026-08-01) : ne pas la rouvrir.
> La distinction n'est pas cosmétique — un plancher à cliquet mord surtout sur les chemins
> *gagnants* (un repli après gains peut casser), donc l'utiliser à tort **sous-estimerait** tous
> les p(pass).

### Variante 1-step (écartée) — citation d'origine

> ✓ Quoted from FTMO Academy:
> _"recalculated daily at 00:00 CE(S)T as the difference between the highest account balance achieved at 00:00 CE(S)T of any preceding trading day or, if higher, the amount of Initial Simulated Capital, and the Maximum Loss Amount, which is 10% of the Initial Simulated Capital. Additionally, the limit can only increase, but never decrease."_

- Equivalent to a **trailing EOD drawdown that locks at the initial balance** (high-water-mark of EOD balance, never below starting capital).
- 10% of initial capital, anchored on EOD HWM ≥ initial.

### Variante 2-step (LA NÔTRE) — plancher statique

- Max Loss = **10 % du capital initial, ancré au capital initial**, jamais recalculé.
- Max Daily Loss = **5 %** du solde d'ouverture de journée, appliqué sur l'**équité** en intraday.

---

## Leverage — by asset class

| Asset class | Standard (Normal) | Swing | Source |
|-------------|------------------|-------|--------|
| Forex | ✓ up to 1:100 | ✓ up to 1:30 | account-specifications + swing-account |
| Indices | ◐ up to 1:50 | ◐ up to 1:30 | bestpropfirmguide 2026 |
| Metals (XAU, XAG, XPT, XPD) | ◐ up to 1:30 | ◐ up to 1:30 | bestpropfirmguide 2026 |
| Commodities/Energies (USOIL, UKOIL, NGAS) | ⚠️ ≤1:10 typical | ⚠️ ≤1:10 typical | not confirmed publicly |
| Crypto | ◐ up to 1:3.3 (≈ 30% margin) | ◐ up to 1:2 (~50% margin) | bestpropfirmguide 2026 + standard prop convention |
| Stocks/Shares | ⚠️ 1:5 typical CFD | ⚠️ 1:5 typical | not confirmed publicly |
| Bonds/Rates | ✗ NOT OFFERED | ✗ NOT OFFERED | see P3 finding below |

> ⚠️ Verify crypto and commodity leverage **in MT5** before sizing — third-party numbers diverge.

---

## Commissions

| Asset class | Commission | Source |
|-------------|-----------|--------|
| Forex | ⚠️ ~$3-$4 per round-turn lot typical | not on public FAQ — check MT5 Specification |
| Indices | ✓ **zero commission** on all index symbols | blog/zero-commissions-on-indices/ |
| Metals | ⚠️ verify in MT5 (often baked in spread) | not public |
| Crypto | ✓ **0.0325% per side** on notional volume (= **0.065% RT**) | blog/ftmo-enhances-crypto-trading/ |
| Stocks | ⚠️ verify in MT5 | not public |

---

## News trading

| Phase | Restriction | Source |
|-------|-------------|--------|
| Challenge (P1) | **None** — news trading unrestricted | tradingfinder 2026 |
| Verification (P2) | **None** — news trading unrestricted | tradingfinder 2026 |
| Funded Standard | ◐ **2-minute window before AND after** restricted news events — cannot open OR close (incl. SL/TP triggers) | tradingfinder 2026, propvator 2026, multiple corroborations |
| Funded Swing | ✓ **EXEMPT** — no news-trading restriction | swing-account/ |

**Restricted events (Tier 1, ◐):** NFP, US CPI, FOMC, ECB rate decision, BOE rate decision, and similar high-impact macro prints. The full list is curated by FTMO; "targeted instruments" = the instruments primarily moved by each event (e.g., USDJPY/EURUSD/GBPUSD for FOMC; XAUUSD also affected).

**Enforcement:** ◐ Immediate breach on violation. No warnings. Holding a position opened >2min before the release is allowed.

> ⚠️ For Strategy C-class (NQ ORB at 09:46 ET): if you ever port to a funded Standard FTMO account, the 09:45 ET window does **not** overlap the typical 08:30 ET print window (NFP/CPI), but **CPI/NFP** print at 08:30 ET = 14:30 CET — outside your entry but **inside potential management of overnight positions**. Confirm if NQ is on the restricted-instrument list (it usually is for US economic prints).

## Weekend holding

| Phase | Rule | Source |
|-------|------|--------|
| Challenge / Verification | ✓ Allowed to hold over weekend | search results 2026 |
| Funded Standard | ◐ Must close before weekend; rollover >2h triggers forced closure | search results 2026 |
| Funded Swing | ✓ No weekend restriction | swing-account/ |

> ⚠️ For Strategy A-class (BTC/ETH/SOL TSMOM, weekly rebalance Monday): on a funded **Standard** account, holding crypto across the FX-close weekend would breach. The Swing account is the only viable path. Crypto trades Fri 22:00 UTC – Mon 22:00 UTC via FTMO simulated venue; FTMO publishes the exact crypto trading hours per symbol on the symbols page — verify in MT5.

---

## Crypto-specific rules

| Rule | Value | Source |
|------|-------|--------|
| Commission per side | ✓ 0.0325% on notional, auto-converted to base currency | blog 2025-07 |
| Round-trip cost (commission only) | ✓ **0.065%** | derived |
| Leverage | ◐ 1:3.3 Standard / 1:2 Swing | bestpropfirmguide 2026 |
| Weekend availability | ◐ Yes, FTMO offers weekend crypto trading | symbols page mention |
| **Reduced weekend DLL/MLL** | ⚠️ **Not confirmed publicly** — initial estimate 2-3% but you MUST verify with FTMO support or in the challenge dashboard | — |
| Available pairs (post-2025-07 expansion) | ✓ BTCUSD, ETHUSD, ADAUSD, DOTUSD, DASHUSD, LTCUSD, XRPUSD, DOGEUSD, XMRUSD, NEOUSD + 12 added (SOL, BNB, XLM, AAVE, LINK, +7 unspecified) | blog 2025-07 |

> ⚠️ **Critical unknowns for Strategy A FTMO port:**
> 1. Exact crypto leverage on Swing (3.3 or 2 or other?)
> 2. Whether crypto has a reduced DLL or modified MLL on weekend
> 3. Exact swap (overnight financing) per crypto symbol — only visible in MT5 Specification
>
> All three must be confirmed BEFORE backtesting an FTMO-targeted variant of Strategy A.

---

## Instruments offered (categories)

Per FAQ ✓ : Forex, Indices, Commodities, Stocks, Crypto. That's it.

**P3 finding (bonds/rates):**
- FTMO does **NOT** publicly list any bond, treasury, or interest-rate CFD (Bund, BTP, US10Y, Gilt, T-Note).
- The official FAQ enumerates the 5 categories above; no mention of bonds or rates anywhere on the symbols page, account specs, or FAQ.
- Confirmed by absence in 2026 third-party reviews (FXEmpire, BrokerAnalysis, MyFXBook).
- **Conclusion:** P3 (bond CFDs on FTMO) is dead. The bond/rate asset class is not testable on FTMO.
- Alternative if you want bond/rate exposure inside a propfirm framework: IC Markets / Pepperstone offer Bund/UST CFDs, but neither runs a challenge model matching FTMO's pass profile. For CME interest-rate futures (ZB, ZN, ZF, ZT) → Apex / Topstep / Tradeify (futures propfirms).

---

## Strategies — explicitly allowed/forbidden

✓ Per FAQ "which-instruments-can-i-trade":
- **Allowed:** EAs (with caveats below), hedging (intra-account), discretionary, algorithmic.
- **Forbidden:** strategies that don't reflect "real market conditions" — vague catch-all FTMO uses against arbitrage exploits (tick-scalping, latency abuse, group strategies sharing identical EA across many accounts beyond the "maximum capital allocation rule").
- **Platform limits:** ✓ 200 orders at a time, 2000 max positions per day.
- **Stop-loss:** ✓ Not mandatory, but "generally advisable."

---

## Account sizes & costs

⚠️ Not extracted in this pass — see ftmo.com pricing page. Standard sizes: $10K / $25K / $50K / $100K / $200K simulated capital. Fee scales accordingly.

---

## What you still need to extract from MT5 (cannot be obtained from public web)

Run this MQL5 script on the FTMO MT5 demo (5 min), no FTMO account purchase required:

```mql5
// Save as ExportSpecs.mq5, attach to any chart, F5
void OnStart() {
    int handle = FileOpen("ftmo_specs.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    FileWrite(handle, "symbol","spread_pts","contract_size",
                      "tick_value","tick_size","commission_per_lot",
                      "swap_long","swap_short","swap_3day",
                      "margin_init_pct","trading_hours","stops_level");
    int total = SymbolsTotal(false);  // all available, not just Market Watch
    for(int i = 0; i < total; i++) {
        string s = SymbolName(i, false);
        SymbolSelect(s, true);  // ensure subscribed
        FileWrite(handle,
            s,
            (long)SymbolInfoInteger(s, SYMBOL_SPREAD),
            SymbolInfoDouble(s, SYMBOL_TRADE_CONTRACT_SIZE),
            SymbolInfoDouble(s, SYMBOL_TRADE_TICK_VALUE),
            SymbolInfoDouble(s, SYMBOL_TRADE_TICK_SIZE),
            0,  // commission not exposed via SymbolInfo* — read from contract spec
            SymbolInfoDouble(s, SYMBOL_SWAP_LONG),
            SymbolInfoDouble(s, SYMBOL_SWAP_SHORT),
            (long)SymbolInfoInteger(s, SYMBOL_SWAP_ROLLOVER3DAYS),
            SymbolInfoDouble(s, SYMBOL_MARGIN_INITIAL),
            SymbolInfoString(s, SYMBOL_DESCRIPTION),
            (long)SymbolInfoInteger(s, SYMBOL_TRADE_STOPS_LEVEL));
    }
    FileClose(handle);
    Print("Exported ", total, " symbols to MQL5/Files/ftmo_specs.csv");
}
```

Output ends up in `<MT5>/MQL5/Files/ftmo_specs.csv` — gives you the full swap table, contract sizes, tick values, and margin per symbol in one shot. Commission isn't exposed via `SymbolInfo*` so still read from the broker contract spec UI (right-click symbol → Specification → Commission row).

For the crypto-weekend DLL question: only FTMO Support chat can confirm. Open chat at ftmo.com, ask verbatim: _"For the 2-Step Standard Challenge, what is the Maximum Daily Loss percentage on Saturday and Sunday for crypto positions? Is it the same 5%, or is it reduced?"_ — they answer in <5 min.
