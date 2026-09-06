# Axe C — Dispersion cross-sectionnelle & flux d'acteurs contraints

**Round** macro_round2_2026-09 · **Rôle** : attaque directe du problème de breadth (2-15 paris indépendants/an au lieu de ~240 comptés naïvement, cause : cycle macro synchronisé entre pays + facteur dollar omniprésent).
**Statut** : revue de littérature + spécification + calcul de breadth. Aucun backtest, aucune donnée téléchargée, aucun verdict rendu — ce document arme le test suivant, il ne le remplace pas.

---

## 0. Résumé exécutif

1. Le calcul (§3.4) donne une réponse nette à la question centrale : **la façon de différencier détermine tout**. Différencier chaque pays contre un même pivot (« vs USD », « vs EUR ») ne résout RIEN — la corrélation résiduelle entre paires plafonne mécaniquement à **0.5** et la breadth effective **converge vers 2, quel que soit le nombre de pays ajoutés**. C'est very probablement le mécanisme exact qui produit le « facteur dollar omniprésent » identifié par le round précédent. À l'inverse, un **démeanage cross-sectionnel** (soustraire chaque période la moyenne de l'univers, pas un pivot unique) élimine le facteur commun exactement sous des hypothèses simples et ramène la breadth théorique à **N−1**, avec corrélation résiduelle négative **−1/(N−1)**.
2. Ce gain est **mécanique, pas économique** : rien ne garantit que le résidu après démeanage porte un signal. La littérature de dispersion (Eriksen 2020 ; NBER w26329) montre que la dispersion cross-sectionnelle EST corrélée aux rendements — mais c'est une observation contemporaine/de risque, pas une preuve de pouvoir prédictif OOS du résidu pays-spécifique. Le point de bascule du volet 1 est donc empirique et vient APRÈS la construction : test IC sur le résidu, pas sur le niveau (§3.5, F4).
3. Volet 2 : le seul flux publié **avant** l'exécution de l'acteur contraint (donc réellement tradable, pas juste un conditionneur a posteriori) est le **calendrier de rebalancement / reconstitution / adjudication** — daté par construction, avant tout signal de marché. Le **COT** est publié avec 3 jours de retard sur la donnée (Tuesday close, vendredi 15h30 ET) : utilisable seulement comme filtre de régime lent (horizon ≥1-2 semaines), jamais comme déclencheur. **TIC** est mensuel et encore plus stale — outil de contexte macro, pas de trading.
4. Le rebalancement daté (pension/indices) est la structure la plus propre sur le papier (dose + acteur forcé + fenêtre bornée) mais la littérature documente elle-même sa **décroissance** (front-running croissant, Russell effect affaibli post-2010). Les adjudications du Trésor ont le même profil de décroissance ET le dépôt a déjà buté sur un piège de placebo exactement sur ce terrain (L58, saisonnalité jour-du-mois masquée par un blackout mal conçu) — ne pas répéter ce test sans corriger le contrôle.
5. Véhicule : le hard rule N≥30 pour toute stratégie cross-sectionnelle **entre en collision directe avec les €13k de capital** si l'on utilise des futures FX pleine taille (marge ~$2-3k/contrat × 30 legs). Seuls les **micro-futures CME (M6E, M6A, M6B, M6J, M6C, M6S, M6N…)** rendent la construction admissible au véhicule. La jambe taux (ZN/Bund/Gilt) ne peut pas atteindre N≥30 seule — elle doit être traitée comme sleeve discrétionnaire séparée, pas comme stratégie CS autonome.

---

## 1. Rappel du problème et cadrage de l'axe

Le round précédent a établi que le score macro naïf compte ~240 paris/an (un par pays par mois, disons) mais que la breadth effective réelle tourne autour de **2 à 15**. Deux causes citées : (a) synchronisation du cycle macro entre pays, (b) omniprésence du facteur dollar dans les paires FX. Ces deux causes sont en réalité **la même cause vue sous deux angles** — un facteur commun qui charge quasi tous les instruments — et c'est ce que le §3.4 formalise.

Ce rapport ne cherche PAS à prouver que l'axe passe. Il :
- construit le calcul qui dit si la différenciation aide, de combien, et sous quelles conditions ;
- inventorie les flux d'acteurs contraints candidats et classe lesquels sont réellement tradables avant l'événement ;
- propose la version la plus forte de la construction, avec le véhicule qui la rend admissible à €13k ;
- liste ce qui la falsifierait, point par point.

---

## 2. Volet 1 — Littérature

### 2.1 Facteurs communs et cycles synchronisés

Les modèles à facteurs dynamiques appliqués aux cycles internationaux (Kose, Otrok & Whiteman 2003 ; Kose, Otrok & Prasad 2012 ; IMF WP/16/54) décomposent la variance des agrégats macro (output, plus rarement inflation/surprises) en un **facteur mondial**, des **facteurs de groupe/région**, et un **facteur idiosyncrasique pays**. Les résultats varient selon l'échantillon et la période mais le message qualitatif est stable :
- Le facteur mondial explique une part substantielle de la variance des pays industrialisés et des secteurs exposés au commerce international — plus que pour les émergents pris isolément.
- La part expliquée par le facteur de GROUPE (région) a AUGMENTÉ avec la globalisation — de l'ordre de 17 % à 30 % pour les pays industrialisés selon l'IMF WP/16/54 — ce qui veut dire que même après avoir retiré le facteur mondial, il reste un **sous-facteur régional** (zone euro, bloc exportateur asiatique) qui recorrèle les résidus entre pays voisins.
- Les spillovers financiers (comovements des marchés actions et immobiliers) ajoutent un canal de corrélation supplémentaire, distinct du canal macro pur.

Implication directe pour le calcul du §3.4 : l'hypothèse « résidu idiosyncrasique iid entre pays » est une IDÉALISATION. La réalité a un sous-facteur régional résiduel — la breadth réelle après démeanage sera donc **inférieure à N−1**, quelque part entre le plancher hub-and-spoke (~2) et le plafond démeanage idéal (N−1), selon la force du sous-facteur régional mesurée empiriquement.

### 2.2 Méthodes de retrait du facteur commun

Trois familles, par ordre de sophistication croissante :
1. **Pivot unique (hub-and-spoke)** : chaque série est exprimée relativement à UN référentiel commun (« vs USD », « vs EUR », « vs moyenne G7 fixe »). C'est la construction FX standard (paires vs USD) et c'est probablement la source du problème « facteur dollar omniprésent » cité par le round précédent — cf. calcul §3.4.
2. **Démeanage cross-sectionnel** : à chaque date, soustraire la moyenne (ou médiane, ou moyenne pondérée) de l'univers à chaque série. Équivalent à retirer le premier facteur principal SI les corrélations entre pays sont approximativement égales (structure équicorrélée) — hypothèse standard en gestion de portefeuille cross-sectionnelle (neutralisation beta-du-marché).
3. **Modèle à facteurs explicite (PCA / facteur global-local à la Kose-Otrok)** : extraire le premier composant principal (ou le facteur latent d'un modèle dynamique) et travailler sur le résidu de régression de chaque série sur ce facteur. Plus flexible (gère les β_i hétérogènes) mais nécessite une estimation glissante (walk-forward) du facteur — risque de look-ahead si le facteur est estimé en pleine période puis appliqué rétroactivement (piège classique, à traiter avec un PCA glissant strictement out-of-sample).

Le §3.4 traite formellement les cas 1 et 2 (fermés analytiquement) ; le cas 3 est en pratique un raffinement du cas 2 quand β_i hétérogène — il ne change pas la conclusion qualitative, il l'améliore marginalement au prix d'une fenêtre d'estimation.

### 2.3 Dispersion cross-sectionnelle comme signal en elle-même

- Eriksen (2020, *Journal of Empirical Finance* / SSRN 3001681) : la dispersion cross-sectionnelle des rendements de change est **priced** dans le cross-section du momentum devises — une hausse inattendue de la dispersion est associée à des rendements positifs pour les devises « gagnantes » et négatifs pour les « perdantes ». C'est un résultat de type risque (la dispersion se comporte comme un facteur de risque conditionnel), pas un signal de niveau country-specific.
- NBER w26329 (« Cross-Sectional Dispersion of Risk in Trading Time ») : dispersion comme mesure de risque en temps de transaction, littérature adjacente mais pas macro-surprise à proprement parler.
- Macrosynergy (recherche appliquée, pas peer-reviewed mais méthodologiquement transparente) documente des constructions « double-relative » : score d'un pays moins le score de son groupe de référence, puis écart de ce différentiel à la moyenne cross-sectionnelle du panier — exactement la construction en deux étages (pivot régional PUIS démeanage) qui, par le calcul du §3.4, est supérieure à un simple pivot mais reste bornée par la taille du sous-panier régional utilisé au premier étage.

**Lecture combinée** : la dispersion cross-sectionnelle est un objet statistiquement établi et mesurable. Ce que la littérature établit est une corrélation dispersion↔rendement **contemporaine ou à très court terme**, pas un pouvoir prédictif du résidu idiosyncrasique pays-spécifique après retrait explicite d'un facteur macro mondial mesuré (ce qui est la construction proposée ici). C'est un écart réel entre ce qui est publié et ce qu'il faudrait démontrer — traité comme falsificateur central en §3.5/F4.

---

## 3. Volet 1 — Le calcul (question centrale du brief)

### 3.1 Modèle

Soit N pays/instruments. Pour chaque période :

```
X_i = β·F + ε_i,     F ~ (0, 1),     ε_i ~ iid (0, σ²),     Cov(F, ε_i) = 0
```

`F` est le facteur mondial (cycle macro global, ou la composante dollar commune à toutes les paires FX). `β` identique pour tous les pays (hypothèse simplificatrice — cf. §2.1 pour la limite de cette hypothèse). La corrélation entre deux niveaux bruts est alors :

```
ρ = Corr(X_i, X_j) = β² / (β² + σ²)          pour TOUTE paire i≠j
```

C'est la source directe du problème de breadth : **toutes les paires ont la même corrélation ρ**, quel que soit N. La formule de breadth effective standard (portefeuille équicorrélé) :

```
N_eff = N / (1 + (N-1)·ρ)
```

Avec N=30 et ρ=0.7 (facteur mondial dominant, cas plausible pour le cycle macro selon §2.1) : N_eff = 30/(1+29×0.7) = 30/21.3 ≈ **1.4**. Avec ρ=0.5 : N_eff ≈ **1.9**. Avec ρ=0.3 : N_eff ≈ **3.1**. Cette fourchette (1.4 à 3.1 pour ρ entre 0.3 et 0.7) est cohérente avec le bas de la fourchette « 2-15 » citée par le round précédent — et suggère que le book actuel opère probablement dans la zone ρ élevé (0.5-0.7), pas dans la zone ρ faible.

### 3.2 Construction 1 — Pivot unique (hub-and-spoke)

Chaque « spoke » i est différencié contre un même pivot p (ex. USD) : `D_i = X_i - X_p = ε_i - ε_p` (le facteur commun s'annule EXACTEMENT si β homogène — c'est le point positif). Mais tous les D_i PARTAGENT la jambe ε_p :

```
Cov(D_i, D_j) = Cov(ε_i - ε_p, ε_j - ε_p) = Var(ε_p) = σ²     (i≠j, tous deux ≠ p)
Var(D_i) = Var(ε_i) + Var(ε_p) = 2σ²
Corr(D_i, D_j) = σ² / 2σ² = 0.5      EXACTEMENT, indépendamment de ρ, de β, de σ, et de N
```

**C'est le résultat clé.** La corrélation résiduelle entre deux paires qui partagent un pivot commun est un **plancher mécanique de 0.5**, qui ne dépend même pas de la force du facteur mondial retiré — il vient uniquement du fait que la jambe pivot est réutilisée partout. En breadth effective :

```
N_eff(hub) = N / (1 + (N-1)×0.5)  →  converge vers 2 quand N → ∞
```

N=10 spokes : N_eff ≈ 1.8. N=30 spokes : N_eff ≈ 1.9. N=100 : N_eff ≈ 2.0. **Ajouter des devises au panier « vs USD » n'augmente quasiment jamais la breadth au-delà de ~2, aussi loin qu'on aille.** C'est un plafond dur, pas asymptotique-lent — il est déjà atteint à N=10.

⚠ **Interprétation directe pour le round précédent** : si le facteur dollar est cité comme cause de la breadth faible, c'est probablement PARCE QUE la construction usuelle (paires FX cotées vs USD, ou scores macro « vs benchmark US ») EST une construction hub-and-spoke — et donc mécaniquement plafonnée à N_eff≈2 quel que soit le nombre de devises suivies. Ce n'est pas un problème de signal, c'est un problème de **choix de référentiel**.

### 3.3 Construction 2 — Démeanage cross-sectionnel

Au lieu d'un pivot unique, on soustrait à chaque date la moyenne de l'univers : `Y_i = X_i - X̄` où `X̄ = (1/N)Σ X_k`.

```
Y_i = X_i - X̄ = (β·F + ε_i) - (β·F + ε̄) = ε_i - ε̄        (le facteur F s'annule EXACTEMENT, sans dépendre d'un pivot)

Var(Y_i) = σ²(N-1)/N
Cov(Y_i, Y_j) = -σ²/N          (i≠j)
Corr(Y_i, Y_j) = -1/(N-1)      EXACTEMENT
```

Avec N=30 : corrélation résiduelle ≈ **−0.034** — quasi nulle, et légèrement NÉGATIVE (mécanique : la somme des résidus démeanés est identiquement nulle par construction, donc ils ne peuvent pas tous être positivement corrélés). Le rang de la matrice de covariance de {Y_i} est **N−1**, pas N (une contrainte linéaire exacte). Donc :

```
Breadth théorique(démeanage) = N - 1        (contre ~2 pour le hub-and-spoke, à N=30)
```

**C'est un gain de breadth de plus d'un ordre de grandeur sur le papier**, purement par changement de référentiel — aucune donnée nouvelle, aucun signal nouveau, juste soustraire la moyenne de l'univers au lieu d'un pivot fixe. C'est mathématiquement gratuit.

### 3.4 Pourquoi ce n'est PAS gratuit en pratique — les trois entorses au modèle

1. **β hétérogène.** Si β_i diffère entre pays (plausible — certains pays sont plus « beta au cycle mondial » que d'autres, cf. §2.1 secteurs tradeables), le démeanage ne retire pas exactement le facteur commun : un résidu de facteur subsiste, proportionnel à (β_i − β̄). Le gain de breadth se dégrade vers le résultat du §2.1 : un sous-facteur régional (17-30 % de la variance selon IMF WP/16/54) recorrèle les Y_i à l'intérieur des blocs (zone euro, bloc export asiatique). **La breadth réelle attendue est donc entre 2 (plancher hub) et N−1 (plafond démeanage idéal), probablement plus proche du bas si les blocs régionaux sont larges et peu nombreux** (ex. univers G10 dominé par 3-4 blocs seulement → breadth réelle proche de 4-8, pas de 9).
2. **ε_i pas nécessairement porteur de signal.** Le calcul ci-dessus est un calcul de VARIANCE/CORRÉLATION, pas de pouvoir prédictif. Que ε_i soit peu corrélé à ε_j ne dit rien sur si ε_i (la surprise macro purement pays-spécifique, nette du cycle mondial) prédit quoi que ce soit sur le rendement relatif futur. Or c'est précisément ce que la littérature de dispersion (§2.3) ne démontre pas directement — elle montre une relation contemporaine dispersion↔rendement, pas un IC out-of-sample du résidu pays-spécifique. **Le gain de breadth calculé ici est nécessaire mais pas suffisant : il faut un test IC séparé sur le résidu (falsificateur F4, §5).**
3. **Arbitrage indépendance/signal — la question posée par le brief.** Sous les hypothèses idéalisées ci-dessus (ε_i iid, homoscédastique), il n'y a PAS d'arbitrage mécanique entre indépendance et rapport signal/bruit par PAIRE : si on décompose ε_i = s_i + η_i (signal pays-spécifique vrai + bruit d'estimation, indépendants entre pays), le démeanage donne Y_i = (s_i − s̄) + (η_i − η̄), et sous les mêmes hypothèses d'homogénéité, le ratio Var(signal)/Var(bruit) dans Y_i est **identique** à celui dans ε_i brut — le démeanage multiplie signal et bruit par le même facteur, il ne dilue ni n'enrichit le SNR par unité. **L'arbitrage réel n'est donc pas un affaiblissement du signal — c'est un risque de destruction du signal si les DEUX jambes d'une paire portent le même signal** (ex. on soustrait la moyenne d'un panier qui contient déjà le pays qu'on trade, ou on démeanage sur un sous-groupe dont les membres ont des surprises pays-spécifiques corrélées entre elles pour des raisons non captées par le facteur mondial retiré — un choc commun sectoriel, une crise régionale). C'est exactement le test de β-orthogonalité (L38 du dépôt) appliqué au résidu, pas au niveau.

**Verdict du calcul, sans rendre de verdict sur la stratégie** : la construction hub-and-spoke usuelle est probablement la cause directe (ou une cause majeure) du plafond de breadth observé, et le démeanage cross-sectionnel offre un gain mathématique réel et gratuit — mais ce gain n'est monétisable que si le résidu porte un signal indépendamment testé, et sa taille réelle dépend d'un sous-facteur régional qu'il faut mesurer, pas supposer nul.

---

## 4. Volet 2 — Flux d'acteurs contraints

### 4.1 CFTC Commitments of Traders (COT)

- **Littérature** : Bessembinder & Chan (1992, *Journal of Finance*) — pouvoir prédictif significatif des positions commerciales (hedgers), surtout aux extrêmes. Travaux plus récents (stock market influence, JKU epub ; ML approach, PM-Research) confirment une significativité statistique mais soulignent une **magnitude économique limitée**. Études sectorielles (agricoles, énergie) : résultats mitigés selon l'instrument.
- **Calendrier de publication — le point décisif** : la donnée porte sur les positions de MARDI, transmise par les déclarants mercredi matin, publiée vendredi 15h30 ET. **Décalage de 3 jours calendaires entre l'état réel du positionnement et sa publication.** Conséquence directe pour la question du brief (« quels flux sont observables à l'avance ») : le COT n'est **jamais** un déclencheur exploitable à horizon court — au moment où vous le lisez, le positionnement qu'il décrit a déjà 3 jours et le marché a eu tout le loisir de réagir. Il n'est utilisable que comme **conditionneur de régime lent** (z-score de positionnement extrême, filtre sur un horizon ≥1-2 semaines), jamais comme signal same-week. Note dépôt : le registre L (regime_markov_sleeves 2026-07) a déjà falsifié un overlay de régime basé sur un mécanisme proche (orthogonalité) — tout nouveau test COT doit d'abord passer le test L38 avant même le test de timing.

### 4.2 Flux TIC (Treasury International Capital)

- Données mensuelles, publiées avec un délai typique de ~6 semaines après la fin du mois. Utilité documentée : identification des flux étrangers vers les bons du Trésor et leur lien avec les rendements/le dollar (dont un papier récent sur les flux OFFICIELS et l'impact sur les taux). Mais le délai de publication rend TIC **structurellement inadapté comme signal tradable** — c'est un outil de contexte macro trimestriel/semestriel (caractérisation de régime, pas de trigger). Encore plus stale que le COT (6 semaines vs 3 jours) : à exclure de tout signal actif, à réserver à de l'analyse de régime a posteriori si besoin.

### 4.3 Rebalancements datés — pension funds, reconstitution d'indices

C'est la catégorie la plus prometteuse EN THÉORIE, car c'est la seule où la **date** de l'action est connue AVANT que l'action n'ait lieu (pas seulement publiée après) :
- **Pension funds** (NBER w33554, Harvey et al. ; CFA Institute 2025) : rebalancement calendaire mensuel/trimestriel documenté, mécanique connue (vendre les actions qui ont surperformé, acheter les obligations sous-pondérées), impact mesuré ≈ **−17 bps sur le rendement actions le jour suivant** pour un rebalancement typique, coût total estimé à **$16 milliards/an** pour les fonds eux-mêmes (soit une estimation directe de ce que le front-running capture). Le point clé : « la prévisibilité du signal calendaire concentre l'effet en fin de mois », et **les trades sont publics par construction** (politique de rebalancement transparente pour beaucoup de fonds).
- **Reconstitution d'indices (Russell, S&P)** : effet de prix bien documenté historiquement (le portefeuille long-ajouts/short-retraits Russell 3000 a rendu ~14.94 % en juin sur 1996-2002), MAIS la littérature elle-même note que **l'effet s'est affaibli dans les années récentes** — un effet de retour post-reconstitution « much smaller to nonexistent in recent years » selon plusieurs études. Interprétation directe : structure quasi-idéale (dose observable — les additions/retraits sont annoncées avant la date effective — acteur forcé — les fonds indiciels DOIVENT trader à la date de reconstitution — fenêtre bornée) mais **la plus arbitrée**, précisément parce qu'elle est la plus documentée depuis 20+ ans. Tout angle sur les indices majeurs US (S&P 500, Russell 3000) est probablement déjà mort de concurrence ; un angle résiduel n'existerait que sur des indices moins suivis (indices européens mid-cap, indices émergents) — à vérifier, pas à supposer.

### 4.4 Adjudications du Trésor

- Littérature (NY Fed staff report ; ECB WP 2208 Sigaux ; Somogyi/FRBSF) : effet de pression de prix intraday autour des adjudications bien identifié (forme en V inversé, concession pré-adjudication puis reprise), mais **magnitude en baisse** — les fonds d'investissement non-dealers absorbent de plus en plus l'offre, réduisant le pouvoir explicatif des contraintes de bilan des dealers historiquement citées comme mécanisme.
- ⚠ **Le dépôt a déjà buté sur ce terrain exact.** L58 (registre du dépôt, 07-30) documente qu'un placebo apparié autour du cycle d'adjudication ZN a produit un **faux PASS** : la fenêtre de blackout ±3 jours a accidentellement retiré 38 % des jours centrés en milieu de mois, période où existe une forte saisonnalité jour-du-mois indépendante (jours 16-20 : −10.79 bps, t −3.38) — confondant blackout et saisonnalité calendaire. **Ne pas répéter ce test sans corriger le contrôle** (comparer contre l'espérance INCONDITIONNELLE de la forme de trade, pas contre un placebo calendaire qui peut lui-même être biaisé). L'angle non encore testé serait d'utiliser directement l'**annonce de taille** (publiée par le Trésor plusieurs semaines à l'avance, quantité connue) comme conditionneur de la position when-issued, plutôt qu'un simple filtre temporel autour de la date — un mécanisme différent de celui déjà falsifié, mais qui doit passer le même contrôle de saisonnalité jour-du-mois avant d'être crédité.

### 4.5 Opérations de banques centrales annoncées

Interventions FX, opérations de contrôle de courbe (BOJ YCC), achats d'actifs programmés (PEPP quand actif) : profil dose+acteur forcé+fenêtre excellent en théorie (mandat + calendrier souvent pré-annoncé), mais fréquence intrinsèquement faible — quelques événements exploitables par an et par banque centrale. Agréger plusieurs banques centrales élargit un peu l'échantillon mais ne résout pas le problème de breadth : cela ne fait que déplacer le problème « peu d'événements indépendants » d'un pays vers un petit groupe de pays, sans en changer l'ordre de grandeur (toujours à un chiffre ou bas de fourchette, cohérent avec le "2-15/an" déjà mesuré par le round précédent).

### 4.6 Fixing / flux de couverture des exportateurs

Le dépôt a déjà fermé cette famille (L23/L23b) : edge adossé à un fixing élargi (BIS WMR fév. 2015, passage 1min→5min) puis MiFID II 2018, non prédictif post-réforme. Aucun élément de la revue de littérature menée ici ne suggère un angle post-2018 différent de celui déjà testé et fermé. **Conformément à la consigne, je ne force pas de réouverture** — la famille reste fermée jusqu'à ce qu'un angle véritablement nouveau soit identifié en dehors de ce round.

### 4.7 Synthèse — observable avant vs après (tableau)

| Flux | Latence publication | Tradable ex-ante ? | Rôle admissible |
|---|---|---|---|
| COT (CFTC) | 3 jours (mardi→vendredi) | Non pour trigger ; oui pour régime lent | Conditionneur horizon ≥1-2 sem., jamais déclencheur |
| TIC (Trésor US) | ~6 semaines | Non | Contexte macro seulement |
| Rebalancement pension mensuel/trimestriel | Date connue À L'AVANCE, montant estimable en temps réel | **Oui — le seul flux vraiment ex-ante** | Signal daté direct |
| Reconstitution d'indice | Date d'annonce connue avant date effective | Oui en théorie, probablement arbitré sur indices majeurs US | Signal daté, angle résiduel seulement sur indices peu suivis |
| Adjudication Trésor | Calendrier + taille annoncés à l'avance | Oui en théorie | Signal daté, MAIS piège de contrôle déjà rencontré (L58) — corriger avant retest |
| Opérations banque centrale | Souvent pré-annoncées | Oui en théorie | Signal daté, mais breadth intrinsèquement faible |
| Fixing/exportateurs | N/A | Fermé (L23/L23b) | Aucun — pas d'angle post-2018 trouvé ici |

---

## 5. La meilleure version — spécification et falsificateurs

### 5.1 Construction proposée (hypothèse à tester, pas un verdict)

- **Univers** : ≥30 instruments FX (G10 + un bloc EM liquide) pour satisfaire le hard rule N≥30 cross-sectionnel.
- **Signal de niveau** : score de surprise macro par pays (construit maison : surprises de taux directeur + surprises PMI/inflation, normalisées), STRICTEMENT à T-1.
- **Retrait du facteur commun** : démeanage cross-sectionnel à chaque date (§3.3), PAS un pivot USD/EUR unique (§3.2) — c'est le choix qui distingue cette version de la construction usuelle et qui, par calcul, change la breadth théorique d'un facteur ~15×.
- **Overlay flux contraint** : le résidu démeané est filtré/pondéré par les fenêtres datées les plus propres identifiées en §4 — priorité aux dates de rebalancement mensuel/trimestriel (jambe la mieux caractérisée dans la littérature) et, pour la jambe US spécifiquement, au calendrier d'adjudication du Trésor (sous réserve de corriger le contrôle placebo, §4.4). Le COT sert uniquement de filtre de régime lent (positionnement extrême = réduction de taille), jamais de déclencheur.
- **Véhicule** : micro-futures CME (M6E, M6A, M6B, M6J, M6C, M6S, M6N…) pour tenir la marge de 30 legs dans €13k — un contrat plein (6E ≈ $2-3k de marge) × 30 legs dépasse le capital disponible ; les micros (1/10 de taille) le permettent. La jambe taux (ZN/Bund/Gilt) ne peut pas séparément atteindre N≥30 (4-5 instruments liquides au mieux) — à traiter comme sleeve discrétionnaire distincte, pas comme composante du calcul de breadth cross-sectionnel.

### 5.2 Ce qui la falsifierait

**Volet 1 (construction dispersion) :**
- **F1** — Mesurer ρ̄ empirique des surprises macro brutes sur l'univers ciblé. Si ρ̄ < 0.3, le problème de breadth est peut-être moins sévère qu'annoncé et la construction usuelle (non démeanée) suffit déjà — pas besoin du volet 1.
- **F2** — Mesurer la corrélation résiduelle moyenne ρ̄_resid entre paires démeanées DISJOINTES. Si ρ̄_resid > 0.15-0.20 (signature d'un sous-facteur régional, cf. §2.1/IMF WP/16/54), recalculer N_eff avec la valeur MESURÉE, pas supposer 0 — la breadth réelle sera très inférieure au N−1 théorique.
- **F3** — Test de β-orthogonalité (L38) appliqué au RÉSIDU (pas au niveau) : régresser le résidu démeané sur le facteur mondial retiré ; R² doit rester <30 %, sinon le "résidu" est encore du timing sur le facteur commun déguisé.
- **F4 — LE falsificateur central** : le résidu idiosyncrasique a-t-il un pouvoir prédictif OOS sur le rendement relatif futur, HAC t>2.5, walk-forward ≥5 folds ? Si non, le gain de breadth est purement mécanique et ne sert à rien — plus de paris indépendants sur du bruit n'améliore aucun Sharpe. C'est le nœud du volet 1 : le calcul §3.4 dit que le gain de breadth est réel, mais SEUL ce test dit s'il vaut quelque chose.
- **F5 — placebo de construction** : reproduire le démeanage sur un univers aux labels-pays permutés aléatoirement (shuffle) et vérifier que le t-stat du résidu retombe à zéro. Sinon le signal résiduel n'est qu'un artefact de la construction elle-même (cf. discipline placebo du dépôt, L49/L58).

**Volet 2 (flux contraints) :**
- **F6** — COT : falsifié si la significativité ne survit qu'à horizon <5 jours (immédiatement après la publication du vendredi) — intraitable vu le décalage de 3 jours. Exiger significativité HAC à horizon ≥5-10 jours OOS ET stabilité par décennie (risque de sur-crowding post-2010 par la prolifération des CTA systématiques qui répliquent des positions proches).
- **F7** — Rebalancement daté : falsifié si l'effet mesuré sur la fenêtre la PLUS RÉCENTE (2020+) est statistiquement indiscernable d'un placebo calendaire apparié en volatilité (méthode L49) — la littérature documente elle-même une décroissance de l'effet Russell/S&P avec le temps ; ne pas citer les chiffres 1996-2002 comme s'ils étaient d'actualité.
- **F8** — Adjudications Trésor : falsifié si le contrôle L58 (moyenne du pool doit égaler l'espérance INCONDITIONNELLE de la forme de trade, pas un placebo calendaire potentiellement biaisé) n'est pas satisfait avant toute mesure d'effet.
- **F9** — Banques centrales : falsifié comme solution de breadth si, même après agrégation multi-banques centrales, le nombre d'événements exploitables/an reste <10-15 — l'axe ne résoudrait alors pas le problème, il le déplacerait seulement.
- **F10** — Véhicule (à faire EN PREMIER, avant tout test statistique, discipline L53) : si marge micro-futures × N legs > capital disponible même en micro, la construction est inadmissible au véhicule et il est inutile de la tester statistiquement avant de revoir N ou le véhicule.

---

## 6. Sources

- Kose, Otrok & Prasad (2012), *Global Business Cycles: Convergence or Decoupling?*, IER — http://prasad.dyson.cornell.edu/doc/IERFinal_KoseOtrokPrasad.2012.pdf
- Kose, Otrok & Whiteman (2003), *Understanding the Evolution of World Business Cycles*, IMF — https://www.imf.org/external/np/res/seminars/2003/global/pdf/kose.pdf
- IMF WP/16/54, *Has Globalization Really Increased Business Cycle Synchronization?* — https://www.imf.org/external/pubs/ft/wp/2016/wp1654.pdf
- Dallas Fed WP2512, *Global Macro-Financial Cycles and Spillovers* — https://www.dallasfed.org/~/media/documents/research/papers/2025/wp2512.pdf
- ScienceDirect, *Global factors, regional factors, and macro-financial linkages* — https://www.sciencedirect.com/science/article/abs/pii/S2110701725000721
- ScienceDirect, *Advanced economies and emerging markets: Dissecting the drivers of business cycle synchronization* — https://www.sciencedirect.com/science/article/abs/pii/S0165188918300496
- Eriksen (2020), *Cross-Sectional Return Dispersion and Currency Momentum*, SSRN 3001681 / ScienceDirect — https://www.sciencedirect.com/science/article/abs/pii/S092753981930057X
- NBER w26329, *Cross-Sectional Dispersion of Risk in Trading Time* — https://www.nber.org/papers/w26329
- Macrosynergy, *Inflation as a trading signal* / *Examples of Macro Trading Factors* — https://macrosynergy.com/research/inflation-as-a-trading-signal/ ; https://macrosynergy.com/academy/examples-macro-trading-factors/
- Lustig, Roussanov & Verdelhan (2011), *Common Risk Factors in Currency Markets*, NBER w14082 — https://www.nber.org/system/files/working_papers/w14082/w14082.pdf
- Bessembinder & Chan (1992) cité via revue épub JKU, *Assessing the Influence of Futures Trader Positions on Stock Markets* — https://epub.jku.at/download/pdf/12001095.pdf
- PM-Research, *Does the CFTC Report Have Predictive Power: Machine Learning Approach* — https://www.pm-research.com/content/iijjfds/3/3/139
- ScienceDirect, *Hedgers, funds, and small speculators in the energy futures markets* — https://www.sciencedirect.com/science/article/abs/pii/S0140988304000209
- CFTC, *Release Schedule — Commitments of Traders* — https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm ; cotdata.uk schedule — https://www.cotdata.uk/blog/cot-report-schedule-release-times
- ScienceDirect, *Dollar reserves and U.S. yields: Identifying the price impact of official flows* — https://www.sciencedirect.com/science/article/abs/pii/S0022199624001016
- Treasury.gov, *TIC System* — https://home.treasury.gov/data/treasury-international-capital-tic-system
- NBER w33554, *The Unintended Consequences of Rebalancing* (Harvey et al.) — https://www.nber.org/system/files/working_papers/w33554/revisions/w33554.rev0.pdf
- CFA Institute Enterprising Investor (2025), *Rebalancing's Hidden Cost* — https://blogs.cfainstitute.org/investor/2025/04/10/rebalancings-hidden-cost-how-predictable-trades-cost-pension-funds-billions/
- IJCB, *Stock Market Performance and Pension Fund Investment Policy* — https://www.ijcb.org/journal/v6n2/stock-market-performance-and-pension-fund-investment-policy-rebalancing-free-float-or
- Madhavan (2003), *The Russell Reconstitution Effect*, FAJ — https://www.hillsdaleinv.com/uploads/The_Russell_Reconstitution_Effect,_Ananth_Madhaven,_Financial_Analysts_Journal,_JulyAugust_2003,_Pages_51-64.pdf
- ScienceDirect, *Russell index reconstitutions and short interest* — https://www.sciencedirect.com/science/article/abs/pii/S1062976920301265
- Springer, *On Russell index reconstitution* — https://link.springer.com/article/10.1007/s11156-006-7441-3
- NY Fed Staff Report, *Intraday Price Pressure and Order Flow Around U.S. Treasury Auctions* — https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr1188.pdf
- ECB WP2208 (Sigaux), *Trading ahead of Treasury auctions* — https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2208.en.pdf
- FRBSF (Somogyi), *Treasury Auctions and Long-Term Bond Yields* — https://www.frbsf.org/wp-content/uploads/Somogyi-paper.pdf
