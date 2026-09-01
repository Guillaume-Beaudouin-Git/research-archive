# Audit du ledger ORB (`nq_v2_trades.parquet`) — résolution intra-barre

**Sleeve armé en production funded** (`FU_ORB_RISK=0.0025`, compte <ACCOUNT_ID>). Δn_tests = 0 :
re-pricing d'un ledger et d'un verdict existants, aucune hypothèse nouvelle, aucune optimisation.
Ledger : `PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet` (N=4013,
2010-06-07 → 2026-05-29). M1 canonique : `data/raw/NQ_1min_databento_2010-2026.parquet`.
Worktree : `<HOME>/Desktop/Algo_claude_orbledger`, branche `claude/audit-ledger-orb`.

## Synthèse (12 lignes)

1. **Double touche** : **40.14 %** des jours (1611/4013) voient les DEUX niveaux de l'OR franchis dans la session — bien au-dessus des 15-27 % du corpus 109. **Mais ce n'est pas de l'ambiguïté** : à résolution M1, **1 seul jour sur 4013 (0.025 %)** a les deux niveaux franchis dans la MÊME minute (irréductible).
2. La direction du ledger concorde avec le premier franchissement M1 sur **98.95 %** (3970/4012) des jours résolus ; **42 jours (1.05 % des trades)** divergent (écart médian 14 min entre les deux touches), pour un impact mesuré de **−13.62 R** (−6.9 % du gross total +197.29 R) — signalé, non corrigé (hors périmètre : ne pas modifier le ledger).
3. **Dérapage d'entrée mesuré en M1** : 11/4011 barres de déclenchement (0.274 %) ouvrent au-delà du niveau, **toutes exactement 1 tick** ⇒ gap moyen **+0.000029 R** (t HAC 2.20, N=4011) — statistiquement non nul, **économiquement nul** (1704× ce dérapage consommerait le gross de +0.0492 R).
4. **Dérapage de sortie au stop mesuré en M1 (L59)** : **0/1586 (0.00 %)** des barres de stop ouvrent au-delà — le canal gap de sortie est **VIDE** ici (mécanisme : RTH intraday continu, pas de gap overnight ; L59 est un chiffre de barres DAILY, il ne transfère pas). **Aucun trade « TP »** n'existe dans ce ledger (`outcome` ∈ {STOP, TIME_STOP} uniquement, spec réelle = OR 30 min + pas de TP fixe, ≠ la description générique 09:30-09:45/TP 1.5R/12:30 citée pour l'ancienne Strategy C) ; les 2423 sorties TIME_STOP correspondent **exactement** (2423/2423) au dernier close M1 RTH de la journée.
5. **Le canal « idéalisation deux jambes » (`entry==level`, `exit_px==stop_eff`) est donc économiquement vide sur NQ** : corriger le gap mesuré ne bouge quasiment rien (t ALL 2.736 → 2.735).
6. **Ce qui tue le sleeve est le SPREAD/microstructure**, pas le gap : au coût natif FTMO mesuré sur le CFD de production (0.96-1.05 bps RT, `AMENDEMENT n°1`), **t HAC(6) tombe à 1.43-1.53 (ALL), 1.61-1.69 (LONG), 0.48-0.54 (SHORT)** — **aucune jambe ne franchit R2 (t>2.0)**.
7. **Verdict par jambe, avant/après correction complète (gap mesuré + spread mesuré)** — voir §4 : R2 **PASS uniquement à coût 0** (ALL et LONG), **ÉCHOUE dès le premier bps de coût réel** ; SHORT échoue **avant même tout coût** (t=1.26 gross).
8. **Point mort de la jambe courte, recalculé avec le levier PAR TRADE (pas le levier médian)** : **1.693-1.694 bps RT** — plus serré que les **1.94 bps** cités dans `AMENDEMENT n°1` (qui utilisait un lev médian=195 uniforme ; le lev par trade révèle un point mort ~13 % plus bas).
9. **Le seuil R2 (t>2.0) de la jambe courte est déjà hors d'atteinte à coût nul** (t=1.260) : la question « two-sided vs long-only » ne se tranche donc PAS sur R2 mais sur le point mort de la MOYENNE (règle opérationnelle déjà en place, `AMENDEMENT n°1` §6) — confirmée, chiffre révisé à la baisse.
10. **Vehicule (Q6)** : le gap (Q2/Q3a) est mesuré SUR NQ futures — le vrai instrument du ledger, donc représentatif de sa construction ; le spread (0.96-2.17 bps) est mesuré SUR US100.cash CFD — le vrai instrument de production. **Ce que ce chiffre couvre** : le coût d'exécution attendu en production. **Ce qu'il ne couvre pas** : le bid/ask NQ CME lui-même (non pertinent, jamais tradé en prod) et la fidélité fine du dérapage LIVE au-delà de n=12 fills (IC large).
11. **Verdict inchangé par rapport à `AMENDEMENT n°1` : `ORB_KILL` tient dans ses termes pré-enregistrés** au coût mesuré (t=1.43-1.53 < 2.0, IC contient 0) — cet audit ne renverse rien, il **resserre** le point mort de la jambe courte (1.94→1.69 bps) et **ferme** l'hypothèse « idéalisation du ledger » comme explication du KILL : le KILL vient du spread, pas du gap.
12. **Recommandation octobre** : la dérogation opérationnelle (`AMENDEMENT n°1`, EV≈0, risque $25/trade borné) reste la décision correcte au vu de ce re-pricing — rien ici ne justifie de désarmer plus tôt que prévu (règle A1, N=30 fills), et rien ne justifie de le maintenir au-delà de la règle gelée. **Pas de changement de décision recommandé** ; le point mort short révisé (1.69 bps) doit remplacer 1.94 bps dans tout futur amendement.

---

## 1. Contexte et méthode

Le ledger `nq_v2_trades.parquet` porte les colonnes `or_hi, or_lo, level, stop_eff, exit_px,
direction, bi, ttb_5min, outcome, r_gross, r_realised`. Il est idéalisé sur ses deux jambes :
`entry == level` (4013/4013) et `exit_px == stop_eff` (1590/1590 des sorties STOP). Un travail
soeur indépendant (`Multi_Asset/research/active/orb_cost_funded_2026-08/`, gelé 2026-08-12,
amendé 2026-08-21, **non modifié par cet audit**) avait déjà mesuré ces deux canaux et le coût
de spread ; ce dossier **reproduit indépendamment** ces mesures en M1 (methodologie identique,
code propre, aucune dépendance de résultat), **ajoute la mesure du double-touche** (jamais faite),
et **recombine** le tout en un verdict par jambe avec point mort révisé.

Fuseau vérifié au tick (L52/L56) : barres RTH converties en `America/New_York` bornées à
[09:30, 15:59] sur 100 % des barres (`is_rth` flag du parquet M1). Spec réelle du ledger,
confirmée par `PRESPEC_orb_signature_2026-06.md` §0/§3 et par la structure `bi`/`ttb_5min` :
**OR = 09:30-10:00 ET (30 min, 6 barres M5)**, entrée sur franchissement, stop = niveau opposé
de l'OR, **pas de TP fixe**, sortie sur stop OU clôture RTH (~16:00 ET). Ceci diffère de la
description générique « OR 09:30-09:45 / TP 1.5R / time-stop 12:30 » associée à l'ancienne
Strategy C (iter_10) dans `CLAUDE.md` — ce sont deux sleeves ORB distinctes ; le sleeve armé en
production funded (`FU_ORB_RISK`) est celui de CE ledger.

L60 (barres à fourchette nulle) : 0.093 % sur le M1 RTH complet (1446/1 551 866), 0.025 % sur les
barres de déclenchement d'entrée (1/4011), 0.000 % sur les barres de sortie au stop (0/1586) —
négligeable, ne contamine pas la mesure (`out/l60_flat_bar_check.csv`).

Statistiques : HAC Newey-West lag-6 (`statsmodels`, `cov_type='HAC', cov_kwds={'maxlags':6}`),
IC95 par block-bootstrap stationnaire (Politis-Romano, longueur de bloc moyenne 10, 5000 tirages),
jamais iid. N systématiquement rapporté.

## 2. Q1 — Double touche (mesure nouvelle, M1)

Pour chacun des 4013 jours : fenêtre OR 09:30-09:59 ET (6 barres M1 par bucket M5, cohérent avec
le ledger), puis scan des barres M1 de 10:00 à 15:59 ET pour le premier franchissement de `or_hi`
(idx_up) et de `or_lo` (idx_dn).

| statut | N | % |
|---|---:|---:|
| SINGLE (un seul côté franchi) | 2402 | 59.86 % |
| DOUBLE_ORD (les deux côtés franchis, ordre résolu au M1) | 1610 | 40.12 % |
| DOUBLE_AMBIG (les deux côtés franchis DANS LA MÊME barre M1) | 1 | 0.025 % |

`out/q1_double_touch_summary.csv`, détail par jour `out/q1_double_touch_per_day.csv` (+ .parquet).

**Lecture.** 40 % de double-touche est un chiffre élevé — mais ce n'est PAS l'ambiguïté du
corpus 109 (bar-level, où l'ordre est indéterminable à la résolution disponible). Ici, à
résolution M1, l'ordre chronologique est quasi toujours déterminable (99.975 %). L'ambiguïté
« irréductible » (même minute) est **1 cas sur 4013**.

**Concordance avec le ledger** (jours résolus, N=4012) : **98.95 %** (3970/4012). Sur les
**42 jours discordants** (2.6 % des DOUBLE_ORD, 1.05 % du ledger total) : écart temporel entre
les deux touches nettement plus serré (médiane 14 min, moyenne 26.6 min) que la population
générale des DOUBLE_ORD (médiane 95 min, moyenne 127 min) — ce sont des cas proches de la
frontière, cohérent avec une construction originelle possiblement calée sur le bucket M5 plutôt
que sur le M1 strict. Impact mesuré sur le P&L du ledger (pas corrigé, juste quantifié) :
`r_gross` moyen sur ces 42 jours = **−0.3242**, somme **−13.62 R**, soit **−6.9 %** du gross
total (+197.29 R). **Non corrigé** : modifier la direction de ces 42 trades reviendrait à changer
le signal, hors périmètre de ce re-pricing (`PREREGISTRATION.md` §4). Signalé pour un futur audit
dédié si le MD le juge prioritaire.

## 3. Q2 — Dérapage d'entrée (mesure indépendante, M1)

Barre M1 de déclenchement = première barre du bucket M5 (`bi`) qui franchit `level` dans le sens
de `direction`. Fill réaliste = `max(open, level)` (long) / `min(open, level)` (short).

| | N résolus | gap > 0 | mean gap | HAC t |
|---|---:|---:|---:|---:|
| points | 4011 | 11 (0.274%) | +0.000686 pt | — |
| bps | 4011 | 11 (0.274%) | +0.001467 bps | — |
| **R** | 4011 | 11 (0.274%) | **+0.000029 R** | **2.195** |

Tous les 11 gaps valent exactement **1 tick (0.25 pt)**, le maximum observé sur 16 ans.
Levier médian mesuré sur ce ledger : **195** (par trade, cf. §5) ⇒ 1 bps RT = 0.0195 R — l'écart
d'entrée mesuré ici (0.0015 bps) est **~700× plus petit** que cette échelle. **Le canal gap
d'entrée est statistiquement non nul mais économiquement négligeable** : `out/q2_entry_slippage_per_trade.csv`,
`out/q2_q3a_summary.csv`.

## 4. Q3 — Dérapage de sortie (STOP séparé de TIME_STOP ; pas de TP dans ce ledger)

**Sorties au STOP (L59)** — barre M1 de franchissement de `stop_eff` en sens adverse, cherchée à
partir de la barre d'entrée :

| | N résolus | ouvre au-delà | mean gap |
|---|---:|---:|---:|
| points/bps/R | 1586 | **0/1586 (0.00 %)** | 0.000000 |

**Canal gap de sortie VIDE.** Reproduction indépendante du résultat du volet soeur (0/1587) à
1 trade près (résolution légèrement différente des cas limites, sans conséquence). Mécanisme :
en RTH intraday continu, la barre qui précède la barre de stop n'a par définition pas touché le
stop (sinon elle serait la barre de stop) — son close est du bon côté, et la continuité M1
intra-session ne permet quasiment aucun saut au-delà d'un stop qui vient d'être touché. **L59
(25 % sur gap_pattern, barres DAILY à gap overnight) ne transfère pas à un stop intraday sur
barres M1 continues.**

**Sorties TIME_STOP** — pas de TP dans ce ledger (`outcome` ∈ {STOP, TIME_STOP} uniquement,
vérifié par value_counts). Les 2423 sorties TIME_STOP correspondent **exactement** au dernier
close M1 RTH du jour : **2423/2423 (100.000 %)**. Lecture : sortie déterministe sur le temps, pas
de seuil de prix à franchir, donc pas de canal gap au sens L59 — l'idéalisation résiduelle est la
même microstructure (spread/tick) que n'importe quel ordre marché, déjà comptée dans le coût de
spread (§5), pas un canal séparé. `out/q3a_exit_stop_slippage_per_trade.csv`, `out/q3b_timestop_fidelity.csv`.

## 5. Q4/Q6 — Verdict corrigé, par jambe, avant/après

Deux corrections distinctes, non redondantes :

1. **Correction GAP mesurée** (Q2 + Q3a, ci-dessus) : `R_gap_corrected = r_gross − gap_R_entry − gap_R_exit_stop`.
2. **Correction de coût de spread mesuré** (véhicule de production, US100.cash CFD, `AMENDEMENT n°1`) :
   appliquée en R via le **levier PAR TRADE** `lev = level / |level − stop_eff|` (pas le levier
   médian utilisé dans l'amendement d'origine).

### 5.1 Effet du seul gap mesuré (négligeable, confirme §3-4)

| série | leg | N | mean R | t HAC6 | R2 |
|---|---|---:|---:|---:|---|
| r_gross (avant) | ALL | 4013 | 0.04916 | 2.736 | PASS |
| R_gap_corrected | ALL | 4013 | 0.04913 | 2.735 | PASS |
| r_gross (avant) | LONG | 2156 | 0.05892 | 2.677 | PASS |
| R_gap_corrected | LONG | 2156 | 0.05888 | 2.675 | PASS |
| r_gross (avant) | SHORT | 1857 | 0.03784 | 1.260 | FAIL |
| R_gap_corrected | SHORT | 1857 | 0.03782 | 1.260 | FAIL |

`out/q6a_gap_only_correction_by_leg.csv`. Ces valeurs à coût 0 reproduisent exactement les
« valeurs de référence » pré-communiquées (ALL 2.736, LONG 2.677, SHORT 1.260) — validation
croisée de la méthode HAC/N utilisée.

### 5.2 Verdict final : gap mesuré + spread mesuré, par jambe

| coût RT | leg | N | mean R | t HAC6 | IC95 | R2 |
|---|---|---:|---:|---:|---|---|
| 0.00 (avant tout coût) | ALL | 4013 | +0.0491 | **2.735** | [0.0148, 0.0833] | **PASS** |
| 0.00 | LONG | 2156 | +0.0589 | **2.675** | [0.0178, 0.0993] | **PASS** |
| 0.00 | SHORT | 1857 | +0.0378 | 1.260 | [−0.0190, 0.0974] | FAIL |
| 0.962 (spread natif, fenêtre ORB) | ALL | 4013 | +0.0275 | 1.530 | [−0.0069, 0.0616] | FAIL |
| 0.962 | LONG | 2156 | +0.0372 | 1.693 | [−0.0039, 0.0776] | FAIL |
| 0.962 | SHORT | 1857 | +0.0163 | 0.542 | [−0.0404, 0.0761] | FAIL |
| 1.045 (spread natif, médiane toutes heures) | ALL | 4013 | +0.0257 | 1.426 | [−0.0087, 0.0598] | FAIL |
| 1.045 | LONG | 2156 | +0.0353 | 1.608 | [−0.0057, 0.0758] | FAIL |
| 1.045 | SHORT | 1857 | +0.0145 | 0.481 | [−0.0422, 0.0742] | FAIL |
| 2.17 (tout-compris, n=12 fills réels) | ALL | 4013 | +0.0004 | 0.022 | [−0.0341, 0.0348] | FAIL |
| 2.17 | LONG | 2156 | +0.0099 | 0.452 | [−0.0312, 0.0501] | FAIL |
| 2.17 | SHORT | 1857 | −0.0107 | −0.352 | [−0.0676, 0.0493] | FAIL |

`out/q6b_final_verdict_by_leg.csv` (identique à `out/q4_verdict_by_leg_cost_sweep.csv` à la
5ᵉ décimale près — la correction gap ne bouge rien de matériel, cf. §5.1).

**Lecture face à R2 (t HAC > 2.0, gelé `PREREGISTRATION.md` §3)** : R2 **PASSE uniquement à
coût nul, et seulement pour ALL et LONG**. Dès le premier niveau de coût mesuré (0.96 bps,
spread natif FTMO sur la fenêtre ORB), **toutes les jambes échouent R2**. SHORT échoue **avant
même tout coût** (t=1.26 à 0 bps) — ce n'est pas le coût qui tue la jambe courte au sens
statistique, elle n'a jamais eu la puissance nécessaire.

## 6. Q5 — Point mort de la jambe courte, révisé

Recalculé avec le **levier par trade** (`lev = level/|level−stop_eff|`, médiane 195.48, moyenne
224.62 — sensiblement plus dispersé qu'un simple médian appliqué uniformément : std=154, p25=138,
p75=270, max=2721) plutôt que le levier médian unique utilisé dans `AMENDEMENT n°1` :

| | valeur |
|---|---:|
| Point mort MOYENNE (mean R_short = 0) | **1.693-1.694 bps RT** |
| t HAC6 short à coût 0 | 1.260 (< 2.0 : R2 échoue déjà) |
| Référence `AMENDEMENT n°1` (lev médian uniforme) | 1.94 bps |

`out/q5_short_breakeven.csv`, `out/q5_short_breakeven_curve.csv`, `out/q6c_short_breakeven_final.csv`.

**Le point mort baisse de 1.94 à ~1.69 bps** (−13 %) quand on utilise le levier par trade plutôt
que la médiane appliquée uniformément — un raffinement de méthode, pas un changement de mesure de
coût. La règle opérationnelle `AMENDEMENT n°1` §6 (< 1.94 → two-sided ; 1.94-2.5 → long-only ;
> 2.5 → désarmer) doit être lue avec ce chiffre révisé : au spread natif mesuré (0.96-1.05 bps),
on reste **sous le point mort** (le two-sided reste net positif en somme, cf. table `Sum(R)`
ci-dessous), mais **aucune jambe ne passe R2** — la question n'est donc plus « garder two-sided
ou passer long-only », elle est déjà tranchée par R2 : **KILL** au sens statistique, indépendamment
de la question de signe.

### Sum(R) par jambe (contexte P&L total, risque fixe ⇒ Σ R compte, pas la moyenne)

| coût RT | Σ R long | Σ R short | Σ R total |
|---|---:|---:|---:|
| 0.00 | 127.02 | 70.26 | 197.29 |
| 0.962 | 80.21 | 30.36 | 110.57 |
| 1.045 | 76.17 | 26.92 | 103.09 |
| 1.80 | 39.44 | −4.40 | 35.04 |
| 2.17 | 21.43 | −19.75 | 1.69 |

`out/q4_sumR_by_leg_cost_sweep.csv`. Au levier par trade, le tout-compris (2.17 bps) donne un
total quasi nul (+1.69 R sur 4013 trades, 16 ans) — cohérent avec le diagnostic « EV ≈ 0 »
d'`AMENDEMENT n°1`, mais la décomposition par jambe est plus dégradée que celle de l'amendement
(qui utilisait le lev médian uniforme : +35.6/−8.5 contre +21.43/−19.75 ici).

## 7. Q6 — Question de véhicule

Le ledger est construit sur **NQ futures** (databento GLBX). La production s'exécute en
**CFD US100.cash chez FTMO**.

- **Ce que Q2/Q3a couvrent** : le canal *gap* (idéalisation de construction) — mesuré **sur NQ**,
  le vrai instrument du ledger. C'est représentatif de la fidélité de construction du ledger
  lui-même, pas du coût de production.
- **Ce que Q4/Q5/Q6b couvrent** : le coût de spread/microstructure — mesuré **sur US100.cash CFD**
  (logger passif embarqué EA, `spread_log_202608.csv`, + 12 fills réels du compte funded). C'est
  le chiffre pertinent pour la décision de production, et il domine économiquement (0.96-2.17 bps
  contre 0.000029-0 R de gap, un facteur ~1000).
- **Ce que ce re-pricing NE couvre PAS** : le bid/ask NQ CME lui-même (non pertinent — jamais
  tradé en production) ; la fidélité fine du dérapage LIVE au-delà de n=12 fills (IC large,
  [1.25, 3.19] bps sur l'entrée seule d'après `AMENDEMENT n°1`) ; et le mécanisme structurel
  documenté par l'amendement (le stop BUY MT5 se déclenche sur l'Ask, ce que le gap NQ ne capture
  pas — d'où l'écart 0 gap NQ vs 2.17 bps tout-compris CFD).

## 8. Verdict et recommandation

**Le KILL pré-enregistré (`R2 : t HAC > 2.0`) tient**, à tous les niveaux de coût mesurés ≥ 0.96
bps, sur les trois découpes (ALL, LONG, SHORT). Ce re-pricing **ne renverse rien** de
`AMENDEMENT n°1` — il :

- **ferme** l'hypothèse que l'idéalisation deux-jambes du ledger (`entry==level`,
  `exit_px==stop_eff`) explique une part matérielle de l'écart : le gap mesuré est
  économiquement nul des deux côtés (Q2, Q3a) — cohérent avec `RESULTS.md §2` ;
- **audite pour la première fois** la question du double-touche (Q1) et la referme aussi : 40 %
  de jours à double-touche est un chiffre élevé mais l'ambiguïté irréductible à résolution M1 est
  quasi nulle (1/4013) ; un résidu de 42 jours discordants (1.05 %, −6.9 % du gross) est signalé
  pour audit futur, non corrigé ici ;
- **resserre** le point mort de la jambe courte de 1.94 à ~1.69 bps (levier par trade au lieu du
  médian) ;
- **confirme** que c'est le SPREAD/microstructure du CFD de production, pas la construction du
  ledger sur NQ, qui pilote le verdict.

**Recommandation pour octobre** : aucun changement de décision. La dérogation opérationnelle
d'`AMENDEMENT n°1` (EV≈0 au coût mesuré, risque borné $25/trade, N=30 fills avant désarmement,
échéance ~octobre 2026) reste la lecture correcte de ce ledger repricé. Le seul ajustement à
reporter dans un futur amendement : remplacer le point mort de la jambe courte cité (1.94 bps)
par la valeur révisée au levier par trade (**1.69 bps**), et noter que le seuil R2 pour la jambe
courte seule est hors d'atteinte indépendamment du coût (t=1.26 gross).

## 9. Livrables

Code (`code/`) : `q1_double_touch.py`, `q2_q3a_slippage.py`, `q4_verdict_by_leg.py`,
`q6_final_verdict.py`. Sorties (`out/`) : `q1_double_touch_summary.csv`,
`q1_double_touch_per_day.csv/.parquet`, `q2_entry_slippage_per_trade.csv`,
`q3a_exit_stop_slippage_per_trade.csv`, `q2_q3a_summary.csv`, `l60_flat_bar_check.csv`,
`q3b_timestop_fidelity.csv`, `q4_verdict_by_leg_cost_sweep.csv`, `q4_sumR_by_leg_cost_sweep.csv`,
`q5_short_breakeven.csv`, `q5_short_breakeven_curve.csv`, `q6a_gap_only_correction_by_leg.csv`,
`q6b_final_verdict_by_leg.csv`, `q6c_short_breakeven_final.csv`.
