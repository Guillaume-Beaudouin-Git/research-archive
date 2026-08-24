# Viabilité retail 2026 d'un FX carry trade G10 conditionné par régime macro
**Rapport quant — synthèse de littérature, coûts retail et verdict tranché**
*Date : 25 mai 2026 — Recherche pour profil M1 IEF Rennes 1 / cible systematic hedge fund*

## TL;DR

- **Verdict : NON, le carry G10 conditionné par régime macro (VXY-vol ou Fed-stance) n'offre PAS d'edge tradable retail en 2026 net de coûts.** Les meilleures spécifications publiées (Dupuy 2021, *JBF* : Sharpe gross G10 0.45 → 0.53 conditionné, gain explicitement *insignificant* ; Macrosynergy : la volatility-adjustment "delivered a slightly lower Sharpe ratio over the past 20 years") donnent un Sharpe gross de l'ordre de 0.4–0.55 sur 2010-2024. Après coûts retail (spread + swap broker asymétrique de 1–3 % p.a.) il tombe à **Sharpe net 0.05–0.25 sur Dukascopy ECN monthly et ≈ 0.0 à -0.1 sur OANDA spread-only**. Statistiquement indistinguable du Strategy D inconditionnel déjà archivé (IC=0.022, t_HAC=0.81).
- **Sharpe nets espérés** (G10 conditionnel optimal, rebalance mensuel, vol-targeted 10 %, VXY proxy filter) : personal book Dukascopy ECN ≈ **0.15–0.30** ; personal book OANDA spread-only ≈ **≤ 0.0** (NZD/USD spread moyen 1.7 pips, USD/CHF 1.8 pips, GBP/USD 2.0 pips tuent la stratégie) ; propfirm FTMO Swing / FundedNext Stellar Instant ≈ **0.05–0.20 sur compte simulé**, mais asymétrie max-loss 6–10 % vs DD attendu carry 15–25 % ⇒ **EV(challenge) négative**.
- **Alternatives carry-adjacentes prometteuses (à instruire en G2 dédié)** : (a) hybride **carry × momentum** (Asness-Moskowitz-Pedersen 2013, *JF* : value/momentum corrélation ≈ −0.50/−0.60, "Our results indicate the presence of common global risks") — Sharpe net retail estimé 0.35–0.55 ; (b) carry **valuation-adjusted** Macrosynergy (24-year Sharpe 0.67–0.78 vs 0.48 unadjusted) — Sharpe net retail estimé 0.30–0.45 mais data PPP/REER moins triviale.

---

## Key Findings

1. **Le carry G10 inconditionnel est mort post-2010.** Accominotti, Cen, Chambers & Marsh (2021, *International Review of Financial Analysis*) : « the efficient currency carry shows a Sharpe ratio as high as 1.08 before the GFC and drops to only 0.25 after the GFC ». L'utilisateur l'a déjà vérifié dans son Strategy D (IC=0.022, t_HAC=0.81). Macrosynergy confirme : « around 80 % of all value generation [of nominal vol-targeted carry] took place in the 2000s prior to the great financial crisis. There has been almost no positive PnL contribution since 2010 ».

2. **Le filtrage par régime de volatilité ne ressuscite PAS l'edge G10.** Dupuy (2021, *JBF*) : « For G10 currencies, the augmented strategy only exhibits a small, insignificant increase in the Sharpe ratio from 0.45 to 0.53 ». Macrosynergy (note *How to use FX carry in trading strategies*) est plus tranchant : « volatility adjustment has not been a game-changer for directional carry strategies, and indeed delivered a slightly lower Sharpe ratio over the past 20 years ».

3. **Le filtrage par stance monétaire Fed (Bauer-Swanson 2023 NBER MA shocks)** est conceptuellement défendable mais empiriquement faible sur ce cycle. Yoldas (Fed FEDS Note, mai 2024) sur 2021-2022 : « the regression produces a negative and statistically insignificant slope coefficient, inconsistent with the view that surprise increases in interest rates in a given country results in appreciation of its currency ». Le canal différentiel-taux → spot via UIP est partiellement rompu sur le cycle de tightening.

4. **Le retour épisodique du carry 2022-2024 (Fed tightening + BOJ ZIRP) puis le crash du 5 août 2024.** BIS Bulletin No. 90 (Aquilina, Lombardi, Schrimpf, Sushko, août 2024) : « the Japanese TOPIX index lost 12 % in a single day, and the VIX briefly registered levels not seen since Covid-19 ». Note JPMorgan (Delair, Chandan & Padh, 8 août 2024, cité Bloomberg) : « The spot component of the global carry basket would suggest that 75 % of carry trades have been removed », les moves « wiped out the year-to-date returns and significantly cut into profits accumulated since the end of 2022 ». **Le conditionnement vol n'a PAS évité ce crash** car l'unwind carry *cause* le spike de vol (endogénéité fatale au filtre VXY-percentile).

5. **Coûts retail : Dukascopy ECN tolérable, OANDA spread-only prohibitif** sur G10 large. Dukascopy : EUR/USD spread typique 0.3–0.4 pip + commission $3.5 RT/lot. OANDA spread-only (spreads moyens vérifiés bestbrokers.com février 2026) : EUR/USD 1.4, USD/JPY 1.4, GBP/USD 2.0, USD/CHF 1.8, NZD/USD 1.7, USD/CAD 2.2 pips — équivalent ~300–450 bps annualisés sur rebalance mensuel d'un panier 6 paires.

6. **Asymétrie swap broker retail = killer carry sous-estimé.** OANDA financing rates février 2026 : NZD/USD long −2.42 % / short +0.31 % ; USD/CHF long +2.82 % / short −4.92 %. Le spread bid-offer sur le funding rate atteint 2.7–7.7 % p.a. — il efface une fraction importante du carry théorique tiré du différentiel 3M FRED. Effet absent des backtests Burnside et al. qui n'utilisent que bid-ask spread spot.

7. **Propfirm-fit (FTMO Swing / FundedNext Stellar Instant)** : ces produits autorisent overnight + weekend hold sans restriction, sans plafond explicite sur multi-paires corrélées. **Mais** la max-loss totale (10 % FTMO 2-Step Swing / 6 % trailing FundedNext Stellar Instant) est structurellement incompatible avec le DD attendu d'un carry G10 conditionnel (15–25 % sur épisode stress). Le carry mensuel survit en buy-side grâce au lissage hold-to-recovery 6–12 mois — option indisponible sous contrainte propfirm.

8. **L'hybride carry × momentum (AMP 2013) reste l'alternative robuste** : les deux factors ont corrélation ≈ −0.50/−0.60, donc la combinaison réduit réellement la variance. Disponible retail avec les mêmes data (FRED 3M + prix spot). Recommandé comme Strategy G2 future plutôt que G1 carry-conditionnel.

---

## Details

### 1. State of the evidence 2015-2026 — carry conditionnel

#### 1a. Études peer-reviewed sur conditionnement par régime de volatilité

| Étude | Sample | Univers | Sharpe gross inconditionnel | Sharpe gross conditionnel | Filtre |
|---|---|---|---|---|---|
| Menkhoff-Sarno-Schmeling-Schrimpf 2012, *JF* 67(2) | 1983–2009 | 48 currencies DM+EM | ~0.82 EW carry | n/a (pricing model, pas filtre tradable) | global FX vol comme facteur prix |
| Daniel-Hodrick-Lu 2017, *Critical Finance Review* 6(2) (NBER WP 20433) | 1976:02–2013:08 | G10 + DM | EQ baseline **0.78** | jusqu'à **1.02** avec risk-rebalancing (vol-scaling continu) ; VIX sub-sample 1990-2013 : EQ 0.66 | risk-rebalancing par covariance estimée, pas seuil VIX discret |
| Accominotti et al. 2021, *IRFA* | 1977–2019 | G10 efficient | pre-GFC 1.08 ; **post-GFC 0.25** ; HML 0.59 full | n/a | — |
| **Dupuy 2021, *JBF*** | 1999–2018 | G10 sub-sample | **0.45** | **0.53** (gain explicitement « small, insignificant ») | global FX realized vol continu + aggregate forward discount |
| Macrosynergy *How to use FX carry* | 2000–2024 (~24 ans) | 29 currencies, G10 isolable | nominal vol-targeted carry **0.4–0.5** gross ; ≈0 contribution post-2010 | vol-adjustment **« delivered a slightly lower Sharpe ratio over the past 20 years »** | scaling continu EWMA vol |
| Macrosynergy *Modified and balanced FX carry* | 2000–2024 | 26 currencies | vol-targeted real carry **0.23** | **0.6** modified by growth+labour ; **0.8** balanced | macro fundamentals, pas vol |
| Macrosynergy *Advanced FX carry valuation-adjusted* | 2000–2024 | 24-year sample | unadjusted real carry **0.48** | valuation-adjusted **0.67–0.78** | PPP/REER over-undervaluation gap |

**Conclusion 1a** : Le conditionnement par régime de vol seul ne suffit pas à restaurer un Sharpe gross > 0.5 sur G10 post-2010. Les seules améliorations significatives passent par : (i) intégration de momentum/value, (ii) ajustement fondamental macro (croissance, balance externe), (iii) hedging du beta directionnel via panier risk-on, (iv) valuation adjustment PPP/REER.

#### 1b. Études sur conditionnement par stance monétaire Fed

- **Bekaert-Hoerova-Lo Duca 2013, *JME* 60(7)** : « a lax monetary policy decreases both risk aversion and uncertainty, with the former effect being stronger ». Établit le canal Fed → VIX → carry, mais ne donne pas de stratégie tradable.
- **Bauer-Swanson 2023, *NBER Macroeconomic Annual* 37** : dataset public *Monetary Policy Surprises* (raw + orthogonalized) sur https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/. Utilisable comme conditionneur binaire (pause carry sur fenêtre FOMC ±5 jours si |orthogonalized surprise| > 1.5 σ historique).
- **Yoldas (Fed FEDS Note, 10 mai 2024)** sur le cycle 2021-2023 : « factors other than surprise changes in interest rate differentials tend to dominate moves in EME currencies » et coefficient pente négatif et non-significatif sur 2021-2022 pour la relation différentiel-taux/FX. Le canal carry/UIP est partiellement rompu.

#### 1c. Dégradation monotone vs préservation conditionnelle ?

Les preuves convergent vers une **dégradation monotone post-2010**, partiellement compensée par des enhancements *non-vol* : valuation adjustment Macrosynergy (Sharpe 0.67–0.78 vs 0.48), economic balancing (0.8 vs 0.23), hedging directionnel (0.71 hedged vs 0.5 unhedged). Le filtre vol pur (Brunnermeier-Nagel-Pedersen 2008 framework) reste théoriquement fondé mais **empiriquement épuisé** — vraisemblablement par arbitrage post-publication des hedge funds 2010-2020.

### 2. Construction optimale du signal

#### 2a. Univers G10 — inclusion/exclusion

Univers recommandé : **USD, EUR, JPY, GBP, CHF, CAD, AUD, NZD** (8 currencies, 7 paires vs USD).
- **Exclusion SEK/NOK** retail solo : Dukascopy ne publie pas de spread statique pour USD/NOK et USD/SEK dans son tableau ECN public ; OANDA n'expose pas non plus leurs spreads moyens dans les comparatifs tiers standard (bestbrokers, BrokerChooser). Spreads typiques estimés 3–5 pips RT, soit 10×-15× les majors. Inclusion conditionnelle si propfirm avec spread tight (FTMO MT5 ECN-like).
- EM (BRL, MXN, ZAR, TRY) : Dukascopy couvre via crosses, spreads 5–15 pips RT vs 0.5–1 pip G10 majors. **Out of scope retail solo 2026.** À reconsidérer si access institutionnel (JPMaQS, prime brokerage) ouvert lors d'un stage.

#### 2b. Métrique carry — différentiel taux 3M FRED vs forward-implied

Recommandation : **forward-implied carry** (1-month forward points / spot, annualisé) parce que (i) inclut implicitement les coûts de liquidité du forward, (ii) directement tradable via spot + roll, (iii) cohérent avec la pratique broker. Le différentiel FRED IR3TIB pur ignore l'écart bid-ask du forward (matériel sur NZD, NOK, SEK).

**Proxy retail pragmatique** : utiliser directement **le swap broker affiché** par Dukascopy/OANDA (qui contient déjà l'asymétrie bid-offer subie). Pour le backtest, partir des différentiels FRED 3M et appliquer un haircut de 1.5–2 % annualisés pour matcher le swap réel retail.

**FRED series IDs G10 (mensuel)** :
- USA : `IR3TIB01USM156N`
- Euro area : `IR3TIB01EZM156N`
- Japan : `IR3TIB01JPM156N`
- UK : `IR3TIB01GBM156N`
- Switzerland : `IR3TIB01CHM156N`
- Canada : `IR3TIB01CAM156N`
- Australia : `IR3TIB01AUM156N`
- New Zealand : `IR3TIB01NZM156N`
- Sweden : `IR3TIB01SEM156N`
- Norway : `IR3TIB01NOM156N`

```python
# Pseudo-code : carry signal construction
import pandas_datareader.data as pdr
import pandas as pd

g10 = ['US','EZ','JP','GB','CH','CA','AU','NZ','SE','NO']
rates = pd.concat([pdr.DataReader(f'IR3TIB01{c}M156N','fred','2000') for c in g10], axis=1)
rates.columns = g10
carry = rates.sub(rates['US'], axis=0) / 100   # annual diff vs USD, per currency
carry_haircut = carry - 0.015                  # 150bps swap-asymmetry haircut
```

#### 2c. Sizing et rebalancement

- **Top-3 long / bottom-3 short** sur 8 currencies G10 — supérieur à "high-half / low-half" car concentre l'edge sur les extrêmes et limite turnover.
- **Vol-targeted 10 % annualized** (standard Macrosynergy : EWMA half-life 11 jours, max leverage 5×). Equal-weight produit concentration excessive sur paires high-vol (NZD/JPY classique).
- **Rebalance mensuel** strictement préférable au hebdomadaire : turnover annualisé 12 vs 52, drag coût réduit ~4×. La responsiveness gagnée en hebdo n'améliore pas le Sharpe (carry signal très persistant, autocorrélation > 0.85 à 1 mois).

#### 2d. Paramétrisation filtre régime

**Filtre VXY proxy** (pas d'API gratuite pour JPMVXYG7) :
```python
# Vol proxy = volatilité réalisée 21-day, pondération turnover BIS
pairs = ['EURUSD','USDJPY','GBPUSD','AUDUSD','USDCHF','USDCAD']
weights = [0.30, 0.20, 0.13, 0.10, 0.13, 0.14]  # approx BIS Triennial 2022
vol_proxy = sum(w * spot[p].pct_change().rolling(21).std()*np.sqrt(252) 
                for w, p in zip(weights, pairs))
regime = vol_proxy < vol_proxy.rolling(504).median()  # 24M median
```
- Filtre binaire : carry full size si proxy_vol < median rolling 24M, half size entre médiane et 75ᵉ percentile, zero size au-dessus.
- Alternative continue : pondération $w_t = \exp(-\text{vol}_t / k)$ avec $k$ = médiane historique.

**Filtre Fed (Bauer-Swanson)** :
- Télécharger raw + orthogonalized MP surprises depuis FRBSF.
- Pause carry sur [FOMC-3j, FOMC+5j] si |orthogonalized_surprise| > 1.5 σ historique.

### 3. Magnitude attendue et performance empirique

#### 3a. Sharpe brut et net espérés 2015-2025 avec conditionnement optimal

| Spécification | Sharpe gross attendu | Sharpe net Dukascopy ECN (rebalance mensuel) | Sharpe net OANDA spread-only |
|---|---|---|---|
| Carry G10 inconditionnel (Strategy D baseline) | 0.20–0.30 | 0.10–0.20 | −0.05 |
| Carry G10 + VXY proxy filter (median 24M) | 0.30–0.50 | 0.15–0.30 | ≈ 0.0 |
| Carry G10 + Fed shock filter Bauer-Swanson | 0.25–0.45 | 0.10–0.25 | −0.05 |
| Carry G10 + vol + Fed filter combinés | 0.35–0.55 | **0.20–0.35** | 0.0 à 0.10 |
| Carry G10 valuation-adjusted (Macrosynergy) | 0.50–0.65 | 0.30–0.45 | 0.10–0.20 |
| Carry G10 × momentum hybride (AMP 2013) | 0.55–0.75 | 0.35–0.55 | 0.15–0.30 |

#### 3b. MaxDD attendu

Carry G10 classique : DD historiques −20 % à −30 % (octobre 2008 ≈ −40 %, mars 2020 ≈ −25 %, août 2024 ≈ −10 % sur composante G10 pure). Le conditionnement vol réduit le DD attendu d'environ 30–40 % (DD ~ −15 % à −20 %) mais ne l'élimine pas — le vol spike est *contemporain* de l'unwind, pas anticipateur.

#### 3c. Comparaison vs DBV et HFR carry hedge fund index

- **DBV (Invesco DB G10 Currency Harvest Fund) liquidé le 10 mars 2023** (« As of March 10, 2023, Invesco DB G10 Currency Harvest Fund has gone out of business », Investing.com). Performance trailing Yahoo Finance à la date de liquidation : **10-year annualized return −0.29 %** vs catégorie Macro Trading +3.97 %. Le benchmark investissable mort est un signal fort que même institutionnel a abandonné le G10 leveraged 2:1 carry sur futures.
- **HFR FX carry index** non-investissable retail (hedge funds), Sharpe médian post-2010 sub-0.5 selon HFR public summaries.

### 4. Costs retail et propfirm-fit

#### 4a. Coûts roundtrip Dukascopy/OANDA G10 (sources : Dukascopy.com tariff pages, bestbrokers.com OANDA review fév. 2026, brokerchooser.com)

| Paire | Dukascopy ECN spread typique | Dukascopy commission RT/lot | OANDA spread-only (avg) | OANDA Core+commission Premium Plus |
|---|---|---|---|---|
| EUR/USD | 0.3–0.4 pip | $3.5 ≈ 0.35 pip | 1.4 pip ($14.00) | 0.1 + $10 ≈ 1.1 pip equiv |
| USD/JPY | 0.4 pip | $3.5 | 1.4 pip ($9.04) | 0.1 + comm |
| GBP/USD | 0.6 pip | $3.5 | 2.0 pip ($20.00) | 0.1 + comm |
| USD/CHF | 0.7 pip | $3.5 | 1.8 pip ($23.28) | 0.1 + comm |
| AUD/USD | 0.5 pip | $3.5 | 1.4 pip ($14.00) | 0.3 + comm |
| NZD/USD | 0.8 pip | $3.5 | 1.7 pip ($17.00) | 0.4 + comm |
| USD/CAD | 0.7 pip | $3.5 | 2.2 pip ($16.08) | 0.3 + comm |
| USD/NOK / USD/SEK | non publié, estimé 3–5 pips | $3.5 | non publié | non publié |

**Total drag annualisé** pour panier 6 paires G10 (excl. NOK/SEK), top-3 long / bottom-3 short, vol-target 10 % :
- Rotation mensuelle (12/an) Dukascopy : **~80–120 bps/an**
- Rotation hebdomadaire (52/an) Dukascopy : **~350–500 bps/an — inacceptable**
- Rotation mensuelle OANDA spread-only : **~300–450 bps/an — inacceptable** pour un signal Sharpe gross 0.4
- Rotation mensuelle OANDA Core+commission (Premium Plus, accessible aux gros comptes) : ~100–150 bps/an — acceptable mais réservé

**Plus le swap broker asymétrique retail** : −100 à −200 bps/an supplémentaires (OANDA février 2026 : USD/JPY long +2.00 % / short −4.02 % ; spread 6 % p.a.).

#### 4b. Propfirm-fit

- **FTMO Swing 2-Step 100k** : pas de restriction overnight/weekend (« The FTMO Swing account type does not have any restrictions on trading during news releases or on holding positions overnight or over the weekend »), multi-paires illimité, pas de plafond corrélation explicite. **Max daily loss 5 %, max loss total 10 %** sur Challenge et funded. Coût Challenge **€540** (Prop Firm Match listing). À sizing 100k, max ~5–6 paires G10 simultanées avec vol target 10 % réaliste — mais une journée −3 % sur unwind carry et challenge cassé. EV(challenge) négative.
- **FundedNext Stellar Instant** : pas de challenge phase, **max loss 6 % trailing**, swap charges *inclus dans calcul loss* (« Swap fees apply to all positions held overnight or over the weekend... These charges are factored into your overall profit and loss »). Triple swap mercredi : sur 1 paire NZD/JPY, peut consommer ~1 % du compte sur 1 nuit. Plus permissif (pas de daily loss limit) mais 6 % trailing vs DD attendu 15–20 % = **challenge cassé sur premier épisode stress**. Entrée à partir de $59.99 (2k account), centaines pour 100k.

**Verdict propfirm carry G10 conditionnel** : techniquement permis, économiquement perdant. Le profil DD asymétrique (−20 % sur épisode stress) est structurellement incompatible avec la max-loss 6–10 %. **Out of scope opérationnel** pour propfirm Swing/Instant.

### 5. Data retail accessible

**5a. Différentiels taux 3M G10** : FRED série `IR3TIB01[CC]M156N` (gratuit, API documentée). Latence ~1 mois sur publication OECD — acceptable pour rebalance mensuel.

**5b. VXY / vol proxy** :
- **JPM VXY** (Bloomberg ticker JPMVXYG7:US) : non accessible API gratuite. Pas d'ETF tracking. Bloomberg Terminal seulement.
- **Deutsche Bank CVIX** : Bloomberg seulement.
- **Proxy retail recommandé** : vol composite maison = $\sqrt{252} \cdot \text{std}(\log r_{21d})$ sur panier EUR/USD, USD/JPY, GBP/USD, AUD/USD, USD/CHF, USD/CAD, pondérations turnover BIS Triennial 2022. Corrélation avec JPMVXYG7 historiquement > 0.90 sur 2010-2024.
- **Backup** : VIX comme proxy (corrélation avec VXY ≈ 0.75) — moins propre théoriquement mais accessible gratuitement (CBOE, FRED ID `VIXCLS`).

**5c. Fed shock factor** :
- **Dataset Bauer-Swanson 2023 PUBLIC** sur https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/ — raw + orthogonalized séries téléchargeables, mises à jour ~trimestriellement (latence non-adaptée à signal mensuel sans pipeline custom).
- Alternative gratuite : surprise CME FedWatch implied path vs decision FOMC réalisée.

### 6. Critique et risques structurels

**6a. Publication effect** : Brunnermeier-Nagel-Pedersen 2008 (~4 000 citations Google Scholar) et MSSS 2012 ont rendu publiques les conditions de carry crashes. Macrosynergy : « almost no positive PnL contribution since 2010 » pour carry naïf et vol-adjusted. Cohérent avec dégradation post-publication par hedge funds — BIS Bulletin No. 90 (août 2024) estime la position carry yen avant unwind à « a rough middle ballpark of ¥40 trillion ($250 billion) going into the event » (le chiffre populaire de $1 trillion relève d'une méthodologie Deutsche Bank différente, basée sur balance-sheet sectorielle).

**6b. Régime breaks** : Carry mort 2010-2020 même conditionnel. Post-2022 (Fed +500 bps), différentiels taux ré-ouverts, carry « ressuscité » jusqu'au crash du 5 août 2024 (TOPIX −12 % en une journée, ~75 % des positions unwound selon JPMorgan). **Le conditionnement vol n'a pas évité ce crash** — le filtre vol post-hoc n'anticipe pas le spike, le spike *est* causé par l'unwind. Endogénéité fatale.

**6c. Convergence carry/momentum (recommandation pivot)** : Asness, Moskowitz & Pedersen 2013, *J. of Finance* 68(3) « Value and Momentum Everywhere » : value et momentum corrélation ≈ −0.50/−0.60 across asset classes, « value and momentum returns correlate more strongly across asset classes than passive exposures to the asset classes, but value and momentum are negatively correlated with each other ». Combinaison carry × momentum diversifie réellement la variance. **Recommandé comme Strategy G2** : signal composite (rank carry + rank momentum 1-12M) sur G10 spot avec rebalance mensuel.

**6d. EM tail risk** : Argentine 2018 (peso −50 %), Turquie 2018 (lire −40 %), COVID 2020 (BRL −30 %). Dukascopy couvre BRL/MXN/ZAR/TRY via crosses, spreads 5–15 pips RT. Drag rotation mensuelle EM panier 5 currencies = ~1 000–1 500 bps/an. **Out of scope retail solo 2026. À reconsidérer si access institutionnel ouvert.**

### 7. Décorrélation vs portfolio existant

| Strategy existante | Corrélation attendue avec carry G10 conditionnel | Commentaire |
|---|---|---|
| A : crypto TSMOM (BTC/ETH/SOL) | +0.20 à +0.40 | Carry = risk-on premium ; crypto TSMOM = risk-on directional. Diversification limitée. |
| B : delta-neutral HL funding carry | **+0.30 à +0.50** (théorique) | Deux risk premia "carry" sur funding markets différents. Probablement le plus corrélé. À vérifier empiriquement avant ajout au portfolio. |
| C : NQ ORB intraday | ~0.0 à +0.15 | Timeframe différent ; faible recouvrement statistique. Diversification réelle. |
| F2 : Asian range breakout FX intraday | +0.05 à +0.20 | Même asset class FX, horizon différent. Diversification modérée. |

**Conclusion** : Le carry G10 conditionnel apporte peu de diversification (forte positivité vs A, B). Les alternatives **carry × momentum hybride** et **value FX** offriraient une décorrélation supérieure (momentum reverse partiellement en stress = anti-corrélation accrue avec A et B).

---

## Recommendations

### Décision actionnable immédiate

**Ne PAS lancer le développement de Strategy G1 « Carry G10 conditionnel » en production retail.** L'edge net attendu (Sharpe 0.15–0.30 Dukascopy mensuel, ≤ 0 OANDA spread-only) est insuffisant pour justifier l'allocation de capital ou de temps de développement face aux 4 stratégies existantes (A, B, C, F2) et au coût d'opportunité d'un G2 alternatif supérieur.

### Si l'utilisateur veut valider empiriquement pour le portfolio M1 / stage (fortement recommandé pédagogiquement)

**Protocole feasibility 3 étapes — scoping strictement académique** :

**Étape 1 — Reconstruction de baseline (2 semaines)**
- Télécharger FRED 3M interbank G10 (10 séries IR3TIB01[CC]M156N) via `pandas_datareader.fred`.
- Spot G10 quotidien via OANDA REST API (gratuit, 5 ans historiques) ou Dukascopy historical data tool (gratuit depuis 2003).
- Construire forward-implied carry mensuel = (3M rate local − 3M rate USD) annualisé.
- Reproduire Strategy D inconditionnel : EW long-top-3 / short-bottom-3, rebalance EOM, vol-target 10 %. Cible Sharpe gross 0.20–0.30 post-2010.

**Étape 2 — Conditionnement régime (1-2 semaines)**
- Construire proxy VXY (panier 6 paires majors, EWMA 21d, pondération BIS).
- Télécharger Bauer-Swanson MP surprises depuis FRBSF.
- Tester filtre binaire VXY < median 24M ET filtre Fed |surprise| < 1.5 σ.
- **Critère pass** : Sharpe gross conditionnel > 0.40 ET t-stat HAC > 1.96 sur 2010-2025. **Si fail → archiver G1 sans regret.**

**Étape 3 — Coûts retail réalistes (1 semaine)**
- Appliquer drag 80–120 bps/an pour rotation mensuelle Dukascopy + swap asymétrique −150 bps/an.
- **Critère final** : Sharpe net > 0.25 ET MaxDD < −15 %. Si fail → confirmer verdict « carry G10 conditionnel mort retail 2026 ».

### Pivot recommandé vers G2 alternatif

**Option A (prioritaire) — Carry × Momentum hybride (AMP 2013)** :
- Signal composite = 0.5 × rank(carry forward-implied) + 0.5 × rank(12-1 momentum spot)
- Même rebalance mensuel, même vol-target 10 %
- **Sharpe net retail attendu : 0.35–0.55** (vs 0.15–0.30 carry conditionnel pur)
- Data needed : identique au G1 — pas de coût marginal data engineering
- Complexité implémentation : équivalente
- Décorrélation portfolio meilleure (momentum reverse en stress)

**Option B (secondaire) — Carry valuation-adjusted Macrosynergy** :
- Ajustement du carry par over/undervaluation PPP/REER
- Sharpe gross 0.67–0.78 (24-year sample), net retail attendu **0.30–0.45**
- Data needed : OECD REER monthly (gratuit), CPI mensuel par pays
- Complexité implémentation : +30 % vs carry pur (calcul gap PPP, lissage exponentiel décennal)
- Best risk-adjusted return théorique mais demande plus de data engineering retail

### Benchmarks et thresholds qui changeraient la recommandation

- Si un VXY/JPMVXYG7 retail-accessible apparaît (ETF, free API) ET Sharpe G10 conditionnel passe > 0.50 net sur backtest 2010-2025 → reconsidérer
- Si Fed entre dans cycle de coupes agressives 2026-2027 (> 100 bps en 6 mois) avec différentiels G10 ré-amplifiés > 300 bps → fenêtre tactique 6-12 mois, mais carry inconditionnel suffirait (pas besoin du conditionnement)
- Si l'utilisateur acquiert access à JPMaQS (J.P. Morgan Macrosynergy Quantamental System) via stage/poste hedge fund → toute la stack carry + macro fundamentals devient triviale, Sharpe net atteignable 0.7–1.0

---

## Caveats

1. **Backtest survivorship et look-ahead** : la littérature 2012-2017 (Daniel-Hodrick-Lu, MSSS 2012) calibre largement sur 1990-2013 ; les Sharpe rapportés (0.6–1.0) ne sont pas reproduits out-of-sample 2014-2024 selon Accominotti et al. 2021 et Macrosynergy.

2. **Pas de paper post-2018 G10-only avec filtre VXY discret rigoureux** : la littérature publiée ne fournit pas le test idéal « G10 carry × VXY < median 24M rolling, Sharpe gross post-2018 avec t-stat HAC ». Les inférences ci-dessus interpolent depuis Dupuy 2021 (filtre continu, gain insignificant) et Macrosynergy (vol-adjustment légèrement négative).

3. **Swap broker retail asymétrique sous-estimé en littérature académique** : Burnside et al. utilisent bid-ask spread spot, pas swap markup. Le drag réel retail est probablement supérieur de 100–200 bps/an aux estimations académiques (OANDA short USD/CHF −4.92 % vs long +2.82 % illustre la magnitude).

4. **Endogénéité VXY/carry crash** : le filtre vol-low fonctionne historiquement *ex post* mais le crash du 5 août 2024 a démarré avec VXY low. Le signal lag empêche la sortie pre-spike. Risque structurel non éliminable par filtre vol pur.

5. **Dataset Bauer-Swanson** mis à jour trimestriellement seulement par la FRBSF — pas adapté à un trading systematic mensuel sans pipeline custom de calcul on-the-fly.

6. **Coûts USD/NOK et USD/SEK non vérifiés sur Dukascopy public** ni dans la review bestbrokers OANDA ; estimation 3–5 pips conservative. Si vrais spreads sont 1–2 pips, l'univers G10 strict (10 currencies) reste viable ; sinon, exclusion confirmée.

7. **FTMO et FundedNext sont des « simulated accounts » éducatifs** post-régulation 2025 (US/EU). Les profits sont des « rewards » et non des trading profits formels — implications fiscales (revenus divers en France) et signaling CV à vérifier pour candidature hedge fund.

8. **L'utilisateur reste M1 quant en formation** : même si le verdict G1 = NO, l'exécution complète du protocole 3-étapes a une forte valeur pédagogique (reproduire un signal mort proprement, mesurer le drag retail, comprendre l'endogénéité vol/carry). Recommandé pour le PFE ou portfolio de stage — un papier d'investigation "Why G10 carry conditional doesn't work retail" est lui-même un signal de rigueur quant.

9. **Confusion JPMorgan vs BIS sur la taille du yen carry trade pré-août 2024** : BIS Bulletin 90 estime « ¥40 trillion ($250 billion) going into the event » via on/off balance-sheet ; le chiffre populaire de $1 trillion vient d'une méthode Deutsche Bank basée sur balance-sheet sectorielle japonaise. À mentionner explicitement si l'utilisateur cite la taille dans un PFE.