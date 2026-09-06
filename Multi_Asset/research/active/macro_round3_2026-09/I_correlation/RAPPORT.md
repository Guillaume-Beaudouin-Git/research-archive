# Axe I — Le régime de corrélation actions-obligations est piloté par la macro

**Round** : macro_round3_2026-09, axe I. **Statut** : cadrage littérature + spécification, **aucun test empirique, aucun téléchargement de donnée, aucun backtest** (contrainte de mission). **Verdict rendu** : aucun — livrable = meilleure version défendable de l'axe, traitement frontal du piège L54, et protocole de falsification. Objet non FTMO/PROPFIRM_PASS-notable : ce n'est **pas** une stratégie génératrice de rendement, donc les gates RESEARCH_PASS/PROPFIRM_PASS du dépôt ne s'appliquent pas ici par construction (§0.2).

---

## 0. Balayage du dépôt (obligatoire, avant recherche externe)

Commande exécutée : `grep -ril "correlation\|correl\|stock-bond\|diversif" --include='*.md' . | grep -v '\.git'` (30+ hits, listés dans le journal de session), puis lecture de `_meta/lessons_registry.md` (registre complet L11-L59, y compris L38 et L54 en texte intégral) et de `Portfolio/risk/correlation.py`.

**Ce qui existe :**

- `Portfolio/risk/correlation.py` — module de **monitoring**, pas de recherche : corrélation glissante entre sleeves (`rolling_correlation_matrix`, `rolling_correlation_history`, `correlation_alert`), seuils d'alerte 0.50/0.65/0.80. Une TODO explicite non résolue dans le docstring : « intégrer avec `PortfolioState.historical_returns` pour générer des alertes quotidiennes quand une paire dépasse le seuil » — jamais fait. Ce module surveille des **sleeves internes** (A vs C, etc.), jamais une corrélation macro actions-obligations sur des actifs sous-jacents. Aucun recouvrement de test avec cet axe.
- Deux items déjà repérés et **jamais lus en texte intégral** dans `_automation/alpha_hunt/promising/` : `quantocracy_revisiting_beyond_60_40_five_decades_of_risk_weight_20260523.md` et `quantocracy_the_inflation_compass_model_20260728.md`. Le second cite **déjà explicitement L54** comme le test à passer avant de faire confiance à un modèle de régime d'allocation piloté par l'inflation, avec la formulation exacte : « le régime doit prédire à la fois le stress ET le rendement forward dans le même sens, pas seulement le stress ». Ces deux fiches sont annotées `TEST_LATER`, jamais promues. Le dépôt avait donc déjà anticipé la question centrale de cette mission sans jamais y répondre.
- Aucun dossier `macro_round1` ; `macro_round2_2026-09` (10 dossiers, axes A-E, cf. `SYNTHESE_ROUND2.md`) ne traite pas la corrélation actions-obligations — grep sur `SYNTHESE_ROUND2.md` et `A_risque/RAPPORT.md` (l'axe le plus proche thématiquement, risque/régime) : zéro occurrence de « correl ».
- L38 (beta-orthogonalité) et L54 (condition de l'overlay de régime) sont les deux leçons directement engagées par cette mission ; texte intégral relu en §6.

**Conclusion du balayage : l'axe est neuf dans ce dépôt.** Aucun test préenregistré, aucune fiche kill, aucun n_test consommé sur la corrélation actions-obligations comme intrant de construction de portefeuille.

### 0.2 Pourquoi cet axe échappe par construction aux Hard Rules de CLAUDE.md

Les règles dures du dépôt (signal T-1/trade T, HAC lag-6, walk-forward ≥5 folds, N≥30, AMTP, RESEARCH_PASS/PROPFIRM_PASS) sont calibrées pour juger une **stratégie génératrice de rendement**. L'idée examinée ici ne prétend prédire aucun rendement — elle prédit un **second moment** (une covariance), qui est un intrant de construction, pas une position. Il n'y a donc pas de Sharpe à faire passer un gate binaire. Le test honnête n'est pas « Sharpe > 0.7 » mais celui posé explicitement par la mission : est-ce que conditionner la CONSTRUCTION (pas le pari directionnel) sur ce régime améliore la survie sous barrière, net de coûts, hors échantillon ? C'est un test de nature différente, développé au §6.

---

## 1. Le mécanisme macro du signe de la corrélation

### 1.1 Ce qui est lu en texte intégral

**Cieslak & Pflueger (2023), NBER WP 30982, « Inflation and Asset Returns »** — lu en texte intégral (introduction + modèle, pages 1-4). Le point d'ancrage empirique : la corrélation entre variations du CAPE (Shiller) et variations du rendement du Trésor 10 ans **change de signe précisément autour de janvier 2000** (Corr = −0.32 avant, +0.33 après, sur données 1952-2023, Figure 1 du papier). Le mécanisme théorique retenu (repris de Campbell-Pflueger-Viceira) : ce n'est pas le NIVEAU d'inflation qui compte, c'est le **signe de la covariance entre inflation et croissance/consommation**. Formellement, la prime de risque du Trésor à long terme est `Cov(m_{t+1}, π^e_{t+1})` où `m` est le facteur d'actualisation (SDF) ; cette covariance est **négative** ("bonne" inflation — l'inflation monte quand la consommation est forte, les obligations restent une couverture, prime de risque négative, corrélation actions-obligations négative) ou **positive** ("mauvaise" inflation — stagflation, les obligations chutent en même temps que les actions, prime de risque positive, corrélation positive). Le papier date la bascule empirique du signe de la covariance inflation/output-gap **vers 2001**, cohérent avec la datation Campbell-Pflueger-Viceira.

**Bonelli, Palazzo & Yamarthy (2025), FEDS 2025-002, « "Good" Inflation, "Bad" Inflation: Implications for Risky Asset Prices »** — lu en texte intégral (introduction + section 2, modèle, Fed Board). Trois faits directement exploitables :

1. Sur l'échantillon 2004-2023 (swaps d'inflation 5 ans), la corrélation actions-obligations glissante à 3 mois (fréquence **journalière**) moyenne **−0.30**, mais atteint des pics positifs autour de **+0.50 fin mai 2021** et **en décembre 2022**, « aux hauteurs de la période stagflationniste des années 1970 ».
2. Magnitude économique mesurée : un mouvement de 1σ des anticipations d'inflation (swap 5 ans) fait, **sans conditionnement**, +40 points de base sur les rendements actions à horizon un jour. **Conditionné** sur une corrélation actions-obligations 2 écarts-types en dessous de sa moyenne (régime « bonne inflation » très marqué), la même surprise produit **+81 points de base** — soit environ un doublement de la sensibilité. C'est un résultat de PRICING conditionnel (comment le marché réagit à une nouvelle d'inflation selon le régime), pas un résultat de timing de portefeuille — mais il quantifie proprement que le régime n'est pas un artefact cosmétique : il double la sensibilité mesurée.
3. Point méthodologique décisif pour la Q2 (prévisibilité, §2) : les auteurs choisissent la corrélation actions-obligations glissante **précisément parce que** « les quantités macroéconomiques, observables à basse fréquence, ne peuvent pas capturer en temps réel les changements de covariance croissance-inflation » — autrement dit, dans cette littérature, **la corrélation elle-même sert de PROXY temps réel du régime**, elle n'est pas un OUTPUT prédit à l'avance par des variables macro indépendantes. Ceci a une conséquence directe et sous-exploitée : si la corrélation EST l'indicateur (et non une variable prédite avec avance par autre chose), alors par construction on ne peut pas espérer une variable macro qui la devance largement — sinon les auteurs l'auraient utilisée à la place.

### 1.2 Ce qui est repris par recherche web (non lu en texte intégral, cité comme secondaire)

- **Campbell, Pflueger & Viceira**, « Bond-Stock Comovements » (revue ARFE 2025) — page bloquée (403) à la récupération directe ; contenu repris via résumé moteur de recherche uniquement. Message central rapporté : la corrélation inflation/output-gap était négative 1979-2001 puis positive après, ce qui entraîne (via un modèle d'habitude à la Campbell-Cochrane, primes de risque amplifiant le lien) le retournement de signe de la corrélation actions-obligations. Cohérent avec Cieslak-Pflueger lu en texte intégral, mais **non vérifié en première main** au-delà du résumé de recherche.
- **Baele, Bekaert & Inghelbrecht (2010)**, Review of Financial Studies, « The Determinants of Stock and Bond Return Comovements » — non lu en texte intégral, résumé de recherche seulement. Finding rapporté, et **important comme contrepoids** : dans un modèle à facteurs avec régimes markoviens sur taux/inflation/output-gap/cash-flows, **les fondamentaux macro expliquent PEU de la comouvement stock-bond** ; ce sont des **proxies de liquidité** (flight-to-quality/flight-to-liquidity) qui font le plus gros du travail explicatif à haute fréquence. Ceci n'invalide pas le mécanisme CPV (qui opère à basse fréquence, structurelle, sur des décennies) mais avertit que la variation **court terme** de la corrélation observée est en bonne partie un phénomène de liquidité/stress de marché, potentiellement moins prévisible et plus corrélé au stress lui-même qu'à un fondamental macro observable à l'avance.

### 1.3 Synthèse du mécanisme, avec le niveau de confiance par brique

| Brique | Statut de lecture | Confiance |
|---|---|---|
| Le signe de la corrélation actions-obligations dépend du signe de Cov(inflation, croissance) | Lu en texte intégral (Cieslak-Pflueger, Bonelli et al.) | Haute |
| La bascule s'est produite autour de 2000-2001 | Lu en texte intégral, daté indépendamment par 2 papiers | Haute |
| La bascule récente (2021-2022) est de même nature (stagflation/mauvaise inflation) | Lu en texte intégral (Bonelli et al., pics +0.50 mai 2021 et déc. 2022) | Haute |
| Le mécanisme est amplifié par les primes de risque, pas seulement les cash-flows | Résumé web (CPV ARFE), non vérifié en 1ère main | Moyenne |
| La variation court-terme est dominée par la liquidité, pas les fondamentaux | Résumé web (Baele et al.) | Moyenne — un seul papier trouvé, pas de réplication vérifiée dans cette recherche |

---

## 2. La prévisibilité du basculement — la question décisive

C'est le point que la mission désigne comme décisif, à raison : un régime identifié seulement un an après coup n'a aucune valeur opérationnelle. Trois éléments, avec preuve à l'appui :

**(a) Le proxy le plus rapide (fenêtre 3 mois, fréquence journalière) a réagi vite — mais de façon épisodique, pas comme un régime stable.** Bonelli et al. montrent des pics à +0.50 en mai 2021 puis en décembre 2022, avec une **moyenne d'échantillon 2004-2023 qui reste à −0.30** — c'est-à-dire que même le proxy le plus réactif de la littérature primaire lue ici ne décrit pas un régime définitivement installé au sens d'une moyenne durablement positive, mais des épisodes de stress ponctuels qui se surimposent à une tendance de fond encore négative sur la fenêtre complète.

**(b) L'indicateur institutionnel standard (fenêtre glissante 36 mois) a un retard structurel de l'ordre de deux ans, arithmétiquement inévitable.** Un chiffre repris par recherche web (non vérifié en texte intégral, mais cohérent entre deux sources indépendantes — futurestandard.com et un second résumé de type Verdad/AQR) : la corrélation glissante à 3 ans entre actions et obligations est repassée positive **pour la première fois depuis novembre 2000** seulement en 2023, atteignant 0.68 fin décembre 2023 — soit **plus de deux ans après** les premiers signaux de mai 2021 relevés par le proxy rapide de Bonelli et al. Ce n'est pas une anomalie de mesure, c'est une **conséquence arithmétique** de la fenêtre : une fenêtre de K mois qui contient, avant la bascule, une longue série négative ne peut mathématiquement basculer en territoire positif qu'après qu'une fraction substantielle des K mois les plus récents soit devenue positive — le délai minimal est de l'ordre de K/2 pour un choc net, et peut être bien pire si le régime est lui-même intermittent (point (a)). C'est **exactement la même famille de piège que L52/L56** dans ce dépôt (un instrument lent agrège silencieusement une information périmée) — sauf qu'ici la « lenteur » n'est pas un bug de fuseau horaire, elle est **inhérente à la définition même de l'indicateur standard de l'industrie**.
- Conséquence directe : toute construction qui utiliserait la fenêtre longue (36 mois, l'usage « standard ») comme signal d'entrée est structurellement en retard de ~2 ans sur l'événement qu'elle est censée détecter. Ce n'est pas un défaut corrigible en raffinant l'estimateur — c'est le compromis biais-variance fondamental : une fenêtre courte réagit vite mais capture le bruit de liquidité (§1.2, Baele et al.), une fenêtre longue est stable mais structurellement en retard.

**(c) Aucune preuve trouvée d'un signal macro qui devance la corrélation elle-même avec une avance économiquement utile.** La recherche menée ici (plusieurs requêtes ciblées sur « détection temps réel », « ex ante », « nowcasting ») ne retourne aucun papier établissant qu'une variable macro observable (dispersion des anticipations d'inflation, pente de courbe, incertitude de politique monétaire) **précède** la corrélation réalisée avec une avance tradable et une robustesse hors échantillon démontrée sur plusieurs cycles. Le point (1.1.3) — le choix même des auteurs primaires d'utiliser la corrélation réalisée COMME proxy temps réel plutôt que de la prédire — est le signal le plus fort trouvé dans cette recherche que la littérature ne dispose pas d'un tel indicateur avancé robuste. Une exception partielle rapportée par recherche web, non vérifiée en texte intégral : un indicateur « ex ante » construit sur la pente de courbe (10 ans − 3 mois) est mentionné dans un résultat de recherche comme alternative à un indicateur de récession ex post — mais aucun détail de performance hors échantillon n'a pu être extrait, et la pente de courbe est elle-même un indicateur de RÉCESSION, pas directement de régime d'inflation ; son usage ici serait une extrapolation non vérifiée.

**Verdict de la section 2, honnête** : le régime de 2021 était **détectable rapidement par un estimateur court/réactif** (2-3 mois, dès mai 2021 — soit à peu près au moment où l'inflation américaine dépassait 4-5 % en glissement annuel, donc quasi contemporain de la donnée d'inflation elle-même, pas en avance sur elle), mais **n'était pas prévisible avec avance** par une variable macro indépendante identifiée dans cette recherche, et **restait invisible à l'indicateur lent standard pendant ~2 ans**. C'est un régime **détectable en temps quasi réel** (contemporain de la publication d'inflation), pas un régime **prévisible** (en avance sur elle). Cette distinction — nowcasting oui, forecasting non démontré — est centrale pour la section 6.

---

## 3. La valeur économique mesurée

**Résumé de recherche web, non vérifié en texte intégral** — Jivraj (SSRN 2024035), « Stock-Bond Correlation and Out-of-Sample Portfolio Performance Using Analyst Forecasts » : coût d'opportunité de « timer » la corrélation actions-obligations avec des prévisions d'analystes chiffré à **1.56 %/an**, avec une hausse mesurée du Sharpe hors échantillon d'un portefeuille à variance minimale construit avec ces prévisions par rapport à un portefeuille équipondéré. Ni la période d'échantillon, ni le traitement des coûts de transaction n'ont pu être confirmés depuis le résumé disponible — **ce chiffre est cité comme ordre de grandeur indicatif de la littérature, pas comme un résultat vérifié**.

**AQR — deux pièces récupérées et lues via extraction structurée (pas le HTML brut, mais un rendu fidèle du contenu) :**

- **« A Changing Stock-Bond Correlation »** : le modèle macro d'AQR (volatilité relative de la croissance et de l'inflation, plus leur corrélation) **explique environ 70 % de la variation LONG TERME** de la corrélation actions-obligations américaine, mais est **« moins réussi pour expliquer les fluctuations court terme »**. C'est une confirmation indépendante, par une deuxième source, du point central de la §2 : le régime est un objet **structurel/décennal** raisonnablement bien expliqué a posteriori, pas un objet **tactique** prévisible à haute fréquence.
- **« A Positive Stock-Bond Correlation Is a Terrible Reason to Add More Equity Risk to Your Portfolio »** : c'est la pièce la plus directement utile pour cadrer un USAGE correct, et elle va dans le sens exact de la mission (« ce n'est pas un signal directionnel »). L'argument : la corrélation actions-obligations a monté (mesurée à 0.53 dans la pièce), mais le **bêta actions des obligations** reste bas (**0.19**) — parce que le bêta dépend aussi du ratio de volatilité relative, pas seulement de la corrélation. Traduction : **corrélation et bêta ne sont pas la même chose**, et la conclusion naïve « les obligations ne couvrent plus, donc remplaçons-les par du crédit privé / des fonds buffer / du bitcoin » est un contre-sens documenté chiffré : ces remplaçants candidats ont un bêta actions PLUS ÉLEVÉ (crédit privé 0.70, fonds buffer 0.63, bitcoin 2.09) que les obligations elles-mêmes (0.19) malgré leur corrélation « propre » apparente. Les seuls vrais diversifieurs identifiés dans la pièce : stratégies market-neutral actions (bêta 0.02) et trend-following/CTA (bêta **négatif**, −0.22).

**Ce que la littérature réunie ici NE fournit PAS** : aucune étude trouvée et vérifiée ne chiffre un gain de Sharpe **net de coûts de rotation**, sur un portefeuille RÉEL conditionné dynamiquement sur le régime de corrélation, comparé à un portefeuille à poids fixes rééquilibré normalement. Le chiffre Jivraj (1.56 %/an) est le seul candidat trouvé et il n'est pas vérifié en première main. **C'est un vide de preuve, pas une preuve négative** — il faut le nommer comme tel plutôt que de l'habiller.

---

## 4. Construction de portefeuille sous contrainte de drawdown, corrélation instable

Recherche menée à un niveau **survol** (résumés de recherche web uniquement, aucun papier lu en texte intégral dans cette section — à traiter avec un degré de confiance plus bas que les sections 1-3) :

- Une littérature identifiée sur la **« tail risk parity »** (introduction pratique trouvée chez AllianceBernstein) : l'idée est d'ajouter une composante d'assurance de queue à la parité de risque classique, précisément parce que la corrélation ORDINAIRE et la corrélation DE QUEUE (en régime de stress) divergent — ce qui est exactement le problème pertinent pour un compte sous barrière (le moment qui compte pour la survie n'est pas la corrélation moyenne, c'est la corrélation conditionnelle aux pires jours).
- Plusieurs papiers récents (2024-2026, non lus, résumés seulement) sur la **parité de risque robuste sous incertitude de covariance** (ensembles de covariance robustes, perturbation calibrée par GARCH + clustering de régime) et sur l'**optimisation CVaR sous covariance robuste** : la direction commune est de traiter la matrice de covariance comme incertaine plutôt que comme un point estimé, et d'optimiser contre le pire cas dans un voisinage de l'estimation — ce qui est conceptuellement le bon outil pour « corrélation instable + contrainte de barrière », mais aucun de ces papiers n'a été vérifié en détail ici, et aucun ne chiffre un gain net de coûts sur un compte de taille comparable à FTMO/perso.
- Le lien le plus solide avec la contrainte de barrière du dépôt n'est pas dans cette littérature externe, mais **déjà dans l'outillage interne** : `Portfolio/admission/marginal.py` (le critère ΔSR au poids ERC) et le déplacement documenté dans MEMORY (« pour un challenge, trancher sur Δp(pass) et Δdurée, PAS sur ΔSR ») sont exactement le bon cadre pour transposer un régime de corrélation : la question n'est pas « est-ce que le régime améliore le Sharpe », c'est **« est-ce que le régime change la probabilité de passage et la durée médiane sous barrière »** (le même déplacement de critère que celui qui a produit l'admission de la sleeve flat-filling à SR 0.62, ρ≈0). C'est le cadre à réutiliser, pas à réinventer, si cet axe devait un jour être testé.

**Verdict de section, honnête** : la littérature externe confirme que le problème est reconnu et outillé (tail risk parity, covariance robuste), mais je n'ai vérifié aucun résultat chiffré net-de-coûts en première main. Le cadre le plus solide pour CE dépôt reste son propre outil (`Portfolio/admission/`), pas un papier externe.

---

## 5. Applicable à quoi, concrètement ?

### 5.1 Le book FTMO déployé (10 000 $, plancher statique)

Composition actuelle (CLAUDE.md, MEMORY.md) : sleeves overnight indices (US100, GER40) + sleeve or + ORB intraday. **Aucune position de duration obligataire dans ce book.** Un régime de corrélation actions-obligations n'a, littéralement, rien à recomposer : il n'existe pas de paire actions/obligations dans ce portefeuille pour que sa corrélation change quoi que ce soit à la construction. **Conclusion : inerte en l'état, et le rester tant qu'aucune sleeve de duration n'est envisagée sur ce véhicule** (ce qui est de toute façon peu probable vu les swaps CFD asymétriques déjà documentés, L30).

Point adjacent réel, mais qui n'est PAS cet axe : la sleeve or joue déjà un rôle de ballast proche, dans l'esprit, de ce que la littérature attribue aux obligations en régime de « bonne inflation » — sauf que l'or est précisément le actif qui, dans le cadre Cieslak-Pflueger/Bonelli, **profite du régime de "mauvaise" inflation/stagflation** (quand actions ET obligations nominales souffrent ensemble), alors que les obligations nominales profitent du régime de "bonne" inflation. Ce sont deux couvertures pour deux régimes OPPOSÉS. Le book FTMO, en détenant de l'or et pas d'obligations, est déjà — sans l'avoir formalisé — positionné du bon côté du régime actuel (or = couverture du régime post-2021), mais **pas parce que cet axe a été construit**, par accident de composition. Ceci mérite d'être noté comme observation, pas comme un résultat à revendiquer.

### 5.2 Le book personnel (~13 k€, IBKR)

C'est ici que l'axe touche quelque chose de réel. Le book personnel validé (`Multi_Asset/research/active/growth_engine_2026-07/STRATEGY_REGISTER.md`, `FINAL_BOOK.md`) combine :
- **H1g — TSMOM diversifié** (trend multi-actifs sur futures, SR 0.35-0.47), qui inclut par construction des instruments actions ET taux parmi ses legs (un TSMOM « diversifié » qui exclut les taux ne mériterait pas ce nom) ;
- **B1 — Month-end Treasury** (`data/personal_book/sleeves/b1_month_end_bond_rally.md`), une sleeve **longue uniquement**, mécanique (flux « dash for cash » de rebalancement de fin de mois, Etula 2020), mesurée β≈0 et décorrélée du trend (ρ≈0.01), SR combiné du book ≈1.02.

Deux implications concrètes, distinctes, et honnêtes :

1. **Pour H1g (trend)** : un régime de corrélation positive actions-obligations n'est PAS mécaniquement un problème pour un système trend-following — c'est même la situation où le trend/CTA gagne le plus en tant que couverture de crise (2022 en est l'illustration empirique la plus citée dans la littérature de marché rassemblée ici, et c'est cohérent avec le bêta actions négatif du trend-following relevé par AQR, −0.22, §3). Le trend n'a pas besoin qu'obligations et actions soient décorrélées ; il a besoin de pouvoir prendre des positions courtes des deux côtés quand elles chutent ensemble, ce qu'il fait par construction. **Aucune action requise ici.**
2. **Pour B1 (bond long-only, mesuré ρ≈0.01 avec le reste du book)** : c'est la vraie question à se poser, et elle n'a **pas** été testée par ce dossier ni par aucun dossier antérieur trouvé dans le balayage. Le ρ≈0.01 est une moyenne mesurée sur un échantillon (TLT 2002-2026, n=269 mois) qui **chevauche les deux régimes** (négatif 2000-2020, positif 2021+). Si le régime post-2021 est structurel et persistant (ce que §1-2 rendent plausible sans le certifier), la question honnête est : **le flux mécanique de fin de mois (dash for cash) survit-il, en magnitude et en signe, dans les mois où actions ET obligations chutent ensemble** (les mois qui comptent le plus pour la survie sous barrière) — ou bien la corrélation ρ≈0.01 mesurée en moyenne plein-échantillon masque-t-elle une corrélation conditionnelle bien plus élevée précisément dans la queue gauche du trend book ? C'est un test de **stabilité conditionnelle d'une hypothèse déjà validée**, pas une nouvelle stratégie — donc il ne consomme pas un nouveau slot du budget de 3 modifications de B1, et il est falsifiable à coût nul avec des données déjà au dépôt (`data/personal_book/`, mensuel, 2002-2026).

### 5.3 La recommandation transférable la plus solide de ce dossier

Elle ne concerne ni FTMO ni le book perso directement — elle concerne **la méthode**. **L38** (test de bêta-orthogonalité : régresser toute prime « structurelle » sur un buy-and-hold vol-targeté de son actif primaire, `R² > 30% ⇒ pas orthogonal`) est, dans sa formulation actuelle, un test PONCTUEL. La littérature de cet axe démontre que le résultat même de ce test — le R² d'une sleeve « décorrélée » contre son actif primaire — **n'est pas stationnaire à l'échelle de la décennie** : un R² mesuré à 5 % en 2015 (régime négatif) n'a aucune garantie de rester bas en 2025 (régime positif), **sans que la sleeve elle-même ait changé de construction**. C'est une observation nouvelle, nommée mais non gravée (discipline de session — voir `CLAUDE.md` §Parallel session coordination) :

> **Candidat de leçon (NAMED, non numéroté)** — *« L38 est un test daté, pas un certificat » (working title `L38_non_stationnaire`)* : tout passage de L38 doit être ré-exécuté périodiquement (proposition : à chaque clôture annuelle, ou dès qu'un papier de référence date un changement de régime macro), avec la fenêtre d'estimation utilisée explicitement rapportée — parce que la littérature du régime actions-obligations (CPV, Cieslak-Pflueger, AQR) démontre que ce type de R² varie par régime macro à l'échelle décennale, indépendamment de toute dérive de la sleeve elle-même.

---

## 6. LA question du dossier — un régime de corrélation échappe-t-il à L54 ?

### 6.1 Rappel exact de L54

« La condition liante d'un overlay de régime n'est PAS le MaxDD : c'est que le régime prédisant la VARIANCE prédise la MOYENNE dans le MÊME SENS. » Mesuré sur le book MONO : les flags prédisaient bien le stress (vol 9.8 % vs 4.2 %) mais le book gagnait PLUS ces jours-là (+218 bps vs +21 bps) — la prime overnight EST la rémunération du risque que l'overlay voulait couper. Aucune variante n'a battu le simple dé-levier à volatilité égale.

### 6.2 Argument à charge — pourquoi un régime de corrélation SEMBLE différent

Le point soulevé par la mission est juste dans sa forme : L54 porte sur un overlay à **UN SEUL actif risqué**, où exposition ≡ risque ≡ capture du rendement — ces trois quantités sont algébriquement la même chose pour une position mono-actif, donc on ne peut PAS couper le risque sans couper mécaniquement le rendement attendu de ce même actif. Un régime de corrélation, appliqué à **N ≥ 2 sleeves déjà détenues**, a un degré de liberté supplémentaire et réel : à budget de risque total CONSTANT (vol-targeting inchangé), on peut recomposer les POIDS relatifs entre les sleeves sans toucher à l'exposition brute totale ni couper le rendement attendu de chaque sleeve individuellement — c'est exactement ce que fait un rebalancement ERC/risk-parity ordinaire à chaque période, et c'est un problème d'estimation de SECOND MOMENT, structurellement plus facile et moins sujet au chevauchement biais/rendement qu'une prédiction de moyenne. Le cadre `Portfolio/admission/marginal.py` (ΔSR_book au poids ERC) accepte déjà, dans sa logique, qu'un changement de poids motivé par la covariance est un acte de construction, pas un pari directionnel. Sous cet angle, une reconstruction de poids pilotée par un régime de corrélation n'est pas un « overlay » au sens de L54/L15 — L54 parlait d'un SWITCH binaire d'exposition (on/off), pas d'une réallocation continue à risque total constant.

### 6.3 Argument à charge inverse — pourquoi cette différence ne suffit PAS à exempter l'axe

C'est le point le plus important de ce dossier, et il n'apparaît dans aucune des sources lues ici sous cette forme — il découle de la mise en regard directe de L54 et du mécanisme de CPV/Cieslak-Pflueger lu en §1.

**Le mécanisme théorique lui-même dit que le régime est PRICÉ.** Dans le modèle Cieslak-Pflueger/CPV, ce n'est pas un hasard si la corrélation actions-obligations devient positive : c'est PARCE QUE la prime de risque des obligations `Cov(m, π^e)` devient positive dans ce régime (équation (3) du papier lu en §1.1) — autrement dit, **au moment précis où un investisseur naïf serait tenté de réduire ou d'abandonner sa position obligataire parce qu'« elle ne couvre plus »**, la théorie dit que sa prime de risque compensatoire **augmente en même temps**, exactement pour la même raison qu'elle ne couvre plus (elle est devenue elle-même risquée, donc rémunérée). C'est **structurellement le même piège que L54**, transposé : L54 dit « le régime qui prédit la variance prédit aussi la moyenne dans le même sens, donc couper l'exposition coupe la rémunération » ; le mécanisme CPV dit « le régime qui fait perdre à un actif sa fonction de couverture relève AUSSI sa prime de risque attendue, donc réduire son poids réduit la rémunération censée compenser la perte de couverture ». Le test L38 (bêta-orthogonalité) mesure une CORRÉLATION, pas une PRIME — et une règle naïve du type « réduire le poids de l'actif dès que sa corrélation avec le reste du book monte » commettrait exactement l'erreur que L54 a démontré coûteuse, sous un déguisement différent (poids relatif au lieu d'exposition brute).

Autrement dit : **l'échappatoire du §6.2 (« ce n'est qu'un problème de second moment, pas de moyenne ») est vraie en mécanique de portefeuille (mean-variance), mais fausse en équilibre général** — parce que dans CE modèle précis, second moment (corrélation) et premier moment (prime de risque) de l'actif concerné **bougent ensemble, et dans le sens qui piège l'investisseur naïf**. Ce n'est pas garanti pour tout régime de corrélation en général (un régime purement lié à un artefact de liquidité de court terme, §1.2, n'a pas nécessairement cette propriété de prime compensatoire) — mais c'est **précisément** ce que dit la théorie pour LE régime étudié ici (inflation/croissance).

### 6.4 Le test qui tranche, falsifiable, jamais exécuté ici

Le §6.2 et le §6.3 ne sont pas contradictoires — ils délimitent une **condition nécessaire** pour qu'une construction pilotée par le régime de corrélation échappe à L54 :

> **Un régime de corrélation échappe à L54 SI ET SEULEMENT SI la reconstruction (a) ne change JAMAIS le budget de risque total du book (vol-targeting constant, pas de switch on/off), ET (b) ne réduit le poids d'un actif QUE si son propre rendement/prime de risque conditionnel, mesuré dans le MÊME régime, n'augmente PAS en compensation. La condition (b) est un test empirique direct, jamais exécuté dans cette recherche, et c'est EXACTEMENT le test L54 lui-même, appliqué à l'actif plutôt qu'au book entier.**

Concrètement, pour B1 (§5.2) : avant de conclure quoi que ce soit sur la stabilité de B1 sous le régime post-2021, il faudrait mesurer — sur les données déjà présentes (`data/personal_book/sleeves/`, TLT/IEF 2002-2026) — le rendement conditionnel de B1 **séparément** dans les sous-échantillons 2002-2000... pardon, 2002-2020 (régime négatif) et 2021-2026 (régime positif). Si le rendement moyen de B1 est stable ou plus élevé dans le sous-échantillon récent, l'hypothèse d'un risque caché est FALSIFIÉE et B1 reste un cas où le §6.2 s'applique proprement (second moment sans prime cachée). S'il est significativement plus faible ou négatif dans le sous-échantillon récent (précisément la signature L54 : le régime qui devrait faire baisser la corrélation-refuge de B1 fait AUSSI baisser son rendement propre), alors §6.3 s'applique et B1 est structurellement plus fragile que sa moyenne plein-échantillon ne le suggère — **sans qu'aucune modification de la sleeve ne soit nécessaire pour le découvrir**, seulement une repartition de l'échantillon déjà disponible. Ce test est gratuit, ne consomme aucun slot du budget de 3 modifications (c'est un audit, pas une modification), et n'a jamais été fait dans ce dépôt.

### 6.5 Verdict de section

**Ni « oui, ça échappe à L54 » ni « non, c'est la même leçon reformulée » n'est la bonne réponse — la bonne réponse est conditionnelle et vérifiable.** Un régime de corrélation à N≥2 actifs a un vrai degré de liberté (recomposition à risque constant) que L54 n'avait pas (un seul actif, exposition=risque=rendement) — le §6.2 n'est pas un artifice rhétorique. Mais la théorie économique qui SOUS-TEND cet axe précis (CPV/Cieslak-Pflueger) prédit explicitement que, pour CE régime précis, le second moment et le premier moment de l'actif délaissé bougent ensemble dans le sens qui piège — ce qui réintroduit la substance de L54 par la porte de derrière, sous une forme testable et jamais testée (§6.4). **Le degré de liberté existe en mécanique de portefeuille ; la question empirique de savoir si l'exploiter est gratuit ou piégé reste ouverte, et le test qui la tranche est spécifié, gratuit, et non exécuté.**

---

## 7. Ce qui falsifierait l'axe, et prochaines étapes

**Falsificateurs de l'axe entier (pas seulement d'un test ponctuel)** :
1. Le test §6.4 appliqué à B1 (ou à toute sleeve candidate future) montre un rendement conditionnel STABLE ou MEILLEUR dans le régime post-2021 → le degré de liberté du §6.2 est réel et exploitable sans piège, au moins pour cette sleeve précise.
2. À l'inverse, un rendement conditionnel dégradé dans le sous-échantillon récent → confirme §6.3, et la bonne conclusion n'est PAS « couper B1 » mais « mesurer si sa prime conditionnelle a aussi monté » avant d'agir — exactement le protocole que L54 impose déjà pour tout overlay.
3. Un test indépendant montrant qu'une variable macro observable EX ANTE (pas la corrélation réalisée elle-même) devance de façon robuste et répliquée sur plusieurs cycles historiques (pas seulement 2021) le régime de corrélation, falsifierait le constat de la §2 (« nowcasting oui, forecasting non démontré ») et ouvrirait une vraie fenêtre opérationnelle qui n'existe pas aujourd'hui dans les sources consultées.
4. Si un futur ajout d'une sleeve de duration au book FTMO ou perso était envisagé, le test AQR bêta-vs-corrélation (§3) doit être appliqué AVANT tout argument qualitatif de diversification — une corrélation basse ne suffit pas, un bêta bas est la condition pertinente, et les deux peuvent diverger.

**Ce que ce dossier NE fait PAS** : il ne recommande aucune modification de code, aucune nouvelle sleeve, aucun changement de poids. Il livre : (a) un mécanisme vérifié en première main sur deux papiers primaires, (b) une réponse honnête à la question de prévisibilité (nowcasting, pas forecasting — avec l'arithmétique du retard de fenêtre comme preuve, pas comme assertion), (c) un vide de preuve nommé sur la valeur économique nette de coûts, (d) un test gratuit et jamais exécuté (§6.4) qui trancherait la question centrale sur la sleeve B1 déjà validée, et (e) une leçon candidate sur la non-stationnarité de L38.

---

## Sources

**Lues en texte intégral :**
- Cieslak, A. & Pflueger, C. (2023). *Inflation and Asset Returns*. NBER Working Paper 30982. https://www.nber.org/system/files/working_papers/w30982/w30982.pdf
- Bonelli, D., Palazzo, B. & Yamarthy, R. (2025). *"Good" Inflation, "Bad" Inflation: Implications for Risky Asset Prices*. FEDS 2025-002, Federal Reserve Board. https://www.federalreserve.gov/econres/feds/files/2025002pap.pdf

**Récupérées via extraction structurée (WebFetch), contenu jugé fidèle mais pas le HTML brut :**
- AQR. *A Changing Stock-Bond Correlation*. https://www.aqr.com/Insights/Research/Journal-Article/A-Changing-Stock-Bond-Correlation
- AQR. *A Positive Stock-Bond Correlation Is a Terrible Reason to Add More Equity Risk to Your Portfolio*. https://www.aqr.com/Insights/Perspectives/A-Positive-Stock-Bond-Correlation-Is-a-Terrible-Reason-to-Add-More-Equity-Risk-to-Your-Portfolio

**Citées via résumé de moteur de recherche uniquement, non vérifiées en texte intégral (confiance moyenne, signalé explicitement à chaque usage) :**
- Campbell, J., Pflueger, C. & Viceira, L. *Bond-Stock Comovements*. ARFE (2025 revision). https://campbell.scholars.harvard.edu/sites/g/files/omnuum5881/files/2025-08/CampbellPfluegerViceira_ARFE_20250820.pdf (page bloquée, 403)
- Baele, L., Bekaert, G. & Inghelbrecht, K. (2010). *The Determinants of Stock and Bond Return Comovements*. Review of Financial Studies 23(6). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1454992
- Jivraj, F. *Stock-Bond Correlation and Out-of-Sample Portfolio Performance Using Analyst Forecasts*. SSRN 2024035. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2024035
- futurestandard.com, *Stock-bond correlation hits multi-decade high* (chiffre 36 mois, 0.68 déc. 2023, première bascule depuis nov. 2000). https://www.futurestandard.com/insights/chart-of-the-week/stock-bond-correlation
- Nelson, R. *Portfolio Construction Under Correlation Breakdowns and Tail Risk*. SSRN 5931154. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5931154
- AllianceBernstein. *An Introduction to Tail Risk Parity*. https://www.alliancebernstein.com/research-publications/cma-created-content/investments_us/instrumentation/anewversionofriskparity.pdf

**Sources internes (dépôt) :**
- `_meta/lessons_registry.md` (L11-L59, texte intégral relu, notamment L38, L54)
- `Portfolio/risk/correlation.py`
- `Portfolio/admission/marginal.py` (cité via MEMORY, non relu en détail ici)
- `Multi_Asset/research/active/growth_engine_2026-07/STRATEGY_REGISTER.md`
- `data/personal_book/sleeves/b1_month_end_bond_rally.md`
- `_automation/alpha_hunt/promising/quantocracy_revisiting_beyond_60_40_five_decades_of_risk_weight_20260523.md`
- `_automation/alpha_hunt/promising/quantocracy_the_inflation_compass_model_20260728.md`
