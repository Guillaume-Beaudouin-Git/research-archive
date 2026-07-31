# REVIEW — Audit des verdicts MR/L43 + revue de littérature orientée mécanisme

**Date :** 2026-07-31 · **Branche/commit de référence :** `main` @ `b6b3c823` · **Essais consommés : 0** (N0, aucun backtest, aucune mesure de performance de stratégie).
**Nature des mesures faites ici :** diagnostics de données et relectures de code / d'artefacts existants. Aucun signal n'a été construit, aucune P&L n'a été simulée.
**Interpréteur :** `/usr/bin/python3`. **Aucun commit, aucun SSH.**

---

# PARTIE A — AUDIT FACTUEL DES DEUX VERDICTS BLOQUANTS

## Synthèse des verdicts

| # | Verdict audité | Statut |
|---|---|---|
| A.1 | « MR intraday indices : 0/344 two-sided » | **PARTIEL** — le *test* two-sided est authentique (ce n'est PAS l'artefact `_SS`), mais l'étude qui porte le « 344 » a une **erreur de fuseau fatale** : 43.9 % de l'échantillon « RTH » est du pré-marché et **38.7 % du vrai RTH n'a jamais été testé** (dont la clôture). Le chiffre « 344 » n'est pas non plus le bon compte (284 cellules reproductibles + 60 non reproductibles). |
| A.2 | L43 « retail FX intraday-flat est cost-dead » | **SOLIDE mais STRICTEMENT FX** dans sa formulation gravée — et la généralisation aux indices, qui existe bel et bien, **repose sur une AUTRE étude** (`intraday_mr_ftmo`, 2026-06-20), pas sur L43. Cette autre étude est **méthodologiquement propre** (vrai UTC, gross two-sided, audit indépendant) → la fermeture des indices tient, mais **elle ne doit plus être citée « par L43 »**. |
| A.3 | Artefact `_SS` (`side = -side_long`) | **CONFIRMÉ, et borné** : 24/24 paires `_LO`/`_SS` exactement miroir dans `top10_test`, **famille `event_drift` uniquement**. **Zéro contamination des verdicts MR.** |

---

## A.1 — « MR intraday indices : 0/344 two-sided »

### Où ça vit
- Rapport : `PropFirms/ftmo/program_2026-06/ftmo_research/MR_deepdive_ftmo.md`
- Code : `PropFirms/ftmo/program_2026-06/ftmo_research/code/mr_deepdive.py`
- Données de sortie : `.../mr_deepdive_grid.csv` (284 lignes + en-tête), `.../mr_deepdive_halflife.csv`
- Propagation du verdict : `N_ledger.md` lignes 114, 126, 128, 130 (« ré-tester … ne peut pas produire un survivant (0/344 two-sided) »).

### Q1 (la question décisive) — le two-sided était-il un vrai test de la jambe short ?

**OUI. Ce n'est pas l'artefact `_SS`.** Preuve dans le code, `build_trades()` :

```python
side = -1.0 if di > 0 else 1.0          # fade
```

Le side est **dispatché par le signe de la déviation** : les trades « long-fade » (prix étendu vers le bas) et « short-fade » (prix étendu vers le haut) sont des **événements disjoints, à des barres différentes**. `mL` et `mS` sont les moyennes de deux sous-populations distinctes, pas deux vues d'un même trade.

Vérification numérique sur les 284 cellules :
- lignes où `mL == -mS` (signature de l'inverse mécanique) : **0 / 284**
- `corr(mL, mS)` = **−0.375** (l'artefact `_SS` donnerait exactement −1.000)
- `mL + mS` : moyenne −3.59, min −13.43, max +5.88 (loin d'être identiquement nul)

**⇒ Le verdict « 0 two-sided » de `MR_deepdive` n'est PAS nul et non avenu au titre de l'artefact `_SS`.** Le test two-sided y est réel et c'est même, dans ce dossier, la partie la mieux faite.

### Q2 — mais alors, qu'est-ce qui cloche ? Le fuseau horaire. C'est fatal.

`load_1m()` fait, pour **les 5 instruments non-NQ** :

```python
d.index = pd.to_datetime(d.index).tz_localize("UTC").tz_convert(tz)
```

Or les panels `data/panels/m5_indices/*_m1_panel.parquet` ont une colonne d'index nommée `timestamp_utc` qui **n'est pas UTC** : c'est l'heure serveur MT5, **EET/EEST**. C'est déjà écrit dans `CLAUDE.md` (« panels parquet EET ») et dans la mémoire `mt5_data_provenance_2026-06`. Je l'ai **re-vérifié empiriquement** (profil de `mean|ret|` horaire, 2022+) :

| série | pic de volatilité (heure du label) hiver | pic été | lecture |
|---|---|---|---|
| US500 (panel) | 16h→17h | 16h→17h | **fixe** ⇒ label = EET/EEST (l'ouverture NY 09:30 tombe à 16:30 dans les deux saisons) |
| GER40 (panel) | 10h | 10h | **fixe** ⇒ EET (ouverture DAX 09:00 Berlin = 10:00 EET, hiver comme été) |
| EURUSD (panel) | 17h | 17h | **fixe** ⇒ EET |
| US500 (`deep_history_utc`) | **15h** | **14h** | **décale de 1 h** ⇒ **vrai UTC ✓** |

Le code traite donc du EET comme de l'UTC. Décalage net **−7 h** sur les indices US (label→UTC→New York = label−5 en hiver, alors que le vrai NY = label−7).

**Conséquence mesurée** (sur les barres réellement sélectionnées par le filtre du code, US500) :

```
barres sélectionnées par le filtre "RTH 09:00-16:00 NY" : 508 880
  dont VRAI RTH (09:30-16:00 NY)      : 56.1 %
  dont VRAI pré-marché (< 09:30 NY)   : 43.9 %
  couverture du vrai RTH              : 61.3 %   (38.7 % du RTH jamais testé)
  histogramme des vraies heures NY    : 06h → 13h
```

Autrement dit, l'étude a testé **06:00–13:00 NY** (été) / **07:00–14:00 NY** (hiver) au lieu de 09:30–16:00 :
- ~44 % de l'échantillon est du **pré-marché** — liquidité mince, spread large, **12.1 % de barres à rendement nul contre 7.1 % en RTH**, et **une volatilité moitié moindre** (1.58 vs 2.79 bps/min). Le coût forfaitaire de 1.5 bps y est irréaliste, et des quotes rassises fabriquent mécaniquement de la « réversion ».
- **Toute la fin de séance est absente** : 13:00/14:00–16:00 NY, c'est-à-dire l'heure de clôture, la fenêtre MOC/auction — **précisément la fenêtre que la littérature désigne comme le lieu de la réversion intraday** (Baltussen-Da-Soebhag ; Bogousslavsky).

Même diagnostic sur **GER40** : 31.7 % des barres retenues sont **avant l'ouverture cash 09:00 Berlin**, couverture du cash 09:00–17:30 = **63.8 %**, et la fenêtre **15:00–17:30 Berlin manque entièrement** — soit le recouvrement avec l'ouverture US, le moment le plus volatil de la journée DAX.

**Et la seule quasi-candidate du rapport est mal nommée.** La cellule vedette « EURUSD midday, 11–14 **UTC** » utilise en fait des labels EET ⇒ **08:00–12:00 UTC réels**. Ce n'est pas un « midday » (creux de mi-journée), c'est **la matinée de Londres**, la période la plus active du FX. Le mécanisme raconté autour de cette cellule (accalmie de mi-journée ⇒ réversion) ne décrit pas la fenêtre réellement mesurée. C'est un cas L56 canonique.

### Q3 — le compte « 344 » et la reproductibilité

- `mr_deepdive_grid.csv` contient **284 cellules** — cohérent avec le rapport.
- Les **60 cellules « regime-conditional »** — celles qui produisent le fameux « 4/60 two-sided-positifs » et l'unique quasi-candidate — **n'ont aucun code dans le repo** : `run_grid()` n'a aucun conditionnement de régime (ni tercile de vol, ni time-of-day, ni variance ratio). **Ces 60 essais sont non reproductibles** ; seul le tableau du markdown en atteste.
- ⇒ « 344 » = 284 vérifiables + 60 invérifiables. Le nombre est utilisé dans `N_ledger.md` comme **déflateur de DSR** pour tous les candidats futurs indices-MR (« tout candidat indices-MR naît DSR-mort »). **Un déflateur dont 17 % des essais sont non reproductibles et dont 100 % portent sur la mauvaise fenêtre horaire ne peut pas jouer ce rôle.**

### Q4 — le critère « two-sided » lui-même : net, pas gross, et sans t par jambe

Le rapport annonce « 0 two-sided », mais le critère appliqué est `mL > 0 et mS > 0` **net de coût**, sur des **estimations ponctuelles** (aucun t-stat par jambe, aucun HAC). J'ai recalculé la version **gross** (en rajoutant le coût, 1.5 bps indices / 1.0 bps FX) :

```
cellules avec les DEUX jambes gross > 0 : 45 / 284   (dont 17 sur indices)
meilleur gross poolé parmi celles-ci     : 0.767 bps
meilleure jambe faible                   : 0.578 bps   (US30 5m RSI14 θ25)
```

Donc la formulation exacte devrait être : *« 0 cellule two-sided **nette**, 45 cellules two-sided **brutes**, dont la meilleure plafonne à 0.77 bps »*. C'est une nuance importante — le « 0 » conflate le test de symétrie et le test de coût — **mais elle ne renverse rien** : 0.77 bps est **4× sous le seuil L33b de 3 bps**. Sur ce point précis, la conclusion économique tient.

Note de direction, rassurante : le coût utilisé (1.5 bps indices) est **plus optimiste** que le standard du repo (2–3 bps mesurés, cf. §A.2). Un coût trop bas rend le passage **plus facile** ⇒ trouver 0 survivant malgré ça est conservateur dans le bon sens.

### Q5 — delay+1 (L59), colonne `spread`, barres à fourchette nulle (L60)

- **delay+1 (L59)** : le délai n'est appliqué qu'à l'**ENTRÉE** (`j = i + delay`). Il n'y a cependant **ni stop ni bracket** dans ce moteur (sorties = time-stop à la half-life, ou « mean-touch »), donc le mode de défaillance spécifique de L59 (fill au stop exact alors que 25 % des barres ouvrent au-delà) **ne s'applique pas ici**. Résidu mineur : la sortie « mean-touch » décide sur `dev[k]` et remplit à `px[k]` (même clôture de barre) — exécutable au close, mais non re-pricé. Second résidu : `delay1_mean` n'est calculé **que si la cellule est déjà nette-positive** (« cheap filter ») — donc pour 282 des 284 cellules, **le test de délai n'a jamais tourné**.
- **Colonne `spread`** : **non utilisée**. Coût forfaitaire en dur (1.5 / 1.0 bps). Le défaut « colonne `spread` inutilisable » ne touche donc pas cette étude.
- **L60 (fourchette nulle)** : le moteur n'utilise que `close`, jamais `high`/`low`. J'ai mesuré la santé des séries indices de `deep_history_utc` : **`high == low` reste ≤ 6 %/an** sur US500/US100/US30/GER40 — **les indices ne souffrent pas du syndrome XPT/XPD**. Le problème équivalent ici est le **rendement nul en pré-marché (12.1 %)**, introduit par le bug de fuseau, pas par la série.

### **VERDICT A.1 : PARTIEL.**

Ce qui **tient** :
- le test two-sided est authentique (jambes disjointes, pas d'inverse mécanique) ;
- l'ordre de grandeur du gross MR intraday sur ces instruments est **sub-bps** (best two-sided brut 0.77 bps) — 4× sous L33b ;
- le sens de l'erreur de coût protège la conclusion.

Ce qui **ne tient pas** :
- « 344 essais » comme **déflateur DSR** : 60 essais non reproductibles, 284 mesurés **sur la mauvaise fenêtre horaire** ;
- « la famille MR intraday indices est close AU DEPTH » : **38.7 % du vrai RTH — dont la clôture — n'a jamais été testé**, et 44 % de ce qui l'a été était du pré-marché ;
- la quasi-candidate « EURUSD midday » : mécanisme mal attribué (matinée de Londres, pas mi-journée).

**Action recommandée :** dégrader dans `N_ledger.md` le statut de `MR_deepdive` de « verdict de famille au depth » à « verdict sur une fenêtre horaire erronée », **retirer 344 du compte de déflation DSR** pour les candidats indices-MR (le compte défendable est celui de `intraday_mr_ftmo`, §A.2, ≈13), et **ne pas** ré-exécuter `mr_deepdive.py` sans corriger `tz_localize("UTC")` → `tz_localize("Europe/Athens")` (ou, mieux, migrer vers `data/deep_history_utc/`, vrai UTC vérifié).

---

## A.2 — L43 : FX seulement, ou aussi les indices ?

### Ce que L43 dit vraiment
Source : `Forex/research/active/fx_intraday_deepdive/SYNTHESIS.md` §4. Univers : **10 majors FX, M1, 2007–2026, `deep_history_utc` vrai UTC**. Les trois hypothèses (H1 reversal London-open, H2 drift post-news, H3 saisonnalité dow×session) sont **toutes FX**. Le texte gravé dit « retail **FX** intraday-flat ». Le ratio plancher **0.36** est un ratio **FX**.

**⇒ L43, dans sa formulation, ne dit rien des indices. Toute citation de L43 pour fermer les indices est, littéralement, hors périmètre.**

C'est mécaniquement important : les indices CFD ont une volatilité intraday nettement supérieure pour un spread comparable. Mesuré dans le repo (médianes de la colonne `spread`, étude `intraday_mr_ftmo`) : US30 0.34 bps, GER40 0.60, US100 0.79, US500 1.16, contre EURUSD 0.16 / GBPUSD 0.36 — soit un spread **du même ordre**, pour une amplitude de barre bien plus grande. L'intuition « L43 ne transfère pas » était donc **légitime**.

### Mais la généralisation existe, et elle est ailleurs — et elle est propre

`yt_strategy_replications/intraday_mr_ftmo/` (2026-06-20) est **une étude indices dédiée**, distincte du deep-dive FTMO, et c'est elle qui porte réellement la fermeture :

- **Données : `data/deep_history_utc/`** (vrai UTC — je l'ai re-vérifié par le décalage DST : pic US500 à 15h l'hiver, 14h l'été ✓).
- **Univers :** US100, US500, US30, GER40 + EURUSD, GBPUSD, USDJPY, barres 15 min.
- **Le gate décisif est au GROSS**, coût = 0 : `bt(...) cost_rt=0.0`, jambes long et short **séparées et disjointes** (`allow_long` / `allow_short`), t HAC Newey-West lag-6.
- **Résultat (out_primary.txt) :** index book poolé **gross SR −0.34 (t −1.34)** ; la seule jambe positive est **US500 long-only gross SR +0.58** — dont l'audit indépendant montre qu'elle est **sous le drift inconditionnel** (conditionnel +1.58 bps vs inconditionnel +1.50 bps t 3.91) ⇒ **piège beta L25**, pas alpha.
- **Grille de robustesse** z0∈{1.5,2,2.5} × H∈{4,8,12} : gross ∈ [−0.49, −0.04], **aucune positive**. **Flip momentum** aussi négatif (−0.08 à −0.59) ⇒ *les barres à |z| extrême ne portent aucune autocorrélation exploitable, dans aucun sens*. **Gap-fade** (mécanisme MR indépendant) : gross poolé −0.50.
- **Audit auteur≠auditeur** : event study from scratch, convention de signe vérifiée, look-ahead testé sur série synthétique, balayage H∈{1,…,24} — le signal two-sided **n'atteint jamais |t| ≥ 2.5**.

**Le point qui rend ce verdict robuste : il échoue au GROSS.** Ni la colonne `spread`, ni le modèle de coût, ni les swaps n'entrent dans le gate 1. Les défauts de coût sont donc **sans effet sur la conclusion**.

### Contrôles L59 / spread / L60 sur cette étude

- **L59 — delay+1 entrée ET sortie : NON.** L'entrée est correcte (`signal at close t → entry at open t+1`, imposé par le moteur). Mais `engine/backtest.py::run_backtest_vectorized` **remplit les SL et les TP au prix exact de la barrière** (`sl_px` / `tp_px`) — c'est exactement le défaut L59, et il mord fort ici : **frac_sl ≈ 0.47 et frac_tp ≈ 0.46**, donc ~93 % des trades sortent sur barrière. **Direction de l'erreur : OPTIMISTE.** Corriger L59 rendrait un résultat déjà négatif **plus** négatif. La conclusion est donc *a fortiori* valide.
- **Colonne `spread` : OUI, elle est utilisée** (`dataload.py` → `spread_bps`, puis `med_cost = median(spread_bps)`). Elle est effectivement peu fiable — et **j'ai trouvé pire que ce que `CLAUDE.md` documente.** `CLAUDE.md` affirme « indices et or plutôt propres » ; c'est **faux pour US30** :

| série | % barres à spread nul, par année |
|---|---|
| US30 | 2018 **5.6** · 2019 **79.7** · 2020 **100.0** · 2021 **74.9** · 2022+ ≈0 |
| EURUSD | 2020 9.9 · 2021 **65.9** · 2022 **69.4** · 2023 **63.3** · 2024 22.3 · 2025 26.2 · 2026 40.4 |
| US500 / US100 / GER40 / XAUUSD | ≤ 5 % partout (2021 ≈ 4.8 % ponctuel) |

Le « spread médian US30 = 0.342 bps » cité par l'étude est donc calculé sur une colonne **vide à 100 % en 2020**. Sans conséquence ici (gate au gross, plus des stress rows à 2 et 3 bps), mais **`CLAUDE.md` doit être corrigé sur ce point** avant qu'un futur PASS ne s'appuie sur du US30 2019-2021.
- **L60 :** non applicable — `high == low` ≤ 6 %/an sur les 4 indices (mesuré ci-dessus). Séries saines.
- **Résidu L56 (mineur) :** la fenêtre indices est figée à **13:30–20:00 UTC**. C'est exactement la séance cash **en été** (EDT), mais **en hiver** (EST) cela vaut 08:30–15:00 ET : ~1 h de pré-marché et **la dernière heure de cotation est perdue**. Même classe de défaut qu'en A.1, d'un ordre de grandeur bien moindre (1 h contre 7 h), mais il ampute **encore une fois la fenêtre de clôture**, sur ~5 mois par an. Pour GER40, la fenêtre 13:30–20:00 UTC déborde largement au-delà de la clôture cash du DAX (16:30 UTC l'hiver, 15:30 l'été) — et GER40 est justement le seul indice dont le gross n'est pas négatif (+0.04).

### **VERDICT A.2 : L43 = SOLIDE, mais STRICTEMENT FX. La généralisation aux indices = SOLIDE, mais elle appartient à `intraday_mr_ftmo`, pas à L43.**

Concrètement :
1. **Cesser de citer L43 pour fermer les indices.** La citation correcte est `yt_strategy_replications/intraday_mr_ftmo/FINDINGS.md`. Le candidat de leçon y est d'ailleurs déjà nommé et **non gravé** : `price-only-intraday-MR-is-autocorr-and-cost-dead-on-equity-indices-too`. **À graver** (numéro à attribuer en réconciliation) — sinon la fermeture des indices reste orpheline et continuera d'être citée à tort via L43.
2. **La généralisation n'est PAS abusive sur le fond** : sur indices, le gross conditionnel mesuré est **≈1.6 bps** (US100/US500 après |z|≥2), soit ~4× le FX — l'intuition « les indices ont plus de vol » est **confirmée** — mais cela reste **sous les 3 bps de L33b**, et surtout **la jambe short est nulle** (US100 +0.09 bps t 0.07 ; US500 +0.79 t 0.91) alors que le drift inconditionnel est massif (t 4.49 / 3.91). Ce n'est pas un problème de coût : **il n'y a pas de signal symétrique**.
3. **Ce qui n'est fermé par personne :** les indices en **clôture** (dernière heure / MOC), jamais couverts par aucune des deux études — A.1 les exclut par bug, A.2 les perd en hiver et n'a jamais isolé la fenêtre. Voir Partie B, mécanisme **B1**.

---

## A.3 — L'artefact `_SS` : confirmé et borné

Localisation : `PropFirms/ftmo/program_2026-06/top10_test/batch_strategies.py:560-572`.

```python
for et, inst, cls, side_long in event_inst_map:
    ... id=f"ed_{et.lower()}_{inst}_LO",  params=dict(..., side=side_long, ...)
    ... id=f"ed_{et.lower()}_{inst}_SS",  params=dict(..., side=-side_long, ...)
```

Vérifié sur `results/summary_batch_142.csv` : **24/24 paires exactement miroir** en `mean_bps_per_trade_gross`, `|LO + SS| < 1e-6`. Le cas cité par le mandat est `ed_fomc_US30` : **+29.407 / −29.407**. Confirmé au chiffre près.

**Portée exacte :** famille **`event_drift` uniquement** (pré-FOMC / NFP / CPI / BoE / BCE / BoJ sur US500, US100, US30, GER40, EURUSD, GBPUSD, USDJPY, EURGBP, EURJPY, XAUUSD). Conséquences :
- ces 24 cellules `_SS` **ne testent rien** — ce ne sont pas des essais, et elles **gonflent `n_trials` de 24** sans apporter d'information (donc sur-déflatent le DSR de tous les candidats suivants) ;
- toute affirmation « two-sided » de la famille `event_drift` est **nulle et non avenue** ;
- **L42** (drift pré-FOMC réel sur indices) repose sur les cellules `_LO` directionnelles et n'est pas invalidée par cet artefact — mais elle n'a, du coup, **aucun support two-sided**, et le mandat L25 n'y a jamais été honoré.

**Aucune contamination des verdicts MR** : `mr_deepdive.py` et `intraday_mr_ftmo` construisent tous deux leurs jambes par dispatch sur le signe du signal, sur des trades disjoints. Vérifié.

---

## A.4 — Ce que je n'ai pas pu vérifier

- Les **60 cellules regime-conditional** de `mr_deepdive` (dont la cellule EURUSD-midday et le tableau §3 du rapport) : **aucun code correspondant dans le repo**. Non reproductible. Je ne peux ni confirmer ni infirmer les chiffres du tableau, seulement constater que la fenêtre horaire sous-jacente est erronée.
- Les chemins d'exécution de `mr_deepdive.py` pointent vers un sandbox cloud (`/sessions/blissful-upbeat-newton/...`). J'ai établi que les données sont **les mêmes** que les panels locaux par recoupement des spans (`US500 2021-01-22..2026-05-28`) et du volume de barres (508 880 barres M1 sélectionnées ≈ 101.8 k barres 5 min, contre 102 890 déclarées) — c'est une inférence, pas une preuve directe.
- La **valeur réelle du round-trip FTMO** sur indices : je m'appuie sur les chiffres déjà consignés dans le repo (2–5 bps, et « colonne spread ≈ 2.4× optimiste »). Non re-mesurée ici.
- Le batch **`#7 idx_spreadMR` (5 essais)** cité dans `N_ledger.md:128` : non localisé.

---

# PARTIE B — REVUE DE LITTÉRATURE, ORIENTÉE MÉCANISME

## B.0 — Ce que les collecteurs du repo contenaient (vérifié en premier)

`_automation/alpha_hunt/promising/` : **421 items**. Filtrage sur reversal / intraday / microstructure / session / auction / order-flow : la quasi-totalité est de l'**économétrie ou du ML** (GARCH multivarié, LSTM vs GBT, pricing d'options, agents LLM). Les trois seuls items plausiblement pertinents sont **des négatifs ou du hors-sujet** :
- *Split-Session Cluster GARCH for Overnight and Intraday Returns* (arXiv 2607.03669) — modélisation de queues par session ; **aucun signal**, `REFERENCE`.
- *Sequential Structure in Intraday MNQ Futures: LSTM vs GBT* (arXiv 2605.17724) — **négatif** : ni LSTM ni GBT ne battent le buy-and-hold après coûts sur 944 jours de MNQ 5 min. Corrobore l'idée que le prix seul en intraday indices est vide.
- *Real-Time Price Impact Detection* (arXiv 2606.13419) — exécution, pas signal.

**Conclusion : le pipeline `alpha_hunt` ne contient aucun mécanisme exploitable pour nos deux familles.** Il collecte du bruit méthodologique. Tout ce qui suit vient de la littérature primaire.

---

## Filtre appliqué à chaque mécanisme
**Retenu** seulement si plausiblement **> 3 bps de gross intraday** (L33b) ou **≫ le swap** si porté (L36), sur **instrument FTMO**, avec **queue gauche courte**. Les mécanismes qui échouent sont listés explicitement — les éliminer maintenant coûte 0 essai et protège le DSR de tous les candidats futurs.

---

## Rang 1 — Le seul mécanisme qui coche la case « > 3 bps », et le seul angle non testé du repo

### **B1. Pression de prix de la clôture et sa réversion (auction / MOC / fin de séance)**

- **Référence :** Baltussen, Da & Soebhag, *End-of-Day Reversal* (SSRN 5039009 ; 2ᵉ prix Quantpedia Awards 2025). Contexte : Bogousslavsky, *The Cross-Section of Intraday and Overnight Returns* (JFE 2021) et *Infrequent Rebalancing, Return Autocorrelation, and Seasonality* (JF 2016) ; littérature sur la croissance de l'auction de clôture (~11 % du volume quotidien, +44 % en six ans).
- **Mécanisme en une phrase :** la concentration croissante du volume institutionnel dans la dernière demi-heure et l'auction de clôture crée une **pression de prix non informative** que personne ne peut absorber dans la fenêtre, et qui **se dénoue** ensuite.
- **Conditions d'existence :** volume de clôture élevé / déséquilibre d'auction important ; l'effet est **une prime de fourniture de liquidité à un flux forcé**, pas une prévision.
- **Ordre de grandeur annoncé :** **0.24 % par jour** sur la dernière demi-heure pour le long-short décile en coupe transverse d'actions US. Et : *« les déviations de prix de clôture se renversent presque intégralement pendant la nuit, dont un tiers à la moitié dans la première demi-heure après la clôture »*. C'est **deux ordres de grandeur au-dessus de nos 3 bps** — c'est le seul mécanisme de cette revue dont l'amplitude brute n'est pas le problème.
- **Ce qui le tue — et c'est décisif pour nous :** l'effet documenté est **cross-sectionnel sur actions individuelles** (N≥30, décile long-short), mécanisme = *« achats retail induits par l'attention + gestion du risque des vendeurs à découvert en fin de journée »*. **FTMO ne donne pas accès à un univers d'actions individuelles à coût viable** ⇒ dans sa forme publiée, **NON TRADABLE chez nous**. En outre : *« provient principalement d'une pression de prix positive sur les perdants intraday »* ⇒ **asymétrique, donc suspect au titre de L25**.
- **Lecture critique / ce qui reste :** la version *au niveau indice* — la déviation de clôture de l'**indice** (et non la coupe transverse) se renverse-t-elle ? — **n'est pas ce que le papier montre**, et **n'a jamais été testée dans ce repo** : A.1 exclut la fenêtre par bug de fuseau, A.2 la perd cinq mois par an. C'est un **trou de couverture réel**, pas une piste recyclée. Prudence a priori forte : en coupe transverse la pression idiosyncratique s'agrège, au niveau indice elle se **compense largement** — l'amplitude indice sera très inférieure à 24 bps, et rien ne garantit qu'elle dépasse 3 bps. Mais c'est le seul endroit où le repo n'a pas de mesure.
- **Verdict :** **le seul candidat qui mérite un essai**, et seulement sous la forme : *fenêtre de clôture de l'indice, testée d'abord au GROSS et two-sided, sur `deep_history_utc` avec horloge d'échange DST-correcte (L56)*.

---

## Rang 2 — Mécanismes réels, mais dont la mort est documentée et récente

### **B2. Overnight drift / dérive de réouverture — le mécanisme d'inventaire. MORT depuis 2021.**

- **Références :** Boyarchenko, Larsen & Whelan, *The Overnight Drift* (RFS 36(9), 2023 ; NY Fed SR 917) — puis, **décisif**, **Boyarchenko, Larsen & Whelan, *The Disappearing Overnight Drift*, Liberty Street Economics, juillet 2026** (SSRN 7035838).
- **Mécanisme en une phrase :** les teneurs de marché US absorbent le **déséquilibre d'ordres de la clôture US** et se font rémunérer pour le risque d'inventaire au moment où la liquidité revient — **à l'ouverture des marchés européens** ; l'équation d'équilibre du papier est `E[R_ON] = (déséquilibre en dollars) × (variance) / (capacité de portage du risque)`.
- **Conditions d'existence :** dispersion des déséquilibres de clôture. Asymétrie documentée : les **sell-offs** produisent des réversions overnight robustes, les rallyes beaucoup moins.
- **Ordre de grandeur :** **~3.7 %/an**, concentré dans la seule fenêtre **02:00–03:00 ET**, soit **> 60 %** du rendement close-to-close du contrat (5.9 %/an), sur ES/NQ/YM, 1998–2020.
- **Ce qui le tue — mesuré, pas conjecturé :** *« proche de zéro »* sur **janvier 2021 – décembre 2025**. Cause identifiée : **l'écart-type du volume signé relatif à la clôture est passé de 6.5 % à 2.9 %** (compression de plus de moitié), parce que *« les ordres limites postés à la clôture sont devenus plus petits, ce qui est cohérent avec des fournisseurs de liquidité algorithmiques qui découpent le flux plus finement »*. VIX et liquidité overnight **inchangés** — ce n'est ni un régime de vol ni un problème de liquidité. **Et la version conditionnelle meurt aussi** : la relation prédictive déséquilibre-de-clôture → rendement overnight *« s'est rompue »*, l'écart entre gros déséquilibres négatifs et positifs est *« bien plus étroit »* en 2021-2025. Les ETF NightShares (NSPY, NIWM), lancés en juin 2022 sur ce mécanisme précis, ont **fermé quatorze mois plus tard**.
- **Lecture critique — et pourquoi cela nous concerne directement :** c'est un cas d'école de **L31 (alpha-decay hors régime)** et de **L23b**, avec en prime la démonstration que **la version conditionnelle ne survit pas** à la mort de la version inconditionnelle. **Implication pour notre L56** : notre drift overnight or/argent, ancré à la première heure après la réouverture Globex 18:00 ET, est **exactement le même type d'effet** (rémunération du portage d'inventaire au retour de liquidité), sur un autre actif et une autre fenêtre. Le papier de 2026 doit être lu comme un **avertissement sur la durée de vie de L56**, pas comme une confirmation. Test gratuit, hautement recommandé : **la dispersion du volume signé de clôture s'est-elle comprimée de la même façon sur l'or ?** Si oui, L56 est en train de mourir pour la même raison, et il faut le savoir **avant** de dimensionner dessus.
- **Verdict :** **famille FERMÉE sur indices** ; **ne pas re-tester le drift overnight indices**. Valeur pour nous : diagnostic de survie à appliquer à L56.

### **B3. Market intraday momentum (première demi-heure → dernière demi-heure)**

- **Référence :** Gao, Han, Li & Zhou, *Market Intraday Momentum* (JFE 129(2), 2018).
- **Mécanisme :** le rendement de la première demi-heure prédit celui de la dernière demi-heure ; le canal proposé est le **rééquilibrage différé** de Bogousslavsky (2016) — des investisseurs qui repoussent leur rééquilibrage vers la clôture plutôt que l'ouverture — plus de l'ordre de flux dépendant de la tendance (vol-targeting, ETF à levier).
- **Conditions d'existence :** *plus fort les jours de forte volatilité, de fort volume, en récession, et les jours d'annonce macro majeure.*
- **Ordre de grandeur :** SPY, 1993–2013, **R² out-of-sample 1.4 %** (2.0 % avec la 12ᵉ demi-heure en plus). C'est un R² de prédiction, pas un gross par trade ; le papier ne fournit pas de mesure de coût sérieuse.
- **Ce qui le tue :** (a) l'échantillon s'arrête en 2013, publication 2018 — l'exposition post-publication n'est pas couverte ; (b) c'est un signal **directionnel one-sided-friendly** sur un actif à drift positif ⇒ **piège L25/L38** à contrôler impérativement ; (c) **`arXiv 2605.04004`, *Structural Limits of OHLCV-Based Intraday Signals in MNQ Futures: A Systematic Falsification Study*** — déjà présent dans `alpha_hunt/promising/` — est une falsification systématique de cette classe de signaux sur MNQ ; (d) le repo l'a déjà rencontré : `session_G` mesure **≈0 gross → −3 bps net (t −6)** sur le time-of-day de Gao à 3 bps RT (c'est l'origine de **L33b**).
- **Verdict :** **ÉCHOUE le filtre.** Déjà brûlé dans le repo, gross ≈ 0, one-sided. Ne pas re-proposer.

---

## Rang 3 — Mécanismes solides mais hors de notre portée d'exécution (à éliminer maintenant)

### **B4. Réversion court terme = rémunération de la fourniture de liquidité, conditionnelle au VIX**

- **Référence :** Nagel, *Evaporating Liquidity* (RFS 25(7), 2012).
- **Mécanisme :** les rendements des stratégies de réversion court terme **sont** le rendement de la fourniture de liquidité ; quand les intermédiaires contraints se retirent, le prix de la liquidité explose.
- **Conditions d'existence :** **prédictibles par le VIX** — rendements attendus et Sharpe conditionnels *« augmentent énormément »* en période de turbulence (2007-09). Même les réversions construites sur portefeuilles sectoriels, sans rendement inconditionnel, deviennent rentables à VIX élevé.
- **Ce qui le tue pour nous :** c'est un **long-short en coupe transverse d'actions** (ou de portefeuilles sectoriels), à horizon journalier/hebdomadaire — pas un signal intraday sur un indice unique. Le repo a déjà l'analogue : **L15** (les overlays de régime n'apportent que ~1.7 %/an sur les stratégies à Sharpe > 1) et le batch de **`regime_markov_sleeves_2026-07`** (« régime = alpha » FALSIFIÉ au filtre d'orthogonalité). Et l'edge est **concentré dans les fenêtres de stress** — c'est-à-dire précisément **la queue gauche que la barrière journalière FTMO −5 % interdit de traverser**. Un edge dont le Sharpe conditionnel n'existe qu'en crise est **structurellement anti-propfirm**.
- **Verdict :** **ÉCHOUE le filtre — pour la raison la plus intéressante de cette revue.** Nagel explique *pourquoi* la MR retail est morte : ce n'est pas une inefficience, c'est **le prix d'un service** ; le collecter demande un inventaire, un bilan et un tier de coût de teneur de marché. **La bonne nouvelle épistémique :** cela **rationalise a posteriori** tous les négatifs MR du repo. La MR est réelle et payée — juste pas à nous. Corollaire à graver : **cesser de chercher de la MR intraday retail** ; c'est chercher une rémunération de fourniture de liquidité depuis le côté preneur de liquidité.

### **B5. Impact transitoire et sa relaxation (propagateur de Bouchaud)**

- **Références :** Bouchaud, Gefen, Potters & Wyart (2004) ; Lillo & Farmer (2004) ; littérature propagateur.
- **Mécanisme :** le flux d'ordres signé est **fortement autocorrélé** (`C(ℓ) ~ ℓ^{-γ}`, γ ≈ 0.5 sur actions) ; pour que le prix reste une martingale, l'impact doit être **transitoire** et décroître en `G(ℓ) ~ ℓ^{-β}` avec **β = (1−γ)/2**. La relaxation d'impact **est** la mean-reversion microstructurelle.
- **Ce qui le tue :** l'égalité `β = (1−γ)/2` est **exactement la condition d'efficience** — le propagateur est calibré pour **annuler** l'autocorrélation du flux et rendre les rendements imprévisibles. **La théorie prédit littéralement l'absence d'edge exploitable** sur ce canal ; la relaxation n'est capturable qu'en voyant le flux signé (données propriétaires) et à un tier de coût de teneur de marché. Cela **explique le résultat de A.2** : le flip momentum est aussi négatif que la MR — *« ce n'est pas le mauvais signe, c'est aucun signe »*, ce qui est précisément ce que le propagateur prédit.
- **Verdict :** **ÉCHOUE le filtre — mais c'est le meilleur argument théorique de tout le dossier.** À citer chaque fois qu'une variante MR prix-seul est reproposée : la MR intraday sans flux signé est **structurellement invisible par construction du marché**.

### **B6. OU / estimation de la vitesse de retour et demi-vie**

- **Références :** Avellaneda & Lee, *Statistical Arbitrage in the U.S. Equities Market* (Quantitative Finance, 2010) ; Leung & Li sur la sortie optimale sous coûts et stop-loss (arXiv 1411.5062, 1707.03498).
- **Mécanisme :** modéliser le **résidu idiosyncratique** (post-PCA / post-facteurs) en OU `dX = κ(μ−X)dt + σ dB`, entrer sur le s-score `s = (X−m)/σ_eq`, `σ_eq = σ/√(2κ)`, sortir sur retour à l'équilibre ; demi-vie = `ln2/κ`.
- **Note de méthode (et c'est le point important) :** Avellaneda-Lee applique l'OU au **résidu**, pas au prix. `mr_deepdive.py` estime une demi-vie AR(1) **sur la déviation de prix brute intra-séance** et l'appareille — la démarche est bonne dans l'esprit (**et le rapport a raison de dire que l'appariement half-life n'a pas fabriqué d'EV**), mais elle n'est pas ce que fait la littérature. Sur un indice **unique**, il n'y a pas de résidu à extraire : c'est le prix lui-même, donc du beta. La condition d'existence de l'OU (stationnarité) est fournie par la **construction du résidu**, pas par le fait de soustraire une moyenne mobile.
- **Ce qui le tue chez nous :** L27 (le spread coïntégré hérite d'une dérive relative), L28 (2× le markup de financement sur une paire CFD), et l'absence d'univers cross-sectionnel FTMO. Signal supplémentaire du repo : le retour du grid en A.1 — **la demi-vie AR(1) 30 m/60 m est NaN sur tous les indices** (φ hors de (0,1)), c'est-à-dire **pas de retour à la moyenne détectable** à ces horizons.
- **Verdict :** **ÉCHOUE le filtre** sur instruments FTMO. Valeur résiduelle : l'estimation de demi-vie reste le bon **outil de diagnostic** pour toute sortie (mais ce n'est pas un edge).

### **B7. Saisonnalité intra-journée et périodicité en coupe transverse**

- **Références :** Heston, Korajczyk & Sadka (JF 2010) ; Bogousslavsky (JF 2016, JFE 2021).
- **Mécanisme :** rééquilibrage peu fréquent — les traders qui absorbent un choc de liquidité en prenant une position sous-optimale la déchargent à leur **prochaine période d'activité**, ce qui recrée un choc de même signe ⇒ autocorrélations qui **changent de signe et deviennent positives à l'horizon de rééquilibrage**, et saisonnalité en coupe transverse.
- **Où l'effet se réalise :** primes de taille et d'illiquidité dans **les 30 dernières minutes** ; profitabilité et vol idiosyncratique s'accumulent en journée mais **subissent de larges rendements négatifs overnight** ; réversion significative entre 15h30-16h00 et le lendemain matin.
- **Ce qui le tue pour nous :** **entièrement cross-sectionnel actions**. Et le repo a déjà brûlé l'analogue intraday-flat : **H3 de `fx_intraday`** (balayage 100 cellules dow×session) — meilleure cellule au plafond du hasard, décroissance monotone vers zéro après 2015 ; sleeve WF net SR **−4.27**, DSR 0.
- **Verdict :** **ÉCHOUE le filtre.** Ne pas re-proposer de scan de saisonnalité intra-journée — c'est un plafond de chance, déjà mesuré comme tel dans ce repo.

### **B8. Flux mécaniques prévisibles (ETF à levier, vol-targeting, risk parity)**

- **Références :** littérature sur l'impact des flux prévisibles (produits VIX à levier, JBF 2021) ; BIS WP 952 sur l'effet prix des fonds passifs ; encadré BCE FSR 2020 sur le vol-targeting.
- **Mécanisme :** les ETP à levier doivent **rééquilibrer leur couverture futures quotidiennement**, dans le sens du mouvement du jour, **dans les 30-60 dernières minutes** ⇒ flux forcé, prévisible, pro-cyclique. Les stratégies vol-control (~300-500 Md$ de notionnel, majoritairement en futures S&P 500) suivent `allocation = vol cible / vol réalisée` ⇒ flux mécaniques déclenchés par des chocs de vol.
- **Conditions d'existence :** amplitude **∝ au mouvement du jour** ⇒ concentrée sur les journées de stress (le 3 septembre cité : 15 Md$ vendus, −3 % sur le Nasdaq 100).
- **Ce qui le tue — et c'est net :** (a) le flux est **du côté du momentum**, donc le fader est du **short gamma** — précisément le profil de **queue gauche longue** que notre contrainte interdit (98 % des morts passent par la barrière journalière) ; (b) le déclencheur exige de **connaître l'AUM et les seuils**, données propriétaires ; (c) l'amplitude n'est significative que les jours où la barrière journalière est déjà en jeu ; (d) c'est **la même famille que B2**, dont la mort par découpage algorithmique du flux est maintenant documentée.
- **Verdict :** **ÉCHOUE le filtre — sur le profil de distribution, pas sur l'amplitude.** Mécanisme réel, amplitude largement > 3 bps, mais **anti-corrélé à notre critère de sélection**. À éliminer explicitement pour qu'il ne remonte pas.

---

## B.9 — Ce que cette revue dit de nos deux familles prioritaires

**Mean-reversion intraday-flat.** La littérature ne dit pas « ça ne marche pas » — elle dit **qui est payé et pourquoi nous ne le sommes pas**. Nagel (B4) : la réversion court terme **est** la rémunération de la fourniture de liquidité. Bouchaud (B5) : la relaxation d'impact est **calibrée par le marché pour annuler** la prévisibilité du flux. Les deux convergent : la MR intraday est une **prime de teneur de marché**, accessible en voyant le flux signé et en payant un tier de coût institutionnel. Le repo l'a établi **empiriquement** trois fois (`ALPHA_hunt`, `mr_deepdive`, `intraday_mr_ftmo`) ; la littérature fournit la **cause**. **La famille doit être considérée comme fermée par mécanisme, pas seulement par mesure** — et c'est plus robuste que le « 0/344 » audité en A.1, dont la fenêtre horaire était fausse.

**Microstructure de session.** Un seul point ouvert, et il est étroit : **B1, la fenêtre de clôture de l'indice** — le seul mécanisme de cette revue dont l'amplitude publiée dépasse largement 3 bps, avec un flux forcé identifié (concentration du volume institutionnel dans l'auction), **et la seule fenêtre que ni A.1 ni A.2 n'ont couverte**. Tout le reste de la famille session est fermé : le drift de réouverture est **mort et autopsié** (B2), le momentum intraday est brûlé dans ce repo (B3), la saisonnalité est un plafond de chance (B7), les flux mécaniques ont le mauvais profil de queue (B8).

**Avertissement le plus important de cette revue, et il porte sur du code en production :** B2 documente la mort d'un effet **de la même famille que notre L56** (drift de réouverture, mécanisme d'inventaire), avec un **diagnostic causal chiffré** — la dispersion du volume signé de clôture s'est comprimée de 6.5 % à 2.9 %. Ce diagnostic est **applicable tel quel à l'or**, ne coûte aucun essai, et devrait être fait **avant** tout dimensionnement supplémentaire sur L56.

---

## Corrections `CLAUDE.md` / `N_ledger.md` appelées par cet audit

1. **`N_ledger.md` (114/126/128/130)** — retirer « 0/344 two-sided » comme argument de fermeture et comme déflateur DSR de l'espace indices-MR. Fenêtre horaire erronée (A.1), 60/344 essais non reproductibles.
2. **Fermeture des indices** — la citer via `yt_strategy_replications/intraday_mr_ftmo/FINDINGS.md`, **pas via L43**. Graver le candidat de leçon déjà nommé `price-only-intraday-MR-is-autocorr-and-cost-dead-on-equity-indices-too`.
3. **`CLAUDE.md` §données** — « indices et or plutôt propres » est **faux pour US30** : colonne `spread` nulle à **79.7 % / 100 % / 74.9 %** en 2019 / 2020 / 2021.
4. **`event_drift` / top10** — marquer les 24 cellules `_SS` comme **non-essais** (miroir mécanique), retirer 24 de `n_trials`, et noter que L42 n'a **aucun support two-sided**.
5. **Panels EET** — `mr_deepdive.py` est un consommateur de `panels/m5_indices/*` avec le bug `tz_localize("UTC")`. À ajouter à `_audit/m5_indices_migration_checklist_2026-06-10.md`.

---

## Sources

- [Baltussen, Da & Soebhag — End-of-Day Reversal (SSRN 5039009)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5039009) · [PDF EFMA](http://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2024-Lisbon/papers/EndofDayReversal_withnames.pdf)
- [Boyarchenko, Larsen & Whelan — The Overnight Drift (RFS 36(9))](https://academic.oup.com/rfs/article-abstract/36/9/3502/7076616) · [NY Fed SR 917](https://www.newyorkfed.org/research/staff_reports/sr917)
- [Boyarchenko, Larsen & Whelan — The Disappearing Overnight Drift (Liberty Street Economics, juillet 2026)](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/) · [SSRN 7035838](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7035838)
- [Lou, Polk & Skouras — A Tug of War: Overnight versus Intraday Expected Returns (JFE 134(1))](https://www.sciencedirect.com/science/article/abs/pii/S0304405X19300650) · [PDF](https://personal.lse.ac.uk/polk/research/TugOfWar.pdf)
- [Gao, Han, Li & Zhou — Market Intraday Momentum (JFE)](https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351) · [SSRN 2440866](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866)
- [Bogousslavsky — Infrequent Rebalancing, Return Autocorrelation, and Seasonality (JF 2016)](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12436) · [SSRN 2308366](https://www.ssrn.com/abstract=2308366)
- [Bogousslavsky — The Cross-Section of Intraday and Overnight Returns (JFE 2021)](https://www.sciencedirect.com/science/article/abs/pii/S0304405X21000854) · [SSRN 2869624](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2869624)
- [Nagel — Evaporating Liquidity (RFS 25(7), 2012)](https://academic.oup.com/rfs/article-abstract/25/7/2005/1602153) · [NBER w17653](https://www.nber.org/papers/w17653)
- [Avellaneda & Lee — Statistical Arbitrage in the U.S. Equities Market](https://www.researchgate.net/publication/227623962_Statistical_Arbitrage_in_the_US_Equities_Market)
- [Leung & Li — Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit (arXiv 1411.5062)](https://arxiv.org/pdf/1411.5062)
- [Bouchaud et al. — Price Impact / propagateur (arXiv 0903.2428)](https://arxiv.org/pdf/0903.2428) · [Order flow and price formation (arXiv 2105.00521)](https://arxiv.org/pdf/2105.00521)
- [Heston, Korajczyk & Sadka — Intraday Patterns in the Cross-section of Stock Returns](https://www.researchgate.net/publication/45918655_Intraday_Patterns_in_the_Cross-section_of_Stock_Returns)
- [Who trades at the close? Implications for price discovery and liquidity (JFM)](https://www.sciencedirect.com/science/article/abs/pii/S1386418123000502) · [SSGA — Closing time: how passive investing is reshaping equity market microstructure](https://www.ssga.com/us/en/institutional/insights/how-passive-investing-reshaping-microstructure)
- [The market impact of predictable flows: evidence from leveraged VIX products (JBF 2021)](https://www.sciencedirect.com/science/article/abs/pii/S0378426621002363) · [BIS WP 952 — Passive funds affect prices](https://www.bis.org/publ/work952.pdf) · [BCE FSR 2020 — vol-targeting et sell-off](https://www.ecb.europa.eu/press/financial-stability-publications/fsr/focus/2020/html/ecb.fsrbox202005_02~f6616db9be.en.html)
- [Structural Limits of OHLCV-Based Intraday Signals in MNQ Futures (arXiv 2605.04004)](https://arxiv.org/pdf/2605.04004)
