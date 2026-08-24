# ÉTUDE DE FAISABILITÉ — SOYBEAN reopen-drift (01:00→07:00 UTC) comme sleeve FTMO candidate

**Date :** 2026-06-19 · **Branche :** `claude/soybean-ftmo-feasibility` (worktree isolé) · **Statut :** RECHERCHE PURE — go/no-go
**Pré-registration :** `PREREGISTRATION_SOYBEAN.md` (committée AVANT tout résultat, commit `4e0f0a7`)
**Auteur :** session Claude Code (author≠auditor — validation indépendante en session fraîche)
**Cadre :** sandboxé. AUCUN déploiement, AUCUN toucher au book live (`ftmo_live/`, EA gelé, FLAT, compte vm14 armé lundi).
Le book FTMO 4-sleeves (vm14) est INDÉPENDANT et n'est pas affecté. Jumeau méthodologique de
`asia_23_8_feasibility/` (gold overnight-drift) — mêmes engines audités réutilisés.

---

## VERDICT — (d) NON-VIABLE pour FTMO

SOYBEAN reopen **échoue le challenge FTMO** (Q2, disqualifiant à lui seul) et n'a **aucune voie d'accès au
format funded** où il survit pourtant en standalone (Q4). Sur les deux axes décisifs il est **≈ identique
au gold ASIA_23_8** (déjà classé NON-VIABLE / REJET), pas « a notch below » comme l'annonce le rapport.
S'ajoutent deux aggravants propres au soybean (un tail négatif et une réalité de coût CFD).

| | p(pass)/p(funded) | attempts | EV campagne | bust/tentative |
|---|--:|--:|--:|--:|
| **Book incumbent (4 sleeves, vm14)** | **87.0 %** | 3.24 | **+$1 554** | — |
| SOYBEAN challenge — meilleur (V1 stop, K=4) **@ 2 bp** | **26.2 %** | 1.12 | +$762 | 10.2 % |
| SOYBEAN challenge — meilleur (V1 stop, K=4) **@ 3 bp (CFD réel mesuré)** | **24.0 %** | 1.1 | ~+$650 | 13 % |

Plancher CONDITIONNEL = **0.30** → échec à 2 **ET** 3 bp. **Le spread n'est PAS le driver du verdict** (cf. note coût + §indépendance).

**Cause racine (jumelle du gold + de l'ORB) :** l'edge est **réel mais trop LENT** pour le mur de 91 j à un
sizing survivable ; pousser K pour atteindre +10 %/+5 % fait exploser le bust. C'est la signature
**« no-bust × temps-illimité »** (L24) — pas un edge exploitable en challenge. **Aucune des 4 configs
pré-enregistrées (V0/V1/V2/V3) n'atteint même le plancher CONDITIONNEL de 0.30.**

**Trois découvertes qui CORRIGENT le rapport :**
1. **Le « skip USDA obligatoire » est RÉFUTÉ (Q3).** Le tail (skew −1.9, pire jour −6.9 %) ne vient PAS des
   rapports USDA : le pire jour (**2022-06-23, −6.65 %**) est un jour non-rapport (krach matières premières
   juin 2022) ; **1/15** des pires jours sont à ±2 j d'un rapport ; les matins de rapport USDA sont au
   contraire **positifs** (+11 bp, skew **+1.30**). Le tail est **météo-de-croissance / macro** (juin-août),
   **non-programmable**. Skipper l'USDA retire 150 bons/neutres jours, **baisse** le Sharpe (1.16→1.09) et
   **ne touche pas** le pire jour. **La vraie mitigation est le STOP intraday dur**, pas le skip de dates.
2. **Le STOP intraday −2.5 % est quasi-gratuit et décisif (Q2/Q4).** Il **élimine TOUS les bust-daily**
   (le plus-bas intraday qui perce −5 %), monte le Sharpe standalone 1.16→1.53, et transforme la survie
   funded (V0 sans stop : bust 65-100 % ; V1 stop : survie 82-100 %). alpha cédé ≈ 0 %, protection +12-23 %.
3. **Décorrélé ≠ bénéfique (Q5).** SOYBEAN est décorrélé (ρ ≈ 0) du book réel ET du gold-ASIA hypothétique —
   mais c'est une décorrélation **générique** (autre classe d'actif), pas le **complément négatif spécifique
   au gold** que vend le rapport (ρ vs gold-ASIA = **+0.06/+0.11**, légèrement POSITIF). L'ablation funded
   montre que l'ajouter au book **EFFONDRE la survie funded du book 100 %→43-72 %** (la leçon asia :
   *funded-survival is drawdown-governed*). **Mécanisme exact (vérifié à l'audit, 65/65 busts) : le binding
   est le FLOOR statique −10 % ($9000), pas la barrière daily.** Le book funded **rase déjà le floor**
   (balance-min médiane ≈ $9058, +$58 ; 96/132 cohortes à ±$250 du floor) ; la perte journalière bornée de
   soybean (médiane −$60, plafonnée −$250) bascule la frôlée en breach. La décorrélation ne protège PAS :
   le book vit au bord de son plancher, donc *toute* source de perte indépendante le buste.

**Note de coût — CORRIGÉE (mesure opérateur, 2026-06-19) :** le « 26 bp = FTMO CFD reality » que citait une
version antérieure de ce verdict est une **HYPOTHÈSE NON-SOURCÉE**, pas une mesure : `candidates.py:24`
(`RT_SPREAD = 26.0`) + docstring l.2-4 (« ~13 bp one-way, ~26 bp round-trip »), un placebo « spread ag large »
d'un script de screening précoce, avec l'étiquette « <- FTMO CFD reality » **codée en dur** dans
`validate_audit.py:67`. Le rapport de due-diligence l'a **lui-même révisé à la baisse** (≤3 bp, §4/§9 : « Read
the live Market-Watch spread to confirm »). **L'opérateur a mesuré le SOYBEAN.c FTMO réel à ≤3 bp.** ⇒ le 26 bp
est **CADUC** ; je retire le cadrage « mort par le spread ». **À ≤3 bp le coût n'est PAS le killer :** l'edge
EXISTE (Sharpe 1.08 @2bp, 0.84 @3bp). **Le verdict (d) ne repose PAS sur le spread** — voir l'encadré ci-dessous.

> **Indépendance au spread (re-run @2 ET 3 bp, `spread_recheck.py`).** Le verdict tient aux **deux axes
> spread-INVARIANTS** : (1) **challenge trop lent** — MAX p_funded = **26.2 % @2bp / 24.0 % @3bp**, tous deux
> ≪ 0.30 (le spread ne déplace que ~2 pts, loin du gate ; le killer est le mur de 91 j, L24) ; (2) **dilution
> funded** — ajouter soybean au book crase la survie funded **100 %→44-72 % @3bp** comme @2bp (mécanisme =
> floor statique −10 %, indépendant du coût). S'y ajoute l'**OOS qui se dégrade** (0.49 @2bp, 0.24 @3bp). Le
> spread ≤3 bp réel **valide la prémisse du rapport** (la stratégie n'est PAS cost-dead) mais **ne sauve aucun
> des trois axes** — le verdict aurait été identique si j'avais ignoré le 26 bp dès le départ.

**Recommandation : NE PAS lancer.** Ni en challenge (Q2 disqualifiant), ni en book add-on (Q5 dilutif funded).
**Le coût n'est PAS l'obstacle** : le SOYBEAN.c CFD FTMO est à **≤3 bp réel (mesuré par l'opérateur)**, et le
verdict tient identique à 2 ET 3 bp (le « 26 bp » était une hypothèse de screening caduque — voir §coût). L'edge
« existe » à ≤3 bp (Sharpe 0.84-1.08) mais il est **modeste, en décroissance (OOS 0.49→0.24)** et **dilutif au
book A+B** (standalone ≪ D-gate 2.54) ; il échoue le propfirm par la **lenteur** (challenge) et la **dilution
funded** (book), deux axes **indépendants du spread**. Voir §Reco.

---

## Q1 — Reproduction : le rapport reproduit AU CENTIÈME ; la tension de coût est ailleurs

`net_analysis.py` / `full_analysis.py` / `validate_audit.py` ré-exécutés sur le stack actuel (SOYBEAN M1→H1
true-UTC, 2017-12→2026-06, 1 500 jours complete-window). **Toutes** les métriques headline reproduisent :

| spread RT | Sharpe | Sortino | DSR(20) | OOS | maxDD | Calmar | skew | pire jour |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| 1 bp | 1.32 ✓ | 1.21 ✓ | 0.89 ✓ | 0.73 ✓ | −15.8 % ✓ | 0.80 ✓ | −1.88 | — |
| **2 bp (base)** | **1.08 ✓** | **1.00 ✓** | **0.75 ✓** | **0.49 ✓** | **−19.7 % ✓** | 0.52 ✓ | **−1.89 ✓** | **−6.90 % ✓** |
| 3 bp | 0.84 ✓ | 0.78 ✓ | 0.56 ✓ | 0.24 ✓ | −23.5 % ✓ | 0.34 ✓ | −1.90 | — |

Gross VT **1.56**, no-VT **1.53** ✓, short-window null **−1.56** ✓, β soybean **+0.239** ✓ / R² **0.265** ✓ /
α HAC t **+4.63** ✓, table annuelle @2bp (2018 +0.9 … 2026 +4.4, **7/9 +**) ✓, MC @2bp médiane 1.08 [5e 0.42]
P(SR>1) 57 % ✓, MC gross médiane 1.58 P>1 90 % ✓, voisinage start-01:00 plateau (1.57/1.52/1.64/1.56) ✓,
robustesse temps d'exécution (entrée +1h 1.32, sortie −1h 1.64) ✓, drop top-20 → 0.88 ✓.

**PASS-repro EXACT.** Code = source de vérité (vérification série : `net_log` == `net_analysis.net()` à
|Δ| = 4.3e-16). **Aucune divergence numérique.** Sur le COÛT : `candidates.py:24` (`RT_SPREAD = 26.0`, docstring
l.2-4 « ~13 bp one-way, ~26 bp round-trip ») fixe un spread CFD « ag large » de 26 bp — **hypothèse de screening
précoce, NON mesurée** — répercutée par l'étiquette codée en dur `validate_audit.py:67` « <- FTMO CFD reality ».
Le rapport de due-diligence l'a ensuite **révisée à ≤3 bp** (§4/§9, « confirm live ») et **l'opérateur a mesuré
le SOYBEAN.c FTMO réel à ≤3 bp** (2026-06-19) → **le 26 bp est CADUC.** À ≤3 bp l'edge **existe** (Sharpe
**0.84 @3bp, 1.08 @2bp** ; break-even gross ≈ 5.9-7.5 bp/trade ; il faut ≤2 bp pour Sharpe>1). La colonne spread
de `deep_history_utc` (Dukascopy, unités ambiguës) n'était pas exploitable — c'est la mesure live opérateur qui fait foi.

## Q2 — Gates FTMO 2-step : NON-VIABLE (le mur, comme le gold)

Moteur barre v2.2 audité (pin `605f4a4`) + injection soybean (plus-bas intraday inclus, alignement **même-jour**
validé 99.8 %), book OFF. **Validation du wrapper (3/3 PASS) :** (i) série == net_analysis (|Δ|=0) ;
(ii) book ON + soy OFF reproduit **87.01 %** ; (iii) `soy_fp` lean == moteur barre **|Δ|=0.00 pt** (K=1.5, 3.0).

**Le point dur du soybean (skew −1.9) — plus-bas intraday vs barrière daily −5 % :**

| K | P(low < −5 %) | pire low | p1 low | vol compte |
|--:|--:|--:|--:|--:|
| 2.0 | 0.6 % | −14.4 % | −3.6 % | 19 % |
| 3.0 | 1.1 % | −21.6 % | −5.5 % | 29 % |
| 4.0 | 2.1 % | −28.8 % | −7.3 % | 38 % |

Aux sizings nécessaires pour un p_funded non-trivial (K≥3), le plus-bas intraday perce −5 % sur ~1-2 % des
jours et les pires excursions sont **catastrophiques** (−21 à −29 %) → floor-bust instantané. **C'est le tail
négatif qui percute la barrière** — exactement la réservation #2, et pire que le gold (+0.35).

**Sweep K × {V0,V1,V2,V3} @ 2 bp (p_funded poolé / IS / OOS ; bust/tentative) :**

| variante | K | p_funded | IS | OOS | att | bust | bust_daily | med_t (j) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| V0 base | 3.0 | 13.9 % | 12.9 | 14.8 | 1.33 | 24.2 % | 13.2 % | 62 |
| V0 base | 4.0 | 22.9 % | 20.2 | 25.8 | 1.58 | 31.5 % | 16.6 % | 52 |
| **V1 stop** | 3.0 | 15.2 % | 13.7 | 16.6 | 1.05 | 5.3 % | **0.0 %** | 63 |
| **V1 stop** | **4.0** | **26.2 %** | 19.3 | 33.2 | 1.12 | 10.2 % | **0.0 %** | 57 |
| V2 skipUSDA | 4.0 | 20.1 % | 16.7 | 23.6 | 1.54 | 30.2 % | 17.7 % | 56 |
| V3 stop+skip | 4.0 | 22.5 % | 16.3 | 28.8 | 1.10 | 8.5 % | 0.0 % | 60 |

**Lecture.**
1. **Aucune config n'atteint 0.30** (plancher CONDITIONNEL), encore moins 0.50 (VIABLE). Maximum **26.2 %**
   (V1, K=4) — et au prix d'un sizing extrême (vol compte 38 %). → **NON-VIABLE** au sens pré-enregistré.
2. **Le STOP (V1) élimine 100 % des bust-daily** (`bust_daily` = 0.0 % à tout K) : il coupe le plus-bas
   intraday avant qu'il ne perce −5 %. Il monte aussi le p_funded (26.2 % vs V0 22.9 %) en convertissant des
   busts en survie. Mais il ne rend pas l'edge plus RAPIDE → plafond 26 %.
3. **Le SKIP USDA (V2/V3) NUIT** : il baisse le p_funded (V2 K=4 = 20.1 % < V0 22.9 %) en retirant des
   opportunités, sans bénéfice (le stop gère déjà le tail). → réfute le rapport (cf. Q3).
4. **EV triplet (meilleur-K) :** V0 K4 (22.9 %, 1.58, **−$130**) ; V1 K4 (26.2 %, 1.12, **+$762**) ;
   V3 K4 (22.5 %, 1.10, **+$628**). L'EV positif de V1/V3 vient du **stage funded** (cf. Q4), pas du challenge.
5. **Contre-vérif `firstpassage` (close-to-close, borne optimiste) :** V0 K=4 → 37.8 % à ≤63 j ; terminal
   (sans mur) 41-50 % mais **médiane 30-115 j**. L'écart firstpassage 37.8 % vs `soy_fp` 22.9 % = le coût du
   plus-bas intraday (le tail). Le terminal qui « passe » à long terme = artefact temps-illimité, pas viabilité.
6. **Sensibilité coût :** dans la plage RÉELLE mesurée (≤3 bp), p_funded MAX (V1 stop, K=4) = **26.2 % @2bp →
   24.0 % @3bp** — le spread ne déplace que ~2 pts, **tous deux ≪ 0.30** ; le killer est la lenteur, pas le coût.
   (Le 26 bp de `candidates.py` — hypothèse caduque, cf. Q1/§coût — donnerait 0.2 % ; non pertinent, l'opérateur
   mesure ≤3 bp.)

**Verdict Q2 = NON-VIABLE.**

## Q3 — Le tail USDA : RÉFUTATION du « skip obligatoire » du rapport

Calendrier USDA construit (WASDE 2025/26 confirmés + 2017-24 best-estimate + Grain Stocks/Plantings/Acreage),
**validé** par range réalisé (le skip touche 150 matins = report-day ∪ day-after).

**(a) Attribution du tail (pires 15 jours, net @2bp) :**

| date | net % | bucket | jours/rapport | proche ±2j ? |
|---|--:|---|--:|:--:|
| **2022-06-23** | **−6.65** | other | −7 | non |
| 2023-06-23 | −5.51 | other | −7 | non |
| 2024-07-24 | −4.35 | other | +12 | non |
| 2025-07-07 | −4.01 | other | −4 | non |
| 2022-08-24 | −3.86 | other | +12 | non |

→ **1/15** des pires jours est à ±2 j d'un rapport programmé. Le pire (2022-06-23, krach matières premières)
et le 2e (2023-06-23) sont à **7 j** du nearest report (Acreage 06-30). Le tail est **juin-août** (météo de
croissance) + **macro 2022** — **non-programmable**.

**(b) Tail par bucket :**

| bucket | n | mean | pire jour | skew | #jours < −3 % |
|---|--:|--:|--:|--:|--:|
| report_R (matin de rapport) | 91 | **+11.19 bp** | −0.80 % | **+1.30** | 0 |
| day_after (digestion) | 59 | −2.27 bp | −1.22 % | +0.21 | 0 |
| **other (non-USDA)** | 1 311 | +4.25 bp | **−6.65 %** | **−1.81** | **6** |

**TOUT le tail vit dans « other ».** Les matins de rapport USDA ont une dérive POSITIVE et un skew POSITIF
(la fenêtre overnight ne tient jamais à travers la publication de midi ET — elle ne capte que l'anticipation).

**(c) Edge AVEC vs SANS skip :** all Sharpe 1.16 / OOS 0.51 / pire −6.65 % ; skip Sharpe **1.09** / OOS 0.62 /
pire **−6.65 % (INCHANGÉ)** / skew −1.81 (légèrement pire). À K=4, pire-jour-scalé −26.6 % avec ET sans skip.

**Verdict Q3 : USDA NON-MATÉRIEL.** Le skip n'améliore pas le pire jour (0 pt), ne sauve pas le daily −5 %,
et coûte du Sharpe. **La vraie mitigation du tail est le STOP intraday** (Q2/Q4 : cape à −2.5 %, ~gratuit).
*Le rapport a raison sur l'EXISTENCE du tail mais TORT sur sa cause et sa mitigation.*

## Q4 — Format funded : VIABLE en standalone (avec stop), mais sans voie d'accès

`run_funded` (horizon 504 j, retrait /14 j, barrières daily −5 % + max −10 % statiques actives), book OFF,
132 cohortes soy-actives (2018-06→2024-06).

| variante | K | p(survie 6 mo) | p(survie 12 mo) | E[retraits] | bust |
|---|--:|--:|--:|--:|--:|
| V0 (sans stop) | 1.0 | 84.9 % | 64.4 % | $1 544 | 65.1 % |
| V0 (sans stop) | 2.0 | 48.5 % | 9.1 % | $1 352 | 100 % |
| **V1 (stop)** | 1.0 | 100 % | **100 %** | $1 644 | 0 % |
| **V1 (stop)** | 2.0 | 97.0 % | **86.4 %** | $3 529 | 29.5 % |
| **V1 (stop)** | 3.0 | 88.6 % | **82.6 %** | $5 221 | 33.3 % |
| V3 (stop+skip) | 3.0 | 93.9 % | 90.1 % | $4 390 | 25.8 % |

**Sans le stop, le funded s'effondre** (le tail négatif buste : 65-100 %). **Avec le stop, survie 82-100 %**
à K modéré + retraits sains ($3.5-5.2k). → **FUNDED-VIABLE en standalone** (V1 le meilleur ; V3 confirme que
le skip réduit les retraits → inutile). **MAIS** (i) **aucune voie d'accès** : il faut passer le challenge
(Q2 NON-VIABLE) ou un véhicule funded-direct (FTMO n'en a pas) ; (ii) conditionnel au même ≤2-3 bp irréaliste
en CFD. Identique à `asia_23_8_funded` = **(c) REJET** (« survit standalone mais pas d'accès »).

## Q5 — Apport au book RÉEL vs gold : décorrélé mais DILUTIF au funded

Book réel reconstruit (`cleanroom.build_signals`) : or-trend (WT XAU) + J1 (WT USDJPY) + nightly (GER40 ON) +
micro-ORB. **Cross-validation : book seul = p 87.01 %, funded_value $2 144** (== asia Q3) → méthode validée.

**(a) Corrélation (Pearson, daily net) :**

| fenêtre | n | book trend | or-trend | J1 | gold-ASIA (hypothétique) |
|---|--:|--:|--:|--:|--:|
| full | 1 461 | +0.00 | −0.03 | +0.03 | **+0.07** |
| soy fort 2018-21 | 742 | −0.03 | −0.08 | +0.06 | **+0.06** |
| soy faible 2022-25 | 656 | +0.02 | +0.02 | +0.02 | +0.11 |

→ Décorrélé (|ρ| < 0.15 partout) du book réel **ET** du gold-ASIA. **MAIS** ρ(soy, gold-ASIA) ≈ ρ(soy, book) ≈ 0,
et même légèrement **positif** : c'est de la décorrélation **générique** (autre actif), **pas** le « complément
négatif au gold » spécifique que vend le rapport (§7 : « negative regime-correlation to the gold sleeve »).
L'argument central transfère donc au book réel… **en étant générique et non-spécifique au gold.**

**(b) Ablation challenge ET funded (book vs book+soy, V1 stop) :**

| config | p_funded challenge | Δp | **survie funded 12 mo** | EV | ΔEV |
|---|--:|--:|--:|--:|--:|
| **book seul** | 87.01 % | — | **100.0 %** | +$1 554 | — |
| book+soy K=1 | 87.01 % | +0.00 | **72.0 %** | +$1 702 | +$148 |
| book+soy K=2 | 88.96 % | +1.95 | **50.0 %** | +$1 207 | −$347 |
| book+soy K=3 | 90.69 % | +3.68 | **46.2 %** | +$1 443 | −$111 |
| book+soy K=4 | 90.91 % | +3.90 | **43.2 %** | +$1 312 | −$242 |

**Le challenge p_funded bouge à peine** (book déjà saturé à 87 %). **Mais l'ajout EFFONDRE la survie funded du
book : 100 %→72 %/50 %/46 %/43 %.** Même à K=1 (le plus petit), −28 pts. C'est la **leçon asia** (extension L24,
*funded-survival-is-drawdown-governed*). **Mécanisme exact (vérifié à l'audit indépendant : 65/65 busts) :
le binding est le FLOOR statique −10 % ($9000), PAS la barrière daily −5 %** (0 daily-bound dans les 65 busts).
Le book funded **rase déjà le floor** : balance-min médiane ≈ **$9058** (+$58 au-dessus de $9000), 96/132
cohortes passent à ±$250 du floor. La perte journalière **bornée** de soybean (médiane −$60, plafonnée −$250
par le stop) **bascule la frôlée en breach floor**. Un sleeve décorrélé, survivable-standalone, à Sharpe positif
crase donc quand même la survie funded : **la décorrélation ne protège PAS** — le book vit au bord de son
plancher, donc *toute* source de perte indépendante le buste. ΔEV négatif dès K≥2.

**(c) Marge :** soybean = instrument distinct (CFD ag ~1:10). Empreinte K=2 : p50 0.18/p99 0.40 ; K=3 :
p50 0.27/**p99 0.60**. Le book lie déjà le cap 60 % ~56 % des jours (métal Swing) ; soybean **empile** sa marge
pendant le chevauchement 01:00-07:00 → combiné > 60 % à K≥2 (axe concentration, comme asia).

**Verdict Q5 :** décorrélé (seuil littéral DIVERSIFIANTE atteint sur le p_funded challenge), **MAIS** l'ablation
funded (in-scope) révèle une **concentration de drawdown** disqualifiante (survie book 100→43-72 %) + marge
empilée à K≥2. **SOYBEAN n'aide PAS le book** ; il est **dilutif au stage funded**.

---

## Comparaison explicite à ASIA_23_8 — « a notch below gold » est INEXACT

| axe décisif | ASIA_23_8 (gold) | SOYBEAN | verdict comparatif |
|---|---|---|---|
| Challenge gates | NON-VIABLE (max 35 % p-funded) | **NON-VIABLE (max 26 %)** | soybean **pire** |
| Cause | edge trop lent / 91 j (L24) | **idem** | identique |
| Funded standalone (avec stop) | survit (REJET = pas d'accès) | **survit (idem)** | identique |
| Ajout au book funded | crase la survie | **crase 100→43-72 %** | identique (leçon asia) |
| Swap-free | confirmé | **confirmé** (01:00-07:00 ne croise jamais 21/22:00 UTC) | identique |
| Skew daily | **+0.35** (favorable) | **−1.9** (tail à la baisse) | soybean **pire** |
| OOS récent | ~0.96 | **0.49** (edge refroidi) | soybean **pire** |
| Réalité coût | spread gold modéré | **CFD ag ~26 bp = mort** | soybean **pire** |
| Mitigation tail | n/a (skew +) | **stop −2.5 % (skip USDA inutile)** | soybean a besoin du stop |

→ Soybean partage l'**échec structurel décisif** du gold ASIA (edge trop lent vs mur 91 j → challenge
non-viable ; funded sans voie d'accès ; dilutif au funded du book). Il est **pire** sur le skew (−1.9 vs +0.35),
l'OOS (0.49 vs 0.96) et le coût CFD (~26 bp), mais **mieux maîtrisé** sur le bust de challenge grâce au stop
(V1 10.2 % vs le 46 % NON-stoppé du gold) — son plafond de p_funded (26 %) reste néanmoins SOUS celui du gold
(35 %). **Net : même verdict, profil de risque différent** — pas « a notch below » (les deux échouent pour la
même raison de fond), mais pas non plus uniformément pire. Honnêteté : le bust-control de soybean vient du stop
V1 (que le headline gold n'utilisait pas) ; comparaison stop-vs-stop non disponible côté gold.

## Recommandation & véhicule (futures vs CFD)

1. **NE PAS lancer sur FTMO** — **pas pour le coût** (CFD SOYBEAN.c à **≤3 bp réel mesuré** ; le 26 bp était une
   hypothèse caduque), mais pour le **FIT propfirm**, sur deux axes **spread-invariants** : challenge trop lent
   (MAX p_funded 24-26 % ≪ 0.30, à 2 comme à 3 bp) **et** dilution de la survie funded du book (Q5, 100 %→44-72 %).
2. **Futures vs CFD = non-débat ici.** Le rapport préférait les futures (ZS) pour un spread plus tight ; mais à
   ≤3 bp le CFD FTMO est équivalent côté coût. **Le véhicule ne change pas le verdict — c'est le fit, pas le spread.**
3. **Même en futures/CFD direct, peu attrayant :** Sharpe net ~1.1 @2bp (0.84 @3bp) mais **OOS 0.49→0.24** (edge
   en décroissance, sort d'un DD de 4 ans), tail négatif. **Dilutif au book personnel A+B** (standalone ≪ D-gate **2.54**).
4. **Le spread est confirmé OK (≤3 bp) — mais ne lève PAS le verdict.** Le make-or-break n'était PAS le spread ;
   c'est le fit (lenteur + dilution funded, spread-invariants). Si jamais re-considéré comme **sleeve de revenu sur
   un compte DÉJÀ funded** (le seul cadre où l'edge « vit »), pré-requis obligatoires : **stop −2.5 % intraday**
   (pas le skip USDA) ; drift glissant 12 m ≥ 0 ; et surtout **re-mesurer la survie funded du book AVEC le sleeve**
   (Q5 montre qu'il la crase même décorrélé) avant tout ajout.

---

## Reproductibilité
- Pré-registration : `PREREGISTRATION_SOYBEAN.md` (commit `4e0f0a7`, avant résultats).
- Code (`code/`) : `usda_calendar.py`, `soy_series.py` (série + plus-bas intraday + tags USDA, |Δ|=0 vs
  net_analysis), `soy_stop.py` (stop V1 + skip V2, adapté d'`asia_stop`), `soy_inject.py` (wrapper moteur barre
  v2.2, alignement même-jour, validé soy-OFF→87.01), `soy_fp.py` (copie d'`asia_fp`, |Δ|=0 vs barre),
  `validate_wrapper.py`, `q2_sim.py`, `q3_usda.py`, `q4_funded.py`, `q5_book.py`.
- Résultats (`results/`) : `q1_*.txt`, `q2_standalone.json`, `q3_usda.json`, `q4_funded.json`, `q5_book.json`,
  `q*_console.txt`.
- Données : `data/deep_history_utc/SOYBEAN_M1.csv` (true-UTC, local, gitignored). Engine v2.2 pin `605f4a4`.
- Env : `/usr/bin/python3` (numpy 2.0.2, pandas 2.2.3, statsmodels 0.14.6, scipy 1.13.1).
- **Aucun fichier live touché.** Travail en **worktree isolé** (`Algo_claude_soy_wt`) — protection contre les
  collisions de sessions parallèles partageant le working-dir (incident documenté ; cf. [[asia_23_8_ftmo_feasibility_2026-06]]).
  Engines + données lus via chemins absolus MAIN (infra partagée branch-invariante + caches gitignored).

### Note de probité (author≠auditor)
- Q5 : le seuil pré-enregistré DIVERSIFIANTE/CONCENTRATION ne portait que sur le p_funded **challenge** + corr +
  marge ; l'ablation **funded** (pré-enregistrée comme test mais non-seuilée) révèle la concentration de
  drawdown. Je l'ai mesurée (in-scope) APRÈS avoir reçu la leçon asia-funded en cours de session, et la rapporte
  comme qualificatif matériel — sans déplacer aucun seuil. Sur les seuils littéraux, soybean serait
  DIVERSIFIANTE-en-challenge ; sur l'évidence funded, il est dilutif. L'auditeur tranchera ce poids.
- Q3 : calendrier USDA 2017-24 best-estimate (±1-2 j) ; l'attribution des pires jours est **robuste à cela**
  (distance ±2 j à TOUT rapport ; les pires jours sont à 7+ j). Conclusion inchangée si calendrier corrigé.
- Le verdict (d) repose sur Q2 (suffisant) ; Q4/Q5 le renforcent. Aucun seuil n'a été déplacé post-résultat.
- **Audit indépendant (author≠auditor, `AUDIT_INDEPENDENT.md`) : CONFIRM-WITH-CAVEATS.** Les 8 items (A-H)
  PASS, tous les chiffres reproduits (souvent au bit près), le crash funded vérifié RÉEL (non-bug : 65/65 busts
  floor-bound, K-scaling correct, pas de look-ahead). **Deux corrections de l'auditeur INTÉGRÉES ci-dessus :**
  (1) le mécanisme du crash funded est le **floor statique −10 %**, pas la « barrière daily » (reformulé en
  Q5b + Verdict §3) ; (2) « égal-ou-pire sur tous les axes » était trop fort — soybean a un bust de challenge
  **mieux** maîtrisé via le stop (reformulé en §Comparaison). L'auditeur a aussi noté la robustesse du chemin
  d'import asia_series (corrigé : worktree-local + fallback MAIN). Aucune correction ne renverse le verdict (d).
