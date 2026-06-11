# RE-COST v2.2.1 — swaps mesurés + commissions + marge Swing (data-only, 2026-06-11)

## Verdict (10 lignes)
1. **Le terme matériel est la marge SWING : OUI.** Si le levier Swing serveur = officiel
   (fx 1:30, indices 1:15, métaux 1:9), le cap 60 % **bind 56 %** des rebalances (vs 5.5 %
   policy), marge pré-cap p50 69 % / p99 395 % / p999 511 %, et p(pass) **−15.58 pt**
   apparié CI95 [−24.0 ; −7.1] (84.6→71.4). vm14 n'est pas exécutable tel quel : le cap
   de-leverage le book ×0.3-0.5 en continu. **Gate déploiement : lire OrderCalcMargin sur le
   serveur SWING avant challenge** (mesure 10/06 = compte Standard).
2. Swaps mesurés (G0 : 4/4 facturés reconstruits au centime) + commissions (JPY 0.5 bps RT,
   XAU 0.14) : challenge **statistiquement inchangé** — deltas appariés CI95 ⊃ 0
   (comm −1.73 [−5.84;+1.95] ; swaps fwd −1.08 [−4.33;+2.60] — jitter de chemin, méthode
   vm-sweep 4e1bac5). **Pin contractuel challenge reste 87.0.** Marge policy : p(pass)
   intouché ✓ (pré-enregistrement respecté).
3. Funded sous coûts mesurés : OOS **$2,529** (−$103 vs $2,632), VAL **$1,381**, EV
   **+$863** (vs +$926) ; insensible à la marge swing (vm1 ne bind jamais).

## Chiffres
| Grandeur | v2.2 | v2.2.1 | Δ |
|---|---:|---:|---|
| Challenge pooled (contractuel) | 87.0 | 87.0 | inchangé (CI appariés ⊃ 0) |
| Challenge si marge SWING enforced | — | 71.4 | **−15.58 pt [−24.0;−7.1] SIGNIF** |
| Marge pré-cap p50/p99/bind — policy | 21/79/5.6 % | 21/78/5.5 % | = |
| — Standard mesurée (1:100/1:50/1:30) | — | 22/104/10.1 % | modéré |
| — **Swing officielle (1:30/1:15/1:9)** | — | **69/395/56.0 %** | **dominant** |
| Funded IS / OOS | $684 / $2,632 | $683 / $2,529 | comm drag −$103 OOS |
| VAL / EV campagne | $1,422 / +$926 | $1,381 / +$863 | −2.9 % / −6.8 % |
| Swap US100 long | −2.241 bps (périmé) | −637.16 pts = −2.13 bps @29 974 | ancre re-datée |
| Swap JPY long (crédit J1) | +0.184 bps | +0.96 pts = +0.06 bps @160.28 | crédit ÷3 |
| Commission JPY / XAU / indices | absentes | 0.50 / 0.14 / 0 bps RT | coût réel ajouté |

## Tâches
- **T1 calendrier ×3 par symbole** : grille mesurée XAU+JPY mercredi, indices vendredi —
  identique au panel sim (1379/1379 par jambe, zéro changement moteur). Incidence sleeves :
  **nightly US100+GER40 = 0 nuit triple** (lun+mar ∩ vendredi = ∅, 1 318 nuits) ; or-trend
  20.3 % des nuits tenues en triple (370/1 824), J1 19.9 % (424/2 136). Forecast/reconcile
  chargent triple_dow PAR symbole (`measured_specs`).
- **T2 commissions** : JPY $2.5/lot/side = 0.50 bps RT (turnover J1 : challenge $49.3k/j
  → ~$1.2/j ; funded $292/j → ~$0.007/j) ; XAU 0.0007 %/side = 0.14 bps RT ; indices 0.
  Effet funded : −$103 OOS. Effet challenge : ns (CI ⊃ 0).
- **T3 marge SWING** : voir verdict 1. Grille type vm14 (poids 0.5/1.31/0.6/0.6, soir ON
  complet) : besoin policy 65.9 % (×0.91 si cap), Standard 75.3 % (×0.80), **Swing 250.9 %
  → scale forcé ×0.24**. Tables côte à côte : `recost/tables/recost_margin.csv` +
  `recost_margin_grid.csv`. Statut : « à confirmer sur specs serveur Swing au déploiement »
  (gravé yaml/mqh).
- **T4 funded re-run** : voir tableau (ORB_RT_BPS = era inchangé, N=60 du 15/06 intact).
- **T5 immunisation ftmo_live** : l'EA lit SYMBOL_SWAP_LONG/SHORT + ROLLOVER3DAYS +
  OrderCalcMargin à l'init + au rebalance ; **enforcement du cap 60 % au taux de marge
  LIVE** (fallback conservateur max(Swing, policy)) ; ancres yaml = bornes datées
  (`measured_specs`, swap ±25 % avec plancher 2 pts, marge ±25 % vs Standard OU Swing,
  triple exact) ; alerte `spec_bounds` supervisor ; brain audite l'export. Test : swap
  hors borne lève l'alerte (`tests/test_live_bounds.py`, 8 tests). 154/154 PASS.

## Gates
G0 mécanique swap **PASS** (4/4 au centime) · G1 repro baseline **PASS** (87.01 exact) ·
G2 dérive challenge **RÉSOLU** (pooled bouge mais appariés ns ; la marge policy ne touche
pas le p(pass) ✓) · AMENDEMENT §10 : gate 2 mesure **PASS**, branche STOP refermée.

## Chaîne de gel
config_v22.py (ancres datées) → spec_v22.yaml sha `56fbdde78a2e…` (#19) → spec_v22.mqh sha
`2fc65503ef66…` (#20) + spec_v22.sha256 à re-déposer dans MQL5/Files. Pins baseline :
605f4a4 + 4e1bac5 + 87b6cd4 + 79c6912 + CE commit (pin de déploiement).
Artefacts : `recost/summary.json`, `recost/tables/*.csv`, `recost/recost_run.log`.
