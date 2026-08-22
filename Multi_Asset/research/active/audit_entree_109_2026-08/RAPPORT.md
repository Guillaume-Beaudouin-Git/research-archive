# Audit de l'ambiguïté d'ENTRÉE dans le corpus des 109 stratégies — RAPPORT

**Date:** 2026-08-21. **Isolation:** aucune commande git, aucune bascule de branche
(`claude/book-idle-escalation` inchangée), VPS non utilisé. Interpréteur `/usr/bin/python3`.
Écritures confinées à ce dossier ; le moteur `oxfordstrat_109_audit/code/` et les rapports
existants ont été LUS (importés en mémoire) mais jamais modifiés — vérifié par `git status`
(le dossier entier est déjà non-tracké, `??`, et aucun fichier n'y a de mtime récent après ce
travail).

---

## Synthèse (12 lignes)

L'ambiguïté d'entrée est un **breakout ORB double-sens dans la même barre daily** (buy-stop
`Open+Stretch` ET sell-stop `Open−Stretch` touchés le même jour) — `ftmo_lab.py:124` la score
**"assume loser" (−2×Stretch/risk0, la pire issue possible)**. ⚠ **Le sens du biais est
PESSIMISTE, PAS optimiste** — c'est l'inverse de l'hypothèse de départ du mandat. Ampleur : **de
14.7 % à 27.4 %** des trades selon la stratégie (S096 le pire), contre **0.02 %** pour la famille
Donchian "skip" — écart de **géométrie d'entrée** (stretch symétrique autour de l'open vs canal
20 jours), pas d'instrument. Biais mesuré par décomposition propre (forced-long/forced-short,
`unbiased = 0.5×(long+short)`) : **−43 à −51 bps/trade ambiguë** (t de −11 à −29 selon
stratégie, N=564 à 2 774). **8 stratégies exposées, 0 famille Donchian.** Correction rejouée sur
les **4 gates constitutionnels réels** (pas seulement Gate 1) : **2 verdicts basculent DISCARD →
KEEP** (S037 Greatest Swing Value, **S061 l'ORB canonique "pilier de la famille"**) ; 6 restent
DISCARD (dont S002, dont le Gate 1 flip mais qui reste tué par le Gate 3 DSR — **passer un gate
n'est pas passer**). Robustesse L60 (exclusion XPTUSD/XPDUSD/XAGUSD/COCOA/COFFEE, print-
settlement) : **le renversement tient**, mais **S061 devient fragile** (Sharpe réel corrigé
+0.32→+0.09). **Sur l'ORB en production** (`FU_ORB_RISK=0.0025`, compte <ACCOUNT_ID>) : ce mécanisme
précis **ne s'applique PAS** (signal directionnel unique à 09:46 ET, pas de double ordre stop —
`signal_engine.py:134`) — mais la question inverse (`entry==level`, **optimiste**) EST pertinente
et **déjà chiffrée par une étude sœur** : le levier direct (2.169 bps mesurés) mange **86 % du
gross edge à lui seul** ; corrigé au véhicule natif FTMO (0.94–1.05 bps, Amendement n°1 du jour
même), t passe de 0.48 à 1.56, **toujours sous le seuil R2 (2.0) — ORB_KILL tient**, le sleeve
reste armé sous **dérogation explicite et bornée** (déjà réconciliée, pas un oubli). **Constat
principal : le corpus a DEUX biais de sens opposé dans deux coins différents du code — le
109-daily est trop dur (pessimiste), le ledger funded-ORB est trop gentil (optimiste) — et
seul le premier bouge des verdicts existants (2/109), le second est déjà sous contrôle.**

---

## A. Ce qu'est exactement l'ambiguïté d'entrée

### A.1 Le mécanisme, cité

`Multi_Asset/research/archived/oxfordstrat_109_audit/code/ftmo_lab.py`, fonction
`simulate_bracket` (docstring lignes 92-99, code lignes ~118-125) :

```python
buy, sell = o[e] + st[i-1], o[e] - st[i-1]     # ligne 105
long_hit  = h[e] >= buy
short_hit = (l[e] <= sell) and allow_short
...
if long_hit and short_hit:                # both sides -> assume loser (spec)   -- ligne 124
    trades.append(_trade(idx[e], idx[e], 'both', 0, -2*st[i-1]/risk0 - cost_R, 0))
    i = e + 1; continue
```

C'est un **ORB straddle daily** : un buy-stop ET un sell-stop, symétriques autour de l'`Open` du
jour de breakout (`Stretch` = bruit Crabel, `SMA(min(H−O,O−L),10)×2` typiquement, ou une variante
GSV/NR/Wide-Range). Si le `High` du jour dépasse le buy-stop **ET** le `Low` dépasse le sell-stop
(un aller-retour dans la même barre daily), le moteur ne peut pas savoir lequel a été touché en
premier — **candidat "franchissement de niveaux à l'entrée"** listé dans le mandat, distinct de
l'ambiguïté de sortie déjà auditée par `audit_moteur_bracket_2026-08` (0 % mesuré sur ce même
corpus, brackets 6×ATR daily). Le moteur retient l'hypothèse **PESSIMISTE codée en dur** : perdre
sur les deux jambes (`−2×Stretch/risk0`), quelle que soit la vraie séquence de touche. C'est
l'inverse du cas L59 (sortie, où l'hypothèse standard est OPTIMISTE) — **⚠ ne pas supposer le
sens, le mesurer**, ce que ce rapport fait au chantier B.

**8 stratégies implémentent ce mécanisme exact** (grep ciblé, lecture directe des 109 fichiers) :
S001, S037, S055, S056, S061, S062, S096 réutilisent `ftmo_lab.simulate_bracket` **inchangé** ;
S002 a sa propre copie octet-pour-octet du même bloc (`strat_s002_crabel_nr_setupexit.py:53-54`)
mais un exit différent (voir C.1). **3 stratégies voisines** (S020/S021/S022, cluster Donchian
channel-breakout) ont le MÊME test `long_hit and short_hit` mais une résolution **différente** :
`strat_s020_donchian.py:44` — *"whole channel engulfed (rare) -> skip"* — la barre ambiguë est
**ignorée** (aucun trade enregistré), pas scorée comme perte. **101 stratégies restantes** :
signal directionnel unique (`d = 1 if ... else (-1 if ... else 0)`), structurellement incapable
de déclencher les deux sens le même jour — **non concernées par construction**.

---

## B. Mesure de l'ampleur

### B.1 Méthode (décomposition propre, sans deviner de règle "juste")

Même logique que le rapport-sœur (`audit_moteur_bracket_2026-08`, chantier A.2) : pour chaque
barre ambiguë, calculer ce qu'aurait donné une résolution **forcée-long** ET une résolution
**forcée-short** (même logique de sortie — target/temps/stop ATR, `fill` identique au reste du
run), en continuant la simulation normalement plutôt qu'en s'arrêtant à la barre d'entrée.
`unbiased_R = 0.5×(long_R + short_R)` — un tirage à pile-ou-face équitable, cohérent avec la
construction symétrique du Stretch (aucun a priori directionnel). `biais = assumed_R − unbiased_R`.
Vérifié trade-pour-trade : le réengagement du moteur (`i = exit_j + 1`, pas de positions qui se
chevauchent) reproduit **exactement** les comptages du moteur réel pour 6/7 stratégies diagnostiquées
(564, 2116, 684, 1105, 2774, 1217 — identiques à `scan_entry_ambiguity.py`) ; S002 diffère
légèrement (564 diagnostiqués vs 666 réels) car son exit ajoute une bande Stretch non modélisée
dans le tail diagnostique simplifié — signalé, sans conséquence (voir C.1).

### B.2 Vérification de qualité des données AVANT de faire confiance à la mesure (L60)

`l60_flat_bar_check.py` sur les 30 daily OHLC de la corpus : **XPTUSD 69.3 %**, **XPDUSD 61.1 %**
et **XAGUSD 22.7 %** de barres `high==low` (print de règlement, pas un vrai prix), plus COCOA
17.2 %, COFFEE 10.0 % — **reproduit exactement** les chiffres L60 cités dans CLAUDE.md (61-69 %
XPTUSD/XPDUSD). Le reste du corpus (25/30 instruments, dont tous les indices et la plupart du FX)
est propre (<1 % de barres plates). **Robustesse traitée au chantier C.3** : le renversement de
verdict S037/S061 est retesté en excluant ces 5 instruments contaminés.

### B.3 Tentative d'arbitrage intraday M1 — honnêteté sur ce qui n'est PAS arbitrable

Le mandat suggère `data/deep_history_utc/` (M1 vrai UTC) pour trancher l'ordre de touche. **Testé
et ABANDONNÉ comme méthode primaire** (`data_concordance_check.py`) : le daily OHLC consommé par
`ftmo_lab.py` provient de `panels/m5_indices/*_M1.csv` (`build_ohlc_store.py:15-24`, coupe UTC
minuit) — une source **différente** du store canonique `deep_history_utc` (réparé 2026-06-10,
sources P1/P2fx/P2idx). Concordance mesurée sur les 10 instruments FX+XAUUSD partagés : seulement
**15 à 39 %** des jours ont un accord Open/High/Low à moins de 5 % du range journalier
(`m1_daily_concordance.csv`, N=839-2185 jours par instrument). **Conclusion honnête : arbitrer
l'ordre de touche via `deep_history_utc` sur les trades DE CE CORPUS reviendrait à arbitrer une
autre journée de marché que celle qui a produit les trades reportés.** Méthode abandonnée comme
primaire ; la décomposition B.1 (forced-long/forced-short sur la MÊME série que le corpus) est la
seule mesure directement attribuable à ces trades précis — **[V]** sur cette série, **[NV]**
comme confirmation M1 indépendante.

### B.4 L'abaque

`abaque_biais_entree.csv` (biais × stretch/ATR × range_jour/ATR, N=9 024 barres ambiguës pooled,
7 stratégies) + marginales `abaque_biais_entree_marginal_stretch.csv` /
`_marginal_range.csv`. Lecture par la marginale stretch/ATR (monotone et propre, N par bin
229-2904) :

| stretch/ATR | n | biais moyen (bps) |
|--:|--:|--:|
| 0.00-0.05 | 544 | **−6.0** |
| 0.05-0.10 | 626 | **−7.4** |
| 0.10-0.15 | 816 | **−26.6** |
| 0.15-0.20 | 1112 | **−28.0** |
| 0.20-0.30 | 2793 | **−44.6** |
| 0.30-0.50 | 2904 | **−73.4** |
| 0.50+ | 229 | **−115.8** |

**Monotone, mécanique et attendue** : la pénalité codée en dur (`−2×Stretch/risk0`) croît
directement avec le Stretch, alors que la vraie moyenne équitable (`unbiased_R`) n'a aucune
raison de croître au même rythme — donc l'écart s'élargit avec le Stretch. Pooled global (7
stratégies, N=9 024) : **−47.1 bps/trade ambiguë, t=−46.6** — **mais ce t est optimiste** (les
observations partagent largement les mêmes jours/instruments entre S001/S002/S055/S056/S096, qui
utilisent tous une variante du même Stretch Crabel sur les mêmes séries) ; les t-stats **par
stratégie** (N indépendant par construction de stratégie, −11 à −29, `impact_by_strategy.csv`)
sont la lecture prudente à citer.

---

## C. Inventaire de contamination — verdict FINAL après les 4 gates, jamais Gate 1 seul

⚠ **Point méthodologique impératif** : Gate 1 (délai+1) est LE gate le plus spectaculaire à
corriger ici (il flippe pour 5/7 stratégies), mais **passer Gate 1 ne veut PAS dire passer**.
`ftmo_lab.run_gates` exige les **4 gates simultanément** (délai+1, two-sided/L25, DSR, OOS/L31).
Le cas S002 le montre nettement : Gate 1 flippe FAIL→PASS, et le verdict **reste DISCARD** parce
que Gate 3 (DSR, `z=−3.10`) est **totalement insensible** à la correction (le DSR utilise la
grille `fill='stop'`, dont l'issue des barres 'both' est **structurellement identique** avant/après
correction pour S002 — voir C.1). Chaque strategie ci-dessous a été rejouée avec le moteur
CORRIGÉ (`corrected_engine.py` : résolution équitable 50/50, MÊME `fill` que le reste du run,
grille de sweep ENTIÈREMENT recalculée pour le DSR) à travers les **4 gates**, pas seulement
l'expectancy native/réaliste. Détail complet : `full_gate_rerun_log.txt`,
`inventaire_contamination_entree.csv`.

### C.1 — 2 renversements DISCARD → KEEP

**S037 (Greatest Swing Value)** — expo 16.9 % (2116/12548). AVANT : native +0.0193R(Sh+1.03) →
réaliste **−0.0085R(Sh−0.47)**, Gate 1 FAIL, verdict DISCARD 1/4. APRÈS : native +0.0273R(Sh+1.45)
→ réaliste **+0.0064R(Sh+0.36)**, Gate 1 PASS ; Gate 2 two-sided PASS (long +0.0719/n5253, short
+0.0103/n5179, **88 % du PnL positif côté long**) ; Gate 3 DSR PASS (z 38.5→61.2) ; Gate 4 OOS
PASS (train/test tous deux positifs). **Verdict corrigé : KEEP (4/4).**

**S061 (Opening Range Breakout, "THE canonical ORB... pilier de la famille" selon sa propre
docstring)** — expo 20.9 % (2774/13272), 2ᵉ plus exposée. AVANT : native +0.0206R(Sh+1.17) →
réaliste **−0.0112R(Sh−0.65)**, DISCARD 1/4. APRÈS : native +0.0293R(Sh+1.66) → réaliste
**+0.0054R(Sh+0.32)**, Gate 1 PASS ; Gate 2 PASS (long 83 % du PnL positif) ; Gate 3 DSR PASS
(z 39.7→62.9) ; Gate 4 OOS PASS. **Verdict corrigé : KEEP (4/4).**

⚠ **Réserve sur les deux** : Gate 2 (two-sided/L25) passe **techniquement** (la jambe minoritaire
a une expectancy positive) mais avec **83-88 % du PnL positif du côté long** — même signature que
le cluster channel-breakout {#6,#7,#20,#21,#22} de ce même corpus, tous tués sur ce critère de
dominance directionnelle malgré un Gate 2 mécanique passant de justesse. **Ce renversement mérite
un ré-audit dédié du Gate 2 lui-même avant tout déploiement — ce rapport ne le fait pas (hors
mandat : corriger un défaut, pas re-durcir un gate).**

### C.2 — Robustesse L60 (exclusion des 5 instruments print-settlement)

`robustness_out.log` : le renversement **tient** sur l'univers propre (25/30 instruments, exclusion
XPTUSD/XPDUSD/XAGUSD/COCOA/COFFEE) :
- S037 : réaliste corrigé **+0.18 Sharpe** (vs +0.36 univers complet) — 4/4 gates, KEEP tient.
- S061 : réaliste corrigé **+0.09 Sharpe** (vs +0.32 univers complet) — 4/4 gates tiennent
  numériquement, mais **la marge s'est réduite d'un facteur 3.5×**. **S061 est un KEEP fragile,
  pas un KEEP confortable** — à re-vérifier avant toute décision qui s'appuierait dessus.

### C.3 — 6 strategies restent DISCARD malgré la correction

| stratégie | expo | Gate1 (natif→réel) avant/après | verdict corrigé |
|---|--:|---|---|
| S001 | 14.7% | −0.0223→−0.0100 (reste négatif) | DISCARD (inchangé, 4/4 fail persistent) |
| S002 | 15.3% | −0.0067→+0.0106 (Gate1 flip technique) | DISCARD (Gate3 DSR z=−3.10 **inchangé** — voir note ci-dessous) |
| S055 | 16.1% | −0.0254→−0.0122 (reste négatif) | DISCARD (inchangé) |
| S056 | 14.7% | −0.0219→−0.0082 (reste négatif) | DISCARD (Gate1 FAIL persiste, DSR z −52.8→−6.96 toujours FAIL) |
| S062 | 19.6% | déjà PASS avant correction | DISCARD (Gate2 100% long-dominé + Gate3 DSR, inchangés) |
| S096 | **27.4%** (max) | −0.0035→+0.0207 (Gate1 flip) | DISCARD (Gate3 DSR z −32.9→−14.8, **améliore beaucoup, reste FAIL**) |

**S002 — note structurale importante** : sous `fill='stop'` (la référence native), le forced-long
ET le forced-short touchent **tous deux** la bande Stretch de sortie de S002 **au niveau opposé
exact de l'entrée**, sur la MÊME barre — parce que l'exit de S002 inclut une "Stretch-band exit"
qui coïncide avec le niveau d'entrée non déclenché. Concrètement : `unbiased_R` calculé =
**exactement** `assumed_R` (vérifié à 15 décimales, `entry_bias_diagnostic.py` output). **Ce
n'est PAS un bug de mesure — c'est une immunité structurelle réelle** : pour CETTE stratégie
précise, l'hypothèse "assume loser" n'est pas un biais, c'est la SEULE issue possible compte
tenu de sa propre règle de sortie. Distinct des 7 autres stratégies (stop ATR pur, 6×ATR, qui ne
coïncide jamais avec le Stretch d'entrée bien plus étroit).

### C.4 — Famille Donchian (S020/S021/S022) — exposition négligeable, non concernée

`donchian_skip_ambiguity_by_instrument.csv` : **8 barres ambiguës sur 33 329** jours-signal
(0.02 %, channel_len=20 canonique) — le double-hit du canal haut/bas 20 jours sur la MÊME journée
est quasi impossible par construction (deux niveaux séparés par un range de 20 jours, contre un
Stretch de quelques jours pour la famille ORB-stop). **Aucune correction n'est mesurable à cette
fréquence** ; ces 3 stratégies restent DISCARD pour leur raison d'origine (dominance bêta long,
Gate 2), sans rapport avec ce mandat.

---

## D. Le lien avec la production — traité sérieusement, pas résumé

### D.1 Le mécanisme de ce rapport NE S'APPLIQUE PAS structurellement à l'ORB en production

Vérifié par lecture directe (`Futures/live/strategy_c_live/signal_engine.py:134,175`) :

```python
direction = "BUY" if close_price > open_price else "SELL"   # ligne 134
...
entry_estimate = close_price   # approximate (actual entry = next bar open)  # ligne 175
```

La production détermine une **direction unique et déterministe** APRÈS la fin de la fenêtre
d'ouverture (09:30-09:45 ET) — comparaison du close de la 16ᵉ barre 1-min à son open. Il n'y a
**aucun ordre stop double en attente** (pas de buy-stop ET sell-stop simultanés dès l'ouverture)
: structurellement, il ne peut PAS y avoir de "double déclenchement dans la même barre" — le
signal n'existe qu'APRÈS que la fenêtre d'ouverture soit close et qu'un seul côté ait été choisi.
**0 % d'exposition à ce mécanisme précis, par construction, pas par mesure.**

### D.2 La question inverse est pertinente — et DÉJÀ chiffrée par une étude sœur

Le ledger simulé (`PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet`,
N=4013) a `entry == level` **exactement 4013/4013** — une hypothèse **OPTIMISTE**, à l'opposé du
sens trouvé au chantier B pour le corpus 109. **Les deux biais sont réels, mesurés
indépendamment, et de sens opposé, dans deux coins différents du dépôt.** Ce rapport ne re-mesure
pas cette question depuis zéro (elle a déjà été **entièrement pré-enregistrée, mesurée et
tranchée** par `Multi_Asset/research/active/orb_cost_funded_2026-08/`, gelé 2026-08-12, résultats
2026-08-13, amendé 2026-08-21) — mais en **relie les chiffres à la même unité (R, via le levier)**
pour répondre au chiffrage demandé :

**Le calcul, en unités communes** (`production_orb_entry_optimism.csv`) :
- Levier médian **195** ⇒ **1 bps RT = 0.0195 R** (`PREREGISTRATION.md`, cité).
- Gross edge à coût nul : **+0.0492 R/trade** (t=2.74, N=4013).
- Décomposition sur fills LIVE réels (N=12, `RESULTS.md` §3) : entrée **+2.169 bps**, sortie
  **−0.374 bps** (crédit net), total **1.795 bps** (concorde à 0.5 % près avec la mesure
  indépendante par cache de spread, 1.804 bps).
- **⇒ La jambe d'ENTRÉE seule, en R : 2.169 × 0.0195 = 0.0423 R/trade = 86.0 % du gross edge
  ENTIER, consommé par la seule optimisme d'entrée.** C'est le chiffre opérationnel : l'hypothèse
  `entry==level` n'est pas un détail, elle mange presque tout l'edge brut à elle seule.
- ⚠ **Limite honnête** : cette décomposition entrée/sortie (2.169/−0.374) a été mesurée sur un
  **autre broker que FTMO** (violation L33, signalée dans l'Amendement n°1 du 2026-08-21 — daté
  d'AUJOURD'HUI). La mesure **native FTMO** (logger passif embarqué, N>13 000 lignes,
  `spread_log_202608.csv`) donne un total tout-compris de **0.94-1.05 bps** (fenêtre ORB
  15:30-16:05 Paris : 0.962-0.982 bps), sans décomposition entrée/sortie repropre à FTMO. En
  **transférant le ratio** entrée/total mesuré sur l'autre broker (2.169/1.795 = 120.8 % — la
  sortie est un léger crédit, donc l'entrée seule dépasse le total) au niveau natif FTMO :
  jambe d'entrée déduite ≈ **1.16-1.26 bps ≈ 0.023-0.025 R = 46-50 % du gross edge** — **[D]**,
  déduit par transfert de ratio, PAS mesuré directement à FTMO (l'entrée seule n'a jamais été
  isolée sur ce broker).
- **Impact sur le verdict R2 (seuil t>2.0)** : au coût tout-compris mesuré (1.80 bps, autre
  broker) → **t=0.48, KILL, marge ×3**. Au coût natif FTMO corrigé (0.94 bps, Amendement n°1) →
  **t=1.56 — un mouvement considérable, mais toujours sous le seuil 2.0. ORB_KILL tient dans ses
  termes pré-enregistrés.**

### D.3 Le sleeve reste armé — sous dérogation explicite, pas par oubli

`FU_ORB_RISK=0.0025`, compte funded **<ACCOUNT_ID>**, armé depuis le 2026-08-17 — **alors que le
verdict pré-enregistré est ORB_KILL**. L'Amendement n°1 (`PREREGISTRATION.md`, 2026-08-21, daté du
jour de cet audit) documente cet écart explicitement : **ce n'est pas une réhabilitation**, c'est
une **dérogation opérationnelle bornée** sur 3 motifs chiffrés — (1) coût d'erreur borné
(**$25/trade**, ≈ neutre au coût mesuré, ni gagnant ni perdant) ; (2) les fills sont la SEULE
route vers la mesure du dérapage manquant (désarmer = renoncer à trancher définitivement) ; (3)
la mesure a une valeur asymétrique (**~57 % de l'EV funded simulée**, cité verbatim). Sortie de
dérogation gelée : **N=30 fills, coût tout-compris > 2.5 bps ⇒ désarmement** (~octobre 2026).
**Ce même Amendement note explicitement** qu'un "audit indépendant (2026-08-21)" avait classé
cette apparente contradiction comme "priorité opérationnelle n°1" — référence quasi certaine au
rapport-sœur `audit_moteur_bracket_2026-08` lu en préalable à ce mandat. **Point clos : la
réconciliation existe déjà, datée d'aujourd'hui, ce rapport n'a rien à ajouter à ce sujet
sinon confirmer qu'elle répond bien à la question soulevée.**

### D.4 Conclusion chantier D

Deux biais réels, mesurés, de sens opposé, dans deux mécanismes structurellement différents :
le corpus 109 (straddle daily, résolution codée pessimiste) et le ledger ORB funded (signal
directionnel unique, fill supposé optimiste). **Aucun des deux n'invalide l'autre** — ce rapport
en corrige un (chantier C, 2 verdicts basculent) et confirme que l'autre est déjà sous contrôle
opérationnel documenté (chantier D, aucune action requise ici).

---

## Fichiers produits

- `scan_entry_ambiguity.py` / `entry_ambiguity_summary.csv` — fréquence de l'ambiguïté (chantier A/C)
- `donchian_skip_ambiguity_by_instrument.csv` — exposition de la famille Donchian "skip"
- `entry_bias_diagnostic.py` / `diag_S0*.csv` — décomposition forced-long/forced-short (chantier B)
- `l60_flat_bar_check.py` / `l60_flat_bar_check.csv` — honnêteté données (L60)
- `data_concordance_check.py` / `m1_daily_concordance.csv` — pourquoi l'arbitrage M1 est abandonné (B.3)
- `build_abaque_and_impact.py` / `abaque_biais_entree.csv` + marginales / `pooled_ambiguous_trades_all_strategies.csv` / `impact_by_strategy.csv` — l'abaque (chantier B.4)
- `corrected_engine.py`, `s002_corrected.py` — moteur corrigé (résolution 50/50 équitable, même `fill`)
- `full_gate_rerun.py` / `full_gate_rerun_log.txt` — re-jeu des 4 gates constitutionnels, ORIGINAL vs CORRIGÉ, 8 stratégies (chantier C)
- `gate1_reprice_precise.py` / `gate1_repricing_precise.csv` — re-pricing précis Gate 1 seul (étape intermédiaire, superseded par full_gate_rerun pour le verdict final)
- `robustness_clean_instruments.py` / `robustness_out.log` — robustesse L60 (chantier C.2)
- `build_inventory.py` / `inventaire_contamination_entree.csv` — inventaire final avec verdict corrigé (chantier C)
- `production_orb_entry_optimism.csv` — chiffrage chantier D (production ORB)

## Reproduction

```
cd Multi_Asset/research/active/audit_entree_109_2026-08
/usr/bin/python3 scan_entry_ambiguity.py          # ~15s — fréquences
/usr/bin/python3 entry_bias_diagnostic.py         # ~20s — décomposition + abaque inputs
/usr/bin/python3 build_abaque_and_impact.py       # ~5s  — abaque + impact
/usr/bin/python3 l60_flat_bar_check.py            # ~2s  — honnêteté données
/usr/bin/python3 data_concordance_check.py        # ~30s — pourquoi M1 abandonné
/usr/bin/python3 full_gate_rerun.py               # ~3-4 min — verdict final 4 gates (S037/S061/S096/S056/S062/S002)
/usr/bin/python3 robustness_clean_instruments.py  # ~2-3 min — robustesse L60
/usr/bin/python3 build_inventory.py               # ~1s  — inventaire final
```

Aucune opération git. Aucun chemin live (`ftmo_live/`, `Portfolio/`, `strategies/`,
`Futures/live/`, `.github/`, `*.mq5`) modifié — `Futures/live/strategy_c_live/signal_engine.py`
a été LU pour le chantier D, jamais écrit. VPS non utilisé. Δn_tests = 0 (correction de verdicts
existants sur un défaut d'instrument, aucune hypothèse neuve).
