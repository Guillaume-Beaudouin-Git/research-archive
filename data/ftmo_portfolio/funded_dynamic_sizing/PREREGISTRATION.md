# PRÉ-REGISTRATION — Sizing funded dynamique sur coussin réalisé (floor statique FTMO)

**Horodatage (committé AVANT tout résultat) :** 2026-06-19
**Worktree dédié :** `../Algo_claude_fundedsizing` · **Branche :** `claude/funded-dynamic-sizing` (off origin/main)
**Auteur :** session Claude Code (author≠auditor — validation ultérieure en session fraîche)
**Cadre :** RECHERCHE PURE. AUCUN déploiement. AUCUN toucher au book live (`ftmo_live/`, EA gelé, FLAT,
targets, spec, yaml). Lecture seule. **Règle d'or : seuils figés, non ajustables après résultats.**

## 0. Portée STRICTE et thèse
**UNIQUEMENT le compte FUNDED** (après passage des 2 phases). Le book CHALLENGE reste **vm14, intact,
optimal — jamais touché**. On étudie un régime de sizing distinct qui ne s'activerait qu'en funded.

**Thèse.** Le floor max-loss FTMO est **STATIQUE à −10% de l'équité INITIALE** ($9 000), il ne monte pas
avec les gains. Chaque dollar de gain RÉALISÉ (consolidé en balance) augmente le coussin de survie
max-loss sans bouger le floor. Puisque la survie funded est gouvernée par le drawdown absolu vs floor
statique (leçon **funded-survival-is-drawdown-governed-not-Sharpe**, [[asia_23_8_ftmo_feasibility_2026-06]]),
on pourrait monter le risque avec le coussin réalisé sans dégrader la survie → maximiser l'extraction.

**CONTRAINTE DOUBLE (le piège central).** Deux barrières ; le coussin n'aide que sur UNE :
- **Max-loss −10% STATIQUE** ($9 000 fixe) : bénéficie du coussin réalisé. Le levier de l'idée.
- **Daily-loss −5%** = `equity ≥ balance@00:00 − 5%·INIT` → **budget $500/jour FIXE**, indépendant du
  coussin accumulé. Monter le risque augmente la proba de percer le DAILY un mauvais jour, **quel que
  soit le coussin max-loss**. Le sizing doit respecter la borne la plus contraignante à chaque instant.
**Pronostic honnête (à mesurer, pas à supposer) :** le daily $500 plafonne l'agression bien avant que le
coussin max-loss morde → bénéfice probablement modeste. Le rôle du coussin ≈ celui du `taper` existant
(réduit près du floor) en miroir (augmente loin du floor) — MAIS borné par le daily.

## 1. Setup (FIXE, réutilise le sim funded audité — pas de réimplémentation)
- **Moteur** : `engine_v22.run_funded` (+ cleanroom), importé **read-only depuis le main dir**
  (`<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/v22`) car cleanroom+caches y
  vivent (gitignored). **Patché UNIQUEMENT** pour (a) vm dynamique/jour, (b) politique de retrait
  cushion-retaining, (c) logs min-balance / daily-bust / extraction. Logique de trading des jambes
  INCHANGÉE. **Validation** : variante statique vm=1.0 retrait-tout doit reproduire le run_funded
  canonique au centime (preuve non-invasive).
- **Cohortes** : démarrages mensuels (tous les 21 j-bourse) sur **TOUT l'échantillon 2013-10→2025-06**
  (incluent les régimes morts 2018-19/2022 — le `FUNDED_WINDOWS` de la spec les saute ; je ne le fais PAS,
  sinon survie flattée). **Horizons : 126 / 252 / 504 j (6 / 12 / 24 mois).**
- **Coussin réalisé** : `excess_cushion = max(0, (balance − INIT)/INIT)` — sur la **BALANCE consolidée**
  (gains réalisés en balance), PAS l'équité flottante. (À balance=$11k → 0.10 ; $13k → 0.30.)
- **Retrait cushion-retaining** (FIXE, régime dynamique) : tous les 14 j, retirer `balance − (INIT + C_keep)`
  si positif, `C_keep = 0.20·INIT = $2 000`. Construit la balance jusqu'à ~$12k (coussin floor $3k) puis
  extrait au-dessus. (La baseline B0 garde le retrait-tout existant `balance − INIT`.)
- **Daily ENFORCÉ par le moteur** : le moteur buste/breaker sur percement du daily ; je **mesure** la
  fréquence de daily-bust (pas de cap analytique — la réalité du moteur enforce la contrainte).
  `dyn_vm` plafonné à `vm_cap = 3.0` (garde-fou absolu).

## 2. Baselines / contrôles (PAS des « variantes » du budget DSR)
- **B0 (RÉFÉRENCE)** : static vm=1.0, retrait-tout (`balance−INIT`) — le **régime funded ACTUEL**. À ne pas dégrader.
- **B1** : static vm=1.0 + retrait cushion-retaining (C_keep=0.20). Isole l'effet de la POLITIQUE de retrait.
- **B2 (placebo exposition-appariée)** : static vm ∈ {1.5, 2.0, 2.5} + retrait cushion-retaining. Donne
  l'optimum de sizing STATIQUE sous contrainte daily, ET sert de placebo : pour chaque variante dynamique
  gagnante, comparer à un vm STATIQUE à exposition moyenne APPARIÉE. **Si dynamique ≈ static-apparié →
  le gating-coussin est cosmétique (le daily mord, pas le floor)** ; si dynamique > static-apparié → le
  gating ajoute de la valeur réelle (le floor mordait au static-haut).

## 3. Q1 — Diagnostic baseline + référence à ne pas dégrader
B0 sur le MC funded : extraction cumulée médiane (trader 0.8·(retraits+résidu)) à 6/12/24m, survie
(p non-busté), distribution min-balance vs floor. **Diagnostic clé** : à vm=1.0, distribution de la
**perte pire-jour vs budget $500** (combien de marge daily ?) + **composition des busts (daily vs floor)**.
C'est ce qui décide s'il existe une marge pour monter le sizing et quelle barrière mord.

## 4. Q2 — Fonction de sizing dynamique (≤6 variantes FIGÉES)
`dyn_vm_t = clip( base × (1 + α × cushion_eff_t), 0, vm_cap )`, base=1.0, vm_cap=3.0.
**6 variantes = α ∈ {1.0, 2.0, 4.0} × asymétrie ∈ {OFF, ON}** (budget épuisé, aucune 7e).
- **asym OFF** : `cushion_eff_t = excess_cushion_t` (symétrique : monte ET descend avec la balance).
- **asym ON** : `cushion_eff_t` à cliquet — monte de ≤ `ramp = 0.02/jour` vers `excess_cushion_t`, mais
  **redescend instantanément** à `excess_cushion_t` dès qu'un jour est en perte (`balance_t < balance_{t-1}`).
  → protège contre le piège Q3 (leveragé pendant un drawdown frais).
Par variante : extraction 6/12/24m, survie, min-balance p5/pire, **fréquence daily-bust**, part daily/floor,
vm moyen réalisé (pour l'appariement B2).

## 5. Q3 — Le piège : montée trop rapide sur coussin fragile
Test de robustesse : mesurer le **taux de bust conditionnel après un pic frais** (séquence gain →
sizing monté → drawdown immédiat, avant consolidation). Concrètement : p(bust dans les N≤10 jours | la
balance vient de faire un nouveau plus-haut ce cycle) pour chaque variante, **asym ON vs OFF**. L'asymétrie
doit réduire ce taux. Une variante qui buste mal ici est **disqualifiée même si extraction médiane haute**.

## 6. Q4 — Contrainte daily-loss isolée (le plateau)
À chaque niveau d'agression (α), de combien monte la fréquence de percement du daily −5% ? Existe-t-il un α
où le gain d'extraction est **mangé par les daily-busts** (optimum, comme le plateau vm-sweep
[[vm_sweep_ftmo_2026-06]]) ? Tracer extraction-à-survie-tenue vs α → point optimal.

## 7. Q5 — Verdict + seuils GO/NO-GO (FIGÉS)
Triplet funded : **(extraction médiane $, survie %, max drawdown / min-balance)**.
- **DOMINE_B0** ssi : `extraction_med(var) > extraction_med(B0)` d'une marge **> CI block-bootstrap**
  (non chevauchant) **ET** `survie(var) ≥ survie(B0) − 0.01` **ET** vrai sur **IS ET OOS** (pas d'artefact).
- **GATING_RÉEL** ssi la variante dynamique gagnante bat le **static-apparié B2** (même vm moyen) d'une
  marge > bruit. Sinon le gating est cosmétique (le daily mord) → la « dynamique » ≡ un vm statique plus haut.
- **Survie = contrainte DURE** : `survie(var) < survie(B0) − 0.01` → **DISQUALIFIÉE**, peu importe l'extraction.
- **Verdict (a) VIABLE** : ∃ variante qui DOMINE_B0 ET GATING_RÉEL ET survit au piège Q3 → recommander
  (α, asym, caps, C_keep) + gain d'extraction chiffré.
- **(b) STATIQUE QUASI-OPTIMAL / NON** : aucune variante ne domine B0 à survie tenue, OU le gain dynamique
  = celui d'un vm statique plus haut (gating cosmétique), OU le daily/piège plafonne. **Le dire clairement.**
- **DSR** pénalise n_trials = **6** (+ recherches funded antérieures : vm-sweep challenge non comptée car
  challenge). Tout Sharpe funded rapporté est déflaté à n_trials≥8.

## Garde-fous & livrable
- Lecture seule live, aucun déploiement, book challenge vm14 jamais touché.
- **Améliorer l'extraction en dégradant la survie n'est PAS une amélioration** — survie = contrainte dure,
  pas une variable d'échange. Critère = extraction À survie tenue.
- Honnêteté author≠auditor : si le gain optimal est modeste (pronostic : le daily plafonne), le dire sans survendre.
- Livrable : `STUDY_FUNDED_DYNAMIC_SIZING_2026-06-19.md`, branche dédiée, pré-reg figée AVANT résultats,
  tableaux, triplets, fonction recommandée OU constat « statique déjà quasi-optimal ». Aucune PR auto-créée.
