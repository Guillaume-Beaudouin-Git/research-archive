# Literature sweep 2026-08 — mécanismes exploitables hors pairs / statarb / mur temporel

**Statut : N0 — revue de littérature, zéro essai consommé, zéro backtest, zéro commit.**
Périmètre exclu (agents frères) : pairs bivariés/cointégration · statarb multivarié (facteurs,
résidus, avance-retard) · économie du mur temporel.
Filtre appliqué : FTMO 2-step, décision sur **p(pass) / durée / EV par unité de temps**, barrière
**journalière −5 % sur l'équité intraday** (80.2 % des morts), coût réel **indices 1.8 bps RT**,
**XAUUSD 1.84 / 3.88 bps**, swap **≈1.5 bps/nuit/jambe**, univers **17 CFD**, **prix seuls**,
M1 vrai UTC 2007→2026.

---

## 0. Le cadrage qui décide (à lire avant la liste)

Deux contraintes du desk, prises ensemble, réduisent drastiquement l'espace :

- **L24** définit le profil FTMO-suitable : Sharpe *daily* élevé, WR > 55 %, win/loss ≈ 1,
  kurtosis basse, fréquence élevée. C'est, trait pour trait, **le profil d'un fournisseur de
  liquidité**.
- **L33b / L43** : en intraday-flat le coût liant est le spread ; il faut **> 3 bps de gross**
  (et le desk n'a jamais mesuré mieux que 0.36 en ratio gross/cost sur le FX).

Or fournir de la liquidité au tarif retail est structurellement impossible : on paie exactement
le spread qu'il faudrait encaisser. **La seule échappatoire logique est donc un mécanisme où un
acteur CONTRAINT paie, dans une fenêtre courte, un montant qui dépasse le spread** — c'est-à-dire
un flux forcé, calendairement daté, dont la TAILLE est observable ex ante à partir du prix.

Ce critère — *dose observable + acteur forcé + fenêtre bornée* — est le fil rouge du classement
ci-dessous. Il explique aussi pourquoi les familles « drift » et « saisonnalité » descendent :
elles n'ont pas de dose, donc leur gross est constant et petit, donc elles meurent au spread.

Conséquence de périmètre, à assumer d'entrée : **le FX intraday est clos** pour nous (L34 + L43,
3 angles orthogonaux, 10 majors, 2007-2026, gross sub-bps vs 2-5 bps RT). Je n'ai trouvé dans la
littérature 2022-2026 **aucun mécanisme FX intraday dont le gross annoncé dépasse ~2 bps/jour** —
et le meilleur survivant en gross de toute la littérature FX de session (Breedon-Ranaldo, 2.07
bps/jour, two-sided, t 3.55) est **déjà** le kill L34 de ce desk. Les candidats ci-dessous sont
donc, sauf mention contraire, **indices et métaux/énergie**.

---

## 1. Mécanismes retenus, classés par (plausibilité × faisabilité)

### A1 — Momentum de clôture CONDITIONNÉ à la demande de couverture (LETF + dealers gamma)
**Rang 1. C'est le seul candidat de la revue qui satisfait les quatre critères du filtre à la fois.**

**Le mécanisme en une phrase.** Les ETF à levier doivent, pour maintenir un levier constant,
rééquilibrer **dans le sens du mouvement du jour** et **au plus près de la clôture** ; les teneurs
de marché d'options courts gamma doivent se couvrir dans le même sens ; ces deux flux sont
insensibles au prix, datés, et leur TAILLE est proportionnelle au rendement cumulé de la journée.

**Source.** Baltussen, Da, Lammers, Martens, *Hedging Demand and Market Intraday Momentum*, JFE
2021 (60+ futures actions/obligations/matières/devises, 1974-2020). Le rééquilibrage LETF
représentait **16.8 % du volume market-on-close les jours à ±1 %, et 50.2 % les jours à ±5 %**.
Confirmation indépendante récente : intraday momentum toujours présent sur un panel futures
2008→oct. 2024, avec la prédictibilité **concentrée sur les dix dernières minutes**, explicitement
reliée aux besoins de couverture des vendeurs d'options et des LETF.

**Conditions d'existence.** (a) mouvement intra-journalier important — c'est la *dose* ;
(b) un complexe LETF/options de taille non nulle sur l'indice (US500 et US100 : massif ; US30 :
moyen ; GER40 : nettement plus petit) ; (c) la fenêtre de clôture doit exister sur le CFD.
**Ce qui le tue** : les petits jours (flux ≈ 0, gross ≈ 0), l'encombrement post-publication 2021,
et un spread qui s'élargit précisément dans la dernière demi-heure.

**Profil de distribution.** Détention 30 minutes, sortie par le temps (pas par un stop) →
**queue gauche bornée par la volatilité d'une demi-heure**, kurtosis basse, aucun swap, ~20-25 %
des séances → 50-60 trades/an et par indice. C'est exactement le profil L24, et le contraire du
profil lumpy qui plafonne p(pass) à 44-54 %.

**Lecture critique — et pourquoi ce n'est PAS un re-test de session_G.**
Le desk a déjà tué la version Gao-Han-Li-Zhou : SG-2, US100, 3 978 jours, gross ≈ −0.0 bps,
net −3.0 bps (t −6.08), échec two-sided sur les deux jambes, mort sur toutes les sous-périodes
(`data/skew_research/session_G_intraday_flat/exploration_2026-06.md`). Trois différences
explicites, écrites AVANT de toucher la donnée, justifient la ré-ouverture (catégories
*mécanisme différent* + *coût*) :
1. **Le prédicteur testé n'est pas celui du mécanisme.** SG-2 a testé `sign(first30) × last30`.
   La dose de flux LETF/gamma n'est pas le rendement de la première demi-heure : c'est le
   **rendement cumulé open→15:30 ET**, parce que c'est lui qui détermine le montant à rééquilibrer.
   Gao et al. avaient le bon signe, Baltussen et al. ont montré quel régresseur porte le mécanisme.
2. **Aucun conditionnement.** Le mécanisme prédit un effet **proportionnel à |mouvement|** ; mettre
   3 978 jours dans une seule moyenne dilue mécaniquement vers zéro. Un gross poolé de 0.0 bps est
   *exactement ce qu'on attend* d'un effet concentré sur le quintile haut, quel que soit son
   ampleur. SG-2 n'a donc pas falsifié le mécanisme, il a falsifié sa version non conditionnée.
3. **Le tier de coût a changé.** SG-2 tournait à **3 bps RT « conservateur, flaggé »** ; le panel
   RT mesuré donne aujourd'hui **1.8 bps** sur indices. La barre gross a baissé de ~40 %.

Reste honnête : l'effet est publié depuis 2021, primé, et abondamment commenté côté praticiens →
attendre une décote de Sharpe de 1/3 à 1/2 par rapport à l'in-sample publié (littérature sur la
décroissance post-publication : ~5 pts de décroissance de Sharpe par année d'ancienneté).

**Le test décisif le moins cher — dose-response, sans coût, sans trading.**
Sur `deep_history_utc` M1 (US500, US100, US30, GER40), horloge **exchange, avec DST** (L56) :
1. Par séance, calculer `R_day = open→15:30 ET` et `R_last30 = 15:30→16:00 ET`.
2. Trier les séances en quintiles de `|R_day|`. Rapporter, par quintile,
   `mean(sign(R_day) × R_last30)` **en GROSS**, avec t HAC lag-6, et **séparément la jambe up et
   la jambe down** (L25).
3. **Critère de falsification pré-enregistré :** l'effet doit être **monotone croissant en
   |R_day|**, et le quintile haut doit dépasser **3 × 1.8 = 5.4 bps de gross** (L11b, porte
   binaire N-indépendante). Si le quintile haut n'atteint pas 5.4 bps, ou si la monotonie est
   absente, **la famille est close définitivement** — et cette fois pour la bonne raison.
4. Contraste croisé gratuit (L44) : le mécanisme prédit **US500/US100 ≫ GER40** (complexe LETF/
   options bien plus petit en Europe) et **≈ 0 sur XAUUSD/UKOIL**. Si l'effet est aussi fort
   partout, ce n'est pas de la demande de couverture — c'est du momentum générique, déjà mort.
5. Seulement si 3 et 4 passent : appliquer 1.8 bps, delay-1 sur l'entrée **ET re-pricer la sortie
   séparément** (L59 — la sortie est ici temporelle, donc peu exposée, mais la fenêtre 15:59-16:00
   doit être vérifiée en spread réel), puis mesurer p(pass)/durée.

**Coût : < 1 journée. Aucune nouvelle donnée.** À faire en premier.

---

### A2 — Cycle FOMC en semaines paires, utilisé comme RÉDUCTEUR DE TEMPS-À-RISQUE (pas comme signal de rendement)
**Rang 2. Faible plausibilité de « nouvel alpha », forte plausibilité de gain sur la GÉOMÉTRIE.**

**Le mécanisme en une phrase.** Cieslak, Morse, Vissing-Jorgensen (*Stock Returns over the FOMC
Cycle*, JF 2019) documentent que depuis 1994 **la totalité de la prime de risque actions est
gagnée dans les semaines 0, 2, 4, 6 du cycle FOMC** (semaines paires depuis la dernière réunion),
les semaines impaires étant plates ; le canal causal avancé est la communication informelle des
responsables de la Fed vers la presse et le secteur financier.

**Pourquoi c'est intéressant ICI et pas ailleurs.** Ce n'est pas un générateur d'alpha — la
régression d'orthogonalité (L38) donnera un R² élevé contre un buy-and-hold vol-targeté, c'est du
**timing sur beta**, et il faut le nommer ainsi (L37). Mais le problème FTMO n'est pas un problème
de rendement : c'est un problème de **temps passé sous une barrière**. Si la moitié du calendrier
porte tout le rendement et l'autre moitié porte du risque sans rendement, alors **couper la moitié
morte divise par deux l'exposition à la barrière journalière à rendement inchangé** — ce qui est
la transformation exacte que le filtre récompense. C'est une amélioration de p(pass)/durée, pas de
Sharpe brut.

**Ordre de grandeur.** Prime actions entière (~6-8 %/an) concentrée sur ~26 semaines détenues →
~25-30 bps/semaine détenue ; portage sur 5 nuits ≈ 7.5 bps → **ratio gross/portage ≈ 3-4×**,
au-dessus de la ligne L36 (qui tue les primes tenues quand le portage agrégé les égale).

**Ce qui le tue.** (a) La décote post-publication : le papier couvre 1994-2016, il est publié en
2019, et **je n'ai pas trouvé de réplication OOS post-2019 publiée** — c'est le risque principal
et il est réel ; (b) la barrière journalière reste pleine sur les jours détenus (le skew daily
d'un indice long est négatif — L39 impose de rapporter daily ET monthly) ; (c) si le desk a déjà
un moteur long-indice, l'overlay ne fait que redistribuer.

**Réutilisable immédiatement.** `fomc_events.csv 2004-2026` existe déjà dans le repo
(post-FOMC drift kill 2026-06) → aucune nouvelle source. Distinct de **L42** (drift la veille de
l'annonce) : ici l'objet est le **cycle de 6 semaines**, pas la fenêtre de 24 h.

**Le test décisif le moins cher.**
1. Sur US500/US100/GER40 daily 2004-2026, étiqueter chaque séance par sa semaine en temps-cycle
   FOMC. Rapporter le rendement moyen **pair vs impair**, avec HAC lag-6, **et surtout la coupure
   1994-2016 (in-sample du papier) vs 2017-2026 (vrai OOS)**. Le verdict tient entièrement dans
   cette seconde colonne.
2. **Placebo calendaire apparié obligatoire** (L49 + surtout **L58**) : la moyenne du pool placebo
   doit égaler l'espérance **inconditionnelle** de la forme de trade. Le piège L58 (le blackout
   pousse le pool dans un creux saisonnier) s'applique directement ici, parce que les dates FOMC
   sont corrélées au calendrier mensuel.
3. Si OOS ≈ 0 → **fermé, kill mécanique, non rouvrable.** Si OOS survit → l'évaluer *uniquement*
   sur Δp(pass) et Δdurée via `Portfolio/admission/barrier.py`, jamais sur ΔSR.

---

### B1 — Turn-of-the-month, testé par CONTRASTE de mécanisme et non par moyenne poolée
**Rang 3. Effet le mieux documenté de la revue, mais le plus contaminé par le beta.**

**Le mécanisme en une phrase.** Les versements de paie et les contributions de retraite tombent en
fin de mois et sont déployés en actions dans les tout premiers jours du mois suivant, pendant que
les grands fonds franchissent une frontière de reporting — un flux acheteur daté, insensible au
prix, dont la contrepartie n'est pas arbitrable parce que le rééquilibrage est **peu fréquent par
construction** (la littérature récente relie l'effet à *infrequent rebalancing and risk deferral*).

**Ordre de grandeur.** Étude internationale 30 pays, janvier 1994 → décembre 2023 : rendement
quotidien moyen **+10 bps** sur la fenêtre des 4 derniers jours + 4 premiers jours, présent dans
29 pays sur 30 (le Japon excepté). C'est le seul effet calendaire que la littérature sur les
futures d'indices décrit comme **statistiquement ET économiquement significatif et persistant**.

**Arithmétique FTMO, honnête.** 8 jours × 10 bps = 80 bps de gross/mois ; 8 nuits × ~1.5 bps =
12 bps de swap ; 1.8 bps de spread → **net ≈ 66 bps/mois**, ratio gross/coût ≈ 5.7. Ça passe
largement le seuil de coût. **Le problème n'est pas le coût, c'est la nature.**

**Lecture critique — et c'est sévère.** Le desk a déjà rejeté « equity calendars (beta) » dans
l'arc *personal book 2026-07*, et « FX month-end » à 0.05. Le mécanisme flux prédit une chose
falsifiable : l'effet doit exister **là où le flux existe** (indices actions, financés par la paie
et les retraites) et **pas là où il n'existe pas** (XAUUSD, USOIL, croisés FX). Mais le fait que
l'effet soit présent dans 29 pays sur 30 affaiblit fortement ce contraste avant même de mesurer.

**Le test décisif le moins cher (L44, contraste piloté par le mécanisme).**
1. Calculer le rendement moyen des jours TOM vs non-TOM sur **les 4 indices** (flux présent) et sur
   **XAUUSD, XAGUSD, USOIL, UKOIL et 4 croisés FX non-USD** (flux absent ou de nature différente).
2. **Falsification pré-enregistrée :** si l'effet est d'ampleur comparable sur les métaux et les
   croisés, ce n'est pas du flux de paie, c'est du bruit saisonnier ou du beta global → mort.
3. **Test d'orthogonalité L38 obligatoire** : régresser la sleeve TOM sur un buy-and-hold
   vol-targeté de l'indice. **R² > 30 % ⇒ ce n'est pas une prime structurelle, c'est du timing sur
   beta** — à présenter comme tel, et à juger alors uniquement sur Δp(pass)/Δdurée.
4. Rapporter **skew daily ET monthly** (L39) : c'est le daily qui lie la barrière −5 %.

---

### B2 — Continuation post-print macro 08:30 ET, ré-ouverture par la PUISSANCE (et non par le signal)
**Rang 4. Le desk a déjà la bonne FORME ; il lui manque des observations. Prior : NON.**

**État du desk.** SG-1 (`session_G_intraday_flat`) : gap-continuation CPI/NFP sur US100,
open+5min→close, N=146, **two-sided et du bon signe** (+9.7 bps gap-up / +9.1 bps gap-down) mais
t net = 0.69 à 3 bps → « bonne forme mais sous-seuil ». C'est le profil canonique d'un
**UNDERPOWERED, pas d'un REJECTED** — catégorie explicitement rouvrable.

**Éléments nouveaux disponibles.** (a) coût 1.8 bps au lieu de 3 bps → +1.2 bps de net par trade,
soit ~+13 % sur la moyenne ; (b) le nombre d'ÉVÉNEMENTS peut monter : PCE, ventes au détail, PIB,
ISM, tous à horaire déterministe et connus sans aucune donnée payante (le *calendrier* est
déterministe ; ce sont les *consensus* qui sont payants, et le signal ici n'en a pas besoin
puisqu'il lit le gap, c'est-à-dire la surprise déjà prixée).

**Le piège à ne pas tomber dedans.** Pooler 5 instruments sur le même print ne multiplie PAS N par
5 : US500/US100/US30/GER40 réagissent au même choc, N_eff ≪ 5N. Le gain de puissance vient des
**événements supplémentaires**, pas des instruments supplémentaires ; toute SE doit être clusterisée
par date d'événement.

**Le contre-prior est fort et récent.** *Structural Limits of OHLCV-Based Intraday Signals in MNQ
Futures* (arXiv 2605.04004, 947 séances 2021-2025, 14 familles de signaux) : sur **993 événements
macro à fort impact 2022-2025** (FOMC, CPI, NFP, PCE), le drift est **entièrement contenu dans les
5 premières barres** — mesuré à partir de la barre 6, tous les horizons donnent **t entre 0.14 et
0.69**. C'est le même ordre de grandeur que le t=0.69 de SG-1, sur un échantillon indépendant.

**Le test décisif le moins cher.** Refaire SG-1 **à événements élargis** (≥400 prints au lieu de
146), un seul instrument (US500, le plus liquide), coût 1.8 bps, SE clusterisée par date, et
**pré-enregistrer le seuil : t_HAC ≥ 2.5 sur l'échantillon complet, sans découpage de
sous-période** (L-candidate *sub-period-sign-flip-is-not-an-edge* de session_G). Une demi-journée.
**Je recommande de ne le faire qu'après A1**, et de l'abandonner définitivement s'il échoue —
deux échantillons indépendants au même t ≈ 0.7 valent une conclusion.

---

### B3 — Semaine post-OPEX (retrait du gamma stabilisant)
**Rang 5. Mécanisme crédible, documentation majoritairement praticienne, horizon multi-jours.**

**Le mécanisme en une phrase.** Dans les jours précédant l'expiration mensuelle des options
(3e vendredi), les dealers longs gamma amortissent mécaniquement les mouvements (ils vendent la
hausse et achètent la baisse pour rester delta-neutres) ; à l'expiration, **20-40 % du gamma
positif disparaît d'un coup**, et le coussin d'amortissement avec lui.

**La prédiction falsifiable est sur la VOLATILITÉ, pas sur le rendement.** C'est important : le
mécanisme dit « la volatilité réalisée est comprimée avant OPEX et se détend après », il ne dit
**rien de la direction**. Les chiffres directionnels qui circulent (S&P 500 : −0.53 % en moyenne
sur les semaines d'expiration trimestrielle depuis 2017, contre +0.37 % les autres semaines) sont
de source praticienne, sur ~30 observations trimestrielles, et n'ont pas de mécanisme directionnel
attaché. **Je ne recommande pas de trader la direction.**

**Où c'est réellement utile pour nous.** Pas comme sleeve, comme **modulateur de géométrie** : si
la volatilité réalisée est prévisiblement basse la semaine avant OPEX et haute la semaine d'après,
c'est un prédicteur *de la variance* — et **L54 est catégorique** : un régime qui prédit la
variance n'aide que s'il prédit la moyenne **dans le même sens**. Ici il ne prédit pas la moyenne
du tout. Donc l'usage légitime est étroit : **calibrer la taille pour que la barrière journalière
soit à distance constante en unités de vol**, ce qui n'est rien d'autre que du vol-targeting
correct, déjà obligatoire.

**Le test décisif le moins cher (30 minutes).** Rapporter la volatilité réalisée quotidienne
moyenne par jour-relatif-à-OPEX (−5 … +5) sur US500/US100 2007-2026, et la moyenne des rendements
sur les mêmes cellules. **Si la vol bouge et pas la moyenne → classé « information de calibrage »,
pas sleeve**, et on n'y revient plus. Si la moyenne bouge aussi, alors placebo apparié L58
obligatoire (les dates OPEX sont fortement corrélées au milieu de mois, exactement le piège
jour-du-mois qui a fabriqué un faux PASS sur ZN).

---

### C1 — Empreinte outright du roll d'indice matières premières sur USOIL / UKOIL
**Rang 6. Mécanisme en or, véhicule probablement absent, effet probablement décayé. À lire, pas à tester tout de suite.**

**Le mécanisme en une phrase.** Les indices matières premières (S&P GSCI, BCOM) roulent leurs
contrats selon un calendrier **publié à l'avance** — pour le GSCI, du **5e au 9e jour ouvré du
mois**, à raison de 20 % par jour, **au prix de règlement** — ce qui oblige des milliards à vendre
le contrat proche et acheter le suivant à date fixe, sans considération de prix.

**Ordre de grandeur historique.** Mou (2010-2011), GSCI 1980-2010, 19 matières : les stratégies de
front-running dégagent des **Sharpe jusqu'à 4.39 avec skewness POSITIVE** (2000 → mars 2010), et
le rendement de roll chute de **0.24 % à 0.47 %** pendant la fenêtre sur l'énergie. Le profil
(skew positif + haute fréquence + calendrier déterministe) est théoriquement idéal pour une
barrière journalière.

**Pourquoi il ne passe probablement pas chez nous — deux raisons indépendantes.**
1. **Véhicule.** L'edge est un **spread calendaire** (proche vs suivant). Les CFD UKOIL/USOIL de
   FTMO sont des séries continues à contrat unique : le second contrat n'existe pas dans l'univers
   des 17. Reste seulement l'empreinte *outright* — la pression baissière sur le proche pendant les
   jours 5-9 — dont le rapport signal/bruit est très défavorable (effet de l'ordre de 20-50 bps
   contre une volatilité quotidienne du pétrole de ~200 bps).
2. **Décroissance.** Irwin, Sanders & Yan (2022), 27 marchés futures 2000-2020 : le coût de flux
   d'ordre du roll a **baissé de plus de 80 % après 2008**, attribué à l'approfondissement de la
   liquidité HFT et à la diversification des calendriers de roll des indices. L'effet mesuré par
   Mou appartient largement à un régime terminé.

**Le test décisif le moins cher, si un jour.** Sur USOIL/UKOIL daily 2007-2026, rendement moyen des
jours ouvrés 5-9 vs les autres, **par sous-période 2007-2012 / 2013-2019 / 2020-2026**. Un effet
présent seulement dans la première sous-période confirme le kill de régime et ferme le dossier
pour de bon. Coût : 20 minutes. **Valeur principale : fermer proprement, pas ouvrir.**

---

## 2. Écartés, et pourquoi

### 2a. Pas de mécanisme / mécanisme falsifié — **restent fermés**

| Candidat | Verdict |
|---|---|
| **Overnight drift 02:00-03:00 ET** (Boyarchenko, Larsen, Whelan, RFS/NY Fed SR917) | **TUÉ PAR SES PROPRES AUTEURS, juillet 2026.** L'original : ~100 % de la prime actions US gagnée dans la fenêtre 02:00-03:00 ET, **3.7 %/an**, 60 % du rendement close-to-close, 1998-2020, mécanisme = gestion d'inventaire des dealers après le déséquilibre de clôture US. Le suivi *The Disappearing Overnight Drift* (Liberty Street Economics, juillet 2026) : **≈ zéro depuis 2021**. Cause : l'écart-type des déséquilibres de fin de séance est passé de **6.5 % à 2.9 %** — les algos de liquidité découpent plus finement et ne transmettent plus d'inventaire résiduel. Le modèle des auteurs est E[R_ON] = déséquilibre × variance × capacité⁻¹, donc l'effet **reviendrait** si la dispersion des déséquilibres se ré-élargissait. C'était, sur le papier, le meilleur candidat imaginable pour nous (fenêtre de 1 h à 08:00-09:00 CET, **qui ne franchit pas le rollover de swap** → carry-immune sans être intraday-flat). Il est mort. **Ne pas le tester ; le citer.** |
| **Post-release drift macro au-delà des 5 premières barres** | Falsifié sur 993 événements 2022-2025 (arXiv 2605.04004) : t entre 0.14 et 0.69 à partir de la barre 6. Concordant avec SG-1 (t=0.69). Voir B2 pour la seule ré-ouverture défendable (puissance), avec prior NON. |
| **Signaux intraday OHLCV génériques sur indice** | *Structural Limits of OHLCV-Based Intraday Signals in MNQ Futures* (arXiv 2605.04004) : 14 familles, 947 séances, **0 survivant** au jeu complet de critères (walk-forward + t ≥ 2.0 + ≥30 trades + net positif + cohérence annuelle). Gross 0.07-1.50 points/trade contre 2 points de friction. ⚠ Les deux « signaux qui passent » cités (RTH Confluence t=5.83, London Session B t=5.15) sont des **contrôles positifs** construits pour valider le détecteur, pas des edges — ne pas les lire comme des résultats. |
| **ML séquentiel sur OHLCV mono-instrument** | arXiv 2605.17724 (LSTM vs gradient boosting, MNQ 5-min, 944 séances) : aucune structure prédictive significative, aucune des deux architectures ne bat le hold après coûts. Cohérent avec L20. |
| **Funding-contrarian crypto, unlock, sentiment, VRP, carry FX/commodity, ORB/breakout, TSMOM multi-jours CFD, MR intraday** | Kills mécaniques déjà gravés (L11, L13, L32/L32b, L43, L45, L49, L50). Rien dans la littérature 2022-2026 balayée ne fournit d'élément nouveau les concernant. |

### 2b. Tier institutionnel — le mécanisme est réel, le coût retail le mange

| Candidat | Verdict |
|---|---|
| **Dépréciation en heures locales** (Breedon & Ranaldo, JMCB 2013 ; confirmé jusqu'aux années 2020) | Mécanisme solide et **two-sided** : les entreprises sont acheteuses nettes de devise étrangère pendant leurs heures locales, donc l'EUR se déprécie le matin européen et s'apprécie en séance US. **C'est exactement le kill L34 de ce desk** : gross 2.07 bps/jour, t 3.55, mais il faut **< ~1 bp RT/jambe** contre **2.48 mesuré**. Ne pas re-proposer. |
| **Fixings autour de l'horloge** (Krohn, *Foreign Exchange Fixings and Returns around the Clock*, JF 2024) | Même tier. Et le fixing WMR lui-même tombe sous **L23** (élargissement 1 min → 5 min en 2015) : les magnitudes pré-réforme ne sont pas prédictives. |
| **Front-running du roll GSCI** | Voir C1 : mécanisme institutionnel, spread calendaire, et coût de flux d'ordre en baisse de >80 % post-2008. |
| **Copper : ancrage sur la séance chinoise** | Mécanisme plausible (demande physique/financière concentrée en heures SHFE) mais (i) c'est de l'avance-retard → périmètre d'un agent frère, (ii) le spread CFD COPPER chez un broker retail est d'un ordre de grandeur au-dessus des indices → cost-dead avant même de mesurer. |

### 2c. Données indisponibles chez nous (prix seuls, 17 CFD, aucune source payante)

| Candidat | Ce qu'il faudrait |
|---|---|
| **End-of-Day Reversal** (Baltussen, Da, Soebhag ; 2e prix Quantpedia Awards 2025) | Le plus bel effet récent de la revue — renversement marqué des perdants intra-journaliers sur les **30 dernières minutes**, **> 20 % d'alpha annualisé brut** 1993-2019, explicitement **distinct** du momentum intraday de marché et explicitement **non expliqué par le gamma** (canaux : achats retail induits par l'attention + gestion du risque des vendeurs à découvert en fin de journée). Mais c'est un **long/short en coupe transversale d'actions individuelles** : il exige N ≥ 30 titres. Notre univers de 17 CFD n'en contient aucun. **Non actionnable ici, et ce n'est pas un problème de coût — c'est un problème d'univers.** |
| **Positionnement dealer / GEX, open interest par strike** | Données d'options. La version *calendaire* du même mécanisme (B3) est la seule accessible. |
| **Flux de vente à découvert (Concretum, « short sellers create overnight alpha »)** | FINRA daily short volume = actions US, pas d'équivalent sur indice/FX/métaux CFD. |
| **Surprises macro (consensus)** | Payant. Le *calendrier* des publications est gratuit et déterministe ; c'est ce que B2 utilise, en lisant le gap comme proxy de surprise. |
| **CNH/CNY basis, CIP, carnet d'ordres, flux de dividendes** | Hors univers et/ou données non disponibles. |

### 2d. Profil incompatible avec la barrière journalière

| Candidat | Verdict |
|---|---|
| **Variation de saut signée / semi-variance réalisée** (Patton-Sheppard REStat 2015 et suite) | Calculable depuis nos M1, aucune donnée nouvelle. Mais le résultat robuste de cette littérature porte sur la prévision de la **VARIANCE**, pas des rendements ; la prédictibilité de rendement est marginale et surtout documentée en coupe transversale d'actions. Et toute version à horizon quotidien/hebdomadaire est **tenue** → paie le swap. **L54 s'applique frontalement** : prédire la variance sans prédire la moyenne dans le même sens n'aide pas. Classé « information de calibrage », pas sleeve. |
| **Surperformance des semaines à faible gamma, trend-following classique, dual momentum, TAA** | Tous à horizon multi-jours à multi-semaines sur CFD → **L36** (le portage agrégé ≈ toute la prime trend) et **L55** (la pondération inverse-vol amplifie le swap sur univers macro mixte : le FX porte 53 % du notionnel pour −7.8 % du gross). |
| **Saisonnalités annuelles** (or en septembre, « sell in May », driving season pétrole) | N ≈ 19 observations sur notre historique. Sous-puissant par construction, et impossible à distinguer d'un placebo calendaire (L49/L58). |
| **Momentum/breakout lumpy en général** | **L24** : WR 27.75 % / win-loss 3.7× plafonne p(pass) à **44-54 %** quelle que soit la taille du compte. Mauvais outil pour une barrière symétrique. |

---

## 3. Ce que je n'ai pas pu vérifier

1. **Les magnitudes conditionnelles exactes de A1.** J'ai la mécanique (part LETF du volume MOC :
   16.8 % à ±1 %, 50.2 % à ±5 %) et la significativité globale, mais **pas la table de gross en bps
   par quintile de |mouvement|** de Baltussen et al. — c'est précisément ce que le test décisif
   mesurerait chez nous. Le PDF de *End-of-Day Reversal* n'a pas pu être extrait (binaire non
   converti) ; le PDF JFE de *Hedging Demand* est derrière un paywall.
2. **La survie OOS post-2019 du cycle FOMC (A2).** Le papier s'arrête en 2016. Je n'ai trouvé
   **aucune réplication OOS publiée**. C'est le risque n°1 de ce candidat et il n'est pas
   contournable autrement que par notre propre coupure 2017-2026.
3. **Les horaires et la liquidité réels de la fenêtre 15:30-16:00 ET sur les CFD indices FTMO.**
   A1 suppose que cette demi-heure est cotée à spread normal. À vérifier sur les données M1
   `deep_history_utc` (part de barres à fourchette nulle, **contrôle L60**, et spread mesuré par
   tranche horaire) **avant** d'interpréter tout gross — et sans jamais utiliser la colonne `spread`
   seule, qui sous-estime le RT réel d'environ 2.4× et est massivement non peuplée sur le FX.
4. **La taille du complexe LETF/options sur GER40 et US30.** Le contraste croisé de A1 en dépend :
   je l'affirme sur une base qualitative (marché des options actions US ≫ européen), pas sur des
   encours mesurés.
5. **La spécification exacte des CFD indices FTMO** (base future vs cash, traitement des dividendes
   et des rolls). Cela conditionne toute lecture d'un effet de calendrier sur indice ; non
   vérifiable sans le document contractuel du broker.
6. **Le dossier `_automation/alpha_hunt/promising/` (421 items) est très largement inexploitable
   en l'état** : les fiches sont des stubs (« No code, formulas, or specific numeric claims in the
   excerpt. Full article needed »), et la majorité sont des papiers econ.EM sans rapport (pricing
   d'options, GARCH, LLM, quantum). Aucun mécanisme nouveau n'en est sorti que la recherche web
   n'ait donné mieux. Si la chaîne doit servir à la veille, elle a besoin d'une extraction de texte
   complet, pas d'un résumé d'abstract tronqué.

---

## 4. Recommandation en une ligne

**Faire A1 en premier**, parce que c'est le seul candidat de toute la revue dont le mécanisme
fournit une **dose observable ex ante**, dont le profil (30 min, sortie temporelle, ~55 trades/an
et par indice, sans swap) correspond au profil L24 récompensé par la barrière journalière, et dont
le test décisif est une **courbe dose-réponse en gross** qui coûte moins d'une journée et ferme
définitivement la famille si elle est plate.
