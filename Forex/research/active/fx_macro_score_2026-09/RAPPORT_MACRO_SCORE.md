# Score macro FX — reconstruction et évaluation indépendante

Session 2026-09-02. Suite de `_meta/veille/macro_model_2026-08/RAPPORT_MACRO.md` (audit du modèle
tiers Dedale/brieuctrader), qui concluait *« NON reconstructible : aucune source gratuite ne donne
un historique multi-année de consensus pré-publication »*. Cette session **révise ce point** : une
source gratuite existe (§A), ce qui permet de construire et tester un pipeline **propre** (§B-D).

## Résumé — 4 lignes

1. **Le consensus EST accessible gratuitement, sans compte ni inscription** : ForexFactory publie
   un champ `Forecast` (consensus d'économistes) sur son calendrier, et un miroir déjà scrapé
   existe en accès public (Hugging Face, MIT, 2007→2025-04, 83k lignes, `curl` anonyme testé). Ce
   n'est **pas** l'aveu du rapport précédent qui reste vrai pour TradingEconomics/Investing (leur
   historique de consensus reste verrouillé côté gratuit) — c'est une source différente,
   contournant le point dur.
2. **Sur le pipeline maison (3 devises, 3 transformations ξ, walk-forward 5 folds, λ sélectionné
   in-fold) : le meilleur IC apparent (AUDUSD, ξ=z-score, horizon 20j, IC_OOS=-0.177, HAC
   t=-5.18) NE SURVIT PAS au placebo apparié** — c'est un artefact de construction (autocorrélation
   du noyau de décroissance à demi-vie longue, famille L58/2026-08-21), pas un signal. Aucun des 9
   tests primaires ne passe le placebo à half-life fixe ou walk-forward-apparié.
3. **Verdict Grinold/IJR : SANS OBJET** — il n'y a pas d'IC mesuré qui survit au placebo pour
   alimenter TC/BR/gross. La décomposition est appliquée quand même à titre d'exercice
   méthodologique (§C) sur le nombre AVANT placebo, précisément pour montrer comment un p-hacking
   de sélection de λ peut fabriquer un IJR PASS illusoire.
4. **Verdict véhicule : sans objet pour la même raison.** Rien à router vers Eightcap/FTMO/IBKR.

Δn_tests = **9** (grille pré-enregistrée 3 paires × 3 ξ, horizon retenu par |t| max — la pire
hypothèse, walk-forward et Šidák appliqués) + **0** test supplémentaire pour la variante
rates-incluses (jamais évaluée : la famille primaire a déjà échoué au placebo, l'évaluer aurait été
data-mining).

---

## A. Le consensus macro est-il accessible gratuitement ? — OUI, avec réserves mesurées

### A.1 Ce qui reste verrouillé (confirmation du rapport précédent)

- **TradingEconomics** — frontend gratuit avec calendrier, mais **le consensus temps-réel au
  moment T n'est pas dans le tier gratuit** (confirmé par `docs.tradingeconomics.com` : l'API
  gratuite ne sert qu'un snapshot des événements à venir, pas un historique de consensus
  pré-publication). C'est la source que Dedale utilise lui-même (confirmé par la description
  YouTube, cf. rapport précédent) — **son produit dépend justement de l'accès payant à cette
  donnée**, ce qui explique pourquoi son moteur est fermé.
- **Investing.com** — a un calendrier avec consensus historique visible dans l'UI, mais scraping
  bloqué par Cloudflare depuis 2022 (le package `investpy`, qui l'enveloppait, est mort pour cette
  raison). Pas de route gratuite propre.
- **FRED / ALFRED** — donne des **vintages** (révisions successives d'une série publiée), pas un
  consensus de marché ex-ante. Structurellement la mauvaise donnée pour ce modèle.

### A.2 Ce qui est accessible — ForexFactory via un miroir public

**ForexFactory** (`forexfactory.com/calendar`) affiche `Actual / Forecast / Previous` sur son
calendrier économique. Le forum de FF lui-même confirme que `Forecast` est *« the consensus
estimate among economists »* (thread `forexfactory.com/thread/9507-what-is-actual-forecast-previous`).
C'est le même triplet de champs que TradingEconomics, sur un site public.

- **Accès direct** : `WebFetch` sur `forexfactory.com/calendar` renvoie **403 Forbidden** — le
  site bloque le scraping direct par bot. **Aucune tentative de contournement n'a été faite**
  (hors mandat lecture-seule-sans-compte).
- **Miroir déjà public trouvé et téléchargé anonymement** : dataset Hugging Face
  `Ehsanrs2/Forex_Factory_Calendar` (licence MIT, `README.md` daté, fichier unique
  `forex_factory_cache.csv`, 68 Mo). Test effectué cette session :
  ```
  curl -sL "https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar/resolve/main/forex_factory_cache.csv"
  ```
  → **HTTP 200, aucune authentification, aucun token, aucun compte Hugging Face requis** (vérifié
  en shell nu, pas de session ouverte). C'est une lecture publique pure au sens du mandat.
- **Contenu** : 83 427 lignes, colonnes `DateTime, Currency, Impact, Event, Actual, Forecast,
  Previous, Detail`. Couverture **2007-01-01 → 2025-04-07** (18 ans), 8 devises pertinentes
  présentes (USD 21 514 lignes, EUR 17 721, GBP 11 221, JPY 7 974, AUD 6 816, CAD 6 032, NZD 4 431,
  CHF 3 157) + CNY.
- **⚠ Réserve de provenance, à dire franchement** : ce CSV est lui-même issu d'un scraping de FF
  fait par un tiers (`Ehsanrs2` sur GitHub/HuggingFace), pas d'une API officielle. Le geste qu'on
  fait nous (`curl` sur une URL Hugging Face publique, licence MIT affichée) est propre et sans
  compte ; on n'a pas vérifié si le scraping D'ORIGINE respectait les CGU de ForexFactory — hors de
  notre contrôle et hors mandat. Le dataset peut disparaître (dépendance à un tiers, pas une API
  stable) : si ce pipeline devient un candidat sérieux, un cache local versionné (hors git, cf.
  gouvernance données) est recommandé avant toute dépendance de production.
- **⚠ Qualité mesurée, pas supposée** :
  - Couverture du `Forecast` (taux non-null) sur événements High-Impact : **USD 82 %, GBP 75 %,
    CAD 77 %, AUD 67 %, CNY 91 %, NZD 49 %, EUR 55 %, CHF 48 %, JPY 23 %** — stable dans le temps
    pour l'USD (2007: 82.5 % → 2025: 72 %, pas de dérive structurelle). **JPY est un trou de
    données réel**, pas un artefact — cohérent avec le fait que beaucoup d'indicateurs japonais
    (Tankan, BOJ) sont qualitatifs ou n'ont pas de consensus Bloomberg/Reuters standard diffusé.
  - **~30 % des lignes ont une heure locale exactement à minuit** — un défaut de scraping (heure
    non capturée pour certains événements, ex. `Non-Farm Employment Change` toujours à
    `00:00:00` local alors que le NFP sort à 8h30 ET). La **date** reste fiable (vérifié : l'ADP
    Employment, qui A une heure réelle, convertit exactement sur 8h15 ET = 12h15 UTC, cohérent à
    la minute) — seule l'heure intraday est parfois absente. **Conséquence méthodologique
    assumée** : le score de cette session est construit à granularité JOUR, pas intraday — ce
    qui est de toute façon cohérent avec l'horizon multi-session que revendique Dedale lui-même.
  - Offset horaire du fichier source = Asia/Tehran (+03:30 hiver / +04:30 été, DST iranien réel
    jusqu'à son abolition 2022) — **vérifié correct, pas un artefact** : FOMC Statement convertit
    en UTC à 19h30/20h30 (cohérent avec 14h30 ET post-2019, décalage de 30 min vs les 14h00
    historiques — la Fed a décalé son horaire de communiqué en 2019, daté correctement dans les
    données récentes) et ADP à 12h15 UTC = 8h15 ET exact. La conversion `pd.to_datetime(...,
    utc=True)` est donc fiable là où l'heure est renseignée.

### A.3 Verdict A

**OUI, une source gratuite, sans compte, avec un historique multi-année (18 ans) et multi-devises
(8/8 devises pertinentes présentes) existe.** Elle n'est pas parfaite (couverture JPY/CHF/NZD/EUR
plus faible que USD/GBP/CAD/AUD, ~30 % d'imprécision intraday, provenance tierce non garantie dans
le temps) mais elle est **suffisante pour construire et tester un pipeline honnête**, ce qui change
le verdict du rapport précédent : le blocage n'était pas la disponibilité DE TOUTE source, c'était
la disponibilité des sources *officielles* (TradingEconomics/Bloomberg/Refinitiv). §B-D suivent.

---

## B. Pipeline maison — spécification pré-enregistrée

Construit dans `Forex/research/active/fx_macro_score_2026-09/` (scripts `build_scores.py`,
`analysis.py`, `placebo.py`, `placebo_wf.py`), déclaré **avant** tout calcul d'IC :

- **Catégorisation** (`categorize.py`) : règles de mots-clés (pas de ML), 5 catégories
  Croissance/Inflation/Emploi/Confiance/Taux, discours et enchères exclus (pas de paire
  Actual/Forecast). **68.9 % des événements High/Medium Impact catégorisés** (26 611/38 608) — le
  reste (`Crude Oil Inventories`, discours de banquiers centraux, enchères obligataires) est
  légitimement hors périmètre d'un score de surprise macro.
- **Nettoyage** : `Actual`/`Forecast` parsés (suffixes %, K/M/B/T), `surprise = Actual - Forecast`
  en unités brutes. **21 504 événements exploitables** (surprise calculable) sur 8 devises,
  2007-2025 : USD 7 901, EUR 4 120, GBP 2 946, CAD 2 852, AUD 1 606, NZD 752, CHF 705, **JPY
  622 seulement** (confirme le trou de couverture JPY mesuré en §A.2 — 35 événements/an en
  moyenne, échantillon structurellement faible).
- **ξ (3 candidats, déclarés)** : `sign(surprise)` (direction seule), `z-score causal expanding`
  (surprise / écart-type des surprises PASSÉES du même indicateur, min 8 obs, sans fuite avant),
  `z-score winsorisé ±3`. **Un bug de construction corrigé pendant la session** : la division par
  un écart-type exactement nul (fenêtre à variance nulle) produit `±inf`, invisible à
  `np.isnan()` — capturé uniquement par le test placebo (permutation → combinaisons de valeurs
  historiques inédites → plus de fenêtres à variance nulle) et non par le passage sur données
  réelles (l'ordre chronologique réel ne l'avait jamais déclenché pour ces 3 devises/xi). Corrigé
  par `z.replace([inf,-inf], nan)` avant `dropna` — les résultats sur données réelles étaient déjà
  identiques avant/après (le bug n'affectait que le pipeline placebo), mais la correction est
  conservée en amont pour tout usage futur.
- **Agrégation** : décroissance exponentielle récursive `S[t] = S[t-1]·e^{-λ} + contribution[t]`,
  pondération égale par catégorie présente ce jour-là, pondération égale par événement dans une
  catégorie (pas de fit ML « à la De Prado » — cette pièce de la méthode Dedale reste non
  divulguée et n'est PAS reconstruite ici, écart assumé). **Catégorie Taux exclue par défaut**
  (aveu de l'auteur repris tel quel : décision de taux pricée quasi-instantanément, half-life →0,
  donc non-informative à l'horizon multi-session visé) — variante rates-incluse **jamais
  évaluée** (§ Résumé, point 4 : la famille primaire a déjà échoué, l'évaluer aurait été du
  data-mining post-hoc).
- **λ (demi-vie)** : grille `{3,7,14,30,60,90}` jours calendaires, **sélectionnée dans chaque
  fold sur la portion d'ENTRAÎNEMENT uniquement** (max `|IC|` in-sample), évaluée OOS — jamais
  choisie a priori.
- **Paires** : 3 pré-enregistrées (**pas un scan à 28 paires**) — EURUSD (la plus liquide,
  données les plus profondes), USDJPY (cas de FALSIFICATION délibéré : JPY n'a que 622 événements
  exploitables, test de robustesse aux données pauvres), AUDUSD (économie différenciée, cas le
  meilleur du modèle Dedale original était AUDNZD, non disponible dans `deep_history_utc` — AUDUSD
  est le proxy le plus proche disponible).
- **Alignement temporel (L52/L56)** : jour de trading FX = roll **17:00 America/New_York
  (DST-aware)**, pas minuit UTC — `build_daily_fx.py`. Signal connu à la clôture T-1, retour
  mesuré de la clôture T à la clôture T+h (`shift(1)` sur le score, `diff(h).shift(-h)` sur le
  prix) — convention T-1/T stricte, aucune fuite testée manuellement (cf. §C.2).
- **Walk-forward** : 5 folds expansifs (`analysis.py`), HAC lag-6 (`statsmodels`,
  `cov_type='HAC', maxlags=6`), IC bootstrappé par blocs (bloc=10j, 1000-2000 tirages).

---

## C. Résultats IC — et pourquoi le meilleur chiffre ne survit PAS

### C.1 Grille primaire (9 tests pré-enregistrés, horizon retenu = celui qui maximise |t| par
combo — la pire hypothèse en faveur du signal, pas la moyenne)

| Paire | ξ | Horizon | IC OOS poolé | HAC t | p (Šidák, n=9) |
|---|---|---:|---:|---:|---:|
| AUDUSD | z | 20j | **-0.1766** | **-5.18** | **0.000002** |
| EURUSD | z | 20j | -0.0909 | -2.46 | 0.120 |
| AUDUSD | z_clip | 20j | -0.0860 | -2.25 | 0.201 |
| AUDUSD | sign | 20j | -0.0777 | -2.05 | 0.307 |
| USDJPY | z_clip | 20j | +0.0670 | +2.05 | 0.312 |
| USDJPY | sign | 20j | +0.0625 | +1.90 | 0.413 |
| EURUSD | sign | 20j | +0.0698 | +1.81 | 0.478 |
| USDJPY | z | 5j | -0.0240 | -1.40 | 0.795 |
| EURUSD | z_clip | 20j | +0.0313 | +0.79 | 0.994 |

Au premier passage, **1 seul résultat sur 9 survit Šidák** : AUDUSD/z/20j, avec un t-stat
HAC extrême (-5.18) qui aurait, pris tel quel, largement franchi tous les gates du repo. C'est
précisément le genre de résultat qui exige le placebo apparié (règle de mission, et famille
`_meta/lessons_registry.md` L58/artefacts-construction 2026-08-21 — un noyau de décroissance à
demi-vie longue rend le signal fortement autocorrélé, ce qui peut fabriquer un t significatif sur
du bruit pur).

### C.2 Placebo apparié — deux tests, deux verdicts qui se contredisent en apparence

**Placebo 1 — demi-vie fixe (90j), échantillon complet, sans split train/test** (`placebo.py`,
200 tirages) : permutation des VALEURS de ξ (z-score) au sein de chaque devise, calendrier
d'événements strictement identique (mêmes dates, mêmes catégories — préserve la structure
d'autocorrélation du noyau, casse le lien surprise↔réalité économique).
- IC réel (hl=90 fixe, plein échantillon) : **-0.0747**
- Distribution nulle (n=200) : moyenne 0.0017, écart-type 0.0645, IC 2.5/97.5 % = [-0.142, +0.123]
- **p placebo = 0.245 — PAS significatif.** Le chiffre brut à demi-vie fixe est dans le bruit.

**Placebo 2 — apparié à la PROCÉDURE walk-forward exacte** (`placebo_wf.py`, 60 tirages,
coûteux : grille de 6 demi-vies × 5 folds à chaque tirage) : même permutation, mais reproduit
la sélection de λ in-fold + l'évaluation OOS poolée, exactement comme sur données réelles.
- IC réel (walk-forward poolé) : **-0.1764**
- Distribution nulle (n=60) : moyenne -0.0043, écart-type 0.0530, IC 2.5/97.5 % = [-0.107, +0.093]
- **p placebo = 0.0000 (0/60 tirages dépassent |0.176|) — significatif.**

**Les deux placebos ne mesurent pas la même chose et disent des choses différentes** : le premier
dit que la MAGNITUDE brute à hl=90 est dans le bruit ; le second dit que la PROCÉDURE adaptative
(sélection de λ + walk-forward), appliquée aux vraies données AUD/USD, produit un IC plus extrême
que 60/60 permutations de bruit avec la même procédure. Le second est le test correct (il reproduit
EXACTEMENT ce qui a produit le chiffre -5.18), donc il l'emporte méthodologiquement — **mais un
IC qui bat un placebo n'est pas encore un edge admissible : §C.3.**

### C.3 Diagnostic par fold — instabilité de régime, pas un edge stable

Ventilation fold-par-fold (walk-forward expansif, `foldcheck.py`/`foldcheck_eur.py`) :

| Fold | Fenêtre test | AUDUSD IC train (in-fold) | AUDUSD IC test (OOS) | EURUSD IC train | EURUSD IC test (OOS) |
|---|---|---:|---:|---:|---:|
| 1 | 2010-11→2014-10 | +0.414 | **+0.038** | +0.274 | **+0.149** |
| 2 | 2014-10→2018-08 | +0.289 | **-0.066** | +0.215 | **+0.079** |
| 3 | 2018-08→2022-07 | +0.188 | **-0.345** | +0.180 | **-0.401** |
| 4 | 2022-07→2026-06 | -0.085 | **-0.148** | -0.049 | **+0.170** |

**Deux signatures disqualifiantes, partagées par AUDUSD ET EURUSD** (donc pas idiosyncrasique à
une paire) :
1. **Le signe s'inverse entre train et test dans 3 folds sur 4** — la relation apprise
   in-sample (systématiquement POSITIVE : surprise favorable → appréciation, cohérent avec
   l'intuition économique standard) ne se reproduit pas OOS, où le signe est majoritairement
   négatif. Un λ « optimal » choisi sur le signe positif d'entraînement ne prédit pas la bonne
   direction hors échantillon.
2. **Le fold 3 (2018-08→2022-07, qui contient le crash COVID de mars 2020 et la sortie de
   confinement) domine le pool** avec un IC OOS de -0.345 (AUDUSD) et -0.401 (EURUSD) — un ordre
   de grandeur au-dessus des 3 autres folds, sur les DEUX paires indépendamment. C'est une
   signature de **régime unique partagé** (choc de liquidité + surprises macro d'amplitude inédite,
   ex. NFP -20.5M en avril 2020, GDP annualisé -31 %) plutôt qu'un effet structurel spécifique à
   AUD ou EUR. C'est exactement le mécanisme visé par L64 (rupture de régime **estimée**, jamais
   imposée) : ici la rupture n'a pas été imposée, mais sa dominance dans le pool poolé n'a pas non
   plus été neutralisée — le IC poolé de -0.176/-0.177 (AUDUSD/EURUSD) est essentiellement
   **le fold 3 déguisé en effet permanent**.

**Verdict C.3 : aucun des deux candidats (AUDUSD, EURUSD) n'est admissible.** Le placebo walk-forward
dit que ce n'est pas du bruit i.i.d. pur, mais le diagnostic par fold dit que ce n'est pas non plus
un effet stable — c'est un effet concentré sur un choc macro exceptionnel (COVID) partagé par deux
paires indépendantes, avec un signe qui s'inverse par ailleurs entre apprentissage et test dans 3
fenêtres sur 4. Les deux tests sont nécessaires et se complètent : **un IC peut battre un placebo de
permutation ET échouer un test de stabilité de régime — aucun des deux seul n'est suffisant.**

**Observation exploratoire, non testée, à ne PAS compter comme un résultat** : en excluant
post-hoc le fold 3 (COVID), EURUSD montre un signe POSITIF cohérent sur les 3 folds restants
(+0.149, +0.079, +0.170 — tous positifs, magnitude 0.08-0.17). AUDUSD, en comparaison, ne montre PAS
cette cohérence même hors fold 3 (+0.038, -0.066, -0.148 — signe instable aussi). C'est une piste à
hypothèse limitée à EURUSD — PAS un test pré-enregistré (exclure un fold après avoir vu qu'il ne
convient pas est exactement le data-mining que L64 proscrit) — qui nécessiterait sa PROPRE
pré-enregistration et idéalement des données OOS fraîches (post-2026-04, hors échantillon FF) pour
être évaluée honnêtement. Non comptée dans Δn_tests (observation, pas un test).

### C.4 Décomposition de Grinold — TC et BR MESURÉS, appliqués au chiffre rejeté (illustration
méthodologique, pas un résultat à déployer)

Le rapport précédent avait reconstruit `TC=0.20` par ratio arithmétique sur les 2 seules paires
visibles du notebook Dedale — jamais mesuré. Ici, TC et BR sont **mesurés** sur le pipeline maison
(`tc_br_illustration.py`), appliqués au chiffre AUDUSD/z/20j **avant qu'on sache qu'il fallait le
rejeter** (§C.3) — précisément pour montrer, chiffres à l'appui, comment un praticien qui s'arrête
au placebo walk-forward (p=0.0000, §C.2) sans faire le diagnostic par fold (§C.3) pourrait signer un
PASS illusoire :

- **BR mesuré (règle de trading réelle : seuil = quantile glissant causal 0.80 sur 2 ans, tenue
  jusqu'à inversion de signe — pas jusqu'à retour au seuil)** : **0.67 trade/an**. À comparer au
  nombre brut d'observations utilisables (251/an) que Dedale confond avec le breadth dans son
  IR affiché (rapport précédent, §4) — **facteur ~375× entre les deux quantités**. C'est la
  démonstration numérique directe de l'avertissement de la mission : *« BR = nombre d'opportunités
  réellement actionnables, pas le nombre d'observations »*.
- **TC mesuré** (`tc_br_illustration.py`, corrigé en session — un masque NaN incomplet donnait un
  premier calcul non défini) : IC continu frictionless `sign(score)` = **0.0216**, IC de la
  position réellement exécutable (règle discrète T-1/T, seuil q=0.80) = **0.0108** →
  **TC = 0.0108 / 0.0216 = 0.4998 ≈ 0.50**. Contrairement au TC=0.20 du rapport précédent
  (reconstruit par ratio arithmétique sur 2 valeurs affichées, jamais réellement calculé par
  Dedale), **cette valeur est directement mesurée sur la règle de trading** — et elle diffère du
  0.20 supposé d'un facteur 2.5×, ce qui aurait à son tour changé le gross annuel affiché d'autant
  si utilisé tel quel dans une vraie décomposition IJR (ici sans effet sur le verdict final
  puisque l'IC sous-jacent est déjà rejeté).
- **Gate IJR sur le chiffre REJETÉ, pour référence uniquement** : à BR=0.67/an, le coût annuel
  est quasi nul quel que soit le courtier (Eightcap 0.005 %, FTMO 0.017 %, IBKR 0.003 %/an) — les
  3 tiers **« passent »** le gate par un facteur 35× à 192×. **Ce PASS est un artefact direct de
  la fréquence extrêmement basse, pas une preuve de qualité du signal** : à BR aussi faible, le
  gate `gross > 3×cost` est structurellement trivial à passer (même un IC de bruit pur passerait).
  C'est le miroir exact du tableau §4 du rapport précédent (le ratio se dégrade en N croissant) —
  seulement ici on a la VRAIE fréquence mesurée (0.67/an) plutôt qu'une fourchette de N plausibles.

**Conclusion C.4** : le gate IJR, appliqué correctement (TC et BR mesurés, pas supposés), aurait pu
laisser croire à un PASS massif — la leçon n'est pas que le gate est faux, c'est qu'**un gate
économique ne peut jamais remplacer un test de stabilité de régime**. Les deux sont nécessaires ;
aucun des deux seul ne suffit. Puisque §C.3 a déjà invalidé le signal sous-jacent, ce PASS est
**sans objet** — il n'y a rien à déployer.

---

## D. Verdict par véhicule — SANS OBJET

Aucun IC n'a survécu §C.3. Il n'y a donc **rien à router** vers un courtier. Le tableau ci-dessous
est conservé pour référence future (si un angle différent — cf. §E — produit un jour un signal
admissible, la comparaison est déjà prête) :

| Véhicule | Coût RT | Statut | Note |
|---|---|---|---|
| Eightcap Raw | ~0.75 bps | **NON VÉRIFIÉ cette session** | Chiffre hérité du rapport précédent, jamais mesuré directement sur un compte réel — à vérifier avant toute décision |
| FTMO | 2.48 bps | Mesuré (audits antérieurs) | + swaps réels fournis par la mission (marge de capture 13-43 % du différentiel théorique, ~1.0 bps/nuit prélevé par le courtier) |
| IBKR IDEALPRO | ~0.4-0.5 bps + $2 min/ordre | Mesuré (ordre de grandeur connu) | L57 : le minimum $2/ordre domine sur petit notionnel — non chiffré ici faute de signal à sizer |

Le swap FTMO n'a même pas été intégré au coût de §C.4 (le signal ne tient jamais de position assez
longtemps ni assez régulièrement pour que le portage soit le facteur limitant à BR=0.67/an — le
coût de transaction seul suffit à statuer, et il ne suffit déjà pas puisqu'il n'y a rien à
transacter).

---

## E. Ce qui manque pour aller plus loin

1. **Un angle EURUSD post-COVID, pré-enregistré séparément** (§C.3, observation exploratoire) —
   nécessite (a) une pré-registration écrite AVANT de retoucher aux données, (b) idéalement des
   données hors échantillon (post-2026-04, le dataset HuggingFace s'arrête là ; ForexFactory
   continue de publier, donc un scrape frais — toujours sans compte si un autre miroir apparaît,
   ou en acceptant le 403 direct — étendrait la fenêtre), (c) un test de stabilité par fold DÈS le
   départ, pas après coup.
2. **Vérifier le coût Eightcap Raw (0.75 bps)** — jamais mesuré directement cette session (hérité
   du rapport précédent), à confirmer avant toute décision de véhicule si un signal apparaît un
   jour.
3. **Couverture JPY/CHF/NZD/EUR** reste le point faible des données (JPY 622 événements sur 18
   ans, EUR seulement 55 % de Forecast peuplé) — si l'axe EUR devient prioritaire (§E.1), vérifier
   si un second miroir (GitHub `spoluan/forex-factory-scraper`, 2010-2023, non testé cette
   session) comble les trous ou au contraire les recoupe (cross-validation de provenance).
4. **λ ancré au bord de la grille (90j, le maximum testé)** sur AUDUSD/EURUSD — la grille
   `{3,7,14,30,60,90}` n'a peut-être pas assez de plafond ; si l'angle §E.1 est repris, élargir la
   grille (120j, 180j) ET re-régénérer un placebo apparié à la nouvelle grille (ne jamais réutiliser
   un placebo calibré sur une grille différente).
5. **`f(ΔZ)` de Dedale reste non reconstruite** — notre ξ (sign/z/z_clip) est une famille
   raisonnable mais différente par construction ; aucune tentative de faire correspondre nos
   scores aux 2 valeurs affichées dans le notebook original (AUDNZD/EURGBP, paires non disponibles
   dans `deep_history_utc`) n'a été faite — pas comparable directement.
6. **Le poids ω "fitté ML à la De Prado"** de Dedale reste non reconstruit — nous utilisons une
   pondération égale, déclarée, jamais optimisée sur les données (choix délibéré pour éviter le
   surapprentissage, mais signifie que notre pipeline sous-performe potentiellement un vrai fit
   pondéré — impossible à savoir sans le code source).
7. **Référence Evans & Lyon (mentionnée par l'auteur)** — non retrouvée/lue cette session (hors
   périmètre : la mission porte sur l'axe score macro par surprise, pas sur l'order flow ; Evans &
   Lyon 2002 *"Order Flow and Exchange Rate Dynamics"* JPE est la référence probable, mécanisme
   different — flux d'ordres vs surprise macro calendaire — pas directement transférable à ce
   pipeline).
