# Gap Pattern A/B (S035/S036) — réhabilitation DSR et ré-instruction complète

**Date** : 2026-07-31 · **Statut** : ❌ **REJECTED** · **Contribution `n_tests` : +6** (l'hypothèse « 0 » est **infirmée**, §7)

> **Verdict en une phrase.** Le gate DSR de l'audit était bien invalide et sa correction est
> **totale** (DSR 1.000 au lieu de FAIL, à n'importe quel N plausible) — mais la réhabilitation ne
> sauve rien : trois gates encore valides mordent indépendamment, et **51 % du P&L de S035 vient de
> deux séries dont la fourchette quotidienne médiane est exactement zéro**.

---

## 1. Ce qui était promis vs ce qui a été trouvé

L'inventaire (`edge_inventory_2026-07/INVENTORY.md`, §3.1 et shortlist n°7) annonçait : *« recalculer
le DSR avec la bonne dispersion sur les Sharpes de grille **déjà stockés** — correction arithmétique
sur des nombres existants, coût nul »*.

**Faux, sur le point matériel.** `results/s035_sensitivity_expectancy.csv` et son homologue S036 ne
contiennent que la grille d'**espérances** (`expR`). La grille de **Sharpes** (`sg` dans
`strat_s035_gap_pattern.py:88`) était calculée en mémoire, passée à `run_gates(...)`, puis **jetée** —
elle n'a jamais été écrite sur disque. Or c'est exactement la dispersion des Sharpes qui définit
`std_sr_trials`. Il a donc fallu **re-exécuter les deux grilles 3×3** pour récupérer σ.

La reproduction est **exacte** : la grille d'expR régénérée coïncide avec le CSV archivé sur les 15
décimales, et les Sharpes retrouvés reproduisent les valeurs citées dans les rapports (1.3886 vs
« 1,389 » pour S035 ; 1.0210 vs « 1,02 » pour S036). Le pipeline est reproductible ; c'est sa
persistance qui était incomplète. Artefacts régénérés et désormais persistés :
`s035_grid_metrics.csv`, `s036_grid_metrics.csv`.

---

## 2. Le DSR : publié vs recalculé

### 2.1 Diagnostic du gate publié — confirmé

`ftmo_lab.gate_dsr` (ligne 214) calcule

```
e_max = sqrt(2*ln N) * (1 - gamma/sqrt(2*ln N))     # = 1.5191 pour N=9
passed = sr_obs > e_max
```

`e_max` est l'espérance du **maximum de N normales centrées réduites** : une quantité **sans
dimension**, exprimée en unités de σ_SR. La comparer directement à un Sharpe annualisé revient à
poser σ_SR = 1.000 — c'est-à-dire à supposer un backtest d'exactement **un an**. Ici T ≈ 5 300 trades
à ~200 trades/an sur 26 ans : le plancher de bruit d'échantillonnage seul vaut
`sqrt(201/5299) = 0.195`, soit **5.1× moins**. Diagnostic de l'inventaire : **correct**.

### 2.2 σ mesuré (et non supposé)

`std_sr_trials` est estimé par `dsr.estimate_std_sr_trials()` sur la **dispersion réelle des 9
cellules** de chaque grille, plancher `sqrt(periods_per_year/T)` appliqué :

| | σ observé (9 cellules) | plancher bruit | **σ retenu** | justification |
|---|---|---|---|---|
| S035 | 0.2646 | 0.1948 | **0.2646** | dispersion observée > plancher ⇒ on garde l'observée (hétérogénéité réelle de la grille) |
| S036 | 0.1288 | 0.1947 | **0.1947** | dispersion observée **sous** le plancher (grille quasi-dégénérée) ⇒ clampée, conformément au garde-fou anti-faux-positif de `dsr.py` |

*Note* : le σ = 0.216 avancé par l'inventaire était une estimation de bonne magnitude mais n'était
adossée à aucune mesure ; les valeurs mesurées l'encadrent (0.195–0.265).

Annualisation : `periods_per_year = trades/an` (convention `ftmo_lab.trade_metrics`), `rf=0.0`
(les `netR` sont des multiples de R nets de coûts, pas des rendements en devise).

### 2.3 Tableau DSR — publié vs recalculé

DSR de la **meilleure cellule** de chaque grille (S035 : F10_T5, SR 1.3877, T=5299 ; S036 : F20_T10,
SR 1.0194, T=5119). Échelle de déflation en N, du compteur de famille au compteur de cohorte :

| Stratégie | N (déflation) | E[max] **publié** | E[max] **corrigé** | SR observé | **DSR corrigé** | Décision |
|---|---|---|---|---|---|---|
| **S035** | 9 — grille propre | 1.519 | **0.402** | 1.388 | **1.0000** | ✅ PASS |
| S035 | 18 — famille gap A+B | 1.827 | 0.491 | 1.388 | 1.0000 | ✅ PASS |
| S035 | 109 — cohorte oxfordstrat | 2.486 | 0.678 | 1.388 | 1.0000 | ✅ PASS |
| S035 | 981 — cohorte × 9 cellules | 3.134 | 0.860 | 1.388 | 0.9990 | ✅ PASS |
| **S036** | 9 — grille propre | 1.519 | **0.296** | 1.019 | **1.0000** | ✅ PASS |
| S036 | 18 | 1.827 | 0.361 | 1.019 | 0.9999 | ✅ PASS |
| S036 | 109 | 2.486 | 0.499 | 1.019 | 0.9982 | ✅ PASS |
| S036 | 981 | 3.134 | 0.633 | 1.019 | 0.9847 | ✅ PASS |

**La décision change, et sans ambiguïté.** Le DSR n'est contraignant à **aucun** compteur plausible —
pas même en déflatant à N=981, soit la cohorte entière des 109 stratégies × 9 cellules, ce qui est
la déflation la plus punitive défendable (S035/S036 ont été *sélectionnées* parmi les 109).
J'ai délibérément affiché cette borne haute plutôt que le seul N1=18 : deux survivantes sur 109 est
le taux du hasard, et il fallait vérifier que la réhabilitation ne tenait pas au choix du compteur.
Elle n'y tient pas. `dsr_recalc.csv`.

**⇒ Gate 3 (DSR) : le kill est annulé. Le « 1/4 FAIL » de l'audit devient 0/4.**

---

## 3. Les gates de mécanisme encore valides

Un DSR réhabilité ne dit que « ce n'est pas du bruit de sur-recherche ». Voici les gates que la
correction ne touche pas.

### 3.1 L38 — β-orthogonalité : ✅ **PASS** (et l'inventaire avait raison sur le mauvais gate)

Série quotidienne de la stratégie (netR × RISK_FRAC, comptabilisée en date de sortie) régressée sur
un buy&hold équipondéré **vol-targeté** de l'univers effectivement tradé, HAC lag-6 :

| | β | t(β) | R² | α HAC | t(α) |
|---|---|---|---|---|---|
| S035 tout | 0.020 | 1.33 | **0.04 %** | +2.20 %/an | **3.89** |
| S035 long seul | 0.127 | 10.3 | 1.62 % | +1.84 %/an | 4.97 |
| S035 short seul | −0.098 | −6.11 | 0.96 % | +0.36 %/an | 0.88 |

R² = 0.04 % ≪ 30 % : ce n'est **pas** du timing de bêta. Le critère qui a réellement tué ces deux
fiches dans l'audit — *« Sharpe récent 0.30 < buy&hold récent 1.02 »*, `beta_bench.beta_line` — est
bien, comme le dit l'inventaire §3.3, une **lentille de passage de challenge** appliquée à un
candidat-sleeve. Sur le gate correct (L38), les deux stratégies passent largement. **Deux des trois
motifs de kill d'origine sont donc annulés.**

### 3.2 L36 — portage overnight mesuré : ❌ **quasi-fatal**

Le modèle de coût de `ftmo_lab` (`round_turn_cost_bps`) ne facture **qu'un aller-retour** — il ignore
totalement le swap. Or ces stratégies tiennent **8.0 nuits en moyenne** (médiane 7–8).

Re-pricing avec le portage **mesuré** (`data/ftmo_portfolio/outputs/phase0_swap_model.csv`,
bps/nuit, validé 4/4 au centime le 10/06) :

| | gross | swap mesuré | AR | **net** | part du gross mangée |
|---|---|---|---|---|---|
| S035 | +27.3 bps/trade | **−12.9** | −2.9 | +11.5 bps | **43 %** |
| S036 | +23.8 bps/trade | **−13.6** | −3.0 | +7.2 bps | **53 %** |

`expR` 0.0329 → **0.0175** (S035) et 0.0264 → **0.0109** (S036). Signature L36 exactement :
le portage agrégé mange la moitié de la prime. À swap ×2, S036 passe négatif.

### 3.3 L26 appliqué à la **sortie** : ❌ **fatal**

Le gate délai+1 de l'audit ne re-price que l'**entrée**. La sortie reste remplie **au niveau exact du
stop** dès que `low[j] <= stop_lvl`. Cette hypothèse est ici particulièrement complaisante :

- le stop réel (pattern-exit au bord du gap) est à **1.03 ATR** de médiane, très en-dedans de l'unité
  de risque nominale de 6 ATR ; **63 %** des sorties passent par ce stop ;
- l'univers est, par construction même de la stratégie, **sélectionné pour ses gaps**.

En facturant la sortie à l'**ouverture** quand la barre ouvre au-delà du stop (et au stop sinon) :

| | % de stops traversés à l'ouverture | expR | Sharpe |
|---|---|---|---|
| S035 | **24.9 %** | 0.0329 → **0.0171** | 0.99 → **0.49** |
| S036 | **18.3 %** | 0.0264 → **0.0159** | 1.02 → **0.60** |

Le fill de sortie intrabar portait **la moitié** de l'edge. Le « ✅ PASS délai+1 » de l'audit —
argument central du dossier « faux mort » — mesurait la mauvaise moitié du trade.

### 3.4 L58 — espérance inconditionnelle : ❌ **fatal, et le signe s'inverse**

Contrôle à géométrie **constante** (stop 6-ATR pur dans tous les bras, seule la **condition** varie),
pondéré instrument × direction × **année** par les poids réels des trades gap :

| Bras (expR apparié) | S035 | S036 |
|---|---|---|
| **inconditionnel** (aucune condition) | **+0.0412** | **+0.0362** |
| gap seul | +0.0276 | +0.0283 |
| filtre de tendance seul | −0.0078 | −0.0096 |
| **gap + filtre = la stratégie** | **−0.0201** | **−0.0148** |

À géométrie constante, **la condition de la stratégie a une espérance négative**, six points de R
**sous** l'entrée inconditionnelle sur les mêmes instruments, les mêmes directions et les mêmes
années. Le filtre de tendance — acheter un gap-up qui fait aussi un plus-haut 20 jours, c'est-à-dire
l'épuisement — détruit à lui seul la valeur, et l'interaction est pire que chacun des termes.

Tout le `expR` positif publié provient donc de la **géométrie de sortie** (stop serré au bord du gap
normalisé par un dénominateur de 6 ATR), pas du signal de continuation de gap. Et §3.3 montre que
cette géométrie ne survit pas à un fill de sortie réaliste. Les deux résultats sont le même fait vu
sous deux angles.

> ⚠ **Mise en garde méthodologique, à conserver.** Une première version de ce contrôle laissait la
> géométrie du stop bouger avec la condition (pattern-exit = extrême/clôture précédente, qui se situe
> **à l'entrée** en l'absence de gap). Le bras inconditionnel affichait alors +0.0787 — un pur
> artefact : sans gap, `stop_lvl` passe **au-dessus** du prix d'entrée pour un long, la boucle sort
> immédiatement *au-dessus* de l'entrée et fabrique un gain instantané. C'est précisément le mode de
> défaillance de L58 (« un placebo apparié peut FABRIQUER un résultat ») — ici dans le sens qui
> **aggrave** le verdict plutôt que le flatter, mais le remède est le même : **tenir la géométrie de
> risque constante entre les bras**, sans quoi les multiples de R ne sont pas comparables.

### 3.5 L25 — two-sided : ✅ plein échantillon / ❌ **dès qu'on price honnêtement**

C'est la propriété qui faisait de S035/S036 « le seul edge bilatéral des 109 ». Elle ne survit pas :

| S035 — jambe short | expR |
|---|---|
| tel que publié | **+0.0181** ✅ |
| + fill de sortie réaliste | +0.0021 |
| + swap mesuré | **−0.0009** ❌ |
| régime récent 2019+ (publié) | **−0.0436** ❌ |
| régime récent + fill + swap | **−0.0540** ❌ |

Pour S036, la jambe short devient négative dès le fill réaliste seul (−0.0040). Le caractère
bilatéral était un artefact de plein échantillon et de coûts sous-facturés. **Sur les données
brokers seules et en régime récent, la stratégie est un long-only** — c'est-à-dire L11/L25 dans sa
forme classique.

### 3.6 L31 — régime : ❌ décroissance monotone jusqu'au signe négatif

| Ère | n | expR publié | Sharpe | expR après swap |
|---|---|---|---|---|
| 1999-2007 | 903 | +0.0395 | 1.21 | +0.0271 |
| 2008-2012 | 1114 | +0.0497 | 1.88 | +0.0401 |
| 2013-2018 | 1294 | +0.0183 | 0.80 | +0.0013 |
| **2019-2026** | 1808 | +0.0113 | 0.49 | **−0.0018** |

Avec fill de sortie réaliste **et** swap, le régime récent tombe à **−0.0213** (S035) / **−0.0151**
(S036). Bootstrap par blocs (instrument × année) sur le régime récent : p(expR ≤ 0) = **0.70** et
**0.65**. Le dossier n'est pas « un edge en fin de vie », il est **déjà mort**.

### 3.7 Ratio de coût — mesuré, seuil 1.5×

Le coût est ici **mesuré** (swap au centime, AR partiellement plancher-é) ⇒ seuil 1.5×, pas 3× :

| | gross bps | coût bps | **ratio** | verdict |
|---|---|---|---|---|
| S035 plein échantillon | 27.3 | 15.6 | **1.75** | passe de justesse |
| S036 plein échantillon | 23.8 | 16.2 | **1.47** | ❌ échoue |
| S035 récent 2019+ | 6.2 | 15.2 | **0.41** | ❌ échoue massivement |
| S036 récent 2019+ | 19.6 | 16.7 | **1.18** | ❌ échoue |

Et ce ratio n'intègre pas encore le slippage de sortie de §3.3 (16.5 bps supplémentaires pour S035).

---

## 4. Le défaut le plus grave : les données

Ce point n'était dans aucun gate, et il domine tous les autres.

**XPTUSD et XPDUSD ont une fourchette quotidienne médiane de EXACTEMENT ZÉRO** — 61 % et 69 % des
barres ont `high == low == close`. Ce sont des **prints de règlement**, pas des barres tradées :
`yfinance PL=F / PA=F` renvoie un contrat front-month très peu liquide.

| instrument | source | fourchette médiane | % barres à fourchette nulle | **taux de « gap »** |
|---|---|---|---|---|
| XPDUSD | yf:PA=F | **0.000 %** | 69.3 % | **78.6 %** |
| XPTUSD | yf:PL=F | **0.000 %** | 61.1 % | **73.8 %** |
| XAGUSD | yf:SI=F | 0.98 % | 22.7 % | **44.0 %** |
| *médiane broker (21 instr.)* | ftmo_panel / M1 | 1.09 % | ~0 % | *0.4 %* |

Un « gap » au sens de la stratégie (`Low[i] > High[i-1]`) suppose que la journée entière est disjointe
de la précédente. **Un taux de 79 % n'est pas un phénomène de marché, c'est une dégénérescence de
série.** Sur XPT/XPD la condition « gap » est quasiment toujours vraie et se réduit à « le règlement a
monté » : ce n'est plus une stratégie de gap. Pire, toute la machinerie de sortie (`l[j] <= stop_lvl`)
est **indéfinie** sur une barre où `low == high` — le stop ne peut mécaniquement pas se déclencher
intrabar, la stratégie touche systématiquement sa sortie temporelle.

**Ces séries portent 32.0 % du P&L de S035 ; avec XAGUSD, 51.3 %** (S036 : 30.4 % / 45.5 %). Plus
largement, **62 % du P&L de S035 provient des 9 séries `yfinance =F`**, aucune n'étant l'instrument
réellement tradable.

Sur les **données brokers seules** (21 instruments, ftmo_panel + M1_resample), avec fill de sortie
réaliste et swap mesuré : expR = **+0.0008** (S035) et **−0.0022** (S036).

---

## 5. Échelle consolidée : du titre publié au chiffre honnête

Chaque échelon retire **un défaut documenté**. Aucun paramètre de la stratégie n'est modifié.

### S035 (Gap Pattern A)

| échelon | n | expR | Sharpe | long | short | IC 95 % bootstrap | p(≤0) |
|---|---|---|---|---|---|---|---|
| 0. tel que publié | 3438 | +0.0329 | **0.99** | +0.0425 | +0.0181 | [0.021, 0.046] | 0.000 |
| 1. + fill de sortie réaliste | 3438 | +0.0171 | 0.49 | +0.0267 | +0.0021 | [0.005, 0.030] | 0.003 |
| 2. + swap FTMO mesuré | 3438 | +0.0016 | **0.05** | +0.0032 | −0.0009 | [−0.010, 0.015] | **0.389** |
| 3. − XPT/XPD (fourchette nulle) | 2823 | +0.0026 | 0.08 | +0.0050 | −0.0011 | [−0.009, 0.015] | 0.318 |
| 3b. − XPT/XPD/XAG | 2557 | −0.0022 | −0.07 | −0.0001 | −0.0055 | [−0.013, 0.009] | 0.647 |
| 4. + régime récent 2019+ | 987 | **−0.0132** | −0.44 | +0.0120 | −0.0540 | [−0.034, 0.009] | **0.893** |

### S036 (Gap Pattern B)

| échelon | n | expR | Sharpe | long | short | IC 95 % bootstrap | p(≤0) |
|---|---|---|---|---|---|---|---|
| 0. tel que publié | 5119 | +0.0264 | **1.02** | +0.0401 | +0.0067 | [0.017, 0.036] | 0.000 |
| 1. + fill de sortie réaliste | 5119 | +0.0159 | 0.60 | +0.0298 | −0.0040 | [0.006, 0.026] | 0.000 |
| 2. + swap FTMO mesuré | 5119 | +0.0004 | **0.02** | +0.0062 | −0.0078 | [−0.009, 0.011] | **0.467** |
| 3. − XPT/XPD | 4492 | −0.0002 | −0.01 | +0.0062 | −0.0094 | [−0.009, 0.009] | 0.519 |
| 3b. − XPT/XPD/XAG | 4184 | −0.0028 | −0.11 | +0.0035 | −0.0119 | [−0.012, 0.006] | 0.733 |
| 4. + régime récent 2019+ | 1567 | **−0.0112** | −0.47 | +0.0166 | −0.0542 | [−0.028, 0.006] | **0.907** |

**Le Sharpe de 0.99 / 1.02 est intégralement consommé par deux hypothèses d'exécution et une
dégénérescence de données. Aucun échelon au-delà du 1 n'est statistiquement distinguable de zéro.**

### Fragilité additionnelle

Le **top 1 % des trades porte 58.5 %** (S035) / **68.9 %** (S036) du P&L net ; le top 5 % en porte
**174 %** / **203 %** — les 95 % restants perdent de l'argent en agrégat. C'est la signature déjà
gravée dans le repo (`orb_2mois_diagnostic` : « edge dans le top 1 % des trades ») et un profil
structurellement inapte à une barrière propfirm (L24).

---

## 6. Dossier véhicule (L53 — avant tout enthousiasme)

Fait **avant** de conclure, comme l'exige L53. Compte de référence **€13 000**.

**Ce que la stratégie demande.** Au dimensionnement audité (0.5 % de l'équité risqué sur l'unité
nominale de 6 ATR, `risk0` = 10.4 % du prix en moyenne) :

- notionnel par jambe : **€725 médian** (moyenne €777, p90 €1 216) ;
- redimensionné pour que le **vrai** stop (1.26 ATR) risque 0.5 % : **€3 453 médian** ;
- jambes concurrentes : **3.2 en moyenne**, p90 = 6, **max 16** ;
- 131 trades/an, tenue moyenne **8.0 nuits**.

**Granularité par véhicule** (specs FTMO **mesurées**, `data/ftmo_portfolio/v22/spec_v22.yaml`, lues
le 2026-06-10) :

| véhicule | lot min | notionnel du lot min | vs cible €725 | verdict |
|---|---|---|---|---|
| CFD indices (US100, contract 1, réf 29 974) | 0.01 | ~$300 | 0.4× | ✅ granularité OK |
| CFD indices (GER40, réf 25 185) | 0.01 | ~$252 | 0.35× | ✅ |
| **CFD XAUUSD** (contract 100, réf 4 326.7) | 0.01 | **$4 327** | **6.0×** | ❌ |
| micro futures (MGC ~$40 k, MES ~$38 k) | 1 | $38–40 k | **52–55×** | ❌ (3× le compte entier) |
| micro futures (M2K/MCL/M6E ~$8–14 k) | 1 | $8–14 k | **11–19×** | ❌ |

**La contradiction est structurelle.** La seule classe dont la granularité tient sur €13 k est
l'**indice CFD** — précisément la classe où l'edge n'existe pas : après swap mesuré, indices long
+0.0041 R et indices **short −0.0011 R** (S036). Les classes qui portent le P&L (métaux précieux)
sont soit **intradables telles quelles** (XPT/XPD = prints de règlement yfinance), soit
**inatteignables à cette taille** (XAUUSD lot min 6× trop gros, avant même de parler des 3 à 16 jambes
simultanées). La diversification 30 instruments qui fait tout le `N=3438` **n'est pas réalisable** sur
€13 k, dans aucun véhicule.

**Coûts réels — rappels d'hier respectés.** La colonne `spread` de `deep_history_utc` n'a pas été
utilisée ; elle est de toute façon absente de 11 des 30 parquets du magasin de l'audit et, là où elle
existe, elle est **massivement creuse** (EURUSD 38.3 % de barres nulles, USDCHF 36.5 %, USDJPY 29.4 %)
— exactement le défaut signalé. Le coût overnight vient du modèle **mesuré et validé au centime**
(§3.2), pas d'une hypothèse. Sur L57 (domination du coût fixe) : à €725 de notionnel par jambe, la
commission FTMO indices est nulle et FX 0.5 bps AR — le coût fixe ne domine donc pas *ici*, mais la
raison en est que le notionnel est si petit que **rien de matériel n'est gagné non plus** : l'edge
résiduel du meilleur échelon honnête (+0.0026 R) vaut **≈ €0.20 par trade**, soit **~€25/an** avant
même de compter la variance. Le dossier est économiquement vide avant d'être statistiquement mort.

---

## 7. Comptabilité `n_tests` — l'hypothèse « 0 » est **infirmée**

Contribution déclarée : **+6**.

| travail | compte ? | pourquoi |
|---|---|---|
| Re-exécution des 2 grilles 3×3 (18 cellules) | **non** | reproduction à l'identique de configurations déjà comptées dans l'audit ; rendue nécessaire par la non-persistance de `sg`, pas par une recherche |
| Recalcul DSR (4 compteurs N × 2) | **non** | arithmétique sur des Sharpes mesurés |
| Fill de sortie réaliste, swap mesuré, multiplicateurs de coût | **non** | **re-pricing** d'une spec figée : aucune de ces variantes ne pouvait « devenir le gagnant » |
| Exclusions XPT/XPD/XAG, split régime, split source | **non** | hygiène de données et découpage d'un pool existant |
| **Bras L58 : `all` / `gap seul` / `filtre seul` × 2 variantes** | **oui, +6** | ce sont de **vraies configurations alternatives** : si « gap seul » était sorti fortement positif, il serait devenu le candidat. Règle du ledger : *« if swapping it could have been the winner, it counts »* |

Ces 6 essais consomment le budget de multiple-testing de la famille gap **sans produire de
candidat** — ce qui est le résultat souhaitable (L48 : chaque essai évité protège le DSR des
candidats futurs ; ici les essais confirment une fermeture).

L'hypothèse de départ du mandat (« tout se règle par arithmétique, contribution = 0 ») est donc
**infirmée sur deux points** : (a) la grille de Sharpes n'était pas stockée, il a fallu re-exécuter ;
(b) juger la stratégie sur autre chose que le DSR exigeait des bras de contrôle qui sont, eux, de
vrais essais.

---

## 8. Verdict

### ❌ **REJECTED**

| gate | verdict | note |
|---|---|---|
| DSR (recalculé, σ mesuré) | ✅ **PASS** | **le kill d'origine est annulé** — DSR 1.000, robuste jusqu'à N=981 |
| L38 β-orthogonalité | ✅ PASS | R² 0.04 %, α HAC t=3.89 — le kill « ne bat plus le buy&hold récent » était bien la mauvaise lentille |
| L26 fill de **sortie** | ❌ **FAIL** | 25 % des stops traversés à l'ouverture ; Sharpe 0.99 → 0.49 |
| L36 portage overnight mesuré | ❌ FAIL | 8 nuits de tenue, 43–53 % du gross mangé |
| L58 espérance inconditionnelle | ❌ **FAIL** | à géométrie constante la condition est **négative** (−0.020) vs +0.041 inconditionnel |
| L25 two-sided | ❌ FAIL | la jambe short passe négative dès le pricing honnête, et vaut −0.054 en régime récent |
| L31 régime | ❌ FAIL | 2019+ négatif après coûts réels, p(≤0) = 0.89 |
| Ratio coût (mesuré, 1.5×) | ❌ FAIL | 1.47 (S036) plein échantillon, 0.41 (S035) en récent |
| **Intégrité des données** | ❌ **FAIL** | 51 % du P&L sur des séries à fourchette quotidienne médiane **nulle** |
| L53 véhicule | ❌ FAIL | la seule classe dont la granularité tient sur €13 k est celle où l'edge n'existe pas |

**La réhabilitation du DSR est réelle, complète, et ne change rien au sort du dossier.** C'est un bon
résultat : elle valide le diagnostic de l'inventaire sur le gate cassé, elle ferme définitivement
S035/S036, et elle établit que les **deux** motifs de kill d'origine étaient faux — la stratégie
survit à ses accusateurs et meurt de trois causes que personne n'avait regardées.

### Portée pour les 3 autres « échouent uniquement le DSR »

S012/S013/S043 ont été tués indépendamment (l'inventaire l'a vérifié). Mais deux constats de cette
session s'appliquent à **toute la cohorte des 109** et ne sont, eux, dans aucun gate :

1. **Le gate délai+1 de `ftmo_lab` ne re-price que l'entrée.** Toute stratégie de la famille
   « stop-entry + bracket-exit » (S001 Crabel, ORB, NR7, breakouts…) a ses sorties remplies au niveau
   exact du stop. Le « ✅ PASS délai+1 » de l'audit ne certifie que la moitié du trade.
2. **Le magasin `ohlc/` mélange trois qualités de données sans marquage.** XPTUSD et XPDUSD
   (fourchette médiane nulle) et XAGUSD (22.7 % de barres plates) contaminent toute stratégie qui lit
   `high`/`low`. `_coverage.csv` documente la source mais rien dans le pipeline n'en tient compte.

⇒ **Candidat de leçon (nommé, non numéroté)** : *« un gate de fill qui ne re-price que l'entrée
certifie la moitié du trade — et une barre dont `high == low` rend indéfinie toute machinerie de stop
intrabar ; contrôler la dégénérescence de fourchette AVANT de lire un OHLC comme un OHLC. »*
À graver en réconciliation si retenu, pas ici.

---

## 9. Fichiers

```
repro.py             re-exécution verbatim des 2 grilles + champs supplémentaires (nuits, risk0, entry_px)
dsr_recalc.py        DSR publié vs corrigé, echelle de N            -> dsr_recalc.csv
mechanism.py         anatomie, swap mesuré, coûts, L58 v1, L38, ères -> mechanism.json
mechanism2.py        L58 à géométrie constante, source des données, bootstrap -> mechanism2.json
exitfill.py          fill de sortie réaliste + fréquence de gap par source -> exitfill.json,
                                                             gap_frequency_by_source.csv
final.py             échelle consolidée                            -> s03*_ladder.csv, final_ladder.json
s03*_grid_metrics.csv        LA grille de Sharpes que l'audit n'avait pas persistée
s03*_trades_{point,best}.parquet
```

Reproduction : `/usr/bin/python3 repro.py && /usr/bin/python3 dsr_recalc.py && /usr/bin/python3
mechanism.py && /usr/bin/python3 mechanism2.py && /usr/bin/python3 exitfill.py && /usr/bin/python3
final.py` (~40 s au total). Aucun fichier hors de ce répertoire n'a été modifié ; rien n'a été commité.
