# ÉTUDE — Sizing funded dynamique sur coussin réalisé (floor statique FTMO)

**Date :** 2026-06-19 · **Worktree :** `../Algo_claude_fundedsizing` · **Branche :** `claude/funded-dynamic-sizing`
**Pré-registration :** `PREREGISTRATION.md` (committée AVANT résultats, commit `b30fed2`)
**Cadre :** RECHERCHE PURE, funded-only. Book CHALLENGE vm14 **jamais touché**. Aucun déploiement, lecture seule live.

---

## VERDICT — (b) le sizing STATIQUE vm=1.0 est déjà quasi-optimal ; le dynamique est strictement DOMINÉ

La thèse est **structurellement défaite** par le piège pré-identifié : **le daily −5% ($500 fixe) est la
barrière contraignante ; le floor max-loss −10% (ce que le coussin protège) NE MORD JAMAIS** au sizing
viable. Le levier « coussin réalisé » n'a donc rien à relâcher. Triplet funded (12 mois) :

| | extraction médiane | survie 12m | min-balance pire |
|---|--:|--:|--:|
| **B0 — static vm=1.0, retrait-tout (régime ACTUEL)** | **$671** | **98.6 %** | −11.8 % |
| meilleure variante dynamique (α=2, asym off) | $445 | 94.5 % | −11.8 % |
| static vm=2.0 (placebo agression) | $0 (médian) | 82.8 % | −14.6 % |

**Aucune des 6 variantes ne domine B0** : toutes ont une survie inférieure de 4–6 pts (disqualifiées sur
la contrainte DURE de survie) **ET** une extraction inférieure. Le régime funded actuel n'est pas à améliorer
par un sizing-coussin. *Pronostic pré-enregistré confirmé : le daily plafonne l'agression — sans survente.*

---

## Validation
Le patch `run_funded_dyn` (vm dynamique + retrait cushion-retaining + logs) avec `vm=1.0, α=0, retrait-tout`
**reproduit le `run_funded` canonique au centime** : **0 mismatch / 40 cohortes**. Le moteur de trading des
jambes est inchangé — seul le sizing/retrait est paramétré. Réutilisé read-only depuis le main dir.

## Q1 — Diagnostic baseline : QUELLE barrière mord ?
Moteur funded v2.2, cohortes mensuelles **2013-2025 (régimes morts inclus)**, vm=1.0 :

| | valeur |
|---|--:|
| Budget daily | **−$500** (5 %·INIT, fixe) |
| Perte pire-jour p50 / p5 / p1 / min | **−$8 / −$165 / −$290 / −$658** |
| Jours perdant > $400 | **0.18 %** |
| B0 survie 12m / extraction | 98.6 % / $671 |
| **Composition des busts (12m)** | **2 daily / 0 floor** |

**Lecture décisive.** À vm=1.0 le book consomme **une fraction infime** du budget daily (médiane −$8 !),
mais ses rares busts sont **DAILY (2/0)** : ce sont les jours de queue (min −$658 > −$500) qui bustent, PAS
une dérive multi-jours vers le floor. **Le floor −10 % ne mord JAMAIS** au sizing de référence → le coussin
réalisé (qui ne protège que le floor) n'a **rien à relâcher**. Il y a de la marge daily en médiane, mais
monter le sizing **multiplie les pertes des jours de queue** → plus de busts DAILY.

## Q2 — Sizing dynamique sur coussin réalisé (6 variantes figées)
`dyn_vm = clip(1 + α·cushion_eff, 0, 3)`, retrait cushion-retaining C_keep=0.20. Cohortes full-sample :

| config | vm moy | survie 6m | extr 6m | **survie 12m** | **extr 12m** | IS/OOS surv | survie 24m | extr 24m | busts d/f |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **B0** (vm1, retrait-tout) | 1.00 | 98.6 % | $362 | **98.6 %** | **$671** | 97/100 % | 98.5 % | $1352 | 2/0 |
| B1 (vm1 + C_keep) | 1.00 | 98.6 % | $217 | 97.2 % | $583 | 94/100 % | 94.0 % | $1024 | 4/0 |
| α=1 asym0 | 1.04 | 98.6 % | $203 | 93.1 % | $504 | 94/92 % | 78.2 % | $597 | 10/0 |
| α=1 asym1 | 1.04 | 98.6 % | $200 | 93.1 % | $504 | 94/92 % | 76.7 % | $597 | 10/0 |
| α=2 asym0 | 1.08 | 99.3 % | $191 | 94.5 % | $445 | 97/92 % | 84.2 % | $674 | 8/0 |
| α=2 asym1 | 1.07 | 99.3 % | $193 | 93.8 % | $446 | 95/92 % | 82.0 % | $709 | 9/0 |
| α=4 asym0 | 1.14 | 98.6 % | $125 | 92.4 % | $382 | 95/90 % | 77.4 % | $459 | 11/0 |
| α=4 asym1 | 1.14 | 98.6 % | $130 | 93.1 % | $395 | 97/90 % | 81.2 % | $478 | 10/0 |

**Deux constats.**
1. **Le dynamique s'active à peine** (vm moyen **1.04–1.14**) : les retraits (même cushion-retaining à $2k)
   plafonnent le coussin réalisé, donc `α·cushion_eff` reste petit. Et **même cette faible activation coûte
   la survie** (−4 à −6 pts vs B0) sans gagner d'extraction (toutes < $671). Les busts restent **DAILY**
   (d/f = 8–11/0) → le floor n'est jamais atteint, le coussin ne sert à rien.
2. **Le retrait cushion-retaining seul (B1) NUIT déjà** : $583 < $671 et survie 97.2 < 98.6. Laisser de
   l'argent dans le compte pour « bâtir le coussin » l'expose au bust **sans bénéfice** (le floor ne mord pas)
   et réduit l'extraction.

## Q3 — Le piège (gain → sizing monté → drawdown immédiat)
Le piège **n'est pas atteint de façon matérielle** parce que le daily plafonne le sizing si bas (vm moyen
≤ 1.14) que la montée est minime. L'**asymétrie up/down est sans effet mesurable** : α=2 asym0 94.5 % vs
asym1 93.8 % ; α=4 asym0 92.4 % vs asym1 93.1 % (dans le bruit). Le test conditionnel (α=4, le plus
agressif) le confirme : les busts **ne sont PAS concentrés près des pics frais** — seulement **3 % (asym off)
/ 0 % (asym on)** surviennent dans les 10 j d'un nouveau plus-haut (médiane **37–42 j** depuis le pic). Le
mode de panne dominant N'EST donc PAS le piège gain→levier→drawdown, mais les **busts de queue daily**
répartis dans les régimes de drawdown soutenu. L'asymétrie réduit marginalement le total (30→25 busts) et
élimine les rares busts près-pic, mais **ne peut rien contre le mode dominant**.
Conclusion : il n'y a pas de levier à protéger — le sizing reste trop petit pour créer le mode de panne.

## Q4 — Contrainte daily isolée (le plateau)
La fréquence de **bust DAILY monte de façon monotone avec l'agression**, sans plateau bénéfique :
- dynamique : busts daily 2 (B0) → 8 (α2) → 11 (α4) ; survie 98.6 → 94.5 → 92.4 %.
- statique : busts daily 2 → 8 (vm1.5) → 15 (vm2.0) → 23 (vm2.5) ; survie 98.6 → 89.7 → 82.8 → 79.3 %.
L'**optimum extraction-à-survie-tenue est au sizing le PLUS BAS (vm=1.0)** : toute agression dégrade
strictement les deux. (Note : les **floor**-busts n'apparaissent qu'à vm≥1.5 statique — 7 à vm1.5, 10 à
vm2.0 — quand des drawdowns multi-jours atteignent −10 %, mais la survie est déjà ruinée par les daily.)

## Q5 — Verdict (seuils pré-enregistrés)
- **DOMINE_B0** exigeait extraction > B0 (CI non chevauchant) ET survie ≥ B0 − 0.01 ET sur IS+OOS.
  **Aucune variante** : toutes ont `survie < B0 − 0.04` (disqualifiées sur la contrainte dure) ET extraction
  inférieure → `dom_B0 = False` pour les 6 + les 3 statiques.
- **GATING_RÉEL** (placebo apparié) : moot — le dynamique est déjà dominé par B0 et par B1 ; le gating
  n'est pas seulement cosmétique, il est **légèrement nuisible** (il monte le sizing après les gains, droit
  dans les jours de queue qui bustent en daily).
- **Verdict = (b)** : **le sizing statique vm=1.0 (retrait-tout) est déjà quasi-optimal.** Le sizing
  dynamique sur coussin réalisé ne domine rien — il dégrade la survie ET l'extraction. La thèse est défaite
  par la **structure à double barrière** : le **daily −5 % ($500 fixe) mord**, le **floor max-loss −10 % est
  lâche** au sizing viable (0 floor-bust à B0), donc le levier-coussin agit sur une contrainte non-active.

### Candidat de leçon (NOMMÉ, non gravé)
**« funded-daily-loss-binds-not-the-static-floor »** : en funded, la barrière contraignante au sizing de
référence est le **daily −5 % ($ fixe), pas le floor statique −10 %** (0 floor-bust mesuré à vm=1.0). Le
levier « monter le risque sur le coussin max-loss réalisé » agit sur une contrainte **non-active** → gain
nul, et toute agression multiplie les **pertes des jours de queue** (busts daily) → survie ruinée. Prolonge
**funded-survival-is-drawdown-governed-not-Sharpe** : non seulement la survie n'est pas gouvernée par le
Sharpe, mais en funded elle est gouvernée par la **queue daily**, pas par le coussin floor. Corollaire
opérationnel : en funded, **extraire les gains (retrait-tout) > les laisser comme coussin** (B0 > B1).

---

## Reproductibilité
- Pré-reg `PREREGISTRATION.md` (`b30fed2`, avant résultats). Code `code/book_funded_dynamic.py` (patch
  validé 0/40 vs canonical), `code/q_funded_sizing.py`, `code/q3_trap.py`. Résultats `results/*.json`.
- Moteur funded v2.2 (`engine_v22.run_funded` + cleanroom) **importé read-only depuis le main dir**
  (cleanroom+caches gitignored, locaux). Cohortes mensuelles 2013-10→2025-06 (régimes morts inclus),
  horizons 126/252/504 j. Book signals = `build_signals` (gold_trend+j1+overnight+ORB), CFG_FUNDED.
- **Book challenge vm14 jamais touché. Aucun fichier live touché. Aucun déploiement.** Env `/usr/bin/python3`.
