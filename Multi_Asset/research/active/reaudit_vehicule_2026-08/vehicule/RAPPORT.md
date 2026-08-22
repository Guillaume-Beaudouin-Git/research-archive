# PROGRAMME 2 — La question du véhicule

**Parmi les familles tuées SUR LE COÛT, lesquelles vivent sur futures IBKR ?**

Protocole gelé : `../PREREGISTRATION.md` §2, règles P2-R1→R4, **non renégociées**.
Interpréteur `/usr/bin/python3`. Lecture seule sur tout chemin du dépôt principal ;
écriture confinée à `vehicule/`. Aucune commande git. Bootstrap par blocs
(Politis–Romano) partout, iid jamais. Annualisation en √(obs/an) mesuré. **N rapporté
partout.**

---

## 0. Le verdict, en quatre lignes

1. **Le tri est brutal et il est sain : 74 des 118 edges mesurés du dépôt (63 %) sont
   morts MÉCANIQUEMENT** et restent fermés sans exception (P2-R1). **11 seulement sont
   tués sur le COÛT** sans composante mécanique.
2. **Le test L53 est unanime et il tranche la question propfirm avant tout backtest :
   15 lots minimum sur 16 tiennent sous 35 % d'un compte de €12 000** (marge médiane
   **16.3 %**). Pour ces familles, **un propfirm n'apporte rien** — il vend du levier
   déjà disponible.
3. **Le re-gate au coût futures n'a produit AUCUN survivant.** 10 lignes sur 14
   franchissent `gross/cost_p95 ≥ 1.5` — jusqu'à **31×** — et **toutes se referment sur
   un SECOND kill que le changement de véhicule ne touche pas** : puissance, sélection,
   ou magnitude d'IC. Le coût n'était le facteur liant d'**aucune** des familles qui
   passent le gate.
4. **Mais la question posée n'est pas « peut-on trouver un edge »**. Sur le seul point
   qui décide de l'allocation d'effort, la réponse est nette et chiffrée : **le prochain
   edge ne doit pas vivre sur FTMO.** Le compte perso divise le coût par **2 à 5×** sur
   les gros contrats, supprime la barrière, l'horloge, et rend 100 % du P&L — et c'est
   déjà là que sont allés les **quatre** derniers edges vivants du dépôt.

---

## 1. Le tri : mécanique contre coût

C'est le tri décisif, et il doit venir en premier. **P2-R1** : un kill MÉCANIQUE (gross
≈ 0, two-sided négatif à coût NUL, régime-dépendant, sous placebo) reste fermé — réparer
un dénominateur ne ressuscite pas un numérateur nul.

Source : `edge_inventory_2026-07/INVENTORY.csv`, 118 entrées, N0 (fouille de rapports,
zéro mesure produite). Classification reproductible : `code/step1_tri.py`
→ `out/tri_kill_nature.csv`, `out/inventaire_annote.csv`.

| statut P2-R1 | n | part |
|---|--:|--:|
| **FERMÉ — kill mécanique** | **74** | **63 %** |
| ROUVRABLE — puissance | 12 | 10 % |
| **ROUVRABLE — coût** | **11** | **9 %** |
| bloqué — données | 8 | 7 % |
| ROUVRABLE — véhicule | 7 | 6 % |
| ROUVRABLE — géométrie | 5 | 4 % |
| autre | 1 | 1 % |

17 entrées portent une mention de coût ; **6 d'entre elles portent AUSSI un kill
mécanique** et sont donc fermées par P2-R1 (la plus instructive : `M006` piste B
range-fade — la détection du range est look-ahead, causale −0.06 contre oracle +2.66 ;
la jambe XAU cost-dead est le second kill, pas le premier). **Reste 11 familles.**

> **Ce que ce tri dit du processus de recherche** : 63 % de kills mécaniques est un
> taux **sain**. Le dépôt ne jette pas des edges valables en masse. Le reproche
> documenté est différent et plus précis — il laisse mourir les edges valables **au
> dernier gate, celui du véhicule**. C'est exactement ce que ce programme teste.

### Les 11 familles tuées sur le coût

| id | famille | instrument d'origine | brut publié | coût qui l'a tuée | véhicule supposé à l'époque |
|---|---|---|--:|---|---|
| E003 | Argent overnight (post-2014) | XAGUSD CFD | 1.99 bps (contrat réel) | break-even 5.3 bps RT | CFD FTMO |
| E004 | WTI overnight | USOIL CFD | 3.20 bps capturable | break-even ~3.5 bps RT | CFD FTMO |
| E005 | Soja — dérive de réouverture CBOT | SOYBEAN CFD | 9.65 bps (ZS=F) | ≤2 bps requis | CFD FTMO |
| E011 | Blé — saisonnalité de mai | WHEAT CFD | +241 bps/mai | swap grain ~−115 bps/mois | CFD FTMO |
| E014 | VRP S1 (VIX − RV) swing | QQQ ETF | 14.2 bps/rotation | 0.10 % RT ETF, turnover 33×/an | ETF |
| E018 | Flux lev-ETF (30 dern. min NQ) | NQ | +1.73 bps (Q90) | ~0.5 bps supposé, **jamais mesuré** | CFD/NQ |
| M022 | Continuation de gap CPI/NFP | US100 CFD | +9.40 bps two-sided | 3 bps RT | CFD FTMO |
| R006 | PMR basis delta-neutral | perps crypto | — | 0.17 % RT → 178 %/an de drag | perp exchange |
| R012 | Réversion H1 ouverture Londres | FX majors | ~0.50 bps | 2-5 bps CFD RT | CFD FTMO |
| R015 | Réversion du fix WMR (Ranaldo) | G10 | 2.07 bps/j two-sided | 2.48 bps RT retail | CFD retail |
| R021 | Fade de l'ORB raté (D1) | NQ | non isolé | $19 RT | futures/CFD |

**Ajout hors-inventaire** : l'**ORB funded** (`orb_cost_funded_2026-08`, 2026-08-13) est
le kill de coût le plus récent du dépôt et postérieur à l'inventaire. Il est traité en
§5 — c'est le cas le plus serré de tout le re-gate.

---

## 2. La matrice de véhicule — **AVANT** tout backtest (L53)

L'ordre n'est pas cosmétique. C'est un correctif de process explicite : le biais
« véhicule en dernier » a coûté **deux rejets** au month-end ZN, edge validé
(t_HAC 4.65) et aujourd'hui déployé sur le compte perso à **+17.6 %/an, SR 0.92 net**.

`code/common.py:contract_specs()` reproduit **exactement** la table canonique de
`overnight_futures_2026-07` (MGC 0.663 vs 0.66 publié · SIL 1.152 vs 1.15 · MCL 3.672 vs
3.67 · MZS 3.891 vs 3.89) — contrôle de reproduction passé avant tout usage.
Compte : **€12 000 × 1.1522 = $13 826**.

| famille | contrat | notionnel | marge lot min | % du compte | notionnel/compte | **test L53** |
|---|---|--:|--:|--:|--:|---|
| E001 month-end | **ZN** | $112 000 | $1 800 | **13.0 %** | 8.10× | **OUI** → propfirm dominé |
| E002 or overnight | **MGC** | $40 709 | $2 308 | **16.7 %** | 2.94× | **OUI** → propfirm dominé |
| E003 argent | SIL | $58 164 | $6 469 | **46.8 %** | 4.21× | **hors budget (M1)** |
| E004 WTI | MCL | $7 352 | $840 | 6.1 % | 0.53× | OUI |
| E005 soja | MZS | $5 975 | $210 | **1.5 %** | 0.43× | OUI |
| E011 blé | ZW | $29 975 | $2 200 | 15.9 % | 2.17× | OUI |
| E014/E018/M022/R021/ORB | MNQ | $60 000 | $3 200 | 23.1 % | 4.34× | OUI |
| R012 | M6E | $14 500 | $350 | 2.5 % | 1.05× | OUI |
| R015 fix WMR | 6E | $145 000 | $2 900 | 21.0 % | **10.49×** | marge OUI, **notionnel non** |
| R006 crypto | **aucun** | — | — | — | — | pas d'instrument |

**Résultat du test L53 : 15 sur 16 contrats tiennent sous 35 % du compte, marge médiane
16.3 %.** Un propfirm vend du levier sur du capital qu'on n'a pas ; ici le capital est
là. **Pour toute cette matrice, la route propfirm est strictement dominée** : pas de
barrière, pas d'horloge, 100 % du P&L, et un coût plus bas.

⚠ **Les marges bougent** (le CME est passé à un barème en % du notionnel en janvier
2026). Les valeurs marquées `ordre de grandeur` dans `code/common.py` doivent être
revérifiées avant tout engagement ; les valeurs MGC/SIL/MCL/MZS viennent d'une table
live rafraîchie le 2026-07-30, ZN de `month_end_vehicle`.

⚠ **Divergence relevée sur ZN** — `swapkilled_futures_2026-07/PREREGISTRATION.md` §4
chiffre le coût RT de ZN à **~0.3 bps**. Le calcul direct donne **1.55 bps**
(1 tick $15.625 + $1.70 de commission sur $112 000), et `month_end_vehicle` retient
$19 RT ≈ 1.6 bps — cohérent avec le mien. **Le 0.3 bps est faux d'un facteur ~5.** Il
n'a inversé aucun verdict (le month-end vaut 16-37 bps par événement, ratio ≈ 5.5 même
au chiffre corrigé), mais cette table est réutilisable par d'autres sessions et
l'erreur doit être signalée.

---

## 3. Le re-gate au coût futures (P2-R2)

`cost_p95` : à défaut d'une distribution de fourchette futures mesurée, j'utilise la
convention de stress documentée du dépôt — **2 ticks au lieu d'un** — comme majorant de
queue. C'est la convention d'`overnight_futures_2026-07`, et elle est conservatrice.

| id | coût CFD d'origine | coût futures base | cost_p95 | brut | **ratio** | P2-R2 (≥1.5) |
|---|---|--:|--:|--:|--:|---|
| E003 argent | 5.3 bps break-even | 1.152 | 2.012 | 1.99 | **0.99** | **FAIL** |
| E004 WTI | ~3.5 bps break-even | 3.672 | 5.033 | 3.20 | **0.64** | **FAIL** |
| E005 soja | ≤2 bps requis | 3.891 | 4.937 | 9.65 | 1.96 | PASS |
| E011 blé | swap −115 bps/mois | 4.737 | 8.907 | 241.0 | **27.06** | PASS |
| E014 VRP | 0.10 % RT ETF | 0.367 | 0.450 | 14.2 | **31.56** | PASS |
| E018 lev-ETF | ~0.5 bps supposé | 0.367 | 0.450 | 1.73 | 3.84 | PASS |
| M022 gap CPI/NFP | 3 bps RT | 0.367 | 0.450 | 9.40 | **20.89** | PASS |
| R006 PMR | 0.17 % RT | — | — | — | — | pas de véhicule |
| R012 Londres | 2-5 bps CFD | 2.034 | 2.897 | 0.50 | **0.17** | **FAIL** |
| R015 fix WMR | 2.48 bps retail | 0.548 | 0.979 | 2.07 | 2.11 | PASS |
| ORB | 1.80 bps mesuré | 0.617 | 0.783 | *frontière* | — | **FAIL** (§5) |

**Le re-gate fonctionne, et fort.** Le passage au véhicule futures divise le coût par
**2 à 5×** sur les gros contrats (MNQ 1.80 → 0.367 bps ; 6E 2.48 → 0.548) et supprime
entièrement le swap sur les familles tenues. Six familles franchissent le gate, deux
d'entre elles par plus d'un ordre de grandeur.

### Les quatre qui échouent quand même — et pourquoi c'est instructif

- **E003 argent (0.99)** et **E004 WTI (0.64)** échouent parce qu'`overnight_futures_2026-07`
  a déjà mesuré que leur brut CFD était **faux**. L'argent : **59 % du rendement de
  fenêtre est le GAP de la pause de settlement**, non tradable (77.5 % l'été), et sur le
  contrat réel la capture tombe à **0.18** (t −3.91 sur l'écart). Le WTI : 35 % de gap, et
  −0.34 bps sur le contrat réel. **Ce ne sont plus des kills de coût : ce sont des kills
  MÉCANIQUES révélés par le passage au véhicule.** Ils basculent en « fermé » définitif.
- **R012 (0.17)** : déjà re-testé au tarif futures par `fx_intraday`, gate non franchi.
  Cohérent avec L43 (0.36) et ses deux réplications indépendantes (carte du gross 0.38,
  exogènes 0.336). Le tier retail FX ne se sauve pas par le contrat.
- **R006** : aucun véhicule futures n'existe pour du basis de perp crypto. Le plafond
  L12 est intrinsèque au tarif d'exchange.

---

## 4. **Le résultat central : le second kill**

C'est ici que le programme répond réellement à sa question.

**Aucune** des six familles qui franchissent P2-R2 n'est libérée par le passage aux
futures, parce qu'**aucune n'était liée par le coût au moment décisif**.

| id | ratio au coût futures | **le kill que le véhicule NE touche PAS** |
|---|--:|---|
| E005 soja | 1.96 | **PUISSANCE** — N = 463 sur 2 ans ; walk-forward ≥5 plis **impossible** (règle dure) |
| E011 blé | 27.06 | **PUISSANCE + SÉLECTION** — mesuré ici : IC95 bootstrap **[−100, +496] contient zéro** ; **sous son placebo de sélection-de-mois** (p 0.333) |
| E014 VRP | 31.56 | **SIGNAL** — le SR au coût futures était **déjà calculé : 0.454** < 0.7. L'IC (0.050-0.075) est une propriété du signal |
| E018 lev-ETF | 3.84 | **PUISSANCE** — t plafonne ~1.3 : l'écart-type de `r_last30` (31 bps) noie un edge de 1.7 bps |
| M022 gap CPI/NFP | 20.89 | **PUISSANCE** — t net 0.69 ; re-échelonné au coût MNQ le t ne monte qu'à ~0.96, N = 146 |
| R015 fix WMR | 2.11 | **L57 + L23** — ne passe **que** sur le 6E plein, notionnel **10.5× le compte** ; le micro M6E retombe à **0.71** |

C'est la leçon H1 de `swapkilled_futures_2026-07`, reproduite sur un échantillon dix
fois plus large et sur une catégorie de kill différente :

> **Le changement de véhicule répare le dénominateur, jamais le numérateur.** Attribuer
> la mort d'une famille à la contrainte AMOVIBLE (le coût) plutôt qu'à la contrainte
> STRUCTURELLE (la puissance, l'IC, la sélection) fabrique un faux espoir de
> ré-ouverture. Là-bas c'était le swap qui masquait le bêta ; ici c'est le spread CFD
> qui masque un t-stat de 0.7 à 1.3.

**Corollaire opératoire, et c'est le vrai livrable de méthode :** `gross/cost ≥ 1.5` est
un gate **nécessaire, pas suffisant**, et il est **bon marché à franchir par changement
de véhicule**. Il ne doit jamais être présenté comme une ré-ouverture. Une famille tuée
sur le coût doit exhiber, AVANT le re-gate, un **t-stat qui survivait déjà à coût nul** —
sinon le coût n'était qu'un second tueur commode.

Cinq des six familles ci-dessus avaient, **à coût strictement nul**, un t entre **0.69 et
1.49**. Une seule (R015, t 3.55) avait un vrai t — et elle meurt sur la granularité.

---

## 5. Le cas le plus serré : l'ORB

`orb_cost_funded_2026-08` (2026-08-13) ne publie pas un brut par trade mais une
**frontière de coût** : R2 (t_HAC > 2.0) tient tant que le coût RT reste sous
**0.588 bps** ; la moyenne elle-même passe négative à 2.189 bps. Le coût CFD mesuré est
**1.80 bps** (deux méthodes indépendantes concordant à 0.5 %) → ORB_KILL.

Le re-gate devient une comparaison directe. Le piège serait de ne facturer que le tick
et la commission : **L19 mesure sur NQ un dérapage de base de 4 ticks RT ($2/MNQ)**, et
impose de stresser ≥1.5×. `code/step4_orb_frontiere.py` → `out/orb_frontiere_mnq.csv` :

| scénario | dérapage | coût RT | **vs frontière 0.588** |
|---|--:|--:|---|
| A. 1 tick + commission (le plus favorable) | $0.50 | **0.367 bps** | ✅ −0.221 |
| **B. L19 base : 4 ticks RT mesurés** | $2.00 | **0.617 bps** | ❌ **+0.029** |
| C. L19 stress ×1.5 (imposé par la leçon) | $3.00 | 0.783 bps | ❌ +0.195 |
| D. L19 fills adverses ×3 (borne documentée) | $6.00 | 1.283 bps | ❌ +0.695 |

**1 scénario sur 4 passe — et ce n'est pas celui que L19 mesure.** Le passage au
véhicule comble **80 % de l'écart** (1.80 → 0.37-0.62 bps) et **manque la frontière de
0.029 bps**, soit 5 %. Sur un dossier où la leçon dédiée impose un stress ×1.5, cette
marge n'existe pas.

Et surtout : **R4 est intact**. Le walk-forward donne **2/5 plis positifs (40 %)** au
coût mesuré, sous le seuil RESEARCH_PASS de 50 %, avec les trois premiers plis négatifs
— l'edge est entièrement récent. **Un pli de walk-forward ne bouge pas avec le
véhicule.** Même en accordant le scénario A, l'ORB reste tué par R4.

> Ce dossier est le meilleur argument du rapport contre l'optimisme de ré-ouverture :
> c'est la famille où le véhicule aide le PLUS en valeur absolue, et elle meurt quand
> même — deux fois.

---

## 6. Le verdict de granularité (L57)

**Deux effets distincts, et le rapport les sépare.**

### 6.1 Le coût fixe ne se dilue que sur du notionnel

Trié par notionnel — la relation est directe et elle contredit « les futures sont la
route propre » :

| contrat | notionnel | **part de frais FIXE** | coût RT |
|---|--:|--:|--:|
| MZW micro blé | $2 998 | **73 %** | **7.76 bps** |
| MZS micro soja | $5 975 | 73 % | 3.89 bps |
| MCL micro WTI | $7 352 | 63 % | 3.67 bps |
| M6E micro EUR | $14 500 | 58 % | 2.03 bps |
| ZW blé plein | $29 975 | 12 % | 4.74 bps |
| MGC micro or | $40 709 | 63 % | **0.66 bps** |
| MNQ micro NQ | $60 000 | 77 % | **0.37 bps** |
| 6E EUR plein | $145 000 | 21 % | **0.55 bps** |

**$1.70 de commission fixe vaut 7.8 bps sur MZW et 0.28 bps sur MNQ — un facteur 28 pour
le même frais.** Les quatre plus petits contrats coûtent **2.0 à 7.8 bps RT**, c'est-à-dire
le tarif CFD ou pire. Sur un compte de €12 000, « passer aux futures » n'est une
économie que si le contrat porte au moins ~$40 000 de notionnel.

**Le piège de ciseaux, mesuré deux fois.** La famille a besoin du petit contrat pour la
granularité et du gros pour le coût, et ne peut pas avoir les deux :

- **R015 fix WMR** : passe le gate sur 6E (ratio **2.11**) dont le notionnel est
  **10.49× le compte** — infaisable ; sur le micro M6E, granulaire (1.05×), le ratio
  tombe à **0.71** → mort. Le coût qui a tué la famille au tier retail la retue au tier
  micro-futures.
- **E005 soja** : ZS plein coûte 1.33 bps (ratio 4.06) mais pèse 4.32× le compte ; MZS,
  parfaitement granulaire (0.43×), coûte **3× plus cher** (3.89 bps, ratio 1.96).

### 6.2 La granularité mord surtout en INTERDISANT le vol-targeting

C'est l'effet dominant, et il est déjà mesuré sur le seul sleeve déployable de la
famille (`overnight_futures_2026-07` §5.4, or sur MGC, N=4 881, 2007-2026) :

| sizing | SR | **skew** | maxDD compte | **pire séance** |
|---|--:|--:|--:|--:|
| vol-target continu | 1.733 | **+0.99** | −21.6 % | −9.8 % |
| **FIXE 1 MGC** | 1.388 | **−0.49** | **−31.9 %** | **−18.4 %** |

Perdre le vol-target coûte **0.35 de Sharpe**, **retourne le skew de +0.99 à −0.49** — la
propriété la plus précieuse du sleeve — et ouvre une queue de **−18.4 % de compte en une
séance**.

**Mesuré ici sur le blé** (`code/step3_ble.py`, ZW=F, N=5 411 séances) :

| contrat | notionnel/compte | skew des séances de mai | **pire séance** | p1 des séances |
|---|--:|--:|--:|--:|
| ZW plein | 2.17× | +0.42 | **−13.5 %** | −9.4 % |
| MZW micro | 0.22× | +0.42 | −1.4 % | −0.9 % |

Le micro divise la queue par 10 — et multiplie le coût par 1.6. Sur le blé le brut est
si gros (203 bps/mois) que le coût ne mord pas ; **c'est le seul cas de la matrice où le
micro est le bon choix**, et il ne sert à rien puisque la famille est morte par ailleurs.

**P2-R4 est donc respecté au sens strict : aucune conclusion de performance n'est émise
dans ce rapport sans skew ET queue single-session au lot déployé.** Il n'y a aucun
survivant à propos duquel en émettre une.

---

## 7. La mesure faite ici : E011 blé/mai

**La seule famille tuée sur le coût qui n'ait jamais été re-mesurée sur son contrat
futures, et dont la donnée est au dépôt.** Kill d'origine (session_E2, CFD) : le swap
grain (~−115 bps/mois) ramène +241 bps brut (t 1.69) à +126 bps net (t 0.89). **Sur
ZW/MZW il n'y a pas de swap** — le portage est dans la base, transigé au roll. Le
dénominateur passe de −115 bps/mois à **4.7 bps RT**.

Spec **gelée, héritée telle quelle, aucun réglage** : LONG le mois de mai, plat sinon.
Données `data/raw/yf_ZW=F_1d_4ca92cfdb4.parquet`, 2005-01 → 2026-07, **N = 5 411
séances / 22 mois de mai**. Observations/an mesuré = **251.6** (annualisation en √251.6,
jamais √252 en dur — L47).

| | |
|---|---|
| mai, moyenne | **+203.5 bps** (médiane +189.7) |
| t simple / **t_HAC lag-6** | 1.124 / **1.486** |
| **IC95 bootstrap par blocs** (5 000 tirages, bloc moyen 3 évts) | **[−100.0, +495.7] → CONTIENT ZÉRO** |
| walk-forward 5 plis | 4/5 positifs (80 %) — mais pli 1 = +790 bps porte le résultat |
| fraction d'années positives | 0.545 (12/22) |

**Placebo apparié de sélection-de-mois (L49)** — c'est le contrôle que le DSR×12 de
l'étude d'origine approximait :

| | |
|---|---|
| pool des 11 autres mois | moyenne +10.8 bps, p50 −33.0, **p95 +309.5**, max +327.5 |
| **mai vs pool** | **3/11 mois font aussi bien ou mieux → p = 0.333** |
| meilleur mois de la série | **décembre** (+327.5 bps, t_HAC **3.442**) — **ce n'est pas mai** |

**Contrôle de baseline L58** — et il a attrapé une erreur de ma part. Ma première version
comparait la moyenne du pool (+10.8) à l'espérance inconditionnelle brute (+26.4) et
déclarait le placebo **biaisé**. C'est faux : retirer mai — un mois au-dessus de la
moyenne — déplace mécaniquement le pool vers le bas. La baseline correcte est
`(12 × inconditionnelle − mai) / 11 = +10.35 bps`, contre **+10.8 mesuré, écart 0.45 bps**.
**Le placebo est non biaisé ; c'est bien le signal qui échoue.** Sans ce contrôle
j'aurais publié un « placebo biaisé » qui aurait excusé mai.

**Verdict E011 : REJECTED.** Supprimer le swap CFD fait passer `gross/cost` de ~2 à
**27** — le gate P2-R2 est franchi par un facteur 18 — et la famille meurt exactement où
elle mourait déjà : son IC contient zéro et elle ne bat pas son propre placebo de
sélection.

> ⚠ **Décembre (t_HAC 3.442) est une observation, PAS un candidat.** Le sélectionner
> après avoir vu les douze mois est précisément le data-mining que le placebo existe
> pour attraper — et c'est ce qui a tué la version mai. **Noté, non testé**, conformément
> à la consigne « toute idée neuve se note, ne se teste pas ».

---

## 8. Où doit vivre le prochain edge ?

Le book FTMO live est **MONO** : deux jambes overnight indices, LONG-only, **sans
signal** — exposition calendaire pure. La recherche de sleeves décorrélées sur FTMO a
consommé **321 essais** sans un seul survivant déployable ; les sept derniers jours à eux
seuls : 8 695 cellules → shortlist vide, 241 prédicteurs exogènes → 0, axe du signe
fermé, dernier candidat rejeté le 12/08.

Ce programme n'a pas produit de survivant non plus. **Mais il chiffre pourquoi, et le
chiffre pointe dans une direction unique.**

### 8.1 Le motif est structurel, et il compte maintenant quatre cas

| edge | verdict FTMO | maison réelle |
|---|---|---|
| Month-end Treasury (E001) | pas d'instrument obligataire (gate-0), rejeté **2×** | **IBKR ZN** — +17.6 %/an, SR 0.92 net, déployé |
| Or overnight (E002) | NON-VIABLE : mur 91 j auto-imposé + barrière −5 % percée | **IBKR MGC** — PASS conditionnel, SR 1.39 à lot fixe |
| Paires / stat-arb (2026-08-03) | 0/171 paires compatibles séance | **IBKR** — demi-vie ≥ 1 588 min |
| Toute la matrice de ce rapport | — | **15/16 lots minimum tiennent dans €12 000** |

### 8.2 Le chiffrage

**Sur le coût.** Le passage CFD → futures divise le dénominateur par **2 à 5×** sur les
contrats à notionnel suffisant : MNQ **1.80 → 0.367 bps** (×4.9), 6E **2.48 → 0.548**
(×4.5), MGC **1.50 → 0.663** (×2.3). Pour l'or, cette seule économie fait passer le
sleeve de **SR 0.99 / DSR 0.495** (sous le gate) à **SR 1.31 / DSR 0.803** sur le régime
2020-2026 — le véhicule n'y est pas cosmétique, il est ce qui fait vivre le sleeve.

**Sur la géométrie.** Le compte perso n'a ni barrière −5 %/−10 %, ni horloge de 91 jours,
ni minimum de jours de trading. Deux des trois kills historiques de l'or overnight
étaient exactement ces contraintes — dont un **auto-imposé** (FTMO n'a aucune limite de
temps).

**Sur le P&L.** 100 % contre 80 %, sans frais d'entrée récurrent.

**Sur le levier — et c'est le point que L53 rend décisif.** Un propfirm vend du levier
sur du capital qu'on n'a pas. Ici la marge médiane du lot minimum est de **16.3 % du
compte**. Il n'y a rien à acheter.

### 8.3 La réponse, sans détour

**Le prochain edge ne doit pas vivre sur FTMO.** Non pas parce que FTMO est mauvais, mais
parce que la contrainte qu'il ajoute — barrière symétrique, horloge, univers CFD à 2-7 bps —
est précisément celle qui a tué les quatre derniers edges vivants du dépôt, et parce
qu'à €12 000 elle n'achète aucun levier qui ne soit déjà disponible.

**Ce que cela n'autorise PAS.** Le compte perso ne ressuscite rien tout seul : ce
programme vient de le mesurer sur onze familles, avec **zéro survivant**. Le véhicule
répare un dénominateur ; il ne fabrique ni t-stat, ni N, ni IC. La conclusion utile
n'est donc pas « chasser sur IBKR », c'est **poser le véhicule au début du protocole**
(L53) et **exiger, avant tout re-gate de coût, un t-stat qui survivait déjà à coût nul**.

---

## 9. Honnêteté de méthode

- **`n_tests` consommés : 0.** Ce programme rouvre des familles **déjà comptées** au
  ledger ; le re-gate au coût futures d'une hypothèse pré-enregistrée est une
  **correction**, pas un essai (prereg §1.5). Le DSR des candidats futurs est intact.
  Une seule mesure a été produite (E011 sur ZW=F, spec gelée héritée, aucun réglage).
- **Deux erreurs de ma part, signalées.** (i) Mon contrôle L58 a d'abord déclaré le
  placebo du blé « biaisé » en comparant à l'inconditionnelle brute au lieu de la
  baseline leave-one-out — j'aurais excusé un échec ; corrigé, écart 0.45 bps. (ii)
  Ma table de coûts a révélé une divergence ZN de facteur ~5 avec
  `swapkilled_futures/PREREGISTRATION.md` §4 — sans conséquence de verdict, mais la
  table est réutilisable et l'erreur devait être dite.
- **Bootstrap par blocs partout** (Politis–Romano, 5 000 tirages) ; aucun bootstrap iid.
  HAC lag-6 sur toute moyenne. Walk-forward 5 plis. **N rapporté partout.**
- **Reproduction contrôlée avant usage** : ma table de contrats reproduit la table
  canonique d'`overnight_futures_2026-07` à 0.5 % sur les quatre contrats communs.
- **Limites assumées.** (a) `cost_p95` futures est un **majorant de convention** (2 ticks),
  pas une distribution mesurée — aucune mesure de fourchette futures intraday n'existe
  au dépôt, et §7 de `COST_AUDIT.md` note que le bon dénominateur est le spread **à
  l'heure tradée**. (b) Les marges non issues de la table live du 2026-07-30 sont des
  ordres de grandeur. (c) Les `gross_bps` sont des chiffres **publiés**, hérités avec
  leurs propres réserves ; je ne les ai pas re-mesurés, sauf pour E011.
- **Résultat défavorable publié tel quel.** Zéro survivant. Les règles de kill n'ont pas
  été renégociées après avoir vu les chiffres.

### Noté, non testé (hors périmètre — aucune de ces idées n'a été mesurée)

1. **E014 VRP sous la règle d'admission ACTUELLE.** Son kill combine le coût ETF *et* le
   gate « Sharpe > 0.7 en standalone », **que `CLAUDE.md` a depuis abandonné** au profit
   de `ΔSR_book > 0 au poids ERC`. Au coût MNQ le SR est **0.454** avec IC 0.05-0.075
   stable pré/post-2020 et WF 4/5. **C'est le seul dossier de la matrice dont le kill
   invoque un gate qui n'existe plus.** Test décisif nommé : ΔSR au poids ERC contre le
   book perso (month-end ZN + spread grid), significatif au block-bootstrap, avec effet
   minimum détectable rapporté. Ce n'est pas une chasse — c'est une admission.
2. **E005 soja.** Verdict UNDERPOWERED, pas REJECTED. Test décisif déjà nommé par
   `overnight_futures` : historique intraday ZS ≥ 10 ans + relevé du spread réel de MZS
   à 20:00-21:00 ET. Sans cela, la règle dure des 5 plis interdit toute conclusion.
3. **Décembre sur ZW** (t_HAC 3.442) — data-mining de mois. Ne pas tester.

---

## 10. Fichiers

| chemin | contenu |
|---|---|
| `out/matrice_vehicule.csv` | **le livrable** — 17 lignes × 20 colonnes : nature du kill, future correspondant, marge lot min, verdict L53, ratio gross/cost_p95 au coût futures, second kill, verdict P2 |
| `out/tri_kill_nature.csv` | le tri P2-R1 sur les 118 entrées |
| `out/inventaire_annote.csv` | les 118 entrées avec leur statut P2-R1 |
| `out/orb_frontiere_mnq.csv` | les 4 scénarios de coût MNQ contre la frontière R2 |
| `out/ble_profil_mensuel.csv` | ZW=F, 12 mois × (moyenne, t_HAC, skew, frac>0) — le placebo |
| `out/ble_mai_par_an.csv`, `out/ble_walkforward.csv` | E011 par année et par pli |
| `code/common.py` | specs de contrats, HAC lag-6, bootstrap par blocs |
| `code/step1_tri.py` · `step2_matrice.py` · `step3_ble.py` · `step4_orb_frontiere.py` | reproduction, dans cet ordre |

*Reproduire : `/usr/bin/python3 code/step1_tri.py && … step2_matrice.py && … step3_ble.py && … step4_orb_frontiere.py`*
