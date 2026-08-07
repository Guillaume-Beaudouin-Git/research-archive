# PRÉ-ENREGISTREMENT — XAUUSD autour de la publication CPI US, échantillon étendu 2007-2026

**Écrit et committé AVANT tout calcul de rendement sur l'échantillon étendu.**
Date : 2026-08-07. Branche `claude/gold-cpi-eve`, worktree dédié.
Interpréteur : `/usr/bin/python3` (explicite). Lecture seule sur tout chemin du répertoire principal.

---

## 0. Objet et nature du geste

`exogenous_predictors_2026-08/RESULTS.md` §6.1 a laissé **une seule hypothèse instruite** de toute
son étude : XAUUSD, entrée à la clôture de la veille de la publication du CPI US.
Mesurée sur **N = 65** (2021-2026) : +38.07 bps, t_HAC 3.86, placebo jour-du-mois p 0.0012,
Šidák-76 p 0.0086, gross/coût 20.7, 6 années sur 6 positives.
Elle est **INADMISSIBLE** : 65 trades ⇒ walk-forward 5 folds impossible, aucun hors-échantillon,
DSR 0.637.

Le blocage est de **NATURE PUISSANCE** au sens de la politique de ré-ouverture (CLAUDE.md), donc
rouvrable. **L'angle explicitement nouveau, écrit avant de toucher la donnée, est : l'échantillon.**
Le fichier d'entrée `data/panels/economic_calendar.csv` commence en 2020 ; le calendrier réel des
publications CPI du BLS remonte à 2003. C'est le motif exact du pre-FOMC (49 événements utilisés
sur 102 disponibles). **Rien d'autre n'est rouvert.**

**La spec est GELÉE. Le SEUL changement autorisé est l'échantillon.**

---

## 1. LA SPEC GELÉE, recopiée depuis `exogenous_predictors_2026-08/code/cpi_candidate.py`

| élément | valeur gelée | ligne source |
|---|---|---|
| instrument | `XAUUSD` | `cpi_candidate.py:40` |
| série de prix | `data/ftmo_portfolio/cache/panel_px.parquet` (clôture quotidienne) | `exog_lib.load_daily_panel` |
| rendement | `r_t = 1e4 × (log P_{t+1} − log P_t)` = `np.log(p).diff().shift(-1)` | `cpi_candidate.py:41` |
| jeu d'entrées | `{date_CPI − 1 jour CALENDAIRE}` ∩ index de prix | `cpi_candidate.py:45` |
| sens | **LONG uniquement**, poids égal par événement, aucun sizing | implicite (`y = rr[sel]`) |
| coût RT | **1.84 bps** (XAUUSD mesuré, `COST_AUDIT.md`) | `exog_lib.COST_RT_BPS` |
| swap | **−1.518 bps**, jambe LONG, **UNE nuit** | `exog_lib.SWAP_BPS` |
| net | `gross + (−1.518) − 1.84` | `cpi_candidate.py:88` |
| inférence | HAC Newey-West **lag 6** | `exog_lib.hac_t` |
| baseline L58 | moyenne inconditionnelle du **même** rendement forward-1j sur l'ère | `cpi_candidate.py:58` |
| placebo | bande jour-du-mois `[dom_min, dom_max]` des entrées, **hors** entrées, 5000 tirages appariés sans remise, `p = P(tirage ≥ observé)`, `rng seed 3` | `cpi_candidate.py:66-77` |
| bootstrap | blocs circulaires, **block=3**, 5000, bilatéral, sur `y − m_all`, seed 7 | `exog_lib.block_bootstrap_p` |
| DSR | `dsr.deflated_sharpe_ratio(net, n_trials, periods_per_year=freq, rf=0.0, std_sr_trials=0.5)` | `cpi_candidate.py:93` |
| MDE | `2.5 × σ(rendement inconditionnel de l'ère) / √N` | `cpi_candidate.py:60` |

**Aucun de ces réglages ne sera touché.** Toute divergence sera signalée explicitement comme telle.

---

## 2. OÙ EXACTEMENT LE TRADE COUPE — et une correction d'interprétation, mesurée avant le test

⚠ **La spec gelée n'est PAS une dérive pré-annonce. C'est le rendement du JOUR de publication,
pris à la clôture de la veille.** Mesuré (diagnostic de convention, aucun rendement conditionnel
calculé) :

- `XAUUSD_M1.csv` (`data/deep_history_utc/`, vrai UTC) : la dernière minute cotée de chaque
  journée est **20:59 / 21:59 UTC** (halt de règlement, L52/L56).
- La clôture quotidienne de `panel_px.parquet` datée `d` **coïncide au tick avec la dernière minute
  M1 de la journée `d`** : concordance exacte **80.9 %** (`|Δ| < 0.01`), contre **0.2 %** avec la
  dernière minute de `d−1`. La barre quotidienne `d` court donc de ~22:00 UTC `d−1` à ~21:00 UTC `d`.
- La publication CPI est à **08:30 ET** (confirmé sur les documents BLS : *« embargoed until
  8:30 a.m. (EDT/EST) »*), soit 12:30/13:30 UTC — **à l'intérieur** de la barre quotidienne datée
  du jour CPI.

⇒ **Le trade gelé entre à la clôture de la veille (~21:00 UTC) et sort à la clôture du jour CPI
(~21:00 UTC), en TRAVERSANT la publication.** Une nuit tenue, un seul rollover broker (22:00 UTC),
donc **un seul swap** — la facture gelée est correcte.

**Look-ahead : aucun.** Les dates CPI sont publiées par le BLS un an à l'avance (les calendriers
annuels `bls<YYYY>sched.pdf` le prouvent, cf. §3) ; entrer à la clôture de la veille n'utilise que
de l'information publique ex ante. La barre de publication est **délibérément incluse** — c'est la
spec gelée, pas un choix de cette session. Le nom « veille de CPI » désigne la **date d'entrée**,
pas la fenêtre de P&L.

**Conséquence pré-enregistrée sur la lecture du mécanisme** : « l'or est l'actif d'inflation et
dérive avant la publication » n'est **pas** l'hypothèse que ce test mesure. L'hypothèse mesurée est
« le rendement du jour CPI, capté depuis la veille, est positif en moyenne ». La décomposition
pré/post-publication est déclarée en §6 comme **diagnostic secondaire, non décisionnel**.

---

## 3. LES DATES — récupérées AVANT ce document, sources et concordance

**Source A (primaire, authentique)** : les **communiqués archivés du BLS** eux-mêmes,
`https://www.bls.gov/bls/news-release/cpi.htm` → `news.release/archives/cpi_MMDDYYYY.htm`.
La date est encodée dans le nom du document publié. **234 communiqués, 2007-01-18 → 2026-07-14**,
12 par an sans exception (sauf 2025 : 11, cf. infra).

**Source B (contrôle de champ)** : l'en-tête d'embargo **dans le corps** de chacun des 234
documents (*« Transmission of material in this release is embargoed until 8:30 a.m. (EDT)
<date> »*). **234 / 234 = 100.00 %** confirment la date du nom de fichier. Zéro divergence.

**Source C (indépendante, ex ante)** : les calendriers annuels BLS publiés d'avance
(`bls2007sched.pdf`, `bls2008sched.pdf` — seules années encore servies sous ce nom).
**24 / 24 = 100 %** de concordance exacte avec la source A sur 2007-2008.

**Source D (tierce, indépendante du BLS)** : le calendrier économique scrapé
`data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv` (USD, event == `CPI`),
disponible 2021-2026. **64 / 64 = 100 %** de concordance exacte.

**Source E (le fichier utilisé hier)** : `data/panels/economic_calendar.csv`, event == `CPI`.
**70 / 77 = 90.9 %** seulement. **Les 7 divergences sont TOUTES postérieures à 2025-09** :

| E (fichier d'hier) | A (BLS réel) | ce qui s'est passé |
|---|---|---|
| 2025-09-10 | 2025-09-11 | — |
| 2025-10-14 | **2025-10-24** | shutdown 2025, publication repoussée |
| 2025-11-12 | **aucune** | shutdown 2025, publication d'octobre **annulée** |
| 2025-12-10 | 2025-12-18 | rattrapage |
| 2026-01-14 | 2026-01-13 | — |
| 2026-02-11 | 2026-02-13 | — |
| 2026-04-09 | 2026-04-10 | — |

⇒ **Le fichier d'hier est authentique jusqu'en 2025-08 et synthétique après.** Environ 6 des 65
événements de la mesure d'hier portent une date fausse. La ré-estimation de l'ère de découverte
avec les vraies dates est donc **aussi** un contrôle de réplication, déclaré ici.

**Les dates CPI ne suivent aucune règle simple** — vérifié : jour du mois de **10 à 30**, quatre
jours de semaine (Mer 82, Jeu 53, Mar 50, Ven 49, **aucun lundi**), décalage fin-de-mois-de-référence
→ publication de **10 à 30 jours** (médiane 15). Les valeurs extrêmes sont des événements réels
(2013-10-30 shutdown, 2015-02-26 / 03-24 / 05-22, 2025-10-24 shutdown). C'est le contraire du piège
NFP d'hier (77/77 = premier vendredi ⇒ règle générée).

Contrôle structurel supplémentaire : le mois de référence extrait du corps des communiqués
(147/234 parsables sur les formats récents) donne **0 doublon** et une séquence mensuelle
consécutive.

---

## 4. ÉCHANTILLON, ÈRES, ET CE QUI COMPTE COMME HORS-ÉCHANTILLON

- **Échantillon étendu** : toutes les dates de la source A dont la veille est dans l'index de prix
  XAUUSD (`panel_px`, 2007-01-01 → 2026-06-05). N attendu ≈ **225-232**.
- **ÈRE OOS PURE = 2007-01-01 → 2020-12-31** (≈ 168 événements). Cette ère n'a **jamais** été vue :
  le fichier calendrier d'hier commence en 2020-01 et l'ère mesurée commençait en 2021-01.
- **ÈRE DE DÉCOUVERTE = 2021-01-01 → 2026-06-05** (≈ 64 événements).
- **PLEIN ÉCHANTILLON** = les deux.
Les trois sont rapportées **séparément puis groupées**, dans cet ordre.

Hygiène déclarée d'avance, rapportée quoi qu'il arrive :
- nombre d'événements perdus parce que la veille calendaire n'est pas un jour coté ;
- nombre d'événements où la barre suivante n'est **pas** le jour CPI (jour férié) — le trade y
  couvre alors plus que la journée de publication ;
- **L60** : part de barres à fourchette nulle sur XAUUSD, **par an**, daily et M1.

---

## 5. RÈGLES DE DÉCISION CHIFFRÉES (kill rules)

`n_trials` déclaré pour la déflation : **80** (les 76 cellules calendrier balayées hier + les
4 tests confirmatoires de ce dossier). Aucune autre cellule ne sera balayée.

### CONFIRMÉ — les SEPT conditions doivent tenir simultanément
1. **Walk-forward ≥ 5 folds chronologiques, ≥ 4/5 folds à moyenne NETTE positive** (≥ 60 %, seuil
   PROPFIRM_PASS). C'est le point n°1 du dossier.
2. **Ère OOS pure 2007-2019 : gross > 0 ET t_HAC ≥ 2.0** sur sa propre ère.
3. **Plein échantillon : t_HAC ≥ 2.5.**
4. **Placebo jour-du-mois apparié : p ≤ 0.05**, ET **contrôle L58 du pool valide** : le biais du
   pool contre l'espérance inconditionnelle doit rester `|biais| ≤ (1/3) × excès mesuré`. Si le
   pool est biaisé au-delà, **le placebo est déclaré invalide et le test est VOID**, pas PASS.
5. **Bootstrap par blocs : p ≤ 0.05.** (Les deux contrôles sont exigés — ils ne testent pas la
   même chose.)
6. **DSR ≥ 0.95** avec `n_trials = 80`, `rf = 0.0`.
7. **gross / coût ≥ 3** (L11b), coût = RT 1.84 + |swap| 1.518 = 3.358 bps, queue provisionnée
   3.88 + 1.518 = 5.398 bps rapportée à côté.

### REJETÉ — une seule suffit
- **R1.** Ère OOS pure 2007-2019 : gross **≤ 0** ⇒ l'effet n'existe pas hors de l'ère de découverte.
- **R2.** Walk-forward : **≤ 2/5** folds positifs.
- **R3.** Placebo jour-du-mois : **p > 0.10**.
- **R4.** Plein échantillon : **t_HAC < 2.0**.
- **R5.** `gross / coût < 3`.
- **R6.** Le contrôle de voisinage (§6.2) montre un effet **de même ampleur** sur FOMC / PPI / NFP :
  l'hypothèse devient « prime générique de veille d'événement », famille déjà NO-GO
  (`announcement_premium_2026-06`, L42, L49). Critère chiffré : si **≥ 2** des 3 événements voisins
  rendent un gross ≥ **50 %** du gross CPI avec t_HAC ≥ 2.0 sur le même échantillon étendu.

### RÉGIME (ni PASS ni REJET) — étiquette explicite
Si l'OOS 2007-2019 est positif mais `t < 2.0`, et que le plein échantillon passe (3)-(7) :
verdict **RÉGIME-CONDITIONNEL, NON CONFIRMÉ**. L'hypothèse de régime est nommée d'avance et
**testable** : *l'inflation est redevenue un risque macro de premier plan à partir de 2021 ; avant
cela le CPI n'était pas un événement pour l'or.* Test pré-enregistré : régression du rendement de
l'événement sur le **niveau du CPI y/y publié** et sur la **volatilité implicite** ; si la pente est
nulle, l'hypothèse de régime est **rejetée** et le verdict retombe sur BRUIT.
Un ΔSR positif dans le bruit est **UNDERPOWERED, pas PASS** (inference layer 2026-07).

### Ce qui ne sera PAS fait
- Aucune ré-optimisation de fenêtre, d'heure, de sens, de sizing, de filtre.
- Aucun sous-échantillon choisi après coup.
- Aucun changement de la définition d'entrée (veille calendaire, pas veille ouvrée).
- Aucun ajout de condition sur la surprise CPI (non disponible ex ante à l'entrée de toute façon).

---

## 6. DIAGNOSTICS SECONDAIRES — rapportés, JAMAIS décisionnels

**6.1 Décomposition pré/post-publication** (M1 vrai UTC, `data/deep_history_utc/XAUUSD_M1.csv`) :
clôture veille → 12:30/13:30 UTC (dernière minute AVANT l'embargo, horloge d'échange ET avec DST,
L56) puis publication → clôture du jour CPI. **But : dire si le P&L gelé est de la dérive ou de la
réaction.** Ce n'est pas un candidat concurrent ; aucune des deux jambes ne peut être promue à la
place de la spec gelée dans ce dossier.

**6.2 Contrôle de voisinage, échantillon étendu** — même spec gelée, autres calendriers :
- **FOMC** : `data/panels/fomc_events.csv` (182 événements 2004-2026).
- **PPI** : archives BLS `news.release/archives/ppi_MMDDYYYY`, même méthode et même contrôle de
  concordance que §3.
- **NFP (Employment Situation)** : archives BLS `news.release/archives/empsit_MMDDYYYY` —
  **jamais** le champ `NFP` de `economic_calendar.csv`, prouvé généré par règle hier.
Un effet **spécifique au CPI** soutient le mécanisme « or = actif d'inflation ». Un effet générique
le contredit et déclenche **R6**.

**6.3 L59** — la spec gelée est une entrée et une sortie **à la clôture**, sans stop ni bracket :
il n'y a pas de géométrie de sortie à re-pricer. Déclaré ici pour que l'absence de test L59 soit un
fait, pas un oubli.

**6.4 Si et seulement si le gross tient** : p(pass), durée médiane et **EV par unité de temps** sur
le livre FTMO (daily −5 % sur l'équité, plancher **STATIQUE** −10 %, horizon 182 j) via
`Portfolio/admission/barrier.py`, **importé sans modification**. Tout p(pass) est accompagné d'un
**placebo à autocorrélation appariée**. La **fréquence (≈ 12 événements/an)** est rapportée à côté
du gross **partout** : une sleeve à 12 trades/an ne remplace pas un moteur, et le jugement se fait
sur le **Sharpe solo et le Δp**, pas sur la décorrélation.

---

## 7. Ce qui est engagé

Le résultat sera écrit tel qu'il sort. Le signe attendu est connu — c'est précisément la raison de
ce document. **Les deux issues sont bonnes** : si l'effet tient sur ~230 événements avec un WF
≥ 5 folds, c'est le premier candidat instruit du programme et il sera pré-enregistré en N2 ; s'il
s'effondre, la classe événementielle se ferme et on cesse d'y revenir.

Aucun blob de données ne sera committé. Les caches de session vivent hors dépôt.
