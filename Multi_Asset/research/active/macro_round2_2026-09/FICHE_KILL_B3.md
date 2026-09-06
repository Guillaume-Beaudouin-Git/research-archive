# Fiche d'attribution de kill — axe B3 (drift post-FOMC sur les taux)

**2026-09-06.** Première application de la candidate « attribution-du-kill ».
**Δn_tests = 0** — aucune donnée touchée, aucun test lancé. Énumération seule.

## Le fait qui déclenche la fiche

L'axe B3, classé **prioritaire** par la synthèse du round 2, **a déjà été testé et tué** :
`data/personal_book/post_fomc_drift/` (pré-enregistré 2026-06-10, commit `2d13d5e`,
4 essais sur un cumul de 101, verdict NO-GO).

⚠ **Ni moi ni l'agent B n'avons balayé le dépôt avant de recommander cet axe.** C'est exactement
la faute que L48 décrit. Le balayage aurait coûté une minute.

L'étude existante est de bonne qualité et je ne la conteste pas : pré-enregistrement gelé avant
tout contact avec les données de sortie, 182 événements FOMC 2004-2026 reconstruits avec
provenance ligne à ligne (58/58 changements de cible appariés), déviations de source loguées
honnêtement, DSR calculé à N=101.

## Ce qui a été testé, exactement

| Axe | Valeur testée |
|---|---|
| Hypothèse | Brooks-Katz-Lustig (NBER w25127), drift post-FOMC sur les Treasuries |
| **Mesure de surprise** | **`d2y_bps` = variation du rendement CMT 2 ans sur la JOURNÉE entière** |
| Instrument | IEF (ETF 7-10 ans) |
| Seuil | 5 bps |
| Horizons | 5 / 10 / 20 jours ouvrés |
| Banque centrale | FOMC seule |
| Coût | 1,0 bp RT (tier futures) |

**Résultat** : brut poolé **+6,8 / +4,5 / −0,8 bps par événement**, t_HAC +0,46 / +0,24 / −0,08.
L'edge est **absent en brut**, pas tué par le coût. Et un motif de régime net :
- **avant 2015** (l'échantillon d'origine de BKL) : drift réel et bilatéral, **+22 bps/événement** à H=5
- **2015-2021** : seule la jambe dovish-long paie — le rallye séculaire de duration déguisé
- **2022+** : **le motif s'inverse franchement** (hawkish-short paie, dovish-long perd ~70 bps/événement à H=20)

## Énumération des axes NON variés

| Axe | Varié ? | Pourrait-il retourner le verdict ? |
|---|---|---|
| **Identification de la surprise** | ❌ **non** | **OUI — voir ci-dessous. C'est l'axe dominant.** |
| Instrument (IEF vs ZN) | ❌ non | Non — le rapport établit que le coût est immatériel, l'edge est absent en brut |
| Seuil (5 bps) | partiellement (1 essai) | Peu probable — ne change pas un brut nul en brut positif |
| Horizons | ✅ 3 valeurs | Non |
| Banques centrales (BCE, BoE, BoJ) | ❌ non | Marginal — augmenterait N, ne corrigerait pas un mécanisme absent |
| Régime | ✅ testé (K3) | Non — c'est ce test qui a révélé l'inversion |

## L'axe dominant, et pourquoi il est plausible

Le pré-enregistrement **admet lui-même la limite** :

> « We do NOT have Fed Funds futures; d(2y) is the pre-registered proxy, accepted as noisier
> (attenuation biases toward NO-GO). »

L'étude traite donc ce proxy comme du **bruit** qui atténue vers zéro. C'est prudent et correct
si le défaut est de la variance. **Mais la littérature dit que ce n'est pas de la variance, c'est
un MÉLANGE.**

Jarociński-Karadi : la variation de rendement le jour d'une annonce **confond deux chocs aux
dynamiques opposées** —
- un **choc de politique monétaire** (la Fed resserre plus que prévu → rendements ↑, actions ↓),
- un **choc d'information** (la Fed resserre parce que l'économie est forte → rendements ↑, actions ↑).

Une mesure qui les additionne peut rendre **zéro en moyenne alors que chaque composante est
non nulle**. Un brut poolé de +6,8 → −0,8 bps est exactement la signature d'une annulation, pas
nécessairement celle d'une absence.

Et surtout : **l'inversion de signe après 2022 constatée par l'étude est le symptôme que JK
prédisent** quand la composition du mélange change. L'étude l'a interprétée comme « un signal dont
le signe change par régime n'est pas un edge » — lecture défendable, mais elle suppose que la
mesure est correcte. Si la mesure mélange deux choses, l'inversion peut être un artefact de
composition et non une instabilité du mécanisme.

## Reclassement

| | avant | après |
|---|---|---|
| Nature du kill | mécanique implicite (« brut ≈ 0 ») | **PARTIEL** — un axe plausible non varié |
| Statut | archivé | **rouvrable une fois**, angle écrit ci-dessous |

## Angle de ré-ouverture — pré-enregistré ici, AVANT toute donnée

**Hypothèse.** Le brut nul mesuré est une **annulation entre deux composantes de signe opposé**,
pas une absence de mécanisme.

**Test.** Remplacer `d2y_bps` par les séries de chocs **publiées et gratuites** (USMPD, Fed de San
Francisco, à jour 2026 ; séries Jarociński-Karadi, CC-BY-4.0), et estimer le drift **séparément sur
la composante politique monétaire et sur la composante information**, sur le même ledger de
182 événements, aux mêmes horizons, avec le même seuil et le même modèle de coût. **Rien d'autre
ne bouge.**

**Ce qui falsifie et clôt définitivement.** Si les deux composantes sont individuellement
indistinguables de zéro, le kill devient **mécanique** et la famille se ferme pour de bon — plus
aucune ré-ouverture sans un mécanisme entièrement nouveau.

**Ce qui valide.** Deux composantes non nulles, de signe opposé, **et** stables en signe à travers
les trois sous-périodes (avant 2015 / 2015-2021 / 2022+). La stabilité par sous-période est
exigée : c'est elle qui distingue une décomposition réelle d'un sur-ajustement à deux paramètres.

**Coût.** **2 essais** (une composante chacune), pas une grille. À ajouter au compteur du
programme, pas au global.

**Ce que je ne teste pas** : ni nouvel instrument, ni nouvel horizon, ni nouveau seuil, ni autres
banques centrales. Un seul axe change. C'est la condition pour que le résultat soit interprétable.
