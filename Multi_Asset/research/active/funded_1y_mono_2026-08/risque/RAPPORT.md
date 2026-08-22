# Compte FTMO funded — à quoi s'attendre

**Analyse de risque. 2026-08-21.** Retraits, drawdowns, ruine.
Aucune re-simulation : ce document **mesure** les trajectoires déjà produites par
`code/run_2ans_path.py` (clone instrumenté de `engine_v22.run_funded`).

| | |
|---|---|
| Source | `out/paths_2ans.parquet` — 280 cohortes × 3 scénarios × 504 jours trades |
| Fenêtre historique | 2013-10-01 → 2026-06-05, **3 295 jours trades** [V `dates_idx.csv`] |
| Scénario de référence | **`0.96_mesure`** — coût ORB au spread FTMO natif mesuré |
| Contraste | **`ORB_OFF`** — c'est la décision ouverte |
| Book simulé | jambes ON (US100 22:05, GER40 17:35) + ORB funded $25/trade. **Or = 0, J1 = 0** [V `run_2ans_path.py:73`] |
| Config | `CFG_FUNDED_V28`, `vm=1.00`, `orb_risk=0.0025`, `SPLIT=0.8`, `WD=14` [V] |
| Géométrie | $10 000 · plancher **statique** $9 000 · daily = ouverture − $500 · `lim_eff = max(daily, statique)` |
| Retraits | tous les **14 jours trades**, tout ce qui dépasse $10 000 sort, solde **remis à $10 000** |
| Reproduction | `/usr/bin/python3 analyse_risque.py` → `sortie_complete.txt` |

**Conséquence structurelle de la géométrie** : le buffer ne grandit jamais. Pas de
compounding, hasard de ruine **constant** dans le temps. On ne maximise ni le Sharpe ni
le taux de croissance, mais `E[Σ payouts avant ruine]`.

**Où tu es aujourd'hui** [V, lecture VPS read-only `ea_state.json`, latin-1] : compte
`<ACCOUNT_ID>`, solde **$10 013.88** au 2026-08-20, `open_days=3`, `wd_tdays=3` — jour 3
du premier cycle de retrait. Tout ce qui suit décrit les 501 jours suivants.

---

## 1. Les retraits

Scénario `0.96_mesure`, N = 280 cohortes, N = 3 554 retraits observés. [V]

| | 1 an | 2 ans |
|---|---|---|
| **Nombre de retraits** — médiane | **7** | **14** |
| p10 / p90 | 2 / 11 | 4 / 18 |
| moyenne | 6.57 | 12.69 |
| min / max | 0 / 16 | 0 / 22 |
| P(**aucun** retrait sur l'horizon) | 2.9 % | 2.5 % |

**Montant par retrait** (brut, avant split 0.8) : médiane **$75**, p10 $13, p25 $36,
p75 $133, p90 $194, max $551. **Part trader** : médiane **$60**, p90 $156. [V N=3 554]

**Délai avant le premier retrait** : médiane **14 jours trades** — c'est-à-dire *au
premier guichet possible*. p75 = 42 j (3ᵉ guichet), p90 = 70 j (5ᵉ guichet). **7 cohortes
sur 280 (2.5 %) n'ont jamais retiré en 2 ans.** [V]

**Intervalle entre deux retraits** : médiane **14 j** (guichets consécutifs), p75 42 j,
p90 84 j, max 420 j. [V]

**Fraction des fenêtres de 14 jours qui ne produisent RIEN : 64.7 %** (médiane par
cohorte 61.1 %). [V] Autrement dit : **environ deux guichets sur trois passent à
vide** — le solde est sous $10 000 le jour du guichet, il n'y a rien à sortir.

**Cash net encaissé, cumulé** (part trader) :

| horizon | p10 | p25 | **médiane** | p75 | p90 |
|---|---|---|---|---|---|
| 3 mois | $0 | $47 | **$133** | $210 | $313 |
| 6 mois | $40 | $142 | **$240** | $377 | $576 |
| 1 an | $112 | $263 | **$445** | $727 | $907 |
| 2 ans | $324 | $692 | **$1 059** | $1 276 | $1 490 |

*Convention de ce tableau : cohortes **vivantes** au jour H (N=280 jusqu'à 1 an, N=277 à
2 ans). `resume_risque.csv` emploie la convention **toutes cohortes** (dernière
observation ≤ H, les mortes comptent avec leur valeur au décès) et donne donc **$1 046**
à 2 ans au lieu de $1 059. Les deux sont justes ; l'écart de $13 est l'effet des
3 cohortes mortes.*

**Contraste ORB_OFF** [V] : 9 retraits médians sur 2 ans (vs 14), montant médian **$45**
brut / **$36** net (vs $75/$60), **74.1 %** de guichets à vide (vs 64.7 %), cash médian
2 ans **$381** (vs $1 059). L'ORB **multiplie le cash médian par 2.8**.

**P(net < 0) = 0, par construction et non par mérite.** Les retraits sont irréversibles
et le résiduel est plancheré à zéro : le trader ne peut pas *perdre* d'argent sur ce
compte, il peut seulement ne pas en gagner et perdre le fee. Le chiffre utile est donc
**P(valeur économique nette < fee €99 ≈ $115)** : **58.2 %** à 3 mois, **37.1 %** à
6 mois, **19.6 %** à 1 an, **13.6 %** à 2 ans. [V]

---

## 2. Les drawdowns

### 2.1 Deux définitions, et pourquoi elles diffèrent

`equity_totale = bal + cum_wd`, et `cum_wd` est **monotone croissante**. Donc
`d(equity_totale) = d(bal)` **partout sauf les jours de retrait**, où le solde chute de
$X et le cash cumulé monte de $X. Les deux séries de drawdown ne diffèrent donc **que**
par le cliquet des retraits — c'est un fait de construction, pas une hypothèse. [D]

- **Base `valeur_eco`** = le P&L réel de la stratégie, débarrassé du cliquet. **C'est la
  série honnête pour juger la performance.**
- **Base `solde`** = ce que l'écran MT5 affiche. Après un retrait, le solde repart de
  $10 000 et **ne peut pas** revenir au plus-haut pré-retrait avant d'avoir regagné le
  montant sorti. Une bonne partie de la « durée sous le plus-haut » sur le solde est
  donc un **artefact comptable du cliquet**, pas de la souffrance.
- Ce qui, sur le solde, est *réellement* liant : la distance au **plancher $9 000** et à
  la **ligne daily** (ouverture − $500). Ce sont les seules deux lignes qui tuent. → §3.

### 2.2 Distribution des épisodes (2 ans, `0.96_mesure`)

| base | N épisodes | /an | amp méd | p75 | p90 | p99 | max | amp % méd | durée méd | p90 | recouvr. méd | p90 | non recouvrés |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **valeur_eco** | 7 449 | **13.3** | **$51** | $130 | $256 | $449 | $1 073 | 0.48 % | **4 j** | 58 j | **2 j** | 16 j | 3.4 % |
| **solde** | 1 767 | **3.2** | **$115** | $368 | $582 | $1 012 | $1 227 | 1.14 % | **11 j** | 312 j | **3 j** | 55 j | 15.8 % |

Lecture [V, seuil de comptage $0.50] : sur la valeur économique, **~13 drawdowns par
an**, médiane **$51 et 4 jours**, recouvrés en 2 jours médians. Sur le solde, moins
d'épisodes mais plus longs — c'est le cliquet qui fusionne les petits creux en longues
plages « sous l'ancien plus-haut ».

### 2.3 Le pire drawdown attendu

Max drawdown par cohorte, **série tronquée à l'horizon** (pas de fuite d'un creux
postérieur), N = 280. [V]

**Base `valeur_eco` — le chiffre à retenir**

| horizon | médiane | p75 | p90 | p99 | max | méd % | p90 % |
|---|---|---|---|---|---|---|---|
| 3 mois | **$214** | $293 | $361 | $519 | $658 | 2.13 % | 3.53 % |
| 6 mois | **$311** | $373 | $454 | $659 | $660 | 2.98 % | 4.46 % |
| 1 an | **$349** | $448 | **$604** | **$834** | $838 | 3.44 % | 5.81 % |
| 2 ans | **$396** | $449 | **$869** | **$987** | $1 073 | 3.67 % | 8.36 % |

**Base `solde`**

| horizon | médiane | p75 | p90 | p99 | max | méd % | p90 % |
|---|---|---|---|---|---|---|---|
| 3 mois | **$298** | $369 | $463 | $621 | $728 | 2.94 % | 4.53 % |
| 6 mois | **$425** | $495 | $586 | $794 | $854 | 4.18 % | 5.71 % |
| 1 an | **$516** | $639 | $740 | $986 | $1 032 | 5.06 % | 7.15 % |
| 2 ans | **$614** | $746 | $926 | $1 089 | $1 227 | 5.97 % | 9.19 % |

⚠ Les p99 et max **dépassent $1 000**, c'est-à-dire la totalité du buffer : ces cellules
contiennent les cohortes mortes (le plus-haut était au-dessus de $10 000, le creux est le
prix au moment du breach). Ce n'est pas une incohérence.

### 2.4 Fraction du temps dans le rouge (2 ans, médiane des 280 cohortes) [V]

| | `0.96_mesure` | `ORB_OFF` |
|---|---|---|
| sous le plus-haut de la **valeur éco** | **89.9 %** | 92.3 % |
| sous le plus-haut du **solde** | 98.0 % ⚠ artefact du cliquet | 97.4 % |
| **solde < $10 000** | **68.3 %** | **79.2 %** |
| valeur éco < $10 000 (donc perte réelle) | **6.7 %** | 15.1 % |
| plus longue série ininterrompue de solde < $10 000 | **89 j** (p75 155, p90 378, max 504) | **172 j** (p90 405) |
| plus longue série de valeur éco < $10 000 | **17 j** (p90 218) | 40 j (p90 317) |
| 1ᵉʳ jour où la valeur éco repasse > 0 | méd **2 j**, p75 5, p90 22 ; jamais : 4/280 | méd 5 j, p90 49 |

Le contraste `solde < 10k` **68 %** contre `valeur éco < 10k` **6.7 %** est toute
l'histoire du cliquet : le solde est structurellement sous $10 000 les deux tiers du
temps **parce qu'on lui retire tout ce qui dépasse**, alors que la richesse réelle n'est
en négatif que 6.7 % du temps.

---

## 3. Le risque de ruine

### 3.1 P(bust)

| scénario | 3 mois | 6 mois | 1 an | **2 ans** | 5 ans (N=204) |
|---|---|---|---|---|---|
| `0.96_mesure` | 0.00 % | 0.00 % | **0.00 %** | **1.07 %** (3/280) | 13.7 % (28/204) |
| `ORB_OFF` | 0.00 % | 0.00 % | 0.00 % | **0.00 %** (0/280) | **0.00 %** (0/204) |
| `2.17_allin` | 0.00 % | 0.00 % | 0.00 % | 1.43 % (4/280) | 3.9 % (8/204) |

[V run 2 ans ; colonne 5 ans lue dans `out/cohortes_deploye.csv.gz`]

**Ces chiffres ne valent pas ce qu'ils laissent croire — voir §3.4.**

### 3.2 Daily ou statique ? Choc ou érosion ? — réponse sans ambiguïté

**51 busts sur 51, tous scénarios et tous horizons confondus, sont des busts du
PLANCHER STATIQUE $9 000. Zéro bust de la barrière daily.** [V `bust_kind` dans
`cohortes_deploye.csv.gz`, N=51]

Anatomie des 7 busts du run 2 ans [V] :

| scénario | départ | jour du bust | solde d'ouverture | perte du jour fatal | jours passés sous $9 500 avant |
|---|---|---|---|---|---|
| 0.96 | 2014-12-09 | 500/504 | $9 262 | $277 | 307 |
| 0.96 | 2014-12-23 | 490/504 | $9 130 | $163 | 353 |
| 0.96 | 2015-02-04 | 460/504 | $9 233 | $262 | 314 |
| 2.17 | 2015-01-07 | 480/504 | $9 006 | **$9** | 386 |
| 2.17 | 2015-01-21 | 470/504 | $9 018 | $21 | 371 |
| 2.17 | 2015-02-18 | 450/504 | $9 052 | $66 | 263 |
| 2.17 | 2015-03-04 | 440/504 | $9 093 | $117 | 234 |

**Le mode est une érosion lente, pas un choc.** La perte du jour fatal va de **$9 à
$277** — dans un cas le compte meurt en perdant neuf dollars. Ce qui tue, c'est d'être
arrivé à $9 006 après **234 à 386 séances** passées sous $9 500. Cohérent avec le
breaker $9 650 : **0 armement sur les 840 cohortes** [V `n_brk`]. La marge daily n'est
jamais le facteur liant — sur les 140 778 journées simulées, la perte intraday médiane
consomme **6.5 %** de la marge du jour, p99 **24.4 %**, max **94.1 %** (hors jours de
bust). [V]

### 3.3 Combien de buffer est consommé

Équité **minimale** atteinte sur 2 ans — le point le plus proche de la mort. [V N=280]

| scénario | médiane | p25 | p10 | p05 | p01 | min | buffer consommé (méd) |
|---|---|---|---|---|---|---|---|
| `0.96_mesure` | **$9 596** | $9 550 | $9 152 | $9 125 | $9 011 | $8 967 | **40.4 %** |
| `ORB_OFF` | $9 651 | $9 601 | $9 357 | $9 292 | $9 229 | **$9 229** | 34.9 % |
| `2.17_allin` | $9 564 | $9 509 | $9 002 | $9 000 | $8 997 | $8 976 | 43.6 % |

Seuils, `0.96_mesure` : P(toucher < $9 750) = **100 %**, < $9 500 = **24.3 %**,
< $9 250 = **13.6 %**, < $9 100 = **2.1 %**. [V]

Contre `ORB_OFF` : < $9 250 = **1.8 %**, < $9 100 = **0.0 %**. **Avec l'ORB éteint, le
compte n'est jamais descendu à moins de $229 du plancher en 13 ans d'historique.** [V]

### 3.4 Ce que « 1.07 % » veut vraiment dire

**50 des 51 busts observés portent la même date : 2016-11-09** (soir d'élection US).
Le 51ᵉ est daté 2015-09-01. [V `bust_date`]

Décomposition exacte du 1.07 % [V] :

```
P(bust @ 2 ans) = P(la fenêtre contient le 2016-11-09) × P(morte | exposée)
0.96_mesure :  1.07 % = 17.9 % (50/280)  ×  6.0 % (3/50)
2.17_allin  :  1.43 % = 17.9 % (50/280)  ×  8.0 % (4/50)
ORB_OFF     :  0.00 % = 17.9 % (50/280)  ×  0.0 % (0/50)
```

Ce jour-là, le book perd **$287 en intraday** (médiane sur les 50 cohortes vivantes,
p90 $296, max $302) — la plus grosse excursion adverse intraday de tout l'historique,
alors même que sa **clôture** n'est que −$122 (le book se retourne dans la journée).
Règle de survie mécanique : **il fallait ouvrir ce jour-là au-dessus de $9 302.** [V]

Or, en régime courant [V, 140 778 journées] : P(solde d'ouverture < $9 302) = **1.14 %**
des journées en `0.96_mesure`, **0.03 %** en `ORB_OFF`, **6.03 %** en `2.17_allin`.

⇒ **Le risque de ruine de ce compte tient en une phrase : mourir demande la conjonction
d'une nuit de queue (fréquence observée ≈ 1 en 13 ans) et d'un solde déjà érodé dans les
$300 du bas du buffer (≈ 1 % des journées).** Ce n'est pas un profil de choc, c'est un
profil de coïncidence entre une queue rare et un état de faiblesse rare.

⚠ **Et l'écart entre scénarios (28 vs 8 vs 4 busts à 5 ans) n'est PAS un classement de
risque** : c'est **un seul soir** ré-échantillonné par des fenêtres qui se chevauchent à
98 %. Le fait que `0.96_mesure` compte plus de morts que `2.17_allin` — alors qu'il est
moins cher et plus rentable — n'a aucune interprétation causale ; c'est du bruit sur un
échantillon de **un événement**. [D]

**Intervalle honnête.** 1 événement potentiellement fatal en 13.1 ans ⇒ intervalle de
Poisson à 95 % sur le taux : **[0.002, 0.43] événement/an**, soit **[0.004, 0.85]**
événement attendu sur 2 ans. Multiplié par la probabilité d'être alors érodé, la vraie
fourchette de P(bust @ 2 ans) couvre grossièrement **[0.02 %, 5 %]** autour d'un point à
~1 %. **Rapporter « 1.07 % » comme une probabilité est une fausse précision d'un facteur
50.** [D]

---

## 4. Le récit opérationnel — ce que tu vas voir

*Scénario de référence `0.96_mesure`, book tel qu'il tourne réellement aujourd'hui
(jambes ON + ORB, or et J1 à zéro). Tous les montants sont en part trader (×0.8) sauf
mention contraire.*

### La texture quotidienne

**Tu perdras de l'argent la majorité des jours.** Sur 140 778 journées simulées : **45.0 %
de jours positifs, 2.4 % plats, 52.6 % négatifs**, pour une moyenne de **+$2.09** et une
**médiane de −$2.00**. L'écart-type quotidien est de $37.51, la skew de **+1.12**. [V]
Le compte gagne par la queue droite, pas par la régularité : p95 = +$67, p99 = +$124,
max +$346 ; en face, p05 = −$41, p01 = −$77, pire journée −$277.

Concrètement : ouvrir MT5 un jour au hasard, c'est **une chance sur deux de voir du
rouge**, et **68 % de chances de voir un solde sous $10 000**. C'est le régime normal du
compte, pas un signal d'alarme.

### Les 3 premiers mois (jours 1 à 63)

- **Premier retrait : jour 14** dans le cas médian — au tout premier guichet possible.
  Mais 17.5 % des cohortes n'ont **rien retiré du tout** au bout de 3 mois. [V]
- **2 retraits médians**, cash encaissé médian **$133**. Le quart défavorable est à
  **$47**, le décile à **$0**. [V]
- Le pire creux du trimestre : **−$214** médian sur la valeur économique (2.1 %),
  **−$298** sur le solde. p90 : −$361 / −$463. [V]
- **58.2 % des cohortes n'ont pas encore remboursé le fee de €99** au bout de 3 mois. [V]
- Ce que tu ne verras **pas** : le breaker $9 650 (0 armement sur 840 cohortes), et une
  journée qui consomme la marge daily (p99 = 24 % de la marge). [V]

### L'année 1 (jours 1 à 252)

- **7 retraits** médians, **$60 net** chacun en médiane. **Deux guichets sur trois
  passent à vide.** [V]
- **$445 net** encaissés en médiane, soit **~$37/mois**. p25 $263, p75 $727. [V]
- Le pire creux de l'année : **−$349** (valeur éco) / **−$516** (solde) en médiane ;
  **−$604 / −$740** au p90 ; **−$834 / −$986** au p99. [V]
- Tu passeras **~70 % de l'année avec un solde sous $10 000**, dont une série
  ininterrompue de **89 jours** (médiane ; p90 : 378 jours). [V]
- **P(bust) sur l'année 1 : 0 sur 280 cohortes**, tous scénarios — et **0 sur 305
  cohortes × 5 scénarios de coût** dans le run à horizon 1 an (`cohortes_deploye.csv.gz`,
  1 525 cohortes-scénarios, zéro mort). **Le compte ne meurt pas en un an dans cet
  historique.** [V]
- **19.6 %** des cohortes n'ont toujours pas remboursé le fee. [V]

### L'année 2 (jours 253 à 504)

- Cumul 2 ans : **14 retraits**, **$1 059 net** de cash médian (~$44/mois), pire creux
  **−$396 / −$614**. [V]
- C'est là qu'apparaît la mortalité : **3 cohortes sur 280**, toutes le **même soir**,
  après **plus de 400 séances** d'érosion. [V]

### Le scénario médian, en une phrase

> Le solde oscille sous $10 000 les deux tiers du temps, remonte au-dessus juste assez
> souvent pour déclencher **un guichet sur trois**, et te verse **$60 environ, 7 fois par
> an** (soit un versement toutes les ~36 séances). Au bout de deux ans tu as encaissé
> **$1 059** et tu n'es jamais descendu sous **$9 596**.

### Le mauvais scénario (p10) — celui qu'il faut avoir vu avant

> Valeur économique nette à j21 : **−$97**. À j63 : **−$136**. À j126 : **−$121**. À
> j252 : **−$181**. À j504 : **−$197** sur les survivantes, **−$230** en comptant les
> 3 mortes (`resume_risque.csv`). [V]
>
> **Le décile défavorable ne repasse jamais durablement positif en deux ans.** Tu paies
> €99, tu regardes une valeur économique négative pendant deux ans, tu encaisses tout de
> même **$324 de cash** au p10 (les retraits sont irréversibles, ils sont sortis les bons
> mois), et tu finis avec un solde résiduel sous $10 000. Tu ne meurs pas. Tu ne gagnes
> pas non plus.

Le quart défavorable, lui, est moins sombre : p25 à 1 an = **$263** de cash, à 2 ans
**$692**. Et le p90 est à **$1 490** sur 2 ans. [V]

### Les trois signaux qui doivent te faire réagir — et le seul qui compte

1. **Solde sous $9 500** — tu es dans les 5.8 % de journées les plus basses. Les 7 morts
   y ont toutes passé **234 à 386 séances** avant de mourir. [V]
2. **Solde sous $9 302** — 1.14 % des journées. C'est le seuil au-dessous duquel le soir
   du 2016-11-09 t'aurait tué. **C'est la seule ligne actionnable de tout ce rapport.**
3. Le breaker $9 650 ne s'arme jamais dans le sim : **ne compte pas dessus comme
   protection**, c'est un plancher qui n'a jamais été testé en simulation. [V 0/840]

### Et la décision ORB

| | `0.96_mesure` (ORB ON) | `ORB_OFF` |
|---|---|---|
| cash net 2 ans, médiane | **$1 059** | $381 |
| retraits 2 ans, médiane | 14 | 9 |
| P(bust) 2 ans / 5 ans | 1.07 % / 13.7 % | **0 % / 0 %** |
| équité min jamais atteinte, sur 280 cohortes | $8 967 | **$9 229** |
| P(descendre sous $9 250) | 13.6 % | **1.8 %** |
| P(journée ouverte sous $9 302) | 1.14 % | **0.03 %** |
| pire creux 2 ans (valeur éco, médiane) | $396 | $384 |

**L'ORB apporte ×2.8 de cash médian et, dans cet historique, la totalité du risque de
ruine.** Le creux *médian* est presque identique ($396 vs $384) — l'ORB ne rend pas la
vie quotidienne plus douloureuse, il déplace uniquement la **queue** : il fait passer le
compte de « jamais à moins de $229 du plancher » à « 13.6 % de chances de descendre à
moins de $250 du plancher ». **Mais lire §5.2 avant de trancher : les $678 de gain
médian de l'ORB reposent sur un ledger à slippage nul sur ses deux jambes.**

---

## 5. Ce que la simulation ne capture PAS

### 5.1 Les cohortes se chevauchent — l'échantillon n'est pas 280

[V] Les 280 cohortes démarrent tous les **10 jours trades** et durent **504 jours**.
Deux cohortes voisines partagent **98.0 %** de leurs journées. L'ensemble couvre
**3 294 jours trades = 13.1 ans**, soit **6.5 fenêtres de 2 ans indépendantes** (et
2.6 fenêtres de 5 ans).

**Conséquence à appliquer littéralement** : les **médianes** de ce rapport sont solides
(elles décrivent 13 ans de marché réel) ; les **queues et les probabilités
d'événements rares le sont beaucoup moins**. Le « N = 280 » qui apparaît partout est un
N d'affichage, pas un N statistique. Toute probabilité inférieure à ~15 % dans ce
document repose sur **un ou deux épisodes historiques**, jamais sur 280 tirages.
Démonstration directe : les 51 busts se réduisent à **2 dates**.

### 5.2 Le ledger ORB est idéalisé sur ses deux jambes — vérifié ici

[V, mesuré sur `nq_v2_trades.parquet`, N = 4 013 trades 2010-2026] :

- `entry == level` au prix exact : **4 013 / 4 013**
- `stop_eff == stop_level` au prix exact : **4 013 / 4 013**
- sorties `STOP` remplies au stop exact : **1 590 / 1 590**

**Slippage nul sur l'entrée ET sur la sortie, sur la totalité du ledger.** C'est
exactement le cas que la **leçon L59** interdit : « le delay+1 ne certifie que l'ENTRÉE
— re-pricer la SORTIE séparément ; 25 % des barres de stop ouvrent au-delà du stop »,
avec un effet mesuré ailleurs de **SR 0.99 → 0.49**. **L59 n'a jamais été appliquée à ce
ledger.**

Cela contamine les deux moitiés de ce rapport dans le même sens : l'ORB porte
**$678 des $1 059** de cash médian 2 ans (**64 %**, ou $665/$1 046 = 64 % en convention
`resume_risque.csv`) **et** la totalité de la mortalité
observée. Un re-pricing L59 dégraderait le rendement ORB **et** ferait descendre les
comptes plus près du plancher plus souvent. **[NV] l'ampleur : non mesurable sans
re-construire le ledger avec des sorties re-pricées.**

### 5.3 Les swaps viennent d'un panel à ancre périmée

[V] `panel_swapL/S.parquet` s'arrête au **2026-06-05**, et les spécifications de swap qui
l'alimentent ont été lues le **2026-06-10 sur un compte démo FTMO STANDARD**
(`config_v22.py:103-104`) — alors que le compte live est un **Swing**. Les valeurs ne
prennent que **14 à 18 niveaux distincts sur les 400 derniers jours** : c'est une
reconstruction en escalier, pas une facturation mesurée jour par jour.

Or **L36 / L55** établissent que le carry overnight est le tueur structurel des books
FTMO tenus (swap ≈ 48 % du gross mesuré sur un cas comparable). Ce book est **long-only
overnight sur indices** : il est exactement dans la classe où l'erreur de swap se
capitalise. **[NV] le biais net** — non mesurable sans relever les swaps réels du compte
Swing sur plusieurs mois.

### 5.4 La granularité M5 sous-estime l'excursion adverse

[V par construction, `engine.load_market`] : les trajectoires sont calculées sur des
**closes M5**. `eq_min` est donc un **minimum sur des clôtures de 5 minutes**, jamais un
minimum sur les ticks. La vraie MAE intraday est **strictement pire** que tout `eq_min`
rapporté ici — et c'est précisément la métrique qui décide de la survie (le breach FTMO
est évalué en continu sur l'équité).

L'ordre de grandeur compte : le seuil fatal du 2016-11-09 a été franchi de **$270-$300**,
mesuré en closes M5. **[NV] de combien un tick-by-tick l'aurait creusé.**

### 5.5 Le précédent documenté où le sim a sous-estimé une queue

[V mémoire `breach_<ACCOUNT_ID>_2026-07-02`] Le compte **<ACCOUNT_ID>** a été breaché sur un
**flash USDJPY**, J1 à 16.8× de levier : « la liquidation continue bat le breaker M5
discret », et le verdict enregistré est explicite — **« le sim sous-estime cette
queue »**. Deux mécanismes, tous deux absents ici : la liquidation en continu, et le
saut de prix intra-barre.

Complément [V mémoire `ath_regime_review_2026-08`] : **1/3 des morts échappe au breaker
M5** (saut + halt). Et une correction en sens **inverse** au même dossier — le levier
réellement déployé est de **~4.5-5.4× par jambe et non 10.6×** (cap de marge Swing
mordant 69 % du temps), ce qui **surestimerait** la mortalité d'un facteur ~2.5. **Les
deux corrections n'ont pas été composées ; le signe net du biais est [NV].**

### 5.6 Divergences et angles morts non résolus

- [V `CARTE_EV_2026-08-20.md:104`] **« les deux modèles de risque du repo divergent d'un
  facteur ~4 »** sur le levier des jambes ON. Ce rapport n'utilise qu'**un** des deux.
- [V] Le book simulé a **or = 0 et J1 = 0**, ce qui correspond au book réellement
  déployé. Mais les gates peuvent se rouvrir (`RAPPORT_STRATEGIE` : P(gate J1 ouvert)
  6 % / 27 % / 36 % à 1/3/6 mois). **Si un moteur se rallume, tout ce rapport est
  périmé.**
- [V] L'historique s'arrête au **2026-06-05** : les **2.5 derniers mois** de marché, dont
  les 3 premiers jours du compte live, ne sont pas dans l'échantillon.
- [NV] Le harness de simulation a été pris en défaut ailleurs (`wall_economics_2026-08` :
  « le harness comptait des GAGNANTS comme des morts » ; `CFG_LIVE` omettait le backstop
  min-trading-days, **même littéral non ré-audité dans un autre dossier**). Je n'ai
  **pas** audité `CFG_FUNDED_V28` pour le même défaut de classe. En funded il n'y a pas
  de contrainte de jours minimum, donc ce défaut précis ne s'applique pas — mais
  **l'audit du harness funded reste à faire**.

---

## Annexe — fichiers produits

| fichier | N lignes | contenu |
|---|---|---|
| `drawdowns.csv` | 24 046 | un drawdown / ligne : `scenario, cohort, base, debut_jour, fin_jour, duree_j, amplitude_usd, amplitude_pct, recouvre, jours_recouvrement` — `debut_jour` = jour du plus-haut, `fin_jour` = jour du creux, `duree_j` = jours strictement sous le plus-haut, seuil de comptage $0.50 |
| `payouts.csv` | 9 001 | un retrait / ligne : `scenario, cohort, n_payout, jour, montant_usd, montant_net_trader` |
| `resume_risque.csv` | 12 | une ligne par (scénario × horizon 3m/6m/1an/2ans), 30 colonnes |
| `trajectoires_quantiles.csv` | 1 512 | éventail par (scénario, jour) : quantiles p05→p95 de la valeur éco et du solde, cash médian, `eq_min` p05/min — **prêt pour un fan chart** |
| `dates_idx.csv` | 3 295 | index des jours trades (permet `date = dates_idx[10 × cohort + jour − 1]`) |
| `sortie_complete.txt` | 220 | toutes les tables détaillées |
| `analyse_risque.py` | — | script de reproduction, `/usr/bin/python3` |
