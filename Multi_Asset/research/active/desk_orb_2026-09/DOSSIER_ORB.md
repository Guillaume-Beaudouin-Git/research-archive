# Dossier de décision — `funded_orb`, go/no-go octobre 2026

**Rôle : quant researcher senior, dossier ORB seul.** Le collègue overnight travaille en
parallèle (`regime_diagnostic_2026-09`, `macro_context_2026-09` — cités, non dupliqués). Tout ce
qui suit est **nouveau** sauf mention explicite « repris de » ; les acquis (`orb_cost_funded_2026-08`,
`audit_ledger_orb_2026-08`, `orb_variants_2026-08`) sont cités, pas re-mesurés.

**Sleeve** : `FU_ORB_RISK=0.0025`, compte funded <ACCOUNT_ID> depuis 2026-08-17. US100 CFD, OR
09:30-10:00 ET (30 min), stop niveau opposé, pas de TP, sortie stop ou clôture RTH (~16:00 ET).
Ledger `PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet`, N=4013,
2010-06-07→2026-05-29.

**Modèle de coût utilisé dans ce dossier** : coût round-trip appliqué **par trade** via le levier
réel `lev = level/|level-stop_eff|` (pas un levier médian uniforme — méthode d'`audit_ledger_orb_2026-08`,
reproduite et validée ci-dessous : ALL t=1.532/LONG t=1.694/SHORT t=0.543 à 0.962 bps, contre
1.530/1.693/0.542 publiés — écart de 5ᵉ décimale). Trois nombres cités partout dans ce dossier,
**MESURÉS** (indépendamment recalculés ici, méthode par-trade) :

| | point mort (mean R_net=0), bps RT |
|---|---:|
| SHORT | **1.694** |
| ALL (two-sided agrégé) | **2.189** |
| LONG | **2.610** (nouveau, non publié ailleurs) |

---

## D. La matrice de décision

**Verdict de robustesse (détail en §A)** : le two-sided 2022-2026 **ne survit pas** à un test de
rupture endogène (Bai-Perron search-adjusted p=0.266 ; CUSUM stable, aucune instabilité détectée
au seuil 5%). La ligne « ROBUSTE » ci-dessous est un **contrefactuel pédagogique** — ce n'est PAS
la conclusion de ce dossier, elle sert à montrer ce que la matrice aurait dit si le résultat avait
tenu. La ligne opérante est **NON ROBUSTE**.

| Coût final | < 1,69 bps | 1,69 – 2,17 bps | > 2,17 bps |
|---|---|---|---|
| **ROBUSTE** (contrefactuel — non confirmé) | **Two-sided.** SHORT sous son point mort (1,694), 2022-2026 t=2,10 (n=528, §A1). | **Long-only.** SHORT économiquement mort (>1,694), ALL encore positif en moyenne (<2,189), porté par LONG. | **Désarmer.** ALL franchit son point mort (2,189) : plus aucune configuration n'est positive en moyenne. |
| **NON ROBUSTE** (ce que ce dossier trouve) | **Long-only, sous dérogation bornée** — pas « garder two-sided » : la justification du SHORT (rupture 2022) est indiscernable du bruit (p=0,266) et le SHORT échoue R2 **à tout coût, y compris coût nul** (t=1,260 gross, §A2/audit_ledger). LONG seul t=1,694 à 0,962 bps — sous R2 (2,0), pas un pass, la seule jambe qui n'est pas déjà écartée par la rupture. | **Long-only, dérogation resserrée.** SHORT négatif en moyenne (§ tableau ci-dessous) en plus de n'avoir jamais été significatif. LONG t tombe à 0,52-0,45 dans cette bande — proche de zéro, aucune base statistique nouvelle pour élargir l'exposition. | **Désarmer.** ALL négatif (>2,189), LONG lui-même t=0,43 (2,19 bps) — même la jambe la moins mauvaise est statistiquement indiscernable de zéro. Coïncide avec la règle A1 déjà gelée (>2,5 bps tout-compris ⇒ désarmer). |

**Où sommes-nous, chiffre à l'appui (§C)** : coût total mesuré actuel **≈ 2,11 bps** [IC95
bootstrap 1,56–2,62] → **bande du milieu**, ligne NON ROBUSTE ⇒ cellule **« long-only, dérogation
resserrée »**. Le haut de l'IC (2,62) dépasse déjà le seuil de désarmement gelé de la dérogation
(2,5 bps, `AMENDEMENT n°1` A1) — pas une action à prendre aujourd'hui (N=9 paires, IC large), mais
un signal que la marge restante avant désarmement automatique est plus mince que le point central
(2,11) ne le suggère seul.

**Sur l'objection « long-only = bêta » (re-testée, §D3)** : elle ne se confirme PAS pleinement
mais elle n'est pas nulle non plus — β annuel de la jambe LONG seule à `bh_us100` = **+31,7 (t=3,03,
significatif)**, R²=**17,8 %** (n=15 années complètes) : sous le seuil L38 de 30 % qui définirait
« pas orthogonal », mais un β statistiquement réel, contrairement au livre COMBINÉ (β=+6,6, t=0,38,
R²=0,25 %, réplication indépendante du β≈0 de `regime_diagnostic_2026-09`). **Choisir la cellule
long-only, c'est accepter une exposition-β modeste mais mesurée, pas nulle.**

---

## A. Le two-sided 2022-2026 est-il robuste, ou un artefact de découpage ?

**Résultat : NON — deux tests indépendants de rupture endogène ne détectent rien de distinguable
du bruit, malgré une date de rupture estimée (2021-11-26) étonnamment proche du découpage
informel « 2022 ».** C'est cette proximité même qui rend le découpage a posteriori convaincant à
l'œil — et c'est exactement ce qu'un test corrigé de la recherche doit percer.

### A1 — combien de temps le signal tient (fenêtres roulantes, code `a_break_test.py`)

Fenêtre **expanding depuis la fin** (2026-05-29), jambe SHORT nette de coût (0,962 bps) :

| départ | n | mean R | t HAC6 |
|---|---:|---:|---:|
| 2020 | 746 | +0,081 | 1,79 |
| 2021 | 642 | +0,104 | **2,05** |
| 2022 | 528 | +0,123 | **2,10** (maximum de la série) |
| 2023 | 399 | +0,109 | 1,57 |
| 2024 | 282 | +0,124 | 1,36 |
| 2025 | 162 | +0,078 | 0,73 |
| 2026 (partiel) | 44 | −0,016 | −0,09 |

Le t **culmine à 2,10 pour la fenêtre 2022→2026** (528 trades) — c'est le meilleur point de toute
la série expanding, ce qui explique pourquoi ce découpage précis a été repéré. Mais il ne dépasse
JAMAIS 2,10 dans aucune fenêtre roulante à longueur FIXE de 2 ans balayée sur toute l'historique
(`a1b_rolling_2y_short_leg.csv`, 28 fenêtres, max observé 1,79). Le t=2,10 de la fenêtre "2022"
n'est donc pas un plateau stable — c'est un pic obtenu en POOLANT deux fenêtres de 2 ans chacune
individuellement sous le seuil. Et essayer de resserrer sur le régime le plus « actuel » (2023+,
2024+…) fait DÉCROÎTRE le t de façon quasi monotone jusqu'à un signe négatif sur les 44 derniers
trades. **Le signal ne s'étend, ni vers le passé (dilué par le pré-2022), ni vers l'avenir (érodé
par les données les plus récentes) — sa durée de vie utile tient sur une fenêtre étroite (~4 ans),
et un an de recul suffit déjà à le faire retomber sous 1,4.**

### A2 — date de rupture ESTIMÉE (Bai-Perron 1-break, pas imposée)

Recherche par minimisation-SSE sur la jambe SHORT (N=1857, trim 10-90 %), statistique = `|t|`
d'un test de rupture de moyenne à chaque point candidat (~1486 candidats) :

- **Date de rupture estimée : 2021-11-26** (index 1316/1857) — moyenne avant −0,029 (n=1316),
  moyenne après **+0,127** (n=541), `|t|`=**2,288**.
- **P-value ajustée de la recherche** (bootstrap par blocs, block=20, 500 tirages, null =
  max-statistique-sur-1486-candidats rejouée sur des données mélangées) : la médiane du bruit
  pur est déjà **1,95**, le p90 est **2,85** — un `|t|` de 2,288 obtenu en cherchant le MEILLEUR
  point de coupure parmi ~1486 candidats **n'a rien d'exceptionnel** : **p=0,266**.
- La date estimée (2021-11-26) tombe à **6 semaines** de la coupure informelle « 2022 » — c'est
  précisément ce qui rend le découpage a posteriori plausible à l'œil, et précisément ce que la
  correction de recherche neutralise : un chercheur qui balaie 1486 points de coupure trouvera
  presque toujours SON meilleur point quelque part près du milieu de l'historique récent, sans
  qu'aucune rupture réelle n'existe.

### A3 — CUSUM (test de stabilité indépendant, même jambe)

`max|CUSUM|` = **1,068**, sous la borne critique à 5 % (**1,36**, borne de Kolmogorov pour un
pont brownien standardisé). **Aucune instabilité détectée.** Le maximum du CUSUM tombe d'ailleurs
le **2019-05-23** — ni en 2022, ni près de la date estimée par Bai-Perron — signature typique
d'une série dont les fluctuations locales de moyenne restent dans l'enveloppe attendue sous
stationnarité, pas d'un régime qui change de nature à une date identifiable.

### A4 — recoupement avec le walk-forward déjà mesuré (repris, pas refait)

`orb_cost_funded_2026-08/RESULTS.md` R4 : walk-forward expanding 5 folds au coût mesuré, **2/5
folds positifs (40 %)**, sous RESEARCH_PASS (50 %). Les deux folds positifs sont **les deux
derniers** (2021-02→2023-10 t=1,83 ; 2023-10→2026-05 t=2,04) — cohérent, à la fois dans le signe
et dans l'ordre de grandeur du t, avec le pic trouvé ici en A1 (fenêtre 2022→2026, t=2,10). Les
trois analyses (A1 sunset, A2 Bai-Perron, walk-forward déjà publié) convergent sur le **même**
sous-échantillon récent comme source unique du signal — ce qui renforce, plutôt qu'atténue,
l'hypothèse d'un point de bascule choisi après coup : trois méthodes différentes retrouvent le
même pic parce qu'il y a réellement UN pic dans les données, pas parce qu'il y en a plusieurs
qui convergent indépendamment sur un mécanisme.

### Verdict A

**Le two-sided 2022-2026 ne survit pas à un test de rupture endogène.** La rupture est réelle au
sens où le P&L est réel et sa date estimée tombe près du découpage informel — mais corrigée pour
la recherche sur ~1486 points candidats, elle est à **p=0,266** : indiscernable du meilleur point
qu'on trouverait en cherchant dans du bruit pur. Le CUSUM, méthode indépendante, ne détecte
aucune instabilité au seuil 5 %. Et même en acceptant le découpage tel quel, sa durée de vie
statistique est courte : un seul an de recul (2023+) fait déjà retomber le t sous 1,6, et les 44
derniers trades sont négatifs. **C'est un excellent résultat négatif, pas un échec de méthode : le
gate R2 pré-enregistré (audit_ledger_orb_2026-08) avait déjà exclu le SHORT au coût nul (t=1,260),
et cette section montre que même l'argument de rechange (« mais ça a changé de régime ») ne tient
pas non plus.**

---

## B. Puissance et déflation

### B1 — N nécessaire pour t=2,0

⚠ **Correction d'un chiffre du brief** : l'énoncé citait « espérance +0,049 R/trade contre σ 1,20 R
⇒ ~7596 trades pour t=2,0 ». Le +0,049 est le mean **GROSS** (0 coût, confirmé : `r_gross` plein
échantillon, mean=0,0492, σ=1,2008) — mais à ce mean-là, N requis pour t=2,0 est **2386**, pas
7596. Le chiffre 7596 correspond en réalité au mean **NET** mesuré (0,962 bps, mean=0,0276,
σ=1,2006) : `N=(2,0×1,2006/0,0276)² = 7595` — à 1 trade près du chiffre cité. **Le brief avait le
bon N mais l'avait adossé au mauvais mean** ; ce dossier utilise le calcul net (7595), cohérent
avec le fait qu'on ne peut pas ignorer le coût pour juger la puissance d'une décision de
production. On dispose de **4013** trades pleins, soit 53 % du N requis.

### B2 — puissance réelle sur 2022-2026 (n=1115 ALL, n=528 SHORT)

- En utilisant l'effet **plein-échantillon net** comme prior (mean=0,0276, σ=1,2006, le choix
  non-circulaire) : puissance à n=1115 = **12,0 %**. Chroniquement sous-alimenté.
- En utilisant le point estimé de la tranche elle-même comme s'il était vrai (mean=0,1232,
  n=528, SHORT) : puissance ex-post = **55,1 %** — **chiffre circulaire, cité pour mémoire
  seulement** : une « puissance » calculée à partir de l'estimation qui a produit la revendication
  n'est pas une preuve indépendante ; elle dit seulement « si le point est vrai, on avait une
  chance sur deux de le voir », ce qui n'aide pas à trancher s'il est vrai.

### B3 — effet minimum détectable (MDE), 80 % puissance, α=0,05 two-sided

| n | MDE (R/trade) |
|---|---:|
| 4013 (plein échantillon) | **0,0531** |
| 1115 (tranche 2022-2026) | **0,1007** |

**L'effet mesuré sur 2022-2026 (ALL, net) est +0,1054** — à peine au-dessus du MDE (0,1007) de
cette même tranche. C'est la signature numérique exacte d'un résultat qui **est juste à la limite
de ce qui est distinguable du bruit à cette taille d'échantillon**, ni confortablement significatif
ni clairement nul : la tranche est powered pour détecter à peu près exactement l'effet qu'elle a
trouvé, ce qui est cohérent avec — et renforce — le verdict A (un résultat qui affleure tout juste
son propre seuil de détection est exactement ce à quoi ressemble un tirage chanceux dans du bruit
à cette taille d'échantillon, pas nécessairement ce à quoi ressemble un edge réel sous-mesuré).

### B4 — DSR (Bailey-López de Prado, `dsr.py` du dépôt, bug rf/std_sr_trials déjà corrigé 2026-08)

Dispersion des trials (`std_sr_trials`) estimée sur la famille locale ORB — grille
`orb_variants_2026-08` (34 variantes uniques après exclusion des 3 Globex, artefact mécanique déjà
documenté) : Sharpe annualisé par variante (fréquence propre à chaque variante, ex. `cal_Mon_only`
≈50 trades/an vs ancrage ≈251/an) → **std_sr_trials = 4,13** (annualisé), très supérieur au plancher
de bruit pur (0,25) — dispersion tirée en bonne partie par une variante à N=44 (`filter_OR_over_ATR_gt1`),
signalé comme limite.

| échelle | n_trials | Sharpe observé (net, annualisé) | benchmark E[max SR] | DSR | pass (≥0,95) |
|---|---:|---:|---:|---:|---|
| local ORB (grille) | 37 | 0,364 | 8,78 | **0,0000** | non |
| cumul registre | 1999 | 0,364 | 14,25 | **0,0000** | non |

**Aux deux échelles, DSR ≈ 0 — décisif, pas marginal.** Le Sharpe net observé (0,364 annualisé,
≈251 trades/an) est un ordre de grandeur sous le benchmark de sélection à N'IMPORTE quelle des deux
échelles ; même en retirant la variante la plus bruitée (N=44) de l'estimation de dispersion, le
Sharpe observé resterait très inférieur au benchmark — **ceci ne dépend pas d'un choix de
calibration marginal.**

### Effet minimum détectable (rapport final)

**0,0531 R/trade au plein échantillon (N=4013) ; 0,1007 R/trade sur 2022-2026 seul (n=1115).**
L'effet net mesuré plein-échantillon (0,0276) est SOUS son propre MDE (0,0531) — cohérent avec
t=1,53 < 2,0. L'effet net mesuré sur 2022-2026 (0,1054) est À PEINE au-dessus de son MDE (0,1007)
— cohérent avec le verdict A (signal fragile, pas absent, pas établi).

---

## C. Le dérapage manquant

### Données — fills réels tirés du compte funded (VPS, lecture seule, `fills.csv`)

Le brief citait « 18/30 observations, entrées +0,909, sorties +0,239 → RT≈1,15 ». **Reproduit ici
depuis la source** : 9 paires entrée/sortie `funded_orb_entry`/`funded_orb_exit` (magic 220512,
2026-08-18→2026-08-31), soit 18 fills individuels sur la cible de 30 (`AMENDEMENT n°1`, règle A1).
Entrée mean = **0,9089** bps (reproduit à 4 décimales), sortie mean = **0,2389** bps (idem) —
confirmé au fill près depuis `fills.csv` du VPS, pas depuis un CSV intermédiaire.

⚠ **Écart à la règle HAC lag-6** : à N=9, un lag-6 consommerait l'essentiel des degrés de liberté
(estimateur HAC non identifié à cette taille). Les t/CI de cette section utilisent un t de Student
standard (df=n−1) **et** un bootstrap par blocs (block=1, justifié : trades non chevauchants, un
jour ne recouvre pas un autre) — les deux méthodes s'accordent à ±0,15 bps près, ce qui borne le
risque de sous-estimation de la variance sans invoquer un HAC non identifiable ici.

⚠ **Note méthodologique** : un échantillon ANTÉRIEUR (N=12, ordres-sonde 0,01 lot, magic 220510,
juin-août 2026, avant armement réel) donnait une entrée moyenne de **2,169 bps** — sensiblement
PLUS élevée que les 0,909 bps mesurés depuis sur les vrais fills armés. Les deux mécanismes ne
sont pas strictement comparables (taille d'ordre différente, ~0,01 lot vs 0,07-0,19 lot réel) ;
ce dossier retient les **fills réels armés** (N=9 paires) comme échantillon faisant foi pour la
décision — la sonde antérieure est un préalable historique, pas la mesure de production.

### C1 — décomposition L59 : entrée (stop-entry) vs sortie (time-stop / stop), séparément

| jambe | n | mean (bps) | sd | t (H0: mean=0, df=n−1) | CI95 |
|---|---:|---:|---:|---:|---|
| ENTRÉE (franchissement, stop natif) | 9 | +0,909 | 0,957 | 2,85 | [0,174, 1,644] |
| SORTIE, toutes (STOP + TIME confondus) | 9 | +0,239 | 0,576 | 1,24 | [−0,204, 0,682] |
| — dont SORTIE au STOP (3 trades, sortie <2h après l'entrée) | 3 | +0,590 | — | — | n trop petit |
| — dont SORTIE au TIME (6 trades, clôture ~22:00 Paris) | 6 | +0,063 | — | — | n trop petit |

**L'entrée porte presque tout le dérapage mesuré**, la sortie au TIME est quasi gratuite (0,063
bps sur 6 trades) — cohérent avec `audit_ledger_orb_2026-08 §4` (canal gap de sortie STOP mesuré
vide sur 1587/1587 trades M1, et sortie TIME = clôture déterministe, pas de canal de franchissement
au sens L59). **La distinction L59 tient** : ce ne sont pas deux dérapages de même nature — l'entrée
est un vrai franchissement de niveau (stop-entry, sujet au gap), la sortie TIME est un ordre marché
à heure fixe (sujet au spread au moment T, pas à un gap de niveau).

### C2 — coût total : IC actuel et valeur critique

RT total = spread natif mesuré (0,962 bps, fenêtre ORB, `>27 000 lignes`, passif) + dérapage
(entrée+sortie, mesuré ci-dessus sur les 9 paires) :

- **Point central : 2,110 bps** (0,962 + 1,148).
- **IC95 (t, df=8) : [1,446, 2,774].**
- **IC95 (bootstrap par blocs, 20 000 tirages, block=1 — trades non chevauchants) : [1,563, 2,623].**
  Les deux méthodes s'accordent à ±0,15 bps près ; le bootstrap est légèrement plus resserré.

**Ce point central (2,110) tombe DANS la bande [1,69 ; 2,17]** — ni sous le seuil de mort du SHORT,
ni au-dessus du seuil de mort du two-sided agrégé. C'est la bande du milieu de la matrice D.

### C3 — que faut-il observer sur les 12 fills restants (6 paires) pour trancher ?

Cible : N=30 fills (15 paires). À N=18 (9 paires), somme du dérapage cumulé = **10,33** (bps·trade).

| bascule visée | seuil sur le dérapage moyen (coût total < / > seuil) | somme requise sur les 6 paires restantes | moyenne requise/paire |
|---|---|---:|---:|
| **coût total < 1,69** (SHORT redevient économiquement vivant) | dérapage moyen ≤ 0,728 | ≤ 0,590 | **≤ 0,098 bps/paire** |
| **coût total > 2,17** (ALL/two-sided passe négatif en moyenne) | dérapage moyen ≥ 1,208 | ≥ 7,790 | **≥ 1,298 bps/paire** |

**Asymétrie nette** : basculer sous 1,69 exige que les 6 prochaines paires soient QUASIMENT sans
dérapage (0,098 bps/paire, contre 1,148 observé jusqu'ici — un ordre de grandeur d'écart). Basculer
au-dessus de 2,17 exige seulement une moyenne de 1,298 bps/paire, à peine 13 % au-dessus de la
moyenne déjà observée (1,148) — largement dans l'enveloppe déjà vue sur l'échantillon actuel (un
seul trade d'entrée à 2,83 bps, déjà observé le 2026-08-27, suffit à lui seul à faire basculer une
paire dans cette zone). **Le chemin le plus probable, si le dérapage récent est représentatif, est
vers le HAUT de la bande (>2,17), pas vers le bas.** Ceci est cohérent avec le fait que la borne
supérieure de l'IC actuel (2,62-2,77 selon la méthode) dépasse déjà le seuil de désarmement gelé
de la dérogation (2,5 bps, `AMENDEMENT n°1` A1) — pas un franchissement acté (N=9 encore loin de
30), mais une direction de risque, pas une garantie de sécurité.

---

## Δn_tests et seuil corrigé

5 tests formulés et évalués cette session (Šidák, tous en excluant les caractérisations
descriptives déjà couvertes ailleurs — walk-forward et grille de variantes citées, pas refaites) :

1. A1 — caractérisation par fenêtres roulantes (sunset + rolling 2 ans), SHORT leg
2. A2 — recherche de rupture Bai-Perron (1 break, endogène) + p-value ajustée par bootstrap
3. A3 — test de stabilité CUSUM
4. D — re-test β d'orthogonalité, jambe LONG seule, fréquence annuelle (méthode reproduite,
   restreinte à la jambe visée par l'objection, pas juste reprise du combiné)
5. D — même re-test à fréquence quotidienne, vol-targeté (résultat rejeté comme mécaniquement
   confondu, §D3 — compté car c'est une recherche qui AURAIT pu être le résultat retenu)

Cumul déclaré en entrée de session (`regime_diagnostic_2026-09`) : **1994**. Cumul après ce
sprint : **1999**. Seuil Šidák (familywise 5 %, n=1999) : **`|t| ≈ 4,21`**. Aucun t-stat cité dans
ce dossier ne l'approche — tout est présenté comme diagnostic, cohérent avec le fait qu'aucune
nouvelle revendication de PASS n'est faite ici.

### D3 — détail du re-test β (annexe, cité en §D)

Repris de `regime_diagnostic_2026-09` (combiné ALL, annuel, n=14 : β=−0,014, R²=0,000) —
**re-testé indépendamment ici, restreint à la jambe visée par l'objection** :

| jambe | fréquence | n | α (HAC) | β (HAC) | t_β | R² |
|---|---|---:|---:|---:|---:|---:|
| LONG | annuel (années pleines 2011-2025) | 15 | +2,78 (t=1,02) | **+31,74** | **+3,03** | **0,178** |
| SHORT | annuel | 15 | +4,03 (t=0,86) | −25,14 | −2,71 | 0,086 |
| ALL | annuel | 15 | +6,80 (t=0,93) | +6,60 | +0,38 | 0,003 |

**Lecture** : le livre COMBINÉ est bien orthogonal (R²=0,3 %, réplication indépendante du chiffre
de `regime_diagnostic_2026-09`, méthode différente — ici jours RTH complets via Databento, pas
le même pipeline). Mais LA JAMBE LONG SEULE porte un β annuel statistiquement réel (t=3,03),
sous le seuil L38 de « pas orthogonal » (R²=30 %) mais loin de zéro (R²=17,8 %). **La cellule
« long-only » de la matrice D n'est donc pas un choix sans coût d'exposition** — c'est un choix
qui échange l'incertitude du two-sided contre une exposition-β modérée et mesurée, pas nulle.

⚠ **Spécification rejetée, documentée pour ne pas la refaire** : la même régression à fréquence
**quotidienne** (vol-targetée) donne des R² de 50-57 % — un ordre de grandeur au-dessus de
l'annuel. Ce n'est PAS un signal plus fort : le rendement ORB d'un jour est un SOUS-INTERVALLE
temporel du rendement du jour complet (entrée après l'OR, sortie à la clôture), donc les deux
séries mesurent en grande partie le MÊME mouvement de prix sur la MÊME séance — comorbidité
mécanique, pas exposition structurelle. Le test pertinent pour « est-ce du bêta déguisé » est
l'agrégation à basse fréquence (annuel), qui isole si la P&L CUMULÉE de la stratégie suit l'indice
sur la durée — pas la comparaison intra-session.

---

## Sources et statut des chiffres

**Mesuré** (donnée réelle, ce dossier) : Task A (break tests), Task C (IC coût, projection N=30),
Task D3 (régression β). **Mesuré, repris d'acquis** : coût natif 0,962 bps (`orb_cost_funded_2026-08`),
points morts SHORT 1,694/ALL 2,189 (recalculés ici, cohérents avec `audit_ledger_orb_2026-08`),
walk-forward 2/5 folds (`orb_cost_funded_2026-08`), β combiné annuel n=14 (`regime_diagnostic_2026-09`).
**Simulé** : aucun (pas de simulation Monte-Carlo dans ce dossier). **Supposé** : le prior d'effet
utilisé en B2 (mean plein-échantillon comme "vrai" effet pour juger la puissance sur 2022-2026) —
choix explicite pour éviter la circularité, signalé comme tel.

## Fichiers

- `code/common.py` — chargeur ledger + modèle de coût par-trade (validé contre audit_ledger_orb_2026-08)
- `code/a_break_test.py` → `out/a1_sunset_expanding_from_end.csv`, `out/a1b_rolling_2y_short_leg.csv`,
  `out/a2_bai_perron_break.csv`, `out/a3_cusum_short_leg.csv`
- `code/b_power_dsr.py` → `out/b_power_summary.csv`, `out/b4_dsr.csv`
- `code/d_beta_retest.py` → `out/d_beta_orthogonality.csv`
- VPS `fills.csv` (lecture seule, SSH ControlPath, aucune écriture) — 18 fills armés réels
  (2026-08-18→2026-08-31), reproduits en §C.

## Conclusion en une phrase

**Le two-sided 2022-2026 ne survit pas à un test de rupture endogène** (Bai-Perron
search-adjusted p=0,266, CUSUM stable) ; au coût actuellement mesuré (≈2,11 bps, bande médiane
1,69-2,17), la décision statistiquement défendable est **long-only sous la dérogation bornée déjà
en place**, pas un élargissement à two-sided — et même cette jambe LONG reste sous R2 (t=1,69 à
0,962 bps) et porte une exposition-β modeste mais réelle (t=3,03, R²=17,8 %) qui n'existait pas
dans le narratif « orthogonal » du livre combiné. La règle de sortie déjà gelée (`AMENDEMENT n°1`,
N=30 fills, >2,5 bps ⇒ désarmer) reste, à l'issue de ce dossier, le bon mécanisme de gouvernance —
rien ici ne justifie de l'anticiper ni de la relâcher.
