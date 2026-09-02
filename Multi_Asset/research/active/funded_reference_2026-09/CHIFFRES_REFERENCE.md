# Chiffres de référence — compte FTMO funded déployé (<ACCOUNT_ID>)

2026-09-01. Lecture seule (repo + VPS via SSH). Aucune action live. Consolidation de 3 études
existantes de périmètres différents + relecture du code + vérification de l'état VPS. **Δn_tests = 0**
— rien n'est re-testé ici, seulement démêlé et vérifié.

**Chaque chiffre ci-dessous porte : (a) son périmètre — MONO déployé / book COMPLET / ORB seul —
(b) sa nature — MESURÉ live / SIMULÉ sur cohortes historiques / SUPPOSÉ (hypothèse de coût) — et
(c) sa source exacte (fichier).**

Unité : les simulations sortent en **`$`** (le compte `<ACCOUNT_ID>` est ouvert et libellé en **USD 10 000**,
confirmé `RAPPORT_STRATEGIE_2026-08-17.md:3` et `attribution/build_series.py:3`). Les frais de challenge
que tu cites (99 €, 267 € restants) sont en EUR. **Aucune conversion n'est faite ici** — ne pas
sommer les deux sans convertir. Là où je compare un chiffre € à un chiffre $, je le signale.

---

## TABLEAU DE RÉFÉRENCE — book réellement déployé (MONO : or et USDJPY à poids nul), coût ORB au niveau mesuré en live (2.17 bps RT, scénario `2.17_allin`)

Source : `Multi_Asset/research/active/funded_1y_mono_2026-08/out/{resume_deploye.csv,cohortes_deploye.csv.gz}`,
généré par `code/run_deploye.py`. **SIMULÉ** sur cohortes historiques 2013-2025 (indices/FX), pas sur
le vécu réel du compte.

| Horizon | N cohortes (N *indépendant* estimé) | P(net > 0) | Net médian | p10 | Risque de bust | Nature du bust | Délai médian du bust |
|---|---|---|---|---|---|---|---|
| 3 mois | — | **non simulé** sur le book MONO | — | — | — | — | — |
| 6 mois | — | **non simulé** sur le book MONO | — | — | — | — | — |
| **1 an** | 305 (**≈13** indépendantes) | **94.8 %** | **+$379** | **+$57** | **0.0 %** (0/305, tous scénarios de coût) | n/a — aucun bust observé | n/a |
| **5 ans** | 204 (**≈2.6** indépendantes) | **95.1 %** | **+$1 991** | **+$183** | **3.9 %** (8/204) | **100 % `floor`** (barrière statique −10 %, 0 % `daily`) | **médiane 694 j / min 420 j** (≈1.9 an / 1.2 an) |

**Ce que ce tableau ne dit pas et qu'il faut lire avant d'agir : la colonne « N indépendant » à 5 ans
vaut ~2.6.** Le P(net>0) et le risque de bust à 5 ans reposent sur environ **deux histoires
indépendantes**, pas 204 tirages — voir §A.2. Les 305/204 cohortes de la colonne N sont des fenêtres
qui démarrent tous les ~14 jours sur les mêmes ~12.7 ans d'historique : elles se recouvrent à 95-99 %,
ce ne sont pas des tirages indépendants.

Les colonnes 1 an / 5 ans ci-dessus utilisent le scénario de coût ORB **le plus proche du coût mesuré
en live** (2.17 bps ≈ 2.11 bps mesuré, §C). La fourchette complète sur les 5 hypothèses de coût
(`ORB_OFF` à `3.00_pessim`) est dans la section A — le risque de bust à 5 ans varie de **0 % à
13.7 %** selon l'hypothèse retenue, de façon **non monotone** en fonction du coût (voir §C).

---

## A. Le book déployé — chiffres complets

### A.1 Ce qui est simulé, et sur quoi

`code/run_deploye.py` prend le moteur `engine_v22` + `funded_instr.run_funded_instr`, force
`WT_mono = 0` sur or et USDJPY (« or = 0, J1 = 0 (regime actuel) », commentaire ligne 39), garde
`orb_risk = 0.0025` (le binaire déployé) et fait tourner 5 hypothèses de coût ORB × 2 horizons
(252j / 1260j trading) × cohortes tous les ~14 jours calendaires de 2013-10-01 à ~2026 (`vm=1.0`,
`wd_every=14`, `SPLIT=0.8` — le split trader FTMO 80 % est déjà appliqué dans `net_trader`).

### A.2 Le chevauchement — quantifié

Départs de cohorte espacés de 14 jours calendaires en médiane (`np.diff(starts)` = 14/15/16/18j).

- **1 an (horizon 252j de trading ≈ 365j calendaires)** : span total utilisé 2013-10-01 → ~2026-06,
  soit **≈12.7 ans**. N_eff = span / horizon ≈ **12.7 blocs indépendants**. Les 305 cohortes
  affichées sont donc ~24× plus nombreuses que l'information indépendante qu'elles contiennent.
- **5 ans (horizon 1260j ≈ 5 ans calendaires)** : même span (~12.8 ans) / 5 ans ⇒ **N_eff ≈ 2.6**.
  Les 204 cohortes à 5 ans recouvrent en pratique **moins de 3 périodes historiques distinctes**
  (grosso modo : 2013-2018, 2018-2023, un bout de 2023-2026). Le `bust_pct` à 5 ans peut être
  entièrement porté par UN régime (ex. un seul épisode de vol qui traîne dans plusieurs cohortes
  qui se chevauchent).

**Conséquence : ne présente jamais le P(>0) ou le bust% à 5 ans comme une fréquence sur 204 tirages.
C'est une fréquence sur ~2-3.**

### A.3 Distribution complète du net, par horizon et scénario de coût

Source : `resume_deploye.csv` (colonnes `net_med`, `net_moy`, `p10`, `p90`, `p_pos`, `bust_pct`).

| horizon | scénario coût ORB | N | bust % | net médian | net moyen | p10 | p90 | P(net>0) | payouts moy. |
|---|---|---|---|---|---|---|---|---|---|
| 1 an | `ORB_OFF` (pas d'ORB, référence) | 305 | 0.0 % | $235 | $259 | $30 | $476 | 96.1 % | 5.3 |
| 1 an | `era` (coût ledger historique) | 305 | 0.0 % | $390 | $450 | $69 | $891 | 93.8 % | 5.8 |
| 1 an | `0.96_mesure` (spread live 08-17) | 305 | 0.0 % | $485 | $524 | $131 | $925 | 97.4 % | 6.6 |
| 1 an | **`2.17_allin` (≈ coût mesuré actuel)** | 305 | 0.0 % | **$379** | $428 | **$57** | $846 | **94.8 %** | 5.5 |
| 1 an | `3.00_pessim` (au-delà de la frontière de mort) | 305 | 0.0 % | $309 | $370 | $27 | $793 | 91.8 % | 4.8 |
| 5 ans | `ORB_OFF` | 204 | 0.0 % | $1 195 | $1 125 | $427 | $1 572 | 100.0 % | 23.7 |
| 5 ans | `era` | 204 | 2.0 % | $2 204 | $1 829 | $147 | $2 868 | 94.1 % | 25.8 |
| 5 ans | `0.96_mesure` | 204 | **13.7 %** | $2 573 | $2 219 | $367 | $3 134 | 98.0 % | 30.1 |
| 5 ans | **`2.17_allin`** | 204 | **3.9 %** | **$1 991** | $1 678 | **$183** | $2 569 | **95.1 %** | 23.1 |
| 5 ans | `3.00_pessim` | 204 | 5.4 % | $1 582 | $1 332 | $89 | $2 194 | 93.6 % | 17.7 |

**Non-monotonicité à noter** (ce n'est pas une erreur, vérifié directement sur `cohortes_deploye.csv.gz`) :
le bust% à 5 ans **n'augmente pas avec le coût** — `0.96_mesure` (le scénario le MOINS cher) a le
bust le PLUS élevé (13.7 %), au-dessus de `3.00_pessim` (5.4 %). Le coût ORB change la trajectoire
(quels trades sont pris, avec quelle taille résiduelle après stop), pas seulement son niveau moyen —
un coût plus faible peut laisser courir des trajectoires qui, sur cet historique précis, traversent
le plancher plus souvent. Avec N_eff≈2.6, ceci est de la **path-dependence sur 2-3 histoires**, pas
une loi generale coût↑⇒risque↑.

### A.4 Bust : taux, nature, délai — vérifié

- **51 busts au total**, TOUS `bust_kind == "floor"` (0 `daily`), TOUS à l'horizon **5 ans** (0 bust
  à 1 an, dans les 5×305 = 1525 cohortes 1-an). Confirmé directement sur `cohortes_deploye.csv.gz`
  (`busted==True` → 51 lignes, `bust_kind.value_counts()` → `floor: 51`).
- ⚠️ **Ces 51 busts sont la SOMME des 4 scénarios de coût réels** (era 4 + `0.96_mesure` 28 +
  `2.17_allin` 8 + `3.00_pessim` 11 = 51), pas les busts d'un seul scénario canonique. Le nombre
  « 51 » que tu as cité est correct en valeur absolue mais mélange 4 hypothèses de coût différentes
  dans un seul pool.
- **Délai (bust_date − start), pooled sur les 51** : min **420 j**, médiane **757 j**, moyenne
  **782 j**, p75 **960 j** — confirme exactement tes chiffres. Par scénario, la médiane bouge :
  `0.96_mesure` 946 j, `2.17_allin` 693.5 j, `3.00_pessim` 560 j, `era` 609 j — le scénario le moins
  cher est aussi celui qui met le plus longtemps à casser (cohérent avec §A.3 : c'est aussi celui qui
  casse le plus souvent, juste plus tard).
- **Nature du bust `floor`** : `bust_bal0` médian ≈ **$9 090**, `bust_eq` médian ≈ **$8 978** — un
  franchissement lent et marginal du plancher statique $9 000, pas un choc violent. Cohérent avec
  `n_brk` (compteur de breaker daily) = **0 pour les 51 busts** : aucun de ces busts n'est passé par
  un breaker intrajournalier, c'est une érosion multi-mois.

### A.5 Net des cohortes qui bustent — ta phrase « buster ne veut pas dire perdre »

**Partiellement vérifiée, avec une correction de périmètre.** Sur les **51 busts pooled** (4 scénarios
mélangés) : `net_trader` médian = **$92**, pas $248. Le chiffre **+$248** que tu cites est réel mais
c'est la médiane du **sous-groupe `0.96_mesure` seul** (28/51 busts, `net_trader` médian **$248.38**,
moyenne $246.6) — le scénario le moins cher, qui est aussi celui qui buste le plus souvent (13.7 %) et
qui rapporte le plus aux non-bustés (net médian global $2 573). Les 3 autres scénarios sont bien plus
proches de zéro : `2.17_allin` médiane busts **$3.49** (quasi nul), `3.00_pessim` $47, `era` **$0**
(médiane exactement nulle sur 4 busts). **Le message qualitatif tient** (un compte qui atteint le
plancher statique après avoir déjà encaissé plusieurs payouts finit net positif dans la majorité des
cas), mais l'ampleur ($248) est optimiste — au scénario de coût le plus réaliste aujourd'hui
(`2.17_allin`), le net médian des comptes qui bustent est **quasi nul (~$3)**, pas +$248.

---

## B. Réponse directe : es-tu quasi sûr d'une EV positive, ou peux-tu perdre en continu jusqu'à 9 000 ?

**À 1 an (le seul horizon avec une puissance statistique correcte, N_eff≈13) : le livre historique ne
produit AUCUN bust, sur AUCUN des 5 scénarios de coût, sur les 12.7 ans testés.** P(net>0) 92-97 %
selon le coût. Ce n'est pas une certitude mathématique (12-13 histoires indépendantes, pas 305), mais
c'est un signal cohérent et robuste au coût — y compris au scénario pessimiste (3 bps).

**À 5 ans, la réponse change de nature : ce n'est plus « quasi sûr », c'est un vrai risque de queue.**
3.9 % à 13.7 % de probabilité de perdre en continu jusqu'au plancher statique $9 000 (**floor**, pas
**daily** — pas un choc, une érosion lente), avec un délai médian de ~2 ans. Mais cette probabilité
est mesurée sur ~2.6 histoires indépendantes : elle peut être dominée par UN régime de marché
(ex. 2022 taux) présent dans plusieurs cohortes qui se recouvrent. **Ni « c'est sûr », ni « c'est du
bruit » — c'est un risque réel mais mal quantifié par manque d'historique indépendant.**

**Horizon pertinent pour rentrer dans tes ~267 € restants** (frais 99 €, `_meta/roadmap_ftmo_2026.md`
ne donne pas de break-even mensuel pour le book MONO — seulement pour le book COMPLET, périmètre
différent, voir §D) : **aucune statistique MONO n'existe en dessous d'1 an.** Le point le plus proche
que je peux te donner honnêtement est le **p10 à 1 an = +$57** (scénario coût mesuré) — c'est-à-dire
que même dans le decile bas, le livre a historiquement fini l'année en territoire positif, mais
**$57 ne couvre pas ~267 €** au taux de change actuel quel qu'il soit. Le vécu réel à 15 jours
(§E) est **négatif** en ce moment — voir plus bas avant de conclure quoi que ce soit sur le délai
réel de retour sur frais.

---

## C. Attribution ORB vs overnight — l'ORB apporte-t-il ou détruit-il de la valeur ?

Source : bloc « CONTRIBUTION DE L'ORB » de `run_deploye.log`, delta vs `ORB_OFF` même horizon.

| horizon | scénario | Δ net médian vs ORB_OFF | Δ bust % vs ORB_OFF | Δ p10 vs ORB_OFF |
|---|---|---|---|---|
| 1 an | era | +$155 | +0.0 pt | +$39 |
| 1 an | 0.96_mesure | +$250 | +0.0 pt | +$101 |
| 1 an | **2.17_allin** | **+$144** | +0.0 pt | **+$27** |
| 1 an | 3.00_pessim | +$74 | +0.0 pt | **−$3** |
| 5 ans | era | +$1 009 | **+2.0 pt** | −$280 |
| 5 ans | 0.96_mesure | +$1 379 | **+13.7 pt** | −$61 |
| 5 ans | **2.17_allin** | **+$796** | **+3.9 pt** | **−$244** |
| 5 ans | 3.00_pessim | +$387 | +5.4 pt | −$338 |

**Le coût réel mesuré en live (18 fills depuis le 08-17, entrées moy. +0.909 bps, sorties moy.
+0.239 bps, dérapage RT moyen +1.148 bps — vérifié directement sur `fills.csv` : 9 allers-retours
`funded_orb_entry`/`funded_orb_exit`) plus le spread mesuré (~0.962 bps) donne ≈2.11 bps RT. C'est
quasiment exactement le scénario `2.17_allin` du sweep** — pas un point extrapolé, la ligne
`2.17_allin` du tableau ci-dessus EST la lecture pertinente pour l'ORB tel qu'il tourne réellement.

**Verdict** : sur 1 an, l'ORB **ajoute** de la valeur (+$144 médian, +$27 au p10, bust inchangé à
0 %) — gain net et gratuit en risque. Sur 5 ans, l'ORB ajoute toujours du rendement médian (+$796,
quasi ×2.7 le net médian sans ORB) **mais paie ce rendement en risque de queue** : +3.9 points de
bust ET le p10 se dégrade de **−$244** (le decile bas est PIRE avec ORB qu'sans, malgré une médiane
bien meilleure). L'ORB élargit la distribution — meilleure moyenne, queue basse plus longue. **⚠ 18
observations est un échantillon minuscule pour calibrer un coût de queue** ; le sweep de scénarios
(0.96 à 3.00 bps) montre que le résultat à 5 ans est sensible à ce paramètre de façon non triviale
(§A.3) — je ne recommande pas de trancher sur l'ORB à partir de ce seul point.

---

## D. Le coût du MONO — chiffré dans les deux sens

### D.1 Vérification de la source 82.5 %/53.7 %

Retrouvé dans `_meta/roadmap_ftmo_2026.md:67` : **« p(campagne) du livre déployé (MONO) = 53.7 % »**,
comparé au book COMPLET dans `Multi_Asset/research/active/audit_sleeve_gold_2026-08/RESULTS.md:370` :
**« 80.3 % → 53.7 % »**, explicitement attribué au **desk audit 2026-07-24**.

**⚠ Périmètre : CHALLENGE, pas funded.** `p(campagne)` = probabilité de RÉUSSIR un challenge (passer
P1+P2), pas la probabilité de rentabilité une fois funded. C'est le chiffre pertinent pour "combien de
temps/frais pour être funded", **pas** pour la question B ("suis-je rentable en tant que funded").
Les deux études du §A/§B (funded_1y_mono) sont **funded uniquement** (`WT_mono` appliqué à un compte
déjà funded, pas de simulation de challenge). Ne mélange pas les deux — c'est exactement l'erreur que
ce document corrige.

**⚠ Source non re-dérivée dans le repo.** `audit_sleeve_gold_2026-08/RESULTS.md:370` le dit
explicitement : *« Je ne peux donc ni confirmer ni réfuter le 80.3 % → 53.7 % du desk audit »* — cet
audit indépendant a testé une reconstruction proxy (ERC, pas le moteur v2.2/v2.8 réel) et n'a PAS pu
reproduire le calcul du desk audit lui-même. **Le 53.7 % / 80.3 % est donc un chiffre cité, pas un
chiffre vérifié dans ce repo.** Je ne l'ai pas retrouvé dans un fichier `.py`/`.csv` que je puisse
ré-exécuter — `desk_audit_2026-07-24` existe en mémoire de session, pas comme artefact reproductible
trouvé dans le worktree.

Autre nuance : la composition exacte de « MONO » a **changé dans le temps**. L'audit du 08-04
(`audit_sleeve_gold_2026-08`) définit MONO comme **« J1+ON, sans or »** (J1 actif, or éteint) pour son
étude p(pass)/SR. L'état LIVE vérifié aujourd'hui (§E) montre **`ea_w_xauusd=0.0` ET
`ea_w_usdjpy=0.0`** — J1 est ÉGALEMENT éteint (gate en zone `t_off=160`, prix 160.092). Le book MONO
d'aujourd'hui n'est donc **pas identique** au « MONO » du 53.7 % (qui gardait J1). Le book
`funded_1y_mono_2026-08` (§A) est le seul des trois à matcher exactement l'état live actuel (or=0
**et** J1=0, commentaire `run_deploye.py:39`).

### D.2 L'autre sens : ce que le MONO éteint côté busts

Confirmé sur `funded_anatomy_2026-07/AUDIT.md` §1.3 : sur les 58 busts du book COMPLET (191 cohortes,
2 ans/cohorte, gate ON), **100 % sont attribués à un dom-leg USDJPY (36) ou XAUUSD (22)** — les deux
seules jambes que le MONO éteint. 98.3 % de ces busts sont de type **`daily`** (barrière −5 %
intrajournalière, chocs de marché réels : 2015-08-24 déval. yuan, 2021-01-07 reflation post-Georgia,
2023-12-07 pivot BoJ). Le book MONO simulé (§A) a **zéro bust `daily` à 1 an ET à 5 ans**, sur les 5
scénarios de coût — cohérent avec le mécanisme : sans or ni JPY, il ne reste plus de jambe capable de
produire un choc intrajournalier assez violent pour franchir la barrière quotidienne.

### D.3 Bilan net

Le MONO **échange un risque contre un autre**, pas un risque contre rien :
- **Il tue** : le risque de bust **rapide, choc de marché, type `daily`** — celui qui domine 100 % du
  book COMPLET (58/58 busts).
- **Il paye** : ~27 points de p(campagne) au challenge (**82.5→53.7 %, non re-vérifié dans ce repo**,
  périmètre CHALLENGE) et **ouvre** un risque `floor` lent — 0 % à 1 an mais jusqu'à 13.7 % à 5 ans
  selon le coût ORB (§A.4), un mécanisme totalement absent du book COMPLET (`0 %` bust `floor` dans
  `funded_anatomy`).
- **Les deux études ne sont pas directement comparables** : `funded_anatomy` simule des cohortes de
  **504 jours de trading (~2 ans)**, `funded_1y_mono` simule 252j et 1260j — aucun horizon commun
  exact, et les moteurs diffèrent (`funded_anat_engine.py` vs `funded_instr.py`). Le bilan qualitatif
  (choc rapide contre érosion lente) tient ; le bilan chiffré point-à-point ne peut pas être fait sans
  re-simuler le book MONO à 504 jours ou le book COMPLET à 252/1260 jours — **hors périmètre ici
  (Δn_tests=0)**.

---

## E. État live et écart aux simulations

### E.1 État vérifié directement sur le VPS (lecture seule, 2026-09-01 ~02:04 UTC serveur)

`state.json` et `targets.json`, `/home/algo/.wine/drive_c/Program Files/FTMO Global Markets MT5
Terminal/MQL5/Files/` :

| champ | valeur relevée | ta note (2026-09-01) | écart |
|---|---|---|---|
| balance | $9 948.49 | 9 948,49 | ✓ identique |
| equity | $9 937.71 | 9 942,09 | proche (equity bouge en continu, normal) |
| plancher statique | $9 000.00 | 9 000 | ✓ |
| **plancher journalier** | **$9 448.49** | 9 473,60 | ⚠ **écart réel** — le plancher journalier se recalcule chaque jour sur `anchor_balance` (5 % de $9 948.49 ≈ $497), ta valeur date d'un jour où l'ancre était différente. Toujours vérifier `state.json` au jour J, ne pas mémoriser un plancher journalier d'une session antérieure. |
| open_days | 10 | 10 | ✓ |
| ea_w_xauusd / ea_w_usdjpy | 0.0 / 0.0 | 0.0 / 0.0 | ✓ MONO confirmé |
| ea_on_w | 0.35 | 0.35 | ✓ |
| ea_orb_risk | 0.0025 | 0.0025 | ✓ |
| gate J1 | t_off 160 / t_on 155 / n_resume 10, level 160.092 | identique | ✓ |
| or à poids nul | vote 2-1, \|sig\| 0.3333 < seuil 0.34 | — | cohérent avec `j1_gate.reason: "in_zone"` |

**Deux éléments présents dans l'état live et absents de ta note, à connaître** :
1. `"last_error": "kill-file FLAT — EA désarmé"` — un kill-file `FLAT` est actuellement posé, l'EA
   n'ouvre plus de nouvelles positions. Les positions existantes (US100 0.12 lot, GER40 0.11 lot,
   toutes deux longues) restent ouvertes — ce n'est pas un flat forcé des positions, juste un arrêt
   des nouvelles entrées. Je ne sais pas depuis quand ni pourquoi (pas d'historique de kill-file
   consulté, lecture seule) — à vérifier de ton côté si ce n'est pas une action délibérée récente.
2. `"spec_bounds_breach": 1` — les swaps live ont dérivé au-delà de ±25 % de leur ancre sur les 4
   jambes (ex. USDJPY swap long +3.40 vs ancre +0.96 = +122 %, US100 swap short −41.68 vs ancre
   +27.49 = +252 %). C'est un flag de dérive de calibration, pas un breach de compte.

### E.2 Réalisé vs simulé — comparaison directe

Balance à l'armement funded (2026-08-17) : **$10 000** exact (`RAPPORT_STRATEGIE_2026-08-17.md:3`).
Balance à J+3 (2026-08-20, `roadmap_ftmo_2026.md:3`) : **$10 013.88** (+$13.88). Balance aujourd'hui
(J+15 calendaires, `open_days=10`) : **$9 948.49**.

**⇒ Net réalisé depuis l'armement funded : −$51.51.** Le compte est actuellement **en perte** depuis
le début du funded, après un pic à +$13.88 à J+3.

Comparé à la distribution simulée 1-an (§A.3, `2.17_allin`) : médiane +$379, p10 +$57 — **les deux
bornes basses de la distribution simulée sont positives, le vécu réel à J+10 (jours de trading) est
négatif.** Ce n'est **pas nécessairement une contradiction** : 10 jours de trading, c'est ~4 % d'une
année de 252 jours — bien trop court pour situer le compte dans un percentile de la distribution
annuelle (qui décrit le NET CUMULÉ EN FIN D'ANNÉE, pas un point intermédiaire — le chemin d'une
cohorte gagnante passe forcément par des segments négatifs). **Aucune conclusion statistique valable
ne peut être tirée de 10 jours de P&L contre une distribution à horizon 1 an.** Ce que je peux dire
honnêtement : le début est mou, pas alarmant, et surtout **pas informatif** au sens statistique du
terme sur 4 % de l'horizon de référence.

**Coût ORB mesuré (§C) confirmé indépendamment** : recalcul direct sur `fills.csv` (9 A/R
`funded_orb_entry`/`funded_orb_exit` depuis le 08-17) → entrées moy. **+0.909 bps**, sorties moy.
**+0.239 bps**, dérapage RT moyen **+1.148 bps** — identiques aux chiffres que tu cites au bps près.
C'est un des rares chiffres de ce dossier qui est du **mesuré pur**, pas du simulé.

### E.3 Ce qui est périmé

- `funded_anatomy_2026-07` (juillet) et `funded_1y_mono_2026-08` (fin août) datent tous les deux
  **d'avant** le funded réel (armé 08-17) — aucun des deux n'intègre le vécu live. Aucune contradiction
  formelle détectée à J+10 (§E.2), mais l'échantillon est trop court pour trancher.
- `audit_sleeve_gold_2026-08` (04-08) décrit un MONO avec J1 actif — le book live actuel a J1 ÉTEINT
  (§D.1). Son p(pass)/SR ne s'applique plus à la composition actuelle du book.
- Aucune étude ne couvre le book MONO **exact d'aujourd'hui** (or=0, J1=0, ORB au coût mesuré) sur un
  horizon 3-6 mois — c'est le trou le plus net de ce dossier (§B).

---

## Sources (fichiers cités, tous relus)

- `Multi_Asset/research/active/funded_1y_mono_2026-08/code/run_deploye.py` (lu en entier)
- `Multi_Asset/research/active/funded_1y_mono_2026-08/out/resume_deploye.csv`,
  `out/cohortes_deploye.csv.gz`, `out/run_deploye.log` (hors worktree, cache local gitignored,
  importé par chemin absolu depuis le main dir — lecture seule)
- `data/ftmo_portfolio/funded_anatomy_2026-07/AUDIT.md`, `STUDY.md`, `run_all_funded.py`
- `Multi_Asset/research/active/audit_sleeve_gold_2026-08/RESULTS.md`
- `_meta/roadmap_ftmo_2026.md`
- `Multi_Asset/research/active/funded_1y_mono_2026-08/RAPPORT_STRATEGIE_2026-08-17.md`,
  `CARTE_EV_2026-08-20.md`
- `data/ftmo_portfolio/v22/config_v22.py` (FUNDED_HORIZON=504, FUNDED_STEP=12)
- VPS `<ACCOUNT_ID>` : `state.json`, `targets.json`, `fills.csv` (SSH ControlMaster, lecture seule)
