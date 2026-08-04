# Audit de la sleeve OR du livre déployé — 2026-08-04

**Verdict en une ligne : l'observation sur la dead-zone est EXACTE au niveau mécanique, et
FAUSSE au niveau économique. Le seuil 0.34 annule bien tous les états « 2 sur 3 » — mais ces
états ne rapportent RIEN (+0.004 bps d'excès, t 0.00, N=1421). La dead-zone n'est pas un bug de
calibration, c'est un filtre de COÛT qui s'auto-finance. Le vrai problème est ailleurs : la
sleeve n'a plus d'edge net.**

Statut : **DIAGNOSTIC**. Aucune modification de spec recommandée. Rien n'a été touché en live.

Sources canoniques (lecture seule) :
`data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py:125-170` (`build_signals`) —
le miroir sim↔live trackè ; `data/ftmo_portfolio/sleeves.py:18-33` ; `data/ftmo_portfolio/v22/spec_v22.yaml`.
Panels : `data/ftmo_portfolio/cache/panel_{px,rets,swapL,swapS,mult}.parquet`,
`outputs/phase0_rt_cost_bps.csv`. Fenêtre **2013-10-01 → 2026-06-05**, N=3232-3309 séances.
Interpréteur `/usr/bin/python3` (pandas 2.2.3 vérifié).

---

## 1. La pondération du blend — vérifiée, pas crue sur parole

Le code canonique, ligne 141 de `cleanroom/engine.py` :

```python
sig = sum(np.sign(base / base.shift(L) - 1.0) for L in lookbacks) / len(lookbacks)
sig = sig.where(sig.abs() >= theta, 0.0)
```

C'est une **somme divisée par 3 — poids strictement égaux**, et non une moyenne `skipna`
(nuance importante : `sleeves.py` utilise `.mean(axis=1)`, qui tolère les NaN de warm-up ;
la version LIVE ne le fait pas, donc l'espace d'états est exactement 4 valeurs, sans état
intermédiaire de démarrage).

Distribution empirique des valeurs distinctes de `s` (arrondi 1e-10, N=4776) :

| `s` | n | part |
|---|---|---|
| −1.000000 | 925 | 19.4 % |
| **−0.333333** | 993 | 20.8 % |
| **+0.333333** | 1076 | 22.5 % |
| +1.000000 | 1782 | 37.3 % |

**Aucune autre valeur n'existe.** `|1/3| = 0.3333333333 < 0.34` ⇒ les deux états centraux sont
mécaniquement mis à zéro. **L'observation qui motivait l'audit est confirmée.**

---

## 2. LA RÉPONSE ATTENDUE — ce que rapporte l'état « 2 sur 3 »

Rendement directionnel = `sign(état) × rendement du lendemain` (entrée delay+1, cf. §7),
en bps, **au GROSS (`cost_rt = 0`)**. Baseline L58 **appariée à l'état** : espérance
inconditionnelle de la *même forme de trade* (baseline long = +moyenne de r ;
baseline short = −moyenne de r), jamais la moyenne pleine fenêtre du directionnel.

### Groupé (|s| = 1/3), et contraste avec l'unanimité

| Ère | état | N | niveau (bps) | t_HAC | **excès vs baseline appariée** | t_HAC |
|---|---|---|---|---|---|---|
| FULL | **\|s\|=1/3** | 1421 | −0.158 | −0.07 | **+0.004** | **+0.00** |
| FULL | \|s\|=1 | 1811 | +2.066 | +0.86 | +1.207 | +0.50 |
| pré-2021 | **\|s\|=1/3** | 848 | −1.022 | −0.36 | **−0.884** | −0.31 |
| pré-2021 | \|s\|=1 | 1000 | −0.115 | −0.04 | −0.115 | −0.04 |
| post-2021 | **\|s\|=1/3** | 573 | +1.121 | +0.31 | **+1.091** | +0.31 |
| post-2021 | \|s\|=1 | 811 | +4.755 | +1.17 | +1.526 | +0.38 |

### Two-sided, jambes disjointes (FULL)

| état | N | baseline appariée | niveau | t_HAC | excès | t_HAC |
|---|---|---|---|---|---|---|
| **+1/3** (long) | 677 | +3.419 | +2.049 | +0.59 | **−1.370** | −0.39 |
| **−1/3** (short) | 744 | −3.419 | −2.166 | −0.73 | **+1.254** | +0.42 |
| +1 (long) | 1133 | +3.419 | +5.205 | +1.58 | +1.786 | +0.54 |
| −1 (short) | 678 | −3.419 | −3.180 | −0.99 | +0.240 | +0.07 |

**Lecture.** L'état « 2 sur 3 » est un **zéro statistique**, dans les deux ères et sur les deux
jambes séparément. Les deux jambes sont de signes opposés en excès (−1.37 long / +1.25 short) et
s'annulent presque exactement — signature d'un bruit, pas d'un edge amputé.

**La dead-zone ne jette donc PAS la moitié des occasions rentables. Elle jette la moitié des
occasions NULLES.** Le gate est justifié, et il faut le dire.

**Le piège L58 a bien mordu ici** — et dans le sens annoncé. Sur la jambe longue de l'unanimité, le
gradient **en niveau** vaut +5.21 bps ; l'excès **+1.79**. Les deux tiers de l'apparente performance
de la sleeve ne sont que la dérive inconditionnelle de l'or (+3.42 bps/j sur la fenêtre). Toute
lecture en niveau surestime la sleeve d'un facteur ~3.

**Réserve de puissance.** Les états sont très persistants (lookbacks 60/120/250) : N=1421 séances
ne représente qu'une poignée de dizaines d'épisodes indépendants. HAC lag-6 ne corrige pas une
persistance de cette échelle ; les t rapportés sont donc **optimistes**, ce qui ne fait que
renforcer la conclusion « nul » (aucun ne s'approche de 2.5).

---

## 3. Part de temps par état, et coût en séances

| état | n | part | tradé sous θ=0.34 |
|---|---|---|---|
| −1 | 678 | 21.0 % | oui |
| −1/3 | 744 | 23.0 % | **non** |
| +1/3 | 677 | 20.9 % | **non** |
| +1 | 1133 | 35.1 % | oui |

- Dead-zone : **1421 séances = 44.0 % de l'échantillon = 112.1 séances/an bloquées** (span 12.7 ans).
- Tradé : 1811 séances (56.0 %) = 142.9/an.
- **k (facteur de fréquence) = 1.770** en jours d'exposition.

### L'arbitrage fréquence↔EV, chiffré — le cœur économique

Conditionner coûte de la fréquence ; l'EV/temps ne tient que si le gross par jour d'exposition
monte d'un facteur ~k.

| variante | exposition | gross | net | gross / jour d'exposition |
|---|---|---|---|---|
| θ=0.20 (tous états) | 100.0 % (3309 j) | **+3.18 %/an** | +0.71 %/an | +1.264 bps |
| θ=0.34 (unanimité) | 56.5 % (1869 j) | **+3.14 %/an** | **+1.03 %/an** | +2.205 bps |

- Lift requis pour tenir l'EV/temps : **×1.770**
- Lift observé : **×1.745**

**C'est un match à 1.4 % près.** La dead-zone est économiquement **neutre au gross** (−4 bps/an,
soit du bruit) et **positive au net (+32 bps/an)**, gain qui vient *entièrement* de la facture de
portage évitée (**+0.36 %/an de swap+spread économisés**), pas d'alpha.

> **La dead-zone n'est pas un filtre d'alpha, c'est un filtre de COÛT.** Elle retire 44 % des jours
> d'exposition qui ne rapportent rien au gross mais paient le swap plein pot. C'est exactement le
> bon geste — et c'est aussi pourquoi la déverrouiller ne rapporterait rien.

---

## 4. Le seuil est-il sur-ajusté ? — Non, et pour une raison structurelle

| θ | % tradé | SR gross | SR net | ann net | t net | mDD net |
|---|---|---|---|---|---|---|
| 0.00 | 100.0 % | 0.395 | 0.088 | +0.71 % | 0.30 | −33.3 % |
| 0.20 | 100.0 % | 0.395 | 0.088 | +0.71 % | 0.30 | −33.3 % |
| **0.34** | **56.5 %** | **0.390** | **0.128** | **+1.03 %** | **0.45** | **−29.4 %** |
| 0.50 | 56.5 % | 0.390 | 0.128 | +1.03 % | 0.45 | −29.4 % |
| 0.90 | 56.5 % | 0.390 | 0.128 | +1.03 % | 0.45 | −29.4 % |

**La courbe est une fonction en escalier à DEUX paliers**, parce que `s` ne prend que 4 valeurs :
tout θ ∈ [0, 1/3] est identique, tout θ ∈ (1/3, 1] est identique. 0.34, 0.5 et 0.9 donnent
**exactement** le même livre.

Ce n'est donc **ni un optimum étroit ni un drapeau rouge** : c'est un **interrupteur binaire**, et
0.34 n'est que « le plus petit nombre au-dessus de 1/3 ». Le réglage est *arbitraire dans sa forme*
mais **du bon côté de l'interrupteur**, et il n'y a aucun degré de liberté sur-ajusté à déflater.
Un θ=0.5 aurait été plus lisible et strictement équivalent.

---

## 5. L'equity_gate mord-il en plus ? — Oui, et il se cumule

`equity_gate` est bien **GOLD-ONLY** : `eq` est construit sur le `net` de l'or seul
(`engine.py:159-160`), pas sur l'équité du compte. **La mémoire du projet est confirmée.**

- gate = 0.4 sur **55.7 %** des séances ; gate = 1.0 sur 44.3 %.
- Dead-zone (sig=0) sur 43.5 %.

Distribution jointe (% des jours) :

| | gate=1.0 | gate=0.4 |
|---|---|---|
| **tradé** | **38.4 %** | 18.1 % |
| **dead-zone** | 5.9 % | 37.6 % |

Les deux gates sont **fortement corrélés positivement** : 37.6 % de jours doublement bridés contre
24.2 % attendus sous indépendance. Quand la tendance est mixte, la courbe d'équité de l'or est
aussi sous sa MA100 — **ils coupent au même moment, pas à des moments complémentaires**.

- **Exposition pleine : 38.4 % des séances seulement.**
- **Multiplicateur d'exposition effectif E[gate × 1{tradé}] = 0.456** — la sleeve tourne en moyenne
  à **moins de la moitié** de sa taille nominale.

### Pourquoi `ea_w_xauusd = 0` en ce moment

Sur les 70 dernières séances du panel : **sig = 0 sur 40/70**, gate = 0.4 sur seulement **9/70**.
Dernière position non nulle : **2026-04-15**, soit 51 jours calendaires avant la fin du panel.

⇒ **Le poids nul actuel vient de la DEAD-ZONE, pas de l'equity_gate.** Le mécanisme causal
avancé dans le mandat est le bon. C'est son *interprétation économique* qui ne tient pas :
la dead-zone est active parce que la tendance or est réellement mixte, et sur ces jours-là il n'y
a rien à gagner.

---

## 6. La sleeve a-t-elle encore un edge ? — Non, au net

| série | SR | ann | vol | mDD | t_HAC(6) | N |
|---|---|---|---|---|---|---|
| **GROSS** (cost_rt=0) | **+0.390** | +3.14 % | 8.05 % | −26.1 % | +1.35 | 3309 |
| **NET** (1.84 bps + swap) | **+0.128** | +1.03 % | 8.04 % | −29.4 % | **+0.45** | 3309 |
| NET pré-2021 | +0.017 | +0.13 % | | | +0.05 | 1893 |
| NET post-2021 | +0.257 | +2.23 % | | | +0.58 | 1416 |

> **Réconciliation importante : le « SR 0.39 » du checkup de juillet est un chiffre GROSS.**
> Au net des coûts réels la sleeve est à **0.128**. Les deux nombres sont cohérents — mais ils ne
> disent pas la même chose, et c'est le second qui est déployé.

**Décomposition du coût** : gross **+3.14 %/an**, swap **−1.94 %/an**, spread −0.17 %/an.
**Le swap mange 62 % du gross** — confirmation mesurée de L36/L55 sur cette sleeve précise.

**Sensibilité à la dérive des swaps** (XAU long live −76.72 vs ancre −65.68, soit ×1.168,
`spec_bounds_breach = 1`) :

| swap | SR net | ann net |
|---|---|---|
| ×1.000 (ancré) | +0.128 | +1.03 % |
| **×1.168 (live dérivé)** | **+0.091** | **+0.72 %** |

La dérive de 17 % du swap retire à elle seule **29 % du rendement net résiduel**. Le modèle de coût
périmé **surestime** donc la sleeve — mais aucune conclusion de ce rapport ne bascule, parce
qu'elles étaient déjà négatives à l'ancre.

### DSR (`dsr.py` racine, `rf=0`, periods_per_year=252)

Famille de variantes déclarée (θ × eq_gate, n=8), SR ∈ {−0.017 … +0.167} ⇒
`std_sr_trials = 0.2760` (**déclaré**, pas le plancher de bruit).

| n_trials | SR | E[max SR] | **DSR** | passé |
|---|---|---|---|---|
| 1 | +0.128 | +0.000 | **0.678** | non |
| 8 | +0.128 | +0.403 | 0.160 | non |
| 50 | +0.128 | +0.628 | 0.035 | non |
| 321 | +0.128 | +0.805 | 0.007 | non |

**La sleeve échoue le DSR même à n_trials = 1** — c'est-à-dire même sans aucune pénalité de
sélection. Au gross et n_trials=8, DSR = 0.482, toujours sous le seuil.

### Walk-forward (5 folds expanding, NET) — orthogonal au DSR, exigé en plus

| fold | SR | ann |
|---|---|---|
| 2018-10 → 2020-05 | +0.312 | +2.25 % |
| 2020-05 → 2021-11 | −0.241 | −1.95 % |
| 2021-11 → 2023-05 | −0.590 | −4.76 % |
| 2023-05 → 2024-11 | +0.250 | +2.25 % |
| **2024-11 → 2026-06** | **+2.013** | **+19.52 %** |

**3/5 folds positifs = 60 %**, ce qui passe formellement la hard rule (>50 %). Mais **la totalité
du résultat plein échantillon est portée par le dernier fold** — le marché haussier de l'or
2024-2026. Les 4 premiers folds cumulent un SR moyen de −0.07. Le WF « passe » sur une technicalité
de comptage ; l'inspection le contredit. **DSR et WF divergent bien, comme prévu, et il faut lire les DEUX.**

### L38 — orthogonalité au beta

Régression sur un buy-and-hold or vol-targeté (même vol target 10 %, même cap 5×) :

| série | β | t(β) | α | t_HAC(α) | **R²** |
|---|---|---|---|---|---|
| gross | +0.172 | +3.7 | +2.07 %/an | +0.92 | **5.1 %** |
| net | +0.171 | +3.7 | **−0.03 %/an** | −0.02 | **5.0 %** |

**R² = 5.0 % ≪ 30 % ⇒ la sleeve PASSE L38.** Ce n'est pas du timing de beta déguisé, et il faut le
créditer : c'est un vrai signal de tendance, structurellement décorrélé du sous-jacent.

Mais l'α net est **−0.03 %/an, t −0.02** : orthogonale et vide. Et le comparateur est cruel —
le simple **buy-and-hold or vol-targeté fait SR +0.589** contre +0.128 pour la sleeve. La sleeve
détruit du rendement par rapport à détenir l'actif (ce qui n'est pas un véhicule FTMO viable pour
autant : le swap et le DD d'un long permanent l'excluent — c'est un repère, pas une alternative).

---

## 7. Contrôles de mesure

- **L59 (delay+1 entrée ET sortie)** — **non liant ici, et c'est vérifié, pas supposé.** La sleeve
  n'a **ni stop-entry ni bracket exit** : c'est une position vol-targetée décidée au close t−1
  (`.shift(1)`) et tenue sur t. Entrée et sortie sont le *même objet de prix* (le close daily), donc
  l'asymétrie de remplissage au stop qui a fait passer SR 0.99 → 0.49 ailleurs n'a pas de prise.
  Le coût est facturé sur |Δposition| à demi-RT par côté, ce qui est la bonne géométrie pour une
  position rebalancée en continu.
- **L60 (barres à fourchette nulle)** — XAUUSD daily, par année : **0.0 % de barres à rendement nul
  sur 15 des 20 années**, maximum **1.18 % (2018)**, zéro sur 2021-2026. Rien à voir avec la
  pathologie XPT/XPD (61-69 % de barres mortes). **La série est saine, l'edge n'est pas un artefact
  de prints de règlement.**
- **Bootstrap par blocs** (stationnaire, mean_block=10) partout ; aucun iid.
- **Coûts** : XAUUSD RT = **1.8389 bps** (`phase0_rt_cost_bps.csv`), conforme au 1.84 du COST_AUDIT.
  Swap **asymétrique** appliqué par signe de position (`sL` si long, `sS` si short), avec le
  multiplicateur de jour triple — **pas** un −2.9 symétrique.
- **Pas de double comptage du carry** : le swap long entre dans le signal (momentum sur total return
  carry-ajusté, `engine.py:137`) *et* dans le P&L par la jambe tenue — ce sont deux usages distincts
  et corrects, vérifiés dans le code.
- Données : panels `cache/` dérivés de `deep_history_utc` ; **jamais** `data/panels/m5_indices/`.

---

## 8. Métrique de décision — p(pass), durée, EV/temps

Barrières FTMO 2-step via `Portfolio/admission/barrier.py` (importé, non modifié) :
target 10 %/5 %, daily −5 %, **floor STATIQUE −10 %**, **horizon 182 j**, 4000 chemins,
bootstrap stationnaire mean_block=10, **graines appariées**.
**Placebo à autocorrélation appariée** = décalage circulaire + démoyennage exact
(moyenne strictement nulle, persistance et vol préservées), 5 décalages.

### Sleeve seule, θ=0.34 vs θ=0.20

| scale | p(pass) θ=0.34 | p(pass) θ=0.20 | Δ | **placebo moy.** | placebo max | jours méd. | échec floor | échec daily |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 0.1540 | 0.1492 | −0.0048 | **0.1278** | 0.1345 | 144.5 | 0.182 | 0.046 |
| 2.0 | 0.2580 | 0.2530 | −0.0050 | **0.2381** | 0.2455 | 74.0 | 0.347 | 0.319 |
| 3.0 | 0.1958 | 0.2125 | +0.0167 | **0.1914** | 0.2035 | 40.0 | 0.139 | 0.659 |

Deux lectures, toutes deux importantes :

1. **Δ(déverrouiller la dead-zone) ∈ [−0.005, +0.017]**, sans signe stable, et **très en-dessous de
   la dispersion du placebo**. Rouvrir les états « 2 sur 3 » **ne rachète pas de p(pass)**.
2. Plus dur : à scale 1, une série **strictement de moyenne nulle** mais persistante atteint déjà
   **p = 0.128** contre 0.154 pour la sleeve réelle. **La sleeve n'apporte que ~2.6 points de
   p(pass) au-dessus du bruit pur.** C'est le rappel exact du piège Δp = +0.1495.
3. Échecs **floor-dominés** à scale 1 (0.182 floor contre 0.046 daily) — cohérent avec le profil
   FLOOR-DOMINATED du livre.

### Niveau LIVRE — la vraie question MONO

Livre proxy = J1 + overnight (colonnes déployées de `phase1c_sleeves.parquet`), pondération ERC,
**re-levier à volatilité égale** pour que la comparaison porte sur la diversification et non sur le
risque pris.

Flatness et corrélations : gold(déployé) flat **68.5 %**, J1 flat 45.6 % (SR +0.492),
overnight flat 45.9 % (SR +0.583). **Le livre sans or est flat 35.1 % des jours** ; l'or est actif
pendant ces trous **21.8 %** du temps à θ=0.34, **34.6 %** à θ=0.20.
**ρ(or, reste du livre) = +0.048** — l'or est *réellement* décorrélé, et c'est son meilleur argument.

| scale | livre | p(pass) | Δ vs MONO | jours méd. |
|---|---|---|---|---|
| 1.0 | **MONO (J1+ON, sans or)** | **0.3690** | — | 170 |
| 1.0 | + or θ=0.34 (LIVE) | 0.3317 | **−0.0373** | 167 |
| 1.0 | + or θ=0.20 | 0.3287 | −0.0403 | 165 |
| 1.0 | + PLACEBO (moyenne nulle, AC appariée) | 0.3148 | −0.0542 | — |
| 2.0 | MONO | 0.4873 | — | 86 |
| 2.0 | + or θ=0.34 | 0.4445 | −0.0428 | 85 |
| 2.0 | + or θ=0.20 | 0.4462 | −0.0410 | 82 |
| 2.0 | + PLACEBO | 0.4289 | −0.0584 | — |
| 3.0 | MONO | 0.3855 | — | 48 |
| 3.0 | + or θ=0.34 | 0.3450 | −0.0405 | 44 |
| 3.0 | + or θ=0.20 | 0.3513 | −0.0343 | 44 |
| 3.0 | + PLACEBO | 0.3457 | −0.0398 | — |

### Critère d'admission du projet (ΔSR au poids ERC, block-bootstrap 2000 tirages)

SR livre MONO (J1+ON, ERC) = **+0.990**

| ajout | SR livre | **ΔSR** | IC95 | verdict |
|---|---|---|---|---|
| or θ=0.34 (LIVE) | +0.856 | **−0.134** | [−0.479, +0.233] | **non significatif / dilutif** |
| or θ=0.20 | +0.839 | −0.152 | [−0.504, +0.231] | non significatif / dilutif |

**Dans cette reconstruction, l'or n'est pas un diversifieur accrétif : il est dilutif.** À poids ERC
il reçoit un tiers du budget de risque pour un SR net de 0.128 face à 0.49 et 0.58 — la
décorrélation (ρ=0.05) ne suffit pas à compenser l'absence de rendement. Il fait mieux que le
placebo (−3.7 pt contre −5.4 pt), donc **il contient quelque chose** ; simplement pas assez pour
payer son tiers de budget.

**Conséquence pour le diagnostic MONO : la dead-zone n'est pas la cause de la perte la plus coûteuse
du projet.** Réarmer les états « 2 sur 3 » remettrait l'or au travail 44 % de jours en plus et
changerait p(pass) de ~0.000. Le symptôme (`ea_w_xauusd = 0`) disparaîtrait sans que la valeur
n'apparaisse.

---

## 9. Ce que ça ne prouve PAS — limites à lire avant toute décision

1. **Réconciliation incomplète avec le livre déployé.** Ma reconstruction corrèle **0.55** avec la
   colonne `gold` de `phase1c_sleeves.parquet` (n=1949 jours d'exposition commune) — pas l'identité.
   Les deux ont un SR quasi identique (0.388 déployé vs 0.390 gross), mais la colonne déployée est
   flat 68.5 % contre 43.5 % pour la mienne : vintage, vol target ou traitement de coût différents.
   **Les niveaux absolus de §8 sont donc indicatifs ; les COMPARAISONS θ=0.34 vs θ=0.20 restent
   valides** (mêmes séries, mêmes graines, différence appariée).
2. **Je n'ai PAS reproduit le moteur de chemin v2.2/v2.8** (vm=14, cap de marge 60 %, breaker daily,
   micro-ORB, quantisation de lots, horaires CET). Mon p(pass) est un proxy ERC vol-normalisé.
   **Je ne peux donc ni confirmer ni réfuter le 80.3 % → 53.7 %** du desk audit. Ce que je montre est
   plus étroit et plus robuste : *à risque égal, réarmer la dead-zone ne récupère pas de p(pass)*.
3. **Panel périmé de ~2 mois** : il s'arrête au **2026-06-05**, on est le 2026-08-04. Le « flat depuis
   38-60 séances » déborde de mes données ; je constate la dernière position non nulle au 2026-04-15.
4. **Puissance faible partout.** Aucun t ne dépasse 1.6 ; les IC95 de ΔSR contiennent zéro des deux
   côtés. Le verdict honnête sur l'état « 2 sur 3 » est **NUL AU SENS UNDERPOWERED**, pas
   « prouvé égal à zéro » — mais la charge de la preuve est du côté de qui veut le rouvrir.
5. **Le livre proxy n'est pas le livre déployé** : les colonnes J1/overnight de `phase1c` peuvent
   dater d'un vintage antérieur à v2.8, et la pondération réelle n'est pas ERC (leg caps fixes + vm).
   Il reste possible que l'or soit accrétif **sous la pondération déployée** ; ce n'est pas testé ici.
6. Le rejet porte sur **cette spec** (blend de signes à 3 horizons sur or). Il ne ferme pas la
   famille « tendance or » : un kill de nature **coût** (le swap mange 62 % du gross) est
   **ROUVRABLE** au sens de la politique de ré-ouverture — sur un véhicule moins cher que le CFD
   FTMO, pas en re-mining le même seuil.

---

## 10. Conclusion et suite

**Sur la question posée : la dead-zone à 0.34 est correctement calibrée, pour une raison que
personne n'avait écrite.** Ce n'est pas un filtre de tendance — c'est un filtre de portage. Elle
retire 44 % de jours d'exposition dont le gross est nul (+0.004 bps d'excès, t 0.00) et dont le
swap est plein. L'arbitrage fréquence/EV tombe à 1.4 % près (lift requis ×1.770, observé ×1.745) et
le solde net est **+32 bps/an en faveur du gate**. Et comme `s` n'a que 4 valeurs, θ=0.34/0.5/0.9
sont le *même* livre : il n'y a pas d'optimum étroit à dénoncer.

**Aucune modification de spec n'est recommandée.** Les chiffres ne la portent pas : Δp(pass)
∈ [−0.005, +0.017], sous le placebo ; ΔSR livre −0.13 à −0.15, IC contenant zéro. Toucher au seuil
coûterait un cycle de gel complet (chaîne de spec, re-pin `ea_targets`, fenêtre du **samedi**, cf. le
piège de restamp-lundi) pour un gain mesuré nul et un risque opérationnel non nul — sur un compte
en challenge à 723 $ de son plancher.

**Le vrai résultat de cet audit est ailleurs, et il est plus grave que la question posée.** La
sleeve or **n'a plus d'edge net** : SR 0.128 (0.091 aux swaps live dérivés), t_HAC 0.45, DSR 0.678
**même à n_trials=1**, α net −0.03 %/an, walk-forward porté en totalité par le dernier fold. Elle
passe L38 (R² 5 %, vraie décorrélation) mais elle est **dilutive à poids ERC**. Le livre est MONO
non parce qu'un seuil est mal réglé, mais parce que **la seule sleeve capable de le dé-monofier ne
gagne plus d'argent après le swap**.

Les deux pistes que ces chiffres soutiennent, par ordre de valeur — **à instruire, pas à appliquer** :
1. **Le poids, pas le seuil.** Si l'or reste au livre pour sa décorrélation (ρ=0.05), il ne devrait
   pas porter un tiers du budget de risque à SR 0.128. À tester sous la pondération réellement
   déployée, pas sous ERC.
2. **Le véhicule.** Le swap FTMO consomme 62 % du gross et a dérivé de 17 % hors ancre. Un kill de
   nature *coût* est rouvrable : l'or sur un véhicule futures (~0.4 bps RT, pas de swap CFD)
   change le gate d'un ordre de grandeur — mais L53 s'applique d'abord (matrice de véhicule AVANT
   le backtest, et le test « la marge du lot minimum tient-elle dans le capital perso ? »).

Compteur d'essais : **7 essais** dans ce dossier (états 2-sur-3 groupé + 2 jambes séparées,
balayage θ à 5 points comptant pour 2 configurations distinctes, variantes eq_gate) — à réconcilier
au ledger `_meta/n_tests_ledger.md` à la clôture, pas ici.

---

### Reproductibilité

Scripts d'analyse (scratchpad de session, hors repo — **aucun blob data commité**) :
`s1_states.py` (pondération, distribution, rendement par état), `s2_sleeve.py` (gate, edge, θ,
L38, WF), `s3_decide.py` (DSR, p(pass) sleeve, placebo, économie de fréquence),
`s4_book.py` / `s5_dsr_book.py` (livre, ΔSR block-bootstrap).
Tout est re-dérivable de `cleanroom/engine.py:build_signals` + les panels `cache/` en lecture seule.
