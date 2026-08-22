# `data/ftmo_universe/` — toutes les données tradeable FTMO

Dossier consolidé construit 2026-06-02. **Contient uniquement des symlinks** vers les fichiers sources originaux (aucune duplication de disque). Si tu veux des copies hard, fais `cp -RL data/ftmo_universe/ ailleurs/` (le `-L` suit les liens).

**57 symlinks, 0 cassé.** Source de vérité de l'univers tradeable : `specs/ftmo_specs_full.csv`.

---

## Arborescence

```
data/ftmo_universe/
├── INDEX.md                  ← ce fichier
├── specs/                    ← FTMO instrument specs (source de vérité)
├── intraday_m1/              ← 1-min OHLCV
│   ├── fx/                   ← 10 majors Dukascopy
│   ├── indices/              ← 5 indices CFD Dukascopy
│   ├── metals/               ← XAUUSD Dukascopy
│   └── crypto/               ← BTCUSD Dukascopy + binance/ (17 cryptos)
├── intraday_m5/              ← 5-min
│   ├── indices/              ← 4 indices CFD (US100/500/30/2000)
│   ├── fx/dukascopy_m5/      ← 10 majors × 9 années (2018-2026)
│   ├── panels/               ← panels indices pré-construits
│   └── EURUSD/               ← EURUSD M5 + M15
├── daily_panels/             ← daily OHLC consolidé
│   ├── indices/              ← 10 indices FTMO (AUS200/US30/UK100/GER40/...)
│   ├── fx/                   ← FX ETF proxy + 3m forwards
│   ├── crypto/               ← crypto panel + btc_full
│   ├── commodities/          ← commodity panel + softs_metals
│   └── stocks_proxy/         ← US single stocks (proxy CFD)
├── parquets/                 ← M1 parquets (BTC, EUR, GER, XAU + global)
├── eurusd_extras/            ← EURUSD M1 + spread profile par heure
└── news/                     ← calendrier économique + news events 2020-2025
```

---

## Inventaire détaillé

### `specs/` — Source de vérité univers FTMO
| Fichier | Description | Source |
|---|---|---|
| ftmo_specs_full.csv | ~100 instruments avec specs (margin, contract size, swap, commission, hours) | `data/ftmo_research/` |
| ftmo_specs.csv | Version compacte | `data/ftmo_research/` |

Classes d'actifs FTMO confirmées par les specs :
- **FX** (Forex pairs)
- **Index CFD** (US100.cash, US500.cash, US30.cash, GER40.cash, ...)
- **Metal CFD** (XAUUSD, XAGUSD, XPDUSD, XPTUSD)
- **Energy CFD** (UKOIL.cash, USOIL.cash, NGAS.cash)
- **Soft CFD** (COCOA.c, COFFEE.c, SOYBEAN.c, WHEAT.c, ...)
- **Crypto CFD** (BTCUSD, ETHUSD)
- **Stocks CFD** (US large caps, subset limité)

⚠ **FTMO ne supporte PAS les futures CME** (NQ/ES/ZN/CL/GC) — L22(c). Strategy C → broker Tradeify.

---

### `intraday_m1/fx/` — FX 1-min Dukascopy
10 majors couvrant ~2018-2026 (last bar 2026-05-29). Format : `timestamp_utc, open, high, low, close, tick_volume, spread, real_volume`.

| Symbole | Source |
|---|---|
| AUDJPY, AUDUSD, EURGBP, EURJPY, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY | `data/panels/m5_indices/{SYM}_M1.csv` |

### `intraday_m1/indices/` — Indices CFD 1-min
| Symbole | Notes |
|---|---|
| US100 (NAS100), US500 (S&P), US30 (Dow), US2000 (Russell), GER40 (DAX) | Dukascopy |

### `intraday_m1/metals/` — Gold 1-min
| Symbole | Notes |
|---|---|
| XAUUSD | Dukascopy |

### `intraday_m1/crypto/` — Crypto 1-min
| Path | Notes |
|---|---|
| BTCUSD_M1.csv | Dukascopy CFD (FTMO-compat) |
| binance/ | 17 cryptos Binance spot (BTC, ETH, ADA, SOL, AVAX, BCH, LTC, XRP, DOT, LINK, BNB, AAVE, DASH, DOGE, NEO, XLM, XMR) — **proxy uniquement**, FTMO crypto CFD se limite à BTC/ETH |

Last bar Binance : 2026-06-01 22:55 UTC.

---

### `intraday_m5/`
| Sous-dossier | Contenu |
|---|---|
| indices/ | US100/US500/US30/US2000 M5 |
| fx/dukascopy_m5/ | 10 majors × 9 années (AUDUSD_2018_M5.parquet → 2026) — utilisé par les scripts de recherche Forex |
| panels/ | m5_close/open/high/low.csv pré-aggrégés (indices) + m5_panel.parquet + samples 60d |
| EURUSD/ | EURUSD_m5.parquet + EURUSD_m15.parquet (legacy ftmo_research) |

---

### `daily_panels/`
| Sous-dossier | Fichiers | Couverture |
|---|---|---|
| indices/ | ftmo_close.csv, ftmo_open.csv, ftmo_high.csv, ftmo_low.csv | 10 indices (AUS200, US30, UK100, GER40, US500, HK50, JP225, US100, US2000, EU50), 2000-01-03 → 2026-05-27, 6870 rows |
| fx/ | fx_panel.csv (ETF proxies FXA/FXB/FXC/FXE/FXF/FXY/UUP), fx_rates_3m.csv | 2006+ |
| crypto/ | crypto_panel.csv, btc_full.csv | daily multi-coin |
| commodities/ | commodity_panel.csv, softs_metals.csv | daily |
| stocks_proxy/ | single_stocks.csv | ⚠ FTMO stocks CFD = subset très limité, vérifier ticker à ticker contre specs |

---

### `parquets/` — M1 OHLC en parquet
| Fichier | Description |
|---|---|
| BTCUSD_m1_panel.parquet, EURUSD_m1_panel.parquet, GER40_m1_panel.parquet, XAUUSD_m1_panel.parquet | M1 par instrument, format panel |
| m1_panel.parquet | M1 panel global indices |

### `eurusd_extras/` — EURUSD analysis spéciaux
| Fichier | Description |
|---|---|
| EURUSD_m1.parquet | 35 MB, M1 historique |
| eurusd_m1_spread.parquet | Spread M1 par bar (~23 MB) |
| eurusd_spread_profile_by_hour.csv | Spread moyen par heure UTC |

### `news/`
| Fichier | Description |
|---|---|
| economic_calendar.csv | Calendar macro multi-pays |
| news_events_2020_2025.csv | Events high-impact 2020-2025 (pour filter trading sur news) |

---

## Données EXCLUES de ce dossier (raison)

Pas FTMO-tradable directement :
- `data/funding_carry/` (HL crypto perp funding — ≠ FTMO crypto CFD)
- `data/panels/factor_etf_panel.csv`, `vol_etf_panel.csv`, `macro_etf_panel.csv` (ETF, non FTMO)
- `data/panels/vix.csv`, `vix_term_structure.csv` (VIX index, non tradable directement FTMO)
- `data/panels/ff5.csv`, `momentum.csv`, `merger_arb.csv` (factors académiques)
- `data/panels/equity_open.csv`, `equity_close2.csv`, `equity_panel.csv` (single stocks panel — `single_stocks.csv` est l'équivalent inclus en `stocks_proxy/`)
- `data/raw/`, `data/vrp/`, `data/pairs_trading/`, `data/momentum_universe.csv` (research datasets non-FTMO)
- `data/GLBX-20260601-FP4HWRA58K/` (CME futures Databento — strict no-FTMO)

Si tu veux qu'on en intègre une ci-dessus (par exemple stocks CFD plus large via equity_panel), dis-moi et je l'ajoute.

---

## Usage

```python
import pandas as pd

# Specs FTMO complet
specs = pd.read_csv("data/ftmo_universe/specs/ftmo_specs_full.csv")

# Intraday EURUSD M1
eurusd_m1 = pd.read_csv("data/ftmo_universe/intraday_m1/fx/EURUSD_M1.csv",
                        parse_dates=["timestamp_utc"])

# Daily indices FTMO panel
close = pd.read_csv("data/ftmo_universe/daily_panels/indices/ftmo_close.csv",
                    parse_dates=["Date"], index_col="Date")

# M5 FX par année
import glob
audusd_m5 = pd.concat([pd.read_parquet(f) for f in
    sorted(glob.glob("data/ftmo_universe/intraday_m5/fx/dukascopy_m5/AUDUSD_*_M5.parquet"))])
```

---

## Maintenance

- **Régénérer** : supprimer `data/ftmo_universe/` puis re-runner le bloc bash du commit qui l'a créé (cf. git log).
- **Convertir en copies hard** : `cp -RL data/ftmo_universe/ data/ftmo_universe_copy/`
- **Ajouter une source** : `ln -sf $BASE/<source> $ROOT/<dest>` puis update INDEX.md.

*Index maintenu manuellement. Si tu modifies les chemins source, vérifier `find data/ftmo_universe -type l ! -exec test -e {} \; -print` pour les symlinks cassés.*
