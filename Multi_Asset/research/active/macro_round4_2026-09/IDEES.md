# Macro round 4 — génération et tri, hors terrain déjà couvert

**2026-09-07.** Mandat : proposer des pistes macro NON explorées par les rounds 1-3, en évitant
tout doublon. Δn_tests = 0 — aucune donnée téléchargée, aucun backtest lancé, aucun fichier
modifié hors de ce dossier. Deux recherches web ponctuelles (littérature crypto/macro, littérature
« liquidité nette ») pour évaluer le sérieux de deux pistes avant de les classer — pas de collecte
de données de marché.

## Balayage effectué

Lu intégralement : `CLAUDE.md`, `_meta/lessons_registry.md` (L11→L67 + candidates), extrait de
`research_history.md`, les cinq rapports du round 1 (`macro_score_2026-09/`), `SYNTHESE_ROUND2.md`
+ `FICHE_KILL_B3.md` + `B3_reopen/`, `SYNTHESE_ROUND3.md`, et l'intégralité de
`macro_review_2026-09/REVUE_INDEPENDANTE.md`. Grep disque (pas seulement `git ls-files`) sur
liquidité nette/TGA/reverse repo, macro-crypto, enquêtes de sentiment, calendrier fiscal — y
compris `.worktrees/` (11 worktrees actifs listés, aucun ne porte un chantier macro non recensé
par les synthèses déjà lues).

**Un fait de balayage change le cadrage de ce livrable** : la revue indépendante du round 3 a déjà
statué, en toutes lettres, que **tout objet produisant une étiquette d'état continue
(« bullish/bearish/risk-on-off ») construite à partir de prix ou de macro est la même famille
tuée quatre fois** (L54 ; `regime_markov_sleeves` 0/6 ; `ath_regime_review` R² contrôle −82/−89 % ;
`fx_macro_score_2026-09` — t=−5,18 qui bat le placebo mais s'effondre au diagnostic fold-par-fold,
breadth réelle mesurée **0,67 pari/an contre 251 observations**, L67). Ça condamne d'avance
la piste 4 proposée ci-dessous sous sa forme naturelle — détaillé dans sa fiche.

---

## Classement

| # | Piste | Verdict | Probabilité de survie honnête |
|---|---|---|---|
| 1 | **Enquêtes de positionnement (NAAIM/AAII/BofA FMS)** | **seule piste neuve qui mérite un test** | ~20-25 %, conditionnée à un pré-test à coût nul |
| 2 | **Surprise d'inventaires pétroliers EIA** (piste perso) | testable, breadth correcte, à spécifier | ~20 % |
| 3 | **Calendrier plafond de dette / TGA** | mécanisme réel, **N structurellement mort** | ~10 %, usage défensif seulement |
| 4 | **École « liquidité nette » (Fed − TGA − RRP)** | testable à coût nul, prior faible | ~10-15 % |
| 5 | **Macro appliquée au crypto** (taux réels/dollar/liquidité) | **quasi tuée en littérature** | ~5-10 % |
| 6 | **Marché comme son propre nowcast** (pentes, breakevens, cycliques/défensives) | **doublon d'une famille déjà morte 4×**, ou doublon de l'axe E déjà couvert | 0 % sous sa forme énoncée |
| — | Intervention de change (BoJ/SNB) — piste perso, écartée vite | rejetée en 3 lignes, §7 | ~5 % |

---

## 1. Enquêtes de positionnement et de sentiment (NAAIM, AAII, BofA Fund Manager Survey)

**Mécanisme.** Signal contrarian sur des extrêmes d'allocation déclarée — pas des positions futures
(COT, déjà traité), mais des enquêtes d'opinion/allocation : NAAIM Exposure Index (gérants actifs
US, hebdo), AAII Bull-Bear Spread (retail, hebdo), BofA Global Fund Manager Survey (cash levels,
allocation actions, mensuel). La littérature établit la persistance de ces enquêtes comme proxys de
positionnement, mais la thèse contrarian (extrême = retournement) a une base empirique nettement
moins solide qu'on ne le croit — pas de paper de référence aussi net que Savor-Wilson pour B3.

**Acteur contraint.** Aucun — c'est un signal comportemental, pas un flux forcé. C'est la faiblesse
structurelle de toute la piste.

**⚠ Précédent direct dans ce dépôt, à ne pas ignorer** : L17/L18 ont fermé exactement cette famille
en crypto — Fear & Greed velocity et l'attention Wikipedia se sont révélés être des **proxys de
momentum** (mauvais sens), pas des signaux contrarian indépendants. AAII/NAAIM sur actions US
pourrait subir le même sort : si `sign(spread AAII)` ne diverge de `sign(rendement SPX trailing
20j)` que dans <5 % des observations, c'est cosmétique (L37) — exactement le test qui a coûté une
phrase et fermé F&G.

**Breadth annuelle.** Nominal 52/an (NAAIM, AAII hebdo) à 12/an (BofA FMS mensuel) — mais le
sentiment est fortement autocorrélé (il ne bascule pas d'une semaine sur l'autre), donc le nombre de
paris effectifs est très inférieur au nominal, par le même calcul de noyau de décroissance que le
round 1 (`T·(1−ρ)/(1+ρ)`). Ordre de grandeur probable : **10-20 paris indépendants/an**, à mesurer
avant tout, pas à supposer.

**Véhicule.** US100/SPX via CFD FTMO (~2,48 bps) ou futures ES/MES chez IBKR (~0,4 bps, marge
IBKR non ouverte). ⚠ Le book FTMO est déjà **MONO** sur du bêta actions US (`desk_audit_2026-07-24`)
— tout signal ici s'ajoute à une exposition déjà concentrée, sauf s'il passe le test d'orthogonalité
L38 (régresser sur un buy-and-hold vol-targeté de l'actif primaire) et se montre net d'un R² bas.

**Données.** Gratuites : AAII (historique complet, aaii.com), NAAIM (historique payant partiel,
mais courant accessible), BofA FMS (résumés relayés gratuitement par la presse financière, série
longue payante). Latence de publication réelle **compatible signal-T-1/trade-T** : NAAIM publié le
mercredi sur la semaine précédente, AAII le jeudi sur la semaine en cours — le nombre est connu
avant l'ouverture du lendemain dans les deux cas.

**Ce qui la falsifierait.** (1) Le test L37 de sanité de filtre — s'il échoue, kill immédiat, coût
= une après-midi, aucune donnée de prix touchée au-delà d'un SPX déjà en cache. (2) Une fois L37
passé : IC HAC lag-6 sur rendement excès à 5/10/20j, walk-forward ≥5 folds, avec un diagnostic
fold-par-fold obligatoire (le piège qui a tué `fx_macro_score` était invisible au bootstrap simple).

**Pourquoi elle passe devant les autres** : c'est la seule piste des six où (a) aucun test
équivalent n'existe déjà dans ce dépôt pour CETTE classe d'actifs, (b) le pré-test décisif coûte une
après-midi et zéro téléchargement de prix, (c) l'échec probable est informatif à bas coût (si c'est
un proxy de momentum comme F&G, on l'apprend en un test, pas cinq).

**Probabilité de survie honnête : 20-25 %.** Le précédent L17/L18 est un signal d'alerte sérieux,
pas une condamnation — actifs et enquêtes différents. Mais ne pas construire l'infrastructure IC
complète avant d'avoir passé le test L37 à la main sur les séries publiques.

---

## 2. Surprise d'inventaires pétroliers EIA (piste personnelle)

**Mécanisme.** Le rapport hebdomadaire EIA Petroleum Status (mercredi 10:30 ET) publie la variation
des stocks de brut US ; un consensus de marché existe (sondages Reuters/Bloomberg, relayés
gratuitement par investing.com et oilprice.com). La littérature établit un impact prix documenté et
mesuré sur des fenêtres courtes après publication (déviation stocks-consensus → mouvement WTI dans
la minute à l'heure suivante), avec un motif de sur-réaction/retour partiel plus incertain au-delà.
Distinct de la famille carry commodities déjà **fermée** (L32b) — ici l'objet n'est pas le portage,
c'est un choc d'information hebdomadaire daté.

**Acteur contraint.** Partiel : les traders physiques et les CTA à horizon court doivent digérer une
surprise d'offre/demande publiée à heure fixe — pas un acteur unique forcé, mais un choc
d'information à consensus vérifiable, donc un vrai test bilatéral (surprise positive vs négative)
existe nativement, contrairement à une prime de résolution d'incertitude (contraste avec le
pré-FOMC, §Étape 2 du brief).

**Breadth annuelle.** ~52 publications/an, fenêtre étroite (minutes à quelques heures) donc
faiblement autocorrélée d'une semaine à l'autre — c'est le point fort par rapport aux pistes 1 et 4 :
peu de risque de décroissance de noyau qui rabote la breadth nominale. Ordre de grandeur plausible :
**35-50 paris indépendants/an**, à confirmer par le calcul de N_eff avant toute conclusion.

**Véhicule.** Futures CL chez IBKR (~0,4 bps RT, marge du lot ~$5-6k selon le contrat, tient dans
13k€ mais serré pour le vol-targeting — vérifier L57 avant tout dimensionnement à lot fixe). CFD
WTI FTMO en repli, coût nettement supérieur.

**Données.** EIA (gratuit, API publique), consensus Reuters/Bloomberg (proxy gratuit via agrégateurs
financiers, à vérifier pour la couverture historique — c'est le goulot probable, comme pour l'axe H
du round 3 : sans consensus point-in-time fiable sur tout l'historique, on régresse sur le niveau,
pas la surprise, et on retombe dans le piège B3/H).

**Ce qui la falsifierait.** Porte préalable gratuite, à trancher avant tout code : existe-t-il un
historique de consensus suffisamment long et point-in-time (pas reconstruit a posteriori) ? Si non,
l'axe s'arrête sans donnée de prix touchée — même discipline que l'axe H. Si oui : IC HAC sur
rendement CL post-publication à 15min/1h/1j, gate économique `E[gross/trade] > 3×cost/trade` (L11b,
gate binaire correct pour ce type d'objet event-driven).

**Probabilité de survie honnête : ~20 %.** Mécanisme réel et documenté, breadth honnête plus
généreuse que les pistes macro lentes — mais la fenêtre d'exploitation courte pourrait déjà être
consommée par les acteurs à latence infra (HFT), risque L23b (tier institutionnel) à vérifier
explicitement avant tout investissement de temps.

---

## 3. Calendrier plafond de dette / cycle TGA

**Mécanisme.** Après résolution d'un plafond de dette, le Trésor doit reconstituer son compte
(TGA) par émission massive de bills — un flux mécanique, daté, quasi certain une fois la résolution
votée. C'est le sous-cas le plus « mécanique » du calendrier institutionnel proposé par le
chercheur.

**Acteur contraint.** Le Trésor US lui-même — obligation légale de refinancement, l'un des rares
mécanismes de ce livrable avec un acteur réellement forcé et daté à l'avance.

**Le tueur : la breadth n'est pas un problème statistique, c'est un problème de calendrier réel.**
Les épisodes de plafond de dette avec résolution suivie d'une reconstitution notable du TGA sont
rares — grosso modo une poignée par décennie (2011, 2013, 2015, 2017, 2019, 2021, 2023). Même en
comptant large, on obtient **6-8 événements exploitables sur 15 ans**, sous le plancher du L12
(plafond d'événements) et bien en-deçà de tout N défendable pour du bootstrap par blocs ou un
walk-forward à 5 folds. Ce n'est pas un HAC qui déflate un t — c'est qu'il n'y a tout simplement pas
assez d'épisodes indépendants pour qu'un test signifie quoi que ce soit.

**Ce qui la falsifierait.** Rien à falsifier par le backtest — la porte se ferme sur le comptage
d'événements, avant toute donnée. Seule utilité défensive : comme l'axe A (flag calendaire de saut),
noter les fenêtres de reconstitution TGA connues comme **drapeau de risque gratuit** sur le book
déjà en argent réel (des épisodes de reconstitution rapide du TGA ont historiquement coïncidé avec
des tensions de collatéral / hausse de vol court terme) — jamais comme signal directionnel.

**Vehicule / données** : sans objet en tant que stratégie — les données (fiscaldata.treasury.gov,
calendrier légal du plafond) sont gratuites si jamais réutilisées en mode diagnostic.

**Probabilité de survie honnête comme STRATÉGIE : ~10 %**, et seulement en usage défensif façon
axe A — pas comme source d'alpha. Ne pas construire d'infrastructure dédiée ; à noter dans le
diagnostic de risque du book existant si l'occasion se présente, rien de plus.

---

## 4. École de la « liquidité nette » (Bilan Fed − TGA − Reverse Repo)

**Vérification littérature (recherche web ponctuelle, 2026-09-07).** Aucune évaluation académique
rigoureuse et indépendante n'est ressortie — la littérature disponible sur ce concept est
essentiellement composée de blogs de marché et de tableaux de bord retail (marketontology.com,
feargreedchart.com, eco3min.fr), pas de papier peer-reviewed testant la relation avec HAC/bootstrap.
Ce n'est ni validé ni réfuté sérieusement : **c'est un trou, pas un consensus**, ce qui confirme le
diagnostic du chercheur (« probablement en grande partie du bruit — mais testable »).

**Mécanisme.** Bilan Fed − TGA − RRP approxime les réserves bancaires disponibles pour les marchés
risqués ; la thèse retail affirme que le S&P suit ce niveau avec un décalage de 2 à 6 semaines.

**Acteur contraint.** Aucun direct sur l'indice lui-même. Il existe un sous-mécanisme technique réel
(les fonds monétaires arbitrent RRP vs bills selon le rendement relatif — Fed notes le confirment),
mais c'est un mécanisme de plomberie de taux court terme, pas une force directionnelle documentée
sur les indices actions.

**⚠ Le risque dominant, à tester en premier, coûte zéro téléchargement supplémentaire** : la série
de liquidité nette et le S&P ont partagé la même **tendance macro commune** post-2020 (QE massif →
hausse conjointe, QT 2022 → baisse conjointe des deux). C'est exactement la signature qui a fait
s'effondrer `fx_macro_score` au diagnostic fold-par-fold (effet porté à 100 % par un seul régime,
COVID) — un test naïf pooled 2020-2026 recréerait presque certainement ce même artefact avant tout
signal réel.

**Breadth annuelle.** Données hebdomadaires (H.4.1 Fed, TGA quotidien sur fiscaldata.treasury.gov,
RRP quotidien NY Fed) mais la série est extrêmement autocorrélée — même calcul de noyau que la
piste 1, avec un τ probablement plus long (mois, pas semaines) vu le mécanisme évoqué (2-6 sem de
délai). Ordre de grandeur plausible : **6-12 paris indépendants/an**, pire que la piste 1.

**Véhicule.** US100/SPX CFD FTMO (déjà MONO, même réserve que piste 1) ou futures ES/MES IBKR.

**Données.** 100 % gratuites et déjà identifiées : H.4.1 (Fed), Daily Treasury Statement
(fiscaldata.treasury.gov), RRP (NY Fed markets data). Aucun goulot d'accès, contrairement aux
pistes 1 et 2.

**Ce qui la falsifierait.** Avant tout calcul d'IC : (a) tester si l'effet survit un split par
sous-régime pré/post-2020, comme B3 et `fx_macro_score` l'ont fait systématiquement ; (b) test
d'orthogonalité L38 contre un trend-following vol-targeté du même indice — si R²>30%, c'est du
timing de bêta déguisé sous un autre nom, la même conclusion que L15/L54 sur tout overlay de
régime ; (c) placebo à autocorrélation appariée (L61) avant de citer un t.

**Probabilité de survie honnête : 10-15 %.** Le seul avantage réel sur les pistes 1/2 est le coût
d'accès aux données (nul, tout est déjà gratuit et identifié) — mais le prior structurel (tendance
commune, pas mécanisme) est plus défavorable. À tester seulement après la piste 1, et uniquement
avec les trois garde-fous ci-dessus posés PAR ÉCRIT avant le premier chiffre calculé.

---

## 5. Macro appliquée au crypto (taux réels, dollar, liquidité)

**Vérification littérature (recherche web ponctuelle, 2026-09-07).** Liu & Tsyvinski, *Risks and
Returns of Cryptocurrency*, **Review of Financial Studies 2021** (pas JoF — correction) : régressions
en série temporelle de BTC/ETH/XRP sur des facteurs macro/finance standards (dollar, VIX, taux,
spreads de crédit) — **aucune relation significative trouvée**. Ce qui prédit les rendements crypto
dans ce papier, ce sont des facteurs **spécifiques à la classe d'actifs** : momentum et attention des
investisseurs. C'est un papier sérieux (RFS, revue tier 1), directement sur la question posée, avec
un résultat négatif net. **Ce n'est pas une littérature anecdotique — c'est une littérature qui a
déjà répondu, et la réponse est non**, sur l'échantillon couvert (pré-2020).

**Le lien avec ce dépôt est direct et déjà mesuré.** `Crypto/research/archived/etf_regime_overlay/`
a testé une variante proche (flux ETF + offre de stablecoins comme overlay ON/OFF sur Strategy A
TSMOM) : **GATE 2 FAIL**, Δ=+0,022 %/jour sous le plancher 0,05 %/jour (L15). Même famille, verdict
identique par une voie différente.

**Nuance honnête, à ne pas cacher** : l'échantillon Liu-Tsyvinski s'arrête avant l'institutionnalisation
2020+ (ETF spot, corrélation BTC-Nasdaq visiblement montée depuis). Un ré-examen post-2020
spécifique n'est pas à 100 % couvert par ce papier — mais **c'est exactement la même faute que
celle nommée en round 2** (rouvrir un mécanisme structurellement mort sous prétexte d'un nouveau
régime, sans nouveau mécanisme) si on ne fait que changer la fenêtre. Le test minimal honnête, s'il
devait être fait : orthogonalité L38 d'un facteur DXY/taux réel contre le signal TSMOM-28j déjà en
production — pas une nouvelle construction de zéro.

**Acteur contraint.** Aucun — canal de taux d'actualisation/appétit pour le risque, pas de flux
structurel forcé. C'est un point contre la piste, pas pour : sans acteur contraint, le risque de
retomber dans L54 (timing de bêta) est élevé.

**Breadth annuelle.** Variables macro mensuelles (Fed, DXY hebdo au mieux en changement notable) →
même arithmétique de décroissance que le round 1, **~8-15 paris/an**, avec l'IC macro documenté à
0,02-0,08 (round 1 §1) très loin du seuil requis à cette breadth (0,45+).

**Véhicule.** Hyperliquid/Binance (~17 bps RT) — le seul avantage réel de cette piste est
l'infrastructure déjà déployée, pas l'économie du signal.

**Ce qui la falsifierait / la confirmerait.** Un test d'orthogonalité gratuit (le signal proposé a-t-il
un R²>30% avec le TSMOM déjà en production, ou de la valeur ajoutée réelle) trancherait en une
after-midi — mais étant donné le prior de la littérature, ce test a une espérance de gain faible
face à son coût d'opportunité par rapport à la piste 1.

**Probabilité de survie honnête : 5-10 %.** Le véhicule est bon marché et l'infra existe, mais c'est
la seule piste du lot directement contredite par un papier tier-1 sur la question précise posée.
Ne pas construire — au mieux, un test d'orthogonalité d'une heure sur des données déjà en cache si
l'occasion se présente en marge d'un autre travail, jamais un chantier dédié.

---

## 6. Le marché comme son propre nowcast — REJETÉE, doublon

**Cette piste, prise au pied de la lettre (pentes de courbe, breakevens, cycliques/défensives →
prédire autre chose que soi-même), n'est pas une piste neuve : c'est un des deux seuls objets
possibles, et les deux sont déjà couverts.**

- **Si l'objet informe une décision (sizing, filtre, sélection de régime)** — ce qu'implique
  « bearish/bullish » ou « état macro » — c'est *exactement* la famille que la revue indépendante du
  round 3 vient de trancher : tuée quatre fois (L54, `regime_markov_sleeves` 0/6, `ath_regime_review`
  R² contrôle −82/−89 %, `fx_macro_score` fold-instable). Une reformulation lexicale (« score » →
  « nowcast extrait des prix ») n'est pas un angle nouveau au sens de la politique de ré-ouverture —
  c'est le même objet.
- **Si l'objet nowcaste une variable économique précise (ISM, inflation) pour se positionner AVANT
  sa publication officielle** — la seule lecture qui échappe à la famille overlay — c'est
  *structurellement identique* à l'axe E du round 2 (nowcast moins consensus), déjà classé
  « en attente d'un test préalable » dans le brief du chercheur lui-même.

Les deux lectures retombent sur du déjà-couvert. **Rien à construire ici sans un mécanisme
authentiquement nouveau, écrit avant de toucher aux données** — et je n'en vois aucun dans le
matériel disponible.

**Probabilité de survie sous la forme énoncée : ~0 %** — pas parce que le mécanisme est faux, mais
parce que la question a déjà deux réponses écrites dans ce dépôt.

---

## 7. Piste écartée en trois lignes — intervention de change (BoJ/SNB)

Mécanisme réel (acteur contraint : la banque centrale défend un niveau), mais rejetée vite pour deux
raisons cumulatives : **N structurellement mort** (quelques interventions confirmées par décennie,
même problème que la piste 3) et **détection en temps réel disputée par un tier institutionnel**
(L23b) — les confirmations officielles arrivent des semaines après coup, et sans détection précoce
il n'y a rien à trader avant que le marché l'ait déjà pricé. Survie ~5 %, ne pas investir de temps.

---

## Ordre de marche recommandé

1. **Piste 1 (enquêtes de positionnement)** : passer le test L37 (sanité de filtre, sign-match
   contre momentum trailing) sur AAII et NAAIM en une session, à la main, avant tout code
   d'infrastructure. Décisif et quasi gratuit.
2. **Piste 2 (surprise EIA)** en parallèle : vérifier d'abord l'existence d'un historique de
   consensus point-in-time fiable — porte gratuite, comme l'axe H du round 3.
3. **Piste 4 (liquidité nette)** seulement après 1 et 2, avec les trois garde-fous écrits (split
   régime, L38, placebo apparié) posés AVANT le premier chiffre.
4. **Pistes 3, 5, 6, 7** : ne pas construire. 3 et 7 sont mécaniquement saines mais mortes de faim
   statistique (bon pour un drapeau de risque gratuit, rien de plus) ; 5 est contredite par la
   littérature tier-1 sur la question précise posée ; 6 est un doublon exact de travaux déjà tranchés
   dans ce dépôt cette semaine.
