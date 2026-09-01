# RAPPORT — Reproduction et test de « Dédale »

Spec : `SPEC_DEDALE.md`. Pré-enregistrement : `PREREGISTRATION.md`. Résultats bruts :
`resultats.csv`, `two_sided_*.csv`, `regime_split_*.csv`, `walkforward_*.csv`. Code :
`code/dedale_engine.py` (moteur), `code/metrics.py` + `code/run_analysis.py` (statistiques).

## Trois réponses

**(1) Sharpe correct.** Sur ses propres chiffres (+60,33 % absolu, 6,5658 ans, vol 10,91 %) : CAGR
= 7,46 %/an, **Sharpe gross ≈ 0,68-0,69**, **Sharpe en excès du taux sans risque réel (DTB3 moyen
2,21 %/an sur la fenêtre) ≈ 0,48**. Le 1,56 revendiqué en est à **2,3× (gross) à 3,2× (excès)**. La
majorité de l'écart (facteur ≈1,60 sur 2,3, soit ~70 %) s'explique mécaniquement par une
annualisation en √252 sur une série indexée par trade (~99 trades/an, L47) ; le résidu (~1,4×) est
compatible avec une absence de soustraction du taux sans risque dans l'appel Sharpe précis
(indice direct : le Sharpe reste **identique à ×3 de levier**, alors qu'un excess-Sharpe correct
devrait légèrement bouger quand seul le rendement est levé et pas le RF).

**(2) Part swap vs part signal.** Sur notre reproduction (config défaut du code, 7 paires
majeures, fenêtre 2018-2024, coût FTMO retail 2,48 bps RT, swap réaliste avec haircut 0,85) : le
P&L net final se décompose en **prix (après coût) 55,5 %** / **swap 44,5 %** — swap non
majoritaire au sens strict du critère pré-enregistré (>50 %), mais **le deuxième contributeur en
importance et le seul qui ne rétrécit pas avec le coût** : sa part passe de 25 % (sans coût) à 29 %
(Eightcap Raw) à 44,5 % (FTMO retail) à mesure que le coût d'exécution érode la jambe prix. Par
paire, la confirmation la plus nette vient de **USDJPY** (le swap seul vaut 150 % du résultat net —
le prix a en réalité PERDU de l'argent sur cette paire, sauvé par le swap) et **USDCHF** (swap =
71 % du net) — exactement les deux paires que l'auteur cite lui-même verbatim comme portant
l'essentiel de la performance à cause de leur swap.

**(3) Ce qui reste.** Une fois le swap retiré et les jambes séparées, aucune ne dépasse le seuil
AMTP corrigé (|t| > 4,21 à n=1990) ; le bootstrap block CI95 du Sharpe net-de-swap-excès en fenêtre
2018-2024 est **[-0,35 ; 1,26]** — contient zéro. Le walk-forward 5 folds alterne signe (2 folds
positifs / 4, dont un −0,85) — sous le seuil WF>50 % de justesse. Sur l'historique complet
disponible (2007-2026), le Sharpe net-de-swap-excès à coût FTMO devient **négatif** (−0,21). Le
régime 2022-2024 — celui que l'auteur cite comme porteur — est, dans NOTRE reproduction (config
sans filtre TDI), le régime le plus mauvais (Sharpe −0,17) ; c'est 2018-2021 qui porte le résultat
positif de la fenêtre primaire. **Verdict : rien ne survit au retrait du carry, à la séparation des
jambes et à l'AMTP — la config par défaut du code, isolée de tout filtre TDI, n'a pas d'edge
mécanique two-sided démontrable ; ce qui reste dans la fenêtre citée par l'auteur est explicable
par un régime de change ponctuel (hausse des taux USD 2022-2024), pas par un signal robuste.**

---

## 1. Ce que le code livre réellement (rappel, détail dans SPEC_DEDALE.md)

Le mécanisme central, câblé en dur, ligne 777/789 de `DédaleFormation.mq5` :
```
if(!IS_NEGSWAP_ALLOWED && swap_long <= 0)  return false;   // refus d'achat si swap négatif
if(!IS_NEGSWAP_ALLOWED && swap_short <= 0) return false;   // refus de vente si swap négatif
```
`IS_NEGSWAP_ALLOWED = false` par défaut. L'auteur le confirme et le revendique lui-même dans le
transcript (Vidéo 6) : *« pour ma stratégie qui a fait ma carrière […] on va faire […] si [le
swap] est inférieur ou égal à zéro donc si on ne gagne pas d'intérêt et bien on ne veut pas
prendre de trade »*. Ce n'est donc pas un sous-produit accidentel du swap positif observé au
backtest : c'est la condition d'entrée elle-même. Les 15 booléens TDI (filtre technique) sont
**tous à `false` par défaut dans le code livré**, et **aucune des deux sources ne révèle la
configuration technique réellement utilisée** pour le chiffre cité (648 trades). Conformément au
mandat, la config A (tous les TDI à false = défaut de code) est retenue comme test primaire,
entièrement déterminée et sans paramètre inventé — voir §4 SPEC_DEDALE.md pour la justification
complète et la config B (démo H4-cross) en sensibilité.

**Conséquence pour la lecture de ce rapport** : notre reproduction n'est PAS un test de sa
stratégie réelle exacte (celle-ci reste non-identifiée dans les sources fournies) — c'est un test
du **squelette carry + pivot** sur lequel son filtre technique (quel qu'il soit) vient se
superposer. Le squelette seul trade **~294 fois/an sur seulement 7 paires** (vs ~100/an sur
« toutes les paires » chez lui) — une fréquence par instrument nettement plus élevée que la
sienne, cohérent avec l'absence totale de filtre technique dans la config A. Le win rate de notre
reproduction (51,7 % en fenêtre primaire) est aussi très inférieur au 63,58 % revendiqué — encore
une fois attendu : un filtre technique sélectif (TDI, quel qu'il soit) devrait mécaniquement
augmenter le win rate en écartant les entrées de moins bonne qualité. Ces deux écarts ne réfutent
pas ses chiffres : ils délimitent honnêtement ce que la config A peut et ne peut pas dire de son
système réel.

## 2. Incohérence n°1 — le Sharpe ne colle pas à ses propres chiffres

| Grandeur | Valeur |
|---|---|
| Rendement absolu | +60,33 % |
| Durée exacte (2018-01-05 → 2024-07-29) | 6,5658 ans |
| CAGR | 7,46 %/an |
| Volatilité annuelle déclarée | 10,91 % |
| RF moyen réel sur la fenêtre (DTB3, mesuré) | 2,21 %/an |
| **Sharpe gross (CAGR/vol)** | **0,68** |
| **Sharpe excess-RF (CAGR-RF)/vol** | **0,48** |
| Sharpe revendiqué | 1,56 (rendu « 156 »/« 15,6 » par endroits — cohérent avec un artefact
  de transcription ASR de « un virgule cinquante-six », pas une preuve d'une autre valeur) |
| **Écart** | **2,3× (gross) / 3,2× (excès)** |

**Mécanisme dominant (L47)** : 648 trades / 6,5658 ans = **98,7 trades/an**. Si le Sharpe a été
calculé sur une série indexée par trade en utilisant l'annualisation par défaut d'un outil comme
quantstats (`periods=252`, conçu pour des séries daily) au lieu de √98,7, le facteur de gonflement
attendu est **√(252/98,7) = 1,60** — soit **~70 % de l'écart total de 2,3×**.

**Piste secondaire (excès de RF)** : au test de levier ×3 qu'il montre lui-même (mêmes trades,
même période, risque 3 %/position), le rendement absolu passe à +181 % et l'Alpha à 162 %, mais
il rapporte *« le Sharpe est le même, c'est 15,6 »*. Or un Sharpe correctement calculé en excès
d'un taux sans risque non levé **doit** légèrement bouger sous un levier appliqué au seul
rendement de la stratégie (le ratio rendement-excès/vol croît un peu plus vite que
proportionnellement). Une invariance parfaite du Sharpe au levier est la signature d'un calcul
sur rendement **brut, RF non soustrait** dans cet appel précis — ce qui est cohérent avec le fait
que l'Alpha (49,54 % en fenêtre non-levée) est, lui, explicitement RF-ajusté ailleurs dans la même
vidéo : deux fonctions distinctes de la bibliothèque de stats, deux conventions différentes,
c'est le schéma d'erreur exact que le toolkit méthodologique de ce dépôt liste comme correctif
n°1/n°2 obligatoire (« 5 correctifs de script obligatoires »). Nous ne pouvons pas confirmer ce
second mécanisme avec certitude sans le code source de son analyse (nous n'avons que le
transcript) — il est rapporté comme **indice cohérent**, pas comme fait établi, et il n'est pas
nécessaire pour expliquer la majorité de l'écart : L47 seul explique déjà l'essentiel.

**Ce qui n'explique PAS l'écart** : il n'y a aucune preuve d'optimisation formelle du signal (voir
§5 SPEC_DEDALE.md — l'auteur affirme explicitement ne pas avoir optimisé, deux fois, en donnant sa
raison : SL/TP fixes sur pivots, "rien à optimiser"). Le PSR qu'il cite (98,97 %) ne corrige de
toute façon PAS le multiple testing (c'est la distinction PSR/DSR de Bailey-López de Prado 2014) —
mais dans ce cas précis, il n'y a pas non plus de preuve d'un grid-search caché à corriger : le
problème est un bug d'annualisation/RF, pas une inflation par sélection.

## 3. Incohérence n°2 — la part de carry dans le P&L

### 3.1 Ce que l'auteur dit lui-même (avant même notre reproduction)
Dans une section du même document où il isole une paire perdante (EURGBP, Sharpe 0,87, 6 %/an) —
« par honnêteté je n'ai pas enlevé les symboles qui perdaient » — il ajoute, sur la performance
d'ensemble : *« notre rendement total, l'essentiel des rendements de la stratégie sont faits que
sur certaines paires, comme par exemple dollar yen, comme par exemple euro yen, parce qu'elles
ont beaucoup de swap »* (`Backtest brieuc.md`, offset ~55051). C'est une **admission directe et
non sollicitée** que le P&L global est porté par un petit nombre de paires à fort swap, avant
même qu'on ait mesuré quoi que ce soit.

### 3.2 Notre décomposition (config A, 7 paires, fenêtre 2018-2024, coût FTMO 2,48 bps RT, swap
réaliste haircut 0,85)

| Composante | Somme (unités de risque, cumulée) | Part du P&L net final |
|---|---|---|
| Prix brut (gross) | +1,521 | — |
| Coût d'exécution | −0,895 | — |
| Swap | +0,502 | **44,5 %** |
| **Net final** | **+1,128** | 100 % |

Sensibilité au barème de coût — la part du swap **croît** quand le coût monte (le coût ronge la
jambe prix beaucoup plus vite que la jambe swap, qui s'accumule indépendamment du résultat du
trade) :

| Coût | Part swap du net final |
|---|---|
| 0 bps (gross) | 24,8 % |
| Eightcap Raw (0,75 bps RT) | 28,7 % |
| FTMO retail (2,48 bps RT) | **44,5 %** |

Décomposition par paire (fenêtre primaire, coût FTMO) — confirme directement sa citation :

| Paire | Prix (gross) | Swap | Coût | Net | Swap/Net |
|---|---|---|---|---|---|
| EURUSD | +0,576 | +0,129 | −0,131 | +0,575 | 22,5 % |
| GBPUSD | −0,149 | +0,034 | −0,176 | **−0,292** | (paire perdante conservée) |
| **USDJPY** | +0,082 | +0,107 | −0,117 | +0,071 | **150,6 %** (le prix a perdu, le swap sauve) |
| AUDUSD | +0,424 | +0,023 | −0,079 | +0,368 | 6,1 % |
| USDCAD | +0,431 | +0,028 | −0,173 | +0,286 | 9,6 % |
| **USDCHF** | +0,202 | +0,163 | −0,136 | +0,229 | **71,3 %** |
| NZDUSD | −0,045 | +0,019 | −0,083 | **−0,109** | (paire perdante conservée) |

USDJPY et USDCHF — les deux paires à plus fort différentiel de taux USD sur la période — sont
exactement les deux cas où le swap porte la quasi-totalité (ou plus) du résultat net, en accord
mécanique avec sa propre citation sur « dollar yen ». GBPUSD et NZDUSD restent nets négatifs — la
config A ne les « sauve » pas, cohérent avec « garder les paires perdantes ».

**Verdict H2** : swap = 44,5 % du net dans le scénario de coût réaliste retenu — sous le seuil de
50 % pré-enregistré, donc **non confirmé au sens strict**, mais c'est le deuxième contributeur, il
est le seul robuste au coût, et il rend positifs des résultats qui seraient négatifs sans lui
(USDJPY). Au barème de coût brut (swap sans haircut), la part passe à ~48,6 %, à la limite du
seuil. **Le verdict le plus honnête : le carry n'est pas la totalité de l'edge, mais il en est la
part qui SURVIT le mieux au coût réel — exactement le mécanisme que le dépôt a déjà documenté sur
d'autres familles (L28, L33, L36) : la structure de coût décide ce qui reste, et ce qui reste est
disproportionnellement du carry.**

## 4. Ce qui reste — jambes séparées, régime découpé, AMTP

### 4.1 Two-sided (L25)
| Fenêtre | Jambe | n | Sharpe | HAC t |
|---|---|---|---|---|
| 2018-2024 | buy | 1029 | 0,27 | 0,49 |
| 2018-2024 | sell | 897 | 0,79 | 1,29 |
| 2007-2026 | buy | 3571 | −0,39 | **−1,22** |
| 2007-2026 | sell | 1904 | 0,11 | 0,24 |

Aucune jambe, dans aucune fenêtre, ne dépasse le seuil conventionnel |t|>2,5 — a fortiori pas le
seuil AMTP corrigé (§4.4). La jambe « buy » devient carrément négative sur l'historique complet.
Pas de two-sided edge démontrable.

### 4.2 Régime 2022-2024 vs reste
| Fenêtre | Régime | n | Sharpe | HAC t |
|---|---|---|---|---|
| 2018-2024 | 2022-2024 | 896 | **−0,17** | −0,23 |
| 2018-2024 | reste (2018-2021 + fin 2024) | 1030 | **+1,00** | 1,78 |
| 2007-2026 | 2022-2024 | 1043 | −0,15 | −0,22 |
| 2007-2026 | reste | 4432 | −0,20 | −0,73 |

**Résultat inattendu et important** : dans NOTRE reproduction (config A, sans filtre TDI), c'est
2022-2024 — la période que l'auteur cite lui-même comme porteuse — qui est la PIRE, et 2018-2021
qui porte tout le résultat positif de la fenêtre primaire. Interprétation la plus probable : un
système bandes-de-pivot 1:1 sans filtre de tendance est structurellement vulnérable à un régime de
trend fort et soutenu (la remontée du dollar 2022-2023, le unwind carry JPY 2024) — le prix
traverse la bande avant de revenir, ce qui déclenche le SL avant le TP. Un filtre technique (TDI
trend/angle, non identifié dans nos sources) pourrait en théorie éviter ce piège — c'est une
hypothèse plausible pour réconcilier son vécu (bon en 2022-2024) avec notre mesure (mauvais en
2022-2024 SANS filtre), mais nous n'avons aucune preuve documentaire de la configuration réelle
pour la trancher. **Ce que cette mesure établit solidement : le squelette carry+pivot seul
n'explique PAS la performance qu'il attribue à cette période — s'il y a un edge en 2022-2024, il
vient nécessairement du filtre technique non-documenté, pas du mécanisme carry+pivot de base.**

### 4.3 Walk-forward (5 folds expanding)
| Fenêtre | Folds positifs | Détail |
|---|---|---|
| 2018-2024 | 2/4 | 0,60 / 1,22 / **−0,85** / −0,01 |
| 2007-2026 | 3/4 | 0,04 / **−1,80** / 0,87 / 0,58 |

WF 2018-2024 = 50 %, sous le seuil RESEARCH_PASS (WF>50 %) de justesse. WF étendu = 75 % mais avec
un fold profondément négatif (−1,80) — signe d'instabilité régime-dépendante, pas d'edge stable.

### 4.4 Bootstrap, DSR, AMTP
- **Block-bootstrap CI95 du Sharpe** (fenêtre primaire, coût FTMO, swap réaliste, excès RF) :
  **[−0,35 ; 1,26]** — contient zéro. Fenêtre étendue : **[−0,78 ; 0,29]** — contient zéro et
  penche négatif.
- **DSR** (nos propres degrés de liberté : config A + config B = n_trials=2) : 0,828 en fenêtre
  primaire — sous le seuil conventionnel 0,95.
- **DSR au n_tests cumulé du dépôt** (n=1990, mandat point 8) : **0,024** — collapse presque total
  ; à ce niveau de charge de test cumulée, quasiment aucun candidat individuel ne passe sans
  edge écrasant.
- **Seuil AMTP Šidák à n=1990** : α_corrigé = 2,58×10⁻⁵ ⇒ **|t| requis > 4,21**. Le HAC t le plus
  élevé observé dans toute cette étude (toutes fenêtres, tous scénarios) est **2,26** (fenêtre
  primaire, coût nul, swap brut, NET_SWAP — le scénario le plus favorable possible). **Rien ne
  franchit le seuil AMTP.**
- **Placebo direction aléatoire** (même cadence, même mécanique pivot/sizing, direction non
  filtrée par le swap) : Sharpe correct **−0,37** (primaire) / **−0,51** (étendu), HAC t −0,96 /
  −2,21. Nettement pire que la direction pilotée par le swap — **le choix de direction ajoute
  une vraie valeur par rapport au hasard**, ce n'est pas un artefact de fréquence ou de sizing.
  Mais combiné au §4.2 (2022-2024 négatif) et à l'historique étendu négatif, l'interprétation la
  plus prudente est que cette valeur reflète un **régime de change ponctuel** (dollar haussier
  2022-2024 récompensant systématiquement le côté long-USD/carry-USD) plutôt qu'une prime de
  risque persistante — exactement le schéma que le toolkit méthodologique du dépôt met en garde
  (« FX carry regime-dependence : 2005-2007 pre-GFC drives all G10 carry IC »).

## 5. Ce qui est solide — à mettre au crédit de l'auteur

- **Il modélise ses coûts, et ses coûts sont NETS POSITIFS** — un choix rare et honnête pour une
  formation grand public ; la plupart des vendeurs d'EA ignorent le swap ou l'omettent par excès
  de prudence dans le mauvais sens (ici il assume correctement que le swap compte, dans les DEUX
  sens, et le filtre explicitement).
- **Il garde les paires perdantes** — confirmé indépendamment par notre reproduction (GBPUSD et
  NZDUSD nets négatifs dans notre config A aussi) ; pas de survivorship bias de sélection de
  paires détecté.
- **Il déclare explicitement ne pas avoir optimisé**, et donne une raison technique cohérente
  (SL/TP fixes sur niveaux de prix) — une discipline anti-surapprentissage rare, même si le choix
  informel des filtres TDI reste un angle mort non documenté (§5 SPEC_DEDALE.md).
- **Il utilise le PSR**, un raffinement que peu de formations grand public introduisent, même s'il
  répond à une question différente du multiple-testing (non-normalité, pas sélection).
- **Il reconnaît lui-même**, dans une section moins mise en avant que le chiffre-titre, que la
  stratégie *« dépend beaucoup des conditions du marché »*, qu'elle *« n'a pas un pouvoir prédictif
  absolument phénoménal »*, et qu'elle fait *« 6 % par an sans levier, donc c'est pas ouf ouf »* —
  une estimation de CAGR très proche de notre calcul indépendant (7,46 %), et une évaluation bien
  plus modeste que le chiffre-titre Sharpe 1,56 mis en avant ailleurs dans la même vidéo. Ce
  décalage interne (lucidité dans le corps du texte, chiffre optimiste dans le titre) est cohérent
  avec un bug d'outil non détecté plutôt qu'avec une intention de tromper.
- **Il déclare avoir tradé en semi-automatique depuis 2022 avec plus de drawdown qu'au backtest** —
  une transparence sur l'écart backtest/live que peu de formations offrent.

## 6. Limitations de cette reproduction (déclarées, pas cachées)

- Univers : 7 paires majeures USD, pas « toutes les paires » (probablement ~25-30 chez son
  courtier) — sous-échantillon, pas réplication complète.
- Config A ne contient aucun filtre TDI — c'est un choix défendable (défaut de code, zéro
  paramètre inventé) mais ce n'est PAS son système exact, dont la config reste non documentée
  dans les deux sources disponibles.
- Swap modélisé par proxy de différentiel de taux directeur (FRED, mensuel, ffill), pas les swaps
  facturés réels de son courtier — approximation déclarée en amont (PREREGISTRATION §3).
- Semaine de pivot ancrée UTC calendaire, pas l'heure serveur réelle de son courtier (L52) —
  approximation déclarée.
- Détection SL/TP à la granularité H1, pas tick — peut manquer des touches infra-horaires
  ponctuelles, sans biais directionnel attendu.
- Coût de spread réel non modélisé (colonne `spread` du dépôt inutilisable, remplacée par des
  barèmes fixes déclarés par le mandat).

## 7. Benchmark honnête
CAGR de sa stratégie sur sa fenêtre : 7,46 %/an, contre un S&P 500 qui a fait environ 13 %/an sur
2018-2024 (chiffre reconnu par le mandat ; l'auteur lui-même, dans une séquence sur une autre
paire, calcule un « alpha » négatif de −7 % dans un des sous-tests où il compare explicitement à
un taux sans risque de 1,5 %, avec un commentaire *« on a sous-performé le benchmark »* — donc il
a lui-même rencontré, sur au moins un sous-test, un cas où sa propre stratégie ne bat pas un
placement plus simple). Sur la fenêtre et l'univers testés ici, un investisseur buy-and-hold
actions aurait fait sensiblement mieux, en absolu, qu'un trader Dédale actif quotidiennement sur
le carry FX — à mettre en regard du temps et du risque opérationnel (compte propfirm/CFD, gestion
active) que la stratégie demande.

## 8. Multiple testing (mandat point 8)
n_tests cumulé avant cette hypothèse : 1989 (ledger canonique). Cette étude ajoute **1** test
(l'hypothèse « Dédale carry+pivot » — les sous-analyses H1/H2/H3 sont des angles de reporting du
même test, pas des essais indépendants, cf. PREREGISTRATION §4). **n cumulé après cette
hypothèse : 1990.** Seuil Šidák à n=1990 : α_corrigé = 2,58×10⁻⁵, **|t| requis > 4,21**. Aucun
résultat de cette étude ne s'en approche (max observé 2,26, scénario le plus favorable). **Cette
hypothèse est classée : signal non établi — kill mécanique probable pour le squelette carry+pivot
nu, résidu non tranchable pour la config technique réelle (non documentée).**
