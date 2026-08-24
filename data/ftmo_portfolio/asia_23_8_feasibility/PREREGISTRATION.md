# PRÉ-REGISTRATION — ASIA_23_8 (gold overnight-drift) comme sleeve candidate FTMO

**Horodatage (committé AVANT tout résultat) :** 2026-06-19
**Auteur :** session de recherche Claude Code (author≠auditor — toute validation se fera en session fraîche)
**Branche :** `claude/asia-23-8-ftmo-feasibility`
**Cadre :** RECHERCHE PURE, sandboxée. AUCUN déploiement. AUCUN toucher au book live
(`ftmo_live/`, EA gelé `book_executor.mq5`, spec, yaml, FLAT/targets.json, compte armé).
Lecture seule sur tout artefact live. Cette étude est un **go/no-go de recherche**.

**Règle d'or :** les questions, métriques, et seuils ci-dessous sont **FIGÉS**. Je ne dois
**PAS** les ajuster après avoir vu le moindre résultat. Toute modification post-résultat
invalide l'étude (elle devra être relancée en session fraîche avec un nouveau pré-enregistrement).

---

## 0. Objet et artefacts de départ

- Stratégie : **long XAUUSD sur la fenêtre 23:00→07:00 UTC**, vol-targetée (VT interne causale,
  levier moyen ~1.05×, ~6.8% vol annualisée), un aller-retour/jour, **flat overnight**
  (swap-free *par construction* si le rollover broker ≤ 22:00 UTC).
- Code : `yt_strategy_replications/gold_research/strategy_overnight.py`
  (fonctions `overnight_returns`, `vol_target_scale`, `backtest`).
- Rapport de due-diligence : `yt_strategy_replications/reports/gold_ASIA_23_8_due_diligence.md`.
- **Incohérence interne notée AVANT résultats** (à arbitrer en Q1) : le rapport annonce
  Sharpe **1.10** / OOS **0.96** / DSR **0.99** / maxDD **−19.4%** / skew **+0.35** / t_HAC **4.8** ;
  le docstring du code annonce Sharpe **1.18** / OOS **1.07** / DSR **0.92** / maxDD **−15.6%** / t_HAC **3.9**.
  Les deux sources ne concordent pas entre elles : Q1 déterminera lesquels (si l'un des deux) sont reproductibles.

### Engines RÉUTILISÉS (read-only, pas de réimplémentation)

1. **PRIMAIRE — moteur barre v2.2 audité** : `data/ftmo_portfolio/v22/engine_v22.py`
   + cleanroom `data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py`
   (pin baseline `605f4a4` ; challenge contractuel pooled **0.87**, gate d'acceptation [86,91]).
   ASIA_23_8 sera **injectée** via un wrapper sandbox (`code/asia_inject.py`) qui *monkeypatche*
   `run_phase` pour ajouter, à l'ouverture de chaque jour (après que la ligne daily-loss est figée
   sur `balance@00:00`, AVANT le segment 09:00 du book), le P&L réalisé d'ASIA + un contrôle de
   barrière sur le **plus-bas intraday** d'ASIA. Justification de fidélité : la fenêtre
   23:00→07:00 UTC = **01:00→09:00 CET**, qui se **clôture exactement quand le premier segment du
   book (09:00 CET) commence** → injection causale, non invasive sur la logique 4-jambes auditée.
   **Validation obligatoire du wrapper** : ASIA OFF ⇒ reproduit le pooled canonique (cible 87.0,
   accept [86,91]) ET l'identité cash tient — preuve que le wrapper n'altère pas le book.
2. **CONTRE-VÉRIFICATION — `firstpassage.py`** (`PropFirms/ftmo/program_2026-06/ftmo_portfolio_audit/code/firstpassage.py`) :
   MC first-passage daily additif, block-bootstrap (Politis-Romano). Second avis indépendant sur les
   chiffres standalone d'ASIA (close-to-close, donc borne **optimiste** connue sur les bust daily-barrier).
   L'écart entre les deux engines borne l'effet du plus-bas intraday.
- **Métriques de perf/sig** : `yt_strategy_replications/engine/stats.py`
  (`sharpe_ratio`, `sortino_ratio`, `max_drawdown`, `hac_tstat` lag-6, `deflated_sharpe_ratio`,
  `stationary_bootstrap_pvalue`, `fold_metrics`).
- **Données** : `data/deep_history_utc/XAUUSD_M1.csv` (true-UTC, présent localement) → H1 via `engine/data.py`.

### Convention de triplet (imposée projet)
Tout chiffre prop-firm est rapporté en **triplet (p, attempts_moyen, EV)** :
- `p` = p(funded) poolé sur cohortes (IS+OOS), + décomposition IS / OOS.
- `attempts_moyen` = nombre moyen de tentatives challenge avant funding (mur 91 j).
- `EV` = espérance $ de campagne = `p_funded × funded_value − E[frais]` (frais $96/tentative,
  remboursés au 1er payout), `funded_value` = retraits espérés du stage funded (via `run_funded`).

### Méthode de cohortes (identique au book canonique, pour comparabilité)
- `cohort_starts` tous les **7 jours** sur `WINDOWS` = IS `2013-10-01→2019-12-31`,
  OOS `2020-01-02→2026-02-25` ; mur **91 j calendaires** ; funnel 2-step (P1 +10% → gap 3 j
  ouvrés → P2 +5%, vm×1.2 ; bust/abandon → retry après 2 j ouvrés ; dans le mur).
- CI : block-bootstrap sur cohortes (≥200 resamples) pour les configs **headline** uniquement.

### Sizing d'ASIA sur le compte (lever `asia_lev` = K)
- `K` = multiplicateur direct sur la série de rendement net natif d'ASIA (qui contient déjà sa VT
  interne ~1.05×, ~6.8% vol annu). K=1 ⇒ ~6.8% vol annu compte. Vol annu compte réalisée ≈ K×6.8%
  (rapportée par config).
- **Grille K pré-enregistrée** : K ∈ {1.0, 1.5, 2.0, 2.5, 3.0, 4.0} (≈ vol annu compte
  {6.8, 10, 14, 17, 20, 27}%). Cette grille ne sera pas étendue post-résultat.

### Variantes Q2 (budget « 3 modifications max » — explicitement consommé ici)
- **V0** baseline (VT native), balayage K.
- **V1** sizing prudent = borne basse de la grille K (K≤1.5) — *pas une mod, c'est V0 à bas K*.
- **V2 (mod 1)** equity-gate MA100 sur l'équité **simulée de la sleeve** : scale 0.4 si
  eq_sleeve < MA100(eq_sleeve), sinon 1.0, `.shift(1)` (strictement causal ; calque du gate gold_trend).
- **V3 (mod 2)** overlay de régime : trader seulement si **drift brut glissant 252 j > 0**
  (somme des window-returns bruts pré-VT/pré-coût sur 252 j, `.shift(1)`, causal), sinon flat (scale 0).
  Rapporté **IS vs OOS séparément** pour exposer tout whipsaw/overfit.
- **V4 (mod 3)** V2+V3 combinées.
Au-delà de V4 : budget épuisé, aucune autre variante.

---

## Q1 — Reproduction
**Test :** exécuter `strategy_overnight.backtest` sur le stack actuel (XAUUSD M1→H1 true-UTC),
spreads {1.0, 1.5, 2.0} bp, swap=0. Calculer : Sharpe full + OOS (dernier 40%), DSR(90 trials),
t_HAC(lag-6), maxDD, skew, kurtosis, β vs buy&hold gold (régression daily), rendement/vol annualisés,
WF 5/5. Comparer aux deux sources (rapport ET docstring).

**Seuil PASS-repro (figé) :** reproduit **au moins une** des deux sources à
|ΔSharpe|≤0.07, |ΔmaxDD|≤2.5 pts, |Δskew|≤0.10, signe/ordre de grandeur de t_HAC et DSR cohérents.
Sinon **DIVERGENCE** : documenter laquelle est reproductible, l'écart exact, et la cause probable.

## Q2 — Survie aux gates FTMO 2-step (LE point critique)
**Test :** moteur barre v2.2 + injection ASIA (plus-bas intraday inclus), book OFF, balayage K + V2/V3/V4.
Règles : daily-loss −5% (M5, vs balance@00:00), max-loss −10% **statique** (floor 9000), cibles
+10%/+5%, min 4 j/phase, mur 91 j, funnel 2-step. Triplet (p_funded, attempts, EV) par config,
+ p_bust par tentative, + distribution du drawdown sous contrainte. Contre-vérif `firstpassage.py`.

**Seuils (figés) :**
- **VIABLE-standalone** : ∃ config pré-enregistrée avec p_funded(poolé) **≥ 0.50** ET
  p_bust(poolé/tentative) **≤ 0.35** ET p_funded(OOS) **≥ 0.40** ET robustesse causale
  (IS et OOS tous deux ≥ 0.30, pas d'effondrement IS≫OOS).
- **CONDITIONNEL-standalone** : best config p_funded(poolé) ∈ **[0.30, 0.50)** avec bust contrôlé,
  OU ne franchit 0.50 qu'en IS (OOS < 0.40) — fonctionne mais régime-fragile.
- **NON-VIABLE-standalone** : aucune config n'atteint p_funded(poolé) **≥ 0.30**, OU bust non
  contrôlé (p_bust > 0.50) à tout sizing atteignant la cible.

## Q3 — Conflit avec la sleeve or-trend existante
**Tests :**
(a) **Corrélation** des rendements daily sleeve-level ASIA vs gold_trend (gold_trend reconstruite
   via `cleanroom.engine.build_signals` — sa série net daily). Pearson + Spearman, full + par régime.
(b) **Marge cumulée pire cas** : pendant la fenêtre 01:00–09:00 CET les deux jambes XAUUSD coexistent
   (gold_trend tenu en continu Swing + ASIA). Calculer marge stackée / équité aux taux **swing_official**
   (XAU 1:9=0.1111) : p50/p99/p999 et fraction de temps > cap 60% / > 100%.
(c) **Chevauchement horaire** : documenter quand les deux positions XAUUSD coexistent.
(d) **Ablation** : book vs book+ASIA (même moteur, mêmes cohortes) → Δp_funded, Δattempts, ΔEV,
   ΔSharpe sleeve-level. Sanity : book seul ASIA-OFF reproduit 0.87.

**Seuils (figés) :**
- **DIVERSIFIANTE** : corr(ASIA, gold_trend) Pearson full **< 0.50** ET book+ASIA p_funded
  **≥ book − 0.02** (non dilutif au bruit près) ET marge pire-cas **≤ 60%** (ne force pas de de-lever).
- **CONCENTRATION DÉGUISÉE** : corr **≥ 0.50** OU marge pire-cas **> 60%** (force de-lever/breach)
  OU book+ASIA p_funded **< book − 0.05** (dilutif).

## Q4 — Risque rollover / swap sur l'infra FTMO
**Tests (lecture seule live + spec) :**
(a) Confirmer le fuseau serveur & l'heure de rollover depuis `ftmo_live/lib/market_hours.py`
   (read-only) + spec_v22 (`triple_dow`, swap_long_pts). Déterminer si la fenêtre **23:00→07:00 UTC**
   contient l'instant de rollover (00:00 serveur). Mesurer le swap-leak effectif (bps/nuit).
(b) Vérifier que l'entrée 23:00 UTC est hors du **trou de liquidité** de rollover (≥1 h).
(c) Wednesday triple-swap : impact (XAUUSD `triple_dow`).

**Seuils (figés) :**
- **SWAP-FREE CONFIRMÉ** : la fenêtre 23:00→07:00 UTC **ne contient pas** l'instant de rollover
  (00:00 serveur) été comme hiver ⇒ 0 nuit facturée ; swap-leak effectif **≤ 0.2 bp/nuit** ;
  entrée 23:00 UTC à **≥ 1 h** du rollover.
- **SWAP-LEAK** : la fenêtre contient l'instant de rollover, OU swap-leak > 0.2 bp/nuit.
- **Caveat exécution** (orthogonal au swap) : la session asiatique a un spread plus large et le
  **fill précis à 23:00 UTC** est le make-or-break (rapport : entrée +1 h ⇒ Sharpe 0.37). Non
  mesurable hors paper-trade → si tout le reste passe, le verdict reste **CONDITIONNEL** sur ce point.

## Q5 — Verdict (règle de décision figée)
- **(a) VIABLE** (mérite une étude d'intégration ultérieure, séparée, frozen, AVANT/APRÈS+GO) ssi
  Q2=VIABLE **ET** Q3=DIVERSIFIANTE **ET** Q4=SWAP-FREE CONFIRMÉ.
- **(b) CONDITIONNEL** ssi Q2∈{VIABLE,CONDITIONNEL} ET Q3=DIVERSIFIANTE ET Q4=SWAP-FREE-en-spec —
  viable **seulement** après paper-trade confirmant le fill 23:00 + spread live ≤ ~1.5 bp + swap-free réel.
- **(c) NON-VIABLE pour FTMO** ssi Q2=NON-VIABLE **OU** Q3=CONCENTRATION **OU** Q4=SWAP-LEAK.

Le rapport final (`STUDY_ASIA_23_8_FTMO_2026-06-19.md`) rendra Q1–Q5, tableaux complets, triplets,
ablations, + (si CONDITIONNEL) la liste exacte de ce qu'il faut mesurer en paper-trade.

---

### Lessons applicables (rappel, non négociées ici)
- L30/L36 : le swap overnight pré-tue toute prime tenue → la viabilité d'ASIA REPOSE sur le swap-free.
- L20/L21 : DSR obligatoire (n_mod≥2) ; SR live single-instrument day-trade ∈ [0.8,2.0] (catégorie).
- L33/L46 : la structure de COÛT réelle (spread session asiatique), pas le signal, décide.
- L39 : reporter skew daily ET mensuel (la barrière FTMO 5% est daily).
- Règle « 3 modifications max » : V2/V3/V4 = budget complet, pas davantage.
