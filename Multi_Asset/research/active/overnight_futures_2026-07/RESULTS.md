# RESULTS — Overnight-drift block on CME futures (compte personnel €13 k IBKR)

**Date : 2026-07-30.** Pré-registration figée dans `PREREGISTRATION.md` **avant** toute mesure.
Interpréteur `/usr/bin/python3`. Aucun commit, aucun SSH, écritures confinées à ce répertoire.

---

## 0. Verdict en un paragraphe

**Un seul des quatre sleeves survit au passage CFD → futures, et pour une raison qui n'a rien à voir
avec celle qu'annonçait l'inventaire.** Le mécanisme revendiqué — « demande physique asiatique » — est
**falsifié** : le drift n'est pas ancré sur l'horloge UTC de Tokyo/Shanghai, il est ancré sur
**l'horloge d'échange CME**, entièrement concentré dans la **première heure après la réouverture
Globex de 18:00 ET**. La fenêtre héritée « 23:00–07:00 UTC » est donc **alignée en hiver et décalée
d'une heure en été** — la moitié de l'échantillon était mesurée à côté de l'edge. Corriger l'horloge
améliore l'or ; mais la même correction expose que **59 % de l'edge argent et 35 % de l'edge WTI sont
le *gap* de la pause de settlement**, non tradable (marché fermé). Sur le contrat réel, l'argent ne
restitue que **18 %** du drift mesuré sur CFD (t = −3.91 sur l'écart). Le WTI meurt sur le coût
micro-futures. Le soja n'a **jamais été mesuré sur la bonne heure** : le CFD ne cote pas la
réouverture CBOT. **Il n'existe aucun panier défendable** (or↔argent 0.69–0.76, et l'argent est mort).
Reste **l'or sur MGC : PASS conditionnel**, avec un caveat lourd — à €13 k le vol-targeting devient
inopérant (1 lot ou rien), ce qui coûte 0.35 de Sharpe, retourne le skew de **+0.99 à −0.49** et
crée une queue à **−18.4 % de compte en une séance**.

---

## 1. Étape 0 — L53, matrice de véhicule (avant tout backtest)

Compte : €13 000 × 1.1522 = **$14 980 → $15 000**. Marges : table live rafraîchie 2026-07-30 11:42 UTC
(source déclarée TradeStation/IBKR) ; MZS depuis les specs CME micro-ag. Prix de référence :
`data/raw/yf_*_1d_*.parquet`, close 2026-07-08.

| Contrat | Taille | Notionnel | Marge | % compte | **Notionnel/compte** | Tick (bps) | Comm. RT (bps) | **RT base** | RT stress 2 ticks | Break-even publié | Verdict étape 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **MGC** or | 10 oz | $40 709 | $2 308 | 15.4 % | **2.71×** | 0.246 | 0.418 | **0.66** | 0.91 | — | **SURVIT** |
| **SIL** argent | 1 000 oz | $58 164 | $6 469 | **43.1 %** | **3.88×** | 0.860 | 0.292 | 1.15 | 2.01 | 5.3 | **REJECTED** (M1 + M2) |
| **MCL** WTI | 100 bbl | $7 352 | $840 | 5.6 % | 0.49× | 1.360 | **2.312** | **3.67** | 5.03 | **3.5** | **REJECTED** (K4) |
| **MZS** soja | 500 bu | $5 975 | $210 | 1.4 % | 0.40× | 1.046 | **2.845** | **3.89** | 4.94 | ~2.0 | REJECTED (K4) — *voir §6* |
| *PL platine (réf.)* | *50 oz* | *$78 820* | *~$7 094* | *47 %* | *5.25×* | — | — | — | — | — | *matériellement mort* |

**Le résultat contre-intuitif de cette table : sur un petit compte, les micro-futures sont CHERS en
bps.** La commission fixe (~$1.70 aller-retour) rapportée à un notionnel de $6–7 k pèse **2.3–2.8 bps
à elle seule** — plus que le budget de coût total du soja (2 bps) et l'essentiel de celui du WTI
(3.5 bps). La recommandation des rapports archivés (« passer aux futures, ~1.5 bps RT, la route la
plus propre ») est **fausse pour MCL et MZS à cette taille** : elle n'est vraie que pour MGC (0.66 bps),
dont le notionnel de $40 k dilue les frais fixes.

> **Divergence signalée (comme exigé par la pré-registration §4).** Le tableau de coûts calculé à la
> main dans `PREREGISTRATION.md` porte une erreur de décimale sur la commission de MCL et MZS
> (0.231 / 0.285 bps au lieu de 2.312 / 2.845). Les chiffres corrects sont ceux ci-dessus, produits
> par `code/step0_vehicle.py`. La conclusion est **inchangée en direction** (MCL et MZS restaient
> au-dessus de leur break-even), mais l'ampleur du dépassement est bien plus grande qu'annoncé.

---

## 2. Étape 1 — LE MAPPING DE SESSION (le test décisif)

### 2.1 La géométrie

| | Réouverture Globex | UTC **hiver** | UTC **été** | Pause settlement |
|---|---|---|---|---|
| GC/MGC, SI/SIL, CL/MCL | 17:00 CT = **18:00 ET** | 23:00 | 22:00 | 17:00–18:00 ET |
| ZS/MZS (CBOT ag) | 19:00 CT = **20:00 ET** | 01:00 | 00:00 | 14:20–20:00 ET |

La fenêtre héritée (23:00 UTC métaux, 01:00 UTC soja) tombe **pile sur la réouverture en hiver et
une heure trop tard en été**, pour les quatre sleeves simultanément.

### 2.2 Contraste DST — Spec A (UTC) vs Spec B (horloge d'échange)

`results/step1_session_map.csv`. En hiver A ≡ B par construction ; le contraste n'est identifié
qu'en **été**, ce qui le rend **immunisé au confondant saisonnier** (les deux specs y voient les
mêmes mois).

| Sleeve | A hiver SR | A été SR | **B été SR** | ΔSR été (bootstrap blocs) | p |
|---|---|---|---|---|---|
| GOLD | 1.624 (t 7.55) | **0.517** (t 2.33) | **1.234** (t 5.64) | **+0.057**/obs | **0.002** |
| SILVER | 1.262 (t 5.14) | **0.345** (t 1.19) | **1.452** (t 5.01) | +0.087/obs | **0.000** |
| WTI | 0.787 (t 2.43) | 0.012 (t 0.04) | 0.236 (t 1.17) | +0.019/obs | 0.324 |
| SOYBEAN | 2.831 (N=126) | 1.111 | 1.470 (**N=175**) | +0.122/obs | 0.061 |

*(Bootstrap stationnaire Politis–Romano apparié, bloc moyen 10 j, 5 000 tirages. ΔSR est en unités de
Sharpe **par observation** ; ×√250 pour l'annualisé.)*

Sous la spec héritée, **l'été fait un tiers du Sharpe de l'hiver**. Corriger l'horloge le restaure.

### 2.3 Le profil horaire tranche entre les deux mécanismes (L44)

Rendement horaire moyen indexé sur l'**heure d'échange (ET)**, hiver vs été (`step1b`) :

| Sleeve | ET 16 (avant pause) | **ET 18 (1ʳᵉ heure après réouverture)** | ET 19 | ET 20 | toutes autres |
|---|---|---|---|---|---|
| GOLD | +0.07 / −0.85 | **+4.79 / +3.31** | +0.72 / +1.12 | +1.95 / −0.39 | \|·\| ≤ 2.4 |
| SILVER | −6.29 / −7.66 | **+11.96 / +7.64** | +1.29 / +4.15 | +2.20 / −0.43 | \|·\| ≤ 3.1 |
| WTI | −1.07 / +0.42 | **+7.36 / +1.89** | +0.80 / +0.67 | +0.62 / −0.81 | — |

**Corrélation du profil hiver vs profil été, par horloge** — la bonne ancre est celle qui superpose :

| | horloge **UTC** | horloge **échange (ET)** |
|---|---|---|
| GOLD | 0.036 | **0.701** |
| SILVER | 0.203 | **0.863** |
| WTI | −0.080 | 0.269 |
| SOYBEAN | 0.190 | −0.106 *(pas de données, §6)* |

**Verdict D1 : l'ancre est l'horloge d'échange. `H_asia` est FALSIFIÉ.** Le pic est à 18:00–19:00 ET,
soit **23:00 UTC en hiver et 22:00 UTC en été** — c.-à-d. **une à deux heures AVANT l'ouverture de
Tokyo** (09:00 JST = 00:00 UTC, sans heure d'été). Le drift suit la cloche du CME, pas celle de l'Asie.
Le récit « demande physique asiatique » des rapports archivés est le mauvais mécanisme ; le bon est
la **réouverture post-pause de settlement**.

*Expérience naturelle complémentaire (±4 semaines autour du basculement, `step1b_dst_transition.csv`) :
pour l'or, A chute 9.51 → 0.71 bps au switch de mars et remonte 7.62 → 11.71 au switch de novembre,
à saison constante — cohérent. Pour l'argent et le WTI le test est **sous-dimensionné et
non-concluant** (N≈250/cellule) ; je ne le compte pas comme confirmation. La preuve porteuse est le
profil horaire, qui utilise tout l'échantillon.*

### 2.4 Et la découverte qui change tout : le *gap* de pause

Le pic est la première heure après la réouverture. Or, quand l'heure de pause n'est pas cotée, la
mesure H1 close-to-close des études archivées **enjambe silencieusement la pause** et compte donc le
**gap de réouverture** — que personne ne peut trader (marché fermé). Décomposition sur M1
(`step1c_gap_decomposition.csv`), horloge d'échange :

| Sleeve | heure de pause cotée | **gap (bps)** | fenêtre **capturable** (bps) | fenêtre **gap inclus** (bps) | **part du gap** | t(capturable) | SR capturable |
|---|---|---|---|---|---|---|---|
| GOLD | 33 % | 0.95 | **4.59** | 5.43 | **17.5 %** | **7.13** | 1.667 |
| SILVER | **0 %** | **6.58** | 4.68 | 11.09 | **59.3 %** | 2.90 | 0.869 |
| SILVER été | 0 % | 7.71 | 2.33 | 9.95 | **77.5 %** | 1.31 | 0.380 |
| WTI | 16 % | 1.62 | 3.20 | 4.56 | **35.5 %** | 2.32 | 0.596 |

**L'or est le seul dont le marché OTC cote pendant la pause du CME** (33 %), donc le seul dont l'edge
mesuré est majoritairement réel. Pour l'argent, **six bps sur onze sont un gap** — et en été, plus des
trois quarts.

---

## 3. Étape 2 — Validation L52 sur barres futures réelles

`GC=F`, `SI=F`, `CL=F`, `ZS=F`, barres horaires Yahoo, 2024-03-07 → 2026-07-30, horodatage converti en
UTC explicite puis en heure d'échange par ma propre fonction DST.

### 3.1 Contrôle de calendrier — **PASS, exactement là où la théorie le met**

| Symbole | heures UTC quasi-vides, **hiver** | **été** | lecture |
|---|---|---|---|
| GC=F / SI=F / CL=F | **[22]** | **[21]** | = 17:00–18:00 ET → la pause d'1 h du CME ✓ |
| ZS=F | [0, 20, 21, 22, 23] | [19, 20, 21, 22, 23] | réouverture **01:00 UTC hiver / 00:00 UTC été** ✓ |

### 3.2 Deux pièges L52 rencontrés, et corrigés

1. **Étiquetage des barres.** Les barres horaires Yahoo sont **left-labelled** (vérifié : aucune barre
   estampillée 17:00 ET, la première de séance est estampillée 18:00 ET). Ma première passe a pris le
   **close** de la barre 18:00 comme prix d'entrée — c'est le prix à 19:00, ce qui **saute l'heure de
   réouverture, donc tout l'edge**. Le drift or mesuré passait de 4.68 à 2.30 bps. Corrigé : l'entrée
   est l'**open** de la barre estampillée 18:00.
2. **Roll du continu.** Les rendements sont mesurés **à l'intérieur d'une séance** (18:00 → 02:00 ET),
   jamais entre séances : le décalage de roll de `=F` ne peut donc pas contaminer la mesure.

### 3.3 Transfert réel — pommes contre pommes (`step2b_apples.csv`)

Futures vs CFD **sur les mêmes séances**, les deux gap-exclus, les deux sur l'horloge d'échange :

| Sleeve | N communs | CFD (bps) | **Futures (bps)** | écart | t(écart) | corr | **ratio de capture** |
|---|---|---|---|---|---|---|---|
| **GOLD** | 392 | 4.58 | **4.68** | +0.10 | 0.10 | **0.954** | **1.02** ✓ |
| **SILVER** | 433 | 10.95 | **1.99** | −8.96 | **−3.91** | 0.928 | **0.18** ✗ |
| **WTI** | 414 | 1.11 | −0.34 | −1.44 | −1.30 | 0.983 | −0.31 |
| SOYBEAN | **0** | — | — | — | — | — | **fenêtre inexistante sur CFD** |

**L'or : K2 et K3 passés, le CFD est un proxy fidèle de MGC (capture 1.02, corr 0.954).**
**L'argent : le CFD n'est PAS un proxy de SI.** Corrélation 0.93 mais niveau 5× différent, écart
significatif à t −3.91. Le drift argent du CFD est une propriété du **quote du broker à la
réouverture**, pas du contrat. Kill indépendant du kill de gap et du kill de marge.

---

## 4. Le PIÈGE N°2 — corrélation mutuelle des quatre sleeves

### (a) Historique long CFD, gap exclu, horloge d'échange, séries **nettes** (N = 3 003, 2014→2026)

| | GOLD | SILVER | WTI |
|---|---|---|---|
| **GOLD** | 1.000 | **0.689** | 0.114 |
| **SILVER** | | 1.000 | 0.210 |
| **WTI** | | | 1.000 |

corr moyenne 0.338 · **paris effectifs 2.21 sur 3** · **janvier seul (N=272) : or↔argent 0.719**
*(l'inventaire annonçait 0.86 ; je mesure 0.72 — même conclusion, un seul pari.)*

### (b) Sur les **contrats réels**, recouvrement 2024-2026 (N = 442)

| | GOLD | SILVER | SOYBEAN | WTI |
|---|---|---|---|---|
| **GOLD** | 1.000 | **0.760** | 0.064 | −0.021 |
| **SILVER** | | 1.000 | 0.056 | 0.011 |
| **SOYBEAN** | | | 1.000 | 0.102 |
| **WTI** | | | | 1.000 |

corr moyenne 0.162 · paris effectifs 3.08 sur 4.

**Or et argent sont un seul pari (0.69–0.76), très au-dessus de la limite pré-enregistrée de 0.50.**
Preuve directe de dilution : le panier équi-risque **GOLD+SILVER donne SR 1.096 contre 1.279 pour l'or
seul** — ajouter l'argent *réduit* le Sharpe, exactement le précédent US30/GER40 à 0.54.

---

## 5. Étape 3–5 — Performance nette, croissance, Kelly (le survivant)

Spec figée : **LONG à la réouverture Globex 18:00 ET, sortie 8 h plus tard à 02:00 ET**
(= 23:00→07:00 UTC de novembre à mars, **22:00→06:00 UTC de mars à novembre**), gap de pause exclu
par construction (l'entrée est le premier print à/après la réouverture). Annualisation
**√(obs/an) mesuré = 252.3** (L47), jamais √252 en dur. Séries **non winsorisées** en titre
(l'étude or d'origine ne winsorisait pas ; winsoriser 0.5/99.5 ajouterait +0.10 de SR).

### 5.1 Contrôle de reproduction — **PASS**

Ma chaîne reproduit exactement le chiffre publié par le code archivé : spec A, net 1.5 bp →
**SR 1.101, maxDD −19.4 %, N = 5 018** (rapport publié : 1.10 / −19.4 %). L'outillage est bon.

### 5.2 L'échelle des différences — d'où vient l'amélioration, bps par bps

| étape | SR brut | maxDD | drift (bps/j) |
|---|---|---|---|
| 0 · spec A archivée (UTC, H1, gap inclus) | 1.701 | −13.6 % | 4.56 |
| 1 · + horloge d'échange (H1, gap **toujours** inclus) | 2.627 | −18.2 % | 7.09 |
| 2 · + entrée M1, **gap EXCLU** | **2.010** | −8.0 % | 5.12 |
| 3 · + winsorisation 0.5/99.5 | 2.129 | −7.2 % | 5.12 |

L'horloge apporte +0.93 de Sharpe ; retirer le gap non tradable en reprend −0.62. **Le gain net et
honnête est +0.31 de Sharpe** (1.70 → 2.01 brut), et il vient avec une chute du maxDD de −13.6 % à
−8.0 %. Aucune magie : rien n'a été ré-optimisé, la fenêtre est restée 8 heures.

*L'épisode 2018-2019 documenté comme « edge éteint » subsiste mais s'atténue nettement (2018 :
−3.72 → −0.35 bps ; 2019 : +0.57 → +2.97). Spec B ≥ spec A dans 14 années sur 20.*

### 5.3 Tableau de décision — GOLD / MGC, non winsorisé

| coût RT | période | N | **SR net** | t_HAC | DSR | vol | **CAGR** | maxDD | skew |
|---|---|---|---|---|---|---|---|---|---|
| **0.66 bps (MGC base)** | 2007-2026 | 4 881 | **1.733** | 7.53 | 1.000 | 6.42 % | 11.54 % | −8.4 % | **+0.99** |
| 0.66 bps | 2014-2026 | 3 084 | **1.324** | 4.54 | 0.989 | 6.30 % | 8.49 % | −7.9 % | +1.88 |
| 0.66 bps | 2020-2026 | 1 569 | **1.313** | 3.27 | 0.803 | 5.88 % | 7.84 % | −7.9 % | +1.43 |
| 0.91 bps (stress 2 ticks) | 2020-2026 | 1 569 | 1.216 | 3.03 | 0.724 | 5.88 % | 7.23 % | −8.4 % | +1.43 |
| *1.50 bps (tarif CFD)* | *2020-2026* | *1 569* | *0.987* | *2.46* | *0.495* | *5.88 %* | *5.79 %* | *−9.6 %* | *+1.42* |

IC 90 % bootstrap par blocs du Sharpe net (2007-2026) : **[1.34, 2.13]** ; (2020-2026) : [0.72, 1.92].
Walk-forward **5/5 plis positifs** ; β vs achat-conservation de l'or **0.0135, R² 0.0012**, α
+5.07 bps/j (t 9.22) → alpha orthogonal, pas du timing sur beta (L38 satisfait).

**La ligne décisive est la dernière.** Au tarif CFD de 1.5 bps, le régime récent tombe à SR 0.99 et
DSR 0.495 — sous le gate. **À 0.66 bps sur MGC il remonte à 1.31 / DSR 0.803.** Le passage aux
futures n'est pas cosmétique : **l'économie de coût est ce qui fait vivre le sleeve dans le régime
actuel.** C'est la réponse directe à la question posée.

### 5.4 Le caveat qui compte — à €13 k le vol-targeting est INOPÉRANT

Le sleeve d'origine vol-cible en continu (multiplicateur causal, cap 3×, moyenne ~1.05×). Avec **1 lot
ou rien**, ce n'est pas implémentable. Coût mesuré (`step5_fixed_vs_vt.csv`, net 0.66 bps) :

| sizing | période | SR | t_HAC | DSR | maxDD sleeve | **skew** | vol compte | **CAGR compte** | **maxDD compte** | **pire séance** |
|---|---|---|---|---|---|---|---|---|---|---|
| VT continu | 2007-2026 | 1.733 | 7.53 | 1.000 | −8.4 % | **+0.99** | 17.4 % | 33.2 % | −21.6 % | −9.8 % |
| VT continu | 2020-2026 | 1.313 | 3.27 | 0.803 | −7.9 % | +1.43 | 16.0 % | 21.8 % | −20.4 % | −4.8 % |
| **FIXE 1 MGC** | 2007-2026 | **1.388** | 6.10 | 1.000 | −12.7 % | **−0.49** | 20.6 % | 30.3 % | **−31.9 %** | **−18.4 %** |
| **FIXE 1 MGC** | 2014-2026 | 0.935 | 3.19 | 0.776 | −12.7 % | −0.58 | 20.2 % | 18.4 % | −31.9 % | −18.4 % |
| **FIXE 1 MGC** | 2020-2026 | **0.770** | **1.91** | **0.294** | −12.7 % | **−1.32** | 23.9 % | 16.7 % | −31.9 % | −18.4 % |

Perdre le vol-target coûte **0.35 de Sharpe**, **retourne le skew de +0.99 à −0.49** (la propriété la
plus précieuse du sleeve disparaît) et ouvre une queue à **−18.4 % de compte en une séance**. Les
pires séances sont des événements réels, pas des ticks : 2026-02-01 (−6.8 % sur la fenêtre),
2026-01-29, 2011-09-25, 2020-03-22/23 — toutes en régime de vol élevé, précisément ce que le
vol-target coupait.

### 5.5 Kelly fractionnaire sur $15 000 (régime récent 2020-2026, SR 1.31, vol 5.88 %)

Kelly plein = SR/σ = **22.3× de notionnel = 8.2 contrats MGC**.

| sizing | levier | contrats (entier) | marge | vol compte | CAGR | maxDD | faisable ? |
|---|---|---|---|---|---|---|---|
| **1 MGC (minimum)** | 2.71× | 1 | **15.4 %** | 16.0 % | 21.8 % | −20.4 % | **oui** |
| **¼ Kelly** | 5.6× | 2 | 30.8 % | 31.9 % | 44.6 % | −37.9 % | oui, mais |
| **½ Kelly** | 11.2× | 4 | **61.6 %** | ~64 % | ~90 % | ~−70 % | **non** (marge) |

**Le lot minimum vaut 0.12 Kelly — la granularité ne force PAS un excès de levier, contrairement à ce
que craignait l'inventaire.** Elle mord ailleurs : elle interdit le vol-targeting (§5.4). Contrôle de
la loi de croissance : `g ≈ (2f − f²)·SR²/2` avec f = 0.12 et SR 1.31 donne **19.4 %/an** contre
21.8 % mesuré — cohérent.

**Taille recommandée : 1 MGC.** Deux contrats donnent −38 % de maxDD sur un sleeve mono-mécanisme
ayant une sécheresse documentée de 4.7 ans : hors de proportion pour un compte de €13 k.

---

## 6. Le soja — la bonne heure n'a jamais été mesurée

Disponibilité des barres CFD par heure UTC (`step1b_bar_availability.csv`) : la session SOYBEAN du
broker ouvre à ~**02:00 UTC en hiver / 01:00 UTC en été**, tandis que le CBOT rouvre à **01:00 UTC
hiver / 00:00 UTC été**. **Le CFD ne cote jamais l'heure de réouverture du CBOT** — en horloge
d'échange, l'heure ET 20 (la réouverture) n'a que 141 + 177 barres sur ~2 100 séances.

Conséquences :
- l'étude archivée mesure la **deuxième heure**, pas la réouverture ; son break-even de 2 bps
  est calculé sur la mauvaise fenêtre. **Le verdict K4 de l'étape 0 pour MZS est donc caduc en tant
  que kill** : il repose sur un chiffre non valide ;
- reconstruire la vraie fenêtre sur CFD donne **N = 13 séances exploitables** → impossible ;
- sur le **contrat réel ZS=F**, 2024-2026, la vraie fenêtre (20:00 → 02:00 ET) donne
  **+9.65 bps/j, t_HAC 2.84, N = 463**, dont +7.79 bps sur la seule première heure (t 2.97), avec un
  gap de réouverture **négatif** (−4.46 bps) — profil opposé à celui de l'argent, donc pas un
  artefact de gap.

Face à un coût MZS de 3.89 bps (base) / 4.94 (stress), 9.65 bps de brut laisserait ~5.8 bps nets.
**Mais N = 463 sur 2 ans ne prouve rien** (ma pré-registration l'interdit explicitement), et
l'hypothèse « 1 tick de large » est la plus fragile de toutes sur un micro-ag lancé récemment et coté
à 20:00 ET. **Verdict : UNDERPOWERED, pas REJECTED.** C'est le seul dossier du bloc qui mérite un
suivi, et son test décisif est bon marché et précis : **obtenir un historique intraday ZS de ≥10 ans
et relever le spread réel de MZS à 20:00–21:00 ET.**

---

## 7. Tableau de verdicts

| Sleeve | Contrat | Étape qui tranche | SR net déployable | Croissance | MaxDD compte | Marge | **VERDICT** |
|---|---|---|---|---|---|---|---|
| **OR** `ASIA_23_8` → *reopen 18:00 ET* | **MGC** | passe tout | **1.39** (2007-26, fixe 1 lot) / 0.77 (2020-26) | **+30 %/an** (18 % sur 2014-26) | **−31.9 %** | 15.4 % | **PASS conditionnel** |
| **ARGENT** | SIL | 0, 1c, 2b — **trois kills indépendants** | 0.70 → non déployable | — | — | **43.1 %** | **REJECTED** |
| **WTI** | MCL | 0 (coût) puis 1c, 2b | **−0.67** | négative | −57.7 % | 5.6 % | **REJECTED** |
| **SOJA** | MZS | 1b/2 — fenêtre jamais mesurée | inconnu (2 ans : SR 1.91 brut) | inconnu | inconnu | 1.4 % | **UNDERPOWERED** |

**Détail des trois kills de l'argent** (chacun suffirait) :
1. **Matériel** : marge 43.1 % du compte **et** notionnel 3.88× — SIL est le plus petit contrat argent
   listé, il n'y a pas de granularité en dessous ;
2. **Gap** : 59.3 % du rendement de fenêtre archivé est le gap de pause, non tradable (77.5 % en été) ;
3. **Transfert** : sur le contrat réel, ratio de capture **0.18**, écart significatif (t −3.91).

**WTI** : coût MGC-équivalent 3.67 bps contre un break-even publié de 3.5 ; 35 % de gap ; et sur la
période de recouvrement le CFD lui-même ne montre plus que 1.11 bps. Net −0.67 de Sharpe. Mort.

---

## 8. Panier — **il n'en existe aucun de défendable**

La règle P1 pré-enregistrée exige ≥ 2 sleeves PASS individuels, corrélation mutuelle < 0.35,
N_eff ≥ 2.0 et somme des marges ≤ 60 %. **Un seul sleeve passe.** Et la seule paire dont on aurait pu
rêver — or + argent — est corrélée **0.69 (historique) / 0.76 (contrats réels) / 0.72 (janvier)**, et
le panier équi-risque **détruit** du Sharpe (1.096 contre 1.279 pour l'or seul).

**Recommandation : sleeve unique, 1 MGC.** Ce n'est pas un panier, et il ne faut pas le présenter
comme tel. La conclusion de l'audit d'origine (« déployer en panier, ~2.5 paris effectifs ») ne
survit pas : deux des trois jambes non-or étaient des artefacts de mesure, la troisième est
cost-dead.

---

## 9. Spécification déployable (si l'or est retenu)

```
Instrument : MGC (Micro Gold, COMEX, 10 oz), 1 contrat, compte IBKR ~$15 000
Entrée     : ACHAT à la réouverture Globex, 18:00 America/New_York
             = 23:00 UTC de nov. à mars | 22:00 UTC de mars à nov.
Sortie     : VENTE 8 h plus tard, 02:00 America/New_York
             = 07:00 UTC hiver | 06:00 UTC été
Sizing     : fixe, 1 contrat. Le vol-target de la recherche N'EST PAS implementable
             a cette granularite -> cout mesure : -0.35 de Sharpe, skew +0.99 -> -0.49
Coût       : ~0.66 bps RT (1 tick $1.00 + $1.70 commission sur $40 709 de notionnel)
Marge      : $2 308 (15.4 %) — a revérifier, les marges métaux bougent (CME est passé
             à un barème en % du notionnel en janvier 2026)
Jamais     : ne pas entrer au close de la barre horaire de réouverture (piège L52 §3.2) ;
             ne pas réclamer le gap de pause (il n'est pas tradable) ;
             ne pas trader une fenêtre incomplète.
```

**L'entrée se fait au tick de réouverture après une pause d'une heure** — c'est le pire moment de la
journée pour le spread. L'hypothèse de 1 tick de large est la variable make-or-break ; le scénario
stress à 2 ticks (0.91 bps) laisse SR 1.22 / DSR 0.72 sur 2020-2026, donc il y a de la marge, mais
elle doit être **mesurée en réel avant de dimensionner**.

---

## 10. Honnêteté de méthode

- **`n_tests` consommés : 5** (contraste DST × 4 sleeves + règle de panier), conformément au budget
  pré-enregistré. Aucune fenêtre re-choisie, aucune ré-optimisation, aucun balayage. Les décompositions
  (gap, profil horaire, disponibilité des barres, validation futures) sont des **diagnostics de
  mesure**, pas des essais de stratégie.
- **Une seule modification de spec** utilisée sur les 3 autorisées : A → B (horloge d'échange).
  Budget restant : 2.
- **Bootstrap par blocs stationnaire partout** (Politis–Romano, bloc moyen 10 j, 5 000 tirages).
  Aucun bootstrap iid.
- **DSR** calculé avec `n_trials = 95` (90 essais de la recherche or d'origine + 5 d'ici).
- **Reproduction du chiffre archivé vérifiée** avant toute revendication (§5.2).
- **Deux erreurs de ma part, signalées** : la décimale de commission MCL/MZS de la pré-registration
  (§1) et le piège L52 sur l'étiquetage des barres Yahoo (§3.2), attrapé parce que le résultat
  paraissait trop mauvais — la même discipline qui, dans l'autre sens, m'a fait auditer l'or (§5.2).
- **Limite assumée** : l'échantillon futures ne couvre que 2024-03 → 2026-07. Il valide le **mapping**
  et le **transfert** ; il ne mesure aucune performance. Toute la performance vient du CFD, dont on a
  démontré (or seulement) qu'il est un proxy fidèle à 1.02.
- **Risque de change non couvert** : compte en EUR, contrat en USD.

---

## 11. Ce qui a été produit

```
PREREGISTRATION.md              figée avant mesure
RESULTS.md                      ce document
code/common.py                  chargement, fenêtres, DST, bootstrap par blocs
code/step0_vehicle.py           L53 matrice de véhicule
code/step1_session_map.py       contraste DST spec A vs B
code/step1b_diagnostics.py      profil horaire, expérience naturelle, disponibilité des barres
code/step1c_gap_decomposition.py  gap de pause vs part capturable (M1)
code/step2_futures_validate.py  calendrier + tick-match sur GC/SI/CL/ZS
code/step2b_apples.py           futures vs CFD, mêmes séances, gap exclu
code/step3_performance.py       performance, beta, sizing
code/step3b_audit.py            reproduction + échelle des différences + année par année
code/step4_correlation_basket.py  matrices de corrélation, règle P1
code/step5_final.py             tableau de tête, Kelly, soja
results/*.csv                   17 tables
```
