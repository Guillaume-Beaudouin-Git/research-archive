# Cartographie des pistes rouvrables — par QUALITÉ DU TEST

**2026-08-21. Première passe, faite à la main.** L'agent Fable 5 lancé sur cette mission est mort
sur limite de session sans rien écrire. Ce document est donc **partiel et honnête sur son
périmètre** : il couvre le registre `research_history.md` (55 lignes, ~320 essais résumés) et
vérifie en profondeur les trois candidats les plus flagrants. Il ne prétend pas à l'exhaustivité.

**Aucun test n'a été exécuté.** Un diagnostic ne consomme pas de DSR ; un essai en consomme pour
tous les candidats futurs.

---

## SYNTHÈSE

La politique de ré-ouverture du repo classe par **nature du kill** (mécanique / véhicule / coût /
puissance / géométrie). Il manque une sixième entrée, et elle est la plus productive ici :

> **KILL MÉTHODOLOGIQUEMENT INADÉQUAT** — « gross ≈ 0 » n'est un kill mécanique que si le gross a
> été mesuré correctement. Mauvais instrument, mauvaise breadth, indicateur ad hoc au lieu de la
> construction canonique, coût faux : le kill falsifie notre implémentation, pas le mécanisme.

**Trois précédents déjà mesurés dans ce repo** prouvent que ce mode de défaillance est réel et
fréquent : sur-facturation des indices de **2.1×**, fuseau EET étiqueté UTC (**38.7 % du RTH
jamais testé**), et `std_sr_trials=1.0` imposant un seuil DSR de **2.57** à 164 tests.

**Verdict : 2 candidats méritent réouverture, dont 1 sans discussion** (le 3ᵉ a été retiré le 2026-08-21 après vérification du fichier source — voir §2.2). Suite du diagnostic : `CARTOGRAPHIE_PART2.md`.

| # | candidat | correctif | Δn_tests |
|---|---|---|---|
| **1** | **Commodity TSMOM** | 12 **ETF** → futures, N≥30 | **0** (correction) |
| ~~2~~ | ~~NQ intraday MR / afternoon momentum~~ | **RETIRÉ 2026-08-21 — voir §2.2** | — |
| **3** | **Equity indices_swing** | tué au coût **ETF**, l'étude dit elle-même « Sharpe 0.45 au coût futures » | **0** (correction) |

**Les trois sont des CORRECTIONS**, pas des essais neufs : hypothèses déjà pré-enregistrées et
déjà comptées ⇒ **aucune déflation du DSR**. C'est le point qui rend ce programme asymétrique.

---

## 1. La grille de diagnostic

Signatures d'un test faible, appliquées à chaque entrée du registre :

| # | signature | leçon du repo violée |
|---|---|---|
| S1 | **Instrument proxy inadapté** (ETF au lieu de futures, CFD au lieu de futures) | **L5** roll drag |
| S2 | **Breadth insuffisante** (N < 30 en cross-section) | **L6**, hard rule |
| S3 | **Coût faux** appliqué | L33, et les 2.1× mesurés |
| S4 | **Une seule spécification**, aucune robustesse | — |
| S5 | **Indicateur ad hoc** au lieu de la construction canonique du papier cité | — |
| S6 | **Horloge / fuseau** erroné | L52, L56 |
| S7 | **Pénalité de multiple testing** appliquée à un test sous-puissant par construction | L11b |
| S8 | **Fréquence inadaptée** au mécanisme | — |

Un kill portant **S1, S2, S3 ou S5** ne falsifie pas le mécanisme. Un kill à gross nul, two-sided
négatif à coût nul, ou sous placebo apparié, **le falsifie** — celui-là reste fermé.

---

## 2. TIER 1 — À rouvrir sans discussion

### 2.1 Commodity TSMOM — le cas d'école

**Ce qui a été testé** [V] `Commodities/research/archived/commodity_tsmom/commodity_tsmom_summary.md` :
- Framework cité : **Hurst-Ooi-Pedersen 2017** — un papier de managed futures, qui opère sur des
  **futures**, sur ~60 instruments.
- Univers réellement utilisé : **GLD, SLV, CPER, PPLT, USO, UNG, BNO, DBA, CORN, WEAT, SOYB, DBB**
  — **12 tickers, tous des ETF, aucun future.**
- Période 2010-02 → 2026-04. Meilleure variante A1 : **Sharpe HAC 0.391**.
- Kill : **AMTP n=78, p=0.808**.

**Le diagnostic — trois signatures simultanées :**

| | |
|---|---|
| **S1** | 12/12 ETF. **USO et UNG** sont les deux véhicules les plus détruits par le contango de l'histoire. Y mesurer du momentum, c'est mesurer le roll. **C'est littéralement l'énoncé de L5.** |
| **S2** | **12 instruments** contre la hard rule **N ≥ 30**, et **5× moins** que la breadth du papier cité. |
| **S7** | Pénalité de multiple testing appliquée à un test que S1+S2 rendaient **sous-puissant par construction**. |

**Pourquoi ça compte** : le TSMOM commodités est l'un des effets les plus répliqués de la finance
quantitative — c'est le fonds de commerce de l'industrie managed futures. Un Sharpe de 0.391 sur
12 ETF ne dit rien sur le mécanisme ; il dit que le roll drag mange l'effet, ce que le repo savait
déjà avant de lancer le test.

**Ce qui a changé** : le véhicule. Futures IBKR à **~0.4 bps RT** contre le tier ETF, et les
futures commodités sont parmi les plus liquides et les moins chers du marché. Le compte perso
€12k porte déjà un book validé sur futures (trend + bond month-end, SR 1.02).

**Correctif** : refaire sur **futures continus, N ≥ 30**, construction Hurst-Ooi-Pedersen
(lookbacks multiples, vol-scaling par instrument, pondération inverse-vol), coût futures mesuré.
⚠ **L55** : sur un univers macro mixte la pondération inverse-vol est un amplificateur de portage
— vérifier la décomposition de contribution par classe.

### 2.2 ~~NQ intraday MR / afternoon momentum~~ — **RETIRÉ, mon diagnostic était faux**

> ## ⛔ ERREUR DE MA PART, corrigée le 2026-08-21
>
> J'ai bâti ce candidat sur la ligne de `research_history.md` : *« NQ VWAP MR / afternoon
> momentum: all FAIL ($19 RT cost kills any edge) »*, et j'en ai conclu à un kill sur le COÛT.
>
> **Le fichier source dit autre chose** [V] `Futures/research/archived/nq_intraday_vwap/iter_01_summary.md` :
> - `:7` — *« FAIL — INSUFFICIENT SAMPLE (automated gates show RESEARCH_PASS but **N=19 over
>   3 years** is statistically meaningless) »*
> - `:45` — `AMTP = 1.000` — faux positif certain à n_tests=130
> - `:47` — *« Sharpe of 21.7 reflects noise: **9 winning days** vs 4 losing days, rest zero »*
> - `:56` — *« **19 trades is the binding constraint** »*
>
> **Le kill est la PUISSANCE, pas le coût.** Et `CLAUDE.md:161` le disait déjà : « NQ intraday
> VWAP, **N=19 insuffisant** ». La ligne du registre **confond `$19 RT` et `N=19`** — un bug de
> documentation qui a produit un faux candidat de Tier 1.
>
> **Conséquence** : la famille n'est pas morte (la puissance est une catégorie rouvrable —
> *UNDERPOWERED ≠ REJECTED*), mais le correctif n'est pas celui que j'avais écrit. Il ne s'agit
> pas de re-tester moins cher, il s'agit d'**obtenir des trades** : échantillon plus long,
> univers élargi, ou déclencheur moins restrictif. Avec un Sharpe de 21.7 bâti sur **9 journées
> gagnantes**, l'attrait est faible. **Priorité basse, pas Tier 1.**
>
> **Leçon de méthode** : un registre condensé n'est pas une source. Il faut ouvrir le fichier de
> l'étude. Deux des trois candidats de cette première passe reposaient sur une ligne de résumé ;
> celui-ci était faux.

**Analyse d'origine, conservée pour mémoire (INFIRMÉE) :**

**Ce qui a été testé** [V] `research_history.md` : *« NQ VWAP MR / afternoon momentum: all FAIL
($19 RT cost kills any edge) »*.

**Le diagnostic — S3, pur.** Le coût appliqué était **$19 aller-retour**. Le repo a depuis
re-baselined le NQ à **$29 RT** (Databento, L19) pour du **CFD/propfirm**… mais sur **MNQ chez
IBKR** le coût réel est de l'ordre de **~0.4 bps**, soit **~$2-4 RT** sur le notionnel d'un micro.
Un facteur **5 à 9**.

Le registre dit explicitement *« costs kill any edge »* — c'est-à-dire que **le gross existait**.
Un kill sur le coût est la catégorie rouvrable la mieux établie du repo.

⚠ **Réserve honnête** : L33b dit qu'en intraday-flat le coût liant est le **spread**, et qu'il
faut **> 3 bps de gross** pour exister. Le gross de cette famille n'est pas rapporté dans le
registre — **il faut le retrouver avant de re-tester**. Si le gross est sub-bps, la famille meurt
quel que soit le véhicule.

### 2.3 Equity indices_swing — l'étude conclut elle-même à sa réouverture

**Ce qui a été testé** [V] : *« Sprint 1+2 (100 tests): IC 0.033-0.075, all fail backtest
(best Sharpe 0.45 at futures cost, costs kill at ETF level) »*.

**Le diagnostic — S1 + S3.** Deux choses dans cette ligne :
1. Les IC de **0.033 à 0.075** sont **dans la fourchette normale** de la littérature pour des
   stratégies d'indices actions (0.02-0.05). Ce ne sont pas des IC nuls.
2. **L'étude rapporte elle-même « Sharpe 0.45 au coût futures »** et conclut quand même à l'échec
   parce que le coût ETF tue. Le verdict est donc **conditionné à un véhicule** — et le véhicule
   a changé.

⚠ Sharpe 0.45 reste **sous RESEARCH_PASS (0.70)**. Ce n'est pas un survivant, c'est un candidat
dont le plafond n'a jamais été mesuré au bon coût. À traiter comme tel : **priorité 3**, pas 1.

---

## 3. À LAISSER FERMÉ — et pourquoi

Cette liste protège le DSR de tout ce qui suivra. Chaque entrée porte un kill **mécanique** :
gross nul, direction inverse, ou sous placebo.

| famille | pourquoi le kill tient |
|---|---|
| **Crypto long-only CS** | β-dominance **L11**, mesurée sur toutes les familles de signal **quel que soit l'IC**. Structurel, pas d'implémentation. |
| **VRP Deribit / BTC** | gross **4.4 %/an** contre coûts **8.9 %/an**, **0/13 folds WF positifs**. Kill arithmétique. |
| **FGVD sentiment, Wikipedia attention** | IC nul, et identifiés comme **proxies de momentum** (L17/L18). Taxonomie Da et al. épuisée. |
| **Round Number Cascade** | tous les horizons d'IC échouent, dont certains **de signe inverse** (t 1.167 → −2.357). |
| **Sector reversal** | Sharpe −0.60, **t = −3.7 : alpha négatif significatif**. Le mécanisme est réel et va dans l'autre sens. |
| **D4 Lunch RSI** | Sharpe −0.70, WF 22 %. |
| **jt_momentum_cs** | sharpe −0.026, ic_t −0.49. |
| **h31_cs_fs_dn** | sharpe −0.80, **3/3 gates FAIL**. |
| **Pairs / Gatev** | 0/19 à l'époque, puis **0/171 paires** re-testées en 2026-08 sur le critère de demi-vie. Re-tester serait le 3ᵉ passage. |
| **D2 VWAP touch fade** | classé « deferred », mais **signal de signe inverse** avec t −0.86 : c'est du bruit, pas une piste. |
| **Momentum de clôture (dose-réponse)** | contrôle négatif XAUUSD monotone ⇒ **ordre attendu inversé**. Kill mécanique explicite. |

---

## 4. Ce qui n'a jamais été testé — le pivot que le repo a lui-même nommé

**Carry cross-asset façon Koijen et al. 2018.** Le postmortem G1 le désigne explicitement comme le
pivot non exploré (*« G2D pivot: Koijen 2018 carry cross-asset »*) et note que l'infra est
réutilisable. Le repo a fermé le carry **FX** (mort post-GFC, IC −0.028 sur 2013-2023) et le carry
**commodités en CFD** (L32b, les deux côtés fermés) — mais **le carry cross-asset sur futures,
qui est la construction du papier, n'a jamais été testé**.

C'est un **NOUVEL ESSAI** (déflate), à la différence des trois du Tier 1. À traiter après eux.

---

## 5. Pré-enregistrement — candidat n°1

**À geler AVANT de toucher la donnée.**

- **Hypothèse** : le time-series momentum sur **futures** commodités produit un Sharpe net > 0.70
  sur N ≥ 30 instruments, et l'échec de 2026-05 est attribuable à l'univers ETF (S1) et à la
  breadth (S2), pas au mécanisme.
- **Univers** : ≥ 30 futures continus, ≥ 4 secteurs (énergie, métaux précieux, métaux industriels,
  agricoles). Contrats front-month avec roll documenté.
- **Construction** : Hurst-Ooi-Pedersen — lookbacks multiples, vol-scaling par instrument,
  pondération inverse-vol. **Aucun réglage ad hoc.**
- **Coût** : futures mesuré, **jamais** une constante de catalogue.
- **Hold-out** : les **3 dernières années réservées et jamais regardées** avant le verdict.
- **Règles de kill, gelées** :
  - R1 — Sharpe net < 0.70 sur l'in-sample ⇒ STOP.
  - R2 — walk-forward < 5 folds positifs sur 5 ⇒ STOP.
  - R3 — la **décomposition de contribution par classe** (L55) montre qu'une classe porte > 50 %
    du gross ⇒ ce n'est pas du TSMOM diversifié, c'est un pari sectoriel ⇒ STOP.
  - R4 — **test L53 en PREMIER** : si la marge du lot minimum ne tient pas dans €12k sur ≥ 30
    instruments, le véhicule ne suit pas ⇒ redimensionner l'univers **avant** tout backtest.
- **Δn_tests = 0** : hypothèse déjà pré-enregistrée et comptée en 2026-05.

---

## 6. Limites de cette passe

- **Partielle.** Le registre résume ~320 essais en 55 lignes ; je n'ai vérifié en profondeur que
  **3 candidats**. Les postmortems FX (E, G1, F2), le corpus crypto (159 essais) et les 164 du
  funnel FTMO n'ont pas été ouverts un par un.
- **Aucun contraste littérature systématique.** C'était le cœur de la mission confiée à l'agent :
  aller chercher la construction canonique de chaque mécanisme et mesurer l'écart. Seul le cas
  Hurst-Ooi-Pedersen a été traité, et de façon superficielle (je n'ai pas relu le papier).
- **Le gross des familles NQ n'est pas retrouvé.** Sans lui, la réserve L33b sur le candidat n°2
  n'est pas levable.
- **Risque de complaisance, à surveiller.** Il est facile de raconter une faiblesse
  d'implémentation pour n'importe quel échec. Le garde-fou appliqué ici : n'accepter la
  réouverture que sur une signature **objective et vérifiable** (S1 instrument, S2 breadth,
  S3 coût), jamais sur une intuition de mécanisme.
