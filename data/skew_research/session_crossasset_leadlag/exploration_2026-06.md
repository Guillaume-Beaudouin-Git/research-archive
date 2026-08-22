# Skew research — session_crossasset_leadlag (candidats 1-5 : cross-asset & lead-lag)
### Exploration 2026-06. Objectif : sleeves skew+ décorrélés pour portefeuille survie-propfirm (L7).
*Esprit : edge d'abord, barrières ensuite. Phase 1 généreuse. Skew négatif = drapeau, pas kill. Candidats-leçons NOMMÉS.*
*Skew mesuré à l'**HORIZON DE DÉTENTION** (hebdo/mensuel), pas daily — leçon J1 (skew quotidien = bruit micro-structure).*

---

## PHASE 1 — edge brut (sans coût, généreux). Gate : t>2 ET skew(horizon) ≥ 0.

| # | candidat | signal (spec existante, T-1→T) | horizon | mean/j | hit | skew_d | **skew_horiz** | t | SR | corrEQ | gate |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | lead-lag cuivre→SP500 | sign(cuivre 5j mom)·shift1 × SP500 ret | jour/sem | −0,47bp | 0,393 | −0,37 | M **−0,39** | −0,41 | −0,07 | −0,18 | ✗ dead |
| 2 | carry FX G10 hedgé-vol | *(non re-mesuré)* | — | — | — | — | — | — | — | — | ✗ **archive** |
| 3 | credit momentum HYG/IEF | sign(3m mom HY/UST)·shift1 × ratio ret | mois | −0,00bp | 0,496 | −0,45 | M **+0,62** (W +1,26) | −0,00 | −0,00 | **−0,36** | ✗ no edge |
| 4 | oil term-struct timé *(carry-dir)* | sign(basis)·shift2 × oil ret | mois | −9,9bp | 0,486 | −0,46 | M −0,29 | **−2,62** | −0,59 | −0,06 | ✗ **NÉG signif** |
| 4b | oil *(inverse anti-carry)* | −sign(basis) × oil ret | mois | +9,9bp | 0,510 | +0,46 | M **+2,39** | **+2,62** | +0,59 | +0,06 | ⚠ sign-flip |
| 5 | gold / real-rates | sign(TIP 1m mom)·shift1 × gold ret | mois | +0,81bp | 0,504 | −0,51 | M **−0,43** | +0,53 | +0,11 | −0,01 | ✗ faible+régime |

**Survivants Phase 1 : AUCUN.** Aucun candidat ne passe `t>2 ET skew(horizon)≥0` dans sa direction pré-spécifiée.

### Détail / robustesse (pourquoi chaque échec est propre)

**#1 — lead-lag cuivre→actions : arbitré à TOUS les horizons (L31 confirmé empiriquement).**
Balayage horizon (cuivre Nj-mom → SP500 lendemain) : t = −1,54 (1j) / +0,20 (3j) / −0,41 (5j) / −1,04 (10j) / +0,33 (20j). Hebdo (4 sem mom → semaine suivante) : t=−0,59, SR=−0,25. **Bruit autour de zéro, jamais significatif.** Le délai+1 sur la base remonte à SR+0,14 / skewM+2,04 mais t=0,79 → bruit, pas edge. « Dr Copper » ne mène plus les actions à l'échelle tradable.

**#4 — oil term-structure timé : L32 RECONFIRMÉ, l'inverse est un sign-flip mono-épisode.**
- Direction carry-correcte (long backwardation / short contango) = **significativement NÉGATIVE** : t=−2,62, SR=−0,59, délai+1 t=−2,39. Le timing two-sided ne rescape PAS le verdict L32 (carry commodity one-sided mort) — il fait *pire* que neutre, il perd.
- L'inverse (anti-carry) paie : t=+2,62, SR=+0,59, skewM+2,39, corr long-oil seulement +0,15 (pas un pur artefact de trend), split-half SR +0,69/+0,51 (stable). **MAIS** c'est (a) un **sign-flip post-hoc** de la direction pré-enregistrée = le piège L33 ; (b) son skew+ est **concentré sur un unique épisode** : skewM 2ᵉ moitié +2,81 vs +0,69 1ʳᵉ, l'année 2020 (oil négatif) = +2,03 du PnL cumulé. Un skew+ porté par un cygne-noir-favorable non répétable n'est PAS un profil convexe fiable pour la survie propfirm. **Non promu.**

**#3 — credit momentum : la FORME recherchée, mais zéro edge.**
t=−0,00, SR=−0,00 : pas d'alpha. Pourtant skew horizon **positif** (W+1,26, M+0,62) et **corrEQ −0,36** (décorrélé, voire négatif — le « beta risk-off caché » ne se matérialise PAS dans cette spec long-short HY-vs-UST). C'est exactement le profil de sleeve voulu… sans rien à récolter. Forme ≠ edge.

**#5 — gold / real-rates : faible + skew− + régime-instable (piège confirmé).**
t=+0,53 (insignifiant), skew horizon −0,43. Split-half SR **−0,05 / +0,31** → signe instable entre régimes (exactement le piège annoncé). corrEQ −0,01 (joliment décorrélé) mais sans edge ni bon skew. La relation or↔taux-réels est trop contemporaine/instable pour un signal momentum tradable à cette spec.

**#2 — carry FX G10 hedgé-vol : mort à l'archive, cité non re-mesuré.**
G10 carry FX-1→FX-4 mort post-GFC (IC −0,028 sur 2013-23) ; **G1 « carry conditionnel VXY-vol » CLOSED** (L11 3× gate fail). L'angle « hedge-vol » ≠ « conditionnement » mais le carry nu a un skew négatif structurel (carry-crash) que le hedge ne transforme pas en edge décorrélé positif. Pas de re-preuve (discipline archive).

## PHASE 2 / 3 — sans objet pour ce batch
Zéro survivant Phase 1 → rien à confronter aux barrières ni à insérer dans la matrice de corrélation. **Le batch cross-asset & lead-lag ne produit aucun sleeve skew+ complémentaire.**

## VERDICT FINAL (session_crossasset_leadlag)
**Aucun sleeve retenu.** Les candidats « décorrélation native » sont tous décorrélés des actions (corrEQ ∈ [−0,36 ; +0,06]) **mais aucun n'a d'edge brut exploitable dans la bonne direction** :
- arbitré à tout horizon (#1 cuivre),
- carry-trap dont la direction correcte perd et dont l'inverse est un sign-flip mono-épisode (#4 oil ; #2 FX par archive),
- régime-instable (#5 or/taux),
- bonne forme mais zéro alpha (#3 crédit).

→ **Contraste session_vol_tail** (qui avait sorti #5-MR reversal, skew +0,71) : ici la décorrélation est gratuite mais creuse. **La décorrélation est nécessaire, pas suffisante — sans edge brut, il n'y a rien à décorréler dans le book.**

## Candidats-leçons (NOMMÉS, pas numérotés — numéro tranché au merge par le mainteneur)
- **« Lead-lag publié = arbitré à tout horizon jusqu'à preuve OOS post-publication »** — cuivre→SP500 mort sur 1/3/5/10/20j ET hebdo (t∈[−1,5 ; +0,3]). L31 confirmé empiriquement, pas seulement présumé.
- **« Carry commodity timé two-sided ne rescape pas L32 »** — la direction carry-correcte (long backwardation) est *significativement négative* (t=−2,62) ; seul l'anti-carry paie, et c'est un sign-flip (L33) dont le skew+ tient à un unique épisode (2020 oil-négatif). Le timing ne ressuscite pas le carry commodity.
- **« Skew+ à l'horizon SANS edge ≠ sleeve »** — credit momentum HYG/IEF a la forme exacte recherchée (skewM +0,62, corrEQ −0,36) mais t≈0. Distinguer la FORME (skew, corrélation) de l'EDGE (t, SR) : la forme sans alpha n'est pas allouable.
- **« Décorrélation native ≠ edge »** — tout le batch est décorrélé equity (corrEQ ≤ +0,06) et pourtant 0 edge tradable. La décorrélation est un filtre de sélection, pas une source de rendement.
- *(rappel transverse)* **« Mesurer le skew à l'horizon de détention »** se confirme utile ici : #3 daily −0,45 → mensuel +0,62 ; #4-inv daily +0,46 → mensuel +2,39 (mais mono-épisode). Le signe quotidien trompe ; le signe à l'horizon est le vrai profil — encore faut-il un edge derrière.

---
*session_crossasset_leadlag, candidats 1-5. Données : cache local (xs_universe : COPPER/SP500/GOLD ; commod_daily : USOIL ; basis_oil) + Yahoo (HYG, IEF, TIP — réseau revenu ce run). Tout backtest, 0 jour live. Réconcilié archive (#2 FX, #4 L32 — pas de re-preuve). Phase 1 seulement. Rien figé, rien mergé. Écrit uniquement dans ce périmètre ; non touché aux autres sessions ni overnight_research/.*
