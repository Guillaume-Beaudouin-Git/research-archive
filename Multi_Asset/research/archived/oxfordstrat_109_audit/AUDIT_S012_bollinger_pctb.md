# AUDIT approfondi — S012 (Bollinger %b mean-reversion)

**Objet :** S012 a passé Gate 1 + Gate 2 (1ʳᵉ du pipeline) et n'a échoué que le DSR → traité ici en **quasi-candidat**. Cet audit tranche la vraie question : **est-ce un edge de mean-reversion réel ou du beta long déguisé ?** + robustesse du short, stabilité temporelle, coûts.
**Code :** `code/audit_s012.py` · **Date :** 2026-06-05 · **Config :** canonique Connors MA5 / SD1 / MA_Trend=200.

---

## Verdict de l'audit (en tête)

> **🟡 C'est un VRAI edge de mean-reversion — pas du beta — mais il a DÉCRU de façon monotone et n'est plus que marginal dans le régime actuel.**
>
> 1. **Alpha de timing réel et bilatéral** : le dip-buy (long) gagne **+0,0189 R au-dessus d'une entrée neutre dans le même uptrend** ; le rip-sell (short) gagne **+0,0119 R au-dessus d'une entrée neutre dans le même downtrend**. ⇒ **Ce n'est PAS du beta** : acheter le creux survendu / vendre le pic suracheté ajoute une vraie valeur de timing, des deux côtés.
> 2. **Mais décroissance monotone** : Sharpe **1,52 → 1,63 → 0,51 → 0,21** sur les 4 blocs 2000→2026. Fort avant 2012, marginal depuis 2018.
> 3. **Concentré sur les indices** (les deux côtés marchent) ; le short crypto est catastrophique.
>
> **Disposition : DISCARD comme stratégie autonome (décayée, Sharpe ~0,2 en régime récent), mais à mettre en WATCHLIST comme premier mécanisme d'alpha réel identifié — surtout en version focalisée indices.** Et : valide que **chercher un MR a du sens** → la #13 (variante filtre) et le **Doji (#16/#17, archétype MR indépendant)** méritent leur test complet.

---

## A) Le test décisif : alpha de timing vs beta

Pour isoler l'effet du *dip*, on compare l'entrée survendue (`%b<0,2`) à une **entrée neutre dans la même tendance** (`%b∈[0,4 ; 0,6]`, même filtre MA200, même sortie). Si le dip-buy ≈ neutre → c'est juste de l'exposition trend (beta). S'il fait nettement mieux → le creux est de l'**alpha**.

| Côté | Stratégie (dip/pop) | Entrée neutre (même trend) | **Alpha de timing** |
|---|---|---|---|
| **Long** (dip-buy) | **+0,0242** (win 71 %) | +0,0053 | **+0,0189** |
| **Short** (rip-sell) | **+0,0038** (win 66 %) | −0,0081 | **+0,0119** |

**Lecture :** ~78 % de l'edge long vient du *timing du creux*, pas du drift haussier (qui ne vaut que +0,005). Et le short a un **alpha positif** (+0,012) : vendre le pic suracheté bat une entrée short neutre — son expR absolu est mince (+0,004) uniquement parce qu'il combat le drift négatif du downtrend (−0,008). **Conclusion : edge MR authentique et bilatéral. Le Gate 2 PASS n'était pas un hasard.**

## B) Long-only vs short-only

| Livre | n | expR | Sharpe | CAGR | MaxDD |
|---|---|---|---|---|---|
| Long-only | 2 628 | +0,0242 | **+0,88** | +1,1 % | −29,0 % |
| Short-only | 2 035 | +0,0038 | +0,12 | +0,0 % | −12,3 % |
| Both | 4 663 | +0,0153 | +0,74 | +0,1 % | −34,5 % |

Le **long-only est le meilleur livre** (Sharpe 0,88) ; le short, malgré son alpha, **dilue** (combiné 0,74 < 0,88) — il est trop bruité/mince. Une version déployable serait **long-only** (ou long + short indices seulement).

## C) Walk-forward — **le point qui tranche le déploiement**

| Bloc (date d'entrée) | n | expR | Sharpe | long | short |
|---|---|---|---|---|---|
| 2000-2006 | 495 | +0,0391 | **+1,52** | +0,0562 | +0,0216 |
| 2006-2012 | 978 | +0,0328 | **+1,63** | +0,0278 | +0,0400 |
| 2012-2018 | 1 033 | +0,0116 | +0,51 | +0,0336 | −0,0193 |
| 2018-2026 | 2 157 | +0,0037 | **+0,21** | +0,0111 | −0,0056 |

**Décroissance monotone nette.** Edge fort et bilatéral avant 2012 (Sharpe ~1,5-1,6), puis **le short meurt post-2012** et le **long s'affaiblit** ; en régime récent (2018-2026) Sharpe **0,21** (marginal). C'est la cause de l'échec DSR/OOS : un **vrai edge, mais en fin de cycle de vie** (arbitragé / changement de régime — vol plus basse, MR moins payant).

## D) Par classe d'actif

| Classe | expR | long | short |
|---|---|---|---|
| **Indices** | **+0,0336** | +0,0429 | +0,0185 | ← les deux côtés marchent |
| Forex | +0,0054 | −0,0166 | +0,0233 | ← short ok, long non |
| Commodities | −0,0047 | +0,0006 | −0,0104 | ← ne MR pas |
| Crypto | −0,0268 | +0,0134 | **−0,0645** | ← short crypto catastrophique |

L'edge est **concentré sur les indices** (MR classique : on achète les pullbacks, on vend les rebonds dans un indice qui oscille). Crypto/commodities ne mean-revert pas ainsi. Une version focalisée **indices** serait nettement plus propre.

## E) Stress coûts
| Mult. | expR | PF | Sharpe |
|---|---|---|---|
| ×1,0 | +0,0153 | 1,172 | 0,74 |
| ×1,5 | +0,0137 | 1,152 | 0,66 |
| ×2,0 | +0,0120 | 1,133 | 0,58 |

**Survit au ×2** (PF 1,13). Robuste aux coûts — l'edge n'est pas une illusion de frais.

---

## Synthèse & recommandation

S012 est le **premier mécanisme d'alpha réel** du pipeline : mean-reversion authentique (alpha de timing bilatéral, pas du beta), robuste aux coûts, concentré sur les indices. **Mais il a décru de Sharpe ~1,6 (pré-2012) à ~0,2 (post-2018)** — il n'est **pas déployable seul aujourd'hui**, ce que le DSR et l'OOS captaient.

**Disposition :**
- **Verdict pipeline : reste DISCARD** (décayé + DSR), mais reclassé **« DISCARD — alpha MR réel mais décayé (watchlist) »** plutôt que mort sec.
- **Si on voulait l'exploiter** : version **indices, long-biais** (le long dip-buy est le cœur robuste), vol-targetée (MaxDD −29→cible), en acceptant un Sharpe récent modeste — à combiner, pas en solo.
- **Conséquence pour la suite** : l'existence d'un alpha MR réel (même décayé) **valide la piste mean-reversion**. La **#13** (Bollinger + filtre — peut assainir le short / réduire le bruit DSR) et surtout le **Doji (#16/#17)** — archétype MR **mécaniquement indépendant** (chandelier de retournement, pas écart à une moyenne) — méritent un **test complet** : ils pourraient être un MR **moins décayé** ou plus robuste.

*Repro : `cd oxfordstrat_109/code && python audit_s012.py` (sortie complète dans la console).*
