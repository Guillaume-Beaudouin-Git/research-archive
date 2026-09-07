# Revue indépendante du programme macro (rounds 1-3) et de sa reformulation proposée

**2026-09-07.** Mandat : regard indépendant, lecture seule hors de ce dossier. Rien n'a été
téléchargé, aucun backtest lancé, aucun fichier modifié en dehors de ce document. Δn_tests = 0.

---

## 0. Ce que j'ai vérifié, et une divergence trouvée en route

J'ai lu intégralement `SYNTHESE.md` (round 1), les 5 rapports `01_academique` à `05_execution`,
`SYNTHESE_ROUND2.md` et l'étude complète `B3_reopen/` (les deux pré-enregistrements, les deux
résultats, `FICHE_KILL_B3.md` implicite via les résultats), `SYNTHESE_ROUND3.md` et le test exécuté
`I_correlation/RESULTAT_TEST_6_4.md`, ainsi que le texte intégral des leçons L54, L58, L64, L65,
L67 et de la politique de ré-ouverture dans `_meta/lessons_registry.md`.

**Le raisonnement de breadth tient.** J'ai refait le calcul de paris effectifs `T·(1−ρ)/(1+ρ)` avec
`ρ = 2^(−1/τ)` : pour τ=45j, ρ=0,985, et sur T=1000 jours on obtient bien ≈8 paris — le tableau du
round 1 est correct. L'argument de construction en étoile (`ρ(Y_i,Y_j)=1/2 ⇒ BR→2` indépendamment
de N) est également correct algébriquement : avec un facteur commun et des idiosyncrasies i.i.d. de
variance égale, `Y_i = e_i − e_0` donne `Cov(Y_i,Y_j) = Var(e_0)` pour i≠j et `Var(Y_i) = 2Var(e_0)`,
d'où ρ=1/2 exactement. Le round 1-2 ne s'est pas trompé sur son arithmétique.

**La chaîne B3 est le meilleur travail du programme et sert de référence pour tout le reste de cette
revue.** Trois pré-enregistrements successifs, gelés avant tout contact avec les rendements, chacun
corrigeant honnêtement le précédent (le proxy journalier atténuait réellement — mesuré, pas supposé
— mais l'effet corrigé reste sous son MDE ; puis le holdout 1990-2003 inverse le signe et le
contrôle de dose montre que les non-tradés de 2004-2024 portent un t **supérieur** aux tradés,
+3,01 contre +2,18). C'est exactement la discipline que le reste du programme, et la reformulation
qu'on m'a demandé d'évaluer, doivent imiter.

**Divergence trouvée, non signalée dans le matériel qu'on m'a demandé de lire : un score macro FX
quasi identique à la reformulation proposée a déjà été construit et testé cette semaine**, sous
`.worktrees/fx-macro/Forex/research/active/fx_macro_score_2026-09/` (session 2026-09-02, leçon
**L67** qui en est directement issue). Ce n'est pas un des dossiers listés dans la mission — je l'ai
trouvé en cherchant la provenance de L67, citée dans le registre mais absente du récit round 1-3.
Ce point est développé en §2 car il change matériellement la réponse : **la question posée par la
reformulation n'est pas hypothétique, elle a une réponse empirique récente, dans ce dépôt.**

Point de méthode transversal : ni `SYNTHESE.md` ni `SYNTHESE_ROUND2.md` ni `SYNTHESE_ROUND3.md` ne
citent `fx_macro_score_2026-09/` ou `_meta/veille/macro_model_2026-08/RAPPORT_MACRO.md` (l'audit du
modèle tiers Dedale, qui est la genèse directe de tout ce sujet). C'est une violation de L48
(balayer les chemins consolidés avant tout verdict) à l'échelle du programme, pas d'une session : le
round 1 a réinventé une partie de ce qui existait déjà sous un nom voisin.

---

## 1. Étape 2 — La reformulation, tranchée point par point

### 1.1 Quelle décision ce score change-t-il ?

Je réponds directement : **aucune troisième voie défendable n'existe si le score doit dire
« bullish/bearish/risk-on-off ».** Un objet qui produit une étiquette directionnelle *est*, par
construction, une entrée dans une fonction de décision — même si cette fonction est « je regarde le
chiffre et je décide à l'œil ». Il y a exactement deux cas, pas trois :

- **Le score touche une décision automatisée** (sizing, mise à plat, sélection d'univers, arbitrage
  de sleeve). Alors il **doit** passer le gate qu'un signal quelconque passe dans ce dépôt : IC/t
  HAC, walk-forward ≥5 folds, placebo apparié, test d'orthogonalité (L38), et — signature propre à
  ce type d'objet — le test exact de L54 : *la moyenne doit se déplacer dans le même sens que la
  variance qu'il prédit, pas seulement la variance*. C'est un signal déguisé en overlay, point.
- **Le score touche une décision discrétionnaire** (le chercheur regarde le nombre puis décide). Ce
  n'est PAS une troisième voie plus douce — c'est le pire des deux cas, développé en §1.3.

Le seul objet qui échapperait réellement au gate est un tableau qui **n'informe aucune décision, ni
automatisée ni discrétionnaire** — un journal de diagnostic post-mortem (« pourquoi cette nuit
a-t-elle sauté »), consulté après coup, jamais avant. C'est utile et ça existe déjà de fait : le
point 6 de `ath_regime_review_2026-08` (la géométrie du sleeve rate FOMC/NVDA/BCE — protection
gratuite, découverte en marge d'une revue de risque, jamais utilisée comme gâchette). Mais ce n'est
manifestement pas ce que le chercheur demande : « être en mesure de dire si c'est plutôt bearish »
est un verbe de décision, pas un verbe de journal. Je ne vais pas accepter le cadrage « juste un
tableau de bord » au nom du chercheur puis le lui reprocher plus tard — je le dis maintenant : **tel
qu'énoncé, l'objet est un signal, et doit être gaté comme tel.**

### 1.2 Quel est le critère de validation d'un instrument de mesure ?

Je refuse la position « pas d'IC, pas de Sharpe, donc pas de critère chiffrable » — c'est
précisément le trou par lequel passerait du non-validé. Trois critères, tous testables et déjà
outillés dans ce dépôt :

1. **Test d'orthogonalité (L38), obligatoire, en premier.** Régresser le score sur une vol réalisée
   vol-targetée du même actif/panier : `(β, α HAC, R²)`. `R² > 30%` ⇒ le score est un proxy de vol
   relabellisé, pas une mesure d'état nouvelle. Ce test a déjà tué le conditionneur « distance à
   l'ATH » (`ath_regime_review` : R² du contrôle vol -82 à -89 %, signe qui s'inverse) et le régime
   Markov par sleeve (`regime_markov_sleeves` : orthogonalité échoue systématiquement, seul le
   régime macro commun réagit et meurt sous contrôle t -1,83). Un score qui ne passe pas cette
   étape n'a rien à faire dans un tableau — il redit la vol autrement.
2. **Test de calibration/pouvoir informatif, PAS de Sharpe.** Diebold-Mariano HAC lag-6 sur une
   cible objective et non ambiguë — le score prédit-il, hors échantillon en walk-forward ≥5 folds,
   quelque chose de mesurable (variance réalisée à h jours, probabilité de saut, régime de
   corrélation) mieux qu'une baseline naïve (vol réalisée seule, marche aléatoire) ? C'est
   exactement le test que le round 2 a déjà spécifié pour l'axe E (nowcast vs consensus) et que le
   round 3 a exécuté pour l'axe I (§6.4 : `t_HAC`, MDE80, effet/MDE, sur périmètre gelé) — le
   protocole existe, il suffit de l'appliquer à l'objet « score d'état » lui-même.
3. **Test de rupture proprement estimée (L64), jamais de fenêtre choisie après coup.** Si le score
   change de régime (le fait, ex. franchit un seuil), la date de rupture doit être estimée
   endogène (Bai-Perron/CUSUM), sa significativité corrigée du nombre de dates balayées — sinon
   c'est le même piège que l'ORB (rupture au 73e percentile du bruit pur, découvert en 2026-09-01)
   qui guette.

Sans ces trois tests passés **dans cet ordre** (orthogonalité d'abord — le moins cher, le plus
souvent décisif), « c'est juste un tableau de bord » est un prétexte, pas un statut.

### 1.3 Le risque spécifique — blanchiment de l'intuition

Le chercheur a raison de le nommer, et le dépôt a déjà mesuré, sans le dire dans ces mots, à quel
point le risque est réel :

- `sharpe231_doc_audit_2026-07` : un score composite externe s'est révélé **fabriqué au niveau
  composant** — un chiffre qui a l'air d'un calcul en est un jusqu'à ce qu'on tente de le
  reproduire. Un tableau de bord maison mal gardé peut dériver vers le même statut sans mauvaise foi.
- `regime_markov_sleeves` cite explicitement un risque cousin : « HMM look-ahead = fabrication » —
  un modèle de régime mal spécifié invente rétrospectivement une lecture qui n'existait pas au
  moment T.
- Le module `decay.py` du plan round 1 (jamais construit, mais bien spécifié) porte déjà le bon
  garde-fou : *« Doit refuser de rendre un t-stat sans rendre le N_eff correspondant »*. C'est
  transposable mot pour mot au score d'état : **refuser d'afficher une étiquette bearish/bullish
  quand N_eff est sous un plancher écrit d'avance**, pas juste refuser un t-stat.

Garde-fous de conception concrets, à coder AVANT toute utilisation, pas après :
- Afficher systématiquement l'intervalle de confiance (bootstrap par blocs) à côté de l'étiquette,
  jamais l'étiquette seule.
- Afficher N_eff (paris effectifs, formule du round 1 §2) à côté de tout chiffre — un score
  construit sur 8 événements/an ne peut pas prétendre à la même autorité qu'un score sur 200.
- **Geler par écrit, avant construction, la règle d'usage exacte** : « si le score dit X, je fais Y »
  — puis tester CETTE règle précise comme n'importe quel signal (§1.1, cas 1). Sans cette règle
  écrite d'avance, il n'y a rien à gater, et donc rien qui empêche la dérive du §1.1 cas 2.
- Un score qui informe une décision discrétionnaire sans avoir été testé DOIT porter, à l'écran,
  un avertissement de son propre statut (« non validé, N=12, R² vol=0,41 ») — pas une esthétique
  propre qui laisse croire à une validation qu'il n'a pas.

### 1.4 Le z-score et sa fenêtre — le paramètre le plus dangereux, déjà documenté

Le round 1 (§7.5, §7.6 candidate A) et le round 2 (SYNTHESE §2-3) ont déjà établi, indépendamment
l'un de l'autre, que **le choix de fenêtre/demi-vie est le paramètre le plus dangereux de toute
construction de ce type** — pas une anecdote, un motif répété. `fx_macro_score_2026-09` en donne la
démonstration numérique la plus propre du dépôt : la grille de demi-vies `{3,7,14,30,60,90}` a été
sélectionnée **in-fold sur la portion d'entraînement seule**, jamais a priori — et malgré cette
discipline, le meilleur résultat apparent (AUDUSD, t=-5.18) s'est avéré porté à 100% par un seul
fold (2018-2022, COVID), avec un signe qui s'inverse entre apprentissage et test dans 3 fenêtres sur
4. **Un placebo walk-forward correctement apparié à la procédure (p=0,0000) n'a pas suffi** — il a
fallu un second test, la ventilation fold par fold, pour voir que ce n'était pas un effet stable.

Comment figer la fenêtre sans data-mining, concrètement :
1. **Fonder le choix sur un argument économique écrit avant tout calcul** (ex. : demi-vie ≈ durée
   du cycle de publication de l'indicateur, ou durée typique d'un régime de vol — jamais « ce qui
   marche le mieux »).
2. **Sélectionner in-fold, jamais sur le poolé**, exactement comme `fx_macro_score` l'a fait — mais
   ne pas s'arrêter là : ajouter systématiquement le diagnostic fold-par-fold (un seul fold qui
   porte tout l'effet invalide, même si le placebo walk-forward est propre).
3. **Le contrôle de dose de B3** (mesurer l'effet sur les observations SOUS le seuil ; s'il n'est
   pas nul, le seuil sélectionne une période et non un état) s'applique ici trait pour trait : un
   score d'état dont les valeurs « neutres » portent le même signal que les valeurs extrêmes ne
   mesure pas un état, il mesure une fenêtre calendaire.
4. **Deux placebos différents peuvent se contredire — c'est un résultat, pas un bug à réconcilier**
   (L67, annexe (a)) : si le placebo à demi-vie fixe dit « bruit » et le placebo apparié à la
   procédure dit « signal », diagnostiquer par fold avant de trancher, ne jamais retenir la version
   qui arrange.

---

## 2. Le précédent direct : `fx_macro_score_2026-09` répond déjà, en partie, à la question posée

C'est le fait le plus important que j'apporte à cette revue, et il n'était dans aucun des cinq
dossiers qu'on m'a demandé de lire. Cette étude a construit **exactement** l'objet que la
reformulation décrit : un score composite de surprise macro, avec z-score contre une baseline
propre (glissante, causale, sans fuite), décroissance exponentielle, sur 3 devises et 3
transformations. Résultat : **1 seul résultat sur 9 survit Šidák** (AUDUSD/z/20j, t=-5.18),
survit un placebo apparié à la procédure exacte (p=0,0000) — puis **échoue au diagnostic fold par
fold** : signe qui s'inverse entre entraînement et test dans 3 folds sur 4, effet concentré à 100%
sur le fold COVID, partagé par deux paires indépendantes (signature de régime unique, pas d'edge
structurel).

Et la mesure de breadth qui en sort (**L67**) est directement pertinente à la reformulation :
BR mesuré = **0,67 trade actionnable/an**, contre 251 observations/an — facteur **~375×** entre ce
qu'un praticien pressé compterait et ce que la règle de trading réellement exécutable produit. Le
gate IJR, appliqué au chiffre pourtant déjà réfuté, « passerait » par un facteur 35× à 192× — parce
qu'à une fréquence aussi faible, **le gate économique est trivialement franchi même par du bruit**.
C'est le miroir exact de l'avertissement de `SYNTHESE.md` round 1 sur la breadth gonflée, version
empirique et non plus algébrique.

**Ce que ça change pour la reformulation** : le chercheur ne demande pas quelque chose de non testé.
Il redemande, en des mots différents (« plus ou moins de pouvoir prédictif », « bearish/bullish »),
une chose dont une version très proche a déjà été construite cette semaine et a échoué — pas au
placebo simple, mais au test le plus exigeant du dépôt (diagnostic de stabilité par fold). Avant
toute nouvelle construction, la chose honnête à faire est de lire ce rapport, pas de repartir de
zéro sous un nom voisin — exactement l'erreur L48 que le round 1 lui-même a commise en ne le citant
pas.

---

## 3. Ce que TOI je ferais

### 3.1 La bonne question, à cette échelle

Ni la question du round 1-3 (« peut-on construire un score cross-sectionnel tenu ? » — déjà tranchée
non, trois fois indépendamment) ni la reformulation littérale (« un score avec plus ou moins de
pouvoir prédictif, bullish/bearish ») ne sont la bonne question à ce stade. Les deux partagent le
même défaut de cadrage, plus profond que le sujet macro lui-même : **définir le succès comme « avoir
construit un objet » (un score, un tableau) plutôt que comme « avoir identifié une décision qui
s'améliore sous une discipline de test »**. La reformulation adoucit le vocabulaire (« score » →
« instrument de mesure ») sans changer cette structure — c'est pour ça qu'elle retombe exactement
dans les familles déjà mortes (L54, régime Markov, `fx_macro_score`) dès qu'on la prend au sérieux.

**La bonne question, à ce capital et cette infrastructure, est : « Existe-t-il une couche de risque
bon marché, PUREMENT DÉFENSIVE, qui protège le book déjà déployé — testée avec le même critère
que L54 (moyenne dans le même sens que la variance), avant qu'on lui demande quoi que ce soit
d'offensif ? »** C'est une question plus étroite que celle du chercheur, mais c'est la seule version
du problème qui n'a pas déjà été tuée sous une forme voisine, et elle réutilise ce que le programme
a déjà produit sans le construire à neuf.

### 3.2 Ce que je construirais en premier, et pourquoi

**Rien de nouveau en fondamentaux macro (PIB/PMI/inflation).** C'est le point le plus direct de
cette revue : ce chantier a déjà consommé 3 rounds + une session parallèle (`fx_macro_score`), et le
verdict converge à chaque fois par une voie différente (arithmétique de breadth, véhicule, fold
diagnostic). Rouvrir demanderait un angle mécaniquement nouveau (politique de ré-ouverture) — je
n'en vois aucun dans ce qu'on m'a montré.

**Premier geste concret : geler l'axe A du round 2 (flag calendaire de saut) tel quel, et l'étendre
avec les variables déjà mesurées dans `ath_regime_review` (VIX/VIX3M term structure, distance à
l'ATH — **comme diagnostics, pas comme conditionneurs**, puisque L54/`regime_markov` ont déjà montré
que le second est un proxy de vol dégradé).** Raison : c'est le seul axe du programme qui (a) protège
un book déjà en argent réel plutôt que d'en chercher un nouveau, (b) est déjà chiffré comme « bon
marché » par le round 2 lui-même, (c) a un test de falsification écrit et non-négociable (Δp(pass)
contre un dé-levier piloté par la vol réalisée seule, à duty cycle apparié — jamais un ΔSharpe), et
(d) réutilise un fait déjà établi sans coût : la géométrie du sleeve **rate** FOMC/NVDA/BCE, une
protection gratuite déjà identifiée en marge d'un audit de risque, jamais encore câblée.

**Deuxième geste, en parallèle et à coût nul : le round 3 a raison, avancer l'ouverture IBKR.**
Quatre axes de suite (round 2 D, round 3 F/G/H) et une sleeve déjà validée (month-end ZN, +17,6 %/an)
sont bloqués dessus. C'est un livrable de recherche, pas une tâche administrative annexe — traiter
la matrice de véhicule avant le mécanisme (L53) aurait dû l'imposer avant d'écrire les rapports
littérature de F/G/H, pas après (voir §3.4).

**Ce que je ne ferais PAS en premier : construire le score fondamentaux z-score/décroissance décrit
par la reformulation.** Il redemande une chose dont une version proche vient d'échouer, sur
l'ensemble le plus dur des tests disponibles ici (§2). S'il devait être retenté un jour, ce ne
pourrait être qu'avec un angle réellement nouveau et écrit avant de toucher aux données — pas une
reformulation du vocabulaire de sortie (signal → étiquette d'état).

### 3.3 Ce qui mérite d'être gardé, ce qui mérite d'être jeté

**À garder** :
- La discipline de breadth honnête (`IR = TC×IC×√BR`, BR = paris actionnables, jamais observations)
  — L67 en donne la preuve empirique la plus nette du dépôt, à citer systématiquement désormais.
- La chaîne B3 comme modèle méthodologique : pré-enregistrement gelé → amendement déclaré →
  holdout authentique → contrôle de dose. C'est la meilleure exécution du programme, à réutiliser
  telle quelle pour tout futur axe événementiel.
- Le module `decay.py`/`breadth.py` planifié (jamais construit) : le garde-fou « refuser un
  t-stat sans N_eff » est directement transposable au score d'état de la reformulation.
- La politique de ré-ouverture, et sa correction round 2 (pré-FOMC : kill puissance → kill
  mécanique, car une prime de résolution d'incertitude n'a structurellement pas de jambe symétrique)
  — bon exemple de discipline auto-corrective, à ne pas défaire.
- Le protocole de test d'orthogonalité (L38) et le test exact de L54 (signe de la moyenne, pas
  seulement de la variance) : ce sont, concrètement, les DEUX seuls tests qui peuvent trancher la
  question 2 de ce mandat, et ils existent déjà.

**À jeter** :
- L'ambition d'un cadran continu bullish/bearish/risk-on-off comme entrée de décision, sous
  n'importe quel nom (« score », « instrument de mesure », « tableau de bord ») — c'est la famille
  L54/régime Markov/ATH-conditioner, tuée trois fois indépendamment (`regime_markov_sleeves` 0/6,
  `ath_regime_review` -82/-89% au contrôle, `fx_macro_score` fold instable), plus une quatrième fois
  en substance par le round 1 lui-même sur l'arithmétique de breadth. Une reformulation lexicale
  n'est pas un angle nouveau au sens de la politique de ré-ouverture.
- Toute nouvelle collecte de données macro fondamentales (ALFRED, calendriers, consensus
  ForexFactory) tant qu'aucune décision précise n'a été écrite d'avance pour les consommer — le
  plan d'infrastructure du round 1 (§7.4) est un bon plan **pour l'axe événementiel B3/F/H**, pas
  une raison de le construire pour un score d'état qui n'a pas encore de règle de décision gelée.

### 3.4 L'erreur de cadrage que je vois, et que le programme n'a pas nommée

Deux, en réalité, l'une imbriquée dans l'autre.

**(a) Le succès a été défini comme « avoir un objet » plutôt que « avoir une décision qui
s'améliore ».** Round 1 : « construire un système de scoring macro institutional grade » — le
livrable est posé avant la question. La reformulation du chercheur répète la même structure d'un
cran plus bas (« délivrer un score... avec plus ou moins de pouvoir prédictif »). Le round 1 s'en
est sorti en bifurquant vers une famille événementielle testable (§7 de `SYNTHESE.md`), mais sans
jamais dire explicitement que c'était le problème initial. Le distinguo est fait ici, en toutes
lettres, pour qu'il ne se reproduise pas silencieusement une quatrième fois.

**(b) Le check de véhicule (L53 : « la matrice de véhicule passe AVANT le backtest ») a été appliqué
par hypothèse, jamais par programme.** Le round 3 découvre, APRÈS avoir écrit quatre rapports
mécanisme/littérature complets, que 3 axes sur 4 vivent sur IBKR et que le compte n'est pas ouvert.
C'est la bonne réponse appliquée trop tard : le statut du compte IBKR (ouvert ou non) était connu
AVANT de briefer F/G/H, et aurait dû gater l'allocation d'effort de recherche elle-même, pas
seulement conclure chaque rapport individuel. Le round 3 le nomme lui-même en fin de synthèse
(« leçon candidate désalignement véhicule/capital ») — je suis d'accord avec ce diagnostic, et
j'ajoute qu'il s'applique rétroactivement à sa propre séquence de travail, pas seulement aux futurs
programmes.

---

## Résumé (20 lignes max)

**Verdict sur la reformulation** : mauvaise, telle qu'énoncée. « Bullish/bearish/risk-on-off » est
un verbe de décision, pas de mesure — il n'existe pas de troisième voie où l'objet informe une
décision sans être gaté comme un signal (§1.1). Pris au sérieux, c'est exactement la famille
régime-overlay déjà tuée trois fois dans ce dépôt (L54, `regime_markov_sleeves` 0/6, `ath_regime_
review` -82/-89% au contrôle) et une quatrième fois en substance, cette semaine, sous une forme
quasi identique dans `fx_macro_score_2026-09` (t=-5,18 qui bat le placebo mais échoue au diagnostic
fold-par-fold, breadth réelle 0,67 trade/an contre 251 observations comptées naïvement — L67). Ce
précédent n'était cité dans aucun des cinq dossiers qu'on m'a demandé de lire — violation L48 à
l'échelle du programme.

Ma recommandation, en trois points :
1. **Ne pas construire le score fondamentaux z-score/décroissance.** Une version proche vient
   d'échouer sur le test le plus dur disponible ici. Le rouvrir exige un mécanisme neuf écrit
   d'avance, pas un habillage lexical (signal → « instrument »).
2. **Construire à la place l'axe A du round 2 (flag calendaire de saut)**, purement défensif sur
   le book déjà en argent réel, gaté par le test exact de L54 (moyenne ET variance dans le même
   sens) — le seul axe du programme qui protège plutôt que cherche, déjà chiffré bon marché, avec
   un falsificateur écrit.
3. **Avancer l'ouverture du compte IBKR en parallèle, dès maintenant** — elle bloque 4 axes de
   recherche plus une sleeve déjà validée (+17,6 %/an) ; c'est un livrable de recherche prioritaire,
   pas une tâche administrative, et le check de véhicule aurait dû gater l'allocation d'effort du
   round 3 avant qu'il écrive 4 rapports complets, pas seulement conclure chacun d'eux après coup.
