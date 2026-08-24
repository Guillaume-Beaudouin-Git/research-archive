# AUDIT INDÉPENDANT — SOYBEAN reopen-drift (01:00→07:00 UTC) comme sleeve FTMO

**Date :** 2026-06-19 · **Auditeur :** session fraîche (author≠auditor) · **Worktree :** `Algo_claude_soy_wt` (isolé, lecture seule sur live)
**Cible :** `STUDY_SOYBEAN_FTMO_2026-06-19.md` (verdict **(d) NON-VIABLE**) vs `PREREGISTRATION_SOYBEAN.md` (commit `4e0f0a7`)
**Méthode :** re-exécution de tous les scripts `code/` sur `/usr/bin/python3` (numpy 2.0.2, pandas 2.2.3) + diagnostics adversariaux propres.

## VERDICT GLOBAL : **CONFIRM-WITH-CAVEATS**

Le verdict **(d) NON-VIABLE pour FTMO est CORRECT et bien soutenu.** Tous les chiffres headline reproduisent (souvent au bit près),
le wrapper est valide et non-invasif, le mécanisme central (crash de survie funded) est RÉEL et non un bug, et le verdict (d) est
atteignable par une route **littérale pré-enregistrée** (axe marge) — pas seulement par le qualificatif funded non-seuilé. Trois caveats
matériels (aucun ne renverse le verdict) : (1) la description verbale du mécanisme du crash funded est **imprécise** (c'est le floor
statique −10%, pas « la barrière daily symétrique ») ; (2) la comparaison « égal-ou-pire que le gold sur TOUS les axes » est **surévaluée**
(soybean est MEILLEUR sur le bust et l'EV grâce au stop) ; (3) l'argument marge repose en partie sur un chiffre book **cité (asia) et
non recalculé** dans q5, et le leg gold-trend est flat 50% du temps.

---

## A. Validité du wrapper — **PASS**

`validate_wrapper.py` ré-exécuté (8 s) :
- **(i)** `soy_series verify_err = 4.30e-16` ≈ 0 → `net_log` == `net_analysis.py net()`. Fenêtre 01:00→07:00 UTC + VT identiques au rapport.
- **(ii)** book ON + soy OFF → pooled p_funded = **87.01%** ∈ [86,91] → injection **non-invasive** (identité confirmée).
- **(iii)** `soy_fp` vs moteur barre (book off, soy on) : K=1.5 → |Δ|=**0.00 pt** ; K=3.0 → |Δ|=**0.00 pt**.

Les trois checks passent exactement comme rapportés (le rapport dit 99.8% pour (ii)-alignement ; cf. item B). Wrapper fiable.

## B. Alignement même-jour — **PASS**

Reproduit indépendamment :
- **∩ même-jour = 100.0%** (étude : 99.8% — écart trivial, bord de fenêtre) ; **∩ +1 shift = 80.1%** (étude : 79.6%).
- **Logique TZ correcte** : 01:00–07:00 UTC = 03:00–10:00 (EET hiver) / 04:00–11:00 (EEST été) serveur. Le rollover serveur 00:00 = 21/22:00 UTC
  veille ⇒ la fenêtre est fermement DANS le même jour-calendaire serveur/CET. Same-day = bon choix (≠ ASIA qui traverse minuit UTC ⇒ +1).
- **Sensibilité confirmée empiriquement** : un +1 NE change PAS Q2 standalone (le first-passage `soy_fp` n'utilise que les dates propres du
  soybean, book off) ; il CHANGE Q5 (survie funded K=1 : same-day **72.0%** vs +1-shift **68.2%**). Le raisonnement de l'étude est exact, et la
  conclusion qualitative du crash funded est **robuste au choix d'alignement** (les deux crashent).

## C. Logique du stop — **PASS**

`soy_stop.apply` vérifié (K=4, X=2.5%) :
- Quand `low ≤ −X` : `net` ET `low` mis à exactement **−0.025** (valeur unique sur jours déclenchés), sortie au stop, reprise perdue.
  **Pas de look-ahead** (le trigger lit le plus-bas, réalise la perte plafonnée, forfait la reprise). `alpha_given_up=87.19%`, `protection=215.76%`.
- À TOUT K∈{1,2,3,4}, le plus-bas réalisé post-stop = **−2.500%** < barrière daily −5% ⇒ **standalone ne daily-buste jamais**.
- Confirme la table Q2 : `bust_daily = 0.0%` pour V1 à tout K. La phrase « le stop élimine TOUS les bust-daily » est **précise** : V1 garde
  un `bust_floor` non-nul croissant (1.8%→10.2% de K=2 à K=4), correctement séparé dans la table — l'étude ne confond pas daily et floor.

## D. Q2 NON-VIABLE — **PASS** (reproduction exacte)

`q2_sim.py` ré-exécuté (15 s) — table identique au .txt sauvegardé :
- **Max p_funded sur TOUT le balayage frozen (4 variantes × 6 K @ 2bp) = 26.2%** (V1, K=4). 26.2% **< 0.30** (plancher CONDITIONNEL).
  → **Q2 = NON-VIABLE** au sens littéral pré-enregistré. CONFIRMÉ.
- **V2 (skip USDA) ne bat PAS V0** : V2 K=4 = 20.1% < V0 K=4 = 22.9%. CONFIRMÉ.
- **26 bp → 0.2%** (bust 65.5%, V3 K=4). CONFIRMÉ. À 1.5 bp futures-optimiste, V3 K=4 = 23.8% (toujours < 30%) → Q2 robuste au coût.
- Pierce intraday-low vs daily −5% : K=3 → 1.1% / pire −21.6% ; K=4 → 2.1% / pire −28.8%. Reproduit exactement.
- Cross-check `firstpassage` (close-to-close, borne optimiste) V0 K=4 = 37.8% @≤63td vs `soy_fp` 22.9% : l'écart = coût du plus-bas
  intraday (vérifié : firstpassage n'utilise QUE les rendements daily close-to-close — pas de plus-bas). Framing de l'étude correct.
- *Note (n'affecte pas le verdict)* : V1 K=4 a OOS 33.2% > IS 19.3% (asymétrie INVERSE du collapse IS≫OOS redouté ; IS=19.3% < 30%). Moot car
  jamais ≥ 0.50.

## E. Q3 réfutation USDA — **PASS** (sound + robuste)

`q3_usda.py` ré-exécuté — identique :
- Pire jour = **2022-06-23 (−6.65%)**, bucket **other**, **7 j** du report le plus proche (Acreage 06-30) → krach matières premières juin 2022.
- **1/15** des pires jours à ±2 j d'un report. Buckets : report_R (n=91) mean **+11.19 bp**, skew **+1.30**, 0 jour <−3% ; day_after mean −2.27 bp ;
  **other (n=1311)** mean +4.25 bp, skew **−1.81**, **6 jours <−3%** → TOUT le tail vit dans « other ».
- Skip USDA : Sharpe 1.16→**1.09**, pire jour **−6.65% INCHANGÉ**, retire 150 jours (mostly bons/neutres). Skip ne sauve pas le daily −5%.
- **Robustesse au calendrier ±1-2 j** (mon test adversarial) : même avec ±3 j de slop, seulement **2/15** pires jours deviennent
  report-adjacents ; les deux pires (juin-23 2022/2023) restent à 7 j. La conclusion « tail = météo/macro non-programmable, skip
  contre-productif » est **robuste** au caveat calendrier que l'auteur a lui-même signalé. CONFIRMÉ.

## F. Crash de survie funded (Q5) — **PASS sur le FOND, CONCERN sur la DESCRIPTION**

`q5_book.py` + `q4_funded.py` ré-exécutés — chiffres reproduits **exactement** :
- Sanity : **book seul p 87.01%, funded_value $2144, funded_survive252 100.0%** (== asia Q3). Méthode validée.
- Ablation funded : book+soy K=1 → **72.0%** ; K=2 → **50.0%** ; K=3 → **46.2%** ; K=4 → **43.2%**. Le crash 100%→43-72% est REPRODUIT.
- Q4 standalone : V1 stop K=1 → survie 252 = **100.0%**, E[wd] $1644 (reproduit).

**Le crash est RÉEL, pas un artefact** (vérifié par 3 diagnostics propres) :
1. **Décomposition de la cause** : sur 132 cohortes funded, le book SEUL a **0 bust** (vie médiane 504), book+soy K=1 a **65 busts** — tous
   sur des cohortes qui SURVIVAIENT en book-seul.
2. **Trigger** : les **65/65** busts sont déclenchés par la **ligne soybean** (`bal + a_low < lim_eff`), **0 par les segments book**. Causalement
   correct : soybean ferme à ~09:00 serveur AVANT le 1er segment book (09:00), `lim_eff` figé sur la balance @début-de-jour, plus-bas
   intraday soybean contrôlé contre la barrière. Pas de double-comptage, pas de look-ahead, K-scaling correct.
3. **Mécanisme exact** : les **65/65** busts sont **floor-bound** (`lim_eff == $9000` statique), **0 daily-bound**. À l'instant du bust, la
   balance est dans **[8866, 9154]** (médiane $9046), et la perte soybean (médiane seulement **−$60**, plafonnée −$250) tippe sous $9000.
   Le book-seul funded **rase le floor** : balance-min médiane **$9058** (=$58 au-dessus du floor), 96/132 cohortes touchent à ±$250 du floor.

> **CONCERN (description, pas conclusion).** L'étude attribue le crash à « la barrière daily symétrique » et « les tails indépendants
> s'empilent contre la barrière daily » (§Verdict, Q5(b), comparaison asia). C'est **imprécis** : la contrainte qui mord est le **floor
> statique max-loss −10% ($9000)** que le book rase déjà, PAS la barrière daily −5% (jamais binding dans les 65 busts). Le mécanisme correct
> est : *funded-survival is proximity-to-static-floor governed* — le book vit au bord du floor, soybean (même perte bornée) convertit le
> rasage en breach. La leçon asia citée (« drawdown-governed not Sharpe/correlation-governed ») reste juste ; la **formulation « barrière
> daily symétrique » est fausse au sens littéral du moteur.** Recommandation : reformuler « daily symmetric barrier » → « static −10%
> max-loss floor that the book already grazes ».

## G. Discipline de pré-registration — **PASS** (probité honnête, pas de goalpost-moving)

- La pré-registration **liste explicitement** l'ablation funded comme test (Q5(b) : « challenge **ET** funded : Δp_funded, …, funded_value »).
  Les **seuils** DIVERSIFIANTE/CONCENTRATION ne référencent QUE `p_funded` (= challenge), corr, et marge. Donc la survie funded était
  **mesurée-mais-non-seuilée** — l'auteur le déclare exactement (note de probité §Q5).
- L'auteur reconnaît : « Sur les seuils littéraux, soybean serait DIVERSIFIANTE-en-challenge ; sur l'évidence funded, il est dilutif.
  L'auditeur tranchera ce poids. » C'est **inhabituellement honnête** et **n'avance aucun seuil**.
- **Aucun seuil déplacé post-résultat** vérifié : Q2 (0.30/0.50), Q4 (0.60), Q5 (0.50/0.02/0.05/60%) tous tels que figés. Le seed/grille K
  {1,…,4} non étendue. Verdict basé sur Q2 (suffisant) + renforts. **PASS.**

## H. Calibration du verdict — **PASS** (verdict (d) atteignable littéralement ; deux nuances)

**Tension structurelle identifiée** : par la règle frozen, (d) première clause = « Q2=NON-VIABLE **ET** Q4=FUNDED-NON-VIABLE ». Or Q4
standalone **ATTEINT** le seuil littéral FUNDED-VIABLE (V1 K=1 : survie 100% ≥ 0.60, E[wd]>0). Donc (d) **ne passe PAS par sa 1ère clause** —
il passe par la **2ème clause : « Q5=CONCENTRATION disqualifiante »**. Le verdict (b) VIABLE-funded-only exige Q5≠CONCENTRATION. **Le verdict
bascule donc entièrement sur la classification de Q5.**

**Q5 = CONCENTRATION est-il atteint littéralement ?** OUI — par l'axe **marge** (règle frozen : CONCENTRATION si « marge combinée > 60% »,
condition OR) :
- Axe corr : ρ(soy, book_trend) full = **+0.00** < 0.50 → diversifiant. ✓
- Axe p_funded challenge : book+soy RISES 87→91% (≥ book−0.02, jamais < book−0.05) → diversifiant. ✓ (la survie funded n'est PAS un seuil)
- **Axe marge** : soybean seul K=1 p99=**0.20**/max 0.23 ; ajouté au métal book (Swing, déjà ~56% des jours près du cap 60% per asia) ⇒ combiné
  p99 ≈ **0.76 > 60%** même à K=1. → **CONCENTRATION par marge (littéral).** ✓

**Donc le verdict (d) est justifié par une route LITTÉRALE pré-enregistrée (marge), indépendamment du crash funded non-seuilé.** L'étude
**sous-vend** ce point : elle s'appuie sur le narratif du crash funded alors qu'elle a une route marge plus propre. La downgrade (b)→(d)
n'est PAS un overstatement.

> **CAVEAT sur l'axe marge.** `q5_book.py` **calcule** la marge soybean mais **assert** la marge book (« 56% des jours », « asia p50 0.687 »)
> via le `book_note` cité — **non recalculée in-engine** dans q5. De plus, le leg gold-trend XAU est **flat ~50% du temps** (|w| p50=0.00,
> Swing-margin p99=0.167) → le métal book n'est PAS continûment près du cap ; le chevauchement marge soy×book n'est pas garanti chaque jour.
> L'axe marge est donc **directionnellement correct mais quantitativement mou** (repose sur une citation + une hypothèse de chevauchement).
> Le disqualifieur **entièrement reproduit bout-en-bout** reste le crash de survie funded (item F).

**Comparaison « ≈ gold, pas a notch below » :**
- Données vérifiées : ASIA Q2 max p_funded **35.1%** @bust 46.4%, EV **−$150** ; SOYBEAN Q2 max **26.2%** @bust **10.2%**, EV **+$762**.
- Sur p_funded brut : soybean (26.2%) **est** pire qu'asia (35.1%) → « soybean pire » CORRECT.
- **MAIS** soybean est MEILLEUR sur bust (10.2% vs 46.4%) et EV (+$762 vs −$150), grâce au stop V1. La phrase de l'étude « **égal-ou-pire
  sur TOUS les axes décisifs** » est un **OVERSTATEMENT** : soybean domine asia sur 2 axes (bust, EV). Le bottom-line (les DEUX échouent le
  même gate, même cause structurelle edge-lent-vs-mur-91j + tail) est **juste** ; le « tous les axes » ne l'est pas.
- gold_asia ρ : l'étude rapporte +0.06/+0.07/+0.11. **Reproduit +0.070** (depuis l'asia_series du worktree). Genuine, non fabriqué. L'argument
  « décorrélation générique, pas complément-gold-spécifique (ρ légèrement POSITIF) » est correct.

---

## Reproductibilité — note importante

- **Q1** : `net_analysis.py` ré-exécuté → Sharpe 1.32/1.08/0.84, OOS 0.73/0.49/0.24, maxDD −15.8/−19.7/−23.5, skew −1.89, pire jour −6.90%,
  DSR 0.89/0.75/0.56 — **identique au centième**. `candidates.py` → `SEAS_elec_1_7` (= la stratégie) gross Sharpe 1.98, **net26 −4.53**,
  break-even 7.52 bp. Le `RT_SPREAD = 26.0` est **hardcodé dans candidates.py** (docstring « ~26 bp round-trip » CFD) — la claim « le codebase
  de la stratégie elle-même fixe la réalité CFD FTMO à 26 bp » est **factuellement exacte**. PASS-repro exact.
- **CONCERN reproductibilité Q5 (gold-ASIA)** : `q5_book.py` importe `asia_series.py` via un chemin **MAIN** absolu
  (`…/Algo_claude/data/ftmo_portfolio/asia_23_8_feasibility/code/asia_series.py`) qui **n'existe plus dans MAIN** (supprimé après l'étude asia ;
  présent UNIQUEMENT dans le worktree). Au re-run aujourd'hui, la branche gold_asia tombe dans `except` → `None` (warning imprimé). Les chiffres
  gold_asia de l'étude étaient corrects (le fichier existait au runtime ; reproduit +0.070 depuis le worktree), mais **la table corr gold_asia
  de l'étude n'est PAS reproductible depuis MAIN telle quelle.** N'affecte AUCUN chiffre du verdict (corr core, ablation, crash funded sont tous
  indépendants de gold_asia et reproduisent exactement). À corriger : repointer le chemin vers le worktree, ou copier asia_series.py.

## Synthèse des erreurs / overstatements trouvés (aucun ne renverse le verdict)

1. **[CONCERN — description]** Le crash de survie funded est attribué à « la barrière daily symétrique / tails empilés contre la barrière
   daily ». Le moteur montre que **les 65/65 busts sont floor-bound ($9000 statique), 0 daily-bound**. Reformuler : « static −10% max-loss
   floor que le book rase déjà ». Le fond (drawdown-governed) est juste.
2. **[OVERSTATEMENT — comparaison]** « égal-ou-pire que le gold sur TOUS les axes décisifs » : faux sur bust (10.2% vs 46.4%) et EV (+$762 vs
   −$150), où soybean est MEILLEUR grâce au stop. Le verdict commun (les deux NON-VIABLE) tient ; le « tous les axes » non.
3. **[CAVEAT — marge non recalculée]** L'axe marge (la seule route LITTÉRALE frozen vers CONCENTRATION) assert la marge book via citation asia,
   non recalculée dans q5 ; le leg gold-trend est flat 50% du temps. Directionnellement correct, quantitativement mou.
4. **[CONCERN — reproductibilité]** Chemin gold-ASIA cassé dans MAIN (fichier supprimé) → table corr gold_asia non re-runnable telle quelle.
   N'affecte pas le verdict.

## Verdict final de l'auditeur

**CONFIRM-WITH-CAVEATS.** Le **(d) NON-VIABLE pour FTMO est correct** :
- **Q2 = NON-VIABLE** est solide et reproduit exactement (max 26.2% < 30%, robuste de 1.5 à 26 bp).
- Q2 étant **disqualifiant à lui seul** par la règle frozen pour la voie challenge, et **Q5 = CONCENTRATION atteignable par l'axe marge
  littéral** (clôt aussi (b) VIABLE-funded-only), le verdict (d) **ne repose pas sur un déplacement de seuil**.
- Le crash de survie funded (le claim le plus surprenant) est **RÉEL, causalement correct, sans bug** — seule sa **dénomination** (« daily »
  au lieu de « floor statique ») est à corriger.
- La probité author≠auditor est **exemplaire** (caveat funded déclaré, poids remis à l'auditeur, aucun seuil bougé).

L'unique correction substantielle demandée : **renommer le mécanisme du crash funded de « barrière daily symétrique » en « floor statique
−10% que le book rase déjà »** (vérifié : 65/65 busts floor-bound, balance médiane $9046 à l'instant du bust, book-min médian $9058).
