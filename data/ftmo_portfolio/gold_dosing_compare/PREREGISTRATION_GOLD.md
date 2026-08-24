# PRÉ-REGISTRATION — Gold dans le book : dosage ASIA + comparaison or-trend vs ASIA

**Horodatage (committé AVANT résultats) :** 2026-06-20
**Auteur :** session Claude Code (author≠auditor — validation en session fraîche)
**Branche :** `claude/gold-dosing-compare` (worktree `Algo_claude_goldcompare`, depuis origin/main)
**Cadre :** RECHERCHE PURE, sandboxée. AUCUN déploiement. AUCUN toucher au book live (`ftmo_live/`, EA gelé,
FLAT, targets). Lecture seule. Go/no-go de recherche.

**Règle d'or :** questions, configs (≤6), métriques, seuils ci-dessous **FIGÉS**. Aucun ajustement post-résultat.

---

## 0. Objet, acquis, engines

- **Deux stratégies gold sur XAUUSD :**
  - **ASIA** = overnight-drift long systématique **23:00→07:00 UTC**, toujours actif, vol-targeted (`gold_research/
    strategy_overnight.py`). Acquis : challenge NON-VIABLE (35 %) ; funded à **taille contributive K=1** dilue la
    survie book **Δ−29.7** (97.9→… ; étude `claude/asia-23-8-funded`). Stop −2.5 % NE mange PAS l'edge (Sharpe 1.12).
  - **or-trend** = sleeve gold du book = blend signe-momentum (lookbacks 60/120/250) + carry-adj swap, **signal-
    dépendant** (n'entre que si |signal|≥θ), equity-gate MA100 sur la courbe sim de la sleeve (`cleanroom.build_signals`
    WT["XAUUSD"]). Baseline mesurée : **active 39.3 % des jours**, long 25.8 %, Sharpe(jours actifs) 0.40.
- **Acquis NON re-testés** (leçons appliquées) : *funded-survival-is-drawdown-governed-not-Sharpe* ;
  *funded-daily-loss-binds / max-loss floor STATIQUE −10 % ($9000)* ; *two-FTMO-stages-reward-opposite-axes* ;
  **ablation funded = FUNDED_WINDOWS CANONIQUES** (IS 2013-17 + OOS 2020-24, 191 cohortes ; book-only **97.9 % /
  fundedV $1442** — REPRODUIT, l'anchor ; PAS de fenêtre de convenance — artefact attrapé à l'étude panier).
- **Engines réutilisés (validés)** : `asia_inject.py` (ASIA-OFF→**87.01 %** reproduit ✓, run_funded patché),
  `asia_series.py`, `asia_stop.py` (stop −2.5 % reproduit : trig 0.1 %, Sharpe 1.13, alpha rendu 2.7 %),
  `asia_fp.py` ; moteur v2.2 audité (pin `605f4a4`) + cleanroom `build_signals` (or-trend) ; données
  `XAUUSD_M1.csv` (true-UTC). Copiés depuis `claude/asia-23-8-funded` dans le worktree (self-contained).
- **Triplet** (imposé) : (extraction = fundedV, survie-12m, min-balance p5). Δ vs book seul.

### Ce qui N'EST PAS encore testé (l'angle neuf)
1. **Dose FINE d'ASIA** : l'asia-funded n'a testé que K=1 (Δ−29.7) et K=0.5 (Δ−23.4) — jamais les **petites
   doses** (0.1, 0.25), ni sur la fenêtre **canonique**. Existe-t-il une dose net-positive à survie tenue ?
2. **Comparaison directe or-trend vs ASIA** (même instrument, deux conteneurs) : complémentaires ou redondants ?

### Configs FIGÉES (≤6 ; anti-sur-recherche — gold a déjà consommé des essais ; DSR n_trials=100 hérité)
- **Part A — 5 doses** : K ∈ {0.1, 0.25, 0.5, 0.75, 1.0} (× la taille contributive K=1), stop −2.5 % fixé.
  (risk-scaling Sharpe-invariant, PAS une recherche d'edge → ne multiplie pas les essais d'alpha.)
- **Part B — 1 swap structurel** : book avec ASIA remplaçant or-trend (mesure comparative, PAS un déploiement).
6 configs au total. Au-delà : budget épuisé.

---

## PARTIE A — Dosage : dose de gold ASIA net-positive à survie tenue ?
**Test :** pour chaque dose K, ablation funded **canonique** (book vs book+ASIA_dosé, stop −2.5 %), moteur v2.2
run_funded patché (cohortes FUNDED_WINDOWS, horizon 504 j, retraits 14 j). Triplet (fundedV, survie-12m,
min-balance p5) + Δsurvie / Δextraction vs book seul (97.9 % / $1442). Courbe dose → (Δsurvie, Δextraction).

**Seuils (figés) :**
- **DOSE NET-POSITIVE EXISTE** : ∃ dose avec **Δsurvie ≥ −2.5 pt** (survie ≥ 95.4 %) **ET Δextraction > 0**
  (gold ASIA ajoute de l'extraction funded sans diluer au-delà du bruit).
- **DILEMME DE DOSAGE PROUVÉ** : pour CHAQUE dose, soit Δsurvie < −2.5 pt (dilue), soit Δextraction ≤ 0 (ne
  contribue pas) — aucune dose n'a les deux. Diagnostic : comparer la dose-seuil où Δextraction>0 vs la dose-
  seuil où Δsurvie passe sous −2.5 pt ; si contribuer EXIGE une dose qui dilue déjà → dilemme.
- **Hypothèse à réfuter** : dilemme (pas de point milieu). Mesurer, ne pas supposer.

## PARTIE B — or-trend (book) vs ASIA (overnight) : complémentaires ou redondantes ?
**Tests (historique commun) :**
(a) **Standalone** : Sharpe, rendement, maxDD, skew de or-trend (WT[XAUUSD] net reconstruit) vs ASIA
   (asia_series net), même période.
(b) **Corrélation** rendements daily or-trend vs ASIA (Pearson + Spearman, full + par régime).
(c) **Complémentarité temporelle** : (i) régime ASIA-mort 2018-19 — or-trend gagne-t-il là ? (ii) jours où
   or-trend est OFF (signal=0/gate, ~60 %) — ASIA est-elle positive (comble-t-elle le trou) ? (iii) overlap ON/ON.
(d) **Jours actifs/an** : ASIA (~100 %) vs or-trend (39.3 %).
(e) **Swap hypothétique (NE PAS déployer)** : book avec or-trend [standard] vs book avec **ASIA remplaçant
   or-trend** (WT[XAUUSD]=0 + ASIA injectée K=1) — challenge p_funded ET funded survie. Optionnel : book avec
   **les DEUX** (or-trend + ASIA) — l'angle « both gold ».

**Seuils (figés) :**
- **COMPLÉMENTAIRES** : ρ(or-trend, ASIA) Pearson **< 0.50** ET anti-phase temporelle (l'une gagne quand
  l'autre est coupée/morte — ex. or-trend positif en 2018-19, OU ASIA positive quand or-trend OFF).
- **REDONDANTES** : ρ ≥ 0.50 OU même phase (les deux ON/OFF ensemble, gains/pertes alignés).
- **MEILLEUR CONTENEUR** : par étage — celui qui donne le meilleur (challenge p_funded ; funded survie) au book
  dans le swap (e). Attendu (à confirmer) : divergence par étage (two-stages-opposite-axes).

## Verdict (règle figée)
- **Part A** : dose net-positive existe (laquelle) OU dilemme prouvé.
- **Part B** : complémentaires (la combinaison battrait-elle l'une seule ? → angle « both gold » futur) OU
  redondantes (double emploi) ; meilleur conteneur gold pour CE book, et pourquoi.
- **Angle « both gold ensemble »** : OUVERT (mérite étude future) ssi Part A trouve une dose ASIA survivable
  **ET** Part B montre complémentarité ; sinon **CLOS**.
Comparaison explicite aux verdicts rendus (ASIA solo rejet). Triplets partout.
Livrable : `STUDY_GOLD_DOSING_COMPARE_2026-06-20.md`. Puis audit indépendant.

### Lessons rappelées : funded-survival-drawdown-governed ; daily-binds/static-floor ; two-stages-opposite-axes ;
ablation funded = fenêtre canonique ; DSR n_trials=100 (hérité asia-funded) ; règle 3-mods (A-doses + B-swap = budget).
