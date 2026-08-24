# vm-sweep — PRÉ-ENREGISTREMENT (figé 2026-06-17, AVANT tout résultat)

**Question.** vm14 + clip dynamique est-il l'optimum d'EV du container FTMO Swing 2-step,
ou un régime de taille plus agressif fait-il mieux ? Caractériser aussi le profil « sprint »
(maximiser p(pass) rapide au prix du bust) — pour DOCUMENTER, pas adopter.

**Contrainte d'intégrité.** Lecture seule. AUCUN contact compte live / EA `book_executor` /
FLAT / targets. On RÉUTILISE le simulateur audité (`engine_v22` + cleanroom `engine`, via les
helpers de `v222_swing_fit/run_swing_fit.py`) ; on NE réimplémente AUCUNE logique de caisse,
barrière, clip ou funnel. Seul le grid `vm` change. Baseline READ-ONLY `1947163`.

---

## Sim réutilisé (inchangé)
- Caisse / barrières / breaker / gap : `data/ftmo_portfolio/v22/engine_v22.py::run_phase` (V).
- Sizing / clip-marge / governor : `audit_v2_independent/cleanroom/engine.py::_target_for_segment` (E).
- Funnel P1→P2 : `engine_v22::run_funnel` (V) ; wall = jours calendaires.
- Mesure (cohortes, block-bootstrap CI, attempt_breakdown, margin_stats, paired, no-clock) :
  helpers importés de `run_swing_fit.py` (code de mesure de l'étude v2.2.2, identique).
- Stack : `M_swc` (swaps mesurés constants + commissions, re-cost v2.2.1) ; `MRATE = SWING`
  (forex 1:30, indices 1:15, métaux 1:9) ; `CFG_CHALLENGE` baseline (breaker 0.30, taper 0.02,
  glide 0.5, pace on k=1, ab_days 5, **margin_cap 0.60**, micro_orb on, p2_mult 1.2, on_w 0.6).
- Cohortes : `WINDOWS` IS (2013-10→2019-12) + OOS (2020-01→2026-02), `COHORT_STEP = 7`
  (identique baseline → vm10/vm14 DOIVENT reproduire 70.13 / 71.43).

## Le clip dynamique = cap marge 60 % (rappel mécanique, figé)
`scale = vm·taper·glide·pace` ; `tgt_k = poids_k·scale·eq` ; puis si `need = Σ|tgt|·MRATE > 0.60·eq`
→ `tgt ·= 0.60·eq/need` (réduction proportionnelle, direction signal préservée). Donc :
**vm→∞ ⇒ need→∞ ⇒ livre épinglé à exactement 60 % de marge** dans la direction signal = le
« full port » LITTÉRAL est borné par le cap (à montrer via bind→100 % et vm_eff plateau). NB : au
cap, le taper de sécurité est DÉFAIT (need reste > cap même quand taper réduit scale).

## Grille figée (7 arms)
`vm ∈ {10, 14, 18, 22, 26, 30, ∞}`  où ∞ = sentinelle `1e6` (cap-bound).
vm14 = arm de référence (= baseline A). Tout le reste identique.

## Métriques figées (1 ligne par vm)
Triplet ÉTENDU demandé :
1. **p(pass P1 / tentative)** — single-attempt SANS horloge (`pass/att P1 no-clock`, terme
   gambler's-ruin pur) ; + P1-pass in-funnel pour contexte.
2. **n_tentatives moyen** (`d91.attempts.mean()`, wall 91j).
3. **p(bust / tentative)** = (bust_daily + bust_floor)/tentative, in-funnel ; split reporté.
4. **délai médian de pass** = `t_med` = médiane des jours **CALENDAIRES** (≤91) des cohortes
   funded (métrique canonique du sim ; jours calendaires, PAS trading — noté tel quel).
5. **p(funded ≤ 3 mois)** = `p91` = `d91.funded.mean()` + CI95 block-bootstrap (B=10, nb=4000).
6. **EV / campagne** = `mean(funded·VAL − attempts·FEE)`, **VAL_swc = $1,438**, **FEE = $96**
   (sim ; remboursé au 1er payout). Colonne miroir @ **VAL_comm = $1,381**. Note fee : à $99,
   ΔEV = −(99−96)·n_tent ≈ −$9/campagne → classement INVARIANT.

Diagnostics figés : bind %, clip_depth, abandon %, timeout %, bust_daily/floor split, pace_floor %,
p182 / p270 (info comité), p30 / p45 (horizons SPRINT, ci-dessous).

## Profil SPRINT (figé, à DOCUMENTER pas adopter)
Walls additionnels figés : `{30, 45}` jours calendaires (campagne ET phase). Sprint-métrique =
**p45** (et p30) = p(funded dans la fenêtre courte). Arm sprint = `argmax_vm p45`. On reporte son
triplet (p45, bust/tentative, EV91) et l'écart vs l'optimum EV. C'est le régime « passer vite au
prix du bust » — documenté, non adopté.

## Trois points figés (a/b/c)
- (a) **argmax_vm EV91**.
- (b) **argmin_vm t_med** (pass médian le plus rapide), avec son (p91, n_tent, EV91).
- (c) **vm où EV91 devient négatif** en montant vm (sinon : « pas de négatif dans la grille ;
  EV plateau/asymptote à $X au cap »).
- Montrer explicitement que (a) ≠ (b) et de combien : ΔEV et Δt_med, CI90 apparié vs l'optimum EV.

## Décomposition bust figée (Q4 — arm le plus agressif ∞, + vm30 en contrôle)
- bust_daily (−5 %) vs bust_floor (−10 %) : en % de tentatives ET en % des busts.
- Passe diag (`V.run_funnel(diag=[])`) : parmi les busts, part au **bar d'ouverture du jour**
  (`first_bar = (seg==0 & bar==0)`) → preuve que le **breaker M5 ne peut PAS agir à travers un
  gap** (aucun bar intra-day antérieur au breach). De ces busts first_bar : part sur lundis
  post-weekend (gap : `(date−date_préc).days ≥ 3`) et jours triple-swap (DOW triple canonique :
  XAU/JPY mercredi[dow=2], US100/GER40 vendredi[dow=4], cf. `MEASURED_SPECS.triple_dow`).
- Vérification breaker-vs-gap : (i) au canonical (`wgap_stress=1.0`, gap = vrai saut d'ouverture
  M5 historique) part first_bar reportée ; (ii) **un** run de stress étiqueté `wgap_stress=1.5`
  pour montrer que les busts first_bar augmentent quand le gap est amplifié (le breaker reste
  incapable d'intervenir dans le trou). Stress = sensibilité étiquetée, PAS un chiffre canonique.

## Single-sleeve vs diversifié figé (Q5)
- p91 standalone @ vm14 des 3 sleeves P&L : **Overnight-only** (WT=0, ON on), **Gold-only**
  (WT col0, ON off), **J1-only** (WT col1, ON off). Micro-ORB on (cosmétique min-4-jours).
- Meilleure sleeve standalone (hypothèse registre : **Overnight = mur porteur +12.1 pts ablation,
  MAIS DSR 0.29 FAIL** sur sa grille 40 cellules ; J1 standalone SR +0.42) prise « full »
  (vm=∞ cap-bound) vs **livre diversifié 4 sleeves @ vm14**. Reporter p91 + EV + split daily-bust
  des deux. Documenter pourquoi la diversification bat (ou non) la concentration.

## Gate de reproduction figé (STOP si échec)
`policy 87.01 ±0.5` ET `swing 71.43 ±0.5` doivent reproduire (sinon STOP : sim mal câblé).
Cross-checks intégrés : `vm10 → 70.13 ±0.7`, `vm14 → 71.43` (= gate swing).

## Discipline no-peek
Grille + métriques + règles de décision figées ici, **committées avant exécution** de
`run_vm_sweep.py`. Toute modif post-résultats = amendement documenté qui invalide le
pré-enregistrement. Conditionnel à l'hypothèse marge Swing officielle (lecture `margin_rate_live`
serveur Swing PENDANTE, comme v2.2.2).

## Livrable
`STUDY_VM_SWEEP_2026-06-17.md` : tableau complet 7 vm, points (a/b/c), profil sprint,
décomposition bust + vérif breaker-gap, single-sleeve vs diversifié, recommandation claire
(garder vm14 ou bouger) avec triplet (p, tentatives, EV) de chaque option.
