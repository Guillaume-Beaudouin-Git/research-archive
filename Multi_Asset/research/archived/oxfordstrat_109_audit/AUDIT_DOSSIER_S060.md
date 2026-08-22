# Dossier d'audit indépendant — Stratégie #60 « Oops Bullish » (gap-down-fade)

*Pour audit externe par l'équipe quant. Auteur : pipeline oxfordstrat_109. Date : 2026-06-07. `ftmo_lab.py` @ commit 9dea332.*

---

## 0. Avertissement — correction majeure suite à cet audit

Ce dossier **corrige à la baisse** le verdict précédent. La version antérieure (`AUDIT_S060_deepdive.md`) annonçait un **Sharpe 2,9–3,1 et un beta ≈ 0** et classait #60 en **KEEP**. En préparant ce dossier reproductible j'ai trouvé que **ces chiffres étaient gonflés par une erreur de méthode de ma part** (voir §5). Mesuré correctement :

| | Annoncé (faux) | **Corrigé (mark-to-market)** |
|---|---|---|
| Sharpe portefeuille (délai+1, déployable) | 2,1–3,1 | **0,70** |
| Sharpe couvert-beta | 2,9 | **0,41** (marginal, t=2,2) |
| Beta au marché | 0,012 | **0,07** |
| Sharpe couvert, **indices seuls (données propres)** | — | **0,12 (t=0,61, NON significatif)** |
| Verdict | KEEP | 🟡 **BORDERLINE — non prouvé** |

**Ce qui reste vrai** : il existe un **petit edge positif par trade**, significatif au bootstrap, **y compris sur données propres** (indices : expR +0,031 R net, IC95 [+0,014 ; +0,050]). **Ce qui était faux** : sa traduction en Sharpe de portefeuille. L'edge est **réel mais modeste**, pas un alpha market-neutral exceptionnel. Le burden of proof pour un KEEP n'est **pas** atteint. Votre audit est justifié.

---

## 1. Résumé exécutif

La stratégie fade les gaps baissiers : après une ouverture sous le plus-bas de la veille, on achète au *reclaim* de ce plus-bas (rebond de réversion overnight). Long-only, ~13 jours de détention, sortie stop ATR.

- **Edge par événement** : réel et significatif (expR net délai+1 ≈ +0,03 à +0,06 R, IC bootstrap > 0), présent sur indices (propres) et commodités. Négatif sur forex.
- **Edge en portefeuille** : modeste. Sharpe mark-to-market **~0,7 brut / ~0,4 couvert-beta** (délai+1). **Pas** significatif une fois le beta retiré sur les indices seuls.
- **Risque data** : le sleeve le plus fort (commodités) repose sur des **futures continus Yahoo Finance** (proxy des CFD FTMO). Risque écarté en partie (les gaps fadés sont petits, pas des sauts de roll), mais **à revalider sur données FTMO réelles**.
- **Verdict** : 🟡 BORDERLINE. À valider indépendamment avant tout capital.

---

## 2. Données utilisées

### 2.1 Magasin OHLC
30 instruments, OHLC **journalier** (+ colonne `spread` pour les sources tick). Stockés en `ohlc/{INSTR}.parquet`, index `Date` (datetime), colonnes `open, high, low, close[, spread]`. Inventaire complet : `ohlc/_coverage.csv`. Construit par `code/build_ohlc_store.py`.

### 2.2 Provenance & couverture (table d'audit)

| Classe | Instruments | Source | Période | Remarque qualité |
|---|---|---|---|---|
| **Indices** (10) | US500, US100, US30, US2000, GER40, UK100, EU50, AUS200, JP225, HK50 | `ftmo_panel` | 2000→2026 (~6 600 j ; EU50 2007+) | **Meilleure qualité.** Données type-FTMO, longue histoire. |
| **Commodités** (9) | XAGUSD, XPTUSD, XPDUSD, COCOA, COFFEE, SOYBEAN, WHEAT (2005+), UKOIL (2007+), XAUUSD (2018+) | **Yahoo Finance futures continus** (`CC=F, KC=F, ZS=F, ZW=F, SI=F, PA=F, PL=F, BZ=F`) ; XAUUSD = resample M1 | 2005→2026 | ⚠️ **Futures continus ≠ CFD FTMO.** Risque de gaps de roll (voir §7.6). Porte l'edge le plus fort. |
| **Crypto** (2) | ETHUSD (2017+), BTCUSD (2018+) | yf + resample M1 | 2017/18→2026 | Peu de trades (n=64). |
| **Forex** (9) | EURUSD/AUDUSD/USDCAD/USDJPY (2018+), GBPUSD/NZDUSD/USDCHF/EURGBP/AUDJPY (2021-22+) | resample M1 (tick broker) | 2018→2025 | Histoire **courte**, proxy. **expR négatif → retiré du sleeve déployable.** |

**Points d'attention data pour l'audit :**
1. **Hétérogénéité des sources** : indices (panel propre), commodités (futures yf), crypto/or/forex (resample M1). Pas une source unique homogène.
2. **Breadth variable dans le temps** : ~16 instruments dispo en 2005, ~18 en 2010-2015, ~21 en 2020+. Les sous-périodes anciennes (2007-2012) ne reposent **que sur indices + commodités**. La diversification « ~6 positions concurrentes » n'est pleine que **post-2018**.
3. **Fin de données** : indices/commodités jusqu'à ~2026-05, forex jusqu'à ~2025-06. Léger décalage de fin.
4. **Pas de survivorship classique** (tous les instruments existent encore), mais **biais de sélection** : on teste l'univers tradable *d'aujourd'hui* sur l'histoire.

---

## 3. Spécification exacte de la stratégie (reproductible sans le code)

**Univers** : 30 instruments ci-dessus. Déployable recommandé : **indices + commodités (+ crypto), SANS forex**.

**Indicateurs** (sur chaque instrument, données jusqu'à la barre `i-1` uniquement) :
- `ATR20[i]` = moyenne mobile simple sur 20 j du True Range (`max(H−L, |H−Cprec|, |L−Cprec|)`).

**Entrée (long uniquement), barre `i`** :
1. Gap baissier : `Open[i] < Low[i−1]`.
2. Niveau de reclaim : `lvl = Low[i−1]` (plus-bas de la veille, **connu d'avance**).
3. Déclenchement : la position s'ouvre **seulement si** `High[i] ≥ lvl` (le prix remonte toucher le plus-bas de la veille).
4. **Prix d'entrée** selon l'hypothèse de fill (levier d'audit, cf. §5) :
   - `stop` (optimiste) : `max(Open[i], lvl)` intrabar — *à ne pas utiliser pour conclure*.
   - **`next_open` (réaliste, retenu)** : `Open[i+1]`.

**Risque & sortie** :
- `risk0 = ATR20[i] × 6` (distance de stop catastrophe, unité de normalisation R).
- **Stop de sortie** : `Entrée − ATR20[i] × 3` (ATR_Index = 3) ; touché si `Low[j] ≤ stop`.
- **Sortie temporelle** : clôture de la barre `i + 10` (Time = 10) si le stop n'est pas touché.
- Premier des deux atteint → sortie.

**Position sizing** : fixed-fractional, **0,5 % du capital risqué par trade** au stop initial (`RISK_FRAC = 0,005`). PnL exprimé en **R** (multiples du risque initial), additionnable entre instruments.

**Coûts** (par round turn, en bps du notionnel, modèle `round_turn_cost_bps`) : `spread médian (si dispo) + commission_classe + 2 bps slippage`, **planchonné** par classe : forex 1,5 / indices 2,0 / commodités 4,0 / crypto 8,0 bps. Commission RT : forex 0,5 / commodités 0,3 / crypto 2,0 / indices 0 bps.

**Point de référence** : ATR_Index = 3, Time = 10 (plateau, cf. §6.4).

---

## 4. Réconciliation des trois « Sharpe » (lire avant tout chiffre)

Trois constructions coexistent dans ce projet ; elles ne mesurent **pas** la même chose :

1. **Sharpe par trade (séquentiel)** — `ftmo_lab.trade_metrics` : moyenne/écart-type des R par trade, annualisé par trades/an, équité compoundée trade après trade. Délai+1 ≈ **1,1**. *Mesure « le trade moyen gagne-t-il ? ».*
2. **Sharpe portefeuille par R étalé** — ⚠️ **biaisé (mon erreur)** : chaque R étalé uniformément sur ses ~13 jours de détention, positions concurrentes sommées. Donne **2,0–3,1**. **À rejeter** (cf. §5).
3. **Sharpe portefeuille mark-to-market** — ✅ **correct** : PnL quotidien réel close-to-close de chaque position ouverte, sommé sur les positions concurrentes. Délai+1 ≈ **0,70** (déployable). *C'est le chiffre exploitable.*

---

## 5. L'artefact trouvé : le lissage par étalement (cause du Sharpe gonflé)

**Le bug.** Pour passer des trades à une série quotidienne, ma méthode initiale (`s060_deepdive.strat_daily`) **étalait le R d'un trade uniformément sur ses jours de détention** (`R/len(jours)` par jour). Étaler un PnL sur 13 jours **écrase la variance quotidienne** : vol annualisée mesurée **1,1 %** au lieu de **3,5 %** réels → Sharpe gonflé d'un facteur ≈ 3, et **biais du beta vers 0** (la covariance jour-à-jour avec le marché est détruite par le lissage).

**La correction.** En marquant le PnL **close-to-close réel** (`s060_audit`, §8) :

| Série (délai+1, déployable) | vol ann. | Sharpe |
|---|---|---|
| R étalé (faux) | 1,1 % | 2,1 |
| **Mark-to-market (correct)** | **3,4 %** | **0,70** |

Leçon : tout Sharpe quotidien issu d'un PnL « réparti » sur une fenêtre de détention est suspect. **Toujours marquer au close réel.**

---

## 6. Métriques corrigées

### 6.1 Edge par trade (indépendant de la méthode — le socle), fill délai+1
Bootstrap par blocs (taille 20), IC 95 % de l'expR :

| Classe | n trades | expR net | IC95 | win % |
|---|---|---|---|---|
| Indices (propres) | 2 051 | **+0,031 R** | [+0,014 ; +0,050] | 55,5 |
| Commodités (yf) | 1 252 | +0,061 R | [+0,033 ; +0,085] | 53,0 |
| Crypto | 64 | +0,117 R | [+0,044 ; +0,150] | 64,1 |
| Forex | 241 | **−0,021 R** | [−0,062 ; +0,020] | 46,9 |
| **Tous** | 3 608 | +0,040 R | [+0,024 ; +0,054] | 54,2 |

→ Edge par trade **positif et significatif même sur données propres (indices)**. Forex négatif. Ce socle **tient**.

### 6.2 Portefeuille mark-to-market (délai+1)

| Sleeve | Sharpe brut | Sharpe couvert-beta | alpha ann. | beta | t_NW(alpha) | maxDD | Calmar |
|---|---|---|---|---|---|---|---|
| Déployable (no-FX) | 0,70 | **0,41** | +1,3 % | +0,07 | **+2,18** (marginal) | −9,9 % | 0,24 |
| **Indices seuls (propres)** | 0,43 | **0,12** | +0,2 % | +0,12 | **+0,61 (NS)** | −9,7 % | 0,10 |
| Commodités seules (yf) | 0,77 | — | — | — | — | −10,0 % | 0,15 |
| 2019+ (déployable) | 0,96 | — | +2,0 % | +0,04 | +1,97 | — | — |

→ Sur les **données les plus propres (indices), l'alpha couvert-beta n'est pas significatif** (t=0,61). Le marginal positif du déployable (t=2,18) **vient surtout des commodités** (données proxy).

### 6.3 Distribution
Skew **par trade +0,6** (pertes plafonnées par le stop ATR, gagnants à queue droite) ; skew **quotidien −0,3 à −0,9** (les gaps se groupent en sell-off → jours rouges corrélés). Kurtosis quotidienne ~5.

### 6.4 Robustesse paramètres
Plateau : sur la grille ATR_Index∈{1,5 ; 3 ; 5} × Time∈{5 ; 10 ; 20}, Sharpe par trade 1,3–1,6 (séquentiel) — pas une cellule isolée.

---

## 7. Catalogue des risques d'artefact — testé / reste à faire

| # | Risque | Test effectué | Résultat | Reste à valider (votre équipe) |
|---|---|---|---|---|
| 7.1 | **Lissage Sharpe** | recalcul mark-to-market | ❌ **artefact confirmé** (3,1→0,7) — corrigé | revérifier le MTM indépendamment |
| 7.2 | **Look-ahead** | entrée=Open[i], niveau=Low[i−1], ATR sur i−1, fill delai+1=Open[i+1] | aucun look-ahead identifié | re-vérifier que ATR & lvl sont strictement décalés |
| 7.3 | **Fill optimiste** | délai+1 + close + slippage +2/+5 bps | edge survit (expR +0,034 à +5 bps) | spreads réels FTMO des jours de gap |
| 7.4 | **Beta déguisé** | régression MTM vs BH | beta +0,07 (pas 0) ; alpha indices NS | refaire sur données FTMO |
| 7.5 | **Multiple testing** | 70 stratégies × grilles testées ; DSR intra-#60 OK | edge faible → fragile au data-snooping | déflation à l'échelle projet |
| 7.6 | **Gaps de roll (commodités yf)** | distribution des tailles de gap | gaps **petits** (médiane 0,13 ATR, 0,2 % > 2 ATR) → **pas dominé par des sauts de roll** ; risque réduit mais data = proxy | **revalider commodités sur CFD FTMO réels** |
| 7.7 | **Breadth temporelle** | instruments/an | ~16 (2005) → ~21 (2020+) ; sous-périodes anciennes = indices+commodités only | tester par fenêtre à breadth constante |

---

## 8. Reproduction exacte

```bash
cd oxfordstrat_109/code
# 1) backtest + 4 gates + beta_line (chiffres bruts, fills stop/next_open)
python strat_s060_oops_bull.py          # dépend de strat_s058_oops + beta_bench
# 2) deep-dive initial (ATTENTION: strat_daily = R étalé, Sharpe gonflé — cf. §5)
python s060_deepdive.py ; python s060_deepdive2.py
```
Le recalcul **mark-to-market** (§5-6) et les régressions corrigées sont des scripts d'audit autonomes ; le code exact est inclus dans ce dossier (annexe `code/s060_audit.py` à régénérer) — fonction clé `mtm_series()` : marque chaque position ouverte en **close-to-close / risk0**, somme les positions concurrentes, ×RISK_FRAC.

**Fichiers de référence** : `code/strat_s058_oops.py` (moteur `simulate_oops`), `code/ftmo_lab.py` (atr, coûts, sizing, métriques — **inchangé 9dea332**), `code/beta_bench.py`, `ohlc/*.parquet` + `ohlc/_coverage.csv`, `results/s060_deepdive*.{csv,png}`.

**Invariants à vérifier** : `git log -1 --format=%h -- code/ftmo_lab.py` == `9dea332` ; le store OHLC n'est pas modifié par les backtests.

---

## 9. Checklist d'audit indépendant recommandée

1. **Reconstruire la série quotidienne en mark-to-market** depuis zéro (sans réutiliser mon code) et confirmer Sharpe ~0,7, pas ~3.
2. **Revalider le sleeve commodités sur données FTMO/broker réelles** (pas Yahoo futures continus) — c'est là que se concentre l'edge marginal.
3. **Indices seuls, données propres** : confirmer que l'alpha couvert-beta est ≈ 0 (t≈0,6).
4. **Coûts jours de gap** : mesurer les spreads/slippage réels d'ouverture en sell-off et re-stresser.
5. **Sous-périodes à breadth constante** (post-2018, 21 instruments) pour éliminer le biais de breadth.
6. **Capacité / contraintes FTMO** : peut-on réellement tenir ~6 positions concurrentes sous les limites de risque FTMO ? Corrélation des positions en krach.
7. **Walk-forward** strict (pas seulement train≤2015/test≥2016).

---

## 10. Verdict révisé

🟡 **BORDERLINE — edge réel mais modeste et non prouvé en alpha.** Rétrogradé de KEEP. Le gap-down-fade a un **petit edge par événement** (expR net positif, significatif au bootstrap, y compris sur données propres), mais (i) son **Sharpe de portefeuille réel est ~0,7, pas ~3** (le 3 était un artefact de lissage de ma part), (ii) l'**alpha couvert-beta n'est pas significatif sur les données les plus propres** (indices, t=0,61), et (iii) le marginal positif se concentre sur des **commodités en données proxy**. Confirmé sur données FTMO réelles (§11).

---

## 11. Validation sur données FTMO réelles (`Algo_claude/data`)

Le dataset FTMO réel a été branché là où il existe en OHLC : **indices** = vrai panel FTMO (`panels/ftmo_{open,high,low,close}.csv`, déjà la source du store) ; **or XAUUSD** = reconstruit depuis le **M1 réel** `deep_history_utc/XAUUSD_M1.csv` (2007→2026, 5 050 j) → `real_data/XAUUSD_real_m1daily.parquet` ; **crypto** = M1 réel. Script : `code/s060_real_audit.py`.

**Limite data importante** : softs (cocoa, coffee, wheat, soybean), **argent, platine, palladium, pétrole** n'ont **aucun OHLC FTMO réel** dans le dataset (uniquement des proxies *close-only* `panels/commodity_panel.csv` = ETF, et les futures continus Yahoo du store). Or **c'est ce sleeve qui portait le marginal d'edge** (§6.2) → **il n'est pas validable**.

**Résultats sur données réelles (délai+1, mark-to-market) :**

| Sleeve (données réelles) | n trades | expR (IC95 bootstrap) | Sharpe MTM | alpha ann. | beta | **t_NW(alpha)** | Sharpe couvert |
|---|---|---|---|---|---|---|---|
| Indices (vrai OHLC FTMO) | 2 051 | +0,031 [+0,014 ; +0,050] | 0,40 | +0,2 % | 0,12 | **+0,61 (NS)** | 0,12 |
| Or XAUUSD (vrai M1 2007+) | **43** | +0,030 [**−0,121** ; +0,081] | — | — | — | — (n trop faible) | — |
| Crypto (réel) | 64 | +0,117 [+0,044 ; +0,150] | — | — | — | — | — |
| **Déployable réel (idx+or+crypto)** | 2 158 | +0,034 [+0,016 ; +0,051] | **0,45** | +0,35 % | 0,05 | **+0,79 (NS)** | **0,15** |

**Lecture :**
1. **L'edge par trade tient sur données réelles** (déployable +0,034 R, IC95 > 0) — ce socle est confirmé, pas un artefact de source.
2. **Mais l'alpha couvert-beta n'est PAS significatif** (t_NW = 0,61 indices / 0,79 déployable ; Sharpe couvert ~0,12-0,15 ≈ 0). Une fois le beta retiré, il ne reste pas d'alpha statistiquement distinguable de zéro.
3. **L'or réel ne « gappe » presque pas** sous le plus-bas de la veille (43 trades seulement, IC straddle 0) : le pattern est quasi absent sur l'or réel.
4. Le marginal qui avait porté le déployable à Sharpe couvert 0,41 (§6.2) **venait des commodités proxy** → **non confirmé** sur données réelles.

## 12. Verdict final (post-données-réelles)

🟡 **BORDERLINE, penche DISCARD — NON promouvable.** Sur **données FTMO réelles**, le gap-down-fade a un **petit edge par trade réel** (expR ~+0,03 R, IC95 > 0) mais **aucun alpha couvert-beta significatif** (t < 1). Ce n'est pas un alpha market-neutral ; au mieux une légère exposition long à une réversion overnight modeste. Le seul sleeve où il paraissait fort (commodités) reposait sur des données proxy non validables. **Ne satisfait pas le critère KEEP.** Compteur KEEP du projet = **0**. À ranger comme « effet réel mais trop faible pour être exploité seul » ; éventuellement composant d'un ensemble, pas une stratégie autonome.
