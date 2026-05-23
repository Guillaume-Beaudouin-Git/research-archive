# Cartographie des sources d'alpha crypto pour un quant retail (data 100% gratuite)

**TL;DR**
- Les edges les moins saturés et les plus accessibles à un retail M1 sont (1) le **funding-rate / perp-spot basis** (carry annualisé ~7–8% sur BTC/ETH selon le BIS WP 1087 « Crypto carry » de Schmeling, Schrimpf & Todorov, 2023), (2) les **flux d'options Deribit gratuits** (DVOL, GEX, skew via l'API publique `/public/get_volatility_index_data`), et (3) la **structure de positionnement Hyperliquid on-chain** (HLP vault, positions de liquidation visibles en temps réel) — trois zones où les pros ont l'edge mais où le retail peut survivre.
- L'alpha pur HFT (OFI, micro-price, VPIN) reste académiquement valide (Cont-Kukanov-Stoikov 2014 ; Xu-Gould-Howison 2019 ; Almeida et al. arXiv 2410.15195 montre une variance risk premium BTC annualisée ≈ 0.14, soit ~7× celle du S&P 500) mais est **dominé par les market makers** ; pour un retail sans co-location, il sert surtout de feature de timing d'exécution.
- À privilégier en R&D : **event-driven** (token unlocks, listings exchange, halving), **on-chain smart money** (Dune + DeFiLlama gratuits), **cross-sectional momentum hebdo** (Drogen-Hoffstein-Otte 2023 : 30d-formation/7d-holding) et **régime detection HMM** ; éviter le pur OFI HFT et la course à la latence cross-exchange.

## Key Findings

1. **Le retail crypto a accès à plus de données gratuites qu'un quant equity moyen** : Binance/Bybit/OKX/Kraken/Coinbase/Hyperliquid exposent toute leur L2/trades/funding sans clé API, Deribit donne toute la surface d'options sans authentification, et l'on-chain est intégralement public (Dune, DeFiLlama, Etherscan, The Graph subgraphs).
2. **La saturation varie radicalement selon l'horizon** : sub-seconde → totalement saturée par Wintermute/Jump/Cumberland ; intraday/swing → exploitable mais compétitif ; event-driven et narrative (unlocks, listings, halving, ETF flows) → relativement sous-exploité par les pros qui chassent le scalable.
3. **Trois sources de données « gratuites » sont en réalité indispensables** : Binance/Bybit/Hyperliquid public APIs (microstructure + funding), Deribit `/public/*` (vol surface complète), et DeFiLlama API publique (TVL, stablecoins, fees — API gratuite sans limite stricte selon DeFiLlama 2026 : « DeFiLlama's free API serves billions of requests per month »).
4. **L'edge le plus accessible mathématiquement est le carry funding/basis** : le BIS Working Paper 1087 documente un carry annualisé moyen ~7–8% sur BTC/ETH 2019–2024 ; une analyse Pendle/Boros de 2025 trouve un APR moyen ~11,4% sur l'arbitrage cross-exchange Binance↔Hyperliquid (échantillon limité, attention au selection bias).
5. **L'edge de feature engineering ML universel en crypto existe** : Bieganowski-Ślepaczuk (arXiv 2602.00776) montre que OFI, spread et VWAP-mid déviation ont la **même forme de dépendance SHAP** à travers les large- et mid-caps — un même modèle se transfère bien d'un actif à l'autre, ce qui justifie le cross-sectional learning.

## Details — Cartographie exhaustive par catégorie

### 1. Microstructure & order flow (CEX & DEX)

**Edge potentiel** : prédire les retours sur 1s–60s à partir du déséquilibre du carnet et du trade flow. La forme universelle (Cont-Kukanov-Stoikov 2014, *Journal of Financial Econometrics* 12(1):47–88 ; extension multi-niveaux Xu-Gould-Howison 2019, arXiv:1907.06230) est : ΔP ~ β·OFI où OFI = Σ(ΔBid_qty − ΔAsk_qty) sur N niveaux. VPIN (Easley-López de Prado-O'Hara 2012, *RFS* 25(5):1457–1493) extensible à BTC (Liu et al. 2025, *Research in International Business and Finance*).

**Sources gratuites** :
- Binance Futures WebSocket : `wss://fstream.binance.com/ws/<symbol>@depth20@100ms` et `@aggTrade` (sans clé)
- Bybit v5 WebSocket public : `wss://stream.bybit.com/v5/public/linear`
- OKX, Kraken, Coinbase WebSockets publiques
- Hyperliquid : `wss://api.hyperliquid.xyz/ws` avec subscriptions `l2Book`, `trades`, `bbo` (SDK Python officiel : `hyperliquid-python-sdk`)
- **`ccxt` (Python)** pour normalisation cross-exchange ; **`ccxt.pro`** pour les WebSockets (la version pro est payante mais `ccxt` standard couvre REST gratuitement)
- DEX : The Graph subgraphs Uniswap V3 (gratuit avec rate limit), `web3.py` pour lire directement les events Swap/Mint/Burn

**Horizon** : T+50ms à T+60s (HF/intraday).

**Saturation** : **TRÈS forte** sub-seconde (Wintermute, Jump, GSR, Cumberland sont co-localisés AWS Tokyo/Virginia). Pour un retail sans co-location, l'OFI/micro-price sert plus de **signal d'exécution** (passer ordre passif vs agressif) que de signal de prise de position pure.

**Stratégie concrète** : market-making passif sur Binance Futures USDM avec rebate maker (-0.005% LP program), inventory-managed via signal OFI 10 niveaux. Voir `hftbacktest` (open-source Python/Rust) pour backtest réaliste avec queue position.

**Pièges** : look-ahead via timestamp d'événement vs timestamp de réception ; aggTrade vs trade individuel ; reconstruction L2 depuis snapshot + diffs (gestion des séquences manquantes).

### 2. On-chain analytics

**Edge potentiel** : exchange in/outflows précèdent les retournements ; whale wallets en accumulation = signal directionnel ; stablecoin mints = liquidity proxy.

**Sources 100% gratuites** :
- **DeFiLlama API publique** (https://api.llama.fi) : TVL par protocole/chaîne, stablecoin supply, fees, DEX volume, raises — pas de clé, pas de rate-limit strict (« billions of requests per month » selon DeFiLlama 2026)
- **Dune Analytics** : 2 500 query executions/mois gratuits, accès à toutes les dashboards publiques + SQL custom sur Ethereum/Solana/Base/Arbitrum/BNB
- **Etherscan/Solscan/Arbiscan** : API gratuites avec clé (5 req/s)
- **Glassnode Studio** : un sous-ensemble de métriques gratuites (NVT, MVRV, SOPR, Active Addresses pour BTC/ETH) — la majorité des métriques avancées sont payantes
- **CryptoQuant Community** (free tier) : exchange flows, miner reserves
- **Token Terminal** free tier : fees/revenue par protocole
- **The Graph** hosted subgraphs (gratuit avec rate limit)
- **Nansen Free** : query limitée par jour, mais labels de wallets exploitables

**Métriques de référence académique** : NVT (Willy Woo), MVRV (Murad Mahmudov & David Puell), SOPR (Renato Shirakashi), Realized Cap (Coinmetrics). Whale tracking : monitorer les top 100 wallets via Etherscan API + filtre balance.

**Horizon** : daily à hebdomadaire (les flows on-chain sont *lents*).

**Saturation** : **moyenne**. Le wallet-tracking pur est saturé par Nansen/Arkham, mais combiner flows + funding + sentiment dans un modèle multi-feature reste relativement exploitable. Le piège classique : confondre une transaction de test ou un OTC hedge avec un signal directionnel.

**Stratégie concrète** : « stablecoin pulse » — Z-score 7j des mints USDT+USDC sur les 7 dernières années, long BTC quand Z>1.5 et flat sinon (testable avec DeFiLlama stablecoins endpoint).

### 3. Funding rates, basis, options structure

**Edge potentiel le mieux documenté pour un retail**. Trois sous-edges :

**(a) Cash-and-carry** (long spot, short perp) : le BIS WP 1087 « Crypto carry » (Schmeling, Schrimpf, Todorov, 2023, https://www.bis.org/publ/work1087.pdf) trouve un carry annualisé moyen ~7-8% sur BTC/ETH 2019-2024 ; les futures à 1 et 3 mois capturent ~5-15% annualisés dans les régimes haussiers. Glassnode publie en temps réel l'« Annualized Perpetual Funding vs 3m Rolling Basis » (https://studio.glassnode.com/charts/futures-annualized-yield).

**(b) Cross-exchange funding spread** : Pendle/Boros analysis (2025) documente un spread moyen Binance vs Hyperliquid de 11,4% APR sur BTC (non peer-reviewed, échantillon limité à 2025).

**(c) Volatility Risk Premium options** : Almeida, Grith, Miftachov, Wang « Risk Premia in the Bitcoin Market » (arXiv:2410.15195, 2024, data Deribit Jul 2017–Dec 2022, ~7.83M transactions) trouve une **variance risk premium BTC annualisée ≈ 0.14**, environ 7× celle du S&P 500 (Bollerslev-Tauchen-Zhou 2009 : ~2%). La stratégie classique = vendre des straddles/strangles BTC delta-hedged.

**Sources gratuites** :
- **Deribit API publique** (https://docs.deribit.com/) — aucun token requis pour `/public/*` :
  - `/public/get_book_summary_by_currency` : toute la chaîne d'options BTC/ETH avec mark IV, OI, volume
  - `/public/ticker` : Greeks (delta, gamma, vega) par instrument
  - `/public/get_volatility_index_data` : **DVOL** (VIX-équivalent BTC/ETH, 30j forward IV)
  - `/public/get_historical_volatility` : RV annualisée 15j
  - `/public/get_funding_rate_history` : funding perpétuel
- Binance/Bybit/OKX funding APIs : `/fapi/v1/fundingRate` (historical)
- **CryptoGamma.io** (https://cryptogamma.io) : GEX et 25-delta skew BTC/ETH calculés en temps réel à partir de Deribit, snapshot JSON public à `/api/public/snapshot`
- **Coinglass free** : funding heatmap multi-exchange, liquidation heatmap

**Horizon** : intraday (gamma flips, 0DTE) à hebdomadaire (carry).

**Saturation** : **moyenne**. Le cash-and-carry pur est exploité par les desks institutionnels mais reste accessible parce que **les spreads se rouvrent constamment** lors des pics de funding. La VRP harvesting est plus risquée (queue à gauche : un crash sur position straddle short = ruine).

### 4. Cross-asset & cross-exchange signals

**Edge potentiel** : lead-lag entre venues (papier SEC 2021 sur le bitcoin price discovery : Coinbase mène souvent en US hours, Binance en Asia hours ; Shu et al. 2023 *Accounting & Finance* sur arbitrage Coinbase-Binance), cross-cryptocurrency return predictability via LASSO (Jia-Wu-Yan-Liu 2023, *Journal of Economic Dynamics & Control* — sur Binance, 30 cryptos, période 2019–2021).

**Sources** : ccxt + WebSockets normalisés. Pour cointégration : `statsmodels.tsa.vector_ar.vecm.coint_johansen` ou test de Engle-Granger.

**Horizon** : 1s à 5min pour le lead-lag pur ; daily/weekly pour le stat arb cointégré.

**Saturation** : **élevée pour la latence pure**, **modérée pour le pair-trading multi-jour**. Drogen-Hoffstein-Otte (SSRN 4322637, 2023) : cross-sectional momentum 30j→7j génère des excess returns vs BTC. Dobrynskaya (SSRN 3913263, 2021) : momentum 2-4 semaines puis reversal au-delà d'1 mois — « faster metabolism of cryptocurrencies ». Kakushadze-Yu (arXiv 1903.06033) fournit un code open-source pour alt-BTC stat arb.

**Stratégie concrète** : portefeuille long-short cross-sectionnel sur top 30 par market cap, ranker hebdo par momentum 14j, long top 20% / short bottom 20%, rebalance hebdo. Attention : transaction costs et liquidation risk peuvent éliminer le edge (Han-Kang-Ryu SSRN 4675565, 2023, montrent que beaucoup de portefeuilles sont liquidés en pratique).

### 5. Sentiment, social, narrative

**Edge potentiel** : Kristoufek (Nature *Scientific Reports* 2013) montre relation bidirectionnelle Google Trends ↔ BTC ; Quantpedia 2024 confirme qu'un signal mixte sentiment + price ratio améliore le Sharpe d'un trend BTC.

**Sources 100% gratuites** :
- **`pytrends`** (Python, GeneralMills/pytrends GitHub, ~1.2M downloads cumulés) : interest over time, related queries — attention rate limit Google (~1400 séquentielles avant ban)
- **alternative.me Fear & Greed Index** : API JSON publique sans clé
- **Reddit PRAW** + Pushshift (gratuit, OAuth requise)
- **Twitter/X** : depuis 2023, le free tier de l'API v2 ne donne **aucun accès en lecture** au-delà de `GET /2/users/me` ; le cap de 1 500 tweets/mois s'applique uniquement à la *publication*. Pour scraper du sentiment il faut le tier Basic ($100/mois, 10 000 reads) ou le nouveau pay-per-use lancé en février 2026. Alternative : `snscrape` (légalité grise) ou scraping via Nitter mirrors
- **GitHub REST API** (5000 req/h authentifié) : `/repos/{org}/{repo}/commits` pour dev activity
- **CryptoPanic API** : free tier 100 req/jour, news taggués bullish/bearish
- **LunarCrush API** : free tier limité, Galaxy Score et AltRank
- **Santiment free** : dev activity, social volume basic
- **NewsAPI.org** : 100 req/jour gratuites

**Horizon** : daily.

**Saturation** : **faible à modérée**. Les hedge funds quant utilisent du sentiment NLP avancé mais le retail peut construire des features simples (z-score des mentions, divergence sentiment-prix) qui ajoutent de la valeur en multi-feature.

**Pièges** : ambiguïté de mots-clés (« Base » = blockchain ou autre), survivorship bias des tickers, look-ahead via timestamps de publication.

### 6. Macro & cross-market

**Edge potentiel** : la corrélation BTC–Nasdaq 100 a culminé à 0,77 (BTC–QQQ) durant la fenêtre d'adoption post-ETF (2021–2023), puis a atteint 0,87 après l'inclusion de MicroStrategy dans le Nasdaq-100 en 2024 — niveau le plus haut jamais observé selon arXiv:2501.09911 (CME Economics Research / données Bloomberg, janvier 2025). DXY négativement corrélé ; les FOMC dates créent du gamma directionnel.

**Sources** :
- **`yfinance`** Python : DXY, SPX, NDX, US10Y, gold (^GSPC, ^IXIC, DX-Y.NYB, ^TNX, GC=F)
- **FRED API** (https://fred.stlouisfed.org/) : clé gratuite, accès à 800k+ séries macro (CPI, real rates, M2)
- **Farside Investors** (https://farside.co.uk/btc/) : flows quotidiens **gratuits** des 11 spot BTC ETFs US (IBIT, FBTC, etc.) — table scrapable
- **Fed calendar** : datetime des FOMC + Powell speeches (économétrie d'événements)
- **DeFiLlama stablecoins** : market cap USDT+USDC comme proxy de liquidité crypto

**Horizon** : daily à mensuel.

**Saturation** : **faible**. Les ETF flow + stablecoin supply combinés en signal de régime macro restent sous-exploités par le retail.

### 7. Calendar & event-driven

**Edge potentiel** : Keyrock (2024) sur 16 000+ unlock events : pressure baissière persistante pré- et post-cliff unlock (-77% sur APE post-team unlock 2023, etc.). Le « Binance listing effect » est documenté par Ren & Heinrich (26 coins, échantillon 18 mois, repris par CoinDesk en janvier 2023) à +41% en 24h et +73% sur 30 jours en moyenne — **mais ce signal s'est inversé** : le dataset 7 ans d'Empirica (2024) montre désormais –1,76% à 30 jours et –22,66% à 3 mois pour la cohorte 2024. Donc le edge naïf est mort ; l'edge survivant est le **short post-listing** des micro-caps.

**Sources gratuites** :
- **TokenUnlocks.app / Tokenomist.ai** : calendrier complet vesting, free tier
- **CryptoRank.io** unlock tracker : free tier
- **Binance Announcements RSS/page** scrapable
- **Halving dates BTC** : déterministes, à coder en feature
- **ETH/L2 upgrade calendars** : EIP tracker, Beacon Chain updates

**Stratégies concrètes** :
- **Short pre-unlock** : entrer 30j avant un cliff unlock >5% du circulating, couvrir 7j post
- **Short post-listing** sur micro-cap Binance (inversion 2024 documentée par Empirica)
- **Funding 8h cycle** : sur certains exchanges le funding paie à H+0, H+8, H+16 UTC ; il existe un mean-reversion intraday autour de ces ticks

**Horizon** : event-driven, fenêtres 1-30j.

**Saturation** : **faible à modérée**. C'est probablement le meilleur risk-reward pour un retail avec peu de capital.

### 8. DEX-specific edges

**Edge potentiel** : Uniswap V3 concentrated liquidity génère des inefficiences spécifiques (JIT liquidity, sandwiching, fee farming dans des bandes étroites).

**Sources gratuites** :
- **Uniswap subgraphs** (The Graph) : tous les Swap/Mint/Burn events
- **Flashbots dashboard** (https://transparency.flashbots.net/) : MEV extraction stats publiques
- **GMX/dYdX/Hyperliquid** APIs publiques : open positions, funding, liquidations
- **Curve gauge weights** : on-chain via web3.py

**Stratégies** :
- **LP rebalancing optimal sur Uniswap V3** : modèle de range adapté à la volatilité réalisée (Loesche et al. : ~50% des LPs V3 sont non-profitables vs HODL)
- **Suivre HLP Hyperliquid** : le vault de market-making est entièrement on-chain, positions visibles. Selon l'analyse de Geronimo (« A Risk & Return Analysis of Hyperliquid's HLP Vault », Medium 2025) : *« HLP generated a lifetime compound annual growth rate (CAGR) of 42%, its CAGR over the past 12 months has fallen to 22%… annualized volatility has also dropped to 4.5%, boosting its Sharpe ratio to 5.2. »* Le rapport OAK Research S1 2025 corrobore : net performance +5,2% au Q1 2025, drawdown <3,5%. Utilisable comme baseline / signal contrarian vs retail positioning.

**Saturation** : la pure MEV (sandwich, arbitrage) est **totalement saturée** par des bots professionnels avec searcher access. Le LP active management reste exploitable.

**Pièges** : impermanent loss, gas costs sur Ethereum mainnet, JIT bots qui captent les fees des LPs passifs (research Kaiko : >$1M extraits par JIT bots avant juillet 2022).

### 9. Alternative data accessible gratuitement

- **Wikipedia pageviews API** (https://wikimedia.org/api/rest_v1/) : public, sans clé
- **App Store / Google Play rankings** : scraping `app-store-scraper` (légal en lecture publique)
- **Stablecoin supply** : DeFiLlama (cf §2)
- **Mining hash rate, difficulty** : `blockchain.info` API gratuite, mempool.space
- **Gas prices ETH** : Etherscan gas tracker, Blocknative API
- **GitHub commits** (cf §5) comme proxy de dev momentum
- **OpenSea/Magic Eden** API : NFT volume comme proxy de risk appetite retail

**Horizon** : daily.

**Saturation** : **faible**. Très peu de quants pros utilisent ces signaux car ils ne scalent pas — opportunité pour le retail.

### 10. ML / feature engineering crypto-spécifique

**Cross-sectional momentum** : Drogen-Hoffstein-Otte (SSRN 4322637, 2023) - lookback 30j, holding 7j, top quintile. À combiner avec time-series momentum (Han-Kang-Ryu 2023 : le TS momentum est plus robuste que CS en crypto).

**Volume profile** : VWAP deviation, cumulative delta, volume nodes (HVN/LVN) — exploitables sur Binance trades stream.

**Microstructure features universels** : Bieganowski-Ślepaczuk (arXiv 2602.00776) montrent que OFI, spread, VWAP-mid déviation ont la **même forme SHAP** à travers BTC/ETH/SOL/altcoins — un modèle entraîné sur BTC transfère bien (avec attention au regime shift via TimeSeries CV).

**Regime detection** : HMM 2-3 états (low-vol / high-vol bullish / high-vol bearish) sur returns log + volume — voir Giudici-Abu Hashish (Wiley 2020) ; `hmmlearn` Python. Alternative : change-point detection via `ruptures` library, ou Bayesian online change-point (Adams-MacKay 2007).

**Transfer learning** : Wood-Roberts-Zohren (arXiv 2208.09968, *Fused Encoder Networks*) — 3× Sharpe boost vs classical momentum en transférant du SPX vers le top-10 crypto via attention encoder.

**Architectures recommandées pour un M1** :
- Baseline : LightGBM/XGBoost avec ~50 features (OFI, momentum, funding, sentiment, on-chain flows)
- Avancé : Temporal Fusion Transformer (PyTorch Forecasting) ou simple LSTM 2 couches avec MC Dropout (déjà maîtrisé par l'utilisateur)
- Calibration : isotonic/Platt sur output ML pour transformer probabilités en sizing Kelly fractionné

**Pièges classiques** :
- **Look-ahead bias** : timestamp d'événement vs timestamp de réception ; clôture de bougie inclut le dernier tick déjà connu
- **Survivorship bias** : utiliser CoinMarketCap historical avec tokens delisted (la liste actuelle filtre les morts)
- **Exchange quirks** : Binance funding tous les 8h fixe, Bybit/OKX variables ; tick size différents ; mark price vs index price ; les liquidation prices visibles côté Hyperliquid mais cachées côté CEX
- **Backtesting unrealiste** : sans slippage modélisé (toujours 5-15 bps taker), sans funding accrual entre les ticks de 8h, sans queue position en maker
- **Overfitting via vibe quanting** (cf Robot James, Robot Wealth) : un edge doit avoir une **explication économique** (qui paye, pourquoi, contraint comment) avant d'être traded

## Recommendations

**Stack technique recommandé (full open-source)** :
- Data : `ccxt`, `python-binance`, `pybit`, `hyperliquid-python-sdk`, `web3.py`, `requests` pour Deribit/DeFiLlama, `pytrends`, `yfinance`
- Storage : DuckDB (colonnaire, gratuit, idéal pour millions de ticks)
- Backtest : `vectorbt` (vectorisé, rapide pour grids) ou `nautilus_trader` (event-driven, plus réaliste pour HF) ; `hftbacktest` pour market-making
- ML : scikit-learn, LightGBM, PyTorch Lightning, Optuna pour HPO ; `mapie` pour intervalles de confiance conformes
- Walk-forward : `mlxtend` ou implémentation maison avec embargo + purged k-fold (López de Prado 2018, *Advances in Financial ML*)

**Plan d'attaque staged sur 6 mois** :

**Phase 1 (mois 1-2) — Quick wins event-driven & carry** : implémenter (a) funding-rate harvesting delta-neutral sur Binance/Hyperliquid avec sizing dynamique selon Z-score du funding, (b) pré-unlock short sur tokens >5% supply unlock, (c) macro régime overlay via ETF flow Z-score. Benchmark : Sharpe out-of-sample > 1.0 sur 3 mois forward.

**Phase 2 (mois 3-4) — Cross-sectional + on-chain** : portefeuille long-short top 30 alts par momentum 14d combiné à un filtre on-chain (DeFiLlama TVL momentum + stablecoin supply Z-score). Cible : Sharpe > 1.5, max DD < 15%.

**Phase 3 (mois 5-6) — Microstructure ML** : un modèle LightGBM par exchange × asset avec features OFI/trade flow/funding/options skew, prédiction du sign return 5min, sizing Kelly fractionné. Si Sharpe out-of-sample > 1.5 sur paper trading 1 mois, passer en testnet Hyperliquid avec micro-position.

**Seuils de décision** :
- Si Sharpe walk-forward < 0.7 après 3 splits → abandonner cette piste
- Si turnover annuel > 50× avec coût total > 80% du gross PnL → restructurer en moins fréquent
- Si max consecutive losing days > 15 → revoir le sizing (régime shift non capté)

**À NE PAS faire en priorité** :
- Pure HFT cross-exchange arbitrage (vous perdez contre Wintermute)
- Sandwich/MEV (besoin Flashbots access + capital + ingénierie spécialisée)
- Sentiment Twitter avec l'API v2 free tier (zéro accès en lecture — il faut le Basic à $100/mois)
- Copy-trading aveugle des whales Nansen (signal déjà priced-in)

## Caveats

- **Le no-cost a une limite cachée** : les *historical* tick data sont rarement gratuites profondément (Binance donne 1 an, Bybit ~6 mois sur les WebSockets — au-delà, il faut Tardis.dev ou Kaiko, payants). Solution : **commencer à collecter SOI-MÊME maintenant** vers DuckDB.
- **Les « free tiers » de Glassnode/Nansen/Santiment sont volontairement frustrants** : les métriques vraiment alpha-generating sont derrière le paywall ($30–$800/mois). Ne pas perdre de temps sur les ratios MVRV publics, qui sont déjà connus de tous.
- **Le testnet Hyperliquid diffère sensiblement du mainnet** (liquidité, slippage, comportement des liquidations) — d'après la doc Hyperliquid, n'utiliser le testnet que pour valider la plomberie API, jamais pour mesurer un edge.
- **La période 2017–2022 utilisée par la plupart des papers académiques contient des régimes très différents** (bull retail 2021, hiver crypto 2022, post-ETF 2024). Toujours splitter walk-forward sur ≥ 3 régimes distincts.
- **Risque réglementaire** : MiCA en EU (2024), restriction US sur Binance.com — assurez-vous d'accès légal à l'exchange testé.
- **Risque opérationnel** : l'incident JELLY sur Hyperliquid (26 mars 2025) a causé une perte non-réalisée de $12–13,5M sur HLP au pic, avant que les validateurs ne force-delist le token à $0.0095 (sources : CoinDesk « HyperLiquid Delists JELLY After Vault Squeezed in $13M Tussle », enquête OAK Research). Rappel que même les vaults « decentralized » ont des tail risks de gouvernance.
- **Survivorship et data quirks** : CoinGecko/CoinMarketCap historical inclut le biais de survie ; CoinAPI free tier coverage limitée ; les funding rates affichés par Coinglass sont parfois en retard de quelques minutes vs API directe exchange.
- **Le retail a un edge structurel** que les pros n'ont pas : **petite taille** (vous pouvez exploiter des poches d'illiquidité où un fund ne peut pas entrer sans bouger le marché). Ne pas chercher à imiter les stratégies des grands — cherchez là où la capacité est faible mais le edge net positif.