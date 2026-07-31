# Le dénominateur : quel est le coût RT réel par instrument FTMO ?

**2026-07-31. Audit N0 (fouille, zéro essai consommé).** Motivation : toute la sélection de
familles repose sur « le gross dépasse-t-il le coût ? ». Ce fichier établit ce que le repo
mesure réellement, ce qu'il suppose, et où les deux divergent.

## 1. Il existe DEUX tables de coûts incompatibles

| Instrument | `outputs/phase0_rt_cost_bps.csv` (sim v22, livre live) | `top10_test/framework.py` (funnel 164 tests) |
|---|--:|--:|
| US100 / US500 / US30 | 2.20 | 1.50 |
| GER40 | 2.20 | 2.50 |
| **XAUUSD** | **1.84** | **3.50** |
| FX major | 1.13 – 1.36 | 1.50 |
| Crypto CFD | 18.5 | 12.0 |

`framework.py` se déclare « per rules.md, last_verified 2026-06-01 » — ce sont des **valeurs de
catalogue**, pas des mesures. `phase0` se déclare mesuré. Les deux ont piloté des décisions
différentes sans jamais être rapprochées.

## 2. Comment `phase0` est réellement construit — `research_panel.py:68-73`

```python
sp = (np.nanmedian(spreads[s].tail(750)) if s in spreads else
      {"index": 1.2, "crypto": 8.0}.get(kind, 2.0))
rt[s] = sp + 2 * SLIPPAGE_BPS[kind] + commission_bps(...)
```

Deux défauts, de sens **opposé** :

**(a) Les indices ne sont jamais mesurés.** `load_all()` charge les indices depuis
`ftmo_close.csv`, qui ne contient que des clôtures ⇒ ils n'entrent jamais dans le dict `spreads`
⇒ ils tombent tous sur le `1.2` codé en dur. Or **la mesure existe** dans
`cache/{US30,US500,US100,GER40}_daily_cet.parquet`. Chiffres réels contre l'hypothèse :

| | spread médian mesuré | hypothèse codée | RT total supposé | RT total mesuré |
|---|--:|--:|--:|--:|
| US30 | **0.465** | 1.20 | 2.20 | **1.47** |
| GER40 | **0.730** | 1.20 | 2.20 | **1.73** |
| US100 | **0.804** | 1.20 | 2.20 | **1.80** |
| US500 | **0.824** | 1.20 | 2.20 | **1.82** |

⇒ le sim v22 est **conservateur de ~20-33 %** sur les indices. Ce n'est pas un bug dangereux
pour le livre en production, mais c'est un **faux plafond pour la recherche**.

**(b) `nanmedian` n'ignore que les NaN, pas les zéros** — et la colonne est zéro-inflée sur une
partie du FX. Fraction de jours à spread nul et médiane résultante :

| | % jours à spread 0 | médiane retenue | plausible ? |
|---|--:|--:|---|
| EURUSD | **33.2 %** | **0.093** | non — ~13× trop bas |
| EURGBP | 4.8 % | 1.153 | oui |
| GBPUSD | 4.7 % | **0.242** | non |
| AUDUSD | 4.0 % | 0.855 | oui |
| USDCAD | 1.5 % | **0.437** | douteux |
| USDJPY | 1.2 % | **0.264** | non |

⇒ sur EURUSD, GBPUSD, USDJPY, USDCAD, le coût modélisé est **biaisé vers le bas**. Les familles
FX tuées SUR LE COÛT (L34, L43) en sortent **renforcées** ; tout PASS sur ces paires est suspect.

## 3. Le finding le plus actionnable : l'or a été sur-pénalisé d'un facteur 1.9

`framework.py` coûte l'or à **3.50 bps** RT. La mesure : spread médian **0.699** + slippage
2×0.5 + commission ⇒ **1.84 bps**. Le funnel top10 (**164 tests**) a donc appliqué à l'or un
coût **1.9× le réel**. L'or est le porteur du livre live. **Tout candidat or rejeté sur le coût
dans ce funnel est à réexaminer** — c'est un réservoir d'erreurs de type II identifié, pas une
spéculation.

## 4. Les matières souples et le gaz sont hors-jeu, définitivement

0 % de barres nulles ⇒ ce sont de vraies mesures, pas un artefact :

| COCOA | NGAS | COTTON | SOYBEAN | SUGAR | COFFEE |
|--:|--:|--:|--:|--:|--:|
| **1189 bps** | **300** | **282** | **153** | **144** | **142** |

Soit 1.4 % à 11.9 % de coût aller-retour. **Aucun edge connu ne franchit ça.** Cette classe est
fermée sur le véhicule CFD, sans avoir besoin de tester quoi que ce soit. (Le chiffre COCOA est
assez extrême pour mériter un contrôle d'unités si jamais quelqu'un y revient — mais la
conclusion ne dépend pas de lui.)

## 5. Ce que ça fait au seuil L33b

L33b dit : « un signal intraday-flat doit produire > 3 bps de gross pour exister », dérivé d'un
**3 bps RT conservateur**. Sur les indices, le RT mesuré est **1.5-1.8 bps**. Le seuil réel
devient **~2.5 bps de gross** au gate 1.5×, au lieu de 4.5.

**Mais** — et c'est la réserve décisive — le sprint du 30/07 a établi que la colonne `spread`
est **2.4× optimiste même quand elle est peuplée**, mesuré contre le RT FTMO réel. Si ce facteur
s'applique aux indices, le RT réel remonte à **~2.9 bps** et le seuil L33b d'origine était juste.

**La fourchette honnête pour les indices est donc [1.8 ; 2.9] bps** — et §6 la tranche **par le
bas** : le compte live montre un modèle qui sur-facture, avec un dérapage médian de ~0.0-0.1 bps
au lieu des 1.0 provisionnés.

**Meilleure estimation retenue pour les indices : ~0.9 bps RT au centre** (fourchette cache
0.73-0.82 + dérapage médian ~0.1), **avec une queue à ~2.3 bps (p95) et 4.5 bps (max observé).**
À comparer aux 2.2 bps que le sim facture uniformément.

⇒ Le seuil L33b pour les indices n'est pas « > 3 bps de gross » mais **> ~1.4 bps au gate 1.5×**
sur l'espérance — à condition de continuer à provisionner la **queue** dans le calcul de
barrière. C'est un espace de recherche nettement plus large que ce que le registre supposait.

## 6. Le départage par les fills live — MESURÉ le 2026-07-31

Source : `runtime/reconcile_log.csv` (30 jours, 61 fills) + `MQL5/Files/fills.csv` et ses deux
archives (compte d'essai + compte breaché).

### 6.1 Le modèle sur-facture, de façon systématique

`reconcile.py:212-213` : `d_cost = d_exec + d_costmb`, où
`d_exec = Σ (prix_demandé − prix_rempli)·side·units`. Donc **`d_cost` = coût modélisé − dérapage
réel**, et son signe dit directement qui sur-facture.

| | |
|---|--:|
| `d_cost` cumulé sur 30 jours | **+$129.60** |
| coût modélisé total (`cost_model_usd`) | $142.50 |
| turnover notionnel | $1 357 617 |
| **coût modélisé en bps du turnover** | **1.05** (≈ 2.1 bps RT) |

Positif et persistant (23 jours ≥ 0 sur 26 renseignés) ⇒ **le modèle est conservateur, pas
optimiste.** Cela **contredit l'hypothèse « colonne spread 2.4× optimiste »** pour les
instruments du livre — au minimum, cette hypothèse ne peut pas être généralisée aux indices.

### 6.2 Le dérapage réalisé, par instrument (`slip_bps`, n=32 fills dédupliqués)

| | n | moyenne | médiane | p95 | max |
|---|--:|--:|--:|--:|--:|
| GER40.cash | 8 | −0.115 | 0.000 | 0.158 | 0.20 |
| US100.cash | 18 | −0.088 | 0.015 | **1.485** | **3.67** |
| USDJPY | 6 | +0.060 | 0.060 | 0.120 | 0.12 |

Le modèle provisionne **0.5 bps par côté**. La médiane réalisée est **~0.0-0.1 bps**.

**Le sim facture donc à chaque trade ce qui est en réalité le p95.** C'est ~2.5× trop sévère au
centre de la distribution — précisément la forme d'erreur qui fabrique des faux négatifs en
recherche — tout en étant **dépassé dans la queue** (max US100 3.67 bps, 7× la provision par
côté). Provision juste pour un problème de barrière, fausse pour un calcul d'espérance.

### 6.3 Limite dure : la fourchette n'est PAS mesurable par cette voie

`FILLS_COLUMNS` (`lib/statefiles.py:31`) ne journalise aucun bid/ask, et `req_price` est le prix
demandé à MT5 — donc **l'ask pour un achat : la fourchette y est déjà payée**. `d_exec` ne
capture que le dérapage *au-delà* du prix demandé.

⇒ On a mesuré le **dérapage** (petit, à queue épaisse), pas la **fourchette**. Le meilleur
estimateur de fourchette reste le cache (`0.73-0.82 bps` sur indices), non validé en live.

### 6.4 Réserves d'échantillon

n=32 fills, un seul compte, aux heures choisies par l'EA (rebalance en séance liquide), en
petite taille. Une famille intraday plus fréquente, ou tradant hors des heures liquides,
n'héritera pas de ces chiffres. **Ce sont des ordres de grandeur, pas des constantes.**

## 7. Raffinement à faire ensuite

`spread_med_bps` est une médiane **sur toutes les barres de la journée**, heures creuses
comprises. Une famille intraday ne trade pas « en moyenne » : elle trade à une heure précise.
Le bon dénominateur est le **spread à l'heure de trading**, calculable depuis le M1. Un edge
mesuré contre la médiane journalière et exécuté à 22:00 paie deux fois le coût supposé.

## 8. Ce que cet audit ne dit pas

Il ne dit pas que les coûts du livre live sont faux : sur les indices ils sont conservateurs, ce
qui est le bon sens d'erreur pour de la production. Il dit que **le même conservatisme, appliqué
en recherche, a fermé des portes qui ne devaient pas l'être** — et il en nomme une, l'or à 1.9×.
