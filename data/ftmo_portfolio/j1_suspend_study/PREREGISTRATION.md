# PRE-REGISTRATION — J1 (USDJPY) suspension en zone d'intervention BoJ/MoF

**FROZEN before results.** Study dir : `data/ftmo_portfolio/j1_suspend_study/`.
Worktree `claude/j1-intervention-suspend` (off `origin/main` 5fcbae1). Auteur : session Claude
2026-07-03. Auditeur ≠ auteur (sous-agent indépendant avant tout verdict).

Baseline = chaîne v2.2.1 gelée (yaml sha `56fbdde7`, `config_v22.py` / `engine_v22.py`,
moteur cleanroom `engine.py`). Réutilise le harnais audité EQUIV de la levcap study
(`j1_engine.py` = clone instrumenté, hooks `j1_lev_cap`/`j1_band` laissés INERTES).

## Contexte & motivation (mesuré AVANT cette pré-reg — rétrospectif)
- 2 comptes FTMO $10k tués en 48 h (<ACCOUNT_ID> le 02/07 documenté ; <ACCOUNT_ID> le 03/07 rapporté
  par l'opérateur, non encore au dépôt) par le MÊME mécanisme : J1/USDJPY LONG ~16.8× ouvert au
  rebalance, flash d'intervention BoJ/MoF le lendemain matin, daily-loss −5 % percé avant que le
  breaker M5 discret ne puisse agir. Root cause = **sizing**, pas le breaker (post-mortem +
  levcap Q4).
- **Donnée décisive** : la série USD/JPY du moteur (`panel_px`, ≡ `USDJPY_daily_cet`) **finit
  2026-06-05, max close 161.57**. Jours ≥ seuil (2013-10→2026-06) : **≥161.95 : 0 ; ≥160 : 17
  (tous 2024-06-26→2026-06-05) ; ≥158 : 100 ; ≥156 : 219**. Les 17 jours ≥160 sont TOUS dans la
  fenêtre OOS (2020-01→2026-02). Les pires gaps J1 in-sample (Grexit −$2,822, NK −$871, SVB −$633)
  n'étaient **PAS** des jours USD/JPY-haut.

## Ce que le backtest PEUT et NE PEUT PAS montrer (déclaré avant résultats)
- **PEUT** : borner le **COÛT campagne** de la suspension (Δp, ΔEV) — attendu ≈ 0 au seuil
  opérationnel car la zone est rare et concentrée en fin d'OOS.
- **NE PEUT PAS** : chiffrer la **QUEUE** que la règle protège — le flash d'intervention 2026 est
  **hors-échantillon** (le sim aurait enregistré « survie » le jour du breach). La protection de
  queue est un **jugement prospectif** (2 breaches + levcap Q4), pas un edge backtesté. Le
  Δqueue-gauche in-sample de GATE sera ≈ 0 par construction (les jours zone ≠ jours pires-gaps).

## Règle de gate (FROZEN — calculable depuis le seul close USD/JPY, causale T-1)
- **J1 OFF (suspension)** : `close(USDJPY) ≥ T_off`.
- **J1 ON (reprise)** : uniquement après `close(USDJPY) ≤ T_on` pendant **N jours ouvrés
  consécutifs** (`T_on < T_off`). → repli franc, JAMAIS reprise par cassure haussière (= moment
  de l'intervention).
- Machine à états **sans état persistant** (fonction déterministe de la série de close), puis
  `shift(1)` (décision du jour T n'utilise que les closes ≤ T-1), alignée aux dates M.
- **Paramètres gelés** : **T_off = 160.00**, **T_on = 155.00**, **N = 10**.
  Justification (prospectif) : 160 = ligne BoJ effectivement défendue (avril-2024), plus sûre que
  161.95 (aurait suspendu la position du breach bâtie à 161.8→162.5, que 161.95 aurait laissée
  passer) ; mord dans l'échantillon (17 j) donc coût mesurable. Reprise ≤155/10j = repli ~5 yen
  sous la ligne + confirmation 2 semaines, cohérent avec la persistance du régime.

## Arms (FROZEN)
1. **equiv** — clone baseline == `engine_v22.run_funnel`, tous cohorts ; doit reproduire pooled
   ≈ 87 / 462 cohorts (gate EQUIV, sinon STOP).
2. **baseline** — WT inchangé (instrumenté : records/events/margins).
3. **FULLOFF** — `WT[:,1] = 0` sur toutes dates. **Borne HAUTE du coût campagne** (gate toujours OFF).
4. **GATE160** — `WT[:,1] *= (1 − off_mask)`, off_mask = hystérésis(T_off=160, T_on=155, N=10).
   **Coût opérationnel réel.**
5. **GATE158** — idem T_off=158 (SENSIBILITÉ pré-enregistrée, PAS une sélection ; reporté à part).

Application : multiplicateur sur `WT[:,1]` en amont du funnel (réplique EXACTE de l'injection
live `weights["USDJPY"]=0` → `ea_w_usdjpy=0` → flatten J1 au 22:05). Aucun hook moteur, aucun
signal réimplémenté.

## Métriques (par arm)
- **Triplet** : `p_pooled` (challenge), `attempts`, `EV` (VAL=$1,422, FEE=$96 — convention v2.2/v2.3).
- **Queue gauche (PRIMARY)** : pire jour J1 ; pire gap week-end (`gap_pnl_jpy` min) ; part de
  busts J1-attribuables ; pire jour book.
- **Diversification** : book vol/jour ; part de risque J1 (cov(J1,book)/var(book)) ; marge p50/p99/bind.
- **Δ appariés vs baseline** : Δp, ΔEV, Δbust, Δgap — CI 90 % bootstrap bloc circulaire
  (blocs=10 cohorts, 3000 tirages, seed=23 — identique v2.3/levcap `aggregate.py`).

## Règle de décision (FROZEN — c'est un OVERLAY DE RISQUE, pas un maximiseur d'EV)
La suspension est un contrôle de risque PROSPECTIF contre une queue hors-modèle. Le backtest ne
peut que **REJETER** (trop cher) ou **DÉGAGER** (abordable) l'overlay — jamais **prouver** le
bénéfice. Donc :
1. **AFFORDABLE (cost gate)** : sur GATE160, Δp CI90 **PAS entièrement < −2.0 pts** ET ΔEV CI90
   **PAS entièrement < −$40**. (même tolérance asymétrique que levcap.)
2. **FULLOFF reporté** comme borne pire-cas (gate toujours OFF).
3. **Protection de queue** affirmée en PROSPECTIF via un replay du scénario breach (baseline J1
   16-18× vs gated J1=0, sous gap intervention −1/−2/−3 yen au notionnel live), **explicitement
   étiqueté jugement**, pas backtest.
- **Verdict = DÉPLOYER la suspension** ssi (1) tient (l'overlay est abordable) — la valeur de
  protection étant prospective. Si (1) échoue (même le gate opérationnel détruit p/EV de façon
  CI-significative), STOP et reporter : le coût de la diversif perdue dépasse le risque couvert.

## Comptabilité d'essais
+4 arms (equiv, baseline, FULLOFF, GATE160) + 1 sensibilité (GATE158). 1 règle de décision fixe,
0 arm post-hoc, seuils gelés ci-dessus. Ce n'est pas un nouvel alpha (overlay de risque sur book
existant) → ne consomme pas le ledger n_tests alpha ; noté au programme FTMO. **DSR/multiple-
testing** : un seul seuil opérationnel pré-enregistré (pas de sweep-sélection) ; GATE158 = borne
de sensibilité, pas un candidat concurrent.

**FROZEN. Toute modification après le premier run de résultats invalide cette pré-registration.**
