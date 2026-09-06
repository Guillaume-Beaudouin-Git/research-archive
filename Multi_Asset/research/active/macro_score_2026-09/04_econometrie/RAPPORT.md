# Score macro par devise/paire — spécification économétrique

**Statut** : document de spécification (pré-implémentation). Aucune donnée, aucun backtest.
**Auteur** : session Claude Code, rôle économètre quant.
**Destinataire** : chercheur solo, book FTMO/perso, exigences repo (`CLAUDE.md` racine) : HAC lag-6,
walk-forward ≥5 folds, bootstrap par blocs, DSR, placebos appariés, rendements en excès du taux sans
risque, max 3 modifications par hypothèse.
**Portée** : ce document spécifie COMMENT construire le score. Il ne teste rien lui-même — chaque
section se termine par le test qui devra être exécuté avant toute mise en production du score, avec
le protocole exact (pas juste le nom de la méthode).

---

## 0. Cadrage du problème et fil conducteur

Un score macro par devise/paire répond à trois sous-problèmes empilés, et l'ordre compte : une erreur
en amont (agrégation) contamine tout ce qui suit (choc, dynamique), donc le budget de rigueur doit
être alloué dans cet ordre, pas également réparti.

```
niveaux macro hétérogènes  →  (a) AGRÉGATION  →  score-niveau composite
                                                        │
                                                        ▼
score-niveau composite     →  (b) CHOC        →  surprise standardisée (tradable)
                                                        │
                                                        ▼
surprise standardisée      →  (c) DYNAMIQUE    →  poids d'exposition à l'instant t
```

Le piège n° 1, transversal aux trois étapes, est de croire que la difficulté est **statistique**
(quel estimateur est le plus efficient) alors qu'elle est **presque toujours structurelle** : le N
effectif est minuscule, les séries partagent des tendances communes cross-pays, et le chercheur a
d'énormes degrés de liberté de spécification. Un estimateur sophistiqué appliqué sans discipline sur
ces trois points produira un t-stat impressionnant et un score inutile. La séquence de recommandation
en fin de document reflète ce diagnostic : la sophistication économétrique n'est PAS le facteur
limitant pour ce chercheur ; la discipline de test l'est.

Convention de notation : pour un pays/bloc $c$ et une série macro $i$, on note $x_{i,c,t}$ le niveau
publié à la date de publication $t$ (pas la date de référence de la série — voir §3.b sur la fuite
par révisions), $\hat{x}_{i,c,t}$ le consensus/l'attendu au moment de la publication, et
$s_{i,c,t} = x_{i,c,t} - \hat{x}_{i,c,t}$ la surprise brute.

---

## (a) Agrégation — combiner des séries hétérogènes en un score

### 1. Z-scores composites (méthode naïve)

**Formulation.** Pour chaque série $i$, calculer un z-score glissant
$z_{i,t} = \dfrac{x_{i,t} - \mu_i(t-1; w)}{\sigma_i(t-1; w)}$, où $\mu_i, \sigma_i$ sont estimés sur
une fenêtre glissante de $w$ observations **strictement antérieures** à $t$ (jamais en excluant $t$
d'un ensemble centré — c'est du leak). Le score composite pour le pays $c$ est
$Z_{c,t} = \sum_i \omega_i z_{i,t}$, avec $\sum_i \omega_i = 1$.

Deux choix de poids :
- **Égalité** : $\omega_i = 1/N$.
- **Optimisée** : $\omega_i \propto$ IC individuel, ou solution d'une régression ridge du rendement
  futur sur les $z_i$.

**Hypothèses.** (i) Stationnarité locale de $\mu_i, \sigma_i$ sur la fenêtre $w$ (violée en cas de
changement de régime de politique monétaire, de changement de méthodologie de publication — ex.
refonte d'un indice PMI) ; (ii) les $z_i$ sont informatifs individuellement (sinon la moyenne de bruit
reste du bruit, elle ne devient pas signal par agrégation — voir le test de falsification) ;
(iii) la relation z-score → rendement futur est approximativement linéaire et stable dans le temps.

**Pourquoi la pondération égale bat souvent l'optimisation.** C'est un résultat robuste de la
littérature sur l'allocation de portefeuille (DeMiguel, Garlappi, Uppal 2009, *Optimal Versus Naive
Diversification*) transposable ici trait pour trait : l'optimisation de poids sur IC ou par régression
introduit une matrice de covariance (ou de corrélations croisées) estimée sur un échantillon petit,
et l'erreur d'estimation sur les poids domine souvent le gain théorique d'optimalité. Le résultat
classique est que 1/N bat les stratégies optimisées tant que la longueur d'historique nécessaire pour
estimer fiablement $\Sigma^{-1}$ (grossièrement, $T \gg N^2$) n'est pas atteinte. En macro, avec
$N \sim 10$-$20$ séries et $T \sim 100$-$400$ observations mensuelles utiles, cette condition n'est
**jamais** remplie ⇒ présomption forte en faveur de 1/N comme point de départ, l'optimisation devant
prouver son droit d'exister (voir test de falsification ci-dessous, calqué sur le protocole DeMiguel).

**Gestion des révisions.** Le z-score doit être calculé sur la **valeur telle que connue à la date
$t$** (vintage), jamais sur la série finale révisée disponible aujourd'hui — sinon le score est
non-réplicable en temps réel (voir §"pièges spécifiques", fuite par révisions).

**Données requises.** Séries de niveau à fréquence native (mensuelle/trimestrielle), historique de
vintages si disponible (ALFRED/ArchiveFRED côté US, moins standard hors US — accepter un proxy
dégradé : première publication vs révisée à N mois si le vintage complet n'existe pas).

**Coût d'implémentation.** Faible. Quelques heures : rolling mean/std, alignement de dates, gestion
des NA. Aucune dépendance à un solveur.

**Test de falsification.** (i) **Test IJR d'abord** : pour chaque z-score individuel, calculer
l'IC (corrélation rang z-score → rendement futur excess) et son t-stat HAC lag-6 ; un z-score dont
IC n'a pas |t| > 2 individuellement ne doit PAS entrer dans le composite (l'agrégation d'inputs non
informatifs ne crée pas d'information — c'est un test de composition, pas juste un test du composite
fini). (ii) **Test DeMiguel apparié** : comparer, en walk-forward ≥5 folds, le Sharpe **OOS** (excess,
HAC) du composite égal-pondéré contre celui du composite à poids optimisés (ridge/IC-weighted) estimés
sur le fold d'entraînement seul ; si l'optimisé ne bat pas l'égal-pondéré de façon significative au
bootstrap par blocs, ABANDONNER l'optimisation — la présomption 1/N n'est pas renversée. (iii) test de
**stabilité des poids** : si l'optimisation est retenue malgré (ii), vérifier que les poids optimaux
ne changent pas de signe d'un fold à l'autre (signe instable = poids qui capturent du bruit
d'échantillonnage, pas un ordre de mérite réel entre séries).

### 2. Modèles à facteurs dynamiques / nowcasting (Giannone-Reichlin-Small, Bańbura-Modugno)

**Formulation.** Modèle à espace d'états. Un facteur commun (scalaire ou vectoriel) $f_t$ évolue selon
une dynamique VAR : $f_t = A f_{t-1} + u_t$, et chaque série observée haute fréquence est une fonction
linéaire bruitée du facteur : $x_{i,t} = \lambda_i f_t + \varepsilon_{i,t}$. Les séries à basse
fréquence (ex. PIB trimestriel) sont traitées comme des observations manquantes la plupart des mois,
et agrégées via une contrainte d'accumulation (approximation d'Mariano-Murasawa pour les taux de
croissance trimestriels observés mensuellement). L'estimation se fait par filtre de Kalman +
EM (Bańbura-Modugno 2014, *Maximum Likelihood Estimation of Factor Models on Datasets with Arbitrary
Pattern of Missing Data*), ce qui permet nativement les fréquences mixtes ET les données manquantes
(un pays qui publie en retard n'interrompt pas l'estimation).

**Hypothèses.** (i) Un petit nombre de facteurs communs (1 à 3) explique l'essentiel de la variance
partagée entre séries — hypothèse de "petit espace de facteurs" qui échoue si le monde macro
pertinent pour la paire de devises est multi-dimensionnel de façon irréductible (croissance ET
inflation ET politique monétaire comme axes séparés — alors il faut plusieurs facteurs, ce qui
dégrade vite le ratio observations/paramètres). (ii) Linéarité $x_{i,t} = \lambda_i f_t + \varepsilon$
— violée en régime de crise où les corrélations inter-séries changent brutalement (voir §4 régimes).
(iii) $\varepsilon_{i,t}$ non corrélé entre séries conditionnellement au facteur — souvent violé pour
des séries très proches (ex. deux mesures de PMI manufacturier de sources différentes), gérable en
autorisant une composante idiosyncratique autocorrélée dans certains blocs.

**Données requises.** Panel large de séries mensuelles + trimestrielles pour le bloc macro visé
(USD : ISM, payrolls, retail sales, PIB, etc.), avec vintages si possible pour un nowcasting fidèle au
temps réel. C'est l'exigence de données la plus lourde des sept familles.

**Coût d'implémentation.** Élevé pour un chercheur solo. Le filtre de Kalman + EM sur données
manquantes à motif arbitraire est un morceau de code non trivial (bugs silencieux fréquents :
normalisation des unités avant stack, initialisation de la matrice de covariance, identification du
signe/échelle du facteur). Des implémentations existent (`dfms` en R, quelques ports Python
incomplets) — buildable en 1-2 semaines pleines pour un chercheur seul en partant d'une librairie,
plusieurs semaines en partant de zéro. Le retour sur investissement n'est positif que si le nombre de
séries d'entrée est réellement grand (>15-20) — sinon un z-score composite capture presque toute la
variance du facteur commun de toute façon (voir test de falsification).

**Test de falsification.** Comparer, sur les MÊMES dates de nowcast (retirées en walk-forward), le
facteur extrait $\hat{f}_t$ du DFM contre le simple z-score composite §1 pondéré égal : régresser
$\hat{f}_t$ sur $Z_t$ (z-score composite) et rapporter le $R^2$. **Si $R^2 > 0.85$-$0.90$, le DFM ne
fait que redécouvrir la moyenne pondérée avec un coût d'implémentation 10x supérieur** — ne pas le
déployer, documenter l'équivalence et arrêter là. Le DFM ne se justifie que si (i) $R^2$ est
significativement plus bas (le facteur latent capture une structure que la moyenne simple rate — par
exemple parce que les séries ont des retards de publication très hétérogènes que le DFM gère et le
z-score ignore), ET (ii) l'IC du DFM sur rendement futur (walk-forward, HAC) domine celui du z-score
composite de façon significative au bootstrap par blocs (pas juste "un peu plus haut en point
estimate" — la marge d'erreur sur un IC estimé sur ~100-200 observations mensuelles est large).

### 3. MIDAS (Mixed Data Sampling, Ghysels)

**Formulation.** Régression directe où la variable expliquée basse fréquence (ex. rendement mensuel de
la paire, ou PIB trimestriel si on prévoit un niveau macro) est régressée sur un polynôme de retards de
la variable haute fréquence, avec une fonction de poids paramétrique qui réduit le nombre de
paramètres à estimer :
$y_{t}^{(LF)} = \beta_0 + \beta_1 \sum_{k=0}^{K} B(k;\theta)\, x^{(HF)}_{t - k/m} + e_t$,
où $B(k;\theta)$ est typiquement une fonction Beta ou Almon exponentielle à 2 paramètres $\theta$, et
$m$ le ratio de fréquences (ex. $m=22$ pour relier du daily à du mensuel). MIDAS peut aussi tourner en
sens inverse : haute fréquence expliquée par un facteur basse fréquence agrégé au dernier point
connu (ex. régression daily de rendement de change sur le dernier PIB publié).

**Hypothèses.** (i) La forme paramétrique du noyau de poids ($B(k;\theta)$) capture correctement la
vraie forme de décroissance de l'influence des retards — mal spécifiée, elle biaise l'estimation même
avec beaucoup de données (contrairement au DFM qui est plus agnostique sur la forme). (ii) Absence de
changement structurel dans la relation HF↔LF sur la fenêtre d'estimation. (iii) Le nombre de retards
$K$ à haute fréquence est fixé ex ante (pas choisi par test de spécification post-hoc — sinon
degrés de liberté du chercheur, voir pièges).

**Données requises.** Une série haute fréquence propre (ex. spread de swap, différentiel de taux
court) alignée sur une série basse fréquence cible. Moins gourmand que le DFM en largeur de panel, mais
exige une série HF de bonne qualité et longue.

**Coût d'implémentation.** Modéré. L'estimation non-linéaire des 2 paramètres du noyau Beta/Almon se
fait par NLS standard (`scipy.optimize`), quelques jours de travail pour un chercheur qui maîtrise déjà
la régression avec HAC. Le risque principal n'est pas le code mais la sur-paramétrisation du noyau.

**Test de falsification.** MIDAS n'a de raison d'être ici que s'il bat un simple agrégat de la série HF
au dernier point du mois (i.e. "moyenne du mois" ou "dernière observation du mois") en walk-forward,
HAC, OOS. **Test direct** : comparer $R^2$ OOS de MIDAS contre un agrégat naïf (moyenne mensuelle de la
série HF) sur les mêmes folds ; si l'écart n'est pas significatif au bootstrap par blocs, la
paramétrisation MIDAS est un coût sans bénéfice — repli sur l'agrégat naïf, qui est un cas particulier
dégénéré de MIDAS (noyau uniforme) et n'a aucun paramètre de forme à mal spécifier.

### 4. Modèles à changement de régime (Markov-switching, Hamilton 1989 ; HMM)

**Formulation.** La série (ou un vecteur de séries macro) suit un processus dont les paramètres
dépendent d'un état latent $S_t \in \{1,\dots,K\}$ markovien : $y_t \mid S_t = k \sim
\mathcal{N}(\mu_k, \sigma_k^2)$ (ou AR($p$) à coefficients dépendant de $k$), avec matrice de
transition $P_{jk} = \Pr(S_t = k \mid S_{t-1} = j)$. Estimation par filtre de Hamilton + EM
(maximum de vraisemblance), donnant à chaque date une probabilité filtrée $\Pr(S_t = k \mid
\mathcal{F}_t)$ utilisable comme état du score (ex. "régime expansion" vs "régime resserrement").

**Hypothèses.** (i) Le nombre d'états $K$ est correctement spécifié — un $K$ trop grand sur-ajuste,
un $K$ trop petit force deux régimes réellement différents à cohabiter dans un seul état. (ii) La
matrice de transition est stable dans le temps (elle-même peut être un objet à faible N effectif : un
cycle complet expansion→récession→expansion ne donne que 2-3 transitions observées sur 25 ans de
données). (iii) **La condition qui manque le plus souvent en pratique** : le régime qui prédit
correctement la variance de $y_t$ prédit AUSSI sa moyenne, et dans le bon sens pour l'usage visé.

**⚠ Avertissement central (issu de l'expérience du dépôt, L54).** Un régime peut être un excellent
classifieur de VARIANCE (le stress macro identifié coïncide bien avec la volatilité réalisée de la
paire) sans être un bon prédicteur de MOYENNE, et pire : la moyenne peut être positive précisément
dans les états de haute variance (le stress se rémunère). Dans ce cas, un overlay qui réduit
l'exposition en régime de haute variance détruit exactement les jours qui paient (cf. L54 : book MONO
déployé, régime prédisant bien la variance stress 9.8% vs 4.2%, mais gagnant +218bps vs +21bps sur ces
mêmes jours — toute coupe retranche les jours qui paient). Il faut donc, avant tout déploiement d'un
overlay Markov-switching, **découpler explicitement les deux prédictions** :

- Test de prédiction de variance : régresser $|r_{t+1}|$ (ou $r_{t+1}^2$) sur $\Pr(S_t=k)$, HAC.
- Test de prédiction de moyenne : régresser $r_{t+1}$ (rendement EXCESS futur, pas $|r|$) sur
  $\Pr(S_t=k)$, HAC lag-6.
- **Condition de validité de l'overlay** : le régime doit prédire la moyenne dans le sens qui justifie
  l'action (ex. si l'overlay COUPE l'exposition en régime $k$, alors le rendement conditionnel moyen en
  régime $k$ doit être négatif ou nul, pas juste plus volatil). Documenter les deux coefficients côte
  à côte, jamais seulement le coefficient de variance.
- Comparer ensuite l'overlay non pas à sa version "sans overlay" mais à un **dé-levier à volatilité
  identique** (réduire l'exposition partout de façon uniforme pour matcher la vol réalisée moyenne du
  book overlay) — si l'overlay ne bat pas ce dé-levier neutre, l'overlay n'ajoute rien au-delà d'un
  simple vol-targeting déjà présent par ailleurs dans le pipeline (rappel : le repo impose déjà le
  vol-targeting quotidien comme hard rule — un overlay Markov qui ne bat pas cette baseline est
  redondant par construction).

**Données requises.** Une série macro ou un rendement suffisamment long pour couvrir plusieurs cycles
(idéalement >3 cycles complets, ce qui en pratique impose souvent >40 ans de données — rarement
disponible proprement à fréquence homogène pour du FX).

**Coût d'implémentation.** Modéré à élevé selon la librairie (statsmodels a un `MarkovAutoregression`
fonctionnel — implémentation rapide ; le risque est presque entièrement dans l'interprétation et la
validation, pas dans le code).

**Test de falsification.** Au-delà du test moyenne/variance ci-dessus : **test de nombre de paris
effectif sur les régimes** — combien de fois la chaîne change-t-elle réellement d'état sur
l'échantillon ? Si $K=2$ et qu'on observe 3 transitions en 25 ans, aucune inférence sur "le régime
prédit X" n'est crédible (N=3 n'est pas un échantillon, indépendamment du t-stat rapporté sur les
probabilités filtrées quotidiennes qui sont, elles, autocorrélées à l'extrême). Rapporter ce compte de
transitions en toutes lettres à côté de tout résultat Markov-switching.

### 5. Rétrécissement et hiérarchie (ridge/lasso/elastic net, moyenne bayésienne, pondération par bloc)

**Formulation.** Régression pénalisée du rendement futur excess sur le panel de prédicteurs macro
$z_{i,t}$ : $\min_\beta \sum_t (r_{t+1} - z_t'\beta)^2 + \lambda_1 \|\beta\|_1 + \lambda_2
\|\beta\|_2^2$ (elastic net, cas particuliers ridge $\lambda_1=0$ / lasso $\lambda_2=0$). Alternative
bayésienne : moyenne de modèles (BMA) sur les $2^N$ sous-ensembles de prédicteurs, pondérée par la
probabilité a posteriori de chaque modèle — en pratique approximée (MC3) pour $N$ modéré. Pondération
hiérarchique : score $=\sum_b w_b \left( \sum_i \omega_{i,b} z_{i,b} \right)$ où $b$ indexe des blocs
(pays, ou catégories growth/inflation/policy), avec un rétrécissement à deux niveaux — d'abord au sein
du bloc, puis entre blocs (partial pooling à la Gelman, coefficients de bloc rétrécis vers la moyenne
cross-bloc).

**Hypothèses.** (i) La sparsité est une hypothèse raisonnable sur la relation macro→rendement (lasso)
— discutable : en macro, l'a priori économique est plutôt que TOUTES les séries portent un peu de
signal corrélé (dense, pas sparse), ce qui favorise ridge/elastic net sur lasso pur. (ii) $\lambda$
choisi par validation croisée **temporelle** (jamais k-fold aléatoire, qui mélange futur et passé) —
piège classique et invisible si on utilise `sklearn.GridSearchCV` par défaut. (iii) La hiérarchie
pays/bloc suppose une corrélation intra-bloc plus forte qu'inter-bloc — à vérifier, pas à supposer (si
les blocs sont mal choisis, le rétrécissement hiérarchique rétrécit dans la mauvaise direction).

**Données requises.** Identiques au z-score composite (mêmes séries), plus un historique suffisant
pour que la validation croisée temporelle ait un sens (au minimum 5 folds walk-forward disjoints ⇒
contrainte dure du dépôt, cohérente ici).

**Coût d'implémentation.** Faible à modéré (`sklearn.ElasticNetCV` avec `TimeSeriesSplit`). Le BMA
complet est plus coûteux et rarement justifié pour $N<20$ prédicteurs — l'elastic net à validation
croisée temporelle capture l'essentiel du bénéfice pour un coût très inférieur.

**Test de falsification.** Même logique que §1(ii) : le shrinkage n'a de valeur que s'il bat le
1/N égal-pondéré **OOS**, en walk-forward, avec IC95 par bootstrap par blocs. Rapporter en particulier
le nombre de coefficients non nuls retenus par le lasso à chaque fold — **s'il change fortement d'un
fold à l'autre (ex. 3 séries retenues au fold 1, 9 au fold 2, aucune en commun), c'est un signe que le
$\lambda$ optimal capture du bruit d'échantillonnage plutôt qu'une vraie sparsité stable**, et le
shrinkage doit être abandonné au profit de 1/N ou de ridge pur (qui ne fait pas de sélection dure et
est donc moins sujet à cette instabilité).

---

## (b) Transformation en choc — du niveau à la surprise tradable

Un niveau macro composite $Z_{c,t}$ n'est pas ce qui bouge les prix : les marchés pricent en
continu l'information disponible, donc c'est l'écart entre le réalisé et ce qui était **déjà anticipé**
qui porte l'information nouvelle. Trois familles de construction du choc, de la plus simple à la plus
structurée :

### 6. Construction du choc

**6.1 — Écart au consensus (surprise standardisée).**
$SU_{i,t} = \dfrac{x_{i,t} - \hat{x}_{i,t}^{consensus}}{\sigma(x_i - \hat{x}_i^{consensus})}$, où le
dénominateur est l'écart-type historique des surprises passées de la série $i$ (standardized surprise
index, à la Balduzzi-Elton-Green / Andersen-Bollerslev-Diebold-Vega). **Hypothèse critique** : le
consensus (Bloomberg/Reuters median forecast) est une proxy raisonnable de l'attente de marché — c'est
l'hypothèse la plus fragile de toute la construction du choc, car (i) l'attente de marché peut diverger
du consensus des économistes (ils ne pricent pas nécessairement la même chose), et (ii) l'historique
de consensus est souvent payant/difficile d'accès pour un chercheur solo (Bloomberg ECO, Refinitiv —
hors budget probable). Alternative low-cost : utiliser un **modèle naïf de prévision** (AR(1) ou moyenne
des 3 dernières publications) comme proxy d'attente si le vrai consensus n'est pas disponible — moins
bon, mais réplicable et gratuit.

**6.2 — Résidu d'un modèle de prévision** (au lieu du consensus de marché, on construit sa propre
attente) : $SU_{i,t} = x_{i,t} - \hat{x}_{i,t}^{model}$, où $\hat{x}^{model}$ vient d'un AR(p),
d'un ARIMA, ou de la prévision du DFM §2 lui-même (le nowcast juste avant publication sert d'attente,
et l'écart entre publication et nowcast est le choc "nowcasting" — c'est la définition la plus propre
pour qui a déjà construit un DFM). Avantage : gratuit, réplicable, pas de dépendance à un vendor de
consensus. Inconvénient : ce résidu mesure la surprise par rapport à un modèle statistique, pas
nécessairement par rapport à l'attente du marché — les deux peuvent diverger si le marché a de
l'information non capturée par le modèle univarié (ex. guidance de banque centrale).

**6.3 — Innovation d'un filtre de Kalman.** Si le score-niveau est construit via le DFM §2, l'innovation
du filtre ($x_{i,t} - E[x_{i,t}\mid \mathcal{F}_{t-1}]$, disponible nativement en sortie du filtre de
Kalman) EST le choc, sans étape supplémentaire — c'est le sous-produit naturel de l'architecture à
espace d'états, cohérent avec §6.2 mais sans re-belle-estimation séparée.

**6.4 — Décomposition tendance/cycle (HP filter et ses critiques ; filtre de Hamilton 2018).** Le
filtre de Hodrick-Prescott décompose $x_t = \tau_t + c_t$ en minimisant
$\sum_t (x_t-\tau_t)^2 + \lambda \sum_t [(\tau_{t+1}-\tau_t)-(\tau_t-\tau_{t-1})]^2$. **Critique sévère
de Hamilton (2018, "Why You Should Never Use the Hodrick-Prescott Filter")** : (i) le filtre introduit
des dynamiques spurious dans le cycle extrait même si la série sous-jacente n'a aucune structure
cyclique réelle (artefact purement mécanique du lissage double) ; (ii) il souffre d'un problème de
fin d'échantillon sévère — le cycle estimé aux derniers points (précisément ceux qu'on veut trader en
temps réel) est instable et révisé fortement quand de nouvelles observations arrivent, ce qui est
disqualifiant pour un usage de signal temps réel ; (iii) le choix de $\lambda$ (1600 pour trimestriel,
14400 pour mensuel par convention) n'a aucune justification structurelle, c'est un artefact numérique
hérité. **Recommandation de Hamilton, reprise ici** : remplacer HP par sa régression de substitution —
régresser $x_{t+h}$ sur $(x_t, x_{t-1}, x_{t-2}, x_{t-3})$ (typiquement $h=8$ trimestres,
4 retards), le résidu de cette régression EST le "cycle" au sens de déviation par rapport à ce qui
était prévisible depuis $t-h$, et il ne souffre ni de l'artefact spurious ni de l'instabilité de fin
d'échantillon (c'est une régression OLS ordinaire, stable par construction). **Pour ce chercheur : ne
jamais utiliser HP comme composante d'un score déployé en production ; si une décomposition
tendance/cycle est nécessaire, utiliser directement la régression de Hamilton.**

**Test de falsification (choc, toutes variantes).** Le test non négociable est le test **two-sided
d'IJR appliqué au choc et non au niveau** : régresser le rendement excess futur sur le choc $SU_{i,t}$
séparément pour les sous-échantillons "surprise positive" et "surprise négative", HAC lag-6 sur chaque
branche. Si l'effet n'existe que d'un côté (ex. seules les mauvaises surprises bougent le prix, les
bonnes non), c'est cohérent avec un choc réel mais asymétrique (à documenter, pas à rejeter) — en
revanche si l'effet total n'existe QUE parce qu'une branche est en fait un habillage de la même chose
que le score de niveau (test de type L37 : le signe du choc coïncide avec le signe du niveau plus de
95% du temps ⇒ le "choc" est cosmétique, c'est le niveau redéguisé, nommer la sleeve pour ce qu'elle
est).

---

## (c) Dynamique — décroissance de l'information et paris indépendants

### 7. Noyaux de décroissance

**Formulation.** Une fois le choc $SU_{i,t}$ calculé à la date de publication, il faut décider combien
de temps il reste dans le score d'exposition. Trois familles de noyau :

- **Fenêtre rectangulaire** : $w_{i,t+h} = \mathbb{1}[0 \le h \le H]$ — le choc compte plein pendant
  $H$ jours puis disparaît d'un coup. Simple, mais discontinuité artificielle à $h=H$.
- **Décroissance exponentielle** : $w_{i,t+h} = \rho^h$, $\rho \in (0,1)$, équivalent à un EWMA du
  choc. Un seul paramètre (la demi-vie $= \ln(2)/\ln(1/\rho)$), lissage continu, standard en pratique.
- **Décroissance en loi de puissance** : $w_{i,t+h} = (1+h)^{-\alpha}$ — queue plus longue que
  l'exponentielle pour $\alpha$ petit, pertinent si l'on croit que l'information macro a un effet
  d'ancrage durable (ex. un choc d'inflation qui redéfinit l'anticipation de trajectoire de taux pour
  plusieurs mois) plutôt qu'un effet purement transitoire.

Le score d'exposition à la date $t$ est alors $E_t = \sum_i \sum_{h\ge 0} w_{i,h}\, SU_{i,t-h}$.

**⚠ Point central pour ce chercheur — effet du noyau sur le nombre de PARIS INDÉPENDANTS.**
Le nombre d'observations $T$ (nombre de jours de la série de score) n'est PAS le nombre de paris
indépendants dès lors que le noyau a une demi-vie non négligeable. Un score dont la demi-vie de
décroissance est de $\tau$ jours a une autocorrélation approximative $\text{Corr}(E_t, E_{t+1}) \approx
\rho = 2^{-1/\tau}$ (pour le noyau exponentiel), et par la formule de variance d'une moyenne de
processus AR(1), le **nombre de paris effectifs sur une fenêtre de $T$ jours** est approximativement

$$N_{\text{eff}} \approx T \cdot \frac{1-\rho}{1+\rho} \approx \frac{T}{2\tau/\ln 2}$$

(approximation standard pour $\rho$ proche de 1 : $N_{\text{eff}} \approx T (1-\rho)$, cf. la
correction déjà appliquée dans le dépôt sur une série de netflow ETH à demi-vie > 30 jours, où
$N_{\text{eff}} \approx 73$ sur $N=3398$ observations nominales — **facteur de déflation ~46x**). Concrètement :

| Demi-vie du noyau | $\rho$ (autocorr. lag-1, daily) | $N_{\text{eff}}$ sur $T=1000$ j |
|---|---|---|
| 1 jour | 0.50 | ~333 |
| 5 jours | 0.87 | ~67 |
| 20 jours (≈1 mois) | 0.966 | ~17 |
| 60 jours (≈1 trimestre) | 0.9886 | ~6 |

La conséquence pratique est directe et sévère : **plus le noyau est choisi "lent" pour capturer un
effet d'ancrage macro durable, plus le nombre de paris indépendants s'effondre, et plus le seuil de
significativité nominal (t>2, ou même le lag-6 de la HAC) devient trompeur** — HAC lag-6 corrige
l'autocorrélation jusqu'à 6 jours de décalage, ce qui est insuffisant dès que la demi-vie du noyau
dépasse quelques jours (il faudrait alors un HAC avec un nombre de lags comparable à la demi-vie, ce
qui réduit mécaniquement la puissance effective du test — un t-stat calculé avec 6 lags sur un
processus dont l'autocorrélation réelle s'étend sur 60 jours est simplement mal spécifié, pas
seulement "conservateur").

**Discipline à appliquer, dans l'ordre :**
1. Choisir la demi-vie du noyau AVANT de voir les résultats de performance (sur un fondement
   économique — ex. durée typique entre deux publications de la même série pour ce bloc macro — pas
   sur un balayage de grille suivi d'un choix du meilleur point, qui est une forme de data-mining pur
   sur le paramètre le plus dangereux de toute la construction).
2. Calculer $N_{\text{eff}}$ correspondant à la demi-vie choisie et l'utiliser pour dimensionner le
   HAC (lags $\gtrsim$ demi-vie en jours, pas un lag-6 fixe importé mécaniquement du reste du repo —
   le lag-6 est calibré pour des signaux à décroissance rapide, ce noyau macro à décroissance lente
   exige un lag adapté).
3. Rapporter systématiquement, à côté de tout Sharpe ou t-stat, le $N_{\text{eff}}$ effectif et non le
   $T$ nominal — c'est la même discipline que L47 (annualiser en $\sqrt{\text{obs/an}}$, jamais
   $\sqrt{252}$, sous peine de gonfler le Sharpe d'un facteur qui peut dépasser 2x) appliquée cette
   fois au nombre d'observations plutôt qu'à l'horizon d'annualisation.

**Test de falsification.** Comparer directement, sur la MÊME série de choc, un noyau rapide (demi-vie
1-5j) et un noyau lent (demi-vie 20-60j) en walk-forward, avec HAC dimensionné à chaque demi-vie
respective (pas HAC lag-6 fixe pour les deux, ce qui avantagerait artificiellement le noyau lent en
sous-estimant son erreur-type). Si le noyau lent ne domine le noyau rapide qu'à HAC lag-6 fixe mais
plus une fois le nombre de lags ajusté à sa propre demi-vie, c'est un artefact de mauvaise
spécification du test, pas un edge réel — préférer alors le noyau rapide, moins fragile.

---

## Pièges spécifiques au macro — traitement détaillé

### N effectif minuscule et puissance statistique honnête

25 ans de données trimestrielles = 100 observations nominales. Le nombre de **cycles économiques
complets** sur cette période est de l'ordre de 2 à 4 (selon le pays). Deux conséquences à traiter
explicitement, jamais implicitement :

- **Calcul de puissance ex ante, pas ex post.** Avant de lancer un test, calculer l'effet minimum
  détectable (MDE) compte tenu du $N_{\text{eff}}$ réel (pas nominal — voir §7) et du niveau de bruit
  observé dans le rendement cible. Si le MDE est plus grand que tout effet économiquement plausible
  (ex. MDE de 40 points de base par trade pour un edge macro dont la littérature suggère 5-10 points
  de base), le test est **structurellement sous-puissant** — un résultat non significatif ne doit pas
  être lu comme "pas d'edge" mais comme "test incapable de trancher", et un résultat significatif doit
  déclencher une suspicion accrue de faux positif (cf. la distinction du repo entre UNDERPOWERED et
  REJECTED — un ΔSR positif dans le bruit n'est pas un PASS, mais l'absence de significativité sur un
  test sous-puissant n'est pas non plus un kill).
- **Ne jamais citer un Sharpe/IC estimé sur un seul cycle** comme généralisable — le cycle 2020-2022
  (COVID + resserrement) a un profil macro totalement atypique, et un score calibré ou validé
  uniquement dessus n'apprend rien de généralisable. Exiger, dans le walk-forward ≥5 folds imposé par
  le repo, que les folds recouvrent **au moins deux régimes de politique monétaire distincts**
  (hausse et baisse de taux, pas seulement des sous-découpes temporelles d'un même régime) — sinon les
  5 folds ne sont walk-forward que nominalement, ils testent 5 fois la même chose.

### Horizons chevauchants (Hodrick, Newey-West et leurs limites)

Un rendement cumulé sur $k$ jours calculé à chaque jour ($r_{t\to t+k}$) chevauche ses voisins de
$k-1$ jours — c'est le cas typique quand on veut relier un choc macro à un rendement "sur l'horizon où
il devrait agir" plutôt qu'au rendement du lendemain seul. La correction Hodrick (1992, régression
inversée) ou Newey-West (HAC) sont les outils standards, mais **toutes deux dégradent fortement quand
le chevauchement $k$ devient grand relativement à $T$** :
- Newey-West avec $k$ lags perd de la puissance de façon quasi-linéaire en $k$ (l'estimateur de
  variance longue devient de plus en plus bruité lui-même à mesure que $k/T$ augmente), et au-delà
  de $k/T \approx 0.1$-$0.2$ les tables de référence indiquent une sur-couverture ou sous-couverture
  significative de l'intervalle de confiance nominal.
- Hodrick (1992) est en général mieux calibré que Newey-West en petit échantillon avec chevauchement
  important, mais reste une approximation asymptotique qui se dégrade pour $k$ très grand relativement
  à $T$ (le cas $k \sim T/4$, pas rare avec des chocs macro à effet trimestriel sur seulement quelques
  années de données, est hors du domaine de validité raisonnable de l'une ou l'autre méthode).
- **Conséquence opérationnelle** : au-delà d'un chevauchement $k > T/10$ environ, ne pas se fier au
  t-stat corrigé quelle que soit la méthode — rééchantillonner en observations NON chevauchantes
  (une observation tous les $k$ jours) et accepter la perte de puissance qui en résulte plutôt que de
  publier un t-stat dont la calibration est hors de son domaine de validité. C'est plus honnête qu'un
  chiffre précis mais mal calibré.
- Corollaire pour le bootstrap par blocs imposé par le repo : la taille de bloc doit être **au moins
  aussi longue que $k$** (le chevauchement), sinon le bootstrap casse artificiellement la dépendance
  qu'il est censé préserver et redevient, de facto, un bootstrap quasi-iid déguisé.

### Fuite par les révisions

Toute série macro publiée est révisée (souvent 2-3 fois : preliminary → revised → final, parfois des
révisions annuelles de base). Le piège : si le score utilise la valeur **finale** (celle disponible
aujourd'hui dans un data provider standard type FRED sans vintage) à une date $t$ historique, il utilise
de l'information qui n'était pas connue à $t$ — c'est un leak, structurellement identique à une
violation du "signal à T-1, trade à T" du reste du repo, sauf qu'il est beaucoup plus facile à
manquer parce qu'il ne saute pas aux yeux dans le code (le bug n'est pas dans l'alignement temporel des
lignes, il est dans le CONTENU de la cellule).

**Protocole obligatoire** : utiliser une base de données à vintages (ALFRED pour les séries US ; pour
les séries non-US, à défaut de vintage complet, reconstruire une approximation par la différence entre
la première publication et la publication à N mois, disponible via les archives de communiqués de
presse officiels — plus lourd mais faisable) ; documenter explicitement, pour chaque série entrant
dans le score, si elle est en "première publication" (préféré, réplicable en temps réel) ou en
"valeur actuelle avec risque de leak" (dégradé, à ne jamais utiliser sans vintage sauf pour une étude
exploratoire dont on sait qu'elle surestime la performance et qu'il faudra revalider en first-release
avant tout déploiement).

**Test de falsification** : reconstruire le score en deux versions (first-release vintages vs valeurs
actuelles révisées) sur la période où les deux sont disponibles, et comparer l'IC des deux versions. Si
l'IC en valeurs révisées est significativement supérieur à l'IC en first-release, l'écart EST la
mesure de la fuite par révision — ne jamais publier ou déployer le chiffre en valeurs révisées comme
performance attendue.

### Tendances communes entre pays — 10 pays ne font pas 10 observations indépendantes

Un score macro par devise appliqué à un panel de paires (EURUSD, GBPUSD, AUDUSD, …) partage souvent un
facteur commun global (cycle du dollar, appétit pour le risque global, cycle de resserrement monétaire
synchronisé post-2022) qui traverse toutes les paires simultanément. Empiler les t-stats "un par paire"
et les traiter comme $N=10$ tests indépendants pour un test AMTP (Šidák) est une erreur de comptage :
le n_tests effectif à corriger est plus proche de 1-3 (le nombre de facteurs communs réels) que de 10.

**Protocole** : avant tout calcul AMTP/Šidák sur un panel multi-paires, estimer la corrélation
cross-sectionnelle des résidus du score (ou des rendements des sleeves individuelles) — si la
corrélation moyenne inter-paires est élevée (>0.3-0.4 selon la fenêtre), réduire le n_tests effectif en
conséquence (à défaut d'un calcul formel du nombre de facteurs, utiliser une règle de type
$N_{\text{eff,tests}} \approx N / (1 + (N-1)\bar{\rho})$, analogue à la formule d'Poisson pour l'effectif
d'un portefeuille corrélé). Documenter ce calcul dans le registre de test — c'est la même discipline que
le repo applique déjà au niveau des instruments individuels (N≥30 pour les stratégies cross-sectionnelles
précisément parce qu'un petit N sous une forte corrélation cross-sectionnelle ne donne pas la
diversification qu'un N nominal suggérerait).

### Sélection de spécification et degrés de liberté du chercheur

Le nombre de choix disponibles à chaque étape (fenêtre de z-score, poids égal vs optimisé, forme du
choc, demi-vie du noyau, nombre de facteurs du DFM, $\lambda$ de shrinkage, seuils de régime) est
énorme, et chacun peut être ajusté après avoir vu un résultat. C'est le terrain le plus fertile pour
un faux positif macro, précisément parce que la sophistication apparente de la méthode (DFM, MIDAS,
Markov-switching) masque le nombre réel de essais implicites derrière un seul "run" apparent.

**Discipline, reprenant la méthode déjà en vigueur dans le repo** (méthode des variantes exhaustives) :
- Toute famille d'estimateurs doit être testée comme une **grille pré-enregistrée**, pas comme une
  spec unique choisie a priori puis retouchée. Écrire la grille AVANT de voir un seul résultat de
  performance (fenêtres de z-score $w \in \{...\}$, demi-vies $\tau \in \{...\}$, etc.), et lire la
  DISTRIBUTION des t-stats sur toute la grille, jamais le maximum.
- Chaque combinaison testée compte comme un essai dans le décompte AMTP/DSR du dépôt — le chercheur
  doit budgéter ce compte AVANT de lancer la grille (une grille de 5 fenêtres × 3 demi-vies × 2
  pondérations = 30 essais à faire entrer dans n_tests, même si un seul chiffre final est retenu).
- Le test de falsification le plus général contre ce piège est le **placebo apparié à la Hamilton/L58** :
  construire un score placebo qui a la MÊME structure d'autocorrélation et la MÊME complexité de
  spécification que le score réel (même grille de paramètres balayée), mais sur des données macro
  aléatoirement permutées entre pays ou décalées d'un cycle complet — si le placebo produit des t-stats
  significatifs à un taux comparable au score réel une fois la meilleure spec choisie sur les deux, la
  significativité du score réel est un artefact de la richesse de la grille, pas un edge. Ce test doit
  être exécuté et rapporté pour CHAQUE famille d'estimateur retenue, pas seulement en fin de pipeline.

---

## Recommandation hiérarchisée — par où commencer, et jusqu'où aller

**Recommandation franche : commencer par la méthode simple (§1, z-score composite égal-pondéré +
surprise standardisée §6.1/6.2 + noyau exponentiel §7 à demi-vie courte pré-enregistrée), et ne
complexifier QUE si cette méthode simple échoue un test spécifique et identifiable — jamais par
principe de sophistication.** Pour un chercheur solo, la contrainte qui domine n'est presque jamais la
puissance économétrique de l'estimateur, c'est le $N_{\text{eff}}$ macro et la discipline de test — un
DFM mal validé sur un $N_{\text{eff}}$ de quelques dizaines n'est pas plus fiable qu'un z-score mal
validé, il est juste plus difficile à auditer et donne une fausse impression de rigueur par le volume
de code qu'il représente.

**Séquence de complexification, avec le déclencheur explicite de passage à l'étape suivante :**

1. **Étape 0 — z-score composite égal-pondéré (§1) + surprise standardisée par résidu AR(1) (§6.2) +
   EWMA à demi-vie courte pré-enregistrée (§7, ex. 5-10 jours pour un score conçu pour moduler un book
   qui rebalance à l'échelle de la semaine).** Coût : quelques jours. Ceci doit être le score de
   référence contre lequel tout le reste se compare — jamais l'inverse.
2. **Déclencheur vers l'étape 1 (rétrécissement, §5)** : uniquement si le test de falsification §1(ii)
   (DeMiguel apparié) montre qu'une pondération optimisée bat significativement 1/N en OOS walk-forward
   — ce qui, compte tenu du $N$ de séries et du $T$ probable, est un résultat que je n'anticipe PAS pour
   ce chercheur avec un panel de 10-20 séries et quelques centaines d'observations utiles. Coût
   marginal : faible (ridge/elastic net avec TimeSeriesSplit, quelques jours de plus).
3. **Déclencheur vers l'étape 2 (DFM/nowcasting, §2)** : uniquement si (i) le panel de séries d'entrée
   dépasse réellement 15-20 séries hétérogènes en fréquence et retard de publication, ET (ii) le test
   de falsification §2 ($R^2$ facteur DFM vs z-score composite) montre une divergence substantielle
   documentée sur un premier prototype léger. Sans ces deux conditions réunies, le ROI du DFM est
   négatif pour un chercheur solo — c'est la famille au plus mauvais ratio coût/preuve de valeur
   ajoutée compte tenu de l'échelle probable du problème (score par devise/paire, pas nowcasting
   multi-pays industriel type banque centrale).
4. **MIDAS (§3)** : à réserver à un besoin précis et différent — relier une série HF propre (spread de
   swap, différentiel de taux) à une cible LF, pas comme méthode d'agrégation générale du score. Ne
   l'introduire que si un besoin de ce type précis se présente, pas en remplacement de §1.
5. **Markov-switching (§4)** : traiter comme un OVERLAY optionnel de fin de chaîne, jamais comme le
   score lui-même, et seulement après avoir exécuté et documenté explicitement le test moyenne/variance
   de la section §4 — l'historique du dépôt (L54) montre que c'est le piège le plus probable de toute
   cette liste pour ce chercheur en particulier, donc le garde-fou doit être non négociable avant tout
   déploiement, même en fin de chaîne.
6. **HP filter (§6.4)** : à ne jamais utiliser en production, quel que soit le stade — remplacer
   systématiquement par la régression de Hamilton (2018) si une décomposition tendance/cycle est
   requise à un stade quelconque de la chaîne.

**Position franche sur la suffisance de la méthode simple.** Je pense que pour l'usage visé (moduler ou
piloter un book personnel/FTMO, pas un desk de nowcasting institutionnel), l'étape 0 seule, correctement
testée avec la discipline $N_{\text{eff}}$ + placebo apparié + walk-forward ≥5 folds à régimes
distincts, a une probabilité non négligeable de suffire ou d'échouer proprement (ce qui est déjà un
résultat utile — un score simple qui échoue proprement ferme la famille sans consommer le budget
d'implémentation du DFM). La valeur marginale du DFM ou de MIDAS pour CE cas d'usage précis est
probablement plus dans la légitimité académique de la méthode que dans un gain d'IC mesurable une fois
le $N_{\text{eff}}$ correctement compté — et la sophistication ajoute des degrés de liberté de
spécification supplémentaires (§ "sélection de spécification" ci-dessus) qui, pour un budget de tests
déjà contraint par le n_tests global du dépôt, peuvent coûter plus cher en pouvoir de détection future
qu'ils ne rapportent en qualité de score.

---

*Fin du document de spécification. Aucun test décrit ci-dessus n'a été exécuté ; ce document ne
contient aucune donnée ni résultat empirique.*
