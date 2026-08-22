# Commodity deep-dive — session_E3 (HOME du programme commodity long-terme)
### Phase 1 + MC book. Mandat : moteur TSMOM mort (F), intraday-flat vide (G) → les commodities sont l'endroit le plus plausible d'une stratégie FTMO déployable.
*L37 : swap-long POSITIF = backwardation = carry-aligné LONG ; NÉGATIF = contango = carry-aligné SHORT. Swaps MESURÉS fournis.*
*Framework par candidat : mécanisme physique PRESPEC (L10), GATE-0 réconciliation série/swap, excess vs DTB3 + HAC lag-6, NET-CFD swap mesuré direction carry, L25 beta-flag, OOS incl 2020, DSR déflaté, corr-précieux.*

> **Honnêteté > optimisme** (mandat). Ce livrable tue la thèse moteur-oil et redimensionne le book à un grinder lent.

---

## GATE-0 — réconciliation série vs swap : un piège majeur attrapé sur l'oil
**`commod_daily` USOIL min avril-2020 = −$37,6 → c'est le FUTURE WTI front-month** (le contrat mai-2020 a coté −$37,63), **PAS le CFD cash FTMO** (jamais passé négatif, plancher ~$6-10). Conséquences :
1. **La série de backtest ≠ l'instrument tradeable** au moment critique (2020) → l'OOS-2020 oil est contaminé par un artefact future.
2. **Double-compte/mis-sign du carry** : le swap mesuré +36,5 est statique (+20%/an backwardation) ; or en 2020 l'oil était en contango massif (carry NÉGATIF). Appliquer +167bp/mois à travers 2020 surcompte.
→ **Oil [C] est GATE-0-bloqué sur cette donnée.** Tout net oil « +438/+460bp » de la run brute est un artefact (carry statique × 2020 contaminé). Verdict propre exige le CFD cash réel + carry time-varying. *(Les autres séries — métaux, coffee, grains — ne sont pas passées négatives ; drift +3-5%/an spot-like ; net-CFD = price+swap OK, pas de double-compte.)*

**Calibration swap** : oil +36,5 pts ancré à +20%/an (donné) ; autres mis à l'échelle (coffee +0,9%/an, soy-short +3,4%, cocoa-short +1,4%, wheat-short +1,8%). Incertaine → sensibilité notée.

## Phase 1 — seasonals carry-alignés (mécanisme physique PRESPEC, direction carry)

| candidat | direction (carry) | gross (t) | **NET mesuré (t)** | OOS pre/post/2020 | corr-préc | verdict |
|---|---|---|---|---|---:|---|
| **COFFEE long-Jul** (gel Brésil) | long (carry +0,9%) | +142bp (1,55) | **+179bp (1,96)** | +98/+389/**+1889** | −0,00 | ✅ **revit** (fragile) |
| **PRECIOUS long-Jan** (Ag/Au/Pt) | long | +429bp (3,41) | **+355bp (2,82)** | +576/+254/+81 | +0,59 | ✅ **robuste** |
| SILVER long-Aug / Sep | long | +106/−153 | +33 / −227 | — | +0,45 | ❌ Janvier seul |
| SOYBEAN short-Oct (glut) | short (carry +3,4%) | −264bp (−3,82) | −207bp (−2,99) | — | +0,00 | ❌ mal-timé (soy monte en Oct) |
| COCOA short-Dec (harvest) | short | −275bp (−1,10) | −235bp | — | +0,00 | ❌ mal-timé |
| WHEAT short-Jul (harvest) | short | −347bp (−1,17) | −302bp | — | +0,00 | ❌ mal-timé |
| WHEAT long-May (météo) | long **vs carry** | +202bp (1,42) | +137bp (0,96) | +316/+81/−170 | −0,00 | ❌ combat le contango (−95bp) |
| OIL long (driving+carry) | long (carry +20%) | — | **GATE-0 bloqué** | — | — | ❌ futures≠CFD + trop violent |

**Corrections E2 confirmées par L37** : coffee **revit** (swap mesuré ≈0 vs mon −5bp/nuit E2 faux → ton intuition juste). Mais les shorts carry-alignés (soybean/cocoa/wheat) **meurent mal-timés** : la baisse de glut n'est pas dans le mois que j'ai pré-spécifié (soy *monte* en octobre). Et wheat-long-May **combat son propre carry** (contango −95bp). DSR (déflaté ~9 candidats) : précieux-Jan t2,82 survit ; **coffee t1,96 borderline** + edge concentré sur le gel 2020 (pre-2020 seulement +98bp) → **fragile**.

## [B]/[C] — le moteur carry-oil : MORT pour FTMO
Le carry-sign **a flippé en contango fin-fév/mars 2020** (basis +0,023 fév → −0,040 mars → −0,78 avr) et le filtre **est sorti (75% flat en 2020)** — **le concept de filtre-régime marche directionnellement**. MAIS :
- **[B]-oil carry-sign (best-effort, 2020 cappé CFD-réaliste) : SR −0,05, MaxDD −93%, 2020 −65%.** Le basis est mensuel/laggé → encore long dans la chute fév-mars ; le filtre sort trop tard.
- **L'oil a une MaxDD −90%+ incompatible avec les caps FTMO** (−5%/jour, −10% total) à toute taille utile — il **bust** par construction, filtre ou pas.
- Le « +25%/an » de la version naïve = artefact du **carry statique +20% appliqué même en contango** (le carry réel était négatif en 2020).

→ **Make-or-break oil = BUST, pas survie bornée.** Le carry L37 est réel (backwardation paie le long), mais **l'oil est un véhicule trop violent pour la structure de barrière FTMO**. [B] (basket piloté carry-sign) et [C] (oil carry-harvest) **ne sont PAS le moteur** : data-bloqués ET, en best-effort, busting. *(À rouvrir seulement avec le CFD cash réel + carry intraday/hebdo — mais la MaxDD −90% rend l'issue très improbable.)*

## STOP-POINT 2 — MC book commodity (la question de structure)
Book = survivants propres : **précieux-Janvier (robuste) + coffee-Juillet (fragile)**, flat hors-fenêtres. 2 fenêtres/an (~39 j actifs). Sleeve vol-target 10% : +1,62%/an actif ±2,9%, worst day −3,5%.

| levier | p(pass) | breach −5%/j | #ans médian | vs E2 (1 fenêtre) |
|---:|---:|---:|---:|---|
| L=1 | 95,9% | 0,0% | **5** | E2 : 8 ans |
| L=2 | 85,7% | 0,9% | **2** | — |
| L=3 | 63,1% | 32,5% | 1 | E2 : — |
| L=4 | 58,6% | 37,0% | 1 | E2 : 69,5%/25% |

**La densité aide mais ne dissout PAS la sparsité.** La 2e fenêtre (coffee-Jul) fait passer L=1 de 8→5 ans, et ouvre un cell L=2 / **2 ans / 85,7% / <1% breach** — le meilleur cas honnête. Mais : (a) 2 ans reste lent pour un standalone, (b) ce cell **dépend de coffee-Jul, fragile** (sans lui = profil E2 lent), (c) L≥3 (1 an) = 32%+ breach (bust). **Pas de moteur rapide** : entre L=1-2 (lent, 2-5 ans) et L≥3 (bust), il n'y a pas de standalone rapide et robuste.

## VERDICT (STOP-POINTS 1 & 2)
**Existe-t-il un book commodity FTMO-viable ?** — **Oui, mais modeste : un grinder lent low-levier (L=1-2, 2-5 ans, sans limite de temps), pas un moteur.** Survivants propres = précieux-Janvier (robuste) + coffee-Juillet (fragile, gel-2020-dépendant). La densité de calendrier espérée (Jan/mai/été/automne/Aug-Sep) **ne se matérialise pas** : grains mal-timés/morts, oil bloqué+violent, Aug-Sep faibles.

**L'oil/[B] est-il le moteur ?** — **NON, mort.** Data-bloqué (futures≠CFD) ET trop violent (MaxDD −90% ≫ cap −10%) ; le carry-sign exit-régime est trop lent (mensuel). Le carry L37 est un vrai signal mais sur un véhicule inutilisable pour FTMO.

→ **Implication** : comme E2, le commodity reste un **topping décorrélé skew+ low-levier** (précieux-Jan ± coffee-Jul) à poser sur une structure (A) intraday-flat, **pas** le moteur déployable espéré. La piste commodity-moteur via le carry-oil est fermée par la violence de l'instrument.

## PHASES 2-3 (batchs suivants, MÊME session — à faire)
[D] trend long-only oil (carry tailwind) — **mais GATE-0 oil bloqué d'abord** : exige le CFD cash réel. [E] overlay COT/inventaire (18y CFTC) sur précieux-Jan/coffee-Jul. [F] event ag (WASDE/OPEC). Chacun PRESPEC + gates, comparé au book Phase-1 (additionnalité).

## Candidats-leçons (NOMMÉS)
- **« GATE-0 série-vs-CFD : le future WTI (négatif 2020) n'est pas le CFD cash — réconcilier avant tout net oil »** — `commod_daily` USOIL = future (−$37,6) ≠ FTMO cash ; bloque l'OOS-2020 ET risque le double-compte du carry. Vérifier le print 2020 de toute série énergie avant de la traiter comme l'instrument.
- **« Carry L37 réel mais l'oil est trop violent pour les barrières FTMO »** — MaxDD −90%+, le carry-sign mensuel sort trop tard (2020 −65% malgré 75% flat). Le carry-aligné ne sauve pas un instrument dont la vol fait sauter le cap.
- **« Carry statique × régime = surcompte »** — appliquer +20%/an de carry à travers un contango (2020) fabrique un faux +25%/an. Le carry doit être time-varying (basis-sign), pas une constante.
- **« Coffee revit avec le swap mesuré ; mon swap générique E2 était faux »** — coffee carry ≈0 (pas −5bp/nuit) → NET +179bp t1,96. Mais edge gel-2020-concentré (pre-2020 +98) → fragile. Mesurer le swap par instrument, jamais un générique de classe.
- **« Short carry-aligné ≠ short au bon mois »** — soybean/cocoa/wheat ont le bon SIGNE carry (contango→short) mais le glut-decline n'est pas dans le mois pré-spec (soy monte en Oct) ; le carry ne sauve pas un timing faux. Mécanisme = signe ET fenêtre.
- **« Densité 2-fenêtres aide mais ne fait pas un moteur »** — Jan+Jul : 8→5 ans (L1), cell L2 2 ans/<1% breach, mais L≥3 buste (32%). Sparsité atténuée, pas dissoute ; reste un grinder lent.

---
*session_E3_commodity_deepdive. Données : commod_daily (Ag/Pt/Au/oil/coffee/cocoa/soybean/wheat), basis_oil, DTB3. Swaps MESURÉS fournis, calibration oil=+20%/an (sensibilité notée). GATE-0 série/swap, HAC lag-6, DSR déflaté, MC 20k. Tout backtest, 0 jour live. Réconcilié archive (session_E précieux, session_E2 grains, session_F moteur — pas de re-preuve). Phases 2-3 à venir (même session). Rien figé, rien mergé. Écrit uniquement dans ce périmètre ; non touché aux autres sessions ni overnight_research/. Dédup vs session_E/E2 flaggé.*
