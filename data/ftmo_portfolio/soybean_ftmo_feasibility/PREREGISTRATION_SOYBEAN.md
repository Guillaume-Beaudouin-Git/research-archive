# PRÉ-REGISTRATION — SOYBEAN reopen-drift comme sleeve candidate FTMO

**Horodatage (committé AVANT tout résultat) :** 2026-06-19
**Auteur :** session de recherche Claude Code (author≠auditor — toute validation se fera en session fraîche)
**Branche :** `claude/soybean-ftmo-feasibility`
**Cadre :** RECHERCHE PURE, sandboxée. AUCUN déploiement. AUCUN toucher au book live
(`ftmo_live/`, EA gelé, FLAT, targets, compte vm14 armé lundi). Lecture seule sur tout artefact live.
Go/no-go de recherche. Jumeau méthodologique de `asia_23_8_feasibility/` (gold overnight-drift).

**Règle d'or :** questions, métriques et seuils ci-dessous **FIGÉS**. Aucun ajustement post-résultat.
Toute modification post-résultat invalide l'étude (relance en session fraîche, nouveau pré-enregistrement).

---

## 0. Objet et artefacts de départ

- **Stratégie :** **long SOYBEAN sur la fenêtre 01:00→07:00 UTC** (heures H1 [1,2,3,4,5,6], label-left =
  entrée ~01:00 UTC à la réouverture électronique post-halt, sortie ~07:00 UTC), vol-targetée (VT interne
  causale = médiane-expanding(vol 20j) / vol 20j, cap 3×), un aller-retour/jour, **flat overnight**.
- **Code source (à reproduire, NON réimplémenté) :** `yt_strategy_replications/soybean_research/`
  (`net_analysis.py`, `full_analysis.py`, `validate_audit.py`, `candidates.py`) + moteur
  `gold_research/intraday.py` (`hourly_pivot`, `win_ret`, `backtest`) + `engine/stats.py`.
- **Rapport de due-diligence (la cible Q1) :** `yt_strategy_replications/reports/soybean_ftmo_due_diligence.md`.
- **Données :** `data/deep_history_utc/SOYBEAN_M1.csv` (true-UTC) → H1 via `engine/data.py`
  (cache `data_cache/gold/SOYBEAN_1h.parquet`, 2017-12-01 → 2026-06-05, vérifié présent).

### Trois réservations sévères du rapport (à CONFRONTER, pas supposer) — pré-inscrites
1. **OOS faible** : Sharpe @2bp full 1.08 mais OOS (40% récent, 2022-25) **0.49** — l'edge a refroidi.
   Le futur ressemble plus à 0.49 qu'à 1.08.
2. **Skew négatif** : daily skew **−1.9**, kurtosis 27, **pire jour −6.9%** (tail à la BAISSE — inverse
   du gold +0.35). Risque USDA/WASDE/météo sur la jambe longue.
3. **Sort d'un drawdown de ~4 ans** (2022→2026, maxDD −19.7% @2bp).

### Pré-condition non négociée : SWAP-FREE (à VÉRIFIER avant Q2)
La fenêtre 01:00→07:00 UTC ne traverse **pas** le rollover broker (00:00 serveur = 21:00 UTC été /
22:00 UTC hiver) : le rollover précédent (21/22:00 UTC veille) est avant 01:00 UTC, le suivant
(21/22:00 UTC jour J) est après 07:00 UTC. ⇒ **0 nuit facturée**, été comme hiver. Le swap long
SOYBEAN.c (−38.76 pt ≈ −3.4 bp/nuit, rapport §4) est donc inopérant. **Coût = spread seul + commission 0.**
Je vérifie ce raisonnement read-only (`ftmo_live/lib/market_hours.py`) AVANT Q2 ; s'il échoue,
toute l'étude tombe (comme le gold L30/L36/L45 : le swap pré-tue les primes tenues). Sortie attendue : CONFIRMÉ.

### Engines RÉUTILISÉS (read-only, pas de réimplémentation)
1. **PRIMAIRE — moteur barre v2.2 audité** : `data/ftmo_portfolio/v22/engine_v22.py` + cleanroom
   `audit_v2_independent/cleanroom/engine.py` (pin baseline `605f4a4` ; challenge contractuel pooled
   **0.87**, gate d'acceptation [86,91]). SOYBEAN **injecté** via `code/soy_inject.py` (calque exact de
   `asia_inject.py`) : un seul bloc inséré à l'ouverture de chaque jour book (après la ligne daily-loss
   figée sur balance@00:00 serveur, AVANT le segment-0 09:00), = P&L réalisé soybean + contrôle de
   barrière sur le **plus-bas intraday**. Fidélité : la fenêtre 01:00→07:00 UTC clôture à ~09:00 serveur =
   juste avant le 1er segment du book → injection causale non-invasive. **Différence vs ASIA :** la
   fenêtre est intra-jour-UTC (≠ ASIA qui traverse minuit) ⇒ alignement **même-jour** (aday D → book D),
   PAS le décalage +1 d'ASIA. Validé empiriquement : ∩ book = **99.8%** en même-jour vs 79.6% en +1.
2. **CONTRE-VÉRIFICATION 1 — `code/soy_fp.py`** : copie de `asia_fp.py` (first-passage daily $-additif,
   plus-bas intraday inclus). Validé |Δ|≈0 contre le moteur barre (book off).
3. **CONTRE-VÉRIFICATION 2 — `firstpassage.py`** (`PropFirms/ftmo/program_2026-06/ftmo_portfolio_audit/
   code/firstpassage.py`) : close-to-close block-bootstrap = **borne optimiste** (sans plus-bas intraday).
- **Métriques** : `yt_strategy_replications/engine/stats.py` (`sharpe_ratio`, `sortino_ratio`,
  `max_drawdown`, `hac_tstat` lag-6, `deflated_sharpe_ratio`, `fold_metrics`).
- **Validation obligatoire du wrapper** (3 checks, AVANT tout chiffre Q2) :
  (i) `soy_series.net_log` == `intraday.backtest(...)['net']` (sémantique de label : fenêtre = 01:00→07:00) ;
  (ii) soybean OFF ⇒ moteur reproduit le pooled **87.0** (accept [86,91]) + identité cash → non-invasif ;
  (iii) `soy_fp` (book off, soy on) == moteur barre (book off, soy on) à |Δ| ≤ 0.5 pt sur K∈{1.5, 3.0}.

### Convention de triplet (imposée projet — identique au book canonique)
Tout chiffre prop-firm en **triplet (p, attempts_moyen, EV)** :
- `p` = p(funded) poolé sur cohortes (IS+OOS), + décomposition IS / OOS.
- `attempts_moyen` = nombre moyen de tentatives challenge avant funding (mur 91 j).
- `EV` = `p_funded × funded_value − E[frais]`. Frais **$96/tentative**, remboursés au 1er payout.
  `funded_value` = `0.8 × (retraits + résidu)` du stage funded (`run_funded`), `+ $96` (refund).

### Méthode de cohortes (identique au book canonique pour comparabilité)
- `cohort_starts` tous les **7 jours** sur `WINDOWS` = IS `2013-10-01→2019-12-31`,
  OOS `2020-01-02→2026-02-25` ; mur **91 j calendaires** ; funnel 2-step (P1 +10% → gap 3 j ouvrés →
  P2 +5%, vm×1.2 ; bust/abandon → retry après 2 j ouvrés ; dans le mur).
  *Note :* SOYBEAN ne commence qu'en 2017-12 → les cohortes IS 2013-2017 n'ont pas de signal soybean
  (traded=0, sleeve flat) ; reporté explicitement (réduit la puissance IS — pas un défaut, un fait de données).
- CI : block-bootstrap sur cohortes (≥200 resamples) pour les configs **headline** uniquement.

### Coût retenu (variable de décision) — le point CFD-vs-futures
FTMO ne supporte pas les futures CME (L22c) → sur FTMO, l'instrument est **SOYBEAN.c (CFD, spread
flottant)**, PAS le future ZS. La grille de coût :
- **PRIMAIRE = 2 bp RT** (le « base case » du rapport ; hypothèse OPTIMISTE pour un CFD ag).
- **CONSERVATEUR = 3 bp RT** (haut de la fourchette mandat CFD).
- **FUTURES = 1.5 bp RT** (ZS/MZS — borne optimiste ; **hors-FTMO**, pour le contraste véhicule).
Le verdict primaire se lit à **2 bp** ; je rapporte le triplet aux 3 coûts. La viabilité CFD exige
≤2 bp confirmé live (non mesurable hors paper-trade — cf. caveat exécution).

### Sizing soybean sur le compte (levier `soy_lev` = K)
- `K` = multiplicateur direct sur la série de rendement net natif soybean (VT interne incluse,
  ~9.6% vol annu @rapport). K=1 ⇒ ~9.6% vol annu compte. Vol annu compte ≈ K×9.6% (rapportée/config).
- **Grille K pré-enregistrée :** K ∈ {1.0, 1.5, 2.0, 2.5, 3.0, 4.0} (≈ vol compte {9.6, 14, 19, 24, 29, 38}%).
  Non étendue post-résultat. « Sizing prudent » (Q2) = borne basse de cette grille, PAS une modification.

### Variantes (budget « 3 modifications max » — explicitement consommé ; cap dur 4 variantes)
Anti-sur-recherche : le rapport est déjà à **DSR 0.75 / 20 trials @2bp**. Ajouter des essais érode la DSR.
Je plafonne à **4 variantes = 3 mods**, figées ici. Si aucune ne passe, je le rapporte — pas de 5e.
- **V0** baseline (VT native), balayage K. (la VT native n'est pas une mod : elle est dans le code source.)
- **V1 (mod 1) — stop intraday dur** : la position soybean est coupée si son plus-bas intraday touche
  **−2.5% du compte** ($250 sur $10k). Mécanique (dans `soy_inject`/`soy_fp`, après K-scaling) : si
  `a_low ≤ −0.025×INIT` ⇒ réalise `a_net = −0.025×INIT` (sortie au stop, perd la reprise éventuelle)
  et `a_low = −0.025×INIT`. Stop **réel** (ordre live), pas de look-ahead. Borne la perte journalière
  soybean à 2.5% ⇒ standalone ne perce jamais le daily −5% par la seule jambe soybean.
- **V2 (mod 2) — skip USDA** : flat (scale 0) les matins de rapport USDA programmé **ET** le lendemain
  (les deux matins encadrant un rapport de midi ET). Dates connues à l'avance (calendrier publié USDA) ⇒
  pas de look-ahead. Calendrier = `code/usda_calendar.py` : WASDE mensuels + Grain Stocks trimestriels +
  Prospective Plantings (mars) + Acreage (juin) + Crop Production, sourcés du calendrier USDA public,
  **validés** par range réalisé élevé sur les jours taggés (anti-erreur de date).
- **V3 (mod 3) — combo V1+V2** (stop + skip ; la mitigation complète recommandée par le rapport §6.2/§12).
Au-delà de V3 : budget épuisé. Un cap de VT < 3× (suggéré pour dompter les excursions) serait une **4e
mod** → exigerait un NOUVEAU pré-enregistrement (hors périmètre, comme la note Q5 du gold).

---

## Q1 — Reproduction (cible : le rapport au centième)
**Test :** exécuter les 4 scripts soybean sur le stack actuel. Vérifier la table net @{1,2,3} bp
(Sharpe **1.32/1.08/0.84**, Sortino 1.21/1.00/0.78, DSR(20) **0.89/0.75/0.56**, annret +12.6/+10.4/+8.1%,
vol 9.6%, maxDD **−15.8/−19.7/−23.5%**, Calmar 0.80/0.52/0.34, OOS **0.73/0.49/0.24**), skew **−1.9** /
pire jour **−6.9%** / kurt 27, table annuelle @2bp (2018 +0.9 … 2026 +4.4, **7/9 +**), gross VT ~1.56 /
no-VT **1.53** / short **−1.56**, MC @2bp (médiane 1.08 [5e 0.42], P(SR>1) 57%, P(SR>0.5) 93%, maxDD med
−13%), MC gross (médiane 1.58, P>1 90%), β soybean **0.24** / R² **0.27** / α HAC t **+4.6**, voisinage
de paramètres (plateau start 01:00) + robustesse temps d'exécution + drop top-20 → 0.88.

**Seuil PASS-repro (figé) :** comme je ré-exécute le code source (seeds MC fixés : net=4, full=3), la
repro doit être **exacte**. Tolérance : |ΔSharpe|≤0.03, |ΔmaxDD|≤1.5 pt, |Δskew|≤0.05, |ΔOOS|≤0.03,
|ΔDSR|≤0.03, table annuelle signes identiques. Sinon **DIVERGENCE** documentée (cause : vintage de
données, fenêtre, arrondi). Arbitrage de probité : si rapport et code divergent, le **code exécuté**
est la source de vérité (le rapport peut être périmé) — je le signale.

## Q2 — Survie aux gates FTMO 2-step (LE point critique)
**Test :** moteur barre v2.2 + injection soybean (plus-bas intraday), book OFF, balayage K × {V0,V1,V2,V3}.
Règles : daily −5% (M5, vs balance@00:00), max −10% **statique** (floor 9000), cibles +10%/+5%, min 4 j/
phase, mur 91 j, funnel 2-step. Triplet (p_funded, attempts, EV) par config + p_bust/tentative + **distribution
du plus-bas intraday** (le point dur : skew −1.9 ⇒ le tail négatif percute le daily −5% plus fort que le gold).
Contre-vérif `soy_fp` + `firstpassage.py`. Coûts {1.5, 2, 3} bp ; décision à 2 bp.

**Seuils (figés) — identiques au gold pour comparabilité :**
- **VIABLE-standalone** : ∃ config pré-enregistrée avec p_funded(poolé) **≥ 0.50** ET p_bust(poolé/
  tentative) **≤ 0.35** ET p_funded(OOS) **≥ 0.40** ET (IS et OOS tous deux ≥ 0.30, pas d'effondrement IS≫OOS).
- **CONDITIONNEL-standalone** : best p_funded(poolé) ∈ **[0.30, 0.50)** avec bust contrôlé, OU ne franchit
  0.50 qu'en IS (OOS < 0.40).
- **NON-VIABLE-standalone** : aucune config n'atteint p_funded(poolé) **≥ 0.30**, OU bust non contrôlé
  (p_bust > 0.50) à tout sizing atteignant la cible.

## Q3 — Le tail USDA (spécifique soybean, absent du gold)
**Tests :**
(a) Construire le calendrier USDA (`usda_calendar.py`), VALIDER par range réalisé élevé sur jours taggés.
(b) **Décomposition du tail** : tagger chaque jour {report_day D, day_after D+1, autre}. Mesurer pour
   chaque bucket : pire jour, p1/p5 du rendement daily, skew, kurtosis, #jours < −3%, contribution au maxDD.
   **Attribuer le pire jour −6.9%** (et les N pires jours) à un bucket.
(c) **Edge AVEC vs SANS skip** (skip = flat report_day ∪ day_after) : Sharpe full/OOS, mean bp, maxDD,
   #trades retirés, skew, pire jour. Le skip améliore-t-il assez le tail pour survivre au daily −5% ?

**Seuils (figés) :**
- **USDA-MATÉRIEL** : skipper report±1 améliore le pire jour de **≥ 1.5 pt absolu** OU le pire jour
  appartient à un bucket USDA. (sinon le tail vient d'ailleurs — météo/macro non-programmable → non-mitigeable
  par skip de dates connues.)
- **SKIP-SAUVE-LE-DAILY** : post-skip, le pire jour K-scalé (au K du meilleur p_funded Q2) reste **dans
  −5%** ET le Sharpe post-skip ≥ 0.9 × Sharpe pré-skip (le skip ne tue pas l'edge).

## Q4 — Format funded (si le challenge échoue, comme attendu)
**Test :** `run_funded` (pas de cible, pas de mur ; horizon 504 j ouvrés), book OFF, soybean ON, config
**V3 (stop+skip)**. Barrières daily −5% + max −10% statique TOUJOURS actives. Mesurer p(survie 126 j ≈ 6 mois /
252 j ≈ 12 mois), rendement net annualisé, maxDD, retraits espérés. Comparer **V0 (sans mitigation) vs V3**
pour isoler si stop+skip mange l'edge. Balayage K. Coût 2 bp (+ 1.5/3 bp en sensibilité).

**Seuils (figés) :**
- **FUNDED-VIABLE** : ∃ K avec p(survie 12 mois) **≥ 0.60** ET retraits espérés **> 0** ET Sharpe(V3) > 0
  (le stop+skip ne flippe pas l'edge négatif).
- **FUNDED-NON-VIABLE** sinon (busté avant 12 mois > 40% du temps, OU EV retraits ≤ 0).

## Q5 — Apport au book RÉEL vs gold (l'argument central du rapport)
Le rapport vend soybean comme **complément de régime au gold** (soybean fort 2018-21 = gold ASIA mort).
MAIS le book vm14 n'a PAS de sleeve gold-ASIA : il a **or-trend** (gold TSMOM momentum, ≠ ASIA), **J1**
(USDJPY 12-1 long-only), **nightly** (GER40 overnight Mon/Mar) + micro-ORB US100. Question décisive :
la complémentarité vaut-elle pour le book RÉEL, ou seulement vs une sleeve gold-ASIA hypothétique ?
**Tests :**
(a) **Corrélation** des rendements daily net sleeve-level :
   - ρ(soybean, **or-trend** reconstruite `cleanroom.build_signals` WT["XAUUSD"]) ;
   - ρ(soybean, **J1** = WT["USDJPY"]) ;
   - ρ(soybean, **book trend combiné** = or-trend + J1, reconstruit analytiquement) ;
   - ρ(soybean, **gold-ASIA hypothétique** = `asia_series.build()`) — la complémentarité ANNONCÉE existe-t-elle ?
   Pearson + Spearman, full + IS/OOS + régime 2018-21 vs 2022-25. (nightly/micro = intraday/Mon-Mar/petit →
   couverts par l'ablation moteur, pas par la reconstruction analytique ; noté.)
(b) **Ablation** book vs book+soybean (moteur barre audité, mêmes cohortes), challenge **ET** funded :
   Δp_funded, Δattempts, ΔEV, funded_value. Sanity : book seul (soy off) reproduit 0.87 + funded_value ≈ spec.
(c) **Marge cumulée** : soybean (instrument distinct du book) empreinte sa propre marge. Taux retenu :
   CFD ag **1:10 (10%)** [hypothèse FTMO SOYBEAN.c, à confirmer] / futures ZS ~5%. Calculer marge soybean
   (K × pos × taux) + marge métal du book (or-trend XAU, swing 1:9) sous le **cap 60%** : p50/p99/max et
   fraction de jours où (book + soybean) > cap.

**Seuils (figés) :**
- **DIVERSIFIANTE** : ρ(soybean, book trend combiné) Pearson full **< 0.50** ET book+soybean p_funded
  **≥ book − 0.02** ET marge pire-cas combinée **≤ 60%**.
- **CONCENTRATION** : ρ **≥ 0.50** OU marge combinée **> 60%** OU book+soybean p_funded **< book − 0.05**.
- Question annexe tranchée explicitement : la complémentarité du rapport est-elle vs gold-ASIA (ρ négatif
  attendu) et NON vs le book réel ? → si ρ(soy, book réel) ≈ ρ(soy, gold-ASIA), l'argument transfère ;
  sinon il est trompeur (vendu sur une sleeve que le book n'a pas).

## Q-Verdict — règle de décision (figée)
Comparée explicitement à ASIA_23_8 (« a notch below gold » selon le rapport — à confirmer/réfuter).
- **(a) VIABLE-challenge** : Q2=VIABLE **ET** Q5=DIVERSIFIANTE **ET** swap-free confirmé.
- **(b) VIABLE-funded-only** : Q2≠VIABLE **MAIS** Q4=FUNDED-VIABLE **ET** Q5≠CONCENTRATION
  (sleeve de revenu funded, pas de challenge — nécessite un compte déjà funded ou un véhicule sans mur).
- **(c) CONDITIONNEL** : Q2∈{CONDITIONNEL} OU Q4 borderline — viable seulement après paper-trade confirmant
  (spread live ≤ 2 bp ; fill 01:00 UTC en réouverture ; swap-free réel relevé ; drift glissant 12 m ≥ 0).
- **(d) NON-VIABLE pour FTMO** : Q2=NON-VIABLE **ET** Q4=FUNDED-NON-VIABLE (les deux formats échouent),
  OU Q5=CONCENTRATION disqualifiante.

Livrable : `STUDY_SOYBEAN_FTMO_2026-06-19.md` (Q1–Q5 + verdict + triplets + tables + comparaison ASIA +
reco futures-vs-CFD + checklist paper-trade si CONDITIONNEL). Puis audit indépendant (session author≠auditor).

---

### Lessons applicables (rappel, non négociées ici)
- **L30/L36/L45** : le swap overnight pré-tue toute prime tenue → la viabilité soybean REPOSE sur le
  swap-free (pré-condition vérifiée avant Q2).
- **L20/L21** : DSR obligatoire (n_mod≥2) ; SR live single-instrument day-trade ∈ [0.8, 2.0] (catégorie) —
  soybean net @2bp 1.08 ∈ catégorie ; mais OOS 0.49 = signal de décroissance à pondérer.
- **L24** : p(pass) prop-firm pilotée par la FORME de la distribution daily vs barrière symétrique, PAS la
  taille de compte. Stratégie lumpy + skew négatif = pire cas contre un daily −5% (le tail percute le bas).
- **L33/L46** : la structure de COÛT réelle (spread CFD ag flottant), pas le signal, décide. Mesure
  obligatoire avant achat (ici : non mesurable hors paper-trade → caveat).
- **L39** : reporter skew daily ET mensuel (la barrière FTMO 5% est daily ; skew daily −1.9 binde).
- **L11/L25** : édge long-only (β soybean 0.24, R² 0.27) → vérifier que ce n'est pas du β-commodité déguisé.
- Règle « 3 modifications max » : V1/V2/V3 = budget complet, pas davantage.
