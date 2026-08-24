# STUDY — Anatomie des busts FUNDED + décomposition cash-flow mensuelle

Pré-reg gelée `PREREGISTRATION.md` (commit `389f8b4`, AVANT résultats). Continuation de real_metrics.
Moteur canonique NON muté ; clone instrumenté `funded_anat_engine.py` validé **self-EQUIV** (382 runs,
0 divergence vs `LC.run_funded` audité). Baseline reproduit real_metrics (58 busts / 30.4 % / EV +$677).
Read-only, AUCUNE action live. Auteur : 2026-07-06. **Audit indépendant : voir AUDIT.md.**

## 0. Le fil rouge (une phrase)
Le tail funded n'est **PAS diffus** : ce sont **3–4 jours historiques** (13 ans), des franchissements
INTRA-BARRE MARGINAUX de la barrière QUOTIDIENNE −5 %, en vol calme → **les gates ciblés échouent
(vol basse, imprévisible)** mais **une réduction de sizing les efface** (marge $510 → ×0.85 = sous
$500). La money-management EST le levier au stade funded (à l'inverse du challenge, L35).

## 1. Volet 1 — Anatomie (baseline gate ON, low-check, vm1 ; 191 runs, 58 busts, **3–4 jours uniques**)
| dimension | résultat |
|---|---|
| **daily vs max-loss** | **98.3 % DAILY** (−5 %), 1.7 % max-loss. Médiane perte-jour **$510** (≈ la barrière $500 → MARGINAL) |
| **par sleeve (dom-leg)** | USDJPY 36 (2 jours) · XAUUSD 22 (1 jour). = 2 jours JPY + 1 jour OR |
| **type** | **100 % INTRADAY** (0 % à l'ouverture/gap), 6.9 % sur jour post-week-end |
| **régime** | **vol BASSE** : percentile vol 20 j du dom-leg au bust ≈ **0.32 / 0.32 / 0.36** (médian 0.36), **0 % > p80** → calme-puis-choc |
| **timing** | life médian **169 j** (q25 89, q75 254, min 1) ; **93 % ont ≥1 payout banké** (médian 6, $1 161) |
| **jours uniques** | **2015-08-24** (JPY, flash déval. Chine) · **2021-01-07** (OR, reflation post-Georgia) · **2023-12-07** (JPY, pivot BoJ). **Step 6 (pré-reg) ajoute 2016-11-09** (nuit électorale US, max_loss faible $310) → **3 au step 12, 4 au step 6** (converge à 4). Tous HORS zone gate. |

**Lecture** : le tail = 3–4 chocs intraday marginaux (perte-jour ~$510, à peine sous la barrière $500),
en vol calme, hors zone gate, tardifs (l'essentiel des retraits déjà banké → dégât $ borné). ⚠️ **N=3–4
événements uniques** — le pattern est net mais repose sur peu de jours. La perte-jour $510 est une
BORNE HAUTE (low-check surestime : liq FTMO ≈ $500, pas $510) → détections « knife-edge ».

> **⚠️ Déviation pré-reg (déclarée, audit) :** la pré-reg §1 spécifiait `FUNDED_STEP=6` pour la
> couverture de l'anatomie ; `run_all_funded.py` a tourné en **step 12** (les overlays Volet 2 restent
> en step 12, grille FUNDED_WINDOWS canonique). Re-run step 6 (`run_baseline_s6.py`) → **4 jours uniques**
> (ajoute 2016-11-09) ; taux/EV density-stables (vérifié audit + step 3 converge à 4). Headline « 3 »
> corrigé en « **3–4** ». Le pattern (daily/marginal/intraday/vol-basse) est inchangé.

## 2. Volet 2 — Réductibilité (funded-only, gate ON de base ; Δ apparié, block-boot seed23)
| overlay | bust % | Δbust (pp) [CI90] | EV | ΔEV | conversion | verdict |
|---|---|---|---|---|---|---|
| baseline vm1 | 30.4 (58) | — | +$677 | — | — | — |
| **gold vol-gate** p80 | 30.4 (58) | +0.0 [−1.0,+1.0] | +$715 | +$38 | saved 1 = harmed 1 | **ÉCHEC (net-0)** |
| **jpy vol-gate** p80 | 34.0 (65) | +3.7 [+0.0,+9.4] | +$548 | **−$130** | saved 0, harmed 7 | **NUISIBLE** |
| **vm 0.85** | **2.1 (4)** | **−28.3 [−44,−14]** | **+$834** | **+$157** | **saved 55**, harmed 1 | **CONVERSION, Pareto-dominant** |
| vm 0.70 | 0.0 (0) | −30.4 [−45,−16] | +$701 | +$24 | saved 58 | conversion |
| vm 0.50 | 0.0 (0) | −30.4 [−45,−16] | +$660 | −$18 | saved 58 | conversion (sur-de-lever) |

- **Les gates ciblés échouent** — mécanisme PROUVÉ Volet 1 : les 3 jours sont en **vol basse** (0 %>p80)
  → un gate sur vol réalisée trailing ne s'arme JAMAIS dessus. Le gold-gate est net-0 (change la
  trajectoire, saved 1 = harmed 1) ; le jpy-gate est nuisible (retire le carry/trend JPY → −$130 EV
  + 7 busts créés). Suspendre 616/627 jours de vol haute n'attrape aucun des 3 jours de choc.
- **Le sizing EST le levier** : vm0.85 **convertit 55/58 busts en survie** (Δbust CI exclut 0) **ET**
  augmente l'EV +$157 → **Pareto-dominant**. Raison : la perte-jour est marginale ($510) ; ×0.85 =
  $433 < $500 → sous la barrière. Conversion (busts éliminés), pas magnitude. vm0.70 efface TOUT le
  tail (+$24) ; vm0.50 sur-de-lève (−$18).
- **⚠️ vm — SIGNALÉ, NON TRANCHÉ (per pré-reg + consigne).** Signal fort : **funded vm1 est sur-sizé** ;
  ~−15 % de sizing (≈vm0.85) efface l'essentiel du tail à EV positif. C'est un candidat de décision
  FUTURE explicite (analogue au flag vm14 challenge). Robustesse : la DIRECTION (de-lever ↓ tail) est
  solide ; le seuil exact 0.85 dépend de la calibration low-check (busts knife-edge $510).

## 3. Volet 3 — Cash-flow mensuel (MC entreprise 24 mois, 20 000 tirages, seed23)
Assemblage : fees challenge (−$96 × 3.29 essais/campagne, re-purchase) → payouts funded (split 80 %,
bi-weekly, +$96 refund au 1er payout/compte) → re-acquisition sur bust funded.

| métrique (BASE vm1) | valeur |
|---|---|
| **break-even** (cumul>0) | **médian mois 5** (p10 mois 2, p90 mois 16) ; **31 % jamais < 24 mois** |
| cumul cash @24 mois | médian **+$522** (p10 −$646, p90 +$3 173) ; **P(>0)=66 %** |
| **$/mois en régime funded** | médian **$197** (p10 $0, p90 $400) |
| profil | mois 1 = −$315 (fees), puis +$40–70/mois une fois funded |

- **Scaling (+25 %/4 mois si ≥2 payouts)** : break-even inchangé (5) ; cumul @24 mois **+$714** médian
  (p90 +$5 319) ; **aide l'UPSIDE, pas le downside ni le break-even** (le scaling ne protège pas contre
  les 3 jours-tail ni les non-funders).
- **vm0.85 funded (lien Volet 2→3)** : cumul @24 mois médian **+$732** (vs +$522, **+40 %**), P(>0)
  **69 %** (vs 66 %), downside p10 **−$511** (vs −$646) — **Pareto sur le cash-flow AUSSI** ($/mois
  ~inchangé $192, mais bien moins de morts funded → moins de re-acquisition). Le signal vm0.85
  améliore le tail ET la trésorerie.
- **Actualisation (0.5 %/mois)** : break-even nominal mois 9 (sur cash-flow MOYEN, tiré par les 31 %
  non-funders) == discounté mois 9 → **lecture INCHANGÉE** (immatériel sur 24 mois). NB : mois 5 =
  break-even du tirage MÉDIAN ; mois 9 = break-even du cumul MOYEN (écart = skew + non-funders).

**Lecture** : un compte $10k avec ce book = **~$200/mois médian en régime funded, break-even typique
~5 mois, mais 31–34 % de proba d'être non-positif à 24 mois** (fees + morts funded). Opération à
petit $, downside réel. Le levier de trésorerie = réduire les morts funded (→ vm0.85), pas le scaling.

## 4. Données (rétrospectif) vs jugement (prospectif)
- **DONNÉE** : anatomie (3 jours), échec gates / succès sizing, cash-flow — tout sur 2013-2026.
- **JUGEMENT** : (a) N=3 jours → l'anatomie décrit un pattern robuste mais rare ; un 4e jour futur
  hors-échantillon pourrait différer. (b) Le tail funded réel LIVE inclura des jours EN zone qu'un
  backtest 2013-2026 n'a pas (cf. les 2 breaches challenge 07-02/03) — le gate J1 les couvre
  (prospectif). (c) vm0.85 = signal robuste en direction, seuil à décider explicitement.

## 5. Anchors & validation
- **G-SELF-EQUIV** : `run_funded_anat` == `LC.run_funded` (busted/wd/payouts/life/residual) sur 382
  runs, 0 divergence. Moteur audité intact.
- **Baseline reproduit real_metrics** : 58 busts / 30.4 % / VAL $1 425 / EV +$677 (identique).
- Convention EV = challenge p_pass 0.697 × VAL − 3.29 × $96 (real_metrics swing_ON_low).

## 6. Caveats (gelés, hérités real_metrics + spécifiques)
Low-check DISCRET + **surestime la perte** (perte-jour $510 = borne haute ; liq réelle ≈ $500 → busts
knife-edge, les + sensibles aux hypothèses bid/M5 — 54/58 busts ∈ [$500,$520], seuil vm0.85 en dépend) ;
all-legs = borne haute (bracket dom-leg real_metrics) ; **N=3–4 jours uniques** (anatomie small-N) ;
couverture lo/hi US100 83.7 %/GER40 83.0 % (fallback conservateur) ; échantillon → 2026-06-05 (jours EN
zone type 07-02/03 hors-fenêtre, gate prospectif) ; cash-flow : hypothèses wd_every=14 td, split 80 %,
refund 1er payout/compte, fees lumpés en début de campagne (léger conservatisme sur le timing).

## 7. Audit indépendant (author≠auditor) — voir AUDIT.md
**VERDICT : CONFIRM-WITH-CAVEATS.** L'auditeur a re-dérivé chaque chiffre depuis les CSV bruts +
`panel_rets`, **re-lancé le self-EQUIV** (382 runs, 0 divergence), **re-lancé le moteur à 3 densités**,
et **ré-implémenté le MC cash-flow clean-room** — tout reproduit (baseline 58/30.37 %/EV +$677.3 ;
anatomie 98.3 % daily, médiane $509.5, 54/58 marginaux ∈[500,520], 4 profonds tous le 2015-08-24 ;
vm085 −28.3pp [−44,−13.6] excl. 0 ET +$156.5 EV réel via E[extr] 1661→1942, saved 55/harmed 1 ;
cash-flow BE 5 / 31.2 % never / cum24 $522 (moyenne $907≈1.43×EV) / vm085 $730). **Corrections
appliquées** : (a) déviation step 12→6 déclarée (§1, « 3–4 jours ») ; (b) label swap corrigé
(2015-08-24=JPY, 2021-01-07=OR) ; (c) volpct 0.00 = artefact NaN jour férié → robuste 0.32 (§1). Réserves
d'audit (toutes déclarées) : small-N 3–4 j ; vm0.85 = seuil knife-edge low-check (dépend de la
sur-estimation ~$10) ; gate prospectif (échantillon → 06-05). vm **SIGNALÉ, non tranché** (conforme).
