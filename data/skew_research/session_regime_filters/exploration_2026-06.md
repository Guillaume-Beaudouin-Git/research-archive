# Skew research — session_regime_filters (filtres de régime sur signaux directionnels)
### Exploration 2026-06. Objectif : briques skew+ décorrélées pour portefeuille L7.
*Terrain neuf : signaux directionnels (trend/momentum = skew+ par nature). Question L7 = le FILTRE gagne-t-il sa place ? Test : filtré vs non-filtré, mécanisme justifié, 1 seul ajout (L10).*

> **Réconciliation headline — L15 + IDEA_3A_4A** : un overlay de régime n'est utile que s'il **bat le signal non-filtré ET le beta de la jambe tradée**. Prior : les filtres ajoutent rarement de l'alpha (lift sub-threshold), parfois en détruisent. Confirmé ci-dessous, avec nuances.

---

## Résultats — filtré vs non-filtré (médiane cross-univers : SP500/NAS100/DAX/FTSE/NIKKEI [+GOLD/OIL pour #1-3])

| # | filtre | version | SR | skewM | MaxDD | t | inMkt | verdict filtre |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | MA200 sur trend court | non-filtré | +0,11 | −0,07 | −65,6% | +0,55 | 100% | |
| 1 | | **MA200-filtré** | **+0,22** | **+0,45** | −52,2% | +1,10 | 74% | ✅ **améliore profil** (edge faible) |
| 2 | vol-régime sur Donchian | non-filtré | −0,02 | +0,14 | −76,3% | −0,10 | 100% | |
| 2 | | low-vol only | +0,00 | +0,08 | −53,3% | +0,01 | 50% | ✗ rien à filtrer |
| 2 | | high-vol only | +0,01 | −0,04 | −69,5% | +0,06 | 45% | ✗ Donchian mort |
| 3 | ADX>25 sur TSMOM | non-filtré | +0,15 | −0,22 | −62,6% | +0,73 | 100% | |
| 3 | | **ADX-filtré** | **−0,01** | +0,59 | −59,5% | −0,04 | 35% | ❌ **détruit l'edge** |
| 4 | breadth sur CS-momentum | non-filtré | +0,05 | −1,11 | −88,3% | +0,24 | 100% | |
| 4 | | **breadth-filtré** | **+0,53** | +0,23 | −30,7% | **+2,62** | 65% | ⚠ **beta timé** (voir P2) |
| 5 | flat-sur-événement | non-filtré (2020+) | +0,36 | +0,02 | −24% | +0,90 | 100% | |
| 5 | | **flat-on-FOMC/CPI** | **+0,28** | −0,00 | −27% | +0,69 | 96% | ❌ **dégrade** |

## #4 — Phase-2-lite : le standout est un BETA TIMÉ (beat-the-beta le tue)
t=2,62 + skew+ semblait le gagnant. Test décisif (IDEA_3A_4A : l'overlay bat-il la jambe tradée ?) :

| version | SR | skewM | MaxDD | t |
|---|---:|---:|---:|---:|
| strongest + breadth | +0,53 | +0,23 | −31% | +2,62 |
| **EW-panier + MÊME breadth** | **+0,87** | −0,04 | −28% | **+4,27** |
| EW-panier buy&hold | +0,48 | −0,62 | −61% | +2,37 |

- **alpha(strongest − EW-timé) = −0,41bp/j, t=−0,51** → la sélection cross-sectionnelle « strongest » ajoute un **alpha négatif**. Toute la valeur vient du **timing breadth** = être long le panier d'indices en uptrend = **timing de beta equity**.
- Robuste (seuil 0,4/0,5/0,6 → t 2,62/2,62/2,94 ; MA50/100 → t 2,62/2,06 ; coût 0/2/5bp → t 2,62/2,50/2,32) et OOS-stable (1ʳᵉ moitié SR 0,31 / 2ᵉ 0,76) — **mais robuste sur le mauvais objet** : c'est du beta equity long-biais, pas un alpha décorrélé. Pour L7 (briques décorrélées), ce n'est qu'« long equity timé » (décorrélé de book_JG seulement parce que book_JG est FX/or). La décorrélation est illusoire ; contre un benchmark equity il serait fortement corrélé.

## Lecture des 5 filtres (le cœur)
1. **MA200 (#1) — gagne sa place sur le profil, mais le signal sous-jacent est faible.** Skew −0,07→+0,45, MaxDD −66%→−52%, SR ×2 (0,11→0,22). Mécanisme sain (ne pas combattre la tendance majeure ; il retire 26% du temps, les signaux contre-MA200). MAIS t reste 1,10 : un filtre sain sur un edge faible → un edge faible au **meilleur profil**, pas une brique.
2. **Vol-filter Donchian (#2) — rien à filtrer.** Donchian daily mort dans tous les régimes (SR ~0). Cohérent `breakout_deepdive` (intraday mort, delay-1 −97%) ; le daily aussi. Un filtre ne ressuscite pas un signal nul.
3. **ADX (#3) — détruit l'edge en montant le skew (faux ami).** SR 0,15→−0,01. L'ADX **garde les tendances mûres** (qui revertent) et **coupe les entrées précoces** (où le momentum gagne) → il est anti-corrélé à l'edge. Le skew monte (−0,22→+0,59) parce qu'on tient moins de positions, plus longues/convexes — **side-effect, pas alpha**. Cas IDEA_3A_4A : l'overlay détruit la valeur.
4. **Breadth (#4) — beta equity timé déguisé en CS-momentum** (voir P2). Le timing breadth marche (c'est du beta), la sélection momentum nuit.
5. **Flat-sur-événement (#5) — retire du drift POSITIF, pas du bruit.** SR 0,36→0,28. Les jours FOMC/CPI portent un drift positif (pré-FOMC, **session_3 C1** : pré-FOMC skew+ t 2-2,6). Le filtre « éviter le bruit événementiel » est **faux empiriquement** : il coûte. Réconciliation directe avec l'archive.

## VERDICT FINAL (session_regime_filters)
**0 brique L7 retenue.** Résultat méthodologique net, qui **raffine L15** :
- **Un skew amélioré NE suffit PAS** : #3 (ADX) et #4 (breadth) montent le skew tout en détruisant l'edge (#3 : SR→−0,01) ou en le déguisant en beta (#4). Le skew+ d'un filtre est souvent un **side-effect** (positions plus longues/convexes / timing beta), pas un alpha neuf.
- **Le test décisif d'un filtre = battre le signal non-filtré ET le beta de la jambe tradée.** Seul #4 passe t>2, et il échoue le beat-the-beta (EW-panier+breadth SR 0,87 > 0,53 ; sélection = alpha −0,41bp/j).
- **Le seul filtre honnêtement améliorateur (#1 MA200)** agit sur un signal trop faible (t 1,10) → pas de brique.
- **Le filtre événementiel « justifié en intuition » (#5) est faux** : l'événement porte un drift, pas du bruit.

→ Les filtres de régime ne **fabriquent** pas d'alpha ici ; au mieux ils améliorent le profil d'un edge déjà faible (#1), au pire ils détruisent (#3) ou déguisent du beta (#4). Cohérent avec le mur du projet : pas d'edge directionnel FTMO au-dessus du gate, filtre ou non.

## Candidats-leçons (NOMMÉS, pas numérotés — tranché au merge)
- **« Skew amélioré ≠ filtre qui gagne sa place »** — #3 ADX (skew −0,22→+0,59 mais SR 0,15→−0,01) et #4 breadth montrent qu'un filtre peut monter le skew en détruisant/déguisant l'edge. Le skew+ d'un overlay est souvent un side-effect (convexité / moins de trades / timing beta), à distinguer d'un alpha neuf.
- **« Test décisif d'un overlay = battre le beta de la jambe tradée »** (IDEA_3A_4A confirmé) — #4 breadth-momentum : EW-panier+breadth (SR 0,87) bat strongest (0,53), la sélection CS ajoute alpha −0,41bp/j (t−0,51). La valeur = timing beta, pas la sélection. Toujours comparer à la version timée la plus simple.
- **« ADX gate le momentum à contretemps »** — garde les tendances mûres (revert), coupe les entrées précoces (gagnantes) → SR 0,15→−0,01. Le filtre force-de-tendance est anti-corrélé à l'edge momentum, pas un confirmateur neutre.
- **« Flat-sur-événement retire du drift positif, pas du bruit »** — FOMC/CPI portent un drift positif (pré-FOMC, session_3 C1) ; flat-on-event coûte (SR 0,36→0,28). Un filtre justifié « en intuition » doit être mesuré (L33), pas supposé.
- **« Filtre sain sur signal faible = signal faible au meilleur profil »** — MA200 améliore réellement le profil (skew −0,07→+0,45) mais t reste 1,10 ; un bon filtre ne crée pas d'edge là où il n'y en a pas.

---
*session_regime_filters, 5 filtres × univers indices/commodités. Données : Yahoo OHLC (^GSPC/^NDX/^GDAXI/^FTSE/^N225 + GC=F/CL=F), news_events_2020_2025.csv (FOMC/CPI, 175 jours), book_JG (trend benchmark). Tout backtest, 0 jour live. Réconcilié archive (L15, IDEA_3A_4A, breakout_deepdive, session_3 C1 — pas de re-preuve). Rien figé, rien mergé. Écrit uniquement dans ce périmètre ; non touché aux autres sessions ni overnight_research/.*
