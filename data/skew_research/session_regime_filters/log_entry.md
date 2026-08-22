# Entrée de log — session_regime_filters (CANDIDAT, à merger par le mainteneur)
*Candidat de section, périmètre session_regime_filters uniquement. Numérotation/intégration tranchées au merge. Ne PAS écrire dans le log partagé (collision sessions parallèles). Rien figé.*

---

## [2026-06] Skew research — session_regime_filters (filtres de régime sur signaux directionnels)

**Objectif** : briques skew+ décorrélées pour portefeuille L7. Test = filtré vs non-filtré, le filtre gagne-t-il sa place ? Détail : `data/skew_research/session_regime_filters/exploration_2026-06.md`.

**Résultat : 0 brique retenue.** Raffine L15 : les filtres ne fabriquent pas d'alpha ; au mieux ils améliorent le profil d'un edge faible, au pire ils détruisent/déguisent du beta.

- **#1 MA200 sur trend court** — ✅ améliore le profil (SR 0,11→0,22, skew **−0,07→+0,45**, MaxDD −66%→−52%) mais signal sous-jacent trop faible (t 1,10). Filtre sain, pas de brique.
- **#2 vol-filter Donchian** — ✗ rien à filtrer (Donchian daily mort, SR ~0 tous régimes ; cohérent breakout_deepdive).
- **#3 ADX>25 sur TSMOM** — ❌ **détruit l'edge** (SR 0,15→−0,01) en montant le skew (−0,22→+0,59, side-effect). L'ADX garde les tendances mûres (revert) et coupe les entrées précoces (gagnantes).
- **#4 breadth sur CS-momentum** — ⚠ semblait gagnant (t=2,62, skew+) mais **beat-the-beta le tue** : EW-panier+MÊME breadth SR **0,87** > strongest 0,53 ; alpha sélection = **−0,41bp/j (t−0,51)**. = beta equity timé, pas alpha CS. Robuste (t 2,3-2,9, OOS-stable) mais sur le mauvais objet.
- **#5 flat-sur-FOMC/CPI** — ❌ **dégrade** (SR 0,36→0,28) : les jours événement portent un drift positif (pré-FOMC, session_3 C1) → on retire du bon, pas du bruit.

**Candidats-leçons (nommés, à numéroter au merge) :**
- « Skew amélioré ≠ filtre qui gagne sa place » (#3/#4 montent le skew en détruisant/déguisant l'edge ; skew+ d'overlay = side-effect convexité/timing-beta).
- « Test décisif d'un overlay = battre le beta de la jambe tradée » (IDEA_3A_4A ; #4 : EW+breadth 0,87 > strongest 0,53, sélection alpha −0,41bp/j).
- « ADX gate le momentum à contretemps » (garde tendances mûres/revert, coupe entrées précoces/gagnantes ; SR 0,15→−0,01).
- « Flat-sur-événement retire du drift positif, pas du bruit » (FOMC/CPI = drift+, session_3 C1 ; SR 0,36→0,28 ; mesurer L33, pas supposer).
- « Filtre sain sur signal faible = signal faible au meilleur profil » (MA200 skew −0,07→+0,45 mais t 1,10).

**Statut** : 0 jour live, tout backtest. Réconcilié archive (L15, IDEA_3A_4A, breakout_deepdive, session_3 C1 — pas de re-preuve). Coordination : écrit uniquement dans `session_regime_filters/`, non touché aux autres sessions ni `overnight_research/`. Ne pas merger sans revue mainteneur.
