# Rapport stratégie {{NNN}}/109 — {{NOM STRATÉGIE}}

**Projet :** filtrage systématique des 109 revues oxfordstrat.com sur l'univers FTMO.
**But :** permettre à l'équipe de **reproduire**, **auditer** et **contredire** le test.
**Pipeline :** `ftmo_lab v2-gates` — **KEEP impossible sans passer les 4 gates constitutionnels (§8).**
**Statut :** {{KEEP / BORDERLINE / DISCARD}} · **Source :** {{URL oxfordstrat}} (rating site : {{A/B/C/D}}).

> ⚠️ Règle de verdict (non négociable) : un edge positif après coûts est **nécessaire mais NON suffisant**.
> Le verdict **KEEP** n'est prononcé que si : `edge_net > 0` **ET** Gate 1 (délai+1) **ET** Gate 2 (two-sided)
> **ET** Gate 3 (DSR) **ET** Gate 4 (OOS) passent. Sinon **DISCARD** (ou **BORDERLINE** si 4/4 OK mais Sharpe faible).

---

## 0. Résumé exécutif
| Élément | Valeur |
|---|---|
| Univers testé | {{n}}/40 instruments |
| Période | {{spans}} |
| Coûts | spread réel + commission specs + slippage (méd. {{x}} bps round-turn) |
| Point de référence | {{params}} → expR {{x}} · PF {{x}} · Sharpe {{x}} |
| **Gates (4/4 requis)** | **{{n_pass}}/4 PASS** |
| **VERDICT** | **{{KEEP / BORDERLINE / DISCARD}}** — {{raison}} |

## 1. Spécification originale (reproduite fidèlement)
{{Développeur, source, concept, setup, entrée, sorties, paramètres du site. Écarts assumés vs site + raison.}}

## 2. Univers et données
{{Instruments couverts par classe, source OHLC, période, manquants. Conventions (frontière de bougie, etc.). Régénération : `python code/build_ohlc_store.py`.}}

## 3. Pré-traitement des signaux (sans look-ahead)
{{Définition formelle des signaux. Justifier l'absence de look-ahead : signal calculé ≤ barre de décision, entrée à la barre suivante.}}

## 4. Modèle de coûts FTMO
{{Reprendre `round_turn_cost_bps` de ftmo_lab : spread (M1) + commission (specs) + slippage, plancher par classe. Coûts effectifs min/méd/max.}}

## 5. Moteur de backtest et hypothèses
{{Type de moteur (bracket event-driven `simulate_bracket`, ou position-based). Normalisation du risque (R-multiples, RISK_FRAC). Hypothèses intrabar (toutes conservatrices). Métriques.}}

## 6. Paramètres
{{Point de référence + grille de balayage (N cellules — noter N, sert au Gate DSR).}}

## 7. Résultats (mesure brute, fill optimiste)
{{Point de référence : trades/win/expR/PF/Sharpe/CAGR/MaxDD. Par instrument (top/bottom). Heatmap de sensibilité. ⚠️ Ces chiffres sont la MESURE ; le verdict dépend des gates §8.}}

---

## 8. GATES CONSTITUTIONNELS (OBLIGATOIRE — dans le test principal, pas en annexe)

Appel unique dans le code : `res = ftmo_lab.run_gates(make_run(params), sharpe_grid, split='2015-12-31')`.
`make_run(params)` renvoie une fonction `run(fill=...)` qui produit les trades poolés de l'univers ;
`sharpe_grid` = Sharpe par cellule du balayage (N essais).

| # | Gate (loi) | Test | Critère FAIL | Résultat | Verdict |
|---|---|---|---|---|---|
| 1 | **Délai+1 / fill réaliste (L26)** | re-fill à `next_open` (ou `close`) au lieu du niveau de stop intrabar | edge s'effondre/inverse (expR≤0 ou Sharpe≤0) → *artefact de fill intrabar* | opt Sh {{x}} → réel {{x}} | {{PASS/FAIL}} |
| 2 | **Two-sided (L25)** | split longs vs shorts | un côté porte >70% du PnL positif ET l'autre expR≤0 → *beta déguisé* (+ re-test vs buy&hold timé) | long {{x}} / short {{x}}, contrib {{x}}% | {{PASS/FAIL}} |
| 3 | **DSR (multiple testing)** | Deflated Sharpe Bailey-LdP, n_trials = N cellules | `SR_obs < E[max bruit]` (DSR_z<0) → *grille = bruit* | SR_obs {{x}} vs E[max] {{x}}, z={{x}} | {{PASS/FAIL}} |
| 4 | **OOS (L31)** | split entrée ≤2015 / ≥2016 | flip de signe ou test expR≤0 → *régime-dépendant / décayé* | train {{x}} → test {{x}} | {{PASS/FAIL}} |

**Gates FAIL : {{n}}/4.**

### 8.1 Lecture de chaque gate
- **Gate 1 (délai+1)** — *le plus décisif.* {{Interprétation : l'edge survit-il à un prix d'exécution réaliste ? Si non, c'est un artefact d'exécution, pas un signal.}}
- **Gate 2 (two-sided)** — {{Symétrie long/short. Si l'edge est mono-directionnel sur un univers qui a trendé → beta déguisé, pas un mécanisme robuste.}}
- **Gate 3 (DSR)** — {{Le « 100% positif / best cell » est-il compatible avec N tirages de bruit ? E[max] de N essais.}}
- **Gate 4 (OOS)** — {{L'edge tient-il hors échantillon / change de régime ?}}

### 8.2 Verdict final (règle stricte)
`KEEP` ⇔ edge_net>0 ET Gate1 ET Gate2 ET Gate3 ET Gate4. `BORDERLINE` ⇔ 4/4 OK mais Sharpe<0,5.
Sinon `DISCARD` avec tags. **Ici : {{VERDICT}} — {{raison}}.**

---

## 9. Limites connues & checklist d'audit complémentaire
{{Gates additionnels non bloquants mais recommandés : cost-stress ×1,5/×2 (L33), block-bootstrap 95% CI, sensibilité frontière de bougie, `≤`/`<`, petits échantillons. Limites structurelles.}}

## 10. Reproduction
{{Environnement figé. Ordre d'exécution : `build_ohlc_store.py` (optionnel) → `strat_s{{NNN}}_*.py`. Sorties attendues (console gates + verdict, csv gates, heatmap).}}

## Annexe A — `code/ftmo_lab.py` (moteur + 4 gates, partagé)
{{Listing intégral ou référence — inchangé d'une stratégie à l'autre.}}

## Annexe B — `code/strat_s{{NNN}}_*.py`
{{Listing intégral du fichier stratégie (signaux + run + appel run_gates + heatmap).}}

---
*Template v2-gates. Une stratégie n'est KEEP que si elle survit aux 4 gates. Le moteur et le store OHLC sont partagés ; seul `strat_s{{NNN}}_*.py` + ce rapport sont produits par stratégie.*
