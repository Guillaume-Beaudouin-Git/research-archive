# RAPPORT BROKER — Dédale sur Eightcap, compte 12-15k€, 2026

Mandat : réalité économique/opérationnelle du véhicule, PAS un backtest. Stratégie : FX swing
multi-paires, tenue moy. 11j, ~100 trades/an sur 10-28 paires, risque 1%/trade, stop fixe,
`IS_NEGSWAP_ALLOWED=false` (refuse tout trade à swap négatif — receveur structurel de portage).
Sources : `Forex/research/active/dedale_config_2026-08/` (worktree `Algo_claude_dedaleconf`),
`Forex/research/active/dedale_strategy_2026-08/` (worktree `Algo_claude_dedale2`).

## Réponse en quatre lignes

1. **Swaps Eightcap réels — NON TROUVÉS en table datée** : le site est une SPA JS (Contentstack),
   `WebFetch` renvoie les libellés « Swap long / Swap court » **sans valeur** sur les pages
   GBPJPY/EURJPY (vérifié directement, 2026-08-29) ; les PDF de spécifications historiques
   redirigent vers la même SPA (aucun PDF réel récupérable). Seuls des **exemples pédagogiques non
   datés ou datés 2019** existent (EURUSD long −8,28 $/lot, AUDUSD long −4,38/court +0,14,
   XAUUSD −11,27, GBPJPY 12,53/−30,18 sans source vérifiable) — **inutilisables comme niveau 2026**.
   Geste à faire soi-même : compte démo MT5 Eightcap → Market Watch → clic droit sur la paire →
   Spécification.
2. **Carry 2026 vs régime 2022-2024 (celui qui a porté le backtest) : COMPRIMÉ sur 5 croix JPY sur
   6, et INVERSÉ DE SIGNE sur CHF/JPY.** USD/JPY −34%, EUR/JPY −46%, GBP/JPY −28%, CAD/JPY −67%,
   NZD/JPY −65% ; seul AUD/JPY s'est ÉLARGI (+4%, la RBA n'a jamais baissé). Le différentiel
   théorique CHF/JPY est passé de +0,83 pp/an à **−1,00 pp/an** : un long CHF/JPY financé en JPY
   serait aujourd'hui **exclu par le filtre swap≥0 de l'EA lui-même**, alors qu'il ne l'était pas
   pendant la fenêtre de backtest.
3. **Coût (méthode = pip minimum publié + commission, PAS mesuré) : 0,66-1,18 bps RT en Raw** selon
   la croix JPY, contre 0,75 bps confirmé pour EURUSD (mesure utilisateur antérieure). **Marge et
   granularité NE bloquent PAS** à 12-15k€ : pic de marge historique mesuré sur les vraies données
   du backtest = **1 285 €, soit 10,7 % d'un compte 12k€** (6 positions concurrentes, fév. 2023) ;
   lot minimum 0,01 seulement frôlé (0,0108-0,0135 lot) lors du choc de vol mars 2020, jamais en
   régime normal.
4. **Verdict véhicule : IBKR > Eightcap pour CETTE stratégie précise.** Coût d'exécution comparable
   en ordre de grandeur (IBKR ECN ~0,5-0,7 bps RT mesuré/publié vs Eightcap Raw ~0,66-1,18 bps
   ESTIMATION) mais **le financement diffère structurellement** : IBKR crédite/débite au taux de
   marché ± spread tiered (mécanisme benchmark+spread, publié), alors qu'un swap CFD est un point
   fixe fixé par le broker des DEUX côtés (L28 : marge captée sur le long ET le short) — pour une
   stratégie dont la moitié du moteur EST le portage reçu, c'est justement le canal où Eightcap est
   structurellement défavorisé et invérifiable a priori. Eightcap reste utilisable (levier et
   granularité suffisent), mais **seulement après avoir mesuré le swap réel en direct** (point 1) ;
   IBKR est le choix par défaut si le produit CFD n'est pas requis pour une autre raison.

---

## 1. Swaps Eightcap — ce qui a été trouvé, ce qui ne l'a pas été

### 1.1 Accès direct (WebFetch, 2026-08-29)
| Page | Résultat |
|---|---|
| `eightcap.com/en/trade/gbpjpy/` | Libellés "Swap long"/"Swap court" présents, **aucune valeur** (SPA JS, contenu chargé côté client) |
| `eightcap.com/en/trade/eurjpy/` | Idem |
| `eightcap.com/en/wp-content/uploads/sites/25/2023/07/Eightcap_Instrument_and_Specifications.pdf` | 404 réel → sert le shell HTML de la SPA (pas un PDF, vérifié par `curl` : `<!DOCTYPE html>` Next.js) |
| `wordpress.dev.eightcap.com/en/trading/trading-conditions/swap-rates/` | 404 |
| `myfxbook.com/forex-broker-swaps/eightcap/1081` | 403 (anti-bot) |

**Conclusion opérationnelle : aucune donnée de swap datée 2026 n'est extractible d'Eightcap par
lecture seule.** C'est une limite du véhicule d'accès (pas de la stratégie) : la donnée existe
côté broker (dynamique, MT4/5), mais n'est publiée dans aucun HTML statique ni PDF stable indexé.

### 1.2 Exemples trouvés — tous non fiables comme niveau 2026
| Pair | Long | Short | Source | Date | Fiabilité |
|---|---|---|---|---|---|
| EURUSD | −8,278045 $/lot | — | `eightcap.com/labs/…swap-value-for-each-asset-type…` | non datée | Exemple pédagogique, formule illustrée — pas un tarif live |
| AUDUSD | −4,38 | +0,14 | `eightcap.com/labs/how-to-calculate-swap-rates/` | **2019-09-19** (datée dans l'article) | Confirmé stale, régime de taux 2019 ≠ 2026 |
| XAUUSD | −11,27 | — | idem | 2019-09-19 | idem |
| GBPJPY | 12,53 | −30,18 | synthèse WebSearch, provenance non re-vérifiable par fetch direct | inconnue | **Ne pas citer comme un fait** — non recoupé |

→ **Point 1 du mandat : NON TROUVÉ** au sens strict (aucun chiffre daté 2026 vérifiable). Le ratio
swap-mesuré / différentiel-théorique demandé ne peut donc pas être calculé avec un point 2026
fiable — seul le différentiel théorique (§2) est disponible pour comparaison future.

### 1.3 Convention Wednesday triple-swap
Confirmée en principe générique par Eightcap (« on Wednesday night the charges are for 3 days
instead of 1 », `eightcap.com/labs/how-to-calculate-swap-rates/`, 2019-09-19) — convention
standard de l'industrie FX (T+2 settlement), aucune raison de penser qu'elle a changé, mais
**non re-confirmée sur une page datée 2026**.

---

## 2. Régime de taux 2026 vs 2018-2024 — la question qui décide

Différentiels calculés à partir des trajectoires officielles des banques centrales (sources
ci-dessous). Méthode : moyenne simple des niveaux annuels connus (ESTIMATION à partir de
trajectoires documentées, PAS une moyenne quotidienne FRED point par point).

| Banque centrale | Instrument | 2018-2024 (ESTIMATION, moy. simple) | 2022-2024 (ESTIMATION) | Actuel (2026-08) | Source niveau actuel |
|---|---|---|---|---|---|
| Fed | Fed funds (mid) | ~2,31 % | ~3,91 % | **3,625 %** (3,50-3,75) | Federal Reserve H.15, 2026-08-27 |
| BoJ | Policy rate | ~−0,08 % | ~−0,06 % | **1,00 %** | CNBC 2026-07-31 ; BoJ 2026-06-16 |
| ECB | Deposit facility | ~0,70 % | ~2,24 % | **2,25 %** | TradingEconomics/ECB, 2026-08 |
| BoE | Base rate | ~1,85 % | ~3,75 % | **3,75 %** | MoneySavingExpert 2026-07-30 |
| RBA | Cash rate | ~1,81 % | ~3,17 % | **4,35 %** | RBA mr-26-19, 2026-08 |
| BoC | Overnight rate | ~2,18 % | ~3,70 % | **2,25 %** | WOWA/BoC, 2026-08 (inchangé depuis 6 réunions) |
| SNB | Policy rate | ~−0,24 % | ~0,77 % | **0,00 %** | SNB 2026-06-18 |
| RBNZ | OCR | ~2,38 % | ~4,25 % | **2,50 %** | RBNZ 2026-07 |

### Différentiel vs JPY (devise de financement de la stratégie), pp/an

| Croix | 2022-2024 (ESTIMATION) | Actuel 2026 | Δ (pp) | Δ (%) | Verdict |
|---|---|---|---|---|---|
| USD/JPY | 3,97 | 2,625 | **−1,35** | −34 % | Comprimé |
| EUR/JPY | 2,30 | 1,25 | **−1,05** | −46 % | Comprimé |
| GBP/JPY | 3,81 | 2,75 | **−1,06** | −28 % | Comprimé |
| AUD/JPY | 3,23 | 3,35 | **+0,12** | +4 % | Élargi (seule croix) |
| CAD/JPY | 3,76 | 1,25 | **−2,51** | −67 % | Comprimé, fort |
| NZD/JPY | 4,31 | 1,50 | **−2,81** | −65 % | Comprimé, fort |
| CHF/JPY | 0,83 | **−1,00** | **−1,83** | signe inversé | **MORT** — filtre swap≥0 exclurait ce sens aujourd'hui |

### Cross-check contre l'hypothèse de swap du backtest lui-même
`trades_CONFIRMED_extended_primary.csv` (290 trades, 2018-2024, 10 paires) porte une colonne
`swap_bps_annual` — l'hypothèse de swap DÉJÀ utilisée par le harnais de reproduction (pas une
mesure broker, mais le proxy du chercheur). Médiane croix JPY : **1,27 bps/nuit** (moy. 1,73,
n=88). Conversion des différentiels ci-dessus en bps/nuit théoriques (pp × 100 / 365) :

| Croix | Théorique 2022-2024 (bps/nuit) | Théorique 2026 (bps/nuit) | Ratio 2026/2022-24 |
|---|---|---|---|
| USD/JPY | 1,088 | 0,719 | 0,66 |
| EUR/JPY | 0,630 | 0,342 | 0,54 |
| GBP/JPY | 1,044 | 0,753 | 0,72 |
| AUD/JPY | 0,885 | 0,918 | 1,04 |
| CAD/JPY | 1,030 | 0,342 | 0,33 |
| NZD/JPY | 1,181 | 0,411 | 0,35 |
| CHF/JPY | 0,227 | −0,274 | signe inversé |

**Le proxy du backtest (médiane 1,27 bps/nuit) collait raisonnablement au régime 2022-2024** (du
même ordre que GBP/JPY 1,044 ou CAD/JPY 1,030 théoriques). **En 2026 la même hypothèse serait
surestimée d'un facteur 1,4 à 3× selon la croix**, et FAUSSE (signe) sur CHF/JPY. ⚠ Ceci est le
différentiel **théorique propre** (avant markup broker) — un swap CFD réel mesuré serait
vraisemblablement **encore plus bas côté receveur** (L28 : le broker capte une marge des deux
côtés), donc ce tableau est un plafond optimiste du portage 2026, pas une estimation basse.

**Réponse au point 2 du mandat : le carry s'est comprimé sur 5 croix JPY sur 6, et le mécanisme
générateur du backtest (yen faible + reste du monde en hausse de taux) s'est en grande partie
refermé — sauf sur AUD/JPY, où il tient toujours, et où il s'est même renforcé.**

---

## 3. Coûts d'exécution Eightcap — barème par paire

### 3.1 Comptes et structure
| | Standard | Raw |
|---|---|---|
| Commission | 0 | $7/lot round-turn ($3,50 x2) — confirmé 3 sources indépendantes |
| Spread minimum publié EURUSD | 1,0 pip | 0,0-0,1 pip |
| Spread minimum publié GBPJPY | 1,2 pip | 0,2 pip |
| Spread minimum publié EURJPY | 1,2 pip | 0,2 pip |
| Spread minimum publié AUDJPY | 1,0 pip | 0,1 pip |
| Spread minimum publié USDJPY | 1,1-1,2 pip | 0,1 pip |
Sources : `eightcap.com/en/trade/{gbpjpy,eurjpy}/` (WebFetch direct 2026-08-29),
compareforexbrokers.com (2026-08), tradingpedia.com (2026-08).

⚠ **« Spread minimum publié » = plancher marketing, pas une moyenne réelle** — cf. mesure
antérieure de l'utilisateur (0,81 pip réalisé sur EURUSD Raw vs 0,0-0,1 pip publié, soit 8-16×
le plancher). Aucune moyenne réelle par paire n'a pu être récupérée pour les croix JPY
(`myfxbook.com` bloqué 403) → **ESTIMATION uniquement ci-dessous, méthode = plancher publié +
commission, à corriger par le même facteur mesuré sur EURUSD une fois disponible**.

### 3.2 Barème RT estimé, compte Raw (bps du notionnel, plancher publié — probablement 2-8× trop bas)
| Paire | Spread publié (bps) | Commission (bps, notionnel ~lot) | Total ESTIMATION (bps RT) |
|---|---|---|---|
| EURUSD | ~0,1-0,9 (mesuré 0,81 pip réel) | ~0,64 | **0,75** (mesuré, ancre) |
| EURJPY | 0,118 | 0,636 | **~0,75** |
| GBPJPY | 0,105 | 0,556 | **~0,66** |
| AUDJPY | 0,102 | 1,077 | **~1,18** |
| USDJPY | 0,067 | ~0,6 | **~0,67** |

Méthode détaillée en annexe de calcul (contract size 100 000 unités, `eightcap.com/en/trade/…`
2026-08-29 ; conversion notionnel via taux indicatifs mi-2026).

---

## 4. Faisabilité opérationnelle 12-15k€ — mesurée sur les VRAIES données du backtest

Calculs faits sur `trades_CONFIRMED_extended_primary.csv` (290 trades réels, 10 paires,
2018-01→2024-07, univers confirmé du RAPPORT.md de `dedale_config_2026-08`), pas une simulation
ad hoc — colonne `notional_per_risk_unit` du moteur `dedale_engine.py`.

### 4.1 Positions concurrentes
- **Max concurrent mesuré : 6 positions** (2023-02-27, cluster EURUSD/GBPUSD/USDCHF/EURJPY/EURGBP/
  USDCAD, toutes ouvertes 2023-02-06→2023-02-27)
- Concurrence moyenne théorique = trades/an × durée/365 ≈ 100×11/365 ≈ **3,0** — le pic mesuré
  (6) est ~2× la moyenne, cohérent avec un clustering directionnel documenté ailleurs dans le
  RAPPORT (fenêtre yen faible).

### 4.2 Marge à 1:30 (CySEC), capital 12 000€, risque 1% (120€/trade)
| Métrique | Valeur | Contexte |
|---|---|---|
| Marge moyenne/position | 283 € | 100 000 unités / 30, notionnel moyen 8 482 € |
| Marge min/position | 36 € | — |
| Marge max/position | 845 € | — |
| **Marge totale au pic de concurrence (6 pos., 2023-02-27)** | **1 285 €** | **10,7 % d'un compte 12k€, 8,6 % d'un compte 15k€** |

**→ La marge NE bloque PAS.** Même au pic historique mesuré, moins de 11 % du capital est
engagé en marge — large coussin avant tout appel de marge, y compris en stackant 2-3 clusters
similaires simultanément.

### 4.3 Granularité du lot (plancher 0,01)
| Cas | sl_pips | notional_per_risk_unit | Lot-équivalent à 120€ risque |
|---|---|---|---|
| Médiane (290 trades) | ~151 | 65,6 | 0,079 lot |
| **Minimum mesuré** (AUDUSD sell, **2020-03-18**, choc COVID) | 654 | 8,99 | **0,0108 lot** |
| Cas extrême SL (GBPUSD sell, **2020-03-18**, même choc) | 1 106 | 10,66 | 0,0128 lot |

**→ La granularité NE bloque PAS en régime normal** (lot médian 8× le plancher) — contrairement
à L57 (futures à lot fixe), le pas FX de 0,01 lot donne un sizing quasi continu. **Elle est
FRÔLÉE uniquement dans un régime de volatilité extrême** (mars 2020 : spreads pivots hebdo
explosés → SL >600 pips) — à 15 000€ (150€ risque) le plancher recule à ~0,0135-0,0169 lot,
coussin supplémentaire mais pas une marge de sécurité illimitée si un choc plus violent survient.

### 4.4 Entité réglementaire, France
| | |
|---|---|
| Entité UE | **Eightcap EU Ltd**, CySEC licence 246/14, Limassol |
| Levier retail | **1:30** sur majors FX (ESMA/CySEC), 1:20 minors/indices, 1:10 commodités, 1:2 crypto |
| Protection | Protection contre solde négatif — confirmé (brokerchooser.com, brokersway.com, 2026-08) |
| Compensation | Fonds de compensation des investisseurs (ICF) Chypre, **jusqu'à 20 000 €/client** (cysec.gov.cy, brokersway.com 2026-08) |
| Résident FR | Passporting CySEC→AMF standard, pas de restriction FR spécifique trouvée (AMF applique le cadre ESMA minimal, pas de sur-restriction identifiée pour Eightcap précisément) |

Source : `brokersway.com/reviews/eightcap/regulations/cysec` (2026-08), `cysec.gov.cy` (ICF).

### 4.5 Frais de portage de compte
| Frais | Valeur | Fiabilité |
|---|---|---|
| Dépôt | 0 $ (la plupart des méthodes) | Confirmé, 3 sources |
| Retrait | 0 $ | Confirmé, 3 sources |
| Inactivité | **CONFLICTUEL** : une page dédiée BrokerChooser titrée « eightcap-no-inactivity-fee » indique aucun frais ; une autre synthèse cite 10 $/€/£ par mois après 3 mois | **Non tranché** — à vérifier dans les CGV PDF avant ouverture |
| Conversion de devise | Non chiffré publiquement — « spread + markup sur le taux LP » (dailyforex.com 2026) | Non trouvé en bps |

---

## 5. Comparaison de véhicules — Eightcap vs IBKR

| Dimension | Eightcap Raw | IBKR |
|---|---|---|
| Coût exécution majors | ~0,66-1,18 bps RT (ESTIMATION plancher, réel probablement 2-8× plus haut d'après le comparable EURUSD mesuré) | **~0,5-0,7 bps RT** : spread ECN 0,1-0,3 pip + commission dès 0,2 bps (min 2$/ticket) — publié, pas une moyenne mesurée non plus |
| Levier UE retail | 1:30 (identique) | 1:30 majors, 1:20 minors (identique, même plafond ESMA) |
| Granularité | 0,01 lot | Pas de lot MT-style — IBKR permet des tailles FX quasi-continues (unités), granularité encore meilleure |
| **Mécanisme de portage** | **Swap CFD** : point fixe publié par le broker, asymétrique par construction (L30 : le broker capte une marge des deux côtés — receveur payé MOINS que le différentiel réel, payeur facturé PLUS) | **Intérêt sur position financée** : benchmark de marché (Fed funds/interbancaire) ± spread tiered, PAS de « swap » nommé — mécanisme quasi-transparent, publié (`interactivebrokers.com/…/pricing-interest-rates.php`) |
| Triple-swap mercredi | Oui (convention CFD standard) | **Non applicable** — IBKR accrue l'intérêt quotidiennement sur le solde réel (weekend = accrual naturel sur J+2, pas de multiplicateur artificiel) |
| Fiabilité/track record | Multi-régulateur (ASIC/CySEC/FCA/SCB), pas de signal d'alerte trouvé | Coté NASDAQ, régulé multi-juridiction, référence historique |
| Frais de compte | Retrait/dépôt gratuits ; inactivité non tranchée | Frais d'inactivité existants historiquement selon palier d'activité (à vérifier séparément, hors mandat) |

**Verdict chiffré : pour une stratégie dont le moteur est le portage REÇU, le canal de financement
d'IBKR (taux de marché ± spread publié, sans marquage bidirectionnel) est structurellement plus
favorable qu'un swap CFD asymétrique (L28) — même si le coût d'EXÉCUTION des deux brokers est du
même ordre de grandeur (0,5-1,2 bps RT).** Eightcap n'est pas disqualifié (levier et granularité
suffisent au véhicule à 12-15k€), mais **aucune conclusion positive sur Eightcap ne peut être
tenue avant une mesure live du swap réel** (§1) — étape obligatoire avant financement, pas une
formalité.

---

## Ce qui reste NON TROUVÉ (à faire soi-même)
1. Table de swap Eightcap datée 2026, toutes croix JPY, long/short — nécessite MT5 démo (Market
   Watch → clic droit → Spécification) ou navigateur avec JS actif sur `myfxbook.com`.
2. Spread MOYEN réel (pas plancher) sur les croix JPY en Raw — nécessite un compte live ou
   `myfxbook.com` en navigateur (403 en lecture automatisée).
3. Frais d'inactivité Eightcap — CGV PDF à lire directement (conflit non résolu par les sources
   publiques indexées).
4. Frais de conversion de devise Eightcap en bps — non chiffré publiquement.

Δn_tests = 0. Aucune interaction avec un service (pas d'inscription, pas de formulaire, pas de
compte ouvert) — uniquement WebSearch/WebFetch en lecture + calculs sur données déjà présentes
dans le repo (`trades_CONFIRMED_extended_primary.csv`).
