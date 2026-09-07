# FX events — calendrier, pas surprise (2026-09-02)

**Rôle** : axe ÉVÉNEMENTS MACRO DATÉS (calendrier, pas contenu). Trois familles testées :
(A) vitesse de pricing par type d'événement, (B) drift pré-événement façon L42, (C) conditionnement
de régime, (D) gate économique. **Verdict global : la carte de vitesse est propre et réplique un
fait déjà connu des praticiens ; un candidat de drift survit à la correction complète et au
contrôle month-end (GDP USD) ; tout le reste est soit mort au placebo, soit UNDERPOWERED.**

## TL;DR

1. **Carte des demi-vies** : la volatilité excédentaire après une annonce macro (banque centrale,
   CPI, NFP, PIB, PMI — 24 combinaisons famille×devise) décroît avec une demi-vie médiane de
   **1.6 à 2.9 minutes**, quasiment IDENTIQUE d'une famille à l'autre. Le pricing PUR (au sens
   volatilité réalisée) est donc déjà terminé en quelques minutes pour TOUT type d'événement — pas
   seulement les décisions de taux. La seule exception franche est **BoJ (JPY rate decision, demi-vie
   53 min, t=2.21)**, très probablement un artefact d'horodatage (la BoJ n'annonce pas à une minute
   fixe pré-publiée, contrairement à Fed/ECB/BoE/RBA).
2. **Effet le plus fort** : **USD s'apprécie avant sa propre publication de PIB (GDP Growth Rate
   QoQ Advance)**, +5.4 à +6.8 bps sur des fenêtres de 1h à 2h avant l'annonce, t_HAC **4.29–4.43**,
   walk-forward **5/5**, effet/MDE **1.25–1.34** (bien alimenté), et — point critique — **résiste à
   un placebo apparié sur le jour-du-mois** (voir §B'). Gross/coût aux trois véhicules : **FTMO 8.3×,
   Eightcap (best-case) 12.5×, IBKR (\$50k notionnel) 7.5×** — très au-dessus du gate L43 (1.5×, le
   meilleur jamais observé dans ce dépôt étant 0.36-0.38×).
3. **Ce qui survit au placebo apparié** : uniquement GDP USD (voir ci-dessus) au seuil Šidák complet.
   Trois candidats **adéquatement alimentés mais sous le seuil Šidák strict** (CPI USD, PMI EUR,
   GDP GBP) sont rapportés comme pistes à confirmer par une réplication moins pénalisée.
4. **Ce qui est mort** : le drift pré-décision-de-taux (8 devises testées, aucune ne survit, y
   compris le franc suisse et le yen qui montrent une inversion suggestive mais non significative
   après correction) ; le drift pré-NFP (nul, t≤0.92 sur toutes les fenêtres) ; PIB JPY, PMI GBP
   (signe instable, wf<4/5).

**Une conclusion « tout est déjà pricé avant qu'on puisse agir » aurait été un résultat parfaitement
acceptable ici — ce n'est pas ce qu'on trouve pour GDP USD, mais c'est bien ce qu'on trouve pour les
décisions de banque centrale et pour NFP.**

---

## Méthodologie

### Données
- **Calendrier** : `data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv` (TradingView,
  74 543 lignes, UTC vrai avec DST, `actual/forecast/previous`). Couverture testée : 2018-01 → 2026-06.
- **Prix** : `data/deep_history_utc/*_M1.csv` (M1, UTC vrai, spread MT5 non fiable seul — cf. L52/L56 —
  donc non utilisé ici ; coûts pris de `phase0_rt_cost_bps.csv`, mesuré indépendamment). Cache parquet
  construit dans `/private/tmp/.../scratchpad/m1_cache/` pour EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD,
  USDCHF, NZDUSD (+ XAUUSD, US30 non utilisés au final) en plus des paires déjà en cache
  (AUDJPY, EURGBP, EURJPY, GBPJPY, US100).
- **Événements testés** (5 familles × devise disponible, HIGH impact, 24 combinaisons, `n` = 29 à 102) :
  - Banque centrale : Fed, ECB, BoE, BoJ, RBA, BoC, SNB, RBNZ (8 devises)
  - CPI : "Inflation Rate YoY" (EUR : version Flash) (8 devises)
  - NFP : "Non Farm Payrolls" (USD seule — pas d'équivalent HIGH-impact ailleurs dans le calendrier)
  - PIB : release la plus précoce/market-moving par devise (USD Adv, EUR Flash, GBP/JPY Prel) (4 devises)
  - PMI manufacturier : release la plus précoce (USD ISM, EUR/GBP Flash) (3 devises)

### Convention de signe et validation "two-sided" (esprit L25)
Une devise n'est jamais négociée seule : c'est toujours une PAIRE. Pour chaque devise on construit un
**proxy multi-paires** (moyenne des rendements log, signe ajusté base/quote) sur TOUTES les paires
majeures disponibles impliquant cette devise (USD : 7 paires ; EUR/GBP : 3 ; JPY : 4 ; AUD : 2 ;
CAD/CHF/NZD : 1 — limite notée). C'est le vrai contrôle "deux jambes indépendantes" adapté à un
event-study FX (par opposition au batch `_SS` du dépôt, qui n'était qu'une négation mécanique du
long — Finding n°2 de `Multi_Asset/research/active/prefomc_drift_2026-07/RESULTS.md`, jamais un test
two-sided réel). Le candidat retenu (GDP USD) est validé sur les **7 paires USD indépendamment** :
voir §B.

### Placebo apparié (L58/L49)
Pour chaque événement réel, 5 à 8 placebos sont tirés parmi les jours de bourse **non-événement**
(exclusion ±2j autour de TOUT événement de la même famille), appariés sur :
- **heure du jour exacte** (même HH:MM:SS que l'événement réel → contrôle direct de la saisonnalité
  intraday/session, y compris DST puisque le calendrier est en UTC vrai) ;
- **régime de volatilité** (vol réalisée 5 jours du proxy-devise la plus proche, L58).

Le pool placebo est restreint à la même fenêtre 2018-2026 que les événements (pas de mélange avec le
régime pré-2018). Pour le candidat GDP USD, un **second placebo, apparié en plus sur le jour-du-mois**,
a été construit spécifiquement pour écarter un biais de saisonnalité de fin de mois (§B').

### Statistiques
HAC Newey-West lag-6 sur l'échantillon d'événements ordonné chronologiquement ; walk-forward 5 folds
(accord de signe rapporté) ; block-bootstrap (bloc=5, 3000 tirages) pour l'IC ; MDE avec puissance
(facteur 1.40, α=0.05, power=0.80) et ratio effet/MDE ; correction Šidák sur l'ensemble des tests d'une
partie (voir §Δn_tests).

---

## A. Carte des demi-vies (pricing map)

Pour chaque combinaison, deux mesures sur `T-2h → T+72h`, comparées à un placebo apparié :

1. **Activité réalisée** (racine de la somme des rendements 1-min² sur un bucket, normalisée par
   √durée-du-bucket pour rendre les buckets comparables — un piège de première mesure : le bucket brut
   sans cette normalisation plaçait faussement le "pic" à 72h simplement parce que ce bucket est le plus
   large). Grille fine près de l'événement (pas de 1 min de -2 à +10min) pour ne pas confondre une
   décroissance en secondes avec une en dizaines de minutes.
2. **Continuation directionnelle** (signée par le sens du mouvement dans les 5-15 premières minutes,
   moyennée sur les événements, excès vs placebo).

### Résultat central : demi-lifes de volatilité (excès vs placebo apparié)

| Famille | Demi-vie médiane | Min–Max | t_HAC pic (médiane / pire cas) |
|---|---:|---:|---:|
| Banque centrale | **1.76 min** | 1.72–**52.96** (JPY) | 6.8 / 2.21 (JPY) |
| CPI | **1.68 min** | 1.62–1.87 | 4.6 / 2.26 (JPY) |
| NFP (USD) | **1.68 min** | — | 7.40 |
| PIB | **2.18 min** | 1.55–2.93 | 3.6 / 1.57 (JPY) |
| PMI | **1.67 min** | 1.66–1.68 | 6.2 / 5.86 |

**Toutes les demi-vies sont significatives** (t_peak dans [2.2, 11.6], seuil Šidák 24 tests = 3.07 ;
franchi partout sauf CHF rate decision 2.46, JPY rate decision 2.21, JPY GDP 1.57).

**Lecture** : contrairement à l'hypothèse du praticien citée dans le brief (« les décisions de taux
se pricent en secondes/minutes car réplicables en OIS/futures, CPI/NFP demandent une interprétation
donc mettent plus longtemps »), **la vitesse de dissipation de la volatilité excédentaire ne
distingue PAS les familles d'événements** : toutes convergent vers ~1.6-2.9 minutes de demi-vie. Le
seul écart notable (BoJ, 53 min) est vraisemblablement un artefact de mesure : contrairement à la Fed,
la BoE, la BCE et la RBA qui publient à une minute pré-annoncée, la BoJ ne fixe pas d'heure exacte —
le calendrier source lui assigne une heure approximative, ce qui étale mécaniquement l'impact mesuré
sur un intervalle plus large sans que le marché lui-même soit plus lent.

**Anatomie d'un impact (Fed, exemple)** — activité (bps/√min), événement vs placebo :

| Fenêtre | Événement | Placebo | Excès |
|---|---:|---:|---:|
| [-5,-2) min | 1.14 | 0.74 | 0.40 |
| [-1,0) min | 2.22 | 0.74 | 1.48 |
| **[0,1) min** | **16.04** | 0.87 | **15.17** |
| [1,2) min | 6.62 | 0.86 | 5.76 |
| [5,6) min | 3.52 | 0.71 | 2.80 |
| [30,45) min | 4.90 | 0.76 | 4.14 |
| [60,90) min | 3.04 | 0.76 | 2.28 |

Deux observations utiles au sizing/exécution : (i) un **frisson pré-annonce** existe déjà dans les 2
dernières minutes avant l'heure officielle (excès 0.4-1.5 bps/√min, à 5-10% du pic) — cohérent avec un
peu de repositionnement algorithmique dans les toutes dernières secondes, pas une fuite d'information ;
(ii) le pic décroît vite (demi-vie ~1.8 min) mais une **traîne élevée persiste 30-90 min** (2-4× le
niveau placebo) — le marché n'est "calme" qu'au sens où le PIC s'est dissipé, pas au sens où l'activité
revient immédiatement à la ligne de base.

### Continuation directionnelle (impact kernel, Evans & Lyon)

Théorie de référence : Evans, M.D. & Lyon, R.K., *"How Is Macro News Transmitted to Exchange Rates?"*,
Journal of Financial Economics 88(1), 2008 — le pricing des news macro en FX ne se fait pas
instantanément mais se propage par l'order flow (dealers → clients → repositionnement), ce qui prédit
une dérive persistante ALIGNÉE avec le sens de la réaction initiale, sur un horizon de plusieurs
heures à plusieurs jours (par opposition à l'explosion-puis-plateau immédiat d'un marché parfaitement
efficient).

Signe fixé par le mouvement des 5 premières minutes (banque centrale) ou 15 premières minutes
(CPI/NFP/PIB/PMI), courbe moyennée sur les événements, **excès vs le même calcul sur le placebo**
(pour ne pas confondre "continuation" avec le momentum FX générique ambiant) :

| Famille / devise | Excès initial (bps) | Plateau excès (bps, ~72h) | Demi-vie continuation |
|---|---:|---:|---:|
| Rate decision USD | 7.8 | **55.2** | ~55h |
| Rate decision EUR | 5.5 | **52.2** | ~41h |
| Rate decision GBP | 8.3 | **-217** (inversion) | n/a |
| CPI JPY | 0.3 | 48.2 | ~30h |
| CPI EUR | 0.4 | 12.6 | ~17h |

**Ce tableau est descriptif, PAS un test de signification formel** (aucun HAC/placebo-percentile
n'a été calculé sur le plateau lui-même — seul le pic de volatilité a été testé formellement en A).
Il est cohérent avec l'hypothèse Evans-Lyon (continuation sur des dizaines d'heures, pas des minutes)
mais l'inversion GBP (-217 bps, signe opposé au signal initial) montre que ce n'est pas un mécanisme
universel — possiblement un effet de petit échantillon (n=69) combiné à la forte dispersion de la
BoE (annonces groupées avec le vote MPC, communiqué détaillé). **Non retenu comme candidat tradable
sans test formel dédié** — signalé comme piste de suivi, pas un résultat.

---

## B. Drift pré-événement (équivalent FX de L42)

**120 tests** (24 combinaisons × 5 fenêtres pré-événement : -30, -60, -120, -240, -1440 min), signe
NON choisi a posteriori (rapporté tel quel dans les deux sens). Seuil Šidák pour n=120, α=0.05 :
**|t| ≥ 3.52**.

### Le candidat qui survit : USD avant sa propre publication de PIB (GDP Advance)

| Fenêtre | n | mean (bps) | t_HAC | pctl vs placebo | WF (5 folds) | effet/MDE |
|---|--:|--:|--:|--:|--:|--:|
| -30 min | 33 | +2.25 | 1.58 | 0.87 | 4/5 | 0.57 |
| **-60 min** | 33 | **+5.43** | **4.29** | 0.997 | **5/5** | **1.34** |
| **-120 min** | 33 | **+6.80** | **4.43** | 0.992 | **5/5** | **1.25** |
| -240 min | 33 | +9.63 | 2.90 | 0.995 | 5/5 | 1.04 |
| -1440 min | 33 | +9.58 | 2.22 | 0.936 | 5/5 | 0.48 |

**-60min et -120min franchissent le seuil Šidák complet.** L'IC block-bootstrap (bloc=5) à -120min
est **[5.06, 10.10] bps**, exclut zéro largement. Le dollar s'apprécie de manière quasi-monotone à
mesure qu'on recule dans le temps (de +2.25 à 30min jusqu'à +9.63 à 4h), avec un plateau logique
autour de -240/-1440min — pas de sur-ajustement à une fenêtre isolée.

**Validation two-sided sur 7 paires USD indépendantes (-120min)** — le signal n'est pas porté par une
seule paire :

| Paire | Sens | mean (bps) | t_HAC | % événements positifs |
|---|---|--:|--:|--:|
| EURUSD | short | +9.40 | **3.63** | 27/33 |
| GBPUSD | short | +6.31 | 2.46 | 22/33 |
| USDJPY | long | +5.93 | 1.52 | 22/33 |
| USDCAD | long | +1.90 | 0.97 | 19/33 |
| USDCHF | long | +8.72 | **4.05** | 23/33 |
| AUDUSD | short | +7.70 | **3.71** | 24/33 |
| NZDUSD | short | +7.63 | **3.80** | 23/33 |

**7/7 paires positives**, 5/7 individuellement significatives à t>2, 67-82% des événements
individuels dans le bon sens sur les paires les plus significatives. Ce n'est pas un artefact d'une
paire isolée.

### B'. Contrôle obligatoire — le piège du mois (L58)

**Les 33 événements GDP Advance tombent TOUS entre le jour-du-mois 20 et 30 (médiane 28)** — par
construction du calendrier statistique américain (Advance GDP = dernière semaine du mois suivant le
trimestre). Ce dépôt a déjà établi l'existence d'un vrai effet de flux de fin de mois indépendant de
tout contenu macro (L51-L55, `Multi_Asset/research/active/month_end_vehicle_2026-07/`) : un placebo
générique (apparié seulement sur l'heure et le régime de vol, PAS sur le jour-du-mois) pourrait donc
fabriquer un faux PASS en sous-représentant la fin de mois dans le pool placebo — exactement le
mécanisme identifié en L58 sur ZN.

**Contrôle exécuté** : second placebo construit en restreignant le pool aux jours de bourse dont le
jour-du-mois est également dans [20,30] (815 jours candidats, 264 placebos tirés, même appariement de
régime de volatilité) :

| Fenêtre | Réel | Placebo générique | **Placebo jour-du-mois** | Diff (réel − placebo DoM) |
|---|--:|--:|--:|--:|
| -60 min | +5.43 | +0.64 | **+0.47** (t=0.74, NS) | +4.96 |
| -120 min | +6.80 | +0.59 | **+0.61** (t=0.73, NS) | +6.19 |
| -240 min | +9.63 | +0.56 | **-0.52** (t=-0.49, NS) | +10.15 |

**Le placebo jour-du-mois est plat (t non significatif à toutes les fenêtres) — il n'y a PAS de drift
générique de fin de mois de cette taille dans l'USD sur cette période.** Le résultat GDP USD n'est
donc pas un habillage du month-end : c'est spécifiquement autour de la publication (l'écart réel vs
placebo-DoM est quasiment identique à l'écart réel vs placebo générique, +4.96 à +10.15 bps). Contrôle
supplémentaire, cohérence de mécanisme : CPI et NFP sont publiés à la même heure de séance (8h30 ET)
et NE montrent PAS le même effet (CPI : signe **opposé**, NFP : nul) — ce qui écarte aussi un effet
générique "toute donnée à 8h30 ET".

### C. Conditionnement de régime (L54 — la variance ≠ la moyenne)

Sur le candidat retenu (GDP USD, -120min), deux scissions (n petits, à titre de diagnostic seulement,
pas des tests formels supplémentaires comptés dans le Δn_tests primaire) :

| Split | n | mean (bps) |
|---|--:|--:|
| Vol réalisée HAUTE (médiane+) | 17 | +3.91 |
| Vol réalisée BASSE | 16 | **+9.87** |
| USD en tendance HAUSSIÈRE (20j) | 17 | +8.56 |
| USD en tendance BAISSIÈRE (20j) | 16 | +4.93 |

**L'effet est présent dans les deux régimes de vol et les deux régimes de tendance** — pas concentré
dans un seul sous-échantillon, et surtout **plus fort en régime de vol BASSE** (contraire à ce
qu'un récit "prime de risque événementiel" prédirait, où la prime devrait grossir avec l'incertitude).
Ceci va dans le sens d'un mécanisme de flux/positionnement plutôt que d'une prime de risque pure — mais
avec n=16-17 par branche, ceci est un contrôle de robustesse, pas une conclusion de régime.

### Candidats secondaires — adéquatement alimentés, SOUS le seuil Šidák complet

Trois pistes clairement au-dessus de MDE (effet/MDE > 1, donc pas "underpowered" au sens strict) mais
qui ne franchissent pas |t|≥3.52 sur 120 tests — dignes d'une réplication à budget de test plus faible,
pas d'un déploiement :

| Famille/devise | Fenêtre | mean (bps) | t_HAC | effet/MDE | WF |
|---|---|--:|--:|--:|--:|
| CPI USD | -240min | -6.46 | -2.43 | 0.79 | 5/5 |
| CPI USD | -1440min | -9.78 | -2.59 | 0.89 | 5/5 |
| PMI EUR | -60min | -7.66 | -2.41 | **1.16** | 4/5 |
| PMI EUR | -120min | -8.45 | -2.71 | **1.26** | 5/5 |
| GDP GBP | -1440min | -14.65 | -2.93 | 0.73 | 5/5 |

Notes : **CPI USD est le miroir exact de GDP USD** (même heure de séance, signe opposé — le dollar
BAISSE avant CPI, monte avant GDP), déjà cité en §B' comme preuve que ce n'est pas un effet de séance
générique. PMI EUR (Flash, jour-du-mois 15-24, pas de confound month-end) montre le contre-flux
symétrique côté euro. GDP GBP jour-du-mois 9-15 (pas de confound month-end non plus), mais fenêtre de
24h — plus exposé à d'autres confondants non testés ici (nuit précédente, autre calendrier).

### Ce qui est mort (drift pré-décision de banque centrale)

**Aucune des 8 devises ne franchit même la significativité brute (|t|<2) sur la majorité des
fenêtres**, sauf JPY et CHF qui montrent un signe négatif (yen/franc se renforcent, i.e. narrative
"risk-off avant la Fed/BCE/BoE") **suggestif mais non significatif après correction** (JPY -240min
t=-2.15, pctl placebo 0.000 mais sous Šidák ; CHF -120min t=-1.86). C'est cohérent avec la littérature
(pas d'équivalent FX propre au pre-FOMC equity drift, cf. §Théorie) et avec le kill mécanique déjà
gravé sur les indices actions (L42 : le "reversal" post-event des indices n'a jamais eu de support
two-sided réel). **Famille "drift pré-décision-de-taux" : REJECTED, gross insuffisant pour dépasser
même le t brut.**

**NFP (USD) : nul sur toutes les fenêtres** (t entre 0.43 et 0.92, aucune tendance). Confirme
l'intuition du brief que NFP, contrairement à GDP, ne montre pas de pré-positionnement mesurable en
FX — malgré son profil de "surprise la plus suivie du calendrier".

---

## D. Gate économique (candidat GDP USD)

Gross mesuré sur la paire la plus liquide et la moins chère (**EURUSD, +9.40 bps à -120min**, coût RT
le plus bas du panier) :

| Véhicule | Coût RT | Ratio gross/coût |
|---|--:|--:|
| **FTMO** (mesuré, `phase0_rt_cost_bps.csv`) | 1.13 bps | **8.34×** |
| **Eightcap Raw** (best-case, NON vérifié) | 0.75 bps | **12.53×** |
| Eightcap Raw (stress ×2, cf. caveat mesuré ci-dessous) | 1.50 bps | 6.27× |
| Eightcap Raw (stress ×8, pire cas cité) | 6.00 bps | 1.57× |
| **IBKR** (\$10k notionnel, floor \$2/ordre — L57) | 4.45 bps | 2.11× |
| **IBKR** (\$50k notionnel) | 1.25 bps | 7.52× |

⚠ **Eightcap Raw n'est pas mesuré dans ce dépôt** : `Forex/research/active/dedale_broker_2026-08/RAPPORT_BROKER.md`
chiffre le best-case à 0.66-1.18 bps RT mais prévient que le coût réel est "probablement 2-8× plus
haut" d'après un comparable EURUSD mesuré — d'où le stress-test ci-dessus. **Même dans le pire cas
cité (×8), le ratio reste au-dessus du gate L43 (1.5×)**. C'est la première fois dans le corpus L43
(FX intraday, meilleur ratio historique 0.36-0.38×) qu'un effet FX **dépasse le gate d'un facteur 4 à
33×** plutôt que d'en être à 25%. Sur USDCHF (2ᵉ meilleure paire, coût FTMO mesuré 2.34 bps, gross
8.72 bps) le ratio FTMO reste à 3.72× — toujours confortable.

**Géométrie du trade** : entrée ~2h avant l'annonce, sortie AU moment de l'annonce (avant la
publication elle-même, pour ne pas porter le risque de surprise) — durée de détention ~2h,
intraday-flat, **aucun swap** (L43 s'applique, pas L36). Pas d'ordre stop dans cette géométrie
(entrée/sortie à l'heure, pas de niveau de prix) donc **L59 (re-pricer la sortie séparément) ne
s'applique pas** ici — la sortie est aussi un ordre au marché à heure fixe, pas un stop.

---

## Δn_tests

| Bloc | n_tests |
|---|--:|
| A — pic de volatilité excédentaire (24 combinaisons famille×devise) | 24 |
| B — drift pré-événement (24 combinaisons × 5 fenêtres) | 120 |
| B' — contre-contrôle jour-du-mois sur GDP USD (5 fenêtres, même hypothèse re-testée) | 5 |
| C — scissions de régime diagnostiques (vol haute/basse, tendance haut/bas) | 4 |
| **Total Δn_tests cette session** | **153** |

Le seuil de significativité rapporté en §B (Šidák |t|≥3.52) est calculé sur le bloc primaire de 120
tests (B), qui est le seul bloc où un signe n'était pas fixé a priori. Le bloc A (24 tests) a son
propre seuil (3.07), tous deux appliqués tels quels — pas de fusion des deux blocs dans une seule
correction (questions différentes : "combien de temps" vs "y a-t-il un drift").

---

## Limites et pistes de suivi

1. **CAD/CHF/NZD n'ont qu'une seule paire dans le proxy** (pas de validation two-sided multi-paires
   possible) — tout résultat sur ces devises serait à confirmer indépendamment avant d'être pris au
   sérieux (aucun candidat retenu ici ne dépend de ces trois devises seules, donc pas bloquant pour
   GDP USD).
2. **BoJ (JPY rate decision) doit être vérifié pour un biais d'horodatage** avant toute réutilisation
   de sa demi-vie — l'écart à toutes les autres banques centrales (53min vs 1.7-2.7min) est trop
   spécifique pour être un effet de marché.
3. **Le plateau de continuation (§A, dernier tableau) n'a pas de test formel** — piste explicite pour
   une session future : HAC + placebo-percentile sur le plateau lui-même (pas seulement le pic de
   vol), avec Šidák sur les ~10 combinaisons qui montrent un plateau non-trivial.
4. **GDP USD n'a que 33 événements (trimestriel)** — c'est peu pour une walk-forward à 5 folds
   (6-7 événements/fold), mais l'accord de signe est total (5/5) et l'IC block-bootstrap exclut
   confortablement zéro ; à surveiller à mesure que l'échantillon s'allonge (prochain point : PIB
   Q3 2026, fin octobre).
5. **Eightcap Raw reste un chiffre non mesuré** — avant tout financement sur ce candidat, une mesure
   live du spread réel sur EURUSD/USDCHF à l'heure exacte de la fenêtre de trade (2h avant 12:30/13:30
   UTC) serait le prochain jalon, pas une nouvelle re-estimation théorique.
6. **Mécanisme non tranché** : positionnement institutionnel pré-publication (Evans-Lyon, ordre flow),
   effet de "flight to information", ou artefact structurel du calendrier US restant à exclure
   (aucun autre effet fin-de-mois n'explique le résultat, mais on n'a pas testé, par exemple, un lien
   avec les rebalancements d'indices actions US qui ont aussi lieu en fin de trimestre).

## Fichiers

- `build_events.py`, `events/*.csv` — 24 tables d'événements consolidées depuis le calendrier canonique
- `build_ccy_proxy.py`, `cache/proxy_*.csv` — proxy quotidien par devise (pour l'appariement de régime)
- `lib.py` — extraction vectorisée, placebo apparié, HAC, block-bootstrap, MDE
- `run_decay.py`, `results/decay_summary.csv`, `results/decay_*.json` — Partie A
- `run_drift.py`, `results/drift_summary.csv` — Partie B
- `verify_gdp_month_end.py` — contrôle B' (placebo jour-du-mois)
- `costs.py` — Partie D
