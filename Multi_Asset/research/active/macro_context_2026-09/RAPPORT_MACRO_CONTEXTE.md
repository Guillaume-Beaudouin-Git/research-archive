# Cadre macro — ORB US100 & Overnight US100/GER40 (2010-2026)

**Rôle** : cadre macro explicatif, en parallèle d'un agent de mesure. Aucune modification de
paramètre de stratégie ici. Δn_tests = 5 (conditionnements testés en §B/§C/§E, comptés
séparément de la mesure de stratégie faite par l'autre agent) — voir note méthodologique en fin
de document.

**Sources** : FRED (DFF, DGS2, DGS10, T10Y2Y, VIXCLS, DTB3, DTWEXBGS, CPIAUCSL, WALCL,
2007-2026, via `pandas_datareader`) ; `Options_Vol/research/archived/vrp_spx_angle_c/phase1/data/vix_daily.csv`
(VIX quotidien 1990-2026) ; `data/raw/NQ_1min_databento_2010-2026.parquet` (NQ 1min, source
canonique de C) ; `data/deep_history_utc/{US100,GER40}_M1.csv` (true UTC, 2013-2026) ; web public
daté (Cboe, NY Fed / Liberty Street Economics, ECB, presse financière).

---

## Frise datée des régimes, 2010 → 2026

| Période | Régime | Variables caractéristiques | Événement de bascule |
|---|---|---|---|
| 2010-01 → 2013-12 | **ZIRP + QE post-GFC, désendettement** | Fed funds 0.05-0.13%, WALCL +8-39%/an, VIX moy. 19.7 (spikes mai 2010 flash crash, été 2011 downgrade US) | QE1→QE3 séquentiels ; pas de hausse Fed avant fin 2015 |
| 2014-01 → 2017-12 | **Taper + normalisation lente, vol la plus basse de l'échantillon** | Fed funds 0.07%→1.33%, VIX moy. **14.4** (le plus bas des 4 tranches), CPI YoY 1.3% moy., WALCL quasi plat 2015-17 | Taper announcement 2013 (avant la fenêtre), 1ère hausse déc. 2015, "taper tantrum" résiduel |
| 2018-01 → 2021-12 | **QT court puis pivot COVID, deux régimes opposés dans la même tranche** | Fed funds 1.33%→2.40%→0.07% (hausses 2018, QE massif 2020), VIX moy. 20.25, spike **82.7** (COVID, 27 fév.-13 mai 2020, 42 séances >35), WALCL +85%/an au pic (juin 2020) | Volmageddon 5 fév. 2018 (VIX 37.3) ; COVID 27 fév. 2020 ; ZIRP+QE illimité mars 2020 |
| 2022-01 → 2024-08 | **Fin du ZIRP, hausses les plus rapides depuis 1980, QT, courbe inversée** | Fed funds 0.07%→**5.33%** (juil. 2023, pic), ECB deposit −0.50%→**4.00%** (sept. 2022→sept. 2023, +10 hausses en 14 mois), T10Y2Y inversé **2022-07-06→2024-08-26** (537j), CPI US pic **8.98%** (2022), WALCL −9.8%/an (2023) | 1ère hausse Fed 16 mars 2022 ; fin taux négatifs zone euro sept. 2022 ; pic Fed funds juil. 2023 |
| 2024-09 → 2025-12 | **Cycle de baisse, courbe re-pentifiée, ECB en avance** | Fed funds 5.33%→3.5-3.75% (3 baisses 2025 : sept./oct./déc.), ECB deposit 4.00%→2.15% (juin 2025), T10Y2Y repasse positif 26 août 2024, spike VIX **60.1** (7 avril 2025, tarifs "Liberation Day") | Fed 1ère baisse sept. 2024 ; choc tarifaire avril 2025 |
| 2026-01 → aujourd'hui | **Pause Fed, résurgence CPI, ECB re-hausse, QT terminé** | Fed funds stable **3.63%**, CPI US YoY remonté à **4.27%** (mai 2026, choc énergie lié au conflit Iran), ECB relève juin 2026 (2.00%→2.25%, 1ère hausse en 3 ans), WALCL repasse **YoY positif** (+1.9%, août 2026, fin de facto du QT), VIX **bas** (14-16, fin août 2026) | Choc Iran/énergie (CPI) ; ECB juin 2026 ; WALCL point bas ~T1 2026 |

---

## A. Régimes macro — détail par variable

**Politique monétaire.** Fed : ZIRP quasi continu 2009-2015 (1ère hausse déc. 2015), normalisation
lente 2016-18 (0.07%→2.40%), retour ZIRP+QE illimité mars 2020, puis le cycle de hausses **le
plus rapide depuis les années 1980** : 1ère hausse 16 mars 2022, pic 5.25-5.50% en juillet 2023
(+525pb en 16 mois). Baisses à partir de septembre 2024, 3 nouvelles baisses en 2025
(sept./oct./déc.), niveau actuel 3.50-3.75% — le marché des taux anticipe encore ~50pb
d'assouplissement en 2026, la Fed elle-même n'en projette qu'un quart de point (source Goldman
Sachs, Morningstar, résumés FOMC déc. 2025).

BCE : taux négatifs de juin 2014 à septembre 2022 (huit ans), cycle de hausses le plus rapide de
l'histoire de la BCE (10 hausses en 14 mois, deposit −0.50%→4.00%, juillet 2022→septembre 2023),
baisses à partir de juin 2024 jusqu'à 2.00% (2025), puis **hausse surprise juin 2026** à 2.25% —
la BCE est actuellement en avance de cycle sur la Fed (elle a fini de baisser puis re-haussé,
pendant que la Fed est encore en pause de baisse).

**Niveau et pente des taux.** 10Y US : ~2.5% (2010-13) → ~2.2% (2014-17, plus bas de la tranche) →
pic ~3.2% (2018) puis 0.5% (2020) → 3.9% (2022-26 moy.) → **4.7%** actuellement. Courbe 10Y-2Y :
jamais inversée 2010-2021 (hors deux brefs épisodes 2007, hors fenêtre), inversée en continu
**2022-07-06 → 2024-08-26** (537 jours, la plus longue inversion de l'après-GFC), repositive depuis,
actuellement **+0.39 à +0.47%** (fin août 2026) — modérément pentue, en re-aplatissement léger
depuis le pic de +0.71% (janvier 2026).

**Régime d'inflation.** CPI YoY US : 0.9-3.8% (2010-13), quasi-déflationniste par moments
(-0.23% en 2015), pic historique **8.98%** (2022, choc énergie post-Ukraine + réouverture post-COVID),
désinflation 2023-2025 vers ~3%, **résurgence à 4.27% en mai 2026** (choc énergie lié au conflit
Iran, cf. Fidelity/Congress.gov), modération à 3.5-3.7% en juillet 2026. La zone euro a suivi un
profil parallèle (négatif à taux nul 2015-16, pic ~10% fin 2022, désinflation depuis).

**Régime de volatilité actions (VIX quotidien, 1990-2026, épisodes >35 depuis 2010).**
Moyenne VIX quasi identique entre tranches de 4 ans : **19.7 (2010-13) / 14.4 (2014-17) / 20.25
(2018-21) / 19.3 (2022-26)** — contre-intuitif si l'on s'attend à un "régime de vol structurellement
plus haut" en 2022-26 : ce n'est PAS le cas au niveau moyen. Ce qui diffère, c'est la **texture** des
épisodes : 2010-13 et 2018-21 contiennent les crises les plus violentes (mai-juin 2010 flash crash,
été 2011 downgrade US, 5 fév. 2018 Volmageddon, 24 déc. 2018, et surtout **COVID 27 fév.-13 mai 2020,
VIX max 82.7, 42 séances >35**) — des chocs de PANIQUE avec forte vol-de-la-vol. 2022 au contraire
est un marché baissier **rampant** (VIX max seulement 36.5 sur 2 séances en mars 2022, malgré un
SPX -19% sur l'année et le cycle de hausses le plus rapide en 40 ans) : la vol moyenne est comparable
mais la dynamique est directionnelle et peu erratique. 2024-2025 réintroduit deux chocs ponctuels
(carry unwind yen, 5 août 2024, VIX 38.6 ; tarifs "Liberation Day", 4-7 avril 2025, VIX **60.1**,
plus haut niveau hors COVID/GFC). Fin août 2026 : VIX **14-16**, régime de complaisance.

**Structure du marché actions.** Concentration : les 10 plus grosses capitalisations du S&P 500
sont passées de ~14% (2014) à ~22% (2020) à **~37-40%** (mi-2024 → 2026), portées par les "Mag 7"
(~31-32% seuls mi-2024) — accélération nette après 2020 (sources Visual Capitalist, CNBC,
Forbes). Options 0DTE : de ~5% du volume SPX en 2016 à ~20% en 2020 à **43-44% en 2022-23** à
**~47% en 2024** — bascule structurelle datée précisément à l'introduction des expirations
quotidiennes SPX par Cboe en **2022** (avant : expirations lun/mer/ven seulement) — source Cboe,
SpotGamma, Benzinga.

**Dollar (DTWEXBGS, indice large).** Non détaillé en tranches ici (hors primo-focus des deux
sleeves, toutes deux sur indices actions USD/EUR) — disponible dans `/tmp/fred_macro_raw.csv`
régénérable, tendance haussière 2014-2016 (fin QE), 2018, pic 2022 (différentiel de taux Fed vs
BCE/BoJ), affaissement 2023-2025 (début du cycle de baisse Fed), stabilisation 2026.

---

## B. Pourquoi 2022-2026 est-il favorable à l'ORB (Nasdaq) ?

Rappel du fait à expliquer : performance nette par tranche de 4 ans **0.10 / −0.60 / 0.34 / 2.85**
(t-stat). Quatre hypothèses examinées, données à l'appui (test empirique fait sur le signal ORB
brut, **sans** les filtres VWAP/gap/stop de la stratégie réelle — c'est une variable de RÉGIME, pas
une réplication de C, dont la mesure est faite par l'agent parallèle).

**Test empirique (NQ 1min Databento, 2010-2026, range 09:30-09:45 ET, exit 12:30 ET, signal =
direction de la cassure à 09:46, aucun stop/TP appliqué) :**

| Tranche | N jours signal (% des jours) | mean_R (unités d'OR) | t-stat | win-rate |
|---|---|---|---|---|
| 2010-13 | 158 (18%) | −0.025 | −0.17 | 48.1% |
| 2014-17 | 198 (20%) | −0.066 | −0.63 | 49.0% |
| 2018-21 | 160 (16%) | −0.052 | −0.44 | 49.4% |
| 2022-26 | 274 (**24%**) | **+0.052** | 0.58 | **52.6%** |

Direction cohérente avec le fait à expliquer (négatif 2010-2021, positif 2022-26) mais **aucune
tranche n'est individuellement significative** — ce proxy brut n'a ni les filtres ni le
stop-loss qui concentrent l'edge réel de C (cf. `Futures/research/active/nq_intraday/results.json`
pour la mesure filtrée, faite par l'autre agent). Le signal utile ici est la **fréquence de
cassure** : elle passe de 16-20% à **24%** des jours en 2022-26, ET le win-rate conditionnel monte
de ~48-49% à 52.6% — les deux bougent dans le même sens (plus de cassures ET plus de cassures qui
tiennent), ce qui est le signe d'un régime plus directionnel à l'ouverture, pas d'un simple effet
d'échantillon.

Hypothèses, départagées :

1. **0DTE (datée, vérifiable, mécanisme plausible mais PAS testé directement ici)** — la part
   0DTE du volume SPX passe de ~20% (2020) à **43-44% (déc. 2022-jan. 2023)** à ~47% (2024), avec
   bascule structurelle nette à l'introduction des expirations quotidiennes Cboe en 2022. Le
   mécanisme plausible (dealer gamma hedging à très court terme, amplifiant les mouvements
   intrajournaliers autour de l'ouverture quand le gamma net est négatif) est cohérent avec la
   dose-réponse temporelle (2022 = l'année de bascule 0DTE ET l'année où l'ORB décolle), mais
   **je n'ai pas mesuré le gamma dealer ni sa corrélation avec les jours de cassure** — **HYPOTHÈSE
   NON TESTÉE au niveau mécanique**, seulement corrélée dans le temps. Le repo a déjà une leçon
   pertinente ici : L54 — corréler dans le temps n'est pas démontrer le mécanisme.
   **Cette hypothèse n'aurait pas été formulable en 2021** (le régime 0DTE n'existait pas encore
   sous sa forme actuelle — daily expiries lancées en 2022).

2. **Fin du ZIRP / taux non nuls (datée : 16 mars 2022)** — mécanisme : à taux zéro, moins de
   dispersion de portage entre "rester en cash" et "être en actions", ce qui peut réduire la
   volatilité de positionnement à l'ouverture (moins d'ordres macro pressés) ; à taux élevés,
   plus de rotations tactiques rapides (obligations vs actions) concentrées à l'ouverture des
   données macro US (souvent 08:30 ET, juste avant l'ouverture actions). Plausible mais **non
   testé** ici faute de temps — nécessiterait un découpage des jours de cassure par présence
   d'une donnée macro à 08:30 ET, ce qui est un test à part entière. **HYPOTHÈSE NON TESTÉE.**
   Elle **aurait été formulable en 2021** (on savait dès 2021 que la Fed finirait par sortir du
   ZIRP), donc ce n'est pas un récit rétrospectif pur.

3. **Concentration Mag7 (datée : accélération nette post-2020, ~22%→37-40% des 10 plus grosses
   capis)** — mécanisme : moins de diversification interne au NDX ⇒ les gaps d'ouverture d'un
   petit nombre de titres à fort poids (résultats trimestriels Nvidia, Apple, etc., souvent
   publiés après clôture ou avant ouverture) dominent plus le gap d'indice qu'en 2014, où le poids
   était mieux réparti. Cohérent avec la hausse de la largeur moyenne de l'Opening Range en points
   (mesurée ici : de 10.3 à 90.9 points sur les 4 tranches — mais cette hausse suit surtout
   l'inflation du niveau de prix du NQ lui-même, donc **peu informative en points bruts** ; il
   faudrait la normaliser en % du niveau d'indice, ce que je n'ai **pas fait** — **HYPOTHÈSE NON
   TESTÉE** proprement, seulement plausible). **N'aurait pas été formulable avant 2020-21**
   (l'ampleur de la concentration Mag7 est un fait post-2020).

4. **Fréquence des ouvertures en tendance vs en range** — c'est le test empirique ci-dessus : la
   fréquence de cassure directionnelle (24% vs 16-20%) et sa persistance (win-rate 52.6% vs
   ~49%) sont les deux seules variables **directement mesurées** ici qui bougent dans le sens du
   fait à expliquer, avec les autres restant non testées.

**Verdict honnête** : la fréquence de cassure et sa persistance sont mesurées et cohérentes avec
le fait à expliquer, mais **pas significatives individuellement** (t max 0.58) et confondues avec
au moins 3 mécanismes plausibles non départagés entre eux (0DTE, fin ZIRP, concentration). Ce qui
est daté et solide : la bascule 0DTE (2022, Cboe) et la bascule taux (mars 2022) coïncident
**toutes les deux** avec le point de rupture de performance de l'ORB — la coïncidence temporelle
est réelle, l'attribution causale entre les deux (ou une troisième cause commune) ne l'est pas.

---

## C. La prime overnight sur indices — a-t-elle disparu, et pour qui ?

**Littérature.** Le papier de référence est Boyarchenko, Larsen & Whelan (NY Fed / Review of
Financial Studies, vol. 36 no. 9, sept. 2023 ; suivi révisé Liberty Street Economics, juillet
2026, échantillon jan. 2021-déc. 2025). Constat : la fenêtre 2h-3h du matin ET (ouverture
Europe) sur futures indices US (**E-mini S&P 500, Nasdaq-100, Dow Jones — nommément cité**)
générait ~3.6-3.7%/an en moyenne 1998-2020, et est tombée **proche de zéro depuis 2021**.

**Mécanisme identifié (décomposition en 3 canaux, papier 2026) :**
E[R_overnight] = (déséquilibre d'ordre à la clôture) × (variance) ÷ (capacité de portage des
teneurs de marché)
- **Canal dominant : la dispersion du déséquilibre d'ordre signé à la clôture s'est effondrée**
  (écart-type de 6.5% à 2.9%, compression de plus de moitié).
- La variance (VIX) n'a quasiment pas bougé (moyenne 20.4→19.4) — **ce n'est PAS un effet de
  régime de vol**, cohérent avec mon propre calcul en §A (VIX moyen quasi stable entre tranches).
- La capacité de portage des teneurs de marché a même légèrement augmenté (liquidité overnight
  15%→16% du volume total).
- Explication candidate des auteurs : les ordres à cours limité postés à la clôture sont devenus
  plus petits en exécution algorithmique — cohérent avec une microstructure plus fragmentée
  post-2020 (croissance des exécutions algo/VWAP institutionnelles).

Ce mécanisme est **exactement celui que le repo redoute** en pareil cas : un régime qui prédit la
variance (le VIX, quasi stable) mais qui n'est PAS ce qui pilote la moyenne (L54) — ici c'est
encore plus net, la variance ne bouge PAS du tout, c'est la **microstructure de l'ordre à la
clôture** qui a changé.

**Mon propre test (US100 & GER40, close ET 16:00 → open ET 09:30, deep_history_utc, 2013-2026) :**

| Instrument | pre-2018 (N/mean/t) | 2018-2021 (N/mean/t) | 2022-2026 (N/mean/t) |
|---|---|---|---|
| US100, tous jours | 1206 / +0.041% / **t=2.61** | 997 / +0.058% / t=2.04 | 1092 / +0.033% / t=1.27 |
| GER40, tous jours | 1062 / +0.050% / t=1.76 | 1023 / +0.023% / t=0.62 | 1029 / +0.024% / t=0.88 |

Décroissance monotone de la significativité sur les deux instruments, cohérente (en direction et
en timing) avec le papier NY Fed — mais le point de bascule chez moi est plus étalé (déjà visible
2018-21 sur GER40) que le "depuis 2021" du papier, ce qui est attendu : le papier mesure une fenêtre
horaire précise (2h-3h ET) sur futures US purs, moi je mesure la totalité clôture-ouverture sur
un CFD (fenêtre plus large, bruit de fond différent).

**Lundi/mardi spécifiquement — la fenêtre réellement tradée par la sleeve B :**

| Instrument, jour | pre-2018 | 2018-2021 | 2022-2026 |
|---|---|---|---|
| US100 Mon | t=0.79 | **t=2.75** | t=0.60 |
| US100 Tue | **t=1.88** | t=1.39 | **t=1.99** |
| GER40 Mon | t=0.97 | **t=2.43** | t=0.63 |
| GER40 Tue | **t=1.92** | t=0.78 | **t=2.05** |

Constat net : **le mardi est le seul jour dont la significativité ne décroît pas** sur les deux
instruments et sur les trois sous-périodes (t entre 1.39 et 2.05), alors que le lundi est fort
uniquement en 2018-21 puis retombe. Ce n'est PAS "la prime overnight a disparu" — c'est "la prime
overnight lundi s'est effondrée, la prime mardi a survécu". Une explication candidate et datable :
la BCE et la Fed tiennent traditionnellement leurs réunions sur 2 jours se terminant le mercredi,
et le calendrier macro US (ISM, JOLTS) tombe souvent en tout début de semaine — un effet de
"positionnement pré-annonce" concentré sur la nuit de mardi à mercredi serait cohérent, mais
**je ne l'ai pas testé** contre un calendrier macro daté (le repo a déjà `data/raw/fomc_events.csv`
pour ça) — **HYPOTHÈSE NON TESTÉE**, à vérifier par l'agent de mesure ou une session dédiée avant
de la citer comme fondement.

⚠ **Le choix Lundi+Mardi dans la stratégie B pourrait donc être partiellement un choix qui capture
le jour restant significatif (mardi) plutôt qu'un choix motivé indépendamment** — à vérifier contre
la note de pré-enregistrement de la sleeve avant de la considérer comme un edge stable plutôt
qu'un artefact de sélection.

**GER40 vs US100** : les deux se comportent de façon très similaire (même profil décroissant, même
persistance relative du mardi), ce qui est cohérent avec un mécanisme commun de flux
transatlantique overnight plutôt qu'un phénomène spécifique à un seul indice — mais le papier NY
Fed ne couvre QUE les futures US, donc le mécanisme précis (dispersion du déséquilibre de clôture)
n'a **pas été vérifié sur le DAX** — HYPOTHÈSE NON TESTÉE pour la transposition du mécanisme exact
à l'Europe, seule la similarité empirique du résultat est mesurée ici.

---

## D. Régime actuel (fin août 2026) et ce qui pourrait le rompre

| Variable | Niveau actuel (28-31 août 2026) | Régime |
|---|---|---|
| Fed funds (DFF) | 3.63% | Pause après cycle de baisse (sept.-déc. 2025), 1 baisse anticipée par la Fed en 2026 |
| ECB deposit | 2.25% (depuis juin 2026) | Re-hausse surprise après un cycle de baisse achevé en 2025 |
| 10Y UST | 4.7% | Modérément élevé vs médiane historique post-GFC |
| 10Y-2Y | +0.39 à +0.47% | Positif, en léger re-aplatissement depuis le pic +0.71% (jan. 2026) |
| CPI US YoY | 3.5-3.7% (juil. 2026), pic 4.27% (mai 2026) | Résurgence inflationniste (choc énergie Iran), en reflux partiel |
| WALCL YoY | **+1.9%** (août 2026) | QT terminé de facto (repassé positif ~T1 2026 après −10.7%/an au creux 2024) |
| VIX | 14-16 (fin août 2026) | Complaisance, bas de fourchette historique |
| Concentration top-10 S&P | ~37-40% | Proche du plus haut de l'échantillon (record post-dot-com dépassé fin 2020) |
| 0DTE % volume SPX | ~47% (dernière mesure 2024, pas de mise à jour 2025-26 trouvée) | Plateau élevé |

**Événements qui feraient basculer un régime, avec seuil observable :**

- **Reprise de la baisse Fed** (2 baisses ou plus en 2026, ramenant DFF sous ~3.0%) —
  romprait le "régime de taux non nuls" invoqué en §B2 pour l'ORB ; seuil : DFF < 3.00%.
- **Ré-inversion de la courbe** (T10Y2Y < 0 à nouveau) — historiquement associée aux phases de fin
  de cycle de hausse, pas de signal actuellement (à +0.39/+0.47%) mais à surveiller si le
  re-aplatissement depuis janvier 2026 (+0.71%→+0.39%) se poursuit.
- **Retour de la volatilité structurelle** — pas le niveau VIX moyen (montré non-discriminant en
  §A) mais la **fréquence des épisodes >35** : zéro depuis avril 2025 ; un nouvel épisode
  signalerait un retour vers le régime "choc de panique" (2018/2020) plutôt que le régime
  "tendance rampante" (2022) — à distinguer, car les deux régimes de vol ont un effet **opposé**
  probable sur l'ORB (une panique casse la structure d'ouverture, une tendance rampante la nourrit).
- **Dé-concentration des indices** — si le poids des 10 plus grosses capis du S&P redescendait
  sous ~30% (retour vers le niveau 2020), l'hypothèse Mag7-gap (§B3) perdrait sa prémisse.
- **Reprise du QT** (WALCL YoY repassant negatif) — signalerait un resserrement renouvelé de la
  liquidité, contexte historiquement associé à une hausse de la dispersion de portage (pertinent
  pour la prime overnight, §C, bien que le mécanisme identifié par NY Fed soit avant tout un
  effet de microstructure de clôture, pas un effet de liquidité macro directe).

---

## E. Les deux régimes sont-ils corrélés ? — la question la plus utile

**Mécanisme.** L'ORB dépend (empiriquement et par la littérature 0DTE/gamma) d'un régime de
**structure intrajournalière** — fréquence de cassure et persistance de la tendance à l'ouverture.
L'overnight dépend (papier NY Fed) d'un régime de **microstructure de clôture** — dispersion du
déséquilibre d'ordre en fin de séance, **explicitement découplé du niveau de VIX** dans le papier
source. Rien n'indique a priori que ces deux mécanismes partagent un driver macro commun — ce
sont des couches différentes de la formation des prix (ouverture vs clôture).

**Test empirique** (P&L quotidien du signal brut ORB vs sleeve overnight lundi+mardi équipondérée
US100/GER40, corrélées en séries temporelles agrégées, 2013-2026) :

- **Corrélation trimestrielle** : r = **0.041**, t = 0.29 (N=54 trimestres) — **statistiquement
  nulle**.
- **Corrélation annuelle** : r = **0.337**, t ≈ 1.19 (N=13 ans) — positif mais **non
  significatif** avec si peu d'observations annuelles ; à ne pas citer comme un résultat, juste
  comme une direction à surveiller (le repo interdit précisément de conclure sur un ΔSR/une
  corrélation non significative — même logique que L54/le gate ERC du dépôt).
- Lecture qualitative de la série annuelle : 2022 est bonne pour les deux (ORB +27.3 unités-R,
  overnight +0.174) ; mais 2016 est catastrophique pour l'ORB (-14.4) et légèrement positive pour
  l'overnight (+0.036) ; 2025 est très négative pour l'ORB (-13.7) et positive pour l'overnight
  (+0.068) — **aucun co-mouvement systématique visible à l'œil**, cohérent avec le r trimestriel nul.

**Verdict** : les deux régimes ne sont **ni corrélés ni anti-corrélés de façon mesurable** — ils
sont **proches de l'orthogonalité empirique** (r trimestriel ≈ 0, non significatif à l'échelle
annuelle). Conséquence pour le dimensionnement : le livre combiné ne bénéficie **pas** d'une
franche décorrélation qui réduirait le risque en période de stress commun (pas de preuve d'un
"quand l'un est mauvais l'autre compense"), mais il n'y a pas non plus de preuve que le risque
s'additionne systématiquement (pas de règle "les deux baissent ensemble"). Le risque partagé
identifiable n'est PAS macro-cyclique mais **structurel et commun aux deux sleeves** : toutes deux
sont des primes de risque sur le **même sous-jacent** (US100, et GER40 pour l'overnight) et
partagent donc le β actions pur en cas de choc — la corrélation qui compte pour un stress de type
avril 2025 ou COVID n'est pas visible dans un r calculé sur des rendements moyens de régime, elle
se manifeste dans la queue, que cette étude ne mesure pas (mesure de queue = tâche de l'agent de
mesure en parallèle, pas de celui-ci).

---

## Ce qu'il faudrait surveiller (seuils chiffrés, vérifiables)

1. **Fed funds (DFF, FRED, quotidien)** — franchissement sous **3.00%** : romprait le régime
   "taux non nuls" invoqué comme facteur favorable à l'ORB depuis mars 2022 (§B2).
2. **10Y-2Y (T10Y2Y, FRED, quotidien)** — repassage sous **0%** : ré-inversion, signal
   historique de fin de cycle, à recouper avec le régime ORB (l'inversion 2022-24 a coïncidé avec
   la meilleure tranche ORB — surveiller si une nouvelle inversion reproduit ou contredit ce
   pattern).
3. **VIX — fréquence des épisodes >35 séances (VIXCLS/vix_daily, quotidien)** — pas le niveau
   moyen (non discriminant, §A), mais le **nombre de séances >35 par trimestre glissant** :
   passage de 0 (régime actuel depuis avril 2025) à ≥3 signalerait un retour vers un régime de
   panique plutôt que de tendance rampante — à traiter différemment pour l'ORB (probable négatif)
   et pour l'overnight (littérature : neutre, la variance n'est pas le canal).
4. **WALCL YoY (FRED, hebdomadaire)** — repassage sous **0%** (fin du QT confirmée depuis ~T1
   2026, actuellement +1.9%/an) : signalerait une reprise du resserrement de bilan Fed.
5. **Concentration top-10 S&P 500 (source publique — pas de série FRED directe, à recalculer
   trimestriellement depuis les poids d'indice)** — repassage sous **30%** : romprait la prémisse
   de l'hypothèse Mag7-gap (§B3), à recouper avec la fréquence de cassure ORB mesurée ici (24% des
   jours en 2022-26 contre 16-20% avant).

---

## Note méthodologique — n_tests et limites

- **Δn_tests = 5** : (1) persistance directionnelle ORB par tranche, (2) décroissance overnight
  US100, (3) décroissance overnight GER40, (4) persistance différentielle lundi/mardi, (5)
  corrélation ORB×overnight (trimestrielle + annuelle comptées comme un seul test, deux
  fréquences de la même hypothèse). Base cumulée ≈ 1989 + 5 = **1994**. Correction Šidák
  approximative pour un test isolé à ce total : seuil t two-sided ≈ **4.1-4.2** (au lieu de
  ~1.96) pour une signification familywise à 5%. **Aucun des t-stats ci-dessus n'approche ce
  seuil** — tout est présenté comme diagnostic/directionnel, pas comme un PASS statistique, en
  cohérence avec le style du dépôt (`approx_multi_test_penalty`, pas un DSR formel puisqu'aucune
  stratégie n'est ici sélectionnée sur ces tests).
- **Toutes les hypothèses non testées mécaniquement sont marquées HYPOTHÈSE NON TESTÉE** dans le
  corps du texte (0DTE→gamma, fin ZIRP→rotation macro, Mag7→largeur d'OR normalisée, mardi→calendrier
  FOMC/macro, mécanisme NY Fed→transposition DAX).
- **Proxy ORB volontairement simplifié** : signal brut de cassure sans VWAP/gap/stop-loss/TP —
  utilisé uniquement pour tester un régime (fréquence et persistance de cassure), PAS pour
  mesurer la stratégie C (dont la mesure filtrée est la responsabilité de l'agent parallèle et vit
  dans `Futures/research/active/nq_intraday/`).
- **Aucune modification de code stratégie, aucun push, aucun accès VPS en écriture.** Fichiers
  temporaires de calcul dans `/tmp/` (hors dépôt, non committés). Le seul fichier livré dans le
  dépôt est ce rapport.
