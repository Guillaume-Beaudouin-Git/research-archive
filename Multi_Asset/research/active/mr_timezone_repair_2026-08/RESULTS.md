# MR timezone repair — and the first test of the index closing window

**Date :** 2026-08-01 · **Branche :** `claude/mr-timezone-repair` (worktree dédié, base `main` @ `9ee59dc0`)
**Interpréteur :** `/usr/bin/python3` (pandas 2.2.3 / numpy 2.0.2 vérifiés au lancement)
**Données :** `data/deep_history_utc/{US500,US100,US30,GER40}_M1.csv` — vrai UTC vérifié, lues en
**LECTURE SEULE** depuis le répertoire principal. Les panels `data/panels/m5_indices/*` (buggés) ne
sont utilisés nulle part, sauf pour re-vérifier le diagnostic de fuseau.
**Gate :** au **GROSS, `cost_rt = 0`**. Coût seulement en aval, à **1.8 bps RT** indices
(`Multi_Asset/research/active/cost_denominator_2026-07/COST_AUDIT.md`) — **jamais** la colonne `spread`.
**Cellules mesurées : 579** (détail §6). La réparation elle-même est **N0** ; aucun survivant n'est promu.

---

## Verdicts en une page

| # | Question | Verdict |
|---|---|---|
| V1 | **B1 — pression de clôture de l'INDICE et sa réversion** (le seul mécanisme neuf de la revue) | **REJECTED** sur les 3 indices US : le signe est **inverse** (continuation, pas réversion), significativement. **REJECTED** sur GER40 : l'effet existe au gross (3.52 bps, t 3.68) mais **vit entièrement dans les 5 minutes de l'auction Xetra** et meurt sur un retard d'entrée de 5 min (0.56 bps, t 1.00, sous le coût). |
| V2 | **Cellules MR de `mr_deepdive` re-passées sur la vraie fenêtre RTH** | **REJECTED** — 384 cellules, gross two-sided moyen **−1.78 bps** (session entière) / **−0.91 bps** (zone jamais testée), **0 cellule à t > 2.5**, **46 à t < −2.5**, **0 survivant L25+L58**. |
| V3 | Le bug de fuseau lui-même | **CONFIRMÉ au tick, indépendamment** — le panel est EET/EEST, pas UTC (§1). |
| V4 | Ancrage horloge d'échange (L56) | **CONFIRMÉ** sur les 4 indices : corr profil horaire hiver~été **0.97-0.99 en horloge d'échange** contre **0.70-0.79 en UTC**. |

**Ce que ça ferme :** le dernier mécanisme neuf de `literature_review_2026-08` (B1) est fermé **au niveau
indice, sur véhicule CFD FTMO**, et il est fermé **au gross** — donc ni le modèle de coût, ni la colonne
`spread`, ni les swaps ne peuvent le rouvrir. La fermeture indices-MR de `intraday_mr_ftmo` est
**confirmée sur la fenêtre horaire correcte**, ce qui lui manquait.

---

## 1. Le défaut, re-vérifié indépendamment (N0)

Diagnostic du mandat : `mr_deepdive.py` lit `data/panels/m5_indices/*` dont la colonne s'appelle
`timestamp_utc` mais qui est en EET/EEST, et fait `tz_localize("UTC")`.

Contrôle indépendant, par **appariement de prix** contre `deep_history_utc` (vrai UTC), US500,
janvier-février 2023, 54 875 barres M1 :

| décalage appliqué au panel | barres appariées | médiane \|diff\| (points d'indice) |
|---|--:|--:|
| **−2 h** | **54 875** | **0.0001** |
| −1 h / −3 h | 51 954 | 3.60 |
| 0 h | 50 795 | 5.40 |
| +8 h | 46 631 | 14.11 |

⇒ le panel est **UTC+2 en janvier** = **EET**. Diagnostic **confirmé au tick**, pas par inférence.
Le décalage effectif contre l'horloge de New York est de 7 h, comme annoncé. `mr_deepdive.py`
n'est **pas** ré-exécuté ici ; il est remplacé.

## 2. Hygiène de données, avant tout usage

### L60 — part de barres à fourchette nulle (`high == low`), par série et par année

Série **entière** (24 h, donc gonflée par les heures creuses de nuit) :

| série | pire année | valeur | 2022-2026 (min-max) |
|---|---|--:|---|
| US500 | 2014 | **12.64 %** | 0.20 - 3.54 % |
| US100 | 2014 | 5.34 % | 0.00 - 0.01 % |
| US30 | 2014 | 4.88 % | 0.04 - 0.26 % |
| GER40 | 2013 | 11.76 % | 0.70 - 1.85 % |

Le chiffre qui décide est celui **dans la fenêtre utilisée** (clôture−30 → clôture+10) :

| série | moyenne | pire année | pire année **≥ 2018** |
|---|--:|---|--:|
| US500 | 1.60 % | 10.82 % (2014) | **1.87 %** |
| US100 | 0.20 % | 1.21 % (2013) | 0.01 % |
| US30 | 0.16 % | 2.16 % (2013) | 0.19 % |
| GER40 | 0.08 % | 2.52 % (2013) | 0.18 % |

**Aucun syndrome XPT/XPD** (à comparer aux 61-69 % de XPTUSD/XPDUSD). L'échantillon B1 des indices
US commence en 2018 (§ disponibilité), donc au-dessous de 1.9 % partout. Contrôle refait minute par
minute autour de la clôture : GER40 **0.00-0.16 %** sur 17:20-18:10 Berlin, avec des fourchettes de
barre normales (4-7 bps) et **aucune discontinuité** au passage de 17:30 — la série GER40 est
réellement cotée pendant l'auction, ce n'est pas un print figé. US500 post-clôture : 0.2 % → 5.8 % à
16:15 ET, avec effondrement de la fourchette (9.2 → 2.7 bps) — fenêtre **mince**, signalée comme telle
(et raison pour laquelle la tenue US est plafonnée à 10 min).

### Colonne `spread` — non utilisée, et voici pourquoi

Part de barres à spread **nul**, mesurée ici : **US30 79.7 % / 100.0 % / 74.9 % en 2019/2020/2021**
(confirme la revue, et contredit « indices plutôt propres » de `CLAUDE.md`), GER40 15-40 % sur
2013-2017, US500 4.8 % en 2021. **Aucun coût de ce rapport ne vient de cette colonne.**

### Disponibilité des barres post-clôture — la contrainte qui cadre le test B1

Fraction des séances (ayant une barre à clôture−5) qui possèdent une barre à clôture+k :

| série | période | +0 | +10 | +15 | +30 | +59 |
|---|---|--:|--:|--:|--:|--:|
| US500 | 2013-2017 | 0.86 | 0.36 | 0.10 | 0.33 | 0.29 |
| US500 | **2018-2026** | 0.97 | **0.96** | 0.56 | 0.54 | 0.04 |
| US100 | 2018-2026 | 0.97 | 0.97 | 0.56 | 0.56 | 0.04 |
| US30 | 2018-2026 | 0.95 | 0.94 | 0.82 | 0.82 | 0.29 |
| **GER40** | **2014-2026** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** |

⇒ **US : échantillon B1 restreint à 2018-2026 et à une tenue ≤ 10 min.** Avant 2018 le CFD US ne
cote pas après la clôture cash — il n'y a rien à tester, pas un résultat nul.
⇒ **GER40 : couverture intégrale 2014-2026, à tous les horizons.** C'est le véhicule propre pour B1.

### L56 — test de falsification d'horloge (gratuit, fait avant toute mesure de performance)

Corrélation du profil horaire de |rendement M1| entre **hiver (déc-fév)** et **été (juin-août)** :

| série | horloge d'ÉCHANGE | UTC fixe |
|---|--:|--:|
| US500 | **0.988** | 0.766 |
| US100 | **0.991** | 0.785 |
| US30 | **0.985** | 0.739 |
| GER40 | **0.971** | 0.703 |

L'effet de session est **ancré à l'horloge de l'échange**. Toutes les fenêtres de ce rapport sont
définies en `America/New_York` (US) et `Europe/Berlin` (GER40), **avec leur DST propre**.

---

## 3. LA CIBLE PRIORITAIRE — B1, la fenêtre de clôture au niveau indice

**Mécanisme testé** (Baltussen, Da & Soebhag, SSRN 5039009) : la concentration du volume
institutionnel dans l'auction de clôture crée une pression de prix non informative qui se dénoue.
**Amplitude publiée : 0.24 %/jour — mais en coupe transverse d'actions US**, long-short décile.
A priori explicite avant mesure, conforme au mandat : **au niveau indice la pression idiosyncratique
se compense largement ; attendre très en dessous de 24 bps, possiblement zéro.**

**Forme de trade, pré-spécifiée :**
- signal = rendement des **K dernières minutes de la séance cash** (K ∈ {15, 30, 60}), z-scoré sur
  une fenêtre glissante **strictement passée** de 250 séances ;
- jambes **DISJOINTES** (L25) : `z > +θ` → **SHORT** (fade la pression haussière), `z < −θ` → **LONG**.
  Aucune jambe n'est jamais obtenue par négation de l'autre ;
- **L59 sur l'entrée ET la sortie** : entrée à l'**OPEN** de la barre **une barre pleine après** la
  barre de signal ; sortie à l'**OPEN** d'une barre ultérieure. **Aucun stop, aucun bracket, aucun
  remplissage à une barrière** — le mode de défaillance L59 est structurellement absent ;
- tenues : +10 / +30 / +60 min après clôture, **overnight jusqu'à l'ouverture cash suivante**, et
  30 premières minutes du lendemain ;
- **L58** : chaque jambe est comparée à l'**espérance INCONDITIONNELLE de la même forme de trade sur
  la même fenêtre** ; le bootstrap de la différence ré-échantillonne le panneau **conjointement** ;
- bootstrap **par blocs circulaires** (Politis-Romano, L = 5 séances, 2 000 tirages), t **HAC(6)**.

**Grille : 153 cellules** (4 instruments × 3 K × 5 fenêtres de tenue × 3 θ, moins celles à N < 25/jambe).

### 3.1 Indices US — le signe est INVERSE. B1 REJECTED.

Sur la fenêtre 0-10 min après la clôture cash, **le fade PERD**, significativement :

| cellule | n_L / m_L (t) | n_S / m_S (t) | two-sided m (t) | boot p | inconditionnel (t) | exL p / exS p |
|---|---|---|---|--:|---|---|
| US100 sig30 H10 θ1.0 | 188 / −2.87 (−1.93) | 200 / −3.69 (−2.06) | **−3.29 (−2.77)** | 0.003 | −0.03 (−0.07) | 0.074 / **0.017** |
| US100 sig15 H10 θ1.5 | 86 / −5.31 (−1.95) | 87 / −4.79 (−1.65) | **−5.05 (−2.50)** | 0.007 | −0.03 (−0.07) | 0.051 / 0.100 |
| US100 sig60 H10 θ1.5 | 101 / −5.29 (−2.26) | 85 / −3.36 (−1.51) | **−4.41 (−2.62)** | 0.004 | −0.03 (−0.07) | **0.022** / 0.243 |
| US500 sig15 H10 θ0.5 | 451 / −1.81 (−2.74) | 421 / −1.15 (−1.43) | **−1.49 (−2.88)** | 0.004 | +0.23 (0.95) | **0.000** / 0.182 |
| US30 sig15 H10 θ1.0 | 185 / −2.25 (−1.47) | 202 / −2.12 (−1.96) | **−2.18 (−2.36)** | 0.008 | +0.18 (0.88) | **0.024** / **0.035** |

Les **deux** jambes sont négatives et **les deux** restent négatives après retrait de
l'inconditionnel ⇒ ce n'est pas un artefact de baseline (L58 est satisfaite dans le mauvais sens
pour B1). **La pression de clôture CONTINUE sur les indices US, elle ne se renverse pas.**

> **Ce que je ne revendique PAS :** ce signe de continuation a été **trouvé, pas pré-enregistré**.
> Le retourner en « edge momentum de clôture » serait une recherche de signe post-hoc. Il est
> rapporté comme **falsification de B1**, rien de plus. Toute exploitation exigerait une
> pré-inscription **N2** indépendante, avec sa propre kill rule.

**Fenêtres overnight — le piège beta L25/L58, exactement celui qui avait tué `intraday_mr_ftmo`.**
Le drift inconditionnel de clôture→ouverture est **massif** (US500 +4.67 bps t 3.12 ; US100 +6.08
t 3.43 ; GER40 +3.17 t 2.44). Aucune jambe conditionnelle ne le bat de façon significative. La
cellule la plus « spectaculaire » du tableau — US500 sig60 HON θ1.5, m_both **+22.7 bps, t 2.36** —
a **exL p 0.073 / exS p 0.089** sur n = 97/87 et **5 années positives sur 9** :
**UNDERPOWERED, pas PASS.** C'est du drift overnight acheté au hasard du conditionnement, et
c'est précisément la lecture que L58 impose.

### 3.2 GER40 — l'effet EXISTE au gross, et meurt à l'exécution

Clôture Xetra 17:30 Berlin. C'est la seule série qui cote intégralement après.

**Meilleure cellule, sig30 / tenue 10 min :**

| θ | n_L / m_L (t) | n_S / m_S (t) | two-sided m (t) | boot p | inconditionnel | exL (p) | exS (p) | années + |
|--:|---|---|---|--:|--:|---|---|--:|
| 0.5 | 732 / +0.98 (1.75) | 805 / +0.74 (1.40) | +0.85 (2.22) | 0.027 | −0.13 | +1.11 (0.025) | +0.61 (0.198) | 10/13 |
| 1.0 | 365 / +2.06 (2.29) | 350 / +1.68 (1.83) | +1.87 (2.92) | 0.005 | −0.13 | +2.18 (0.011) | +1.55 (0.105) | 11/13 |
| **1.5** | 194 / **+4.03 (3.62)** | 153 / **+2.88 (1.77)** | **+3.52 (3.68)** | **0.000** | −0.13 | **+4.15 (0.000)** | +2.75 (0.089) | **12/13** |

Monotone en θ, les deux jambes du bon signe, baseline inconditionnelle **nulle** (−0.13, t −0.56)
donc L58 ne mord pas, 12 années positives sur 13. **C'est un vrai signal au gross.** Il fallait donc
essayer de le tuer.

### 3.3 Batterie de falsification du candidat GER40

**A. Placebo temporel — la même forme de trade ancrée toutes les 30 minutes (29 ancres, θ 1.0).**
17:30 arrive **1ᵉʳ sur 29** (m_both 1.871), au-dessus du **p95 des 28 ancres non-clôture (1.225)** et
au-dessus du meilleur placebo (1.439 à 20:30). **Le placebo NE tue PAS le candidat.**
Réserve honnête : **4 ancres sur 29 ont t > 2.0** contre **0.7 attendues** — la famille d'ancres est
plus bruyante qu'un tirage iid, et 18:30 (t 2.48) / 20:30 (t 2.50) sont du même ordre. L'ancre de
clôture est la meilleure, pas la seule.

**B. Décomposition de l'auction — c'est ici que ça meurt.**
L'auction de clôture Xetra court de 17:30 à ~17:35.

| segment | m_both | t | boot p | inconditionnel (t) |
|---|--:|--:|--:|---|
| 17:31 → 17:36 (**dans l'auction**) | +1.13 | 2.29 | 0.032 | −0.56 (−2.87) |
| 17:36 → 17:41 (après l'auction) | +0.74 | 1.80 | 0.088 | +0.46 (3.33) |
| 17:31 → 17:41 (fenêtre complète) | +1.87 | 2.99 | 0.002 | −0.11 (−0.47) |
| **17:36 → 17:46 (entrée APRÈS l'auction)** | **+0.56** | **1.00** | **0.320** | +0.38 (2.02) |
| 17:41 → 17:51 (entrée +10 min plus tard) | −0.14 | −0.27 | 0.814 | −0.13 (−0.72) |

**60 % de l'effet est à l'intérieur de l'auction**, et la demi-vie du reste se compte en minutes :
retarder l'entrée de **cinq minutes** — le genre de retard qu'impose n'importe quelle contrainte
d'exécution réelle — laisse **0.56 bps, t 1.00, non significatif et SOUS le coût mesuré de 1.8 bps
RT**. Dix minutes de retard : **négatif**.
Noter aussi les **drifts inconditionnels significatifs** des sous-fenêtres (−0.56 puis +0.46, |t| ≈ 3)
qui s'annulent sur la fenêtre complète : la micro-structure de ces cinq minutes est **structurée**,
et c'est précisément la structure qu'on ne peut pas prendre de l'extérieur.

**C. Stabilité de sous-période — l'effet n'est PAS mort, et ce n'est pas la bonne excuse.**

| θ | 2014-2019 | 2020-2026 | 2014-2026 |
|--:|---|---|---|
| 1.0 | +1.85 (t 2.60) | +1.92 (t 1.96) | +1.87 (t 2.92) |
| 1.5 | +3.89 (t 3.39) | +3.82 (t 2.48) | +3.52 (t 3.68) |

Remarquablement stable. **Le kill n'est pas « ça a décayé » — c'est « c'est dans l'auction et c'est
trop petit ».**

**D. Test d'horloge (L56) — INCONCLUANT ici, et il faut le dire.**
UTC 16:30 fixe donne t 2.81, contre 2.99 en horloge d'échange. Contrairement au cas de l'or
(0.70/0.86 ET vs 0.04/0.20 UTC), l'écart Berlin−UTC n'est que de 1-2 h et **18:30 est elle-même une
ancre bruyamment positive** : le test ne sépare pas. Il **ne confirme ni n'infirme** l'ancrage pour
cette cellule précise. (L'ancrage à l'horloge d'échange reste établi au niveau du profil de
volatilité, §2.)

**E. Concentration et queue.**

| θ | n | m (bps) | sd | skew | WR | top 1 % du P&L | top 5 % du P&L | m sans le top 5 % |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 1.0 | 732 | 1.87 | 17.25 | 0.11 | 0.557 | 35.9 % | 114.7 % | **−0.29** |
| 1.5 | 354 | 3.38 | 19.79 | 0.07 | 0.599 | 19.7 % | 74.5 % | **+0.90** |

À θ = 1.5, **retirer les 5 % de meilleurs trades (≈ 18 trades sur 13 ans) laisse 0.90 bps, sous le
coût de 1.8 bps.** À θ = 1.0 le retrait rend la sleeve **négative**. Tout le net est porté par une
poignée de séances.

**Économie, au coût mesuré (1.8 bps RT, pas 2.2, pas 3, pas la colonne `spread`) :**

| θ | trades/an | gross bps/an | SR gross (√trades/an, L47) | net bps/an | SR net |
|--:|--:|--:|--:|--:|--:|
| 1.0 | 56.3 | 105.3 | 0.81 | **4.0** | **0.03** |
| 1.5 | 27.2 | 92.0 | 0.89 | **42.9** | **0.42** |

### 3.4 Métrique de décision — p(pass) 2 phases et durée, pas le Sharpe

`Portfolio/admission/barrier.py`, barrières FTMO : daily **−5 %** sur l'équité intraday, floor
**STATIQUE −10 %** du capital initial, **aucune limite de temps**. 3 000 chemins, bootstrap
stationnaire par blocs (bloc moyen 10 j). Sleeve GER40 θ1.5 **nette à 1.8 bps** :
3 115 séances, **88.6 % de jours FLAT**, rendement annuel +0.45 %, SR daily 0.43, pire jour −0.87 %.

| vm | p(pass) | durée médiane (j) | p_floor | p_daily | p_timeout |
|--:|--:|--:|--:|--:|--:|
| 1 | 0.000 | — | 0.000 | 0.000 | 1.000 |
| 10 | 0.240 | 216 | 0.088 | 0.156 | 0.516 |
| **20** | **0.255** | **139** | 0.056 | 0.633 | 0.056 |
| 40 | 0.106 | 91 | 0.007 | 0.886 | 0.001 |

Plafond **25.5 %** à vm 20, pour une durée médiane de **139 jours** et 63 % de morts par barrière
journalière. À comparer au livre déployé (~53.7 % single). **Ce n'est pas un véhicule de challenge.**
Et comme diversifieur remplisseur-de-jours-flat, il faudrait d'abord que l'edge survive à
l'exécution — §3.3 B dit non.

### 3.5 Verdict B1

**REJECTED.**
- **US500 / US100 / US30 : signe inverse**, significatif, sur les deux jambes, après retrait de
  l'inconditionnel. La pression de clôture continue au lieu de se renverser.
- **GER40 : effet gross réel (3.52 bps, t 3.68, 12/13 années, stable sur les deux moitiés) mais
  confiné à l'auction** — il ne survit pas à un retard d'entrée de 5 minutes (0.56 bps, t 1.00,
  p 0.32, sous les 1.8 bps de coût), et 74.5 % de son P&L net tient dans 5 % des trades.
  p(pass) plafonne à 25.5 % / 139 jours.

**Le dernier mécanisme neuf de `literature_review_2026-08` est donc fermé au niveau indice sur
véhicule CFD FTMO — et fermé au GROSS**, ce qui rend le verdict immune au modèle de coût.

---

## 4. Les cellules MR ré-passées sur la zone jamais testée

Même grille que `mr_deepdive.py` (logiques `sma20_z`, `ema20_z`, `vwap_z`, `rsi14`, `range_fade` ;
θ d'origine ; sorties `ts` half-life-matched et `mt` mean-touch ; TF 5/15/30 min), mais :
horloge d'échange DST-correcte, `deep_history_utc`, **`cost_rt = 0`**, **delay+1 sur l'entrée ET la
sortie** (les deux sont des OPEN de barres ultérieures ; aucun stop, aucun bracket ⇒ pas de
remplissage à une barrière), **jambes disjointes**, et baseline **L58 appariée en DURÉE** (moyenne
inconditionnelle du même horizon de tenue sur toutes les barres).

Trois portées :
- **FULL** = vraie séance cash entière ;
- **CLOSE** = les 90 dernières minutes seulement (ancres calculées dedans) ;
- **CLOSE_ENTRY** = ancres sur la séance entière, **entrées restreintes aux 90 dernières minutes** —
  c'est la version honnête de « la zone que le bug n'a jamais visitée ».

| portée | cellules | m two-sided moyen | m > 0 | t > 2.5 | t < −2.5 | survivants L25+L58 (2 jambes > 0, 2 jambes > inconditionnel, t > 2.0) |
|---|--:|--:|--:|--:|--:|--:|
| FULL | 176 | **−1.78 bps** | 16 | **0** | 46 | **0** |
| CLOSE | 48 | −1.72 bps | 14 | **0** | 18 | **0** |
| **CLOSE_ENTRY** | 160 | **−0.91 bps** | 19 | **0** | 10 | **1 (nominal)** |

**Le survivant nominal, et pourquoi il n'en est pas un :**
`GER40 · 5m · sma20_z · θ 2.5 · exit ts` — m_both +1.75 bps, t 2.18, boot p 0.028, n 992.
Jambes : **long +0.45 bps (t 0.40, n 549)** / short +3.35 bps (t 3.08, n 443).
⇒ **c'est une sleeve one-sided en substance : L25 n'est pas honorée.** Et sur 384 cellules, le seuil
Šidák à 5 % est **p < 1.3 × 10⁻⁴** ; p = 0.028 en est à plus de deux ordres de grandeur.
**REJECTED.**

**Limite à déclarer :** la portée **CLOSE** est **sous-peuplée par construction** (48 cellules au lieu
de 240) — une ancre de 20 barres ne tient pas dans une fenêtre de 90 minutes en 15/30 min, donc
`sma20_z`/`ema20_z`/`vwap_z`/`rsi14` y disparaissent. C'est exactement pourquoi **CLOSE_ENTRY**
existe et c'est elle qui porte la conclusion sur la zone jamais testée.

**Verdict V2 : REJECTED.** La zone que le bug avait rendue invisible ne contient pas d'edge MR
prix-seul. Le résultat est **concordant** avec `intraday_mr_ftmo` (index book gross SR −0.34) et avec
la lecture mécanique de la revue (Nagel B4 : la MR court terme **est** la rémunération de la
fourniture de liquidité ; Bouchaud B5 : le propagateur est calibré pour annuler la prévisibilité).
La différence est que **cette fois la fenêtre horaire est la bonne**.

---

## 5. Statut du « 0/344 »

`mr_deepdive` mesurait sur une fenêtre fausse ; sa conclusion (« MR intraday indices : rien ») est
**re-établie ici sur la bonne fenêtre**, avec 384 cellules, un gate au gross et des contrôles que
l'original n'avait pas (delay+1 en sortie, baseline L58, bootstrap par blocs).

⚠ **Cela ne réhabilite PAS le nombre 344 comme déflateur.** Les 384 cellules de ce rapport
**remplacent** les 284 reproductibles de l'étude buggée, elles ne s'y ajoutent pas : ce sont les
**mêmes hypothèses** mesurées correctement. Le compte défendable pour l'espace indices-MR reste
celui recommandé par la revue (`intraday_mr_ftmo`, ≈13) **plus** les 384 d'ici, **pas** 344 + 384.

---

## 6. Comptabilité des essais

| bloc | cellules |
|---|--:|
| B1 — grille fenêtre de clôture (4 instr × 3 K × 5 tenues × 3 θ) | **153** |
| B1 — placebo temporel (29 ancres) | 29 |
| B1 — décomposition auction / retards d'entrée | 5 |
| B1 — sous-périodes | 6 |
| B1 — test d'horloge UTC | 2 |
| MR réparé — FULL / CLOSE / CLOSE_ENTRY | **384** |
| **TOTAL mesuré** | **579** |

Diagnostics N0 **non comptés** (ils ne mesurent aucune performance) : appariement de fuseau, L60,
part de spread nul, disponibilité des barres post-clôture, profils horaires L56, profil minute
autour de la clôture.

**Statut :** la réparation est **N0, non déflatrice** — elle corrige une mesure existante, elle ne
propose pas d'hypothèse nouvelle. **Aucun survivant n'est promu.** Šidák à 5 % sur 579 cellules
exigerait p < 8.9 × 10⁻⁵ ; la meilleure cellule two-sided du rapport (GER40 clôture θ1.5, p < 0.001
au bootstrap) **ne l'atteint pas**, et de toute façon elle est tuée par le test d'exécution, pas par
le comptage.

**Si quelqu'un veut rouvrir GER40-clôture, la pré-inscription N2 est déjà écrite :**
- **hypothèse** : la réversion post-clôture GER40 est collectable **avec une entrée à 17:36 ou plus
  tard** (c'est-à-dire hors auction) ;
- **kill rule, écrite AVANT la donnée** : mort si `m_two_sided(17:36→17:46) < 1.5 × 1.8 bps` **ou**
  si l'une des deux jambes a t < 1.0 **ou** si retirer les 5 % de meilleurs trades fait passer la
  moyenne sous le coût ;
- **état actuel : les trois conditions de mort sont déjà remplies** (0.56 bps ; t_S −0.16 ; 0.90 bps).
  Rouvrir sans **véhicule ou données nouvelles** (imbalance d'auction, cotation intra-auction) serait
  du data-mining et déflaterait le DSR de tous les candidats suivants.

---

## 7. Ce que ce rapport NE prouve PAS

1. **Il ne réfute pas Baltussen-Da-Soebhag.** Le papier mesure un **long-short en coupe transverse
   d'actions individuelles**. Je teste **l'agrégat au niveau indice**, qui est une quantité
   différente — l'a priori du mandat (« la pression idiosyncratique se compense en grande partie »)
   est **confirmé**, pas contredit. Un univers d'actions individuelles reste non testé faute de
   véhicule FTMO viable.
2. **Il ne teste pas la version conditionnée au déséquilibre d'auction.** La variable de
   conditionnement du papier — le déséquilibre de l'auction — est exactement celle dont nous ne
   disposons pas. Un candidat futur avec ces données serait une **hypothèse nouvelle**, relevant de
   la catégorie « données » et non des quatre catégories rouvrables.
3. **Il ne teste que 4 indices, 2 régions.** Nikkei, FTSE, ASX, indices émergents : non couverts.
   Le résultat US (continuation) et le résultat GER40 (réversion) ayant des **signes opposés**, on ne
   peut pas extrapoler à un troisième marché.
4. **Il ne revendique pas la continuation post-clôture US comme un edge.** Signe trouvé, pas
   pré-enregistré. Et la fenêtre US post-clôture est **mince** (fourchette 9.2 → 2.7 bps, jusqu'à
   5.8 % de barres à fourchette nulle) : le coût réel y est vraisemblablement supérieur aux 1.8 bps
   de séance, non mesuré ici.
5. **Il ne dit rien du GER40 hors 2014-2026**, ni de ce que ferait la sleeve GER40 avec une exécution
   **dans** l'auction (ordre MOC / participation à l'auction Xetra) — ce serait un **véhicule
   différent**, hors CFD retail, et donc légitimement rouvrable au titre de la politique de
   ré-ouverture (catégorie **véhicule**).
6. **Il ne mesure pas les swaps.** Les cellules overnight (`r_HON`) sont **gross et sans swap** ; à
   ce titre elles sont **optimistes**, ce qui renforce leur verdict négatif (L36).
7. **La portée CLOSE est sous-peuplée** (§4) ; c'est CLOSE_ENTRY qui porte la conclusion.
8. **Le test d'horloge D est inconclusif** pour la cellule GER40 précise (§3.3 D). L'ancrage à
   l'horloge d'échange est établi au niveau du profil de volatilité, pas au niveau de cette cellule.

---

## 8. Corrections appelées ailleurs dans le repo

1. **`CLAUDE.md` §Data sources** — « indices et or plutôt propres » est **faux pour US30** :
   colonne `spread` nulle à **79.7 / 100.0 / 74.9 %** en 2019 / 2020 / 2021 (re-mesuré ici).
2. **`_audit/m5_indices_migration_checklist_2026-06-10.md`** — ajouter
   `PropFirms/ftmo/program_2026-06/ftmo_research/code/mr_deepdive.py` comme consommateur buggé
   (`tz_localize("UTC")` sur des timestamps EET, confirmé au tick §1). Ce rapport le **remplace** ;
   ne pas le ré-exécuter.
3. **Fermeture indices-MR** — désormais adossée à **deux** études sur horloge correcte
   (`intraday_mr_ftmo` + celle-ci), et **jamais** à L43 (strictement FX).
4. **Candidat de leçon (non numéroté — pas de minting en session) :**
   `closing-auction-reversal-exists-at-index-level-but-lives-inside-the-auction-window`.
   Formulation : *un effet de clôture doit être re-daté à l'intérieur de la fenêtre d'auction avant
   d'être revendiqué ; décomposer l'auction et retarder l'entrée de 5 minutes coûte zéro essai et
   sépare « prime de liquidité prise de l'extérieur » (0.56 bps, t 1.00) de « effet de prix »
   (3.52 bps, t 3.68). Corollaire : la stabilité en sous-période ne défend pas un edge dont la
   demi-vie est de quelques minutes.*

---

## 9. Reproduire

```
/usr/bin/python3 code/prep_cache.py      <scratch>/cache   # cache M1 + L60 + L56  (~8 min)
/usr/bin/python3 code/close_window.py    <scratch>/cache   # B1, 153 cellules
/usr/bin/python3 code/falsify_ger40.py   <scratch>/cache   # placebo / auction / sous-périodes / queue
/usr/bin/python3 code/mr_repaired.py     <scratch>/cache   # MR réparé, 384 cellules
/usr/bin/python3 code/decision_metric.py <scratch>/cache   # p(pass) + durée
```

Les caches et les tables de cellules sont écrits **hors du repo** (scratchpad) : **aucun blob data
n'entre dans git**. Les sources M1 sont lues en **lecture seule** dans le répertoire principal
(`<HOME>/Desktop/Algo_claude/data/deep_history_utc/`), absentes du worktree car
gitignorées. Aucun chemin live n'est touché (`ftmo_live/`, `strategies/`, `Futures/live/`,
`Portfolio/`, `.github/`, `*.mq5`) — `Portfolio/admission/barrier.py` est **importé**, jamais modifié.
