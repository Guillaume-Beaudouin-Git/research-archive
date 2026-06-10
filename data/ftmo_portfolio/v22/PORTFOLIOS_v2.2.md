# PORTEFEUILLES FTMO v2.2 — RE-RUN CONTRACTUEL
*2026-06-10 · Stack v2.1 corrigé (cleanroom audit + patch deadlock), gelé. CHAQUE chiffre
régénéré dans ce run — rien d'hérité des documents v2.0/v2.1. CIs = block-bootstrap
(blocs 10 cohortes), N_eff affiché. Code : `v22/` (config_v22.py = spec exécutable).*

## SPEC DIFF vs v2.1 — UN SEUL ITEM (gelé)

> **CHALLENGE : ORB OFF comme sleeve P&L → MICRO-ORB compteur de jours.**
> 0.01 lot US100, entrée ORB canonique (16:05-16:10 Paris), règles de sortie V2+E7
> normales, pris tout jour SANS autre trade ouvert à 21:30 CET (en moteur : flag
> `opened` à la pose 22:05, état ≤21:30). P&L modélisé : risk$ = 0.01 lot × or_range
> ≈ $0.2-2.0/trade, P&L = risk$ × R_era. Backstop moteur (patch v2.1, $1) maintenu
> pour les jours sans signal — 50 déclenchements sur ~13k jours-tentatives.
> **FUNDED : inchangé** (ORB ON 0.25% taper, vm 1.0) ; switch au funding. Coût ORB
> funded **PARAMÉTRÉ** (`ORB_RT_BPS` dans config_v22.py, défaut "era") — le verdict
> démo N=60 = changement d'une ligne + re-run de l'étape funded seule.
> Hors périmètre (réservé v2.3) : resize J1, tout autre paramètre.

## CHIFFRES CONTRACTUELS v2.2

### Challenge — funnel 91 jours (retries+abandon ; n=462 step-7, N_eff=174)

| Métrique | IS 2013-19 | OOS 2020-26 | Pooled |
|---|---:|---:|---:|
| **p(funded ≤ 3 mois)** | **90.6%** | **83.4%** | **87.0% — IC95 [82.3 ; 91.6]** |
| Essais (espérance) | — | — | 3.24 |
| Temps médian de funding | 35 j | 29 j | — |
| Micro-ORB | — | — | 9,248 poses ; 100% des cohortes ≥1 ; backstop 50 |

### CDF (pooled, retries ; monotone ✓)

| mur | 30 j | 61 j | **91 j** | 182 j | 270 j |
|---|---:|---:|---:|---:|---:|
| p | 41.6% | 70.3% | **87.0%** | 98.9% | 100.0% |

### Funded — extraction 2 ans, vm 1.0 (config inchangée, régénérée ; wd14, ORB_RT_BPS=era)

| | IS (n=93) | OOS (n=98) |
|---|---:|---:|
| E[extraction brute] | $684 | **$2,632** |
| médiane | $135 | $2,208 |
| bust | 3.2% | 1.0% |
| payouts | 3.3 | 10.8 |

### Chaîne EV (valeur funded RE-DÉRIVÉE, pas héritée)

| | Valeur |
|---|---:|
| Extraction pooled (IS+OOS)/2 | $1,658 |
| **VAL = refund $96 + 0.8 × extraction** | **$1,422** |
| **EV / campagne = 0.870 × $1,422 − 3.24 × $96** | **+$926** |
| Sensibilité ORB funded (audit C40) : ORB@3bps / ORB-mort | ≈ +$745 / ≈ +$310 |

### Robustesse (tout régénéré sur le spec v2.2)

| Test | Résultat | Lecture |
|---|---|---|
| Placebo cost-symmetric (flip pré-coût) | 71.2% → **edge +15.8 pts** | container 71 pts domine ; edge réel des jambes |
| Anticausal −1j | 83.1% < 87.0% (−3.9) | **aucun leak** ✓ |
| Path-bootstrap 78 histoires (blocs 13 sem.) | **moyenne 87.6, p5 76.7, min 71.4, P(p>50%)=100%** | single-history OK (min v2.0 était 62.9) |
| Swap ×1.5 / Spread ×2 | 86.4% / 77.9% | pas de falaise |
| Marge pré-cap | p50 21% / p99 79% / max 116% ; cap mord 5.6% | ≈ v2.1 ✓ |
| Gap weekend ×1.5 / ×2 (rule-check) | 84.9% / 85.1% | −2 pts, borné |
| vm sweep 10/12/**13/15**/16/18 | 84.2 / 83.8 / **86.2 / 87.7** / 84.4 / 84.6 | plateau lisse autour de vm14 (87.0) ; deltas appariés vs vm14 TOUS CI95 ⊃ 0 (ex. vm12 −3.2 [−9.3;+2.8]) — provenance vérifiée (runs v2.2 frais, colonne micro), vm13/15 = diagnostic post-résidu |

### Notes de lecture (honnêteté)
1. Le micro-ORB coûte **−1.3 pt** vs le compteur $1 idéalisé (87.0 vs 88.3 backstop-only,
   runner-equivalence vérifiée à la décimale) : dip de règle 1.31R sur ~$1-2.6 + bruit P&L
   ±$2/j + timing min-4-jours. C'est le prix de la version IMPLÉMENTABLE du compteur ;
   88.3 reste la borne haute théorique.
2. IS>OOS (90.6 vs 83.4) — l'écart de régime persiste ; le pooled 87.0 est le chiffre
   défendable, l'IC95 [82.3;91.6] couvre les deux.
3. Conventions EV maintenues : fee $96 ; VAL re-dérivée $1,422 (l'ancien $1,453 surestimait
   de ~$30 ; le label v2.0 "$1,342" reste faux — cf. audit C04).
4. Gates live INCHANGÉS (audit BLOCKED) : test swap overnight, démo 3 sem. fills ACTIFS
   16:00-16:30 (≥60 trades, gate du paramètre ORB_RT_BPS funded), EA + réconciliation,
   budget 4+ fees, clause 7.3.

*Tables : v22/tables/*.csv. Reproduction : `python3 run_battery.py` puis
`python3 run_pathboot.py` (lecture seule hors v22/).*

**Spec exécutable (gel EA)** : `spec_v22.yaml`, GÉNÉRÉ depuis `config_v22.py` par
`make_spec_yaml.py` (byte-identique, sha256 en ancre #19 — ne jamais éditer à la main).
Baseline épinglée : `605f4a42…` + `4e1bac5c…` (remplace toute référence baseline v2.1).
Le compteur de jours de l'EA = la règle MICRO-ORB du yaml (sémantique 605f4a4), pas un
token arbitraire ; le backstop no-signal y est spécifié séparément (incidence sim 50/13k).
