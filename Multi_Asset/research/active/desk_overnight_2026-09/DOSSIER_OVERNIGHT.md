# Dossier overnight — US100 / GER40 : le lundi mérite-t-il d'être tradé ?

*2026-09 · lecture seule sur le VPS · worktree interne `.worktrees/desk-overnight`, branche
`claude/desk-overnight`, non poussée. Périmètre : la jambe overnight (US100 22:05→15:30 Paris,
GER40 17:35→09:00 Paris, lundi+mardi, poids 0.35, compte funded <ACCOUNT_ID>). L'ORB est traité par
un autre chantier — non dupliqué ici.*

*Code : `code/build_overnight.py` (reconstruction M1 indépendante) → `code/stats_lib.py` (HAC,
bloc-bootstrap, rupture endogène) → `code/analysis.py` (toutes les sections numérotées ci-dessous).
Sorties brutes : `results/*.csv`, `results/analysis_results.json`, `results/analysis_final_run.txt`,
`results/partC_proxy.txt`. Interpréteur `/usr/bin/python3`.*

---

## Verdict d'ouverture

**GARDER lundi ET mardi.** Ce n'est PAS parce que lundi passe un seuil de significativité rigoureux
— **il n'en passe aucun**, ni local ni cumulé, pris isolément (t_HAC6 = 2,27–2,29 sur toute la
période, contre un seuil Šidák local à 3,10 et cumulé à 4,21). C'est parce que :

1. **Le test qui correspond à ce qui est réellement déployé — lundi+mardi POOLÉS comme UNE seule
   hypothèse — est nettement plus robuste** : brut, US100 passe le seuil cumulé le plus dur
   (t=4,65 > 4,21) et GER40 en est à un cheveu (t=4,18) ; net des coûts réels mesurés (spread+swap,
   asymétrique), les deux repassent sous le seuil cumulé (t=2,92 / 2,73) mais restent économiquement
   positifs (~+5 bps/nuit net) et p_bootstrap < 0,02.
2. **Aucune rupture temporelle de lundi (ni de mardi) ne survit à une correction honnête de la
   recherche de date** : en laissant le point de rupture totalement libre (non imposé) et en
   testant sa significativité par bootstrap de blocs sur le MÊME scan, p = 0,43 à 0,61 dans les
   quatre cellules. Le récit « lundi s'est effondré depuis 2022 » repose sur un découpage choisi
   après coup — je ne peux pas le distinguer statistiquement du bruit.
3. **Couper lundi DÉGRADE le ratio risque/rendement du sleeve au lieu de l'améliorer** : lundi et
   mardi sont quasi non corrélés (r = −0,08 à −0,15, même semaine) donc les combiner diversifie
   presque idéalement — Sharpe annualisé du pool (0,73 US100 / 0,75 GER40) domine strictement
   « mardi seul » (0,54 / 0,46).
4. **L'historique opérationnel incrimine un bug, pas lundi** : les deux pertes qui ont
   spécifiquement touché des nuits de lundi (compte <ACCOUNT_ID>, juillet 2026) venaient d'un bug
   logiciel (GER40 sauté les lundis, `monday_restamp`), pas d'un edge intrinsèquement mauvais —
   corriger le bug a réglé le problème, sans toucher au calendrier lundi/mardi.

Chiffre à retenir : **couper lundi retirerait ~51 % de la contribution économique nette du sleeve
(reconstruction 2013–2026) pour ne retirer que 50 % des nuits d'exposition** — ce n'est pas un
déjeuner gratuit, et la case « alternative moins chère » (Partie D) n'est pas « mardi seul », c'est
« déleviérer les deux nuits ».

---

## A. Le lundi est-il mort ?

### A.1 Méthode — reconstruction indépendante, piège d'étiquetage vérifié

Source : M1 OHLC vrai-UTC (`data/deep_history_utc/{US100,GER40}_M1.csv`, caché en parquet),
2013-01 → 2026-06-05. Séances cash retenues, ancrées **en heure d'échange AVEC DST** :
- **US100** : 09:30–16:00 America/New_York (NASDAQ-100 cash)
- **GER40** : 09:00–17:30 Europe/Berlin (Xetra)

Ce sont exactement les horaires natifs qui correspondent au sleeve déployé (`build_series.py` du
chantier `funded_1y_mono_2026-08` : US100 entre à 22:05 Paris — 5 min après la clôture cash — et
sort à 15:30 Paris — l'ouverture cash — le lendemain ; GER40 entre à 17:35 Paris — 5 min après
Xetra — et sort à 09:00 Paris).

**Nuit étiquetée par le jour d'ENTRÉE** (le jour de la clôture tenue), pas le jour d'ouverture —
c'était le piège signalé par le coordinateur. Vérification explicite (Section 2 du script) : les
nuits d'entrée **vendredi** ont un écart calendaire médian de 3 jours vers la ligne suivante (le
week-end), confirmant que le gap de week-end est bien porté par la ligne « vendredi », pas
« lundi ». L'étiquetage par jour d'entrée est confirmé correct.

### A.2 Mesure brute, HAC lag-6, plein échantillon (recalculée indépendamment)

| US100 (2013-01→2026-06, N=3299) | mean bps | t_HAC6 | n |
|---|---:|---:|---:|
| **lundi** | 8,320 | 2,271 | 621 |
| **mardi** | 8,637 | 2,905 | 685 |
| mercredi | 1,233 | 0,331 | 676 |
| jeudi | 0,513 | 0,195 | 664 |
| vendredi | 1,943 | 0,588 | 653 |

| GER40 (2013-10→2026-06, N=3231) | mean bps | t_HAC6 | n |
|---|---:|---:|---:|
| **lundi** | 8,140 | 2,291 | 639 |
| **mardi** | 6,749 | 2,657 | 657 |
| mercredi | −0,322 | −0,111 | 648 |
| jeudi | 2,348 | 0,999 | 648 |
| vendredi | 1,966 | 0,511 | 639 |

Cross-validation contre le tableau du coordinateur (même forme, source/fenêtre/session légèrement
différentes) : US100 lundi 8,32/t2,27 ici vs 6,65/t1,98 (coordinateur) ; mardi 8,64/t2,91 vs
9,77/t3,13 ; GER40 lundi 8,14/t2,29 vs 7,70/t2,17 ; mardi 6,75/t2,66 vs 6,45/t2,42. Même signe,
même ordre de grandeur, même hiérarchie (mardi > lundi ≫ mercredi/jeudi/vendredi) sur les deux
reconstructions indépendantes — le pattern qualitatif est confirmé, pas un artefact de pipeline.

### A.3 Multiple testing — Šidák au n cumulé

26 tests comptés cette session (5 jours × 2 instruments = 10 en A.2, 4 bloc-bootstrap Lun/Mar en
A.4, 4 ruptures endogènes en A.5, 4 net-de-coût en A.6, 4 tests joints en A.7). **Šidák local
(n=26) : |t| > 3,10. Šidák CUMULÉ (n=1994+26=2020, ledger canonique) : |t| > 4,21.**

**Aucune des 4 cellules lundi/mardi individuelles (US100/GER40) ne passe le seuil local, a
fortiori le cumulé.** Le tableau du coordinateur utilisait un Šidák à 20 cellules (seuil 3,02,
que je retrouve à 3,016 avec `sidak_threshold(20)`) — c'est le bon calcul LOCAL à sa propre grille,
mais **la règle du projet est le n cumulé**, pas le n local (`CLAUDE.md` : « Δn_tests > 0 : compte
tes tests, seuil Šidák au n cumulé »). Au n cumulé, même la cellule la plus forte du coordinateur
(US100 mardi, t=3,13) échoue.

### A.4 Placebo apparié — bloc-bootstrap (H0 : moyenne nulle), lundi et mardi seuls

Bootstrap de blocs (Politis-Romano, blocs de 20 obs, 4000 réplicats, série recentrée à 0) — pas
d'i.i.d. :

| | mean bps | t_HAC6 | n | p_bloc_bootstrap |
|---|---:|---:|---:|---:|
| US100 lundi | 8,320 | 2,271 | 621 | 0,0450 |
| US100 mardi | 8,637 | 2,905 | 685 | 0,0088 |
| GER40 lundi | 8,140 | 2,291 | 639 | 0,0573 |
| GER40 mardi | 6,749 | 2,657 | 657 | 0,0132 |

À 5 % non corrigé, 3 des 4 cellules passeraient (GER40 lundi à la marge, p=0,057). **Mais aucune
ne passerait un seuil corrigé au n cumulé** (qui exigerait p ≈ 2,5×10⁻⁵ pour un t équivalent à
4,21). Le bloc-bootstrap confirme le HAC analytique — la significativité individuelle par jour
tient à un niveau non corrigé, pas au niveau qui compte pour ce projet.

### A.5 Rupture ENDOGÈNE — date estimée, non imposée, corrigée par bootstrap de blocs

⚠️ Le découpage 2018-21/2022-26 du coordinateur a été choisi **après avoir vu la forme des
données** — exactement le piège qu'il signale lui-même. Test correct : scanner TOUS les points de
rupture candidats (tous les 10 obs, marge 90 obs de chaque côté), prendre le |t_diff| MAXIMUM
(pré vs post, HAC sur chaque segment), puis bootstrap de blocs (blocs de 15, 300 réplicats,
**même scan refait sur chaque réplicat**) pour obtenir un p qui corrige nativement la recherche
sur de multiples candidats :

| | rupture estimée | n pré/post | mean pré | mean post | t_diff | p (recherche corrigée) |
|---|---|---:|---:|---:|---:|---:|
| US100 lundi | 2023-03-20 | 470/151 | 11,44 | −1,39 | −1,93 | **0,433** |
| US100 mardi | 2024-05-28 | 580/105 | 6,67 | 19,49 | +1,66 | **0,613** |
| GER40 lundi | 2022-02-07 | 420/219 | 12,34 | 0,09 | −1,83 | **0,460** |
| GER40 mardi | 2024-03-12 | 540/117 | 4,01 | 19,38 | +1,73 | **0,500** |

**Aucune des quatre ruptures n'est significative.** Même en laissant la machine choisir librement
la MEILLEURE date de rupture possible pour maximiser l'écart apparent, le résultat n'est pas
distinguable du bruit une fois la recherche corrigée. Point remarquable : le sens de la « rupture »
n'est même pas cohérent — lundi apparaît décliner (11,4→−1,4 et 12,3→0,1 bps) alors que mardi
apparaît AUGMENTER sur la même fenêtre récente (6,7→19,5 et 4,0→19,4 bps). C'est la signature
d'un ré-échantillonnage bruité d'un même processus poolé, pas de deux régimes distincts et
opposés. **Le tableau 2018-21/2022-26 du coordinateur — comme le mien s'il avait été présenté de
la même façon — est une lecture post-hoc d'un point qui n'est pas statistiquement identifiable.**

Ceci classe la question dans la catégorie **PUISSANCE** de la politique de réouverture
(`CLAUDE.md`) : sous-échantillon court (105-219 obs post-rupture) ⇒ **UNDERPOWERED, PAS REJECTED**
— je ne peux ni confirmer ni exclure un vrai déclin de lundi ; je peux seulement dire qu'aucune
rupture n'est démontrée avec les données actuelles.

### A.6 Net de coût réel — spread ET swap, asymétrique (L30)

Coûts appliqués par nuit tenue (lundi/mardi = 1× le swap ; `triple_dow` US100/GER40 = 4 = vendredi,
non concerné) :
- **RT mesuré récent** (`funded_1y_mono_2026-08/attribution/build_series.py`, semaine 2026-08-17,
  natif) : US100 1,045 bps, GER40 1,017 bps — remplace le chiffre placeholder de juin (2,2 bps,
  `cost_anchors.rt_bps_legs_allin`, conservé en sensibilité ci-dessous.
- **Swap LONG mesuré** (`spec_v22.yaml::measured_specs`, points MT5 datés 2026-06-10) : US100
  −2,1257 bps/nuit, GER40 −1,564 bps/nuit. Asymétrie L30 confirmée (short US100 serait +0,0917,
  short GER40 −0,1933 — mais le sleeve est LONG-only, l'asymétrie n'est pertinente que si on
  envisageait un jour l'autre côté, ce qui n'est pas le cas ici).

| | gross (t) | net coût récent (t) | net coût spec juin, conservateur (t) |
|---|---:|---:|---:|
| US100 lundi | 8,32 (2,27) | **5,15 (1,41)** | 3,99 (1,09) |
| US100 mardi | 8,64 (2,91) | **5,47 (1,84)** | 4,31 (1,45) |
| GER40 lundi | 8,14 (2,29) | **5,56 (1,56)** | 4,38 (1,23) |
| GER40 mardi | 6,75 (2,66) | **4,17 (1,64)** | 2,99 (1,17) |

Le coût mange 1 à 2 points de t mais **ne renverse le signe d'aucune cellule** — même au coût
conservateur de juin, l'espérance nette reste positive sur les quatre cellules. Le sleeve n'est
donc pas dans la zone L33 (bascule de signe au coût).

### A.7 Test JOINT lundi+mardi — ce qui est réellement déployé

C'est le test qui correspond le mieux à la spec live (`overnight_midweek`, une seule hypothèse
« lundi ou mardi » plutôt que deux hypothèses séparées) :

| | GROSS mean (t) | GROSS p_boot | NET mean (t) | NET p_boot |
|---|---:|---:|---:|---:|
| US100 (n=1306) | 8,49 (**4,65**) | 0,0000 | 5,32 (2,92) | 0,0088 |
| GER40 (n=1296) | 7,44 (**4,18**) | 0,0005 | 4,85 (2,73) | 0,0155 |

**US100 brut clear le seuil cumulé le plus dur (4,65 > 4,21). GER40 brut est juste en-dessous
(4,18 vs 4,21) — à un niveau de test qui n'a jamais reçu de correction de ce calibre avant
aujourd'hui, c'est remarquablement proche.** Net des coûts réels, les deux repassent sous 4,21
mais restent économiquement positifs (~+5 bps/nuit) avec p_bootstrap < 0,02 (non corrigé).

**Conclusion Partie A** : le lundi n'est pas « mort » au sens où on pourrait démontrer une
rupture — cette rupture n'est PAS démontrable, dans un sens ou dans l'autre (sous-puissance). Le
sleeve dans son ensemble (lundi+mardi poolés, ce qui est déployé) a un edge gross qui clear la
barre la plus dure du projet pour US100 et s'en approche pour GER40 ; net des coûts réels il
retombe sous cette barre mais reste économiquement positif. **Isoler lundi seul et le juger sur
son propre t-stat est statistiquement le mauvais test** — il n'a jamais eu la puissance nécessaire
pour trancher seul.

---

## B. Le choix « lundi + mardi » était-il motivé ou fortuit ?

**Sélection post-hoc, documentée et jamais résolue. Archéologie complète :**

1. **`PropFirms/ftmo/program_2026-06/ftmo_universe/OVERNIGHT_VERIFICATION_REPORT.md`** (daté
   2026-06-03 dans le corps du texte) est le document où la concentration midweek est DÉCOUVERTE.
   Il l'admet explicitement lui-même (§4.6, verbatim) :
   > « Le mapping jour/nuit ... 6. Multiple-testing — le chiffre robuste est TOUTES nuits (+4,90,
   > t=4,04), non cherry-pické. **La concentration midweek est un post-hoc**, mais **cross-confirmé
   > NQ+GER40+US100** (3 marchés, même jour) → crédible, pas une cellule isolée. Traite +4,9 comme
   > la borne dure, midweek comme l'amélioration. »
   C'est une reconnaissance honnête de l'équipe — mais c'est bien un aveu de sélection après coup,
   pas une pré-registration.

2. **`FTMO_LOG_overnight_candidate.md`** (même date, 2026-06-03) traite la thèse « equity overnight
   premium » en version TOUTES-NUITS, sans mention de lundi/mardi spécifiquement — confirme qu'à
   cette date, la version canonique de l'edge était encore « toutes les nuits », pas « midweek ».

3. **`FTMO_CANONICAL_STATE.md`** (§v2.1, post 2026-06-03) documente le passage à la sélection
   midweek et son coût statistique, verbatim :
   > « (5) Overnight : le mur porteur (+12,1 pts d'ablation) MAIS **DSR 0,29 FAIL sur la grille de
   > sélection 40 cellules (équipe)** → statut : sleeve CONSERVÉE (contribution funnel massive,
   > mécanisme documenté, cross-confirmée 3 marchés par l'archive) avec **caveat de sélection
   > ouvert** ; **sensibilité all-nights-vs-midweek à trancher avant signature**. »
   DSR 0,29 est très en-dessous du seuil L20 (≥1,0–1,1) — la sélection midweek, évaluée sur sa
   propre grille de recherche (40 cellules, vraisemblablement jour × instrument × fenêtre), échoue
   formellement le test de déflation.

4. **`data/ftmo_portfolio/v22/spec_v22.yaml`** (spec_date 2026-06-10, **7 jours après** la
   découverte) fige `nights_held: lundi + mardi` dans la config `challenge.sleeves.overnight_midweek`
   ET dans la config `funded` déployée — **sans que le caveat DSR 0,29 ait été résolu**.

5. **Le caveat n'a JAMAIS été refermé** — il est re-cité identique, mot pour mot, dans au moins
   quatre documents postérieurs : `data/ftmo_portfolio/PORTFOLIOS.md` (« sensibilité
   all-nights-vs-midweek à trancher avant signature »), `data/ftmo_portfolio/CANONICAL_AMENDMENT_PENDING.md`,
   `data/ftmo_portfolio/attribution_timing/ATTRIBUTION_TIMING.md` (« Caveat maintenu : la preuve
   STANDALONE du sleeve reste faible (DSR 0,29 vs sa grille de sélection, audit) ; ce verdict est
   in-container, pas une validation du signal en soi »), `data/ftmo_portfolio/v222_vm_sweep/
   PREREGISTRATION.md` et `STUDY_VM_SWEEP_2026-06-17.md`. Cinq citations du même chiffre sur
   plus de deux mois, jamais suivies d'une résolution formelle.

6. **Aucune pré-registration antérieure au 2026-06-03 n'existe.** Recherche exhaustive des
   fichiers `PREREG*`/`PRESPEC*` dans `PropFirms/ftmo/program_2026-06/` et `data/ftmo_portfolio/` :
   toutes les pré-registrations qui existent (nightly_us100, overnight_ftmo_improve, v222_vm_sweep,
   asia_23_8, soybean, gold_dosing, funded_anatomy) sont datées **juillet 2026 ou plus tard**,
   c'est-à-dire après que le choix midweek était déjà en production.

**Verdict Partie B : la sélection est FORTUITE au sens statistique (post-hoc, DSR-fail sur sa
propre grille), MOTIVÉE au sens du mécanisme (cross-confirmée sur 3 marchés indépendants dans le
document fondateur, ce qui est un vrai garde-fou contre le pur bruit).** L'équipe l'a documenté
honnêtement sur le moment (rare), mais la clause de résolution avant signature n'a jamais été
honorée. Ma propre ré-analyse (Partie A, §A.7) est la première tentative de trancher réellement
ce caveat de deux mois — et le verdict qu'elle rend (edge gross robuste au niveau poolé, net
positif mais sous le seuil le plus dur) est plus proche de « survit à un audit sérieux » que de
« artefact pur », sans être un PASS sans réserve.

**Point additionnel, hors du périmètre strict de la question mais pertinent pour la
recommandation** : `data/ftmo_portfolio/nightly_us100_2026-07/{PREREG,VERDICT}.md` (compte
<ACCOUNT_ID>, un compte antérieur, pas <ACCOUNT_ID>) documente les deux seules pertes historiques
spécifiquement associées à des nuits de lundi (−$354, −$402, toutes deux flattées par le
breaker M5). Le diagnostic tranché par l'équipe (Hb2, confirmé) : ce n'était PAS un edge lundi
défectueux, mais un **bug logiciel** — GER40 sautait les lundis (flag stale), rendant le book
mono-sleeve US100 non-diversifié précisément ces nuits-là et donc sur-sizé par le mécanisme de
cap de marge. Le fix (`monday_restamp`, déployé 2026-07-14) a restauré la jambe GER40 les lundis
et « adresse » le problème selon le VERDICT.md de ce chantier. **Les seules pertes empiriques
attribuables à « lundi » dans l'historique récent ont une cause opérationnelle identifiée et
corrigée, pas une cause de marché.**

---

## C. Le mécanisme NY Fed transpose-t-il ?

**Limite honnête posée d'emblée** : le cache M1 local (`US100_M1.parquet`, `GER40_M1.parquet`) ne
contient QUE OHLC, **pas de volume**. Je ne peux donc pas construire un vrai proxy de déséquilibre
d'ordres (order imbalance) comme Boyarchenko-Larsen-Whelan — je construis à la place deux proxies
de **dispersion de prix** dans la dernière demi-heure de séance, en étant clair que ce n'est PAS la
même chose :
- `range30_bps` = (high−low) sur les 30 dernières minutes avant clôture, en bps du close
- `twap_dev_bps` = écart entre le prix de clôture et le TWAP (proxy de VWAP sans volume) de ces
  30 dernières minutes

### C.1 Le proxy prédit-il la moyenne, ou seulement la variance ?

| | corr(proxy, overnight SIGNÉ) | corr(proxy, |overnight|) |
|---|---:|---:|
| US100 (n=1306) | **+0,215** | **+0,511** |
| GER40 (n=1296) | **+0,201** | **+0,455** |

Le proxy est **2 à 2,5× plus corrélé à l'AMPLEUR** du rendement overnight qu'à son **signe/niveau**.
C'est la signature L54 : la dispersion de clôture prédit surtout la VARIANCE de la nuit qui suit,
pas sa direction. Ça n'exclut pas une contribution positive au niveau (r=0,20 n'est pas nul), mais
ça veut dire que le mécanisme, s'il existe, n'explique qu'une fraction modeste de la moyenne — la
majorité de l'effet observé en Partie A n'est pas expliquée par cette dispersion de clôture.

### C.2 Le proxy a-t-il décliné depuis 2021 (comme le prétend la littérature) ?

| | pente range30_bps / an | pente \|twap_dev_bps\| / an |
|---|---:|---:|
| US100 | **+0,981** (AUGMENTE) | +0,087 |
| GER40 | −0,229 (léger déclin) | −0,043 |

**US100 va dans le sens INVERSE de la thèse** : la dispersion de clôture a AUGMENTÉ sur
l'échantillon (portée par les pics 2020/2022), pas décliné. GER40 montre un très léger déclin,
d'une ampleur négligeable face au bruit année-à-année (écart-type inter-annuel ≫ pente). **Le
canal « dispersion en baisse depuis 2021 » de Boyarchenko-Larsen-Whelan (marché futures actions
US, échantillon différent) ne se retrouve pas clairement dans mon proxy sur CFD US100/GER40** —
et de toute façon, la Partie A.5 n'a trouvé aucune rupture significative à expliquer en premier
lieu. Je ne peux pas dire que le mécanisme transpose ; je peux dire que mon proxy ne le confirme
pas, avec la réserve qu'un vrai proxy d'imbalance (avec volume/carnet) pourrait donner un résultat
différent — donnée non disponible ici.

### C.3 GER40 suit-il le même canal, ou un flux distinct ?

**Je ne fabrique pas de corrélation entre proxies de clôture des deux instruments** : les fenêtres
de clôture ne sont PAS simultanées (Xetra clôture 17:30 Paris/Berlin ; US100 clôture ~22:00 Paris)
— comparer les dispersions de clôture « même date calendaire » comparerait deux moments sans lien
de flux direct, ce qui fabriquerait une conclusion sans fondement.

Ce qui EST honnêtement testable : la corrélation des rendements overnight EUX-MÊMES (même date
d'entrée, lundi+mardi) :

**corr(US100_overnight, GER40_overnight) = +0,486 (n=1224)**

Une corrélation modérée, ni nulle ni proche de 1 : **les deux jambes partagent une composante
commune substantielle** (vraisemblablement un facteur risk-on/risk-off actions global qui se
propage sur la nuit US → matin européen), **mais ne sont pas un seul et même pari déguisé** — il
reste une fraction significative de variance idiosyncratique par marché. Ni « canal commun »
au sens strict, ni « flux transatlantique totalement distinct » : un entre-deux, cohérent avec deux
marchés actions liés par le beta global mais avec des refresh sessions différents.

---

## D. La décision, chiffrée

Trois options, mêmes coûts nets mesurés (§A.6), volatilité annualisée en **√(obs/an)** (L47 : 1
nuit/semaine = √52, 2 nuits/semaine = √104) :

| Option | Sharpe_ann US100 | Sharpe_ann GER40 | $ net capturé (vs pool=100%) | nuits d'exposition/sem |
|---|---:|---:|---:|---:|
| **1. Garder lundi+mardi (statu quo)** | **0,732** | **0,748** | 100 % | 2 |
| 2. Réduire à mardi seul | 0,543 | 0,461 | US100 54%/GER40 44% | 1 |
| 3. Déleviérer (Mon+Tue à poids moitié) | **0,732** (identique) | **0,748** (identique) | 50 % | 2 |

**Option 2 est DOMINÉE, pas seulement moins rentable.** Couper lundi ne réduit pas non plus
la queue de risque comme on pourrait l'espérer : la pire nuit historique de **mardi** (US100,
net) est **−486,84 bps**, contre **−298,53 bps** pour la pire nuit de lundi — mardi porte la queue
la plus grasse dans cet échantillon, pas lundi. Couper lundi pour « sécuriser » le book est donc un
choix qui, empiriquement, retire la nuit la MOINS risquée du duo tout en gardant celle qui a produit
la pire perte isolée.

**Pourquoi le pool bat mardi-seul (le calcul L54)** : lundi et mardi sont quasi-indépendants
(corr = −0,084 US100 / −0,149 GER40, même semaine). Combiner deux paris de Sharpe comparable et
peu corrélés augmente le Sharpe agrégé d'un facteur proche de √2 (0,543→0,732 = ×1,35 ; 0,461→0,748
= ×1,62) — c'est un gain de diversification pur, pas un artefact de sizing.

**Si l'objectif est de réduire le risque du sleeve (barrière FTMO, DD)**, l'option qui domine
n'est PAS « couper une nuit » mais **déleviérer les deux nuits à poids égal réduit** (option 3,
L54) : Sharpe et durée d'exposition inchangés, DD et $ à risque réduits proportionnellement au
poids. Couper un jour à espérance équivalente sacrifie de la diversification pour rien ; réduire
le poids ne sacrifie rien.

**Effet sur le nombre de jours d'exposition** — c'est le seul point réel en faveur de l'option 2 :
couper lundi réduit de moitié le nombre de nuits où un gap peut toucher la barrière quotidienne
FTMO (moins d'occasions de tail-risk, indépendamment de la taille). Mais empiriquement (ce
paragraphe), la pire nuit du duo est mardi, pas lundi — donc ce bénéfice de réduction du nombre
d'occasions ne cible pas la bonne nuit si l'objectif est spécifiquement de retirer la queue la plus
grasse. Un vrai calcul de p(pass)/durée (dans l'esprit `Portfolio/admission/barrier.py`) serait
nécessaire pour chiffrer ce trade-off proprement à la barrière FTMO réelle — hors du périmètre
overnight strict de ce dossier, signalé comme piste pour le chantier portefeuille.

### Recommandation finale

**GARDER lundi et mardi, plein poids, statu quo.** Si une réduction du risque du sleeve overnight
est requise pour d'autres raisons (budget de risque du book, DD funded), **préférer réduire
`ON_W` (déleviérer) plutôt que couper un jour du calendrier** — cela préserve le Sharpe et la
diversification que couper un jour détruit. Le caveat DSR 0,29 hérité de juin doit être considéré
comme **partiellement résolu par ce dossier** (le test joint gross clear/quasi-clear la barre la
plus dure du projet, aucune rupture n'est démontrable) mais **pas entièrement** (net des coûts
réels, le test joint retombe sous le seuil cumulé) — le statut honnête est **« garder, preuve
insuffisante pour couper »**, pas « validé sans réserve ».

---

## Annexe — comptage des tests et fichiers

- **26 tests** comptés cette session (détail : 10 en A.2, 4+4 en A.4/A.5, 4 en A.6, 4 en A.7).
  Šidák local (n=26) = 3,095. Šidák cumulé (n=1994+26=2020) = 4,211.
- Les proxys de la Partie C (corrélations descriptives, pas des tests de significativité au sens
  du gate IC) ne sont pas comptés dans les 26 — ce sont des diagnostics, pas des hypothèses
  pré-enregistrées à gate.
- Fichiers : `code/build_overnight.py`, `code/stats_lib.py`, `code/analysis.py`,
  `results/us100_overnight_daily.csv`, `results/ger40_overnight_daily.csv`,
  `results/analysis_results.json`, `results/analysis_final_run.txt`, `results/partC_proxy.txt`.
- Sources externes citées : `Multi_Asset/research/active/funded_1y_mono_2026-08/attribution/
  build_series.py` (RT récent, méthode de reconstruction du sleeve) ; `data/ftmo_portfolio/v22/
  spec_v22.yaml` (swap mesuré, config funded, historique de la sélection midweek) ;
  `PropFirms/ftmo/program_2026-06/ftmo_universe/{OVERNIGHT_VERIFICATION_REPORT,
  FTMO_CANONICAL_STATE,FTMO_LOG_overnight_candidate}.md` ; `data/ftmo_portfolio/{PORTFOLIOS,
  CANONICAL_AMENDMENT_PENDING}.md` ; `data/ftmo_portfolio/attribution_timing/ATTRIBUTION_TIMING.md` ;
  `data/ftmo_portfolio/v222_vm_sweep/{PREREGISTRATION,STUDY_VM_SWEEP_2026-06-17}.md` ;
  `data/ftmo_portfolio/nightly_us100_2026-07/{PREREG,VERDICT}.md`.
