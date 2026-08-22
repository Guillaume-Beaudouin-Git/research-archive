# FTMO — Classe 3 (stat-arb pairs) & carte 5-classes : entrée de log (CANDIDAT À MERGER)
*2026-06-03. Périmètre tenu : rien touché côté `data/trend_research/` ni section trend.
Candidats-leçons NOMMÉS (numérotation tranchée au merge contre CLAUDE.md).*

## Réconciliation archive (avant de relancer #3)
J'allais relancer les paires d'indices intraday en croyant « jamais testé en frais ». **Faux** :
`ftmo_research/statarb_deepdive_ftmo.md` les a déjà couvertes (18 pairs, données intraday/horaires,
ADF train/test + half-life + financing + two-sided). Chiffres durs :

| pair | ret_corr | EG_p OOS | half-life | lecture |
|---|---:|---:|---:|---|
| US100/US500 | 0,93 | 0,43 ✗ | 39 j | casse OOS |
| US500/US30 | 0,89 | 0,043 ✓ | 24 j | OOS-stable mais multi-semaine |
| US100/US30 | 0,76 | 0,035 ✓ | 37 j | OOS-stable mais multi-semaine |

GATE-0 tranché : la cointégration **existe** (2 pairs OOS) mais **half-life 24-39 jours = PAS intraday**.
Cost-gate (L28) : ~21 bps financing + 4 bps 2-jambes ≈ **25 bps** > réversion 8-31 bps → net ≈ 0/neg.
Two-sided (L27) : spread US100/US30 long +79 / short −61 = **drift relatif**, pas réversion. Best t +1,18 < 2,78.
→ **#3 = clos. Re-rouler = re-prouver du clos. STOP.** (= ex-Strategy D rejoué sur indices.)

## Candidats-leçons
> **LESSON-CANDIDATE: index-pairs-not-intraday-cointegrated** — les paires d'indices ont une half-life de
> réversion **24-39 jours** (multi-semaine), donc forcément multi-jour → le financing CFD **2× markup
> (L28)** les tue, et le spread est un **drift relatif (L27)**, pas une réversion two-sided. N'admettre
> une paire que si half-life < horizon intraday tenable **ET** OOS-cointégrée **ET** two-sided **ET**
> nette de 2-leg cost+financing.

> **LESSON-CANDIDATE: reconcile-archive-before-claiming-untested** — toujours grep l'archive avant de
> revendiquer « jamais testé » ; a évité ici de re-prouver du clos (#3).

## Carte 5-classes — état réel (épuisée dans l'univers FTMO liquide + données gratuites)
| # | Classe | Statut | Verdict |
|---|---|---|---|
| 1 | Mean-reversion intraday (VWAP/OR-fade) | TUÉE | VWAP-MR net −0,5 à −1,5 bps/trade, SR<0 (cost-killed) |
| 2 | ORB / momentum intraday | TUÉE/CLOSE | full-hist SR 0,11, flip négatif à 2-3 bps (L33), beta (L25) |
| 3 | Stat-arb / pairs (cointégration) | CLOSE | half-life 24-39j non-intraday + financing-killed (L28) + drift relatif (L27) |
| 4 | Scalping order-flow / microstructure | NON-FAISABLE | besoin tick/L2 ; M1 seulement |
| 5 | Session / time-of-day + vol-targeting | TUÉE | seasonality = bruit ; overnight = beta-proxy (SR 0,68<0,70) + gap-tail |

Fronts restants = hors-menu (tick/L2, term-structure payante) = « leads restants » du canonique.
Les VARIATIONS fines restent à explorer (cf. session de recherche en cours) — négatifs rigoureux = livrables.
