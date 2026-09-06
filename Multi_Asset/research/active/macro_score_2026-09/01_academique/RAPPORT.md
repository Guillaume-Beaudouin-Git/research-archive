# État de l'art académique — prédictibilité macro des rendements d'actifs

**Statut** : rédaction en cours (au fil de l'eau). **Aucune donnée téléchargée, aucun backtest — revue de littérature uniquement.**
**Date** : 2026-09-06. **Auteur** : Claude (session recherche), pour compte de G. Beaudouin.

## Objectif et méthode de lecture

Ce rapport n'est PAS une liste de papiers à citer dans un mémoire. C'est un audit de faisabilité :
pour chaque courant, la question posée est **« si je réplique ça avec des données que je peux
obtenir, combien de PARIS INDÉPENDANTS par an cela me donne-t-il, et à quel Sharpe/IC net de
coûts, mesuré HORS de l'échantillon original de publication ? »**. Le defaut du modèle de scoring
macro amateur déjà audité était de confondre observations (souvent quotidiennes) et paris
indépendants dans la loi de Grinold — cette confusion est le fil conducteur de la critique
ci-dessous, courant par courant.

Convention de notation : **PEER-REVIEWED** (revue à comité de lecture) / **WORKING PAPER** (NBER,
SSRN, non arbitré ou en cours d'arbitrage) / **WHITEPAPER GÉRANT** (AQR, Bridgewater, etc. — à
lire avec un biais de vente et souvent un biais de survie/hindsight explicitement reconnu par les
auteurs eux-mêmes).

---

## 1. Macro momentum / macro trend

### 1.1 Brooks (AQR), *A Half Century of Macro Momentum*, whitepaper, août 2017

**Statut** : **WHITEPAPER GÉRANT**, non publié dans une revue à comité de lecture. Auteur : Jordan
Brooks, Managing Director AQR (affilié à un gérant qui vend ce type de stratégie — conflit
d'intérêt explicite, à pondérer). Remerciements à Cliff Asness, Antti Ilmanen — écosystème AQR
pur.

**Échantillon d'origine** : janvier 1970 – décembre 2016 (47 ans). Univers : indices actions
globaux, obligations souveraines globales (maturité 10 ans synthétique), devises globales,
taux d'intérêt globaux (3 mois). Dates de début variables par classe d'actif (cf. Appendix A du
papier, non entièrement consultée ici).

**Construction du signal (4 thèmes macro)** :
- **Cycle économique** : combinaison 50/50 de la variation sur 1 an des prévisions de croissance
  du PIB réel et de la variation sur 1 an des prévisions d'inflation CPI (consensus).
- **Commerce international** : variation sur 1 an du taux de change spot vs panier pondéré par les
  exportations.
- **Politique monétaire** : variation sur 1 an du taux à 2 ans.
- **Sentiment de risque** : rendement du marché actions sur 1 an.

Portefeuille = long/short et directionnel sur chaque thème × chaque classe d'actif (32
sous-portefeuilles agrégés en poids égal, chacun scalé à 10% de vol annualisée cible).

**Résultat central chiffré** :
- Sharpe **1.2** plein échantillon (1970-2016), rendement excess annualisé **13.0%**, vol **10.7%**.
- Corrélation aux actions US **-0.22**, aux obligations US 10 ans **+0.03**.
- Sharpe par classe d'actif : actions 0.7, devises 0.6, obligations 0.5, taux d'intérêt (futures) 0.8.
- Sharpe par thème : cycle économique 0.5, commerce international 0.6, politique monétaire 0.9,
  sentiment de risque 0.7.
- « Smile » vs actions : sur les 10 pires trimestres actions depuis 1970 (actions moyenne -19.9%),
  macro momentum rend en moyenne **+13.7%**. Sur les 10 épisodes de hausse extrême des taux
  réels, macro momentum rend en moyenne **+12.0%/an** vs -14.2% pour les obligations US 10 ans.

**⚠ DÉCROISSANCE PAR DÉCENNIE — signal de décroissance hors échantillon récent, à l'intérieur même
du papier** :
| Décennie | Sharpe |
|---|---|
| 1970-1979 | 0.9 |
| 1980-1989 | 1.7 |
| 1990-1999 | 1.4 |
| 2000-2009 | 1.3 |
| **2010-2016** | **0.7** |

Le papier ne discute pas explicitement cette décroissance comme un problème (il la présente comme
« consistante »), mais **le Sharpe de la dernière décennie (0.7) est presque exactement le Sharpe
plein-échantillon d'un facteur unique (cycle économique, 0.5) et bien en dessous du 1.2 headline** —
c'est un pattern classique de dégradation post-crowding ou de sur-ajustement in-sample. Aucune
donnée post-2016 n'a été trouvée dans cette recherche (le papier date de 2017 et n'a pas été mis à
jour publiquement à ma connaissance — **non trouvé**).

**Note explicite des auteurs (à prendre au sérieux)** : *« All returns throughout the paper are
hypothetical, gross of transaction costs and fees. Even after adjusting for transaction costs and
fees, backtest returns (and Sharpe ratios) are likely overstated, [...] due to unavoidable
hindsight bias. »* — l'auteur reconnaît lui-même le biais. Coûts de transaction NON déduits.

**Fréquence de décision réelle — LE POINT CRITIQUE** : les 4 signaux sont des **variations sur 1
an** de séries macro (prévisions de croissance/inflation consensus, taux 2 ans, FX vs panier). Les
prévisions consensus de croissance/inflation ne sont típicamente révisées qu'à fréquence mensuelle
au mieux (souvent moins, les enquêtes consensus type Consensus Economics sont mensuelles), et une
variation sur 1 an est par construction une série à forte autocorrélation (chevauchement de 11/12
mois d'un mois sur l'autre). **Même si le portefeuille est rebalancé mensuellement, le nombre de
PARIS INDÉPENDANTS par an et par thème est de l'ordre de 1 à 4** (l'horizon de la variation étant
annuel, un signal ne se renouvelle vraiment que quand l'info sous-jacente change, soit
approximativement à fréquence trimestrielle pour les enquêtes de croissance/inflation). Avec 4
thèmes × 4 classes d'actifs partiellement décorrélés (corrélation moyenne par paires **0.1**, citée
dans le papier), le nombre efficace de paris indépendants du portefeuille agrégé est probablement
de l'ordre de **10-20/an**, pas de 32×12=384. C'est un ordre de grandeur, pas un chiffre du papier
— **non trouvé** de calcul explicite de breadth effective dans le document, ce qui est en soi un
manque de rigueur du whitepaper (aucune démonstration IJR/Grinold n'y figure).

**Réplicabilité gratuite** : prévisions consensus growth/inflation = données payantes
(Consensus Economics, Bloomberg). Alternative gratuite dégradée : utiliser les surprises réalisées
CPI/PIB (FRED, gratuit) au lieu des révisions de prévisions consensus — proxy imparfait. Taux 2 ans
et FX spot = gratuits (FRED, yfinance). **Le signal « cycle économique » n'est donc PAS
réplicable à l'identique sans données payantes** ; le signal « politique monétaire » (taux 2 ans)
et « commerce international » (FX) le sont.

**Verdict provisoire** : résultat intéressant comme *proof of concept économique* (macro momentum
existe, diversifie un 60/40), mais **fragile pour usage direct** : (i) whitepaper non arbitré et
auteur juge et partie, (ii) décroissance de Sharpe manifeste sur la dernière décennie observée
dans le papier lui-même, (iii) gross-of-costs explicitement reconnu comme optimiste, (iv) breadth
effective non quantifiée et probablement basse (dizaine de paris/an, pas des centaines).

---

## 3. Carry comme phénomène macro

### 3.1 Koijen, Moskowitz, Pedersen, Vrugt, *Carry*, NBER WP 19325 (août 2013) → **Journal of Financial Economics**, vol. 127, no. 2, 2018, pp. 197-225

**Statut** : **PEER-REVIEWED** (JFE 2018 ; version NBER WP antérieure non arbitrée mais le texte
final l'est). Co-auteurs affiliés AQR (Moskowitz, Pedersen) — même réserve de conflit d'intérêt
que ci-dessus, mais publication dans une revue de premier rang atténue le risque de p-hacking non
détecté (arbitrage par les rapporteurs).

**Définition centrale** : le carry d'un actif est son rendement attendu **si son prix ne change
pas** : `rendement = carry + appréciation de prix attendue + choc de prix inattendu`. Le carry est
observable ex ante, sans modèle de pricing — c'est un caractère mesurable directement à partir des
prix (spread de taux pour le FX, pente de la courbe pour les obligations, rendement du dividende
pour les actions, convenience yield pour les commodités).

**Univers** : **9 classes d'actifs** — devises (contrats forward 1 mois), actions globales
(futures synthétiques 1 mois), obligations souveraines globales (futures synthétiques via taux
zéro-coupon), commodités (pente de la courbe futures), Treasuries US (cross-maturité), crédit US,
options sur indice actions (calls et puts, cross-moneyness). *Non trouvé* dans les pages consultées :
dates de début précises par classe d'actif (renvoyé à l'Appendix A, non lu en détail) — à
vérifier avant citation d'un chiffre de durée d'échantillon précis.

**Résultat central chiffré** :
- Portefeuille long-short carry **intra-classe d'actif** (long haut carry / short bas carry, market
  neutral par classe) : Sharpe annualisé moyen **0.7** à travers les 9 classes.
- Portefeuille **diversifié à travers les 9 classes** (le vrai portefeuille cross-asset carry) :
  Sharpe **1.1** — gain de diversification net (corrélations pairwise faibles entre carry
  strategies des différentes classes, sauf pendant les récessions).
- Coefficient de régression prédictive rendement futur ~ carry : **≈ 1 (non significativement
  différent de 1)** pour la plupart des classes → rejette l'Uncovered Interest Parity et
  l'Expectations Hypothesis en général (le carry n'est PAS compensé par une appréciation de prix
  anticipée égale et opposée, sauf pour commodités et options où le coefficient est **< 1** — le
  carry y prédit une appréciation de prix future négative, partielle compensation).
- **Décomposition macro directe** : les 3 pires drawdowns du carry diversifié global coïncident
  avec des récessions globales — août 1972-sept. 1975, mars 1980-juin 1982, **août 2008-févr.
  2009**. Le carry expose donc à un facteur de risque macro de récession/liquidité globale — ce
  n'est PAS un free lunch, c'est une prime de risque business-cycle, cohérent avec le narratif
  "carry = vendre de l'assurance contre les états mauvais du monde".
- Skewness du portefeuille diversifié cross-asset ≈ 0 (contrairement au carry FX seul, fortement
  skew négatif) — un des résultats les plus cités du papier : diversifier le carry across asset
  classes réduit substantiellement le risque de queue par rapport au carry FX isolé.

**Ce qui a survécu / ce qui est mort depuis publication (2013 WP / 2018 JFE)** : **non trouvé**
dans cette recherche de suivi systématique post-2018 du Sharpe réalisé du carry cross-asset
KMPV lui-même (pas de réplication publique identifiée avec des chiffres). Ce qui EST bien
documenté dans la littérature adjacente et déjà dans le registre L de ce dépôt (L28, L32, L32b,
L36, L55) : le carry FX et le carry commodities souffrent spécifiquement, en exécution CFD retail,
d'un doublement du markup de financement (swap asymétrique) qui détruit la prime pour un horizon de
rotation en semaines — **ce n'est pas un échec du signal KMPV lui-même (qui reste institutionnel,
futures, coût ~quasi-nul), c'est un échec de VÉHICULE quand on essaie de le répliquer en CFD retail
ou en funding perp crypto** (cf. Strategy B du présent dépôt — déjà caduque pour cette raison
précise). Le signal académique carry-cross-asset n'est donc probablement pas mort, mais son
**exécution low-cost (futures institutionnels)** est une condition nécessaire, jamais suffisante en
elle-même.

**Fréquence de décision réelle** : rebalancement mensuel dans la plupart des implémentations de ce
type (données forward 1 mois pour le FX, futures synthétiques 1 mois pour actions/obligations).
**Contrairement au macro momentum (score 1.), le carry cross-sectionnel a une vraie fréquence de
pari élevée** : c'est un tri cross-sectionnel mensuel sur N instruments dans chaque classe d'actif,
donc le nombre de paris indépendants par an se rapproche de **N_classes × 12** si les instruments
dans chaque classe sont suffisamment nombreux et le tri suffisamment renouvelé (le carry FX/taux
change lentement — corrélation mois-sur-mois élevée — donc l'estimation naïve N×12 est SURESTIMÉE;
le papier documente lui-même une composante "statique" du carry qui domine dans plusieurs classes
— "carry fluctuates... but the passive/static component contributes about half the returns in
Treasuries, currencies, credit and commodities" — ce qui, en langage Grinold, veut dire qu'une
bonne partie du portefeuille N'EST PAS un nouveau pari indépendant chaque mois, c'est une exposition
statique long-biaisée à un facteur qui bouge lentement). **Estimation qualitative : plusieurs
dizaines à ~100 paris quasi-indépendants par an pour le carry cross-asset diversifié — nettement
plus que le macro momentum ci-dessus, mais nettement moins que le nombre brut d'instruments ×
fréquence de rebalancement ne le suggérerait.**

**Réplicabilité gratuite** : carry FX (spread de taux, FRED/yfinance forward points), carry
obligataire (pente de courbe, gratuit), carry actions (dividend yield forward — nécessite futures
dividend data, **partiellement payant**), carry commodités (pente de la courbe futures, calculable
depuis données futures gratuites type yfinance/Quandl legacy). Crédit et options : nécessitent des
données de spread/vol surface **payantes**. **Verdict : 4 des 9 classes (FX, obligations, taux,
commodités) sont réplicables à coût quasi nul ; les 5 autres (equity carry forward-looking, US
Treasuries cross-maturité fine, crédit, options) demandent des données propriétaires ou un travail
de construction significatif.**

**Fragilité à signaler** : c'est le SEUL résultat de ce rapport avec une revue à comité de lecture
de premier rang (JFE) ET une taille d'échantillon multi-décennie ET une réplication
cross-asset — donc le résultat le MOINS fragile de la liste jusqu'ici. Réserve : les auteurs sont
juges et parties (gérant AQR) même si publié en peer-review, et le lien carry↔macro (récessions)
signifie que le Sharpe historique inclut une compensation pour un risque de queue rare mais sévère
qui peut ne pas s'être encore matérialisé assez souvent dans l'échantillon pour être bien mesuré
(les 3 drawdowns cités couvrent ~6 ans sur ~40 ans d'échantillon — MECHANICALLY peu d'événements de
queue, gros risque de sous-estimation du vrai risque de queue, classique pour toute stratégie de
vente d'assurance).

---

## 2. Cycle économique et allocation — le régime prédit-il la MOYENNE ou seulement la VARIANCE ?

C'est la question la plus directement utile de tout ce rapport pour ce dépôt : on a déjà falsifié
(cf. `_meta` L54, `regime_overlay_ftmo_2026-07`) un overlay de régime qui prédisait bien la
variance (vol stress 9.8% vs 4.2%) mais PAS la moyenne dans le même sens, ce qui a détruit toute sa
valeur (le book gagnait justement sur les jours de haute vol). La littérature académique confirme
que ce piège est un résultat GÉNÉRIQUE, pas une anomalie du book FTMO.

### 2.1 Ang & Timmermann, *Regime Changes and Financial Markets*, **PEER-REVIEWED**, Annual Review
of Financial Economics, vol. 4, 2012, pp. 313-337

Survey de référence, non un test empirique isolé — c'est voulu : ce qui compte ici est le
consensus de champ, pas un chiffre unique falsifiable. Résultat théorique central, démontré
formellement (éq. 5-6 du papier, modèle à 2 régimes) : **une différence de MOYENNE entre régimes
(`μ₀ - μ₁`) génère MÉCANIQUEMENT un excès de variance, de skew et de kurtosis** — la variance
inconditionnelle d'un mélange de régimes n'est PAS la moyenne pondérée des variances intra-régime,
elle inclut un terme `π₀(1-π₀)(μ₀-μ₁)²` qui vient uniquement de l'écart de moyenne. **Implication
directe et non-triviale pour notre usage** : un signal peut sembler « prédire la variance » de
façon totalement mécanique et sans rien prédire d'utile, simplement parce que le régime a des
moyennes différentes — et RÉCIPROQUEMENT, un régime peut avoir un excès de variance apparent qui ne
vient QUE d'un excès de switching-risk (risque de changer de régime), sans que la moyenne ne soit
elle-même exploitable en trading (car on ne connaît le régime qu'après coup, avec un `p_ii` de
persistance imparfait). Le papier montre aussi que les corrélations augmentent en régime bas
(effet asymétrique bien connu, Longin-Solnik 2001, Ang-Chen 2002) et que le nombre de régimes
« correct » n'est en général PAS identifiable par test statistique standard (les tests de rapport
de vraisemblance ne suivent pas une loi χ² asymptotique standard sous H0 — Davies 1977, Hansen
1992) : **en pratique le nombre de régimes est fixé arbitrairement (souvent 2), pas estimé.**

**Verdict** : la littérature académique de référence ne dit PAS que le régime prédit la moyenne EN
GÉNÉRAL — elle dit que régimes-moyenne et régimes-variance sont mathématiquement enchevêtrés, et
qu'il FAUT vérifier explicitement, pour chaque application, si le régime candidat prédit la
moyenne DANS LE MÊME SENS que la variance (exactement la correction que L54 a dû faire après coup
en interne). Aucun chiffre de Sharpe out-of-sample d'une stratégie de régime générique n'est
rapporté dans ce survey — **non trouvé** de méta-analyse chiffrée de la performance OOS des
stratégies d'allocation à changement de régime dans cette recherche (le champ reste
essentiellement descriptif/économétrique, pas un champ de stratégies validées).

### 2.2 Ilmanen, *Expected Returns: An Investor's Guide to Harvesting Market Rewards*, Wiley, 2011

**Statut** : livre destiné aux praticiens (AQR), pas un article à comité de lecture — synthèse de
la littérature académique, pas une contribution empirique originale nouvelle. **Non trouvé** dans
cette recherche : un chiffre précis, extrait du livre lui-même, quantifiant séparément l'effet
régime→moyenne vs régime→variance sur un univers d'actifs donné (le livre est structurel/narratif,
organisé autour des primes de risque — value, momentum, carry — plutôt qu'autour d'un test formel
mean-vs-variance). Le cadre "quadrant" croissance/inflation qui circule dans l'industrie (souvent
attribué à Ilmanen/AQR ou à Merrill Lynch "Investment Clock") n'a PAS de source académique à comité
de lecture identifiée dans cette recherche avec un chiffre d'effet net de coûts — c'est un outil
narratif de gérant, pas un résultat publié avec IC/t-stat. Cohérent avec la synthèse trouvée en
recherche généraliste (§ci-dessus) : le consensus qualitatif de l'industrie est que ces quadrants
« aident à comprendre la volatilité plutôt qu'à prévoir directement la moyenne » — exactement la
mise en garde que ce rapport doit signaler.

**Fréquence de décision implicite** : les régimes croissance/inflation typiques (goldilocks,
reflation, stagflation, ralentissement désinflationniste) sont mesurés sur des données macro
mensuelles/trimestrielles (PMI, CPI) et changent rarement — persistance typique de plusieurs
trimestres à plusieurs années selon Ang-Timmermann. **Un système de régime macro de ce type ne
génère PAS plus de 2 à 4 changements de régime « vrais » par an, souvent moins.** C'est un
overlay de sizing/exposition, pas une source de breadth — à ne jamais compter comme des paris
indépendants supplémentaires dans un calcul de Sharpe composite.

---

## 4. Prédictibilité par facteurs macro extraits (primes obligataires)

### 4.1 Cochrane & Piazzesi, *Bond Risk Premia*, **PEER-REVIEWED**, American Economic Review, vol.
95, no. 1, 2005, pp. 138-160

**Résultat central chiffré** : un facteur unique — combinaison linéaire « en tente » (tent-shaped)
des taux forward (1 à 5 ans) — prédit les rendements excès à un an des obligations US de maturité
1 à 5 ans avec un **R² allant jusqu'à 0.44**. Le facteur est contra-cyclique et prédit aussi les
rendements actions. Une composante importante du facteur n'est PAS expliquée par les mouvements de
niveau/pente/courbure standard de la structure par terme (donc pas juste "duration timing"
déguisé).

**Échantillon d'origine** : taux Treasury US, période longue (fin des années 1960 aux
années 2000 — **non trouvé** de dates exactes dans les pages consultées, à vérifier avant citation
précise dans un document externe).

**⚠ CRITIQUE OUT-OF-SAMPLE MAJEURE, essentielle à signaler** : Bauer & Hamilton, *Robust Bond Risk
Premia*, **PEER-REVIEWED**, Review of Financial Studies, vol. 31, no. 2, 2018, pp. 399-448. Les
auteurs montrent que **les tests statistiques standards utilisés dans Cochrane-Piazzesi (2005) ET
Ludvigson-Ng (2009, cf. 4.2) souffrent de distorsions sérieuses en petit échantillon** — en
particulier le fait de tester la significativité d'un facteur extrait par régression en 2 étapes
(component 4-5 des composantes principales des taux) gonfle artificiellement les t-stats. Avec une
procédure bootstrap robuste conçue spécifiquement pour tester l'hypothèse de "spanning", **la
preuve contre l'hypothèse nulle (les facteurs macro n'apportent rien de plus que niveau-pente-
courbure) est BEAUCOUP plus faible qu'il n'y paraît dans l'article original**, et les résultats de
Cochrane-Piazzesi et Ludvigson-Ng ne sont **PAS stables à travers différentes périodes
d'échantillon**. **C'est un résultat mort ou très affaibli hors échantillon au sens statistique
strict** — pas au sens où le R² in-sample de 0.44 est faux, mais au sens où la significativité
statistique qui justifiait de le traiter comme un vrai signal (et pas un artefact de petit
échantillon/data-mining sur composantes principales d'ordre élevé) ne survit pas à un test robuste.
**Ceci est exactement le type de résultat que ce dépôt doit refuser de citer sans le caveat.**

**Fréquence de décision** : rendements excès annuels prédits par les taux forward observés à un
instant donné — la fréquence naturelle d'implémentation est **mensuelle au mieux** (nouvelle
observation de taux forward chaque mois), mais l'horizon de la variable prédite est de 12 mois,
donc les observations successives se chevauchent massivement. **Le nombre de paris réellement
indépendants sur un historique de 40 ans est de l'ordre de 40 (annuel), pas de 480 (mensuel)** —
c'est un cas d'école exact du problème identifié dans le brief : confondre observations mensuelles
et paris indépendants sur un horizon de prédiction de 12 mois.

### 4.2 Ludvigson & Ng, *Macro Factors in Bond Risk Premia*, **PEER-REVIEWED**, Review of
Financial Studies, vol. 22, no. 12, 2009, pp. 5027-5067

**Résultat central chiffré** : des facteurs macro extraits par analyse en composantes principales
de plus de 130 séries macro US ajoutent **15 à 25 points de pourcentage de R² incrémental** au-delà
des facteurs de la seule courbe des taux (niveau/pente/courbure ou le facteur Cochrane-Piazzesi),
pour prédire les rendements excès futurs des obligations souveraines US. Les facteurs "réel" et
"inflation" ont un pouvoir prédictif significatif au-delà de ce que contiennent déjà les taux
forward et les spreads de taux.

**⚠ Même critique que ci-dessus** : Bauer & Hamilton (2018) montrent explicitement des problèmes
de stabilité des résultats de Ludvigson-Ng à travers différentes périodes d'échantillon, avec la
même distorsion de petit échantillon dans les tests de significativité en 2 étapes.

**Réplicabilité** : nécessite de construire un modèle à facteurs dynamiques sur ~130 séries macro
US mensuelles (proche des données FRED-MD, **gratuites** — le dataset FRED-MD de McCracken-Ng est
une réplication publique standard de ce type de dataset). **Réplicable gratuitement en principe**,
mais l'extraction de facteurs par ACP sur données macro publiées avec retard/révisions pose le
problème classique de look-ahead bias (retard de publication + révisions historiques des séries
FRED elles-mêmes) — non traité dans cette recherche, **à vérifier avant toute implémentation**
(utiliser ALFRED — vintages réels — et non FRED révisé).

**Fréquence de décision** : identique au 4.1 — signal mensuel, cible annuelle, chevauchement
massif. Nombre de paris indépendants de l'ordre de la dizaine par décennie pour un seul horizon de
prédiction (12 mois), pas plus.

### 4.3 Cieslak & Povala, *Expected Returns in Treasury Bonds*, **PEER-REVIEWED**, Review of
Financial Studies, vol. 28, no. 10, 2015, pp. 2859-2901

**Résultat central** : décomposition des taux Treasury nominaux en (a) anticipations d'inflation
« tendancielle » (trend inflation, moyenne mobile de long terme des surprises d'inflation passées)
et (b) cycle de taux d'intérêt propre à la maturité (variation orthogonale à l'inflation
anticipée). **L'inflation tendancielle explique plus de 80% de la variance inconditionnelle du
niveau des taux nominaux US depuis les années 1970** — la prime de risque elle-même ne contribue
que le moins à cette variance inconditionnelle, mais son effet se renforce avec la maturité. Le
facteur de prime de risque ainsi extrait **prédit les rendements excès obligataires en et hors
échantillon**, et absorbe (subsumes) le pouvoir prédictif du facteur Cochrane-Piazzesi construit à
partir des taux forward seuls. **Chiffre R² précis non trouvé** dans cette recherche — la revue
des sources disponibles confirme le mécanisme et la robustesse hors-échantillon revendiquée par les
auteurs mais pas le chiffre exact ; à vérifier dans le papier complet avant citation d'un R²
précis dans un document externe.

**Point fort méthodologique notable** : contrairement à 4.1/4.2, ce facteur est construit à partir
d'une décomposition économique explicite (tendance d'inflation, pas une composante principale
d'ordre élevé extraite mécaniquement), ce qui le rend a priori moins sujet à la critique
Bauer-Hamilton de sur-ajustement en petit échantillon sur des combinaisons linéaires à haute
dimension — mais **aucune réplication indépendante post-2015 avec test robuste n'a été trouvée
dans cette recherche** pour confirmer que ce facteur spécifique résiste au même type de test
bootstrap que Bauer-Hamilton a appliqué à Cochrane-Piazzesi et Ludvigson-Ng. **Non vérifié — à
traiter comme prometteur mais non blanchi du même risque tant qu'un test équivalent n'est pas
trouvé.**

**Réplicabilité** : les composantes (inflation réalisée US, taux Treasury) sont **gratuites**
(FRED). C'est le résultat le plus facilement réplicable de cette section 4.

---

## 5. Surprises macro et réaction des prix

### 5.1 Andersen, Bollerslev, Diebold & Vega, *Micro Effects of Macro Announcements: Real-Time
Price Discovery in Foreign Exchange*, **PEER-REVIEWED**, American Economic Review, vol. 93, no. 1,
2003, pp. 38-62

**Résultat central** : les surprises d'annonces macro programmées (US et allemandes/européennes)
produisent des **sauts (jumps) dans la moyenne conditionnelle** des taux de change spot au moment
précis de l'annonce — effet de haute fréquence, mesuré en temps réel sur 6 ans de cotations
intra-journalières. **Réaction asymétrique** : les mauvaises nouvelles ont un impact plus fort que
les bonnes nouvelles (lien avec la littérature sur le traitement de l'information). Étude
complémentaire (Andersen-Bollerslev-Diebold-Vega, NBER WP 11312, *Real-Time Price Discovery in
Stock, Bond and Foreign Exchange Markets*) : **les marchés obligataires réagissent le plus
fortement aux nouvelles macro, suivis du FX, puis des actions** — mais en conditionnant sur l'état
de l'économie (récession vs expansion), FX et actions deviennent comparables en sensibilité.

**Taille d'effet chiffrée en R²/ampleur de mouvement** : **non trouvé** dans cette recherche un
chiffre agrégé unique (le papier original documente des coefficients de réaction par variable
macro et par devise, tableau par tableau — pas un R² de synthèse citable en une ligne). Ce qui EST
solidement établi : l'effet est réel, de haute fréquence (minutes), et surtout **transitoire** —
la littérature de microstructure ultérieure (non détaillée ici) documente que l'essentiel du
re-pricing se fait en quelques minutes à quelques heures.

**Fréquence de décision implicite — LE POINT CRITIQUE pour cette famille** : les annonces macro
programmées majeures (NFP, CPI, FOMC, PIB) sont en nombre **fini et connu à l'avance** — de
l'ordre de **20 à 40 événements par an aux US** selon la liste retenue (8 FOMC, 12 NFP, 12 CPI,
4 PIB, plus quelques autres — avec chevauchements de calendrier). **Un signal qui n'existe que sur
la fenêtre de quelques minutes autour de ces annonces a un plafond dur de breadth ≈ 20-40
paris/an, quel que soit le nombre d'instruments ou de devises testés simultanément** (tester 10
paires de devises sur le même événement FOMC ne donne PAS 10 paris indépendants — c'est
exactement la même surprise macro, donc un seul pari répliqué 10 fois, fortement corrélé). C'est
le deuxième cas d'école du rapport pour la confusion observations/paris.

### 5.2 Evans & Lyons, *Order Flow and Exchange Rate Dynamics*, **PEER-REVIEWED**, Journal of
Political Economy, vol. 110, no. 1, 2002, pp. 170-180

**Résultat central chiffré** : un modèle de changement quotidien du taux de change intégrant le
flux d'ordres (order flow, variable de microstructure — pas une variable macro publique) produit
un **R² > 50%** en général et **> 60% pour le DEM/USD**, contre un R² typiquement **≤ 10%** pour les
modèles macro traditionnels (fondamentaux publiés). Le modèle bat la marche aléatoire hors
échantillon à court horizon.

**⚠ Ce résultat n'est PAS un résultat de prédictibilité MACRO** — c'est l'inverse : la conclusion
du papier est précisément que ce sont les variables de MICROSTRUCTURE (flux d'ordres interbancaires
non publics au moment de la transaction) qui expliquent le taux de change quotidien, PAS les
variables macro publiées. Il est cité ici parce qu'il définit le contraste : R²<10% pour les
modèles macro vs R²>50% pour l'order flow, sur le MÊME horizon quotidien. **Le flux d'ordres n'est
en général pas une donnée gratuite/accessible au retail** (nécessite un accès broker/interbancaire
agrégé) — famille non réplicable à bas coût.

### 5.3 Savor & Wilson, *How Much Do Investors Care About Macroeconomic Risk? Evidence from
Scheduled Economic Announcements*, **PEER-REVIEWED**, Journal of Financial and Quantitative
Analysis, vol. 48, no. 2, 2013, pp. 343-375

**Résultat central chiffré, échantillon 1958-2009 (51 ans), marché actions US** :
- Rendement excès moyen les jours d'annonce macro programmée : **11.4 points de base**, contre
  **1.1 points de base** les autres jours.
- **Plus de 60% de la prime de risque actions annuelle cumulée est gagnée sur les jours
  d'annonce** — alors que ces jours ne représentent qu'une fraction du calendrier.
- Sharpe ratio **~10× plus élevé** les jours d'annonce macro que les autres jours.
- Sur les jours FOMC spécifiquement : rendement moyen et Sharpe ratio **20 à 40× plus élevés**
  qu'en jours normaux.
- Le taux sans risque est mesurablement plus bas les jours d'annonce (cohérent avec un motif
  d'épargne de précaution).

**Fragilité/robustesse** : résultat très cité (peer-reviewed JFQA), échantillon long (51 ans),
effet non marginal — c'est probablement le résultat le PLUS robuste de toute la section 5. Réserve
académique standard : le mécanisme (pourquoi une prime EX ANTE sur un jour où l'incertitude se
RÉSOUT ex post ?) reste débattu théoriquement (papier récent cité en lien, Ai et al., NBER WP
31923, *Macroeconomic Announcement Premium*, tente une explication structurelle — **non lu en
détail dans cette recherche**).

**Fréquence de décision implicite — MÊME PLAFOND que 5.1** : le nombre de jours d'annonce macro
programmée majeure aux US est de l'ordre de **30-50/an**. Une stratégie de type « long actions
uniquement les jours d'annonce macro programmée » a un plafond dur de breadth de **30-50 paris par
an**, indépendamment du nombre d'instruments — exactement la même contrainte que 5.1. C'est un
edge réel et bien documenté, mais **structurellement un edge à basse fréquence de pari**, jamais un
edge "haute fréquence de décision" même s'il est mesuré en rendement journalier.

**Réplicabilité gratuite** : calendrier des annonces macro programmées = gratuit (BLS, Fed,
Investing.com economic calendar). Rendements actions = gratuits (indices larges). **Entièrement
réplicable à coût nul** — bon candidat pour une vérification interne rapide, à condition de traiter
honnêtement le plafond de breadth ci-dessus dans tout calcul de Sharpe annualisé (ne jamais
annualiser en √252 un edge qui ne se manifeste que ~40 jours/an — cf. déjà L47 du registre interne
sur l'annualisation en √(obs/an)).

---

## 6. FX — fondamentaux et taux de change

### 6.1 Meese & Rogoff, *Empirical Exchange Rate Models of the Seventies: Do They Fit Out of
Sample?*, **PEER-REVIEWED**, Journal of International Economics, vol. 14, no. 1, 1983, pp. 3-24

**Résultat fondateur, toujours la référence 40+ ans après** : les modèles structurels
(monétaires flexible-price Frenkel-Bilson, sticky-price Dornbusch-Frankel, sticky-price avec
compte courant Hooper-Morton) estimés sur les données des années 1970 **ne battent pas une simple
marche aléatoire** en prévision hors échantillon à horizons de 1 à 12 mois, sur USD/GBP, USD/DEM,
USD/JPY et un indice USD pondéré par les échanges. **Univers/échantillon exact des sous-périodes
de test non retrouvé au chiffre près dans cette recherche** (le papier est structuré autour d'un
découpage in-sample années 1970 / out-of-sample fin de période — **non trouvé** de dates exactes
de coupure à la décimale près, à vérifier avant citation dans un document externe).

**Ce qui a survécu 40+ ans plus tard** : **le résultat tient toujours pour la prévision de NIVEAU
et en erreur quadratique moyenne** — confirmé par les répliques successives (Meese-Rogoff 1988,
Chinn-Meese 1995, Cheung-Chinn-Garcia Pascual 2005, cités dans la littérature de suivi). **Ce qui
a été nuancé** : si on change le critère d'évaluation — précision directionnelle, mesure combinant
magnitude et direction, ou rentabilité d'une stratégie de trading plutôt qu'erreur quadratique —
**certains modèles fondamentaux BATTENT la marche aléatoire**, y compris avec exactement les mêmes
données et la même méthode d'estimation que Meese-Rogoff. **Point clé pour ce dépôt** : ceci est
cohérent avec l'expérience interne déjà documentée sur l'ORB et d'autres familles (le critère
d'évaluation change le verdict) — mais aussi un motif de scepticisme renforcé : la littérature qui
« bat » la marche aléatoire le fait quasi-systématiquement sur un critère DIFFÉRENT de celui utilisé
pour établir le puzzle initial, jamais sur le même critère à erreur quadratique.

### 6.2 Engel & West, *Exchange Rates and Fundamentals*, **PEER-REVIEWED**, Journal of Political
Economy, vol. 113, no. 3, 2005, pp. 485-517

**Résultat central, théorique** : dans un modèle rationnel de valeur actualisée (present-value
model), si les fondamentaux sont intégrés d'ordre 1 (I(1), marche aléatoire eux-mêmes — vrai pour
masse monétaire, PIB, inflation, taux) et que le facteur d'actualisation des fondamentaux futurs
est PROCHE de 1, alors le prix de l'actif (le taux de change) se comporte lui-même **proche d'une
marche aléatoire, MÊME SI le vrai modèle sous-jacent est entièrement fondé sur les fondamentaux
macro**. C'est une **explication théorique du puzzle Meese-Rogoff**, pas une réfutation : les
fondamentaux macro sont réels et pertinents, mais leur effet sur le prix, une fois actualisé à un
facteur proche de 1, produit un signal quasi indiscernable d'une marche aléatoire au niveau. Les
auteurs montrent aussi une preuve empirique complémentaire dans le sens inverse : **le taux de
change aide à prédire les fondamentaux futurs** (le prix contient de l'info sur le futur macro,
pas l'inverse) — cohérent avec l'hypothèse d'un marché efficient qui price déjà l'information macro
disponible.

**Verdict pour ce dépôt** : ce papier est la meilleure explication théorique disponible de
POURQUOI chercher un signal FX directement dans les fondamentaux macro publiés est structurellement
voué à l'échec au niveau (level), quel que soit l'effort d'ingénierie de features. Le signal
existe, mais il est dans le PRIX avant d'être dans la donnée macro publiée.

### 6.3 Fratzscher, Rime, Sarno & Zinna, *The Scapegoat Theory of Exchange Rates: The First
Tests*, **PEER-REVIEWED** (ECB Working Paper puis Journal of International Economics), 2015 —
test empirique de la théorie de Bacchetta & van Wincoop (2004, 2013)

**Correction méthodologique nécessaire** : le brief de mission citait "Della Corte... modèles de
scapegoat" — recherche effectuée confirme que la théorie du scapegoat est de **Bacchetta &
van Wincoop**, et son premier test empirique direct est de **Fratzscher, Rime, Sarno & Zinna**, PAS
de Della Corte (qui a d'autres contributions FX notables — carry trade, dollar risk factor — non
couvertes ici faute de correspondance avec le brief). À corriger dans toute citation ultérieure.

**Mécanisme** : dans un contexte où le taux de change est en partie mû par des chocs non
observables, les participants de marché attachent un poids excessif à UN fondamental macro
particulier — le « bouc émissaire » — choisi d'autant plus qu'il est lui-même éloigné de son
équilibre de long terme ET que le mouvement de change inexpliqué est large. Testé sur des données
d'enquête (survey) mesurant directement quel fondamental est cité comme scapegoat pour 12 taux de
change.

**Résultat chiffré** : le modèle résultant **explique une large fraction de la variation et des
changements directionnels EN ÉCHANTILLON**, mais **la performance de prévision HORS échantillon
est mitigée (mixed)** — c'est un aveu explicite des auteurs, cité dans la synthèse trouvée.
**Chiffre R²/Sharpe précis non trouvé** dans cette recherche — à consulter dans le papier complet
avant toute citation d'un chiffre exact.

**Fréquence de décision** : nécessite des données d'enquête FX spécialisées identifiant le
scapegoat en temps réel — **donnée propriétaire (Bloomberg/Reuters survey), non réplicable
gratuitement**. Même en supposant l'accès aux données, le mécanisme suppose une ré-estimation
fréquente de quel fondamental est le scapegoat courant — pas un signal simple à breadth élevée.

### Synthèse section 6 — existe-t-il un horizon où les fondamentaux battent la marche aléatoire ?

**Réponse honnête, synthèse des 3 papiers ci-dessus** : à l'horizon standard (1-12 mois, en erreur
quadratique de prévision de niveau), **NON** — le puzzle Meese-Rogoff tient toujours 40+ ans après,
et Engel-West en donne une explication structurelle qui prédit que ça CONTINUERA de tenir tant que
les fondamentaux macro seront eux-mêmes proches d'une marche aléatoire. Il existe des nuances
(précision directionnelle, rentabilité de trading, théories de deuxième ordre comme le scapegoat)
où certains résultats battent la marche aléatoire, mais systématiquement (a) sur un critère
différent de l'erreur quadratique de niveau, (b) avec une performance hors échantillon
« mitigée » quand elle est rapportée honnêtement, et (c) souvent avec des données propriétaires
(order flow, enquêtes FX). **Aucun résultat FX-fondamentaux de ce rapport ne constitue un signal
directement actionnable et réplicable gratuitement à un horizon utile pour ce dépôt.**

---

## 7. Nowcasting

### 7.1 Giannone, Reichlin & Small, *Nowcasting: The Real-Time Informational Content of
Macroeconomic Data*, **PEER-REVIEWED**, Journal of Monetary Economics, vol. 55, no. 4, 2008, pp.
665-676

**Résultat central** : méthode formelle (modèle à facteurs dynamiques, gérant les données
déséquilibrées/asynchrones typiques du temps réel) pour évaluer l'impact marginal de CHAQUE
publication macro intra-mensuelle sur la prévision du PIB du trimestre en cours. Décompose la
contribution de chaque "news" (surprise = donnée publiée moins attendue) en (a) ce qui vient de la
RAPIDITÉ de publication (certaines séries sortent plus tôt que d'autres dans le mois) et (b) ce qui
vient du CONTENU économique propre de la série. **Chiffre de réduction d'erreur de prévision
précis non trouvé** dans cette recherche (nécessiterait la lecture du corps du papier, non faite
ici) — mais le résultat qualitatif bien établi dans la littérature de suivi (dynamic factor models,
désormais standard à la Fed/BCE/NY Fed pour le nowcasting GDP en temps réel) est que l'ajout
séquentiel des publications réduit MONOTONIQUEMENT l'incertitude de la prévision du trimestre en
cours, avec un gain marginal décroissant au fil du mois.

**⚠ POINT CRITIQUE POUR CE DÉPÔT — fréquence de décision** : le nowcasting est un exercice de
RÉDUCTION D'INCERTITUDE SUR UNE CIBLE TRIMESTRIELLE (le PIB du trimestre courant), pas un
générateur de signal de trading à haute fréquence. Même si le nowcast est mis à jour à CHAQUE
publication intra-mensuelle (donc potentiellement plusieurs dizaines de fois par mois, mise à jour
"continue"), **la variable réellement prédite (croissance du PIB du trimestre) ne se réalise que 4
fois par an**, et la fenêtre de vraie nouveauté économique nette (au-delà du simple raffinement
d'une estimation déjà largement anticipée) est bien plus étroite que le nombre de publications ne
le suggère. **C'est le troisième cas d'école du rapport pour la confusion observations/paris** :
un modèle qui "tourne" quotidiennement en apparence ne produit, au fond, qu'une poignée de vrais
paris macro par an sur la cible qu'il est censé prédire — sauf si l'objectif de trading est
lui-même à la fréquence des surprises de publication elles-mêmes (auquel cas on retombe dans la
famille section 5, avec le même plafond de ~20-40 événements/an, et le même besoin de traiter
chaque surprise comme sa propre variable cible, pas comme une resucée du nowcast trimestriel).

**Réplicabilité gratuite** : **oui, en bonne partie**. Le dataset FRED-MD (McCracken-Ng) est conçu
précisément pour ce type de modèle à facteurs dynamiques et est gratuit. Des implémentations
open-source de nowcasting DFM existent (ex. bibliothèques Python/R publiques). **C'est la famille
la plus réplicable à coût nul de tout ce rapport en termes d'infrastructure de données**, mais avec
la réserve de fréquence de pari ci-dessus : ce n'est PAS une source de breadth élevée, c'est un
outil de timing macro à très basse fréquence de décision utile (4-12 paris/an selon comment on le
recycle).

---

## Synthèse transversale — fréquence de paris indépendants par courant (vue d'ensemble)

| Courant | Paris indépendants/an (estimation qualitative) | Statut peer-review | Survit hors échantillon ? |
|---|---|---|---|
| Macro momentum (AQR, §1) | ~10-20 (signaux annuels, 4 thèmes × 4 classes, corr. moyenne 0.1) | Whitepaper gérant | Décroissance nette 2010-16 (SR 1.2→0.7), dans le papier lui-même |
| Régime croissance/inflation (§2) | ~2-4 (changements de régime réels) | Peer-reviewed (survey) + whitepapers gérants pour les quadrants | Mécanisme mean/variance enchevêtré ; pas de méta-analyse OOS chiffrée trouvée |
| Carry cross-asset (KMPV, §3) | Plusieurs dizaines à ~100 (cross-sectionnel mensuel, mais forte composante statique) | **Peer-reviewed (JFE)** | Signal probablement vivant en exécution institutionnelle ; VÉHICULE (CFD/perp retail) déjà tué en interne (L28, L36, Strategy B) |
| Facteurs macro obligataires (CP/LN/CieslakPovala, §4) | ~10-40 (cible annuelle, chevauchement massif) | **Peer-reviewed**, mais CP et LN **explicitement affaiblis** par Bauer-Hamilton 2018 | CP/LN : significativité ne survit pas à un test robuste. Cieslak-Povala : non re-testé trouvé |
| Surprises macro / annonces (ABDV, Savor-Wilson, §5) | **Plafond dur ~20-50/an** (nb d'annonces programmées) | **Peer-reviewed**, Savor-Wilson particulièrement robuste (51 ans) | Effet réel et large, mais structurellement basse fréquence — pas décayé à ma connaissance (non re-testé post-2013 dans cette recherche) |
| FX fondamentaux (Meese-Rogoff et suite, §6) | N/A — le signal lui-même est essentiellement absent au niveau standard | **Peer-reviewed**, résultat de 1983 **toujours valide 40+ ans après** | Confirmé mort pour l'usage direct (marche aléatoire non battue en RMSE) |
| Nowcasting (GRS, §7) | ~4-12 (cible trimestrielle recyclée) | **Peer-reviewed** | Outil d'infrastructure, pas un générateur de Sharpe direct |

**Le motif qui traverse TOUT ce rapport** : dans chaque courant testé, le nombre de vrais paris
indépendants par an est un ordre de grandeur (parfois deux) EN DESSOUS de ce que la fréquence
apparente des données (quotidienne, voire intra-journalière) suggère. C'est structurellement la
MÊME erreur que celle déjà identifiée dans le modèle de scoring macro amateur audité en amont de ce
travail — elle n'est pas propre à ce dépôt, elle est endémique à toute la littérature de
prédictibilité macro, y compris dans des papiers publiés dans les meilleures revues.

---

## CE QUE JE NE RECOMMANDE PAS DE POURSUIVRE ET POURQUOI

1. **FX fondamentaux au niveau standard (§6, Meese-Rogoff/Engel-West)** — NE PAS poursuivre. Le
   puzzle tient depuis 1983, a une explication théorique solide (facteur d'actualisation proche de
   1 + fondamentaux eux-mêmes proches d'une marche aléatoire), et la littérature qui prétend le
   battre change systématiquement de critère d'évaluation. Le peu qui reste (scapegoat) demande des
   données d'enquête propriétaires et a une performance OOS "mitigée" de l'aveu même des auteurs.

2. **Cochrane-Piazzesi et Ludvigson-Ng tels quels (§4.1-4.2)** — NE PAS citer leurs R² comme des
   faits établis sans le caveat Bauer-Hamilton 2018. Ce sont des résultats emblématiques de la
   littérature de finance obligataire, mais un test statistique robuste et publié en peer-review
   montre que leur significativité ne survit pas à une correction de petit échantillon. Réplicable
   gratuitement (FRED/FRED-MD), mais réplicable ≠ vivant.

3. **Cadres "quadrant" croissance/inflation à la Ilmanen/Investment Clock (§2.2)** — NE PAS
   poursuivre sous cette forme narrative. Aucune source académique à comité de lecture avec un
   chiffre d'effet net de coûts n'a été identifiée ; le mécanisme mathématique (Ang-Timmermann)
   montre que régime-prédit-la-moyenne et régime-prédit-la-variance sont enchevêtrés par
   construction, exactement le piège déjà tombé dessus en interne (L54). Tout nouveau projet de
   ce type doit d'abord démontrer, sur les données du book RÉEL, que le régime candidat prédit la
   moyenne DANS LE MÊME SENS que la variance — sinon c'est un déguisement de risk-parity, pas un
   alpha.

4. **Order flow FX (Evans-Lyon, §5.2) comme source de signal accessible** — NE PAS poursuivre pour
   ce dépôt : le signal est réel et fort (R²>50%) mais nécessite des données de microstructure
   interbancaire non accessibles à un chercheur solo à coût raisonnable.

5. **Macro momentum AQR tel quel (§1)** — NE PAS répliquer à l'identique. Whitepaper gérant non
   arbitré, décroissance de Sharpe manifeste sur la dernière décennie du papier lui-même
   (1.2→0.7), gross-of-costs explicitement reconnu comme optimiste par l'auteur, breadth effective
   non quantifiée par les auteurs et probablement de l'ordre de 10-20 paris/an — pas la source de
   diversification "gratuite" qu'elle a l'air d'être en lecture rapide. La partie réplicable
   gratuitement (thèmes politique monétaire et commerce international, via taux 2 ans et FX spot)
   pourrait justifier un test interne prudent, mais SANS le thème "cycle économique" (données
   consensus payantes) et avec un budget de breadth réaliste dès le départ.

6. **Ce qui mérite un test interne prudent, sous conditions strictes** : le carry cross-asset
   KMPV (§3, seul résultat peer-reviewed en revue de premier rang + multi-décennie + multi-classe
   de ce rapport) — MAIS seulement sur les 4 classes réplicables gratuitement (FX, obligations,
   taux, commodités) et seulement en environnement à coût institutionnel (futures), jamais en CFD
   retail ou funding perp (déjà tué en interne pour cette raison précise, cf. L28/L36/Strategy B).
   Et Savor-Wilson (§5.3) comme vérification interne rapide et gratuite du calendrier d'annonces
   macro US sur le book réel — à condition de traiter le plafond de ~30-50 paris/an honnêtement
   dans tout calcul de Sharpe, jamais en annualisation √252.

---

*Fin du rapport. Toutes les affirmations sans chiffre précis sont marquées "non trouvé" plutôt que
comblées par extrapolation. Sections lues en détail depuis les PDF sources primaires : AQR "A Half
Century of Macro Momentum" (10 pages), NBER "Carry" (15 pages), Ang & Timmermann "Regime Changes
and Financial Markets" (8 pages). Les autres résultats sont rapportés depuis les résumés/abstracts
retournés par la recherche web et devraient être re-vérifiés sur le texte intégral avant toute
citation dans un document destiné à circuler hors de ce dépôt.*
