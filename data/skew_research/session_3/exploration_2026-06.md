# Skew Research — Session 3 — Exploration 2026-06
*Objectif : sleeves SKEW+ / low-DD pour portefeuille à corrélation négative entre sleeves (L7).
Esprit : edge D'ABORD, barrières ENSUITE. Gate phase-1 léger (t brut>2 ET skew≥0). Signaux nus (L10).
Périmètre : écrit uniquement dans `data/skew_research/session_3/`. Candidats-leçons NOMMÉS.*
Données : NQ databento RTH 2010-2026 ; FOMC/OPEX via `economic_calendar.csv` (2020+) & calcul 3e-vendredi.

---

## PHASE 1 — Edge brut (sans coût, exploratoire, généreux)

| # | Candidat (réf.) | Signal nu | n | mean | t brut | **skew** | forme | Phase 2 ? |
|---|---|---|---:|---:|---:|---:|---|:--:|
| 1 | **Pré-FOMC drift** (Lucca-Moench 2015) | long prior-close→14:00 ET, jours FOMC | 51 | +34 bps (narrow) / **+67** (full pré-jour) | **1,97 / 2,58** | **+0,13 / +0,88** | bien distribué (top5%=19 %), hit 59 % | ✅ **OUI** |
| 2 | PEAD index/méga-caps (Bernard-Thomas) | surprise→drift | — | — | — | — | pas de data earnings ; archive = mort large-caps post-2006 | ❌ cite archive |
| 3 | Last-hour momentum (Gao-Han-Li-Zhou 2018) | sign(1ère ½h)×dernière ½h | 3978 | −0,06 | **−0,13** | +0,16 | **pas d'edge** | ❌ no-edge |
| 4 | Overnight conditionnel (Lou-Polk-Skouras) | −sign(intraday[t])×overnight[t+1] | 4104 | +0,33 | **0,27** | +0,35 | conditionnel n'ajoute rien ; *inconditionnel* +4,9/t4,04 mais **skew −0,70** (beta, archivé) | ❌ |
| 5 | OPEX / quad-witching (Stoll-Whaley) | rendement jour 3e-vendredi | 192 / 64 | quad-day **−25 bps** | −1,96 | **−0,95** | seule cellule signif = quad NÉGATIF + skew négatif | ❌ mauvais profil |

**Survivant unique : C1 Pré-FOMC.** Edge brut t≈2-2,6, **skew positif**, P&L bien distribué (pas tail-lottery),
hit 59 %. Les autres : pas d'edge brut (C3, C4-conditionnel), ou profil skew négatif sur la seule cellule
significative (C5 quad-witching ; C4-inconditionnel = beta). Drapeau directionnel noté : **quad-witching day =
drift NÉGATIF** (short-able mais skew −0,95 → mauvais profil pour ce portefeuille).

---

## PHASE 2 — Confrontation aux barrières (C1 seulement)

| Barrière | Test | Résultat |
|---|---|---|
| **Coût (L33)** | net de coût (1 nuit tenue = swap + 2 spreads) | **cost-immune** : +34 bps/évt → net **+28,6** @5bps, **+13,6 @20bps** encore positif. L'edge par-événement (dizaines de bps) dwarfe les coûts — contrairement aux edges intraday bps-level. |
| **Two-sided / beta (L25)** | c'est un **premium long d'événement** (pas un signal 2-sided) | positif **6/7 ans** : 2020 +58, 2021 **−37**, **2022 +123** (bear !), 2023 +15, 2024 +52, 2025 +1, 2026 +7. → **pas du pur bull-beta** (positif dans le bear 2022). Mais **décay récent** (2025/26 ≈ 0). |
| **Load-bearing (L26)** | dates connues à l'avance + fenêtre à heure fixe | pas d'artefact de fill ; calendrier FOMC publié → robuste. |
| **OOS / régime (L31)** | 2020-22 vs 2023-26 | +48 → +21 bps (**décay**) ; échantillon **N=51 (faible puissance)** ; littérature : effet affaibli post-2011/publication. |
| **Archive** | `RAPPORT_institutionnel_FTMO_ORB.md` | FOMC **est** dans la sweep ~1100-hyp → verdict global « beta long faible, SR≤0,34, **ne bat pas la barrière FTMO en standalone** ». `INTRADAY_decorrelated_search_NQ.md` le listait comme **lead non-testé**. → en **standalone challenge-passer = clos (cite)** ; en **sleeve décorrélé = caractérisation fraîche (ce livrable).** |

---

## PHASE 3 — Aptitude portefeuille (le vrai critère)

- **corr(sleeve Pré-FOMC, long-equity daily) = +0,11** → **structurellement décorrélé** (ne tire que ~7 jours/an ; série = 0 le reste du temps).
- Sur les jours FOMC seuls, corr au marché = +0,70 (c'est du beta *ces jours-là*, mais 7 j/an → dilué).
- Pas de paires intra-session (1 seul survivant). **Corrélations cross-session** (vs Long-vol VXX, XS-momentum, Donchian des autres sessions) = **à calculer au merge** (je ne touche pas leurs dossiers).

**Verdict sleeve : C1 = CANDIDAT OUI (conviction modérée).** Skew+ ✅, décorrélé du beta (corr 0,11) ✅,
cost-immune ✅, positif 6/7 ans dont 2022 ✅. Réserves : **SR net modeste (~0,6)**, **N=51 (faible puissance)**,
**décay récent** (2025/26 ≈ 0), et beta sur les 7 jours d'événement. → bon profil de *complément* (rare,
décorrélé, skew+), pas un moteur ; à fusionner avec d'autres sleeves événementiels/décorrélés, pas seul.

### Fiche survivant final
| Métrique | C1 Pré-FOMC |
|---|---|
| skew | +0,13 (fenêtre 2pm) / +0,88 (pré-jour complet) |
| SR net (≈) | ~0,6 (7 évts/an, per-évt 0,28 × √7, net coût) |
| mean / évt | +34 bps (net ~+29) |
| corr long-equity | **+0,11** (décorrélé) |
| forme | hit 59 %, top-5 % = 19 % du P&L (broad, pas lottery) |
| statut archive | dans la sweep ~1100 = « beta faible, pas standalone-passer » ; ici re-cadré **sleeve décorrélé** |

---

## Candidats-leçons (NOMMÉS)
> **LESSON-CANDIDATE: event-premia-are-cost-immune** — un edge par-événement de dizaines de bps (pré-FOMC
> +34/évt) dwarfe les coûts ; pour les stratégies événementielles la contrainte liante n'est PAS le coût
> (L33) mais la **puissance statistique (N faible)** et le **décay**. Profil skew+ et décorrélé (tire ~7×/an)
> → bon sleeve de portefeuille même à SR modeste.

> **LESSON-CANDIDATE: portfolio-sleeve-lens ≠ challenge-passing-lens** — un edge classé « trop faible pour
> battre la barrière FTMO » (SR≤0,34, beta) par l'archive peut rester un **sleeve décorrélé skew+ valable**
> sous le critère L7. Re-évaluer les edges archivés « faibles » sous l'angle portefeuille avant de jeter.

## Synthèse session_3
5 candidats → **1 survivant** (Pré-FOMC, sleeve-candidat conviction modérée). 4 tués proprement (no-edge
C3/C4 ; mauvais-profil-skew C5/C4-inconditionnel ; pas de data + archive C2). Négatifs = livrables.
Code repro : `code/skew_phase1.py`, `code/skew_phase2_fomc.py`.

---

# BATCH 2 — Flux & contraintes mécaniques (skew via dislocation forcée)
*MESURÉ (VM fraîche). Phase-1 : edge brut + **skew à l'horizon de DÉTENTION** (par-trade, pas daily) + **délai+1**
dès la phase 1 (L26). Signaux nus (L10). Périmètre session_3 ; pas de merge (géré ailleurs).*

## Phase 0 — Faisabilité — 2 kills nets (sans calcul, actés)
| # | Candidat | Verdict |
|---|---|---|
| B2 | **Index reconstitution (Russell/S&P)** | ❌ **NON-APPLICABLE** : l'effet est sur les *actions* ajoutées/retirées, l'indice rebalancé est net ≈0 ; pas de dates recon ; érodé par l'anticipation. Sur CFD d'indice = négligeable. |
| B4 | **ETF NAV premium/discount arb** | ❌ **NON-FAISABLE** : besoin de NAV intraday (absente) + ETF non-tradeables FTMO. |

## Phase 1 — edge brut MESURÉ (panels macro_etf/factor)
| # | Candidat (réf.) | Signal nu | n | mean | t | skew | Verdict |
|---|---|---|---:|---:|---:|---:|:--:|
| **B1a** | **Month-end bond rally** « dash for cash » (Etula 2020) | long TLT, 3 derniers jours du mois (daily) | 483 | +11,3 bps | **+3,18** | **+0,29** | ✅ |
| B1b | rebalance LS eq-bond | −sign(SPY−TLT mois)×spread 3 derniers j | 161 | −22,4 | −1,44 | −0,78 | ❌ **wrong-signed** |
| B3 | Window dressing fin de Q | SPY 3 derniers j de Mar/Jun/Sep/Dec | 159 | +3,0 | +0,40 | −0,21 | ❌ no-edge |
| B3' | réversion début Q | SPY 3 premiers j du Q suivant | 161 | +7,9 | +0,96 | −1,12 | ❌ |
| B5 | TOM multi-actifs | fenêtre TOM (dernier+3 premiers) | 643 | SPY +4,1/t1,0 · **TLT −0,7/t−0,17** · IEF +1,1/t0,6 · DBC −3,6/t−0,8 · GLD +6,0/t1,3 | −0,0 à −1,3 | ❌ **null toutes classes** |

### B1 — survivant — mesuré à l'HORIZON DE DÉTENTION + délai+1 (TLT 2002-2026, n=269 mois)
| Version (le « trade » = long bonds N derniers jours) | mean/trade | t | **skew (horizon)** | hit |
|---|---:|---:|---:|---:|
| hold 3 j (dend 3,2,1), no-delay | **+37,5 bps** | **+4,65** | −0,19 | 63 % |
| **délai+1** (entrée 1 j plus tard, hold 2 j) | +30,6 bps | **+4,45** | **+0,51** | 61 % |
| dernier jour seul (dend 1) | +17,7 bps | +3,43 | +0,27 | 61 % |

- **Robuste au délai+1** : l'edge survit à une entrée retardée d'1 jour (t=4,45) → pas un artefact de fill/single-print (L26 OK). Le skew-horizon est ≈neutre-à-positif (−0,19 strict 3 j, **+0,51** en délai+1, +0,27 dernier jour) — pas un profil tail-loser.
- **Cost-immune** : net +35,5 @2bps, +33,5 @4bps, **+31,5 @6bps** — l'edge en dizaines de bps dwarfe le coût (même logique que pré-FOMC).
- **corr(sleeve, long-equity daily) = −0,03** → décorrélé du beta (mieux que pré-FOMC +0,11).
- **Mécanique cohérente** : la demande Treasury « dash for cash » culmine **à** la fin du mois (3 derniers jours, +37,5 bps) puis **se renverse au début du mois suivant** → c'est pourquoi la fenêtre **TOM (B5) est nulle** (dominée par le début de mois) alors que les 3 derniers jours sont à t=4,65. Trade = long bonds 3 derniers jours, **sortie au month-end** (pas de hold à travers).
- **⚠ Réserve faisabilité FTMO (à trancher en Phase 2)** : l'edge est sur le complexe Treasury (TLT). À **mesurer pas supposer** (L33) : FTMO propose-t-il un instrument obligataire tradeable (bond CFD/futures) ? Si oui → sleeve implémentable ; sinon → sleeve de **portefeuille** valable (L7) mais hors-challenge.

## Candidats-leçons (NOMMÉS)
> **LESSON-CANDIDATE: month-end-edge-lives-in-the-bond-leg** — l'effet month-end robuste n'est PAS le rebalance-fade
> equity (wrong-signed, −22 bps : la divergence eq-bond CONTINUE, ne reverse pas) mais la **demande obligataire**
> « dash for cash » (TLT 3 derniers jours, t=4,65 sur 2002-2026, cost-immune, décorrélé −0,03). Tester la jambe bond,
> pas la jambe equity-rebalance.

> **LESSON-CANDIDATE: turn-of-month-is-fully-arbitraged-but-month-end-bond-is-not** — le TOM (dernier+3 premiers j)
> est NULL dans TOUTES les classes liquides : equity (archive), bonds (TLT t=−0,17), commo (DBC t=−0,76), gold
> (GLD t=1,3 / skew −1,3). À NE PAS confondre avec le **month-end-3-day bond rally** (qui survit, t=4,65) : le TOM
> moyenne ce rally de fin de mois avec sa réversion de début de mois → ≈0. Le « month-end » (3 derniers jours) ≠
> le « turn-of-month » (englobe le début du mois suivant).

## Synthèse batch 2
5 candidats → **1 survivant : B1 dash-for-cash bond month-end** — fort (t=4,65, cost-immune, décorrélé −0,03,
robuste délai+1, skew-horizon ≈0/+), **sous réserve de tradeabilité FTMO d'un instrument Treasury (Phase 2)**.
4 tués proprement : B2/B4 faisabilité, B3 no-edge, B5 **TOM null toutes classes** (la question ouverte « bonds ? »
est tranchée : non). Négatifs = livrables.
Code : `code/skew_phase1b.py` (phase 1) + `code/skew_phase1b_B1holding.py` (horizon + délai+1).

---

# PHASE 2 — B1 (month-end bond rally « dash for cash »)
*Le Test #1 (tradeabilité FTMO) décide la catégorie. Tout mesuré, pas supposé (L33). Code : `code/skew_phase2_B1.py`.*

## Test #1 — TRADEABILITÉ FTMO : ❌ **NON** → reclassé sleeve de portefeuille (L7)
Sources FTMO (FAQ « which instruments », MAJ 2026-05-27 ; revues 2026) : univers = **Forex, Indices, Commodities,
Stocks (23 actions large-cap US en CFD : AAPL, TSLA…), Crypto**. Explicitement : **« no access to ETFs, bonds,
options, or spot markets »** ; futures non offerts. → **Aucun instrument Treasury tradeable sur FTMO** : pas de
bond CFD, pas de ZN/ZB futures, pas de TLT/IEF (ETF exclus).
→ **B1 N'EST PAS un trade de challenge FTMO.** Par la règle de décision : reclassé **sleeve de portefeuille perso
(L7)**, implémentable **hors-FTMO** (TLT/IEF ETF ou futures Treasury ZN/ZB, compte courtier classique). Reste un
excellent sleeve — simplement hors-périmètre challenge. Le flux est bond-spécifique → **pas de proxy FTMO fidèle**
(le tenter via FX/indices ré-introduirait du beta).

## Test #3 — RÉGIME DE TAUX (crucial) : ✅ survit le flip
| Régime | mean/trade | t (brut) | demeaned-within-régime |
|---|---:|---:|---:|
| 2002-2021 (bull bond, baisse taux) | +39,8 bps | +4,43 | +32,2 (t 3,58) |
| **2022-2026 (bear bond, hausse taux)** | +28,1 bps | +1,53 | **+38,9 (t 2,12)** |

→ L'edge **survit la hausse des taux post-2022** ; demeaned-within, il est **plus fort** dans le régime bear
(+38,9 vs +32,2). Ce **n'est PAS** 20 ans de bull-bond séculaire.

## Test #4 — FLOW vs BETA (two-sided) : ✅ vrai flux, pas du beta
- baseline (drift séculaire = mean daily ×3, ce que donne le beta long sur 3 jours quelconques) = **+4,0 bps** ;
  month-end 3-day = +37,5 → **excès +33,5 bps** = le flux réel (9× le drift).
- **DEMEANED** (drift retiré entièrement) = +33,5 bps, **t=4,16** → robuste sans aucune contribution beta.
- **23/23 années positives** (2004-2026, de +2 à +99 bps) → pas porté par quelques années.

## Test #2 — COÛT sur 3 nuits : breakeven **12,5 bps/nuit**
Net +34,5 @1bps/nuit · +31,5 @2 · +22,5 @5 · +13,5 @8 → survit à tout swap réaliste. *(Moot pour FTMO car
non-tradeable ; pertinent pour l'implémentation réelle ETF/futures, où le carry réel ≪ 12,5 bps/nuit.)*

## Verdict B1
**Meilleur edge de tout l'exercice — mais sleeve de portefeuille (L7), PAS un trade FTMO.** Vrai flux « dash for
cash » : holding t=4,65, **23/23 ans positifs**, **regime-proof** (survit 2022+, demeaned plus fort), **flow-not-beta**
(excès +33,5 vs baseline +4, demeaned t=4,16), cost-immune (breakeven 12,5 bps/nuit), décorrélé equity (−0,03),
robuste délai+1. **Unique barrière = l'univers FTMO sans obligations.** → garder pour portefeuille perso
(TLT/IEF/ZN-ZB) ; pour le **portefeuille FTMO-implémentable**, le survivant reste **C1 Pré-FOMC** (sur NQ/indices, lui tradeable).

> **LESSON-CANDIDATE: venue-instrument-availability-is-gate-0** — pour un mandat contraint par le lieu (FTMO),
> la **tradeabilité de l'instrument sur le lieu** est un gate-0 à vérifier AVANT le travail statistique profond.
> B1 = cas d'école : stats parfaites (t=4,65, 23/23 ans, regime-proof, flow-not-beta) mais **FTMO n'a pas d'obligations**
> → zéro valeur pour le challenge, grande valeur pour un portefeuille perso. Confirme concrètement
> `portfolio-sleeve-lens ≠ challenge-passing-lens` (batch 1) : ici la lentille qui tranche est l'**instrument**, pas la stat.

---

# BATCH 3 — Effets datés sur instruments FTMO-tradeables (gate-0 tradeabilité intégré)
*Gate-0 (tradeabilité FTMO) satisfait par construction (indices/FX/commodities/crypto). Phase 1 : edge brut,
skew à l'horizon de détention, reconcile archive (L31). Code : `code/skew_phase1c.py` (daily), `code/skew_phase1d.py`
(intraday). Données : ftmo_close (indices 2000-26), EURUSD M1 UTC (2020-26), BTC 8h + funding (2023-26).*

## Phase 1 — résultats mesurés
| # | Candidat (réf.) | Signal nu | n | mean | t | skew | Verdict |
|---|---|---|---:|---:|---:|---:|:--:|
| B3-1 | Pré-OPEX index drift (Stoll-Whaley / gamma) | OPEX-week US500 **nu** | 316 | +10,1 | +0,72 | −1,06 | ❌ (cf. batch1 C5) |
| B3-1' | …**conditionné prior-trend UP** (proxy gamma) | OPEX-week \| tendance↑ | 191 | +35,3 | **+2,89** | −0,04 | ⚠ **FLAG** (confound) |
| B3-2 | TOM conditionné perf (rebond sous-perf) | TS −sign(mois préc.)×first3 | 316 | −2,6 | −0,23 | +0,12 | ❌ rebond nul |
| B3-2' | …version cross-sectionnelle | XS long losers − winners | 316 | +8,8 | +0,76 | −0,24 | ❌ |
| B3-3 | FX month-end London 4pm fix | EURUSD 15→16h UTC, month-end | 76 | −1,6 | −1,14 | +0,35 | ❌ arbitré |
| B3-4 | Commodity seasonality (archive keeper) | proxy signe-saisonnier naïf | 228 | −12,5 | −0,52 | −0,07 | ⤳ keeper (cite) |
| B3-5 | Crypto funding-reset timing | −sign(funding)×next-8h | 3266 | −0,3 | −0,12 | +0,10 | ❌ |
| B3-5' | (réf carry, archive H31) | sign(funding)×next-8h | 3266 | +0,3 | +0,12 | −0,10 | ❌ confirme archive |

## B3-1 — le test de confound qui décide (OPEX vs momentum)
La cellule « OPEX-week | prior-trend UP » (+35,3 bps, t=2,89) **passe le t mais échoue le skew (−0,04)**.
Test décisif : dans le **même régime up-trend**, OPEX-week = +35,3 (t2,90) vs **semaine normale = +7,9 (t1,01)**
→ excès OPEX-spécifique **+27,4 bps mais t=1,89 (sous 2)**. Donc ~60 % OPEX-spécifique / **~40 % momentum déguisé**
(L25). Le proxy de tendance **ne sépare pas gamma de momentum**. → **FLAGGÉ, pas avancé** : l'angle gamma exige
de la vraie data dealer-gamma (OI/GEX) absente ici. Lead réel mais non-testable proprement.

## B3-4 — commodity seasonality (archive keeper, NON re-prouvé)
Archive : Sharpe 0,30, OOS-stable (seul survivant de cet arc). Mon proxy naïf (signe de la moyenne du même mois
calendaire, expanding) = **flat (t=−0,52)** → **l'edge archive est method-specific, PAS de la saisonnalité naïve**
(je ne le re-dérive pas, périmètre). Datum portefeuille frais : **corr(sleeve naïf, SPY) = +0,04** (décorrélé).
Pour la caractérisation skew+ propre → tirer la série de rendements du sleeve archive **au merge** (cross-session,
hors session_3).

## Reconcile archive (L31)
OPEX nu = déjà mort (batch1 C5 quad-witching) ✓ ; TOM-equity = mort (archive + batch2 B5) ✓ ; funding carry =
H31 RESEARCH_FAIL, **confirmé** (carry t=0,12) ✓ ; commodity seasonality = **keeper**, cité non re-prouvé ✓.

## Verdict batch 3 : 0 nouveau survivant propre (négatif rigoureux = livrable)
B3-2/B3-3/B3-5 tués (no-edge) ; B3-1 **flaggé** (momentum-confound + skew-flat, besoin GEX) ; B3-4 = keeper
archive (décorrélé, cité). Aucune nouvelle pièce skew+/décorrélée ajoutée au book FTMO-implémentable.

## Candidats-leçons (NOMMÉS)
> **LESSON-CANDIDATE: gamma-conditioning-needs-GEX-not-a-trend-proxy** — conditionner l'OPEX au « gamma dealer »
> via un proxy de tendance **confond gamma et momentum** : l'excès OPEX-spécifique existe (+27 bps) mais t=1,89, et
> ~40 % du signal est du pur momentum. Sans data OI/GEX, l'angle dealer-positioning n'est pas testable — ne pas le
> compter comme edge.

> **LESSON-CANDIDATE: dated-microstructure-flows-die-post-arbitrage** — les flux datés micro-structure largement
> publiés (FX London-fix post-scandale 2013 ; crypto funding-reset) sont **nuls sur data récente** (FX 2020+ t≈−1 ;
> funding 2023+ t≈0,1). À distinguer des **event-premia** (FOMC) et **flux contraints** (dash-for-cash bond) qui,
> eux, survivent : la frontière n'est pas « daté » vs « non-daté » mais **contrainte mécanique persistante** vs
> **flux publié arbitrable**.

---

# BATCH 4 — Combos multi-indicateurs (mécanismes distincts)
*Versions canoniques SIMPLES (L10, params standards : MA50/200, RSI14, BB20/2, mom20/60, ER20 ; aucun sweep),
**TWO-SIDED** (L25), **délai+1 intégré** (pos décidée en t-1, gagne t). Stratégies daily → barre = **Sharpe annualisé
+ skew** (le t est trivialement grand à n élevé). US500 OHLC 2000-26 ; SPY (volume réel) 2015+. Code : `code/skew_phase1e.py`.*

## Phase 1 — le filtre ajoute-t-il sur la base nue ?
| # | Combo | Candidat (filtré) | Référence (nue) | Verdict |
|---|---|---|---|:--:|
| B4-1 | Trend+MR switch régime (ER) | switch = **Sh 0,04** | trend\|trending **Sh −0,02**, MR\|chop 0,07 | ❌ mécanisme rejeté |
| B4-2 | Breakout + volume (SPY) | vol-confirmé **Sh −0,36** (skew −8,1) | breakout nu −0,15 | ❌ volume EMPIRE |
| B4-3 | Double-TF momentum | aligné **Sh 0,14** | daily seul 0,03 | ❌ faible |
| B4-4 | MR filtrée MA200 | filtré **Sh 0,37** | **MR inconditionnel Sh 0,51** (skew +1,46) | ❌ filtre RÉDUIT |
| B4-5 | Bollinger + MA200 | filtré **Sh 0,37 / skew −0,78** | **BB nu Sh 0,46 / skew +3,29** | ❌ filtre RÉDUIT + flippe skew |

## Détail mécanismes
- **B4-1** : matrice 2×2 → le trend ne gagne PAS en régime « trending » (Sh −0,02) ; c'est la **MR** qui a la meilleure
  cellule (MR\|trending Sh 0,38). L'Efficiency-Ratio **ne sépare pas** trend-favorable de MR-favorable → le switch est flat.
- **B4-2** : les breakouts d'indice sont fadés (indice = MR daily) ; le pic de volume = climax/retournement → confirme à
  contre-sens (Sh −0,36, skew −8,1). + **gate-0** : FTMO CFD n'ont pas de vrai volume (tick-volume seulement).
- **B4-4 / B4-5** : le filtre MA200 ne fait que **réduire l'exposition** (24 %→3 %, 9 %→3 %) et **baisser le Sharpe** ;
  pour B4-5 il **flippe même le skew** de +3,29 (BB nu) à −0,78. La jambe short-en-downtrend est faible (Sh 0,11) → asymétrie.

## Verdict batch 4 : 0 survivant parmi les candidats (négatif rigoureux)
Chaque « ajout conceptuel » a **dégradé** le signal de base — le plus simple gagne (L10 vindiqué). Aucune nouvelle
pièce skew+/décorrélée ajoutée. **Note incidente** (≠ candidat) : la MR court-terme **nue** sur indice (RSI/Bollinger)
a skew+ (1,46 / 3,29) et Sharpe ~0,5, MAIS c'est la *référence*, **beta-suspecte** (acheter les dips equity = beta long
partiel) → exigerait la décompo flow-vs-beta (cf. B1) avant de compter ; hors-scope batch 4.

## Reconcile archive (L31)
Trend/momentum/breakout : déjà couverts en profondeur dans l'arc ORB/trend (cité ; **je ne touche pas `trend_research/`**).
MR-court-terme-indice : famille #1 de la liste d'origine (mean-reversion intraday), déjà explorée → ici seulement
référence. Aucun re-prouvé.

## Candidats-leçons (NOMMÉS)
> **LESSON-CANDIDATE: layering-filters-degrades-not-improves** — sur 5 combos classiques, ajouter le filtre
> (régime / volume / MA200) a **réduit le Sharpe** et souvent **flippé le skew** vs le signal nu. « Plus d'indicateurs »
> = sur-ajustement déguisé ; la version nue est le bon prior (L10). Un filtre ne se garde que s'il **bat** la base nue
> sur Sharpe ET skew — ce qui n'est arrivé dans aucun des 5 cas.

> **LESSON-CANDIDATE: regime-switch-needs-a-validated-detector** — un switch trend/MR ne vaut que si le détecteur de
> régime sépare réellement les régimes sur la matrice 2×2 AVANT de construire le sleeve. Ici l'Efficiency-Ratio a
> échoué (la MR a gagné dans le régime « trending ») → switch flat. Valider le détecteur d'abord, pas après.
