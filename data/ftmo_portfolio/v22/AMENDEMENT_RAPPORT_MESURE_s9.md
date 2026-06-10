# AMENDEMENT §9 — RAPPORT_MESURE_us100_execution_cost_v1 (re-scope v2.2, commit 605f4a4)
*2026-06-10 soir. Le fichier hôte (`RAPPORT_MESURE_us100_execution_cost_v1.md`, rapport équipe,
interim n=15/60, verdict lundi 15/06) n'est PAS présent dans ce repo (workspace équipe — vérifié
par find/grep ; seule sa synthèse vit dans `data/ftmo_portfolio/PORTFOLIOS.md`). Cet amendement
est donc consigné ICI canoniquement, cité dans FTMO_CANONICAL_STATE.md, et DOIT être inséré
verbatim au §9 du fichier hôte à la prochaine synchro. Pas de dérive silencieuse : l'arbre de
décision ci-dessous REMPLACE explicitement l'arbre pré-enregistré.*

## §9 PRÉ-ENREGISTRÉ (rappel, version v1)
- ≤ 1.0 bps all-in RT (N=60, fills actifs 16:00-16:30) → ré-ancrage du coût ORB ;
- > 1.5 bps → **KILL : ORB off** (mécanique v2.0 — où « ORB off » détruisait le challenge).

## §9 AMENDÉ (v2.2 — la branche kill est RETIRÉE)
La v2.2 (commit `605f4a4`) sort l'ORB du challenge : micro-ORB compteur de jours, P&L ORB nul
dans P1/P2, **le challenge est insensible au coût ORB par construction** (ancres de
non-régression #1-3/#6-13 : toute dérive du challenge après changement d'ORB_RT_BPS = bug →
STOP). **L'ORB ne peut plus tuer le challenge.** Le verdict N=60 devient :

> **mesure all-in RT (N=60) → `config_v22.py: ORB_RT_BPS = <valeur mesurée>` → re-run de la
> SECTION FUNDED uniquement → EV de campagne rapportée à la valeur mesurée.**

Aucun seuil de kill côté challenge. Côté funded, pas de kill non plus : l'EV reste positive sur
tout le domaine (plancher ORB-mort ≈ +$295-310) ; la mesure ne fait que POSITIONNER l'EV.

## Branches N=60 — RERUN EXACT SUR LEDGER (remplace l'approximation shift 0.0225 R/bps)
*ftmo_research/ est monté dans cette session — le « rerun exact au remontage » pendant dans
PORTFOLIOS.md est fait. Funded 2 ans, vm 1.0, wd14 ; EV chaîne au challenge v2.2 (87.0%, 3.24
essais, fee $96, VAL = 96 + 0.8 × extraction pooled (IS+OOS)/2).*

| Branche | OOS exact (approx équipe) | IS exact | **EV/campagne v2.2** |
|---|---:|---:|---:|
| 0.61 bps (interim) | **$2,897** ($2,887, +0.3%) | $989 | **+$1,125** |
| 1.0 bps | $2,807 ($2,798, +0.3%) | $901 | +$1,063 |
| 1.5 bps | $2,578 | $849 | +$965 |
| era (défaut actuel) | $2,632 | $684 | +$926 |
| ORB mort / off | $1,262 cleanroom ($1,280 équipe ✓) | ~$330 | ≈ +$295-310 |

L'approximation de l'équipe est validée à +0.3% — leurs branches pré-calculées étaient justes.

## Ce qui reste VIVANT du protocole v1 (inchangé)
- Règle pré-enregistrée « aucun ré-ancrage avant N=60 » : RESPECTÉE (era reste le défaut
  jusqu'au verdict du 15/06).
- Caveats au registre : sélection adverse des stops (plancher de bruit ≠ prime stop-through —
  variante stop-order si verdict 1.0-1.5) ; asymétrie de venue démo/funded.
- Cohérence audit : la requalification « session 1 auction −3.34 = hors-sujet » converge avec
  le finding d'audit C21 (fills réels 16:05-16:10, l'auction n'est pas le timestamp d'entrée).
