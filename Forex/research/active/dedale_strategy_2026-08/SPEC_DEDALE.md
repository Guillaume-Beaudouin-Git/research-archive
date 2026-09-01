# SPEC — « Dédale » (DédaleFormation.mq5), reconstruite depuis le code + le transcript

Source code : `Algorithm_Brieuc/DédaleFormation.mq5` (806 lignes, UTF-16LE — converti). Source
narrative : `Algorithm_Brieuc/Transcript_Vidéos_Brieuc.md` (6 vidéos, 232 959 caractères) +
`Algorithm_Brieuc/Backtest brieuc.md` (vidéo de résultats, 0 mention de TDI/pivot/angle — ne
décrit AUCUN paramètre, seulement le P&L final).

## 1. Mécanisme d'entrée (fidèle au code, ligne par ligne)

### 1.1 Pivots hebdomadaires (`SupportPivot`/`ResistancePivot`, lignes 172-228)
`PIVOT_TIMEFRAME = PERIOD_W1` (défaut, ligne 43), `PIVOT_NUMBER = 2` (ligne 44). Calculés sur le
**dernier bar W1 CLOS** (`iHigh(...,1)` = shift 1, jamais le bar en formation — pas de lookahead
dans le code lui-même).

```
P0 = (H + L + C) / 3
R1 = 2*P0 - L        S1 = 2*P0 - H
R2 = P0 + (H-L)      S2 = P0 - (H-L)
```
`H, L, C` = high/low/close de la semaine calendaire précédente complète.

### 1.2 Choix du couple (SL, TP) par appariement de probabilité (`GetTradeInfo`, lignes 476-570)
Pour chaque direction, l'EA teste les **4 combinaisons** {S1,S2}×{R1,R2} (i,j ∈ {0,1},
`PIVOT_NUMBER²=4`), calcule pour chacune une "probabilité de SL" :
```
sl_probability = tp_size / (tp_size + sl_size) * 100
```
(c'est un ratio risk/reward inversé en %, PAS une probabilité empirique — aucune calibration
statistique, c'est un nom trompeur dans le code lui-même), **seulement si le prix courant est
strictement contenu entre le support et la résistance testés** ; sinon `sl_probability = 151`
(valeur sentinelle hors-borne). L'EA choisit la combinaison qui minimise
`|sl_probability - TARGET_PROBABILITY|` avec `TARGET_PROBABILITY = 50` (ligne 45, défaut) — donc
en pratique il cherche une paire SL/TP à peu près **1:1 en risk/reward** (car ratio 50 % ⟺
`tp_size ≈ sl_size`). **Défaut de code non corrigé** : si aucune des 4 combinaisons n'a le prix
contenu dans la bande (les 4 valent 151), l'algorithme choisit quand même arbitrairement la
première combinaison testée en cas d'égalité — comportement reproduit fidèlement, pas corrigé,
dans notre backtest.

### 1.3 Filtres TDI (`CheckTradeSignal`, lignes 336-473) — **15 booléens, tous `false` par défaut**
5 timeframes (`TDI_TIMEFRAME0..4` = M15/M30/H1/H4/D1, lignes 47-51) × 3 types de condition
(`_CROSS`, `_TREND`, `_ANGLE`, lignes 58-72) = 15 booléens indépendants. La fonction ne renvoie
`true` que si **toutes** les conditions activées sont simultanément vraies (`cross_check_sum ==
cross_condition_sum` etc., lignes 461-464) — désactivée (`false`), une condition ne contribue
jamais au filtre (elle est neutre, pas "toujours vraie" : cf. ligne 419-430, un check désactivé
force `*_condition[timeframe] = false` mais son poids dans le sum désactivé aussi car
`*_check[timeframe]` vaut 0 → ne compte pas dans `*_check_sum`). **Avec les 15 booléens à leur
valeur par défaut (false), la fonction retourne inconditionnellement `true`** : il n'existe
**aucun filtre technique actif** dans la configuration par défaut du code livré.

### 1.4 Filtre de swap — **la découverte structurelle centrale** (`IsTradeAllowed`, lignes
743-806)
```
input bool IS_NEGSWAP_ALLOWED = false;   // ligne 93, défaut

// achat (direction=0) :
if(!IS_NEGSWAP_ALLOWED && swap_long <= 0)  return false;   // ligne 777
// vente (direction=1) :
if(!IS_NEGSWAP_ALLOWED && swap_short <= 0) return false;   // ligne 789
```
**Par défaut, l'EA refuse d'ouvrir toute position dont le swap serait négatif ou nul.** Ce n'est
pas un filtre optionnel accessoire : c'est un **veto structurel** appliqué à chaque signal, dans
les deux sens. Confirmé verbatim par l'auteur au minutage ~213 000-214 500 (Vidéo 6) : *« est-ce
qu'on ferait pas […] un moyen de ne trader uniquement dans le sens du carry trading […] et si
[les swaps] sont inférieurs à zéro alors on ne prendra pas de trade dans cette direction là »*,
puis, en nommant explicitement le mécanisme : *« pour le car[ry] trading, pour ma stratégie qui a
fait ma carrière […] on va faire swap tir du bas short […] return false ici […] swap tir du B
long si c'est inférieur ou égal à zéro donc si on ne gagne pas d'intérêt et bien on ne veut pas
prendre de trade »*. **L'auteur qualifie lui-même sa propre stratégie de « carry trading » et
attribue sa carrière à ce mécanisme.** Ceci répond directement à la question n°2 du mandat : le
biais vers le swap positif n'est pas un sous-produit accidentel, il est câblé en dur dans la
condition d'entrée elle-même.

### 1.5 Autres filtres d'admissibilité (`IsTradeAllowed`)
- Pas de hedging par défaut (`IS_HEDGING_ALLOWED = false`, ligne 92) : une direction ouverte
  bloque l'autre.
- `SPREAD_MAX = 2` pips (ligne 94) — **non modélisable** ici (colonne `spread` inutilisable, cf.
  mandat) ; remplacé par le barème de coût fixe RT déclaré en §4 de `PREREGISTRATION.md`.
- `SL_DISTANCE_MIN = TP_DISTANCE_MIN = 10` pips (lignes 95-96) : le trade est rejeté si le prix
  est à moins de 10 pips du SL ou du TP calculé.

## 2. Sortie
Stop loss et take profit **fixes**, posés sur les niveaux de pivots au moment de l'entrée
(§1.2) — aucun trailing, aucune sortie sur signal, aucun time-stop dans le code. L'auteur le
confirme explicitement (Vidéo 4, offset ~145 900) : *« c'est pas le genre d'algo que tu peux
optimiser parce que les stop loss et les take profit sont fixes […] sur des niveaux de prix fixe
sur les points pivots »*.

## 3. Sizing
`RISK_MODE = 0` (Pourcentage, défaut, ligne 85), `RISK_PCT = 1` (défaut, ligne 86) — confirmé par
la démo de l'auteur (Vidéo 6, ~fin) sur un compte à $100 000 : *« on va risquer 1000 dollars par
trade »* = 1 % du solde courant. Sizing dynamique par distance au SL (`CalculateLotSize`, lignes
647-697) : le nombre de lots est calculé pour que la distance SL corresponde exactement à 1 % du
solde — **équivalent, en unités de R-multiple, à risquer un montant fixe indépendant de la
distance SL** (une propriété standard du position-sizing par risque fixe, pas un artefact du
code). Le risque est recalculé à chaque trade sur le solde **courant** ⇒ **intérêts composés**,
comme l'auteur le précise lui-même dans la même vidéo en comparant au mode "argent fixe".

## 4. Configuration retenue pour la reproduction — **déclarée AVANT tout calcul**

**Aucune des deux sources ne révèle la combinaison exacte des 15 booléens TDI utilisée pour le
backtest chiffré (648 trades, 2018-2024) montré dans `Backtest brieuc.md`.** Recherche exhaustive
effectuée : 89 occurrences de "TDI", 106 de "angle", 63 de "croisement", 143 de "pivot" dans le
transcript — **aucune ne fixe une configuration finale**. La seule instance concrète observée est
une **démonstration pédagogique** (Vidéo 4, offset ~145 500-146 000) où l'auteur active
**uniquement** `TDI_TIMEFRAME3_CROSS` (= H4, croisement rapide/lent) dans le Visualiseur de
Stratégie MetaTrader, pour illustrer le fonctionnement du filtre sur une fenêtre de quelques mois
en 2024 — il précise lui-même *« on va en choisir qu'un pour le moment »*, ce n'est pas présenté
comme la configuration de production, et cette démo ne couvre pas 2018-2024.

Conformément au mandat (*« Si un paramètre reste indéterminé, dis-le explicitement et choisis la
valeur par défaut du code »*), la reproduction retient donc :

**Config A — DÉFAUT DE CODE (config primaire, entièrement déterminée, zéro paramètre inventé)**
: les 15 booléens TDI à `false` (aucun filtre technique actif). Le signal se réduit
mécaniquement à : *entrer dans la direction où le swap est positif, dès que flat, avec SL/TP
posés sur les pivots hebdomadaires les plus proches d'un ratio risk/reward 1:1, sous réserve des
filtres de distance minimale.* C'est un choix **défendable et utile** : il isole exactement le
squelette carry + pivot du système, sans aucune composante TDI non-identifiée — la comparaison la
plus honnête possible avec l'hypothèse n°2 du mandat (part swap vs part signal).

**Config B — DÉMO H4-CROSS (secondaire, illustrative, PAS vérifiée comme config de production)**
: identique à A + `TDI_TIMEFRAME3_CROSS = true` (croisement rapide/lent du TDI H4). Rapportée à
titre de sensibilité uniquement ; jamais présentée comme réplication du chiffre revendiqué.

Nous n'avons **pas** cherché, par recherche combinatoire sur les 32 768 configurations, une
combinaison qui reproduirait 648 trades / 11 jours de tenue moyenne — ce serait de l'optimisation
post-hoc sur la cible, explicitement interdite par le mandat (*« N'optimise rien »*) et par la
hard rule "max 3 modifications par hypothèse".

## 5. Optimisation revendiquée par l'auteur — réponse à la question DSR du mandat

Recherche des 15 occurrences d'« optimis » dans le transcript (offsets listés) : l'auteur
affirme **explicitement, deux fois, ne PAS avoir optimisé** cette stratégie (Vidéo 4, offset
~145 824-146 550) : *« on fera pas d'optimisation je précise parce que c'est pas le genre d'algo
que tu peux optimiser […] c'est un signal unique qui existe tel qu'il est et qui n'est pas
optimisable donc ça aussi c'est un gros défaut de cette stratégie mais qui n'est aussi pas
tellement un défaut parce que du coup tu évites la suroptimisation, tu évites le
surentraînement »*. Toutes les autres occurrences d'« optimis » dans le transcript concernent la
**qualité du code** (refactoring, lisibilité, vitesse d'exécution), jamais un balayage de
paramètres de stratégie.

**Conséquence méthodologique** : à prendre l'auteur au mot, il n'y a pas de recherche
d'hyperparamètres à corriger par DSR au sens strict de Bailey-López de Prado (pas de
`n_trials` explicite sur cette stratégie). Mais deux réserves demeurent, à rapporter honnêtement :
(a) le **choix des 15 booléens et de leurs timeframes reste un degré de liberté de conception non
documenté** — même sans grid-search formel, le fait de ne JAMAIS révéler la configuration
utilisée pour LE chiffre cité est en soi un signal d'alerte (impossibilité de distinguer
"non-optimisé" de "sélectionné informellement puis non documenté") ; (b) le **PSR qu'il cite
(98,97 %) ne corrige PAS le multiple testing** — c'est précisément la différence entre PSR et DSR
(Bailey & López de Prado, 2014) : le PSR teste la significativité d'UN Sharpe candidat contre un
seuil, en tenant compte de skewness/kurtosis de la série de rendements, mais ne pénalise pas le
nombre d'essais qui ont mené à ce candidat. Si un choix informel de config (même non formalisé en
grid-search) a eu lieu parmi les 32 768 combinaisons possibles avant de fixer celle du backtest
montré, le PSR à 98,97 % est **sans objet** vis-à-vis de cette question — il répond à une
question différente. Nous ne pouvons trancher (a) faute de preuve documentaire, et le déclarons
explicitement comme incertitude résiduelle plutôt que de trancher par excès de sévérité.

## 6. Univers et paires
L'auteur revendique *« toutes les paires »*, en insistant sur le fait qu'il a **gardé les paires
perdantes** (pas de survivorship bias déclaré — un point solide à son crédit, cf. §Ce qui est
bien fait du rapport). Notre reproduction est limitée aux **7 paires FX majeures USD** disponibles
en cache M1 vrai-UTC (`EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD`) — un
**sous-ensemble**, pas l'univers complet (probablement ~25-30 paires chez un courtier MT5
généraliste, majors + minors + quelques exotiques). Cette limitation abaisse mécaniquement la
fréquence de trading reproduite (moins de paires ⇒ moins d'opportunités) et doit être lue comme
telle : un écart entre notre fréquence et ses ~100 trades/an ne réfute PAS son chiffre, il reflète
l'univers plus restreint. Déclaré ici, avant calcul, pour ne pas être réinterprété a posteriori.
