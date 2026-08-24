# ÉTUDE — ASIA_23_8 en FUNDED-only avec stop intraday

**Date :** 2026-06-19 · **Branche :** `claude/asia-23-8-funded` · **Statut :** RECHERCHE PURE
**Pré-registration :** `PREREGISTRATION_FUNDED.md` (committée AVANT résultats, commit `7dd6f56`)
**Suite de :** `STUDY_ASIA_23_8_FTMO_2026-06-19.md` (challenge = NON-VIABLE, acquis)
**Cadre :** sandboxé. AUCUN déploiement, AUCUN toucher au book live. Lecture seule.
**Discipline anti-sur-recherche :** 4 variantes (sur 5 max), K=1 fixé a priori, **DSR n_trials=100**.

---

## VERDICT — (c) REJET (survit + edge en standalone, mais aucun apport au book funded)

Résultat plus riche que le challenge. **La bonne nouvelle :** sans cible, ASIA_23_8 **survit en funded
ET garde son edge** — le stop intraday à −2.5 % NE mange PAS l'alpha (hypothèse réfutée). **Le problème :**
elle n'a **aucun chemin de déploiement funded** :

1. **Pas de compte funded propre** : elle échoue le challenge en standalone (étude précédente : 35 % max,
   EV négatif) → on ne peut jamais atteindre un compte funded ASIA-seul.
2. **Ajoutée au book funded** (seule voie réaliste, façon ORB ON-funded), elle **détruit la survie du
   book** : **98.6 % → 69.0 %** (K=1, Δ−29.7 pt) — **75.2 % même à K=0.5** (Δ−23.4 pt) — malgré un Sharpe
   funded en hausse (0.43→0.74). C'est l'effet **L24 en contexte funded** : la survie est gouvernée par le
   **drawdown absolu vs le floor statique −10 %**, PAS par le Sharpe ; greffer une sleeve à 6.8 % de vol
   empile du drawdown contre la barrière et multiplie les percements.

**L'analogie ORB échoue** : ORB ON-funded est un micro-ajout intraday-flat (0.25 % de risque) ; ASIA est
une sleeve always-on pleine-vol dont le **saignement de régime-mort** (2018, ~−15 %) busterait le floor.

**Recommandation :** ne PAS intégrer ASIA_23_8 au book funded. La viabilité standalone-funded est réelle
mais inaccessible (challenge-bloquée) et marginale (survie 92.4 % = 7.6 %/an de perte de compte, +$690/an).

---

## Q1 — Format funded (pas de cible), sans stop

ASIA standalone (book OFF), K=1, moteur funded v2.2 audité (pas de cible ; daily −5 %, floor statique
−10 % ; retraits 14 j ; **cohortes mensuelles 2013-2025 incluant le régime-mort 2018-19**) :

| | p(survie 6m) | p(survie 12m) | rendt annu net | DD pire |
|---|--:|--:|--:|--:|
| **V_nostop** | 92.5 % | **84.1 %** | +6.6 % | −13.4 % |

Sans cible, la lenteur cesse d'être un handicap (✓ l'intuition). MAIS la survie 12 m n'est que **84.1 %** :
deux tueurs subsistent — (i) le **percement intraday du daily −5 %** (les rares jours à plus-bas −5 à −7.7 %),
(ii) le **saignement multi-mois vers le floor −10 %** en régime-mort (DD pire −13.4 % < −10 % → bust).
Le stop (Q2) adresse (i), pas (ii).

## Q2 — Stop intraday : survie ↑ ET l'edge SURVIT (hypothèse d'érosion réfutée)

Stop dur −X % (fraction de compte) ; sortie si la position franchit −X % intraday. `n_trials DSR = 100` :

| variante | trig % | Sharpe | OOS | **DSR(100)** | p(surv 6m) | **p(surv 12m)** | rendt | DD pire | alpha rendu / protection |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| no-stop | 0.0 | 1.14 | 1.00 | 0.99 | 92.5 % | 84.1 % | +6.6 % | −13.4 % | — |
| stop −1.5 % | 0.8 | 1.08 | 0.95 | 0.99 | 95.9 % | 91.7 % | +6.8 % | −10.9 % | **17.4 % / 9.2 %** (érode) |
| **stop −2.5 %** | 0.1 | **1.12** | 1.00 | **0.99** | 96.6 % | **92.4 %** | +6.9 % | −11.1 % | 2.7 % / 1.6 % (négligeable) |
| stop −3.5 % | 0.0 | 1.12 | 1.00 | 0.99 | 95.9 % | 89.7 % | +6.8 % | −11.1 % | 1.6 % / 0.3 % (négligeable) |

**Lecture (le point qui décide).**
- **L'hypothèse « le stop mange l'alpha » est RÉFUTÉE à −2.5 % et −3.5 %** : le stop ne se déclenche que
  0.0–0.1 % des jours (le plus-bas intraday atteint rarement −2.5 %), Sharpe 1.12 (vs 1.14 sans stop),
  OOS 1.00, **DSR 0.99 à n_trials=100**. L'edge SURVIT. À −1.5 % le stop se déclenche plus (0.8 %) et
  érode (alpha rendu 17.4 % > protection 9.2 % → Sharpe 1.08) — la mécanique « sortie sur bougie qui se
  retourne » existe mais seulement au niveau serré. Le point exact où l'edge s'efface : **entre −1.5 % et
  −2.5 %** (à −2.5 % l'érosion devient négligeable).
- **Le stop relève la survie 84.1 % → 92.4 %** (−2.5 %) en coupant les rares jours à excursion ≥ −5 %.
- **Au seuil pré-enregistré standalone** (p survie 12m ≥ 0.90 ET Sharpe ≥ 0.70 ET DSR ≥ 0.90) :
  **−2.5 % PASSE** (92.4 % / 1.12 / 0.99) et −1.5 % aussi (91.7 % / 1.08 / 0.99) ; −3.5 % à 89.7 % (limite).
  **Le meilleur niveau = −2.5 %** (survie max + Sharpe top, érosion nulle).

**Sensibilité K (risk-scaling seul, Sharpe ~invariant — PAS une recherche d'edge) :**

| | p(surv 12m) | rendt annu net | DD pire |
|---|--:|--:|--:|
| K=0.5 (no-stop / stop −2.5) | 100 % / 100 % | +1.7 % | −4.5 % |
| K=1.0 (stop −2.5) | 92.4 % | +6.9 % | −11.1 % |
| K=1.5 (no-stop / stop −2.5) | 31.0 % / 33.8 % | +12.1 / +12.7 % | −26.7 / −13.0 % |

K=1 est le point d'équilibre (survie 92 %, +6.9 %). K=1.5 buste (le bleed ×1.5 perce −10 %). K=0.5 survit
à 100 % mais rendement trivial (+1.7 %). K=1 fixé a priori = bien calibré.

## Q3 — Apport au book funded : DILUTION SÉVÈRE de la survie

Ablation funded (book CFG_FUNDED : gold_trend ON, ORB ON, vm=1) ± ASIA stoppée −2.5 %, cohortes 12 m :

| config | p(survie 12m) | Δ | rendt annu net | Sharpe funded | DD pire |
|---|--:|--:|--:|--:|--:|
| **book seul** | **98.6 %** | — | +9.6 % | 0.43 | −13.6 % |
| book + ASIA (K=1.0) | **69.0 %** | **−29.7** | +13.6 % | 0.74 (Δ+0.32) | −15.2 % |
| book + ASIA (K=0.5) | 75.2 % | **−23.4** | +10.0 % | — | −11.6 % |

- **L'ajout d'ASIA effondre la survie funded du book** : 98.6 % → 69.0 % (K=1), 75.2 % (K=0.5). Δ de −23 à
  −30 pt = **très au-delà du bruit** (le book seul est à 98.6 %). À K=0.5, le rendement n'augmente quasi
  pas (+10.0 % vs +9.6 %) mais la survie chute quand même de 23 pt → **dilutif à toute taille**.
- **Pourquoi (L24 funded)** : le book funded à vm=1 est très peu risqué (DD −13.6 %, Sharpe 0.43, survie
  98.6 %). Greffer une sleeve à 6.8 % de vol **double le risque absolu** → bien plus de percements du floor
  STATIQUE −10 %, **même si le Sharpe monte** (0.43→0.74, diversification réelle). La survie d'un compte
  funded est gouvernée par le **drawdown absolu vs barrière**, pas par le Sharpe.
- **ρ(ASIA, gold_trend) = 0.085** (décorrélée — d'où le gain de Sharpe) ; **marge métal funded p99 0.355 <
  cap 0.60** (PAS de problème de marge en funded vm=1, contrairement au challenge vm=14). Donc la dilution
  vient du floor statique, pas de la marge ni de la corrélation.

## Synthèse — pourquoi (c) REJET et pas (a)

Le seuil pré-enregistré **SURVIE** exigeait « p(survie 12m) ≥ 0.90 **ET ne réduit pas la survie du book
funded** ». ASIA −2.5 % passe la 1re clause (92.4 %) mais **échoue la 2nde** (−29.7 pt). L'**EDGE est
préservé** (Sharpe 1.12, DSR 0.99) → ce n'est **PAS (b)** « le stop mange l'edge » (réfuté). C'est **(c)
REJET** : survit + edge en standalone, mais **aucun apport au book** (dilution sévère de la survie) — et
**aucun chemin d'accès indépendant** (challenge-bloquée). *Probité author≠auditor : verdict rendu sans
déplacer aucun seuil ; aucune 5e/6e variante testée (budget 4/5).*

**Nuance honnête.** Le résultat standalone-funded est genuinement bon (survie 92.4 %, edge intact post-stop,
post-DSR à n=100) — c'est la découverte de l'étude, et elle distingue le funded du challenge. Mais un compte
funded ASIA-seul nécessiterait de **passer le challenge avec une AUTRE stratégie puis basculer** (convoluté,
fragile) pour un gain marginal (+$690/an/compte, 7.6 %/an de risque de perte du compte). Et la voie réaliste
(ON le book funded) est nettement dilutive. → pas de cas d'intégration.

### Candidat de leçon (NOMMÉ, non gravé — réconciliation ultérieure)
**« funded-survival-is-drawdown-governed-not-Sharpe »** : sur un compte funded à floor statique, une sleeve
décorrélée **à Sharpe positif** peut DÉTRUIRE la survie en empilant du drawdown absolu contre la barrière
(book 98.6 %→69 % en ajoutant une sleeve 6.8 %-vol, Sharpe pourtant +0.32). Extension de L24 au contexte
funded/intégration. Le test d'ajout d'une sleeve funded doit être la **survie**, pas le Sharpe.

---

## Reproductibilité
- Pré-registration : `PREREGISTRATION_FUNDED.md` (commit `7dd6f56`, avant résultats).
- Code : `code/asia_stop.py` (stop série-level, érosion quantifiée), `code/q_funded.py` ; réutilise
  `asia_inject.py` (run_funded patché + log équité ; run_phase INCHANGÉ → challenge toujours 87.01 vérifié),
  `asia_series.py`, `engine/stats.py` (DSR n_trials=100).
- Résultats : `results/q_funded.json`.
- Cohortes funded : mensuelles 2013-10→2025-06 (incluent 2018-19), horizons 126/252 j ; moteur funded v2.2
  (pas de cible, daily −5 %, floor statique −10 %, retraits 14 j split 0.8). Engine pin `605f4a4`.
- **Aucun fichier live touché.** Env `/usr/bin/python3`.
