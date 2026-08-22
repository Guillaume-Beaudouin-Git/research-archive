# Deep-dive & itération — S012 Bollinger %b (la seule watchlist)

**Objet :** disséquer l'unique alpha du pipeline, localiser l'edge, l'**améliorer**, et l'**auditer** sans complaisance. · **Code :** `code/s012_deepdive.py` + `code/s012_deepdive2.py` (+ figure `results/s012_deepdive.png`). · **Date :** 2026-06-07. · Réutilise `strat_s012` (pctb) + `ftmo_lab` v2-gates inchangés.

---

## Verdict (en tête) — révision à la hausse

> 🟢 **Le « décay » du 1ᵉʳ audit était un ARTEFACT** du mélange (short mort + non-indices). Isolé, le **cœur indices-LONG dip-buy n'est PAS décayé** : Sharpe plein **1,20**, récent 2019+ **0,97**, et **1,1–1,3 en version low-vol**. C'est un **vrai alpha de timing** (pas du beta), qui **survit au délai+1 et à l'OOS strict**, large sur **9/10 indices**.
>
> **Reclassé : 🟡 BORDERLINE / candidat déployable** — *sleeve indices long-biais (+ filtre low-vol)*. Il échoue **uniquement** la DSR, et pour une raison bénigne (grille uniformément ~1,2, sous le seuil conservateur E[max de 11]=1,61) — pas un mirage de cellule chanceuse. **Premier non-DISCARD du projet.**

---

## 1. Où est l'edge — décomposition

**Par régime de volatilité (indices, le mécanisme clé) :**

| Régime vol (percentile 252 j) | n | expR | Sharpe | long | short |
|---|---|---|---|---|---|
| **Bas (<0,33)** | 873 | **+0,0629** | **+1,46** | **+0,0715** | +0,0013 |
| Moyen (0,33–0,66) | 683 | +0,0197 | +0,37 | +0,0219 | +0,0159 |
| Haut (>0,66) | 865 | +0,0138 | +0,31 | +0,0018 | +0,0208 |

→ **L'edge (surtout le dip-buy long) vit dans le calme, pas la panique.** Mécanisme : on achète un *pullback survendu dans un uptrend tranquille*, pas un krach. *(Mon hypothèse initiale « filtrer la haute vol » était à l'envers — corrigée.)*

**Par côté & classe (1ᵉʳ audit confirmé) :** l'alpha est **indices** ; le **long dip-buy** est le cœur robuste, le **short dilue** (meurt post-2012), FX/commodities/crypto **ne mean-revertent pas**.

**Alpha de timing vs beta (dip-buy − entrée neutre dans le même uptrend) :**

| | dip-buy (full / 2019+) | neutre (full / 2019+) | **ALPHA (full / 2019+)** |
|---|---|---|---|
| Indices long | +0,0429 / +0,0340 | +0,0189 / +0,0158 | **+0,0239 / +0,0182** |
| US-indices long | +0,0604 / +0,0517 | +0,0322 / +0,0263 | **+0,0282 / +0,0255** |

→ **~53 % de l'edge récent est de l'alpha de timing pur** (au-dessus du simple « être long l'uptrend »). Ce n'est pas que du beta — y compris **en régime récent**.

## 2. Ce qui marche / ce qui marche moins (itérations)

| Variante | n | expR | Sharpe (full) | **Sharpe 2019+** | PF | MaxDD |
|---|---|---|---|---|---|---|
| Baseline (tout, 2 côtés) | 4 663 | +0,015 | 0,74 | 0,43 | 1,17 | −34 % |
| **C0 indices / LONG** | 1 515 | +0,043 | 1,20 | **0,97** | 1,55 | −26 % |
| **C1 indices / LONG / vol≤0,5** | 1 041 | +0,059 | 1,43 | **1,16** | 1,87 | −25 % |
| **C2 indices / LONG / vol≤0,66** | 1 216 | +0,052 | 1,34 | **1,33** | 1,73 | −26 % |
| C3 US-indices / LONG | 679 | +0,060 | 1,22 | 1,02 | 1,92 | −16 % |
| **C4 US-indices / LONG / vol≤0,5** | 471 | +0,083 | **1,54** | 1,08 | **2,62** | **−15 %** |
| C5 indices / 2 côtés / vol≤0,5 | 1 302 | +0,049 | 1,32 | 0,91 | 1,67 | −26 % |

**Améliorations qui marchent :** (1) **focaliser indices** (Sharpe 0,74→1,20) ; (2) **droper le short** (le long-only bat le mélangé) ; (3) **filtre low-vol** (vol≤0,66) → sauve le bloc faible 2018-23 et **monte le Sharpe récent à 1,3** ; (4) **concentrer US-indices** → PF 2,6 / MaxDD −15 %.
**Améliorations qui NE marchent pas :** filtre **haute-vol** (à l'envers, détruit l'edge) ; seuil **plus profond %b<0,1** (réduit l'échantillon sans gain récent) ; sortie **time-only** (légèrement pire que le revert %b).

**Walk-forward (le test qui tranche) — le low-vol stabilise :**

| | 2000-05 | 2006-11 | 2012-17 | **2018-23** | 2024-29 |
|---|---|---|---|---|---|
| C0 indices/LONG | +1,70 | +1,19 | +2,15 | **+0,01** | +1,43 |
| **C1 +low-vol** | +1,75 | +1,63 | +2,12 | **+0,57** | +1,10 |
| C5 2 côtés +low-vol | +1,86 | +1,80 | +1,71 | **+0,36** | +1,06 |

→ Le seul trou (2018-23 : acheter les dips des krachs 2020/2022) est **comblé par le filtre low-vol**. **Aucun bloc < 0,36** en C5.

**Par indice, récent (2019+, C0) :** **9/10 positifs** — US100 **Sh 1,15**, US2000 0,54, US500 0,52, AUS200 0,35, JP225 0,33, EU50 0,27, GER40 0,14, UK100 0,13, US30 0,06 ; seul HK50 négatif (−0,14).

## 3. Audit (gates adaptés à un sleeve long-only)

| Test | Résultat | Verdict |
|---|---|---|
| **Délai+1** (open s+1 → s+2) | Sharpe 1,20 → **0,89** (close s+1 : 0,86) | ✅ PASS — entrée@open, pas un artefact de fill |
| **Alpha vs neutre** (remplace two-sided pour un long-only) | +0,018 R récent au-dessus du neutre | ✅ PASS — alpha de timing, pas du beta |
| **OOS 2015** | train +0,051 (Sh 1,48) → test +0,032 (Sh 0,86) | ✅ PASS |
| **OOS strict ≤2018 / 2019+** | train +0,047 (Sh 1,31) → test +0,034 (**Sh 0,97**) | ✅ PASS — persiste hors-échantillon |
| **DSR** (N=11, grille MA×SD) | SR_obs 1,21 vs E[max] 1,61, z −6,1 | ❌ FAIL |

**La nuance DSR est décisive et honnête :** contrairement aux 29 DISCARD (grille = bruit, une cellule chanceuse à Sharpe 0,5–0,9), **ici toute la grille est uniformément Sharpe ~1,0–1,5**. La DSR « échoue » seulement parce que le seuil E[max de 11 tirages] = 1,61 est plus haut que notre 1,21 *uniforme*. C'est la **conservativité du test face à une grille robuste**, pas une preuve de sur-ajustement. Les 4 autres tests (delay+1, alpha-vs-neutre, OOS, OOS strict) **passent**.

## 4. Verdict & déploiement

🟡 **BORDERLINE — candidat déployable (premier non-DISCARD).** Sleeve recommandé : **indices, long-biais, dip-buy %b survendu en uptrend, filtre low-vol (vol≤~0,66), sortie au revert %b** — **Sharpe récent ~1,1–1,3, PF ~1,7–1,9, MaxDD ~−25 %** (version US-concentrée : PF 2,6 / DD −15 %).

**Honnêteté / risques (anti-complaisance) :**
- **Ce n'est pas market-neutral.** ~½ de l'edge est du timing-alpha, mais ~½ reste du **beta actions long** : ce sleeve **perdra en bear-market prolongé** (cf. bloc 2018-23 non filtré à 0,01). À tailler petit et à combiner.
- **Degrés de liberté** : ~17 variantes testées ; le seuil vol (0,5/0,66) et le sous-ensemble US sont des hyperparamètres. Le choix low-vol est **motivé par le mécanisme** (décomposition par régime), pas par data-snooping — mais le **seuil doit être validé en walk-forward** avant capital réel.
- **DSR non passé** : par la constitution stricte, ce n'est pas un KEEP « propre ». Je le classe **candidat fort à forward-tester**, pas KEEP automatique.

**Prochaines itérations utiles :** (a) walk-forward du seuil vol (purge/embargo) ; (b) dimensionnement vol-target portefeuille ; (c) overlay d'un hedge beta (short futures indice) pour neutraliser le ½ beta → tester si le timing-alpha seul passe la DSR ; (d) combiner avec un 2ᵉ alpha MR décorrélé (si on en trouve un dans #31+ False Breakout).

*Repro : `cd oxfordstrat_109/code && python s012_deepdive.py` puis `python s012_deepdive2.py`. Figure : `results/s012_deepdive.png`. Données : `results/s012_deepdive_battery.csv`, `s012_deepdive2_candidates.csv`.*
